#!/usr/bin/env python3

import json
from collections import deque
from pathlib import Path
import sys
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import rospkg
import rospy
import tf
import yaml
from gazebo_msgs.msg import ModelStates
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray, MultiArrayDimension, String


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from b8_bc_h8_xyz_base_relative_rollout_dry_run_node import (  # noqa: E402
    _clip_xyz,
    _position_in_base_frame,
)
from learning.eval.policy_runtime import RuntimePolicy, choose_device  # noqa: E402
from rexrov_single_oberon7_fm_dp.action_converter import action_to_msg  # noqa: E402
from rexrov_single_oberon7_fm_dp.arm_command_converter import ArmEEDeltaCommandConverter  # noqa: E402
from rexrov_single_oberon7_fm_dp.ros_interface import (  # noqa: E402
    joint_state_maps,
    model_pose_from_states,
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
    msg = Float64MultiArray()
    msg.layout.dim.append(MultiArrayDimension(label="action_xyz", size=3, stride=3))
    msg.data = values.tolist()
    return msg


class B8BCH8XYZBaseRelativeExecutionSmokeNode:
    """Dedicated tiny active-left arm-only execution smoke adapter.

    This node is intentionally separate from the dry-run adapter. It publishes
    active-left arm commands only when both execute_actions and the explicit
    acknowledgement flag are true. It never publishes gripper commands.
    """

    def __init__(self) -> None:
        package_path = _package_path()
        config_path = Path(
            rospy.get_param(
                "~config",
                str(package_path / "config" / "b8_bc_h8_xyz_base_relative_execution_smoke.yaml"),
            )
        ).expanduser()
        self.cfg = _load_yaml(config_path)
        self.obs_cfg = self.cfg.get("observation", {}) or {}
        self.runtime_cfg = self.cfg.get("runtime", {}) or {}
        self.safety_cfg = self.cfg.get("safety", {}) or {}
        self.output_cfg = self.cfg.get("output", {}) or {}

        self.execute_actions = bool(rospy.get_param("~execute_actions", False))
        self.ack = bool(rospy.get_param("~i_understand_this_publishes_arm_commands", False))
        if self.execute_actions and not self.ack:
            raise RuntimeError(
                "execute_actions=true requires i_understand_this_publishes_arm_commands=true"
            )

        joints_cfg = _load_yaml(package_path / "config" / "active_joints_left_arm.yaml")
        self.active_joint_names = list(joints_cfg["active_joint_names"])

        checkpoint = str(rospy.get_param("~checkpoint", "")).strip()
        if not checkpoint:
            checkpoint = str(self.runtime_cfg["checkpoint"])
        device = choose_device(str(rospy.get_param("~device", self.cfg.get("device", "auto"))))
        self.policy_type_param = str(rospy.get_param("~policy_type", "auto"))
        self.num_inference_steps = int(rospy.get_param("~num_inference_steps", 50))
        self.ode_steps = int(rospy.get_param("~ode_steps", 50))
        self.method_name = str(rospy.get_param("~method_name", "bc"))
        self.policy = RuntimePolicy.from_checkpoint(
            checkpoint,
            device=device,
            policy_type=self.policy_type_param,
        )
        if self.policy.obs_dim != 23 or self.policy.action_dim != 3 or self.policy.action_horizon != 8:
            raise RuntimeError(
                "expected base-relative BC h8 xyz checkpoint with obs_dim=23, "
                f"action_dim=3, action_horizon=8; got obs_dim={self.policy.obs_dim}, "
                f"action_dim={self.policy.action_dim}, action_horizon={self.policy.action_horizon}"
            )

        self.rate_hz = float(rospy.get_param("~rate_hz", self.runtime_cfg.get("rate_hz", 3.0)))
        self.max_duration_sec = float(
            rospy.get_param("~max_duration_sec", self.runtime_cfg.get("max_duration_sec", 7.2))
        )
        self.max_control_ticks = int(
            rospy.get_param("~max_control_ticks", self.runtime_cfg.get("max_control_ticks", 3))
        )
        self.early_stop_on_reaching = bool(rospy.get_param("~early_stop_on_reaching", False))
        self.early_stop_distance = float(rospy.get_param("~early_stop_distance", 0.095))
        self.early_stop_min_control_ticks = int(rospy.get_param("~early_stop_min_control_ticks", 1))
        self.early_stop_min_distance_reduction = float(
            rospy.get_param("~early_stop_min_distance_reduction", 0.0)
        )
        self.early_stop_initial_distance_override = float(
            rospy.get_param("~early_stop_initial_distance_override", -1.0)
        )
        self.replan_every_steps = int(
            rospy.get_param("~replan_every_steps", self.runtime_cfg.get("replan_every_steps", 1))
        )
        self.max_policy_xyz_component = float(
            rospy.get_param("~max_policy_xyz_component", self.safety_cfg["max_policy_xyz_component"])
        )
        self.max_policy_xyz_norm = float(
            rospy.get_param("~max_policy_xyz_norm", self.safety_cfg["max_policy_xyz_norm"])
        )
        self.raw_component_abort = float(
            rospy.get_param(
                "~raw_component_abort",
                self.safety_cfg["absolute_stop_if_raw_component_exceeds"],
            )
        )
        self.max_abs_base_relative_position = float(
            rospy.get_param(
                "~max_abs_base_relative_position",
                self.safety_cfg.get("max_abs_base_relative_position", 5.0),
            )
        )
        self.max_joint_delta = float(self.safety_cfg["max_joint_delta_per_command_rad"])
        self.time_from_start_sec = float(self.safety_cfg["time_from_start_sec"])

        self.base_odom_topic = self.obs_cfg.get("base_odom_topic", "/rexrov/pose_gt")
        self.joint_states_topic = self.obs_cfg.get("joint_states_topic", "/joint_states")
        self.model_states_topic = self.obs_cfg.get("model_states_topic", "/gazebo/model_states")
        self.target_model_name = self.obs_cfg.get("target_model_name", "cylinder_target_gate_probe")
        self.base_frame = self.obs_cfg.get("base_frame", "rexrov/base_link")
        self.eef_frame = self.obs_cfg.get("eef_frame", "oberon7_l/end_effector")
        self.planning_frame = self.obs_cfg.get("planning_frame", "world")
        self.arm_command_topic = self.obs_cfg.get("arm_command_topic", "/oberon7/arm_position_l/command")
        self.compute_ik_service = self.obs_cfg.get("compute_ik_service", "/compute_ik")
        self.arm_group = self.obs_cfg.get("arm_group", "arm_l")

        self.action_xyz_pub = rospy.Publisher(
            self.output_cfg.get(
                "action_xyz_topic",
                "/rexrov_single_oberon7_fm_dp/policy/bc_h8_xyz_base_relative/action_xyz_execution_smoke",
            ),
            Float64MultiArray,
            queue_size=10,
        )
        self.action_7d_pub = rospy.Publisher(
            self.output_cfg.get(
                "action_7d_topic",
                "/rexrov_single_oberon7_fm_dp/policy/bc_h8_xyz_base_relative/action_7d_execution_smoke",
            ),
            Float64MultiArray,
            queue_size=10,
        )
        self.status_pub = rospy.Publisher(
            self.output_cfg.get(
                "status_topic",
                "/rexrov_single_oberon7_fm_dp/policy/bc_h8_xyz_base_relative/execution_smoke_status",
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
                            / "outputs/logs/b8_rollout_planning"
                            / "bc_h8_xyz_base_relative_execution_smoke_latest.json"
                        ),
                    ),
                )
            )
        ).expanduser()

        self.tf_listener = tf.TransformListener()
        self.converter = ArmEEDeltaCommandConverter(
            joint_states_topic=self.joint_states_topic,
            arm_command_topic=self.arm_command_topic,
            compute_ik_service=self.compute_ik_service,
            arm_group=self.arm_group,
            eef_link=self.eef_frame,
            planning_frame=self.planning_frame,
            action_frame="base_link",
            base_odom_topic=self.base_odom_topic,
            base_link_frame=self.base_frame,
            active_joint_names=self.active_joint_names,
            max_linear_step=self.max_policy_xyz_component,
            max_angular_step=0.0,
            max_joint_delta=self.max_joint_delta,
            time_from_start_sec=self.time_from_start_sec,
        )
        self.obs_history = deque(maxlen=self.policy.obs_horizon)
        self.current_chunk: Optional[np.ndarray] = None
        self.chunk_index = 0
        self.steps_since_replan = self.replan_every_steps
        self.start_wall_time = time.monotonic()
        self.history: List[Dict[str, object]] = []
        self.aborted = False
        self.abort_reason = ""
        self.control_commands_sent = False
        self.initial_distance_to_target: Optional[float] = (
            self.early_stop_initial_distance_override
            if self.early_stop_initial_distance_override > 0.0
            else None
        )

        rospy.loginfo(
            "b8_bc_h8_xyz_base_relative_execution_smoke loaded checkpoint=%s "
            "execute_actions=%s max_control_ticks=%d gripper_enabled=false",
            checkpoint,
            self.execute_actions,
            self.max_control_ticks,
        )

    def _lookup_eef_position_base_frame(self) -> np.ndarray:
        translation, _ = self.tf_listener.lookupTransform(self.base_frame, self.eef_frame, rospy.Time(0))
        return np.asarray(translation, dtype=np.float64)

    def _sample_observation(self) -> Tuple[np.ndarray, Dict[str, object]]:
        base_odom = rospy.wait_for_message(self.base_odom_topic, Odometry, timeout=0.5)
        joint_state = rospy.wait_for_message(self.joint_states_topic, JointState, timeout=0.5)
        model_states = rospy.wait_for_message(self.model_states_topic, ModelStates, timeout=0.5)

        base_pose, _ = odom_to_pose_velocity(base_odom)
        positions, velocities, _ = joint_state_maps(joint_state)
        active_positions, missing_pos = values_for_names(positions, self.active_joint_names)
        active_velocities, missing_vel = values_for_names(velocities, self.active_joint_names)
        missing_active = list(missing_pos) + list(missing_vel)
        if missing_active:
            raise RuntimeError("missing_active_joint_names:" + ",".join(sorted(set(missing_active))))

        eef_position_base = self._lookup_eef_position_base_frame()
        target_pose = model_pose_from_states(model_states, self.target_model_name)
        if target_pose is None:
            raise RuntimeError(f"target model missing: {self.target_model_name}")
        target_position_base = _position_in_base_frame(target_pose[:3], base_pose)
        target_to_eef_base = target_position_base - eef_position_base
        base_relative_values = np.concatenate([eef_position_base, target_position_base, target_to_eef_base])
        if not np.all(np.isfinite(base_relative_values)):
            raise RuntimeError("base_relative_geometry_nonfinite")
        if float(np.max(np.abs(base_relative_values))) > self.max_abs_base_relative_position:
            raise RuntimeError("base_relative_geometry_out_of_bounds")

        elapsed = max(0.0, time.monotonic() - self.start_wall_time)
        progress = min(elapsed / max(self.max_duration_sec, 1e-6), 1.0)
        obs = np.concatenate(
            [
                active_positions,
                active_velocities,
                eef_position_base,
                target_position_base,
                target_to_eef_base,
                np.asarray([progress, 1.0 - progress], dtype=np.float64),
            ]
        ).astype(np.float32)
        if obs.shape[0] != self.policy.obs_dim:
            raise RuntimeError(f"obs_dim_mismatch:{obs.shape[0]}!={self.policy.obs_dim}")
        meta = {
            "eef_position_base_frame": eef_position_base.tolist(),
            "target_position_base_frame": target_position_base.tolist(),
            "target_to_eef_base_frame": target_to_eef_base.tolist(),
            "distance_to_target": float(np.linalg.norm(target_to_eef_base)),
        }
        return obs, meta

    def _publish_status(self, payload: Dict[str, object]) -> None:
        self.status_pub.publish(String(data=json.dumps(payload, sort_keys=True)))

    def _abort(self, reason: str, context: Dict[str, object]) -> None:
        self.aborted = True
        self.abort_reason = reason
        self._publish_status(
            {
                "status": "aborted",
                "failure_reason": reason,
                "control_commands_sent": self.control_commands_sent,
                "gripper_commands_sent": False,
                **context,
            }
        )

    def _write_summary(self, status: str) -> None:
        self.output_json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "tool": "b8_bc_h8_xyz_base_relative_execution_smoke_node",
            "status": status,
            "execute_actions": self.execute_actions,
            "control_commands_sent": self.control_commands_sent,
            "gripper_commands_sent": False,
            "hand_controller_started": False,
            "method_name": self.method_name,
            "policy_type": self.policy.policy_type,
            "policy_type_param": self.policy_type_param,
            "num_inference_steps": self.num_inference_steps,
            "ode_steps": self.ode_steps,
            "obs_design": "base_relative_arm_only_no_gripper_no_absolute_target_pose",
            "action_labels": ["dx", "dy", "dz"],
            "action_frame": "base_link",
            "max_control_ticks": self.max_control_ticks,
            "early_stop_on_reaching": self.early_stop_on_reaching,
            "early_stop_distance": self.early_stop_distance,
            "early_stop_min_control_ticks": self.early_stop_min_control_ticks,
            "early_stop_min_distance_reduction": self.early_stop_min_distance_reduction,
            "early_stop_initial_distance_override": self.early_stop_initial_distance_override,
            "initial_distance_to_target": self.initial_distance_to_target,
            "max_policy_xyz_component": self.max_policy_xyz_component,
            "max_policy_xyz_norm": self.max_policy_xyz_norm,
            "raw_component_abort": self.raw_component_abort,
            "max_joint_delta": self.max_joint_delta,
            "aborted": self.aborted,
            "abort_reason": self.abort_reason,
            "samples": len(self.history),
            "history": self.history,
        }
        self.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def spin(self) -> None:
        rate = rospy.Rate(self.rate_hz)
        executed_ticks = 0
        while not rospy.is_shutdown():
            if time.monotonic() - self.start_wall_time > self.max_duration_sec:
                self._write_summary("timeout_complete")
                return
            if self.max_control_ticks > 0 and executed_ticks >= self.max_control_ticks:
                self._write_summary("max_control_ticks_complete")
                return

            try:
                obs, meta = self._sample_observation()
            except Exception as exc:
                self._abort("observation_unavailable", {"error": str(exc)})
                self._write_summary("aborted")
                return
            if self.initial_distance_to_target is None:
                self.initial_distance_to_target = float(meta["distance_to_target"])
            distance_reduction = self.initial_distance_to_target - float(meta["distance_to_target"])

            if (
                self.execute_actions
                and self.early_stop_on_reaching
                and executed_ticks >= self.early_stop_min_control_ticks
                and float(meta["distance_to_target"]) <= self.early_stop_distance
                and distance_reduction >= self.early_stop_min_distance_reduction
            ):
                terminal_row = {
                    "tick": len(self.history),
                    "execution_status": "early_stop_observation",
                    "control_commands_sent": self.control_commands_sent,
                    "gripper_commands_sent": False,
                    "executed_ticks": executed_ticks,
                    "distance_reduction_from_initial_distance": float(distance_reduction),
                    "early_stop_distance": self.early_stop_distance,
                    "early_stop_min_distance_reduction": self.early_stop_min_distance_reduction,
                    **meta,
                }
                self.history.append(terminal_row)
                self._publish_status(
                    {
                        "status": "early_reaching_stop",
                        "distance_to_target": float(meta["distance_to_target"]),
                        "distance_reduction_from_initial_distance": float(distance_reduction),
                        "early_stop_distance": self.early_stop_distance,
                        "early_stop_min_distance_reduction": self.early_stop_min_distance_reduction,
                        "executed_ticks": executed_ticks,
                        "control_commands_sent": self.control_commands_sent,
                        "gripper_commands_sent": False,
                        **meta,
                    }
                )
                self._write_summary("early_reaching_stop")
                return

            if not self.obs_history:
                for _ in range(self.policy.obs_horizon):
                    self.obs_history.append(obs.copy())
            else:
                self.obs_history.append(obs)

            should_replan = (
                self.current_chunk is None
                or self.chunk_index >= self.policy.action_horizon
                or self.steps_since_replan >= self.replan_every_steps
            )
            if should_replan:
                start = time.perf_counter()
                self.current_chunk, _ = self.policy.predict_action_chunk(
                    np.stack(list(self.obs_history), axis=0),
                    num_inference_steps=self.num_inference_steps,
                    ode_steps=self.ode_steps,
                )
                latency_ms = (time.perf_counter() - start) * 1000.0
                self.chunk_index = 0
                self.steps_since_replan = 0
            else:
                latency_ms = 0.0

            raw_xyz = np.asarray(self.current_chunk[self.chunk_index], dtype=np.float64)
            if raw_xyz.shape != (3,) or not np.all(np.isfinite(raw_xyz)):
                self._abort("raw_xyz_invalid", {"raw_action_xyz": raw_xyz.tolist(), **meta})
                self._write_summary("aborted")
                return
            max_abs_raw = float(np.max(np.abs(raw_xyz)))
            if max_abs_raw > self.raw_component_abort:
                self._abort(
                    "raw_xyz_component_abort",
                    {
                        "raw_action_xyz": raw_xyz.tolist(),
                        "max_abs_raw_component": max_abs_raw,
                        "raw_component_abort": self.raw_component_abort,
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
            try:
                if self.execute_actions:
                    conversion = self.converter.execute(action_7d)
                    self.control_commands_sent = True
                    execution_status = "published_arm_command"
                    executed_ticks += 1
                else:
                    conversion = self.converter.convert(action_7d)
                    execution_status = "preview_only"
            except Exception as exc:
                self._abort(
                    "arm_command_conversion_or_execution_failed",
                    {
                        "error": str(exc),
                        "raw_action_xyz": raw_xyz.tolist(),
                        "clipped_action_xyz": clipped_xyz.tolist(),
                        **meta,
                    },
                )
                self._write_summary("aborted")
                return

            self.action_xyz_pub.publish(_xyz_to_msg(clipped_xyz))
            self.action_7d_pub.publish(action_to_msg(action_7d))
            row = {
                "tick": len(self.history),
                "execution_status": execution_status,
                "control_commands_sent": self.control_commands_sent,
                "gripper_commands_sent": False,
                "latency_ms": float(latency_ms),
                "raw_action_xyz": raw_xyz.tolist(),
                "clipped_action_xyz": clipped_xyz.tolist(),
                "logging_action_7d": action_7d.tolist(),
                "clip": clip_meta,
                "active_joint_names": conversion.active_joint_names,
                "current_eef_xyz": conversion.current_eef_xyz,
                "target_eef_xyz": conversion.target_eef_xyz,
                "clipped_xyz_planning_frame": conversion.clipped_xyz_planning_frame,
                "raw_joint_delta": conversion.raw_joint_delta,
                "clipped_joint_delta": conversion.clipped_joint_delta,
                "command_positions": conversion.command_positions,
                **meta,
            }
            self.history.append(row)
            self._publish_status({"status": execution_status, **row})
            self.chunk_index += 1
            self.steps_since_replan += 1
            rate.sleep()

        self._write_summary("shutdown")


def main() -> int:
    rospy.init_node("b8_bc_h8_xyz_base_relative_execution_smoke_node")
    node = B8BCH8XYZBaseRelativeExecutionSmokeNode()
    node.spin()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
