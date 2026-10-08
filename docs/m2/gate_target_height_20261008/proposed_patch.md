# Minimum legitimate repair specification — not implemented

Status: **capability proposal requiring a scope decision and visibility feasibility
proof**, not an existing-field integration patch. The current camera cannot see
the target at the mandatory pre-attachment gate. No software-only connection
satisfies the frozen contract. This is the minimum repair class supported by the
evidence; a final mount or a guaranteed successful estimator is not yet proven.

## Approval boundary and first feasibility gate

Approve use of the **same existing RGB-D sensor** from a placement/view that covers
the unchanged grasp, raise and post-release retreat configurations. Do not alter
camera clipping, depth acceptance, arm poses, grasp window, safety thresholds,
physics, search or navigation. In particular, merely reducing near clipping is
not a sensor observation repair. No geometry edits are authorized by this report.

For a forward-facing camera, the nearest relevant surface at the grasp window is
as close as `0.151 - 0.016 = 0.135 m` along base X. To observe that surface at the
existing 0.15 m acceptance limit, camera X would have to be below -0.015 m,
before considering vertical field of view, margins or occlusion. This necessary
bound rules out the current X=0.125 m. It is **not** a proposed mount: placing the
camera there at its current height can intersect the chassis. A feasible mount
requires clearance, full vertical geometry, arm/finger occlusion and carry/release
views to be checked against the actual URDF on both backends. Pitch alone has not
been proved to solve any of these constraints.

Deliver feasibility evidence before implementing the consumer: synchronized
sensor frames with identifiable observed geometry at pre-attach, raised and
released/retreated states, with deliberately failed grasp/retained-object negatives.
Use evaluator truth only in the offline acceptance test. If the existing sensor
cannot furnish these views without changing frozen motions, stop and request a
new scope decision. Do not add a fallback height or substitute joint/magnet state.

## Exact prospective changes, after that gate

| File | Functions/classes and purpose |
| --- | --- |
| `coco_config/coco_config/robot.py` | CAMERA_MOUNT_XYZ, CAMERA_XYZ, CAMERA_RPY only if an existing-sensor remount is approved; derive one consistent measured extrinsic, no other robot constants |
| `gazebo_models/urdf/coco_robo2.xacro` | camera_joint origin only for approved physical mount; keep sensor type, clipping, rates and physics unchanged |
| `coco_sim/coco_sim/isaac/model.py` | camera prim setup in robot construction currently using CAMERA_MOUNT_XYZ; update orientation handling to match approved shared extrinsic if required; robot_description camera_joint must agree |
| `coco_perception/coco_perception/object_height.py` (new) | `ObjectHeightObservation`, `estimate_object_height`: pure measured geometry, source validity and support-reference estimation; do not repurpose target_pose's centroid contract |
| `coco_perception/coco_perception/object_height_node.py` (new) | `ObjectHeightNode(AutonomyNode)`, `_on_info`, `_on_depth`, `_on_image`, `_on_colour`, `_publish`: sensor-time pairing/TF, association and dedicated physical observation output |
| `coco_perception/setup.py` | register `object_height_node` executable |
| `coco_perception/launch/perception.launch.py` | start the dedicated observer; preserve existing acquisition producer and its topic meanings |
| `coco_moveit_config/scripts/arm_control.py` | constructor subscriber/cache, `_on_object_height`, `target_height`; baseline/source-reference bookkeeping in grasp_magnet/check_lifted only as needed to reject incomparable samples |
| `coco_moveit_config/scripts/grasp_server.py` | `_select` invalidates object observation on target change; check_released validates the same support-height semantics; preserve ordering and comparisons |
| `coco_perception/test/test_object_height.py`, `test_object_height_node.py` (new) | measured center/support, occlusion/identity/timing/TF rejection and actual ROS message contract tests |
| `coco_moveit_config/test/test_grasp_contract.py` | valid independent observations and adversarial observations, no changes to current missing-data rejection expectation |
| `coco_mission/test/test_ground_truth_isolation.py` | include observer in endpoint/remap isolation and contradictory-/eval independence tests |

These changes are a bounded new observation capability. They are larger than a
topic remap because no existing module computes the required quantity. Camera
extrinsic changes are **robot configuration changes** and must be approved as
such; they must not be hidden as evaluator work. The pure estimator may reuse
existing colour masks, depth statistics and deprojection, but must not change
TargetPose/TargetFinder acceptance or centroid/grasp-point semantics.

## Input, output and ROS contract

Input: existing `/camera/image_raw` (sensor_msgs/Image BGR),
`/camera/depth/image_raw` (Image metric depth), `/camera/camera_info` (CameraInfo),
`/mission/target_colour` (String), legitimate camera/base TF at image time and IMU
attitude when gravity alignment is required. Confirm actual configured parameter
values at implementation; reuse the existing sensor topic parameters/remaps.
No `/eval`, simulator pose, model query, object world-height cache or scene manifest.

