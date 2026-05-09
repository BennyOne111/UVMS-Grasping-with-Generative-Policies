#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List, Mapping

import numpy as np
import torch
from torch.utils.data import DataLoader


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from analyze_b8_dp_fm_validation_windows import (  # noqa: E402
    _json_safe,
    _load_dataset,
    _load_diffusion_model,
    _unnormalize_actions,
)
from learning.train.train_bc import choose_device  # noqa: E402


def _masked_mean_square(values: torch.Tensor, mask: torch.Tensor) -> float:
    expanded = mask.unsqueeze(-1)
    weighted = values.pow(2) * expanded
    denom = expanded.sum() * values.shape[-1]
    return float((weighted.sum() / denom.clamp_min(1.0)).item())


@torch.no_grad()
def _diagnose_timestep(model, loader, stats, device, timestep: int, seed: int) -> Dict[str, object]:
    generator = torch.Generator(device=device)
    generator.manual_seed(int(seed) + int(timestep) * 1009)

    eps_losses: List[float] = []
    x0_norm_losses: List[float] = []
    valid_weights: List[float] = []
    pred_chunks = []
    target_chunks = []
    mask_chunks = []

    for batch in loader:
        obs = batch["obs"].to(device)
        action = batch["action"].to(device)
        mask = batch["action_mask"].to(device)
        t = torch.full((action.shape[0],), int(timestep), device=device, dtype=torch.long)
        noise = torch.randn(action.shape, device=device, dtype=action.dtype, generator=generator)
        noisy = model.q_sample(action, t, noise)
        pred_noise = model.predict_noise(noisy, t, obs)
        eps_losses.append(_masked_mean_square(pred_noise - noise, mask) * float(mask.sum().item()))

        scale_clean = model.sqrt_alphas_cumprod[t].view(-1, 1, 1)
        scale_noise = model.sqrt_one_minus_alphas_cumprod[t].view(-1, 1, 1)
        pred_x0 = (noisy - scale_noise * pred_noise) / scale_clean.clamp_min(1e-12)
        x0_norm_losses.append(_masked_mean_square(pred_x0 - action, mask) * float(mask.sum().item()))
        valid_weights.append(float(mask.sum().item()))

        pred_chunks.append(pred_x0.cpu().numpy())
        target_chunks.append(action.cpu().numpy())
        mask_chunks.append(mask.cpu().numpy().astype(bool))

    pred_norm = np.concatenate(pred_chunks, axis=0)
    target_norm = np.concatenate(target_chunks, axis=0)
    mask = np.concatenate(mask_chunks, axis=0).astype(bool)
    pred = _unnormalize_actions(pred_norm, stats)
    target = _unnormalize_actions(target_norm, stats)
    valid_error = pred[mask] - target[mask]

    pred_valid = pred[mask]
    target_valid = target[mask]
    pred_norms = np.linalg.norm(pred_valid, axis=1)
    target_norms = np.linalg.norm(target_valid, axis=1)
    cosine = np.sum(pred_valid * target_valid, axis=1) / np.maximum(pred_norms * target_norms, 1e-12)
    total_weight = max(float(sum(valid_weights)), 1.0)
    return {
        "timestep": int(timestep),
        "alpha_cumprod": float(model.alphas_cumprod[int(timestep)].detach().cpu().item()),
        "epsilon_mse_norm": float(sum(eps_losses) / total_weight),
        "x0_mse_norm": float(sum(x0_norm_losses) / total_weight),
        "x0_action_mse": float(np.mean(valid_error**2)),
        "x0_per_dim_action_mse": np.mean(valid_error**2, axis=0).tolist(),
        "x0_pred_absmax": float(np.max(np.abs(pred_valid))),
        "x0_pred_p95_absmax": float(np.percentile(np.max(np.abs(pred_valid), axis=1), 95)),
        "cosine_mean": float(np.mean(cosine)),
        "valid_action_steps": int(mask.sum()),
    }


