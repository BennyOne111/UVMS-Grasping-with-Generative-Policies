# Stage Progress

## Current Route Alignment: B5d' To B8'

Status: documented on 2026-05-04.

This is not a new stage. It records the current route after the B5d' debug
smoke work:

```text
arm-only reaching / pre-grasp demo
-> B5d': scripted expert drives left arm toward static/base-relative target
-> B8': small real non-fallback reaching/pre-grasp demonstrations
-> retrain BC / DP / FM
-> real arm-only rollout evaluation
```

B5d' is debug-smoke minimal resolved. The scripted expert can issue repeated
small bounded left-arm commands with gripper disabled through:

```text
EE-delta -> IK/joint target -> /oberon7/arm_position_l/command
```

This result is not grasping, not a learned-policy rollout, and not a success
rate evaluation. Historical Stage 0-12 records below are preserved as history.
Stage 6 fallback data remains pipeline-smoke data only.

B8' next:

- collect 5 short real non-fallback arm-only reaching/pre-grasp episodes;
- require live odom, joint states, Gazebo target state, and eef pose;
- record distance metrics and validator result for every episode;
- keep gripper disabled and record `is_grasp_dataset=false`.

## Stage 0: Project Initialization And Documentation Center

Status: completed on 2026-04-29.

Completed:

- Confirmed workspace root at `/home/benny/uuv_manipulator_ws`.
- Read root project map: `docs/PROJECT_MAP_FOR_DP_FM.md`.
- Confirmed `src/uvms/rexrov_single_oberon7_fm_dp` did not exist before this stage.
- Created ROS package `rexrov_single_oberon7_fm_dp` under `src/uvms`.
- Created package directory structure:
  - `docs`
  - `launch`
  - `config`
  - `scripts`
  - `src/rexrov_single_oberon7_fm_dp`
  - `learning/datasets`
  - `learning/models`
  - `learning/train`
  - `learning/eval`
  - `data/raw`
  - `data/processed`
  - `outputs/checkpoints`
  - `outputs/logs`
  - `outputs/eval`
- Created initial documentation center.
- Added Python package marker at `src/rexrov_single_oberon7_fm_dp/__init__.py`.
- Updated package metadata description and catkin dependency export.

Created docs:

- `PROJECT_CONTEXT.md`
- `CODEX_GUIDE.md`
- `TASK_DEFINITION.md`
- `DATASET_SCHEMA.md`
- `TOPIC_MAP_RUNTIME.md`
- `EXPERT_POLICY_PLAN.md`
- `DATA_COLLECTION_LOG.md`
- `TRAINING_PLAN.md`
- `EXPERIMENT_LOG.md`
- `TODO.md`
- `STAGE_PROGRESS.md`

Verification:

- `catkin build rexrov_single_oberon7_fm_dp` succeeded.
- After re-sourcing `devel/setup.bash`, `rospack find rexrov_single_oberon7_fm_dp` resolved to:

  ```text
  /home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp
  ```

## Next Stage

Stage 1 should only begin after re-reading `./docs` and this package's `docs`.

Recommended next focus:

- Identify the safest RexROV + dual Oberon7 launch path to wrap.
- Confirm runtime topics/controllers/joint names with short ROS checks.
- Check current MoveIt viability before choosing a MoveIt-based expert.

Do not implement recorder, expert policy, BC, Diffusion Policy, or Flow Matching Policy in stage 0.

## Stage 1: Static Existing-Project Map For Single Active Left Arm

Status: completed on 2026-04-29.

Completed:

- Re-read root docs and all package docs before stage work.
- Ran the requested static package/file discovery:
  - `find src/uvms -maxdepth 3 -name package.xml -print`
  - `find src/uvms -maxdepth 4 -type f \( -name "*.launch" -o -name "*.py" -o -name "*.yaml" -o -name "*.xacro" \)`
- Inspected the requested packages:
  - `data_rexrov_dual_oberon7`
  - `rexrov_data`
  - `oberon7_data`
  - `uvms_control`
  - `rexrov_moveit_revised`
  - `oberon7_moveit_revised`
  - `oberon7_effort_utils`
  - `rexrov_nmpc_controller_plugin`
- Read-only checked DAVE/RexROV/Oberon7 xacro and object/world files needed for static mapping.
- Did not launch Gazebo.
- Did not implement recorder, expert policy, BC, Diffusion Policy, or Flow Matching Policy.
- Did not modify official or third-party packages.

Key findings:

