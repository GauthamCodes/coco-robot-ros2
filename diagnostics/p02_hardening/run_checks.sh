#!/usr/bin/env bash
# Run from any directory after sourcing the overlay to validate.
# ROS_DOMAIN_ID must identify an isolated test graph.
set -o pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
evidence="${1:?usage: run_checks.sh OUTPUT_DIRECTORY}"
mkdir -p "$evidence"
evidence="$(cd "$evidence" && pwd)"
status=0
for package in coco_config custom_teleop coco_rl coco_perception gazebo_models coco_moveit_config coco_sim coco_mission coco_web; do
  (cd "$repo/$package" &&
   python3 -m pytest test -q --ignore=test_integration \
     --junitxml="$evidence/$package.xml") > "$evidence/$package.log" 2>&1
  result=$?
  echo "$package exit=$result"
  tail -3 "$evidence/$package.log"
  [ "$result" = 0 ] || status=1
done
exit "$status"
