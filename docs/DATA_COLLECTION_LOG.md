# Data Collection Log

## 2026-05-07 Formal Live Eval Attempt: No New Data Collected

Scope:

```text
BC / DP / FM same-protocol arm-only reaching / pre-grasp live evaluation attempt
```

No new `.npz` dataset episodes were collected. The live attempt stopped before
policy rollout because BC cycle 0 failed the strict fresh target-aware pre-gate
after return-to-reference and two wait/retries.

Result:

```text
return_to_reference reached=true
pre_gate attempts=3
pre_gate passes=0
best retry target_base_drift=0.010550711129789662
best retry relative_base_drift=0.007371669176824283
policy rollout commands sent=false
gripper commands sent=false
hand controller started=false
```

Artifacts are under:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
```

This entry is not a dataset collection, not grasping, and not a completed
live success-rate comparison.

Follow-up target-gate restart also collected no data:

```text
target gate probe restarted=true
target present=true
strict pre-gate after restart failed
target_base_drift=0.006711007793366516
relative_base_drift=0.006271075196806217
policy rollout commands sent=false
gripper commands sent=false
```

Additional artifact root:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol_after_target_restart/
```

Aggressive protocol-v4 live evaluation generated rollout/evaluation logs but
no new `.npz` dataset episodes:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol_v4/
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
```

These are live evaluation artifacts, not data collection episodes. They remain
arm-only reaching/pre-grasp artifacts with gripper disabled.

No trajectories have been collected in stage 0.

Stage 0 only created the project package and documentation scaffold.

Future entries should record:

- date/time
- launch file
- world
- target model
- active arm
- topic map used
- controller/expert type
- episode count
- rate and duration
- output path
- validation result
- failure reason if any

## 2026-05-05 B8' Small Debug Batch

Record label:

```text
B8' small debug batch：10–15 episode real non-fallback arm-only reaching/pre-grasp debug collection，不训练、不处理 gripper。
```

Scope:

- Collected a short 10-episode real non-fallback arm-only reaching/pre-grasp
  debug batch.
- This was not training, not learned policy rollout, and not grasping.
- Gripper remained disabled; no hand controller was started and no gripper
  command was sent.

Launch/runtime:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch allow_trajectory_execution:=false
rexrov_single_oberon7_fm_dp load_left_controllers.launch start:=true load_hand:=false
rexrov_single_oberon7_fm_dp world_base_tf_bridge.launch
rexrov_single_oberon7_fm_dp collect_episode.launch
```

Important collection settings:

```text
episode_count: 10
rate_hz: 3.0
max_duration_sec: 7.2
allow_nominal_state_fallback: false
prefer_model_states_base_pose: false
base_state_source required: odom
target_state_source: gazebo_model_states
task_type: arm_only_reaching
success_metric: reaching_success
gripper_enabled: false
is_grasp_dataset: false
```

Output:

```text
data/raw/b8_reaching_debug_10/
```

Diagnostic outputs:

```text
outputs/logs/b8_reaching_debug_10/repeatability_summary.json
outputs/logs/b8_reaching_debug_10/repeatability_summary.md
outputs/logs/b8_reaching_debug_10_quality/
outputs/logs/b8_reaching_debug_10_direction/
outputs/logs/b8_reaching_debug_10_command_motion/
```

Validation and metadata:

```text
validator_pass_count: 10/10
all_required_metadata_ok: true
all_success_metadata_consistent: true
allow_nominal_state_fallback: false for all episodes
base_state_source: odom for all episodes
joint_state_source: joint_states for all episodes
target_state_source: gazebo_model_states for all episodes
gripper_enabled: false for all episodes
is_grasp_dataset: false for all episodes
success_source: recorded_final_distance for all episodes
recorded_success_distance_threshold_m: 0.1 for all episodes
```

Quality summary:

```text
episodes_total: 10
success_count: 7
reaching_success_rate: 0.7
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

Per-episode distances:

```text
initial_distance:
  [0.1077032901391015,
   0.10770363307558108,
   0.10946906431308212,
   0.10939656740011629,
   0.10947634414934099,
   0.10770329737098815,
   0.10944617528536583,
   0.10948271784930183,
   0.10907808958307377,
   0.10727472958874361]
min_distance:
  [0.04737587025733589,
   0.04851354464686713,
   0.056242964248424114,
   0.06191583067914912,
   0.06898559297244955,
   0.0823199994929284,
   0.09418571864374334,
   0.10761105267418075,
   0.10802835002420302,
   0.10727472958874361]
final_distance:
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
distance_reduction:
  [0.049993997313688886,
   0.05456462274151942,
   0.053226100064658007,
   0.0465446084590482,
   0.04049075117689144,
   0.02538329787805975,
   0.014931374134645667,
   0.00030680039887728827,
   -0.010777986338643977,
   -0.016798119727515354]
```

Failure reasons:

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

Decision:

```text
The batch is valid non-fallback arm-only debug data, but it does not pass the
small debug-batch quality gate because success_count / N = 0.7 < 0.8 and the
last three episodes failed consecutively. Do not train. Do not run learned
rollout. Do not expand to 20/50/100 episodes. Inspect and tune scripted
reaching behavior first.
```

### Offline Failure Analysis For `b8_reaching_debug_10`

Record label:

```text
B8' debug batch failure analysis：分析 b8_reaching_debug_10 中 0007–0009 连续失败，不训练、不扩采、不处理 gripper。
```

Scope:

- Offline analysis only over the existing 10 NPZ files.
- No new trajectories were collected.
- No ROS/Gazebo runtime, training, learned rollout, hand controller, or gripper
  command was used.

Read-only analyzer:

```text
scripts/analyze_b8_debug_batch_failure.py
```

Output:

```text
outputs/logs/b8_reaching_debug_10_failure_analysis/
```

Generated artifacts:

```text
failure_analysis_summary.json
failure_analysis_summary.md
success_vs_failure_table.csv
success_vs_failure_table.md
initial_condition_drift.json
per_episode_distance_curves.png
command_motion_success_vs_failure.png
joint_initial_drift.png
base_target_drift.png
```

Success-vs-failure summary:

```text
success episodes: 0000-0006
failure episodes: 0007-0009
initial_distance success/failure mean: 0.108700 / 0.108612
final_distance success/failure mean: 0.067966 / 0.117702
distance_reduction success/failure mean: 0.040734 / -0.009090
action_relative_cosine success/failure mean: 0.897726 / 0.943494
best_action_to_eef_cosine success/failure mean: 0.823278 / -0.071778
best_realized_gain_along_action success/failure mean: 0.209131 / -0.021860
joint_initial_drift_from_ep0 success/failure mean: 0.304920 / 0.806195
target_base_max_step success/failure mean: 0.006151 / 0.001934
```

Conclusion:

```text
The 10-episode batch remains valid non-fallback arm-only debug data, but
0007-0009 failed because the command-to-motion response degraded after
cross-episode configuration drift. The scripted action direction remained
target-aligned, and target/base sync did not show a large-jump failure.
```

Collection decision:

```text
Do not collect additional B8' episodes until the reset/settle and
command-to-motion degradation are addressed. Do not train from this batch.
```

## 2026-05-05 B8' One Gated Arm-Only Verification Episode

Record label:

```text
B8' one gated arm-only verification：exactly one short real non-fallback
arm-only reaching/pre-grasp verification episode，不扩采、不训练、不处理 gripper。
```

Scope:

- Collected exactly one short arm-only verification episode after target-aware
  initial-state gates passed.
- This was not a dataset expansion, not learned rollout, not training, and not
  grasping.
- Gripper remained disabled; no hand controller was started and no gripper
  command was sent.

Runtime:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
b5d_move_group_with_context.launch allow_trajectory_execution:=false
load_left_controllers.launch start:=true load_hand:=false
world_base_tf_bridge.launch
b8_target_gate_probe.launch
collect_episode.launch
```

Important collection settings:

```text
episode_count: 1
target_model_name: cylinder_target_gate_probe
spawn_target: false
enable_base_relative_target: false
execute_arm: true
enable_gripper_command: false
allow_nominal_state_fallback: false
prefer_model_states_base_pose: false
rate_hz: 3.0
max_duration_sec: 7.2
task_type: arm_only_reaching
success_metric: reaching_success
gripper_enabled: false
is_grasp_dataset: false
```

Output:

```text
data/raw/b8_gated_arm_verify_1/b8_gated_arm_verify_1_0000.npz
```

Diagnostics:

```text
outputs/logs/b8_initial_state_gate/gated_arm_verify_pre_gate.json
outputs/logs/b8_initial_state_gate/gated_arm_verify_post_gate.json
outputs/logs/b8_gated_arm_verify_1_quality/
outputs/logs/b8_gated_arm_verify_1_direction/
outputs/logs/b8_gated_arm_verify_1_command_motion/
```

## 2026-05-05 B8' Return-To-Reference Reset/Settle Live Check

Record label:

```text
B8' return-to-reference reset/settle live check：bounded active-left return
command followed by target-aware gate，不采新 episode、不训练、不处理 gripper。
```

Scope:

- This was a reset/settle data-quality check, not episode collection and not
  dataset expansion.
- The tool sent bounded active-left joint trajectory commands only.
- No hand controller was started and no gripper command was sent.

Result:

```text
return_left_arm_to_reference.py reached=true
commands_sent=8
final_joint_l2_error=0.0010774700888416262
final_joint_max_abs_error=0.0010726177090809585
gripper_commands_sent=false

post_return_target_gate passed=true
initial_distance=0.11073716282178127
joint_l2_drift=0.0010745595666474277
joint_max_abs_drift=0.0010454018959631384
relative_base_drift=0.0032940252409286845
```

Collection decision:

```text
The reset/settle mechanism is single-cycle smoke-level resolved. Do not expand
collection yet. The next minimum check is exactly one short gated arm-only
episode after return-to-reference, followed by validator and quality diagnostics.
```

## 2026-05-05 B8' Return-Gated Episode Attempt With Wrong Overrides

Record label:

```text
B8' return-gated arm-only verification attempt：saved one non-fallback episode,
but launch overrides were wrong; do not treat as passing return-gated evidence.
```

Saved file:

```text
/home/benny/.ros/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_return_gated_arm_verify_1/b8_return_gated_arm_verify_1_0000.npz
```

Validation/data status:

```text
validator: PASS
success: false
recorded_success_distance_m: 0.10891000445099207
allow_nominal_state_fallback: false
gripper_enabled: false
is_grasp_dataset: false
```

Reason this is not a valid return-gated target-directed check:

```text
target_directed_reaching=false
state_sequence included CLOSE_GRIPPER,LIFT_OR_HOLD
output_dir was relative and resolved under /home/benny/.ros
runtime expert crashed with unsupported operand type(s) for *: 'NoneType' and 'NoneType'
```

Collection decision:

