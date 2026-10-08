# Gazebo bootstrap startup — actual sensor capture, emergency resource abort

Start SHA `f85c8184458ca436949bf374794c65bfba8b39a9`; branch
`coco-2.1-isaac-integration`, clean entry. Downloads/repo Master Plans byte-equal,
unmodified. Earlier foreign Gazebo111827 and metadata-denied60465 are absent.
Both clean-domain82 bootstrap preflight-only commands pass with no reasons.
This is bootstrap safety approval, never production host qualification.

Milestone M1/M1.1 engineering bootstrap + authorized RGB-D prerequisite.
**Requested observer/consumer and mandatory-phase visibility NOT ACHIEVED.**
Stop condition6 reached under committed emergency policy. No claim that a new
sensor, geometry change or inadequate hardware is established.

## Executed command and result

```bash
export COCO_WS=/home/gautham/coco_m1_ws
export COCO_MOVEIT_PREFIX='/home/gautham/ros2_ws(personal)/moveit_prefix/root/opt/ros/jazzy'
source setup_env.sh
export ROS_DOMAIN_ID=82 ROS2CLI_NO_DAEMON=1
./eval/bin/eval bootstrap --backend gazebo --seconds 120 --domain 82 \
  --output /home/gautham/coco_m1_runs/bootstrap-20261009-continue/gazebo-sensor-current
```

Execution used env-i/no shell startup files and exact existing overlay.
One unchanged Dev5 full-stack launch; no repeated experiment or Isaac launch.
120s is a wall ceiling, not observed duration. Emergency abort at wall7.0108s:
load14.54638671875>12 and RAM available8,010,498,048<8,229,273,600 bytes.
Manifest ABORTED_BOOTSTRAP_RESOURCE_LIMIT, qualified=false, denominator=false.
Total lifecycle27.2786s including owned teardown; no survivors/errors.
The scene reaches ROS/Gazebo sensor startup; manipulation not reached.

Safety reserves were unchanged:50% actual physical RAM (or16×kernel min-free
if greater),1/3 physical GPU memory, existing load/disk limits. Current RAM total
is16,458,547,200 bytes; min-free67,584KiB. Policy is a conservative derived
budget, not a measured workload requirement or proven hardware incapacity.
No threshold lowered to pass. Release unrelated background resources with owner
authority and allow host load to settle before a future fresh gate. If startup
still violates the budget, a reviewed emergency-policy/resource-allocation
decision is required; production qualification must remain unchanged.

## Actual RGB-D evidence

[Sensor inspection](../../../m2/target_observation_20261009/sensor_inspection.json)
is decoded from actual MCAP, without reading /eval payloads/world/object state.
3 RGB,3 depth,4 CameraInfo,10 TF and1 TF-static packets retained. Source stamps
and frames are retained. Startup-only sensor streams were actually observed in
NON_QUALIFYING runtime; mandatory-phase visibility is **NOT VERIFIED**.

No requested red-target mask appears in any frame. Global valid depth fractions
are0.69190,0.69190,0.62014 (finite0.15–8m; not target depth fractions).
Paired RGB/depth source skew0,60ms,460ms; third pair invalid against existing
100ms convention. No target geometry/physical identity/near-plane result inferred
from the ground/background. The current unchanged camera view remains nominal
(0.125,0,0.0685)m base_footprint, original clipping; no mount searched in runtime.
Frame previews, depth arrays and TF are retained/hash-linked. These establish
sensor transport/capture only, not an observable centre/support-height model.

## New concrete capture defect and bounded fix

MCAP raw final JointState contains8 NaNs in effort. Strict JSON recorder crashes
on that packet after writing CDR, leaving its wall sidecar missing. Captured raw
bag remains preserved; never relabelled complete or reconstructed as a valid trace.
Recorder also reports magnet DURABILITY incompatibility; no attachment evidence
was received. MoveGroup logs a segmentation fault during teardown; no manipulation
success or mission/oracle contradiction is asserted from that exit.

Minimal fix commit4988df9: `ros_json_data` explicitly tags NaN/+Infinity/-Infinity
in sidecars; raw MCAP/CDR unchanged. Replay uses the same representation and still
requires exact topic/payload/receipt matches. Finite values, headers and UUIDs
are preserved; tagged unknown cannot become a finite measurement. No benchmark,
oracle, qualification, autonomy, geometry or safety semantics changed.

**TESTED locally:**41 focused bootstrap/qualification/replay/encoding checks;
1 real ROS/CDR/MCAP simulator-free check round-trips NaN effort and rejects zero
substitution. Not a simulator rerun or CI claim. Runtime recorder fix remains
**NOT VERIFIED**. Observer/consumer tests were not run because no observer exists.

## Partial startup resource observations (not full-stack envelope)

8 host samples, approximately1Hz; resources include background host activity.
CPU maximum99.9150%; load maximum14.5464; RAM used maximum8,448,049,152 bytes,
RAM available minimum8,010,498,048; VRAM used maximum953,155,584,
VRAM free minimum5,486,149,632; minimum free disk15,874,551,808 bytes.
No RTF value was sampled before abort. Samples end at the abort; they do not
bound teardown allocations. Stage/control not reached; no qualified measurement
or production-candidate envelope exists. Isaac CPU/RAM/VRAM/RTF unmeasured.
Full envelope files are deliberately not fabricated under bootstrap_resource_envelope.

## Production and M1

Fresh post-teardown original production preflights reject only null RAM/VRAM
requirements on both backends. Foreign-process/DDS/metadata issues are absent
in those snapshots. No host policy or analyzer threshold edited.19 calibration
dependencies unresolved; no qualified oracle-PASS Dev controls, smoke0/4,
M1.8 not started0/140. No held-out/reserve inspection. Oracle FAIL/mission
UNOBSERVED for aborted evidence; required physical witnesses missing, no successful
mission result with which to establish disagreement. ROOT_CAUSES fixed entry
not added without system-level observer/manipulation validation.

## Evidence and continuation

run_summary.json and startup_resource_summary.json are compact derivatives;
safety_envelope.json retains separate emergency limits. external_evidence.json
hashes all raw attempts/MCAP/logs/sensor frames/arrays under the external root.
Source-run SHA is f85c818; later recording patch cannot retroactively repair it.

No automatic next simulator launch after emergency abort. Smallest human action:
make the host quieter/free additional background RAM under owner control, then
fresh unchanged bootstrap preflight with new exclusive output. Otherwise review
an evidence-backed engineering-only resource policy, without weakening production.
Do not kill unknown host processes or infer cleanup permission from this report.

Next action remains actual bounded existing-camera visibility search covering
pre-grasp/approach/lift/release → observer + guarded consumer → successful Gazebo
and Isaac controls → full-stack envelope → original production qualification →
qualified Dev calibration/smoke → M1.8. No unrelated M2 reopened.
