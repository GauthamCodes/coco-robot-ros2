# Manipulation-phase validation — 2026-10-09

Authorized bounded RGB-D prerequisite; exit advanced: fresh sensor-derived
baseline/grasp/lift/release observations supporting unchanged guarded manipulation.
All fixtures are NON_QUALIFYING and excluded from every M1 denominator.

`coco_config.observation_phase.PhaseValidator` requires an explicit ROS-time
control phase event and a newer, consumer-valid source sample. Each transition
invalidates prior live evidence. Baseline is historical context, never a live
lift/release substitute. Identity/reference continuity is required; explicit
reacquisition starts a new baseline. `eval/observation_phase_export.py` records
raw observation fields, consumer rejection, receipt age and deterministic
median/IQR/bootstrap summaries. Missing phases are NOT_REACHED.

First live acquisition retained 21 observation records: 20 geometrically valid,
but only 2 fresh at the recorder. Engineering image JSON expansion and depth-100
image queues create avoidable evidence latency. Raw MCAP is retained at full
fidelity; optimized engineering sidecars contain original header/encoding/shape
and raw-byte SHA256. Production recording defaults remain unchanged.

Retained old flank RGB frame shows robot-body occlusion of the target lower end
and ground around it. Hypothesis: move the same engineering camera candidate
forward to x=0.40,y=0.30,z=0.25 m (base_link), retaining sensor resolution, clips,
object body and robot geometry, to expose the target/support from the front side.
This generated-fixture candidate is not a certified production sensor placement.
No motion/attachment/lift/release is inferred from static fixtures.
