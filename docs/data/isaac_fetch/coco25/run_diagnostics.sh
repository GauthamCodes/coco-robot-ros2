#!/usr/bin/env bash
# Same episode definitions/profiles as COCO24, sequential fresh simulators.
set -o pipefail
cd /home/gautham/coco-isaac-21 || exit 1
export COCO_WS=/home/gautham/coco_isaac21_ws
export COCO_MOVEIT_PREFIX=/home/gautham/coco_p03d_ws/moveit_prefix/root/opt/ros/jazzy
source setup_env.sh || exit 1
root="${1:?Supply a NEW runtime root}"
if [ -e "$root" ]; then
    echo "REFUSING existing runtime root $root" >&2
    exit 2
fi
# Read process inventory only. Never stop an unrelated workload.
python3 - <<'PY'
from pathlib import Path
import sys
busy=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():
        continue
    try:
        comm=(p/'comm').read_text().strip()
        argv=(p/'cmdline').read_bytes().split(b'\0')
    except (OSError,PermissionError):
        continue
    title=b' '.join(argv).decode(errors='replace').strip()
    if (title.startswith('gz sim ') or comm.startswith('gz sim') or
            b'coco_sim.isaac.runtime' in argv):
        busy.append((p.name,comm))
if busy:
    print('BLOCKED: existing simulator; host is not idle:',busy,file=sys.stderr)
    sys.exit(3)
PY
check=$?
if [ "$check" -ne 0 ]; then exit "$check"; fi
mkdir -p "$root"
for backend in isaac gazebo; do
    for seed in 6 7; do
        out="$root/${backend}_seed${seed}"
        echo "START $backend seed=$seed $(date -u +%FT%TZ)"
        python3 scripts/isaac_fetch.py "$out" --backend "$backend" \
            --level positions --seed "$seed" --colour red --domain 82 --timeout 1200 \
            --diagnostic-script docs/data/isaac_fetch/coco25/diagnostic_trace.py \
            > "$root/${backend}_seed${seed}_runner.log" 2>&1
        code=$?
        echo "$backend $seed $code" >> "$root/matrix_exits.txt"
        echo "END $backend seed=$seed exit=$code $(date -u +%FT%TZ)"
        # Fail closed on broken capture or unsuccessful safe retreat.
        python3 - "$out" <<'PY'
import gzip,json,sys
from pathlib import Path
p=Path(sys.argv[1])
rows=[json.loads(s) for s in gzip.open(p/'diagnostic.jsonl.gz','rt')]
assert rows[-1]['topic']=='recorder_end','recorder did not shut down cleanly'
assert any(r['topic']=='sample' and r['data']['costmaps'] for r in rows),'no costmap capture'
assert any(r['topic']=='candidate' for r in rows),'no search candidate capture'
r=json.loads((p/'result.json').read_text())
states=r.get('states',[])
assert not any(a=='RETREAT' and b not in ('NAVIGATE_TO_RAMP','RETURN_HOME')
               for a,b in zip(states,states[1:])), 'retreat did not reach verified exit'
PY
        check=$?
        if [ "$check" -ne 0 ]; then exit "$check"; fi
    done
done
