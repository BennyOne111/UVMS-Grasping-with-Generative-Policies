#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SRC = PACKAGE_ROOT / "src"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

from rexrov_single_oberon7_fm_dp.dataset_writer import (  # noqa: E402
    metadata_from_npz,
    validate_episode_file,
)


RANGE_KEYS = (
    "active_joint_positions",
    "active_joint_velocities",
    "gripper_state",
    "action_ee_delta",
    "target_pose",
)


def _finite_min_max(arrays: Sequence[np.ndarray]) -> Optional[Dict[str, object]]:
    finite_arrays = []
    for arr in arrays:
        values = np.asarray(arr, dtype=float)
        finite = values[np.isfinite(values)]
        if finite.size:
            finite_arrays.append(finite)
    if not finite_arrays:
        return None
    merged = np.concatenate(finite_arrays)
    return {
        "min": float(np.min(merged)),
        "max": float(np.max(merged)),
    }


def _per_dim_min_max(arrays: Sequence[np.ndarray]) -> Optional[Dict[str, List[float]]]:
    finite_arrays = []
    for arr in arrays:
        values = np.asarray(arr, dtype=float)
        if values.ndim == 1:
            values = values.reshape(-1, 1)
        if values.ndim != 2:
            continue
        finite_arrays.append(values)
    if not finite_arrays:
        return None
    merged = np.concatenate(finite_arrays, axis=0)
    mins = []
    maxs = []
    for col in range(merged.shape[1]):
        values = merged[:, col]
        finite = values[np.isfinite(values)]
        if finite.size:
            mins.append(float(np.min(finite)))
            maxs.append(float(np.max(finite)))
        else:
            mins.append(float("nan"))
            maxs.append(float("nan"))
    return {"min": mins, "max": maxs}


def _load_episode(path: Path) -> Tuple[Mapping[str, np.ndarray], Dict[str, object]]:
    with np.load(str(path), allow_pickle=False) as loaded:
        data = {key: loaded[key] for key in loaded.files}
    metadata = metadata_from_npz(data)
    return data, metadata


def summarize_dataset(
    input_dir: Path,
    pattern: str,
    allow_unavailable_nan: bool = True,
) -> Dict[str, object]:
    episode_paths = sorted(input_dir.glob(pattern))
    valid_paths: List[str] = []
    invalid: List[Dict[str, object]] = []
    success_values: List[bool] = []
    lengths: List[int] = []
    unavailable_counts: Dict[str, int] = {}
    availability_counts: Dict[str, Dict[str, int]] = {}
    range_values: Dict[str, List[np.ndarray]] = {key: [] for key in RANGE_KEYS}
    metadata_examples: List[Dict[str, object]] = []

    for path in episode_paths:
        validation = validate_episode_file(
            str(path),
            allow_unavailable_nan=allow_unavailable_nan,
        )
        if not validation.ok:
            invalid.append(
                {
                    "path": str(path),
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                }
            )
            continue

        data, metadata = _load_episode(path)
        valid_paths.append(str(path))
        success_values.append(bool(np.asarray(data["success"]).item()))
        lengths.append(int(np.asarray(data["timestamp"]).shape[0]))

        for field in metadata.get("unavailable_fields", []) or []:
            unavailable_counts[field] = unavailable_counts.get(field, 0) + 1

        field_availability = metadata.get("field_availability", {}) or {}
        for field, available in field_availability.items():
            counts = availability_counts.setdefault(field, {"available": 0, "unavailable": 0})
            if available:
                counts["available"] += 1
            else:
                counts["unavailable"] += 1

        for key in RANGE_KEYS:
            if key in data:
                range_values[key].append(np.asarray(data[key]))

        if len(metadata_examples) < 3:
            metadata_examples.append(
                {
                    "episode_id": metadata.get("episode_id"),
                    "target_model_name": metadata.get("target_model_name"),
                    "controller_type": metadata.get("controller_type"),
                    "rate_hz": metadata.get("rate_hz"),
                    "max_duration_sec": metadata.get("max_duration_sec"),
                }
            )

    ranges = {}
    per_dim_ranges = {}
    for key, arrays in range_values.items():
        ranges[key] = _finite_min_max(arrays)
        per_dim_ranges[key] = _per_dim_min_max(arrays)

    success_count = int(sum(success_values))
    valid_count = len(valid_paths)
    summary = {
        "input_dir": str(input_dir),
        "pattern": pattern,
        "episodes_total": len(episode_paths),
        "episodes_valid": valid_count,
        "episodes_invalid": len(invalid),
        "success_count": success_count,
        "success_rate": float(success_count / valid_count) if valid_count else 0.0,
        "length": {
            "mean_T": float(np.mean(lengths)) if lengths else 0.0,
            "min_T": int(np.min(lengths)) if lengths else 0,
            "max_T": int(np.max(lengths)) if lengths else 0,
        },
        "unavailable_field_counts": unavailable_counts,
        "field_availability_counts": availability_counts,
        "ranges": ranges,
        "per_dim_ranges": per_dim_ranges,
        "valid_episode_paths": valid_paths,
        "invalid_episodes": invalid,
        "metadata_examples": metadata_examples,
    }
    return summary


def write_markdown(summary: Mapping[str, object], output_path: Path) -> None:
    length = summary["length"]
    lines = [
        "# Dataset Summary",
        "",
        f"- Input dir: `{summary['input_dir']}`",
        f"- Pattern: `{summary['pattern']}`",
        f"- Episodes total: {summary['episodes_total']}",
        f"- Valid episodes: {summary['episodes_valid']}",
        f"- Invalid episodes: {summary['episodes_invalid']}",
        f"- Success count: {summary['success_count']}",
        f"- Success rate: {summary['success_rate']:.3f}",
        f"- Mean T: {length['mean_T']:.2f}",
        f"- Min/Max T: {length['min_T']} / {length['max_T']}",
        "",
        "## Unavailable Fields",
        "",
    ]
    unavailable = summary.get("unavailable_field_counts", {}) or {}
    if unavailable:
        for key, count in sorted(unavailable.items()):
            lines.append(f"- `{key}`: {count}")
    else:
        lines.append("- None")

    lines.extend(["", "## Ranges", ""])
    for key, value in sorted((summary.get("ranges", {}) or {}).items()):
        if value is None:
            lines.append(f"- `{key}`: no finite values")
        else:
            lines.append(f"- `{key}`: min={value['min']:.6g}, max={value['max']:.6g}")

    invalid = summary.get("invalid_episodes", []) or []
    if invalid:
        lines.extend(["", "## Invalid Episodes", ""])
        for item in invalid:
            lines.append(f"- `{item['path']}`: {item['errors']}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Stage 6 DP/FM episode datasets.")
    parser.add_argument("--input-dir", required=True, help="Directory containing episode .npz files.")
    parser.add_argument("--pattern", default="*.npz", help="Glob pattern under input-dir.")
    parser.add_argument("--output-json", default="", help="Optional JSON summary output path.")
    parser.add_argument("--output-md", default="", help="Optional Markdown summary output path.")
    parser.add_argument(
        "--strict-nan",
        action="store_true",
        help="Fail episodes with NaN even when metadata marks fields unavailable.",
    )
    args = parser.parse_args()

    summary = summarize_dataset(
        input_dir=Path(args.input_dir).expanduser(),
        pattern=args.pattern,
        allow_unavailable_nan=not args.strict_nan,
    )

    if args.output_json:
        output_json = Path(args.output_json).expanduser()
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.output_md:
        write_markdown(summary, Path(args.output_md).expanduser())

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["episodes_invalid"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
