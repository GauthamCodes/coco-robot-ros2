# P0.2 hardening verification

These checks validate isolated components. They do not deploy Docker, run
a mission, launch Gazebo, change QoS, or enable depth fusion.

## Recorded evidence

[evidence/validation.json](evidence/validation.json) aggregates the nine
per-package JUnit XML files. The final coco_web.xml supersedes the earlier
465-test web run with 470. Other package results were unchanged after the
final binary-only fix. build.log records the initial nine-package private
build; final-build.log records the final affected-package rebuild.
ros-smoke.log is a real ROS/WebSocket test with synthetic data, not a
simulator or hardware result. The red logs record failures before fixes.
Warnings are retained, not suppressed.

## Reproduce

Use Bash. Set these locations for your checkout and machine:

```bash
export P02_REPO=/path/to/coco-p02-hardening
export P02_OUT=/tmp/coco-p02-validation-new
export COCO_MOVEIT_PREFIX=/path/to/moveit_prefix/root/opt/ros/jazzy
unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH
source /opt/ros/jazzy/setup.bash

# Omit this block if MoveIt is installed in the normal ROS prefix.
export AMENT_PREFIX_PATH="$COCO_MOVEIT_PREFIX:$AMENT_PREFIX_PATH"
export CMAKE_PREFIX_PATH="$COCO_MOVEIT_PREFIX:$CMAKE_PREFIX_PATH"
export LD_LIBRARY_PATH="$COCO_MOVEIT_PREFIX/lib:$COCO_MOVEIT_PREFIX/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"
export PYTHONPATH="$COCO_MOVEIT_PREFIX/lib/python3.12/site-packages:$PYTHONPATH"

mkdir -p "$P02_OUT"
colcon --log-base "$P02_OUT/build-logs" build \
  --base-paths "$P02_REPO" --build-base "$P02_OUT/build" \
  --install-base "$P02_OUT/install" --symlink-install \
  --packages-select coco_config coco_mission coco_moveit_config coco_perception \
    coco_rl coco_sim coco_web custom_teleop gazebo_models
source "$P02_OUT/install/setup.bash"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_LOCALHOST_ONLY=1
export ROS_DOMAIN_ID=97  # choose an unused domain
bash "$P02_REPO/diagnostics/p02_hardening/run_checks.sh" "$P02_OUT/tests"
export ROS_DOMAIN_ID=98  # choose a second unused domain
python3 -P "$P02_REPO/diagnostics/p02_hardening/ros_smoke.py"
```

Node is required only for test_frontend_transport.py (standard Node test
runner; no npm dependencies). ROS/Python/OpenCV and the repository's existing
test dependencies are required. Gazebo launch integration tests remain
excluded, following the existing per-package test procedure.

The smoke launches the production ROS node and Tornado handler on a loopback
ephemeral HTTP port, publishes synthetic RGB/depth/LiDAR and odometry, and
records teleop intents only within the selected domain. It uses positive
nonzero control observations before testing both STOP mechanisms. It owns
and closes its own executor, node, publishers, subscriptions, HTTP server and
socket. Its internal deadline is 30 seconds. It creates no wheel publisher.
