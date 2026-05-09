from typing import Sequence

import torch
from torch import nn


def _activation(name: str) -> nn.Module:
    normalized = name.lower()
    if normalized == "relu":
        return nn.ReLU()
    if normalized == "gelu":
        return nn.GELU()
    if normalized == "tanh":
        return nn.Tanh()
    raise ValueError(f"unsupported activation: {name}")


class BCMLPPolicy(nn.Module):
    """Small MLP behavior-cloning policy for state history to action chunk."""

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        obs_horizon: int = 4,
        action_horizon: int = 16,
        hidden_dims: Sequence[int] = (128, 128),
        dropout: float = 0.0,
        activation: str = "relu",
    ) -> None:
        super().__init__()
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.obs_horizon = int(obs_horizon)
        self.action_horizon = int(action_horizon)

        input_dim = self.obs_dim * self.obs_horizon
        output_dim = self.action_dim * self.action_horizon
        layers = []
        current_dim = input_dim
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(current_dim, int(hidden_dim)))
            layers.append(_activation(activation))
            if dropout > 0:
                layers.append(nn.Dropout(float(dropout)))
            current_dim = int(hidden_dim)
        layers.append(nn.Linear(current_dim, output_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, obs_history: torch.Tensor) -> torch.Tensor:
        if obs_history.ndim != 3:
            raise ValueError(f"obs_history must be [B,H,D], got {tuple(obs_history.shape)}")
        batch = obs_history.shape[0]
        flat = obs_history.reshape(batch, self.obs_horizon * self.obs_dim)
        action = self.net(flat)
        return action.reshape(batch, self.action_horizon, self.action_dim)
