# COCO 2.1 — Isaac Sim digital twin and cross-simulator integration

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

[Diagnosis, correction, reproduction and limitations](data/isaac_fetch/coco24/README.md) ·
[Pre-fix/post-fix measurements](data/isaac_fetch/coco24/comparison.json).
Historical results below remain intact.

## COCO 2.3 — matched positions-level repeatability (2026-10-05)

Five existing P03D `positions` layouts (seeds 5–9), requesting red, were run once
per simulator with the shared fetch runner at SHA
`2e15706875c4850fe3a00200a9c5fd878e4b312d`. Backend manifests match apart from
backend/episode ID; all four targets use the existing seeded region placement
sampling. The preceding milestone's colours-level seed 5 does not count here.
Fresh sequential runs use the existing Isaac/Gazebo launch profiles, shared
mission/safety chain and fixed 1200-wall-second observation budget.

**Verdict B: partial repeatability demonstrated, with specific failure modes.**
Isaac physically completed 3/5 (60%), Gazebo 4/5 (80%); both completed 5, 8, 9,
and Gazebo also completed 7. Isaac 6/7 timed out during the first search-continuation
descent before acquisition. Gazebo 6 aborted after an ODE collision assertion
stopped simulation time during the second descent. Exact physical triggers and
whether failures are deterministic remain unverified. Gazebo 5/9 physically
completed but retain observer idle-mode timing flags; original protocol pass
counts are 3/5 Isaac and 2/5 Gazebo. Source digests and all command graphs verify
unchanged runtime code and the sole authoritative `cmd_vel_arbiter` wheel path.

Completed placement error averaged 0.289 m Isaac (n=3) /0.093 m Gazebo (n=4);
first verified lift averaged 33.0/34.775 mm. In the three both-completed pairs,
Isaac minus Gazebo averaged +53.734 sim seconds, +174.506 wall seconds and +0.206 m
placement error. These descriptive measurements do not establish performance
or physics parity. Displaced-target fetches are demonstrated across three
matched lane 1 layouts; broader search-region repeatability remains incomplete.
Five distinct layouts, one trial each, do not establish reliability or production
readiness. Ideal Isaac odometry, contact/grasp approximations, asynchronous
telemetry and variable simulation rates remain limitations.

No implementation fix, parameter adjustment or rerun was made. Only evidence
orchestration/evaluation and documentation changed. All nine relevant package
suites passed 1,952 tests once after the batch. The major next milestone is to
characterize and validate search-continuation far-slope descent across backends.

[Full methodology, outcomes, failure evidence and limitations](data/isaac_fetch/coco23/README.md)
· [All ten episodes and aggregates](data/isaac_fetch/coco23/comparison.json).
The sections below describe preceding historical milestones.


## COCO 2.2 full-fetch investigation (2026-10-03)

Starting state: clean `589e1f1b8225a857d7c03ed9f019f53a5bd1efb9` on
`coco-2.1-isaac-integration`. The records in
[`data/isaac_fetch/coco22`](data/isaac_fetch/coco22/) extend the previous milestone;
historical records below are retained. **One Isaac full fetch is physically
verified COMPLETE** (`coco22/fetch_009`, seed5, colours-level red). Matched Gazebo
comparison is also runtime verified COMPLETE (`coco22/gazebo_004`). This is
one complete episode per simulator, not a parity or reliability claim.

Measured grasp-entry x/y was `(0.15456, -0.00388)` m, first lift 32.8 mm;
the target remained welded over 6.06 m carry displacement (95 samples,
maximum palm-relative span 0.318 mm). After opening, detach and arm retreat,
it stood upright at `(-1.81776, -0.20426, 0.079014)` m, 0.274 m from home.
Mission runtime was 255.77 sim / 729.48 wall seconds, zero recoveries;
simulator, mission and observer all exited zero. Final wheel publisher remains
the arbiter. Bypass arrival error was 0.352 m within the unchanged 0.50 m
consistency band; navigation timing remains variable.

Reproduce with the existing isolated overlay and native installation described
below (use new output directories):

