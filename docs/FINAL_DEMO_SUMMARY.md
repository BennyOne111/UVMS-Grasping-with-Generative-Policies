# Final Demo Summary

## Current Route Clarification

The current first-version real closed-loop demo route is:

```text
RexROV + single-active-left Oberon7 arm-only reaching / pre-grasp positioning
```

This is not a learned-policy rollout yet, not grasping, and not a
success-rate evaluation. Gripper execution remains blocked and disabled.
`success=False` in current B5d'/B8' smoke data is expected and must not be
reported as grasp failure.

The long-term goal may still be underwater grasping, but current results must
use reaching/pre-grasp language:

```text
reaching_success or pregrasp_success
final_distance
distance_reduction
episode_length
action_smoothness
inference_latency
failure_reason
```

Do not report `grasp_success_rate` or claim that the object was grasped,
lifted, or held.

## Project Motivation

This project builds a first reproducible demo for comparing Behavioral Cloning
(BC), Diffusion Policy (DP), and Flow Matching Policy (FM) on an underwater
manipulation task in Project DAVE / Gazebo.

The long-term target is a RexROV + Oberon7 system that can collect expert
demonstrations and evaluate learned policies in simulation. The first version
keeps the existing RexROV + dual Oberon7 model but treats only the left arm as
active. This keeps the task small enough to debug the full learning pipeline
before adding bimanual coordination or image observations.

## Method

Task setup:

```text
robot: RexROV + dual Oberon7
active arm: left Oberon7
passive arm: right Oberon7 fixed or ignored
target: simple geometric object, currently cylinder_target
observation: state-based, no RGB/depth
action: [dx, dy, dz, droll, dpitch, dyaw, gripper_cmd]
```

Policy methods:

- BC: MLP mapping `obs_history -> action_chunk`.
- Diffusion Policy: conditional denoising model over future action chunks.
- Flow Matching Policy: conditional velocity field integrated from Gaussian
  noise to an action chunk.

Fair-comparison choices:

- Same `.npz` episode schema.
- Same Stage 6 train/validation split.
- Same observation representation and action dimension.
- Same normalization path.
- Comparable small state-based MLP capacity for DP and FM.

## System Architecture

```text
Project DAVE / Gazebo
  -> ROS state topics
  -> episode recorder
  -> per-episode .npz files
  -> validator and dataset summary
  -> UVMS episode dataset loader
  -> BC / Diffusion / Flow Matching training
  -> offline evaluation
  -> dry-run rollout policy runtime
  -> ablation report tables and plots
```

Important runtime topics confirmed during earlier stages:

```text
/rexrov/pose_gt
/joint_states
/gazebo/model_states
/gazebo/get_model_state
/rexrov/thruster_manager/input
```

MoveIt status:

- `move_group`, `/compute_ik`, and groups `arm_l`, `arm_r`, `hand_l`,
  `hand_r` were confirmed.
- MoveIt trajectory execution is not configured because the controller list is
  empty.

## Data Collection Flow

Episode format:

```text
timestamp
base_pose
base_velocity
active_joint_positions
active_joint_velocities
gripper_state
target_pose
eef_pose
relative_target_to_eef
action_ee_delta
raw_command
done
success
metadata_json
```

The first dataset path is:

```text
data/raw/stage6_debug
outputs/logs/stage6_debug/dataset_split_combined.json
```

Stage 6 dataset status:

```text
episodes_total: 20
episodes_valid: 20
train: 16
val: 4
mean_T: 10
action_dim: 7
success_rate: 0.0
```

Important limitation:

- Stage 6 used nominal fallback base/joint/target state to complete the data
  pipeline without modifying official packages.
- It is suitable for loader, normalization, training-loop, and report smoke
  tests.
- It is not a real physical grasp dataset.

## Model Comparison

Current checkpoints:

```text
BC:              outputs/checkpoints/stage7_bc_smoke/best.pt
Diffusion:       outputs/checkpoints/stage8_diffusion_smoke/best.pt
Flow Matching:   outputs/checkpoints/stage9_flow_matching_smoke/best.pt
```

