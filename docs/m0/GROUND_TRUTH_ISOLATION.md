# M0 ground-truth isolation boundary investigation — 2026-10-06

## Scope and result

M0, approved ground-truth isolation amendment; exit criterion: remove privileged
state from autonomy before compliant evaluation. **Unresolved.** No production
code, thresholds, command path or milestone structure changed. M1 did not start.
Starting SHA `74875c7aca2fcb5a6d3020438588a39b8855c22b`, expected branch
`coco-2.1-isaac-integration`, worktree `/home/gautham/coco-isaac-21`, clean.
Amendment recorded before implementation in `docs/STATUS.md`, commit `b541fc8`.

The extended trace found an additional architectural boundary: object-height
truth gates grasp attachment, lift verification and release verification. Wheel
encoders and IMU cannot measure independent target-object motion. The existing
RGB-D detector does not expose the required tracked height. The user explicitly
requires stopping at missing sensor-input boundaries and forbids inventing an
input, substituting truth, weakening gates or undertaking a larger redesign.
Consequently this session stops before a partial production replacement that
would leave the full mission privileged. This is a blocker report, not successful
remediation or an isolation proof.

## Trace method and coverage

Read MASTER_PLAN, AUDIT, STOP_CONDITION_INVESTIGATION and then created STATUS.
Searched the full repository for the named odometry topic, `/eval`, model-state
and world/articulation pose, velocity and simulator API calls, publishers,
subscriptions and shell-outs. Followed production backend, launch, bridge,
mission, ramp, perception, manipulation, normal odometry/TF and control inputs.
Historical `docs/data` matches were read as evidence, not active production code;
they remain unmodified. Read matched call sites to distinguish motion consumers,
backend physics/sensor simulation, evaluation and operator tools. Arbitrary
external remaps, external nodes and a complete running simulator graph have not
been audited. No assertion of universal isolation is made.

## Source → interface → node → behavior and genuine input required

| Source | Topic/API | Consumer → behavior | Genuine required input / classification |
| --- | --- | --- | --- |
| Gazebo model EntityComponentManager world pose | OdometryPublisher in `gazebo_models/urdf/coco_robo2.xacro`, bridged in `gazebo_models/config/bridge.yaml`, `/model/coco/odometry` | mission_executive → startup, arrival/alignment/climb/search/retreat gates | planar motion estimate in the plan's coordinate frame; use legitimate localization/encoder estimate, not truth |
| Isaac `robot.get_world_pose`, physics linear/angular velocity | same world topic, `coco_sim/coco_sim/isaac/runtime.py` | same shared consumers | same requirement; world-offset subtraction is still truth |
| Same world topic, both backends | ramp_driver `odom_topic` | selected-region lateral steering and descent endpoint stopping | estimated planar location/yaw; region geometry is prior map structure |
| Same world topic | CocoRampEnv preferred `_gt` input | observations, progress/termination, time stepping; driver climb/descent/retreat | encoder motion/displacement/twist plus IMU roll/pitch; current `_odom` fallback alone is insufficient while Isaac normal odom is truth |
| Same world topic | ArmControl `_gt_cb` inherited by grasp_server and pick_place | fresh/upright posture; standalone demo XY gate | IMU attitude, odometry/localization XY; planar encoder quaternion must not masquerade as roll/pitch |
| Isaac physics state | `/diff_drive_controller/odom` and `/tf` odom→base_footprint | Nav2, approach_server, ramp_env fallback, global TF consumers | replace producer semantics with encoder integration; renaming only the world topic does not solve this |
| Isaac body angular velocity | runtime `measured_yaw` → `DriveCommand.step` → YawServo | final wheel-target yaw feedback | measured angular rate from legitimate IMU/encoder source; another physics-feedback path requiring explicit attention |
| Gazebo object pose | ArmControl `model_z` → `run_cmd(['gz','model','-m',name,'-p'])` | `target_height` → grasp_magnet, check_lifted, GraspServer.check_released → mission success/retry gates | independently observed object rise/resting height; **missing current sensor contract; blocker** |
| Isaac target rigid-body world pose | `Magnet.publish`, `/grasp/<target>/height` Float64 | ArmControl target_height → same attachment/lift/release gates | same missing independent observation; the topic name disguises privileged semantics |
| Gazebo world odometry | map_drive | autonomous mapping waypoint P-controller | localization/encoder estimate; optional legacy motion tool, not standard fetch. It already publishes final cmd_vel directly and must not be considered a compliant arbiter-based autonomy launch |
| Gazebo world odometry | traverse_demo | readiness, pose reporting, invokes shared ramp/grasp | readiness can use legitimate odometry; inherited shared consumers still privileged |
| Gazebo world odometry | nav_round_trip | readiness, records distance/trajectory while sending Nav2 goals | separate legitimate readiness from evaluator-only trajectory measurement |
| World odometry raw bytes | platform_server `sim_topic`, run_platform.sh/verify_all.sh waits, coco_config rate inventory | simulator liveness and launch readiness | no pose decoded; legitimate heartbeat/readiness can replace it. Not an evaluator subscription, so must be considered when truth moves to /eval |
| Gazebo/Isaac simulator target pose | episode_cli → read_gz_poses; runtime check_instantiation and JSON logs | scene-instantiation validation, runtime observer evidence | simulator/evaluator boundary; not robot sensing |
| Simulator world pose | nav_bench, pitch_probe, climb_check, verify_sim, vision_check, isaac_fetch_observer, gazebo_pose_observer | measurement/probes/benchmark reference | evaluator-only truth must move under /eval; tools that also command the robot need that distinction enforced, not just a label |
| Historical world pose/API matches | `docs/data/**` analysis and probes | historical evidence replay | append-only history; no edits |

