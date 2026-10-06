# M0.6 repository hygiene audit — 2026-10-06

M0 / M0.6; advances classified audit and M1-blocker identification exit criteria.
Input SHA: `33354011c9d76857b3c66b12e14176633b1346ee`. No robot behavior,
physics, Nav2, gains, frozen components or historical evidence changed.

## Coverage and method

`control_plane/hygiene_inventory.json` inventories **all git-tracked text** at
M0.5, searching mission/region definitions, colour/lane relations, machine paths,
joint limits and privileged/final-command interfaces. It records paths, line
numbers and full matching lines, separating historical data from candidates.
The inventory also checks byte-identical launches, AST-parses tracked Python,
and syntax-checks tracked shell outside historical evidence. Matches are not
automatically defects: tests, comments, ROS install paths and evaluator truth
are legitimate. Reviewed production call sites, launch composition, package
install/dependency declarations, workflow, entry points and current/historical
docs. No simulator launched. Scripts needing simulation/training were inspected,
not executed. This is not proof that every optional tool runs on every host.

Categories below are exhaustive for the actionable findings in the inventory;
source examples identify each group. No old file was deleted. All exact raw
matches remain available for review. Later work does not acquire authorization
merely by appearing in this table.

## Classified findings

| ID | Finding / evidence paths | Classification | Disposition / why |
| --- | --- | --- | --- |
| H01 | New `eval/tests` outside colcon package discovery; workflow initially omitted oracle coverage | **blocks M1** | Resolved in M0.4: explicit CI evaluation unit-test step. Complete local eval suite passes; remote CI not claimed. |
| H02 | Root `CLAUDE.md` says PROJECT_STATE is authoritative, everything on main and old M7/Yard roadmap; README/PROJECT_STATE mix old completion with current branch | **blocks M1** | Resolved here by a small current-authority banner in those three root docs pointing to MASTER_PLAN/STATUS and fail-closed observation contract. Original historical content retained. Broader editing is H03. |
| H03 | Old current-state prose, public labels/numbers, README/P03D “not demonstrated” versus later historical fetch, `HOW_TO_RUN.md`, `RUNNING.md`, `docs/COCO_2_1_ISAAC.md`, `docs/FUTURE_WORK.md`, `docs/M7_DESIGN.md` | **M3 cleanup** | Archive-aware documentation consolidation; current authority/banner and STATUS prevent scope drift now. Historical evidence never becomes a compliant current capability. No claim cleanup performed. |
| H04 | Legacy procedural mission in `gazebo_models/scripts/traverse_demo.py` overlaps `coco_mission/scripts/mission_states.py`; `nav_round_trip.py` is another fixed demo | **historical, keep** | Historical reproduction/diagnostic paths, not the production executive. Launch explicitly warns against both mission mode publishers and defaults executive. Shared manipulation fails closed. Keep provenance; no cosmetic unification. |
| H05 | `coco_web/coco_web/mission_view.py` copies state/reason inventories and HUD/formatters mirror telemetry | **M3 cleanup** | Drift guarded by `test_mission_view.py`, including earlier resolved RETREAT inventory failure. No duplicated robot mission control. Future generated inventory may reduce copy maintenance. |
| H06 | Region definitions are centralized in `coco_config.robot.TARGET_REGIONS`; episode generator and mission import them. Static world/map/URDF geometry necessarily repeats some coordinates | **M3 cleanup** | No second production search-region authority found. Geometry consistency tests cover current copies; generation/consolidation deferred. |
| H07 | `lane_for_colour`, `resolve_lane`, `FIXED_REGION_MAP` fixed-mode compatibility; `traverse_demo`, `nav_round_trip`, `plan_compare`, evaluator `vision_check` defaults | **historical, keep** | Fixed-layout task compatibility and old evidence. Production autonomous_search uses region IDs and measured acquisition, not requested-colour lane shortcut; existing region/search tests prove separation. Do not remove fixed fixtures. |
| H08 | `target_finder` status lane field still uses fixed colour mapping and comments describe old lane-led behavior; `full_world_robo.launch.py` old sequencer comment | **M3 cleanup** | Diagnostic field/comment only; executive reads sel/found, HUD sel/range. `target_pose.compatibility_fields` explicitly states no lane consumer. No motion gate reads this field. No behavior edit. |
| H09 | `$HOME/isaac-sim`, bundled Python3.10/Humble bridge path in `scripts/isaac_sim_coco.sh`; hardcoded Jazzy RViz binary in `scripts/isaac_smoke.py` | **M3 cleanup** | Known pinned host layout, manifest captures it; environment capture supports explicit alternative interpreter. Portable launcher/deployment packaging deferred. No unconditional user home path in active robot controller code found. |
| H10 | `/opt/ros/jazzy` in setup/CI, `/opt/coco_ws` Docker default, `/tmp` output defaults in probes and runners | **M3 cleanup** | Intentional install/temporary defaults, not leaked prior worktree paths. Shared /tmp log names can collide; run-directory isolation belongs to M1 capture and M3 packaging. No defaults changed. |
| H11 | `/home/gautham/...` in historical `docs/data` orchestration, `runtime_reference.json`, archive scripts and `experiments/legacy/overnight_chain.sh` | **historical, keep** | Host provenance; some old scripts mutate training configs/start simulators and must not be used for current milestones. Not executed here. Nothing removed. |
| H12 | `mission.launch` / `web.launch` / `platform.launch` overlap includes; 13 launch/test-launch files, no byte-identical pair | **M3 cleanup** | Intentional composition with mission passing arbiter:=false into optional platform. Standalone web/platform default arbiters can duplicate authority if operator launches both separately; existing comments/tests and current production composition handle it. Consolidation deferred; no second current command path found. |
| H13 | Xacro position/velocity limits, Python ARM_LIMITS, MoveIt velocity/acceleration YAML and controller limits | **M3 cleanup** | ARM_LIMITS versus URDF consistency tested; IK/Isaac import it, USD expansion reads URDF. MoveIt acceleration is additional data URDF cannot express. Maintenance duplication remains, no current contradictory limit found. |
| H14 | CI PR trigger targets main only; floating actions/dependencies, no Isaac runtime/qualified mission campaign, simulator launch test default disabled, no Docker-build job | **M3 cleanup** | CI/deployment expansion explicitly M3. Current integration-branch pushes run package plus oracle tests. M0 does not add expensive campaigns or claim remote execution. |
| H15 | Fresh checkout needs ROS/dependencies and explicit COCO_WS/MoveIt prefix on this host; setup path inferred two levels above repo is wrong for arbitrary worktree; copying install breaks yard params | **M3 cleanup** | `scripts/build_overlay.sh` supplies explicit overlay and symlink-install, tested fresh here. Documented environment prerequisites, not a current build blocker. General install portability deferred. |
| H16 | Historical analyzers write measurements/comparisons and `check_evidence.py` compares recorded hashes against current runtime sources | **historical, keep** | Expected to fail hash checks after later code changes; never run them to rewrite old results. New read-only `eval/backcheck.py` hashes saved sources and writes a fresh directory. |
| H17 | Legacy climb/training reset/scene-mutating pick demos intentionally unavailable; `verify_all.sh`, training/curriculum/browser live scripts require simulation or archived artifacts | **historical, keep** | Explicit approved isolation/freeze disposition, not a fresh-checkout regression to restore. Optional historical entry points are not M1 evaluator prerequisites. No training or expensive verification run. |
| H18 | Physics truth exports, evaluator world APIs and normal state producers; current `MANIPULATION_OBSERVATION.md` source map and production graph tests | **historical, keep** | Retain simulator/evaluator internals and historical truth evidence. Active autonomy normal state remains encoder/IMU/joints/RGB-D; no new privileged dependency found. Missing independent object observation remains intentionally fail closed. |

