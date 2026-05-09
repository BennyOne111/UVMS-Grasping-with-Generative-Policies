# TODO

## Current TODO: Arm-Only Reaching / Pre-Grasp Route

2026-05-07 formal live protocol update:

- [x] Create a formal same-protocol BC / DP / FM arm-only reaching/pre-grasp
  live evaluation protocol.
  - Artifacts:
    `outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/formal_protocol.md`
    and `.json`.
- [x] Run read-only runtime checks for ROS topics, TF, active-left controller,
  and no hand controller before live execution.
- [x] Attempt BC cycle 0 initial gate under the formal protocol.
  - Result: return-to-reference passed, but strict target-aware pre-gate failed
    three times on target/relative drift. No rollout command and no gripper
    command were sent.
- [x] Stop live execution and generate partial summary instead of forcing
  policy commands through a failed gate.
  - Artifacts:
    `outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/bc/cycle_0/summary.md`
    and
    `outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md`.
- [ ] Restore clean target/base sync before any further live BC/DP/FM command.
  Minimum next action: reset or restart the target gate probe/base-relative
  target updater, then require two strict fresh gates with target and relative
  drift within threshold.
  - 2026-05-07 follow-up: target gate probe was reset/restarted and target
    became present again, but strict pre-gate still failed with
    `target_base_drift=0.006711007793366516` and
    `relative_base_drift=0.006271075196806217`. Do not continue live rollout
    until the frame/target sync blocker is resolved.
- [ ] After clean gates pass, rerun BC formal N=3 first. DP/FM dry-run and
  live smoke remain pending until the shared gate passes.
  - 2026-05-07 aggressive update: protocol v4 ran with shared gates. DP and FM
    completed N=3 with 3/3 reaching success and no abort. BC reached the
    distance threshold in cycle 0 but safety-aborted on IK error code `-31`, so
    BC remains 0/1 under the formal protocol and the three-method comparison is
    still incomplete.
- [ ] Next BC-specific fix: add a same-protocol early-stop-on-reaching option
  or IK failure guard after success threshold is reached, then rerun all methods
  under the revised shared protocol if a fair three-method table is required.

Current route:

```text
arm-only reaching / pre-grasp demo
-> B5d': scripted expert drives left arm toward static/base-relative target
-> B8': small real non-fallback reaching/pre-grasp demonstrations
-> retrain BC / DP / FM
-> real arm-only rollout evaluation
```

Current status:

- [x] B5d' debug-smoke minimal resolved for arm-only reaching/pre-grasp.
- [x] B8' collect 5 short real non-fallback arm-only reaching/pre-grasp
  episodes.
- [x] Validate every B8' episode and record distance/joint-motion metrics.
- [x] Review B8' 5-episode smoke quality before training or expansion.
- [x] Implement base-relative arm-only BC observation and safe action
  normalization for rollout planning.
- [x] Implement a dedicated active-left arm-only execution-smoke adapter with
  default-off command publishing, no gripper, and explicit execution ack.
- [x] Run first tiny BC base-relative arm-only learned smoke; command path
  smoke resolved, but no arm-only success claim.
- [x] Return after first tiny smoke and verify the strict target-aware gate
  returns to a controlled initial state.
- [x] Run second tiny BC base-relative arm-only learned smoke with only
  `max_control_ticks` changed from `3` to `5`; one reviewed arm-only reaching
  smoke threshold was met.
- [x] Return after the second tiny smoke and run one strict fresh target-aware
  gate before any further live learned execution.
  - 2026-05-07 result: return reached reference with
    `joint_l2_error=0.00010727774213185266`, no gripper command. The first
    strict gate failed only on marginal `initial_distance=0.11597705385617631`;
    one 5 s read-only retry passed with
    `initial_distance=0.11436097332458071`.
- [x] Do not run a third learned smoke, rollout batch, or DP/FM live execution
  until the second-smoke summary is reviewed and a separate repeatability plan
  is approved.
- [x] Return to offline-only DP/FM after the second tiny smoke; rerun
  sampling-step sensitivity and generate a post-live-smoke gate report.
- [x] Run only bounded offline DP h8 budget/seed ablation under the same
  base-relative observation and safe action normalization.
  - 2026-05-07 result: seed86 improved the best DP candidate to
    `action_mse=3.1088134733181505e-07`, but BC remains better at
    `3.066821534503106e-07`. DP/FM live remains blocked.
- [x] Prepare the BC base-relative N=2 tiny repeatability runbook and
  read-only aggregate summary helper. Do not execute it automatically.
- [x] If explicitly approved for live work, run only the N=2 repeatability
  runbook with stop-on-first-failure; do not jump to N=3 or a larger rollout
  batch.
  - 2026-05-07 result: N=2 passed,
    `repeatability_smoke_status=arm_only_reaching_repeatability_smoke_passed`,
    success_count=2/2, mean_final_distance=0.07611795154782355,
    min_gate_distance_reduction=0.034746377345962684, no gripper command, no
    grasp/general learned rollout success claim. Post-repeatability return and
    strict gate also passed.
- [ ] If explicitly continuing live work, plan only N=3 repeatability with the
  same fixed checkpoint/action horizon/clip/tick parameters and corrected
  post-gate handling; do not jump to a large rollout batch.
  - 2026-05-07 update: N=3 runbook prepared at
    `outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3_runbook.md`;
    not run because ROS master was unavailable in this Codex turn.
- [x] Run the approved N=3 repeatability runbook after ROS restart with
  stop-on-first-failure and post-run recovery.
  - 2026-05-07 result: stopped at cycle 1; cycle 0 passed, cycle 1 failed,
    cycle 2 not run. Partial summary:
    `outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/partial_summary_after_stop.json`.
    Recovery return and strict gate passed.
- [ ] Do not run another live smoke immediately after the failed N=3 attempt.
  First inspect cycle 1 JSON artifacts and compare cycle 0/cycle 1 read-only,
  or return to offline-only model diagnostics.
- [x] Complete the combined read-only N=3 cycle 0/1 live-artifact comparison
  and offline-only model diagnostic.
  - 2026-05-07 result: `policy_output_instability_detected=false`,
    `geometry_ood_detected=false`, `clip_limited_motion_detected=true`,
    `insufficient_motion_detected=true`,
    `target_drift_boundary_detected=true`.
    Report:
    `outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/read_only_failure_diagnosis.md`.
- [ ] Before any further live rerun, do offline-only sensitivity planning for
  fixed tick budget and/or clip limits using existing traces; keep DP/FM
  offline-only and do not run another live smoke immediately.
- [x] Complete offline-only tick-budget / clip-limit sensitivity projection on
  the failed N=3 cycle 1 trace.
  - 2026-05-07 result: current `0.005 m` clip needs about 9 ticks for the
    reduction threshold in cycle 1; projected `0.0075 m` clip with 6 ticks or
    `0.010 m` clip with 5 ticks can pass the distance gate in the replay-style
    estimate, but target drift remains unresolved. Report:
    `outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/offline_tick_clip_sensitivity.md`.
- [ ] Do not approve another live rerun from the projection alone. If a future
  rerun is proposed, change only one variable at a time and require a separate
  runbook/review.
- [x] Prepare the single-variable candidate review and default-not-run runbook.
  - 2026-05-07 result: selected `max_control_ticks: 5 -> 9` as the first
    candidate because it keeps per-command clip and joint limits unchanged.
    Artifacts:
    `outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_single_variable_candidate_review.md`,
    `outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke_runbook.md`.
- [x] Execute the tick9 single-smoke runbook only after separate explicit
  approval, then document the result as N=1 tick-budget sensitivity only.
  - 2026-05-07 result: tick9 single smoke passed its arm-only threshold with
    `gate_distance_reduction=0.038791103596488574`,
    `post_gate_initial_distance=0.06884095013771155`,
    `gripper_commands_sent=false`, and `learned_rollout_success_claimed=false`.
    Recovery return reached reference; strict gate passed on the second
    read-only retry. Outcome:
    `outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke/outcome.md`.
- [ ] Do not run another learned live smoke from the tick9 result alone. Treat
  it as one successful N=1 tick-budget sensitivity smoke only; it does not
  resolve N=3 repeatability and does not approve DP/FM live.
