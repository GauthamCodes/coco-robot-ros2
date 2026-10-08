# Existing RGB-D repair: feasibility execution checkpoint

**NOT VERIFIED. No production observation repair implemented.** This records
executed feasibility checks and the gate encountered, not a replacement design.
The implementation authority remains
[`../gate_target_height_20261008/proposed_patch.md`](../gate_target_height_20261008/proposed_patch.md).
The user's 2026-10-08 instruction supplies the previously missing bounded robotics
scope authorization. It does not supply calibrated host limits or remove the
instruction to qualify before simulator launch.

## Current sensor configuration, checked from source

Both cameras are at base_link `(0.125, 0, 0.055)` m, equivalently
base_footprint `(0.125, 0, 0.0685)` m. Camera-link RPY is zero. The optical
frame has joint RPY `(-pi/2, 0, -pi/2)`: Z forward, X right, Y down.
The chain is base_footprint → base_link → camera_link → camera_optical_frame.

Resolution is 320×240; horizontal FOV 1.25 rad; derived vertical FOV
0.9919896804 rad. The nominal pinhole intrinsics are fx=fy=221.76500408 px,
cx=160, cy=120. Gazebo RGB clips at 0.05–8 m, depth at 0.1–8 m.
Isaac's USD camera clips at 0.1–8 m. Acquisition accepts 0.15–2 m.
Gazebo specifies RGB8, and the ROS consumer converts to BGR8 and float-metre
32FC1 depth. Isaac requests RGB/depth/CameraInfo helpers, simulation timestamps,
frameSkipCount=1 and queueSize=2. Actual Isaac depth encoding, delivered rates,
RGB/depth skew and source stamps are **not freshly observed**.

Gazebo specifies a 15 Hz camera. Existing acquisition pairs source timestamps
within 0.1 s and requests image-time TF, with max_tf_age=0.2 s. These existing
limits are not a validated physical-height uncertainty budget. No observer age,
point-count, fit-error, or uncertainty threshold has been invented from them.

## Executed geometry checks

`validation/geometry_audit.py` re-reads the configuration and computes bounds.
At the accepted grasp window the current forward depth is at most 41.5–47.5 mm.
An enclosing-box distance bound, including the permitted lateral offset and full
upright height, is only 100.66–104.61 mm. Forward depth in any orientation cannot
exceed Euclidean distance. Thus pitch/yaw alone at the current camera origin
cannot reach the unchanged 150 mm acceptance bound. Translation is necessary.
This is an offline nominal-rest bound, not evidence about actual object pose.

`validation/mount_probe.py` expands the actual xacro, performs joint FK, loads
CAD triangles, and tests camera-to-fixture segments against the robot. It includes
Isaac's solid chassis cube as an additional conservative blocker; it does not
pretend the two renderers have identical base visuals. Target geometry is confined
to this diagnostic fixture and never reaches ROS/autonomy.

Frustum screening covers all colours, both grasp-window endpoints, both lateral
extremes, and unchanged baseline/raise/release-retreat poses. Ideal successful weld,
failed grasp and retained-object hypotheses are explicit test fixtures. Forward
acquisition volumes are also screened. Mesh rays sample one blue window corner:
three points at each end and three at mid-height. Passing sparse rays would still
not certify a complete mask, end observability, physical mount clearance, swept
volume, sensor uncertainty, timestamp correctness or robot dynamics.

The coarse grid is 648 candidate placements, of which 285 satisfy the conservative
frustum test. All 285 have at least one blocked sampled ray. A refined flank grid
is separately retained in the external evidence. Neither a discrete grid nor
sparse ray sampling proves that every compliant placement is impossible. No
mount is selected or applied from these checks.

## Current-code corrections to the proposal

1. Isaac's `coco_sim/coco_sim/isaac/runtime.py` directly publishes the camera
   static transform in its non-fetch path. Any orientation change must update
   that publication consistently with `model.py`, generated robot_description,
   the shared extrinsic and the xacro. Updating only the camera prim would
   produce a sensor/TF discrepancy. Fetch extracts the full static tree from
   its description. This additional file is inside the same sensor-plumbing scope.
2. The welded target rotates with the palm. `grasp_server.py` explicitly documents
   this and the existing FK supplies the transform. An upright-only estimator
   throughout raise would contradict the frozen motion. Full pose/end geometry
   is required for height during lift; upright rest is a release check.

## Gate reached before production integration

The approved proposal requires synchronized sensor visibility evidence **before
implementing the consumer**, and independently supported age/uncertainty limits
before enabling it. Both fresh project preflights exit 3 solely for null
`min_ram_available_bytes` and `min_vram_free_bytes`. No foreign robotics process
or DDS rejection is reported. Idle headroom and MCAP plugin availability do not
establish a full-stack resource envelope.

There is no bootstrap policy in `eval/qualification.py`, `eval/cli.py` or
`eval/host_policy.json`. Null limits explicitly reject launch. A successful run
cannot retroactively qualify the launch needed to obtain its own limits. The
missing decision is an approved bootstrap qualification policy or an independently
validated full-stack envelope, not routine sensor/interface design approval.
The production observer/consumer and sensor mount remain unchanged at this gate.

Final preflights also detect a newly active foreign Gazebo process (PID111827,
domain115) and unreadable PID60465 metadata. Isaac reports the additional
opposite-backend conflict. These new external blockers are preserved separately
from the clean-at-entry process inventory and the independent policy cycle.

## 2026-10-09 implementation checkpoint (supersedes absent-code statements above)

IMPLEMENTED and TESTED: `coco_perception/object_height.py` estimates a complete
measured cylinder from target-associated RGB-D samples. It deprojects through
CameraInfo and image-time TF into base_footprint; fits a support plane with bounded
NumPy Huber IRLS, a PCA cylinder axis and measured cross-section; reconstructs
centre and support-relative height. No known target radius/height or scene pose
is an estimator argument. A fit does not imply visibility during manipulation.

Depth gates reuse 0.15–2 m sensor/acquisition limits and six-point minimum.
Majority depth and untruncated endpoints are required. Depth outlier rejection
uses median/MAD and projected pixel resolution. Work is bounded to 2,048 samples
and ten IRLS iterations. Timestamp freshness uses the existing 0.2 s convention;
exact RGB/depth pairing avoids an unmeasured motion/skew assumption. Geometry
uncertainty combines pixel footprint, measured residuals and endpoint sampling.
The 5 mm rejection budget is one quarter of the existing 20 mm release tolerance,
not a measured production accuracy calibration. Ambiguous gravity/support,
occluded ends, changing target/support association and invalid TF fail closed.

`object_height_node.py` reuses colour_mask, requires one associated component,
publishes explicit invalid updates, and retains source timestamps. Shared
`coco_config/object_observation.py` validates the contract again at manipulation.
The consumer captures a valid measured baseline before attachment; later lift
requires a newer same-track/support sample and subtracts both uncertainty bounds
before applying the unchanged 30 mm rise gate. Release uses the unchanged 20 mm
tolerance with uncertainty included. There is no None-to-height fallback.

Runtime boundary: the engineering acquisition fixture produced usable real RGB-D;
the actual ROS publisher accepted its recorded frame and rejected stale replay.
Live Gazebo+observer startup aborted at the unchanged RAM reserve. Flank target
visibility exists in a partial capture but its support fit is rejected. No
production remount or full grasp/lift/release visibility is certified.
