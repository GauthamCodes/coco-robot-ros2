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
