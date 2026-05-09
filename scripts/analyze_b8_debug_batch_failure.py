#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Sequence

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


def _yaw_from_quat_xyzw(quat: np.ndarray) -> float:
    x, y, z, w = [float(v) for v in quat]
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return float(np.arctan2(siny_cosp, cosy_cosp))


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


def _finite_mean(values: Iterable[float]) -> float:
    finite = np.asarray([value for value in values if np.isfinite(value)], dtype=np.float64)
    if finite.size == 0:
        return float("nan")
    return float(np.mean(finite))


def _finite_std(values: Iterable[float]) -> float:
    finite = np.asarray([value for value in values if np.isfinite(value)], dtype=np.float64)
    if finite.size == 0:
        return float("nan")
    return float(np.std(finite))


def _float(value: float) -> float:
    if not np.isfinite(value):
        return float("nan")
    return float(value)


def _episode_index(path: Path) -> int:
    try:
        return int(path.stem.rsplit("_", 1)[-1])
    except ValueError:
        return -1


def _lag_metrics(
    action_xyz: np.ndarray,
    eef_step_base: np.ndarray,
    relative_base: np.ndarray,
    distance_base: np.ndarray,
    lag: int,
) -> Dict[str, object]:
    cosines: List[float] = []
    gains: List[float] = []
    eef_target_cosines: List[float] = []
    distance_decreasing: List[bool] = []
    sample_count = max(0, min(action_xyz.shape[0], eef_step_base.shape[0] - lag))
    for index in range(sample_count):
        action = action_xyz[index]
        eef_step = eef_step_base[index + lag]
        action_norm_sq = float(np.dot(action, action))
        cosines.append(_cosine(action, eef_step))
        eef_target_cosines.append(_cosine(eef_step, relative_base[index]))
        gains.append(float(np.dot(eef_step, action) / action_norm_sq) if action_norm_sq > 1e-12 else float("nan"))
        distance_decreasing.append(bool(distance_base[index + lag + 1] < distance_base[index + lag]))
    return {
        "lag_steps": lag,
        "sample_count": int(sample_count),
        "mean_action_to_eef_cosine": _float(_finite_mean(cosines)),
        "mean_eef_to_target_cosine": _float(_finite_mean(eef_target_cosines)),
        "mean_realized_gain_along_action": _float(_finite_mean(gains)),
        "distance_decreasing_ratio": _float(float(np.mean(distance_decreasing)) if distance_decreasing else float("nan")),
    }


