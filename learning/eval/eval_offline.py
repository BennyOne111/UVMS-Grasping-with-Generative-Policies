#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, Mapping, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from learning.datasets.uvms_episode_dataset import UVMSEpisodeDataset, load_stats  # noqa: E402
from learning.models.bc_policy import BCMLPPolicy  # noqa: E402
from learning.models.diffusion_policy import DiffusionPolicy  # noqa: E402
from learning.models.flow_matching_policy import FlowMatchingPolicy  # noqa: E402
from learning.train.train_bc import choose_device, masked_mse  # noqa: E402


def load_config(path: str) -> Dict[str, object]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_bc_model(checkpoint_path: str, device: torch.device) -> Tuple[BCMLPPolicy, Dict[str, object]]:
    checkpoint = torch.load(str(Path(checkpoint_path).expanduser()), map_location=device)
    cfg = checkpoint["config"]
    model_cfg = cfg.get("model", {}) or {}
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


def load_diffusion_model(checkpoint_path: str, device: torch.device) -> Tuple[DiffusionPolicy, Dict[str, object]]:
    checkpoint = torch.load(str(Path(checkpoint_path).expanduser()), map_location=device)
    cfg = checkpoint["config"]
    model_cfg = cfg.get("model", {}) or {}
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


def load_flow_matching_model(checkpoint_path: str, device: torch.device) -> Tuple[FlowMatchingPolicy, Dict[str, object]]:
    checkpoint = torch.load(str(Path(checkpoint_path).expanduser()), map_location=device)
    cfg = checkpoint["config"]
    model_cfg = cfg.get("model", {}) or {}
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
def collect_bc_predictions(model, loader, device):
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
        loss = masked_mse(pred, action, mask)
        losses.append(float(loss.item()) * float(mask.sum().item()))
        weights.append(float(mask.sum().item()))
        pred_chunks.append(pred.cpu().numpy())
        target_chunks.append(action.cpu().numpy())
        mask_chunks.append(mask.cpu().numpy())
    pred = np.concatenate(pred_chunks, axis=0)
    target = np.concatenate(target_chunks, axis=0)
    mask = np.concatenate(mask_chunks, axis=0).astype(bool)
    mse = float(sum(losses) / max(sum(weights), 1.0))
    return mse, pred, target, mask


@torch.no_grad()
def collect_diffusion_predictions(model, loader, device, num_inference_steps: int, sampling_mode: str):
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
            initial_action = torch.zeros(
                (obs.shape[0], model.action_horizon, model.action_dim),
                device=device,
                dtype=obs.dtype,
            )
            pred = model.sample(
                obs,
                num_inference_steps=num_inference_steps,
                initial_action=initial_action,
                deterministic_reverse=True,
            )
        else:
            pred = model.sample(obs, num_inference_steps=num_inference_steps)
        loss = masked_mse(pred, action, mask)
        losses.append(float(loss.item()) * float(mask.sum().item()))
        weights.append(float(mask.sum().item()))
        pred_chunks.append(pred.cpu().numpy())
        target_chunks.append(action.cpu().numpy())
        mask_chunks.append(mask.cpu().numpy())
    pred = np.concatenate(pred_chunks, axis=0)
    target = np.concatenate(target_chunks, axis=0)
    mask = np.concatenate(mask_chunks, axis=0).astype(bool)
    mse = float(sum(losses) / max(sum(weights), 1.0))
    return mse, pred, target, mask


@torch.no_grad()
def collect_flow_matching_predictions(model, loader, device, ode_steps: int, sampling_mode: str):
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
            initial_action = torch.zeros(
                (obs.shape[0], model.action_horizon, model.action_dim),
                device=device,
                dtype=obs.dtype,
            )
            pred = model.sample(obs, ode_steps=ode_steps, initial_action=initial_action)
        else:
            pred = model.sample(obs, ode_steps=ode_steps)
        loss = masked_mse(pred, action, mask)
        losses.append(float(loss.item()) * float(mask.sum().item()))
        weights.append(float(mask.sum().item()))
        pred_chunks.append(pred.cpu().numpy())
        target_chunks.append(action.cpu().numpy())
        mask_chunks.append(mask.cpu().numpy())
    pred = np.concatenate(pred_chunks, axis=0)
    target = np.concatenate(target_chunks, axis=0)
    mask = np.concatenate(mask_chunks, axis=0).astype(bool)
    mse = float(sum(losses) / max(sum(weights), 1.0))
    return mse, pred, target, mask


def unnormalize_actions(values: np.ndarray, stats) -> np.ndarray:
    return values * stats.action_std.reshape(1, 1, -1) + stats.action_mean.reshape(1, 1, -1)


def plot_pred_vs_target(pred, target, mask, output_path: Path, max_points: int = 300) -> None:
    flat_pred = pred[mask]
    flat_target = target[mask]
    count = min(max_points, flat_pred.shape[0])
    dims = min(flat_pred.shape[1], 7)
    fig, axes = plt.subplots(dims, 1, figsize=(10, 1.8 * dims), sharex=True)
    if dims == 1:
        axes = [axes]
    labels = ["dx", "dy", "dz", "droll", "dpitch", "dyaw", "gripper"]
    x = np.arange(count)
    for dim in range(dims):
        axes[dim].plot(x, flat_target[:count, dim], label="expert", linewidth=1.5)
        axes[dim].plot(x, flat_pred[:count, dim], label="pred", linewidth=1.0, linestyle="--")
        axes[dim].set_ylabel(labels[dim] if dim < len(labels) else f"a{dim}")
        axes[dim].grid(True, alpha=0.3)
    axes[0].legend(loc="upper right")
    axes[-1].set_xlabel("valid action sample")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_path), dpi=150)
    plt.close(fig)