def _decision(rows: List[Mapping[str, object]], bc_action_mse: float) -> Dict[str, object]:
    best = min(rows, key=lambda row: float(row["x0_action_mse"]))
    worst = max(rows, key=lambda row: float(row["x0_action_mse"]))
    best_mse = float(best["x0_action_mse"])
    worst_mse = float(worst["x0_action_mse"])
    return {
        "best_timestep": int(best["timestep"]),
        "best_timestep_action_mse": best_mse,
        "best_timestep_relative_to_bc": (best_mse - bc_action_mse) / max(bc_action_mse, 1e-12),
        "worst_timestep": int(worst["timestep"]),
        "worst_timestep_action_mse": worst_mse,
        "x0_error_range_ratio": worst_mse / max(best_mse, 1e-12),
        "one_step_x0_diagnostic_not_policy_candidate": True,
        "bc_reference_not_displaced_by_this_diagnostic": True,
        "epsilon_objective_needs_action_metric_selection": True,
        "objective_ablation_recommended": True,
        "dp_fm_live_approved": False,
        "training_started": False,
        "next_allowed": "offline-only objective ablation design; no live",
    }


def _write_md(payload: Mapping[str, object], path: Path) -> None:
    decision = payload["decision"]
    lines = [
        "# B8 DP Objective Timestep Diagnostic",
        "",
        "Offline-only diagnostic for the current best DP checkpoint. It evaluates",
        "one-step x0/action reconstruction quality at fixed diffusion timesteps.",
        "No ROS, no live execution, no gripper command, and no training are run.",
        "",
        "## Decision",
        "",
        "```text",
        f"bc_reference_not_displaced_by_this_diagnostic={decision['bc_reference_not_displaced_by_this_diagnostic']}",
        f"one_step_x0_diagnostic_not_policy_candidate={decision['one_step_x0_diagnostic_not_policy_candidate']}",
        f"best_timestep={decision['best_timestep']}",
        f"best_timestep_relative_to_bc={decision['best_timestep_relative_to_bc']}",
        f"x0_error_range_ratio={decision['x0_error_range_ratio']}",
        f"objective_ablation_recommended={decision['objective_ablation_recommended']}",
        "dp_fm_live_approved=false",
        "training_started=false",
        "```",
        "",
        "## Timestep Metrics",
        "",
        "| timestep | alpha_cumprod | epsilon MSE norm | x0 MSE norm | x0 action MSE | pred absmax | cosine mean |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["timesteps"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["timestep"]),
                    str(row["alpha_cumprod"]),
                    str(row["epsilon_mse_norm"]),
                    str(row["x0_mse_norm"]),
                    str(row["x0_action_mse"]),
                    str(row["x0_pred_absmax"]),
                    str(row["cosine_mean"]),
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
            "- This diagnostic supports objective/selection work only; it does not",
            "  claim grasp success, learned rollout success, or general rollout success.",
            "- Continue selecting candidates by unnormalized action-window metrics",
            "  against BC.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline DP objective timestep diagnostic.")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--split", default="val", choices=["train", "val"])
    parser.add_argument("--seed", type=int, default=86)
    parser.add_argument("--timesteps", type=int, nargs="+", default=[0, 1, 2, 5, 10, 20, 35, 49])
    parser.add_argument(
        "--config",
        type=Path,
        default=PACKAGE_ROOT / "config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86.yaml",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86/best.pt",
    )
    parser.add_argument(
        "--bc-action-mse",
        type=float,
        default=3.066821534503106e-07,
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp_objective_timestep_diagnostic.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp_objective_timestep_diagnostic.md",
    )
    args = parser.parse_args()

    device = choose_device(args.device)
    cfg, dataset, stats = _load_dataset(args.config, args.checkpoint, args.split)
    loader = DataLoader(
        dataset,
        batch_size=int((cfg.get("train", {}) or {}).get("batch_size", 32)),
        shuffle=False,
    )
    model, _ = _load_diffusion_model(args.checkpoint, device)
    rows = [_diagnose_timestep(model, loader, stats, device, timestep, args.seed) for timestep in args.timesteps]
    payload = {
        "artifact": "dp_objective_timestep_diagnostic",
        "offline_only": True,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "hand_controller_started": False,
        "training_started": False,
        "learned_rollout_run": False,
        "learned_rollout_success_claimed": False,
        "grasp_success_claimed": False,
        "checkpoint": str(args.checkpoint.relative_to(PACKAGE_ROOT)),
        "config": str(args.config.relative_to(PACKAGE_ROOT)),
        "split": args.split,
        "bc_action_mse_reference": float(args.bc_action_mse),
        "timesteps": rows,
        "decision": _decision(rows, float(args.bc_action_mse)),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    safe = _json_safe(payload)
    args.output_json.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(safe, args.output_md)
    print(json.dumps(safe["decision"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
