# Isaac backend evidence — 2026-09-24 / 2026-09-25

All runtime measurements here were produced during this implementation.
PASS means the named checks were run, not that the whole mission works.
Operations and scope: [../../ISAAC_BACKEND.md](../../ISAAC_BACKEND.md).

## Final raw-interface acceptance

[smoke07_shutdown/result.json](smoke07_shutdown/result.json): **PASS**, all
19 ROS-visible assertions, normal Isaac close, and zero exits for observer,
ROS peer, Isaac, and RViz. Private DDS domain 78. Sensor rates below are
measured from received messages' simulation timestamps, not wall time.

* Forward displacement: 3.863428366138775 m
  (derived from recorded odometry), commanded 0.5 m/s for the recorded
  8.000000417 simulation seconds.
* Positive yaw change: 0.6836177892251978 rad
  (derived), commanded 0.5 rad/s for 3.0000001560000005 simulation seconds.
  Direction passes; angular tracking is substantially below command and is
  not claimed calibrated or equivalent to Gazebo.
* RGB received: 246; depth: 245; LiDAR: 179;
  odometry: 538; clock: 539.
* Measured rates (sim Hz): {'rgb': 13.7640442262341, 'depth': 13.707864453882124, 'scan': 9.999999478651713, 'odom': 29.99999843463695}.
  Nominal image rate is 15 Hz; no loss-free/full-nominal-rate claim is made.
* Initial central axial depth: 6.8269124031066895 m, against
  fixture-derived 6.825 m. Encoding 32FC1, metres, 320×240, optical frame.
* LiDAR bearing/range residual p95: 7.366605624878891e-05 m at start,
  3.606723269591327e-05 m after motion (derived comparisons against
  analytic ray/rectangle intersections using the recorded pose).
* Peak Isaac RSS: 4959672 kbytes (measured by /usr/bin/time); sampled total GPU
  memory maximum: 2292 MiB. GPU includes desktop/RViz and is sampled after
  readiness, not a cold-start peak. Earlier runs overlapped other applications;
  these are not exclusive-machine performance benchmarks.

Exact evidence: `launch.log`, `observer.log`, `ros_peer.log`, `rviz.log`,
`process_exit.json`, `resources.txt`, `gpu.json`, `capture_error.txt`, and `sim/` under
that run. `result.json` includes topic/type inventory, publisher endpoint QoS,
sensor samples and scan arrays, TF edges, motion phases and assertions.
`sim/episode.json`, `scene.json`, `robot.urdf` and normal-close marker record
what was instantiated. Episode manifests across completed fixed runs are
byte-identical; the fixture explicitly does not instantiate the fetch layout.

## Navigation and RViz

`nav03_landmark`: NavigateToPose SUCCEEDED (status 4, error 0), final map
error 0.08518153452292665 m; sole wheel publisher cmd_vel_arbiter. **PARTIAL**
overall: RViz exit -11 and composed Nav2 child exit -6 during teardown.
Its old `passed: true` field predates child/auxiliary exit auditing; it must
not be interpreted as clean whole-run shutdown.

`nav04_final`: second SUCCEEDED goal, final map error 0.044509391904768256 m,
1.5283983708097049 m odometry displacement, all five command-chain stages
observed. Isaac and RViz exited 0. **PARTIAL** overall: composed Nav2 child
exit -6 although ros2 launch returned 0. `result.json` contains an explicit
post-run audit correcting the initial parent-only verdict.

`nav06_uncomposed`: readiness FAIL after 90 wall seconds. The map server
attempted `map.yaml` and failed to load it, so no map TF was available.
Isaac, RViz, and every Nav2 child shut down normally. The subsequent
run pins the fixture filename in a run-local parameter copy.

`nav07_map`: the explicit map parameter fixed localization. All lifecycle
nodes activated and the full command chain moved the robot 0.5633 m. The
navigation action then ABORTED (status 6): `compute_path_to_pose` goal-request
acknowledgement timed out (`nav2.log`, immediately before Goal failed).
Isaac and every Nav2 process exited normally; RViz exited -6 with an Ogre
vertex-buffer out-of-memory exception (`rviz.log`). **FAIL** for this run;
**PARTIAL** for Nav2 integration across the evidence. The two composed-mode
successful goals remain valid behavioral evidence, not reliability evidence.
The exact root cause of the action timeout and RViz allocation failure is
unresolved. No claim of physical GPU exhaustion follows from that exception.
`environment.json` captures the actual whitelisted Isaac and Jazzy process
environments; `nav2_params.yaml` records the map-only override.

The test now uses Nav2's existing `use_composition:=False` launch option and
checks child-process failure lines as well as parent exits.
`--nav-composed` explicitly selects the earlier mode for reproduction. No navigation
algorithm, tolerance, footprint, mission logic, or shared YAML was changed.
The fixture's off-axis landmark and its map come from one definition.
Successful goals with it do not isolate why the original bare room failed.

Visual proof: `nav03_landmark/rviz.png` shows robot, scan, RGB, depth and
odometry; RobotModel/TF statuses are OK. The final raw run screenshot
capture failed with an unsupported XWD pixel layout (`capture_error.txt`);
its ROS-visible acceptance does not depend on a screenshot. Successful
XWD captures contain only the owned RViz window. The initial
`nav02/rviz.png` root crop is excluded from Git because it included pixels
beyond that window; it was not deleted.

