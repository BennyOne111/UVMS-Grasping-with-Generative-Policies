#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List, Mapping, Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader
import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from learning.datasets.uvms_episode_dataset import UVMSEpisodeDataset, load_stats  # noqa: E402
from learning.models.bc_policy import BCMLPPolicy  # noqa: E402
from learning.models.diffusion_policy import DiffusionPolicy  # noqa: E402
from learning.models.flow_matching_policy import FlowMatchingPolicy  # noqa: E402
from learning.train.train_bc import choose_device  # noqa: E402


def _masked_mse(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    expanded = mask.unsqueeze(-1)
    sq = (pred - target) ** 2 * expanded
    return sq.sum() / expanded.sum().clamp_min(1.0)


def _load_checkpoint(path: Path, device: torch.device) -> Dict[str, object]:
    return torch.load(str(path.expanduser()), map_location=device)


def _load_bc_model(path: Path, device: torch.device) -> Tuple[BCMLPPolicy, Dict[str, object]]:
    checkpoint = _load_checkpoint(path, device)
    model_cfg = (checkpoint["config"].get("model", {}) or {})
    model = BCMLPPolicy(
        obs_dim=int(checkpoint["obs_dim"]),
        action_dim=int(checkpoint["action_dim"]),
        obs_horizon=int(checkpoint["obs_horizon"]),
        action_horizon=int(checkpoint["action_horizon"]),
        hidden_dims=model_cfg.get("hidden_dims", [128, 128]),
        dropout=float(model_cfg.get("dropout", 0.0)),
        activation=str(model_cfg.get("activation", "relu")),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, checkpoint


def _load_diffusion_model(path: Path, device: torch.device) -> Tuple[DiffusionPolicy, Dict[str, object]]:
    checkpoint = _load_checkpoint(path, device)
    model_cfg = (checkpoint["config"].get("model", {}) or {})
    model = DiffusionPolicy(
        obs_dim=int(checkpoint["obs_dim"]),
        action_dim=int(checkpoint["action_dim"]),
        obs_horizon=int(checkpoint["obs_horizon"]),
        action_horizon=int(checkpoint["action_horizon"]),
        num_diffusion_steps=int(model_cfg.get("num_diffusion_steps", checkpoint.get("num_diffusion_steps", 50))),
        beta_start=float(model_cfg.get("beta_start", 1e-4)),
        beta_end=float(model_cfg.get("beta_end", 0.02)),
        hidden_dims=model_cfg.get("hidden_dims", [256, 256, 256]),
        time_embed_dim=int(model_cfg.get("time_embed_dim", 64)),
        dropout=float(model_cfg.get("dropout", 0.0)),
        activation=str(model_cfg.get("activation", "silu")),
        prediction_type=str(model_cfg.get("prediction_type", "epsilon")),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, checkpoint


def _load_flow_matching_model(path: Path, device: torch.device) -> Tuple[FlowMatchingPolicy, Dict[str, object]]:
    checkpoint = _load_checkpoint(path, device)
    model_cfg = (checkpoint["config"].get("model", {}) or {})
    model = FlowMatchingPolicy(
        obs_dim=int(checkpoint["obs_dim"]),
        action_dim=int(checkpoint["action_dim"]),
        obs_horizon=int(checkpoint["obs_horizon"]),
        action_horizon=int(checkpoint["action_horizon"]),
        hidden_dims=model_cfg.get("hidden_dims", [256, 256, 256]),
        time_embed_dim=int(model_cfg.get("time_embed_dim", 64)),
        time_scale=float(model_cfg.get("time_scale", 1000.0)),
        dropout=float(model_cfg.get("dropout", 0.0)),
        activation=str(model_cfg.get("activation", "silu")),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, checkpoint


@torch.no_grad()
def _collect_bc_predictions(model, loader, device):
    losses = []
    weights = []
    pred_chunks = []
    target_chunks = []
    mask_chunks = []
    for batch in loader:
        obs = batch["obs"].to(device)
        action = batch["action"].to(device)
        mask = batch["action_mask"].to(device)
        pred = model(obs)
        loss = _masked_mse(pred, action, mask)
        losses.append(float(loss.item()) * float(mask.sum().item()))
        weights.append(float(mask.sum().item()))
        pred_chunks.append(pred.cpu().numpy())
        target_chunks.append(action.cpu().numpy())
        mask_chunks.append(mask.cpu().numpy())
    return (
        float(sum(losses) / max(sum(weights), 1.0)),
        np.concatenate(pred_chunks, axis=0),
        np.concatenate(target_chunks, axis=0),
        np.concatenate(mask_chunks, axis=0).astype(bool),
    )


@torch.no_grad()
def _collect_diffusion_predictions(model, loader, device, num_inference_steps: int, sampling_mode: str):
    losses = []
    weights = []
    pred_chunks = []
    target_chunks = []
    mask_chunks = []
    for batch in loader:
        obs = batch["obs"].to(device)
        action = batch["action"].to(device)
        mask = batch["action_mask"].to(device)
        if sampling_mode == "zero":
            initial_action = torch.zeros((obs.shape[0], model.action_horizon, model.action_dim), device=device, dtype=obs.dtype)
            pred = model.sample(
                obs,
                num_inference_steps=num_inference_steps,
                initial_action=initial_action,
                deterministic_reverse=True,
            )
        else:
            pred = model.sample(obs, num_inference_steps=num_inference_steps)
        loss = _masked_mse(pred, action, mask)
        losses.append(float(loss.item()) * float(mask.sum().item()))
        weights.append(float(mask.sum().item()))
        pred_chunks.append(pred.cpu().numpy())
        target_chunks.append(action.cpu().numpy())
        mask_chunks.append(mask.cpu().numpy())
    return (
        float(sum(losses) / max(sum(weights), 1.0)),
        np.concatenate(pred_chunks, axis=0),
        np.concatenate(target_chunks, axis=0),
        np.concatenate(mask_chunks, axis=0).astype(bool),
    )


@torch.no_grad()
def _collect_flow_matching_predictions(model, loader, device, ode_steps: int, sampling_mode: str):
    losses = []
    weights = []
    pred_chunks = []
    target_chunks = []
    mask_chunks = []
    for batch in loader:
        obs = batch["obs"].to(device)
        action = batch["action"].to(device)
        mask = batch["action_mask"].to(device)
        if sampling_mode == "zero":
            initial_action = torch.zeros((obs.shape[0], model.action_horizon, model.action_dim), device=device, dtype=obs.dtype)
            pred = model.sample(obs, ode_steps=ode_steps, initial_action=initial_action)
        else:
            pred = model.sample(obs, ode_steps=ode_steps)
        loss = _masked_mse(pred, action, mask)
        losses.append(float(loss.item()) * float(mask.sum().item()))
        weights.append(float(mask.sum().item()))
        pred_chunks.append(pred.cpu().numpy())
        target_chunks.append(action.cpu().numpy())
        mask_chunks.append(mask.cpu().numpy())
    return (
        float(sum(losses) / max(sum(weights), 1.0)),
        np.concatenate(pred_chunks, axis=0),
        np.concatenate(target_chunks, axis=0),
        np.concatenate(mask_chunks, axis=0).astype(bool),
    )


def _unnormalize_actions(values: np.ndarray, stats) -> np.ndarray:
    return values * stats.action_std.reshape(1, 1, -1) + stats.action_mean.reshape(1, 1, -1)


def _load_yaml(path: Path) -> Dict[str, object]:
    with path.expanduser().open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _json_safe(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _load_dataset(config_path: Path, checkpoint_path: Path, split: str) -> Tuple[Dict[str, object], UVMSEpisodeDataset, object]:
    cfg = _load_yaml(config_path)
    checkpoint = torch.load(str(checkpoint_path.expanduser()), map_location="cpu")
    stats = load_stats(str(checkpoint["stats_path"]))
    dataset = UVMSEpisodeDataset.from_config(cfg["dataset"], split=split, stats=stats)
    return cfg, dataset, stats


def _window_metadata(dataset: UVMSEpisodeDataset) -> List[Dict[str, object]]:
    rows = []
    for episode_idx, end_idx in dataset.index:
        episode = dataset.episodes[episode_idx]
        rows.append(
            {
                "episode_path": str(episode["path"]),
                "episode_name": Path(str(episode["path"])).stem,
                "end_idx": int(end_idx),
            }
        )
    return rows


def _predict_candidate(candidate: Mapping[str, object], split: str, device: torch.device) -> Dict[str, object]:
    cfg, dataset, stats = _load_dataset(Path(candidate["config"]), Path(candidate["checkpoint"]), split)
    loader = DataLoader(
        dataset,
        batch_size=int((cfg.get("train", {}) or {}).get("batch_size", 32)),
        shuffle=False,
    )
    policy_type = str(candidate["policy_type"])
    checkpoint_path = str(candidate["checkpoint"])
    if policy_type == "bc":
        model, _ = _load_bc_model(Path(checkpoint_path), device)
        norm_mse, pred_norm, target_norm, mask = _collect_bc_predictions(model, loader, device)
    elif policy_type == "diffusion":
        model, _ = _load_diffusion_model(Path(checkpoint_path), device)
        torch.manual_seed(int(candidate.get("seed", 0)))
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(int(candidate.get("seed", 0)))
        norm_mse, pred_norm, target_norm, mask = _collect_diffusion_predictions(
            model,
            loader,
            device,
            num_inference_steps=int(candidate.get("num_inference_steps", 50)),
            sampling_mode=str(candidate.get("sampling_mode", "zero")),
        )
    elif policy_type == "flow_matching":
        model, _ = _load_flow_matching_model(Path(checkpoint_path), device)
        torch.manual_seed(int(candidate.get("seed", 0)))
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(int(candidate.get("seed", 0)))
        norm_mse, pred_norm, target_norm, mask = _collect_flow_matching_predictions(
            model,
            loader,
            device,
            ode_steps=int(candidate.get("ode_steps", 50)),
            sampling_mode=str(candidate.get("sampling_mode", "zero")),
        )
    else:
        raise ValueError(f"unsupported policy type: {policy_type}")

    pred = _unnormalize_actions(pred_norm, stats)
    target = _unnormalize_actions(target_norm, stats)
    mask_bool = mask.astype(bool)
    error = pred - target
    valid_error = error[mask_bool]
    action_mse = float(np.mean(valid_error**2))
    per_dim_mse = np.mean(valid_error**2, axis=0)

    # Per-window MSE uses only valid action steps for each window.
    per_window_mse = []
    first_step_mse = []
    for idx in range(pred.shape[0]):
        valid = mask_bool[idx]
        per_window_mse.append(float(np.mean((pred[idx][valid] - target[idx][valid]) ** 2)))
        first_step_mse.append(float(np.mean((pred[idx, 0] - target[idx, 0]) ** 2)))
    per_window_mse_arr = np.asarray(per_window_mse, dtype=np.float64)
    first_step_mse_arr = np.asarray(first_step_mse, dtype=np.float64)

    pred_valid = pred[mask_bool]
    target_valid = target[mask_bool]
    pred_norms = np.linalg.norm(pred_valid, axis=1)
    target_norms = np.linalg.norm(target_valid, axis=1)
    cosine = np.sum(pred_valid * target_valid, axis=1) / np.maximum(pred_norms * target_norms, 1e-12)

    metadata = _window_metadata(dataset)
    episode_groups: Dict[str, List[int]] = {}
    for idx, row in enumerate(metadata):
        episode_groups.setdefault(str(row["episode_name"]), []).append(idx)
    episode_rows = []
    for episode_name, indices in sorted(episode_groups.items()):
        vals = per_window_mse_arr[indices]
        episode_rows.append(
            {
                "episode_name": episode_name,
                "window_count": len(indices),
                "mean_window_mse": float(np.mean(vals)),
                "max_window_mse": float(np.max(vals)),
            }
        )

    worst_indices = np.argsort(per_window_mse_arr)[-10:][::-1]
    worst_windows = []
    for idx in worst_indices:
        row = dict(metadata[int(idx)])
        row.update(
            {
                "window_mse": float(per_window_mse_arr[int(idx)]),
                "first_step_mse": float(first_step_mse_arr[int(idx)]),
                "target_first": target[int(idx), 0].tolist(),
                "pred_first": pred[int(idx), 0].tolist(),
            }
        )
        worst_windows.append(row)

    return {
        "candidate": str(candidate["name"]),
        "key": str(candidate["key"]),
        "policy_type": policy_type,
        "checkpoint": str(candidate["checkpoint"]),
        "config": str(candidate["config"]),
        "split": split,
        "samples": int(pred.shape[0]),
        "valid_action_steps": int(mask_bool.sum()),
        "normalized_mse": float(norm_mse),
        "action_mse": action_mse,
        "first_step_mse_mean": float(np.mean(first_step_mse_arr)),
        "per_dim_action_mse": per_dim_mse.tolist(),
        "per_step_action_mse": np.mean(error**2, axis=(0, 2)).tolist(),
        "per_window_mse": {
            "mean": float(np.mean(per_window_mse_arr)),
            "p50": float(np.percentile(per_window_mse_arr, 50)),
            "p90": float(np.percentile(per_window_mse_arr, 90)),
            "p95": float(np.percentile(per_window_mse_arr, 95)),
            "max": float(np.max(per_window_mse_arr)),
        },
        "action_scale": {
            "pred_valid_absmax": float(np.max(np.abs(pred_valid))),
            "pred_valid_p95_absmax": float(np.percentile(np.max(np.abs(pred_valid), axis=1), 95)),
            "target_valid_absmax": float(np.max(np.abs(target_valid))),
            "target_valid_p95_absmax": float(np.percentile(np.max(np.abs(target_valid), axis=1), 95)),
            "pred_norm_mean": float(np.mean(pred_norms)),
            "target_norm_mean": float(np.mean(target_norms)),
            "cosine_mean": float(np.mean(cosine)),
            "cosine_p10": float(np.percentile(cosine, 10)),
        },
        "worst_windows": worst_windows,
        "episode_rows": episode_rows,
    }


def _decision(rows: List[Mapping[str, object]]) -> Dict[str, object]:
    by_key = {str(row["key"]): row for row in rows}
    bc = by_key["bc_ref"]
    dp = by_key["dp30_zero"]
    fm = by_key["fm10_zero"]
    bc_action = float(bc["action_mse"])
    best_non_bc = min([dp, fm], key=lambda row: float(row["action_mse"]))
    return {
        "bc_remains_reference": bool(bc_action < float(best_non_bc["action_mse"])),
        "best_non_bc": best_non_bc["key"],
        "best_non_bc_action_mse": float(best_non_bc["action_mse"]),
        "bc_action_mse": bc_action,
        "dp30_action_mse_relative_to_bc": (float(dp["action_mse"]) - bc_action) / max(bc_action, 1e-12),
        "fm10_action_mse_relative_to_bc": (float(fm["action_mse"]) - bc_action) / max(bc_action, 1e-12),
        "dp_fm_live_approved": False,
        "training_started": False,
        "next_allowed": "offline-only DP/FM seed/budget or architecture diagnostics; no live",
    }


def _write_md(payload: Mapping[str, object], path: Path) -> None:
    decision = payload["decision"]
    lines = [
        "# B8 DP/FM Validation-Window Diagnostics",
        "",
        "Offline-only validation diagnostics for BC, DP30 zero, and FM10 zero under",
        "the same base-relative safe-norm xyz h8 setup. No ROS, no live commands,",
        "no gripper, and no training are used.",
        "",
        "## Decision",
        "",
        "```text",
        f"bc_remains_reference={decision['bc_remains_reference']}",
        f"best_non_bc={decision['best_non_bc']}",
        f"dp30_action_mse_relative_to_bc={decision['dp30_action_mse_relative_to_bc']}",
        f"fm10_action_mse_relative_to_bc={decision['fm10_action_mse_relative_to_bc']}",
        "dp_fm_live_approved=false",
        "training_started=false",
        "```",
        "",
        "## Candidate Metrics",
        "",
        "| candidate | action MSE | first-step MSE | p95 window MSE | max window MSE | pred absmax | cosine mean |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
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
                    str(row["action_scale"]["cosine_mean"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- DP/FM can continue offline-only.",
            "- DP/FM live remains blocked.",
            "- No full training-as-success evidence is approved.",
            "- No grasp or general learned rollout success is claimed.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline-only DP/FM validation-window diagnostics.")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--split", default="val", choices=["train", "val"])
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_primary30_training_planning/dp_fm_validation_window_diagnostics.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT
        / "outputs/logs/b8_primary30_training_planning/dp_fm_validation_window_diagnostics.md",
    )
    args = parser.parse_args()

    candidates = [
        {
            "key": "bc_ref",
            "name": "BC direct base-relative safe-norm",
            "policy_type": "bc",
            "config": PACKAGE_ROOT / "config/train_bc_b8_primary30_h8_xyz_base_relative_safe_norm.yaml",
            "checkpoint": PACKAGE_ROOT / "outputs/checkpoints/b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt",
        },
        {
            "key": "dp30_zero",
            "name": "Diffusion zero epoch30",
            "policy_type": "diffusion",
            "sampling_mode": "zero",
            "num_inference_steps": 50,
            "seed": 84,
            "config": PACKAGE_ROOT / "config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30.yaml",
            "checkpoint": PACKAGE_ROOT
            / "outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30/best.pt",
        },
        {
            "key": "fm10_zero",
            "name": "Flow Matching zero epoch10",
            "policy_type": "flow_matching",
            "sampling_mode": "zero",
            "ode_steps": 50,
            "seed": 93,
            "config": PACKAGE_ROOT / "config/train_flow_matching_b8_primary30_h8_xyz_base_relative_safe_norm_smoke.yaml",
            "checkpoint": PACKAGE_ROOT
            / "outputs/checkpoints/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_smoke/best.pt",
        },
    ]

    device = choose_device(args.device)
    rows = [_predict_candidate(candidate, args.split, device) for candidate in candidates]
    payload = {
        "artifact": "dp_fm_validation_window_diagnostics",
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
    args.output_json.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(_json_safe(payload), args.output_md)
    print(json.dumps(_json_safe(payload["decision"]), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