## Classification summary and blockers

**18 findings: 2 blocks M1 (both resolved), 10 M3 cleanup, 6 historical, keep.**
No unresolved hygiene blocker or new owner-decision/architecture contradiction.
The manipulation observation limitation is a documented capability constraint,
not permission to restore truth or implement a later feature. M0 is ready for
independent review only after complete regression verification below. G0 is an
owner gate, not passed by this audit.

## Fresh-checkout verification

Fresh isolated build from current checkout using `scripts/build_overlay.sh`,
explicit existing read-only MoveIt dependency prefix, new build/install directory:
`control_plane/build_destination.txt`, `clean_build.log`. Nine packages build.
Reproduction script: `control_plane/run_checks.sh NEW_EVIDENCE_DIRECTORY` after
exporting COCO_WS and COCO_MOVEIT_PREFIX. Complete per-package pytest XML/logs,
new production-node isolation graphs and evaluator suite: `control_plane/regressions/`.
No historical graph/evidence overwrite. Existing test source is unchanged.
All tracked non-historical Python AST parses and 13 shell syntax checks pass;
no syntax-failing entry point found. These checks do not claim a runtime campaign.

Final counts: **1984 package tests + 49 evaluator tests = 2033 passed,
0 failed, 0 errors, 0 skipped**. XML-derived totals: `control_plane/test_counts.json`.
Isolation subset includes 10 production-graph tests, 18 grasp-contract tests and
9 encoder-isolation tests (within the 1984, not additional). Both backend graph
JSONs are retained. Build warnings and existing fork warnings are retained;
no failure was suppressed. Remote CI and simulator bringup remain unexecuted.

`eval/hygiene_inventory.py NEW_JSON` reproduces the search/syntax inventory.
The initial inventory is retained; final tracked inventory is appended as
`control_plane/hygiene_inventory_final.json`. `python3 eval/status.py` resolves
the exact current full SHA and clean state without embedding an impossible
self-referential commit hash in STATUS. Checkpoint input SHAs remain explicit.

Final oracle hardening tests reject overflowed quaternions, stale terminal
placement proof and preserve definite logged safety failures with partial
coverage. These are M0 correctness checks, no robot behavior change. All 16
committed v2 rescoring outcomes match the final scorer; all historical source
hashes unchanged (`control_plane/backcheck_validation.json`).
