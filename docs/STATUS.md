# COCO status

Updated: 2026-10-06. Milestone: M0; checkpoint: approved ground-truth isolation remediation. M1 has not started.

Starting verified HEAD: `74875c7aca2fcb5a6d3020438588a39b8855c22b`.
Branch: `coco-2.1-isaac-integration`.
Worktree: `/home/gautham/coco-isaac-21`; initially clean.
Current commit: resolve with `git rev-parse HEAD` (a commit cannot contain its own SHA).

## Plan-change history

### 2026-10-06 — Ground-truth isolation before M1 (approved by Gautham)

> Ground-truth isolation is required before M1. Existing autonomy consumes simulator world-pose odometry outside /eval, which contradicts the integrity rules. This must be remediated before compliant evaluation begins. The remediation will replace autonomy consumption of simulator world pose with non-privileged wheel/encoder-derived state using the existing common ROS architecture. Simulator ground truth remains available only to /eval. M3.1 remains the formal Isaac fidelity milestone for wheel-encoder odometry, fidelity ablation and related work.

Reason: Master Plan integrity rule 1 conflicts with existing mission/ramp/manipulation world-pose consumers and Isaac's simulator-derived normal odometry/TF. M0's behavior freeze prevented correction without this explicit amendment. Producer and consumer evidence forcing the amendment: `docs/m0/STOP_CONDITION_INVESTIGATION.md`, sections “Outcome B: simulator ground truth” and “Master Plan consistency and owner decision”; original finding retained in `docs/m0/AUDIT.md`. Milestone structure and M3 purpose are unchanged.

### 2026-10-06 — All privileged autonomy inputs and fail-closed manipulation (approved by Gautham)

> Ground-truth isolation must cover not only simulator world-pose odometry but every simulator-derived value that directly supplies autonomy with privileged state. This includes manipulation/attachment/lift/release truth and any simulator-state feedback used by autonomy where that feedback is not equivalent to a legitimate simulated robot sensor. Before M1, such dependencies must be replaced by legitimate robot-observable state or made explicitly fail-closed. Simulator ground truth remains evaluator-only under /eval. M3 retains its planned fidelity work for odometry, IMU and alignment.

Evidence forcing this amendment: `docs/m0/GROUND_TRUTH_ISOLATION.md` and
`docs/m0/gti/grasp_graph.json` at `af8921a57006a3f5110a58316dc0e5b8dbfb652a`:
Gazebo direct object-pose queries and Isaac height exports gate manipulation;
Isaac world state also feeds normal odometry/TF and yaw control. This amendment
explicitly authorizes unavailable manipulation observations to fail closed.
This session starts at that SHA, on the expected branch and worktree, clean.
Checkpoint: M0 manipulation observation boundary and ground-truth isolation.
Exit: all identified privileged paths removed/replaced/fail-closed with tests.
M1 remains unstarted; M3 structure and fidelity scope remain unchanged.

## Open status and evidence

- Privileged autonomy state: unresolved; stopped at missing independent object-motion observation. Full dependency map and boundary: `docs/m0/GROUND_TRUTH_ISOLATION.md`. No production remediation implemented.
- Prior telemetry inventory failure: locally corrected; evidence in stop-condition investigation. CI NOT VERIFIED.
- Baseline capabilities and clean-build counts: `docs/m0/AUDIT.md`; historical runtime evidence remains unchanged. No new runtime capability claims.
- M0.2 control files, M0.3 manifest, M0.4 oracle/back-check, M0.5 seed policy and M0.6 audit remain incomplete; this file is not completion of those checkpoints.
- Seed policy: existing seeds are dev only; fresh held-out/reserve ranges have not yet been committed. No episodes run in this session.

## Isolation session verification

Production GraspServer ROS graph inspected with both backend parameters: world
odometry remains subscribed; Isaac also subscribes to simulator object height.
Raw graph: `docs/m0/gti/grasp_graph.json`. No simulator or mission run performed.
Focused checks: 65 passed. Relevant regressions: mission 365, ramp 236,
perception 139, manipulation 28, simulation 228, teleop/arbiter 78:
**1074 passed, 0 failed, 0 skipped**. Logs: `docs/m0/gti/*_regression.log`.
Local verification only; CI NOT VERIFIED. Existing overlay reused; no new clean
build claimed. No behavior or gate changes; no command path introduced.

Missing input: independently observed target rise/resting height for attachment,
lift and release checks. Encoders/IMU do not provide it; current RGB-D contract
provides a framing-dependent point and fixed grasp height. Replacing those gates
requires an explicitly scoped sensor-based observation contract or an approved
fail-closed limitation. M3.1 fidelity remains deferred; this new manipulation gap
is not silently assigned to M3. Integrity stop condition remains unresolved.

Exactly one next action: Gautham resolves the documented manipulation observation
boundary through Master Plan change control before isolation remediation resumes.
