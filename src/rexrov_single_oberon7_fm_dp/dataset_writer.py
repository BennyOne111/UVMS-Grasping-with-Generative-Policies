import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np


REQUIRED_KEYS = (
    "timestamp",
    "base_pose",
    "base_velocity",
    "active_joint_positions",
    "active_joint_velocities",
    "gripper_state",
    "target_pose",
    "action_ee_delta",
    "done",
    "success",
    "metadata_json",
)


TIME_SERIES_KEYS = (
    "timestamp",
    "base_pose",
    "base_velocity",
    "active_joint_positions",
    "active_joint_velocities",
    "gripper_state",
    "target_pose",
    "action_ee_delta",
    "done",
)


NAN_ALLOWED_WHEN_UNAVAILABLE = {
    "target_pose",
    "eef_pose",
    "relative_target_to_eef",
    "action_ee_delta",
    "raw_command",
}


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    summary: Dict[str, object] = field(default_factory=dict)

    def add_error(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def metadata_to_json(metadata: Mapping[str, object]) -> str:
    return json.dumps(metadata, sort_keys=True, indent=2)


def metadata_from_npz(data: Mapping[str, np.ndarray]) -> Dict[str, object]:
    raw = data["metadata_json"]
    if isinstance(raw, np.ndarray):
        raw = raw.item()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(str(raw))


def save_episode_npz(
    arrays: Mapping[str, np.ndarray],
    metadata: Mapping[str, object],
    output_dir: str,
    episode_id: str,
    save_sidecar_metadata: bool = True,
) -> Path:
    output_path = Path(output_dir).expanduser()
    output_path.mkdir(parents=True, exist_ok=True)

    episode_path = output_path / f"{episode_id}.npz"
    metadata_json = metadata_to_json(metadata)

    payload = dict(arrays)
    payload["metadata_json"] = np.array(metadata_json)
    payload["success"] = np.array(bool(metadata.get("success", False)))

    np.savez_compressed(str(episode_path), **payload)

    if save_sidecar_metadata:
        sidecar_path = output_path / f"{episode_id}.metadata.json"
        sidecar_path.write_text(metadata_json + "\n", encoding="utf-8")

    return episode_path


def stack_samples(samples: Sequence[Mapping[str, np.ndarray]]) -> Dict[str, np.ndarray]:
    if not samples:
        raise ValueError("cannot stack an empty episode")

    keys = sorted(samples[0].keys())
    arrays = {}
    for key in keys:
        arrays[key] = np.stack([np.asarray(sample[key]) for sample in samples], axis=0)
    return arrays


def _is_unavailable(metadata: Mapping[str, object], key: str) -> bool:
    unavailable_fields = set(metadata.get("unavailable_fields", []) or [])
    field_availability = metadata.get("field_availability", {}) or {}
    if key in unavailable_fields:
        return True
    return field_availability.get(key) is False


def _check_finite_or_unavailable(
    result: ValidationResult,
    data: Mapping[str, np.ndarray],
    metadata: Mapping[str, object],
    key: str,
) -> None:
    arr = np.asarray(data[key])
    finite = np.isfinite(arr)
    if finite.all():
        return
    if key in NAN_ALLOWED_WHEN_UNAVAILABLE and _is_unavailable(metadata, key):
        if np.isnan(arr).any():
            result.add_warning(f"{key} contains NaN because metadata marks it unavailable")
        if np.isinf(arr).any():
            result.add_error(f"{key} contains Inf even though it is marked unavailable")
        return
    result.add_error(f"{key} contains NaN or Inf")


def validate_episode_file(path: str, allow_unavailable_nan: bool = True) -> ValidationResult:
    result = ValidationResult(ok=True)
    episode_path = Path(path)
    if not episode_path.exists():
        result.add_error(f"file does not exist: {episode_path}")
        return result

    try:
        with np.load(str(episode_path), allow_pickle=False) as loaded:
            data = {key: loaded[key] for key in loaded.files}
    except Exception as exc:
        result.add_error(f"failed to load npz: {exc}")
        return result

    for key in REQUIRED_KEYS:
        if key not in data:
            result.add_error(f"missing required key: {key}")
    if not result.ok:
        return result

    try:
        metadata = metadata_from_npz(data)
    except Exception as exc:
        result.add_error(f"metadata_json is not valid JSON: {exc}")
        return result

    active_arm = metadata.get("active_arm")
    robot_mode = metadata.get("robot_mode")
    if active_arm != "left":
        result.add_error(f"metadata active_arm must be 'left', got {active_arm!r}")
    if robot_mode != "dual_model_single_active_left_arm":
        result.add_error(f"unexpected robot_mode: {robot_mode!r}")
    if metadata.get("use_images") is not False:
        result.add_error("metadata use_images must be false for first-version schema")

    timestamp = np.asarray(data["timestamp"])
    if timestamp.ndim != 1:
        result.add_error(f"timestamp must have shape [T], got {timestamp.shape}")
        return result
    t_count = int(timestamp.shape[0])
    if t_count <= 1:
        result.add_error(f"episode must contain at least 2 samples, got T={t_count}")

    for key in TIME_SERIES_KEYS:
        arr = np.asarray(data[key])
        if arr.shape[0] != t_count:
            result.add_error(f"{key} has T={arr.shape[0]}, expected {t_count}")

    expected_shapes: Iterable[Tuple[str, Tuple[int, ...]]] = (
        ("base_pose", (t_count, 7)),
        ("base_velocity", (t_count, 6)),
        ("target_pose", (t_count, 7)),
        ("action_ee_delta", (t_count, 7)),
        ("done", (t_count,)),
    )
    for key, expected in expected_shapes:
        if np.asarray(data[key]).shape != expected:
            result.add_error(f"{key} shape {np.asarray(data[key]).shape}, expected {expected}")

    active_joint_names = metadata.get("active_joint_names", []) or []
    gripper_joint_names = metadata.get("gripper_joint_names", []) or []
    if np.asarray(data["active_joint_positions"]).shape != (t_count, len(active_joint_names)):
        result.add_error(
            "active_joint_positions shape "
            f"{np.asarray(data['active_joint_positions']).shape}, expected {(t_count, len(active_joint_names))}"
        )
    if np.asarray(data["active_joint_velocities"]).shape != (t_count, len(active_joint_names)):
        result.add_error(
            "active_joint_velocities shape "
            f"{np.asarray(data['active_joint_velocities']).shape}, expected {(t_count, len(active_joint_names))}"
        )
    if np.asarray(data["gripper_state"]).shape != (t_count, len(gripper_joint_names)):
        result.add_error(
            f"gripper_state shape {np.asarray(data['gripper_state']).shape}, "
            f"expected {(t_count, len(gripper_joint_names))}"
        )

    if not np.isfinite(timestamp).all():
        result.add_error("timestamp contains NaN or Inf")
    elif np.any(np.diff(timestamp) < 0.0):
        result.add_error("timestamp is not monotonic nondecreasing")

    for key, arr in data.items():
        if key in ("metadata_json", "success", "eef_pose", "relative_target_to_eef", "raw_command"):
            continue
        if not np.issubdtype(np.asarray(arr).dtype, np.number) and key != "done":
            continue
        if allow_unavailable_nan:
            _check_finite_or_unavailable(result, data, metadata, key)
        elif not np.isfinite(np.asarray(arr)).all():
            result.add_error(f"{key} contains NaN or Inf")

    done = np.asarray(data["done"]).astype(bool)
    if done.shape != (t_count,):
        result.add_error(f"done shape {done.shape}, expected {(t_count,)}")
    elif not bool(done[-1]):
        result.add_error("done[-1] must be true")

    success_value = bool(np.asarray(data["success"]).item())
    if success_value != bool(metadata.get("success", False)):
        result.add_error("success scalar does not match metadata success")

    for key in ("eef_pose", "relative_target_to_eef", "raw_command"):
        if key in data:
            arr = np.asarray(data[key])
            if arr.shape[0] != t_count:
                result.add_error(f"{key} has T={arr.shape[0]}, expected {t_count}")
            if allow_unavailable_nan:
                _check_finite_or_unavailable(result, data, metadata, key)
            elif not np.isfinite(arr).all():
                result.add_error(f"{key} contains NaN or Inf")

    result.summary = {
        "path": str(episode_path),
        "T": t_count,
        "success": success_value,
        "episode_id": metadata.get("episode_id"),
        "unavailable_fields": metadata.get("unavailable_fields", []),
    }
    return result