- [x] Run read-only tick9-vs-N3 tick5 comparison before considering any new
  live rerun.
  - 2026-05-07 result: tick9 improvement is best explained by both extra tick
    budget and cleaner target drift, not policy-output shift. The clipped
    action mean delta from failed cycle 1 to tick9 was only
    `5.2579650057143435e-05`; tick9 extra ticks contributed
    `0.015276998081651047` additional distance reduction, while target drift
    improved from `0.01016428396425749` to `7.858877409400243e-05`. Report:
    `outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_vs_n3_tick5_comparison.md`.
- [ ] Keep DP/FM live blocked and do not approve another BC live run from this
  comparison alone. If continuing, prefer offline-only DP/FM comparison under
  the same base-relative safe-norm setup, or design a separate target-drift
  stabilization/readiness gate.
- [x] Design a separate target-drift stabilization/readiness gate from existing
  read-only gate artifacts.
  - 2026-05-07 result: recommended `two_fresh_gates_with_clean_target_drift`
    before any separately approved future live smoke: two consecutive gates
    with `initial_distance<=0.115`, `target_base_drift<=0.001`,
    `relative_base_drift<=0.001`, `joint_l2<=0.02`, `joint_max_abs<=0.01`,
    `eef_base_drift<=0.02`, wait/retry only. This readiness review does not
    approve live. Report:
    `outputs/logs/b8_rollout_planning/b8_target_drift_readiness_gate_review.md`.
- [ ] Do not reset target or run another live smoke from readiness analysis
  alone. Resetting target after repeated clean-gate failure requires separate
  explicit approval and a new runbook.
- [x] Advance DP/FM with a post-tick9 offline-only gate under the same
  base-relative safe-norm setup.
  - 2026-05-07 result: DP/FM may continue offline-only. BC remains the live
    reference; DP30 is the best non-BC candidate but is still `2.01%` worse
    than BC by action MSE. DP/FM live and full training-as-success remain
    blocked. Report:
    `outputs/logs/b8_primary30_training_planning/dp_fm_post_tick9_offline_gate.md`.
- [ ] If continuing DP/FM, do offline-only diagnostics only: seed/budget review,
  action-scale review, validation-window error review, and deterministic
  sampling review. Do not run DP/FM live from the offline gate alone.
- [x] Run DP/FM validation-window and action-scale diagnostics offline.
  - 2026-05-07 result: BC remains reference; DP30 is the closest non-BC model
    but remains `2.01%` worse by action MSE. FM10 has higher max-window error.
    Action scale is stable and no live/training was run. Report:
    `outputs/logs/b8_primary30_training_planning/dp_fm_validation_window_diagnostics.md`.
- [ ] If continuing DP/FM, prefer offline-only seed/budget or architecture
  diagnostics for DP30 under the same base-relative safe-norm setup. Do not
  promote DP/FM to live until it beats BC offline and live readiness is
  separately re-approved.
- [x] Complete DP offline objective/selection ablations under the same
  base-relative safe-norm h8 xyz setup.
  - 2026-05-07 result: action-space checkpoint selection and x0 auxiliary loss
    did not beat baseline DP seed86 and did not beat BC. A per-dimension
    x0-aux variant `[0.25, 1.0, 1.0]` was slightly better than scalar x0-aux
    but still worse than baseline DP and BC. Latest report:
    `outputs/logs/b8_primary30_training_planning/dp_x0_aux_outcome.md`.
- [ ] Keep DP/FM live blocked. If continuing DP/FM, do offline-only objective
  design review only; do not start live execution or claim learned rollout
  success from offline metrics.
- [x] Generate final-presentation-ready DP/FM offline result package.
  - 2026-05-07 result: FM action-selected `best_action.pt` achieved the best
    offline validation action MSE (`3.0398447847801435e-07`, `0.88%` lower
    than BC); DP seed86 remained the best DP candidate but was `1.37%` worse
    than BC. Artifacts:
    `outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_results.md`
    and
    `outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_slide_notes.md`.
- [ ] Do not convert the presentation-ready offline FM result into DP/FM live
  execution without a separate robustness check across seeds/folds and a
  separate live readiness approval.
- [x] Prepare tuned scripted reaching behavior before collecting a new B8'
  smoke set.
- [x] Runtime-check tuned v1 and tuned v2 smoke episodes.
- [x] Run read-only tuned v2 quality, direction, and command-to-motion
  diagnostics.
- [x] Inspect expert/IK command rule and target/base geometry before collecting
  more B8' data.
- [x] Inspect MoveIt/SRDF virtual-joint and planning-frame assumptions for the
  missing `world -> rexrov/base_link` TF connection.
- [x] Run package-local `world_base_tf_bridge.launch` and verify
  `world -> rexrov/base_link` and `world -> oberon7_l/end_effector` TF
  connectivity before collecting more B8' data.
- [x] Collect exactly one short B8' frame-fix validation episode with the TF
  bridge running, then validate and rerun offline quality/command-to-motion
  diagnostics before any 5-episode collection.
- [x] Run read-only direction diagnostics on the single TF-bridge frame-fix
  episode before changing expert parameters or collecting another episode.
- [x] Inspect base-relative target update timing/jitter before collecting
  another episode; target base-frame jumps currently dominate EEF motion.
- [x] Run exactly one B8' TF-bridge + 30 Hz target-updater validation episode,
  then validate and rerun offline quality/direction diagnostics.
- [x] Run read-only target30 command-to-motion diagnostic and inspect target_base
  net/max-step before collecting or tuning further.
- [x] Inspect target30 command-motion markdown per-lag table; if lag-2 remains
  dominant, prepare one bounded horizon/state-duration tuning check only.
- [x] Run exactly one tuned v3 horizon/state-duration validation episode and
  rerun validation plus quality/direction/command-motion diagnostics.
- [x] Inspect tuned v3 quality/direction markdown to determine whether the
  below-threshold sample was transient and whether target_base max-step stayed
  bounded before collecting any repeatability episodes.
- [x] Run a read-only per-sample NPZ trace check for tuned v3 to count
  below-threshold samples and identify target_base step spikes.
- [x] Inspect/fix package-local base-relative target updater behavior to reduce
  target_base step spikes before any repeatability collection.
- [x] Run exactly one tuned v3 cached-odom target-updater validation episode and
  rerun validation, quality, direction, and command-motion diagnostics.
- [x] Run read-only per-sample trace on the tuned v3 cached-odom episode before
  any further code/config changes.
- [x] Compare recomputed base-frame distance with stored relative_target_to_eef
  for tuned v3 cached-odom to separate real geometry from recorder sync artifact.
- [x] Add a package-local recorder option for B8' v3 to record base and target
  geometry from the same `/gazebo/model_states` source.
- [x] Run exactly one tuned v3 model-states-base validation episode and rerun
  validation plus quality/direction/command-motion diagnostics.
- [x] Run read-only per-sample trace and command-motion markdown inspection for
  the tuned v3 model-states-base episode.
- [x] Run read-only action saturation and lag-compensated progress analysis for
  the tuned v3 model-states-base episode.
- [x] Run read-only active-joint per-step saturation analysis for the tuned v3
  model-states-base episode.
- [x] Attempt exactly one bounded parameter-only tuned v3 smoke with
  `max_linear_step=0.015` and `max_joint_delta=0.010`; result was inconclusive
  because the B8 v3 wrapper did not pass through the override.
- [x] Expose `max_linear_step` and `max_joint_delta` in
  `b8_reaching_tuned_v3_episode.launch`.
- [x] Re-run exactly one bounded parameter-only tuned v3 smoke with the fixed
  wrapper, `max_linear_step=0.015`, and `max_joint_delta=0.010`.
- [x] Expose `time_from_start_sec` in `b8_reaching_tuned_v3_episode.launch`.
- [x] Run exactly one timing-only tuned v3 smoke with `max_linear_step=0.010`,
  `max_joint_delta=0.010`, and `time_from_start_sec=0.5`.
- [x] Run read-only per-sample timing05 trace diagnostics before collecting any
  more B8' episodes.
- [x] Run read-only active-joint per-step saturation diagnostics on timing05 to
  explain the large reported `max_active_left_joint_delta`.
- [x] Run read-only timing05 source-synchronization diagnostics comparing base
  world step, target world step, base yaw step, and target-in-base step around
  the target-base jumps.