```text
Do not expand collection and do not train. Rerun only after return-to-reference
and target-aware gate, with explicit target-directed arm-only launch overrides
and an absolute workspace output_dir.
```

## 2026-05-05 B8' Corrected Return-Gated Arm-Only Verification

Record label:

```text
B8' corrected return-gated arm-only verification：one return->gate->episode
cycle, real non-fallback arm-only reaching/pre-grasp，不扩采、不训练、不处理 gripper。
```

Output:

```text
data/raw/b8_return_gated_arm_verify_2/b8_return_gated_arm_verify_2_0000.npz
```

Pre-episode reset/gate:

```text
return_to_reference_live_2 reached=true
commands_sent=1
final_joint_l2_error=8.382996789634279e-05
pre_corrected_return_episode_gate passed=true
initial_distance=0.11332110045439249
relative_base_drift=0.00710979212566845
gripper_commands_sent=false
```

Episode validation:

```text
validator=PASS
T=22
success=True
success_source=recorded_final_distance
recorded_success_distance_m=0.08215466060136162
allow_nominal_state_fallback=false
base_state_source=odom
joint_state_source=joint_states
target_state_source=gazebo_model_states
gripper_enabled=false
is_grasp_dataset=false
task_type=arm_only_reaching
success_metric=reaching_success
```

Quality:

```text
initial_distance=0.10769470167832411
min_distance=0.08071406189845907
final_distance=0.08215466060136162
distance_reduction=0.02554004107696249
mean_best_action_to_eef_cosine=0.2649969261995647
mean_best_lag_steps=3.0
mean_best_realized_gain_along_action=0.08132703920221891
```

Collection decision:

```text
This validates one corrected return-gated arm-only cycle, but command-motion
quality is still weak and post-episode gate fails as expected from the reached
configuration. Do not expand or train. Require return-to-reference + gate before
any next episode.
```

Follow-up reset/gate after the corrected success:

```text
return_to_reference_live_3 reached=true
commands_sent=5
final_joint_l2_error=0.00010091317246476995
gripper_commands_sent=false

post_success_return_gate passed=false
initial_distance=0.12368795041111422
relative_base_drift=0.01695805312367644
target_base_drift=0.01691229565682799
joint_l2_drift=0.0006517102217792586
eef_base_drift=4.920892227205025e-05
```

Data-quality decision:

```text
No new episode should be collected from this state. Arm reset passed, but
target/base initial geometry is outside the target-aware gate. Check target/base
stability or reinitialize the target probe before the next arm-only episode.
```

## 2026-05-05 B8' Restarted Runtime Target Gate Settle Check

Record label:

```text
B8' target/base settle check after runtime restart：three read-only
target-aware gates, no episode collection, no training, no gripper.
```

Result:

```text
gate_0 passed=false
relative_base_drift=0.02327702221543785
target_base_drift=0.022187036192277323
initial_distance=0.11029615817327146

gate_1 passed=false
relative_base_drift=0.0232763337054756
target_base_drift=0.02218640052215951
initial_distance=0.11029953375977956

gate_2 passed=true
relative_base_drift=5.5529932828080466e-06
target_base_drift=0.0012237377600882425
initial_distance=0.10770297148110519
```

Data-quality decision:

```text
This was not collection. It shows target/base geometry can recover after
runtime restart, but startup/settle transients can make early gates fail. Do
not start an arm episode until a fresh target-aware gate passes; prefer two
consecutive passing gates before another episode.
```

Validation and metadata:

```text
validator: PASS
T: 22
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
```

Quality:

```text
initial_distance: 0.10625611763364251
min_distance: 0.045301559855776316
final_distance: 0.045301559855776316
distance_reduction: 0.060954557777866195
max_active_left_joint_delta: 0.0771154374980636
```

Direction and command-motion:

```text
mean_eef_motion_cosine_with_target: 0.8411411057732849
mean_eef_positive_target_direction_ratio: 1.0
mean_best_action_to_eef_cosine: 0.8718392906129798
mean_best_lag_steps: 0.0
mean_best_realized_gain_along_action: 0.24521231853273232
```

Post-gate result:

```text
passed: false
relative_base_drift_ok: false
relative_base_drift: 0.07180542804879099
initial_distance: 0.04013113557371512
```

Decision:

```text
The single gated arm-only verification passed, but multi-episode repeatability
is still blocked because the system remains in the reached configuration after
the command. Do not expand collection or train until reset/settle or
per-episode reinitialization is defined.
```

## 2026-05-04 Route Alignment: B8' Arm-Only Data Requirements

This entry records documentation alignment only. No Gazebo run, rollout, or
training was performed for this entry.

Current first-version data route:

```text
RexROV + single-active-left Oberon7 arm-only reaching / pre-grasp positioning
```

B5d' debug-smoke status:

- minimal resolved for arm-only reaching/pre-grasp;
- gripper disabled;
- repeated small bounded left-arm commands published through
  `/oberon7/arm_position_l/command`;
- non-fallback live-state `.npz` smoke episode validated.

B8' next collection target:

```text
episodes: 5 short smoke episodes first
fallback: disabled
task_type: arm_only_reaching or pregrasp_positioning
success_metric: reaching_success or pregrasp_success
gripper_enabled: false
is_grasp_dataset: false
```

B8' must record these quality metrics for every episode:

```text
initial_distance
min_distance
final_distance
distance_reduction
active-left joint motion magnitude
validator result
failure_reason, if any
```

Do not treat Stage 6 fallback data as real demonstration data. Do not record or
report `grasp_success_rate` for B8'.

## 2026-05-04 B8' Reaching Smoke Quality Review

Scope:

- Analyzed only the existing 5-episode B8' non-fallback reaching smoke dataset.
- No new episode was collected.
- No Gazebo run, training, rollout, gripper command, or hand controller startup
  was performed.

Dataset:

```text
data/raw/b8_reaching_smoke/b8_reaching_smoke_0000.npz
data/raw/b8_reaching_smoke/b8_reaching_smoke_0001.npz
data/raw/b8_reaching_smoke/b8_reaching_smoke_0002.npz
data/raw/b8_reaching_smoke/b8_reaching_smoke_0003.npz
data/raw/b8_reaching_smoke/b8_reaching_smoke_0004.npz
```

Quality artifacts:

```text
outputs/logs/b8_reaching_smoke_quality/per_episode_quality.json
outputs/logs/b8_reaching_smoke_quality/per_episode_quality.md
outputs/logs/b8_reaching_smoke_quality/distance_curves.png
outputs/logs/b8_reaching_smoke_quality/action_magnitude_summary.json
outputs/logs/b8_reaching_smoke_quality/joint_motion_summary.json
```

Validation and metadata:

```text
validator: PASS for 5/5
T per episode: 6
allow_nominal_state_fallback: false for 5/5
base_state_source: odom for 5/5
joint_state_source: joint_states for 5/5
target_state_source: gazebo_model_states for 5/5
task_type: arm_only_reaching for 5/5
success_metric: reaching_success for 5/5
gripper_enabled: false for 5/5
is_grasp_dataset: false for 5/5
```

Quality result:

```text
episodes_with_positive_distance_reduction: 3/5
episodes_below_0.10: 0/5
min_distance_overall: 0.118852 m
mean_initial_distance: 0.133968 m
mean_final_distance: 0.131069 m
mean_distance_reduction: 0.002899 m
max_active_left_joint_delta: 0.008000 rad
```

Decision:

```text
The B8' collection chain is usable, but the reaching quality is not strong
enough to justify 20-episode expansion or BC/DP/FM training.
```

Next data-collection action should wait until the scripted reaching expert is
tuned and another short 5-episode smoke is explicitly requested.

## 2026-05-04 B8' Tuned Smoke Preparation

Scope:

- Prepared the next B8' tuned smoke collection path.
- No new data was collected in this entry.
- No Gazebo run, rollout, training, gripper command, or hand controller startup
  was performed.

Prepared one-episode wrapper:

```text
launch/b8_reaching_tuned_episode.launch
```

Planned output path for the next smoke:

```text
data/raw/b8_reaching_smoke_tuned_v1
outputs/logs/b8_reaching_smoke_tuned_v1
```

Key tuned settings:

```text
target_directed_action_frame: base_link
arm_action_frame: base_link
rate_hz: 3.0
max_duration_sec: 3.3
max_linear_step: 0.010
max_joint_delta: 0.015
time_from_start_sec: 1.0
execute_arm_states: MOVE_TO_PREGRASP,MOVE_TO_GRASP
enable_gripper_command: false
allow_nominal_state_fallback: false
```

Next runtime action:

```text
Collect and validate only b8_reaching_smoke_tuned_v1_0000 first. Continue to
0001-0004 only if the first tuned episode remains bounded and non-fallback.
```

## 2026-05-04 B8' Tuned v2 Data Quality Diagnostics

Scope:

- Analyzed existing tuned v2 non-fallback arm-only reaching episodes only.
- No new episode was collected for this entry.
- No Gazebo run, rollout, training, gripper command, or hand controller startup
  was performed.

Dataset:

```text
data/raw/b8_reaching_smoke_tuned_v2/b8_reaching_smoke_tuned_v2_0000.npz
data/raw/b8_reaching_smoke_tuned_v2/b8_reaching_smoke_tuned_v2_0001.npz
```

Quality and diagnostic artifacts:

```text
outputs/logs/b8_reaching_smoke_tuned_v2_quality/per_episode_quality.json
outputs/logs/b8_reaching_smoke_tuned_v2_quality/per_episode_quality.md
outputs/logs/b8_reaching_smoke_tuned_v2_direction/direction_diagnostic.json
outputs/logs/b8_reaching_smoke_tuned_v2_direction/direction_diagnostic.md
outputs/logs/b8_reaching_smoke_tuned_v2_command_motion/command_motion_diagnostic.json
outputs/logs/b8_reaching_smoke_tuned_v2_command_motion/command_motion_diagnostic.md
```

Validation and metadata:

```text
validator: PASS for 2/2
T per episode: 16
allow_nominal_state_fallback: false
target_state_source: gazebo_model_states
task_type: arm_only_reaching
success_metric: reaching_success
gripper_enabled: false
is_grasp_dataset: false
```

Quality result:

```text
episodes_below_threshold: 0/2
episodes_with_positive_distance_reduction: 1/2
min_distance_overall: 0.12082938778758692 m
mean_distance_reduction: 0.0018827220443207587 m
max_active_left_joint_delta: 0.0560245462242559 rad
```

Direction / command-to-motion result:

```text
mean_eef_motion_cosine_with_target: -0.09207573656385626
mean_eef_positive_target_direction_ratio: 0.4666666666666667
mean_best_lag_steps: 0.0
mean_best_action_to_eef_cosine: 0.0921582493936101
mean_best_realized_gain_along_action: 0.02557494803831787
```

Decision:

```text
Tuned v2 data is valid smoke data, but reaching quality remains blocked.
Do not continue tuned v2 collection to 0002-0004.
Do not expand collection or train until the command-to-motion path and
target/base geometry are understood.
```

## 2026-05-04 B8' TF Bridge Frame-Fix Validation Episode

Scope:

- Collected exactly one short non-fallback arm-only frame-fix validation
  episode with `world_base_tf_bridge.launch` running.
- This was not a 5-episode collection expansion.
- No training, rollout, gripper command, or hand controller startup was
  performed.

Dataset:

```text
data/raw/b8_reaching_smoke_tf_bridge_check/b8_reaching_smoke_tf_bridge_check_0000.npz
```

Validation:

```text
validation: PASS
T: 16
success: False
unavailable_fields: ['raw_command']
allow_nominal_state_fallback: false
gripper_enabled: false
is_grasp_dataset: false
task_type: arm_only_reaching
success_metric: reaching_success
```

Quality artifacts:

```text
outputs/logs/b8_reaching_smoke_tf_bridge_check_quality/per_episode_quality.json
outputs/logs/b8_reaching_smoke_tf_bridge_check_quality/per_episode_quality.md
outputs/logs/b8_reaching_smoke_tf_bridge_check_command_motion/command_motion_diagnostic.json
outputs/logs/b8_reaching_smoke_tf_bridge_check_command_motion/command_motion_diagnostic.md
```

Quality result:

```text
episodes_below_threshold: 0/1
episodes_with_positive_distance_reduction: 1/1
initial_distance: 0.12896387383800806 m
min_distance_overall: 0.12272243911393374 m
final_distance: 0.12671316334997665 m
mean_distance_reduction: 0.00225071048803141 m
max_active_left_joint_delta: 0.04185326590208582 rad
```

Command-to-motion result:

```text
mean_best_action_to_eef_cosine: 0.38837550274847654
mean_best_realized_gain_along_action: 0.10417398838872995
mean_best_lag_steps: 0.0
```

Decision:

```text
TF bridge improves command-to-motion coupling, but reaching quality is still
not sufficient for 5-episode collection expansion or training.
```

Direction diagnostic:

```text
episodes_below_threshold: 0/1
mean_eef_motion_cosine_with_target: 0.008830359482655255
mean_eef_positive_target_direction_ratio: 0.4666666666666667
mean_action_to_eef_motion_cosine: 0.38837550274847654
target_base_net/max-step: 0.011852 / 0.089075
base_world_net/path: 1.079475 / 1.082072
```

Updated interpretation:

```text
The TF bridge improves command-to-motion coupling, but target/base geometry is
still not stable enough for useful reaching demonstrations. The target moves
in base frame much more per sample than the EEF, so reaching quality remains
blocked.
```

Follow-up per-sample geometry:

```text
max_target_step_base: 0.08907516876353049 m
max_eef_step_base:    0.006750324744116928 m
```

Data-collection decision:

```text
Do not continue this dataset to a 5-episode set.
Do not train BC / DP / FM.
Do not rollout.
Run exactly one new TF-bridge validation episode after increasing the
base-relative target updater to 30 Hz, then re-check quality/direction/
command-to-motion metrics.
```

## 2026-05-04 B8' TF Bridge Target30 Validation Episode

Scope:

- Collected exactly one short non-fallback arm-only validation episode with
  `world_base_tf_bridge.launch` running and `base_relative_target_rate_hz=30.0`.
- This was not a 5-episode collection expansion.
- No training, rollout, gripper command, or hand controller startup was
  performed.

Dataset:

```text
data/raw/b8_reaching_smoke_tf_bridge_target30_check/b8_reaching_smoke_tf_bridge_target30_check_0000.npz
```

Validation:

```text
validation: PASS
T: 16
success: False
unavailable_fields: ['raw_command']
```

Quality result:

```text
episodes_below_threshold: 0/1
episodes_with_positive_distance_reduction: 1/1
initial_distance: 0.12549968637530884 m
min_distance_overall: 0.12160315011478852 m
final_distance: 0.12413588250680598 m
mean_distance_reduction: 0.0013638038685028636 m
max_active_left_joint_delta: 0.04081576279364185 rad
```

Direction result:

```text
mean_action_to_eef_motion_cosine: 0.6983946289035002
mean_eef_motion_cosine_with_target: 0.4453145000526829
mean_eef_positive_target_direction_ratio: 0.8
```

Data-collection decision:

```text
Direction improved, but reaching quality remains below acceptance.
Do not expand to a 5-episode set yet.
Do not train BC / DP / FM.
Run only read-only command-to-motion and target_base max-step checks next.
```

Follow-up command-to-motion / target-step result:

```text
mean_best_action_to_eef_cosine: 0.956902308613389
mean_best_lag_steps: 2.0
mean_best_realized_gain_along_action: 0.3194339452607246
target_base_net/max-step: 0.034005 / 0.014167
```

Updated data-collection decision:

```text
Target updater jitter is smoke-level improved, but B8' reaching quality still
does not meet the 0.10 m threshold. Do not collect a larger dataset yet. The
next step is read-only inspection of the per-lag command-motion markdown table,
then a possible one-episode horizon/state-duration tuning check.
```

Per-lag command-motion table:

```text
lag 0: action/eef cos 0.698395, eef/target cos 0.445315, gain 0.226123
lag 1: action/eef cos 0.820193, eef/target cos 0.537372, gain 0.268557
lag 2: action/eef cos 0.956902, eef/target cos 0.654001, gain 0.319434
lag 3: action/eef cos 0.946611, eef/target cos 0.776835, gain 0.310540
```

Updated data-collection decision:

```text
The target30 single episode is valid smoke data, but it still misses the
0.10 m reaching threshold. Do not expand collection. A package-local tuned v3
single-episode check has been prepared with a longer horizon/state duration to
test the observed 2-3 sample response lag.
```

## 2026-05-04 B8' Tuned v3 One-Episode Validation

Scope:

- Collected exactly one short non-fallback arm-only validation episode with
  `world_base_tf_bridge.launch` running.
- Used the tuned v3 package-local wrapper with longer horizon/state durations.
- No training, rollout, gripper command, or hand controller startup was
  performed.

Dataset:

```text
data/raw/b8_reaching_smoke_tuned_v3_check/b8_reaching_smoke_tuned_v3_check_0000.npz
```

Validation:

```text
validation: PASS
T: 22
success: False
unavailable_fields: ['raw_command']
```

Quality result:

```text
episodes_below_threshold: 1/1
episodes_with_positive_distance_reduction: 1/1
initial_distance: 0.1264832193593639 m
min_distance_overall: 0.08480029669684241 m
final_distance: 0.12246726976236536 m
mean_distance_reduction: 0.004015949596998553 m
max_active_left_joint_delta: 0.06377453998389893 rad
```

Direction / command-to-motion result:

```text
mean_eef_motion_cosine_with_target: 0.5093671918914294
mean_eef_positive_target_direction_ratio: 0.8095238095238095
mean_best_action_to_eef_cosine: 0.6652890486895977
mean_best_lag_steps: 0.0
mean_best_realized_gain_along_action: 0.19879837117714555
```

Data-collection decision:

```text
This is the first B8' single-episode smoke to cross the 0.10 m threshold.
Treat it as smoke-level progress only. Do not expand collection or train until
read-only markdown inspection confirms whether the threshold crossing was
transient and whether target/base geometry stayed bounded.
```

Markdown inspection:

```text
distance initial/min/final/reduction:
  0.126483 / 0.084800 / 0.122467 / 0.004016
distance decreasing step ratio: 0.523810
joint max delta / step max delta: 0.063775 / 0.006013
target world/base motion: 0.374723 / 0.038119
target base net/max-step: 0.038119 / 0.055363
labels: target_moves_in_base_frame, base_world_drift_present
```

Updated data-collection decision:

```text
Do not expand collection yet. The one v3 episode crossed threshold but final
distance rebounded above threshold and target_base max-step remains a residual
risk. Next step is a read-only per-sample trace check.
```

Per-sample trace:

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

Data-collection decision:

```text
Do not collect repeatability episodes yet. The only below-threshold sample is
transient and is adjacent to target_base step spikes. Fix or bound target/base
geometry stability before any further B8' collection.
```

Target updater fix before next data check:

```text
base_relative_target.py now uses cached fresh /rexrov/pose_gt odom instead of
blocking on wait_for_message during each target update.
base_relative_target_max_base_pose_age_sec: 0.25
```

Next data-quality check:

```text
Collect exactly one tuned v3 cached-odom validation episode, then compare
target_base max-step and below-threshold persistence against
b8_reaching_smoke_tuned_v3_check_0000.
```

Cached-odom validation result:

```text
dataset:
  data/raw/b8_reaching_smoke_tuned_v3_cached_odom_check/b8_reaching_smoke_tuned_v3_cached_odom_check_0000.npz

validation: PASS
T: 22
success: False

episodes_below_threshold: 1/1
episodes_with_positive_distance_reduction: 0/1
initial_distance: 0.12630808035415297 m
min_distance_overall: 0.08611444139540192 m
final_distance: 0.14779493259862328 m
mean_distance_reduction: -0.021486852244470306 m
mean_best_lag_steps: 2.0
```

Data-collection decision:

```text
Do not collect repeatability episodes. Cached-odom still produced only
smoke-level threshold crossing and worse final distance. Run per-sample trace
before any further code/config changes.
```

Cached-odom per-sample trace:

```text
below_count: 1
below_indices: [10]
min_distance: 0.08611444139540188 m
final_distance: 0.14779493259862325 m
max_target_step: 0.050329083057232285 m
max_target_step_idx: 11
```

Data-collection decision:

```text
Do not collect repeatability episodes. The cached-odom episode still has a
single transient below-threshold sample and target_base step spikes. Next check
is read-only consistency between recomputed distance and stored
relative_target_to_eef.
```

## 2026-04-29 Stage 4 Smoke Test

Purpose:

- Verify the first state-based recorder can subscribe to runtime topics, save one `.npz` episode, and pass the validator.

Launch used:

```bash
roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=false
roslaunch rexrov_single_oberon7_fm_dp record_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw \
  episode_id:=stage4_smoke_runtime \
  rate_hz:=2.0 \
  max_duration_sec:=1.0 \
  require_target:=false
```

Output:

```text
/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage4_smoke_runtime.npz
/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage4_smoke_runtime.metadata.json
```

Recorded topics:

- `/rexrov/pose_gt`
- `/joint_states`
- `/gazebo/model_states`
- optional `/rexrov/thruster_manager/input`
- optional `/rexrov/thruster_manager/input_stamped`

Smoke-test result:

```text
validation: PASS
T: 2
success: False
unavailable_fields:
  - target_pose
  - eef_pose
  - relative_target_to_eef
  - action_ee_delta
  - raw_command
```

