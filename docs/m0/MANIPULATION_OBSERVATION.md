# M0 manipulation observation and ground-truth isolation — 2026-10-06

## Checkpoint and provenance

Milestone M0; checkpoint: manipulation observation boundary and ground-truth
isolation. Exit criterion: identified privileged autonomy paths removed,
legitimately replaced or fail-closed, with isolation and regression evidence.
M1 has not started. No general cleanup or fidelity experiments were performed.

Starting SHA: `af8921a57006a3f5110a58316dc0e5b8dbfb652a`.
Branch: `coco-2.1-isaac-integration`.
Worktree: `/home/gautham/coco-isaac-21`, initially clean.
Amendment recorded before implementation: `f47f4df` in `docs/STATUS.md`.
Implementation checkpoint: `e4f58dad27e7506a049f0f604514eef44a8fc6bb`.
Historical violations and original graphs remain in `GROUND_TRUTH_ISOLATION.md`,
`STOP_CONDITION_INVESTIGATION.md`, `AUDIT.md` and `gti/`; none were erased.

**IMPLEMENTED; local automated verification passed; CI NOT VERIFIED.**
The committed active architecture supports the isolation invariant. This is not
RUNTIME VERIFIED full simulator/mission behavior, a measured success rate, or
completion of all M0 checkpoints. Removing truth deliberately removes verified
fetch completion until independent manipulation observations exist.

## Source classification and dependency closure

Classification follows producer semantics, not message/topic names. The trace
searched all repository code for simulator pose/state APIs, model/world/grasp
interfaces, publishers/subscribers, object-height queries, articulation state,
physics velocity, attachment/lift/release conditions and normal odometry/TF.
Historical evidence and archived experiments were classified separately from
active autonomy. No unresolved state source remains in the traced active path.

| Source → interface | Original node → decision → behavior | Classification / current disposition |
| --- | --- | --- |
| Gazebo world entity pose → OdometryPublisher → bridge | executive → arrival, alignment, climb/search/retreat gates → advance/retry/steer | PRIVILEGED. ROS and Gazebo output now `/eval/robot/odometry`; executive consumes controller encoder odometry |
| Same world pose stream | ramp_driver/env → lane error, policy motion observations, descent/retreat endpoints → wheel intents | PRIVILEGED. Removed preferred truth input; measured encoder pose/twist and IMU attitude used instead |
| Same world pose stream | ArmControl/grasp → fresh/upright/XY checks → permit manipulation | PRIVILEGED. XY now encoder estimate plus fixed start prior; roll/pitch from fresh valid IMU |
| Isaac articulation world pose and physics velocities → normal odometry + odom/base TF | Nav2, approach, ramp fallback, global TF consumers → navigation/motion/perception transforms | PRIVILEGED. Normal odometry and base TF now integrate measured wheel angles only |
| Gazebo `gz model -m … -p` → model_z/target_height | ArmControl → pre-attachment reference, lift proof; grasp_server → release proof → attachment, held/placed outcomes | PRIVILEGED. API query removed; model_z and target_height return unavailable; physical gates fail closed |
| Isaac rigid-body world Z → `/grasp/<target>/height` | same shared manipulation gates → same outcomes | PRIVILEGED. Export moved to `/eval/objects/<target>/height`; autonomy subscription removed; former height cache is ignored |
| Isaac physics angular velocity → body-coordinate angular.z → YawServo | backend actuator loop → adjust wheel targets | Original direct input replaced with the exact ideal IMU message's angular_velocity.z. LEGITIMATE simulated gyro-equivalent rate; see detailed boundary below |
| Measured wheel joint positions/velocities → joint_states | controllers, arm/gripper checks, TerrainObserver | LEGITIMATE encoder/actuator state; retained. Joint feedback does not prove object motion |
| Gazebo IMU / Isaac synthesized body-mounted IMU → `/imu` | ramp/terrain/posture checks → tilt/steering/safety gates | LEGITIMATE ideal simulated robot sensor. Does not expose position or object state; noise/fidelity deferred |
| RGB-D rendering → camera/depth/info and camera/base geometry | TargetFinder/TargetPoseNode → target validity/reachability → approach/manipulation goals | LEGITIMATE perception. Validation structure and thresholds retained; no new height/retention observation invented |
| Gazebo DetachableJoint transition / Isaac fixed-joint engagement → `/magnet/<target>/state` | ArmControl.magnet → actuator acknowledgment and cleanup | LEGITIMATE actuator-mechanism acknowledgment only, **not** physical grasp/retention/release proof. No new contact sensor or real-hardware equivalence claim. Independent physical gates remain unavailable |
| IMU, joints, command → TerrainObserver | terrain estimate → robot-observable diagnostics | LEGITIMATE estimated terrain; no simulator terrain truth input |
| World odometry → map_drive | waypoint position error → steering | PRIVILEGED. Replaced with encoder estimate; output goes to `/cmd_vel_gated`, never final wheels |
| World odometry → traverse_demo/nav_round_trip | readiness and trajectory observation → start shared services/Nav2 goals | PRIVILEGED robot input removed; use controller odometry. Their shared manipulation now fails closed |
| Model/world odometry raw arrival → platform_server, readiness scripts and sensor inventory | readiness → permit startup/report health | Not pose-decoded, but unnecessary world-state transport. Replaced with legitimate controller odometry and clock; removed from normal sensor inventory |
| Truth + direct final-wheel output → climb_check | legacy physical climb probe → command/truth-dependent diagnostics | FAIL-CLOSED before creating endpoints. Cannot run the old truth-controlled probe |
| Simulator scene spawn/remove helpers → pick_place standalone demo | setup scene then scripted manipulation | FAIL-CLOSED run entry before scene mutation or motion. Shared active ArmControl contains no model-pose read; preserved operator scene helper is not used by grasp_server |
| World pose/height → nav_bench, pitch_probe, verify_sim, vision_check, isaac_fetch_observer | independent measurement/reference | EVALUATOR. ROS truth input under `/eval`; neither truth pose nor height is forwarded to autonomy. vision_check's teleport is evaluator fixture setup, not active mission control |
| Direct world API → episode_cli/read_gz_poses, Isaac scene checks/logs, gazebo_pose_observer | world-instantiation validation and observation files | EVALUATOR / simulator internal. Direct transport/API retained for observer files, not a robot input. No evaluator observation file is read by autonomy |
| Physics world poses → internal magnet geometry/constraint construction | contact/weld mechanism simulation | SIMULATOR INTERNAL, not robot state export; retained to simulate the existing actuator |
| Historical `docs/data` model queries / archived MuJoCo, PPO/Yard experiments | historical analysis/experimental evaluation | Preserved and excluded from active mission. Shared ROS env rejects legacy teleport reset before ROS initialization; no training, RL redesign or campaign performed |

