#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


def _metadata(data: Dict[str, np.ndarray]) -> Dict[str, object]:
    raw = data["metadata_json"]
    if isinstance(raw, np.ndarray):
        raw = raw.item()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(str(raw))


def _quat_to_matrix_xyzw(quat: np.ndarray) -> np.ndarray:
    x, y, z, w = [float(v) for v in quat]
    norm = np.sqrt(x * x + y * y + z * z + w * w)
    if norm <= 1e-12:
        return np.eye(3, dtype=np.float64)
    x, y, z, w = x / norm, y / norm, z / norm, w / norm
    return np.asarray(
        [
            [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
            [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
            [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def _points_world_to_base(points_world: np.ndarray, base_pose: np.ndarray) -> np.ndarray:
    converted = np.zeros_like(points_world, dtype=np.float64)
    for index in range(points_world.shape[0]):
        rotation = _quat_to_matrix_xyzw(base_pose[index, 3:7])
        converted[index] = rotation.T @ (points_world[index] - base_pose[index, :3])
    return converted


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    an = float(np.linalg.norm(a))
    bn = float(np.linalg.norm(b))
    if an <= 1e-12 or bn <= 1e-12:
        return float("nan")
    return float(np.dot(a, b) / (an * bn))


def _finite_mean(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return float("nan")
    return float(np.mean(finite))


def _round(value: float) -> float:
    if not np.isfinite(value):
        return float("nan")
    return float(value)


def _episode_direction(path: Path, threshold: float) -> Dict[str, object]:
    with np.load(str(path), allow_pickle=False) as loaded:
        data = {key: loaded[key] for key in loaded.files}
    metadata = _metadata(data)

    base_pose = np.asarray(data["base_pose"], dtype=np.float64)
    target_pose = np.asarray(data["target_pose"], dtype=np.float64)
    eef_pose = np.asarray(data["eef_pose"], dtype=np.float64)
    actions = np.asarray(data["action_ee_delta"], dtype=np.float64)

    target_base = _points_world_to_base(target_pose[:, :3], base_pose)
    eef_base = _points_world_to_base(eef_pose[:, :3], base_pose)
    relative_base = target_base - eef_base
    relative_world = target_pose[:, :3] - eef_pose[:, :3]

    distance_base = np.linalg.norm(relative_base, axis=1)
    distance_world = np.linalg.norm(relative_world, axis=1)

    eef_step_base = np.diff(eef_base, axis=0)
    target_step_base = np.diff(target_base, axis=0)
    base_step_world = np.diff(base_pose[:, :3], axis=0)
    action_xyz = actions[:-1, :3]
    relative_for_step = relative_base[:-1]
    distance_delta = np.diff(distance_base)

    eef_step_norm = np.linalg.norm(eef_step_base, axis=1)
    target_step_norm = np.linalg.norm(target_step_base, axis=1)
    base_step_norm = np.linalg.norm(base_step_world, axis=1)
    action_norm = np.linalg.norm(action_xyz, axis=1)

    eef_to_target_cosine = np.asarray(
        [_cosine(eef_step_base[index], relative_for_step[index]) for index in range(eef_step_base.shape[0])],
        dtype=np.float64,
    )
    action_to_eef_cosine = np.asarray(
        [_cosine(action_xyz[index], eef_step_base[index]) for index in range(eef_step_base.shape[0])],
        dtype=np.float64,
    )
    action_to_target_cosine = np.asarray(
        [_cosine(action_xyz[index], relative_for_step[index]) for index in range(eef_step_base.shape[0])],
        dtype=np.float64,
    )

    moving_steps = eef_step_norm > 1e-6
    commanded_steps = action_norm > 1e-9
    positive_eef_direction = eef_to_target_cosine > 0.0
    decreasing_distance = distance_delta < 0.0

    labels: List[str] = []
    if float(np.min(distance_base)) > threshold:
        labels.append("threshold_not_reached")
    if moving_steps.any() and float(np.mean(positive_eef_direction[moving_steps])) < 0.60:
        labels.append("actual_eef_not_consistently_target_directed")
    if moving_steps.any() and float(np.mean(decreasing_distance[moving_steps])) < 0.50:
        labels.append("distance_not_consistently_decreasing")
    if commanded_steps.any() and _finite_mean(action_to_eef_cosine[commanded_steps]) < 0.30:
        labels.append("action_to_eef_motion_mismatch")
    if float(np.max(target_step_norm)) > 0.015:
        labels.append("target_moves_in_base_frame")
    if float(np.sum(base_step_norm)) > 0.05:
        labels.append("base_world_drift_present")
    if not labels:
        labels.append("no_clear_direction_issue")

    return {
        "episode_id": str(metadata.get("episode_id", path.stem)),
        "path": str(path),
        "T": int(base_pose.shape[0]),
        "metadata": {
            "allow_nominal_state_fallback": metadata.get("allow_nominal_state_fallback"),
            "target_state_source": metadata.get("target_state_source"),
            "task_type": metadata.get("task_type"),
            "success_metric": metadata.get("success_metric"),
            "gripper_enabled": metadata.get("gripper_enabled"),
            "is_grasp_dataset": metadata.get("is_grasp_dataset"),
            "target_directed_action_frame": metadata.get("target_directed_action_frame"),
            "arm_action_frame": metadata.get("arm_action_frame"),
            "max_linear_step": metadata.get("max_linear_step"),
            "max_joint_delta": metadata.get("max_joint_delta"),
        },
        "distance_base": {
            "initial": _round(float(distance_base[0])),
            "minimum": _round(float(np.min(distance_base))),
            "final": _round(float(distance_base[-1])),
            "reduction": _round(float(distance_base[0] - distance_base[-1])),
            "steps_decreasing_ratio": _round(float(np.mean(decreasing_distance)) if decreasing_distance.size else float("nan")),
        },
        "distance_world": {
            "initial": _round(float(distance_world[0])),
            "minimum": _round(float(np.min(distance_world))),
            "final": _round(float(distance_world[-1])),
            "reduction": _round(float(distance_world[0] - distance_world[-1])),
        },
        "eef_motion_base": {
            "net_norm": _round(float(np.linalg.norm(eef_base[-1] - eef_base[0]))),
            "step_norm_mean": _round(float(np.mean(eef_step_norm)) if eef_step_norm.size else 0.0),
            "step_norm_max": _round(float(np.max(eef_step_norm)) if eef_step_norm.size else 0.0),
            "mean_cosine_with_relative_target": _round(_finite_mean(eef_to_target_cosine[moving_steps]) if moving_steps.any() else float("nan")),
            "positive_direction_ratio": _round(float(np.mean(positive_eef_direction[moving_steps])) if moving_steps.any() else float("nan")),
        },
        "action_vs_motion": {
            "mean_action_to_target_cosine": _round(_finite_mean(action_to_target_cosine[commanded_steps]) if commanded_steps.any() else float("nan")),
            "mean_action_to_eef_motion_cosine": _round(_finite_mean(action_to_eef_cosine[commanded_steps]) if commanded_steps.any() else float("nan")),
            "commanded_step_count": int(np.sum(commanded_steps)),
        },
        "target_and_base_motion": {
            "target_base_net_norm": _round(float(np.linalg.norm(target_base[-1] - target_base[0]))),
            "target_base_step_norm_max": _round(float(np.max(target_step_norm)) if target_step_norm.size else 0.0),
            "base_world_net_norm": _round(float(np.linalg.norm(base_pose[-1, :3] - base_pose[0, :3]))),
            "base_world_path_norm": _round(float(np.sum(base_step_norm))),
        },
        "diagnosis_labels": labels,
    }


def _write_markdown(report: Dict[str, object], path: Path) -> None:
    lines = [
        "# B8' Reaching Direction Diagnostic",
        "",
        "This is an offline, read-only diagnostic over existing NPZ episodes.",
        "It does not start ROS, Gazebo, controllers, training, or rollout.",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Per Episode", ""])
    for episode in report["episodes"]:
        db = episode["distance_base"]
        eef = episode["eef_motion_base"]
        avm = episode["action_vs_motion"]
        tb = episode["target_and_base_motion"]
        lines.extend(
            [
                f"### {episode['episode_id']}",
                "",
                f"- base distance initial/min/final/reduction: {db['initial']:.6f} / {db['minimum']:.6f} / {db['final']:.6f} / {db['reduction']:.6f}",
                f"- distance decreasing step ratio: {db['steps_decreasing_ratio']:.6f}",
                f"- eef base net/mean-step/max-step: {eef['net_norm']:.6f} / {eef['step_norm_mean']:.6f} / {eef['step_norm_max']:.6f}",
                f"- eef-motion cosine with target direction: {eef['mean_cosine_with_relative_target']:.6f}",
                f"- eef positive target-direction ratio: {eef['positive_direction_ratio']:.6f}",
                f"- action target/eef-motion cosine: {avm['mean_action_to_target_cosine']:.6f} / {avm['mean_action_to_eef_motion_cosine']:.6f}",
                f"- target base net/max-step: {tb['target_base_net_norm']:.6f} / {tb['target_base_step_norm_max']:.6f}",
                f"- base world net/path: {tb['base_world_net_norm']:.6f} / {tb['base_world_path_norm']:.6f}",
                f"- labels: {', '.join(episode['diagnosis_labels'])}",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline direction diagnostic for B8' reaching NPZ episodes.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--pattern", default="b8_reaching_smoke_tuned_v2_*.npz")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--threshold", type=float, default=0.10)
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    episode_paths = sorted(input_dir.glob(args.pattern))
    if not episode_paths:
        raise FileNotFoundError(f"no episodes found: {input_dir}/{args.pattern}")

    episodes = [_episode_direction(path, args.threshold) for path in episode_paths]
    reductions = [float(item["distance_base"]["reduction"]) for item in episodes]
    min_distances = [float(item["distance_base"]["minimum"]) for item in episodes]
    eef_target_cosines = [float(item["eef_motion_base"]["mean_cosine_with_relative_target"]) for item in episodes]
    eef_direction_ratios = [float(item["eef_motion_base"]["positive_direction_ratio"]) for item in episodes]
    action_eef_cosines = [float(item["action_vs_motion"]["mean_action_to_eef_motion_cosine"]) for item in episodes]

    summary = {
        "episodes_total": len(episodes),
        "episodes_below_threshold": int(sum(value < args.threshold for value in min_distances)),
        "episodes_with_positive_distance_reduction": int(sum(value > 0.0 for value in reductions)),
        "mean_distance_reduction_base": _round(float(np.mean(reductions))),
        "min_distance_overall_base": _round(float(np.min(min_distances))),
        "mean_eef_motion_cosine_with_target": _round(_finite_mean(np.asarray(eef_target_cosines, dtype=np.float64))),
        "mean_eef_positive_target_direction_ratio": _round(_finite_mean(np.asarray(eef_direction_ratios, dtype=np.float64))),
        "mean_action_to_eef_motion_cosine": _round(_finite_mean(np.asarray(action_eef_cosines, dtype=np.float64))),
        "recommendation": "do_not_collect_more_until_direction_issue_is_understood",
    }
    report = {
        "input_dir": str(input_dir),
        "pattern": args.pattern,
        "threshold": args.threshold,
        "summary": summary,
        "episodes": episodes,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "direction_diagnostic.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(report, output_dir / "direction_diagnostic.md")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