```bash
export COCO_WS=/home/gautham/coco_isaac21_ws
export COCO_MOVEIT_PREFIX=/home/gautham/coco_p03d_ws/moveit_prefix/root/opt/ros/jazzy
source setup_env.sh
python3 scripts/isaac_fetch.py /home/gautham/coco22_runtime/isaac_new --domain 82
python3 scripts/isaac_fetch.py /home/gautham/coco22_runtime/gazebo_new --backend gazebo --domain 88
```

The runner's default Isaac Nav2 profile exactly matches the completed run's
explicit saved profile: alpha1–5=0.001 for ideal odometry, DWB rotation window
0.20 m inside the unchanged 0.25 m goal checker. Gazebo keeps canonical
parameters. Run profiles, source hashes/patches, logical task inputs and
physical telemetry are retained; `--params-file` overrides either backend.

The matched Gazebo run measured grasp-entry x/y `(0.15455, -0.00039)` m,
34.4-mm first lift, 6.34-m carry displacement and upright release at
`(-1.88162, +0.03482, 0.079000)` m, 0.123 m from home. It completed in
166.39 sim / 174.44 wall seconds with zero recoveries. Both runs retain
source provenance, physical traces, single-arbiter graphs and zero owned
process exit codes. See the detailed n=1 table and limitations in
[`data/isaac_fetch/README.md`](data/isaac_fetch/README.md).

Gazebo startup exhausted DDS participant indices before mission start.
A held-process diagnostic measured 32/40 ready under the existing setup
and 40/40 with explicit maximum index119. The fetch runner scopes that
loopback discovery configuration to its Gazebo children only. An earlier
startup stall remains unexplained; all failed attempts are preserved. No
Gazebo rebuild or wheel-command bypass was introduced.

Implementation checkpoint: `70d3f38c0e99de8f35c8a419f16e4ae00b84f672`;
the final evidence commit also adds the measured DDS correction. Runtime
patches/digests identify the tested code precisely. Resolve the evidence
commit with `git log -1 --format=%H -- docs/data/isaac_fetch/coco22`.

Run006's apparent target loss was a clock-domain error: two valid RGB-D fixes
were only 0.100 s apart in simulation but 1.185 s apart in wall time, exceeding
the approach controller's wall-time freshness limit. The controller now ages
image timestamps in simulation time, rejects invalid frames/values, and
reprojects the last observed pose using measured base odometry. Level settling
at the ramp crest now stops the base; it previously drove toward an already
near target during settling. Creep timeout fails closed and its final pose
estimate uses measured translation and rotation.

Measured Isaac yaw response at a requested 0.1 rad/s was approximately
0.0035 rad/s, while 0.03 m/s forward motion tracked at 0.0291 m/s. Disabling
self-collision did not resolve this skid-steer dead zone and was reverted.
A bounded body-yaw feedback adapter corrects the physical wheel conversion
behind the existing arbiter. Wheel gains, geometry, acceleration bounds and
the disclosed 2 Nm drive ceiling are unchanged. Short probes improved yaw
response; they do not establish perfect tracking or numerical Gazebo parity.

Arm command delivery was starved by one ROS callback per render step. Logged
backend targets stopped at 0.4167 rad despite a 0.5-rad finger request.
Bounded callback draining delivers the complete request. During physical
magnet attachment, contacts between the target and its welded palm/fingers
are filtered to avoid fighting the fixed joint; world contacts remain active
and internal contacts are restored on detach. This remains an explicit
fixed-joint magnet approximation, not a friction grasp.

Fetch005 physically acquired and lifted the target on its first attempt,
then retained it over 2.62 m of travel (44 simulator samples; largest
palm-relative position span 0.149 mm). It aborted during bypass navigation;
acquisition is not a full fetch. Retry logic incorrectly re-seeded AMCL at the
nominal ramp exit after the robot had already driven away. The shared executive
now performs that region-based handoff once, preserving current localization
on retries. No target coordinates are supplied to navigation.

Fetch007 completed bypass and returned home with physical retention over
6.05 m, then aborted at placement. CCD and clearance alone did not resolve
floor penetration. A free-body probe, without any weld, also lost the cylinder
through the scaled box floor. Replacing that floor with flat triangles, using
the same contact offsets and friction, retained released cylinders at their
expected 79-mm centre height. The canonical fetch world now uses this plane;
the original mobile-base fixture is unchanged.

