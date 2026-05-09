#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np
import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from learning.datasets.uvms_episode_dataset import UVMSEpisodeDataset, load_stats  # noqa: E402


def _load_json(path: Path) -> Dict[str, object]:
    with path.expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_yaml(path: Path) -> Dict[str, object]:
    with path.expanduser().open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a YAML mapping")
    return data


def _json_safe(value):
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _as_array(items: Sequence[Sequence[float]]) -> np.ndarray:
    return np.asarray(items, dtype=np.float64)


def _history_array(history: Sequence[Mapping[str, object]], key: str) -> np.ndarray:
    return _as_array([row[key] for row in history])


def _norm_rows(values: np.ndarray) -> np.ndarray:
    return np.linalg.norm(values, axis=1)


def _diff_summary(a: np.ndarray, b: np.ndarray) -> Dict[str, object]:
    diff = b - a
    return {
        "cycle1_minus_cycle0": diff.tolist(),
        "abs_delta": np.abs(diff).tolist(),
        "l2_delta": float(np.linalg.norm(diff)),
    }


def _sequence_summary(values: np.ndarray) -> Dict[str, object]:
    if values.size == 0:
        return {}
    return {
        "first": values[0].tolist() if values.ndim > 1 else float(values[0]),
        "last": values[-1].tolist() if values.ndim > 1 else float(values[-1]),
        "mean": values.mean(axis=0).tolist() if values.ndim > 1 else float(values.mean()),
        "min": values.min(axis=0).tolist() if values.ndim > 1 else float(values.min()),
        "max": values.max(axis=0).tolist() if values.ndim > 1 else float(values.max()),
        "range": (values.max(axis=0) - values.min(axis=0)).tolist()
        if values.ndim > 1
        else float(values.max() - values.min()),
    }


def _load_raw_dataset(config: Mapping[str, object], split: str) -> UVMSEpisodeDataset:
    dataset_cfg = dict((config.get("dataset", {}) or {}))
    dataset_cfg["normalize"] = False
    return UVMSEpisodeDataset.from_config(dataset_cfg, split=split)


def _dataset_obs_matrix(dataset: UVMSEpisodeDataset) -> np.ndarray:
    rows = []
    for episode in dataset.episodes:
        rows.append(np.asarray(episode["obs"], dtype=np.float64))
    return np.concatenate(rows, axis=0)


def _dataset_action_matrix(dataset: UVMSEpisodeDataset) -> np.ndarray:
    rows = []
    for episode in dataset.episodes:
        rows.append(np.asarray(episode["action"], dtype=np.float64))
    return np.concatenate(rows, axis=0)


def _feature_indices(dataset: UVMSEpisodeDataset, prefix: str) -> List[int]:
    return [idx for idx, name in enumerate(dataset.feature_names) if name.startswith(prefix + "/")]


