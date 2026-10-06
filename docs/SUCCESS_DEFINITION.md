# Single physical-success definition — M0 v1

The committed Master Plan is authoritative. `eval/oracle.py` is the **one**
scoring module. It consumes evaluator facts only, has no ROS imports/endpoints,
and is never imported by robot packages. M1 will supply live `/eval` trace
adapters. Historical raw world topics are read only as saved evaluator data;
they are not restored to autonomy. Mission COMPLETE is never a physical check.

A PASS requires all six checks below (placement and rest jointly implement the
first Master Plan condition). A known failed condition means FAIL even if
another check is unknown: the conjunction is already disproved. Otherwise missing
or invalid evidence means UNSCORABLE, never assumed success. Every result stores
mission verdict beside oracle verdict, each condition, metrics and missing-data
reasons. Disagreement is true/false only for COMPLETE/ABORT versus a scorable
oracle verdict; unknowns have null comparison.

| Check | Definition and threshold | Existing justification |
| --- | --- | --- |
| Requested target in home placement zone | Center XY distance ≤0.50 m from configured home; floor center Z within 0.02 m of half target height | Existing 2.3 `analyze.py` uses 0.50 m placement, inherited ±20 mm release height; target height 0.158 m in `coco_config.robot` and manifests. 2.3 completed placements were 0.076–0.355 m. These are fixed prior tolerances, not expanded to pass new runs. |
| Target at rest | Detached terminal pose samples spanning ≥2 simulated seconds; maximum pairwise center motion ≤0.005 m and orientation change expressed as axis-tip motion at half target height ≤0.005 m | Existing evidence uses ~2 s simulator snapshots and ≥2 post-release samples; 2.3 initial physical/manifest agreement already has a 5 mm evidence allowance (`check_evidence.py`). 5 mm is half the smallest cylinder radius (20 mm diameter), small enough to distinguish gross transport/tipping from observed settled jitter. Existing completed height spans are below 1 mm. Orientation motion uses normalized quaternions with sign equivalence, avoiding a stationary-center spinning false pass. This is an operational sampled rest definition, not a claim of exactly zero physics velocity. |
| Non-requested cylinders undisturbed | Maximum sampled **3D** displacement of every non-requested cylinder from its first physical pose at mission start ≤0.005 m, over the entire episode; returning an object does not erase an excursion | Reuses the existing 5 mm physical-placement evidence allowance, not a new tuned value. 2.4 control-run displacement is ≤0.000077 m, orders below 5 mm; 2.3 destructive transit moves objects by decimeters/meters. 5 mm is half the smallest radius and excludes meaningful object transport while admitting numerical settling. Initial baseline is measured truth, not a manifest pose. |
| Robot home | Terminal robot center XY distance ≤0.50 m from configured home | `mission_states.py` GOAL_XY_CONSISTENCY = 2 × existing Nav2 0.25 m tolerance, justified there by C2-NAV.44 measured 0.305–0.312 m arrival errors and 0.004–0.049 m AMCL offsets. Reuses the established hard consistency bound, not the tighter nominal arrival target. |
| No arbiter violation | Covered command-authority evidence and empty violation list | Existing sole-publisher graph and observer command/idle evidence. No mission outcome can clear a violation. An unresolved asynchronous idle flag is unknown, not an asserted breach or clean proof. |
| Episode completes within budget | Observed terminal episode end and monotonic elapsed wall time ≤1200 s from mission start | Existing `scripts/isaac_fetch.py` / observer default and 2.3/2.4 runner policy: 1200 **wall** seconds. Do not silently reinterpret as simulated seconds. |

The home is the static world/map start configuration (`SPAWN_XY`, -2,0 in saved
runs), not the robot's final pose. A future mission may supply another justified
home before its campaign. Placement volume is floor-relative, so a target over
home but held in the air cannot pass. No additional grasp/lift stage or
mission COMPLETE requirement is added: these are useful diagnostics, not the
Master Plan's end-state oracle. A physically successful ABORT is a disagreement.

## Evidence contract and limits

The normalized JSON schema is exercised in `eval/tests/test_oracle.py`. Facts
include finite target/robot poses, target height, detached terminal rest samples
with quaternions and simulated stamps, all non-requested model IDs with
whole-episode max displacements, independently attested truth/arbiter coverage,
wall duration/end, and a separate mission verdict. Non-finite or malformed
measurements are unknown. Coverage flags are evaluator attestations, never robot
claims; adapters must compute them from captured traces. The pure module cannot
verify the provenance of an arbitrary JSON file by itself.

`eval/backcheck.py` reads every saved Gazebo physical pose packet and Isaac state
snapshot during LOCALIZE→terminal, and uses historical simulator-derived
odometry only for Isaac robot truth. Its last truth sample must lie within one
existing 2 s snapshot interval of terminal; the rest window ends at that sample
and starts at the latest preceding sample at least 2 s earlier. No post-terminal
cleanup motion is counted. It requires all non-requested cylinders observed.
Finite historical samples cannot exclude motion between samples; no continuous
contact/velocity, host qualification or current-baseline claim is made.

For historical safety: zero recorded observer flags plus sole-arbiter graph means
no violation **logged** in the captured evidence. Nonzero flags stay unknown due
to the existing documented asynchronous timing ambiguity. Even the seed5 timing
explanation is not silently promoted to full authority proof. M1's synchronized
trace/invariant instrumentation will improve coverage without changing this
success definition. Unqualified historical scores are not benchmark rates.

The current compliant robot cannot establish legitimate manipulation completion;
attachment/lift/release/placement remain fail closed as documented in
`m0/MANIPULATION_OBSERVATION.md`. The oracle cannot send success or truth to
robot control to bypass that boundary.

## Reproduction

```bash
python3 -m pytest -q eval/tests
python3 eval/oracle.py /path/to/evaluator-facts.json /path/to/new-oracle.json
python3 eval/backcheck.py --output-dir /path/to/new-backcheck
```

Outputs are exclusive-create. Historical files remain untouched. Per-run scores
include SHA256s of source files. Committed rescoring and every disagreement:
`m0/ORACLE_BACKCHECK.md`, `m0/control_plane/backcheck_v2/`.
