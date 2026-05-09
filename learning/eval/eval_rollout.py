#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Dict, List

import numpy as np
import torch
import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from learning.datasets.uvms_episode_dataset import UVMSEpisodeDataset  # noqa: E402
from learning.eval.policy_runtime import RuntimePolicy, choose_device  # noqa: E402


def load_config(path: str) -> Dict[str, object]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle) or {}
    if not isinstance(cfg, dict):
        raise ValueError("config must be a YAML mapping")
    return cfg


def clip_action_chunk(action: np.ndarray, safety_cfg: Dict[str, object]) -> np.ndarray:
    clipped = np.asarray(action, dtype=np.float64).copy()
    max_linear = float(safety_cfg.get("max_linear_delta", 0.03))
    max_angular = float(safety_cfg.get("max_angular_delta", 0.15))
    clipped[..., :3] = np.clip(clipped[..., :3], -max_linear, max_linear)
    clipped[..., 3:6] = np.clip(clipped[..., 3:6], -max_angular, max_angular)
    clipped[..., 6] = np.clip(
        clipped[..., 6],
        float(safety_cfg.get("min_gripper_cmd", 0.0)),
        float(safety_cfg.get("max_gripper_cmd", 1.0)),
    )
    return clipped


def action_smoothness(action: np.ndarray, mask: np.ndarray) -> float:
    valid = action[mask.astype(bool)]
    if valid.shape[0] < 2:
        return 0.0
    diffs = np.diff(valid, axis=0)
    return float(np.mean(np.linalg.norm(diffs, axis=1)))


def load_raw_dataset(policy: RuntimePolicy, split: str) -> UVMSEpisodeDataset:
    dataset_cfg = dict((policy.checkpoint.get("config", {}) or {}).get("dataset", {}) or {})
    dataset_cfg["normalize"] = False
    return UVMSEpisodeDataset.from_config(dataset_cfg, split=split)


def evaluate_policy(
    name: str,
    policy_cfg: Dict[str, object],
    cfg: Dict[str, object],
    device: torch.device,
) -> Dict[str, object]:
    started = time.perf_counter()
    result = {
        "policy": name,
        "policy_type": policy_cfg.get("policy_type", "auto"),
        "checkpoint": policy_cfg.get("checkpoint", ""),
        "checkpoint_loaded": False,
        "generated_action_chunk": False,
        "success_rate": None,
        "final_distance_to_target": None,
        "episode_length": None,
        "action_smoothness": None,
        "mean_inference_latency_ms": None,
        "max_inference_latency_ms": None,
        "failure_reason": "",
    }
    try:
        policy = RuntimePolicy.from_checkpoint(
            str(policy_cfg["checkpoint"]),
            device=device,
            policy_type=str(policy_cfg.get("policy_type", "auto")),
        )
        result["policy_type"] = policy.policy_type
        result["checkpoint_loaded"] = True

        eval_cfg = cfg.get("evaluation", {}) or {}
        split = str(eval_cfg.get("offline_split", "val"))
        max_windows = int(eval_cfg.get("num_eval_windows", 8))
        dataset = load_raw_dataset(policy, split=split)
        count = min(max_windows, len(dataset))
        if count <= 0:
            raise RuntimeError("no evaluation windows available")

        latencies = []
        smoothness_values = []
        clip_changes = []
        valid_lengths = []
        safety_cfg = cfg.get("safety", {}) or {}
        for index in range(count):
            item = dataset[index]
            obs = item["obs"].numpy()
            target = item["action"].numpy()
            mask = item["action_mask"].numpy().astype(bool)
            start = time.perf_counter()
            pred, _ = policy.predict_action_chunk(
                obs,
                num_inference_steps=policy_cfg.get("num_inference_steps"),
                ode_steps=policy_cfg.get("ode_steps"),
            )
            latencies.append((time.perf_counter() - start) * 1000.0)
            clipped = clip_action_chunk(pred, safety_cfg)
            clip_changes.append(float(np.mean(np.abs(clipped - pred) > 1e-8)))
            smoothness_values.append(action_smoothness(clipped, mask))
            valid_lengths.append(int(mask.sum()))
            _ = target  # kept explicit: target is available for future rollout-aligned metrics.

        result.update(
            {
                "generated_action_chunk": True,
                "success_rate": None,
                "final_distance_to_target": None,
                "episode_length": float(np.mean(valid_lengths)),
                "action_smoothness": float(np.mean(smoothness_values)),
                "mean_inference_latency_ms": float(np.mean(latencies)),
                "max_inference_latency_ms": float(np.max(latencies)),
                "clip_fraction": float(np.mean(clip_changes)),
                "evaluated_windows": int(count),
                "failure_reason": "dry_run_no_sim_rollout_controller_mapping_unconfirmed",
            }
        )
    except Exception as exc:
        result["failure_reason"] = f"exception:{type(exc).__name__}:{exc}"
    result["wall_time_sec"] = float(time.perf_counter() - started)
    return result


def write_markdown(results: List[Dict[str, object]], path: Path) -> None:
    headers = [
        "policy",
        "type",
        "loaded",
        "generated",
        "success_rate",
        "final_distance",
        "episode_length",
        "smoothness",
        "mean_latency_ms",
        "failure_reason",
    ]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for item in results:
        row = [
            str(item.get("policy")),
            str(item.get("policy_type")),
            str(item.get("checkpoint_loaded")),
            str(item.get("generated_action_chunk")),
            "not_evaluated" if item.get("success_rate") is None else f"{item.get('success_rate'):.3f}",
            "unavailable" if item.get("final_distance_to_target") is None else f"{item.get('final_distance_to_target'):.4f}",
            "unavailable" if item.get("episode_length") is None else f"{item.get('episode_length'):.2f}",
            "unavailable" if item.get("action_smoothness") is None else f"{item.get('action_smoothness'):.6f}",
            "unavailable"
            if item.get("mean_inference_latency_ms") is None
            else f"{item.get('mean_inference_latency_ms'):.3f}",
            str(item.get("failure_reason", "")),
        ]
        lines.append("| " + " | ".join(row) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified rollout/dry-run evaluation for BC, DP, and FM.")
    parser.add_argument(
        "--config",
        default=str(PACKAGE_ROOT / "config" / "eval_rollout.yaml"),
        help="Path to eval_rollout.yaml.",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    seed = int(cfg.get("seed", 10))
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    device = choose_device(str(cfg.get("device", "auto")))

    policies = cfg.get("policies", {}) or {}
    results = []
    for name, policy_cfg in policies.items():
        results.append(evaluate_policy(name, dict(policy_cfg or {}), cfg, device))

    output_dir = Path(str((cfg.get("evaluation", {}) or {}).get("output_dir", "outputs/eval/stage10_rollout"))).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "mode": (cfg.get("evaluation", {}) or {}).get("mode", "dry_run_offline"),
        "device": str(device),
        "results": results,
        "notes": (
            "Stage 10 dry-run loads policies and generates clipped action chunks. "
            "Real Gazebo rollout success is blocked until left-arm/gripper command "
            "interfaces, eef_pose, and non-fallback live-state data are fixed."
        ),
    }
    json_path = output_dir / "rollout_eval_summary.json"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if bool((cfg.get("evaluation", {}) or {}).get("write_markdown", True)):
        write_markdown(results, output_dir / "rollout_eval_summary.md")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
