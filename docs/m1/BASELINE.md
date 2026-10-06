# M1 baseline — implementation checkpoint, campaign not started

2026-10-07. Labels: **IMPLEMENTED** infrastructure; **NOT VERIFIED** qualified
runtime and baseline. Session start: `1bd501efb5ba444e61ae10ab5b107789f393a80a`.
Branch `coco-2.1-isaac-integration`, initially clean. Canonical and Downloads
Master Plan byte-identical; no plan or seed changes. M0 remains passed.

## Current checkpoint status

| Checkpoint | Implementation/evidence | Remaining validation or implementation |
| --- | --- | --- |
| M1.1 | Read-only inventory, explicit allowlist, fail-closed qualification, 1 Hz runtime metrics; synthetic dirty/mid-run/crash fixtures | Full-stack RAM/VRAM requirements are null; qualification refuses launch |
| M1.2 | Gazebo/Isaac evaluator-only truth exports; live ROS isolation launch test with negative control | Qualified full simulator graph/truth coverage on both backends; remote CI execution |
| M1.3 | Fixed-topic MCAP recorder, hashes, storage caps/retention; actual simulator-free ROS→MCAP replay | Full mission trace coverage, including Nav2 goal/result service events |
| M1.4 | Candidate diagnostics after existing decisions, no threshold changes; 145 perception tests | Qualified simulator candidate evidence |
| M1.5 | Server debug logging/lifecycle snapshots, UUID status, callback durations, optional owned LTTng session | Exact service receipt/acceptance correlation, executor trace validation |
| M1.6 | I01–I25 tri-state engine; pass/fail/missing fixtures for each; supported historical replay | Raw derivations listed below and qualified-control calibration |
| M1.7 | Sequential locked append-only runner, preflight gates, crash reconciliation, standard evidence, single oracle/analyzer, summaries | Qualified smoke and full oracle command-authority coverage; not a validated harness |
| M1.8 | Executable campaign definitions preregistered | All 140 initial baseline runs remain; no campaign started |

Local tests: 1,992 robot-package tests pass; latest evaluator suite 155 pass;
two ROS integration tests pass. Fresh isolated overlay build: 9 packages pass.
See [validation](validation/), especially `checkpoint_regressions.log`,
`regressions/*.xml`, `eval_verified.log`, `ros_final.log`, `build.log`.
These are local tests, not a claim of executed remote CI. Earlier failed test
invocations are retained alongside corrected passing evidence.

## Qualification blocker

[runtime_preflight_final.json](validation/runtime_preflight_final.json) preserves
live process identities/resource inventory and every rejection reason. Foreign
Gazebo launch PID 183965, simulator PID 183995, mission PID 184811 and related
ROS nodes belong to another workspace; ROS daemon PID 8877 is also foreign.
Load1 22.720703125 exceeds 12. An unlisted process PID 6293 has unreadable `/proc`
metadata. No processes were killed. No simulator was launched by this session.
Earlier snapshots remain in `validation/runtime_preflight*.json` and the entry
inventory below; PIDs are snapshot evidence, not instructions to kill them.

`eval/host_policy.json` documents why historical foundation RSS/VRAM lower bounds
cannot justify full-stack requirements. RAM/VRAM preflight and runtime limits
remain null and block launch even on an otherwise idle host. Thresholds were not
invented to get a run accepted. Successful-control invariant limits likewise
remain null in `eval/thresholds.json`; calibration requires qualified oracle-PASS
Dev controls with explicit margins/provenance. Current M0 fail-closed manipulation
is preserved, so complete physical-success controls are not established.

## Campaign registration and results

| Campaign file under `eval/campaigns/` | Definition | Planned | Executed |
| --- | --- | ---: | ---: |
| `m1_smoke.yaml` | Dev 5/8 once per backend, sequential | 4 | 0 |
| `m1_determinism.yaml` | Dev 6/7 ×3, controls 5/8 ×2, both backends | 20 | 0 |
| `m1_breadth.yaml` | Dev 10000–10029 once per backend | 60 | 0 |
| `m1_test_a.yaml` | Preregistered untouched Test A 1000000–1000029 once per backend | 60 | 0 |