## Gazebo and shared-stack regression

The unrelated simple_bot simulator found initially was left untouched.
Conflicting Gazebo runtime testing was deferred at the user's request. A
later process check found it had exited independently; the existing headless
Gazebo integration test was then run on domain 79 with a private GZ_PARTITION.

`gazebo_live.log`: **3 live assertions + 1 post-shutdown assertion PASS**:
four controllers active, load-bearing topics at expected simulation rates,
and base TF resolves. Gazebo's shutdown was -15, allowed by the existing
integration test. No full mission rerun or Gazebo navigation benchmark is
claimed. No Gazebo runtime/configuration file was edited.

Latest package test counts (measured separately, cwd inside each package):

| Package | Passed | Failed | Skipped | Evidence |
|---|---:|---:|---:|---|
| coco_config | 70 | 0 | 0 | baseline_overlay_coco_config.log |
| coco_sim | 135 | 0 | 0 | final_static_and_sim_tests.log |
| custom_teleop | 75 | 0 | 0 | baseline_overlay_custom_teleop.log |
| gazebo_models | 206 | 0 | 0 | baseline_overlay_gazebo_models.log |
| coco_perception | 139 | 0 | 0 | regression_coco_perception.log |
| coco_moveit_config | 12 | 0 | 0 | regression_moveit_with_prefix.log |
| coco_mission | 317 | 0 | 0 | regression_coco_mission.log |
| coco_rl | 218 | 0 | 0 | regression_coco_rl.log |
| **Total** | **1172** | **0** | **0** | Sum of these runs |

Seven new tests cover physical parameter propagation, control signs, timeout,
nonfinite input/acceleration, TF geometry, startup order/no chassis teleport,
and agreement with existing controller limits. Build: `build_complete.log`
(all nine existing packages), then `final_build.log` (coco_sim after backend
addition). Fatal Python lint, compileall and source/document whitespace checks pass.
Archived unmodified tool logs retain their emitted trailing whitespace.
The earlier optional full-style flake8 report (`style.log`) includes import,
docstring and layout nits; a full-style clean result is not claimed.

## Development failures retained

| Run/log | Verdict and reason |
|---|---|
| baseline_gazebo_models.log | FAIL: no COCO ament index; corrected overlay run 206 PASS |
| build.log | FAIL: first package selection omitted coco_rl/coco_web dependencies; full build PASS |
| regression_coco_moveit_config.log | 7 SKIPPED without user-space MoveIt prefix; rerun 12 PASS |
| probe01 / probe02 | FAIL: logging array not JSON-serializable; explicit traceback added then corrected |
| smoke01 | FAIL: native cylinder wheel setup had no usable ground contact; command queue also aged out |
| smoke02 | FAIL: same contact issue; full-extension-close did not finish normally, test-owned process cleanup required |
| smoke03 | PASS: wheel convex geometry + newest-command queue, all original raw checks and clean Isaac exit |
| smoke04_gui | PASS: GUI/RViz repeat, raw checks and process exits 0 |
| smoke05_bearings | PASS: off-axis landmark + independent full-scan bearing check |
| smoke06_final | Raw checks PASS; overall FAIL: RViz teardown -11 |
| smoke07_shutdown | PASS: producer-first shutdown; 19 checks; all exits 0 |
| nav01 | FAIL: test submitted before lifecycle activation; readiness gate corrected; forced child teardown recorded |
| nav02 | FAIL: goal aborted, error 103, path outside local costmap; no claimed single-cause diagnosis |
| nav03_landmark / nav04_final | Navigation PASS; teardown PARTIAL as detailed above |
| nav06_uncomposed / nav07_map | FAIL: map startup then action timeout/RViz teardown, detailed above |
| nav05_uncomposed | FAIL: installed Nav2 launch PythonExpression requires `False`, not lowercase `false`; stopped and corrected |

Normal fast-close is Isaac's validated/default path. Full extension-by-extension
unload was tested and failed; it is not enabled. The final harness cannot call
an auxiliary crash or forced timeout a whole-run PASS.

## Boundaries

UNKNOWN/not attempted: full mission, MoveIt/manipulation in Isaac, perception
execution, IMU, noisy encoder odometry, complete deterministic fetch world,
random layouts, terrain/ramp transfer, cold-cache startup in this final fixture,
long-duration stability and performance rates across repeated episodes.
The common episode specification and safe manipulation envelope are unchanged.

Functional additions: `coco_sim/coco_sim/isaac/{__init__,config,model,runtime}.py`,
`coco_sim/test/test_isaac.py`, `coco_sim/rviz/isaac.rviz`,
`scripts/isaac_sim_coco.sh`, `scripts/isaac_ros.py`, `scripts/isaac_smoke.py`,
`scripts/isaac_smoke_observer.py`, `scripts/isaac_fixture_map.py`,
`scripts/isaac_nav_observer.py`. Documentation: `docs/ISAAC_BACKEND.md`,
`docs/EPISODE_ARCHITECTURE.md`, session checkpoint and this evidence directory.
