#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, object]:
    with path.expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _rows_by_key(rows: Iterable[Mapping[str, object]], key: str) -> Dict[str, Mapping[str, object]]:
    return {str(row[key]): row for row in rows if key in row}


def _fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.9g}"
    return str(value)


def _relative_delta(candidate: float, reference: float) -> float:
    return (candidate - reference) / max(reference, 1e-12)


def _write_md(payload: Mapping[str, object], path: Path) -> None:
    lines: List[str] = [
        "# B8 DP/FM Post-Tick9 Offline Gate",
        "",
        "Scope: offline-only DP/FM gate after the tick9 BC arm-only sensitivity",
        "smoke and target-drift readiness review. This report reads existing",
        "artifacts only. It does not run ROS, publish arm commands, publish gripper",
        "commands, train BC/DP/FM, or claim rollout/grasp success.",
        "",
        "## Decision",
        "",
        "```text",
        f"dp_fm_offline_can_continue={payload['decision']['dp_fm_offline_can_continue']}",
        f"dp_fm_live_execution_approved={payload['decision']['dp_fm_live_execution_approved']}",
        f"full_dp_fm_training_approved={payload['decision']['full_dp_fm_training_approved']}",
        f"bc_remains_live_reference={payload['decision']['bc_remains_live_reference']}",
        f"best_dp_candidate={payload['decision']['best_dp_candidate']}",
        f"best_fm_candidate={payload['decision']['best_fm_candidate']}",
        f"next_allowed={payload['decision']['next_allowed']}",
        "```",
        "",
        "## Checks",
        "",
        "| check | passed | detail |",
        "| --- | ---: | --- |",
    ]
    for check in payload["checks"]:
        lines.append(f"| {check['name']} | {check['passed']} | {check['detail']} |")

    lines.extend(
        [
            "",
            "## Offline Metrics",
            "",
            "| candidate | action MSE | normalized MSE | action MSE vs BC | note |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in payload["offline_metrics"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["candidate"]),
                    _fmt(row["action_mse"]),
                    _fmt(row["normalized_mse"]),
                    _fmt(row["action_mse_relative_to_bc"]),
                    str(row["note"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- DP/FM may continue offline-only under the same base-relative safe-norm setup.",
            "- Do not run DP/FM live.",
            "- Do not start full DP/FM training as success evidence.",
            "- Do not claim grasp success or general learned rollout success.",
            "- Any future live work remains gated by BC repeatability and the clean target-drift readiness gate.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline-only DP/FM gate after tick9 BC sensitivity smoke.")
    parser.add_argument(
        "--epoch-budget-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_epoch_budget_ablation.json",
    )
    parser.add_argument(
        "--comparison-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_offline_comparison.json",
    )
    parser.add_argument(
        "--tick9-outcome-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke/outcome.json",
    )
    parser.add_argument(
        "--target-readiness-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/b8_target_drift_readiness_gate_review.json",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_primary30_training_planning/dp_fm_post_tick9_offline_gate.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_primary30_training_planning/dp_fm_post_tick9_offline_gate.md",
    )
    args = parser.parse_args()

    epoch_budget = _load_json(args.epoch_budget_json)
    comparison = _load_json(args.comparison_json)
    tick9 = _load_json(args.tick9_outcome_json)
    readiness = _load_json(args.target_readiness_json)

    rows = _rows_by_key(epoch_budget.get("rows", []), "key")
    bc = rows["bc_ref"]
    dp10 = rows["dp10_zero"]
    dp30 = rows["dp30_zero"]
    fm10 = rows["fm10_zero"]
    fm30 = rows["fm30_zero"]

    bc_action = float(bc["action_mse"])
    dp_rows = [dp10, dp30]
    fm_rows = [fm10, fm30]
    best_dp = min(dp_rows, key=lambda row: float(row["action_mse"]))
    best_fm = min(fm_rows, key=lambda row: float(row["action_mse"]))
    best_non_bc = min([best_dp, best_fm], key=lambda row: float(row["action_mse"]))

    offline_metrics = []
    for row in [bc, dp10, dp30, fm10, fm30]:
        offline_metrics.append(
            {
                "candidate": row["name"],
                "key": row["key"],
                "policy_type": row["policy_type"],
                "epochs": row["epochs"],
                "sampling_mode": row["sampling_mode"],
                "action_mse": float(row["action_mse"]),
                "normalized_mse": float(row["normalized_mse"]),
                "action_mse_relative_to_bc": _relative_delta(float(row["action_mse"]), bc_action),
                "per_dim_action_mse": row.get("per_dim_action_mse"),
                "checkpoint": row.get("checkpoint"),
                "note": "BC live reference" if row["key"] == "bc_ref" else "offline-only candidate",
            }
        )

    safe_norm = comparison.get("safe_action_normalization", {}) or {}
    observation_keys = comparison.get("observation_keys", []) or []
    readiness_decision = readiness.get("decision", {}) or {}
    tick9_decision = tick9.get("decision", {}) or {}

    checks = [
        {
            "name": "offline_artifacts_only",
            "passed": bool(
                epoch_budget.get("offline_only") is True
                and comparison.get("offline_only") is True
                and epoch_budget.get("control_commands_sent") is False
                and comparison.get("control_commands_sent") is False
                and epoch_budget.get("gripper_commands_sent") is False
                and comparison.get("gripper_commands_sent") is False
            ),
            "detail": "reads existing offline eval artifacts only",
        },
        {
            "name": "same_base_relative_safe_norm",
            "passed": bool(
                comparison.get("old_absolute_pose_checkpoints_excluded") is True
                and comparison.get("action_dim_indices") == [0, 1, 2]
                and safe_norm.get("action_std_fallback") == 0.001
                and "target_position_base_frame" in observation_keys
                and "target_to_eef_base_frame" in observation_keys
            ),
            "detail": "same xyz h8 base-relative no-gripper observation and safe action normalization",
        },
        {
            "name": "tick9_is_single_smoke_only",
            "passed": bool(
                tick9.get("smoke_status") == "arm_only_reaching_success"
                and tick9_decision.get("tick9_single_smoke_passed") is True
                and tick9_decision.get("n3_repeatability_resolved") is False
                and tick9.get("learned_rollout_success_claimed") is False
                and tick9.get("grasp_success_claimed") is False
            ),
            "detail": f"tick9_status={tick9.get('smoke_status')} n3_resolved={tick9_decision.get('n3_repeatability_resolved')}",
        },
        {
            "name": "target_readiness_blocks_live",
            "passed": bool(
                readiness_decision.get("target_drift_is_live_confound") is True
                and readiness_decision.get("next_live_approved") is False
                and readiness_decision.get("dp_fm_live_approved") is False
            ),
            "detail": "target drift remains live confound; clean two-gate readiness required before any separately approved live",
        },
        {
            "name": "bc_still_best_action_mse",
            "passed": bool(bc_action < float(best_non_bc["action_mse"])),
            "detail": f"bc={bc_action} best_non_bc={best_non_bc['key']}:{float(best_non_bc['action_mse'])}",
        },
    ]

    payload = {
        "artifact": "dp_fm_post_tick9_offline_gate",
        "offline_only": True,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "hand_controller_started": False,
        "training_started": False,
        "learned_rollout_run": False,
        "learned_rollout_success_claimed": False,
        "grasp_success_claimed": False,
        "old_absolute_pose_checkpoints_excluded": True,
        "inputs": {
            "epoch_budget_json": str(args.epoch_budget_json),
            "comparison_json": str(args.comparison_json),
            "tick9_outcome_json": str(args.tick9_outcome_json),
            "target_readiness_json": str(args.target_readiness_json),
        },
        "checks_passed": all(bool(check["passed"]) for check in checks),
        "checks": checks,
        "offline_metrics": offline_metrics,
        "decision": {
            "dp_fm_offline_can_continue": True,
            "dp_fm_live_execution_approved": False,
            "full_dp_fm_training_approved": False,
            "bc_remains_live_reference": True,
            "best_dp_candidate": best_dp["key"],
            "best_dp_action_mse": float(best_dp["action_mse"]),
            "best_fm_candidate": best_fm["key"],
            "best_fm_action_mse": float(best_fm["action_mse"]),
            "best_non_bc_candidate": best_non_bc["key"],
            "best_non_bc_action_mse": float(best_non_bc["action_mse"]),
            "bc_action_mse": bc_action,
            "next_allowed": (
                "offline-only DP/FM diagnostics under the same base-relative safe-norm setup; "
                "no DP/FM live and no full training-as-success evidence"
            ),
        },
        "next_steps": [
            "Keep DP/FM live blocked.",
            "Do not run another learned live smoke from this offline gate alone.",
            "If continuing DP/FM, do offline-only diagnostics: seed/budget review, action-scale review, and validation-window error review.",
            "BC remains the live reference until DP/FM beat it offline and live readiness is separately re-approved.",
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(payload, args.output_md)
    print(json.dumps(payload["decision"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
