#!/usr/bin/env bash
set -euo pipefail
TASK_ISAAC="$HOME/isaac-sim"
TASK_REPO="$(pwd)"
TASK_PROBE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/release_probe.py"
TASK_BRIDGE="$TASK_ISAAC/venv/lib/python3.10/site-packages/isaacsim/exts/isaacsim.ros2.bridge/humble/lib"
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/coco-isaac-${UID}.lock"
flock -n 9
exec env -i HOME="$HOME" PATH=/usr/bin:/bin OMNI_KIT_ACCEPT_EULA=YES ROS_DISTRO=humble \
 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_DOMAIN_ID=83 \
 LD_LIBRARY_PATH="$TASK_BRIDGE" \
 PYTHONPATH="$TASK_REPO/coco_config:$TASK_REPO/coco_sim" \
 "$TASK_ISAAC/venv/bin/python" "$TASK_PROBE" "$@"
