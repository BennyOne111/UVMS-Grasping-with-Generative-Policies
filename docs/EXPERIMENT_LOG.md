# Experiment Log

## 2026-05-07 Formal BC/DP/FM Arm-Only Live Protocol Attempt

Commands/checks performed:

- Read the current project and package docs.
- Inspected relevant scripts, configs, launch files, checkpoints, and rollout
  artifacts.
- Ran read-only ROS runtime checks:
  - `rostopic list`
  - `/joint_states`
  - `/rexrov/pose_gt`
  - `/gazebo/model_states`
  - TF `rexrov/base_link -> oberon7_l/end_effector`
  - `/oberon7/arm_position_l/state`
  - `/controller_manager/list_controllers`
- Added a method-general policy loader path to the existing base-relative h8
  xyz execution adapter so BC / DP / FM can use the same live protocol.
- Added an optional strict `target_base_drift` check to
  `scripts/check_b8_initial_state_gate.py`.
- Created formal protocol artifacts and attempted BC cycle 0.

No BC rollout command was sent.
No DP/FM dry-run or live smoke was started.
No gripper command was sent.
No hand controller was started.
No grasp success was claimed.

BC cycle 0:

```text
return_to_reference reached=true
return commands_sent=0
pre_gate attempts=3
pre_gate passes=0
best retry initial_distance=0.11371573515906652
best retry target_base_drift=0.010550711129789662
best retry relative_base_drift=0.007371669176824283
strict target/relative drift threshold=0.001
stop_reason=strict_pre_gate_failed_target_relative_drift
```

Artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/formal_protocol.md
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/formal_protocol.json
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/bc/cycle_0/return_to_reference.json
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/bc/cycle_0/pre_gate_0.json
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/bc/cycle_0/pre_gate_0_retry_1.json
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/bc/cycle_0/pre_gate_0_retry_2.json
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/bc/cycle_0/smoke.json
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/bc/cycle_0/post_gate.json
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/bc/cycle_0/summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
```

Outcome:

```text
complete_three_method_live_comparison=false
BC success_count=0/1, success_rate=0.0, abort_count=1
DP not run
FM not run
equal_N_across_methods=false
```

Interpretation: this was a shared initial-gate failure caused by target/base
sync drift. It is not a policy rollout success-rate result and not a grasping
result.

Follow-up target-gate restart:

```text
reset target helper passed
b8_target_gate_probe.launch restarted
target model present=true
BC return_to_reference reached=true
strict post-restart pre-gate failed
retry target_base_drift=0.006711007793366516
retry relative_base_drift=0.006271075196806217
policy rollout commands sent=false
gripper commands sent=false
```

Additional artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol_after_target_restart/
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_after_target_restart.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_after_target_restart.json
```

Outcome remains unchanged: no complete BC/DP/FM live success-rate comparison.

## 2026-05-07 Aggressive Live Evaluation Protocol v4

Commands/checks performed:

- Restarted the package-local target gate probe.
- Added `scripts/run_b8_bc_dp_fm_live_eval.py` to orchestrate shared
  return/gate/dry-run/live-smoke/formal-cycle artifacts.
- Fixed two runner bugs:
  - workspace root path resolution;
  - absolute `output_json` paths for roslaunch policy nodes.
- Ran protocol v4 with shared settings:
  `initial_distance_max=0.125`, `target_drift_max=0.02`,
  `relative_drift_max=0.02`, `max_control_ticks=9`, `clip=0.005 m`,
  `max_joint_delta=0.01 rad`.

No gripper command was sent.
No hand controller was started.
No grasp success was claimed.

Result:

```text
BC: 0/1, success_rate=0.0, abort_count=1
BC failure_reason=arm_command_conversion_or_execution_failed
BC IK error code=-31
DP: 3/3, success_rate=1.0, abort_count=0
FM: 3/3, success_rate=1.0, abort_count=0
equal_N_across_methods=false
complete_three_method_live_comparison=false
```

