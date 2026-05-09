#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, object]:
    with path.expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _rows_by_key(rows: Iterable[Dict[str, object]], key_name: str) -> Dict[str, Dict[str, object]]:
    return {str(row[key_name]): row for row in rows if key_name in row}


def _fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.9g}"
    return str(value)


def _write_markdown(payload: Dict[str, object], path: Path) -> None:
    lines: List[str] = [
        "# B8 DP/FM Post-Live-Smoke Offline Gate",
        "",
        "Scope: offline-only DP/FM decision after the second tiny BC",
        "base-relative arm-only smoke. This report reads existing artifacts and",
        "offline eval JSON files only. It does not run ROS, publish arm commands,",
        "publish gripper commands, train full DP/FM, or claim grasp success.",
        "",
        "## Decision",
        "",
        f"- DP/FM live execution approved: `{payload['decision']['dp_fm_live_execution_approved']}`",
        f"- Full DP/FM training approved: `{payload['decision']['full_dp_fm_training_approved']}`",
        f"- BC remains live reference: `{payload['decision']['bc_remains_live_reference']}`",
        f"- Next allowed work: `{payload['decision']['next_allowed']}`",
        "",
        "## Checks",
        "",
        "| check | passed | detail |",
        "|---|---:|---|",
    ]
    for check in payload["checks"]:
        lines.append(f"| {check['name']} | {check['passed']} | {check['detail']} |")

    lines.extend(
        [
            "",
            "## Offline Metrics",
            "",
            "| candidate | action MSE | normalized MSE | note |",
            "|---|---:|---:|---|",
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
                    str(row["note"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Sampling Sensitivity",
            "",
            "| candidate | steps | action MSE | normalized MSE |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in payload["sampling_sensitivity"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["candidate"]),
                    str(row["steps"]),
                    _fmt(row["action_mse"]),
                    _fmt(row["normalized_mse"]),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Next", ""])
    for item in payload["next_steps"]:
        lines.append(f"- {item}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline-only DP/FM gate after the second BC base-relative tiny live smoke."
    )
    parser.add_argument(
        "--offline-comparison-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_offline_comparison.json",
    )
    parser.add_argument(
        "--epoch-budget-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_epoch_budget_ablation.json",
    )
    parser.add_argument(
        "--second-smoke-summary-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/second_tiny_smoke_summary.json",
    )
    parser.add_argument(
        "--post-second-gate-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/post_second_tiny_smoke_return_gate/gate_retry_1.json",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_primary30_training_planning/dp_fm_post_live_smoke_offline_gate.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_primary30_training_planning/dp_fm_post_live_smoke_offline_gate.md",
    )
    args = parser.parse_args()

    comparison = _load_json(args.offline_comparison_json)
    epoch_budget = _load_json(args.epoch_budget_json)
    second_smoke = _load_json(args.second_smoke_summary_json)
    post_gate = _load_json(args.post_second_gate_json)

    comparison_rows = _rows_by_key(comparison.get("comparison_rows", []), "short_name")
    epoch_rows = _rows_by_key(epoch_budget.get("rows", []), "key")

    bc = epoch_rows["bc_ref"]
    dp10 = epoch_rows["dp10_zero"]
    dp30 = epoch_rows["dp30_zero"]
    fm10 = epoch_rows["fm10_zero"]
    fm30 = epoch_rows["fm30_zero"]

    sampling_paths = [
        (
            "dp30_zero",
            10,
            PACKAGE_ROOT
            / "outputs/eval/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30/"
            "offline_eval_diffusion_val_post_smoke_zero_steps10.json",
        ),
        (
            "dp30_zero",
            25,
            PACKAGE_ROOT
            / "outputs/eval/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30/"
            "offline_eval_diffusion_val_post_smoke_zero_steps25.json",
        ),
        (
            "dp30_zero",
            50,
            PACKAGE_ROOT
            / "outputs/eval/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30/"
            "offline_eval_diffusion_val_post_smoke_zero_steps50.json",
        ),
        (
            "dp30_zero",
            100,
            PACKAGE_ROOT
            / "outputs/eval/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30/"
            "offline_eval_diffusion_val_post_smoke_zero_steps100.json",
        ),
        (
            "fm10_zero",
            10,
            PACKAGE_ROOT
            / "outputs/eval/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_smoke/"
            "offline_eval_flow_matching_val_post_smoke_zero_ode10.json",
        ),
        (
            "fm10_zero",
            25,
            PACKAGE_ROOT
            / "outputs/eval/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_smoke/"
            "offline_eval_flow_matching_val_post_smoke_zero_ode25.json",
        ),
        (
            "fm10_zero",
            50,
            PACKAGE_ROOT
            / "outputs/eval/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_smoke/"
            "offline_eval_flow_matching_val_post_smoke_zero_ode50.json",
        ),
        (
            "fm10_zero",
            100,
            PACKAGE_ROOT
            / "outputs/eval/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_smoke/"
            "offline_eval_flow_matching_val_post_smoke_zero_ode100.json",
        ),
    ]

    sensitivity = []
    for candidate, steps, path in sampling_paths:
        row = _load_json(path)
        sensitivity.append(
            {
                "candidate": candidate,
                "steps": steps,
                "action_mse": float(row["action_mse"]),
                "normalized_mse": float(row["normalized_mse"]),
                "path": str(path),
            }
        )

    dp_best = min((row for row in sensitivity if row["candidate"] == "dp30_zero"), key=lambda row: row["action_mse"])
    fm_best = min((row for row in sensitivity if row["candidate"] == "fm10_zero"), key=lambda row: row["action_mse"])
    best_non_bc_action_mse = min(float(dp_best["action_mse"]), float(fm_best["action_mse"]))
    bc_action_mse = float(bc["action_mse"])

    checks = [
        {
            "name": "offline_only_inputs",
            "passed": bool(
                comparison.get("offline_only") is True
                and epoch_budget.get("offline_only") is True
                and comparison.get("control_commands_sent") is False
                and comparison.get("gripper_commands_sent") is False
                and epoch_budget.get("control_commands_sent") is False
                and epoch_budget.get("gripper_commands_sent") is False
            ),
            "detail": "comparison and epoch-budget artifacts are offline-only with no control/gripper command",
        },
        {
            "name": "same_base_relative_safe_norm_gate",
            "passed": bool(
                comparison.get("old_absolute_pose_checkpoints_excluded") is True
                and comparison.get("action_dim_indices") == [0, 1, 2]
                and comparison.get("safe_action_normalization", {}).get("action_std_fallback") == 0.001
                and "target_position_base_frame" in comparison.get("observation_keys", [])
                and "target_to_eef_base_frame" in comparison.get("observation_keys", [])
            ),
            "detail": "uses dx/dy/dz, base-relative geometry, no old absolute-pose checkpoints",
        },
        {
            "name": "bc_has_one_live_arm_only_smoke_success",
            "passed": bool(
                second_smoke.get("smoke_status") == "arm_only_reaching_success"
                and second_smoke.get("arm_only_reaching_success_claimed") is True
                and second_smoke.get("learned_rollout_success_claimed") is False
                and second_smoke.get("grasp_success_claimed") is False
            ),
            "detail": (
                f"smoke_status={second_smoke.get('smoke_status')} "
                f"gate_reduction={second_smoke.get('metrics', {}).get('gate_distance_reduction')}"
            ),
        },
        {
            "name": "system_recovered_after_live_smoke",
            "passed": bool(
                post_gate.get("passed") is True
                and post_gate.get("control_commands_sent") is False
                and post_gate.get("gripper_commands_sent") is False
            ),
            "detail": (
                f"post_recovery_gate={post_gate.get('passed')} "
                f"initial_distance={post_gate.get('metrics', {}).get('initial_distance')}"
            ),
        },
        {
            "name": "dp_fm_do_not_beat_bc_action_mse",
            "passed": bool(bc_action_mse < best_non_bc_action_mse),
            "detail": f"bc={bc_action_mse} best_non_bc={best_non_bc_action_mse}",
        },
        {
            "name": "dp_fm_no_live_adapter_approval",
            "passed": True,
            "detail": "no DP/FM execution adapter or live smoke is approved by this offline gate",
        },
    ]

    offline_metrics = [
        {
            "candidate": "BC h8 xyz base-relative safe-norm",
            "action_mse": bc_action_mse,
            "normalized_mse": float(bc["normalized_mse"]),
            "note": "current live reference; one tiny arm-only smoke success",
        },
        {
            "candidate": "DP h8 xyz zero epoch10",
            "action_mse": float(dp10["action_mse"]),
            "normalized_mse": float(dp10["normalized_mse"]),
            "note": "same observation/norm; no live execution",
        },
        {
            "candidate": "DP h8 xyz zero epoch30",
            "action_mse": float(dp30["action_mse"]),
            "normalized_mse": float(dp30["normalized_mse"]),
            "note": "best DP in current epoch-budget set",
        },
        {
            "candidate": "FM h8 xyz zero epoch10",
            "action_mse": float(fm10["action_mse"]),
            "normalized_mse": float(fm10["normalized_mse"]),
            "note": "best FM in current epoch-budget set",
        },
        {
            "candidate": "FM h8 xyz zero epoch30",
            "action_mse": float(fm30["action_mse"]),
            "normalized_mse": float(fm30["normalized_mse"]),
            "note": "worse than FM epoch10",
        },
    ]

    payload = {
        "tool": "analyze_b8_dp_fm_post_live_smoke_gate",
        "offline_only": True,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "learned_rollout_run": False,
        "grasp_success_claimed": False,
        "learned_rollout_success_claimed": False,
        "old_absolute_pose_checkpoints_excluded": True,
        "inputs": {
            "offline_comparison_json": str(args.offline_comparison_json),
            "epoch_budget_json": str(args.epoch_budget_json),
            "second_smoke_summary_json": str(args.second_smoke_summary_json),
            "post_second_gate_json": str(args.post_second_gate_json),
        },
        "checks_passed": all(bool(check["passed"]) for check in checks),
        "checks": checks,
        "offline_metrics": offline_metrics,
        "sampling_sensitivity": sensitivity,
        "decision": {
            "bc_remains_live_reference": True,
            "dp_fm_live_execution_approved": False,
            "full_dp_fm_training_approved": False,
            "dp_fm_rollout_ready_success_claimed": False,
            "best_dp_action_mse": float(dp_best["action_mse"]),
            "best_dp_steps": int(dp_best["steps"]),
            "best_fm_action_mse": float(fm_best["action_mse"]),
            "best_fm_steps": int(fm_best["steps"]),
            "bc_action_mse": bc_action_mse,
            "next_allowed": (
                "offline-only DP h8 focused budget/seed ablation or keep BC for "
                "repeatability planning; no DP/FM live execution"
            ),
        },
        "next_steps": [
            "Do not run DP/FM live smoke or learned rollout.",
            "Do not start full DP/FM training from this evidence.",
            (
                "If continuing DP offline, prefer a bounded DP h8 focused ablation "
                "because DP epoch30 is closest to BC but still worse."
            ),
            "If continuing live work, use the BC base-relative checkpoint and a separate repeatability plan.",
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(payload, args.output_md)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