- First-version launch reference should be `data_rexrov_dual_oberon7/launch/rexrov_dual_oberon7.launch`.
- Static active-left arm joint names are `oberon7_l/azimuth`, `oberon7_l/shoulder`, `oberon7_l/elbow`, `oberon7_l/roll`, `oberon7_l/pitch`, `oberon7_l/wrist`.
- Static left gripper joint names are `oberon7_l/finger_left_joint`, `oberon7_l/finger_tip_left_joint`, `oberon7_l/finger_right_joint`, `oberon7_l/finger_tip_right_joint`.
- MoveIt groups `base`, `arm_l`, `arm_r`, `hand_l`, and `hand_r` exist in revised SRDF.
- Existing left-arm MoveIt script uses `MoveGroupCommander("arm_l")`, `oberon7_l/end_effector`, and `/compute_ik`.
- `simple_moveit_controllers.yaml` has an empty `controller_list`, and `ros_controllers.yaml` is empty, so real trajectory execution is not confirmed.
- `rexrov_nmpc_controller_plugin` is not first-version ready because its build/install logic is commented out and package export references a plugin XML filename that does not exist.

Docs updated in stage 1:

- `PROJECT_CONTEXT.md`
- `TOPIC_MAP_RUNTIME.md`
- `EXPERT_POLICY_PLAN.md`
- `STAGE_PROGRESS.md`

Next stage recommendation:

- Start with short runtime checks only.
- Launch the selected RexROV + dual Oberon7 setup if explicitly requested.
- Confirm active topics, controller manager state, joint names from live `/joint_states`, and MoveIt `/compute_ik` before implementing any recorder or expert.

## Stage 2: Runtime Topic, Controller, And MoveIt Availability Check

Status: completed on 2026-04-29.

Completed:

- Re-read root docs and all package docs before stage work.
- Selected a minimal runtime launch from Stage 1 candidates:

  ```bash
  roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=true
  ```

- Started Gazebo without GUI and without the existing dual-arm data collector.
- Ran the requested read-only ROS graph checks:
  - `rostopic list`
  - `rosparam list`
  - `rosservice list`
  - `rostopic info /joint_states`
  - `rostopic info /rexrov/pose_gt`
  - `rostopic info /rexrov/thruster_manager/input`
  - `rostopic info /gazebo/model_states`
- Briefly unpaused physics to collect one sample from `/joint_states`, `/rexrov/pose_gt`, `/gazebo/model_states`, and `/clock`, then paused physics again.
- Checked `/rexrov/joint_states`; it was not present.
- Loaded MoveIt planning context and started `move_group` with trajectory execution disabled.
- Queried `MoveGroupCommander` groups without sending any planning execution or joint command.
- Did not implement recorder, expert policy, BC, Diffusion Policy, or Flow Matching Policy.
- Did not modify official or third-party packages.

Confirmed:

- Base state topic: `/rexrov/pose_gt` (`nav_msgs/Odometry`), published by `/gazebo`.
- Joint state topic: `/joint_states` (`sensor_msgs/JointState`), published by `/gazebo`.
- `/rexrov/joint_states` is not present in the minimal launch.
- Base command topics:
  - `/rexrov/thruster_manager/input` (`geometry_msgs/Wrench`)
  - `/rexrov/thruster_manager/input_stamped` (`geometry_msgs/WrenchStamped`)
- Target pose source:
  - `/gazebo/model_states` is present.
  - `/gazebo/get_model_state` service is present.
  - The minimal launch loaded only `ocean_box` and `rexrov`, so no grasp target object exists yet.
- Runtime active-left arm joint names:
  - `oberon7_l/azimuth`
  - `oberon7_l/shoulder`
  - `oberon7_l/elbow`
  - `oberon7_l/roll`
  - `oberon7_l/pitch`
  - `oberon7_l/wrist`
- Runtime left gripper joint names:
  - `oberon7_l/finger_left_joint`
  - `oberon7_l/finger_tip_left_joint`
  - `oberon7_l/finger_right_joint`
  - `oberon7_l/finger_tip_right_joint`
- MoveIt groups:
  - `arm_l`
  - `arm_r`
  - `base`
  - `hand_l`
  - `hand_r`
- Valid active-arm MoveIt group: `arm_l`.
- Invalid group name: `left_arm`.
- `arm_l` end-effector link: `oberon7_l/end_effector`.
- `/compute_ik` exists after `move_group` starts and uses service type `moveit_msgs/GetPositionIK`.

Important issues:

- `/joint_states.name` runtime order differs from the semantic arm/controller order. Future code must index joints by name.
- `MoveGroupCommander` read-only query timed out while Gazebo physics was paused; it succeeded after `/clock` advanced.
- `move_group` warned that complete robot state was not known, including `world_to_base` and several fixed/sensor joints.
- `move_group` reported `No controller_list specified` and returned zero controllers.
- Minimal launch exposed no left-arm command/action topics matching `oberon7`, `arm_position`, `joint_group`, `hand_position`, `hand_effort`, or `follow_joint`.
- `/controller_manager/list_controllers` did not return during this check, despite controller manager services appearing in `rosservice list`.
- Launch output showed `joint_state_controller` loaded successfully but the arm controller spawner could not find the expected controller manager interface.

Docs updated in stage 2:

- `TOPIC_MAP_RUNTIME.md`
- `EXPERT_POLICY_PLAN.md`
- `TASK_DEFINITION.md`
- `STAGE_PROGRESS.md`

