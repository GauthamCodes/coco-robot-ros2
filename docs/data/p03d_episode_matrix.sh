#!/usr/bin/env bash
# Twelve fresh Gazebo missions. Each completed run has its own evidence dir.
set -u
WT="${COCO_WT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
ROOT="${1:-$HOME/coco_p03d_runs}"
: "${COCO_WS:?set COCO_WS to the P03D overlay}"
mkdir -p "$ROOT"

# Seed 1/red is deliberately adversarial: fixed red is lane_1, this
# episode puts red in lane_2. Other seeds exercise farther regions.
RUNS=(
    'fixed_red fixed 0 red'
    'colours_s1_red colours 1 red'
    'positions_s1_red positions 1 red'
    'fixed_green fixed 0 green'
    'colours_s2_red colours 2 red'
    'positions_s2_red positions 2 red'
    'fixed_blue fixed 0 blue'
    'colours_s5_red colours 5 red'
    'positions_s5_red positions 5 red'
    'fixed_yellow fixed 0 yellow'
    'colours_s7_red colours 7 red'
    'positions_s7_red positions 7 red'
)
for spec in "${RUNS[@]}"; do
    read -r name level seed colour <<< "$spec"
    if [ -f "$ROOT/$name/result.json" ]; then
        echo "=== $name already recorded; skipping"
        continue
    fi
    echo "=== $name starting $(date -u +%FT%TZ)"
    bash "$WT/docs/data/p03d_episode_run.sh" \
        "$ROOT/$name" "$level" "$seed" "$colour"
    echo "=== $name runner exit $? $(date -u +%FT%TZ)"
    # The runner tears down its process groups and scopes ros_clean.sh
    # before returning. No second cleanup runs here.
done