def _load_episode(path: Path, threshold: float, max_lag_steps: int, reference: Dict[str, np.ndarray]) -> Dict[str, object]:
    with np.load(str(path), allow_pickle=False) as loaded:
        data = {key: loaded[key] for key in loaded.files}
    metadata = _metadata(data)

    timestamp = np.asarray(data["timestamp"], dtype=np.float64)
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
    base_step_world = np.diff(base_pose[:, :3], axis=0) if base_pose.shape[0] > 1 else np.zeros((0, 3))
    target_step_base = np.diff(target_base, axis=0) if target_base.shape[0] > 1 else np.zeros((0, 3))
    eef_step_base = np.diff(eef_base, axis=0) if eef_base.shape[0] > 1 else np.zeros((0, 3))
    joint_step = np.diff(joints, axis=0) if joints.shape[0] > 1 else np.zeros((0, joints.shape[1]))
    action_xyz = actions[:, :3]
    action_norm = np.linalg.norm(action_xyz, axis=1)
    action_positive = action_norm > 1e-9
    max_linear_step = float(metadata.get("max_linear_step") or 0.0)
    max_joint_delta = float(metadata.get("max_joint_delta") or 0.0)
    if max_linear_step > 0.0:
        component_clip_fraction = float(np.mean(np.isclose(np.abs(action_xyz), max_linear_step, rtol=1e-4, atol=1e-5)))
        sample_clip_fraction = float(np.mean(np.any(np.isclose(np.abs(action_xyz), max_linear_step, rtol=1e-4, atol=1e-5), axis=1)))
    else:
        component_clip_fraction = float("nan")
        sample_clip_fraction = float("nan")

    action_relative_cosines = [
        _cosine(action_xyz[index], relative_base[index])
        for index in range(action_xyz.shape[0])
        if action_positive[index]
    ]
    lag_scan = [_lag_metrics(action_xyz, eef_step_base, relative_base, distance_base, lag) for lag in range(max_lag_steps + 1)]
    best_lag = max(
        lag_scan,
        key=lambda item: -1.0
        if not np.isfinite(float(item["mean_action_to_eef_cosine"]))
        else float(item["mean_action_to_eef_cosine"]),
    )

    initial_base = base_pose[0, :3]
    initial_target_base = target_base[0]
    initial_eef_base = eef_base[0]
    initial_relative_base = relative_base[0]
    initial_joints = joints[0]
    success = bool(np.asarray(data["success"]).item())
    min_index = int(np.argmin(distance))
    below_indices = [int(index) for index, value in enumerate(distance.tolist()) if float(value) < threshold]

    return {
        "episode_id": str(metadata.get("episode_id", path.stem)),
        "episode_index": _episode_index(path),
        "path": str(path),
        "success": success,
        "group": "success_0000_0006" if success else "failure_0007_0009",
        "T": int(timestamp.shape[0]),
        "duration_sec": _float(float(timestamp[-1] - timestamp[0]) if timestamp.shape[0] > 1 else 0.0),
        "metadata": {
            "allow_nominal_state_fallback": metadata.get("allow_nominal_state_fallback"),
            "base_state_source": metadata.get("base_state_source"),
            "joint_state_source": metadata.get("joint_state_source"),
            "target_state_source": metadata.get("target_state_source"),
            "eef_pose_source": metadata.get("eef_pose_source"),
            "task_type": metadata.get("task_type"),
            "success_metric": metadata.get("success_metric"),
            "success_source": metadata.get("success_source"),
            "recorded_success_distance_m": metadata.get("recorded_success_distance_m"),
            "recorded_success_distance_threshold_m": metadata.get("recorded_success_distance_threshold_m"),
            "gripper_enabled": metadata.get("gripper_enabled"),
            "is_grasp_dataset": metadata.get("is_grasp_dataset"),
            "max_linear_step": metadata.get("max_linear_step"),
            "max_joint_delta": metadata.get("max_joint_delta"),
            "target_model_name": metadata.get("target_model_name"),
        },
        "distance": {
            "initial": _float(float(distance[0])),
            "minimum": _float(float(np.min(distance))),
            "min_index": min_index,
            "final": _float(float(distance[-1])),
            "reduction": _float(float(distance[0] - distance[-1])),
            "final_minus_min": _float(float(distance[-1] - np.min(distance))),
            "below_threshold_count": len(below_indices),
            "below_threshold_indices": below_indices,
            "curve": [_float(float(value)) for value in distance.tolist()],
            "base_curve": [_float(float(value)) for value in distance_base.tolist()],
        },
        "initial_conditions": {
            "base_xyz": [_float(float(value)) for value in initial_base.tolist()],
            "base_yaw": _float(_yaw_from_quat_xyzw(base_pose[0, 3:7])),
            "base_xyz_drift_from_ep0": _float(float(np.linalg.norm(initial_base - reference["base_xyz"]))),
            "eef_xyz_world": [_float(float(value)) for value in eef_pose[0, :3].tolist()],
            "eef_xyz_base": [_float(float(value)) for value in initial_eef_base.tolist()],
            "eef_base_drift_from_ep0": _float(float(np.linalg.norm(initial_eef_base - reference["eef_base"]))),
            "target_xyz_world": [_float(float(value)) for value in target_pose[0, :3].tolist()],
            "target_xyz_base": [_float(float(value)) for value in initial_target_base.tolist()],
            "target_base_drift_from_ep0": _float(float(np.linalg.norm(initial_target_base - reference["target_base"]))),
            "relative_xyz_base": [_float(float(value)) for value in initial_relative_base.tolist()],
            "relative_base_drift_from_ep0": _float(float(np.linalg.norm(initial_relative_base - reference["relative_base"]))),
            "active_joint_positions": [_float(float(value)) for value in initial_joints.tolist()],
            "active_joint_initial_drift_from_ep0": _float(float(np.linalg.norm(initial_joints - reference["joints"]))),
            "active_joint_initial_max_abs_diff_from_ep0": _float(float(np.max(np.abs(initial_joints - reference["joints"])))),
        },
        "motion": {
            "base_world_path": _float(float(np.sum(np.linalg.norm(base_step_world, axis=1))) if base_step_world.size else 0.0),
            "base_world_net": _float(float(np.linalg.norm(base_pose[-1, :3] - base_pose[0, :3]))),
            "target_base_net": _float(float(np.linalg.norm(target_base[-1] - target_base[0]))),
            "target_base_max_step": _float(float(np.max(np.linalg.norm(target_step_base, axis=1))) if target_step_base.size else 0.0),
            "eef_base_net": _float(float(np.linalg.norm(eef_base[-1] - eef_base[0]))),
            "eef_base_path": _float(float(np.sum(np.linalg.norm(eef_step_base, axis=1))) if eef_step_base.size else 0.0),
            "mean_eef_step_base": _float(float(np.mean(np.linalg.norm(eef_step_base, axis=1))) if eef_step_base.size else 0.0),
        },
        "action": {
            "xyz_norm_mean": _float(float(np.mean(action_norm))),
            "xyz_norm_max": _float(float(np.max(action_norm))),
            "xyz_norm_sum": _float(float(np.sum(action_norm))),
            "mean_cosine_with_relative_base": _float(_finite_mean(action_relative_cosines)),
            "component_clip_fraction": _float(component_clip_fraction),
            "sample_clip_fraction": _float(sample_clip_fraction),
            "max_linear_step": _float(max_linear_step),
        },
        "command_motion": {
            "lag_scan": lag_scan,
            "best_lag_steps": int(best_lag["lag_steps"]),
            "best_action_to_eef_cosine": best_lag["mean_action_to_eef_cosine"],
            "best_eef_to_target_cosine": best_lag["mean_eef_to_target_cosine"],
            "best_realized_gain_along_action": best_lag["mean_realized_gain_along_action"],
            "best_distance_decreasing_ratio": best_lag["distance_decreasing_ratio"],
            "eef_path_over_action_path": _float(
                float(np.sum(np.linalg.norm(eef_step_base, axis=1)) / np.sum(action_norm))
                if eef_step_base.size and np.sum(action_norm) > 1e-12
                else float("nan")
            ),
        },
        "joints": {
            "max_delta_from_episode_start": _float(float(np.max(np.abs(joints - joints[0])))),
            "max_step_delta": _float(float(np.max(np.abs(joint_step))) if joint_step.size else 0.0),
            "near_joint_step_limit_fraction": _float(
                float(np.mean(np.isclose(np.abs(joint_step), max_joint_delta, rtol=1e-4, atol=1e-5)))
                if joint_step.size and max_joint_delta > 0.0
                else float("nan")
            ),
            "final_minus_initial": [_float(float(value)) for value in (joints[-1] - joints[0]).tolist()],
        },
        "observability_limits": {
            "raw_command_available": "raw_command" not in metadata.get("unavailable_fields", []),
            "ik_failure_logged_in_npz": False,
            "ik_failure_note": "NPZ contains actions and realized motion, but not MoveIt IK return codes or command acknowledgements.",
        },
    }


