#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Dict, Mapping, Sequence

import numpy as np


def _load_json(path: Path) -> Dict[str, object]:
    with path.expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _json_safe(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _history_array(history: Sequence[Mapping[str, object]], key: str) -> np.ndarray:
    return np.asarray([row[key] for row in history], dtype=np.float64)


def _summary_array(values: np.ndarray) -> Dict[str, object]:
    if values.size == 0:
        return {}
    if values.ndim == 1:
        return {
            "first": float(values[0]),
            "last": float(values[-1]),
            "mean": float(values.mean()),
            "min": float(values.min()),
            "max": float(values.max()),
            "range": float(values.max() - values.min()),
        }
    return {
        "first": values[0],
        "last": values[-1],
        "mean": values.mean(axis=0),
        "min": values.min(axis=0),
        "max": values.max(axis=0),
        "range": values.max(axis=0) - values.min(axis=0),
    }


def _diff_summary(a: np.ndarray, b: np.ndarray) -> Dict[str, object]:
    diff = b - a
    return {
        "delta": diff,
        "abs_delta": np.abs(diff),
        "l2_delta": float(np.linalg.norm(diff)),
    }


def _clip_stats(raw: np.ndarray, clipped: np.ndarray) -> Dict[str, object]:
    raw_norm = np.linalg.norm(raw, axis=1)
    clipped_norm = np.linalg.norm(clipped, axis=1)
    loss = raw - clipped
    return {
        "raw_absmax": float(np.max(np.abs(raw))),
        "clipped_absmax": float(np.max(np.abs(clipped))),
        "raw_norm_mean": float(raw_norm.mean()),
        "clipped_norm_mean": float(clipped_norm.mean()),
        "raw_to_clipped_norm_ratio_mean": float(np.mean(raw_norm / np.maximum(clipped_norm, 1e-12))),
        "clip_l2_loss_mean": float(np.mean(np.linalg.norm(loss, axis=1))),
        "component_saturation_fraction": float(np.mean(np.isclose(np.abs(clipped), 0.005, atol=1e-8))),
    }


def _run_report(
    label: str,
    smoke: Mapping[str, object],
    summary: Mapping[str, object],
    post_gate: Mapping[str, object],
    comparable_ticks: int,
) -> Dict[str, object]:
    history = smoke.get("history", []) or []
    distances = np.asarray([float(row["distance_to_target"]) for row in history], dtype=np.float64)
    raw = _history_array(history, "raw_action_xyz")
    clipped = _history_array(history, "clipped_action_xyz")
    raw_joint = _history_array(history, "raw_joint_delta")
    clipped_joint = _history_array(history, "clipped_joint_delta")
    target_base = _history_array(history, "target_position_base_frame")
    eef_base = _history_array(history, "eef_position_base_frame")
    target_to_eef = _history_array(history, "target_to_eef_base_frame")

    first_n = min(comparable_ticks, len(history))
    comparable_distance_reduction = float(distances[0] - distances[first_n - 1]) if first_n else None
    total_distance_reduction = float(distances[0] - distances[-1]) if len(distances) else None
    extra_tick_distance_reduction = (
        float(distances[first_n - 1] - distances[-1])
        if len(distances) > first_n and first_n > 0
        else 0.0
    )
    metrics = summary.get("metrics", {}) or {}

    return {
        "label": label,
        "max_control_ticks": smoke.get("max_control_ticks"),
        "samples": len(history),
        "status": smoke.get("status"),
        "aborted": smoke.get("aborted"),
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
        "distance_trace": distances,
        "distance_delta_per_tick": np.diff(distances),
        "distance_first": float(distances[0]) if len(distances) else None,
        "distance_at_comparable_tick": float(distances[first_n - 1]) if first_n else None,
        "distance_last": float(distances[-1]) if len(distances) else None,
        "comparable_tick_count": first_n,
        "comparable_distance_reduction": comparable_distance_reduction,
        "extra_tick_distance_reduction": extra_tick_distance_reduction,
        "total_smoke_distance_reduction": total_distance_reduction,
        "summary_smoke_distance_reduction": metrics.get("smoke_distance_reduction"),
        "summary_gate_distance_reduction": metrics.get("gate_distance_reduction"),
        "post_gate_initial_distance": metrics.get("post_gate_initial_distance"),
        "post_gate_target_base_drift": metrics.get("post_gate_target_base_drift"),
        "post_gate_relative_base_drift": metrics.get("post_gate_relative_base_drift"),
        "post_gate_passed": post_gate.get("passed"),
        "post_gate_checks": post_gate.get("checks"),
        "raw_action_xyz_summary": _summary_array(raw),
        "clipped_action_xyz_summary": _summary_array(clipped),
        "raw_joint_delta_summary": _summary_array(raw_joint),
        "clipped_joint_delta_summary": _summary_array(clipped_joint),
        "action_clip_stats": _clip_stats(raw, clipped),
        "joint_clip_stats": _clip_stats(raw_joint, clipped_joint),
        "target_base_range_norm": float(np.linalg.norm(target_base.max(axis=0) - target_base.min(axis=0))),
        "eef_base_range_norm": float(np.linalg.norm(eef_base.max(axis=0) - eef_base.min(axis=0))),
        "target_to_eef_base_summary": _summary_array(target_to_eef),
    }


def _decide(runs: Mapping[str, Mapping[str, object]]) -> Dict[str, object]:
    c0 = runs["n3_cycle_0_tick5"]
    c1 = runs["n3_cycle_1_tick5"]
    t9 = runs["tick9_single_smoke"]

    tick9_first5 = float(t9["comparable_distance_reduction"])
    tick9_extra = float(t9["extra_tick_distance_reduction"])
    tick9_total = float(t9["total_smoke_distance_reduction"])
    tick9_extra_fraction = tick9_extra / max(tick9_total, 1e-12)
    cycle1_target_drift = float(c1["post_gate_target_base_drift"])
    tick9_target_drift = float(t9["post_gate_target_base_drift"])

    action_delta_c1_t9 = _diff_summary(
        np.asarray(c1["clipped_action_xyz_summary"]["mean"], dtype=np.float64),
        np.asarray(t9["clipped_action_xyz_summary"]["mean"], dtype=np.float64),
    )
    first5_reduction_gain_vs_cycle1 = tick9_first5 - float(c1["comparable_distance_reduction"])
    total_reduction_gain_vs_cycle1 = tick9_total - float(c1["total_smoke_distance_reduction"])

    tick_budget_helped = bool(tick9_extra > 0.01 and tick9_extra_fraction > 0.35)
    target_drift_helped = bool(cycle1_target_drift > 0.01 and tick9_target_drift < 0.001)
    policy_action_shift_detected = bool(action_delta_c1_t9["l2_delta"] > 0.002)

    if tick_budget_helped and target_drift_helped:
        primary_explanation = "both_tick_budget_and_cleaner_target_drift"
    elif tick_budget_helped:
        primary_explanation = "tick_budget"
    elif target_drift_helped:
        primary_explanation = "cleaner_target_drift"
    else:
        primary_explanation = "inconclusive"

    return {
        "tick_budget_helped": tick_budget_helped,
        "target_drift_helped": target_drift_helped,
        "policy_action_shift_detected": policy_action_shift_detected,
        "primary_explanation": primary_explanation,
        "tick9_extra_tick_distance_reduction": tick9_extra,
        "tick9_extra_tick_fraction_of_smoke_reduction": tick9_extra_fraction,
        "tick9_first5_reduction_gain_vs_cycle1": first5_reduction_gain_vs_cycle1,
        "tick9_total_reduction_gain_vs_cycle1": total_reduction_gain_vs_cycle1,
        "cycle1_target_drift": cycle1_target_drift,
        "tick9_target_drift": tick9_target_drift,
        "clipped_action_mean_delta_cycle1_to_tick9": action_delta_c1_t9,
        "n3_repeatability_resolved": False,
        "next_live_approved": False,
        "dp_fm_live_approved": False,
    }


def _write_md(payload: Mapping[str, object], path: Path) -> None:
    runs = payload["runs"]
    decision = payload["decision"]
    lines = [
        "# B8 Tick9 vs N3 Tick5 Read-Only Comparison",
        "",
        "This report is read-only. It sends no commands, starts no gripper or hand",
        "controller, and does not train BC/DP/FM.",
        "",
        "## Decision",
        "",
        "```text",
        f"primary_explanation={decision['primary_explanation']}",
        f"tick_budget_helped={decision['tick_budget_helped']}",
        f"target_drift_helped={decision['target_drift_helped']}",
        f"policy_action_shift_detected={decision['policy_action_shift_detected']}",
        "n3_repeatability_resolved=false",
        "next_live_approved=false",
        "dp_fm_live_approved=false",
        "```",
        "",
        "Interpretation: tick9 improved because the extra ticks supplied meaningful",
        "additional distance reduction, and the target drift was much cleaner than the",
        "failed N=3 cycle 1. The clipped action means stayed nearly identical, so this",
        "does not look like a policy-output shift. This does not prove repeatability.",
        "",
        "## Run Comparison",
        "",
        "| run | ticks | status | checks | first dist | comparable dist | last dist | smoke reduction | gate reduction | target drift | relative drift |",
        "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in ["n3_cycle_0_tick5", "n3_cycle_1_tick5", "tick9_single_smoke"]:
        run = runs[key]
        lines.append(
            "| "
            + " | ".join(
                [
                    key,
                    str(run["samples"]),
                    str(run["smoke_status"]),
                    str(run["checks_passed"]),
                    str(run["distance_first"]),
                    str(run["distance_at_comparable_tick"]),
                    str(run["distance_last"]),
                    str(run["total_smoke_distance_reduction"]),
                    str(run["summary_gate_distance_reduction"]),
                    str(run["post_gate_target_base_drift"]),
                    str(run["post_gate_relative_base_drift"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Tick9 Increment",
            "",
            "```text",
            f"tick9_first5_reduction_gain_vs_cycle1={decision['tick9_first5_reduction_gain_vs_cycle1']}",
            f"tick9_extra_tick_distance_reduction={decision['tick9_extra_tick_distance_reduction']}",
            f"tick9_extra_tick_fraction_of_smoke_reduction={decision['tick9_extra_tick_fraction_of_smoke_reduction']}",
            f"tick9_total_reduction_gain_vs_cycle1={decision['tick9_total_reduction_gain_vs_cycle1']}",
            "```",
            "",
            "## Action Stability",
            "",
            "```text",
            f"clipped_action_mean_delta_cycle1_to_tick9_l2={decision['clipped_action_mean_delta_cycle1_to_tick9']['l2_delta']}",
            f"policy_action_shift_detected={decision['policy_action_shift_detected']}",
            "```",
            "",
            "## Safety Boundary",
            "",
            "- Treat tick9 as a single successful arm-only tick-budget sensitivity smoke.",
            "- Do not claim N=3 repeatability, grasp success, or general learned rollout success.",
            "- Do not run another live smoke or DP/FM live from this report alone.",
            "- DP/FM remain offline-only.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only comparison of N3 tick5 cycle 0/1 and tick9 single-smoke artifacts."
    )
    default_root = Path("src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_rollout_planning")
    parser.add_argument("--n3-dir", type=Path, default=default_root / "bc_h8_xyz_base_relative_repeatability_n3")
    parser.add_argument("--tick9-dir", type=Path, default=default_root / "bc_h8_xyz_base_relative_tick9_single_smoke")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=default_root / "bc_h8_xyz_base_relative_tick9_vs_n3_tick5_comparison.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=default_root / "bc_h8_xyz_base_relative_tick9_vs_n3_tick5_comparison.md",
    )
    parser.add_argument("--comparable-ticks", type=int, default=5)
    args = parser.parse_args()

    runs = {}
    for label, base in [
        ("n3_cycle_0_tick5", args.n3_dir / "cycle_0"),
        ("n3_cycle_1_tick5", args.n3_dir / "cycle_1"),
    ]:
        runs[label] = _run_report(
            label,
            smoke=_load_json(base / "smoke.json"),
            summary=_load_json(base / "summary.json"),
            post_gate=_load_json(base / "post_gate/post_smoke_gate.json"),
            comparable_ticks=args.comparable_ticks,
        )
    runs["tick9_single_smoke"] = _run_report(
        "tick9_single_smoke",
        smoke=_load_json(args.tick9_dir / "smoke.json"),
        summary=_load_json(args.tick9_dir / "summary.json"),
        post_gate=_load_json(args.tick9_dir / "post_gate/post_smoke_gate.json"),
        comparable_ticks=args.comparable_ticks,
    )

    payload = {
        "artifact": "bc_h8_xyz_base_relative_tick9_vs_n3_tick5_comparison",
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "hand_controller_started": False,
        "training_started": False,
        "dp_fm_live_approved": False,
        "runs": runs,
        "decision": _decide(runs),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(_json_safe(payload), args.output_md)
    print(json.dumps(_json_safe(payload["decision"]), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
