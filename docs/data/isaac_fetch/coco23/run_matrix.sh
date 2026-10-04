#!/usr/bin/env bash
# Evidence-only orchestration of the unchanged shared fetch runner.
set -u
cd /home/gautham/coco-isaac-21 || exit 1
export COCO_WS=/home/gautham/coco_isaac21_ws
export COCO_MOVEIT_PREFIX=/home/gautham/coco_p03d_ws/moveit_prefix/root/opt/ros/jazzy
set +u
source setup_env.sh
set -u
ROOT=/home/gautham/coco23_runtime
mkdir -p "$ROOT"
for backend in isaac gazebo; do
    for seed in 5 6 7 8 9; do
        out="$ROOT/${backend}_seed${seed}"
        if [ -e "$out" ]; then
            echo "REFUSING existing run directory $out"
            exit 2
        fi
        echo "START $backend seed=$seed $(date -u +%FT%TZ)"
        python3 scripts/isaac_fetch.py "$out" --backend "$backend" \
            --level positions --seed "$seed" --colour red --domain 82 --timeout 1200 \
            > "$ROOT/${backend}_seed${seed}_runner.log" 2>&1
        code=$?
        echo "END $backend seed=$seed exit=$code $(date -u +%FT%TZ)"
        echo "$backend $seed $code" >> "$ROOT/matrix_exits.txt"
    done
done
