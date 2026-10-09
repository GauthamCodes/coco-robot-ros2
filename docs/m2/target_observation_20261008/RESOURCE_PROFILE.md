# RGB-D engineering composition and measured resources — 2026-10-09

All data here are NON_QUALIFYING. No full-stack production envelope is established.
`--profile rgbd_capture` contains Gazebo server, existing RGB-D sensor, four-topic
bridge, static robot TF, recorder and owned launch/probe children.
`--profile rgbd_observation` additionally starts the actual observer.
Nav2, MoveIt, mission, actuator plugins and unrelated perception are absent.
Only unused LiDAR/IMU execution is removed from the generated engineering fixture;
robot visual/collision geometry and backend target SDF remain unchanged.
Static zero-joint fixtures cannot validate physical manipulation.

The existing emergency policy is unchanged: available RAM >=8,229,273,600 bytes,
free VRAM >=2,146,435,072 bytes, load1 <=12, plus disk/domain/process checks.
These are emergency reserves, not production qualification thresholds. A 1 Hz
watchdog stops only owned PID/start-time identities and preserves evidence;
it cannot guarantee a kernel allocation quota between samples.

| Component | Capture02 peak RSS bytes | Live observer04 peak RSS bytes |
|---|---:|---:|
| Gazebo including sensor plugins | 841072640 | 836661248 |
| Recorder | 91594752 | 83025920 |
| Bridge/middleware | 43323392 | 43368448 |
| Robot TF | 20586496 | 20787200 |
| Observer | absent | 182628352 |
| Launch/probe overhead | 68489216 | 81502208 |

RSS can double-count shared pages; maxima need not occur simultaneously. CPU
peaks per component are saved in `validation/lightweight_20261009/component_peaks.json`
in percent of one logical CPU, distinct from host CPU percent. Recorder peaks
~1.7–1.8 cores; Gazebo ~0.84–0.94 core. Sensor plugins share Gazebo and cannot be
individually attributed from these process samples. GPU values are host-wide,
not component allocations. Nav2/MoveIt/mission consume no resources in this
profile; their contribution to the old full-run abort cannot be inferred.

Capture02 completed30 s, host CPU peak39.77%, load2.659, available RAM minimum
8,638,615,552 bytes, host VRAM used maximum1,030,750,208 bytes. Receipt-delta RTF
range0.727–1.296 includes startup sampling noise; settled clock progression is
approximately real time. This is sensor-only data, not calibration evidence.

Live observer04 aborted near6 s: RAM8,106,254,336 bytes, below reserve;
load2.274 at abort. Removing unnecessary SciPy imports reduced observer RSS
from204,357,632 to182,628,352 bytes, without changing thresholds/geometry.
Flank capture06 without observer aborted near7.15 s: RAM8,228,495,360 bytes,
778,240 bytes below reserve; load2.067, CPU30.50%. Its RTF is unmeasured.
All executed fixture teardowns report zero surviving owned processes. No foreign
process was terminated. Capture05 was blocked before launch by transient
unreadable metadata; those processes exited before fresh capture06 preflight.

The full bootstrap's historical CPU99.92%, load14.55 and RAM8.01GB abort is
preserved, but lacked this component attribution. No claim that a particular
Nav2/MoveIt node caused it. Current lightweight aborts identify RAM headroom as
the immediate cause, rather than CPU/load. Safe continuation needs a quieter host
with enough additional available RAM for simulator/observer/recorder startup
while retaining the existing reserve. No reserve increase/decrease was made.

## Phase engineering profile resource continuation

All values are bytes unless noted. No production envelope or machine requirement
is inferred. Full-stack execution has not been attempted without a successful
controlled lift/release. The unchanged RAM reserve is8,229,273,600 bytes.

| Component | Observer acquisition-01 peak RSS | Front-flank observer peak RSS | Minimal arm-06 peak RSS | Arm minus front-flank | Full stack |
|---|---:|---:|---:|---:|---|
| gazebo_including_sensor_plugins | 868466688 | 868700160 | 890712064 | 22011904 | NOT MEASURED |
| launch_or_runtime_overhead | 155582464 | 154939392 | 708440064 | 553500672 | NOT MEASURED |
| moveit_manipulation | 0 | 0 | 219598848 | 219598848 | NOT MEASURED |
| observer | 252649472 | 253603840 | 258150400 | 4546560 | NOT MEASURED |
| recorder | 145178624 | 89948160 | 104280064 | 14331904 | NOT MEASURED |
| robot_tf | 20971520 | 21106688 | 23642112 | 2535424 | NOT MEASURED |
| ros_bridge_middleware | 43724800 | 43634688 | 47538176 | 3903488 | NOT MEASURED |

