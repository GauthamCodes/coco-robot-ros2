# M1 baseline — not started

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
