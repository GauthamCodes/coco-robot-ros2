# C2-NAV.35 exact AMCL input capture

Instrumentation only. This directory prepares a checksum-pinned Nav2 **1.3.11**
AMCL overlay against installed Jazzy dependencies. It does not replace the
system installation, edit robot configuration, or launch anything. The hypothesis
that odometry explains the wall bias remains **UNKNOWN**.

## Prepare and build offline

From the Codex worktree root (one-time preparation; destination must be new):

```bash
mkdir -p .navbench/c2nav35
curl -fL --max-time 180 https://codeload.github.com/ros-navigation/navigation2/tar.gz/refs/tags/1.3.11 -o .navbench/c2nav35/navigation2-1.3.11.tar.gz
python3 -P diagnostics/c2nav35/prepare.py .navbench/c2nav35/navigation2-1.3.11.tar.gz .navbench/c2nav35/prepared
source /opt/ros/jazzy/setup.bash
cmake -S .navbench/c2nav35/prepared/src/nav2_amcl -B .navbench/c2nav35/build-enabled -DCMAKE_INSTALL_PREFIX="$PWD/.navbench/c2nav35/install-enabled" -DC2NAV35_CAPTURE=ON -DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_CXX_FLAGS='-Wall -Wextra -Wpedantic -Werror'
cmake --build .navbench/c2nav35/build-enabled -j2
cmake --install .navbench/c2nav35/build-enabled
cmake -S .navbench/c2nav35/prepared/src/nav2_amcl -B .navbench/c2nav35/build-disabled -DC2NAV35_CAPTURE=OFF -DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_CXX_FLAGS='-Wall -Wextra -Wpedantic -Werror'
cmake --build .navbench/c2nav35/build-disabled -j2
python3 -P diagnostics/c2nav35/test_capture.py
```

The archive SHA-256 is
`05782fd66698ea51de6a62d2483da34b85c1149ef93ba7c1b67507005a4d0170`.
The preparer refuses another archive or a reused destination. It extracts only
regular files from `nav2_amcl`, leaves licenses intact, and checks every patch
site occurs exactly once. It emits a baseline/patched file hash manifest and an
instrumentation fingerprint embedded in the capture library. Retain this manifest
with the enabled build's library hashes and future runtime parameter readback.

The only upstream execution files modified are `src/amcl_node.cpp` and
`src/motion_model/differential_motion_model.cpp`; CMake adds the optional sink.
Public AMCL class layout and motion-model interfaces are unchanged. The patch is
expressed as exact-site transformations in `prepare.py`, not an approximate AMCL
implementation. The source tag matches the installed package version; binary
equivalence to every Debian build choice is not assumed.

## Capture boundaries and enablement

Compile option `C2NAV35_CAPTURE` defaults **OFF**. Off removes all hooks, does not
build/link the sink, and leaves the production execution sources equivalent to
upstream after preprocessing. Tests verify that and absence of sink symbols.

An enabled build still produces no diagnostic output or writer thread unless
`C2NAV35_TRACE` specifies a new output file. Sink initialization happens in AMCL
configuration, before scan processing. Creation is exclusive: existing files are
never overwritten. Use **one AMCL instance per process**, with a unique output
file; the sink is process-local and scan state belongs to its callback thread.
Changing/restarting callback threads mid-capture is unsupported and duplicate
identities are rejected. These settings are diagnostic opt-ins, not AMCL ROS
parameters. No launch file activates them automatically.

`getOdomPose` captures the actual successful identity-pose transform returned by
the existing buffer call. It copies the exact planar pose AMCL extracts and
records failure on the existing exception path. It does not request another TF.
The query is target `odom`, source `base_footprint`, at the scan header time,
with zero local lookup timeout; MessageFilter's earlier wait is separate.

The scan callback records the actual `pf_odom_pose_` anchor and `pose/delta`
arguments immediately before the existing `odometryUpdate` call. The differential
model copies its existing `delta_rot1`, `delta_trans`, `delta_rot2` locals before
sampling. No production arithmetic or RNG call is replaced. Initialization,
threshold eligibility, prediction begin/end, sensor outcome, anchor advancement
and callback end are separate events. In particular, prediction can occur before
a sensor failure without advancing the anchor.

