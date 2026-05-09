from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import rospy
import tf
from gazebo_msgs.msg import ModelState, ModelStates
from gazebo_msgs.srv import GetModelState, SetModelState
from nav_msgs.msg import Odometry
from tf.transformations import quaternion_matrix


@dataclass
class BaseRelativeTargetConfig:
    target_model_name: str = "cylinder_target"
    base_model_name: str = "rexrov"
    base_odom_topic: str = "/rexrov/pose_gt"
    model_states_topic: str = "/gazebo/model_states"
    base_frame: str = "rexrov/base_link"
    eef_frame: str = "oberon7_l/end_effector"
    get_model_state_service: str = "/gazebo/get_model_state"
    set_model_state_service: str = "/gazebo/set_model_state"
    rate_hz: float = 5.0
    offset_xyz: Optional[List[float]] = None
    wait_timeout_sec: float = 5.0
    max_base_pose_age_sec: float = 0.25
    prefer_model_states_base_pose: bool = False

    def __post_init__(self) -> None:
        if self.offset_xyz is None:
            self.offset_xyz = [0.10, 0.0, 0.04]


class BaseRelativeTargetUpdater:
    """Keep a Gazebo target at a fixed base-frame pose during short smoke tests."""

    def __init__(self, config: BaseRelativeTargetConfig) -> None:
        self.config = config
        self.listener = tf.TransformListener()
        self.get_model_state = None
        self.set_model_state = None
        self.target_base_xyz: Optional[np.ndarray] = None
        self.latest_base_pose = None
        self.latest_model_states_base_pose = None
        self.base_odom_sub = rospy.Subscriber(
            self.config.base_odom_topic,
            Odometry,
            self._base_odom_callback,
            queue_size=1,
        )
        self.model_states_sub = rospy.Subscriber(
            self.config.model_states_topic,
            ModelStates,
            self._model_states_callback,
            queue_size=1,
        )

    @staticmethod
    def _pose_from_odom(odom: Odometry):
        base_position = np.array(
            [
                odom.pose.pose.position.x,
                odom.pose.pose.position.y,
                odom.pose.pose.position.z,
            ],
            dtype=np.float64,
        )
        q = odom.pose.pose.orientation
        base_rotation = quaternion_matrix([q.x, q.y, q.z, q.w])[:3, :3]
        return odom.header.stamp.to_sec(), base_position, base_rotation

    def _base_odom_callback(self, odom: Odometry) -> None:
        self.latest_base_pose = self._pose_from_odom(odom)

    @staticmethod
    def _pose_from_model_state(pose):
        base_position = np.array(
            [
                pose.position.x,
                pose.position.y,
                pose.position.z,
            ],
            dtype=np.float64,
        )
        q = pose.orientation
        base_rotation = quaternion_matrix([q.x, q.y, q.z, q.w])[:3, :3]
        return rospy.Time.now().to_sec(), base_position, base_rotation

    def _model_states_callback(self, msg: ModelStates) -> None:
        try:
            index = msg.name.index(self.config.base_model_name)
        except ValueError:
            return
        self.latest_model_states_base_pose = self._pose_from_model_state(
            msg.pose[index]
        )

    def _base_pose_is_fresh(self, pose) -> bool:
        stamp_sec, _, _ = pose
        now_sec = rospy.Time.now().to_sec()
        if stamp_sec <= 0.0 or now_sec <= 0.0:
            return True
        return (now_sec - stamp_sec) <= self.config.max_base_pose_age_sec

    def _base_pose(self):
        deadline = rospy.Time.now() + rospy.Duration(self.config.wait_timeout_sec)
        while not rospy.is_shutdown() and rospy.Time.now() < deadline:
            pose = (
                self.latest_model_states_base_pose
                if self.config.prefer_model_states_base_pose
                else self.latest_base_pose
            )
            if pose is not None and self._base_pose_is_fresh(pose):
                return pose
            rospy.sleep(0.005)
        if self.config.prefer_model_states_base_pose:
            raise RuntimeError(
                f"fresh base model state for {self.config.base_model_name!r} "
                f"unavailable on {self.config.model_states_topic!r} within "
                f"{self.config.wait_timeout_sec:.3f} s"
            )
        raise RuntimeError(
            f"fresh base odom unavailable on {self.config.base_odom_topic!r} "
            f"within {self.config.wait_timeout_sec:.3f} s"
        )

    def _eef_base_xyz(self) -> np.ndarray:
        self.listener.waitForTransform(
            self.config.base_frame,
            self.config.eef_frame,
            rospy.Time(0),
            rospy.Duration(self.config.wait_timeout_sec),
        )
        trans, _ = self.listener.lookupTransform(
            self.config.base_frame,
            self.config.eef_frame,
            rospy.Time(0),
        )
        return np.asarray(trans, dtype=np.float64)

    def initialize(self) -> None:
        rospy.wait_for_service(
            self.config.get_model_state_service, timeout=self.config.wait_timeout_sec
        )
        rospy.wait_for_service(
            self.config.set_model_state_service, timeout=self.config.wait_timeout_sec
        )
        self.get_model_state = rospy.ServiceProxy(
            self.config.get_model_state_service, GetModelState
        )
        self.set_model_state = rospy.ServiceProxy(
            self.config.set_model_state_service, SetModelState
        )
        self._wait_for_target_model()
        self.target_base_xyz = self._eef_base_xyz() + np.asarray(
            self.config.offset_xyz, dtype=np.float64
        )
        rospy.loginfo(
            "B5d base-relative target initialized: model=%s base_frame=%s "
            "eef_frame=%s base_pose_source=%s target_base_xyz=%s",
            self.config.target_model_name,
            self.config.base_frame,
            self.config.eef_frame,
            (
                "gazebo_model_states"
                if self.config.prefer_model_states_base_pose
                else "odom"
            ),
            self.target_base_xyz.astype(float).tolist(),
        )

    def _wait_for_target_model(self) -> None:
        deadline = rospy.Time.now() + rospy.Duration(self.config.wait_timeout_sec)
        last_status = ""
        while not rospy.is_shutdown() and rospy.Time.now() < deadline:
            response = self.get_model_state(self.config.target_model_name, "world")
            if response.success:
                return
            last_status = response.status_message
            rospy.sleep(0.05)
        raise RuntimeError(
            f"target model {self.config.target_model_name!r} is not available: {last_status}"
        )

    def _target_world_xyz(self) -> np.ndarray:
        if self.target_base_xyz is None:
            raise RuntimeError("BaseRelativeTargetUpdater.initialize() was not called")
        _, base_position, base_rotation = self._base_pose()
        return base_position + base_rotation.dot(self.target_base_xyz)

    def update_once(self):
        target_world = self._target_world_xyz()
        state = ModelState()
        state.model_name = self.config.target_model_name
        state.reference_frame = "world"
        state.pose.position.x = float(target_world[0])
        state.pose.position.y = float(target_world[1])
        state.pose.position.z = float(target_world[2])
        state.pose.orientation.w = 1.0
        response = self.set_model_state(state)
        if not response.success:
            raise RuntimeError(
                f"failed to update {self.config.target_model_name}: {response.status_message}"
            )
        return target_world

    def run(self) -> None:
        self.initialize()
        rate = rospy.Rate(self.config.rate_hz)
        while not rospy.is_shutdown():
            target_world = self.update_once()
            rospy.logdebug(
                "B5d base-relative target update: target_world_xyz=%s",
                target_world.astype(float).tolist(),
            )
            rate.sleep()


