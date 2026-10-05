# Isaac fetch consolidation evidence

## COCO 2.4 — far-region search transit diagnosis and correction (2026-10-05)

Rejected search previously drove forward through an unrequested cylinder.
Saved Isaac6/7 traces show obstruction at the far crest with live commands and
clock; Gazebo6 shows cylinder ejection followed by a native ODE assertion.
Gazebo7's prior completion also displaced cylinders. Search failure now retreats
through the already climbed corridor, verifies its near exit, then navigates to
the next region. Acquired-target descent and the sole arbiter path are retained.
No wheel gain, physics, Nav2 profile, perception threshold or seed tuning changed.

**The shared unsafe transit is corrected; full-fetch repeatability remains open.**
Nine rejected-search retreats complete with nonrequested cylinders undisturbed.
Both seed8 controls physically complete; Isaac8 passes the original protocol,
Gazebo8 retains one observer idle-mode timing flag. Isaac6/7 abort on Nav2 action
acknowledgement/retry exhaustion; Gazebo6 aborts on an occupied planner start after
handoff; Gazebo7 searches all regions and fails closed on IMPLAUSIBLE_SIZE poses.
Host resource contention is recorded and not treated as proven sole causation.
431 targeted tests and six-case source/manifest/sole-authority checks pass.

[COCO2.4 evidence and reproduction](coco24/README.md) ·
[Matched comparison](coco24/comparison.json) · [Provenance checks](coco24/evidence_checks.json).

## COCO 2.3 repeatability evidence (2026-10-05)

**Verdict B: partial repeatability, with remaining failure modes.** Five matched
**positions-level** red layouts, seeds 5–9, were attempted once in each backend
at clean starting SHA `2e15706875c4850fe3a00200a9c5fd878e4b312d`.
Isaac physically completed 3/5 (60%); Gazebo 4/5 (80%). Both completed 5, 8, 9;
Gazebo also completed 7. Isaac 6/7 aborted during search-continuation descent;
Gazebo 6 suffered an ODE physics abort/stopped clock during its second descent.
Gazebo 5/9 each retain one observer idle-mode timing flag despite physical
COMPLETE; original full runner protocol passes are 3/5 Isaac and 2/5 Gazebo.
No implementation changes, parameter tuning, or episode reruns were made.
All nine relevant regression suites passed 1,952 tests. Five layouts do not
establish statistical reliability or within-seed repeatability.

[Methodology, all ten outcomes, aggregates, failure diagnosis and limitations](coco23/README.md)
· [Machine-readable comparison](coco23/comparison.json)
· [Source/architecture/evidence checks](coco23/evidence_checks.json).
Prior milestone evidence below remains unchanged and is historical.

## COCO 2.2 evidence (2026-10-03)

Starting SHA `589e1f1b8225a857d7c03ed9f019f53a5bd1efb9`, branch
`coco-2.1-isaac-integration`, initially clean. See
[`coco22/starting_state.json`](coco22/starting_state.json) and
[`coco22/diagnosis.json`](coco22/diagnosis.json). Historical milestone evidence
below is unchanged. **Isaac fetch009 is physically verified COMPLETE.**
The matching Gazebo fetch004 is also physically verified COMPLETE.

Fetch009 (replacement after the environment interruption) ran the shared
seed-5, colours-level red episode through navigation, climb, RGB-D search,
approach, acquisition, lift, descent, bypass, return, release, placement
verification and COMPLETE. All owned processes exited zero. Its measured
grasp-entry pose was `(0.154559, -0.003878, 0.079029)` m relative to
`base_footprint` (object centre); the perception-derived grasp-band handoff
was `(0.153977, -0.003673, 0.128)` m. The first lift check measured 32.8 mm.
During carry, 95 sampled palm-relative positions spanned at most 0.318 mm
over 6.063 m displacement. After detach and arm retreat, the cylinder stood
at world `(-1.817764, -0.204262, 0.079014)` m, 0.274 m from home; its up-axis
z component was 0.9999988. Four post-release samples were 79.014–79.183 mm
high. Mission runtime was 255.767 simulation / 729.476 wall seconds, with
zero RECOVERY entries and zero sampled idle-wheel breaches.

