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
