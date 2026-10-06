# M0.2–M0.6 control-plane execution

## Entry verification — 2026-10-06

M0 / M0.2; advances committed control files and truthful capability inventory.
Actual starting HEAD: `c45d224a9cbcfd10b9661a40c4df7866febdce38`.
Branch: `coco-2.1-isaac-integration`. Git short status empty, worktree clean.
Read MASTER_PLAN first, STATUS and all five requested M0 reports. Repository
MASTER_PLAN and Downloads source compare byte-identical (`git diff --no-index`
exit 0). Repository plan remains canonical and unchanged. No new amendment.
Existing two dated owner approvals concerning isolation remain in STATUS.

M0.2: capability table, open classes, seed governance and approved change history
recorded in STATUS; IDEAS initialized. Evidence labels follow CI/runtime limits.
No robot behavior, simulator run or historical evidence modified.

## M0.3 environment mechanism

M0 / M0.3; advances reproducible manifest exit criterion. `eval/environment.py`
executed after sourcing setup_env with the existing fresh overlay and explicit
read-only MoveIt prefix. Output: `control_plane/environment/env.json`. No
simulator imported or launched. Captures missing-tool errors explicitly and
refuses overwrite. `eval/README.md` defines per-run usage and the separate Isaac
bridge environment. M1 will integrate this mechanism into its runner.

## M0.4 oracle and M0.4b back-check

`SUCCESS_DEFINITION.md` justifies existing placement/home/budget bounds and
5 mm sampled disturbance/rest criteria against existing evidence allowances,
object geometry and numerical settling measurements. `eval/oracle.py` is the
single pure scorer, independent of mission verdict. `ORACLE_BACKCHECK.md`
records all 16 historical attempts, the one definite disagreement and unknowns.
40 local unit tests passed; CI explicitly collects the new evaluator suite.
No historical script was executed in write mode or historical evidence edited.

## M0.5 seed governance

Dev includes prior simulator/P03D IDs, all previously generated 0–9999 layouts
and high fixture IDs. Thirty fresh Dev seeds allocated. Test A 1000000–1000059
and M4 reserve 2000000–2000059, each inclusive 60, remain untouched. Static
validation and six tests verify disjointness, invalid policy rejection and all
saved JSON seed IDs are Dev; no held-out layout generation or inspection.
M0's ≥60 pool and the protocol's later smaller campaign subsets coexist without
a scope change. `control_plane/seed_validation.json`, `seed_tests.log`.

## M0.6 hygiene and final verification

All findings classified in HYGIENE_AUDIT: 2 M1 blockers resolved, 10 M3 cleanup
items deferred, 6 historical groups retained. No new truth dependency found.
Only control-plane code, explicit new test CI coverage/dependencies and
current-authority doc banners changed. Existing robot behavior and historical
files are byte-unchanged against the entry SHA.

Fresh build 9/9; 1984 package + 49 evaluation tests pass, 0 failures/errors/skips.
`control_plane/test_counts.json` records XML-derived counts and source hashes;
`regressions/graphs` retains new production-node proofs. Environment mechanism
ran again against this fresh overlay (`final_environment/env.json`). No simulator,
held-out seed, reliability campaign, M2 causal investigation or M3 cleanup run.
No new ideas/hypotheses beyond threshold justification and oracle correctness.

Execution is complete for M0.2–M0.6; milestone closure remains pending the Master
Plan's fresh independent review and Gautham's G0 decision. Stop here; no M1.
The live STATUS resolver reports exact HEAD and cleanliness; static checkpoint
provenance names each input SHA because a committed file cannot hold its own SHA.