Producer semantics and the first consumer chain are proved in
`STOP_CONDITION_INVESTIGATION.md` (including matching Gazebo upstream source).
The newly discovered object-height paths are in `arm_control.py:146–165,250–258,
356–405`, `grasp_server.py:507–534`, and `isaac/grasp.py:73–78,151–156`.
The low-level yaw path is `isaac/runtime.py:450,510` and `isaac/config.py:130–149`.

## Legitimate sources already present; replacement not implemented

Gazebo diff_drive_controller is configured with wheel position feedback,
`open_loop: false`, four named wheel joints, radius 0.0585 m, separation 0.274 m
and the existing separation multiplier 1.10. Its normal odometry is separate
from OdometryPublisher world pose. Isaac already exports measured joint positions
and velocities; those can support equivalent differential-drive integration at
`/diff_drive_controller/odom` and its TF. Mission coordinate gates cannot simply
consume zero-origin odometry as world coordinates: the existing map/world
alignment and legitimate localization must be respected without injecting a
simulator pose. Ramp state requires IMU attitude separately from planar odometry.
Mission remains shared between backends; no separate mission logic is proposed.

TerrainObserver already consumes IMU, joint states and stamped command; its
terrain estimate is not world terrain truth. TargetPoseNode/TargetFinder use
RGB-D and camera calibration/TF. Their local camera→base geometry is legitimate;
Isaac's world-derived odom TF remains an indirect leak for global consumers.
Isaac IMU synthesis currently uses physics pose/velocity as an ideal simulated
sensor; raw world pose must not escape as navigation state. IMU noise/fidelity
is deferred. Simulator-internal magnet contact and weld geometry require world
state to simulate the mechanism; exporting object height to autonomy is the
violation, not retaining physics internally. Existing magnet attach/detach state
alone does not prove an object moved with the arm.

No replacement normal odometry, /eval migration, graph invariant, divergence
proof or full isolated launch was implemented. It would be false to mark any
minimum acceptance condition complete based on this investigation.

## Exact missing-input blocker

1. `grasp_magnet()` records independent target height before attachment and
   refuses if it is unavailable.
2. `check_lifted()` requires independent target rise ≥0.03 m; it was introduced
   because the magnet could say “attached” while welding nothing.
3. `check_released()` requires target center height within 0.02 m of
   `TARGET_HEIGHT / 2`; “detached” does not prove a physical placement.