- [x] Align the package-local base-relative target updater with recorder base
  pose source when `prefer_model_states_base_pose=true`.
- [x] Run exactly one source-aligned B8' smoke after the helper fix with
  `max_linear_step=0.010`, `max_joint_delta=0.010`, and
  `time_from_start_sec=1.0`.
- [x] Convert package-local `cylinder_target` into a static visual marker to
  remove target physical/contact dynamics from B8' reaching diagnostics.
- [x] Run exactly one source-aligned static-marker B8' smoke with
  `max_linear_step=0.010`, `max_joint_delta=0.010`, and
  `time_from_start_sec=1.0`.
- [x] Run read-only command-to-motion diagnostics on the static-marker NPZ.
- [x] Inspect the scripted expert log around MoveIt error code `-31`.
- [x] Run read-only static-marker per-sample action/motion diagnostics to
  explain poor action-to-EEF alignment after the IK crash.
- [x] Add package-local IK failure context logging to
  `arm_command_converter.py`.
- [x] Run exactly one static-marker IK-context smoke with the same conservative
  parameters and inspect the detailed IK failure log.
- [x] Run read-only validation and quality diagnostics on the IK-context NPZ.
- [x] Run read-only command-motion diagnostics on the IK-context NPZ.
- [x] Run read-only source-sync diagnostics on the IK-context NPZ.
- [x] Inspect saved success metadata synchronization for the IK-context NPZ
  after source-sync is confirmed clean.
- [x] Patch recorder saved success synchronization for arm-only reaching /
  pregrasp episodes.
- [x] Run exactly one short smoke to validate that the fixed recorder saves
  `success=True` when final recorded distance is below threshold.
- [x] Run B8' repeatability smoke: 5 short real non-fallback arm-only
  reaching/pre-grasp episodes, with validation, source-sync, quality, and
  command-motion diagnostics.
- [x] Plan the next deliberately small real non-fallback arm-only data
  collection batch using the B8' repeatability smoke gates.
- [x] Run B8' small debug batch: 10 short real non-fallback arm-only
  reaching/pre-grasp episodes, no training, no learned rollout, no gripper.
- [x] Inspect why B8' small debug batch command-to-motion quality degraded in
  tail episodes 0007-0009 before collecting more data.
- [x] Add a read-only B8' initial-state gate script for active-left joint,
  EEF/base pose, relative target/EEF, and initial-distance checks.
- [x] Run the read-only B8' initial-state gate in live runtime with
  `--skip-target-checks`; startup active-left joint and EEF/base pose passed.
- [x] Add a target-only B8' gate probe launch that spawns/updates
  `cylinder_target_gate_probe` without recorder, expert, arm command, or
  gripper command.
- [x] Run the target-aware B8' initial-state gate with
  `cylinder_target_gate_probe`; startup target-relative initial geometry
  passed.
- [x] Run a short read-only repeated target-aware gate stability check with no
  arm command before any arm-command verification.
- [x] Run exactly one short gated arm-only verification episode only if
  explicitly approved, then rerun target-aware gate and offline diagnostics.
- [x] Define the minimum reset/settle/reinitialization strategy and add a
  bounded return-to-reference active-left joint command tool.
- [x] Runtime-test bounded return-to-reference once, then rerun target-aware
  gate before any additional episode.
- [ ] Run exactly one short gated arm-only verification episode after
  return-to-reference + target-aware gate, then run validator and
  quality/command-motion diagnostics.
  - 2026-05-05 attempt `b8_return_gated_arm_verify_1_0000` did not satisfy
    this item because the launch command used default
    `target_directed_reaching=false`, default gripper/lift-inclusive
    `state_sequence`, and relative `output_dir`.
  - 2026-05-05 corrected attempt `b8_return_gated_arm_verify_2_0000`
    satisfied this item at single-cycle smoke level:
    validator PASS, success=True, final_distance=0.08215466060136162,
    allow_nominal_state_fallback=false, gripper disabled. Command-motion
    remained weak, so do not expand collection yet.
- [ ] Rerun return-to-reference and target-aware gate after
  `b8_return_gated_arm_verify_2_0000`; use it to confirm that the post-episode
  reached state can be reset again before any further episode.
  - 2026-05-05 result: return succeeded, but target-aware gate failed due to
    target/base relative drift (`relative_base_drift=0.01695805312367644`),
    not due to arm joint reset.
- [ ] Run a short read-only target/base stability check before any further
  arm episode; decide whether the target probe must be reinitialized between
  cycles.
  - 2026-05-05 restarted-runtime check: first two target-aware gates failed
    with `relative_base_drift≈0.02327`, third gate passed with
    `relative_base_drift=5.5529932828080466e-06`. Treat this as target probe
    startup/settle transient; require a fresh target-aware gate pass before
    any next episode.
- [ ] Before any next arm-only episode, require one fresh target-aware gate
  pass after settle; prefer two consecutive passes 5 s apart.
  - 2026-05-05 result: two consecutive target-aware gates passed after settle
    (`relative_base_drift=3.503815165242792e-05` and
    `4.5012944528958283e-05`). Target/base settle gate is smoke-level resolved.
- [ ] Enforce a minimum per-episode reset/settle gate for active-left
  joint initial configuration, EEF base pose, and previous command transients.
- [x] Fix target-directed action-frame mismatch in the scripted expert.
  - 2026-05-05: `b8_return_gated_arm_verify_3_0000` exposed IK -31 and weak
    command-motion because target-directed base_link deltas were interpreted as
    planning_frame deltas.
  - Patched `expert_policy.py` so the arm converter uses
    `target_directed_action_frame` when `target_directed_reaching=true`.
  - `b8_return_gated_arm_verify_4_0000` validated the fix at single-episode
    smoke level: runtime `action_frame=base_link`, validator PASS,
    success=True, final_distance=0.05744791236250198.
- [ ] If explicitly continuing, run only a tiny post-fix
  return->gate->episode repeatability check; do not expand to 10+ episodes
  yet because command-motion remains weaker than the earlier best smoke.
  - 2026-05-05 completed tiny check:
    `data/raw/b8_postfix_repeatability_2/`, validator_pass_count=2/2,
    success_count=2/2, mean_final_distance=0.057304824535672975,
    mean_best_action_to_eef_cosine=0.5379418351868376,
    mean_best_realized_gain_along_action=0.17491140517275186.
    This is smoke-level repeatability, not training readiness.
- [ ] Tune or gate scripted reaching behavior, then rerun only a short
  repeatability/debug check if explicitly approved.
- [x] Plan a small post-fix debug batch with per-episode
  return/gate/diagnostics.
  - Default N=3, hard max N=5.
  - Do not execute until explicitly approved.
  - Stop on return/gate failure, IK -31, validator failure, metadata mismatch,
    target/base jump, or command-motion collapse.
- [ ] If explicitly approved, execute the small post-fix debug batch plan
  using `data/raw/b8_postfix_debug_3` and
  `outputs/logs/b8_postfix_debug_3*`.
  - 2026-05-05 attempt stopped before collection at cycle 0 gate:
    return succeeded, but target-aware gate and one 5 s retry both failed
    because `initial_distance` remained just above `0.115 m`
    (`0.1159362425810477`, retry `0.11528983854046555`). No episode was
    collected.
- [ ] Diagnose target-aware gate boundary behavior before retrying the small
  debug batch: either wait/reinitialize target probe or explicitly decide
  whether the `initial_distance_max=0.115 m` gate should remain unchanged.
  - Next minimum check should be read-only repeated target-aware gates from the
    current runtime. Do not collect or command the arm until the gate boundary
    behavior is understood.
  - 2026-05-05 gate boundary probe: 5 read-only gates, 3 pass / 2 fail.
    Failures were caused only by `initial_distance` slightly exceeding
    `0.115 m`; `relative_base_drift` stayed below threshold for all checks.
    Next: inspect target probe/base-relative updater behavior read-only.
  - 2026-05-05 ROS graph spot check showed one visible target updater:
    `/b8_target_gate_base_relative_target`; no duplicate target updater was
    observed. Raw `/gazebo/model_states` grep was inconclusive because names
    and poses are parallel arrays.
  - 2026-05-05 indexed target pose probe showed
    `cylinder_target_gate_probe` moving in world from approximately
    `[24.729, -13.440, -99.713]` to `[25.758, -13.291, -99.713]` over 10
    samples. The follow-up target-aware gate passed with
    `initial_distance=0.10771781639816572`,
    `relative_base_drift=1.5569323561687856e-05`, and
    `target_base_drift=8.595952887736536e-05`.
    This confirms the target can be clean in base frame, but does not yet
    explain earlier intermittent gate-boundary failures.
