#!/usr/bin/env python3

import argparse
import json
import math
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, object]:
    with path.expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


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


def _history_array(history: Sequence[Mapping[str, object]], key: str) -> np.ndarray:
    return np.asarray([row[key] for row in history], dtype=np.float64)


def _norm_rows(values: np.ndarray) -> np.ndarray:
    return np.linalg.norm(values, axis=1)


def _clip_candidate(raw: np.ndarray, clip_limit: float) -> np.ndarray:
    clipped = raw.copy()
    clipped[:, 0] = np.clip(clipped[:, 0], -clip_limit, clip_limit)
    clipped[:, 2] = np.clip(clipped[:, 2], -clip_limit, clip_limit)
    return clipped


def _required_ticks(
    current_ticks: int,
    current_reduction: float,
    required_reduction: float,
    scale: float,
) -> int:
    if current_reduction <= 0.0 or scale <= 0.0:
        return 10**9
    return int(math.floor(required_reduction / (current_reduction * scale / current_ticks)) + 1)


def _project_cycle(
    index: int,
    smoke: Mapping[str, object],
    summary: Mapping[str, object],
    clip_limits: Sequence[float],
    tick_budgets: Sequence[int],
    success_reduction_min: float,
    success_distance_max: float,
    target_base_drift_max: float,
) -> Dict[str, object]:
    history = smoke.get("history", []) or []
    distances = np.asarray([float(row["distance_to_target"]) for row in history], dtype=np.float64)
    raw = _history_array(history, "raw_action_xyz")
    clipped = _history_array(history, "clipped_action_xyz")
    raw_joint = _history_array(history, "raw_joint_delta")
    clipped_joint = _history_array(history, "clipped_joint_delta")
    metrics = summary.get("metrics", {}) or {}
    current_ticks = int(smoke.get("max_control_ticks", len(history)))
    current_clip = float(smoke.get("max_policy_xyz_component", 0.005))

    smoke_reduction = float(metrics.get("smoke_distance_reduction", distances[0] - distances[-1]))
    gate_reduction = float(metrics.get("gate_distance_reduction", 0.0))
    pre_gate_distance = float(metrics.get("pre_gate_1_initial_distance", distances[0]))
    post_gate_distance = float(metrics.get("post_gate_initial_distance", pre_gate_distance - gate_reduction))
    target_base_drift = float(metrics.get("post_gate_target_base_drift", float("inf")))
    current_pass_by_gate_distance = bool(
        post_gate_distance <= success_distance_max and gate_reduction > success_reduction_min
    )
    current_pass_all_modeled = bool(
        current_pass_by_gate_distance and target_base_drift <= target_base_drift_max
    )

    raw_norm = _norm_rows(raw)
    clipped_norm = _norm_rows(clipped)
    raw_joint_absmax = np.max(np.abs(raw_joint), axis=1)
    clipped_joint_absmax = np.max(np.abs(clipped_joint), axis=1)
    joint_clip_fraction = float(np.mean(raw_joint_absmax > clipped_joint_absmax + 1e-9))

    projections = []
    for clip_limit in clip_limits:
        candidate_clip = _clip_candidate(raw, clip_limit)
        candidate_norm = _norm_rows(candidate_clip)
        # Conservative scalar approximation: distance improvement scales with
        # mean clipped action norm relative to the actually executed clipped norm.
        clip_scale = float(np.mean(candidate_norm / np.maximum(clipped_norm, 1e-12)))
        clip_scale = max(0.0, clip_scale)
        candidate_component_fraction = float(np.mean(np.max(np.abs(raw[:, [0, 2]]), axis=1) > clip_limit))
        for ticks in tick_budgets:
            tick_scale = float(ticks) / float(max(current_ticks, 1))
            smoke_projected_reduction = smoke_reduction * clip_scale * tick_scale
            gate_projected_reduction = gate_reduction * clip_scale * tick_scale
            smoke_projected_final = distances[0] - smoke_projected_reduction
            gate_projected_final = pre_gate_distance - gate_projected_reduction
            pass_distance = bool(
                gate_projected_final <= success_distance_max
                and gate_projected_reduction > success_reduction_min
            )
            pass_with_static_target_drift = bool(
                pass_distance and target_base_drift <= target_base_drift_max
            )
            projections.append(
                {
                    "clip_limit": clip_limit,
                    "tick_budget": ticks,
                    "clip_scale_vs_current": clip_scale,
                    "candidate_component_clip_fraction": candidate_component_fraction,
                    "smoke_projected_reduction": smoke_projected_reduction,
                    "smoke_projected_final_distance": smoke_projected_final,
                    "gate_projected_reduction": gate_projected_reduction,
                    "gate_projected_final_distance": gate_projected_final,
                    "distance_gate_pass_projected": pass_distance,
                    "target_drift_assumed_static": target_base_drift,
                    "all_modeled_pass_projected": pass_with_static_target_drift,
                }
            )

    required_ticks_current_clip = _required_ticks(
        current_ticks=current_ticks,
        current_reduction=gate_reduction,
        required_reduction=success_reduction_min,
        scale=1.0,
    )
    required_ticks_raw_scale = _required_ticks(
        current_ticks=current_ticks,
        current_reduction=gate_reduction,
        required_reduction=success_reduction_min,
        scale=float(np.mean(raw_norm / np.maximum(clipped_norm, 1e-12))),
    )

    return {
        "cycle_index": index,
        "current_ticks": current_ticks,
        "current_clip_limit": current_clip,
        "smoke_status": summary.get("smoke_status"),
        "checks_passed": summary.get("checks_passed"),
        "current_pass_by_gate_distance": current_pass_by_gate_distance,
        "current_pass_all_modeled": current_pass_all_modeled,
        "distance_trace": distances.tolist(),
        "distance_delta_per_interval": np.diff(distances).tolist(),
        "smoke_reduction": smoke_reduction,
        "gate_reduction": gate_reduction,
        "pre_gate_distance": pre_gate_distance,
        "post_gate_distance": post_gate_distance,
        "target_base_drift": target_base_drift,
        "relative_base_drift": metrics.get("post_gate_relative_base_drift"),
        "raw_action_absmax": float(np.max(np.abs(raw))),
        "clipped_action_absmax": float(np.max(np.abs(clipped))),
        "raw_action_norm_mean": float(np.mean(raw_norm)),
        "clipped_action_norm_mean": float(np.mean(clipped_norm)),
        "raw_to_clipped_norm_ratio_mean": float(np.mean(raw_norm / np.maximum(clipped_norm, 1e-12))),
        "raw_joint_absmax_mean": float(np.mean(raw_joint_absmax)),
        "clipped_joint_absmax_mean": float(np.mean(clipped_joint_absmax)),
        "joint_clip_fraction": joint_clip_fraction,
        "required_ticks_current_clip_for_reduction": required_ticks_current_clip,
        "required_ticks_raw_scale_for_reduction": required_ticks_raw_scale,
        "projection_grid": projections,
    }


