# Dataset Schema

## Purpose

This schema defines the first-version state-based episode format for BC, Diffusion Policy, and Flow Matching Policy. All three methods must consume the same observations, actions, train/validation split, and normalization statistics.

The first version does not collect RGB or depth images.

## Current B8' Arm-Only Dataset Overlay

B8' data is for arm-only reaching / pre-grasp positioning, not grasping. The
long-term project may return to grasping later, but B8' episodes must be
interpreted as real non-fallback reaching/pre-grasp demonstrations.

Every B8' episode must satisfy:

```yaml
allow_nominal_state_fallback: false
base_state_source: odom
joint_state_source: joint_states
target_state_source: gazebo_model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
gripper_enabled: false
task_type: arm_only_reaching | pregrasp_positioning
success_metric: reaching_success | pregrasp_success
is_grasp_dataset: false
```

Required available fields for B8':

```text
target_pose
eef_pose
relative_target_to_eef
action_ee_delta
```

`raw_command` may remain unavailable for the first B8' smoke if metadata
explicitly marks it unavailable. `gripper_state` may still be recorded as
observed state, but it is not a control target and must not be used as a grasp
success criterion.

B8' quality checks must record:

```text
initial_distance
min_distance
final_distance
distance_reduction
active-left joint motion magnitude
validator result
failure_reason, if any
```

`success=False` is acceptable for early B8' smoke episodes. B8' quality should
first be judged by validator PASS, non-fallback metadata, bounded active-left
motion, and distance behavior. Do not convert B8' results into
`grasp_success_rate`.

## Storage Format

Initial training data is one `.npz` file per episode:

```text
data/raw/<episode_id>.npz
```

Later conversions to HDF5 or Zarr are allowed only after the `.npz` loop works. Loosely-coupled CSV files are not the main training format.

## Coordinate And Unit Conventions

- Time: seconds from ROS/Gazebo time when available.
- Linear position: meters.
- Linear velocity: meters per second.
- Angular velocity: radians per second.
- Orientation: quaternion `[qx, qy, qz, qw]`.
- Rotation deltas: radians, represented as roll/pitch/yaw deltas for the first version.
- Base pose frame: `world`, from `/rexrov/pose_gt`.
- Target pose frame: `world`, from `/gazebo/model_states` or `/gazebo/get_model_state`.
- End-effector pose frame: `world` if available from TF or MoveIt.
- End-effector delta action frame: configurable; first config marks it as `eef_or_task_frame_to_be_confirmed` until controller implementation fixes the convention.

## Required `.npz` Keys

Use flat key names for compatibility with NumPy and simple validators:

```text
timestamp
base_pose
base_velocity
active_joint_positions
active_joint_velocities
gripper_state
target_pose
action_ee_delta
done
success
metadata_json
```

Recommended optional keys:

```text
eef_pose
relative_target_to_eef
raw_command
```

Do not add image arrays in the first-version schema.

## Shapes

All time-series arrays are time-major and share the same leading dimension `T`.

| Key | Shape | Required | Meaning |
| --- | --- | --- | --- |
| `timestamp` | `[T]` | yes | ROS/Gazebo timestamp in seconds |
| `base_pose` | `[T, 7]` | yes | RexROV pose `[x, y, z, qx, qy, qz, qw]` in `world` |
| `base_velocity` | `[T, 6]` | yes | RexROV twist `[vx, vy, vz, wx, wy, wz]`; use odometry twist frame recorded in metadata |
| `active_joint_positions` | `[T, J]` | yes | left arm joint positions, `J=6` for current `arm_l` |
| `active_joint_velocities` | `[T, J]` | yes | left arm joint velocities, same joint order as `active_joint_positions` |
| `gripper_state` | `[T, G]` | yes | left gripper joint positions or compact gripper state, `G=4` if raw gripper joints are used |
| `target_pose` | `[T, 7]` | yes | target pose `[x, y, z, qx, qy, qz, qw]` in `world` |
| `eef_pose` | `[T, 7]` | optional | left end-effector pose `[x, y, z, qx, qy, qz, qw]` in `world` |
| `relative_target_to_eef` | `[T, 3]` or `[T, 6]` | optional | relative vector or pose error from end-effector to target |
| `action_ee_delta` | `[T, 7]` | yes | policy action label `[dx, dy, dz, droll, dpitch, dyaw, gripper_cmd]` |
| `raw_command` | implementation-specific | optional | raw ROS command sent by expert/controller, if available |
| `done` | `[T]` | yes | bool episode termination flag |
| `success` | scalar bool | yes | episode success label |
| `metadata_json` | scalar string | yes | JSON-serialized metadata dictionary |