Placement also changed palm pitch: the previous nominal x/z IK tilted the
acquired cylinder approximately 7.4 degrees, beyond its static stability
angle. Matched-height drop probes distinguished tipped (10-mm centre) from
upright (79-mm centre) outcomes. Shared placement now derives a clearance pose
from the perception-driven grasp, preserving palm pitch. Its FK height,
orientation and joint-limit checks pass. At the actual acquisition geometry, detach-before-open restores contacts
against closed fingers and tips the cylinder. Arm-only probes with canonical
target inertia/friction distinguish detach-first (10-mm centre) from open-first
(79-mm centre). Shared placement now opens while welded, then detaches; failed
opening retains attachment. Fetch009 verifies the full release sequence.
Run-local AMCL noise and DWB goal-radius experiments are recorded
separately from the canonical Gazebo configuration. Isaac uses ideal pose
odometry; localization and short Nav2 action-acknowledgement deadlines remain
measured runtime risks.

## Historical COCO 2.1 consolidation (2026-10-02)

The session begins at `569b81ff744c2542498bd37201ef509b3ec4b949`.
The initial base fixture remains reproducible without `--fetch`. The new
`--fetch` mode builds the canonical arm and `coco_world` target arena and
launches the shared P03D mission; it does not implement a second mission.
Historical P03D evidence has not been rewritten.

| Capability | Current evidence level |
| --- | --- |
| Four-wheel base, safety/arbiter, Nav2 interfaces | Runtime verified; original fixture smoke evidence below |
| Arm/gripper geometry, joint frames, URDF mass/inertia/limits | Implemented; FK and command-boundary tested; articulation initializes at runtime |
| Arm action controller and gripper trajectory adapter | Implemented; ROS controller tests cover arrival, cancellation, stale feedback and timeout; physical MoveIt stow trajectory runtime verified (run006) |
| Canonical arena and four randomized coloured targets | Runtime verified; settled poses checked against episode |
| RGB-D, LiDAR, IMU, odometry, eight joint states and arm TF | Runtime publication verified; rates recorded |
| P03D mission launch, lifecycle readiness, sole arbiter publisher | Runtime verified through successful climb and approach/recovery failures |
| Proximity-gated magnet, lift/release measurement | Implemented and boundary tested; physical attach/lift/release not yet runtime verified |
| Perception execution | Runtime verified positive RGB-D pose and target search transition (run006); close approach loses the target |
| Full fetch / cross-simulator parity | **Not demonstrated** |

The host Jazzy process exposes MoveIt's existing
`/arm_controller/follow_joint_trajectory` action. Validated arm-only
`JointState` commands cross Isaac's bundled Humble bridge. Completion uses
fresh measured joint positions. The gripper retains its existing trajectory
topic. Isaac magnet attach creates a physical fixed joint at the current
relative pose only when the target intersects the pinch envelope; no snap,
teleport, target-coordinate navigation or evaluator movement shortcut exists.

Safety repairs also apply to Gazebo: grasp no longer falls back to a nominal
pose when the approach fix is absent, invalid or stale, and missing height
feedback fails verification. Colour changes clear the perception fix. Joint
arrival requires fresh feedback. These are deliberate fail-closed changes.

### Reproduce the fetch attempt

Use an isolated COCO overlay with Jazzy, Nav2, MoveIt and ROS message packages.
On this machine the installed MoveIt prefix is read from the existing P03D
workspace; it is never modified by the runner. Other installations can use
system MoveIt or set their own `COCO_MOVEIT_PREFIX`.

```bash
cd /home/gautham/coco-isaac-21
export COCO_WS=/home/gautham/coco_isaac21_ws
export COCO_MOVEIT_PREFIX=/home/gautham/coco_p03d_ws/moveit_prefix/root/opt/ros/jazzy
source setup_env.sh
# After source changes, build all nine packages in the selected overlay:
cd "$COCO_WS"
colcon build --symlink-install
cd /home/gautham/coco-isaac-21
source setup_env.sh
python3 scripts/isaac_fetch.py /tmp/coco-fetch-new --domain 82 --timeout 600
```