def _group_values(episodes: Sequence[Dict[str, object]], group: str, path: Sequence[str]) -> List[float]:
    values: List[float] = []
    for episode in episodes:
        if episode["group"] != group:
            continue
        item = episode
        for key in path:
            item = item[key]  # type: ignore[index]
        try:
            values.append(float(item))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            pass
    return values


def _group_compare(episodes: Sequence[Dict[str, object]], path: Sequence[str]) -> Dict[str, float]:
    success = _group_values(episodes, "success_0000_0006", path)
    failure = _group_values(episodes, "failure_0007_0009", path)
    return {
        "success_mean": _float(_finite_mean(success)),
        "success_std": _float(_finite_std(success)),
        "failure_mean": _float(_finite_mean(failure)),
        "failure_std": _float(_finite_std(failure)),
        "failure_minus_success": _float(_finite_mean(failure) - _finite_mean(success)),
    }


def _summarize(episodes: Sequence[Dict[str, object]]) -> Dict[str, object]:
    comparisons = {
        "initial_distance": _group_compare(episodes, ("distance", "initial")),
        "final_distance": _group_compare(episodes, ("distance", "final")),
        "distance_reduction": _group_compare(episodes, ("distance", "reduction")),
        "final_minus_min": _group_compare(episodes, ("distance", "final_minus_min")),
        "base_initial_drift_from_ep0": _group_compare(episodes, ("initial_conditions", "base_xyz_drift_from_ep0")),
        "target_base_initial_drift_from_ep0": _group_compare(episodes, ("initial_conditions", "target_base_drift_from_ep0")),
        "eef_base_initial_drift_from_ep0": _group_compare(episodes, ("initial_conditions", "eef_base_drift_from_ep0")),
        "relative_base_initial_drift_from_ep0": _group_compare(episodes, ("initial_conditions", "relative_base_drift_from_ep0")),
        "joint_initial_drift_from_ep0": _group_compare(episodes, ("initial_conditions", "active_joint_initial_drift_from_ep0")),
        "target_base_max_step": _group_compare(episodes, ("motion", "target_base_max_step")),
        "target_base_net": _group_compare(episodes, ("motion", "target_base_net")),
        "eef_base_path": _group_compare(episodes, ("motion", "eef_base_path")),
        "action_norm_mean": _group_compare(episodes, ("action", "xyz_norm_mean")),
        "action_relative_cosine": _group_compare(episodes, ("action", "mean_cosine_with_relative_base")),
        "component_clip_fraction": _group_compare(episodes, ("action", "component_clip_fraction")),
        "best_action_to_eef_cosine": _group_compare(episodes, ("command_motion", "best_action_to_eef_cosine")),
        "best_realized_gain_along_action": _group_compare(episodes, ("command_motion", "best_realized_gain_along_action")),
        "best_distance_decreasing_ratio": _group_compare(episodes, ("command_motion", "best_distance_decreasing_ratio")),
        "eef_path_over_action_path": _group_compare(episodes, ("command_motion", "eef_path_over_action_path")),
        "joint_episode_max_delta": _group_compare(episodes, ("joints", "max_delta_from_episode_start")),
    }

    likely_causes = []
    cm_drop = comparisons["best_action_to_eef_cosine"]["failure_minus_success"]
    gain_drop = comparisons["best_realized_gain_along_action"]["failure_minus_success"]
    reduction_drop = comparisons["distance_reduction"]["failure_minus_success"]
    action_dir_drop = comparisons["action_relative_cosine"]["failure_minus_success"]
    target_step_fail = comparisons["target_base_max_step"]["failure_mean"]
    joint_drift_delta = comparisons["joint_initial_drift_from_ep0"]["failure_minus_success"]
    eef_drift_delta = comparisons["eef_base_initial_drift_from_ep0"]["failure_minus_success"]

    likely_causes.append(
        {
            "rank": 1,
            "cause": "command_motion_alignment_degradation",
            "evidence": {
                "best_action_to_eef_cosine_failure_minus_success": cm_drop,
                "best_realized_gain_failure_minus_success": gain_drop,
                "distance_reduction_failure_minus_success": reduction_drop,
            },
            "interpretation": "Failed episodes show much weaker action-to-EEF coupling and realized gain.",
        }
    )
    likely_causes.append(
        {
            "rank": 2,
            "cause": "cross_episode_initial_condition_drift",
            "evidence": {
                "joint_initial_drift_failure_minus_success": joint_drift_delta,
                "eef_base_initial_drift_failure_minus_success": eef_drift_delta,
            },
            "interpretation": "Initial joint and EEF pose drift should be checked as a reset/accumulation issue.",
        }
    )
    likely_causes.append(
        {
            "rank": 3,
            "cause": "scripted_expert_action_direction_or_horizon_limit",
            "evidence": {
                "action_relative_cosine_failure_minus_success": action_dir_drop,
                "component_clip_fraction_comparison": comparisons["component_clip_fraction"],
            },
            "interpretation": "If action direction stays aligned while EEF motion degrades, the issue is more likely IK/controller response than action generation.",
        }
    )
    likely_causes.append(
        {
            "rank": 4,
            "cause": "target_base_sync",
            "evidence": {
                "target_base_max_step_failure_mean": target_step_fail,
                "target_base_max_step_comparison": comparisons["target_base_max_step"],
            },
            "interpretation": "Target/base sync is less likely if failed max steps remain below 0.03 m.",
        }
    )
    likely_causes.append(
        {
            "rank": 5,
            "cause": "episode_duration_or_termination",
            "evidence": {
                "T_values": [episode["T"] for episode in episodes],
                "duration_values": [episode["duration_sec"] for episode in episodes],
                "final_minus_min_comparison": comparisons["final_minus_min"],
            },
            "interpretation": "Duration is less likely if all episodes have the same T and failed episodes never get below threshold.",
        }
    )

    return {
        "episodes_total": len(episodes),
        "success_count": int(sum(bool(episode["success"]) for episode in episodes)),
        "failure_count": int(sum(not bool(episode["success"]) for episode in episodes)),
        "success_episode_ids": [episode["episode_id"] for episode in episodes if episode["success"]],
        "failure_episode_ids": [episode["episode_id"] for episode in episodes if not episode["success"]],
        "comparisons": comparisons,
        "likely_causes_ranked": likely_causes,
    }


