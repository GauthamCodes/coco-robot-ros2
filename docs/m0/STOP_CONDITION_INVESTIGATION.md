# M0 stop-condition investigation — 2026-10-06

## Scope and starting state

M0.1 follow-up only: resolve the test failure and establish the odometry
semantics for the plan owner. No later checkpoint or milestone started.
Starting HEAD: `103b94cd09abda6735b4085b6189a71de1c6c00f`.
Branch: `coco-2.1-isaac-integration`.
Worktree: `/home/gautham/coco-isaac-21`, initially clean.
`docs/STATUS.md` is absent; it was not created in this restricted session.
Read canonical MASTER_PLAN.md and the existing M0 audit. Historical audit,
evidence and plan remain unchanged.

## Test root cause and minimal correction

`coco_web/test/test_mission_view.py::_executive_constants` parses top-level
assignments in `coco_mission/scripts/mission_states.py` using AST. The failing
test requires every self-named string constant to belong to mission_view's
state/reason inventories or its five explicitly enumerated result/escalation
constants. It is a bidirectional drift guard for the telemetry copy, not a
mock of robot behavior.

Commit `e4ed2292440b03f17b25b50c91da664ec1fe0dac` introduced:
- state `RETREAT` at mission_states.py:116;
- reasons `RETREAT_FAILED`, `RETREAT_TIMEOUT`, `RETREAT_POSE_UNVERIFIED`
  at mission_states.py:173–175.

The mission implementation symbols exist and are used. The copied display
inventory was last synchronized before this change (test history points to
`320223d128f3ed057d2b517050a1b511bbdf85b0`). Thus the problem is a stale
production telemetry copy, not a missing mission symbol or a faulty test.

Correction: add RETREAT to mission_view's states, display phase RETURNING and
wording; add its three reasons; synchronize exact state/reason count assertions
from 20/53 to 21/56. The missing-constant assertion is unchanged. RETREAT is
not added to the nominal IDLE-to-COMPLETE path, which remains 16 entries.
Only display metadata changes; no autonomy, launch, parameter or command path
changes. No new package dependency is introduced.

Targeted verification, from coco_web after sourcing the previously clean-built
COCO overlay and setup_env.sh:

```
python3 -m pytest -q test/test_mission_view.py
46 passed in 0.12s
```

0 failed, 0 skipped. This includes the unchanged missing-constant guard and the
state/phase/wording checks. An earlier unsourced pre-correction invocation
reproduced 1 failure, 44 passed, 1 skipped; sourcing the overlay enables the
configuration-dependent test. The initial edit command used the package cwd
with repository-relative paths and failed before writing; corrected cwd was
used for the actual edits. No full clean-build rerun or CI run was claimed.
`git diff --check` passed. CI status for this change is NOT VERIFIED.

## Outcome B: simulator ground truth

This conclusion is based on producer implementation and deployed configuration,
not the word “odometry”. Model-state world pose is simulator ground truth even
when encoded in nav_msgs/Odometry.

### Gazebo dependency chain

Gazebo model entity world pose in EntityComponentManager
→ gz::sim::systems::OdometryPublisher
→ gz.msgs.Odometry `/model/coco/odometry`
→ ros_gz_bridge parameter_bridge
→ nav_msgs/Odometry `/model/coco/odometry`
→ mission_executive / ramp_driver / coco_ramp_env / grasp_server.

- `gazebo_models/urdf/coco_robo2.xacro:556–566` configures the plugin,
  odom_frame world, robot_base_frame base_footprint, dimensions 3, 50 Hz.
  No xyz/rpy offset or gaussian noise is configured in this block.
- `gazebo_models/launch/full_world_robo.launch.py:109,130` expands that Xacro;
  lines 199–205 launch ros_gz_bridge with config/bridge.yaml.
- `gazebo_models/config/bridge.yaml:46–54` preserves the name and converts
  GZ_TO_ROS, gz.msgs.Odometry to nav_msgs/msg/Odometry. It does not integrate
  wheels or estimate pose.