The output directory must be new. The runner writes exact commands/source
provenance, expanded URDF, manifest, task-only robot input, measured target
placement, simulator/mission logs, ROS observations, results and exit codes.
It waits for all Nav2 lifecycle nodes, MoveIt and shared worker services,
then starts `/mission/start`. It shuts down only process groups it created,
including orphan descendants; it does not use global `pkill` or alter other
workspaces. Interrupted/failed runs retain their outputs and return failure.

The native Isaac installation is expected at `$HOME/isaac-sim`, version4.5,
with its Python3.10 venv and bundled Humble bridge. The shell wrapper isolates
that environment from host Jazzy3.12, uses CycloneDDS on loopback and an
advisory lock to prevent concurrent COCO Isaac launches. No Docker/GPU
container or external service was verified here.

### Model and measurement limitations

The base retains primitive collision geometry and approximate inertia from
the measured Isaac fixture. The arm uses URDF primitives and principal axes
of the full URDF inertia tensor; arm visuals reuse the canonical CAD STL meshes; base/wheel visuals remain primitive.
The fixed mounting link retains its URDF mass and a fixed articulation joint. Isaac
wheel velocity drives retain the fixture's 2 Nm force ceiling, exceeding the
0.4 Nm URDF wheel effort: the 0.4 Nm experiment produced poor steering and an
off-lane climb. This is a disclosed simulator actuator approximation, not
physical hardware equivalence. Arm drive gains require physical-motion tuning.

