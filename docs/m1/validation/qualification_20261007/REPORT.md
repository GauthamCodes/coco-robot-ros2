# M1 qualification forensic checkpoint — 2026-10-07

Evidence label: **IMPLEMENTED** inspection/provenance; qualified runtime **NOT
VERIFIED**. Entry HEAD `ceeb914923f7629b4830d58fd3b47279044b2024`, expected branch
`coco-2.1-isaac-integration`, clean. Downloads and canonical plans byte-identical.
Milestone M1, checkpoint M1.1; advances dirty-host provenance and safe ownership
reconciliation required before a qualified batch. No implementation rewrite.

## Concrete blocker and decision

`daemon_forensics.json` identifies PID260322/start8029900, UID1000, Jazzy
CycloneDDS daemon on domain66. CWD is the `.claude/worktrees/lab1` directory;
COCO_WS and ament/colcon/Python/library paths belong to `coco_search_ws`.
The daemon is in a GNOME terminal user cgroup, root namespace, PPID2244 (user
systemd). Source/origin is established as another COCO workspace; M1 ownership
or staleness is not established. Normal daemon reparenting is not evidence of
an orphan. It is an actually foreign user-level ROS participant for this runner,
not a qualification classification bug. Only the existing `/proc` metadata was
read; unrelated worktree files were not inspected or modified.

**Stop condition 1:** safe cleanup ownership cannot be established as stale
M1-owned. No signal, daemon shutdown or allowlist change performed. The owner of
the lab/search domain66 session must confirm that the daemon is no longer needed
and release it. If the owner confirms, the owner may use the original ROS shell:

```bash
ROS_DOMAIN_ID=66 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 daemon stop
```

This command was **not executed**. Domain selection alone does not authorize
shutdown; confirm current PID/start identity and ownership first. Do not signal
unrelated PIDs or delete DDS state. No current Gazebo/Isaac workload, DDS segment
or inventory error was detected. Different ROS domains isolate the graph but do
not satisfy the plan's no-foreign-workload host rule.

## Clean environment and preflight

`clean_environment.json`: env -i, bash --noprofile --norc, explicit COCO_WS
`/home/gautham/coco_m1_ws`, explicit personal MoveIt binary underlay, Jazzy,
domain82, rmw_cyclonedds_cpp, CycloneDDS loopback, GZ harmonic/127.0.0.1,
Python `/usr/bin/python3` 3.12. No competing COCO overlay is sourced. No global
shell changes. `host_preflight.json` captures all processes and both backend
verdicts from that environment. Both fail only on the foreign daemon and null
preflight RAM/VRAM limits. Load1 3.8603515625 versus12; available RAM9690378240
bytes; GPU free5643436032/total6439305216 bytes. These are inventory readings,
not a resource envelope or hardware-capacity verdict.

## Calibration and remaining measurement dependencies

`calibration_dependency_audit.json` hashes current qualification, trace/analyzer,
calibration and manipulation sources; maps all 19 null threshold keys to raw
fields/invariants. CPU/load12 is the committed logical-capacity ceiling, not a
measured successful-control timing limit. RAM/VRAM preflight/runtime remain null
for both backends. Historical foundation samples lack fetch/ROS/MCAP overhead.
RTF and clock/timing/geometry limits require qualified oracle-PASS Dev controls,
normalized traces and justified margins under eval/calibration.py. None produced.
No simulator resource probe attempted while the foreign gate fails.

ArmControl.target_height returns None; grasp_magnet rejects before calling the
magnet; GraspServer inherits the path. This approved M0 boundary is preserved.
A legitimate successful-control prerequisite is unresolved, not permission to
inject truth or alter behavior. Remaining raw witnesses: I07 motion association,
I12 independent world-free costmap, I13 exact plan-return source timing, I14
clearance, I16 truth projection, I18 physical identity, I21 proximity, I23 finger
before detach, I25 progress. They were inspected, not changed after the stop.

## Exact continuation

After owner release, rerun read-only qualification from this clean environment:

```bash
cd /home/gautham/coco-isaac-21
env -i HOME=/home/gautham USER=gautham PATH=/usr/bin:/bin /bin/bash --noprofile --norc -c '
export COCO_WS=/home/gautham/coco_m1_ws
export COCO_MOVEIT_PREFIX="/home/gautham/ros2_ws(personal)/moveit_prefix/root/opt/ros/jazzy"
export ROS_DOMAIN_ID=82
source setup_env.sh
./eval/bin/eval preflight --backend isaac --output /tmp/coco-m1-after-owner-preflight.json
'
```

Use a new output name if it already exists; outputs are exclusive. Owner release
resolves only the foreign process gate. It does not fill resource limits or
successful-control calibration. Resolve a documented resource-calibration path
and legitimate control evidence with the plan owner before simulation if existing
prerequisites remain unsatisfiable; do not substitute idle free-memory readings
or unqualified missions. Then finish measurement witnesses, qualified sequential
smoke, inspect/validate proof, and only then committed M1.8 campaigns.

No package/code/campaign/threshold changes or tests rerun. Read-only forensic and
preflight checks completed. Qualified/unqualified/failed/unclassified simulated
runs0/0/0/0; no smoke, no baseline, no oracle/mission agreement evidence. No new
M2 hypotheses, Test A inspection, reserve use or IDEAS additions. This checkpoint
is a stop report, not calibration/measurement/smoke completion.
