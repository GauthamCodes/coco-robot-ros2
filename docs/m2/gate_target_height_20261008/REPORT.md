# Target-height gate: a missing observation capability

Decision: **success criterion B, within the frozen robot/sensor configuration**.
This is not a lost valid height field or an evaluator/interface bug. Acquisition
RGB-D exists, but an independent, fresh object-center/support-height observation
at attachment, lift and release does not. A data-only wiring patch cannot restore
that contract. The deliberate `None` and rejection are correct safety behavior.

Starting SHA: `a863e228a9ca317dddc023a618913f27f7977ea8`.
Branch: `coco-2.1-isaac-integration`; initially clean.
Master Plan copies byte-identical, SHA256
`e2d899d3b4f1b96a3958ace3833e32318985cc4edbcd05e12858ec91698aa03d`.
No Master Plan, production robot code, parameters, physics, seeds or benchmark
definition changed. No Test A traces inspected. M2 implementation not started.

## 1. Exact current failure

`ArmControl.target_height()` unconditionally returns `None`; GraspServer inherits
it without an override. `grasp_magnet()` assigns that result to `_grasp_z`, rejects
it, and returns false **before** `magnet('attached')`. `_do_pick()` records
`phase=pick:magnet attach`, `outcome=failed at magnet attach`. Finger closing,
raise, lift confirmation and carry are unreachable after this rejection.

The deterministic production-method reproduction accepts a valid RGB-D candidate,
approaches to `(0.15333169163659582, 0, 0.128)` in `base_footprint`, accepts the
fresh approach fix, passes the actual window/IK checks, then reproduces this
precise rejection. Its actuator log contains no attachment and no raise.
This is executable synthetic diagnostic evidence, **not a simulator episode**.

## 2. First point of information loss

There is **no valid independent physical center height to lose** in the existing
candidate contract. The earliest reduction is in `target_pose.observe()`:
RGB mask/depth becomes a selected blob's vertical centroid ray, with robust
surface depth and the existing radius correction. `transform_observation()`
transforms that axis reference point; it does not estimate physical center height.

At the actual attachment workspace, the first unavoidable acquisition failure is
earlier still: the target is inside the camera near plane. The approach deliberately
uses a last visible fix and blind encoder creep. `ApproachServer._run_phases()`
then overwrites report Z with the intended fixed grasp band. This is documented
command-pose construction, not an accidental conversion of a physical measurement.

Thus there are two distinct issues: the visible candidate never claimed the
required center-height semantics; and the frozen sensor geometry supplies no
fresh depth at the decisive attachment instant. Adding a subscriber cannot fix
the latter.

## 3. Legitimate observation available?

**YES for acquisition RGB-D/visible geometry; NO for the required independent
height during the frozen manipulation sequence.**

The repository configures a forward camera at base-footprint X=0.125 m. Every
colour's accepted grasp axis is in [0.151, 0.1565] m. For an upright target,
even its furthest surface has optical forward depth bounded by:

`0.1565 + radius - 0.125 = 0.0415 / 0.0435 / 0.0455 / 0.0475 m`.

These bounds are below Gazebo's RGB near plane 0.05 m, Gazebo depth near plane
0.1 m, Isaac camera clipping near plane 0.1 m, and perception's min_range 0.15 m.
The diagnostic parses both backend clipping values from their actual sources.
This proves the whole nominal upright target is near-clipped at attachment,
even before arm occlusion is considered. It is a configuration/geometry proof,
not a claim of measured rendering on this host. Arbitrarily pitching or remounting
the camera is a robot configuration change requiring separate approval/proof.

Single-plane LiDAR has no object vertical profile or independent center-height
contract. Its nominal scan height is 0.2135 m; the resting cylinder top is 0.158 m.
IMU measures robot attitude; joint encoders/FK measure arm motion; odometry
measures planar robot motion. None observes whether this cylinder rose or stayed
attached. Magnet state is mechanism acknowledgment, explicitly able to acknowledge
a stale weld that holds nothing. Their combination cannot distinguish the object
remaining on the support from following the arm without an object observation.

This does **not** prove RGB-D technology or this camera after approved relocation
is incapable. It proves the existing frozen interfaces/placement cannot satisfy
the contract at a mandatory gate. The future feasibility gate must cover all
three physical checks, not just acquisition.

## 4. Why None; complete data path and hidden support