Observed shapes:

```text
action_ee_delta: [2, 7]
active_joint_positions: [2, 6]
active_joint_velocities: [2, 6]
base_pose: [2, 7]
base_velocity: [2, 6]
done: [2]
eef_pose: [2, 7]
gripper_state: [2, 4]
raw_command: [2, 6]
relative_target_to_eef: [2, 3]
success: scalar
target_pose: [2, 7]
timestamp: [2]
```

Known missing fields:

- No target object was spawned in the minimal launch, so `target_pose` is unavailable.
- No TF/MoveIt end-effector pose lookup is implemented in the recorder yet, so `eef_pose` and `relative_target_to_eef` are unavailable.
- No expert action converter exists yet, so `action_ee_delta` is unavailable.
- No base wrench command was published during the smoke test, so `raw_command` is unavailable.

Notes:

- `/joint_states` extraction had no missing active-left or gripper joints in the smoke test.
- `rosparam load` cannot marshal YAML `null`, so unresolved command topics are stored as empty strings in `config/topics.yaml` and serialized as `null` in episode metadata.
- Gazebo shutdown again emitted a nonfatal `boost::lock_error`/thruster allocator shutdown message, consistent with prior short-runtime checks.

## 2026-04-29 Stage 5 Scripted Expert Smoke Test

Purpose:

- Verify a first scripted expert can generate finite expert action labels while the recorder collects a valid state-based episode.

Launch used:

```bash
roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=false
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw \
  episode_id:=stage5_scripted_expert_smoke_v2 \
  rate_hz:=2.0 \
  max_duration_sec:=5.0 \
  spawn_target:=true
```

Output:

```text
/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage5_scripted_expert_smoke_v2.npz
/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage5_scripted_expert_smoke_v2.metadata.json
```

Expert:

```text
type: scripted
target: cylinder_target
target source: /gazebo/model_states
action topic: /rexrov_single_oberon7_fm_dp/expert/action_ee_delta
state topic: /rexrov_single_oberon7_fm_dp/expert/state
success topic: /rexrov_single_oberon7_fm_dp/expert/success
```

Validation result:

```text
validation: PASS
T: 10
success: False
unavailable_fields:
  - eef_pose
  - relative_target_to_eef
  - raw_command
```

Recorded field availability:

```text
action_ee_delta: finite
target_pose: finite
eef_pose: unavailable
relative_target_to_eef: unavailable
raw_command: unavailable
```

Example action labels:

```text
first action: [0.03, 0.0, 0.02, 0.0, 0.0, 0.0, 0.0]
last action:  [0.0, 0.0, 0.04, 0.0, 0.0, 0.0, 1.0]
```

Known limitations:

- This is an action-label expert; it does not yet execute left-arm motion in Gazebo.
- Success is false because `eef_pose` is still unavailable.
- No base wrench command was published during the smoke test, so `raw_command` remains unavailable.

## 2026-05-01 Stage 6 Batch Demonstration Dataset

Purpose:

- Build the first multi-episode `.npz` dataset for BC/DP/FM pipeline development.
- Exercise batch collection, per-episode validation, dataset summary, and train/val split generation.

Implemented collection utilities:

```text
config/batch_collection.yaml
scripts/batch_collect_episodes.py
scripts/summarize_dataset.py
```

Important runtime finding:

- In this Stage 6 session, the selected Gazebo launch exposed topics/services but did not reliably publish live `/joint_states`, `/rexrov/pose_gt`, or a spawned target model sample to the recorder.
- `gazebo_ros/spawn_model` and some `/gazebo/*` service calls could block during batch collection.
- To finish the Stage 6 data-pipeline acceptance target without modifying official packages, batch collection was run with explicit fallback metadata:
  - `base_state_source: nominal_base_state_fallback`
  - `joint_state_source: zero_joint_state_fallback`
  - `target_state_source: nominal_target_pose_fallback`
  - `allow_nominal_state_fallback: true`
- This dataset is therefore a scripted action-label / schema-debug dataset, not a real physical grasp dataset.

Smoke dataset:

```text
episodes: 5
path: /home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage6_smoke
summary: /home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/stage6_smoke/dataset_summary.json
```

Debug dataset:

```text
episodes_total: 20
episodes_valid: 20
episodes_invalid: 0
path: /home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage6_debug
summary_json: /home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/stage6_debug/dataset_summary.json
summary_md: /home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/stage6_debug/dataset_summary.md
split: /home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/stage6_debug/dataset_split_combined.json
```

Debug summary:

```text
success_count: 0
success_rate: 0.0
mean_T: 10.0
min_T: 10
max_T: 10
action_ee_delta: available in 20/20
target_pose: available in 20/20
eef_pose: unavailable in 20/20
relative_target_to_eef: unavailable in 20/20
raw_command: unavailable in 20/20
```

Per-dimension ranges from the 20-episode debug summary:

```text
action_ee_delta min: [0.0, 0.0, -0.03, 0.0, 0.0, 0.0, 0.0]
action_ee_delta max: [0.03, 0.0, 0.04, 0.0, 0.0, 0.0, 1.0]
target_pose min: [2.457960790905159, 1.8575032265668001, -40.04072541566198, 0.0, 0.0, 0.0, 1.0]
target_pose max: [2.7468570051909786, 2.141934729193811, -39.960782043229514, 0.0, 0.0, 0.0, 1.0]
active_joint_positions min/max: all 0.0 due zero_joint_state_fallback
active_joint_velocities min/max: all 0.0 due zero_joint_state_fallback
gripper_state min/max: all 0.0 due zero_joint_state_fallback
```

Combined split:

```text
train: 16
val: 4
test: 0
seed: 42
```

Known limitations:

- The 20-episode debug set is suitable for dataset loader, normalization, BC/DP/FM shape checks, and training-loop smoke tests.
- It is not suitable for evaluating real grasp success or learning real arm dynamics because the arm state is fallback zeros and the target is not physically spawned.
- The next runtime priority is to fix live `/joint_states` sampling, target spawn stability, and left-arm/gripper command topics before collecting a real demonstration dataset.

## 2026-05-04 B8' Tuned V3 Cached-Odom Data Quality

Dataset checked:

```text
data/raw/b8_reaching_smoke_tuned_v3_cached_odom_check/
```

Episode checked:

```text
b8_reaching_smoke_tuned_v3_cached_odom_check_0000.npz
```

Validation:

```text
validation: PASS
T: 22
success: False
unavailable_fields: ['raw_command']
```

Quality summary:

```text
episodes_total: 1
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 0
min_distance_overall: 0.08611444139540192
mean_initial_distance: 0.12630808035415297
mean_final_distance: 0.14779493259862328
mean_distance_reduction: -0.021486852244470306
```

Direction and command-motion summary:

```text
mean_eef_motion_cosine_with_target: 0.5192861743957111
mean_eef_positive_target_direction_ratio: 0.8095238095238095
mean_action_to_eef_motion_cosine: 0.6683840448271507
mean_best_action_to_eef_cosine: 0.7985718493152257
mean_best_lag_steps: 2.0
```

Read-only consistency check:

```text
max_abs_dist_diff between stored and recomputed distance: 5.27e-16
stored_min_idx: 10
recomputed_min_idx: 10
```

Data-quality interpretation:

- The episode is valid live non-fallback smoke data, but not yet repeatability
  collection data.
- The below-threshold sample is transient; final distance is worse than initial.
- Stored `relative_target_to_eef` is internally consistent, but this only
  confirms saved-field arithmetic.
- Because recorder base pose and target pose used different source topics, the
  next collection-quality check should record base and target from
  `/gazebo/model_states` in the B8' v3 diagnostic path.

Do not expand this dataset or train from it.

## 2026-05-05 B8' Timing05 Fresh-Restart Data Quality

Dataset checked:

```text
data/raw/b8_reaching_smoke_tuned_v3_timing05_check/
```

Episode checked:

```text
b8_reaching_smoke_tuned_v3_timing05_check_0000.npz
```

Runtime context:

```text
fresh restart: yes
max_linear_step: 0.010
max_joint_delta: 0.010
time_from_start_sec: 0.5
gripper_enabled: false
prefer_model_states_base_pose: true
```

Validation and quality:

```text
validation: PASS
T: 22
success: False
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 0
min_distance_overall: 0.09537016926721392
mean_initial_distance: 0.12756819181897866
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

Data-quality interpretation:

- This is valid non-fallback diagnostic smoke data.
- It is not acceptable for repeatability collection or training.
- The threshold crossing was transient and final distance worsened.
- Fresh restart did not resolve the blocker.
- Next action should be read-only per-sample diagnostics, not another
  collection run.

Per-sample follow-up:

```text
below_count: 2
below_indices: [9, 14]
min_distance: 0.09537016926721362
final_distance: 0.13770812387361822
max_target_step_base: 0.04418920181065058
max_eef_step_base: 0.017600391738394876
```

Both below-threshold samples coincide with target-base jumps:

```text
idx 9:  target_step_base=0.044189, eef_step_base=0.011241
idx 14: target_step_base=0.040712, eef_step_base=0.010332
```

Active-joint per-step follow-up:

```text
max_joint_delta: 0.01
overall_abs_dq_max: 0.00828410691511916
near_limit_component_fraction: 0.0
near_limit_step_fraction: 0.0
```

Updated data-quality interpretation:

- The transient threshold crossings should not be counted as stable reaching.
- The episode remains diagnostic-only data.
- Do not expand collection or train from this data.

Source-sync follow-up:

```text
target_step_base spikes:
  idx 1:  0.037657 m
  idx 2:  0.033334 m
  idx 9:  0.044189 m
  idx 10: 0.038757 m
  idx 14: 0.040712 m
  idx 15: 0.032510 m

base_step_world: typically 0.15-0.16 m/sample
base_yaw_step: typically 0.035-0.038 rad/sample
```

Data-quality conclusion:

- The timing05 threshold crossings are contaminated by target-in-base jumps.
- This dataset remains diagnostic-only and should not be used for training.
- The next data-quality check should be one source-aligned smoke after the
  package-local target updater fix, not a multi-episode collection.

## 2026-05-05 B8' Source-Aligned Data Quality

Dataset checked:

```text
data/raw/b8_reaching_smoke_tuned_v3_source_aligned_check/
```

Episode checked:

```text
b8_reaching_smoke_tuned_v3_source_aligned_check_0000.npz
```

Validation and quality:

```text
validation: PASS
T: 22
success: False
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 0
min_distance_overall: 0.0532669152181874
mean_initial_distance: 0.12408179276740143
mean_final_distance: 0.1551152861323729
mean_distance_reduction: -0.03103349336497148
```

Source-sync result:

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

Data-quality interpretation:

- This remains diagnostic-only data.
- The source-aligned updater improved early target/base stability, but the
  dynamic colliding target still produced late jumps.
- The target model has been changed to a static visual marker before any next
  smoke check.
- Do not expand collection or train from this data.

## 2026-05-05 B8' Static-Marker Source-Aligned Data Quality

Dataset checked:

```text
data/raw/b8_reaching_smoke_tuned_v3_static_marker_check/
```

Episode checked:

```text
b8_reaching_smoke_tuned_v3_static_marker_check_0000.npz
```

Runtime note:

```text
scripted expert failed mid-episode:
  IK failed with MoveIt error code -31