def _flatten_row(episode: Dict[str, object]) -> Dict[str, object]:
    return {
        "episode_id": episode["episode_id"],
        "episode_index": episode["episode_index"],
        "success": episode["success"],
        "T": episode["T"],
        "duration_sec": episode["duration_sec"],
        "initial_distance": episode["distance"]["initial"],
        "min_distance": episode["distance"]["minimum"],
        "min_index": episode["distance"]["min_index"],
        "final_distance": episode["distance"]["final"],
        "distance_reduction": episode["distance"]["reduction"],
        "final_minus_min": episode["distance"]["final_minus_min"],
        "below_threshold_count": episode["distance"]["below_threshold_count"],
        "base_initial_drift_from_ep0": episode["initial_conditions"]["base_xyz_drift_from_ep0"],
        "target_base_initial_drift_from_ep0": episode["initial_conditions"]["target_base_drift_from_ep0"],
        "eef_base_initial_drift_from_ep0": episode["initial_conditions"]["eef_base_drift_from_ep0"],
        "relative_base_initial_drift_from_ep0": episode["initial_conditions"]["relative_base_drift_from_ep0"],
        "joint_initial_drift_from_ep0": episode["initial_conditions"]["active_joint_initial_drift_from_ep0"],
        "joint_initial_max_abs_diff_from_ep0": episode["initial_conditions"]["active_joint_initial_max_abs_diff_from_ep0"],
        "base_world_path": episode["motion"]["base_world_path"],
        "target_base_net": episode["motion"]["target_base_net"],
        "target_base_max_step": episode["motion"]["target_base_max_step"],
        "eef_base_path": episode["motion"]["eef_base_path"],
        "action_norm_mean": episode["action"]["xyz_norm_mean"],
        "action_norm_max": episode["action"]["xyz_norm_max"],
        "action_relative_cosine": episode["action"]["mean_cosine_with_relative_base"],
        "component_clip_fraction": episode["action"]["component_clip_fraction"],
        "sample_clip_fraction": episode["action"]["sample_clip_fraction"],
        "best_lag_steps": episode["command_motion"]["best_lag_steps"],
        "best_action_to_eef_cosine": episode["command_motion"]["best_action_to_eef_cosine"],
        "best_eef_to_target_cosine": episode["command_motion"]["best_eef_to_target_cosine"],
        "best_realized_gain_along_action": episode["command_motion"]["best_realized_gain_along_action"],
        "best_distance_decreasing_ratio": episode["command_motion"]["best_distance_decreasing_ratio"],
        "eef_path_over_action_path": episode["command_motion"]["eef_path_over_action_path"],
        "joint_episode_max_delta": episode["joints"]["max_delta_from_episode_start"],
        "joint_max_step_delta": episode["joints"]["max_step_delta"],
    }


