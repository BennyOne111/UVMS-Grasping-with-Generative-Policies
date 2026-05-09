# Task Definition

## Current Route Override: Arm-Only Reaching / Pre-Grasp

Current first-version real closed-loop demo target:

```text
RexROV + single-active-left Oberon7 arm-only reaching / pre-grasp positioning
```

The long-term goal can remain underwater grasping, but the current route is
not grasping. The current demo does not close the gripper, does not lift or
hold an object, and must not report `grasp_success` or `grasp_success_rate`.

Current success metric:

```text
reaching_success or pregrasp_success =
  distance(eef_pose, target_or_pregrasp_pose) < threshold
  and not timeout
```

The provisional threshold remains `0.05 m` to `0.10 m`; B8' data collection
must record the threshold used in metadata or logs. `success=False` is normal
for current B5d'/B8' smoke runs because gripper execution is disabled and
blocked. It must not be interpreted as grasp failure.

The action vector remains `action_dim=7` for compatibility:

```text
[dx, dy, dz, droll, dpitch, dyaw, gripper_cmd]
```

For the current arm-only route, `gripper_cmd` is ignored or fixed at `0`, and
metadata must mark:

```text
gripper_enabled: false
is_grasp_dataset: false
success_metric: reaching_success or pregrasp_success
```

## First Version Task

Current route: single-active-left-arm reaching or pre-grasp positioning toward
one simple geometric object in the Project DAVE/Gazebo RexROV + Oberon7
environment.

Historical/long-term route: single-arm grasping of one simple geometric object.
Historical grasping references below are retained as project history or future
work, not as the current B5d'/B8' task.

## Robot Setup

- Platform: RexROV + Oberon7
- Initial simulation mode: existing RexROV + dual Oberon7 setup remains available.
- Active manipulator: left Oberon7 arm.
- Right manipulator: fixed or ignored by the first-version observation/action spaces.
- Metadata must include:
  - `robot_mode: rexrov_dual_oberon7`
  - `active_arm: left`
  - `passive_arm_policy: fixed_or_ignored`

Stage 2 runtime correction:

- Minimal checked launch: `uvms_control/launch/oberon7_position_control.launch` with `gui:=false paused:=true`.
- Runtime robot model included RexROV with both `oberon7_l/*` and `oberon7_r/*` joints.
- First-version active arm must use MoveIt group `arm_l`; `left_arm` is not a valid group name.
- First-version gripper group is `hand_l`.
- Left arm end-effector link is `oberon7_l/end_effector`.

## Observation Space

First version is state-based. Candidate fields:

- timestamp
- RexROV base pose from `/rexrov/pose_gt`
- RexROV base velocity
- left arm joint positions from `/joint_states`, indexed by joint name
- left arm joint velocities from `/joint_states`, indexed by joint name
- gripper state
- target object pose from `/gazebo/model_states` or `/gazebo/get_model_state`
- optional left end-effector pose

Do not collect RGB/depth in the first version.

Runtime-confirmed active left arm joints:

```text
oberon7_l/azimuth
oberon7_l/shoulder
oberon7_l/elbow
oberon7_l/roll
oberon7_l/pitch
oberon7_l/wrist
```

Runtime-confirmed left gripper joints:

```text
oberon7_l/finger_left_joint
oberon7_l/finger_tip_left_joint
oberon7_l/finger_right_joint
oberon7_l/finger_tip_right_joint
```

Do not assume `/joint_states` array order. The runtime sample used a different order than the semantic arm order above.

## Action Space

Policy action should be:

- end-effector delta translation/rotation
- gripper command

Exact representation is deferred until controller and IK paths are confirmed. Candidate action vector:

```text
[dx, dy, dz, droll, dpitch, dyaw, gripper_cmd]
```

Stage 2 command-topic status:

- RexROV base wrench command is available at `/rexrov/thruster_manager/input` (`geometry_msgs/Wrench`) and `/rexrov/thruster_manager/input_stamped` (`geometry_msgs/WrenchStamped`).
- Low-level per-thruster inputs are published by `/rexrov/thruster_allocator` to `/rexrov/thrusters/0/input` through `/rexrov/thrusters/7/input`.
- The checked minimal launch did not expose usable left-arm controller command/action topics.
- The first recorder can be designed now, but rollout control needs a confirmed left-arm command interface in the next stage.

## Expert Collection Direction

Preferred expert types, in order of practicality:

1. Scripted waypoint expert
2. IK waypoint expert
3. MoveIt expert if current configuration is confirmed usable

MoveIt Stage 2 result:

