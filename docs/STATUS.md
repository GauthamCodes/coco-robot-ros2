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

## Open status and evidence

- Privileged autonomy state: unresolved; investigation/remediation in progress.
- Prior telemetry inventory failure: locally corrected; evidence in stop-condition investigation. CI NOT VERIFIED.
- Baseline capabilities and clean-build counts: `docs/m0/AUDIT.md`; historical runtime evidence remains unchanged. No new runtime capability claims.
- M0.2 control files, M0.3 manifest, M0.4 oracle/back-check, M0.5 seed policy and M0.6 audit remain incomplete; this file is not completion of those checkpoints.
- Seed policy: existing seeds are dev only; fresh held-out/reserve ranges have not yet been committed. No episodes run in this session.

Next action: complete the approved isolation remediation, or record the exact sensor/architecture blocker.
