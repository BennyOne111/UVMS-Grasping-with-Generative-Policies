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
        "# B8 Base-Relative Tiny Arm-Only Repeatability Summary",
        "",
        "This is a read-only aggregate over tiny active-left arm-only learned",
        "smoke summaries. It may report an arm-only repeatability smoke pass,",
        "but it never claims grasp success or general learned rollout success.",
        "",
        "## Decision",
        "",
        f"- Repeatability smoke status: `{payload['repeatability_smoke_status']}`",
        f"- Repeatability smoke passed: `{payload['repeatability_smoke_passed']}`",
        f"- Arm-only reaching repeatability claimed: `{payload['arm_only_reaching_repeatability_claimed']}`",
        f"- Learned rollout success claimed: `{payload['learned_rollout_success_claimed']}`",
        f"- Grasp success claimed: `{payload['grasp_success_claimed']}`",
        "",
        "## Cycle Checks",
        "",
        "| cycle | passed | status | final distance | reduction | gripper | detail |",
        "|---:|---:|---|---:|---:|---:|---|",
    ]
    for cycle in payload["cycles"]:
        metrics = cycle["metrics"]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(cycle["cycle_index"]),
                    str(cycle["passed"]),
                    str(cycle["smoke_status"]),
                    str(metrics.get("post_gate_initial_distance")),
                    str(metrics.get("gate_distance_reduction")),
                    str(cycle["gripper_commands_sent"]),
                    str(cycle["detail"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Aggregate Metrics",
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
        description="Aggregate N-cycle B8 base-relative tiny arm-only smoke summaries."
    )
    parser.add_argument(
        "--cycle-summary-json",
        type=Path,
        action="append",
        required=True,
        help="Per-cycle summary JSON produced by summarize_b8_base_relative_tiny_smoke.py.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n2/summary.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n2/summary.md",
    )
    parser.add_argument("--expected-cycle-count", type=int, default=2)
    parser.add_argument("--max-raw-action-absmax", type=float, default=0.012)
    parser.add_argument("--max-clipped-action-absmax", type=float, default=0.005)
    parser.add_argument("--max-clipped-joint-delta-absmax", type=float, default=0.01)
    args = parser.parse_args()

    cycles = []
    for index, path in enumerate(args.cycle_summary_json):
        summary = _load_json(path)
        metrics = summary.get("metrics", {}) or {}
        cycle_passed = bool(
            summary.get("checks_passed") is True
            and summary.get("command_path_smoke_resolved") is True
            and summary.get("smoke_status") == "arm_only_reaching_success"
            and summary.get("arm_only_reaching_success_claimed") is True
            and summary.get("learned_rollout_success_claimed") is False
            and summary.get("grasp_success_claimed") is False
            and summary.get("gripper_commands_sent") is False
            and summary.get("hand_controller_started") is False
            and float(metrics.get("raw_action_absmax", float("inf"))) <= args.max_raw_action_absmax
            and float(metrics.get("clipped_action_absmax", float("inf"))) <= args.max_clipped_action_absmax
            and float(metrics.get("clipped_joint_delta_absmax", float("inf")))
            <= args.max_clipped_joint_delta_absmax
        )
        cycles.append(
            {
                "cycle_index": index,
                "path": str(path),
                "passed": cycle_passed,
                "smoke_status": summary.get("smoke_status"),
                "checks_passed": summary.get("checks_passed"),
                "command_path_smoke_resolved": summary.get("command_path_smoke_resolved"),
                "arm_only_reaching_success_claimed": summary.get("arm_only_reaching_success_claimed"),
                "learned_rollout_success_claimed": summary.get("learned_rollout_success_claimed"),
                "grasp_success_claimed": summary.get("grasp_success_claimed"),
                "gripper_commands_sent": summary.get("gripper_commands_sent"),
                "hand_controller_started": summary.get("hand_controller_started"),
                "metrics": metrics,
                "detail": (
                    f"raw={metrics.get('raw_action_absmax')} "
                    f"clip={metrics.get('clipped_action_absmax')} "
                    f"joint={metrics.get('clipped_joint_delta_absmax')}"
                ),
            }
        )

    expected_count_ok = len(cycles) == args.expected_cycle_count
    repeatability_passed = bool(expected_count_ok and all(cycle["passed"] for cycle in cycles))
    final_distances = [
        float(cycle["metrics"]["post_gate_initial_distance"])
        for cycle in cycles
        if "post_gate_initial_distance" in cycle["metrics"]
    ]
    reductions = [
        float(cycle["metrics"]["gate_distance_reduction"])
        for cycle in cycles
        if "gate_distance_reduction" in cycle["metrics"]
    ]

    payload = {
        "tool": "summarize_b8_base_relative_tiny_repeatability",
        "cycle_count": len(cycles),
        "expected_cycle_count": args.expected_cycle_count,
        "offline_only_summary": True,
        "control_commands_sent_by_summary": False,
        "gripper_commands_sent": False,
        "learned_rollout_run_by_summary": False,
        "repeatability_smoke_status": (
            "arm_only_reaching_repeatability_smoke_passed"
            if repeatability_passed
            else "not_resolved"
        ),
        "repeatability_smoke_passed": repeatability_passed,
        "arm_only_reaching_repeatability_claimed": repeatability_passed,
        "learned_rollout_success_claimed": False,
        "grasp_success_claimed": False,
        "checks_passed": repeatability_passed,
        "cycles": cycles,
        "metrics": {
            "expected_count_ok": expected_count_ok,
            "success_count": int(sum(1 for cycle in cycles if cycle["passed"])),
            "mean_final_distance": (
                float(sum(final_distances) / len(final_distances)) if final_distances else None
            ),
            "max_final_distance": max(final_distances) if final_distances else None,
            "mean_gate_distance_reduction": (
                float(sum(reductions) / len(reductions)) if reductions else None
            ),
            "min_gate_distance_reduction": min(reductions) if reductions else None,
        },
        "next_steps": [
            "Do not claim grasp success or general learned rollout success.",
            "Return the arm to reference before any further live work.",
            (
                "If N=2 passes and further live work is approved, plan N=3 with "
                "the same fixed checkpoint/clip/tick parameters."
            ),
            "If any cycle fails, stop live work and inspect that cycle's JSON artifacts.",
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(payload, args.output_md)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
