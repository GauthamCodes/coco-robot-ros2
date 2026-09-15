# COCO implementation sprint — 2026-09-16

Implementation, build, tests and controlled simulation were executed in the
specified Codex worktree. Main and the diagnosis worktree were not modified;
`docs/RSE_ASSIGNMENT_PLAN_V2.md` was not touched. No merge or push was performed.
The stale local `.git` pointer was repaired to a relative path inside this
worktree; administrative metadata in the protected main checkout was not repaired.

## Delivered

- Counted AMCL/GT footers: attempted, successful, dropped, malformed, write failure
  and explicit completion. Empty, truncated, lossy and inconsistent captures fail.
- Strict correlation requires current and anchor successful TF, matching full
  transforms/consumed poses, timestamps, prediction stages and frame identities.
  Duplicate identities, clock reversals/nonzero epochs, changed frames and GT
  brackets over the default 50 ms are rejected. No sorting hides time reversals.
- CLI requires explicit model/base correspondence and evidence. Installed-library
  zero-noise oracle supplies motion prediction; named longitudinal/lateral/yaw and
  world-frame residuals are emitted. Oracle/source/library hashes are retained.
- Diagnostic hooks remain compile-time OFF by default. Cleanup joins AMCL's scan
  executor before draining the recorder. This avoids relying on static destruction
  inside a component container. One configured lifecycle per capture is supported.
- Bounded foreground experiment wrapper and launch: run ID, Git/config provenance,
  environment, timestamps, return code, navigation outcome, safety/clearance/error
  metrics, physical stalls, diagnostic integrity and optional baseline comparison.
  Failed tours have an observed duration and a null completion time.
- Lifecycle readiness gate prevents sending goals to an inactive navigator.
  Gazebo world paths are quoted for checkout names with parentheses or spaces.
- Applied only the accepted behavior changes: LOCAL costmap scaling 65 and the
  NavigateThroughPoses replanning/recovery BT. Safety polygons, critic scales,
  tolerances and committed tour goals were not weakened or moved.

## Build and tests (measured)

- Isolated colcon build: `coco_config`, `coco_sim`, `custom_teleop`, `gazebo_models`
  all built; `gazebo_models` rebuilt after the launch/tool changes.
- Enabled and disabled AMCL builds passed with `-Wall -Wextra -Wpedantic -Werror`.
  Enabled overlay rebuilt after the cleanup hook and installed into a local prefix.
  Preprocessor comparison proves disabled source remains upstream-equivalent;
  disabled library has no diagnostic symbols.
- Focused diagnostic/oracle suite: **20/20 passed**.
  Installed/enabled/disabled particles, weights and RNG progression match in the
  deterministic probe. Regression coverage includes the requested failure cases
  plus full-transform and prediction-event mismatch.
- Full `gazebo_models` pytest suite: **43 passed**. Colcon reported **44 test
  entries, zero errors/failures/skips** (includes the CTest wrapper entry).
- Upstream AMCL CTest suite: **4/4 passed** (cppcheck, CMake lint, uncrustify,
  XML lint). Initial formatting failures in generated instrumentation were fixed.
- An intermediate oracle test captured queue contention while simulation was
  running and correctly failed integrity validation. The final suite ran on a
  clean graph. This is not evidence of loss-free live recording.

## Simulation comparison (measured)

Same accepted parameter file/hash, default world, committed
`open_space -> wall_adjacent` goals, one fresh simulator per tour, 75 wall seconds
per leg. Historical .37/.38 artifacts were unavailable and the human withdrew
that lookup; r3 is a contemporaneous control, not a claimed reproduction of those
historical runs. The experiments are observations, not statistical success rates.

| Metric | r3: diagnostics off | r4: diagnostics on | r5: cleanup fix, diagnostics on |
|---|---:|---:|---:|
| Successful legs | 2/2 | 1/2 | 2/2 |
| Completed-tour simulated seconds | 33.02 | not completed | 55.00 |
| Observed leg duration sum, simulated seconds | 33.02 | 82.42 | 55.00 |
| Minimum benchmark clearance, m | 0.421 | 0.318 | 0.383 |
| Observed safety-stop episodes | 0 | 0 | 0 |
| Physical low-speed stops | 5 | 8 | 7 |
| Terminal error, open/wall, m | 0.086 / 0.112 | 0.130 / 0.058 | 0.101 / 0.063 |
| Wall-leg actual speed below 0.05 m/s | 0.776 | 0.932 | 0.905 |
| Wall-leg DWB zero-forward fraction | 0.590 | 0.548 | 0.691 |