M0 deliberately removed `gz model` world-Z queries and the Isaac privileged
height subscription. `docs/m0/MANIPULATION_OBSERVATION.md` records the reason,
the unavailable physical contract and the intentional loss of verified fetch.
`model_z()` remains unavailable; `_heights` is an unused legacy cache, not a
sensor subscriber. Restoring either privileged path would violate isolation.

| Step | Actual producer/consumer and semantics |
| --- | --- |
| Sensor | Gazebo xacro RGB-D / Isaac camera render helpers → Image, depth Image, CameraInfo; legitimate simulated sensor observations |
| Selection | TargetPoseNode image/depth matching + image-time TF → `target_pose.observe`, size/depth validation; M1 positions missions explicitly select `target_pose` |
| Candidate | `transform_observation` → base-frame visible axis reference; candidate diagnostics also deproject masked depth pixels |
| Geometry | `/perception/target_pose` Detection3D bbox center is that reference; bbox dimensions are known configuration priors, not measured object extent |
| Grasp point | `/perception/grasp_point` PoseStamped fixes Z to TARGET_GRASP_Z=0.128; `/perception/target` PointStamped retains observed reference Z and source image stamp |
| Approach | `_on_target`/`_fresh_target` preserve/dead-reckon the reference; `_run_phases` creeps blind and publishes `/approach/target` PointStamped, with Z=0.128 and current report stamp |
| Manipulation | `_on_fix` validates frame, finite values, grasp band and stamp; `_target_pose` returns XY only; `solve_grasp` uses the fixed arm grasp height |
| Physical reference | `ArmControl.target_height` has no independent observation producer; returns unavailable |
| Attachment | `grasp_magnet` rejects missing reference before magnet transport |
| Lift/release | `check_lifted`/`check_released` need new independent physical observations; never infer them from a commanded pose |

Hidden support checked: TargetFinder's alternative acquisition path has the same
centroid/surface-depth semantics. Candidate diagnostics expose visible point cloud
centroid/extents, explicitly **not** object center/full-cylinder dimensions.
MoveIt scene cylinders use `(x,y,TARGET_HEIGHT/2)` and known dimensions as planning
priors, not sensed state. Neither detection IDs mapped from colour nor configured
dimensions constitute physical identity or observed center height.

The synthetic occlusion fixture demonstrates two accepted internal masks with
`touches_image_edge=false`, observed base Z 0.126913 and 0.081099 m, a **45.814 mm**
centroid difference, despite identical grasp Z=0.128. These are idealized visible
bands at the same range, with no physical lift encoded; they are not rendered
cylinder frames. They demonstrate framing dependence, not measured robot motion.
Visible extents are only
24.801 mm vertically in the optical image plane. Wiring reference Z or visible
bbox extrema into lift proof could pass the 30 mm gate from framing alone.

## 5. Exact fail-closed safety conditions

`grasp_magnet`: independent baseline must be available before attach.
`check_lifted`: baseline and current independent height must be available; rise
must be at least `LIFT_MIN_RISE=0.03` m. Actuator state/FK is insufficient.
`check_released`: independent center/support height must be available and within
0.02 m of `TARGET_HEIGHT/2=0.079` m after detach and retreat. The object remaining
stuck or falling over must not produce placed success. Existing finger-open-before-
detach ordering, posture/fix validation, cleanup and numeric comparisons remain.

The old privileged value was world Z. A replacement cannot silently substitute
arbitrary base Z: lift samples need a consistent gravity/support reference, and
release requires center above the actual support. Planar odom TF does not provide
world elevation. Support-reference validity must be established from legitimate
observations/geometry, with invalid or incomparable references remaining unavailable.

## 6. Classification against the Master Plan

Question-1 categories: **G intentional fail-closed logic + H missing capability**,
with A missing fresh object data at the manipulation workspace. Not B/E interface
or schema mismatch, not C/F TF/timing failure in the demonstrated rejection.
There is no accidental D connection whose restoration supplies the missing truth.

This is a **pre-existing robotics observation capability gap exposed by M0**, not
an M1 evaluation defect or a proven simple integration bug. A future repair is
robotics work requiring explicit scope. The plan forbids behavior changes in M1
(M1 “Forbidden”) and makes ordinary M2 fixes follow M1's failure Pareto (M2 opening).
G1 is not satisfied, so naming this directory `m2` does not authorize M2 entry.
A scope exception/prerequisite decision is required; this investigation neither
changes the plan nor reclassifies the absent sensor capability for convenience.

## 7–10. Minimum legitimate fix, files, safety, tests

