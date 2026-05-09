# Training Plan

## Current Arm-Only Retraining Boundary

Do not retrain BC, Diffusion Policy, or Flow Matching Policy for current
results until B8' real non-fallback arm-only reaching/pre-grasp data exists.

## 2026-05-07 Formal Live Success-Rate Attempt

A same-protocol BC / DP / FM live arm-only reaching/pre-grasp protocol was
defined, but no formal success-rate comparison was completed. BC cycle 0 did
not start policy rollout because the strict fresh target-aware gate failed
three times after return-to-reference:

```text
best retry target_base_drift=0.010550711129789662
best retry relative_base_drift=0.007371669176824283
strict target/relative drift threshold=0.001
policy rollout commands sent=false
gripper commands sent=false
```

Artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/formal_protocol.md
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/bc/cycle_0/summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
```

Training/live boundary:

```text
BC formal success rate: not obtained
DP dry-run/live smoke: not started
FM dry-run/live smoke: not started
three-method live comparison complete: false
```

Do not use offline action MSE as a live success-rate substitute. The next
minimum live prerequisite is restoring a clean two-gate target/base sync before
any BC/DP/FM policy command.

Target-gate restart follow-up:

```text
target gate probe restarted=true
target present=true
strict pre-gate after restart failed
target_base_drift=0.006711007793366516
relative_base_drift=0.006271075196806217
policy rollout commands sent=false
```

The BC/DP/FM live comparison remains incomplete.

Aggressive protocol-v4 live result:

```text
protocol root=outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol_v4/
summary=outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
BC success_count=0/1, success_rate=0.0, abort_count=1
DP success_count=3/3, success_rate=1.0, abort_count=0
FM success_count=3/3, success_rate=1.0, abort_count=0
equal_N_across_methods=false
complete_three_method_live_comparison=false
```

DP/FM live execution is no longer blank: both have N=3 arm-only reaching
evidence under protocol v4. BC remains unresolved because cycle 0 aborted on IK
conversion after reaching the distance threshold. Do not present this as a fair
three-method equal-N comparison.

Stage 6 remains a historical fallback dataset suitable only for loader,
normalization, training-loop, and report smoke tests. It must not be used as a
real demonstration dataset or as evidence of grasping/reaching success.

## 2026-05-07 Live-Smoke Boundary Before DP/FM

The second tiny active-left arm-only BC base-relative learned smoke met the
configured single-smoke arm-only reaching threshold:

```text
smoke_status=arm_only_reaching_success
arm_only_reaching_success_claimed=true
learned_rollout_success_claimed=false
grasp_success_claimed=false
gate_distance_reduction=0.03444809112864822
post_gate_initial_distance=0.0796048439094755
control_commands_sent=true
gripper_commands_sent=false
hand_controller_started=false
```

This does not approve full DP/FM training or DP/FM live execution. The live
result only upgrades the BC base-relative path from command-path smoke to one
successful arm-only reaching smoke. Before any DP/FM live work, DP/FM must stay
under the same base-relative observation and safe action normalization, and
must first pass offline comparison against the current BC reference. Before any
additional BC live smoke, return the arm to reference and run a strict fresh
target-aware gate.

Post-live-smoke offline DP/FM gate:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_post_live_smoke_offline_gate.md
outputs/logs/b8_primary30_training_planning/dp_fm_post_live_smoke_offline_gate.json
```

Result:

```text
bc_action_mse=3.0668218187202e-07
best_dp_action_mse=3.1285387080970395e-07
best_fm_action_mse=3.1596741223438585e-07
bc_remains_live_reference=true
dp_fm_live_execution_approved=false
full_dp_fm_training_approved=false
```

Training boundary:

- Full DP/FM training is still not approved.
- DP/FM live execution is still not approved.
- The only acceptable DP/FM continuation is bounded offline-only DP h8
  budget/seed ablation under the same base-relative observation and safe action
  normalization.

BC live repeatability update:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n2/summary.json
repeatability_smoke_status=arm_only_reaching_repeatability_smoke_passed
success_count=2/2
mean_final_distance=0.07611795154782355
min_gate_distance_reduction=0.034746377345962684
learned_rollout_success_claimed=false
grasp_success_claimed=false
```

This improves BC live evidence from one smoke to N=2 repeatability smoke, but
still does not approve full training or a large rollout batch by itself. If
live work continues, use a separately planned N=3 repeatability check before
any larger rollout evaluation.

N=3 repeatability follow-up:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/
repeatability_smoke_status=not_resolved
success_count=1/3
stop_reason=cycle_1_summary_failed
recovery_return_reached=true
recovery_strict_gate_passed=true
learned_rollout_success_claimed=false
grasp_success_claimed=false
```

Read-only diagnosis and offline tick/clip sensitivity found that cycle 1 was
not explained by policy output instability or obvious geometry OOD. The failure
is better treated as a brittle motion-budget case: the current `0.005 m`
Cartesian clip and `max_control_ticks=5` did not provide enough progress, while
the post-smoke target drift sat just over the strict `0.01 m` threshold.

Single-variable candidate review:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_single_variable_candidate_review.md
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke_runbook.md
selected_candidate=bc_h8_xyz_base_relative_tick9_single_smoke
only_variable_change=max_control_ticks: 5 -> 9
live_rerun_approved_by_this_review=false
dp_fm_live_approved=false
```

This runbook was later executed after explicit approval as a single N=1
tick-budget sensitivity smoke. It passed the configured arm-only threshold:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke/outcome.md
smoke_status=arm_only_reaching_success
checks_passed=true
post_gate_initial_distance=0.06884095013771155
gate_distance_reduction=0.038791103596488574
gripper_commands_sent=false
hand_controller_started=false
learned_rollout_success_claimed=false
grasp_success_claimed=false
system_recovered_after_retry=true
```

This does not restore N=3 repeatability and does not approve another live
smoke, a larger rollout batch, DP/FM live execution, grasp success, or general
learned rollout success. DP/FM remain offline-only.

Tick9-vs-N3 read-only comparison:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_vs_n3_tick5_comparison.md
primary_explanation=both_tick_budget_and_cleaner_target_drift
tick_budget_helped=true
target_drift_helped=true
policy_action_shift_detected=false
n3_repeatability_resolved=false
next_live_approved=false
dp_fm_live_approved=false
```

The tick9 pass was not caused by a material policy-output change. The clipped
action mean delta from failed N=3 cycle 1 to tick9 was only
`5.2579650057143435e-05`. The extra four ticks contributed
`0.015276998081651047` additional smoke-distance reduction, and target drift
was much cleaner than cycle 1. This reinforces the current boundary: no new
BC live smoke, no larger rollout batch, and no DP/FM live execution from this
evidence alone.

Target-drift readiness review:

```text
outputs/logs/b8_rollout_planning/b8_target_drift_readiness_gate_review.md
target_drift_is_live_confound=true
recommended_gate=two_fresh_gates_with_clean_target_drift
consecutive_required=2
target_base_drift_max=0.001
relative_base_drift_max=0.001
next_live_approved=false
dp_fm_live_approved=false
```

Before any future BC live smoke is separately approved, target drift should be
decoupled from motion-budget testing by requiring two consecutive strict
fresh gates with both target and relative drift below `0.001 m`. This gate is
only a readiness condition and does not approve live execution. DP/FM remain
offline-only.

Final presentation DP/FM offline result:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_results.md
outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_results.csv
outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_slide_notes.md
```

Result:

```text
bc_action_mse=3.066821534503106e-07
best_dp=dp30_seed86_baseline_best
best_dp_action_mse=3.1088134733181505e-07
best_dp_relative_to_bc=0.013692332058653145
best_fm=fm30_action_select_best_action
best_fm_action_mse=3.0398447847801435e-07
best_fm_relative_to_bc=-0.008796321996393281
presentation_ready_offline_results=true
dp_fm_live_approved=false
```

This is now suitable for a final project presentation as an offline method
comparison: FM has the best validation action MSE, DP remains close but worse
than BC, and BC remains the only live-smoke-tested reference. Do not present
this as DP/FM rollout success or grasp success.

