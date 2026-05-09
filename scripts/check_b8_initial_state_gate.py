#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Dict, Sequence

import numpy as np


PACKAGE_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

import rospy  # noqa: E402
import tf  # noqa: E402
from gazebo_msgs.msg import ModelStates  # noqa: E402
from nav_msgs.msg import Odometry  # noqa: E402
from sensor_msgs.msg import JointState  # noqa: E402

from rexrov_single_oberon7_fm_dp.ros_interface import (  # noqa: E402
    joint_state_maps,
    model_pose_from_states,
    values_for_names,
)


def _metadata(data: Dict[str, np.ndarray]) -> Dict[str, object]:
    raw = data["metadata_json"]
    if isinstance(raw, np.ndarray):
        raw = raw.item()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(str(raw))


def _transform_points_world_to_base(points_world: np.ndarray, base_pose: np.ndarray) -> np.ndarray:
    output = np.zeros_like(points_world, dtype=np.float64)
    for index in range(points_world.shape[0]):
        world_from_base = tf.transformations.translation_matrix(base_pose[index, :3])
        world_from_base = np.dot(
            world_from_base,
            tf.transformations.quaternion_matrix(base_pose[index, 3:7]),
        )
        base_from_world = np.linalg.inv(world_from_base)
        point_world = np.asarray([points_world[index, 0], points_world[index, 1], points_world[index, 2], 1.0])
        output[index] = np.dot(base_from_world, point_world)[:3]
    return output


def _load_reference(path: Path) -> Dict[str, object]:
    with np.load(str(path), allow_pickle=False) as loaded:
        data = {key: loaded[key] for key in loaded.files}
    metadata = _metadata(data)
    joint_names = list(metadata.get("active_joint_names") or [])
    if not joint_names:
        raise ValueError(f"reference episode has no active_joint_names metadata: {path}")

    base_pose = np.asarray(data["base_pose"], dtype=np.float64)
    target_pose = np.asarray(data["target_pose"], dtype=np.float64)
    eef_pose = np.asarray(data["eef_pose"], dtype=np.float64)
    joints = np.asarray(data["active_joint_positions"], dtype=np.float64)
    target_base = _transform_points_world_to_base(target_pose[:, :3], base_pose)
    eef_base = _transform_points_world_to_base(eef_pose[:, :3], base_pose)
    relative_base = target_base - eef_base

    return {
        "episode_id": metadata.get("episode_id", path.stem),
        "path": str(path),
        "active_joint_names": joint_names,
        "joint_positions": joints[0],
        "base_xyz": base_pose[0, :3],
        "target_base_xyz": target_base[0],
        "eef_base_xyz": eef_base[0],
        "relative_base_xyz": relative_base[0],
        "initial_distance": float(np.linalg.norm(relative_base[0])),
    }


def _live_eef_base(tf_listener: tf.TransformListener, base_frame: str, eef_frame: str, timeout_sec: float) -> np.ndarray:
    deadline = time.monotonic() + timeout_sec
    last_error = None
    while not rospy.is_shutdown() and time.monotonic() < deadline:
        try:
            translation, _ = tf_listener.lookupTransform(base_frame, eef_frame, rospy.Time(0))
            return np.asarray(translation, dtype=np.float64)
        except (
            tf.Exception,
            tf.LookupException,
            tf.ConnectivityException,
            tf.ExtrapolationException,
        ) as exc:
            last_error = exc
            rospy.sleep(0.05)
    raise RuntimeError(f"failed to read TF {base_frame}->{eef_frame}: {last_error}")


def _live_target_base(
    model_states: ModelStates,
    odom: Odometry,
    target_model_name: str,
) -> np.ndarray:
    target_pose = model_pose_from_states(model_states, target_model_name)
    if target_pose is None:
        raise RuntimeError(f"target model {target_model_name!r} not present in /gazebo/model_states")
    base_pose = np.asarray(
        [
            odom.pose.pose.position.x,
            odom.pose.pose.position.y,
            odom.pose.pose.position.z,
            odom.pose.pose.orientation.x,
            odom.pose.pose.orientation.y,
            odom.pose.pose.orientation.z,
            odom.pose.pose.orientation.w,
        ],
        dtype=np.float64,
    )
    return _transform_points_world_to_base(target_pose[:3].reshape(1, 3), base_pose.reshape(1, 7))[0]


def _joint_values(msg: JointState, names: Sequence[str]) -> np.ndarray:
    positions, _, _ = joint_state_maps(msg)
    values, missing = values_for_names(positions, names)
    if missing:
        raise RuntimeError(f"missing active joints in /joint_states: {missing}")
    return values