See [proposed_patch.md](proposed_patch.md). **No compliant data-only patch exists
under the frozen geometry.** The minimum feasible class is an explicitly approved
observability repair using the existing RGB-D sensor, followed by a measured
physical-center/support-height producer and a narrow ArmControl consumer.
Camera relocation/view feasibility must be established before approving mounting
coordinates or promising a working implementation. No new sensor or planner is
proposed. If existing-sensor placement changes are disallowed, keep this gate closed.

The proposal names exact prospective files/functions, ROS inputs/output schema,
frame/timing requirements, preserved gates, focused tests and cross-backend
validation. There is no guessed/default height, prior-only lift proof, ground-truth
input, threshold relaxation or attachment-ack shortcut. No robotics patch applied.

## 11. Actual M1 restart dependencies

The fix alone does **not** make production M1 launchable. Prior sprint evidence
records a resource bootstrap cycle: production preflight requires calibrated
limits; calibration requires qualified oracle-PASS Dev controls; those controls
need preflight and physical fetch. Nine raw evaluator witnesses are also unfinished.
They are independent work, not solved by this proposal. `dependency_graph.json`
preserves all19 threshold dependencies and the raw-witness gaps by reference/data.

Correct sequence: owner scope decision → existing-sensor visibility proof → minimal
observation implementation → focused regression/isolation → separately authorized
resource-bootstrap resolution and missing passive witnesses → fresh host qualification
→ successful Dev controls with independent oracle agreement → full-stack CPU/RAM/
VRAM/RTF measurement and all applicable analyzer distributions/margins → qualified
four-job smoke and validate-smoke → M1.8 sequential 20/60/60 committed campaigns.
Stop immediately on mission/oracle disagreement. Synthetic evidence cannot calibrate.

Immediately newly measurable after a *validated physical observation repair* are
pre-attach reference, actual object rise, release/rest height and mission progression
past attachment. Complete successful controls would then expose resource peaks,
RTF and threshold distributions **only after the other qualification prerequisites**.
Failures may still prevent oracle-PASS; this proposal promises no success rate.

After all gates pass, use a **new runtime fingerprint/campaign root** for changed
robotics, preserving the old blocked root. Exact runner sequence:

```bash
./eval/bin/eval preflight --backend gazebo --output /tmp/coco-height-gazebo-new.json
./eval/bin/eval preflight --backend isaac --output /tmp/coco-height-isaac-new.json
./eval/bin/eval campaign eval/campaigns/m1_smoke.yaml --output /home/gautham/coco_m1_runs/approved-height-smoke
./eval/bin/eval validate-smoke /home/gautham/coco_m1_runs/approved-height-smoke --output eval/runtime_validation.json
./eval/bin/eval campaign eval/campaigns/m1_determinism.yaml --output /home/gautham/coco_m1_runs/approved-height-determinism
./eval/bin/eval campaign eval/campaigns/m1_breadth.yaml --output /home/gautham/coco_m1_runs/approved-height-breadth
./eval/bin/eval campaign eval/campaigns/m1_test_a.yaml --output /home/gautham/coco_m1_runs/approved-height-test-a
```

These are conditional restart commands, not authorization or claims of execution.
Source the clean M1 environment as in reproduction/README.md; production uses
documented domain82, not diagnostic domain187. No seeds or campaign files change.

## 12. External domain66 status

At 2026-10-08 05:21:48 UTC, PID260322 absent; no accessible `/proc` environment
declared domain66. This records the known blocker no longer being observed, not
machine qualification or proof about permission-denied processes. No external
process signaled. Fresh project preflight remains mandatory; if an external workload
returns, only its owner may release it. Remaining resource/observation/witness gates
are independent of domain66 and were not removed by this disappearance.

## 13. Exact human decision

Authorize a **scoped prerequisite capability repair before the M1 behavior freeze
can resume**: first prove an existing RGB-D camera placement/view can independently
observe baseline/lift/release without changing motions, clipping, physics or safety;
then review/approve the bounded observer/consumer patch specified here. This is a
scope exception for robotics capability, not approval for broad M2 or automatic
implementation. Alternatively decline geometry/capability work and retain the
current fail-closed blocker. A one-line height connection is not a legitimate option.

Evidence: [reproduction/result.json](reproduction/result.json),
[logs and command](reproduction/README.md), [provenance](reproduction/provenance.json).
Focused regressions8/8 passed. Behavior changes **NONE**; no qualified controls,
smoke, baseline, M1 completion or M2 engineering claimed.
