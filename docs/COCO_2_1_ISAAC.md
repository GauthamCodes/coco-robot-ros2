# COCO 2.1 — Isaac Sim digital twin and cross-simulator integration

This branch starts at the clean P03D commit `8e518cf99b50347568d9e7c303ec80b18ef8c223`.
The Gazebo implementation and all files under `docs/data/p03d_autonomous_search/`
remain unchanged. The Isaac foundation code was ported from the committed
`p03-isaac-backend` work at `ffb3fc6` (original implementation `9197bf2`).
Uncommitted files in that separate worktree were not used or changed.

## Architecture and ownership

| Component | Current owner | Portability |
| --- | --- | --- |
| Dimensions, mass, wheel and sensor poses | `coco_config/robot.py` | Reuse unchanged |
| Full arm, gripper, collisions and Gazebo sensors | `gazebo_models/urdf/coco_robo2.xacro`, meshes | Gazebo specific; Isaac currently approximates arm mass |
| Four wheel geometry and contact | Xacro + `gz_ros2_control` in Gazebo; generated USD articulation in Isaac | Reuse geometry with simulator adapter |
| Differential drive command | `diff_drive_controller` in Gazebo; `DriveCommand` and four joint velocity targets in Isaac | Simulator specific, behind same final ROS command |
| Scan, RGB-D, IMU, clock | Gazebo sensors and `ros_gz_bridge`; Isaac PhysX LiDAR, RTX camera and bridge | Simulator specific |
| `odom → base_footprint` | Gazebo diff drive controller; Isaac measured pose publisher | Same ROS frames, different odometry source |
| Static robot TF and joint state | Gazebo robot state publisher/controllers; Isaac ROS publishers | Same navigation frames; Isaac publishes four wheel joints only |
| Localization and Nav2 | `gazebo_models/nav.launch.py`, `nav2_params.yaml` | Reuse unchanged, with run-local fixture map override |
| Perception and target pose | `coco_perception` | ROS nodes reusable; Isaac input topics present, detection not yet verified |
| Mission executive and P03D search | `coco_mission` | ROS logic reusable; Isaac target scene and grasp absent |
| Arm planning and grasp | MoveIt and Gazebo DetachableJoint magnet | Not yet portable |
| Command safety | `cmd_vel_relay` → `cmd_vel_arbiter` | Reuse unchanged; sole publisher of final wheel command |
| Gazebo spawn, bridge, controllers | `gazebo_models/full_world_robo.launch.py` | Gazebo specific |
| Isaac scene and ROS output | `coco_sim/coco_sim/isaac/`, `scripts/isaac_sim_coco.sh` | Isaac specific |

The Isaac scene is a small, deterministic navigation fixture generated from
`coco_config` measurements, with four driven wheels and collision geometry.
It is not the P03D ramp and target world. The chassis uses primitive geometry
and diagonal approximate inertia; the arm's mass is fixed at its mounting
location. The wheel joint names in Isaac differ from the Gazebo URDF names,
but the final velocity topic and navigation frames match. This is a mobile
base integration, not a complete manipulation twin.

## ROS compatibility contract

These names come from the Xacro, `bridge.yaml`, Nav2 parameters, perception
node, and arbiter, rather than a new interface. Isaac publishes:

| Topic | Type | Frame / consumer |
| --- | --- | --- |
| `/clock` | `rosgraph_msgs/Clock` | All nodes with `use_sim_time` |
| `/tf`, `/tf_static` | `tf2_msgs/TFMessage` | `odom → base_footprint → base_link`; sensor frames; AMCL owns `map → odom` |
| `/diff_drive_controller/odom` | `nav_msgs/Odometry` | Nav2; `odom`, child `base_footprint` |
| `/joint_states` | `sensor_msgs/JointState` | Four wheel joints |
| `/scan` | `sensor_msgs/LaserScan` | Nav2 costmaps and AMCL; `lidar_link` |
| `/camera/image_raw` | `sensor_msgs/Image` | RGB perception; optical frame |
| `/camera/depth/image_raw` | `sensor_msgs/Image` | Depth perception; optical frame, 32FC1 metres |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | RGB-D calibration |

The backend **subscribes only** to `/diff_drive_controller/cmd_vel`
(`geometry_msgs/TwistStamped`). The host `isaac_ros.py` supplies a plain
`/cmd_vel` smoke/teleop adapter to `/cmd_vel_teleop` and instantiates the
existing arbiter. For Nav2, the existing collision monitor and relay feed
`/cmd_vel_gated` into that arbiter. Only the arbiter publishes the final
controller topic. Do not launch a second arbiter, Gazebo controller, robot
state publisher, or clock source on the Isaac ROS domain. The Isaac backend
rejects stale commands after 0.5 simulated seconds and applies the existing
velocity and acceleration limits before setting joint velocity targets.

