from typing import Sequence

import torch
from torch import nn


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


class SinusoidalTimeEmbedding(nn.Module):
    def __init__(self, dim: int) -> None:
        super().__init__()
        if dim <= 0:
            raise ValueError("time embedding dim must be positive")
        self.dim = int(dim)

    def forward(self, timesteps: torch.Tensor) -> torch.Tensor:
        half_dim = self.dim // 2
        if half_dim == 0:
            return timesteps.float().unsqueeze(-1)
        exponent = torch.arange(half_dim, device=timesteps.device, dtype=torch.float32)
        exponent = -torch.log(torch.tensor(10000.0, device=timesteps.device)) * exponent / max(half_dim - 1, 1)
        freqs = torch.exp(exponent)
        args = timesteps.float().unsqueeze(-1) * freqs.unsqueeze(0)
        embedding = torch.cat([torch.sin(args), torch.cos(args)], dim=-1)
        if self.dim % 2 == 1:
            embedding = torch.cat([embedding, torch.zeros_like(embedding[:, :1])], dim=-1)
        return embedding


class ConditionalActionDenoiser(nn.Module):
    """Small state-conditioned denoiser for normalized action chunks."""

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        obs_horizon: int = 4,
        action_horizon: int = 16,
        hidden_dims: Sequence[int] = (256, 256, 256),
        time_embed_dim: int = 64,
        dropout: float = 0.0,
        activation: str = "silu",
    ) -> None:
        super().__init__()
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.obs_horizon = int(obs_horizon)
        self.action_horizon = int(action_horizon)
        self.time_embed_dim = int(time_embed_dim)

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

    def forward(self, noisy_action: torch.Tensor, timesteps: torch.Tensor, obs_history: torch.Tensor) -> torch.Tensor:
        if noisy_action.ndim != 3:
            raise ValueError(f"noisy_action must be [B,A,D], got {tuple(noisy_action.shape)}")
        if obs_history.ndim != 3:
            raise ValueError(f"obs_history must be [B,H,D], got {tuple(obs_history.shape)}")
        batch = noisy_action.shape[0]
        obs_flat = obs_history.reshape(batch, self.obs_horizon * self.obs_dim)
        action_flat = noisy_action.reshape(batch, self.action_horizon * self.action_dim)
        time_embed = self.time_embedding(timesteps)
        pred = self.net(torch.cat([obs_flat, action_flat, time_embed], dim=-1))
        return pred.reshape(batch, self.action_horizon, self.action_dim)