Output proposal: **`/perception/object_height`**, std_msgs/String containing a
versioned JSON observation (existing standard message; no rosidl/interface package):

```json
{
  "schema": "coco.object_height.v1",
  "stamp_ns": 0,
  "depth_stamp_ns": 0,
  "frame_id": "base_footprint",
  "colour": "red",
  "track_id": "sensor-associated-track",
  "reference_id": "observed-support-reference",
  "valid": false,
  "reason": "UNAVAILABLE",
  "center_m": null,
  "support_height_m": null,
  "center_height_above_support_m": null,
  "uncertainty_m": null
}
```

This is a **proposed interface**, not currently published. Use source image stamp,
not report/receipt stamp; invalid observations must actively invalidate the cache.
Track identity is perception association, never configured model truth or requested
colour alone. Ambiguous identity invalidates the physical proof.

The estimator must recover center and upright extent from **observed** object
surface/end geometry, with support estimated from depth. Known cylinder dimensions
are legitimate configuration priors but cannot themselves produce measured height.
Do not take a visible mask centroid, bbox center, fixed grasp point or partial
extent as the physical center. Occluded/missing ends or ambiguous model fit must
return unavailable unless observability of the center is independently demonstrated
by the measured geometry. A full object pose/support fit is needed to distinguish
upright rest from a fallen cylinder. Geometry feasibility includes that visibility.

## Frame and validation contract

1. Pair depth/RGB with the existing sensor timestamp matching mechanism. Apply
   image-time camera TF; reject missing/stale transform. The existing 0.1 s pairing
   and 0.2 s TF-age conventions are not proof of acceptable *height* uncertainty;
   validate them under manipulation and tighten rejection if required by evidence,
   never silently increase them to accept data.
2. Sensor center must be finite, independently observable and associated with the
   selected physical track. Missing, NaN, inf, ambiguous, clipped/unobservable and
   future samples invalidate. A mask not touching the image edge is insufficient.
3. Gravity/support reference must be valid and consistent across pre-attach/lift
   samples. IMU provides attitude, not support position. Encoder TF cannot supply
   missing vertical displacement. Reject reference changes instead of interpreting
   them as object lift.
4. `target_height()` returns the validated center-height scalar in that reference,
   or None. Require a fresh source sample at attachment and a later fresh sample
   after raise. For release use the independently observed actual support and
   upright center/rest semantics, not a prior that the object is standing.
5. Commit justified age/uncertainty limits from independent sensor validation before
   enabling the valid consumer path. They must rule out the fixture's 45.814 mm
   framing-induced false lift. **No guessed numeric limits are supplied here.**
   Until supported limits/observability are established, fail closed. Preserve
   physical rise≥0.03 m and release tolerance0.02 m; uncertainty must not allow
   borderline evidence to create a false PASS.
6. Preserve no attach without baseline, finger opening before detach, missing/stale
   posture/fix rejection, cleanup, retry budgets and all arm/MoveIt/Nav2 behavior.
   Positive verification must arise solely from the independently observed object.

## Required regression and runtime acceptance

- Current reproduction still rejects when the new observer is absent. No privileged
  cache, constant pose, successful arm movement or magnet acknowledgment satisfies it.
- Pure fixtures with measured complete geometry, known camera extrinsics and support
  reproduce center/support height; occlusion-only centroid shifts cannot become lift.
  Clipped surfaces, ambiguous same-colour objects, fallen targets and missing support
  invalidate. Use geometry-derived fixture truth solely in tests.
- Node tests use real ROS Image/CameraInfo/TF/messages: pairing mismatch, stale/future
  stamps, source-vs-report stamp, invalid schema/frame/units, target changes, replayed
  old sample, track/reference change and invalid-after-valid all remain fail closed.
- Consumer sequence: fresh baseline before attach; independently later object rise
  passes only at existing threshold; commanded raise with object stationary fails;
  detached actuator with object still carried fails release; valid observed upright
  rest passes existing comparison. Verify command ordering unchanged.
- Actual ROS graph proves observer/autonomy do not subscribe to `/eval`; remapping
  the observation input there rejects. Inject contradictory evaluator data and
  demonstrate identical autonomy decisions.
- After host/bootstrap gates permit it, sequential Gazebo then Isaac Dev controls
  record RGB-D/observation, source TF/stamps, actual mission, magnet/fingers, MCAP,
  independent evaluator object pose and oracle. Check sensor estimate against
  offline evaluator truth, attachment failure/lift-air/retained-object negatives,
  and mission/oracle agreement. Stop on disagreement; never tune from Test A.

Expected effect: physical checks become possible, not guaranteed successful fetch.
Successful oracle-PASS Dev controls are still conditional on host qualification,
resource-bootstrap resolution, complete passive witnesses and the unchanged robot
actually succeeding. Then full-stack resource/invariant calibration and smoke can
proceed. No production implementation, behavior change or success claim is made.