def config_from_ros_params() -> BaseRelativeTargetConfig:
    return BaseRelativeTargetConfig(
        target_model_name=rospy.get_param("~target_model_name", "cylinder_target"),
        base_model_name=rospy.get_param("~base_model_name", "rexrov"),
        base_odom_topic=rospy.get_param("~base_odom_topic", "/rexrov/pose_gt"),
        model_states_topic=rospy.get_param("~model_states_topic", "/gazebo/model_states"),
        base_frame=rospy.get_param("~base_frame", "rexrov/base_link"),
        eef_frame=rospy.get_param("~eef_frame", "oberon7_l/end_effector"),
        get_model_state_service=rospy.get_param(
            "~get_model_state_service", "/gazebo/get_model_state"
        ),
        set_model_state_service=rospy.get_param(
            "~set_model_state_service", "/gazebo/set_model_state"
        ),
        rate_hz=float(rospy.get_param("~rate_hz", 5.0)),
        offset_xyz=[
            float(rospy.get_param("~offset_x", 0.10)),
            float(rospy.get_param("~offset_y", 0.0)),
            float(rospy.get_param("~offset_z", 0.04)),
        ],
        wait_timeout_sec=float(rospy.get_param("~wait_timeout_sec", 5.0)),
        max_base_pose_age_sec=float(rospy.get_param("~max_base_pose_age_sec", 0.25)),
        prefer_model_states_base_pose=bool(
            rospy.get_param("~prefer_model_states_base_pose", False)
        ),
    )
