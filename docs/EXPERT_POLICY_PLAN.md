# Expert Policy Plan

## Goal

Collect automated expert trajectories for the current first state-based
single-active-left arm-only reaching / pre-grasp demo.

Historical grasping expert notes below are retained as project history and
future-work context. The current B5d'/B8' route does not close the gripper and
does not claim grasp success.

## Current B5d' Arm-Only Expert Status

B5d' is debug-smoke minimal resolved:

- scripted expert publishes target-directed, clipped `action_ee_delta`;
- gripper command is disabled and ignored;
- converter uses the current route:

  ```text
  EE-delta -> IK/joint target -> /oberon7/arm_position_l/command
  ```

- the package-local MoveIt context wrapper provides semantic context for IK;
- repeated small `MOVE_TO_PREGRASP` commands were generated with bounded
  active-left joint motion;
- recorder wrote a non-fallback live-state `.npz` episode and validator passed.

Current success labels must be interpreted as `reaching_success` or
`pregrasp_success`, not `grasp_success`. `success=False` is expected for early
smoke episodes because gripper execution is disabled/blocked.

B8' next expert use:

- do not collect more episodes until the current 10-episode debug-batch tail
  failure is addressed;
- keep `enable_gripper_command=false`;
- keep hand controllers disabled;
- keep `target_directed_action_frame=base_link`;
- validate every episode and inspect distance metrics before training.

## B8' Debug Batch Failure Expert Update

Review date: 2026-05-05.

Offline analysis was run over:

```text
data/raw/b8_reaching_debug_10/
```

The first seven episodes succeeded and the last three failed. The important
expert-side comparison is:

```text
action_relative_cosine:
  success_mean: 0.897726
  failure_mean: 0.943494
best_action_to_eef_cosine:
  success_mean: 0.823278
  failure_mean: -0.071778
best_realized_gain_along_action:
  success_mean: 0.209131
  failure_mean: -0.021860
joint_initial_drift_from_ep0:
  success_mean: 0.304920
  failure_mean: 0.806195
```

Expert interpretation:

- The target-directed action generator is still pointing in the expected
  target direction in failed episodes.
- The failure is more likely in repeated-episode reset/settle state,
  IK/controller response, or action-to-motion mapping than in the immediate
  action direction rule.
- Initial active-left joint configuration drift is large enough to treat reset
  or accumulation as the next expert blocker.
- Target/base sync is less likely as the primary cause for 0007-0009 because
  failed `target_base_max_step` stayed below the large-jump threshold.

Recommended minimum expert/debug changes before any more collection:

- Add or enforce a pre-episode settle/reset gate for active-left joint initial
  positions and EEF base pose.
- Ensure previous joint commands have decayed before recording starts.
- Abort or skip an episode if initial joint drift or initial EEF pose is
  outside a conservative tolerance.
- Keep the gripper disabled and keep the task as arm-only reaching/pre-grasp.

Do not expand collection or train BC / DP / FM from `b8_reaching_debug_10`.

Implementation note:

```text
scripts/check_b8_initial_state_gate.py
```

This first gate is intentionally read-only. It checks whether the live
active-left joint configuration, EEF/base pose, relative target/EEF vector, and
initial distance remain near a successful reference episode before any further
collection attempt. It does not publish arm commands and does not implement a
return-to-neutral command.

Reason for not adding a neutral/reset command yet:

- The failure evidence says reset/settle is likely needed, but a safe neutral
  target and controller response still need to be checked.
- A read-only gate can confirm the drift hypothesis without adding another
  control action to the system.
- If the gate fails consistently, the next expert change should be a bounded
  reset/settle behavior with explicit metadata, followed by one short
  verification run only.

## B8' Reset/Settle Expert Update

Review date: 2026-05-05.

The one gated arm-only verification episode showed good single-episode
reaching and command-motion, but the post-episode gate failed because the arm
remained in the reached/pregrasp configuration. The next expert-side blocker
is therefore repeatable reinitialization.

Selected minimum reset/settle strategy:

```text
bounded return-to-reference active-left joint command
-> target-aware initial-state gate
-> only then allow another episode
```

Added tool:

```text
scripts/return_left_arm_to_reference.py
```

Expert constraints:

- Use the active-left initial joint positions from a successful reference NPZ.
- Clip every return command to a small per-joint step, default `0.01 rad`.
- Publish only `/oberon7/arm_position_l/command`.
- Do not send gripper commands.
- Do not start hand controllers.
- After return, require `check_b8_initial_state_gate.py` to pass before
  another episode.

This is not training, not learned rollout, and not grasping.

## B8' Repeatability Smoke Expert Update

Review date: 2026-05-05.

The tuned v3 scripted reaching expert was used for a 5-episode repeatability
smoke set:

```text
data/raw/b8_reaching_repeatability_smoke/
```

Runtime constraints were preserved:

- `enable_gripper_command=false`;
- `load_hand=false`;
- `gripper_enabled=false`;
- `is_grasp_dataset=false`;
- `allow_nominal_state_fallback=false`;
- `target_directed_action_frame=base_link`;
- `arm_action_frame=base_link`.

Result:

```text
validator_pass_count: 5/5
success_count: 5/5
mean_initial_distance: 0.10765874377608645
mean_final_distance: 0.06034401658235772
mean_distance_reduction: 0.0473147271937287
max_target_step_base: 0.014892885342403243
large_target_step_indices: [] for all episodes
mean_best_action_to_eef_cosine: 0.7559808833882034
mean_best_lag_steps: 2.2
mean_best_realized_gain_along_action: 0.2432157689973347
```

Expert interpretation:

- The scripted expert is repeatable enough for a 5-episode arm-only
  reaching/pre-grasp smoke check.
- This result is not grasping and not learned rollout evidence.
- Do not change gripper handling as part of this route.
- The next data action should be a small deliberate real non-fallback
  arm-only collection plan with the same quality gates, not immediate
  large-scale expansion.

## B8' Quality Review Expert Update

Review date: 2026-05-04.

The first B8' 5-episode smoke collection validated the non-fallback data path,
but the reaching quality is still weak:

```text
episodes_below_0.10: 0/5
episodes_with_positive_distance_reduction: 3/5
min_distance_overall: 0.118852 m
mean_distance_reduction: 0.002899 m
max_active_left_joint_delta: 0.008000 rad
```

Action review:

```text
action_xyz_norm_mean_all_samples: 0.007494 m
action_xyz_norm_max_all_samples: 0.008660 m
per-axis clipping at 0.005 m is frequent
```

Expert interpretation:

- The data path is no longer the immediate blocker for B8' smoke collection.
- The scripted reaching expert is too conservative for useful demonstration
  quality under the current short-window settings.
- Joint motion is small and bounded, so the next adjustment should still remain
  conservative, but it should produce more decisive base-frame distance
  reduction.
- With `enable_base_relative_target:=true`, target motion should be interpreted
  as base-relative target setup, not a world-static target success claim.

Recommended next expert changes before another 5-episode smoke:

- use `arm_action_frame:=base_link` so base-frame target-directed deltas are
  rotated into the MoveIt planning frame before IK;
- increase `max_linear_step` from `0.005 m` to `0.010 m` for the next bounded
  smoke;
- increase `max_joint_delta` from `0.010 rad` to `0.015 rad` for the next
  bounded smoke;
- increase the command rate to `3.0 Hz` and use `time_from_start_sec:=1.0`;
- execute both `MOVE_TO_PREGRASP` and `MOVE_TO_GRASP`, while keeping
  `max_duration_sec:=3.3` to avoid entering gripper states;
- review base-frame action direction and pregrasp offset before changing the
  reaching threshold.

Implementation prepared:

```text
launch/b8_reaching_tuned_episode.launch
```

This wrapper collects one tuned B8' smoke episode. Run episode 0000 first and
review it before collecting 0001-0004.

Do not expand to 20 episodes or retrain BC / DP / FM from the current smoke set.

## Candidate Expert Types

1. Scripted waypoint expert
   - Define approach, pre-grasp, grasp, lift/hold waypoints.
   - Use deterministic target-relative poses.
   - Best first fallback if MoveIt is not immediately usable.

2. IK waypoint expert
   - Convert target-relative end-effector waypoints into left-arm joint commands.
   - Requires confirmed left-arm joint names, kinematic chain, and command interface.

3. MoveIt expert
   - Use existing `rexrov_moveit_revised` or `oberon7_moveit_revised` only after confirming the current setup works.
   - Must check `move_group`, planning groups, `/compute_ik`, and controller execution before relying on it.

## Stage 1 Static Expert Sources

