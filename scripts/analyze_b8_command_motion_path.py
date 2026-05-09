#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Dict, List

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


def _finite_mean(values: List[float]) -> float:
    finite = np.asarray([value for value in values if np.isfinite(value)], dtype=np.float64)
    if finite.size == 0:
        return float("nan")
    return float(np.mean(finite))


def _round(value: float) -> float:
    if not np.isfinite(value):
        return float("nan")
    return float(value)


def _lag_metrics(
    action_xyz: np.ndarray,
    eef_step_base: np.ndarray,
    relative_base: np.ndarray,
    distance_base: np.ndarray,
    lag: int,
) -> Dict[str, object]:
    cosines: List[float] = []
    gains: List[float] = []
    step_ratios: List[float] = []
    target_cosines: List[float] = []
    distance_decreasing: List[bool] = []
    sample_count = max(0, min(action_xyz.shape[0], eef_step_base.shape[0] - lag))

    for index in range(sample_count):
        action = action_xyz[index]
        eef_step = eef_step_base[index + lag]
        action_norm_sq = float(np.dot(action, action))
        action_norm = float(np.sqrt(action_norm_sq))
        eef_norm = float(np.linalg.norm(eef_step))
        cosines.append(_cosine(action, eef_step))
        target_cosines.append(_cosine(eef_step, relative_base[index]))
        if action_norm_sq > 1e-12:
            gains.append(float(np.dot(eef_step, action) / action_norm_sq))
        else:
            gains.append(float("nan"))
        if action_norm > 1e-12:
            step_ratios.append(float(eef_norm / action_norm))
        else:
            step_ratios.append(float("nan"))
        distance_decreasing.append(bool(distance_base[index + lag + 1] < distance_base[index + lag]))

    return {
        "lag_steps": lag,
        "sample_count": sample_count,
        "mean_action_to_eef_cosine": _round(_finite_mean(cosines)),
        "mean_eef_to_target_cosine": _round(_finite_mean(target_cosines)),
        "mean_realized_gain_along_action": _round(_finite_mean(gains)),
        "mean_eef_step_over_action_norm": _round(_finite_mean(step_ratios)),
        "distance_decreasing_ratio": _round(float(np.mean(distance_decreasing)) if distance_decreasing else float("nan")),
    }


def _episode_report(path: Path, threshold: float, max_lag_steps: int) -> Dict[str, object]:
    with np.load(str(path), allow_pickle=False) as loaded:
        data = {key: loaded[key] for key in loaded.files}
    metadata = _metadata(data)

    base_pose = np.asarray(data["base_pose"], dtype=np.float64)
    target_pose = np.asarray(data["target_pose"], dtype=np.float64)
    eef_pose = np.asarray(data["eef_pose"], dtype=np.float64)
    action_xyz = np.asarray(data["action_ee_delta"], dtype=np.float64)[:, :3]

    target_base = _points_world_to_base(target_pose[:, :3], base_pose)
    eef_base = _points_world_to_base(eef_pose[:, :3], base_pose)
    relative_base = target_base - eef_base
    distance_base = np.linalg.norm(relative_base, axis=1)
    eef_step_base = np.diff(eef_base, axis=0)
    target_step_base = np.diff(target_base, axis=0)
    base_step_world = np.diff(base_pose[:, :3], axis=0)

    lag_reports = [
        _lag_metrics(action_xyz, eef_step_base, relative_base, distance_base, lag)
        for lag in range(max_lag_steps + 1)
    ]
    best_lag = max(
        lag_reports,
        key=lambda item: (
            -1.0 if not np.isfinite(float(item["mean_action_to_eef_cosine"])) else float(item["mean_action_to_eef_cosine"])
        ),
    )

    labels: List[str] = []
    if float(np.min(distance_base)) > threshold:
        labels.append("threshold_not_reached")
    if float(best_lag["mean_action_to_eef_cosine"]) < 0.30:
        labels.append("weak_action_to_motion_coupling")
    if int(best_lag["lag_steps"]) > 0:
        labels.append("possible_command_response_lag")
    if float(best_lag["distance_decreasing_ratio"]) < 0.50:
        labels.append("distance_not_decreasing_under_best_lag")
    if target_step_base.size and float(np.max(np.linalg.norm(target_step_base, axis=1))) > 0.03:
        labels.append("target_moves_in_base_frame")
    if float(np.sum(np.linalg.norm(base_step_world, axis=1))) > 0.05:
        labels.append("base_world_drift_present")
    if not labels:
        labels.append("no_clear_command_motion_issue")

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
        },
        "motion_context": {
            "eef_base_net_norm": _round(float(np.linalg.norm(eef_base[-1] - eef_base[0]))),
            "target_base_net_norm": _round(float(np.linalg.norm(target_base[-1] - target_base[0]))),
            "target_base_step_norm_max": _round(float(np.max(np.linalg.norm(target_step_base, axis=1))) if target_step_base.size else 0.0),
            "base_world_path_norm": _round(float(np.sum(np.linalg.norm(base_step_world, axis=1)))),
        },
        "lag_scan": lag_reports,
        "best_lag_by_action_to_eef_cosine": best_lag,
        "diagnosis_labels": labels,
    }