Final artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol_v4/
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
```

Interpretation: DP/FM have completed N=3 live arm-only reaching evidence. BC
does not have a completed formal success rate under the same protocol because
its first cycle safety-aborted after an IK conversion failure.

## 2026-05-05 B8' Reset/Settle Strategy Definition

Commands/checks performed:

- Added bounded return-to-reference tool:
  `scripts/return_left_arm_to_reference.py`.
- Ran syntax check.
- Ran CLI help check.
- Ran `--dry-run` from the current post-command state; no command was sent.

No episode was collected for this entry.
No training command was run.
No learned rollout command was run.
No gripper command was sent.
No hand controller was started.

Dry-run result:

```text
commands_sent: 0
gripper_commands_sent: false
reached: false
joint_l2_error: 0.11564320348459194
joint_max_abs_error: 0.08137583509102786
```

Selected strategy:

```text
bounded return-to-reference active-left joint command
-> target-aware initial-state gate
-> next episode only if the gate passes
```

This defines the reset/settle path; it does not yet verify live return command
execution.

## 2026-05-05 B8' One Gated Arm-Only Verification

Commands/checks performed:

- Ran pre-episode target-aware initial-state gate.
- Collected exactly one short arm-only reaching/pre-grasp verification episode:
  `data/raw/b8_gated_arm_verify_1/b8_gated_arm_verify_1_0000.npz`.
- Ran post-episode target-aware initial-state gate.
- Ran validator.
- Ran offline quality, direction, and command-motion diagnostics.

No learned policy rollout was run.
No BC / Diffusion Policy / Flow Matching Policy training was run.
No hand controller was started.
No gripper command was sent.
No grasp success was claimed.

Result:

```text
validator: PASS
success: true
recorded_success_distance_m: 0.045301559855776316
initial_distance: 0.10625611763364251
final_distance: 0.045301559855776316
distance_reduction: 0.060954557777866195
mean_best_action_to_eef_cosine: 0.8718392906129798
mean_best_realized_gain_along_action: 0.24521231853273232
```

Post-gate result:

```text
passed: false
relative_base_drift_ok: false
relative_base_drift: 0.07180542804879099
initial_distance: 0.04013113557371512
```

Interpretation:

- One gated arm-only verification episode is smoke-level resolved.
- Multi-episode repeatability remains blocked because the arm remains in the
  reached/pregrasp configuration after the command.
- Next work should define reset/settle/reinitialization before any additional
  collection.

## 2026-05-05 B8' Initial-State Gate Preparation

Commands/checks performed:

- Re-read root docs and package docs requested for the current B8' blocker.
- Inspected `collect_episode.launch`, `batch_collect_episodes.py`,
  `expert_policy.py`, `arm_command_converter.py`, and `recorder.py`.
- Added read-only gate script:
  `scripts/check_b8_initial_state_gate.py`.
- Ran syntax check:
  `python3 -m py_compile scripts/check_b8_initial_state_gate.py`.
- Ran CLI help check after sourcing the workspace:
  `source devel/setup.bash; python3 scripts/check_b8_initial_state_gate.py --help`.

No Gazebo simulation was launched.
No new episode was collected.
No training command was run.
No learned rollout command was run.
No arm reset command was sent.
No gripper command was sent.
No hand controller was started.

Purpose:

```text
Before any further B8' collection attempt, check live initial active-left joint
configuration, EEF/base pose, relative target/EEF vector, and initial distance
against a successful reference episode.
```

Current blocker decision:

```text
B8' tail degradation is not resolved. The next evidence needed is a live
initial-state gate result and, if the gate fails, a minimal reset/settle fix
before any additional collection.
```

Follow-up target-only probe support:

- Added `launch/b8_target_gate_probe.launch`.
- Verified XML parse and `roslaunch --ros-args`.
- This launch only spawns `cylinder_target_gate_probe` and starts
  `base_relative_target.py`.
- It does not start recorder, expert, arm command, hand controller, gripper
  command, training, or learned rollout.

## 2026-05-05 B8' Debug Batch Failure Analysis

Commands/checks performed:

- Read current package docs before analysis.
- Added read-only offline analyzer:
  `scripts/analyze_b8_debug_batch_failure.py`.
- Ran syntax check:
  `python3 -m py_compile scripts/analyze_b8_debug_batch_failure.py`.
- Ran the analyzer over existing episodes only:
  `data/raw/b8_reaching_debug_10/b8_reaching_debug_10_*.npz`.
- Read existing command-motion and direction diagnostics for consistency.
- Updated docs with the failure-analysis result.

No Gazebo simulation was launched.
No new episode was collected.
No training command was run.
No learned rollout command was run.
No gripper command was sent.
No hand controller was started.

Output paths:

```text
outputs/logs/b8_reaching_debug_10_failure_analysis/failure_analysis_summary.json
outputs/logs/b8_reaching_debug_10_failure_analysis/failure_analysis_summary.md
outputs/logs/b8_reaching_debug_10_failure_analysis/success_vs_failure_table.csv
outputs/logs/b8_reaching_debug_10_failure_analysis/success_vs_failure_table.md
outputs/logs/b8_reaching_debug_10_failure_analysis/initial_condition_drift.json
outputs/logs/b8_reaching_debug_10_failure_analysis/per_episode_distance_curves.png
outputs/logs/b8_reaching_debug_10_failure_analysis/command_motion_success_vs_failure.png
outputs/logs/b8_reaching_debug_10_failure_analysis/joint_initial_drift.png
outputs/logs/b8_reaching_debug_10_failure_analysis/base_target_drift.png
```

Result:

```text
success episodes: 0000-0006
failure episodes: 0007-0009
initial_distance success/failure mean: 0.108700 / 0.108612
distance_reduction success/failure mean: 0.040734 / -0.009090
best_action_to_eef_cosine success/failure mean: 0.823278 / -0.071778
best_realized_gain_along_action success/failure mean: 0.209131 / -0.021860
action_relative_cosine success/failure mean: 0.897726 / 0.943494
joint_initial_drift_from_ep0 success/failure mean: 0.304920 / 0.806195
target_base_max_step success/failure mean: 0.006151 / 0.001934
```

Interpretation:

- The failed tail is not explained by initial distance.
- Scripted action direction remains target-aligned in failed episodes.
- The strongest signal is command-to-motion degradation after cross-episode
  configuration drift.
- Target/base source-sync and episode duration are less likely primary causes.

Decision:

```text
Do not collect more B8' data, train BC / DP / FM, or run learned rollout until
the per-episode reset/settle and command-to-motion degradation are addressed.
```

## 2026-05-04 Documentation Alignment: Arm-Only Route

Commands/checks performed:

- Read the project documentation set.
- Updated documentation only under
  `src/uvms/rexrov_single_oberon7_fm_dp/docs`.
- No Gazebo command was run.
- No training command was run.
- No rollout command was run.
- No README or code/config/launch/script file was modified.

Current interpretation recorded:

```text
B5d' arm-only scripted reaching expert: debug-smoke minimal resolved
B8' next: 5 short real non-fallback arm-only reaching/pre-grasp episodes
```

Important boundaries:

- This is not learned-policy rollout evidence.
- This is not grasping.
- This is not a success-rate evaluation.
- Gripper command/stability remains blocked and disabled.
- Stage 6 fallback data remains pipeline-smoke data only.

## 2026-05-05 B8' Repeatability Smoke

Commands/checks performed:

- Read root and package docs before running.
- Added read-only summary script:
  `scripts/summarize_b8_repeatability_smoke.py`.
- Ran preflight:
  - launch XML validation;
  - `b8_reaching_tuned_v3_episode.launch --ros-args`;
  - output path collision checks;
  - ROS graph check.
- Started minimal runtime:
  - `roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=false`;
  - `roslaunch rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch allow_trajectory_execution:=false`;
  - `roslaunch rexrov_single_oberon7_fm_dp load_left_controllers.launch start:=true load_hand:=false`;
  - `roslaunch rexrov_single_oberon7_fm_dp world_base_tf_bridge.launch`.
- Collected five short B8' episodes with
  `b8_reaching_tuned_v3_episode.launch`.
- Ran validator, reaching quality, reaching direction, command-motion, and
  repeatability summary diagnostics.
- Shut down all runtime processes after collection.

No training command was run.
No learned rollout command was run.
No gripper command was sent.
No hand controller was started.

Key output paths:

```text
data/raw/b8_reaching_repeatability_smoke/
outputs/logs/b8_reaching_repeatability_smoke/
outputs/logs/b8_reaching_repeatability_smoke_quality/
outputs/logs/b8_reaching_repeatability_smoke_direction/
outputs/logs/b8_reaching_repeatability_smoke_command_motion/
```

Result:

```text
episodes_total: 5
validator_pass_count: 5
success_count: 5
reaching_success_rate: 1.0
all_required_metadata_ok: true
all_success_metadata_consistent: true
mean_final_distance: 0.06034401658235772
mean_distance_reduction: 0.0473147271937287
max_target_step_base: 0.014892885342403243
large_target_step_indices: [] for all episodes
mean_best_action_to_eef_cosine: 0.7559808833882034
mean_best_lag_steps: 2.2
mean_best_realized_gain_along_action: 0.2432157689973347
```

Interpretation:

- B8' repeatability smoke is resolved at the 5-episode smoke level.
- This is arm-only reaching/pre-grasp evidence, not grasping.
- This is not learned rollout evidence and not BC/DP/FM training evidence.
- Next data action should be a small deliberate real non-fallback arm-only
  collection plan, not immediate large-scale expansion.

## 2026-04-29 Stage 0 Initialization

Commands/checks performed:

- Confirmed workspace path: `/home/benny/uuv_manipulator_ws`
- Listed workspace root: `build`, `devel`, `docs`, `logs`, `src`
- Read `docs/PROJECT_MAP_FOR_DP_FM.md`
- Confirmed target package did not exist before creation
- Checked ROS package path after sourcing `devel/setup.bash`
- Listed relevant `rospack` entries matching `uvms|rexrov|oberon|dave|uuv`
- Checked ML dependencies:
  - `torch: 2.11.0+cu130`
  - `cuda: True`
  - `gpu: NVIDIA GeForce RTX 4060 Laptop GPU`
  - `casadi: 3.7.0`
- Created package with `catkin_create_pkg rexrov_single_oberon7_fm_dp rospy std_msgs geometry_msgs nav_msgs sensor_msgs trajectory_msgs control_msgs`
- Built only the new package with `catkin build rexrov_single_oberon7_fm_dp`
- Verified after re-sourcing `devel/setup.bash`:
  - `rospack find rexrov_single_oberon7_fm_dp`
  - result: `/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp`

No Gazebo simulation was launched.

No recorder, expert policy, training code, or evaluator was implemented.

Note: command execution required elevated local command execution because the default sandbox could not create a namespace in this environment.

## 2026-05-01 Stage 6 Batch Collection

Commands/checks performed:

- Added `config/batch_collection.yaml`.
- Added `scripts/batch_collect_episodes.py`.
- Added `scripts/summarize_dataset.py`.
- Ran Python syntax checks for package modules and scripts.
- Ran YAML parse checks for package configs.
- Ran XML check for `launch/collect_episode.launch`.
- Built the package with `catkin build rexrov_single_oberon7_fm_dp`.
- Ran 5-episode smoke collection.
- Ran 20-episode debug collection in two parts:
  - first run produced 16 valid episodes before repeated Gazebo service calls blocked;
  - after removing per-episode unpause/delete calls for `spawn_target=false`, a second run produced 4 additional valid episodes.
- Ran `summarize_dataset.py` on smoke and debug datasets.
- Wrote combined debug split:
  - train: 16
  - val: 4
  - test: 0

Key output paths:

```text
data/raw/stage6_smoke
data/raw/stage6_debug
outputs/logs/stage6_smoke/dataset_summary.json
outputs/logs/stage6_debug/dataset_summary.json
outputs/logs/stage6_debug/dataset_split_combined.json
```

Stage 6 result:

```text
debug episodes_total: 20
debug episodes_valid: 20
debug episodes_invalid: 0
debug success_rate: 0.0
debug mean_T: 10.0
```

Important limitation:

- This collection used explicit nominal fallback for base, joint, and target state because the current runtime did not reliably publish live samples to the recorder and target spawn services could block.
- The dataset is valid for pipeline smoke tests, not for real grasp policy conclusions.

## 2026-05-01 Stage 7 BC Baseline Smoke Test

Commands/checks performed:

- Added BC training config at `config/train_bc.yaml`.
- Added state-based episode loader, MLP BC policy, trainer, and offline evaluator.
- Ran Python syntax checks for Stage 7 files.
- Parsed `config/train_bc.yaml` with PyYAML.
- Loaded the Stage 6 debug split through `UVMSEpisodeDataset`.
- Trained the BC MLP for 120 epochs on the 20-episode fallback debug dataset.
- Ran offline evaluation on train and validation splits.

Dataset loader check:

```text
train_samples: 112
val_samples: 28
obs_dim: 38
action_dim: 7
obs_horizon: 4
action_horizon: 16
first_sample_action_mask_valid: 7
```

Training result:

```text
device: cuda
initial train_loss: 0.42980525
final train_loss: 0.04464374
best val_loss: 0.09266304
final val_loss: 0.09374733
```

Offline eval result:

```text
train normalized_mse: 0.05121726
train action_mse: 0.00359283
train valid_action_steps: 448