Potentially reusable expert/controller sources:

| Source | File | Reuse value | Caveat |
| --- | --- | --- | --- |
| Fixed left EE target publisher | `uvms_control/scripts/ref_traj_oberon7_fixed_point.py` | Publishes `geometry_msgs/Pose` to `/uvms/left_arm/end/target` | Only a target publisher, not a policy |
| Left-arm MoveIt tracker | `uvms_control/scripts/baseline_oberon7_planning_and_control_rrtconnect_and_pid_py.py` | Uses `MoveGroupCommander("arm_l")`, `eef_link=oberon7_l/end_effector`, and `/compute_ik`; best MoveIt expert prototype | Requires `move_group`, `/compute_ik`, TF, planning frame, and trajectory execution to work |
| Base MoveIt planner | `uvms_control/scripts/baseline_rexrov_planning_rrtconnect_py.py` | Plans `base` group path and publishes `/baseline/rexrov/target_traj` | Useful only if base motion is part of expert; first grasp demo may keep base simple |
| RexROV NMPC tracker | `uvms_control/scripts/rexrov_controller.py` | Tracks `/uvms/ref_traj_rexrov` and publishes `/rexrov/thruster_manager/input` | Base-only; not an arm grasp expert |
| Baseline RexROV NMPC | `uvms_control/scripts/baseline_rexrov_control_nmpc_py.py` | Tracks `nav_msgs/Path` from base planner | Base-only; logs CSV, not episode data |
| Dual-arm sine effort collector | `data_rexrov_dual_oberon7/scripts/data_collector_dual_oberon7.py` | Shows how to publish left/right effort vectors and read joint states | Excitation collector, not task expert |
| Simple joint reference forwarder | `uvms_control/scripts/ref_traj_oberon7_simple.py` and `oberon7_controller_pid.py` | Shows joint order and position-command flow | Dual-arm sinusoidal/static reference, not object-aware |

Recommended first expert direction after runtime checks:

1. Use `data_rexrov_dual_oberon7/launch/rexrov_dual_oberon7.launch` or a project-local wrapper around it as the base simulation.
2. Confirm left-arm controller command path and joint state topic.
3. If `move_group` and `/compute_ik` work, adapt the left-arm MoveIt tracker concept into this package as an expert.
4. If MoveIt trajectory execution is not reliable, start with a scripted or IK waypoint expert that outputs fixed left-arm position or effort commands.

MoveIt static status:

- Planning groups `arm_l` and `hand_l` exist in revised SRDF.
- `kinematics.yaml` defines KDL solvers for `arm_l` and `arm_r`.
- `simple_moveit_controllers.yaml` has an empty `controller_list`.
- `ros_controllers.yaml` is empty.
- Therefore, MoveIt planning may work, but Gazebo trajectory execution is not proven statically.

## First-Version Constraints

- Active arm: left only.
- Right arm: fixed or ignored.
- Observation: state only.
- Action labels: end-effector delta action plus a compatibility
  `gripper_cmd` slot.
- Current arm-only route ignores or fixes `gripper_cmd`; do not publish gripper
  commands.
- No joystick dependency.
- No long simulation runs in early validation.

## Open Questions For Stage 1

- Which launch file is the cleanest base for RexROV + dual Oberon7 with left-arm control?
- Which joint state topic is authoritative?
- Which controller interface should be used for left-arm commands?
- Is the existing MoveIt configuration usable in the current workspace without modifying official packages?
- What target object model and pose source should be used for the first geometric grasp task?

## Stage 1 Answers And Remaining Gaps

- Cleanest static base launch: `data_rexrov_dual_oberon7/launch/rexrov_dual_oberon7.launch`.
- Best MoveIt expert prototype: `uvms_control/scripts/baseline_oberon7_planning_and_control_rrtconnect_and_pid_py.py`.
- Joint state topic remains unresolved: static code uses both `/joint_states` and `/rexrov/joint_states`.
- Current MoveIt config is promising for planning groups but not confirmed for trajectory execution.
- First target candidates: `cylinder_target`, `sphere_target`, or the inline `grabbapole` in `dave_bimanual_example.world`; prefer project-local world/launch wrapper later instead of editing DAVE.

## Stage 2 Runtime Expert Findings

Runtime date: 2026-04-29.

MoveIt check sequence:

