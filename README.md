# UVMS Grasping with Generative Policies

State-based imitation learning and generative policy comparison for a
RexROV + Oberon7 underwater vehicle-manipulator system in Project DAVE /
Gazebo.

This repository contains the ROS package:

```text
rexrov_single_oberon7_fm_dp
```

The long-term motivation is underwater manipulation and grasping. The current
demonstrated scope is deliberately narrower and should be described as:

```text
active-left arm-only reaching / pre-grasp positioning
```

The project compares:

1. Behavior Cloning (BC)
2. Diffusion Policy (DP)
3. Flow Matching Policy (FM)

Two main contributions are emphasized:

- An end-to-end UVMS learning pipeline: recording, validation, scripted expert
  labels, state/action dataset schema, BC/DP/FM training, offline validation,
  and live arm-only reaching evaluation.
- A Flow Matching Policy implementation and evaluation inside this
  RexROV + Oberon7 UVMS manipulation pipeline.

## Current Status

Last updated: 2026-05-08.

The latest project result is a same-protocol formal live evaluation for
arm-only pre-grasp reaching. BC, DP, and FM were each evaluated for 10
independent cycles under the same protocol.

Important boundary:

- This is not full underwater grasping.
- The gripper is disabled.
- No hand controller is started.
- No object is claimed to be grasped, lifted, or held.
- `gripper_cmd` remains in the action vector only as a compatibility slot.
- Stage 6 fallback data is historical pipeline smoke-test data, not real task
  performance evidence.

### Final N=10 Live Arm-Only Reaching Result

Scope:

```text
task: active-left arm-only reaching / pre-grasp positioning
formal_N: 10 per method
success:
  final_distance <= 0.10 m
  and distance_reduction > 0.02 m
  and no abort
gripper_enabled: false
hand_controller_allowed: false
max_control_ticks: 9
EE delta clip: 0.005 m
joint delta clip: 0.01 rad
```

Result:

| Method | Success Count / N | Success Rate | Mean Final Distance | Mean Inference Latency | Mean Action Smoothness |
| --- | ---: | ---: | ---: | ---: | ---: |
| BC | 10/10 | 1.0 | 0.08978 m | 18.37 ms | 4.36e-05 |
| DP | 10/10 | 1.0 | 0.09130 m | 68.34 ms | 5.11e-04 |
| FM | 10/10 | 1.0 | 0.09004 m | 49.46 ms | 7.14e-04 |

Interpretation:

- All three policies repeatedly crossed the current arm-only reaching
  threshold.
- The binary success threshold is not discriminative enough to rank the three
  policies by success rate.
- Secondary metrics are more informative:
  - BC is fastest and smoothest in this N=10 run.
  - FM has the best offline action MSE and middle live latency.
  - DP succeeds but has the highest live latency and slightly larger final
    distance.
- Do not say FM beats BC/DP in live success rate; live success rate is tied.

### Latest Offline BC / DP / FM Action-MSE Comparison

The offline comparison uses the same base-relative safe-normalized arm-only
dataset and action metric.

| Method | Best Checkpoint / Rule | Offline Action MSE | Relative to BC |
| --- | --- | ---: | ---: |
| BC | best BC validation checkpoint | 3.066821534503106e-07 | baseline |
| DP | `dp30_seed86_baseline_best` | 3.1088134733181505e-07 | +1.369% |
| FM | `fm30_action_select_best_action` | 3.0398447847801435e-07 | -0.880% |

Interpretation:

- Flow Matching produced the best offline validation action MSE.
- Diffusion Policy improved with seed/objective-selection ablations but stayed
  slightly worse than BC on this metric.
- Offline action MSE is not the same as live robot success. The N=10 live result
  and offline validation result should be presented together, not substituted
  for one another.

## Task Definition

Current task:

```text
robot: RexROV + dual Oberon7 model
active arm: left Oberon7
right arm: fixed or ignored
task: arm-only reaching / pre-grasp positioning
target: static or base-relative cylinder/package-local target setup
observation: state-based, no RGB/depth
gripper: disabled
```

Policy action:

```text
a_t = [dx, dy, dz, droll, dpitch, dyaw, gripper_cmd]
```

For the current arm-only route:

```text
gripper_cmd is ignored or fixed
gripper_enabled = false
```

Reaching success:

```text
reaching_success =
    1[ ||p_eef - p_target|| < threshold ]
```

The current formal live protocol uses a threshold of `0.10 m` plus a minimum
distance reduction of `0.02 m`.

## What Has Been Built

Implemented and exercised in this package:

- ROS package for the RexROV + Oberon7 UVMS learning task.
- State-based `.npz` episode recorder and validator.
- Dataset summary and split utilities.
- Scripted expert action labels.
- Base-relative target-to-end-effector observation route.
- End-effector delta action representation.
- Left-arm joint-space command path through:

```text
/oberon7/arm_position_l/command
```

- EE-delta to left-arm command conversion for arm-only reaching.
- BC, Diffusion Policy, and Flow Matching training code.
- Offline validation and presentation-result generation.
- Formal same-protocol live arm-only reaching evaluation for BC/DP/FM.

## Environment

Tested development environment:

```text
OS / ROS: Ubuntu + ROS Noetic
simulator: Gazebo / Project DAVE
GPU used during development: NVIDIA GeForce RTX 4060 Laptop GPU
torch: 2.11.0+cu130
cuda available: true
casadi: 3.7.0
```

