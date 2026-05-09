#!/usr/bin/env python3

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Optional


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, object]:
    with path.expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _mean(values: Iterable[Optional[float]]) -> Optional[float]:
    clean = [float(value) for value in values if value is not None]
    return float(mean(clean)) if clean else None


def _action_smoothness(history: List[Dict[str, object]]) -> Optional[float]:
    actions = [
        [float(v) for v in row.get("clipped_action_xyz", [])]
        for row in history
        if len(row.get("clipped_action_xyz", []) or []) == 3
    ]
    if len(actions) < 2:
        return None
    diffs = []
    for prev, cur in zip(actions[:-1], actions[1:]):
        diffs.append(sum((cur[i] - prev[i]) ** 2 for i in range(3)) ** 0.5)
    return float(mean(diffs)) if diffs else None


def _method_summary(method_dir: Path, method: str) -> Dict[str, object]:
    cycle_dirs = sorted(path for path in method_dir.glob("cycle_*") if path.is_dir())
    cycles = []
    failure_reasons: Counter = Counter()
    incomplete_cycle_count = 0
    for cycle_dir in cycle_dirs:
        cycle_index = int(cycle_dir.name.split("_")[-1])
        summary_path = cycle_dir / "summary.json"
        smoke_path = cycle_dir / "smoke.json"
        post_gate_path = cycle_dir / "post_gate.json"
        return_path = cycle_dir / "return_to_reference.json"
        pre_gate_paths = sorted(cycle_dir.glob("pre_gate_*.json"))

        summary = _load_json(summary_path) if summary_path.exists() else {}
        smoke = _load_json(smoke_path) if smoke_path.exists() else {}
        incomplete_artifact = not (summary_path.exists() and smoke_path.exists())
        if incomplete_artifact:
            incomplete_cycle_count += 1
        post_gate = _load_json(post_gate_path) if post_gate_path.exists() else {}
        ret = _load_json(return_path) if return_path.exists() else {}
        pre_gates = [_load_json(path) for path in pre_gate_paths]
        metrics = summary.get("metrics", {}) or {}
        history = list(smoke.get("history", []) or [])
        distances = [
            float(row["distance_to_target"])
            for row in history
            if "distance_to_target" in row
        ]

        passed = bool(
            summary.get("smoke_status") == "arm_only_reaching_success"
            and summary.get("checks_passed") is True
            and smoke.get("aborted") is False
            and smoke.get("gripper_commands_sent") is False
            and smoke.get("hand_controller_started") is False
        )
        abort_reason = str(smoke.get("abort_reason") or "")
        if abort_reason:
            failure_reasons[abort_reason] += 1
        elif not passed:
            failed_checks = [
                str(check.get("name"))
                for check in summary.get("checks", []) or []
                if check.get("passed") is not True
            ]
            reason = ",".join(failed_checks) if failed_checks else "not_success"
            failure_reasons[reason] += 1

        cycles.append(
            {
                "cycle_index": cycle_index,
                "incomplete_artifact": incomplete_artifact,
                "passed": passed,
                "status": smoke.get("status"),
                "aborted": bool(smoke.get("aborted")),
                "abort_reason": abort_reason or None,
                "final_distance": metrics.get("formal_final_distance")
                if metrics.get("formal_final_distance") is not None
                else metrics.get("post_gate_initial_distance"),
                "final_distance_source": metrics.get("formal_final_distance_source", "post_gate"),
                "min_distance": metrics.get("smoke_min_distance")
                if metrics.get("smoke_min_distance") is not None
                else (min(distances) if distances else None),
                "distance_reduction": metrics.get("formal_distance_reduction")
                if metrics.get("formal_distance_reduction") is not None
                else metrics.get("gate_distance_reduction"),
                "target_base_drift": metrics.get("post_gate_target_base_drift")
                if metrics.get("post_gate_target_base_drift") is not None
                else (
                    metrics.get("pre_gate_target_base_drift")
                    if metrics.get("pre_gate_target_base_drift") is not None
                    else (post_gate.get("metrics", {}) or {}).get("target_base_drift")
                ),
                "relative_base_drift": metrics.get("post_gate_relative_base_drift")
                if metrics.get("post_gate_relative_base_drift") is not None
                else (
                    metrics.get("pre_gate_relative_base_drift")
                    if metrics.get("pre_gate_relative_base_drift") is not None
                    else (post_gate.get("metrics", {}) or {}).get("relative_base_drift")
                ),
                "mean_action_smoothness": _action_smoothness(history),
                "mean_inference_latency_ms": _mean(
                    row.get("latency_ms") for row in history if row.get("latency_ms") is not None
                ),
                "raw_action_absmax": metrics.get("raw_action_absmax"),
                "clipped_action_absmax": metrics.get("clipped_action_absmax"),
                "clipped_joint_delta_absmax": metrics.get("clipped_joint_delta_absmax"),
                "return_reached": ret.get("reached"),
                "pre_gate_passed": [gate.get("passed") for gate in pre_gates],
                "gripper_commands_sent": bool(
                    summary.get("gripper_commands_sent") or smoke.get("gripper_commands_sent")
                ),
                "hand_controller_started": bool(
                    summary.get("hand_controller_started") or smoke.get("hand_controller_started")
                ),
                "paths": {
                    "return_json": str(return_path) if return_path.exists() else None,
                    "pre_gate_json": [str(path) for path in pre_gate_paths],
                    "smoke_json": str(smoke_path) if smoke_path.exists() else None,
                    "post_gate_json": str(post_gate_path) if post_gate_path.exists() else None,
                    "summary_json": str(summary_path) if summary_path.exists() else None,
                },
            }
        )

    success_count = sum(1 for cycle in cycles if cycle["passed"])
    n = len(cycles)
    return {
        "method": method,
        "completed": n > 0 and incomplete_cycle_count == 0,
        "incomplete_cycle_count": incomplete_cycle_count,
        "N": n,
        "success_count": success_count,
        "success_rate": float(success_count / n) if n else None,
        "abort_count": sum(1 for cycle in cycles if cycle["aborted"]),
        "mean_final_distance": _mean(cycle.get("final_distance") for cycle in cycles),
        "mean_min_distance": _mean(cycle.get("min_distance") for cycle in cycles),
        "mean_distance_reduction": _mean(cycle.get("distance_reduction") for cycle in cycles),
        "target_drift_summary": {
            "mean_target_base_drift": _mean(cycle.get("target_base_drift") for cycle in cycles),
            "max_target_base_drift": max(
                [float(cycle["target_base_drift"]) for cycle in cycles if cycle.get("target_base_drift") is not None],
                default=None,
            ),
            "mean_relative_base_drift": _mean(cycle.get("relative_base_drift") for cycle in cycles),
        },
        "mean_action_smoothness": _mean(cycle.get("mean_action_smoothness") for cycle in cycles),
        "mean_inference_latency_ms": _mean(cycle.get("mean_inference_latency_ms") for cycle in cycles),
        "failure_reason_distribution": dict(sorted(failure_reasons.items())),
        "gripper_commands_sent": any(cycle["gripper_commands_sent"] for cycle in cycles),
        "hand_controller_started": any(cycle["hand_controller_started"] for cycle in cycles),
        "cycles": cycles,
    }


