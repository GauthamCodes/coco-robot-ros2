# COCO status

Updated: 2026-10-07. Milestone **M1**, checkpoints **M1.1–M1.7 infrastructure
implemented in part; qualified runtime/calibration and M1.8 blocked**.
M0 independently reviewed/passed and G0 passed per Gautham. No M0 reopened.
M1 remains incomplete; no qualified smoke or baseline and no M2 authorized.

Current session start/live verified input SHA: `10ba56210429d7e56e9fc605d879643dd3dda2d4`.
Branch: `coco-2.1-isaac-integration`; worktree initially clean.
Canonical repository and Downloads Master Plans byte-identical (SHA256
`e2d899d3b4f1b96a3958ace3833e32318985cc4edbcd05e12858ec91698aa03d`).
Previous session SHA entries below are historical, not this session's HEAD.
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
| Qualified cross-simulator reliability | NOT VERIFIED | M1 qualification/trace infrastructure implemented in part, runtime not validated; M4 benchmark not implemented |
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

## 2026-10-06 — M1 entry and host qualification stop

Milestone: M1 — Evaluation harness and failure taxonomy. Checkpoint: M1.1.
Exit criterion advanced: establish live provenance and identify host conditions
that must block a qualified batch before simulator launch.

Input HEAD: `3671059fd86d8cdd2a052283f6cad47e071e148b`; expected branch
`coco-2.1-isaac-integration`; worktree clean at entry. The committed Master Plan
and Downloads source are byte-identical; hashes and read-only worktree inventory
are in `m1/entry_20261006/host_inventory.json`. Gautham's session instruction
confirms the independent M0 pass and owner G0 pass. This records the owner's
confirmation; it does not fabricate a new independent review artifact or modify
the plan. Existing M0 evidence was read, not re-audited or replaced.

**Stop condition hit: host cannot currently be qualified for Isaac runs.**
Foreign Gazebo PID 147972 runs from `coco_search_ws`; foreign launch PID 147942
records to `coco_lab_runs/lab4/matrix/C2_green_nearest`. Foreign mission launch
PID 148693, Nav2 container PID 148738 and associated ROS nodes/recorder are also
active. No foreign processes were terminated or modified. Launching Isaac would
violate the explicit simultaneous-simulator prohibition. At 17:45:49 UTC the
1-minute load was 24.7739 on 12 logical CPUs. Load/RAM/VRAM are inventory facts,
not newly invented qualification cutoffs. No simulator or seed was launched.

Evidence: `m1/entry_20261006/host_inventory.json`, `env.json`, and
`m1/BASELINE.md`. Environment captured in the entry shell (ROS not sourced),
not represented as the future run environment. No DDS-named shared-memory
segments were found; orphan detection is not implemented or claimed complete.

Evidence label: **NOT VERIFIED** for M1 harness/baseline capabilities. This is a
recorded host blocker, not a completed or tested M1.1 preflight. No autonomy,
parameters, launch, oracle, seed policy, historical evidence or CI changed.
No M2 hypothesis, new invariant or parked idea added. No campaign started.

Next: Gautham makes the host available without foreign simulator/ROS workloads;
then resume M1.1, commit environment-grounded qualification thresholds, implement
and test the preflight (including no simulator launch), and continue M1.2–M1.8.
This is a stop-condition report, **not** the validated-harness overnight handoff.
No baseline execution command exists yet. M2 remains forbidden until all M1
exit criteria are satisfied and independently reviewed.

## 2026-10-06 — M1.1 non-runtime qualification implementation

Session input SHA `1bd501efb5ba444e61ae10ab5b107789f393a80a`, expected branch,
clean. Downloads and canonical plan byte-identical (SHA256
`e2d899d3b4f1b96a3958ace3833e32318985cc4edbcd05e12858ec91698aa03d`).
Owner explicitly directs non-runtime implementation to continue on a busy host.
M1.1 advances dirty-host rejection: read-only /proc identity and loaded ROS
library inspection, overwritten gz process titles, PID/start-time allowlist,
unknown DDS segments blocked, missing metrics/thresholds fail closed.
`eval/qualification.py`, `eval/host_policy.json`; local fixtures in
`m1/validation/m11_tests.log` (initial failure retained; corrected result in
`m11_tests_final.log`). IMPLEMENTED, remote CI/runtime not verified.
Measured historical foundation lower bounds: RAM 5098934272 bytes, total GPU
allocation 2585788416 bytes. They omit full fetch/ROS/MCAP overhead and are not
silently used as production limits. CPU ceiling 12 comes from logical capacity.
RAM/VRAM requirements remain calibration blockers, not invented thresholds.
Checkpoint incomplete until justified full-stack limits and runtime sampling
are validated. No simulator launched, no behavior changes.

## 2026-10-06 — M1.2 evaluator-only truth and launch graph checks

