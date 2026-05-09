#!/usr/bin/env python3

import argparse
import json
import random
from pathlib import Path
import sys
from typing import Dict, List, Mapping

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader

try:
    from torch.utils.tensorboard import SummaryWriter
except Exception as exc:  # pragma: no cover - environment fallback
    SummaryWriter = None
    TENSORBOARD_IMPORT_ERROR = str(exc)
else:
    TENSORBOARD_IMPORT_ERROR = ""


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from learning.datasets.uvms_episode_dataset import (  # noqa: E402
    UVMSEpisodeDataset,
    load_stats,
    save_stats,
)
from learning.models.bc_policy import BCMLPPolicy  # noqa: E402


def load_config(path: str) -> Dict[str, object]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle) or {}
    if not isinstance(cfg, dict):
        raise ValueError("config must be a YAML mapping")
    return cfg


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def choose_device(config_value: str) -> torch.device:
    if config_value == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(config_value)


def masked_mse(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    weight = mask.unsqueeze(-1)
    squared = (pred - target).pow(2) * weight
    denom = weight.sum() * pred.shape[-1]
    return squared.sum() / denom.clamp_min(1.0)


class NullSummaryWriter:
    def add_scalar(self, *args, **kwargs) -> None:
        return None

    def close(self) -> None:
        return None


@torch.no_grad()
def evaluate(model: torch.nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    losses = []
    weights = []
    for batch in loader:
        obs = batch["obs"].to(device)
        action = batch["action"].to(device)
        mask = batch["action_mask"].to(device)
        pred = model(obs)
        loss = masked_mse(pred, action, mask)
        losses.append(float(loss.item()) * float(mask.sum().item()))
        weights.append(float(mask.sum().item()))
    return float(sum(losses) / max(sum(weights), 1.0))


def make_loaders(cfg: Mapping[str, object]):
    dataset_cfg = cfg["dataset"]
    train_dataset = UVMSEpisodeDataset.from_config(dataset_cfg, split="train")
    val_dataset = UVMSEpisodeDataset.from_config(
        dataset_cfg,
        split="val",
        stats=train_dataset.stats,
    )

    train_cfg = cfg["train"]
    train_loader = DataLoader(
        train_dataset,
        batch_size=int(train_cfg.get("batch_size", 32)),
        shuffle=True,
        num_workers=int(train_cfg.get("num_workers", 0)),
        drop_last=False,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=int(train_cfg.get("batch_size", 32)),
        shuffle=False,
        num_workers=int(train_cfg.get("num_workers", 0)),
        drop_last=False,
    )
    return train_dataset, val_dataset, train_loader, val_loader


def save_checkpoint(
    path: Path,
    model: BCMLPPolicy,
    optimizer: torch.optim.Optimizer,
    cfg: Mapping[str, object],
    epoch: int,
    train_loss: float,
    val_loss: float,
    stats_path: Path,
    feature_names: List[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
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
        },
        str(path),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a small BC baseline on UVMS episodes.")
    parser.add_argument(
        "--config",
        default=str(PACKAGE_ROOT / "config" / "train_bc.yaml"),
        help="Path to train_bc.yaml.",
    )
    parser.add_argument("--epochs", type=int, default=None, help="Optional epoch override.")
    args = parser.parse_args()

    cfg = load_config(args.config)
    set_seed(int(cfg.get("seed", 7)))
    device = choose_device(str(cfg.get("device", "auto")))

    train_dataset, val_dataset, train_loader, val_loader = make_loaders(cfg)
    model_cfg = cfg.get("model", {}) or {}
    model = BCMLPPolicy(
        obs_dim=train_dataset.obs_dim,
        action_dim=train_dataset.action_dim,
        obs_horizon=train_dataset.obs_horizon,
        action_horizon=train_dataset.action_horizon,
        hidden_dims=model_cfg.get("hidden_dims", [128, 128]),
        dropout=float(model_cfg.get("dropout", 0.0)),
        activation=str(model_cfg.get("activation", "relu")),
    ).to(device)

    train_cfg = cfg.get("train", {}) or {}
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(train_cfg.get("lr", 1e-3)),
        weight_decay=float(train_cfg.get("weight_decay", 0.0)),
    )
    epochs = int(args.epochs if args.epochs is not None else train_cfg.get("epochs", 120))
    grad_clip = float(train_cfg.get("grad_clip_norm", 0.0))
    log_interval = int(train_cfg.get("log_interval", 10))

    outputs = cfg.get("outputs", {}) or {}
    checkpoint_dir = Path(str(outputs.get("checkpoint_dir", "outputs/checkpoints/stage7_bc_smoke"))).expanduser()
    log_dir = Path(str(outputs.get("log_dir", "outputs/logs/stage7_bc_smoke"))).expanduser()
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
    history = []
    print(
        f"train samples={len(train_dataset)} val samples={len(val_dataset)} "
        f"obs_dim={train_dataset.obs_dim} action_dim={train_dataset.action_dim} device={device}"
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
            pred = model(obs)
            loss = masked_mse(pred, action, mask)
            loss.backward()
            if grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()
            weight = float(mask.sum().item())
            train_weighted += float(loss.item()) * weight
            train_count += weight

        train_loss = train_weighted / max(train_count, 1.0)
        val_loss = evaluate(model, val_loader, device)
        writer.add_scalar("loss/train", train_loss, epoch)
        writer.add_scalar("loss/val", val_loss, epoch)
        history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})

        if epoch == 1 or epoch % log_interval == 0 or epoch == epochs:
            print(f"epoch {epoch:04d} train_loss={train_loss:.8f} val_loss={val_loss:.8f}")

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
            )

    writer.close()
    summary = {
        "config": str(Path(args.config).expanduser()),
        "epochs": epochs,
        "train_samples": len(train_dataset),
        "val_samples": len(val_dataset),
        "obs_dim": train_dataset.obs_dim,
        "action_dim": train_dataset.action_dim,
        "best_val_loss": best_val,
        "final_train_loss": history[-1]["train_loss"],
        "final_val_loss": history[-1]["val_loss"],
        "checkpoint_last": str(checkpoint_dir / "last.pt"),
        "checkpoint_best": str(checkpoint_dir / "best.pt"),
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
