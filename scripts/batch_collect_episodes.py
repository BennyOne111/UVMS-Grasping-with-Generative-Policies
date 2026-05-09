#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import time
from typing import Dict, List, Mapping, Optional

import numpy as np
import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SRC = PACKAGE_ROOT / "src"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

from rexrov_single_oberon7_fm_dp.dataset_writer import validate_episode_file  # noqa: E402


def load_config(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"batch config must be a mapping: {path}")
    return data


def _as_float_pair(config: Mapping[str, object], key: str) -> List[float]:
    value = config.get(key)
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"target_randomization.{key} must be a two-element list")
    return [float(value[0]), float(value[1])]


def sample_target_pose(config: Mapping[str, object], rng: random.Random) -> Dict[str, float]:
    target_cfg = config.get("target_randomization", {}) or {}
    if not target_cfg.get("enabled", False):
        return {"x": 2.6, "y": 2.0, "z": -40.0, "yaw": 0.0}
    ranges = {axis: _as_float_pair(target_cfg, axis) for axis in ("x", "y", "z", "yaw")}
    return {
        "x": rng.uniform(*ranges["x"]),
        "y": rng.uniform(*ranges["y"]),
        "z": rng.uniform(*ranges["z"]),
        "yaw": rng.uniform(*ranges["yaw"]),
    }


def run_command(command: List[str], timeout: Optional[float] = None) -> subprocess.CompletedProcess:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        preexec_fn=os.setsid,
    )
    try:
        stdout, _ = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command, process.returncode, stdout=stdout, stderr=None)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(process.pid), signal.SIGINT)
        try:
            stdout, _ = process.communicate(timeout=10.0)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            stdout, _ = process.communicate(timeout=10.0)
        return subprocess.CompletedProcess(command, 124, stdout=stdout or "", stderr=None)


def launch_background(command: List[str]) -> subprocess.Popen:
    return subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        preexec_fn=os.setsid,
    )


def terminate_process(process: Optional[subprocess.Popen], timeout_sec: float = 10.0) -> None:
    if process is None or process.poll() is not None:
        return
    os.killpg(os.getpgid(process.pid), signal.SIGINT)
    try:
        process.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        try:
            process.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            process.wait(timeout=timeout_sec)


def wait_for_ros(timeout_sec: float) -> None:
    deadline = time.time() + timeout_sec
    last_output = ""
    while time.time() < deadline:
        topic_result = run_command(["rostopic", "list"], timeout=5.0)
        service_result = run_command(["rosservice", "list"], timeout=5.0)
        last_output = topic_result.stdout + "\n" + service_result.stdout
        topics_ready = (
            topic_result.returncode == 0
            and "/joint_states" in topic_result.stdout
            and "/gazebo/model_states" in topic_result.stdout
        )
        services_ready = (
            service_result.returncode == 0
            and "/gazebo/spawn_sdf_model" in service_result.stdout
            and "/gazebo/delete_model" in service_result.stdout
        )
        if topics_ready and services_ready:
            return
        time.sleep(1.0)
    raise RuntimeError(f"ROS graph did not expose required topics within {timeout_sec:.1f}s:\n{last_output}")


def delete_gazebo_model(model_name: str) -> None:
    run_command(
        ["rosservice", "call", "/gazebo/delete_model", f"model_name: '{model_name}'"],
        timeout=5.0,
    )


def unpause_gazebo() -> None:
    run_command(["rosservice", "call", "/gazebo/unpause_physics"], timeout=5.0)


def build_sim_command(config: Mapping[str, object]) -> List[str]:
    sim_cfg = config.get("simulation", {}) or {}
    args = sim_cfg.get("args", {}) or {}
    command = [
        "roslaunch",
        str(sim_cfg.get("package", "uvms_control")),
        str(sim_cfg.get("launch_file", "oberon7_position_control.launch")),
    ]
    for key, value in args.items():
        command.append(f"{key}:={value}")
    return command


