# COCO 2.1 Isaac run evidence — 2026-10-02

Source branch: `coco-2.1-isaac-integration`, starting from P03D
`8e518cf99b50347568d9e7c303ec80b18ef8c223`. Backend source was
ported from committed `p03-isaac-backend@ffb3fc6`; these are **new live
runs from this branch**, not results copied from that branch.

All four runs used Isaac Sim 4.5.0.0 at `~/isaac-sim/venv`, ROS 2 Jazzy in
an isolated overlay, CycloneDDS on loopback domain 81, and the same
RTX 4050 Laptop GPU (6141 MiB VRAM). Commands are in
[`docs/COCO_2_1_ISAAC.md`](../../COCO_2_1_ISAAC.md). The full run
directories retain harness result JSON, process exits, exact launch and
Nav2 logs, observer log, resource sample, GPU time series, scene/episode
manifest, generated robot URDF and fixture map/parameters.

| Measure | `smoke_001` | `nav_001` | `smoke_002` | `nav_002` |
| --- | ---: | ---: | ---: | ---: |
| Harness result | PASS | PASS | PASS | PASS |
| Isaac exit | 0 | 0 | 0 | 0 |
| ROS peer exit | 0 | 0 | 0 | 0 |
| Nav2 exit | — | 0 | — | 0 |
| Observer exit | 0 | 0 | 0 | 0 |
| Peak Isaac process RSS | 4,951,652 kB | 4,979,428 kB | 4,970,252 kB | 4,977,416 kB |
| Peak sampled total GPU memory used | 2,177 MiB | 2,466 MiB | 2,341 MiB | 2,339 MiB |

`smoke_001/result.json` and `smoke_002/result.json` each record 19/19
checks true, including ground
contact, four-wheel motion, command timeout stop, all scan bearing checks,
depth geometry, camera calibration, TF, timestamps and one final wheel
publisher. A 0.5 m/s forward command over 8.0 simulation seconds moved
the odom x coordinate from −0.001 to 3.864 m. Measured simulated-time
rates: RGB **15.000 Hz**, depth **14.944 Hz**, scan **10.000 Hz**, odom
**30.000 Hz**. The initial forward scan range to the known east wall was
**7.041 m** in run 001. Run 002 measured RGB/depth/scan/odom at
15.000/15.000/10.000/30.000 Hz and 3.865 m forward x displacement.
The selected camera pixels/depth and scan bearing geometry
were checked against the fixture, not against Gazebo. Isaac bridge logs
contain CycloneDDS `rcutils`/type-hash warnings; delivery and acceptance
checks still passed. These warnings are retained in the raw logs.

Both navigation results record lifecycle activation of the BT navigator,
controller, planner and collision monitor. The unchanged Nav2 stack was
given a map-frame `(1.5, 0.5, yaw 0)` goal. `NavigateToPose` returned
**SUCCEEDED** (status 4, error code 0). Run 001 ended **0.1402 m** from
the map goal with **1.7048 m** action-start odom displacement; run 002
ended **0.0945 m** away with **1.7181 m** displacement. Their sampled
odom traces covered **3.161 m** and **2.642 m** respectively, over
57.8 s and 39.0 s simulation spans; those spans include readiness/startup samples
and is **not** action execution time. Every command-chain topic had
nonzero samples. ROS graph inspection found only `cmd_vel_arbiter` as
publisher to `/diff_drive_controller/cmd_vel`. All harness-owned child
processes shut down with exit 0 in both runs. These are two executions of
one goal in a small fixture; they do not establish broad repeatability or
P03D mission parity. Run 001 preceded formatting-only changes and a
source-string test repair; run 002 used the final code.

For context, the older Gazebo [`RESULTS.md`](../../RESULTS.md) measured
scan 10.0, RGB 15.2 and wheel odom 50.0 Hz in simulation time, and a
10/10 goal tour in a materially different world. The shared topics and
Nav2 launch are the useful comparison. The goal count, trajectory length,
time, position error, depth and contact response are **not paired
Gazebo–Isaac measurements** because the environments, map, sensor FOV and
odometry sources differ. This is the first comparison baseline, not a
claim of physical equivalence.

The P03D 29-attempt Gazebo inventory and adversarial search proof remain
under `docs/data/p03d_autonomous_search/` unchanged. No Isaac target
search or grasp was attempted: this backend has no articulated arm,
targets, or magnet interface yet.

`tests/` retains the isolated overlay build log, the 404-test regression,
the nine per-package results (**1,887 passed, 7 skipped, 6 live tests
deselected**), the final focused 27-test result, and the empty successful
E/F lint output. The combined pytest collection failed because ROS's
`launch_testing` hook imported same-named style modules from different
packages; running each package separately resolved it. The first lint pass
also found formatting and unused-binding issues in the port; those are
retained in `initial_lint_failure.log` and fixed in the final code.
