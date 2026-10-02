# Isaac fetch consolidation evidence

Starting state: clean `569b81ff744c2542498bd37201ef509b3ec4b949`, branch
`coco-2.1-isaac-integration`, worktree `/home/gautham/coco-isaac-21`.
Implementation commit: `dab3115` (follow-up evidence commit also hardens
non-finite feedback/height checks and explicit verification-overlay selection).

Work was performed on 2026-10-02/03 with Isaac4.5, Jazzy host and bundled
Humble bridge on private loopback domain82. Tests used domain85.
Old `isaac_21` and P03D evidence directories are unchanged.

## What the records establish

**Implemented:** URDF-derived articulated arm/gripper (including inertia,
collision and canonical CAD visuals), canonical ramp/target arena, shared
MoveIt trajectory action, measured joint feedback/TF/IMU, proximity-gated
physical fixed-joint magnet and height verification, same P03D mission launch.
No new wheel publisher or mission implementation exists.

**Tested:** 1,941 unique package tests passed, zero skipped, including nine
style tests and six self-contained live ROS graph tests. Counts and individual
logs are in `tests/summary.json`. This is an aggregate of per-package regression
commands, not a fabricated single-suite transcript. Four launch tests initially
failed because the simulator launch substitution lacked its default; the
corrected full mission/nav selection passed371. An attempted multi-package
pytest command encountered duplicate test-module names; per-package runs
corrected that invocation. Both initial failures are retained.

Nine packages build successfully (`build_overlay_final.log`); canonical URDF
passes `check_urdf` (`urdf_check.log`). Changed-code flake8 E/F checks pass,
excluding E501 for existing long lines (`static.log`, empty means success).
External GitHub CI and Docker runtime were not executed.

**Runtime verified:** generated articulation starts with all eight joints;
all four targets settle within the episode placement checks; shared Nav2,
arbiter and mission run; run006 reaches climb verification, positive RGB-D
pose, SEARCH_TARGET, physical MoveIt STOW_ARM and APPROACH_TARGET.

**Not verified:** successful close approach, magnet attach/lift/release,
return with an object, COMPLETE, displaced-target full search and quantitative
Gazebo/Isaac full-fetch parity. No full-fetch success is claimed.

## Runtime attempts (all retained)

| Record | Outcome / engineering finding |
| --- | --- |
| `build_001` | Invalid XML comment in canonical SDF stopped scene construction; fixed comment only |
| `build_004` | JointState array mutation type error after articulation startup; fixed array handling |
| `build_005` | Clean 12-sim-second articulation/target placement smoke |
| `run_001` | Shared launch could not find coco_sim libexec; added standard ROS setup.cfg |
| `run_002` | Nested noncomposed map selection loaded map.yaml instead of requested map; corrected shared launch YAML rewrite; orphan from prior failed launch exposed shutdown gap |
| `run_003` | Mission reached CLIMB then aborted at 0.28m lateral displacement; wheel drive0.4Nm experiment rejected, validated fixture2Nm restored |
| `run_004` | Nav2 lifecycle activation failure; readiness did not start mission; deliberately interrupted and preserved |
| `run_005` | Navigation failed with position-only progress checker; safe ABORT |
| `run_006` | Rotation-aware progress check: navigation, climb, positive perception, measured arm stow, approach; target lost during alignment, retry, descent recovery timeout, ABORT |
| `run_007` | Canonical CAD arm visuals initialize; navigation fails before grasp; evaluator camera/depth snapshots captured |
| `run_008` | Wheel feedback gain20 experiment also fails navigation; rejected and gain1 restored |

The failure matrix is evidence of remaining integration work, not an assertion
that any individual parameter caused every failure. Rotation-aware progress
helped run006 but did not make navigation repeatable. The two existing goal
tolerances remain pinned at their baseline values. Safety polygon parameters,
arrival gates, mission recovery and P03D search transitions were not relaxed.

## Measurements

