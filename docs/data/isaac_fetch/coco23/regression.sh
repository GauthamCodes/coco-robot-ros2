#!/usr/bin/env bash
# One package-scoped relevant regression sweep after the simulation batch.
cd /home/gautham/coco-isaac-21 || exit 1
export COCO_WS=/home/gautham/coco_isaac21_ws
export COCO_MOVEIT_PREFIX=/home/gautham/coco_p03d_ws/moveit_prefix/root/opt/ros/jazzy
source setup_env.sh
export ROS_DOMAIN_ID=85
OUT=/home/gautham/coco-isaac-21/docs/data/isaac_fetch/coco23/tests
mkdir -p "$OUT"
for package in coco_config coco_sim coco_mission coco_perception coco_moveit_config custom_teleop gazebo_models coco_rl coco_web; do
    (cd "$package" && python3 -m pytest -q test) > "$OUT/$package.log" 2>&1
    echo "$package $?" >> "$OUT/exits.txt"
done
