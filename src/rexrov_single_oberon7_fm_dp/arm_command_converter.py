from dataclasses import dataclass
import copy
from typing import Dict, List, Sequence

from geometry_msgs.msg import PoseStamped
import moveit_commander
import numpy as np
import rospy
import tf
from moveit_msgs.msg import MoveItErrorCodes, RobotState
from moveit_msgs.srv import GetPositionIK, GetPositionIKRequest
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from rexrov_single_oberon7_fm_dp.ros_interface import joint_state_maps, values_for_names


DEFAULT_ARM_JOINTS = [
    "oberon7_l/azimuth",
    "oberon7_l/shoulder",
    "oberon7_l/elbow",
    "oberon7_l/roll",
    "oberon7_l/pitch",
    "oberon7_l/wrist",
]


@dataclass
class ArmCommandConversionResult:
    planning_frame: str
    action_frame: str
    current_eef_xyz: List[float]
    target_eef_xyz: List[float]
    clipped_xyz_action_frame: List[float]
    clipped_xyz_planning_frame: List[float]
    active_joint_names: List[str]
    current_joints: List[float]
    ik_joints: List[float]
    raw_joint_delta: List[float]
    clipped_joint_delta: List[float]
    command_positions: List[float]
    trajectory: JointTrajectory


class ArmEEDeltaCommandConverter:
    """Convert small EE-delta actions into left-arm JointTrajectory commands."""

    def __init__(
        self,
        joint_states_topic: str = "/joint_states",
        arm_command_topic: str = "/oberon7/arm_position_l/command",
        compute_ik_service: str = "/compute_ik",
        arm_group: str = "arm_l",
        eef_link: str = "oberon7_l/end_effector",
        planning_frame: str = "world",
        action_frame: str = "planning_frame",
        base_odom_topic: str = "/rexrov/pose_gt",
        base_link_frame: str = "rexrov/base_link",
        active_joint_names: Sequence[str] = DEFAULT_ARM_JOINTS,
        max_linear_step: float = 0.005,
        max_angular_step: float = 0.05,
        max_joint_delta: float = 0.01,
        time_from_start_sec: float = 3.0,
        ik_timeout_sec: float = 2.0,
        wait_timeout_sec: float = 10.0,
        command_connection_timeout_sec: float = 5.0,
        post_publish_sleep_sec: float = 0.5,
    ) -> None:
        self.joint_states_topic = joint_states_topic
        self.arm_command_topic = arm_command_topic
        self.compute_ik_service = compute_ik_service
        self.arm_group = arm_group
        self.eef_link = eef_link
        self.planning_frame = planning_frame
        self.action_frame = str(action_frame or "planning_frame")
        self.base_odom_topic = base_odom_topic
        self.base_link_frame = base_link_frame
        self.active_joint_names = list(active_joint_names)
        self.max_linear_step = float(max_linear_step)
        self.max_angular_step = float(max_angular_step)
        self.max_joint_delta = float(max_joint_delta)
        self.time_from_start_sec = float(time_from_start_sec)
        self.ik_timeout_sec = float(ik_timeout_sec)
        self.wait_timeout_sec = float(wait_timeout_sec)
        self.command_connection_timeout_sec = float(command_connection_timeout_sec)
        self.post_publish_sleep_sec = float(post_publish_sleep_sec)

        self.tf_listener = tf.TransformListener()
        self.move_group = None
        self._init_move_group_if_available()
        self.command_pub = rospy.Publisher(
            self.arm_command_topic, JointTrajectory, queue_size=1, latch=False
        )

    def _init_move_group_if_available(self) -> None:
        if not rospy.has_param("/robot_description_semantic"):
            rospy.logwarn(
                "MoveIt semantic param /robot_description_semantic is unavailable; "
                "B5 arm converter will use direct /compute_ik service mode"
            )
            return
        try:
            moveit_commander.roscpp_initialize([])
            self.move_group = moveit_commander.MoveGroupCommander(self.arm_group)
            self.move_group.set_end_effector_link(self.eef_link)
        except Exception as exc:
            self.move_group = None
            rospy.logwarn(
                "MoveGroupCommander(%s) unavailable (%s); using direct /compute_ik service mode",
                self.arm_group,
                exc,
            )

    @staticmethod
    def _map_joint_positions(msg: JointState) -> Dict[str, float]:
        positions, _, _ = joint_state_maps(msg)
        return positions

    def _wait_for_joint_state(self) -> JointState:
        return rospy.wait_for_message(
            self.joint_states_topic, JointState, timeout=self.wait_timeout_sec
        )

    @staticmethod
    def _rotate_vector(quaternion, vector: np.ndarray) -> np.ndarray:
        rotation = tf.transformations.quaternion_matrix(quaternion)[:3, :3]
        return np.dot(rotation, vector)

    def _base_delta_in_world(self, delta_xyz: np.ndarray) -> np.ndarray:
        odom = rospy.wait_for_message(
            self.base_odom_topic, Odometry, timeout=self.wait_timeout_sec
        )
        base_q = [
            odom.pose.pose.orientation.x,
            odom.pose.pose.orientation.y,
            odom.pose.pose.orientation.z,
            odom.pose.pose.orientation.w,
        ]
        return self._rotate_vector(base_q, delta_xyz)

    def _delta_xyz_in_planning_frame(self, delta_xyz: np.ndarray) -> np.ndarray:
        frame = self.action_frame.strip()
        if frame in ("", "planning_frame", self.planning_frame):
            return delta_xyz

        if frame in ("base_link", self.base_link_frame):
            if self.planning_frame == "world":
                return self._base_delta_in_world(delta_xyz)
            try:
                _, quaternion = self.tf_listener.lookupTransform(
                    self.planning_frame,
                    self.base_link_frame,
                    rospy.Time(0),
                )
                return self._rotate_vector(quaternion, delta_xyz)
            except (
                tf.Exception,
                tf.LookupException,
                tf.ConnectivityException,
                tf.ExtrapolationException,
            ) as exc:
                raise RuntimeError(
                    f"failed to transform action delta from {frame} to "
                    f"{self.planning_frame}: {exc}"
                )

        try:
            _, quaternion = self.tf_listener.lookupTransform(
                self.planning_frame,
                frame,
                rospy.Time(0),
            )
            return self._rotate_vector(quaternion, delta_xyz)
        except (
            tf.Exception,
            tf.LookupException,
            tf.ConnectivityException,
            tf.ExtrapolationException,
        ) as exc:
            raise RuntimeError(
                f"unsupported or unavailable action_frame {frame!r} for "
                f"planning frame {self.planning_frame!r}: {exc}"
            )

    def _target_pose_from_action(self, action: Sequence[float]):
        if self.move_group is not None:
            planning_frame = self.move_group.get_planning_frame()
            self.move_group.set_pose_reference_frame(planning_frame)
            current_pose = self.move_group.get_current_pose(self.eef_link)
            current_pose.header.frame_id = planning_frame
            current_pose.header.stamp = rospy.Time(0)
        else:
            current_pose = self._lookup_current_eef_pose()

        values = np.asarray(action, dtype=np.float64)
        if values.shape[0] < 6:
            raise ValueError(f"action must contain at least 6 EE-delta values, got {values.shape}")
        clipped_xyz = np.clip(values[:3], -self.max_linear_step, self.max_linear_step)
        clipped_rpy = np.clip(values[3:6], -self.max_angular_step, self.max_angular_step)
        planning_xyz = self._delta_xyz_in_planning_frame(clipped_xyz)

        target_pose = copy.deepcopy(current_pose)
        target_pose.pose.position.x += float(planning_xyz[0])
        target_pose.pose.position.y += float(planning_xyz[1])
        target_pose.pose.position.z += float(planning_xyz[2])

        current_q = [
            target_pose.pose.orientation.x,
            target_pose.pose.orientation.y,
            target_pose.pose.orientation.z,
            target_pose.pose.orientation.w,
        ]
        delta_q = tf.transformations.quaternion_from_euler(*clipped_rpy.tolist())
        target_q = tf.transformations.quaternion_multiply(current_q, delta_q)
        target_q = target_q / max(np.linalg.norm(target_q), 1e-12)
        target_pose.pose.orientation.x = float(target_q[0])
        target_pose.pose.orientation.y = float(target_q[1])
        target_pose.pose.orientation.z = float(target_q[2])
        target_pose.pose.orientation.w = float(target_q[3])
        target_pose.header.stamp = rospy.Time(0)
        return current_pose, target_pose, clipped_xyz, planning_xyz

    def _lookup_current_eef_pose(self) -> PoseStamped:
        try:
            translation, quaternion = self.tf_listener.lookupTransform(
                self.planning_frame,
                self.eef_link,
                rospy.Time(0),
            )
        except (
            tf.Exception,
            tf.LookupException,
            tf.ConnectivityException,
            tf.ExtrapolationException,
        ):
            if self.planning_frame != "world":
                raise
            translation, quaternion = self._lookup_world_eef_via_base()

        pose = PoseStamped()
        pose.header.frame_id = self.planning_frame
        pose.header.stamp = rospy.Time(0)
        pose.pose.position.x = float(translation[0])
        pose.pose.position.y = float(translation[1])
        pose.pose.position.z = float(translation[2])
        pose.pose.orientation.x = float(quaternion[0])
        pose.pose.orientation.y = float(quaternion[1])
        pose.pose.orientation.z = float(quaternion[2])
        pose.pose.orientation.w = float(quaternion[3])
        return pose

    def _lookup_world_eef_via_base(self):
        odom = rospy.wait_for_message(
            self.base_odom_topic, Odometry, timeout=self.wait_timeout_sec
        )
        base_pose = [
            odom.pose.pose.position.x,
            odom.pose.pose.position.y,
            odom.pose.pose.position.z,
            odom.pose.pose.orientation.x,
            odom.pose.pose.orientation.y,
            odom.pose.pose.orientation.z,
            odom.pose.pose.orientation.w,
        ]
        translation, quaternion = self.tf_listener.lookupTransform(
            self.base_link_frame,
            self.eef_link,
            rospy.Time(0),
        )
        world_from_base = tf.transformations.translation_matrix(base_pose[:3])
        world_from_base = np.dot(
            world_from_base, tf.transformations.quaternion_matrix(base_pose[3:7])
        )
        base_from_eef = tf.transformations.translation_matrix(translation)
        base_from_eef = np.dot(base_from_eef, tf.transformations.quaternion_matrix(quaternion))
        world_from_eef = np.dot(world_from_base, base_from_eef)
        return (
            tf.transformations.translation_from_matrix(world_from_eef),
            tf.transformations.quaternion_from_matrix(world_from_eef),
        )

    def _seed_joint_state(self, current_joints: np.ndarray) -> JointState:
        seed = JointState()
        if self.move_group is not None:
            seed.name = list(self.move_group.get_active_joints())
            seed.position = list(self.move_group.get_current_joint_values())
        else:
            seed.name = list(self.active_joint_names)
            seed.position = current_joints.astype(float).tolist()
        return seed

    def _request_ik(self, target_pose, current_joints: np.ndarray):
        rospy.wait_for_service(self.compute_ik_service, timeout=self.wait_timeout_sec)
        service = rospy.ServiceProxy(self.compute_ik_service, GetPositionIK)

        request = GetPositionIKRequest()
        request.ik_request.group_name = self.arm_group
        request.ik_request.ik_link_name = self.eef_link
        request.ik_request.pose_stamped = target_pose
        request.ik_request.timeout = rospy.Duration(self.ik_timeout_sec)
        request.ik_request.avoid_collisions = False
        request.ik_request.robot_state = RobotState()
        request.ik_request.robot_state.joint_state = self._seed_joint_state(current_joints)
        request.ik_request.robot_state.is_diff = True

        response = service(request)
        error_code = int(response.error_code.val)
        if error_code != MoveItErrorCodes.SUCCESS:
            pos = target_pose.pose.position
            quat = target_pose.pose.orientation
            rospy.logerr(
                "IK request failed: error_code=%s group=%s ik_link=%s frame=%s "
                "target_xyz=[%.6f, %.6f, %.6f] target_quat_xyzw=[%.6f, %.6f, %.6f, %.6f] "
                "seed_joint_names=%s seed_joint_positions=%s",
                error_code,
                self.arm_group,
                self.eef_link,
                target_pose.header.frame_id,
                pos.x,
                pos.y,
                pos.z,
                quat.x,
                quat.y,
                quat.z,
                quat.w,
                request.ik_request.robot_state.joint_state.name,
                [
                    float(v)
                    for v in request.ik_request.robot_state.joint_state.position
                ],
            )
            raise RuntimeError(f"IK failed with MoveIt error code {error_code}")
        return response.solution.joint_state

    def _make_trajectory(self, positions: np.ndarray) -> JointTrajectory:
        msg = JointTrajectory()
        msg.joint_names = list(self.active_joint_names)
        point = JointTrajectoryPoint()
        point.positions = positions.astype(float).tolist()
        point.velocities = [0.0] * len(self.active_joint_names)
        point.time_from_start = rospy.Duration(self.time_from_start_sec)
        msg.points = [point]
        return msg

    def convert(self, action: Sequence[float]) -> ArmCommandConversionResult:
        joint_state = self._wait_for_joint_state()
        current_joints, missing = values_for_names(
            self._map_joint_positions(joint_state), self.active_joint_names
        )
        if missing:
            raise RuntimeError(f"missing active arm joints in {self.joint_states_topic}: {missing}")

        current_pose, target_pose, clipped_xyz, planning_xyz = self._target_pose_from_action(action)
        ik_solution = self._request_ik(target_pose, current_joints)
        ik_positions, missing_ik = values_for_names(
            self._map_joint_positions(ik_solution), self.active_joint_names
        )
        if missing_ik:
            raise RuntimeError(f"IK solution missing active arm joints: {missing_ik}")

        raw_delta = ik_positions - current_joints
        clipped_delta = np.clip(raw_delta, -self.max_joint_delta, self.max_joint_delta)
        command_positions = current_joints + clipped_delta
        trajectory = self._make_trajectory(command_positions)
        return ArmCommandConversionResult(
            planning_frame=current_pose.header.frame_id,
            action_frame=self.action_frame,
            current_eef_xyz=[
                float(current_pose.pose.position.x),
                float(current_pose.pose.position.y),
                float(current_pose.pose.position.z),
            ],
            target_eef_xyz=[
                float(target_pose.pose.position.x),
                float(target_pose.pose.position.y),
                float(target_pose.pose.position.z),
            ],
            clipped_xyz_action_frame=clipped_xyz.astype(float).tolist(),
            clipped_xyz_planning_frame=planning_xyz.astype(float).tolist(),
            active_joint_names=list(self.active_joint_names),
            current_joints=current_joints.astype(float).tolist(),
            ik_joints=ik_positions.astype(float).tolist(),
            raw_joint_delta=raw_delta.astype(float).tolist(),
            clipped_joint_delta=clipped_delta.astype(float).tolist(),
            command_positions=command_positions.astype(float).tolist(),
            trajectory=trajectory,
        )

    def _wait_for_command_subscriber(self) -> None:
        deadline = rospy.Time.now() + rospy.Duration(self.command_connection_timeout_sec)
        while not rospy.is_shutdown() and rospy.Time.now() < deadline:
            if self.command_pub.get_num_connections() > 0:
                return
            rospy.sleep(0.05)
        raise RuntimeError(f"timed out waiting for subscriber on {self.arm_command_topic}")

    def execute(self, action: Sequence[float]) -> ArmCommandConversionResult:
        result = self.convert(action)
        self._wait_for_command_subscriber()
        self.command_pub.publish(result.trajectory)
        rospy.sleep(self.post_publish_sleep_sec)
        return result