Post-tick9 DP/FM offline gate:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_post_tick9_offline_gate.md
dp_fm_offline_can_continue=true
dp_fm_live_execution_approved=false
full_dp_fm_training_approved=false
bc_remains_live_reference=true
best_dp_candidate=dp30_zero
best_fm_candidate=fm10_zero
```

Offline action-MSE comparison:

```text
bc_action_mse=3.0668218187202e-07
dp30_action_mse=3.1285387080970395e-07
dp30_action_mse_relative_to_bc=0.020124054485367575
fm10_action_mse=3.1596741223438585e-07
fm10_action_mse_relative_to_bc=0.03027639331925912
```

DP/FM can continue offline-only under the same base-relative safe-norm setup.
BC remains the live reference because it still has the best action MSE and the
only live arm-only evidence. DP/FM live execution and full DP/FM training as
success evidence remain blocked.

DP/FM validation-window diagnostics:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_validation_window_diagnostics.md
bc_remains_reference=true
best_non_bc=dp30_zero
dp30_action_mse_relative_to_bc=0.020124149025167605
fm10_action_mse_relative_to_bc=0.030276674149539513
dp_fm_live_approved=false
training_started=false
```

Window-level metrics confirm the same boundary: DP30 is close but not better
than BC, and FM10 has a higher max-window error. Continue DP/FM only as
offline diagnostics under the same base-relative safe-norm setup.

DP30 focused offline ablation plan:

```text
outputs/logs/b8_primary30_training_planning/dp30_focused_offline_ablation_plan.md
outputs/logs/b8_primary30_training_planning/dp30_focused_offline_ablation_plan.json
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.md
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.json
```

Prepared configs:

```text
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed85.yaml
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86.yaml
```

Current seed-ablation baseline:

```text
bc_action_mse=3.066821534503106e-07
best_dp_seed_candidate=dp30_seed84_zero
best_dp_action_mse=3.1285387080970395e-07
best_dp_relative_to_bc=0.020124149025167605
missing_candidate_count=2
dp_fm_live_approved=false
training_started_by_this_script=false
```

The selected DP/FM continuation axis is diffusion seed-only, still under the
same base-relative safe-norm h8 xyz setup. Seed85/seed86 were first prepared
as offline candidates, then run after explicit approval as recorded below.
Running them is an offline training step, not evidence of live success. DP/FM
live remains blocked until a candidate beats the BC reference offline and live
readiness is separately reviewed.

DP30 seed-ablation outcome:

```text
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_outcome.md
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_outcome.json
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.md
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.json
```

Training results:

```text
seed85 best_val_loss=0.48370392736728474 final_val_loss=0.5302829148388037
seed86 best_val_loss=0.504732092542033 final_val_loss=0.504732092542033
```

Validation result:

```text
bc_action_mse=3.066821534503106e-07
dp30_seed84_action_mse=3.1285387080970395e-07
dp30_seed85_action_mse=3.1949056733537873e-07
dp30_seed86_action_mse=3.1088134733181505e-07
best_dp_seed_candidate=dp30_seed86_zero
best_dp_relative_to_bc=0.013692332058653145
bc_remains_live_reference=true
dp_fm_live_approved=false
```

Seed86 improves the best DP candidate but still does not beat BC. DP/FM live
remains blocked. Further DP/FM work should stay offline-only unless a later
candidate beats BC and live readiness is separately approved.

Sampling sweep after seed ablation:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_sampling_after_seed_ablation.md
outputs/logs/b8_primary30_training_planning/dp_fm_sampling_after_seed_ablation.json
```

Key result:

```text
bc_action_mse=3.066821534503106e-07
dp30_seed86_zero_steps10=3.175369158725516e-07
dp30_seed86_zero_steps25=3.138577824302047e-07
dp30_seed86_zero_steps50=3.1088134733181505e-07
dp30_seed86_zero_steps100=3.1088134733181505e-07
dp30_seed86_zero_steps200=3.1088134733181505e-07
fm10_zero_steps50=3.159674690778047e-07
fm10_zero_steps100=3.162173243254074e-07
```

Changing sampling steps does not close the BC gap. The next DP/FM direction,
if continued, should be offline architecture/objective diagnostics under the
same base-relative safe-norm setup, not DP/FM live and not more sampling-step
tuning.

Loss-action alignment diagnostic:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_loss_action_alignment.md
outputs/logs/b8_primary30_training_planning/dp_fm_loss_action_alignment.json
```

Result:

```text
best_non_bc=dp30_seed86
best_dp_relative_to_bc=0.013692332058653145
loss_metric_sufficient_for_selection=false
sampling_or_seed_not_enough=true
dp_fm_live_approved=false
training_started=false
```

The diffusion training loss is not a sufficient model-selection metric here:
`dp30_seed85` has the lowest denoising validation loss but worse action MSE
than `dp30_seed86`. Further DP/FM work should therefore use offline
architecture/objective ablations and continue to select by action-window
metrics against BC, not by denoising/flow loss alone.

DP architecture ablation:

```text
outputs/logs/b8_primary30_training_planning/dp_architecture_ablation_outcome.md
outputs/logs/b8_primary30_training_planning/dp_architecture_ablation_validation.md
```

Result:

```text
bc_action_mse=3.066821534503106e-07
dp30_seed86_w256_action_mse=3.1088134733181505e-07
dp30_seed86_w128_action_mse=3.179889915827516e-07
w128_improves_over_w256=false
dp_fm_live_approved=false
```

Reducing the DP hidden width did not help. If DP/FM continues, prioritize
offline objective/label diagnostics over smaller model capacity or live
execution.

DP objective timestep diagnostic:

```text
outputs/logs/b8_primary30_training_planning/dp_objective_timestep_diagnostic.md
outputs/logs/b8_primary30_training_planning/dp_objective_timestep_diagnostic.json
```

Result:

```text
bc_reference_not_displaced_by_this_diagnostic=true
one_step_x0_diagnostic_not_policy_candidate=true
x0_error_range_ratio=1288.354547513286
objective_ablation_recommended=true
dp_fm_live_approved=false
```

The current epsilon objective is not well aligned with action-space selection:
normalized epsilon MSE decreases at high timesteps, while one-step x0/action
reconstruction error increases. This supports an offline objective/selection
ablation if DP work continues, but it does not approve DP/FM live.

DP action-selection ablation:

```text
outputs/logs/b8_primary30_training_planning/dp_action_selection_outcome.md
outputs/logs/b8_primary30_training_planning/dp_action_selection_validation.md
```

Result:

```text
bc_action_mse=3.066821534503106e-07
dp30_seed86_baseline_action_mse=3.1088134733181505e-07
dp30_seed86_action_select_best_action_action_mse=3.1140186251832347e-07
action_selection_improves_over_baseline_seed86=false
action_selection_beats_bc=false
dp_fm_live_approved=false
```

Adding an action-space checkpoint-selection metric improved max-window MSE for
`best_action.pt`, but did not improve mean action MSE over the baseline seed86
checkpoint and did not beat BC. DP/FM live remains blocked.

DP x0 auxiliary objective ablation:

```text
outputs/logs/b8_primary30_training_planning/dp_x0_aux_validation.md
outputs/logs/b8_primary30_training_planning/dp_x0_aux_outcome.md
```

Result:

```text
bc_action_mse=3.066821534503106e-07
dp30_seed86_baseline_action_mse=3.1088134733181505e-07
dp30_seed86_action_select_best_action_mse=3.1140186251832347e-07
dp30_seed86_x0aux0p1_best_loss_action_mse=3.133305597202707e-07
dp30_seed86_x0aux0p1_best_action_mse=3.1106586106943723e-07
dp30_seed86_x0aux0p1_dimw025_1_1_best_action_mse=3.110033617303998e-07
best_dp=dp30_seed86_baseline_best
x0_aux_improves_mean_action_mse_over_baseline=false
x0_aux_beats_bc=false
per_dim_x0_aux_improves_mean_action_mse_over_baseline=false
per_dim_x0_aux_beats_bc=false
bc_remains_reference=true
dp_fm_live_approved=false
```

Adding a normalized x0/action reconstruction auxiliary term with weight `0.1`
did not improve mean action MSE over the DP seed86 baseline and did not beat
BC. A per-dimension weighted variant `[0.25, 1.0, 1.0]` was slightly better
than scalar x0-aux but still worse than baseline DP seed86 and BC. BC remains
the live reference. DP/FM can continue only as offline objective/selection
design review; DP/FM live remains blocked.

