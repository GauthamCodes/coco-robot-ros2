#!/usr/bin/env bash
set -euo pipefail
TASK_ISAAC=/home/gautham/isaac-sim
TASK_BRIDGE="$TASK_ISAAC/venv/lib/python3.10/site-packages/isaacsim/exts/isaacsim.ros2.bridge/humble/lib"
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/coco-isaac-${UID}.lock"
flock -n 9
exec env -i HOME="$HOME" PATH=/usr/bin:/bin OMNI_KIT_ACCEPT_EULA=YES ROS_DISTRO=humble \
 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_DOMAIN_ID=83 \
 LD_LIBRARY_PATH="$TASK_BRIDGE" \
 PYTHONPATH=/home/gautham/coco-isaac-21/coco_config:/home/gautham/coco-isaac-21/coco_sim \
 "$TASK_ISAAC/venv/bin/python" docs/data/isaac_fetch/coco22/release_probes/release_grasp_probe.py "$@"
