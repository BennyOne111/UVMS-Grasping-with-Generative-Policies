#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Dict, List


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, object]:
    with path.expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_markdown(payload: Dict[str, object], path: Path) -> None:
    lines: List[str] = [
        "# B8 Base-Relative Tiny Arm-Only Smoke Summary",
        "",
        "This summary evaluates one tiny learned arm-only smoke. It may claim",
        "`arm_only_reaching_success` for this single smoke only when the configured",
        "distance thresholds are met. It never claims grasp success or general",
        "learned rollout success.",
        "",
        "## Decision",
        "",
        f"- Smoke status: `{payload['smoke_status']}`",
        f"- Command path smoke resolved: `{payload['command_path_smoke_resolved']}`",
        f"- Arm-only reaching success claimed: `{payload['arm_only_reaching_success_claimed']}`",
        f"- Grasp success claimed: `{payload['grasp_success_claimed']}`",
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
            "## Metrics",
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
        description="Summarize the B8 base-relative tiny arm-only learned smoke."
    )
    parser.add_argument(
        "--return-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/tiny_smoke_return_to_reference.json",
    )
    parser.add_argument(
        "--pre-gate-0-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/tiny_smoke_pre_gate/gate_0.json",
    )
    parser.add_argument(
        "--pre-gate-1-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/tiny_smoke_pre_gate/gate_1.json",
    )
    parser.add_argument(
        "--smoke-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_execution_smoke_latest.json",
    )
    parser.add_argument(
        "--post-gate-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/tiny_smoke_post_gate/post_smoke_gate.json",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_summary.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_summary.md",
    )
    parser.add_argument("--success-distance-max", type=float, default=0.10)
    parser.add_argument("--success-distance-reduction-min", type=float, default=0.02)
    parser.add_argument(
        "--final-distance-source",
        choices=["post_gate", "terminal_observation"],
        default="post_gate",
        help="Source used for the formal success distance. post_gate preserves legacy behavior.",
    )
    parser.add_argument("--target-base-drift-max", type=float, default=0.01)
    args = parser.parse_args()

    ret = _load_json(args.return_json)
    gate0 = _load_json(args.pre_gate_0_json)
    gate1 = _load_json(args.pre_gate_1_json)
    smoke = _load_json(args.smoke_json)
    post_gate = _load_json(args.post_gate_json)

    smoke_history = list(smoke.get("history", []) or [])
    distances = [float(row["distance_to_target"]) for row in smoke_history if "distance_to_target" in row]
    pre_initial_distance = float(gate1["metrics"]["initial_distance"])
    post_initial_distance = float(post_gate["metrics"]["initial_distance"])
    distance_reduction_gate = pre_initial_distance - post_initial_distance
    min_smoke_distance = min(distances) if distances else None
    first_smoke_distance = distances[0] if distances else None
    last_smoke_distance = distances[-1] if distances else None
    smoke_distance_reduction = (
        first_smoke_distance - last_smoke_distance if first_smoke_distance is not None else None
    )
    if args.final_distance_source == "terminal_observation":
        formal_final_distance = last_smoke_distance
    else:
        formal_final_distance = post_initial_distance
    formal_distance_reduction = (
        pre_initial_distance - formal_final_distance
        if formal_final_distance is not None
        else None
    )
    raw_absmax = max(
        (
            max((abs(float(v)) for v in row.get("raw_action_xyz", [])), default=float("nan"))
            for row in smoke_history
            if row.get("raw_action_xyz")
        ),
        default=float("nan"),
    )
    clipped_absmax = max(
        (
            max((abs(float(v)) for v in row.get("clipped_action_xyz", [])), default=float("nan"))
            for row in smoke_history
            if row.get("clipped_action_xyz")
        ),
        default=float("nan"),
    )
    joint_delta_absmax = max(
        (
            max((abs(float(v)) for v in row.get("clipped_joint_delta", [])), default=float("nan"))
            for row in smoke_history
            if row.get("clipped_joint_delta")
        ),
        default=float("nan"),
    )
    arm_only_success = bool(
        formal_final_distance is not None
        and formal_final_distance <= args.success_distance_max
        and formal_distance_reduction is not None
        and formal_distance_reduction > args.success_distance_reduction_min
        and smoke.get("aborted") is False
    )
    completed_status_ok = bool(
        smoke.get("status") == "max_control_ticks_complete"
        or smoke.get("status") == "early_reaching_stop"
    )
    sample_count_ok = bool(
        len(smoke_history) == int(smoke.get("max_control_ticks", -1))
        if smoke.get("status") == "max_control_ticks_complete"
        else 0 < len(smoke_history) <= int(smoke.get("max_control_ticks", 999999))
    )
    command_path_smoke_resolved = bool(
        ret.get("reached") is True
        and gate0.get("passed") is True
        and gate1.get("passed") is True
        and completed_status_ok
        and smoke.get("aborted") is False
        and smoke.get("control_commands_sent") is True
        and smoke.get("gripper_commands_sent") is False
        and smoke.get("hand_controller_started") is False
        and sample_count_ok
        and post_gate["metrics"]["target_base_drift"] <= args.target_base_drift_max
    )

    checks = [
        {
            "name": "return_reached_no_gripper",
            "passed": bool(ret.get("reached") is True and ret.get("gripper_commands_sent") is False),
            "detail": f"reached={ret.get('reached')} gripper={ret.get('gripper_commands_sent')}",
        },
        {
            "name": "two_pre_gates_passed",
            "passed": bool(gate0.get("passed") is True and gate1.get("passed") is True),
            "detail": f"gate0={gate0.get('passed')} gate1={gate1.get('passed')}",
        },
        {
            "name": "tiny_smoke_completed_configured_commands",
            "passed": bool(completed_status_ok and sample_count_ok),
            "detail": f"status={smoke.get('status')} samples={len(smoke_history)}",
        },
        {
            "name": "tiny_smoke_no_abort_no_gripper",
            "passed": bool(
                smoke.get("aborted") is False
                and smoke.get("gripper_commands_sent") is False
                and smoke.get("hand_controller_started") is False
            ),
            "detail": (
                f"aborted={smoke.get('aborted')} gripper={smoke.get('gripper_commands_sent')} "
                f"hand={smoke.get('hand_controller_started')}"
            ),
        },
        {
            "name": "post_target_drift_ok",
            "passed": bool(post_gate["metrics"]["target_base_drift"] <= args.target_base_drift_max),
            "detail": (
                f"target_base_drift={post_gate['metrics']['target_base_drift']} "
                f"threshold={args.target_base_drift_max}"
            ),
        },
        {
            "name": "post_initial_gate_expected_not_required",
            "passed": True,
            "detail": (
                "post initial-state gate passed=false is expected after moving the arm; "
                f"failed_check_relative_base={not post_gate['checks'].get('relative_base_drift_ok', False)}"
            ),
        },
        {
            "name": "arm_only_success_threshold",
            "passed": bool(arm_only_success),
            "detail": (
                f"final_distance_source={args.final_distance_source} "
                f"final_distance={formal_final_distance} "
                f"distance_reduction={formal_distance_reduction} "
                f"success_distance_max={args.success_distance_max} "
                f"required_reduction>{args.success_distance_reduction_min}"
            ),
        },
    ]

    metrics = {
        "formal_final_distance_source": args.final_distance_source,
        "formal_final_distance": formal_final_distance,
        "formal_distance_reduction": formal_distance_reduction,
        "pre_gate_1_initial_distance": pre_initial_distance,
        "post_gate_initial_distance": post_initial_distance,
        "gate_distance_reduction": distance_reduction_gate,
        "smoke_first_distance": first_smoke_distance,
        "smoke_last_distance": last_smoke_distance,
        "smoke_distance_reduction": smoke_distance_reduction,
        "smoke_min_distance": min_smoke_distance,
        "raw_action_absmax": raw_absmax,
        "clipped_action_absmax": clipped_absmax,
        "clipped_joint_delta_absmax": joint_delta_absmax,
        "post_gate_passed": post_gate.get("passed"),
        "post_gate_failed_checks": [
            name for name, ok in post_gate.get("checks", {}).items() if not ok
        ],
        "post_gate_target_base_drift": post_gate["metrics"]["target_base_drift"],
        "post_gate_relative_base_drift": post_gate["metrics"]["relative_base_drift"],
    }
    payload = {
        "tool": "summarize_b8_base_relative_tiny_smoke",
        "control_commands_sent": bool(smoke.get("control_commands_sent")),
        "gripper_commands_sent": False,
        "hand_controller_started": False,
        "learned_rollout_run": True,
        "smoke_status": (
            "arm_only_reaching_success"
            if command_path_smoke_resolved and arm_only_success
            else
            "command_path_smoke_resolved_not_success"
            if command_path_smoke_resolved and not arm_only_success
            else "not_resolved"
        ),
        "command_path_smoke_resolved": command_path_smoke_resolved,
        "arm_only_reaching_success_claimed": bool(arm_only_success),
        "grasp_success_claimed": False,
        "learned_rollout_success_claimed": False,
        "checks_passed": all(bool(check["passed"]) for check in checks),
        "checks": checks,
        "metrics": metrics,
        "inputs": {
            "return_json": str(args.return_json),
            "pre_gate_0_json": str(args.pre_gate_0_json),
            "pre_gate_1_json": str(args.pre_gate_1_json),
            "smoke_json": str(args.smoke_json),
            "post_gate_json": str(args.post_gate_json),
        },
        "next_steps": [
            "Return the arm to reference before any further live checks.",
            "Do not run another learned smoke until this summary is reviewed.",
            (
                "Treat this as a single arm-only reaching smoke success, not "
                "general learned rollout success."
                if arm_only_success
                else "Treat the command path as smoke-resolved only; do not claim arm-only reaching success."
            ),
            "If continuing, use read-only diagnostics on the smoke history or run a post-return gate.",
        ],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(payload, args.output_md)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
