#!/usr/bin/env bash
# Six unchanged logical episodes, fresh owned processes and unique outputs.
set -o pipefail
cd /home/gautham/coco-isaac-21 || exit 1
export COCO_WS=/home/gautham/coco_isaac21_ws
export COCO_MOVEIT_PREFIX=/home/gautham/coco_p03d_ws/moveit_prefix/root/opt/ros/jazzy
source setup_env.sh || exit 1
RUN_ROOT="${1:-/home/gautham/coco24_final_runtime}"
mkdir -p "$RUN_ROOT"
for backend in isaac gazebo; do
    for seed in 6 7 8; do
        out="$RUN_ROOT/${backend}_seed${seed}"
        if [ -e "$out" ]; then
            echo "REFUSING existing run directory $out"
            exit 2
        else
            echo "START $backend seed=$seed $(date -u +%FT%TZ)"
            python3 scripts/isaac_fetch.py "$out" --backend "$backend" \
                --level positions --seed "$seed" --colour red --domain 82 --timeout 1200 \
                > "$RUN_ROOT/${backend}_seed${seed}_runner.log" 2>&1
            code=$?
            echo "END $backend seed=$seed exit=$code $(date -u +%FT%TZ)"
            echo "$backend $seed $code" >> "$RUN_ROOT/matrix_exits.txt"
        fi
        # Do not propagate an unsuccessful new retreat controller through a batch.
        python3 - "$out" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text())
states=r.get('states',[])
if any(a=='RETREAT' and b not in ('NAVIGATE_TO_RAMP','RETURN_HOME') for a,b in zip(states,states[1:])):
    print('STOP: retreat did not reach verified near exit; inspect this evidence')
    sys.exit(3)
PY
        check=$?
        if [ "$check" -ne 0 ]; then exit "$check"; fi
    done
done