Next stage recommendation:

- Do not implement policy training yet.
- First resolve the left-arm command interface:
  - identify whether another launch spawns `arm_position_l`, `joint_group_arm_l_position_controller`, or trajectory controllers correctly;
  - verify controller manager responsiveness;
  - confirm a safe command topic for holding/right-arm-static and left-arm movement.
- Add a project-local launch/world wrapper for a simple target object rather than modifying DAVE or other official packages.
- Use MoveIt only as an IK/planning component until trajectory execution controllers are confirmed.

## Stage 3: State-Based Data Schema And Config Files

Status: completed on 2026-04-29.

Completed:

- Re-read root docs and all package docs before stage work.
- Created first-version YAML configuration files:
  - `config/data_collection.yaml`
  - `config/topics.yaml`
  - `config/task_grasp.yaml`
  - `config/active_joints_left_arm.yaml`
- Updated `docs/DATASET_SCHEMA.md` with:
  - one-episode-per-`.npz` storage rule;
  - required and optional `.npz` keys;
  - shapes, units, and coordinate-frame conventions;
  - active-left joint and gripper ordering;
  - metadata requirements including `active_arm` and `robot_mode`;
  - first-version policy action definition;
  - validation requirements.
- Ran a short PyYAML parse check for all four config files.
- Did not implement recorder, expert policy, BC, Diffusion Policy, or Flow Matching Policy.
- Did not launch Gazebo.
- Did not modify official or third-party packages.

Config defaults defined:

- `save_format: npz`
- `use_images: false`
- `active_arm: left`
- `robot_mode: dual_model_single_active_left_arm`
- `rate_hz: 10.0`
- `max_duration_sec: 60.0`
- policy action:

  ```text
  [dx, dy, dz, droll, dpitch, dyaw, gripper_cmd]
  action_dim = 7
  ```

Runtime topic defaults from Stage 2:

- `base_odom_topic: /rexrov/pose_gt`
- `joint_states_topic: /joint_states`
- `base_wrench_topic: /rexrov/thruster_manager/input`
- `model_states_topic: /gazebo/model_states`
- `get_model_state_service: /gazebo/get_model_state`
- `moveit.active_arm_group: arm_l`
- `moveit.gripper_group: hand_l`
- `moveit.eef_link: oberon7_l/end_effector`

Known unresolved fields:

- `arm_command_topic: ""` in ROS/YAML config, serialized as `null` in episode metadata
- `gripper_command_topic: ""` in ROS/YAML config, serialized as `null` in episode metadata
- action frame remains `eef_or_task_frame_to_be_confirmed`
- target object launch/spawn is not implemented; `target_model_name` currently defaults to `cylinder_target`

Verification:

```text
data_collection.yaml: ok (dict)
topics.yaml: ok (dict)
task_grasp.yaml: ok (dict)
active_joints_left_arm.yaml: ok (dict)
```

Docs updated in stage 3:

- `DATASET_SCHEMA.md`
- `STAGE_PROGRESS.md`
- `TODO.md`

Next stage recommendation:

- Implement a schema-aware episode recorder only after choosing how to handle missing optional fields such as `eef_pose`.
- Keep recorder config-driven and index `/joint_states` by name.
- Before rollout/expert execution, resolve the left-arm and gripper command topics.
- Add a project-local target-object launch/world wrapper instead of editing DAVE assets.

## Stage 4: Episode Recorder And Validator

Status: completed on 2026-04-29.

Completed:

- Re-read root docs and all package docs before stage work.
- Implemented first state-based episode recorder.
- Implemented offline `.npz` validator.
- Added ROS launch entry for recording one episode.
- Added package Python setup and script install rules.
- Added `gazebo_msgs` package dependency for `/gazebo/model_states`.
- Built the updated package successfully with `catkin build rexrov_single_oberon7_fm_dp`.
- Ran offline synthetic validator self-test.
- Ran a short real ROS/Gazebo smoke test and produced a valid episode file.
- Did not implement expert policy, BC, Diffusion Policy, Flow Matching Policy, or rollout evaluation.
- Did not modify official or third-party packages.

Files added:

- `setup.py`
- `src/rexrov_single_oberon7_fm_dp/dataset_writer.py`
- `src/rexrov_single_oberon7_fm_dp/ros_interface.py`
- `src/rexrov_single_oberon7_fm_dp/recorder.py`
- `scripts/dp_fm_episode_recorder.py`
- `scripts/validate_episode.py`
- `launch/record_episode.launch`

Files updated:

- `CMakeLists.txt`
- `package.xml`
- `config/topics.yaml`
- `docs/DATASET_SCHEMA.md`
- `docs/DATA_COLLECTION_LOG.md`
- `docs/STAGE_PROGRESS.md`
- `docs/TODO.md`

Recorder behavior:

- Subscribes to `/rexrov/pose_gt`, `/joint_states`, `/gazebo/model_states`, and optional base wrench command topics.
- Samples at fixed `rate_hz`.
- Extracts active-left arm and left gripper values by joint name.
- Saves one `.npz` episode plus a sidecar `.metadata.json`.
- Includes `metadata_json` inside the `.npz`.
- Does not record the right arm as an active observation/action.

Validator checks:

- required keys exist
- `metadata_json` parses
- metadata has `active_arm=left`
- metadata has `robot_mode=dual_model_single_active_left_arm`
- `use_images=false`
- time dimension `T` is consistent
- timestamps are monotonic nondecreasing
- shapes match schema
- observed numeric arrays contain no NaN/Inf
- `done[-1] == true`
- `success` scalar matches metadata

Unavailable-field handling:

- `target_pose`, `eef_pose`, `relative_target_to_eef`, `action_ee_delta`, and `raw_command` may contain `NaN` only when metadata marks them unavailable.
- The validator reports those cases as warnings, not failures.
- This avoids fabricating target/eef/action data before the target wrapper, TF/eef lookup, and action converter are implemented.

Smoke-test output:

```text
/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage4_smoke_runtime.npz
/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage4_smoke_runtime.metadata.json
```

Smoke-test validation:

```text
validation: PASS
T: 2
success: False
unavailable_fields: ['target_pose', 'eef_pose', 'relative_target_to_eef', 'action_ee_delta', 'raw_command']
```

Known limitations:

- The minimal launch still does not spawn `cylinder_target`, so `target_pose` is unavailable in the smoke episode.
- `eef_pose` and `relative_target_to_eef` are not computed yet.
- `action_ee_delta` is shape-correct but unavailable; an expert action converter is still required before training BC/DP/FM.
- `raw_command` was unavailable in the smoke test because no base wrench command publisher was active.
- Left-arm and gripper command topics remain unresolved for rollout/expert execution.

Next stage recommendation:

- Add project-local target spawn/world wrapper and verify `target_pose` becomes finite.
- Add TF or MoveIt-based `eef_pose` lookup.
- Implement an action converter for scripted/IK expert deltas.
- Resolve and test left-arm/gripper command topics before collecting learning episodes.

## Stage 5: First Scripted Expert Policy

Status: completed on 2026-04-29.

Completed:

- Re-read root docs and all package docs before stage work.
- Chose scripted fallback expert instead of MoveIt execution because Stage 2 showed MoveIt execution controllers are not configured.
- Implemented project-local expert action labels.
- Added a package-local simple cylinder target SDF model.
- Added `collect_episode.launch` that can spawn the target, run scripted expert, and run recorder together.
- Extended recorder to subscribe to expert action and success topics.
- Generated a Stage 5 scripted expert episode.
- Validated the generated episode successfully.
- Did not implement BC, Diffusion Policy, Flow Matching Policy, or rollout evaluation.
- Did not modify official or third-party packages.

Files added:

- `models/cylinder_target/model.sdf`
- `src/rexrov_single_oberon7_fm_dp/action_converter.py`
- `src/rexrov_single_oberon7_fm_dp/expert_policy.py`
- `src/rexrov_single_oberon7_fm_dp/success_checker.py`
- `scripts/scripted_expert.py`
- `launch/collect_episode.launch`

Files updated:

- `CMakeLists.txt`
- `config/topics.yaml`
- `config/task_grasp.yaml`
- `src/rexrov_single_oberon7_fm_dp/recorder.py`
- `docs/EXPERT_POLICY_PLAN.md`
- `docs/TASK_DEFINITION.md`
- `docs/DATA_COLLECTION_LOG.md`
- `docs/STAGE_PROGRESS.md`
- `docs/TODO.md`

Expert state machine:

```text
WAIT_FOR_STATE
MOVE_TO_PREGRASP
MOVE_TO_GRASP
CLOSE_GRIPPER
LIFT_OR_HOLD
FINISH
```

Published expert topics:

```text
/rexrov_single_oberon7_fm_dp/expert/action_ee_delta
/rexrov_single_oberon7_fm_dp/expert/state
/rexrov_single_oberon7_fm_dp/expert/success
```

Smoke-test command:

```bash
roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=false
roslaunch rexrov_single_oberon7_fm_dp collect_episode.launch \
  output_dir:=/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw \
  episode_id:=stage5_scripted_expert_smoke_v2 \
  rate_hz:=2.0 \
  max_duration_sec:=5.0 \
  spawn_target:=true
```

Smoke-test output:

```text
/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage5_scripted_expert_smoke_v2.npz
/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage5_scripted_expert_smoke_v2.metadata.json
```

Smoke-test validation:

```text
validation: PASS
T: 10
success: False
unavailable_fields: ['eef_pose', 'relative_target_to_eef', 'raw_command']
```

Recorded availability:

- `target_pose`: finite
- `action_ee_delta`: finite
- `eef_pose`: unavailable
- `relative_target_to_eef`: unavailable
- `raw_command`: unavailable

Verification:

- Python syntax check passed.
- YAML config parse passed.
- XML syntax check passed for `model.sdf` and `collect_episode.launch`.
- `catkin build rexrov_single_oberon7_fm_dp` passed.
- Validator passed on the Stage 5 expert episode.

Known limitations:

- Scripted expert currently generates action labels only; it does not move the real left arm.
- Success remains false because `eef_pose` is unavailable and the distance-based success checker cannot evaluate a grasp.
- Left-arm and gripper command topics still need runtime confirmation before physical rollout.
- The expert timed out at the configured smoke-test `max_duration_sec`; this is acceptable for short validation but a full collection episode should use the default longer duration.

Next stage recommendation:

- Add TF/MoveIt end-effector pose lookup to recorder and success checker.
- Confirm and test left-arm/gripper command topics.
- Convert scripted EE delta labels into actual controller commands once command topics are confirmed.
- Collect a tiny multi-episode dataset only after action labels and target/eef fields are finite.

## Stage 6: Batch Demonstration Dataset

Status: completed on 2026-05-01 with explicit fallback limitations.

Completed:

- Re-read root docs and all package docs before stage work.
- Added batch collection configuration.
- Added batch collector script.
- Added dataset summarizer script.
- Added a combined train/val split for the first 20-episode debug set.
- Ran a 5-episode smoke collection.
- Ran and completed a 20-episode debug collection.
- Validated all 20 debug episodes with the existing episode validator through `summarize_dataset.py`.
- Did not implement BC, Diffusion Policy, Flow Matching Policy, or rollout evaluation.
- Did not modify official or third-party packages.

Files added:

- `config/batch_collection.yaml`
- `scripts/batch_collect_episodes.py`
- `scripts/summarize_dataset.py`

Files updated:

- `CMakeLists.txt`
- `config/topics.yaml`
- `launch/collect_episode.launch`
- `src/rexrov_single_oberon7_fm_dp/expert_policy.py`
- `src/rexrov_single_oberon7_fm_dp/recorder.py`
- `src/rexrov_single_oberon7_fm_dp/ros_interface.py`
- `docs/DATA_COLLECTION_LOG.md`
- `docs/DATASET_SCHEMA.md`
- `docs/EXPERIMENT_LOG.md`
- `docs/STAGE_PROGRESS.md`
- `docs/TODO.md`

Runtime blockers observed:

- `/rexrov/pose_gt` was not reliably available in this session.
- `/gazebo/model_states` and `/joint_states` topics existed, but the recorder/expert did not reliably receive live samples.
- `gazebo_ros/spawn_model` could block on `/gazebo/spawn_sdf_model`.
- Repeated `/gazebo/unpause_physics` and `/gazebo/delete_model` service calls could also block.

Stage 6 fallback used:

```text
spawn_target: false
allow_nominal_state_fallback: true
base_state_source: nominal_base_state_fallback
joint_state_source: zero_joint_state_fallback
target_state_source: nominal_target_pose_fallback
```

Dataset outputs:

```text
5-episode smoke:
/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage6_smoke

20-episode debug:
/home/benny/uuv_manipulator_ws/src/uvms/rexrov_single_oberon7_fm_dp/data/raw/stage6_debug
```

Debug summary:

```text
episodes_total: 20
episodes_valid: 20
episodes_invalid: 0
success_rate: 0.0
mean_T: 10.0
action_ee_delta available: 20/20
target_pose available: 20/20
eef_pose unavailable: 20/20
relative_target_to_eef unavailable: 20/20
raw_command unavailable: 20/20
```

Summary and split files:

```text
outputs/logs/stage6_debug/dataset_summary.json
outputs/logs/stage6_debug/dataset_summary.md
outputs/logs/stage6_debug/dataset_split_combined.json
```

Verification:

- Python syntax checks passed.
- YAML config parse checks passed.
- XML syntax check passed for `collect_episode.launch`.
- `catkin build rexrov_single_oberon7_fm_dp` passed.
- `summarize_dataset.py` reported 20 valid and 0 invalid debug episodes.

Known limitations:

- This is a schema/debug dataset for downstream loader and training-loop smoke tests.
- It is not a real grasp demonstration dataset because live joint/base/target sampling fell back to nominal values.
- Success remains false because `eef_pose` is unavailable and no real grasp execution occurs.

Next stage recommendation:

- Before using this data for meaningful policy comparison, fix the runtime state pipeline:
  - restore live `/joint_states` samples;
  - restore or replace `/rexrov/pose_gt`;
  - make target spawn deterministic or use a stable world wrapper;
  - confirm left-arm and gripper command topics.
- Stage 7 may still start with a BC loader/training smoke test using this fallback dataset, but results must be treated only as code-path validation.

## Stage 7: Dataset Loader And BC Baseline

Status: completed on 2026-05-01 as a fallback-dataset pipeline smoke test.

Completed:

- Re-read root docs and all package docs before stage work.
- Added first-version state-based episode dataset loader.
- Added a small MLP BC policy.
- Added BC training script with YAML config support, normalization statistics,
  checkpoint saving, and masked action-chunk loss.