val normalized_mse: 0.09266304
val action_mse: 0.00643590
val valid_action_steps: 112
```

Key output paths:

```text
outputs/checkpoints/stage7_bc_smoke/best.pt
outputs/checkpoints/stage7_bc_smoke/last.pt
outputs/checkpoints/stage7_bc_smoke/normalization_stats.json
outputs/logs/stage7_bc_smoke/train_summary.json
outputs/eval/stage7_bc_smoke/offline_eval_train.json
outputs/eval/stage7_bc_smoke/offline_eval_val.json
outputs/eval/stage7_bc_smoke/pred_vs_expert_train.png
outputs/eval/stage7_bc_smoke/pred_vs_expert_val.png
```

Environment note:

- TensorBoard import failed because the active Anaconda protobuf extension
  required `GLIBCXX_3.4.29` from `libstdc++`.
- The trainer fell back to a no-op writer and recorded the disabled status in
  `train_summary.json`; JSON summaries and checkpoints were still written.

Interpretation:

- BC loss decreased, so the Stage 7 loader, normalization, masked action-chunk
  loss, checkpointing, and offline evaluation path are functional.
- This experiment used the Stage 6 fallback dataset and is only a pipeline
  sanity check, not a real grasp-performance result.

## 2026-05-01 Stage 8 Diffusion Policy Smoke Test

Commands/checks performed:

- Added `config/train_diffusion.yaml`.
- Added `learning/models/diffusion_policy.py`.
- Added `learning/train/train_diffusion.py`.
- Extended `learning/eval/eval_offline.py` with `--policy-type diffusion`.
- Ran Python syntax checks for Stage 8 files.
- Parsed `config/train_diffusion.yaml` with PyYAML.
- Ran a minimal loader/model forward pass and sampled a `[1, 16, 7]` action chunk.
- Trained the Diffusion Policy for 160 epochs on the same Stage 6 fallback
  debug split used by BC.
- Ran offline diffusion sampling evaluation on train and validation splits.
- Re-ran BC validation eval to confirm the expanded evaluator still supports BC.

Model:

```text
condition: obs_history [B, 4, 38]
target: action_chunk [B, 16, 7]
policy: DDPM-style epsilon prediction
denoiser: conditional MLP [256, 256, 256]
diffusion steps: 50
inference steps: 50
```

Training result:

```text
device: cuda
initial train_loss: 1.03681373
final train_loss: 0.32737366
best val_loss: 0.30106574
final val_loss: 0.35403574
```

Offline eval result:

```text
train normalized_mse: 0.77574102
train action_mse: 0.14291643
train valid_action_steps: 448

