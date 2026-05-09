#!/usr/bin/env python3

import json
from collections import deque
from pathlib import Path
import sys
import threading
import time
from typing import Dict, Optional

import numpy as np
import rospkg
import rospy
import yaml
from gazebo_msgs.msg import ModelStates
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray, String


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


def _clip_action(action: np.ndarray, safety_cfg: Dict) -> np.ndarray:
    clipped = np.asarray(action, dtype=np.float64).copy()
    clipped[:3] = np.clip(
        clipped[:3],
        -float(safety_cfg.get("max_linear_delta", 0.03)),
        float(safety_cfg.get("max_linear_delta", 0.03)),
    )
    clipped[3:6] = np.clip(
        clipped[3:6],
        -float(safety_cfg.get("max_angular_delta", 0.15)),
        float(safety_cfg.get("max_angular_delta", 0.15)),
    )
    clipped[6] = np.clip(
        clipped[6],
        float(safety_cfg.get("min_gripper_cmd", 0.0)),
        float(safety_cfg.get("max_gripper_cmd", 1.0)),
    )
    return clipped


class RolloutPolicyNode:
    def __init__(self) -> None:
        package_path = _package_path()
        config_path = Path(
            rospy.get_param("~config", str(package_path / "config" / "eval_rollout.yaml"))
        ).expanduser()
        self.cfg = _load_yaml(config_path)
        self.obs_cfg = self.cfg.get("observation", {}) or {}
        self.rollout_cfg = self.cfg.get("rollout", {}) or {}
        self.safety_cfg = self.cfg.get("safety", {}) or {}

        joints_cfg = _load_yaml(package_path / "config" / "active_joints_left_arm.yaml")
        self.active_joint_names = list(joints_cfg["active_joint_names"])
        self.gripper_joint_names = list(joints_cfg["gripper_joint_names"])

        self.policy_name = rospy.get_param("~policy_name", "bc")
        policy_cfg = (self.cfg.get("policies", {}) or {}).get(self.policy_name, {})
        if not policy_cfg:
            raise RuntimeError(f"policy_name {self.policy_name!r} is not configured")
        self.policy_type = rospy.get_param("~policy_type", policy_cfg.get("policy_type", "auto"))
        checkpoint = rospy.get_param("~checkpoint", policy_cfg.get("checkpoint", ""))
        if not checkpoint:
            raise RuntimeError("checkpoint path is required")
        device = choose_device(str(rospy.get_param("~device", self.cfg.get("device", "auto"))))
        self.policy = RuntimePolicy.from_checkpoint(checkpoint, device=device, policy_type=self.policy_type)
        self.policy_cfg = policy_cfg

        self.rate_hz = float(rospy.get_param("~rate_hz", self.rollout_cfg.get("rate_hz", 5.0)))
        self.max_duration_sec = float(
            rospy.get_param("~max_duration_sec", self.rollout_cfg.get("max_duration_sec", 20.0))
        )
        self.replan_every_steps = int(
            rospy.get_param("~replan_every_steps", self.rollout_cfg.get("replan_every_steps", 4))
        )
        self.execute_steps_per_chunk = int(
            rospy.get_param("~execute_steps_per_chunk", self.rollout_cfg.get("execute_steps_per_chunk", 4))
        )
        self.execute_actions = bool(
            rospy.get_param("~execute_actions", self.rollout_cfg.get("execute_actions", False))
        )
        if self.execute_actions:
            rospy.logwarn(
                "execute_actions=true requested, but Stage 10 has no confirmed left-arm "
                "controller mapping. The node will still publish only action labels."
            )
            self.execute_actions = False

        self.base_odom_topic = self.obs_cfg.get("base_odom_topic", "/rexrov/pose_gt")
        self.joint_states_topic = self.obs_cfg.get("joint_states_topic", "/joint_states")
        self.model_states_topic = self.obs_cfg.get("model_states_topic", "/gazebo/model_states")
        self.target_model_name = self.obs_cfg.get("target_model_name", "cylinder_target")
        self.base_model_name = self.obs_cfg.get("base_state_fallback_model_name", "rexrov")
        self.allow_nominal_state_fallback = bool(self.obs_cfg.get("allow_nominal_state_fallback", False))
        self.allow_nominal_target_fallback = bool(self.obs_cfg.get("allow_nominal_target_fallback", True))
        self.nominal_base_pose = np.asarray(
            self.obs_cfg.get("nominal_base_pose", [2.0, 2.0, -40.0, 0.0, 0.0, 0.0, 1.0]),
            dtype=np.float64,
        )
        self.nominal_target_pose = np.asarray(
            self.obs_cfg.get("nominal_target_pose", [2.6, 2.0, -40.0, 0.0, 0.0, 0.0, 1.0]),
            dtype=np.float64,
        )
        self.include_progress = bool(self.obs_cfg.get("include_progress", True))

        action_topic = rospy.get_param(
            "~action_output_topic",
            self.rollout_cfg.get("action_output_topic", "/rexrov_single_oberon7_fm_dp/policy/action_ee_delta"),
        )
        status_topic = rospy.get_param(
            "~status_topic",
            self.rollout_cfg.get("status_topic", "/rexrov_single_oberon7_fm_dp/policy/status"),
        )
        self.action_pub = rospy.Publisher(action_topic, Float64MultiArray, queue_size=10)
        self.status_pub = rospy.Publisher(status_topic, String, queue_size=10)

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

        rospy.Subscriber(self.base_odom_topic, Odometry, self._base_odom_cb, queue_size=1)
        rospy.Subscriber(self.joint_states_topic, JointState, self._joint_state_cb, queue_size=1)
        rospy.Subscriber(self.model_states_topic, ModelStates, self._model_states_cb, queue_size=1)

        rospy.loginfo(
            "rollout_policy_node loaded policy=%s type=%s obs_horizon=%d action_horizon=%d execute_actions=%s",
            self.policy_name,
            self.policy.policy_type,
            self.policy.obs_horizon,
            self.policy.action_horizon,
            self.execute_actions,
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

    def _sample_observation(self) -> Optional[np.ndarray]:
        with self._lock:
            base_odom = self._base_odom
            joint_state = self._joint_state
            model_states = self._model_states

        if base_odom is not None:
            base_pose, base_velocity = odom_to_pose_velocity(base_odom)
        elif model_states is not None:
            base_pose = model_pose_from_states(model_states, self.base_model_name)
            base_velocity = model_twist_from_states(model_states, self.base_model_name)
            if base_pose is None or base_velocity is None:
                if not self.allow_nominal_state_fallback:
                    self._last_failure_reason = "base_state_unavailable"
                    return None
                base_pose = self.nominal_base_pose.copy()
                base_velocity = np.zeros((6,), dtype=np.float64)
        elif self.allow_nominal_state_fallback:
            base_pose = self.nominal_base_pose.copy()
            base_velocity = np.zeros((6,), dtype=np.float64)
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
        else:
            positions, velocities, _ = joint_state_maps(joint_state)
            active_positions, missing_pos = values_for_names(positions, self.active_joint_names)
            active_velocities, missing_vel = values_for_names(velocities, self.active_joint_names)
            gripper_state, missing_gripper = values_for_names(positions, self.gripper_joint_names)
            missing = list(missing_pos) + list(missing_vel) + list(missing_gripper)
            if missing:
                self._last_failure_reason = "missing_joint_names:" + ",".join(sorted(set(missing)))
                return None

        target_pose = None
        if model_states is not None:
            target_pose = model_pose_from_states(model_states, self.target_model_name)
        if target_pose is None:
            if not self.allow_nominal_target_fallback:
                self._last_failure_reason = "target_pose_unavailable"
                return None
            target_pose = self.nominal_target_pose.copy()

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
        return obs

    def _publish_status(self, payload: Dict[str, object]) -> None:
        self.status_pub.publish(String(data=json.dumps(payload, sort_keys=True)))

    def spin(self) -> None:
        rate = rospy.Rate(self.rate_hz)
        while not rospy.is_shutdown():
            if time.monotonic() - self._start_wall_time > self.max_duration_sec:
                self._publish_status(
                    {
                        "policy": self.policy_name,
                        "policy_type": self.policy.policy_type,
                        "status": "timeout",
                        "execute_actions": self.execute_actions,
                    }
                )
                return

            obs = self._sample_observation()
            if obs is None:
                self._publish_status(
                    {
                        "policy": self.policy_name,
                        "policy_type": self.policy.policy_type,
                        "status": "waiting_for_observation",
                        "failure_reason": self._last_failure_reason,
                    }
                )
                rate.sleep()
                continue

            if not self._obs_history:
                for _ in range(self.policy.obs_horizon):
                    self._obs_history.append(obs.copy())
            else:
                self._obs_history.append(obs)

            should_replan = (
                self._current_chunk is None
                or self._chunk_index >= min(self.execute_steps_per_chunk, self.policy.action_horizon)
                or self._steps_since_replan >= self.replan_every_steps
            )
            if should_replan:
                history = np.stack(list(self._obs_history), axis=0)
                start = time.perf_counter()
                chunk, _ = self.policy.predict_action_chunk(
                    history,
                    num_inference_steps=self.policy_cfg.get("num_inference_steps"),
                    ode_steps=self.policy_cfg.get("ode_steps"),
                )
                latency_ms = (time.perf_counter() - start) * 1000.0
                self._current_chunk = chunk
                self._chunk_index = 0
                self._steps_since_replan = 0
            else:
                latency_ms = 0.0

            action = _clip_action(self._current_chunk[self._chunk_index], self.safety_cfg)
            self.action_pub.publish(action_to_msg(action))
            self._publish_status(
                {
                    "policy": self.policy_name,
                    "policy_type": self.policy.policy_type,
                    "status": "published_action_label",
                    "execute_actions": self.execute_actions,
                    "chunk_index": int(self._chunk_index),
                    "latency_ms": float(latency_ms),
                    "action": action.tolist(),
                    "failure_reason": "controller_mapping_unconfirmed" if not self.execute_actions else "",
                }
            )
            self._chunk_index += 1
            self._steps_since_replan += 1
            rate.sleep()


def main() -> int:
    rospy.init_node("rollout_policy_node")
    node = RolloutPolicyNode()
    node.spin()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
