# M1 baseline — partial infrastructure, campaign not started

2026-10-07. **IMPLEMENTED / locally verified** means infrastructure evidence;
**NOT VERIFIED** means qualified simulator evidence is absent. Session start
`10ba56210429d7e56e9fc605d879643dd3dda2d4`, branch
`coco-2.1-isaac-integration`, initially clean. Downloads and canonical Master
Plans byte-identical. Plan, campaigns, seed policy and autonomy behavior unchanged.

## Latest qualification-session inspection

Entry `ceeb914923f7629b4830d58fd3b47279044b2024`, clean expected branch.
[Forensic stop report](validation/qualification_20261007/REPORT.md): domain66
ROS daemon provenance is another COCO search/lab workspace; not stale M1-owned.
Its owner must release it. Clean M1 environment (domain82) rejects the same
process plus null RAM/VRAM requirements. No classification defect found, no
signal or simulation. Load1 3.8604, RAM available9.69GB, VRAM free5.64GB; readings
do not establish production limits. Calibration dependencies audited; no code
changes, tests rerun, smoke or baseline. All statuses below remain partial.

## Current checkpoint status

| Checkpoint | Progress this session | Still incomplete |
| --- | --- | --- |
| M1.1 | Fresh process inventories, diagnostic-shell classification, owned/opposite-backend blocking, 1 Hz host/clock sampling | Justified full-stack RAM/VRAM limits; qualified runtime |
| M1.2 | Actual ROS isolation test including negative control; evaluator-only truth preserved | Qualified full graph/truth coverage on both simulators |
| M1.3 | Actual arbiter lineage, reliable final-command capture, explicit clocks, real MCAP UUID/stamp replay, bag integrity gate | Complete qualified mission/action trace coverage |
| M1.4 | Requested/detected diagnostic colour semantics, six targeted tests | Qualified simulator candidate evidence/overhead |
| M1.5 | Native owned-PID UST capture: 22 paired callbacks, 94 executor events, zero unmatched | Mission/Nav2 executor timing; exact goal receipt/acceptance/service payload coverage |
| M1.6 | Additional raw command, resource, costmap, target, joint, lift/carry/release and tilt measurements; conservative missing-field coverage | Raw catalog witnesses listed below and successful-control thresholds |
| M1.7 | Content-bound resumability/smoke gate, persistent integrity stops, teardown checks, held-out protections | Trustworthy qualified smoke; not a validated harness |
| M1.8 | Preregistered definitions retained | All 140 initial baseline runs |

Evidence root: [session_20261007](validation/session_20261007/). Latest evaluator
suite **176 passed** (`eval_tests_checkpoint_final.log`); affected package tests
custom_teleop **78**, coco_sim **237** pass, with **2/2** packages built.
Authority regression **38** and candidate diagnostics **6** passed (overlap with
package tests). Full ROS suite **4** items passed before the teardown refinement;
corrected isolation/recorder subset **2** passed, then clock replay **1** passed.
Native tracing and authority tests passed independently. These are local checks,
not remote CI or simulator success. Earlier failed invocations remain preserved.
Prior full-suite/build reports remain historical evidence below, not fresh reruns.

## Qualification and calibration blockers

Latest full inventory:
[preflight_checkpoint_isaac.json](validation/session_20261007/preflight_checkpoint_isaac.json).
Same inventory's Gazebo verdict: `preflight_checkpoint_gazebo.json`.
Both reject foreign ROS daemon PID **260322**, start ticks **8029900**, domain
**66**, CycloneDDS, plus null RAM/VRAM requirements. Load1 **2.1513671875** against
unchanged limit **12**; available RAM **9711841280 bytes**; GPU free
**5649727488 / 6439305216 bytes**. No DDS segments or inventory errors.
Temporary foreign Gazebo/Nav2 workloads in `preflight_final_isaac.json` ended
externally. No foreign process was signaled. No simulator was launched.

A leaked child from our isolation test was identified by exact PID/start time,
installed executable, domain 181 and pytest marker, then gracefully stopped.
`test_orphan_teardown.json` records ownership. The test now launches directly
and asserts clean recorded exit and no surviving process identity; corrected
validation passes. This was harness cleanup, not host cleaning.

