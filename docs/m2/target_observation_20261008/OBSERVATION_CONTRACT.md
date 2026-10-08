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