```

Validation and quality:

```text
validation: PASS
T: 22
success: False
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 1
min_distance_overall: 0.09603994656753867
mean_initial_distance: 0.10795291320748376
mean_final_distance: 0.09728469429144865
mean_distance_reduction: 0.010668218916035116
max_active_left_joint_delta: 0.010010654179503753
```

Source-sync result:

```text
target_step_base max: 0.011193 m
previous 0.06-0.10 m target-base jumps: absent
```

Data-quality interpretation:

- This is the cleanest B8' geometry smoke so far.
- It is still diagnostic-only data because the expert crashed and the saved
  metadata is `success=False`.
- Do not expand collection or train from this data until the IK failure is
  understood.

Command-motion follow-up:

```text
mean_best_action_to_eef_cosine: -0.001546695428668099
mean_best_lag_steps: 1.0
mean_best_realized_gain_along_action: 0.055096269666949214
recommendation: do_not_collect_more_until_command_to_motion_path_is_explained
```

Expert log follow-up:

```text
First MOVE_TO_PREGRASP command was published.
The expert then failed with MoveIt error code -31.
```

Updated data-quality interpretation:

- Geometry quality is improved, but the episode is still not collection-ready.
- The command/IK path must be debugged before collecting repeatability data.

Per-sample action/motion follow-up:

```text
action labels remain nonzero after the expert crash
joint_step_norm is zero from idx 5 through idx 21
distance remains near 0.096-0.097 m for most samples
```

Updated data-quality interpretation:

- The saved static-marker episode should not be used as an executed command
  dataset because action labels are stale after the IK failure.
- It remains diagnostic geometry evidence only.

## 2026-05-05 B8' IK-Context Static-Marker Runtime Check

Dataset path:

```text
data/raw/b8_reaching_smoke_tuned_v3_ik_context_check/
```

Episode:

```text
b8_reaching_smoke_tuned_v3_ik_context_check_0000.npz
```

Runtime result:

```text
multiple MOVE_TO_PREGRASP and MOVE_TO_GRASP commands published
no IK failure reproduced
scripted expert finished success=True with distance 0.091776 below 0.100000
```

Data-quality limitation:

```text
The recorder saved the NPZ before the expert success line, so the saved NPZ
still needs validation and offline quality diagnostics before it can be counted
as smoke-level data evidence.
```

Next data-quality action:

```text
Run read-only validation, reaching quality, source-sync, and command-motion
diagnostics on this single IK-context NPZ. Do not collect more episodes or
train before reviewing those outputs.
```

Validation and quality follow-up:

```text
validation: PASS
T: 22
metadata success: False
all_required_metadata_ok: true
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 1
min_distance_overall: 0.0828415071948108
mean_initial_distance: 0.10770328097682604
mean_final_distance: 0.08769499361884395
mean_distance_reduction: 0.020008287357982088
max_active_left_joint_delta: 0.07163564753196727
```

Data-quality interpretation:

- This is the first saved non-fallback static-marker B8' smoke NPZ with final
  distance below the `0.10 m` reaching threshold and positive distance
  reduction.
- It is smoke-level evidence only; do not expand collection or train.
- Saved `success=False` remains a metadata synchronization limitation.
- Source-sync and command-motion diagnostics must still be reviewed for this
  exact NPZ before any next collection decision.

### Per-Sample Trace Review

Read-only trace over:

```text
data/raw/b8_reaching_smoke_tuned_v3_modelstates_base_check/
  b8_reaching_smoke_tuned_v3_modelstates_base_check_0000.npz
```

Trace result:

```text
samples: 22
below_count: 0
min_distance: 0.12090753743754573
final_distance: 0.13143181756986858
max_target_step: 0.016551355118223997
max_eef_step: 0.007806147901855314
```

Command-motion result:

```text
target_base_net/max-step: 0.046422 / 0.016551
eef_base_net_norm: 0.048886
best lag steps: 2
best action-to-eef cosine: 0.872771
best eef-to-target cosine: 0.698900
best realized gain along action: 0.228406
best distance decreasing ratio: 0.368421
```

Data-quality interpretation:

- The target-base step spike is reduced, so this dataset is useful for the
  current blocker diagnosis.
- It remains unsuitable for repeatability collection or training because no
  sample reaches the `0.10 m` threshold and the final distance is worse than
  initial.
- Next review should focus on action clipping and lag-compensated realized EEF
  progress.

### Action Saturation / Lag Progress Review

Read-only analysis over:

```text
data/raw/b8_reaching_smoke_tuned_v3_modelstates_base_check/
  b8_reaching_smoke_tuned_v3_modelstates_base_check_0000.npz
```

Result:

```text
max_linear_step: 0.01
clip_component_fraction: 0.5909090909090909
clip_sample_fraction: 0.9545454545454546
lag_2_mean_motion_toward_target: 0.002913311600383822
lag_2_distance_decrease_ratio: 0.3888888888888889
```

Data-quality interpretation:

- This episode is useful diagnostic data, but not collection data.
- The expert is asking for clipped target-directed EE motion almost every
  sample, while the realized EEF progress remains too small and too
  inconsistent to reach the threshold.
- Next read-only check should inspect active joint per-step saturation before
  changing any runtime parameter.

### Active-Joint Step Saturation Review

Read-only analysis over:

```text
data/raw/b8_reaching_smoke_tuned_v3_modelstates_base_check/
  b8_reaching_smoke_tuned_v3_modelstates_base_check_0000.npz
```

Result:

```text
max_joint_delta: 0.01
overall_abs_dq_max: 0.0064445232886694015
step_norm_mean: 0.0060936974244918014
step_norm_max: 0.011151830271949407
near_limit_component_fraction: 0.0
near_limit_step_fraction: 0.0
```

Data-quality interpretation:

- The observed active joint per-component steps are not saturated.
- The episode remains diagnostic-only and should not be expanded.
- The next check can be one bounded parameter-only smoke that increases
  `max_linear_step` while keeping `max_joint_delta` unchanged.

## 2026-05-04 B8' Linear015 Attempt Data Quality

Dataset checked:

```text
data/raw/b8_reaching_smoke_tuned_v3_linear015_check/
```

Episode checked:

```text
b8_reaching_smoke_tuned_v3_linear015_check_0000.npz
```

Important parameter finding:

```text
Requested max_linear_step: 0.015
Recorded/launch max_linear_step: 0.01
```

Validation and quality:

```text
validation: PASS
T: 22
metadata success: False
episodes_below_threshold: 0
episodes_with_positive_distance_reduction: 1
min_distance_overall: 0.12092995986807226
mean_final_distance: 0.12181283826761834
mean_distance_reduction: 0.004700148271823371
```

Command-motion:

```text
mean_best_action_to_eef_cosine: 0.9001290086972836
mean_best_lag_steps: 3.0
mean_best_realized_gain_along_action: 0.17225911074464081
```

Data-quality interpretation:

- This episode is valid NPZ smoke data, but it is not a valid
  `max_linear_step=0.015` experiment because the launch wrapper did not pass the
  override through.
- The expert's later live `success=True` log happened after recorder save and
  does not override the saved NPZ/offline quality result.
- Do not expand this dataset or train from it.

## 2026-05-04 B8' Linear015 Fixed Data Quality

Dataset checked:

```text
data/raw/b8_reaching_smoke_tuned_v3_linear015_fixed_check/
```

Episode checked:

```text
b8_reaching_smoke_tuned_v3_linear015_fixed_check_0000.npz
```

Runtime parameter confirmation:

```text
max_linear_step: 0.015
max_joint_delta: 0.01
```

Validation and quality:

```text
validation: PASS
T: 22
success: False
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 0
min_distance_overall: 0.09764575942871043
mean_initial_distance: 0.12656234283023146
mean_final_distance: 0.1301823491793326
mean_distance_reduction: -0.003620006349101146
```

Per-sample / command-motion:

```text
below_count: 1
below_indices: [11]
max_target_step: 0.02990258511521412
max_eef_step: 0.007442174853866621
mean_best_action_to_eef_cosine: 0.8544660083304763
mean_best_lag_steps: 3.0
mean_best_realized_gain_along_action: 0.09906462168993792
```

Data-quality interpretation:

- This is valid non-fallback diagnostic smoke data.
- It is not acceptable for repeatability collection or training: threshold hit
  was transient and final distance was worse than initial.
- Increasing `max_linear_step` to `0.015` did not improve realized EEF gain.
- Next check should change timing only, not collect more data.

## 2026-05-04 B8' Tuned V3 Model-States-Base Data Quality

Dataset checked:

```text
data/raw/b8_reaching_smoke_tuned_v3_modelstates_base_check/
```

Episode checked:

```text
b8_reaching_smoke_tuned_v3_modelstates_base_check_0000.npz
```

Validation:

```text
validation: PASS
T: 22
success: False
unavailable_fields: ['raw_command']
```

Quality summary:

```text
all_required_metadata_ok: true
episodes_total: 1
episodes_valid_assumed: 1
episodes_below_threshold: 0
episodes_with_positive_distance_reduction: 0
min_distance_overall: 0.12090753743754559
mean_initial_distance: 0.12842290220394803
mean_final_distance: 0.13143181756986871
mean_distance_reduction: -0.0030089153659206835
```

Direction and command-motion summary:

```text
mean_action_to_eef_motion_cosine: 0.7703734921799059
mean_eef_motion_cosine_with_target: 0.5634035566283175
mean_eef_positive_target_direction_ratio: 0.8571428571428571
mean_best_action_to_eef_cosine: 0.8727706444229774
mean_best_lag_steps: 2.0
mean_best_realized_gain_along_action: 0.22840569163153385
```

Data-quality interpretation:

- This is valid live non-fallback smoke data.
- It is not acceptable for repeatability collection or training because it does
  not cross the `0.10 m` threshold and final distance is worse than initial.
- The model-states-base recording path reduced the evidence for recorder source
  mismatch, but the arm behavior still needs per-sample review before any new
  data collection.

Do not expand this dataset or train from it.

## 2026-05-05 B8' IK-Context Smoke Data Quality

Dataset checked:

```text
data/raw/b8_reaching_smoke_tuned_v3_ik_context_check/
```

Episode checked:

```text
b8_reaching_smoke_tuned_v3_ik_context_check_0000.npz
```

Runtime context:

```text
static visual marker target
base-relative target updater using gazebo_model_states base pose
world_base_tf_bridge.launch running
max_linear_step: 0.010
max_joint_delta: 0.010
time_from_start_sec: 1.0
gripper_enabled: false
is_grasp_dataset: false
```

Validation and reaching quality:

```text
validation: PASS
T: 22
saved metadata success: False
all_required_metadata_ok: true
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 1
min_distance_overall: 0.0828415071948108
mean_initial_distance: 0.10770328097682604
mean_final_distance: 0.08769499361884395
mean_distance_reduction: 0.020008287357982088
```

Command-motion diagnostic:

```text
mean_best_action_to_eef_cosine: 0.21415299860000098
mean_best_lag_steps: 2.0
mean_best_realized_gain_along_action: 0.1560406398996791
recommendation: do_not_collect_more_until_command_to_motion_path_is_explained
```

Source-sync diagnostic:

```text
min_distance: 0.08284150719481084
final_distance: 0.08769499361884403
max_target_step_base: 0.012109104884360282
large_target_step_indices: []
```

Data-quality interpretation:

- This is a valid one-episode non-fallback arm-only reaching smoke.
- It crosses and ends below the `0.10 m` threshold, with positive distance
  reduction.
- Target/base source synchronization is clean enough for this smoke episode:
  no target-in-base step jumps above `0.03 m`.
- It is not repeatability-collection ready because command-to-motion alignment
  is still mixed and saved metadata still reports `success=False`.
- Do not expand collection and do not train from this single smoke episode.

Recorder metadata follow-up:

```text
Root cause: recorder saved before the expert's final success=True message
arrived, so metadata fell back to launch parameter success=False.
Code fix: recorder now computes saved reaching/pregrasp success from the final
recorded relative_target_to_eef distance.
Static verification: existing IK-context final recorded distance is
0.08769499361884395 m, so the fixed recorder would save success=True.
```

This fix does not create new data by itself. It must be validated by exactly
one short new smoke episode before repeatability collection.

## 2026-05-05 B8' Success-Sync Smoke Validation

Dataset checked:

```text
data/raw/b8_reaching_smoke_tuned_v3_success_sync_check/
```

Episode checked:

```text
b8_reaching_smoke_tuned_v3_success_sync_check_0000.npz
```

Runtime:

```text
static visual marker target
base-relative target updater using gazebo_model_states base pose
max_linear_step: 0.010
max_joint_delta: 0.010
time_from_start_sec: 1.0
gripper_enabled: false
is_grasp_dataset: false
scripted expert finished: success=True, distance 0.035195 below 0.100000
```

Validation and metadata:

```text
validation: PASS
T: 22
success: True
success scalar: True
metadata success: True
success_source: recorded_final_distance
recorded_success_distance_m: 0.0404588355643862
recorded_success_distance_threshold_m: 0.1
unavailable_fields: ['raw_command']
```

Data-quality interpretation:

- This validates the recorder success synchronization fix at smoke level.
- Saved success now matches recorded reaching distance instead of staying at
  the launch default `success=False`.
- This is not repeatability evidence and is not a training dataset.
- Do not report grasp success or learned rollout success from this result.

## 2026-05-05 B8' Repeatability Smoke Collection

Scope:

- Collected five short real non-fallback arm-only reaching/pre-grasp smoke
  episodes.
- No BC / Diffusion Policy / Flow Matching Policy training was run.
- No learned policy rollout was run.
- No gripper command was sent and no hand controller was started.

Launch/runtime:

```text
uvms_control/oberon7_position_control.launch gui:=false paused:=false
rexrov_single_oberon7_fm_dp/b5d_move_group_with_context.launch allow_trajectory_execution:=false
rexrov_single_oberon7_fm_dp/load_left_controllers.launch start:=true load_hand:=false
rexrov_single_oberon7_fm_dp/world_base_tf_bridge.launch
rexrov_single_oberon7_fm_dp/b8_reaching_tuned_v3_episode.launch
```

Episode parameters:

```text
max_linear_step: 0.010
max_joint_delta: 0.010
time_from_start_sec: 1.0
rate_hz: 3.0
max_duration_sec: 7.2
allow_nominal_state_fallback: false
gripper_enabled: false
is_grasp_dataset: false
task_type: arm_only_reaching
success_metric: reaching_success
```

Dataset:

```text
data/raw/b8_reaching_repeatability_smoke/
  b8_reaching_repeatability_smoke_0000.npz
  b8_reaching_repeatability_smoke_0001.npz
  b8_reaching_repeatability_smoke_0002.npz
  b8_reaching_repeatability_smoke_0003.npz
  b8_reaching_repeatability_smoke_0004.npz