def build_collect_command(
    config: Mapping[str, object],
    episode_id: str,
    target_model_name: str,
    target_pose: Mapping[str, float],
    output_dir: Path,
) -> List[str]:
    launch_cfg = config.get("collection_launch", {}) or {}
    return [
        "roslaunch",
        str(launch_cfg.get("package", "rexrov_single_oberon7_fm_dp")),
        str(launch_cfg.get("launch_file", "collect_episode.launch")),
        f"output_dir:={output_dir}",
        f"episode_id:={episode_id}",
        f"rate_hz:={float(config.get('rate_hz', 2.0))}",
        f"max_duration_sec:={float(config.get('max_duration_sec', 5.0))}",
        f"target_model_name:={target_model_name}",
        f"target_x:={target_pose['x']}",
        f"target_y:={target_pose['y']}",
        f"target_z:={target_pose['z']}",
        f"spawn_target:={str(bool(launch_cfg.get('spawn_target', True))).lower()}",
        "allow_nominal_state_fallback:="
        f"{str(bool(launch_cfg.get('allow_nominal_state_fallback', False))).lower()}",
        f"state_fallback_wait_sec:={float(launch_cfg.get('state_fallback_wait_sec', 30.0))}",
        f"expert_wait_for_target_sec:={float(launch_cfg.get('expert_wait_for_target_sec', 5.0))}",
    ]


