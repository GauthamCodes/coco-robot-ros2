# COCO 2.5 — diagnostic preparation; idle-host reproduction blocked

Starting SHA `25e8fdc8781bb547a882d33ed14fc44dd60afc76`, branch
`coco-2.1-isaac-integration`, verified clean before any edits. Source of truth:
repository and durable COCO23/24 evidence. Those directories are unchanged.

**No qualified diagnostic episodes have been run. No root-cause fix or
repeatability improvement is claimed.** The host has an unrelated Gazebo
server, PID270753, active at the initial inventory and final preflight.
Its initial measured CPU use was 89.9%, GPU allocation 890MiB; the host also
had active browser workloads. See [host_condition.json](host_condition.json).
The user was asked to make the host idle. Unrelated processes/projects were
left untouched. Launching another benchmark would violate the required
idle-host experiment and the repository's one-Gazebo-at-a-time constraint.

## Existing infrastructure and missing evidence

`scripts/isaac_fetch.py` remains the episode runner, using positions seeds6/7,
red task-only inputs, domain82, default backend profiles and 1200s timeout.
`scripts/isaac_fetch_observer.py` captures mission/recovery/retry status, command
chain, AMCL, target status and poses; Isaac native telemetry and
`scripts/gazebo_pose_observer.py` provide physical world/body/object state.
The observer's odometry lacks velocity; its camera samples lack candidate
geometry; its readiness probes do not trace Nav2 internal action lifecycle.
COCO24's `nav_snapshot.py` provides a five-second TF/costmap window, not
continuous causal ordering. `candidate_trace.py` recomputes candidate widths
but was not used to capture the historical failures.

[historical_comparison.json](historical_comparison.json) re-extracts boundary
logs/results for COCO24 failed6/7 and successful8, plus COCO23 successful9,
in both backends. These are historical observations, not new runtime results:

- Isaac6: three retreat completions, then `compute_path_to_pose`
  acknowledgement failure/retry exhaustion. Earlier next-lane requests also
  fail once before recovering. The exact server scheduling/goal lifecycle
  and relationship to host contention are unresolved.
- Isaac7: `follow_path` acknowledgement failure already occurs on the first
  navigation leg, before any retreat. It recurs after the first retreat.
  Therefore a defect exclusively triggered by retreat cannot explain every
  historical acknowledgement error. This does not establish host timing as
  the cause.
- Gazebo6: retreat completes at the near exit, then planning immediately
  fails from map `(2.77,-0.95)` to `(2.50,-0.25)` with `Start occupied`.
  No reseed/releasing-handoff log occurs in that run. Code inspection shows
  the existing handoff can skip reseeding when AMCL lies within the 0.50m
  consistency band; that path does not wait on the TF consistency test used
  after a reseed. This is a causal hypothesis to check, not proof of the
  occupied cell's source or a justification to change the band.
- Gazebo7: four retreats finish, but later search regions have
  `IMPLAUSIBLE_SIZE` and acquisition never occurs. Historical rejection
  status does not retain rejected blob width/depth; physical plausibility
  remains unresolved. No acceptance thresholds were changed.
- Successful8/9 acquire in lane1 and do not exercise rejected-search
  retreat/next-lane handoff. They remain controls for ordinary navigation,
  perception and complete physical fetching, not proof of that handoff.

The first *causal* divergence among localization/costmap, action lifecycle,
motion, perception, physics, host timing and shared state is **not yet
measured with synchronized diagnostic traces**.

## Instrumentation changes

- The executive logs request token/map goal/sim time; acknowledgement,
  goal UUID and elapsed wall latency; result/status and stale callbacks.
  Goal routing, callback decisions, handoff, retry budgets and tuning are
  unchanged. These are diagnostic log additions only.
- The existing runner accepts `--diagnostic-script` and owns/stops that
  child in the same ROS domain/DDS environment as the episode. Its normal
  invocation retains its previous behavior.
- [diagnostic_trace.py](diagnostic_trace.py) records receive epoch/elapsed
  wall time, ROS time, and source message time separately. It subscribes
  to mission/localization/initialpose/rosout, all three Nav2 action status
  streams, BT transitions, plans, AMCL covariance, odometry velocities,
  command chain, actual perception detections/status and camera inputs.
  It samples map→base/odom and costmap robot patches at 5 wall Hz and
  queries planner/controller/navigator lifecycle every5 wall seconds.
  Changed full grids are gzip-compressed separately; patches retain the
  latest grid stamp and raw cost encoding, rather than inventing occupancy
  thresholds. Plans retain their point geometry; planner errors retain
  logged start/goal coordinates.