Recording uses a fixed 4096-record queue with a try-lock; contention or capacity
overflow drops diagnostic records and increments a footer counter. Serialization,
flush and I/O happen on a worker. No filter callback waits for the writer or GT.
Enabled recording nevertheless has scheduling/cache overhead. Offline equal
outputs do **not** establish live timing neutrality. A crash or forced kill may
lose the footer and is classified as incomplete capture.

## Schema and missing values

AMCL JSONL schema 1 has a manifest, events and a footer. All scan/TF/anchor times
are integer nanoseconds; `receipt_ns` is the extra ROS-clock observation at callback
entry, not the scan time. File identity plus `scan_id` and `prediction_id` identify
events. `epoch` advances on a backward callback receipt clock. Preserve files per
run; do not concatenate unrelated processes.

| Fields | Meaning |
| --- | --- |
| `stage`, `scan_id`, `prediction_id`, `epoch` | Scan/processing identity; prediction ID zero means no prediction assigned yet |
| `scan_ns`, `scan_frame`, `source`, `target` | Original scan stamp/frame and the actual normalized lookup frames |
| `tf_ok`, `tf_ns`, `tf`, `pose` | Lookup result; full `[x,y,z,qx,qy,qz,qw]`, and consumed planar `[x,y,yaw]` |
| `anchor_id`, `anchor_ns`, `anchor` | Prior anchor scan/time and actual planar anchor; full anchor transform is that scan's `tf_success` event |
| `delta`, `motion` | Actual `[dx,dy,dyaw]` argument in odom axes; exact pre-noise `[rot1,trans,rot2]` locals |
| `eligible`, `forced`, `scanner` | Threshold-only OR result before force flag, original force flag, scanner index |
| `sample_count`, `current_set` | Particle set identity/count immediately before prediction |
| `truncated`, footer `dropped` / `write_failed` | Frame truncation and capture integrity; any such loss invalidates a complete-input verdict |

`tf_ok` and flags use `-1` for not reached/unavailable, 0 for false and 1 for true.
Unavailable numeric arrays contain JSON nulls. Missing TF/anchor stamps are null;
zero acquisition time remains a valid time when the corresponding result exists.
`motion` is populated only once the actual differential model reaches its
decomposition. `anchor_set` identifies advancement to the current event's pose;
its anchor fields retain the **previous** anchor. An initialization anchor has
no prior planar anchor. No event-specific value is forward-filled into later scans.

The installed Jazzy MessageFilter does **not** expose `registerFailureCallback`.
Pre-callback filter drops therefore have no counter here. This is an explicit
limitation, not a zero count. Callbacks that return before the odometry query
have `tf_ok=-1` and no prediction. The stream proves inputs for actual recorded
prediction calls, not delivery of every emitted lidar scan. Per-particle random
increments, weights, sensor contributions and resampling ancestry are not captured.

## GT and offline comparison

`nav_bench.py --odom-gt-jsonl NEW_FILE` enables an acquisition-stamped sidecar
through its existing GT subscription. With the flag absent the helper is not
loaded and no sidecar is created. Legacy `self.gt`, callback receipt clocks,
10 Hz trace columns, bucket selection and output are unchanged. The extra writer
has a bounded queue; its manifest/footer and loss rules match the AMCL stream.
No `/model/coco/odometry` value is used as AMCL input.

GT records retain header/child frame, full pose, integer acquisition stamp,
original `receipt_sim`/`receipt_wall`, sequence and clock epoch. The offline join
requires an explicitly verified model-to-base rigid transform and its evidence
reference. Do not assume the child-frame label proves model-origin equivalence.
For example, after proving an identity extrinsic (not merely assuming one):

```bash
python3 -P diagnostics/c2nav35/join.py AMCL.jsonl GT.jsonl JOINED.json --gt-to-base 0 0 0 0 0 0 1 --extrinsic-evidence VERIFIED_REFERENCE
```

The join preserves every prediction, reports unobservable pairs, and retains
actual arguments/decomposition with GT at both scan and anchor times. GT is
interpolated with linear translation/quaternion shortest-path interpolation;
brackets wider than 50 ms by default, extrapolation, unknown anchors, epoch/frame
changes and incomplete predictions are rejected. Gap limits bound sample spacing,
not physical interpolation error. Returned TF stamps that differ from scan stamps
(including zero-time/latest queries) are not paired as scan-time GT. The
timestamp uncertainty and model-origin evidence
must still support the desired millimeter-scale conclusion. Longitudinal, lateral
and yaw residuals are relative base motions; the historical map translation is not
refitted. Overlapping anchor intervals after failures are retained, not summed as
disjoint travel.

