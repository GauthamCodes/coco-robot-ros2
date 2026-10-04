# COCO 2.3 — five matched positions-level fetches

**Verdict B: partial repeatability demonstrated, with specific remaining failure modes.**
Isaac physically completed 3/5 (60%); Gazebo 4/5 (80%). Seeds5,8,9 completed
in both; Gazebo also completed seed 7. Original observer/runner protocol passed
3/5 Isaac and 2/5 Gazebo. Two Gazebo COMPLETE runs retain one idle-mode timing
flag each. These are ten attempts, including all failures, not a curated success set.
Five different layouts with one trial each do not establish statistical reliability,
within-seed repeatability, production readiness, or physics/performance parity.

Starting branch `coco-2.1-isaac-integration`, clean SHA
`2e15706875c4850fe3a00200a9c5fd878e4b312d`. Runtime on 2026-10-05 Asia/Kolkata
(2026-10-04 UTC). All ten runs tested this SHA with unchanged runtime source digests.
Only evidence orchestration/evaluation and documentation were added; no implementation,
mission, generator, safety, or parameter edits, and no episode reruns.
The final evidence commit can be resolved with
`git log -1 --format=%H -- docs/data/isaac_fetch/coco23`.

## Methodology

The existing `coco_sim/coco_sim/episode.py` definition is authoritative:
`generate_episode(seed=n, level='positions', backend=..., requested_colour='red')`.
One `random.Random(seed)` shuffles the four colours, then samples x followed by y
for each region. Target x ranges from the nominal row to 85% of the remaining
validated far bound; target y is within its lane ±0.030 m. Rejection sampling
preserves target separation and approach corridors. All four targets move.
This is **not** the preceding milestone's colours-level seed 5 episode.

| Seed | Red region | Manifest world x/y/z (m) |
| --- | --- | --- |
| 5 | lane_1 | 4.347402394 / -0.723452983 / 0.728839392 |
| 6 | lane_4 | 4.058186785 / 0.749330476 / 0.728839392 |
| 7 | lane_3 | 4.071691598 / 0.250446144 / 0.728839392 |
| 8 | lane_1 | 4.097247756 / -0.737710985 / 0.728839392 |
| 9 | lane_1 | 4.149908274 / -0.768831303 / 0.728839392 |

Both backend manifests match in every field except backend and derived episode ID:
start pose, ramp, targets, world variant, requested colour and obstacles match.
The existing shared `scripts/isaac_fetch.py` launches fresh processes sequentially,
Isaac 5–9 then Gazebo 5–9, with private ROS domain 82 and 1200 wall seconds per mission.
No override profile was supplied. Isaac uses the already-shipped ideal-odometry
AMCL alpha1–5=0.001 / DWB rotation window 0.20 m profile; Gazebo uses canonical
Nav2 parameters and the existing scoped DDS participant-index setting.
Existing navigation gates, search timing, approach and manipulation remain unchanged.

Mission inputs are task-only. Manifests/physical coordinates are world/evaluator data;
the robot searches through RGB-D perception. Every graph records `cmd_vel_arbiter`
as the sole final wheel publisher. No teleportation, new command source, safety
bypass, or simulator-specific mission shortcut was introduced.

Physical completion requires mission COMPLETE and offline evidence of attach,
logged lift, retained palm-relative samples, detach, upright floor height and
placement near home. The extra offline corroboration never commands the robot
or substitutes for its mission gates. Original observer protocol additionally
requires zero sampled idle-mode flags and zero wrapper exit codes; native logs
are inspected because wrapper exit codes can hide a crashed child.
The precise gates and metric definitions are in [comparison.json](comparison.json).

## All episodes