val normalized_mse: 0.76420820
val action_mse: 0.13530311
val valid_action_steps: 112
```

Key output paths:

```text
outputs/checkpoints/stage8_diffusion_smoke/best.pt
outputs/checkpoints/stage8_diffusion_smoke/last.pt
outputs/checkpoints/stage8_diffusion_smoke/normalization_stats.json
outputs/logs/stage8_diffusion_smoke/train_summary.json
outputs/eval/stage8_diffusion_smoke/offline_eval_diffusion_train.json
outputs/eval/stage8_diffusion_smoke/offline_eval_diffusion_val.json
outputs/eval/stage8_diffusion_smoke/pred_vs_expert_diffusion_train.png
outputs/eval/stage8_diffusion_smoke/pred_vs_expert_diffusion_val.png
```

Environment note:

- TensorBoard is still disabled by the same `GLIBCXX_3.4.29` protobuf import
  issue recorded in Stage 7.
- The diffusion trainer uses the same no-op writer fallback and still writes
  checkpoints plus JSON summaries.

Interpretation:

- Denoising loss decreased, and the policy can generate action chunks from
  Gaussian noise.
- Sampling MSE is higher than BC on the tiny deterministic fallback dataset.
  This Stage 8 result validates the diffusion pipeline only; it is not a
  meaningful policy-quality comparison.

## 2026-05-01 Stage 9 Flow Matching Policy Smoke Test

Commands/checks performed:

- Added `config/train_flow_matching.yaml`.
- Added `learning/models/flow_matching_policy.py`.
- Added `learning/train/train_flow_matching.py`.
- Extended `learning/eval/eval_offline.py` with `--policy-type flow_matching`.
- Ran Python syntax checks for Stage 9 files.
- Parsed `config/train_flow_matching.yaml` with PyYAML.
- Ran a minimal loader/model forward pass and sampled a `[1, 16, 7]` action chunk.
- Trained the Flow Matching Policy for 160 epochs on the same Stage 6 fallback
  debug split used by BC and Diffusion Policy.
- Ran offline Euler ODE sampling evaluation on train and validation splits.
- Re-ran BC and Diffusion validation evals to confirm the expanded evaluator
  still supports earlier checkpoints.

Model:

```text
condition: obs_history [B, 4, 38]
target: action_chunk [B, 16, 7]
policy: rectified-flow / flow matching velocity prediction
velocity field: conditional MLP [256, 256, 256]
time_embed_dim: 64
ode_steps: 50
```

Training result:

```text
device: cuda
initial train_loss: 1.44762514
final train_loss: 0.49487846
best val_loss: 0.39671761
final val_loss: 0.50331438
```

Offline eval result:

```text
train normalized_mse: 0.36070445
train action_mse: 0.09820177
train valid_action_steps: 448

