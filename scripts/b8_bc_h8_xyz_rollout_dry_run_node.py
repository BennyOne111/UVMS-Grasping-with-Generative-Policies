#!/usr/bin/env python3

import json
from collections import deque
from pathlib import Path
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import rospkg
import rospy
import yaml
from gazebo_msgs.msg import ModelStates
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray, MultiArrayDimension, String


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from learning.eval.policy_runtime import RuntimePolicy, choose_device  # noqa: E402
from rexrov_single_oberon7_fm_dp.action_converter import action_to_msg  # noqa: E402
from rexrov_single_oberon7_fm_dp.ros_interface import (  # noqa: E402
    joint_state_maps,
    model_pose_from_states,
    model_twist_from_states,
    odom_to_pose_velocity,
    values_for_names,
)


def _load_yaml(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _package_path() -> Path:
    return Path(rospkg.RosPack().get_path("rexrov_single_oberon7_fm_dp"))


def _xyz_to_msg(action_xyz: np.ndarray) -> Float64MultiArray:
    values = np.asarray(action_xyz, dtype=np.float64)
    if values.shape != (3,):
        raise ValueError(f"action_xyz must have shape (3,), got {values.shape}")
    msg = Float64MultiArray()
    msg.layout.dim.append(MultiArrayDimension(label="action_xyz_dry_run", size=3, stride=3))
    msg.data = values.tolist()
    return msg


def _clip_xyz(action_xyz: np.ndarray, max_component: float, max_norm: float) -> Tuple[np.ndarray, Dict[str, object]]:
    raw = np.asarray(action_xyz, dtype=np.float64)
    clipped = np.clip(raw, -max_component, max_component)
    component_clipped = bool(np.any(np.abs(clipped - raw) > 1e-12))
    norm_before = float(np.linalg.norm(clipped))
    norm_clipped = False
    if norm_before > max_norm > 0.0:
        clipped = clipped * (max_norm / norm_before)
        norm_clipped = True
    return clipped, {
        "component_clipped": component_clipped,
        "norm_clipped": norm_clipped,
        "raw_norm": float(np.linalg.norm(raw)),
        "clipped_norm": float(np.linalg.norm(clipped)),
    }


class B8BCH8XYZRolloutDryRunNode:
    """BC h8 xyz live policy adapter that only publishes dry-run action labels."""

    def __init__(self) -> None:
        package_path = _package_path()
        config_path = Path(
            rospy.get_param(
                "~config",
                str(package_path / "config" / "b8_bc_h8_xyz_rollout_dry_run.yaml"),
            )
        ).expanduser()
        self.cfg = _load_yaml(config_path)
        self.obs_cfg = self.cfg.get("observation", {}) or {}
        self.runtime_cfg = self.cfg.get("runtime", {}) or {}
        self.safety_cfg = self.cfg.get("safety", {}) or {}
        self.output_cfg = self.cfg.get("output", {}) or {}

        if bool(rospy.get_param("~execute_actions", False)):
            raise RuntimeError("This adapter is dry-run only; execute_actions=true is forbidden")

        joints_cfg = _load_yaml(package_path / "config" / "active_joints_left_arm.yaml")
        self.active_joint_names = list(joints_cfg["active_joint_names"])
        self.gripper_joint_names = list(joints_cfg["gripper_joint_names"])

        checkpoint = str(rospy.get_param("~checkpoint", "")).strip()
        if not checkpoint:
            checkpoint = str(
                self.runtime_cfg.get(
                    "checkpoint",
                    str(package_path / "outputs" / "checkpoints" / "b8_primary30_bc_h8_xyz" / "best.pt"),
                )
            )
        device = choose_device(str(rospy.get_param("~device", self.cfg.get("device", "auto"))))
        self.policy = RuntimePolicy.from_checkpoint(checkpoint, device=device, policy_type="bc")
        if self.policy.action_dim != 3:
            raise RuntimeError(f"BC h8 xyz adapter requires action_dim=3, got {self.policy.action_dim}")
        if self.policy.action_horizon != 8:
            raise RuntimeError(f"BC h8 xyz adapter expects action_horizon=8, got {self.policy.action_horizon}")

        self.rate_hz = float(rospy.get_param("~rate_hz", self.runtime_cfg.get("rate_hz", 3.0)))
        self.max_duration_sec = float(
            rospy.get_param("~max_duration_sec", self.runtime_cfg.get("max_duration_sec", 7.2))
        )
        self.replan_every_steps = int(
            rospy.get_param("~replan_every_steps", self.runtime_cfg.get("replan_every_steps", 1))
        )
        self.max_policy_xyz_component = float(
            rospy.get_param(
                "~max_policy_xyz_component",
                self.safety_cfg.get("max_policy_xyz_component", 0.005),
            )
        )
        self.max_policy_xyz_norm = float(
            rospy.get_param("~max_policy_xyz_norm", self.safety_cfg.get("max_policy_xyz_norm", 0.00866))
        )
        self.raw_component_abort = float(
            rospy.get_param(
                "~raw_component_abort",
                self.safety_cfg.get("absolute_stop_if_raw_component_exceeds", 0.03),
            )
        )
        self.max_inference_latency_ms = float(
            rospy.get_param(
                "~max_inference_latency_ms",
                self.safety_cfg.get("max_inference_latency_ms", 200.0),
            )
        )
        self.allow_nominal_state_fallback = bool(self.obs_cfg.get("allow_nominal_state_fallback", False))
        self.allow_nominal_target_fallback = bool(self.obs_cfg.get("allow_nominal_target_fallback", False))
        self.zero_missing_gripper_state = bool(self.obs_cfg.get("zero_missing_gripper_state", True))
        self.include_progress = bool(self.obs_cfg.get("include_progress", True))

        self.base_odom_topic = self.obs_cfg.get("base_odom_topic", "/rexrov/pose_gt")
        self.joint_states_topic = self.obs_cfg.get("joint_states_topic", "/joint_states")
        self.model_states_topic = self.obs_cfg.get("model_states_topic", "/gazebo/model_states")
        self.target_model_name = self.obs_cfg.get("target_model_name", "cylinder_target_gate_probe")
        self.base_model_name = self.obs_cfg.get("base_state_fallback_model_name", "rexrov")
        self.nominal_base_pose = np.asarray(
            self.obs_cfg.get("nominal_base_pose", [2.0, 2.0, -40.0, 0.0, 0.0, 0.0, 1.0]),
            dtype=np.float64,
        )
        self.nominal_target_pose = np.asarray(
            self.obs_cfg.get("nominal_target_pose", [2.6, 2.0, -40.0, 0.0, 0.0, 0.0, 1.0]),
            dtype=np.float64,
        )

        self.action_xyz_pub = rospy.Publisher(
            self.output_cfg.get(
                "action_xyz_topic",
                "/rexrov_single_oberon7_fm_dp/policy/bc_h8_xyz/action_xyz_dry_run",
            ),
            Float64MultiArray,
            queue_size=10,
        )
        self.action_7d_pub = rospy.Publisher(
            self.output_cfg.get(
                "action_7d_topic",
                "/rexrov_single_oberon7_fm_dp/policy/bc_h8_xyz/action_7d_label_dry_run",
            ),
            Float64MultiArray,
            queue_size=10,
        )
        self.status_pub = rospy.Publisher(
            self.output_cfg.get(
                "status_topic",
                "/rexrov_single_oberon7_fm_dp/policy/bc_h8_xyz/status",
            ),
            String,
            queue_size=10,
        )
        self.output_json = Path(
            str(
                rospy.get_param(
                    "~output_json",
                    self.output_cfg.get(
                        "output_json",
                        str(
                            package_path
                            / "outputs"
                            / "logs"
                            / "b8_rollout_planning"
                            / "bc_h8_xyz_dry_run_latest.json"
                        ),
                    ),
                )
            )
        ).expanduser()

        self._lock = threading.Lock()
        self._base_odom: Optional[Odometry] = None
        self._joint_state: Optional[JointState] = None
        self._model_states: Optional[ModelStates] = None
        self._obs_history = deque(maxlen=self.policy.obs_horizon)
        self._current_chunk: Optional[np.ndarray] = None
        self._chunk_index = 0
        self._steps_since_replan = self.replan_every_steps
        self._start_wall_time = time.monotonic()
        self._last_failure_reason = ""
        self._latency_over_limit_count = 0
        self._history: List[Dict[str, object]] = []
        self._aborted = False
        self._abort_reason = ""
        self._abort_context: Dict[str, object] = {}

        rospy.Subscriber(self.base_odom_topic, Odometry, self._base_odom_cb, queue_size=1)
        rospy.Subscriber(self.joint_states_topic, JointState, self._joint_state_cb, queue_size=1)
        rospy.Subscriber(self.model_states_topic, ModelStates, self._model_states_cb, queue_size=1)

        rospy.loginfo(
            "b8_bc_h8_xyz_rollout_dry_run loaded checkpoint=%s obs_horizon=%d action_horizon=%d "
            "action_dim=%d dry_run_only=true",
            checkpoint,
            self.policy.obs_horizon,
            self.policy.action_horizon,
            self.policy.action_dim,
        )

    def _base_odom_cb(self, msg: Odometry) -> None:
        with self._lock:
            self._base_odom = msg

    def _joint_state_cb(self, msg: JointState) -> None:
        with self._lock:
            self._joint_state = msg

    def _model_states_cb(self, msg: ModelStates) -> None:
        with self._lock:
            self._model_states = msg

    def _sample_observation(self) -> Optional[Tuple[np.ndarray, Dict[str, object]]]:
        with self._lock:
            base_odom = self._base_odom
            joint_state = self._joint_state
            model_states = self._model_states

        if base_odom is not None:
            base_pose, base_velocity = odom_to_pose_velocity(base_odom)
            base_state_source = "odom"
        elif model_states is not None:
            base_pose = model_pose_from_states(model_states, self.base_model_name)
            base_velocity = model_twist_from_states(model_states, self.base_model_name)
            base_state_source = "model_states"
            if base_pose is None or base_velocity is None:
                if not self.allow_nominal_state_fallback:
                    self._last_failure_reason = "base_state_unavailable"
                    return None
                base_pose = self.nominal_base_pose.copy()
                base_velocity = np.zeros((6,), dtype=np.float64)
                base_state_source = "nominal_fallback"
        elif self.allow_nominal_state_fallback:
            base_pose = self.nominal_base_pose.copy()
            base_velocity = np.zeros((6,), dtype=np.float64)
            base_state_source = "nominal_fallback"
        else:
            self._last_failure_reason = "base_state_unavailable"
            return None

        if joint_state is None:
            if not self.allow_nominal_state_fallback:
                self._last_failure_reason = "joint_states_unavailable"
                return None
            active_positions = np.zeros((len(self.active_joint_names),), dtype=np.float64)
            active_velocities = np.zeros((len(self.active_joint_names),), dtype=np.float64)
            gripper_state = np.zeros((len(self.gripper_joint_names),), dtype=np.float64)
            missing_gripper = list(self.gripper_joint_names)
            joint_state_source = "nominal_fallback"
        else:
            positions, velocities, _ = joint_state_maps(joint_state)
            active_positions, missing_pos = values_for_names(positions, self.active_joint_names)
            active_velocities, missing_vel = values_for_names(velocities, self.active_joint_names)
            gripper_state, missing_gripper = values_for_names(positions, self.gripper_joint_names)
            missing_active = list(missing_pos) + list(missing_vel)
            if missing_active:
                self._last_failure_reason = "missing_active_joint_names:" + ",".join(sorted(set(missing_active)))
                return None
            if missing_gripper:
                if not self.zero_missing_gripper_state:
                    self._last_failure_reason = "missing_gripper_joint_names:" + ",".join(sorted(set(missing_gripper)))
                    return None
                gripper_state = np.zeros((len(self.gripper_joint_names),), dtype=np.float64)
            joint_state_source = "joint_states"

        target_pose = None
        if model_states is not None:
            target_pose = model_pose_from_states(model_states, self.target_model_name)
        target_state_source = "model_states"
        if target_pose is None:
            if not self.allow_nominal_target_fallback:
                self._last_failure_reason = "target_pose_unavailable"
                return None
            target_pose = self.nominal_target_pose.copy()
            target_state_source = "nominal_fallback"

        parts = [
            base_pose,
            base_velocity,
            active_positions,
            active_velocities,
            gripper_state,
            target_pose,
        ]
        if self.include_progress:
            elapsed = max(0.0, time.monotonic() - self._start_wall_time)
            progress = min(elapsed / max(self.max_duration_sec, 1e-6), 1.0)
            parts.append(np.asarray([progress, 1.0 - progress], dtype=np.float64))
        obs = np.concatenate(parts).astype(np.float32)
        if obs.shape[0] != self.policy.obs_dim:
            self._last_failure_reason = f"obs_dim_mismatch:{obs.shape[0]}!={self.policy.obs_dim}"
            return None
        self._last_failure_reason = ""
        meta = {
            "base_state_source": base_state_source,
            "joint_state_source": joint_state_source,
            "target_state_source": target_state_source,
            "missing_gripper_joint_names": list(missing_gripper),
            "target_model_name": self.target_model_name,
        }
        return obs, meta

    def _publish_status(self, payload: Dict[str, object]) -> None:
        self.status_pub.publish(String(data=json.dumps(payload, sort_keys=True)))

    def _abort(self, reason: str, context: Optional[Dict[str, object]] = None) -> None:
        self._aborted = True
        self._abort_reason = reason
        self._abort_context = context or {}
        self._publish_status(
            {
                "status": "aborted",
                "failure_reason": reason,
                "abort_context": self._abort_context,
                "dry_run_only": True,
                "control_commands_sent": False,
                "gripper_commands_sent": False,
            }
        )

    def _write_summary(self, status: str) -> None:
        self.output_json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "tool": "b8_bc_h8_xyz_rollout_dry_run_node",
            "status": status,
            "dry_run_only": True,
            "control_commands_sent": False,
            "gripper_commands_sent": False,
            "hand_controller_started": False,
            "policy_type": self.policy.policy_type,
            "obs_horizon": self.policy.obs_horizon,
            "action_horizon": self.policy.action_horizon,
            "action_dim": self.policy.action_dim,
            "action_labels": ["dx", "dy", "dz"],
            "max_policy_xyz_component": self.max_policy_xyz_component,
            "max_policy_xyz_norm": self.max_policy_xyz_norm,
            "raw_component_abort": self.raw_component_abort,
            "aborted": self._aborted,
            "abort_reason": self._abort_reason,
            "abort_context": self._abort_context,
            "samples": len(self._history),
            "history": self._history,
        }
        self.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def spin(self) -> None:
        rate = rospy.Rate(self.rate_hz)
        while not rospy.is_shutdown():
            if time.monotonic() - self._start_wall_time > self.max_duration_sec:
                self._publish_status(
                    {
                        "status": "timeout_complete",
                        "dry_run_only": True,
                        "control_commands_sent": False,
                        "gripper_commands_sent": False,
                    }
                )
                self._write_summary("timeout_complete")
                return

            sampled = self._sample_observation()
            if sampled is None:
                self._publish_status(
                    {
                        "status": "waiting_for_observation",
                        "failure_reason": self._last_failure_reason,
                        "dry_run_only": True,
                        "control_commands_sent": False,
                        "gripper_commands_sent": False,
                    }
                )
                rate.sleep()
                continue
            obs, meta = sampled

            if not self._obs_history:
                for _ in range(self.policy.obs_horizon):
                    self._obs_history.append(obs.copy())
            else:
                self._obs_history.append(obs)

            should_replan = (
                self._current_chunk is None
                or self._chunk_index >= self.policy.action_horizon
                or self._steps_since_replan >= self.replan_every_steps
            )
            if should_replan:
                history = np.stack(list(self._obs_history), axis=0)
                start = time.perf_counter()
                chunk, _ = self.policy.predict_action_chunk(history)
                latency_ms = (time.perf_counter() - start) * 1000.0
                self._current_chunk = chunk
                self._chunk_index = 0
                self._steps_since_replan = 0
                if latency_ms > self.max_inference_latency_ms:
                    self._latency_over_limit_count += 1
                else:
                    self._latency_over_limit_count = 0
                if self._latency_over_limit_count >= 2:
                    self._abort(
                        f"inference_latency_over_limit:{latency_ms:.3f}ms",
                        context={"latency_ms": float(latency_ms), **meta},
                    )
                    self._write_summary("aborted")
                    return
            else:
                latency_ms = 0.0

            raw_xyz = np.asarray(self._current_chunk[self._chunk_index], dtype=np.float64)
            if raw_xyz.shape != (3,) or not np.all(np.isfinite(raw_xyz)):
                self._abort(
                    "raw_xyz_invalid",
                    context={
                        "chunk_index": int(self._chunk_index),
                        "raw_action_xyz": raw_xyz.tolist(),
                        **meta,
                    },
                )
                self._write_summary("aborted")
                return
            if float(np.max(np.abs(raw_xyz))) > self.raw_component_abort:
                self._abort(
                    "raw_xyz_component_abort",
                    context={
                        "chunk_index": int(self._chunk_index),
                        "raw_action_xyz": raw_xyz.tolist(),
                        "max_abs_raw_component": float(np.max(np.abs(raw_xyz))),
                        "raw_component_abort": self.raw_component_abort,
                        "latency_ms": float(latency_ms),
                        **meta,
                    },
                )
                self._write_summary("aborted")
                return

            clipped_xyz, clip_meta = _clip_xyz(
                raw_xyz,
                max_component=self.max_policy_xyz_component,
                max_norm=self.max_policy_xyz_norm,
            )
            action_7d = np.concatenate([clipped_xyz, np.zeros((4,), dtype=np.float64)])

            self.action_xyz_pub.publish(_xyz_to_msg(clipped_xyz))
            self.action_7d_pub.publish(action_to_msg(action_7d))

            row = {
                "tick": len(self._history),
                "chunk_index": int(self._chunk_index),
                "latency_ms": float(latency_ms),
                "raw_action_xyz": raw_xyz.tolist(),
                "clipped_action_xyz": clipped_xyz.tolist(),
                "logging_action_7d": action_7d.tolist(),
                "clip": clip_meta,
                **meta,
            }
            self._history.append(row)
            self._publish_status(
                {
                    "status": "published_dry_run_action_label",
                    "dry_run_only": True,
                    "control_commands_sent": False,
                    "gripper_commands_sent": False,
                    **row,
                }
            )
            self._chunk_index += 1
            self._steps_since_replan += 1
            rate.sleep()

        self._write_summary("shutdown")


def main() -> int:
    rospy.init_node("b8_bc_h8_xyz_rollout_dry_run_node")
    node = B8BCH8XYZRolloutDryRunNode()
    node.spin()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
