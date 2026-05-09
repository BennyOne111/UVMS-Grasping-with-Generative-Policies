#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional

import numpy as np


def _load_json(path: Path) -> Optional[Dict[str, object]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _is_gate(data: Mapping[str, object]) -> bool:
    return (
        data.get("gate") == "b8_initial_state_gate"
        and isinstance(data.get("metrics"), dict)
        and isinstance(data.get("checks"), dict)
    )


def _context(path: Path) -> str:
    text = str(path)
    if "/pre_gate/" in text or "_pre_gate/" in text or "/pre_" in text:
        return "pre_live_gate"
    if "/post_gate/" in text or "post_smoke_gate" in text:
        return "post_live_gate"
    if "post_run_recovery" in text or "post_repeatability_return_gate" in text:
        return "recovery_gate"
    if "return_gate" in text:
        return "post_return_gate"
    if "initial_state_gate" in text:
        return "initial_state_gate"
    return "other_gate"


def _iter_gate_files(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if not root.exists():
            continue
        yield from sorted(root.rglob("*.json"))


def _float_or_none(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percentiles(values: List[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"count": 0, "min": None, "p50": None, "p90": None, "p95": None, "max": None}
    arr = np.asarray(values, dtype=np.float64)
    return {
        "count": int(arr.size),
        "min": float(np.min(arr)),
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(np.max(arr)),
    }


def _summarize(rows: List[Mapping[str, object]]) -> Dict[str, object]:
    by_context: Dict[str, List[Mapping[str, object]]] = {}
    for row in rows:
        by_context.setdefault(str(row["context"]), []).append(row)

    output = {}
    for name, items in sorted(by_context.items()):
        target = [row["target_base_drift"] for row in items if row["target_base_drift"] is not None]
        relative = [row["relative_base_drift"] for row in items if row["relative_base_drift"] is not None]
        initial = [row["initial_distance"] for row in items if row["initial_distance"] is not None]
        output[name] = {
            "count": len(items),
            "passed_count": sum(1 for row in items if row["passed"] is True),
            "clean_target_count": sum(1 for row in items if row["target_clean"] is True),
            "target_base_drift": _percentiles(target),
            "relative_base_drift": _percentiles(relative),
            "initial_distance": _percentiles(initial),
        }
    return output


def _row(path: Path, data: Mapping[str, object], clean_target_max: float, clean_relative_max: float) -> Dict[str, object]:
    metrics = data.get("metrics", {}) or {}
    checks = data.get("checks", {}) or {}
    target_base_drift = _float_or_none(metrics.get("target_base_drift"))
    relative_base_drift = _float_or_none(metrics.get("relative_base_drift"))
    target_clean = (
        target_base_drift is not None
        and relative_base_drift is not None
        and target_base_drift <= clean_target_max
        and relative_base_drift <= clean_relative_max
    )
    return {
        "path": str(path),
        "context": _context(path),
        "passed": data.get("passed"),
        "target_clean": target_clean,
        "initial_distance": _float_or_none(metrics.get("initial_distance")),
        "target_base_drift": target_base_drift,
        "relative_base_drift": relative_base_drift,
        "eef_base_drift": _float_or_none(metrics.get("eef_base_drift")),
        "joint_l2_drift": _float_or_none(metrics.get("joint_l2_drift")),
        "joint_max_abs_drift": _float_or_none(metrics.get("joint_max_abs_drift")),
        "failed_checks": [name for name, ok in checks.items() if ok is not True],
        "control_commands_sent": data.get("control_commands_sent"),
        "gripper_commands_sent": data.get("gripper_commands_sent"),
    }


def _decision(rows: List[Mapping[str, object]], clean_target_max: float, clean_relative_max: float) -> Dict[str, object]:
    pre = [row for row in rows if row["context"] == "pre_live_gate"]
    post = [row for row in rows if row["context"] == "post_live_gate"]
    failed_post_target = [
        row
        for row in post
        if row["target_base_drift"] is not None and float(row["target_base_drift"]) > 0.01
    ]
    clean_pre = [row for row in pre if row["passed"] is True and row["target_clean"] is True]

    return {
        "target_drift_is_live_confound": bool(failed_post_target),
        "clean_pre_gate_examples": len(clean_pre),
        "failed_post_target_drift_examples": len(failed_post_target),
        "recommended_readiness_gate": {
            "name": "two_fresh_gates_with_clean_target_drift",
            "consecutive_required": 2,
            "initial_distance_max": 0.115,
            "relative_base_drift_max": clean_relative_max,
            "target_base_drift_max": clean_target_max,
            "joint_l2_max": 0.02,
            "joint_max_abs_max": 0.01,
            "eef_base_drift_max": 0.02,
            "wait_retry_only": True,
            "reset_target_if_failed_after_retries": "separate explicit approval required",
        },
        "why": [
            "Tick9 passed with very low target drift, while failed N3 cycle 1 had target drift just over the strict 0.01 m boundary.",
            "A standard passed gate can still be near the target-drift boundary; requiring a cleaner target drift separates motion-budget effects from target-updater jitter.",
            "This is a readiness gate only and does not approve live execution by itself.",
        ],
        "next_live_approved": False,
        "dp_fm_live_approved": False,
        "n3_repeatability_resolved": False,
    }


def _write_md(payload: Mapping[str, object], path: Path) -> None:
    decision = payload["decision"]
    gate = decision["recommended_readiness_gate"]
    lines = [
        "# B8 Target-Drift Readiness Gate Review",
        "",
        "This report is read-only. It scans existing gate artifacts only; it sends no",
        "commands, starts no hand/gripper controller, and does not train BC/DP/FM.",
        "",
        "## Decision",
        "",
        "```text",
        f"target_drift_is_live_confound={decision['target_drift_is_live_confound']}",
        f"clean_pre_gate_examples={decision['clean_pre_gate_examples']}",
        f"failed_post_target_drift_examples={decision['failed_post_target_drift_examples']}",
        "next_live_approved=false",
        "dp_fm_live_approved=false",
        "n3_repeatability_resolved=false",
        "```",
        "",
        "## Recommended Readiness Gate",
        "",
        "Before any future BC live smoke is separately approved, use this stricter",
        "fresh-gate readiness criterion to decouple target drift from motion budget:",
        "",
        "```text",
        f"name={gate['name']}",
        f"consecutive_required={gate['consecutive_required']}",
        f"initial_distance_max={gate['initial_distance_max']}",
        f"relative_base_drift_max={gate['relative_base_drift_max']}",
        f"target_base_drift_max={gate['target_base_drift_max']}",
        f"joint_l2_max={gate['joint_l2_max']}",
        f"joint_max_abs_max={gate['joint_max_abs_max']}",
        f"eef_base_drift_max={gate['eef_base_drift_max']}",
        "wait_retry_only=true",
        "```",
        "",
        "## Context Summary",
        "",
        "| context | count | passed | clean target | target drift p50 | target drift p95 | target drift max |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for context, summary in payload["summary_by_context"].items():
        target = summary["target_base_drift"]
        lines.append(
            "| "
            + " | ".join(
                [
                    context,
                    str(summary["count"]),
                    str(summary["passed_count"]),
                    str(summary["clean_target_count"]),
                    str(target["p50"]),
                    str(target["p95"]),
                    str(target["max"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This does not approve another live smoke.",
            "- This does not approve DP/FM live.",
            "- This does not claim N=3 repeatability, grasp success, or general learned rollout success.",
            "- If live is later approved separately, use wait/retry only until the readiness gate passes.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only review of target drift readiness from existing gate artifacts.")
    default_roots = [
        Path("src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_rollout_planning"),
        Path("src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_initial_state_gate"),
    ]
    parser.add_argument("--roots", nargs="*", type=Path, default=default_roots)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path(
            "src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_rollout_planning/"
            "b8_target_drift_readiness_gate_review.json"
        ),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path(
            "src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_rollout_planning/"
            "b8_target_drift_readiness_gate_review.md"
        ),
    )
    parser.add_argument("--clean-target-drift-max", type=float, default=0.001)
    parser.add_argument("--clean-relative-drift-max", type=float, default=0.001)
    args = parser.parse_args()

    rows = []
    for path in _iter_gate_files(args.roots):
        data = _load_json(path)
        if data is None or not _is_gate(data):
            continue
        rows.append(_row(path, data, args.clean_target_drift_max, args.clean_relative_drift_max))

    payload = {
        "artifact": "b8_target_drift_readiness_gate_review",
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "hand_controller_started": False,
        "training_started": False,
        "gate_count": len(rows),
        "clean_target_drift_max": args.clean_target_drift_max,
        "clean_relative_drift_max": args.clean_relative_drift_max,
        "summary_by_context": _summarize(rows),
        "decision": _decision(rows, args.clean_target_drift_max, args.clean_relative_drift_max),
        "rows": rows,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(payload, args.output_md)
    print(json.dumps(payload["decision"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
