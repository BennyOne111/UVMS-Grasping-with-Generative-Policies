# Project Context

## Workspace

- Workspace: `/home/benny/uuv_manipulator_ws`
- ROS distro: Noetic
- Simulator stack: Gazebo + Project DAVE + UUV Simulator
- Main project package: `src/uvms/rexrov_single_oberon7_fm_dp`
- Created in stage 0 as a new overlay package under `src/uvms`

## Goal

Build a first demo for automated expert trajectory collection and state-based imitation learning on a RexROV + Oberon7 underwater manipulation task.

Policies to compare:

1. Behavior Cloning baseline
2. Diffusion Policy
3. Flow Matching Policy

Current route:

```text
RexROV + single-active-left Oberon7 arm-only reaching / pre-grasp positioning
```

The long-term goal can remain underwater grasping, but the current route is
not grasping. Current B5d'/B8' work keeps the gripper disabled because gripper
command/stability is blocked. Current success metrics are
`reaching_success` or `pregrasp_success`, not `grasp_success`.

## First Demo Scope

- Robot mode: keep the existing RexROV + dual Oberon7 simulation available.
- Active arm: `left`
- Passive arm: right arm fixed or excluded from observation/action.
- Current task: arm-only reaching / pre-grasp positioning toward a simple
  geometric target.
- Long-term task: single-arm, single-object grasping with a simple geometric
  target.
- Observation: state-based only for the first version.
- Action: end-effector delta action plus a compatibility gripper slot; current
  arm-only route ignores/fixes the gripper command.
- Dataset unit: episode.
- Initial storage: `.npz`; later HDF5 or Zarr if needed.

## Dependency Snapshot

Checked in stage 0:

- `torch`: `2.11.0+cu130`
- CUDA available: `True`
- GPU: `NVIDIA GeForce RTX 4060 Laptop GPU`
- `casadi`: `3.7.0`

User previously confirmed these packages are installed:

- numpy
- scipy
- pandas
- pyyaml
- tqdm
- matplotlib
- torch
- torchvision
- tensorboard
- h5py
- zarr
- opencv-python
- pillow
- casadi

## Relevant Existing Packages

Static/project-map context identifies these `src/uvms` packages as relevant references:

- `data_rexrov_dual_oberon7`
- `oberon7_data`
- `oberon7_effort_utils`
- `oberon7_moveit_revised`
- `rexrov_data`
- `rexrov_moveit_revised`
- `rexrov_nmpc_controller_plugin`
- `uvms_control`

Stage 1 static inspection confirmed these ROS packages under `src/uvms`:

| Package | Role for this project | Reuse decision |
| --- | --- | --- |
| `data_rexrov_dual_oberon7` | RexROV + dual Oberon7 launch, controller YAML, sine-excitation CSV collector | Best first launch/config reference for RexROV + dual Oberon7 with left active arm |
| `rexrov_data` | RexROV-only launch and wrench/odom/IMU CSV collector | Reuse as base-state and base-wrench recorder reference only |
| `oberon7_data` | Per-joint random effort data collection with `oberon7_left/right` names | Lower priority; naming differs from current `oberon7_l/r` dual-arm xacro |
| `uvms_control` | Base NMPC, MoveIt planning baselines, reference publishers, CSV recorder | Main source of controller and expert-policy prototypes |
| `rexrov_moveit_revised` | MoveIt config for RexROV + dual Oberon7 groups | Preferred MoveIt config to inspect first in runtime checks |
| `oberon7_moveit_revised` | Near-duplicate revised MoveIt config | Secondary reference; differs in some launch/package metadata |
| `oberon7_effort_utils` | Effort controller helper launch | Not directly reusable as-is; it references a missing package-local config file |
| `rexrov_nmpc_controller_plugin` | Draft MoveIt controller manager plugin for RexROV NMPC | Not first-version reusable; build/export appear incomplete |
| `rexrov_single_oberon7_fm_dp` | New project package | Write target for future wrapper/recorder/training code |

## Stage 1 Static Reuse Map

Recommended first-version base launch:

- `src/uvms/data_rexrov_dual_oberon7/launch/rexrov_dual_oberon7.launch`
- Alternative reference: `src/uvms/uvms_control/launch/uvms_baseline_vs_rl_v1.launch`

Why:

- Both use `rexrov_description/launch/upload_rexrov_oberon7_moveit.launch`.
- `rexrov_robot.urdf.xacro` mounts two arms as `oberon7_l` and `oberon7_r`.
- `data_rexrov_dual_oberon7/config/oberon7_controllers.yaml` defines left/right arm and hand controllers with explicit joint names.

Static left-arm joint names:

```text
oberon7_l/azimuth
oberon7_l/shoulder
oberon7_l/elbow
oberon7_l/roll
oberon7_l/pitch
oberon7_l/wrist
```

Static left gripper joint names:

```text
oberon7_l/finger_left_joint
oberon7_l/finger_tip_left_joint
oberon7_l/finger_right_joint
oberon7_l/finger_tip_right_joint
```

Static right-arm joint names:

```text
oberon7_r/azimuth
oberon7_r/shoulder
oberon7_r/elbow
oberon7_r/roll
oberon7_r/pitch
oberon7_r/wrist
```

Right arm can probably remain static by not sending changing commands, or by sending a fixed hold command through its position controller. This must be verified at runtime because controller behavior under no command depends on which controller type is spawned.

MoveIt groups confirmed statically in both revised SRDF files:

```text
base
arm_l
arm_r
hand_l
hand_r
```

MoveIt end effector declarations:

```text
hand_l parent_link=oberon7_l/end_effector parent_group=arm_l
hand_r parent_link=oberon7_r/end_effector parent_group=arm_r
```

Important MoveIt controller caveat:

- `config/simple_moveit_controllers.yaml` contains `controller_list: []`.
- `config/ros_controllers.yaml` is empty.
- `fake_controllers.yaml` defines fake arm/hand controllers.
- Existing trajectory execution against Gazebo controllers is therefore not proven by static files.

Object/world candidates:

- `src/dave/models/dave_worlds/worlds/dave_bimanual_example.world` includes `grabbapole`, `sunken_vase`, and `sunken_vase_distorted`.
- `src/dave/models/dave_object_models/models/cylinder_target` and `sphere_target` are simple geometric objects suitable for first-version tasks, but a project-local launch/world wrapper should be used later instead of editing official DAVE worlds.

Read-only reference areas:

- `src/dave`
- `src/uuv_simulator`
- `src/uuv_manipulators`
- `src/rexrov2`

Do not modify those official or third-party packages unless the user explicitly requests it.

## External References

Use official sources when Project DAVE behavior, launch files, worlds, models, or tutorials need confirmation:

- Project DAVE docs: <https://field-robotics-lab.github.io/dave.doc/>
- Project DAVE GitHub: <https://github.com/Field-Robotics-Lab/dave>

Do not rely on memory for DAVE details that can change or need exact launch/model names.

## Stage 12 Demo Packaging Status

The package now has a top-level `README.md` and a final demo summary:

```text
README.md
docs/FINAL_DEMO_SUMMARY.md
```

The README is the entry point for a new reader. It records:

- project goal and current status;
- environment and dependency notes;
- simulation and MoveIt check commands;
- data collection, validation, and summarization commands;
- BC, Diffusion Policy, and Flow Matching training commands;
- offline rollout and ablation report commands;
- key output paths and known limitations.

The current reproducible demo is best described as:

```text
state-based BC / DP / FM pipeline smoke demo
robot model: RexROV + dual Oberon7
active arm: left only
dataset: Stage 6 fallback debug dataset
rollout: safe dry-run action-label rollout
report: Stage 11 offline comparison and ablation artifacts
```

This is not yet a real underwater grasping benchmark. The following remain
open before report-grade physical-policy results:

- live non-fallback state collection;
- confirmed left-arm and gripper command execution;
- TF or MoveIt-based `eef_pose`;
- real EE-delta action conversion to IK or joint commands;
- real Gazebo rollout success-rate evaluation.