Clearance retains the existing benchmark's robot-center-to-occupied-map-cell
semantics; it is not a certified footprint clearance. Low terminal XY error does
not imply goal success: r4's wall leg timed out. Zero observed safety stops does
not establish safety in untested situations. No safety threshold was relaxed.

Two startup failures are retained: r1 failed on Gazebo's unquoted world path;
r2 started the simulator but both goals were rejected before Nav2 activation.
The source fixes were then validated by actual navigation in r3–r5.

All three navigation runs returned a nonzero launch exit during teardown.
The component container required forced termination or crashed, and launch
reported `Cannot shutdown a ROS adapter that is not running`. The wrapper keeps
process failure separate from navigation completion and kills its owned group.
Final process inspection found no surviving Gazebo, component container or bridge.

## Diagnostic integrity and remaining blockers

- r3 and r4 GT captures had complete footers with no reported loss.
- r4 AMCL lacked a footer and is rejected as incomplete.
- r5 proves the lifecycle cleanup footer fix: **2698 attempted, 2697 successful,
  1 dropped, 0 malformed, no write failure, completion incomplete**. The strict
  loader rejects it. A footer's existence alone does not make a capture valid.
- Therefore **no valid live AMCL/GT motion decomposition is claimed**. No
  unverified GT/model-to-base extrinsic was inserted to manufacture a result.
- Enabled runs showed longer completion/stall behavior and one timeout relative
  to the single control. Timing neutrality and absence of navigation regression
  are **not established**. Keep capture disabled in normal navigation.
- Container/launch teardown remains unreliable even though the recorder now
  flushes during AMCL cleanup. The unavailable historical load/unload fix was not
  copied or reconstructed speculatively.

## Reproduction and retained evidence

[Machine-readable comparison](../data/implementation_sprint/comparison.json)
contains per-run metrics, capture manifests/footers and SHA-256 hashes of retained
artifacts. Its sibling `.gz` files contain original run reports/logs, navigation
results/traces, GT/AMCL streams and verification logs. `gzip -dc FILE.gz > NEW_FILE`
restores the exact original bytes; compare against `uncompressed_sha256`.

Build and run commands are in [the diagnostic README](../../diagnostics/c2nav35/README.md).
The scratch builds and original evidence remain under `.navbench/sprint/`.
A failed/incomplete strict load is the expected result for the archived AMCL
captures; do not remove its checks to obtain an `OK` verdict.

## Recommended integration order

1. `132942a`: accepted configuration defaults, independently reviewable.
2. `e7fee9d`, then `1c56dcd`: recorder integrity, validation and installed oracle.
3. `98e3ebb`: experiment tooling, startup readiness and world-path quoting.
4. `9fcabef`, then `d5bc11a`: lifecycle close/full-transform validation and metrics.
5. This report, final regression test and evidence archive commit.

Keep instrumentation disabled for ordinary navigation. Integration should not
be described as proving loss-free capture, timing neutrality or reliable teardown.

## Changed implementation files

- `diagnostics/c2nav35/README.md`
- `diagnostics/c2nav35/build_oracle.py`
- `diagnostics/c2nav35/capture.cpp`
- `diagnostics/c2nav35/capture.hpp`
- `diagnostics/c2nav35/join.py`
- `diagnostics/c2nav35/motion_oracle.cpp`
- `diagnostics/c2nav35/prepare.py`
- `diagnostics/c2nav35/test_capture.py`
- `gazebo_models/CMakeLists.txt`
- `gazebo_models/config/nav2_params.yaml`
- `gazebo_models/launch/benchmark.launch.py`
- `gazebo_models/launch/full_world_robo.launch.py`
- `gazebo_models/scripts/nav_bench.py`
- `gazebo_models/scripts/odom_capture.py`
- `gazebo_models/scripts/run_experiment.py`
- `gazebo_models/test/test_run_experiment.py`

This delivery also adds this report, the final session/results entries and
`docs/data/implementation_sprint/` evidence archives.
