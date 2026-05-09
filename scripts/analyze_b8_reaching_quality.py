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


def _round_float(value: float) -> float:
    if not np.isfinite(value):
        return float("nan")
    return float(value)


def _episode_quality(path: Path, threshold: float) -> Tuple[Dict[str, object], Dict[str, np.ndarray]]:
    with np.load(str(path), allow_pickle=False) as loaded:
        data = {key: loaded[key] for key in loaded.files}
    metadata = _metadata(data)

    timestamp = np.asarray(data["timestamp"], dtype=np.float64)
    base_pose = np.asarray(data["base_pose"], dtype=np.float64)
    target_pose = np.asarray(data["target_pose"], dtype=np.float64)
    eef_pose = np.asarray(data["eef_pose"], dtype=np.float64)
    relative_world = np.asarray(data["relative_target_to_eef"], dtype=np.float64)
    actions = np.asarray(data["action_ee_delta"], dtype=np.float64)
    joint_positions = np.asarray(data["active_joint_positions"], dtype=np.float64)

    target_base = _points_world_to_base(target_pose[:, :3], base_pose)
    eef_base = _points_world_to_base(eef_pose[:, :3], base_pose)
    relative_base = target_base - eef_base

    distance = np.linalg.norm(relative_world, axis=1)
    distance_base = np.linalg.norm(relative_base, axis=1)
    action_xyz = actions[:, :3]
    action_xyz_norm = np.linalg.norm(action_xyz, axis=1)
    action_total_norm = np.linalg.norm(actions[:, :6], axis=1)
    positive_action = action_xyz_norm > 1e-9
    action_cosine_base = np.asarray(
        [_cosine(action_xyz[index], relative_base[index]) for index in range(actions.shape[0])],
        dtype=np.float64,
    )
    action_cosine_world = np.asarray(
        [_cosine(action_xyz[index], relative_world[index]) for index in range(actions.shape[0])],
        dtype=np.float64,
    )
    max_linear_step = float(metadata.get("max_linear_step") or 0.005)
    clip_fraction = float(np.mean(np.isclose(np.abs(action_xyz), max_linear_step, atol=1e-9)))

    joint_delta = joint_positions - joint_positions[0]
    joint_step_delta = np.diff(joint_positions, axis=0) if joint_positions.shape[0] > 1 else np.zeros((0, 0))

    target_world_motion = np.linalg.norm(target_pose[-1, :3] - target_pose[0, :3])
    eef_world_motion = np.linalg.norm(eef_pose[-1, :3] - eef_pose[0, :3])
    target_base_motion = np.linalg.norm(target_base[-1] - target_base[0])
    eef_base_motion = np.linalg.norm(eef_base[-1] - eef_base[0])
    target_base_range = np.ptp(target_base, axis=0)

    failure_reasons: List[str] = []
    if float(np.max(action_xyz_norm)) <= max_linear_step * 1.05 and clip_fraction >= 0.30:
        failure_reasons.append("clipping_too_conservative")
    if float(np.mean(action_xyz_norm[positive_action])) <= 0.0075 if np.any(positive_action) else True:
        failure_reasons.append("action_too_small")
    if timestamp.shape[0] <= 6:
        failure_reasons.append("episode_too_short")
    if float(np.max(np.abs(joint_delta))) < 0.01:
        failure_reasons.append("ik_solution_small_motion")
    if target_world_motion > 0.20 and target_base_motion < 0.05:
        failure_reasons.append("base_drift_dominates_world_eef")
    if float(np.min(distance)) > threshold:
        failure_reasons.append("threshold_not_reached")
    if float(distance[-1] - distance[0]) > 0.0:
        failure_reasons.append("target_direction_not_followed")
    if target_base_motion > 0.05:
        failure_reasons.append("pregrasp_offset_not_stable_in_base_frame")
    if not failure_reasons:
        failure_reasons.append("no_clear_issue")

    base_state_source = metadata.get("base_state_source")
    metadata_ok = (
        metadata.get("allow_nominal_state_fallback") is False
        and base_state_source in ("odom", "gazebo_model_states")
        and metadata.get("joint_state_source") == "joint_states"
        and metadata.get("target_state_source") == "gazebo_model_states"
        and metadata.get("gripper_enabled") is False
        and metadata.get("is_grasp_dataset") is False
        and metadata.get("task_type") in ("arm_only_reaching", "pregrasp_positioning")
        and metadata.get("success_metric") in ("reaching_success", "pregrasp_success")
    )

    quality = {
        "episode_id": metadata.get("episode_id", path.stem),
        "path": str(path),
        "T": int(timestamp.shape[0]),
        "validator_expected": "PASS",
        "metadata_ok": bool(metadata_ok),
        "success": bool(np.asarray(data["success"]).item()),
        "metadata": {
            "allow_nominal_state_fallback": metadata.get("allow_nominal_state_fallback"),
            "base_state_source": metadata.get("base_state_source"),
            "joint_state_source": metadata.get("joint_state_source"),
            "target_state_source": metadata.get("target_state_source"),
            "eef_pose_source": metadata.get("eef_pose_source"),
            "task_type": metadata.get("task_type"),
            "success_metric": metadata.get("success_metric"),
            "gripper_enabled": metadata.get("gripper_enabled"),
            "is_grasp_dataset": metadata.get("is_grasp_dataset"),
            "target_directed_action_frame": metadata.get("target_directed_action_frame"),
            "arm_action_frame": metadata.get("arm_action_frame"),
            "max_linear_step": metadata.get("max_linear_step"),
            "max_joint_delta": metadata.get("max_joint_delta"),
            "rate_hz": metadata.get("rate_hz"),
            "max_duration_sec": metadata.get("max_duration_sec"),
            "field_availability": metadata.get("field_availability", {}),
            "unavailable_fields": metadata.get("unavailable_fields", []),
        },
        "distance": {
            "curve": [_round_float(v) for v in distance.tolist()],
            "initial": _round_float(float(distance[0])),
            "minimum": _round_float(float(np.min(distance))),
            "final": _round_float(float(distance[-1])),
            "reduction": _round_float(float(distance[0] - distance[-1])),
            "min_below_threshold": bool(np.min(distance) < threshold),
            "final_closer_than_initial": bool(distance[-1] < distance[0]),
            "base_frame_curve": [_round_float(v) for v in distance_base.tolist()],
        },
        "action": {
            "xyz_norm_curve": [_round_float(v) for v in action_xyz_norm.tolist()],
            "xyz_norm_mean": _round_float(float(np.mean(action_xyz_norm))),
            "xyz_norm_max": _round_float(float(np.max(action_xyz_norm))),
            "six_dof_norm_mean": _round_float(float(np.mean(action_total_norm))),
            "six_dof_norm_max": _round_float(float(np.max(action_total_norm))),
            "xyz_dim_min": [_round_float(v) for v in np.min(action_xyz, axis=0).tolist()],
            "xyz_dim_max": [_round_float(v) for v in np.max(action_xyz, axis=0).tolist()],
            "xyz_dim_mean": [_round_float(v) for v in np.mean(action_xyz, axis=0).tolist()],
            "max_linear_step": _round_float(max_linear_step),
            "clip_fraction_xyz_at_max_linear_step": _round_float(clip_fraction),
            "mean_cosine_with_relative_base": _round_float(float(np.nanmean(action_cosine_base[positive_action])) if np.any(positive_action) else float("nan")),
            "mean_cosine_with_relative_world": _round_float(float(np.nanmean(action_cosine_world[positive_action])) if np.any(positive_action) else float("nan")),
        },
        "eef_and_target": {
            "target_world_motion": _round_float(float(target_world_motion)),
            "eef_world_motion": _round_float(float(eef_world_motion)),
            "target_base_motion": _round_float(float(target_base_motion)),
            "eef_base_motion": _round_float(float(eef_base_motion)),
            "target_base_range_xyz": [_round_float(v) for v in target_base_range.tolist()],
            "target_static_in_world": bool(target_world_motion < 0.02),
            "target_stable_in_base": bool(target_base_motion < 0.05),
        },
        "joints": {
            "active_left_delta_first_to_last": [_round_float(v) for v in (joint_positions[-1] - joint_positions[0]).tolist()],
            "active_left_total_max_abs_delta": _round_float(float(np.max(np.abs(joint_delta)))),
            "active_left_step_max_abs_delta": _round_float(float(np.max(np.abs(joint_step_delta))) if joint_step_delta.size else 0.0),
            "bounded_small_motion": bool(np.max(np.abs(joint_delta)) < 0.02),
        },
        "failure_reason_candidates": failure_reasons,
    }

    curves = {
        "timestamp": timestamp,
        "distance": distance,
        "action_xyz_norm": action_xyz_norm,
    }
    return quality, curves