## Manipulation observation contract

No sensor was added. Arm IK, MoveIt trajectories, existing perception gates,
magnet commands and finger joint semantics are preserved.

| Gate | Minimum independent physical information | Existing legitimate interface | Current result |
| --- | --- | --- | --- |
| Attachment | valid robot-relative target location and independent object reference for subsequent physical verification; engaged actuator alone is insufficient | RGB-D supports acquisition XY; joints support arm/finger motion; magnet supports acknowledgment; no tracked target-height reference | grasp_magnet rejects unavailable reference **before issuing attachment** |
| Lift | independently observed target rise ≥0.03 m after arm motion | joint FK proves arm movement, not target movement; current RGB-D point.z is framing dependent | check_lifted returns false; no held/lifted success |
| Retention | fresh independent evidence that the object remains with the end effector while carrying | magnet engagement/command state alone is insufficient; no existing target tracking/contact observation contract | verified lift cannot be established, so normal mission never enters successful carry/retention; holding remains actuator belief for cleanup, not physical proof |
| Release | independent evidence of object separation and resting center height within 0.02 m of TARGET_HEIGHT/2 | detached acknowledgment does not show object separation/rest; no current independent center/support-height interface | check_released returns false; cannot claim placed |
| Placement | release evidence plus object rest/location inside placement zone | existing acquisition perception does not establish post-release object pose/rest | physical placement unavailable. Future evaluator may score physical reality, but may not feed that verdict back into autonomy |

`target_pose.py` documents why visible point.z differs from target center as
framing/clipping changes and why grasp_point.z is fixed TARGET_GRASP_Z. It is
not relabeled as an independent lift/release measurement. No thresholds,
timeouts or retries were loosened to regain historical success. No hidden truth,
arm FK or actuator state is substituted for independent object motion.

The normal pick sequence may still approach/hover/descend using existing
perception and trajectories, but stops at the unavailable attachment reference,
before weld/close/lift. Stowing and legitimate joint/IMU interfaces remain
available. The standalone scene-mutating pick_place demo is explicitly disabled.
Missing/stale/invalid IMU attitude also rejects manipulation posture checks;
planar encoder orientation cannot stand in for physical roll/pitch.

## Legitimate odometry and angular-rate boundary

Gazebo's existing diff_drive_controller uses wheel position feedback,
open_loop=false and its existing geometry/covariance. Isaac samples measured
joint angles in right-front/right-rear/left-front/left-rear order and integrates
common differential-drive kinematics in `coco_config.encoder_odometry`.
`isaac.odometry.encoder_message` accepts only encoder angles, estimator state and
time; `/diff_drive_controller/odom` and odom→base_footprint TF use that estimate.
No simulator pose, velocity, spawn manifest, target or evaluator result enters
normal odometry. Base elevation is unavailable in planar encoder odometry.

Shared mission/ramp XY gates express zero-origin odometry using the existing
fixed nominal start prior SPAWN_XY. This is a robot configuration/map prior,
not the simulator's actual spawn pose, and is not updated from an episode or
world state. Startup displacement, slip and accumulated drift remain estimation
error. Gazebo and Isaac use the same conceptual normal interface and same shared
mission logic. No claim of metric accuracy, physical calibration or parity.

