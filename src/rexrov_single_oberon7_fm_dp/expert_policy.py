import enum
import time
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import rospkg
import rospy
import yaml
from gazebo_msgs.msg import ModelStates
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, Float64MultiArray, String
import tf

from rexrov_single_oberon7_fm_dp.action_converter import action_to_msg, make_action
from rexrov_single_oberon7_fm_dp.arm_command_converter import ArmEEDeltaCommandConverter
from rexrov_single_oberon7_fm_dp.ros_interface import model_pose_from_states
from rexrov_single_oberon7_fm_dp.success_checker import check_simple_success


class ExpertState(enum.Enum):
    WAIT_FOR_STATE = "WAIT_FOR_STATE"
    APPROACH_BASE = "APPROACH_BASE"
    MOVE_TO_PREGRASP = "MOVE_TO_PREGRASP"
    MOVE_TO_GRASP = "MOVE_TO_GRASP"
    CLOSE_GRIPPER = "CLOSE_GRIPPER"
    LIFT_OR_HOLD = "LIFT_OR_HOLD"
    FINISH = "FINISH"


def _load_yaml(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def load_configs() -> Dict[str, Dict]:
    package_path = Path(rospkg.RosPack().get_path("rexrov_single_oberon7_fm_dp"))
    config_dir = package_path / "config"
    return {
        "topics": _load_yaml(config_dir / "topics.yaml"),
        "task": _load_yaml(config_dir / "task_grasp.yaml"),
        "joints": _load_yaml(config_dir / "active_joints_left_arm.yaml"),
    }


class ScriptedExpert:
    def __init__(self) -> None:
        configs = load_configs()
        self.topics_cfg = configs["topics"]
        self.task_cfg = configs["task"]
        self.joints_cfg = configs["joints"]
        self.expert_cfg = self.task_cfg.get("scripted_expert", {})

        self.rate_hz = float(rospy.get_param("~rate_hz", self.expert_cfg.get("rate_hz", 10.0)))
        self.max_duration_sec = float(
            rospy.get_param("~max_duration_sec", self.expert_cfg.get("max_duration_sec", 8.0))
        )
        self.wait_for_target_sec = float(
            rospy.get_param("~wait_for_target_sec", self.expert_cfg.get("wait_for_target_sec", 5.0))
        )
        self.target_model_name = rospy.get_param(
            "~target_model_name", self.task_cfg.get("target_model_name", "cylinder_target")
        )
        self.model_states_topic = rospy.get_param(
            "~model_states_topic", self.topics_cfg.get("model_states_topic", "/gazebo/model_states")
        )
        self.base_odom_topic = rospy.get_param(
            "~base_odom_topic", self.topics_cfg.get("base_odom_topic", "/rexrov/pose_gt")
        )
        self.joint_states_topic = rospy.get_param(
            "~joint_states_topic", self.topics_cfg.get("joint_states_topic", "/joint_states")
        )
        self.action_topic = rospy.get_param(
            "~expert_action_topic",
            self.topics_cfg.get(
                "expert_action_topic", "/rexrov_single_oberon7_fm_dp/expert/action_ee_delta"
            ),
        )
        self.state_topic = rospy.get_param(
            "~expert_state_topic",
            self.topics_cfg.get("expert_state_topic", "/rexrov_single_oberon7_fm_dp/expert/state"),
        )
        self.success_topic = rospy.get_param(
            "~expert_success_topic",
            self.topics_cfg.get(
                "expert_success_topic", "/rexrov_single_oberon7_fm_dp/expert/success"
            ),
        )
        self.task_type = rospy.get_param("~task_type", "arm_only_reaching")
        self.success_metric = rospy.get_param("~success_metric", "reaching_success")
        self.execute_arm = bool(rospy.get_param("~execute_arm", False))
        self.enable_gripper_command = bool(rospy.get_param("~enable_gripper_command", False))
        if self.enable_gripper_command:
            raise RuntimeError(
                "gripper command execution is blocked and disabled for B5b arm-only debug"
            )
        self.arm_command_topic = rospy.get_param(
            "~arm_command_topic", self.topics_cfg.get("arm_command_topic") or "/oberon7/arm_position_l/command"
        )
        moveit_cfg = self.topics_cfg.get("moveit", {})
        self.compute_ik_service = rospy.get_param(
            "~compute_ik_service", moveit_cfg.get("compute_ik_service", "/compute_ik")
        )
        self.arm_group = rospy.get_param("~arm_group", moveit_cfg.get("active_arm_group", "arm_l"))
        self.eef_link = rospy.get_param("~eef_link", moveit_cfg.get("eef_link", "oberon7_l/end_effector"))
        self.max_linear_step = float(rospy.get_param("~max_linear_step", 0.005))
        self.max_angular_step = float(rospy.get_param("~max_angular_step", 0.05))
        self.max_joint_delta = float(rospy.get_param("~max_joint_delta", 0.01))
        self.time_from_start_sec = float(rospy.get_param("~time_from_start_sec", 3.0))
        self.command_connection_timeout_sec = float(
            rospy.get_param("~command_connection_timeout_sec", 5.0)
        )
        self.post_publish_sleep_sec = float(rospy.get_param("~post_publish_sleep_sec", 0.5))
        self.execute_arm_once_per_state = bool(rospy.get_param("~execute_arm_once_per_state", True))
        self.execute_arm_states = {
            item.strip()
            for item in str(
                rospy.get_param("~execute_arm_states", "MOVE_TO_PREGRASP,MOVE_TO_GRASP,LIFT_OR_HOLD")
            ).split(",")
            if item.strip()
        }
        self.label_max_linear_step = float(
            rospy.get_param("~label_max_linear_step", self.max_linear_step if self.execute_arm else 0.05)
        )
        self.label_max_angular_step = float(
            rospy.get_param("~label_max_angular_step", self.max_angular_step if self.execute_arm else 0.25)
        )
        self.target_directed_reaching = bool(rospy.get_param("~target_directed_reaching", False))
        self.target_directed_states = {
            item.strip()
            for item in str(
                rospy.get_param("~target_directed_states", "MOVE_TO_PREGRASP,MOVE_TO_GRASP")
            ).split(",")
            if item.strip()
        }
        self.state_sequence = self._state_sequence_from_param(
            rospy.get_param(
                "~state_sequence",
                "MOVE_TO_PREGRASP,MOVE_TO_GRASP,CLOSE_GRIPPER,LIFT_OR_HOLD",
            )
        )
        self.target_directed_action_frame = rospy.get_param(
            "~target_directed_action_frame", "base_link"
        )
        self.arm_action_frame = rospy.get_param("~arm_action_frame", "planning_frame")
        self.converter_action_frame = (
            self.target_directed_action_frame
            if self.target_directed_reaching
            else self.arm_action_frame
        )
        self.eef_pose_reference_frame = rospy.get_param("~eef_pose_reference_frame", "world")
        self.base_link_frame = rospy.get_param("~base_link_frame", "rexrov/base_link")
        self.tf_listener = tf.TransformListener() if self.target_directed_reaching else None
        self._warned_eef_unavailable = False

        self.nominal_target_pose = self._nominal_target_pose()
        self.target_pose: Optional[np.ndarray] = None
        self.base_pose: Optional[np.ndarray] = None
        self.target_source = "unavailable"
        self.have_joint_state = False
        self.last_action = make_action([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 0.0)
        self._arm_executed_states = set()
        self.arm_converter = None
        if self.execute_arm:
            active_joint_names = self.joints_cfg.get("active_joint_names") or [
                "oberon7_l/azimuth",
                "oberon7_l/shoulder",
                "oberon7_l/elbow",
                "oberon7_l/roll",
                "oberon7_l/pitch",
                "oberon7_l/wrist",
            ]
            self.arm_converter = ArmEEDeltaCommandConverter(
                joint_states_topic=self.joint_states_topic,
                arm_command_topic=self.arm_command_topic,
                compute_ik_service=self.compute_ik_service,
                arm_group=self.arm_group,
                eef_link=self.eef_link,
                planning_frame=self.eef_pose_reference_frame,
                action_frame=self.converter_action_frame,
                base_odom_topic=self.base_odom_topic,
                base_link_frame=self.base_link_frame,
                active_joint_names=active_joint_names,
                max_linear_step=self.max_linear_step,
                max_angular_step=self.max_angular_step,
                max_joint_delta=self.max_joint_delta,
                time_from_start_sec=self.time_from_start_sec,
                command_connection_timeout_sec=self.command_connection_timeout_sec,
                post_publish_sleep_sec=self.post_publish_sleep_sec,
            )

        self.action_pub = rospy.Publisher(
            self.action_topic, Float64MultiArray, queue_size=10, latch=True
        )
        self.state_pub = rospy.Publisher(self.state_topic, String, queue_size=10, latch=True)
        self.success_pub = rospy.Publisher(self.success_topic, Bool, queue_size=10, latch=True)

        rospy.Subscriber(self.model_states_topic, ModelStates, self._model_states_cb, queue_size=1)
        rospy.Subscriber(self.base_odom_topic, Odometry, self._base_odom_cb, queue_size=1)
        rospy.Subscriber(self.joint_states_topic, JointState, self._joint_states_cb, queue_size=1)

    def _nominal_target_pose(self) -> np.ndarray:
        pose_cfg = self.task_cfg.get("nominal_target_pose", {})
        xyz = list(pose_cfg.get("xyz", [2.6, 2.0, -40.0]))
        xyz[0] = float(rospy.get_param("~target_x", xyz[0]))
        xyz[1] = float(rospy.get_param("~target_y", xyz[1]))
        xyz[2] = float(rospy.get_param("~target_z", xyz[2]))
        quat = pose_cfg.get("quaternion_xyzw", [0.0, 0.0, 0.0, 1.0])
        return np.asarray(list(xyz) + list(quat), dtype=np.float64)

    def _model_states_cb(self, msg: ModelStates) -> None:
        maybe_pose = model_pose_from_states(msg, self.target_model_name)
        if maybe_pose is not None:
            self.target_pose = maybe_pose
            self.target_source = "gazebo_model_states"

    def _base_odom_cb(self, msg: Odometry) -> None:
        self.base_pose = np.asarray(
            [
                msg.pose.pose.position.x,
                msg.pose.pose.position.y,
                msg.pose.pose.position.z,
                msg.pose.pose.orientation.x,
                msg.pose.pose.orientation.y,
                msg.pose.pose.orientation.z,
                msg.pose.pose.orientation.w,
            ],
            dtype=np.float64,
        )

    def _joint_states_cb(self, msg: JointState) -> None:
        self.have_joint_state = True

    def _current_target_pose(self) -> np.ndarray:
        if self.target_pose is not None and np.isfinite(self.target_pose).all():
            return self.target_pose
        self.target_source = "nominal_target_pose_fallback"
        return self.nominal_target_pose

    def _state_duration(self, state: ExpertState) -> float:
        durations = self.expert_cfg.get("state_durations_sec", {})
        param_name = f"~state_duration_{state.value}"
        return float(rospy.get_param(param_name, durations.get(state.value, 1.0)))

    @staticmethod
    def _state_sequence_from_param(value) -> list:
        states = []
        for item in str(value).split(","):
            name = item.strip()
            if not name:
                continue
            try:
                states.append(ExpertState(name))
            except ValueError as exc:
                valid = ",".join(state.value for state in ExpertState)
                raise ValueError(f"unsupported expert state {name!r}; valid states: {valid}") from exc
        if not states:
            raise ValueError("state_sequence must contain at least one expert state")
        return states

    def _lookup_eef_pose(self) -> Optional[np.ndarray]:
        if self.tf_listener is None:
            return None
        try:
            translation, quaternion = self.tf_listener.lookupTransform(
                self.eef_pose_reference_frame,
                self.eef_link,
                rospy.Time(0),
            )
            return np.asarray(list(translation) + list(quaternion), dtype=np.float64)
        except (
            tf.Exception,
            tf.LookupException,
            tf.ConnectivityException,
            tf.ExtrapolationException,
        ):
            if self.eef_pose_reference_frame != "world" or self.base_pose is None:
                return None
            return self._lookup_world_eef_via_base()

    def _lookup_world_eef_via_base(self) -> Optional[np.ndarray]:
        if self.tf_listener is None or self.base_pose is None or not np.isfinite(self.base_pose).all():
            return None
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
            return None

        world_from_base = tf.transformations.translation_matrix(self.base_pose[:3])
        world_from_base = np.dot(
            world_from_base, tf.transformations.quaternion_matrix(self.base_pose[3:7])
        )
        base_from_eef = tf.transformations.translation_matrix(translation)
        base_from_eef = np.dot(base_from_eef, tf.transformations.quaternion_matrix(quaternion))
        world_from_eef = np.dot(world_from_base, base_from_eef)
        eef_translation = tf.transformations.translation_from_matrix(world_from_eef)
        eef_quaternion = tf.transformations.quaternion_from_matrix(world_from_eef)
        return np.asarray(list(eef_translation) + list(eef_quaternion), dtype=np.float64)

    def _target_eef_delta_base_frame(self, target_pose: np.ndarray) -> Optional[np.ndarray]:
        if self.tf_listener is None or self.base_pose is None or not np.isfinite(self.base_pose).all():
            return None
        try:
            eef_translation, _ = self.tf_listener.lookupTransform(
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
            return None

        world_from_base = tf.transformations.translation_matrix(self.base_pose[:3])
        world_from_base = np.dot(
            world_from_base, tf.transformations.quaternion_matrix(self.base_pose[3:7])
        )
        base_from_world = np.linalg.inv(world_from_base)
        target_world = np.asarray([target_pose[0], target_pose[1], target_pose[2], 1.0])
        target_base = np.dot(base_from_world, target_world)[:3]
        return np.asarray(target_base - np.asarray(eef_translation), dtype=np.float64)

    def _target_directed_action(self) -> Optional[np.ndarray]:
        target_pose = self._current_target_pose()
        if target_pose is None or not np.isfinite(target_pose).all():
            if not self._warned_eef_unavailable:
                rospy.logwarn(
                    "Target-directed reaching requested but finite target/eef pose is unavailable; "
                    "falling back to scripted deltas"
                )
                self._warned_eef_unavailable = True
            return None

        if self.target_directed_action_frame == "base_link":
            delta_xyz = self._target_eef_delta_base_frame(target_pose)
        else:
            eef_pose = self._lookup_eef_pose()
            delta_xyz = None if eef_pose is None else np.asarray(target_pose[:3] - eef_pose[:3])

        if delta_xyz is None or not np.isfinite(delta_xyz).all():
            if not self._warned_eef_unavailable:
                rospy.logwarn(
                    "Target-directed reaching requested but finite target/eef pose is unavailable; "
                    "falling back to scripted deltas"
                )
                self._warned_eef_unavailable = True
            return None
        delta_xyz = np.asarray(delta_xyz, dtype=np.float64)
        rospy.logdebug(
            "B5d target-directed reaching frame=%s delta_xyz=%s distance=%.6f",
            self.target_directed_action_frame,
            delta_xyz.astype(float).tolist(),
            float(np.linalg.norm(delta_xyz)),
        )
        return make_action(
            [float(delta_xyz[0]), float(delta_xyz[1]), float(delta_xyz[2]), 0.0, 0.0, 0.0],
            self.expert_cfg.get("gripper_open_cmd", 0.0),
            max_linear_step=self.label_max_linear_step,
            max_angular_step=self.label_max_angular_step,
        )

    def _action_for_state(self, state: ExpertState) -> np.ndarray:
        if self.target_directed_reaching and state.value in self.target_directed_states:
            action = self._target_directed_action()
            if action is not None:
                return action
        if state == ExpertState.MOVE_TO_PREGRASP:
            return make_action(
                self.expert_cfg.get("approach_delta", [0.03, 0.0, 0.02, 0.0, 0.0, 0.0]),
                self.expert_cfg.get("gripper_open_cmd", 0.0),
                max_linear_step=self.label_max_linear_step,
                max_angular_step=self.label_max_angular_step,
            )
        if state == ExpertState.MOVE_TO_GRASP:
            return make_action(
                self.expert_cfg.get("grasp_delta", [0.02, 0.0, -0.03, 0.0, 0.0, 0.0]),
                self.expert_cfg.get("gripper_open_cmd", 0.0),
                max_linear_step=self.label_max_linear_step,
                max_angular_step=self.label_max_angular_step,
            )
        if state == ExpertState.CLOSE_GRIPPER:
            return make_action(
                self.expert_cfg.get("close_delta", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
                self.expert_cfg.get("gripper_closed_cmd", 1.0),
                max_linear_step=self.label_max_linear_step,
                max_angular_step=self.label_max_angular_step,
            )
        if state == ExpertState.LIFT_OR_HOLD:
            return make_action(
                self.expert_cfg.get("lift_delta", [0.0, 0.0, 0.04, 0.0, 0.0, 0.0]),
                self.expert_cfg.get("gripper_closed_cmd", 1.0),
                max_linear_step=self.label_max_linear_step,
                max_angular_step=self.label_max_angular_step,
            )
        return make_action(
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            self.last_action[-1],
            max_linear_step=self.label_max_linear_step,
            max_angular_step=self.label_max_angular_step,
        )

    def _maybe_execute_arm(self, state: ExpertState, action: np.ndarray) -> None:
        if not self.execute_arm or self.arm_converter is None:
            return
        if state.value not in self.execute_arm_states:
            return
        if self.execute_arm_once_per_state and state.value in self._arm_executed_states:
            return
        result = self.arm_converter.execute(action)
        self._arm_executed_states.add(state.value)
        rospy.loginfo(
            "B5 arm command state=%s planning_frame=%s action_frame=%s current_eef_xyz=%s target_eef_xyz=%s clipped_xyz_action_frame=%s clipped_xyz_planning_frame=%s command_positions=%s",
            state.value,
            result.planning_frame,
            result.action_frame,
            result.current_eef_xyz,
            result.target_eef_xyz,
            result.clipped_xyz_action_frame,
            result.clipped_xyz_planning_frame,
            result.command_positions,
        )

    def _evaluate_success(self):
        distance_threshold = float(self.task_cfg.get("success_distance_threshold", 0.1))
        if (
            self.task_type in ("arm_only_reaching", "pregrasp_positioning")
            or self.success_metric in ("reaching_success", "pregrasp_success")
            or not self.enable_gripper_command
        ):
            target_pose = self._current_target_pose()
            if target_pose is None or not np.isfinite(target_pose).all():
                return False, "target_unavailable"
            if self.target_directed_action_frame == "base_link":
                delta_xyz = self._target_eef_delta_base_frame(target_pose)
            else:
                eef_pose = self._lookup_eef_pose()
                if eef_pose is None:
                    return False, "eef_pose_unavailable"
                delta_xyz = np.asarray(target_pose[:3] - eef_pose[:3], dtype=np.float64)
            distance = float(np.linalg.norm(delta_xyz))
            if distance < distance_threshold:
                return True, f"{self.success_metric}: distance {distance:.6f} below {distance_threshold:.6f}"
            return False, f"{self.success_metric}: distance {distance:.6f} above {distance_threshold:.6f}"

        success = check_simple_success(
            gripper_cmd=float(self.last_action[-1]),
            target_pose=self.target_pose,
            eef_pose=None,
            distance_threshold=distance_threshold,
        )
        return bool(success.success), success.reason

    def _publish(self, state: ExpertState, action: np.ndarray) -> None:
        self.last_action = action
        self.action_pub.publish(action_to_msg(action))
        self.state_pub.publish(String(data=state.value))
        self._maybe_execute_arm(state, action)

    def wait_for_state(self) -> None:
        timeout = self.wait_for_target_sec
        start = time.monotonic()
        while not rospy.is_shutdown() and not self.have_joint_state:
            self._publish(ExpertState.WAIT_FOR_STATE, make_action([0.0] * 6, 0.0))
            if time.monotonic() - start > timeout:
                rospy.logwarn("Proceeding scripted expert without seeing joint state timeout")
                return
            time.sleep(0.1)

    def wait_for_target(self) -> None:
        timeout = self.wait_for_target_sec
        start = time.monotonic()
        while not rospy.is_shutdown() and self.target_pose is None:
            self._publish(ExpertState.WAIT_FOR_STATE, make_action([0.0] * 6, 0.0))
            if time.monotonic() - start > timeout:
                rospy.logwarn(
                    "Target %s not observed; using nominal target pose fallback",
                    self.target_model_name,
                )
                return
            time.sleep(0.1)

    def run(self) -> bool:
        self.wait_for_state()
        self.wait_for_target()
        self._current_target_pose()
        rospy.loginfo(
            "Scripted expert running with target source %s and target pose %s; execute_arm=%s gripper_command_enabled=%s target_directed_reaching=%s",
            self.target_source,
            self._current_target_pose().tolist(),
            self.execute_arm,
            self.enable_gripper_command,
            self.target_directed_reaching,
        )

        sequence = self.state_sequence
        rospy.loginfo(
            "Scripted expert state_sequence=%s",
            [state.value for state in sequence],
        )
        sleep_dt = 1.0 / max(self.rate_hz, 1e-6)
        start = time.monotonic()
        for state in sequence:
            state_start = time.monotonic()
            duration = self._state_duration(state)
            while not rospy.is_shutdown() and time.monotonic() - state_start < duration:
                if time.monotonic() - start > self.max_duration_sec:
                    rospy.logwarn("Scripted expert reached max_duration_sec")
                    self.state_pub.publish(String(data=ExpertState.FINISH.value))
                    self.success_pub.publish(Bool(data=False))
                    return False
                self._publish(state, self._action_for_state(state))
                time.sleep(sleep_dt)

        success, reason = self._evaluate_success()
        rospy.loginfo("Scripted expert finished: success=%s reason=%s", success, reason)
        self.state_pub.publish(String(data=ExpertState.FINISH.value))
        self.success_pub.publish(Bool(data=success))
        self.action_pub.publish(action_to_msg(self.last_action))
        return success