def _zscore(values: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return (values - mean) / np.maximum(std, 1e-12)


def _percentile_position(reference_abs: np.ndarray, values_abs: np.ndarray) -> List[float]:
    flat_ref = np.asarray(reference_abs, dtype=np.float64)
    output = []
    for value in np.asarray(values_abs, dtype=np.float64).reshape(-1):
        output.append(float(np.mean(flat_ref <= value)))
    return output


def _compare_cycle(
    index: int,
    smoke: Mapping[str, object],
    post_gate: Mapping[str, object],
    summary: Mapping[str, object],
) -> Dict[str, object]:
    history = smoke.get("history", []) or []
    distances = np.asarray([float(row["distance_to_target"]) for row in history], dtype=np.float64)
    raw = _history_array(history, "raw_action_xyz")
    clipped = _history_array(history, "clipped_action_xyz")
    raw_joint = _history_array(history, "raw_joint_delta")
    clipped_joint = _history_array(history, "clipped_joint_delta")
    target_to_eef = _history_array(history, "target_to_eef_base_frame")
    target_base = _history_array(history, "target_position_base_frame")
    eef_base = _history_array(history, "eef_position_base_frame")
    component_clipped = [bool((row.get("clip", {}) or {}).get("component_clipped")) for row in history]
    norm_clipped = [bool((row.get("clip", {}) or {}).get("norm_clipped")) for row in history]
    metrics = summary.get("metrics", {}) or {}

    distance_delta = np.diff(distances) if len(distances) > 1 else np.asarray([], dtype=np.float64)
    raw_norm = _norm_rows(raw)
    clipped_norm = _norm_rows(clipped)
    raw_joint_absmax = np.max(np.abs(raw_joint), axis=1)
    clipped_joint_absmax = np.max(np.abs(clipped_joint), axis=1)

    return {
        "cycle_index": index,
        "status": smoke.get("status"),
        "aborted": smoke.get("aborted"),
        "abort_reason": smoke.get("abort_reason"),
        "samples": smoke.get("samples"),
        "control_commands_sent": smoke.get("control_commands_sent"),
        "gripper_commands_sent": smoke.get("gripper_commands_sent"),
        "hand_controller_started": smoke.get("hand_controller_started"),
        "smoke_status": summary.get("smoke_status"),
        "checks_passed": summary.get("checks_passed"),
        "failed_checks": [
            check.get("name")
            for check in summary.get("checks", [])
            if check.get("passed") is not True
        ],
        "distance_trace": distances.tolist(),
        "distance_delta_per_tick": distance_delta.tolist(),
        "distance_monotonic_nonincreasing": bool(np.all(distance_delta <= 1e-9))
        if distance_delta.size
        else True,
        "distance_first": float(distances[0]) if distances.size else None,
        "distance_last": float(distances[-1]) if distances.size else None,
        "smoke_distance_reduction": metrics.get("smoke_distance_reduction"),
        "gate_distance_reduction": metrics.get("gate_distance_reduction"),
        "post_gate_initial_distance": metrics.get("post_gate_initial_distance"),
        "post_gate_target_base_drift": metrics.get("post_gate_target_base_drift"),
        "post_gate_relative_base_drift": metrics.get("post_gate_relative_base_drift"),
        "raw_action_xyz_summary": _sequence_summary(raw),
        "clipped_action_xyz_summary": _sequence_summary(clipped),
        "raw_action_norm": raw_norm.tolist(),
        "clipped_action_norm": clipped_norm.tolist(),
        "clip_component_fraction": float(np.mean(component_clipped)) if component_clipped else None,
        "clip_norm_fraction": float(np.mean(norm_clipped)) if norm_clipped else None,
        "clip_xyz_l1_loss_mean": float(np.mean(np.abs(raw - clipped))) if raw.size else None,
        "clip_xyz_l2_loss_mean": float(np.mean(_norm_rows(raw - clipped))) if raw.size else None,
        "raw_joint_absmax": raw_joint_absmax.tolist(),
        "clipped_joint_absmax": clipped_joint_absmax.tolist(),
        "joint_clip_l2_loss_mean": float(np.mean(_norm_rows(raw_joint - clipped_joint)))
        if raw_joint.size
        else None,
        "target_to_eef_base_summary": _sequence_summary(target_to_eef),
        "target_position_base_summary": _sequence_summary(target_base),
        "eef_position_base_summary": _sequence_summary(eef_base),
        "post_gate_checks": post_gate.get("checks"),
        "post_gate_metrics": post_gate.get("metrics"),
    }


def _offline_diagnostics(
    config: Mapping[str, object],
    stats_path: Path,
    cycle_reports: Sequence[Mapping[str, object]],
) -> Dict[str, object]:
    train = _load_raw_dataset(config, "train")
    val = _load_raw_dataset(config, "val")
    stats = load_stats(str(stats_path))

    train_obs = _dataset_obs_matrix(train)
    val_obs = _dataset_obs_matrix(val)
    train_action = _dataset_action_matrix(train)
    val_action = _dataset_action_matrix(val)

    geometry_prefixes = [
        "eef_position_base_frame",
        "target_position_base_frame",
        "target_to_eef_base_frame",
    ]
    geometry_indices = {prefix: _feature_indices(train, prefix) for prefix in geometry_prefixes}

    live_geometry = {}
    for prefix in geometry_prefixes:
        key = prefix + "_summary"
        if prefix == "target_to_eef_base_frame":
            key = "target_to_eef_base_summary"
        elif prefix == "target_position_base_frame":
            key = "target_position_base_summary"
        elif prefix == "eef_position_base_frame":
            key = "eef_position_base_summary"
        live_geometry[prefix] = []
        for cycle in cycle_reports:
            summary = cycle[key]
            live_geometry[prefix].extend([summary["first"], summary["last"]])
        live_geometry[prefix] = np.asarray(live_geometry[prefix], dtype=np.float64)

    geometry_report: Dict[str, object] = {}
    for prefix, indices in geometry_indices.items():
        train_values = train_obs[:, indices]
        val_values = val_obs[:, indices]
        live_values = live_geometry[prefix]
        z = _zscore(
            live_values,
            stats.obs_mean[indices].astype(np.float64),
            stats.obs_std[indices].astype(np.float64),
        )
        train_z = _zscore(
            train_values,
            stats.obs_mean[indices].astype(np.float64),
            stats.obs_std[indices].astype(np.float64),
        )
        val_z = _zscore(
            val_values,
            stats.obs_mean[indices].astype(np.float64),
            stats.obs_std[indices].astype(np.float64),
        )
        geometry_report[prefix] = {
            "feature_indices": indices,
            "live_values_first_last_per_cycle": live_values.tolist(),
            "live_abs_z_max": float(np.max(np.abs(z))),
            "live_abs_z_p95": float(np.percentile(np.abs(z), 95)),
            "train_abs_z_p99": float(np.percentile(np.abs(train_z), 99)),
            "val_abs_z_p99": float(np.percentile(np.abs(val_z), 99)),
            "live_range": (live_values.max(axis=0) - live_values.min(axis=0)).tolist(),
            "train_min": train_values.min(axis=0).tolist(),
            "train_max": train_values.max(axis=0).tolist(),
            "val_min": val_values.min(axis=0).tolist(),
            "val_max": val_values.max(axis=0).tolist(),
        }

    all_live_raw = []
    all_live_clipped = []
    for cycle in cycle_reports:
        # Reconstruct from summary min/max/mean is insufficient for every tick, so
        # use representative first/last for distribution placement.
        all_live_raw.append(np.asarray(cycle["raw_action_xyz_summary"]["first"], dtype=np.float64))
        all_live_raw.append(np.asarray(cycle["raw_action_xyz_summary"]["last"], dtype=np.float64))
        all_live_clipped.append(np.asarray(cycle["clipped_action_xyz_summary"]["first"], dtype=np.float64))
        all_live_clipped.append(np.asarray(cycle["clipped_action_xyz_summary"]["last"], dtype=np.float64))
    live_raw = np.vstack(all_live_raw)
    live_clipped = np.vstack(all_live_clipped)

    action_z = _zscore(
        live_raw,
        stats.action_mean.astype(np.float64),
        stats.action_std.astype(np.float64),
    )
    train_abs = np.abs(train_action)
    val_abs = np.abs(val_action)
    live_abs = np.abs(live_raw)
    live_clip_abs = np.abs(live_clipped)

    return {
        "dataset": {
            "train_samples": len(train),
            "val_samples": len(val),
            "obs_dim": train.obs_dim,
            "action_dim": train.action_dim,
            "feature_names": train.feature_names,
        },
        "safe_action_normalization": {
            "action_mean": stats.action_mean.tolist(),
            "action_std": stats.action_std.tolist(),
            "config_action_std_epsilon": (config.get("dataset", {}) or {}).get("action_std_epsilon"),
            "config_action_std_fallback": (config.get("dataset", {}) or {}).get("action_std_fallback"),
        },
        "geometry_ood": geometry_report,
        "action_distribution": {
            "train_abs_p95": np.percentile(train_abs, 95, axis=0).tolist(),
            "train_abs_p99": np.percentile(train_abs, 99, axis=0).tolist(),
            "train_abs_max": train_abs.max(axis=0).tolist(),
            "val_abs_p95": np.percentile(val_abs, 95, axis=0).tolist(),
            "val_abs_p99": np.percentile(val_abs, 99, axis=0).tolist(),
            "val_abs_max": val_abs.max(axis=0).tolist(),
            "live_raw_representative": live_raw.tolist(),
            "live_clipped_representative": live_clipped.tolist(),
            "live_raw_absmax": float(np.max(live_abs)),
            "live_clipped_absmax": float(np.max(live_clip_abs)),
            "live_raw_abs_z_max": float(np.max(np.abs(action_z))),
            "live_raw_abs_z_p95": float(np.percentile(np.abs(action_z), 95)),
            "live_raw_percentile_vs_train_abs": _percentile_position(train_abs, live_abs),
        },
    }


def _decision(live: Mapping[str, object], offline: Mapping[str, object]) -> Dict[str, object]:
    c0, c1 = live["cycles"]
    cycle1_failed = c1["checks_passed"] is not True
    policy_instability = (
        np.linalg.norm(
            np.asarray(c1["raw_action_xyz_summary"]["mean"])
            - np.asarray(c0["raw_action_xyz_summary"]["mean"])
        )
        > 0.002
    )
    target_drift_boundary = float(c1["post_gate_target_base_drift"]) > 0.01
    insufficient_motion = float(c1["gate_distance_reduction"]) < 0.02
    clip_limited = (
        float(c0["clip_component_fraction"]) >= 1.0
        and float(c1["clip_component_fraction"]) >= 1.0
        and offline["action_distribution"]["live_raw_absmax"]
        > offline["action_distribution"]["live_clipped_absmax"] * 1.5
    )
    geometry_abs_z = max(
        float(item["live_abs_z_max"]) for item in offline["geometry_ood"].values()
    )
    geometry_ood = geometry_abs_z > 3.0

    likely_causes = []
    if cycle1_failed:
        if target_drift_boundary:
            likely_causes.append(
                "cycle_1 target_base_drift is just over the strict 0.01 m threshold"
            )
        if insufficient_motion:
            likely_causes.append(
                "cycle_1 distance reduction is below the 0.02 m arm-only success threshold"
            )
        if clip_limited:
            likely_causes.append(
                "policy repeatedly asks for near-demonstration-scale x/z actions but live safety clip halves x/z to 0.005 m"
            )
        if not policy_instability:
            likely_causes.append(
                "raw policy outputs are stable across cycles; failure is not explained by output instability"
            )
        if geometry_ood:
            likely_causes.append(
                "some live base-relative geometry is outside the nominal normalized training range"
            )
    return {
        "n3_repeatability_resolved": False,
        "cycle1_failed": cycle1_failed,
        "policy_output_instability_detected": policy_instability,
        "target_drift_boundary_detected": target_drift_boundary,
        "insufficient_motion_detected": insufficient_motion,
        "clip_limited_motion_detected": clip_limited,
        "geometry_ood_detected": geometry_ood,
        "likely_causes": likely_causes,
        "next_steps": [
            "Do not run another live smoke immediately.",
            "Keep DP/FM offline-only.",
            "If continuing, inspect whether fixed max_control_ticks=5 is too brittle under target drift and clipped x/z commands.",
            "Consider offline-only checks for a smaller/larger clip or tick-budget sensitivity before any live rerun.",
        ],
    }


def _write_markdown(payload: Mapping[str, object], path: Path) -> None:
    live = payload["live_artifact_comparison"]
    c0, c1 = live["cycles"]
    offline = payload["offline_model_diagnostics"]
    decision = payload["decision"]
    lines = [
        "# B8 N=3 Repeatability Failure Read-Only Diagnosis",
        "",
        "This report is read-only/offline-only. It does not send arm commands,",
        "does not start a hand controller, does not send gripper commands, and",
        "does not train BC/DP/FM.",
        "",
        "## Decision",
        "",
        f"- N=3 repeatability resolved: `{decision['n3_repeatability_resolved']}`",
        f"- Cycle 1 failed: `{decision['cycle1_failed']}`",
        f"- Policy output instability detected: `{decision['policy_output_instability_detected']}`",
        f"- Target drift boundary detected: `{decision['target_drift_boundary_detected']}`",
        f"- Insufficient motion detected: `{decision['insufficient_motion_detected']}`",
        f"- Clip-limited motion detected: `{decision['clip_limited_motion_detected']}`",
        f"- Geometry OOD detected: `{decision['geometry_ood_detected']}`",
        "",
        "Likely causes:",
    ]
    for item in decision["likely_causes"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Live Cycle Comparison",
            "",
            "| metric | cycle 0 | cycle 1 |",
            "|---|---:|---:|",
            f"| smoke status | `{c0['smoke_status']}` | `{c1['smoke_status']}` |",
            f"| checks passed | `{c0['checks_passed']}` | `{c1['checks_passed']}` |",
            f"| first distance | {c0['distance_first']} | {c1['distance_first']} |",
            f"| last smoke distance | {c0['distance_last']} | {c1['distance_last']} |",
            f"| smoke distance reduction | {c0['smoke_distance_reduction']} | {c1['smoke_distance_reduction']} |",
            f"| gate distance reduction | {c0['gate_distance_reduction']} | {c1['gate_distance_reduction']} |",
            f"| post target drift | {c0['post_gate_target_base_drift']} | {c1['post_gate_target_base_drift']} |",
            f"| post relative drift | {c0['post_gate_relative_base_drift']} | {c1['post_gate_relative_base_drift']} |",
            f"| component clip fraction | {c0['clip_component_fraction']} | {c1['clip_component_fraction']} |",
            f"| raw action mean | `{c0['raw_action_xyz_summary']['mean']}` | `{c1['raw_action_xyz_summary']['mean']}` |",
            f"| clipped action mean | `{c0['clipped_action_xyz_summary']['mean']}` | `{c1['clipped_action_xyz_summary']['mean']}` |",
            "",
            "Cycle 0 distance trace:",
            "",
            "```text",
            str(c0["distance_trace"]),
            "```",
            "",
            "Cycle 1 distance trace:",
            "",
            "```text",
            str(c1["distance_trace"]),
            "```",
            "",
            "## Offline Model Diagnostics",
            "",
            "Safe action normalization:",
            "",
            "```text",
            json.dumps(offline["safe_action_normalization"], indent=2, sort_keys=True),
            "```",
            "",
            "Action distribution placement:",
            "",
            "```text",
            json.dumps(offline["action_distribution"], indent=2, sort_keys=True),
            "```",
            "",
            "Geometry OOD summary:",
            "",
            "```text",
            json.dumps(
                {
                    key: {
                        "live_abs_z_max": value["live_abs_z_max"],
                        "train_abs_z_p99": value["train_abs_z_p99"],
                        "val_abs_z_p99": value["val_abs_z_p99"],
                        "live_range": value["live_range"],
                    }
                    for key, value in offline["geometry_ood"].items()
                },
                indent=2,
                sort_keys=True,
            ),
            "```",
            "",
            "## Next",
            "",
        ]
    )
    for item in decision["next_steps"]:
        lines.append(f"- {item}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only diagnosis for B8 N=3 base-relative BC repeatability failure."
    )
    base = PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3"
    parser.add_argument("--cycle0-dir", type=Path, default=base / "cycle_0")
    parser.add_argument("--cycle1-dir", type=Path, default=base / "cycle_1")
    parser.add_argument(
        "--config",
        type=Path,
        default=PACKAGE_ROOT / "config/train_bc_b8_primary30_h8_xyz_base_relative_safe_norm.yaml",
    )
    parser.add_argument(
        "--stats",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/checkpoints/b8_primary30_bc_h8_xyz_base_relative_safe_norm/normalization_stats.json",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/read_only_failure_diagnosis.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/read_only_failure_diagnosis.md",
    )
    args = parser.parse_args()

    cycles = []
    for index, cycle_dir in enumerate([args.cycle0_dir, args.cycle1_dir]):
        smoke = _load_json(cycle_dir / "smoke.json")
        post_gate = _load_json(cycle_dir / "post_gate/post_smoke_gate.json")
        summary = _load_json(cycle_dir / "summary.json")
        cycles.append(_compare_cycle(index, smoke, post_gate, summary))

    config = _load_yaml(args.config)
    offline = _offline_diagnostics(config, args.stats, cycles)
    live = {
        "cycle_count": len(cycles),
        "cycles": cycles,
        "cycle1_minus_cycle0": {
            "raw_action_mean": _diff_summary(
                np.asarray(cycles[0]["raw_action_xyz_summary"]["mean"]),
                np.asarray(cycles[1]["raw_action_xyz_summary"]["mean"]),
            ),
            "clipped_action_mean": _diff_summary(
                np.asarray(cycles[0]["clipped_action_xyz_summary"]["mean"]),
                np.asarray(cycles[1]["clipped_action_xyz_summary"]["mean"]),
            ),
            "target_base_first": _diff_summary(
                np.asarray(cycles[0]["target_position_base_summary"]["first"]),
                np.asarray(cycles[1]["target_position_base_summary"]["first"]),
            ),
            "target_to_eef_first": _diff_summary(
                np.asarray(cycles[0]["target_to_eef_base_summary"]["first"]),
                np.asarray(cycles[1]["target_to_eef_base_summary"]["first"]),
            ),
        },
    }
    payload = {
        "tool": "analyze_b8_n3_repeatability_failure",
        "offline_only": True,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "hand_controller_started": False,
        "training_started": False,
        "dp_fm_live_execution": False,
        "live_artifact_comparison": live,
        "offline_model_diagnostics": offline,
        "decision": _decision(live, offline),
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = _json_safe(payload)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(payload, args.output_md)
    print(json.dumps(payload["decision"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