The schema is single-active-arm, not dual-arm. It must not assume a 12-DOF dual-arm action or observation vector.

## Policy Action

First-version policy output:

```text
action = [dx, dy, dz, droll, dpitch, dyaw, gripper_cmd]
action_dim = 7
```

Fields:

- `dx, dy, dz`: end-effector translation delta in meters.
- `droll, dpitch, dyaw`: end-effector orientation delta in radians.
- `gripper_cmd`: scalar gripper command. Suggested convention is `0.0=open`, `1.0=closed`; final command mapping must be recorded in metadata.

For B8' arm-only reaching/pre-grasp data, `gripper_cmd` is ignored or fixed at
`0.0`; metadata must state `gripper_enabled=false` and
`is_grasp_dataset=false`.

The action frame must be recorded in metadata. Until the left-arm controller interface is confirmed, the default config marks the action frame as to-be-confirmed.

## Joint Ordering

Use the semantic active-left order from `config/active_joints_left_arm.yaml`:

```text
oberon7_l/azimuth
oberon7_l/shoulder
oberon7_l/elbow
oberon7_l/roll
oberon7_l/pitch
oberon7_l/wrist
```

Gripper order:

```text
oberon7_l/finger_left_joint
oberon7_l/finger_tip_left_joint
oberon7_l/finger_right_joint
oberon7_l/finger_tip_right_joint
```

Stage 2 showed that `/joint_states.name` runtime order differs from this semantic order. Recorders must index by joint name on every sample or maintain a verified name-to-index map.

## Required Metadata

Minimum metadata fields:

```yaml
schema_version: "0.1"
episode_id: string
created_at: string
workspace: "/home/benny/uuv_manipulator_ws"
package: "rexrov_single_oberon7_fm_dp"
robot_mode: "dual_model_single_active_left_arm"
active_arm: "left"
passive_arm_policy: "fixed_or_ignored"
use_images: false
world: string
launch_file: string
target_model_name: string
target_state_source: "gazebo_model_states" | "gazebo_get_model_state" | "unknown"
base_odom_topic: "/rexrov/pose_gt"
joint_states_topic: "/joint_states"
base_wrench_topic: "/rexrov/thruster_manager/input"
arm_command_topic: string | null
gripper_command_topic: string | null
controller_type: "scripted" | "ik_waypoint" | "moveit_ik" | "moveit_execution" | "replay" | "unknown"
moveit_group: "arm_l"
gripper_group: "hand_l"
eef_link: "oberon7_l/end_effector"
action_mode: "eef_delta_plus_gripper"
action_dim: 7
action_frame: string
rate_hz: float
max_duration_sec: float
active_joint_names: list[string]
gripper_joint_names: list[string]
inactive_joint_names: list[string]
success: bool
failure_reason: string | null
```

Optional metadata:

```yaml
normalization_version: string
expert_script: string
expert_parameters: dict
git_commit: string | null
rosbag_path: string | null
notes: string
```

## Validation Requirements

Every episode validator should check:

- all required keys exist
- `metadata_json` parses as JSON
- metadata includes `active_arm` and `robot_mode`
- `active_arm == "left"` for the first version
- `robot_mode == "dual_model_single_active_left_arm"` for the first version
- `use_images == false`
- time dimension `T` is consistent across required time-series arrays
- `T > 1`
- timestamps are finite and monotonic nondecreasing
- numeric arrays contain no NaN or Inf
- pose quaternions are finite and nonzero
- `action_ee_delta.shape == [T, 7]`
- `active_joint_positions.shape[1] == len(active_joint_names)`
- `active_joint_velocities.shape[1] == len(active_joint_names)`
- `done` is boolean or convertible to boolean
- `done[-1] == true`
- scalar `success` matches metadata `success`
- optional arrays, when present, share the same leading dimension `T`