- Added offline evaluator that reports MSE and writes predicted-vs-expert plots.
- Used the Stage 6 fallback debug split for a smoke training run.
- Did not implement Diffusion Policy, Flow Matching Policy, or rollout
  evaluation.
- Did not modify official or third-party packages.

Files added:

- `config/train_bc.yaml`
- `learning/datasets/__init__.py`
- `learning/datasets/uvms_episode_dataset.py`
- `learning/models/__init__.py`
- `learning/models/bc_policy.py`
- `learning/train/__init__.py`
- `learning/train/train_bc.py`
- `learning/eval/__init__.py`
- `learning/eval/eval_offline.py`

Files updated:

- `docs/TRAINING_PLAN.md`
- `docs/EXPERIMENT_LOG.md`
- `docs/STAGE_PROGRESS.md`
- `docs/TODO.md`

Dataset loader verification:

```text
train_samples: 112
val_samples: 28
obs_dim: 38
action_dim: 7
obs_horizon: 4
action_horizon: 16
first_sample_action_mask_valid: 7
```

BC training verification:

```text
epochs: 120
device: cuda
initial train_loss: 0.42980525
final train_loss: 0.04464374
best val_loss: 0.09266304
final val_loss: 0.09374733
```

Offline evaluation:

```text
train normalized_mse: 0.05121726
train action_mse: 0.00359283
val normalized_mse: 0.09266304
val action_mse: 0.00643590
```

Output artifacts:

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

Known limitations:

- Stage 7 used the Stage 6 nominal fallback dataset. It verifies code paths but
  is not evidence of real grasp learning.
- TensorBoard import failed in the active Anaconda environment because
  `google.protobuf` required `GLIBCXX_3.4.29`. The trainer now falls back to a
  no-op writer and still writes checkpoints and JSON summaries.
- `eef_pose`, `relative_target_to_eef`, and real arm/gripper command execution
  remain unresolved.

Next stage recommendation:

- Keep the Stage 7 loader/statistics/checkpoint format as the common base for
  Diffusion Policy and Flow Matching Policy.
- Before serious policy comparison, collect a real live-state dataset by fixing
  `/joint_states`, `/rexrov/pose_gt`, target spawn, and command interfaces.

## Stage 8: Diffusion Policy

Status: completed on 2026-05-01 as a fallback-dataset pipeline smoke test.

Completed:

- Re-read root docs and all package docs before stage work.
- Added first-version state-based Diffusion Policy.
- Added a small conditional MLP denoiser with sinusoidal timestep embedding.
- Added DDPM-style epsilon-prediction training with masked valid action steps.
- Added Gaussian-noise sampling with configurable denoising steps.
- Added diffusion training config using the same Stage 6 debug split and
  observation/action representation as BC.
- Extended offline eval to support both BC and Diffusion Policy.
- Verified the expanded evaluator still supports the Stage 7 BC checkpoint.
- Did not implement Flow Matching Policy or rollout evaluation.
- Did not modify official or third-party packages.

Files added:

- `config/train_diffusion.yaml`
- `learning/models/diffusion_policy.py`
- `learning/train/train_diffusion.py`

Files updated:

- `learning/eval/eval_offline.py`
- `docs/TRAINING_PLAN.md`
- `docs/EXPERIMENT_LOG.md`
- `docs/STAGE_PROGRESS.md`
- `docs/TODO.md`

Model settings:

```text
condition: obs_history [B, 4, 38]
target: action_chunk [B, 16, 7]
denoiser: conditional MLP [256, 256, 256]
time_embed_dim: 64
num_diffusion_steps: 50
num_inference_steps: 50
```

Training verification:

```text
train_samples: 112
val_samples: 28
device: cuda
epochs: 160
initial train_loss: 1.03681373
final train_loss: 0.32737366
best val_loss: 0.30106574
final val_loss: 0.35403574
```

Offline evaluation:

```text
train normalized_mse: 0.77574102
train action_mse: 0.14291643
val normalized_mse: 0.76420820
val action_mse: 0.13530311
```

Output artifacts:

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

Known limitations:

- Stage 8 used the Stage 6 nominal fallback dataset. It verifies diffusion code
  paths but is not evidence of real grasp learning.
- Sampling MSE is higher than BC on this small deterministic fallback dataset;
  this should not be treated as a final policy comparison.
- TensorBoard remains disabled in this environment because the active protobuf
  extension requires `GLIBCXX_3.4.29`; JSON summaries and checkpoints are valid.
- `eef_pose`, `relative_target_to_eef`, and real arm/gripper command execution
  remain unresolved.

Next stage recommendation:

- Implement Flow Matching Policy using the same loader, split, normalization
  statistics, action mask handling, and comparable model capacity.
- For meaningful BC/DP/FM comparison, first fix live runtime data collection and
  collect a real non-fallback demonstration dataset.

