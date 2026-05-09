#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, object]:
    with path.expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _raw_action_metrics(dry_run: Dict[str, object]) -> Dict[str, object]:
    history = list(dry_run.get("history", []) or [])
    if not history:
        return {
            "samples": 0,
            "raw_absmax": float("nan"),
            "raw_p95_absmax_per_tick": float("nan"),
            "clipped_absmax": float("nan"),
            "component_clip_count": 0,
            "norm_clip_count": 0,
        }
    raw = np.asarray([row["raw_action_xyz"] for row in history], dtype=np.float64)
    clipped = np.asarray([row["clipped_action_xyz"] for row in history], dtype=np.float64)
    per_tick_absmax = np.max(np.abs(raw), axis=1)
    return {
        "samples": int(len(history)),
        "raw_absmax": float(np.max(np.abs(raw))),
        "raw_p95_absmax_per_tick": float(np.percentile(per_tick_absmax, 95)),
        "clipped_absmax": float(np.max(np.abs(clipped))),
        "component_clip_count": int(sum(1 for row in history if row.get("clip", {}).get("component_clipped"))),
        "norm_clip_count": int(sum(1 for row in history if row.get("clip", {}).get("norm_clipped"))),
        "raw_first": raw[0].tolist(),
        "target_to_eef_base_first": history[0].get("target_to_eef_base_frame"),
    }


