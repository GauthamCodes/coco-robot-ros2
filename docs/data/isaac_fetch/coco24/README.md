# COCO 2.4 — search-continuation route correction

Starting clean SHA `98744ce2153807c684acc8530c17541cd83561a9`, branch
`coco-2.1-isaac-integration`. Historical COCO 2.3 evidence is unchanged.

## Pre-fix mechanism and hypothesis

All ten saved runs were inspected before changing control. Failed searches
transition directly SEARCH_TARGET → RECOVERY → DESCEND, crossing the entire
occupied candidate lane. Not acquiring the requested colour does not make that
lane empty. The robot hits and pushes the unrequested cylinder to the far crest.

Isaac6/7 first leave lane_1 toward lane_2. Initial world poses are respectively
(2.600,-0.720,0.520) and (2.598,-0.724,0.519) m, yaw +0.059/+0.064 rad, pitch
-0.314/-0.313 rad. Positive descent commands bring them over the near crest and
across the deck. Yellow starts at x4.064/4.290 and moves to x4.65/4.67 by the
far crest; it tips and remains beside the base. Progress stalls around x4.50.
Final x4.755/4.567, pitch +0.314/+0.134, yaw +0.245/-0.174. Commands remain
0.18 m/s plus heading correction, ages around 0.03–0.07 simulated seconds;
one wheel pair spins ~6 rad/s while the other hardly moves. Clock and command
delivery continue. Failure is during physical traversal, before acquisition.
Neither Nav2 nor AMCL steers this segment: ramp_driver uses ground-truth pose
and IMU and publishes through the existing arbiter. Arm home geometry is clear
of terrain (URDF FK minimum arm clearance ~74 mm); blaming direct arm/ramp
collision or wheel gain is unsupported.

Gazebo6 first crosses lane_1 and ejects yellow from the platform. After returning,
it climbs/searches lane_2, then repeats the forward traversal. Blue moves from
(4.267,-0.222,0.729) to (5.165,0.451,0.448), then to
(5.712,2.544,2.766) m immediately before native ODE AABB assertion/exit134.
Base freezes at (4.497,-0.300,0.637), pitch +0.155; last command remains 0.18.
Simulation time stops at ~177.17 s; the mission clock watchdog aborts. This is a
native solver failure following object collision, not a missed command.
The exact invalid solver contact/NaN chain is not recorded.

Gazebo7 COMPLETE is a crucial contrary control: it also pushes yellow off the
platform, waits near x4.497 for tens of seconds, eventually progresses, then
knocks green off the platform on lane_2. Completion masked destructive search
transit. Isaac/Gazebo5/8/9 instead acquire red in lane_1 and physically remove
it before descent. Their successful descents cross an emptied centreline.

No historical contact pair/force telemetry exists: cylinder displacement,
tipping, co-location and wheel/body disagreement support obstruction/contact;
exact wheel/cylinder pairs and the ODE numerical trigger remain inferred.
[Pre-fix sampled segment reconstruction](pre_fix_traces.json.gz) contains all ten
runs' transitions, commands, physical pose/velocity, rpy, lane errors, arm/wheel
positions, AMCL, arbiter and object pose samples, with original trace references.
The original raw logs remain in [coco23](../coco23/README.md).

## Correction

Unsuccessful autonomous search now enters RETREAT: reverse heading hold down the
already climbed corridor, without entering the occupied row or pivoting on the
grade. Same 0.18 m/s speed, yaw gains, limits, arbiter path and worker watchdog.
A fresh near-exit pose must corroborate worker success before Nav2 is released.
Nav2 then drives directly to the next region's nearby pre-ramp goal using
the existing perception gates.
Exhausting search returns empty and reports failure. Acquired-target forward
DESCEND, physical grasp/carry/release and the south bypass remain in place.

The existing AMCL handoff uses the near exit after retreat and far exit after
carry descent; its one-time latch resets per traversal but never on Nav2 retry.
No target manifest/pose reaches this route decision. The near exit is derived
from static ramp-foot geometry; no seed-specific parameter or simulator bypass.

Initial retreat checkpoint: `e4ed229`. Targeted development tests passed 227;
the mission package plus arbiter suite passed 393 (these counts overlap).
No full repository regression sweep was run during development.

Reproduce the six matched episodes with a new runtime root:

