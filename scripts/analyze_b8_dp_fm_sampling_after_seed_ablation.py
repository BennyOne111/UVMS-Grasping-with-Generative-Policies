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


def _dp_candidate(seed: int, steps: int) -> Mapping[str, object]:
    suffix = "" if seed == 84 else f"_seed{seed}"
    return {
        "key": f"dp30_seed{seed}_zero_steps{steps}",
        "name": f"Diffusion seed{seed} zero-init steps{steps}",
        "policy_type": "diffusion",
        "sampling_mode": "zero",
        "num_inference_steps": steps,
        "seed": seed,
        "config": PACKAGE_ROOT / f"config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30{suffix}.yaml",
        "checkpoint": PACKAGE_ROOT
        / f"outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30{suffix}/best.pt",
    }


def _fm_candidate(steps: int) -> Mapping[str, object]:
    return {
        "key": f"fm10_zero_steps{steps}",
        "name": f"Flow Matching smoke zero-init steps{steps}",
        "policy_type": "flow_matching",
        "sampling_mode": "zero",
        "ode_steps": steps,
        "seed": 93,
        "config": PACKAGE_ROOT / "config/train_flow_matching_b8_primary30_h8_xyz_base_relative_safe_norm_smoke.yaml",
        "checkpoint": PACKAGE_ROOT
        / "outputs/checkpoints/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_smoke/best.pt",
    }


def _decision(rows):
    by_key = {row["key"]: row for row in rows}
    bc = by_key["bc_ref"]
    bc_mse = float(bc["action_mse"])
    non_bc = [row for row in rows if row["key"] != "bc_ref"]
    best = min(non_bc, key=lambda row: float(row["action_mse"]))
    dp86_rows = [row for row in rows if str(row["key"]).startswith("dp30_seed86")]
    best_dp86 = min(dp86_rows, key=lambda row: float(row["action_mse"]))
    return {
        "bc_remains_reference": bool(bc_mse <= float(best["action_mse"])),
        "best_non_bc": best["key"],
        "best_non_bc_action_mse": float(best["action_mse"]),
        "best_non_bc_relative_to_bc": (float(best["action_mse"]) - bc_mse) / max(bc_mse, 1e-12),
        "best_dp86": best_dp86["key"],
        "best_dp86_action_mse": float(best_dp86["action_mse"]),
        "best_dp86_relative_to_bc": (float(best_dp86["action_mse"]) - bc_mse) / max(bc_mse, 1e-12),
        "sampling_steps_close_gap": bool(float(best_dp86["action_mse"]) < float(by_key["dp30_seed86_zero_steps50"]["action_mse"])),
        "dp_fm_live_approved": False,
        "training_started": False,
        "next_allowed": "offline-only DP/FM architecture/objective diagnostics; no live",
    }


def _write_md(payload: Mapping[str, object], path: Path) -> None:
    decision = payload["decision"]
    lines = [
        "# B8 DP/FM Sampling After Seed Ablation",
        "",
        "Offline-only sampling sensitivity after the DP30 seed ablation. This",
        "uses the same base-relative safe-norm h8 xyz setup and does not train,",
        "start ROS, or run learned rollout.",
        "",
        "## Decision",
        "",
        "```text",
        f"bc_remains_reference={decision['bc_remains_reference']}",
        f"best_non_bc={decision['best_non_bc']}",
        f"best_non_bc_relative_to_bc={decision['best_non_bc_relative_to_bc']}",
        f"best_dp86={decision['best_dp86']}",
        f"sampling_steps_close_gap={decision['sampling_steps_close_gap']}",
        "dp_fm_live_approved=false",
        "training_started=false",
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
            "- No grasp success, learned rollout success, or general rollout success",
            "  is claimed.",
            "- If DP/FM continues, use offline architecture/objective diagnostics",
            "  rather than changing live execution.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline-only DP/FM sampling sweep after DP seed ablation.")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--split", default="val", choices=["train", "val"])
    parser.add_argument("--dp86-steps", type=int, nargs="+", default=[10, 25, 50, 100, 200])
    parser.add_argument("--fm-steps", type=int, nargs="+", default=[50, 100])
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_primary30_training_planning/dp_fm_sampling_after_seed_ablation.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_primary30_training_planning/dp_fm_sampling_after_seed_ablation.md",
    )
    args = parser.parse_args()

    candidates = [_bc_candidate(), _dp_candidate(84, 50)]
    candidates.extend(_dp_candidate(86, steps) for steps in args.dp86_steps)
    candidates.extend(_fm_candidate(steps) for steps in args.fm_steps)

    device = choose_device(args.device)
    rows = [_predict_candidate(candidate, args.split, device) for candidate in candidates]
    payload = {
        "artifact": "dp_fm_sampling_after_seed_ablation",
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
