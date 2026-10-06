# COCO status

Updated: 2026-10-06. Milestone **M0**, checkpoint **M0.2–M0.6 execution complete; independent review pending**.
M1 has not started. Independent milestone review and owner G0 decision pending.

Session start SHA: `c45d224a9cbcfd10b9661a40c4df7866febdce38`.
Checkpoint input/current verified SHA: `33354011c9d76857b3c66b12e14176633b1346ee`.
Branch: `coco-2.1-isaac-integration`; worktree initially clean.
Current SHA and worktree state (live): **`python3 eval/status.py`**. It prints
the true full HEAD SHA, branch and cleanliness before this committed status.
Equivalent SHA command: `git rev-parse HEAD`. A committed file cannot
literally contain its own commit hash; checkpoint entries record their input SHA,
and the final report records the exact resulting HEAD. Verify cleanliness with
`git status --porcelain=v1`. Do not substitute a prior implementation SHA for HEAD.

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

## Capability inventory

Each capability has exactly one Master Plan label. Local tests do not establish
CI-dependent TESTED; historical runtime is explicitly separated from current behavior.

| Capability | Evidence label | Evidence / limitation |
| --- | --- | --- |
| Shared mission/search state machine and rejected-search retreat | IMPLEMENTED | `coco_mission/scripts/mission_states.py`; local regression in `m0/gti_remediation/coco_mission_regression.log` |
| Arbiter sole final wheel authority | IMPLEMENTED | `m0/gti_remediation/`; production-node graph tests; semantics preserved |
| Encoder normal odometry / evaluator-only truth isolation | IMPLEMENTED | `m0/MANIPULATION_OBSERVATION.md`; encoder provenance and production graph tests; no full compliant simulator mission |
| RGB-D perception and validation gates | IMPLEMENTED | `coco_perception/`; local 139-test suite in remediation evidence |
| Arm IK / MoveIt trajectory interface | IMPLEMENTED | `coco_moveit_config/`; local 32-test suite; frozen |
| Historical fetch under current qualification rules | NOT VERIFIED | `data/isaac_fetch/coco23/README.md`, `coco24/README.md`; unqualified historical observations, not a qualified current capability or reliability result |
| Current physical manipulation completion | NOT VERIFIED | `m0/MANIPULATION_OBSERVATION.md`; independent object observation unavailable; attachment/lift/release/placement fail closed |
| Qualified cross-simulator reliability | NOT VERIFIED | M1 qualification/trace harness and M4 benchmark not implemented |
| Single physical-success oracle | IMPLEMENTED | `SUCCESS_DEFINITION.md`; `m0/ORACLE_BACKCHECK.md`; 43 oracle/environment/adapter tests and 6 seed tests locally pass; CI configured, execution unverified |
| Environment capture | IMPLEMENTED | `../eval/environment.py`; `m0/control_plane/environment/env.json`; executed without simulator launch |
| Held-out seed governance | IMPLEMENTED | `../eval/seeds.yaml`; `m0/control_plane/seed_tests.log`; disjoint pools, never run |

## Open failure classes and blockers

| Class | State | Evidence |
| --- | --- | --- |
| Ground-truth autonomy dependency | Resolved by approved isolation amendment; preserve boundary | `m0/GROUND_TRUTH_ISOLATION.md`, `m0/MANIPULATION_OBSERVATION.md` |
| Stale mission-view reason inventory test failure | Resolved | `m0/STOP_CONDITION_INVESTIGATION.md` |
| Legitimate manipulation observation unavailable | Explicit capability limitation; no bypass and no new M0 work | `m0/MANIPULATION_OBSERVATION.md` |
| Historical far-region descent/contact and ODE crash | Open; later causal evaluation, no M0 investigation | `data/isaac_fetch/coco23/README.md`, `coco24/README.md` |
| Historical far-region Nav2 acknowledgment / perception geometry rejection | Open; later milestones | `data/isaac_fetch/coco24/README.md`, `data/isaac_fetch/coco25/` |
| Observer idle-command ordering ambiguity | Open evidence ambiguity; oracle must not infer a clean arbiter from mission success | `data/isaac_fetch/coco23/gazebo_seed9_idle_sample.json` |
| M0 control-plane implementation | No unresolved implementation blocker; review/G0 pending | `m0/HYGIENE_AUDIT.md`, `m0/ORACLE_BACKCHECK.md` |

## Seed policy

`eval/seeds.yaml` is canonical. All previously used seeds are Dev permanently,
including 0–9/P03D, generated layouts 0–9999, and fixture seeds 12345, 99999,
2147483647. Thirty fresh Dev IDs: **10000–10029**.
Held-out Test A: **1000000–1000059 inclusive (60)**.
Untouched M4 reserve/Test B: **2000000–2000059 inclusive (60)**.
No held-out/reserve layouts generated or run. Never debug/tune with those IDs;
inspection for fixes permanently promotes a seed to Dev and requires replacement.
M0 creates 60-seed pools; later campaigns pre-register the plan's 30 and 30–50
subsets before looking at layouts/outcomes. No new plan amendment.

## Checkpoint evidence

- M0.1 audit and fresh 9-package build counts: `m0/AUDIT.md`.
- Isolation follow-up fresh build 9/9; **1984 passed, 0 failed, 0 skipped**:
  `m0/MANIPULATION_OBSERVATION.md`, `m0/gti_remediation/`.
- Session entry and plan comparison: `m0/CONTROL_PLANE.md`.
- CI execution remains NOT VERIFIED; no simulation campaign in this session.

Next: independent fresh M0 review, then owner G0 decision. **M0 is not formally
closed until review passes.** Do not start M1 in this session. Historical oracle coverage: 16 inspected,
13 scorable (5 PASS / 8 FAIL), 3 UNSCORABLE; one definite COMPLETE/FAIL disagreement
(M2.3 Gazebo seed7). Evidence: `m0/ORACLE_BACKCHECK.md`.
No M1, M2 reliability, M3 cleanup or robot behavior work authorized here.

## M0.6 exit evidence and remaining gates

Fresh isolated build **9/9**; complete package suites **1984 passed / 0 failed /
0 skipped**; evaluator suite **49 passed / 0 failed / 0 skipped**; total **2033**.
`m0/control_plane/clean_build.log`, `test_counts.json`, `regressions/` contain
logs/XML and current Gazebo/Isaac production-node ROS graphs. Existing isolation
and fail-closed tests pass unchanged. Simulator bringup, expensive campaigns and
remote CI were not run. No robot source, launch, parameters, gains or historical
`docs/data` changed relative to this session's starting SHA.

M0.6: **18 findings**, **2 blocks M1 resolved**, **10 M3 cleanup deferred**,
**6 historical, keep**. No unresolved M0 stop condition or new plan amendment.
See `m0/HYGIENE_AUDIT.md` and full tracked-text inventory. Current-authority
banners prevent root historical roadmap instructions from superseding this plan.
New eval CI dependencies/coverage are pinned as explicit requirements, while
broader CI/deployment work remains M3. Manipulation stays fail closed wherever
legitimate independent object observation is missing; truth remains evaluator-only.

All M0 implementation checkpoints are ready for review. Independent review and
Gautham's G0 remain pending; this session does not pass either gate.
