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
python3 docs/data/isaac_fetch/coco24/evaluate.py --runtime /home/gautham/coco24_new_runtime
python3 docs/data/isaac_fetch/coco24/trace_segments.py \
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
Runtime validation is pending. The hypothesis predicts continued search without
displacing nonrequested cylinders, then physical fetch in failed cases.
