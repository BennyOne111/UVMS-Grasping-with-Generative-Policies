#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Dict, Mapping

import torch


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from analyze_b8_dp_fm_validation_windows import _json_safe, _predict_candidate  # noqa: E402
from learning.train.train_bc import choose_device  # noqa: E402


def _candidate(
    key: str,
    label: str,
    family: str,
    config: str,
    checkpoint: str,
    selection: str,
    sampling_mode: str = None,
    num_inference_steps: int = None,
    ode_steps: int = None,
    seed: int = None,
) -> Dict[str, object]:
    row = {
        "key": key,
        "name": label,
        "family": family,
        "selection": selection,
        "policy_type": {
            "BC": "bc",
            "DP": "diffusion",
            "FM": "flow_matching",
        }[family],
        "config": PACKAGE_ROOT / config,
        "checkpoint": PACKAGE_ROOT / checkpoint,
    }
    if sampling_mode is not None:
        row["sampling_mode"] = sampling_mode
    if num_inference_steps is not None:
        row["num_inference_steps"] = int(num_inference_steps)
    if ode_steps is not None:
        row["ode_steps"] = int(ode_steps)
    if seed is not None:
        row["seed"] = int(seed)
    return row


def _checkpoint_meta(path: Path) -> Dict[str, object]:
    meta = torch.load(str(path), map_location="cpu")
    return {
        "checkpoint_epoch": meta.get("epoch"),
        "checkpoint_val_loss": meta.get("val_loss"),
        "checkpoint_train_loss": meta.get("train_loss"),
        "checkpoint_val_zero_init_action_mse": meta.get("val_zero_init_action_mse"),
        "action_metric_ode_steps": meta.get("action_metric_ode_steps"),
        "action_metric_inference_steps": meta.get("action_metric_inference_steps"),
    }


def _relative(value: float, reference: float) -> float:
    return (float(value) - float(reference)) / max(float(reference), 1e-12)


def _decision(rows):
    bc = next(row for row in rows if row["key"] == "bc_ref")
    bc_mse = float(bc["action_mse"])
    dp_rows = [row for row in rows if row["family"] == "DP"]
    fm_rows = [row for row in rows if row["family"] == "FM"]
    best_dp = min(dp_rows, key=lambda row: float(row["action_mse"]))
    best_fm = min(fm_rows, key=lambda row: float(row["action_mse"]))
    best_overall = min(rows, key=lambda row: float(row["action_mse"]))
    return {
        "presentation_ready_offline_results": True,
        "bc_action_mse": bc_mse,
        "best_dp": best_dp["key"],
        "best_dp_action_mse": float(best_dp["action_mse"]),
        "best_dp_relative_to_bc": _relative(float(best_dp["action_mse"]), bc_mse),
        "best_fm": best_fm["key"],
        "best_fm_action_mse": float(best_fm["action_mse"]),
        "best_fm_relative_to_bc": _relative(float(best_fm["action_mse"]), bc_mse),
        "best_overall": best_overall["key"],
        "best_overall_relative_to_bc": _relative(float(best_overall["action_mse"]), bc_mse),
        "fm_beats_bc_offline_action_mse": bool(float(best_fm["action_mse"]) < bc_mse),
        "dp_beats_bc_offline_action_mse": bool(float(best_dp["action_mse"]) < bc_mse),
        "dp_fm_live_approved": False,
        "grasp_success_claimed": False,
        "learned_rollout_success_claimed": False,
        "boundary": (
            "Offline presentation results are ready. They are not live rollout "
            "success, grasp success, or approval for DP/FM live execution."
        ),
    }


