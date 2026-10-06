# COCO status

Updated: 2026-10-06. Milestone: M0; checkpoint: manipulation observation boundary and ground-truth isolation. M1 has not started.

Starting verified HEAD for this checkpoint: `af8921a57006a3f5110a58316dc0e5b8dbfb652a`.
Implementation checkpoint: `e4f58dad27e7506a049f0f604514eef44a8fc6bb`.
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

## Current checkpoint status

Ground-truth isolation is IMPLEMENTED with locally passing automated graph and
regression evidence. CI and full physical simulator behavior are NOT VERIFIED.
The integrity stop condition is resolved for the committed active architecture;
this is not completion of M0 or authorization to start M1.

- Gazebo truth and Isaac world/object exports are evaluator-only under `/eval`.
- Shared autonomy uses normal encoder-derived odometry/TF, IMU, joints and RGB-D.
- Manipulation attachment/lift/release/physical placement fails closed: independent
  object-motion observations are unavailable. Historical fetch completion cannot
  be claimed for this compliant checkpoint. Actuator acknowledgment is not
  physical retention proof.
- Isaac yaw feedback uses the exact existing ideal simulated IMU gyro sample;
  no raw-world pose or velocity enters normal odometry. Fidelity remains M3.
- Existing arbiter semantics remain; direct-wheel publishers/remaps outside it
  are rejected or use its existing inputs. Legacy truth climb/teleport/demo entry
  points are explicitly unavailable.
- Full contract, classified source map and limitations:
  `docs/m0/MANIPULATION_OBSERVATION.md`.

## Verification and evidence

Fresh nine-package build passed. Relevant regressions: **1984 passed, zero
failures/skips**. Focused graph/executive checks: 50 passed; encoder/Isaac checks:
32 passed. Logs and contradictory-truth production-node ROS graphs:
`docs/m0/gti_remediation/`. Initial failed tests are retained beside final logs.
No full simulator runs, benchmark campaigns, held-out inspection or remote CI.
Baseline audit and historical violations: `docs/m0/AUDIT.md`,
`STOP_CONDITION_INVESTIGATION.md`, `GROUND_TRUTH_ISOLATION.md`, `gti/`.
These historical files retain their original findings with appended follow-up.

## Remaining M0 and plan boundaries

M0.2 control-file capability inventory and IDEAS, M0.3 manifest, M0.4 oracle and
back-check, M0.5 seed policy and M0.6 hygiene audit remain incomplete. No broad M0
work was performed. Known dev seeds remain dev; held-out/reserve ranges have not
been committed and no seeds were run here. M3 retains odometry/IMU/alignment
fidelity, C++ arbiter, safety case, Docker, CI expansion and observability.
A future legitimate object-motion observation needs explicit milestone scope;
none is silently assigned by this checkpoint. No owner decision is needed to
keep the approved fail-closed limitation in force.

Exactly one next action according to MASTER_PLAN: resume **M0.2 control files**
and capability inventory with this checkpoint's evidence and limitations.
Do not start M1.
