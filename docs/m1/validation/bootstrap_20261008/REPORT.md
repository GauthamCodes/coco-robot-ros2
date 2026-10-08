# NON_QUALIFYING bootstrap checkpoint — foreign-process safety stop

Start SHA `7071727674ff7c375d05a61c831600bdca8a91ee`; implementation commit
`6be2dfaa98d3a0cc0618258716029e43c5cd7fc8`. Expected branch, clean entry;
Master Plan copies compare byte-identical. Neither copy changed.
Milestone M1 / M1.1, authorized bounded RGB-D prerequisite engineering.

**Primary sensor/observer deliverable NOT ACHIEVED. Stop condition7 reached.**
No simulator child launched, no camera sample recorded, no physical manipulation
attempt. Bootstrap gate implementation is **IMPLEMENTED**, with36 focused local
policy/abort/calibration-rejection/production-qualification tests passing (not CI
or simulator lifecycle verification). No RUNTIME VERIFIED or MEASURED claim.

## Concrete progress

`./eval/bin/eval bootstrap --backend {gazebo|isaac} --seconds 120 --domain 82
--output EXTERNAL_NEW_DIRECTORY` is implemented separately from `run_batch`.
The CLI never registers a campaign, emits batch summaries, writes runtime
validation or uses production-qualifying verdicts. Manifests always record
NON_QUALIFYING, qualified=false, denominator eligibility=false, M1.8=false,
Test A=false. Dev5 fixed; no seed/task/geometry/safety/motion override.
Production qualify(), host_policy.json, calibration.py, oracle.py, thresholds,
campaigns, seeds and topic contract are unchanged.

Conservative emergency reserve derivation is recorded separately from production
requirements in safety_envelope.json: physical RAM16,458,551,296 bytes; reserve
8,229,275,648 bytes (half capacity exceeds16×67,584KiB kernel min-free reserve).
GPU6,439,305,216 bytes; reserve2,146,435,072 bytes (one third). Load≤12, original
1GiB run/8GiB root/2GiB free disk protection. These are policy safety budgets,
**derived**, not measured production requirements or a hardware incapacity proof.
Host cgroup ancestors inspected read-only have memory.max=max. No kernel quota
is configured;1Hz emergency watchdog cannot prevent between-sample allocation
bursts. Simulator suitability remains NOT VERIFIED.

Owned roots use new sessions; descendants require current parentage/PID/start
identity. Existing owned-group teardown is reused; recorder stops last.
Runtime samples persist CPU/load/RAM/VRAM/disk/clock-derived RTF at1Hz including
startup; ceiling violations stop owned workload and preserve evidence under
ABORTED_BOOTSTRAP_RESOURCE_LIMIT. Recorder process locally extends fixed-topic
capture with RGB/depth/CameraInfo at1Hz alongside TF/candidates/mission evidence.
Ground truth is evaluator-only for post-run validation. Live teardown, sensor
stream timing, geometry and post-run oracle scoring remain NOT VERIFIED.

## Actual execution

Both bootstrap commands executed in env-i, no startup files, explicit
coco_m1_ws/MoveIt underlay, Jazzy, loopback CycloneDDS/Gazebo, domain82.
Both ended BLOCKED_BOOTSTRAP with empty owned_processes. Full raw inventories,
manifest, environment, production policy and ceiling remain outside Git;
external_evidence.json records every file hash. gate_results.json preserves
compact current verdicts. No broad process cleanup or allowlist exemption.

Gazebo blockers:

- Foreign Gazebo111827/start2051123/domain115, `/usr/bin/ruby3.2`, cwd
  `/home/gautham/ros2_ws`, argv `gz sim server`, parent user systemd2519.
- `/proc/60465/exe` permission denied. Read-only comm/argv/status identify
  UID1000 ssh-agent under GNOME-keyring parent2545; no ownership or robotics
  classification exemption inferred from inaccessible executable/maps.
- Available RAM7,793,401,856 bytes below8,229,275,648 bootstrap reserve.

Isaac: same foreign process/metadata blockers plus opposite-backend conflict;
available RAM7,766,237,184 bytes below the same reserve. These are instantaneous
inventory values, not workload peaks or calibrated envelope measurements.
Foreign-workload release may change headroom; this session did not reduce the
safety budget in response to failure or retry unchanged launches.

Fresh original production preflights separately reject foreign Gazebo, unknown
metadata and null RAM/VRAM requirements. Isaac additionally rejects opposite
backend. No production resource values invented. Capacity is not proven inadequate.

## Remaining engineering and exact continuation

Sensor visibility/placement/near-plane/depth/geometry: NOT VERIFIED on both.
Observer/consumer: NOT IMPLEMENTED, respecting rendered feasibility first.
Exact proposed ROS2 contract remains
`docs/m2/target_observation_20261008/OBSERVATION_CONTRACT.md` and the approved
`gate_target_height_20261008/proposed_patch.md`; not a live producer contract.
No observation/grasp/attachment/lift/release/oracle runtime evidence.
Focused observation/replay/ROS tests not run because no observer exists.
Root-caused-and-fixed ROOT_CAUSES entry not created without system verification.
Full-stack envelope not measured on either backend; all CPU/RAM/VRAM/RTF workload
maxima unavailable.19 calibration dependencies unresolved, smoke0/4,
M1.8 not started0/140. No held-out data opened. Production limits remain null.

Smallest human action: owning domain115 session releases its Gazebo; restore
inspectable process metadata for60465 or provide verified provenance permitting
a narrowly reviewed background classification (never broad cleanup). Host must
also meet committed bootstrap headroom after owner release. No request to add a
sensor, change task geometry or weaken safety. No sensor impossibility established.

Then, with clean committed worktree:

```bash
cd /home/gautham/coco-isaac-21
export COCO_WS=/home/gautham/coco_m1_ws
export COCO_MOVEIT_PREFIX='/home/gautham/ros2_ws(personal)/moveit_prefix/root/opt/ros/jazzy'
source setup_env.sh
./eval/bin/eval bootstrap --backend gazebo --seconds 120 --domain 82 \
  --output /home/gautham/coco_m1_runs/bootstrap-resume-NEW/gazebo
```

Use new output paths; prior attempts are exclusive/append-only. This runs the
unchanged controlled Dev5 episode and records actual camera evidence through
reachable phases. It does not prove mandatory lift/release visibility or solve
the placement search. Inspect frames/TF, conduct the bounded approved placement
experiment, then implement observation and consumer only after visibility proof.
Gazebo control → Isaac control → full-stack envelope → original production gates
→ qualified Dev calibration → unchanged qualified smoke → M1.8 remain conditional.
This capability breaks the policy cycle in code, but the foreign-host safety gate
prevents executing it today. No claim of M1 completion or minimum sensor result.

Safety semantics changed: NONE. Ground truth used by autonomy: NONE.
Exact changed sources: eval/bootstrap.py, eval/bootstrap_recorder.py,
eval/cli.py, eval/tests/test_bootstrap.py; documentation: eval/README.md,
docs/STATUS.md and this evidence directory.
