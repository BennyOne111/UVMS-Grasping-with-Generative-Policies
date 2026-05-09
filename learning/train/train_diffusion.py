#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List, Mapping

import numpy as np
import torch
from torch.utils.data import DataLoader


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from learning.datasets.uvms_episode_dataset import UVMSEpisodeDataset, save_stats  # noqa: E402
from learning.models.diffusion_policy import DiffusionPolicy  # noqa: E402
from learning.train.train_bc import (  # noqa: E402
    NullSummaryWriter,
    SummaryWriter,
    TENSORBOARD_IMPORT_ERROR,
    choose_device,
    load_config,
    set_seed,
)


def make_loaders(cfg: Mapping[str, object]):
    dataset_cfg = cfg["dataset"]
    train_dataset = UVMSEpisodeDataset.from_config(dataset_cfg, split="train")
    val_dataset = UVMSEpisodeDataset.from_config(
        dataset_cfg,
        split="val",
        stats=train_dataset.stats,
    )
    train_cfg = cfg["train"]
    batch_size = int(train_cfg.get("batch_size", 32))
    num_workers = int(train_cfg.get("num_workers", 0))
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        drop_last=False,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        drop_last=False,
    )
    return train_dataset, val_dataset, train_loader, val_loader


def build_model(cfg: Mapping[str, object], dataset: UVMSEpisodeDataset) -> DiffusionPolicy:
    model_cfg = cfg.get("model", {}) or {}
    return DiffusionPolicy(
        obs_dim=dataset.obs_dim,
        action_dim=dataset.action_dim,
        obs_horizon=dataset.obs_horizon,
        action_horizon=dataset.action_horizon,
        num_diffusion_steps=int(model_cfg.get("num_diffusion_steps", 50)),
        beta_start=float(model_cfg.get("beta_start", 1e-4)),
        beta_end=float(model_cfg.get("beta_end", 0.02)),
        hidden_dims=model_cfg.get("hidden_dims", [256, 256, 256]),
        time_embed_dim=int(model_cfg.get("time_embed_dim", 64)),
        dropout=float(model_cfg.get("dropout", 0.0)),
        activation=str(model_cfg.get("activation", "silu")),
        prediction_type=str(model_cfg.get("prediction_type", "epsilon")),
    )