Run006 reached SEARCH_TARGET at sim95.09s, STOW_ARM95.46s and approach98.66s.
A representative valid pose at sim102.43s: red blob u144/v114, width9pixels,
range0.5886m, base pose `(0.7136, +0.0417, 0.0841)`m,
grasp-band projection z0.128m, depth valid fraction0.9973, spread0.0010m,
frame `base_footprint`, reported TF age0. Its target geometry remains world-side.
MoveIt stow finished from measured shoulder/elbow feedback approximately
`(-1.197, -0.498)`rad for commanded `(-1.2, -0.5)`rad.

Run006 mission elapsed164.2667sim seconds /250.4948wall seconds, ending in
ABORT after one approach retry and descent timeout. Observed rates per sim
second: joints/odom/IMU30.01Hz, scan10.00Hz, RGB11.20Hz, depth10.66Hz.
Zero nonzero final-wheel samples were observed in27 idle-mode samples.
A final 8-sim-second stationary LiDAR probe found zero self-hit rays at the
home pose, so self-interference was not established as the navigation cause.
It initializes the final CAD visuals and restored gain1 model. Other arm
poses were not checked by that probe.
This is sampled evidence, not proof for every instant. The recorded ROS graph
shows the cmd_vel_arbiter as the sole final wheel-command publisher.

Settled-target smoke errors are tens of micrometres in XY, a few micrometres
in Z and below0.0005rad tilt (`build_005_targets.json`). Simulator numeric
agreement is not a claim about real hardware accuracy.

## Reproduction and provenance

See [the authoritative Isaac commands](../../COCO_2_1_ISAAC.md).
Each full attempt used:

```bash
export COCO_WS=/home/gautham/coco_isaac21_ws
export COCO_MOVEIT_PREFIX=/home/gautham/coco_p03d_ws/moveit_prefix/root/opt/ros/jazzy
source setup_env.sh
python3 scripts/isaac_fetch.py /tmp/coco-isaac-fetch-008 --domain 82 --timeout 600
```

Use a fresh output path and the desired run number. `meta.json` records argv,
starting HEAD and dirty status; `source.patch.gz` archives tracked changes.
Attempts were made during development, before the implementation commit;
early patches do not snapshot then-untracked modules. Their scope/version
limitations are explicit. Run008 additionally records SHA256 for source and
config files, including untracked implementation. Later reproduction should
run the committed tree. Manifest/task-only inputs, measured scene placement,
command graph, final poses/joints, transitions, timing and exit status are
retained per run. Full ROS observations and logs are gzip-compressed:

```bash
gzip -dc docs/data/isaac_fetch/run_006/observations.jsonl.gz
gzip -dc docs/data/isaac_fetch/run_006/mission.log.gz
```

Generated USD/URDF are reproducible from the committed sources and unchanged
assets and are not duplicated in Git. The temporary run directories retain
those generated artifacts locally. Evaluator snapshots in runs007/008 (depth arrays losslessly gzip-compressed) are
not inputs to autonomy. The runner stops only its own process groups, including
orphans, and never uses global cleanup or teleports the robot/targets.

Final stationary probe command:

```bash
ROS_DOMAIN_ID=82 bash scripts/isaac_sim_coco.sh --fetch \
  --robot-urdf /tmp/coco-isaac-fetch-008/robot.urdf \
  --episode-manifest /tmp/coco-isaac-fetch-008/manifest.json \
  --output /tmp/coco-fetch-self-lidar --seconds 8
```

Archive: `final_stationary_probe.log.gz` and `final_stationary_targets.json`.

Gazebo P03D history and mission-state logic remain intact; no fresh Gazebo
full-fetch runtime was run in this session after the shared safety/Nav2 repairs.
Those changes have regression coverage, not a new Gazebo mission measurement.

Baseline AST/module ownership inventory: `architecture_inventory.json`.
Source hashes for the final tested code: `final_source_sha256.json`.