Qualified simulated runs **0**; unqualified simulated runs **0**. Rejected
preflight inventories are not simulated runs or evaluation denominators.
Qualified smoke **not passed**; harness **not validated before M1.8**.
Determinism verdicts: pending. Dev Pareto: unavailable for Gazebo and Isaac.
Test A: n=0 on both backends; completion rates/Wilson 95% intervals undefined.
UNCLASSIFIED: no scored baseline failures; fraction undefined, exit criterion
not met. No Test A layout or individual held-out trace has been opened.
Reserve 2000000–2000059 remains untouched.

Historical Dev replay finds I19 nonrequested displacement for coco23 Gazebo6 at
61.726 sim s and Isaac6 at 62.0583365699 sim s. Artifacts:
`validation/historical_gazebo6.json`, `validation/historical_isaac6.json`.
These are first **supported** breaches, not proven earliest causal divergence
among unobserved invariants, and not qualified current baseline evidence.

## Analyzer and oracle gaps

Raw derivations cover clock, sampled TF availability/age, planar AMCL/odometry
truth comparison with bracketed translation interpolation, latest lifecycle
observations, acknowledged UUID/server status correlation, perception timestamps
and projected width, MoveIt terminal status, displacement and graph authority.
Missing evidence stays unknown. Outstanding work includes complete command
lineage/arbiter latency (I06), command-motion delay (I07), costmap/plan geometry and
latency (I11–I14), accepted-target identity/position (I17–I18), joint tracking
(I20), attachment/lift/carry/release ordering (I21–I23), roll/pitch (I24), and
stage-progress/budget extraction (I25). I01 resource/RTF facts still need complete
analyzer ingestion. Known passes alone cannot certify the whole catalog.

Installed Nav2 does not currently publish action service introspection. Requested
service-event topics remain explicit missing streams; debug receipt logs and
status UUIDs cannot replace missing goal/result payloads. Host has LTTng but no
`ros2 trace` CLI; executor timing remains unverified. Oracle adapter fails closed
on missing correlated command-authority coverage rather than granting PASS.
No independent physical-outcome comparison has yet been performed; no oracle
agreement/disagreement claim is possible without a qualified run.

## Remaining execution path

Exact guarded commands and evidence/retention contract are in [eval README](../../eval/README.md).
Finish the listed raw derivations and justify resource limits; obtain qualified
controls/calibration without changing autonomy; run/inspect the four-run Dev smoke;
validate both backends. Only then run the committed baseline campaigns. Any new
breadth failure needs additional qualified Dev repetitions to assign a determinism
verdict. Qualified-only aggregates use Wilson score intervals with z=1.96; unknown
oracle outcomes suppress reported rates/intervals and remain visible. Pareto
counts qualified Dev oracle failures; no held-out debugging or tuning.

This is **not** a validated overnight handoff and M1 is **not complete**. The
Isaac host-qualification stop condition is hit at the runtime gate. Infrastructure
progress continued despite the busy host. No autonomy repair or M2 work occurred.

## Preserved previous M1 entry report

# Previous entry — not started

2026-10-06. Evidence label: **NOT VERIFIED**.
M1.1 stopped at entry because the current host cannot qualify for Isaac while
foreign Gazebo/ROS workloads run. M1.1–M1.8 are incomplete; no evaluation
harness, qualified smoke batch or baseline measurement is claimed.

Entry SHA: `3671059fd86d8cdd2a052283f6cad47e071e148b`, branch
`coco-2.1-isaac-integration`, initially clean. Master Plan and approved Downloads
source compare byte-identical. M0 review/G0 pass confirmed by Gautham's session
instruction; no M0 changes made.