def _decision(cycles: Sequence[Mapping[str, object]], success_reduction_min: float) -> Dict[str, object]:
    failed = [cycle for cycle in cycles if cycle["checks_passed"] is not True]
    cycle1 = cycles[1] if len(cycles) > 1 else None
    recommended = "offline_only_no_live_rerun"
    rationale = []
    if cycle1 is not None:
        if cycle1["gate_reduction"] < success_reduction_min:
            rationale.append("cycle_1 observed gate reduction is below threshold")
        if cycle1["target_base_drift"] > 0.01:
            rationale.append("cycle_1 target drift is over the strict post-target threshold")
        if cycle1["required_ticks_current_clip_for_reduction"] <= 8:
            rationale.append("tick budget appears plausible as a sensitivity axis")
        if cycle1["raw_to_clipped_norm_ratio_mean"] > 1.5:
            rationale.append("clip limit appears plausible as a sensitivity axis")
    if failed:
        recommended = "do_not_run_live_until_offline_plan_reviewed"

    return {
        "n3_repeatability_resolved": False,
        "live_rerun_approved": False,
        "dp_fm_live_approved": False,
        "training_started": False,
        "recommended_status": recommended,
        "rationale": rationale,
        "next_steps": [
            "Do not run another live smoke from this projection alone.",
            "Review the offline projection and decide whether the next candidate should change only one variable.",
            "If a future live rerun is approved, change either tick budget or clip limit, not both at once.",
            "Keep DP/FM offline-only.",
        ],
    }