def _write_csv(rows, path: Path) -> None:
    columns = [
        "rank",
        "key",
        "family",
        "selection",
        "checkpoint_epoch",
        "action_mse",
        "relative_to_bc",
        "first_step_mse_mean",
        "p95_window_mse",
        "max_window_mse",
        "pred_valid_absmax",
        "cosine_mean",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            flat = {key: row.get(key) for key in columns}
            flat["p95_window_mse"] = row.get("per_window_mse", {}).get("p95")
            flat["max_window_mse"] = row.get("per_window_mse", {}).get("max")
            flat["pred_valid_absmax"] = row.get("action_scale", {}).get("pred_valid_absmax")
            flat["cosine_mean"] = row.get("action_scale", {}).get("cosine_mean")
            writer.writerow(flat)


def _write_md(payload: Mapping[str, object], path: Path) -> None:
    d = payload["decision"]
    rows = payload["ranked_candidates"]
    lines = [
        "# B8 DP/FM Final Presentation Results",
        "",
        "Date: 2026-05-07.",
        "",
        "Scope: offline-only comparison under the same B8' primary30",
        "base-relative safe-norm h8 xyz dataset, split, observation, action",
        "normalization, and validation-window action metric.",
        "",
        "No ROS launch, no arm command, no gripper/hand command, no learned",
        "rollout, no grasp success, and no general rollout success are claimed.",
        "",
        "## Presentation Takeaway",
        "",
        "```text",
        f"presentation_ready_offline_results={d['presentation_ready_offline_results']}",
        f"best_dp={d['best_dp']}",
        f"best_dp_relative_to_bc={d['best_dp_relative_to_bc']}",
        f"best_fm={d['best_fm']}",
        f"best_fm_relative_to_bc={d['best_fm_relative_to_bc']}",
        f"best_overall={d['best_overall']}",
        f"fm_beats_bc_offline_action_mse={d['fm_beats_bc_offline_action_mse']}",
        f"dp_beats_bc_offline_action_mse={d['dp_beats_bc_offline_action_mse']}",
        "dp_fm_live_approved=false",
        "```",
        "",
        "## Ranked Offline Metrics",
        "",
        "| rank | method | selection | epoch | val action MSE | vs BC | p95 window MSE | max window MSE | note |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["rank"]),
                    str(row["family"]),
                    str(row["selection"]),
                    str(row.get("checkpoint_epoch")),
                    f"{float(row['action_mse']):.12g}",
                    f"{float(row['relative_to_bc']):+.3%}",
                    f"{float(row['per_window_mse']['p95']):.12g}",
                    f"{float(row['per_window_mse']['max']):.12g}",
                    str(row["presentation_note"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- BC is still the live reference because it has the only reviewed",
            "  arm-only learned-smoke evidence.",
            "- DP seed86 is the best DP candidate, but remains worse than BC on",
            "  validation action MSE.",
            "- FM action-selected `best_action.pt` is the best offline validation",
            "  action-MSE candidate in this table, but it is an epoch-1 checkpoint",
            "  and has not been tested live.",
            "- The correct presentation phrasing is: DP/FM were evaluated offline",
            "  under the same base-relative safe-norm setup; FM produced the best",
            "  validation action MSE, while BC remains the only live-smoke-tested",
            "  policy.",
            "",
            "## Boundary",
            "",
            "- Do not claim DP/FM rollout success.",
            "- Do not claim grasp success.",
            "- Do not run DP/FM live from this result alone.",
            "- Next DP/FM step, if needed, is offline robustness: repeat FM",
            "  action-selection across seeds or folds before any live consideration.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate offline DP/FM final presentation results.")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--split", default="val", choices=["train", "val"])
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_results.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_results.md",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_results.csv",
    )
    args = parser.parse_args()

    candidates = [
        _candidate(
            "bc_ref",
            "BC direct base-relative safe-norm",
            "BC",
            "config/train_bc_b8_primary30_h8_xyz_base_relative_safe_norm.yaml",
            "outputs/checkpoints/b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt",
            "best validation MSE",
        ),
        _candidate(
            "dp30_seed86_baseline_best",
            "DP seed86 baseline",
            "DP",
            "config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86.yaml",
            "outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86/best.pt",
            "best denoising val loss",
            sampling_mode="zero",
            num_inference_steps=50,
            seed=86,
        ),
        _candidate(
            "dp30_seed86_x0aux_dimw_best_action",
            "DP x0-aux per-dim best action",
            "DP",
            "config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86_x0aux0p1_dimw025_1_1.yaml",
            "outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86_x0aux0p1_dimw025_1_1/best_action.pt",
            "best action MSE checkpoint",
            sampling_mode="zero",
            num_inference_steps=50,
            seed=86,
        ),
        _candidate(
            "fm10_zero",
            "FM epoch10 zero-init",
            "FM",
            "config/train_flow_matching_b8_primary30_h8_xyz_base_relative_safe_norm_smoke.yaml",
            "outputs/checkpoints/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_smoke/best.pt",
            "best flow val loss",
            sampling_mode="zero",
            ode_steps=50,
            seed=93,
        ),
        _candidate(
            "fm30_action_select_best_loss",
            "FM epoch30 action-select best loss",
            "FM",
            "config/train_flow_matching_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_action_select.yaml",
            "outputs/checkpoints/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_epoch30_action_select/best.pt",
            "best flow val loss",
            sampling_mode="zero",
            ode_steps=50,
            seed=94,
        ),
        _candidate(
            "fm30_action_select_best_action",
            "FM epoch30 action-select best action",
            "FM",
            "config/train_flow_matching_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_action_select.yaml",
            "outputs/checkpoints/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_epoch30_action_select/best_action.pt",
            "best action MSE checkpoint",
            sampling_mode="zero",
            ode_steps=50,
            seed=94,
        ),
    ]

    device = choose_device(args.device)
    rows = []
    for candidate in candidates:
        meta = _checkpoint_meta(Path(candidate["checkpoint"]))
        row = _predict_candidate(candidate, args.split, device)
        row.update(meta)
        row["family"] = candidate["family"]
        row["selection"] = candidate["selection"]
        rows.append(row)

    bc_mse = float(next(row for row in rows if row["key"] == "bc_ref")["action_mse"])
    for row in rows:
        row["relative_to_bc"] = _relative(float(row["action_mse"]), bc_mse)
        if row["key"] == "bc_ref":
            row["presentation_note"] = "live-smoke reference; not grasp"
        elif row["family"] == "DP":
            row["presentation_note"] = "offline DP only; no live"
        elif row["key"] == "fm30_action_select_best_action":
            row["presentation_note"] = "best offline action MSE; epoch-1 checkpoint"
        else:
            row["presentation_note"] = "offline FM only; no live"

    ranked = sorted(rows, key=lambda row: float(row["action_mse"]))
    for idx, row in enumerate(ranked, start=1):
        row["rank"] = idx

    payload = {
        "artifact": "dp_fm_final_presentation_results",
        "offline_only": True,
        "split": args.split,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "hand_controller_started": False,
        "learned_rollout_run": False,
        "grasp_success_claimed": False,
        "learned_rollout_success_claimed": False,
        "ranked_candidates": ranked,
        "decision": _decision(rows),
    }

    safe = _json_safe(payload)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_csv(safe["ranked_candidates"], args.output_csv)
    _write_md(safe, args.output_md)
    print(json.dumps(safe["decision"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