When retraining resumes after B8':

- use the B8' real non-fallback reaching/pre-grasp dataset;
- use the same train/validation split for BC, DP, and FM;
- use the same normalization statistics;
- use the same `obs_horizon` and `action_horizon`;
- keep `action_dim=7` for compatibility;
- fix or ignore `gripper_cmd` and record that in metadata;
- report the task as arm-only reaching/pre-grasp, not grasping.

## 2026-05-06 B8' Primary30 Candidate And BC Sanity

The B8' primary real non-fallback candidate pool is:

```text
data/raw/b8_postfix_debug_10_clean/
data/raw/b8_controlled_debug_20/
```

Read-only manifest:

```text
outputs/logs/b8_training_dataset_candidate_manifest/candidate_manifest.md
outputs/logs/b8_training_dataset_candidate_manifest/candidate_manifest.json
outputs/logs/b8_training_dataset_candidate_manifest/candidate_episodes.csv
```

Primary candidate summary:

```text
episode_count=30
validator_pass_count=30/30
success_count=30/30
allow_nominal_state_fallback=false for all episodes
base_state_source=odom for all episodes
joint_state_source=joint_states for all episodes
target_state_source=gazebo_model_states for all episodes
gripper_enabled=false for all episodes
is_grasp_dataset=false for all episodes
mean_final_distance=0.05003238637536062
mean_distance_reduction=0.05960007870215763
```

Training split:

```text
outputs/logs/b8_training_dataset_candidate_manifest/dataset_split_primary_30.json
train=24
val=6
test=0
```

Training configs:

```text
config/train_bc_b8_primary30.yaml
config/train_diffusion_b8_primary30.yaml
config/train_flow_matching_b8_primary30.yaml
config/train_bc_b8_primary30_sanity.yaml
```

Loader check:

```text
train_windows=456
val_windows=114
obs_dim=38
action_dim=7
obs_horizon=4
action_horizon=16
allow_fallback_dataset=false
```

BC sanity training result:

```text
epochs=20
device=cuda
best_val_loss=0.40424566834733106
best_val_epoch=3
final_train_loss=0.02826811047355253
final_val_loss=0.49751798444818973
```

Offline eval from BC sanity best checkpoint:

```text
train normalized_mse=0.16825989753672638
train action_mse=0.0024937160778790712
val normalized_mse=0.40424566834733106
val action_mse=0.0024596124421805143
```

Decision:

```text
B8' primary30 dataset and BC training code path are validated at sanity level.
Do not start Diffusion Policy or Flow Matching Policy training until the BC
sanity result and val split boundary cases are reviewed. Learned rollout has
not been run.
```

## 2026-05-06 BC Val Review And DP/FM Decision

BC sanity val behavior review:

```text
outputs/logs/b8_primary30_bc_sanity_val_review/val_behavior_review.md
outputs/logs/b8_primary30_bc_sanity_val_review/val_behavior_review.json
```

Val aggregate:

```text
mean_episode_normalized_mse=0.40424565280166774
max_episode_normalized_mse=1.3814396424138027
mean_episode_action_mse=0.002459612661197383
max_episode_action_mse=0.0038022409793009738
flagged_val_episode_count=3
```

Worst normalized-MSE val episodes:

```text
b8_controlled_debug_20_0014:
  normalized_mse=1.381440
  flags=low_action_eef_cosine_lt_0.50
b8_controlled_debug_20_0017:
  normalized_mse=0.560607
  flags=weak_final_distance_ge_0.065; low_realized_gain_lt_0.16
b8_controlled_debug_20_0010:
  normalized_mse=0.172372
  flags=initial_distance_boundary_gt_0.115; weak_final_distance_ge_0.065; low_realized_gain_lt_0.16
```

Decision:

```text
Do not start full Diffusion Policy or Flow Matching Policy training yet.
The next allowed step, if explicitly approved, is a short DP/FM smoke run on
the same primary30 split, not full training and not rollout.
```

Prepared smoke configs:

```text
config/train_diffusion_b8_primary30_smoke.yaml
config/train_flow_matching_b8_primary30_smoke.yaml
```

Smoke config loader check:

```text
train_windows=456
val_windows=114
obs_dim=38
action_dim=7
epochs=10
allow_fallback_dataset=false
```

## 2026-05-06 Short DP/FM Smoke Results

Short smoke training was run for Diffusion Policy and Flow Matching Policy on
the same B8' primary30 split. This was not full training and not rollout.

Comparison artifact:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_smoke_comparison.md
outputs/logs/b8_primary30_training_planning/dp_fm_smoke_comparison.json
```

Offline comparison:

```text
BC sanity:
  epochs=20
  best_val_loss=0.404246
  train_normalized_mse=0.168260
  train_action_mse=0.00249372
  val_normalized_mse=0.404246
  val_action_mse=0.00245961

Diffusion smoke:
  epochs=10
  best_val_loss=0.867681
  train_normalized_mse=1.326684
  train_action_mse=0.72233635
  val_normalized_mse=1.438239
  val_action_mse=0.73058528

Flow Matching smoke:
  epochs=10
  best_val_loss=1.256665
  train_normalized_mse=1.090433
  train_action_mse=0.67131901
  val_normalized_mse=1.454579
  val_action_mse=0.68037963
```

Decision:

```text
DP/FM smoke verifies train/eval code paths, but sampled action quality is far
worse than BC sanity. Do not run learned rollout. Do not start full DP/FM
training until sampling configuration, epoch budget, and model settings are
reviewed.
```

## 2026-05-06 DP/FM Sampling And Epoch-Budget Review

Review artifact:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_sampling_epoch_model_review.md
outputs/logs/b8_primary30_training_planning/dp_fm_sampling_epoch_model_review.json
```

Reviewed items:

- Diffusion Policy objective: epsilon/noise prediction MSE on normalized action
  chunks; this is not direct sampled-action MSE.
- Flow Matching objective: velocity MSE from Gaussian source to clean
  normalized action chunks; this is not direct sampled-action MSE.
- DP/FM smoke model capacity: hidden dims `[256, 256, 256]`,
  `time_embed_dim=64`.
- Full config epoch budget is `160`, but only the approved `10`-epoch smoke
  runs have been executed.
- Re-evaluated the smoke checkpoints with DP `num_inference_steps=50` and FM
  `ode_steps=50`.

Offline sampling result:

```text
BC sanity val_action_mse=0.00245961

Diffusion smoke:
  10-step prior val_action_mse=0.73058528
  50-step re-eval val_action_mse=1.06960142

Flow Matching smoke:
  10-ODE prior val_action_mse=0.68037963
  50-ODE re-eval val_action_mse=0.68106294
```

Decision:

```text
Do not start longer/full DP/FM training yet.
Do not run learned rollout.
Do not claim grasp or learned rollout success.
```

Reason:

- Increasing DP reverse steps to 50 did not improve sampled action quality.
- Increasing FM ODE steps to 50 was essentially unchanged and still much worse
  than BC.
- The current evidence points to sampling/objective/model/action-space review
  before more training, not simply insufficient smoke epochs.

Next allowed work is offline-only bounded ablation: deterministic or
mean-style sampling checks, per-dimension action/objective review, shorter
action horizon, and a small epoch-budget check. Full training and rollout stay
blocked until these offline checks produce credible sampled actions.

## 2026-05-06 DP/FM Offline Bounded Ablations

Completed offline-only checks:

- deterministic/mean-style sampling via zero initial action;
- per-dimension action/objective review;
- short action horizon ablation with `action_horizon=8`, `epochs=10`;
- small epoch-budget ablation with `action_horizon=16`, `epochs=30`.