| Backend / seed | Region | Mission outcome | Original protocol | Recoveries | Runtime sim / wall (s) | First lift (mm) | Placement error (m) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [isaac 5](isaac_seed5/measurements.json) | lane_1 | COMPLETE | PASS | 0 | 278.80 / 404.25 | 33.5 | 0.266 |
| [isaac 6](isaac_seed6/measurements.json) | lane_4 | ABORT / DESCENT_TIMEOUT | FAIL | 2 | 108.20 / 141.91 | — | — |
| [isaac 7](isaac_seed7/measurements.json) | lane_3 | ABORT / DESCENT_TIMEOUT | FAIL | 2 | 92.43 / 150.24 | — | — |
| [isaac 8](isaac_seed8/measurements.json) | lane_1 | COMPLETE | PASS | 0 | 175.43 / 330.83 | 32.1 | 0.244 |
| [isaac 9](isaac_seed9/measurements.json) | lane_1 | COMPLETE | PASS | 0 | 191.23 / 342.66 | 33.4 | 0.355 |
| [gazebo 5](gazebo_seed5/measurements.json) | lane_1 | COMPLETE | FAIL | 0 | 160.35 / 185.01 | 34.6 | 0.088 |
| [gazebo 6](gazebo_seed6/measurements.json) | lane_4 | ABORT / CLOCK_STALLED (ODE abort) | FAIL | 2 | 168.72 / 214.44 | — | — |
| [gazebo 7](gazebo_seed7/measurements.json) | lane_3 | COMPLETE | PASS | 2 | 437.62 / 494.18 | 34.5 | 0.124 |
| [gazebo 8](gazebo_seed8/measurements.json) | lane_1 | COMPLETE | PASS | 0 | 160.21 / 184.23 | 35.2 | 0.076 |
| [gazebo 9](gazebo_seed9/measurements.json) | lane_1 | COMPLETE | FAIL | 0 | 163.71 / 184.99 | 34.8 | 0.083 |

Placement error is target XY distance from home after completed release;
failed targets remaining on the platform are not included in placement statistics.
Recovery entries include ordinary unsuccessful-region search transitions.
Each per-run measurements file retains all state transitions, detections,
approach handoff, approximate grasp-entry relative pose, attach/detach events,
carry/retention, final pose/orientation and post-release samples.
[comparison.json](comparison.json) also contains explicit stage results and failure states.

## Aggregate measurements

| Quantity | Isaac | Gazebo |
| --- | --- | --- |
| Physical completions / attempts | 3/5 (60%) | 4/5 (80%) |
| Original observer/runner protocol pass | 3/5 (60%) | 2/5 (40%) |
| Terminal failures by state | DESCEND: 2 | DESCEND: 1 |
| Mission recovery entries, all trials | 4 | 4 |
| Sampled idle-mode wheel flags | 0 | 2 |
| Runtime all attempts, mean sim / wall (s) | 169.22 / 273.98 | 218.12 / 252.57 |
| Runtime all attempts, sim range (s) | 92.43–278.80 | 160.21–437.62 |
| Runtime all attempts, wall range (s) | 141.91–404.25 | 184.23–494.18 |
| Completed placement error mean / range (m) | 0.289 / 0.244–0.355, n=3 | 0.093 / 0.076–0.124, n=4 |
| Grasp-relative signed x/y error means (mm) | -0.530 / -2.658, n=3 | -0.069 / -0.488, n=4 |
| First verified lift mean / range (mm) | 33.0 / 32.1–33.5, n=3 | 34.775 / 34.5–35.2, n=4 |
| Carry displacement mean (m), not path length | 6.357, n=3 | 6.431, n=4 |
| Maximum palm-relative axis span range (mm) | 0.181–0.393, n=3 | approximately 0–0.000362, n=4 |

Grasp error is measured object-centre x minus existing red `approach_stop_x=0.15375 m`,
and measured y minus zero. It is **not** centre z minus the 0.128-m grasp-band handoff.
Snapshots are approximately 2 s apart and ROS reception times differ; grasp-entry
errors are approximate. Fixed-joint retention is an approximation in both engines,
so microscopic spans do not establish realistic friction grasping. Maximum rise
before descent is separate from the first verified lift; the reused evaluator has
no rise result for Gazebo 7 because its first DESCEND preceded acquisition.
Full metric sample counts, ranges and medians are in the JSON.

## Failures and root-cause limits

- **Isaac 6/7:** `DESCENT_TIMEOUT` during continuation from the first search lane,
  before approach/grasp. Seed6 first reported `TARGET_NOT_FOUND`; seed 7 reported
  `SEARCH_REJECTED_GEOMETRY`. The worker then timed out at world x 4.76 / 4.57 m,
  pitch +0.314 /+0.134 rad. Saved traces show sustained forward commands,
  little progress, uneven wheel motion and drift on the far slope. Gazebo passed
  both matching first descents. This is a repeated Isaac physical-descent failure
  pattern in this sample. Exact contact/steering cause and determinism remain
  **unverified**. Initial arm pose differs from carry descents; causality is not isolated.