```

Quality artifacts:

```text
outputs/logs/b8_reaching_repeatability_smoke/repeatability_summary.json
outputs/logs/b8_reaching_repeatability_smoke/repeatability_summary.md
outputs/logs/b8_reaching_repeatability_smoke_quality/per_episode_quality.json
outputs/logs/b8_reaching_repeatability_smoke_quality/per_episode_quality.md
outputs/logs/b8_reaching_repeatability_smoke_quality/distance_curves.png
outputs/logs/b8_reaching_repeatability_smoke_direction/direction_diagnostic.json
outputs/logs/b8_reaching_repeatability_smoke_command_motion/command_motion_diagnostic.json
```

Validation and metadata:

```text
validator_pass_count: 5/5
T: 22 for all episodes
success_count: 5
reaching_success_rate: 1.0
all_required_metadata_ok: true
all_success_metadata_consistent: true
success_source: recorded_final_distance for all episodes
allow_nominal_state_fallback: false for all episodes
base_state_source: gazebo_model_states for all episodes
joint_state_source: joint_states for all episodes
target_state_source: gazebo_model_states for all episodes
gripper_enabled: false for all episodes
is_grasp_dataset: false for all episodes
unavailable_fields: ['raw_command'] for all episodes
```

Distance and source-sync result:

```text
initial_distance_per_episode:
  [0.10792017854224915,
   0.1083219563070354,
   0.10742952851370599,
   0.10812468561962112,
   0.10649736989782044]
min_distance_per_episode:
  [0.06296655604382587,
   0.04955370542041048,
   0.05586573174312177,
   0.06039576817075455,
   0.06681846583370564]
final_distance_per_episode:
  [0.06906018109665871,
   0.04955370542041048,
   0.05586573174312177,
   0.06042199881789199,
   0.06681846583370564]
mean_final_distance: 0.06034401658235772
min_distance_overall: 0.04955370542041048
mean_distance_reduction: 0.0473147271937287
max_target_step_base: 0.014892885342403243
large_target_step_indices: [] for all episodes
```

Command-motion:

```text
mean_best_action_to_eef_cosine: 0.7559808833882034
mean_best_lag_steps: 2.2
mean_best_realized_gain_along_action: 0.2432157689973347
```

Decision:

```text
B8' repeatability smoke is resolved at the 5-episode smoke level.
```

Interpretation:

- This is real non-fallback arm-only reaching/pre-grasp evidence.
- This is not grasping and not learned-policy rollout evidence.
- Do not train BC / DP / FM directly from this smoke result.
- Next data action should be a small, deliberate real non-fallback arm-only
  data collection plan with the same validation and quality gates.

## 2026-05-05 B8' Two-Pass Target Gate After Settle

Record label:

```text
B8' target/base two-pass settle gate：two consecutive read-only target-aware
gates after settle, no episode collection, no training, no gripper.
```

Result:

```text
gate_0 passed=true
relative_base_drift=3.503815165242792e-05
target_base_drift=0.001223737760115677
initial_distance=0.1076746834400219

gate_1 passed=true
relative_base_drift=4.5012944528958283e-05
target_base_drift=0.001223737760115677
initial_distance=0.10766337265266729
```

Data-quality decision:

```text
This was not collection. The target/base settle gate is smoke-level resolved
after two consecutive read-only passes. Any next episode must still be preceded
by return-to-reference and a fresh target-aware gate, and must be followed by
validator and quality/command-motion diagnostics.
```

## 2026-05-05 B8' Action-Frame Fix And Post-Fix Single Episode

Record label:

```text
B8' action-frame fix + one post-fix return-gated arm-only reaching/pre-grasp
verification episode，不扩采、不训练、不处理 gripper。
```

Pre-fix failed episode:

```text
data/raw/b8_return_gated_arm_verify_3/b8_return_gated_arm_verify_3_0000.npz
validator=PASS
success=false
runtime failure=IK failed with MoveIt error code -31
recorded_success_distance_m=0.10966874121994438
distance_reduction=-0.0021273869346622593
mean_best_action_to_eef_cosine=0.08695271743383595
mean_best_realized_gain_along_action=0.022552544812475088
```

Code fix:

```text
file=src/rexrov_single_oberon7_fm_dp/expert_policy.py
fix=use target_directed_action_frame for the arm converter when
    target_directed_reaching=true
py_compile=PASS
```

Post-fix episode:

```text
data/raw/b8_return_gated_arm_verify_4/b8_return_gated_arm_verify_4_0000.npz
runtime action_frame=base_link
runtime expert success=True
validator=PASS
success=True
success_source=recorded_final_distance
recorded_success_distance_m=0.05744791236250198
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
mean_best_action_to_eef_cosine=0.3532763904220775
mean_best_lag_steps=0.0
mean_best_realized_gain_along_action=0.17090696757478616
```

Data-quality decision:

```text
The action-frame bug is smoke-fixed and one post-fix real non-fallback
arm-only episode succeeded. This is not enough to train or expand collection.
Require return-to-reference and a fresh target-aware gate before every next
episode; target/base gate may need a 5 s settle retry.
```

## 2026-05-05 B8' Tiny Post-Fix Repeatability Check

Record label:

```text
B8' tiny post-fix repeatability check：2-cycle real non-fallback arm-only
reaching/pre-grasp return->gate->episode check，不训练、不 rollout、不处理 gripper。
```

Output:

```text
data/raw/b8_postfix_repeatability_2/b8_postfix_repeatability_2_0000.npz
data/raw/b8_postfix_repeatability_2/b8_postfix_repeatability_2_0001.npz
```

Strict summary:

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
```

Quality:

```text
initial_distance_per_episode=[0.1075630541970971, 0.10756418870221732]
min_distance_per_episode=[0.053346384327736994, 0.05765681709279224]
final_distance_per_episode=[0.05464734951940092, 0.05996229955194503]
distance_reduction_per_episode=[0.05291570467769617, 0.04760188915027229]
mean_final_distance=0.057304824535672975
mean_distance_reduction=0.05025879691398423
max_active_left_joint_delta=0.03859894310454148
max_target_step_base=0.007109516133871766
large_target_step_indices=[] for both
mean_best_action_to_eef_cosine=0.5379418351868376
mean_best_lag_steps=0.0
mean_best_realized_gain_along_action=0.17491140517275186
```

Data-quality decision:

```text
Tiny post-fix repeatability is smoke-level resolved. This supports planning a
small post-fix debug batch with per-episode return/gate/diagnostics, but it is
not training readiness and not learned rollout or grasp evidence.
```

## 2026-05-05 B8' Small Post-Fix Debug Batch Plan

Record label:

```text
B8' small post-fix debug batch plan：planned 3-episode real non-fallback
arm-only reaching/pre-grasp debug batch with per-episode return/gate/diagnostics.
No collection executed for this entry.
```

Planned paths:

```text
data/raw/b8_postfix_debug_3/
outputs/logs/b8_postfix_debug_3/
outputs/logs/b8_postfix_debug_3_quality/
outputs/logs/b8_postfix_debug_3_direction/
outputs/logs/b8_postfix_debug_3_command_motion/
outputs/logs/b8_initial_state_gate/b8_postfix_debug_3_*.json
```

Planned scale:

```text
default_episode_count=3
hard_max_episode_count=5
do not run 10+ episodes in this step
```

Per-episode policy:

```text
return_to_reference -> target-aware gate -> corrected target-directed
arm-only episode -> later validator/quality diagnostics

If target-aware gate fails from target/base settle, wait 5 s and retry once.
If retry fails, stop without collecting that episode.
```

Required collection settings:

```text
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

Pass criteria:

```text
validator_pass_count=N/N
success_count=N/N preferred
all_required_metadata_ok=true
all_success_metadata_consistent=true
large_target_step_indices=[] for all episodes
mean_distance_reduction positive
command-motion must not collapse toward the pre-fix failed values
final return/gate passes
```

Data-quality decision:

```text
This is only a plan. It does not authorize training, learned rollout,
gripper work, or grasp claims.
```

## 2026-05-05 B8' Small Post-Fix Debug Batch Attempt Stopped By Gate

Record label:

```text
B8' small post-fix debug batch attempt：planned 3 episodes, stopped at cycle 0
target-aware gate before collection. No episode was collected.
```

Artifacts:

```text
outputs/logs/b8_initial_state_gate/b8_postfix_debug_3_0000_return.json
outputs/logs/b8_initial_state_gate/b8_postfix_debug_3_0000_gate.json
outputs/logs/b8_initial_state_gate/b8_postfix_debug_3_0000_gate_retry.json
```

Result:

```text
episodes_collected=0
return reached=true
return commands_sent=0
return gripper_commands_sent=false

gate passed=false
gate initial_distance=0.1159362425810477
gate relative_base_drift=0.00872391480943356

gate_retry_after_5s passed=false
gate_retry initial_distance=0.11528983854046555
gate_retry relative_base_drift=0.008109968028264436
```

Data-quality decision:

```text
The stop policy worked. No episode was collected from a marginal precondition.
Do not train, do not expand, and do not treat this as dataset evidence. Diagnose
the target-aware initial-distance gate boundary before retrying collection.
```

## 2026-05-05 B8' Gate Boundary Probe

Record label:

```text
B8' gate boundary probe：5 read-only target-aware gate checks after the stopped
small post-fix debug batch attempt. No episode collection, no training, no
gripper command.
```

Artifacts:

```text
outputs/logs/b8_initial_state_gate/gate_boundary_probe/gate_*.json
outputs/logs/b8_initial_state_gate/gate_boundary_probe/gate_boundary_probe_summary.json
outputs/logs/b8_initial_state_gate/gate_boundary_probe/gate_boundary_probe_summary.md
```

Result:

```text
checks_total=5
pass_count=3
fail_count=2
episodes_collected=0
control_commands_sent=false for all
gripper_commands_sent=false for all
initial_distance_values=[0.11326617951540467, 0.11374995074828124, 0.11564356703916857, 0.10753170023825985, 0.11502167746808681]
relative_base_drift_values=[0.006954684079328241, 0.007563652990111229, 0.008480493184240828, 0.0012413657006039953, 0.007817255991339152]
```

Data-quality decision:

```text
No new data was collected. The blocker is intermittent target-aware initial
geometry near the initial_distance_max=0.115 m boundary. Do not collect, train,
or relax thresholds until target probe/base-relative updater behavior is
checked read-only.
```

## 2026-05-05 B8' ROS Graph Target-Updater Spot Check

Record label:

```text
B8' target-updater spot check：read-only ROS graph/topic inspection after gate
boundary failures. No episode collection, no training, no gripper command.
```

Result:

```text
filtered rosnode list:
  /b8_target_gate_base_relative_target
  /dp_fm_left_arm_controller_starter
  /dp_fm_odom_tf_bridge

duplicate target updater observed: false
episodes_collected: 0
```

Data-quality note:

```text
The raw grep of /gazebo/model_states is inconclusive because model_states uses
parallel name[] and pose[] arrays. The target pose must be read by matching
the index of cylinder_target_gate_probe in name[] and then printing pose[index].
```

## 2026-05-05 B8' Indexed Target Pose Probe

Record label:

```text
B8' indexed target pose probe：read-only indexed /gazebo/model_states check for
cylinder_target_gate_probe, followed by one target-aware gate. No episode
collection, no training, no gripper command.
```

Result:

```text
target_model_name: cylinder_target_gate_probe
samples: 10
target world pose moved from:
  [24.7291204633037, -13.440451519135685, -99.71307050685847]
to:
  [25.7584837884664, -13.290649770155733, -99.71303967275239]
```

Follow-up gate:

```text
passed=true
initial_distance=0.10771781639816572
relative_base_drift=1.5569323561687856e-05
target_base_drift=8.595952887736536e-05
control_commands_sent=false
gripper_commands_sent=false
episodes_collected=0
```

Data-quality decision:

```text
No new data was collected. The indexed target pose check confirms that the
probe target is moving in world, which is expected for a base-relative target.
The passing follow-up gate confirms target-in-base geometry can be clean, but
the previous intermittent gate-boundary failures remain unresolved. Do not
collect or train until base/target indexed relative motion is checked during
the same sampling window.
```

## 2026-05-05 B8' Indexed Base+Target Relative-Motion Probe

Record label:

```text
B8' indexed base+target relative-motion probe：read-only synchronized
/gazebo/model_states check for rexrov and cylinder_target_gate_probe. No
episode collection, no training, no gripper command.
```

Result:

```text
samples: 20
target_in_base_mean=[2.1643409987668636, 0.4999520343001693, -1.2753631745317109]
target_in_base_range=[0.006791861699614543, 0.0004789883705331732, 0.0024808085858580853]
target_in_base_range_norm=0.007246601027065321
episodes_collected=0
```

Data-quality decision:

```text
No new data was collected. The base-relative target is stable enough for the
current 0.01 m relative-drift gate. Remaining small debug-batch blocker is the
initial-distance gate policy near 0.115 m, not gross target/base
desynchronization.
```

## 2026-05-05 B8' Conservative Gate Policy Helper

Record label:

```text
B8' conservative gate policy helper：implemented scheme 1 for the next tiny
post-fix debug batch. No episode collection, no training, no learned rollout,
no gripper command.
```

Implementation:

```text
scripts/run_b8_postfix_debug_batch_conservative.py
```

Default output paths when executed later:

```text
data/raw/b8_postfix_debug_3/
outputs/logs/b8_postfix_debug_3_conservative/
outputs/logs/b8_postfix_debug_3_summary/
```

Data-quality policy:

```text
Keep initial_distance_max=0.115 m.
Before each episode:
  return active-left joints to reference;
  run target-aware gate with wait/retry;
  collect only after fresh gate pass.
Stop on return failure, gate failure after retries, collect failure,
validator failure, or summary failure.
```

No data was collected by this documentation/implementation step.

## 2026-05-05 B8' Conservative Batch Attempt

Record label:

```text
B8' conservative scheme-1 attempt：run conservative return/gate/collect helper
with episode_count=3. Stopped before collection because fresh target-aware gate
did not pass. No training, no learned rollout, no gripper command.
```

Manifest:

```text
outputs/logs/b8_postfix_debug_3_conservative/conservative_batch_manifest.json
```

Result:

```text
episodes_requested=3
episodes_completed=0
episodes_collected=0
stop_reason=fresh gate did not pass for b8_postfix_debug_3_0000
```

Return result:

```text
reached=true
commands_sent=0
gripper_commands_sent=false
joint_l2_error=0.00010753423427348858
joint_max_abs_error=9.103467156545975e-05
```

Gate result:

```text
gate_attempts=6
initial_distance_ok=true for all attempts
relative_base_drift_ok=false for all attempts
initial_distance≈0.11029-0.11040 m
relative_base_drift≈0.02326-0.02328 m
target_base_drift≈0.02327-0.02329 m
```

Data-quality decision:

```text
No episode was collected from the gate-failing state. The conservative stop
condition worked. The next work is target probe reinitialization / fresh gate
checks, not training or expansion.
```

## 2026-05-05 B8' Target Probe Restart / Reset Helper

Record label:

```text
B8' target probe restart check：restart b8_target_gate_probe.launch and rerun
two fresh target-aware gates. No episode collection, no training, no learned
rollout, no gripper command.
```

Result:

```text
spawn_b8_target_gate_probe failed because cylinder_target_gate_probe already
exists.
fresh gates: 0/2 passed.
episodes_collected=0
```

Gate metrics:

```text
gate_0 relative_base_drift=0.023257329633886537
gate_1 relative_base_drift=0.023272689950670524
initial_distance_ok=true for both gates
relative_base_drift_ok=false for both gates
```

Data-quality decision:

```text
Do not collect from this target state. Add/use a target-only reset step that
deletes the stale cylinder_target_gate_probe model before relaunching the
target probe.
```

Implementation note:

```text
scripts/reset_b8_target_gate_probe.py added. It deletes only the gate target
model and sends no arm/gripper commands.
```

## 2026-05-05 B8' Target Reset And Fresh Gate Validation

Record label:

```text
B8' target reset and fresh gate validation：delete stale cylinder_target_gate_probe,
cleanly respawn target probe, and run two fresh target-aware gates. No episode
collection, no training, no learned rollout, no gripper command.
```

Reset:

```text
passed=true
delete_success=true
absent_after_delete=true
control_commands_sent=false
gripper_commands_sent=false
```

Relaunch:

```text
SpawnModel: Successfully spawned entity
target_base_xyz initialized near reference:
  [2.1598220509962056, 0.500061142548624, -1.2763767663921255]