M1 / M1.2 advances /eval isolation and ground-truth capture. Input `84f9e98`.
Isaac adds only world-pose/dimension publications under `/eval/ground_truth`;
Gazebo read-only transport adapter publishes the same schema. Existing encoder,
IMU, manipulation and final wheel inputs unchanged. Graph checks reject any
non-/eval subscriber (including misleading `/eval_disguised` namespace) and
multiple/non-arbiter final wheel publishers. The launch test constructs a real
production TargetFinder and evaluator, then proves detection with a real illicit
subscriber negative control. Existing M0 full production graph tests are retained.
Local: two pure tests, one ROS launch test pass; new nine-package overlay build
passes. Evidence `m1/validation/m12_*`, `build.log`; IMPLEMENTED, remote CI and
both simulator truth streams not runtime verified. CI explicitly runs new launch
suite after build. Early import/context/launch-marker failures remain recorded.
M1.2 runtime validation remains open; no simulator or seed launched.

## 2026-10-06 — M1.3 bounded passive trace capture

M1 / M1.3 advances synchronized standard evidence and retained failure traces.
`eval/recorder.py` writes fixed-topic MCAP plus timestamped decoded events;
records source headers and receive simulation/wall stamps separately. Raw
costmap writes throttled to 1 wall Hz; no image/depth streams or camera assets.
Evaluator graph and lifecycle snapshots at 1 Hz. Service-event topic capture is
conditional on producer availability; missing action goal/result service events
are explicit trace gaps, not invented acknowledgements. `eval/topics.py` is the
fixed list. `eval/evidence.py` provides atomic manifests, streaming bag hashes,
outside-git storage, disk guard and conservative retention. Retention keeps all
failed/unknown/unqualified/interrupted runs and two qualified PASS controls.
8 GiB batch, 1 GiB run and 2 GiB filesystem reserve are committed storage
allocations justified against entry ~15 GiB availability, not invariant tuning.
Three local disk/hash/retention tests pass (`m1/validation/m13_tests.log`).
IMPLEMENTED; real MCAP replay and qualified runtime pending. No simulator run.

## 2026-10-06 — M1.4 observational perception candidate diagnostics

M1 / M1.4 advances candidate-level rejection/acceptance evidence. Both existing
perception nodes now emit `/perception/candidates` after their unchanged decision
and outputs. One JSON String per selected-colour component, including small
rejected blobs, records source stamp/frame, label/colour, visible-surface 3D
centroid/extents, point counts, depth statistics, range/bearing, image-edge flag,
actual selected acceptance/rejection and separate recomputed geometry reason.
Missing geometry is explicit null; visible surface is not relabeled as target
center/full dimensions. Diagnostic failures cannot change the original result.
Existing gates, ordering, thresholds, task inputs and output state unchanged.
Six new functional tests; complete package validation in `m1/validation/m14_*`.
Initial root-cwd lint run and own new-file style failures retained, corrected
without broad source refactoring. IMPLEMENTED; simulator overhead not measured.

## 2026-10-06 — M1.5 Nav2 server logs and callback timing

M1 / M1.5 advances server-side action/lifecycle and executive timing evidence.
Nav2's shipped SimpleActionServer debug logs include "Received request for goal
acceptance" and "Receiving a new goal". New launch option changes logging only;
normal default remains info. The evaluator runner selects debug and captures
rosout plus server status/UUID streams and 1 Hz lifecycle replies. No Nav2
parameter/controller/timeout or action semantics changed. Server logs and UUID
status are separate observations; an unobserved request/response is never
invented from a client request. Exact goal/result service payloads remain a gap
when installed producers lack service introspection.
Executive callbacks/future callbacks publish observational wall durations and
source sim times on `/diagnostics/mission_callbacks`; callback returns and
exceptions preserved, logging errors cannot affect them. Sole wheel authority
unchanged; existing publisher-inventory test adds only that diagnostic topic.
42 focused timing/executive tests pass: `m1/validation/m15_callbacks_corrected.log`.
`eval/tracing.py` probes ros2_tracing and can own a unique LTTng UST session for
Dev 6/7, without destroying other sessions. This host has lttng but no ros2 trace
CLI (`tracing_availability.json`); executor timing is NOT VERIFIED, no timing
trace claimed. IMPLEMENTED; qualified server goal/lifecycle runtime pending.

## 2026-10-06 — M1.6 offline invariant engine and supported historical replay

