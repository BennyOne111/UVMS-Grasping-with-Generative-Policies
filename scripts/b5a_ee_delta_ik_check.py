#!/usr/bin/env python3

from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple


PACKAGE_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

import numpy as np
import moveit_commander
import rospy
import tf
from geometry_msgs.msg import PoseStamped
from moveit_msgs.msg import MoveItErrorCodes, RobotState
from moveit_msgs.srv import GetPositionIK, GetPositionIKRequest
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


def _as_string_list(value) -> List[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


class B5AActionConverterCheck:
    def __init__(self) -> None:
        self.joint_states_topic = rospy.get_param("~joint_states_topic", "/joint_states")
        self.arm_command_topic = rospy.get_param(
            "~arm_command_topic", "/oberon7/arm_position_l/command"
        )
        self.compute_ik_service = rospy.get_param("~compute_ik_service", "/compute_ik")
        self.arm_group = rospy.get_param("~arm_group", "arm_l")
        self.eef_link = rospy.get_param("~eef_link", "oberon7_l/end_effector")
        self.use_moveit_commander_pose = bool(rospy.get_param("~use_moveit_commander_pose", True))
        self.ik_pose_frames = _as_string_list(
            rospy.get_param("~ik_pose_frames", "rexrov/base_link,oberon7_l/base,world")
        )
        self.active_joint_names = list(rospy.get_param("~active_joint_names", DEFAULT_ARM_JOINTS))
        self.execute = bool(rospy.get_param("~execute", False))

        self.delta_xyz = np.asarray(
            [
                float(rospy.get_param("~delta_x", 0.005)),
                float(rospy.get_param("~delta_y", 0.0)),
                float(rospy.get_param("~delta_z", 0.0)),
            ],
            dtype=np.float64,
        )
        self.delta_rpy = np.asarray(
            [
                float(rospy.get_param("~droll", 0.0)),
                float(rospy.get_param("~dpitch", 0.0)),
                float(rospy.get_param("~dyaw", 0.0)),
            ],
            dtype=np.float64,
        )
        self.max_linear_step = float(rospy.get_param("~max_linear_step", 0.005))
        self.max_angular_step = float(rospy.get_param("~max_angular_step", 0.05))
        self.max_joint_delta = float(rospy.get_param("~max_joint_delta", 0.01))
        self.time_from_start_sec = float(rospy.get_param("~time_from_start_sec", 3.0))
        self.ik_timeout_sec = float(rospy.get_param("~ik_timeout_sec", 2.0))
        self.wait_timeout_sec = float(rospy.get_param("~wait_timeout_sec", 10.0))
        self.command_connection_timeout_sec = float(
            rospy.get_param("~command_connection_timeout_sec", 5.0)
        )
        self.post_publish_sleep_sec = float(rospy.get_param("~post_publish_sleep_sec", 0.5))

        self.tf_listener = tf.TransformListener()
        self.move_group = None
        if self.use_moveit_commander_pose:
            moveit_commander.roscpp_initialize([])
            self.move_group = moveit_commander.MoveGroupCommander(self.arm_group)
            self.move_group.set_end_effector_link(self.eef_link)
        self.command_pub = rospy.Publisher(
            self.arm_command_topic, JointTrajectory, queue_size=1, latch=False
        )

    @staticmethod
    def _map_joint_positions(msg: JointState) -> Dict[str, float]:
        positions, _, _ = joint_state_maps(msg)
        return positions

    def _wait_for_joint_state(self) -> JointState:
        return rospy.wait_for_message(
            self.joint_states_topic, JointState, timeout=self.wait_timeout_sec
        )

    def _lookup_current_eef_pose(self, frame: str) -> PoseStamped:
        deadline = rospy.Time.now() + rospy.Duration(self.wait_timeout_sec)
        while not rospy.is_shutdown() and rospy.Time.now() < deadline:
            try:
                translation, quaternion = self.tf_listener.lookupTransform(
                    frame, self.eef_link, rospy.Time(0)
                )
                pose = PoseStamped()
                pose.header.frame_id = frame
                pose.header.stamp = rospy.Time.now()
                pose.pose.position.x = translation[0]
                pose.pose.position.y = translation[1]
                pose.pose.position.z = translation[2]
                pose.pose.orientation.x = quaternion[0]
                pose.pose.orientation.y = quaternion[1]
                pose.pose.orientation.z = quaternion[2]
                pose.pose.orientation.w = quaternion[3]
                return pose
            except (
                tf.Exception,
                tf.LookupException,
                tf.ConnectivityException,
                tf.ExtrapolationException,
            ) as exc:
                last_error = exc
                rospy.sleep(0.1)
        raise RuntimeError(
            f"timed out waiting for TF {frame} -> {self.eef_link}: {last_error}"
        )

    def _target_pose_from_delta(self, current: PoseStamped, stamp_zero: bool = False) -> PoseStamped:
        clipped_xyz = np.clip(self.delta_xyz, -self.max_linear_step, self.max_linear_step)
        clipped_rpy = np.clip(self.delta_rpy, -self.max_angular_step, self.max_angular_step)

        target = PoseStamped()
        target.header.frame_id = current.header.frame_id
        target.header.stamp = rospy.Time(0) if stamp_zero else rospy.Time.now()
        target.pose.position.x = current.pose.position.x + float(clipped_xyz[0])
        target.pose.position.y = current.pose.position.y + float(clipped_xyz[1])
        target.pose.position.z = current.pose.position.z + float(clipped_xyz[2])

        current_q = [
            current.pose.orientation.x,
            current.pose.orientation.y,
            current.pose.orientation.z,
            current.pose.orientation.w,
        ]
        delta_q = tf.transformations.quaternion_from_euler(*clipped_rpy.tolist())
        target_q = tf.transformations.quaternion_multiply(current_q, delta_q)
        target_q = target_q / max(np.linalg.norm(target_q), 1e-12)
        target.pose.orientation.x = float(target_q[0])
        target.pose.orientation.y = float(target_q[1])
        target.pose.orientation.z = float(target_q[2])
        target.pose.orientation.w = float(target_q[3])
        return target

    def _request_ik(self, joint_state: JointState, target_pose: PoseStamped):
        rospy.wait_for_service(self.compute_ik_service, timeout=self.wait_timeout_sec)
        service = rospy.ServiceProxy(self.compute_ik_service, GetPositionIK)

        request = GetPositionIKRequest()
        request.ik_request.group_name = self.arm_group
        request.ik_request.ik_link_name = self.eef_link
        request.ik_request.pose_stamped = target_pose
        request.ik_request.timeout = rospy.Duration(self.ik_timeout_sec)
        request.ik_request.avoid_collisions = False
        request.ik_request.robot_state = RobotState()
        request.ik_request.robot_state.joint_state = joint_state
        request.ik_request.robot_state.is_diff = True

        return service(request)

    def _moveit_current_pose_and_seed(self) -> Tuple[PoseStamped, JointState]:
        if self.move_group is None:
            raise RuntimeError("MoveGroupCommander is disabled")
        planning_frame = self.move_group.get_planning_frame()
        self.move_group.set_pose_reference_frame(planning_frame)
        current_pose = self.move_group.get_current_pose(self.eef_link)
        current_pose.header.frame_id = planning_frame
        current_pose.header.stamp = rospy.Time(0)
        seed = JointState()
        seed.name = list(self.move_group.get_active_joints())
        seed.position = list(self.move_group.get_current_joint_values())
        return current_pose, seed

    def _solve_ik_with_moveit_commander_pose(
        self,
    ) -> Tuple[str, PoseStamped, PoseStamped, JointState, List[str]]:
        current_pose, seed_joint_state = self._moveit_current_pose_and_seed()
        target_pose = self._target_pose_from_delta(current_pose, stamp_zero=True)
        response = self._request_ik(seed_joint_state, target_pose)
        error_code = int(response.error_code.val)
        frame = current_pose.header.frame_id
        attempts = [f"moveit_commander:{frame}: error_code={error_code}"]
        if error_code != MoveItErrorCodes.SUCCESS:
            raise RuntimeError(f"MoveGroupCommander seed IK failed: {attempts}")
        return frame, current_pose, target_pose, response.solution.joint_state, attempts

    def _solve_ik_with_frame_candidates(
        self, joint_state: JointState
    ) -> Tuple[str, PoseStamped, PoseStamped, JointState, List[str]]:
        attempts = []
        last_error: Optional[Exception] = None
        for frame in self.ik_pose_frames:
            try:
                current_pose = self._lookup_current_eef_pose(frame)
                target_pose = self._target_pose_from_delta(current_pose, stamp_zero=True)
                response = self._request_ik(joint_state, target_pose)
                error_code = int(response.error_code.val)
                attempts.append(f"{frame}: error_code={error_code}")
                if error_code == MoveItErrorCodes.SUCCESS:
                    return frame, current_pose, target_pose, response.solution.joint_state, attempts
            except Exception as exc:
                last_error = exc
                attempts.append(f"{frame}: exception={exc}")
        if last_error is not None:
            raise RuntimeError(f"IK failed for all candidate frames: {attempts}") from last_error
        raise RuntimeError(f"IK failed for all candidate frames: {attempts}")

    def _solve_ik(self, joint_state: JointState) -> Tuple[str, PoseStamped, PoseStamped, JointState, List[str]]:
        attempts = []
        if self.use_moveit_commander_pose:
            try:
                return self._solve_ik_with_moveit_commander_pose()
            except Exception as exc:
                attempts.append(str(exc))
        try:
            frame, current_pose, target_pose, ik_solution, frame_attempts = (
                self._solve_ik_with_frame_candidates(joint_state)
            )
            return frame, current_pose, target_pose, ik_solution, attempts + frame_attempts
        except Exception as exc:
            attempts.append(str(exc))
            raise RuntimeError(f"IK failed for all strategies: {attempts}") from exc

    def _make_trajectory(self, positions: np.ndarray) -> JointTrajectory:
        msg = JointTrajectory()
        msg.joint_names = list(self.active_joint_names)
        point = JointTrajectoryPoint()
        point.positions = positions.astype(float).tolist()
        point.velocities = [0.0] * len(self.active_joint_names)
        point.time_from_start = rospy.Duration(self.time_from_start_sec)
        msg.points = [point]
        return msg

    def _wait_for_command_subscriber(self) -> None:
        deadline = rospy.Time.now() + rospy.Duration(self.command_connection_timeout_sec)
        while not rospy.is_shutdown() and rospy.Time.now() < deadline:
            if self.command_pub.get_num_connections() > 0:
                return
            rospy.sleep(0.05)
        raise RuntimeError(
            f"timed out waiting for subscriber on {self.arm_command_topic}"
        )

    def run(self) -> None:
        joint_state = self._wait_for_joint_state()
        position_map = self._map_joint_positions(joint_state)
        current_joints, missing = values_for_names(position_map, self.active_joint_names)
        if missing:
            raise RuntimeError(f"missing active arm joints in {self.joint_states_topic}: {missing}")

        ik_frame, current_pose, target_pose, ik_solution, ik_attempts = self._solve_ik(joint_state)
        ik_positions, missing_ik = values_for_names(
            self._map_joint_positions(ik_solution), self.active_joint_names
        )
        if missing_ik:
            raise RuntimeError(f"IK solution missing active arm joints: {missing_ik}")

        raw_delta = ik_positions - current_joints
        clipped_delta = np.clip(raw_delta, -self.max_joint_delta, self.max_joint_delta)
        command_positions = current_joints + clipped_delta
        trajectory = self._make_trajectory(command_positions)

        rospy.loginfo("B5a IK frame attempts: %s", ik_attempts)
        rospy.loginfo("B5a selected pose frame: %s", ik_frame)
        rospy.loginfo(
            "B5a current eef xyz: [%.6f, %.6f, %.6f]",
            current_pose.pose.position.x,
            current_pose.pose.position.y,
            current_pose.pose.position.z,
        )
        rospy.loginfo(
            "B5a target eef xyz:  [%.6f, %.6f, %.6f]",
            target_pose.pose.position.x,
            target_pose.pose.position.y,
            target_pose.pose.position.z,
        )
        rospy.loginfo("B5a active joints: %s", self.active_joint_names)
        rospy.loginfo("B5a current joints: %s", current_joints.tolist())
        rospy.loginfo("B5a IK joints:      %s", ik_positions.tolist())
        rospy.loginfo("B5a raw joint delta:     %s", raw_delta.tolist())
        rospy.loginfo("B5a clipped joint delta: %s", clipped_delta.tolist())
        rospy.loginfo("B5a command positions:   %s", command_positions.tolist())
        rospy.loginfo("B5a execute: %s", self.execute)

        if self.execute:
            self._wait_for_command_subscriber()
            self.command_pub.publish(trajectory)
            rospy.loginfo("B5a published JointTrajectory to %s", self.arm_command_topic)
            rospy.sleep(self.post_publish_sleep_sec)
        else:
            rospy.loginfo("B5a dry-run only; no JointTrajectory was published")


def main() -> int:
    rospy.init_node("b5a_ee_delta_ik_check")
    try:
        B5AActionConverterCheck().run()
    except Exception as exc:
        rospy.logerr("B5a EE-delta IK check failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