Artifacts:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_offline_ablation_review.md
outputs/logs/b8_primary30_training_planning/dp_fm_offline_ablation_review.json
```

New configs:

```text
config/train_diffusion_b8_primary30_h8_smoke.yaml
config/train_flow_matching_b8_primary30_h8_smoke.yaml
config/train_diffusion_b8_primary30_epoch30.yaml
config/train_flow_matching_b8_primary30_epoch30.yaml
```

Offline val sampling table:

```text
BC sanity                      action_mse=0.00245961
DP h16 smoke stochastic50       action_mse=1.06960142
DP h16 smoke zero50             action_mse=0.01415015
FM h16 smoke stochastic50       action_mse=0.68106294
FM h16 smoke zero50             action_mse=0.00765850
DP h8 smoke stochastic50        action_mse=0.65730250
DP h8 smoke zero50              action_mse=0.02315055
FM h8 smoke stochastic50        action_mse=0.70807338
FM h8 smoke zero50              action_mse=0.00469423
DP h16 epoch30 stochastic50     action_mse=0.44135934
DP h16 epoch30 zero50           action_mse=0.00704497
FM h16 epoch30 stochastic50     action_mse=0.38137627
FM h16 epoch30 zero50           action_mse=0.01068851
```

Interpretation:

- Gaussian-source stochastic sampling remains poor after h8 and epoch30
  ablations.
- Zero-init/mean-style sampling reduces DP/FM sampled action MSE by roughly two
  orders of magnitude.
- Best DP/FM offline result is FM h8 zero-init with val action MSE
  `0.00469423`, still worse than BC sanity `0.00245961`.
- Inactive angular and gripper-like action dimensions dominate stochastic
  sampled-action error.

Decision:

```text
Do not start full DP/FM training.
Do not run learned rollout.
Keep the next step offline-only.
```

Next training-plan item: add an action-space-filtered or masked-objective
variant before any larger DP/FM training. Compare BC and FM h8 zero-init under
the same active reaching action-space definition.

## 2026-05-06 XYZ-Filtered Action-Space Comparison

Implemented and evaluated an action-space-filtered variant:

```text
action_dim_indices=[0,1,2]
kept dimensions: dx, dy, dz
removed dimensions: droll, dpitch, dyaw, gripper_like_disabled
```

Configs:

```text
config/train_bc_b8_primary30_h8_xyz.yaml
config/train_diffusion_b8_primary30_h8_xyz_smoke.yaml
config/train_flow_matching_b8_primary30_h8_xyz_smoke.yaml
```

Artifact:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_xyz_filtered_comparison.md
outputs/logs/b8_primary30_training_planning/dp_fm_xyz_filtered_comparison.json
```

Offline val result:

```text
BC h8 xyz direct             action_mse=0.00138611 normalized_mse=0.84109951
DP h8 xyz stochastic50       action_mse=0.12639004 normalized_mse=1.98532737
DP h8 xyz zero50             action_mse=0.01584135 normalized_mse=1.02125073
FM h8 xyz stochastic50       action_mse=0.32252964 normalized_mse=2.01401833
FM h8 xyz zero50             action_mse=0.00157071 normalized_mse=0.94525194
```

Decision:

```text
Do not start full DP/FM training.
Do not run learned rollout.
Keep the next step offline-only.
```

The filtered FM h8 zero-init result is close to BC but still slightly worse on
validation action MSE and normalized MSE. The next allowed offline step is a
small FM h8 xyz epoch-budget ablation or an additional deterministic direct-head
baseline under the exact same `dx/dy/dz` action-space definition.

## 2026-05-06 FM H8 XYZ Epoch-Budget Review

Completed one small offline epoch-budget ablation:

```text
config/train_flow_matching_b8_primary30_h8_xyz_epoch30.yaml
```

Artifact:

```text
outputs/logs/b8_primary30_training_planning/fm_h8_xyz_epoch_budget_review.md
outputs/logs/b8_primary30_training_planning/fm_h8_xyz_epoch_budget_review.json
```

Offline val result:

```text
BC h8 xyz direct              action_mse=0.00138611 normalized_mse=0.84109951
FM h8 xyz epoch10 zero50      action_mse=0.00157071 normalized_mse=0.94525194
FM h8 xyz epoch30 zero50      action_mse=0.00147991 normalized_mse=0.90564308
FM h8 xyz epoch30 stoch50     action_mse=0.33842790 normalized_mse=2.16292317
```

Decision:

```text
Do not start full DP/FM training.
Do not run learned rollout.
BC h8 xyz remains the current best offline baseline.
```

FM h8 xyz epoch30 improved zero-init action MSE slightly, but final validation
velocity loss worsened while train loss continued downward, so this is not a
stronger training direction yet.

## 2026-05-06 BC H8 XYZ Offline Candidate

Generated the candidate report:

```text
outputs/logs/b8_primary30_training_planning/bc_h8_xyz_offline_candidate_report.md
outputs/logs/b8_primary30_training_planning/bc_h8_xyz_offline_candidate_report.json
```

Candidate status:

```text
rollout_planning_candidate=true
rollout_ready_success=false
learned_rollout_has_run=false
full_training_candidate=false
```

Candidate checkpoint:

```text
config=config/train_bc_b8_primary30_h8_xyz.yaml
checkpoint=outputs/checkpoints/b8_primary30_bc_h8_xyz/best.pt
action_space=dx,dy,dz only
action_dim_indices=[0,1,2]
obs_horizon=4
action_horizon=8
```

Offline eval:

```text
train_action_mse=0.00125866
train_normalized_mse=0.44862161
val_action_mse=0.00138611
val_normalized_mse=0.84109951
```

Planning decision:

- BC h8 xyz is the current offline baseline and rollout-planning candidate.
- It is not rollout-ready success.
- A separate rollout safety/evaluation plan is required before any learned
  rollout command is run.
- Any future rollout must be arm-only reaching/pre-grasp, with no gripper/hand
  controller and no gripper command.

Real arm-only rollout evaluation should record:

```text
reaching_success_rate
final_distance
distance_reduction
episode_length
action_smoothness
inference_latency
failure_reason
```

Do not record `grasp_success_rate` for the current route, and do not claim
object grasped, lifted, or held.

## 2026-05-06 Arm-Only Rollout Safety/Evaluation Plan

Generated a separate rollout planning artifact:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_arm_only_rollout_safety_plan.md
outputs/logs/b8_rollout_planning/bc_h8_xyz_arm_only_rollout_safety_plan.json
```

Status:

```text
planning_artifact_only=true
rollout_execution_approved_by_this_plan=false
requires_separate_approval=true
learned_rollout_has_run=false
```

The first future learned evaluation is constrained to one short arm-only
reaching/pre-grasp rollout after separate approval. It must use the BC h8 xyz
candidate as a 3-D `[dx, dy, dz]` action policy, not the existing Stage 10 7-D
rollout execution assumptions.

Required safety/evaluation protocol:

- map policy output as `dx,dy,dz` in meters and log any 7-D expansion only as
  `[dx, dy, dz, 0, 0, 0, 0]`;
- clip first-attempt xyz commands to `0.005 m` per component and `0.00866 m`
  norm, with `0.03 m` raw-component hard abort;
- clip active-left joint command delta to `0.01 rad` per command;
- return arm to the B8 reference state before rollout;
- reset/restart the B8 target gate probe if stale target drift is suspected;
- require two consecutive fresh target-aware initial-state gates with
  `passed=true`;
- abort on missing state, invalid policy output, IK/command conversion failure,
  target relative-base drift over `0.01 m`, distance regression, excessive
  EEF displacement, joint tracking error, rejected arm command, or any
  gripper/hand command path becoming active.

Required metrics include initial/final/min distance, distance reduction, raw and
clipped xyz action series, clip fraction, EEF/target base-frame series, joint
positions and joint commands, maximum joint delta, inference latency,
abort/failure reason, return/gate JSON paths, and explicit
`gripper_commands_sent=false`.

Allowed success label for the first reviewed rollout is only
`arm_only_reaching_success`. Do not record or claim `grasp_success`, object
grasped/lifted/held, or general learned-policy success.

Next allowed step: review or implement the arm-only xyz rollout adapter in
dry-run mode only. Live execution remains blocked until separately approved.

## 2026-05-06 BC H8 XYZ Dry-Run Adapter

Implemented a separate dry-run adapter for the BC h8 xyz candidate:

```text
scripts/b8_bc_h8_xyz_rollout_dry_run_node.py
config/b8_bc_h8_xyz_rollout_dry_run.yaml
launch/b8_bc_h8_xyz_rollout_dry_run.launch
outputs/logs/b8_rollout_planning/bc_h8_xyz_dry_run_adapter_report.md
outputs/logs/b8_rollout_planning/bc_h8_xyz_dry_run_adapter_report.json
```

This adapter exists because the current Stage 10 rollout node assumes 7-D
action chunks, while the current rollout-planning candidate is the filtered
3-D BC h8 xyz model.

Properties:

```text
dry_run_only=true
execute_actions=true is forbidden
policy_type=bc
checkpoint=outputs/checkpoints/b8_primary30_bc_h8_xyz/best.pt
obs_dim=38
obs_horizon=4
action_dim=3
action_horizon=8
```

It publishes only action labels:

```text
action_xyz=[dx, dy, dz]
logging_action_7d=[dx, dy, dz, 0, 0, 0, 0]
arm_control_commands_sent=false
gripper_commands_sent=false
```

Static checks passed: Python compilation, YAML parse, launch XML parse,
`roslaunch --nodes`, and checkpoint dimension loading.

This is still not a live learned rollout. The next minimum runtime step is a
single live dry-run label check after return-to-reference and two fresh
target-aware gates pass. Do not execute arm commands from this adapter until a
separate live rollout approval is given.

## 2026-05-06 BC H8 XYZ Rollout-Planning Reassessment

The live dry-run and validation neutralization diagnostics showed that BC h8
xyz is not rollout-planning safe in its current form.

Key evidence:

```text
live dry-run raw_action_xyz=[0.09588255733251572, 0.00029814825393259525, 0.010294424369931221]
raw_component_abort=0.03

