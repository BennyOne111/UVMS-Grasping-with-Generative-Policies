# RexROV Single-Active-Left Oberon7 BC / Diffusion / Flow Matching Demo

This ROS package contains the first demo pipeline for comparing Behavioral
Cloning, Diffusion Policy, and Flow Matching Policy on a state-based underwater
manipulation task in Project DAVE / Gazebo.

The robot model is the existing RexROV + dual Oberon7 setup. The first-version
learning task uses only the left Oberon7 arm as the active arm:

```text
robot_mode: dual_model_single_active_left_arm
active_arm: left
passive_arm_policy: fixed_or_ignored
observation: state-based, no RGB/depth
action: [dx, dy, dz, droll, dpitch, dyaw, gripper_cmd]
```

Current status: the full data, loader, BC, Diffusion Policy, Flow Matching
Policy, dry-run rollout, and ablation-report code paths are implemented. The
current dataset is a Stage 6 fallback debug dataset for pipeline validation, not
a real successful grasp dataset.

## Environment

Workspace:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
```

Observed dependency state:

```text
ROS: Noetic
simulator: Gazebo / Project DAVE
torch: 2.11.0+cu130
cuda available: true
GPU: NVIDIA GeForce RTX 4060 Laptop GPU
casadi: 3.7.0
```

Python packages used by the pipeline include:

```text
numpy scipy pandas pyyaml tqdm matplotlib torch torchvision h5py zarr
opencv-python pillow casadi
```

Check the package is visible:

```bash
rospack find rexrov_single_oberon7_fm_dp
```

## Directory Structure

```text
rexrov_single_oberon7_fm_dp/
├── config/                 # collection, training, rollout, ablation configs
├── docs/                   # project context and stage logs
├── launch/                 # recorder, collection, rollout launch files
├── learning/
│   ├── datasets/           # .npz episode loader
│   ├── models/             # BC, Diffusion, Flow Matching models
│   ├── train/              # training scripts
│   └── eval/               # offline eval, rollout eval, ablation report
├── models/                 # package-local simple target model
├── scripts/                # ROS nodes and dataset utilities
├── src/rexrov_single_oberon7_fm_dp/
│   ├── recorder.py
│   ├── dataset_writer.py
│   ├── ros_interface.py
│   ├── expert_policy.py
│   ├── action_converter.py
│   └── success_checker.py
├── data/raw/               # episode .npz files
└── outputs/                # checkpoints, logs, eval outputs
```

## Launch Simulation

The minimal runtime inspection and smoke-test launch used so far is:

```bash
roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=false
```

This launch exposes the confirmed state topics:

```text
/rexrov/pose_gt
/joint_states
/gazebo/model_states
/gazebo/get_model_state
/rexrov/thruster_manager/input
```

MoveIt can be checked separately:

```bash
roslaunch rexrov_moveit_revised planning_context_revised.launch load_robot_description:=false
roslaunch rexrov_moveit_revised move_group_revised.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
```

MoveIt IK and groups `arm_l`, `arm_r`, `hand_l`, and `hand_r` were confirmed,
but trajectory execution is not configured because the MoveIt controller list is
empty.

## Collect Data

Record one state-based episode:

```bash
roslaunch rexrov_single_oberon7_fm_dp record_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw \
  episode_id:=stage4_smoke_runtime \
  rate_hz:=2.0 \
  max_duration_sec:=1.0 \
  require_target:=false
```

Collect one scripted expert action-label episode:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw \
  episode_id:=stage5_scripted_expert_smoke_v2 \
  rate_hz:=2.0 \
  max_duration_sec:=5.0 \
  spawn_target:=true
```

Batch collection smoke/debug path:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/batch_collect_episodes.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/batch_collection.yaml
```

The current Stage 6 debug dataset is:

```text
data/raw/stage6_debug
outputs/logs/stage6_debug/dataset_summary.json
outputs/logs/stage6_debug/dataset_split_combined.json
```

Important: this Stage 6 dataset used nominal fallback state for pipeline
debugging. It is valid for loader/training smoke tests but not for real grasp
performance claims.

Validate an episode:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/validate_episode.py \
  src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage6_debug/<episode>.npz
```

Summarize a dataset:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/summarize_dataset.py \
  --input-dir src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage6_debug \
  --output-json src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/stage6_debug/dataset_summary.json \
  --output-md src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/stage6_debug/dataset_summary.md
```

## Train BC, Diffusion Policy, And Flow Matching Policy

BC baseline:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/train/train_bc.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/train_bc.yaml
```

Diffusion Policy:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/train/train_diffusion.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/train_diffusion.yaml
```

Flow Matching Policy:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/train/train_flow_matching.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/train_flow_matching.yaml
```

Current checkpoints:

```text
outputs/checkpoints/stage7_bc_smoke/best.pt
outputs/checkpoints/stage8_diffusion_smoke/best.pt
outputs/checkpoints/stage9_flow_matching_smoke/best.pt
```

Offline evaluation examples:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/eval/eval_offline.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/train_bc.yaml \
  --split val

python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/eval/eval_offline.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/train_diffusion.yaml \
  --split val \
  --num-inference-steps 50

python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/eval/eval_offline.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/train_flow_matching.yaml \
  --split val \
  --ode-steps 50
```

## Rollout Evaluation

Dry-run unified rollout evaluation:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/eval/eval_rollout.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/eval_rollout.yaml
```

ROS rollout node:

```bash
roslaunch rexrov_single_oberon7_fm_dp rollout_policy.launch \
  policy_name:=bc \
  execute_actions:=false
```

The rollout node currently publishes clipped action labels to:

```text
/rexrov_single_oberon7_fm_dp/policy/action_ee_delta
/rexrov_single_oberon7_fm_dp/policy/status
```

Real left-arm/gripper command execution is intentionally disabled until the
controller mapping, action converter, and end-effector pose source are
confirmed.

## Ablation And Report Generation

Generate the Stage 11 comparison tables and plots:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/eval/ablation_report.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/ablation_report.yaml
```

Key output:

```text
outputs/eval/stage11_ablation/ablation_report.md
outputs/eval/stage11_ablation/ablation_summary.json
outputs/eval/stage11_ablation/policy_comparison.md
outputs/eval/stage11_ablation/inference_steps_ablation.md
```

## Current Results

Stage 11 comparison on the Stage 6 fallback validation split:

```text
policy          val_action_mse  dry_run_latency_ms  success_rate
BC              0.006436        8.451               not_evaluated
Diffusion       0.135303        65.826              not_evaluated
Flow Matching   0.087300        14.478              not_evaluated
```

Pipeline-only DP vs FM conclusion:

- Flow Matching produced lower offline action MSE and lower dry-run latency than
  Diffusion Policy on the fallback validation split.
- This is not a real grasp-success conclusion.

## Important Notes

- Do not modify official packages under `src/dave`, `src/uuv_simulator`,
  `src/uuv_manipulators`, or `src/rexrov2` for this first demo.
- The right arm remains passive or ignored in the first-version task.
- The first version is state-based only; RGB/depth collection is out of scope.
- Real success-rate evaluation requires live non-fallback data, confirmed
  left-arm and gripper command interfaces, and a valid `eef_pose` source.
- Project DAVE ocean-current disturbance ablations are deferred until the
  official DAVE ocean-current configuration is checked.
