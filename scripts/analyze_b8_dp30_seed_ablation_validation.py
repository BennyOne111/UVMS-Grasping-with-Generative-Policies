#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
from typing import Mapping

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from analyze_b8_dp_fm_validation_windows import _json_safe, _predict_candidate  # noqa: E402
from learning.train.train_bc import choose_device  # noqa: E402


def _dp_config(seed: int) -> Path:
    suffix = "" if seed == 84 else f"_seed{seed}"
    return PACKAGE_ROOT / f"config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30{suffix}.yaml"


def _dp_checkpoint(seed: int) -> Path:
    suffix = "" if seed == 84 else f"_seed{seed}"
    return PACKAGE_ROOT / f"outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30{suffix}/best.pt"


def _candidate_for_seed(seed: int) -> Mapping[str, object]:
    return {
        "key": f"dp30_seed{seed}_zero",
        "name": f"Diffusion zero epoch30 seed{seed}",
        "policy_type": "diffusion",
        "sampling_mode": "zero",
        "num_inference_steps": 50,
        "seed": seed,
        "config": _dp_config(seed),
        "checkpoint": _dp_checkpoint(seed),
    }


def _bc_candidate() -> Mapping[str, object]:
    return {
        "key": "bc_ref",
        "name": "BC direct base-relative safe-norm",
        "policy_type": "bc",
        "config": PACKAGE_ROOT / "config/train_bc_b8_primary30_h8_xyz_base_relative_safe_norm.yaml",
        "checkpoint": PACKAGE_ROOT / "outputs/checkpoints/b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt",
    }


def _decision(rows, missing):
    by_key = {row["key"]: row for row in rows}
    bc = by_key["bc_ref"]
    dp_rows = [row for row in rows if str(row["key"]).startswith("dp30_seed")]
    best_dp = min(dp_rows, key=lambda row: float(row["action_mse"])) if dp_rows else None
    bc_mse = float(bc["action_mse"])
    best_dp_mse = float(best_dp["action_mse"]) if best_dp else float("inf")
    return {
        "bc_remains_reference": bool(bc_mse <= best_dp_mse),
        "best_dp_seed_candidate": best_dp["key"] if best_dp else None,
        "best_dp_action_mse": best_dp_mse,
        "bc_action_mse": bc_mse,
        "best_dp_relative_to_bc": (best_dp_mse - bc_mse) / max(bc_mse, 1e-12),
        "missing_candidate_count": len(missing),
        "dp_fm_live_approved": False,
        "training_started_by_this_script": False,
        "next_allowed": "offline-only training/eval iteration; no DP/FM live",
    }


def _write_md(payload: Mapping[str, object], path: Path) -> None:
    decision = payload["decision"]
    lines = [
        "# B8 DP30 Seed Ablation Validation",
        "",
        "Offline-only validation-window comparison for BC and available DP30 seed",
        "ablation checkpoints. This script does not train, does not start ROS, and",
        "does not run learned rollout.",
        "",
        "## Decision",
        "",
        "```text",
        f"bc_remains_reference={decision['bc_remains_reference']}",
        f"best_dp_seed_candidate={decision['best_dp_seed_candidate']}",
        f"best_dp_relative_to_bc={decision['best_dp_relative_to_bc']}",
        f"missing_candidate_count={decision['missing_candidate_count']}",
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
    if payload["missing_candidates"]:
        lines.extend(["", "## Missing Candidates", ""])
        for row in payload["missing_candidates"]:
            lines.append(f"- `{row['key']}` missing checkpoint `{row['checkpoint']}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- DP/FM live remains blocked.",
            "- BC remains the live reference unless a DP seed beats it offline under",
            "  the same base-relative safe-norm setup and live readiness is separately",
            "  reviewed.",
            "- No grasp or general learned rollout success is claimed.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline-only validation for DP30 seed ablation checkpoints.")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--split", default="val", choices=["train", "val"])
    parser.add_argument("--seeds", type=int, nargs="+", default=[84, 85, 86])
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.md",
    )
    args = parser.parse_args()

    device = choose_device(args.device)
    candidates = [_bc_candidate()]
    missing = []
    for seed in args.seeds:
        candidate = _candidate_for_seed(seed)
        checkpoint = Path(candidate["checkpoint"])
        if checkpoint.exists():
            candidates.append(candidate)
        else:
            missing.append(
                {
                    "key": candidate["key"],
                    "checkpoint": str(checkpoint.relative_to(PACKAGE_ROOT)),
                    "config": str(Path(candidate["config"]).relative_to(PACKAGE_ROOT)),
                }
            )

    rows = [_predict_candidate(candidate, args.split, device) for candidate in candidates]
    payload = {
        "artifact": "dp30_seed_ablation_validation_windows",
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
        "missing_candidates": missing,
        "decision": _decision(rows, missing),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    safe = _json_safe(payload)
    args.output_json.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(safe, args.output_md)
    print(json.dumps(safe["decision"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
