#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, Mapping

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


EXPECTED_OBSERVATION_KEYS = [
    "active_joint_positions",
    "active_joint_velocities",
    "eef_position_base_frame",
    "target_position_base_frame",
    "target_to_eef_base_frame",
]


def _load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _candidate_config(seed: int) -> Path:
    suffix = "" if seed == 84 else f"_seed{seed}"
    return PACKAGE_ROOT / f"config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30{suffix}.yaml"


def _checkpoint_dir(seed: int) -> Path:
    suffix = "" if seed == 84 else f"_seed{seed}"
    return PACKAGE_ROOT / f"outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30{suffix}"


def _log_dir(seed: int) -> Path:
    suffix = "" if seed == 84 else f"_seed{seed}"
    return PACKAGE_ROOT / f"outputs/logs/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30{suffix}"


def _validate_config(path: Path, seed: int) -> Dict[str, object]:
    cfg = _load_yaml(path)
    dataset = cfg.get("dataset", {}) or {}
    outputs = cfg.get("outputs", {}) or {}
    checks = {
        "exists": path.exists(),
        "seed_matches": int(cfg.get("seed", -1)) == seed,
        "obs_horizon_h4": int(dataset.get("obs_horizon", -1)) == 4,
        "action_horizon_h8": int(dataset.get("action_horizon", -1)) == 8,
        "xyz_only": list(dataset.get("action_dim_indices", [])) == [0, 1, 2],
        "base_relative_observation": list(dataset.get("observation_keys", [])) == EXPECTED_OBSERVATION_KEYS,
        "no_fallback_dataset": dataset.get("allow_fallback_dataset") is False,
        "safe_action_std_fallback": float(dataset.get("action_std_fallback", -1.0)) == 0.001,
        "output_run_name_is_seeded": str(seed) in str(outputs.get("run_name", "")) if seed != 84 else True,
    }
    return {
        "path": str(path.relative_to(PACKAGE_ROOT)),
        "checks": checks,
        "passed": all(bool(v) for v in checks.values()),
    }


def _metric_by_key(validation: Mapping[str, object], key: str) -> Mapping[str, object]:
    for row in validation.get("candidates", []):
        if row.get("key") == key:
            return row
    raise KeyError(key)


def _train_command(config: Path) -> str:
    return (
        "python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/train/train_diffusion.py "
        f"--config src/uvms/rexrov_single_oberon7_fm_dp/{config.relative_to(PACKAGE_ROOT)}"
    )


def _eval_command(output_json: Path, output_md: Path) -> str:
    return (
        "python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/analyze_b8_dp30_seed_ablation_validation.py "
        f"--output-json src/uvms/rexrov_single_oberon7_fm_dp/{output_json.relative_to(PACKAGE_ROOT)} "
        f"--output-md src/uvms/rexrov_single_oberon7_fm_dp/{output_md.relative_to(PACKAGE_ROOT)}"
    )


