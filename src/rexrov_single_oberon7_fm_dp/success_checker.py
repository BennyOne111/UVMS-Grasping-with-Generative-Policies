from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class SuccessResult:
    success: bool
    reason: str
    distance_m: Optional[float] = None


def check_simple_success(
    gripper_cmd: float,
    target_pose: Optional[np.ndarray],
    eef_pose: Optional[np.ndarray],
    distance_threshold: float,
) -> SuccessResult:
    if gripper_cmd < 0.5:
        return SuccessResult(False, "gripper_not_closed")
    if target_pose is None or not np.isfinite(target_pose).all():
        return SuccessResult(False, "target_pose_unavailable")
    if eef_pose is None or not np.isfinite(eef_pose).all():
        return SuccessResult(False, "eef_pose_unavailable")
    distance = float(np.linalg.norm(np.asarray(eef_pose[:3]) - np.asarray(target_pose[:3])))
    if distance <= distance_threshold:
        return SuccessResult(True, "closed_gripper_and_eef_near_target", distance)
    return SuccessResult(False, "eef_too_far_from_target", distance)