- Installed libgz-sim8, libgz-sim8-dev and libgz-sim8-plugins versions are
  `8.13.0-1~noble` (dpkg-query).
- Matching upstream source tag gz-sim8_8.13.0, file
  src/systems/odometry_publisher/OdometryPublisher.cc, lines 383–392 reads
  `worldPose(this->model.Entity(), _ecm)` and fills pose directly. Twist is
  derived from successive model poses and smoothed; no wheel or sensor
  integration produces the pose. Default gaussianNoise is zero.
  Source: https://raw.githubusercontent.com/gazebosim/gz-sim/gz-sim8_8.13.0/src/systems/odometry_publisher/OdometryPublisher.cc
  Retrieved source SHA256: a4acf7d2c4970b0505b60351be94450d51575c7427e5cc92032e340e9b9cce29.

The configured child-frame name does not change the source into wheel odometry.
Gazebo's separate diff_drive_controller odometry is distinct from this plugin.

### Isaac dependency chain

Isaac articulation simulator state
→ robot.get_world_pose(), get_linear_velocity(), get_angular_velocity()
→ coco_isaac_backend (coco_sim/coco_sim/isaac/runtime.py)
→ nav_msgs/Odometry `/model/coco/odometry` when args.fetch
→ the same shared autonomy consumers.

- runtime.py:304 creates coco_isaac_backend; lines 335–340 create gt_pub.
- runtime.py:469–488 reads world pose and physics velocities. It rotates the
  chassis-clearance offset to represent base_footprint and subtracts spawn XY
  for the odom-frame version. Lines 511–536 fill and publish that Odometry.
- runtime.py:537–544 deep-copies the message, restores spawn XY, sets world
  frame and publishes `/model/coco/odometry`. This is transformed physics
  state, not wheel-derived or noisy sensor-derived odometry.
- config.py:21 and runtime.py:343,536 ALSO publish this simulator-derived
  state to `/diff_drive_controller/odom`; runtime.py:585–587 broadcasts its
  odom→base_footprint transform. Therefore moving just the named world topic
  under /eval would not remove all indirect privileged access in Isaac.
  Nav2 (gazebo_models/config/nav2_params.yaml:520), approach_server
  (custom_teleop/custom_teleop/approach_server.py:299,343), and ramp_env's
  wheel-odom fallback consume that parallel odometry channel. Perception and
  other TF consumers can also obtain the ideal base transform indirectly.
  The plan already names Isaac wheel odometry as M3 work; no replacement is
  implemented here.

### Active direct autonomy consumers and affected behavior

| Consumer | Code evidence | Behavior affected |
| --- | --- | --- |
| mission_executive | scripts/mission_executive.py:284–285,394–398,477; mission_states.py:1211,1284–1290,1316–1333,1357–1364,1388–1405,1462–1469 | startup pose availability; navigation/home/bypass arrival acceptance and retries; pre-climb alignment/flat checks; climb corroboration; retreat exit release; robot yaw/world-y transforms for perception search-corridor acceptance |
| ramp_driver | coco_rl/ramp_driver.py:274,310–312,335–336,359–374,475–485 | world lateral-error feedback for autonomous selected-region heading correction and status |
| coco_ramp_env, created by ramp_driver | coco_rl/ramp_env.py:243,264,295–296,336–350,389–407; ramp_driver.py:466–486,539–547 | preferred GT position/yaw/twist enter policy observations, progress/termination, segment timing; descent/retreat steering and endpoint stopping use the same preferred pose |
| grasp_server through ArmControl | coco_moveit_config/scripts/grasp_server.py:197–207,384,464; arm_control.py:215–218,409–442 | pre-grasp and pre-place checks reject stale pose or excessive physical roll/pitch; expect_xy=None disables only XY gate, not GT attitude gate |

The topic is outside `/eval`. No filtering or information boundary in the
bridge/subscriptions prevents autonomy receiving its simulator state.
Even “verification-only” gates affect whether the robot proceeds or retries,
so these are autonomy inputs, not an offline evaluator.