validation as_val:
  p95_first_step_absmax=0.11106296367943283
  max_first_step_absmax=0.13884584605693817

validation zero_gripper_target:
  p95_first_step_absmax=0.09894258603453636
  max_first_step_absmax=0.11847516894340515

checkpoint action_std=[1.0, 0.0006739544332958758, 0.0005034060450270772]
```

Decision:

- BC h8 xyz remains an offline diagnostic baseline.
- BC h8 xyz is not a live rollout-planning candidate until the observation
  design and action normalization are fixed and re-evaluated.
- Do not use inference-time zeroing alone as a rollout-safety fix.
- Do not run learned rollout.
- Do not advance longer/full DP/FM training from this checkpoint.

Next training-planning direction should be offline-only: create a new
base-relative / arm-only observation variant and a safe action normalization
policy for near-constant clipped action dimensions, then re-run BC sanity before
returning to DP/FM comparisons.

## 2026-05-06 Base-Relative Arm-Only BC Safe-Norm Sanity

Implemented the offline-only correction:

```text
config/train_bc_b8_primary30_h8_xyz_base_relative_safe_norm.yaml
outputs/checkpoints/b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt
outputs/logs/b8_primary30_training_planning/bc_h8_xyz_base_relative_safe_norm_report.md
outputs/logs/b8_primary30_training_planning/bc_h8_xyz_base_relative_safe_norm_report.json
```

Observation:

```text
active_joint_positions
active_joint_velocities
eef_position_base_frame
target_position_base_frame
target_to_eef_base_frame
episode_progress
episode_remaining
```

Removed:

```text
absolute world base_pose
absolute world target_pose
gripper_state
```

Action normalization:

```text
action_std_fallback=0.001
action_std=[0.0010000000474974513, 0.0006739544332958758, 0.0005034060450270772]
```

Offline result:

```text
val_normalized_mse=0.9591013831837524
val_action_mse=3.0668218187202e-07
val_first_absmax_p95=0.010084372432902455
val_first_absmax_max=0.010133071802556515
```

Decision:

- Offline action scale is safe for this BC sanity checkpoint.
- This is not rollout-ready success.
- No learned rollout has run.
- No gripper or hand command was used.
- Do not compare DP/FM against the old absolute-pose BC h8 xyz checkpoint.
- Future DP/FM comparisons must use this same base-relative / arm-only
  observation and safe action normalization.

## 2026-05-05 B8' Debug Batch No-Training Gate

The 10-episode B8' small debug batch exists:

```text
data/raw/b8_reaching_debug_10/
```

It passed validation and metadata gates, but did not pass the reaching-quality
gate:

```text
validator_pass_count: 10/10
success_count: 7/10
reaching_success_rate: 0.7
proposed pass gate: success_count / N >= 0.8
failed tail: 0007-0009
```

Offline failure analysis found:

```text
action_relative_cosine remained target-aligned in failures
best_action_to_eef_cosine degraded from 0.823278 to -0.071778
best_realized_gain_along_action degraded from 0.209131 to -0.021860
joint_initial_drift_from_ep0 increased from 0.304920 to 0.806195
```

Training decision:

```text
Do not train BC / Diffusion Policy / Flow Matching Policy from
b8_reaching_debug_10.
```

Reason:

- The batch is useful debug data, but not a stable training dataset.
- The failed tail indicates cross-episode reset/settle or command-to-motion
  degradation that should be fixed before collecting a training dataset.
- Training on this batch would mix successful demonstrations with unexplained
  non-target-directed realized motion.

## 2026-05-05 B8' Repeatability Boundary

A five-episode B8' repeatability smoke set now exists:

```text
data/raw/b8_reaching_repeatability_smoke/
```

Smoke result:

```text
validator_pass_count: 5/5
success_count: 5/5
mean_final_distance: 0.06034401658235772
mean_distance_reduction: 0.0473147271937287
max_target_step_base: 0.014892885342403243
large_target_step_indices: [] for all episodes
```

Training decision:

```text
Do not train BC / Diffusion Policy / Flow Matching Policy from this smoke set
as a final dataset.
```

Reason:

- The set is intentionally small and was collected to verify repeatability and
  quality diagnostics.
- It is arm-only reaching/pre-grasp evidence, not grasping.
- The next step should be a small deliberate real non-fallback arm-only
  collection plan with the same validation, source-sync, and command-motion
  gates before retraining.

## First Training Milestone

Run BC as a sanity check before Diffusion Policy or Flow Matching Policy.

Suggested order:

1. Validate `.npz` episode schema.
2. Build dataset loader and normalization.
3. Train BC on a tiny dataset to confirm loss decreases.
4. Train Diffusion Policy using the same dataset and normalization.
5. Train Flow Matching Policy using the same dataset and normalization.
6. Evaluate all policies with the same rollout protocol.

## Fair Comparison Rules

- BC, DP, and FM must use the same train/validation split.
- DP and FM must use the same observation/action representation.
- DP and FM must use the same normalization statistics.
- DP and FM should use comparable model capacity.
- Rollout evaluation should use the same initial-state distribution and success metric.

## First-Version Model Inputs

Observation is state-based:

- base pose/velocity
- left arm joint state
- gripper state
- target pose
- optional left end-effector pose

Action:

- end-effector delta action
- gripper command

## Stage 0 Boundary

No dataset loader, model, training loop, or evaluation code is implemented in stage 0.

## Stage 7 BC Baseline

Implemented first-version state-based BC pipeline:

- dataset loader: `learning/datasets/uvms_episode_dataset.py`
- MLP policy: `learning/models/bc_policy.py`
- trainer: `learning/train/train_bc.py`
- offline evaluator: `learning/eval/eval_offline.py`
- config: `config/train_bc.yaml`

The loader reads episode `.npz` files from a split JSON, builds
`obs_history -> action_chunk` windows, normalizes observations/actions using
train-split statistics, and returns an action mask so short episodes can be
used with `action_horizon: 16`.

Default Stage 7 settings:

```text
obs_horizon: 4
action_horizon: 16
observation keys:
  base_pose, base_velocity, active_joint_positions,
  active_joint_velocities, gripper_state, target_pose
