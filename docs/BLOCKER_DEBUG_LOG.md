# Blocker Debug Log

Last updated: 2026-05-07

## Round 2026-05-07: Formal BC/DP/FM Live Protocol Blocked At Strict Pre-Gate

Scope:

```text
arm-only reaching / pre-grasp positioning
no gripper command
no hand controller
no grasp success claim
```

Read-only runtime checks showed the live ROS graph was available:
`/joint_states`, `/rexrov/pose_gt`, `/gazebo/model_states`, TF
`rexrov/base_link -> oberon7_l/end_effector`, and
`/oberon7/arm_position_l/state` were readable. Controller manager listed
`joint_state_controller` and `oberon7/arm_position_l` running, with no hand
controller in the controller list.

Formal protocol artifacts were written:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/formal_protocol.md
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/formal_protocol.json
```

BC cycle 0 stopped before rollout:

```text
return_to_reference reached=true
return commands_sent=0
strict pre-gate attempt 0: failed
strict pre-gate retry 1: failed
strict pre-gate retry 2: failed
best retry target_base_drift=0.010550711129789662
best retry relative_base_drift=0.007371669176824283
strict target/relative drift threshold=0.001
rollout command sent=false
gripper command sent=false
```

Failure artifact:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/bc/cycle_0/summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol/bc/cycle_0/summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
```

Interpretation:

```text
This is an initial target/base synchronization gate failure, not a BC rollout
performance failure. DP/FM dry-run and live smoke were not started because the
shared live protocol gate did not pass.
```

Next minimum debug target: restore a clean target/base gate, likely by
restarting or resetting the target gate probe/base-relative target updater,
then require two strict fresh gates before any policy command.

Follow-up in the same turn:

```text
reset_b8_target_gate_probe.py: passed, target already absent
b8_target_gate_probe.launch: restarted
b8_target_gate_base_relative_target: running
cylinder_target_gate_probe: present in /gazebo/model_states
BC return_to_reference: reached=true
strict pre-gate after restart: failed
retry target_base_drift=0.006711007793366516
retry relative_base_drift=0.006271075196806217
rollout command sent=false
```

Artifact:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_live_protocol_after_target_restart/bc/cycle_0/summary.md
```

Judgment: target gate restart alone is insufficient. The remaining blocker is
live target/base/EEF frame consistency under the strict `0.001 m` fresh-gate
threshold.

Aggressive protocol-v4 follow-up:

```text
shared gate thresholds:
  initial_distance_max=0.125
  target_drift_max=0.02
  relative_drift_max=0.02
  max_control_ticks=9
  clip=0.005 m
  max_joint_delta=0.01 rad

BC: 0/1, safety abort on arm_command_conversion_or_execution_failed
BC IK error code=-31
DP: 3/3 reaching_success, abort_count=0
FM: 3/3 reaching_success, abort_count=0
```

BC details: the BC cycle reached the configured distance/reduction thresholds,
but continuing to tick 9 led to an IK failure, so the cycle is correctly marked
failed under the safety criterion.

Artifact:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
```

This log records blocker-focused debugging after Stage 12. Work should proceed
one blocker at a time. Prefer read-only checks first. Do not claim real rollout
success until action execution, live recording, and success checking are all
verified.

## Debug Rules

- Handle one blocker at a time.
- Explain what each user-run command verifies before asking for output.
- Prefer read-only ROS graph/topic/service checks before modifying code.
- Record each round's findings here and in `CURRENT_STATUS.md`.
- Do not modify:
  - `src/dave`
  - `src/uuv_simulator`
  - `src/uuv_manipulators`
  - `src/rexrov2`
- Main write scope remains:
  `src/uvms/rexrov_single_oberon7_fm_dp`.
- Do not run training or long simulation during blocker triage unless the user
  explicitly asks.

## Blocker Inventory

| ID | Blocker | Current status | Next debug target |
| --- | --- | --- | --- |
| B1 | Live state collection unstable | Resolved for current minimal launch and recorder smoke test | Revisit only if later non-fallback collection fails |
| B2 | Left-arm/gripper command interface unconfirmed | Partially resolved: left-arm joint-space command execution minimally resolved; B2b confirms gripper moves in clean baseline with no hand controller loaded | Diagnose gripper model/physics/controller config; do not send gripper command |
| B3 | `eef_pose` / TF unavailable | Resolved for current minimal launch and non-fallback recorder smoke test | Revisit only if later runtime launch changes TF frames |
| B4 | Stage 6 fallback dataset | Open | Recollect only after B1-B3 are fixed |
| B5 | Scripted expert does not drive arm | Partially resolved: B5a/B5b/B5c minimal resolved; B5d' selected for arm-only reaching route | Restore arm controller + static target prerequisites, then run arm-only reaching smoke |
| B6 | MoveIt IK works but execution is unconfirmed | Open | Requires controller mapping check after B2 |
| B7 | TensorBoard unavailable | Low priority | Keep JSON/checkpoint workflow; revisit only if needed |

## Round 1: Initialize Debug Tracking

Date: 2026-05-02

Docs read:

- `docs/PROJECT_MAP_FOR_DP_FM.md`
- all files under `src/uvms/rexrov_single_oberon7_fm_dp/docs`

Key facts read from docs:

- Stage 2 confirmed `/joint_states`, `/rexrov/pose_gt`, `/gazebo/model_states`,
  and `/gazebo/get_model_state` in an earlier minimal launch.
- Stage 6 later found live samples and target spawn were not reliable enough for
  batch collection, so fallback metadata was used.
- Stage 10 rollout is safe dry-run only because controller mapping is
  unconfirmed.
- Stage 11 results are fallback-data pipeline results, not real grasp success.
- Stage 12 packaged the demo and preserved the same limitations.

Selected first blocker:

```text
B1: live state collection unstable
```

Reason:

- Non-fallback demonstration data requires stable live base, joint, and target
  state first.
- Real success-rate evaluation is impossible without reliable live observations.
- Controller and expert debugging can come after the state recorder has a stable
  truth source.

Minimal read-only checks proposed for the user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=false
```

In a second terminal:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rostopic list | grep -E "joint_states|pose_gt|model_states|clock|gazebo"
rostopic info /joint_states
rostopic info /rexrov/pose_gt
rostopic info /gazebo/model_states
rostopic echo -n 1 /joint_states
rostopic echo -n 1 /rexrov/pose_gt
rostopic echo -n 1 /gazebo/model_states
rosservice list | grep -E "gazebo/get_model_state|gazebo/spawn|controller_manager"
```

Expected success signal:

- `/joint_states` exists and publishes one message with all left-arm and left
  gripper joints.
- `/rexrov/pose_gt` exists and publishes one odometry message.
- `/gazebo/model_states` exists and publishes one message containing at least
  the RexROV model and any spawned target model if present.
- `/gazebo/get_model_state` is available.

Expected failure signals:

- A topic exists but `rostopic echo -n 1` hangs or returns no message.
- `/joint_states` lacks left Oberon7 joint names.
- `/gazebo/model_states` does not include the expected target after target
  spawn is enabled in a later check.
- Gazebo services exist but calls hang during spawn/delete operations.

Round 1 status:

- Documentation initialized.
- Waiting for user terminal output from the proposed read-only checks.

## Round 2: B1 Base And Joint Live State Check

Date: 2026-05-02

User launch:

```bash
roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=false
```

User-reported topic list included:

```text
/clock
/gazebo/link_states
/gazebo/model_states
/joint_states
/rexrov/pose_gt
/rexrov/pose_gt/state
```

Topic info:

```text
/joint_states:
  type: sensor_msgs/JointState
  publisher: /gazebo
  subscriber: /robot_state_publisher

/rexrov/pose_gt:
  type: nav_msgs/Odometry
  publisher: /gazebo

/gazebo/model_states:
  type: gazebo_msgs/ModelStates
  publisher: /gazebo
```

Single-sample checks:

- `/joint_states` returned a live sample at simulation time around 340 s.
- `/rexrov/pose_gt` returned a live odometry sample at simulation time around
  341 s.
- `/gazebo/model_states` returned a live model-state sample.

Active-left joint names present in `/joint_states`:

```text
oberon7_l/azimuth
oberon7_l/elbow
oberon7_l/finger_left_joint
oberon7_l/finger_right_joint
oberon7_l/finger_tip_left_joint
oberon7_l/finger_tip_right_joint
oberon7_l/pitch
oberon7_l/roll
oberon7_l/shoulder
oberon7_l/wrist
```

Important recorder note:

- Runtime joint order differs from the semantic controller order. This matches
  Stage 2. Recorder/controller code must continue indexing joints by name.

Gazebo model list from `/gazebo/model_states`:

```text
ocean_box
rexrov
```

Services present:

```text
/gazebo/get_model_state
/gazebo/spawn_sdf_model
/gazebo/spawn_urdf_model
/controller_manager/list_controllers
/controller_manager/switch_controller
```

Judgment:

```text
B1 is partially resolved, not fully resolved.
```

Resolved by this check:

- Live `/joint_states` exists and includes the active-left arm and gripper.
- Live `/rexrov/pose_gt` exists.
- Live `/gazebo/model_states` exists.
- Gazebo model-state and spawn services exist.

Still open:

- No task target is present in the current Gazebo model list.
- Target pose source is therefore not yet live for a grasp episode.
- Topic-rate stability has not been measured.
- Spawn/get-model-state behavior for `cylinder_target` has not been isolated.

Does this require code changes now?

```text
No.
```

Reason:

- The immediate finding is runtime configuration/state, not a recorder code
  defect.
- Next step should remain read-only: check publish rates and call
  `/gazebo/get_model_state` for `rexrov` and `cylinder_target`.

Next minimal checks requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rostopic hz /joint_states -w 20
rostopic hz /rexrov/pose_gt -w 20
rostopic hz /gazebo/model_states -w 20
```

Purpose:

- Confirm that the live topics publish continuously at nonzero rates instead of
  only producing a single sample.

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosservice call /gazebo/get_model_state "{model_name: 'rexrov', relative_entity_name: 'world'}"
rosservice call /gazebo/get_model_state "{model_name: 'cylinder_target', relative_entity_name: 'world'}"
```

Purpose:

- Confirm that `/gazebo/get_model_state` can return the RexROV pose.
- Confirm the expected current failure for `cylinder_target`, since no target is
  present in `/gazebo/model_states`.

Expected interpretation:

- If all `rostopic hz` calls show stable nonzero rates and `rexrov` returns
  `success: True`, then base/joint live state is no longer the blocker.
- If `cylinder_target` returns `success: False`, the next B1 sub-blocker is
  target spawn/state availability.
- If any command hangs or returns no data, keep B1 focused on that specific
  topic/service before moving to command-interface debugging.

## Round 3: B1 Topic Rate And Target Absence Check

Date: 2026-05-02

User-reported topic rates:

```text
/joint_states: about 50 Hz
/rexrov/pose_gt: about 20 Hz
/gazebo/model_states: about 500 Hz
```

User-reported `/gazebo/get_model_state` results:

```text
model: rexrov
success: True
status_message: "GetModelState: got properties"

model: cylinder_target
success: False
status_message: "GetModelState: model does not exist"
```

Judgment:

```text
B1 remains partially resolved.
```

Resolved by this check:

- `/joint_states` is continuously publishing at a recorder-suitable rate.
- `/rexrov/pose_gt` is continuously publishing at a recorder-suitable rate.
- `/gazebo/model_states` is continuously publishing.
- `/gazebo/get_model_state` works for an existing model (`rexrov`).

Still open:

- `cylinder_target` is not present in the current Gazebo world.
- Target live pose is not available until the target is spawned.
- A non-fallback grasp episode cannot be recorded yet because the target state
  source would fail for the configured target.

Does this require code changes now?

```text
No.
```

Reason:

- The remaining issue is target-model availability in Gazebo, not a code defect.
- The package already contains a local target SDF:
  `models/cylinder_target/model.sdf`.
- `collect_episode.launch` already contains a `gazebo_ros/spawn_model` path, but
  the next check should isolate target spawn without starting recorder/expert.

Next minimal check requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosrun gazebo_ros spawn_model \
  -sdf \
  -file "$(rospack find rexrov_single_oberon7_fm_dp)/models/cylinder_target/model.sdf" \
  -model cylinder_target \
  -x 2.6 -y 2.0 -z -40.0
```

Purpose:

- Test whether the package-local `cylinder_target` can be spawned into the
  currently running Gazebo world without invoking the recorder or scripted
  expert.

Verification after spawn:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosservice call /gazebo/get_model_state "{model_name: 'cylinder_target', relative_entity_name: 'world'}"
rostopic echo -n 1 /gazebo/model_states
```

Expected interpretation:

- If `spawn_model` returns promptly and `get_model_state` returns
  `success: True`, B1 target-state availability is confirmed for a single
  spawned target.
- If `spawn_model` hangs or target state still returns `success: False`, B1
  remains focused on spawn/model availability.
- If target state succeeds, the next B1 check should be a short recorder smoke
  test with fallback disabled, not controller debugging yet.

## Round 4: B1 Target Spawn Check

Date: 2026-05-02

User command:

```bash
rosrun gazebo_ros spawn_model \
  -sdf \
  -file "$(rospack find rexrov_single_oberon7_fm_dp)/models/cylinder_target/model.sdf" \
  -model cylinder_target \
  -x 2.6 -y 2.0 -z -40.0
```

User-reported result from first run:

```text
Loading model XML from file .../models/cylinder_target/model.sdf
Waiting for service /gazebo/spawn_sdf_model
Calling service /gazebo/spawn_sdf_model
Spawn status: SpawnModel: Successfully spawned entity
```

User accidentally repeated the same spawn command. Second-run result:

```text
Spawn status: SpawnModel: Failure - entity already exists.
Spawn service failed. Exiting.
```

Judgment:

```text
Target spawn path works.
B1 is still not fully closed until target state readback is confirmed.
```

Resolved by this check:

- The package-local SDF file is valid enough for Gazebo spawn.
- `/gazebo/spawn_sdf_model` returns promptly.
- The first call created `cylinder_target`.
- The second call failing with `entity already exists` is expected and confirms
  the target exists in the Gazebo world after the first spawn.

Still open:

- The user has not yet pasted `/gazebo/get_model_state` output for
  `cylinder_target` after the successful spawn.
- The user has not yet pasted `/gazebo/model_states` after spawn showing
  `cylinder_target` in the `name` list.
- A non-fallback recorder smoke test should wait until these state-readback
  checks are confirmed.

Does this require code changes now?

```text
No.
```

Reason:

- Spawn works from the existing package-local model and existing Gazebo service.
- The remaining step is read-only verification of target state visibility.

Next minimal check requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosservice call /gazebo/get_model_state "{model_name: 'cylinder_target', relative_entity_name: 'world'}"
rostopic echo -n 1 /gazebo/model_states
```

Purpose:

- Confirm that the successfully spawned target can be read through
  `/gazebo/get_model_state`.
- Confirm that `/gazebo/model_states` includes `cylinder_target`, which is the
  source used by the recorder for target pose.

Expected interpretation:

- If `success: True` and `/gazebo/model_states.name` includes
  `cylinder_target`, B1 live base/joint/target state is resolved for the current
  minimal launch.
- If readback fails, continue debugging target state availability before moving
  to command interface or `eef_pose`.

## Round 5: B1 Target State Readback Check

Date: 2026-05-02

User-reported `/gazebo/get_model_state` for `cylinder_target` after spawn:

```text
success: True
status_message: "GetModelState: got properties"
pose.position:
  x: 2.5999811641058828
  y: 1.9999992079287308
  z: -99.80004115722211
pose.orientation.w: 0.9999999985999719
```

User-reported `/gazebo/model_states.name`:

```text
ocean_box
rexrov
cylinder_target
```

Judgment:

```text
B1 state-source availability is resolved for the current minimal launch.
```

Resolved by this check:

- `/joint_states` publishes live active-left arm and gripper joints.
- `/rexrov/pose_gt` publishes live base odometry.
- `/gazebo/model_states` publishes continuously.
- `/gazebo/get_model_state` works for `rexrov`.
- `cylinder_target` can be spawned from the package-local SDF.
- `cylinder_target` is visible through both `/gazebo/get_model_state` and
  `/gazebo/model_states`.

Important observation:

- The target was spawned with `z=-40.0`, but the readback pose was near
  `z=-99.8`.
- This means the simple dynamic target can fall or settle in the current world.
- That is not a state-source blocker, but it is a later task-setup issue for
  reachable grasp demonstrations.

Does this require code changes now?

```text
No.
```

Reason:

- The ROS/Gazebo state sources needed by the recorder are available.
- The next check should validate the recorder's non-fallback write path before
  moving to B2 command-interface debugging.

Next minimal check requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
roslaunch rexrov_single_oberon7_fm_dp record_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw \
  episode_id:=b1_live_state_smoke \
  rate_hz:=2.0 \
  max_duration_sec:=2.0 \
  require_target:=true \
  target_model_name:=cylinder_target
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/validate_episode.py \
  src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b1_live_state_smoke.npz
```

Purpose:

- Confirm that the recorder writes a short `.npz` using live base, live joint,
  and live target state without nominal target fallback.
- This does not test controller execution, `eef_pose`, expert motion, or policy
  rollout.

Expected interpretation:

- Validator pass plus metadata showing live base/joint/target availability
  closes B1 at the recorder level.
- `eef_pose`, `relative_target_to_eef`, `action_ee_delta`, and `raw_command`
  may remain unavailable for this state-only test; that is expected and belongs
  to later blockers.

## Round 6: B1 Non-Fallback Recorder Smoke Test

Date: 2026-05-02

User command:

```bash
roslaunch rexrov_single_oberon7_fm_dp record_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw \
  episode_id:=b1_live_state_smoke \
  rate_hz:=2.0 \
  max_duration_sec:=2.0 \
  require_target:=true \
  target_model_name:=cylinder_target
```

User-reported recorder result:

```text
Recording episode b1_live_state_smoke: 4 samples at 2.000 Hz
Saved episode to .../data/raw/b1_live_state_smoke.npz
Episode recording complete
process has finished cleanly
```

User-reported validator result:

```text
validation: PASS
T: 4
success: False
episode_id: b1_live_state_smoke
unavailable_fields:
  - eef_pose
  - relative_target_to_eef
  - action_ee_delta
  - raw_command
```

Local read-only metadata check:

```text
episode_id: b1_live_state_smoke
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
allow_nominal_state_fallback: False
target_model_name: cylinder_target
field_availability.target_pose: True
target_pose finite: True
base_pose finite: True
active_joint_positions finite: True
T: 4
```

Judgment:

```text
B1 is resolved for the current minimal launch and recorder write path.
```

Resolved by this check:

- Recorder can write a short episode with live base pose from `/rexrov/pose_gt`.
- Recorder can write active-left joint state from `/joint_states`.
- Recorder can write target pose from `/gazebo/model_states`.
- Fallback state was not used for base, joint, or target in this smoke file.

Remaining issues moved to later blockers:

- `eef_pose` and `relative_target_to_eef` remain unavailable: B3.
- `action_ee_delta` is unavailable because no expert/policy action was active:
  B5/B2.
- `raw_command` is unavailable because no real command was sent: B2.
- The target falling to around `z=-99.8` is a task/world setup issue for later
  demonstration quality, not a live state-source blocker.

Does this require code changes now?

```text
No.
```

Reason:

- The recorder and validator already support non-fallback live state recording
  for the base, active-left joints, and target.

Next blocker:

```text
B2: left-arm and gripper command interface unconfirmed
```

Next minimal checks requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rostopic list | grep -E "arm|hand|oberon|controller|trajectory|follow_joint"
rosparam list | grep -E "controller|arm|hand|oberon"
rosservice list | grep -E "controller_manager|controller"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
timeout 5s rosservice call /controller_manager/list_controller_types "{}"
```

Purpose:

- Identify which left-arm and gripper controller topics or action interfaces
  exist in the current launch.
- Check whether the controller manager can list controllers without hanging.
- Do not send any command or trajectory yet.

Expected interpretation:

- If arm/hand controllers are loaded and running, the next B2 step can inspect
  exact command topic types.
- If controller-manager calls time out, debug controller-manager health before
  attempting motion.
- If only joint-state controller is present, command execution remains
  unavailable in this minimal launch.

## Round 7: B2 Read-Only Controller Graph Check

Date: 2026-05-02

User commands:

```bash
rostopic list | grep -E "arm|hand|oberon|controller|trajectory|follow_joint"
rosparam list | grep -E "controller|arm|hand|oberon"
rosservice list | grep -E "controller_manager|controller"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
timeout 5s rosservice call /controller_manager/list_controller_types "{}"
```

User-reported topic result:

```text
no matching arm/hand/oberon/controller/trajectory/follow_joint topics
```

User-reported parameter result:

- Many controller parameters exist under `/oberon7/...`.
- Candidate left-arm parameters include:
  - `/oberon7/arm_position_l/type`
  - `/oberon7/arm_position_l/joints`
  - `/oberon7/arm_l_group_effort/type`
  - `/oberon7/joint_group_arm_l_position_controller/type`
- Candidate left-gripper parameters include:
  - `/oberon7/hand_position_l/type`
  - `/oberon7/hand_position_l/joints`
  - `/oberon7/hand_effort_l/type`
  - `/oberon7/joint_group_hand_l_position_controller/type`

User-reported services:

```text
/controller_manager/list_controller_types
/controller_manager/list_controllers
/controller_manager/load_controller
/controller_manager/reload_controller_libraries
/controller_manager/switch_controller
/controller_manager/unload_controller
```

User-reported loaded controllers:

```text
joint_state_controller:
  state: running
  type: joint_state_controller/JointStateController
```

User-reported available controller types include:

```text
position_controllers/JointTrajectoryController
position_controllers/JointGroupPositionController
effort_controllers/JointTrajectoryController
effort_controllers/JointGroupEffortController
```

Additional static read-only finding:

- `uvms_control/launch/oberon7_position_control.launch` loads the controller
  YAML into namespace `/oberon7`.
- The launch attempts to run the controller spawner under `<group ns="oberon7">`
  with args `arm_position_l arm_position_r`.
- Runtime controller-manager services observed by the user are global
  `/controller_manager/...`.
- No `/oberon7/controller_manager/...` service was reported.

Judgment:

```text
B2 is not resolved.
```

Interpretation:

- Candidate left-arm and gripper controller configurations are loaded as ROS
  params.
- Controller plugin types are available.
- The global controller manager is responsive.
- However, no left-arm or gripper controller is loaded/running, and no command
  or trajectory topics are available.
- The current launch does not provide a usable command interface for the left
  arm or gripper in its current runtime state.
- A likely cause is controller spawner namespace mismatch, but this needs one
  more read-only confirmation.

Does this require code changes now?

```text
No, not yet.
```

Reason:

- The next step should confirm exact namespace and parameter details before
  trying a runtime load/switch test or editing a launch file.
- No motion command should be sent until a controller is loaded and its command
  interface is identified.

Next minimal checks requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosservice list | grep -E "^/oberon7/controller_manager|^/controller_manager"
rosnode list | grep -E "spawner|controller|gazebo"
rosparam get /oberon7/arm_position_l/type
rosparam get /oberon7/arm_position_l/joints
rosparam get /oberon7/hand_position_l/type
rosparam get /oberon7/hand_position_l/joints
rosparam get /oberon7/arm_l_group_effort/type
rosparam get /oberon7/arm_l_group_effort/joints
```

Purpose:

- Confirm whether a namespaced `/oberon7/controller_manager` exists.
- Check whether the spawner node is still alive or has exited.
- Confirm exact left-arm and left-gripper controller type/joint configs.

Expected interpretation:

- If there is no `/oberon7/controller_manager`, the `<group ns="oberon7">`
  spawner likely targeted the wrong controller-manager namespace.
- If the controller parameters are valid, the next B2 step can be a non-motion
  runtime load check for one controller.
- If params are invalid, fix should focus on the controller config before any
  runtime loading attempt.

## Round 8: B2 Controller Namespace And Param Confirmation

Date: 2026-05-02

User commands:

```bash
rosservice list | grep -E "^/oberon7/controller_manager|^/controller_manager"
rosnode list | grep -E "spawner|controller|gazebo"
rosparam get /oberon7/arm_position_l/type
rosparam get /oberon7/arm_position_l/joints
rosparam get /oberon7/hand_position_l/type
rosparam get /oberon7/hand_position_l/joints
rosparam get /oberon7/arm_l_group_effort/type
rosparam get /oberon7/arm_l_group_effort/joints
```

User-reported service result:

```text
/controller_manager/list_controller_types
/controller_manager/list_controllers
/controller_manager/load_controller
/controller_manager/reload_controller_libraries
/controller_manager/switch_controller
/controller_manager/unload_controller
```

No `/oberon7/controller_manager/...` services were present.

User-reported node result:

```text
/gazebo
```

No spawner or controller node remained alive.

User-reported controller params:

```text
/oberon7/arm_position_l/type:
  position_controllers/JointTrajectoryController
/oberon7/arm_position_l/joints:
  - oberon7_l/azimuth
  - oberon7_l/shoulder
  - oberon7_l/elbow
  - oberon7_l/roll
  - oberon7_l/pitch
  - oberon7_l/wrist

/oberon7/hand_position_l/type:
  position_controllers/JointTrajectoryController
/oberon7/hand_position_l/joints:
  - oberon7_l/finger_left_joint
  - oberon7_l/finger_tip_left_joint
  - oberon7_l/finger_right_joint
  - oberon7_l/finger_tip_right_joint

/oberon7/arm_l_group_effort/type:
  effort_controllers/JointGroupEffortController
/oberon7/arm_l_group_effort/joints:
  - oberon7_l/azimuth
  - oberon7_l/shoulder
  - oberon7_l/elbow
  - oberon7_l/roll
  - oberon7_l/pitch
  - oberon7_l/wrist
```

Judgment:

```text
B2 remains open.
```

Interpretation:

- Controller parameters for left arm and left hand are complete enough to try
  controller loading.
- The available controller manager is global `/controller_manager`.
- The current launch's `<group ns="oberon7">` spawner likely targeted
  `/oberon7/controller_manager`, which does not exist, and then exited.
- This explains why controller params exist but no arm/hand controllers are
  loaded and no command topics exist.

Does this require code changes now?

```text
No, not yet.
```

Reason:

- The next safest step is a non-motion `load_controller` check through the
  global controller manager using the namespaced controller name.
- Loading a controller should instantiate it in stopped state and should not
  command motion. Do not start or switch it yet.

Next minimal check requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/load_controller "{name: 'oberon7/arm_position_l'}"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic list | grep -E "oberon7/arm_position_l|follow_joint|trajectory"
```

Purpose:

- Test whether the global controller manager can load the left-arm trajectory
  controller from `/oberon7/arm_position_l` parameters.
- Confirm whether it appears in `stopped` state.
- Inspect whether loading creates the expected trajectory/action topics.

Expected interpretation:

- If load returns `ok: True`, B2 progresses to identifying topics and later
  starting the controller safely.
- If load returns `ok: False`, the error will indicate whether the blocker is
  parameter namespace, controller type, or hardware-interface mismatch.
- Do not call `/controller_manager/switch_controller` yet.
- Do not publish to any command or trajectory topic yet.

## Round 10: B2 Left-Gripper Controller Load And Topic Type Check

Date: 2026-05-02

User commands:

```bash
timeout 5s rosservice call /controller_manager/load_controller "{name: 'oberon7/hand_position_l'}"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic list | grep -E "oberon7/(arm_position_l|hand_position_l)|follow_joint|trajectory"
rostopic info /oberon7/arm_position_l/command
rostopic info /oberon7/arm_position_l/follow_joint_trajectory/goal
rostopic info /oberon7/hand_position_l/command
rostopic info /oberon7/hand_position_l/follow_joint_trajectory/goal
```

User-reported load result:

```text
ok: True
```

User-reported controller list:

```text
oberon7/arm_position_l:
  state: initialized
  type: position_controllers/JointTrajectoryController
  hardware_interface: hardware_interface::PositionJointInterface

oberon7/hand_position_l:
  state: initialized
  type: position_controllers/JointTrajectoryController
  hardware_interface: hardware_interface::PositionJointInterface
```

User-reported topics:

```text
/oberon7/arm_position_l/command
/oberon7/arm_position_l/follow_joint_trajectory/*
/oberon7/arm_position_l/state
/oberon7/hand_position_l/command
/oberon7/hand_position_l/follow_joint_trajectory/*
/oberon7/hand_position_l/state
```

User-reported topic types:

```text
/oberon7/arm_position_l/command:
  trajectory_msgs/JointTrajectory
/oberon7/arm_position_l/follow_joint_trajectory/goal:
  control_msgs/FollowJointTrajectoryActionGoal
/oberon7/hand_position_l/command:
  trajectory_msgs/JointTrajectory
/oberon7/hand_position_l/follow_joint_trajectory/goal:
  control_msgs/FollowJointTrajectoryActionGoal
```

Judgment:

```text
B2 is partially resolved.
```

Resolved by this check:

- Left-arm trajectory controller can be loaded.
- Left-gripper trajectory controller can be loaded.
- Command and FollowJointTrajectory action topics are visible for both.
- Command topic message types are known.

Still open:

- Controllers are `initialized`, not running.
- No controller start has been tested.
- No safe/no-op trajectory has been sent.
- Real arm/gripper motion remains unverified.
- Existing `uvms_control/launch/oberon7_position_control.launch` still has a
  spawner namespace issue; do not edit it unless explicitly requested.

Code change made in project package:

```text
launch/load_left_controllers.launch
```

Purpose:

- Provide a package-local helper for the confirmed working controller-manager
  naming pattern.
- Default `start:=false` uses controller_manager spawner with `--stopped` for:
  - `oberon7/arm_position_l`
  - `oberon7/hand_position_l`
- It does not start controllers and does not send any command.

Verification performed:

```text
XML parse: passed
roslaunch --ros-args: passed
```

Next minimal check requested from user:

Start from a clean simulation where these controllers are not already loaded,
then run:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
roslaunch rexrov_single_oberon7_fm_dp load_left_controllers.launch start:=false
timeout 5s rosservice call /controller_manager/list_controllers "{}"
```

Purpose:

- Confirm the package-local helper reproduces the manual stopped-load result.

Expected interpretation:

- `oberon7/arm_position_l` and `oberon7/hand_position_l` should be present and
  not running.
- If this passes, the next B2 step can be a carefully isolated start-only check.
- Do not publish a trajectory yet.

## Round 11: B2 Package-Local Stopped Loader Check

Date: 2026-05-02

User command:

```bash
roslaunch rexrov_single_oberon7_fm_dp load_left_controllers.launch start:=false
```

User-reported launch output:

```text
Loading controller: oberon7/arm_position_l
Loading controller: oberon7/hand_position_l
Controller Spawner: Loaded controllers: oberon7/arm_position_l, oberon7/hand_position_l
```

User-reported controller list:

```text
joint_state_controller:
  state: running

oberon7/arm_position_l:
  state: initialized
  type: position_controllers/JointTrajectoryController

oberon7/hand_position_l:
  state: initialized
  type: position_controllers/JointTrajectoryController
```

Judgment:

```text
Package-local stopped loader works.
B2 remains partially resolved.
```

Resolved by this check:

- `launch/load_left_controllers.launch start:=false` reproduces the manual
  stopped-load behavior.
- The helper launch uses the confirmed global controller manager naming pattern.
- Both left-arm and left-gripper controllers can be loaded without starting or
  commanding motion.

Still open:

- Controllers are still `initialized`, not `running`.
- No start-only check has been run.
- No no-op trajectory has been sent.
- Real arm/gripper motion remains unverified.

Does this require code changes now?

```text
No.
```

Reason:

- The helper launch works as intended.
- Next step should be a start-only controller check without publishing a
  trajectory.

Next minimal check requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/switch_controller \
  "{start_controllers: ['oberon7/arm_position_l', 'oberon7/hand_position_l'], stop_controllers: [], strictness: 2, start_asap: false, timeout: 5.0}"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /oberon7/hand_position_l/state
```

Purpose:

- Confirm both controllers can transition to `running`.
- Confirm controller state topics publish after start.
- This still does not send arm or gripper trajectories.

Expected interpretation:

- If `switch_controller` returns `ok: True` and both controllers are running,
  B2 can proceed to a later no-op trajectory test.
- If `switch_controller` fails, do not publish commands; inspect the failure
  first.

## Round 12: B2 Start-Only Controller Check

Date: 2026-05-02

User command:

```bash
timeout 5s rosservice call /controller_manager/switch_controller \
  "{start_controllers: ['oberon7/arm_position_l', 'oberon7/hand_position_l'], stop_controllers: [], strictness: 2, start_asap: false, timeout: 5.0}"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /oberon7/hand_position_l/state
```

User-reported switch result:

```text
ok: True
```

User-reported controller list:

```text
oberon7/arm_position_l:
  state: running
  type: position_controllers/JointTrajectoryController

oberon7/hand_position_l:
  state: running
  type: position_controllers/JointTrajectoryController
```

User-reported arm state:

```text
joint_names:
  - oberon7_l/azimuth
  - oberon7_l/shoulder
  - oberon7_l/elbow
  - oberon7_l/roll
  - oberon7_l/pitch
  - oberon7_l/wrist
desired positions: close to actual positions
actual velocities: small but nonzero
```

User-reported gripper state:

```text
joint_names:
  - oberon7_l/finger_left_joint
  - oberon7_l/finger_tip_left_joint
  - oberon7_l/finger_right_joint
  - oberon7_l/finger_tip_right_joint
desired positions:
  [-0.1337, 0.0400, -0.2049, 0.0564]
actual positions:
  [0.0027, -0.0028, 0.0012, -0.0005]
actual velocities:
  [1.0738, -0.9321, 0.5957, -0.2389]
```

Judgment:

```text
B2 is still partially resolved.
```

Resolved by this check:

- Both left-arm and left-gripper controllers can transition to `running`.
- Both controller state topics publish.
- The ROS command interface is now present at the controller/action-topic level.

Still open:

- No trajectory command has been tested.
- No no-op hold command has been tested.
- Real arm/gripper command execution is not verified.
- The gripper start-only state is not a clean passive no-op: desired and actual
  positions differ substantially and velocities are nontrivial.

Safety interpretation:

- Do not publish a no-op trajectory immediately after this observation.
- First re-check state after a short wait to see whether the gripper controller
  settles.
- If gripper error/velocity remains large, consider stopping the gripper
  controller before any further command tests, or design a hold command from
  current joint states.

Does this require code changes now?

```text
No.
```

Reason:

- This is runtime behavior that should be characterized with another read-only
  state sample before adding or changing command code.

Next minimal check requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
sleep 3
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /oberon7/hand_position_l/state
rostopic echo -n 1 /joint_states
```

Purpose:

- Check whether the running controllers settle after start-only.
- Compare gripper desired/actual/error/velocity after a short delay.
- Confirm current joint states before deciding whether a no-op trajectory test
  is safe.

Expected interpretation:

- If velocities and errors settle near zero, the next B2 step can be a carefully
  constructed hold/no-op trajectory using current joint positions.
- If gripper velocities/errors remain large, avoid sending new commands and
  stop or isolate the gripper controller first.

## Round 13: B2 Running Controller Stability Recheck

Date: 2026-05-02

User command:

```bash
sleep 3
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /oberon7/hand_position_l/state
rostopic echo -n 1 /joint_states
```

User-reported arm state after waiting:

```text
desired and actual positions remain close
example position errors:
  azimuth: about -3.1e-06
  shoulder: about 4.4e-06
  elbow: about 2.0e-05
  pitch: about -5.2e-05
actual velocities remain small but nonzero
```

User-reported gripper state after waiting:

```text
desired positions:
  [-0.1337, 0.0400, -0.2049, 0.0564]
actual positions:
  [0.0029, -0.0029, 0.0014, -0.0007]
position errors:
  [-0.1366, 0.0429, -0.2064, 0.0571]
actual velocities:
  [1.1298, -0.9804, 0.6553, -0.2585]
```

User-reported `/joint_states` agrees with the gripper concern:

```text
oberon7_l/finger_left_joint velocity: about 1.17
oberon7_l/finger_right_joint velocity: about 0.51
oberon7_l/finger_tip_left_joint velocity: about -1.02
oberon7_l/finger_tip_right_joint velocity: about -0.17
```

Judgment:

```text
B2 is not fully resolved.
```

Resolved by this check:

- The left-arm trajectory controller can run and appears stable in a
  start-only condition.
- The left-arm controller state topic is usable.

Still open:

- The left-gripper trajectory controller does not settle after start-only.
- The gripper desired state is far from actual state.
- The gripper joints continue moving with large velocities after waiting.
- No trajectory command has been tested.
- Real gripper command execution is unsafe to test in this condition.

Safety interpretation:

- Do not publish a gripper trajectory yet.
- Do not publish an arm no-op trajectory while the gripper controller is still
  actively driving unsettled finger joints.
- The next check should stop only the gripper controller and verify that the
  arm controller can remain running.

Does this require code changes now?

```text
No.
```

Reason:

- The immediate issue is runtime controller behavior, not package code.
- The package-local helper launch already loads controllers safely with
  `start:=false`.
- The next step should be another minimal controller-manager check, not an
  implementation change.

Next minimal check requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/switch_controller \
  "{start_controllers: [], stop_controllers: ['oberon7/hand_position_l'], strictness: 2, start_asap: false, timeout: 5.0}"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
sleep 2
rostopic echo -n 1 /joint_states
rostopic echo -n 1 /oberon7/arm_position_l/state
```

Purpose:

- Stop the left-gripper trajectory controller that is showing unsafe behavior.
- Leave the left-arm controller running.
- Confirm gripper joint velocities reduce after the gripper controller stops.
- Confirm the arm controller remains healthy before any later no-op trajectory
  or hold-command test.

## Round 9: B2 Left-Arm Controller Non-Motion Load Check

Date: 2026-05-02

User commands:

```bash
timeout 5s rosservice call /controller_manager/load_controller "{name: 'oberon7/arm_position_l'}"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic list | grep -E "oberon7/arm_position_l|follow_joint|trajectory"
```

User-reported load result:

```text
ok: True
```

User-reported controller list:

```text
joint_state_controller:
  state: running
  type: joint_state_controller/JointStateController

oberon7/arm_position_l:
  state: initialized
  type: position_controllers/JointTrajectoryController
  claimed_resources:
    hardware_interface: hardware_interface::PositionJointInterface
    resources:
      - oberon7_l/azimuth
      - oberon7_l/elbow
      - oberon7_l/pitch
      - oberon7_l/roll
      - oberon7_l/shoulder
      - oberon7_l/wrist
```

User-reported left-arm topics:

```text
/oberon7/arm_position_l/command
/oberon7/arm_position_l/follow_joint_trajectory/cancel
/oberon7/arm_position_l/follow_joint_trajectory/feedback
/oberon7/arm_position_l/follow_joint_trajectory/goal
/oberon7/arm_position_l/follow_joint_trajectory/result
/oberon7/arm_position_l/follow_joint_trajectory/status
/oberon7/arm_position_l/state
```

Judgment:

```text
B2 is partially resolved.
```

Resolved by this check:

- The global controller manager can load the namespaced left-arm trajectory
  controller from `/oberon7/arm_position_l` parameters.
- The left-arm command and `follow_joint_trajectory` topics are now visible.
- The namespace mismatch diagnosis is confirmed: using
  `oberon7/arm_position_l` with global `/controller_manager/load_controller`
  works.

Still open:

- `oberon7/arm_position_l` is `initialized`, not `running`.
- No trajectory has been sent.
- The left-gripper controller has not been loaded or inspected.
- The exact ROS message types for `/command` and action goal topics have not
  been recorded.
- Real arm/gripper motion is still unverified.

Does this require code changes now?

```text
No.
```

Reason:

- The runtime controller can be loaded using existing params and services.
- Next checks should remain non-motion: load the gripper controller and inspect
  topic types.

Next minimal checks requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/load_controller "{name: 'oberon7/hand_position_l'}"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic list | grep -E "oberon7/(arm_position_l|hand_position_l)|follow_joint|trajectory"
rostopic info /oberon7/arm_position_l/command
rostopic info /oberon7/arm_position_l/follow_joint_trajectory/goal
rostopic info /oberon7/hand_position_l/command
rostopic info /oberon7/hand_position_l/follow_joint_trajectory/goal
```

Purpose:

- Verify that the left gripper trajectory controller can also be loaded without
  starting it.
- Record command/action goal topic types needed for future action-converter and
  safe start tests.

Expected interpretation:

- If `hand_position_l` load returns `ok: True`, B2 has loadable left-arm and
  left-gripper controllers.
- If topic types are `trajectory_msgs/JointTrajectory` and
  `control_msgs/FollowJointTrajectoryActionGoal`, the command interface shape is
  clear enough for a later safe start/no-op trajectory test.
- Do not call `/controller_manager/switch_controller` yet.
- Do not publish to any command or trajectory topic yet.

## Round 14: B2 Stop Gripper Controller And Recheck State

Date: 2026-05-02

User command:

```bash
timeout 5s rosservice call /controller_manager/switch_controller \
  "{start_controllers: [], stop_controllers: ['oberon7/hand_position_l'], strictness: 2, start_asap: false, timeout: 5.0}"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
sleep 2
rostopic echo -n 1 /joint_states
rostopic echo -n 1 /oberon7/arm_position_l/state
```

User-reported switch result:

```text
ok: True
```

User-reported controller states:

```text
joint_state_controller: running
oberon7/arm_position_l: running
oberon7/hand_position_l: stopped
```

User-reported left gripper velocities from `/joint_states` after stopping the
hand controller and waiting about 2 seconds:

```text
oberon7_l/finger_left_joint: about 1.00
oberon7_l/finger_right_joint: about 0.47
oberon7_l/finger_tip_left_joint: about -0.90
oberon7_l/finger_tip_right_joint: about -0.09
```

User-reported arm controller state after stopping the hand controller:

```text
desired and actual arm positions remain close
position errors are on the order of 1e-06 to 3e-05
arm actual velocities are small
```

Judgment:

```text
B2 is still not fully resolved.
```

Resolved by this check:

- The left hand trajectory controller can be stopped cleanly through
  `/controller_manager/switch_controller`.
- The left arm trajectory controller can remain running while the left hand
  controller is stopped.
- The left arm still appears stable after stopping the hand controller.

Still open:

- Left gripper joints continue to show large velocities even after the hand
  trajectory controller is stopped.
- No trajectory command has been tested.
- Real gripper command execution remains unsafe to test.
- The source of gripper motion is not yet isolated. It may be physics/model
  behavior, stale desired state effects before stop, joint coupling, contact, or
  another controller/config path.

Does this require code changes now?

```text
No.
```

Reason:

- The current evidence is still runtime behavior, not a project-package code
  defect.
- The next step should remain read-only: confirm no hand command publishers and
  observe whether gripper velocity decays with the hand controller stopped.

Next minimal check requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic info /oberon7/hand_position_l/command
rostopic info /oberon7/hand_position_l/follow_joint_trajectory/goal
sleep 5
rostopic echo -n 1 /joint_states
rostopic echo -n 1 /oberon7/arm_position_l/state
```

Purpose:

- Confirm `oberon7/hand_position_l` remains stopped.
- Confirm there are no unexpected publishers on hand command/action-goal topics.
- Check whether gripper joint velocities decay after a longer wait with the
  hand controller stopped.
- Confirm the arm controller remains healthy.

Expected interpretation:

- If hand command topics have no publishers and gripper velocities decay, the
  next safe B2 step can be an arm-only no-op trajectory test.
- If hand command topics have publishers, identify and stop that publisher
  before any command test.
- If gripper velocities remain large without publishers and with the hand
  controller stopped, debug gripper model/controller configuration before
  attempting gripper motion.

## Round 15: B2 Stopped Gripper Publisher And Decay Check

Date: 2026-05-02

User command:

```bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic info /oberon7/hand_position_l/command
rostopic info /oberon7/hand_position_l/follow_joint_trajectory/goal
sleep 5
rostopic echo -n 1 /joint_states
rostopic echo -n 1 /oberon7/arm_position_l/state
```

User-reported controller states:

```text
joint_state_controller: running
oberon7/arm_position_l: running
oberon7/hand_position_l: stopped
```

User-reported hand command topics:

```text
/oberon7/hand_position_l/command:
  type: trajectory_msgs/JointTrajectory
  publishers: None
  subscriber: /gazebo

/oberon7/hand_position_l/follow_joint_trajectory/goal:
  type: control_msgs/FollowJointTrajectoryActionGoal
  publishers: None
  subscriber: /gazebo
```

User-reported left gripper velocities after waiting 5 seconds with the hand
controller stopped:

```text
oberon7_l/finger_left_joint: about 1.01
oberon7_l/finger_right_joint: about 0.48
oberon7_l/finger_tip_left_joint: about -0.92
oberon7_l/finger_tip_right_joint: about -0.16
```

User-reported right gripper velocities from the same `/joint_states` sample:

```text
oberon7_r/finger_left_joint: about -0.36
oberon7_r/finger_right_joint: about -0.65
oberon7_r/finger_tip_left_joint: about 0.11
oberon7_r/finger_tip_right_joint: about 0.28
```

User-reported arm controller state:

```text
desired and actual arm positions remain close
position errors remain around 1e-06 to 3e-05
arm remains stable
```

Judgment:

```text
B2 remains partially resolved, not fully resolved.
```

Resolved by this check:

- There are no publishers on the left hand command or FollowJointTrajectory
  goal topics.
- `oberon7/hand_position_l` remains stopped.
- `oberon7/arm_position_l` remains running and stable.

Still open:

- Left gripper joint velocities remain large with the hand controller stopped
  and no hand command publishers.
- Right gripper joint velocities are also substantial without a loaded right
  hand controller.
- This points away from an active left hand command publisher and toward
  model/physics/uncontrolled-joint behavior or a controller startup side effect.
- Gripper command execution is still unsafe to test.

Does this require code changes now?

```text
No.
```

Reason:

- The evidence still indicates a runtime/model/control configuration issue,
  not a defect in the project package code.
- Before modifying package launch or command code, isolate whether the gripper
  motion exists in a clean baseline with no arm/hand controllers loaded.

Next minimal check requested from user:

Start a clean simulation, then before loading or starting any left arm/hand
controllers run:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic echo -n 1 /joint_states
```

Purpose:

- Confirm whether only `joint_state_controller` is running in the clean
  baseline.
- Check whether left and right gripper velocities are already large before any
  `oberon7/arm_position_l` or `oberon7/hand_position_l` load/start.

Expected interpretation:

- If gripper velocities are already large in the clean baseline, classify the
  gripper as a model/physics/uncontrolled-joint blocker. Then B2 can proceed
  separately with arm-only command verification while gripper execution remains
  blocked.
- If gripper velocities are near zero in the clean baseline, the previous
  gripper instability was introduced by the hand-controller lifecycle and the
  next debug target should be hand-controller startup behavior.

## Round 16: B2 Clean-Baseline Gripper Check

Date: 2026-05-02

User context:

```text
fresh simulation
gui:=false paused:=false
no arm_position_l or hand_position_l load/start performed
```

User command:

```bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic echo -n 1 /joint_states
```

User-reported controller list:

```text
joint_state_controller:
  state: running
```

No left or right arm/hand trajectory controllers were loaded or running.

User-reported clean-baseline gripper velocities:

```text
oberon7_l/finger_left_joint: about -0.477
oberon7_l/finger_right_joint: about -0.652
oberon7_l/finger_tip_left_joint: about 0.219
oberon7_l/finger_tip_right_joint: about 0.277

oberon7_r/finger_left_joint: about -0.477
oberon7_r/finger_right_joint: about -0.652
oberon7_r/finger_tip_left_joint: about 0.219
oberon7_r/finger_tip_right_joint: about 0.277
```

Judgment:

```text
B2 remains partially resolved, but the gripper subpath is now classified as a
baseline model/physics/uncontrolled-joint blocker.
```

Resolved by this check:

- The gripper motion exists before any project-package arm or hand controller
  is loaded or started.
- The motion is symmetric on left and right grippers.
- The source is not a publisher to the left hand command topic and is not caused
  by starting/stopping `oberon7/hand_position_l`.
- The arm command-interface subpath can be debugged separately as arm-only.

Still open:

- Real gripper command execution remains blocked.
- Real grasp success cannot be evaluated until gripper control is made stable
  or the first task is explicitly changed to arm-only contact/positioning.
- No trajectory command has been tested for the left arm yet.

Does this require code changes now?

```text
No.
```

Reason:

- The finding is in the clean baseline simulation before this project package
  starts any arm/hand controller.
- We should not edit official DAVE/UUV/uvms packages in this debug loop.
- The project package can continue B2 with an arm-only command test while
  documenting gripper execution as blocked.

Next minimal check requested from user:

Use the fresh simulation if it still has only `joint_state_controller` running.
Load and start only the left-arm controller; do not load or start any hand
controller:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/load_controller "{name: 'oberon7/arm_position_l'}"
timeout 5s rosservice call /controller_manager/switch_controller \
  "{start_controllers: ['oberon7/arm_position_l'], stop_controllers: [], strictness: 2, start_asap: false, timeout: 5.0}"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic info /oberon7/arm_position_l/command
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
```

Purpose:

- Verify the left-arm command path in isolation.
- Keep both hand controllers unloaded/stopped.
- Collect current arm controller state that can be used for a later arm-only
  no-op trajectory command.

Expected interpretation:

- If `oberon7/arm_position_l` becomes `running`, the command topic has Gazebo
  as subscriber, and arm desired/actual remain close, proceed next to a
  current-position arm-only no-op trajectory test.
- If starting the arm controller changes gripper behavior, note it but keep
  gripper execution blocked.

## Round 17: B2 Arm-Only Controller Start Check

Date: 2026-05-02

User context:

```text
fresh simulation
gui:=false paused:=false
hand controllers not loaded or started
```

User command:

```bash
timeout 5s rosservice call /controller_manager/load_controller "{name: 'oberon7/arm_position_l'}"
timeout 5s rosservice call /controller_manager/switch_controller \
  "{start_controllers: ['oberon7/arm_position_l'], stop_controllers: [], strictness: 2, start_asap: false, timeout: 5.0}"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic info /oberon7/arm_position_l/command
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
```

User-reported load and start results:

```text
load_controller: ok: True
switch_controller: ok: True
```

User-reported controller list:

```text
joint_state_controller: running
oberon7/arm_position_l: running
```

No `oberon7/hand_position_l` controller was loaded or running.

User-reported command topic:

```text
/oberon7/arm_position_l/command:
  type: trajectory_msgs/JointTrajectory
  publishers: None
  subscriber: /gazebo
```

User-reported arm controller state:

```text
joint_names:
  - oberon7_l/azimuth
  - oberon7_l/shoulder
  - oberon7_l/elbow
  - oberon7_l/roll
  - oberon7_l/pitch
  - oberon7_l/wrist
desired and actual positions are close
largest reported position error: about 9.6e-05 rad on pitch
reported pitch velocity: about 0.048 rad/s
```

User-reported `/joint_states`:

- Left arm joints are present.
- Gripper joints still show substantial baseline motion, as expected from Round
  16.
- Right gripper joints also continue to move, so gripper execution remains
  blocked.

Judgment:

```text
B2 remains partially resolved.
```

Resolved by this check:

- Left-arm trajectory controller can be loaded alone.
- Left-arm trajectory controller can be started alone.
- Left-arm command topic exists and Gazebo subscribes to it.
- Hand controllers can remain unloaded while testing the arm path.

Still open:

- No trajectory command has been published yet.
- The arm state should be checked once more after a short wait because the first
  sample still has nonzero velocities.
- Gripper command execution remains blocked by baseline gripper joint motion.

Does this require code changes now?

```text
No.
```

Reason:

- Existing runtime controller services and topics are enough to continue
  arm-only verification.
- The next step should still be read-only: confirm arm state settles before
  publishing a current-position no-op trajectory.

Next minimal check requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
sleep 3
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
```

Purpose:

- Confirm `oberon7/arm_position_l` remains running.
- Confirm no hand controller was loaded.
- Confirm desired/actual arm positions remain close.
- Capture current arm positions for the next possible current-position no-op
  trajectory command.

Expected interpretation:

- If arm errors remain small and velocities are not growing, the next step can
  publish a single arm-only no-op `JointTrajectory` using the latest actual
  positions.
- If arm velocities or errors grow, do not publish a trajectory; continue
  controller stability debugging.

## Round 18: B2 Arm-Only Settle Check

Date: 2026-05-02

User context:

```text
fresh simulation
oberon7/arm_position_l running
hand controllers not loaded or started
```

User command:

```bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
sleep 3
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
```

User-reported controller list:

```text
joint_state_controller: running
oberon7/arm_position_l: running
```

No hand controller was loaded or running.

User-reported arm controller state after waiting:

```text
desired positions:
  [0.0003426965, 0.0048252137, 0.0052532439, 0.0004994372, 0.0119618380, 0.0021839831]
actual positions:
  [0.0003372278, 0.0048185449, 0.0052512543, 0.0004992199, 0.0119498140, 0.0021815869]
position errors:
  about 2.2e-07 to 1.2e-05 rad
actual velocities:
  [-0.00136, -0.00331, -0.00099, -0.000002, -0.00601, -0.000088]
```

Judgment:

```text
B2 remains partially resolved, but the arm-only path is ready for the first
no-op trajectory command.
```

Resolved by this check:

- `oberon7/arm_position_l` remains running.
- Arm desired and actual positions remain close.
- Arm velocities are small and lower than the earlier first sample.
- Current arm positions are available for a current-position no-op
  `JointTrajectory`.

Still open:

- No trajectory command has been published yet.
- Gripper command execution remains blocked by baseline gripper motion.

Does this require code changes now?

```text
No.
```

Reason:

- The next step can use existing ROS command topic and a single manually
  constructed `trajectory_msgs/JointTrajectory`.
- No package code is needed for this one-shot no-op execution test.

Next minimal check requested from user:

This is the first non-read-only arm command test. It publishes the current arm
position back to the running arm trajectory controller and should not create
visible motion. Do not load or start either hand controller.

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic pub -1 /oberon7/arm_position_l/command trajectory_msgs/JointTrajectory \
  "{joint_names: ['oberon7_l/azimuth', 'oberon7_l/shoulder', 'oberon7_l/elbow', 'oberon7_l/roll', 'oberon7_l/pitch', 'oberon7_l/wrist'], points: [{positions: [0.00033722783914313936, 0.004818544882332354, 0.005251254292496732, 0.000499219910508053, 0.011949814043682672, 0.0021815869327630466], velocities: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], time_from_start: {secs: 2, nsecs: 0}}]}"
sleep 2
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
```

Purpose:

- Confirm Gazebo/controller accepts an arm-only `JointTrajectory` command.
- Verify a current-position no-op command does not destabilize the arm.
- Keep gripper execution out of the test.

Expected interpretation:

- If `rostopic pub` exits normally and arm desired/actual remain close after
  the command, the arm topic execution path is confirmed for hold/no-op
  commands.
- If arm state jumps, errors grow, or controller state changes unexpectedly,
  stop further command tests and debug the trajectory command shape/timing.

## Round 19: B2 Arm-Only Current-Position No-Op Command

Date: 2026-05-02

User command:

```bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic pub -1 /oberon7/arm_position_l/command trajectory_msgs/JointTrajectory \
  "{joint_names: ['oberon7_l/azimuth', 'oberon7_l/shoulder', 'oberon7_l/elbow', 'oberon7_l/roll', 'oberon7_l/pitch', 'oberon7_l/wrist'], points: [{positions: [0.00033722783914313936, 0.004818544882332354, 0.005251254292496732, 0.000499219910508053, 0.011949814043682672, 0.0021815869327630466], velocities: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], time_from_start: {secs: 2, nsecs: 0}}]}"
sleep 2
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
```

User-reported controller list before command:

```text
joint_state_controller: running
oberon7/arm_position_l: running
```

User-reported publish result:

```text
publishing and latching message for 3.0 seconds
```

User-reported arm controller state after the no-op command:

```text
desired positions match commanded positions:
  [0.0003372278, 0.0048185449, 0.0052512543, 0.0004992199, 0.0119498140, 0.0021815869]
actual positions:
  [0.0003340931, 0.0048386354, 0.0052473891, 0.0005016475, 0.0119798646, 0.0022069553]
position errors:
  about 2.4e-06 to 3.0e-05 rad
actual velocities:
  about -0.0019, 0.0101, -0.0020, 0.0015, 0.0151, 0.0122 rad/s
```

Judgment:

```text
B2 remains partially resolved, but the left-arm topic execution path is now
confirmed for current-position hold/no-op commands.
```

Resolved by this check:

- `rostopic pub` to `/oberon7/arm_position_l/command` completed normally.
- The arm controller accepted the command: desired positions updated to the
  command values.
- Actual positions remained close to desired after the command.
- The arm did not show a large jump or obvious instability.

Still open:

- A nonzero arm command has not been tested yet, so actual arm motion is not
  fully confirmed.
- Gripper command execution remains blocked by clean-baseline gripper motion.
- Real grasp success cannot be evaluated.

Does this require code changes now?

```text
No.
```

Reason:

- The one-shot command path works through existing ROS topics.
- The next step can remain a manual tiny joint-space command; no package code is
  needed yet.

Next minimal check requested from user:

This is a tiny nonzero arm-only command. It offsets the latest measured shoulder
position by about `+0.001 rad`. Do not load or start either hand controller.

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic pub -1 /oberon7/arm_position_l/command trajectory_msgs/JointTrajectory \
  "{joint_names: ['oberon7_l/azimuth', 'oberon7_l/shoulder', 'oberon7_l/elbow', 'oberon7_l/roll', 'oberon7_l/pitch', 'oberon7_l/wrist'], points: [{positions: [0.0003340930631443584, 0.005838635435847394, 0.0052473890709681115, 0.0005016475274404186, 0.01197986462830869, 0.0022069553168027056], velocities: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], time_from_start: {secs: 3, nsecs: 0}}]}"
sleep 3
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
```

Purpose:

- Confirm the arm command path can produce a small intentional joint movement.
- Keep the test isolated from gripper execution.

Expected interpretation:

- Desired shoulder should update to about `0.0058386354`.
- Actual shoulder should move toward that target without large errors or
  unstable velocities.
- If this passes, left-arm joint-space command execution is confirmed at a
  minimal level.

## Round 20: B2 Tiny Nonzero Arm-Only Command

Date: 2026-05-02

User command:

```bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic pub -1 /oberon7/arm_position_l/command trajectory_msgs/JointTrajectory \
  "{joint_names: ['oberon7_l/azimuth', 'oberon7_l/shoulder', 'oberon7_l/elbow', 'oberon7_l/roll', 'oberon7_l/pitch', 'oberon7_l/wrist'], points: [{positions: [0.0003340930631443584, 0.005838635435847394, 0.0052473890709681115, 0.0005016475274404186, 0.01197986462830869, 0.0022069553168027056], velocities: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], time_from_start: {secs: 3, nsecs: 0}}]}"
sleep 3
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
```

User-reported controller list before command:

```text
joint_state_controller: running
oberon7/arm_position_l: running
```

User-reported publish result:

```text
publishing and latching message for 3.0 seconds
```

User-reported arm controller state after command:

```text
desired positions:
  [0.0003340931, 0.0058386354, 0.0052473891, 0.0005016475, 0.0119798646, 0.0022069553]
actual positions:
  [0.0003483646, 0.0058774165, 0.0052712601, 0.0005038745, 0.0120713652, 0.0022485447]
position errors:
  about -1.4e-05, -3.9e-05, -2.4e-05, -2.2e-06, -9.2e-05, -4.2e-05 rad
actual velocities:
  about -0.00015, 0.0194, 0.0119, 0.00070, 0.0468, 0.0057 rad/s
```

User-reported `/joint_states`:

- Left shoulder joint position was near `0.0058462`, close to the commanded
  shoulder target `0.0058386`.
- Gripper joints still show baseline motion and remain out of scope for this
  arm-only command test.

Judgment:

```text
B2 remains partially resolved, but minimal left-arm joint-space command
execution is now confirmed.
```

Resolved by this check:

- A tiny nonzero arm-only `JointTrajectory` was accepted by the controller.
- The controller desired positions updated to the commanded positions.
- The actual shoulder position moved to the commanded neighborhood.
- Arm errors stayed small, below about `1e-04` rad in the first post-command
  sample.

Still open:

- Arm velocities are nonzero in the first post-command sample, so perform one
  settle check before declaring the left-arm joint-space command subpath
  resolved at minimal level.
- Gripper command execution remains blocked by baseline gripper motion.
- End-effector delta action conversion is not yet verified; this only confirms
  low-level joint-space arm command execution.

Does this require code changes now?

```text
No.
```

Reason:

- The manual command path is enough to validate minimal arm execution.
- A package-level action converter can be updated later after the command
  interface is documented and stable.

Next minimal check requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
sleep 5
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
```

Purpose:

- Confirm `oberon7/arm_position_l` remains running after the tiny nonzero
  command.
- Confirm desired/actual positions remain close.
- Check whether arm velocities decay or remain bounded after the movement.

Expected interpretation:

- If errors remain small and velocities settle, mark the left-arm joint-space
  command subpath resolved at minimal level.
- If velocities grow or errors increase, continue arm controller stability
  debugging before adding package code.

## Round 21: B2 Post-Motion Arm Settle Check

Date: 2026-05-02

User command:

```bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
sleep 5
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
```

User-reported controller list:

```text
joint_state_controller: running
oberon7/arm_position_l: running
```

No hand controller was reported loaded or running.

User-reported arm controller state after waiting:

```text
desired positions:
  [0.0003340931, 0.0058386354, 0.0052473891, 0.0005016475, 0.0119798646, 0.0022069553]
actual positions:
  [0.0003548056, 0.0058788229, 0.0052715412, 0.0005041377, 0.0119837345, 0.0022580568]
position errors:
  about -2.1e-05, -4.0e-05, -2.4e-05, -2.5e-06, -3.9e-06, -5.1e-05 rad
actual velocities:
  about 0.0025, 0.0201, 0.0121, 0.00083, 0.0027, 0.0049 rad/s
```

User-reported `/joint_states`:

- Left shoulder joint position remained near `0.0058461`, close to commanded
  shoulder target `0.0058386`.
- Left arm joint velocities in `/joint_states` remained bounded.
- Gripper joints still showed clean-baseline motion and remain blocked.

Judgment:

```text
Left-arm joint-space command execution is minimally resolved for B2.
B2 as a whole remains partially resolved because gripper execution is blocked.
```

Resolved by this check:

- `oberon7/arm_position_l` remained running after no-op and tiny nonzero
  trajectory commands.
- Desired and actual arm positions remained close after the tiny nonzero
  command.
- The arm did not show growing error or instability in the post-motion settle
  check.
- Minimal left-arm joint-space command execution through
  `/oberon7/arm_position_l/command` is confirmed.

Still open:

- Gripper command execution remains blocked by clean-baseline gripper motion.
- End-effector pose / TF is not yet verified.
- End-effector delta action conversion is not yet verified.
- Real grasp success rate cannot be evaluated.

Does this require code changes now?

```text
No.
```

Reason:

- B2 left-arm joint-space command path is sufficiently characterized for the
  current debug level.
- The next blocker for policy/evaluation progress is B3: `eef_pose` / TF
  availability.

Next minimal check requested from user:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosrun tf view_frames
rosrun tf tf_echo rexrov/base_link oberon7_l/end_effector
```

Purpose:

- Generate a TF frame report.
- Check whether the configured left end-effector frame
  `oberon7_l/end_effector` exists.
- Check whether a transform from `rexrov/base_link` to the left eef frame can
  be queried.

Expected interpretation:

- If `tf_echo` prints a transform, B3 can proceed to recorder integration for
  `eef_pose`.
- If it reports missing frames, inspect the frame report and identify the actual
  left endpoint frame name.

## Round 22: B3 TF Frame And Recorder Integration

Date: 2026-05-03

User context:

```text
gui:=false paused:=false
source devel/setup.bash already executed
```

User commands:

```bash
rosrun tf view_frames
rosrun tf tf_echo rexrov/base_link oberon7_l/end_effector
```

User-reported `view_frames` result:

```text
Listening to /tf for 5.0 seconds
Done Listening
frames.pdf generated
```

User-reported `tf_echo` result:

```text
At time 4565.654 and later:
Translation: [2.071, 0.500, -1.310]
Quaternion: [0.506, 0.494, -0.495, 0.505]
RPY degree: [90.140, 88.676, about 0.004]
```

Judgment:

```text
B3 is partially resolved.
```

Resolved by this check:

- The configured left end-effector frame `oberon7_l/end_effector` exists in the
  runtime TF tree.
- A transform from `rexrov/base_link` to `oberon7_l/end_effector` is available
  and publishes continuously.
- The configured frame name in `config/active_joints_left_arm.yaml` and
  `config/topics.yaml` is therefore valid for the current minimal launch.

Code changes made in the project package:

```text
src/rexrov_single_oberon7_fm_dp/recorder.py
package.xml
CMakeLists.txt
```

Implementation details:

- `EpisodeRecorder` now creates a ROS TF listener by default.
- New recorder parameters:
  - `~enable_tf_eef_pose`, default `true`
  - `~eef_link`, default `oberon7_l/end_effector`
  - `~eef_pose_reference_frame`, default `world`
  - `~base_link_frame`, default `rexrov/base_link`
  - `~tf_eef_wait_sec`, default `2.0`
  - `~require_eef_pose`, default `false`
- Each sample now attempts `TF(reference_frame -> eef_link)`.
- If direct `world -> eef_link` TF is unavailable, the recorder can compose
  `/rexrov/pose_gt` world base pose with the verified
  `rexrov/base_link -> oberon7_l/end_effector` TF.
- If TF lookup succeeds:
  - `eef_pose` is filled as `[x, y, z, qx, qy, qz, qw]`.
  - `relative_target_to_eef` is filled as `target_position - eef_position`
    when target pose is also finite.
  - metadata records `eef_pose_source`.
- If TF lookup fails, the recorder keeps the previous safe behavior and writes
  NaN for `eef_pose` and `relative_target_to_eef`.
- `tf` was added as a package dependency in `package.xml` and `CMakeLists.txt`.

Verification performed locally:

```text
python3 -m py_compile .../recorder.py: passed
catkin build rexrov_single_oberon7_fm_dp: passed
```

Still open:

- The recorder TF write path has not yet been validated in a live `.npz`
  episode.
- Real grasp success is still not evaluable because gripper execution remains
  blocked.
- Policy/expert actions still do not drive a full grasp loop.

Does this require more code changes now?

```text
No.
```

Reason:

- The missing implementation for B3 was added.
- The next step should be a short runtime recorder smoke test, not more code.

Next minimal check requested from user:

First confirm the target exists. If `cylinder_target` is missing, spawn it using
the same package-local SDF command from B1. Then run:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosservice call /gazebo/get_model_state "{model_name: 'cylinder_target', relative_entity_name: 'world'}"
roslaunch rexrov_single_oberon7_fm_dp record_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw \
  episode_id:=b3_eef_tf_smoke \
  rate_hz:=2.0 \
  max_duration_sec:=2.0 \
  require_target:=true \
  target_model_name:=cylinder_target
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/validate_episode.py \
  src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b3_eef_tf_smoke.npz
```

Purpose:

- Confirm the recorder writes finite `eef_pose` and
  `relative_target_to_eef`.
- Keep fallback disabled.
- Avoid sending any arm or gripper command.

Expected interpretation:

- If validator passes and metadata marks `eef_pose` and
  `relative_target_to_eef` available, B3 is resolved at the recorder level.
- If `eef_pose` remains unavailable, inspect whether `world ->
  oberon7_l/end_effector` is available or whether the recorder should use a
  different `eef_pose_reference_frame`.

## Round 23: B3 Recorder Smoke Attempt Blocked By Missing Target

Date: 2026-05-03

User context:

```text
gui:=false paused:=false
source devel/setup.bash already executed
```

User command:

```bash
rosservice call /gazebo/get_model_state "{model_name: 'cylinder_target', relative_entity_name: 'world'}"
```

User-reported result:

```text
success: False
status_message: "GetModelState: model does not exist"
pose.orientation.w: 0.0
```

The user then ran the B3 recorder smoke command with:

```text
require_target:=true
target_model_name:=cylinder_target
episode_id:=b3_eef_tf_smoke
```

Recorder result:

```text
Episode recording failed: timed out waiting for target model 'cylinder_target'
```

Validator result:

```text
validation: FAIL
ERROR: file does not exist: .../data/raw/b3_eef_tf_smoke.npz
```

Judgment:

```text
B3 is not resolved at the recorder level.
```

Interpretation:

- This attempt did not test the new recorder TF/eef write path.
- The failure happened before sampling because `require_target:=true` and
  `cylinder_target` was not present in Gazebo.
- The recorder behavior is correct for a non-fallback target-required episode:
  it must fail instead of silently recording nominal target state.
- No code defect is indicated by this output.

Does this require code changes now?

```text
No.
```

Reason:

- The blocker in this attempt is runtime target availability, not TF lookup or
  recorder implementation.
- B1 already proved the package-local target can be spawned. This fresh runtime
  simply does not currently contain `cylinder_target`.

Next minimal check requested from user:

Spawn the package-local target, verify it exists, then rerun the short B3
recorder smoke test. Do not publish any arm or gripper command.

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosrun gazebo_ros spawn_model \
  -sdf \
  -file "$(rospack find rexrov_single_oberon7_fm_dp)/models/cylinder_target/model.sdf" \
  -model cylinder_target \
  -x 2.6 -y 2.0 -z -40.0
rosservice call /gazebo/get_model_state "{model_name: 'cylinder_target', relative_entity_name: 'world'}"
roslaunch rexrov_single_oberon7_fm_dp record_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw \
  episode_id:=b3_eef_tf_smoke \
  rate_hz:=2.0 \
  max_duration_sec:=2.0 \
  require_target:=true \
  target_model_name:=cylinder_target
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/validate_episode.py \
  src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b3_eef_tf_smoke.npz
```

Expected interpretation:

- If spawn returns success and `get_model_state` returns `success: True`, the
  recorder should proceed to sampling.
- If validator passes and `unavailable_fields` does not include `eef_pose` or
  `relative_target_to_eef`, B3 is resolved at the recorder level.
- If target exists but `eef_pose` remains unavailable, inspect the recorder
  metadata field `eef_pose_source` and the runtime TF path.

## Round 24: B3 Recorder TF Smoke Test Passed

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
source devel/setup.bash already executed
```

User command:

```bash
rosrun gazebo_ros spawn_model \
  -sdf \
  -file "$(rospack find rexrov_single_oberon7_fm_dp)/models/cylinder_target/model.sdf" \
  -model cylinder_target \
  -x 2.6 -y 2.0 -z -40.0
rosservice call /gazebo/get_model_state "{model_name: 'cylinder_target', relative_entity_name: 'world'}"
roslaunch rexrov_single_oberon7_fm_dp record_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw \
  episode_id:=b3_eef_tf_smoke \
  rate_hz:=2.0 \
  max_duration_sec:=2.0 \
  require_target:=true \
  target_model_name:=cylinder_target
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/validate_episode.py \
  src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b3_eef_tf_smoke.npz
```

User-reported target spawn/readback:

```text
Spawn status: SpawnModel: Successfully spawned entity
get_model_state success: True
target pose: x=2.6, y=2.0, z=-44.2107072
target twist linear z: -9.0944
```

User-reported recorder result:

```text
Recording episode b3_eef_tf_smoke: 4 samples at 2.000 Hz
Saved episode to .../data/raw/b3_eef_tf_smoke.npz
Episode recording complete
process has finished cleanly
```

User-reported validator result:

```text
validation: PASS
T: 4
success: False
episode_id: b3_eef_tf_smoke
unavailable_fields: ['action_ee_delta', 'raw_command']
```

Local read-only metadata check:

```text
field_availability.target_pose: True
field_availability.eef_pose: True
field_availability.relative_target_to_eef: True
field_availability.action_ee_delta: False
field_availability.raw_command: False
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
allow_nominal_state_fallback: False
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
eef_pose_reference_frame: world
eef_link: oberon7_l/end_effector
eef_pose finite: True
relative_target_to_eef finite: True
target_pose finite: True
T: 4
```

Judgment:

```text
B3 is resolved for the current minimal launch and recorder write path.
```

Resolved by this check:

- The configured left eef frame exists in TF.
- The recorder writes finite `eef_pose`.
- The recorder writes finite `relative_target_to_eef`.
- The recorder keeps base, joint, and target state on live non-fallback sources.
- The validator passes with only `action_ee_delta` and `raw_command`
  unavailable, which is expected because no expert/policy command was active.

Still open outside B3:

- `action_ee_delta` and `raw_command` remain unavailable in this state-only B3
  smoke episode.
- Gripper command execution remains blocked by clean-baseline gripper joint
  motion.
- Real grasp success rate still cannot be evaluated.
- The target is falling after spawn, as shown by the target z velocity; this is
  a later task setup issue, not a B3 TF/eef blocker.

Does this require code changes now?

```text
No.
```

Reason:

- The B3 implementation and runtime smoke test are now sufficient for the
  current debug level.
- Further work should move to another blocker only after explicitly selecting
  it.

## Round 25: B5a Runtime Prerequisites And Dry-Run Converter Script

Date: 2026-05-03

Selected blocker:

```text
B5a: verify EE-delta action -> left-arm joint command action converter
```

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
source devel/setup.bash already executed
```

User commands and reported results:

```bash
timeout 5s rosservice call /controller_manager/load_controller "{name: 'oberon7/arm_position_l'}"
timeout 5s rosservice call /controller_manager/switch_controller \
  "{start_controllers: ['oberon7/arm_position_l'], stop_controllers: [], strictness: 2, start_asap: false, timeout: 5.0}"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
rosrun tf tf_echo rexrov/base_link oberon7_l/end_effector
```

Reported controller results:

```text
load_controller: ok: True
switch_controller: ok: True
joint_state_controller: running
oberon7/arm_position_l: running
```

No `oberon7/hand_position_l` controller was loaded or started in this check.

Reported left-arm controller state:

```text
desired and actual positions close
position errors about 2.6e-06 to 3.0e-05 rad
actual velocities small/bounded, with shoulder about -0.0084 rad/s and pitch
about 0.0147 rad/s in the sampled controller state
```

Reported `/joint_states`:

- All active-left arm joints are present.
- Runtime joint order differs from semantic controller order, so B5a converter
  must index by name.
- Clean-baseline gripper velocities remain large on both hands, consistent with
  the existing gripper blocker:

  ```text
  left gripper velocities around -0.48, -0.66, 0.22, 0.28 rad/s
  right gripper velocities around -0.48, -0.66, 0.22, 0.28 rad/s
  ```

Reported TF result:

- `tf_echo rexrov/base_link oberon7_l/end_effector` initially reported
  `oberon7_l/end_effector` missing and listed only:
  - `world_ned`
  - `oberon7_l/base`
  - `oberon7_r/base`
  - `rexrov/base_link_ned`
- It then began returning a stable transform:

  ```text
  Translation: [2.060, 0.500, -1.315]
  Quaternion: [0.499, 0.501, -0.501, 0.499]
  ```

Interpretation:

- Treat the initial missing-frame output as transient TF startup delay unless
  it persists in later checks.
- B3 remains resolved for the current launch because the transform becomes
  available and the earlier B3 recorder smoke test wrote finite `eef_pose`.

MoveIt/IK commands and reported results:

```bash
roslaunch rexrov_moveit_revised planning_context_revised.launch load_robot_description:=false
roslaunch rexrov_moveit_revised move_group_revised.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
rosservice list | grep -E "^/compute_ik$"
rosservice info /compute_ik
rosparam get /robot_description_semantic | grep -E "arm_l|oberon7_l/end_effector" | head -20
```

Reported MoveIt findings:

- `planning_context_revised.launch` loaded kinematics and semantic/planning
  parameters, then exited because it has no nodes to monitor.
- `move_group_revised.launch` started `/move_group` with
  `allow_trajectory_execution: False`.
- `/compute_ik` exists.
- `/compute_ik` is provided by `/move_group`.
- `/compute_ik` type is `moveit_msgs/GetPositionIK`.
- SRDF includes group `arm_l` with chain:

  ```text
  base_link="oberon7_l/base"
  tip_link="oberon7_l/end_effector"
  ```

Known MoveIt limitations still present:

- MoveIt reports `No controller_list specified`.
- MoveIt warns that `world_to_base` and several fixed/sensor joints are
  missing from the complete robot state.
- Therefore B5a must use MoveIt only as an IK source, not as a trajectory
  execution path.

Judgment:

```text
B5a is not resolved yet.
```

Resolved by this check:

- Left-arm controller runtime prerequisite is present.
- Active-left joint-state readback is present.
- EEF TF is available after a startup delay.
- `/compute_ik` is available with the expected service type.
- MoveIt trajectory execution is explicitly disabled and still not claimed.

Still open:

- No `action_ee_delta` has been converted into an IK joint target yet.
- No converter-produced `JointTrajectory` has been dry-run inspected yet.
- No converter-produced arm command has been published.
- Gripper remains blocked and out of scope.
- Real rollout and real grasp success remain not evaluated.

Does this require code changes now?

```text
Yes, for B5a dry-run validation.
```

Reason:

- Existing `action_converter.py` only creates/parses the 7D action label.
- The package did not yet contain a runtime check that maps a tiny EE delta to
  current eef pose, `/compute_ik`, bounded joint target, and a candidate
  `JointTrajectory`.
- The safest next implementation is a dry-run script that does not publish by
  default.

Code changes made in the project package:

```text
scripts/b5a_ee_delta_ik_check.py
CMakeLists.txt
package.xml
```

Implementation details:

- Added `scripts/b5a_ee_delta_ik_check.py`.
- Default behavior is `execute:=false`, so no `JointTrajectory` is published.
- The script:
  - reads `/joint_states`;
  - indexes active-left joints by name;
  - looks up `oberon7_l/end_effector` in `oberon7_l/base`;
  - applies clipped tiny EE deltas;
  - calls `/compute_ik` for MoveIt group `arm_l`;
  - extracts IK solution joints by name;
  - clips each joint delta by `~max_joint_delta`;
  - constructs a candidate `/oberon7/arm_position_l/command`
    `trajectory_msgs/JointTrajectory`;
  - publishes only if `~execute:=true`.
- Added `moveit_msgs` to `package.xml` and `CMakeLists.txt`.
- Added the new script to `catkin_install_python`.

Verification performed locally:

```text
chmod +x scripts/b5a_ee_delta_ik_check.py: passed
python3 -m py_compile scripts/b5a_ee_delta_ik_check.py: passed
catkin build rexrov_single_oberon7_fm_dp: passed
```

Build note:

- The package build succeeded.
- The only warning was the existing Gazebo classic `gazebo_msgs` deprecation
  warning.

Next minimal check requested from user:

This is dry-run only. It should not move the arm and should not touch the
gripper.

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=false \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01
```

Purpose:

- Verify the converter can compute:

  ```text
  tiny action_ee_delta
    -> current eef pose in oberon7_l/base
    -> target eef pose
    -> /compute_ik solution
    -> bounded left-arm joint target
    -> candidate JointTrajectory
  ```

Expected interpretation:

- If the script exits cleanly and logs `B5a dry-run only; no JointTrajectory
  was published`, then B5a has passed the no-motion conversion check.
- If IK fails, inspect the target pose frame, current joint state, and MoveIt
  group state before attempting any command.
- If TF lookup fails persistently, re-check B3 TF availability in the current
  runtime.
- Do not run `execute:=true` until dry-run output is reviewed.

## Round 26: B5a Dry-Run Blocked By Missing `/compute_ik`

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
source devel/setup.bash already executed
```

User command:

```bash
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=false \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01
```

User-reported result:

```text
B5a EE-delta IK check failed: timeout exceeded while waiting for service /compute_ik
```

Python also printed `SyntaxWarning` messages from ROS Noetic packages
`actionlib` and `tf`. These are environment/package warnings and are not the
B5a failure cause.

Judgment:

```text
B5a is not resolved.
```

Interpretation:

- The dry-run converter did not reach IK solving.
- No IK joint target was generated.
- No candidate `JointTrajectory` was validated.
- No command was published because `execute:=false` and the script failed
  before command construction completed.
- The immediate blocker is missing `/compute_ik` service at script runtime.
- This is a runtime MoveIt process availability issue, not evidence that the
  converter math or arm command topic is wrong.

Important runtime note:

- `rexrov_moveit_revised planning_context_revised.launch` loads parameters and
  exits because it has no nodes to monitor.
- `/compute_ik` is provided by `/move_group`, so
  `rexrov_moveit_revised move_group_revised.launch` must remain running in a
  live terminal while `b5a_ee_delta_ik_check.py` runs.
- Keep `allow_trajectory_execution:=false`; B5a uses MoveIt only for IK.

Does this require code changes now?

```text
No.
```

Reason:

- The script failed at the expected service wait boundary because `/compute_ik`
  was unavailable.
- The next step should be a read-only ROS graph check and, if needed, restarting
  `move_group` with trajectory execution disabled.
- Do not move to `execute:=true` until the dry-run succeeds.

Next minimal checks requested from user:

Read-only service/node check:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosnode list | grep -E "^/move_group$"
rosservice list | grep -E "^/compute_ik$"
rosservice info /compute_ik
```

Purpose:

- Confirm whether `/move_group` is alive.
- Confirm whether `/compute_ik` exists and is still served by `/move_group`.

If `/compute_ik` is missing, start or restart MoveIt IK in a separate terminal
and keep it running:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
roslaunch rexrov_moveit_revised move_group_revised.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
```

Then re-run the dry-run converter in another terminal:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=false \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01
```

Expected interpretation:

- If `/compute_ik` exists and the dry-run logs current pose, target pose, IK
  joints, and clipped joint deltas, B5a passes the no-motion converter check.
- If `/compute_ik` exists but IK fails with a MoveIt error code, inspect pose
  frame, current joint state, and IK target magnitude.
- If `/compute_ik` disappears again, treat it as a MoveIt launch/process
  persistence issue before changing converter code.

## Round 27: B5a `/compute_ik` Service Recheck Passed

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch running with allow_trajectory_execution:=false
source devel/setup.bash already executed
```

User commands:

```bash
rosnode list | grep -E "^/move_group$"
rosservice list | grep -E "^/compute_ik$"
rosservice info /compute_ik
```

User-reported result:

```text
/move_group
/compute_ik
/compute_ik:
  Node: /move_group
  Type: moveit_msgs/GetPositionIK
  Args: ik_request
```

Judgment:

```text
B5a is still not resolved, but the previous immediate blocker is cleared.
```

Resolved by this check:

- `/move_group` is alive.
- `/compute_ik` exists.
- `/compute_ik` is served by `/move_group`.
- The service type is the expected `moveit_msgs/GetPositionIK`.
- MoveIt trajectory execution remains disabled by launch argument, so this is
  still an IK-only path.

Still open:

- The dry-run converter has not yet been rerun while `/compute_ik` is online.
- No IK solution has been generated from a tiny `action_ee_delta`.
- No bounded joint target has been inspected.
- No `JointTrajectory` has been published.
- Gripper remains blocked and out of scope.

Does this require code changes now?

```text
No.
```

Reason:

- The package script is ready for the next dry-run.
- This round only confirmed that the required MoveIt IK service is live.
- The next step should be the dry-run converter check, still with
  `execute:=false`.

Next minimal check requested from user:

Keep the `move_group_revised.launch` terminal running, then run:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=false \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01
```

Purpose:

- Verify the no-motion converter path:

  ```text
  tiny action_ee_delta
    -> current eef pose in oberon7_l/base
    -> target eef pose
    -> /compute_ik solution
    -> bounded left-arm joint target
    -> candidate JointTrajectory
  ```

Expected interpretation:

- If the script exits cleanly and logs `B5a dry-run only; no JointTrajectory
  was published`, B5a has passed the no-motion conversion check.
- If it fails with a MoveIt error code, keep B5a focused on IK target frame,
  current robot state, and delta magnitude.
- Do not run `execute:=true` until the dry-run output is reviewed.

## Round 28: B5a Dry-Run Reached IK But Failed With Frame Transform Error

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch running with allow_trajectory_execution:=false
source devel/setup.bash already executed
```

User command:

```bash
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=false \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01
```

User-reported result:

```text
B5a EE-delta IK check failed: IK failed with MoveIt error code -21
```

Python again printed `SyntaxWarning` messages from ROS Noetic packages
`actionlib` and `tf`. These are environment/package warnings and are not the
B5a failure cause.

Judgment:

```text
B5a is not resolved.
```

Interpretation:

- The dry-run reached `/compute_ik`, so the previous missing-service blocker is
  cleared.
- MoveIt error code `-21` is `FRAME_TRANSFORM_FAILURE`.
- The request pose frame used by the script was not transformable by MoveIt in
  the current planning scene.
- No IK solution was produced.
- No bounded joint target was generated.
- No `JointTrajectory` was published because `execute:=false` and the script
  failed before command construction completed.
- Gripper remains blocked and out of scope.

Does this require code changes now?

```text
Yes, to improve B5a frame-debug robustness.
```

Reason:

- The first dry-run script used one IK request frame, `oberon7_l/base`.
- Runtime evidence shows TF can expose the eef transform, but MoveIt may not be
  able to transform every TF frame in the IK service request.
- A safer debug script should try a short list of plausible pose frames and log
  each MoveIt error code before failing.

Code change made:

```text
scripts/b5a_ee_delta_ik_check.py
```

Implementation details:

- Replaced single `~ik_pose_frame` with `~ik_pose_frames`.
- Default frame candidate order:

  ```text
  rexrov/base_link, oberon7_l/base, world
  ```

- For each candidate frame, the script:
  - looks up current `frame -> oberon7_l/end_effector` TF;
  - constructs the tiny target pose in that same frame;
  - calls `/compute_ik`;
  - records the MoveIt error code.
- It uses the first frame that returns `MoveItErrorCodes.SUCCESS`.
- Default remains `execute:=false`, so no command is sent.

Verification performed locally:

```text
python3 -m py_compile scripts/b5a_ee_delta_ik_check.py: passed
catkin build rexrov_single_oberon7_fm_dp: passed
```

Build note:

- The package build succeeded.
- The only warning was the existing Gazebo classic `gazebo_msgs` deprecation
  warning.

Next minimal check requested from user:

Keep `move_group_revised.launch` running, then rerun the dry-run. This should
still not move the arm and should not touch the gripper.

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=false \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01
```

Expected interpretation:

- If a candidate frame succeeds, the script logs `B5a IK frame attempts`,
  selected pose frame, current pose, target pose, IK joints, and clipped joint
  delta. That would pass the no-motion B5a converter check.
- If all candidate frames fail, the script should report the error code or
  exception for each candidate. Use that output to decide whether the next
  blocker is MoveIt frame configuration, stale robot state, or target pose
  reachability.
- Do not run `execute:=true` until the dry-run output is reviewed.

## Round 29: B5a Multi-Frame IK Dry-Run Still Fails

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch running with allow_trajectory_execution:=false
source devel/setup.bash already executed
```

User command:

```bash
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=false \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01
```

User-reported result:

```text
B5a EE-delta IK check failed: IK failed for all candidate frames:
['rexrov/base_link: error_code=-21',
 'oberon7_l/base: error_code=-21',
 "world: exception=timed out waiting for TF world -> oberon7_l/end_effector:
 Could not find a connection between 'world' and 'oberon7_l/end_effector'
 because they are not part of the same tree.Tf has two or more unconnected trees."]
```

Judgment:

```text
B5a is not resolved.
```

Interpretation:

- `/compute_ik` is being called.
- Direct IK requests in `rexrov/base_link` and `oberon7_l/base` both return
  MoveIt `-21` (`FRAME_TRANSFORM_FAILURE`).
- The `world` candidate cannot even build a target pose from TF because
  `world` and `oberon7_l/end_effector` are not in the same TF tree.
- No IK solution was produced.
- No bounded joint target was generated.
- No `JointTrajectory` was published.
- The failure is now narrowed to MoveIt request frame/current-state handling,
  not the left-arm command topic and not missing `/compute_ik`.

Does this require code changes now?

```text
Yes, for B5a dry-run diagnostics.
```

Reason:

- The existing `uvms_control` Oberon7 baseline does not derive the current eef
  pose from TF. It uses `MoveGroupCommander("arm_l").get_current_pose()` and
  seeds `/compute_ik` from `group.get_active_joints()` /
  `group.get_current_joint_values()`.
- The B5a script should match that local MoveIt pattern before treating IK as
  blocked.
- This remains a no-motion dry-run path; no MoveIt trajectory execution and no
  arm command publication are enabled by default.

Code changes made:

```text
scripts/b5a_ee_delta_ik_check.py
CMakeLists.txt
package.xml
```

Implementation details:

- Added `moveit_commander` import and package dependency.
- Added default `~use_moveit_commander_pose:=true`.
- The script now first tries the MoveIt Commander path:
  - create `MoveGroupCommander("arm_l")`;
  - set `oberon7_l/end_effector` as eef link;
  - use `group.get_planning_frame()`;
  - use `group.get_current_pose(eef_link)` for the current eef pose;
  - seed `/compute_ik` with `group.get_active_joints()` and
    `group.get_current_joint_values()`;
  - construct the tiny target pose in the MoveIt planning frame.
- If that fails, it falls back to the earlier TF-frame candidates.
- Default remains `execute:=false`, so no command is sent.

Verification performed locally:

```text
rospack find moveit_commander: /opt/ros/noetic/share/moveit_commander
python3 import moveit_commander: passed, with existing ROS/PyAssimp warnings
python3 -m py_compile scripts/b5a_ee_delta_ik_check.py: passed
catkin build rexrov_single_oberon7_fm_dp: passed
```

Build note:

- The package build succeeded.
- The only build warning was the existing Gazebo classic `gazebo_msgs`
  deprecation warning.

Next minimal check requested from user:

Keep `move_group_revised.launch` running, then rerun the dry-run. This should
not move the arm and should not touch the gripper.

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=false \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01
```

Expected interpretation:

- If the MoveIt Commander path works, the script logs an attempt like
  `moveit_commander:<planning_frame>: error_code=1`, then logs current pose,
  target pose, IK joints, raw joint delta, clipped joint delta, and
  `B5a dry-run only; no JointTrajectory was published`.
- If it fails, the script should include both the MoveIt Commander attempt and
  fallback frame attempts. Use that output to decide whether B5a needs a lower
  level KDL/RobotState route or whether MoveIt current-state completeness must
  be fixed first.
- Do not run `execute:=true` until the dry-run output is reviewed.

## Round 30: B5a MoveIt Commander Dry-Run Converter Passed

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch running with allow_trajectory_execution:=false
source devel/setup.bash already executed
```

User command:

```bash
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=false \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01
```

User-reported result:

```text
B5a IK frame attempts: ['moveit_commander:world: error_code=1']
B5a selected pose frame: world
B5a current eef xyz: [2.059550, 0.500330, -1.315203]
B5a target eef xyz:  [2.064550, 0.500330, -1.315203]
B5a active joints:
  ['oberon7_l/azimuth', 'oberon7_l/shoulder', 'oberon7_l/elbow',
   'oberon7_l/roll', 'oberon7_l/pitch', 'oberon7_l/wrist']
B5a current joints:
  [0.0002290029, -0.0009488744, -0.0001356824,
   0.0000191029, -0.0017449896, -0.0000759615]
B5a IK joints:
  [0.0002357601, -0.0033535053, 0.0122152798,
   0.0000062776, -0.0115932695, 0.0002005778]
B5a raw joint delta:
  [0.0000067572, -0.0024046309, 0.0123509621,
   -0.0000128254, -0.0098482799, 0.0002765393]
B5a clipped joint delta:
  [0.0000067572, -0.0024046309, 0.01,
   -0.0000128254, -0.0098482799, 0.0002765393]
B5a command positions:
  [0.0002357601, -0.0033535053, 0.0098643176,
   0.0000062776, -0.0115932695, 0.0002005778]
B5a execute: False
B5a dry-run only; no JointTrajectory was published
```

Environment warnings also appeared:

- ROS Noetic Python `SyntaxWarning` messages from `actionlib` and `tf`.
- `Failed to import pyassimp` from MoveIt Commander.
- KDL warning about root link `rexrov/base_link` inertia.
- MoveIt warning that `world_to_base` cannot be updated because `world` and
  `rexrov/base_link` are not in the same TF tree.

These warnings do not invalidate the dry-run converter result, because
`/compute_ik` returned success for the MoveIt Commander path.

Judgment:

```text
B5a is partially resolved.
```

Resolved by this check:

- The no-motion converter path now works:

  ```text
  tiny action_ee_delta
    -> MoveIt Commander current eef pose
    -> target eef pose
    -> /compute_ik solution
    -> bounded left-arm joint target
    -> candidate JointTrajectory
  ```

- `/compute_ik` returned success (`error_code=1`).
- The command remained bounded by `~max_joint_delta`.
- The dry-run did not publish a `JointTrajectory`.
- Gripper was not loaded or commanded.

Still open:

- Converter-produced command execution has not been tested.
- No `/joint_states` or `/oberon7/arm_position_l/state` readback exists yet
  after an `execute:=true` converter command.
- No eef pose change has been observed after a converter-produced command.
- Gripper remains blocked.
- Real rollout and real grasp success remain not evaluated.

Does this require code changes now?

```text
No.
```

Reason:

- The no-motion converter check passed.
- The next step can use the existing script with `execute:=true` for one tiny
  arm-only command.
- Keep the test bounded and read back arm/eef state before declaring B5a
  minimally resolved.

Next minimal check requested from user:

This is the first converter-produced control command. Safety boundary:

- Keep `move_group_revised.launch` running with
  `allow_trajectory_execution:=false`.
- Do not load or start any hand controller.
- The command publishes only to `/oberon7/arm_position_l/command`.
- EE delta remains `0.005 m`.
- Per-joint delta remains clipped to at most `0.01 rad`.
- If the post-command state looks wrong, rollback is a current-position hold
  command.

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=true \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01
sleep 3
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
timeout 5s rosrun tf tf_echo rexrov/base_link oberon7_l/end_effector
```

Expected interpretation:

- If `oberon7/arm_position_l` is running and no hand controller is running,
  proceed with the command.
- If the script publishes a `JointTrajectory`, then desired arm positions
  should match the logged command positions.
- Actual arm positions should move toward desired with bounded errors.
- `tf_echo` should show a small eef pose change.
- If controller errors grow or arm state jumps unexpectedly, stop further B5a
  command tests and send a current-position hold command.

## Round 31: B5a First Converter-Produced Command Did Not Update Desired State

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch running with allow_trajectory_execution:=false
source devel/setup.bash already executed
```

Pre-command controller check:

```text
joint_state_controller: running
oberon7/arm_position_l: running
```

No hand controller was reported loaded or running.

User command:

```bash
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=true \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01
sleep 3
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
timeout 5s rosrun tf tf_echo rexrov/base_link oberon7_l/end_effector
```

User-reported script result:

```text
B5a IK frame attempts: ['moveit_commander:world: error_code=1']
B5a selected pose frame: world
B5a current eef xyz: [2.059488, 0.500326, -1.315235]
B5a target eef xyz:  [2.064488, 0.500326, -1.315235]
B5a current joints:
  [0.0002436934, -0.0009180616, -0.0000987074,
   0.0000888876, -0.0014542414, 0.0002962323]
B5a IK joints:
  [0.0002298340, -0.0033922384, 0.0121792696,
   0.0000170208, -0.0116384767, 0.0001189417]
B5a clipped joint delta:
  [-0.0000138594, -0.0024741768, 0.01,
   -0.0000718668, -0.01, -0.0001772906]
B5a command positions:
  [0.0002298340, -0.0033922384, 0.0099012926,
   0.0000170208, -0.0114542414, 0.0001189417]
B5a execute: True
B5a published JointTrajectory to /oberon7/arm_position_l/command
```

Post-command `/oberon7/arm_position_l/state` after about 3 seconds:

```text
desired positions:
  [0.0002295010, -0.0009499990, -0.0001320175,
   0.0000144202, -0.0016502914, -0.0001602329]
actual positions:
  [0.0002431983, -0.0009215441, -0.0000996648,
   0.0000844577, -0.0016028947, 0.0002424539]
position errors:
  about -1.37e-05, -2.85e-05, -3.24e-05, -7.00e-05,
  -4.74e-05, -4.03e-04 rad
```

Post-command `/joint_states`:

- Active-left arm joints remained near the pre-command neighborhood.
- Arm velocities were bounded but did not show clear movement toward the
  converter command target.
- Gripper velocities remained present as part of the known clean-baseline
  gripper blocker.

Post-command TF:

- `tf_echo rexrov/base_link oberon7_l/end_effector` initially reported the eef
  frame unavailable, then returned transforms.
- Translation stayed near:

  ```text
  [2.059-2.060, 0.500, -1.315]
  ```

Judgment:

```text
B5a is not resolved.
```

Interpretation:

- The converter produced a valid bounded command and the script logged that it
  published it.
- However, the controller desired positions after the command did not match the
  logged command positions.
- The post-command desired state stayed at the old controller desired values.
- This means the first converter-produced command execution is not confirmed.
- The most likely immediate cause is ROS publisher synchronization: the script
  created a publisher, published once, and exited before the subscriber
  connection to `/gazebo` was reliably established.
- This is not evidence that IK is wrong, and it does not change the gripper
  blocker status.

Does this require code changes now?

```text
Yes.
```

Reason:

- A one-shot `rospy.Publisher` can drop a message if the node exits before a
  subscriber connection is established or before the message is flushed.
- Manual `rostopic pub -1` worked earlier because it waits and latches for a
  short period.
- The B5a script should wait for a command-topic subscriber before publishing
  and stay alive briefly after publishing.

Code change made:

```text
scripts/b5a_ee_delta_ik_check.py
```

Implementation details:

- Added `~command_connection_timeout_sec`, default `5.0`.
- Added `~post_publish_sleep_sec`, default `0.5`.
- In `execute:=true`, the script now:
  - waits until `/oberon7/arm_position_l/command` has at least one subscriber;
  - publishes the `JointTrajectory`;
  - sleeps briefly after publishing so the message can flush.

Verification performed locally:

```text
python3 -m py_compile scripts/b5a_ee_delta_ik_check.py: passed
catkin build rexrov_single_oberon7_fm_dp: passed
```

Build note:

- The package build succeeded.
- The only build warning was the existing Gazebo classic `gazebo_msgs`
  deprecation warning.

Next minimal check requested from user:

Repeat the tiny converter-produced arm-only command with the synchronized
publisher path. Keep the same safety boundaries: no hand controller, no gripper
command, no MoveIt execution.

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=true \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01 \
  _command_connection_timeout_sec:=5.0 \
  _post_publish_sleep_sec:=0.5
sleep 3
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
timeout 5s rosrun tf tf_echo rexrov/base_link oberon7_l/end_effector
```

Expected interpretation:

- If the controller receives the command, `/oberon7/arm_position_l/state`
  desired positions should match the command positions logged by the script.
- Actual positions should move toward desired with bounded errors.
- If desired still does not update, inspect `/oberon7/arm_position_l/command`
  publisher/subscriber timing and consider publishing the same trajectory for a
  short repeated burst in the script.

## Round 32: Current B5a Decision After First Execute Output

Date: 2026-05-03

Decision:

```text
B5a is still not resolved.
```

Reason:

- The dry-run action converter path is working: tiny EE delta, current eef pose,
  MoveIt Commander pose frame, `/compute_ik`, active-left joint extraction, and
  per-joint clipping all produced a bounded arm-only `JointTrajectory`.
- The first `execute:=true` run logged a publish to
  `/oberon7/arm_position_l/command`.
- The post-command controller state did not show those command positions as
  desired positions.
- Therefore the converter-produced command has not yet been confirmed to drive
  the left arm.

Current code status:

- No additional code change is required before the next check.
- The B5a script already waits for a command-topic subscriber and sleeps briefly
  after publish in `execute:=true`.

Next minimal check remains:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=true \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01 \
  _command_connection_timeout_sec:=5.0 \
  _post_publish_sleep_sec:=0.5
sleep 3
rostopic echo -n 1 /oberon7/arm_position_l/state
rostopic echo -n 1 /joint_states
timeout 5s rosrun tf tf_echo rexrov/base_link oberon7_l/end_effector
```

Success criterion for this next check:

- `oberon7/arm_position_l` is running.
- No hand/gripper controller is loaded or commanded.
- Controller desired positions match the script's logged command positions.
- Actual active-left arm joints move toward desired with bounded errors.
- TF reports a small eef pose change.

## Round 33: B5a Synchronized Tiny Execute Passed

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch running with allow_trajectory_execution:=false
source devel/setup.bash already executed
```

Pre-command controller check:

```text
joint_state_controller: running
oberon7/arm_position_l: running
```

No hand/gripper controller was reported loaded or running.

Command under test:

```bash
rosrun rexrov_single_oberon7_fm_dp b5a_ee_delta_ik_check.py \
  _execute:=true \
  _delta_x:=0.005 \
  _delta_y:=0.0 \
  _delta_z:=0.0 \
  _max_linear_step:=0.005 \
  _max_joint_delta:=0.01 \
  _command_connection_timeout_sec:=5.0 \
  _post_publish_sleep_sec:=0.5
```

Script result:

```text
B5a IK frame attempts: ['moveit_commander:world: error_code=1']
B5a current eef xyz: [2.059573, 0.500333, -1.315203]
B5a target eef xyz:  [2.064573, 0.500333, -1.315203]
B5a command positions:
  [0.0002395104, -0.0033546553, 0.0098995494,
   0.0000112465, -0.0114451132, 0.0003411589]
B5a published JointTrajectory to /oberon7/arm_position_l/command
```

Post-command controller state:

```text
desired positions:
  [0.0002395104, -0.0033546553, 0.0098995494,
   0.0000112465, -0.0114451132, 0.0003411589]
actual positions:
  [0.0002517514, -0.0033242450, 0.0099326379,
   0.0000865204, -0.0113411858, 0.0002664748]
position errors:
  about -1.22e-05, -3.04e-05, -3.31e-05, -7.53e-05,
  -1.04e-04, 7.47e-05 rad
```

Post-command `/joint_states`:

- Active-left arm joints were in the commanded neighborhood.
- Arm velocities remained bounded.
- Gripper joints still showed uncontrolled baseline motion; this remains the
  separate B2 gripper blocker and was not commanded.

Post-command TF:

- `tf_echo rexrov/base_link oberon7_l/end_effector` again initially reported
  the eef frame unavailable, then returned transforms.
- Translation was around:

  ```text
  [2.063, 0.500, -1.315/-1.316]
  ```

- This is a small x-direction eef motion from the script's pre-command x near
  `2.059573`.

Decision:

```text
B5a is minimally resolved for the left-arm-only action converter path.
```

Resolved scope:

- tiny `action_ee_delta` style translation;
- current eef pose from MoveIt Commander;
- IK through `/compute_ik`;
- active-left joint target extraction by name;
- per-joint delta clipping to `0.01 rad`;
- direct `JointTrajectory` publish to `/oberon7/arm_position_l/command`;
- controller desired update;
- bounded active-left actual motion;
- small eef TF motion.

Still not resolved by this check:

- gripper command/control;
- full scripted expert runtime integration;
- MoveIt trajectory execution;
- non-fallback demonstration collection;
- real policy rollout;
- real grasp success rate.

Next logical blocker:

```text
B5b: integrate the B5a converter into the scripted expert/runtime command path,
still arm-only and with gripper disabled.
```

## Round 34: B5b Read-Only Preconditions And Arm-Only Expert Wiring

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch running with allow_trajectory_execution:=false
source devel/setup.bash already executed
```

Read-only precheck output:

```text
joint_state_controller: running
oberon7/arm_position_l: running
/move_group: present
/compute_ik: moveit_msgs/GetPositionIK served by /move_group
/oberon7/arm_position_l/command: trajectory_msgs/JointTrajectory, subscriber /gazebo
/oberon7/arm_position_l/state: published by /gazebo
```

Live state / TF:

- `tf_echo rexrov/base_link oberon7_l/end_effector` returned transforms around
  `[2.063, 0.500, -1.315/-1.316]`.
- `/joint_states` returned live active-left arm joints.
- `/rexrov/pose_gt` returned live odometry.

Target state:

```text
/gazebo/get_model_state cylinder_target: success=False
/gazebo/model_states names: ocean_box, rexrov
```

Judgment:

```text
B5b is not resolved yet.
```

Reason:

- The arm command, IK, TF, joint-state, and base-odom prerequisites are present.
- However, `cylinder_target` is not currently spawned, so a B5b recorder smoke
  test requiring non-fallback target state would fail.
- The scripted expert code still needed runtime command integration before this
  round.

Code change made:

```text
src/rexrov_single_oberon7_fm_dp/arm_command_converter.py
src/rexrov_single_oberon7_fm_dp/expert_policy.py
launch/collect_episode.launch
config/topics.yaml
```

Implementation details:

- Added `ArmEEDeltaCommandConverter`, which reuses the B5a-safe route:
  `MoveGroupCommander("arm_l") -> /compute_ik -> clipped active-left joint target
  -> /oberon7/arm_position_l/command`.
- The converter waits for a command-topic subscriber before publish and sleeps
  briefly after publish.
- `ScriptedExpert` now accepts:
  - `execute_arm`
  - `enable_gripper_command`
  - `arm_command_topic`
  - `max_linear_step`
  - `max_angular_step`
  - `max_joint_delta`
  - `time_from_start_sec`
  - `command_connection_timeout_sec`
  - `post_publish_sleep_sec`
  - `execute_arm_once_per_state`
  - `execute_arm_states`
- Default behavior remains non-commanding:

  ```text
  execute_arm: false
  ```

- Gripper command execution remains blocked:

  ```text
  enable_gripper_command: false
  ```

- If `enable_gripper_command:=true`, the expert raises an error instead of
  pretending gripper control works.
- `collect_episode.launch` exposes the B5b safety parameters.
- `collect_episode.launch` also exposes `require_target` independently from
  `spawn_target`; this lets a manually pre-spawned target remain mandatory for
  recorder validation.
- `topics.yaml` now records `/oberon7/arm_position_l/command` as the minimally
  resolved left-arm command topic.

Static verification:

```text
python3 -m py_compile arm_command_converter.py expert_policy.py scripted_expert.py: passed
python3 -m xml.etree.ElementTree collect_episode.launch: passed
catkin build rexrov_single_oberon7_fm_dp: passed
```

Next minimal user-run check:

1. Spawn or confirm `cylinder_target` before recorder validation.
2. Run a short arm-only B5b scripted expert smoke test with:
   - `execute_arm:=true`
   - `enable_gripper_command:=false`
   - `allow_nominal_state_fallback:=false`
   - low rate and short duration.
3. Validate the episode.

Expected B5b success criteria:

- scripted expert publishes finite `action_ee_delta`;
- one tiny arm-only `JointTrajectory` reaches
  `/oberon7/arm_position_l/command`;
- `/oberon7/arm_position_l/state` desired matches the command target;
- active-left joints move by a small bounded amount;
- `eef_pose` changes by a small bounded amount;
- validator passes;
- metadata shows non-fallback live state and target sources;
- `success=False` remains acceptable because gripper is unresolved.

Still not claimed:

- gripper command/control;
- MoveIt trajectory execution;
- real policy rollout;
- real grasp success rate.

## Round 35: B5b Arm-Only Scripted Expert Smoke Passed

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch running with allow_trajectory_execution:=false
source devel/setup.bash already executed
```

Target spawn:

```text
SpawnModel: Successfully spawned entity
/gazebo/get_model_state cylinder_target: success=True
initial readback pose: [2.6, 2.0, -44.3204]
initial readback twist z: -9.1924
```

Interpretation:

- The target exists and is visible through Gazebo, so recorder target source can
  be non-fallback.
- The target is still physically unstable/falling immediately after spawn; this
  remains a later task setup issue.

B5b command:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=.../data/raw/b5b_smoke \
  episode_id:=b5b_arm_only_smoke \
  rate_hz:=2.0 \
  max_duration_sec:=3.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  execute_arm_once_per_state:=true \
  execute_arm_states:=MOVE_TO_PREGRASP
```

Runtime logs:

```text
Recording episode b5b_arm_only_smoke: 6 samples at 2.000 Hz
Scripted expert running with target source gazebo_model_states ...
execute_arm=True gripper_command_enabled=False
B5b arm command state=MOVE_TO_PREGRASP
current_eef_xyz=[2.062989, 0.500349, -1.315499]
target_eef_xyz=[2.067989, 0.500349, -1.310499]
command_positions=[0.0002594683, 0.0032141103, 0.0130758532,
                   -0.0000183038, -0.0211685831, 0.0002506068]
Saved episode to .../data/raw/b5b_smoke/b5b_arm_only_smoke.npz
```

Validation:

```text
validation: PASS
T: 6
success: False
unavailable_fields: ['raw_command']
WARNING: raw_command contains NaN because metadata marks it unavailable
```

Post-run episode inspection:

```text
allow_nominal_state_fallback: False
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
controller_type: scripted
arm_command_topic: /oberon7/arm_position_l/command
gripper_command_topic: None
field_availability:
  action_ee_delta: True
  eef_pose: True
  relative_target_to_eef: True
  target_pose: True
  raw_command: False
```

Recorded motion:

```text
active_joint_positions: finite, shape [6, 6]
max_abs_active_delta_from_first:
  [4.2e-05, 5.5e-03, 2.7e-03, 1.3e-04, 8.1e-03, 5.8e-04] rad
action_ee_delta: finite, shape [6, 7]
last recorded action:
  [0.005, 0.0, -0.005, 0.0, 0.0, 0.0, 0.0]
```

Decision:

```text
B5b is minimally resolved for arm-only scripted expert execution smoke.
```

Resolved scope:

- scripted expert runs with explicit `execute_arm:=true`;
- gripper command execution remains disabled;
- scripted EE-delta action labels are clipped;
- B5a converter is called from the scripted expert runtime path;
- one arm-only `JointTrajectory` is published through the verified
  `/oberon7/arm_position_l/command` path;
- recorder writes non-fallback base, joint, target, action, eef, and relative
  target-to-eef fields;
- validator passes.

Caveats:

- `raw_command` is unavailable because recorder does not yet capture the raw arm
  `JointTrajectory`; this is documented and not a B5b failure.
- `success=False` is expected because gripper remains blocked and no real grasp
  success should be claimed.
- World-frame `eef_pose` includes base drift; active-left joint deltas provide
  the bounded arm-motion evidence for this smoke test.
- The target is visible through Gazebo but falls to about `z=-99.8` during the
  episode, so target stabilization remains a separate task-setup issue.

Still not resolved:

- gripper command/control;
- MoveIt trajectory execution;
- raw arm command recording in `raw_command`;
- target physical stability;
- real policy rollout;
- real grasp success rate.

## Round 36: B5c Target Stability Read-Only Check And Static Target Fix

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch running with allow_trajectory_execution:=false
source devel/setup.bash already executed
```

Read-only checks:

```text
models/cylinder_target/model.sdf:
  <static>false</static>
  mass: 0.5
  cylinder collision radius 0.05 length 0.30
  no buoyancy, fixed joint, world attachment, or hold plugin

/gazebo/get_physics_properties:
  gravity.z: -9.8
  pause: False
  max_update_rate: 500.0

/gazebo/model_states names:
  ocean_box
  rexrov

/gazebo/get_model_state cylinder_target:
  success: False
  model does not exist

/gazebo/get_model_properties cylinder_target:
  success: False
  model does not exist
```

Judgment:

```text
B5c is not resolved yet.
```

Interpretation:

- The latest runtime did not contain `cylinder_target`, so this read-only check
  could not resample its falling trajectory.
- The existing SDF plus Gazebo physics settings explain the earlier B5b
  observation: a dynamic cylinder under standard gravity with no support or
  buoyancy will fall.
- Earlier B5b evidence remains valid: after spawn, the target was visible
  through Gazebo but quickly reached about `z=-99.8`.

Minimal package-local fix:

```text
models/cylinder_target_static/model.sdf
launch/collect_episode.launch
```

Implementation:

- Added a static smoke target SDF:

  ```text
  <model name="cylinder_target">
    <static>true</static>
    ...
  </model>
  ```

- Reused the same cylinder geometry.
- Added `target_sdf_path` argument to `collect_episode.launch`, defaulting to
  the existing dynamic SDF for backward compatibility.
- This allows smoke tests to spawn the stable static model as
  `model_name:=cylinder_target`, so recorder metadata can still report
  `target_state_source: gazebo_model_states`.
- No DAVE, UUV, manipulator, or RexROV2 package was modified.

Verification:

```text
python3 -m xml.etree.ElementTree models/cylinder_target_static/model.sdf: passed
python3 -m xml.etree.ElementTree launch/collect_episode.launch: passed
catkin build rexrov_single_oberon7_fm_dp: passed
```

Next minimal user-run check:

1. Spawn the static SDF as `cylinder_target`.
2. Sample `/gazebo/get_model_state` for a few seconds.
3. Confirm:
   - `success: True`;
   - z remains near requested spawn depth;
   - twist remains near zero;
   - `/gazebo/model_states` includes `cylinder_target`.

Only after that should recorder validation be repeated with:

```text
allow_nominal_state_fallback:=false
require_target:=true
target_sdf_path:=.../models/cylinder_target_static/model.sdf
```

Still not addressed:

- gripper command/control;
- dynamic floating-object realism;
- MoveIt trajectory execution;
- real policy rollout;
- real grasp success rate.

## Round 37: B5c Static Target Runtime Stability Passed

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch running with allow_trajectory_execution:=false
source devel/setup.bash already executed
```

Command under test:

```bash
rosrun gazebo_ros spawn_model \
  -sdf \
  -file $(rospack find rexrov_single_oberon7_fm_dp)/models/cylinder_target_static/model.sdf \
  -model cylinder_target \
  -x 2.6 -y 2.0 -z -40.0

for i in 1 2 3 4 5; do
  timeout 3s rosservice call /gazebo/get_model_state \
    "{model_name: 'cylinder_target', relative_entity_name: 'world'}"
  sleep 0.5
done

timeout 5s rostopic echo -n 1 /gazebo/model_states
```

Result:

```text
SpawnModel: Successfully spawned entity
```

Five `/gazebo/get_model_state` samples returned:

```text
success: True
pose.position: [2.6, 2.0, -40.0]
pose.orientation: [0.0, 0.0, 0.0, 1.0]
twist.linear: [0.0, 0.0, 0.0]
twist.angular: [0.0, 0.0, 0.0]
```

The samples covered approximately sim time `1185.058` to `1190.668`.

`/gazebo/model_states` included:

```text
ocean_box
rexrov
cylinder_target
```

with `cylinder_target` at:

```text
position: [2.6, 2.0, -40.0]
orientation: [0.0, 0.0, 0.0, 1.0]
twist.linear: [0.0, 0.0, 0.0]
twist.angular: [0.0, 0.0, 0.0]
```

Judgment:

```text
B5c target-stability subcheck passed, but full B5c is not resolved until a
non-fallback recorder smoke episode validates the stable target source.
```

Interpretation:

- The package-local static target fixes the fast-falling target behavior for
  smoke-test purposes.
- Target pose remains available from Gazebo, not nominal fallback.
- This is a task-setup smoke fix, not a physically realistic dynamic
  underwater object model.

Next minimal user-run check:

Run a short recorder smoke with the already-spawned static target:

```bash
mkdir -p src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b5c_smoke

roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b5c_smoke \
  episode_id:=b5c_static_target_recorder_smoke \
  rate_hz:=2.0 \
  max_duration_sec:=2.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=false \
  enable_gripper_command:=false

rosrun rexrov_single_oberon7_fm_dp validate_episode.py \
  src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b5c_smoke/b5c_static_target_recorder_smoke.npz
```

Expected:

- validator PASS;
- `target_state_source: gazebo_model_states`;
- `allow_nominal_state_fallback: False`;
- target pose finite and stable near `[2.6, 2.0, -40.0]`;
- `success=False` remains acceptable because gripper is unresolved.

## Round 38: B5c Static Target Recorder Smoke Passed

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch running with allow_trajectory_execution:=false
source devel/setup.bash already executed
static cylinder_target already spawned and stable
```

Command:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=.../data/raw/b5c_smoke \
  episode_id:=b5c_static_target_recorder_smoke \
  rate_hz:=2.0 \
  max_duration_sec:=2.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=false \
  enable_gripper_command:=false
```

Runtime logs:

```text
Recording episode b5c_static_target_recorder_smoke: 4 samples at 2.000 Hz
Scripted expert running with target source gazebo_model_states and target pose
[2.6, 2.0, -40.0, 0.0, 0.0, 0.0, 1.0]
execute_arm=False gripper_command_enabled=False
Saved episode to .../data/raw/b5c_smoke/b5c_static_target_recorder_smoke.npz
```

Validation:

```text
validation: PASS
T: 4
success: False
unavailable_fields: ['raw_command']
WARNING: raw_command contains NaN because metadata marks it unavailable
```

Post-run episode inspection:

```text
allow_nominal_state_fallback: False
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
controller_type: scripted
arm_command_topic: /oberon7/arm_position_l/command
gripper_command_topic: None
field_availability:
  action_ee_delta: True
  eef_pose: True
  relative_target_to_eef: True
  target_pose: True
  raw_command: False
```

Recorded target stability:

```text
target_pose first:
  [2.6, 2.0, -40.0, 0.0, 0.0, 0.0, 1.0]
target_pose last:
  [2.6, 2.0, -40.0, 0.0, 0.0, 0.0, 1.0]
target xyz delta:
  [0.0, 0.0, 0.0]
max abs target xyz delta from first sample:
  [0.0, 0.0, 0.0]
```

Decision:

```text
B5c is minimally resolved for package-local static-target smoke.
```

Resolved scope:

- target falling behavior is reproduced/explained for the original dynamic SDF;
- package-local static target SDF keeps `cylinder_target` stable in the grasp
  workspace;
- target state remains a live non-fallback Gazebo source;
- recorder writes stable finite `target_pose`;
- `allow_nominal_state_fallback` remains false;
- validator passes.

Caveats:

- This is a smoke-test task setup fix, not a physically realistic dynamic
  underwater floating-object model.
- `success=False` remains expected because gripper is unresolved.
- `raw_command` remains unavailable and is not part of B5c.
- MoveIt trajectory execution and real policy rollout are still not resolved.

## Round 39: B2b Clean-Baseline Gripper Diagnosis

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
source devel/setup.bash already executed
move_group not required for this B2b check
```

Safety boundary:

- No gripper command was sent.
- No hand controller was loaded or started.
- This round was read-only: controller graph, topic graph, params, and
  `/joint_states` samples.

Controller-manager output:

```text
/controller_manager/list_controllers:
  joint_state_controller:
    state: running
```

No arm or hand controller was loaded in this clean baseline.

Available controller plugin types included:

```text
position_controllers/JointTrajectoryController
effort_controllers/JointTrajectoryController
position_controllers/GripperActionController
effort_controllers/GripperActionController
```

Service/topic graph:

```text
rosservice list | grep hand/gripper/finger/follow_joint:
  no matches except controller_manager services

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

Controller params:

```text
/oberon7/hand_position_l/type:
  position_controllers/JointTrajectoryController

/oberon7/hand_position_l/joints:
  oberon7_l/finger_left_joint
  oberon7_l/finger_tip_left_joint
  oberon7_l/finger_right_joint
  oberon7_l/finger_tip_right_joint

/oberon7/hand_effort_l/type:
  effort_controllers/JointTrajectoryController

/oberon7/hand_effort_l/joints:
  same four left gripper joints
```

`/robot_description_semantic` was not set because MoveIt was not launched.
This is acceptable for the B2b clean-baseline gripper check.

Read-only `/joint_states` sampling:

- Six samples were collected over roughly 2.6 seconds.
- Both left and right gripper joints showed large nonzero velocities despite
  no hand controller or command topic being present.

Representative left gripper velocities:

```text
oberon7_l/finger_left_joint:       about -0.479 rad/s
oberon7_l/finger_tip_left_joint:   about  0.219 rad/s
oberon7_l/finger_right_joint:      about -0.655 rad/s
oberon7_l/finger_tip_right_joint:  about  0.277 rad/s
```

Representative right gripper velocities:

```text
oberon7_r/finger_left_joint:       about -0.480 rad/s
oberon7_r/finger_tip_left_joint:   about  0.220 rad/s
oberon7_r/finger_right_joint:      about -0.655 rad/s
oberon7_r/finger_tip_right_joint:  about  0.277 rad/s
```

Measured gripper position deltas from first to last sample:

```text
oberon7_l/finger_left_joint:       +2.912e-06 rad
oberon7_l/finger_tip_left_joint:   -9.130e-07 rad
oberon7_l/finger_right_joint:      +3.012e-06 rad
oberon7_l/finger_tip_right_joint:  -8.295e-07 rad

oberon7_r/finger_left_joint:       +2.914e-06 rad
oberon7_r/finger_tip_left_joint:   -9.132e-07 rad
oberon7_r/finger_right_joint:      +3.011e-06 rad
oberon7_r/finger_tip_right_joint:  -8.295e-07 rad
```

Decision:

```text
B2b is not resolved. The gripper remains blocked.
```

What this round confirms:

- The clean baseline has only `joint_state_controller` running.
- No hand/gripper command topic or action server exists.
- No active publisher can be responsible for gripper command motion.
- Hand controller params are present but the controllers are not loaded.
- Both left and right grippers still report large nonzero velocities.

Current best classification:

```text
baseline model / Gazebo physics / uncontrolled or passive gripper joint blocker
```

Implications:

- Do not publish gripper trajectories yet.
- Do not treat hand controller load/start as evidence that gripper execution is
  safe.
- Real grasp success remains unevaluable.
- The next B2b step should remain diagnostic: inspect package-local/runtime
  model and controller definitions for gripper joint limits, damping, friction,
  mimic/passive joints, transmissions, and gain assumptions before considering
  any tiny gripper command.

## Round 40: B2b Runtime URDF Gripper Joint Inspection

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
source devel/setup.bash already executed
```

Safety boundary:

- Read-only `/robot_description` inspection.
- No hand controller was loaded or started.
- No gripper command was sent.

User inspected these joints in `/robot_description`:

```text
oberon7_l/finger_left_joint
oberon7_l/finger_tip_left_joint
oberon7_l/finger_right_joint
oberon7_l/finger_tip_right_joint
oberon7_r/finger_left_joint
oberon7_r/finger_tip_left_joint
oberon7_r/finger_right_joint
oberon7_r/finger_tip_right_joint
```

Main finger joint pattern:

```text
type: revolute
limit:
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

Finger-tip joint pattern:

```text
type: revolute
limit:
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

Transmissions:

- All eight gripper joints have
  `transmission_interface/SimpleTransmission`.
- All eight use `hardware_interface/PositionJointInterface`.
- That includes the four finger-tip joints whose URDF limits indicate zero
  range, zero effort, and zero velocity.

Decision:

```text
B2b remains unresolved.
```

Interpretation:

- The URDF contains a suspicious gripper modeling/controller combination:
  finger-tip joints are revolute and transmitted through a position interface,
  but have zero range and zero command authority.
- The finger-tip joints are not fixed and do not mimic the parent finger
  joints.
- This supports the current classification of a baseline model / Gazebo physics
  / uncontrolled-or-passive-joint blocker.
- It is not enough evidence yet to edit URDF/SDF/controller configs, because
  the next question is how Gazebo represents these joints at runtime.

Next minimum check:

- Query Gazebo joint properties for the same eight joints.
- Confirm whether Gazebo reports nonzero rates for the zero-range finger-tip
  joints.
- Inspect link gravity/mass for the finger links if joint properties confirm
  runtime movement.

Still prohibited:

- Do not publish gripper trajectories.
- Do not start hand controllers as a "fix".
- Do not claim grasp success.

## Round 41: B2b Gazebo Runtime Gripper Joint Properties

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
source devel/setup.bash already executed
```

Safety boundary:

- Read-only `/gazebo/get_joint_properties` calls.
- No hand controller was loaded or started.
- No gripper command was sent.

Command:

```bash
for j in \
  oberon7_l/finger_left_joint \
  oberon7_l/finger_tip_left_joint \
  oberon7_l/finger_right_joint \
  oberon7_l/finger_tip_right_joint \
  oberon7_r/finger_left_joint \
  oberon7_r/finger_tip_left_joint \
  oberon7_r/finger_right_joint \
  oberon7_r/finger_tip_right_joint
do
  timeout 3s rosservice call /gazebo/get_joint_properties "{joint_name: '$j'}"
done
```

Result summary:

- Gazebo returned `success: True` for all eight gripper joints.
- Gazebo reported `type: 0` for all eight gripper joints.
- Gazebo reported `damping: []` for all eight gripper joints.
- Every sampled joint had a nonzero runtime rate.

Representative main-finger runtime rates:

```text
oberon7_l/finger_left_joint:
  position:  0.0005289406
  rate:     -0.2292318426

oberon7_l/finger_right_joint:
  position: -0.0004096008
  rate:     -0.1058246144

oberon7_r/finger_left_joint:
  position:  0.0007259333
  rate:     -0.3551586906

oberon7_r/finger_right_joint:
  position:  0.0004099235
  rate:     -0.5804416846
```

Zero-range finger-tip runtime rates:

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

Decision:

```text
B2b remains unresolved.
```

What this round confirms:

- Gazebo runtime agrees that the gripper joints are present.
- Zero-range finger-tip joints are not effectively fixed in the running Gazebo
  model.
- The finger-tip joints can report positions outside their URDF zero range and
  nonzero rates.
- Gazebo's joint-property service does not expose the URDF damping/friction
  values for these joints in the reported `damping` field.

Updated classification:

```text
baseline model / Gazebo physics / zero-range transmitted revolute joint /
controller-interface mismatch blocker
```

Implications:

- Do not publish gripper commands yet.
- Do not treat `hand_position_l` load/start as a fix.
- Before editing any file, inspect whether the finger/finger-tip links are
  dynamic bodies under gravity/contact and whether PID gains exist for these
  gripper joints in the running ROS parameter tree.

Next minimum check:

```text
read-only Gazebo link properties for finger links plus runtime PID/gain params
```

## Round 42: B2b Gripper Link Dynamics And Controller Param Listing

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
source devel/setup.bash already executed
```

Safety boundary:

- Read-only `/gazebo/get_link_properties` calls.
- Read-only `rosparam list` query.
- No hand controller was loaded or started.
- No gripper command was sent.

Gazebo link-property result:

- `success: True` for all left/right finger and finger-tip links.
- All sampled links reported `gravity_mode: True`.
- Main finger links reported:

  ```text
  mass: 0.879771
  com: [0.025268, -0.001931, -0.000079]
  inertia:
    ixx: 0.00378331
    iyy: 0.00886148
    izz: 0.00919231
  ```

- Finger-tip links reported:

  ```text
  mass: 1.12551
  com: [0.027744, 0.017278, 0.0]
  inertia:
    ixx: 0.00611047
    iyy: 0.0134903
    izz: 0.0121556
  ```

Runtime parameter listing:

- Hand-controller params exist for:

  ```text
  /oberon7/hand_position_l
  /oberon7/hand_position_r
  /oberon7/hand_effort_l
  /oberon7/hand_effort_r
  /oberon7/joint_group_hand_l_position_controller
  /oberon7/joint_group_hand_r_position_controller
  ```

- `hand_position_l` and `hand_effort_l` include constraints/gains for all four
  left gripper joints, including finger-tip joints.
- `hand_effort_r` includes constraints/gains for all four right gripper joints.
- Suspicious runtime-param-name finding:

  ```text
  /oberon7/hand_position_r/gains/oberon7_l/finger_left_joint/...
  /oberon7/hand_position_r/gains/oberon7_l/finger_right_joint/...
  /oberon7/hand_position_r/gains/oberon7_l/finger_tip_left_joint/...
  /oberon7/hand_position_r/gains/oberon7_l/finger_tip_right_joint/...
  ```

  The right hand position controller appears to have gains keyed by left-hand
  joint names. This may be a controller YAML copy/paste bug, but exact param
  values and source YAML must be checked before changing anything.

Decision:

```text
B2b remains unresolved.
```

Updated interpretation:

- The finger-tip links are dynamic, gravity-enabled bodies with substantial
  mass.
- They are attached through zero-range, zero-effort, zero-velocity revolute
  joints that still have position-interface transmissions.
- Gazebo reports nonzero rates on those zero-range joints.
- Runtime hand controller params include the finger-tip joints as controlled
  joints.
- The combined evidence points to a model/controller configuration mismatch,
  not an expert/policy command problem.

Next minimum check:

```text
read exact hand controller parameter dictionaries and source YAML snippets
```

Purpose:

- Confirm exact `joints`, `constraints`, and `gains` for
  `hand_position_l/r`, `hand_effort_l/r`, and group hand controllers.
- Verify whether `hand_position_r` actually has left-hand gain keys.
- Decide whether the safest package-local fix should be:
  - exclude zero-range finger-tip joints from command controllers;
  - add/override package-local gripper hold config;
  - or leave gripper blocked and continue arm-only until the upstream model is
    fixed.

Still prohibited:

- Do not publish gripper trajectories.
- Do not start hand controllers as a fix.
- Do not train or evaluate grasp success.

## Round 43: B2b Exact Hand Controller Params

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
source devel/setup.bash already executed
```

Safety boundary:

- Read-only `rosparam get` checks.
- Read-only source YAML inspection.
- No hand controller was loaded or started.
- No gripper command was sent.

Runtime controller params inspected:

```text
/oberon7/hand_position_l
/oberon7/hand_position_r
/oberon7/hand_effort_l
/oberon7/hand_effort_r
/oberon7/joint_group_hand_l_position_controller
/oberon7/joint_group_hand_r_position_controller
```

Confirmed common pattern:

- All hand trajectory controllers include four joints:

  ```text
  finger_left_joint
  finger_tip_left_joint
  finger_right_joint
  finger_tip_right_joint
  ```

- Therefore the zero-range finger-tip joints are included in the command
  controller joint lists.
- Group hand position controllers also include the same four joints.

Left hand params:

- `hand_position_l` and `hand_effort_l` use left-hand joints.
- Their gains are keyed by `oberon7_l/...`.
- The gain values are:

  ```text
  p: 1000.0
  i: 1.0
  d: 0.5
  ```

Right hand params:

- `hand_effort_r` uses right-hand joints and right-hand gain keys.
- `hand_position_r` uses right-hand joints but left-hand gain keys:

  ```text
  hand_position_r.joints:
    oberon7_r/finger_left_joint
    oberon7_r/finger_tip_left_joint
    oberon7_r/finger_right_joint
    oberon7_r/finger_tip_right_joint

  hand_position_r.gains:
    oberon7_l/finger_left_joint
    oberon7_l/finger_tip_left_joint
    oberon7_l/finger_right_joint
    oberon7_l/finger_tip_right_joint
  ```

Source YAML:

The active launch loads:

```text
src/uvms/data_rexrov_dual_oberon7/config/oberon7_controllers.yaml
```

Read-only source inspection confirms the same issue in that file:

```text
hand_position_r:
  joints:
    oberon7_r/finger_...
  gains:
    oberon7_l/finger_...
```

Decision:

```text
B2b remains unresolved.
```

What this round resolves diagnostically:

- The right-hand position controller has a real gain-key configuration bug.
- Both left and right hand controllers include the zero-range finger-tip joints
  as command-controller joints.
- The controller config source is identified.

Why this does not solve B2b:

- Clean-baseline gripper movement occurs before any hand controller is loaded or
  running.
- Therefore the `hand_position_r` gains bug is not the cause of the baseline
  motion.
- It is still a blocker for any future right-hand controller test and should be
  fixed before using right-hand position control.

Current best diagnosis:

```text
baseline model/interface issue plus controller config defects:
  1. dynamic gravity-enabled finger-tip links;
  2. zero-range transmitted revolute finger-tip joints;
  3. finger-tip joints included in hand command controllers;
  4. hand_position_r gains keyed to left-hand joints.
```

Next minimum safe direction:

- Do not publish gripper commands.
- Do not start hand controllers as a fix.
- If code/config changes are attempted later, they should be isolated and
  package-local when possible:
  - left-gripper-only controller config excluding finger-tip joints;
  - corrected right-hand gain keys;
  - or a documented decision to keep gripper blocked and proceed arm-only until
    upstream model/controller config is fixed.

## Round 44: Route Change To Arm-Only Reaching And B5d' Precheck

Date: 2026-05-03

Route decision:

```text
short-term demo route changes from full grasping to arm-only reaching /
pre-grasp positioning
```

Reason:

- B2b gripper diagnosis shows the gripper blocker is not a simple command-topic
  issue.
- Clean-baseline gripper joints move without hand controllers or command
  publishers.
- Finger-tip links are dynamic and gravity-enabled.
- Finger-tip joints are zero-range, zero-effort, zero-velocity revolute joints
  with position-interface transmissions.
- Existing hand controllers include those zero-range finger-tip joints in their
  command lists.
- `hand_position_r` has a confirmed gain-key namespace bug.

Explicitly skipped for the current route:

```text
B5d: gripper command integration
B5e: arm + gripper scripted grasp smoke
```

New debug target:

```text
B5d': arm-only scripted reaching expert
```

Task definition for this route:

```text
RexROV + single-active-left Oberon7 arm-only reaching / pre-grasp positioning
```

Success metric naming:

```text
reaching_success or pregrasp_success
```

Do not claim:

- object grasped;
- object lifted;
- object held;
- real grasp success rate;
- real underwater grasping complete.

Runtime context for the precheck:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
source devel/setup.bash already executed
```

Read-only / low-risk prerequisite checks:

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
  status_message: model does not exist

/gazebo/model_states:
  cylinder_target not found
```

Decision:

```text
B5d' is not ready to run yet.
```

What passed:

- MoveIt `/compute_ik` is available.
- EEF TF is available.

What failed:

- Left-arm command topic is absent because `oberon7/arm_position_l` is not
  loaded/running in this clean runtime.
- Static `cylinder_target` is absent.

No code change needed for this finding.

Next minimum step:

- Load/start only `oberon7/arm_position_l`.
- Spawn the package-local static target as `cylinder_target`.
- Re-run the same precheck.
- Do not load/start any hand controller.
- Do not publish gripper commands.

Still not part of B5d':

- gripper command/control;
- hand controller startup;
- BC/DP/FM training;
- long simulation;
- real policy rollout;
- grasp success evaluation.

## Round 45: B5d' Prerequisites Restored

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
source devel/setup.bash already executed
```

Commands run:

```bash
rosservice call /controller_manager/load_controller "{name: 'oberon7/arm_position_l'}"
rosservice call /controller_manager/switch_controller \
  "{start_controllers: ['oberon7/arm_position_l'], stop_controllers: [], strictness: 2, start_asap: false, timeout: 5.0}"
rosservice call /controller_manager/list_controllers "{}"

rosrun gazebo_ros spawn_model \
  -sdf \
  -file $(rospack find rexrov_single_oberon7_fm_dp)/models/cylinder_target_static/model.sdf \
  -model cylinder_target \
  -x 2.6 -y 2.0 -z -40.0

rosservice call /gazebo/get_model_state "{model_name: 'cylinder_target', relative_entity_name: 'world'}"
rostopic info /oberon7/arm_position_l/command
```

Result:

```text
load_controller oberon7/arm_position_l:
  ok: True

switch_controller start oberon7/arm_position_l:
  ok: True

list_controllers:
  joint_state_controller: running
  oberon7/arm_position_l: running
```

`oberon7/arm_position_l` claimed only the active-left arm resources:

```text
oberon7_l/azimuth
oberon7_l/elbow
oberon7_l/pitch
oberon7_l/roll
oberon7_l/shoulder
oberon7_l/wrist
```

No hand/gripper controller was loaded or started.

Static target:

```text
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
B5d' prerequisites are restored, but B5d' itself is not solved yet.
```

What passed:

- left-arm command path exists and is running;
- MoveIt IK was already available from the precheck;
- static target is present and stable;
- no hand/gripper controller was started.

Next minimum step:

- Run a read-only non-fallback recorder baseline with `execute_arm:=false` to
  measure initial eef-target/pregrasp distance from recorded `eef_pose` and
  `target_pose`.
- Then run the shortest possible arm-only reaching smoke, or modify the expert
  first if the existing fixed-delta state machine cannot be made target-directed
  safely.

Still not allowed:

- gripper commands;
- hand controller startup;
- grasp-success claims;
- training;
- long simulation.

## Round 46: B5d' Non-Control Baseline Recorder Passed But Target Is Unreachable

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
oberon7/arm_position_l running
static cylinder_target spawned
source devel/setup.bash already executed
```

Command:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=.../data/raw/b5d_reaching_precheck \
  episode_id:=b5d_reaching_baseline_no_control \
  rate_hz:=2.0 \
  max_duration_sec:=2.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=false \
  enable_gripper_command:=false
```

Runtime log:

```text
Scripted expert running with target source gazebo_model_states and target pose
[2.6, 2.0, -40.0, 0.0, 0.0, 0.0, 1.0]
execute_arm=False gripper_command_enabled=False
Recording episode b5d_reaching_baseline_no_control: 4 samples at 2.000 Hz
Saved episode to .../b5d_reaching_baseline_no_control.npz
```

Validation:

```text
validation: PASS
T: 4
success: False
unavailable_fields: ['raw_command']
WARNING: raw_command contains NaN because metadata marks it unavailable
```

Metadata:

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
target_first:
  [2.6, 2.0, -40.0]

eef_first:
  [-40.2129914966344, -3.839671742860088, -99.75204165781498]

initial_distance:
  73.73846004109731 m

final_distance:
  73.86181687780048 m

min_distance:
  73.73846004109731 m
```

Decision:

```text
B5d' is not solved.
```

What passed:

- Non-fallback recorder path works for B5d'.
- `target_pose`, `eef_pose`, `relative_target_to_eef`, and `action_ee_delta`
  are all available.
- `target_state_source` is `gazebo_model_states`.
- Gripper remains disabled.

What failed:

- The current static target is far outside the current arm-only reachable
  workspace.
- The recorded EEF world pose is around `z=-99.75`, while the static target is
  at `z=-40.0`.
- A reaching smoke against this target would be invalid because the target
  placement is wrong for the current drifted RexROV pose.

Interpretation:

- This is a B5d' task setup/pregrasp placement issue, not a recorder failure.
- Before testing arm command execution, move or respawn the static target near
  the current EEF/pregrasp workspace and re-check initial distance.

Next minimum step:

- Reposition `cylinder_target` near the current EEF world pose using Gazebo
  model state, or delete/re-spawn the static target at a current EEF-relative
  world pose.
- Re-run the non-control baseline and confirm initial distance is finite and
  near the intended reaching threshold/workspace scale.

Still not allowed:

- gripper commands;
- hand controller startup;
- training;
- long simulation;
- grasp-success claims.

## Round 47: B5d' Near-Target Baseline Still Too Far Due To Stale EEF Pose

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
oberon7/arm_position_l running
static cylinder_target present
source devel/setup.bash already executed
```

Target reposition command:

- The target was repositioned using the previous baseline episode's final
  recorded `eef_pose`.

Set target result:

```text
set_model_state success: True
status: SetModelState: set model state done
new_target_xyz:
  [-40.32524771314997, -3.8380501244831398, -99.71209805902916]
```

Readback:

```text
/gazebo/get_model_state cylinder_target:
  success: True
  position:
    [-40.32524771314997, -3.8380501244831398, -99.71209805902916]
  orientation:
    [0.0, 0.0, 0.0, 1.0]
  twist.linear:
    [0.0, 0.0, 0.0]
  twist.angular:
    [0.0, 0.0, 0.0]
```

No-control baseline command:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=.../data/raw/b5d_reaching_precheck \
  episode_id:=b5d_reaching_baseline_near_target \
  rate_hz:=2.0 \
  max_duration_sec:=2.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=false \
  enable_gripper_command:=false
```

Validation:

```text
validation: PASS
T: 4
success: False
unavailable_fields: ['raw_command']
```

Metadata:

```text
field_availability:
  action_ee_delta: True
  eef_pose: True
  raw_command: False
  relative_target_to_eef: True
  target_pose: True

allow_nominal_state_fallback: False
target_state_source: gazebo_model_states
```

Distance result:

```text
target_first:
  [-40.32524771314997, -3.8380501244831398, -99.71209805902916]

eef_first:
  [-50.70703373594152, -4.015825629082565, -99.75201271243112]

initial_distance:
  10.383384724290138 m

final_distance:
  10.563886255042627 m

min_distance:
  10.383384724290138 m
```

Decision:

```text
B5d' is still not solved.
```

What passed:

- Target reposition service worked.
- Target remained a live Gazebo model-state source.
- Non-fallback recorder baseline passed validation.

What failed:

- The target was not near the EEF at episode start.
- The target placement was based on a stale recorded EEF pose from the previous
  episode.
- The EEF world pose drifted by about 10 m before the next episode baseline was
  recorded.

Interpretation:

- B5d' has a task-placement/time-sync problem in the current drifting
  world-frame setup.
- A reaching smoke test should not be attempted until the target is placed from
  the current live EEF world pose immediately before the episode.
- Longer term, B5d' may need a base-relative target/pregrasp definition or base
  stabilization, but the next check should remain minimal and runtime-only.

Next minimum step:

- Compute current live EEF world pose from `/rexrov/pose_gt` plus
  `rexrov/base_link -> oberon7_l/end_effector` TF immediately before setting
  the target.
- Set target near that live pose.
- Immediately re-run the no-control baseline and check initial distance.

Still not allowed:

- gripper commands;
- hand controller startup;
- training;
- long simulation;
- grasp-success claims.

## Round 48: B5d' Live EEF Target Placement Still Drifts Before Baseline

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
oberon7/arm_position_l running
static cylinder_target present
source devel/setup.bash already executed
```

Live placement script result:

```text
set_model_state success: True
status: SetModelState: set model state done

base_world:
  [-69.52104407468721, -4.476964239028076, -98.54334253085695]

eef_base_tf:
  [2.0708814125823, 0.4984930547418398, -1.310037055627614]

eef_world_live:
  [-67.34184073023106, -4.272243987204881, -99.7526417658384]

new_target_xyz:
  [-67.24184073023106, -4.272243987204881, -99.7126417658384]

expected_distance:
  0.10770329614268713 m
```

Target readback:

```text
/gazebo/get_model_state cylinder_target:
  success: True
  position:
    [-67.24184073023106, -4.272243987204881, -99.7126417658384]
  twist.linear:
    [0.0, 0.0, 0.0]
  twist.angular:
    [0.0, 0.0, 0.0]
```

No-control baseline:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=.../data/raw/b5d_reaching_precheck \
  episode_id:=b5d_reaching_baseline_live_near_target \
  rate_hz:=2.0 \
  max_duration_sec:=2.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=false \
  enable_gripper_command:=false
```

Validation:

```text
validation: PASS
T: 4
success: False
unavailable_fields: ['raw_command']
```

Metadata:

```text
field_availability:
  action_ee_delta: True
  eef_pose: True
  raw_command: False
  relative_target_to_eef: True
  target_pose: True

allow_nominal_state_fallback: False
target_state_source: gazebo_model_states
```

Recorded distance:

```text
target_first:
  [-67.24184073023106, -4.272243987204881, -99.7126417658384]

eef_first:
  [-68.57055780475194, -3.9736012548043984, -99.75216038267928]

initial_distance:
  1.362438353400245 m

final_distance:
  1.5364981412648813 m

min_distance:
  1.362438353400245 m
```

Decision:

```text
B5d' remains unresolved.
```

What passed:

- Live placement service worked.
- Target remained available from Gazebo model states.
- Non-fallback recorder validation still passes.
- Gripper remained disabled.

What failed:

- Set-time target distance was about 0.108 m, but first recorded episode sample
  was already about 1.36 m away.
- Distance increased during the 2 s no-control baseline.

Interpretation:

- The current world-frame setup has enough RexROV/base drift that a static
  world target becomes stale before/while the recorder episode starts.
- A B5d' arm command smoke would not cleanly measure arm-only reaching yet,
  because target distance is dominated by base/world drift and task placement
  timing.

Next minimum check:

- Measure EEF/base drift over a short 2-5 second window with no arm command and
  no target movement.
- Use that to decide whether B5d' should:
  - run in a much shorter immediate target-placement/execution window;
  - use a base-relative/dynamic target placement helper;
  - or first stabilize/hold the RexROV base for the arm-only reaching smoke.

Still not allowed:

- gripper commands;
- hand controller startup;
- training;
- long simulation;
- grasp-success claims.

## Round 49: B5d' Live Near-Target Baseline Confirms Base/World Drift Blocker

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
oberon7/arm_position_l running
static cylinder_target present
source devel/setup.bash already executed
```

Live target placement:

```text
set_model_state success: True
status: SetModelState: set model state done
base_world:
  [-69.52104407468721, -4.476964239028076, -98.54334253085695]
eef_base_tf:
  [2.0708814125823, 0.4984930547418398, -1.310037055627614]
eef_world_live:
  [-67.34184073023106, -4.272243987204881, -99.7526417658384]
new_target_xyz:
  [-67.24184073023106, -4.272243987204881, -99.7126417658384]
expected_distance:
  0.10770329614268713 m
```

Readback:

```text
/gazebo/get_model_state cylinder_target:
  success: True
  position:
    [-67.24184073023106, -4.272243987204881, -99.7126417658384]
  twist.linear:
    [0.0, 0.0, 0.0]
  twist.angular:
    [0.0, 0.0, 0.0]
```

No-control baseline:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=.../data/raw/b5d_reaching_precheck \
  episode_id:=b5d_reaching_baseline_live_near_target \
  rate_hz:=2.0 \
  max_duration_sec:=2.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=false \
  enable_gripper_command:=false
```

Validation:

```text
validation: PASS
T: 4
success: False
unavailable_fields: ['raw_command']
```

Metadata:

```text
field_availability:
  action_ee_delta: True
  eef_pose: True
  raw_command: False
  relative_target_to_eef: True
  target_pose: True

allow_nominal_state_fallback: False
target_state_source: gazebo_model_states
```

Distance result:

```text
target_first:
  [-67.24184073023106, -4.272243987204881, -99.7126417658384]

eef_first:
  [-68.57055780475194, -3.9736012548043984, -99.75216038267928]

initial_distance:
  1.362438353400245 m

final_distance:
  1.5364981412648813 m

min_distance:
  1.362438353400245 m
```

Decision:

```text
B5d' is not solved.
```

What passed:

- Live placement from `/rexrov/pose_gt` plus TF worked.
- Static target remained available from `/gazebo/model_states`.
- Recorder wrote a non-fallback episode and validator passed.
- Gripper stayed disabled and no hand controller was started.

What failed:

- The target was placed about `0.108 m` from the live EEF at set time, but the
  first recorder sample was already about `1.36 m` away.
- Distance increased during the 2 s no-control baseline.

Interpretation:

- The current B5d' failure is dominated by RexROV/base drift in the world-frame
  setup and target-placement timing.
- This is not evidence that the B5a converter or recorder validation failed.
- A multi-step arm-reaching command should not be sent yet, because the smoke
  would not cleanly measure arm-only reaching toward the static target.

Next minimum check:

- Measure live base and EEF world drift over a short no-command window.
- If drift is large, choose the next B5d' task setup route explicitly:
  - a shorter integrated target-placement plus execution window;
  - a package-local base-relative/dynamic target helper for smoke tests;
  - or base stabilization/hold before arm-only reaching.

Still not allowed:

- gripper commands;
- hand controller startup;
- training;
- long simulation;
- rollout or grasp-success claims.

## Round 50: B5d' No-Command Drift Measurement

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
oberon7/arm_position_l running
static cylinder_target present
source devel/setup.bash already executed
```

Measurement:

- User sampled `/rexrov/pose_gt` plus TF
  `rexrov/base_link -> oberon7_l/end_effector`.
- No arm command was sent.
- No gripper command was sent.
- No hand controller was started.

Result:

```text
sample window:
  sim_t 2749.154 -> 2753.004
  duration: 3.85 s

base_drift_total_m:
  0.6695749498121972

eef_drift_total_m:
  0.5760234188002605

eef_drift_rate_mps:
  0.14961647241565562
```

Representative EEF world poses:

```text
first:
  [-63.2465417364064, -5.289317470101548, -99.7517287489803]

last:
  [-63.20298357308517, -5.863691564598733, -99.75198367045911]
```

Decision:

```text
B5d' remains unresolved.
```

What this confirms:

- The EEF world pose drifts about `0.58 m` in under 4 s even without arm
  command.
- The measured `~0.15 m/s` EEF drift is larger than the intended first reaching
  threshold scale of `0.05-0.10 m`.
- A world-static target reaching smoke would be dominated by base/world drift
  and would not cleanly validate arm-only reaching.

What remains valid:

- This does not invalidate the B5a converter.
- This does not invalidate recorder non-fallback state capture.
- This does not change the gripper blocker.

Next minimum check:

- Read-only inspect whether the current runtime exposes an existing RexROV base
  hold / DP / station-keeping interface.
- If an existing base hold interface is present, use that as the next safe task
  setup candidate before arm reaching.
- If no such interface exists, move B5d' toward a package-local base-relative or
  dynamic-target smoke helper, or a tightly integrated immediate
  target-placement plus execution helper.

Still not allowed:

- gripper commands;
- hand controller startup;
- training;
- long simulation;
- rollout or grasp-success claims.

## Round 51: B5d' Base-Hold Interface Check

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
oberon7/arm_position_l running
static cylinder_target present
source devel/setup.bash already executed
```

Read-only checks:

```bash
rostopic list | grep -E "rexrov/(cmd|thruster|dp|trajectory|waypoint|hold)|dp|station|hold|controller|thruster"
rosnode list | grep -E "dp|station|hold|thruster|controller|rexrov"
rosparam list | grep -E "dp|station|hold|thruster|controller|rexrov"
rosservice list | grep -E "dp|station|hold|thruster|controller|rexrov"
timeout 5s rosservice call /controller_manager/list_controllers "{}"
```

Key runtime findings:

- Topics expose low-level thruster infrastructure:
  - `/rexrov/thruster_manager/input`
  - `/rexrov/thruster_manager/input_stamped`
  - `/rexrov/thrusters/*/input`
  - `/rexrov/thrusters/*/thrust`
  - `/rexrov/thrusters/*/thrust_wrench`
- Nodes matched only:
  - `/rexrov/thruster_allocator`
- Services expose thruster manager, thruster state/config, and vehicle
  hydrodynamic parameter services.
- No read-only output showed a running DP, station-keeping, waypoint, hold, or
  high-level base controller node/action/service.
- Controller manager still reports:
  - `joint_state_controller: running`
  - `oberon7/arm_position_l: running`
- No hand/gripper controller is running.

Decision:

```text
B5d' remains unresolved, and an existing base-hold interface is not available in the current launch.
```

Interpretation:

- The current runtime has low-level thruster allocation/manager plumbing, but
  not a ready high-level RexROV base hold or DP interface.
- Implementing or tuning base hold is a separate controller task and is not the
  minimum B5d' arm-only reaching smoke.
- Because measured EEF/world drift is about `0.15 m/s`, B5d' should not use a
  long world-static target reaching smoke.

Next minimum step:

- Move B5d' toward a package-local task setup helper, checked read-only/static
  first:
  - option A: base-relative/dynamic target helper that keeps the Gazebo target
    near the current EEF/pregrasp reference during a short smoke;
  - option B: tightly integrated immediate target-placement plus short
    arm-command execution helper to minimize stale target time.
- Prefer option A for cleaner recorder evidence because `target_pose` can remain
  live from `/gazebo/model_states` while staying near the drifting base/EEF.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands without a separate safety plan;
- training;
- long simulation;
- rollout or grasp-success claims.

## Round 52: B5d' Base-Relative Target-Only Smoke

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
oberon7/arm_position_l running
static cylinder_target present
source devel/setup.bash already executed
```

Smoke command behavior:

- The user ran a target-only Python smoke.
- It computed a fixed target pose in `rexrov/base_link` frame:

  ```text
  target_base = current_eef_base + [0.10, 0.0, 0.04]
  ```

- It repeatedly transformed that base-frame target into world coordinates and
  called `/gazebo/set_model_state`.
- No arm command was sent.
- No gripper command was sent.
- No thruster or base command was sent.

Result:

```text
all 20 updates:
  set_ok True

target_base:
  [2.1708558381948855, 0.49849956648740684, -1.270042197863489]

initial_distance:
  0.10763503700570734 m

final_distance:
  0.10754083126294889 m

min_distance:
  0.10754083126294889 m

max_distance:
  0.10768849201959516 m
```

Decision:

```text
B5d' task-setup sub-blocker is minimally resolved, but B5d' full arm-only reaching smoke is not complete yet.
```

What this confirms:

- A base-relative/dynamic target setup can keep the target near the EEF despite
  the measured world-frame RexROV/base drift.
- The EEF-target distance stayed around `0.108 m` instead of drifting toward
  meter-scale error.
- This is a clean B5d' setup path for arm-only reaching/pre-grasp smoke.

Code changes made:

- Added `src/rexrov_single_oberon7_fm_dp/base_relative_target.py`.
- Added `scripts/base_relative_target.py`.
- Added the script to `catkin_install_python`.
- Added optional `collect_episode.launch` args:
  - `enable_base_relative_target`
  - `base_relative_target_rate_hz`
  - `base_relative_target_offset_x`
  - `base_relative_target_offset_y`
  - `base_relative_target_offset_z`
  - `base_relative_target_wait_timeout_sec`
- Added an optional `b5d_base_relative_target` node to
  `collect_episode.launch`.
- The helper is disabled by default, so existing launch behavior is unchanged.

Verification:

```text
python3 -m py_compile:
  base_relative_target.py module: PASS
  base_relative_target.py script wrapper: PASS
```

Next minimum check:

- Run a short non-fallback recorder smoke with:
  - `enable_base_relative_target:=true`
  - `execute_arm:=false`
  - `enable_gripper_command:=false`
  - `allow_nominal_state_fallback:=false`
- Validate the episode and inspect recorded initial/final/min/max distance.
- If recorded distance stays near `0.108 m`, proceed to the first tiny
  arm-only B5d' reaching smoke.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- rollout or grasp-success claims.

## Round 83: B8' Target Base-Frame Jitter Identified, Target Updater Rate Raised

Date: 2026-05-04

User runtime context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
rexrov_single_oberon7_fm_dp load_left_controllers.launch \
  start:=true \
  load_hand:=false
world_base_tf_bridge.launch running
```

Input episode:

```text
data/raw/b8_reaching_smoke_tf_bridge_check/b8_reaching_smoke_tf_bridge_check_0000.npz
```

Previously recorded diagnostics for this episode:

```text
validator: PASS
T: 16
success: False
unavailable_fields: ['raw_command']

quality:
  episodes_below_threshold: 0
  initial_distance: 0.12896387383800806
  min_distance_overall: 0.12272243911393374
  final_distance: 0.12671316334997665
  mean_distance_reduction: 0.00225071048803141

command-to-motion:
  mean_best_action_to_eef_cosine: 0.38837550274847654
  mean_best_realized_gain_along_action: 0.10417398838872995

direction:
  mean_eef_motion_cosine_with_target: 0.008830359482655255
  mean_eef_positive_target_direction_ratio: 0.4666666666666667
```

Latest read-only per-sample geometry check:

```text
idx time dist target_step_base eef_step_base
0  24705.670 0.128964 0.000000 0.000000
1  24706.002 0.126755 0.040124 0.004243
2  24706.334 0.164869 0.085102 0.005223
3  24706.668 0.129052 0.039788 0.004655
4  24706.998 0.131814 0.047943 0.004540
5  24707.330 0.136312 0.078691 0.003333
6  24707.662 0.126970 0.048615 0.002003
7  24707.992 0.130072 0.039357 0.006750
8  24708.324 0.151312 0.082623 0.004262
9  24708.656 0.122722 0.053732 0.003649
10 24708.988 0.132673 0.039518 0.002880
11 24709.320 0.131865 0.089075 0.004843
12 24709.642 0.136702 0.070372 0.002414
13 24709.976 0.128264 0.021237 0.003678
14 24710.310 0.129891 0.088199 0.003914
15 24710.642 0.126713 0.054798 0.002195

max_target_step: 0.08907516876353049
max_eef_step:    0.006750324744116928
```

Decision:

```text
B8' reaching-quality blocker remains open.
The world/base TF bridge sub-blocker is smoke-level resolved, but the target
base-frame geometry is still unstable at the episode sample scale.
```

Interpretation:

- The TF bridge improved command-to-motion coupling compared with pre-bridge
  tuned v2, but it did not solve reaching quality.
- No episode/sample crossed the `0.10 m` reaching threshold.
- Target base-frame jumps reach about `0.089 m`, while EEF base-frame steps
  are at most about `0.00675 m`; target motion dominates the recorded reaching
  geometry.
- The next bounded fix should reduce target updater lag/jitter before any
  further expert tuning, larger collection, training, or rollout.

Code change:

- Updated `launch/b8_reaching_tuned_v2_episode.launch`:
  - set `base_relative_target_rate_hz` to `30.0`.

Why:

- The previous tuned v2 wrapper inherited the base-relative target updater's
  slower default rate. With a drifting RexROV base, a low-rate target update can
  produce large target-base jumps between recorder samples.
- Increasing the target updater frequency is the smallest package-local change
  that directly targets the measured blocker.

Verification:

```text
xmllint --noout launch/b8_reaching_tuned_v2_episode.launch: PASS
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v2_episode.launch --ros-args: PASS
```

Next minimum check:

```text
Run exactly one short B8' TF-bridge + target30 validation episode, validate it,
and rerun offline quality, direction, and command-to-motion diagnostics.
Do not collect a 5-episode set, train, rollout, or send gripper commands.
```

## Round 84: B8' Target30 Episode Improved Direction But Still Missed Threshold

Date: 2026-05-04

User runtime context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
rexrov_single_oberon7_fm_dp load_left_controllers.launch \
  start:=true \
  load_hand:=false
world_base_tf_bridge.launch running
```

Command under test:

```bash
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v2_episode.launch \
  output_dir:=.../data/raw/b8_reaching_smoke_tf_bridge_target30_check \
  episode_id:=b8_reaching_smoke_tf_bridge_target30_check_0000 \
  target_model_name:=cylinder_target_b8_tf_bridge_target30_check_0000
```

Important runtime confirmation:

```text
/b5d_base_relative_target/rate_hz: 30.0
```

Episode:

```text
data/raw/b8_reaching_smoke_tf_bridge_target30_check/b8_reaching_smoke_tf_bridge_target30_check_0000.npz
```

Validation:

```text
validation: PASS
T: 16
success: False
episode_id: b8_reaching_smoke_tf_bridge_target30_check_0000
unavailable_fields: ['raw_command']
```

Quality diagnostic:

```text
episodes_total: 1
episodes_below_threshold: 0
episodes_with_positive_distance_reduction: 1
initial_distance: 0.12549968637530884 m
min_distance_overall: 0.12160315011478852 m
final_distance: 0.12413588250680598 m
mean_distance_reduction: 0.0013638038685028636 m
max_active_left_joint_delta: 0.04081576279364185 rad
action_xyz_norm_mean_all_samples: 0.013504182785515031
action_xyz_norm_max_all_samples: 0.015136546393841514
recommendation: A
```

Direction diagnostic:

```text
episodes_total: 1
episodes_below_threshold: 0
episodes_with_positive_distance_reduction: 1
mean_distance_reduction_base: 0.0013638038685029608
min_distance_overall_base: 0.12160315011478864
mean_action_to_eef_motion_cosine: 0.6983946289035002
mean_eef_motion_cosine_with_target: 0.4453145000526829
mean_eef_positive_target_direction_ratio: 0.8
recommendation: do_not_collect_more_until_direction_issue_is_understood
```

Decision:

```text
B8' reaching-quality blocker remains open.
```

Interpretation:

- Compared with the earlier TF-bridge episode, directional behavior improved:
  - action-to-EEF cosine improved from about `0.388` to about `0.698`;
  - EEF-to-target cosine improved from about `0.009` to about `0.445`;
  - positive target-direction ratio improved from about `0.467` to `0.8`.
- However, the episode still did not cross the `0.10 m` reaching threshold:
  `min_distance_overall` is about `0.1216 m`.
- Distance reduction is positive but very small, about `0.00136 m`.
- This is valid non-fallback smoke data, but not enough to expand collection
  or train.

No functional code change in this round.

Next minimum read-only check:

```text
Run command-to-motion diagnostic on the target30 episode and inspect the
target30 direction diagnostic markdown for target_base net/max-step.
```

Purpose:

- Confirm whether the 30 Hz target updater reduced base-frame target jumps.
- Confirm whether command-to-motion coupling and lag improved consistently
  with the direction diagnostic.

Expected success signal:

- target_base max-step is much lower than the previous `0.089 m`;
- command-to-motion mean_best_action_to_eef_cosine remains high;
- best lag remains near 0.

Failure interpretation:

- If target_base max-step is still large, the blocker remains target update /
  Gazebo set_model_state timing.
- If target_base max-step is low but distance still stays above threshold, the
  next bounded change should tune reaching duration/step size, not gripper or
  training.

Follow-up command-to-motion diagnostic:

```text
episodes_total: 1
episodes_below_threshold: 0
mean_best_action_to_eef_cosine: 0.956902308613389
mean_best_lag_steps: 2.0
mean_best_realized_gain_along_action: 0.3194339452607246
recommendation: do_not_collect_more_until_command_to_motion_path_is_explained
```

Follow-up direction markdown:

```text
base distance initial/min/final/reduction:
  0.125500 / 0.121603 / 0.124136 / 0.001364
distance decreasing step ratio: 0.400000
eef base net/mean-step/max-step:
  0.044696 / 0.004615 / 0.007119
eef-motion cosine with target direction: 0.445315
eef positive target-direction ratio: 0.800000
action target/eef-motion cosine: 0.805218 / 0.698395
target base net/max-step:
  0.034005 / 0.014167
base world net/path:
  0.477275 / 0.481984
labels:
  threshold_not_reached, distance_not_consistently_decreasing,
  base_world_drift_present
```

Updated decision:

```text
B8' target updater jitter sub-blocker is smoke-level resolved.
B8' reaching-quality blocker remains open.
```

Updated interpretation:

- The 30 Hz target updater reduced the previous target base-frame max-step from
  about `0.089 m` to about `0.014 m`.
- Command-to-motion coupling is strong: mean best action-to-EEF cosine is about
  `0.957`.
- The best coupling appears at lag `2` recorder steps, about `0.67 s` at the
  current `3 Hz` recorder rate.
- The remaining issue is no longer missing `world -> rexrov/base_link` TF and
  no longer gross target updater jitter. It is short-horizon/lag-limited
  reaching quality: the episode still bottoms out at about `0.1216 m`, above
  the `0.10 m` threshold.

No code change in this round.

Next minimum read-only check:

```text
Inspect the command-motion markdown table for per-lag rows on the target30
episode before changing config. If lag-2 is clearly dominant, the next minimal
package-local change should be a tuned wrapper with a slightly longer horizon
or state durations, still gripper-disabled and still one-episode only.
```

Per-lag command-motion table:

```text
lag | samples | action/eef cos | eef/target cos | gain     | eef/action norm | dist-decrease ratio
0   | 15      | 0.698395       | 0.445315       | 0.226123 | 0.336145        | 0.400000
1   | 14      | 0.820193       | 0.537372       | 0.268557 | 0.335126        | 0.357143
2   | 13      | 0.956902       | 0.654001       | 0.319434 | 0.330313        | 0.384615
3   | 12      | 0.946611       | 0.776835       | 0.310540 | 0.324558        | 0.416667
```

Updated blocker judgment:

```text
B8' reaching-quality blocker remains open.
Target updater jitter is smoke-level resolved.
Command-to-motion coupling is strong but lagged by about 2-3 recorder steps.
```

Interpretation:

- Lag `2` is the best action-to-EEF coupling row.
- Lag `3` has the strongest EEF-to-target cosine and distance-decrease ratio.
- The episode is too short for the lagged response to reliably cross the
  `0.10 m` threshold.
- This justifies a minimal package-local horizon/state-duration tuning check.

Code/config change:

- Added `launch/b8_reaching_tuned_v3_episode.launch`.

Change target:

- Keep the current safe arm-only setup unchanged.
- Give the lagged command response more time to affect the recorded reaching
  metric.

Parameter differences from tuned v2:

```text
max_duration_sec: 5.2 -> 7.2
state_duration_MOVE_TO_PREGRASP: 3.0 -> 4.0
state_duration_MOVE_TO_GRASP: 2.0 -> 3.0
```

Parameters intentionally unchanged:

```text
rate_hz: 3.0
max_linear_step: 0.010
max_joint_delta: 0.010
base_relative_target_rate_hz: 30.0
gripper_enabled: false
enable_gripper_command: false
task_type: arm_only_reaching
success_metric: reaching_success
```

Verification:

```text
xmllint --noout launch/b8_reaching_tuned_v3_episode.launch: PASS
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v3_episode.launch --ros-args: PASS
```

Next minimum check:

```text
Run exactly one tuned v3 validation episode. Validate it and rerun quality,
direction, and command-to-motion diagnostics. Do not collect multiple episodes,
train, rollout, or send gripper commands.
```

## Round 85: B8' Tuned v3 Crossed Reaching Threshold Once

Date: 2026-05-04

User runtime context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
rexrov_single_oberon7_fm_dp load_left_controllers.launch \
  start:=true \
  load_hand:=false
world_base_tf_bridge.launch running
```

Command under test:

```bash
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v3_episode.launch \
  output_dir:=.../data/raw/b8_reaching_smoke_tuned_v3_check \
  episode_id:=b8_reaching_smoke_tuned_v3_check_0000 \
  target_model_name:=cylinder_target_b8_tuned_v3_check_0000
```

Runtime confirmation:

```text
/b5d_base_relative_target/rate_hz: 30.0
/dp_fm_episode_recorder/max_duration_sec: 7.2
/dp_fm_scripted_expert/state_duration_MOVE_TO_PREGRASP: 4.0
/dp_fm_scripted_expert/state_duration_MOVE_TO_GRASP: 3.0
```

Episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_check/b8_reaching_smoke_tuned_v3_check_0000.npz
```

Validation:

```text
validation: PASS
T: 22
success: False
episode_id: b8_reaching_smoke_tuned_v3_check_0000
unavailable_fields: ['raw_command']
```

Quality diagnostic:

```text
episodes_total: 1
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 1
initial_distance: 0.1264832193593639 m
min_distance_overall: 0.08480029669684241 m
final_distance: 0.12246726976236536 m
mean_distance_reduction: 0.004015949596998553 m
max_active_left_joint_delta: 0.06377453998389893 rad
action_xyz_norm_mean_all_samples: 0.013723604201309749
action_xyz_norm_max_all_samples: 0.016232047296442963
recommendation: A
```

Direction diagnostic:

```text
episodes_total: 1
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 1
mean_distance_reduction_base: 0.0040159495969987885
min_distance_overall_base: 0.08480029669684272
mean_action_to_eef_motion_cosine: 0.6652890486895977
mean_eef_motion_cosine_with_target: 0.5093671918914294
mean_eef_positive_target_direction_ratio: 0.8095238095238095
```

Command-to-motion diagnostic:

```text
episodes_total: 1
episodes_below_threshold: 1
mean_best_action_to_eef_cosine: 0.6652890486895977
mean_best_lag_steps: 0.0
mean_best_realized_gain_along_action: 0.19879837117714555
```

Decision:

```text
B8' reaching-quality blocker is smoke-level resolved for one tuned v3
validation episode crossing the 0.10 m threshold.
```

Limitations:

- This is only one episode.
- `success=False` and scripted expert finish reason still indicate the final
  distance was above the `0.10 m` threshold.
- The threshold crossing may be transient; distance consistency and hold/final
  behavior remain unverified.
- Do not expand collection, train, rollout, or claim success rate yet.

No code change in this round.

Next minimum read-only check:

```text
Inspect tuned v3 quality/direction markdown reports to determine how many
samples were below threshold, when the minimum occurred, and whether
target_base max-step stayed bounded.
```

Markdown inspection result:

```text
quality:
  distance initial/min/final/reduction:
    0.126483 / 0.084800 / 0.122467 / 0.004016
  below threshold: True
  final closer: True
  action xyz norm mean/max: 0.013724 / 0.016232
  clip fraction at max_linear_step: 0.561
  joint max delta / step max delta: 0.063775 / 0.006013
  target world/base motion: 0.374723 / 0.038119
  failure reason candidates:
    base_drift_dominates_world_eef

direction:
  distance decreasing step ratio: 0.523810
  eef base net/mean-step/max-step:
    0.049145 / 0.004544 / 0.009855
  target base net/max-step:
    0.038119 / 0.055363
  base world net/path:
    0.797345 / 0.799997
  labels:
    target_moves_in_base_frame, base_world_drift_present
```

Updated decision:

```text
B8' remains smoke-level resolved only.
```

Updated interpretation:

- The episode crossed threshold, but final distance rebounded to about
  `0.122 m`.
- Distance decreased in only about `52%` of steps.
- `target_base max-step` is about `0.055 m`, larger than the previous target30
  one-episode check. Target/base geometry is still a residual risk.
- This is not enough evidence to expand collection or train.

No code change in this round.

Next minimum read-only check:

```text
Run a per-sample NPZ trace check to count below-threshold samples and identify
the index/time of min distance and any target_base step spikes.
```

Per-sample trace result:

```text
samples: 22
below_count: 1
below_indices: [12]
min_idx: 12
min_distance: 0.08480029669684272
final_distance: 0.12246726976236501
max_target_step: 0.05536288107656983
max_target_step_idx: 13
```

Relevant rows:

```text
idx time      dist      below  target_step_base  eef_step_base
11  35699.628 0.127842  False  0.006681          0.004417
12  35699.960 0.084800  True   0.041232          0.004999
13  35700.294 0.132893  False  0.055363          0.006427
14  35700.624 0.131823  False  0.006147          0.004005
```

Updated decision:

```text
B8' remains smoke-level progress only, not resolved enough for repeatability
collection or training.
```

Interpretation:

- Only one recorded sample is below the `0.10 m` threshold.
- The below-threshold sample coincides with a large target base-frame step.
- The largest target base-frame step occurs immediately afterward and distance
  rebounds to about `0.133 m`.
- The remaining blocker is target/base geometry stability around threshold, not
  command execution or missing TF.

No code change in this round.

Next minimum check:

```text
Inspect the base-relative target updater implementation/config and make only a
package-local bounded change if needed to reduce target_base step spikes before
another one-episode validation.
```

Code change:

- Updated `src/rexrov_single_oberon7_fm_dp/base_relative_target.py`.
- Updated `launch/collect_episode.launch`.
- Updated `launch/b8_reaching_tuned_v3_episode.launch`.

Change details:

- `BaseRelativeTargetUpdater` now subscribes to `/rexrov/pose_gt` once and
  caches the latest base pose.
- `update_once()` uses a fresh cached pose instead of calling
  `rospy.wait_for_message()` for every target update.
- Added `max_base_pose_age_sec`, exposed as ROS param
  `base_relative_target_max_base_pose_age_sec`, default `0.25`.

Reason:

- The previous implementation could block irregularly at 30 Hz while the base
  odom topic publishes at about 20 Hz.
- The tuned v3 per-sample trace showed a transient threshold hit followed by a
  target_base step spike and distance rebound.
- This fix targets update timing jitter without changing gripper, arm command
  limits, training, rollout, or external packages.

Verification:

```text
python3 -m py_compile:
  src/rexrov_single_oberon7_fm_dp/base_relative_target.py: PASS
  scripts/base_relative_target.py: PASS
xmllint:
  collect_episode.launch: PASS
  b8_reaching_tuned_v3_episode.launch: PASS
roslaunch b8_reaching_tuned_v3_episode.launch --ros-args: PASS
```

Next minimum check:

```text
Run exactly one tuned v3 cached-odom validation episode. Validate it and rerun
quality, direction, command-to-motion, and the same per-sample NPZ trace.
```

Cached-odom validation result:

```text
episode:
  data/raw/b8_reaching_smoke_tuned_v3_cached_odom_check/b8_reaching_smoke_tuned_v3_cached_odom_check_0000.npz

validation:
  PASS
  T: 22
  success: False
  unavailable_fields: ['raw_command']

quality:
  episodes_total: 1
  episodes_below_threshold: 1
  episodes_with_positive_distance_reduction: 0
  initial_distance: 0.12630808035415297 m
  min_distance_overall: 0.08611444139540192 m
  final_distance: 0.14779493259862328 m
  mean_distance_reduction: -0.021486852244470306 m
  max_active_left_joint_delta: 0.06405061370333787 rad

direction:
  episodes_below_threshold: 1
  episodes_with_positive_distance_reduction: 0
  mean_distance_reduction_base: -0.02148685224447025
  mean_action_to_eef_motion_cosine: 0.6683840448271507
  mean_eef_motion_cosine_with_target: 0.5192861743957111
  mean_eef_positive_target_direction_ratio: 0.8095238095238095

command-to-motion:
  episodes_below_threshold: 1
  mean_best_action_to_eef_cosine: 0.7985718493152257
  mean_best_lag_steps: 2.0
  mean_best_realized_gain_along_action: 0.26166311035433365
```

Updated decision:

```text
B8' remains smoke-level progress only.
Cached-odom target updater did not resolve reaching stability.
```

Interpretation:

- The episode crossed threshold once but got worse overall:
  final distance is about `0.148 m`, worse than the initial `0.126 m`.
- Positive distance reduction is no longer present.
- Best command-to-motion coupling is again lagged by about two recorder steps.
- Do not collect repeatability episodes, train, or rollout.

No code change in this round.

Next minimum read-only check:

```text
Run the per-sample trace on the cached-odom episode to inspect below_count,
below_indices, max_target_step, max_target_step_idx, and rebound timing.
```

Cached-odom per-sample trace:

```text
samples: 22
below_count: 1
below_indices: [10]
min_idx: 10
min_distance: 0.08611444139540188
final_distance: 0.14779493259862325
max_target_step: 0.050329083057232285
max_target_step_idx: 11
```

Relevant rows:

```text
idx time      dist      below  target_step_base  eef_step_base
9   37408.648 0.124672  False  0.009712          0.004388
10  37408.958 0.086114  True   0.036269          0.005077
11  37409.288 0.131695  False  0.050329          0.004172
12  37409.616 0.144238  False  0.023333          0.004376
16  37410.936 0.148117  False  0.042151          0.004758
21  37412.536 0.147795  False  0.021348          0.004554
```

Updated decision:

```text
B8' remains smoke-level progress only.
Cached-odom target updater did not materially reduce target_base step spikes.
```

Interpretation:

- The cached-odom episode still has only one below-threshold sample.
- The target_base max-step decreased only slightly from about `0.055 m` to
  about `0.050 m`.
- Final distance got worse compared with the non-cached v3 episode.
- Before making another code change, determine whether the target_base spikes
  are real task geometry or an artifact of recomputing target/eef/base from
  asynchronous recorded fields.

No code change in this round.

Next minimum read-only check:

```text
Compare recomputed base-frame distance with stored relative_target_to_eef norm
from the NPZ episode.
```

## Round 62: B8' First Attempt Blocked By Missing Target And Arm Controller

Date: 2026-05-04

User runtime context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
```

Readiness checks:

```text
/joint_states: present and publishing live samples
/rexrov/pose_gt: present and publishing live odometry
/gazebo/model_states: present and publishing, but only ocean_box and rexrov
/compute_ik: present
/robot_description_semantic: contains arm_l and oberon7_l/end_effector
/controller_manager/list_controllers: only joint_state_controller running
/oberon7/arm_position_l/command: unknown topic
```

The manually started base-relative target helper failed immediately:

```text
B5d base-relative target updater failed:
target model 'cylinder_target' is not available:
GetModelState: model does not exist
```

B8' collection command attempted:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=.../data/raw/b8_reaching_smoke \
  episode_id:=b8_reaching_smoke_0000 \
  rate_hz:=2.0 \
  max_duration_sec:=4.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_action_frame:=base_link \
  target_directed_states:=MOVE_TO_PREGRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=false \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.25
```

Runtime result:

```text
Scripted expert used nominal_target_pose_fallback because cylinder_target was
not observed.
Scripted expert failed: timed out waiting for subscriber on
/oberon7/arm_position_l/command.
Episode recorder failed: timed out waiting for target model 'cylinder_target'.
Validator failed because the episode file did not exist.
```

Decision:

```text
B8' is not resolved. No B8' non-fallback demonstration episode was collected.
```

Interpretation:

- The live state and MoveIt semantic/IK prerequisites are present.
- The target prerequisite is missing in this clean runtime.
- The left-arm controller prerequisite is missing in this clean runtime.
- This is not a failure of learned policy rollout, grasping, or success-rate
  evaluation; none of those were attempted.
- `success=False` is not relevant here because no episode was written.

Code/config fixes applied in the project package only:

- `launch/load_left_controllers.launch`
  - defaults to arm-only controller loading/start;
  - no longer loads or starts `oberon7/hand_position_l` unless
    `load_hand:=true` is explicitly provided.
- `config/data_collection.yaml`
  - adds B8' route metadata defaults:
    `task_type: arm_only_reaching`, `success_metric: reaching_success`,
    `gripper_enabled: false`, `is_grasp_dataset: false`.
- `launch/collect_episode.launch`
  - adds args/recorder params for the same B8' metadata.
- `src/rexrov_single_oberon7_fm_dp/recorder.py`
  - writes the B8' metadata fields into every episode metadata dict.

Static verification after edits:

```text
python3 -m py_compile recorder.py: PASS
collect_episode.launch XML parse: PASS
load_left_controllers.launch XML parse: PASS
data_collection.yaml parse: PASS
```

Next minimum checks for the user:

1. Start only the left-arm controller:

   ```bash
   roslaunch rexrov_single_oberon7_fm_dp load_left_controllers.launch \
     start:=true \
     load_hand:=false
   ```

   This verifies only the left-arm command controller startup. It must not
   start the hand controller.

2. Confirm controller/topic state:

   ```bash
   rosservice call /controller_manager/list_controllers "{}"
   rostopic info /oberon7/arm_position_l/command
   ```

   Expected:

   ```text
   oberon7/arm_position_l: running
   /oberon7/arm_position_l/command: subscriber includes /gazebo
   no hand controller running
   ```

3. Retry a single short B8' smoke with target spawn and the base-relative
   target helper enabled by the collection launch, not as a separate pre-target
   `rosrun`:

   ```bash
   roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
     output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_smoke \
     episode_id:=b8_reaching_smoke_0000 \
     rate_hz:=2.0 \
     max_duration_sec:=3.0 \
     spawn_target:=true \
     require_target:=true \
     enable_base_relative_target:=true \
     allow_nominal_state_fallback:=false \
     execute_arm:=true \
     enable_gripper_command:=false \
     target_directed_reaching:=true \
     target_directed_action_frame:=base_link \
     target_directed_states:=MOVE_TO_PREGRASP,MOVE_TO_GRASP \
     execute_arm_states:=MOVE_TO_PREGRASP \
     execute_arm_once_per_state:=false \
     max_linear_step:=0.005 \
     max_joint_delta:=0.01 \
     command_connection_timeout_sec:=5.0 \
     post_publish_sleep_sec:=0.25 \
     expert_wait_for_target_sec:=10.0 \
     base_relative_target_wait_timeout_sec:=10.0 \
     task_type:=arm_only_reaching \
     success_metric:=reaching_success \
     gripper_enabled:=false \
     is_grasp_dataset:=false
   ```

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- learned-policy rollout or grasp-success claims.

## Round 67: B8' First 5-Episode Smoke Collection Complete

Date: 2026-05-04

User runtime context remained:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
rexrov_single_oberon7_fm_dp load_left_controllers.launch \
  start:=true \
  load_hand:=false
```

Fifth collection command used a unique target model name:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_smoke \
  episode_id:=b8_reaching_smoke_0004 \
  target_model_name:=cylinder_target_b8_0004 \
  rate_hz:=2.0 \
  max_duration_sec:=3.0 \
  spawn_target:=true \
  require_target:=true \
  enable_base_relative_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_action_frame:=base_link \
  target_directed_states:=MOVE_TO_PREGRASP,MOVE_TO_GRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=false \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.25 \
  expert_wait_for_target_sec:=10.0 \
  base_relative_target_wait_timeout_sec:=10.0 \
  task_type:=arm_only_reaching \
  success_metric:=reaching_success \
  gripper_enabled:=false \
  is_grasp_dataset:=false
```

Runtime result:

```text
SpawnModel: Successfully spawned entity
B5d base-relative target initialized:
  model=cylinder_target_b8_0004
Scripted expert running with target source gazebo_model_states;
  execute_arm=True
  gripper_command_enabled=False
  target_directed_reaching=True
Recording episode b8_reaching_smoke_0004: 6 samples at 2.000 Hz
B5 arm command state=MOVE_TO_PREGRASP ...
B5 arm command state=MOVE_TO_PREGRASP ...
B5 arm command state=MOVE_TO_PREGRASP ...
Saved episode:
  data/raw/b8_reaching_smoke/b8_reaching_smoke_0004.npz
```

Validation for episode 0004:

```text
validation: PASS
T: 6
success: False
episode_id: b8_reaching_smoke_0004
unavailable_fields: ['raw_command']
```

Metadata check for episode 0004:

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

field_availability:
  action_ee_delta: true
  eef_pose: true
  raw_command: false
  relative_target_to_eef: true
  target_pose: true
```

Distance and bounded-motion metrics for episode 0004:

```text
initial_distance: 0.13654060230739734
min_distance:     0.1267681665750868
final_distance:   0.1267681665750868
distance_reduction: 0.009772435732310542
min_distance_below_0.10: false

active_left_joint_total_max_abs_delta: 0.00799993301324875
target_motion_norm: 0.24210453393234765
eef_motion_norm: 0.23125036531371668
```

Five-episode summary:

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
min_distance_overall: 0.1188520365091187
mean_initial_distance: 0.13396804089248232
mean_final_distance: 0.1310687641785459
mean_distance_reduction: 0.002899276713936444
max_active_left_joint_delta: 0.00799993301324875
```

Summary artifacts written:

```text
outputs/logs/b8_reaching_smoke/dataset_summary.json
outputs/logs/b8_reaching_smoke/dataset_summary.md
```

Decision:

```text
B8' first 5-episode smoke collection is complete at the data-collection smoke
level.
```

Interpretation:

- The 5 episodes are real non-fallback arm-only reaching/pre-grasp smoke data.
- The recorder captured live odom, live joint states, Gazebo target poses,
  finite `eef_pose`, finite `relative_target_to_eef`, and finite
  `action_ee_delta`.
- The left-arm controller was running and accepted bounded arm commands.
- Gripper was disabled and no hand controller was started.
- No episode crossed the temporary `0.10 m` reaching threshold; this is not a
  reaching success-rate result.
- This is not a learned rollout, not grasping, and not a grasp-success claim.

Next minimum check:

- Stop short collection launch processes/helpers if still running.
- Review the 5-episode B8' smoke metrics and decide whether to:
  - keep this as a smoke dataset only; or
  - tune short reaching behavior before collecting a larger B8' dataset.
- Do not train BC / Diffusion Policy / Flow Matching Policy until explicitly
  moving past this B8' smoke review.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- learned-policy rollout or grasp-success claims.

## Round 68: B8' Reaching Smoke Quality Review

Date: 2026-05-04

Scope:

```text
B8' reaching smoke quality review: only analyze the existing 5-episode
non-fallback reaching dataset; no new data collection, no Gazebo run, no
training, no rollout, no gripper work, and no control-code changes.
```

Reviewed dataset:

```text
data/raw/b8_reaching_smoke/b8_reaching_smoke_0000.npz
data/raw/b8_reaching_smoke/b8_reaching_smoke_0001.npz
data/raw/b8_reaching_smoke/b8_reaching_smoke_0002.npz
data/raw/b8_reaching_smoke/b8_reaching_smoke_0003.npz
data/raw/b8_reaching_smoke/b8_reaching_smoke_0004.npz
```

Analysis utility added:

```text
scripts/analyze_b8_reaching_quality.py
```

This script is offline and read-only with respect to the robot. It reads `.npz`
episodes and writes analysis artifacts only; it imports no ROS modules and does
not publish commands or call Gazebo services.

Quality artifacts:

```text
outputs/logs/b8_reaching_smoke_quality/per_episode_quality.json
outputs/logs/b8_reaching_smoke_quality/per_episode_quality.md
outputs/logs/b8_reaching_smoke_quality/distance_curves.png
outputs/logs/b8_reaching_smoke_quality/action_magnitude_summary.json
outputs/logs/b8_reaching_smoke_quality/joint_motion_summary.json
```

Validator re-check:

```text
validation: PASS for 5/5 episodes
T: 6 for each episode
success: False for each episode
unavailable_fields: ['raw_command']
```

Metadata check:

```text
all_required_metadata_ok: true
allow_nominal_state_fallback: false
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
task_type: arm_only_reaching
success_metric: reaching_success
gripper_enabled: false
is_grasp_dataset: false
```

Distance summary:

```text
episodes_with_positive_distance_reduction: 3/5
episodes_below_0.10: 0/5
min_distance_overall: 0.1188520365091187
mean_initial_distance: 0.13396804089248232
mean_final_distance: 0.1310687641785459
mean_distance_reduction: 0.002899276713936444
```

Per-episode quality labels:

```text
b8_reaching_smoke_0000:
  initial/min/final/reduction: 0.131584 / 0.118852 / 0.136327 / -0.004743
  failure candidates:
    action_too_small, episode_too_short, ik_solution_small_motion,
    threshold_not_reached, target_direction_not_followed,
    pregrasp_offset_not_stable_in_base_frame

b8_reaching_smoke_0001:
  initial/min/final/reduction: 0.141116 / 0.124463 / 0.131371 / 0.009745
  failure candidates:
    episode_too_short, ik_solution_small_motion, threshold_not_reached,
    pregrasp_offset_not_stable_in_base_frame

b8_reaching_smoke_0002:
  initial/min/final/reduction: 0.129065 / 0.125776 / 0.126832 / 0.002233
  failure candidates:
    episode_too_short, ik_solution_small_motion, base_drift_dominates_world_eef,
    threshold_not_reached

b8_reaching_smoke_0003:
  initial/min/final/reduction: 0.131535 / 0.125531 / 0.134046 / -0.002512
  failure candidates:
    action_too_small, episode_too_short, ik_solution_small_motion,
    threshold_not_reached, target_direction_not_followed,
    pregrasp_offset_not_stable_in_base_frame

b8_reaching_smoke_0004:
  initial/min/final/reduction: 0.136541 / 0.126768 / 0.126768 / 0.009772
  failure candidates:
    episode_too_short, ik_solution_small_motion, threshold_not_reached,
    pregrasp_offset_not_stable_in_base_frame
```

Action and joint findings:

```text
action_xyz_norm_mean_all_samples: 0.007494212270760313
action_xyz_norm_max_all_samples: 0.008660254037844387
clip_fraction_xyz_at_0p005:
  0000: 0.667
  0001: 0.833
  0002: 0.778
  0003: 0.444
  0004: 1.000
max_active_left_joint_delta: 0.00799993301324875 rad
all active-left joint motions: bounded and small
```

Target/EEF interpretation:

- `target_state_source` remains `gazebo_model_states`.
- With `enable_base_relative_target:=true`, the target is not world-static in
  these episodes; the helper keeps it near the drifting RexROV/EEF frame.
- World-frame target and EEF motion are much larger than the net reaching
  improvement. Base-frame distance is therefore the relevant short-window
  smoke metric.

Decision:

```text
Current blocker is not the data collection chain; 5/5 non-fallback B8' smoke
episodes were collected and validated.

The active blocker is reaching quality. The scripted expert is too conservative
for useful demonstrations at the current 3 s / 2 Hz / 0.005 m clipped-action
setting.
```

Recommendation:

```text
Choose A: tune the scripted reaching expert before collecting a new 5-episode
smoke set. Do not expand to 20 episodes and do not train BC / DP / FM yet.
```

Candidate next tuning checks:

- increase or adapt `max_linear_step` cautiously above `0.005 m`;
- consider a slightly larger `max_joint_delta` after a bounded smoke check;
- extend short smoke duration or number of approach steps;
- command until distance falls below threshold or a max-step cap, instead of
  only a fixed few steps;
- review base-frame action direction and pregrasp offset stability before
  changing the reaching threshold.

## Round 69: B8' Scripted Reaching Expert Tuned For Next Smoke

Date: 2026-05-04

Scope:

```text
Prepare option A before collecting new data. No Gazebo run, no new episode
collection, no training, no rollout, no gripper command, and no hand controller
startup were performed in this round.
```

Root-cause candidate addressed:

```text
target_directed_action_frame:=base_link generated base-frame reaching deltas,
but the arm EE-delta converter applied xyz deltas directly in the MoveIt
planning frame. This can explain weak or inconsistent reaching direction in the
first B8' smoke dataset.
```

Code/config changes:

```text
src/rexrov_single_oberon7_fm_dp/arm_command_converter.py
  - added action_frame support;
  - rotates base-frame xyz deltas into the planning frame before IK;
  - records clipped xyz in action frame and planning frame in the conversion
    result for log visibility.

src/rexrov_single_oberon7_fm_dp/expert_policy.py
  - reads ~arm_action_frame;
  - passes it to ArmEEDeltaCommandConverter;
  - logs planning_frame/action_frame and both clipped xyz vectors.

src/rexrov_single_oberon7_fm_dp/recorder.py
  - records target_directed_action_frame, arm_action_frame, max_linear_step,
    and max_joint_delta in episode metadata.

launch/collect_episode.launch
  - added arm_action_frame arg and recorder metadata params.

launch/b8_reaching_tuned_episode.launch
  - added a one-episode B8' tuned wrapper around collect_episode.launch.
```

Tuned single-episode wrapper defaults:

```text
output_dir: data/raw/b8_reaching_smoke_tuned_v1
rate_hz: 3.0
max_duration_sec: 3.3
max_linear_step: 0.010
max_joint_delta: 0.015
time_from_start_sec: 1.0
target_directed_action_frame: base_link
arm_action_frame: base_link
execute_arm_states: MOVE_TO_PREGRASP,MOVE_TO_GRASP
execute_arm_once_per_state: false
enable_gripper_command: false
task_type: arm_only_reaching
success_metric: reaching_success
gripper_enabled: false
is_grasp_dataset: false
allow_nominal_state_fallback: false
```

Static verification:

```text
python3 -m py_compile:
  arm_command_converter.py, expert_policy.py, recorder.py: PASS

xmllint --noout:
  collect_episode.launch, b8_reaching_tuned_episode.launch: PASS

roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_episode.launch --ros-args:
  PASS
```

Next minimum runtime command:

```text
Collect exactly one tuned smoke episode first:
  b8_reaching_smoke_tuned_v1_0000

Then validate and inspect distance/joint metrics before collecting 0001-0004.
```

## Round 70: B8' Tuned Episode 0000 Valid But Reaching Quality Still Weak

Date: 2026-05-04

User runtime context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
rexrov_single_oberon7_fm_dp load_left_controllers.launch \
  start:=true \
  load_hand:=false
```

Command run:

```bash
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_episode.launch \
  episode_id:=b8_reaching_smoke_tuned_v1_0000 \
  target_model_name:=cylinder_target_b8_tuned_v1_0000
```

Key launch params:

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

Runtime evidence:

```text
Scripted expert running with target source gazebo_model_states;
  execute_arm=True
  gripper_command_enabled=False
  target_directed_reaching=True

B5 arm command state=MOVE_TO_PREGRASP
  planning_frame=world
  action_frame=base_link
  clipped_xyz_action_frame=[...]
  clipped_xyz_planning_frame=[...]

B5 arm command state=MOVE_TO_GRASP
  planning_frame=world
  action_frame=base_link
  clipped_xyz_action_frame=[...]
  clipped_xyz_planning_frame=[...]

Saved episode:
  data/raw/b8_reaching_smoke_tuned_v1/b8_reaching_smoke_tuned_v1_0000.npz
```

Validation:

```text
validation: PASS
T: 10
success: False
episode_id: b8_reaching_smoke_tuned_v1_0000
unavailable_fields: ['raw_command']
```

Offline metric review:

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

target_base_motion: 0.005055356470380404
eef_base_motion:    0.013228142361489623
```

Decision:

```text
The frame-mismatch blocker is minimal resolved: the log confirms
action_frame=base_link and shows transformed planning-frame deltas.

The data path remains valid: validator PASS, non-fallback state, gripper
disabled.

The reaching-quality blocker is not resolved yet: the episode did not cross
0.10 m and only reduced final distance by about 0.0012 m.
```

Next minimum check:

```text
Continue the tuned-v1 smoke to episodes 0001-0004, then perform a 5-episode
offline quality review. Do not train, do not rollout, and do not expand beyond
this tuned 5-episode smoke until the quality review is complete.
```

## Round 71: B8' Tuned v1 Smoke Complete, Reaching Quality Still Blocked

Date: 2026-05-04

User completed tuned v1 collection:

```text
b8_reaching_smoke_tuned_v1_0000.npz
b8_reaching_smoke_tuned_v1_0001.npz
b8_reaching_smoke_tuned_v1_0002.npz
b8_reaching_smoke_tuned_v1_0003.npz
b8_reaching_smoke_tuned_v1_0004.npz
```

Validation:

```text
5/5 PASS
T: 10
success: False
unavailable_fields: ['raw_command']
```

Metadata:

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
```

Offline quality summary:

```text
episodes_total: 5
all_required_metadata_ok: true
episodes_with_positive_distance_reduction: 3/5
episodes_below_0.10: 0/5
min_distance_overall: 0.12024381987253685
mean_initial_distance: 0.13489757997960966
mean_final_distance: 0.13210586269487332
mean_distance_reduction: 0.002791717284736356
max_active_left_joint_delta: 0.04820419986762747
action_xyz_norm_mean_all_samples: 0.014747916139934376
action_xyz_norm_max_all_samples: 0.017320508075688773
```

Per-episode distance:

```text
0000: 0.127285 / 0.122664 / 0.126087 /  0.001198
0001: 0.140956 / 0.120244 / 0.126678 /  0.014278
0002: 0.128815 / 0.120976 / 0.142158 / -0.013344
0003: 0.152236 / 0.121936 / 0.130982 /  0.021255
0004: 0.125196 / 0.125196 / 0.134625 / -0.009429
```

Decision:

```text
Tuned v1 data-collection smoke is complete and valid.
Frame mismatch is minimal resolved.
Reaching quality remains blocked: no episode crossed 0.10 m and mean
distance reduction is still only about 0.0028 m.
```

Do not train, do not rollout, do not expand to 20 episodes, and do not claim
grasp or reaching success from tuned v1.

## Round 72: B8' Tuned v2 Prepared For One-Episode Check

Date: 2026-05-04

Reason:

```text
Tuned v1 increased action size and fixed action-frame execution but did not
improve reaching enough. A longer arm-only PREGRASP/GRASP sequence is needed,
while still avoiding CLOSE_GRIPPER and LIFT_OR_HOLD.
```

Code/config changes:

```text
src/rexrov_single_oberon7_fm_dp/expert_policy.py
  - added configurable state_sequence;
  - added per-state duration overrides.

src/rexrov_single_oberon7_fm_dp/recorder.py
  - records state_sequence in metadata.

launch/collect_episode.launch
  - exposes state_sequence and MOVE_TO_PREGRASP/MOVE_TO_GRASP duration args.

launch/b8_reaching_tuned_v2_episode.launch
  - added one-episode tuned v2 wrapper.
```

Tuned v2 wrapper:

```text
output_dir: data/raw/b8_reaching_smoke_tuned_v2
state_sequence: MOVE_TO_PREGRASP,MOVE_TO_GRASP
state_duration_move_to_pregrasp: 3.0
state_duration_move_to_grasp: 2.0
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
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v2_episode.launch --ros-args: PASS
```

Next minimum check:

```text
Run only b8_reaching_smoke_tuned_v2_0000 first. Validate and inspect distance
and joint-motion metrics before deciding whether to collect more tuned v2
episodes.
```

## Round 73: B8' Tuned v2 Episode 0000 Valid, Success Semantics Fixed

Date: 2026-05-04

Command run:

```bash
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v2_episode.launch \
  episode_id:=b8_reaching_smoke_tuned_v2_0000 \
  target_model_name:=cylinder_target_b8_tuned_v2_0000
```

Runtime settings:

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

Runtime evidence:

```text
Scripted expert state_sequence=['MOVE_TO_PREGRASP', 'MOVE_TO_GRASP']
B5 arm command ... planning_frame=world action_frame=base_link ...
Saved episode:
  data/raw/b8_reaching_smoke_tuned_v2/b8_reaching_smoke_tuned_v2_0000.npz
```

Validation:

```text
validation: PASS
T: 16
success: False
episode_id: b8_reaching_smoke_tuned_v2_0000
unavailable_fields: ['raw_command']
```

Offline quality metrics:

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
```

Decision:

```text
B8' tuned v2_0000 is valid non-fallback arm-only reaching smoke data.
The state sequence avoided gripper states.
Reaching quality improved but is not resolved: min distance is still above
0.10 m.
```

Semantic issue found:

```text
The runtime finished with success=False reason=gripper_not_closed. This is
historical grasp-success logic and is misleading for B8' because gripper is
disabled and the success metric is reaching_success.
```

Minimal code fix:

```text
src/rexrov_single_oberon7_fm_dp/expert_policy.py
  - reads task_type and success_metric;
  - for arm_only_reaching/pregrasp_positioning or reaching/pregrasp success
    metrics, evaluates distance threshold instead of gripper closure;
  - no control-command behavior changed.

launch/collect_episode.launch
  - passes task_type and success_metric into dp_fm_scripted_expert.
```

Static verification:

```text
python3 -m py_compile expert_policy.py: PASS
xmllint --noout collect_episode.launch b8_reaching_tuned_v2_episode.launch: PASS
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v2_episode.launch --ros-args: PASS
```

Next minimum check:

```text
Run only b8_reaching_smoke_tuned_v2_0001 after this semantic fix. Confirm the
expert finish reason is distance-based, not gripper_not_closed, then validate
and inspect distance/joint metrics before collecting additional v2 episodes.
```

## Round 74: B8' Tuned v2 Episode 0001 Valid, Reaching Quality Still Blocked

Date: 2026-05-04

Command run:

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

Semantic check:

```text
Scripted expert finished:
  success=False
  reason=reaching_success: distance 0.128588 above 0.100000
```

Decision:

```text
The success-semantics fix is confirmed. The expert no longer reports
gripper_not_closed for arm-only reaching.
```

Offline quality summary for tuned v2 episodes 0000-0001:

```text
episodes_total: 2
all_required_metadata_ok: true
episodes_with_positive_distance_reduction: 1/2
episodes_below_0.10: 0/2
min_distance_overall: 0.12082938778758692
mean_initial_distance: 0.1310415302513212
mean_final_distance: 0.12915880820700043
mean_distance_reduction: 0.0018827220443207587
max_active_left_joint_delta: 0.0560245462242559
```

Per-episode distance:

```text
0000: 0.133072 / 0.123457 / 0.125982 /  0.007090
0001: 0.129011 / 0.120829 / 0.132335 / -0.003325
```

Interpretation:

- The tuned v2 data path is valid and non-fallback.
- The state sequence remains arm-only: `MOVE_TO_PREGRASP,MOVE_TO_GRASP`.
- Reaching quality is still blocked: no episode crossed `0.10 m`, and 0001
  moved farther away by the final sample.
- Active-left cumulative motion increased to about `0.056 rad`, while distance
  improvement remains inconsistent.

Decision:

```text
Do not continue tuned v2 collection to 0002-0004 yet.
Do not expand to 20 episodes.
Do not train BC / DP / FM.
```

Next minimum check:

```text
Run an offline direction diagnostic on tuned v2 episodes 0000-0001:
compare actual base-frame EEF displacement against the base-frame
relative_target_to_eef direction, and inspect whether target/pregrasp offset or
IK/joint-limited motion is causing the poor convergence.
```

## Round 75: B8' Tuned v2 Read-Only Offline Direction Diagnostic

Date: 2026-05-04

User ran the read-only quality review:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/analyze_b8_reaching_quality.py \
  --input-dir src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_smoke_tuned_v2 \
  --pattern 'b8_reaching_smoke_tuned_v2_*.npz' \
  --output-dir src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_reaching_smoke_tuned_v2_quality \
  --threshold 0.10
```

Quality summary:

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

Decision:

```text
The reaching-quality blocker is not resolved.
Do not collect tuned v2 0002-0004 yet.
Do not expand collection or train.
```

Added offline-only diagnostic script:

```text
scripts/analyze_b8_reaching_direction.py
```

Purpose:

- read existing `.npz` episodes only;
- compute base-frame target/eef geometry from recorded `base_pose`,
  `target_pose`, and `eef_pose`;
- compare actual next-step `eef_base` displacement against base-frame
  `relative_target_to_eef`;
- compare action direction against actual EEF displacement;
- write JSON/Markdown diagnostics only.

This script does not import ROS, start Gazebo, publish commands, control the
robot, train, or rollout.

Command run:

```bash
python3 src/uvms/rexrov_single_oberon7_fm_dp/scripts/analyze_b8_reaching_direction.py \
  --input-dir src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_smoke_tuned_v2 \
  --pattern 'b8_reaching_smoke_tuned_v2_*.npz' \
  --output-dir src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_reaching_smoke_tuned_v2_direction \
  --threshold 0.10
```

Artifacts:

```text
outputs/logs/b8_reaching_smoke_tuned_v2_direction/direction_diagnostic.json
outputs/logs/b8_reaching_smoke_tuned_v2_direction/direction_diagnostic.md
```

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

Per-episode labels:

```text
0000:
  threshold_not_reached
  distance_not_consistently_decreasing
  action_to_eef_motion_mismatch
  target_moves_in_base_frame
  base_world_drift_present

0001:
  threshold_not_reached
  actual_eef_not_consistently_target_directed
  distance_not_consistently_decreasing
  action_to_eef_motion_mismatch
  target_moves_in_base_frame
  base_world_drift_present
```

Interpretation:

- The tuned v2 episodes remain valid non-fallback arm-only reaching smoke data.
- The blocker is reaching quality, not validator/metadata.
- The action direction is generally aligned with target direction in base frame,
  but actual EEF motion is not reliably target-directed.
- The mean action-to-actual-EEF-motion cosine is only about `0.092`, and the
  mean EEF-motion-to-target cosine is negative.
- Base/world drift and target motion in base frame are present in the recorded
  samples, so additional collection would likely reproduce weak/non-convergent
  demonstrations.

Next minimum check:

```text
Do not collect more yet. Inspect the command-to-motion path around tuned v2:
compare clipped_xyz_planning_frame/action_ee_delta against next-step eef_base
displacement and decide whether the remaining fix is target/base stabilization,
a simpler fixed base-frame pregrasp target, or an IK command-rule adjustment.
```

Still not allowed:

- training;
- rollout;
- gripper/hand-controller work;
- claiming grasp success.

## Round 76: B8' Command-To-Motion Offline Lag Check

Date: 2026-05-04

Added offline-only diagnostic script:

```text
scripts/analyze_b8_command_motion_path.py
```

Purpose:

- read existing tuned v2 `.npz` files only;
- compare recorded `action_ee_delta[t]` against later base-frame EEF
  displacement;
- scan short lags from 0 to 3 sample steps;
- report action-to-EEF cosine, EEF-to-target cosine, realized gain, and
  distance-decreasing ratio.

No ROS, Gazebo, controller command, training, rollout, or gripper action is
performed by this script.

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

Per-episode key result:

```text
0000:
  best lag steps: 0
  best action-to-eef cosine: 0.274922
  best eef-to-target cosine: 0.119690
  best realized gain along action: 0.087396
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
  labels:
    threshold_not_reached
    weak_action_to_motion_coupling
    distance_not_decreasing_under_best_lag
    target_moves_in_base_frame
    base_world_drift_present
```

Interpretation:

- The poor action-to-EEF relationship is not explained by a simple 1-3 sample
  response lag.
- The best lag is 0, but action-to-motion coupling is still weak or negative.
- Base/world drift and target movement in base frame remain strong confounders.
- Reaching-quality blocker remains open.

Decision:

```text
Do not continue tuned v2 collection.
Do not expand collection.
Do not train BC / DP / FM.
Do not rollout.
```

Next minimum check:

```text
Inspect the expert/IK command rule and target geometry before any new
collection. The next useful code-level check is to expose the commanded
planning-frame IK target in the recorded/debug data, then run at most one short
episode to compare commanded IK target, actual EEF motion, and target motion.
```

User reproduced the command-to-motion check:

```text
python3 -m py_compile scripts/analyze_b8_command_motion_path.py: PASS

episodes_total: 2
episodes_below_threshold: 0
mean_best_lag_steps: 0.0
mean_best_action_to_eef_cosine: 0.0921582493936101
mean_best_realized_gain_along_action: 0.02557494803831787
recommendation: do_not_collect_more_until_command_to_motion_path_is_explained
```

Confirmed blocker decision:

```text
Current blocker is not resolved.
The result is not smoke-level reaching resolved.
Missing evidence:
  - at least one tuned v2 episode below the temporary 0.10 m threshold;
  - stable positive action-to-EEF motion coupling;
  - stable positive EEF-to-target motion direction;
  - target/base geometry that does not dominate the short episode.
```

Next minimum read-only check:

```text
Inspect source/config only:
  - expert_policy.py target-directed action generation;
  - arm_command_converter.py base-frame action to planning-frame IK target;
  - b8_reaching_tuned_v2_episode.launch and collect_episode.launch parameter
    pass-through.
```

Do not run collection, rollout, training, or gripper commands for this check.

## Round 77: B8' Tuned v2 Source/Config Read-Only Check

Date: 2026-05-04

User result:

```text
rg command failed because rg is not installed in the container.
```

The same launch parameter check was completed with `grep`.

Launch check result:

```text
b8_reaching_tuned_v2_episode.launch:
  state_sequence=MOVE_TO_PREGRASP,MOVE_TO_GRASP
  target_directed_action_frame=base_link
  arm_action_frame=base_link
  max_linear_step=0.010
  max_joint_delta=0.010

collect_episode.launch:
  passes target_directed_action_frame into dp_fm_scripted_expert and recorder;
  passes arm_action_frame into dp_fm_scripted_expert and recorder;
  passes state_sequence into dp_fm_scripted_expert and recorder;
  passes max_linear_step/max_joint_delta into dp_fm_scripted_expert and recorder.
```

Source snippets inspected by user:

```text
expert_policy.py:
  _target_eef_delta_base_frame:
    target_base = base_from_world * target_world
    delta = target_base - eef_translation

  _target_directed_action:
    if target_directed_action_frame == base_link:
      delta_xyz = _target_eef_delta_base_frame(target_pose)
    action = [delta_xyz, 0, 0, 0, gripper_open_cmd]

arm_command_converter.py:
  _delta_xyz_in_planning_frame:
    if action_frame is base_link and planning_frame is world:
      planning_xyz = _base_delta_in_world(clipped_xyz)

  _base_delta_in_world:
    rotate clipped base-frame action by a fresh /rexrov/pose_gt orientation.
```

Interpretation:

- Tuned v2 static launch/config pass-through is correct.
- The source contains the intended base-frame target-directed action path and
  base-frame to planning-frame conversion.
- This does not resolve the blocker because offline data still shows:
  `episodes_below_threshold=0`, weak action-to-EEF coupling, and strong
  base/target motion confounding.
- The likely remaining issue is runtime state-source consistency, not an
  obvious static launch mismatch:
  - expert action uses target pose + stored base pose + latest TF EEF pose;
  - converter uses MoveGroup/current IK pose + fresh odom orientation;
  - recorder samples base/target/eef independently.

Decision:

```text
Current blocker is not resolved.
No control-code change is justified yet from this static source/config check.
```

Next minimum read-only check:

```text
Inspect live ROS params and frame availability:
  - confirm dp_fm_scripted_expert arm_action_frame and
    target_directed_action_frame are actually base_link at runtime;
  - confirm move_group planning frame and TF connectivity/timing for
    world, rexrov/base_link, and oberon7_l/end_effector.
```

## Round 78: B8' Runtime Params And TF Connectivity Check

Date: 2026-05-04

Runtime parameter check:

```text
/dp_fm_scripted_expert/target_directed_action_frame: base_link
/dp_fm_scripted_expert/arm_action_frame: base_link
/dp_fm_scripted_expert/state_sequence: MOVE_TO_PREGRASP,MOVE_TO_GRASP
/dp_fm_scripted_expert/max_linear_step: 0.01
/dp_fm_scripted_expert/max_joint_delta: 0.01
```

TF check:

```text
timeout 4s rosrun tf tf_echo rexrov/base_link oberon7_l/end_effector

result:
  available and stable
  translation approx [2.075, 0.615, -1.290]
```

TF world/base check:

```text
timeout 4s rosrun tf tf_echo world rexrov/base_link

result:
  failure on every sample:
    Could not find a connection between 'world' and 'rexrov/base_link'
    because they are not part of the same tree.
```

Interpretation:

- The tuned v2 expert runtime parameters are correctly loaded.
- The base-to-left-EEF TF chain is available.
- The world-to-base TF connection required by a `world` planning frame is not
  available.
- This confirms the earlier MoveIt warning:
  `Unable to update multi-DOF joint 'world_to_base'`.
- The command-to-motion blocker is now strongly tied to runtime frame/state
  consistency, not static launch parameter mismatch.

Decision:

```text
Current blocker remains unresolved.
Do not collect more tuned v2 data.
Do not train.
Do not rollout.
Do not touch gripper/hand controller.
```

Next minimum read-only check:

```text
Inspect MoveIt/SRDF virtual-joint configuration and planning frame assumptions.
Confirm whether MoveIt expects a world -> rexrov/base_link transform that is
not being published by the current runtime stack.
```

## Round 79: B8' SRDF Confirms Missing World/Base TF Bridge

Date: 2026-05-04

User checked `/robot_description_semantic`:

```text
<virtual_joint
  name="world_to_base"
  type="floating"
  parent_frame="world"
  child_link="rexrov/base_link" />
```

Interpretation:

- MoveIt expects the virtual joint `world_to_base`.
- Runtime TF previously showed `world` and `rexrov/base_link` are in separate
  trees.
- This explains the repeated MoveIt warning:
  `Unable to update multi-DOF joint 'world_to_base'`.
- It also explains why world/planning-frame IK commands can be inconsistent
  with recorder geometry computed from `/rexrov/pose_gt` and base-link TF.

Decision:

```text
Current blocker remains unresolved.
The next fix must target frame/state consistency.
```

Package-local code update:

```text
Added:
  src/rexrov_single_oberon7_fm_dp/odom_tf_bridge.py
  scripts/odom_tf_bridge.py
  launch/world_base_tf_bridge.launch
```

Bridge behavior:

```text
subscribe: /rexrov/pose_gt
publish TF: world -> rexrov/base_link
repeat_rate_hz: 20.0
```

Safety scope:

- no robot command topics;
- no gripper;
- no hand controller;
- no training;
- no rollout;
- no modifications outside `rexrov_single_oberon7_fm_dp`.

Static checks:

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

Next minimum runtime check:

```text
Run only the TF bridge and verify:
  tf_echo world rexrov/base_link
  tf_echo world oberon7_l/end_effector

Do not collect a new episode until both succeed.
```

## Round 80: B8' TF Bridge Runtime Smoke Passed

Date: 2026-05-04

User ran:

```bash
roslaunch rexrov_single_oberon7_fm_dp world_base_tf_bridge.launch
```

Bridge params:

```text
child_frame: rexrov/base_link
odom_topic: /rexrov/pose_gt
parent_frame: world
repeat_rate_hz: 20.0
```

Bridge log:

```text
Odom TF bridge publishing world -> rexrov/base_link from /rexrov/pose_gt
```

TF result:

```text
timeout 4s rosrun tf tf_echo world rexrov/base_link:
  SUCCESS
  example translation: [141.667, -8.227, -98.464]
```

EEF TF result:

```text
timeout 4s rosrun tf tf_echo world oberon7_l/end_effector:
  first two samples failed while TF tree was updating;
  then SUCCESS with example translation [140.493, -5.907, -99.751].
```

Interpretation:

- The package-local bridge successfully publishes the MoveIt virtual-joint
  transform `world -> rexrov/base_link`.
- The combined `world -> rexrov/base_link -> oberon7_l/end_effector` TF chain
  becomes available after a short startup delay.
- This resolves the frame-connectivity sub-blocker at smoke level.
- It does not resolve reaching-quality or command-to-motion quality by itself.

Decision:

```text
World/base TF bridge smoke: resolved.
B8' reaching-quality blocker: still open.
Do not train.
Do not rollout.
Do not touch gripper.
```

Next minimum check:

```text
With the bridge running, collect exactly one short tuned-v2-style arm-only
frame-fix validation episode, then validate and run offline quality +
command-to-motion diagnostics. Do not collect a 5-episode set yet.
```

## Round 81: B8' TF Bridge Frame-Fix Validation Episode

Date: 2026-05-04

Runtime context:

```text
uvms_control running
b5d_move_group_with_context running
load_left_controllers start:=true load_hand:=false running
world_base_tf_bridge.launch running
```

Command:

```bash
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v2_episode.launch \
  output_dir:=.../data/raw/b8_reaching_smoke_tf_bridge_check \
  episode_id:=b8_reaching_smoke_tf_bridge_check_0000 \
  target_model_name:=cylinder_target_b8_tf_bridge_check_0000
```

Runtime observations:

```text
B5d base-relative target initialized.
MoveIt ready for planning group arm_l.
No world_to_base update warning appeared.
B5 arm command lines used planning_frame=world and action_frame=base_link.
```

Validation:

```text
validation: PASS
T: 16
success: False
episode_id: b8_reaching_smoke_tf_bridge_check_0000
unavailable_fields: ['raw_command']
```

Quality:

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

Detailed quality findings:

```text
clip fraction at max_linear_step: 0.646
action-relative cosine base/world: 0.658332 / 0.322924
target world/base motion: 0.913777 / 0.011852
failure candidates:
  base_drift_dominates_world_eef
  threshold_not_reached
```

Command-to-motion:

```text
episodes_total: 1
episodes_below_threshold: 0
mean_best_lag_steps: 0.0
mean_best_action_to_eef_cosine: 0.38837550274847654
mean_best_realized_gain_along_action: 0.10417398838872995
best distance decreasing ratio: 0.466667
```

Comparison with tuned v2 before bridge:

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
- The missing world/base TF sub-blocker is smoke-level resolved.
- The remaining reaching-quality blocker is not resolved: the episode did not
  cross `0.10 m`, and distance reduction is only about `0.00225 m`.
- The remaining limiting factors appear to be target/base drift and
  conservative/clipped reaching commands.

Decision:

```text
Do not collect a 5-episode set yet.
Do not expand to 20 episodes.
Do not train BC / DP / FM.
Do not rollout.
Do not touch gripper.
```

Next minimum check:

```text
Run read-only direction diagnostics on this single TF-bridge frame-fix episode
to classify the remaining failure before changing expert parameters or
collecting another episode.
```

## Round 82: B8' TF Bridge Direction Diagnostic

Date: 2026-05-04

User ran:

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

Per-episode detail:

```text
b8_reaching_smoke_tf_bridge_check_0000:
  distance initial/min/final/reduction:
    0.128964 / 0.122722 / 0.126713 / 0.002251
  eef base net/mean-step/max-step:
    0.008801 / 0.003905 / 0.006750
  action target/eef-motion cosine:
    0.654347 / 0.388376
  target base net/max-step:
    0.011852 / 0.089075
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

- The TF bridge materially improved command-to-motion coupling.
- The EEF still does not move consistently toward the target:
  `mean_eef_motion_cosine_with_target` is near zero and only 46.7% of steps are
  target-positive.
- The target moves in base frame by up to about `0.089 m` between recorded
  samples, much larger than EEF step motion.
- Remaining blocker is target/base geometry stability and update timing/jitter,
  not the missing world/base TF sub-blocker.

Decision:

```text
B8' reaching-quality blocker remains open.
Do not collect more episodes yet.
Do not train.
Do not rollout.
Do not touch gripper.
```

Next minimum check:

```text
Read-only inspect target updater timing and per-sample target_base/eef_base
geometry. The next bounded change is likely to reduce base-relative target
update lag/jitter before tuning expert step sizes.
```

## Round 66: B8' Episode 0003 Valid Non-Fallback Smoke Collected

Date: 2026-05-04

User runtime context remained:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
rexrov_single_oberon7_fm_dp load_left_controllers.launch \
  start:=true \
  load_hand:=false
```

Collection command used a unique target model name:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_smoke \
  episode_id:=b8_reaching_smoke_0003 \
  target_model_name:=cylinder_target_b8_0003 \
  rate_hz:=2.0 \
  max_duration_sec:=3.0 \
  spawn_target:=true \
  require_target:=true \
  enable_base_relative_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_action_frame:=base_link \
  target_directed_states:=MOVE_TO_PREGRASP,MOVE_TO_GRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=false \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.25 \
  expert_wait_for_target_sec:=10.0 \
  base_relative_target_wait_timeout_sec:=10.0 \
  task_type:=arm_only_reaching \
  success_metric:=reaching_success \
  gripper_enabled:=false \
  is_grasp_dataset:=false
```

Runtime result:

```text
SpawnModel: Successfully spawned entity
B5d base-relative target initialized:
  model=cylinder_target_b8_0003
Scripted expert running with target source gazebo_model_states;
  execute_arm=True
  gripper_command_enabled=False
  target_directed_reaching=True
Recording episode b8_reaching_smoke_0003: 6 samples at 2.000 Hz
B5 arm command state=MOVE_TO_PREGRASP ...
B5 arm command state=MOVE_TO_PREGRASP ...
B5 arm command state=MOVE_TO_PREGRASP ...
Saved episode:
  data/raw/b8_reaching_smoke/b8_reaching_smoke_0003.npz
```

Validation:

```text
validation: PASS
T: 6
success: False
episode_id: b8_reaching_smoke_0003
unavailable_fields: ['raw_command']
```

Metadata check:

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

field_availability:
  action_ee_delta: true
  eef_pose: true
  raw_command: false
  relative_target_to_eef: true
  target_pose: true
```

Distance and bounded-motion metrics:

```text
initial_distance: 0.13153451988022635
min_distance:     0.12553149231421182
final_distance:   0.1340460554870676
distance_reduction: -0.002511535606841253
min_distance_below_0.10: false

active_left_joint_total_max_abs_delta: 0.0075762803935965906
target_motion_norm: 0.488219224441765
eef_motion_norm: 0.4876609306058586
```

Decision:

```text
B8' is partially progressed, not complete: 4/5 requested short non-fallback
arm-only reaching/pre-grasp smoke episodes are collected and validator PASS.
```

Interpretation:

- Episode 0003 is valid B8' smoke data.
- Minimum distance still did not cross the temporary `0.10 m` reaching
  threshold.
- Final distance was slightly larger than initial distance.
- This is not a learned rollout, not grasping, and not a success-rate
  evaluation.

Next minimum check:

- Collect the fifth short episode:
  - `episode_id:=b8_reaching_smoke_0004`;
  - `target_model_name:=cylinder_target_b8_0004`;
  - keep `allow_nominal_state_fallback:=false`;
  - keep `enable_gripper_command:=false`;
  - keep `load_hand:=false`;
  - keep `execute_arm:=true`;
  - keep `target_directed_action_frame:=base_link`.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- learned-policy rollout or grasp-success claims.

## Round 65: B8' Episode 0002 Valid Non-Fallback Smoke Collected

Date: 2026-05-04

User runtime context remained:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
rexrov_single_oberon7_fm_dp load_left_controllers.launch \
  start:=true \
  load_hand:=false
```

Collection command used a unique target model name:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_smoke \
  episode_id:=b8_reaching_smoke_0002 \
  target_model_name:=cylinder_target_b8_0002 \
  rate_hz:=2.0 \
  max_duration_sec:=3.0 \
  spawn_target:=true \
  require_target:=true \
  enable_base_relative_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_action_frame:=base_link \
  target_directed_states:=MOVE_TO_PREGRASP,MOVE_TO_GRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=false \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.25 \
  expert_wait_for_target_sec:=10.0 \
  base_relative_target_wait_timeout_sec:=10.0 \
  task_type:=arm_only_reaching \
  success_metric:=reaching_success \
  gripper_enabled:=false \
  is_grasp_dataset:=false
```

Runtime result:

```text
SpawnModel: Successfully spawned entity
B5d base-relative target initialized:
  model=cylinder_target_b8_0002
Scripted expert running with target source gazebo_model_states;
  execute_arm=True
  gripper_command_enabled=False
  target_directed_reaching=True
Recording episode b8_reaching_smoke_0002: 6 samples at 2.000 Hz
B5 arm command state=MOVE_TO_PREGRASP ...
B5 arm command state=MOVE_TO_PREGRASP ...
Saved episode:
  data/raw/b8_reaching_smoke/b8_reaching_smoke_0002.npz
```

Validation:

```text
validation: PASS
T: 6
success: False
episode_id: b8_reaching_smoke_0002
unavailable_fields: ['raw_command']
```

Metadata check:

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

field_availability:
  action_ee_delta: true
  eef_pose: true
  raw_command: false
  relative_target_to_eef: true
  target_pose: true
```

Distance and bounded-motion metrics:

```text
initial_distance: 0.12906499849282646
min_distance:     0.12577619168420862
final_distance:   0.1268316520246349
distance_reduction: 0.002233346468191566
min_distance_below_0.10: false

active_left_joint_total_max_abs_delta: 0.006852510399685485
target_motion_norm: 0.2815507779598974
eef_motion_norm: 0.2799250204741346
```

Decision:

```text
B8' is partially progressed, not complete: 3/5 requested short non-fallback
arm-only reaching/pre-grasp smoke episodes are collected and validator PASS.
```

Interpretation:

- Episode 0002 is valid B8' smoke data.
- It had a small positive final distance reduction.
- Minimum distance still did not cross the temporary `0.10 m` reaching
  threshold, so this is not a reaching success claim.
- This is not a learned rollout, not grasping, and not a success-rate
  evaluation.

Next minimum check:

- Collect one more short episode:
  - `episode_id:=b8_reaching_smoke_0003`;
  - `target_model_name:=cylinder_target_b8_0003`;
  - keep `allow_nominal_state_fallback:=false`;
  - keep `enable_gripper_command:=false`;
  - keep `load_hand:=false`;
  - keep `execute_arm:=true`;
  - keep `target_directed_action_frame:=base_link`.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- learned-policy rollout or grasp-success claims.

## Round 64: B8' Episode 0001 Valid Non-Fallback Smoke Collected

Date: 2026-05-04

User runtime context remained:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
rexrov_single_oberon7_fm_dp load_left_controllers.launch \
  start:=true \
  load_hand:=false
```

Collection command used a unique target model name:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_smoke \
  episode_id:=b8_reaching_smoke_0001 \
  target_model_name:=cylinder_target_b8_0001 \
  rate_hz:=2.0 \
  max_duration_sec:=3.0 \
  spawn_target:=true \
  require_target:=true \
  enable_base_relative_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_action_frame:=base_link \
  target_directed_states:=MOVE_TO_PREGRASP,MOVE_TO_GRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=false \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.25 \
  expert_wait_for_target_sec:=10.0 \
  base_relative_target_wait_timeout_sec:=10.0 \
  task_type:=arm_only_reaching \
  success_metric:=reaching_success \
  gripper_enabled:=false \
  is_grasp_dataset:=false
```

Runtime result:

```text
SpawnModel: Successfully spawned entity
B5d base-relative target initialized:
  model=cylinder_target_b8_0001
Scripted expert running with target source gazebo_model_states;
  execute_arm=True
  gripper_command_enabled=False
  target_directed_reaching=True
Recording episode b8_reaching_smoke_0001: 6 samples at 2.000 Hz
B5 arm command state=MOVE_TO_PREGRASP ...
B5 arm command state=MOVE_TO_PREGRASP ...
Saved episode:
  data/raw/b8_reaching_smoke/b8_reaching_smoke_0001.npz
```

Validation:

```text
validation: PASS
T: 6
success: False
episode_id: b8_reaching_smoke_0001
unavailable_fields: ['raw_command']
```

Metadata check:

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

field_availability:
  action_ee_delta: true
  eef_pose: true
  raw_command: false
  relative_target_to_eef: true
  target_pose: true
```

Distance and bounded-motion metrics:

```text
initial_distance: 0.14111589664042035
min_distance:     0.12446322761096357
final_distance:   0.1313705762718126
distance_reduction: 0.009745320368607757
min_distance_below_0.10: false

active_left_joint_total_max_abs_delta: 0.005944080347275005
target_motion_norm: 0.42643927771340934
eef_motion_norm: 0.4340629871127455
```

Decision:

```text
B8' is partially progressed, not complete: 2/5 requested short non-fallback
arm-only reaching/pre-grasp smoke episodes are collected and validator PASS.
```

Interpretation:

- Episode 0001 is valid B8' smoke data.
- The final distance improved relative to the initial distance by about
  `0.0097 m`.
- Minimum distance still did not cross the temporary `0.10 m` reaching
  threshold, so this is not a reaching success claim.
- This is not a learned rollout, not grasping, and not a success-rate
  evaluation.

Next minimum check:

- Collect one more short episode:
  - `episode_id:=b8_reaching_smoke_0002`;
  - `target_model_name:=cylinder_target_b8_0002`;
  - keep `allow_nominal_state_fallback:=false`;
  - keep `enable_gripper_command:=false`;
  - keep `load_hand:=false`;
  - keep `execute_arm:=true`;
  - keep `target_directed_action_frame:=base_link`.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- learned-policy rollout or grasp-success claims.

## Round 63: B8' Episode 0000 Valid Non-Fallback Smoke Collected

Date: 2026-05-04

User runtime context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
rexrov_single_oberon7_fm_dp load_left_controllers.launch \
  start:=true \
  load_hand:=false
```

Controller readiness check:

```text
/controller_manager/list_controllers:
  joint_state_controller: running
  oberon7/arm_position_l: running
    type: position_controllers/JointTrajectoryController
    claimed resources:
      oberon7_l/azimuth
      oberon7_l/elbow
      oberon7_l/pitch
      oberon7_l/roll
      oberon7_l/shoulder
      oberon7_l/wrist

/oberon7/arm_position_l/command:
  type: trajectory_msgs/JointTrajectory
  subscribers:
    /gazebo
```

No hand controller was reported running.

Collection command:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_smoke \
  episode_id:=b8_reaching_smoke_0000 \
  rate_hz:=2.0 \
  max_duration_sec:=3.0 \
  spawn_target:=true \
  require_target:=true \
  enable_base_relative_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_action_frame:=base_link \
  target_directed_states:=MOVE_TO_PREGRASP,MOVE_TO_GRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=false \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.25 \
  expert_wait_for_target_sec:=10.0 \
  base_relative_target_wait_timeout_sec:=10.0 \
  task_type:=arm_only_reaching \
  success_metric:=reaching_success \
  gripper_enabled:=false \
  is_grasp_dataset:=false
```

Runtime result:

```text
SpawnModel: Successfully spawned entity
B5d base-relative target initialized
Scripted expert running with target source gazebo_model_states;
  execute_arm=True
  gripper_command_enabled=False
  target_directed_reaching=True
Recording episode b8_reaching_smoke_0000: 6 samples at 2.000 Hz
B5 arm command state=MOVE_TO_PREGRASP ...
B5 arm command state=MOVE_TO_PREGRASP ...
B5 arm command state=MOVE_TO_PREGRASP ...
Saved episode:
  data/raw/b8_reaching_smoke/b8_reaching_smoke_0000.npz
```

Validation:

```text
validation: PASS
T: 6
success: False
episode_id: b8_reaching_smoke_0000
unavailable_fields: ['raw_command']
```

Metadata check:

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

field_availability:
  action_ee_delta: true
  eef_pose: true
  raw_command: false
  relative_target_to_eef: true
  target_pose: true
```

Distance and bounded-motion metrics:

```text
initial_distance: 0.1315841871415412
min_distance:     0.1188520365091187
final_distance:   0.13632737053412758
distance_reduction: -0.004743183392586392
min_distance_below_0.10: false

active_left_joint_delta_first_to_last:
  [0.0006589049180805162, 0.00511155935974017,
   0.002621044676268447, 0.0021072663169157124,
   -0.007721456966788942, -0.0014826844879474166]

active_left_joint_total_max_abs_delta: 0.007721456966788942
target_motion_norm: 0.595817774371313
eef_motion_norm: 0.590899902474541
```

Decision:

```text
B8' is partially progressed, not complete.
```

Resolved by this check:

- Clean-runtime left arm controller startup works with the arm-only helper and
  `load_hand:=false`.
- Target spawn works when `spawn_target:=true`.
- Base-relative target helper starts successfully when launched after target
  spawn inside `collect_episode.launch`.
- A real non-fallback arm-only reaching/pre-grasp smoke episode was written.
- Validator passes and required live-state/eef/action fields are available.
- B8' metadata now correctly marks the episode as arm-only and non-grasp.

Still open:

- B8' requested 5 short smoke episodes; only 1/5 has been collected.
- Reaching quality is not yet strong: min distance did not cross the temporary
  `0.10 m` threshold, and final distance was slightly larger than initial.
- This is not a learned rollout, not grasping, and not a success-rate
  evaluation.

Next minimum check:

- Stop the completed `collect_episode.launch` if its `b5d_base_relative_target`
  node is still running.
- Collect one more short episode before trying a larger run.
- Use a unique target model name, for example
  `target_model_name:=cylinder_target_b8_0001`, or delete the previous
  `cylinder_target` before reusing that name.
- Keep:
  - `allow_nominal_state_fallback:=false`;
  - `enable_gripper_command:=false`;
  - `load_hand:=false`;
  - `execute_arm:=true`;
  - `target_directed_action_frame:=base_link`.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- learned-policy rollout or grasp-success claims.

## Round 62: Route Documentation Alignment - Arm-Only Reaching / Pre-Grasp

Date: 2026-05-04.

User request:

- Continue debug/documentation alignment mode.
- Update docs only under
  `src/uvms/rexrov_single_oberon7_fm_dp/docs`.
- Do not modify README, code, launch, config, scripts, learning files, or
  official packages.
- Do not run Gazebo, training, or rollout.

Decision:

```text
Current first-version real closed-loop demo route is arm-only reaching /
pre-grasp positioning, not grasping.
```

Recorded status:

- B5d' is debug-smoke minimal resolved.
- The scripted expert can drive the left arm with small bounded commands while
  gripper command is disabled.
- Current execution route is:

  ```text
  EE-delta -> IK/joint target -> /oberon7/arm_position_l/command
  ```

- MoveIt trajectory execution is still not considered fully solved.
- `success=False` remains normal for current smoke data and is not a B5d'
  failure.
- Success metrics for the current route are `reaching_success` or
  `pregrasp_success`, not `grasp_success`.
- Stage 6 fallback data remains historical pipeline-smoke data only.

B8' next:

- collect 5 short real non-fallback arm-only reaching/pre-grasp episodes;
- require `allow_nominal_state_fallback=false`;
- require live odom, `/joint_states`, Gazebo target state, finite `eef_pose`,
  finite `relative_target_to_eef`, and finite `action_ee_delta`;
- record `gripper_enabled=false`, `task_type`, `success_metric`, and
  `is_grasp_dataset=false`;
- record initial/min/final distance, distance reduction, active-left joint
  motion magnitude, validator result, and failure reason.

Still not allowed:

- gripper commands;
- hand controller startup as a workaround;
- training;
- rollout;
- grasp-success or object-grasped/lifted/held claims.

## Round 53: B5d' Base-Relative No-Arm Recorder Smoke

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
oberon7/arm_position_l running
static cylinder_target present
source devel/setup.bash already executed
```

Runtime:

- `base_relative_target.py` was running separately.
- It initialized with:

  ```text
  target_base_xyz:
    [2.170883638549231, 0.49849393817160165, -1.2700366174217264]
  ```

- `collect_episode.launch` ran with:

  ```text
  episode_id: b5d_base_relative_target_no_arm
  rate_hz: 2.0
  max_duration_sec: 3.0
  spawn_target: false
  require_target: true
  allow_nominal_state_fallback: false
  execute_arm: false
  enable_gripper_command: false
  ```

Validation:

```text
validation: PASS
T: 6
success: False
unavailable_fields: ['raw_command']
```

Metadata and distance check:

```text
field_availability:
  action_ee_delta: True
  eef_pose: True
  raw_command: False
  relative_target_to_eef: True
  target_pose: True

allow_nominal_state_fallback:
  False

base_state_source:
  odom

joint_state_source:
  joint_states

target_state_source:
  gazebo_model_states

eef_pose_source:
  odom+tf:rexrov/base_link->oberon7_l/end_effector

distances:
  [0.15567486673041456,
   0.12589378961612116,
   0.1637074291633053,
   0.1242521882294868,
   0.18226778797458662,
   0.10634645938592203]

initial_distance:
  0.15567486673041456 m

final_distance:
  0.10634645938592203 m

min_distance:
  0.10634645938592203 m

max_distance:
  0.18226778797458662 m
```

World-frame motion:

```text
target_motion:
  0.9986519715789479 m

eef_motion:
  0.9479762276473431 m
```

Decision:

```text
B5d' base-relative recorder task setup is resolved enough for first tiny arm-only reaching smoke.
B5d' full arm-only reaching smoke is still not complete.
```

Interpretation:

- The base-relative helper kept target and EEF in the same local neighborhood
  while both moved about 1 m in world coordinates.
- The no-arm recorder path remains non-fallback and validator-clean.
- `success=False` remains expected and is not a failure because this is not a
  grasp task and no arm command was sent.
- `raw_command` remains unavailable because recorder does not yet log the raw
  arm `JointTrajectory`; this is not blocking B5d' smoke.

Code changes made for next step:

- Added default-off target-directed reaching support to the scripted expert:
  - `target_directed_reaching`
  - `target_directed_states`
- When enabled, the expert computes clipped EE delta from live
  `target_pose - eef_pose`.
- The previous fixed scripted deltas remain the default behavior.
- `collect_episode.launch` now exposes the target-directed args.

Verification:

```text
python3 -m py_compile:
  expert_policy.py: PASS
  scripted_expert.py: PASS
  base_relative_target.py module: PASS
  base_relative_target.py script wrapper: PASS
```

Next minimum check:

- Run the first tiny B5d' arm-only smoke:
  - base-relative target helper active;
  - `target_directed_reaching:=true`;
  - `execute_arm:=true`;
  - `enable_gripper_command:=false`;
  - `execute_arm_states:=MOVE_TO_PREGRASP`;
  - `execute_arm_once_per_state:=true`;
  - `max_linear_step:=0.005`;
  - `max_joint_delta:=0.01`;
  - fallback disabled.

Expected success signal:

- one small arm-only command is published;
- `/oberon7/arm_position_l/state` desired matches the command;
- active-left joints move by bounded small deltas;
- recorder validates PASS;
- final distance is less than initial distance or at least shows a controlled
  local reaching response.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- rollout or grasp-success claims.

## Round 54: B5d' Tiny Arm Smoke Blocked By Missing MoveIt Semantic Params

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
base_relative_target.py still running
source devel/setup.bash already executed
```

Command attempted:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=.../data/raw/b5d_reaching_smoke \
  episode_id:=b5d_target_directed_arm_once \
  rate_hz:=2.0 \
  max_duration_sec:=3.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_states:=MOVE_TO_PREGRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=true \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.5
```

Failure:

```text
Robot semantic description not found. Did you forget to define or remap '/robot_description_semantic'?
Group 'arm_l' was not found.
Scripted expert failed: Group 'arm_l' was not found.
Episode recording failed: timed out waiting for expert action on
/rexrov_single_oberon7_fm_dp/expert/action_ee_delta
validation: FAIL
file does not exist: .../b5d_target_directed_arm_once.npz
```

Decision:

```text
B5d' remains unresolved. The arm smoke did not reach the command-execution step.
```

Interpretation:

- The failure occurred while constructing the MoveIt arm group inside the B5a
  converter.
- `/robot_description_semantic` was not available in the active ROS master, so
  MoveIt could not expose group `arm_l`.
- This is a runtime MoveIt prerequisite issue.
- It does not invalidate:
  - B5a converter behavior when MoveIt semantic state is available;
  - the base-relative target helper;
  - the non-fallback recorder path.

Does this require code changes now?

```text
No.
```

Reason:

- The current error is missing runtime MoveIt semantic configuration, not a
  package code defect.
- The same converter previously worked when `/robot_description_semantic`,
  `/move_group`, and `/compute_ik` were present.

Next minimum check:

- Before rerunning any arm-command smoke, run read-only MoveIt readiness checks:
  - `/move_group` node exists;
  - `/compute_ik` service exists and is owned by `/move_group`;
  - `/robot_description_semantic` exists and contains group `arm_l`;
  - `/oberon7/arm_position_l` remains running;
  - `/oberon7/arm_position_l/command` has `/gazebo` subscriber.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- rollout or grasp-success claims.

## Round 55: B5d' MoveIt Readiness Shows Client Semantic Gap

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
base_relative_target.py still running
source devel/setup.bash already executed
```

Read-only checks:

```text
rosnode list:
  /move_group

rosservice list:
  /compute_ik

rosservice info /compute_ik:
  Node: /move_group
  Type: moveit_msgs/GetPositionIK

rosparam get /robot_description_semantic:
  ERROR: Parameter [/robot_description_semantic] is not set

controller_manager/list_controllers:
  joint_state_controller: running
  oberon7/arm_position_l: running

/oberon7/arm_position_l/command:
  type: trajectory_msgs/JointTrajectory
  subscriber: /gazebo
```

Decision:

```text
B5d' remains unresolved, but the failure is narrowed to client-side MoveGroupCommander semantic dependency.
```

Interpretation:

- MoveIt IK service exists and is owned by `/move_group`.
- The left-arm trajectory controller remains available.
- The missing global `/robot_description_semantic` prevents client-side
  `MoveGroupCommander("arm_l")` construction, even though `/compute_ik` exists.
- This is exactly why Round 54 failed before publishing any arm command.

Code change:

- Updated `arm_command_converter.py` with a direct `/compute_ik` fallback:
  - if `/robot_description_semantic` is unavailable, do not construct
    `MoveGroupCommander`;
  - compute current EEF pose from direct TF or odom+TF;
  - seed IK with current active-left joint positions from `/joint_states`;
  - call `/compute_ik` with group `arm_l` and link `oberon7_l/end_effector`;
  - keep the same per-step linear and joint clipping.
- Updated `expert_policy.py` to pass planning frame, base odom topic, and base
  link frame to the converter.

Verification:

```text
python3 -m py_compile:
  arm_command_converter.py: PASS
  expert_policy.py: PASS
  scripted_expert.py: PASS
```

Next minimum check:

- Rerun the same tiny B5d' arm-only smoke:
  - base-relative target helper active;
  - `target_directed_reaching:=true`;
  - `execute_arm:=true`;
  - `enable_gripper_command:=false`;
  - `execute_arm_states:=MOVE_TO_PREGRASP`;
  - `execute_arm_once_per_state:=true`;
  - `max_linear_step:=0.005`;
  - `max_joint_delta:=0.01`;
  - fallback disabled.

Expected result:

- The expert should no longer fail at `Group 'arm_l' was not found`.
- Either direct `/compute_ik` succeeds and publishes one bounded arm command, or
  a later, more specific IK error is exposed.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- rollout or grasp-success claims.

## Round 56: B5d' Readiness Reconfirmed After Direct IK Fallback Patch

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
source devel/setup.bash already executed
```

Read-only checks:

```text
rosnode list:
  /move_group

rosservice list:
  /compute_ik

rosservice info /compute_ik:
  Node: /move_group
  Type: moveit_msgs/GetPositionIK

rosparam get /robot_description_semantic:
  ERROR: Parameter [/robot_description_semantic] is not set

controller_manager/list_controllers:
  joint_state_controller: running
  oberon7/arm_position_l: running

/oberon7/arm_position_l/command:
  type: trajectory_msgs/JointTrajectory
  subscriber: /gazebo
```

Decision:

```text
B5d' is not solved yet. The next check must verify the new direct /compute_ik fallback in an actual tiny arm-only smoke.
```

Interpretation:

- This repeats and confirms the Round 55 runtime condition.
- The runtime has enough pieces for a direct IK service call:
  - `/compute_ik` exists and is owned by `/move_group`;
  - the left-arm trajectory controller is running;
  - `/oberon7/arm_position_l/command` has a Gazebo subscriber.
- The missing global `/robot_description_semantic` still explains why
  client-side `MoveGroupCommander("arm_l")` failed in Round 54.
- The package-local converter patch is still the correct minimum fix path:
  use `/compute_ik` directly instead of requiring client-side semantic params.

Code/doc status:

- No additional code change was needed for this repeated readiness output.
- `arm_command_converter.py` already contains the direct `/compute_ik`
  fallback.
- `CURRENT_STATUS.md` was updated to note that this readiness state was
  reconfirmed.

Next minimum check:

- With the base-relative target helper active, rerun the tiny B5d' arm-only
  smoke:
  - `target_directed_reaching:=true`;
  - `execute_arm:=true`;
  - `enable_gripper_command:=false`;
  - `execute_arm_states:=MOVE_TO_PREGRASP`;
  - `execute_arm_once_per_state:=true`;
  - `max_linear_step:=0.005`;
  - `max_joint_delta:=0.01`;
  - `allow_nominal_state_fallback:=false`.

Expected result:

- The expert should not fail with `Group 'arm_l' was not found`.
- Either direct `/compute_ik` succeeds and publishes one bounded arm command, or
  a later, more specific IK/service/controller error is exposed.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- rollout or grasp-success claims.

## Round 57: B5d' Direct IK Reaches Service But MoveIt Has No Semantic Groups

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
base_relative_target.py running
source devel/setup.bash already executed
```

Command attempted:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=.../data/raw/b5d_reaching_smoke \
  episode_id:=b5d_target_directed_arm_once_direct_ik \
  rate_hz:=2.0 \
  max_duration_sec:=3.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_states:=MOVE_TO_PREGRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=true \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.5
```

Observed output:

```text
MoveIt semantic param /robot_description_semantic is unavailable;
B5 arm converter will use direct /compute_ik service mode

Scripted expert running ... execute_arm=True gripper_command_enabled=False
target_directed_reaching=True

Scripted expert failed: IK failed with MoveIt error code -15

recorder wrote:
  data/raw/b5d_reaching_smoke/b5d_target_directed_arm_once_direct_ik.npz

validator:
  PASS
  T=6
  success=False
  unavailable_fields=['raw_command']
```

Decision:

```text
B5d' is not solved yet, but the blocker moved forward: the direct /compute_ik fallback is now active and the next failure is MoveIt semantic group availability.
```

Interpretation:

- The previous `MoveGroupCommander("arm_l")` crash is bypassed.
- `/compute_ik` was called, but MoveIt returned error `-15`.
- In MoveIt this is consistent with an invalid group name.
- The revised SRDF file contains `arm_l`:

```text
src/uvms/rexrov_moveit_revised/config/rexrov_dual_oberon7.srdf
  <group name="arm_l">
    <chain base_link="oberon7_l/base" tip_link="oberon7_l/end_effector"/>
```

- However, `src/uvms/rexrov_moveit_revised/launch/move_group_revised.launch`
  has its `planning_context_revised.launch` include commented out, so the
  active `/move_group` can expose `/compute_ik` without knowing `arm_l`.

Code/config change:

- Added a package-local wrapper:

```text
launch/b5d_move_group_with_context.launch
```

- The wrapper:
  - first includes
    `rexrov_moveit_revised/launch/planning_context_revised.launch`;
  - keeps `load_robot_description:=false` by default so it does not overwrite
    the UVMS Gazebo robot description;
  - then includes the original
    `rexrov_moveit_revised/launch/move_group_revised.launch`;
  - does not modify `src/dave`, `src/uuv_simulator`, `src/uuv_manipulators`,
    `src/rexrov2`, or `src/uvms/rexrov_moveit_revised`.

Next minimum check:

- Stop only the current `move_group_revised.launch` terminal.
- Relaunch MoveIt through the package-local wrapper:

```bash
roslaunch rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
```

- Then run read-only checks:

```bash
rosnode list | grep -E "^/move_group$"
rosservice list | grep -E "^/compute_ik$"
rosparam get /robot_description_semantic | grep -E "group name=\"arm_l\"|oberon7_l/end_effector" | head -20
timeout 5s rosservice call /controller_manager/list_controllers "{}"
rostopic info /oberon7/arm_position_l/command
```

Expected result:

- `/move_group` exists.
- `/compute_ik` exists.
- `/robot_description_semantic` contains `group name="arm_l"` and
  `oberon7_l/end_effector`.
- `oberon7/arm_position_l` remains running.
- `/oberon7/arm_position_l/command` still has the `/gazebo` subscriber.

If the read-only checks pass:

- Rerun the same tiny direct-IK arm-only smoke with:
  - base-relative target helper active;
  - `target_directed_reaching:=true`;
  - `execute_arm:=true`;
  - `enable_gripper_command:=false`;
  - `max_linear_step:=0.005`;
  - `max_joint_delta:=0.01`;
  - `allow_nominal_state_fallback:=false`.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- rollout or grasp-success claims.

## Round 58: B5d' MoveIt Wrapper Readiness Passes

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
roslaunch rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
source devel/setup.bash already executed
```

Read-only checks:

```text
rosnode list:
  /move_group

rosservice list:
  /compute_ik

rosparam get /robot_description_semantic | grep ...
  returned revised SRDF content containing oberon7_l/end_effector

controller_manager/list_controllers:
  joint_state_controller: running
  oberon7/arm_position_l: running

/oberon7/arm_position_l/command:
  type: trajectory_msgs/JointTrajectory
  subscriber: /gazebo
```

Decision:

```text
B5d' is not solved yet, but the MoveIt semantic-group blocker is minimally resolved for the next smoke test.
```

Interpretation:

- The package-local wrapper successfully starts `/move_group` with semantic
  context loaded.
- `/compute_ik` remains available.
- The left-arm controller and command subscriber remain available.
- The next blocker check should be actual direct-IK arm-only command execution,
  not more MoveIt launch inspection.

Code/config status:

- No additional code change was needed.
- Keep using `launch/b5d_move_group_with_context.launch` for B5d' tests instead
  of directly launching `rexrov_moveit_revised/move_group_revised.launch`.

Next minimum check:

- Keep exactly one `base_relative_target.py` instance running.
- Rerun the tiny direct-IK arm-only smoke:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b5d_reaching_smoke \
  episode_id:=b5d_target_directed_arm_once_with_context \
  rate_hz:=2.0 \
  max_duration_sec:=3.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_states:=MOVE_TO_PREGRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=true \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.5
```

Expected result:

- The expert should not fail with `Group 'arm_l' was not found`.
- The expert should not fail with IK error `-15`.
- Either one bounded arm command is published, or a later more specific IK,
  TF, or controller error is exposed.
- Recorder should write an `.npz`; validator should PASS if required fields are
  present.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- rollout or grasp-success claims.

## Round 59: B5d' Tiny Direct-IK Arm-Only Smoke Passes

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
roslaunch rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
base_relative_target.py running
source devel/setup.bash already executed
```

Command:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=.../data/raw/b5d_reaching_smoke \
  episode_id:=b5d_target_directed_arm_once_with_context \
  rate_hz:=2.0 \
  max_duration_sec:=3.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_states:=MOVE_TO_PREGRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=true \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.5
```

Runtime result:

```text
Loading robot model 'rexrov'...
Ready to take commands for planning group arm_l.
Scripted expert running ... execute_arm=True gripper_command_enabled=False target_directed_reaching=True
B5 arm command state=MOVE_TO_PREGRASP frame=world
  current_eef_xyz=[2.0708874117128375, 0.49849446361067595, -1.310027833719664]
  target_eef_xyz=[2.0658874117128376, 0.49349446361067595, -1.3050278337196641]
  command_positions=[-0.00872978595214149, 0.015341291156129025,
                     -0.004505414759411899, -0.006802623366670097,
                     0.02343441993722802, -0.00034170589556076474]
Saved episode:
  data/raw/b5d_reaching_smoke/b5d_target_directed_arm_once_with_context.npz
```

Validation:

```text
validation: PASS
T: 6
success: False
episode_id: b5d_target_directed_arm_once_with_context
unavailable_fields: ['raw_command']
```

Metadata:

```text
allow_nominal_state_fallback: False
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
field_availability:
  action_ee_delta: True
  eef_pose: True
  raw_command: False
  relative_target_to_eef: True
  target_pose: True
```

Distance and bounded-motion check:

```text
distances:
  [0.1788248795800101, 0.15094216251956288,
   0.2019240911612161, 0.13331866502087025,
   0.16604065914296204, 0.1364991914775168]

initial_distance: 0.1788248795800101
final_distance:   0.1364991914775168
min_distance:     0.13331866502087025
distance_reduction: 0.04232568810249329

active_joint_delta_first_to_last:
  [-0.005845746760841486, 0.008859318743169808,
   -0.00887410261843069, -0.006141069955479139,
   0.008787710103255186, 0.0002996564801662771]

active_joint_max_abs_delta_from_first:
  [0.005845746760841486, 0.008859318743169808,
   0.00887410261843069, 0.006141069955479139,
   0.008787710103255186, 0.0002996564801662771]
```

Decision:

```text
B5d' one-command direct-IK arm-only reaching smoke is minimally resolved.
B5d' multi-step reaching behavior is not yet resolved.
```

Interpretation:

- The package-local MoveIt wrapper fixed the semantic group issue for this
  runtime.
- The expert reached `arm_l`, generated a target-directed clipped action, and
  published one bounded left-arm command through the B5a converter.
- The recorder wrote a non-fallback episode and validator passed.
- EEF-target distance decreased by about `0.042 m`, while active-left joint
  movement stayed below `0.009 rad` from the first sample.
- `success=False` is expected and is not a B5d' failure, because this route is
  arm-only reaching and gripper remains disabled/blocked.
- `raw_command` is still unavailable and remains a known schema/recorder
  limitation, not a failure of this one-command smoke.

Next minimum check:

- Run one short multi-step B5d' smoke by keeping the same safety limits but
  allowing arm execution on repeated `MOVE_TO_PREGRASP` loop iterations:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b5d_reaching_smoke \
  episode_id:=b5d_target_directed_arm_multistep_with_context \
  rate_hz:=2.0 \
  max_duration_sec:=4.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_states:=MOVE_TO_PREGRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=false \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.25
```

Expected result:

- Multiple bounded `B5 arm command` log lines, all in `MOVE_TO_PREGRASP`.
- Validator PASS.
- Active-left joint changes remain bounded.
- Final distance should be lower than initial distance or at least show stable,
  controlled local reaching behavior.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- rollout or grasp-success claims.

## Round 60: B5d' Multi-Step Smoke Runs But Frame Mismatch Blocks Convergence

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
roslaunch rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
base_relative_target.py running
source devel/setup.bash already executed
```

Command:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=.../data/raw/b5d_reaching_smoke \
  episode_id:=b5d_target_directed_arm_multistep_with_context \
  rate_hz:=2.0 \
  max_duration_sec:=4.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_states:=MOVE_TO_PREGRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=false \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.25
```

Runtime result:

```text
Ready to take commands for planning group arm_l.
Scripted expert running ... execute_arm=True gripper_command_enabled=False target_directed_reaching=True
B5 arm command state=MOVE_TO_PREGRASP ... command_positions=[-0.002185..., 0.021803..., ...]
B5 arm command state=MOVE_TO_PREGRASP ... command_positions=[-0.001121..., 0.022849..., ...]
B5 arm command state=MOVE_TO_PREGRASP ... command_positions=[0.001079..., 0.025010..., ...]
Saved episode:
  data/raw/b5d_reaching_smoke/b5d_target_directed_arm_multistep_with_context.npz
```

Validation:

```text
validation: PASS
T: 8
success: False
episode_id: b5d_target_directed_arm_multistep_with_context
unavailable_fields: ['raw_command']
```

Metadata:

```text
allow_nominal_state_fallback: False
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
field_availability:
  action_ee_delta: True
  eef_pose: True
  raw_command: False
  relative_target_to_eef: True
  target_pose: True
```

Distance and bounded-motion check:

```text
distances:
  [0.11676057170211303, 0.12691824122338707,
   0.11749238132282656, 0.1603248303311277,
   0.11471695057400262, 0.12193476704870661,
   0.11587600932885406, 0.1693073637034611]

initial_distance: 0.11676057170211303
final_distance:   0.1693073637034611
min_distance:     0.11471695057400262
distance_reduction: -0.05254679200134808

target_motion: 1.00507005876165
eef_motion:    1.0544313811960602

active_joint_delta_first_to_last:
  [0.008093050867595153, 0.007344060912485517,
   0.009968943570005884, 0.012204180905835749,
   -0.010044932674059481, -0.018327077870040398]

active_joint_total_max_abs: 0.018327077870040398
```

Decision:

```text
B5d' multi-step command execution is working, but B5d' reaching convergence is not resolved yet.
```

Interpretation:

- The multi-step execution path is alive: the expert issued three bounded arm
  commands, the recorder wrote a non-fallback episode, and the validator passed.
- The final EEF-target distance increased from about `0.117 m` to about
  `0.169 m`; the best sample was only about `0.115 m`.
- This is not a gripper issue and not a validator issue.
- The likely cause is a frame mismatch: target-directed action labels were
  computed from Gazebo world-frame `target_pose - eef_pose`, while the arm
  converter applies the EE delta inside MoveIt's local arm/planning frame.
- With the base-relative target helper active, the target is stable relative to
  `rexrov/base_link`, so the reaching delta should be computed in the base
  frame before sending it to the converter.

Code change:

- Updated `expert_policy.py`:
  - added `target_directed_action_frame`, default `base_link`;
  - added base-frame target conversion using `/rexrov/pose_gt` and
    `rexrov/base_link -> oberon7_l/end_effector` TF;
  - `target_directed_reaching` now computes `target_base - eef_base` by
    default.
- Updated `collect_episode.launch`:
  - added arg/param `target_directed_action_frame`, default `base_link`.

Verification:

```text
python3 -m py_compile:
  expert_policy.py: PASS
  scripted_expert.py: PASS
```

Next minimum check:

- Rerun the same short multi-step B5d' smoke after the base-frame action fix:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b5d_reaching_smoke \
  episode_id:=b5d_target_directed_arm_multistep_base_frame \
  rate_hz:=2.0 \
  max_duration_sec:=4.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_action_frame:=base_link \
  target_directed_states:=MOVE_TO_PREGRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=false \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.25
```

Expected result:

- Multiple bounded `B5 arm command` log lines.
- Validator PASS.
- Active-left joint changes remain bounded.
- Final distance should be lower than initial distance, or the distance should
  remain stably near the base-relative target offset without the previous
  frame-induced divergence.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- rollout or grasp-success claims.

## Round 61: B5d' Base-Frame Multi-Step Smoke Minimal Resolved

Date: 2026-05-03

User context:

```text
uvms_control oberon7_position_control.launch gui:=false paused:=false
roslaunch rexrov_single_oberon7_fm_dp b5d_move_group_with_context.launch \
  allow_trajectory_execution:=false \
  load_robot_description:=false \
  pipeline:=ompl
base_relative_target.py running
source devel/setup.bash already executed
```

Command:

```bash
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=.../data/raw/b5d_reaching_smoke \
  episode_id:=b5d_target_directed_arm_multistep_base_frame \
  rate_hz:=2.0 \
  max_duration_sec:=4.0 \
  spawn_target:=false \
  require_target:=true \
  allow_nominal_state_fallback:=false \
  execute_arm:=true \
  enable_gripper_command:=false \
  target_directed_reaching:=true \
  target_directed_action_frame:=base_link \
  target_directed_states:=MOVE_TO_PREGRASP \
  execute_arm_states:=MOVE_TO_PREGRASP \
  execute_arm_once_per_state:=false \
  max_linear_step:=0.005 \
  max_joint_delta:=0.01 \
  command_connection_timeout_sec:=5.0 \
  post_publish_sleep_sec:=0.25
```

Runtime result:

```text
Ready to take commands for planning group arm_l.
Scripted expert running ... execute_arm=True gripper_command_enabled=False target_directed_reaching=True
B5 arm command state=MOVE_TO_PREGRASP ...
B5 arm command state=MOVE_TO_PREGRASP ...
B5 arm command state=MOVE_TO_PREGRASP ...
Saved episode:
  data/raw/b5d_reaching_smoke/b5d_target_directed_arm_multistep_base_frame.npz
```

Validation:

```text
validation: PASS
T: 8
success: False
episode_id: b5d_target_directed_arm_multistep_base_frame
unavailable_fields: ['raw_command']
```

Metadata:

```text
allow_nominal_state_fallback: False
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
field_availability:
  action_ee_delta: True
  eef_pose: True
  raw_command: False
  relative_target_to_eef: True
  target_pose: True
```

Distance and bounded-motion check:

```text
distances:
  [0.11674903139713148, 0.1440472438725511,
   0.12025333681185787, 0.11337451150939361,
   0.10535137682758079, 0.1214406345568693,
   0.09354451986644824, 0.11532847539566887]

initial_distance: 0.11674903139713148
final_distance:   0.11532847539566887
min_distance:     0.09354451986644824
distance_reduction: 0.0014205560014626112

target_motion: 1.2395830313254934
eef_motion:    1.2362182789054765

active_joint_delta_first_to_last:
  [-0.005893073707248675, 0.008004283206865637,
   -0.003241815258467895, 0.007022440524626639,
   -0.016295125282568712, -0.008366855979776489]

active_joint_total_max_abs: 0.022689931659028773
```

Decision:

```text
B5d' arm-only scripted reaching expert is minimal resolved for debug smoke.
```

Interpretation:

- Multi-step command execution works with the package-local MoveIt context
  wrapper and base-frame target-directed action.
- The expert issued repeated bounded left-arm commands with gripper disabled.
- The recorder wrote a non-fallback live-state episode and validator passed.
- The EEF-target distance stayed in a local band and reached a minimum of about
  `0.094 m`, below the provisional `0.10 m` reaching threshold.
- Final distance was slightly lower than initial distance, though only by about
  `0.0014 m`; this is enough for B5d' smoke but not enough to claim robust
  reaching performance.
- `success=False` remains expected and should not be interpreted as grasp
  failure or B5d' failure, because the current route is arm-only and gripper is
  disabled.
- `raw_command` remains unavailable and should remain documented as a recorder
  limitation.

Remaining limitations:

- This is not a real rollout evaluation.
- This is not grasping.
- This is not a success-rate result.
- The reaching behavior is still noisy because the base and base-relative target
  move through world while the arm executes small commands.
- Gripper remains blocked and out of scope.

Next minimum check:

- Move to B8' only as a small data-collection smoke, not training:
  - collect 5 short arm-only reaching/pre-grasp episodes;
  - keep `allow_nominal_state_fallback:=false`;
  - keep `enable_gripper_command:=false`;
  - keep `target_directed_action_frame:=base_link`;
  - use the package-local `b5d_move_group_with_context.launch`;
  - keep exactly one `base_relative_target.py` helper running;
  - validate every episode and inspect distance reduction/min distance.

Still not allowed:

- gripper commands;
- hand controller startup;
- base thruster commands;
- training;
- long simulation;
- rollout or grasp-success claims.

## 2026-05-04 B8' Tuned V3 Cached-Odom Consistency Check

Input episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_cached_odom_check/
  b8_reaching_smoke_tuned_v3_cached_odom_check_0000.npz
```

Prior diagnostics for this episode:

```text
validation: PASS
T: 22
success: False
episodes_below_threshold: 1
min_distance_overall: 0.08611444139540192
mean_final_distance: 0.14779493259862328
mean_distance_reduction: -0.021486852244470306
mean_eef_motion_cosine_with_target: 0.5192861743957111
mean_eef_positive_target_direction_ratio: 0.8095238095238095
mean_best_action_to_eef_cosine: 0.7985718493152257
mean_best_lag_steps: 2.0
```

Per-sample trace:

```text
below_count: 1
below_indices: [10]
min_idx: 10
min_distance: 0.08611444139540188
final_distance: 0.14779493259862325
max_target_step: 0.050329083057232285
max_target_step_idx: 11
```

Stored-vs-recomputed distance check:

```text
max_abs_dist_diff: 5.273559366969494e-16
mean_abs_dist_diff: 2.498001805406602e-16
stored_min_idx: 10
recomputed_min_idx: 10
stored_min_distance: 0.08611444139540192
recomputed_min_distance: 0.08611444139540188
```

Interpretation:

- The saved `relative_target_to_eef` field is arithmetically consistent with
  the saved `base_pose`, `target_pose`, and `eef_pose`.
- This does not independently prove correct runtime synchronization because
  `recorder.py` writes `relative_target_to_eef = target_pose[:3] - eef_pose[:3]`.
- Code inspection showed the likely remaining issue: recorder samples base pose
  from `/rexrov/pose_gt` when available, while target pose comes from
  `/gazebo/model_states`. With a moving base and base-relative target helper,
  this can leave base/target geometry in the saved arrays out of phase.

Decision:

```text
B8' remains unresolved. Current status is smoke-level progress only.
```

Package-local change made for the next minimum check:

- Added default-off recorder parameter `prefer_model_states_base_pose`.
- Exposed it in `collect_episode.launch`.
- Enabled it in `b8_reaching_tuned_v3_episode.launch` so the next B8' v3
  diagnostic records base and target from the same Gazebo model-state source.
- Updated the B8 quality analyzer to accept `base_state_source:
  gazebo_model_states` as valid live non-fallback metadata.

Static checks:

```text
python3 -m py_compile recorder.py analyze_b8_reaching_quality.py: PASS
xmllint collect_episode.launch b8_reaching_tuned_v3_episode.launch: PASS
roslaunch ... b8_reaching_tuned_v3_episode.launch --ros-args: PASS
```

Next minimum check:

```text
Run one short B8' tuned-v3 model-states-base episode only, then validate and run
quality, direction, and command-to-motion diagnostics. Do not collect more
episodes or train until the target-base jumps and final-distance behavior are
understood.
```

## 2026-05-04 B8' Tuned V3 Model-States-Base Check

Input episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_modelstates_base_check/
  b8_reaching_smoke_tuned_v3_modelstates_base_check_0000.npz
```

Runtime setup:

```text
world_base_tf_bridge.launch: running
prefer_model_states_base_pose: True
enable_gripper_command: False
load_hand: false
```

Validation:

```text
validation: PASS
T: 22
success: False
unavailable_fields: ['raw_command']
```

Quality diagnostic:

```text
all_required_metadata_ok: true
episodes_below_threshold: 0
episodes_with_positive_distance_reduction: 0
action_xyz_norm_mean_all_samples: 0.013705911245971635
action_xyz_norm_max_all_samples: 0.015634232257955336
max_active_left_joint_delta: 0.061886022111568906
mean_initial_distance: 0.12842290220394803
min_distance_overall: 0.12090753743754559
mean_final_distance: 0.13143181756986871
mean_distance_reduction: -0.0030089153659206835
recommendation: A
```

Direction diagnostic:

```text
episodes_below_threshold: 0
episodes_with_positive_distance_reduction: 0
mean_action_to_eef_motion_cosine: 0.7703734921799059
mean_eef_motion_cosine_with_target: 0.5634035566283175
mean_eef_positive_target_direction_ratio: 0.8571428571428571
mean_distance_reduction_base: -0.0030089153659203505
recommendation: do_not_collect_more_until_direction_issue_is_understood
```

Command-to-motion diagnostic:

```text
episodes_below_threshold: 0
mean_best_action_to_eef_cosine: 0.8727706444229774
mean_best_lag_steps: 2.0
mean_best_realized_gain_along_action: 0.22840569163153385
recommendation: do_not_collect_more_until_command_to_motion_path_is_explained
```

Decision:

```text
B8' remains unresolved.
```

Interpretation:

- The model-states-base recorder option produced valid live non-fallback data,
  so the previous recorder source-sync suspicion is no longer the leading
  blocker.
- The transient below-threshold artifact disappeared, but the episode did not
  reach the `0.10 m` threshold and final distance was worse than initial.
- The arm is not moving randomly: action-to-EEF and EEF-to-target cosines are
  positive, with a strong best action-to-motion cosine under lag 2.
- The remaining blocker is likely command-response lag / insufficient realized
  end-effector progress relative to the moving base-relative target.

Next minimum check:

```text
Read-only per-sample trace for this exact NPZ, plus command-motion markdown
inspection. Verify target_base max-step, eef_base step, below-threshold count,
and whether lag-2/lag-3 remains dominant. Do not change code or collect another
episode until this trace is reviewed.
```

## 2026-05-04 B8' Model-States-Base Per-Sample Trace Review

Input episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_modelstates_base_check/
  b8_reaching_smoke_tuned_v3_modelstates_base_check_0000.npz
```

Read-only trace result:

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

Command-motion per-lag table:

```text
lag 0: action/eef cos 0.770373, eef/target cos 0.563404,
       gain 0.179801, eef/action norm 0.273518,
       dist-decrease ratio 0.380952
lag 1: action/eef cos 0.828099, eef/target cos 0.633394,
       gain 0.200648, eef/action norm 0.269840,
       dist-decrease ratio 0.400000
lag 2: action/eef cos 0.872771, eef/target cos 0.698900,
       gain 0.228406, eef/action norm 0.254399,
       dist-decrease ratio 0.368421
lag 3: action/eef cos 0.829978, eef/target cos 0.776200,
       gain 0.219708, eef/action norm 0.251689,
       dist-decrease ratio 0.388889
```

Updated blocker interpretation:

- Target-base max step is now about `0.0166 m`, not the previous `0.05 m`
  spike scale. The base-relative target / recorder source issue is reduced for
  this run.
- EEF motion is directionally aligned but small relative to command magnitude:
  `eef/action norm` is only about `0.25-0.27`.
- Best response is still lag 2, and distance decreases on fewer than half the
  samples even under the best lag.
- Current blocker is therefore not target placement or saved-field math. It is
  the quality of the closed-loop arm response: command saturation, response lag,
  and insufficient realized EEF progress.

Decision:

```text
B8' remains unresolved. Do not collect more episodes or train.
```

Next minimum check:

```text
Run one read-only action saturation / lag-compensated progress analysis on this
same NPZ. Confirm whether action_xyz is frequently clipped at max_linear_step
and whether lag-2 EEF progress is too small to close the remaining ~0.02-0.03 m
gap to the reaching threshold.
```

## 2026-05-04 B8' Action Saturation / Lag Progress Review

Input episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_modelstates_base_check/
  b8_reaching_smoke_tuned_v3_modelstates_base_check_0000.npz
```

Action saturation result:

```text
max_linear_step: 0.01
action_norm_mean: 0.013705911245971635
action_norm_max: 0.015634232257955336
clip_component_fraction: 0.5909090909090909
clip_sample_fraction: 0.9545454545454546
initial/min/final_distance:
  0.12842290220394822 / 0.12090753743754573 / 0.13143181756986858
```

Lag-compensated progress:

```text
lag 0: mean_motion_along_action 0.0026166904028726524,
       mean_motion_toward_target 0.002141803549978179,
       distance_decrease_ratio 0.4,
       mean_eef_step 0.003954285937645451
lag 1: mean_motion_along_action 0.002896688193264319,
       mean_motion_toward_target 0.0024535920254215907,
       distance_decrease_ratio 0.3684210526315789,
       mean_eef_step 0.0038850260069578134
lag 2: mean_motion_along_action 0.003289428594567762,
       mean_motion_toward_target 0.002913311600383822,
       distance_decrease_ratio 0.3888888888888889,
       mean_eef_step 0.0036671859016857303
lag 3: mean_motion_along_action 0.00317978200838158,
       mean_motion_toward_target 0.002893324943002134,
       distance_decrease_ratio 0.35294117647058826,
       mean_eef_step 0.003646056491872315
```

Updated blocker interpretation:

- Target-directed commands are nearly always clipped at `max_linear_step`.
- EEF motion is directionally positive, but realized target-directed progress is
  only about `2-3 mm` per sample and does not consistently reduce distance.
- Lag 2 remains visible, but lag compensation does not resolve the reaching
  failure.
- The remaining issue is likely either:
  - EE action limit too small for the moving target/base condition;
  - joint delta limit clipping IK output;
  - controller response lag / low realized gain;
  - or a combination of these.

Decision:

```text
B8' remains unresolved. Do not collect more episodes or train.
```

Next minimum check:

```text
Read-only active-joint step saturation analysis on the same NPZ. Check whether
per-step active joint deltas are close to max_joint_delta=0.01. This decides
whether the next bounded smoke should tune max_linear_step, max_joint_delta, or
timing/horizon.
```

## 2026-05-04 B8' Active-Joint Step Saturation Review

Input episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_modelstates_base_check/
  b8_reaching_smoke_tuned_v3_modelstates_base_check_0000.npz
```

Read-only result:

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

Updated blocker interpretation:

- The active joint position changes are not close to the configured
  per-component `max_joint_delta=0.01`.
- The earlier action saturation is therefore not mirrored by observed joint
  step saturation in this episode.
- The narrowest next runtime check is to increase only `max_linear_step`
  slightly while keeping `max_joint_delta` unchanged.

Decision:

```text
B8' remains unresolved. Do not collect more than one check episode and do not
train.
```

Next minimum check:

```text
Run exactly one bounded parameter-only B8' smoke:
  max_linear_step:=0.015
  max_joint_delta:=0.010
Then validate and rerun quality, direction, command-motion, and per-sample
trace checks.
```

## 2026-05-04 B8' Linear015 Attempt / Launch Arg Bug

Attempted runtime command:

```text
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v3_episode.launch \
  output_dir:=.../b8_reaching_smoke_tuned_v3_linear015_check \
  episode_id:=b8_reaching_smoke_tuned_v3_linear015_check_0000 \
  target_model_name:=cylinder_target_b8_tuned_v3_linear015_check_0000 \
  max_linear_step:=0.015 \
  max_joint_delta:=0.010
```

Observed launch parameters:

```text
/dp_fm_scripted_expert/max_linear_step: 0.01
/dp_fm_scripted_expert/max_joint_delta: 0.01
/dp_fm_episode_recorder/max_linear_step: 0.01
/dp_fm_episode_recorder/max_joint_delta: 0.01
```

Saved episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_linear015_check/
  b8_reaching_smoke_tuned_v3_linear015_check_0000.npz
```

Saved/offline results:

```text
validation: PASS
T: 22
metadata success: False
episodes_below_threshold: 0
episodes_with_positive_distance_reduction: 1
min_distance_overall: 0.12092995986807226
mean_initial_distance: 0.1265129865394417
mean_final_distance: 0.12181283826761834
mean_distance_reduction: 0.004700148271823371
mean_best_action_to_eef_cosine: 0.9001290086972836
mean_best_lag_steps: 3.0
mean_best_realized_gain_along_action: 0.17225911074464081
```

Runtime discrepancy:

```text
Scripted expert finished: success=True reason=reaching_success: distance
0.072762 below 0.100000
```

Interpretation:

- The parameter check was inconclusive because the B8 v3 wrapper hardcoded
  `max_linear_step=0.010` and did not expose/pass through the requested
  top-level override.
- The expert logged a later live success after the recorder had already saved
  the NPZ. The saved episode remains `success=False` and should be used for
  offline quality decisions.
- This episode cannot be counted as a valid `max_linear_step=0.015` check.

Package-local fix:

- `launch/b8_reaching_tuned_v3_episode.launch` now declares top-level
  `max_linear_step` and `max_joint_delta` args.
- The wrapper passes those values through to `collect_episode.launch`.

Verification:

```text
xmllint --noout launch/b8_reaching_tuned_v3_episode.launch: PASS
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v3_episode.launch \
  max_linear_step:=0.015 max_joint_delta:=0.010 --ros-args: PASS
```

Decision:

```text
B8' remains unresolved. Re-run exactly one bounded linear015 smoke after the
launch fix. Do not collect multiple episodes and do not train.
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

Validation:

```text
validation: PASS
T: 22
success: False
unavailable_fields: ['raw_command']
```

Quality:

```text
all_required_metadata_ok: true
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 0
min_distance_overall: 0.09764575942871043
mean_initial_distance: 0.12656234283023146
mean_final_distance: 0.1301823491793326
mean_distance_reduction: -0.003620006349101146
```

Per-sample trace:

```text
below_count: 1
below_indices: [11]
min_distance: 0.09764575942871055
final_distance: 0.13018234917933294
max_target_step: 0.02990258511521412
max_eef_step: 0.007442174853866621
```

Command-motion:

```text
mean_best_action_to_eef_cosine: 0.8544660083304763
mean_best_lag_steps: 3.0
mean_best_realized_gain_along_action: 0.09906462168993792
best_distance_decreasing_ratio: 0.555556
best_eef_action_norm: 0.112664
```

Action/joint saturation:

```text
max_linear_step: 0.015
clip_component_fraction: 0.6666666666666666
clip_sample_fraction: 1.0
overall_abs_dq_max: 0.005893111747848678
near_limit_component_fraction: 0.0
near_limit_step_fraction: 0.0
```

Updated blocker interpretation:

- The fixed linear015 run is now a valid parameter check.
- It produced a single transient below-threshold sample, but not a stable
  reaching result.
- Final distance is worse than initial distance and metadata `success=False`.
- Increasing `max_linear_step` did not improve realized gain; best realized
  gain fell to about `0.099`, and best lag moved to 3 samples.
- Joint step saturation is still ruled out.

Decision:

```text
B8' remains unresolved. Do not collect more episodes or train.
```

Package-local timing arg fix:

- `launch/b8_reaching_tuned_v3_episode.launch` now declares and passes through
  `time_from_start_sec`.
- Verification passed with:
  `roslaunch ... time_from_start_sec:=0.5 --ros-args`.

Next minimum check:

```text
Run exactly one timing-only smoke:
  max_linear_step:=0.010
  max_joint_delta:=0.010
  time_from_start_sec:=0.5
Then validate and rerun quality / command-motion diagnostics.
```

## 2026-05-05 B8' Timing05 Fresh-Restart Check

User runtime setup:

- Restarted `oberon7_position_control.launch`.
- Restarted `b5d_move_group_with_context.launch`.
- Restarted `load_left_controllers.launch` with `load_hand:=false`.
- Restarted `world_base_tf_bridge.launch`.

Episode command:

```bash
roslaunch rexrov_single_oberon7_fm_dp b8_reaching_tuned_v3_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_smoke_tuned_v3_timing05_check \
  episode_id:=b8_reaching_smoke_tuned_v3_timing05_check_0000 \
  target_model_name:=cylinder_target_b8_tuned_v3_timing05_check_0000 \
  max_linear_step:=0.010 \
  max_joint_delta:=0.010 \
  time_from_start_sec:=0.5
```

Runtime parameter confirmation:

```text
/dp_fm_scripted_expert/max_linear_step: 0.01
/dp_fm_episode_recorder/max_linear_step: 0.01
/dp_fm_scripted_expert/max_joint_delta: 0.01
/dp_fm_episode_recorder/max_joint_delta: 0.01
/dp_fm_scripted_expert/time_from_start_sec: 0.5
/dp_fm_episode_recorder/prefer_model_states_base_pose: True
```

Validation:

```text
validation: PASS
T: 22
success: False
unavailable_fields: ['raw_command']
```

Quality:

```text
all_required_metadata_ok: true
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

Judgment:

```text
B8' is not resolved.
```

Evidence:

- Fresh restart did not produce stable reaching; the saved episode is
  `success=False`.
- The episode crossed the threshold only transiently, while final distance
  ended worse than initial distance.
- Timing05 made command-to-motion evidence worse, not better.
- Because the environment was freshly restarted, the blocker should not be
  reduced to "simulation has been open too long".

Next minimum read-only checks:

```text
1. Per-sample timing05 trace: distance, target step in base frame, EEF step in
   base frame, and below-threshold sample count.
2. Active-joint per-step saturation: identify whether the large
   max_active_left_joint_delta is a single jump, normal accumulated motion, or
   an analyzer convention issue.
```

No code change is required before these read-only checks.

### Timing05 Per-Sample And Joint-Step Read-Only Follow-Up

Per-sample trace result:

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

Relevant rows:

```text
idx 9:  distance=0.095370, below=True, target_step_base=0.044189,
        eef_step_base=0.011241
idx 14: distance=0.099106, below=True, target_step_base=0.040712,
        eef_step_base=0.010332
```

Active-joint per-step check:

```text
max_joint_delta: 0.01
per_component_abs_dq_max:
  [0.008265520424274975, 0.008111074374643756,
   0.008274420660465687, 0.008281278212217913,
   0.00825260410423212, 0.00828410691511916]
overall_abs_dq_max: 0.00828410691511916
step_norm_mean: 0.011891137668989504
step_norm_max: 0.019516438887074192
near_limit_component_fraction: 0.0
near_limit_step_fraction: 0.0
```

Judgment:

```text
B8' remains unresolved.
```

Updated evidence:

- The two threshold crossings align with target-in-base jumps of about
  `4 cm`, so they are not stable reaching evidence.
- Joint per-component steps remain below the configured `0.01 rad` step limit;
  joint-step saturation is ruled out for this episode.
- The quality summary's larger active-left joint delta should be interpreted as
  an episode-level joint range metric, not as a single command step violation.

Next minimum read-only check:

```text
Inspect source synchronization on the same timing05 NPZ by comparing base world
step, base yaw step, target world step, and target-in-base step. This should
separate target updater/base-source mismatch from EEF/control response.
```

### Timing05 Source-Synchronization Read-Only Follow-Up

Diagnostic result:

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

Important rows:

```text
idx 9:
  distance=0.095370
  target_step_base=0.044189
  target_step_world=0.111323
  base_step_world=0.149658
  base_yaw_step=0.035038

idx 14:
  distance=0.099106
  target_step_base=0.040712
  target_step_world=0.109175
  base_step_world=0.150734
  base_yaw_step=0.035259
```

Judgment:

```text
B8' remains unresolved, but the immediate source of false threshold crossings
is now identified.
```

Interpretation:

- The target is being moved in world at almost the same scale as the base
  motion, but the target-in-base reconstruction still jumps several
  centimeters.
- The likely cause is source mismatch: `base_relative_target.py` was computing
  target updates from `/rexrov/pose_gt`, while the recorder was configured to
  prefer `/gazebo/model_states` for base pose.
- This explains why threshold crossings line up with target-in-base jumps
  rather than stable EEF progress.

Package-local code change:

- `src/rexrov_single_oberon7_fm_dp/base_relative_target.py` now subscribes to
  `/gazebo/model_states` and can use the `rexrov` model pose when
  `prefer_model_states_base_pose=true`.
- `launch/collect_episode.launch` passes `prefer_model_states_base_pose` to
  the base-relative target helper.

Verification:

```text
python3 -m py_compile base_relative_target.py: PASS
xmllint --noout collect_episode.launch b8_reaching_tuned_v3_episode.launch: PASS
roslaunch ... b8_reaching_tuned_v3_episode.launch ... --ros-args: PASS
```

Next minimum check:

```text
Run exactly one short source-aligned B8' smoke with the same conservative
step limits and default v3 timing:
  max_linear_step:=0.010
  max_joint_delta:=0.010
  time_from_start_sec:=1.0
Then validate and rerun quality plus source-sync diagnostics.
```

### Source-Aligned Smoke Result

Episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_source_aligned_check/
  b8_reaching_smoke_tuned_v3_source_aligned_check_0000.npz
```

Runtime confirmation:

```text
/b5d_base_relative_target/prefer_model_states_base_pose: True
B5d base-relative target initialized with base_pose_source=gazebo_model_states
/dp_fm_scripted_expert/time_from_start_sec: 1.0
/dp_fm_scripted_expert/max_linear_step: 0.01
/dp_fm_scripted_expert/max_joint_delta: 0.01
```

Validation:

```text
validation: PASS
T: 22
success: False
```

Quality:

```text
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 0
min_distance_overall: 0.0532669152181874
mean_initial_distance: 0.12408179276740143
mean_final_distance: 0.1551152861323729
mean_distance_reduction: -0.03103349336497148
max_active_left_joint_delta: 0.07687656416610089
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

Judgment:

```text
B8' remains unresolved.
```

Updated evidence:

- The source-aligned base pose fix improved the early target-in-base stability.
- The later 6-10 cm target-in-base jumps occur while base world/yaw steps are
  small, so the previous odom/model-states mismatch is not the remaining cause.
- The target model is still a dynamic, colliding SDF object, which can be
  pushed or destabilized near the arm/EEF and contaminate reaching geometry.

Package-local code/data fix:

- `models/cylinder_target/model.sdf` changed from a dynamic colliding cylinder
  to a static visual marker:
  - `<static>true</static>`
  - inertial block removed
  - collision block removed

Verification:

```text
xmllint --noout models/cylinder_target/model.sdf: PASS
```

Next minimum check:

```text
Run exactly one source-aligned static-marker B8' smoke with:
  max_linear_step:=0.010
  max_joint_delta:=0.010
  time_from_start_sec:=1.0
Then validate and rerun quality plus source-sync diagnostics.
```

### Static-Marker Source-Aligned Smoke Result

Episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_static_marker_check/
  b8_reaching_smoke_tuned_v3_static_marker_check_0000.npz
```

Runtime confirmation:

```text
/b5d_base_relative_target/prefer_model_states_base_pose: True
B5d base-relative target initialized with base_pose_source=gazebo_model_states
/dp_fm_scripted_expert/time_from_start_sec: 1.0
/dp_fm_scripted_expert/max_linear_step: 0.01
/dp_fm_scripted_expert/max_joint_delta: 0.01
gripper command disabled
```

Runtime failure:

```text
Scripted expert failed: IK failed with MoveIt error code -31
```

Validation:

```text
validation: PASS
T: 22
success: False
unavailable_fields: ['raw_command']
```

Quality:

```text
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 1
min_distance_overall: 0.09603994656753867
mean_initial_distance: 0.10795291320748376
mean_final_distance: 0.09728469429144865
mean_distance_reduction: 0.010668218916035116
max_active_left_joint_delta: 0.010010654179503753
```

Source-sync diagnostic:

```text
target_step_base max: 0.011193 m
prior 0.06-0.10 m target-base jumps: absent
distance entered and stayed near the threshold band from idx 3 onward
```

Judgment:

```text
Target/source synchronization is smoke-level resolved. B8' remains unresolved
because the scripted expert crashed with IK error -31.
```

Updated evidence:

- Static marker plus model-states base alignment removed the previous geometry
  contamination.
- The saved episode is valid diagnostic NPZ data and distance quality improved.
- It is not enough to expand collection or train because the runtime expert
  failed and metadata `success=False`.

Next minimum read-only checks:

```text
1. Run command-to-motion diagnostics on the static-marker NPZ.
2. Inspect the dp_fm_scripted_expert log around MoveIt error code -31.
```

No code change is required before those read-only checks.

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

Expert log excerpt:

```text
Scripted expert running with target source gazebo_model_states
Scripted expert state_sequence=['MOVE_TO_PREGRASP', 'MOVE_TO_GRASP']
B5 arm command state=MOVE_TO_PREGRASP ... command_positions=[...]
Scripted expert failed: IK failed with MoveIt error code -31
```

Judgment:

```text
B8' remains unresolved.
```

Evidence:

- Geometry/source-sync blocker is smoke-level resolved for this single static
  marker episode.
- The expert crashed after publishing one arm command.
- Command-to-motion alignment remains poor, with best action/eef cosine near
  zero.
- The saved episode remains metadata `success=False`.

Next minimum read-only check:

```text
Inspect static-marker NPZ per-sample action, EEF motion, target direction,
distance, and active-joint deltas. This should determine whether the command
topic data is stale after the crash, whether base-relative EEF motion is not
following the published action, or whether IK is failing at a Cartesian
boundary.
```

### Static-Marker Per-Sample Action/Motion Follow-Up

Read-only per-sample result:

```text
max_joint_delta: 0.01
action_xyz remained nonzero after the expert crash:
  [0.01, -0.000966, 0.01] for most samples
joint_step_norm:
  nonzero through idx 4
  zero from idx 5 through idx 21
distance:
  stayed around 0.096-0.097 m for most samples
```

Judgment:

```text
B8' remains unresolved.
```

Interpretation:

- Command-motion diagnostics are not reliable after the expert crash because
  the recorder stores the last action while no new joint command is being
  executed.
- Geometry/source-sync is now clean enough for smoke evidence, but the executed
  command sequence is invalid after the IK failure.
- The active blocker is `IK failed with MoveIt error code -31`.

Package-local diagnostic code change:

- `arm_command_converter.py` now logs the failed IK request context before
  raising the existing runtime error:
  - MoveIt error code;
  - group name;
  - IK link;
  - target frame, target XYZ, target quaternion;
  - seed joint names and seed positions.

Verification:

```text
python3 -m py_compile arm_command_converter.py: PASS
```

Next minimum check:

```text
Run exactly one short static-marker IK-context smoke with the same parameters,
then inspect the new dp_fm_scripted_expert log. This is instrumentation-only
debug, not dataset collection expansion.
```

### IK-Context Static-Marker Smoke Follow-Up

Episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_ik_context_check/
  b8_reaching_smoke_tuned_v3_ik_context_check_0000.npz
```

Runtime outcome:

```text
target updater base_pose_source: gazebo_model_states
static visual marker target
max_linear_step: 0.010
max_joint_delta: 0.010
time_from_start_sec: 1.0
```

Expert behavior:

```text
multiple B5 arm commands were published through MOVE_TO_PREGRASP and
MOVE_TO_GRASP
no "IK request failed" line appeared in the latest expert log
no "IK failed" line appeared in the latest expert log
scripted expert finished cleanly:
  success=True reason=reaching_success: distance 0.091776 below 0.100000
```

Recorder timing limitation:

```text
The recorder saved the NPZ before the expert printed success=True, so the
saved episode cannot be judged from runtime success alone.
```

Judgment:

```text
B8' is not yet resolved. The IK error did not reproduce, which is runtime
progress, but saved-data validation and quality evidence are still missing.
```

Next minimum read-only checks:

```text
1. validate_episode.py on the IK-context NPZ.
2. analyze_b8_reaching_quality.py on the IK-context output directory.
3. source-sync diagnostic on the same NPZ.
4. command-motion diagnostic on the same NPZ.
```

### IK-Context Saved-NPZ Validation And Quality Follow-Up

Validation:

```text
validation: PASS
T: 22
success: False
unavailable_fields: ['raw_command']
```

Quality:

```text
all_required_metadata_ok: true
episodes_below_threshold: 1
episodes_with_positive_distance_reduction: 1
min_distance_overall: 0.0828415071948108
mean_initial_distance: 0.10770328097682604
mean_final_distance: 0.08769499361884395
mean_distance_reduction: 0.020008287357982088
max_active_left_joint_delta: 0.07163564753196727
```

Judgment:

```text
B8' is smoke-level resolved for one saved non-fallback static-marker reaching
episode, with limitations.
```

Evidence:

- The saved NPZ validates.
- The saved NPZ crosses and ends below the `0.10 m` reaching threshold.
- Distance reduction is positive.
- The previous IK `-31` failure did not reproduce in the instrumented run.

Limitations:

- This is not repeatability evidence.
- Saved `success` metadata is still false even though the distance metric and
  later expert runtime line indicate reaching success.
- Source-sync and command-motion diagnostics are still required before any
  collection expansion.

Next minimum checks:

```text
Run source-sync and command-motion diagnostics on the IK-context NPZ only.
Do not collect another episode and do not train.
```

### IK-Context Command-Motion Follow-Up

Read-only per-sample action/motion result:

```text
max_joint_delta: 0.01
distance: 0.107703 -> 0.087695 m
min distance: 0.082842 m
joint_step_norm: nonzero through idx 1-21
max_abs_dq per sample: below 0.0061 rad
```

Command-motion diagnostic:

```text
episodes_total: 1
episodes_below_threshold: 1
mean_best_action_to_eef_cosine: 0.21415299860000098
mean_best_lag_steps: 2.0
mean_best_realized_gain_along_action: 0.1560406398996791
recommendation: do_not_collect_more_until_command_to_motion_path_is_explained
```

Judgment:

```text
B8' is smoke-level resolved only; it is not collection-ready.
```

Evidence:

- The saved IK-context NPZ is valid and reaches below threshold.
- Final distance is below threshold and improves from the first sample.
- The previous IK `-31` crash did not reproduce.
- The stale-action failure mode from the crashed static-marker episode is not
  present in this saved episode because joints continue moving.

Remaining blockers before expanding data collection:

- The saved success metadata remains `False`.
- Command-to-motion alignment is still weak/mixed despite improvement over the
  crashed static-marker episode.
- Source-sync diagnostics on this exact IK-context NPZ are still missing.

Next minimum read-only check:

```text
Run source-sync diagnostics on the IK-context NPZ. Expected clean result:
target_step_base remains bounded with no new >0.03 m jumps. If it is clean,
the next blocker-local question is saved success synchronization and
repeatability, not gripper or training.
```

### IK-Context Source-Sync Follow-Up

Read-only source-sync result:

```text
min_distance: 0.08284150719481084
final_distance: 0.08769499361884403
max_target_step_base: 0.012109104884360282
large_target_step_indices: []
```

Judgment:

```text
The current B8' blocker is smoke-level resolved, with strict one-episode
limits. It is not repeatability-collection ready.
```

Resolved at smoke level:

- The saved NPZ validates.
- The saved episode reaches below threshold and finishes below threshold.
- Distance improves from initial to final.
- The previous IK `-31` crash did not reproduce.
- Target/base synchronization is clean enough for this smoke episode:
  no `>0.03 m` target-in-base jumps.
- The stale-action-after-crash failure mode is absent in this saved episode.

Still open before any collection expansion:

- Saved metadata `success=False` is inconsistent with distance-based reaching
  success.
- Command-to-motion remains mixed; the analyzer still recommends explaining the
  path before collecting more.
- No repeatability evidence exists yet.

Next blocker-local task:

```text
Inspect/fix recorder success synchronization for arm-only reaching episodes.
Do not collect repeatability episodes, do not start gripper/hand controllers,
and do not train policies before this is addressed.
```

### Recorder Success Metadata Synchronization Fix

Read-only inspection:

```text
recorder.py line path:
  _expert_success_cb stores the latest expert success Bool.
  _build_metadata uses that value only if it has arrived.
  Otherwise it falls back to self.success from the launch parameter.
```

Diagnosis:

- In the IK-context smoke, the recorder saved the NPZ before the scripted
  expert published its final `success=True`.
- Therefore saved metadata stayed at the launch default `success=False`,
  despite the saved final distance being below the reaching threshold.

Code change:

```text
src/rexrov_single_oberon7_fm_dp/recorder.py
```

Implementation:

- Added final-distance success evaluation for `reaching_success` and
  `pregrasp_success`.
- Uses final recorded `relative_target_to_eef` and
  `task_grasp.yaml::success_distance_threshold`.
- Writes success provenance into metadata:
  - `success_source`;
  - `recorded_success_distance_m`;
  - `recorded_success_distance_threshold_m`.

Verification:

```text
python3 -m py_compile recorder.py: PASS
existing IK-context final distance: 0.08769499361884395
would_record_success: True
```

Next minimum validation:

```text
Run one short IK-context-equivalent smoke only, then run validate_episode.py.
Expected: saved `success=True` if final recorded distance remains below
0.10 m. Do not run repeatability collection or training yet.
```

### Recorder Success Metadata Runtime Validation

Validation episode:

```text
data/raw/b8_reaching_smoke_tuned_v3_success_sync_check/
  b8_reaching_smoke_tuned_v3_success_sync_check_0000.npz
```

Runtime:

```text
Scripted expert finished:
  success=True reason=reaching_success: distance 0.035195 below 0.100000
```

Validator:

```text
validation: PASS
T: 22
success: True
unavailable_fields: ['raw_command']
```

Metadata:

```text
success scalar: True
metadata success: True
success_source: recorded_final_distance
recorded_success_distance_m: 0.0404588355643862
recorded_success_distance_threshold_m: 0.1
```

Judgment:

```text
The current B8' blocker is smoke-level resolved, including saved success
metadata synchronization.
```

Evidence:

- Runtime expert success and saved NPZ success agree.
- Saved success is sourced from the recorded final distance, so it no longer
  depends on the expert success message arriving before recorder save.
- The validation episode remains non-gripper arm-only reaching evidence.

Limits:

- This does not prove repeatability.
- This does not prove grasp success or learned-policy rollout success.
- Do not train or expand to large collection from this single episode.

### B8' Repeatability Smoke: 5 Short Episodes

Scope:

```text
B8' repeatability smoke: 3-5 episode real non-fallback arm-only
reaching/pre-grasp repeatability check, no training, no gripper handling.
```

Runtime:

- Minimal simulation: `uvms_control oberon7_position_control.launch
  gui:=false paused:=false`.
- MoveIt context: `b5d_move_group_with_context.launch
  allow_trajectory_execution:=false`.
- Left arm controller only:
  `load_left_controllers.launch start:=true load_hand:=false`.
- TF bridge: `world_base_tf_bridge.launch`.
- Episode wrapper: `b8_reaching_tuned_v3_episode.launch`.
- Parameters: `max_linear_step=0.010`, `max_joint_delta=0.010`,
  `time_from_start_sec=1.0`.
- Gripper remained disabled; no hand controller was started and no gripper
  command was sent.

Data:

```text
data/raw/b8_reaching_repeatability_smoke/
  b8_reaching_repeatability_smoke_0000.npz
  b8_reaching_repeatability_smoke_0001.npz
  b8_reaching_repeatability_smoke_0002.npz
  b8_reaching_repeatability_smoke_0003.npz
  b8_reaching_repeatability_smoke_0004.npz
```

New helper:

```text
scripts/summarize_b8_repeatability_smoke.py
```

Reason:

- Existing B8 analyzers split quality, direction, and command-motion metrics.
- The repeatability smoke needed one read-only summary for validator pass
  count, metadata consistency, saved success provenance, source-sync large
  target-step indices, and failure reason per episode.

Validation:

```text
validator_pass_count: 5/5
T: 22 for all episodes
success: True for all episodes
unavailable_fields: ['raw_command'] for all episodes
```

Repeatability summary:

```text
episodes_total: 5
episodes_valid: 5
success_count: 5
reaching_success_rate: 1.0
all_required_metadata_ok: true
all_success_metadata_consistent: true
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
distance_reduction_per_episode:
  [0.03885999744559045,
   0.05876825088662491,
   0.05156379677058422,
   0.04770268680172913,
   0.0396789040641148]
mean_final_distance: 0.06034401658235772
min_distance_overall: 0.04955370542041048
mean_distance_reduction: 0.0473147271937287
max_active_left_joint_delta: 0.06810874321597282
max_target_step_base: 0.014892885342403243
large_target_step_indices: [] for all episodes
failure_reason: none for all episodes
```

Command-motion and direction diagnostics:

```text
mean_best_action_to_eef_cosine: 0.7559808833882034
mean_best_lag_steps: 2.2
mean_best_realized_gain_along_action: 0.2432157689973347
mean_eef_motion_cosine_with_target: 0.5385524726109748
mean_eef_positive_target_direction_ratio: 0.819047619047619
mean_action_to_eef_motion_cosine: 0.583383307160201
```

Metadata:

```text
success_source: recorded_final_distance for all episodes
recorded_success_distance_threshold_m: 0.1 for all episodes
allow_nominal_state_fallback: false for all episodes
base_state_source: gazebo_model_states for all episodes
joint_state_source: joint_states for all episodes
target_state_source: gazebo_model_states for all episodes
gripper_enabled: false for all episodes
is_grasp_dataset: false for all episodes
```

Judgment:

```text
B8' repeatability smoke is resolved at the 5-episode smoke level.
```

Limits:

- This is still arm-only reaching/pre-grasp evidence, not grasping.
- This is not learned rollout evaluation.
- This is not BC / Diffusion Policy / Flow Matching Policy training evidence.
- Do not expand directly to 20/50/100 episodes from this result; the next step
  should be a deliberately small real non-fallback arm-only data collection
  plan with the same diagnostics.

### B8' Small Debug Batch: 10-Episode Odom-Source Check

Scope:

```text
B8' small debug batch：10–15 episode real non-fallback arm-only reaching/pre-grasp debug collection，不训练、不处理 gripper。
```

Date: 2026-05-05.

What changed from the 5-episode repeatability smoke:

- The 5-episode repeatability smoke used `base_state_source=gazebo_model_states`.
- This run required `base_state_source=odom`, so collection used
  `collect_episode.launch` directly with
  `prefer_model_states_base_pose:=false`.
- A strict `--required-base-state-source odom` mode and
  `--fail-on-problem` option were added to
  `scripts/summarize_b8_repeatability_smoke.py`.

Runtime:

- `uvms_control oberon7_position_control.launch gui:=false paused:=false`
- `b5d_move_group_with_context.launch allow_trajectory_execution:=false`
- `load_left_controllers.launch start:=true load_hand:=false`
- `world_base_tf_bridge.launch`
- `collect_episode.launch` with gripper disabled and
  `allow_nominal_state_fallback:=false`

Data:

```text
data/raw/b8_reaching_debug_10/
```

Diagnostics:

```text
outputs/logs/b8_reaching_debug_10/repeatability_summary.json
outputs/logs/b8_reaching_debug_10/repeatability_summary.md
outputs/logs/b8_reaching_debug_10_quality/
outputs/logs/b8_reaching_debug_10_direction/
outputs/logs/b8_reaching_debug_10_command_motion/
```

Summary:

```text
episodes_total: 10
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

Important failure pattern:

```text
episodes 0000-0006: success=True
episode 0007: success=False, final_distance_above_threshold
episode 0008: success=False, final_distance_above_threshold, no_positive_distance_reduction
episode 0009: success=False, final_distance_above_threshold, no_positive_distance_reduction
```

Metadata was correct for all 10 episodes:

```text
allow_nominal_state_fallback=false
base_state_source=odom
joint_state_source=joint_states
target_state_source=gazebo_model_states
gripper_enabled=false
is_grasp_dataset=false
task_type=arm_only_reaching
success_metric=reaching_success
success_source=recorded_final_distance
```

Blocker judgment:

```text
B8' data-path blocker remains resolved for odom-source non-fallback arm-only
recording, but B8' reaching-quality repeatability is not resolved at the
10-episode debug-batch level.
```

Reason:

- Validator and metadata gates passed.
- Target/base source-sync stayed bounded.
- The proposed pass gate was `success_count / N >= 0.8`; this batch reached
  only `0.7`.
- Direction and command-motion diagnostics degraded in the failed tail:
  command-motion recommendation was
  `do_not_collect_more_until_command_to_motion_path_is_explained`.

Next blocker target:

```text
Do not collect more and do not train. Inspect why command-to-motion quality
degrades across repeated short episodes with odom-source base recording,
especially the tail episodes 0007-0009.
```

### B8' Debug Batch Failure Analysis: Tail Episodes 0007-0009

Scope:

```text
B8' debug batch failure analysis：分析 b8_reaching_debug_10 中 0007–0009 连续失败，不训练、不扩采、不处理 gripper。
```

Date: 2026-05-05.

Work performed:

- Added one package-local read-only offline analyzer:
  `scripts/analyze_b8_debug_batch_failure.py`.
- Ran it only on existing NPZ files under
  `data/raw/b8_reaching_debug_10/`.
- Generated failure-analysis artifacts under
  `outputs/logs/b8_reaching_debug_10_failure_analysis/`.
- Did not start ROS, Gazebo, MoveIt, controllers, gripper, training, or
  learned rollout.

Artifacts:

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

Key comparisons:

```text
initial_distance:
  success_mean=0.108700
  failure_mean=0.108612
distance_reduction:
  success_mean=0.040734
  failure_mean=-0.009090
best_action_to_eef_cosine:
  success_mean=0.823278
  failure_mean=-0.071778
best_realized_gain_along_action:
  success_mean=0.209131
  failure_mean=-0.021860
action_relative_cosine:
  success_mean=0.897726
  failure_mean=0.943494
joint_initial_drift_from_ep0:
  success_mean=0.304920
  failure_mean=0.806195
eef_base_initial_drift_from_ep0:
  success_mean=0.173386
  failure_mean=0.330540
target_base_max_step:
  success_mean=0.006151
  failure_mean=0.001934
```

Blocker interpretation:

- Failures are not explained by worse initial distance; failed episodes start
  at essentially the same recorded distance as successful episodes.
- Scripted action direction is not the first-order problem; failed episodes
  still command target-aligned `action_ee_delta`.
- Command-to-motion alignment is the strongest failure signal: realized EEF
  motion weakens in 0007 and becomes poorly aligned or negative along the
  commanded direction in 0008-0009.
- Cross-episode initial active-left joint drift is significant and is the
  strongest reset/accumulation clue.
- Target/base source-sync is less likely as the primary blocker because failed
  target-in-base steps remain below the large-jump threshold.
- Episode duration is less likely because all episodes have `T=22` and similar
  duration.

Current blocker judgment:

```text
B8' reaching-quality repeatability remains blocked by cross-episode
configuration/reset and command-to-motion degradation, not by validator,
metadata, gripper, or target/base source-sync.
```

Next blocker-local action:

```text
Do not collect more yet. Inspect or implement the minimum per-episode
reset/settle gate for active-left joint initial configuration, EEF base pose,
and previous command transients. Then run only a short verification if
explicitly approved.
```

### B8' Initial-State Gate Preparation

Date: 2026-05-05.

Blocker status:

```text
Not resolved.
```

Why:

- The failure-analysis evidence is strong, but it is still diagnostic evidence.
- No runtime check has yet shown that a reset/settle gate prevents the tail
  command-to-motion degradation.
- Do not expand collection or train from `b8_reaching_debug_10`.

Read-only inspection result:

- `collect_episode.launch` has no pre-episode active-left joint reset/gate.
- `batch_collect_episodes.py` has validation/success filtering after an
  episode, but no live initial-state gate before an episode.
- `expert_policy.py` can publish no-op actions while waiting for state/target,
  but does not reject a bad accumulated initial joint/EEF configuration before
  arm execution.

Minimal code added:

```text
scripts/check_b8_initial_state_gate.py
```

Behavior:

- Reads live state only:
  - `/joint_states`;
  - `/rexrov/pose_gt`;
  - `/gazebo/model_states`;
  - TF `rexrov/base_link -> oberon7_l/end_effector`.
- Compares live state against a reference successful NPZ episode.
- Reports:
  - `joint_l2_drift`;
  - `joint_max_abs_drift`;
  - `eef_base_drift`;
  - `target_base_drift`;
  - `relative_base_drift`;
  - `initial_distance`.
- Exits nonzero if any configured gate fails.

Safety boundary:

```text
control_commands_sent=false
gripper_commands_sent=false
```

Verification:

```text
python3 -m py_compile scripts/check_b8_initial_state_gate.py: PASS
source devel/setup.bash; python3 scripts/check_b8_initial_state_gate.py --help: PASS
```

Next minimum command once B8 runtime is active, before any collection. First
run it without requiring a live target:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
rosrun rexrov_single_oberon7_fm_dp check_b8_initial_state_gate.py \
  --reference-npz src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_debug_10/b8_reaching_debug_10_0000.npz \
  --skip-target-checks \
  --output-json src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_initial_state_gate/latest_gate.json
```

What this verifies:

- Whether the next episode would start from a known-good active-left joint and
  EEF/base neighborhood.
- Whether cross-episode drift is already visible before any new command.

Expected success output:

```text
"passed": true
```

Expected useful failure signals:

- `joint_l2_ok=false`: active-left arm did not reset/settle near the reference.
- `eef_base_drift_ok=false`: EEF/base pose accumulated drift.
- In full target-check mode, `initial_distance_ok=false`: the episode would
  start outside the intended reaching envelope.

After a target model/updater is active, rerun without `--skip-target-checks`
and pass the actual current `--target-model-name`.

Do not run collection from a failed gate state.

### B8' Runtime Initial-State Gate Result

Date: 2026-05-05.

User-reported active runtime:

- `uvms_control oberon7_position_control.launch gui:=false paused:=false`
- `b5d_move_group_with_context.launch allow_trajectory_execution:=false`
- `load_left_controllers.launch start:=true load_hand:=false`
- `world_base_tf_bridge.launch`

Command:

```text
check_b8_initial_state_gate.py --reference-npz b8_reaching_debug_10_0000.npz --skip-target-checks
```

Result:

```text
passed: true
control_commands_sent: false
gripper_commands_sent: false

joint_l2_drift: 0.00015674238939907846
joint_max_abs_drift: 0.00010077841280065059
eef_base_drift: 0.00008922043640714035
```

Blocker interpretation:

- Clean runtime startup state is good: active-left joints and EEF/base pose are
  effectively at the successful reference initial condition.
- The previous 0007-0009 failure is therefore unlikely to be caused by bad
  initial state immediately after starting the four base runtime processes.
- The failure remains consistent with drift/accumulation after repeated
  arm-command episodes, or with command-to-motion degradation that only appears
  after commands are issued.
- Target checks were skipped, so target-relative initial distance and
  target/base sync are not covered by this gate result.
- `TF_REPEATED_DATA` warnings were observed from `world_base_tf_bridge`; because
  the gate read finite TF and passed, this is a monitoring warning, not current
  failure evidence.

Updated blocker judgment:

```text
B8' tail degradation is still not resolved. Startup reset looks clean, but
post-command repeatability and target-aware initial-state gating remain
unverified.
```

### B8' Target-Only Gate Probe Launch

Date: 2026-05-05.

Added:

```text
launch/b8_target_gate_probe.launch
```

Reason:

- The previous full target-aware gate could not run because
  `/gazebo/model_states/name` contained only `ocean_box` and `rexrov`.
- Running `collect_episode.launch` only to spawn a target would also start
  recorder/expert and could write a short NPZ, which would mix target probing
  with data collection.
- A target-only launch keeps the next check clean.

Behavior:

- Spawns `cylinder_target_gate_probe`.
- Starts `base_relative_target.py` with offset `[0.10, 0.0, 0.04]`.
- Uses odom base pose by default:
  `prefer_model_states_base_pose=false`.

Safety boundary:

```text
recorder_started=false
expert_started=false
arm_commands_sent=false
hand_controller_started=false
gripper_commands_sent=false
training_started=false
learned_rollout_started=false
```

Verification:

```text
XML parse: PASS
roslaunch --ros-args: PASS
```

Next minimum commands:

```bash
cd /home/benny/uuv_manipulator_ws
source devel/setup.bash
roslaunch rexrov_single_oberon7_fm_dp b8_target_gate_probe.launch
```

Then verify:

```bash
rostopic echo -n 1 /gazebo/model_states/name
```

Expected:

```text
cylinder_target_gate_probe
```

Then run:

```bash
rosrun rexrov_single_oberon7_fm_dp check_b8_initial_state_gate.py \
  --reference-npz src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_reaching_debug_10/b8_reaching_debug_10_0000.npz \
  --target-model-name cylinder_target_gate_probe \
  --output-json src/uvms/rexrov_single_oberon7_fm_dp/outputs/logs/b8_initial_state_gate/latest_target_gate.json
```

Do not collect an episode from this check.

### B8' Target-Aware Initial-State Gate Result

Date: 2026-05-05.

User confirmed the target-only probe model is live:

```text
/gazebo/model_states/name:
  ocean_box
  rexrov
  cylinder_target_gate_probe
```

Command:

```text
check_b8_initial_state_gate.py
  --reference-npz b8_reaching_debug_10_0000.npz
  --target-model-name cylinder_target_gate_probe
```

Result, repeated twice:

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

All gate checks passed:

```text
joint_l2_ok=true
joint_max_abs_ok=true
eef_base_drift_ok=true
relative_base_drift_ok=true
initial_distance_ok=true
```

Blocker interpretation:

- The clean runtime plus target-only probe reproduces the desired initial
  geometry without collecting an episode.
- Startup active-left joint/EEF state and target-relative setup are not the
  cause of the 0007-0009 tail failures.
- This resolves the startup initial-condition gate at smoke level.
- It does not resolve command-to-motion degradation after repeated arm
  commands.

Updated blocker judgment:

```text
B8' startup initial-condition gate: smoke-level resolved.
B8' repeated-command reaching-quality blocker: still open.
```

Next blocker-local action:

```text
Before any arm-command verification, repeat the target-aware gate for a short
read-only stability window with no arm command. If it remains stable, the next
minimum non-read-only check would be one short gated arm-only verification,
not data expansion and not training.
```

### B8' Repeated Target-Aware Gate Stability Result

Date: 2026-05-05.

Command pattern:

```text
Run check_b8_initial_state_gate.py five times with
--target-model-name cylinder_target_gate_probe and about 5 s between runs.
```

Runtime boundary:

```text
arm_commands_sent=false
gripper_commands_sent=false
recorder_started=false
expert_started=false
training_started=false
learned_rollout_started=false
```

Result:

```text
passes: 5/5
all checks true for all runs
```

Metric ranges:

```text
joint_l2_drift: 0.006571430078048146 to 0.006618381619597192
joint_max_abs_drift: 0.006313718676446811 to 0.006351625337845057
eef_base_drift: 0.0011618486495774648 to 0.0012022803850341706
target_base_drift: 0.0011803381838229614 to 0.004144552964742915
relative_base_drift: 0.00004526798965118013 to 0.004136018974138625
initial_distance: 0.10394396276812444 to 0.11000999665938455
```

Blocker interpretation:

- The target-only probe and live TF/EEF geometry are stable enough in a short
  no-command window.
- Passive drift is not currently explaining the 0007-0009 failures.
- The remaining blocker is now specifically post-command: repeated arm
  commands or episode transitions degrade command-to-motion alignment.

Updated blocker judgment:

```text
B8' startup/passive initial-condition gate: smoke-level resolved.
B8' post-command command-to-motion repeatability: still unresolved.
```

Next blocker-local action:

```text
If proceeding, run exactly one short gated arm-only verification episode, then
immediately rerun the target-aware gate and offline diagnostics. This is not a
dataset expansion and not training.
```

### B8' One Gated Arm-Only Verification Episode

Date: 2026-05-05.

Scope:

```text
Exactly one short gated arm-only verification episode.
Not data expansion. Not training. Not learned rollout. Not grasping.
Gripper disabled.
```

Pre-gate:

```text
passed=true
initial_distance=0.1077189674919894
relative_base_drift=0.000060108361737702964
joint_l2_drift=0.006583236356065188
eef_base_drift=0.0011656954861866385
```

Episode:

```text
data/raw/b8_gated_arm_verify_1/b8_gated_arm_verify_1_0000.npz
```

Runtime expert:

```text
success=True
reason=reaching_success: distance 0.042648 below 0.100000
```

Validator:

```text
PASS
T=22
success=True
unavailable_fields=['raw_command']
```

Metadata:

```text
allow_nominal_state_fallback=false
base_state_source=odom
joint_state_source=joint_states
target_state_source=gazebo_model_states
gripper_enabled=false
is_grasp_dataset=false
success_source=recorded_final_distance
recorded_success_distance_m=0.045301559855776316
recorded_success_distance_threshold_m=0.1
```

Offline diagnostics:

```text
initial/min/final distance: 0.106256 / 0.045302 / 0.045302
distance_reduction: 0.060954557777866195
max_active_left_joint_delta: 0.0771154374980636
mean_eef_motion_cosine_with_target: 0.8411411057732849
mean_eef_positive_target_direction_ratio: 1.0
mean_best_action_to_eef_cosine: 0.8718392906129798
mean_best_lag_steps: 0.0
mean_best_realized_gain_along_action: 0.24521231853273232
best_distance_decreasing_ratio: 0.952381
```

Post-gate:

```text
passed=false
relative_base_drift_ok=false
relative_base_drift=0.07180542804879099
initial_distance=0.04013113557371512
joint_l2_drift=0.11565944021317238
eef_base_drift=0.07153365725910747
```

Blocker interpretation:

- Single-command reaching/pre-grasp is good in this gated setup.
- The post-gate failure is expected and useful: after reaching, the arm remains
  near the target instead of returning to the reference initial condition.
- This confirms that a next episode cannot simply start from the post-command
  state if the goal is repeatable same-envelope demonstrations.
- The remaining blocker is reset/return-to-start or per-episode
  reinitialization, not single-episode action direction or single-episode
  command-to-motion.

Updated blocker judgment:

```text
B8' one gated arm-only verification: smoke-level resolved.
B8' multi-episode repeatability: blocked on reset/settle/reinitialization.
```

Next blocker-local action:

```text
Do not collect more episodes yet. Define the minimum reset/settle strategy:
either a bounded return-to-reference arm command, a runtime reset/restart
between episodes, or an explicit gate-and-skip policy that prevents recording
from post-command reached configurations.
```

### B8' Reset/Settle Strategy Definition

Date: 2026-05-05.

Decision:

```text
Use bounded return-to-reference joint command as the first reset/settle
strategy, followed by the existing target-aware initial-state gate.
```

Rejected as first choice:

- Runtime reset/restart between every episode:
  - heavier and slower;
  - hides whether the arm command path can be made repeatable.
- Pure gate-and-skip:
  - protects data quality;
  - does not recover from the reached/pregrasp post-command configuration.

Added tool:

```text
scripts/return_left_arm_to_reference.py
```

Safety/behavior:

```text
input: reference NPZ initial active-left joint positions
state source: /joint_states
command topic: /oberon7/arm_position_l/command
command type: trajectory_msgs/JointTrajectory
per-step clip: max_joint_delta, default 0.01 rad
stop condition: joint_l2_error <= 0.01 and joint_max_abs_error <= 0.005
gripper_commands_sent=false
hand_controller_started=false
training_started=false
learned_rollout_started=false
```

Verification:

```text
py_compile: PASS
--help: PASS
dry-run from post-command state: PASS, no command sent
```

Dry-run observation:

```text
commands_sent=0
gripper_commands_sent=false
reached=false
joint_l2_error=0.11564320348459194
joint_max_abs_error=0.08137583509102786
```

Interpretation:

- The post-command reached/pregrasp state is outside the reference initial
  joint envelope.
- A bounded return command is necessary before another same-envelope episode.
- The tool computes the first clipped recovery step without sending it in
  dry-run mode.

Next blocker-local runtime check if approved:

```text
Run return_left_arm_to_reference.py without --dry-run once, then rerun
check_b8_initial_state_gate.py. Only if both pass should another episode be
considered.
```

### B8' Return-To-Reference Live Smoke

Date: 2026-05-05.

Runtime result:

```text
tool: return_left_arm_to_reference
dry_run: false
commands_sent: 8
reached: true
gripper_commands_sent: false
final_joint_l2_error: 0.0010774700888416262
final_joint_max_abs_error: 0.0010726177090809585
```

Post-return target-aware initial-state gate:

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

- The active-left bounded return-to-reference reset step works in one live
  smoke cycle.
- The arm can be returned from the reached/pregrasp post-command state to the
  reference initial envelope without gripper command.
- The target-aware gate passes after return, so the immediate reset/settle
  blocker is smoke-level resolved.
- The broader B8' multi-episode blocker is not fully resolved until a short
  gated episode after return shows validator PASS, saved metadata consistency,
  target/base stability, and restored command-motion diagnostics.

Next minimum check:

```text
Run exactly one short gated arm-only verification episode after this
return-to-reference + gate pass, then run validator, target-aware gate, and
quality/direction/command-motion diagnostics. Do not expand collection and do
not train.
```

### B8' Return-Gated Episode Attempt With Wrong Overrides

Date: 2026-05-05.

Attempt:

```text
episode_id=b8_return_gated_arm_verify_1_0000
intended purpose: exactly one short arm-only episode after return-to-reference
actual saved path:
/home/benny/.ros/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/b8_return_gated_arm_verify_1/b8_return_gated_arm_verify_1_0000.npz
```

Result:

```text
validator: PASS
success: false
recorded_success_distance_m: 0.10891000445099207
recorded_success_distance_threshold_m: 0.1
allow_nominal_state_fallback: false
gripper_enabled: false
is_grasp_dataset: false
```

The file was saved under `/home/benny/.ros/...` because the launch command used
a relative `output_dir`. Use an absolute workspace path for the next attempt.

Why this does not validate the return-gated route:

```text
target_directed_reaching=false
state_sequence=['MOVE_TO_PREGRASP', 'MOVE_TO_GRASP', 'CLOSE_GRIPPER', 'LIFT_OR_HOLD']
max_linear_step=0.005
time_from_start_sec=3.0
```

This is not the same as the previous successful gated arm-only target-directed
verification setup. Runtime expert output:

```text
Scripted expert failed: unsupported operand type(s) for *: 'NoneType' and 'NoneType'
```

Offline quality:

```text
mean_initial_distance=0.10788122569941581
mean_final_distance=0.10891000445099207
mean_distance_reduction=-0.0010287787515762536
min_distance_overall=0.10458705289514927
mean_action_to_eef_motion_cosine=0.11290408272341595
mean_best_action_to_eef_cosine=0.2521221409884768
mean_best_realized_gain_along_action=0.045054442830130825
```

Interpretation:

- The reset/settle mechanism remains single-cycle smoke-level resolved.
- This failed episode is attributed to wrong launch overrides and the default
  non-target-directed/gripper-inclusive state sequence, not to proven reset
  failure.
- Do not collect more. First run return-to-reference and target-aware gate
  again, then run exactly one corrected target-directed arm-only episode.

### B8' Corrected Return-Gated Arm-Only Episode

Date: 2026-05-05.

Pre-episode reset/gate:

```text
return_left_arm_to_reference.py:
  reached=true
  commands_sent=1
  final_joint_l2_error=8.382996789634279e-05
  final_joint_max_abs_error=7.591381990490476e-05
  gripper_commands_sent=false

pre_corrected_return_episode_gate:
  passed=true
  initial_distance=0.11332110045439249
  joint_l2_drift=0.00010507141667035804
  relative_base_drift=0.00710979212566845
```

Episode:

```text
path=data/raw/b8_return_gated_arm_verify_2/b8_return_gated_arm_verify_2_0000.npz
validator=PASS
T=22
runtime expert success=True
saved success=True
success_source=recorded_final_distance
recorded_success_distance_m=0.08215466060136162
threshold=0.1
allow_nominal_state_fallback=false
gripper_enabled=false
is_grasp_dataset=false
```

Quality/command-motion:

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

Post-episode gate:

```text
passed=false
relative_base_drift_ok=false
initial_distance=0.08076170932878053
joint_l2_drift=0.08521686992588655
relative_base_drift=0.05839507151533
```

Interpretation:

- The corrected return->gate->episode cycle proves the reset/settle approach
  can recover from a post-command configuration and produce one successful
  non-fallback arm-only reaching/pre-grasp episode.
- The post-episode gate failure is expected and reinforces that no next episode
  may be recorded directly from the reached/pregrasp state.
- Command-motion remains weaker than the best previous smoke episode, so the
  broader B8' repeatability blocker is not fully resolved.
- Do not train and do not expand to 10+ episodes. The next minimum check should
  be another return-to-reference + target-aware gate from this post-episode
  state, followed by at most a tiny 2-cycle repeatability check if explicitly
  approved.

### B8' Post-Success Return Gate Failure

Date: 2026-05-05.

After `b8_return_gated_arm_verify_2_0000`, return-to-reference was run again:

```text
return_left_arm_to_reference.py
reached=true
commands_sent=5
final_joint_l2_error=0.00010091317246476995
final_joint_max_abs_error=7.563576529534544e-05
gripper_commands_sent=false
```

The follow-up target-aware gate failed:

```text
passed=false
initial_distance_ok=false
relative_base_drift_ok=false
initial_distance=0.12368795041111422
relative_base_drift=0.01695805312367644
target_base_drift=0.01691229565682799
joint_l2_drift=0.0006517102217792586
eef_base_drift=4.920892227205025e-05
```

Interpretation:

- Arm joint reset is not the failing part; joint and EEF gate metrics are well
  inside threshold.
- The remaining issue is target/base initial geometry drift after the runtime
  has been running through several command cycles.
- The target-relative drift is large enough to fail the initial gate and would
  make the next episode incomparable to the reference envelope.
- Do not run another arm episode until target/base stability is checked
  read-only or the target probe is reinitialized and passes the target-aware
  gate again.

### B8' Restarted Runtime Target Gate Settle

Date: 2026-05-05.

Runtime was restarted, including:

```text
uvms_control oberon7_position_control.launch
b5d_move_group_with_context.launch
load_left_controllers.launch start=true load_hand=false
world_base_tf_bridge.launch
b8_target_gate_probe.launch
```

Then three read-only target-aware gates were run 5 s apart:

```text
gate_0:
  passed=false
  initial_distance=0.11029615817327146
  relative_base_drift=0.02327702221543785
  target_base_drift=0.022187036192277323

gate_1:
  passed=false
  initial_distance=0.11029953375977956
  relative_base_drift=0.0232763337054756
  target_base_drift=0.02218640052215951

gate_2:
  passed=true
  initial_distance=0.10770297148110519
  relative_base_drift=5.5529932828080466e-06
  target_base_drift=0.0012237377600882425
```

Interpretation:

- The target/base geometry recovers after restart and settle; gate_2 is almost
  exactly back on the reference target-relative offset.
- The two initial failures show startup/settle transients in the target probe
  or base-relative target updater, not a durable arm reset failure.
- The next arm-only episode must be gated by a fresh passing target-aware
  check. Prefer two consecutive passes 5 s apart before allowing another
  episode.
- This remains B8' blocker work only. No training, no learned rollout, no
  gripper command, and no grasp claim.

### B8' Two-Pass Target Gate After Settle

Date: 2026-05-05.

Two additional read-only target-aware gates were run 5 s apart:

```text
gate_0:
  passed=true
  initial_distance=0.1076746834400219
  relative_base_drift=3.503815165242792e-05
  target_base_drift=0.001223737760115677

gate_1:
  passed=true
  initial_distance=0.10766337265266729
  relative_base_drift=4.5012944528958283e-05
  target_base_drift=0.001223737760115677
```

Interpretation:

- The target-aware gate is stable after settle.
- The prior two failing gates after restart are best explained as startup or
  target-probe settle transients.
- The target/base gate sub-blocker is now smoke-level resolved with a stricter
  two-pass read-only gate.
- The larger B8' repeatability blocker remains unresolved until another
  return-to-reference + gate + corrected arm-only episode cycle also passes
  validation and quality diagnostics.

### B8' Target-Directed Action-Frame Fix

Date: 2026-05-05.

Problem observed in `b8_return_gated_arm_verify_3`:

```text
pre-return: reached=true
pre-gate: passed=true
runtime failure: IK failed with MoveIt error code -31
validator=PASS
saved success=false
recorded_success_distance_m=0.10966874121994438
distance_reduction=-0.0021273869346622593
mean_best_action_to_eef_cosine=0.08695271743383595
mean_best_realized_gain_along_action=0.022552544812475088
```

Code diagnosis:

```text
ScriptedExpert._target_directed_action() produced base_link-frame target
deltas when target_directed_action_frame=base_link, but the arm converter was
constructed with arm_action_frame=planning_frame. This made the converter treat
base-frame deltas as planning-frame deltas.
```

Patch:

```text
file: src/rexrov_single_oberon7_fm_dp/expert_policy.py
change: converter_action_frame = target_directed_action_frame when
        target_directed_reaching=true, otherwise arm_action_frame
py_compile: PASS
```

Post-fix verification `b8_return_gated_arm_verify_4`:

```text
runtime log: action_frame=base_link
runtime expert success=True, distance 0.062727 below 0.1
validator=PASS
saved success=True
recorded_success_distance_m=0.05744791236250198
initial_distance=0.10753282417279568
min_distance=0.05743319455171586
final_distance=0.05744791236250198
distance_reduction=0.0500849118102937
mean_best_action_to_eef_cosine=0.3532763904220775
mean_best_lag_steps=0.0
mean_best_realized_gain_along_action=0.17090696757478616
allow_nominal_state_fallback=false
gripper_enabled=false
is_grasp_dataset=false
```

Post-fix reset/gate:

```text
return_to_reference_live_6 reached=true
commands_sent=4
final_joint_l2_error=0.00011415046805219868
gripper_commands_sent=false

post_postfix_return_gate passed=false
initial_distance=0.11655218918085192
relative_base_drift=0.009639652376657452

post_postfix_return_gate_retry passed=true
initial_distance=0.1075386326894244
relative_base_drift=0.0012386357816084035
```

Interpretation:

- The action-frame mismatch sub-blocker is fixed and smoke-validated.
- One post-fix return-gated arm-only episode succeeded without IK crash.
- Command-motion improved strongly relative to the pre-fix failed episode, but
  it is not yet enough evidence for larger collection or training.
- Target/base gate still needs settle/retry at episode boundaries.
- Do not expand to 10+ episodes and do not train. If continuing, run only a
  tiny post-fix repeatability check with return-to-reference and fresh
  target-aware gate before every episode.

### B8' Tiny Post-Fix Repeatability Check

Date: 2026-05-05.

Scope:

```text
2-cycle return->gate->episode->diagnostics check
data_dir=data/raw/b8_postfix_repeatability_2/
training=false
learned_rollout=false
gripper_command=false
```

Preconditions:

```text
cycle_0_return reached=true, commands_sent=0
cycle_0_pre_gate passed=true, relative_base_drift=0.006780562427391431
cycle_1_return reached=true, commands_sent=4
cycle_1_pre_gate passed=true, relative_base_drift=0.008245004755328939
```

Runtime:

```text
b8_postfix_repeatability_2_0000: runtime success=True, action_frame=base_link
b8_postfix_repeatability_2_0001: runtime success=True, action_frame=base_link
```

Strict summary:

```text
validator_pass_count=2
episodes_valid=2
success_count=2
reaching_success_rate=1.0
all_required_metadata_ok=true
all_success_metadata_consistent=true
mean_initial_distance=0.1075636214496572
mean_final_distance=0.057304824535672975
mean_distance_reduction=0.05025879691398423
min_distance_overall=0.053346384327736994
max_active_left_joint_delta=0.03859894310454148
max_target_step_base=0.007109516133871766
large_target_step_indices=[] for both episodes
mean_best_action_to_eef_cosine=0.5379418351868376
mean_best_lag_steps=0.0
mean_best_realized_gain_along_action=0.17491140517275186
```

Final reset/gate:

```text
final_return reached=true
final_gate passed=true
final_gate relative_base_drift=0.008009723575080853
```

Interpretation:

- The action-frame fix, return-to-reference, and target-aware gate together are
  repeatable at a tiny 2-cycle smoke level.
- The original 10-episode tail failure blocker is not fully solved at dataset
  scale, but the most likely implementation bug has been corrected and
  smoke-validated.
- Do not train or run learned rollout. The next appropriate B8' step, if
  explicitly approved, is a small post-fix debug batch plan with the same
  per-episode return/gate/diagnostic policy.

### B8' Small Post-Fix Debug Batch Plan

Date: 2026-05-05.

Decision:

```text
Plan a small post-fix debug batch, but do not execute it yet.
Default N=3 episodes.
Hard max N=5 episodes.
No training, no learned rollout, no gripper command, no grasp claim.
```

Why:

- The post-fix 2-cycle repeatability check passed.
- The earlier 10-episode batch failed in the tail, so jumping straight back to
  a 10+ episode run would hide whether the fix remains stable across a slightly
  longer sequence.
- A 3-episode batch is the next minimum scale beyond the 2-cycle smoke.

Per-episode policy:

```text
1. Run return_left_arm_to_reference.py.
2. Require reached=true and gripper_commands_sent=false.
3. Run check_b8_initial_state_gate.py.
4. If gate fails due to target/base settle, wait 5 s and retry once.
5. Only collect if the gate passes.
6. Collect one corrected target-directed arm-only episode.
7. Continue only if the episode does not crash and later diagnostics pass.
```

Collection settings must match the fixed route:

```text
execute_arm=true
execute_arm_once_per_state=false
state_sequence=MOVE_TO_PREGRASP,MOVE_TO_GRASP
execute_arm_states=MOVE_TO_PREGRASP,MOVE_TO_GRASP
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

Required summary checks:

```text
validate_episode.py for all episodes
summarize_b8_repeatability_smoke.py --required-base-state-source odom
  --fail-on-problem
analyze_b8_reaching_quality.py
analyze_b8_reaching_direction.py
analyze_b8_command_motion_path.py
final return_to_reference + target-aware gate
```

Pass criteria:

```text
validator_pass_count=N/N
success_count=N/N preferred
all_required_metadata_ok=true
all_success_metadata_consistent=true
allow_nominal_state_fallback=false for all
base_state_source=odom for all
target_state_source=gazebo_model_states for all
gripper_enabled=false for all
is_grasp_dataset=false for all
large_target_step_indices=[] for all
command-motion must not collapse toward the pre-fix failed values
```

Stop immediately if:

```text
return/gate fails after one retry
IK -31 or expert crash appears
validator fails
success metadata mismatch appears
target/base large jump appears
success_count drops below all-pass at N=3
command-motion collapses toward pre-fix failure values
```

### B8' Small Post-Fix Debug Batch Attempt Stopped By Gate

Date: 2026-05-05.

Attempt:

```text
planned data_dir=data/raw/b8_postfix_debug_3/
planned episodes=3
actual episodes_collected=0
stop condition=cycle 0 target-aware gate failed after one 5 s retry
```

Cycle 0 return:

```text
reached=true
commands_sent=0
final_joint_l2_error=0.00015090229670289678
final_joint_max_abs_error=0.0001343175473884628
gripper_commands_sent=false
```

Cycle 0 gate:

```text
passed=false
initial_distance=0.1159362425810477
initial_distance_ok=false
relative_base_drift=0.00872391480943356
relative_base_drift_ok=true
target_base_drift=0.008698731973559727
```

Cycle 0 gate retry after 5 s:

```text
passed=false
initial_distance=0.11528983854046555
initial_distance_ok=false
relative_base_drift=0.008109968028264436
relative_base_drift_ok=true
target_base_drift=0.008066761178696735
```

Interpretation:

- The per-episode gate prevented collection from a marginal target/EEF initial
  geometry.
- No new episode was recorded, so there is no new failed dataset item.
- Arm reset was not the blocker. The limiting factor is target-aware initial
  distance just above the configured `0.115 m` gate threshold.
- Do not continue the batch from this state. Next work should be read-only
  target/base settle diagnosis or explicit target probe reinitialization, then
  rerun the gate.

Current blocker status:

```text
Not fully resolved.
```

Evidence already resolved at smoke level:

```text
target-directed action-frame fix: validated by b8_return_gated_arm_verify_4
return-to-reference reset: repeated live checks reached=true
target/base settle: can pass after wait/retry
tiny post-fix repeatability: 2/2 validator PASS and 2/2 reaching success
```

Remaining missing evidence:

```text
The small post-fix debug batch has not started because the cycle 0
target-aware gate failed on initial_distance after one retry.
Need to determine whether this is:
  - transient target/base settle near the gate boundary;
  - target probe/base-relative updater offset;
  - base pose drift;
  - or a gate threshold that is too tight for current runtime variability.
```

Next minimum check:

```text
Read-only repeated target-aware gates only. Do not collect. Do not command arm.
Do not change the threshold until repeated gate evidence is reviewed.
```

### B8' Gate Boundary Probe

Date: 2026-05-05.

Read-only repeated gate probe:

```text
checks_total=5
pass_count=3
fail_count=2
episodes_collected=0
control_commands_sent=false for all
gripper_commands_sent=false for all
```

Results:

```text
gate_0 passed=true
initial_distance=0.11326617951540467
relative_base_drift=0.006954684079328241
target_base_drift=0.0069650802824294915

gate_1 passed=true
initial_distance=0.11374995074828124
relative_base_drift=0.007563652990111229
target_base_drift=0.007574522009981456

gate_2 passed=false
initial_distance=0.11564356703916857
relative_base_drift=0.008480493184240828
target_base_drift=0.008459386395596714

gate_3 passed=true
initial_distance=0.10753170023825985
relative_base_drift=0.0012413657006039953
target_base_drift=0.0012237377601163773

gate_4 passed=false
initial_distance=0.11502167746808681
relative_base_drift=0.007817255991339152
target_base_drift=0.00783235310664415
```

Interpretation:

- The gate boundary problem is intermittent.
- The failing checks are not due to arm joint reset or EEF drift.
- All observed `relative_base_drift` values are below the `0.01 m` threshold,
  but the `initial_distance` sometimes exceeds `0.115 m` by a small amount.
- The target position appears to switch between a near-reference mode and a
  shifted mode. The shifted mode is still within relative drift threshold, but
  can fail the stricter initial distance gate.
- Do not relax the gate yet. First inspect target probe/updater behavior
  read-only.

Next minimum check:

```text
Read-only ROS graph/topic check for target updater/probe behavior. Look for
multiple target/base updater nodes, duplicate target spawners, or target pose
toggling in /gazebo/model_states. Do not collect and do not command the arm.
```

### B8' ROS Graph Target-Updater Spot Check

Date: 2026-05-05.

Command:

```text
rosnode list | grep -E "target|base_relative|gate|spawn|dp_fm"
```

Observed:

```text
/b8_target_gate_base_relative_target
/dp_fm_left_arm_controller_starter
/dp_fm_odom_tf_bridge
```

Interpretation:

- No duplicate target/base updater was observed in the filtered ROS graph.
- The target gate probe appears to have one active base-relative target updater.
- This does not yet resolve the blocker because target indexed pose stability
  was not actually measured.

The attempted raw topic grep:

```text
rostopic echo -n 10 /gazebo/model_states | grep -A 8 -B 2 "cylinder_target_gate_probe"
```

is ambiguous because `/gazebo/model_states` uses parallel arrays:

```text
name[i] corresponds to pose[i]
```

The displayed `pose.position.x: 0.0` block is likely the first model's pose
block (`ocean_box`), not the indexed pose of `cylinder_target_gate_probe`.

Next minimum check:

```text
Read `/gazebo/model_states` by index and print only
pose[name.index("cylinder_target_gate_probe")].
```

### B8' Indexed Target Pose Probe

Date: 2026-05-05.

Read-only indexed `/gazebo/model_states` check:

```text
target_model_name: cylinder_target_gate_probe
samples: 10
pose lookup: pose[name.index("cylinder_target_gate_probe")]
```

Observed target world pose:

```text
i=0  x=24.7291204633037  y=-13.440451519135685  z=-99.71307050685847
i=1  x=24.84313452156804 y=-13.427533233803874  z=-99.71295896025687
i=2  x=24.958963473604427 y=-13.413235008370519 z=-99.71207734581594
i=3  x=25.075882160834045 y=-13.39839771663587  z=-99.71352174893009
i=4  x=25.196237450763203 y=-13.381992047388469 z=-99.71327027605352
i=5  x=25.31099992144687  y=-13.365326016564923 z=-99.71293976803561
i=6  x=25.42527619326163  y=-13.348076933754998 z=-99.71245273323048
i=7  x=25.537864640964763 y=-13.329733043610993 z=-99.71301376480756
i=8  x=25.648039177943016 y=-13.310821579179837 z=-99.71194187810143
i=9  x=25.7584837884664   y=-13.290649770155733 z=-99.71303967275239
orientation=[0, 0, 0, 1] for all samples
```

Follow-up target-aware gate:

```text
passed=true
initial_distance=0.10771781639816572
relative_base_drift=1.5569323561687856e-05
target_base_drift=8.595952887736536e-05
eef_base_drift=0.00010009142460273303
joint_l2_drift=0.00012836553017450003
control_commands_sent=false
gripper_commands_sent=false
```

Interpretation:

- The target pose is not fixed in world. It is moving by about `1.03 m` in x
  and `0.15 m` in y across the 10 samples, consistent with a base-relative
  target following the drifting RexROV.
- The follow-up gate confirms that the target-in-base geometry can be clean:
  `relative_base_drift` and `target_base_drift` were near zero and
  `initial_distance` matched the reference geometry.
- The current blocker is still not fully resolved because earlier repeated
  gate checks intermittently failed near `initial_distance_max=0.115 m`.
- The remaining missing evidence is whether target world motion tracks RexROV
  base world motion one-to-one during the boundary failures. The next minimum
  check should print indexed `rexrov` and `cylinder_target_gate_probe` poses
  together and compute target-in-base displacement without commanding the arm.

### B8' Indexed Base+Target Relative-Motion Probe

Date: 2026-05-05.

Read-only indexed `/gazebo/model_states` check:

```text
base_model_name: rexrov
target_model_name: cylinder_target_gate_probe
samples: 20
pose lookup:
  base = pose[name.index("rexrov")]
  target = pose[name.index("cylinder_target_gate_probe")]
computed:
  target_in_base = R_base_world.T * (target_world - base_world)
```

Summary:

```text
target_in_base_mean:
  [2.1643409987668636, 0.4999520343001693, -1.2753631745317109]
target_in_base_min:
  [2.160763731941731, 0.49970602555314947, -1.2764671785475143]
target_in_base_max:
  [2.1675555936413455, 0.5001850139236826, -1.2739863699616563]
target_in_base_range:
  [0.006791861699614543, 0.0004789883705331732, 0.0024808085858580853]
target_in_base_range_norm:
  0.007246601027065321
```

Interpretation:

- The target follows the base closely enough for the current gate:
  `target_in_base_range_norm=0.00725 m`, below the `0.01 m`
  relative-drift threshold.
- No evidence was found for duplicate target updater fighting, target pose
  gross jumps, or base/target desynchronization large enough to explain the
  B8' debug-batch failure.
- The target pose in base frame is around
  `[2.164, 0.500, -1.275]` because the target is near the EEF, and the EEF is
  offset from `rexrov/base_link`; it should not be expected to equal the
  target-to-EEF vector `[0.1, 0.0, 0.04]`.
- The remaining gate-boundary issue is most likely policy/threshold
  tightness: `initial_distance_max=0.115 m` is only about `7.3 mm` above the
  nominal reference distance `0.1077 m`, comparable to the observed
  target-in-base range.

Current blocker assessment:

```text
target/base sync blocker: smoke-level resolved
batch-start blocker: not fully resolved because gate policy still needs a
deliberate decision before retrying the small post-fix debug batch
```

Recommended next step:

```text
No more read-only target/base checks are needed immediately.
Choose the gate policy before any new episode:
  option A: keep initial_distance_max=0.115 m and wait/retry until one or two
            fresh gates pass;
  option B: widen only initial_distance_max slightly, e.g. to 0.120 m, while
            keeping relative_base_drift_threshold=0.01 m and all non-fallback,
            gripper-disabled constraints.
Do not train and do not expand collection.
```

### B8' Conservative Gate Policy Helper

Date: 2026-05-05.

Implemented option A as a package-local execution helper:

```text
scripts/run_b8_postfix_debug_batch_conservative.py
```

Purpose:

```text
For a tiny post-fix debug batch, enforce:
  return -> wait/retry target-aware gate -> collect one arm-only episode ->
  validate -> continue only if all checks pass.
```

Key behavior:

```text
initial_distance_max is fixed at 0.115 m by default.
The script rejects any non-0.115 override for --initial-distance-max.
Default gate attempts: 6.
Default wait between gate attempts: 5 s.
Default episode count: 3, hard-limited to 1-5.
Any return/gate/collect/validation failure stops the batch.
Existing episode files are refused unless --allow-existing is explicitly set.
```

Safety constraints:

```text
allow_nominal_state_fallback=false
execute_arm=true
target_directed_reaching=true
target_directed_action_frame=base_link
state_sequence=MOVE_TO_PREGRASP,MOVE_TO_GRASP
execute_arm_states=MOVE_TO_PREGRASP,MOVE_TO_GRASP
enable_gripper_command=false
gripper_enabled=false
is_grasp_dataset=false
task_type=arm_only_reaching
success_metric=reaching_success
spawn_target=false
enable_base_relative_target=false
```

Verification:

```text
chmod +x scripts/run_b8_postfix_debug_batch_conservative.py
python3 -m py_compile scripts/run_b8_postfix_debug_batch_conservative.py: PASS
scripts/run_b8_postfix_debug_batch_conservative.py --help: PASS
```

Files changed:

```text
scripts/run_b8_postfix_debug_batch_conservative.py
CMakeLists.txt
```

No collection, training, learned rollout, gripper command, or hand controller
startup was run during implementation.

### B8' Conservative Batch Attempt With Scheme 1

Date: 2026-05-05.

Command:

```text
rosrun rexrov_single_oberon7_fm_dp run_b8_postfix_debug_batch_conservative.py --episode-count 3
```

Result:

```text
status=stopped
episodes_completed=0
stop_reason=fresh gate did not pass for b8_postfix_debug_3_0000
manifest=outputs/logs/b8_postfix_debug_3_conservative/conservative_batch_manifest.json
```

Return step:

```text
reached=true
commands_sent=0
final joint_l2_error=0.00010753423427348858
final joint_max_abs_error=9.103467156545975e-05
gripper_commands_sent=false
```

Gate attempts:

```text
attempts=6
gate_wait_sec=5.0
initial_distance_max=0.115
relative_base_drift_threshold=0.01

initial_distance values stayed inside threshold:
  approximately 0.11029-0.11040 m

relative_base_drift values stayed outside threshold:
  approximately 0.02326-0.02328 m

target_base_drift values:
  approximately 0.02327-0.02329 m
```

Interpretation:

- Scheme 1 behaved as intended: no episode was collected because the fresh
  gate never passed.
- The remaining blocker is not active-left reset and not initial-distance
  boundary. It is a stable target/base reference offset of about `2.33 cm`
  relative to `b8_reaching_debug_10_0000`.
- Because the offset persisted over all six retries, waiting alone is
  insufficient for the current runtime.
- Do not retry collection from this target probe state. Do not train.

Next minimum action:

```text
Stop and restart only b8_target_gate_probe.launch, then run two fresh
target-aware gates 5 s apart. If both pass, rerun the conservative helper.
If they fail with the same ~0.023 m relative_base_drift, the target probe
spawn/updater reference must be reinitialized more explicitly before any
batch collection.
```

### B8' Target Probe Restart Still Fails Gate

Date: 2026-05-05.

User restarted:

```text
roslaunch rexrov_single_oberon7_fm_dp b8_target_gate_probe.launch
```

Launch result:

```text
spawn_b8_target_gate_probe:
  SpawnModel: Failure - entity already exists.
b8_target_gate_base_relative_target:
  started
```

Two fresh gates after restart:

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

- The blocker is not solved.
- Restarting the launch does not reset the target if the model already exists.
- The target updater runs, but the stale existing target remains about `2.3 cm`
  away from the reference target/base geometry used by the gate.
- No episode was collected and no gripper command was sent.

Minimum code change:

```text
Added scripts/reset_b8_target_gate_probe.py
Updated CMakeLists.txt to install it.
```

Behavior:

```text
Calls Gazebo /gazebo/delete_model only for cylinder_target_gate_probe.
Checks the model becomes absent from /gazebo/model_states.
Records control_commands_sent=false and gripper_commands_sent=false.
Does not spawn, record, command arm, command gripper, or train.
```

Verification:

```text
python3 -m py_compile scripts/reset_b8_target_gate_probe.py: PASS
source devel/setup.bash; scripts/reset_b8_target_gate_probe.py --help: PASS
```

Next command sequence:

```text
1. Stop b8_target_gate_probe.launch.
2. Run reset_b8_target_gate_probe.py.
3. Restart b8_target_gate_probe.launch.
4. Run two fresh target-aware gates 5 s apart.
5. Retry conservative helper only if both gates pass.
```

### B8' Target Reset And Fresh Gate Pass

Date: 2026-05-05.

Reset result:

```text
tool=reset_b8_target_gate_probe
passed=true
before_present_in_model_states=true
get_model_state_success=true
delete_attempted=true
delete_success=true
delete_status="DeleteModel: successfully deleted model"
absent_after_delete=true
control_commands_sent=false
gripper_commands_sent=false
```

Clean relaunch:

```text
roslaunch rexrov_single_oberon7_fm_dp b8_target_gate_probe.launch
spawn_b8_target_gate_probe:
  SpawnModel: Successfully spawned entity
b8_target_gate_base_relative_target:
  initialized target_base_xyz=[2.1598220509962056, 0.500061142548624, -1.2763767663921255]
```

Two fresh target-aware gates:

```text
gate_0:
  passed=true
  initial_distance=0.10479344544370915
  relative_base_drift=0.003596792375915908
  target_base_drift=0.0034034423602981
  control_commands_sent=false
  gripper_commands_sent=false

gate_1:
  passed=true
  initial_distance=0.1096170277494551
  relative_base_drift=0.0021184551807263505
  target_base_drift=0.0027022208599847518
  control_commands_sent=false
  gripper_commands_sent=false
```

Interpretation:

- The stale/existing target probe blocker is smoke-level resolved.
- Clean delete + respawn is required; restarting the launch alone is
  insufficient when Gazebo already has the model.
- Both fresh gates pass under the strict scheme-1 thresholds:
  `initial_distance_max=0.115 m` and
  `relative_base_drift_threshold=0.01 m`.
- No data was collected and no gripper command was sent in this check.

Next minimum step:

```text
Rerun the conservative helper for the small post-fix debug batch. It should
still stop on the first return/gate/collect/validation problem.
```

### B8' Conservative Post-Fix Debug Batch Result

Date: 2026-05-05.

Command:

```text
rosrun rexrov_single_oberon7_fm_dp run_b8_postfix_debug_batch_conservative.py --episode-count 3
```

Helper terminal result:

```text
STOP: summary failed
manifest:
  outputs/logs/b8_postfix_debug_3_conservative/conservative_batch_manifest.json
```

Manifest interpretation:

```text
episodes_completed=3
return passed for all episodes
gate passed for all episodes
collect returncode=0 for all episodes
validate returncode=0 for all episodes
summary returncode=3
```

The summary failure was not a data-quality failure. It was caused by:

```text
[rosrun] Couldn't find executable named summarize_b8_repeatability_smoke.py
...
Found the following, but they're either not files, or not executable:
  scripts/summarize_b8_repeatability_smoke.py
```

Fix:

```text
Added scripts/summarize_b8_repeatability_smoke.py to CMakeLists.txt
Confirmed executable bit via stat.
Reran summary manually without recollecting data.
```

Manual summary rerun:

```text
rosrun rexrov_single_oberon7_fm_dp summarize_b8_repeatability_smoke.py \
  --input-dir data/raw/b8_postfix_debug_3 \
  --pattern 'b8_postfix_debug_3_*.npz' \
  --output-dir outputs/logs/b8_postfix_debug_3_summary \
  --required-base-state-source odom \
  --fail-on-problem
```

Summary result:

```text
episodes_total=3
episodes_valid=3
validator_pass_count=3
success_count=3
reaching_success_rate=1.0
all_required_metadata_ok=true
all_success_metadata_consistent=true
initial_distance_per_episode=[0.10756171217710446, 0.11280464422849693, 0.11374001401115195]
final_distance_per_episode=[0.04954892757671833, 0.04937153823147446, 0.050071126547465185]
distance_reduction_per_episode=[0.05801278460038613, 0.06343310599702247, 0.06366888746368676]
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

Assessment:

```text
B8' conservative post-fix 3-episode debug batch is smoke-level resolved.
This is not training, not learned rollout, and not grasp success.
Do not expand automatically. Next step should be an explicit decision between
one more small 3-5 episode confirmation or a controlled 10-episode post-fix
debug batch with the same reset/gate policy.
```

### B8' Controlled 10-Episode Post-Fix Batch Preparation

Date: 2026-05-05.

User requested:

```text
一个受控 10-episode post-fix debug batch，继续保持 reset/gate/validate 策略
```

Implementation update:

```text
scripts/run_b8_postfix_debug_batch_conservative.py
  episode-count hard limit changed from 5 to 10
  safety policy unchanged
  per-step timeouts added
```

Timeouts:

```text
return-timeout-sec=90
gate-timeout-sec=30
collect-timeout-sec=90
validate-timeout-sec=30
summary-timeout-sec=60
```

Attempted command:

```text
rosrun rexrov_single_oberon7_fm_dp run_b8_postfix_debug_batch_conservative.py \
  --episode-count 10 \
  --episode-prefix b8_postfix_debug_10 \
  --output-dir data/raw/b8_postfix_debug_10 \
  --log-dir outputs/logs/b8_postfix_debug_10_conservative \
  --summary-output-dir outputs/logs/b8_postfix_debug_10_summary
```

Result:

```text
status=stopped before collection
episodes_written=0
manifest=outputs/logs/b8_postfix_debug_10_conservative/conservative_batch_manifest.json
reason=ROS master/runtime unavailable; helper was interrupted while waiting in
       the first return step
```

Read-only ROS check after interruption:

```text
rostopic info /oberon7/arm_position_l/command: Unable to communicate with master
rostopic info /joint_states: Unable to communicate with master
```

Interpretation:

- No 10-episode data was collected.
- This is not a reaching failure, not a validator failure, and not a data
  quality failure.
- The runtime must be restarted before retrying.
- The helper is now hardened so future runtime loss should stop by timeout
  instead of hanging indefinitely.

### B8' Controlled 10-Episode Retry Precheck Fails

Date: 2026-05-06.

Runtime was restarted and two pre-batch target-aware gates were run:

```text
gate_0:
  passed=false
  initial_distance=0.11033622160686253
  initial_distance_ok=true
  relative_base_drift=0.0232793818376196
  relative_base_drift_ok=false
  target_base_drift=0.023300825981187705

gate_1:
  passed=false
  initial_distance=0.11041099785110788
  initial_distance_ok=true
  relative_base_drift=0.02325376923014353
  relative_base_drift_ok=false
  target_base_drift=0.023275458190915907
```

Interpretation:

- Current blocker is not solved for the 10-episode batch.
- The precondition gate failed for the same stale/offset target-probe reason:
  target/base-relative geometry is about `2.3 cm` from the reference.
- This is not an arm reset problem and not an initial-distance problem.
- No collection should proceed from this target state.

The 10-episode helper was then run and stopped immediately:

```text
STOP: episode already exists:
  data/raw/b8_postfix_debug_10/b8_postfix_debug_10_0000.npz
```

Existing files in the target directory:

```text
b8_postfix_debug_10_0000.npz: validator PASS, T=22, success=True
b8_postfix_debug_10_0001.npz: validator PASS, T=22, success=True
b8_postfix_debug_10_0002.npz: validator PASS, T=6,  success=True
```

Decision:

```text
Treat data/raw/b8_postfix_debug_10 as partial/contaminated. Do not use it as
the clean 10-episode debug batch and do not delete it automatically.
```

Next minimum action:

```text
1. Stop b8_target_gate_probe.launch.
2. Run reset_b8_target_gate_probe.py --ignore-missing.
3. Restart b8_target_gate_probe.launch.
4. Run two fresh target-aware gates.
5. If both pass, run the helper with a clean output/prefix, e.g.
   b8_postfix_debug_10_clean.
```

### B8' Clean Controlled 10-Episode Post-Fix Debug Batch Passes

Date: 2026-05-06.

After deleting/respawning `cylinder_target_gate_probe`, two fresh target-aware
gates passed before collection:

```text
gate_2:
  passed=true
  initial_distance=0.11275964751174658
  relative_base_drift=0.005776400519545737
  target_base_drift=0.005732252450675206

gate_3:
  passed=true
  initial_distance=0.1099109092621023
  relative_base_drift=0.0028252985404082476
  target_base_drift=0.002810133672367156
```

Then the conservative helper completed a clean 10-episode batch:

```text
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
mean_final_distance=0.05024581695716414
mean_distance_reduction=0.05853092374442983
max_target_step_base=0.009844175150497677
large_target_step_indices=[] for all episodes
mean_best_action_to_eef_cosine=0.6498955385760039
mean_best_lag_steps=0.1
mean_best_realized_gain_along_action=0.21301870762024094
failure_reason=none for all episodes
```

Decision:

```text
B8' post-fix reaching-quality blocker is smoke-level resolved for a clean
controlled 10-episode scripted arm-only debug batch.
```

Limits:

```text
This is not learned-policy rollout, not grasping, not a final training dataset,
and not permission to claim grasp success. Keep gripper disabled and keep the
return/gate/validate strategy for any next debug collection.
```

Offline fix-effect comparison artifact:

```text
outputs/logs/b8_postfix_debug_10_clean_comparison/fix_effect_comparison.md
outputs/logs/b8_postfix_debug_10_clean_comparison/fix_effect_comparison.json
```

Key comparison against the failed `b8_reaching_debug_10` batch:

```text
success_count: 7/10 -> 10/10
reaching_success_rate: 0.7 -> 1.0
mean_final_distance: 0.08288684626534658 -> 0.05024581695716414
mean_distance_reduction: 0.02578654461012293 -> 0.05853092374442983
mean_best_action_to_eef_cosine: 0.5547614407437549 -> 0.6498955385760039
mean_best_lag_steps: 2.6 -> 0.1
mean_best_realized_gain_along_action: 0.13983358394761614 -> 0.21301870762024094
max_target_step_base: 0.02330097538679025 -> 0.009844175150497677
```

### B8' Next Direction Approved: Larger Controlled Debug Collection Planning

Date: 2026-05-06.

User approved entering a larger controlled debug collection or training dataset
planning.

Decision:

```text
Current blocker remains only smoke-level resolved.
Do not train yet.
Do not run learned-policy rollout.
Do not touch gripper or hand controller.
Proceed first with a controlled 20-episode arm-only debug collection plan.
```

Planning artifact:

```text
outputs/logs/b8_training_dataset_planning/b8_controlled_collection_plan.md
```

Next target if runtime is clean:

```text
data/raw/b8_controlled_debug_20/
outputs/logs/b8_controlled_debug_20_conservative/
outputs/logs/b8_controlled_debug_20_summary/
```

Stop conditions remain strict:

```text
stop on first return/gate/collection/validation/summary failure
skip training if validator_pass_count is not N/N
skip training if success_count/N drops below 0.8
continue debug if command-motion alignment collapses
```

### B8' Conservative Runner Episode Limit Updated

Date: 2026-05-06.

The first attempt to run the approved 20-episode controlled collection failed
before any collection because the conservative runner still enforced the older
debug-batch limit:

```text
ValueError: --episode-count must be in [1, 10] for this conservative debug runner
```

Patch:

```text
scripts/run_b8_postfix_debug_batch_conservative.py
  added MAX_EPISODE_COUNT = 20
  changed episode-count validation to [1, 20]
```

Verification:

```text
python3 -m py_compile scripts/run_b8_postfix_debug_batch_conservative.py: PASS
python3 scripts/run_b8_postfix_debug_batch_conservative.py --help: PASS
```

No data was collected by the failed attempt. No training, learned rollout, or
gripper command was run.

### B8' Controlled 20-Episode Attempt Stops At Fresh Gate

Date: 2026-05-06.

The approved 20-episode command was rerun after two manual pre-gates passed.
The conservative helper stopped before collecting episode 0000:

```text
STOP: fresh gate did not pass for b8_controlled_debug_20_0000
manifest:
  outputs/logs/b8_controlled_debug_20_conservative/conservative_batch_manifest.json
episodes_completed=0
```

Manual pre-gate context:

```text
gate_2 passed=true
  eef_base_drift=0.06542156925976753
  joint_l2_drift=0.08222160827670166
  relative_base_drift=0.005562236799568654
  target_base_drift=0.060531411709373956

gate_3 passed=true
  eef_base_drift=0.06538516538398671
  joint_l2_drift=0.08222007645958142
  relative_base_drift=0.004482665836028303
  target_base_drift=0.06251221385438185
```

Helper return result:

```text
return_left_arm_to_reference:
  reached=true
  commands_sent=5
  final joint_l2_error=0.0008240220815145631
  final joint_max_abs_error=0.0008193521437780404
  gripper_commands_sent=false
```

Helper fresh-gate result:

```text
gate attempts: 6
passed: 0/6
initial_distance: about 0.174-0.180 m
relative_base_drift: about 0.067-0.073 m
target_base_drift: about 0.067-0.073 m
```

Decision:

```text
Do not collect 20 episodes yet. The current unresolved blocker is target
freshness/geometry after returning the arm to reference. The helper correctly
prevented collection from a bad post-return target state.
```

Follow-up read-only runtime check:

```text
rosnode list | grep -E "b8_target_gate_base_relative_target|base_relative|spawn_b8_target_gate_probe"
  /b8_target_gate_base_relative_target

rosnode info /b8_target_gate_base_relative_target:
  subscriptions include /gazebo/model_states, /rexrov/pose_gt, /tf, /tf_static
```

Conclusion:

```text
There is a single target updater and it is connected to the expected state
topics. Duplicate target updater is not the cause.
```

Code diagnosis:

```text
BaseRelativeTargetUpdater.initialize() sets target_base_xyz from the current
EEF pose once at node startup. update_once() then keeps that fixed base-frame
target. Therefore the target probe must be started/reinitialized only after
the arm has returned to reference.
```

Patch:

```text
scripts/check_b8_initial_state_gate.py
  joint_l2_threshold default: 0.65 -> 0.02
  joint_max_abs_threshold default: 0.50 -> 0.01
  eef_base_drift_threshold default: 0.33 -> 0.02
```

This prevents a manual gate from passing while the arm is still in a
post-command reached pose.

### B8' Controlled 20-Episode Debug Collection Passes

Date: 2026-05-06.

After the tightened gate defaults and target-probe reinitialization order, two
fresh precollection gates passed and the conservative helper completed:

```text
status=completed
episode_count_requested=20
episodes_completed=20
stop_reason=""
manifest:
  outputs/logs/b8_controlled_debug_20_conservative/conservative_batch_manifest.json
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

```text
B8' target freshness / return-to-reference blocker is resolved at the
controlled 20-episode scripted arm-only debug collection level.
```

Limits:

```text
This is not learned-policy rollout, not training, not grasping, and not
grasp-success evidence. Keep gripper disabled.
```

Quality notes:

```text
weak but successful episodes:
  b8_controlled_debug_20_0010 final_distance=0.06764477900695165
  b8_controlled_debug_20_0017 final_distance=0.07005001495598358
boundary initial-distance episode:
  b8_controlled_debug_20_0010 initial_distance=0.11527553514048791
```

### B8' Read-Only Training-Dataset Candidate Manifest

Date: 2026-05-06.

Generated read-only planning artifacts:

```text
outputs/logs/b8_training_dataset_candidate_manifest/candidate_manifest.md
outputs/logs/b8_training_dataset_candidate_manifest/candidate_manifest.json
outputs/logs/b8_training_dataset_candidate_manifest/candidate_episodes.csv
```

Primary candidate pool:

```text
sources:
  b8_postfix_debug_10_clean
  b8_controlled_debug_20
episode_count=30
validator_pass_count=30/30
success_count=30/30
all metadata/source checks=true
mean_final_distance=0.05003238637536062
mean_distance_reduction=0.05960007870215763
max_target_step_base=0.009847087316117917
mean_best_action_to_eef_cosine=0.6328925916111913
mean_best_lag_steps=0.2
mean_best_realized_gain_along_action=0.21062497700834037
```

Flagged primary episodes:

```text
b8_controlled_debug_20_0010:
  initial_distance_boundary_gt_0.115
  weak_final_distance_ge_0.065
  low_realized_gain_lt_0.16
b8_controlled_debug_20_0014:
  low_action_eef_cosine_lt_0.50
b8_controlled_debug_20_0017:
  weak_final_distance_ge_0.065
  low_realized_gain_lt_0.16
```

Decision:

```text
Candidate manifest is ready for training-planning review only. No training has
started and no learned rollout or gripper command was run.
```

### BC H8 XYZ Live Dry-Run Action-Label Attempt

Date: 2026-05-06.

Precheck:

```text
gate_0 passed=true
gate_1 passed=true
target_model_name=cylinder_target_gate_probe
control_commands_sent=false
gripper_commands_sent=false
```

Gate metrics:

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

Dry-run result:

```text
tool=b8_bc_h8_xyz_rollout_dry_run_node
status=aborted
abort_reason=raw_xyz_component_abort
samples=0
dry_run_only=true
control_commands_sent=false
gripper_commands_sent=false
hand_controller_started=false
```

Judgment:

The gate side passed, but the BC h8 xyz dry-run action-label check did not
pass. The policy hit the hard raw xyz component abort before any publishable
label was recorded. This is a safe failure: no arm command, no gripper command,
no learned rollout execution, and no grasp claim.

Follow-up:

The dry-run adapter now writes `abort_context` into its JSON summary, including
raw xyz values for `raw_xyz_component_abort`. Rerun only the dry-run label check
with `execute_actions=false` and inspect the updated JSON before changing any
safety threshold or considering live execution.

### BC H8 XYZ Dry-Run Abort Context

Date: 2026-05-06.

Updated dry-run JSON:

```text
status=aborted
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

Decision:

```text
BC h8 xyz dry-run action-label blocker is not resolved.
```

The safety gate worked correctly: no command was sent and no label was
published. The failure is now actionable because the raw policy output is
known: `dx` is about `9.6 cm`, exceeding the `3 cm` hard abort threshold.

Next minimum check:

Run a read-only/offline comparison between the live dry-run raw xyz / live
observation scale and the B8 primary30 training distribution before changing
thresholds, running more dry-runs, or considering any live learned execution.

### BC H8 XYZ Dry-Run Action Distribution Diagnostic

Date: 2026-05-06.

Read-only comparison result:

```text
dry_raw_xyz=[0.09588255733251572, 0.00029814825393259525, 0.010294424369931221]
train_xyz_abs_max=[0.01, 0.001722396053442099, 0.01]
train_xyz_p95_abs=[0.01, 0.0012805263113561116, 0.01]
train_xyz_p99_abs=[0.01, 0.001722396053442099, 0.01]
train_xyz_mean=[0.009848484848484705, 0.00009620598359071179, 0.009686892926596432]
train_xyz_std=[0.0012215542042876574, 0.0006196520780459629, 0.0012921835415458805]
dry_raw_zscore_vs_action_dist=[70.42943152889856, 0.3258909613747649, 0.47015514611532966]
```

Decision:

```text
BC h8 xyz live dry-run blocker remains unresolved.
```

The safety abort is justified. The `dx` output is about `9.6x` the maximum
absolute `dx` present in the B8 primary30 training actions. This is not a case
where clipping alone should be trusted for live execution.

Next minimum check:

Run a read-only live-observation / normalized-policy-output diagnostic for the
same BC h8 xyz adapter. The goal is to determine whether the first live
observation is out-of-distribution or whether the BC head is extrapolating to a
bad normalized action despite an in-distribution observation.

### BC H8 XYZ Live Observation OOD Diagnostic

Date: 2026-05-06.

Read-only live probe:

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

Top live observation z-scores:

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

Decision:

```text
BC h8 xyz live dry-run blocker remains unresolved.
```

The current evidence points to observation distribution shift. The largest
offending features are gripper-state slots and absolute world `base_pose` /
`target_pose` coordinates. This is consistent with the policy being trained on
short, bounded real debug episodes while the live runtime can drift in absolute
world coordinates. Relative target-base gating can still pass in this state,
but the absolute observation given to BC is out-of-distribution.

Next minimum check:

Run a read-only normalized-observation ablation: evaluate the same BC checkpoint
on the same live observation while neutralizing gripper-state, absolute
base-pose, and absolute target-pose groups in normalized space. This determines
which OOD group drives the unsafe `dx` before any code-path or training
decision.

### BC H8 XYZ Normalized-Observation Ablation

Date: 2026-05-06.

Read-only ablation results:

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

Decision:

```text
BC h8 xyz live dry-run blocker remains unresolved.
```

The dominant driver is absolute `target_pose` OOD. Zeroing the normalized
target-pose group brings the first raw action back to the training-scale
envelope. Gripper neutralization also helps, but is not sufficient as a robust
solution. Base-pose neutralization alone worsens the result.

Implication:

Do not relax the abort threshold and do not execute learned arm commands. The
current observation design is not robust to drifting absolute world target
coordinates. The next safe step is an offline/readonly val-set ablation of the
same neutralization cases before considering any new adapter config or
base-relative observation retraining.

### BC H8 XYZ Validation Neutralization Ablation

Date: 2026-05-06.

Read-only validation-set result:

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

Checkpoint normalization:

```text
action_mean=[0.0100001972168684, 0.00011238727165618911, 0.009779215790331364]
action_std=[1.0, 0.0006739544332958758, 0.0005034060450270772]
```

Decision:

```text
BC h8 xyz live dry-run blocker remains unresolved.
BC h8 xyz is not rollout-planning safe.
```

The ablation confirms that inference-time zeroing is not sufficient: first-step
raw predictions remain about `0.1 m` at p95 across validation windows. The
underlying normalization is also unsuitable for rollout safety because `dx`
uses `action_std=1.0` despite a real command range around `0.01 m`, so small
normalized errors can become large raw `dx` commands.

Implication:

Do not run learned rollout, do not relax dry-run abort thresholds, and do not
advance DP/FM. The next blocker-local work is to design an offline-only
base-relative / arm-only observation and safe action normalization variant, then
re-evaluate before any live dry-run or rollout planning.

### Base-Relative Arm-Only BC Safe-Norm Sanity

Date: 2026-05-06.

Implemented offline-only dataset/training support:

```text
derived observation keys:
  eef_position_base_frame
  target_position_base_frame
  target_to_eef_base_frame

safe normalization config:
  action_std_epsilon=1e-6
  action_std_fallback=0.001
```

New BC config:

```text
config/train_bc_b8_primary30_h8_xyz_base_relative_safe_norm.yaml
```

Observation design:

```text
included:
  active_joint_positions
  active_joint_velocities
  eef_position_base_frame
  target_position_base_frame
  target_to_eef_base_frame
  episode_progress
  episode_remaining
removed:
  absolute world base_pose
  absolute world target_pose
  gripper_state
```

Dataset check:

```text
train_samples=456
val_samples=114
obs_dim=23
action_dim=3
action_std=[0.0010000000474974513, 0.0006739544332958758, 0.0005034060450270772]
```

BC sanity result:

```text
best_val_loss=0.9591013831837524
final_train_loss=0.13797813154236283
final_val_loss=1.4230697549959666
val_action_mse=3.0668218187202e-07
train_action_mse=1.9021148034426005e-07
```

Action-scale check:

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
live_rollout_ready=false
learned_rollout_has_run=false
gripper_commands_sent=false
dp_fm_training_started=false
```

The offline action-scale blocker is resolved for this new BC variant: outputs
stay around `0.01 m`, not `0.1 m`. This is not rollout success. Next safe
choices are either a matching live dry-run adapter, or DP/FM offline comparison
under the exact same observation and normalization.

### Base-Relative BC H8 XYZ Live Dry-Run Adapter

Date: 2026-05-06.

Implemented a matching live dry-run adapter for the base-relative arm-only BC
checkpoint:

```text
scripts/b8_bc_h8_xyz_base_relative_rollout_dry_run_node.py
config/b8_bc_h8_xyz_base_relative_rollout_dry_run.yaml
launch/b8_bc_h8_xyz_base_relative_rollout_dry_run.launch
```

The adapter reconstructs the same 23-D observation used by
`b8_primary30_bc_h8_xyz_base_relative_safe_norm`:

```text
active_joint_positions[6]
active_joint_velocities[6]
eef_position_base_frame[3]
target_position_base_frame[3]
target_to_eef_base_frame[3]
progress
one_minus_progress
```

Safety behavior:

```text
execute_actions=true is rejected
control_commands_sent=false
gripper_commands_sent=false
raw component abort threshold=0.03 m
label clip max component=0.005 m
label clip max norm=0.00866 m
```

Static checks passed:

```text
python3 -m py_compile scripts/b8_bc_h8_xyz_base_relative_rollout_dry_run_node.py
YAML parse of config/b8_bc_h8_xyz_base_relative_rollout_dry_run.yaml
xmllint --noout launch/b8_bc_h8_xyz_base_relative_rollout_dry_run.launch
roslaunch --nodes rexrov_single_oberon7_fm_dp b8_bc_h8_xyz_base_relative_rollout_dry_run.launch
```

Live `execute_actions=false` action-label check:

```text
output_json=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_dry_run_latest.json
status=timeout_complete
samples=21
aborted=false
control_commands_sent=false
gripper_commands_sent=false
raw_first=[0.009798044338822365, 0.00023514856002293527, 0.010150494053959846]
raw_absmax=0.010233319364488125
raw_p95_absmax_per_tick=0.010180839337408543
clipped_absmax=0.005
clip_component_count=21
clip_norm_count=0
first_target_to_eef_base=[0.11210433459712954, 0.0017082339120696455, 0.04141181584544196]
```

Decision:

```text
BC base-relative dry-run label path is smoke-level resolved.
This is not learned rollout success.
No arm command, gripper command, or grasp claim was made.
DP/FM may be compared later only under the same base-relative observation and
safe action normalization.

### DP/FM Base-Relative Safe-Norm Offline Comparison

Date: 2026-05-06.

Added DP/FM smoke configs that intentionally match the BC base-relative
rollout-planning route:

```text
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_smoke.yaml
config/train_flow_matching_b8_primary30_h8_xyz_base_relative_safe_norm_smoke.yaml
```

Shared observation/action gate:

```text
observation_keys:
  active_joint_positions
  active_joint_velocities
  eef_position_base_frame
  target_position_base_frame
  target_to_eef_base_frame
  episode_progress
  episode_remaining
action_dim_indices=[0,1,2]
action_std=[0.0010000000474974513, 0.0006739544332958758, 0.0005034060450270772]
```

Training was offline-only, 10 epochs each:

```text
Diffusion:
  obs_dim=23 action_dim=3 action_horizon=8
  best_val_loss=0.724308885473718
  checkpoint=outputs/checkpoints/b8_primary30_diffusion_h8_xyz_base_relative_safe_norm_smoke/best.pt
Flow Matching:
  obs_dim=23 action_dim=3 action_horizon=8
  best_val_loss=1.5957417760484962
  checkpoint=outputs/checkpoints/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_smoke/best.pt
```

Offline val comparison, using deterministic/direct BC and zero-init DP/FM:

```text
BC:
  normalized_mse=0.9591013831837524
  action_mse=3.0668218187202e-07
  pred_valid_p95_absmax=0.010113954171538353
Diffusion zero:
  normalized_mse=1.0149838184156725
  action_mse=3.2943790984063526e-07
  pred_valid_p95_absmax=0.010258672572672368
Flow Matching zero:
  normalized_mse=0.938351327353107
  action_mse=3.1596741223438585e-07
  pred_valid_p95_absmax=0.01013039778918028
```

Report:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_offline_comparison.md
outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_offline_comparison.json
```

Decision:

```text
The comparison is now apples-to-apples.
Old absolute-pose checkpoints are excluded.
BC remains the rollout-planning reference.
DP/FM are not rollout-ready and do not justify learned arm execution.
Full DP/FM training is not approved by this comparison alone.
No control command or gripper command was sent.
```

### DP/FM Base-Relative Epoch-Budget Ablation

Date: 2026-05-06.

Added and ran small epoch30 ablation configs:

```text
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30.yaml
config/train_flow_matching_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30.yaml
```

Training results:

```text
Diffusion epoch30:
  best_val_loss=0.4933774649536097
  final_val_loss=0.5405919651991578
Flow Matching epoch30:
  best_val_loss=1.5745682310192817
  final_val_loss=1.855106167735592
```

Offline zero-sampling val evaluation:

```text
DP epoch30:
  normalized_mse=0.9813141929366256
  action_mse=3.1285387080970395e-07
FM epoch30:
  normalized_mse=1.3268678915356436
  action_mse=4.1219857394025894e-07
```

Budget report:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_epoch_budget_ablation.md
outputs/logs/b8_primary30_training_planning/dp_fm_base_relative_safe_norm_epoch_budget_ablation.json
```

Decision:

```text
DP e30 is better than DP e10, but BC still has lower action MSE.
FM e30 overfits/worsens relative to FM e10.
BC remains the rollout-planning reference.
Do not start full DP/FM training from this evidence alone.
No rollout, arm command, gripper command, or grasp claim.
```

### Base-Relative Rollout-Readiness Preflight

Date: 2026-05-07.

Added a read-only preflight tool:

```text
scripts/analyze_b8_base_relative_rollout_readiness.py
```

The tool checks existing artifacts only:

```text
dry-run action-label JSON
base-relative DP/FM offline comparison
base-relative DP/FM epoch-budget ablation
arm-only rollout safety plan
```

Output:

```text
outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.md
outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.json
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
```

Passed gates:

```text
dry_run_no_abort=true
dry_run_no_control_or_gripper=true
dry_run_sample_count=true
dry_run_raw_action_scale=true
offline_comparison_same_observation_gate=true
bc_reference_not_displaced_by_dp_fm=true
safety_plan_no_gripper_no_grasp=true
```

Decision:

```text
The BC base-relative h8 xyz candidate is ready for rollout-planning review only.
This does not approve learned execution.
Before any tiny learned arm-only smoke: return to reference, require two fresh
target-aware gates, and obtain separate explicit approval.
```

### Base-Relative BC IK Command Preview

Date: 2026-05-07.

Enhanced:

```text
scripts/b8_bc_h8_xyz_base_relative_rollout_dry_run_node.py
config/b8_bc_h8_xyz_base_relative_rollout_dry_run.yaml
launch/b8_bc_h8_xyz_base_relative_rollout_dry_run.launch
```

New default-off args:

```text
preview_ik_once:=false
preview_ik_required:=true
```

With `preview_ik_once:=true`, the dry-run adapter calls
`ArmEEDeltaCommandConverter.convert()` for the first clipped 7-D action label.
It does not call `execute()` and does not publish the resulting trajectory.

Static checks:

```text
py_compile: PASS
YAML parse: PASS
xmllint: PASS
roslaunch --nodes: PASS
```

Live preview result:

```text
output_json=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_ik_preview_latest.json
status=timeout_complete
aborted=false
samples=17
control_commands_sent=false
gripper_commands_sent=false
preview_status=passed
would_publish_arm_command=false
raw_absmax=0.01020748633891344
clipped_xyz_action_frame=[0.005, 0.00026573764625936747, 0.005]
clipped_xyz_planning_frame=[-0.004293242404385794, 0.002860568696133876, 0.004843122225230549]
raw_joint_delta_max_abs=0.03397963688957391
clipped_joint_delta_max_abs=0.01
```

The rollout-readiness preflight now includes `ik_preview_no_publish=true`.

Decision:

```text
learned action -> IK preview path is available and bounded.
No command was published.
This is still not learned rollout success and does not approve execution.
```

### Base-Relative Rollout Safety Plan V2

Date: 2026-05-07.

Current blocker handled in this pass:

- The previous rollout safety plan artifact still referenced the old
  absolute-pose BC checkpoint:
  `outputs/checkpoints/b8_primary30_bc_h8_xyz/best.pt`.
- That checkpoint is already excluded from current rollout planning because the
  live dry-run/diagnostics showed unsafe action scale under absolute
  world-pose observations.

Changes:

```text
Added:
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_arm_only_rollout_safety_plan.md
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_arm_only_rollout_safety_plan.json

Updated:
scripts/analyze_b8_base_relative_rollout_readiness.py
```

The v2 plan references only the base-relative safe-norm BC candidate:

```text
checkpoint=outputs/checkpoints/b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt
config=config/train_bc_b8_primary30_h8_xyz_base_relative_safe_norm.yaml
obs_design=base-relative arm-only, no gripper_state, no absolute target_pose
action=dx,dy,dz in base_link
```

Static/read-only verification:

```text
python3 -m py_compile scripts/analyze_b8_base_relative_rollout_readiness.py: PASS
python3 scripts/analyze_b8_base_relative_rollout_readiness.py: PASS
```

Preflight output:

```text
outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.md
outputs/logs/b8_rollout_planning/base_relative_rollout_readiness_preflight.json
```

Preflight result:

```text
candidate_status=rollout_planning_candidate
checks_passed=true
go_for_learned_execution_now=false
separate_execution_approval_required=true
rollout_ready_success_claimed=false
control_commands_sent=false
gripper_commands_sent=false
safety_plan_json=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_arm_only_rollout_safety_plan.json
```

Passed gates:

```text
dry_run_no_abort=true
dry_run_no_control_or_gripper=true
dry_run_sample_count=true
dry_run_raw_action_scale=true
offline_comparison_same_observation_gate=true
bc_reference_not_displaced_by_dp_fm=true
safety_plan_no_gripper_no_grasp=true
ik_preview_no_publish=true
```

Decision:

```text
The base-relative BC h8 xyz candidate is a rollout-planning candidate only.
No learned rollout was run.
No arm or gripper command was sent.
This does not approve learned execution and does not claim rollout success.
Any future learned arm-only smoke still requires separate approval, return to
reference, and two fresh target-aware gates.
```

### Tiny Arm-Only Smoke Checklist Artifact

Date: 2026-05-07.

Added:

```text
scripts/generate_b8_base_relative_tiny_smoke_checklist.py
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_checklist.md
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_checklist.json
```

Updated:

```text
CMakeLists.txt
```

Purpose:

- Keep the next step as a planning/checklist artifact only.
- Verify that the current adapter remains dry-run only.
- Prevent accidentally treating the dry-run adapter as an executable learned
  rollout adapter.

Verification:

```text
python3 -m py_compile scripts/generate_b8_base_relative_tiny_smoke_checklist.py: PASS
python3 scripts/generate_b8_base_relative_tiny_smoke_checklist.py: PASS
launch XML parse: PASS
```

Checklist output:

```text
checklist_status=ready_for_review
checks_passed=true
learned_execution_approved_here=false
current_adapter_can_execute_actions=false
control_commands_sent=false
gripper_commands_sent=false
```

Adapter guard summary:

```text
execute_actions_true_forbidden=true
calls_arm_converter_convert=true
calls_arm_converter_execute=false
publishes_action_labels=true
```

Decision:

```text
Current adapter cannot be used for learned execution.
If a tiny arm-only learned smoke is separately approved later, first implement
and review a dedicated execution adapter; then return to reference and require
two fresh target-aware gates.
No gripper/hand and no grasp claim remain mandatory.
```

### Dedicated Active-Left Execution Smoke Adapter

Date: 2026-05-07.

Implemented:

```text
scripts/b8_bc_h8_xyz_base_relative_execution_smoke_node.py
config/b8_bc_h8_xyz_base_relative_execution_smoke.yaml
launch/b8_bc_h8_xyz_base_relative_execution_smoke.launch
```

Registered:

```text
CMakeLists.txt
```

Generated static review artifacts:

```text
outputs/logs/b8_rollout_planning/base_relative_execution_smoke_adapter_review.md
outputs/logs/b8_rollout_planning/base_relative_execution_smoke_adapter_review.json
```

Design:

- Separate node from the dry-run adapter.
- Default launch does not execute actions.
- Publishing arm commands requires both:
  - `execute_actions:=true`
  - `i_understand_this_publishes_arm_commands:=true`
- Uses the base-relative safe-norm BC checkpoint only.
- Sends only active-left arm trajectory through
  `/oberon7/arm_position_l/command`.
- Never starts hand controller and never publishes gripper commands.
- Limits first smoke to `max_control_ticks=3`.
- Keeps `max_policy_xyz_component=0.005` and
  `max_joint_delta_per_command_rad=0.01`.

Verification:

```text
python3 -m py_compile scripts/b8_bc_h8_xyz_base_relative_execution_smoke_node.py: PASS
YAML parse config/b8_bc_h8_xyz_base_relative_execution_smoke.yaml: PASS
launch XML parse b8_bc_h8_xyz_base_relative_execution_smoke.launch: PASS
roslaunch --nodes rexrov_single_oberon7_fm_dp b8_bc_h8_xyz_base_relative_execution_smoke.launch: PASS
```

Static review result:

```text
adapter_review_status=ready_for_return_and_two_fresh_gates
checks_passed=true
control_commands_sent=false
gripper_commands_sent=false
learned_rollout_run=false
```

Important:

```text
No learned execution was run in this pass.
The next runtime step is return-to-reference and two fresh target-aware gates.
Only after both gates pass should the explicit tiny smoke command be run.
Do not claim grasp success or general learned rollout success.
```

Runbook:

```text
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_runbook.md
```

### First Tiny Arm-Only Learned Smoke Result

Date: 2026-05-07.

User ran the first tiny active-left arm-only BC base-relative execution smoke
after return-to-reference and two fresh target-aware gates.

Preconditions:

```text
return_left_arm_to_reference: reached=true, gripper_commands_sent=false
pre_gate_0: passed=true, control_commands_sent=false, gripper_commands_sent=false
pre_gate_1: passed=true, control_commands_sent=false, gripper_commands_sent=false
```

Execution smoke:

```text
output=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_execution_smoke_latest.json
status=max_control_ticks_complete
samples=3
control_commands_sent=true
gripper_commands_sent=false
hand_controller_started=false
aborted=false
max_control_ticks=3
```

Command/action bounds:

```text
raw_action_absmax=0.010118558071553707
clipped_action_absmax=0.005
clipped_joint_delta_absmax=0.01
```

Distance/target result:

```text
pre_gate_1_initial_distance=0.10769686466831795
post_gate_initial_distance=0.09675726747351836
gate_distance_reduction=0.010939597194799588
smoke_first_distance=0.1124765533517506
smoke_last_distance=0.1044908581133651
smoke_distance_reduction=0.007985695238385493
post_gate_target_base_drift=0.006632863059974026
post_gate_relative_base_drift=0.013394591587890489
post_gate_passed=false
post_gate_failed_checks=[relative_base_drift_ok]
```

Added summary tool/artifacts:

```text
scripts/summarize_b8_base_relative_tiny_smoke.py
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_summary.md
outputs/logs/b8_rollout_planning/base_relative_tiny_smoke_summary.json
```

Verification:

```text
python3 -m py_compile scripts/summarize_b8_base_relative_tiny_smoke.py: PASS
python3 scripts/summarize_b8_base_relative_tiny_smoke.py: PASS
roslaunch --nodes rexrov_single_oberon7_fm_dp b8_bc_h8_xyz_base_relative_execution_smoke.launch: PASS
```

Summary decision:

```text
command_path_smoke_resolved=true
smoke_status=command_path_smoke_resolved_not_success
arm_only_reaching_success_claimed=false
grasp_success_claimed=false
```

Interpretation:

```text
The learned active-left arm command path is smoke-level resolved.
This is not arm-only reaching success because distance reduction was
0.01094 m, below the planned 0.02 m threshold.
The post initial-state gate failed only because relative_base_drift changed
after the arm moved; target_base_drift stayed within 0.01 m.
No gripper/hand command was sent.
Return to reference before any further live checks.
```

### Post Tiny-Smoke Return/Gate Recovery

Date: 2026-05-07.

User ran the requested post-smoke recovery check.

Artifacts:

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
checks.eef_base_drift_ok=true
checks.initial_distance_ok=true
checks.joint_l2_ok=true
checks.joint_max_abs_ok=true
checks.relative_base_drift_ok=true
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

```text
The active-left learned command path blocker is resolved at smoke level:
the adapter published three bounded arm commands, then the arm could be
returned and the fresh target-aware initial-state gate passed.
This is not rollout success and not grasp success.
Do not run a second learned smoke or a larger batch without a separate review.
```

### First Tiny-Smoke Review Decision

Date: 2026-05-07.

Reviewed the first tiny-smoke summary and the post-return gate.

Artifacts:

```text
outputs/logs/b8_rollout_planning/first_tiny_smoke_review_decision.md
outputs/logs/b8_rollout_planning/first_tiny_smoke_review_decision.json
```

Review checks:

```text
command_path_smoke_resolved=true
system_recovered_to_gate=true
distance_decreased_monotonically_during_smoke=true
bounded_actions_and_joints=true
no_gripper_or_hand=true
success_not_claimed=true
```

Distance evidence:

```text
distances_during_smoke=[0.1124765533517506, 0.10822837102368213, 0.1044908581133651]
per_tick_distance_reductions=[0.004248182328068464, 0.0037375129103170285]
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

Rationale:

```text
The first smoke proves the active-left learned command path at smoke level.
It is too short to claim arm-only reaching success.
The cleanest second test changes only max_control_ticks from 3 to 5.
Changing model, action horizon, or training now would confound the result.
DP/FM stay offline-only.
```

### Second Tiny-Smoke Runbook Prepared

Date: 2026-05-07.

Prepared, but did not execute, the next live test runbook:

```text
outputs/logs/b8_rollout_planning/second_tiny_smoke_runbook.md
```

Decision carried into runbook:

```text
same_checkpoint=true
same_action_horizon=true
same_clip_limits=true
max_control_ticks=5
return_and_two_fresh_gates_required=true
no_gripper_or_hand=true
```

The runbook includes:

```text
second_tiny_smoke_return_to_reference.json
second_tiny_smoke_pre_gate/gate_0.json
second_tiny_smoke_pre_gate/gate_1.json
bc_h8_xyz_base_relative_second_execution_smoke.json
second_tiny_smoke_post_gate/post_smoke_gate.json
second_tiny_smoke_summary.json
```

No control command was sent by this preparation step. No second learned smoke
was run.

### Second Tiny Arm-Only Learned Smoke Result

Date: 2026-05-07.

User ran the approved second active-left arm-only BC base-relative execution
smoke after return-to-reference and two fresh target-aware gates. This second
smoke changed only one runtime variable from the first smoke:

```text
max_control_ticks: 3 -> 5
same_checkpoint=true
same_action_horizon=true
same_clip_limits=true
no_gripper_or_hand=true
```

Pre-gate evidence:

```text
second_tiny_smoke_pre_gate/gate_0.json:
  passed=true
  initial_distance=0.10770107274397023
  relative_base_drift=2.3910213487824768e-06
  target_base_drift=0.0009021523014456818

second_tiny_smoke_pre_gate/gate_1.json:
  passed=true
  initial_distance=0.11405293503812372
  relative_base_drift=0.006740151128213844
  target_base_drift=0.00585548667369759
```

Execution:

```text
output=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_second_execution_smoke.json
status=max_control_ticks_complete
samples=5
control_commands_sent=true
gripper_commands_sent=false
hand_controller_started=false
aborted=false
raw_action_absmax=0.010124818421900272
clipped_action_absmax=0.005
clipped_joint_delta_absmax=0.01
```

Post-smoke gate:

```text
output=outputs/logs/b8_rollout_planning/second_tiny_smoke_post_gate/post_smoke_gate.json
passed=false
failed_checks=[relative_base_drift_ok]
initial_distance=0.0796048439094755
relative_base_drift=0.029749312305554818
target_base_drift=0.0006060769336670867
```

The post initial-state gate failing `relative_base_drift_ok` is expected after
the arm has moved. It is not evidence of target drift; target drift remained
well below `0.01 m`.

Summary script fix:

```text
scripts/summarize_b8_base_relative_tiny_smoke.py
```

The first implementation could mark the second smoke as `not_resolved` even
when the configured arm-only reaching threshold was met, because the
`arm_only_success_threshold` check was inverted and the success status branch
was missing. The script now reports:

```text
smoke_status=arm_only_reaching_success
arm_only_reaching_success_claimed=true
learned_rollout_success_claimed=false
grasp_success_claimed=false
```

Verification:

```text
python3 -m py_compile scripts/summarize_b8_base_relative_tiny_smoke.py: PASS
regenerated first summary: still command_path_smoke_resolved_not_success
regenerated second summary: arm_only_reaching_success, checks_passed=true
```

Second summary result:

```text
output=outputs/logs/b8_rollout_planning/second_tiny_smoke_summary.json
smoke_status=arm_only_reaching_success
command_path_smoke_resolved=true
checks_passed=true
arm_only_reaching_success_claimed=true
learned_rollout_success_claimed=false
grasp_success_claimed=false
gate_distance_reduction=0.03444809112864822
smoke_distance_reduction=0.022283184328319994
post_gate_initial_distance=0.0796048439094755
```

Current blocker judgment:

```text
active-left command path blocker: resolved
single-smoke arm-only reaching threshold: met once
general learned rollout success: not claimed
grasp success: not claimed
repeatability across learned smokes: not yet proven
DP/FM live readiness: still blocked
```

Next blocker-local action:

```text
Return the arm to reference and run one strict fresh target-aware gate before
any further live work. Do not run a third learned smoke or rollout batch until
this second summary is reviewed and a separate repeatability plan is approved.
```

### Post-Second-Smoke Return/Gate Recovery

Date: 2026-05-07.

Ran the blocker-local recovery check after the second tiny learned smoke. This
sent bounded active-left return commands only; no gripper or hand command was
sent.

Artifacts:

```text
outputs/logs/b8_rollout_planning/post_second_tiny_smoke_return_gate/return_to_reference.json
outputs/logs/b8_rollout_planning/post_second_tiny_smoke_return_gate/gate.json
outputs/logs/b8_rollout_planning/post_second_tiny_smoke_return_gate/gate_retry_1.json
```

Return result:

```text
reached=true
commands_sent=4
gripper_commands_sent=false
joint_l2_error=0.00010727774213185266
joint_max_abs_error=7.796206191645894e-05
```

First strict fresh gate:

```text
passed=false
failed_checks=[initial_distance_ok]
initial_distance=0.11597705385617631
eef_base_drift=3.680959080162773e-05
joint_l2_drift=0.0003393003577343886
joint_max_abs_drift=0.000332950770830287
relative_base_drift=0.008407799299876022
target_base_drift=0.008371269123874233
control_commands_sent=false
gripper_commands_sent=false
```

Because the only failed check was a marginal `initial_distance` boundary miss
about `0.00098 m` above the strict `0.115 m` threshold, ran one read-only
5-second settle retry.

Retry strict fresh gate:

```text
passed=true
initial_distance=0.11436097332458071
eef_base_drift=2.446827570313163e-05
joint_l2_drift=0.00019197469822725472
joint_max_abs_drift=0.00015823643874046667
relative_base_drift=0.0070635920892258355
target_base_drift=0.007080020803718068
control_commands_sent=false
gripper_commands_sent=false
```

Recovery judgment:

```text
post_second_smoke_return_reached=true
post_second_smoke_strict_gate_recovered_after_one_retry=true
system_back_to_controlled_initial_state=true
gripper_commands_sent=false
hand_controller_started=false
```

This completes the post-second-smoke recovery requirement. Do not run a third
learned smoke automatically; the next decision should be either a separately
approved N=2/3 repeatability plan or offline-only DP/FM diagnostics under the
same base-relative observation and safe action normalization.

### Offline-Only DP/FM Post-Live-Smoke Gate

Date: 2026-05-07.

Returned to DP/FM work in offline-only mode after the second BC
base-relative tiny arm-only smoke and post-smoke recovery gate. No ROS,
simulator, arm command, gripper command, full training, or learned rollout was
run.

Added:

```text
scripts/analyze_b8_dp_fm_post_live_smoke_gate.py
outputs/logs/b8_primary30_training_planning/dp_fm_post_live_smoke_offline_gate.md
outputs/logs/b8_primary30_training_planning/dp_fm_post_live_smoke_offline_gate.json
```

Registered:

```text
CMakeLists.txt
```

Offline-only sampling sensitivity rerun:

```text
DP epoch30 zero-init denoise steps: 10, 25, 50, 100
FM epoch10 zero-init ODE steps: 10, 25, 50, 100
```

Results:

```text
BC h8 xyz base-relative safe-norm:
  action_mse=3.0668218187202e-07
  normalized_mse=0.9591013831837524

DP h8 xyz zero epoch30:
  steps10 action_mse=3.186387402820401e-07
  steps25 action_mse=3.1589311788593477e-07
  steps50 action_mse=3.1285387080970395e-07
  steps100 action_mse=3.1285387080970395e-07

FM h8 xyz zero epoch10:
  ode10 action_mse=3.162992356919858e-07
  ode25 action_mse=3.1664731636737997e-07
  ode50 action_mse=3.1596741223438585e-07
  ode100 action_mse=3.1621729590369796e-07
```

Gate report decision:

```text
checks_passed=true
bc_remains_live_reference=true
dp_fm_live_execution_approved=false
full_dp_fm_training_approved=false
dp_fm_rollout_ready_success_claimed=false
learned_rollout_run=false
gripper_commands_sent=false
grasp_success_claimed=false
```

Interpretation:

- The DP/FM comparison remains apples-to-apples: same base-relative arm-only
  observation, same dx/dy/dz action space, same safe action normalization, old
  absolute-pose checkpoints excluded.
- The BC base-relative checkpoint now has one reviewed arm-only live smoke
  success and still has lower offline action MSE than the best DP/FM candidate.
- More sampling steps alone do not close the gap: DP stops improving at 50
  steps and FM is nearly flat across ODE steps.
- DP/FM live execution remains blocked. Do not build a DP/FM live adapter or
  run a DP/FM smoke from this evidence.

Next allowed DP/FM work:

```text
offline-only DP h8 focused budget/seed ablation, if explicitly approved.
No full DP/FM training.
No DP/FM learned rollout.
```

### BC Base-Relative Tiny Repeatability N=2 Runbook

Date: 2026-05-07.

Prepared the next BC repeatability plan without executing live commands.

Added:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n2_runbook.md
scripts/summarize_b8_base_relative_tiny_repeatability.py
```

Registered:

```text
CMakeLists.txt
```

Runbook constraints:

```text
N=2 only
same_checkpoint=true
same_action_horizon=true
same_clip_limits=true
max_control_ticks=5
stop_on_first_failure=true
no_gripper_or_hand=true
no_grasp_claim=true
learned_rollout_success_claimed=false
dp_fm_live_execution=false
training=false
```

Per-cycle sequence:

```text
return_left_arm_to_reference
strict fresh gate with wait/retry only
same BC base-relative tiny smoke
post gate
per-cycle summary
```

The new aggregate summary script only reads per-cycle summary JSONs and writes
an aggregate report. It does not run ROS, publish arm commands, or send
gripper commands.

Verification:

```text
python3 -m py_compile scripts/summarize_b8_base_relative_tiny_repeatability.py: PASS
offline smoke-test of aggregator with existing second_tiny_smoke_summary.json: PASS
runbook markdown fence check: PASS
```

No third learned smoke was run by this preparation step.

### BC Base-Relative Tiny Repeatability N=2 Result

Date: 2026-05-07.

Executed the approved N=2 BC base-relative tiny repeatability run. The fixed
live parameters were unchanged from the second tiny smoke:

```text
checkpoint=b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt
max_control_ticks=5
max_duration_sec=7.2
rate_hz=3.0
max_policy_xyz_component=0.005
max_joint_delta_per_command_rad=0.01
no_gripper_or_hand=true
```

During cycle 0, the runbook stopped after the post gate because `set -e` saw
the expected post-move `check_b8_initial_state_gate.py` nonzero exit when
`relative_base_drift_ok=false`. This was a runbook control-flow issue, not a
cycle failure. Cycle 0 summary was then run read-only and passed. The runbook
was patched so post-gate nonzero exit is captured and summary decides whether
the expected post-move gate failure is acceptable.

Cycle 0:

```text
return_reached=true
pre_gate_passed=true
smoke_status=arm_only_reaching_success
checks_passed=true
post_gate_initial_distance=0.07552088193012559
gate_distance_reduction=0.037702544189661805
smoke_distance_reduction=0.022082939032266186
raw_action_absmax=0.010138695128262043
clipped_action_absmax=0.005
clipped_joint_delta_absmax=0.01
post_gate_target_base_drift=0.0009021523014518786
gripper_commands_sent=false
learned_rollout_success_claimed=false
grasp_success_claimed=false
```

Cycle 1:

```text
return_reached=true
pre_gate_passed=true
smoke_status=arm_only_reaching_success
checks_passed=true
post_gate_initial_distance=0.07671502116552151
gate_distance_reduction=0.034746377345962684
smoke_distance_reduction=0.023297424060010133
raw_action_absmax=0.010102524422109127
clipped_action_absmax=0.005
clipped_joint_delta_absmax=0.01
post_gate_target_base_drift=0.0009021523014478303
gripper_commands_sent=false
learned_rollout_success_claimed=false
grasp_success_claimed=false
```

Aggregate:

```text
output=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n2/summary.json
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
```

Post-repeatability recovery:

```text
return_reached=true
return_joint_l2_error=0.0001292675365380578
return_joint_max_abs_error=9.511785811078255e-05
strict_gate_passed=true
strict_gate_initial_distance=0.10690899555892072
strict_gate_relative_base_drift=0.0008686295574533427
strict_gate_target_base_drift=0.0009021523014487895
gripper_commands_sent=false
```

Current blocker judgment:

```text
BC base-relative active-left arm-only reaching repeatability smoke: resolved for N=2
grasp success: not claimed
general learned rollout success rate: not claimed
DP/FM live readiness: still blocked
```

Next:

```text
Do not jump to a large rollout batch. If continuing live work, plan N=3 with
the same fixed checkpoint/action horizon/clip/tick parameters and the corrected
post-gate handling. Otherwise return to offline diagnostics/reporting.
```

### BC Base-Relative Tiny Repeatability N=3 Runbook Prepared

Date: 2026-05-07.

Prepared a dedicated N=3 continuation runbook:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3_runbook.md
```

The runbook keeps the N=2 live parameters unchanged:

```text
checkpoint=b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt
max_control_ticks=5
max_duration_sec=7.2
rate_hz=3.0
max_policy_xyz_component=0.005
max_joint_delta_per_command_rad=0.01
cycles=3
stop_on_first_failure=true
no_gripper_or_hand=true
no_dp_fm_live=true
```

Each cycle is still:

```text
return_left_arm_to_reference
strict fresh target-aware gate with wait/retry
BC base-relative tiny smoke
post gate with nonzero exit captured
per-cycle summary
```

The N=3 live run was not executed in this Codex turn because the runtime was
not connected to a ROS master:

```text
rosnode list -> ERROR: Unable to communicate with master
```

Current blocker judgment is unchanged:

```text
latest executed BC repeatability evidence=N=2 passed
N=3 status=prepared_not_run
grasp success=not claimed
general learned rollout success=not claimed
DP/FM live readiness=still blocked
```

### BC Base-Relative Tiny Repeatability N=3 Attempt

Date: 2026-05-07.

After ROS was restarted, executed the N=3 runbook with the same fixed live
parameters:

```text
checkpoint=b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt
max_control_ticks=5
max_duration_sec=7.2
rate_hz=3.0
max_policy_xyz_component=0.005
max_joint_delta_per_command_rad=0.01
no_gripper_or_hand=true
```

The run stopped on the first per-cycle failure, as intended:

```text
cycle_0=passed
cycle_1=failed
cycle_2=not_run
partial_summary=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/partial_summary_after_stop.json
repeatability_smoke_status=not_resolved
repeatability_smoke_passed=false
success_count=1
arm_only_reaching_repeatability_claimed=false
learned_rollout_success_claimed=false
grasp_success_claimed=false
gripper_commands_sent=false
```

Cycle 0:

```text
pre_gate_passed=true
smoke_status=arm_only_reaching_success
checks_passed=true
post_gate_initial_distance=0.08205602794720912
gate_distance_reduction=0.02565459092089968
smoke_distance_reduction=0.022549257867972697
post_gate_target_base_drift=0.004307210431956841
raw_action_absmax=0.010069108568131924
clipped_action_absmax=0.005
clipped_joint_delta_absmax=0.01
```

Cycle 1:

```text
pre_gate_passed=true
smoke_status=not_resolved
checks_passed=false
post_gate_initial_distance=0.09688016467661553
gate_distance_reduction=0.012153615105508359
smoke_distance_reduction=0.01512330204500184
post_gate_target_base_drift=0.01016428396425749
raw_action_absmax=0.010100629180669785
clipped_action_absmax=0.005
clipped_joint_delta_absmax=0.01
failed_checks=post_target_drift_ok, arm_only_success_threshold
```

The wrapper then performed recovery:

```text
return_reached=true
return_joint_l2_error=0.0001857971116926321
return_joint_max_abs_error=0.00016350626718075745
strict_gate_passed=true
strict_gate_initial_distance=0.10764093300810804
strict_gate_relative_base_drift=7.61146949187862e-05
strict_gate_target_base_drift=7.858877410019059e-05
gripper_commands_sent=false
```

Current blocker judgment:

```text
BC base-relative active-left arm-only reaching repeatability smoke: resolved for N=2 only
N=3 repeatability: not resolved
grasp success: not claimed
general learned rollout success rate: not claimed
DP/FM live readiness: still blocked
```

Next:

```text
Do not run another live smoke immediately. Inspect cycle_1 JSON artifacts and
compare cycle_0/cycle_1 command and distance traces read-only, or return to
offline-only model diagnostics. Do not start DP/FM live execution.
```

### N=3 Cycle 0/1 Read-Only And Offline-Only Diagnosis

Date: 2026-05-07.

Completed both requested diagnostic lines without live execution or training:

```text
tool=scripts/analyze_b8_n3_repeatability_failure.py
output_json=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/read_only_failure_diagnosis.json
output_md=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/read_only_failure_diagnosis.md
control_commands_sent=false
gripper_commands_sent=false
hand_controller_started=false
training_started=false
dp_fm_live_execution=false
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

Cycle comparison:

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
cycle_0_joint_clip_l2_loss_mean=0.01305745916537569
cycle_1_joint_clip_l2_loss_mean=0.030305542098136923
```

Offline model diagnostic:

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

```text
primary_failure_mode=motion_budget_brittleness_under_clip_and_target_drift
not_policy_output_instability=true
not_clear_geometry_ood=true
```

The raw policy output is stable across cycle 0/1 and close to the training
action distribution. The live adapter clips x/z from roughly `0.010 m` to
`0.005 m` every tick. With only five control ticks, cycle 0 still passed, but
cycle 1 did not meet the `>0.02 m` reduction requirement and its target drift
landed just above the strict `0.01 m` post-target threshold.

Next:

```text
Do not run another live smoke immediately.
Do not start DP/FM live execution.
If continuing, first do offline-only sensitivity checks for tick budget and/or
clip limits against recorded traces before proposing any live rerun.
```

### N=3 Tick/Clip Sensitivity Projection

Date: 2026-05-07.

Completed an offline-only replay-style projection over the recorded N=3 cycle
0/1 traces:

```text
tool=scripts/analyze_b8_n3_tick_clip_sensitivity.py
output_json=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/offline_tick_clip_sensitivity.json
output_md=outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_repeatability_n3/offline_tick_clip_sensitivity.md
projection_only_not_physics_sim=true
control_commands_sent=false
gripper_commands_sent=false
hand_controller_started=false
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

Cycle 1 sensitivity:

```text
current_clip=0.005
current_ticks=5
gate_reduction=0.012153615105508359
target_base_drift=0.01016428396425749
raw_to_clipped_norm_ratio_mean=2.0005623615947354
required_ticks_current_clip_for_reduction=9
required_ticks_raw_scale_for_reduction=5
```

Projection examples:

```text
clip=0.005 ticks=8 -> projected_gate_reduction=0.019445784168813374, distance_gate_pass=false
clip=0.0075 ticks=6 -> projected_gate_reduction=0.02187393241902867, distance_gate_pass=true, all_modeled_pass=false
clip=0.010 ticks=5 -> projected_gate_reduction=0.02424284511639152, distance_gate_pass=true, all_modeled_pass=false
```

Interpretation:

```text
tick_budget_axis=plausible_but_5_to_8_at_current_clip_is_insufficient_for_cycle_1
clip_limit_axis=plausible_for_distance_reduction
target_drift_axis=not_resolved_by_projection
live_rerun=not_approved
```

The projection suggests the current `0.005 m` x/z clip is too restrictive for
the failed cycle 1 at five ticks. However, because the post target drift was
already just above the strict `0.01 m` threshold, changing tick or clip alone
is not proven safe by this offline projection. Any future live rerun should be
separately reviewed and change only one variable at a time.

### Single-Variable Candidate Review And Tick9 Runbook

Date: 2026-05-07.

Prepared the next single-variable candidate review and runbook. No live command
was executed.

Artifacts:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_single_variable_candidate_review.json
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_single_variable_candidate_review.md
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke_runbook.md
```

Selected candidate:

```text
candidate_id=bc_h8_xyz_base_relative_tick9_single_smoke
change=max_control_ticks: 5 -> 9
scope=N=1 only
live_rerun_approved_by_this_review=false
n3_repeatability_resolved=false
dp_fm_live_approved=false
```

Fixed parameters:

```text
checkpoint=b8_primary30_bc_h8_xyz_base_relative_safe_norm/best.pt
action_horizon=8
max_policy_xyz_component=0.005
max_joint_delta_per_command_rad=0.01
rate_hz=3.0
max_duration_sec=7.2
no_gripper_or_hand=true
```

Why tick first:

```text
single_launch_argument=true
per_command_cartesian_clip_unchanged=true
per_command_joint_delta_limit_unchanged=true
cycle_1_required_ticks_current_clip_for_reduction=9
```

Why not clip first:

```text
clip_change_requires_config_level_change=true
per_command_cartesian_authority_changes=true
target_drift_unresolved_by_projection=true
cycle_1_raw_joint_deltas_already_often_above_joint_clamp=true
```

### Tick9 Single-Smoke Execution Outcome

Date: 2026-05-07.

After explicit approval, executed the prepared N=1 tick-budget sensitivity
smoke. The only planned variable change was:

```text
max_control_ticks: 5 -> 9
```

Artifacts:

```text
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke/summary.json
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke/summary.md
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke/outcome.json
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_single_smoke/outcome.md
```

Preconditions:

```text
return_reached=true
pre_gate_passed=true
pre_gate_initial_distance=0.10763205373420012
pre_gate_relative_base_drift=7.418546451184545e-05
pre_gate_target_base_drift=7.858877410063669e-05
```

Smoke result:

```text
smoke_status=arm_only_reaching_success
checks_passed=true
control_commands_sent=true
gripper_commands_sent=false
hand_controller_started=false
grasp_success_claimed=false
learned_rollout_success_claimed=false
post_gate_initial_distance=0.06884095013771155
gate_distance_reduction=0.038791103596488574
smoke_distance_reduction=0.032973856201507806
raw_action_absmax=0.010168945416808128
clipped_action_absmax=0.005
clipped_joint_delta_absmax=0.01
post_gate_target_base_drift=7.858877409400243e-05
```

Post-run recovery:

```text
recovery_return_reached=true
initial_recovery_gate_passed=false
initial_recovery_gate_failure=initial_distance_ok,false;relative_base_drift_ok,false
retry_gate_1_passed=false
retry_gate_2_passed=true
final_retry_gate_initial_distance=0.10763685573691596
final_retry_gate_relative_base_drift=7.244770614888639e-05
final_retry_gate_target_base_drift=7.858877410115714e-05
```

Interpretation:

```text
tick9_single_smoke_passed=true
system_recovered_after_retry=true
n3_repeatability_resolved=false
next_live_approved=false
dp_fm_live_approved=false
```

### Tick9 Vs N3 Tick5 Read-Only Comparison

Date: 2026-05-07.

Added and ran a read-only comparison script:

```text
scripts/analyze_b8_tick9_vs_n3_tick5.py
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_vs_n3_tick5_comparison.json
outputs/logs/b8_rollout_planning/bc_h8_xyz_base_relative_tick9_vs_n3_tick5_comparison.md
```

No ROS commands, no hand/gripper controller, no gripper command, and no
training were used.

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

Distance and drift comparison:

```text
n3_cycle_0_tick5_smoke_reduction=0.022549257867972697
n3_cycle_1_tick5_smoke_reduction=0.01512330204500184
tick9_first5_reduction=0.017696858119856753
tick9_extra_tick_distance_reduction=0.015276998081651047
tick9_total_smoke_reduction=0.032973856201507806
tick9_first5_reduction_gain_vs_cycle1=0.0025735560748549186
tick9_total_reduction_gain_vs_cycle1=0.017850554156505966
n3_cycle_1_target_drift=0.01016428396425749
tick9_target_drift=7.858877409400243e-05
```

Action stability:

```text
clipped_action_mean_delta_cycle1_to_tick9_l2=5.2579650057143435e-05
policy_action_shift_detected=false
```

Interpretation:

```text
tick9_improvement_due_to_extra_ticks=true
tick9_improvement_due_to_cleaner_target_drift=true
tick9_improvement_due_to_policy_shift=false
```

The tick9 pass should therefore remain scoped as one successful arm-only
tick-budget sensitivity smoke. It is not proof of N=3 repeatability, not grasp
success, and not general learned rollout success.

### Target-Drift Readiness Gate Review

Date: 2026-05-07.

Added and ran a read-only target-drift readiness review:

```text
scripts/analyze_b8_target_drift_readiness_gate.py
outputs/logs/b8_rollout_planning/b8_target_drift_readiness_gate_review.json
outputs/logs/b8_rollout_planning/b8_target_drift_readiness_gate_review.md
```

No ROS commands, no hand/gripper controller, no gripper command, and no
training were used.

Decision:

```text
target_drift_is_live_confound=true
clean_pre_gate_examples=8
failed_post_target_drift_examples=1
next_live_approved=false
dp_fm_live_approved=false
n3_repeatability_resolved=false
```

Recommended readiness gate:

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

Historical gate distribution from existing artifacts:

```text
gate_count=75
pre_live_gate_count=25
pre_live_gate_passed=24
pre_live_gate_clean_target=8
pre_live_gate_target_drift_p50=0.003737260370026336
pre_live_gate_target_drift_p95=0.0506330196239176
post_live_gate_target_drift_max=0.01016428396425749
```

Interpretation:

```text
standard_passed_gate_not_enough_to_isolate_target_drift=true
future_live_readiness_requires_two_clean_gates=true
readiness_gate_approves_live=false
dp_fm_live_approved=false
```

### DP/FM Post-Tick9 Offline Gate

Date: 2026-05-07.

Added and ran a post-tick9 DP/FM offline gate:

```text
scripts/analyze_b8_dp_fm_post_tick9_offline_gate.py
outputs/logs/b8_primary30_training_planning/dp_fm_post_tick9_offline_gate.json
outputs/logs/b8_primary30_training_planning/dp_fm_post_tick9_offline_gate.md
```

No ROS commands, no hand/gripper controller, no gripper command, no BC/DP/FM
training, and no learned rollout were used.

Checks:

```text
offline_artifacts_only=true
same_base_relative_safe_norm=true
tick9_is_single_smoke_only=true
target_readiness_blocks_live=true
bc_still_best_action_mse=true
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

Metrics:

```text
bc_action_mse=3.0668218187202e-07
dp10_action_mse=3.2943790984063526e-07
dp30_action_mse=3.1285387080970395e-07
fm10_action_mse=3.1596741223438585e-07
fm30_action_mse=4.1219857394025894e-07
dp30_action_mse_relative_to_bc=0.020124054485367575
fm10_action_mse_relative_to_bc=0.03027639331925912
```

Interpretation:

```text
dp_fm_can_continue_offline=true
dp_fm_live_remains_blocked=true
bc_live_reference_unchanged=true
```

### DP/FM Validation-Window Diagnostics

Date: 2026-05-07.

Added and ran offline validation-window diagnostics:

```text
scripts/analyze_b8_dp_fm_validation_windows.py
outputs/logs/b8_primary30_training_planning/dp_fm_validation_window_diagnostics.json
outputs/logs/b8_primary30_training_planning/dp_fm_validation_window_diagnostics.md
```

No ROS commands, no hand/gripper controller, no gripper command, no training,
and no learned rollout were used.

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

```text
dp30_close_but_not_better_than_bc=true
fm10_max_window_risk_higher=true
action_scale_stable=true
dp_fm_live_remains_blocked=true
```

Interpretation:

```text
prepared_only=true
live_execution=false
grasp_success_claimed=false
general_learned_rollout_success_claimed=false
```

If this candidate is later approved and passes, it is still only a single
tick-budget sensitivity smoke, not repeatability and not a learned rollout
success rate.

### DP30 Focused Offline Ablation Plan

Date: 2026-05-07.

Continued DP/FM strictly offline. Added DP30 seed-ablation configs and
planning/evaluation tools:

```text
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed85.yaml
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86.yaml
scripts/plan_b8_dp30_focused_offline_ablation.py
scripts/analyze_b8_dp30_seed_ablation_validation.py
outputs/logs/b8_primary30_training_planning/dp30_focused_offline_ablation_plan.json
outputs/logs/b8_primary30_training_planning/dp30_focused_offline_ablation_plan.md
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.json
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.md
```

No ROS command, no hand/gripper controller, no gripper command, no training,
and no learned rollout were used.

Plan decision:

```text
dp_offline_ablation_can_continue=true
selected_axis=diffusion_seed_only
candidate_seeds=[84, 85, 86]
bc_remains_live_reference=true
dp_fm_live_approved=false
full_dp_fm_training_as_success_approved=false
training_started=false
```

Seed-ablation evaluator baseline:

```text
bc_action_mse=3.066821534503106e-07
best_dp_seed_candidate=dp30_seed84_zero
best_dp_action_mse=3.1285387080970395e-07
best_dp_relative_to_bc=0.020124149025167605
missing_candidate_count=2
dp_fm_live_approved=false
training_started_by_this_script=false
```

Interpretation:

- Seed85/seed86 are prepared as bounded offline-only candidates, not trained.
- The comparison remains apples-to-apples with the BC base-relative safe-norm
  route: h4/h8, xyz-only action, no absolute world target pose, no gripper
  state, and safe action std fallback.
- BC remains the live reference.
- DP/FM live execution remains blocked.
- No grasp success, learned rollout success, or general rollout success is
  claimed.

### DP/FM Sampling Sweep After Seed Ablation

Date: 2026-05-07.

Ran an offline-only DP/FM sampling sensitivity check:

```text
scripts/analyze_b8_dp_fm_sampling_after_seed_ablation.py
outputs/logs/b8_primary30_training_planning/dp_fm_sampling_after_seed_ablation.json
outputs/logs/b8_primary30_training_planning/dp_fm_sampling_after_seed_ablation.md
```

No ROS command, no hand/gripper controller, no gripper command, no training,
and no learned rollout were used by this diagnostic.

Result:

```text
bc_remains_reference=true
best_non_bc=dp30_seed86_zero_steps50
best_non_bc_relative_to_bc=0.013692332058653145
sampling_steps_close_gap=false
dp_fm_live_approved=false
training_started=false
```

Metrics:

```text
bc_ref action_mse=3.066821534503106e-07
dp30_seed84_zero_steps50 action_mse=3.1285387080970395e-07
dp30_seed86_zero_steps10 action_mse=3.175369158725516e-07
dp30_seed86_zero_steps25 action_mse=3.138577824302047e-07
dp30_seed86_zero_steps50 action_mse=3.1088134733181505e-07
dp30_seed86_zero_steps100 action_mse=3.1088134733181505e-07
dp30_seed86_zero_steps200 action_mse=3.1088134733181505e-07
fm10_zero_steps50 action_mse=3.159674690778047e-07
fm10_zero_steps100 action_mse=3.162173243254074e-07
```

Interpretation:

- Sampling-step tuning does not close the BC gap.
- DP seed86 remains the best non-BC candidate but still trails BC.
- FM10 remains worse than DP seed86 and has a higher max-window error.
- DP/FM live remains blocked.

### DP/FM Loss-Action Alignment Diagnostic

Date: 2026-05-07.

Ran a read-only diagnostic comparing training summaries against validation
action-window metrics:

```text
scripts/analyze_b8_dp_fm_loss_action_alignment.py
outputs/logs/b8_primary30_training_planning/dp_fm_loss_action_alignment.json
outputs/logs/b8_primary30_training_planning/dp_fm_loss_action_alignment.md
```

No ROS command, no hand/gripper controller, no gripper command, no training,
and no learned rollout were used by this diagnostic.

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

Key rows:

```text
dp30_seed84 best_val_loss=0.4933774649536097 action_mse=3.1285387080970395e-07
dp30_seed85 best_val_loss=0.48370392736728474 action_mse=3.1949056733537873e-07
dp30_seed86 best_val_loss=0.504732092542033 action_mse=3.1088134733181505e-07
fm10 best_val_loss=1.5957417760484962 action_mse=3.159674690778047e-07
```

Interpretation:

- Lower DP denoising validation loss did not produce lower unnormalized action
  MSE.
- Continue selecting DP/FM candidates by offline action-window metrics against
  BC, not by denoising/flow loss alone.
- Seed and sampling-step tuning are not enough to displace BC.
- DP/FM live remains blocked.

### DP Architecture Ablation Outcome

Date: 2026-05-07.

Ran one bounded offline DP architecture ablation:

```text
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86_w128.yaml
python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/train/train_diffusion.py --config src/uvms/rexrov_single_oberon7_fm_dp/config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86_w128.yaml
scripts/analyze_b8_dp_architecture_ablation_validation.py
outputs/logs/b8_primary30_training_planning/dp_architecture_ablation_validation.json
outputs/logs/b8_primary30_training_planning/dp_architecture_ablation_validation.md
outputs/logs/b8_primary30_training_planning/dp_architecture_ablation_outcome.json
outputs/logs/b8_primary30_training_planning/dp_architecture_ablation_outcome.md
```

No ROS command, no hand/gripper controller, no gripper command, and no learned
rollout were used.

Training result:

```text
dp30_seed86_w128 epochs=30 best_val_loss=0.5577844112150131 final_val_loss=0.5638075888317119
```

Validation result:

```text
bc_action_mse=3.066821534503106e-07
dp30_seed86_w256_action_mse=3.1088134733181505e-07
dp30_seed86_w128_action_mse=3.179889915827516e-07
w128_improves_over_w256=false
bc_remains_reference=true
dp_fm_live_approved=false
```

Interpretation:

- Reducing hidden width from `[256, 256, 256]` to `[128, 128, 128]` did not
  improve DP action-window metrics.
- BC remains the live reference.
- DP/FM live remains blocked.

### DP Objective Timestep Diagnostic

Date: 2026-05-07.

Ran an offline-only timestep diagnostic for the current best DP checkpoint:

```text
scripts/analyze_b8_dp_objective_timestep_diagnostic.py
outputs/logs/b8_primary30_training_planning/dp_objective_timestep_diagnostic.json
outputs/logs/b8_primary30_training_planning/dp_objective_timestep_diagnostic.md
```

No ROS command, no hand/gripper controller, no gripper command, no training,
and no learned rollout were used.

Decision:

```text
bc_reference_not_displaced_by_this_diagnostic=true
one_step_x0_diagnostic_not_policy_candidate=true
x0_error_range_ratio=1288.354547513286
objective_ablation_recommended=true
dp_fm_live_approved=false
training_started=false
```

Representative timestep metrics:

```text
t=0  epsilon_mse_norm=1.0759165661950265 x0_action_mse=6.060692225862141e-11
t=10 epsilon_mse_norm=0.7305153001860906 x0_action_mse=7.929157774810847e-09
t=20 epsilon_mse_norm=0.4632123941455477 x0_action_mse=1.722153974981211e-08
t=35 epsilon_mse_norm=0.31718284861054474 x0_action_mse=3.892042244046934e-08
t=49 epsilon_mse_norm=0.29180770487554614 x0_action_mse=7.808320390267909e-08
```

Interpretation:

- The one-step x0 diagnostic is not a policy candidate and cannot displace BC.
- Epsilon loss and action-space reconstruction error are not aligned enough
  for model selection.
- If DP continues, the next work should be offline objective/selection
  ablation; DP/FM live remains blocked.

### DP Action-Selection Outcome

Date: 2026-05-07.

Implemented and ran a bounded offline checkpoint-selection ablation. The DP
training objective remained epsilon, but validation additionally tracked
unnormalized zero-init action MSE and saved `best_action.pt`.

Files:

```text
learning/train/train_diffusion.py
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86_action_select.yaml
scripts/analyze_b8_dp_action_selection_validation.py
outputs/logs/b8_primary30_training_planning/dp_action_selection_validation.json
outputs/logs/b8_primary30_training_planning/dp_action_selection_validation.md
outputs/logs/b8_primary30_training_planning/dp_action_selection_outcome.json
outputs/logs/b8_primary30_training_planning/dp_action_selection_outcome.md
```

No ROS command, no hand/gripper controller, no gripper command, and no learned
rollout were used.

Training result:

```text
epochs=30
best_val_loss=0.5124573306611149
best_val_zero_init_action_mse=3.1140185834165647e-07
final_val_loss=0.5124573306611149
final_val_zero_init_action_mse=3.1352445272387485e-07
```

Validation result:

```text
bc_action_mse=3.066821534503106e-07
dp30_seed86_baseline_action_mse=3.1088134733181505e-07
dp30_seed86_action_select_best_loss_action_mse=3.135244526220049e-07
dp30_seed86_action_select_best_action_action_mse=3.1140186251832347e-07
action_selection_improves_over_baseline_seed86=false
action_selection_beats_bc=false
bc_remains_reference=true
dp_fm_live_approved=false
```

Interpretation:

- `best_action.pt` selected epoch 24 and improved max-window MSE relative to
  baseline DP seed86, but did not improve mean action MSE.
- Action-space checkpoint selection alone does not displace BC.
- DP/FM live remains blocked.

### DP x0 Auxiliary Objective Outcome

Date: 2026-05-07.

Implemented and ran one bounded offline objective ablation for DP. The run kept
the same base-relative safe-norm h8 xyz observation/action setup, seed86, and
width256 model, and added a normalized x0/action reconstruction auxiliary loss
with weight `0.1`. The training code also keeps action-space checkpoint
selection default-off and records `best_action.pt` when enabled.

Files:

```text
learning/train/train_diffusion.py
config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86_x0aux0p1.yaml
scripts/analyze_b8_dp_x0_aux_validation.py
outputs/logs/b8_primary30_training_planning/dp_x0_aux_validation.json
outputs/logs/b8_primary30_training_planning/dp_x0_aux_validation.md
outputs/logs/b8_primary30_training_planning/dp_x0_aux_outcome.json
outputs/logs/b8_primary30_training_planning/dp_x0_aux_outcome.md
```

No ROS command, no hand/gripper controller, no gripper command, and no learned
rollout were used.

Training result:

```text
epochs=30
x0_aux_loss_weight=0.1
best_val_loss=0.5127105430890155
best_val_zero_init_action_mse=3.110658636161854e-07
final_val_loss=0.5127105430890155
final_val_zero_init_action_mse=3.133305478014893e-07
```

Validation result:

```text
bc_action_mse=3.066821534503106e-07
dp30_seed86_baseline_action_mse=3.1088134733181505e-07
dp30_seed86_action_select_best_action_action_mse=3.1140186251832347e-07
dp30_seed86_x0aux0p1_best_loss_action_mse=3.133305597202707e-07
dp30_seed86_x0aux0p1_best_action_action_mse=3.1106586106943723e-07
dp30_seed86_x0aux0p1_dimw025_1_1_best_loss_action_mse=3.132266215288837e-07
dp30_seed86_x0aux0p1_dimw025_1_1_best_action_action_mse=3.110033617303998e-07
best_dp=dp30_seed86_baseline_best
best_dp_relative_to_bc=0.013692332058653145
x0_aux_improves_mean_action_mse_over_baseline=false
x0_aux_beats_bc=false
per_dim_x0_aux_improves_mean_action_mse_over_baseline=false
per_dim_x0_aux_beats_bc=false
bc_remains_reference=true
dp_fm_live_approved=false
```

Interpretation:

- The x0 auxiliary objective did not improve mean action MSE over the DP seed86
  baseline.
- The per-dimension weighted x0-aux candidate is slightly better than scalar
  x0-aux, but still worse than baseline DP and still worse than BC.
- BC remains the live reference.
- DP/FM live remains blocked. Further DP/FM work should remain offline-only and
  focus on objective/selection design review, not live execution.

### DP/FM Final Presentation Result Package

Date: 2026-05-07.

Generated a final presentation-ready offline comparison for BC, DP, and FM
under the same B8' primary30 base-relative safe-norm h8 xyz setup.

Additional FM work completed:

```text
learning/train/train_flow_matching.py
config/train_flow_matching_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_action_select.yaml
outputs/checkpoints/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_epoch30_action_select/best.pt
outputs/checkpoints/b8_primary30_flow_matching_h8_xyz_base_relative_safe_norm_epoch30_action_select/best_action.pt
```

The FM training objective remained flow matching. The training loop now can
optionally track zero-init action MSE and save `best_action.pt`; this is
default-off for existing configs.

Presentation artifacts:

```text
outputs/logs/b8_primary30_training_planning/dp_fm_final_presentation_results.json
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
best_overall=fm30_action_select_best_action
fm_beats_bc_offline_action_mse=true
dp_beats_bc_offline_action_mse=false
presentation_ready_offline_results=true
dp_fm_live_approved=false
```

Interpretation:

- FM action-selected `best_action.pt` gives the best offline validation action
  MSE in the presentation table, slightly better than BC.
- DP seed86 is the best DP candidate, but remains worse than BC.
- BC remains the only live-smoke-tested policy reference.
- This package is suitable for presenting offline DP/FM method results, but it
  does not approve DP/FM live and does not claim grasp or learned rollout
  success.

### DP30 Seed Ablation Training Outcome

Date: 2026-05-07.

After explicit approval, ran the two bounded offline-only DP30 seed trainings:

```text
python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/train/train_diffusion.py --config src/uvms/rexrov_single_oberon7_fm_dp/config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed85.yaml
python3 src/uvms/rexrov_single_oberon7_fm_dp/learning/train/train_diffusion.py --config src/uvms/rexrov_single_oberon7_fm_dp/config/train_diffusion_b8_primary30_h8_xyz_base_relative_safe_norm_epoch30_seed86.yaml
```

No ROS command, no hand/gripper controller, no gripper command, and no learned
rollout were used.

Training summaries:

```text
seed85 epochs=30 best_val_loss=0.48370392736728474 final_val_loss=0.5302829148388037
seed86 epochs=30 best_val_loss=0.504732092542033 final_val_loss=0.504732092542033
```

TensorBoard was disabled by the local protobuf/libstdc++ `GLIBCXX_3.4.29`
mismatch, but checkpoints and JSON summaries were written.

Validation artifacts:

```text
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.json
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_validation_windows.md
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_outcome.json
outputs/logs/b8_primary30_training_planning/dp30_seed_ablation_outcome.md
```

Validation result:

```text
bc_action_mse=3.066821534503106e-07
dp30_seed84_action_mse=3.1285387080970395e-07
dp30_seed85_action_mse=3.1949056733537873e-07
dp30_seed86_action_mse=3.1088134733181505e-07
best_dp_seed_candidate=dp30_seed86_zero
best_dp_relative_to_bc=0.013692332058653145
bc_remains_reference=true
dp_fm_live_approved=false
```

Interpretation:

- Seed86 improves over seed84, but it still does not beat the BC reference.
- BC remains the live reference.
- DP/FM live execution remains blocked.
- No grasp success, learned rollout success, or general rollout success is
  claimed.

### 2026-05-07 Live Equal-N Comparison Blocker

Aggressive live execution reached multiple shared arm-only protocol attempts
for BC / DP / FM. The gripper and hand controller stayed disabled, and the
artifacts make no grasp claim.

Artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
outputs/logs/b8_rollout_planning/bc_dp_fm_protocol_attempts_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_protocol_attempts_summary.md
```

Observed blocker pattern:

```text
v4: DP 3/3, FM 3/3, BC aborted after IK command conversion/execution failure.
v6: BC 3/3, FM 3/3, DP failed the arm-only success threshold at N=1.
v7: DP 3/3, BC/FM failed the distance-reduction threshold at N=1.
v8: full success-criterion early stop guard was implemented, but fresh pre-gate
    failed before rollout due target/base drift and initial-distance boundary.
v8 after user restart: fresh gates passed; BC missed reduction threshold, DP
    failed tiny smoke threshold after dry-run passed, FM reached 2/3.
v9 threshold095: threshold-only variant did not improve; BC failed first cycle
    and DP/FM failed tiny smoke threshold.
v10 aligned guard: fixed early-stop baseline/logging; BC re-summary passed, but
    the first run stopped before DP/FM due summarizer incompatibility with
    terminal observation rows.
v10b aligned guard: reran after summarizer fix; BC missed threshold and DP/FM
    failed tiny-smoke threshold.
```

Current blocker:

```text
No single shared protocol has produced equal-N BC/DP/FM live success rates.
The success-criterion early stop guard is now implemented. The remaining
blocker is stop/settle sensitivity around the success threshold. Do not
increase N or keep changing thresholds until the protocol defines whether
terminal early-stop observation or post-gate readback is the formal final
distance.
```

### 2026-05-07 Blocker Resolved For N=3 Live Comparison

Resolution:

```text
formal_final_distance_source=terminal_observation
success=formal_final_distance<=0.10 and formal_distance_reduction>0.02
```

After fixing terminal early-stop logging, `pre_gate_1` baseline alignment, and
summary handling for terminal rows, the shared v11 protocol completed:

```text
BC 3/3
DP 3/3
FM 3/3
complete_three_method_live_comparison=true
equal_N_across_methods=true
```

Artifacts:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v11_terminal_final_distance.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v11_terminal_final_distance.md
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.json
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary.md
```

Remaining extension blocker:

```text
N=5 is partial only. BC and DP completed 5/5, but FM has one incomplete cycle
artifact after the interrupted/hung extension. Use N=3 as the fair final table.
```

### 2026-05-07 N=10 Extension Completed

The N=5 extension blocker was bypassed by a fresh clean N=10 run after fixing a
package-local return-to-reference tooling issue.

Failure artifact retained:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v12_terminal_final_distance_n10_interrupted.json
failure=BC return_to_reference_failed before rollout
root_cause=return tool waited for command subscriber before checking already-at-reference state
```

Fix:

```text
return_left_arm_to_reference.py now reads /joint_states first and exits
successfully if already within reference tolerance; it waits for the arm command
subscriber only when it actually needs to publish an arm command.
```

Clean result:

```text
outputs/logs/b8_rollout_planning/bc_dp_fm_success_rate_summary_v12b_terminal_final_distance_n10.json
BC 10/10
DP 10/10
FM 10/10
abort_count=0
no_gripper_command_observed=true
```
