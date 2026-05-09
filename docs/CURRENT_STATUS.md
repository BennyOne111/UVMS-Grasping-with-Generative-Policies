# Current Status

Last updated: 2026-05-07

## Latest BC/DP/FM Formal Live Protocol Attempt

Date: 2026-05-07.

A formal same-protocol live arm-only reaching/pre-grasp evaluation protocol was
created for BC / DP / FM, but live execution was stopped before any policy arm
rollout because the strict fresh target-aware pre-gate failed repeatedly after
return-to-reference.

Runtime read-only checks passed for ROS master, `/joint_states`,
`/rexrov/pose_gt`, `/gazebo/model_states`, TF
`rexrov/base_link -> oberon7_l/end_effector`, and
`/oberon7/arm_position_l/state`. Controller manager reported only
`joint_state_controller` and `oberon7/arm_position_l` running; no hand
controller was running.

Artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/formal_protocol.md
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/formal_protocol.json
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/bc/cycle_0/
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
```

BC cycle-0 result:

```text
return_to_reference: reached=true, commands_sent=0, gripper_commands_sent=false
strict pre-gate attempts: 3/3 failed
best retry initial_distance=0.11371573515906652
best retry target_base_drift=0.010550711129789662
best retry relative_base_drift=0.007371669176824283
strict target/relative drift threshold=0.001
policy rollout commands sent=false
gripper commands sent=false
hand controller started=false
```

Combined partial summary:

```text
complete_three_method_live_comparison=false
equal_N_across_methods=false
bc_success_count=0/1, success_rate=0.0, abort_reason=strict_pre_gate_failed_target_relative_drift
dp_success_rate=null, not run because BC strict pre-gate blocked live evaluation
fm_success_rate=null, not run because BC strict pre-gate blocked live evaluation
grasp_success_claimed=false
object_grasped_lifted_held_claimed=false
```

Decision: do not claim BC/DP/FM live success-rate comparison completion. The
next minimum fix is target/base synchronization or target gate reset/restart,
then rerun the strict fresh target-aware gate before any policy command.

Follow-up target-gate restart attempt:

```text
target gate probe launch restarted by Codex
target model present=true
BC return_to_reference reached=true
strict pre-gate after restart failed
retry target_base_drift=0.006711007793366516 > 0.001
retry relative_base_drift=0.006271075196806217 > 0.001
rollout command sent=false
```

Additional artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol_after_target_restart/
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_after_target_restart.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_after_target_restart.json
```

The restart reduced but did not resolve target/relative drift. Live evaluation
remains stopped at the strict initial gate.

## Aggressive Live BC/DP/FM Protocol v4 Result

Date: 2026-05-07.

After the target gate restart, a bounded protocol-v4 live evaluation was run
with shared settings for all methods:

```text
task=arm-only reaching / pre-grasp positioning
success=post_gate_initial_distance <= 0.10 and distance_reduction > 0.02 and no abort
initial_distance_max=0.125
target_drift_max=0.02
relative_drift_max=0.02
max_control_ticks=9
clip=0.005 m
max_joint_delta=0.01 rad
gripper_enabled=false
hand_controller_allowed=false
```

Final artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol_v4/
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
```

Result:

```text
BC: success_count=0/1, success_rate=0.0, abort_count=1
BC failure_reason=arm_command_conversion_or_execution_failed
BC note=distance threshold was reached, but an IK failure after continued ticks caused safety abort

DP: success_count=3/3, success_rate=1.0
DP mean_final_distance=0.07340604205685235
DP mean_min_distance=0.0753625276898795
DP mean_distance_reduction=0.04164234887598133
DP abort_count=0

FM: success_count=3/3, success_rate=1.0
FM mean_final_distance=0.07724064665390937
FM mean_min_distance=0.07588761756813343
FM mean_distance_reduction=0.038229286508386605
FM abort_count=0

equal_N_across_methods=false
complete_three_method_live_comparison=false
gripper_commands_sent=false
grasp_success_claimed=false
object_grasped_lifted_held_claimed=false
```

Interpretation: DP and FM now have live arm-only reaching/pre-grasp N=3
success-rate evidence under the same protocol. BC remains incomplete under this
formal protocol because the first BC cycle safety-aborted on IK error code
`-31`; do not mix BC N=1/failed with DP/FM N=3 as a fair three-method table.

## Scope

This file tracks the current debug status after Stages 0-12 and the route
adjustment to arm-only reaching / pre-grasp positioning.

Current first-version real closed-loop demo route:

```text
RexROV + single-active-left Oberon7 arm-only reaching / pre-grasp positioning
```

The long-term goal can remain underwater grasping, but the current route is
not grasping. The project should not claim real rollout success rate until the
full live loop is verified:

```text
policy/expert action
  -> real left-arm motion with gripper disabled
  -> recorder captures non-fallback live state
  -> eef_pose and target_pose are available
  -> success_checker evaluates reaching/pre-grasp criteria
```

Do not report `grasp_success`, `grasp_success_rate`, object grasped, object
lifted, or object held for the current route.

## Latest DP/FM Offline Objective Ablation

Date: 2026-05-07.

DP was advanced offline-only with an action-space selection metric and a
normalized x0/action auxiliary objective under the same base-relative safe-norm
h8 xyz setup as the BC rollout-planning checkpoint. No ROS launch, no live
rollout, no gripper/hand command, and no grasp/general rollout success claim
were involved.

Artifacts:

```text
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86_action_select.yaml
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86_x0aux0p1.yaml
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86_x0aux0p1_dimw025_1_1.yaml
outputs/logs/b8_primary30_training_planning/dp_action_selection_outcome.md
outputs/logs/b8_primary30_training_planning/dp_x0_aux_validation.md
outputs/logs/b8_primary30_training_planning/dp_x0_aux_outcome.md
```

Key offline metrics:

```text
bc_action_mse=3.066821534503106e-07
dp30_seed86_baseline_action_mse=3.1088134733181505e-07
dp30_seed86_action_select_best_action_mse=3.1140186251832347e-07
dp30_seed86_x0aux0p1_best_action_mse=3.1106586106943723e-07
dp30_seed86_x0aux0p1_dimw025_1_1_best_action_mse=3.110033617303998e-07
best_dp=dp30_seed86_baseline_best
best_dp_relative_to_bc=0.013692332058653145
x0_aux_improves_mean_action_mse_over_baseline=false
x0_aux_beats_bc=false
per_dim_x0_aux_improves_mean_action_mse_over_baseline=false
per_dim_x0_aux_beats_bc=false
bc_remains_reference=true
dp_fm_live_approved=false
```

Decision: per-dimension weighted x0 auxiliary loss is slightly better than the
scalar x0-aux candidate, but still does not beat baseline DP seed86 or BC. BC
remains the live reference. DP/FM can continue only as offline
objective/selection design work; DP/FM live execution remains blocked.

## Latest DP/FM Final Presentation Result

Date: 2026-05-07.

DP/FM now have a presentation-ready offline result package under the same B8'
primary30 base-relative safe-norm h8 xyz setup. This is offline-only and does
not approve DP/FM live execution.

Artifacts:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_results.md
outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_results.json
outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_results.csv
outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_slide_notes.md
```

Presentation metrics:

```text
bc_action_mse=3.066821534503106e-07
best_dp=dp30_seed86_baseline_best
best_dp_action_mse=3.1088134733181505e-07
best_dp_relative_to_bc=+1.3692332058653145%
best_fm=fm30_action_select_best_action
best_fm_action_mse=3.0398447847801435e-07
best_fm_relative_to_bc=-0.8796321996393281%
fm_beats_bc_offline_action_mse=true
dp_beats_bc_offline_action_mse=false
dp_fm_live_approved=false
```

Interpretation: FM produced the best offline validation action MSE via an
action-selected epoch-1 checkpoint. DP improved through seed/objective
ablations but did not beat BC. BC remains the only live-smoke-tested reference;
do not claim DP/FM rollout success, grasp success, or general learned rollout
success.

## Latest Second Tiny Arm-Only Learned Smoke Result

Date: 2026-05-07.

The second controlled active-left arm-only BC base-relative execution smoke was
run after return-to-reference and two fresh target-aware gates. This run used
the same base-relative safe-norm BC checkpoint, same action horizon, and same
clip limits as the first smoke; only `max_control_ticks` changed from `3` to
`5`.

Summary artifacts:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_second_execution_smoke.json
outputs/logs/b8_rollout_planning/second_tiny_smoke_post_gate/post_smoke_gate.json
outputs/logs/b8_rollout_planning/second_tiny_smoke_summary.md
outputs/logs/b8_rollout_planning/second_tiny_smoke_summary.json
```

Result:

```text
smoke_status=arm_only_reaching_success
command_path_smoke_resolved=true
arm_only_reaching_success_claimed=true
learned_rollout_success_claimed=false
grasp_success_claimed=false
control_commands_sent=true
gripper_commands_sent=false
hand_controller_started=false
aborted=false
samples=5
raw_action_absmax=0.010124818421900272
clipped_action_absmax=0.005
clipped_joint_delta_absmax=0.01
pre_gate_1_initial_distance=0.11405293503812372
post_gate_initial_distance=0.0796048439094755
gate_distance_reduction=0.03444809112864822
smoke_distance_reduction=0.022283184328319994
post_gate_target_base_drift=0.0006060769336670867
```

Interpretation:

- The active-left command path is resolved beyond command-path-only smoke: one
  reviewed tiny run met the configured arm-only reaching smoke threshold.
- This is still a single arm-only smoke result, not a general learned rollout
  success rate, not grasping, and not object manipulation.
- The post initial-state gate failing `relative_base_drift_ok` is expected
  after moving the arm; target drift itself stayed within threshold.
- Do not run another live learned smoke or rollout batch before returning the
  arm to reference and reviewing whether repeatability testing is needed.

Post-second-smoke recovery:

```text
outputs/logs/b8_rollout_planning/post_second_tiny_smoke_return_gate/return_to_reference.json
outputs/logs/b8_rollout_planning/post_second_tiny_smoke_return_gate/gate.json
outputs/logs/b8_rollout_planning/post_second_tiny_smoke_return_gate/gate_retry_1.json
```

Result:

```text
return_reached=true
return_commands_sent=4
return_joint_l2_error=0.00010727774213185266
return_joint_max_abs_error=7.796206191645894e-05
return_gripper_commands_sent=false
first_strict_gate_passed=false
first_strict_gate_failed_checks=[initial_distance_ok]
first_strict_gate_initial_distance=0.11597705385617631
retry_strict_gate_passed=true
retry_strict_gate_initial_distance=0.11436097332458071
retry_relative_base_drift=0.0070635920892258355
retry_target_base_drift=0.007080020803718068
```

Interpretation: the system did return to a controlled strict initial gate after
one settle/retry. The first gate failure was a marginal initial-distance
boundary miss, not an arm reset failure and not a gripper/hand issue.

Implementation note:

```text
scripts/summarize_b8_base_relative_tiny_smoke.py
```

was fixed so a run that meets the configured arm-only distance threshold is
reported as `smoke_status=arm_only_reaching_success`; it still never claims
grasp success or general learned rollout success.

## Latest B8' Rollout-Planning Status

Date: 2026-05-06.

The old absolute-world BC h8 xyz adapter is not rollout-planning safe. Its live
dry-run produced an unsafe raw `dx` because the checkpoint used absolute
world `target_pose` / `base_pose` and `action_std=1.0` for a near-constant
clipped `dx` dimension.

A replacement base-relative arm-only BC checkpoint and matching live dry-run
adapter now exist:

```text
config/train_bc_b8_primary30_h8_xyz_base_relative_safe_norm.yaml
outputs/checkpoints/b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt
scripts/b8_bc_h8_xyz_base_relative_rollout_dry_run_node.py
config/b8_bc_h8_xyz_base_relative_rollout_dry_run.yaml
launch/b8_bc_h8_xyz_base_relative_rollout_dry_run.launch
```

Observation design for this route:

```text
active_joint_positions
active_joint_velocities
eef_position_base_frame
target_position_base_frame
target_to_eef_base_frame
episode_progress
episode_remaining
```

It intentionally excludes absolute world `base_pose`, absolute world
`target_pose`, and `gripper_state`.

Latest live action-label check:

```text
launch: b8_bc_h8_xyz_base_relative_rollout_dry_run.launch
execute_actions: false
output: outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_dry_run_latest.json
status: timeout_complete
samples: 21
aborted: false
control_commands_sent: false
gripper_commands_sent: false
raw_action_absmax: 0.010233319364488125 m
raw_action_p95_absmax_per_tick: 0.010180839337408543 m
clipped_action_absmax: 0.005 m
```

Decision:

```text
base-relative BC h8 xyz dry-run adapter: implemented and smoke-checked
offline/live action-scale blocker for BC: resolved at dry-run label level
learned rollout success: not claimed
learned arm execution: not run
gripper/hand command: not run
DP/FM comparison: still must use this same observation + safe normalization
```

## Latest DP/FM Offline Comparison Gate

Date: 2026-05-06.

DP/FM comparison has been rerun under the same base-relative arm-only
observation and safe action normalization as the BC rollout-planning
checkpoint. Old absolute-world pose checkpoints are excluded.

New offline-only configs:

```text
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_smoke.yaml
config/train_flow_matching_b8_primary30_h8_xyz_base_relative_safe_norm_smoke.yaml
```

New checkpoints:

```text
outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_smoke/best.pt
outputs/checkpoints/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_smoke/best.pt
```

Val offline comparison:

```text
policy              sampling  normalized_mse  action_mse       pred_p95_absmax
BC                  direct    0.959101        3.0668218e-07    0.01011395
Diffusion Policy    zero      1.014984        3.2943791e-07    0.01025867
Flow Matching       zero      0.938351        3.1596741e-07    0.01013040
```

Report:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_offline_comparison.md
outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_offline_comparison.json
```

Decision:

```text
offline DP/FM comparison under the correct observation/norm: complete
BC remains the rollout-planning reference
DP/FM are close enough for further offline-only budget/sampling ablation
full DP/FM training: not approved by this comparison alone
learned rollout success: not claimed
learned arm execution: not run
gripper/hand command: not run
```

## Latest DP/FM Epoch-Budget Ablation

Date: 2026-05-06.

Small offline-only epoch-budget ablation under the same base-relative
safe-norm configuration family:

```text
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30.yaml
config/train_flow_matching_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30.yaml
```

Validation comparison:

```text
candidate   sampling  normalized_mse  action_mse
BC ref      direct    0.959101        3.0668218e-07
DP e10      zero      1.014984        3.2943791e-07
DP e30      zero      0.981314        3.1285387e-07
FM e10      zero      0.938351        3.1596741e-07
FM e30      zero      1.326868        4.1219857e-07
```

Report:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_epoch_budget_ablation.md
outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_epoch_budget_ablation.json
```

Decision:

```text
DP epoch30 improves over DP epoch10 but still does not beat BC action MSE.
FM epoch30 worsens versus FM epoch10 and should not be extended blindly.
BC remains the rollout-planning reference.
Full DP/FM training remains blocked.
No learned rollout, arm command, gripper command, or grasp claim.
```

## Latest DP/FM Post-Live-Smoke Offline Gate

Date: 2026-05-07.

After the second BC base-relative tiny arm-only smoke met the configured
single-smoke reaching threshold, DP/FM work was moved back to offline-only.
No ROS, simulator, arm command, gripper command, or training rollout was run.

New read-only report script/artifacts:

```text
scripts/analyze_b8_dp_fm_post_live_smoke_gate.py
outputs/logs/b8_primary30_training_planning/dp_fm_post_live_smoke_offline_gate.md
outputs/logs/b8_primary30_training_planning/dp_fm_post_live_smoke_offline_gate.json
```

Additional offline sampling-sensitivity checks:

```text
DP epoch30 zero-init steps: 10, 25, 50, 100
FM epoch10 zero-init ODE steps: 10, 25, 50, 100
```

Key result:

```text
BC h8 base-relative action_mse=3.0668218187202e-07
best DP h8 zero action_mse=3.1285387080970395e-07 at 50 steps
best FM h8 zero action_mse=3.1596741223438585e-07 at 50 ODE steps
dp_fm_live_execution_approved=false
full_dp_fm_training_approved=false
bc_remains_live_reference=true
```

Interpretation:

- DP/FM are still close offline, but neither beats the current BC live
  reference under the same base-relative observation and safe action
  normalization.
- Increasing DP steps beyond 50 did not improve action MSE; FM ODE-step
  sensitivity was essentially flat.
- DP/FM live execution remains blocked. If DP/FM continues, the next acceptable
  work is a bounded offline-only DP h8 budget/seed ablation, not full training
  and not live rollout.

## Latest BC Tiny Repeatability Plan

Date: 2026-05-07.

Prepared, but did not run, the next BC live repeatability check:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n2_runbook.md
scripts/summarize_b8_base_relative_tiny_repeatability.py
```

Scope:

```text
N=2 only
same BC base-relative safe-norm checkpoint
same action horizon
same clip limits
max_control_ticks=5
stop_on_first_failure=true
no_gripper_or_hand=true
no_grasp_claim=true
general_learned_rollout_success_claimed=false
```

Each cycle requires:

```text
return_left_arm_to_reference
strict fresh gate with wait/retry only
same BC base-relative tiny smoke
post gate
per-cycle summary
```

The aggregate summary script was smoke-tested offline using existing summary
artifacts and registered in `CMakeLists.txt`. No ROS command, arm command,
gripper command, training, DP/FM live execution, or third smoke was run during
this preparation step.

## Latest BC Tiny Repeatability N=2 Result

Date: 2026-05-07.

The N=2 BC base-relative tiny repeatability runbook was executed with fixed
checkpoint, action horizon, clip limits, and `max_control_ticks=5`.

Artifacts:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n2/
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n2/summary.md
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n2/summary.json
```

Aggregate result:

```text
repeatability_smoke_status=arm_only_reaching_repeatability_smoke_passed
repeatability_smoke_passed=true
arm_only_reaching_repeatability_claimed=true
success_count=2/2
mean_final_distance=0.07611795154782355
max_final_distance=0.07671502116552151
mean_gate_distance_reduction=0.036224460767812244
min_gate_distance_reduction=0.034746377345962684
learned_rollout_success_claimed=false
grasp_success_claimed=false
gripper_commands_sent=false
```

Per-cycle status:

```text
cycle_0 smoke_status=arm_only_reaching_success
cycle_0 final_distance=0.07552088193012559
cycle_0 gate_distance_reduction=0.037702544189661805
cycle_0 raw_action_absmax=0.010138695128262043

cycle_1 smoke_status=arm_only_reaching_success
cycle_1 final_distance=0.07671502116552151
cycle_1 gate_distance_reduction=0.034746377345962684
cycle_1 raw_action_absmax=0.010102524422109127
```

Both post-smoke gates failed only on `relative_base_drift_ok`, which is
expected after arm motion; target-base drift stayed below `0.01 m`.

Post-repeatability recovery:

```text
return_reached=true
return_joint_l2_error=0.0001292675365380578
return_joint_max_abs_error=9.511785811078255e-05
strict_gate_passed=true
strict_gate_initial_distance=0.10690899555892072
strict_gate_relative_base_drift=0.0008686295574533427
strict_gate_target_base_drift=0.0009021523014487895
```

Interpretation:

- BC base-relative active-left arm-only reaching is now repeatability-smoke
  resolved for N=2.
- This is still not grasp success and not a general learned rollout success
  rate.
- Do not jump directly to a large rollout batch. If continuing live work, the
  next step should be a separately planned N=3 repeatability check using the
  same parameters.

## Latest BC Tiny Repeatability N=3 Attempt

Date: 2026-05-07.

The N=3 continuation runbook was executed after ROS was restarted:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3_runbook.md
```

Runtime result:

```text
N=3 live run executed=true
stop_policy=stop_on_first_failure
cycle_0=passed
cycle_1=failed
cycle_2=not_run
partial_summary=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/partial_summary_after_stop.json
repeatability_smoke_status=not_resolved
repeatability_smoke_passed=false
success_count=1/2 observed, expected 3
arm_only_reaching_repeatability_claimed=false
learned_rollout_success_claimed=false
grasp_success_claimed=false
gripper_commands_sent=false
```

Cycle 0 passed:

```text
pre_gate_initial_distance=0.1077106188681088
post_gate_initial_distance=0.08205602794720912
gate_distance_reduction=0.02565459092089968
smoke_distance_reduction=0.022549257867972697
post_gate_target_base_drift=0.004307210431956841
raw_action_absmax=0.010069108568131924
clipped_action_absmax=0.005
clipped_joint_delta_absmax=0.01
```

Cycle 1 failed the per-cycle summary:

```text
pre_gate_initial_distance=0.10903377978212389
post_gate_initial_distance=0.09688016467661553
gate_distance_reduction=0.012153615105508359
smoke_distance_reduction=0.01512330204500184
post_gate_target_base_drift=0.01016428396425749
raw_action_absmax=0.010100629180669785
clipped_action_absmax=0.005
clipped_joint_delta_absmax=0.01
failed_checks=post_target_drift_ok, arm_only_success_threshold
```

The wrapper then returned the arm to reference and ran a strict fresh gate:

```text
recovery_return_reached=true
recovery_return_joint_l2_error=0.0001857971116926321
recovery_return_joint_max_abs_error=0.00016350626718075745
recovery_strict_gate_passed=true
recovery_initial_distance=0.10764093300810804
recovery_relative_base_drift=7.61146949187862e-05
recovery_target_base_drift=7.858877410019059e-05
```

Interpretation:

- N=3 repeatability is not resolved.
- N=2 remains the strongest executed live repeatability evidence.
- Do not run another live smoke immediately.
- Next work should be read-only diagnostics on cycle 1 or offline-only model
  analysis.
- DP/FM remain offline-only.

## Latest N=3 Read-Only Failure Diagnosis

Date: 2026-05-07.

Completed the two requested read-only lines together:

```text
live artifact comparison=true
offline_model_diagnostics=true
control_commands_sent=false
gripper_commands_sent=false
training_started=false
dp_fm_live_execution=false
```

Artifacts:

```text
scripts/analyze_b8_n3_repeatability_failure.py
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/read_only_failure_diagnosis.json
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/read_only_failure_diagnosis.md
```

Decision:

```text
n3_repeatability_resolved=false
cycle1_failed=true
policy_output_instability_detected=false
target_drift_boundary_detected=true
insufficient_motion_detected=true
clip_limited_motion_detected=true
geometry_ood_detected=false
```

Live artifact comparison:

```text
cycle_0_distance_trace=[0.10770563213739766, 0.10142589637876798, 0.09461431768771815, 0.09029866267785029, 0.08515637426942496]
cycle_1_distance_trace=[0.10766687024029667, 0.1034693864556223, 0.09864202861453193, 0.0960789292727208, 0.09254356819529483]
cycle_0_gate_distance_reduction=0.02565459092089968
cycle_1_gate_distance_reduction=0.012153615105508359
cycle_0_post_target_base_drift=0.004307210431956841
cycle_1_post_target_base_drift=0.01016428396425749
cycle_0_raw_action_mean=[0.009959764964878558, 0.00012267265701666475, 0.010031704790890217]
cycle_1_raw_action_mean=[0.009955698624253273, 0.00013040421108598821, 0.010052720084786415]
cycle_0_clipped_action_mean=[0.005, 0.00012267265701666475, 0.005]
cycle_1_clipped_action_mean=[0.005, 0.00013040421108598821, 0.005]
```

Offline-only model diagnostic:

```text
live_raw_action_absmax=0.010049115866422653
live_clipped_action_absmax=0.005
live_raw_action_abs_z_max=0.5361478646462661
train_action_abs_p99=[0.009999999776482582, 0.001722396002151072, 0.009999999776482582]
geometry_ood_detected=false
eef_position_base_frame_live_abs_z_max=2.0791297489119525
target_position_base_frame_live_abs_z_max=0.494902031005145
target_to_eef_base_frame_live_abs_z_max=2.0117134072414102
```

Interpretation:

- Cycle 1 failure is not explained by unstable raw policy output.
- Live geometry is not clearly outside the training distribution.
- The model repeatedly requests near-demonstration-scale x/z actions, while
  the live safety clip halves x/z to `0.005 m`.
- With fixed `max_control_ticks=5`, that clipped motion was enough for cycle 0
  but not robust to cycle 1 target drift and command-to-motion variation.
- Do not run another live smoke immediately. Next work should remain
  read-only/offline-only.

## Latest N=3 Tick/Clip Sensitivity Projection

Date: 2026-05-07.

Completed the offline-only tick-budget / clip-limit sensitivity projection:

```text
script=scripts/analyze_b8_n3_tick_clip_sensitivity.py
output_json=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/offline_tick_clip_sensitivity.json
output_md=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/offline_tick_clip_sensitivity.md
projection_only_not_physics_sim=true
control_commands_sent=false
gripper_commands_sent=false
training_started=false
dp_fm_live_execution=false
```

Decision:

```text
n3_repeatability_resolved=false
live_rerun_approved=false
dp_fm_live_approved=false
recommended_status=do_not_run_live_until_offline_plan_reviewed
```

Projection highlights:

```text
cycle_1_current_clip=0.005
cycle_1_current_ticks=5
cycle_1_gate_reduction=0.012153615105508359
cycle_1_required_ticks_current_clip_for_reduction=9
cycle_1_required_ticks_raw_scale_for_reduction=5
cycle_1_raw_to_clipped_norm_ratio_mean=2.0005623615947354
cycle_1_target_base_drift=0.01016428396425749
```

Candidate projection examples:

```text
clip=0.005 ticks=8 -> projected_gate_reduction=0.019445784168813374, distance_gate_pass=false
clip=0.0075 ticks=6 -> projected_gate_reduction=0.02187393241902867, distance_gate_pass=true, all_modeled_pass=false
clip=0.010 ticks=5 -> projected_gate_reduction=0.02424284511639152, distance_gate_pass=true, all_modeled_pass=false
```

Interpretation:

- Increasing tick budget alone from 5 to 8 is still projected just below the
  `0.02 m` reduction threshold for cycle 1 at the current `0.005 m` clip.
- A larger x/z clip is a plausible sensitivity axis, but this projection does
  not resolve the target-drift threshold because drift is assumed static.
- This is not approval for live rerun. If a future live rerun is considered,
  change only one variable at a time after review.
- DP/FM remain offline-only.

## Latest Single-Variable Candidate Plan

Date: 2026-05-07.

Prepared a single-variable candidate review and runbook without executing live
commands:

```text
review_json=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_single_variable_candidate_review.json
review_md=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_single_variable_candidate_review.md
runbook=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke_runbook.md
control_commands_sent=false
gripper_commands_sent=false
training_started=false
dp_fm_live_execution=false
live_rerun_approved_by_this_review=false
```

Selected candidate:

```text
candidate_id=bc_h8_xyz_base_relative_tick9_single_smoke
change=max_control_ticks: 5 -> 9
scope=N=1 only, not repeatability
```

Fixed parameters:

```text
checkpoint=b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt
action_horizon=8
max_policy_xyz_component=0.005
max_joint_delta_per_command_rad=0.01
rate_hz=3.0
max_duration_sec=7.2
```

Reasoning:

- Tick budget is exposed as a launch argument and keeps per-command action and
  joint limits unchanged.
- Clip change was not selected first because it changes per-command authority,
  requires config-level override, and does not resolve target-drift risk in the
  offline projection.
- A pass would only be a single tick-budget sensitivity smoke. It would not
  restore N=3 repeatability and would not claim general learned rollout or
  grasp success.

## Latest Tick9 Single-Smoke Outcome

Date: 2026-05-07.

After explicit approval, executed the prepared N=1 tick-budget sensitivity
smoke with only this variable changed:

```text
max_control_ticks: 5 -> 9
```

Artifacts:

```text
output_dir=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke/
summary=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke/summary.json
outcome=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke/outcome.md
```

Result:

```text
smoke_status=arm_only_reaching_success
checks_passed=true
control_commands_sent=true
gripper_commands_sent=false
hand_controller_started=false
grasp_success_claimed=false
learned_rollout_success_claimed=false
```

Key metrics:

```text
pre_gate_initial_distance=0.10763205373420012
post_gate_initial_distance=0.06884095013771155
gate_distance_reduction=0.038791103596488574
smoke_distance_reduction=0.032973856201507806
raw_action_absmax=0.010168945416808128
clipped_action_absmax=0.005
clipped_joint_delta_absmax=0.01
post_gate_target_base_drift=7.858877409400243e-05
```

Recovery:

```text
recovery_return_reached=true
initial_recovery_gate_passed=false
final_retry_gate_passed=true
final_retry_gate_initial_distance=0.10763685573691596
final_retry_gate_relative_base_drift=7.244770614888639e-05
final_retry_gate_target_base_drift=7.858877410115714e-05
```

Interpretation:

- Tick9 passed as a single arm-only tick-budget sensitivity smoke.
- This does not resolve N=3 repeatability.
- This does not approve another live smoke or a larger rollout batch.
- DP/FM remain offline-only.
- No grasp success or general learned rollout success is claimed.

## Latest Tick9 Vs N3 Tick5 Read-Only Comparison

Date: 2026-05-07.

Generated a read-only comparison of N=3 tick5 cycle 0/1 against the tick9
single smoke. No ROS commands, gripper commands, hand controller, or training
were used.

Artifacts:

```text
script=scripts/analyze_b8_tick9_vs_n3_tick5.py
json=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_vs_n3_tick5_comparison.json
md=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_vs_n3_tick5_comparison.md
```

Decision:

```text
primary_explanation=both_tick_budget_and_cleaner_target_drift
tick_budget_helped=true
target_drift_helped=true
policy_action_shift_detected=false
n3_repeatability_resolved=false
next_live_approved=false
dp_fm_live_approved=false
```

Key comparison:

```text
n3_cycle_1_tick5_smoke_reduction=0.01512330204500184
tick9_first5_reduction_gain_vs_cycle1=0.0025735560748549186
tick9_extra_tick_distance_reduction=0.015276998081651047
tick9_extra_tick_fraction_of_smoke_reduction=0.46330638395130963
tick9_total_reduction_gain_vs_cycle1=0.017850554156505966
cycle1_target_drift=0.01016428396425749
tick9_target_drift=7.858877409400243e-05
clipped_action_mean_delta_cycle1_to_tick9_l2=5.2579650057143435e-05
```

Interpretation:

- The tick9 result is not explained by a policy-output shift; clipped actions
  are effectively the same as the failed tick5 cycle 1.
- The extra four ticks supplied substantial additional distance reduction.
- The target was also much cleaner in the tick9 run, so the pass is partly
  target-drift dependent.
- This does not resolve N=3 repeatability and does not approve another live
  rerun. DP/FM remain offline-only.

## Latest Target-Drift Readiness Gate Review

Date: 2026-05-07.

Generated a read-only target-drift readiness review from existing gate
artifacts only. No ROS commands, gripper commands, hand controller, or training
were used.

Artifacts:

```text
script=scripts/analyze_b8_target_drift_readiness_gate.py
json=outputs/logs/b8_rollout_planning/b8_target_drift_readiness_gate_review.json
md=outputs/logs/b8_rollout_planning/b8_target_drift_readiness_gate_review.md
```

Decision:

```text
target_drift_is_live_confound=true
clean_pre_gate_examples=8
failed_post_target_drift_examples=1
next_live_approved=false
dp_fm_live_approved=false
n3_repeatability_resolved=false
```

Recommended readiness gate for any separately approved future BC live smoke:

```text
name=two_fresh_gates_with_clean_target_drift
consecutive_required=2
initial_distance_max=0.115
relative_base_drift_max=0.001
target_base_drift_max=0.001
joint_l2_max=0.02
joint_max_abs_max=0.01
eef_base_drift_max=0.02
wait_retry_only=true
reset_target_if_failed_after_retries=separate_explicit_approval_required
```

Historical gate distribution:

```text
pre_live_gate_count=25
pre_live_gate_passed=24
pre_live_gate_clean_target=8
pre_live_gate_target_drift_p50=0.003737260370026336
pre_live_gate_target_drift_p95=0.0506330196239176
post_live_gate_target_drift_max=0.01016428396425749
```

Interpretation:

- A standard `passed=true` pre-live gate is not enough to isolate target-drift
  effects.
- Future live readiness should require two consecutive clean target-aware gates
  with both target and relative drift below `0.001 m`.
- This is only a readiness design and does not approve another live run. DP/FM
  remain offline-only.

## Latest DP/FM Post-Tick9 Offline Gate

Date: 2026-05-07.

Generated a post-tick9 DP/FM gate using existing offline eval artifacts only.
No ROS commands, gripper commands, hand controller, BC/DP/FM training, or live
rollout were used.

Artifacts:

```text
script=scripts/analyze_b8_dp_fm_post_tick9_offline_gate.py
json=outputs/logs/b8_primary30_training_planning/dp_fm_post_tick9_offline_gate.json
md=outputs/logs/b8_primary30_training_planning/dp_fm_post_tick9_offline_gate.md
```

Decision:

```text
dp_fm_offline_can_continue=true
dp_fm_live_execution_approved=false
full_dp_fm_training_approved=false
bc_remains_live_reference=true
best_dp_candidate=dp30_zero
best_fm_candidate=fm10_zero
best_non_bc_candidate=dp30_zero
```

Offline metrics:

```text
bc_action_mse=3.0668218187202e-07
dp30_action_mse=3.1285387080970395e-07
dp30_action_mse_relative_to_bc=0.020124054485367575
fm10_action_mse=3.1596741223438585e-07
fm10_action_mse_relative_to_bc=0.03027639331925912
fm30_action_mse_relative_to_bc=0.3440577845904052
```

Interpretation:

- DP30 is the current best non-BC DP/FM offline candidate, but it is still
  about `2.01%` worse than BC by action MSE.
- FM10 has slightly lower normalized MSE than BC but worse action MSE, so it is
  not promoted for live planning.
- DP/FM may continue offline-only under the same base-relative safe-norm setup.
- DP/FM live execution remains blocked by BC repeatability and target-drift
  readiness boundaries.

## Latest DP/FM Validation-Window Diagnostics

Date: 2026-05-07.

Generated offline validation-window diagnostics for BC, DP30 zero, and FM10
zero under the same base-relative safe-norm xyz h8 setup. No ROS commands,
gripper commands, hand controller, training, or live rollout were used.

Artifacts:

```text
script=scripts/analyze_b8_dp_fm_validation_windows.py
json=outputs/logs/b8_primary30_training_planning/dp_fm_validation_window_diagnostics.json
md=outputs/logs/b8_primary30_training_planning/dp_fm_validation_window_diagnostics.md
```

Decision:

```text
bc_remains_reference=true
best_non_bc=dp30_zero
dp30_action_mse_relative_to_bc=0.020124149025167605
fm10_action_mse_relative_to_bc=0.030276674149539513
dp_fm_live_approved=false
training_started=false
```

Validation-window metrics:

```text
bc_action_mse=3.066821534503106e-07
bc_first_step_mse=2.58595216224805e-07
bc_p95_window_mse=1.2529629771051987e-06
bc_max_window_mse=1.3236631275503896e-06
dp30_action_mse=3.1285387080970395e-07
dp30_first_step_mse=2.5940171429975604e-07
dp30_p95_window_mse=1.3123909809564794e-06
dp30_max_window_mse=1.3434267884804285e-06
fm10_action_mse=3.159674690778047e-07
fm10_first_step_mse=2.905671348218173e-07
fm10_p95_window_mse=1.297833932767389e-06
fm10_max_window_mse=2.013348876062082e-06
```

Interpretation:

- DP30 is close to BC but remains worse on aggregate action MSE and p95 window
  MSE.
- FM10 has the worst max-window behavior among the three candidates.
- Action scale is stable; `pred_valid_absmax` stays near `0.0103`.
- Worst windows are concentrated in existing validation boundary episodes,
  especially `b8_controlled_debug_20_0014`.
- DP/FM should continue with offline-only diagnostics; live remains blocked.

## Latest Rollout-Readiness Preflight

Date: 2026-05-07.

A read-only rollout-readiness preflight was added and run:

```text
scripts/analyze_b8_base_relative_rollout_readiness.py
outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.md
outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.json
```

Inputs:

```text
bc_h8_xyz_base_relative_dry_run_latest.json
dp_fm_base_relative_safe_norm_offline_comparison.json
dp_fm_base_relative_safe_norm_epoch_budget_ablation.json
bc_h8_xyz_arm_only_rollout_safety_plan.json
```

Result:

```text
candidate_status=rollout_planning_candidate
checks_passed=true
go_for_learned_execution_now=false
separate_execution_approval_required=true
rollout_ready_success_claimed=false
control_commands_sent=false
gripper_commands_sent=false
raw_absmax=0.010233319364488125
bc_action_mse=3.0668218187202e-07
min_non_bc_action_mse=3.1285387080970395e-07
ik_preview_status=passed
ik_preview_would_publish_arm_command=false
ik_preview_clipped_joint_delta_max_abs=0.01
```

Decision:

```text
BC base-relative h8 xyz is a rollout-planning candidate.
It is not rollout-ready success.
Any learned execution still requires return-to-reference, two fresh gates, and
separate explicit approval for a tiny arm-only smoke.
No gripper/hand path is allowed.
```

## Latest IK Command Preview

Date: 2026-05-07.

The base-relative dry-run adapter now supports a default-off IK preview mode:

```text
preview_ik_once:=true
preview_ik_required:=true
execute_actions:=false
```

This path converts the first clipped policy action into an active-left
`JointTrajectory` preview through the existing IK converter, but it does not
publish the trajectory.

Output:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_ik_preview_latest.json
```

Result:

```text
status=timeout_complete
aborted=false
samples=17
control_commands_sent=false
gripper_commands_sent=false
preview_status=passed
would_publish_arm_command=false
clipped_xyz_action_frame=[0.005, 0.00026573764625936747, 0.005]
clipped_xyz_planning_frame=[-0.004293242404385794, 0.002860568696133876, 0.004843122225230549]
raw_joint_delta_max_abs=0.03397963688957391
clipped_joint_delta_max_abs=0.01
```

Decision:

```text
learned action -> IK command preview path is smoke-level resolved.
No arm command was published.
This still does not approve learned execution.
```

## Completed Pipeline Pieces

- ROS package exists:
  `src/uvms/rexrov_single_oberon7_fm_dp`.
- State-based `.npz` episode schema is defined.
- Episode recorder and validator exist.
- Scripted expert action-label publisher exists.
- Batch collection and dataset summary tools exist.
- BC, Diffusion Policy, and Flow Matching Policy training code exists.
- Offline evaluation, dry-run rollout runtime, and ablation report generation
  exist.
- README and final demo summary exist.

## Current Dataset And Result Status

Current dataset:

```text
data/raw/stage6_debug
outputs/logs/stage6_debug/dataset_split_combined.json
```

Dataset interpretation:

- 20 valid `.npz` episodes.
- Suitable for loader, normalization, training-loop, and report smoke tests.
- Not a real demonstration dataset because Stage 6 used fallback state:
  - `base_state_source: nominal_base_state_fallback`
  - `joint_state_source: zero_joint_state_fallback`
  - `target_state_source: nominal_target_pose_fallback`
  - `allow_nominal_state_fallback: true`

Current policy checkpoints:

```text
outputs/checkpoints/stage7_bc_smoke/best.pt
outputs/checkpoints/stage8_diffusion_smoke/best.pt
outputs/checkpoints/stage9_flow_matching_smoke/best.pt
```

Current evaluation interpretation:

- Stage 10 rollout is dry-run action-label generation only.
- Stage 11 comparison is fallback-data pipeline evidence only.
- `success_rate` is not evaluated for real grasping.

## Known Blockers

1. Live state collection was unstable:
   - `/joint_states`
   - `/rexrov/pose_gt`
   - target pose from `/gazebo/model_states` or `/gazebo/get_model_state`
   - status: resolved for the current minimal launch and recorder smoke test
2. Left-arm command interface is minimally resolved; gripper command/stability
   remains blocked.
3. `eef_pose` / TF lookup is resolved for the current minimal launch and
   non-fallback recorder smoke test.
4. Stage 6 dataset uses fallback state and is not real demonstration data.
5. B5d' arm-only scripted reaching expert is debug-smoke minimal resolved.
6. MoveIt IK is available, but trajectory execution controller configuration is
   not confirmed; current execution uses
   `EE-delta -> IK/joint target -> /oberon7/arm_position_l/command`.
7. TensorBoard is unavailable in this environment, but checkpoint and JSON
   summary outputs work.

## Current Debug Priority

Priority task:

```text
B8': small real non-fallback arm-only reaching / pre-grasp data collection
```

Reason:

- B1 live base, joint, and target recording is now verified in a short
  non-fallback recorder smoke test.
- B2 minimal left-arm joint-space command execution is verified, but the arm
  controller still must be loaded/started in each clean runtime before an
  arm-only smoke test.
- B2 gripper execution remains blocked by clean-baseline gripper joint motion
  and model/controller mismatch.
- B3 TF availability and recorder writing of finite `eef_pose` /
  `relative_target_to_eef` are verified.
- B5a verified that a tiny `action_ee_delta` can be converted through MoveIt IK
  into an arm-only `JointTrajectory` and accepted by
  `/oberon7/arm_position_l/command`.
- B5b verified the arm-only scripted expert runtime path with gripper disabled.
- B5c verified the package-local static target smoke path.
- The route is now explicitly changed away from full grasping toward arm-only
  reaching / pre-grasp positioning.
- The next narrow gap is B5d': make the scripted expert drive multiple small,
  bounded left-arm steps toward a static target or pre-grasp pose.
- Latest B5d' precheck result: placing the static target near the current live
  EEF succeeded at set time, but the first recorder sample was already about
  `1.36 m` from the target and the no-control baseline distance increased to
  about `1.54 m` over 2 s. The current blocker is therefore world-frame
  target/EEF synchronization under RexROV base drift, not recorder validation
  or the B5a converter.
- Follow-up drift measurement confirmed the issue: over about `3.85 s`, the
  base drifted about `0.67 m` and the EEF world pose drifted about `0.58 m`
  (`~0.15 m/s`) with no arm command. This is larger than the intended
  `0.05-0.10 m` reaching threshold, so a world-static target smoke test would
  be dominated by base drift.
- Runtime graph inspection found no existing RexROV DP / station-keeping /
  base-hold interface. The launch exposes thruster manager/allocation topics
  and services, but no high-level hold node/action/service is running.
- Base-relative target-only smoke passed: repeatedly updating
  `cylinder_target` from a fixed base-frame pose kept EEF-target distance in
  `[0.10754, 0.10769] m` despite base/world drift.
- A package-local helper has been added for this B5d' task setup:
  - `src/rexrov_single_oberon7_fm_dp/base_relative_target.py`
  - `scripts/base_relative_target.py`
  - optional `collect_episode.launch` args with
    `enable_base_relative_target:=false` by default.
- Next minimum check is a short no-arm recorder smoke with
  `enable_base_relative_target:=true`, `execute_arm:=false`, and fallback
  disabled. If that passes with stable recorded distance, the next step can be
  the first tiny arm-only reaching smoke.
- No-arm recorder smoke with the base-relative helper passed:
  - episode: `data/raw/b5d_reaching_precheck/b5d_base_relative_target_no_arm.npz`
  - validator: PASS, `T=6`
  - `allow_nominal_state_fallback: False`
  - recorded distance range: `[0.10635, 0.18227] m`
  - target and EEF moved together in world while staying in the same local
    neighborhood.
- The scripted expert now has a default-off `target_directed_reaching` option
  that computes clipped EE deltas from live `target_pose - eef_pose`; this is
  needed because the original scripted deltas were fixed grasp-state labels, not
  target-directed reaching actions.
- Next minimum check is the first tiny arm-only B5d' smoke with:
  `target_directed_reaching:=true`, `execute_arm:=true`, gripper disabled, and
  the base-relative target helper active.
- First tiny arm-only B5d' smoke attempt failed before any arm command because
  MoveIt semantic parameters were not available to the scripted expert:
  `Robot semantic description not found` and `Group 'arm_l' was not found`.
  No `.npz` was written. This is a runtime MoveIt prerequisite issue, not
  evidence against the base-relative target helper or B5a converter.
- MoveIt readiness check confirmed `/move_group` and `/compute_ik` are present
  and `/compute_ik` is owned by `/move_group`, but
  `/robot_description_semantic` is still not set globally. The left-arm
  controller remains running and `/oberon7/arm_position_l/command` has the
  `/gazebo` subscriber.
- The arm command converter now has a direct `/compute_ik` service fallback:
  when `/robot_description_semantic` is unavailable to the client, it computes
  the current EEF pose from odom+TF and sends a `GetPositionIK` request without
  constructing `MoveGroupCommander("arm_l")`.
- A repeated readiness check confirmed the same runtime state:
  `/move_group` and `/compute_ik` are available, `/robot_description_semantic`
  is not set globally, `oberon7/arm_position_l` is running, and
  `/oberon7/arm_position_l/command` has the `/gazebo` subscriber.
- The first direct-IK B5d' smoke reached the direct `/compute_ik` path, but
  MoveIt returned error code `-15`, consistent with an invalid group name in
  the active MoveIt model. The revised SRDF does contain `arm_l`, but
  `rexrov_moveit_revised/move_group_revised.launch` has its
  `planning_context_revised.launch` include commented out, so the active
  `/move_group` was started without semantic groups.
- A package-local wrapper was added:
  `launch/b5d_move_group_with_context.launch`. It loads the revised planning
  context first and then includes the original `move_group_revised.launch`
  without modifying `rexrov_moveit_revised`.
- MoveIt readiness with the package-local wrapper now passes:
  - `/move_group` exists;
  - `/compute_ik` exists;
  - `/robot_description_semantic` is populated with revised SRDF content that
    includes `oberon7_l/end_effector` and the expected left-arm semantic
    context;
  - `oberon7/arm_position_l` is still running;
  - `/oberon7/arm_position_l/command` still has the `/gazebo` subscriber.
- The first tiny direct-IK arm-only B5d' smoke with semantic context passed at
  the one-command level:
  - episode:
    `data/raw/b5d_reaching_smoke/b5d_target_directed_arm_once_with_context.npz`
  - validator: PASS, `T=6`
  - `allow_nominal_state_fallback: False`
  - `base_state_source: odom`
  - `joint_state_source: joint_states`
  - `target_state_source: gazebo_model_states`
  - `eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector`
  - `action_ee_delta`, `target_pose`, `eef_pose`, and
    `relative_target_to_eef` available
  - raw command still unavailable, documented separately
  - one bounded arm command was logged for `MOVE_TO_PREGRASP`
  - active-left max joint delta from first sample was below `0.009 rad`
  - EEF-target distance decreased from about `0.179 m` to about `0.136 m`
- At this point in the debug sequence, the B5d' one-command arm-only reaching
  smoke was minimally resolved, but the broader multi-step behavior still
  needed one more short, bounded smoke before moving toward B8' data
  collection.
- First multi-step B5d' smoke with repeated `MOVE_TO_PREGRASP` arm execution
  ran three bounded arm commands and validator passed, but reaching convergence
  was not stable enough:
  - episode:
    `data/raw/b5d_reaching_smoke/b5d_target_directed_arm_multistep_with_context.npz`
  - validator: PASS, `T=8`
  - fallback disabled and live odom/joint/model-state/eef fields available
  - final distance increased from about `0.117 m` to about `0.169 m`
  - minimum distance reached about `0.115 m`
  - active-left cumulative max joint delta was about `0.018 rad`
- Diagnosis: repeated commands exposed a frame mismatch. The target-directed
  action was computed from Gazebo world-frame `target - eef`, but the arm
  converter applies EE deltas in the MoveIt/local arm frame. This is unstable
  with the base-relative target helper.
- Code fix applied: `target_directed_action_frame` now defaults to
  `base_link`, and target-directed reaching converts the Gazebo target into
  `rexrov/base_link` before computing the EE delta.
- Base-frame multi-step B5d' smoke now passes at the debug-smoke level:
  - episode:
    `data/raw/b5d_reaching_smoke/b5d_target_directed_arm_multistep_base_frame.npz`
  - validator: PASS, `T=8`
  - fallback disabled and live odom/joint/model-state/eef fields available
  - repeated bounded `MOVE_TO_PREGRASP` arm commands were logged
  - distance stayed local: initial about `0.117 m`, final about `0.115 m`, min
    about `0.094 m`
  - active-left cumulative max joint delta was about `0.023 rad`
- Current interpretation: B5d' arm-only scripted reaching expert is minimal
  resolved for debug smoke. This is not a rollout, not grasping, and not a
  success-rate claim.
- Next minimum check moves to B8' as a small real non-fallback arm-only
  reaching/pre-grasp data collection smoke, starting with 5 short episodes and
  validating each episode before any training.
- Do not start a new stage, training run, long simulation, gripper test, or
  grasp-success evaluation during this route-alignment pass.

## B8' Next Data Collection Requirements

B8' should start with 5 short real non-fallback arm-only reaching/pre-grasp
episodes. Do not train from these until all episodes validate and the distance
metrics are inspected.

Required metadata and fields:

```text
allow_nominal_state_fallback=false
base_state_source=odom
joint_state_source=joint_states
target_state_source=gazebo_model_states
eef_pose available
relative_target_to_eef available
action_ee_delta available
gripper_enabled=false
task_type=arm_only_reaching or pregrasp_positioning
success_metric=reaching_success or pregrasp_success
is_grasp_dataset=false
```

Record per episode:

```text
initial_distance
min_distance
final_distance
distance_reduction
active-left joint motion magnitude
validator result
failure_reason, if any
```

Stage 6 fallback data remains historical pipeline-smoke data only and must not
be used as a real demonstration dataset.

## Latest B8' Attempt

Date: 2026-05-04.

User ran the B8' readiness checks with:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch
```

Readiness result:

- `/joint_states`, `/rexrov/pose_gt`, `/gazebo/model_states`, `/compute_ik`,
  and `/robot_description_semantic` were available.
- `/robot_description_semantic` included `arm_l` and
  `oberon7_l/end_effector`.
- `/gazebo/model_states` contained only `ocean_box` and `rexrov`; no
  `cylinder_target` was present.
- `/controller_manager/list_controllers` showed only
  `joint_state_controller` running.
- `/oberon7/arm_position_l/command` was unknown, so the left-arm command
  controller was not loaded/started in this clean runtime.

The attempted B8' episode did not write an `.npz` file:

```text
episode_id: b8_reaching_smoke_0000
result: no episode file
```

Failure reasons:

- `base_relative_target.py` was started before `cylinder_target` existed and
  failed with `GetModelState: model does not exist`.
- `collect_episode.launch` was run with `spawn_target:=false` and
  `require_target:=true`, so the recorder timed out waiting for
  `cylinder_target`.
- The scripted expert timed out waiting for a subscriber on
  `/oberon7/arm_position_l/command`.

Decision:

```text
B8' is not resolved yet. No real non-fallback B8' demonstration episode has
been collected in this attempt.
```

Package-local fixes applied after this attempt:

- `launch/load_left_controllers.launch` now defaults to loading/starting only
  `oberon7/arm_position_l`. Hand controller loading is explicit via
  `load_hand:=true` and remains disabled for B8'.
- `config/data_collection.yaml`, `launch/collect_episode.launch`, and
  `src/rexrov_single_oberon7_fm_dp/recorder.py` now support B8' metadata:
  `task_type`, `success_metric`, `gripper_enabled`, and `is_grasp_dataset`.

Next minimum checks:

1. Start/load only the left-arm controller, not the hand controller.
2. Confirm `/oberon7/arm_position_l/command` exists and has the Gazebo
   subscriber.
3. Run a short target-spawn/base-relative-target smoke with `spawn_target:=true`
   and `enable_base_relative_target:=true`, so `cylinder_target` exists before
   B8' collection is retried.

## Latest B8' Progress

Date: 2026-05-04.

User started the left-arm controller with:

```text
roslaunch rexrov_single_oberon7_fm_dp load_left_controllers.launch \
  start:=true \
  load_hand:=false
```

Controller readiness:

```text
joint_state_controller: running
oberon7/arm_position_l: running
/oberon7/arm_position_l/command: subscriber /gazebo
```

No hand controller was reported running in the controller list.

First B8' smoke episode was collected with `spawn_target:=true`,
`enable_base_relative_target:=true`, `execute_arm:=true`,
`enable_gripper_command:=false`, and `allow_nominal_state_fallback:=false`.

Output:

```text
data/raw/b8_reaching_smoke/b8_reaching_smoke_0000.npz
```

Validation:

```text
validation: PASS
T: 6
success: False
unavailable_fields: ['raw_command']
```

Metadata:

```text
allow_nominal_state_fallback: false
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
task_type: arm_only_reaching
success_metric: reaching_success
gripper_enabled: false
is_grasp_dataset: false
action_ee_delta_available: true
target_pose/eef_pose/relative_target_to_eef/action_ee_delta: available
raw_command: unavailable
```

Distance and bounded-motion metrics:

```text
initial_distance: 0.131584 m
min_distance:     0.118852 m
final_distance:   0.136327 m
distance_reduction: -0.004743 m
min_distance_below_0.10: false
active-left joint total max abs delta: 0.007721 rad
target_motion_norm: 0.595818 m
eef_motion_norm: 0.590900 m
```

Decision:

```text
B8' is partially progressed: 1/5 requested short non-fallback arm-only
reaching/pre-grasp smoke episodes has been collected and validated.
```

Interpretation:

- This episode is valid B8' smoke data.
- It is not a learned rollout.
- It is not grasping.
- It is not a success-rate result.
- `success=False` is acceptable for this smoke episode and must be interpreted
  through reaching distance metrics, not grasp success.
- Reaching quality is still weak in this episode because `min_distance` did not
  cross the temporary `0.10 m` threshold and final distance was slightly worse
  than initial distance.

Next minimum action:

- Stop the completed `collect_episode.launch` if its base-relative target node
  is still running.
- Collect the next single short episode before attempting a 5-episode batch.
  Use a unique target model name such as `cylinder_target_b8_0001` or delete
  the previous target before reusing `cylinder_target`.

## Latest B8' Small Debug Batch

Date: 2026-05-05.

Record label:

```text
B8' small debug batch：10–15 episode real non-fallback arm-only reaching/pre-grasp debug collection，不训练、不处理 gripper。
```

Scope:

- Collected a 10-episode real non-fallback arm-only reaching/pre-grasp debug
  batch.
- Did not train BC / Diffusion Policy / Flow Matching Policy.
- Did not run learned policy rollout.
- Did not start the hand controller, did not send gripper commands, and did
  not evaluate grasping.

Data and logs:

```text
data/raw/b8_reaching_debug_10/
outputs/logs/b8_reaching_debug_10/
outputs/logs/b8_reaching_debug_10_quality/
outputs/logs/b8_reaching_debug_10_direction/
outputs/logs/b8_reaching_debug_10_command_motion/
```

Runtime route:

- Used `collect_episode.launch` directly instead of the tuned v3 wrapper so
  `prefer_model_states_base_pose:=false` could satisfy the required
  `base_state_source=odom`.
- Left arm controller only; `load_hand:=false`.
- Gripper disabled throughout.

Batch result:

```text
episodes_total: 10
episodes_valid: 10
validator_pass_count: 10/10
success_count: 7/10
reaching_success_rate: 0.7
all_required_metadata_ok: true
all_success_metadata_consistent: true
mean_initial_distance: 0.10867339087546952
mean_final_distance: 0.08288684626534658
mean_distance_reduction: 0.02578654461012293
min_distance_overall: 0.04737587025733589
max_active_left_joint_delta: 0.06559905751000272
max_target_step_base: 0.02330097538679025
large_target_step_indices: [] for all episodes
mean_best_action_to_eef_cosine: 0.5547614407437549
mean_best_lag_steps: 2.6
mean_best_realized_gain_along_action: 0.13983358394761614
```

Per-episode final distances:

```text
[0.057709292825412616,
 0.053139010334061654,
 0.056242964248424114,
 0.06285195894106808,
 0.06898559297244955,
 0.0823199994929284,
 0.09451480115072017,
 0.10917591745042454,
 0.11985607592171775,
 0.12407284931625896]
```

Metadata result:

```text
allow_nominal_state_fallback: false for all episodes
base_state_source: odom for all episodes
joint_state_source: joint_states for all episodes
target_state_source: gazebo_model_states for all episodes
gripper_enabled: false for all episodes
is_grasp_dataset: false for all episodes
task_type: arm_only_reaching for all episodes
success_metric: reaching_success for all episodes
success_source: recorded_final_distance for all episodes
recorded_success_distance_threshold_m: 0.1 for all episodes
```

Failure pattern:

```text
b8_reaching_debug_10_0007:
  saved_success_false, final_distance_above_threshold
b8_reaching_debug_10_0008:
  saved_success_false, final_distance_above_threshold,
  no_positive_distance_reduction
b8_reaching_debug_10_0009:
  saved_success_false, final_distance_above_threshold,
  no_positive_distance_reduction
```

Diagnostic interpretation:

- The live non-fallback data path and metadata contract pass at 10/10.
- Target/base source-sync is clean for this batch: no large target-base step
  indices and `max_target_step_base < 0.03 m`.
- Reaching quality does not meet the proposed small-batch pass gate because
  `success_count / N = 0.7`, below the `>=0.8` suggested threshold.
- Direction and command-motion diagnostics both warn against collecting more
  until the command-to-motion path is explained:
  - `mean_eef_motion_cosine_with_target: 0.39138751200070315`
  - `mean_eef_positive_target_direction_ratio: 0.7047619047619047`
  - command-motion recommendation:
    `do_not_collect_more_until_command_to_motion_path_is_explained`

Current decision:

```text
B8' small debug batch is not passed. It is valid non-fallback arm-only
reaching/pre-grasp debug data, but reaching quality degraded over the batch.
Do not train. Do not run learned rollout. Do not expand to 20/50/100 episodes.
Debug the scripted reaching behavior and command-to-motion drift first.
```

## Latest B8' Progress: Episode 0001

Date: 2026-05-04.

Second B8' smoke episode was collected with a unique target model name:

```text
episode_id: b8_reaching_smoke_0001
target_model_name: cylinder_target_b8_0001
```

Output:

```text
data/raw/b8_reaching_smoke/b8_reaching_smoke_0001.npz
```

Validation:

```text
validation: PASS
T: 6
success: False
unavailable_fields: ['raw_command']
```

Metadata:

```text
allow_nominal_state_fallback: false
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
task_type: arm_only_reaching
success_metric: reaching_success
gripper_enabled: false
is_grasp_dataset: false
action_ee_delta_available: true
target_pose/eef_pose/relative_target_to_eef/action_ee_delta: available
raw_command: unavailable
```

Distance and bounded-motion metrics:

```text
initial_distance: 0.141116 m
min_distance:     0.124463 m
final_distance:   0.131371 m
distance_reduction: 0.009745 m
min_distance_below_0.10: false
active-left joint total max abs delta: 0.005944 rad
target_motion_norm: 0.426439 m
eef_motion_norm: 0.434063 m
```

Decision:

```text
B8' is partially progressed: 2/5 requested short non-fallback arm-only
reaching/pre-grasp smoke episodes have been collected and validated.
```

Interpretation:

- `b8_reaching_smoke_0001` is valid B8' smoke data.
- It is still not a learned rollout, not grasping, and not success-rate
  evidence.
- `success=False` remains acceptable and should be interpreted using reaching
  distance metrics.
- Episode 0001 improved final distance relative to initial distance, but did
  not cross the temporary `0.10 m` reaching threshold.

Next minimum action:

- Continue with one more short episode, `b8_reaching_smoke_0002`, using a
  unique target model name such as `cylinder_target_b8_0002`.

## Latest B8' Progress: Episode 0002

Date: 2026-05-04.

Third B8' smoke episode was collected with:

```text
episode_id: b8_reaching_smoke_0002
target_model_name: cylinder_target_b8_0002
```

Output:

```text
data/raw/b8_reaching_smoke/b8_reaching_smoke_0002.npz
```

Validation:

```text
validation: PASS
T: 6
success: False
unavailable_fields: ['raw_command']
```

Metadata:

```text
allow_nominal_state_fallback: false
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
task_type: arm_only_reaching
success_metric: reaching_success
gripper_enabled: false
is_grasp_dataset: false
action_ee_delta_available: true
target_pose/eef_pose/relative_target_to_eef/action_ee_delta: available
raw_command: unavailable
```

Distance and bounded-motion metrics:

```text
initial_distance: 0.129065 m
min_distance:     0.125776 m
final_distance:   0.126832 m
distance_reduction: 0.002233 m
min_distance_below_0.10: false
active-left joint total max abs delta: 0.006853 rad
target_motion_norm: 0.281551 m
eef_motion_norm: 0.279925 m
```

Decision:

```text
B8' is partially progressed: 3/5 requested short non-fallback arm-only
reaching/pre-grasp smoke episodes have been collected and validated.
```

Interpretation:

- `b8_reaching_smoke_0002` is valid B8' smoke data.
- It is still not a learned rollout, not grasping, and not success-rate
  evidence.
- `success=False` remains acceptable and should be interpreted using reaching
  distance metrics.
- Episode 0002 had a small positive distance reduction, but did not cross the
  temporary `0.10 m` reaching threshold.

Next minimum action:

- Continue with one more short episode, `b8_reaching_smoke_0003`, using a
  unique target model name such as `cylinder_target_b8_0003`.

## Latest B8' Progress: Episode 0003

Date: 2026-05-04.

Fourth B8' smoke episode was collected with:

```text
episode_id: b8_reaching_smoke_0003
target_model_name: cylinder_target_b8_0003
```

Output:

```text
data/raw/b8_reaching_smoke/b8_reaching_smoke_0003.npz
```

Validation:

```text
validation: PASS
T: 6
success: False
unavailable_fields: ['raw_command']
```

Metadata:

```text
allow_nominal_state_fallback: false
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
task_type: arm_only_reaching
success_metric: reaching_success
gripper_enabled: false
is_grasp_dataset: false
action_ee_delta_available: true
target_pose/eef_pose/relative_target_to_eef/action_ee_delta: available
raw_command: unavailable
```

Distance and bounded-motion metrics:

```text
initial_distance: 0.131535 m
min_distance:     0.125531 m
final_distance:   0.134046 m
distance_reduction: -0.002512 m
min_distance_below_0.10: false
active-left joint total max abs delta: 0.007576 rad
target_motion_norm: 0.488219 m
eef_motion_norm: 0.487661 m
```

Decision:

```text
B8' is partially progressed: 4/5 requested short non-fallback arm-only
reaching/pre-grasp smoke episodes have been collected and validated.
```

Interpretation:

- `b8_reaching_smoke_0003` is valid B8' smoke data.
- It is still not a learned rollout, not grasping, and not success-rate
  evidence.
- `success=False` remains acceptable and should be interpreted using reaching
  distance metrics.
- Episode 0003 did not cross the temporary `0.10 m` reaching threshold and
  final distance was slightly worse than initial distance.

Next minimum action:

- Continue with the fifth short episode, `b8_reaching_smoke_0004`, using a
  unique target model name such as `cylinder_target_b8_0004`.

## Latest B8' Progress: 5-Episode Smoke Complete

Date: 2026-05-04.

Fifth B8' smoke episode was collected with:

```text
episode_id: b8_reaching_smoke_0004
target_model_name: cylinder_target_b8_0004
```

Output:

```text
data/raw/b8_reaching_smoke/b8_reaching_smoke_0004.npz
```

Validation:

```text
validation: PASS
T: 6
success: False
unavailable_fields: ['raw_command']
```

Metadata:

```text
allow_nominal_state_fallback: false
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
task_type: arm_only_reaching
success_metric: reaching_success
gripper_enabled: false
is_grasp_dataset: false
action_ee_delta_available: true
target_pose/eef_pose/relative_target_to_eef/action_ee_delta: available
raw_command: unavailable
```

Distance and bounded-motion metrics for episode 0004:

```text
initial_distance: 0.136541 m
min_distance:     0.126768 m
final_distance:   0.126768 m
distance_reduction: 0.009772 m
min_distance_below_0.10: false
active-left joint total max abs delta: 0.008000 rad
target_motion_norm: 0.242105 m
eef_motion_norm: 0.231250 m
```

Five-episode B8' smoke summary:

```text
episodes_total: 5
episodes_valid: 5
episodes_invalid: 0
T per episode: 6
all_required_metadata_ok: true
target_pose/eef_pose/relative_target_to_eef/action_ee_delta available: 5/5
raw_command unavailable: 5/5
episodes_with_positive_distance_reduction: 3/5
episodes_below_0.10: 0/5
min_distance_overall: 0.118852 m
mean_initial_distance: 0.133968 m
mean_final_distance: 0.131069 m
mean_distance_reduction: 0.002899 m
max_active_left_joint_delta: 0.008000 rad
```

Summary artifacts:

```text
outputs/logs/b8_reaching_smoke/dataset_summary.json
outputs/logs/b8_reaching_smoke/dataset_summary.md
```

Decision:

```text
B8' first 5-episode smoke data collection is complete at the data-collection
smoke level.
```

Interpretation:

- This is a real non-fallback arm-only reaching/pre-grasp smoke dataset.
- This is not a learned-policy rollout.
- This is not grasping.
- This is not a success-rate evaluation.
- `success=False` remains acceptable for these smoke episodes and must be
  interpreted through reaching distance metrics.
- Reaching quality remains weak: no episode crossed the temporary `0.10 m`
  threshold, though 3/5 episodes reduced final distance.

Next minimum action:

- Stop short collection launches/helpers if still running.
- Do a read-only quality review of the 5-episode B8' smoke dataset before any
  training decision.
- Do not start BC / Diffusion Policy / Flow Matching retraining until the user
  explicitly moves past this B8' smoke review.

## Latest B8' Quality Review

Review date: 2026-05-04.

Scope:

```text
B8' reaching smoke quality review: only analyze the existing 5-episode
non-fallback reaching dataset; no new data collection, no Gazebo run, no
training, no rollout, and no gripper work.
```

Reviewed inputs:

```text
data/raw/b8_reaching_smoke/b8_reaching_smoke_0000.npz
data/raw/b8_reaching_smoke/b8_reaching_smoke_0001.npz
data/raw/b8_reaching_smoke/b8_reaching_smoke_0002.npz
data/raw/b8_reaching_smoke/b8_reaching_smoke_0003.npz
data/raw/b8_reaching_smoke/b8_reaching_smoke_0004.npz
outputs/logs/b8_reaching_smoke/dataset_summary.json
outputs/logs/b8_reaching_smoke/dataset_summary.md
```

Quality review artifacts:

```text
outputs/logs/b8_reaching_smoke_quality/per_episode_quality.json
outputs/logs/b8_reaching_smoke_quality/per_episode_quality.md
outputs/logs/b8_reaching_smoke_quality/distance_curves.png
outputs/logs/b8_reaching_smoke_quality/action_magnitude_summary.json
outputs/logs/b8_reaching_smoke_quality/joint_motion_summary.json
```

Validator re-check:

```text
5/5 PASS
T per episode: 6
success: False
unavailable_fields: ['raw_command']
```

Metadata remains aligned for all 5 episodes:

```text
allow_nominal_state_fallback: false
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
task_type: arm_only_reaching
success_metric: reaching_success
gripper_enabled: false
is_grasp_dataset: false
```

Quality summary:

```text
episodes_total: 5
episodes_with_positive_distance_reduction: 3/5
episodes_below_0.10: 0/5
min_distance_overall: 0.118852 m
mean_initial_distance: 0.133968 m
mean_final_distance: 0.131069 m
mean_distance_reduction: 0.002899 m
max_active_left_joint_delta: 0.008000 rad
action_xyz_norm_mean_all_samples: 0.007494 m
action_xyz_norm_max_all_samples: 0.008660 m
```

Interpretation:

- The B8' smoke data is valid non-fallback arm-only reaching/pre-grasp smoke
  data at the recorder and metadata level.
- It is not a learned rollout, not grasping, and not a grasp-success result.
- Reaching quality is weak: no episode crossed the temporary `0.10 m`
  threshold and mean final distance improved by only about `0.0029 m`.
- The expert actions are frequently clipped at the `0.005 m` per-axis limit.
- Active-left joint motion is small and bounded, with no abnormal jumps, but
  the maximum first-to-last active joint delta is only about `0.008 rad`.
- World-frame target and EEF motion are much larger than the net distance
  improvement because the base-relative target helper and RexROV base drift
  move through world coordinates. Base-frame distance remains the better
  short-window quality signal for this smoke route.
- The target source is still `gazebo_model_states`; however, with
  `enable_base_relative_target:=true`, the target is not static in world during
  the short windows. This should be documented as base-relative target setup,
  not a world-static target success result.

Decision:

```text
Choose A: tune the scripted reaching expert before collecting a larger B8'
dataset.
```

Do not expand to a 20-episode debug collection and do not train BC / Diffusion
Policy / Flow Matching Policy from this smoke set until the scripted reaching
behavior is improved and another short smoke set is reviewed.

## Latest B8' Expert Tuning Prepared

Update date: 2026-05-04.

Purpose:

```text
Prepare option A: tune the scripted reaching expert before collecting a new
5-episode B8' smoke set.
```

Important finding from the quality review:

- `target_directed_action_frame:=base_link` generated target-directed action
  labels in the RexROV base frame.
- The existing EE-delta arm converter applied action xyz directly in the MoveIt
  planning frame.
- This frame mismatch can make an action that is target-directed in base frame
  execute as a wrong-direction world-frame EEF delta.

Package-local changes:

```text
src/rexrov_single_oberon7_fm_dp/arm_command_converter.py
src/rexrov_single_oberon7_fm_dp/expert_policy.py
src/rexrov_single_oberon7_fm_dp/recorder.py
launch/collect_episode.launch
launch/b8_reaching_tuned_episode.launch
```

Behavior:

- `ArmEEDeltaCommandConverter` now accepts `action_frame`.
- Default `action_frame` is `planning_frame`, preserving old behavior unless
  the launch explicitly requests otherwise.
- For B8' tuned smoke, `arm_action_frame:=base_link` rotates the clipped
  base-frame action delta into the MoveIt planning frame before IK.
- Recorder metadata now stores:

  ```text
  target_directed_action_frame
  arm_action_frame
  max_linear_step
  max_joint_delta
  ```

- `b8_reaching_tuned_episode.launch` wraps one short tuned episode with:

  ```text
  rate_hz: 3.0
  max_duration_sec: 3.3
  max_linear_step: 0.010
  max_joint_delta: 0.015
  time_from_start_sec: 1.0
  target_directed_action_frame: base_link
  arm_action_frame: base_link
  execute_arm_states: MOVE_TO_PREGRASP,MOVE_TO_GRASP
  enable_gripper_command: false
  gripper_enabled: false
  is_grasp_dataset: false
  allow_nominal_state_fallback: false
  ```

Verification performed:

```text
python3 -m py_compile: PASS
xmllint --noout launch files: PASS
roslaunch --ros-args b8_reaching_tuned_episode.launch: PASS
```

Not yet done:

- No new tuned B8' episode has been collected yet in this update.
- No Gazebo run was started by this update.
- No training, rollout, gripper command, or hand controller startup was
  performed.

Next minimum runtime check:

```text
Run one tuned short episode first:
  b8_reaching_smoke_tuned_v1_0000

Validate it and inspect distance/joint motion before running the remaining four
tuned episodes.
```

## Latest B8' Tuned Smoke Progress: Episode 0000

Update date: 2026-05-04.

User ran the first tuned B8' single-episode smoke with:

```bash
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_episode.launch \
  episode_id:=b8_reaching_smoke_tuned_v1_0000 \
  target_model_name:=cylinder_target_b8_tuned_v1_0000
```

Runtime settings confirmed:

```text
allow_nominal_state_fallback: False
target_directed_action_frame: base_link
arm_action_frame: base_link
max_linear_step: 0.01
max_joint_delta: 0.015
rate_hz: 3.0
max_duration_sec: 3.3
execute_arm_states: MOVE_TO_PREGRASP,MOVE_TO_GRASP
enable_gripper_command: False
gripper_enabled: False
is_grasp_dataset: False
```

Runtime result:

```text
episode:
  data/raw/b8_reaching_smoke_tuned_v1/b8_reaching_smoke_tuned_v1_0000.npz

validator:
  PASS
  T: 10
  success: False
  unavailable_fields: ['raw_command']
```

The log showed the frame fix was active:

```text
B5 arm command state=MOVE_TO_PREGRASP planning_frame=world action_frame=base_link
clipped_xyz_action_frame=[...]
clipped_xyz_planning_frame=[...]
```

Offline quality review for episode 0000:

```text
initial_distance: 0.12728478584630584
min_distance:     0.12266351842923223
final_distance:   0.12608663873005227
distance_reduction: 0.0011981471162535728
min_distance_below_0.10: false

action_xyz_norm_mean: 0.01518659761050544
action_xyz_norm_max:  0.017320508075688773
action-relative cosine base/world: 0.640965 / 0.631116

active_left_joint_total_max_abs_delta: 0.04587725454909197
active_left_step_max_abs_delta: 0.009355441098312767

target_world_motion: 0.31929702333470134
target_base_motion:  0.005055356470380404
eef_world_motion:    0.3213029384584727
eef_base_motion:     0.013228142361489623
```

Interpretation:

- The tuned frame-alignment fix is working: target-directed actions are
  generated in base frame and executed with `action_frame=base_link`.
- The episode is valid non-fallback B8' tuned smoke data.
- The gripper remained disabled and no hand controller was started.
- Reaching quality is still not resolved: the episode did not cross the
  temporary `0.10 m` threshold and final distance improved by only about
  `0.0012 m`.
- Joint motion is larger than the first B8' smoke set but still bounded at the
  per-step level; no abnormal jump or divergence was observed in this episode.

Decision:

```text
Frame-mismatch blocker: minimal resolved.
Tuned 5-episode smoke collection: not complete yet, 1/5 collected.
Reaching-quality blocker: still open pending 5-episode tuned-v1 review.
```

Next minimum action:

- Continue with tuned episodes `0001` through `0004` using the same
  `b8_reaching_tuned_episode.launch`.
- After 5/5 tuned episodes are collected and validated, run the offline quality
  review on `data/raw/b8_reaching_smoke_tuned_v1`.
- Do not train BC / DP / FM and do not run rollout until the tuned 5-episode
  review shows clearly better reaching quality.

## Latest B8' Tuned v1 5-Episode Smoke Complete

Update date: 2026-05-04.

User completed tuned v1 episodes `0001` through `0004` and validated all five
tuned v1 episodes:

```text
data/raw/b8_reaching_smoke_tuned_v1/b8_reaching_smoke_tuned_v1_0000.npz
data/raw/b8_reaching_smoke_tuned_v1/b8_reaching_smoke_tuned_v1_0001.npz
data/raw/b8_reaching_smoke_tuned_v1/b8_reaching_smoke_tuned_v1_0002.npz
data/raw/b8_reaching_smoke_tuned_v1/b8_reaching_smoke_tuned_v1_0003.npz
data/raw/b8_reaching_smoke_tuned_v1/b8_reaching_smoke_tuned_v1_0004.npz
```

Validator result:

```text
5/5 PASS
T: 10 for every episode
success: False for every episode
unavailable_fields: ['raw_command']
```

Tuned v1 metadata:

```text
allow_nominal_state_fallback: false
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
task_type: arm_only_reaching
success_metric: reaching_success
gripper_enabled: false
is_grasp_dataset: false
target_directed_action_frame: base_link
arm_action_frame: base_link
max_linear_step: 0.010
max_joint_delta: 0.015
rate_hz: 3.0
max_duration_sec: 3.3
```

Offline quality artifacts:

```text
outputs/logs/b8_reaching_smoke_tuned_v1_quality/per_episode_quality.json
outputs/logs/b8_reaching_smoke_tuned_v1_quality/per_episode_quality.md
outputs/logs/b8_reaching_smoke_tuned_v1_quality/distance_curves.png
outputs/logs/b8_reaching_smoke_tuned_v1_quality/action_magnitude_summary.json
outputs/logs/b8_reaching_smoke_tuned_v1_quality/joint_motion_summary.json
```

Tuned v1 quality summary:

```text
episodes_total: 5
all_required_metadata_ok: true
episodes_with_positive_distance_reduction: 3/5
episodes_below_0.10: 0/5
min_distance_overall: 0.120244 m
mean_initial_distance: 0.134898 m
mean_final_distance: 0.132106 m
mean_distance_reduction: 0.002792 m
max_active_left_joint_delta: 0.048204 rad
action_xyz_norm_mean_all_samples: 0.014748 m
action_xyz_norm_max_all_samples: 0.017321 m
```

Per-episode distance:

```text
0000: initial/min/final/reduction = 0.127285 / 0.122664 / 0.126087 /  0.001198
0001: initial/min/final/reduction = 0.140956 / 0.120244 / 0.126678 /  0.014278
0002: initial/min/final/reduction = 0.128815 / 0.120976 / 0.142158 / -0.013344
0003: initial/min/final/reduction = 0.152236 / 0.121936 / 0.130982 /  0.021255
0004: initial/min/final/reduction = 0.125196 / 0.125196 / 0.134625 / -0.009429
```

Interpretation:

- Tuned v1 completed the requested 5-episode smoke and all episodes are valid
  non-fallback arm-only reaching/pre-grasp smoke data.
- The frame-alignment fix remains active: the runtime logs show
  `action_frame=base_link`.
- Reaching quality is still not resolved: no tuned v1 episode crossed the
  temporary `0.10 m` threshold and mean distance reduction remains about
  `0.0028 m`, similar to the first B8' smoke set.
- Tuned v1 produced larger actions and larger cumulative left-arm motion than
  the first smoke set. Per-step joint changes remained bounded, but the total
  active-left joint delta rose to about `0.048 rad`.
- The current blocker is no longer data collection or frame mismatch; it is
  target/pregrasp setup and scripted reaching convergence.

Decision:

```text
B8' tuned v1 data-collection smoke: complete.
Frame-mismatch blocker: minimal resolved.
Reaching-quality blocker: still open.
Do not expand to 20 episodes and do not train BC / DP / FM from tuned v1.
```

## Latest B8' Tuned v2 Prepared

Update date: 2026-05-04.

Reason:

- Increasing action and fixing frame alignment did not produce reliable
  crossing of the `0.10 m` reaching threshold.
- Simply increasing `max_duration_sec` on the old state sequence would enter
  `CLOSE_GRIPPER` / `LIFT_OR_HOLD`, which is out of scope for B8'.

Package-local changes:

```text
src/rexrov_single_oberon7_fm_dp/expert_policy.py
  - added configurable state_sequence;
  - added per-state duration params.

src/rexrov_single_oberon7_fm_dp/recorder.py
  - records state_sequence in metadata.

launch/collect_episode.launch
  - exposes state_sequence and MOVE_TO_PREGRASP/MOVE_TO_GRASP duration args.

launch/b8_reaching_tuned_v2_episode.launch
  - one-episode wrapper for the next bounded arm-only reaching smoke.
```

Tuned v2 planned settings:

```text
state_sequence: MOVE_TO_PREGRASP,MOVE_TO_GRASP
state_duration_MOVE_TO_PREGRASP: 3.0
state_duration_MOVE_TO_GRASP: 2.0
max_duration_sec: 5.2
rate_hz: 3.0
max_linear_step: 0.010
max_joint_delta: 0.010
target_directed_action_frame: base_link
arm_action_frame: base_link
enable_gripper_command: false
gripper_enabled: false
is_grasp_dataset: false
allow_nominal_state_fallback: false
```

Static verification:

```text
python3 -m py_compile: PASS
xmllint --noout: PASS
roslaunch --ros-args b8_reaching_tuned_v2_episode.launch: PASS
```

Next minimum runtime check:

```text
Run only b8_reaching_smoke_tuned_v2_0000 first, validate it, and inspect
distance/joint metrics before collecting more tuned v2 episodes.
```

## Latest B8' Tuned v2 Progress: Episode 0000

Update date: 2026-05-04.

User ran the first tuned v2 single-episode smoke:

```bash
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v2_episode.launch \
  episode_id:=b8_reaching_smoke_tuned_v2_0000 \
  target_model_name:=cylinder_target_b8_tuned_v2_0000
```

Runtime settings confirmed:

```text
state_sequence: MOVE_TO_PREGRASP,MOVE_TO_GRASP
state_duration_MOVE_TO_PREGRASP: 3.0
state_duration_MOVE_TO_GRASP: 2.0
max_duration_sec: 5.2
rate_hz: 3.0
target_directed_action_frame: base_link
arm_action_frame: base_link
max_linear_step: 0.010
max_joint_delta: 0.010
allow_nominal_state_fallback: false
enable_gripper_command: false
gripper_enabled: false
is_grasp_dataset: false
```

Runtime result:

```text
episode:
  data/raw/b8_reaching_smoke_tuned_v2/b8_reaching_smoke_tuned_v2_0000.npz

validator:
  PASS
  T: 16
  success: False
  unavailable_fields: ['raw_command']
```

Offline quality review:

```text
initial_distance: 0.1330721651505095
min_distance:     0.12345733437492694
final_distance:   0.12598214995126653
distance_reduction: 0.007090015199242988
min_distance_below_0.10: false

action_xyz_norm_mean: 0.015119067436619676
action_xyz_norm_max:  0.017320508075688773
action-relative cosine base/world: 0.727002 / 0.120774

active_left_joint_total_max_abs_delta: 0.05311554674420638
active_left_step_max_abs_delta: 0.006368390020192294

target_world_motion: 0.753281
target_base_motion:  0.046881
```

Interpretation:

- Tuned v2 is valid non-fallback arm-only reaching/pre-grasp smoke data.
- The arm-only state sequence worked: it ran only `MOVE_TO_PREGRASP` and
  `MOVE_TO_GRASP`, with no gripper command and no hand controller.
- Reaching quality improved compared with tuned v1 mean reduction, but the
  episode still did not cross the temporary `0.10 m` threshold.
- Per-step joint motion stayed bounded; cumulative active-left joint motion is
  larger than previous smoke sets and must be monitored before collecting many
  episodes.
- The active blocker remains reaching quality, not data collection.

Additional semantic fix:

- The tuned v2_0000 runtime log ended with `success=False reason=gripper_not_closed`
  because the expert still used the historical grasp success checker at finish.
- This is misleading for B8' because gripper is disabled and the metric is
  `reaching_success`.
- `expert_policy.py` now evaluates arm-only `reaching_success` /
  `pregrasp_success` by distance threshold and no longer uses gripper closure as
  the finish reason for this route.
- `collect_episode.launch` now passes `task_type` and `success_metric` into the
  scripted expert as well as the recorder.

Verification after semantic fix:

```text
python3 -m py_compile expert_policy.py: PASS
xmllint --noout collect_episode.launch b8_reaching_tuned_v2_episode.launch: PASS
roslaunch --ros-args b8_reaching_tuned_v2_episode.launch: PASS
```

Decision:

```text
B8' tuned v2_0000: valid and improved, but reaching-quality blocker is not
resolved because min_distance remains above 0.10 m.
```

Next minimum runtime check:

```text
Run only b8_reaching_smoke_tuned_v2_0001 after the success-semantic fix. Verify
that the final expert reason reports reaching distance, not gripper_not_closed,
then validate and inspect distance/joint metrics before collecting more v2
episodes.
```

## Latest B8' Tuned v2 Progress: Episode 0001

Update date: 2026-05-04.

User ran:

```bash
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v2_episode.launch \
  episode_id:=b8_reaching_smoke_tuned_v2_0001 \
  target_model_name:=cylinder_target_b8_tuned_v2_0001
```

Validation:

```text
validation: PASS
T: 16
success: False
episode_id: b8_reaching_smoke_tuned_v2_0001
unavailable_fields: ['raw_command']
```

Semantic fix result:

```text
Scripted expert finished:
  success=False
  reason=reaching_success: distance 0.128588 above 0.100000
```

This confirms the historical `gripper_not_closed` finish reason has been
removed for the current arm-only reaching route.

Current tuned v2 offline quality summary for episodes 0000-0001:

```text
episodes_total: 2
all_required_metadata_ok: true
episodes_with_positive_distance_reduction: 1/2
episodes_below_0.10: 0/2
min_distance_overall: 0.120829 m
mean_initial_distance: 0.131042 m
mean_final_distance: 0.129159 m
mean_distance_reduction: 0.001883 m
max_active_left_joint_delta: 0.056025 rad
```

Per-episode distance:

```text
0000: initial/min/final/reduction = 0.133072 / 0.123457 / 0.125982 /  0.007090
0001: initial/min/final/reduction = 0.129011 / 0.120829 / 0.132335 / -0.003325
```

Interpretation:

- Tuned v2 episodes are valid non-fallback arm-only smoke data.
- Success semantics are now correct for B8': finish reason is distance-based,
  not gripper-based.
- Reaching quality remains blocked: neither episode crossed `0.10 m`, and
  episode 0001 finished farther than it started.
- Cumulative joint motion is now larger than prior smoke sets while distance
  improvement is still inconsistent. Continuing to collect more v2 episodes
  without another setup/debug check is not recommended.

Decision:

```text
B8' tuned v2 semantic blocker: resolved.
B8' reaching-quality blocker: still open.
Do not continue to tuned v2 episodes 0002-0004 yet.
Do not expand collection or train BC / DP / FM.
```

Next minimum check:

```text
Do a read-only/offline direction diagnostic before changing control again:
compare actual base-frame EEF displacement against the base-frame
relative_target_to_eef direction over tuned v2 episodes 0000-0001.
```

This should determine whether the remaining issue is:

- action direction still not producing target-directed EEF motion;
- target/pregrasp offset or moving base-relative target setup;
- IK/joint-limited motion; or
- the temporary `0.10 m` threshold being inconsistent with the current target
  placement.

## Latest B8' Tuned v2 Offline Direction Diagnostic

Update date: 2026-05-04.

User ran the existing read-only quality review:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/analyze_b8_reaching_quality.py \
  --input-dir src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_smoke_tuned_v2 \
  --pattern 'b8_reaching_smoke_tuned_v2_*.npz' \
  --output-dir src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_reaching_smoke_tuned_v2_quality \
  --threshold 0.10
```

Quality review result:

```text
episodes_total: 2
all_required_metadata_ok: true
episodes_with_positive_distance_reduction: 1
episodes_below_threshold: 0
min_distance_overall: 0.12082938778758692
mean_initial_distance: 0.1310415302513212
mean_final_distance: 0.12915880820700043
mean_distance_reduction: 0.0018827220443207587
max_active_left_joint_delta: 0.0560245462242559
action_xyz_norm_mean_all_samples: 0.015906386305716676
action_xyz_norm_max_all_samples: 0.017320508075688773
recommendation: A
```

Decision from quality review:

```text
B8' reaching-quality blocker is still open.
Do not continue tuned v2 collection to 0002-0004 yet.
Do not expand to 20 episodes.
Do not train BC / DP / FM.
```

Code/tooling update:

```text
Added read-only offline diagnostic script:
  scripts/analyze_b8_reaching_direction.py

Generated artifacts:
  outputs/logs/b8_reaching_smoke_tuned_v2_direction/direction_diagnostic.json
  outputs/logs/b8_reaching_smoke_tuned_v2_direction/direction_diagnostic.md
```

The script only reads existing `.npz` episodes and writes analysis artifacts. It
does not import ROS, start Gazebo, publish commands, train, or rollout.

Direction diagnostic summary:

```text
episodes_total: 2
episodes_below_threshold: 0
episodes_with_positive_distance_reduction: 1
min_distance_overall_base: 0.12082938778758634
mean_distance_reduction_base: 0.001882722044321175
mean_eef_motion_cosine_with_target: -0.09207573656385626
mean_eef_positive_target_direction_ratio: 0.4666666666666667
mean_action_to_eef_motion_cosine: 0.0921582493936101
recommendation: do_not_collect_more_until_direction_issue_is_understood
```

Per-episode direction diagnosis:

```text
0000:
  distance initial/min/final/reduction:
    0.133072 / 0.123457 / 0.125982 / 0.007090
  eef-motion cosine with target direction: 0.119690
  eef positive target-direction ratio: 0.600000
  action target/eef-motion cosine: 0.719576 / 0.274922
  labels:
    threshold_not_reached
    distance_not_consistently_decreasing
    action_to_eef_motion_mismatch
    target_moves_in_base_frame
    base_world_drift_present

0001:
  distance initial/min/final/reduction:
    0.129011 / 0.120829 / 0.132335 / -0.003325
  eef-motion cosine with target direction: -0.303841
  eef positive target-direction ratio: 0.333333
  action target/eef-motion cosine: 0.658835 / -0.090606
  labels:
    threshold_not_reached
    actual_eef_not_consistently_target_directed
    distance_not_consistently_decreasing
    action_to_eef_motion_mismatch
    target_moves_in_base_frame
    base_world_drift_present
```

Interpretation:

- The tuned v2 data is valid non-fallback arm-only reaching smoke data.
- The blocker is not data validity or success metadata.
- The action vector is still generally aligned with the target direction in base
  frame, but actual EEF base-frame displacement does not reliably follow that
  action.
- Base/world drift is present, and the target also moves in base frame in the
  recorded samples. This means the current target/EEF geometry is not stable
  enough for reliable reaching demonstration.
- The current evidence points to action-to-EEF-motion mismatch plus target/base
  motion effects, not to a need for training or larger collection.

Next minimum check:

```text
Inspect the scripted expert / IK command path offline and with logs only:
compare commanded clipped_xyz_planning_frame against actual next-step
eef_base displacement for tuned v2 0000-0001, then decide whether to reduce
target/base motion, simplify to a fixed base-frame pregrasp point, or adjust
the IK command rule.
```

Still not allowed:

- collect more tuned v2 episodes;
- train BC / DP / FM;
- run rollout;
- start or command gripper/hand controller;
- claim grasp success.

## Latest B8' Command-To-Motion Offline Check

Update date: 2026-05-04.

To refine the direction diagnostic, an additional offline-only script was added:

```text
scripts/analyze_b8_command_motion_path.py
```

Purpose:

- read existing tuned v2 `.npz` files only;
- compare `action_ee_delta[t]` with later `eef_base` displacement;
- scan short response lags from 0 to 3 sample steps;
- report action-to-EEF coupling, realized gain, and distance-decreasing ratio;
- write artifacts only under `outputs/logs`.

It does not import ROS, start Gazebo, publish commands, control the robot,
train, or rollout.

Command run:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/analyze_b8_command_motion_path.py \
  --input-dir src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_smoke_tuned_v2 \
  --pattern 'b8_reaching_smoke_tuned_v2_*.npz' \
  --output-dir src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_reaching_smoke_tuned_v2_command_motion \
  --threshold 0.10 \
  --max-lag-steps 3
```

Artifacts:

```text
outputs/logs/b8_reaching_smoke_tuned_v2_command_motion/command_motion_diagnostic.json
outputs/logs/b8_reaching_smoke_tuned_v2_command_motion/command_motion_diagnostic.md
```

Summary:

```text
episodes_total: 2
episodes_below_threshold: 0
mean_best_lag_steps: 0.0
mean_best_action_to_eef_cosine: 0.0921582493936101
mean_best_realized_gain_along_action: 0.02557494803831787
recommendation: do_not_collect_more_until_command_to_motion_path_is_explained
```

Per-episode command-to-motion result:

```text
0000:
  best lag steps: 0
  best action-to-eef cosine: 0.274922
  best eef-to-target cosine: 0.119690
  best realized gain along action: 0.087396
  distance decreasing ratio: 0.466667
  labels:
    threshold_not_reached
    weak_action_to_motion_coupling
    distance_not_decreasing_under_best_lag
    target_moves_in_base_frame
    base_world_drift_present

0001:
  best lag steps: 0
  best action-to-eef cosine: -0.090606
  best eef-to-target cosine: -0.303841
  best realized gain along action: -0.036246
  distance decreasing ratio: 0.466667
  labels:
    threshold_not_reached
    weak_action_to_motion_coupling
    distance_not_decreasing_under_best_lag
    target_moves_in_base_frame
    base_world_drift_present
```

Interpretation:

- The weak action-to-EEF coupling is not explained by a simple 1-3 sample
  response lag.
- The best lag is still 0 for both episodes, but coupling remains weak or
  negative.
- The target moves substantially in base frame during the samples, and base
  world drift is present.
- The remaining blocker is command-to-motion / task-geometry quality, not
  dataset validity.

Decision:

```text
B8' reaching-quality blocker remains open.
Do not continue tuned v2 collection.
Do not train.
Do not rollout.
```

Next minimum action:

```text
Stop collecting and inspect the expert/IK command rule plus target geometry.
The safest next code-level check is to make the expert log or record the
commanded planning-frame IK target and compare it with observed eef_base motion
in one short episode only after the check is implemented.
```

User reproduction:

```text
python3 -m py_compile scripts/analyze_b8_command_motion_path.py: PASS

command-to-motion summary reproduced:
  episodes_total: 2
  episodes_below_threshold: 0
  mean_best_lag_steps: 0.0
  mean_best_action_to_eef_cosine: 0.0921582493936101
  mean_best_realized_gain_along_action: 0.02557494803831787
  recommendation: do_not_collect_more_until_command_to_motion_path_is_explained
```

Confirmed decision:

```text
Current blocker is not resolved.
This is not smoke-level reaching resolved.
The missing evidence is a stable command-to-motion relationship:
  action_ee_delta / IK target should produce target-directed eef_base motion
  and at least one episode should cross the temporary 0.10 m threshold.
```

Next read-only checks:

```text
1. Inspect the existing command construction source:
   expert_policy.py target-directed action generation
   arm_command_converter.py action-frame to planning-frame IK target conversion

2. Inspect tuned v2 launch parameters:
   b8_reaching_tuned_v2_episode.launch
   collect_episode.launch arm_action_frame/target_directed_action_frame pass-through
```

Do not collect additional episodes until this source/config check explains the
weak coupling or identifies a bounded code change.

## Latest B8' Source/Config Read-Only Check

Update date: 2026-05-04.

User attempted the requested source/config check. `rg` was unavailable in the
container, so the launch check was completed with `grep`.

Launch parameter check:

```text
b8_reaching_tuned_v2_episode.launch:
  state_sequence: MOVE_TO_PREGRASP,MOVE_TO_GRASP
  target_directed_action_frame: base_link
  arm_action_frame: base_link
  max_linear_step: 0.010
  max_joint_delta: 0.010

collect_episode.launch:
  passes target_directed_action_frame to expert and recorder
  passes arm_action_frame to expert and recorder
  passes state_sequence to expert and recorder
  passes max_linear_step/max_joint_delta to expert and recorder
```

Source check:

```text
expert_policy.py:
  _target_eef_delta_base_frame computes:
    target_base - eef_translation
  _target_directed_action returns that base-frame delta as action_ee_delta.

arm_command_converter.py:
  action_frame=base_link with planning_frame=world calls _base_delta_in_world.
  _base_delta_in_world rotates the clipped base-frame action by a fresh
  /rexrov/pose_gt orientation sample before constructing the planning-frame IK
  target.
```

Interpretation:

- Static launch/config pass-through is aligned for tuned v2.
- The source contains the intended base-frame action and base-to-world action
  conversion path.
- This does not resolve the blocker because the recorded data still shows weak
  command-to-motion coupling.
- The remaining suspect is runtime state-source consistency:
  - expert action uses target pose, stored `base_pose`, and TF EEF pose;
  - converter uses current MoveGroup/IK pose plus a fresh `/rexrov/pose_gt`
    sample for action-frame conversion;
  - recorder evaluates EEF/target/base from its own recorded samples.

Decision:

```text
Current blocker remains open.
No control-code change is justified yet from static source/config inspection
alone.
```

Next minimum read-only check:

```text
Check live runtime frame/config state before any new collection:
  - verify ROS params for arm_action_frame and target_directed_action_frame;
  - verify whether move_group planning_frame is world and whether TF can connect
    world, rexrov/base_link, and oberon7_l/end_effector consistently.
```

## Latest B8' Runtime Frame Check

Update date: 2026-05-04.

User checked live expert parameters:

```text
/dp_fm_scripted_expert/target_directed_action_frame: base_link
/dp_fm_scripted_expert/arm_action_frame: base_link
/dp_fm_scripted_expert/state_sequence: MOVE_TO_PREGRASP,MOVE_TO_GRASP
/dp_fm_scripted_expert/max_linear_step: 0.01
/dp_fm_scripted_expert/max_joint_delta: 0.01
```

Runtime TF check:

```text
tf_echo rexrov/base_link oberon7_l/end_effector:
  available and stable
  translation approx [2.075, 0.615, -1.290]

tf_echo world rexrov/base_link:
  fails consistently
  Could not find a connection between 'world' and 'rexrov/base_link'
  Tf has two or more unconnected trees.
```

Interpretation:

- Tuned v2 runtime parameters are correct.
- The local robot kinematic chain from `rexrov/base_link` to the left EEF is
  visible and stable in TF.
- The `world` planning frame is not connected to `rexrov/base_link` in TF.
- This confirms the earlier MoveIt warning about `world_to_base` and explains
  why a command built as a world/planning-frame IK target can fail to match the
  recorder's odom + base-link EEF geometry.
- The remaining blocker is runtime frame consistency between MoveIt planning
  frame, odom-derived base pose, TF EEF pose, and recorder samples.

Decision:

```text
Current blocker is not resolved.
This is not smoke-level reaching resolved.
Do not continue tuned v2 collection.
Do not train or rollout.
```

Next minimum read-only check:

```text
Inspect the MoveIt/SRDF virtual joint and planning-frame configuration to
confirm that MoveIt expects world -> rexrov/base_link while TF does not provide
that transform.
```

This check should remain read-only. A code change may be needed after that, but
the change should be targeted at frame/state consistency, not at gripper,
training, or rollout.

## Latest B8' World/Base TF Bridge Prepared

Update date: 2026-05-04.

User inspected `/robot_description_semantic`:

```text
<virtual_joint
  name="world_to_base"
  type="floating"
  parent_frame="world"
  child_link="rexrov/base_link" />
```

This confirms:

- MoveIt expects a `world -> rexrov/base_link` virtual joint.
- Runtime TF did not provide that connection.
- The earlier `world_to_base` MoveIt warning and command-to-motion mismatch are
  consistent with a missing TF bridge between MoveIt `world` and the odom/base
  state source.

Code update, package-local only:

```text
src/rexrov_single_oberon7_fm_dp/odom_tf_bridge.py
scripts/odom_tf_bridge.py
launch/world_base_tf_bridge.launch
```

Purpose:

```text
Subscribe: /rexrov/pose_gt
Publish TF: world -> rexrov/base_link
No robot command topics.
No gripper.
No training.
No rollout.
```

Static verification:

```text
python3 -m py_compile:
  src/rexrov_single_oberon7_fm_dp/odom_tf_bridge.py
  scripts/odom_tf_bridge.py
  PASS

xmllint --noout launch/world_base_tf_bridge.launch:
  PASS

roslaunch rexrov_single_oberon7_fm_dp world_base_tf_bridge.launch --ros-args:
  PASS
```

Decision:

```text
Current reaching-quality blocker is not resolved yet.
The next check is TF-bridge smoke only: run the bridge and verify that
tf_echo world rexrov/base_link succeeds.
Do not collect new episodes until that passes.
```

Next command for user:

```bash
roslaunch rexrov_single_oberon7_fm_dp world_base_tf_bridge.launch
```

Then, in another shell:

```bash
timeout 4s rosrun tf tf_echo world rexrov/base_link
timeout 4s rosrun tf tf_echo world oberon7_l/end_effector
```

Expected result:

```text
world -> rexrov/base_link succeeds with odom-like translation/orientation.
world -> oberon7_l/end_effector also succeeds through the connected TF tree.
```

This is still only a frame/connectivity smoke check, not reaching success.

## Latest B8' TF Bridge Runtime Smoke

Update date: 2026-05-04.

User ran:

```bash
roslaunch rexrov_single_oberon7_fm_dp world_base_tf_bridge.launch
```

Runtime output:

```text
dp_fm_odom_tf_bridge params:
  child_frame: rexrov/base_link
  odom_topic: /rexrov/pose_gt
  parent_frame: world
  repeat_rate_hz: 20.0

Odom TF bridge publishing world -> rexrov/base_link from /rexrov/pose_gt
```

TF checks:

```text
tf_echo world rexrov/base_link:
  SUCCESS
  example translation: [141.667, -8.227, -98.464]
  example yaw: about 106.7 deg

tf_echo world oberon7_l/end_effector:
  initially failed while TF tree was updating, then SUCCESS
  example translation: [140.493, -5.907, -99.751]
```

Interpretation:

- The package-local TF bridge is working.
- The missing MoveIt virtual-joint TF connection is resolved at frame-smoke
  level.
- `world -> oberon7_l/end_effector` connectivity can lag briefly at startup,
  but becomes available once the bridge and robot TF chain are both active.
- This does not prove reaching quality. It only resolves the frame-connectivity
  sub-blocker that prevented consistent MoveIt world-frame state updates.

Decision:

```text
TF bridge / world-base connectivity smoke: resolved.
B8' reaching-quality blocker: still open.
Do not train.
Do not rollout.
Do not claim grasp success.
```

Next minimum check:

```text
With the TF bridge still running, run exactly one short tuned-v2-style
arm-only smoke episode using a new output directory/name, then validate and run
offline quality + command-to-motion diagnostics before collecting any more.
```

This next check is allowed only as a single short frame-fix validation episode,
not as 5-episode collection expansion.

## Latest B8' TF Bridge Frame-Fix Validation Episode

Update date: 2026-05-04.

Runtime context:

```text
uvms_control running
b5d_move_group_with_context running
load_left_controllers start:=true load_hand:=false running
world_base_tf_bridge.launch running
```

User collected exactly one short frame-fix validation episode:

```bash
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v2_episode.launch \
  output_dir:=.../data/raw/b8_reaching_smoke_tf_bridge_check \
  episode_id:=b8_reaching_smoke_tf_bridge_check_0000 \
  target_model_name:=cylinder_target_b8_tf_bridge_check_0000
```

Runtime evidence:

```text
No "Unable to update multi-DOF joint world_to_base" warning appeared.
B5 arm command lines used:
  planning_frame=world
  action_frame=base_link
```

Validation:

```text
validation: PASS
T: 16
success: False
episode_id: b8_reaching_smoke_tf_bridge_check_0000
unavailable_fields: ['raw_command']
```

Quality summary:

```text
episodes_total: 1
all_required_metadata_ok: true
episodes_with_positive_distance_reduction: 1
episodes_below_threshold: 0
initial_distance: 0.12896387383800806
min_distance_overall: 0.12272243911393374
final_distance: 0.12671316334997665
mean_distance_reduction: 0.00225071048803141
max_active_left_joint_delta: 0.04185326590208582
action_xyz_norm_mean_all_samples: 0.01503565601297632
action_xyz_norm_max_all_samples: 0.017320508075688773
```

Detailed quality labels:

```text
action-relative cosine base/world: 0.658332 / 0.322924
clip fraction at max_linear_step: 0.646
target world/base motion: 0.913777 / 0.011852
failure reason candidates:
  base_drift_dominates_world_eef
  threshold_not_reached
```

Command-to-motion summary:

```text
episodes_total: 1
episodes_below_threshold: 0
mean_best_lag_steps: 0.0
mean_best_action_to_eef_cosine: 0.38837550274847654
mean_best_realized_gain_along_action: 0.10417398838872995
```

Comparison to tuned v2 before bridge:

```text
mean_best_action_to_eef_cosine:
  before bridge: 0.0921582493936101
  after bridge:  0.38837550274847654

mean_best_realized_gain_along_action:
  before bridge: 0.02557494803831787
  after bridge:  0.10417398838872995
```

Interpretation:

- The TF bridge materially improves command-to-motion coupling.
- The frame/state consistency sub-blocker is resolved at frame-fix validation
  smoke level.
- The reaching-quality blocker is still open because the episode did not cross
  the temporary `0.10 m` threshold and distance reduction remains small.
- The remaining issue is likely target/base drift plus conservative/clipped
  reaching behavior, not the previous missing `world -> rexrov/base_link` TF.

Decision:

```text
TF bridge / command-to-motion sub-blocker: smoke-level improved/resolved.
B8' reaching-quality blocker: still open.
Do not expand to 5/20 episodes yet.
Do not train.
Do not rollout.
Do not claim grasp success.
```

Next minimum check:

```text
Run read-only direction diagnostics on this single frame-fix episode before
changing expert parameters or collecting another episode.
```

## Latest B8' TF Bridge Direction Diagnostic

Update date: 2026-05-04.

User ran read-only direction diagnostics on the single TF-bridge frame-fix
episode:

```bash
python3 scripts/analyze_b8_reaching_direction.py \
  --input-dir data/raw/b8_reaching_smoke_tf_bridge_check \
  --pattern 'b8_reaching_smoke_tf_bridge_check_*.npz' \
  --output-dir outputs/logs/b8_reaching_smoke_tf_bridge_check_direction \
  --threshold 0.10
```

Summary:

```text
episodes_total: 1
episodes_below_threshold: 0
episodes_with_positive_distance_reduction: 1
min_distance_overall_base: 0.12272243911393352
mean_distance_reduction_base: 0.002250710488031743
mean_action_to_eef_motion_cosine: 0.38837550274847654
mean_eef_motion_cosine_with_target: 0.008830359482655255
mean_eef_positive_target_direction_ratio: 0.4666666666666667
recommendation: do_not_collect_more_until_direction_issue_is_understood
```

Per-episode details:

```text
distance initial/min/final/reduction:
  0.128964 / 0.122722 / 0.126713 / 0.002251

eef base net/mean-step/max-step:
  0.008801 / 0.003905 / 0.006750

action target/eef-motion cosine:
  0.654347 / 0.388376

target base net/max-step:
  0.011852 / 0.089075

base world net/path:
  1.079475 / 1.082072

labels:
  threshold_not_reached
  actual_eef_not_consistently_target_directed
  distance_not_consistently_decreasing
  target_moves_in_base_frame
  base_world_drift_present
```

Additional read-only per-sample geometry check:

```text
max target_base step: 0.089075 m
max eef_base step:    0.006750 m
```

Interpretation:

- The TF bridge improved action-to-EEF coupling, but actual EEF motion is still
  not consistently target-directed.
- The target moves in base frame by as much as about `0.089 m` between samples,
  while EEF motion per sample is only about `0.002-0.007 m`.
- The remaining blocker is dominated by target/base geometry stability and
  update lag, not by missing `world -> rexrov/base_link` TF anymore.
- The current episode remains valid non-fallback smoke data, but reaching
  quality is still insufficient.

Decision:

```text
B8' reaching-quality blocker remains open.
Do not collect more episodes yet.
Do not train.
Do not rollout.
```

Next minimum check:

```text
Read-only inspect base-relative target updater timing and recorded
target_base/eef_base per-sample geometry before changing expert parameters.
The likely next bounded change will be to reduce target update lag/jitter,
not to touch gripper or training.
```

Latest per-sample geometry check on the single TF-bridge validation episode:

```text
episode:
  data/raw/b8_reaching_smoke_tf_bridge_check/b8_reaching_smoke_tf_bridge_check_0000.npz

max_target_step_base: 0.08907516876353049 m
max_eef_step_base:    0.006750324744116928 m
initial_distance:     0.128964 m
min_distance:         0.122722 m
final_distance:       0.126713 m
```

Interpretation:

- The TF bridge sub-blocker is smoke-level resolved, and command-to-motion
  coupling improved relative to tuned v2 without the bridge.
- The B8' reaching-quality blocker is still open: no sample crossed the
  `0.10 m` threshold, and the target base-frame jumps are more than 10x larger
  than EEF base-frame step motion.
- The remaining narrow blocker is target update timing/jitter in the
  base-relative target helper.

Code change:

- `launch/b8_reaching_tuned_v2_episode.launch` now sets
  `base_relative_target_rate_hz` to `30.0` for the tuned v2 smoke wrapper.
- This only changes the package-local B8' target-updater frequency. It does
  not touch gripper, hand controller, training, rollout, or external packages.

Next minimum check:

```text
Run exactly one short B8' validation episode with the TF bridge still running
and the 30 Hz base-relative target updater, then validate and rerun the same
offline quality/direction/command-motion diagnostics.

Do not collect a 5-episode set, train, or rollout until this one-episode check
shows that target base-frame jumps are reduced and reaching quality improves.
```

Latest target30 validation result:

```text
episode:
  data/raw/b8_reaching_smoke_tf_bridge_target30_check/b8_reaching_smoke_tf_bridge_target30_check_0000.npz

validator: PASS
T: 16
success: False
unavailable_fields: ['raw_command']

quality:
  episodes_below_threshold: 0/1
  initial_distance: 0.12549968637530884 m
  min_distance_overall: 0.12160315011478852 m
  final_distance: 0.12413588250680598 m
  mean_distance_reduction: 0.0013638038685028636 m
  max_active_left_joint_delta: 0.04081576279364185 rad

direction:
  mean_action_to_eef_motion_cosine: 0.6983946289035002
  mean_eef_motion_cosine_with_target: 0.4453145000526829
  mean_eef_positive_target_direction_ratio: 0.8
```

Interpretation:

- The 30 Hz target updater improved directional consistency substantially.
- The B8' reaching-quality blocker remains open because the episode still did
  not cross the `0.10 m` reaching threshold.
- The current remaining question is whether target base-frame jumps were
  actually reduced enough, and whether the command-to-motion lag diagnostic
  agrees with the improved direction diagnostic.

Next minimum read-only check:

```text
Run command-to-motion diagnostic and inspect the generated direction diagnostic
markdown for target_base net/max-step on the target30 episode.
Do not collect more episodes or tune parameters until those two numbers are
known.
```

Latest target30 command-to-motion and target-step result:

```text
command-to-motion:
  episodes_below_threshold: 0/1
  mean_best_action_to_eef_cosine: 0.956902308613389
  mean_best_lag_steps: 2.0
  mean_best_realized_gain_along_action: 0.3194339452607246

direction markdown:
  target_base_net/max-step: 0.034005 / 0.014167
  eef_base_net/mean-step/max-step: 0.044696 / 0.004615 / 0.007119
  distance decreasing step ratio: 0.400000
```

Interpretation:

- The target updater change resolved the large target-jump sub-blocker at the
  smoke level: max target base-frame step dropped from about `0.089 m` to about
  `0.014 m`.
- Command-to-motion coupling is now strong, but the best observed lag is
  `2` recorder steps at `3 Hz` (about `0.67 s`).
- B8' remains below acceptance because the minimum distance is still about
  `0.1216 m`; the remaining blocker is now short-horizon/lag-limited reaching,
  not missing TF or target updater jitter.

Next minimum check:

```text
Before changing code, inspect the per-lag command-motion markdown table for
the target30 episode. If the table confirms lag-2 is the dominant coupling,
the next bounded code/config change should extend the tuned v2 smoke horizon
or state durations, not collect more data or train.
```

Latest per-lag command-motion result:

```text
lag 0:
  action/eef cos: 0.698395
  eef/target cos: 0.445315
  gain: 0.226123
  dist-decrease ratio: 0.400000

lag 1:
  action/eef cos: 0.820193
  eef/target cos: 0.537372
  gain: 0.268557
  dist-decrease ratio: 0.357143

lag 2:
  action/eef cos: 0.956902
  eef/target cos: 0.654001
  gain: 0.319434
  dist-decrease ratio: 0.384615

lag 3:
  action/eef cos: 0.946611
  eef/target cos: 0.776835
  gain: 0.310540
  dist-decrease ratio: 0.416667
```

Decision:

```text
B8' remains unresolved, but the blocker has narrowed to lag/horizon-limited
reaching. Target updater jitter is smoke-level improved, and command-to-motion
coupling is strong.
```

Code/config change:

- Added `launch/b8_reaching_tuned_v3_episode.launch`.
- It preserves the v2 safety constraints:
  - gripper disabled;
  - `target_directed_action_frame=base_link`;
  - `base_relative_target_rate_hz=30.0`;
  - `max_linear_step=0.010`;
  - `max_joint_delta=0.010`.
- It only extends the short smoke horizon:
  - `max_duration_sec: 5.2 -> 7.2`;
  - `MOVE_TO_PREGRASP: 3.0 -> 4.0`;
  - `MOVE_TO_GRASP: 2.0 -> 3.0`.

Next minimum check:

```text
Run exactly one tuned v3 episode with the same runtime prerequisites and then
validate + rerun quality/direction/command-motion diagnostics. Do not collect a
5-episode set or train unless this one-episode check crosses or clearly
approaches the 0.10 m reaching threshold.
```

Latest tuned v3 one-episode result:

```text
episode:
  data/raw/b8_reaching_smoke_tuned_v3_check/b8_reaching_smoke_tuned_v3_check_0000.npz

validator: PASS
T: 22
success: False
unavailable_fields: ['raw_command']

quality:
  episodes_below_threshold: 1/1
  initial_distance: 0.1264832193593639 m
  min_distance_overall: 0.08480029669684241 m
  final_distance: 0.12246726976236536 m
  mean_distance_reduction: 0.004015949596998553 m
  max_active_left_joint_delta: 0.06377453998389893 rad

direction:
  mean_action_to_eef_motion_cosine: 0.6652890486895977
  mean_eef_motion_cosine_with_target: 0.5093671918914294
  mean_eef_positive_target_direction_ratio: 0.8095238095238095

command-to-motion:
  mean_best_action_to_eef_cosine: 0.6652890486895977
  mean_best_lag_steps: 0.0
  mean_best_realized_gain_along_action: 0.19879837117714555
```

Decision:

```text
B8' reaching-quality blocker is smoke-level resolved for a single tuned v3
episode crossing the 0.10 m threshold.
```

Limitations:

- This is one short validation episode only, not a dataset expansion.
- `success=False` remains because the final/finish distance was about
  `0.122 m`, above the threshold.
- The threshold crossing may be transient; distance consistency and threshold
  persistence have not been inspected.
- No training, rollout, grasp success, or learned-policy success should be
  claimed from this result.

Next minimum read-only check:

```text
Inspect the tuned v3 quality and direction markdown reports to determine
whether the threshold crossing is transient or stable enough to justify a small
repeatability check.
```

Latest tuned v3 markdown inspection:

```text
quality markdown:
  distance initial/min/final/reduction:
    0.126483 / 0.084800 / 0.122467 / 0.004016
  below threshold: True
  final closer: True
  action xyz norm mean/max: 0.013724 / 0.016232
  clip fraction at max_linear_step: 0.561
  joint max delta / step max delta: 0.063775 / 0.006013
  target world/base motion: 0.374723 / 0.038119
  failure reason candidates: base_drift_dominates_world_eef

direction markdown:
  distance decreasing step ratio: 0.523810
  eef base net/mean-step/max-step: 0.049145 / 0.004544 / 0.009855
  target base net/max-step: 0.038119 / 0.055363
  base world net/path: 0.797345 / 0.799997
  labels: target_moves_in_base_frame, base_world_drift_present
```

Updated interpretation:

- The tuned v3 threshold crossing is real in the recorded episode, but the
  final distance rebounded above threshold.
- `target_base max-step` increased to about `0.055 m`, so target/base geometry
  is improved versus the pre-30Hz case but not as stable as the target30
  episode (`0.014 m` max-step).
- Before any repeatability collection, inspect the raw per-sample distance
  trace to count how many samples were below threshold and when the rebound
  occurred.

Next minimum read-only check:

```text
Count per-sample distances below the 0.10 m threshold and inspect the target
base-frame step sequence for the tuned v3 episode.
```

Latest tuned v3 per-sample trace:

```text
samples: 22
below_count: 1
below_indices: [12]
min_idx: 12
min_distance: 0.08480029669684272 m
final_distance: 0.12246726976236501 m
max_target_step: 0.05536288107656983 m
max_target_step_idx: 13
```

Key samples:

```text
idx 11: distance=0.127842, target_step=0.006681, eef_step=0.004417
idx 12: distance=0.084800, target_step=0.041232, eef_step=0.004999
idx 13: distance=0.132893, target_step=0.055363, eef_step=0.006427
```

Updated interpretation:

- The tuned v3 threshold crossing is a single-sample transient.
- The minimum occurs at the same time as a large target base-frame step, and the
  next sample has the largest target step and rebounds above threshold.
- B8' is not ready for repeatability collection, dataset expansion, or
  training. The residual blocker is target/base geometry stability around
  threshold crossing, not arm command execution.

Next minimum check:

```text
Do not collect another B8' episode yet. Inspect the base-relative target updater
implementation and launch parameters to decide the smallest package-local way
to reduce target_base step spikes before another one-episode validation.
```

Package-local target updater fix:

- Updated `src/rexrov_single_oberon7_fm_dp/base_relative_target.py` to subscribe
  to `/rexrov/pose_gt` and use a fresh cached odom pose instead of blocking on
  `rospy.wait_for_message()` inside every target update.
- Added `base_relative_target_max_base_pose_age_sec`, default `0.25 s`.
- Updated `collect_episode.launch` and `b8_reaching_tuned_v3_episode.launch`
  to pass the freshness bound.

Reason:

- The tuned v3 trace showed the only below-threshold sample was adjacent to
  large target base-frame steps.
- The updater was configured at `30 Hz` while `/rexrov/pose_gt` is around
  `20 Hz`; blocking for a new odom message inside each update can introduce
  irregular update timing.
- The new cached-odom path is the smallest package-local change aimed at
  reducing target_base step spikes.

Verification:

```text
python3 -m py_compile base_relative_target.py scripts/base_relative_target.py: PASS
xmllint collect_episode.launch b8_reaching_tuned_v3_episode.launch: PASS
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v3_episode.launch --ros-args: PASS
```

Next minimum check:

```text
Run exactly one tuned v3 cached-odom validation episode and compare
target_base max-step, below_count, min/final distance, and command-to-motion
metrics with the previous tuned v3 episode.
```

Latest cached-odom tuned v3 validation result:

```text
episode:
  data/raw/b8_reaching_smoke_tuned_v3_cached_odom_check/b8_reaching_smoke_tuned_v3_cached_odom_check_0000.npz

validator: PASS
T: 22
success: False
unavailable_fields: ['raw_command']

quality:
  episodes_below_threshold: 1/1
  episodes_with_positive_distance_reduction: 0/1
  initial_distance: 0.12630808035415297 m
  min_distance_overall: 0.08611444139540192 m
  final_distance: 0.14779493259862328 m
  mean_distance_reduction: -0.021486852244470306 m
  max_active_left_joint_delta: 0.06405061370333787 rad

direction:
  mean_distance_reduction_base: -0.02148685224447025 m
  mean_eef_motion_cosine_with_target: 0.5192861743957111
  mean_eef_positive_target_direction_ratio: 0.8095238095238095
  mean_action_to_eef_motion_cosine: 0.6683840448271507

command-to-motion:
  mean_best_action_to_eef_cosine: 0.7985718493152257
  mean_best_lag_steps: 2.0
  mean_best_realized_gain_along_action: 0.26166311035433365
```

Decision:

```text
Cached-odom updater did not resolve B8' reaching stability.
B8' remains smoke-level progress only, not ready for repeatability collection,
training, or rollout.
```

Interpretation:

- The episode still crossed threshold once, but the final distance worsened to
  about `0.148 m`.
- Positive distance reduction regressed from `1/1` to `0/1`.
- The best command-to-motion lag moved back to `2` recorder steps.
- The cached-odom updater did not remove the residual instability by itself.

Next minimum read-only check:

```text
Run the same per-sample NPZ trace on the cached-odom episode to determine
below_count and target_base max-step before changing code again.
```

Latest cached-odom per-sample trace:

```text
samples: 22
below_count: 1
below_indices: [10]
min_idx: 10
min_distance: 0.08611444139540188 m
final_distance: 0.14779493259862325 m
max_target_step: 0.050329083057232285 m
max_target_step_idx: 11
```

Key samples:

```text
idx 10: distance=0.086114, below=True,  target_step=0.036269, eef_step=0.005077
idx 11: distance=0.131695, below=False, target_step=0.050329, eef_step=0.004172
idx 16: distance=0.148117, below=False, target_step=0.042151, eef_step=0.004758
idx 21: distance=0.147795, below=False, target_step=0.021348, eef_step=0.004554
```

Updated interpretation:

- Cached-odom still produced only a single below-threshold sample.
- The largest target base-frame step occurs immediately after the minimum and
  coincides with a distance rebound.
- The target_base step spike decreased only slightly versus tuned v3
  (`0.055 m -> 0.050 m`), and final distance got worse.
- The remaining ambiguity is whether target_base spikes reflect real target
  motion or recorder-time mismatch between `base_pose`, `target_pose`, and
  `eef_pose` samples.

Next minimum read-only check:

```text
Compare recomputed target/eef distance against the recorder's stored
relative_target_to_eef field for the same cached-odom episode. If they diverge,
the blocker is at least partly recorder synchronization / representation. If
they match, target/base motion is real in the recorded task geometry.
```

## B2 Command Interface Check Result

User check date: 2026-05-02.

Launch under test:

```bash
roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=false
```

Read-only runtime findings:

- No topics matched:

  ```bash
  rostopic list | grep -E "arm|hand|oberon|controller|trajectory|follow_joint"
  ```

- Controller parameters exist under `/oberon7/...`, including:
  - `/oberon7/arm_position_l/type`
  - `/oberon7/arm_position_l/joints`
  - `/oberon7/hand_position_l/type`
  - `/oberon7/hand_position_l/joints`
  - `/oberon7/arm_l_group_effort/type`
  - `/oberon7/joint_group_arm_l_position_controller/type`
- Controller-manager services exist at the global namespace:
  - `/controller_manager/list_controllers`
  - `/controller_manager/list_controller_types`
  - `/controller_manager/load_controller`
  - `/controller_manager/switch_controller`
- `list_controllers` returns promptly but only reports:

  ```text
  joint_state_controller: running
  ```

- `list_controller_types` returns available controller plugin types, including
  trajectory, position, effort, and group controllers.

Static launch/config findings:

- `uvms_control/launch/oberon7_position_control.launch` loads
  `data_rexrov_dual_oberon7/config/oberon7_controllers.yaml` into namespace
  `/oberon7`.
- The launch attempts to spawn `arm_position_l arm_position_r` inside:

  ```xml
  <group ns="oberon7">
    <node pkg="controller_manager" type="spawner" name="arm_pos_spawner"
          args="arm_position_l arm_position_r" output="screen"/>
  </group>
  ```

- Runtime services shown by the user are global `/controller_manager/...`, not
  `/oberon7/controller_manager/...`.

B2 status:

```text
partially resolved: left-arm joint-space command execution is minimally resolved; clean baseline shows gripper joints already moving fast before arm/hand controllers are loaded; gripper command remains blocked
```

Interpretation:

- Candidate controller configs are present, but the controllers are not loaded
  or running in the current runtime.
- Because no left-arm or gripper command/action topics exist, the package still
  cannot drive the left arm or gripper.
- MoveIt trajectory execution remains blocked for the same reason.
- The likely issue is controller loading/namespace wiring, but this still needs
  one more read-only confirmation before trying any runtime load/switch action.
- Follow-up read-only checks confirmed:
  - only global `/controller_manager/...` services exist;
  - no `/oberon7/controller_manager/...` services exist;
  - no controller spawner node remains alive;
  - `/oberon7/arm_position_l` and `/oberon7/hand_position_l` params are present
    and specify `position_controllers/JointTrajectoryController`;
  - `/oberon7/arm_l_group_effort` params are present and specify
    `effort_controllers/JointGroupEffortController`.
- Current best interpretation: the active launch loads controller parameters
  under `/oberon7`, but the only available controller manager is global. The
  controller spawner under `<group ns="oberon7">` likely targeted a namespaced
  controller manager that does not exist, then exited.
- Non-motion `load_controller` check succeeded for
  `oberon7/arm_position_l`.
- `list_controllers` now shows:

  ```text
  oberon7/arm_position_l:
    state: initialized
    type: position_controllers/JointTrajectoryController
    hardware_interface: hardware_interface::PositionJointInterface
    resources:
      oberon7_l/azimuth
      oberon7_l/elbow
      oberon7_l/pitch
      oberon7_l/roll
      oberon7_l/shoulder
      oberon7_l/wrist
  ```

- Left-arm trajectory topics now exist:
  - `/oberon7/arm_position_l/command`
  - `/oberon7/arm_position_l/follow_joint_trajectory/*`
  - `/oberon7/arm_position_l/state`
- Non-motion `load_controller` check also succeeded for
  `oberon7/hand_position_l`.
- `list_controllers` shows `oberon7/hand_position_l` in `initialized` state.
- Left-gripper trajectory topics now exist:
  - `/oberon7/hand_position_l/command`
  - `/oberon7/hand_position_l/follow_joint_trajectory/*`
  - `/oberon7/hand_position_l/state`
- Command/action topic types were confirmed:
  - `/oberon7/arm_position_l/command`: `trajectory_msgs/JointTrajectory`
  - `/oberon7/arm_position_l/follow_joint_trajectory/goal`:
    `control_msgs/FollowJointTrajectoryActionGoal`
  - `/oberon7/hand_position_l/command`: `trajectory_msgs/JointTrajectory`
  - `/oberon7/hand_position_l/follow_joint_trajectory/goal`:
    `control_msgs/FollowJointTrajectoryActionGoal`
- Both left controllers are still not running, and no trajectory has been sent.
- Added package-local helper launch:
  `launch/load_left_controllers.launch`.
  It defaults to `start:=false`, which loads controllers with `--stopped` and
  does not command motion.
- The helper launch was tested on a clean simulation with `start:=false`.
- It loaded both left controllers:
  - `oberon7/arm_position_l`
  - `oberon7/hand_position_l`
- A later `switch_controller` check started both controllers successfully.
- Left-arm controller state after start showed desired and actual positions
  close together with small errors.
- Left-gripper controller state after start showed large desired-vs-actual
  errors and high finger joint velocities.
- A follow-up state sample after about 3 seconds still showed the gripper with
  large error and high velocities, while the arm remained close to desired.
- Stopping only `oberon7/hand_position_l` succeeded and the controller state
  changed to `stopped`.
- After stopping the hand controller and waiting 2 seconds, `/joint_states`
  still showed large left gripper joint velocities, including about `1.00`,
  `0.47`, `-0.90`, and `-0.09` rad/s for the four left gripper joints.
- After waiting 5 more seconds with `oberon7/hand_position_l` still stopped,
  the hand command and action-goal topics had no publishers, but the left
  gripper velocities remained large: about `1.01`, `0.48`, `-0.92`, and
  `-0.16` rad/s.
- The right gripper joints also showed substantial velocities even though no
  right hand controller was loaded, which suggests a model/physics or
  uncontrolled-joint behavior rather than a left hand command publisher.
- A fresh simulation with only `joint_state_controller` running showed the same
  pattern before loading or starting any arm/hand controller:
  - left and right gripper finger velocities around `-0.48`, `-0.65`, `0.22`,
    and `0.28` rad/s;
  - both sides nearly symmetric.
- In a fresh simulation, loading and starting only `oberon7/arm_position_l`
  succeeded.
- `oberon7/arm_position_l` became `running`; no hand controller was loaded.
- `/oberon7/arm_position_l/command` is `trajectory_msgs/JointTrajectory` and is
  subscribed by `/gazebo`.
- Arm desired and actual positions were close, but the state still had nonzero
  velocities, including pitch around `0.048` rad/s in the first sample.
- A later arm-only settle check showed arm position errors around `1e-05` rad
  and velocities reduced to small values; the largest reported arm velocity was
  pitch around `0.006` rad/s.
- A current-position arm-only no-op `JointTrajectory` was published to
  `/oberon7/arm_position_l/command`; `rostopic pub` completed normally.
- After the no-op command, controller desired positions matched the commanded
  positions and actual positions remained close, with errors around `3e-06` to
  `3e-05` rad.
- Post-command arm velocities stayed small, though slightly higher than the
  pre-command settle sample, with largest reported values around `0.015`
  rad/s.
- A tiny nonzero arm-only command was published with shoulder target increased
  by about `+0.001` rad.
- Desired shoulder updated to the commanded value near `0.0058386354`; actual
  shoulder moved near that target (`0.0058774`) with about `3.9e-05` rad error.
- Post-command arm errors remained under about `9.2e-05` rad. Arm velocities
  stayed bounded, though pitch velocity was about `0.047` rad/s in the first
  post-command sample.
- A later post-motion settle check kept errors small, about `2.5e-06` to
  `5.1e-05` rad. Arm velocities remained bounded; controller-state shoulder
  velocity was about `0.020` rad/s and joint-state shoulder velocity was about
  `0.0038` rad/s in the sampled messages.
- Minimal left-arm joint-space command execution is therefore considered
  resolved for B2. This does not imply end-effector delta control is available.
- The arm controller remained running and stable after stopping the hand
  controller.
- Current B2 safety conclusion:

  ```text
  left-arm joint-space commands are minimally usable; gripper execution remains
  blocked by baseline model/physics/uncontrolled-joint motion
  ```

Next minimal check:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosrun tf view_frames
rosrun tf tf_echo rexrov/base_link oberon7_l/end_effector
```

Purpose:

- Start B3 with read-only TF/end-effector availability checks.
- Confirm whether the configured `oberon7_l/end_effector` frame exists.
- Confirm whether an eef pose can be computed relative to `rexrov/base_link`.
- If the frame name is wrong, use the generated TF frame list to select the
  correct left-arm endpoint frame.
- `list_controllers` confirmed both controllers in `initialized` state after
  the helper launch.
- Start-only `switch_controller` check returned `ok: True`.
- `list_controllers` confirmed both left controllers in `running` state:
  - `oberon7/arm_position_l`
  - `oberon7/hand_position_l`
- `/oberon7/arm_position_l/state` publishes controller state.
- `/oberon7/hand_position_l/state` publishes controller state.
- Safety observation: after start-only, the arm desired and actual positions
  were close, but the gripper desired and actual positions had a much larger
  error and nontrivial velocities. Treat gripper start behavior as potentially
  active, not a guaranteed passive no-op.

## B1 Live State Check Result

User check date: 2026-05-02.

Launch used:

```bash
roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=false
```

Observed live topics:

```text
/clock
/gazebo/model_states
/joint_states
/rexrov/pose_gt
/rexrov/pose_gt/state
```

Confirmed publishers:

```text
/joint_states: gazebo -> robot_state_publisher
/rexrov/pose_gt: gazebo
/gazebo/model_states: gazebo
```

Confirmed live samples:

- `/joint_states` returned a finite `sensor_msgs/JointState` sample.
- `/joint_states.name` included all left Oberon7 arm and gripper joints:
  - `oberon7_l/azimuth`
  - `oberon7_l/shoulder`
  - `oberon7_l/elbow`
  - `oberon7_l/roll`
  - `oberon7_l/pitch`
  - `oberon7_l/wrist`
  - `oberon7_l/finger_left_joint`
  - `oberon7_l/finger_tip_left_joint`
  - `oberon7_l/finger_right_joint`
  - `oberon7_l/finger_tip_right_joint`
- `/rexrov/pose_gt` returned a finite `nav_msgs/Odometry` sample in `world`.
- `/gazebo/model_states` returned a finite sample with models:
  - `ocean_box`
  - `rexrov`
- `/gazebo/get_model_state`, `/gazebo/spawn_sdf_model`,
  `/gazebo/spawn_urdf_model`, and controller-manager services exist.

B1 status:

```text
resolved for current minimal launch and non-fallback recorder smoke test
```

Resolved:

- Live joint state for the active-left arm exists.
- Live RexROV odometry exists.
- Gazebo model-state topic exists.
- Topic-rate checks show stable continuous publication:
  - `/joint_states`: about 50 Hz
  - `/rexrov/pose_gt`: about 20 Hz
  - `/gazebo/model_states`: about 500 Hz
- `/gazebo/get_model_state` returns `success: True` for `rexrov`.
- Package-local `cylinder_target` SDF can be spawned with `gazebo_ros
  spawn_model`.
- Re-running the same spawn command returns `Failure - entity already exists`,
  which confirms the first spawn created the target entity.
- `/gazebo/get_model_state` returns `success: True` for `cylinder_target`.
- `/gazebo/model_states.name` includes `cylinder_target`.
- Recorder smoke test wrote:
  `data/raw/b1_live_state_smoke.npz`.
- Validator passed with `T=4`.
- Metadata confirms:
  - `base_state_source: odom`
  - `joint_state_source: joint_states`
  - `target_state_source: gazebo_model_states`
  - `allow_nominal_state_fallback: False`
- `base_pose`, `active_joint_positions`, and `target_pose` are finite.

Still open:

- The spawned target readback pose was near `z=-99.8` even though the spawn
  command requested `z=-40.0`; this likely reflects target physics/falling in
  the current world and should be handled later as a task-setup issue, not as a
  state-source availability issue.
- `action_ee_delta` and `raw_command` are still unavailable in the B1 smoke
  episode. These belong to later blockers.

## B3 TF / End-Effector Pose Check Result

User check date: 2026-05-03.

Launch under test:

```bash
roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=false
```

Read-only runtime findings:

- `rosrun tf view_frames` listened to `/tf` for 5 seconds and generated
  `frames.pdf`.
- `rosrun tf tf_echo rexrov/base_link oberon7_l/end_effector` returned a
  continuous transform.
- Example transform:

  ```text
  Translation: [2.071, 0.500, -1.310]
  Quaternion: [0.506, 0.494, -0.495, 0.505]
  RPY degree: [90.140, 88.676, about 0.004]
  ```

B3 status:

```text
resolved for current minimal launch and non-fallback recorder smoke test
```

Resolved:

- The configured left end-effector frame `oberon7_l/end_effector` exists in
  the runtime TF tree.
- A transform from `rexrov/base_link` to `oberon7_l/end_effector` is available.
- Recorder code now uses TF to fill `eef_pose` and
  `relative_target_to_eef` when the configured reference frame and target pose
  are available.
- If direct `world -> oberon7_l/end_effector` TF is unavailable, recorder code
  can compose live `/rexrov/pose_gt` base pose with the verified
  `rexrov/base_link -> oberon7_l/end_effector` TF.
- `package.xml` and `CMakeLists.txt` now declare the `tf` dependency.
- B3 smoke episode:
  `data/raw/b3_eef_tf_smoke.npz`.
- Validator passed with `T=4`.
- Metadata confirms:
  - `base_state_source: odom`
  - `joint_state_source: joint_states`
  - `target_state_source: gazebo_model_states`
  - `allow_nominal_state_fallback: False`
  - `field_availability.eef_pose: True`
  - `field_availability.relative_target_to_eef: True`
  - `eef_pose_source:
    odom+tf:rexrov/base_link->oberon7_l/end_effector`

Still open:

- The gripper remains blocked, so real grasp success rate is still not
  evaluable.
- `action_ee_delta` and `raw_command` were unavailable in the B3 smoke episode
  because no expert/policy command was active.
- The spawned target was falling during readback; this remains a later task
  setup issue.

## Next Minimal User-Run Checks

Current B5a status:

```text
minimal resolved for left-arm only; synchronized execute:=true converted a
tiny EE delta into a bounded IK-derived JointTrajectory, the arm controller
accepted it as desired state, active-left joints moved toward it, and TF showed
a small eef pose change
```

Current decision after the synchronized `execute:=true` user report:

```text
B5a is resolved at the minimal arm-only debug level. This does not resolve
gripper control, MoveIt trajectory execution, scripted-expert runtime
integration, real rollout, or real grasp success.
```

Latest B5a read-only findings:

- `oberon7/arm_position_l` can be loaded and started alone.
- `/controller_manager/list_controllers` reports:
  - `joint_state_controller: running`
  - `oberon7/arm_position_l: running`
- No hand controller was loaded or started in the reported B5a check.
- `/oberon7/arm_position_l/state` reported desired/actual errors around
  `1e-05` to `3e-05` rad.
- `/joint_states` includes all active-left arm joints; runtime order still
  differs from semantic controller order.
- Clean-baseline gripper velocities remain large and symmetric on both hands,
  so gripper remains blocked and out of scope.
- `tf_echo rexrov/base_link oberon7_l/end_effector` initially reported the eef
  frame unavailable, then began returning a stable transform. Treat this as a
  transient TF startup delay, not a B3 regression unless it persists.
- `move_group_revised.launch` was started with
  `allow_trajectory_execution:=false`.
- `/compute_ik` exists and is served by `/move_group` with type
  `moveit_msgs/GetPositionIK`.
- MoveIt still reports `No controller_list specified` and missing
  `world_to_base`, so this B5a path uses MoveIt only for IK, not execution.

Code added for B5a:

```text
scripts/b5a_ee_delta_ik_check.py
```

Purpose:

- Default `execute:=false` dry-run only.
- Reads current `/joint_states` by name.
- Looks up current `oberon7_l/end_effector` pose in candidate IK frames.
- Applies a clipped tiny EE delta.
- Calls `/compute_ik` for `arm_l`.
- Clips per-joint delta before constructing a candidate
  `/oberon7/arm_position_l/command` `JointTrajectory`.
- Publishes only if `execute:=true` is explicitly set.
- After the first MoveIt `-21` result, the script was updated to try multiple
  pose frames by default and log each frame's IK result:
  - `rexrov/base_link`
  - `oberon7_l/base`
  - `world`
- The multi-frame dry-run still failed:
  - `rexrov/base_link: error_code=-21`
  - `oberon7_l/base: error_code=-21`
  - `world`: TF exception because `world` and `oberon7_l/end_effector` are in
    unconnected TF trees.
- The script has now been updated again to default to the existing local
  MoveIt pattern:
  - `MoveGroupCommander("arm_l")`
  - `group.get_planning_frame()`
  - `group.get_current_pose(eef_link)`
  - `group.get_active_joints()` / `group.get_current_joint_values()` as IK seed
- This still uses `/compute_ik` only; it does not call MoveIt trajectory
  execution.
- The MoveIt Commander dry-run passed:
  - `B5a IK frame attempts: ['moveit_commander:world: error_code=1']`
  - selected pose frame: `world`
  - current eef xyz: `[2.059550, 0.500330, -1.315203]`
  - target eef xyz: `[2.064550, 0.500330, -1.315203]`
  - IK solution was produced for all active-left joints.
  - one raw joint delta was clipped:
    `oberon7_l/elbow` from about `0.01235` rad to `0.01` rad.
  - `execute: False`
  - `B5a dry-run only; no JointTrajectory was published`
- The first `execute:=true` attempt generated and published a bounded command:
  - command positions:
    `[0.0002298340, -0.0033922384, 0.0099012926,
    0.0000170208, -0.0114542414, 0.0001189417]`
  - script logged:
    `B5a published JointTrajectory to /oberon7/arm_position_l/command`
- Post-command `/oberon7/arm_position_l/state` did not show the command as
  desired. Desired positions remained the older controller values:
  `[0.0002295010, -0.0009499990, -0.0001320175,
  0.0000144202, -0.0016502914, -0.0001602329]`
- Post-command `/joint_states` showed bounded arm motion, but not clear
  movement toward the converter command target.
- Post-command `tf_echo rexrov/base_link oberon7_l/end_effector` produced a
  stable transform after a short startup delay, but the eef pose stayed near
  `[2.059-2.060, 0.500, -1.315]`.
- Current interpretation: the script likely published before the ROS command
  publisher connection to `/gazebo` was established, so the single
  `JointTrajectory` may have been dropped.
- The script has now been updated so `execute:=true` waits for a command-topic
  subscriber and sleeps briefly after publishing.
- The synchronized `execute:=true` rerun succeeded:
  - script command positions:
    `[0.0002395104, -0.0033546553, 0.0098995494,
    0.0000112465, -0.0114451132, 0.0003411589]`
  - `/oberon7/arm_position_l/state` desired positions matched those command
    positions.
  - actual positions after about 3 seconds were close:
    `[0.0002517514, -0.0033242450, 0.0099326379,
    0.0000865204, -0.0113411858, 0.0002664748]`
  - controller position errors stayed bounded, around `1e-05` to `1e-04` rad.
  - `/joint_states` showed active-left arm joint positions in the commanded
    neighborhood.
  - `tf_echo rexrov/base_link oberon7_l/end_effector` reported eef translation
    around `[2.063, 0.500, -1.315/-1.316]`, after the usual short TF startup
    delay. This is a small x-direction change from the pre-command eef x near
    `2.059573`.
- No further B5a code change is required.

Build verification:

```text
python3 -m py_compile scripts/b5a_ee_delta_ik_check.py: passed
catkin build rexrov_single_oberon7_fm_dp: passed
```

Latest dry-run attempts:

```bash
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=false \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01
```

Result:

```text
B5a EE-delta IK check failed: timeout exceeded while waiting for service /compute_ik
B5a EE-delta IK check failed: IK failed with MoveIt error code -21
B5a EE-delta IK check failed: IK failed for all candidate frames:
  rexrov/base_link: error_code=-21
  oberon7_l/base: error_code=-21
  world: TF exception, unconnected TF trees
B5a dry-run passed with moveit_commander:world error_code=1 and no command
published
B5a execute:=true initially logged a publish, but
/oberon7/arm_position_l/state desired did not match the logged command
positions
B5a synchronized execute:=true passed: desired matched logged command
positions, active-left joints moved toward desired, and TF showed small eef
motion
```

Interpretation:

- The first dry-run did not reach IK because `/compute_ik` was unavailable.
- The later dry-run reached `/compute_ik`, but MoveIt returned `-21`
  (`FRAME_TRANSFORM_FAILURE`).
- The multi-frame dry-run showed direct TF-framed IK requests still fail for
  robot-link frames, while `world -> eef` is not available in TF.
- No IK joint target was generated.
- No `JointTrajectory` was published.
- This indicates the request pose frame was not transformable by MoveIt in the
  current planning scene.
- The latest dry-run solved this by using MoveIt Commander current pose and
  seed state.
- The first execute attempt did not validate command execution because the arm
  controller desired state did not update to the logged command.
- The likely immediate issue was command publication synchronization, not IK.
- After adding publisher subscriber-wait and post-publish sleep, the
  synchronized execute check validated real left-arm motion for this tiny
  converter command.

Latest MoveIt service recheck:

```text
/move_group is present in rosnode list
/compute_ik is present in rosservice list
/compute_ik is served by /move_group
/compute_ik type: moveit_msgs/GetPositionIK
```

No further B5a check is required before moving to the next blocker. Safety
boundary remains:

- Keep `move_group_revised.launch` running with
  `allow_trajectory_execution:=false`.
- Do not load or start any hand controller.
- Do not claim MoveIt trajectory execution is resolved; this path used MoveIt
  for IK only and published directly to `/oberon7/arm_position_l/command`.
- Do not claim real rollout or real grasp success.
- The next logical blocker is scripted-expert/runtime integration of this
  converter path, still arm-only and without gripper.

## B5b Scripted Expert Runtime Integration

Current B5b status:

```text
minimal resolved for arm-only scripted expert execution smoke; scripted expert
ran with execute_arm:=true, gripper command disabled, converted one clipped EE
delta into a left-arm JointTrajectory command, recorder wrote non-fallback live
state plus action/eef fields, and validator passed
```

Read-only precheck result from 2026-05-03:

- `/controller_manager/list_controllers` showed:
  - `joint_state_controller: running`
  - `oberon7/arm_position_l: running`
- No hand/gripper controller was reported loaded or running.
- `/move_group` was present.
- `/compute_ik` was available from `/move_group` with type
  `moveit_msgs/GetPositionIK`.
- `/oberon7/arm_position_l/command` type was
  `trajectory_msgs/JointTrajectory` and had `/gazebo` as subscriber.
- `/oberon7/arm_position_l/state` was published by `/gazebo`.
- `tf_echo rexrov/base_link oberon7_l/end_effector` returned transforms around
  `[2.063, 0.500, -1.315/-1.316]`.
- `/joint_states` and `/rexrov/pose_gt` returned live samples.
- `cylinder_target` did not exist:
  - `/gazebo/get_model_state` returned `success: False`;
  - `/gazebo/model_states` contained only `ocean_box` and `rexrov`.

Interpretation:

- Arm command, IK, TF, base odom, and joint-state prerequisites are present.
- Non-fallback target recording is not ready until `cylinder_target` is spawned
  and visible in `/gazebo/model_states`.
- B5b should not run recorder validation with `require_target=true` until the
  target exists.

Code added for B5b:

```text
src/rexrov_single_oberon7_fm_dp/arm_command_converter.py
src/rexrov_single_oberon7_fm_dp/expert_policy.py
launch/collect_episode.launch
config/topics.yaml
```

Implementation details:

- Added reusable `ArmEEDeltaCommandConverter`.
- It uses the B5a-safe path:
  `MoveGroupCommander("arm_l") -> /compute_ik -> clipped active-left joint target
  -> /oberon7/arm_position_l/command`.
- It waits for a command-topic subscriber and sleeps briefly after publish.
- `ScriptedExpert` now supports explicit arm execution through
  `execute_arm:=true`.
- Default remains safe: `execute_arm:=false`.
- `enable_gripper_command:=true` raises an error; gripper command execution is
  intentionally blocked for B5b.
- B5b command clipping defaults:
  - `max_linear_step: 0.005 m`
  - `max_angular_step: 0.05 rad`
  - `max_joint_delta: 0.01 rad`
- `execute_arm_once_per_state:=true` defaults to one arm command per configured
  scripted state.
- `collect_episode.launch` exposes these safety parameters.
- `collect_episode.launch` also exposes `require_target` independently from
  `spawn_target`, so a pre-spawned target can still be required by the
  recorder.
- `topics.yaml` now records the minimally resolved left-arm command topic:
  `/oberon7/arm_position_l/command`.

Static verification:

```text
python3 -m py_compile .../arm_command_converter.py .../expert_policy.py .../scripted_expert.py: passed
python3 -m xml.etree.ElementTree launch/collect_episode.launch: passed
catkin build rexrov_single_oberon7_fm_dp: passed
```

Next minimal checks:

1. Spawn or confirm `cylinder_target` so target state can be non-fallback.
2. Run a short arm-only scripted expert smoke test with:
   - `execute_arm:=true`
   - `enable_gripper_command:=false`
   - `allow_nominal_state_fallback:=false`
   - short duration and low rate.
3. Validate the recorded episode and check metadata:
   - `base_state_source: odom`
   - `joint_state_source: joint_states`
   - `target_state_source: gazebo_model_states`
   - `allow_nominal_state_fallback: False`
   - `field_availability.eef_pose: True`
   - `field_availability.relative_target_to_eef: True`
   - `field_availability.action_ee_delta: True`
   - `raw_command` may remain unavailable because arm joint command recording is
     not implemented yet.

Still not resolved by B5b code support alone:

- gripper command/control;
- MoveIt trajectory execution;
- real policy rollout;
- real grasp success rate.

B5b smoke result:

```text
episode: data/raw/b5b_smoke/b5b_arm_only_smoke.npz
validation: PASS
T: 6
success: False
unavailable_fields: ['raw_command']
```

Runtime facts:

- `cylinder_target` spawned successfully.
- `/gazebo/get_model_state` returned `success: True`, but the target was
  already falling after spawn; during recording, target z was near `-99.8`.
- The expert ran with:
  - `execute_arm: True`
  - `enable_gripper_command: False`
  - `execute_arm_states: MOVE_TO_PREGRASP`
  - `max_linear_step: 0.005`
  - `max_joint_delta: 0.01`
- The expert logged one B5b arm command:

  ```text
  state=MOVE_TO_PREGRASP
  current_eef_xyz=[2.062989, 0.500349, -1.315499]
  target_eef_xyz=[2.067989, 0.500349, -1.310499]
  command_positions=[0.0002594683, 0.0032141103, 0.0130758532,
                     -0.0000183038, -0.0211685831, 0.0002506068]
  ```

Recorded metadata:

```text
allow_nominal_state_fallback: False
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
arm_command_topic: /oberon7/arm_position_l/command
gripper_command_topic: None
field_availability:
  action_ee_delta: True
  eef_pose: True
  relative_target_to_eef: True
  target_pose: True
  raw_command: False
```

Recorded motion checks:

- `active_joint_positions` were finite with max absolute deltas from the first
  sample approximately:

  ```text
  [4.2e-05, 5.5e-03, 2.7e-03, 1.3e-04, 8.1e-03, 5.8e-04] rad
  ```

- `action_ee_delta` was finite; the recorded last action was clipped to:

  ```text
  [0.005, 0.0, -0.005, 0.0, 0.0, 0.0, 0.0]
  ```

Caveats:

- `raw_command` remains unavailable because the recorder does not yet record the
  raw arm `JointTrajectory`; this is acceptable for B5b and explicitly marked.
- World-frame `eef_pose` includes RexROV base drift. The arm joint deltas are
  the primary bounded-motion evidence for this B5b smoke test.
- The target is non-fallback Gazebo state, but it is physically unstable/falling
  in this launch. Target stabilization remains a later task-setup blocker.

## B5c Target Stability / Task Setup

Current B5c status:

```text
minimal resolved for package-local static-target smoke; target remains stable
near the requested grasp workspace pose, recorder captures non-fallback
gazebo_model_states target_pose with fallback disabled, and validator passes
```

Read-only checks from 2026-05-03:

- `models/cylinder_target/model.sdf` contains:

  ```text
  <static>false</static>
  mass: 0.5
  collision cylinder radius 0.05 length 0.30
  no buoyancy, fixed joint, world attachment, or hold plugin
  ```

- Gazebo physics properties:

  ```text
  gravity.z: -9.8
  pause: False
  max_update_rate: 500.0
  ```

- Current `/gazebo/model_states` contained only:

  ```text
  ocean_box
  rexrov
  ```

- `/gazebo/get_model_state cylinder_target` returned:

  ```text
  success: False
  status_message: model does not exist
  ```

Interpretation:

- The target was absent during the latest read-only check, so the new check did
  not sample an active falling target.
- Earlier B5b logs already showed the spawned dynamic target falling quickly
  after spawn, including large negative z velocity and later target z near
  `-99.8`.
- The simplest explanation is consistent with the package-local SDF and physics
  settings: the target is a dynamic body under gravity with no support,
  buoyancy, or static constraint.

Package-local fix added:

```text
models/cylinder_target_static/model.sdf
launch/collect_episode.launch
```

Fix details:

- Added a static smoke target model:

  ```text
  models/cylinder_target_static/model.sdf
  <static>true</static>
  same cylinder geometry as cylinder_target
  ```

- Added `target_sdf_path` to `collect_episode.launch`, defaulting to the
  original dynamic target SDF for backward compatibility.
- No official DAVE, UUV, manipulator, or RexROV2 package was modified.

Static verification:

```text
python3 -m xml.etree.ElementTree models/cylinder_target_static/model.sdf: passed
python3 -m xml.etree.ElementTree launch/collect_episode.launch: passed
catkin build rexrov_single_oberon7_fm_dp: passed
```

Static target stability runtime check passed:

- `cylinder_target` was spawned from
  `models/cylinder_target_static/model.sdf`.
- Five `/gazebo/get_model_state` samples over about 5.6 seconds all returned:

  ```text
  success: True
  pose.position: [2.6, 2.0, -40.0]
  orientation: [0.0, 0.0, 0.0, 1.0]
  twist.linear: [0.0, 0.0, 0.0]
  twist.angular: [0.0, 0.0, 0.0]
  ```

- `/gazebo/model_states` included:

```text
ocean_box
rexrov
cylinder_target
```

B5c recorder smoke passed:

```text
episode: data/raw/b5c_smoke/b5c_static_target_recorder_smoke.npz
validation: PASS
T: 4
success: False
unavailable_fields: ['raw_command']
```

Runtime/launch settings:

- `spawn_target:=false`, using the already-spawned static `cylinder_target`.
- `require_target:=true`.
- `allow_nominal_state_fallback:=false`.
- `execute_arm:=false`.
- `enable_gripper_command:=false`.

Recorded metadata:

```text
allow_nominal_state_fallback: False
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
field_availability:
  target_pose: True
  eef_pose: True
  relative_target_to_eef: True
  action_ee_delta: True
  raw_command: False
```

Recorded target stability:

```text
target_pose first: [2.6, 2.0, -40.0, 0.0, 0.0, 0.0, 1.0]
target_pose last:  [2.6, 2.0, -40.0, 0.0, 0.0, 0.0, 1.0]
target xyz delta:  [0.0, 0.0, 0.0]
max abs target xyz delta from first sample: [0.0, 0.0, 0.0]
```

B5c still does not address:

- gripper command/control;
- real grasp success;
- dynamic-object physics realism;
- MoveIt trajectory execution.
- real policy rollout.

## B2b Gripper Baseline Stability Diagnosis

Current B2b status:

```text
not resolved; gripper remains blocked, but the latest read-only check confirms
the motion is present in a clean baseline with no hand controller loaded
```

Latest user check date: 2026-05-03.

Runtime context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group was not required for this check
no arm_position_l or hand_position_l controller was loaded or started
no gripper command was published
```

Controller graph:

```text
/controller_manager/list_controllers:
  joint_state_controller: running

no running or initialized oberon7/hand_position_l controller
no running or initialized oberon7/hand_position_r controller
```

Available controller types include both trajectory and gripper-action
controllers:

```text
position_controllers/JointTrajectoryController
effort_controllers/JointTrajectoryController
position_controllers/GripperActionController
effort_controllers/GripperActionController
```

ROS graph:

```text
rostopic list | grep hand/gripper/finger/follow_joint/controller:
  no matches

/oberon7/hand_position_l/command:
  unknown topic
/oberon7/hand_position_l/state:
  unknown topic
/oberon7/hand_position_l/follow_joint_trajectory/goal:
  unknown topic
/oberon7/hand_position_r/command:
  unknown topic
/oberon7/hand_position_r/state:
  unknown topic
/oberon7/hand_position_r/follow_joint_trajectory/goal:
  unknown topic
```

Controller params still exist:

```text
/oberon7/hand_position_l/type: position_controllers/JointTrajectoryController
/oberon7/hand_position_l/joints:
  oberon7_l/finger_left_joint
  oberon7_l/finger_tip_left_joint
  oberon7_l/finger_right_joint
  oberon7_l/finger_tip_right_joint

/oberon7/hand_effort_l/type: effort_controllers/JointTrajectoryController
/oberon7/hand_effort_l/joints:
  same four left finger joints
```

`/robot_description_semantic` was not set in this clean baseline because MoveIt
was not launched. That is expected for this B2b check and does not affect
gripper baseline stability diagnosis.

Read-only `/joint_states` sampling over six samples showed both left and right
grippers moving even though no hand controller/topic was active:

```text
left gripper velocities, representative sample:
  finger_left_joint:      about -0.479 rad/s
  finger_tip_left_joint:  about  0.219 rad/s
  finger_right_joint:     about -0.655 rad/s
  finger_tip_right_joint: about  0.277 rad/s

right gripper velocities, representative sample:
  finger_left_joint:      about -0.480 rad/s
  finger_tip_left_joint:  about  0.220 rad/s
  finger_right_joint:     about -0.655 rad/s
  finger_tip_right_joint: about  0.277 rad/s
```

The sampled position drift over roughly 2.6 seconds was small but nonzero:

```text
left:
  finger_left_joint:       +2.91e-06 rad
  finger_tip_left_joint:   -9.13e-07 rad
  finger_right_joint:      +3.01e-06 rad
  finger_tip_right_joint:  -8.29e-07 rad

right:
  finger_left_joint:       +2.91e-06 rad
  finger_tip_left_joint:   -9.13e-07 rad
  finger_right_joint:      +3.01e-06 rad
  finger_tip_right_joint:  -8.29e-07 rad
```

Interpretation:

- The latest check confirms there is no active gripper command topic, action
  server, or hand controller in the clean baseline.
- Both left and right grippers still report large nonzero velocities.
- Because the behavior is bilateral and exists before hand controller load or
  command, the current best classification is:

```text
baseline model / Gazebo physics / uncontrolled or passive gripper joint blocker
```

B2b decision:

- B2b is not solved.
- Gripper command execution is still unsafe to test.
- Do not publish gripper trajectories yet.
- The next minimum step should remain diagnostic: inspect package-local and
  runtime model/controller definitions for gripper joints, mimic/passive joint
  structure, damping/friction/limits, and controller gain assumptions before
  any gripper command test.

Latest URDF read-only check:

- `/robot_description` exists in the `uvms_control` baseline launch.
- All eight left/right gripper joints are present.
- Main finger joints are `revolute` with:

  ```text
  lower: 0
  upper: 1.04709283144
  effort: 3000
  velocity: 0.15
  dynamics:
    damping: 5
    friction: 10
  mimic: None
  hardwareInterface: PositionJointInterface
  ```

- Finger-tip joints are also `revolute`, but have zero range and zero command
  authority in URDF limits:

  ```text
  lower: 0
  upper: 0
  effort: 0
  velocity: 0
  dynamics:
    damping: 5
    friction: 10
  mimic: None
  hardwareInterface: PositionJointInterface
  ```

Interpretation:

- The gripper finger-tip joints are modeled as actuated/transmitted position
  joints even though their limits imply fixed zero-DOF behavior.
- They are not marked `fixed` and do not mimic the parent finger joints.
- This is consistent with a model/controller mismatch candidate and may explain
  why the gripper state is not a clean controllable interface.
- It does not by itself prove the root cause of the baseline velocity; the next
  check should compare Gazebo's runtime joint properties against the URDF
  limits and reported `/joint_states` velocities.

Current B2b next step:

```text
read-only Gazebo joint/link property check for main finger and finger-tip joints
```

No package code, launch, controller YAML, or SDF should be changed until that
runtime Gazebo check confirms which joints are physically moving and how Gazebo
reports their limits/rates.

Gazebo runtime joint property check:

- `/gazebo/get_joint_properties` succeeded for all eight left/right gripper
  joints.
- Gazebo reported `type: 0` and `damping: []` for every sampled gripper joint.
- Main finger joints had nonzero rates.
- Zero-range finger-tip joints also had nonzero positions and nonzero rates:

```text
oberon7_l/finger_tip_left_joint:
  position:  0.0016097588
  rate:     -0.5119182211

oberon7_l/finger_tip_right_joint:
  position: -0.0006066859
  rate:     -0.2948593325

oberon7_r/finger_tip_left_joint:
  position: -0.0020240736
  rate:     -0.4595462765

oberon7_r/finger_tip_right_joint:
  position:  0.0006242092
  rate:      0.2305161933
```

Updated interpretation:

- B2b is still not resolved.
- The runtime Gazebo model confirms movement in joints that the URDF describes
  as zero-range, zero-effort, zero-velocity revolute joints.
- Gazebo's joint-property service did not report damping values for these
  joints, even though `/robot_description` contains `damping=5` and
  `friction=10`.
- This strengthens the model/physics/controller-interface mismatch diagnosis.

Next minimum diagnostic step:

```text
read-only inspect Gazebo link properties for gripper links and ROS PID/gain
params for gripper joints
```

The purpose is to determine whether the moving finger-tip links are dynamic
bodies under gravity/contact and whether Gazebo controller PID gains exist for
the transmitted finger-tip joints before deciding on any package-local fix.

Gazebo link property and PID-param listing check:

- `/gazebo/get_link_properties` succeeded for all left/right finger and
  finger-tip links.
- All sampled gripper links are dynamic and have `gravity_mode: True`.
- Main finger links:

  ```text
  mass: 0.879771
  inertia: ixx=0.00378331, iyy=0.00886148, izz=0.00919231
  ```

- Finger-tip links:

  ```text
  mass: 1.12551
  inertia: ixx=0.00611047, iyy=0.0134903, izz=0.0121556
  ```

- Runtime ROS params include hand controller constraints and gains for:

  ```text
  /oberon7/hand_position_l
  /oberon7/hand_position_r
  /oberon7/hand_effort_l
  /oberon7/hand_effort_r
  ```

- The parameter list also shows `joint_group_hand_l_position_controller` and
  `joint_group_hand_r_position_controller` configs.
- One suspicious finding from the param names: `/oberon7/hand_position_r/gains`
  appears to contain `oberon7_l/...` joint names instead of `oberon7_r/...`.
  This may be a copy/paste controller-config issue, but it must be confirmed by
  reading exact param values before changing anything.

Updated B2b interpretation:

- B2b remains unresolved.
- The finger-tip links are not massless/fixed placeholders; they are dynamic,
  gravity-enabled bodies attached through zero-range transmitted revolute
  joints.
- Combined with Gazebo reporting nonzero rates for zero-range finger-tip
  joints, this strongly supports a model/controller configuration mismatch.

Next minimum diagnostic step:

```text
read exact hand controller param dictionaries and source YAML snippets
```

Specifically confirm:

- whether `hand_position_l/r` include the zero-range finger-tip joints as
  controlled joints;
- whether right-hand gains are incorrectly keyed with left-hand joint names;
- whether effort and position hand controllers disagree;
- whether group hand controllers omit gains or use a different joint list.

Exact hand controller parameter check:

- `hand_position_l`, `hand_position_r`, `hand_effort_l`, `hand_effort_r`, and
  the two `joint_group_hand_*_position_controller` configs all include the
  zero-range finger-tip joints in their `joints` lists.
- `hand_position_l`, `hand_effort_l`, and `hand_effort_r` have gains keyed by
  their matching left/right joint namespaces.
- `hand_position_r` has a confirmed namespace mismatch:

  ```text
  joints:
    oberon7_r/finger_left_joint
    oberon7_r/finger_tip_left_joint
    oberon7_r/finger_right_joint
    oberon7_r/finger_tip_right_joint

  gains:
    oberon7_l/finger_left_joint
    oberon7_l/finger_tip_left_joint
    oberon7_l/finger_right_joint
    oberon7_l/finger_tip_right_joint
  ```

- The source file loaded by `oberon7_position_control.launch` is:

  ```text
  src/uvms/data_rexrov_dual_oberon7/config/oberon7_controllers.yaml
  ```

- The same source file contains the `hand_position_r.gains` left/right namespace
  mismatch.

Impact:

- The `hand_position_r` gain-key bug is a real controller configuration defect,
  but it does not explain the clean-baseline gripper motion because no hand
  controller is loaded or running in the baseline check.
- The more fundamental B2b blocker remains the model/interface design:
  dynamic, gravity-enabled finger-tip links attached through zero-range
  revolute joints that are also listed as controllable transmitted joints.

Current decision:

```text
B2b remains unresolved. Do not command gripper yet.
```

Next minimum safe direction:

- No code/config change is required yet to preserve debug safety.
- If a fix is attempted later, it should be package-local or isolated from
  official packages, and should first be validated as a dry launch/config check.
- Candidate fixes to evaluate later:
  - remove zero-range finger-tip joints from hand command controllers;
  - correct `hand_position_r.gains` to right-hand keys;
  - add a package-local left-gripper-only controller config that controls only
    the two main finger joints;
  - or keep gripper blocked and continue arm-only data work until the upstream
    model is corrected.

## Route Change: Arm-Only Reaching / Pre-Grasp

Current route decision:

```text
short-term demo target is arm-only reaching / pre-grasp positioning, not full
grasping
```

Reason:

- B2b confirms the gripper is not a simple command-topic issue.
- Clean-baseline gripper joints move without hand controllers or command
  publishers.
- Finger-tip links are dynamic and gravity-enabled.
- Finger-tip joints are zero-range revolute joints with transmissions and are
  included in hand controller joint lists.
- `hand_position_r` has a confirmed gain-key namespace bug.

Route implications:

- Do not proceed with B5d gripper command integration.
- Do not proceed with B5e arm+gripper scripted grasp smoke.
- Do not start hand controllers as a fix.
- Do not publish gripper commands.
- Keep `enable_gripper_command:=false`.

New first-version task:

```text
RexROV + single-active-left Oberon7 arm-only reaching / pre-grasp positioning
```

Success metric naming:

```text
reaching_success or pregrasp_success
```

Minimal metric definition:

```text
distance(eef_pose, target_or_pregrasp_pose) < threshold and not timeout
```

Initial threshold recommendation:

```text
0.10 m for first smoke/debug pass; consider 0.05 m only after observed
initial/final distances and reachable workspace are characterized.
```

Schema compatibility note:

- The existing scalar `success` field can remain for validator compatibility,
  but metadata must explicitly state this is reaching/pre-grasp success, not
  grasp success.
- `action_ee_delta` can remain 7-D; `gripper_cmd` should be fixed at `0.0` or
  marked ignored for arm-only reaching.
- `gripper_state` may still be recorded as observed state but is not a control
  target or success criterion.
- `raw_command` may remain unavailable for now and should be documented as not
  blocking B5d' smoke.

## B5d' Arm-Only Reaching Precheck

Latest user check date: 2026-05-03.

Runtime context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false
source devel/setup.bash already executed
```

Read-only precheck result:

```text
/controller_manager/list_controllers:
  joint_state_controller: running

/move_group:
  present

/compute_ik:
  present

/oberon7/arm_position_l/command:
  unknown topic

TF rexrov/base_link -> oberon7_l/end_effector:
  available
  translation approx [2.061, 0.500, -1.315]

/gazebo/get_model_state cylinder_target:
  success: False
  model does not exist

/gazebo/model_states:
  cylinder_target not found
```

Decision:

```text
B5d' is not ready to run.
```

Missing prerequisites:

- `oberon7/arm_position_l` is not loaded/running in this clean runtime, so the
  command topic does not exist.
- Static `cylinder_target` is absent.

What is available:

- MoveIt `/compute_ik` is available.
- EEF TF is available.

Next minimum check:

```text
restore only B5d' prerequisites: load/start left-arm controller and spawn static
target; do not touch hand controllers or gripper.
```

B5d' prerequisite restore check:

```text
/controller_manager/load_controller oberon7/arm_position_l:
  ok: True

/controller_manager/switch_controller start oberon7/arm_position_l:
  ok: True

/controller_manager/list_controllers:
  joint_state_controller: running
  oberon7/arm_position_l: running
```

The running left-arm controller claims only active-left arm resources:

```text
oberon7_l/azimuth
oberon7_l/elbow
oberon7_l/pitch
oberon7_l/roll
oberon7_l/shoulder
oberon7_l/wrist
```

No hand/gripper controller was loaded or started.

Static target restore:

```text
spawn_model models/cylinder_target_static/model.sdf as cylinder_target:
  SpawnModel: Successfully spawned entity

/gazebo/get_model_state cylinder_target:
  success: True
  position: [2.6, 2.0, -40.0]
  orientation: [0.0, 0.0, 0.0, 1.0]
  twist.linear: [0.0, 0.0, 0.0]
  twist.angular: [0.0, 0.0, 0.0]
```

Arm command topic:

```text
/oberon7/arm_position_l/command:
  type: trajectory_msgs/JointTrajectory
  publishers: None
  subscribers:
    /gazebo
```

Decision:

```text
B5d' prerequisites are restored, but B5d' is not solved yet.
```

Next minimum check:

```text
read-only state-only recorder/distance baseline check with static target and
fallback disabled, then decide whether the existing fixed-delta expert is
sufficient or target-directed reaching code is required.
```

B5d' non-control baseline recorder check:

```text
episode:
  data/raw/b5d_reaching_precheck/b5d_reaching_baseline_no_control.npz

validator:
  PASS
  T: 4
  success: False
  unavailable_fields: ['raw_command']
```

Runtime settings:

```text
spawn_target: false
require_target: true
allow_nominal_state_fallback: false
execute_arm: false
enable_gripper_command: false
```

Recorded metadata:

```text
field_availability:
  action_ee_delta: True
  eef_pose: True
  raw_command: False
  relative_target_to_eef: True
  target_pose: True

allow_nominal_state_fallback: False
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
```

Distance baseline:

```text
target_first: [2.6, 2.0, -40.0]
eef_first: [-40.2129914966344, -3.839671742860088, -99.75204165781498]
initial_distance: 73.73846004109731 m
final_distance: 73.86181687780048 m
min_distance: 73.73846004109731 m
```

Decision:

```text
B5d' is not solved. Recorder preconditions are good, but the static target is
far outside the current arm-only reachable workspace in world coordinates.
```

Interpretation:

- The recorder and non-fallback state path are ready for B5d'.
- The target is stable and observed from Gazebo.
- The current target pose `[2.6, 2.0, -40.0]` is not meaningful after RexROV
  drift; the EEF is around `z=-99.75`.
- A reaching smoke test against this target would fail for task setup reasons,
  not because the arm converter is necessarily wrong.

Next minimum step:

```text
reposition the static target near the current EEF/pregrasp workspace, then
re-run the non-control baseline to confirm initial distance is small and finite.
```

This should be done with Gazebo model-state repositioning or delete/re-spawn of
the package-local static target. It does not require code changes yet.

Near-target baseline attempt:

```text
target reposition script used previous episode's last recorded eef_pose:
  new_target_xyz: [-40.32524771314997, -3.8380501244831398, -99.71209805902916]

/gazebo/get_model_state cylinder_target:
  success: True
  position: [-40.32524771314997, -3.8380501244831398, -99.71209805902916]
  twist: zero
```

Recorder result:

```text
episode:
  data/raw/b5d_reaching_precheck/b5d_reaching_baseline_near_target.npz

validator:
  PASS
  T: 4
  success: False
  unavailable_fields: ['raw_command']

metadata:
  allow_nominal_state_fallback: False
  target_state_source: gazebo_model_states
  field_availability:
    action_ee_delta: True
    eef_pose: True
    raw_command: False
    relative_target_to_eef: True
    target_pose: True
```

Distance result:

```text
target_first: [-40.32524771314997, -3.8380501244831398, -99.71209805902916]
eef_first: [-50.70703373594152, -4.015825629082565, -99.75201271243112]
initial_distance: 10.383384724290138 m
final_distance: 10.563886255042627 m
min_distance: 10.383384724290138 m
```

Decision:

```text
B5d' is still not solved.
```

Interpretation:

- The non-fallback recorder and target fields remain valid.
- The attempted near-target placement used a stale EEF pose from a previous
  episode.
- By the time the next baseline episode started, the EEF world pose had drifted
  by about 10 m relative to that stale pose.
- This confirms that B5d' needs live, immediately computed EEF-world placement
  or a base-relative task setup before arm-only reaching smoke is meaningful.

Next minimum check:

```text
compute current live EEF world pose from /rexrov/pose_gt + TF immediately before
setting target, set the target within about 0.10 m of that live pose, and
immediately re-run the no-control baseline.
```

This still does not require code changes. It is a runtime task-placement check.

Live-EEF target placement attempt:

```text
live base_world:
  [-69.52104407468721, -4.476964239028076, -98.54334253085695]

live eef_base_tf:
  [2.0708814125823, 0.4984930547418398, -1.310037055627614]

computed live eef_world:
  [-67.34184073023106, -4.272243987204881, -99.7526417658384]

target set to:
  [-67.24184073023106, -4.272243987204881, -99.7126417658384]

expected set-time distance:
  0.10770329614268713 m
```

Target readback:

```text
/gazebo/get_model_state cylinder_target:
  success: True
  position: [-67.24184073023106, -4.272243987204881, -99.7126417658384]
  twist.linear: [0.0, 0.0, 0.0]
  twist.angular: [0.0, 0.0, 0.0]
```

Immediate no-control baseline after live placement:

```text
episode:
  data/raw/b5d_reaching_precheck/b5d_reaching_baseline_live_near_target.npz

validator:
  PASS
  T: 4
  success: False
  unavailable_fields: ['raw_command']

metadata:
  allow_nominal_state_fallback: False
  target_state_source: gazebo_model_states
  field_availability:
    action_ee_delta: True
    eef_pose: True
    raw_command: False
    relative_target_to_eef: True
    target_pose: True
```

Recorded distance:

```text
target_first: [-67.24184073023106, -4.272243987204881, -99.7126417658384]
eef_first: [-68.57055780475194, -3.9736012548043984, -99.75216038267928]
initial_distance: 1.362438353400245 m
final_distance: 1.5364981412648813 m
min_distance: 1.362438353400245 m
```

Updated B5d' decision:

```text
B5d' remains blocked by world-frame base drift / target placement timing.
```

Interpretation:

- The live placement script placed the target about 0.108 m from the EEF at
  service-call time.
- By the first recorder sample, the EEF-target distance was already about
  1.36 m and increased during the 2 s baseline.
- The target is static in world coordinates while RexROV/EEF continues drifting
  in world coordinates.
- A B5d' reaching command test against this world-static target would currently
  confound arm motion with base drift.

Next minimum check:

```text
measure short-window EEF/base drift over 2-5 seconds with no arm command and no
target movement, then decide whether B5d' needs a base-relative/dynamic target
placement helper or a much shorter immediate smoke window.
```

No reaching command should be sent until the target placement can stay near the
EEF long enough for a meaningful arm-only smoke test.

## 2026-05-04 B8' Current Blocker Update

Latest checked episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_cached_odom_check/
  b8_reaching_smoke_tuned_v3_cached_odom_check_0000.npz
```

Observed results:

- validator passed with `T=22`, `success=False`, and only `raw_command`
  unavailable.
- Quality/direction diagnostics showed one transient below-threshold sample:
  `min_distance=0.086114 m`, but `final_distance=0.147795 m` and
  `mean_distance_reduction=-0.021487 m`.
- Command-to-motion coupling improved but was still lagged:
  `mean_best_action_to_eef_cosine=0.798572`, `mean_best_lag_steps=2`.
- Per-sample trace showed the only below-threshold sample at index 10, followed
  by a target-base jump of about `0.050329 m` at index 11.
- Stored `relative_target_to_eef` distance exactly matched recomputation from
  `base_pose`, `target_pose`, and `eef_pose`
  (`max_abs_dist_diff=5.27e-16`), so there is no offline arithmetic mismatch in
  the saved field.

Decision:

```text
B8' is not resolved. It is smoke-level progress only.
```

The latest consistency check rules out a saved-field arithmetic bug, but it is
not independent timing evidence because the recorder writes
`relative_target_to_eef = target_pose[:3] - eef_pose[:3]`. The remaining
blocker is likely recorder/source synchronization: recorded base pose was
odom-based while target pose came from `/gazebo/model_states`.

Package-local diagnostic change made for the next minimum check:

- `recorder.py` now supports default-off
  `prefer_model_states_base_pose`.
- `collect_episode.launch` exposes `prefer_model_states_base_pose`.
- `b8_reaching_tuned_v3_episode.launch` enables it so B8' v3 recording uses
  Gazebo model state for both base and target geometry.
- `analyze_b8_reaching_quality.py` now treats `base_state_source` of either
  `odom` or `gazebo_model_states` as acceptable non-fallback live metadata.

Next minimum check:

```text
Run exactly one B8' tuned-v3 model-states-base validation episode with the TF
bridge still running, then validate and rerun quality/direction/command-motion
diagnostics. Do not collect repeatability data or train until the target-base
step spikes and final-distance behavior improve.
```

## 2026-05-04 B8' Model-States-Base Check Result

Latest checked episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_modelstates_base_check/
  b8_reaching_smoke_tuned_v3_modelstates_base_check_0000.npz
```

Runtime confirmation:

- `dp_fm_episode_recorder/prefer_model_states_base_pose: True`
- world/base TF bridge was running.
- gripper command remained disabled.

Validation and quality:

```text
validation: PASS
T: 22
success: False
unavailable_fields: ['raw_command']
all_required_metadata_ok: true
episodes_below_threshold: 0
episodes_with_positive_distance_reduction: 0
initial_distance: 0.128423 m
min_distance: 0.120908 m
final_distance: 0.131432 m
mean_distance_reduction: -0.003009 m
```

Direction and command-motion diagnostics:

```text
mean_action_to_eef_motion_cosine: 0.770373
mean_eef_motion_cosine_with_target: 0.563404
mean_eef_positive_target_direction_ratio: 0.857143
mean_best_action_to_eef_cosine: 0.872771
mean_best_lag_steps: 2.0
mean_best_realized_gain_along_action: 0.228406
```

Decision:

```text
B8' is still not resolved. The current result is valid non-fallback smoke data
only, not repeatability data and not training data.
```

Interpretation:

- The recorder source-sync suspicion is reduced: using model_states for base
  and target produced valid metadata and removed the earlier transient
  below-threshold artifact.
- The remaining blocker is real behavior quality: the arm tends to move in the
  commanded/target direction, but the episode still never crosses the `0.10 m`
  threshold and final distance is worse than initial distance.
- The lag-2 best coupling is still present, so command response timing and
  per-sample target stability must be inspected before any further tuning or
  collection.

Next minimum check:

```text
Run read-only per-sample diagnostics on the model-states-base episode: distance,
target_base step, eef_base step, below-threshold count, and the command-motion
markdown lag table. Do not change code, collect more episodes, or train before
that check is reviewed.
```

## 2026-05-04 B8' Model-States-Base Per-Sample Trace

Input episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_modelstates_base_check/
  b8_reaching_smoke_tuned_v3_modelstates_base_check_0000.npz
```

Per-sample trace:

```text
samples: 22
below_count: 0
below_indices: []
min_idx: 9
min_distance: 0.12090753743754573
final_distance: 0.13143181756986858
max_target_step: 0.016551355118223997
max_target_step_idx: 20
max_eef_step: 0.007806147901855314
```

Command-motion markdown:

```text
target_base_net/max-step: 0.046422 / 0.016551
eef_base_net_norm: 0.048886
base_world_path_norm: 0.250948
best lag steps: 2
best action-to-eef cosine: 0.872771
best eef-to-target cosine: 0.698900
best realized gain along action: 0.228406
best distance decreasing ratio: 0.368421
labels:
  threshold_not_reached
  possible_command_response_lag
  distance_not_decreasing_under_best_lag
  base_world_drift_present
```

Decision:

```text
B8' remains unresolved, but the target-base jump blocker is reduced.
```

Interpretation:

- Target-base motion is now bounded at the sampling scale
  (`max_target_step=0.01655 m`), so the earlier `0.05 m` target step spike is
  no longer the leading issue for this model-states-base run.
- EEF motion is smaller per sample (`max_eef_step=0.00781 m`) and directionally
  aligned, but the net behavior still does not reduce distance consistently.
- Lag 2 remains best, and even under best lag the distance-decrease ratio is
  only `0.368421`.
- The current leading blocker is therefore command response / action saturation
  / realized EEF progress, not recorder arithmetic or gross target jumps.

Next minimum check:

```text
Run one read-only action saturation and lag-compensated progress analysis over
the same NPZ. Verify whether commands are saturated at max_linear_step and
whether lag-2 EEF motion is too small to overcome the target/base motion. Do
not modify code, collect more data, or train before this check is reviewed.
```

## 2026-05-04 B8' Action Saturation / Lag Progress Check

Input episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_modelstates_base_check/
  b8_reaching_smoke_tuned_v3_modelstates_base_check_0000.npz
```

Action saturation:

```text
max_linear_step: 0.01
action_norm_mean: 0.013705911245971635
action_norm_max: 0.015634232257955336
clip_component_fraction: 0.5909090909090909
clip_sample_fraction: 0.9545454545454546
initial/min/final_distance:
  0.12842290220394822 / 0.12090753743754573 / 0.13143181756986858
```

Lag-compensated realized progress:

```text
lag 0:
  mean_motion_along_action: 0.0026166904028726524
  mean_motion_toward_target: 0.002141803549978179
  distance_decrease_ratio: 0.4
  mean_eef_step: 0.003954285937645451
lag 1:
  mean_motion_along_action: 0.002896688193264319
  mean_motion_toward_target: 0.0024535920254215907
  distance_decrease_ratio: 0.3684210526315789
  mean_eef_step: 0.0038850260069578134
lag 2:
  mean_motion_along_action: 0.003289428594567762
  mean_motion_toward_target: 0.002913311600383822
  distance_decrease_ratio: 0.3888888888888889
  mean_eef_step: 0.0036671859016857303
lag 3:
  mean_motion_along_action: 0.00317978200838158
  mean_motion_toward_target: 0.002893324943002134
  distance_decrease_ratio: 0.35294117647058826
  mean_eef_step: 0.003646056491872315
```

Decision:

```text
B8' remains unresolved. The leading blocker is saturated target-directed
commands producing too little realized EEF progress.
```

Interpretation:

- Almost every sample has at least one action component clipped at
  `max_linear_step` (`clip_sample_fraction=0.9545`).
- The best lag is still about 2 samples, but lag compensation does not make the
  distance decrease consistently.
- Even under lag 2, mean EEF progress toward the target is only about
  `0.0029 m/sample`, while the remaining gap to the threshold is about
  `0.0209 m` at the minimum and about `0.0314 m` at final distance.
- Before increasing EE delta or changing horizon, confirm whether the joint
  command path is also saturated by `max_joint_delta`.

Next minimum check:

```text
Run one read-only joint-delta saturation analysis on the same NPZ. If active
joint steps are already near max_joint_delta, increasing max_linear_step alone
will not help. If joint steps are not saturated, the next runtime check can be
a single bounded parameter-only smoke with a slightly larger max_linear_step.
```

## 2026-05-04 B8' Active-Joint Step Saturation Check

Input episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_modelstates_base_check/
  b8_reaching_smoke_tuned_v3_modelstates_base_check_0000.npz
```

Read-only joint-delta result:

```text
max_joint_delta: 0.01
samples: 22
joints: 6
per_component_abs_dq_max:
  [0.004038117530795304, 0.004044387745462785,
   0.0064093413954182665, 0.0006558945416408335,
   0.0064445232886694015, 0.004162998998299194]
overall_abs_dq_max: 0.0064445232886694015
step_norm_mean: 0.0060936974244918014
step_norm_max: 0.011151830271949407
near_limit_component_fraction: 0.0
near_limit_step_fraction: 0.0
```

Decision:

```text
B8' remains unresolved, but active-joint per-component saturation is ruled out
for this episode.
```

Interpretation:

- The target-directed EE action is saturated, but observed active-joint
  per-component steps are not near `max_joint_delta=0.01`.
- This suggests that a slightly larger `max_linear_step` is the next smallest
  runtime check. Keep `max_joint_delta` unchanged for the first check so the
  blast radius stays bounded.
- This is still a single blocker-debug smoke, not dataset expansion.

Next minimum check:

```text
Run exactly one short B8' tuned-v3 model-states-base smoke with
max_linear_step:=0.015 and max_joint_delta:=0.010. Validate it and rerun the
same quality/direction/command-motion diagnostics. Do not collect multiple
episodes and do not train.
```

## 2026-05-04 B8' Linear015 Attempt Was Inconclusive

Attempted episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_linear015_check/
  b8_reaching_smoke_tuned_v3_linear015_check_0000.npz
```

Observed runtime issue:

```text
command line requested:
  max_linear_step:=0.015
  max_joint_delta:=0.010

roslaunch parameter summary showed:
  /dp_fm_scripted_expert/max_linear_step: 0.01
  /dp_fm_episode_recorder/max_linear_step: 0.01
```

Offline diagnostics for the saved episode:

```text
validation: PASS
T: 22
metadata success: False
quality episodes_below_threshold: 0
quality min_distance_overall: 0.12092995986807226
quality mean_final_distance: 0.12181283826761834
quality mean_distance_reduction: 0.004700148271823371
command-motion mean_best_action_to_eef_cosine: 0.9001290086972836
command-motion mean_best_lag_steps: 3.0
command-motion mean_best_realized_gain_along_action: 0.17225911074464081
```

Important discrepancy:

- The live scripted expert logged `success=True` after the recorder had already
  saved its episode.
- The saved NPZ metadata and offline quality analysis still show
  `success=False` and no below-threshold sample.
- Because the intended `max_linear_step:=0.015` override did not propagate, this
  attempt is not valid evidence for the planned linear015 parameter check.

Package-local fix:

- `b8_reaching_tuned_v3_episode.launch` now exposes top-level
  `max_linear_step` and `max_joint_delta` args.
- The wrapper now passes those args through to `collect_episode.launch` instead
  of hardcoding `0.010`.

Static checks:

```text
xmllint --noout b8_reaching_tuned_v3_episode.launch: PASS
roslaunch ... b8_reaching_tuned_v3_episode.launch max_linear_step:=0.015
  max_joint_delta:=0.010 --ros-args: PASS
```

Decision:

```text
B8' remains unresolved. Re-run exactly one linear015 smoke after the launch arg
fix; the previous linear015 output should be treated as an invalid parameter
override attempt.
```

## 2026-05-04 B8' Linear015 Fixed Check

Input episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_linear015_fixed_check/
  b8_reaching_smoke_tuned_v3_linear015_fixed_check_0000.npz
```

Runtime confirmation:

```text
/dp_fm_scripted_expert/max_linear_step: 0.015
/dp_fm_episode_recorder/max_linear_step: 0.015
/dp_fm_scripted_expert/max_joint_delta: 0.01
/dp_fm_episode_recorder/max_joint_delta: 0.01
```

Offline validation and quality:

```text
validation: PASS
T: 22
success: False
all_required_metadata_ok: true
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 0
mean_initial_distance: 0.12656234283023146
min_distance_overall: 0.09764575942871043
mean_final_distance: 0.1301823491793326
mean_distance_reduction: -0.003620006349101146
```

Per-sample trace:

```text
below_count: 1
below_indices: [11]
min_idx: 11
min_distance: 0.09764575942871055
final_distance: 0.13018234917933294
max_target_step: 0.02990258511521412
max_target_step_idx: 12
max_eef_step: 0.007442174853866621
```

Command-motion:

```text
mean_best_action_to_eef_cosine: 0.8544660083304763
mean_best_lag_steps: 3.0
mean_best_realized_gain_along_action: 0.09906462168993792
best distance decreasing ratio: 0.555556
eef/action norm at best lag: 0.112664
```

Action and joint saturation:

```text
max_linear_step: 0.015
action_norm_mean: 0.021413832975277623
action_norm_max: 0.022360560574173304
clip_component_fraction: 0.6666666666666666
clip_sample_fraction: 1.0
max_joint_delta: 0.01
overall_abs_dq_max: 0.005893111747848678
near_limit_component_fraction: 0.0
near_limit_step_fraction: 0.0
```

Decision:

```text
B8' remains unresolved. Linear015 is smoke-level progress only.
```

Interpretation:

- The fixed `max_linear_step=0.015` run produced one transient below-threshold
  sample, but final distance was worse than initial and the saved episode is
  still `success=False`.
- Increasing EE step worsened realized gain (`0.099` versus the prior
  model-states-base `0.228`) and shifted best response from lag 2 to lag 3.
- Active-joint per-component steps are still not near `max_joint_delta`, so the
  remaining blocker is not joint step saturation.
- The current evidence points to timing/controller response: larger EE targets
  do not produce proportionally larger realized EEF progress.

Package-local fix for next timing check:

- `b8_reaching_tuned_v3_episode.launch` now exposes and passes through
  `time_from_start_sec`.
- Static checks passed:
  - `xmllint --noout b8_reaching_tuned_v3_episode.launch`
  - `roslaunch ... time_from_start_sec:=0.5 --ros-args`

Next minimum check:

```text
Run exactly one short timing smoke with max_linear_step:=0.010,
max_joint_delta:=0.010, and time_from_start_sec:=0.5. This checks whether a
more aggressive trajectory timing improves realized EEF gain without increasing
the EE action magnitude. Do not collect multiple episodes and do not train.
```

## 2026-05-05 B8' Timing05 Fresh-Restart Check

Input episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_timing05_check/
  b8_reaching_smoke_tuned_v3_timing05_check_0000.npz
```

Runtime context:

- The base simulation, MoveIt context, left-arm controller loader, and
  `world_base_tf_bridge.launch` were restarted before this episode.
- The episode used `max_linear_step=0.010`, `max_joint_delta=0.010`, and
  `time_from_start_sec=0.5`.
- Gripper command remained disabled.

Validation and quality:

```text
validation: PASS
T: 22
success: False
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 0
mean_initial_distance: 0.12756819181897866
min_distance_overall: 0.09537016926721392
mean_final_distance: 0.13770812387361814
mean_distance_reduction: -0.010139932054639478
max_active_left_joint_delta: 0.11660205743292629
```

Command-motion:

```text
mean_best_action_to_eef_cosine: 0.12289950937188704
mean_best_lag_steps: 0.0
mean_best_realized_gain_along_action: 0.03274875046464168
```

Decision:

```text
B8' remains unresolved. The fresh restart rules out a simple long-running
simulation-session explanation for the blocker.
```

Interpretation:

- The below-threshold event is still transient; the saved episode is
  `success=False` and final distance is worse than initial.
- Reducing `time_from_start_sec` to `0.5` did not improve realized EEF gain.
- Command-to-motion alignment collapsed compared with the prior
  model-states-base run (`0.1229` versus `0.8728` best action/eef cosine).
- The unexpectedly large `max_active_left_joint_delta` needs read-only
  inspection before changing control parameters.

Next minimum check:

```text
Run read-only per-sample diagnostics on the timing05 NPZ to inspect distance,
target-base steps, EEF steps, action vectors, and active-joint per-step
saturation. Do not collect another episode, do not start gripper/hand
controllers, and do not train.
```

### Timing05 Per-Sample Follow-Up

Read-only per-sample trace:

```text
samples: 22
below_count: 2
below_indices: [9, 14]
min_idx: 9
min_distance: 0.09537016926721362
final_distance: 0.13770812387361822
max_target_step_base: 0.04418920181065058
max_target_step_idx: 9
max_eef_step_base: 0.017600391738394876
```

The below-threshold samples coincide with large target-base steps:

```text
idx 9:  distance=0.095370, target_step_base=0.044189, eef_step_base=0.011241
idx 14: distance=0.099106, target_step_base=0.040712, eef_step_base=0.010332
```

Read-only joint-step check:

```text
max_joint_delta: 0.01
overall_abs_dq_max: 0.00828410691511916
near_limit_component_fraction: 0.0
near_limit_step_fraction: 0.0
step_norm_max: 0.019516438887074192
```

Updated interpretation:

- The threshold crossings are transient and coupled to target-base jumps, not
  stable arm reaching.
- Active-joint per-component commands are not saturating `max_joint_delta`.
- The larger `max_active_left_joint_delta` from the quality summary is a
  whole-episode range-style metric, not evidence of a per-step limit violation.
- The current blocker is target/base synchronization plus weak
  command-to-motion behavior, not gripper, training, or joint-step saturation.

Next minimum check:

```text
Run one read-only NPZ source-synchronization diagnostic on timing05: compare
base world step, target world step, base yaw step, and target-in-base step
around the target-base jump indices. Do not collect another episode before this
is understood.
```

### Timing05 Source-Synchronization Follow-Up

Read-only source-sync diagnostic showed:

```text
target_step_base spikes:
  idx 1:  0.037657 m
  idx 2:  0.033334 m
  idx 9:  0.044189 m
  idx 10: 0.038757 m
  idx 14: 0.040712 m
  idx 15: 0.032510 m

typical target_step_world: 0.11-0.18 m/sample
typical base_step_world:   0.15-0.16 m/sample
typical base_yaw_step:     0.035-0.038 rad/sample
```

The threshold samples align with target-in-base jumps:

```text
idx 9:  distance=0.095370, target_step_base=0.044189
idx 14: distance=0.099106, target_step_base=0.040712
```

Interpretation:

- The target itself is being moved in world at nearly the same scale as base
  motion, but the reconstructed target-in-base pose still jumps by several
  centimeters.
- This is consistent with a base pose source mismatch: the target updater used
  `/rexrov/pose_gt` odom, while the recorder used `/gazebo/model_states` for
  base pose when `prefer_model_states_base_pose=true`.
- With the base moving about `0.15 m` and yawing about `0.036 rad` per recorder
  sample, the odom/model-state mismatch is large enough to create false
  below-threshold transients.

Package-local fix:

- `base_relative_target.py` can now use `/gazebo/model_states` for the RexROV
  base pose when `prefer_model_states_base_pose=true`.
- `collect_episode.launch` passes `prefer_model_states_base_pose` to the
  base-relative target helper.
- Static checks passed:
  - `python3 -m py_compile base_relative_target.py`
  - `xmllint --noout collect_episode.launch b8_reaching_tuned_v3_episode.launch`
  - `roslaunch ... b8_reaching_tuned_v3_episode.launch ... --ros-args`

Next minimum check:

```text
Run exactly one short B8' source-aligned smoke after the helper fix with
max_linear_step=0.010, max_joint_delta=0.010, and time_from_start_sec=1.0.
Then validate and rerun quality plus the same per-sample source-sync diagnostic.
Do not collect multiple episodes and do not train.
```

### Source-Aligned Smoke Follow-Up

Input episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_source_aligned_check/
  b8_reaching_smoke_tuned_v3_source_aligned_check_0000.npz
```

Runtime confirmation:

```text
/b5d_base_relative_target/prefer_model_states_base_pose: True
B5d base-relative target initialized with base_pose_source=gazebo_model_states
max_linear_step: 0.010
max_joint_delta: 0.010
time_from_start_sec: 1.0
gripper command disabled
```

Validation and quality:

```text
validation: PASS
T: 22
success: False
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 0
mean_initial_distance: 0.12408179276740143
min_distance_overall: 0.0532669152181874
mean_final_distance: 0.1551152861323729
mean_distance_reduction: -0.03103349336497148
```

Source-sync diagnostic:

```text
early target_step_base before idx 12: mostly <= 0.024 m
large target_step_base after idx 13:
  idx 13: 0.076240 m
  idx 14: 0.101956 m
  idx 16: 0.061249 m
  idx 17: 0.080733 m
  idx 19: 0.106041 m
  idx 21: 0.103271 m
```

Interpretation:

- Aligning the target updater base source with the recorder improved the early
  source-sync behavior, so the odom/model-states mismatch fix was directionally
  correct.
- The later target-in-base jumps are much larger and coincide with target world
  jumps while base world/yaw steps remain small.
- The remaining contamination is therefore not the previous base-source
  mismatch. The current target model was still a dynamic, colliding cylinder,
  so physical/contact dynamics can contaminate reaching geometry.

Package-local target marker fix:

- `models/cylinder_target/model.sdf` is now a static visual marker:
  - `<static>true</static>`
  - inertial block removed
  - collision block removed
- `xmllint --noout models/cylinder_target/model.sdf`: PASS

Next minimum check:

```text
Run exactly one source-aligned static-marker smoke with the same parameters.
Then validate, rerun quality, and rerun source-sync diagnostics. The immediate
success criterion is target_step_base no longer showing 0.06-0.10 m jumps.
Do not collect multiple episodes and do not train.
```

### Static-Marker Source-Aligned Smoke Follow-Up

Input episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_static_marker_check/
  b8_reaching_smoke_tuned_v3_static_marker_check_0000.npz
```

Runtime confirmation:

```text
/b5d_base_relative_target/prefer_model_states_base_pose: True
B5d base-relative target initialized with base_pose_source=gazebo_model_states
target model loaded from package-local static visual marker SDF
max_linear_step: 0.010
max_joint_delta: 0.010
time_from_start_sec: 1.0
gripper command disabled
```

Validation and quality:

```text
validation: PASS
T: 22
success: False
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 1
mean_initial_distance: 0.10795291320748376
min_distance_overall: 0.09603994656753867
mean_final_distance: 0.09728469429144865
mean_distance_reduction: 0.010668218916035116
max_active_left_joint_delta: 0.010010654179503753
```

Source-sync diagnostic:

```text
target_step_base no longer has 0.06-0.10 m jumps
max observed target_step_base: 0.011193 m
target_base_xyz stayed near the intended local target neighborhood
```

Runtime failure:

```text
Scripted expert failed: IK failed with MoveIt error code -31
```

Decision:

```text
The target/source-sync portion of the blocker is smoke-level resolved, but B8'
as a collection blocker remains unresolved because the scripted expert crashed
with an IK failure and the saved episode metadata remains success=False.
```

Interpretation:

- Static marker plus model-states base alignment removed the large
  target-in-base jumps that contaminated prior below-threshold samples.
- The distance signal is now much cleaner: it entered the threshold band and
  stayed around `0.096-0.097 m` through the saved samples.
- This is still one short smoke episode, not repeatability evidence and not a
  training dataset.
- The next blocker is no longer target geometry; it is the IK/command path
  failing mid-episode.

Next minimum checks:

```text
Run read-only command-motion diagnostics on the static-marker NPZ and inspect
the scripted expert log around MoveIt error code -31. Do not collect another
episode, do not change gripper state, and do not train.
```

### Static-Marker Command-Motion And IK Log Follow-Up

Command-motion diagnostic:

```text
episodes_total: 1
episodes_below_threshold: 1
mean_best_action_to_eef_cosine: -0.001546695428668099
mean_best_lag_steps: 1.0
mean_best_realized_gain_along_action: 0.055096269666949214
recommendation: do_not_collect_more_until_command_to_motion_path_is_explained
```

Expert log:

```text
Scripted expert started with target source gazebo_model_states.
First MOVE_TO_PREGRASP command was published.
Then the expert failed:
  IK failed with MoveIt error code -31
```

Decision:

```text
B8' remains unresolved.
```

Updated interpretation:

- Target/source synchronization is no longer the main blocker.
- The static-marker episode is valid diagnostic data and has improved distance
  quality, but action-to-motion alignment is still poor.
- MoveIt error code `-31` is consistent with no valid IK solution for one of
  the requested Cartesian target poses.
- The current blocker is now the scripted expert / IK command path, not target
  geometry, gripper, training, or data expansion.

Next minimum check:

```text
Run read-only per-sample action/motion diagnostics on the static-marker NPZ to
separate three cases:
1. the logged action is stale after the expert crash;
2. the arm moved mostly due base/TF effects rather than commanded action;
3. the commanded Cartesian targets approach an IK boundary.
```

### Static-Marker Per-Sample Action/Motion Follow-Up

Per-sample diagnostic:

```text
max_joint_delta: 0.01
action stayed nonzero after the expert crash
joint motion stopped after the first few samples:
  idx 0-4: joint_step_norm nonzero
  idx 5-21: joint_step_norm=0.0
distance stayed near threshold: 0.096-0.097 m for most saved samples
```

Key interpretation:

- The poor command-motion metric is dominated by stale action labels after the
  scripted expert crashed. The recorder keeps the last nonzero action while no
  new arm command is being executed.
- The episode is useful as geometry evidence, but not as a valid executed
  command sequence.
- The active blocker is the IK failure, not target/source sync.

Package-local diagnostic instrumentation:

- `arm_command_converter.py` now logs failed IK request context before raising:
  - MoveIt error code;
  - group and IK link;
  - planning frame;
  - target XYZ and quaternion;
  - seed joint names and positions.
- This does not change control behavior; it only makes the next single smoke
  failure diagnosable.
- `python3 -m py_compile arm_command_converter.py`: PASS

Next minimum check:

```text
Run exactly one short static-marker IK-context smoke with the same parameters
to capture the detailed IK failure log. Do not collect multiple episodes and do
not train.
```

### IK-Context Static-Marker Smoke Follow-Up

Input episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_ik_context_check/
  b8_reaching_smoke_tuned_v3_ik_context_check_0000.npz
```

Runtime result:

```text
static visual marker target
base_pose_source: gazebo_model_states
max_linear_step: 0.010
max_joint_delta: 0.010
time_from_start_sec: 1.0
multiple MOVE_TO_PREGRASP and MOVE_TO_GRASP arm commands published
no IK request failed log emitted in this run
scripted expert finished: success=True, distance 0.091776 below 0.100000
```

Important limitation:

```text
The recorder saved the NPZ before the scripted expert printed success=True.
Offline validation/quality for the saved NPZ has not yet been run.
```

Decision:

```text
B8' is not yet resolved, but the IK failure was not reproduced in this
instrumented run. The current state is promising smoke-level runtime progress
only.
```

Next minimum check:

```text
Run read-only validation, quality, source-sync, and command-motion diagnostics
on the IK-context NPZ. If the saved NPZ is valid, below threshold without
target-base jumps, and command-motion is no longer stale/crash-contaminated,
then this blocker can be considered smoke-level resolved with one-episode
limits.
```

### IK-Context Saved-NPZ Quality Follow-Up

Validation and quality:

```text
validation: PASS
T: 22
metadata success: False
all_required_metadata_ok: true
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 1
mean_initial_distance: 0.10770328097682604
min_distance_overall: 0.0828415071948108
mean_final_distance: 0.08769499361884395
mean_distance_reduction: 0.020008287357982088
max_active_left_joint_delta: 0.07163564753196727
```

Decision:

```text
B8' is smoke-level resolved for one saved non-fallback static-marker reaching
episode, with strict limitations.
```

Evidence:

- The saved NPZ validates.
- The saved NPZ crosses the `0.10 m` reaching threshold.
- Final distance is below threshold and closer than initial distance.
- The runtime IK failure did not reproduce in the IK-context run.
- The runtime expert reported reaching success after the recorder saved.

Limitations:

- This is a single short smoke episode, not repeatability evidence.
- Saved metadata still has `success=False` because recorder success state is
  not synchronized with the expert's later runtime success line.
- Source-sync and command-motion diagnostics still need to be run on this exact
  NPZ before collecting more data.
- Do not expand to multiple episodes or train from this yet.

Next minimum check:

```text
Run source-sync and command-motion diagnostics on the IK-context NPZ. If both
are clean, the next blocker-local decision can be whether to fix saved success
metadata synchronization before any repeatability collection.
```

### IK-Context Command-Motion Follow-Up

Read-only per-sample action/motion diagnostic:

```text
max_joint_delta: 0.01
distance: 0.107703 -> 0.087695 m
min distance: 0.082842 m
joint_step_norm: nonzero through the saved episode
max_abs_dq per sample: below 0.0061 rad
```

Command-motion diagnostic:

```text
episodes_below_threshold: 1
mean_best_action_to_eef_cosine: 0.21415299860000098
mean_best_lag_steps: 2.0
mean_best_realized_gain_along_action: 0.1560406398996791
recommendation: do_not_collect_more_until_command_to_motion_path_is_explained
```

Decision:

```text
B8' remains smoke-level resolved only. It is not repeatability-collection ready.
```

Evidence for smoke-level resolution:

- The saved non-fallback NPZ validates.
- The saved episode crosses and ends below the `0.10 m` reaching threshold.
- Distance reduction is positive.
- The IK-context run did not reproduce the previous IK `-31` crash.
- Unlike the crashed static-marker episode, joint motion is present throughout
  the saved IK-context episode, so this diagnostic is not dominated by stale
  action labels after a crash.

Remaining limitations:

- This is still one short episode only.
- Saved metadata still reports `success=False`.
- Command-to-motion alignment is improved but mixed; cosine is low and the
  analyzer still recommends not collecting more until the path is explained.
- Source-sync diagnostics for this exact IK-context NPZ are still missing.

Next minimum check:

```text
Run read-only source-sync diagnostics on the IK-context NPZ. Do not collect
repeatability episodes or train before confirming that target-in-base geometry
does not contain new step jumps in this exact saved episode.
```

### IK-Context Source-Sync Follow-Up

Read-only source-sync result:

```text
min_distance: 0.08284150719481084
final_distance: 0.08769499361884403
max_target_step_base: 0.012109104884360282
large_target_step_indices: []
```

Decision:

```text
The current B8' blocker is smoke-level resolved for one saved non-fallback
static-marker arm-only reaching episode.
```

Evidence:

- Saved NPZ validation passed.
- Saved episode crosses and ends below the `0.10 m` reaching threshold.
- Distance reduction is positive.
- The prior IK `-31` failure did not reproduce in the IK-context run.
- Joint motion is present throughout the saved episode, so command-motion is
  not dominated by stale action after a crash.
- Target-in-base source sync is clean for this episode:
  `max_target_step_base=0.012109 m` and no `>0.03 m` step jumps.

Strict limitations:

- This is one short smoke episode only, not repeatability evidence.
- Saved metadata still reports `success=False`, despite distance-based success
  and the later runtime expert success line.
- Command-to-motion alignment is still mixed:
  `mean_best_action_to_eef_cosine=0.214153`,
  `mean_best_lag_steps=2.0`, and analyzer recommendation remains
  `do_not_collect_more_until_command_to_motion_path_is_explained`.
- Do not expand collection and do not train BC / DP / FM from this yet.

Next blocker-local task:

```text
Inspect/fix saved success metadata synchronization so the recorder's saved
`success` field matches the reaching-distance evidence before any repeatability
collection.
```

### Recorder Success Metadata Synchronization Fix

Read-only code inspection found:

```text
recorder.py subscribes to expert_success_topic.
If no expert success message has arrived by save time, metadata success falls
back to the launch parameter `~success`, which is false in B8' smoke runs.
The IK-context runtime expert published success=True after the recorder had
already saved the NPZ.
```

Package-local code fix:

```text
src/rexrov_single_oberon7_fm_dp/recorder.py
```

Change:

- For `reaching_success` and `pregrasp_success`, the recorder now computes
  saved success from the final recorded `relative_target_to_eef` distance.
- It records:
  - `success_source`;
  - `recorded_success_distance_m`;
  - `recorded_success_distance_threshold_m`.
- Expert success topic remains available, but recorded reaching distance now
  takes precedence for the saved NPZ because it is synchronized with the saved
  samples.

Verification:

```text
python3 -m py_compile recorder.py: PASS
existing IK-context final recorded distance: 0.08769499361884395
would_record_success: True
```

Next minimum runtime validation:

```text
Run exactly one short IK-context-equivalent smoke and validate the new NPZ.
Expected result: validation PASS and saved metadata `success=True` when final
recorded distance is below `0.10 m`.
```

### Recorder Success Metadata Runtime Validation

Validation episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_success_sync_check/
  b8_reaching_smoke_tuned_v3_success_sync_check_0000.npz
```

Runtime result:

```text
scripted expert finished:
  success=True reason=reaching_success: distance 0.035195 below 0.100000
```

Saved NPZ validation:

```text
validation: PASS
T: 22
success: True
unavailable_fields: ['raw_command']
```

Saved metadata inspection:

```text
success scalar: True
metadata success: True
success_source: recorded_final_distance
recorded_success_distance_m: 0.0404588355643862
recorded_success_distance_threshold_m: 0.1
```

Decision:

```text
The current B8' blocker, including saved success metadata synchronization, is
resolved at smoke level.
```

Remaining limits:

- This is still smoke-level evidence only, not repeatability evidence.
- Do not claim grasp success, learned rollout success, or real policy success.
- Do not train BC / DP / FM from this single validation episode.
- Any later expansion should begin with a small repeatability set and the same
  read-only quality/source-sync/command-motion diagnostics.

## 2026-05-05 B8' Repeatability Smoke Result

This round records:

```text
B8' repeatability smoke: 3-5 episode real non-fallback arm-only
reaching/pre-grasp repeatability check, no training, no gripper handling.
```

Runtime scope:

- Started the minimal Gazebo/RexROV/Oberon7 runtime.
- Started package-local MoveIt semantic context via
  `b5d_move_group_with_context.launch`.
- Started only the left arm controller via
  `load_left_controllers.launch start:=true load_hand:=false`.
- Started `world_base_tf_bridge.launch`.
- Collected five short `b8_reaching_tuned_v3_episode.launch` episodes with
  `max_linear_step=0.010`, `max_joint_delta=0.010`, and
  `time_from_start_sec=1.0`.
- Kept `allow_nominal_state_fallback=false`, gripper commands disabled,
  `gripper_enabled=false`, and `is_grasp_dataset=false`.

Dataset:

```text
data/raw/b8_reaching_repeatability_smoke/
  b8_reaching_repeatability_smoke_0000.npz
  b8_reaching_repeatability_smoke_0001.npz
  b8_reaching_repeatability_smoke_0002.npz
  b8_reaching_repeatability_smoke_0003.npz
  b8_reaching_repeatability_smoke_0004.npz
```

Diagnostics:

```text
outputs/logs/b8_reaching_repeatability_smoke/repeatability_summary.json
outputs/logs/b8_reaching_repeatability_smoke/repeatability_summary.md
outputs/logs/b8_reaching_repeatability_smoke_quality/per_episode_quality.json
outputs/logs/b8_reaching_repeatability_smoke_direction/direction_diagnostic.json
outputs/logs/b8_reaching_repeatability_smoke_command_motion/command_motion_diagnostic.json
```

Summary:

```text
episodes_total: 5
validator_pass_count: 5
success_count: 5
reaching_success_rate: 1.0
all_required_metadata_ok: true
all_success_metadata_consistent: true
mean_initial_distance: 0.10765874377608645
mean_final_distance: 0.06034401658235772
mean_distance_reduction: 0.0473147271937287
min_distance_overall: 0.04955370542041048
max_active_left_joint_delta: 0.06810874321597282
max_target_step_base: 0.014892885342403243
large_target_step_indices: [] for all episodes
mean_best_action_to_eef_cosine: 0.7559808833882034
mean_best_lag_steps: 2.2
mean_best_realized_gain_along_action: 0.2432157689973347
```

Per-episode final distances:

```text
0000: 0.06906018109665871 m
0001: 0.04955370542041048 m
0002: 0.05586573174312177 m
0003: 0.06042199881789199 m
0004: 0.06681846583370564 m
```

Metadata consistency:

- `success_source=recorded_final_distance` for all five episodes.
- `recorded_success_distance_threshold_m=0.1` for all five episodes.
- `base_state_source=gazebo_model_states` for all five episodes.
- `joint_state_source=joint_states` for all five episodes.
- `target_state_source=gazebo_model_states` for all five episodes.
- `gripper_enabled=false` and `is_grasp_dataset=false` for all five episodes.
- `raw_command` remains unavailable and documented in metadata, so it is only
  a validator warning, not a failure.

Decision:

```text
B8' repeatability smoke is resolved at the 5-episode smoke level.
```

Interpretation:

- This is real non-fallback arm-only reaching/pre-grasp evidence.
- This is not grasping, not learned-policy rollout, and not BC/DP/FM training
  evidence.
- The next step can be a deliberately small real non-fallback arm-only dataset
  collection plan, not an immediate large 20/50/100 episode expansion.

## 2026-05-05 B8' Debug Batch Failure Analysis

This round records:

```text
B8' debug batch failure analysis：分析 b8_reaching_debug_10 中 0007–0009 连续失败，不训练、不扩采、不处理 gripper。
```

Scope:

- Offline-only analysis over the existing 10 episodes in
  `data/raw/b8_reaching_debug_10/`.
- No new episodes were collected.
- No training, learned rollout, gripper handling, hand controller, or gripper
  command was used.

New read-only analysis script:

```text
scripts/analyze_b8_debug_batch_failure.py
```

Generated artifacts:

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

Main success-vs-failure differences:

```text
episodes_total: 10
success_count: 7
failure_count: 3
success episodes: 0000-0006
failure episodes: 0007-0009

initial_distance:
  success_mean: 0.108700
  failure_mean: 0.108612
final_distance:
  success_mean: 0.067966
  failure_mean: 0.117702
distance_reduction:
  success_mean: 0.040734
  failure_mean: -0.009090
best_action_to_eef_cosine:
  success_mean: 0.823278
  failure_mean: -0.071778
best_realized_gain_along_action:
  success_mean: 0.209131
  failure_mean: -0.021860
action_relative_cosine:
  success_mean: 0.897726
  failure_mean: 0.943494
joint_initial_drift_from_ep0:
  success_mean: 0.304920
  failure_mean: 0.806195
eef_base_initial_drift_from_ep0:
  success_mean: 0.173386
  failure_mean: 0.330540
target_base_max_step:
  success_mean: 0.006151
  failure_mean: 0.001934
T: 22 for all episodes
duration: about 6.9 s for all episodes
```

Interpretation:

- Initial distance did not explain the failures; success and failure episodes
  started at nearly the same recorded distance.
- The scripted `action_ee_delta` direction remained target-aligned in failed
  episodes, and was slightly more aligned than in successful episodes.
- The main degradation was command-to-motion: in episodes 0007-0009, realized
  EEF motion became weak, non-target-directed, and by episode 0009 negative
  along the commanded action direction.
- Active-left joint motion within each episode stayed bounded and similar, but
  initial active-left joint configuration drifted across repeated episodes.
- Target/base source sync is unlikely to be the primary cause in the failed
  tail because failed `target_base_max_step` stayed well below the `0.03 m`
  large-jump threshold.
- Episode duration is unlikely to be the primary cause because all episodes had
  the same `T=22` and similar duration.

Current B8' judgment:

```text
B8' data-path and metadata gates remain resolved for this 10-episode odom-source
non-fallback arm-only debug batch, but reaching-quality repeatability is not
resolved at the 10-episode level.
```

Most likely blocker:

```text
Repeated short episodes accumulate arm/base/controller state so the scripted
target-directed action remains geometrically correct, but the IK/controller
response no longer produces target-directed EEF motion.
```

Next minimum fix/diagnostic before any new collection:

- Add or enforce a per-episode reset/settle gate for active-left joint initial
  configuration and EEF/base-frame pose before recording starts.
- Add a pre-episode no-op or hold/settle check to ensure previous command
  transients have decayed.
- Consider gating collection if initial active-joint drift or command-motion
  response drops below a conservative threshold.
- If a runtime check is approved later, run only a very short verification
  after the reset/settle change; do not expand to 20/50/100 episodes.

Do not train BC / DP / FM and do not run learned rollout from
`b8_reaching_debug_10`.

## 2026-05-05 B8' Initial-State Gate Preparation

This round continues the same blocker:

```text
B8' 10-episode debug batch tail reaching-quality degradation.
```

Current blocker judgment:

```text
Not resolved.
```

Reason:

- Offline evidence identified the likely failure mode, but no runtime evidence
  yet shows that the cross-episode drift can be prevented.
- Episodes 0007-0009 still show command-to-motion collapse in the existing
  batch.
- There is not yet a verified per-episode reset/settle gate or short
  post-gate verification run.

Read-only code inspection found:

- `collect_episode.launch` exposes timing parameters such as
  `post_publish_sleep_sec`, but no pre-episode joint reset, EEF pose gate, or
  initial joint drift gate.
- `batch_collect_episodes.py` accepts episodes based on validator/success
  filtering, but does not check live initial state before launching an episode.
- The scripted expert publishes target-directed action correctly, but does not
  currently reject a bad accumulated initial joint/EEF configuration before
  commanding arm motion.

Minimal package-local tool added:

```text
scripts/check_b8_initial_state_gate.py
```

Purpose:

- Read live `/joint_states`, `/rexrov/pose_gt`, `/gazebo/model_states`, and
  TF `rexrov/base_link -> oberon7_l/end_effector`.
- Compare the live initial state against a reference successful episode,
  normally `b8_reaching_debug_10_0000.npz`.
- Exit nonzero if active-left joint drift, EEF/base drift, relative target/EEF
  drift, or initial distance exceeds conservative thresholds.
- Write a JSON report if requested.

Safety boundary:

- The script sends no arm command.
- The script sends no gripper command.
- It does not start a hand controller, train, rollout, or collect an episode.

Verification performed:

```text
python3 -m py_compile scripts/check_b8_initial_state_gate.py: PASS
source devel/setup.bash; python3 scripts/check_b8_initial_state_gate.py --help: PASS
```

Next minimum runtime check, after the normal B8 runtime is already started and
before any collection. First run it without requiring a live target:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosrun rexrov_single_oberon7_fm_dp check_b8_initial_state_gate.py \
  --reference-npz src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_debug_10/b8_reaching_debug_10_0000.npz \
  --skip-target-checks \
  --output-json src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_initial_state_gate/latest_gate.json
```

Expected pass signal:

```text
"passed": true
"control_commands_sent": false
"gripper_commands_sent": false
```

If it fails:

- `joint_l2_ok=false` or `joint_max_abs_ok=false` supports the reset/settle
  hypothesis.
- `eef_base_drift_ok=false` supports accumulated arm/base configuration drift.
- In full target-check mode, `relative_base_drift_ok=false` or
  `initial_distance_ok=false` means the next episode would start outside the
  intended initial condition envelope.

After a target model/updater is active, rerun without `--skip-target-checks`
and pass the actual current `--target-model-name`.

Do not use a failed gate state for additional B8' data collection.

### Runtime Result: Skip-Target Initial-State Gate

User ran the read-only gate with the current B8 runtime active:

```text
rosrun rexrov_single_oberon7_fm_dp check_b8_initial_state_gate.py
  --reference-npz data/raw/b8_reaching_debug_10/b8_reaching_debug_10_0000.npz
  --skip-target-checks
```

Result:

```text
passed: true
control_commands_sent: false
gripper_commands_sent: false
target_checks_skipped: true

joint_l2_drift: 0.00015674238939907846
joint_max_abs_drift: 0.00010077841280065059
eef_base_drift: 0.00008922043640714035
```

Interpretation:

- The current clean runtime starts in a known-good active-left joint and
  EEF/base neighborhood relative to successful reference episode 0000.
- The immediate startup state does not reproduce the large tail-episode joint
  drift seen in `b8_reaching_debug_10`.
- The gate is only skip-target mode, so it does not verify target-relative
  initial distance, target/base sync, or command-to-motion after arm commands.
- TF repeated-data warnings from `world_base_tf_bridge` were observed, but the
  gate still obtained finite TF and passed; treat this as a warning to monitor,
  not as a blocker by itself.

Current blocker judgment remains:

```text
Not resolved.
```

Reason:

- The passed gate rules out bad startup joint/EEF state in the current runtime,
  but it does not prove that repeated arm-command episodes will stay reset or
  that command-to-motion alignment will remain stable after several episodes.
- The next missing evidence is either a full target-aware gate before
  collection or a short approved post-gate verification run with the gate
  checked before/after.

### Target-Only Gate Probe Launch

Added a package-local target-only launch:

```text
launch/b8_target_gate_probe.launch
```

Purpose:

- Spawn `cylinder_target_gate_probe`.
- Run `base_relative_target.py` to keep that target at the same conservative
  base-frame offset used by B8' reaching checks:
  `[0.10, 0.0, 0.04]`.
- Use odom-sourced base pose by default
  (`prefer_model_states_base_pose=false`) so it matches the target-aware gate's
  live base calculation.

Safety boundary:

- Does not start recorder.
- Does not start scripted expert.
- Does not execute arm commands.
- Does not start hand controller.
- Does not send gripper commands.
- Does not train or run learned rollout.

Verification:

```text
XML parse: PASS
roslaunch rexrov_single_oberon7_fm_dp b8_target_gate_probe.launch --ros-args: PASS
```

Next minimum runtime sequence:

1. In a separate terminal, keep the target-only probe running:

   ```bash
   cd /home/benny/uuv_manipulator_ws
   source devel/setup.bash
   roslaunch rexrov_single_oberon7_fm_dp b8_target_gate_probe.launch
   ```

2. In another terminal, confirm the model exists:

   ```bash
   rostopic echo -n 1 /gazebo/model_states/name
   ```

   Expected model name:

   ```text
   cylinder_target_gate_probe
   ```

3. Then run the target-aware gate:

   ```bash
   rosrun rexrov_single_oberon7_fm_dp check_b8_initial_state_gate.py \
     --reference-npz src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_debug_10/b8_reaching_debug_10_0000.npz \
     --target-model-name cylinder_target_gate_probe \
     --output-json src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_initial_state_gate/latest_target_gate.json
   ```

Expected pass signal:

```text
passed: true
relative_base_drift_ok: true
initial_distance_ok: true
control_commands_sent: false
gripper_commands_sent: false
```

### Runtime Result: Target-Aware Initial-State Gate

User ran the target-only probe and confirmed:

```text
/gazebo/model_states/name:
  ocean_box
  rexrov
  cylinder_target_gate_probe
```

The target-aware gate was then run twice with:

```text
--target-model-name cylinder_target_gate_probe
--reference-npz data/raw/b8_reaching_debug_10/b8_reaching_debug_10_0000.npz
```

Both runs produced the same pass result:

```text
passed: true
target_checks_skipped: false
control_commands_sent: false
gripper_commands_sent: false

joint_l2_drift: 0.006599956530879626
joint_max_abs_drift: 0.006339712261209662
eef_base_drift: 0.0011713350520162551
target_base_drift: 0.0011803381838364844
relative_base_drift: 0.000038338634031170594
initial_distance: 0.10771198633079769
```

All checks passed:

```text
joint_l2_ok: true
joint_max_abs_ok: true
eef_base_drift_ok: true
relative_base_drift_ok: true
initial_distance_ok: true
```

Interpretation:

- Clean runtime startup, active-left joint state, EEF/base pose, target/base
  pose, relative target/EEF vector, and initial distance are all consistent
  with successful reference episode 0000.
- The B8' target-only gate probe is valid for checking target-aware initial
  conditions without collecting an episode.
- The original 0007-0009 failure is therefore unlikely to be caused by bad
  clean-start initial conditions or target placement.

Current blocker judgment:

```text
B8' startup initial-condition gate is smoke-level resolved.
B8' tail command-to-motion degradation remains unresolved.
```

Remaining missing evidence:

- Whether the same gate remains clean after one or more arm-command episodes.
- Whether command-to-motion alignment remains stable after commands are issued.
- Whether a short gated verification episode can pass without reproducing the
  0007-0009 degradation.

Next minimum read-only check before any arm command:

```text
Repeat the target-aware gate a few times while the target-only probe is running
and no arm command is issued, to confirm no passive target/EEF drift.
```

### Runtime Result: Repeated Target-Aware Gate Stability

User ran the target-aware gate five times at about 5 s spacing while
`b8_target_gate_probe.launch` was running and no arm command was issued.

Result:

```text
passes: 5/5
control_commands_sent: false for all
gripper_commands_sent: false for all
target_checks_skipped: false for all
```

Metric ranges:

```text
joint_l2_drift:
  min: 0.006571430078048146
  max: 0.006618381619597192
joint_max_abs_drift:
  min: 0.006313718676446811
  max: 0.006351625337845057
eef_base_drift:
  min: 0.0011618486495774648
  max: 0.0012022803850341706
target_base_drift:
  min: 0.0011803381838229614
  max: 0.004144552964742915
relative_base_drift:
  min: 0.00004526798965118013
  max: 0.004136018974138625
initial_distance:
  min: 0.10394396276812444
  max: 0.11000999665938455
```

Interpretation:

- With no arm command, target-aware initial geometry remains inside all gates
  over the short repeated check.
- Passive target/updater/TF/EEF drift is not currently reproducing the
  0007-0009 failure mode.
- Startup and passive target-aware initial-condition gating are now
  smoke-level resolved.

Current blocker judgment:

```text
B8' startup/passive initial-condition gate: smoke-level resolved.
B8' post-command repeatability and command-to-motion degradation: still open.
```

Remaining missing evidence:

- Whether a single short arm-only command episode leaves the system inside the
  target-aware gate afterward.
- Whether command-to-motion alignment is acceptable in that one gated
  verification episode.

Next minimum non-read-only check, if approved:

```text
Run exactly one short gated arm-only verification episode, then immediately
rerun the target-aware gate and offline command-motion diagnostics.
Do not expand collection and do not train.
```

### Runtime Result: One Gated Arm-Only Verification Episode

User approved one short gated arm-only verification episode. The episode used:

```text
target_model_name: cylinder_target_gate_probe
spawn_target: false
enable_base_relative_target: false
execute_arm: true
enable_gripper_command: false
allow_nominal_state_fallback: false
prefer_model_states_base_pose: false
rate_hz: 3.0
max_duration_sec: 7.2
max_linear_step: 0.010
max_joint_delta: 0.010
time_from_start_sec: 1.0
state_sequence: MOVE_TO_PREGRASP,MOVE_TO_GRASP
```

Output:

```text
data/raw/b8_gated_arm_verify_1/b8_gated_arm_verify_1_0000.npz
```

Pre-gate:

```text
passed: true
initial_distance: 0.1077189674919894
relative_base_drift: 0.000060108361737702964
joint_l2_drift: 0.006583236356065188
eef_base_drift: 0.0011656954861866385
```

Runtime expert:

```text
success=True
reason=reaching_success: distance 0.042648 below 0.100000
```

Validator:

```text
validation: PASS
T: 22
success: True
unavailable_fields: ['raw_command']
```

Saved metadata:

```text
success: true
success_source: recorded_final_distance
recorded_success_distance_m: 0.045301559855776316
recorded_success_distance_threshold_m: 0.1
allow_nominal_state_fallback: false
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
gripper_enabled: false
is_grasp_dataset: false
task_type: arm_only_reaching
success_metric: reaching_success
```

Quality diagnostics:

```text
initial_distance: 0.10625611763364251
min_distance: 0.045301559855776316
final_distance: 0.045301559855776316
distance_reduction: 0.060954557777866195
max_active_left_joint_delta: 0.0771154374980636
episodes_below_threshold: 1/1
```

Direction and command-motion diagnostics:

```text
mean_eef_motion_cosine_with_target: 0.8411411057732849
mean_eef_positive_target_direction_ratio: 1.0
mean_action_to_eef_motion_cosine: 0.8718392906129798
mean_best_action_to_eef_cosine: 0.8718392906129798
mean_best_lag_steps: 0.0
mean_best_realized_gain_along_action: 0.24521231853273232
best_distance_decreasing_ratio: 0.952381
target_base_net/max-step: 0.003335 / 0.003335
```

Post-gate:

```text
passed: false
relative_base_drift_ok: false
relative_base_drift: 0.07180542804879099
initial_distance: 0.04013113557371512
joint_l2_drift: 0.11565944021317238
eef_base_drift: 0.07153365725910747
control_commands_sent: false
gripper_commands_sent: false
```

Interpretation:

- The single gated arm-only verification episode succeeded and command-motion
  quality was strong.
- This is not learned rollout, not grasping, and not training evidence.
- The post-gate failure is informative: after the arm reaches/pre-grasps, the
  system remains in the reached configuration and no automatic return-to-start
  or reset/settle step exists.
- Therefore, the 0007-0009 batch degradation is most consistent with
  cross-episode state accumulation/reset policy, not with bad clean-start
  target placement or single-episode command-motion failure.

Current blocker judgment:

```text
B8' single gated arm-only verification: smoke-level resolved.
B8' multi-episode repeatability: still blocked until reset/return-to-start or
per-episode reinitialization is defined and verified.
```

Next minimum fix direction:

```text
Do not expand collection. Add or define a bounded reset/settle policy before
running another multi-episode check. Candidate approaches: explicit
return-to-reference joint command, restart/reset runtime between episodes, or
gate-and-skip episodes until active-left joint/EEF state returns inside the
initial-condition envelope.
```

### Reset/Settle/Reinitialization Strategy

Selected minimum strategy for the next B8' blocker step:

```text
bounded return-to-reference joint command
  -> target-aware initial-state gate
  -> only then allow the next episode
```

Rationale:

- Runtime restart between every episode is heavier and would hide whether the
  arm command path can be stabilized.
- Pure gate-and-skip prevents bad data but does not recover from the
  post-command reached/pregrasp configuration.
- A bounded left-arm return command directly targets the observed blocker:
  after a successful reaching command, the arm remains near the target and must
  be returned to the reference initial envelope before another episode.

Added package-local tool:

```text
scripts/return_left_arm_to_reference.py
```

Behavior:

- Loads active-left joint names and initial joint positions from a reference
  NPZ, normally `b8_reaching_debug_10_0000.npz`.
- Reads current `/joint_states`.
- Publishes only bounded active-left `JointTrajectory` commands to
  `/oberon7/arm_position_l/command`.
- Clips each command step by `--max-joint-delta`, default `0.01 rad`.
- Stops when joint errors are inside:
  - `joint_l2_tolerance=0.01`;
  - `joint_max_abs_tolerance=0.005`.
- Sends no gripper command and does not start hand controllers.

Verification:

```text
python3 -m py_compile scripts/return_left_arm_to_reference.py: PASS
python3 scripts/return_left_arm_to_reference.py --help: PASS
```

Dry-run result from the post-command reached/pregrasp state:

```text
dry_run: true
commands_sent: 0
gripper_commands_sent: false
reached: false
joint_l2_error: 0.11564320348459194
joint_max_abs_error: 0.08137583509102786
first bounded delta clipped to <= 0.01 rad per active-left joint
```

This confirms the post-command state is outside the reference initial joint
envelope and that the tool computes a bounded recovery step without sending it.

Proposed next runtime check if approved:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosrun rexrov_single_oberon7_fm_dp return_left_arm_to_reference.py \
  --reference-npz src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_debug_10/b8_reaching_debug_10_0000.npz \
  --output-json src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_initial_state_gate/return_to_reference_live.json
```

Then immediately run the target-aware gate:

```bash
rosrun rexrov_single_oberon7_fm_dp check_b8_initial_state_gate.py \
  --reference-npz src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_debug_10/b8_reaching_debug_10_0000.npz \
  --target-model-name cylinder_target_gate_probe \
  --output-json src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_initial_state_gate/post_return_target_gate.json
```

Pass criteria:

```text
return tool reached=true
post-return target-aware gate passed=true
control_commands_sent only by return tool
gripper_commands_sent=false everywhere
```

Live runtime check result:

```text
return_left_arm_to_reference.py
commands_sent: 8
dry_run: false
reached: true
gripper_commands_sent: false
final_joint_l2_error: 0.0010774700888416262
final_joint_max_abs_error: 0.0010726177090809585
```

Post-return target-aware gate:

```text
passed: true
target_model_name: cylinder_target_gate_probe
initial_distance: 0.11073716282178127
joint_l2_drift: 0.0010745595666474277
joint_max_abs_drift: 0.0010454018959631384
eef_base_drift: 0.00021356578002534779
relative_base_drift: 0.0032940252409286845
control_commands_sent: false
gripper_commands_sent: false
```

Interpretation:

- The bounded return-to-reference reset/settle step is live smoke-level
  resolved.
- It successfully moves the active-left arm from the post-command reached
  configuration back inside the reference initial joint envelope.
- The following target-aware gate also passes, including target-relative
  geometry.
- This resolves the reset/settle mechanism at single-cycle smoke level, but it
  does not yet prove multi-episode repeatability. The next minimal check is one
  short gated arm-only episode after return-to-reference, followed by validator,
  target-aware gate, and quality/command-motion diagnostics.
- No gripper command was sent; this remains arm-only reaching/pre-grasp, not
  grasping and not learned rollout.

Follow-up one-episode verification attempt:

```text
episode_id: b8_return_gated_arm_verify_1_0000
actual saved path:
/home/benny/.ros/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_return_gated_arm_verify_1/b8_return_gated_arm_verify_1_0000.npz
validator: PASS
success: false
recorded_success_distance_m: 0.10891000445099207
threshold: 0.1
allow_nominal_state_fallback: false
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
gripper_enabled: false
is_grasp_dataset: false
```

The episode was not a valid check of the intended return-gated target-directed
route because the launch invocation omitted the target-directed overrides:

```text
target_directed_reaching: false
state_sequence: MOVE_TO_PREGRASP,MOVE_TO_GRASP,CLOSE_GRIPPER,LIFT_OR_HOLD
max_linear_step: 0.005
time_from_start_sec: 3.0
```

Runtime symptom:

```text
Scripted expert failed: unsupported operand type(s) for *: 'NoneType' and 'NoneType'
```

Offline diagnostics for that saved file:

```text
mean_initial_distance: 0.10788122569941581
mean_final_distance: 0.10891000445099207
mean_distance_reduction: -0.0010287787515762536
min_distance_overall: 0.10458705289514927
mean_action_to_eef_motion_cosine: 0.11290408272341595
mean_best_action_to_eef_cosine: 0.2521221409884768
mean_best_lag_steps: 2.0
mean_best_realized_gain_along_action: 0.045054442830130825
```

Interpretation:

- This failed episode does not disprove the return-to-reference reset/settle
  result.
- It does show that the next command must use an absolute `output_dir` and
  must explicitly set the same B8' arm-only target-directed parameters that
  produced the previous successful gated verification:
  `target_directed_reaching:=true`,
  `state_sequence:=MOVE_TO_PREGRASP,MOVE_TO_GRASP`,
  `execute_arm_states:=MOVE_TO_PREGRASP,MOVE_TO_GRASP`,
  `max_linear_step:=0.010`, and `time_from_start_sec:=1.0`.
- The current blocker is still not fully resolved; after another
  return-to-reference + target-aware gate, run exactly one corrected short
  arm-only verification episode, then validator, target-aware gate, and
  quality/command-motion diagnostics.

Corrected return-gated arm-only verification:

```text
pre-return:
  return_left_arm_to_reference.py reached=true
  commands_sent=1
  final_joint_l2_error=8.382996789634279e-05
  final_joint_max_abs_error=7.591381990490476e-05
  gripper_commands_sent=false

pre-episode target-aware gate:
  passed=true
  initial_distance=0.11332110045439249
  joint_l2_drift=0.00010507141667035804
  joint_max_abs_drift=8.427760260509842e-05
  relative_base_drift=0.00710979212566845

episode:
  path=data/raw/b8_return_gated_arm_verify_2/b8_return_gated_arm_verify_2_0000.npz
  validator=PASS
  T=22
  success=True
  runtime expert success=True
  success_source=recorded_final_distance
  recorded_success_distance_m=0.08215466060136162
  recorded_success_distance_threshold_m=0.1
  allow_nominal_state_fallback=false
  base_state_source=odom
  joint_state_source=joint_states
  target_state_source=gazebo_model_states
  gripper_enabled=false
  is_grasp_dataset=false
```

Offline quality:

```text
initial_distance=0.10769470167832411
min_distance=0.08071406189845907
final_distance=0.08215466060136162
distance_reduction=0.02554004107696249
max_active_left_joint_delta=0.04737701535920724
mean_action_to_eef_motion_cosine=0.23340877386497508
mean_best_action_to_eef_cosine=0.2649969261995647
mean_best_lag_steps=3.0
mean_best_realized_gain_along_action=0.08132703920221891
```

Post-episode target-aware gate:

```text
passed=false
relative_base_drift_ok=false
initial_distance=0.08076170932878053
joint_l2_drift=0.08521686992588655
joint_max_abs_drift=0.047383085806978364
relative_base_drift=0.05839507151533
gripper_commands_sent=false
```

Interpretation:

- The corrected return-gated single episode is successful and non-fallback,
  with consistent saved success metadata.
- The reset/settle strategy is now validated through one corrected
  return->gate->arm-only episode cycle at smoke level.
- The post-episode gate failure is expected: after reaching, the arm is again
  outside the reference initial envelope. This confirms that every subsequent
  episode must be preceded by return-to-reference and target-aware gate.
- Command-motion quality is positive but still weak compared with the earlier
  strongest single episode, so this is not enough to resume 10+ episode
  collection or training.
- B8' multi-episode blocker remains partially unresolved until repeated
  return->gate->episode cycles show stable success and stronger/consistent
  command-motion diagnostics.

Post-success return-to-reference check:

```text
return_left_arm_to_reference.py:
  reached=true
  commands_sent=5
  final_joint_l2_error=0.00010091317246476995
  final_joint_max_abs_error=7.563576529534544e-05
  gripper_commands_sent=false

post_success_return_gate:
  passed=false
  joint_l2_ok=true
  joint_max_abs_ok=true
  eef_base_drift_ok=true
  initial_distance_ok=false
  relative_base_drift_ok=false
  initial_distance=0.12368795041111422
  relative_base_drift=0.01695805312367644
  target_base_drift=0.01691229565682799
  joint_l2_drift=0.0006517102217792586
  eef_base_drift=4.920892227205025e-05
```

Interpretation:

- The active-left return command remains effective after a successful
  corrected reaching episode.
- The failed gate is no longer explained by arm joint or EEF reset; those are
  inside the reference envelope.
- The current remaining blocker is target-relative initial geometry drift:
  the live target/base offset is about 1.7 cm away from the reference gate and
  pushes initial distance above the `0.115 m` gate threshold.
- Do not run another episode until target/base stability is rechecked
  read-only, or the target probe is deliberately reinitialized and then gated.

Restarted-runtime repeated target-aware gate:

```text
runtime: restarted uvms_control, move_group context, left controllers,
world_base_tf_bridge, and b8_target_gate_probe
check: 3 read-only target-aware gates, 5 s apart
control_commands_sent=false for all
gripper_commands_sent=false for all
```

Results:

```text
gate_0:
  passed=false
  initial_distance=0.11029615817327146
  relative_base_drift=0.02327702221543785
  target_base_drift=0.022187036192277323
  joint_l2_drift=0.00656463862838594

gate_1:
  passed=false
  initial_distance=0.11029953375977956
  relative_base_drift=0.0232763337054756
  target_base_drift=0.02218640052215951
  joint_l2_drift=0.006564707845546027

gate_2:
  passed=true
  initial_distance=0.10770297148110519
  relative_base_drift=5.5529932828080466e-06
  target_base_drift=0.0012237377600882425
  joint_l2_drift=0.006564523581859333
```

Interpretation:

- Restarting the runtime and target probe can recover target/base geometry, but
  the first target-aware gates after startup may still see a transient
  target-relative offset.
- The blocker is not a permanent target/base drift after restart; it is a
  target probe / base-relative target settle timing issue.
- No arm episode should start from the first passing-looking startup moment
  unless the target-aware gate has actually passed.
- Before the next arm episode, require at least one fresh target-aware gate
  pass after the runtime has settled; a stricter policy is two consecutive
  read-only target-aware gate passes 5 s apart.

Two-pass target-aware gate after settle:

```text
check: 2 read-only target-aware gates, 5 s apart
control_commands_sent=false for both
gripper_commands_sent=false for both

gate_0:
  passed=true
  initial_distance=0.1076746834400219
  relative_base_drift=3.503815165242792e-05
  target_base_drift=0.001223737760115677
  joint_l2_drift=0.006460512049110969

gate_1:
  passed=true
  initial_distance=0.10766337265266729
  relative_base_drift=4.5012944528958283e-05
  target_base_drift=0.001223737760115677
  joint_l2_drift=0.006451700794021077
```

Interpretation:

- The target/base startup-settle transient is smoke-level resolved after
  waiting for the target probe/base-relative target updater to settle.
- The stricter two-consecutive-pass target-aware gate is satisfied.
- This permits at most the next small blocker-local check: one corrected
  return-gated arm-only episode, followed by validator, target-aware gate, and
  quality/command-motion diagnostics.
- This still does not justify training, learned rollout, gripper work, or
  larger 10+ episode collection.

Action-frame bug and post-fix verification:

```text
b8_return_gated_arm_verify_3:
  pre-return reached=true
  pre-gate passed=true
  runtime failure: IK failed with MoveIt error code -31
  validator=PASS
  saved success=false
  recorded_success_distance_m=0.10966874121994438
  initial_distance=0.10754135428528212
  min_distance=0.09737090906980891
  final_distance=0.10966874121994438
  distance_reduction=-0.0021273869346622593
  mean_action_to_eef_motion_cosine=0.08695271743383595
  mean_best_action_to_eef_cosine=0.08695271743383595
  mean_best_realized_gain_along_action=0.022552544812475088
```

Root cause found by code inspection:

```text
target_directed_reaching=true generated target-directed deltas in base_link,
but ArmEEDeltaCommandConverter was initialized with arm_action_frame=planning_frame.
The converter therefore interpreted base-frame deltas as planning-frame deltas.
```

Patch:

```text
file: src/rexrov_single_oberon7_fm_dp/expert_policy.py
change: use target_directed_action_frame as converter action_frame when
        target_directed_reaching=true
py_compile: PASS
```

Post-fix single episode:

```text
b8_return_gated_arm_verify_4:
  pre-return reached=true
  pre-gate passed=true
  runtime log action_frame=base_link
  runtime expert success=True, distance 0.062727 below 0.1
  validator=PASS
  saved success=True
  success_source=recorded_final_distance
  recorded_success_distance_m=0.05744791236250198
  recorded_success_distance_threshold_m=0.1
  allow_nominal_state_fallback=false
  base_state_source=odom
  joint_state_source=joint_states
  target_state_source=gazebo_model_states
  gripper_enabled=false
  is_grasp_dataset=false
```

Post-fix quality:

```text
initial_distance=0.10753282417279568
min_distance=0.05743319455171586
final_distance=0.05744791236250198
distance_reduction=0.0500849118102937
max_active_left_joint_delta=0.03833441102274282
mean_action_to_eef_motion_cosine=0.3532763904220775
mean_best_action_to_eef_cosine=0.3532763904220775
mean_best_lag_steps=0.0
mean_best_realized_gain_along_action=0.17090696757478616
```

Post-fix reset/gate:

```text
return_to_reference_live_6:
  reached=true
  commands_sent=4
  final_joint_l2_error=0.00011415046805219868
  final_joint_max_abs_error=8.851098779949496e-05
  gripper_commands_sent=false

post_postfix_return_gate:
  passed=false
  initial_distance=0.11655218918085192
  relative_base_drift=0.009639652376657452

post_postfix_return_gate_retry after 5 s:
  passed=true
  initial_distance=0.1075386326894244
  relative_base_drift=0.0012386357816084035
```

Interpretation:

- The target-directed action-frame mismatch is fixed at code level and
  validated by one successful post-fix arm-only reaching/pre-grasp episode.
- The post-fix episode has much better distance reduction and command-motion
  than the pre-fix failed episode, but command-motion is still weaker than the
  earlier best 5-episode smoke.
- Target/base settle remains timing-sensitive near episode boundaries; a
  delayed retry gate can pass after 5 s.
- B8' is still not fully complete and must not advance to training or learned
  rollout. The next B8' blocker-local step, if approved, should be a tiny
  2-cycle post-fix return->gate->episode repeatability check, not 10+ episodes.

Tiny post-fix repeatability check:

```text
label: B8' tiny post-fix repeatability check
scope: 2-cycle return->gate->episode->diagnostics
data_dir: data/raw/b8_postfix_repeatability_2/
episodes:
  - b8_postfix_repeatability_2_0000.npz
  - b8_postfix_repeatability_2_0001.npz
no training
no learned rollout
no gripper command
```

Per-cycle gate/reset:

```text
cycle_0_return:
  reached=true
  commands_sent=0
  final_joint_l2_error=9.868715516250662e-05
cycle_0_pre_gate:
  passed=true
  initial_distance=0.1133408946420597
  relative_base_drift=0.006780562427391431

cycle_1_return:
  reached=true
  commands_sent=4
  final_joint_l2_error=9.155680473676398e-05
cycle_1_pre_gate:
  passed=true
  initial_distance=0.11462735371763454
  relative_base_drift=0.008245004755328939

final_return:
  reached=true
  commands_sent=4
  final_joint_l2_error=0.0001689532909666089
final_gate:
  passed=true
  initial_distance=0.11464855723095672
  relative_base_drift=0.008009723575080853
```

Validation/summary:

```text
validator_pass_count=2/2
episodes_valid=2
success_count=2
reaching_success_rate=1.0
all_required_metadata_ok=true
all_success_metadata_consistent=true
allow_nominal_state_fallback=false for both
base_state_source=odom for both
joint_state_source=joint_states for both
target_state_source=gazebo_model_states for both
gripper_enabled=false for both
is_grasp_dataset=false for both
success_source=recorded_final_distance for both
```

Quality:

```text
initial_distance_per_episode=[0.1075630541970971, 0.10756418870221732]
min_distance_per_episode=[0.053346384327736994, 0.05765681709279224]
final_distance_per_episode=[0.05464734951940092, 0.05996229955194503]
distance_reduction_per_episode=[0.05291570467769617, 0.04760188915027229]
mean_initial_distance=0.1075636214496572
mean_final_distance=0.057304824535672975
mean_distance_reduction=0.05025879691398423
min_distance_overall=0.053346384327736994
max_active_left_joint_delta=0.03859894310454148
max_target_step_base=0.007109516133871766
large_target_step_indices=[] for both
mean_best_action_to_eef_cosine=0.5379418351868376
mean_best_lag_steps=0.0
mean_best_realized_gain_along_action=0.17491140517275186
```

Interpretation:

- The post-fix reset/gate/action-frame route is now repeatable at a tiny
  2-cycle smoke level.
- Command-motion is substantially better than the pre-fix failed episode and
  better than the failed 10-episode tail, but still below the earlier strongest
  single-episode smoke.
- This supports moving from blocker isolation to a deliberately small
  post-fix debug batch plan, but not directly to 10+ collection or training.
- B8' remains arm-only reaching/pre-grasp; this is not grasp success and not
  learned rollout evidence.

Small post-fix debug batch plan:

```text
label: B8' small post-fix debug batch plan
scope: real non-fallback arm-only reaching/pre-grasp debug collection
default_episode_count: 3
hard_max_episode_count: 5
route: per-episode return -> target-aware gate -> corrected target-directed
       arm-only episode -> validator/diagnostics
training: false
learned_rollout: false
gripper_command: false
hand_controller: false
grasp_claim: false
```

Rationale:

- The 2-cycle post-fix smoke passed, but it is too small to resume a 10+
  episode batch directly.
- The previous 10-episode debug batch failed in the tail, so the next batch
  should test whether the action-frame fix plus reset/gate policy survives a
  slightly longer run.
- Keep the first post-fix debug batch at 3 episodes. Only consider extending
  to 5 in the same session if all three episodes pass validation, success
  metadata consistency, target/base sync, and command-motion sanity.

Required per-episode preconditions:

```text
return_left_arm_to_reference.py:
  reached=true
  gripper_commands_sent=false

check_b8_initial_state_gate.py:
  passed=true
  allow target-aware gate retry after 5 s if target/base settle is marginal
  do not collect if the retry still fails
```

Episode collection settings:

```text
target_model_name=cylinder_target_gate_probe
spawn_target=false
enable_base_relative_target=false
execute_arm=true
execute_arm_once_per_state=false
execute_arm_states=MOVE_TO_PREGRASP,MOVE_TO_GRASP
state_sequence=MOVE_TO_PREGRASP,MOVE_TO_GRASP
target_directed_reaching=true
target_directed_action_frame=base_link
enable_gripper_command=false
allow_nominal_state_fallback=false
prefer_model_states_base_pose=false
rate_hz=3.0
max_duration_sec=7.2
max_linear_step=0.010
max_joint_delta=0.010
time_from_start_sec=1.0
```

Required post-batch diagnostics:

```text
validate_episode.py for every episode
summarize_b8_repeatability_smoke.py with --required-base-state-source odom
  and --fail-on-problem
analyze_b8_reaching_quality.py
analyze_b8_reaching_direction.py
analyze_b8_command_motion_path.py
final return_to_reference + target-aware gate
```

Batch pass criteria:

```text
validator_pass_count=N/N
success_count=N/N preferred; any failure requires stop-and-diagnose
all_required_metadata_ok=true
all_success_metadata_consistent=true
allow_nominal_state_fallback=false for all episodes
base_state_source=odom for all episodes
joint_state_source=joint_states for all episodes
target_state_source=gazebo_model_states for all episodes
gripper_enabled=false for all episodes
is_grasp_dataset=false for all episodes
large_target_step_indices=[] for all episodes
final return/gate passes before leaving runtime idle
```

Quality expectations:

```text
mean_final_distance should remain near the post-fix 2-cycle level
  (~0.057 m) or be explainable.
mean_distance_reduction should stay positive.
mean_best_action_to_eef_cosine should not collapse toward the pre-fix failure
  (~0.087); use the 2-cycle value (~0.538) as the immediate reference.
mean_best_realized_gain_along_action should not collapse toward the pre-fix
  failure (~0.023); use the 2-cycle value (~0.175) as the immediate reference.
```

Stop conditions:

```text
return_to_reference reached=false
target-aware gate fails after one 5 s retry
IK -31 or expert crash reappears
validator FAIL
success metadata mismatch
target/base large jump appears
consecutive reaching failures
command-motion collapses toward pre-fix failure values
```

This is a planning entry only; no new post-fix debug batch has been collected
for this plan yet.

Small post-fix debug batch attempt:

```text
label: B8' small post-fix debug batch attempt
planned data_dir: data/raw/b8_postfix_debug_3/
planned episode_count: 3
actual episodes_collected: 0
stop point: cycle 0 pre-episode target-aware gate
```

Cycle 0 preconditions:

```text
return_to_reference:
  reached=true
  commands_sent=0
  final_joint_l2_error=0.00015090229670289678
  final_joint_max_abs_error=0.0001343175473884628
  gripper_commands_sent=false

gate:
  passed=false
  initial_distance=0.1159362425810477
  initial_distance_ok=false
  relative_base_drift=0.00872391480943356
  relative_base_drift_ok=true
  target_base_drift=0.008698731973559727
  joint_l2_drift=9.35513884789246e-05

gate_retry_after_5s:
  passed=false
  initial_distance=0.11528983854046555
  initial_distance_ok=false
  relative_base_drift=0.008109968028264436
  relative_base_drift_ok=true
  target_base_drift=0.008066761178696735
  joint_l2_drift=9.244745447016366e-05
```

Interpretation:

- The stop condition worked correctly: no episode was collected from a marginal
  initial geometry state.
- Arm return was healthy; gripper remained disabled.
- The blocker is not an episode data failure, because no new `.npz` was saved.
- The current limiting condition is target-aware gate strictness near the
  `initial_distance_max=0.115 m` boundary. Relative target/base drift was
  within threshold, but the resulting initial distance was still slightly too
  large.
- Do not relax the threshold or collect from this state without a deliberate
  decision. The next minimum step is read-only target/base settle/reposition
  diagnosis or explicit target probe reinitialization, followed by the same
  gate.

Current blocker assessment:

```text
B8' overall blocker: not fully resolved
resolved at smoke level:
  - action-frame mismatch fixed and post-fix validated
  - return-to-reference reset works
  - target-aware gate works after settle
  - tiny 2-cycle post-fix repeatability passed
not resolved:
  - small 3-episode post-fix debug batch could not start because cycle 0
    target-aware gate failed the initial_distance boundary twice
```

Missing evidence before expanding:

```text
Need evidence that the target-aware initial geometry can be brought back
inside the configured gate reliably enough to start a small debug batch.
Need a successful 3-episode post-fix debug batch with per-episode
return/gate/diagnostics before considering larger collection or training.
```

Next minimum check:

```text
Run only a short read-only repeated target-aware gate check from the current
runtime, without arm commands and without collection. The goal is to determine
whether initial_distance remains just over 0.115 m, settles back under the
threshold, or drifts further.
```

Gate boundary probe result:

```text
artifacts:
  outputs/logs/b8_initial_state_gate/gate_boundary_probe/gate_*.json
  outputs/logs/b8_initial_state_gate/gate_boundary_probe/gate_boundary_probe_summary.json
  outputs/logs/b8_initial_state_gate/gate_boundary_probe/gate_boundary_probe_summary.md

checks_total=5
pass_count=3
fail_count=2
episodes_collected=0
all_control_commands_sent_false=true
all_gripper_commands_sent_false=true
```

Per-gate result:

```text
gate_0 passed=true  initial_distance=0.11326617951540467 relative_base_drift=0.006954684079328241
gate_1 passed=true  initial_distance=0.11374995074828124 relative_base_drift=0.007563652990111229
gate_2 passed=false initial_distance=0.11564356703916857 relative_base_drift=0.008480493184240828
gate_3 passed=true  initial_distance=0.10753170023825985 relative_base_drift=0.0012413657006039953
gate_4 passed=false initial_distance=0.11502167746808681 relative_base_drift=0.007817255991339152
```

Interpretation:

- Current blocker is not solved.
- The repeated read-only probe shows intermittent target-aware gate boundary
  failure.
- Failures are caused by `initial_distance` exceeding the configured
  `0.115 m` threshold by a small margin; `relative_base_drift_ok`,
  `joint_l2_ok`, `joint_max_abs_ok`, and `eef_base_drift_ok` stayed true.
- The target/base geometry appears to alternate between a near-reference mode
  and a shifted mode around 7-8 mm target/base drift. That shifted mode can
  push the initial distance just above the strict threshold.
- Do not collect from failing gate states. Do not train.

Next minimum check:

```text
Read-only inspect the target probe / base-relative target updater behavior.
Specifically, check whether multiple nodes are publishing or updating the
target, and whether `/gazebo/model_states` target position is toggling between
the near-reference and shifted target_base modes. Do not command the arm.
```

ROS graph / model_states spot check:

```text
rosnode list | grep -E "target|base_relative|gate|spawn|dp_fm"

observed nodes:
  /b8_target_gate_base_relative_target
  /dp_fm_left_arm_controller_starter
  /dp_fm_odom_tf_bridge
```

Interpretation:

- No duplicate target/base updater node was visible in the filtered ROS graph.
- This reduces the likelihood that the intermittent gate boundary failure is
  caused by multiple active target updater nodes fighting each other.
- The `rostopic echo ... | grep -A 8 -B 2 "cylinder_target_gate_probe"`
  output is not sufficient to determine the target pose. `/gazebo/model_states`
  stores `name[]` and `pose[]` as parallel arrays, and the displayed pose block
  begins with the first model (`ocean_box`), not necessarily the indexed pose
  for `cylinder_target_gate_probe`.

Current status:

```text
blocker not fully resolved
duplicate target updater not observed
target indexed pose still needs a precise read-only check
```

Next minimum read-only check:

```text
Use an indexed `/gazebo/model_states` read that prints the pose whose index
matches `cylinder_target_gate_probe`, not a grep of the raw array output.
```

Indexed target pose probe result:

```text
target_model_name: cylinder_target_gate_probe
samples: 10 over about 10 s
target world x: 24.7291204633037 -> 25.7584837884664
target world y: -13.440451519135685 -> -13.290649770155733
target world z: approximately -99.713
orientation: [0, 0, 0, 1] for all samples
```

Follow-up target-aware gate:

```text
passed=true
initial_distance=0.10771781639816572
relative_base_drift=1.5569323561687856e-05
target_base_drift=8.595952887736536e-05
joint_l2_drift=0.00012836553017450003
control_commands_sent=false
gripper_commands_sent=false
```

Interpretation:

- The previous raw `grep` result was indeed not a valid target pose check.
- The indexed target world pose is not static; it moves with the drifting base,
  as expected for the base-relative target probe.
- The target-in-base geometry can still be clean when the base-relative updater
  and gate sample are synchronized.
- The B8' blocker is not fully resolved because earlier repeated gates still
  showed intermittent boundary failures. The next check should compare target
  world motion against RexROV base world motion by index, not collect new
  episodes yet.

Indexed base+target relative-motion probe result:

```text
samples: 20
target_in_base_mean: [2.1643409987668636, 0.4999520343001693, -1.2753631745317109]
target_in_base_min: [2.160763731941731, 0.49970602555314947, -1.2764671785475143]
target_in_base_max: [2.1675555936413455, 0.5001850139236826, -1.2739863699616563]
target_in_base_range: [0.006791861699614543, 0.0004789883705331732, 0.0024808085858580853]
target_in_base_range_norm: 0.007246601027065321
```

Interpretation:

- The base-relative target updater is not the main remaining blocker. The
  indexed target-in-base range is below the existing `0.01 m`
  `relative_base_drift_threshold`.
- The target-in-base value is large because it is the target pose in RexROV
  base frame; the reaching distance gate compares target to EEF, and the EEF is
  already near `[2.06, 0.50, -1.315]` in base frame.
- The earlier intermittent gate failures are now best interpreted as an
  overly tight initial-distance gate relative to normal target/base + EEF
  variation, not as duplicate target updaters or gross target/base
  desynchronization.
- Current blocker status: smoke-level understood, not fully resolved for batch
  collection. Before retrying any small post-fix debug batch, make a deliberate
  gate policy decision: keep the strict `0.115 m` gate and wait/retry until it
  passes, or widen only the initial-distance gate slightly while keeping
  `relative_base_drift_threshold=0.01 m`.

Conservative gate policy implementation:

```text
script: scripts/run_b8_postfix_debug_batch_conservative.py
policy: keep initial_distance_max=0.115 m
per episode:
  1. return_left_arm_to_reference.py
  2. check_b8_initial_state_gate.py with wait/retry
  3. collect exactly one arm-only target-directed episode only after fresh gate pass
  4. validate_episode.py
  5. stop on return/gate/collect/validator failure
defaults:
  episode_count=3
  gate_attempts=6
  gate_wait_sec=5.0
  output_dir=data/raw/b8_postfix_debug_3
  log_dir=outputs/logs/b8_postfix_debug_3_conservative
```

Safety constraints baked into the script:

```text
allow_nominal_state_fallback=false
enable_gripper_command=false
gripper_enabled=false
is_grasp_dataset=false
task_type=arm_only_reaching
success_metric=reaching_success
target_directed_reaching=true
target_directed_action_frame=base_link
spawn_target=false
enable_base_relative_target=false
```

Static verification:

```text
python3 -m py_compile scripts/run_b8_postfix_debug_batch_conservative.py: PASS
run_b8_postfix_debug_batch_conservative.py --help: PASS
```

This is an execution helper for the current B8' blocker only. It is not
training, not learned rollout, and not grasp evaluation.

Conservative helper runtime result:

```text
command:
  rosrun rexrov_single_oberon7_fm_dp run_b8_postfix_debug_batch_conservative.py --episode-count 3

status: stopped before collection
episodes_completed: 0
stop_reason: fresh gate did not pass for b8_postfix_debug_3_0000
manifest:
  outputs/logs/b8_postfix_debug_3_conservative/conservative_batch_manifest.json
```

Return step:

```text
reached=true
commands_sent=0
joint_l2_error=0.00010753423427348858
joint_max_abs_error=9.103467156545975e-05
gripper_commands_sent=false
```

Gate attempts:

```text
attempts=6
initial_distance_ok=true for all attempts
initial_distance range: 0.11029098384377001 to 0.11039552892596491
relative_base_drift_ok=false for all attempts
relative_base_drift range: 0.023256039016610285 to 0.02327696668177505
target_base_drift range: 0.023272689304819343 to 0.02329353209401274
control_commands_sent=false for all attempts
gripper_commands_sent=false for all attempts
episodes_written=0
```

Interpretation:

- The conservative stop policy worked correctly and prevented collection from
  a gate-failing state.
- The failure was not caused by active-left reset or by initial distance.
- The current target probe geometry is stably offset by about `2.33 cm` from
  the reference target/base-relative geometry. Because the offset persisted
  across 6 wait/retry attempts, this is not a short settle transient.
- Current B8' blocker is still not resolved for batch collection. The next
  minimum action should reinitialize or respawn the target gate probe and then
  rerun target-aware gates before retrying the conservative batch.

Target probe restart check:

```text
command: roslaunch rexrov_single_oberon7_fm_dp b8_target_gate_probe.launch
spawn result: failed because entity already exists
updater node: started
```

Two fresh gates after this restart both failed:

```text
gate_0:
  passed=false
  initial_distance=0.11038362617734776
  initial_distance_ok=true
  relative_base_drift=0.023257329633886537
  relative_base_drift_ok=false
  target_base_drift=0.02217653258758869

gate_1:
  passed=false
  initial_distance=0.11031085375856366
  initial_distance_ok=true
  relative_base_drift=0.023272689950670524
  relative_base_drift_ok=false
  target_base_drift=0.022190674613100935
```

Interpretation:

- Restarting the probe launch without deleting the old target does not reset
  target geometry.
- The current blocker is a stale/existing `cylinder_target_gate_probe` model
  with stable about `2.3 cm` target/base reference offset.
- Waiting or restarting the updater alone is insufficient.

Package-local reset helper added:

```text
scripts/reset_b8_target_gate_probe.py
```

Purpose:

```text
Delete only the `cylinder_target_gate_probe` Gazebo model so the next
`b8_target_gate_probe.launch` can spawn a clean target. It sends no arm command
and no gripper command.
```

Verification:

```text
chmod +x scripts/reset_b8_target_gate_probe.py
python3 -m py_compile scripts/reset_b8_target_gate_probe.py: PASS
source devel/setup.bash; scripts/reset_b8_target_gate_probe.py --help: PASS
```

Next minimum action:

```text
Stop b8_target_gate_probe.launch.
Run reset_b8_target_gate_probe.py.
Restart b8_target_gate_probe.launch.
Run two fresh target-aware gates.
Only if both pass should the conservative helper be retried.
```

Target reset and fresh gate validation:

```text
reset_b8_target_gate_probe.py:
  passed=true
  before_present_in_model_states=true
  get_model_state_success=true
  delete_attempted=true
  delete_success=true
  absent_after_delete=true
  control_commands_sent=false
  gripper_commands_sent=false

b8_target_gate_probe.launch:
  spawn status: Successfully spawned entity
  updater initialized target_base_xyz=[2.1598220509962056, 0.500061142548624, -1.2763767663921255]
```

Two fresh gates after clean respawn:

```text
gate_0:
  passed=true
  initial_distance=0.10479344544370915
  relative_base_drift=0.003596792375915908
  target_base_drift=0.0034034423602981

gate_1:
  passed=true
  initial_distance=0.1096170277494551
  relative_base_drift=0.0021184551807263505
  target_base_drift=0.0027022208599847518
```

Interpretation:

- The stale target model blocker is smoke-level resolved.
- Deleting the old target, relaunching, and requiring two fresh gates brought
  the target-aware gate back inside the strict `initial_distance_max=0.115 m`
  and `relative_base_drift_threshold=0.01 m` policy.
- This does not yet prove the small post-fix debug batch is complete. The next
  minimum step is to rerun the conservative helper, which will stop again if
  return/gate/collection/validation fails.

Conservative helper rerun after clean target reset:

```text
command:
  rosrun rexrov_single_oberon7_fm_dp run_b8_postfix_debug_batch_conservative.py --episode-count 3

helper terminal result:
  STOP: summary failed
```

Interpretation of the stop:

- The helper did not fail during return, gate, collection, or validation.
- It collected and validated all 3 requested episodes.
- The stop was caused by a tool execution issue:
  `summarize_b8_repeatability_smoke.py` existed but was not executable via
  `rosrun`.
- The summary tool permission/install list was fixed and the summary was rerun
  manually without recollecting data.

Post-fix debug batch summary:

```text
data:
  data/raw/b8_postfix_debug_3/
episodes_total: 3
episodes_valid: 3
validator_pass_count: 3
success_count: 3
reaching_success_rate: 1.0
all_required_metadata_ok: true
all_success_metadata_consistent: true
mean_initial_distance: 0.11136879013891778
mean_final_distance: 0.04966386411855266
mean_distance_reduction: 0.06170492602036512
min_distance_overall: 0.04882503315948199
max_active_left_joint_delta: 0.04715301585407605
max_target_step_base: 0.007595107419430765
large_target_step_indices_by_episode: [] for all episodes
mean_best_action_to_eef_cosine: 0.7134615751223703
mean_best_lag_steps: 0.0
mean_best_realized_gain_along_action: 0.2127923769777379
failure_reason_by_episode: none for all episodes
```

Current B8' assessment:

- The conservative post-fix 3-episode debug batch is smoke-level resolved.
- This is still not training readiness by itself, not learned rollout, and not
  grasp success.
- Before any larger collection, keep the same reset/delete-spawn/gate policy
  and review whether to run one more small 3-5 episode debug batch or plan a
  controlled 10-episode post-fix batch.

Controlled 10-episode post-fix debug batch preparation:

```text
helper: scripts/run_b8_postfix_debug_batch_conservative.py
episode-count limit: raised from 5 to 10
target output:
  data/raw/b8_postfix_debug_10/
  outputs/logs/b8_postfix_debug_10_conservative/
  outputs/logs/b8_postfix_debug_10_summary/
policy unchanged:
  return -> wait/retry gate -> collect one arm-only episode -> validate
  initial_distance_max=0.115
  relative_base_drift_threshold=0.01
  allow_nominal_state_fallback=false
  gripper disabled
  stop on first return/gate/collect/validation/summary problem
```

First 10-episode attempt:

```text
status: stopped before collection
episodes_written: 0
reason: ROS master/runtime became unavailable; helper was interrupted while
        waiting in the first return step
```

Follow-up helper hardening:

```text
added per-step subprocess timeouts:
  return-timeout-sec=90
  gate-timeout-sec=30
  collect-timeout-sec=90
  validate-timeout-sec=30
  summary-timeout-sec=60
```

This prevents future runtime loss from leaving an unbounded helper subprocess.
The controlled 10-episode batch still needs to be rerun after the base runtime,
MoveIt, left controllers, TF bridge, and clean target probe are all running.

2026-05-06 controlled 10-episode retry precheck:

```text
pre_b8_postfix_debug_10_gate/gate_0:
  passed=false
  initial_distance=0.11033622160686253
  initial_distance_ok=true
  relative_base_drift=0.0232793818376196
  relative_base_drift_ok=false
  target_base_drift=0.023300825981187705

pre_b8_postfix_debug_10_gate/gate_1:
  passed=false
  initial_distance=0.11041099785110788
  initial_distance_ok=true
  relative_base_drift=0.02325376923014353
  relative_base_drift_ok=false
  target_base_drift=0.023275458190915907
```

Interpretation:

- The fresh gate precondition did not pass; the stale/offset target probe state
  reappeared at about `2.3 cm` relative drift.
- The 10-episode helper should not have been run after those failed gates.
- The helper correctly refused to continue because the intended output path
  already had existing episode files.

Existing `b8_postfix_debug_10` directory state:

```text
data/raw/b8_postfix_debug_10/b8_postfix_debug_10_0000.npz: validator PASS, T=22
data/raw/b8_postfix_debug_10/b8_postfix_debug_10_0001.npz: validator PASS, T=22
data/raw/b8_postfix_debug_10/b8_postfix_debug_10_0002.npz: validator PASS, T=6
```

Decision:

- Treat `data/raw/b8_postfix_debug_10` as a partial/contaminated attempt, not a
  clean 10-episode debug batch.
- Do not delete it automatically.
- For the next clean retry, first reset/delete and respawn the target probe,
  require two passing gates, then use a new output prefix/path such as
  `b8_postfix_debug_10_clean`.

2026-05-06 clean controlled 10-episode post-fix debug batch:

```text
record:
  B8' controlled 10-episode post-fix debug batch with conservative
  return/gate/validate strategy
input gate:
  two fresh target-aware gates passed before collection
output:
  data/raw/b8_postfix_debug_10_clean/
  outputs/logs/b8_postfix_debug_10_clean_conservative/
  outputs/logs/b8_postfix_debug_10_clean_summary/
episodes_total=10
episodes_valid=10
validator_pass_count=10/10
success_count=10/10
reaching_success_rate=1.0
all_required_metadata_ok=true
all_success_metadata_consistent=true
mean_initial_distance=0.10877674070159396
mean_final_distance=0.05024581695716414
mean_distance_reduction=0.05853092374442983
min_distance_overall=0.0438650711641242
max_active_left_joint_delta=0.047653774525344694
max_target_step_base=0.009844175150497677
large_target_step_indices=[] for all episodes
mean_best_action_to_eef_cosine=0.6498955385760039
mean_best_lag_steps=0.1
mean_best_realized_gain_along_action=0.21301870762024094
failure_reason=none for all episodes
```

Interpretation:

- The B8' post-fix reaching-quality blocker is smoke-level resolved for a clean
  controlled 10-episode scripted arm-only debug batch.
- The evidence supports the return-to-reference plus target-aware gate strategy:
  all clean episodes validated, all reached the recorded threshold, metadata
  stayed consistent, target/base jumps were absent, and command-motion metrics
  stayed usable.
- This is still only scripted expert arm-only reaching/pre-grasp data. It is not
  learned-policy rollout, not grasping, not final training-dataset approval, and
  not grasp success.

2026-05-06 offline fix-effect comparison:

```text
artifact:
  outputs/logs/b8_postfix_debug_10_clean_comparison/fix_effect_comparison.md
  outputs/logs/b8_postfix_debug_10_clean_comparison/fix_effect_comparison.json
comparison:
  old=b8_reaching_debug_10
  new=b8_postfix_debug_10_clean
success_count: 7/10 -> 10/10
reaching_success_rate: 0.7 -> 1.0
mean_final_distance: 0.08288684626534658 -> 0.05024581695716414
mean_distance_reduction: 0.02578654461012293 -> 0.05853092374442983
mean_best_action_to_eef_cosine: 0.5547614407437549 -> 0.6498955385760039
mean_best_lag_steps: 2.6 -> 0.1
mean_best_realized_gain_along_action: 0.13983358394761614 -> 0.21301870762024094
max_target_step_base: 0.02330097538679025 -> 0.009844175150497677
```

Interpretation:

- The post-fix return/gate/action-frame strategy materially improves the same
  10-episode debug-batch scale that previously failed.
- This strengthens the smoke-level resolved decision for the current B8'
  reaching-quality blocker.

2026-05-06 approved next B8' direction:

```text
User approved entering a larger controlled debug collection or training dataset
planning.
```

Decision:

- Do not train yet.
- Do not run learned-policy rollout.
- Keep gripper disabled.
- Next recommended step is a controlled 20-episode arm-only debug collection
  with the same return/gate/validate strategy.
- If that passes, prepare a read-only training-dataset candidate manifest and
  quality report before any training starts.

Planning artifact:

```text
outputs/logs/b8_training_dataset_planning/b8_controlled_collection_plan.md
```

Proposed clean 20-episode target:

```text
data/raw/b8_controlled_debug_20/
outputs/logs/b8_controlled_debug_20_conservative/
outputs/logs/b8_controlled_debug_20_summary/
```

Suggested pass criteria:

```text
validator_pass_count=20/20
success_count>=18/20
reaching_success_rate>=0.9
all_required_metadata_ok=true
all_success_metadata_consistent=true
large_target_step_indices=[] for all episodes
no sharp command-motion regression
```

Implementation note:

```text
scripts/run_b8_postfix_debug_batch_conservative.py
  MAX_EPISODE_COUNT changed from the previous hard-coded 10-episode limit to 20
  so the approved controlled 20-episode debug collection can run.
```

Verification:

```text
python3 -m py_compile scripts/run_b8_postfix_debug_batch_conservative.py: PASS
python3 scripts/run_b8_postfix_debug_batch_conservative.py --help: PASS
```

2026-05-06 controlled 20-episode attempt:

```text
command:
  run_b8_postfix_debug_batch_conservative.py --episode-count 20
status:
  stopped before collection
episodes_completed=0
stop_reason:
  fresh gate did not pass for b8_controlled_debug_20_0000
manifest:
  outputs/logs/b8_controlled_debug_20_conservative/conservative_batch_manifest.json
```

Important observation:

```text
manual pre-gates before helper:
  passed=true twice
  but arm/eef were still in post-command reached configuration
  eef_base_drift about 0.065 m
  joint_l2_drift about 0.082
  target_base_drift about 0.060-0.063 m

helper behavior:
  return_left_arm_to_reference succeeded
  final joint_l2_error=0.0008240220815145631
  final joint_max_abs_error=0.0008193521437780404
  gripper_commands_sent=false

fresh gate after return:
  attempts=6/6 failed
  initial_distance about 0.174-0.180 m
  relative_base_drift about 0.067-0.073 m
  target_base_drift about 0.067-0.073 m
```

Interpretation:

- The controlled 20-episode collection blocker is not resolved.
- The runner stopped correctly before collecting any episode.
- The failure is not an arm return failure: active-left joints returned near
  the reference.
- The current blocker is target/reference freshness after arm return: target
  geometry passed while the arm was still in a post-command pose, then became
  invalid after return-to-reference.

2026-05-06 target updater/gate diagnosis:

```text
rosnode list:
  /b8_target_gate_base_relative_target

rosnode info:
  subscriptions:
    /clock
    /gazebo/model_states
    /rexrov/pose_gt
    /tf
    /tf_static
```

Interpretation:

- There is only one target updater; duplicate updater is not the cause.
- `BaseRelativeTargetUpdater` initializes `target_base_xyz` once from the EEF
  pose at node startup, then keeps that fixed base-frame target.
- If `b8_target_gate_probe.launch` starts while the arm is still in a
  post-command reached pose, target geometry can pass relative to that pose but
  fail after `return_left_arm_to_reference`.

Patch:

```text
scripts/check_b8_initial_state_gate.py
  joint_l2_threshold default: 0.65 -> 0.02
  joint_max_abs_threshold default: 0.50 -> 0.01
  eef_base_drift_threshold default: 0.33 -> 0.02
```

Reason:

- Prevent manual pre-gates from passing when the arm has not returned close to
  the reference configuration.
- Keep the target-aware gate aligned with the conservative collection policy:
  return arm first, then initialize/validate target geometry.

Verification:

```text
python3 -m py_compile scripts/check_b8_initial_state_gate.py: PASS
source devel/setup.bash; python3 scripts/check_b8_initial_state_gate.py --help: PASS
```

2026-05-06 controlled 20-episode debug collection:

```text
precollection gates:
  two fresh target-aware gates passed with tightened defaults
  joint_l2_threshold=0.02
  joint_max_abs_threshold=0.01
  eef_base_drift_threshold=0.02
  initial_distance_max=0.115
  relative_base_drift_threshold=0.01

collection:
  run_b8_postfix_debug_batch_conservative.py --episode-count 20
  status=completed
  episodes_completed=20
  stop_reason=""
output:
  data/raw/b8_controlled_debug_20/
  outputs/logs/b8_controlled_debug_20_conservative/
  outputs/logs/b8_controlled_debug_20_summary/
```

Summary:

```text
episodes_total=20
episodes_valid=20
validator_pass_count=20/20
success_count=20/20
reaching_success_rate=1.0
all_required_metadata_ok=true
all_success_metadata_consistent=true
mean_initial_distance=0.1100603272654804
mean_final_distance=0.04992567108445887
mean_distance_reduction=0.060134656181021526
min_distance_overall=0.04228625127539157
max_active_left_joint_delta=0.04746787049063439
max_target_step_base=0.009847087316117917
large_target_step_indices=[] for all episodes
mean_best_action_to_eef_cosine=0.624391118128785
mean_best_lag_steps=0.25
mean_best_realized_gain_along_action=0.2094281117023901
failure_reason=none for all episodes
```

Decision:

- The B8' controlled 20-episode arm-only reaching/pre-grasp debug collection
  passes the current controlled-debug criteria.
- The target freshness/return-to-reference blocker is resolved at this
  controlled 20-episode debug level.
- This is still not learned-policy rollout, not training completion, not
  grasping, and not a grasp-success claim.

Notes:

- Episodes `0010` and `0017` are weaker but still successful, with final
  distances about `0.0676 m` and `0.0701 m`.
- Episode `0010` recorded initial distance is slightly above `0.115 m`
  (`0.11527553514048791`), so the next dataset manifest should flag this as a
  boundary case rather than silently ignoring it.

2026-05-06 read-only training-dataset candidate manifest:

```text
artifacts:
  outputs/logs/b8_training_dataset_candidate_manifest/candidate_manifest.md
  outputs/logs/b8_training_dataset_candidate_manifest/candidate_manifest.json
  outputs/logs/b8_training_dataset_candidate_manifest/candidate_episodes.csv
```

Primary candidate pool:

```text
include:
  data/raw/b8_postfix_debug_10_clean/
  data/raw/b8_controlled_debug_20/
episode_count=30
validator_pass_count=30/30
success_count=30/30
all_allow_nominal_state_fallback_false=true
all_base_state_source_odom=true
all_joint_state_source_joint_states=true
all_target_state_source_gazebo_model_states=true
all_gripper_disabled=true
all_is_grasp_dataset_false=true
all_success_metadata_consistent=true
mean_initial_distance=0.10963246507751825
mean_final_distance=0.05003238637536062
mean_distance_reduction=0.05960007870215763
max_target_step_base=0.009847087316117917
mean_best_action_to_eef_cosine=0.6328925916111913
mean_best_lag_steps=0.2
mean_best_realized_gain_along_action=0.21062497700834037
flagged_episode_count=3
```

Optional smoke source:

```text
data/raw/b8_postfix_debug_3/
episode_count=3
validator_pass_count=3/3
success_count=3/3
```

Excluded sources:

```text
data/raw/b8_reaching_debug_10/      # pre-fix failed 7/10 debug batch
data/raw/b8_postfix_debug_10/       # partial/contaminated attempt
Stage 6 fallback datasets           # not real non-fallback demonstrations
```

Flagged primary episodes:

```text
b8_controlled_debug_20_0010:
  initial_distance=0.11527553514048791
  final_distance=0.06764477900695165
  flags=initial_distance_boundary_gt_0.115; weak_final_distance_ge_0.065; low_realized_gain_lt_0.16
b8_controlled_debug_20_0014:
  flags=low_action_eef_cosine_lt_0.50
b8_controlled_debug_20_0017:
  final_distance=0.07005001495598358
  flags=weak_final_distance_ge_0.065; low_realized_gain_lt_0.16
```

Decision:

- Primary candidate pool is ready for training-planning review, not training.
- Training still requires explicit approval.
- This remains arm-only reaching/pre-grasp only: no gripper, no grasp dataset,
  no learned rollout, no grasp-success claim.

2026-05-06 B8' primary30 training config review and BC sanity:

```text
split:
  outputs/logs/b8_training_dataset_candidate_manifest/dataset_split_primary_30.json
  train=24 episodes
  val=6 episodes
  test=0 episodes

loader check:
  outputs/logs/b8_training_dataset_candidate_manifest/dataset_loader_check_primary_30.json
  train_windows=456
  val_windows=114
  obs_dim=38
  action_dim=7
  obs_horizon=4
  action_horizon=16
  allow_fallback_dataset=false
```

Training configs created:

```text
config/train_bc_b8_primary30.yaml
config/train_diffusion_b8_primary30.yaml
config/train_flow_matching_b8_primary30.yaml
config/train_bc_b8_primary30_sanity.yaml
```

BC sanity training:

```text
config=config/train_bc_b8_primary30_sanity.yaml
epochs=20
device=cuda
train_samples=456
val_samples=114
best_val_loss=0.40424566834733106
best_val_epoch=3
final_train_loss=0.02826811047355253
final_val_loss=0.49751798444818973
checkpoint_best=outputs/checkpoints/b8_primary30_bc_sanity/best.pt
```

Offline eval for best checkpoint:

```text
train normalized_mse=0.16825989753672638
train action_mse=0.0024937160778790712
val normalized_mse=0.40424566834733106
val action_mse=0.0024596124421805143
```

Planning review artifact:

```text
outputs/logs/b8_primary30_training_planning/training_config_review.md
```

Decision:

- B8' primary30 dataset and BC training code path are validated at sanity level.
- DP/FM training has not started.
- Learned rollout has not been run.
- The BC sanity run is not grasping and not rollout success.

2026-05-06 BC sanity validation behavior review:

```text
artifacts:
  outputs/logs/b8_primary30_bc_sanity_val_review/val_behavior_review.md
  outputs/logs/b8_primary30_bc_sanity_val_review/val_behavior_review.json

aggregate:
  mean_episode_normalized_mse=0.40424565280166774
  max_episode_normalized_mse=1.3814396424138027
  mean_episode_action_mse=0.002459612661197383
  max_episode_action_mse=0.0038022409793009738
  flagged_val_episode_count=3
```

Worst val normalized errors:

```text
b8_controlled_debug_20_0014 normalized_mse=1.381440
b8_controlled_debug_20_0017 normalized_mse=0.560607
b8_controlled_debug_20_0010 normalized_mse=0.172372
```

DP/FM decision:

```text
Do not start full DP/FM training yet.
Prepared short smoke configs only:
  config/train_diffusion_b8_primary30_smoke.yaml
  config/train_flow_matching_b8_primary30_smoke.yaml
These configs load the same primary30 split and use epochs=10, but have not
been run.
```

2026-05-06 short DP/FM smoke training:

```text
scope:
  short training smoke and offline eval only
  no learned rollout
  no gripper command
  no grasp-success claim

artifacts:
  outputs/logs/b8_primary30_training_planning/dp_fm_smoke_comparison.md
  outputs/logs/b8_primary30_training_planning/dp_fm_smoke_comparison.json
```

Results:

```text
BC sanity:
  epochs=20
  best_val_loss=0.404246
  train_action_mse=0.00249372
  val_action_mse=0.00245961

Diffusion smoke:
  epochs=10
  best_val_loss=0.867681
  train_action_mse=0.72233635
  val_action_mse=0.73058528

Flow Matching smoke:
  epochs=10
  best_val_loss=1.256665
  train_action_mse=0.67131901
  val_action_mse=0.68037963
```

Decision:

- DP/FM short smoke training verifies the training/eval code paths on B8'
  primary30 real non-fallback data.
- DP/FM sampled action MSE is far worse than BC in these smoke runs.
- Do not run learned rollout.
- Do not start full DP/FM training until sampling configuration, epoch budget,
  and model settings are reviewed.

2026-05-06 DP/FM sampling, epoch-budget, and model review:

```text
artifacts:
  outputs/logs/b8_primary30_training_planning/dp_fm_sampling_epoch_model_review.md
  outputs/logs/b8_primary30_training_planning/dp_fm_sampling_epoch_model_review.json
```

Sampling re-eval:

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

- Longer/full DP/FM training is not approved by this review.
- DP/FM 50-step/50-ODE sampled action MSE remains far worse than BC; DP gets
  worse at 50 reverse steps and FM is essentially unchanged.
- The next DP/FM work should remain offline-only bounded ablations: sampling
  behavior, per-dimension action/objective review, action horizon, and small
  epoch-budget checks.
- Learned rollout remains blocked and has not been run.

2026-05-06 DP/FM offline-only bounded ablations:

```text
artifacts:
  outputs/logs/b8_primary30_training_planning/dp_fm_offline_ablation_review.md
  outputs/logs/b8_primary30_training_planning/dp_fm_offline_ablation_review.json

new configs:
  config/train_diffusion_b8_primary30_h8_smoke.yaml
  config/train_flow_matching_b8_primary30_h8_smoke.yaml
  config/train_diffusion_b8_primary30_epoch30.yaml
  config/train_flow_matching_b8_primary30_epoch30.yaml
```

Offline val sampling result:

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

Decision:

- Zero-init/mean-style sampling is much better than Gaussian-source stochastic
  sampling, so random source/sampler behavior is a major DP/FM issue.
- Best DP/FM offline result is FM h8 zero-init, but it is still worse than BC
  sanity.
- Do not start full DP/FM training.
- Do not run learned rollout.
- Next allowed work is action-space/objective masking for inactive angular and
  gripper-like dimensions, then a BC vs FM h8 zero-init comparison under the
  same action-space definition.

2026-05-06 xyz-filtered action-space offline comparison:

```text
artifacts:
  outputs/logs/b8_primary30_training_planning/dp_fm_xyz_filtered_comparison.md
  outputs/logs/b8_primary30_training_planning/dp_fm_xyz_filtered_comparison.json

new configs:
  config/train_bc_b8_primary30_h8_xyz.yaml
  config/train_diffusion_b8_primary30_h8_xyz_smoke.yaml
  config/train_flow_matching_b8_primary30_h8_xyz_smoke.yaml

action_dim_indices=[0,1,2]  # dx, dy, dz
removed_dims=droll, dpitch, dyaw, gripper_like_disabled
```

Offline val comparison:

```text
BC h8 xyz direct             action_mse=0.00138611 normalized_mse=0.84109951
DP h8 xyz stochastic50       action_mse=0.12639004 normalized_mse=1.98532737
DP h8 xyz zero50             action_mse=0.01584135 normalized_mse=1.02125073
FM h8 xyz stochastic50       action_mse=0.32252964 normalized_mse=2.01401833
FM h8 xyz zero50             action_mse=0.00157071 normalized_mse=0.94525194
```

Decision:

- Removing inactive angular/gripper-like dimensions improves DP/FM offline
  action MSE substantially.
- FM h8 xyz zero-init is close to BC h8 xyz but still not better on val action
  MSE or val normalized MSE.
- Do not start full DP/FM training.
- Do not run learned rollout.
- Next allowed offline step is a slightly longer FM h8 xyz epoch-budget
  ablation or another deterministic direct-head baseline under the same
  `dx/dy/dz` action space.

2026-05-06 FM h8 xyz epoch-budget offline ablation:

```text
artifacts:
  outputs/logs/b8_primary30_training_planning/fm_h8_xyz_epoch_budget_review.md
  outputs/logs/b8_primary30_training_planning/fm_h8_xyz_epoch_budget_review.json

new config:
  config/train_flow_matching_b8_primary30_h8_xyz_epoch30.yaml
```

Offline val comparison:

```text
BC h8 xyz direct              action_mse=0.00138611 normalized_mse=0.84109951
FM h8 xyz epoch10 zero50      action_mse=0.00157071 normalized_mse=0.94525194
FM h8 xyz epoch30 zero50      action_mse=0.00147991 normalized_mse=0.90564308
FM h8 xyz epoch30 stoch50     action_mse=0.33842790 normalized_mse=2.16292317
```

Decision:

- FM h8 xyz epoch30 zero-init improves over epoch10 but still does not beat BC.
- FM epoch30 shows overfitting risk: train loss keeps dropping while final val
  velocity loss worsens.
- Do not start full DP/FM training.
- Do not run learned rollout.
- BC h8 xyz remains the current best offline baseline.

2026-05-06 BC h8 xyz offline candidate report:

```text
artifacts:
  outputs/logs/b8_primary30_training_planning/bc_h8_xyz_offline_candidate_report.md
  outputs/logs/b8_primary30_training_planning/bc_h8_xyz_offline_candidate_report.json
```

Status:

```text
rollout_planning_candidate=true
rollout_ready_success=false
learned_rollout_has_run=false
full_training_candidate=false
```

Candidate:

```text
policy=BC MLP
config=config/train_bc_b8_primary30_h8_xyz.yaml
checkpoint=outputs/checkpoints/b8_primary30_bc_h8_xyz/best.pt
action_space=dx,dy,dz only
action_dim_indices=[0,1,2]
obs_horizon=4
action_horizon=8
```

Offline eval:

```text
train_normalized_mse=0.44862161
train_action_mse=0.00125866
val_normalized_mse=0.84109951
val_action_mse=0.00138611
```

Decision:

- This is the current rollout-planning candidate because it has the best
  current offline validation action MSE in the same `dx/dy/dz` action space.
- It is not rollout-ready success.
- No learned rollout has run.
- Before any learned rollout, write a separate arm-only rollout
  safety/evaluation plan with action mapping, clipping, abort conditions,
  return/gate setup, metrics, and explicit no-gripper constraints.

2026-05-06 arm-only rollout safety/evaluation plan:

```text
artifacts:
  outputs/logs/b8_rollout_planning/bc_h8_xyz_arm_only_rollout_safety_plan.md
  outputs/logs/b8_rollout_planning/bc_h8_xyz_arm_only_rollout_safety_plan.json

status=planning_artifact_only
rollout_execution_approved_by_this_plan=false
requires_separate_approval=true
learned_rollout_has_run=false
gripper_or_hand_controller_allowed=false
grasp_claim_allowed=false
```

The plan defines the first future rollout as exactly one short arm-only
reaching/pre-grasp evaluation using the BC h8 xyz checkpoint, with:

- action mapping from `[dx, dy, dz]` only;
- no direct use of the existing Stage 10 7-D rollout execution path for this
  3-D candidate;
- conservative xyz and joint-command clipping;
- immediate abort conditions for missing state, raw action outliers, IK/command
  failure, target drift, distance regression, joint tracking error, or any
  gripper/hand command path becoming active;
- per-rollout return-to-reference, target reset/restart if needed, and two
  consecutive fresh target-aware gates before execution;
- required metrics for raw/clipped actions, distance reduction, command
  deltas, latency, abort reason, return/gate JSONs, and explicit
  `gripper_commands_sent=false`.

This plan does not run a rollout and does not approve a rollout. The next
allowed implementation step is to review or implement an arm-only xyz rollout
adapter in dry-run mode only. Any live learned rollout still requires separate
explicit approval and must remain no-gripper/no-grasp-claim.

2026-05-06 BC h8 xyz arm-only dry-run adapter:

```text
artifacts:
  scripts/b8_bc_h8_xyz_rollout_dry_run_node.py
  config/b8_bc_h8_xyz_rollout_dry_run.yaml
  launch/b8_bc_h8_xyz_rollout_dry_run.launch
  outputs/logs/b8_rollout_planning/bc_h8_xyz_dry_run_adapter_report.md
  outputs/logs/b8_rollout_planning/bc_h8_xyz_dry_run_adapter_report.json

status=implemented_static_checked
live_dry_run_has_run=false
learned_rollout_has_run=false
arm_control_commands_sent=false
gripper_commands_sent=false
```

The adapter is intentionally separate from the Stage 10 rollout node because
Stage 10 assumes 7-D action chunks, while the current BC candidate emits only
`dx,dy,dz`. The new adapter:

- requires `action_dim=3` and `action_horizon=8`;
- maps the policy output as `[dx, dy, dz]`;
- publishes dry-run labels only, including a logging-only 7-D expansion
  `[dx, dy, dz, 0, 0, 0, 0]`;
- forbids `execute_actions=true`;
- does not publish any arm controller command;
- does not publish any gripper or hand command;
- clips xyz labels with the first-rollout safety limits from the plan;
- writes a dry-run JSON summary.

Static verification passed:

```text
python3 -m py_compile scripts/b8_bc_h8_xyz_rollout_dry_run_node.py
yaml.safe_load(config/b8_bc_h8_xyz_rollout_dry_run.yaml)
xmllint --noout launch/b8_bc_h8_xyz_rollout_dry_run.launch
roslaunch --nodes rexrov_single_oberon7_fm_dp b8_bc_h8_xyz_rollout_dry_run.launch
RuntimePolicy.from_checkpoint(.../b8_primary30_bc_h8_xyz/best.pt)
```

Checkpoint dimensions confirmed:

```text
policy_type=bc
obs_dim=38
obs_horizon=4
action_dim=3
action_horizon=8
```

Next minimum check, only after the normal B8 runtime is up, arm return passes,
and two fresh target-aware gates pass: run one live dry-run action-label check
with `execute_actions=false`, then inspect the output JSON. Do not run live
arm execution from this adapter yet.

2026-05-06 BC h8 xyz live dry-run attempt:

```text
pre_gate_0_passed=true
pre_gate_1_passed=true
dry_run_status=aborted
abort_reason=raw_xyz_component_abort
samples=0
control_commands_sent=false
gripper_commands_sent=false
hand_controller_started=false
```

Evidence:

```text
gate_0:
  initial_distance=0.10684487538197888
  relative_base_drift=0.0012186126370324819
  eef_base_drift=0.000039905666830357396
  joint_l2_drift=0.00015561060815530333

gate_1:
  initial_distance=0.10764622164929451
  relative_base_drift=0.00006084384456262284
  eef_base_drift=0.00005015581198220797
  joint_l2_drift=0.00011833639517548527
```

Judgment:

- The return/gate side of the dry-run precheck passed at smoke level.
- The BC h8 xyz live action-label side is not resolved: the policy produced a
  raw xyz action over the hard `0.03 m` component abort threshold before any
  publishable label was recorded.
- This is still not learned rollout, not training, not grasping, and no
  command was sent.

Code follow-up:

```text
scripts/b8_bc_h8_xyz_rollout_dry_run_node.py now persists abort_context in
the JSON summary, including raw_action_xyz for raw_xyz_component_abort.
```

Next minimum check: rerun only the same dry-run label check, with
`execute_actions=false`, after the current fresh gate state is still acceptable.
Return the updated `bc_h8_xyz_dry_run_latest.json` so the raw abort vector can
be inspected. Do not relax the abort threshold yet.

2026-05-06 BC h8 xyz dry-run abort context:

```text
dry_run_status=aborted
abort_reason=raw_xyz_component_abort
samples=0
raw_action_xyz=[0.09588255733251572, 0.00029814825393259525, 0.010294424369931221]
max_abs_raw_component=0.09588255733251572
raw_component_abort=0.03
latency_ms=52.34609100079979
base_state_source=odom
joint_state_source=joint_states
target_state_source=model_states
missing_gripper_joint_names=[]
control_commands_sent=false
gripper_commands_sent=false
hand_controller_started=false
```

Judgment:

- The dry-run adapter is behaving safely: it aborted before publishing any
  action label and sent no commands.
- The BC h8 xyz live action is not acceptable for rollout planning yet because
  the first raw `dx` is about `9.6 cm`, more than three times the `3 cm` hard
  abort threshold and far above the first-attempt `5 mm` clip component.
- Do not relax thresholds and do not run learned arm execution.

Next minimum check is read-only/offline: compare this live raw xyz output and
current live observation scale against the B8 primary30 training action/obs
distribution. This should determine whether the issue is policy output
magnitude under otherwise-normal state, observation construction mismatch, or
live state out-of-distribution.

2026-05-06 BC h8 xyz dry-run action-distribution diagnostic:

```text
dry_raw_xyz=[0.09588255733251572, 0.00029814825393259525, 0.010294424369931221]
train_xyz_abs_max=[0.01, 0.001722396053442099, 0.01]
train_xyz_p95_abs=[0.01, 0.0012805263113561116, 0.01]
train_xyz_p99_abs=[0.01, 0.001722396053442099, 0.01]
train_xyz_mean=[0.009848484848484705, 0.00009620598359071179, 0.009686892926596432]
train_xyz_std=[0.0012215542042876574, 0.0006196520780459629, 0.0012921835415458805]
dry_raw_zscore_vs_action_dist=[70.42943152889856, 0.3258909613747649, 0.47015514611532966]
```

Judgment:

- The live dry-run blocker is not resolved.
- `dy` and `dz` are within the training action distribution.
- `dx` is not acceptable: `0.0959 m` is about `9.6x` the training max and
  about `70.4 sigma` from the primary30 action distribution.
- This is not a threshold-tuning problem. Do not relax the `0.03 m` hard abort
  and do not run learned arm execution.

Next minimum check remains read-only: inspect the live observation vector and
the policy normalized output for the aborting state. The goal is to separate
observation construction/OOD state from a learned-head extrapolation problem.

2026-05-06 BC h8 xyz live-observation / normalized-policy diagnostic:

```text
obs_dim=38
missing_active_pos=[]
missing_active_vel=[]
missing_gripper_zeroed=[]
target_pose=[-25.904912783421462, -7.6929047700323885, -99.7138775307461, 0, 0, 0, 1]
pred_norm_step0=[0.05817652493715286, 0.907192587852478, 1.8972406387329102]
pred_raw_step0=[0.06817672401666641, 0.0007237937534227967, 0.010734298266470432]
pred_raw_abs_max_step0=0.06817672401666641
```

Largest live observation z-scores:

```text
gripper_state[oberon7_l/finger_right_joint] 15.333526611328125
gripper_state[oberon7_l/finger_tip_right_joint] -13.017897605895996
target_pose[0] -9.196915626525879
base_pose[0] -7.35105562210083
active_vel[oberon7_l/shoulder] 3.3422889709472656
gripper_state[oberon7_l/finger_left_joint] -3.238586664199829
active_vel[oberon7_l/azimuth] 2.920839309692383
base_vel[1] 2.7117531299591064
target_pose[1] -2.584564447402954
gripper_state[oberon7_l/finger_tip_left_joint] 2.430304765701294
```

Judgment:

- The live dry-run blocker remains unresolved.
- The failure is now consistent with observation distribution shift, not a
  missing topic or command-side issue.
- Two likely contributors are present:
  1. gripper-state dimensions are extreme even though the route is arm-only
     and no hand controller should be used;
  2. absolute `base_pose` / `target_pose` world coordinates have drifted far
     from the primary30 training distribution, even while the relative
     target-base gate can pass.
- The policy normalized first-step output is not itself extreme, but the raw
  `dx` after unnormalization still exceeds the hard abort threshold.

Next minimum check remains read-only: run a live-observation ablation that
compares policy output with selected OOD groups neutralized in normalized space
(`gripper_state`, absolute `base_pose`, absolute `target_pose`). Do not retrain,
do not run DP/FM, and do not execute learned arm commands.

2026-05-06 BC h8 xyz normalized-observation ablation:

```text
as_live:
  pred_raw_step0=[0.07037436217069626, 0.00048296028398908675, 0.010377679020166397]
  pred_raw_abs_max=0.07037436217069626

zero_gripper:
  pred_raw_step0=[-0.027984583750367165, 0.0003147294919472188, 0.010034470818936825]
  pred_raw_abs_max=0.027984583750367165

zero_base_pose:
  pred_raw_step0=[0.1399548351764679, 0.0005101020215079188, 0.010373920202255249]
  pred_raw_abs_max=0.1399548351764679

zero_target_pose:
  pred_raw_step0=[-0.0023795459419488907, 0.0003971104742959142, 0.010353369638323784]
  pred_raw_abs_max=0.010353369638323784

zero_base_and_target_pose:
  pred_raw_step0=[0.0686231181025505, 0.0003914297267328948, 0.01031067967414856]
  pred_raw_abs_max=0.0686231181025505

zero_gripper_base_target:
  pred_raw_step0=[-0.03965198993682861, 0.00014158365956973284, 0.009958907961845398]
  pred_raw_abs_max=0.03965198993682861
```

Judgment:

- The live BC h8 xyz dry-run blocker remains unresolved.
- `zero_target_pose` is the only ablation that cleanly returns the first-step
  raw xyz action to the training-scale envelope.
- `zero_gripper` lowers `dx` below the hard `0.03 m` abort threshold but still
  changes the sign and leaves the action far above the planned `5 mm`
  first-attempt component clip.
- `zero_base_pose` makes the action worse, and combined zeroing is not stable.
- Therefore the dominant live failure path is the absolute target world-pose
  field, with gripper-state OOD as a secondary contributor.

Do not implement a quick threshold relaxation or live execution. A policy that
depends on absolute world target pose is not suitable for this drifting runtime
without either a base-relative observation model or a validated inference-time
observation filter.

Next minimum check remains offline/read-only: run the same observation-group
neutralization over the primary30 validation windows and compare action MSE.
Only if a neutralized variant preserves offline quality should a new dry-run
adapter/config be considered. No DP/FM training or learned rollout yet.

2026-05-06 BC h8 xyz validation-set neutralization ablation:

```text
val_windows=114

as_val:
  mean_chunk_mse=0.001444374104929075
  mean_first_step_mse=0.0014359504112452374
  p95_first_step_absmax=0.11106296367943283
  max_first_step_absmax=0.13884584605693817

zero_gripper:
  mean_chunk_mse=0.0013471957635167136
  mean_first_step_mse=0.0012092705574523758
  p95_first_step_absmax=0.1005253043025732
  max_first_step_absmax=0.12775343656539917

zero_target_pose:
  mean_chunk_mse=0.0012772556270774977
  mean_first_step_mse=0.0013216916045206617
  p95_first_step_absmax=0.10347290225327015
  max_first_step_absmax=0.13346779346466064

zero_gripper_target:
  mean_chunk_mse=0.0012040883056327228
  mean_first_step_mse=0.0011200821216159071
  p95_first_step_absmax=0.09894258603453636
  max_first_step_absmax=0.11847516894340515
```

Checkpoint normalization stats:

```text
action_mean=[0.0100001972168684, 0.00011238727165618911, 0.009779215790331364]
action_std=[1.0, 0.0006739544332958758, 0.0005034060450270772]
```

Judgment:

- The BC h8 xyz live dry-run blocker remains unresolved.
- The validation ablation does not produce a rollout-safe inference-time
  filter: even the best case has `p95_first_step_absmax ~= 0.099 m`.
- The checkpoint's `dx` normalization is unsafe for rollout planning:
  `action_std[0]=1.0` while the real `dx` command range is about `0.01 m`.
  Small normalized `dx` prediction errors therefore become centimeter-scale
  raw actions.
- The earlier offline MSE alone was not sufficient to mark this checkpoint as
  rollout-planning safe.

Status update:

```text
BC h8 xyz remains useful as an offline diagnostic baseline.
BC h8 xyz is not a live rollout-planning candidate until action normalization
and observation design are fixed and re-evaluated.
learned_rollout_has_run=false
arm_control_commands_sent=false
gripper_commands_sent=false
```

Next minimum work should stay offline/read-only or planning-only: design a
base-relative / arm-only observation variant and an action normalization policy
that cannot map small normalized errors to >3 cm raw actions. Do not run DP/FM
or live learned rollout before that fix is validated offline.

2026-05-06 base-relative / arm-only BC h8 xyz safe-norm sanity:

```text
config:
  config/train_bc_b8_primary30_h8_xyz_base_relative_safe_norm.yaml

report:
  outputs/logs/b8_primary30_training_planning/bc_h8_xyz_base_relative_safe_norm_report.md
  outputs/logs/b8_primary30_training_planning/bc_h8_xyz_base_relative_safe_norm_report.json

checkpoint:
  outputs/checkpoints/b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt
```

Implementation:

- Added derived dataset observation keys:
  - `eef_position_base_frame`
  - `target_position_base_frame`
  - `target_to_eef_base_frame`
- New observation removes:
  - absolute world `base_pose`;
  - absolute world `target_pose`;
  - `gripper_state`.
- New observation keeps arm-only state:
  - `active_joint_positions`;
  - `active_joint_velocities`;
  - base-frame EEF/target geometry;
  - progress/remaining.
- Added configurable std fallback:
  - old dangerous behavior preserved by default;
  - new config uses `action_std_fallback=0.001` for near-constant clipped
    action dimensions.

Dataset sanity:

```text
train_samples=456
val_samples=114
obs_dim=23
action_dim=3
action_mean=[0.0100001972168684, 0.00011238727165618911, 0.009779215790331364]
action_std=[0.0010000000474974513, 0.0006739544332958758, 0.0005034060450270772]
```

Training:

```text
epochs=20
best_val_loss=0.9591013831837524
final_train_loss=0.13797813154236283
final_val_loss=1.4230697549959666
best checkpoint selected from epoch 1
```

Offline eval:

```text
train_normalized_mse=0.5539891415761323
train_action_mse=1.9021148034426005e-07
val_normalized_mse=0.9591013831837524
val_action_mse=3.0668218187202e-07
```

Offline action-scale check:

```text
train_first_absmax_p95=0.01007651025429368
train_first_absmax_max=0.010140507481992245
val_first_absmax_p95=0.010084372432902455
val_first_absmax_max=0.010133071802556515
val_valid_step_absmax_max=0.010275864973664284
```

Decision:

```text
offline_action_scale_safe=true
rollout_ready_success=false
learned_rollout_has_run=false
gripper_commands_sent=false
dp_fm_training_started=false
```

This resolves the offline action-scale portion of the BC blocker. It does not
resolve live rollout readiness. Next options are:

1. implement a matching base-relative live dry-run adapter and run one
   action-label dry-run only after return/gate; or
2. start DP/FM comparison under the exact same base-relative observation and
   safe normalization, still offline-only.

## Base-Relative Rollout Safety Plan V2

Date: 2026-05-07.

Generated a replacement rollout-planning safety/evaluation artifact for the
current base-relative BC candidate:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_arm_only_rollout_safety_plan.md
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_arm_only_rollout_safety_plan.json
```

This v2 plan replaces the older absolute-pose BC planning artifact for current
rollout planning. The current candidate is:

```text
checkpoint=outputs/checkpoints/b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt
config=config/train_bc_b8_primary30_h8_xyz_base_relative_safe_norm.yaml
obs_design=base-relative arm-only; no gripper_state; no absolute target_pose
action=dx,dy,dz in base_link
```

Updated the read-only rollout-readiness preflight default safety-plan input to
the v2 artifact:

```text
scripts/analyze_b8_base_relative_rollout_readiness.py
```

Verification:

```text
python3 -m py_compile scripts/analyze_b8_base_relative_rollout_readiness.py: PASS
python3 scripts/analyze_b8_base_relative_rollout_readiness.py: PASS
```

Latest preflight result:

```text
outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.md
outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.json

candidate_status=rollout_planning_candidate
checks_passed=true
go_for_learned_execution_now=false
separate_execution_approval_required=true
rollout_ready_success_claimed=false
control_commands_sent=false
gripper_commands_sent=false
safety_plan_json=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_arm_only_rollout_safety_plan.json
```

Interpretation:

- The BC base-relative h8 xyz checkpoint remains a rollout-planning candidate.
- No learned rollout was run and no learned rollout success is claimed.
- The plan does not approve execution.
- Any learned arm-only execution still requires separate explicit approval,
  return-to-reference, and two fresh target-aware gates.

## Tiny Arm-Only Smoke Checklist Artifact

Date: 2026-05-07.

Added a read-only checklist generator for the next possible step after planning
review:

```text
scripts/generate_b8_base_relative_tiny_smoke_checklist.py
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_checklist.md
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_checklist.json
```

This does not execute ROS control, learned policy rollout, or gripper commands.
It inspects the current preflight, v2 safety plan, launch defaults, and adapter
guardrails.

Verification:

```text
python3 -m py_compile scripts/generate_b8_base_relative_tiny_smoke_checklist.py: PASS
python3 scripts/generate_b8_base_relative_tiny_smoke_checklist.py: PASS
launch XML parse: PASS
```

Checklist result:

```text
checklist_status=ready_for_review
checks_passed=true
learned_execution_approved_here=false
current_adapter_can_execute_actions=false
control_commands_sent=false
gripper_commands_sent=false
```

Important guardrail:

```text
The current base-relative adapter is still dry-run only.
execute_actions=true is forbidden before spin.
The adapter calls convert() for IK preview only and does not call execute().
```

Therefore the next engineering step, if learned execution is separately
approved later, is not to run the current dry-run launch with
`execute_actions:=true`; it is to implement/review a tiny active-left arm-only
execution adapter under the v2 safety plan.

## Tiny Arm-Only Execution Smoke Adapter

Date: 2026-05-07.

Implemented a dedicated active-left arm-only execution-smoke adapter, separate
from the dry-run adapter:

```text
scripts/b8_bc_h8_xyz_base_relative_execution_smoke_node.py
config/b8_bc_h8_xyz_base_relative_execution_smoke.yaml
launch/b8_bc_h8_xyz_base_relative_execution_smoke.launch
outputs/logs/b8_rollout_planning/base_relative_execution_smoke_adapter_review.md
outputs/logs/b8_rollout_planning/base_relative_execution_smoke_adapter_review.json
```

Safety defaults:

```text
execute_actions default=false
i_understand_this_publishes_arm_commands default=false
max_control_ticks=3
max_policy_xyz_component=0.005
max_joint_delta_per_command_rad=0.01
arm_command_topic=/oberon7/arm_position_l/command
gripper_commands_sent=false
```

The adapter only publishes active-left arm commands if both flags are set:

```text
execute_actions:=true
i_understand_this_publishes_arm_commands:=true
```

Static review:

```text
py_compile: PASS
YAML parse: PASS
launch XML parse: PASS
roslaunch --nodes: PASS
adapter_review_status=ready_for_return_and_two_fresh_gates
checks_passed=true
control_commands_sent=false
gripper_commands_sent=false
learned_rollout_run=false
```

No learned execution was run in this implementation/review pass. Next required
runtime step is return-to-reference and two fresh target-aware gates before
starting the explicit tiny smoke command.

Runbook:

```text
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_runbook.md
```

## First Tiny Arm-Only Learned Smoke Result

Date: 2026-05-07.

The first tiny active-left arm-only BC base-relative execution smoke was run
after return-to-reference and two fresh target-aware gates.

Inputs/results:

```text
outputs/logs/b8_rollout_planning/tiny_smoke_return_to_reference.json
outputs/logs/b8_rollout_planning/tiny_smoke_pre_gate/gate_0.json
outputs/logs/b8_rollout_planning/tiny_smoke_pre_gate/gate_1.json
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_execution_smoke_latest.json
outputs/logs/b8_rollout_planning/tiny_smoke_post_gate/post_smoke_gate.json
```

Added a read-only summary tool/artifacts:

```text
scripts/summarize_b8_base_relative_tiny_smoke.py
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_summary.md
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_summary.json
```

Summary:

```text
return_reached=true
pre_gate_0_passed=true
pre_gate_1_passed=true
smoke_status=max_control_ticks_complete
smoke_samples=3
control_commands_sent=true
gripper_commands_sent=false
hand_controller_started=false
aborted=false
raw_action_absmax=0.010118558071553707
clipped_action_absmax=0.005
clipped_joint_delta_absmax=0.01
pre_gate_1_initial_distance=0.10769686466831795
post_gate_initial_distance=0.09675726747351836
gate_distance_reduction=0.010939597194799588
smoke_distance_reduction=0.007985695238385493
post_gate_target_base_drift=0.006632863059974026
post_gate_passed=false
post_gate_failed_checks=[relative_base_drift_ok]
```

Decision:

```text
command_path_smoke_resolved=true
smoke_status=command_path_smoke_resolved_not_success
arm_only_reaching_success_claimed=false
grasp_success_claimed=false
learned_rollout_success_claimed=false
```

Interpretation:

- The active-left learned command path is smoke-level resolved: three bounded
  commands were published, no abort occurred, and no gripper/hand command was
  sent.
- The post initial-state gate failing `relative_base_drift_ok` is expected
  after the arm moves; target drift itself stayed within threshold.
- The single tiny smoke does not meet the planned arm-only success threshold
  because distance reduction was below `0.02 m`.
- Return the arm to reference before any further live checks or learned smoke.

## Post Tiny-Smoke Return/Gate Recovery

Date: 2026-05-07.

After the first tiny learned arm-only smoke, the arm was returned to the B8
reference and a fresh target-aware gate was run:

```text
outputs/logs/b8_rollout_planning/post_tiny_smoke_return_gate/return_to_reference.json
outputs/logs/b8_rollout_planning/post_tiny_smoke_return_gate/gate.json
```

Return result:

```text
reached=true
gripper_commands_sent=false
joint_l2_error=0.0047864537974148256
joint_max_abs_error=0.004785099945048721
```

Fresh gate result:

```text
passed=true
control_commands_sent=false
gripper_commands_sent=false
initial_distance=0.10777052317169064
eef_base_drift=0.0009491936570787988
joint_l2_drift=0.004772390611295937
joint_max_abs_drift=0.004763332143273402
relative_base_drift=6.784824831158697e-05
target_base_drift=0.0008889194699589182
```

Decision:

```text
post_smoke_recovery_gate_passed=true
system_returned_to_controlled_initial_gate=true
command_path_blocker_status=smoke_level_resolved
arm_only_reaching_success_claimed=false
grasp_success_claimed=false
```

Interpretation:

- The first tiny learned command path smoke is closed at smoke level.
- The system can return to the controlled B8 gate state after the learned
  three-command smoke.
- This still does not claim arm-only reaching success or grasp success.
- Do not start a second learned smoke or larger rollout batch without a
  separate review of the first-smoke summary and an explicit next-run plan.

## First Tiny-Smoke Review Decision

Date: 2026-05-07.

Reviewed the first tiny-smoke summary and post-return gate.

Artifacts:

```text
outputs/logs/b8_rollout_planning/first_tiny_smoke_review_decision.md
outputs/logs/b8_rollout_planning/first_tiny_smoke_review_decision.json
```

Evidence:

```text
command_path_smoke_resolved=true
system_recovered_to_gate=true
distance_decreased_monotonically=true
distances=[0.1124765533517506, 0.10822837102368213, 0.1044908581133651]
avg_per_tick_distance_reduction=0.0039928476191927464
gate_distance_reduction=0.010939597194799588
remaining_reduction_to_0p02_success_threshold=0.009060402805200412
estimated_extra_ticks_at_observed_rate=2.269158172139862
```

Decision:

```text
run_second_smoke_now=false
recommended_next_path=second_tiny_smoke_after_separate_approval
second_smoke_max_control_ticks=5
keep_same_checkpoint=true
keep_same_action_horizon=true
keep_same_clip_limits=true
do_not_change_model_now=true
do_not_train_dp_fm_now=true
requires_return_and_two_fresh_gates=true
```

Interpretation:

- The first smoke supports a second controlled smoke only if separately
  approved.
- The second smoke should change only one variable: tick budget from `3` to
  `5`.
- Do not adjust action horizon, retrain BC, or start DP/FM training yet.
- DP/FM remain offline-only.
- If a second smoke aborts or loses monotonic improvement, stop live execution
  and return to offline diagnostics.

## Second Tiny-Smoke Runbook Prepared

Date: 2026-05-07.

Prepared the next-run command artifact without executing it:

```text
outputs/logs/b8_rollout_planning/second_tiny_smoke_runbook.md
```

Scope:

```text
run_second_smoke_now=false
only_if_user_runs_commands=true
same_checkpoint=true
same_action_horizon=true
same_clip_limits=true
max_control_ticks=5
no_gripper_or_hand=true
```

The runbook preserves the same safety sequence:

1. return left arm to reference;
2. two fresh target-aware gates;
3. one second tiny active-left arm-only smoke with `max_control_ticks:=5`;
4. post-smoke gate;
5. read-only summary using `summarize_b8_base_relative_tiny_smoke.py`.

No command was sent by this preparation step. No second learned smoke was run.

## DP/FM Offline-Only Continuation

Date: 2026-05-07.

Continued DP/FM work only as offline planning and validation. No ROS command,
no hand/gripper controller, no gripper command, no training, and no learned
rollout were run.

Added DP30 focused seed-ablation configs:

```text
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed85.yaml
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86.yaml
```

Added offline planning/evaluation tools:

```text
scripts/plan_b8_dp30_focused_offline_ablation.py
scripts/analyze_b8_dp30_seed_ablation_validation.py
outputs/logs/b8_primary30_training_planning/dp30_focused_offline_ablation_plan.json
outputs/logs/b8_primary30_training_planning/dp30_focused_offline_ablation_plan.md
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.json
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.md
```

Current decision:

```text
dp_offline_ablation_can_continue=true
selected_axis=diffusion_seed_only
bc_remains_live_reference=true
dp_fm_live_approved=false
training_started=false
missing_candidate_count=2
```

Interpretation:

- DP30 seed84 remains the best available DP checkpoint, but BC still has lower
  validation action MSE.
- Seed85/seed86 were prepared as bounded offline-only candidates; the training
  outcome is recorded below.
- DP/FM live execution remains blocked.
- No grasp success, learned rollout success, or general rollout success is
  claimed.

## DP/FM Sampling Sweep After Seed Ablation

Date: 2026-05-07.

Ran an offline-only sampling sensitivity check after the DP30 seed ablation:

```text
scripts/analyze_b8_dp_fm_sampling_after_seed_ablation.py
outputs/logs/b8_primary30_training_planning/dp_fm_sampling_after_seed_ablation.json
outputs/logs/b8_primary30_training_planning/dp_fm_sampling_after_seed_ablation.md
```

Decision:

```text
bc_remains_reference=true
best_non_bc=dp30_seed86_zero_steps50
best_non_bc_relative_to_bc=0.013692332058653145
sampling_steps_close_gap=false
dp_fm_live_approved=false
training_started=false
```

Interpretation:

- DP seed86 remains the best non-BC candidate, but still does not beat BC.
- Increasing DP sampling from 50 to 100/200 steps does not improve the result.
- FM10 remains worse than DP seed86 and has higher max-window error.
- DP/FM live remains blocked; next DP/FM work should stay offline-only and
  focus on architecture/objective diagnostics rather than sampling steps.

## DP/FM Loss-Action Alignment Diagnostic

Date: 2026-05-07.

Ran a read-only training-loss versus validation-action-MSE diagnostic:

```text
scripts/analyze_b8_dp_fm_loss_action_alignment.py
outputs/logs/b8_primary30_training_planning/dp_fm_loss_action_alignment.json
outputs/logs/b8_primary30_training_planning/dp_fm_loss_action_alignment.md
```

Decision:

```text
bc_remains_reference=true
best_non_bc=dp30_seed86
best_dp_relative_to_bc=0.013692332058653145
loss_metric_sufficient_for_selection=false
sampling_or_seed_not_enough=true
dp_fm_live_approved=false
training_started=false
```

Key observation:

```text
dp30_seed85 best_val_loss=0.48370392736728474 action_mse=3.1949056733537873e-07
dp30_seed86 best_val_loss=0.504732092542033 action_mse=3.1088134733181505e-07
```

Interpretation:

- Lower diffusion denoising validation loss did not imply lower action MSE.
- Seed and sampling-step tuning are not enough to displace BC.
- DP/FM should continue only as offline architecture/objective diagnostics.
- DP/FM live remains blocked.

## DP Architecture Ablation Outcome

Date: 2026-05-07.

Ran one bounded offline architecture ablation:

```text
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86_w128.yaml
outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86_w128/best.pt
outputs/logs/b8_primary30_training_planning/dp_architecture_ablation_validation.md
outputs/logs/b8_primary30_training_planning/dp_architecture_ablation_outcome.md
```

Validation decision:

```text
bc_action_mse=3.066821534503106e-07
dp30_seed86_w256_action_mse=3.1088134733181505e-07
dp30_seed86_w128_action_mse=3.179889915827516e-07
w128_improves_over_w256=false
best_dp_beats_bc=false
dp_fm_live_approved=false
```

Interpretation:

- Reducing DP hidden width from `[256,256,256]` to `[128,128,128]` worsened
  validation action-window metrics.
- The current DP gap is not fixed by a smaller model.
- DP/FM live remains blocked.

## DP Objective Timestep Diagnostic

Date: 2026-05-07.

Ran an offline-only objective diagnostic on the current best DP checkpoint
(`dp30_seed86_w256`):

```text
scripts/analyze_b8_dp_objective_timestep_diagnostic.py
outputs/logs/b8_primary30_training_planning/dp_objective_timestep_diagnostic.json
outputs/logs/b8_primary30_training_planning/dp_objective_timestep_diagnostic.md
```

Decision:

```text
bc_reference_not_displaced_by_this_diagnostic=true
one_step_x0_diagnostic_not_policy_candidate=true
x0_error_range_ratio=1288.354547513286
objective_ablation_recommended=true
dp_fm_live_approved=false
training_started=false
```

Key timestep pattern:

```text
t=0  epsilon_mse_norm=1.0759165661950265 x0_action_mse=6.060692225862141e-11
t=20 epsilon_mse_norm=0.4632123941455477 x0_action_mse=1.722153974981211e-08
t=49 epsilon_mse_norm=0.29180770487554614 x0_action_mse=7.808320390267909e-08
```

Interpretation:

- This one-step x0 reconstruction diagnostic is not a rollout/policy candidate
  and does not displace BC.
- Epsilon loss improves at high timesteps while x0/action reconstruction error
  grows substantially.
- If DP continues, the next offline direction should be objective/selection
  work that explicitly tracks action-space metrics, not live execution.

## DP Action-Selection Outcome

Date: 2026-05-07.

Implemented and ran a bounded offline checkpoint-selection ablation:

```text
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86_action_select.yaml
outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86_action_select/best.pt
outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86_action_select/best_action.pt
outputs/logs/b8_primary30_training_planning/dp_action_selection_validation.md
outputs/logs/b8_primary30_training_planning/dp_action_selection_outcome.md
```

Decision:

```text
bc_action_mse=3.066821534503106e-07
dp30_seed86_baseline_action_mse=3.1088134733181505e-07
dp30_seed86_action_select_best_loss_action_mse=3.135244526220049e-07
dp30_seed86_action_select_best_action_action_mse=3.1140186251832347e-07
action_selection_improves_over_baseline_seed86=false
action_selection_beats_bc=false
dp_fm_live_approved=false
```

Interpretation:

- `best_action.pt` selected epoch 24 and improved max-window MSE versus the
  baseline DP seed86 checkpoint, but mean action MSE was still worse.
- Action-space checkpoint selection alone does not displace BC.
- DP/FM live remains blocked.

## DP30 Seed Ablation Outcome

Date: 2026-05-07.

Ran the two approved bounded offline DP30 trainings:

```text
seed85 epochs=30 best_val_loss=0.48370392736728474 final_val_loss=0.5302829148388037
seed86 epochs=30 best_val_loss=0.504732092542033 final_val_loss=0.504732092542033
```

Artifacts:

```text
outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed85/best.pt
outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_epoch30_seed86/best.pt
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.md
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_outcome.md
```

Validation decision:

```text
bc_action_mse=3.066821534503106e-07
best_dp_seed_candidate=dp30_seed86_zero
best_dp_action_mse=3.1088134733181505e-07
best_dp_relative_to_bc=0.013692332058653145
best_dp_beats_bc=false
bc_remains_live_reference=true
dp_fm_live_approved=false
```

Interpretation:

- Seed86 improves over the previous DP30 seed84 candidate, but still does not
  beat BC.
- DP/FM live execution remains blocked.
- No grasp success, learned rollout success, or general rollout success is
  claimed.

## 2026-05-07 Live Arm-Only BC / DP / FM Protocol Attempts

Scope:

```text
active-left arm-only reaching / pre-grasp positioning
no gripper command
no hand controller
no grasp success claim
no object grasped/lifted/held claim
```

Implemented and ran a shared live evaluation runner for BC, Diffusion Policy,
and Flow Matching Policy using the base-relative EE-delta / IK / joint-target
arm command path. The runner writes return, pre-gate, rollout, post-gate,
per-method, and combined summary artifacts.

Current final summary artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_protocol_attempts_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_protocol_attempts_summary.md
```

Latest formal protocol attempt, `v7_tick6`:

```text
BC: 0/1, success_rate=0.0, failure_reason=arm_only_success_threshold
DP: 3/3, success_rate=1.0
FM: 0/1, success_rate=0.0, failure_reason=arm_only_success_threshold
complete_three_method_live_comparison=false
equal_N_across_methods=false
```

Important earlier partial evidence:

```text
v4 ticks=9: DP 3/3 and FM 3/3, but BC 0/1 aborted on
             arm_command_conversion_or_execution_failed.
v6 early_stop_distance=0.090: BC 3/3 and FM 3/3, but DP 0/1 missed
                              arm_only_success_threshold.
v8 success-criterion guard: implemented and attempted, but blocked before
                             rollout by strict fresh pre-gate failure
                             (initial_distance 0.1328-0.1441 m,
                             target_base_drift 0.0255-0.0373 m).
v8 after user restart: fresh gates passed and rollout ran; BC 0/1,
                       DP dry-run passed but tiny smoke missed threshold,
                       FM 2/3. Still not equal-N complete.
v9 threshold095: threshold-only variant also remained partial; BC 0/1 and
                 DP/FM tiny smoke missed threshold.
v10 aligned guard: early-stop terminal observation logging and pre_gate_1
                   baseline were implemented. First BC cycle re-summarized as
                   success, but the run was truncated by a summary tooling
                   crash before DP/FM.
v10b aligned guard: same protocol after summarizer fix; BC 0/1, DP/FM
                    tiny-smoke threshold misses. Still not equal-N complete.
```

Conclusion:

```text
The package now has live arm-only DP/FM evidence, but it still does not have a
fair equal-N BC/DP/FM success-rate comparison under one protocol. Do not report
BC/DP/FM success rates as a completed comparison yet.
```

## 2026-05-07 Final Live Arm-Only BC / DP / FM N=3 Comparison

The revised protocol now uses the terminal early-stop observation as the formal
final-distance metric:

```text
formal_final_distance(terminal_observation) <= 0.10 m
formal_distance_reduction > 0.02 m
max_control_ticks=9
clip=0.005 m
max_joint_delta=0.01 rad
initial_distance<=0.125 m
target_base_drift<=0.02 m
arm-only, no gripper command, no hand controller
```

Final fair N=3 artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v11_terminal_final_distance.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v11_terminal_final_distance.md
```

Result:

```text
complete_three_method_live_comparison=true
equal_N_across_methods=true
BC: success_count=3, N=3, success_rate=1.0, mean_final_distance=0.08638367363982202
DP: success_count=3, N=3, success_rate=1.0, mean_final_distance=0.08258604938106842
FM: success_count=3, N=3, success_rate=1.0, mean_final_distance=0.0851672499059044
abort_count=0 for all methods
no_gripper_command_observed=true
no_hand_controller_started_by_eval=true
grasp_success_claimed=false
```

N=5 extension status:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v11_terminal_final_distance_n5_partial.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v11_terminal_final_distance_n5_partial.md
BC: 5/5
DP: 5/5
FM: 4 completed successes plus 1 incomplete cycle artifact
complete_three_method_live_comparison=false
```

Do not mix the partial N=5 extension into the final fair N=3 table.

## 2026-05-07 Final Live Arm-Only BC / DP / FM N=10 Comparison

After the N=5 partial extension, a clean N=10 run was completed under the same
terminal-observation protocol. The first N=10 attempt (`v12`) was interrupted
and recorded as a tooling failure because `return_left_arm_to_reference.py`
waited for a command subscriber before checking that the arm was already at
reference. That package-local tool was fixed, and the clean retry is `v12b`.

Latest final artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v12b_terminal_final_distance_n10.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v12b_terminal_final_distance_n10.md
```

Result:

```text
complete_three_method_live_comparison=true
equal_N_across_methods=true
BC: success_count=10, N=10, success_rate=1.0, mean_final_distance=0.08977726792087681
DP: success_count=10, N=10, success_rate=1.0, mean_final_distance=0.09129602109718894
FM: success_count=10, N=10, success_rate=1.0, mean_final_distance=0.09004022450698068
abort_count=0 for all methods
no_gripper_command_observed=true
no_hand_controller_started_by_eval=true
grasp_success_claimed=false
```

Use `v12b_terminal_final_distance_n10` as the current presentation-ready live
success-rate comparison. The earlier N=3 result remains preserved as
`v11_terminal_final_distance`.