def _write_md(payload: Mapping[str, object], path: Path) -> None:
    decision = payload["decision"]
    lines = [
        "# B8 DP30 Focused Offline Ablation Plan",
        "",
        "Scope: offline-only DP seed ablation under the exact base-relative",
        "safe-action-normalization setup used by the current BC reference. This",
        "plan does not run ROS, does not publish arm commands, does not train by",
        "itself, and does not approve DP/FM live execution.",
        "",
        "## Decision",
        "",
        "```text",
        f"dp_offline_ablation_can_continue={decision['dp_offline_ablation_can_continue']}",
        f"selected_axis={decision['selected_axis']}",
        f"dp_fm_live_approved={decision['dp_fm_live_approved']}",
        f"training_started={decision['training_started']}",
        f"bc_remains_live_reference={decision['bc_remains_live_reference']}",
        "```",
        "",
        "## Baseline",
        "",
        "```text",
        f"bc_action_mse={payload['baseline']['bc_action_mse']}",
        f"dp30_seed84_action_mse={payload['baseline']['dp30_seed84_action_mse']}",
        f"dp30_seed84_relative_to_bc={payload['baseline']['dp30_seed84_relative_to_bc']}",
        "```",
        "",
        "## Candidate Configs",
        "",
        "| seed | config | checkpoint_exists | config_ok |",
        "| ---: | --- | ---: | ---: |",
    ]
    for row in payload["candidates"]:
        lines.append(
            f"| {row['seed']} | `{row['config']['path']}` | "
            f"{row['checkpoint_exists']} | {row['config']['passed']} |"
        )
    lines.extend(
        [
            "",
            "## Runbook",
            "",
            "Run only if an offline training run is explicitly allowed for this",
            "bounded ablation. These commands do not start ROS and do not run live",
            "rollouts.",
            "",
            "```bash",
            "cd /home/benny/uuv_manipulator_ws",
            "source devel/setup.bash",
        ]
    )
    for cmd in payload["runbook"]["training_commands"]:
        lines.append(cmd)
    lines.extend(
        [
            payload["runbook"]["post_training_eval_command"],
            "```",
            "",
            "## Boundary",
            "",
            "- DP/FM live remains blocked.",
            "- BC remains the live reference until a DP/FM candidate beats BC offline",
            "  under the same setup and live readiness is separately reviewed.",
            "- No grasp success, learned rollout success, or general rollout success is",
            "  claimed by this plan.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan a focused offline-only DP30 seed ablation for B8'.")
    parser.add_argument(
        "--validation-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp_fm_validation_window_diagnostics.json",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp30_focused_offline_ablation_plan.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp30_focused_offline_ablation_plan.md",
    )
    parser.add_argument("--seeds", type=int, nargs="+", default=[84, 85, 86])
    args = parser.parse_args()

    validation = _load_json(args.validation_json)
    bc = _metric_by_key(validation, "bc_ref")
    dp30 = _metric_by_key(validation, "dp30_zero")

    candidates = []
    for seed in args.seeds:
        config_path = _candidate_config(seed)
        checkpoint_dir = _checkpoint_dir(seed)
        candidates.append(
            {
                "seed": seed,
                "config": _validate_config(config_path, seed),
                "checkpoint_dir": str(checkpoint_dir.relative_to(PACKAGE_ROOT)),
                "checkpoint_exists": (checkpoint_dir / "best.pt").exists(),
                "log_dir": str(_log_dir(seed).relative_to(PACKAGE_ROOT)),
            }
        )

    output_eval_json = PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.json"
    output_eval_md = PACKAGE_ROOT / "outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.md"
    training_commands = [
        _train_command(_candidate_config(seed))
        for seed in args.seeds
        if seed != 84
    ]

    payload = {
        "artifact": "dp30_focused_offline_ablation_plan",
        "offline_only": True,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "hand_controller_started": False,
        "training_started": False,
        "learned_rollout_run": False,
        "learned_rollout_success_claimed": False,
        "grasp_success_claimed": False,
        "baseline": {
            "validation_json": str(args.validation_json.relative_to(PACKAGE_ROOT)),
            "bc_action_mse": float(bc["action_mse"]),
            "dp30_seed84_action_mse": float(dp30["action_mse"]),
            "dp30_seed84_relative_to_bc": (float(dp30["action_mse"]) - float(bc["action_mse"]))
            / max(float(bc["action_mse"]), 1e-12),
        },
        "candidates": candidates,
        "runbook": {
            "training_commands": training_commands,
            "post_training_eval_command": _eval_command(output_eval_json, output_eval_md),
            "note": "post-training evaluation includes BC and every available DP30 seed checkpoint",
        },
        "decision": {
            "dp_offline_ablation_can_continue": True,
            "selected_axis": "diffusion_seed_only",
            "candidate_seeds": list(args.seeds),
            "dp_fm_live_approved": False,
            "full_dp_fm_training_as_success_approved": False,
            "training_started": False,
            "bc_remains_live_reference": True,
            "next_step_requires_explicit_training_approval": True,
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(payload, args.output_md)
    print(json.dumps(payload["decision"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
