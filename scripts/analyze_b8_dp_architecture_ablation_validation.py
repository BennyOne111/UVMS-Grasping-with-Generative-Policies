#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
from typing import Mapping


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from analyze_b8_dp_fm_validation_windows import _json_safe, _predict_candidate  # noqa: E402
from learning.train.train_bc import choose_device  # noqa: E402


def _bc_candidate() -> Mapping[str, object]:
    return {
        "key": "bc_ref",
        "name": "BC direct base-relative safe-norm",
        "policy_type": "bc",
        "config": PACKAGE_ROOT / "config/train_bc_b8_primary30_h8_xyz_base_relative_safe_norm.yaml",
        "checkpoint": PACKAGE_ROOT / "outputs/checkpoints/b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt",
    }


def _dp_candidate(key: str, config_name: str, checkpoint_name: str) -> Mapping[str, object]:
    return {
        "key": key,
        "name": key,
        "policy_type": "diffusion",
        "sampling_mode": "zero",
        "num_inference_steps": 50,
        "seed": 86,
        "config": PACKAGE_ROOT / "config" / config_name,
        "checkpoint": PACKAGE_ROOT / "outputs/checkpoints" / checkpoint_name / "best.pt",
    }


def _decision(rows):
    bc = next(row for row in rows if row["key"] == "bc_ref")
    dp_rows = [row for row in rows if row["key"] != "bc_ref"]
    best_dp = min(dp_rows, key=lambda row: float(row["action_mse"]))
    bc_mse = float(bc["action_mse"])
    return {
        "bc_remains_reference": bool(bc_mse <= float(best_dp["action_mse"])),
        "best_dp": best_dp["key"],
        "best_dp_action_mse": float(best_dp["action_mse"]),
        "best_dp_relative_to_bc": (float(best_dp["action_mse"]) - bc_mse) / max(bc_mse, 1e-12),
        "w128_improves_over_w256": bool(
            float(next(row for row in rows if row["key"] == "dp30_seed86_w128_zero")["action_mse"])
            < float(next(row for row in rows if row["key"] == "dp30_seed86_w256_zero")["action_mse"])
        ),
        "dp_fm_live_approved": False,
        "training_started_by_this_script": False,
        "next_allowed": "offline-only objective/architecture diagnostics; no live",
    }


def _write_md(payload: Mapping[str, object], path: Path) -> None:
    decision = payload["decision"]
    lines = [
        "# B8 DP Architecture Ablation Validation",
        "",
        "Offline-only validation-window comparison for BC, DP seed86 width256,",
        "and DP seed86 width128. This script does not train, start ROS, or run",
        "learned rollout.",
        "",
        "## Decision",
        "",
        "```text",
        f"bc_remains_reference={decision['bc_remains_reference']}",
        f"best_dp={decision['best_dp']}",
        f"best_dp_relative_to_bc={decision['best_dp_relative_to_bc']}",
        f"w128_improves_over_w256={decision['w128_improves_over_w256']}",
        "dp_fm_live_approved=false",
        "training_started_by_this_script=false",
        "```",
        "",
        "## Metrics",
        "",
        "| candidate | action MSE | first-step MSE | p95 window MSE | max window MSE | pred absmax |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["candidates"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["key"]),
                    str(row["action_mse"]),
                    str(row["first_step_mse_mean"]),
                    str(row["per_window_mse"]["p95"]),
                    str(row["per_window_mse"]["max"]),
                    str(row["action_scale"]["pred_valid_absmax"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- DP/FM live remains blocked.",
            "- BC remains the live reference unless an offline DP/FM candidate beats",
            "  it and live readiness is separately reviewed.",
            "- No grasp success, learned rollout success, or general rollout success",
            "  is claimed.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline-only DP architecture ablation validation.")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--split", default="val", choices=["train", "val"])
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp_architecture_ablation_validation.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp_architecture_ablation_validation.md",
    )
    args = parser.parse_args()

    candidates = [
        _bc_candidate(),
        _dp_candidate(
            "dp30_seed86_w256_zero",
            "train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86.yaml",
            "b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86",
        ),
        _dp_candidate(
            "dp30_seed86_w128_zero",
            "train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86_w128.yaml",
            "b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86_w128",
        ),
    ]
    missing = [candidate for candidate in candidates if not Path(candidate["checkpoint"]).exists()]
    if missing:
        raise FileNotFoundError("missing checkpoints: " + ", ".join(str(row["checkpoint"]) for row in missing))

    device = choose_device(args.device)
    rows = [_predict_candidate(candidate, args.split, device) for candidate in candidates]
    payload = {
        "artifact": "dp_architecture_ablation_validation",
        "offline_only": True,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "hand_controller_started": False,
        "training_started": False,
        "learned_rollout_run": False,
        "learned_rollout_success_claimed": False,
        "grasp_success_claimed": False,
        "split": args.split,
        "candidates": rows,
        "decision": _decision(rows),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    safe = _json_safe(payload)
    args.output_json.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(safe, args.output_md)
    print(json.dumps(safe["decision"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
