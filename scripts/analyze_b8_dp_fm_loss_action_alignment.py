#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Dict, List, Mapping

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    return str(path.relative_to(PACKAGE_ROOT))


def _summary_path(kind: str, name: str) -> Path:
    return PACKAGE_ROOT / "outputs/logs" / name / "train_summary.json"


def _validation_rows(path: Path) -> Dict[str, Mapping[str, object]]:
    data = _load_json(path)
    return {str(row["key"]): row for row in data.get("candidates", [])}


def _candidate_rows(seed_validation: Mapping[str, Mapping[str, object]], sampling: Mapping[str, Mapping[str, object]]) -> List[Dict[str, object]]:
    candidates = [
        {
            "key": "bc_ref",
            "policy_type": "bc",
            "train_summary": _summary_path("bc", "b8_primary30_bc_h8_xyz_base_relative_safe_norm"),
            "validation_key": "bc_ref",
            "source": seed_validation,
        },
        {
            "key": "dp30_seed84",
            "policy_type": "diffusion",
            "train_summary": _summary_path("diffusion", "b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30"),
            "validation_key": "dp30_seed84_zero",
            "source": seed_validation,
        },
        {
            "key": "dp30_seed85",
            "policy_type": "diffusion",
            "train_summary": _summary_path("diffusion", "b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed85"),
            "validation_key": "dp30_seed85_zero",
            "source": seed_validation,
        },
        {
            "key": "dp30_seed86",
            "policy_type": "diffusion",
            "train_summary": _summary_path("diffusion", "b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86"),
            "validation_key": "dp30_seed86_zero_steps50",
            "source": sampling,
        },
        {
            "key": "fm10",
            "policy_type": "flow_matching",
            "train_summary": _summary_path("flow_matching", "b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_smoke"),
            "validation_key": "fm10_zero_steps50",
            "source": sampling,
        },
        {
            "key": "fm30",
            "policy_type": "flow_matching",
            "train_summary": _summary_path("flow_matching", "b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_epoch30"),
            "validation_key": None,
            "source": {},
        },
    ]

    rows = []
    for candidate in candidates:
        summary_path = Path(candidate["train_summary"])
        summary = _load_json(summary_path) if summary_path.exists() else {}
        validation = {}
        if candidate["validation_key"] is not None:
            validation = candidate["source"].get(str(candidate["validation_key"]), {}) or {}
        history = summary.get("history", []) or []
        val_losses = [float(row["val_loss"]) for row in history if "val_loss" in row]
        train_losses = [float(row["train_loss"]) for row in history if "train_loss" in row]
        best_epoch = None
        if val_losses:
            best_idx = int(np.argmin(np.asarray(val_losses)))
            best_epoch = int(history[best_idx].get("epoch", best_idx + 1))
        rows.append(
            {
                "key": candidate["key"],
                "policy_type": candidate["policy_type"],
                "train_summary": _rel(summary_path),
                "epochs": int(summary.get("epochs", 0)) if summary else None,
                "best_epoch": best_epoch,
                "best_val_loss": float(summary["best_val_loss"]) if "best_val_loss" in summary else None,
                "final_val_loss": float(summary["final_val_loss"]) if "final_val_loss" in summary else None,
                "final_train_loss": float(summary["final_train_loss"]) if "final_train_loss" in summary else None,
                "val_loss_improved": bool(val_losses[-1] < val_losses[0]) if len(val_losses) >= 2 else None,
                "final_over_best_val_loss": (
                    float(summary["final_val_loss"]) / max(float(summary["best_val_loss"]), 1e-12)
                    if "final_val_loss" in summary and "best_val_loss" in summary
                    else None
                ),
                "action_mse": float(validation["action_mse"]) if "action_mse" in validation else None,
                "first_step_mse": float(validation["first_step_mse_mean"]) if "first_step_mse_mean" in validation else None,
                "p95_window_mse": float(validation["per_window_mse"]["p95"]) if validation else None,
                "max_window_mse": float(validation["per_window_mse"]["max"]) if validation else None,
            }
        )
    return rows