def _write_csv(rows: Sequence[Dict[str, object]], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_table_md(rows: Sequence[Dict[str, object]], path: Path) -> None:
    columns = [
        "episode_id",
        "success",
        "initial_distance",
        "min_distance",
        "final_distance",
        "distance_reduction",
        "joint_initial_drift_from_ep0",
        "target_base_max_step",
        "action_relative_cosine",
        "best_action_to_eef_cosine",
        "best_realized_gain_along_action",
    ]
    lines = [
        "# B8' Debug Batch Success vs Failure Table",
        "",
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in rows:
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:.6f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary_md(report: Dict[str, object], path: Path) -> None:
    summary = report["summary"]
    comparisons = summary["comparisons"]
    lines = [
        "# B8' Debug Batch Failure Analysis",
        "",
        "Analysis label: B8' debug batch failure analysis: existing b8_reaching_debug_10 only.",
        "",
        "This is offline-only analysis. It is not training, learned rollout, gripper handling, or grasp evaluation.",
        "",
        "## Batch Result",
        "",
        f"- episodes_total: {summary['episodes_total']}",
        f"- success_count: {summary['success_count']}",
        f"- failure_count: {summary['failure_count']}",
        f"- success episodes: {', '.join(summary['success_episode_ids'])}",
        f"- failure episodes: {', '.join(summary['failure_episode_ids'])}",
        "",
        "## Success vs Failure Means",
        "",
        "| metric | success_mean | failure_mean | failure_minus_success |",
        "| --- | ---: | ---: | ---: |",
    ]
    for key, values in comparisons.items():
        lines.append(
            f"| {key} | {values['success_mean']:.6f} | {values['failure_mean']:.6f} | {values['failure_minus_success']:.6f} |"
        )
    lines.extend(["", "## Ranked Causes", ""])
    for cause in summary["likely_causes_ranked"]:
        lines.extend(
            [
                f"### {cause['rank']}. {cause['cause']}",
                "",
                cause["interpretation"],
                "",
                "Evidence:",
                "",
            ]
        )
        for key, value in cause["evidence"].items():
            lines.append(f"- `{key}`: {value}")
        lines.append("")
    lines.extend(
        [
            "## Decision",
            "",
            "The 10-episode batch remains valid non-fallback arm-only debug data, but it should not be expanded or used for training until the tail-episode command-to-motion degradation is explained.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _plot_artifacts(episodes: Sequence[Dict[str, object]], rows: Sequence[Dict[str, object]], output_dir: Path) -> Dict[str, object]:
    artifacts: Dict[str, object] = {}
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - depends on local environment
        return {"plots_skipped": str(exc)}

    output_dir.mkdir(parents=True, exist_ok=True)
    indices = [int(row["episode_index"]) for row in rows]
    colors = ["#2a9d8f" if row["success"] else "#d62828" for row in rows]

    plt.figure(figsize=(10, 5))
    for episode in episodes:
        distance = episode["distance"]["curve"]
        color = "#2a9d8f" if episode["success"] else "#d62828"
        plt.plot(range(len(distance)), distance, color=color, alpha=0.75, label=episode["episode_id"])
    plt.axhline(0.10, color="#333333", linestyle="--", linewidth=1)
    plt.xlabel("sample index")
    plt.ylabel("distance to target (m)")
    plt.title("B8 debug batch distance curves")
    plt.tight_layout()
    distance_path = output_dir / "per_episode_distance_curves.png"
    plt.savefig(distance_path, dpi=150)
    plt.close()
    artifacts["per_episode_distance_curves_png"] = str(distance_path)

    plt.figure(figsize=(10, 5))
    plt.scatter(
        [row["best_action_to_eef_cosine"] for row in rows],
        [row["best_realized_gain_along_action"] for row in rows],
        c=colors,
        s=70,
    )
    for row in rows:
        plt.text(row["best_action_to_eef_cosine"], row["best_realized_gain_along_action"], str(row["episode_index"]))
    plt.xlabel("best action-to-EEF cosine")
    plt.ylabel("best realized gain along action")
    plt.title("Command-motion success vs failure")
    plt.tight_layout()
    command_path = output_dir / "command_motion_success_vs_failure.png"
    plt.savefig(command_path, dpi=150)
    plt.close()
    artifacts["command_motion_success_vs_failure_png"] = str(command_path)

    plt.figure(figsize=(10, 5))
    plt.plot(indices, [row["joint_initial_drift_from_ep0"] for row in rows], marker="o", color="#457b9d")
    plt.scatter(indices, [row["joint_initial_drift_from_ep0"] for row in rows], c=colors, s=60)
    plt.xlabel("episode index")
    plt.ylabel("initial joint drift from episode 0000 (rad L2)")
    plt.title("Initial active-left joint drift")
    plt.tight_layout()
    joint_path = output_dir / "joint_initial_drift.png"
    plt.savefig(joint_path, dpi=150)
    plt.close()
    artifacts["joint_initial_drift_png"] = str(joint_path)

    plt.figure(figsize=(10, 5))
    plt.plot(indices, [row["base_initial_drift_from_ep0"] for row in rows], marker="o", label="base initial drift")
    plt.plot(indices, [row["target_base_initial_drift_from_ep0"] for row in rows], marker="o", label="target-in-base initial drift")
    plt.plot(indices, [row["relative_base_initial_drift_from_ep0"] for row in rows], marker="o", label="relative initial drift")
    plt.xlabel("episode index")
    plt.ylabel("drift from episode 0000 (m)")
    plt.title("Base/target/relative initial drift")
    plt.legend()
    plt.tight_layout()
    drift_path = output_dir / "base_target_drift.png"
    plt.savefig(drift_path, dpi=150)
    plt.close()
    artifacts["base_target_drift_png"] = str(drift_path)

    return artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline B8 debug batch failure analysis.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--pattern", default="b8_reaching_debug_10_*.npz")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--threshold", type=float, default=0.10)
    parser.add_argument("--max-lag-steps", type=int, default=3)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    paths = sorted(input_dir.glob(args.pattern))
    if not paths:
        raise FileNotFoundError(f"no episodes found: {input_dir}/{args.pattern}")

    with np.load(str(paths[0]), allow_pickle=False) as first:
        base_pose = np.asarray(first["base_pose"], dtype=np.float64)
        target_pose = np.asarray(first["target_pose"], dtype=np.float64)
        eef_pose = np.asarray(first["eef_pose"], dtype=np.float64)
        joints = np.asarray(first["active_joint_positions"], dtype=np.float64)
        target_base = _points_world_to_base(target_pose[:, :3], base_pose)
        eef_base = _points_world_to_base(eef_pose[:, :3], base_pose)
        reference = {
            "base_xyz": base_pose[0, :3],
            "target_base": target_base[0],
            "eef_base": eef_base[0],
            "relative_base": target_base[0] - eef_base[0],
            "joints": joints[0],
        }

    episodes = [_load_episode(path, args.threshold, args.max_lag_steps, reference) for path in paths]
    rows = [_flatten_row(episode) for episode in episodes]
    summary = _summarize(episodes)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "analysis_label": "B8' debug batch failure analysis：分析 b8_reaching_debug_10 中 0007–0009 连续失败，不训练、不扩采、不处理 gripper。",
        "input_dir": str(input_dir),
        "pattern": args.pattern,
        "threshold": args.threshold,
        "summary": summary,
        "episodes": episodes,
    }
    plot_artifacts = _plot_artifacts(episodes, rows, output_dir)
    report["plot_artifacts"] = plot_artifacts

    (output_dir / "failure_analysis_summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_summary_md(report, output_dir / "failure_analysis_summary.md")
    _write_csv(rows, output_dir / "success_vs_failure_table.csv")
    _write_table_md(rows, output_dir / "success_vs_failure_table.md")
    drift = {
        "base_initial_drift_from_ep0": [row["base_initial_drift_from_ep0"] for row in rows],
        "target_base_initial_drift_from_ep0": [row["target_base_initial_drift_from_ep0"] for row in rows],
        "eef_base_initial_drift_from_ep0": [row["eef_base_initial_drift_from_ep0"] for row in rows],
        "relative_base_initial_drift_from_ep0": [row["relative_base_initial_drift_from_ep0"] for row in rows],
        "joint_initial_drift_from_ep0": [row["joint_initial_drift_from_ep0"] for row in rows],
    }
    (output_dir / "initial_condition_drift.json").write_text(
        json.dumps(drift, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    compact = {
        "episodes_total": summary["episodes_total"],
        "success_count": summary["success_count"],
        "failure_count": summary["failure_count"],
        "comparisons": summary["comparisons"],
        "likely_causes_ranked": summary["likely_causes_ranked"],
        "plot_artifacts": plot_artifacts,
    }
    print(json.dumps(compact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