## Stage 3 Config Files

The schema is paired with:

- `config/data_collection.yaml`
- `config/topics.yaml`
- `config/task_grasp.yaml`
- `config/active_joints_left_arm.yaml`

These files define defaults only. The left-arm command topic remains unconfirmed after Stage 2 and must be resolved before rollout control.

## Stage 4 Recorder Output

The first recorder implementation writes these keys:

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

Stage 4 smoke-test shapes:

```text
timestamp: [T]
base_pose: [T, 7]
base_velocity: [T, 6]
active_joint_positions: [T, 6]
active_joint_velocities: [T, 6]
gripper_state: [T, 4]
target_pose: [T, 7]
eef_pose: [T, 7]
relative_target_to_eef: [T, 3]
action_ee_delta: [T, 7]
raw_command: [T, 6]
done: [T]
success: scalar bool
metadata_json: scalar string
```

Unavailable-field convention:

- The recorder does not fabricate target, end-effector, action, or command values.
- If `target_pose`, `eef_pose`, `relative_target_to_eef`, `action_ee_delta`, or `raw_command` cannot be observed, the array is filled with `NaN`.
- Metadata records this explicitly through:

  ```yaml
  field_availability:
    target_pose: bool
    eef_pose: bool
    relative_target_to_eef: bool
    action_ee_delta: bool
    raw_command: bool
  unavailable_fields: list[string]
  action_ee_delta_available: false
  ```

- `validate_episode.py` treats NaN in these fields as a warning, not a failure, only when metadata marks the field unavailable.
- NaN in required observed fields such as `timestamp`, `base_pose`, `base_velocity`, `active_joint_positions`, `active_joint_velocities`, `gripper_state`, or `done` is always a validation failure.

Stage 4 known limits:

- `action_ee_delta` is present with shape `[T, 7]`, but is marked unavailable until an expert action converter is implemented.
- `raw_command` records the latest base wrench command when observed; in the Stage 4 smoke test no wrench command publisher was active, so it was marked unavailable.
- `eef_pose` and `relative_target_to_eef` are placeholders until TF/MoveIt pose lookup is added.
- `target_pose` is unavailable when the current launch does not spawn `target_model_name`.

## Stage 6 Batch Dataset Notes

Stage 6 added batch collection and summarization around the same `.npz` schema. The schema keys did not change.

Additional metadata fields may appear:

```yaml
base_state_fallback_model_name: "rexrov"
base_state_source: "odom" | "gazebo_model_states" | "nominal_base_state_fallback"
joint_state_source: "joint_states" | "zero_joint_state_fallback"
allow_nominal_state_fallback: bool
target_state_source: "gazebo_model_states" | "nominal_target_pose_fallback" | "unknown"
```

The 2026-05-01 Stage 6 debug dataset used:

```text
base_state_source: nominal_base_state_fallback
joint_state_source: zero_joint_state_fallback
target_state_source: nominal_target_pose_fallback
allow_nominal_state_fallback: true
```

Interpretation:

- The Stage 6 debug dataset is schema-valid and useful for dataset loader, normalization, and training-loop smoke tests.
- It must not be treated as real robot demonstration data because base, active joint, gripper, and target values were not all live Gazebo measurements.
- Future real demonstration datasets should set `allow_nominal_state_fallback: false` and should have live `joint_state_source: joint_states` plus a physical or stable Gazebo target source.

## Stage 12 Reproducible Dataset Pointers

The packaged demo references the following dataset artifacts:

```text
data/raw/stage6_debug
outputs/logs/stage6_debug/dataset_summary.json
outputs/logs/stage6_debug/dataset_summary.md
outputs/logs/stage6_debug/dataset_split_combined.json
```

The Stage 6 debug split is:

```text
train: 16 episodes
val: 4 episodes
test: 0 episodes
obs_horizon: 4
action_horizon: 16
action_dim: 7
```

Stage 12 documentation keeps this explicit because all Stage 7-11 training,
offline evaluation, rollout dry-run, and ablation results depend on this same
fallback dataset. Any later real dataset should use the same keys and shapes but
must record live, non-fallback state sources in `metadata_json`.