def _correlation(rows: List[Mapping[str, object]], policy_type: str) -> Dict[str, object]:
    filtered = [
        row
        for row in rows
        if row["policy_type"] == policy_type and row.get("best_val_loss") is not None and row.get("action_mse") is not None
    ]
    if len(filtered) < 2:
        return {"policy_type": policy_type, "sample_count": len(filtered), "pearson_best_val_loss_vs_action_mse": None}
    x = np.asarray([float(row["best_val_loss"]) for row in filtered], dtype=np.float64)
    y = np.asarray([float(row["action_mse"]) for row in filtered], dtype=np.float64)
    if np.std(x) <= 1e-12 or np.std(y) <= 1e-12:
        corr = None
    else:
        corr = float(np.corrcoef(x, y)[0, 1])
    return {
        "policy_type": policy_type,
        "sample_count": len(filtered),
        "pearson_best_val_loss_vs_action_mse": corr,
    }


def _decision(rows: List[Mapping[str, object]]) -> Dict[str, object]:
    bc = next(row for row in rows if row["key"] == "bc_ref")
    scored = [row for row in rows if row.get("action_mse") is not None and row["key"] != "bc_ref"]
    best_non_bc = min(scored, key=lambda row: float(row["action_mse"]))
    dp_rows = [row for row in scored if row["policy_type"] == "diffusion"]
    best_dp = min(dp_rows, key=lambda row: float(row["action_mse"]))
    return {
        "bc_remains_reference": float(bc["action_mse"]) <= float(best_non_bc["action_mse"]),
        "best_non_bc": best_non_bc["key"],
        "best_dp": best_dp["key"],
        "best_dp_relative_to_bc": (float(best_dp["action_mse"]) - float(bc["action_mse"])) / max(float(bc["action_mse"]), 1e-12),
        "loss_metric_sufficient_for_selection": False,
        "sampling_or_seed_not_enough": True,
        "dp_fm_live_approved": False,
        "training_started": False,
        "next_allowed": "offline-only architecture/objective ablation plan; no live",
    }


def _write_md(payload: Mapping[str, object], path: Path) -> None:
    decision = payload["decision"]
    lines = [
        "# B8 DP/FM Loss-Action Alignment",
        "",
        "Offline-only diagnostic comparing training losses against validation action",
        "MSE. No ROS, live execution, gripper command, or training is run by this",
        "script.",
        "",
        "## Decision",
        "",
        "```text",
        f"bc_remains_reference={decision['bc_remains_reference']}",
        f"best_non_bc={decision['best_non_bc']}",
        f"best_dp={decision['best_dp']}",
        f"best_dp_relative_to_bc={decision['best_dp_relative_to_bc']}",
        f"loss_metric_sufficient_for_selection={decision['loss_metric_sufficient_for_selection']}",
        "dp_fm_live_approved=false",
        "training_started=false",
        "```",
        "",
        "## Rows",
        "",
        "| key | type | epochs | best epoch | best val loss | final val loss | action MSE | p95 window MSE | max window MSE |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["key"]),
                    str(row["policy_type"]),
                    str(row["epochs"]),
                    str(row["best_epoch"]),
                    str(row["best_val_loss"]),
                    str(row["final_val_loss"]),
                    str(row["action_mse"]),
                    str(row["p95_window_mse"]),
                    str(row["max_window_mse"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Correlations",
            "",
            "```text",
        ]
    )
    for row in payload["correlations"]:
        lines.append(
            f"{row['policy_type']} sample_count={row['sample_count']} "
            f"pearson={row['pearson_best_val_loss_vs_action_mse']}"
        )
    lines.extend(
        [
            "```",
            "",
            "## Boundary",
            "",
            "- DP/FM live remains blocked.",
            "- Loss alone is not enough to approve DP/FM live.",
            "- Continue only with offline architecture/objective ablations if needed.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline DP/FM training-loss vs action-MSE diagnostic.")
    parser.add_argument(
        "--seed-validation-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.json",
    )
    parser.add_argument(
        "--sampling-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp_fm_sampling_after_seed_ablation.json",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp_fm_loss_action_alignment.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp_fm_loss_action_alignment.md",
    )
    args = parser.parse_args()

    seed_validation = _validation_rows(args.seed_validation_json)
    sampling = _validation_rows(args.sampling_json)
    rows = _candidate_rows(seed_validation, sampling)
    payload = {
        "artifact": "dp_fm_loss_action_alignment",
        "offline_only": True,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "hand_controller_started": False,
        "training_started": False,
        "learned_rollout_run": False,
        "learned_rollout_success_claimed": False,
        "grasp_success_claimed": False,
        "rows": rows,
        "correlations": [_correlation(rows, "diffusion"), _correlation(rows, "flow_matching")],
        "decision": _decision(rows),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(payload, args.output_md)
    print(json.dumps(payload["decision"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
