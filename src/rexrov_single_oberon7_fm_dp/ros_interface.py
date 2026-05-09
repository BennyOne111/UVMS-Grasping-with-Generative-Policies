from typing import Dict, Iterable, Optional, Sequence, Tuple

import numpy as np


def stamp_to_sec(stamp) -> float:
    return float(stamp.secs) + float(stamp.nsecs) * 1e-9


def pose_to_array(pose) -> np.ndarray:
    return np.array(
        [
            pose.position.x,
            pose.position.y,
            pose.position.z,
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w,
        ],
        dtype=np.float64,
    )


def twist_to_array(twist) -> np.ndarray:
    return np.array(
        [
            twist.linear.x,
            twist.linear.y,
            twist.linear.z,
            twist.angular.x,
            twist.angular.y,
            twist.angular.z,
        ],
        dtype=np.float64,
    )


def odom_to_pose_velocity(msg) -> Tuple[np.ndarray, np.ndarray]:
    return pose_to_array(msg.pose.pose), twist_to_array(msg.twist.twist)


def wrench_to_array(msg) -> np.ndarray:
    return np.array(
        [
            msg.force.x,
            msg.force.y,
            msg.force.z,
            msg.torque.x,
            msg.torque.y,
            msg.torque.z,
        ],
        dtype=np.float64,
    )


def wrench_stamped_to_array(msg) -> np.ndarray:
    return wrench_to_array(msg.wrench)


def joint_state_maps(msg) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
    positions = {name: float(value) for name, value in zip(msg.name, msg.position)}
    velocities = {name: float(value) for name, value in zip(msg.name, msg.velocity)}
    efforts = {name: float(value) for name, value in zip(msg.name, msg.effort)}
    return positions, velocities, efforts


def values_for_names(value_map: Dict[str, float], names: Sequence[str]) -> Tuple[np.ndarray, Sequence[str]]:
    values = []
    missing = []
    for name in names:
        if name in value_map:
            values.append(value_map[name])
        else:
            values.append(np.nan)
            missing.append(name)
    return np.asarray(values, dtype=np.float64), missing


def model_pose_from_states(msg, model_name: str) -> Optional[np.ndarray]:
    try:
        index = list(msg.name).index(model_name)
    except ValueError:
        return None
    return pose_to_array(msg.pose[index])


def model_twist_from_states(msg, model_name: str) -> Optional[np.ndarray]:
    try:
        index = list(msg.name).index(model_name)
    except ValueError:
        return None
    return twist_to_array(msg.twist[index])


def nan_pose() -> np.ndarray:
    return np.full((7,), np.nan, dtype=np.float64)


def nan_twist() -> np.ndarray:
    return np.full((6,), np.nan, dtype=np.float64)


def nan_action() -> np.ndarray:
    return np.full((7,), np.nan, dtype=np.float64)