## Stage 9: Flow Matching Policy

Status: completed on 2026-05-01 as a fallback-dataset pipeline smoke test.

Completed:

- Re-read root docs and all package docs before stage work.
- Added first-version state-based Flow Matching Policy.
- Added a small conditional MLP velocity field with sinusoidal timestep
  embedding.
- Added rectified-flow training with `x0 ~ N(0,I)`, `x1=action_chunk`, and
  masked velocity MSE.
- Added Euler ODE sampling from `t=0` to `t=1` with configurable `ode_steps`.
- Added flow matching training config using the same Stage 6 debug split and
  observation/action representation as BC and Diffusion Policy.
- Extended offline eval to support BC, Diffusion Policy, and Flow Matching
  Policy.
- Verified the expanded evaluator still supports the Stage 7 BC and Stage 8
  Diffusion checkpoints.
- Did not implement rollout evaluation.
- Did not modify official or third-party packages.

Files added:

- `config/train_flow_matching.yaml`
- `learning/models/flow_matching_policy.py`
- `learning/train/train_flow_matching.py`

Files updated:

- `learning/eval/eval_offline.py`
- `docs/TRAINING_PLAN.md`
- `docs/EXPERIMENT_LOG.md`
- `docs/STAGE_PROGRESS.md`
- `docs/TODO.md`

Model settings:

```text
condition: obs_history [B, 4, 38]
target: action_chunk [B, 16, 7]
velocity field: conditional MLP [256, 256, 256]
time_embed_dim: 64
time_scale: 1000.0
ode_steps: 50
```

Training verification:

```text
train_samples: 112
val_samples: 28
device: cuda
epochs: 160
initial train_loss: 1.44762514
final train_loss: 0.49487846
best val_loss: 0.39671761
final val_loss: 0.50331438
```

Offline evaluation:

```text
train normalized_mse: 0.36070445
train action_mse: 0.09820177
val normalized_mse: 0.35701191
val action_mse: 0.08730043
```

Output artifacts:

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

Known limitations:

- Stage 9 used the Stage 6 nominal fallback dataset. It verifies flow matching
  code paths but is not evidence of real grasp learning.
- TensorBoard remains disabled in this environment because the active protobuf
  extension requires `GLIBCXX_3.4.29`; JSON summaries and checkpoints are valid.
- `eef_pose`, `relative_target_to_eef`, and real arm/gripper command execution
  remain unresolved.

Next stage recommendation:

- Add a shared comparison/evaluation summary across BC, Diffusion Policy, and
  Flow Matching Policy using the generated offline eval JSON files.
- For meaningful rollout evaluation, first fix live runtime data collection and
  confirm left-arm/gripper command interfaces.

## Stage 10: Rollout Policy Node And Unified Evaluation

Status: completed on 2026-05-01 as a safe dry-run rollout/evaluation layer.

Completed:

- Re-read root docs and all package docs before stage work.
- Added a shared policy runtime loader for BC, Diffusion Policy, and Flow
  Matching Policy checkpoints.
- Added a ROS rollout node that subscribes to recorder-compatible observation
  topics, maintains an observation-history buffer, loads checkpoint
  normalization statistics, and generates future action chunks.
- Added action clipping and status reporting.
- Added a rollout launch file.
- Added unified dry-run rollout evaluation across BC, Diffusion Policy, and
  Flow Matching Policy.
- Built the package successfully.
- Did not enable real arm/gripper command execution because the command
  interface remains unconfirmed.
- Did not modify official or third-party packages.

Files added:

- `config/eval_rollout.yaml`
- `learning/eval/policy_runtime.py`
- `learning/eval/eval_rollout.py`
- `scripts/rollout_policy_node.py`
- `launch/rollout_policy.launch`

Files updated:

- `CMakeLists.txt`
- `docs/EXPERIMENT_LOG.md`
- `docs/TRAINING_PLAN.md`
- `docs/TASK_DEFINITION.md`
- `docs/STAGE_PROGRESS.md`
- `docs/TODO.md`

Rollout node behavior:

```text
input topics:
  /rexrov/pose_gt
  /joint_states
  /gazebo/model_states

output topics:
  /rexrov_single_oberon7_fm_dp/policy/action_ee_delta
  /rexrov_single_oberon7_fm_dp/policy/status
```

Safety behavior:

- `execute_actions=false` by default.
- Stage 10 publishes action labels only; it does not send low-level arm or
  gripper commands.
- If `execute_actions=true` is requested, the node logs a warning and keeps real
  execution disabled.
- Linear, angular, and gripper action clipping is applied before publishing.

Unified dry-run evaluation:

```text
policy          loaded  generated  success_rate   final_distance  mean_latency_ms  smoothness
BC              true    true       not_evaluated  unavailable     8.451            0.186389
Diffusion       true    true       not_evaluated  unavailable     65.826           0.378986
Flow Matching   true    true       not_evaluated  unavailable     14.478           0.369584
```

Output artifacts:

```text
outputs/eval/stage10_rollout/rollout_eval_summary.json
outputs/eval/stage10_rollout/rollout_eval_summary.md
```

Verification:

- Python syntax checks passed.
- `config/eval_rollout.yaml` parsed successfully.
- `launch/rollout_policy.launch` parsed as XML.
- `eval_rollout.py` loaded all three checkpoints and generated clipped action
  chunks.
- `catkin build rexrov_single_oberon7_fm_dp` passed.

Known limitations:

- No real Gazebo arm rollout was executed in Stage 10.
- Success rate and final distance are unavailable because `eef_pose` is not yet
  available and no real controller command path is confirmed.
- The Stage 6 fallback dataset remains unsuitable for real policy-quality
  conclusions.

Next stage recommendation:

- Resolve and test left-arm and gripper command interfaces.
- Add TF or MoveIt-based `eef_pose` lookup.
- Add a real action converter from EE delta to IK/joint command.
- Re-run Stage 10 rollout against live non-fallback Gazebo episodes only after
  those interfaces are confirmed.

## Stage 11: Ablation And Comparison Experiments

Status: completed on 2026-05-01 as an offline report over existing Stage 6-10
artifacts.

Completed:

- Re-read root docs and all package docs before stage work.
- Added a reproducible ablation/report config.
- Added an offline ablation report generator.
- Produced a BC / Diffusion Policy / Flow Matching comparison table.
- Produced a DP inference-step ablation for `num_inference_steps = 5, 10, 20`.
- Produced a Flow Matching ODE-step ablation for `ode_steps = 2, 4, 8, 16`.
- Produced action MSE, latency, action smoothness, and success-rate-status
  plots.
- Recorded planned but not-run ablations for larger data volumes, alternate
  action horizons, and ocean-current disturbance settings.
- Did not modify official or third-party packages.
- Did not run Gazebo, long training, or disturbance simulation.

Files added:

- `config/ablation_report.yaml`
- `learning/eval/ablation_report.py`

Generated artifacts:

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

Key result:

```text
BC              val_action_mse=0.006436  dry_run_latency_ms=8.451
Diffusion       val_action_mse=0.135303  dry_run_latency_ms=65.826
Flow Matching   val_action_mse=0.087300  dry_run_latency_ms=14.478
```

DP vs FM conclusion:

- On the Stage 6 fallback validation split, Flow Matching is better than
  Diffusion Policy on offline action MSE and dry-run latency.
- This conclusion is limited to the current fallback-data pipeline. It must not
  be reported as a real underwater grasping success-rate result.

Verification:

- `learning/eval/ablation_report.py` passed Python syntax checks.
- `config/ablation_report.yaml` parsed successfully.
- The report generator completed and wrote all Stage 11 artifacts.

Known limitations:

- Only the `20 episodes` data-volume setting is available.
- Only `action_horizon=16` has trained BC/DP/FM checkpoints.
- Success rate and final distance remain unavailable because Stage 10 was a
  safe dry-run without real controller execution.
- Disturbance ablation is deferred until Project DAVE ocean-current
  configuration is verified from official documentation.

Next stage recommendation:

- Fix live data collection and left-arm/gripper command execution before
  collecting 50/100/300 real episodes.
- Add `eef_pose` and `relative_target_to_eef` to the dataset.
- Retrain BC/DP/FM on real non-fallback data before treating the Stage 11
  tables as report-grade experimental results.

## Stage 12: Demo, README, And Final Report Materials

Status: completed on 2026-05-01 as documentation and demo packaging.

Completed:

- Re-read root docs and all package docs before stage work.
- Added a package-level README for new users.
- Added a final demo summary for course-project or paper-draft material.
- Updated project context, task definition, dataset schema, training plan,
  experiment log, stage progress, and TODO docs.
- Preserved all intermediate experiment logs and artifacts.
- Did not modify official or third-party packages.
- Did not run Gazebo, long training, or real rollout execution.

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

README coverage:

- project goal and current status;
- environment dependencies;
- simulation and MoveIt check commands;
- data collection and validation commands;
- BC, Diffusion Policy, and Flow Matching training commands;
- dry-run rollout evaluation commands;
- ablation report commands;
- directory structure;
- limitations and safety notes.

Final summary coverage:

- motivation;
- method;
- system architecture;
- data collection flow;
- model comparison;
- experiment artifacts;
- current results;
- limitations;
- next work.

Known limitations preserved in Stage 12 docs:

- Stage 6 data is fallback state data, not real demonstration data.
- Stage 10 rollout is dry-run action-label publication only.
- Success rate and final distance remain unavailable.
- Left-arm/gripper command execution and `eef_pose` remain unresolved.
- Disturbance ablations are deferred until official Project DAVE ocean-current
  configuration is checked.

Next stage recommendation:

- Treat the current package as a reproducible pipeline/demo artifact.
- For a real performance report, first fix live data collection and action
  execution, then collect non-fallback demonstrations and rerun Stages 7-11.