Isaac odometry is perfect measured pose relative to spawn, not wheel-integrated
odometry. IMU specific force is derived from body motion plus gravity without
noise. Magnet grip approximates Gazebo's DetachableJoint semantics, not contact
friction grasping. Only `coco_world` is implemented; Yard remains unsupported.
Current startup yaw is the canonical zero-yaw episode. Low-speed steering
and near-field approach remain uncalibrated: run006 reaches perception/arm
stow, but repeated navigation attempts also fail, and the gain20 experiment
was rejected. The baseline gain1 is retained. Cross-Humble/Jazzy DDS
emits type-hash warnings; actual deliveries and lifecycle failures are logged.
A shared PoseProgressChecker now recognises measured in-place rotation while retaining the translation and time bounds. The two existing goal tolerances remain unchanged.
See the [Jazzy plugin documentation](https://docs.nav2.org/jazzy/configuration_and_development/navigation_plugins/).
Tests and runtime status must not be confused with full-fetch parity.

[Current runtime failures, measurements and test logs](data/isaac_fetch/README.md)
are authoritative for this implementation. The remainder is the historical
initial mobile-base milestone, whose absent-arm statements refer to its fixture.

## Historical initial Isaac foundation milestone

This branch starts at the clean P03D commit `8e518cf99b50347568d9e7c303ec80b18ef8c223`.
The Gazebo implementation and all files under `docs/data/p03d_autonomous_search/`
remain unchanged. The Isaac foundation code was ported from the committed
`p03-isaac-backend` work at `ffb3fc6` (original implementation `9197bf2`).
Uncommitted files in that separate worktree were not used or changed.

## Architecture and ownership

| Component | Current owner | Portability |
| --- | --- | --- |
| Dimensions, mass, wheel and sensor poses | `coco_config/robot.py` | Reuse unchanged |
| Full arm, gripper, collisions and Gazebo sensors | `gazebo_models/urdf/coco_robo2.xacro`, meshes | Gazebo specific; Isaac currently approximates arm mass |
| Four wheel geometry and contact | Xacro + `gz_ros2_control` in Gazebo; generated USD articulation in Isaac | Reuse geometry with simulator adapter |
| Differential drive command | `diff_drive_controller` in Gazebo; `DriveCommand` and four joint velocity targets in Isaac | Simulator specific, behind same final ROS command |
| Scan, RGB-D, IMU, clock | Gazebo sensors and `ros_gz_bridge`; Isaac PhysX LiDAR, RTX camera and bridge | Simulator specific |
| `odom → base_footprint` | Gazebo diff drive controller; Isaac measured pose publisher | Same ROS frames, different odometry source |
| Static robot TF and joint state | Gazebo robot state publisher/controllers; Isaac ROS publishers | Same navigation frames; Isaac publishes four wheel joints only |
| Localization and Nav2 | `gazebo_models/nav.launch.py`, `nav2_params.yaml` | Reuse unchanged, with run-local fixture map override |
| Perception and target pose | `coco_perception` | ROS nodes reusable; Isaac input topics present, detection not yet verified |
| Mission executive and P03D search | `coco_mission` | ROS logic reusable; Isaac target scene and grasp absent |
| Arm planning and grasp | MoveIt and Gazebo DetachableJoint magnet | Not yet portable |
| Command safety | `cmd_vel_relay` → `cmd_vel_arbiter` | Reuse unchanged; sole publisher of final wheel command |
| Gazebo spawn, bridge, controllers | `gazebo_models/full_world_robo.launch.py` | Gazebo specific |
| Isaac scene and ROS output | `coco_sim/coco_sim/isaac/`, `scripts/isaac_sim_coco.sh` | Isaac specific |

The Isaac scene is a small, deterministic navigation fixture generated from
`coco_config` measurements, with four driven wheels and collision geometry.
It is not the P03D ramp and target world. The chassis uses primitive geometry
and diagonal approximate inertia; the arm's mass is fixed at its mounting
location. The wheel joint names in Isaac differ from the Gazebo URDF names,
but the final velocity topic and navigation frames match. This is a mobile
base integration, not a complete manipulation twin.

## ROS compatibility contract

These names come from the Xacro, `bridge.yaml`, Nav2 parameters, perception
node, and arbiter, rather than a new interface. Isaac publishes:

| Topic | Type | Frame / consumer |
| --- | --- | --- |
| `/clock` | `rosgraph_msgs/Clock` | All nodes with `use_sim_time` |
| `/tf`, `/tf_static` | `tf2_msgs/TFMessage` | `odom → base_footprint → base_link`; sensor frames; AMCL owns `map → odom` |
| `/diff_drive_controller/odom` | `nav_msgs/Odometry` | Nav2; `odom`, child `base_footprint` |
| `/joint_states` | `sensor_msgs/JointState` | Four wheel joints |
| `/scan` | `sensor_msgs/LaserScan` | Nav2 costmaps and AMCL; `lidar_link` |
| `/camera/image_raw` | `sensor_msgs/Image` | RGB perception; optical frame |
| `/camera/depth/image_raw` | `sensor_msgs/Image` | Depth perception; optical frame, 32FC1 metres |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | RGB-D calibration |

The backend **subscribes only** to `/diff_drive_controller/cmd_vel`
(`geometry_msgs/TwistStamped`). The host `isaac_ros.py` supplies a plain
`/cmd_vel` smoke/teleop adapter to `/cmd_vel_teleop` and instantiates the
existing arbiter. For Nav2, the existing collision monitor and relay feed
`/cmd_vel_gated` into that arbiter. Only the arbiter publishes the final
controller topic. Do not launch a second arbiter, Gazebo controller, robot
state publisher, or clock source on the Isaac ROS domain. The Isaac backend
rejects stale commands after 0.5 simulated seconds and applies the existing
velocity and acceleration limits before setting joint velocity targets.

Gazebo also publishes `/imu`, `/camera/points`, `/model/coco/odometry`, arm and
gripper states, and `/magnet/<target>/{attach,detach,state}`. Isaac does not
yet satisfy those mission/manipulation interfaces. Its `/scan` is 360°/480
beams rather than Gazebo's 240° front arc. Isaac odometry is simulator ground
truth in an odom frame; Gazebo navigation uses wheel odometry. These are
material differences for cross-simulator comparisons.

## Setup and reproduction

Verified host: Ubuntu 24.04, ROS 2 Jazzy, Isaac Sim **4.5.0.0** pip install
at `~/isaac-sim/venv`, NVIDIA RTX 4050 Laptop GPU with 6141 MiB VRAM and
driver 580.173.02. Isaac's process uses the bridge's bundled Humble libraries
and Python 3.10; host ROS stays Jazzy/Python 3.12. Both use CycloneDDS on a
private loopback domain. The launcher isolates the Isaac environment rather
than sourcing Jazzy into it. The small scene ran on this host; full Isaac
workloads are not implied to fit its GPU/RAM.

```bash
cd /home/gautham/coco-isaac-21
bash scripts/build_overlay.sh /home/gautham/coco_isaac21_ws --packages-up-to coco_sim gazebo_models custom_teleop coco_mission coco_perception
export COCO_WS=/home/gautham/coco_isaac21_ws
source setup_env.sh
python3 scripts/isaac_smoke.py /tmp/coco-isaac21-smoke-new --domain 81
python3 scripts/isaac_smoke.py /tmp/coco-isaac21-nav-new --domain 81 --nav --raw-evidence /tmp/coco-isaac21-smoke-new/result.json
```

Each output path must be new. The harness owns and stops only its child
process groups, records the ROS graph and observations, and checks all exit
codes. `--gui --rviz` is optional and consumes more graphics memory. For
manual use, start `scripts/isaac_sim_coco.sh --output NEW_DIRECTORY` in one
terminal, `python3 scripts/isaac_ros.py --ros-args -p use_sim_time:=true`
in another, then use the existing Nav2 launch with `arbiter:=true` and the
fixture map from `scripts/isaac_fixture_map.py`. The harness also writes a
run-local Nav2 parameter copy with the fixture map filename, needed by the
noncomposed Nav2 launch on this installation.

Required environment: `COCO_WS` selects the isolated Jazzy overlay;
`ROS_DOMAIN_ID` selects a private domain for manual runs. The wrapper fixes
`ROS_DISTRO=humble`, `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` and bridge
library paths **inside Isaac only**. No external account or container is
required. The wrapper expects Isaac at `~/isaac-sim/venv`.

## Validation and limits

The new backend's pure configuration/model tests, shared robot-constant
guards and command wiring tests run in the isolated overlay. The focused
port and wiring check passed **73 tests** (six live-graph tests deselected
because they require a separately started graph). The P03D/autonomy and
related static regression selection passed **404 tests**, with nine style
checks deselected. The nine package suites, run separately to avoid duplicate
pytest module names, passed **1,887 tests**, with **7 skipped** MoveIt
tests and **6 deselected** live-graph tests. Final `flake8 --select=E,F`
on the new Python files passed. Live evidence and numerical results for this branch are
under [`docs/data/isaac_21/`](data/isaac_21/README.md).

Two live raw runs passed 19/19 checks each; the final run delivered
RGB/depth/scan/odom at 15.000/15.000/10.000/30.000 Hz in simulation time.
A 0.5 m/s command over 8.0 simulation seconds produced 3.865 m x
displacement. Command dropout stopped the base. Isaac and all owned ROS
peers exited zero. Two Nav2 runs used the existing launch, planner,
collision monitor, relay and arbiter, and completed the same map-frame
`(1.5, 0.5)` goal with action status SUCCEEDED. Their final map position
errors were 0.140 and 0.095 m, with 1.705 and 1.718 m odom displacement
from action start to finish. The arbiter was the sole publisher to
`/diff_drive_controller/cmd_vel`; all Nav2 and Isaac processes exited zero.
These are two measured executions of one simple goal, not a broad
repeatability estimate.

For an initial cross-simulator frame of reference, historical Gazebo
measurement in `docs/RESULTS.md` has scan/RGB/odom at 10.0/15.2/50.0 Hz
in simulation time, while this Isaac fixture measured 10.0/15.0/30.0 Hz.
The Gazebo Nav2 tour and these Isaac goals use different worlds, maps,
sensor fields of view and odometry sources. Therefore goal success and
position error are reported separately, without claiming parity.
The earlier `p03-isaac-backend` branch also contains raw development runs,
including failures; its two composed Nav2 goals succeeded behaviorally but
the Nav2 container crashed on shutdown, and a later noncomposed goal
aborted. Those runs are provenance, not a pass attributed to this branch.

Next required engineering work is a full articulated arm/gripper model and
magnet/grasp interface, perception execution against Isaac targets, realistic
odometry, then a P03D search in a corresponding world. The fixture's
navigation metrics cannot be compared one-to-one with the Gazebo ramp arena.