include_progress: true
action_key: action_ee_delta
action_dim: 7
model: MLP [128, 128]
```

Stage 7 smoke training used the Stage 6 fallback debug dataset only:

```text
train episodes: 16
val episodes: 4
train windows: 112
val windows: 28
obs_dim: 38
action_dim: 7
```

BC smoke-training result:

```text
epochs: 120
device: cuda
initial train loss: 0.42980525
final train loss: 0.04464374
best val loss: 0.09266304
final val loss: 0.09374733
```

Offline evaluation from `best.pt`:

```text
train normalized_mse: 0.05121726
train action_mse: 0.00359283
val normalized_mse: 0.09266304
val action_mse: 0.00643590
```

Output paths:

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

TensorBoard note:

- `torch.utils.tensorboard` could not import in this environment because the
  active Anaconda protobuf extension requires `GLIBCXX_3.4.29`.
- The trainer now falls back to a no-op writer and records the reason in
  `train_summary.json`; checkpointing and JSON summaries still work.

Interpretation:

- Stage 7 proves the `.npz` loader, normalization, windowing, masked loss,
  checkpointing, and offline evaluation path.
- It does not prove grasp policy quality because the Stage 6 data uses nominal
  fallback base/joint/target state and success is false for all episodes.

## Stage 8 Diffusion Policy

Implemented first-version state-based Diffusion Policy:

- diffusion model: `learning/models/diffusion_policy.py`
- trainer: `learning/train/train_diffusion.py`
- config: `config/train_diffusion.yaml`
- offline eval extension: `learning/eval/eval_offline.py`

Representation is shared with BC:

```text
condition: obs_history [B, 4, 38]
target: normalized action_chunk [B, 16, 7]
loss mask: action_mask [B, 16]
```

Model and scheduler:

```text
policy type: DDPM-style epsilon prediction
denoiser: conditional MLP
hidden_dims: [256, 256, 256]
time_embed_dim: 64
num_diffusion_steps: 50
beta schedule: linear 0.0001 -> 0.02
num_inference_steps: 50
```

Training objective:

- sample diffusion timestep `t`
- add Gaussian noise to normalized action chunks
- predict the added noise
- optimize masked MSE over valid action steps only

Stage 8 smoke-training result on the same Stage 6 fallback debug split:

```text
train windows: 112
val windows: 28
device: cuda
epochs: 160
initial train denoising loss: 1.03681373
final train denoising loss: 0.32737366
best val denoising loss: 0.30106574
final val denoising loss: 0.35403574
```

Offline sampling evaluation from Gaussian noise with 50 denoising steps:

```text
train normalized_mse: 0.77574102
train action_mse: 0.14291643
val normalized_mse: 0.76420820
val action_mse: 0.13530311
```

Output paths:

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

Interpretation:

- Stage 8 proves the state-based diffusion training and sampling code path.
- Sampling MSE is worse than the BC smoke baseline on this tiny deterministic
  fallback dataset; that is expected for this first stochastic model and is not
  a real policy comparison.
- Real comparison requires a live-state demonstration dataset after runtime
  state and command interfaces are fixed.

## Stage 9 Flow Matching Policy

Implemented first-version state-based Flow Matching Policy:

- flow matching model: `learning/models/flow_matching_policy.py`
- trainer: `learning/train/train_flow_matching.py`
- config: `config/train_flow_matching.yaml`
- offline eval extension: `learning/eval/eval_offline.py`

Representation is shared with BC and Diffusion Policy:

```text
condition: obs_history [B, 4, 38]
target: normalized action_chunk [B, 16, 7]
loss mask: action_mask [B, 16]
```

Model:

```text
policy type: rectified-flow / flow matching velocity prediction
velocity field: conditional MLP
hidden_dims: [256, 256, 256]
time_embed_dim: 64
time_scale: 1000.0
ode_steps: 50
```

Training objective:

```text
x0 ~ Gaussian noise
x1 = expert action_chunk
t ~ Uniform(0, 1)
xt = (1 - t) * x0 + t * x1
target_velocity = x1 - x0
loss = masked MSE(v_theta(xt, t, obs_history), target_velocity)
```

Stage 9 smoke-training result on the same Stage 6 fallback debug split:

```text
train windows: 112
val windows: 28
device: cuda
epochs: 160
initial train flow loss: 1.44762514
final train flow loss: 0.49487846
best val flow loss: 0.39671761
final val flow loss: 0.50331438
```

Offline Euler ODE evaluation from Gaussian noise with 50 steps:

```text
train normalized_mse: 0.36070445
train action_mse: 0.09820177
val normalized_mse: 0.35701191
val action_mse: 0.08730043
```

Output paths:

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

Interpretation:

- Stage 9 proves the state-based Flow Matching training and ODE sampling code
  path.
- FM uses the same data split, loader, normalization, action chunk shape, mask
  handling, and comparable MLP capacity as Diffusion Policy.
- The fallback dataset is too small and deterministic for real conclusions; use
  these metrics only as pipeline checks.

## Stage 10 Rollout Node And Unified Evaluation

Implemented first-version rollout infrastructure:

- policy runtime loader: `learning/eval/policy_runtime.py`
- ROS rollout node: `scripts/rollout_policy_node.py`
- rollout launch: `launch/rollout_policy.launch`
- unified dry-run eval: `learning/eval/eval_rollout.py`
- config: `config/eval_rollout.yaml`

The rollout node can:

- subscribe to the same state topics used by the recorder;
- maintain an `obs_history` buffer;
- load BC, Diffusion Policy, or Flow Matching checkpoints;
- apply saved normalization statistics;
- generate future `action_chunk`;
- publish clipped action labels to
  `/rexrov_single_oberon7_fm_dp/policy/action_ee_delta`;
- publish JSON status to `/rexrov_single_oberon7_fm_dp/policy/status`.

Safety/default behavior:

- `execute_actions: false` by default.
- If `execute_actions=true` is requested, Stage 10 still refuses real controller
  execution and publishes action labels only because the left-arm/gripper
  command mapping remains unconfirmed.
- Action clipping is applied to linear deltas, angular deltas, and gripper
  command.

Unified dry-run evaluation result:

```text
policy          loaded  generated  success_rate   final_distance  mean_latency_ms  failure_reason
BC              true    true       not_evaluated  unavailable     8.451            controller_mapping_unconfirmed
Diffusion       true    true       not_evaluated  unavailable     65.826           controller_mapping_unconfirmed
Flow Matching   true    true       not_evaluated  unavailable     14.478           controller_mapping_unconfirmed
```

Output paths:

```text
outputs/eval/stage10_rollout/rollout_eval_summary.json
outputs/eval/stage10_rollout/rollout_eval_summary.md
```

Interpretation:

- Stage 10 validates that all three trained policies can be loaded by a shared
  runtime path and can generate rollout-compatible action chunks.
- Real Gazebo rollout success rate and final distance are not evaluated yet
  because left-arm/gripper command topics, `eef_pose`, and non-fallback live
  data remain unresolved.

## Stage 11 Comparison And Ablation

Stage 11 added a report generator:

```text
config/ablation_report.yaml
learning/eval/ablation_report.py
outputs/eval/stage11_ablation/ablation_report.md
```

Current fallback-data comparison:

```text
policy          val_action_mse  dry_run_latency_ms
BC              0.006436        8.451
Diffusion       0.135303        65.826
Flow Matching   0.087300        14.478
```

Pipeline-only conclusion:

- Flow Matching outperformed Diffusion Policy on fallback validation action MSE
  and dry-run latency.
- BC had the lowest offline MSE on the small deterministic fallback dataset.
- These are not real grasping results.

## Stage 12 Reproduction Commands

From workspace root:

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

Evaluate and report:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/eval/eval_rollout.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/eval_rollout.yaml

python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/eval/ablation_report.py \
  --config src/uvms/rexrov_single_oberon7_fm_dp/config/ablation_report.yaml
```

Before using these results in a final paper/report as real policy performance,
replace the Stage 6 fallback dataset with non-fallback demonstrations and rerun
the same training/evaluation commands.

## B8' Base-Relative Arm-Only Policy Gate

Date: 2026-05-06.

The rollout-planning policy interface for B8' is now the base-relative
arm-only `dx,dy,dz` route, not the old absolute-world BC h8 xyz route.

Required observation design for any BC / Diffusion Policy / Flow Matching
comparison from this point:

```text
active_joint_positions
active_joint_velocities
eef_position_base_frame
target_position_base_frame
target_to_eef_base_frame
episode_progress
episode_remaining
```

Excluded from this gate:

```text
absolute world base_pose
absolute world target_pose
gripper_state
angular action dimensions
gripper-like action dimensions
```

Required action normalization:

```text
action_dim_indices=[0,1,2]
action_std_epsilon=1e-6
action_std_fallback=0.001
```

BC base-relative checkpoint:

```text
outputs/checkpoints/b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt
```

Matching live dry-run adapter:

```text
launch/b8_bc_h8_xyz_base_relative_rollout_dry_run.launch
```

Latest dry-run label check:

```text
status=timeout_complete
samples=21
aborted=false
raw_action_absmax=0.010233319364488125 m
clipped_action_absmax=0.005 m
control_commands_sent=false
gripper_commands_sent=false
```

Training decision:

