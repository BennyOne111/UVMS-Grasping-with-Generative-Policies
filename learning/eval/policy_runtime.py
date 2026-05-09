from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple

import numpy as np
import torch

from learning.datasets.uvms_episode_dataset import DatasetStats, load_stats
from learning.models.bc_policy import BCMLPPolicy
from learning.models.diffusion_policy import DiffusionPolicy
from learning.models.flow_matching_policy import FlowMatchingPolicy


def _infer_policy_type(requested: str, checkpoint: Mapping[str, object]) -> str:
    if requested != "auto":
        return requested
    return str(checkpoint.get("policy_type", "bc"))


def _build_bc(checkpoint: Mapping[str, object], device: torch.device) -> BCMLPPolicy:
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
    return model


def _build_diffusion(checkpoint: Mapping[str, object], device: torch.device) -> DiffusionPolicy:
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
    return model


def _build_flow_matching(checkpoint: Mapping[str, object], device: torch.device) -> FlowMatchingPolicy:
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
    return model


class RuntimePolicy:
    def __init__(
        self,
        model: torch.nn.Module,
        checkpoint: Dict[str, object],
        stats: DatasetStats,
        policy_type: str,
        device: torch.device,
    ) -> None:
        self.model = model
        self.checkpoint = checkpoint
        self.stats = stats
        self.policy_type = policy_type
        self.device = device
        self.obs_dim = int(checkpoint["obs_dim"])
        self.action_dim = int(checkpoint["action_dim"])
        self.obs_horizon = int(checkpoint["obs_horizon"])
        self.action_horizon = int(checkpoint["action_horizon"])

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_path: str,
        device: torch.device,
        policy_type: str = "auto",
    ) -> "RuntimePolicy":
        path = Path(checkpoint_path).expanduser()
        checkpoint = torch.load(str(path), map_location=device)
        resolved_type = _infer_policy_type(policy_type, checkpoint)
        if resolved_type == "diffusion":
            model = _build_diffusion(checkpoint, device)
        elif resolved_type == "flow_matching":
            model = _build_flow_matching(checkpoint, device)
        elif resolved_type == "bc":
            model = _build_bc(checkpoint, device)
        else:
            raise ValueError(f"unsupported policy_type: {resolved_type}")
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        stats = load_stats(str(checkpoint["stats_path"]))
        return cls(model=model, checkpoint=checkpoint, stats=stats, policy_type=resolved_type, device=device)

    def normalize_obs(self, obs_history: np.ndarray) -> np.ndarray:
        obs = np.asarray(obs_history, dtype=np.float32)
        if obs.shape != (self.obs_horizon, self.obs_dim):
            raise ValueError(
                f"obs_history must have shape ({self.obs_horizon}, {self.obs_dim}), got {obs.shape}"
            )
        return (obs - self.stats.obs_mean) / self.stats.obs_std

    def unnormalize_action(self, action_chunk: np.ndarray) -> np.ndarray:
        action = np.asarray(action_chunk, dtype=np.float32)
        return action * self.stats.action_std.reshape(1, -1) + self.stats.action_mean.reshape(1, -1)

    @torch.no_grad()
    def predict_action_chunk(
        self,
        obs_history: np.ndarray,
        num_inference_steps: Optional[int] = None,
        ode_steps: Optional[int] = None,
    ) -> Tuple[np.ndarray, float]:
        obs = self.normalize_obs(obs_history)
        obs_tensor = torch.from_numpy(obs).unsqueeze(0).to(self.device)
        if self.policy_type == "diffusion":
            steps = int(num_inference_steps if num_inference_steps is not None else 50)
            pred = self.model.sample(obs_tensor, num_inference_steps=steps)
        elif self.policy_type == "flow_matching":
            steps = int(ode_steps if ode_steps is not None else 50)
            pred = self.model.sample(obs_tensor, ode_steps=steps)
        else:
            pred = self.model(obs_tensor)
        normalized = pred.squeeze(0).detach().cpu().numpy()
        return self.unnormalize_action(normalized), float(torch.cuda.max_memory_allocated(self.device) if self.device.type == "cuda" else 0.0)


def choose_device(config_value: str) -> torch.device:
    if config_value == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(config_value)
