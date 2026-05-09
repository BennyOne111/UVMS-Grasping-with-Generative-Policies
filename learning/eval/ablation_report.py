#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path
import sys
import time
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
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


def load_json(path: str) -> Dict[str, object]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def markdown_table(rows: List[Dict[str, object]], fieldnames: List[str]) -> str:
    lines = [
        "| " + " | ".join(fieldnames) + " |",
        "| " + " | ".join(["---"] * len(fieldnames)) + " |",
    ]
    for row in rows:
        values = []
        for key in fieldnames:
            value = row.get(key, "")
            if isinstance(value, float):
                values.append(f"{value:.6f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def load_raw_dataset(policy: RuntimePolicy, split: str) -> UVMSEpisodeDataset:
    dataset_cfg = dict((policy.checkpoint.get("config", {}) or {}).get("dataset", {}) or {})
    dataset_cfg["normalize"] = False
    return UVMSEpisodeDataset.from_config(dataset_cfg, split=split)


def masked_mse_np(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> float:
    valid = mask.astype(bool)
    if not valid.any():
        return 0.0
    return float(np.mean((pred[valid] - target[valid]) ** 2))


def action_smoothness(pred: np.ndarray, mask: np.ndarray) -> float:
    valid = pred[mask.astype(bool)]
    if valid.shape[0] < 2:
        return 0.0
    return float(np.mean(np.linalg.norm(np.diff(valid, axis=0), axis=1)))


def evaluate_sampling_variant(
    policy: RuntimePolicy,
    dataset: UVMSEpisodeDataset,
    max_windows: int,
    num_inference_steps: Optional[int] = None,
    ode_steps: Optional[int] = None,
) -> Dict[str, float]:
    latencies = []
    norm_mse = []
    action_mse = []
    smoothness = []
    count = min(max_windows, len(dataset))
    for idx in range(count):
        item = dataset[idx]
        obs = item["obs"].numpy()
        target = item["action"].numpy()
        mask = item["action_mask"].numpy().astype(bool)
        start = time.perf_counter()
        pred, _ = policy.predict_action_chunk(
            obs,
            num_inference_steps=num_inference_steps,
            ode_steps=ode_steps,
        )
        latencies.append((time.perf_counter() - start) * 1000.0)
        pred_norm = (pred - policy.stats.action_mean.reshape(1, -1)) / policy.stats.action_std.reshape(1, -1)
        target_norm = (target - policy.stats.action_mean.reshape(1, -1)) / policy.stats.action_std.reshape(1, -1)
        norm_mse.append(masked_mse_np(pred_norm, target_norm, mask))
        action_mse.append(masked_mse_np(pred, target, mask))
        smoothness.append(action_smoothness(pred, mask))
    return {
        "evaluated_windows": float(count),
        "normalized_mse": float(np.mean(norm_mse)),
        "action_mse": float(np.mean(action_mse)),
        "mean_latency_ms": float(np.mean(latencies)),
        "max_latency_ms": float(np.max(latencies)),
        "action_smoothness": float(np.mean(smoothness)),
    }


def collect_policy_table(cfg: Dict[str, object], rollout_summary: Dict[str, object]) -> List[Dict[str, object]]:
    rollout_by_policy = {
        str(item.get("policy")): item for item in rollout_summary.get("results", [])
    }
    rows = []
    for name, policy_cfg in (cfg.get("policies", {}) or {}).items():
        offline = load_json(str(policy_cfg["offline_eval_json"]))
        rollout = rollout_by_policy.get(name, {})
        rows.append(
            {
                "policy": name,
                "policy_type": policy_cfg.get("policy_type", name),
                "dataset_episodes": 20,
                "action_horizon": 16,
                "val_normalized_mse": float(offline.get("normalized_mse", np.nan)),
                "val_action_mse": float(offline.get("action_mse", np.nan)),
                "dry_run_latency_ms": float(rollout.get("mean_inference_latency_ms", np.nan)),
                "dry_run_smoothness": float(rollout.get("action_smoothness", np.nan)),
                "success_rate": "not_evaluated",
                "failure_reason": rollout.get(
                    "failure_reason",
                    "dry_run_no_sim_rollout_controller_mapping_unconfirmed",
                ),
                "checkpoint": policy_cfg.get("checkpoint", ""),
            }
        )
    return rows


def collect_inference_ablation(cfg: Dict[str, object], device: torch.device) -> List[Dict[str, object]]:
    rows = []
    split = str((cfg.get("dataset", {}) or {}).get("split", "val"))
    max_windows = int((cfg.get("dataset", {}) or {}).get("max_windows", 28))
    for name, policy_cfg in (cfg.get("policies", {}) or {}).items():
        if name == "bc":
            continue
        policy = RuntimePolicy.from_checkpoint(
            str(policy_cfg["checkpoint"]),
            device=device,
            policy_type=str(policy_cfg.get("policy_type", "auto")),
        )
        dataset = load_raw_dataset(policy, split=split)
        if name == "diffusion":
            for steps in policy_cfg.get("inference_steps", []):
                metrics = evaluate_sampling_variant(
                    policy,
                    dataset,
                    max_windows=max_windows,
                    num_inference_steps=int(steps),
                )
                rows.append({"policy": name, "steps": int(steps), "step_type": "num_inference_steps", **metrics})
        elif name == "flow_matching":
            for steps in policy_cfg.get("ode_steps", []):
                metrics = evaluate_sampling_variant(
                    policy,
                    dataset,
                    max_windows=max_windows,
                    ode_steps=int(steps),
                )
                rows.append({"policy": name, "steps": int(steps), "step_type": "ode_steps", **metrics})
    return rows


def planned_ablation_rows(cfg: Dict[str, object]) -> List[Dict[str, object]]:
    planned = cfg.get("planned_ablations", {}) or {}
    rows = []
    for episodes in planned.get("data_episodes", []):
        rows.append(
            {
                "ablation": "data_volume",
                "setting": f"{episodes}_episodes",
                "status": "completed" if int(episodes) == 20 else "not_run",
                "reason": (
                    "Stage 6 fallback debug dataset exists"
                    if int(episodes) == 20
                    else "requires additional non-fallback episode collection and retraining"
                ),
            }
        )
    for horizon in planned.get("action_horizon", []):
        rows.append(
            {
                "ablation": "action_horizon",
                "setting": f"{horizon}",
                "status": "completed" if int(horizon) == 16 else "not_run",
                "reason": (
                    "current BC/DP/FM checkpoints use action_horizon=16"
                    if int(horizon) == 16
                    else "requires retraining with a different action_horizon"
                ),
            }
        )
    disturbance = planned.get("disturbance", {}) or {}
    for variant in disturbance.get("variants", []):
        rows.append(
            {
                "ablation": "disturbance",
                "setting": variant,
                "status": "not_run",
                "reason": disturbance.get(
                    "note",
                    "requires official Project DAVE ocean current config verification",
                ),
            }
        )
    return rows


def plot_bar(rows: List[Dict[str, object]], key: str, ylabel: str, output_path: Path) -> None:
    labels = [str(row["policy"]) for row in rows]
    values = [float(row[key]) for row in rows]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, values, color=["#4c78a8", "#f58518", "#54a24b"][: len(labels)])
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(str(output_path), dpi=150)
    plt.close(fig)


def plot_inference_ablation(rows: List[Dict[str, object]], output_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for policy in sorted(set(row["policy"] for row in rows)):
        subset = [row for row in rows if row["policy"] == policy]
        x = [int(row["steps"]) for row in subset]
        axes[0].plot(x, [float(row["action_mse"]) for row in subset], marker="o", label=policy)
        axes[1].plot(x, [float(row["mean_latency_ms"]) for row in subset], marker="o", label=policy)
        axes[2].plot(x, [float(row["action_smoothness"]) for row in subset], marker="o", label=policy)
    axes[0].set_xlabel("steps")
    axes[0].set_ylabel("val action MSE")
    axes[1].set_xlabel("steps")
    axes[1].set_ylabel("mean latency ms")
    axes[2].set_xlabel("steps")
    axes[2].set_ylabel("action smoothness")
    for ax in axes:
        ax.grid(True, alpha=0.3)
        ax.legend()
    fig.tight_layout()
    fig.savefig(str(output_path), dpi=150)
    plt.close(fig)


def plot_success_status(rows: List[Dict[str, object]], output_path: Path) -> None:
    labels = [str(row["policy"]) for row in rows]
    values = [0.0 for _ in rows]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, values, color="#bab0ac")
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("success rate")
    ax.set_title("Success rate not evaluated: controller mapping unconfirmed")
    for idx, _ in enumerate(labels):
        ax.text(idx, 0.05, "N/A", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(str(output_path), dpi=150)
    plt.close(fig)


def write_summary(
    output_dir: Path,
    policy_rows: List[Dict[str, object]],
    inference_rows: List[Dict[str, object]],
    planned_rows: List[Dict[str, object]],
) -> Dict[str, object]:
    policy_fields = [
        "policy",
        "policy_type",
        "dataset_episodes",
        "action_horizon",
        "val_normalized_mse",
        "val_action_mse",
        "dry_run_latency_ms",
        "dry_run_smoothness",
        "success_rate",
        "failure_reason",
        "checkpoint",
    ]
    inference_fields = [
        "policy",
        "step_type",
        "steps",
        "normalized_mse",
        "action_mse",
        "mean_latency_ms",
        "max_latency_ms",
        "action_smoothness",
        "evaluated_windows",
    ]
    planned_fields = ["ablation", "setting", "status", "reason"]
    write_csv(output_dir / "policy_comparison.csv", policy_rows, policy_fields)
    write_csv(output_dir / "inference_steps_ablation.csv", inference_rows, inference_fields)
    write_csv(output_dir / "planned_ablation_status.csv", planned_rows, planned_fields)

    (output_dir / "policy_comparison.md").write_text(
        markdown_table(policy_rows, policy_fields),
        encoding="utf-8",
    )
    (output_dir / "inference_steps_ablation.md").write_text(
        markdown_table(inference_rows, inference_fields),
        encoding="utf-8",
    )
    (output_dir / "planned_ablation_status.md").write_text(
        markdown_table(planned_rows, planned_fields),
        encoding="utf-8",
    )

    plot_bar(policy_rows, "val_action_mse", "val action MSE", output_dir / "policy_action_mse_comparison.png")
    plot_bar(policy_rows, "dry_run_latency_ms", "mean latency ms", output_dir / "policy_latency_comparison.png")
    plot_bar(policy_rows, "dry_run_smoothness", "action smoothness", output_dir / "policy_smoothness_comparison.png")
    plot_inference_ablation(inference_rows, output_dir / "inference_steps_mse_latency.png")
    plot_success_status(policy_rows, output_dir / "success_rate_status.png")

    dp_base = next(row for row in policy_rows if row["policy"] == "diffusion")
    fm_base = next(row for row in policy_rows if row["policy"] == "flow_matching")
    conclusion = (
        "On the Stage 6 fallback validation split, Flow Matching produced lower "
        f"action MSE ({fm_base['val_action_mse']:.6f}) than Diffusion "
        f"({dp_base['val_action_mse']:.6f}) and lower dry-run latency "
        f"({fm_base['dry_run_latency_ms']:.3f} ms vs {dp_base['dry_run_latency_ms']:.3f} ms). "
        "This is a pipeline-only conclusion, not a real grasp-performance claim."
    )
    summary = {
        "policy_comparison": policy_rows,
        "inference_steps_ablation": inference_rows,
        "planned_ablation_status": planned_rows,
        "core_dp_vs_fm_conclusion": conclusion,
        "limitations": [
            "Only 20 fallback episodes are available.",
            "No real Gazebo arm rollout success rate is available.",
            "50/100/300 episode, horizon, and disturbance ablations require new collection/training.",
        ],
    }
    (output_dir / "ablation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = [
        "# Stage 11 Ablation Summary",
        "",
        "## BC / DP / FM Comparison",
        "",
        markdown_table(policy_rows, policy_fields),
        "## DP / FM Inference-Step Ablation",
        "",
        markdown_table(inference_rows, inference_fields),
        "## Planned Ablations",
        "",
        markdown_table(planned_rows, planned_fields),
        "## Core Conclusion",
        "",
        conclusion,
        "",
        "## Limitations",
        "",
        "- Results use the Stage 6 nominal fallback dataset.",
        "- Success rate and final distance are not evaluated until real controller rollout is enabled.",
        "- Disturbance ablation was not run because DAVE ocean-current configuration must be verified from official documentation first.",
    ]
    (output_dir / "ablation_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Stage 11 ablation tables and plots.")
    parser.add_argument(
        "--config",
        default=str(PACKAGE_ROOT / "config" / "ablation_report.yaml"),
        help="Path to ablation_report.yaml.",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    seed = int(cfg.get("seed", 11))
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    device = choose_device(str(cfg.get("device", "auto")))
    output_dir = Path(str((cfg.get("outputs", {}) or {}).get("output_dir", "outputs/eval/stage11_ablation"))).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    rollout_summary = load_json(str(cfg["rollout_summary_json"]))
    policy_rows = collect_policy_table(cfg, rollout_summary)
    inference_rows = collect_inference_ablation(cfg, device)
    planned_rows = planned_ablation_rows(cfg)
    summary = write_summary(output_dir, policy_rows, inference_rows, planned_rows)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
