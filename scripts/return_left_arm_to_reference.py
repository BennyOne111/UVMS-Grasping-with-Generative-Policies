#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, Sequence

import numpy as np


PACKAGE_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

import rospy  # noqa: E402
from sensor_msgs.msg import JointState  # noqa: E402
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint  # noqa: E402

from rexrov_single_oberon7_fm_dp.ros_interface import (  # noqa: E402
    joint_state_maps,
    values_for_names,
)


def _metadata(data: Dict[str, np.ndarray]) -> Dict[str, object]:
    raw = data["metadata_json"]
    if isinstance(raw, np.ndarray):
        raw = raw.item()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(str(raw))


def _load_reference(path: Path) -> Dict[str, object]:
    with np.load(str(path), allow_pickle=False) as loaded:
        data = {key: loaded[key] for key in loaded.files}
    metadata = _metadata(data)
    joint_names = list(metadata.get("active_joint_names") or [])
    if not joint_names:
        raise ValueError(f"reference episode has no active_joint_names metadata: {path}")
    joints = np.asarray(data["active_joint_positions"], dtype=np.float64)
    if joints.ndim != 2 or joints.shape[0] == 0 or joints.shape[1] != len(joint_names):
        raise ValueError(f"invalid active_joint_positions shape in reference episode: {joints.shape}")
    return {
        "episode_id": metadata.get("episode_id", path.stem),
        "path": str(path),
        "active_joint_names": joint_names,
        "joint_positions": joints[0],
    }


def _joint_values(msg: JointState, names: Sequence[str]) -> np.ndarray:
    positions, _, _ = joint_state_maps(msg)
    values, missing = values_for_names(positions, names)
    if missing:
        raise RuntimeError(f"missing active joints in /joint_states: {missing}")
    return values


def _metrics(current: np.ndarray, reference: np.ndarray) -> Dict[str, float]:
    delta = reference - current
    return {
        "joint_l2_error": float(np.linalg.norm(delta)),
        "joint_max_abs_error": float(np.max(np.abs(delta))),
    }


def _make_command(names: Sequence[str], positions: np.ndarray, time_from_start_sec: float) -> JointTrajectory:
    trajectory = JointTrajectory()
    trajectory.joint_names = list(names)
    point = JointTrajectoryPoint()
    point.positions = positions.astype(float).tolist()
    point.velocities = [0.0] * len(names)
    point.time_from_start = rospy.Duration(float(time_from_start_sec))
    trajectory.points = [point]
    return trajectory


def _wait_for_subscriber(pub: rospy.Publisher, topic: str, timeout_sec: float) -> None:
    deadline = rospy.Time.now() + rospy.Duration(timeout_sec)
    while not rospy.is_shutdown() and rospy.Time.now() < deadline:
        if pub.get_num_connections() > 0:
            return
        rospy.sleep(0.05)
    raise RuntimeError(f"timed out waiting for subscriber on {topic}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Bounded left-arm return-to-reference command. "
            "Publishes only active-left JointTrajectory commands; sends no gripper command."
        )
    )
    parser.add_argument("--reference-npz", required=True)
    parser.add_argument("--joint-states-topic", default="/joint_states")
    parser.add_argument("--arm-command-topic", default="/oberon7/arm_position_l/command")
    parser.add_argument("--max-joint-delta", type=float, default=0.01)
    parser.add_argument("--time-from-start-sec", type=float, default=1.0)
    parser.add_argument("--settle-sec", type=float, default=0.25)
    parser.add_argument("--wait-timeout-sec", type=float, default=5.0)
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument("--joint-l2-tolerance", type=float, default=0.01)
    parser.add_argument("--joint-max-abs-tolerance", type=float, default=0.005)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-json", default="")
    args = parser.parse_args()

    rospy.init_node("b8_return_left_arm_to_reference", anonymous=True)
    reference = _load_reference(Path(args.reference_npz).expanduser())
    joint_names = list(reference["active_joint_names"])
    reference_joints = np.asarray(reference["joint_positions"], dtype=np.float64)

    history = []
    commands_sent = 0
    reached = False
    current = None
    command_pub = None

    for iteration in range(max(1, int(args.max_iterations))):
        joint_msg = rospy.wait_for_message(args.joint_states_topic, JointState, timeout=args.wait_timeout_sec)
        current = _joint_values(joint_msg, joint_names)
        current_metrics = _metrics(current, reference_joints)
        history.append(
            {
                "iteration": iteration,
                "joint_l2_error": current_metrics["joint_l2_error"],
                "joint_max_abs_error": current_metrics["joint_max_abs_error"],
                "command_sent": False,
            }
        )
        if (
            current_metrics["joint_l2_error"] <= args.joint_l2_tolerance
            and current_metrics["joint_max_abs_error"] <= args.joint_max_abs_tolerance
        ):
            reached = True
            break

        delta = reference_joints - current
        bounded_delta = np.clip(delta, -float(args.max_joint_delta), float(args.max_joint_delta))
        command_positions = current + bounded_delta
        history[-1]["bounded_delta"] = bounded_delta.astype(float).tolist()
        history[-1]["command_positions"] = command_positions.astype(float).tolist()
        if args.dry_run:
            break
        if command_pub is None:
            command_pub = rospy.Publisher(args.arm_command_topic, JointTrajectory, queue_size=1, latch=False)
            _wait_for_subscriber(command_pub, args.arm_command_topic, args.wait_timeout_sec)
        command_pub.publish(_make_command(joint_names, command_positions, args.time_from_start_sec))
        history[-1]["command_sent"] = True
        commands_sent += 1
        rospy.sleep(max(0.0, float(args.time_from_start_sec) + float(args.settle_sec)))

    if current is None:
        raise RuntimeError("failed to read any joint state")

    final_msg = rospy.wait_for_message(args.joint_states_topic, JointState, timeout=args.wait_timeout_sec)
    final_joints = _joint_values(final_msg, joint_names)
    final_metrics = _metrics(final_joints, reference_joints)
    reached = bool(
        final_metrics["joint_l2_error"] <= args.joint_l2_tolerance
        and final_metrics["joint_max_abs_error"] <= args.joint_max_abs_tolerance
    )

    report = {
        "tool": "return_left_arm_to_reference",
        "reference": {
            "episode_id": reference["episode_id"],
            "path": reference["path"],
        },
        "active_joint_names": joint_names,
        "reference_joint_positions": reference_joints.astype(float).tolist(),
        "final_joint_positions": final_joints.astype(float).tolist(),
        "thresholds": {
            "max_joint_delta": args.max_joint_delta,
            "joint_l2_tolerance": args.joint_l2_tolerance,
            "joint_max_abs_tolerance": args.joint_max_abs_tolerance,
        },
        "dry_run": bool(args.dry_run),
        "reached": reached,
        "commands_sent": commands_sent,
        "gripper_commands_sent": False,
        "final_metrics": final_metrics,
        "history": history,
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output_json:
        output_path = Path(args.output_json).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    if args.dry_run:
        return 0
    return 0 if reached else 2


if __name__ == "__main__":
    raise SystemExit(main())