M1 / M1.6 advances first-violation analysis, fixture coverage and explicit gaps.
`eval/invariants.py` implements all I01–I25 as tri-state checks on normalized
measurements; `analyzer.py` orders source sim timestamps, preserves receive order,
writes stage/stamp and a centered ten-second context. Missing evidence/limits
are unknown, never successful or forcibly classified. 25 passing, 25 failing,
25 missing-evidence fixtures plus order/context/calibration checks pass (77).
`calibration.py` derives P99 ceilings/P1 floors from qualified oracle-PASS Dev
controls with explicitly justified margins and trace hashes; held-out inputs
rejected. Production thresholds remain null because qualified controls do not
exist; no arbitrary invariant limits committed. Existing oracle/physical gates
and stage budgets retained where already defined.
`normalize.py` currently derives physical finiteness, I19 disturbance, graph
sole-publisher evidence and explicit planner "Start occupied" observations.
Other catalog raw-trace derivations remain analyzer work, not a complete M1.6.
Historical replay proves I19 is observed for coco23 Gazebo6 at 61.726 sim s and
Isaac6 at 62.0583365699 sim s. These are the first supported displacement breaches,
not proven earliest causal divergence among missing invariants, and are not
qualified baseline evidence. `m1/validation/historical_*.json`, `m16_*`.
IMPLEMENTED engine; full trace-to-catalog coverage/calibration remains pending.


## 2026-10-07 — M1.7 runner implementation and runtime-gate stop

Input SHA `ab45dc5034cecae364ad8909499498a73dd6597d`. IMPLEMENTED, not a
completed/validated M1.7: `eval/bin/eval`, `cli.py`, `batch.py` provide sequential
locked batches, preflight before any launch, append-only crash attempts, saved
PID/start-time and process-group reconciliation, recorder-first/last lifecycle,
1 Hz host metrics/RTF, disk gates, preserved failures, single oracle/analyzer and
qualified-only Dev/Test A summaries. Large campaigns require fresh validated
smoke proof. Dirty-host and mid-run resource tests explicitly assert launch
blocking/unqualification; synthetic bag placeholders are not MCAP evidence.
Corrupt raw traces fail closed and processing exceptions preserve an interrupted
manifest. Standard evidence dirs include blocked attempts; counts distinguish
blocked inventories from simulated runs.

Supporting hardening: explicit UID/comm/argv allowlist for installed background
services; unknown unreadable userspace remains blocked. Kernel threads excluded
only via PF_KTHREAD. Recorder samples TF/lifecycle and writes a bounded clock
cache. Additional raw derivations cover source-stamped clock/TF/AMCL/odom,
lifecycle, correlated acknowledged UUID status, perception timestamps/width and
MoveIt terminal status. Null calibration and missing command/manipulation/
costmap/progress evidence remain explicit analyzer work; no earliest causal
classification or physical-success proof claimed. Oracle authority coverage
remains fail-closed. No control/source/parameter/physics/timeout/retry changes.

Evidence: `m1/validation/eval_verified.log` (155 pass), `ros_final.log` (2 pass,
actual MCAP replay plus isolation launch negative control), `regressions/*.xml`
(1,992 robot-package tests pass, zero failures), `build.log` (9 packages built).
CI dependencies include MCAP/launch testing, tests configured; remote CI not run.
Earlier failed invocations preserved with corrected results. New perception
logging field rerun in `perception_final.log` (145 pass).

Runtime gate STOP: `m1/validation/runtime_preflight_final.json` records foreign
Gazebo/ROS in coco_search_ws (launch183965, sim183995, executive184811), daemon8877,
unreadable process6293 and load1=22.720703125 >12. Isaac cannot qualify; no simulator
launched, no foreign PID killed or worktree modified. Even after busy host clears,
full-stack RAM/VRAM thresholds remain uncalibrated and refuse launch. M0 foundation
lower bounds cannot establish full fetch/ROS/MCAP requirements. No arbitrary
threshold substituted. Qualified controls/calibration and catalog raw derivations
are additional unfinished harness work, not merely an overnight campaign.

See `m1/BASELINE.md` and `../eval/README.md` for exact gaps, evidence schema,
retention, guarded commands and baseline state. This is not a validated overnight
handoff. M1 exit criteria remain open; M2 must not start. No hypotheses newly
confirmed/rejected, no autonomy repair or IDEAS additions.

## 2026-10-07 — M1.1 fresh host audit and process classifier correction

Input `10ba56210429d7e56e9fc605d879643dd3dda2d4`, expected branch, clean.
Approved Downloads plan byte-identical. M1 / M1.1 advances dirty-host
blocking without false simulator detection. Diagnostic shell command text is
no longer classified as an executable; loaded ROS libraries still block.
Root fwupd/anacron are explicitly allowed by UID/comm/argv after read-only ps
and dpkg package ownership checks. No blanket unreadable-process exemption.
16 targeted fixtures pass locally; IMPLEMENTED, remote CI not verified.
Evidence: `m1/validation/session_20261007/m11_tests.log`, initial/corrected
preflight JSON. Fresh corrected host has no foreign robotics process or DDS
segment rejection; old foreign workloads are gone. Qualification still refuses
Isaac solely because full-stack RAM/VRAM requirements are null. CPU ceiling
and resource limits were not relaxed. No simulator launched or PID killed.
M1.1 remains incomplete pending actual resource calibration; other missing
non-runtime evidence work continues within M1. No M2 or IDEAS additions.