4. Existing perception explicitly says its point.z is framing dependent and
   its grasp_point.z is fixed `TARGET_GRASP_Z`
   (`coco_perception/coco_perception/target_pose.py:66–81,522–547`). It does not
   track object center/support height or provide independently validated
   visibility, uncertainty and freshness across lift/occlusion/release.

Wheel encoders can report robot/arm motion, not independently verify target
motion. Substituting arm FK, a fixed height, magnet state or stale pre-grasp
perception would conceal precisely the previously measured failure. Adding a
sensor-based lift/release observation contract and establishing coverage would
extend manipulation/perception behavior beyond the approved wheel-state
remediation and frozen gate structure. No such redesign is invented here.
A policy that deliberately fails closed without that input is possible, but
would prevent all grasps and would not preserve the existing functioning mission;
this session does not silently choose it as completed remediation.

Plan-owner decision required on that exact boundary before resuming: explicitly
scope a legitimate lift/release observation contract or approve a bounded
fail-closed unavailable-input behavior. Do not authorize a temporary truth leak.
M3.1 remains wheel-encoder fidelity/ablation, IMU noise and alignment work; this
new manipulation-input gap is **not automatically assigned to M3** by this
report and cannot wait behind a purportedly compliant M1 baseline.

## Evidence and verification

`gti/inspect_grasp_graph.py` constructs the real production GraspServer under
both backend parameters, spins it and reads ROS graph subscription endpoints.
No simulator, grasp, MoveIt goal or command invocation occurs. Domain 174.
`gti/grasp_graph.json` proves the real world-odometry subscription under both
parameters and Isaac's `/grasp/target_red/height` subscription. This is graph
evidence of the **remaining violation**, not a complete launch/graph isolation
test. Gazebo's direct model API read cannot appear in a ROS subscription graph.
No /eval subscription is present on this inspected node; absence alone is
insufficient because truth is currently outside /eval.

Reproduction environment: existing `/tmp/coco-m0-clean-build-20261005` overlay,
`COCO_MOVEIT_PREFIX=/home/gautham/ros2_ws(personal)/moveit_prefix/root/opt/ros/jazzy`,
source repo `setup_env.sh`; run pytest from each package directory. Focused
suites in domain 173: grasp contract 14 passed, Isaac manipulation/adapter 23
passed, arbiter 28 passed (65 total, no skips). Missing lift/release input is
exercised by existing `test_unavailable_lift_and_release_measurements_fail` on
the real server and fails closed as required; this is not an isolation test.
An initial root-directory invocation omitted the explicit MoveIt prefix and
reported one module skip; retained in `gti/focused_tests.log`, superseded by
properly sourced per-package logs. CI is NOT VERIFIED. Local counts alone are
not assigned the plan's CI-dependent TESTED capability label.

Full relevant per-package regression results (domain 175): mission 365,
ramp 236, perception 139, manipulation 28, simulation 228, teleop/arbiter 78;
**1074 passed, 0 failed, 0 skipped**. Perception and teleop retain 12 existing
multi-threaded-fork warnings each. Results are recorded in
`gti/*_regression.log`; no full project clean build or simulator episodes were
performed. All historical success evidence remains historical privileged-input
behavior and cannot serve as a compliant evaluation baseline.

## Exit and next action

Amendment and dependency evidence recorded; isolation stop condition remains
**unresolved**. No behavior changes or second command path introduced. No broad
M0 work, cleanup, M1 work or M3 fidelity experiments. Exactly one next action:
Gautham resolves the newly documented manipulation observation boundary through
Master Plan change control before ground-truth isolation remediation resumes.

## 2026-10-06 fail-closed remediation follow-up

The plan owner subsequently approved legitimate replacement or explicit
fail-closed handling of every privileged autonomy input. Amendment: `f47f4df`;
implementation: `e4f58dad27e7506a049f0f604514eef44a8fc6bb`. See
[the current observation contract and isolation evidence](MANIPULATION_OBSERVATION.md).
The original blocker and next-action statements above are historical and are
superseded by that report. World odometry/height are now evaluator-only; normal
odometry/TF are encoder-derived; manipulation's missing physical observation
fails closed. Historical evidence remains unchanged. M1 has not started.