```

Gate validation:

```text
gate_pass_count=2/2
gate_0 initial_distance=0.10479344544370915
gate_0 relative_base_drift=0.003596792375915908
gate_1 initial_distance=0.1096170277494551
gate_1 relative_base_drift=0.0021184551807263505
episodes_collected=0
```

Data-quality decision:

```text
Target gate precondition is restored at smoke level. No data was collected by
this check. The next data-affecting step is to rerun the conservative helper,
which must still validate each episode and stop on any gate/collection problem.
```

## 2026-05-05 B8' Conservative Post-Fix Debug Batch

Record label:

```text
B8' conservative post-fix debug batch：3 episode real non-fallback arm-only
reaching/pre-grasp debug collection with per-episode return/gate/validation.
No training, no learned rollout, no gripper command.
```

Data:

```text
data/raw/b8_postfix_debug_3/
  b8_postfix_debug_3_0000.npz
  b8_postfix_debug_3_0001.npz
  b8_postfix_debug_3_0002.npz
```

Helper manifest:

```text
outputs/logs/b8_postfix_debug_3_conservative/conservative_batch_manifest.json
```

Note:

```text
The helper ended with "summary failed" only because
summarize_b8_repeatability_smoke.py was not executable via rosrun at that
moment. All return/gate/collect/validate steps completed for 3/3 episodes.
The summary was rerun manually after fixing the diagnostic script install /
execution path.
```

Summary artifacts:

```text
outputs/logs/b8_postfix_debug_3_summary/repeatability_summary.json
outputs/logs/b8_postfix_debug_3_summary/repeatability_summary.md
```

Results:

```text
episodes_total=3
episodes_valid=3
validator_pass_count=3
success_count=3
reaching_success_rate=1.0
all_required_metadata_ok=true
all_success_metadata_consistent=true
mean_initial_distance=0.11136879013891778
mean_final_distance=0.04966386411855266
mean_distance_reduction=0.06170492602036512
min_distance_overall=0.04882503315948199
max_active_left_joint_delta=0.04715301585407605
max_target_step_base=0.007595107419430765
large_target_step_indices_by_episode=[] for all episodes
mean_best_action_to_eef_cosine=0.7134615751223703
mean_best_lag_steps=0.0
mean_best_realized_gain_along_action=0.2127923769777379
failure_reason_by_episode=none for all episodes
```

Data-quality decision:

```text
This 3-episode post-fix debug batch passes at smoke level. It is valid
non-fallback arm-only reaching/pre-grasp debug data, but it is not a final
training dataset, not learned rollout evidence, and not grasp success.
```

## 2026-05-05 B8' Controlled 10-Episode Post-Fix Batch Attempt

Record label:

```text
B8' controlled 10-episode post-fix debug batch attempt：planned and started
with the conservative return/gate/validate helper. No training, no learned
rollout, no gripper command.
```

Intended output:

```text
data/raw/b8_postfix_debug_10/
outputs/logs/b8_postfix_debug_10_conservative/
outputs/logs/b8_postfix_debug_10_summary/
```

Result:

```text
episodes_requested=10
episodes_collected=0
status=stopped before collection
reason=ROS master/runtime unavailable during first return step
```

Data-quality decision:

```text
No data was collected, so there is no new data-quality result. Retry only after
restarting the required ROS/Gazebo runtime and clean target probe. The helper
now has per-step timeouts to avoid hanging if runtime becomes unavailable.
```

## 2026-05-06 B8' Controlled 10-Episode Retry Precheck

Record label:

```text
B8' controlled 10-episode retry precheck：two target-aware gates before any
clean 10-episode collection. No training, no learned rollout, no gripper
command.
```

Gate result:

```text
gate_pass_count=0/2
gate_0 initial_distance=0.11033622160686253
gate_0 relative_base_drift=0.0232793818376196
gate_1 initial_distance=0.11041099785110788
gate_1 relative_base_drift=0.02325376923014353
```

Data-quality decision:

```text
Do not collect from this target state. The gate failed because target/base
relative geometry was again offset by about 2.3 cm.
```

Existing output-directory note:

```text
data/raw/b8_postfix_debug_10 already contains partial prior files:
  b8_postfix_debug_10_0000.npz: validator PASS, T=22
  b8_postfix_debug_10_0001.npz: validator PASS, T=22
  b8_postfix_debug_10_0002.npz: validator PASS, T=6
```

Decision:

```text
Treat data/raw/b8_postfix_debug_10 as partial/contaminated, not as the clean
10-episode batch. Use a new clean output directory/prefix after target reset
and two passing gates.
```

## 2026-05-06 B8' Clean Controlled 10-Episode Post-Fix Debug Batch

Record label:

```text
B8' clean controlled 10-episode post-fix debug batch：real non-fallback
arm-only reaching/pre-grasp debug collection with per-episode
return/gate/validate. No training, no learned rollout, no gripper command.
```

Output:

```text
data/raw/b8_postfix_debug_10_clean/
outputs/logs/b8_postfix_debug_10_clean_conservative/
outputs/logs/b8_postfix_debug_10_clean_summary/
```

Summary:

```text
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
```

Data-quality decision:

```text
Clean 10-episode scripted arm-only post-fix debug batch passes the current
smoke-level B8' quality criteria. Keep this result separate from partial
attempt data/raw/b8_postfix_debug_10 and do not treat it as grasp data.
```

Offline comparison artifact:

```text
outputs/logs/b8_postfix_debug_10_clean_comparison/fix_effect_comparison.md
outputs/logs/b8_postfix_debug_10_clean_comparison/fix_effect_comparison.json
```

Comparison against failed pre-fix `b8_reaching_debug_10`:

```text
success_count: 7/10 -> 10/10
mean_final_distance: 0.08288684626534658 -> 0.05024581695716414
mean_distance_reduction: 0.02578654461012293 -> 0.05853092374442983
mean_best_lag_steps: 2.6 -> 0.1
```

## 2026-05-06 B8' Larger Controlled Debug Collection Planning

Record label:

```text
B8' larger controlled debug collection / training-dataset planning approval.
No training, no learned rollout, no gripper command.
```

Planning artifact:

```text
outputs/logs/b8_training_dataset_planning/b8_controlled_collection_plan.md
```

Recommended next controlled collection:

```text
data/raw/b8_controlled_debug_20/
outputs/logs/b8_controlled_debug_20_conservative/
outputs/logs/b8_controlled_debug_20_summary/
```

Data-use rule:

```text
Do not merge into a training dataset until the controlled 20-episode collection
passes validation and a read-only dataset manifest/quality report is generated.
Training still requires explicit approval.
```

## 2026-05-06 B8' Controlled 20-Episode Attempt

Record label:

```text
B8' controlled 20-episode debug collection attempt. No training, no learned
rollout, no gripper command.
```

Result:

```text
episodes_requested=20
episodes_collected=0
status=stopped before collection
reason=fresh gate did not pass for b8_controlled_debug_20_0000
manifest=outputs/logs/b8_controlled_debug_20_conservative/conservative_batch_manifest.json
```

Data-quality decision:

```text
No data was collected. Do not treat this as a failed reaching episode and do
not merge any output into a training dataset. Continue debugging target
freshness/geometry after return-to-reference.
```

## 2026-05-06 B8' Controlled 20-Episode Debug Collection

Record label:

```text
B8' controlled 20-episode real non-fallback arm-only reaching/pre-grasp debug
collection with return/gate/validate strategy. No training, no learned rollout,
no gripper command.
```

Output:

```text
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

Data-quality decision:

```text
The controlled 20-episode debug collection passes the current B8' debug
criteria and may be considered for a read-only training-dataset candidate
manifest. It must not be used for training until that manifest/quality report is
generated and training is explicitly approved.
```

Notes:

```text
Do not treat this as grasp data. gripper_enabled=false and is_grasp_dataset=false
remain required. Episode 0010 is an initial-distance boundary case and should be
flagged in the candidate dataset manifest.
```

## 2026-05-06 B8' Training-Dataset Candidate Manifest

Record label:

```text
B8' read-only training-dataset candidate manifest / quality report. No
training, no learned rollout, no gripper command.
```

Artifacts:

```text
outputs/logs/b8_training_dataset_candidate_manifest/candidate_manifest.md
outputs/logs/b8_training_dataset_candidate_manifest/candidate_manifest.json
outputs/logs/b8_training_dataset_candidate_manifest/candidate_episodes.csv
```

Primary candidate:

```text
data/raw/b8_postfix_debug_10_clean/
data/raw/b8_controlled_debug_20/
episode_count=30
validator_pass_count=30/30
success_count=30/30
mean_final_distance=0.05003238637536062
mean_distance_reduction=0.05960007870215763
```

Optional separate smoke source:

```text
data/raw/b8_postfix_debug_3/
episode_count=3
validator_pass_count=3/3
success_count=3/3
```

Excluded:

```text
data/raw/b8_reaching_debug_10/
data/raw/b8_postfix_debug_10/
Stage 6 fallback datasets as real demonstrations
```

Data-use decision:

```text
Primary candidate pool is ready for training-planning review. Training has not
started and still requires explicit approval.
```

Training-planning follow-up:

```text
outputs/logs/b8_training_dataset_candidate_manifest/dataset_split_primary_30.json
outputs/logs/b8_training_dataset_candidate_manifest/dataset_loader_check_primary_30.json
outputs/logs/b8_primary30_training_planning/training_config_review.md
```

BC sanity training has now been run on the primary candidate split:

```text
config/train_bc_b8_primary30_sanity.yaml
outputs/logs/b8_primary30_bc_sanity/train_summary.json
outputs/eval/b8_primary30_bc_sanity/offline_eval_train.json
outputs/eval/b8_primary30_bc_sanity/offline_eval_val.json
```

This is a training-code sanity check only, not rollout evaluation and not grasp
success.

## 2026-05-07 Live Evaluation Artifact Note

No new demonstration dataset was collected in this step. The generated files
are live evaluation logs for active-left arm-only reaching / pre-grasp
positioning, not grasp data and not additional training data.

Artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_protocol_attempts_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_protocol_attempts_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v8_success_guard.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v8_success_guard.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v8_after_user_restart.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v8_after_user_restart.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v9_threshold095_after_user_restart.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v9_threshold095_after_user_restart.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v10_aligned_success_guard.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v10_aligned_success_guard.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v10b_aligned_success_guard.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v10b_aligned_success_guard.md
```

Data-use decision:

```text
Do not add these logs to the B8' demonstration dataset. Use them only as live
evaluation/debug artifacts.
```

Update after v11 terminal-final-distance protocol:

```text
No new demonstration data was collected.
BC/DP/FM live N=3 comparison artifacts were generated from evaluation rollouts
only.
Do not add any rollout logs to the B8' primary30 training dataset.
```

Final live comparison artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v11_terminal_final_distance.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v11_terminal_final_distance.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v11_terminal_final_distance_n5_partial.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v11_terminal_final_distance_n5_partial.md
```

Update after v12b N=10:

```text
No new demonstration data was collected.
The latest live evaluation artifacts are N=10 success-rate summaries, not
training data.
Do not add rollout logs to the B8' primary30 training dataset.
```

N=10 artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v12b_terminal_final_distance_n10.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v12b_terminal_final_distance_n10.md
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol_v12b_terminal_final_distance_n10/
```