`resource_audit.json` rehashes four historical foundation samples. Maximum RSS
**5098934272 bytes**, peak total GPU use **2585788416 bytes** are lower bounds
without complete fetch/ROS/MCAP. They cannot justify production limits. Host
hardware incapacity is **not established**. RAM/VRAM and invariant thresholds
remain null rather than being increased to pass. Qualified oracle-PASS Dev
controls required by calibration are also unavailable: the approved M0
fail-closed `ArmControl.target_height()` returns None and inherited grasp rejects
before attachment. M1 does not repair that behavior or restore privileged truth.

## Campaign registration and results

| File under `eval/campaigns/` | Definition | Planned | Executed |
| --- | --- | ---: | ---: |
| `m1_smoke.yaml` | Dev 5/8 once per backend, sequential | 4 | 0 |
| `m1_determinism.yaml` | Dev 6/7 ×3, 5/8 ×2 per backend | 20 | 0 |
| `m1_breadth.yaml` | Dev 10000–10029 per backend | 60 | 0 |
| `m1_test_a.yaml` | Test A 1000000–1000029 per backend | 60 | 0 |

Qualified simulated runs **0**, unqualified simulated runs **0**. Preflight
inventories are not episodes or rate denominators. Smoke not passed.
Determinism and both Dev failure Paretos unmeasured. Test A n=0 per backend:
completion rates and Wilson 95% intervals undefined. UNCLASSIFIED **0 scored
baseline failures**, fraction undefined; exit criterion not met. Oracle/mission
and independent physical-outcome agreement remain unmeasured. No individual
Test A layout/trace inspected; reserve seeds untouched.

Historical Dev replay reproduces supported I19 displacement at Gazebo6 **61.726
sim s** and Isaac6 **62.05833656992763 sim s** (`historical_*_corrected.json`).
These are unqualified historical observations, not earliest causal proof or
current baseline. Synthetic `/clock`→MCAP evidence is hashed in
`mcap_clock_replay_evidence.json`; CTF/MCAP stay outside Git under
`/home/gautham/coco_m1_runs/`.

## Remaining measurement work

Missing fields remain unknown. Remaining witnesses include I07 command-motion
association, I12 independent world-free costmap, I13 exact plan-return source
timing, I14 clearance, I16 truth projection, I18 physical identity, I21 proximity,
I23 finger-before-detach and I25 progress. Successful-control thresholds are
uncalibrated. Older throttled costmaps are context only; unknown raw cost 255
cannot establish an occupied goal. Candidate self-model extents cannot establish
true projection. Source colour/class cannot establish physical identity.
Production analysis keeps incomplete catalogs UNCLASSIFIED and separately records
first-supported violation/context; no forced earliest-cause claim.

Installed Nav2 service introspection streams remain missing. Logs/status UUIDs
do not replace server request/result payloads. Native ROS UST works without the
`ros2 trace` CLI, but synthetic C++ executor spans do not verify mission timing.
Actual simulator-free ROS tests prove isolation and root arbiter command lineage;
qualified simulator graph/lineage/clock equivalence remains unverified.

## Exact continuation point

Commands and prerequisites are in [eval README](../../eval/README.md). Resolve
foreign workload ownership and justified resource/control prerequisites, finish
raw catalog witnesses/calibration within approved scope, then run the four-run
qualified smoke sequentially, inspect evidence and validate it before baseline.
If the frozen successful-control dependency needs a decision, do not silently
change autonomy in M1. No baseline or M2 is authorized by an incomplete proof.

Integrity/disk stops persist in `STOP.json` and prohibit automatic resume.
Resume otherwise binds exact executable/data/campaign/policy content; docs/proof
commits may change SHA without changing runtime fingerprints. Original batch
registration remains immutable. Test A public summaries expose aggregates only;
manual trace analysis is guarded by committed seed governance.

M1 is **not complete** and this is **not a validated overnight handoff**. Runtime
qualification gate failed; hardware-incapacity, disk-overrun and actual oracle
mismatch stop conditions are not established. No new M2 hypotheses confirmed,
no IDEAS entries, no autonomy repair or plan deviation beyond withheld runtime.

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