def _write_markdown(report: Dict[str, object], path: Path) -> None:
    lines = [
        "# B8' Command-To-Motion Diagnostic",
        "",
        "Offline-only analysis over existing NPZ episodes. No ROS, Gazebo, control, training, or rollout.",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Per Episode", ""])

    for episode in report["episodes"]:
        distance = episode["distance_base"]
        context = episode["motion_context"]
        best = episode["best_lag_by_action_to_eef_cosine"]
        lines.extend(
            [
                f"### {episode['episode_id']}",
                "",
                f"- distance initial/min/final/reduction: {distance['initial']:.6f} / {distance['minimum']:.6f} / {distance['final']:.6f} / {distance['reduction']:.6f}",
                f"- eef_base_net_norm: {context['eef_base_net_norm']:.6f}",
                f"- target_base_net/max-step: {context['target_base_net_norm']:.6f} / {context['target_base_step_norm_max']:.6f}",
                f"- base_world_path_norm: {context['base_world_path_norm']:.6f}",
                f"- best lag steps: {best['lag_steps']}",
                f"- best action-to-eef cosine: {best['mean_action_to_eef_cosine']:.6f}",
                f"- best eef-to-target cosine: {best['mean_eef_to_target_cosine']:.6f}",
                f"- best realized gain along action: {best['mean_realized_gain_along_action']:.6f}",
                f"- best distance decreasing ratio: {best['distance_decreasing_ratio']:.6f}",
                f"- labels: {', '.join(episode['diagnosis_labels'])}",
                "",
                "| lag | samples | action/eef cos | eef/target cos | gain | eef/action norm | dist-decrease ratio |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for item in episode["lag_scan"]:
            lines.append(
                f"| {item['lag_steps']} | {item['sample_count']} | "
                f"{item['mean_action_to_eef_cosine']:.6f} | "
                f"{item['mean_eef_to_target_cosine']:.6f} | "
                f"{item['mean_realized_gain_along_action']:.6f} | "
                f"{item['mean_eef_step_over_action_norm']:.6f} | "
                f"{item['distance_decreasing_ratio']:.6f} |"
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline B8' command-to-motion diagnostic.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--pattern", default="b8_reaching_smoke_tuned_v2_*.npz")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--threshold", type=float, default=0.10)
    parser.add_argument("--max-lag-steps", type=int, default=3)
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    paths = sorted(input_dir.glob(args.pattern))
    if not paths:
        raise FileNotFoundError(f"no episodes found: {input_dir}/{args.pattern}")

    episodes = [_episode_report(path, args.threshold, args.max_lag_steps) for path in paths]
    best_lags = [int(item["best_lag_by_action_to_eef_cosine"]["lag_steps"]) for item in episodes]
    best_cosines = [float(item["best_lag_by_action_to_eef_cosine"]["mean_action_to_eef_cosine"]) for item in episodes]
    best_gains = [float(item["best_lag_by_action_to_eef_cosine"]["mean_realized_gain_along_action"]) for item in episodes]
    min_distances = [float(item["distance_base"]["minimum"]) for item in episodes]

    summary = {
        "episodes_total": len(episodes),
        "episodes_below_threshold": int(sum(value < args.threshold for value in min_distances)),
        "mean_best_lag_steps": _round(float(np.mean(best_lags))),
        "mean_best_action_to_eef_cosine": _round(_finite_mean(best_cosines)),
        "mean_best_realized_gain_along_action": _round(_finite_mean(best_gains)),
        "recommendation": "do_not_collect_more_until_command_to_motion_path_is_explained",
    }
    report = {
        "input_dir": str(input_dir),
        "pattern": args.pattern,
        "threshold": args.threshold,
        "max_lag_steps": args.max_lag_steps,
        "summary": summary,
        "episodes": episodes,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "command_motion_diagnostic.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(report, output_dir / "command_motion_diagnostic.md")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