```bash
bash docs/data/isaac_fetch/coco24/run_matrix.sh /home/gautham/coco24_new_runtime
# Or one case, after exporting COCO_WS/COCO_MOVEIT_PREFIX and sourcing setup_env.sh:
python3 scripts/isaac_fetch.py /home/gautham/coco24_new_case --backend isaac \
  --level positions --seed 6 --colour red --domain 82 --timeout 1200
PYTHONPATH=coco_config python3 docs/data/isaac_fetch/coco24/evaluate.py --runtime /home/gautham/coco24_new_runtime
PYTHONPATH=coco_config python3 docs/data/isaac_fetch/coco24/trace_segments.py \
  docs/data/isaac_fetch/coco24 /home/gautham/coco24_post_fix_traces.json
```

The matrix uses seeds6/7 plus seed8 as the previously successful control in each
backend. Every run uses the original generator, task-only inputs, default
backend Nav2 profile and 1200-wall-second limit. The existing installed mission
and driver resolve to source symlinks in this repository; no foreign workspace
or package overlay is rebuilt or edited. Evaluator asserts byte-identical
manifests and Isaac Nav2 profiles against COCO 2.3, sole arbiter, task-only
inputs and runtime source digests.

The first post-fix attempt at `e4ed229` demonstrated three successful retreats
with undisturbed nonrequested cylinders. Its redundant RETURN_HOME leg after
each retreat caused long navigation detours (second leg ~288 wall seconds).
That leg existed to clear the old far-side route. The near exit already lies
beside the next pre-ramp goal, so the final correction goes directly there;
only exhausted search returns empty to home. The AMCL seed retains the exited
lane before selecting the next lane, preventing a wrong-lane localization seed.
The initial attempt remains separately preserved and is not counted as final
validation. A read-only Nav2 snapshot retains the observed localization/plan.

Final targeted tests: 431 passed (mission, arbiter, ramp driver/regions).
Six final matched runs at `668190252d9e3e893a50ba785ed8fb5c169a07e6` are preserved
below. The initial diagnostic is excluded. Offline provenance checks pass:
all six original manifests, unchanged simulator/navigation/perception/grasp
sources, one runtime implementation, sole authoritative arbiter, unchanged
COCO22/23 history. Evaluation uses the original physical and protocol gates.

## Runtime result and limits

| Backend | Seed | Before | After | Retreats completed | Final limitation |
| --- | --- | --- | --- | --- | --- |
| Isaac | 6 | DESCENT_TIMEOUT | ABORT | 3 | Nav2 action acknowledgement timeouts; retries exhausted before lane_4 |
| Isaac | 7 | DESCENT_TIMEOUT | ABORT | 1 | Nav2 action acknowledgement timeouts; retries exhausted before lane_2 |
| Isaac | 8 control | COMPLETE | physical COMPLETE, protocol PASS | 0 | None observed |
| Gazebo | 6 | CLOCK_STALLED / ODE assertion | ABORT | 1 | Planner start occupied after near-side handoff |
| Gazebo | 7 | physical COMPLETE, destructive transit | ABORT | 4 | All regions searched; red pose IMPLAUSIBLE_SIZE, fail-closed SEARCH_FAILED |
| Gazebo | 8 control | COMPLETE | physical COMPLETE, protocol FAIL | 0 | One original observer idle-mode timing flag |

All nine RETREAT workers report goal on flat ground, x approximately 0.65 m,
with fresh physical mission corroboration. No DESCENT_TIMEOUT or native ODE
abort occurs in these reruns. Nonrequested cylinder displacement is below
0.00008 m in Isaac and 0.000003 m in Gazebo, including initial settling;
all three nonrequested targets are measured. This materially improves rejected
search transit safety, but **does not demonstrate better full-fetch reliability**.
The selected sample physically completes 1/3 in each backend (original protocol
1/3 Isaac, 0/3 Gazebo). This differs from the historical five-case sample and
must not be presented as a new five-seed completion rate.

The seed8 controls physically attach, lift, retain, return, release and place
red upright. Gazebo's flag is reported separately from physical completion;
it is not silently waived. Gazebo7's prior COMPLETE is also retained: the new
route changes that case's outcome, so successful farther-region fetch has not
been preserved or proven yet. Prior cylinder ejection could alter subsequent
perception/scene conditions; that is an inference, not justification to weaken
perception gates or reproduce destructive movement.