@torch.no_grad()
def evaluate_denoising_loss(model: DiffusionPolicy, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    weighted = 0.0
    count = 0.0
    for batch in loader:
        obs = batch["obs"].to(device)
        action = batch["action"].to(device)
        mask = batch["action_mask"].to(device)
        loss = model.training_loss(obs, action, mask)
        weight = float(mask.sum().item())
        weighted += float(loss.item()) * weight
        count += weight
    return weighted / max(count, 1.0)


@torch.no_grad()
def evaluate_zero_init_action_mse(
    model: DiffusionPolicy,
    loader: DataLoader,
    device: torch.device,
    action_mean: np.ndarray,
    action_std: np.ndarray,
    num_inference_steps: int,
) -> float:
    model.eval()
    mean = torch.as_tensor(action_mean, device=device, dtype=torch.float32).view(1, 1, -1)
    std = torch.as_tensor(action_std, device=device, dtype=torch.float32).view(1, 1, -1)
    weighted = 0.0
    count = 0.0
    for batch in loader:
        obs = batch["obs"].to(device)
        action = batch["action"].to(device)
        mask = batch["action_mask"].to(device)
        initial_action = torch.zeros(
            (obs.shape[0], model.action_horizon, model.action_dim),
            device=device,
            dtype=obs.dtype,
        )
        pred = model.sample(
            obs,
            num_inference_steps=int(num_inference_steps),
            initial_action=initial_action,
            deterministic_reverse=True,
        )
        pred_raw = pred * std + mean
        action_raw = action * std + mean
        expanded_mask = mask.unsqueeze(-1)
        sq = (pred_raw - action_raw).pow(2) * expanded_mask
        weight = float(expanded_mask.sum().item() * model.action_dim)
        weighted += float(sq.sum().item())
        count += weight
    return weighted / max(count, 1.0)


def diffusion_training_loss_with_x0_aux(
    model: DiffusionPolicy,
    obs_history: torch.Tensor,
    clean_action: torch.Tensor,
    action_mask: torch.Tensor,
    x0_aux_loss_weight: float,
    x0_aux_loss_dim_weights: torch.Tensor = None,
) -> torch.Tensor:
    batch = clean_action.shape[0]
    timesteps = torch.randint(
        low=0,
        high=model.num_diffusion_steps,
        size=(batch,),
        device=clean_action.device,
        dtype=torch.long,
    )
    noise = torch.randn_like(clean_action)
    noisy_action = model.q_sample(clean_action, timesteps, noise)
    pred_noise = model.predict_noise(noisy_action, timesteps, obs_history)
    weight = action_mask.unsqueeze(-1)
    denom = (weight.sum() * clean_action.shape[-1]).clamp_min(1.0)
    epsilon_loss = ((pred_noise - noise).pow(2) * weight).sum() / denom

    scale_clean = model.sqrt_alphas_cumprod[timesteps].view(-1, 1, 1)
    scale_noise = model.sqrt_one_minus_alphas_cumprod[timesteps].view(-1, 1, 1)
    pred_x0 = (noisy_action - scale_noise * pred_noise) / scale_clean.clamp_min(1e-12)
    if x0_aux_loss_dim_weights is None:
        x0_weight = weight
        x0_denom = denom
    else:
        dim_weights = x0_aux_loss_dim_weights.view(1, 1, -1).to(
            device=clean_action.device,
            dtype=clean_action.dtype,
        )
        x0_weight = weight * dim_weights
        x0_denom = (weight.sum() * dim_weights.sum()).clamp_min(1.0)
    x0_loss = ((pred_x0 - clean_action).pow(2) * x0_weight).sum() / x0_denom
    return epsilon_loss + float(x0_aux_loss_weight) * x0_loss


def save_checkpoint(
    path: Path,
    model: DiffusionPolicy,
    optimizer: torch.optim.Optimizer,
    cfg: Mapping[str, object],
    epoch: int,
    train_loss: float,
    val_loss: float,
    stats_path: Path,
    feature_names: List[str],
    extra_metrics: Mapping[str, object] = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
            "policy_type": "diffusion",
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "config": dict(cfg),
            "epoch": int(epoch),
            "train_loss": float(train_loss),
            "val_loss": float(val_loss),
            "stats_path": str(stats_path),
            "feature_names": feature_names,
            "obs_dim": model.obs_dim,
            "action_dim": model.action_dim,
            "obs_horizon": model.obs_horizon,
            "action_horizon": model.action_horizon,
            "num_diffusion_steps": model.num_diffusion_steps,
        }
    if extra_metrics:
        payload.update(dict(extra_metrics))
    torch.save(payload, str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a small state-based Diffusion Policy.")
    parser.add_argument(
        "--config",
        default=str(PACKAGE_ROOT / "config" / "train_diffusion.yaml"),
        help="Path to train_diffusion.yaml.",
    )
    parser.add_argument("--epochs", type=int, default=None, help="Optional epoch override.")
    args = parser.parse_args()

    cfg = load_config(args.config)
    set_seed(int(cfg.get("seed", 8)))
    device = choose_device(str(cfg.get("device", "auto")))

    train_dataset, val_dataset, train_loader, val_loader = make_loaders(cfg)
    model = build_model(cfg, train_dataset).to(device)

    train_cfg = cfg.get("train", {}) or {}
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(train_cfg.get("lr", 1e-3)),
        weight_decay=float(train_cfg.get("weight_decay", 1e-6)),
    )
    epochs = int(args.epochs if args.epochs is not None else train_cfg.get("epochs", 160))
    grad_clip = float(train_cfg.get("grad_clip_norm", 1.0))
    log_interval = int(train_cfg.get("log_interval", 20))
    x0_aux_loss_weight = float(train_cfg.get("x0_aux_loss_weight", 0.0))
    x0_aux_loss_dim_weights_cfg = train_cfg.get("x0_aux_loss_dim_weights")
    x0_aux_loss_dim_weights = None
    if x0_aux_loss_dim_weights_cfg is not None:
        if len(x0_aux_loss_dim_weights_cfg) != train_dataset.action_dim:
            raise ValueError(
                "train.x0_aux_loss_dim_weights length must match action_dim "
                f"({train_dataset.action_dim})"
            )
        x0_aux_loss_dim_weights = torch.as_tensor(
            [float(v) for v in x0_aux_loss_dim_weights_cfg],
            device=device,
            dtype=torch.float32,
        )
    eval_cfg = cfg.get("eval", {}) or {}
    select_best_action_metric = bool(eval_cfg.get("select_best_action_metric", False))
    action_metric_inference_steps = int(eval_cfg.get("action_metric_inference_steps", eval_cfg.get("num_inference_steps", 50)))

    outputs = cfg.get("outputs", {}) or {}
    checkpoint_dir = Path(str(outputs.get("checkpoint_dir", "outputs/checkpoints/stage8_diffusion_smoke"))).expanduser()
    log_dir = Path(str(outputs.get("log_dir", "outputs/logs/stage8_diffusion_smoke"))).expanduser()
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    stats_path = checkpoint_dir / "normalization_stats.json"
    save_stats(train_dataset.stats, str(stats_path))

    tensorboard_status = "enabled"
    if SummaryWriter is None:
        writer = NullSummaryWriter()
        tensorboard_status = f"disabled: {TENSORBOARD_IMPORT_ERROR}"
        print(f"tensorboard disabled: {TENSORBOARD_IMPORT_ERROR}")
    else:
        writer = SummaryWriter(log_dir=str(log_dir / "tensorboard"))

    best_val = float("inf")
    best_action_mse = float("inf")
    history = []
    print(
        f"train samples={len(train_dataset)} val samples={len(val_dataset)} "
        f"obs_dim={train_dataset.obs_dim} action_dim={train_dataset.action_dim} "
        f"steps={model.num_diffusion_steps} device={device}"
    )

    for epoch in range(1, epochs + 1):
        model.train()
        train_weighted = 0.0
        train_count = 0.0
        for batch in train_loader:
            obs = batch["obs"].to(device)
            action = batch["action"].to(device)
            mask = batch["action_mask"].to(device)
            optimizer.zero_grad(set_to_none=True)
            if x0_aux_loss_weight > 0.0:
                loss = diffusion_training_loss_with_x0_aux(
                    model,
                    obs,
                    action,
                    mask,
                    x0_aux_loss_weight,
                    x0_aux_loss_dim_weights=x0_aux_loss_dim_weights,
                )
            else:
                loss = model.training_loss(obs, action, mask)
            loss.backward()
            if grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()
            weight = float(mask.sum().item())
            train_weighted += float(loss.item()) * weight
            train_count += weight

        train_loss = train_weighted / max(train_count, 1.0)
        val_loss = evaluate_denoising_loss(model, val_loader, device)
        val_action_mse = None
        if select_best_action_metric:
            val_action_mse = evaluate_zero_init_action_mse(
                model,
                val_loader,
                device,
                train_dataset.stats.action_mean,
                train_dataset.stats.action_std,
                action_metric_inference_steps,
            )
        writer.add_scalar("loss/train_denoising", train_loss, epoch)
        writer.add_scalar("loss/val_denoising", val_loss, epoch)
        if val_action_mse is not None:
            writer.add_scalar("metrics/val_zero_init_action_mse", val_action_mse, epoch)
        history_row = {"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss}
        if val_action_mse is not None:
            history_row["val_zero_init_action_mse"] = val_action_mse
        history.append(history_row)

        if epoch == 1 or epoch % log_interval == 0 or epoch == epochs:
            if val_action_mse is None:
                print(f"epoch {epoch:04d} train_loss={train_loss:.8f} val_loss={val_loss:.8f}")
            else:
                print(
                    f"epoch {epoch:04d} train_loss={train_loss:.8f} "
                    f"val_loss={val_loss:.8f} val_action_mse={val_action_mse:.12f}"
                )

        extra_metrics = {}
        if val_action_mse is not None:
            extra_metrics["val_zero_init_action_mse"] = float(val_action_mse)
            extra_metrics["action_metric_inference_steps"] = int(action_metric_inference_steps)
        save_checkpoint(
            checkpoint_dir / "last.pt",
            model,
            optimizer,
            cfg,
            epoch,
            train_loss,
            val_loss,
            stats_path,
            train_dataset.feature_names,
            extra_metrics=extra_metrics,
        )
        if val_loss < best_val:
            best_val = val_loss
            save_checkpoint(
                checkpoint_dir / "best.pt",
                model,
                optimizer,
                cfg,
                epoch,
                train_loss,
                val_loss,
                stats_path,
                train_dataset.feature_names,
                extra_metrics=extra_metrics,
            )
        if val_action_mse is not None and val_action_mse < best_action_mse:
            best_action_mse = val_action_mse
            save_checkpoint(
                checkpoint_dir / "best_action.pt",
                model,
                optimizer,
                cfg,
                epoch,
                train_loss,
                val_loss,
                stats_path,
                train_dataset.feature_names,
                extra_metrics=extra_metrics,
            )

    writer.close()
    summary = {
        "policy_type": "diffusion",
        "config": str(Path(args.config).expanduser()),
        "epochs": epochs,
        "train_samples": len(train_dataset),
        "val_samples": len(val_dataset),
        "obs_dim": train_dataset.obs_dim,
        "action_dim": train_dataset.action_dim,
        "action_horizon": train_dataset.action_horizon,
        "num_diffusion_steps": model.num_diffusion_steps,
        "best_val_loss": best_val,
        "x0_aux_loss_weight": x0_aux_loss_weight,
        "x0_aux_loss_dim_weights": (
            [float(v) for v in x0_aux_loss_dim_weights_cfg]
            if x0_aux_loss_dim_weights_cfg is not None
            else None
        ),
        "best_val_zero_init_action_mse": best_action_mse if select_best_action_metric else None,
        "action_metric_inference_steps": action_metric_inference_steps if select_best_action_metric else None,
        "final_train_loss": history[-1]["train_loss"],
        "final_val_loss": history[-1]["val_loss"],
        "final_val_zero_init_action_mse": history[-1].get("val_zero_init_action_mse"),
        "checkpoint_last": str(checkpoint_dir / "last.pt"),
        "checkpoint_best": str(checkpoint_dir / "best.pt"),
        "checkpoint_best_action": str(checkpoint_dir / "best_action.pt") if select_best_action_metric else None,
        "normalization_stats": str(stats_path),
        "tensorboard": tensorboard_status,
        "history": history,
    }
    (log_dir / "train_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({k: summary[k] for k in summary if k != "history"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
