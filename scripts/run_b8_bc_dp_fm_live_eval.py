#!/usr/bin/env python3

import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PACKAGE_ROOT.parents[2]
REFERENCE_NPZ = PACKAGE_ROOT / "data/raw/b8_reaching_repeatability_smoke/b8_reaching_repeatability_smoke_0000.npz"


POLICIES = {
    "bc": {
        "checkpoint": PACKAGE_ROOT / "outputs/checkpoints/b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt",
        "policy_type": "auto",
        "num_inference_steps": 50,
        "ode_steps": 50,
    },
    "dp": {
        "checkpoint": PACKAGE_ROOT
        / "outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86/best.pt",
        "policy_type": "auto",
        "num_inference_steps": 50,
        "ode_steps": 50,
    },
    "fm": {
        "checkpoint": PACKAGE_ROOT
        / "outputs/checkpoints/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_epoch30_action_select/best_action.pt",
        "policy_type": "auto",
        "num_inference_steps": 50,
        "ode_steps": 50,
    },
}


def _run(cmd: List[str], log_path: Path, allow_fail: bool = False, timeout: Optional[float] = None) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write("$ " + " ".join(cmd) + "\n\n")
        handle.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=str(WORKSPACE_ROOT),
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            handle.write(f"\nTIMEOUT after {timeout} sec; terminating process group.\n")
            handle.flush()
            try:
                os.killpg(proc.pid, signal.SIGINT)
                proc.wait(timeout=5.0)
            except Exception:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=5.0)
            if allow_fail:
                return 124
            raise
    if proc.returncode != 0 and not allow_fail:
        raise RuntimeError(f"command failed rc={proc.returncode}: {' '.join(cmd)}")
    return int(proc.returncode)


def _bash(command: str) -> List[str]:
    return ["bash", "-lc", f"source devel/setup.bash; {command}"]