- [ ] Run one read-only indexed base+target relative-motion probe: print
  indexed `rexrov` and `cylinder_target_gate_probe` world poses from the same
  `/gazebo/model_states` messages, then compute target-minus-base displacement
  over 10-20 samples. Do not collect or command the arm.
  - 2026-05-05 result: 20 synchronized indexed samples showed
    `target_in_base_range_norm=0.007246601027065321`, below the existing
    `relative_base_drift_threshold=0.01 m`. This supports smoke-level
    resolution of target/base sync. The remaining blocker is the strict
    `initial_distance_max=0.115 m` gate policy, which is only about 7.3 mm
    above the nominal reference distance.
- [ ] Before retrying `b8_postfix_debug_3`, choose the gate policy explicitly:
  either keep `initial_distance_max=0.115 m` and require wait/retry until fresh
  gates pass, or widen only the initial-distance gate slightly while keeping
  `relative_base_drift_threshold=0.01 m`, non-fallback recording, gripper
  disabled, and per-episode return/gate/diagnostics.
  - 2026-05-05 selected scheme 1 and implemented
    `scripts/run_b8_postfix_debug_batch_conservative.py`. It keeps
    `initial_distance_max=0.115 m`, runs per-episode
    return -> wait/retry gate -> one arm-only episode -> validator, and stops
    on the first return/gate/collect/validation problem. No collection was run
    during implementation.
- [ ] If explicitly approved, run
  `run_b8_postfix_debug_batch_conservative.py --episode-count 3` with the four
  base runtime launches plus `b8_target_gate_probe.launch` already running.
  Review its manifest and summary before any further collection.
  - 2026-05-05 result: helper stopped before collection at episode 0000.
    Return passed with `reached=true`, `commands_sent=0`, and no gripper
    command. Six gate attempts all failed because
    `relative_base_drift≈0.02326-0.02328 m` while
    `initial_distance≈0.11029-0.11040 m` remained within
    `initial_distance_max=0.115 m`. No `.npz` was written.
- [ ] Stop/restart only `b8_target_gate_probe.launch`, then run two fresh
  target-aware gates 5 s apart. Retry the conservative helper only if both
  gates pass.
  - 2026-05-05 result: restart was insufficient because
    `spawn_b8_target_gate_probe` failed with `entity already exists`. Two
    fresh gates still failed with `relative_base_drift≈0.02326-0.02327 m`.
    Added `scripts/reset_b8_target_gate_probe.py` to delete only the stale gate
    target before relaunching the probe.
- [ ] Stop `b8_target_gate_probe.launch`, run `reset_b8_target_gate_probe.py`,
  restart `b8_target_gate_probe.launch`, then run two fresh target-aware gates.
  Retry the conservative helper only if both gates pass.
  - 2026-05-05 result: reset passed, clean respawn succeeded, and two fresh
    gates passed. Gate metrics:
    `initial_distance=[0.10479344544370915, 0.1096170277494551]`,
    `relative_base_drift=[0.003596792375915908, 0.0021184551807263505]`.
    Target reset/gate precondition is smoke-level resolved.
- [ ] Rerun `run_b8_postfix_debug_batch_conservative.py --episode-count 3`
  with the clean target probe running. Review manifest and summary before any
  further collection.
  - 2026-05-05 result: 3 episodes were collected and validated. Helper stopped
    only at summary because `summarize_b8_repeatability_smoke.py` was not
    executable via `rosrun`; after fixing the diagnostic install/execution path,
    manual summary rerun passed with `validator_pass_count=3/3`,
    `success_count=3/3`, `mean_final_distance=0.04966386411855266`,
    `max_target_step_base=0.007595107419430765`, and
    `mean_best_action_to_eef_cosine=0.7134615751223703`.
- [ ] Decide the next B8' debug step explicitly: either one more small
  3-5 episode confirmation with the same reset/gate policy, or a controlled
  10-episode post-fix debug batch. Do not train yet.
  - 2026-05-05 selected controlled 10-episode post-fix debug batch.
    Helper was extended to allow `--episode-count 10` and per-step timeouts
    were added. First attempt stopped before collection because ROS master /
    runtime became unavailable during the first return step. No `.npz` was
    written.
- [ ] Restart the required runtime stack, reset/respawn the target probe, run
  two fresh target-aware gates, then retry the controlled 10-episode helper:
  `run_b8_postfix_debug_batch_conservative.py --episode-count 10 --episode-prefix b8_postfix_debug_10 ...`.
  - 2026-05-06 result: runtime restarted, but the two pre-batch gates failed
    with `relative_base_drift≈0.02325-0.02328 m`; helper then stopped because
    `data/raw/b8_postfix_debug_10/b8_postfix_debug_10_0000.npz` already
    existed. Existing `b8_postfix_debug_10` contains partial prior files
    (`0000` T=22, `0001` T=22, `0002` T=6), so it should not be used as the
    clean 10-episode batch.
- [ ] Stop `b8_target_gate_probe.launch`, run `reset_b8_target_gate_probe.py
  --ignore-missing`, restart `b8_target_gate_probe.launch`, require two fresh
  passing gates, then run the controlled helper with a clean output/prefix such
  as `b8_postfix_debug_10_clean`.
- [ ] Only after a real non-fallback arm-only dataset is deliberately collected
  and reviewed, retrain BC / Diffusion Policy / Flow Matching Policy.
- [ ] Evaluate real arm-only rollout with reaching metrics only.

Current B8' quality-review decision:

```text
B8' repeatability smoke is resolved at the 5-episode smoke level:
validator_pass_count=5/5, success_count=5/5, all required metadata is
consistent, and target/base source-sync has no large target-step indices.

This is still arm-only reaching/pre-grasp smoke evidence. It is not grasping,
not a learned policy rollout, and not training evidence.

Do not expand directly to 20/50/100 episodes.
Do not train BC / DP / FM yet.

The next action should be a small, deliberate real non-fallback arm-only
collection plan using the same validation and quality gates.
```

Latest B8' small debug batch decision:

```text
B8' small debug batch collected 10 real non-fallback arm-only reaching episodes
with odom-source base recording:

validator_pass_count=10/10
success_count=7/10
reaching_success_rate=0.7
all_required_metadata_ok=true
all_success_metadata_consistent=true
max_target_step_base=0.02330097538679025
large_target_step_indices=[] for all episodes

The batch did not pass the proposed quality gate of success_count / N >= 0.8.
Episodes 0007-0009 failed consecutively, and command-motion diagnostics
recommended not collecting more until the command-to-motion path is explained.

Do not train BC / DP / FM.
Do not run learned rollout.
Do not expand to 20/50/100 episodes.
Do not treat this as final training data.
```

Latest B8' failure-analysis decision:

```text
B8' debug batch failure analysis was completed offline over the existing
data/raw/b8_reaching_debug_10 episodes only.

Generated artifacts:
outputs/logs/b8_reaching_debug_10_failure_analysis/

Main finding:
- failed episodes 0007-0009 did not start farther away from the target;
- scripted actions remained target-aligned;
- command-to-motion alignment collapsed in the failed tail;
- active-left joint initial configuration drift accumulated across episodes;
- target/base source-sync and episode duration are less likely primary causes.

Do not collect more B8' data until reset/settle and command-to-motion behavior
are addressed.
Do not train BC / DP / FM.
Do not run learned rollout.
Do not handle gripper.
```

Latest B8' initial-state gate preparation:

```text
Added scripts/check_b8_initial_state_gate.py.

This is a read-only gate:
- reads /joint_states, /rexrov/pose_gt, /gazebo/model_states, and TF;
- compares live initial state to a successful reference NPZ;
- sends no arm command and no gripper command;
- exits nonzero if initial joint/EEF/relative/distance gates fail.

The blocker is still not resolved until this gate or an equivalent reset/settle
mechanism is verified in runtime and followed by only a short approved
verification check.

Runtime skip-target gate result:
- `passed=true`
- `joint_l2_drift=0.00015674238939907846`
- `joint_max_abs_drift=0.00010077841280065059`
- `eef_base_drift=0.00008922043640714035`
- no arm command and no gripper command were sent.

This rules out bad clean-start joint/EEF initial state, but it does not verify
target-relative state or post-command repeatability.

Added `launch/b8_target_gate_probe.launch` so the target-aware gate can be run
without starting `collect_episode.launch`, recorder, expert, arm command, or
gripper command.

Runtime target-aware gate result:
- `passed=true` twice
- `target_checks_skipped=false`
- `joint_l2_drift=0.006599956530879626`
- `joint_max_abs_drift=0.006339712261209662`
- `eef_base_drift=0.0011713350520162551`
- `target_base_drift=0.0011803381838364844`
- `relative_base_drift=0.000038338634031170594`
- `initial_distance=0.10771198633079769`

This smoke-resolves startup initial-condition gating, but not post-command
command-to-motion degradation.

Runtime repeated target-aware gate result:
- `passes=5/5`
- no arm command and no gripper command were sent;
- `relative_base_drift` stayed between about `0.0000453` and `0.004136` m;
- `initial_distance` stayed between about `0.103944` and `0.110010` m.

This smoke-resolves passive target-aware initial-condition stability. The
remaining blocker is post-command repeatability / command-to-motion
degradation.

One gated arm-only verification result:
- `validator=PASS`
- `success=true`
- `recorded_success_distance_m=0.045301559855776316`
- `initial_distance=0.10625611763364251`
- `final_distance=0.045301559855776316`
- `distance_reduction=0.060954557777866195`
- `mean_best_action_to_eef_cosine=0.8718392906129798`
- `mean_best_realized_gain_along_action=0.24521231853273232`
- post-gate failed because the arm remained in the reached/pregrasp
  configuration:
  `relative_base_drift=0.07180542804879099`,
  `initial_distance=0.04013113557371512`.

This smoke-resolves exactly one gated arm-only verification episode. The next
blocker is reset/settle/reinitialization before any multi-episode collection.

Reset/settle strategy:
- selected first strategy: bounded return-to-reference active-left joint
  command, followed by target-aware gate;
- added `scripts/return_left_arm_to_reference.py`;
- dry-run from post-command state sent no command and reported
  `joint_l2_error=0.11564320348459194`,
  `joint_max_abs_error=0.08137583509102786`;
- next runtime check is one live return command followed by target-aware gate,
  not collection expansion and not training.
```

Historical B8' quality-review notes:

```text
Tuned v3 one-episode smoke crossed the 0.10 m reaching threshold once and is
smoke-level progress, but final distance remained above threshold and
`success=False`.

Do not expand tuned v3 collection yet.
Do not expand to 20 episodes.
Do not train BC / DP / FM.

The stored/recomputed distance comparison matched exactly, which rules out a
saved-field arithmetic mismatch but does not rule out recorder source
synchronization. `recorder.py` derives `relative_target_to_eef` directly from
the saved world `target_pose` and `eef_pose`, while the cached-odom episode used
odom for base and `/gazebo/model_states` for target.

The tuned v3 model-states-base validation episode produced valid non-fallback
metadata and improved action-to-motion alignment, but did not reach the
`0.10 m` threshold:

- `episodes_below_threshold=0`
- `initial_distance=0.128423 m`
- `min_distance=0.120908 m`
- `final_distance=0.131432 m`
- `mean_best_action_to_eef_cosine=0.872771`
- `mean_best_lag_steps=2.0`

The next minimum check is read-only per-sample trace and command-motion
markdown inspection for this exact episode. Do not collect repeatability
episodes or train until target-base step size, EEF step size, and lag behavior
are reviewed.

Latest per-sample review:

- `below_count=0`
- `min_distance=0.120908 m`
- `final_distance=0.131432 m`
- `max_target_step=0.016551 m`
- `max_eef_step=0.007806 m`
- `best lag steps=2`
- `best distance decreasing ratio=0.368421`

The target-base step spike is reduced. The next minimum check is read-only
action saturation and lag-compensated progress analysis for the same NPZ.

Latest action saturation review:

- `max_linear_step=0.01`
- `clip_component_fraction=0.590909`
- `clip_sample_fraction=0.954545`
- `lag_2_mean_motion_toward_target=0.002913 m/sample`
- `lag_2_distance_decrease_ratio=0.388889`

The action is saturated, but realized EEF progress is still small and
inconsistent. The next minimum check is read-only active-joint per-step
saturation analysis on the same NPZ before changing any runtime parameter.

Latest active-joint saturation review:

- `max_joint_delta=0.01`
- `overall_abs_dq_max=0.006445`
- `near_limit_component_fraction=0.0`
- `near_limit_step_fraction=0.0`

Active joint per-component steps are not saturated. The next minimum check is
exactly one bounded parameter-only smoke with `max_linear_step=0.015` and
`max_joint_delta=0.010`; do not collect multiple episodes or train.

Latest linear015 attempt:

- Command requested `max_linear_step=0.015`.
- Launch parameter summary still showed `max_linear_step=0.01`.
- The saved NPZ remained `success=False`, `episodes_below_threshold=0`, and
  `min_distance=0.120930 m`.
- The expert logged a later live `success=True`, but this happened after the
  recorder saved the NPZ and is not offline dataset evidence.

The B8 v3 wrapper now exposes and passes through `max_linear_step` and
`max_joint_delta`. Re-run exactly one linear015 smoke with the fixed wrapper.

Latest fixed linear015 review:

- Runtime parameter override worked: `max_linear_step=0.015`.
- `episodes_below_threshold=1`, but only one transient sample crossed the
  threshold.
- `min_distance=0.097646 m`, `final_distance=0.130182 m`,
  `mean_distance_reduction=-0.003620 m`.
- `mean_best_lag_steps=3.0`.
- `mean_best_realized_gain_along_action=0.099065`, worse than the prior
  model-states-base run.
- Joint step saturation remains absent.

Linear015 is smoke-level progress only and does not resolve B8'. The next
minimum check is one timing-only smoke with `max_linear_step=0.010`,
`max_joint_delta=0.010`, and `time_from_start_sec=0.5`.

Latest timing05 fresh-restart review:

- The base simulation, MoveIt context, left-arm controller loader, and
  world-base TF bridge were restarted before the episode.
- Runtime parameters were confirmed:
  `max_linear_step=0.010`, `max_joint_delta=0.010`,
  `time_from_start_sec=0.5`.
- `validation=PASS`, `T=22`, metadata `success=False`.
- `episodes_below_threshold=1`, but the threshold crossing was transient.
- `episodes_with_positive_distance_reduction=0`.
- `min_distance=0.095370 m`, `final_distance=0.137708 m`,
  `mean_distance_reduction=-0.010140 m`.
- `mean_best_action_to_eef_cosine=0.122900`.
- `mean_best_lag_steps=0.0`.
- `mean_best_realized_gain_along_action=0.032749`.
- `max_active_left_joint_delta=0.116602`.

Timing05 does not resolve B8'. Fresh restart rules out a simple long-running
simulation-session explanation. The next minimum checks are read-only
per-sample trace and active-joint per-step saturation diagnostics on the same
NPZ. Do not collect another episode or train.

Latest timing05 per-sample follow-up:

- `below_count=2`, `below_indices=[9, 14]`.
- `min_distance=0.095370 m`, `final_distance=0.137708 m`.
- `max_target_step_base=0.044189 m` at idx 9.
- Both below-threshold samples coincide with target-base jumps:
  - idx 9: `target_step_base=0.044189 m`, `eef_step_base=0.011241 m`;
  - idx 14: `target_step_base=0.040712 m`, `eef_step_base=0.010332 m`.
- Active-joint per-component steps are not saturated:
  `overall_abs_dq_max=0.008284 rad`,
  `near_limit_component_fraction=0.0`,
  `near_limit_step_fraction=0.0`.

The current minimum check is source synchronization on the same timing05 NPZ:
compare base world step, base yaw step, target world step, and target-in-base
step around the target-base jumps. Do not collect another episode before this
is understood.

Latest timing05 source-sync follow-up:

- `target_step_base` spikes reached `0.037657`, `0.033334`, `0.044189`,
  `0.038757`, `0.040712`, and `0.032510 m`.
- The threshold samples at idx 9 and idx 14 coincide with
  `target_step_base=0.044189 m` and `0.040712 m`.
- `target_step_world` and `base_step_world` were both large, with base moving
  about `0.15-0.16 m/sample` and yawing about `0.035-0.038 rad/sample`.

The immediate contamination source is now identified: the target updater was
using `/rexrov/pose_gt` while the recorder was using `/gazebo/model_states` for
base pose. The package-local base-relative target helper now supports
`/gazebo/model_states` as its base pose source when
`prefer_model_states_base_pose=true`, and `collect_episode.launch` passes the
flag through.

Next minimum check: run exactly one source-aligned B8' smoke with
`max_linear_step=0.010`, `max_joint_delta=0.010`, and
`time_from_start_sec=1.0`; then validate and rerun quality plus source-sync
diagnostics. Do not collect multiple episodes or train.

Latest source-aligned smoke review:

- Runtime confirmed
  `base_pose_source=gazebo_model_states`.
- `validation=PASS`, `T=22`, metadata `success=False`.
- `episodes_below_threshold=1`, but `episodes_with_positive_distance_reduction=0`.
- `min_distance=0.053267 m`, `final_distance=0.155115 m`,
  `mean_distance_reduction=-0.031033 m`.
- Early source-sync improved: before idx 12, `target_step_base` was mostly
  `<= 0.024 m`.
- Late source-sync still failed with target-in-base jumps:
  `0.076240`, `0.101956`, `0.061249`, `0.080733`, `0.106041`,
  and `0.103271 m`.

The remaining jump is no longer explained by base source mismatch. The target
SDF was still a dynamic colliding cylinder, which can contaminate arm-only
reaching geometry. The package-local target is now a static visual marker:
`static=true`, no inertial block, and no collision block. `xmllint` passed.

Next minimum check: run exactly one source-aligned static-marker B8' smoke with
`max_linear_step=0.010`, `max_joint_delta=0.010`, and
`time_from_start_sec=1.0`; then validate and rerun quality plus source-sync
diagnostics. Do not collect multiple episodes or train.

Latest static-marker source-aligned smoke review:

- Runtime confirmed `base_pose_source=gazebo_model_states`.
- Static visual marker target was used.
- `validation=PASS`, `T=22`, metadata `success=False`.
- Scripted expert failed mid-episode with MoveIt error code `-31`.
- `episodes_below_threshold=1`, `episodes_with_positive_distance_reduction=1`.
- `min_distance=0.096040 m`, `final_distance=0.097285 m`,
  `mean_distance_reduction=0.010668 m`.
- Source-sync contamination is much improved:
  `target_step_base max=0.011193 m`; prior `0.06-0.10 m` jumps are absent.

Target/source synchronization is smoke-level resolved, but B8' remains
unresolved because the scripted expert crashed with IK error `-31` and the
saved metadata is still `success=False`. The next minimum checks are read-only:
run command-to-motion diagnostics on the static-marker NPZ and inspect the
scripted expert log around the IK error. Do not collect another episode or
train yet.

Latest static-marker command/IK follow-up:

- Command-motion diagnostic reported
  `mean_best_action_to_eef_cosine=-0.001547`,
  `mean_best_lag_steps=1.0`, and
  `mean_best_realized_gain_along_action=0.055096`.
- Expert log shows the first `MOVE_TO_PREGRASP` command was published, then
  the scripted expert failed with MoveIt error code `-31`.

B8' remains unresolved. Geometry/source-sync is smoke-level resolved for one
static marker episode, but the command/IK path is now the active blocker. Next
minimum check is read-only per-sample action/motion diagnostics on the same
NPZ. Do not collect another episode or train.

Latest static-marker per-sample action/motion review:

- Action labels remain nonzero after the scripted expert crashes.
- `joint_step_norm` is nonzero only through idx 4 and is zero from idx 5 through
  idx 21.
- Distance stays near `0.096-0.097 m` for most saved samples.

The command-motion diagnostic is therefore contaminated by stale action labels
after the IK failure. The active blocker is now the MoveIt IK failure, not
target geometry. `arm_command_converter.py` now logs IK failure context
including group, IK link, target pose, and seed joints; `py_compile` passed.
Next minimum check is exactly one static-marker IK-context smoke with the same
parameters, followed by expert-log inspection. Do not collect multiple episodes
or train.

Latest IK-context static-marker runtime review:

- Multiple `MOVE_TO_PREGRASP` and `MOVE_TO_GRASP` arm commands were published.
- The instrumented run did not reproduce `IK failed` or `IK request failed`.
- The scripted expert finished cleanly with
  `success=True reason=reaching_success: distance 0.091776 below 0.100000`.
- The recorder saved the NPZ before the expert success line, so runtime success
  is not enough to mark B8' resolved.

Next minimum checks are read-only validation, reaching quality, source-sync,
and command-motion diagnostics on the single IK-context NPZ. Do not collect
more episodes or train before reviewing those outputs.

Latest IK-context saved-NPZ quality review:

- `validation=PASS`, `T=22`.
- Saved metadata still reports `success=False`.
- `episodes_below_threshold=1`.
- `episodes_with_positive_distance_reduction=1`.
- `min_distance=0.082842 m`.
- `final_distance=0.087695 m`.
- `mean_distance_reduction=0.020008 m`.

B8' is now smoke-level resolved for one saved non-fallback static-marker
reaching episode, with limitations. Do not expand collection or train: source
sync and command-motion diagnostics still need to be reviewed for this exact
NPZ, and saved success metadata synchronization remains unresolved.

Latest IK-context command-motion review:

- The per-sample trace shows joint motion through the saved episode rather than
  the stale-action-after-crash pattern seen in the prior static-marker run.
- `mean_best_action_to_eef_cosine=0.214153`.
- `mean_best_lag_steps=2.0`.
- `mean_best_realized_gain_along_action=0.156041`.
- The command-motion analyzer still recommends
  `do_not_collect_more_until_command_to_motion_path_is_explained`.

B8' remains smoke-level resolved only, not repeatability-collection ready. The
next minimum check is read-only source-sync diagnostics on the same
IK-context NPZ. If target-in-base geometry is clean, inspect saved success
metadata synchronization before any collection expansion.

Latest IK-context source-sync review:

- `min_distance=0.082842 m`.
- `final_distance=0.087695 m`.
- `max_target_step_base=0.012109 m`.
- `large_target_step_indices=[]`.

The current B8' blocker is smoke-level resolved for one saved non-fallback
static-marker arm-only reaching episode. It is not repeatability-collection
ready because saved `success=False` is inconsistent with distance-based
success, command-to-motion alignment remains mixed, and no repeatability
evidence exists. The next blocker-local task is to inspect/fix saved success
metadata synchronization before any new collection or training.

Latest saved-success synchronization fix:

- Root cause: recorder saved before the expert's final `success=True` message
  arrived, so saved metadata fell back to launch parameter `success=False`.
- Fix: for `reaching_success` and `pregrasp_success`, recorder now computes
  saved success from the final recorded `relative_target_to_eef` distance.
- Added metadata provenance fields:
  `success_source`, `recorded_success_distance_m`, and
  `recorded_success_distance_threshold_m`.
- `python3 -m py_compile recorder.py`: PASS.
- Existing IK-context final recorded distance is `0.087695 m`, so the fixed
  recorder would save `success=True` for that geometry.

Next minimum validation is exactly one short smoke to verify saved metadata.
Do not collect repeatability episodes or train yet.

Latest success-sync smoke validation:

- Episode:
  `data/raw/b8_reaching_smoke_tuned_v3_success_sync_check/b8_reaching_smoke_tuned_v3_success_sync_check_0000.npz`.
- Runtime expert finished with `success=True`, distance `0.035195 m`.
- `validate_episode.py`: PASS, `T=22`, `success=True`.
- Saved scalar and metadata both report `success=True`.
- `success_source=recorded_final_distance`.
- `recorded_success_distance_m=0.0404588355643862`.
- `recorded_success_distance_threshold_m=0.1`.

The current B8' blocker is smoke-level resolved, including saved success
metadata synchronization. This is not repeatability evidence and must not be
treated as grasp success or learned rollout success.
```

B8' episode requirements:

- `allow_nominal_state_fallback=false`
- `base_state_source=odom` or `base_state_source=gazebo_model_states`
- `joint_state_source=joint_states`
- `target_state_source=gazebo_model_states`
- `eef_pose`, `relative_target_to_eef`, and `action_ee_delta` available
- `gripper_enabled=false`
- `task_type=arm_only_reaching` or `pregrasp_positioning`
- `success_metric=reaching_success` or `pregrasp_success`
- `is_grasp_dataset=false`

Do not do for the current route:

- no gripper commands;
- no hand controller startup as a workaround;
- no grasp success or grasp success rate;
- no learned-policy rollout claim before rollout evaluation;
- no Stage 6 fallback data as real demonstration.

## Completed Work

Completed in stages 1-4:

- Re-read `./docs` and this package's `docs` before each stage.
- Inspected launch files for RexROV + dual Oberon7 startup paths.
- Confirmed runtime state topics and MoveIt group names.
- Confirmed left-arm and gripper joint names.
- Defined first-version state-based `.npz` schema.
- Added config files for data collection, topics, grasp task, and active-left joints.
- Implemented `.npz` episode recorder.
- Implemented episode validator.
- Generated and validated one short smoke-test episode.
- Implemented first scripted expert action-label policy.
- Added package-local `cylinder_target` SDF model and `collect_episode.launch`.
- Generated and validated one scripted expert smoke-test episode.
- Added Stage 6 batch collection and dataset summarization scripts.
- Generated a 5-episode Stage 6 smoke set.
- Generated a 20-episode Stage 6 debug set with 20 valid `.npz` episodes.
- Generated `dataset_summary.json`, `dataset_summary.md`, and a combined train/val split for the Stage 6 debug set.

Still open:

- Confirm left-arm command interface.
- Confirm gripper command interface.
- Expand target object launch/world wrapper beyond smoke-test spawn if needed.
- Add TF or MoveIt lookup for `eef_pose` and `relative_target_to_eef`.
- Convert scripted expert action labels into real controller commands after command topics are confirmed.
- Fix live runtime state collection before treating Stage 6 data as real demonstrations:
  - restore live `/joint_states` samples;
  - restore or replace `/rexrov/pose_gt`;
  - make target spawn stable;
  - remove nominal base/joint/target fallback from real data collection.

## Later Tasks

- B8' post-fix blocker status, 2026-05-06:
  - clean controlled 10-episode scripted arm-only debug batch
    `data/raw/b8_postfix_debug_10_clean/` passed smoke-level checks;
  - result is `10/10` validator pass and `10/10` reaching success with
    consistent metadata and no target/base large jumps;
  - keep `data/raw/b8_postfix_debug_10/` marked partial/contaminated;
  - do not train from this result yet without an explicit next-step approval;
  - keep return-to-reference, fresh target-aware gate, validation, and summary
    diagnostics for any further debug collection.
- B8' next approved direction, 2026-05-06:
  - [x] Update the conservative helper to allow the approved 20-episode
        controlled debug collection while keeping the hard upper bound at 20;
  - [x] Run a controlled 20-episode arm-only debug collection only after clean
        runtime, target reset/respawn, and fresh target-aware gates pass;
  - [ ] Use `data/raw/b8_controlled_debug_20/` and matching conservative +
        summary log directories;
  - [ ] Stop on first return/gate/collection/validation/summary problem;
  - [ ] If 20-episode batch passes, generate a read-only training-dataset
        candidate manifest/quality report before any training;
  - [ ] Continue to exclude partial/contaminated attempts and Stage 6 fallback
        data from real demonstration data.
  - [x] Resolve the new 20-episode precollection blocker: after
        return-to-reference, target-aware gate fails with about 6.7-7.3 cm
        target/relative drift even though arm return succeeds.
  - [x] Tighten `check_b8_initial_state_gate.py` default arm/eef thresholds so
        manual gates cannot pass from a post-command reached arm pose.
  - [ ] Before retrying 20 episodes, use this order: stop target probe, return
        arm to reference, delete/reset target probe, restart target probe, then
        require two fresh target-aware gates.
  - [x] Generate a read-only training-dataset candidate manifest/quality report
        for `b8_postfix_debug_10_clean`, `b8_controlled_debug_20`, and optional
        `b8_postfix_debug_3`; flag `b8_controlled_debug_20_0010` as an
        initial-distance boundary case.
  - [x] Review the primary 30-episode candidate pool and create training
        planning/config artifacts.
  - [x] Run BC sanity training on the B8' primary30 split and offline-evaluate
        the best checkpoint.
  - [x] Review BC sanity validation behavior before starting Diffusion Policy
        or Flow Matching Policy training.
  - [x] Prepare short DP/FM smoke configs on the B8' primary30 split without
        running them.
  - [x] Decide whether to run short DP/FM smoke training. Full DP/FM training
        remains blocked until smoke results are reviewed.
  - [x] Run short DP/FM smoke training and offline eval on the B8' primary30
        split.
  - [x] Review DP/FM smoke sampling quality, epoch budget, model settings, and
        training objectives before any full DP/FM training.
  - [ ] Keep DP/FM work offline-only until bounded ablations explain the poor
        sampled action MSE: deterministic/mean-style sampling checks,
        per-dimension action/objective review, shorter action horizon, and a
        small epoch-budget check.
  - [x] Complete DP/FM offline-only bounded ablations: zero-init sampling,
        per-dimension action/objective review, `action_horizon=8`, and
        `epochs=30`.
  - [x] Add an action-space-filtered or masked-objective DP/FM variant that
        removes inactive angular and gripper-like dimensions from the
        sampled-action objective before any larger training.
  - [x] Compare BC and FM h8 zero-init under the same active reaching
        action-space definition.
  - [x] Keep the next training check offline-only: run a small FM h8 xyz
        epoch-budget ablation or an additional deterministic direct-head
        baseline under the exact same `dx/dy/dz` action-space definition.
  - [x] Treat BC h8 xyz as the current best offline baseline; only continue
        FM offline if trying lower learning rate or early-stopped h8 xyz
        ablations.
  - [x] Generate a BC h8 xyz offline candidate report and mark it as a
        rollout-planning candidate, not rollout-ready success.
  - [x] Write a separate arm-only rollout safety/evaluation plan before any
        learned rollout command is run.
  - [x] Review or implement the BC h8 xyz arm-only rollout adapter in dry-run
        mode only. It must use 3-D `dx,dy,dz` action mapping, conservative
        clipping, abort checks, return/gate discipline, and no gripper/hand
        command path.
  - [ ] Rerun one live BC h8 xyz dry-run action-label check only after
        return-to-reference and two fresh target-aware gates pass. Keep
        `execute_actions=false`; inspect `abort_context` in the dry-run JSON
        before considering threshold changes or any live arm execution.
  - [x] Run a read-only BC h8 xyz dry-run distribution diagnostic comparing
        the live raw xyz / live observation scale against the B8 primary30
        training action and observation distribution.
  - [x] Run a read-only live-observation / normalized-policy-output diagnostic
        for BC h8 xyz before changing abort thresholds, retraining, or
        considering live learned arm execution.
  - [x] Run a read-only normalized-observation ablation for BC h8 xyz to
        isolate whether gripper-state OOD, absolute base-pose drift, or
        absolute target-pose drift drives the unsafe live `dx`.
  - [x] Run offline/read-only BC h8 xyz validation-set observation
        neutralization ablations before changing the dry-run adapter, changing
        thresholds, retraining, or considering live learned arm execution.
  - [x] Design an offline-only base-relative / arm-only observation variant and
        safe action normalization policy for near-constant clipped dimensions
        before retraining BC or comparing DP/FM again.
  - [x] Re-run BC sanity with the base-relative / arm-only observation and
        safe action normalization, then verify offline action scale before any
        DP/FM comparison.
  - [x] Implement a matching base-relative live dry-run adapter for the
        `b8_primary30_bc_h8_xyz_base_relative_safe_norm` checkpoint.
  - [x] Run one `execute_actions=false` base-relative BC h8 xyz live
        action-label check; confirm no abort, no control command, and no
        gripper command.
  - [x] Run DP/FM smoke comparisons only under the exact same base-relative
        observation and safe action normalization; exclude old absolute-pose
        checkpoints from the comparison.
  - [ ] If continuing DP/FM, keep it offline-only and use this same
        base-relative config family for small epoch-budget/sampling ablations.
  - [x] Run a small DP/FM epoch-budget ablation under the same base-relative
        safe-norm config family; keep BC as rollout-planning reference because
        DP30 still does not beat BC action MSE and FM30 worsens.
  - [x] Add a DP30 focused offline-only seed-ablation plan and evaluator under
        the same base-relative safe-norm config family.
  - [x] If explicitly approved as offline training, run only the prepared DP30
        seed85/seed86 commands, then evaluate with
        `analyze_b8_dp30_seed_ablation_validation.py`; do not start ROS or
        learned rollout.
  - [ ] Keep BC as the live reference because the best DP seed still does not
        beat BC validation action MSE.
  - [x] Run a DP/FM offline sampling sweep after DP seed ablation; confirm
        sampling steps do not close the BC gap.
  - [x] Run a read-only DP/FM training-loss versus action-MSE diagnostic;
        confirm denoising/flow loss alone is not sufficient for selection.
  - [ ] If continuing DP/FM, use offline architecture/objective diagnostics
        under the same base-relative safe-norm setup; do not tune live
        execution based on DP/FM yet.
  - [x] Run one bounded DP architecture ablation with seed86 and width128;
        confirm smaller hidden width does not beat width256 or BC.
  - [x] Run a DP objective timestep diagnostic; confirm epsilon loss and
        action-space reconstruction error are not aligned enough for model
        selection.
  - [x] Add and run a bounded DP action-space checkpoint-selection ablation;
        confirm `best_action.pt` does not beat baseline seed86 or BC on mean
        action MSE.
  - [ ] If continuing DP/FM, prefer offline objective/label diagnostics rather
        than smaller hidden-width ablations.
  - [ ] Do not start full DP/FM training unless a later offline-only ablation
        beats or materially complements the BC base-relative reference.
  - [x] Add and run a read-only rollout-readiness preflight over the
        base-relative BC dry-run, DP/FM offline comparison, epoch-budget
        ablation, and safety plan.
  - [ ] If learned execution is requested next, require explicit approval and
        first run return-to-reference plus two fresh target-aware gates; keep it
        tiny, arm-only, and gripper-disabled.
  - [x] Add and run a default-off IK command preview for the base-relative BC
        dry-run adapter; confirm it uses `convert()` only, does not publish arm
        command, and clips joint delta to `0.01 rad`.
  - [x] Replace the stale absolute-pose rollout safety-plan artifact with a
        base-relative safe-norm BC v2 plan, and make the rollout-readiness
        preflight default to that v2 plan.
  - [x] Generate a read-only tiny arm-only smoke checklist showing that the
        current base-relative adapter is still dry-run only and cannot execute
        learned actions.
  - [x] If execution is separately approved, implement and review a dedicated
        tiny active-left arm-only execution adapter; do not use the dry-run
        adapter with `execute_actions:=true`.
  - [x] Implement and statically review a dedicated tiny active-left arm-only
        BC base-relative execution-smoke adapter with dual opt-in flags and
        `max_control_ticks=3`.
  - [x] If a learned arm-only smoke is explicitly approved, first return to
        reference, require two fresh target-aware gates, then run exactly one
        tiny execution with no gripper/hand and immediate diagnostics.
  - [x] Summarize the first tiny learned arm-only smoke; mark the active-left
        command path as smoke-level resolved but do not claim arm-only reaching
        success because distance reduction was below `0.02 m`.
  - [x] Before any second learned smoke, return the arm to reference and run a
        fresh target-aware gate; do not proceed directly from the moved state.
  - [x] Review the first tiny-smoke summary and post-return gate before
        deciding whether to run a second tiny learned smoke, adjust the BC
        action horizon/tick budget, or keep further work offline-only.
  - [ ] If the user separately approves a second learned smoke, run only one
        controlled test with the same checkpoint/horizon/clip limits and
        `max_control_ticks=5`, after return-to-reference and two fresh gates.
  - [x] Prepare the second tiny-smoke runbook with the same checkpoint,
        horizon, and clip limits; only `max_control_ticks` changes from `3` to
        `5`.
  - [ ] If the second smoke aborts or does not improve monotonically, stop live
        learned execution and return to offline diagnostics.
  - [ ] Do not start longer/full DP/FM training until offline sampled action
        quality is credible relative to the BC sanity baseline.
  - [ ] Do not run learned rollout until after model training results are
        reviewed and a separate rollout-evaluation plan is approved.