- Every received search RGB image gets per-component width/height/area,
  centroid, depth quantiles/valid fraction/spread/surface/axis range,
  expected width, inferred diameter, optical position and image-time TF.
  It recomputes the shipped default geometry policy; actual perception
  verdicts are separate records. Raw frames/depth/masks are bounded to
  one per region/geometry outcome, maximum24. No manifest is read by this
  recorder; it sends no mission/action/wheel commands.

Capture limitations: receive order is not producer execution order. 5Hz
motion/TF/costmap samples bound rather than exactly timestamp sub-200ms
changes; source stamps and action/server logs must be used to reconstruct
causality. Nav2 internal action statuses/BT logs do not expose every DDS
service request. Missing topics are evidence gaps, not successful
acknowledgements. Candidate recomputation uses the unchanged default policy
and may pair differently if frames are dropped; image stamps and actual
status/detection streams must be compared. Actual recorder overhead under
simulation load has not yet been measured. Future profile changes require
updating/recording recorder policy rather than assuming it still matches.

## Verification and interrupted launch

- Executive node tests: **40 passed**, 5.68s (overlap with package suite).
- Mission package suite: **365 passed**, 7.50s.
- Simulator/runner package suite: **228 passed**, 4.53s.
- Synthetic ROS replay: passed; **219 records**, 1 candidate record,
  17 costmap samples. It checks raw lethal-cell254 capture, geometry gate,
  image-time TF, actual verdict subscription, BT messages and odometry.
  [validate_trace.py](validate_trace.py) produces this replay; compressed
  `synthetic_*` traces are explicitly synthetic and are not runtime proof.

An initial test command used the package cwd with repository-relative paths;
it failed setup/imports and was corrected. The first synthetic fixture used
a point on a floating-point grid boundary; its occupied-cell assertion failed.
A binary-exact resolution fixed the fixture, and the replay passed.

The initial idle preflight checked executable `comm`. Gazebo's executable is
`ruby`, while its process title is `gz sim server`; the preflight missed it
and briefly launched an Isaac startup. The owned batch/runner was interrupted,
all owned simulator/mission/observer/recorder processes were stopped, and the
guard was corrected to inspect process title as well. The observer result is
`NOT_STARTED`, state `IDLE`: no mission was started. This contaminated startup
is durably retained in [excluded_nonidle_startup](excluded_nonidle_startup/)
with its exclusion reason. It is not a diagnostic run, pre-fix outcome, or
repeatability attempt. The original expanded assets/images remain at the
runtime path in `exclusion.json`. The corrected preflight reports exit3 and
refuses to launch; see [idle_preflight.log](idle_preflight.log).

## Exact reproduction and remaining work

After the user frees the host and its condition is verified, use a new root:

```bash
cd /home/gautham/coco-isaac-21
bash docs/data/isaac_fetch/coco25/run_diagnostics.sh /home/gautham/coco25_idle_diagnostics_v2
```

This executes Isaac6, Isaac7, Gazebo6, Gazebo7 sequentially, without changing
definitions or profiles. It refuses existing outputs and an active simulator,
and stops the batch on broken diagnostic capture or failed retreat.
Verify other host contention manually before running; the simulator preflight
alone does not prove all host resources idle. A single case/control uses:

```bash
export COCO_WS=/home/gautham/coco_isaac21_ws
export COCO_MOVEIT_PREFIX=/home/gautham/coco_p03d_ws/moveit_prefix/root/opt/ros/jazzy
source setup_env.sh
python3 scripts/isaac_fetch.py /home/gautham/coco25_new_case --backend isaac \
  --level positions --seed 6 --colour red --domain 82 --timeout 1200 \
  --diagnostic-script docs/data/isaac_fetch/coco25/diagnostic_trace.py
# Replace backend/seed with the affected case or seed8/9 control; use NEW outputs.
```

Instrumentation replay (no simulator) uses a new temporary directory:

```bash
ROS_DOMAIN_ID=95 python3 docs/data/isaac_fetch/coco25/validate_trace.py /tmp/coco25_trace_new
```

Do not execute COCO24's evaluator unmodified on new results: its output root
is fixed to COCO24 and would overwrite historical evidence. Reuse its physical
evaluation functions with the output root redirected to COCO25 when curating
the completed batch. Preserve diagnostic gzip files and representative camera
artifacts in addition to the existing curator's retained signals.

Pending: all four idle-host pre-fix reproductions, synchronized first-divergence
analysis against8/9 controls, evidence-backed correction, affected-case rerun,
one successful Isaac and Gazebo control, and the full relevant final regression
after any correction. Post-fix results are not yet measured. Safe retreat is
preserved in source; no new runtime validation of it is claimed.

**Next concrete milestone:** obtain one qualified synchronized idle-host trace
for each of the four unchanged failing episodes and identify the earliest
divergence before selecting a corrective layer.