val normalized_mse: 0.35701191
val action_mse: 0.08730043
val valid_action_steps: 112
```

Key output paths:

```text
outputs/checkpoints/stage9_flow_matching_smoke/best.pt
outputs/checkpoints/stage9_flow_matching_smoke/last.pt
outputs/checkpoints/stage9_flow_matching_smoke/normalization_stats.json
outputs/logs/stage9_flow_matching_smoke/train_summary.json
outputs/eval/stage9_flow_matching_smoke/offline_eval_flow_matching_train.json
outputs/eval/stage9_flow_matching_smoke/offline_eval_flow_matching_val.json
outputs/eval/stage9_flow_matching_smoke/pred_vs_expert_flow_matching_train.png
outputs/eval/stage9_flow_matching_smoke/pred_vs_expert_flow_matching_val.png
```

Environment note:

- TensorBoard is still disabled by the same `GLIBCXX_3.4.29` protobuf import
  issue recorded in Stages 7 and 8.
- The Flow Matching trainer uses the same no-op writer fallback and still
  writes checkpoints plus JSON summaries.

Interpretation:

- Flow loss decreased, and the policy can generate action chunks from Gaussian
  noise through Euler ODE integration.
- FM, DP, and BC now share the same loader, split, normalization path, and
  offline eval interface.
- This Stage 9 result validates the FM pipeline only; it is not a meaningful
  policy-quality comparison because the dataset remains nominal fallback data.

## 2026-05-01 Stage 10 Rollout Node And Unified Evaluation

Commands/checks performed:

- Added `config/eval_rollout.yaml`.
- Added `learning/eval/policy_runtime.py`.
- Added `learning/eval/eval_rollout.py`.
- Added `scripts/rollout_policy_node.py`.
- Added `launch/rollout_policy.launch`.
- Updated `CMakeLists.txt` to install the rollout node script.
- Ran Python syntax checks for Stage 10 files.
- Parsed `config/eval_rollout.yaml` with PyYAML.
- Parsed `launch/rollout_policy.launch` as XML.
- Ran unified dry-run rollout evaluation for BC, Diffusion Policy, and Flow
  Matching Policy.
- Built the package with `catkin build rexrov_single_oberon7_fm_dp`.

Important safety decision:

- Real low-level arm/gripper execution is not enabled in Stage 10 because the
  left-arm and gripper command interfaces remain unconfirmed.
- The rollout node defaults to `execute_actions=false` and publishes clipped
  policy action labels only.
- If `execute_actions=true` is requested, the node logs a warning and still
  refuses real controller execution.

Dry-run rollout evaluation:

```text
policy          loaded  generated  success_rate   final_distance  mean_latency_ms  smoothness  failure_reason
BC              true    true       not_evaluated  unavailable     8.451            0.186389    controller_mapping_unconfirmed
Diffusion       true    true       not_evaluated  unavailable     65.826           0.378986    controller_mapping_unconfirmed
Flow Matching   true    true       not_evaluated  unavailable     14.478           0.369584    controller_mapping_unconfirmed
```

Key output paths:

```text
outputs/eval/stage10_rollout/rollout_eval_summary.json
outputs/eval/stage10_rollout/rollout_eval_summary.md
```

Build result:

```text
catkin build rexrov_single_oberon7_fm_dp: succeeded
```

Build warning:

- `gazebo_msgs` is deprecated with Gazebo classic end-of-life. This warning is
  inherited from the current ROS/Gazebo stack and did not block Stage 10.

Interpretation:

- Stage 10 validates policy runtime loading, normalization reuse, action-chunk
  generation, clipping, ROS action-label publishing, and unified reporting.
- It does not validate real Gazebo grasp rollouts yet. Real success rate and
  final distance remain unavailable until controller execution, `eef_pose`, and
  non-fallback live data collection are fixed.

## 2026-05-01 Stage 11 Ablation And Comparison Report

Commands/checks performed:

- Added `config/ablation_report.yaml`.
- Added `learning/eval/ablation_report.py`.
- Parsed `config/ablation_report.yaml` with PyYAML.
- Ran Python syntax checks for `learning/eval/ablation_report.py`.
- Generated the Stage 11 ablation report from existing Stage 6-10 artifacts.
- Did not run long retraining, Gazebo simulation, or disturbance simulation.

Output artifacts:

```text
outputs/eval/stage11_ablation/ablation_report.md
outputs/eval/stage11_ablation/ablation_summary.json
outputs/eval/stage11_ablation/policy_comparison.csv
outputs/eval/stage11_ablation/policy_comparison.md
outputs/eval/stage11_ablation/inference_steps_ablation.csv
outputs/eval/stage11_ablation/inference_steps_ablation.md
outputs/eval/stage11_ablation/planned_ablation_status.csv
outputs/eval/stage11_ablation/planned_ablation_status.md
outputs/eval/stage11_ablation/policy_action_mse_comparison.png
outputs/eval/stage11_ablation/policy_latency_comparison.png
outputs/eval/stage11_ablation/policy_smoothness_comparison.png
outputs/eval/stage11_ablation/inference_steps_mse_latency.png
outputs/eval/stage11_ablation/success_rate_status.png
```

BC / Diffusion Policy / Flow Matching comparison:

```text
policy          episodes  horizon  val_action_mse  val_normalized_mse  dry_run_latency_ms  dry_run_smoothness  success_rate
BC              20        16       0.006436        0.092663            8.451               0.186389            not_evaluated
Diffusion       20        16       0.135303        0.764208            65.826              0.378986            not_evaluated
Flow Matching   20        16       0.087300        0.357012            14.478              0.369584            not_evaluated
```

DP / FM inference-step ablation:

```text
policy          step_type             steps  action_mse  normalized_mse  mean_latency_ms  action_smoothness
Diffusion       num_inference_steps   5      0.326742    1.037157        10.802           1.769585
Diffusion       num_inference_steps   10     0.217743    0.865444        9.826            1.276770
Diffusion       num_inference_steps   20     0.110831    0.609261        10.241           0.795342
Flow Matching   ode_steps             2      0.070893    0.317776        2.143            0.700992
Flow Matching   ode_steps             4      0.100395    0.339696        2.628            0.759390
Flow Matching   ode_steps             8      0.077081    0.294979        4.010            0.665033
Flow Matching   ode_steps             16     0.062849    0.322429        5.011            0.645247
```

Core conclusion:

- On the Stage 6 fallback validation split, Flow Matching produced lower
  action MSE than Diffusion Policy (`0.087300` vs `0.135303`) and lower dry-run
  latency (`14.478 ms` vs `65.826 ms`).
- This is a pipeline-only DP-vs-FM conclusion. It is not a real grasp
  performance claim because the dataset is fallback data and real controller
  rollout remains unavailable.

Planned ablation status:

- Data-volume ablation: `20 episodes` is completed with the Stage 6 fallback
  debug dataset. `50`, `100`, and `300` episode settings are not run because
  they require additional non-fallback data collection and retraining.
- Horizon ablation: `action_horizon=16` is completed. `8` and `32` are not run
  because they require retraining.
- Disturbance ablation: not run. Project DAVE ocean-current plugin and launch
  configuration must be checked against official DAVE documentation before
  enabling `no_current`, `weak_current`, or `medium_current` variants.

Reproducibility pointers:

```text
config/ablation_report.yaml
outputs/checkpoints/stage7_bc_smoke/best.pt
outputs/checkpoints/stage8_diffusion_smoke/best.pt
outputs/checkpoints/stage9_flow_matching_smoke/best.pt
outputs/eval/stage10_rollout/rollout_eval_summary.json
outputs/eval/stage11_ablation/ablation_summary.json
```

## 2026-05-01 Stage 12 Demo, README, And Final Report Materials

Commands/checks performed:

- Re-read root docs and all package docs before stage work.
- Checked workspace path, PyTorch/CUDA/GPU state, and `rospack find`.
- Inspected package scripts, configs, output artifacts, and existing docs.
- Added a package top-level `README.md`.
- Added `docs/FINAL_DEMO_SUMMARY.md`.
- Updated project context, task definition, dataset schema, training plan,
  experiment log, stage progress, and TODO docs.
- Did not delete intermediate logs or experiment artifacts.
- Did not run Gazebo, training, rollout execution, or disturbance simulation.

Files added:

```text
README.md
docs/FINAL_DEMO_SUMMARY.md
```

Files updated:

```text
docs/PROJECT_CONTEXT.md
docs/TASK_DEFINITION.md
docs/DATASET_SCHEMA.md
docs/TRAINING_PLAN.md
docs/EXPERIMENT_LOG.md
docs/STAGE_PROGRESS.md
docs/TODO.md
```

Demo packaging result:

- A new reader can start from `README.md` to understand the project goal,
  environment, directory structure, launch commands, data collection commands,
  training commands, rollout evaluation, ablation report generation, and known
  limitations.
- `docs/FINAL_DEMO_SUMMARY.md` provides report-ready material covering
  motivation, method, architecture, data flow, model comparison, current
  results, limitations, and next work.

Current final-demo interpretation:

- The package is ready as a reproducible pipeline demo for BC/DP/FM on
  state-based RexROV + single-active-left Oberon7 action-label data.
- The package is not yet a real grasp-performance benchmark because the live
  controller execution, `eef_pose`, non-fallback data, and real success metrics
  remain unresolved.

## 2026-05-05 B8' Small Debug Batch

Experiment label:

```text
B8' small debug batch：10–15 episode real non-fallback arm-only reaching/pre-grasp debug collection，不训练、不处理 gripper。
```

Purpose:

- Test whether the 5/5 repeatability smoke behavior holds under a slightly
  larger 10-episode odom-source debug batch.
- Keep the route strictly arm-only reaching/pre-grasp.
- Do not train, do not run learned rollout, and do not handle the gripper.

Data:

```text
data/raw/b8_reaching_debug_10/
```

Diagnostics:

```text
outputs/logs/b8_reaching_debug_10/repeatability_summary.json
outputs/logs/b8_reaching_debug_10_quality/
outputs/logs/b8_reaching_debug_10_direction/
outputs/logs/b8_reaching_debug_10_command_motion/
```

Result:

```text
episodes_total: 10
validator_pass_count: 10/10
success_count: 7/10
reaching_success_rate: 0.7
all_required_metadata_ok: true
all_success_metadata_consistent: true
base_state_source: odom for all episodes
target_state_source: gazebo_model_states for all episodes
gripper_enabled: false for all episodes
is_grasp_dataset: false for all episodes
mean_initial_distance: 0.10867339087546952
mean_final_distance: 0.08288684626534658
mean_distance_reduction: 0.02578654461012293
max_target_step_base: 0.02330097538679025
large_target_step_indices: [] for all episodes
mean_best_action_to_eef_cosine: 0.5547614407437549
mean_best_realized_gain_along_action: 0.13983358394761614
```

Conclusion:

- The non-fallback odom-source recorder/metadata path passed.
- The reaching quality gate did not pass because success rate was `0.7`, below
  the proposed `0.8` gate, with consecutive failures in episodes 0007-0009.
- This is not grasp success, not learned rollout success, and not training
  evidence.
- Next experiment should diagnose scripted reaching command-to-motion
  degradation before collecting more data.

## 2026-05-05 B8' Action-Frame Fix And Post-Fix Episode

Scope:

```text
B8' blocker debug only. One pre-fix failed episode was diagnosed, one package
local expert-policy fix was made, and one post-fix arm-only verification
episode was collected. No training, no learned rollout, no gripper.
```

Pre-fix failure:

```text
b8_return_gated_arm_verify_3_0000
runtime failure=IK failed with MoveIt error code -31
validator=PASS
saved success=false
recorded_success_distance_m=0.10966874121994438
mean_best_action_to_eef_cosine=0.08695271743383595
```

Fix:

```text
file=src/rexrov_single_oberon7_fm_dp/expert_policy.py
change=use target_directed_action_frame for the arm converter when
       target_directed_reaching=true