Isaac failures are Nav2 BT action acknowledgement errors (compute_path_to_pose
and follow_path), not retreat stalls. Isaac7 also has an acknowledgement error
before its first climb. Recorded unrelated Gazebo/RViz/SLAM workloads and nearly
full swap reduced simulator throughput. They were left untouched; the user
instructed continuation. Load is a confounder, not proof these aborts are solely
infrastructure. No Nav2 timing parameters or retry budgets were changed.

Gazebo6 Nav2 plans from map (2.77,-0.95) after a physical near exit around
world (0.65,-0.77), expected map (2.65,-0.75). Its approximately 0.23 m error passes
the existing 0.50 m consistency gate, but the planner start lies in an occupied
cell. Retries immediately repeat the same failure. The handoff gate's sufficiency
near the inflated ramp footprint remains unresolved; neither observed ODE nor
this localization failure can be classified as fixed through complete fetch.

Gazebo7 climbs/searches all four regions, retreats each time, returns empty and
reports SEARCH_FAILED. Perception status is NOT_DETECTED in lane_1 and
IMPLAUSIBLE_SIZE in all 75 sampled statuses per later lane, including red's lane.
The size filter correctly remains fail-closed. Exact projected size/depth/TF
cause is not isolated; status samples and physical poses are preserved for the
next investigation. No seed-specific or perception-threshold tuning was made.

**Verdict B with an explicit boundary:** the shared occupied-route defect is
corrected and runtime transit behavior improves; simulator/backend navigation
and perception failures remain. Original farther-region **complete-fetch
repeatability is not closed**. This is not verdict D: the evidence does not
support attributing all remaining behavior failures to infrastructure.

Next milestone: complete the same seed6/7 far-region fetches on an idle host
with synchronized Nav2 action request/acknowledgement, map→base/costmap and
perception candidate size/depth traces, resolving the newly exposed handoff
and perception gates from those measurements.

## Durable evidence

- [Comparison and physical measurements](comparison.json): pre-fix references,
  all six final outcomes, transitions, original protocol results and provenance.
- [Post-fix reconstruction](post_fix_traces.json.gz): command/odometry, world
  pose/velocity, yaw/roll/pitch, lane error, localization and object samples.
  Lane error is measured against the segment entry lane; published region may
  advance at the final dispatch boundary.
- [Failure excerpts and search validity counts](post_fix_diagnosis.json),
  [host contention](environment_contention.json), [matrix execution](matrix.log),
  [offline checks](evidence_checks.json), [431-test log](final_targeted_tests.log).
- Each backend_seed folder retains compressed raw mission/simulator/observer/
  physical traces, original result/exits, command graph, manifest, task inputs,
  source metadata/patch and runtime_reference.json for expanded URDF/assets/images.
- [Initial deliberately stopped attempt](retreat_v1/isaac_seed6/diagnostic_stop.json)
  retains the obsolete RETURN_HOME refinement and raw logs separately.

Run offline assertions after evaluation:

```bash
PYTHONPATH=coco_config python3 docs/data/isaac_fetch/coco24/check_evidence.py
```

No exact contact-force/pair telemetry exists in the historical runs. World
velocity is reconstructed by finite differences; rpy uses physical body
quaternion because historical IMU observations store sample presence only.
The ODE solver's invalid-contact chain and remaining failures are not fully
explained. No identical failed experiment was repeated without a changed route
hypothesis; no full suite was repeatedly run and no unrelated worktree changed.

Additional read-only instrumentation for the next run (not used as runtime proof
for this completed batch):

```bash
# In the same sourced ROS overlay and ROS_DOMAIN_ID as the episode:
python3 docs/data/isaac_fetch/coco24/candidate_trace.py /tmp/candidate_sizes.jsonl --seconds 1200
python3 docs/data/isaac_fetch/coco24/nav_snapshot.py /tmp/nav_handoff.json
```

The candidate recorder writes RGB/depth timestamps, selected colour, region,
mission, raw pose status, component dimensions, depth-derived axis range and
expected width/ratio. It publishes nothing. It uses the current default depth
limits; record any future profile changes separately. The script passes import/
startup verification; it has not yet collected a failed far-region candidate.
Nav2 BT acknowledgement latency still needs dedicated action instrumentation.