```bash
roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=true
roslaunch rexrov_moveit_revised planning_context_revised.launch load_robot_description:=false
roslaunch rexrov_moveit_revised move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
```

MoveIt status:

- `move_group` does not start with the minimal simulation launch; it must be launched separately for MoveIt expert checks.
- `/compute_ik` is available after starting `move_group`; service type is `moveit_msgs/GetPositionIK`.
- `MoveGroupCommander("arm_l")` works for read-only group inspection when `/clock` is advancing.
- `MoveGroupCommander("left_arm")` fails; the valid group name is `arm_l`.
- `MoveGroupCommander("hand_l")` works for the left gripper group.
- `arm_l` end-effector link is `oberon7_l/end_effector`.
- Planning frame reported by MoveIt is `world`.
- `move_group` reports `No controller_list specified` and returns zero controllers, matching the static finding that `simple_moveit_controllers.yaml` has an empty `controller_list`.
- `move_group` repeatedly warned that the complete robot state was not known, including missing `world_to_base` and several fixed/sensor joints. This did not block group discovery, but it must be checked before relying on full planning results.

Conclusion for first expert choice:

- MoveIt is usable as an IK/planning source for `arm_l`.
- MoveIt is not yet proven usable for direct trajectory execution in Gazebo.
- Do not base the first data-collection loop on MoveIt execution until a left-arm controller command path is confirmed.
- Preferred next expert implementation path remains:
  1. scripted waypoint expert or IK waypoint expert that outputs project-local commands;
  2. optionally use `/compute_ik`/`MoveGroupCommander("arm_l")` to generate waypoints;
  3. only add MoveIt execution after controller mapping is fixed and tested.

Controller/execution blockers:

- Minimal launch did not expose left-arm `follow_joint_trajectory` or group command topics.
- `joint_state_controller` loaded, but the arm controller spawner did not produce visible command/action topics.
- `/controller_manager/list_controllers` did not return during the check.
- Stage 3 should first identify a launch or controller spawner sequence that exposes a safe left-arm command interface.

Fallback expert plan if controller execution remains unavailable:

- Keep the base fixed or command only through `/rexrov/thruster_manager/input` if needed.
- Use Gazebo reset/model-state services plus joint-state observations for dataset validation.
- Generate target-relative desired EE deltas offline or with `/compute_ik`.
- Delay policy rollout until a confirmed low-level left-arm command topic is available.

## Stage 5 Scripted Expert Implementation

Runtime date: 2026-04-29.

Expert type decision:

- MoveIt IK/planning is available, but MoveIt trajectory execution is not configured because `controller_list` is empty.
- Left-arm and gripper command topics are still unresolved for execution.
- Therefore Stage 5 implements a scripted fallback expert that publishes project-local expert action labels, not physical arm commands.

Implemented files:

- `src/rexrov_single_oberon7_fm_dp/action_converter.py`
- `src/rexrov_single_oberon7_fm_dp/expert_policy.py`
- `src/rexrov_single_oberon7_fm_dp/success_checker.py`
- `scripts/scripted_expert.py`
- `launch/collect_episode.launch`
- `models/cylinder_target/model.sdf`

State machine:

```text
WAIT_FOR_STATE
MOVE_TO_PREGRASP
MOVE_TO_GRASP
CLOSE_GRIPPER
LIFT_OR_HOLD
FINISH
```

`APPROACH_BASE` is defined as a stage concept but is not active in the first implementation because the base-control/expert coupling is not needed for the first state-based data smoke test.

Published expert topics:

```text
/rexrov_single_oberon7_fm_dp/expert/action_ee_delta
/rexrov_single_oberon7_fm_dp/expert/state
/rexrov_single_oberon7_fm_dp/expert/success
```

Action label:

```text
[dx, dy, dz, droll, dpitch, dyaw, gripper_cmd]
```

Stage 5 action sequence:

- `MOVE_TO_PREGRASP`: small positive approach delta, gripper open.
- `MOVE_TO_GRASP`: small forward/down grasp delta, gripper open.
- `CLOSE_GRIPPER`: zero EE delta, gripper closed.
- `LIFT_OR_HOLD`: upward lift delta, gripper closed.

Target handling:

- `collect_episode.launch` can spawn a package-local simple cylinder model named `cylinder_target`.
- The expert waits for `cylinder_target` in `/gazebo/model_states`.
- If the target is unavailable, the expert can use `task_grasp.yaml` nominal target pose as fallback, but the recorder only marks `target_pose` available when Gazebo actually publishes the target model.

