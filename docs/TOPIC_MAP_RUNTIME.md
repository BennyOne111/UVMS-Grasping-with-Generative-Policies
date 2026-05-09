# Topic Map Runtime

This file records candidate topics and the runtime checks required before implementing collection or control. Nothing here should be treated as final until confirmed in a running ROS graph.

## Current Arm-Only Reaching Runtime Map

Current route:

```text
RexROV + single-active-left Oberon7 arm-only reaching / pre-grasp positioning
```

Confirmed sources for B5d'/B8':

```text
base_state_source: /rexrov/pose_gt (odom)
joint_state_source: /joint_states
target_state_source: /gazebo/model_states
eef_pose_source: odom+tf:rexrov/base_link->oberon7_l/end_effector
arm_command_topic: /oberon7/arm_position_l/command
IK service: /compute_ik
```

Current command path:

```text
action_ee_delta -> IK/joint target -> /oberon7/arm_position_l/command
```

Do not use gripper command topics for B5d'/B8'. Hand controllers and gripper
commands remain blocked/future work. MoveIt trajectory execution is still not
the current execution path.

## Candidate State Topics

Base state candidates:

```text
/rexrov/pose_gt
/rexrov/imu
/rexrov/dvl
```

Joint state candidates:

```text
/joint_states
/rexrov/joint_states
```

Target object state candidates:

```text
/gazebo/model_states
/gazebo/get_model_state
```

## Stage 1 Static Topic Findings

Static references found in `src/uvms`:

| Topic or service | Type inferred from code | Static source | Runtime status |
| --- | --- | --- | --- |
| `/rexrov/pose_gt` | `nav_msgs/Odometry` | `rexrov_data`, `data_rexrov_dual_oberon7`, `uvms_control` | Must confirm active publisher |
| `/rexrov/imu` | `sensor_msgs/Imu` | `rexrov_data`, `data_rexrov_dual_oberon7` | Must confirm active publisher |
| `/joint_states` | `sensor_msgs/JointState` | `data_rexrov_dual_oberon7`, `uvms_recorder` | Must confirm whether this or `/rexrov/joint_states` is authoritative |
| `/rexrov/joint_states` | `sensor_msgs/JointState` | `oberon7_data` | Naming may come from another launch path; must confirm |
| `/rexrov/thruster_manager/input` | `geometry_msgs/Wrench` | RexROV collectors and NMPC controllers | Must confirm controller manager startup |
| `/arm_l_group_effort/command` | `std_msgs/Float64MultiArray` | `data_collector_dual_oberon7.py` | Exists only if `arm_l_group_effort` is spawned |
| `/arm_r_group_effort/command` | `std_msgs/Float64MultiArray` | `data_collector_dual_oberon7.py` | Avoid changing for first active-left demo |
| `/joint_group_arm_l_position_controller/command` | likely `std_msgs/Float64MultiArray` | `oberon7_controllers.yaml`, launch spawners | Must confirm exact topic name from controller |
| `/joint_group_arm_r_position_controller/command` | likely `std_msgs/Float64MultiArray` | `oberon7_controllers.yaml`, launch spawners | Candidate hold/static command path |
| `/arm_position_l/follow_joint_trajectory` | trajectory action | `oberon7_controllers.yaml` | Must confirm if spawned and action server exists |
| `/hand_position_l/follow_joint_trajectory` | trajectory action | `oberon7_controllers.yaml` | Candidate gripper command path |
| `/hand_effort_l/follow_joint_trajectory` | trajectory action | `oberon7_controllers.yaml` | Candidate gripper command path in effort mode |
| `/uvms/left_arm/end/target` | `geometry_msgs/Pose` | `ref_traj_oberon7_fixed_point.py` | Useful for MoveIt expert prototype |
| `/compute_ik` | `moveit_msgs/GetPositionIK` service | `baseline_oberon7_planning_and_control_rrtconnect_and_pid_py.py` | Must be available before MoveIt expert |
| `/baseline/rexrov/target_traj` | `nav_msgs/Path` | `baseline_rexrov_planning_rrtconnect_py.py` | Base planning prototype only |
| `/gazebo/model_states` | `gazebo_msgs/ModelStates` expected | root project map | Must confirm when Gazebo is running |
| `/gazebo/get_model_state` | `gazebo_msgs/GetModelState` expected | root project map | Must confirm when Gazebo is running |

