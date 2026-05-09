# Codex Guide

## Required Start-of-Stage Routine

Before each stage:

1. Work from `/home/benny/uuv_manipulator_ws`.
2. Source the workspace when ROS commands are needed:

   ```bash
   source devel/setup.bash
   ```

3. Read workspace docs:

   ```text
   ./docs
   ./src/uvms/rexrov_single_oberon7_fm_dp/docs
   ```

4. After reading, output:

   ```text
   当前理解
   本阶段计划
   ```

5. Only then perform stage operations.

## Required End-of-Stage Routine

At the end of each stage, update one or more docs in this directory. Prefer updating the files that match the work just done:

- `PROJECT_CONTEXT.md`
- `CODEX_GUIDE.md`
- `TASK_DEFINITION.md`
- `TOPIC_MAP_RUNTIME.md`
- `DATASET_SCHEMA.md`
- `EXPERT_POLICY_PLAN.md`
- `DATA_COLLECTION_LOG.md`
- `TRAINING_PLAN.md`
- `EXPERIMENT_LOG.md`
- `TODO.md`
- `STAGE_PROGRESS.md`

If a stage fails, document the failure reason and the next concrete step before stopping.

## Modification Boundaries

Primary write scope:

```text
src/uvms/rexrov_single_oberon7_fm_dp
```

Read-only reference scope unless explicitly approved by the user:

```text
src/dave
src/uuv_simulator
src/uuv_manipulators
src/rexrov2
```

Do not make broad edits to official Project DAVE, UUV Simulator, UUV manipulators, or RexROV2 packages.

## Project Rules

- Preserve the existing RexROV + dual Oberon7 simulation path in early work.
- Use `active_arm=left` for the first version.
- Keep the right arm fixed or outside observation/action.
- Current route is arm-only reaching / pre-grasp positioning.
- Treat grasping as long-term goal or historical context only until the
  gripper blocker is resolved.
- Do not publish gripper commands or start hand controllers for the current
  arm-only route.
- Use `reaching_success` or `pregrasp_success`, not `grasp_success`, for
  current B5d'/B8' work.
- Do not treat Stage 6 fallback data as real demonstration data.
- Do not hard-code single-arm assumptions across the full workspace.
- First version is state-based. Do not collect RGB/depth initially.
- Compare BC, Diffusion Policy, and Flow Matching Policy.
- Use the same data, same normalization, and comparable model sizes for DP and FM.
- Prefer automated expert collection: scripted expert, MoveIt expert, or IK waypoint expert.
- Before using MoveIt as expert, confirm the current RexROV + Oberon7 MoveIt setup works.
- Store first episodes as `.npz`; avoid loosely-coupled CSV as the main training format.
- Do not add Ray, RLlib, or PettingZoo as first-version dependencies.
- Do not run long Gazebo simulations or long training unless explicitly requested.

## Runtime Confirmation Rule

Never assume topic names, controller names, joint names, or service names are final. Confirm with static files and, in later stages, runtime tools such as:

```bash
rostopic list
rostopic info
rosparam list
rosservice list
rosservice info
rospack find
```