Success checker:

- The first success checker requires closed gripper, finite target pose, finite end-effector pose, and distance below threshold.
- Because Stage 5 still does not compute `eef_pose`, final success remains `False` in the smoke episode.
- This is intentional: Stage 5 validates expert action-label generation and dataset structure, not real grasp execution.

Stage 5 smoke result:

```text
episode: data/raw/stage5_scripted_expert_smoke_v2.npz
validation: PASS
T: 10
controller_type: scripted
target_pose finite: true
action_ee_delta finite: true
success: false
unavailable_fields:
  - eef_pose
  - relative_target_to_eef
  - raw_command
```

Remaining expert gaps:

- The scripted expert does not yet command the real Oberon7 controllers.
- `eef_pose` is not computed, so success cannot become true using the distance-based criterion.
- MoveIt can still be used later for IK waypoint generation once command execution is mapped.

## B8' Small Debug Batch Expert Follow-Up

Date: 2026-05-05.

Latest arm-only reaching debug batch:

```text
data/raw/b8_reaching_debug_10/
```

Result:

```text
episodes_total: 10
validator_pass_count: 10/10
success_count: 7/10
reaching_success_rate: 0.7
mean_best_action_to_eef_cosine: 0.5547614407437549
mean_best_lag_steps: 2.6
mean_best_realized_gain_along_action: 0.13983358394761614
```

Expert-policy implication:

- The current scripted reaching expert can produce valid non-fallback arm-only
  reaching data, but the quality is not stable enough for training-data
  expansion.
- Episodes 0007-0009 failed consecutively despite clean metadata and bounded
  target/base source-sync.
- The next expert-policy work should inspect command-to-motion degradation
  across repeated episodes, especially whether accumulated arm/base
  configuration drift changes the IK context or reduces realized EEF progress.

Do not use this batch to claim grasping, learned rollout success, or final
training dataset completion.

## B8' Target-Directed Action-Frame Fix

Date: 2026-05-05.

`b8_return_gated_arm_verify_3_0000` exposed an expert-policy implementation
bug:

```text
target_directed_reaching=true
target_directed_action_frame=base_link
arm converter action_frame=planning_frame
runtime failure=IK failed with MoveIt error code -31
saved success=false
mean_best_action_to_eef_cosine=0.08695271743383595
```

The target-directed action was generated as a base-link delta, but the arm
converter interpreted it as a planning-frame delta.

Patch:

```text
file: src/rexrov_single_oberon7_fm_dp/expert_policy.py
behavior: when target_directed_reaching=true, initialize the arm converter with
          target_directed_action_frame; otherwise keep arm_action_frame
py_compile: PASS
```

Post-fix smoke:

```text
b8_return_gated_arm_verify_4_0000
runtime action_frame=base_link
validator=PASS
saved success=True
recorded_success_distance_m=0.05744791236250198
mean_best_action_to_eef_cosine=0.3532763904220775
mean_best_realized_gain_along_action=0.17090696757478616
```

This is still only B8' arm-only reaching/pre-grasp debug evidence. It is not
grasp success, not learned rollout, and not training evidence.

## B8' Small Post-Fix Debug Batch Expert Plan

Date: 2026-05-05.

The next expert-policy validation step is planned but not executed:

```text
small post-fix debug batch
default_episode_count=3
hard_max_episode_count=5
route=return_to_reference -> target-aware gate -> corrected target-directed
      arm-only episode -> diagnostics
```

Required expert settings:

```text
execute_arm=true
execute_arm_once_per_state=false
execute_arm_states=MOVE_TO_PREGRASP,MOVE_TO_GRASP
state_sequence=MOVE_TO_PREGRASP,MOVE_TO_GRASP
target_directed_reaching=true
target_directed_action_frame=base_link
enable_gripper_command=false
allow_nominal_state_fallback=false
max_linear_step=0.010
max_joint_delta=0.010
time_from_start_sec=1.0
```

Stop conditions:

```text
return/gate failure after one 5 s target-settle retry
IK -31 or expert crash
validator failure
metadata inconsistency
target/base large jump
command-motion collapse toward pre-fix failed values
```

This remains arm-only reaching/pre-grasp expert-debug work. It is not grasping,
not learned rollout, and not training.