Both streams must cover initialization/anchor time and the complete approach.
Start GT acquisition before AMCL's first relevant anchor; otherwise the first
affected interval is unobservable. Missing data, footer loss or writer failure
cannot count as evidence that odometry is clean.

## Next live action (not executed)

After separate approval: one baseline `open_space -> wall_adjacent` traversal,
with this isolated overlay selected, a unique `C2NAV35_TRACE` path and GT sidecar
active before the initial relevant anchor. Retain source/build hashes, actual
loaded paths, unchanged parameter readback and verified GT/base extrinsics.
Compare exact prediction inputs against synchronized GT. Do not tune anything,
change resampling, or claim the odometry hypothesis is proven by this instrument.

## Implementation sprint: strict completion and reproducible runs

New captures require footer `attempted`, `successful`, `dropped`, `malformed`,
`write_failed` and `completion`. Successful counts exclude malformed or dropped
records. Only nonempty, lossless captures with exact body/count agreement and
`completion: complete` are accepted. Earlier schema-1 files without these counters
are intentionally rejected; they cannot prove capture completeness.

The join rejects repeated event identities before building lookup dictionaries,
backward acquisition/receipt time, nonzero clock epochs, changed frames, and
missing or inconsistent current/anchor TF. Motion and end events must match the
prediction identity, timestamps, frames and arguments. It never sorts away a
clock reversal. The existing 50 ms GT bracket limit remains enforced.

Build the zero-noise oracle against the installed motion library:

```bash
python3 -P diagnostics/c2nav35/build_oracle.py .navbench/sprint/motion_oracle
C2NAV35_BUILD_ROOT=.navbench/sprint python3 -P diagnostics/c2nav35/test_capture.py
```

`C2NAV35_BUILD_ROOT` selects a fresh `prepared`, `build-enabled`, `build-disabled`
set built with the preparation commands above. The checksum-pinned archive remains
at `.navbench/c2nav35/navigation2-1.3.11.tar.gz`. The oracle builder retains source,
executable, shared-library hashes and installed package version in a manifest.
Use `--motion-oracle .navbench/sprint/motion_oracle --gt-model-frame FRAME` in
addition to the join arguments above. `FRAME` must be the actual GT child frame,
and the extrinsic must map it to `--base-frame` (default `base_footprint`).
Do not substitute an unverified identity transform. CLI joins use installed AMCL
with zero noise for predicted motion; no replacement motion equations are used.
The body residual is named longitudinal/lateral/yaw; `world_residual` rotates its
translation by the GT anchor heading. This is a deterministic motion-input
residual, not an attribution of stochastic filter or laser correction error.

After building/installing `gazebo_models`, a bounded fresh tour can be run with:

```bash
python3 -P gazebo_models/scripts/run_experiment.py \
  --run-id trial --params "$PWD/gazebo_models/config/nav2_params.yaml" \
  --result "$PWD/.navbench/sprint/trial.json" \
  --output "$PWD/.navbench/sprint/trial-run.json" --timeout 260 -- \
  ros2 launch gazebo_models benchmark.launch.py run_id:=trial \
  out:="$PWD/.navbench/sprint" \
  params_file:="$PWD/gazebo_models/config/nav2_params.yaml"
```

Run on a clean graph with one simulator. The wrapper owns and terminates only its
child process group. It reserves a new output file, records Git SHA/dirty state,
tracked-diff hash, parameter path/hash, exact command and UTC/wall duration. It
records failures even when no benchmark JSON appears. `--baseline` accepts a
previous nav_bench JSON; `--diagnostic-result` accepts a strict join result.
Missing telemetry stays null. Navigation completion and process success are
separate fields. Safety-stop episodes are separate from physical low-speed stops.
`gt_capture:=NEW_PATH` enables the GT sidecar in the launch; it defaults off.

The benchmark waits up to 60 wall seconds for `/bt_navigator/get_state` to report
active before goals. Action discovery alone does not prove lifecycle readiness.
The world path is shell-quoted for Gazebo so checkout names with spaces or
parentheses work. No safety threshold, polygon, goal or critic was weakened.