Peaks are sampled per-component sums; maxima can occur at different times and RSS
double-counts shared pages. Partial arm accounting groups controller spawners with
MoveIt/overhead by argv signatures; target_finder/arbiter/phase driver are included
in overhead. Plugins share Gazebo RSS. Background host activity differs between
runs, so these deltas are descriptive, not isolated causal allocation measurements.
Sensor-only baseline capture02 from the prior checkpoint remains above for context;
there is no fresh same-condition observer-free paired run in this continuation.

Acquisition-01 minimum available RAM8,672,575,488; front-flank observer
8,595,410,944; minimal arm-06 minimum8,400,928,768. The latter stays171,655,168
bytes above reserve at sampled points, but aborts for unknown process metadata.
Arm-06 host CPU peak96.699375558%, load peak9.351074219, used RAM peak
8,057,618,432, VRAM peak1,034,944,512. Recorded receipt-delta RTF0.254359006–
0.982938802 is partial startup/control context, **not a validated steady-state
RTF mean**: recorder clock callbacks show lag and there is no completed workload.
Exact samples/extrema/component peaks are in validation/phase_20261009/ and hashed
external host_metrics.jsonl files. No full-stack/Isaac resource claim is made.

Optimizations preserve full raw image CDR in MCAP: bounded RGB/depth caches,
consumed-frame removal, no preliminary float64 depth copy, depth-one engineering
image/observation recording queues, and image metadata/byte hashes instead of
duplicate JSON pixel arrays. Optional annotated-image publication is disabled
only in the engineering target_finder; raw RGB/depth/CameraInfo remain recorded.
Observer sensor subscriptions now explicitly use BEST_EFFORT depth1 rather than
the default sensor profile depth5; source pairing/freshness/rejection gates stay
unchanged. Last queue/phase refinements await runtime under an inspectable host.
No recording disabled, pixel fidelity reduced, required topic removed, sensor
added, task body changed or reserve/production policy lowered.

### Reusable compositions

`rgbd_capture`: Gazebo server (physics, commands, scene, RGB-D rendering systems),
four-topic bridge(/clock,RGB,depth,CameraInfo), robot_state_publisher, recorder,
owned launch/probe. `rgbd_observation` adds object_height_node. Static fixtures
remove actuator plugins and unused LiDAR/IMU execution only; no manipulation claim.
Sensor inputs BEST_EFFORT depth1; height output RELIABLE/VOLATILE depth10 JSON.

`rgbd_manipulation`: existing ros2_control and target_red DetachableJoint plugins;
RGB-D+IMU; joint_state_broadcaster, diff_drive_controller, arm_controller,
gripper_controller; robot_state_publisher, bridge, observer, target_finder,
existing idle-default arbiter, existing approach_server, MoveIt, grasp_server,
sensor-only phase_control, recorder. /joint_states and encoder /odom feed the
existing pose guard; /imu feeds its unchanged attitude guard. Every wheel command
uses the unchanged arbiter. No Nav2/search/localization/mission/web stack. Normal
magnet_release initializes detach; actual attach/place use existing guarded
services. Phase control publishes standard mission mode and calls standard
services; its inputs are legitimate height/status/controller-state messages.

Raw sensor MCAP sampling is1Hz at full source resolution/encoding. Other existing
fixed trace topics retain their capture contract. Engineering image sidecars store
source header, dimensions, encoding, byte count/hash and MCAP payload location.
Magnet recorder uses live VOLATILE QoS; consumer QoS is unchanged. TF static is
TRANSIENT_LOCAL. No /eval/world/model subscriptions are added to autonomy.

All children are new-session owned roots/verified descendants tracked by PID/start
identity in bootstrap manifests. Driver completion shuts down its fixture launch;
bootstrap stops recorder last and checks survivors. Every finalized executed
attempt has zero owned survivors. All profiles are NON_QUALIFYING, denominator
false; a static fixture never establishes lift/release or a production limit.