This is **one complete Isaac fetch**, not statistical reliability or physical
parity. Bypass arrival took longer than earlier attempts and had 0.352 m
physical error, accepted by the pre-existing 0.50 m consistency band; home
arrival had 0.241 m error. Neither arrival gate was relaxed. The arbiter
remains the sole final wheel publisher, recorded in `fetch_009/command_graph.json`.

| Evidence | Status / result |
| --- | --- |
| Run006 clock gap | **MEASURED:** valid fixes 0.100 s apart in simulation, 1.185 s in wall time; old 1-s wall freshness caused false loss |
| Approach timestamp / frame checks and odometry handoff | **IMPLEMENTED, TESTED, RUNTIME VERIFIED:** fetch001/003/004/005/006 enter GRASP after RGB-D approach; no target coordinates supplied to robot |
| Drive probes | **MEASURED:** 0.1 rad/s request yielded 0.0035 rad/s baseline; body-rate feedback improved response without increasing motor gains or 2 Nm ceiling; self-collision hypothesis rejected |
| Arm command delivery | **MEASURED:** old single-callback render loop accepted only 0.4167 rad of a 0.5-rad request; bounded draining delivers 0.5 rad |
| Physical magnet and carry | **RUNTIME VERIFIED:** fetch005 first-attempt attach/lift; 44 samples over 2.62 m, palm-relative span below 0.149 mm |
| Release / placement | **RUNTIME VERIFIED, MEASURED:** fetch009 separates and stands upright near home; mesh floor, preserved acquisition pitch and open-before-detach address distinct failures |
| Navigation | **MEASURED:** scan geometry agrees with map at one mapped-ground pose; AMCL process noise, DWB goal radius and return retry handoff investigated; reliability not established |
| Relevant regression | **TESTED:** 1,053 unique tests across six packages; final zero failures. Initial root-cwd style invocations scanned unrelated packages; corrected package scope and one new test line wrap. Raw logs retained in `coco22/tests/` |
| Gazebo full-fetch comparison | **RUNTIME VERIFIED, MEASURED:** fetch004 completes the same seed5 red episode; n=1 complete episode per backend, no parity or reliability claim |

`coco22/fetch_001`, `fetch_003`, `fetch_004`, `fetch_005`, `fetch_006`, `fetch_007`, `fetch_008`, `fetch_009`
retain full compressed simulator/mission/observer logs and ROS traces,
source patches and source digests, manifests, task-only robot inputs, graph,
exit codes and offline measurements. `fetch-002` retains the startup logging
failure (non-serializable numpy value), fixed by float conversion. Drive probe
records and rejected configurations are retained separately. Images and expanded
USD/URDF remain in each original `/tmp/coco22-*` directory; the durable trace
contains physical poses, arm targets, target orientations and velocities.

