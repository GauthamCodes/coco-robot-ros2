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
