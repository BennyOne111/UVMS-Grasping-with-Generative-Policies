#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List, Tuple

import numpy as np


PACKAGE_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

from rexrov_single_oberon7_fm_dp.dataset_writer import validate_episode_file  # noqa: E402


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


def _float(value: float) -> float:
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
    sample_count = max(0, min(action_xyz.shape[0], eef_step_base.shape[0] - lag))
    for index in range(sample_count):
        action = action_xyz[index]
        eef_step = eef_step_base[index + lag]
        action_norm_sq = float(np.dot(action, action))
        cosines.append(_cosine(action, eef_step))
        gains.append(float(np.dot(eef_step, action) / action_norm_sq) if action_norm_sq > 1e-12 else float("nan"))
    return {
        "lag_steps": lag,
        "sample_count": sample_count,
        "mean_action_to_eef_cosine": _float(_finite_mean(cosines)),
        "mean_realized_gain_along_action": _float(_finite_mean(gains)),
        "distance_decreasing_ratio": _float(
            float(np.mean(np.diff(distance_base[lag : lag + sample_count + 1]) < 0.0))
            if sample_count > 0
            else float("nan")
        ),
    }


def _episode_report(
    path: Path,
    threshold: float,
    target_step_threshold: float,
    max_lag_steps: int,
    required_base_state_source: str,
) -> Dict[str, object]:
    validation = validate_episode_file(str(path), allow_unavailable_nan=True)
    with np.load(str(path), allow_pickle=False) as loaded:
        data = {key: loaded[key] for key in loaded.files}
    metadata = _metadata(data)

    base_pose = np.asarray(data["base_pose"], dtype=np.float64)
    target_pose = np.asarray(data["target_pose"], dtype=np.float64)
    eef_pose = np.asarray(data["eef_pose"], dtype=np.float64)
    relative = np.asarray(data["relative_target_to_eef"], dtype=np.float64)
    actions = np.asarray(data["action_ee_delta"], dtype=np.float64)
    joints = np.asarray(data["active_joint_positions"], dtype=np.float64)

    target_base = _points_world_to_base(target_pose[:, :3], base_pose)
    eef_base = _points_world_to_base(eef_pose[:, :3], base_pose)
    relative_base = target_base - eef_base
    distance = np.linalg.norm(relative, axis=1)
    distance_base = np.linalg.norm(relative_base, axis=1)
    target_step_base = np.linalg.norm(np.diff(target_base, axis=0), axis=1) if target_base.shape[0] > 1 else np.zeros(0)
    eef_step_base = np.diff(eef_base, axis=0) if eef_base.shape[0] > 1 else np.zeros((0, 3))
    joint_delta = joints - joints[0]
    joint_step = np.diff(joints, axis=0) if joints.shape[0] > 1 else np.zeros((0, joints.shape[1]))

    lag_reports = [
        _lag_metrics(actions[:, :3], eef_step_base, relative_base, distance_base, lag)
        for lag in range(max_lag_steps + 1)
    ]
    best_lag = max(
        lag_reports,
        key=lambda item: (
            -1.0
            if not np.isfinite(float(item["mean_action_to_eef_cosine"]))
            else float(item["mean_action_to_eef_cosine"])
        ),
    )

    large_target_step_indices = [
        int(index + 1)
        for index, value in enumerate(target_step_base.tolist())
        if float(value) > target_step_threshold
    ]
    success_scalar = bool(np.asarray(data["success"]).item())
    metadata_success = metadata.get("success")
    unavailable = metadata.get("unavailable_fields", [])
    field_availability = metadata.get("field_availability", {})
    required_fields_available = all(
        bool(field_availability.get(key, key not in unavailable))
        for key in ("target_pose", "eef_pose", "relative_target_to_eef", "action_ee_delta")
    )
    allowed_base_sources = (
        (required_base_state_source,)
        if required_base_state_source
        else ("odom", "gazebo_model_states")
    )
    metadata_ok = (
        metadata.get("allow_nominal_state_fallback") is False
        and metadata.get("base_state_source") in allowed_base_sources
        and metadata.get("joint_state_source") == "joint_states"
        and metadata.get("target_state_source") == "gazebo_model_states"
        and metadata.get("gripper_enabled") is False
        and metadata.get("is_grasp_dataset") is False
        and metadata.get("task_type") in ("arm_only_reaching", "pregrasp_positioning")
        and metadata.get("success_metric") in ("reaching_success", "pregrasp_success")
        and required_fields_available
    )

    failure_reasons: List[str] = []
    if not validation.ok:
        failure_reasons.append("validator_failed")
    if not metadata_ok:
        failure_reasons.append("metadata_or_required_fields_not_ok")
    if large_target_step_indices:
        failure_reasons.append("target_base_step_jump")
    if not success_scalar:
        failure_reasons.append("saved_success_false")
    if float(distance[-1]) >= threshold:
        failure_reasons.append("final_distance_above_threshold")
    if float(distance[0] - distance[-1]) <= 0.0:
        failure_reasons.append("no_positive_distance_reduction")
    if float(np.max(np.abs(joint_step))) > float(metadata.get("max_joint_delta") or 0.01) * 2.0:
        failure_reasons.append("large_joint_step")
    if not failure_reasons:
        failure_reasons.append("none")

    return {
        "episode_id": str(metadata.get("episode_id", path.stem)),
        "path": str(path),
        "T": int(distance.shape[0]),
        "validation": {
            "ok": bool(validation.ok),
            "errors": validation.errors,
            "warnings": validation.warnings,
            "summary": validation.summary,
        },
        "success": {
            "scalar": success_scalar,
            "metadata": bool(metadata_success) if isinstance(metadata_success, bool) else metadata_success,
            "consistent": bool(success_scalar == metadata_success),
            "source": metadata.get("success_source"),
            "recorded_success_distance_m": metadata.get("recorded_success_distance_m"),
            "recorded_success_distance_threshold_m": metadata.get("recorded_success_distance_threshold_m"),
        },
        "metadata": {
            "ok": bool(metadata_ok),
            "allow_nominal_state_fallback": metadata.get("allow_nominal_state_fallback"),
            "base_state_source": metadata.get("base_state_source"),
            "joint_state_source": metadata.get("joint_state_source"),
            "target_state_source": metadata.get("target_state_source"),
            "eef_pose_source": metadata.get("eef_pose_source"),
            "gripper_enabled": metadata.get("gripper_enabled"),
            "is_grasp_dataset": metadata.get("is_grasp_dataset"),
            "task_type": metadata.get("task_type"),
            "success_metric": metadata.get("success_metric"),
            "unavailable_fields": unavailable,
            "field_availability": field_availability,
        },
        "distance": {
            "initial": _float(float(distance[0])),
            "minimum": _float(float(np.min(distance))),
            "final": _float(float(distance[-1])),
            "reduction": _float(float(distance[0] - distance[-1])),
            "below_threshold": bool(float(np.min(distance)) < threshold),
            "final_below_threshold": bool(float(distance[-1]) < threshold),
        },
        "joints": {
            "max_active_left_joint_delta": _float(float(np.max(np.abs(joint_delta)))),
            "max_active_left_joint_step_delta": _float(float(np.max(np.abs(joint_step))) if joint_step.size else 0.0),
        },
        "target_base_sync": {
            "max_target_step_base": _float(float(np.max(target_step_base)) if target_step_base.size else 0.0),
            "large_target_step_indices": large_target_step_indices,
            "threshold": target_step_threshold,
        },
        "command_motion": {
            "best_lag_steps": int(best_lag["lag_steps"]),
            "best_action_to_eef_cosine": best_lag["mean_action_to_eef_cosine"],
            "best_realized_gain_along_action": best_lag["mean_realized_gain_along_action"],
            "best_distance_decreasing_ratio": best_lag["distance_decreasing_ratio"],
        },
        "failure_reason": ", ".join(failure_reasons),
    }