Stage 11 comparison:

```text
policy          episodes  horizon  val_action_mse  val_normalized_mse  dry_run_latency_ms  success_rate
BC              20        16       0.006436        0.092663            8.451               not_evaluated
Diffusion       20        16       0.135303        0.764208            65.826              not_evaluated
Flow Matching   20        16       0.087300        0.357012            14.478              not_evaluated
```

DP / FM step ablation:

```text
Diffusion steps 5:   action_mse=0.326742, mean_latency_ms=10.802
Diffusion steps 10:  action_mse=0.217743, mean_latency_ms=9.826
Diffusion steps 20:  action_mse=0.110831, mean_latency_ms=10.241
FM ode_steps 2:      action_mse=0.070893, mean_latency_ms=2.143
FM ode_steps 4:      action_mse=0.100395, mean_latency_ms=2.628
FM ode_steps 8:      action_mse=0.077081, mean_latency_ms=4.010
FM ode_steps 16:     action_mse=0.062849, mean_latency_ms=5.011
```

Pipeline-only conclusion:

- On the fallback validation split, Flow Matching produced lower action MSE
  than Diffusion Policy and lower dry-run latency.
- BC has the lowest offline MSE on this small deterministic fallback dataset.
- These results validate the comparison machinery; they do not establish real
  underwater grasping performance.

## Experiment Artifacts

Main reports:

```text
outputs/eval/stage10_rollout/rollout_eval_summary.md
outputs/eval/stage11_ablation/ablation_report.md
outputs/eval/stage11_ablation/ablation_summary.json
```

Stage 11 tables and plots:

```text
outputs/eval/stage11_ablation/policy_comparison.md
outputs/eval/stage11_ablation/inference_steps_ablation.md
outputs/eval/stage11_ablation/planned_ablation_status.md
outputs/eval/stage11_ablation/policy_action_mse_comparison.png
outputs/eval/stage11_ablation/policy_latency_comparison.png
outputs/eval/stage11_ablation/policy_smoothness_comparison.png
outputs/eval/stage11_ablation/inference_steps_mse_latency.png
outputs/eval/stage11_ablation/success_rate_status.png
```

## Reproduction Commands

Environment:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
```

Train:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/train/train_bc.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/train_bc.yaml

python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/train/train_diffusion.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/train_diffusion.yaml

python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/train/train_flow_matching.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/train_flow_matching.yaml
```

Dry-run rollout and ablation report:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/eval/eval_rollout.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/eval_rollout.yaml

python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/eval/ablation_report.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/ablation_report.yaml
```

## Current Limitations

- The current dataset is fallback state data, not real demonstration data.
- Stage 6 is still a fallback-data smoke dataset and cannot be used as real
  demonstration evidence.
- B5d' arm-only scripted reaching is debug-smoke minimal resolved, but B8'
  real non-fallback reaching/pre-grasp data collection is still next.
- `eef_pose` and `relative_target_to_eef` are now available in B5d' non-fallback
  recorder smoke episodes, but historical Stage 6 data does not contain real
  live-state demonstrations.
- Gripper command/stability remains blocked and is future work.
- The left-arm and gripper command interfaces are not confirmed.
- The action converter from end-effector delta action to safe joint/IK command
  is not complete.
- Stage 10 rollout is dry-run only and reports `success_rate=not_evaluated`.
- Disturbance ablations with ocean currents have not been run; Project DAVE
  current configuration must be checked in official docs first.

## Next Work

1. Fix live `/joint_states`, `/rexrov/pose_gt`, and target state collection.
2. Confirm left-arm and gripper command topics or action servers.
3. Add TF or MoveIt-based `eef_pose` and `relative_target_to_eef`.
4. Implement and safety-test the EE-delta-to-IK/joint action converter.
5. Collect non-fallback 50/100/300 episode datasets.
6. Retrain BC, DP, and FM on real demonstrations.
7. Run real Gazebo rollout evaluation with success rate, final distance,
   episode length, smoothness, and latency.
8. Add disturbance ablations only after checking official Project DAVE ocean
   current documentation.