Fetch003 reached home while holding, then failed release. Fetch004 tested low
AMCL noise with the old 5-cm DWB rotation window, delivered the complete gripper
request but failed arm raise without welded-cluster filtering, and stalled on
return. Fetch005 used the 25-cm DWB window and canonical AMCL noise: attachment,
lift and descent succeeded, but return pose consistency failed (0.95 / 0.60 m).
The shared retry code re-seeded the ramp exit after navigation moved away; the
new regression prevents that. Fetch006 used low AMCL noise plus the 25-cm DWB
window: first grasp and descent succeeded, localization remained much closer,
but bypass circled at the rotation window boundary until the 600-wall-second
observation timeout. `fetch_006/dwb.json` records selected critic scores;
RotateToGoal alternates between active and zero around 0.25 m. Jazzy DWB
[resets critics on each new plan](https://raw.githubusercontent.com/ros-navigation/navigation2/jazzy/nav2_dwb_controller/dwb_core/src/dwb_local_planner.cpp)
and [latches rotation only inside its configured window](https://raw.githubusercontent.com/ros-navigation/navigation2/jazzy/nav2_dwb_controller/dwb_critics/src/rotate_to_goal.cpp).
Fetch008 completed navigation, acquisition, lift, descent and return without
mission recovery, but its detach-first release tipped the target on the repaired
floor: separation occurred, placement verification correctly failed.

A 20-cm window leaves one 5-cm map-cell margin inside the unchanged 25-cm
arrival tolerance. Fetch007 used it to complete bypass and return (one return
retry after an action-acknowledgement timeout), but physical placement failed. Safety polygons, physical
arrival consistency, wheel torque and gain ceilings are unchanged.

`coco22/release_probes/summary.json` and compressed native traces retain nine
isolated physical experiments. These are **not fetch episodes**: they create a
new diagnostic cylinder, command no wheel, never teleport an existing body,
and run no mission node. Both release orders and joint-disable vs removal
failed on the old floor; a free cylinder also failed, ruling out the weld as
the sole cause. Flat-mesh release probes with matched floor offsets/material
settled upright at 79.007 / 79.019 mm. At identical 94-mm creation height,
0.13-rad tilt tipped over whereas zero tilt settled at 79.003 mm. Diagnostic
cylinder friction differs from the canonical target; full mission evidence is
still required. The new shared `place_clearance_pose` preserves acquisition
palm pitch while adding 15 mm height and respecting joint limits.

Three further arm-actuated probes (`release_probes/grasp-*`) use the
perception-derived acquisition pose, canonical target inertia/friction and
physical joint actuation. Detach-first tips the target; opening before detach
settles upright at 79.004 mm, also at the attachment offset measured in fetch008
(79.002 mm). They isolate finger contact restoration as the remaining cause.
These create a diagnostic body and are never counted as fetches. The shared
place worker now opens while retaining the weld; opening failure leaves it held.

Reproduce a narrow fixture without changing a mission episode:

```bash
xacro gazebo_models/urdf/coco_robo2.xacro > /tmp/coco22-probe-robot.urdf
bash docs/data/isaac_fetch/coco22/release_probes/release_probe.sh \
  free /tmp/coco22-probe-new --robot-urdf /tmp/coco22-probe-robot.urdf \
  --floor-mesh --height .094 --tilt 0
```

A run under `/tmp/coco22-fetch-009` was interrupted by an environment switch
after return began. Its temporary directory and process disappeared; it is
excluded from completion counts. `coco22/environment_interruption.json` records
that evidence limit. The replacement writes native output under
`/home/gautham/coco22_runtime/fetch_009_restarted`.

The observer's `result.json passed` records mission COMPLETE plus sampled
idle-wheel safety only. Full physical success requires the simulator trace
as well: attachment, retained relative pose, detach, final floor pose and
placement area. `coco22/measure_fetch.py` evaluates saved telemetry offline;
it never commands or supplies coordinates to robot nodes. Each measurement
record has sample size one; interrupted and failed attempts are not successes.

The fetch runner now generates the measured Isaac profile from canonical Nav2
parameters: ideal-odometry AMCL alpha1–5=0.001 and DWB rotation window=0.20 m.
The goal checker remains 0.25 m. `tests/profile_equivalence.log` verifies semantic
identity to COMPLETE fetch009's explicit input. Gazebo uses the canonical
profile; `--params-file` remains an explicit override. Every generated profile
is saved in the run directory.

### Matched fetch measurements

`coco22/matched_episode.json` checks identical seed, level, requested colour,
robot start, ramp, targets, obstacles and world variant. Backend-specific
episode IDs differ. `coco22/comparison.json` contains the full measurements;
`tests/comparison_checks.log` verifies physical evidence alongside COMPLETE.
**Sample size: one recorded complete episode per simulator.** Development
failures are retained and are not used to estimate a success rate.

| Quantity | Isaac fetch009 | Gazebo fetch004 |
| --- | --- | --- |
| First detection after search entry, base xyz (m) | (1.2875, -0.1110, -0.2553) | (1.2853, +0.1020, -0.2480) |
| Grasp-entry measured base x/y (m) | (0.154559, -0.003878) | (0.154550, -0.000392) |
| First verified lift (mm) | 32.8 | 34.4 |
| Maximum displacement from carry start (m), not path length | 6.063 | 6.345 |
| Palm-relative maximum axis span (mm), samples | 0.318, 95 | 0.000325, 45 |
| Ramp-goal / bypass / home arrival error (m) | 0.192 / 0.352 / 0.241 | 0.110 / 0.226 / 0.042 |
| Final target height (mm) | 79.014 | 79.000 |
| Placement distance from home (m) | 0.274 | 0.123 |
| Runtime, sim / wall seconds | 255.767 / 729.476 | 166.386 / 174.437 |
| Mission RECOVERY entries / sampled idle-wheel breaches | 0 / 0 | 0 / 0 |
| Physical attach, retain, detach, upright placement / mission | verified / COMPLETE | verified / COMPLETE |

The first detection occurs on the pitched crest, before final level approach;
its z is the observed object centre in that base frame, not the 0.128-m
grasp-band handoff. Gazebo palm poses are model-relative and composed with
the measured model pose. Protobuf JSON seconds may be strings; omitted scalar
quaternion fields are zero. The first evaluator incorrectly defaulted missing
w to one, producing apparent 28.5-mm jumps during turns. Corrected evaluation
of unchanged raw telemetry removes them; rejected results remain explicitly
labelled in `gazebo_004/rejected_measurement.json`.

Gazebo attempts001 and003 failed before mission start due to DDS participant
index exhaustion; the publisher guard correctly refused an absent arbiter.
Attempt002 had no simulator/mission startup output and timed out; its transient
cause is **NOT VERIFIED**. The initial 28-process probe did not enforce peak
concurrency. A held-process probe then measured 32/40 ready with the existing
configuration versus 40/40 with explicit `MaxAutoParticipantIndex=119`.
The runner applies that bounded loopback discovery setting only to its owned
Gazebo children; other environments are untouched. Native controller processes
make the Gazebo stack larger than the Isaac stack. The setting's meaning is
documented by [Cyclone DDS](https://cyclonedds.io/docs/cyclonedds/latest/config/config_file_reference.html#cyclonedds-domain-discovery-maxautoparticipantindex).
`dds_probe/*_barrier.json` and logs retain the measured comparison. Final
Gazebo simulator, mission, observer and physical recorder all exited zero.
No Gazebo rebuild was performed.

Reproduce the narrow held-process diagnostic after sourcing `setup_env.sh`:

```bash
python3 docs/data/isaac_fetch/coco22/dds_probe/barrier_probe.py /tmp/coco-dds-new --domain 89
```

**Remaining limitations:** variable Isaac navigation time and localization
error, ideal pose odometry, approximate base inertia/contact dynamics, 2-Nm
wheel ceiling, and an explicitly filtered fixed-joint magnet approximation.
Displaced-target full-fetch trials and broader repeatability remain **NOT
VERIFIED**. These two runs do not establish physics or performance parity.

Implementation checkpoint: `70d3f38c0e99de8f35c8a419f16e4ae00b84f672`.
The final evidence commit also contains the measured DDS launch correction.
Each runtime preserves its actual HEAD, dirty patch and source digests.
Resolve the exact evidence commit with
`git log -1 --format=%H -- docs/data/isaac_fetch/coco22`.

## Historical COCO 2.1 evidence


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