def _row_by_key(report: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    return {str(row.get("key") or row.get("short_name")): row for row in report.get("rows", [])}


def _comparison_rows(report: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    return {str(row.get("short_name")): row for row in report.get("comparison_rows", [])}


def _write_markdown(payload: Dict[str, object], path: Path) -> None:
    lines: List[str] = [
        "# B8' Base-Relative Rollout Readiness Preflight",
        "",
        "This is a read-only preflight over existing offline and dry-run artifacts.",
        "It does not run a learned rollout, does not send arm commands, and does not send gripper commands.",
        "",
        "## Decision",
        "",
        f"- Candidate status: `{payload['candidate_status']}`",
        f"- Go for learned execution now: `{payload['go_for_learned_execution_now']}`",
        f"- Separate approval required: `{payload['separate_execution_approval_required']}`",
        f"- Rollout-ready success claimed: `{payload['rollout_ready_success_claimed']}`",
        "",
        "## Gate Checks",
        "",
        "| check | passed | detail |",
        "|---|---:|---|",
    ]
    for check in payload["checks"]:
        detail = str(check.get("detail", "")).replace("\n", " ")
        lines.append(f"| {check['name']} | {check['passed']} | {detail} |")
    lines.extend(
        [
            "",
            "## Key Metrics",
            "",
            "```text",
            json.dumps(payload["metrics"], indent=2, sort_keys=True),
            "```",
            "",
            "## Next",
            "",
        ]
    )
    for item in payload["next_steps"]:
        lines.append(f"- {item}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only readiness preflight for the B8' base-relative BC rollout-planning candidate."
    )
    parser.add_argument(
        "--dry-run-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_dry_run_latest.json",
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
        "--safety-plan-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_arm_only_rollout_safety_plan.json",
    )
    parser.add_argument(
        "--ik-preview-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_ik_preview_latest.json",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.md",
    )
    parser.add_argument("--raw-absmax-threshold", type=float, default=0.012)
    parser.add_argument("--min-dry-run-samples", type=int, default=12)
    args = parser.parse_args()

    dry_run = _load_json(args.dry_run_json)
    comparison = _load_json(args.offline_comparison_json)
    epoch_budget = _load_json(args.epoch_budget_json)
    safety_plan = _load_json(args.safety_plan_json)
    ik_preview = _load_json(args.ik_preview_json) if args.ik_preview_json.exists() else {}

    action_metrics = _raw_action_metrics(dry_run)
    ik_history = list(ik_preview.get("history", []) or [])
    ik_first_row = ik_history[0].get("ik_preview", {}) if ik_history else {}
    ik_preview_result = ik_preview.get("preview_ik_result", {}) or ik_first_row or {}
    comparison_rows = _comparison_rows(comparison)
    epoch_rows = _row_by_key(epoch_budget)
    bc_epoch = epoch_rows.get("bc_ref", {})
    non_bc_epochs = [row for key, row in epoch_rows.items() if key != "bc_ref"]
    min_non_bc_action_mse = min((float(row["action_mse"]) for row in non_bc_epochs), default=float("inf"))
    bc_action_mse = float(bc_epoch.get("action_mse", float("inf")))

    hard_non_goals = " ".join(str(item).lower() for item in safety_plan.get("hard_non_goals", []))
    safety_decision = safety_plan.get("decision", {}) or {}
    checks = [
        {
            "name": "dry_run_no_abort",
            "passed": bool(dry_run.get("aborted") is False and dry_run.get("status") == "timeout_complete"),
            "detail": f"status={dry_run.get('status')} aborted={dry_run.get('aborted')}",
        },
        {
            "name": "dry_run_no_control_or_gripper",
            "passed": bool(
                dry_run.get("control_commands_sent") is False
                and dry_run.get("gripper_commands_sent") is False
                and dry_run.get("hand_controller_started") is False
            ),
            "detail": (
                f"control={dry_run.get('control_commands_sent')} "
                f"gripper={dry_run.get('gripper_commands_sent')} "
                f"hand={dry_run.get('hand_controller_started')}"
            ),
        },
        {
            "name": "dry_run_sample_count",
            "passed": bool(action_metrics["samples"] >= args.min_dry_run_samples),
            "detail": f"samples={action_metrics['samples']} threshold={args.min_dry_run_samples}",
        },
        {
            "name": "dry_run_raw_action_scale",
            "passed": bool(action_metrics["raw_absmax"] <= args.raw_absmax_threshold),
            "detail": f"raw_absmax={action_metrics['raw_absmax']} threshold={args.raw_absmax_threshold}",
        },
        {
            "name": "offline_comparison_same_observation_gate",
            "passed": bool(
                comparison.get("offline_only") is True
                and comparison.get("old_absolute_pose_checkpoints_excluded") is True
                and comparison.get("action_dim_indices") == [0, 1, 2]
                and "target_position_base_frame" in comparison.get("observation_keys", [])
            ),
            "detail": "offline-only base-relative comparison excludes old absolute-pose checkpoints",
        },
        {
            "name": "bc_reference_not_displaced_by_dp_fm",
            "passed": bool(bc_action_mse <= min_non_bc_action_mse),
            "detail": f"bc_action_mse={bc_action_mse} min_non_bc_action_mse={min_non_bc_action_mse}",
        },
        {
            "name": "safety_plan_no_gripper_no_grasp",
            "passed": bool(
                "no gripper" in hard_non_goals
                and "no grasp" in hard_non_goals
                and safety_decision.get("rollout_execution_approved_by_this_plan") is False
                and safety_decision.get("requires_separate_approval") is True
                and "no rollout executed" in str(safety_plan.get("status", "")).lower()
            ),
            "detail": (
                "safety plan hard non-goals include no gripper/no grasp and "
                "explicitly require separate execution approval"
            ),
        },
        {
            "name": "ik_preview_no_publish",
            "passed": bool(
                ik_preview
                and ik_preview.get("aborted") is False
                and ik_preview.get("control_commands_sent") is False
                and ik_preview.get("gripper_commands_sent") is False
                and ik_preview.get("preview_ik_done") is True
                and ik_preview_result.get("status") == "passed"
                and ik_preview_result.get("would_publish_arm_command") is False
            ),
            "detail": (
                f"preview_status={ik_preview_result.get('status')} "
                f"would_publish={ik_preview_result.get('would_publish_arm_command')} "
                f"aborted={ik_preview.get('aborted') if ik_preview else 'missing'}"
            ),
        },
    ]

    all_checks_passed = all(bool(check["passed"]) for check in checks)
    metrics = {
        "dry_run": action_metrics,
        "ik_preview": {
            "available": bool(ik_preview),
            "status": ik_preview_result.get("status"),
            "would_publish_arm_command": ik_preview_result.get("would_publish_arm_command"),
            "clipped_xyz_action_frame": ik_preview_result.get("clipped_xyz_action_frame"),
            "clipped_xyz_planning_frame": ik_preview_result.get("clipped_xyz_planning_frame"),
            "raw_joint_delta_max_abs": (
                float(np.max(np.abs(ik_preview_result.get("raw_joint_delta", []))))
                if ik_preview_result.get("raw_joint_delta")
                else None
            ),
            "clipped_joint_delta_max_abs": (
                float(np.max(np.abs(ik_preview_result.get("clipped_joint_delta", []))))
                if ik_preview_result.get("clipped_joint_delta")
                else None
            ),
        },
        "bc_action_mse": bc_action_mse,
        "min_non_bc_action_mse": min_non_bc_action_mse,
        "comparison_bc_action_mse": comparison_rows.get("bc", {}).get("action_mse"),
        "comparison_diffusion_zero_action_mse": comparison_rows.get("diffusion_zero", {}).get("action_mse"),
        "comparison_flow_matching_zero_action_mse": comparison_rows.get("flow_matching_zero", {}).get("action_mse"),
    }
    payload = {
        "tool": "analyze_b8_base_relative_rollout_readiness",
        "read_only": True,
        "offline_only_inputs": True,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "learned_rollout_run": False,
        "rollout_ready_success_claimed": False,
        "candidate_status": "rollout_planning_candidate" if all_checks_passed else "not_ready",
        "go_for_learned_execution_now": False,
        "separate_execution_approval_required": True,
        "checks_passed": bool(all_checks_passed),
        "checks": checks,
        "metrics": metrics,
        "inputs": {
            "dry_run_json": str(args.dry_run_json),
            "offline_comparison_json": str(args.offline_comparison_json),
            "epoch_budget_json": str(args.epoch_budget_json),
            "safety_plan_json": str(args.safety_plan_json),
            "ik_preview_json": str(args.ik_preview_json),
        },
        "next_steps": [
            "Keep BC base-relative h8 xyz as the rollout-planning reference.",
            "Before any learned execution, run return-to-reference and two fresh target-aware gates.",
            "Request separate approval for a tiny arm-only execution smoke; do not start gripper/hand.",
            "If approval is not granted, continue offline-only diagnostics or collect more controlled data.",
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(payload, args.output_md)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