def _load_json(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _return_to_reference(cycle_dir: Path) -> bool:
    cmd = (
        "python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/return_left_arm_to_reference.py "
        f"--reference-npz {REFERENCE_NPZ} "
        "--max-joint-delta 0.01 --time-from-start-sec 1.0 --settle-sec 0.25 "
        "--max-iterations 20 --joint-l2-tolerance 0.01 --joint-max-abs-tolerance 0.005 "
        f"--output-json {cycle_dir / 'return_to_reference.json'}"
    )
    rc = _run(_bash(cmd), cycle_dir / "return_to_reference.log", allow_fail=True, timeout=90.0)
    return rc == 0 and bool(_load_json(cycle_dir / "return_to_reference.json").get("reached"))


def _gate(
    cycle_dir: Path,
    label: str,
    target_drift_max: float,
    relative_drift_max: float,
    initial_distance_max: float,
) -> bool:
    output = cycle_dir / f"{label}.json"
    cmd = (
        "python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/check_b8_initial_state_gate.py "
        f"--reference-npz {REFERENCE_NPZ} "
        "--target-model-name cylinder_target_gate_probe "
        "--joint-l2-threshold 0.02 --joint-max-abs-threshold 0.01 "
        "--eef-base-drift-threshold 0.02 "
        f"--target-base-drift-threshold {target_drift_max} "
        f"--relative-base-drift-threshold {relative_drift_max} "
        f"--initial-distance-max {initial_distance_max} "
        f"--output-json {output}"
    )
    rc = _run(_bash(cmd), cycle_dir / f"{label}.log", allow_fail=True, timeout=30.0)
    return rc == 0 and bool(_load_json(output).get("passed"))


def _gate_with_retries(
    cycle_dir: Path,
    label: str,
    target_drift_max: float,
    relative_drift_max: float,
    initial_distance_max: float,
) -> Optional[Path]:
    for attempt in range(3):
        suffix = label if attempt == 0 else f"{label}_retry_{attempt}"
        if _gate(cycle_dir, suffix, target_drift_max, relative_drift_max, initial_distance_max):
            src = cycle_dir / f"{suffix}.json"
            canonical = cycle_dir / f"{label}.json"
            if src != canonical:
                canonical.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            return canonical
        if attempt < 2:
            _run(_bash("sleep 3"), cycle_dir / f"{suffix}_wait.log", allow_fail=True, timeout=10.0)
    return None


def _run_policy_node(
    method: str,
    cycle_dir: Path,
    output_name: str,
    execute_actions: bool,
    max_control_ticks: int,
    early_stop_on_reaching: bool,
    early_stop_distance: float,
    early_stop_min_distance_reduction: float,
    early_stop_initial_distance_override: Optional[float] = None,
) -> bool:
    policy = POLICIES[method]
    cmd = (
        "roslaunch rexrov_single_oberon7_fm_dp b8_bc_h8_xyz_base_relative_execution_smoke.launch "
        f"method_name:={method} policy_type:={policy['policy_type']} "
        f"checkpoint:={policy['checkpoint']} "
        f"num_inference_steps:={policy['num_inference_steps']} ode_steps:={policy['ode_steps']} "
        "rate_hz:=3.0 max_duration_sec:=7.2 "
        f"max_control_ticks:={max_control_ticks} replan_every_steps:=1 "
        f"early_stop_on_reaching:={'true' if execute_actions and early_stop_on_reaching else 'false'} "
        f"early_stop_distance:={early_stop_distance} "
        f"early_stop_min_distance_reduction:={early_stop_min_distance_reduction} "
        f"early_stop_initial_distance_override:={early_stop_initial_distance_override if early_stop_initial_distance_override is not None else -1.0} "
        "early_stop_min_control_ticks:=1 "
        f"execute_actions:={'true' if execute_actions else 'false'} "
        f"i_understand_this_publishes_arm_commands:={'true' if execute_actions else 'false'} "
        f"output_json:={cycle_dir / output_name}"
    )
    rc = _run(_bash(cmd), cycle_dir / output_name.replace(".json", ".log"), allow_fail=True, timeout=80.0)
    if not (cycle_dir / output_name).exists():
        return False
    payload = _load_json(cycle_dir / output_name)
    return rc == 0 and payload.get("aborted") is False


def _summarize_cycle(
    cycle_dir: Path,
    target_drift_max: float,
    success_distance_max: float,
    success_distance_reduction_min: float,
    final_distance_source: str,
) -> bool:
    cmd = (
        "python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/summarize_b8_base_relative_tiny_smoke.py "
        f"--return-json {cycle_dir / 'return_to_reference.json'} "
        f"--pre-gate-0-json {cycle_dir / 'pre_gate_0.json'} "
        f"--pre-gate-1-json {cycle_dir / 'pre_gate_1.json'} "
        f"--smoke-json {cycle_dir / 'smoke.json'} "
        f"--post-gate-json {cycle_dir / 'post_gate.json'} "
        f"--output-json {cycle_dir / 'summary.json'} "
        f"--output-md {cycle_dir / 'summary.md'} "
        f"--success-distance-max {success_distance_max} "
        f"--success-distance-reduction-min {success_distance_reduction_min} "
        f"--final-distance-source {final_distance_source} "
        f"--target-base-drift-max {target_drift_max}"
    )
    rc = _run(_bash(cmd), cycle_dir / "summary.log", allow_fail=True, timeout=30.0)
    if not (cycle_dir / "summary.json").exists():
        return False
    return rc == 0 and _load_json(cycle_dir / "summary.json").get("smoke_status") == "arm_only_reaching_success"


def _failure_cycle(cycle_dir: Path, method: str, reason: str) -> None:
    smoke = {
        "tool": "run_b8_bc_dp_fm_live_eval",
        "status": "not_started_or_failed",
        "method_name": method,
        "aborted": True,
        "abort_reason": reason,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "hand_controller_started": False,
        "samples": 0,
        "history": [],
    }
    _write_json(cycle_dir / "smoke.json", smoke)
    if not (cycle_dir / "post_gate.json").exists():
        _write_json(
            cycle_dir / "post_gate.json",
            {
                "gate": "post_gate_not_run",
                "passed": False,
                "reason": reason,
                "control_commands_sent": False,
                "gripper_commands_sent": False,
            },
        )
    summary = {
        "tool": "run_b8_bc_dp_fm_live_eval",
        "method": method,
        "smoke_status": "not_resolved",
        "checks_passed": False,
        "command_path_smoke_resolved": False,
        "arm_only_reaching_success_claimed": False,
        "learned_rollout_success_claimed": False,
        "grasp_success_claimed": False,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
        "hand_controller_started": False,
        "failure_reason": reason,
        "checks": [{"name": reason, "passed": False, "detail": reason}],
        "metrics": {},
    }
    _write_json(cycle_dir / "summary.json", summary)
    (cycle_dir / "summary.md").write_text(
        f"# {method.upper()} Cycle Failure\n\nFailure reason: `{reason}`.\n\nNo gripper command. No grasp claim.\n",
        encoding="utf-8",
    )


def _post_gate(cycle_dir: Path, target_drift_max: float, initial_distance_max: float) -> None:
    # Post-gate may fail because the arm moved; keep target drift in the artifact.
    _gate(
        cycle_dir,
        "post_gate",
        target_drift_max=target_drift_max,
        relative_drift_max=0.25,
        initial_distance_max=initial_distance_max,
    )


def run_method(
    method: str,
    root: Path,
    formal_n: int,
    max_control_ticks: int,
    target_drift_max: float,
    relative_drift_max: float,
    initial_distance_max: float,
    early_stop_on_reaching: bool,
    early_stop_distance: float,
    early_stop_min_distance_reduction: float,
    success_distance_max: float,
    success_distance_reduction_min: float,
    final_distance_source: str,
) -> None:
    method_dir = root / method
    method_dir.mkdir(parents=True, exist_ok=True)
    if method in {"dp", "fm"}:
        dry_dir = method_dir / "dry_run"
        dry_dir.mkdir(parents=True, exist_ok=True)
        if not _return_to_reference(dry_dir):
            _write_json(dry_dir / "dry_run_result.json", {"passed": False, "failure_reason": "return_failed"})
            return
        if _gate_with_retries(
            dry_dir,
            "pre_gate_0",
            target_drift_max,
            relative_drift_max,
            initial_distance_max,
        ) is None:
            _write_json(dry_dir / "dry_run_result.json", {"passed": False, "failure_reason": "dry_run_gate_failed"})
            return
        ok = _run_policy_node(
            method,
            dry_dir,
            "dry_run.json",
            execute_actions=False,
            max_control_ticks=1,
            early_stop_on_reaching=False,
            early_stop_distance=early_stop_distance,
            early_stop_min_distance_reduction=early_stop_min_distance_reduction,
        )
        payload = _load_json(dry_dir / "dry_run.json") if (dry_dir / "dry_run.json").exists() else {}
        passed = bool(ok and payload.get("control_commands_sent") is False and payload.get("gripper_commands_sent") is False)
        _write_json(dry_dir / "dry_run_result.json", {"passed": passed, "policy_output": payload})
        if not passed:
            return

        smoke_dir = method_dir / "tiny_smoke"
        smoke_dir.mkdir(parents=True, exist_ok=True)
        if not _run_one_cycle(
            method,
            smoke_dir,
            target_drift_max,
            relative_drift_max,
            initial_distance_max,
            max_control_ticks,
            early_stop_on_reaching,
            early_stop_distance,
            early_stop_min_distance_reduction,
            success_distance_max,
            success_distance_reduction_min,
            final_distance_source,
        ):
            return

    for index in range(formal_n):
        cycle_dir = method_dir / f"cycle_{index}"
        cycle_dir.mkdir(parents=True, exist_ok=True)
        ok = _run_one_cycle(
            method,
            cycle_dir,
            target_drift_max,
            relative_drift_max,
            initial_distance_max,
            max_control_ticks,
            early_stop_on_reaching,
            early_stop_distance,
            early_stop_min_distance_reduction,
            success_distance_max,
            success_distance_reduction_min,
            final_distance_source,
        )
        if not ok:
            break


def _run_one_cycle(
    method: str,
    cycle_dir: Path,
    target_drift_max: float,
    relative_drift_max: float,
    initial_distance_max: float,
    max_control_ticks: int,
    early_stop_on_reaching: bool,
    early_stop_distance: float,
    early_stop_min_distance_reduction: float,
    success_distance_max: float,
    success_distance_reduction_min: float,
    final_distance_source: str,
) -> bool:
    if not _return_to_reference(cycle_dir):
        _failure_cycle(cycle_dir, method, "return_to_reference_failed")
        return False
    if _gate_with_retries(
        cycle_dir,
        "pre_gate_0",
        target_drift_max,
        relative_drift_max,
        initial_distance_max,
    ) is None:
        _failure_cycle(cycle_dir, method, "pre_gate_0_failed")
        return False
    pre_gate_1_path = _gate_with_retries(
        cycle_dir,
        "pre_gate_1",
        target_drift_max,
        relative_drift_max,
        initial_distance_max,
    )
    if pre_gate_1_path is None:
        _failure_cycle(cycle_dir, method, "pre_gate_1_failed")
        return False
    pre_gate_1 = _load_json(pre_gate_1_path)
    early_stop_initial_distance = (
        (pre_gate_1.get("metrics", {}) or {}).get("initial_distance")
        if isinstance(pre_gate_1, dict)
        else None
    )
    if not _run_policy_node(
        method,
        cycle_dir,
        "smoke.json",
        execute_actions=True,
        max_control_ticks=max_control_ticks,
        early_stop_on_reaching=early_stop_on_reaching,
        early_stop_distance=early_stop_distance,
        early_stop_min_distance_reduction=early_stop_min_distance_reduction,
        early_stop_initial_distance_override=early_stop_initial_distance,
    ):
        _post_gate(cycle_dir, target_drift_max, initial_distance_max)
        _summarize_cycle(
            cycle_dir,
            target_drift_max,
            success_distance_max,
            success_distance_reduction_min,
            final_distance_source,
        )
        return False
    _post_gate(cycle_dir, target_drift_max, initial_distance_max)
    return _summarize_cycle(
        cycle_dir,
        target_drift_max,
        success_distance_max,
        success_distance_reduction_min,
        final_distance_source,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-dir", type=Path, default=PACKAGE_ROOT / "outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol_v2")
    parser.add_argument("--formal-n", type=int, default=3)
    parser.add_argument("--target-drift-max", type=float, default=0.01)
    parser.add_argument("--relative-drift-max", type=float, default=0.01)
    parser.add_argument("--initial-distance-max", type=float, default=0.115)
    parser.add_argument("--max-control-ticks", type=int, default=9)
    parser.add_argument("--early-stop-on-reaching", action="store_true")
    parser.add_argument("--early-stop-distance", type=float, default=0.095)
    parser.add_argument("--early-stop-min-distance-reduction", type=float, default=0.0)
    parser.add_argument("--success-distance-max", type=float, default=0.10)
    parser.add_argument("--success-distance-reduction-min", type=float, default=0.02)
    parser.add_argument(
        "--final-distance-source",
        choices=["post_gate", "terminal_observation"],
        default="post_gate",
    )
    args = parser.parse_args()
    args.root_dir = args.root_dir.expanduser().resolve()
    args.root_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        args.root_dir / "formal_protocol.json",
        {
            "protocol_name": "b8_bc_dp_fm_live_arm_only_reaching_pregrasp_protocol_v2",
            "success": (
                f"formal_final_distance({args.final_distance_source}) <= {args.success_distance_max} "
                f"and formal_distance_reduction > {args.success_distance_reduction_min} "
                "and rollout not aborted"
            ),
            "success_distance_max": args.success_distance_max,
            "success_distance_reduction_min": args.success_distance_reduction_min,
            "final_distance_source": args.final_distance_source,
            "target_drift_max": args.target_drift_max,
            "relative_drift_max": args.relative_drift_max,
            "initial_distance_max": args.initial_distance_max,
            "max_control_ticks": args.max_control_ticks,
            "early_stop_on_reaching": args.early_stop_on_reaching,
            "early_stop_distance": args.early_stop_distance,
            "early_stop_min_distance_reduction": args.early_stop_min_distance_reduction,
            "clip_m": 0.005,
            "max_joint_delta_rad": 0.01,
            "gripper_enabled": False,
            "hand_controller_allowed": False,
            "formal_n": args.formal_n,
        },
    )
    for method in ["bc", "dp", "fm"]:
        run_method(
            method,
            args.root_dir,
            args.formal_n,
            args.max_control_ticks,
            args.target_drift_max,
            args.relative_drift_max,
            args.initial_distance_max,
            args.early_stop_on_reaching,
            args.early_stop_distance,
            args.early_stop_min_distance_reduction,
            args.success_distance_max,
            args.success_distance_reduction_min,
            args.final_distance_source,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
