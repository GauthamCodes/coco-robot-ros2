#!/usr/bin/env bash
# Execute, do not source. Isaac's bundled Humble is process-local.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISAAC="$HOME/isaac-sim"
PY="$ISAAC/venv/bin/python"
BRIDGE="$ISAAC/venv/lib/python3.10/site-packages/isaacsim/exts/isaacsim.ros2.bridge/humble/lib"
[[ -x "$PY" && -d "$BRIDGE" ]] || { echo "Expected Isaac Sim 4.5 at $ISAAC" >&2; exit 2; }
# An advisory lock prevents two COCO Isaac launches; never kills a process.
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/coco-isaac-${UID}.lock"
flock -n 9 || { echo 'Another COCO Isaac instance owns the lock' >&2; exit 2; }
exec env -i HOME="$HOME" PATH=/usr/bin:/bin \
    DISPLAY="${DISPLAY:-}" XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" \
    XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$UID}" \
    OMNI_KIT_ACCEPT_EULA=YES ROS_DISTRO=humble \
    RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-78}" \
    CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo" multicast="true"/></Interfaces></General></Domain></CycloneDDS>' \
    LD_LIBRARY_PATH="$BRIDGE" \
    COCO_GAZEBO_SHARE="$REPO/gazebo_models" \
    PYTHONPATH="$REPO/coco_config:$REPO/coco_sim" \
    "$PY" -m coco_sim.isaac.runtime "$@"