- **Gazebo 6:** first descent and lane 2 search occurred, then `CLOCK_STALLED` in
  the second DESCEND. Native Gazebo log records ODE collision-space assertion
  `aabbBound >= dMinIntExact && aabbBound < dMaxIntExact`, native exit 134, and
  required-system shutdown. This is a simulator physics/infrastructure failure,
  not evidence of perception/manipulation failure. Exact trigger and whether it
  recurs deterministically remain unverified. Launch-wrapper exit 0 hid native
  failure; native logs and mission clock watchdog expose it. MoveIt also crashed
  during shutdown; no active manipulation had been attempted.
- **Gazebo 5 observer:** one nonzero command sampled against the observer's last
  `idle` mode during LOCALIZE→NAVIGATE_TO_RAMP. The observer had received arbiter
  `mode=nav active=nav` before the command and received mission mode `nav` about 6 ms
  afterward. Evidence supports cross-topic observation ordering as the cause of
  this flag. Original observer failure is preserved, not overwritten.
- **Gazebo 9 observer:** one residual yaw 0.005846 rad/s sampled at the
  NAVIGATE_TO_RAMP→ALIGN_FOR_CLIMB nav→idle transition; next final command was
  zero 70 simulated ms later. Cross-topic delivery/timer ordering is plausible,
  but there is no captured arbiter idle acknowledgement at that instant to
  resolve ordering. It is a retained timing ambiguity, not cleared safety proof.
  [Seed5 context](gazebo_seed5_idle_sample.json) and
  [seed 9 context](gazebo_seed9_idle_sample.json) preserve the samples.

There was no clear small implementation defect isolated well enough to fix
without confounding the measurement. No tuning or corrective code was applied.
A shell `nounset` startup issue was corrected before any episode launched;
[orchestration_startup.txt](orchestration_startup.txt) records it.

## Cross-simulator interpretation

Both completed seeds 5,8,9; Gazebo additionally completed the lane3 seed 7 after
searching lanes 1/2. Neither completed seed 6. Thus displaced-target acquisition,
carry and upright release repeat across three matched lane 1 layouts, while
farther-region full-fetch repeatability is not established in both engines.

For the three **both-completed** pairs, Isaac minus Gazebo averages:
+53.734 simulation seconds, +174.506 wall seconds, +0.206 m placement error,
and -1.867 mm first lift. These are paired descriptive measurements, not a
performance or physics equivalence claim. All-pair runtime differences include
failed episodes of different lengths and should not be interpreted as speed.
Ideal Isaac odometry versus Gazebo wheel odometry, contact approximations,
backend profiles, asynchronous telemetry and changing simulation rates limit comparisons.

## Persistence and verification

[comparison.json](comparison.json) is the concise machine-readable comparison.
Raw compressed simulator/mission/observer logs, ROS observations, Gazebo physical
traces, manifests, inputs, graphs, exit codes, source hashes/patches and Isaac
settled-target checks are in the ten run directories. `runtime_reference.json`
points to the original `/home/gautham/coco23_runtime/` images/generated assets.
Those large local assets are not required to reproduce offline measurements.
Previous `coco22` seed 5 and historical evidence are unchanged.

[evidence_checks.json](evidence_checks.json) verifies all five matched manifests,
all ten unchanged source-digest sets, task-only robot inputs, sole arbiter,
initial red placement within 5 mm, and physical completion corroboration.
[tests/summary.json](tests/summary.json): all nine relevant package suites passed,
**1,952 tests, zero failures**, run once after the ten episodes. Package logs
retain warnings; no suite was run between simulations.

Re-evaluate saved telemetry after sourcing the existing overlay:

```bash
python3 docs/data/isaac_fetch/coco23/analyze.py
python3 docs/data/isaac_fetch/coco23/check_evidence.py
```

`run_matrix.sh` records the exact experiment commands and refuses existing
output directories; `curate.py` copies/compresses evidence without deleting originals.
Its absolute paths describe this host. A new experiment requires a new runtime root.

**Recommended next milestone:** diagnose and validate the search-continuation
far-slope descent path with matched physical telemetry, prioritizing Isaac's
repeat failures and Gazebo's collision instability, then repeat the failed
farther-region episodes without seed-specific tuning.