Isaac's prior `angular[2]` was a direct body-projected physics velocity passed
into DriveCommand. It is now passed only as `imu.angular_velocity.z`, the exact
body-mounted ideal gyro sample published on `/imu`; this contains robot-local
angular rate, not world position or target state. The synthesis uses body-frame
physics rotation/velocity, as simulated sensor generation must. This does not
add a sensor: the fetch backend already synthesized that IMU. In non-fetch
foundation mode no IMU interface exists, so body-rate feedback remains disabled
rather than falling back to raw physics state. The actuator loop still accepts
only the arbiter's final stamped command; gains, bounds and timeout are unchanged.
IMU noise, sensor placement calibration, wheel-slip fidelity/ablation and map
alignment experiments remain M3 work.

## Enforcement and proof

Robot-side nodes use AutonomyNode, a narrow ROS endpoint guard. It resolves
launch remaps before rejecting `/eval`, `/model`, `/world` and legacy grasp-height
subscriptions. It also rejects final-wheel publication outside CmdVelArbiter.
The arbiter selection/watchdog/preemption semantics are unchanged. Legacy direct
relay/teleop/mapping outputs now use existing arbiter inputs; nav.launch's legacy
flag cannot create a bypass. Commands stop if the required arbiter is absent.

`coco_mission/test/test_ground_truth_isolation.py` constructs real executive,
ramp_driver, ramp_env, grasp_server, TerrainObserver, both perception nodes,
approach_server, localization_monitor, relay and arbiter. It inspects discovered
ROS subscription endpoints under both backend parameters. A real evaluator
subscriber receives deliberately contradictory `/eval` truth (X=1000 m), while
normal encoder odometry reports X=0.117 m and the executive uses X=-1.883 m
in the nominal arena prior. Ramp/env/manipulation also receive normal state.
Injected evaluator object height and even the former height cache cannot satisfy
attachment/lift/release. The graph has exactly one final wheel publisher,
cmd_vel_arbiter. Resolved remaps to privileged namespaces and direct wheel output
are tested to fail before endpoint creation. Source/API checks complement this
real graph proof; they do not replace it.

`coco_sim/test/test_encoder_isolation.py` verifies distance/arc/turn integration,
invalid samples, shared Gazebo feedback geometry/frame/covariance, deployed Isaac
publisher/TF encoder provenance and Gazebo's evaluator-only world bridge.
`test_grasp_contract.py` verifies no attachment command without observation and
that missing/stale IMU is not replaced by encoder attitude.

Limits of proof: no full simulator launch, C++ Nav2 graph or qualified physical
mission was run. Nav2's committed odometry config remains the legitimate normal
interface; base TF producer provenance is checked. Arbitrary external ROS nodes
or uncommitted remaps are outside this evidence. The existing CI suite collects
these tests, but no remote CI execution is claimed. Capability label remains
IMPLEMENTED with local automated evidence, not CI-dependent TESTED.

## Build, tests and retained evidence

Fresh overlay: `/tmp/coco-m0-gti-remediation-20261006`; 9/9 packages built.
Read-only MoveIt dependency prefix explicitly set via COCO_MOVEIT_PREFIX.
Focused graph/executive checks: 50 passed. Encoder/Isaac adapter/manipulation
checks: 32 passed. Full relevant nine-package regressions from the fresh overlay:

| Package | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| coco_config | 92 | 0 | 0 |
| coco_mission | 375 | 0 | 0 |
| coco_moveit_config | 32 | 0 | 0 |
| coco_perception | 139 | 0 | 0 |
| coco_rl | 236 | 0 | 0 |
| coco_sim | 237 | 0 | 0 |
| coco_web | 575 | 0 | 0 |
| custom_teleop | 78 | 0 | 0 |
| gazebo_models | 220 | 0 | 0 |
| **Total** | **1984** | **0** | **0** |

Raw build, focused and per-package regression logs plus both backend graph JSON
files are in `gti_remediation/`. Initial failed regression logs are retained:
import-order errors introduced by the guard imports and stale direct-wheel/world
odometry expectations were corrected. Existing setuptools unbuilt-egg and
multi-threaded-fork warnings remain recorded. No simulator episodes, performance
campaign, held-out inspection or historical evidence deletion occurred.

Reproduction: export COCO_WS to the fresh overlay, set COCO_MOVEIT_PREFIX to the
recorded read-only prefix, source repo setup_env.sh; from each package run
`python3 -m pytest -q test`. Set COCO_GTI_EVIDENCE to a new directory to capture
current graph JSON without replacing historical evidence. Tests use private
ROS domains; graph fixtures intentionally contain an evaluator listener.

## Status and next action

Ground-truth isolation: compliant in the committed active architecture with
explicit unavailable-observation gates; locally verified by automated graph,
provenance and regression tests. Full physical fetch completion is unavailable
and not claimed. No remaining owner decision is required to enforce this
fail-closed boundary. A future legitimate retention/lift/release observation
contract needs explicit milestone scope; this report does not assign it to M3.

M3 retains odometry/IMU/alignment fidelity, C++ arbiter, safety case, Docker,
CI expansion and observability. M0's oracle, seed policy, manifest and remaining
control/audit checkpoints are not completed here.

Exactly one next action under MASTER_PLAN: resume M0.2 control files and status
inventory, using this capability limitation and evidence. Do not start M1.