- Implement IK waypoint or MoveIt-planning expert after execution mapping is confirmed.
- Use the Stage 6 fallback dataset only for loader/training-loop smoke tests.
- Implement BC dataset loader and sanity training. Completed in Stage 7 on the
  Stage 6 fallback debug dataset.
- Add Diffusion Policy with shared normalization. Completed in Stage 8 on the
  Stage 6 fallback debug dataset.
- Add Flow Matching Policy with shared normalization. Completed in Stage 9 on
  the Stage 6 fallback debug dataset.
- Add offline comparison summary across BC, Diffusion Policy, and Flow Matching
  Policy. Completed in Stage 11 with a BC/DP/FM table and DP/FM step ablation.
- Add rollout policy node. Completed in Stage 10 in safe action-label mode.
- Add real Gazebo rollout evaluation after command interfaces are confirmed.
- [x] Implement a shared BC / DP / FM live arm-only reaching protocol runner
      with return, strict fresh gate, dry-run/smoke, rollout, post-gate, and
      summary artifacts.
- [x] Run aggressive partial live evaluation attempts for BC / DP / FM without
      hand controller or gripper command.
- [x] Generate partial success-rate artifacts when equal-N comparison remained
      incomplete.
- [x] Do not report BC / DP / FM as a completed fair live comparison until an
      equal-N shared protocol finishes. Completed by v11 terminal-final-distance
      protocol with BC/DP/FM all 3/3.
- [x] Revise shared protocol/controller termination so
      threshold-reaching is detected before the next IK conversion attempt,
      without treating IK/controller failure as success.
- [ ] Reset/restart the target gate until strict fresh gate metrics return to
      `initial_distance <= 0.125 m` and `target_base_drift <= 0.02 m`.
- [ ] Rerun v8 success-criterion-guard protocol for all three methods from
      N=1 smoke to N=3 formal evaluation before considering N=5.
- [x] After user restarted launch 1-4, restart target gate and rerun v8.
- [x] Record v8/v9 after-restart partial artifacts instead of claiming a fair
      table.
- [x] Fix early-stop/summary alignment: log the terminal early-stop observation
      into rollout history and pass `pre_gate_1` initial distance into the
      early-stop guard before any further protocol rerun.
- [x] Implement early-stop terminal observation logging and `pre_gate_1`
      baseline override in the shared runner.
- [x] Fix summarizer compatibility with terminal observation rows that do not
      contain action vectors.
- [x] Rerun fixed v10/v10b N=3-entry protocol and record partial artifacts.
- [x] Decide the formal final-distance metric. v11 uses terminal early-stop
      observation and completed equal-N N=3 for BC/DP/FM.
- [x] Treat N=5/N=10 only as optional extensions unless all three methods
      complete the same larger N. v12b completed N=10 for BC/DP/FM, so the
      latest presentation-ready success-rate table is now N=10.
- [x] Preserve the interrupted first N=10 attempt as a failure artifact and do
      not mix it into the final table.
- Re-run data-volume ablation for 50, 100, and optionally 300 episodes after
  live non-fallback data collection is fixed.
- Re-run horizon ablation for `action_horizon=8` and `action_horizon=32` after
  retraining matching BC/DP/FM checkpoints.
- Check official Project DAVE ocean-current documentation before enabling
  disturbance ablations.
- Replace Stage 11 fallback-data conclusions with real rollout conclusions
  after `eef_pose`, action conversion, and controller execution are available.
- Keep `README.md` and `docs/FINAL_DEMO_SUMMARY.md` synchronized when the
  dataset, checkpoints, or rollout status changes. Initial versions were added
  in Stage 12.

## Non-Goals For Now

- No RGB/depth collection.
- No dual-arm coordination.
- No Ray/RLlib/PettingZoo dependency.
- No long training.
- No modifications to official DAVE/UUV/RexROV2 packages.