def infer_policy_type(requested: str, checkpoint: Mapping[str, object]) -> str:
    if requested != "auto":
        return requested
    return str(checkpoint.get("policy_type", "bc"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline evaluation for BC, Diffusion, and Flow Matching policies.")
    parser.add_argument(
        "--config",
        default=str(PACKAGE_ROOT / "config" / "train_bc.yaml"),
        help="Training config YAML used to build the dataset.",
    )
    parser.add_argument("--checkpoint", default="", help="Checkpoint path. Defaults to config best.pt.")
    parser.add_argument("--split", default="val", choices=["train", "val", "test"], help="Dataset split.")
    parser.add_argument(
        "--policy-type",
        default="auto",
        choices=["auto", "bc", "diffusion", "flow_matching"],
        help="Policy type.",
    )
    parser.add_argument("--num-inference-steps", type=int, default=None, help="Diffusion denoising steps override.")
    parser.add_argument("--ode-steps", type=int, default=None, help="Flow Matching Euler ODE steps override.")
    parser.add_argument(
        "--sampling-mode",
        default="stochastic",
        choices=["stochastic", "zero"],
        help="Sampling mode for DP/FM. zero uses zero initial action and deterministic DP reverse noise.",
    )
    parser.add_argument(
        "--output-suffix",
        default="",
        help="Optional suffix for output JSON/plot filenames, e.g. '_zero'.",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    outputs = cfg.get("outputs", {}) or {}
    checkpoint_path = args.checkpoint or str(
        Path(str(outputs.get("checkpoint_dir", "outputs/checkpoints/stage7_bc_smoke"))).expanduser()
        / "best.pt"
    )
    device = choose_device(str(cfg.get("device", "auto")))
    raw_checkpoint = torch.load(str(Path(checkpoint_path).expanduser()), map_location="cpu")
    policy_type = infer_policy_type(args.policy_type, raw_checkpoint)
    if policy_type == "diffusion":
        model, checkpoint = load_diffusion_model(checkpoint_path, device)
    elif policy_type == "flow_matching":
        model, checkpoint = load_flow_matching_model(checkpoint_path, device)
    else:
        model, checkpoint = load_bc_model(checkpoint_path, device)
    stats = load_stats(checkpoint["stats_path"])
    dataset = UVMSEpisodeDataset.from_config(cfg["dataset"], split=args.split, stats=stats)
    loader = DataLoader(dataset, batch_size=int((cfg.get("train", {}) or {}).get("batch_size", 32)), shuffle=False)

    if policy_type == "diffusion":
        eval_cfg = cfg.get("eval", {}) or {}
        num_inference_steps = int(
            args.num_inference_steps
            if args.num_inference_steps is not None
            else eval_cfg.get("num_inference_steps", checkpoint.get("num_diffusion_steps", 50))
        )
        seed = int(cfg.get("seed", 8))
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        mse_norm, pred_norm, target_norm, mask = collect_diffusion_predictions(
            model, loader, device, num_inference_steps, args.sampling_mode
        )
        ode_steps = None
    elif policy_type == "flow_matching":
        eval_cfg = cfg.get("eval", {}) or {}
        ode_steps = int(
            args.ode_steps
            if args.ode_steps is not None
            else eval_cfg.get("ode_steps", 50)
        )
        seed = int(cfg.get("seed", 9))
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        mse_norm, pred_norm, target_norm, mask = collect_flow_matching_predictions(
            model, loader, device, ode_steps, args.sampling_mode
        )
        num_inference_steps = None
    else:
        num_inference_steps = None
        ode_steps = None
        mse_norm, pred_norm, target_norm, mask = collect_bc_predictions(model, loader, device)
    pred = unnormalize_actions(pred_norm, stats)
    target = unnormalize_actions(target_norm, stats)
    mse_action = float(np.mean((pred[mask] - target[mask]) ** 2))
    per_dim_mse = np.mean((pred[mask] - target[mask]) ** 2, axis=0)

    eval_dir = Path(str(outputs.get("eval_dir", "outputs/eval/stage7_bc_smoke"))).expanduser()
    eval_dir.mkdir(parents=True, exist_ok=True)
    prefix = "" if policy_type == "bc" else f"{policy_type}_"
    output_suffix = str(args.output_suffix or "")
    plot_path = eval_dir / f"pred_vs_expert_{prefix}{args.split}{output_suffix}.png"
    plot_pred_vs_target(pred, target, mask, plot_path)

    summary = {
        "policy_type": policy_type,
        "checkpoint": str(Path(checkpoint_path).expanduser()),
        "split": args.split,
        "samples": len(dataset),
        "valid_action_steps": int(mask.sum()),
        "normalized_mse": mse_norm,
        "action_mse": mse_action,
        "per_dim_action_mse": per_dim_mse.tolist(),
        "plot": str(plot_path),
    }
    if policy_type in {"diffusion", "flow_matching"}:
        summary["sampling_mode"] = args.sampling_mode
    if num_inference_steps is not None:
        summary["num_inference_steps"] = int(num_inference_steps)
    if ode_steps is not None:
        summary["ode_steps"] = int(ode_steps)
    summary_path = eval_dir / f"offline_eval_{prefix}{args.split}{output_suffix}.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