class DiffusionPolicy(nn.Module):
    """DDPM-style policy for normalized action chunks conditioned on state history."""

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        obs_horizon: int = 4,
        action_horizon: int = 16,
        num_diffusion_steps: int = 50,
        beta_start: float = 1e-4,
        beta_end: float = 0.02,
        hidden_dims: Sequence[int] = (256, 256, 256),
        time_embed_dim: int = 64,
        dropout: float = 0.0,
        activation: str = "silu",
        prediction_type: str = "epsilon",
    ) -> None:
        super().__init__()
        if prediction_type != "epsilon":
            raise ValueError("Stage 8 supports prediction_type='epsilon' only")
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.obs_horizon = int(obs_horizon)
        self.action_horizon = int(action_horizon)
        self.num_diffusion_steps = int(num_diffusion_steps)
        self.prediction_type = prediction_type

        self.denoiser = ConditionalActionDenoiser(
            obs_dim=obs_dim,
            action_dim=action_dim,
            obs_horizon=obs_horizon,
            action_horizon=action_horizon,
            hidden_dims=hidden_dims,
            time_embed_dim=time_embed_dim,
            dropout=dropout,
            activation=activation,
        )

        betas = torch.linspace(float(beta_start), float(beta_end), self.num_diffusion_steps, dtype=torch.float32)
        alphas = 1.0 - betas
        alphas_cumprod = torch.cumprod(alphas, dim=0)
        alphas_cumprod_prev = torch.cat([torch.ones(1, dtype=torch.float32), alphas_cumprod[:-1]], dim=0)

        self.register_buffer("betas", betas)
        self.register_buffer("alphas", alphas)
        self.register_buffer("alphas_cumprod", alphas_cumprod)
        self.register_buffer("alphas_cumprod_prev", alphas_cumprod_prev)
        self.register_buffer("sqrt_alphas_cumprod", torch.sqrt(alphas_cumprod))
        self.register_buffer("sqrt_one_minus_alphas_cumprod", torch.sqrt(1.0 - alphas_cumprod))
        self.register_buffer("sqrt_recip_alphas", torch.sqrt(1.0 / alphas))
        posterior_variance = betas * (1.0 - alphas_cumprod_prev) / (1.0 - alphas_cumprod).clamp_min(1e-12)
        self.register_buffer("posterior_variance", posterior_variance)

    def q_sample(self, clean_action: torch.Tensor, timesteps: torch.Tensor, noise: torch.Tensor) -> torch.Tensor:
        scale_clean = self.sqrt_alphas_cumprod[timesteps].view(-1, 1, 1)
        scale_noise = self.sqrt_one_minus_alphas_cumprod[timesteps].view(-1, 1, 1)
        return scale_clean * clean_action + scale_noise * noise

    def predict_noise(self, noisy_action: torch.Tensor, timesteps: torch.Tensor, obs_history: torch.Tensor) -> torch.Tensor:
        return self.denoiser(noisy_action, timesteps, obs_history)

    def training_loss(
        self,
        obs_history: torch.Tensor,
        clean_action: torch.Tensor,
        action_mask: torch.Tensor,
    ) -> torch.Tensor:
        batch = clean_action.shape[0]
        timesteps = torch.randint(
            low=0,
            high=self.num_diffusion_steps,
            size=(batch,),
            device=clean_action.device,
            dtype=torch.long,
        )
        noise = torch.randn_like(clean_action)
        noisy_action = self.q_sample(clean_action, timesteps, noise)
        pred_noise = self.predict_noise(noisy_action, timesteps, obs_history)
        weight = action_mask.unsqueeze(-1)
        squared = (pred_noise - noise).pow(2) * weight
        denom = weight.sum() * clean_action.shape[-1]
        return squared.sum() / denom.clamp_min(1.0)

    @torch.no_grad()
    def sample(
        self,
        obs_history: torch.Tensor,
        num_inference_steps: int = 50,
        generator: torch.Generator = None,
        initial_action: torch.Tensor = None,
        deterministic_reverse: bool = False,
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

        step_count = max(1, min(int(num_inference_steps), self.num_diffusion_steps))
        timesteps = torch.linspace(
            self.num_diffusion_steps - 1,
            0,
            steps=step_count,
            device=obs_history.device,
        ).long()
        timesteps = torch.unique_consecutive(timesteps)

        for step in timesteps:
            t = torch.full((batch,), int(step.item()), device=obs_history.device, dtype=torch.long)
            pred_noise = self.predict_noise(action, t, obs_history)
            beta_t = self.betas[t].view(-1, 1, 1)
            sqrt_one_minus = self.sqrt_one_minus_alphas_cumprod[t].view(-1, 1, 1)
            sqrt_recip_alpha = self.sqrt_recip_alphas[t].view(-1, 1, 1)
            model_mean = sqrt_recip_alpha * (action - beta_t * pred_noise / sqrt_one_minus.clamp_min(1e-12))
            if int(step.item()) == 0:
                action = model_mean
            else:
                if deterministic_reverse:
                    noise = torch.zeros_like(action)
                elif generator is None:
                    noise = torch.randn_like(action)
                else:
                    noise = torch.randn(action.shape, device=action.device, generator=generator)
                variance = self.posterior_variance[t].view(-1, 1, 1)
                action = model_mean + torch.sqrt(variance.clamp_min(1e-20)) * noise
        return action
