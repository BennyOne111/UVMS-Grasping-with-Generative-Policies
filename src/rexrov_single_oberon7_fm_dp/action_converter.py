from typing import Iterable, Sequence

import numpy as np
from std_msgs.msg import Float64MultiArray, MultiArrayDimension


ACTION_FIELDS = ("dx", "dy", "dz", "droll", "dpitch", "dyaw", "gripper_cmd")
ACTION_DIM = 7


def make_action(
    delta_xyz_rpy: Sequence[float],
    gripper_cmd: float,
    max_linear_step: float = 0.05,
    max_angular_step: float = 0.25,
) -> np.ndarray:
    values = np.asarray(list(delta_xyz_rpy), dtype=np.float64)
    if values.shape != (6,):
        raise ValueError(f"delta_xyz_rpy must have shape (6,), got {values.shape}")
    values[:3] = np.clip(values[:3], -max_linear_step, max_linear_step)
    values[3:] = np.clip(values[3:], -max_angular_step, max_angular_step)
    gripper = float(np.clip(gripper_cmd, 0.0, 1.0))
    return np.concatenate([values, np.array([gripper], dtype=np.float64)])


def action_to_msg(action: Sequence[float]) -> Float64MultiArray:
    values = np.asarray(action, dtype=np.float64)
    if values.shape != (ACTION_DIM,):
        raise ValueError(f"action must have shape ({ACTION_DIM},), got {values.shape}")
    msg = Float64MultiArray()
    msg.layout.dim.append(
        MultiArrayDimension(label="action_ee_delta", size=ACTION_DIM, stride=ACTION_DIM)
    )
    msg.data = values.tolist()
    return msg


def msg_to_action(msg: Float64MultiArray) -> np.ndarray:
    values = np.asarray(msg.data, dtype=np.float64)
    if values.shape[0] < ACTION_DIM:
        return np.full((ACTION_DIM,), np.nan, dtype=np.float64)
    return values[:ACTION_DIM].astype(np.float64)