def _write_markdown(report: Dict[str, object], path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# B8' Repeatability Smoke Summary",
        "",
        "Offline summary over real non-fallback arm-only reaching/pre-grasp smoke episodes.",
        "This is not training, learned rollout, gripper evaluation, or grasp success.",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Per Episode", ""])
    for episode in report["episodes"]:
        distance = episode["distance"]
        sync = episode["target_base_sync"]
        cm = episode["command_motion"]
        success = episode["success"]
        lines.extend(
            [
                f"### {episode['episode_id']}",
                "",
                f"- validation: {'PASS' if episode['validation']['ok'] else 'FAIL'}",
                f"- success scalar / metadata / source: {success['scalar']} / {success['metadata']} / {success['source']}",
                f"- recorded success distance / threshold: {success['recorded_success_distance_m']} / {success['recorded_success_distance_threshold_m']}",
                f"- distance initial/min/final/reduction: {distance['initial']:.6f} / {distance['minimum']:.6f} / {distance['final']:.6f} / {distance['reduction']:.6f}",
                f"- max target step base: {sync['max_target_step_base']:.6f}; large indices: {sync['large_target_step_indices']}",
                f"- max joint delta / step: {episode['joints']['max_active_left_joint_delta']:.6f} / {episode['joints']['max_active_left_joint_step_delta']:.6f}",
                f"- best lag / action-eef cosine / gain: {cm['best_lag_steps']} / {cm['best_action_to_eef_cosine']:.6f} / {cm['best_realized_gain_along_action']:.6f}",
                f"- failure_reason: {episode['failure_reason']}",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize B8' repeatability smoke episodes.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--pattern", default="b8_reaching_repeatability_smoke_*.npz")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--threshold", type=float, default=0.10)
    parser.add_argument("--target-step-threshold", type=float, default=0.03)
    parser.add_argument("--max-lag-steps", type=int, default=3)
    parser.add_argument(
        "--required-base-state-source",
        default="",
        choices=("", "odom", "gazebo_model_states"),
        help="Require a specific metadata base_state_source. Empty keeps the historical permissive check.",
    )
    parser.add_argument(
        "--fail-on-problem",
        action="store_true",
        help="Exit nonzero if any episode fails validation, metadata, success consistency, or source-sync checks.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    paths = sorted(input_dir.glob(args.pattern))
    if not paths:
        raise FileNotFoundError(f"no episodes found: {input_dir}/{args.pattern}")

    episodes = [
        _episode_report(
            path,
            args.threshold,
            args.target_step_threshold,
            args.max_lag_steps,
            args.required_base_state_source,
        )
        for path in paths
    ]
    final_distances = [float(item["distance"]["final"]) for item in episodes]
    initial_distances = [float(item["distance"]["initial"]) for item in episodes]
    reductions = [float(item["distance"]["reduction"]) for item in episodes]
    min_distances = [float(item["distance"]["minimum"]) for item in episodes]
    joint_deltas = [float(item["joints"]["max_active_left_joint_delta"]) for item in episodes]
    target_steps = [float(item["target_base_sync"]["max_target_step_base"]) for item in episodes]
    best_cosines = [float(item["command_motion"]["best_action_to_eef_cosine"]) for item in episodes]
    best_lags = [int(item["command_motion"]["best_lag_steps"]) for item in episodes]
    best_gains = [float(item["command_motion"]["best_realized_gain_along_action"]) for item in episodes]

    summary = {
        "episodes_total": len(episodes),
        "episodes_valid": int(sum(item["validation"]["ok"] for item in episodes)),
        "validator_pass_count": int(sum(item["validation"]["ok"] for item in episodes)),
        "success_count": int(sum(item["success"]["scalar"] is True for item in episodes)),
        "reaching_success_rate": _float(float(np.mean([item["success"]["scalar"] is True for item in episodes]))),
        "all_required_metadata_ok": bool(all(item["metadata"]["ok"] for item in episodes)),
        "all_success_metadata_consistent": bool(all(item["success"]["consistent"] for item in episodes)),
        "initial_distance_per_episode": [_float(float(item["distance"]["initial"])) for item in episodes],
        "min_distance_per_episode": [_float(float(item["distance"]["minimum"])) for item in episodes],
        "final_distance_per_episode": [_float(float(item["distance"]["final"])) for item in episodes],
        "distance_reduction_per_episode": [_float(float(item["distance"]["reduction"])) for item in episodes],
        "mean_initial_distance": _float(float(np.mean(initial_distances))),
        "mean_final_distance": _float(float(np.mean(final_distances))),
        "min_distance_overall": _float(float(np.min(min_distances))),
        "mean_distance_reduction": _float(float(np.mean(reductions))),
        "max_active_left_joint_delta": _float(float(np.max(joint_deltas))),
        "max_target_step_base": _float(float(np.max(target_steps))),
        "large_target_step_indices_by_episode": {
            item["episode_id"]: item["target_base_sync"]["large_target_step_indices"] for item in episodes
        },
        "mean_best_action_to_eef_cosine": _float(_finite_mean(best_cosines)),
        "mean_best_lag_steps": _float(float(np.mean(best_lags))),
        "mean_best_realized_gain_along_action": _float(_finite_mean(best_gains)),
        "failure_reason_by_episode": {
            item["episode_id"]: item["failure_reason"] for item in episodes
        },
        "interpretation": "repeatability_smoke_only_not_training_not_grasp",
    }

    report = {
        "input_dir": str(input_dir),
        "pattern": args.pattern,
        "threshold": args.threshold,
        "target_step_threshold": args.target_step_threshold,
        "required_base_state_source": args.required_base_state_source,
        "summary": summary,
        "episodes": episodes,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "repeatability_summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(report, output_dir / "repeatability_summary.md")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.fail_on_problem:
        has_problem = (
            summary["validator_pass_count"] != summary["episodes_total"]
            or not summary["all_required_metadata_ok"]
            or not summary["all_success_metadata_consistent"]
            or any(summary["large_target_step_indices_by_episode"].values())
            or any(reason != "none" for reason in summary["failure_reason_by_episode"].values())
        )
        if has_problem:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
