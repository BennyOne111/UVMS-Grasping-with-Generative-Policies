from typing import Sequence

import torch
from torch import nn

from learning.models.diffusion_policy import SinusoidalTimeEmbedding


def _activation(name: str) -> nn.Module:
    normalized = name.lower()
    if normalized == "relu":
        return nn.ReLU()
    if normalized == "gelu":
        return nn.GELU()
    if normalized == "silu":
        return nn.SiLU()
    if normalized == "tanh":
        return nn.Tanh()
    raise ValueError(f"unsupported activation: {name}")


class ConditionalVelocityField(nn.Module):
    """Small state-conditioned velocity field for normalized action chunks."""

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        obs_horizon: int = 4,
        action_horizon: int = 16,
        hidden_dims: Sequence[int] = (256, 256, 256),
        time_embed_dim: int = 64,
        time_scale: float = 1000.0,
        dropout: float = 0.0,
        activation: str = "silu",
    ) -> None:
        super().__init__()
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.obs_horizon = int(obs_horizon)
        self.action_horizon = int(action_horizon)
        self.time_embed_dim = int(time_embed_dim)
        self.time_scale = float(time_scale)

        self.time_embedding = SinusoidalTimeEmbedding(self.time_embed_dim)
        input_dim = (
            self.obs_dim * self.obs_horizon
            + self.action_dim * self.action_horizon
            + self.time_embed_dim
        )
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

    def forward(self, action_state: torch.Tensor, times: torch.Tensor, obs_history: torch.Tensor) -> torch.Tensor:
        if action_state.ndim != 3:
            raise ValueError(f"action_state must be [B,A,D], got {tuple(action_state.shape)}")
        if obs_history.ndim != 3:
            raise ValueError(f"obs_history must be [B,H,D], got {tuple(obs_history.shape)}")
        batch = action_state.shape[0]
        obs_flat = obs_history.reshape(batch, self.obs_horizon * self.obs_dim)
        action_flat = action_state.reshape(batch, self.action_horizon * self.action_dim)
        time_embed = self.time_embedding(times.float() * self.time_scale)
        velocity = self.net(torch.cat([obs_flat, action_flat, time_embed], dim=-1))
        return velocity.reshape(batch, self.action_horizon, self.action_dim)


class FlowMatchingPolicy(nn.Module):
    """Rectified-flow style policy for normalized action chunks."""

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        obs_horizon: int = 4,
        action_horizon: int = 16,
        hidden_dims: Sequence[int] = (256, 256, 256),
        time_embed_dim: int = 64,
        time_scale: float = 1000.0,
        dropout: float = 0.0,
        activation: str = "silu",
    ) -> None:
        super().__init__()
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.obs_horizon = int(obs_horizon)
        self.action_horizon = int(action_horizon)
        self.time_scale = float(time_scale)

        self.velocity_field = ConditionalVelocityField(
            obs_dim=obs_dim,
            action_dim=action_dim,
            obs_horizon=obs_horizon,
            action_horizon=action_horizon,
            hidden_dims=hidden_dims,
            time_embed_dim=time_embed_dim,
            time_scale=time_scale,
            dropout=dropout,
            activation=activation,
        )

    def predict_velocity(self, action_state: torch.Tensor, times: torch.Tensor, obs_history: torch.Tensor) -> torch.Tensor:
        return self.velocity_field(action_state, times, obs_history)

    def training_loss(
        self,
        obs_history: torch.Tensor,
        clean_action: torch.Tensor,
        action_mask: torch.Tensor,
    ) -> torch.Tensor:
        batch = clean_action.shape[0]
        x0 = torch.randn_like(clean_action)
        x1 = clean_action
        times = torch.rand((batch,), device=clean_action.device, dtype=clean_action.dtype)
        t_view = times.view(-1, 1, 1)
        xt = (1.0 - t_view) * x0 + t_view * x1
        target_velocity = x1 - x0
        pred_velocity = self.predict_velocity(xt, times, obs_history)
        weight = action_mask.unsqueeze(-1)
        squared = (pred_velocity - target_velocity).pow(2) * weight
        denom = weight.sum() * clean_action.shape[-1]
        return squared.sum() / denom.clamp_min(1.0)

    @torch.no_grad()
    def sample(
        self,
        obs_history: torch.Tensor,
        ode_steps: int = 50,
        generator: torch.Generator = None,
        initial_action: torch.Tensor = None,
    ) -> torch.Tensor:
        self.eval()
        batch = obs_history.shape[0]
        shape = (batch, self.action_horizon, self.action_dim)
        if initial_action is not None:
            if tuple(initial_action.shape) != shape:
                raise ValueError(f"initial_action must have shape {shape}, got {tuple(initial_action.shape)}")
            action = initial_action.to(device=obs_history.device, dtype=obs_history.dtype)
        elif generator is None:
            action = torch.randn(shape, device=obs_history.device)
        else:
            action = torch.randn(shape, device=obs_history.device, generator=generator)

        steps = max(1, int(ode_steps))
        dt = 1.0 / float(steps)
        for step in range(steps):
            t_value = step / float(steps)
            times = torch.full((batch,), t_value, device=obs_history.device, dtype=obs_history.dtype)
            velocity = self.predict_velocity(action, times, obs_history)
            action = action + dt * velocity
        return action
