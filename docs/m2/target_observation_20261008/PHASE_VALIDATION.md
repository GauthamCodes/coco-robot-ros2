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

## Executed phase/control evidence

Entry SHA `1376250fe91adc07f2404530e1e048fbfc52ab24`; clean expected branch;
Downloads and repository Master Plans were byte-identical.

* Acquisition-01: 20 geometrically valid source observations; support-relative
  centre median79.003038768mm, uncertainty2.531797975mm. Recorder receipt
  freshness accepted only2 samples; this is not a live consumer success claim.
* Grasp-original-03:23 consecutive TARGET_ABSENT_OR_AMBIGUOUS outputs at the
  original mount/grasp distance. No near-plane mechanism inferred from absence
  alone; original CAD range bounds and raw frames remain separate evidence.
* Grasp-front-flank-01:23 valid source observations; measured support Z
  -12.543285834mm in base_footprint; measured centre Z67.451822931mm;
  centre above support79.995108765mm; uncertainty4.120002813mm;
  depth median425.203144550mm; valid depth fraction1.0. Static repeated values
  have IQR0 and degenerate bootstrap median intervals, recorded in
  `validation/phase_20261009/runtime_summary.json`. This measures repeatability
  of this static render, not independent accuracy or a calibrated noise bound.
  Only1 recorded sample passes receipt freshness/continuous-association checks.
* Guarded-motion-03: real existing-controller/MoveIt stow completed. Independent
  sensor-only phase consumer accepts5/5 baseline and31/31 approach observations
  at 24–46ms source age. Existing robot-pose guard rejects pick
  because this composition lacked encoder odometry; no safety bypass applied.
* Guarded-motion-06: existing encoder controller/arbiter, normal approach service,
  corrected image-time target TF and normal guarded grasp server used. Approach
  arrives with x0.1517m,y approximately-0.0001m; real MoveIt hover/grasp complete.
  Log explicitly reports `Magnet attached` at wall epoch1791494007.993052925.
  A fresh measured baseline is required by the unmodified-at-that-run grasp
  consumer before it can issue attach. This confirms command/plugin state,
  **not independently verified physical attachment/lift**. Watchdog aborts on
  unreadable external PID51340 metadata before raise/release evidence exists.
  Driver final JSON was interrupted by repeated shutdown signals; raw MCAP,
  sidecar, source phase events and logs are preserved; no finalized driver
  result is reconstructed. Oracle with absent terminal facts is UNSCORABLE.

All raw runs are under `/home/gautham/coco_m1_runs/rgbd-phase-20261009/`.
`validation/phase_20261009/external_evidence.json` hashes retained external files,
including every bag; each run manifest also hashes its MCAP and metadata.
Failed, blocked and interrupted attempts remain retained and excluded from M1.

## Final consumer transition implementation (runtime pending)

Acquisition/colour selection clears both live observation and old grasp context.
Grasp approach clears live data and requires a source stamp after that transition.
Before raise, clear live data again; the measured grasp baseline stays historical
context only. A later same-track/support observation must prove rise with both
uncertainties and the unchanged30mm requirement. Descent and post-detach retreat
start new observation epochs; release confirmation requires a post-retreat sample.
Release compares to the **measured original baseline**, with both uncertainty
bounds and the unchanged20mm tolerance. Nominal TARGET_HEIGHT is no longer a
release measurement reference. Planning/task dimensions and motion remain frozen.
These refinements pass regression but postdate guarded-motion-06 and are not
retroactively called runtime verified.

Phase validator, exporter and engineering driver never subscribe to /eval or
world/model/object truth. Runtime target_finder now uses source-time camera TF;
its former configured extrinsics produced x approximately0.5525m for the remounted
camera. Same pixels/segmentation/gates, correct TF, and existing approach contract
produce the x0.1517m fix. No camera production asset was changed.

## External gate

Current read-only diagnostic directly caught root-owned `(udev-worker)` PID23669,
PPid445(systemd-udevd), stateS, repeatedly unreadable `/proc/23669/exe`.
The production background allowlist recognizes systemd-udevd, but not its worker
signature. No live process was killed or ignored. Passwordless read-only sudo is
unavailable. An exact background-rule proposal is preserved but NOT APPLIED;
user approval is required by this session for any qualification-policy change.
Until approved or metadata is inspectable, further dependent simulation is gated.
Lift/release/Isaac/full-stack/M1 remain blocked, not disproved or completed.

## Final resource stop after consumer/queue repair

Guarded-motion-08 (source7659bf1) passes preflight but aborts during startup at
available RAM8,191,639,552 below the unchanged capacity-derived8,229,275,648-byte
reserve. No motion or phase records reached; finalized control reports zero samples.
A new evidence-backed optimization replaces four simultaneous Python controller
spawners with one installed multi-name spawner, and execs the generated launch
instead of retaining a duplicate fixture-builder interpreter. All required
controllers and the active-controller-before-command guard remain intact.
126 focused checks pass after this optimization.

Guarded-motion-09 (source33ca3cb) still aborts during startup at RAM8,120,913,920,
108,361,728 bytes below8,229,275,648. Both attempts preserve MCAP and finalize
owned teardown with zero survivors/errors. No final consumer lift/release runtime
claim. Current post-teardown idle available RAM8,640,970,752 leaves only411,695,104
bytes above reserve before the required simulator/control/evidence workload.
This is user stop condition5 for the required engineering phase experiment;
recurring unreadable root metadata is a second environmental gate. No further
simulation is safe under current headroom. No hardware-incapacity conclusion:
additional owner-controlled background headroom may suffice. Do not kill foreign
processes or lower reserve. The udev proposal remains NOT APPLIED; approval alone
would not resolve this resource stop. Next run must use a new output (guarded-motion-10)
and fresh unchanged preflight after host resources recover.