Gazebo also publishes `/imu`, `/camera/points`, `/model/coco/odometry`, arm and
gripper states, and `/magnet/<target>/{attach,detach,state}`. Isaac does not
yet satisfy those mission/manipulation interfaces. Its `/scan` is 360°/480
beams rather than Gazebo's 240° front arc. Isaac odometry is simulator ground
truth in an odom frame; Gazebo navigation uses wheel odometry. These are
material differences for cross-simulator comparisons.

## Setup and reproduction

Verified host: Ubuntu 24.04, ROS 2 Jazzy, Isaac Sim **4.5.0.0** pip install
at `~/isaac-sim/venv`, NVIDIA RTX 4050 Laptop GPU with 6141 MiB VRAM and
driver 580.173.02. Isaac's process uses the bridge's bundled Humble libraries
and Python 3.10; host ROS stays Jazzy/Python 3.12. Both use CycloneDDS on a
private loopback domain. The launcher isolates the Isaac environment rather
than sourcing Jazzy into it. The small scene ran on this host; full Isaac
workloads are not implied to fit its GPU/RAM.

```bash
cd /home/gautham/coco-isaac-21
bash scripts/build_overlay.sh /home/gautham/coco_isaac21_ws --packages-up-to coco_sim gazebo_models custom_teleop coco_mission coco_perception
export COCO_WS=/home/gautham/coco_isaac21_ws
source setup_env.sh
python3 scripts/isaac_smoke.py /tmp/coco-isaac21-smoke-new --domain 81
python3 scripts/isaac_smoke.py /tmp/coco-isaac21-nav-new --domain 81 --nav --raw-evidence /tmp/coco-isaac21-smoke-new/result.json
```

Each output path must be new. The harness owns and stops only its child
process groups, records the ROS graph and observations, and checks all exit
codes. `--gui --rviz` is optional and consumes more graphics memory. For
manual use, start `scripts/isaac_sim_coco.sh --output NEW_DIRECTORY` in one
terminal, `python3 scripts/isaac_ros.py --ros-args -p use_sim_time:=true`
in another, then use the existing Nav2 launch with `arbiter:=true` and the
fixture map from `scripts/isaac_fixture_map.py`. The harness also writes a
run-local Nav2 parameter copy with the fixture map filename, needed by the
noncomposed Nav2 launch on this installation.

Required environment: `COCO_WS` selects the isolated Jazzy overlay;
`ROS_DOMAIN_ID` selects a private domain for manual runs. The wrapper fixes
`ROS_DISTRO=humble`, `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` and bridge
library paths **inside Isaac only**. No external account or container is
required. The wrapper expects Isaac at `~/isaac-sim/venv`.

## Validation and limits

The new backend's pure configuration/model tests, shared robot-constant
guards and command wiring tests run in the isolated overlay. The focused
port and wiring check passed **73 tests** (six live-graph tests deselected
because they require a separately started graph). The P03D/autonomy and
related static regression selection passed **404 tests**, with nine style
checks deselected. The nine package suites, run separately to avoid duplicate
pytest module names, passed **1,887 tests**, with **7 skipped** MoveIt
tests and **6 deselected** live-graph tests. Final `flake8 --select=E,F`
on the new Python files passed. Live evidence and numerical results for this branch are
under [`docs/data/isaac_21/`](data/isaac_21/README.md).

Two live raw runs passed 19/19 checks each; the final run delivered
RGB/depth/scan/odom at 15.000/15.000/10.000/30.000 Hz in simulation time.
A 0.5 m/s command over 8.0 simulation seconds produced 3.865 m x
displacement. Command dropout stopped the base. Isaac and all owned ROS
peers exited zero. Two Nav2 runs used the existing launch, planner,
collision monitor, relay and arbiter, and completed the same map-frame
`(1.5, 0.5)` goal with action status SUCCEEDED. Their final map position
errors were 0.140 and 0.095 m, with 1.705 and 1.718 m odom displacement
from action start to finish. The arbiter was the sole publisher to
`/diff_drive_controller/cmd_vel`; all Nav2 and Isaac processes exited zero.
These are two measured executions of one simple goal, not a broad
repeatability estimate.

For an initial cross-simulator frame of reference, historical Gazebo
measurement in `docs/RESULTS.md` has scan/RGB/odom at 10.0/15.2/50.0 Hz
in simulation time, while this Isaac fixture measured 10.0/15.0/30.0 Hz.
The Gazebo Nav2 tour and these Isaac goals use different worlds, maps,
sensor fields of view and odometry sources. Therefore goal success and
position error are reported separately, without claiming parity.
The earlier `p03-isaac-backend` branch also contains raw development runs,
including failures; its two composed Nav2 goals succeeded behaviorally but
the Nav2 container crashed on shutdown, and a later noncomposed goal
aborted. Those runs are provenance, not a pass attributed to this branch.

Next required engineering work is a full articulated arm/gripper model and
magnet/grasp interface, perception execution against Isaac targets, realistic
odometry, then a P03D search in a corresponding world. The fixture's
navigation metrics cannot be compared one-to-one with the Gazebo ramp arena.