- `/compute_ik` and `MoveGroupCommander("arm_l")` are available after starting `move_group`.
- MoveIt planning/IK can be used as an expert component.
- MoveIt trajectory execution is not ready because the controller list is empty and no left-arm execution topic was confirmed.

Stage 5 expert definition:

- First executable expert type: scripted fallback expert.
- The expert publishes project-local EE delta action labels to `/rexrov_single_oberon7_fm_dp/expert/action_ee_delta`.
- It does not yet command the physical left arm because the left-arm command interface remains unresolved.
- `collect_episode.launch` spawns a simple package-local `cylinder_target` SDF model for the first target.
- Recorder episodes from the Stage 5 expert have finite `target_pose` and finite `action_ee_delta`.
- `eef_pose` and `relative_target_to_eef` remain unavailable until TF/MoveIt lookup is added.
- Success remains false in the smoke test because distance-based success requires finite `eef_pose`.

## Evaluation Loop

The first complete loop should support:

1. Automated episode collection
2. Dataset validation
3. BC sanity training
4. Diffusion Policy training
5. Flow Matching Policy training
6. Simulation rollout evaluation

Stage 0 does not implement any of these runtime components.

## Stage 10 Rollout Status

Stage 10 adds the first rollout-policy node and unified evaluation harness, but
keeps real controller execution disabled by default.

Current rollout action path:

```text
policy checkpoint
  -> normalized obs_history
  -> action_chunk [T, 7]
  -> safety clipping
  -> /rexrov_single_oberon7_fm_dp/policy/action_ee_delta
```

The published action is still an end-effector delta action label:

```text
[dx, dy, dz, droll, dpitch, dyaw, gripper_cmd]
```

Real arm/gripper command execution is blocked until these are confirmed:

- left-arm command topic or action server;
- gripper command topic or action server;
- action-frame convention and conversion into IK/joint commands;
- end-effector pose source for success and distance metrics;
- stable live `/joint_states`, `/rexrov/pose_gt`, and target state collection.

Stage 10 unified evaluation therefore reports `success_rate=not_evaluated` and
`final_distance=unavailable` for BC, Diffusion Policy, and Flow Matching Policy.
This is intentional; failure reason is recorded as
`controller_mapping_unconfirmed` instead of silently attempting unsafe commands.

## Stage 12 Demo Definition

The packaged demo target is now:

```text
name: RexROV + single-active-left Oberon7 state-based BC/DP/FM demo
scope: reproducible pipeline demonstration
active robot components: RexROV base state + left Oberon7 observation/action labels
passive robot components: right Oberon7 fixed or ignored
target: package-local cylinder_target or simple DAVE geometric object
policy action: [dx, dy, dz, droll, dpitch, dyaw, gripper_cmd]
rollout mode: dry-run action-label publication by default
```

What the demo currently proves:

- episode schema, writer, and validator work;
- scripted expert action labels can be recorded;
- batch collection and dataset summaries work;
- BC, Diffusion Policy, and Flow Matching Policy can be trained on the same
  state/action representation;
- all three policies can be loaded by the shared runtime path;
- comparison tables and plots can be generated reproducibly.

What the demo does not yet prove:

- real left-arm motion execution;
- real gripper closure;
- real target grasp success;
- distance-to-target success metrics based on `eef_pose`;
- ocean-current robustness.

The next task definition should stay focused on converting the current
action-label pipeline into a real safe controller rollout before adding images,
dual-arm coordination, or disturbance experiments.

## B5d' / B8' Arm-Only Route

B5d' status:

- Minimal debug smoke is resolved for arm-only reaching/pre-grasp.
- The scripted expert can publish target-directed clipped EE deltas.
- The converter can generate bounded left-arm joint targets through IK and
  publish to `/oberon7/arm_position_l/command`.
- Gripper command is disabled and remains blocked as future work.
- MoveIt trajectory execution remains unproven; the current path is:

  ```text
  EE-delta -> IK/joint target -> /oberon7/arm_position_l/command
  ```

B8' next task:

- Collect a small real non-fallback arm-only reaching/pre-grasp dataset.
- Start with 5 short episodes and validate every episode before training.
- Required runtime sources:
  - `base_state_source=odom`
  - `joint_state_source=joint_states`
  - `target_state_source=gazebo_model_states`
  - `eef_pose_source=odom+tf:rexrov/base_link->oberon7_l/end_effector`
- Required interpretation:
  - no `grasp_success`;
  - no object grasped/lifted/held claim;
  - Stage 6 fallback data remains a pipeline smoke dataset only.