### Other subscribers in the repository

These tools are not all launched by the standard fetch launch. They are listed
to distinguish active autonomy from diagnostics and historical operator paths:

- `gazebo_models/scripts/map_drive.py:121`: automated mapping drive, waypoint
  feedback from world pose (another motion consumer if invoked).
- `gazebo_models/scripts/traverse_demo.py:103`: historical mission harness,
  readiness/world-pose observation; invokes shared ramp/grasp consumers.
- `coco_moveit_config/scripts/pick_place.py`: inherits ArmControl subscription;
  pre-flight/post-run world XY/upright checks (lines 300,356).
- `gazebo_models/scripts/nav_round_trip.py:88`: navigation measurement/tooling,
  records world trajectory/displacement.
- `gazebo_models/scripts/nav_bench.py:571`: evaluator subscriber; explicitly
  described as evaluation-only.
- `gazebo_models/scripts/pitch_probe.py:101`, `climb_check.py:71`,
  `verify_sim.py:55`: physical probes/validation.
- `coco_perception/coco_perception/vision_check.py:158`: perception benchmark
  reference world-to-base comparison, not target_pose_node's detector input.
- `scripts/isaac_fetch_observer.py:161`: run observer.

Localization_monitor has no subscription to this topic (its source and test
explicitly guard that). Default Gazebo Nav2 and approach_server use separate
controller odometry, not the world topic. This distinction does not clear the
shared executive/ramp/manipulation violation.

No simulator was started; no live graph was queried or claimed. Producer code,
launch configuration and matching Gazebo source suffice for outcome B.
No claim is made about arbitrary external runtime remaps not stored in the repo.

## Master Plan consistency and owner decision

Contradictory to integrity rule 1: autonomy receives simulator ground truth,
and this ground truth is outside /eval. M0's behavior freeze is respected in
this session. M1/M2 ordering is unchanged; neither has started.
The test defect is resolved locally; the integrity contradiction remains open.

Decision required: Gautham must approve a precise, dated plan amendment resolving
WHEN the enumerated legacy GT-dependent autonomy paths must be removed, relative
to M0's freeze and M1's qualified baseline evaluation. If temporarily retained,
the amendment must explicitly authorize the bounded legacy exception, its expiry
checkpoint, affected consumers/channels and resulting limits on evidence claims.
Otherwise the owner must authorize and place a behavior-changing removal before
compliant evaluation. Renaming the topic or calling world pose “odometry” cannot
resolve the contradiction. This session proposes no architecture or milestone
reordering and does not edit the plan on the owner's behalf.

Exactly one next action: Gautham records that plan decision before further M0 work.

## 2026-10-06 approved-amendment follow-up

Gautham approved pre-M1 isolation remediation; recorded before implementation in
`../STATUS.md` at commit `b541fc8`. The original findings above remain historical
evidence. The expanded [dependency map](GROUND_TRUTH_ISOLATION.md) found direct
Gazebo object-height API access and Isaac `/grasp/<target>/height` truth in active
grasp/lift/release gates, plus Isaac low-level physics yaw feedback. Live
production GraspServer graph evidence and fail-closed tests are preserved in
`gti/`. The missing legitimate independent object-motion observation triggers
the authorized architectural stop boundary. Isolation is still unresolved; M1
has not started. The previous next action is superseded by the follow-up next
action in the dependency report.

## 2026-10-06 fail-closed remediation follow-up

The plan owner subsequently approved legitimate replacement or explicit
fail-closed handling of every privileged autonomy input. Amendment: `f47f4df`;
implementation: `e4f58dad27e7506a049f0f604514eef44a8fc6bb`. See
[the current observation contract and isolation evidence](MANIPULATION_OBSERVATION.md).
The original blocker and next-action statements above are historical and are
superseded by that report. World odometry/height are now evaluator-only; normal
odometry/TF are encoder-derived; manipulation's missing physical observation
fails closed. Historical evidence remains unchanged. M1 has not started.