py_compile=PASS
```

Post-fix verification:

```text
b8_return_gated_arm_verify_4_0000
runtime action_frame=base_link
validator=PASS
success=True
recorded_success_distance_m=0.05744791236250198
distance_reduction=0.0500849118102937
mean_best_action_to_eef_cosine=0.3532763904220775
mean_best_realized_gain_along_action=0.17090696757478616
```

## 2026-05-05 B8' Tiny Post-Fix Repeatability Check

Scope:

```text
2-cycle return->gate->episode->diagnostics check after the target-directed
action-frame fix. No training, no learned rollout, no gripper command, and no
grasp claim.
```

Data:

```text
data/raw/b8_postfix_repeatability_2/b8_postfix_repeatability_2_0000.npz
data/raw/b8_postfix_repeatability_2/b8_postfix_repeatability_2_0001.npz
```

Result:

```text
validator_pass_count=2/2
success_count=2/2
reaching_success_rate=1.0
all_required_metadata_ok=true
all_success_metadata_consistent=true
mean_final_distance=0.057304824535672975
mean_distance_reduction=0.05025879691398423
min_distance_overall=0.053346384327736994
max_target_step_base=0.007109516133871766
large_target_step_indices=[] for both episodes
mean_best_action_to_eef_cosine=0.5379418351868376
mean_best_lag_steps=0.0
mean_best_realized_gain_along_action=0.17491140517275186
```

Final state check:

```text
final_return reached=true
final_gate passed=true
```

## 2026-05-05 B8' Small Post-Fix Debug Batch Plan

Scope:

```text
Planning entry only. No new episode was collected for this entry.
No training, no learned rollout, no gripper command, no grasp claim.
```

Plan:

```text
default_episode_count=3
hard_max_episode_count=5
data_dir=data/raw/b8_postfix_debug_3/
per_episode=return_to_reference -> target-aware gate -> corrected
            target-directed arm-only episode