def _write_markdown(payload: Mapping[str, object], path: Path) -> None:
    lines: List[str] = [
        "# B8 N=3 Tick/Clip Sensitivity Projection",
        "",
        "This is an offline-only replay-style projection from recorded N=3 cycle",
        "0/1 traces. It is not a Gazebo physics simulation and it does not",
        "approve another live run.",
        "",
        "## Decision",
        "",
    ]
    decision = payload["decision"]
    for key in [
        "n3_repeatability_resolved",
        "live_rerun_approved",
        "dp_fm_live_approved",
        "recommended_status",
    ]:
        lines.append(f"- {key}: `{decision[key]}`")
    lines.extend(["", "Rationale:"])
    for item in decision["rationale"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Cycle Summary",
            "",
            "| cycle | status | gate reduction | target drift | raw/clipped norm ratio | required ticks current clip | required ticks raw scale |",
            "|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for cycle in payload["cycles"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(cycle["cycle_index"]),
                    str(cycle["smoke_status"]),
                    str(cycle["gate_reduction"]),
                    str(cycle["target_base_drift"]),
                    str(cycle["raw_to_clipped_norm_ratio_mean"]),
                    str(cycle["required_ticks_current_clip_for_reduction"]),
                    str(cycle["required_ticks_raw_scale_for_reduction"]),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Projection Grid", ""])
    for cycle in payload["cycles"]:
        lines.extend(
            [
                f"### Cycle {cycle['cycle_index']}",
                "",
                "| clip | ticks | gate reduction | final distance | distance gate pass | all modeled pass |",
                "|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in cycle["projection_grid"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row["clip_limit"]),
                        str(row["tick_budget"]),
                        str(row["gate_projected_reduction"]),
                        str(row["gate_projected_final_distance"]),
                        str(row["distance_gate_pass_projected"]),
                        str(row["all_modeled_pass_projected"]),
                    ]
                )
                + " |"
            )
        lines.append("")

    lines.extend(["## Next", ""])
    for item in decision["next_steps"]:
        lines.append(f"- {item}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline-only tick budget and clip limit sensitivity projection for N=3 BC smoke."
    )
    base = PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3"
    parser.add_argument("--cycle0-dir", type=Path, default=base / "cycle_0")
    parser.add_argument("--cycle1-dir", type=Path, default=base / "cycle_1")
    parser.add_argument("--success-distance-max", type=float, default=0.10)
    parser.add_argument("--success-distance-reduction-min", type=float, default=0.02)
    parser.add_argument("--target-base-drift-max", type=float, default=0.01)
    parser.add_argument("--clip-limit", type=float, action="append", default=[0.005, 0.006, 0.0075, 0.01])
    parser.add_argument("--tick-budget", type=int, action="append", default=[5, 6, 7, 8])
    parser.add_argument(
        "--output-json",
        type=Path,
        default=base / "offline_tick_clip_sensitivity.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=base / "offline_tick_clip_sensitivity.md",
    )
    args = parser.parse_args()

    cycles = []
    for index, cycle_dir in enumerate([args.cycle0_dir, args.cycle1_dir]):
        cycles.append(
            _project_cycle(
                index=index,
                smoke=_load_json(cycle_dir / "smoke.json"),
                summary=_load_json(cycle_dir / "summary.json"),
                clip_limits=sorted(set(args.clip_limit)),
                tick_budgets=sorted(set(args.tick_budget)),
                success_reduction_min=args.success_distance_reduction_min,
                success_distance_max=args.success_distance_max,
                target_base_drift_max=args.target_base_drift_max,
            )
        )

    payload = {
        "tool": "analyze_b8_n3_tick_clip_sensitivity",
        "offline_only": True,
        "projection_only_not_physics_sim": True,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "hand_controller_started": False,
        "training_started": False,
        "dp_fm_live_execution": False,
        "success_thresholds": {
            "success_distance_max": args.success_distance_max,
            "success_distance_reduction_min": args.success_distance_reduction_min,
            "target_base_drift_max": args.target_base_drift_max,
        },
        "cycles": cycles,
        "decision": _decision(cycles, args.success_distance_reduction_min),
    }
    payload = _json_safe(payload)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(payload, args.output_md)
    print(json.dumps(payload["decision"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