def write_split(valid_paths: List[str], output_dir: Path, split_cfg: Mapping[str, object], seed: int) -> Optional[Path]:
    if not split_cfg.get("enabled", True):
        return None

    rng = random.Random(seed)
    shuffled = list(valid_paths)
    rng.shuffle(shuffled)

    n_total = len(shuffled)
    train_fraction = float(split_cfg.get("train_fraction", 0.8))
    val_fraction = float(split_cfg.get("val_fraction", 0.2))
    n_train = int(round(n_total * train_fraction))
    n_val = int(round(n_total * val_fraction))
    if n_train + n_val > n_total:
        n_val = max(0, n_total - n_train)

    split = {
        "train": shuffled[:n_train],
        "val": shuffled[n_train : n_train + n_val],
        "test": shuffled[n_train + n_val :],
        "counts": {
            "total": n_total,
            "train": n_train,
            "val": n_val,
            "test": max(0, n_total - n_train - n_val),
        },
        "seed": seed,
    }

    path = output_dir / str(split_cfg.get("write_filename", "dataset_split.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(split, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch collect scripted expert demonstration episodes.")
    parser.add_argument(
        "--config",
        default=str(PACKAGE_ROOT / "config" / "batch_collection.yaml"),
        help="Path to batch_collection.yaml.",
    )
    parser.add_argument("--num-episodes", type=int, default=None, help="Override config num_episodes.")
    parser.add_argument("--output-dir", default="", help="Override episode output directory.")
    parser.add_argument("--summary-dir", default="", help="Override summary output directory.")
    parser.add_argument("--episode-prefix", default="", help="Override episode id prefix.")
    parser.add_argument("--no-start-sim", action="store_true", help="Assume the Gazebo launch is already running.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned commands without running them.")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser()
    config = load_config(config_path)
    num_episodes = int(args.num_episodes if args.num_episodes is not None else config.get("num_episodes", 20))
    output_dir = Path(args.output_dir or str(config.get("output_dir"))).expanduser()
    summary_dir = Path(args.summary_dir or str(config.get("summary_output_dir"))).expanduser()
    episode_prefix = args.episode_prefix or str(config.get("episode_id_prefix", "stage6_debug"))
    seed = int(config.get("random_seed", 42))
    rng = random.Random(seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    sim_cfg = config.get("simulation", {}) or {}
    start_simulation = bool(sim_cfg.get("start_simulation", True)) and not args.no_start_sim
    sim_process: Optional[subprocess.Popen] = None
    results: List[Dict[str, object]] = []
    valid_paths: List[str] = []

    try:
        if start_simulation:
            sim_command = build_sim_command(config)
            if args.dry_run:
                print("SIM:", " ".join(sim_command))
            else:
                sim_process = launch_background(sim_command)
                wait_for_ros(float(sim_cfg.get("startup_wait_sec", 8.0)))
                unpause_gazebo()
                time.sleep(float(sim_cfg.get("stabilization_wait_sec", 0.0)))
        elif not args.dry_run:
            wait_for_ros(5.0)

        timeout = float(config.get("max_duration_sec", 5.0)) + float(
            (config.get("collection_launch", {}) or {}).get("timeout_margin_sec", 20.0)
        )

        for index in range(num_episodes):
            episode_id = f"{episode_prefix}_{index:04d}"
            target_model_name = f"{config.get('target_model_name_base', 'cylinder_target')}_{episode_id}"
            target_pose = sample_target_pose(config, rng)
            command = build_collect_command(config, episode_id, target_model_name, target_pose, output_dir)
            episode_path = output_dir / f"{episode_id}.npz"

            if args.dry_run:
                print("COLLECT:", " ".join(command))
                continue

            if bool((config.get("collection_launch", {}) or {}).get("spawn_target", True)):
                unpause_gazebo()
                delete_gazebo_model(target_model_name)
            started_at = time.time()
            result = run_command(command, timeout=timeout)
            elapsed = time.time() - started_at

            validation_ok = False
            validation_errors: List[str] = []
            validation_warnings: List[str] = []
            if episode_path.exists() and bool((config.get("validation", {}) or {}).get("run_per_episode", True)):
                validation = validate_episode_file(
                    str(episode_path),
                    allow_unavailable_nan=not bool((config.get("validation", {}) or {}).get("strict_nan", False)),
                )
                validation_ok = validation.ok
                validation_errors = validation.errors
                validation_warnings = validation.warnings
            elif episode_path.exists():
                validation_ok = True
            else:
                validation_errors = [f"episode file was not created: {episode_path}"]

            accepted = validation_ok
            if bool(config.get("success_filter", False)) and episode_path.exists():
                with np.load(str(episode_path), allow_pickle=False) as loaded:
                    accepted = accepted and bool(np.asarray(loaded["success"]).item())

            if accepted and episode_path.exists():
                valid_paths.append(str(episode_path))

            results.append(
                {
                    "episode_id": episode_id,
                    "episode_path": str(episode_path),
                    "target_model_name": target_model_name,
                    "target_pose_command": target_pose,
                    "returncode": result.returncode,
                    "elapsed_sec": elapsed,
                    "validation_ok": validation_ok,
                    "accepted": accepted,
                    "validation_errors": validation_errors,
                    "validation_warnings": validation_warnings,
                    "launch_output_tail": "\n".join(result.stdout.splitlines()[-40:]),
                }
            )

            if bool((config.get("collection_launch", {}) or {}).get("spawn_target", True)):
                delete_gazebo_model(target_model_name)
            status = "ok" if validation_ok else "fail"
            print(f"[{index + 1}/{num_episodes}] {episode_id}: {status}, accepted={accepted}, elapsed={elapsed:.1f}s")

        split_path = None
        if not args.dry_run:
            split_path = write_split(valid_paths, summary_dir, config.get("split", {}) or {}, seed)

        manifest = {
            "config_path": str(config_path),
            "num_episodes_requested": num_episodes,
            "output_dir": str(output_dir),
            "summary_dir": str(summary_dir),
            "success_filter": bool(config.get("success_filter", False)),
            "episodes": results,
            "accepted_episode_paths": valid_paths,
            "split_path": str(split_path) if split_path else None,
        }
        manifest_path = summary_dir / "batch_collection_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"manifest: {manifest_path}")
        if split_path:
            print(f"split: {split_path}")
    finally:
        terminate_process(sim_process)

    failed = [item for item in results if not item.get("validation_ok")]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