Workspace setup:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rospack find rexrov_single_oberon7_fm_dp
```

Python packages used by the pipeline include:

```text
numpy scipy pandas pyyaml tqdm matplotlib torch torchvision h5py zarr
opencv-python pillow casadi
```

## Directory Structure

```text
rexrov_single_oberon7_fm_dp/
|-- config/                 # collection, training, rollout, ablation configs
|-- docs/                   # project context, stage logs, status documents
|-- launch/                 # recorder, collection, rollout launch files
|-- learning/
|   |-- datasets/           # .npz episode loader
|   |-- models/             # BC, Diffusion, Flow Matching models
|   |-- train/              # training scripts
|   `-- eval/               # offline eval, rollout eval, ablation/report code
|-- models/                 # package-local target model
|-- scripts/                # ROS nodes and dataset utilities
|-- src/rexrov_single_oberon7_fm_dp/
|   |-- recorder.py
|   |-- dataset_writer.py
|   |-- ros_interface.py
|   |-- expert_policy.py
|   |-- action_converter.py
|   `-- success_checker.py
|-- data/                   # local data location; usually ignored in Git
`-- outputs/                # local generated logs/checkpoints/reports; ignored in Git
```

Note: this repository is expected to ignore generated data and outputs such as
`.npz` episodes, checkpoints, logs, and presentation PDFs. Result paths below
refer to local generated artifacts from the development workspace.

## Launch Simulation

The minimal runtime inspection and smoke-test launch used during development:

```bash
roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=false
```

Confirmed state/control topics include:

```text
/rexrov/pose_gt
/joint_states
/gazebo/model_states
/gazebo/get_model_state
/oberon7/arm_position_l/command
/oberon7/arm_position_l/state
```

MoveIt can be inspected separately:

```bash
roslaunch rexrov_moveit_revised planning_context_revised.launch load_robot_description:=false
roslaunch rexrov_moveit_revised move_group_revised.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
```

MoveIt IK and groups `arm_l`, `arm_r`, `hand_l`, and `hand_r` were confirmed.
MoveIt trajectory execution controller integration remains unresolved.

## Data Collection

Record one state-based episode:

```bash
roslaunch rexrov_single_oberon7_fm_dp record_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw \
  episode_id:=runtime_smoke \
  rate_hz:=2.0 \
  max_duration_sec:=1.0 \
  require_target:=false
```

Collect one scripted expert action-label episode:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw \
  episode_id:=scripted_expert_smoke \
  rate_hz:=2.0 \
  max_duration_sec:=5.0 \
  spawn_target:=true
```

Batch collection:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/batch_collect_episodes.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/batch_collection.yaml
```

Validate an episode:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/validate_episode.py \
  src/uvms/rexrov_single_oberon7_fm_dp/data/raw/<dataset>/<episode>.npz
```

Summarize a dataset:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/summarize_dataset.py \
  --input-dir src/uvms/rexrov_single_oberon7_fm_dp/data/raw/<dataset> \
  --output-json src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/<dataset>/dataset_summary.json \
  --output-md src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/<dataset>/dataset_summary.md
```

## Training

Behavior Cloning:

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

For the final offline comparison, the project used base-relative,
safe-normalized arm-only configs rather than the early fallback Stage 6 smoke
configs. See `docs/TRAINING_PLAN.md` and `docs/CURRENT_STATUS.md` for the
latest exact config names and result artifacts.

## Offline Evaluation

Examples:

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

Presentation-ready offline comparison artifacts were generated locally under:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_results.md
outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_results.csv
outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_slide_notes.md
```

## Rollout / Live Evaluation

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

The rollout node publishes clipped action labels to:

```text
/rexrov_single_oberon7_fm_dp/policy/action_ee_delta
/rexrov_single_oberon7_fm_dp/policy/status
```

The final same-protocol N=10 live comparison artifacts were generated locally
under:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v12b_terminal_final_distance_n10.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v12b_terminal_final_distance_n10.json
```

## Limitations

- Current task is arm-only reaching / pre-grasp positioning, not full grasping.
- Gripper command and gripper stability remain unresolved.
- B2b gripper diagnosis points to a model / Gazebo physics / zero-range
  transmitted revolute joint / controller-interface mismatch blocker.
- MoveIt IK is available, but MoveIt trajectory execution controller
  integration remains unresolved.
- Stage 6 fallback data is only useful for pipeline smoke testing.
- The N=10 success threshold is intentionally reachable and does not separate
  methods by success rate.
- The current live result does not prove broad robustness across randomized
  targets, larger initial distances, currents, contact, or full manipulation.

## Recommended Next Evaluation Improvements

Keep the current primary success criterion, but add more discriminative
secondary metrics:

- strict reaching tiers: `final_distance <= 0.095`, `0.085`, and `0.075 m`;
- median and p90 final distance;
- mean minimum distance and distance reduction;
- ticks-to-success and time-to-success;
- clip saturation and joint-delta saturation;
- IK failure count;
- randomized target offsets and harder initial-distance bins;
- eventually, gripper-enabled grasping once the gripper/controller blocker is
  resolved.

## Important Notes

- Do not modify official packages under `src/dave`, `src/uuv_simulator`,
  `src/uuv_manipulators`, or `src/rexrov2` for this package-level demo.
- The right arm remains passive or ignored in the current task.
- The first version is state-based only; RGB/depth collection is out of scope.
- Do not report `grasp_success`, `grasp_success_rate`, object grasped, object
  lifted, or object held for current results.
- Generated `data/` and `outputs/` artifacts may be ignored in GitHub to avoid
  committing large datasets, checkpoints, logs, and PDFs.