Static left active-arm joint order from controller YAML:

```text
oberon7_l/azimuth
oberon7_l/shoulder
oberon7_l/elbow
oberon7_l/roll
oberon7_l/pitch
oberon7_l/wrist
```

Static left gripper joint order from controller YAML:

```text
oberon7_l/finger_left_joint
oberon7_l/finger_tip_left_joint
oberon7_l/finger_right_joint
oberon7_l/finger_tip_right_joint
```

## Candidate Control Topics

RexROV base action candidates:

```text
/rexrov/thruster_manager/input
/rexrov/thruster_manager/input_stamped
```

Left/right arm controller candidates from previous static project map:

```text
/arm_l_group_effort/command
/arm_r_group_effort/command
/joint_group_arm_l_position_controller/command
/joint_group_arm_r_position_controller/command
/arm_position_l/follow_joint_trajectory
/arm_position_r/follow_joint_trajectory
/hand_position_l/follow_joint_trajectory
/hand_position_r/follow_joint_trajectory
```

## Runtime Checks For Stage 1

When Gazebo/ROS runtime inspection is allowed in a later stage, run short checks only:

```bash
rostopic list
rostopic info /joint_states
rostopic info /rexrov/joint_states
rosparam list
rosservice list
rosservice info /gazebo/get_model_state
```

Controller checks:

```bash
rosservice list | grep controller
rosparam list | grep controller
```

MoveIt checks before using MoveIt as expert:

```bash
rospack find rexrov_moveit_revised
rospack find oberon7_moveit_revised
rosservice list | grep compute_ik
```

Additional checks recommended after launching the selected base simulation:

```bash
rostopic info /arm_l_group_effort/command
rostopic info /joint_group_arm_l_position_controller/command
rostopic info /hand_position_l/follow_joint_trajectory
rostopic echo -n 1 /joint_states
rosservice list | grep controller_manager
rosparam get /robot_description_semantic
rosparam get /move_group/controller_list
```

## Notes

- Do not hard-code names from this document without confirming them.
- The first recorder should parameterize topic names through ROS params or config.
- The right arm should remain fixed or excluded from observation/action for first-version learning data.

## Stage 2 Runtime Findings

Runtime date: 2026-04-29.

Minimal simulation launch used:

```bash
roslaunch uvms_control oberon7_position_control.launch gui:=false paused:=true
```

Reason:

- `data_rexrov_dual_oberon7/launch/rexrov_dual_oberon7.launch` starts the existing dual-arm/base data collector and can publish active excitation commands.
- `uvms_control/launch/oberon7_position_control.launch` loads the RexROV + dual Oberon7 model, Gazebo, robot state publisher, thruster manager/allocation, and controller parameters without starting the collector/expert scripts.
- `paused:=true` was used for initial read-only inspection. `/clock` and `/joint_states` did not publish samples until physics was briefly unpaused.

Confirmed runtime state topics:

| Topic | Type | Publisher | Subscriber | Stage 2 status |
| --- | --- | --- | --- | --- |
| `/joint_states` | `sensor_msgs/JointState` | `/gazebo` | `/robot_state_publisher` | Authoritative joint state topic for this launch |
| `/rexrov/joint_states` | n/a | n/a | n/a | Not present in this launch |
| `/rexrov/pose_gt` | `nav_msgs/Odometry` | `/gazebo` | none | Confirmed base state topic |
| `/gazebo/model_states` | `gazebo_msgs/ModelStates` | `/gazebo` | none | Confirmed Gazebo model-state source |
| `/gazebo/get_model_state` | `gazebo_msgs/GetModelState` service | `/gazebo` | n/a | Confirmed available |

Confirmed runtime base command topics:

| Topic | Type | Publisher | Subscriber | Stage 2 status |
| --- | --- | --- | --- | --- |
| `/rexrov/thruster_manager/input` | `geometry_msgs/Wrench` | none | `/rexrov/thruster_allocator` | Confirmed base wrench command topic |
| `/rexrov/thruster_manager/input_stamped` | `geometry_msgs/WrenchStamped` | none | `/rexrov/thruster_allocator` | Confirmed stamped base wrench command topic |
| `/rexrov/thrusters/0/input` through `/rexrov/thrusters/7/input` | `uuv_gazebo_ros_plugins_msgs/FloatStamped` | `/rexrov/thruster_allocator` | `/gazebo` | Low-level thruster inputs; not the first choice for learning action commands |

Runtime thruster-manager parameters included:

```text
/rexrov/thruster_manager/base_link: base_link
/rexrov/thruster_manager/tf_prefix: /rexrov/
/rexrov/thruster_manager/max_thrust: 2000.0
/rexrov/thruster_manager/update_rate: 50
/rexrov/thruster_manager/timeout: -1
```

Confirmed runtime joint names from `/joint_states` sample:

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
oberon7_r/azimuth
oberon7_r/elbow
oberon7_r/finger_left_joint
oberon7_r/finger_right_joint
oberon7_r/finger_tip_left_joint
oberon7_r/finger_tip_right_joint
oberon7_r/pitch
oberon7_r/roll
oberon7_r/shoulder
oberon7_r/wrist
```

Important recorder implication:

- `/joint_states.name` order is not the same as the controller YAML order.
- Recorders and controllers must index joints by name, not by raw array position.
- First-version active arm should use the MoveIt/controller order for semantic action vectors:

```text
oberon7_l/azimuth
oberon7_l/shoulder
oberon7_l/elbow
oberon7_l/roll
oberon7_l/pitch
oberon7_l/wrist
```

Runtime controller status:

- `/controller_manager/list_controller_types`, `/controller_manager/list_controllers`, `/controller_manager/load_controller`, `/controller_manager/switch_controller`, and related services appeared in `rosservice list`.
- `rosservice call /controller_manager/list_controllers "{}"` did not return during this check and had to be killed.
- Launch output showed `joint_state_controller` loaded and started successfully.
- Launch output also showed a controller spawner warning: `Controller Spawner couldn't find the expected controller_manager ROS interface`.
- No left-arm controller command/action topics matching `oberon7`, `arm_position`, `joint_group`, `hand_position`, `hand_effort`, or `follow_joint` were present in `rostopic list` for this minimal launch.

MoveIt runtime status:

- Base minimal launch did not start `move_group`; `/compute_ik` was absent before MoveIt launch.
- Loaded MoveIt parameters with:

  ```bash
  roslaunch rexrov_moveit_revised planning_context_revised.launch load_robot_description:=false
  ```

- Started MoveIt static check with:

  ```bash
  roslaunch rexrov_moveit_revised move_group_revised.launch allow_trajectory_execution:=false load_robot_description:=false pipeline:=ompl
  ```

- `/move_group` started.
- `/compute_ik` appeared as `moveit_msgs/GetPositionIK`, provided by `/move_group`.
- `move_group` reported `No controller_list specified` and `Returned 0 controllers in list`, so planning/IK is available but trajectory execution is not configured.
- `MoveGroupCommander` query succeeded only while `/clock` was advancing; it timed out while Gazebo physics was paused.
- Confirmed MoveIt groups:

```text
arm_l
arm_r
base
hand_l
hand_r
```

- `left_arm` is not a valid MoveIt group name.
- `arm_l` active joints:

```text
oberon7_l/azimuth
oberon7_l/shoulder
oberon7_l/elbow
oberon7_l/roll
oberon7_l/pitch
oberon7_l/wrist
```

- `arm_l` end-effector link: `oberon7_l/end_effector`.
- `hand_l` active joints:

```text
oberon7_l/finger_left_joint
oberon7_l/finger_tip_left_joint
oberon7_l/finger_right_joint
oberon7_l/finger_tip_right_joint
```

Target object status:

- The minimal launch's `/gazebo/model_states` sample contained `ocean_box` and `rexrov` only.
- No grasp target object was loaded by this minimal launch.
- Target pose acquisition through `/gazebo/model_states` or `/gazebo/get_model_state` is available once a project-local target model/world wrapper is added in a later stage.