def _write_markdown(report: Dict[str, object], path: Path) -> None:
    lines: List[str] = [
        "# B8' Reaching Smoke Quality Review",
        "",
        "This review only analyzes existing non-fallback arm-only reaching smoke episodes.",
        "It is not training, rollout, grasping, or success-rate evaluation.",
        "",
        "## Summary",
        "",
    ]
    summary = report["summary"]
    for key in (
        "episodes_total",
        "episodes_valid_assumed",
        "all_required_metadata_ok",
        "episodes_with_positive_distance_reduction",
        "episodes_below_threshold",
        "min_distance_overall",
        "mean_initial_distance",
        "mean_final_distance",
        "mean_distance_reduction",
        "max_active_left_joint_delta",
        "recommendation",
    ):
        lines.append(f"- `{key}`: {summary[key]}")

    lines.extend(["", "## Per Episode", ""])
    for episode in report["episodes"]:
        distance = episode["distance"]
        action = episode["action"]
        joints = episode["joints"]
        eef_target = episode["eef_and_target"]
        lines.extend(
            [
                f"### {episode['episode_id']}",
                "",
                f"- distance initial/min/final/reduction: "
                f"{distance['initial']:.6f} / {distance['minimum']:.6f} / "
                f"{distance['final']:.6f} / {distance['reduction']:.6f}",
                f"- below threshold: {distance['min_below_threshold']}; "
                f"final closer: {distance['final_closer_than_initial']}",
                f"- action xyz norm mean/max: {action['xyz_norm_mean']:.6f} / "
                f"{action['xyz_norm_max']:.6f}; clip fraction at max_linear_step "
                f"({action['max_linear_step']:.3f} m): "
                f"{action['clip_fraction_xyz_at_max_linear_step']:.3f}",
                f"- action-relative cosine base/world: "
                f"{action['mean_cosine_with_relative_base']:.6f} / "
                f"{action['mean_cosine_with_relative_world']:.6f}",
                f"- joint max delta / step max delta: "
                f"{joints['active_left_total_max_abs_delta']:.6f} / "
                f"{joints['active_left_step_max_abs_delta']:.6f}",
                f"- target world/base motion: "
                f"{eef_target['target_world_motion']:.6f} / "
                f"{eef_target['target_base_motion']:.6f}",
                f"- failure reason candidates: {', '.join(episode['failure_reason_candidates'])}",
                "",
            ]
        )

    lines.extend(
        [
            "## Recommendation",
            "",
            str(summary["recommendation_detail"]),
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _plot_distance_curves(report: Dict[str, object], curves_by_episode: Dict[str, Dict[str, np.ndarray]], path: Path, threshold: float) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for episode in report["episodes"]:
        episode_id = str(episode["episode_id"])
        curves = curves_by_episode[episode_id]
        x = np.arange(curves["distance"].shape[0])
        ax.plot(x, curves["distance"], marker="o", label=episode_id)
    ax.axhline(threshold, color="black", linestyle="--", linewidth=1.0, label=f"threshold {threshold:.2f} m")
    ax.set_xlabel("sample index")
    ax.set_ylabel("EEF-target distance (m)")
    ax.set_title("B8' reaching smoke distance curves")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze B8' reaching smoke quality from existing NPZ episodes.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--pattern", default="b8_reaching_smoke_*.npz")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--threshold", type=float, default=0.10)
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    episode_paths = sorted(input_dir.glob(args.pattern))
    if not episode_paths:
        raise FileNotFoundError(f"no episodes found: {input_dir}/{args.pattern}")

    episodes = []
    curves_by_episode: Dict[str, Dict[str, np.ndarray]] = {}
    for path in episode_paths:
        quality, curves = _episode_quality(path, args.threshold)
        episodes.append(quality)
        curves_by_episode[str(quality["episode_id"])] = curves

    distance_reductions = [float(item["distance"]["reduction"]) for item in episodes]
    min_distances = [float(item["distance"]["minimum"]) for item in episodes]
    initial_distances = [float(item["distance"]["initial"]) for item in episodes]
    final_distances = [float(item["distance"]["final"]) for item in episodes]
    joint_max = [float(item["joints"]["active_left_total_max_abs_delta"]) for item in episodes]
    action_xyz_norms = []
    for item in episodes:
        action_xyz_norms.extend([float(v) for v in item["action"]["xyz_norm_curve"]])

    clip_fractions = [
        float(item["action"]["clip_fraction_xyz_at_max_linear_step"]) for item in episodes
    ]
    base_cosines = [
        float(item["action"]["mean_cosine_with_relative_base"]) for item in episodes
    ]
    recommendation = "A"
    if any(v < args.threshold for v in min_distances):
        recommendation_detail = (
            "Choose A cautiously: at least one episode crossed the reaching threshold, "
            "but this is still a small smoke dataset. Review bounded joint motion and "
            "distance consistency before expanding collection or training."
        )
    elif np.mean(clip_fractions) >= 0.30:
        recommendation_detail = (
            "Choose A: tune the scripted reaching expert before collecting a larger "
            "dataset. Episodes are valid non-fallback smoke data, but no episode crossed "
            "the reaching threshold and action deltas are frequently clipped at the "
            "configured max_linear_step. Do not expand to 20 episodes or train yet."
        )
    elif float(np.max(joint_max)) >= 0.04 and float(np.mean(distance_reductions)) < 0.005:
        recommendation_detail = (
            "Choose A: reaching quality is still weak. The tuned expert produces larger "
            "bounded joint motion and base-frame-aligned actions, but no episode crossed "
            "the reaching threshold and mean distance reduction remains small. Avoid "
            "larger collection or training; next inspect target setup, offset, and "
            "command-direction consistency."
        )
    elif float(np.nanmean(base_cosines)) > 0.5 and float(np.mean(distance_reductions)) < 0.005:
        recommendation_detail = (
            "Choose A: action direction is generally aligned in base frame, but distance "
            "reduction is still too small and no episode crossed the reaching threshold. "
            "Review target/pregrasp setup before expanding collection or training."
        )
    else:
        recommendation_detail = (
            "Choose A: the dataset is valid non-fallback smoke data, but reaching quality "
            "is not sufficient for larger collection or training until distance metrics "
            "improve."
        )

    report = {
        "input_dir": str(input_dir),
        "pattern": args.pattern,
        "threshold": args.threshold,
        "episodes": episodes,
        "summary": {
            "episodes_total": len(episodes),
            "episodes_valid_assumed": len(episodes),
            "all_required_metadata_ok": bool(all(item["metadata_ok"] for item in episodes)),
            "episodes_with_positive_distance_reduction": int(sum(v > 0.0 for v in distance_reductions)),
            "episodes_below_threshold": int(sum(v < args.threshold for v in min_distances)),
            "min_distance_overall": _round_float(float(np.min(min_distances))),
            "mean_initial_distance": _round_float(float(np.mean(initial_distances))),
            "mean_final_distance": _round_float(float(np.mean(final_distances))),
            "mean_distance_reduction": _round_float(float(np.mean(distance_reductions))),
            "max_active_left_joint_delta": _round_float(float(np.max(joint_max))),
            "action_xyz_norm_mean_all_samples": _round_float(float(np.mean(action_xyz_norms))),
            "action_xyz_norm_max_all_samples": _round_float(float(np.max(action_xyz_norms))),
            "recommendation": recommendation,
            "recommendation_detail": recommendation_detail,
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "per_episode_quality.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(report, output_dir / "per_episode_quality.md")
    _plot_distance_curves(report, curves_by_episode, output_dir / "distance_curves.png", args.threshold)

    action_summary = {
        "threshold": args.threshold,
        "episodes": {
            item["episode_id"]: item["action"] for item in episodes
        },
        "summary": {
            "action_xyz_norm_mean_all_samples": report["summary"]["action_xyz_norm_mean_all_samples"],
            "action_xyz_norm_max_all_samples": report["summary"]["action_xyz_norm_max_all_samples"],
        },
    }
    (output_dir / "action_magnitude_summary.json").write_text(
        json.dumps(action_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    joint_summary = {
        "episodes": {
            item["episode_id"]: item["joints"] for item in episodes
        },
        "summary": {
            "max_active_left_joint_delta": report["summary"]["max_active_left_joint_delta"],
        },
    }
    (output_dir / "joint_motion_summary.json").write_text(
        json.dumps(joint_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
