#!/usr/bin/env bash
# Run from any directory after setting COCO_WS and (if needed) COCO_MOVEIT_PREFIX.
set -eo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT="${1:?new evidence directory required}"
mkdir "$OUT"
OUT="$(cd "$OUT" && pwd)"
source "$REPO/setup_env.sh" > "$OUT/setup.log" 2>&1
export ROS_DOMAIN_ID=176
export COCO_GTI_EVIDENCE="$OUT/graphs"
for package in coco_config coco_mission coco_moveit_config coco_perception coco_rl coco_sim coco_web custom_teleop gazebo_models; do
    (cd "$REPO/$package" && python3 -m pytest -q test --junitxml="$OUT/$package.xml") > "$OUT/$package.log" 2>&1
    tail -n 1 "$OUT/$package.log"
done
(cd "$REPO" && python3 -m pytest -q eval/tests --junitxml="$OUT/eval.xml") > "$OUT/eval.log" 2>&1
tail -n 1 "$OUT/eval.log"
