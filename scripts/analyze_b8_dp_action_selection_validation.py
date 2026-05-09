#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
from typing import Mapping

import torch


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


def _dp_candidate(key: str, config_name: str, checkpoint_path: str) -> Mapping[str, object]:
    checkpoint = PACKAGE_ROOT / checkpoint_path
    meta = torch.load(str(checkpoint), map_location="cpu")
    return {
        "key": key,
        "name": key,
        "policy_type": "diffusion",
        "sampling_mode": "zero",
        "num_inference_steps": 50,
        "seed": 86,
        "config": PACKAGE_ROOT / "config" / config_name,
        "checkpoint": checkpoint,
        "checkpoint_epoch": int(meta.get("epoch", -1)),
        "checkpoint_val_loss": float(meta.get("val_loss", float("nan"))),
        "checkpoint_val_zero_init_action_mse": (
            float(meta["val_zero_init_action_mse"]) if "val_zero_init_action_mse" in meta else None
        ),
    }


def _decision(rows):
    bc = next(row for row in rows if row["key"] == "bc_ref")
    dp_rows = [row for row in rows if row["key"] != "bc_ref"]
    best_dp = min(dp_rows, key=lambda row: float(row["action_mse"]))
    bc_mse = float(bc["action_mse"])
    action_selected = next(row for row in rows if row["key"] == "dp30_seed86_action_selected_best_action")
    return {
        "bc_remains_reference": bool(bc_mse <= float(best_dp["action_mse"])),
        "best_dp": best_dp["key"],
        "best_dp_action_mse": float(best_dp["action_mse"]),
        "best_dp_relative_to_bc": (float(best_dp["action_mse"]) - bc_mse) / max(bc_mse, 1e-12),
        "action_selection_improves_over_baseline_seed86": bool(
            float(action_selected["action_mse"])
            < float(next(row for row in rows if row["key"] == "dp30_seed86_baseline_best")["action_mse"])
        ),
        "action_selection_beats_bc": bool(float(action_selected["action_mse"]) < bc_mse),
        "dp_fm_live_approved": False,
        "training_started_by_this_script": False,
        "next_allowed": "offline-only objective/selection diagnostics; no live",
    }


def _write_md(payload: Mapping[str, object], path: Path) -> None:
    decision = payload["decision"]
    lines = [
        "# B8 DP Action-Selection Validation",
        "",
        "Offline-only validation of a DP checkpoint-selection ablation. Training",
        "still used the epsilon objective, but saved an additional `best_action.pt`",
        "using unnormalized zero-init action MSE on validation windows.",
        "",
        "## Decision",
        "",
        "```text",
        f"bc_remains_reference={decision['bc_remains_reference']}",
        f"best_dp={decision['best_dp']}",
        f"best_dp_relative_to_bc={decision['best_dp_relative_to_bc']}",
        f"action_selection_improves_over_baseline_seed86={decision['action_selection_improves_over_baseline_seed86']}",
        f"action_selection_beats_bc={decision['action_selection_beats_bc']}",
        "dp_fm_live_approved=false",
        "training_started_by_this_script=false",
        "```",
        "",
        "## Metrics",
        "",
        "| candidate | epoch | ckpt val loss | ckpt action MSE | eval action MSE | first-step MSE | p95 window MSE | max window MSE |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["candidates"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["key"]),
                    str(row.get("checkpoint_epoch")),
                    str(row.get("checkpoint_val_loss")),
                    str(row.get("checkpoint_val_zero_init_action_mse")),
                    str(row["action_mse"]),
                    str(row["first_step_mse_mean"]),
                    str(row["per_window_mse"]["p95"]),
                    str(row["per_window_mse"]["max"]),
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
            "- This is an offline checkpoint-selection ablation only.",
            "- No grasp success, learned rollout success, or general rollout success",
            "  is claimed.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline-only DP action-selection validation.")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--split", default="val", choices=["train", "val"])
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp_action_selection_validation.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp_action_selection_validation.md",
    )
    args = parser.parse_args()

    candidates = [
        _bc_candidate(),
        _dp_candidate(
            "dp30_seed86_baseline_best",
            "train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86.yaml",
            "outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86/best.pt",
        ),
        _dp_candidate(
            "dp30_seed86_action_select_best_loss",
            "train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86_action_select.yaml",
            "outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86_action_select/best.pt",
        ),
        _dp_candidate(
            "dp30_seed86_action_selected_best_action",
            "train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86_action_select.yaml",
            "outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86_action_select/best_action.pt",
        ),
    ]

    device = choose_device(args.device)
    rows = []
    for candidate in candidates:
        meta = {
            "checkpoint_epoch": candidate.pop("checkpoint_epoch", None),
            "checkpoint_val_loss": candidate.pop("checkpoint_val_loss", None),
            "checkpoint_val_zero_init_action_mse": candidate.pop("checkpoint_val_zero_init_action_mse", None),
        }
        row = _predict_candidate(candidate, args.split, device)
        row.update(meta)
        rows.append(row)

    payload = {
        "artifact": "dp_action_selection_validation",
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