```text
BC base-relative action scale is acceptable for dry-run label planning.
DP/FM comparisons may proceed only if they use the exact same observation
scheme and safe action normalization.
Do not start longer/full DP/FM training until short offline DP/FM results are
credible against this BC baseline.
Do not run learned arm execution without a separate rollout approval.
```

## B8' Base-Relative DP/FM Offline Comparison

Date: 2026-05-06.

DP/FM have now been compared only under the same base-relative observation and
safe action normalization as the BC rollout-planning candidate. The old
absolute-pose BC/DP/FM checkpoints are not part of this comparison.

Configs:

```text
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_smoke.yaml
config/train_flow_matching_b8_primary30_h8_xyz_base_relative_safe_norm_smoke.yaml
```

Comparison report:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_offline_comparison.md
outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_offline_comparison.json
```

Validation metrics:

```text
policy              sampling  normalized_mse  action_mse       pred_p95_absmax
BC                  direct    0.959101        3.0668218e-07    0.01011395
Diffusion Policy    zero      1.014984        3.2943791e-07    0.01025867
Flow Matching       zero      0.938351        3.1596741e-07    0.01013040
```

Interpretation:

- The comparison is now fair: same split, same 23-D base-relative observation,
  same `[dx,dy,dz]` action space, same safe action normalization.
- BC remains the current rollout-planning reference because it is direct-head,
  already passed the base-relative live dry-run action-label check, and has
  the lowest action MSE in this run.
- DP/FM are close enough to justify offline-only epoch-budget or sampler
  ablations under this same config family.
- This does not approve full DP/FM training, learned rollout, gripper command,
  or any grasp claim.

## B8' DP/FM Epoch-Budget Result

Date: 2026-05-06.

An offline-only epoch30 ablation was run under the same base-relative
safe-norm config family.

```text
candidate   sampling  normalized_mse  action_mse
BC ref      direct    0.959101        3.0668218e-07
DP e10      zero      1.014984        3.2943791e-07
DP e30      zero      0.981314        3.1285387e-07
FM e10      zero      0.938351        3.1596741e-07
FM e30      zero      1.326868        4.1219857e-07
```

Interpretation:

- DP improves with the small epoch-budget increase, but not enough to displace
  BC as the rollout-planning reference.
- FM worsens at epoch30 on this split, so extending FM without a different
  regularization/sampler plan is not justified.
- Full DP/FM training remains blocked.
- Learned rollout execution remains blocked; BC has only passed dry-run
  action-label checks, not live learned control.

## Rollout-Planning Preflight

Date: 2026-05-07.

The current rollout-planning state is now captured by:

```text
outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.md
outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.json
```

Preflight decision:

```text
candidate_status=rollout_planning_candidate
go_for_learned_execution_now=false
separate_execution_approval_required=true
```

Interpretation:

- BC base-relative h8 xyz remains the only rollout-planning reference.
- DP/FM remain offline-only comparison candidates.
- The next live step, if separately approved, must be a tiny arm-only smoke
  after return-to-reference and two fresh target-aware gates.
- No gripper/hand controller and no grasp claim.

## IK Preview Before Execution

Date: 2026-05-07.

The BC base-relative dry-run adapter can now run a non-publishing IK preview:

```text
roslaunch rexrov_single_oberon7_fm_dp b8_bc_h8_xyz_base_relative_rollout_dry_run.launch \
  execute_actions:=false \
  preview_ik_once:=true \
  preview_ik_required:=true
```

Latest result:

```text
preview_status=passed
would_publish_arm_command=false
clipped_joint_delta_max_abs=0.01
control_commands_sent=false
gripper_commands_sent=false
```

Interpretation:

- The learned BC action can be converted into a bounded active-left IK command
  preview.
- This is still dry-run/pre-execution evidence only.
- Learned arm execution still requires separate explicit approval.

## Base-Relative Rollout Planning Safety Plan V2

Date: 2026-05-07.

The rollout-planning safety/evaluation plan has been updated to match the
current base-relative safe-norm BC checkpoint:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_arm_only_rollout_safety_plan.md
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_arm_only_rollout_safety_plan.json
```

This supersedes the earlier absolute-pose `BC h8 xyz` safety-plan artifact for
current rollout planning. The current candidate is:

```text
checkpoint=outputs/checkpoints/b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt
config=config/train_bc_b8_primary30_h8_xyz_base_relative_safe_norm.yaml
observation=active joints + base-frame EEF/target geometry + progress
excluded_observation=absolute world target_pose, base_pose, gripper_state
action=dx,dy,dz in base_link
```

The read-only readiness preflight now defaults to this v2 plan:

```text
scripts/analyze_b8_base_relative_rollout_readiness.py
outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.md
outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.json
```

Latest preflight decision:

```text
candidate_status=rollout_planning_candidate
checks_passed=true
go_for_learned_execution_now=false
separate_execution_approval_required=true
rollout_ready_success_claimed=false
```

Planning implication:

- BC base-relative h8 xyz remains the only rollout-planning reference.
- DP/FM remain offline-only comparison candidates under the same observation
  and safe normalization.
- No learned execution is approved by this plan.
- Before any tiny learned arm-only smoke: return-to-reference, two fresh
  target-aware gates, and separate explicit approval remain mandatory.

## Tiny Smoke Execution Gap Checklist

Date: 2026-05-07.

Added a read-only checklist artifact for the transition from rollout planning
to any future tiny arm-only execution smoke:

```text
scripts/generate_b8_base_relative_tiny_smoke_checklist.py
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_checklist.md
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_checklist.json
```

Latest checklist result:

```text
checklist_status=ready_for_review
checks_passed=true
current_adapter_can_execute_actions=false
learned_execution_approved_here=false
```

The current base-relative adapter remains intentionally dry-run only:

```text
execute_actions=true is forbidden
calls ArmEEDeltaCommandConverter.convert() for preview only
does not call ArmEEDeltaCommandConverter.execute()
publishes only dry-run action-label topics
```

Training/rollout implication:

- Do not run the current dry-run launch with `execute_actions:=true`.
- Do not treat the BC candidate as rollout-ready success.
- If execution is separately approved, implement/review a dedicated tiny
  active-left arm-only execution adapter first.
- DP/FM remain offline-only until their sampled action quality is credible
  under the same base-relative observation and safe action normalization.

## Dedicated Tiny Execution Smoke Adapter

Date: 2026-05-07.

A dedicated execution-smoke adapter now exists for the BC base-relative h8 xyz
candidate:

```text
scripts/b8_bc_h8_xyz_base_relative_execution_smoke_node.py
config/b8_bc_h8_xyz_base_relative_execution_smoke.yaml
launch/b8_bc_h8_xyz_base_relative_execution_smoke.launch
```

Static review artifacts:

```text
outputs/logs/b8_rollout_planning/base_relative_execution_smoke_adapter_review.md
outputs/logs/b8_rollout_planning/base_relative_execution_smoke_adapter_review.json
```

Review result:

```text
adapter_review_status=ready_for_return_and_two_fresh_gates
checks_passed=true
```

Execution remains opt-in and bounded:

```text
execute_actions default=false
i_understand_this_publishes_arm_commands default=false
max_control_ticks=3
max_policy_xyz_component=0.005
max_joint_delta_per_command_rad=0.01
```

The next runtime sequence is:

1. Return left arm to the B8 reference.
2. Run two fresh target-aware gates.
3. If both gates pass, run one tiny active-left arm-only execution smoke.
4. Immediately inspect output JSON and run post-smoke diagnostics.

This does not affect DP/FM status. DP/FM remain offline-only comparison
candidates until they beat or materially complement the BC base-relative
reference under the same observation/normalization.

Command runbook for the first tiny smoke:

```text
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_runbook.md
```

## First Tiny Smoke Outcome

Date: 2026-05-07.

The first tiny active-left arm-only learned smoke completed the command-path
smoke:

```text
status=max_control_ticks_complete
samples=3
control_commands_sent=true
gripper_commands_sent=false
hand_controller_started=false
aborted=false
```

Read-only summary:

```text
scripts/summarize_b8_base_relative_tiny_smoke.py
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_summary.md
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_summary.json
```

Result:

```text
command_path_smoke_resolved=true
smoke_status=command_path_smoke_resolved_not_success
arm_only_reaching_success_claimed=false
grasp_success_claimed=false
```