post_batch=validator + repeatability summary + quality/direction/command-motion
           diagnostics + final return/gate
```

Stop conditions:

```text
return/gate failure after one retry
IK -31 or expert crash
validator failure
metadata mismatch
target/base source-sync jump
command-motion collapse
```

## 2026-05-05 B8' Small Post-Fix Debug Batch Attempt Stopped By Gate

Scope:

```text
Attempted to start the planned small post-fix debug batch. The cycle 0
pre-episode gate failed and one 5 s retry also failed, so collection stopped
before any episode was recorded. No training, no learned rollout, no gripper.
```

Result:

```text
episodes_collected=0
return reached=true
return commands_sent=0
gate passed=false
initial_distance=0.1159362425810477
relative_base_drift=0.00872391480943356
gate_retry passed=false
retry_initial_distance=0.11528983854046555
retry_relative_base_drift=0.008109968028264436
```

Interpretation:

```text
The per-episode gate stop policy worked. The limiting condition was initial
reaching distance slightly above the 0.115 m gate threshold, not arm reset or
gripper behavior. Diagnose target-aware gate boundary / target probe settle
before retrying collection.
```

## 2026-05-07 BC / DP / FM Live Arm-Only Protocol Attempts

Scope:

```text
active-left arm-only reaching / pre-grasp positioning
no gripper command
no hand controller
no grasp success claim
```

Generated protocol and runner tooling, then ran shared live attempts for BC,
Diffusion Policy, and Flow Matching Policy. DP/FM dry-run action-label checks
and tiny live smoke gates were included before formal cycles where applicable.

Primary artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_protocol_attempts_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_protocol_attempts_summary.md
```

