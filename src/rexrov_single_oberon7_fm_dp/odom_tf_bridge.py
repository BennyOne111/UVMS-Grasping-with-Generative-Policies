from dataclasses import dataclass
from typing import Optional

import rospy
import tf
from nav_msgs.msg import Odometry


@dataclass
class OdomTfBridgeConfig:
    odom_topic: str = "/rexrov/pose_gt"
    parent_frame: str = "world"
    child_frame: str = "rexrov/base_link"
    repeat_rate_hz: float = 20.0


class OdomTfBridge:
    """Publish an odometry pose as a TF transform for MoveIt virtual joints."""

    def __init__(self, config: OdomTfBridgeConfig) -> None:
        self.config = config
        self.broadcaster = tf.TransformBroadcaster()
        self.latest_msg: Optional[Odometry] = None
        self.subscriber = rospy.Subscriber(
            self.config.odom_topic, Odometry, self._on_odom, queue_size=1
        )
        self.timer = rospy.Timer(
            rospy.Duration(1.0 / max(self.config.repeat_rate_hz, 1e-6)),
            self._on_timer,
        )

    def _on_odom(self, msg: Odometry) -> None:
        self.latest_msg = msg
        self._broadcast(msg)

    def _on_timer(self, _event) -> None:
        if self.latest_msg is not None:
            self._broadcast(self.latest_msg)

    def _broadcast(self, msg: Odometry) -> None:
        pose = msg.pose.pose
        translation = (
            pose.position.x,
            pose.position.y,
            pose.position.z,
        )
        rotation = (
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w,
        )
        self.broadcaster.sendTransform(
            translation,
            rotation,
            rospy.Time.now(),
            self.config.child_frame,
            self.config.parent_frame,
        )

    def run(self) -> None:
        rospy.loginfo(
            "Odom TF bridge publishing %s -> %s from %s",
            self.config.parent_frame,
            self.config.child_frame,
            self.config.odom_topic,
        )
        rospy.spin()


def config_from_ros_params() -> OdomTfBridgeConfig:
    return OdomTfBridgeConfig(
        odom_topic=rospy.get_param("~odom_topic", "/rexrov/pose_gt"),
        parent_frame=rospy.get_param("~parent_frame", "world"),
        child_frame=rospy.get_param("~child_frame", "rexrov/base_link"),
        repeat_rate_hz=float(rospy.get_param("~repeat_rate_hz", 20.0)),
    )
