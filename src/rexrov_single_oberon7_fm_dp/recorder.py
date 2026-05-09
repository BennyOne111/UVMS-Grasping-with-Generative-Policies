import datetime as _dt
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import rospkg
import rospy
import tf
import yaml
from gazebo_msgs.msg import ModelStates
from geometry_msgs.msg import Wrench, WrenchStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, Float64MultiArray

from rexrov_single_oberon7_fm_dp.action_converter import msg_to_action
from rexrov_single_oberon7_fm_dp.dataset_writer import save_episode_npz, stack_samples
from rexrov_single_oberon7_fm_dp.ros_interface import (
    joint_state_maps,
    model_pose_from_states,
    model_twist_from_states,
    nan_action,
    nan_pose,
    nan_twist,
    odom_to_pose_velocity,
    values_for_names,
    wrench_stamped_to_array,
    wrench_to_array,
)


def _load_yaml(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def load_default_configs() -> Dict[str, Dict]:
    package_path = Path(rospkg.RosPack().get_path("rexrov_single_oberon7_fm_dp"))
    config_dir = package_path / "config"
    return {
        "data_collection": _load_yaml(config_dir / "data_collection.yaml"),
        "topics": _load_yaml(config_dir / "topics.yaml"),
        "task": _load_yaml(config_dir / "task_grasp.yaml"),
        "joints": _load_yaml(config_dir / "active_joints_left_arm.yaml"),
    }


class EpisodeRecorder:
    def __init__(self) -> None:
        configs = load_default_configs()
        self.data_cfg = configs["data_collection"]
        self.topics_cfg = configs["topics"]
        self.task_cfg = configs["task"]
        self.joints_cfg = configs["joints"]

        self.output_dir = rospy.get_param("~output_dir", self.data_cfg["output_dir"])
        self.rate_hz = float(rospy.get_param("~rate_hz", self.data_cfg["rate_hz"]))
        self.max_duration_sec = float(
            rospy.get_param("~max_duration_sec", self.data_cfg["max_duration_sec"])
        )
        self.episode_id = rospy.get_param("~episode_id", "")
        if not self.episode_id:
            prefix = str(self.data_cfg.get("episode_id_prefix", "episode"))
            stamp = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            self.episode_id = f"{prefix}_{stamp}_{uuid.uuid4().hex[:8]}"

        self.success = bool(rospy.get_param("~success", False))
        self.require_target = bool(rospy.get_param("~require_target", False))
        self.require_action = bool(rospy.get_param("~require_action", False))
        self.allow_nominal_state_fallback = bool(
            rospy.get_param("~allow_nominal_state_fallback", False)
        )
        self.state_fallback_wait_sec = float(rospy.get_param("~state_fallback_wait_sec", 30.0))
        self.min_samples = int(rospy.get_param("~min_samples", 2))
        self.controller_type = rospy.get_param("~controller_type", "unknown")
        self.task_type = rospy.get_param(
            "~task_type", self.data_cfg.get("task_type", "arm_only_reaching")
        )
        self.success_metric = rospy.get_param(
            "~success_metric", self.data_cfg.get("success_metric", "reaching_success")
        )
        self.gripper_enabled = bool(
            rospy.get_param("~gripper_enabled", self.data_cfg.get("gripper_enabled", False))
        )
        self.is_grasp_dataset = bool(
            rospy.get_param("~is_grasp_dataset", self.data_cfg.get("is_grasp_dataset", False))
        )
        self.max_linear_step = float(rospy.get_param("~max_linear_step", float("nan")))
        self.max_joint_delta = float(rospy.get_param("~max_joint_delta", float("nan")))
        self.target_directed_action_frame = rospy.get_param(
            "~target_directed_action_frame", "unknown"
        )
        self.arm_action_frame = rospy.get_param("~arm_action_frame", "unknown")
        self.state_sequence = rospy.get_param("~state_sequence", "unknown")

        self.base_odom_topic = rospy.get_param(
            "~base_odom_topic", self.topics_cfg["base_odom_topic"]
        )
        self.base_state_fallback_model_name = rospy.get_param(
            "~base_state_fallback_model_name",
            self.topics_cfg.get("base_state_fallback_model_name", "rexrov"),
        )
        self.prefer_model_states_base_pose = bool(
            rospy.get_param("~prefer_model_states_base_pose", False)
        )
        self.joint_states_topic = rospy.get_param(
            "~joint_states_topic", self.topics_cfg["joint_states_topic"]
        )
        self.model_states_topic = rospy.get_param(
            "~model_states_topic", self.topics_cfg["model_states_topic"]
        )
        self.base_wrench_topic = rospy.get_param(
            "~base_wrench_topic", self.topics_cfg["base_wrench_topic"]
        )
        self.base_wrench_stamped_topic = rospy.get_param(
            "~base_wrench_stamped_topic",
            self.topics_cfg.get("base_wrench_stamped_topic", ""),
        )
        self.target_model_name = rospy.get_param(
            "~target_model_name", self.task_cfg["target_model_name"]
        )
        moveit_cfg = self.topics_cfg.get("moveit", {})
        self.eef_link = rospy.get_param(
            "~eef_link",
            self.joints_cfg.get("eef_link", moveit_cfg.get("eef_link", "oberon7_l/end_effector")),
        )
        self.eef_pose_reference_frame = rospy.get_param(
            "~eef_pose_reference_frame", moveit_cfg.get("planning_frame", "world")
        )
        self.base_link_frame = rospy.get_param("~base_link_frame", "rexrov/base_link")
        self.enable_tf_eef_pose = bool(rospy.get_param("~enable_tf_eef_pose", True))
        self.require_eef_pose = bool(rospy.get_param("~require_eef_pose", False))
        self.tf_eef_wait_sec = float(rospy.get_param("~tf_eef_wait_sec", 2.0))
        self.tf_listener = tf.TransformListener() if self.enable_tf_eef_pose else None
        self.use_nominal_target_when_unavailable = bool(
            rospy.get_param("~use_nominal_target_when_unavailable", False)
        )
        nominal_cfg = self.task_cfg.get("nominal_target_pose", {})
        nominal_xyz = list(nominal_cfg.get("xyz", [2.6, 2.0, -40.0]))
        nominal_xyz[0] = float(rospy.get_param("~target_x", nominal_xyz[0]))
        nominal_xyz[1] = float(rospy.get_param("~target_y", nominal_xyz[1]))
        nominal_xyz[2] = float(rospy.get_param("~target_z", nominal_xyz[2]))
        nominal_quat = list(nominal_cfg.get("quaternion_xyzw", [0.0, 0.0, 0.0, 1.0]))
        self.nominal_target_pose = np.asarray(nominal_xyz + nominal_quat, dtype=np.float64)
        self.nominal_base_pose = np.asarray([2.0, 2.0, -40.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float64)
        self.nominal_base_velocity = np.zeros((6,), dtype=np.float64)
        self.expert_action_topic = rospy.get_param(
            "~expert_action_topic",
            self.topics_cfg.get(
                "expert_action_topic", "/rexrov_single_oberon7_fm_dp/expert/action_ee_delta"
            ),
        )
        self.expert_success_topic = rospy.get_param(
            "~expert_success_topic",
            self.topics_cfg.get(
                "expert_success_topic", "/rexrov_single_oberon7_fm_dp/expert/success"
            ),
        )

        self.active_joint_names = list(self.joints_cfg["active_joint_names"])
        self.gripper_joint_names = list(self.joints_cfg["gripper_joint_names"])
        self.inactive_joint_names = list(self.joints_cfg.get("inactive_joint_names", []))

        self._lock = threading.Lock()
        self._base_odom: Optional[Odometry] = None
        self._joint_state: Optional[JointState] = None
        self._model_states: Optional[ModelStates] = None
        self._base_wrench: Optional[np.ndarray] = None
        self._expert_action: Optional[np.ndarray] = None
        self._expert_success: Optional[bool] = None
        self._samples: List[Dict[str, np.ndarray]] = []
        self._missing_joint_names = set()

        rospy.Subscriber(self.base_odom_topic, Odometry, self._base_odom_cb, queue_size=1)
        rospy.Subscriber(self.joint_states_topic, JointState, self._joint_state_cb, queue_size=1)
        rospy.Subscriber(self.model_states_topic, ModelStates, self._model_states_cb, queue_size=1)
        if self.base_wrench_topic:
            rospy.Subscriber(self.base_wrench_topic, Wrench, self._base_wrench_cb, queue_size=10)
        if self.base_wrench_stamped_topic:
            rospy.Subscriber(
                self.base_wrench_stamped_topic,
                WrenchStamped,
                self._base_wrench_stamped_cb,
                queue_size=10,
            )
        if self.expert_action_topic:
            rospy.Subscriber(
                self.expert_action_topic,
                Float64MultiArray,
                self._expert_action_cb,
                queue_size=10,
            )
        if self.expert_success_topic:
            rospy.Subscriber(
                self.expert_success_topic,
                Bool,
                self._expert_success_cb,
                queue_size=10,
            )

    def _lookup_eef_pose(self, base_pose: Optional[np.ndarray] = None) -> tuple:
        if self.tf_listener is None:
            return nan_pose(), "disabled"
        try:
            translation, quaternion = self.tf_listener.lookupTransform(
                self.eef_pose_reference_frame,
                self.eef_link,
                rospy.Time(0),
            )
        except (
            tf.Exception,
            tf.LookupException,
            tf.ConnectivityException,
            tf.ExtrapolationException,
        ):
            if self.eef_pose_reference_frame != "world" or base_pose is None:
                return nan_pose(), "unavailable"
            return self._lookup_world_eef_via_base(base_pose)
        pose = np.asarray(list(translation) + list(quaternion), dtype=np.float64)
        return pose, f"tf:{self.eef_pose_reference_frame}->{self.eef_link}"

    def _lookup_world_eef_via_base(self, base_pose: np.ndarray) -> tuple:
        if not np.isfinite(base_pose).all():
            return nan_pose(), "unavailable"
        try:
            translation, quaternion = self.tf_listener.lookupTransform(
                self.base_link_frame,
                self.eef_link,
                rospy.Time(0),
            )
        except (
            tf.Exception,
            tf.LookupException,
            tf.ConnectivityException,
            tf.ExtrapolationException,
        ):
            return nan_pose(), "unavailable"

        world_from_base = tf.transformations.translation_matrix(base_pose[:3])
        world_from_base = np.dot(
            world_from_base, tf.transformations.quaternion_matrix(base_pose[3:7])
        )
        base_from_eef = tf.transformations.translation_matrix(translation)
        base_from_eef = np.dot(
            base_from_eef, tf.transformations.quaternion_matrix(quaternion)
        )
        world_from_eef = np.dot(world_from_base, base_from_eef)
        eef_translation = tf.transformations.translation_from_matrix(world_from_eef)
        eef_quaternion = tf.transformations.quaternion_from_matrix(world_from_eef)
        pose = np.asarray(list(eef_translation) + list(eef_quaternion), dtype=np.float64)
        return pose, f"odom+tf:{self.base_link_frame}->{self.eef_link}"

    def _base_odom_cb(self, msg: Odometry) -> None:
        with self._lock:
            self._base_odom = msg

    def _joint_state_cb(self, msg: JointState) -> None:
        with self._lock:
            self._joint_state = msg

    def _model_states_cb(self, msg: ModelStates) -> None:
        with self._lock:
            self._model_states = msg

    def _base_wrench_cb(self, msg: Wrench) -> None:
        with self._lock:
            self._base_wrench = wrench_to_array(msg)

    def _base_wrench_stamped_cb(self, msg: WrenchStamped) -> None:
        with self._lock:
            self._base_wrench = wrench_stamped_to_array(msg)

    def _expert_action_cb(self, msg: Float64MultiArray) -> None:
        with self._lock:
            self._expert_action = msg_to_action(msg)

    def _expert_success_cb(self, msg: Bool) -> None:
        with self._lock:
            self._expert_success = bool(msg.data)

    def _has_required_state(self) -> bool:
        with self._lock:
            if self._joint_state is None:
                return False
            if self._base_odom is not None:
                return True
            if self._model_states is None:
                return False
            return (
                model_pose_from_states(self._model_states, self.base_state_fallback_model_name)
                is not None
            )

    def _has_required_target(self) -> bool:
        with self._lock:
            if self._model_states is None:
                return False
            return model_pose_from_states(self._model_states, self.target_model_name) is not None

    def _has_required_action(self) -> bool:
        with self._lock:
            return self._expert_action is not None and np.isfinite(self._expert_action).all()

    def wait_for_required_state(self, timeout_sec: float = 30.0) -> None:
        wall_start = time.monotonic()
        while not rospy.is_shutdown() and not self._has_required_state():
            if timeout_sec > 0:
                if time.monotonic() - wall_start > timeout_sec:
                    if self.allow_nominal_state_fallback:
                        rospy.logwarn(
                            "Proceeding with nominal state fallback after recorder topic timeout"
                        )
                        return
                    raise RuntimeError(
                        "timed out waiting for required recorder topics: "
                        f"{self.base_odom_topic} or {self.model_states_topic}"
                        f"[{self.base_state_fallback_model_name}], {self.joint_states_topic}"
                    )
            time.sleep(0.1)

        if self.require_target:
            target_start = time.monotonic()
            while not rospy.is_shutdown() and not self._has_required_target():
                if timeout_sec > 0 and time.monotonic() - target_start > timeout_sec:
                    raise RuntimeError(
                        f"timed out waiting for target model {self.target_model_name!r}"
                    )
                time.sleep(0.1)

        if self.require_action:
            action_start = time.monotonic()
            while not rospy.is_shutdown() and not self._has_required_action():
                if timeout_sec > 0 and time.monotonic() - action_start > timeout_sec:
                    raise RuntimeError(
                        f"timed out waiting for expert action on {self.expert_action_topic}"
                    )
                time.sleep(0.1)

        if self.enable_tf_eef_pose and self.tf_eef_wait_sec > 0:
            tf_start = time.monotonic()
            while not rospy.is_shutdown():
                base_pose_for_tf = self._current_base_pose_for_tf()
                eef_pose, _ = self._lookup_eef_pose(base_pose_for_tf)
                if np.isfinite(eef_pose).all():
                    return
                if time.monotonic() - tf_start > self.tf_eef_wait_sec:
                    message = (
                        "timed out waiting for TF eef pose "
                        f"{self.eef_pose_reference_frame}->{self.eef_link}"
                    )
                    if self.require_eef_pose:
                        raise RuntimeError(message)
                    rospy.logwarn("%s; eef_pose will be marked unavailable", message)
                    return
                time.sleep(0.1)

    def _current_base_pose_for_tf(self) -> Optional[np.ndarray]:
        with self._lock:
            base_odom = self._base_odom
            model_states = self._model_states
        if self.prefer_model_states_base_pose and model_states is not None:
            base_pose = model_pose_from_states(
                model_states, self.base_state_fallback_model_name
            )
            if base_pose is not None:
                return base_pose
        if base_odom is not None:
            base_pose, _ = odom_to_pose_velocity(base_odom)
            return base_pose
        if model_states is not None:
            return model_pose_from_states(model_states, self.base_state_fallback_model_name)
        return None

    def _sample_once(self) -> Dict[str, np.ndarray]:
        with self._lock:
            base_odom = self._base_odom
            joint_state = self._joint_state
            model_states = self._model_states
            base_wrench = None if self._base_wrench is None else self._base_wrench.copy()
            expert_action = None if self._expert_action is None else self._expert_action.copy()

        joint_state_source = "joint_states"

        base_pose = None
        base_velocity = None
        base_state_source = "unavailable"
        if self.prefer_model_states_base_pose and model_states is not None:
            base_pose = model_pose_from_states(model_states, self.base_state_fallback_model_name)
            base_velocity = model_twist_from_states(model_states, self.base_state_fallback_model_name)
            if base_pose is not None and base_velocity is not None:
                base_state_source = "gazebo_model_states"

        if base_pose is None or base_velocity is None:
            if base_odom is not None:
                base_pose, base_velocity = odom_to_pose_velocity(base_odom)
                base_state_source = "odom"
            elif model_states is not None:
                base_pose = model_pose_from_states(
                    model_states, self.base_state_fallback_model_name
                )
                base_velocity = model_twist_from_states(
                    model_states, self.base_state_fallback_model_name
                )
                if base_pose is not None and base_velocity is not None:
                    base_state_source = "gazebo_model_states"

        if base_pose is None or base_velocity is None:
            if not self.allow_nominal_state_fallback:
                raise RuntimeError("cannot sample before base odom or model states are available")
            base_pose = self.nominal_base_pose.copy()
            base_velocity = self.nominal_base_velocity.copy()
            base_state_source = "nominal_base_state_fallback"

        if joint_state is not None:
            positions, velocities, _ = joint_state_maps(joint_state)
            active_positions, missing_pos = values_for_names(positions, self.active_joint_names)
            active_velocities, missing_vel = values_for_names(velocities, self.active_joint_names)
            gripper_state, missing_gripper = values_for_names(positions, self.gripper_joint_names)
        elif self.allow_nominal_state_fallback:
            active_positions = np.zeros((len(self.active_joint_names),), dtype=np.float64)
            active_velocities = np.zeros((len(self.active_joint_names),), dtype=np.float64)
            gripper_state = np.zeros((len(self.gripper_joint_names),), dtype=np.float64)
            missing_pos = list(self.active_joint_names)
            missing_vel = list(self.active_joint_names)
            missing_gripper = list(self.gripper_joint_names)
            joint_state_source = "zero_joint_state_fallback"
        else:
            raise RuntimeError("cannot sample before joint states are available")
        self._missing_joint_names.update(missing_pos)
        self._missing_joint_names.update(missing_vel)
        self._missing_joint_names.update(missing_gripper)

        target_pose = nan_pose()
        target_pose_source = "unavailable"
        if model_states is not None:
            maybe_target = model_pose_from_states(model_states, self.target_model_name)
            if maybe_target is not None:
                target_pose = maybe_target
                target_pose_source = "gazebo_model_states"
        if not np.isfinite(target_pose).all() and self.use_nominal_target_when_unavailable:
            target_pose = self.nominal_target_pose.copy()
            target_pose_source = "nominal_target_pose_fallback"

        eef_pose, eef_pose_source = self._lookup_eef_pose(base_pose)
        relative_target_to_eef = np.full((3,), np.nan, dtype=np.float64)
        if np.isfinite(target_pose).all() and np.isfinite(eef_pose).all():
            relative_target_to_eef = target_pose[:3] - eef_pose[:3]

        sample = {
            "timestamp": np.array(rospy.Time.now().to_sec(), dtype=np.float64),
            "base_pose": base_pose,
            "base_velocity": base_velocity,
            "active_joint_positions": active_positions,
            "active_joint_velocities": active_velocities,
            "gripper_state": gripper_state,
            "target_pose": target_pose,
            "eef_pose": eef_pose,
            "relative_target_to_eef": relative_target_to_eef,
            "action_ee_delta": expert_action if expert_action is not None else nan_action(),
            "raw_command": base_wrench if base_wrench is not None else nan_twist(),
            "_base_state_source": np.array(base_state_source),
            "_joint_state_source": np.array(joint_state_source),
            "_target_pose_source": np.array(target_pose_source),
            "_eef_pose_source": np.array(eef_pose_source),
        }
        return sample

    def _success_from_recorded_reaching_distance(
        self, arrays: Dict[str, np.ndarray]
    ) -> Tuple[Optional[bool], Optional[float], Optional[float], str]:
        if self.success_metric not in ("reaching_success", "pregrasp_success"):
            return None, None, None, "unsupported_success_metric"
        if "relative_target_to_eef" not in arrays:
            return None, None, None, "missing_relative_target_to_eef"

        relative = np.asarray(arrays["relative_target_to_eef"], dtype=np.float64)
        if relative.ndim != 2 or relative.shape[0] == 0 or relative.shape[1] < 3:
            return None, None, None, "invalid_relative_target_to_eef_shape"
        if not np.isfinite(relative[:, :3]).all():
            return None, None, None, "relative_target_to_eef_unavailable"

        threshold = float(self.task_cfg.get("success_distance_threshold", 0.1))
        final_distance = float(np.linalg.norm(relative[-1, :3]))
        return bool(final_distance < threshold), final_distance, threshold, "recorded_final_distance"

    def _build_metadata(self, arrays: Dict[str, np.ndarray]) -> Dict[str, object]:
        expert_action_available = bool(np.isfinite(arrays["action_ee_delta"]).all())
        with self._lock:
            expert_success = self._expert_success
        recorded_success, recorded_distance, success_threshold, recorded_success_source = (
            self._success_from_recorded_reaching_distance(arrays)
        )
        if recorded_success is not None:
            success_value = bool(recorded_success)
            success_source = recorded_success_source
        elif expert_success is not None:
            success_value = bool(expert_success)
            success_source = "expert_success_topic"
        else:
            success_value = self.success
            success_source = "recorder_success_param"

        if success_value:
            failure_reason = None
        elif recorded_distance is not None and success_threshold is not None:
            failure_reason = (
                f"{self.success_metric}: final distance {recorded_distance:.6f} "
                f"above {success_threshold:.6f}"
            )
        else:
            failure_reason = "not_evaluated_or_unsuccessful"

        field_availability = {
            "target_pose": bool(np.isfinite(arrays["target_pose"]).all()),
            "eef_pose": bool(np.isfinite(arrays["eef_pose"]).all()),
            "relative_target_to_eef": bool(np.isfinite(arrays["relative_target_to_eef"]).all()),
            "action_ee_delta": expert_action_available,
            "raw_command": bool(np.isfinite(arrays["raw_command"]).all()),
        }
        unavailable_fields = [
            key for key, available in field_availability.items() if not available
        ]

        return {
            "schema_version": str(self.data_cfg.get("schema_version", "0.1")),
            "episode_id": self.episode_id,
            "created_at": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "workspace": "/home/benny/uuv_manipulator_ws",
            "package": "rexrov_single_oberon7_fm_dp",
            "robot_mode": self.data_cfg.get("robot_mode", "dual_model_single_active_left_arm"),
            "active_arm": self.data_cfg.get("active_arm", "left"),
            "passive_arm_policy": self.data_cfg.get("passive_arm_policy", "fixed_or_ignored"),
            "use_images": bool(self.data_cfg.get("use_images", False)),
            "task_type": self.task_type,
            "success_metric": self.success_metric,
            "gripper_enabled": self.gripper_enabled,
            "is_grasp_dataset": self.is_grasp_dataset,
            "world": "runtime_current_world",
            "launch_file": "runtime_current_launch",
            "target_model_name": self.target_model_name,
            "target_state_source": self._sample_source_from_arrays(
                arrays, "_target_pose_source", "unknown"
            ),
            "base_odom_topic": self.base_odom_topic,
            "base_state_fallback_model_name": self.base_state_fallback_model_name,
            "base_state_source": self._base_state_source_from_samples(arrays),
            "joint_states_topic": self.joint_states_topic,
            "joint_state_source": self._sample_source_from_arrays(
                arrays, "_joint_state_source", "unknown"
            ),
            "allow_nominal_state_fallback": self.allow_nominal_state_fallback,
            "base_wrench_topic": self.base_wrench_topic,
            "arm_command_topic": self.topics_cfg.get("arm_command_topic") or None,
            "gripper_command_topic": self.topics_cfg.get("gripper_command_topic") or None,
            "expert_action_topic": self.expert_action_topic,
            "expert_success_topic": self.expert_success_topic,
            "controller_type": self.controller_type,
            "moveit_group": self.joints_cfg.get("moveit_group", "arm_l"),
            "gripper_group": self.joints_cfg.get("gripper_group", "hand_l"),
            "eef_link": self.eef_link,
            "eef_pose_reference_frame": self.eef_pose_reference_frame,
            "eef_pose_source": self._sample_source_from_arrays(
                arrays, "_eef_pose_source", "unknown"
            ),
            "action_mode": self.data_cfg.get("policy_action", {}).get(
                "mode", "eef_delta_plus_gripper"
            ),
            "action_dim": int(self.data_cfg.get("policy_action", {}).get("action_dim", 7)),
            "action_frame": self.data_cfg.get("policy_action", {}).get(
                "frame", "eef_or_task_frame_to_be_confirmed"
            ),
            "target_directed_action_frame": self.target_directed_action_frame,
            "arm_action_frame": self.arm_action_frame,
            "state_sequence": self.state_sequence,
            "max_linear_step": self.max_linear_step,
            "max_joint_delta": self.max_joint_delta,
            "action_ee_delta_available": expert_action_available,
            "rate_hz": self.rate_hz,
            "max_duration_sec": self.max_duration_sec,
            "active_joint_names": self.active_joint_names,
            "gripper_joint_names": self.gripper_joint_names,
            "inactive_joint_names": self.inactive_joint_names,
            "missing_joint_names": sorted(self._missing_joint_names),
            "field_availability": field_availability,
            "unavailable_fields": unavailable_fields,
            "success": success_value,
            "success_source": success_source,
            "recorded_success_distance_m": recorded_distance,
            "recorded_success_distance_threshold_m": success_threshold,
            "failure_reason": failure_reason,
            "notes": (
                "Stage 6 recorder captures project-local scripted expert action labels when "
                "available. The recorder uses TF for eef_pose when available. "
                "Real arm execution still depends on confirming controller topics. "
                "If target_state_source is nominal_target_pose_fallback, the target was not "
                "physically spawned in Gazebo for that episode."
            ),
        }

    def _base_state_source_from_samples(self, arrays: Dict[str, np.ndarray]) -> str:
        return self._sample_source_from_arrays(arrays, "_base_state_source", "unknown")

    def _sample_source_from_arrays(
        self, arrays: Dict[str, np.ndarray], key: str, default: str
    ) -> str:
        raw = arrays.pop(key, None)
        if raw is None or len(raw) == 0:
            return default
        values = [str(value) for value in np.asarray(raw).tolist()]
        unique = sorted(set(values))
        if len(unique) == 1:
            return unique[0]
        return "mixed:" + ",".join(unique)

    def run(self) -> Path:
        wait_timeout = self.state_fallback_wait_sec if self.allow_nominal_state_fallback else 30.0
        self.wait_for_required_state(timeout_sec=wait_timeout)

        sample_count = max(self.min_samples, int(round(self.max_duration_sec * self.rate_hz)))
        rospy.loginfo(
            "Recording episode %s: %d samples at %.3f Hz",
            self.episode_id,
            sample_count,
            self.rate_hz,
        )

        sleep_dt = 1.0 / max(self.rate_hz, 1e-6)
        for index in range(sample_count):
            if rospy.is_shutdown():
                break
            sample = self._sample_once()
            self._samples.append(sample)
            time.sleep(sleep_dt)

        if len(self._samples) < self.min_samples:
            raise RuntimeError(f"recorded only {len(self._samples)} samples")

        arrays = stack_samples(self._samples)
        done = np.zeros((arrays["timestamp"].shape[0],), dtype=np.bool_)
        done[-1] = True
        arrays["done"] = done

        metadata = self._build_metadata(arrays)
        if self.require_target and not metadata["field_availability"]["target_pose"]:
            raise RuntimeError(f"target model {self.target_model_name!r} was not observed")

        episode_path = save_episode_npz(arrays, metadata, self.output_dir, self.episode_id)
        rospy.loginfo("Saved episode to %s", episode_path)
        return episode_path