Latest formal attempt, `v7_tick6`:

```text
BC: 0/1, success_rate=0.0, failure_reason=arm_only_success_threshold
DP: 3/3, success_rate=1.0
FM: 0/1, success_rate=0.0, failure_reason=arm_only_success_threshold
```

Best partial evidence across attempts:

```text
v4: DP 3/3 and FM 3/3, BC aborted on IK command conversion/execution.
v6: BC 3/3 and FM 3/3, DP missed the arm-only success threshold at N=1.
v8: success-criterion early stop guard was implemented, but the attempt was
    blocked before rollout by strict fresh pre-gate failure.
v8_after_user_restart: fresh gates passed; BC 0/1, DP tiny smoke threshold
    miss after dry-run passed, FM 2/3.
v9_threshold095_after_user_restart: threshold-only variant remained partial;
    BC 0/1 and DP/FM tiny smoke threshold misses.
v10_aligned_success_guard: early-stop baseline/logging fixed; BC cycle
    re-summary passed, but the run stopped before DP/FM due summary tooling.
v10b_aligned_success_guard: rerun after summarizer fix; BC 0/1, DP/FM
    tiny-smoke threshold misses.
```

Conclusion:

```text
The experiment produced live arm-only evidence for all three policy families,
but it did not produce a fair equal-N BC/DP/FM success-rate table. The next
work item is deciding the formal final-distance source around early stop:
terminal observation or post-gate readback after settle. Do not increase N.
```

## 2026-05-07 Final BC / DP / FM Live Arm-Only N=3 Comparison

The formal final-distance source was fixed to the terminal early-stop
observation and the same v11 protocol was rerun for all three methods.

Artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v11_terminal_final_distance.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v11_terminal_final_distance.md
outputs/logs/b8_rollout_planning/bc_dp_fm_protocol_attempts_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_protocol_attempts_summary.md
```

Result:

```text
BC: 3/3, success_rate=1.0, mean_final_distance=0.08638367363982202
DP: 3/3, success_rate=1.0, mean_final_distance=0.08258604938106842
FM: 3/3, success_rate=1.0, mean_final_distance=0.0851672499059044
complete_three_method_live_comparison=true
equal_N_across_methods=true
```

Safety:

```text
abort_count=0 for all methods
no_gripper_command_observed=true
no_hand_controller_started_by_eval=true
grasp_success_claimed=false
object_grasped_lifted_held_claimed=false
```

N=5 extension:

```text
partial only; BC 5/5, DP 5/5, FM 4 completed successes plus 1 incomplete
cycle artifact. Do not use this as the fair comparison table.
```

## 2026-05-07 Final BC / DP / FM Live Arm-Only N=10 Comparison

The N=10 extension was rerun from a fresh target-gated runtime after fixing a
return-to-reference tooling issue. The clean run is `v12b`.

Artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v12b_terminal_final_distance_n10.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v12b_terminal_final_distance_n10.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v12_terminal_final_distance_n10_interrupted.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v12_terminal_final_distance_n10_interrupted.md
```

Result:

```text
BC: 10/10, success_rate=1.0, mean_final_distance=0.08977726792087681
DP: 10/10, success_rate=1.0, mean_final_distance=0.09129602109718894
FM: 10/10, success_rate=1.0, mean_final_distance=0.09004022450698068
complete_three_method_live_comparison=true
equal_N_across_methods=true
```

Safety:

```text
abort_count=0 for all methods in v12b
no_gripper_command_observed=true
no_hand_controller_started_by_eval=true
grasp_success_claimed=false
object_grasped_lifted_held_claimed=false
```
