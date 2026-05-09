import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset


DEFAULT_OBSERVATION_KEYS = (
    "base_pose",
    "base_velocity",
    "active_joint_positions",
    "active_joint_velocities",
    "gripper_state",
    "target_pose",
)

DERIVED_OBSERVATION_DIMS = {
    "eef_position_base_frame": 3,
    "target_position_base_frame": 3,
    "target_to_eef_base_frame": 3,
}


@dataclass(frozen=True)
class DatasetStats:
    obs_mean: np.ndarray
    obs_std: np.ndarray
    action_mean: np.ndarray
    action_std: np.ndarray

    def to_json_dict(self) -> Dict[str, object]:
        return {
            "obs_mean": self.obs_mean.tolist(),
            "obs_std": self.obs_std.tolist(),
            "action_mean": self.action_mean.tolist(),
            "action_std": self.action_std.tolist(),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "DatasetStats":
        return cls(
            obs_mean=np.asarray(data["obs_mean"], dtype=np.float32),
            obs_std=np.asarray(data["obs_std"], dtype=np.float32),
            action_mean=np.asarray(data["action_mean"], dtype=np.float32),
            action_std=np.asarray(data["action_std"], dtype=np.float32),
        )


def load_split_paths(split_file: str, split: str) -> List[str]:
    split_path = Path(split_file).expanduser()
    with split_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    paths = payload.get(split)
    if paths is None:
        raise KeyError(f"split {split!r} not found in {split_path}")
    return [str(Path(path).expanduser()) for path in paths]


def save_stats(stats: DatasetStats, path: str) -> None:
    output = Path(path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(stats.to_json_dict(), indent=2, sort_keys=True) + "\n")


def load_stats(path: str) -> DatasetStats:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        return DatasetStats.from_mapping(json.load(handle))


def _metadata_from_npz(data: Mapping[str, np.ndarray]) -> Dict[str, object]:
    raw = data["metadata_json"]
    if isinstance(raw, np.ndarray):
        raw = raw.item()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(str(raw))


def _safe_std(values: np.ndarray, eps: float = 1e-6, fallback: float = 1.0) -> np.ndarray:
    std = values.std(axis=0).astype(np.float32)
    std[std < eps] = float(fallback)
    return std


def _finite_array(data: Mapping[str, np.ndarray], key: str) -> np.ndarray:
    arr = np.asarray(data[key], dtype=np.float32)
    if not np.isfinite(arr).all():
        raise ValueError(f"{key} contains NaN/Inf and cannot be used for training")
    return arr


def _quat_to_rotmat_xyzw(quat: np.ndarray) -> np.ndarray:
    x, y, z, w = [float(v) for v in quat]
    norm = x * x + y * y + z * z + w * w
    if norm < 1e-12:
        return np.eye(3, dtype=np.float32)
    scale = 2.0 / norm
    xx = x * x * scale
    yy = y * y * scale
    zz = z * z * scale
    xy = x * y * scale
    xz = x * z * scale
    yz = y * z * scale
    wx = w * x * scale
    wy = w * y * scale
    wz = w * z * scale
    return np.asarray(
        [
            [1.0 - yy - zz, xy - wz, xz + wy],
            [xy + wz, 1.0 - xx - zz, yz - wx],
            [xz - wy, yz + wx, 1.0 - xx - yy],
        ],
        dtype=np.float32,
    )


def _position_in_base_frame(world_pose: np.ndarray, base_pose: np.ndarray) -> np.ndarray:
    if world_pose.shape[1] < 3 or base_pose.shape[1] < 7:
        raise ValueError("world_pose must have xyz and base_pose must have xyz+quat")
    output = np.zeros((world_pose.shape[0], 3), dtype=np.float32)
    for idx in range(world_pose.shape[0]):
        rot = _quat_to_rotmat_xyzw(base_pose[idx, 3:7])
        output[idx] = rot.T.dot(world_pose[idx, :3] - base_pose[idx, :3])
    return output


class UVMSEpisodeDataset(Dataset):
    """Windowed state-based dataset for BC/DP/FM smoke training."""

    def __init__(
        self,
        episode_paths: Sequence[str],
        obs_horizon: int = 4,
        action_horizon: int = 16,
        observation_keys: Sequence[str] = DEFAULT_OBSERVATION_KEYS,
        action_key: str = "action_ee_delta",
        stride: int = 1,
        normalize: bool = True,
        stats: Optional[DatasetStats] = None,
        include_progress: bool = True,
        require_action_available: bool = True,
        allow_fallback_dataset: bool = False,
        action_dim_indices: Optional[Sequence[int]] = None,
        obs_std_epsilon: float = 1e-6,
        obs_std_fallback: float = 1.0,
        action_std_epsilon: float = 1e-6,
        action_std_fallback: float = 1.0,
    ) -> None:
        if obs_horizon <= 0:
            raise ValueError("obs_horizon must be positive")
        if action_horizon <= 0:
            raise ValueError("action_horizon must be positive")
        if stride <= 0:
            raise ValueError("stride must be positive")

        self.episode_paths = [Path(path).expanduser() for path in episode_paths]
        self.obs_horizon = int(obs_horizon)
        self.action_horizon = int(action_horizon)
        self.observation_keys = tuple(observation_keys)
        self.action_key = action_key
        self.stride = int(stride)
        self.normalize = bool(normalize)
        self.include_progress = bool(include_progress)
        self.require_action_available = bool(require_action_available)
        self.allow_fallback_dataset = bool(allow_fallback_dataset)
        self.obs_std_epsilon = float(obs_std_epsilon)
        self.obs_std_fallback = float(obs_std_fallback)
        self.action_std_epsilon = float(action_std_epsilon)
        self.action_std_fallback = float(action_std_fallback)
        if action_dim_indices is None:
            self.action_dim_indices = None
        else:
            self.action_dim_indices = tuple(int(index) for index in action_dim_indices)
            if not self.action_dim_indices:
                raise ValueError("action_dim_indices must not be empty")

        self.episodes: List[Dict[str, object]] = []
        self.index: List[Tuple[int, int]] = []
        self.feature_names: List[str] = []
        self._load_episodes()
        self.stats = stats if stats is not None else self.compute_stats()

    @classmethod
    def from_config(
        cls,
        dataset_cfg: Mapping[str, object],
        split: str,
        stats: Optional[DatasetStats] = None,
    ) -> "UVMSEpisodeDataset":
        split_file = str(dataset_cfg["split_file"])
        paths = load_split_paths(split_file, split)
        return cls(
            episode_paths=paths,
            obs_horizon=int(dataset_cfg.get("obs_horizon", 4)),
            action_horizon=int(dataset_cfg.get("action_horizon", 16)),
            observation_keys=dataset_cfg.get("observation_keys", DEFAULT_OBSERVATION_KEYS),
            action_key=str(dataset_cfg.get("action_key", "action_ee_delta")),
            stride=int(dataset_cfg.get("stride", 1)),
            normalize=bool(dataset_cfg.get("normalize", True)),
            stats=stats,
            include_progress=bool(dataset_cfg.get("include_progress", True)),
            require_action_available=bool(dataset_cfg.get("require_action_available", True)),
            allow_fallback_dataset=bool(dataset_cfg.get("allow_fallback_dataset", False)),
            action_dim_indices=dataset_cfg.get("action_dim_indices"),
            obs_std_epsilon=float(dataset_cfg.get("obs_std_epsilon", 1e-6)),
            obs_std_fallback=float(dataset_cfg.get("obs_std_fallback", 1.0)),
            action_std_epsilon=float(dataset_cfg.get("action_std_epsilon", 1e-6)),
            action_std_fallback=float(dataset_cfg.get("action_std_fallback", 1.0)),
        )

    @property
    def obs_dim(self) -> int:
        return int(self.episodes[0]["obs"].shape[1])

    @property
    def action_dim(self) -> int:
        return int(self.episodes[0]["action"].shape[1])

    def _load_episodes(self) -> None:
        if not self.episode_paths:
            raise ValueError("no episode paths provided")

        for path in self.episode_paths:
            if not path.exists():
                raise FileNotFoundError(path)
            with np.load(str(path), allow_pickle=False) as loaded:
                data = {key: loaded[key] for key in loaded.files}

            metadata = _metadata_from_npz(data)
            if metadata.get("use_images") is not False:
                raise ValueError(f"{path} is not a first-version state-only episode")
            if metadata.get("active_arm") != "left":
                raise ValueError(f"{path} active_arm is not left")

            if self.require_action_available:
                field_availability = metadata.get("field_availability", {}) or {}
                if field_availability.get(self.action_key) is False:
                    raise ValueError(f"{path} action field is marked unavailable")

            if not self.allow_fallback_dataset:
                sources = (
                    metadata.get("base_state_source"),
                    metadata.get("joint_state_source"),
                    metadata.get("target_state_source"),
                )
                if any("fallback" in str(source) for source in sources):
                    raise ValueError(
                        f"{path} uses fallback state sources; set allow_fallback_dataset=true"
                    )

            derived_cache: Dict[str, np.ndarray] = {}
            obs_parts = []
            feature_names = []
            for key in self.observation_keys:
                if key in DERIVED_OBSERVATION_DIMS:
                    if not derived_cache:
                        base_pose = _finite_array(data, "base_pose")
                        eef_pose = _finite_array(data, "eef_pose")
                        target_pose = _finite_array(data, "target_pose")
                        eef_base = _position_in_base_frame(eef_pose, base_pose)
                        target_base = _position_in_base_frame(target_pose, base_pose)
                        derived_cache["eef_position_base_frame"] = eef_base
                        derived_cache["target_position_base_frame"] = target_base
                        derived_cache["target_to_eef_base_frame"] = target_base - eef_base
                    arr = derived_cache[key]
                else:
                    arr = _finite_array(data, key)
                if arr.ndim != 2:
                    raise ValueError(f"{path}:{key} must be [T,D], got {arr.shape}")
                obs_parts.append(arr)
                feature_names.extend([f"{key}/{idx}" for idx in range(arr.shape[1])])

            timestamp = _finite_array(data, "timestamp")
            t_count = int(timestamp.shape[0])
            if self.include_progress:
                denom = max(t_count - 1, 1)
                progress = (np.arange(t_count, dtype=np.float32) / float(denom)).reshape(-1, 1)
                remaining = (1.0 - progress).astype(np.float32)
                obs_parts.extend([progress, remaining])
                feature_names.extend(["episode_progress", "episode_remaining"])

            obs = np.concatenate(obs_parts, axis=1).astype(np.float32)
            action = _finite_array(data, self.action_key)
            if action.ndim != 2:
                raise ValueError(f"{path}:{self.action_key} must be [T,A], got {action.shape}")
            if self.action_dim_indices is not None:
                if min(self.action_dim_indices) < 0 or max(self.action_dim_indices) >= action.shape[1]:
                    raise ValueError(
                        f"{path}:{self.action_key} action_dim_indices={self.action_dim_indices} "
                        f"out of range for action_dim={action.shape[1]}"
                    )
                action = action[:, self.action_dim_indices]
            if obs.shape[0] != action.shape[0]:
                raise ValueError(f"{path} obs/action T mismatch")
            if obs.shape[0] < self.obs_horizon:
                raise ValueError(f"{path} T={obs.shape[0]} is shorter than obs_horizon")

            if not self.feature_names:
                self.feature_names = feature_names
            elif self.feature_names != feature_names:
                raise ValueError(f"{path} feature layout differs from previous episodes")

            episode_index = len(self.episodes)
            self.episodes.append(
                {
                    "path": str(path),
                    "obs": obs,
                    "action": action.astype(np.float32),
                    "metadata": metadata,
                    "T": obs.shape[0],
                }
            )
            for end_idx in range(self.obs_horizon - 1, obs.shape[0], self.stride):
                self.index.append((episode_index, end_idx))

        if not self.index:
            raise ValueError("no training windows could be generated")

    def compute_stats(self) -> DatasetStats:
        obs_values = []
        action_values = []
        for episode_idx, end_idx in self.index:
            episode = self.episodes[episode_idx]
            obs_values.append(episode["obs"][end_idx - self.obs_horizon + 1 : end_idx + 1])
            chunk, mask = self._raw_action_chunk(episode, end_idx)
            action_values.append(chunk[mask])
        obs_flat = np.concatenate([arr.reshape(-1, arr.shape[-1]) for arr in obs_values], axis=0)
        action_flat = np.concatenate(action_values, axis=0)
        return DatasetStats(
            obs_mean=obs_flat.mean(axis=0).astype(np.float32),
            obs_std=_safe_std(
                obs_flat,
                eps=self.obs_std_epsilon,
                fallback=self.obs_std_fallback,
            ),
            action_mean=action_flat.mean(axis=0).astype(np.float32),
            action_std=_safe_std(
                action_flat,
                eps=self.action_std_epsilon,
                fallback=self.action_std_fallback,
            ),
        )

    def _raw_action_chunk(self, episode: Mapping[str, object], end_idx: int) -> Tuple[np.ndarray, np.ndarray]:
        action = episode["action"]
        start = end_idx
        stop = min(start + self.action_horizon, action.shape[0])
        valid = action[start:stop]
        chunk = np.zeros((self.action_horizon, action.shape[1]), dtype=np.float32)
        mask = np.zeros((self.action_horizon,), dtype=bool)
        chunk[: valid.shape[0]] = valid
        mask[: valid.shape[0]] = True
        return chunk, mask

    def __len__(self) -> int:
        return len(self.index)

    def __getitem__(self, idx: int) -> Dict[str, object]:
        episode_idx, end_idx = self.index[idx]
        episode = self.episodes[episode_idx]
        obs = episode["obs"][end_idx - self.obs_horizon + 1 : end_idx + 1].copy()
        action, mask = self._raw_action_chunk(episode, end_idx)

        if self.normalize:
            obs = (obs - self.stats.obs_mean) / self.stats.obs_std
            action = (action - self.stats.action_mean) / self.stats.action_std
            action[~mask] = 0.0

        return {
            "obs": torch.from_numpy(obs.astype(np.float32)),
            "action": torch.from_numpy(action.astype(np.float32)),
            "action_mask": torch.from_numpy(mask.astype(np.float32)),
            "episode_path": str(episode["path"]),
            "end_idx": torch.tensor(end_idx, dtype=torch.long),
        }