def _write_markdown(payload: Dict[str, object], path: Path) -> None:
    lines = [
        "# BC / DP / FM Arm-Only Live Success-Rate Summary",
        "",
        "Scope: active-left arm-only reaching / pre-grasp positioning. This report",
        "does not evaluate grasping and does not claim object grasped, lifted, or held.",
        "",
        f"- Equal N across completed methods: `{payload['equal_N_across_methods']}`",
        f"- Complete three-method comparison: `{payload['complete_three_method_live_comparison']}`",
        f"- No gripper command observed in summaries: `{payload['no_gripper_command_observed']}`",
        "",
        "| method | completed | incomplete cycles | success_count | N | success_rate | mean final distance | mean min distance | mean reduction | aborts | mean latency ms | mean smoothness |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for method in payload["methods"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    method["method"],
                    str(method["completed"]),
                    str(method["incomplete_cycle_count"]),
                    str(method["success_count"]),
                    str(method["N"]),
                    str(method["success_rate"]),
                    str(method["mean_final_distance"]),
                    str(method["mean_min_distance"]),
                    str(method["mean_distance_reduction"]),
                    str(method["abort_count"]),
                    str(method["mean_inference_latency_ms"]),
                    str(method["mean_action_smoothness"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Failure Reasons", ""])
    for method in payload["methods"]:
        lines.append(f"- {method['method']}: `{method['failure_reason_distribution']}`")
    lines.extend(["", "## Protocol", "", "```text"])
    lines.append(json.dumps(payload["protocol"], indent=2, sort_keys=True))
    lines.extend(["```", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_method_markdown(method: Dict[str, object], path: Path) -> None:
    lines = [
        f"# {method['method'].upper()} Live Arm-Only Method Summary",
        "",
        f"- Completed cycles: `{method['N']}`",
        f"- Complete artifact set: `{method['completed']}`",
        f"- Incomplete cycle count: `{method['incomplete_cycle_count']}`",
        f"- Success count: `{method['success_count']}`",
        f"- Success rate: `{method['success_rate']}`",
        f"- Abort count: `{method['abort_count']}`",
        f"- Mean final distance: `{method['mean_final_distance']}`",
        f"- Mean min distance: `{method['mean_min_distance']}`",
        f"- Mean distance reduction: `{method['mean_distance_reduction']}`",
        f"- Failure reasons: `{method['failure_reason_distribution']}`",
        f"- Gripper commands sent: `{method['gripper_commands_sent']}`",
        f"- Hand controller started by eval: `{method['hand_controller_started']}`",
        "",
        "This summary is for arm-only reaching / pre-grasp positioning only.",
        "It does not claim grasp success.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize BC/DP/FM formal live arm-only success-rate artifacts.")
    parser.add_argument(
        "--root-dir",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md",
    )
    args = parser.parse_args()

    protocol_path = args.root_dir / "formal_protocol.json"
    protocol = _load_json(protocol_path) if protocol_path.exists() else {}
    methods = [_method_summary(args.root_dir / method, method) for method in ["bc", "dp", "fm"]]
    for method in methods:
        method_dir = args.root_dir / str(method["method"])
        method_dir.mkdir(parents=True, exist_ok=True)
        (method_dir / "method_summary.json").write_text(
            json.dumps(method, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_method_markdown(method, method_dir / "method_summary.md")
    completed_ns = [method["N"] for method in methods if method["completed"]]
    equal_n = bool(completed_ns and len(set(completed_ns)) == 1 and len(completed_ns) == 3)
    payload = {
        "tool": "summarize_b8_bc_dp_fm_success_rate",
        "root_dir": str(args.root_dir),
        "protocol": protocol,
        "methods": methods,
        "equal_N_across_methods": equal_n,
        "complete_three_method_live_comparison": bool(
            equal_n and all(method["completed"] for method in methods)
        ),
        "no_gripper_command_observed": not any(method["gripper_commands_sent"] for method in methods),
        "no_hand_controller_started_by_eval": not any(method["hand_controller_started"] for method in methods),
        "grasp_success_claimed": False,
        "object_grasped_lifted_held_claimed": False,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(payload, args.output_md)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
