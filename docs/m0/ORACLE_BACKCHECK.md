# M0.4b historical oracle back-check

M0 / M0.4–M0.4b; advances single oracle, independent tests and historical
rescoring exit criteria. Definition: `../SUCCESS_DEFINITION.md`. Evaluator:
`../../eval/oracle.py`; adapter: `../../eval/backcheck.py`. Both are offline,
without ROS/control endpoints. Mission verdict is recorded separately.

## Coverage

All **16** saved M2.3/M2.4 run directories were inspected: M2.3 10, M2.4 6.
**13 scorable** (5 PASS, 8 FAIL), **3 UNSCORABLE**. No source evidence was
rewritten/deleted. These are historical unqualified, privileged-input runs;
no score establishes compliant current fetch or qualified reliability.

Authoritative M0 results: `control_plane/backcheck_v2/summary.json`, per-run
facts/metrics/checks/missing-data reasons and source hashes alongside it.
`backcheck_v1/` preserves preliminary position-only rest scoring; v2 additionally
checks orientation rest. Counts/outcomes are unchanged. Initial string-valued
Gazebo protobuf stamp parser error is retained in `backcheck_initial.log`;
corrected parser is covered by a synthetic saved-trace adapter test.

## All outcomes

| Saved run | Mission | Oracle | Disagreement | Failed / unknown conditions |
| --- | --- | --- | --- | --- |
| coco23/gazebo_seed5 | COMPLETE | UNSCORABLE | None | no_arbiter_violation unknown |
| coco23/gazebo_seed6 | ABORT | FAIL | False | target_in_placement_zone, nonrequested_undisturbed, robot_home |
| coco23/gazebo_seed7 | COMPLETE | FAIL | True | nonrequested_undisturbed |
| coco23/gazebo_seed8 | COMPLETE | PASS | False | all checks pass |
| coco23/gazebo_seed9 | COMPLETE | UNSCORABLE | None | no_arbiter_violation unknown |
| coco23/isaac_seed5 | COMPLETE | PASS | False | all checks pass |
| coco23/isaac_seed6 | ABORT | FAIL | False | target_in_placement_zone, nonrequested_undisturbed, robot_home |
| coco23/isaac_seed7 | ABORT | FAIL | False | target_in_placement_zone, nonrequested_undisturbed, robot_home |
| coco23/isaac_seed8 | COMPLETE | PASS | False | all checks pass |
| coco23/isaac_seed9 | COMPLETE | PASS | False | all checks pass |
| coco24/gazebo_seed6 | ABORT | FAIL | False | target_in_placement_zone, robot_home |
| coco24/gazebo_seed7 | ABORT | FAIL | False | target_in_placement_zone; no_arbiter_violation unknown |
| coco24/gazebo_seed8 | COMPLETE | UNSCORABLE | None | no_arbiter_violation unknown |
| coco24/isaac_seed6 | ABORT | FAIL | False | target_in_placement_zone, robot_home; no_arbiter_violation unknown |
| coco24/isaac_seed7 | ABORT | FAIL | False | target_in_placement_zone, robot_home |
| coco24/isaac_seed8 | COMPLETE | PASS | False | all checks pass |

## Every definite mission/oracle disagreement

Exactly one: **M2.3 Gazebo seed 7** — mission COMPLETE, oracle FAIL. Target
placement/rest, robot home, recorded authority and time checks pass, but
non-requested cylinder displacement violates the ≤5 mm condition. Measured
maximum sampled 3D displacement by model:

- `target_yellow`: 2.726209001 m.
- `target_green`: 4.115623461 m.
- `target_blue`: 0.000000000 m.

This follows the already-documented destructive transit in M2.4's pre-fix
report; no new causal investigation or robot change was performed. No other
scorable mission/oracle disagreement occurs; ABORT runs fail physical checks.

## Unscorable / partially missing evidence

M2.3 Gazebo seeds **5 and 9**, M2.4 Gazebo seed **8**: all physical/time checks
pass, but each has one recorded idle-mode observer flag. Cross-topic delivery
ordering lacks synchronized authority evidence sufficient to clear or assert
those flags. Mark **UNSCORABLE**, comparison null; never count them as FAIL,
PASS or definite disagreements. M2.3 seed5's existing explanatory evidence is
preserved, but does not by itself establish complete authority proof.

M2.4 Gazebo seed7 (two flags) and Isaac seed6 (one flag) also have unknown safety
checks. They are nevertheless **scorable FAIL** because known physical conditions
already falsify the conjunction. Every missing reason is retained in JSON.
No missing data requires changing the success definition. No new simulation,
host qualification, benchmark confidence interval or held-out inspection occurred.

## Verification

`control_plane/oracle_tests.log`: 40 passed, 0 failed/skipped. Includes each
physical failure, missing/non-finite data, time boundary, whole-window motion,
orientation/sign equivalence, disagreement in both directions and string-stamp
Gazebo historical parsing. CI now explicitly runs `eval/tests` in addition to
existing package suites; remote CI execution is NOT VERIFIED.

Final M0.6 verification: 43 oracle/environment/adapter tests plus 6 seed tests,
49 total, all passing. Final stale/partial/overflow checks leave every v2 result
unchanged; source-hash equality and score equality are recorded in
`control_plane/backcheck_validation.json`.