def _pass(value: float, threshold: float) -> bool:
    return bool(np.isfinite(value) and value <= threshold)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only B8 initial-state gate. It reads live ROS state and sends no commands."
    )
    parser.add_argument("--reference-npz", required=True)
    parser.add_argument("--target-model-name", default="cylinder_target")
    parser.add_argument("--joint-states-topic", default="/joint_states")
    parser.add_argument("--base-odom-topic", default="/rexrov/pose_gt")
    parser.add_argument("--model-states-topic", default="/gazebo/model_states")
    parser.add_argument("--base-frame", default="rexrov/base_link")
    parser.add_argument("--eef-frame", default="oberon7_l/end_effector")
    parser.add_argument("--timeout-sec", type=float, default=5.0)
    parser.add_argument(
        "--skip-target-checks",
        action="store_true",
        help="Only check active-left joints and EEF/base pose; do not require a live target model.",
    )
    parser.add_argument("--joint-l2-threshold", type=float, default=0.02)
    parser.add_argument("--joint-max-abs-threshold", type=float, default=0.01)
    parser.add_argument("--eef-base-drift-threshold", type=float, default=0.02)
    parser.add_argument(
        "--target-base-drift-threshold",
        type=float,
        default=-1.0,
        help=(
            "Optional strict target drift threshold. Negative disables this "
            "check for backward-compatible gate runs."
        ),
    )
    parser.add_argument("--relative-base-drift-threshold", type=float, default=0.01)
    parser.add_argument("--initial-distance-max", type=float, default=0.115)
    parser.add_argument("--output-json", default="")
    args = parser.parse_args()

    rospy.init_node("b8_initial_state_gate", anonymous=True)
    reference = _load_reference(Path(args.reference_npz).expanduser())

    joint_msg = rospy.wait_for_message(args.joint_states_topic, JointState, timeout=args.timeout_sec)
    tf_listener = tf.TransformListener()
    rospy.sleep(0.2)

    joint_names = list(reference["active_joint_names"])
    live_joints = _joint_values(joint_msg, joint_names)
    live_eef_base = _live_eef_base(tf_listener, args.base_frame, args.eef_frame, args.timeout_sec)

    target_checks_skipped = bool(args.skip_target_checks)
    if target_checks_skipped:
        live_target_base = np.full((3,), np.nan, dtype=np.float64)
        live_relative_base = np.full((3,), np.nan, dtype=np.float64)
    else:
        odom_msg = rospy.wait_for_message(args.base_odom_topic, Odometry, timeout=args.timeout_sec)
        model_msg = rospy.wait_for_message(args.model_states_topic, ModelStates, timeout=args.timeout_sec)
        live_target_base = _live_target_base(model_msg, odom_msg, args.target_model_name)
        live_relative_base = live_target_base - live_eef_base

    joint_delta = live_joints - np.asarray(reference["joint_positions"], dtype=np.float64)
    metrics = {
        "joint_l2_drift": float(np.linalg.norm(joint_delta)),
        "joint_max_abs_drift": float(np.max(np.abs(joint_delta))),
        "eef_base_drift": float(
            np.linalg.norm(live_eef_base - np.asarray(reference["eef_base_xyz"], dtype=np.float64))
        ),
        "target_base_drift": None
        if target_checks_skipped
        else float(np.linalg.norm(live_target_base - np.asarray(reference["target_base_xyz"], dtype=np.float64))),
        "relative_base_drift": None
        if target_checks_skipped
        else float(np.linalg.norm(live_relative_base - np.asarray(reference["relative_base_xyz"], dtype=np.float64))),
        "initial_distance": None if target_checks_skipped else float(np.linalg.norm(live_relative_base)),
    }
    checks = {
        "joint_l2_ok": _pass(metrics["joint_l2_drift"], args.joint_l2_threshold),
        "joint_max_abs_ok": _pass(metrics["joint_max_abs_drift"], args.joint_max_abs_threshold),
        "eef_base_drift_ok": _pass(metrics["eef_base_drift"], args.eef_base_drift_threshold),
        "target_base_drift_ok": True
        if target_checks_skipped or args.target_base_drift_threshold < 0.0
        else _pass(float(metrics["target_base_drift"]), args.target_base_drift_threshold),
        "relative_base_drift_ok": True
        if target_checks_skipped
        else _pass(float(metrics["relative_base_drift"]), args.relative_base_drift_threshold),
        "initial_distance_ok": True
        if target_checks_skipped
        else _pass(float(metrics["initial_distance"]), args.initial_distance_max),
    }
    passed = bool(all(checks.values()))
    report = {
        "gate": "b8_initial_state_gate",
        "passed": passed,
        "reference": {
            "episode_id": reference["episode_id"],
            "path": reference["path"],
            "initial_distance": reference["initial_distance"],
        },
        "target_model_name": args.target_model_name,
        "target_checks_skipped": target_checks_skipped,
        "active_joint_names": joint_names,
        "live": {
            "joint_positions": live_joints.astype(float).tolist(),
            "eef_base_xyz": live_eef_base.astype(float).tolist(),
            "target_base_xyz": None if target_checks_skipped else live_target_base.astype(float).tolist(),
            "relative_base_xyz": None if target_checks_skipped else live_relative_base.astype(float).tolist(),
        },
        "thresholds": {
            "joint_l2_threshold": args.joint_l2_threshold,
            "joint_max_abs_threshold": args.joint_max_abs_threshold,
            "eef_base_drift_threshold": args.eef_base_drift_threshold,
            "target_base_drift_threshold": args.target_base_drift_threshold,
            "relative_base_drift_threshold": args.relative_base_drift_threshold,
            "initial_distance_max": args.initial_distance_max,
        },
        "metrics": metrics,
        "checks": checks,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output_json:
        output_path = Path(args.output_json).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