## Host blocker and evidence

[Host inventory](entry_20261006/host_inventory.json) records UTC time, live SHA,
process argv/identity, read-only worktree inventory, plan hashes, CPU/load,
RAM/VRAM, disk space and DDS-named segments.
[Environment inventory](entry_20261006/env.json) uses the existing M0 capture
script in the entry shell; ROS is unsourced. It is not a qualified run env.json.

Foreign Gazebo PID 147972 runs a world from `coco_search_ws`. Launch PID 147942
records to `coco_lab_runs/lab4/matrix/C2_green_nearest`; mission PID 148693 and
Nav2 PID 148738 plus associated ROS nodes and recorder are active. No unrelated
processes or worktrees were modified. No simulator was launched by this session.
Isaac cannot start concurrently with that Gazebo. Resource numbers are inventory
only: qualification thresholds, resource derivation and orphan-DDS ownership
checks have not yet been implemented. Absence of DDS-named segments in this
snapshot is not proof of a complete orphan detector.

## Required remaining campaign

Definitions below restate MASTER_PLAN, not executable runner configuration.
`eval/seeds.yaml` remains authoritative and unchanged.

| Part | Seeds | Repeats per backend | Required runs | Recorded runs |
| --- | --- | --- | ---: | ---: |
| Determinism failures | Dev 6, 7 | 3 | 12 | 0 |
| Determinism controls | Dev 5, 8 | 2 | 8 | 0 |
| Breadth | New Dev 10000–10029 | 1 | 60 | 0 |
| Held-out before | 30 of Test A 1000000–1000059, subset to pre-register before use | 1 | 60 | 0 |

Both Gazebo and Isaac are required, sequentially. Total: 140 initial baseline
runs, plus any additional Dev reproduction required to assign every failing seed
a determinism verdict. M4 reserve 2000000–2000059 remains untouched.
No held-out layouts were generated, runs performed or individual traces opened.

Qualified simulated runs: **0**. Unqualified simulated runs: **0**.
Blocked host inventory: **1**; not an episode or an evaluation denominator.
Determinism: not measured. Dev failure Pareto: unavailable on both backends.
Test A completion rates and Wilson 95% intervals: unavailable, n=0 on both.
UNCLASSIFIED count and fraction: unavailable; no failures scored.
First-divergence labels: unavailable; analyzer not implemented.

## Remaining validation and methodology

All M1 exit criteria remain open. Before any large batch: implement the harness,
run targeted tests, one small qualified smoke batch, inspect Dev evidence,
correct harness defects, then checkpoint-level validation. Thresholds must be
justified from existing environment/resource evidence and successful controls;
none are inferred from this loaded snapshot. No behavior tuning is authorized.

Required evidence layout remains `manifest.json`, `env.json`, `host_metrics.csv`,
`logs/`, `bag/`, `oracle.json`, `analysis.json`. MCAP bags remain outside git,
hashed in the manifest; retain every failure/unqualified run and two controls
per batch, with committed retention/disk protection before capture. This entry
inventory is not a standard run directory and must not be counted as one.

Use the single `eval/oracle.py`; mission verdict stays separate. Offline invariant
analysis must name the first violation, mission stage, simulation timestamp and
10-second context, with passing/failing fixtures for every catalog invariant.
Historical failures may be replayed only where data supports attribution;
missing evidence remains an analyzer gap. No new invariant is claimed here.

Deterministic/intermittent/not-reproduced verdicts must follow repeated qualified
Dev outcomes. Pareto tables use qualified Dev failures per backend. Test A uses
only qualified aggregate physical-completion counts with Wilson 95% intervals,
listing exclusions separately; individual held-out traces stay closed for
debugging. No rate or interval can be reported before those counts exist.

Resume M1.1 after host availability is restored. This is a stop-condition report,
not an overnight handoff: there is no validated resumable runner or exact
baseline command yet. Do not start M2.
