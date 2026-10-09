# Observation contract status at the qualification stop

**NOT IMPLEMENTED.** No `/perception/object_height` publisher or subscriber has
been added. The proposed `coco.object_height.v1` contract in
[`proposed_patch.md`](../gate_target_height_20261008/proposed_patch.md) remains
the starting contract; this file does not declare it operational.

| Item | Required semantics / current status |
| --- | --- |
| Publisher | Dedicated `ObjectHeightNode(AutonomyNode)`; absent |
| Inputs | Existing RGB, depth, CameraInfo, selected colour and image-time camera/base TF; gravity attitude when needed |
| Sensor QoS | Existing BEST_EFFORT, depth 1 convention; actual graph unverified here |
| Output | Proposed std_msgs/String versioned JSON on `/perception/object_height`; absent |
| Output QoS | Not instantiated or validated; must be recorded when implemented |
| Identity | Perception-associated physical track; colour alone is insufficient |
| Quantities | Measured object centre, measured support plane/reference, centre height above that support, uncertainty and spatial/depth support |
| Units | Metres for positions/heights/uncertainty; nanoseconds for source stamps |
| Frame | Proposed base_footprint coordinates plus a stable, observed gravity/support reference; base Z alone is not global elevation |
| Time | RGB and depth source stamps, image-time TF; receipt/report time cannot rejuvenate data |
| Validity | Explicit valid/invalid with machine-readable reason; invalid updates must clear the cache |
| Rejections | Missing/sparse/near-plane depth, unobservable ends, occlusion, edge clipping, ambiguous fit or identity, invalid/future/stale source time, missing/bad TF, frame/target/reference mismatch |
| Consumer | Guarded ArmControl baseline/lift and GraspServer release validation; absent |
| Physical gates | Preserve baseline-before-attach, 0.03 m minimum rise, 0.02 m release tolerance, opening-before-detach and all existing motion/safety gates |
| Uncertainty | Must be justified from independent sensor validation, with conservative comparisons; no defaults accepted |
| Failure | No fallback height; `target_height()` currently returns None |

The valid sample path is not enabled. No live graph or contradictory-evaluator
independence experiment is claimed. Existing AutonomyNode rejects resolved
`/eval`, `/world`, `/model` and privileged grasp-height subscriptions; it was not
modified. Simulator truth remains restricted to offline evaluation. No autonomy
ground-truth input, fixed-height fallback or alternate success source was added.

## Implemented ROS contract — 2026-10-09

The historical absent-contract statements above describe the previous checkpoint.
Publisher: `object_height_node`; topic `/perception/object_height`; type
`std_msgs/msg/String` containing strict JSON schema `coco.object_height.v1`.
QoS: RELIABLE, VOLATILE, KEEP_LAST depth10; confirmed with actual ROS CLI.
Consumers: ArmControl and GraspServer. Invalid updates clear usable measurement;
missing, stale or malformed data cannot construct a manipulation height.

Fields: `colour`, `track_id`, `reference_id`, `stamp_ns`, `depth_stamp_ns`,
`source_frame`, `frame_id`, `units`, `valid`, `reason`, `center_m`,
`support_height_m`, `center_height_above_support_m`, `uncertainty_m`,
`transform_valid`, `observation_age_s`, `depth_sample_count`, `inlier_count`,
`mask_pixels`, `valid_fraction`, `depth_median_m`, `depth_mad_m`, measured radius,
axis and extents. Invalid geometry is null, never a guessed zero/height.

Coordinates are metres in base_footprint, transformed from camera_optical_frame
at the original RGB/depth source stamp. Support height is the measured support
plane Z at centre XY; centre height above support is their difference. It is
not global altitude. Timestamps are integer ROS nanoseconds; exact pairing and
age in [0,0.2] s are mandatory. Consumer computes age from its own ROS clock.
Transform validity includes finite rigid transform, proper frames and timestamp.
Track/reference IDs are sensor association tokens, not simulator model IDs.
Unique-colour association cannot identify two same-colour objects: reject.

Actual subscriptions: RGB, depth, CameraInfo, mission target colour, /clock,
/tf and /tf_static. No /eval/world/model input. Live graph and successful
sensor-byte replay: `validation/lightweight_20261009/ros_replay_result.json`.
This is NON_QUALIFYING_ENGINEERING_REPLAY, not a simulator mission or Dev control.

### Phase epochs and measured release reference — current implementation

`ArmControl.begin_observation_phase` clears the live cache and records the ROS
transition epoch. A consumer-valid sample must be strictly newer than that epoch.
GraspServer applies this at acquisition, grasp approach, raise, release descent
and post-detach retreat. Historical measured baseline is retained for comparison,
never returned as live height. Release uses that measured baseline and both
uncertainties within the unchanged20mm gate. No nominal height substitutes for
measurement. These final refinements are TESTED; full-phase runtime remains open.
