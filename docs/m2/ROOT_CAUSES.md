# COCO root-cause records

## RGB-D physical-observation gap — OPEN, 2026-10-09

- Hypothesis: removing privileged target-height inputs exposes a missing legitimate
  RGB-D height capability; current grasp geometry also near-clips the sensors.
- Observation: target_height returned None and grasp rejected before attachment.
  Historical CAD search did not certify an existing-sensor placement.
- Discriminator: sensor-only Gazebo fixture with unchanged backend target body,
  actual RGB/depth/CameraInfo/TF, plus runtime ROS observer replay; no autonomy
  world state, /eval input or height constant.
- Proof/evidence: static acquisition view has3228 target pixels, valid depth1.0
  and median0.216059m.22 coherent real frames estimate79.003mm above measured
  support. Recorded-frame ROS publisher accepts and subsequently rejects stale
  data. This establishes acquisition measurement capability, not full-phase
  manipulation observability or a fixed system-level root cause.
- Rejected alternatives: fixed-height fallback, privileged simulator object pose,
  rotation-only remedy for near clipping, production preflight bypass, counting
  engineering captures as M1 controls. None implemented.
- Fix implemented: bounded masked depth/support/cylinder estimator, actual ROS
  validity contract, guarded consumer baseline/lift/release integration. Existing
  30mm lift and20mm release gates retained, uncertainty applied conservatively.
- Regression:65 focused checks pass, including actual sensor bytes, NaN/near/sparse/
  stale/TF/frame/association/occlusion/outlier rejection and positive consumer.
- Rerun: acquisition camera-only fixture completes30s; live observer startup and
  flank capture abort at emergency RAM reserve. Partial flank data sees target
  but observer rejects its support/gravity reference. No actual manipulation
  outcome/oracle agreement exists; Isaac not launched.
- Result: IMPLEMENTED, TESTED, acquisition sensor and ROS replay RUNTIME VERIFIED;
  full system fix NOT VERIFIED. Required grasp/lift/release placement remains open.
  Full-stack resource envelope and original production RAM/VRAM limits unresolved.

Exact evidence: `target_observation_20261008/validation/lightweight_20261009/`;
report, DESIGN.md, OBSERVATION_CONTRACT.md and RESOURCE_PROFILE.md in that package.

### Phase execution continuation (still OPEN)

Input1376250: real existing-controller stow,5/5 fresh baseline and31/31 fresh
approach observations verified by a sensor-only phase consumer. Front-side
existing-camera fixture yields23 repeated valid source geometries. Runtime exposed
configured-extrinsics target_finder output inconsistent with remounted camera TF;
source-time TF plumbing repaired with regression, segmentation/gates unchanged.
Normal approach then yields x0.1517m, real hover/grasp and `Magnet attached`.
External metadata safety abort interrupts before lift/release; physical attachment
and oracle PASS remain unverified. Final phase-cache invalidation and measured
release-reference changes are tested, not runtime closed. Never mark ROOT-CAUSED
AND FIXED from this partial control. Exact evidence:
`target_observation_20261008/validation/phase_20261009/` and PHASE_VALIDATION.md.

Final motion-08/09 resource aborts prevent final phase-consumer runtime; minimal
startup still violates unchanged RAM reserve after duplicate-loader/builder costs
are removed. Stop condition5, plus recurring unreadable root process metadata.
No system-level ROOT-CAUSED AND FIXED entry; qualification/M1 remain unopened.

### Manipulation verifier continuation — OPEN

- Hypothesis: command/plugin evidence cannot establish physical object following;
  absent evaluator truth in the partial-arm composition prevents independent
  attachment/lift/release claims.
- Discriminator: synthetic traces retain identical command/plugin reports but
  vary only world target motion; report remains PASS while physical attachment
  changes from PASS to FAIL. Missing truth/TF/calibration stays unknown.
- Evidence: real guarded-motion-06 MCAP decodes1730 matching records, including
  attached report but no evaluator target truth. Historical replay preserves
  existing oracle FAIL and supported I19; no retrospective physical PASS.
- Rejected alternatives: mission verdict, changed camera centroid, or plugin
  `attached` as independent physical evidence; invented numeric calibration;
  repeating resource-limited simulation without changed headroom.
- Fix: offline diagnostic extension of existing oracle/analyzer/replay; exact-time
  recorded TF and independent world object evidence; engineering truth capture
  and explicit checkpoints. Recorder's unused summary helper is now called from
  the actual callback, with raw CDR integrity preserved and ROS replay regression.
- Regression:221 focused and4 ROS tests pass; three dependency packages build.
- Rerun: two existing real/historical traces replayed, not qualified episodes.
  New simulation depends on unchanged preflight and workload headroom.
- Result: implementation/local regression evidence only. System closure remains
  OPEN; no physical attachment/lift/release or oracle PASS demonstrated.

Hardening result (2026-10-10): final targeted240, ROS/runner9 and manipulation
package43 pytest cases pass; colcon44 includes the wrapper. First malformed-truth
AttributeError regression failure is retained and corrected. Both final replays
pass integrity checks; guarded-motion-06 remains plugin-only evidence. Added
passive exact-consumer-sample logging, explicit engineering episode boundaries
and a post-place recording window; neither changes motion/safety decisions.
No system rerun permitted at the first RAM gate. Closure remains OPEN; independent
physical evidence, calibrated relative-motion quality limits and a finger-opening
witness are still required. No simulator or foreign process was signalled.


### Final controlled startup evidence — 2026-10-10

After changed-host read-only preflight passed, one NON_QUALIFYING controlled
attempt exited ABORTED_BOOTSTRAP_SAFETY on unreadable `/proc/96143/exe`. Only the
recorder started; Gazebo never launched and capture never began. Owned teardown:
zero survivors/errors; foreign signals NONE. Oracle/verifier UNSCORABLE. No retry:
runtime available RAM margin ~1.135 GB was below the previous incomplete arm run's
observed 1.304 GB decrease. Production Isaac RAM/VRAM calibration remains null.
Early-abort automatic reporting regression: 56 passed. Root cause remains OPEN;
physical attachment/lift/retention/release/placement unverified, all M1 counts
unchanged. Full report: `docs/m2/target_observation_20261008/VERIFICATION_REPORT.md`.
