#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Dict, List, Optional


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = PACKAGE_ROOT / "data/raw/b8_reaching_debug_10/b8_reaching_debug_10_0000.npz"
DEFAULT_OUTPUT_DIR = PACKAGE_ROOT / "data/raw/b8_postfix_debug_3"
DEFAULT_LOG_DIR = PACKAGE_ROOT / "outputs/logs/b8_postfix_debug_3_conservative"
MAX_EPISODE_COUNT = 20


def _run_command(command: List[str], log_path: Path, timeout_sec: Optional[float] = None) -> Dict[str, object]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=timeout_sec,
        )
        stdout = completed.stdout
        returncode = int(completed.returncode)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        partial = exc.stdout or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        stdout = partial + f"\nTIMEOUT after {timeout_sec:.1f} sec: {' '.join(command)}\n"
        returncode = 124
    elapsed = time.time() - started
    log_path.write_text(stdout, encoding="utf-8")
    return {
        "command": command,
        "returncode": returncode,
        "elapsed_sec": elapsed,
        "log_path": str(log_path),
        "timed_out": timed_out,
        "timeout_sec": timeout_sec,
    }


def _load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_manifest(path: Path, manifest: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _episode_id(prefix: str, index: int) -> str:
    return f"{prefix}_{index:04d}"


def _return_command(args: argparse.Namespace, output_json: Path) -> List[str]:
    return [
        "rosrun",
        "rexrov_single_oberon7_fm_dp",
        "return_left_arm_to_reference.py",
        "--reference-npz",
        str(args.reference_npz),
        "--max-joint-delta",
        str(args.return_max_joint_delta),
        "--time-from-start-sec",
        str(args.return_time_from_start_sec),
        "--settle-sec",
        str(args.return_settle_sec),
        "--max-iterations",
        str(args.return_max_iterations),
        "--joint-l2-tolerance",
        str(args.return_joint_l2_tolerance),
        "--joint-max-abs-tolerance",
        str(args.return_joint_max_abs_tolerance),
        "--output-json",
        str(output_json),
    ]


def _gate_command(args: argparse.Namespace, output_json: Path) -> List[str]:
    return [
        "rosrun",
        "rexrov_single_oberon7_fm_dp",
        "check_b8_initial_state_gate.py",
        "--reference-npz",
        str(args.reference_npz),
        "--target-model-name",
        args.target_model_name,
        "--initial-distance-max",
        str(args.initial_distance_max),
        "--relative-base-drift-threshold",
        str(args.relative_base_drift_threshold),
        "--output-json",
        str(output_json),
    ]


def _collect_command(args: argparse.Namespace, episode_id: str) -> List[str]:
    return [
        "roslaunch",
        "rexrov_single_oberon7_fm_dp",
        "collect_episode.launch",
        f"output_dir:={args.output_dir}",
        f"episode_id:={episode_id}",
        f"target_model_name:={args.target_model_name}",
        "spawn_target:=false",
        "enable_base_relative_target:=false",
        "execute_arm:=true",
        "execute_arm_once_per_state:=false",
        "execute_arm_states:=MOVE_TO_PREGRASP,MOVE_TO_GRASP",
        "state_sequence:=MOVE_TO_PREGRASP,MOVE_TO_GRASP",
        "target_directed_reaching:=true",
        "target_directed_action_frame:=base_link",
        "arm_action_frame:=planning_frame",
        "enable_gripper_command:=false",
        "gripper_enabled:=false",
        "is_grasp_dataset:=false",
        "allow_nominal_state_fallback:=false",
        "prefer_model_states_base_pose:=false",
        "task_type:=arm_only_reaching",
        "success_metric:=reaching_success",
        "require_target:=false",
        f"rate_hz:={args.rate_hz}",
        f"max_duration_sec:={args.max_duration_sec}",
        f"max_linear_step:={args.max_linear_step}",
        f"max_joint_delta:={args.max_joint_delta}",
        f"time_from_start_sec:={args.time_from_start_sec}",
        f"post_publish_sleep_sec:={args.post_publish_sleep_sec}",
    ]


def _validate_command(episode_path: Path) -> List[str]:
    return [
        "rosrun",
        "rexrov_single_oberon7_fm_dp",
        "validate_episode.py",
        str(episode_path),
    ]


def _summary_command(args: argparse.Namespace) -> List[str]:
    return [
        "rosrun",
        "rexrov_single_oberon7_fm_dp",
        "summarize_b8_repeatability_smoke.py",
        "--input-dir",
        str(args.output_dir),
        "--pattern",
        f"{args.episode_prefix}_*.npz",
        "--output-dir",
        str(args.summary_output_dir),
        "--required-base-state-source",
        "odom",
        "--fail-on-problem",
    ]


def _stop(manifest: Dict[str, object], reason: str, manifest_path: Path) -> int:
    manifest["status"] = "stopped"
    manifest["stop_reason"] = reason
    _write_manifest(manifest_path, manifest)
    print(f"STOP: {reason}")
    print(f"manifest: {manifest_path}")
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Conservative B8' post-fix debug batch runner: return -> wait/retry gate -> one arm-only "
            "episode -> validation. It keeps initial_distance_max=0.115 by default and sends no gripper commands."
        )
    )
    parser.add_argument("--episode-count", type=int, default=3)
    parser.add_argument("--episode-prefix", default="b8_postfix_debug_3")
    parser.add_argument("--reference-npz", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--summary-output-dir", type=Path, default=PACKAGE_ROOT / "outputs/logs/b8_postfix_debug_3_summary")
    parser.add_argument("--target-model-name", default="cylinder_target_gate_probe")
    parser.add_argument("--gate-attempts", type=int, default=6)
    parser.add_argument("--gate-wait-sec", type=float, default=5.0)
    parser.add_argument("--initial-distance-max", type=float, default=0.115)
    parser.add_argument("--relative-base-drift-threshold", type=float, default=0.01)
    parser.add_argument("--rate-hz", type=float, default=3.0)
    parser.add_argument("--max-duration-sec", type=float, default=7.2)
    parser.add_argument("--max-linear-step", type=float, default=0.010)
    parser.add_argument("--max-joint-delta", type=float, default=0.010)
    parser.add_argument("--time-from-start-sec", type=float, default=1.0)
    parser.add_argument("--post-publish-sleep-sec", type=float, default=0.5)
    parser.add_argument("--return-max-joint-delta", type=float, default=0.01)
    parser.add_argument("--return-time-from-start-sec", type=float, default=1.0)
    parser.add_argument("--return-settle-sec", type=float, default=0.25)
    parser.add_argument("--return-max-iterations", type=int, default=20)
    parser.add_argument("--return-joint-l2-tolerance", type=float, default=0.01)
    parser.add_argument("--return-joint-max-abs-tolerance", type=float, default=0.005)
    parser.add_argument("--return-timeout-sec", type=float, default=90.0)
    parser.add_argument("--gate-timeout-sec", type=float, default=30.0)
    parser.add_argument("--collect-timeout-sec", type=float, default=90.0)
    parser.add_argument("--validate-timeout-sec", type=float, default=30.0)
    parser.add_argument("--summary-timeout-sec", type=float, default=60.0)
    parser.add_argument(
        "--allow-existing",
        action="store_true",
        help="Allow existing episode files. By default the runner refuses to overwrite/append over existing IDs.",
    )
    parser.add_argument(
        "--skip-summary",
        action="store_true",
        help="Do not run summarize_b8_repeatability_smoke.py after successful collection.",
    )
    args = parser.parse_args()

    if args.episode_count < 1 or args.episode_count > MAX_EPISODE_COUNT:
        raise ValueError(
            f"--episode-count must be in [1, {MAX_EPISODE_COUNT}] for this conservative debug runner"
        )
    if args.initial_distance_max != 0.115:
        raise ValueError("方案1 keeps --initial-distance-max exactly 0.115")

    args.reference_npz = args.reference_npz.expanduser().resolve()
    args.output_dir = args.output_dir.expanduser().resolve()
    args.log_dir = args.log_dir.expanduser().resolve()
    args.summary_output_dir = args.summary_output_dir.expanduser().resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.log_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = args.log_dir / "conservative_batch_manifest.json"
    manifest: Dict[str, object] = {
        "tool": "run_b8_postfix_debug_batch_conservative",
        "policy": "方案1: keep initial_distance_max=0.115; wait/retry gate; collect only after fresh gate pass",
        "episode_count_requested": args.episode_count,
        "episodes_completed": 0,
        "output_dir": str(args.output_dir),
        "log_dir": str(args.log_dir),
        "reference_npz": str(args.reference_npz),
        "target_model_name": args.target_model_name,
        "constraints": {
            "allow_nominal_state_fallback": False,
            "enable_gripper_command": False,
            "gripper_enabled": False,
            "is_grasp_dataset": False,
            "task_type": "arm_only_reaching",
            "success_metric": "reaching_success",
            "learned_rollout": False,
            "training": False,
        },
        "gate_policy": {
            "gate_attempts": args.gate_attempts,
            "gate_wait_sec": args.gate_wait_sec,
            "initial_distance_max": args.initial_distance_max,
            "relative_base_drift_threshold": args.relative_base_drift_threshold,
        },
        "episodes": [],
        "status": "running",
    }
    _write_manifest(manifest_path, manifest)

    for index in range(args.episode_count):
        episode_id = _episode_id(args.episode_prefix, index)
        episode_path = args.output_dir / f"{episode_id}.npz"
        if episode_path.exists() and not args.allow_existing:
            return _stop(manifest, f"episode already exists: {episode_path}", manifest_path)

        record: Dict[str, object] = {
            "episode_index": index,
            "episode_id": episode_id,
            "episode_path": str(episode_path),
            "status": "running",
            "gate_attempts": [],
        }
        manifest["episodes"].append(record)  # type: ignore[index]
        _write_manifest(manifest_path, manifest)

        return_json = args.log_dir / f"{episode_id}_return.json"
        return_run = _run_command(
            _return_command(args, return_json),
            args.log_dir / f"{episode_id}_return.log",
            timeout_sec=args.return_timeout_sec,
        )
        record["return"] = return_run
        if return_run["returncode"] != 0:
            record["status"] = "return_failed"
            return _stop(manifest, f"return failed for {episode_id}", manifest_path)
        return_report = _load_json(return_json)
        record["return_report"] = {
            "reached": return_report.get("reached"),
            "commands_sent": return_report.get("commands_sent"),
            "gripper_commands_sent": return_report.get("gripper_commands_sent"),
            "final_metrics": return_report.get("final_metrics"),
        }
        if return_report.get("reached") is not True or return_report.get("gripper_commands_sent") is not False:
            record["status"] = "return_gate_failed"
            return _stop(manifest, f"return report not safe for {episode_id}", manifest_path)

        gate_passed = False
        for attempt in range(max(1, args.gate_attempts)):
            gate_json = args.log_dir / f"{episode_id}_gate_attempt_{attempt:02d}.json"
            gate_run = _run_command(
                _gate_command(args, gate_json),
                args.log_dir / f"{episode_id}_gate_attempt_{attempt:02d}.log",
                timeout_sec=args.gate_timeout_sec,
            )
            gate_report: Optional[Dict[str, object]] = None
            if gate_json.exists():
                gate_report = _load_json(gate_json)
            attempt_record = {
                "attempt": attempt,
                "run": gate_run,
                "passed": None if gate_report is None else gate_report.get("passed"),
                "metrics": None if gate_report is None else gate_report.get("metrics"),
                "checks": None if gate_report is None else gate_report.get("checks"),
                "control_commands_sent": None if gate_report is None else gate_report.get("control_commands_sent"),
                "gripper_commands_sent": None if gate_report is None else gate_report.get("gripper_commands_sent"),
            }
            record["gate_attempts"].append(attempt_record)  # type: ignore[index]
            _write_manifest(manifest_path, manifest)
            if (
                gate_run["returncode"] == 0
                and gate_report is not None
                and gate_report.get("passed") is True
                and gate_report.get("control_commands_sent") is False
                and gate_report.get("gripper_commands_sent") is False
            ):
                gate_passed = True
                break
            if attempt + 1 < args.gate_attempts:
                time.sleep(max(0.0, args.gate_wait_sec))

        if not gate_passed:
            record["status"] = "gate_failed"
            return _stop(manifest, f"fresh gate did not pass for {episode_id}", manifest_path)

        collect_run = _run_command(
            _collect_command(args, episode_id),
            args.log_dir / f"{episode_id}_collect.log",
            timeout_sec=args.collect_timeout_sec,
        )
        record["collect"] = collect_run
        if collect_run["returncode"] != 0:
            record["status"] = "collect_failed"
            return _stop(manifest, f"collect failed for {episode_id}", manifest_path)
        if not episode_path.exists():
            record["status"] = "episode_missing"
            return _stop(manifest, f"expected episode was not written: {episode_path}", manifest_path)

        validate_run = _run_command(
            _validate_command(episode_path),
            args.log_dir / f"{episode_id}_validate.log",
            timeout_sec=args.validate_timeout_sec,
        )
        record["validate"] = validate_run
        if validate_run["returncode"] != 0:
            record["status"] = "validate_failed"
            return _stop(manifest, f"validator failed for {episode_id}", manifest_path)

        record["status"] = "completed"
        manifest["episodes_completed"] = index + 1
        _write_manifest(manifest_path, manifest)

    if not args.skip_summary:
        summary_run = _run_command(
            _summary_command(args),
            args.log_dir / "summary.log",
            timeout_sec=args.summary_timeout_sec,
        )
        manifest["summary"] = summary_run
        if summary_run["returncode"] != 0:
            return _stop(manifest, "summary failed", manifest_path)

    manifest["status"] = "completed"
    manifest["stop_reason"] = ""
    _write_manifest(manifest_path, manifest)
    print(f"completed conservative batch: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
