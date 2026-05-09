#!/usr/bin/env python3

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, object]:
    with path.expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _launch_arg_default(path: Path, arg_name: str) -> str:
    root = ET.parse(str(path)).getroot()
    for elem in root.findall("arg"):
        if elem.attrib.get("name") == arg_name:
            return elem.attrib.get("default", "")
    return ""


def _adapter_guard_summary(path: Path) -> Dict[str, object]:
    text = path.read_text(encoding="utf-8")
    return {
        "execute_actions_true_forbidden": "execute_actions=true is forbidden" in text,
        "dry_run_only_markers": len(re.findall(r"dry_run_only", text)),
        "calls_arm_converter_convert": ".convert(action_7d)" in text,
        "calls_arm_converter_execute": ".execute(" in text,
        "publishes_action_labels": "action_7d_label_dry_run" in text and "action_xyz_dry_run" in text,
    }


def _write_markdown(payload: Dict[str, object], path: Path) -> None:
    lines: List[str] = [
        "# B8' Base-Relative Tiny Arm-Only Smoke Checklist",
        "",
        "This is a planning/checklist artifact only. It does not run a learned rollout,",
        "does not send arm commands, and does not send gripper commands.",
        "",
        "## Decision",
        "",
        f"- Checklist status: `{payload['checklist_status']}`",
        f"- Learned execution approved here: `{payload['learned_execution_approved_here']}`",
        f"- Current adapter can execute actions: `{payload['current_adapter_can_execute_actions']}`",
        f"- Separate approval required: `{payload['separate_approval_required']}`",
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
            "## If Separately Approved Later",
            "",
            "Run only after return-to-reference and two fresh target-aware gates pass.",
            "The current adapter is still dry-run only, so an execution adapter/review is",
            "required before any command publication.",
            "",
            "```bash",
            payload["future_command_skeleton"],
            "```",
            "",
            "## Non-Goals",
            "",
        ]
    )
    for item in payload["non_goals"]:
        lines.append(f"- {item}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a read-only checklist for a future B8' base-relative tiny "
            "arm-only learned smoke. This does not execute or publish commands."
        )
    )
    parser.add_argument(
        "--preflight-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.json",
    )
    parser.add_argument(
        "--safety-plan-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_arm_only_rollout_safety_plan.json",
    )
    parser.add_argument(
        "--adapter-script",
        type=Path,
        default=PACKAGE_ROOT / "scripts/b8_bc_h8_xyz_base_relative_rollout_dry_run_node.py",
    )
    parser.add_argument(
        "--adapter-launch",
        type=Path,
        default=PACKAGE_ROOT / "launch/b8_bc_h8_xyz_base_relative_rollout_dry_run.launch",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_checklist.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_checklist.md",
    )
    args = parser.parse_args()

    preflight = _load_json(args.preflight_json)
    safety_plan = _load_json(args.safety_plan_json)
    adapter_guard = _adapter_guard_summary(args.adapter_script)
    execute_actions_default = _launch_arg_default(args.adapter_launch, "execute_actions")
    decision = safety_plan.get("decision", {}) or {}

    checks = [
        {
            "name": "preflight_passed",
            "passed": bool(preflight.get("checks_passed") is True),
            "detail": f"candidate_status={preflight.get('candidate_status')}",
        },
        {
            "name": "preflight_does_not_approve_execution",
            "passed": bool(preflight.get("go_for_learned_execution_now") is False),
            "detail": f"go_for_learned_execution_now={preflight.get('go_for_learned_execution_now')}",
        },
        {
            "name": "safety_plan_requires_separate_approval",
            "passed": bool(
                decision.get("requires_separate_approval") is True
                and decision.get("rollout_execution_approved_by_this_plan") is False
            ),
            "detail": (
                f"requires={decision.get('requires_separate_approval')} "
                f"approved={decision.get('rollout_execution_approved_by_this_plan')}"
            ),
        },
        {
            "name": "adapter_execute_actions_forbidden",
            "passed": bool(adapter_guard["execute_actions_true_forbidden"]),
            "detail": "execute_actions=true raises before spin",
        },
        {
            "name": "adapter_no_execute_call",
            "passed": bool(adapter_guard["calls_arm_converter_execute"] is False),
            "detail": f"calls_arm_converter_execute={adapter_guard['calls_arm_converter_execute']}",
        },
        {
            "name": "launch_default_dry_run",
            "passed": bool(execute_actions_default.lower() == "false"),
            "detail": f"execute_actions_default={execute_actions_default}",
        },
    ]

    hard_non_goals = [str(item) for item in safety_plan.get("hard_non_goals", [])]
    payload = {
        "tool": "generate_b8_base_relative_tiny_smoke_checklist",
        "read_only": True,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "learned_rollout_run": False,
        "learned_execution_approved_here": False,
        "separate_approval_required": True,
        "current_adapter_can_execute_actions": False,
        "checklist_status": "ready_for_review" if all(check["passed"] for check in checks) else "not_ready",
        "checks_passed": bool(all(check["passed"] for check in checks)),
        "checks": checks,
        "adapter_guard": adapter_guard,
        "inputs": {
            "preflight_json": str(args.preflight_json),
            "safety_plan_json": str(args.safety_plan_json),
            "adapter_script": str(args.adapter_script),
            "adapter_launch": str(args.adapter_launch),
        },
        "future_command_skeleton": (
            "roslaunch rexrov_single_oberon7_fm_dp <future_reviewed_execution_adapter>.launch \\\n"
            "  execute_actions:=true \\\n"
            "  max_duration_sec:=7.2 \\\n"
            "  rate_hz:=3.0 \\\n"
            "  enable_gripper_command:=false"
        ),
        "non_goals": hard_non_goals,
        "next_steps": [
            "Do not use the current dry-run adapter for execution; it forbids execute_actions=true.",
            "If execution is separately approved, implement/review a tiny active-left arm-only execution adapter first.",
            "Before any execution, return to reference and require two fresh target-aware gates.",
            "Keep no gripper/hand/no grasp-claim constraints in force.",
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(payload, args.output_md)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