The execution path is now smoke-level resolved, but the single run is not a
success claim:

```text
post_gate_initial_distance=0.09675726747351836
gate_distance_reduction=0.010939597194799588
required_distance_reduction_for_success>0.02
```

The post initial-state gate failed on `relative_base_drift_ok`; this is
expected after moving the arm and should not be interpreted as target drift.
Target drift remained under `0.01 m`.

Next training implication:

- Do not start full DP/FM training from this.
- Do not claim learned rollout success.
- Before any second learned smoke, return to reference and review this first
  smoke summary.

## First Tiny-Smoke Review Decision

Date: 2026-05-07.

Read-only review artifacts:

```text
outputs/logs/b8_rollout_planning/first_tiny_smoke_review_decision.md
outputs/logs/b8_rollout_planning/first_tiny_smoke_review_decision.json
```

Decision:

```text
recommended_next_path=second_tiny_smoke_after_separate_approval
second_smoke_max_control_ticks=5
keep_same_checkpoint=true
keep_same_action_horizon=true
keep_same_clip_limits=true
do_not_change_model_now=true
do_not_train_dp_fm_now=true
requires_return_and_two_fresh_gates=true
```

Training implication:

- Do not modify action horizon yet.
- Do not retrain BC yet.
- Do not start longer/full DP/FM training.
- A second live smoke, if separately approved, should isolate only the tick
  budget variable: `max_control_ticks=5`.
- If the second smoke fails monotonic improvement or aborts, stop live testing
  and return to offline diagnostics.

## Second Tiny-Smoke Runbook

Date: 2026-05-07.

Prepared the second controlled live-smoke runbook:

```text
outputs/logs/b8_rollout_planning/second_tiny_smoke_runbook.md
```

It keeps the model/training setup fixed:

```text
same_checkpoint=true
same_action_horizon=true
same_clip_limits=true
do_not_train_dp_fm_now=true
```

The only live variable changes from the first smoke:

```text
max_control_ticks: 3 -> 5
```

This remains a live smoke test plan, not a training stage. A second smoke result
must be summarized and reviewed before any third smoke, rollout batch, or
training decision.

## BC Tiny Repeatability N=3 Boundary

Date: 2026-05-07.

After the N=2 BC base-relative arm-only repeatability smoke passed, the next
live continuation was limited to an N=3 repeatability runbook:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3_runbook.md
```

N=3 was executed after ROS was restarted. The run stopped on cycle 1:

```text
cycle_0=passed
cycle_1=failed
cycle_2=not_run
repeatability_smoke_status=not_resolved
partial_summary=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/partial_summary_after_stop.json
```

The run did not change the checkpoint, action horizon, clip limits, or tick
budget:

```text
checkpoint=b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt
action_horizon=8
max_control_ticks=5
max_policy_xyz_component=0.005
max_joint_delta_per_command_rad=0.01
```

The system was returned to reference afterward and strict gate passed.

Training implication:

- N=2 remains the latest executed live repeatability evidence.
- N=3 is not resolved and should not be used as approval for a large rollout
  batch.
- Do not run another live smoke immediately; inspect the cycle 1 artifacts or
  return to offline-only diagnostics.
- DP/FM remain offline-only; no DP/FM live execution is approved.

## N=3 Failure Read-Only Diagnosis

Date: 2026-05-07.

Completed a combined read-only live artifact comparison and offline-only model
diagnostic:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/read_only_failure_diagnosis.md
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/read_only_failure_diagnosis.json
```

Key diagnostic result:

```text
policy_output_instability_detected=false
geometry_ood_detected=false
clip_limited_motion_detected=true
insufficient_motion_detected=true
target_drift_boundary_detected=true
```

Training implication:

- Do not treat the failed N=3 attempt as a reason to start DP/FM live.
- Do not start full DP/FM training from this live failure.
- The immediate issue appears to be live execution budget/clip brittleness
  under target drift, not raw BC output instability.
- Further work should stay offline-only: tick-budget/clip sensitivity using
  recorded traces, or model diagnostics under the same base-relative safe-norm
  observation.

## N=3 Tick/Clip Sensitivity Projection

Date: 2026-05-07.

Completed an offline-only replay-style projection:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/offline_tick_clip_sensitivity.md
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/offline_tick_clip_sensitivity.json
```

Key result:

```text
live_rerun_approved=false
dp_fm_live_approved=false
training_started=false
cycle_1_required_ticks_current_clip_for_reduction=9
cycle_1_required_ticks_raw_scale_for_reduction=5
cycle_1_raw_to_clipped_norm_ratio_mean=2.0005623615947354
```

Projection examples:

```text
clip=0.005 ticks=8 -> distance_gate_pass=false
clip=0.0075 ticks=6 -> distance_gate_pass=true, all_modeled_pass=false
clip=0.010 ticks=5 -> distance_gate_pass=true, all_modeled_pass=false
```

Training implication:

- The failed N=3 cycle does not justify DP/FM live.
- This projection also does not justify training changes by itself.
- The plausible next variable is execution budget/clip sensitivity, but any
  live rerun would need a separate approval and should change only one
  variable at a time.

## Current No-Training Gate: B8' Small Debug Batch

Date: 2026-05-05.

Latest real non-fallback arm-only reaching/pre-grasp debug batch:

```text
data/raw/b8_reaching_debug_10/
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
gripper_enabled: false for all episodes
is_grasp_dataset: false for all episodes
```

Training decision:

```text
Do not train BC / Diffusion Policy / Flow Matching Policy from this batch.
```

Reason:

- The small debug-batch quality gate was `success_count / N >= 0.8`; this run
  reached `0.7`.
- The final three episodes failed consecutively and command-motion diagnostics
  recommended not collecting more until the command-to-motion path is
  explained.
- The batch is valid debug data, not a completed training dataset.
- This remains arm-only reaching/pre-grasp data, not grasp data.

## Live Arm-Only BC / DP / FM Evaluation Outcome

Date: 2026-05-07.

Offline action MSE is no longer being used as a substitute for live success
rate. A shared live arm-only protocol was implemented and executed for BC,
Diffusion Policy, and Flow Matching Policy.

Artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_protocol_attempts_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_protocol_attempts_summary.md
```

Decision:

```text
complete_three_method_live_comparison=false
equal_N_across_methods=false
dp_fm_have_live_arm_only_evidence=true
grasp_success_claimed=false
```

Training implication:

```text
Do not start additional BC/DP/FM training solely from these live attempts. The
current limitation is shared live protocol/controller termination sensitivity,
not a confirmed need for more training.
```

Update after v8:

```text
success_criterion_early_stop_guard_implemented=true
v8_rollout_started=false
v8_blocker=strict_fresh_pre_gate_failed
next_step=target_gate_reset_or_settle_then_same_protocol_rerun
```

Update after user restart:

```text
v8_after_user_restart_complete_three_method_comparison=false
v8_after_user_restart_result=BC 0/1, DP tiny-smoke threshold miss, FM 2/3
v9_threshold095_result=partial only; threshold-only variant did not close table
training_change_recommended=false
next_step=fix live termination/summary alignment, not retraining
```

Update after v10/v10b:

```text
early_stop_pre_gate_1_baseline_fix=true
terminal_early_stop_observation_logged=true
summarizer_terminal_observation_compatibility=true
v10b_complete_three_method_comparison=false
training_change_recommended=false
next_step=define final-distance source/settle behavior, then rerun N=3
```

Update after v11 terminal-final-distance protocol:

```text
complete_three_method_live_comparison=true
equal_N_across_methods=true
formal_n=3
BC_success_rate=1.0
DP_success_rate=1.0
FM_success_rate=1.0
training_change_recommended=false
```

Interpretation:

```text
The live N=3 arm-only reaching comparison is complete under one shared
protocol. Do not use offline MSE as the success-rate substitute. Do not start
additional training solely to explain the N=3 live table.
```

Update after v12b N=10:

```text
complete_three_method_live_comparison=true
equal_N_across_methods=true
formal_n=10
BC_success_rate=1.0
DP_success_rate=1.0
FM_success_rate=1.0
training_change_recommended=false
```

Training implication:

```text
The requested larger-N live comparison is complete. There is no evidence from
this run that additional BC/DP/FM training is needed before presentation.
```
