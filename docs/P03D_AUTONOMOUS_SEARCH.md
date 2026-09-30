# P03D autonomous target search

Randomized Gazebo missions use only `EpisodeSpec.task_view().requested_colour`
on the robot side. The manifest, including the target's region and world pose,
belongs to the world generator and evaluator. The mission launch resolves a
manifest to a colour and an `autonomous_search` flag; it passes an empty
`region_map` to both the executive and ramp driver. Fixed mode retains the
existing colour-to-lane compatibility path.

## Search contract

`TARGET_REGIONS` supplies the four named candidate lanes in world-y order.
The executive uses each lane only as a Nav2 pre-ramp approach goal and a
cross-track datum for the existing ramp driver. The region's nominal row x
and the episode's target pose are never search inputs. The requested colour
does not change traversal order.

After each climb, `SEARCH_TARGET` waits for a new RGB-D frame from
`target_pose_node`. The observation must select the requested colour, carry
`VALID` depth/size/transform status, include a `base_footprint` point from
that frame or a newer one, and put the point in the current lane's lateral
corridor. The corridor ends at the midpoint to the next candidate lane.
`reach_appr=OFF_ARM_PLANE` is allowed at this stage because the existing
approach servo turns toward the target before its final straight creep.
The corridor check rotates the perceived `base_footprint` point by the
robot's observed yaw and compares its world lateral coordinate with the
selected region centre. The first position seed 6 retry exposed why the
frame matters: a valid red point at robot-relative y = -0.272 m was rejected
when the robot itself finished 0.235 m off-centre. The previous comparison
used the robot-relative y against a world-lane boundary. The corrected check
still rejects a point in an adjacent lane, including when robot heading
changes its world lateral coordinate.
Other reachability faults are rejected. The approach and grasp servers retain
their measured final reach, lateral, self-collision, and grasp-window checks.

A miss or rejected observation times out with a named reason. Recovery stops
the drivers and confirms the arbiter is idle, then the existing ramp driver
descends. Nav2 visits a measured clear south-side bypass waypoint, returns
HOME, then takes the robot to the next candidate's pre-ramp pose. A direct
far-side to pre-ramp goal stalled at the ramp's southwest corner in the first
adversarial run. A direct lane_2 return chose the north side and ended with
AMCL's estimated start in an occupied map cell in the second run.
After the fourth miss, the robot descends and returns home with
`SEARCH_FAILED`.
No search failure calls grasp.

On acquisition, the executive records the observed point and image time in
`MissionMachine.acquired` and logs `TARGET_ACQUIRED` with the region and pose.
`approach_server` consumes the same `/perception/target` PointStamped stream,
keeps checking that points remain fresh, aligns, and produces its existing
`/approach/target` estimate for grasp. Neither server consumes an episode
target coordinate.

## Interfaces and ownership

- `/mission/search_region` carries a region ID to the ramp driver in
  autonomous mode. The ramp driver ignores target colour for lane selection
  in that mode.
- `/perception/target_pose/status` includes `stamp_ns`, the RGB image stamp.
  A timer's repeated status line alone cannot satisfy SEARCH_TARGET.
- `/perception/target` is published by exactly one perception node. Randomized
  episode launch selects `target_pose_node`; fixed mode keeps its default.
- Nav2, ramp driver, and approach server remain the only motion sources.
  `/diff_drive_controller/cmd_vel` remains owned by `cmd_vel_arbiter`.

The first search domain is the existing single crest's four lanes. This
implementation does not add platforms or change the validated target
placement envelope.

## Code paths that still know the fixed colour lanes

`coco_config.robot.lane_for_colour` and `resolve_lane` remain as the fixed
compatibility mapping. `mission_states.MissionPlan` calls `resolve_lane` only
when `autonomous_search` is false; the ramp driver likewise resolves the
selected colour only in fixed mode. `target_finder` still uses
`lane_for_colour` for its original fixed-lane status and is not launched for
randomized episodes. The `vision_check`, `traverse_demo`, `nav_round_trip`,
and `plan_compare` scripts retain their older fixed-layout diagnostics.
Episode generation knows the colour-to-region assignment for spawning and
evaluation, but randomized mission launch passes only the requested colour,
an empty region map, and `autonomous_search=true` to robot nodes. Tests
assert the randomized plan's order and selected region are independent of
the requested colour and of any supplied region map.

## Gazebo evidence

Every row below is an actual Gazebo mission. `--` for a fixed acquired
region means the legacy status gate did not emit a `TARGET_ACQUIRED` event;
its grasp and mission outcome were recorded. The seed 2 failures are retained
as failures. The full 29-attempt record, including retries and the exact
wall/simulation timing, detection counts, Nav2 goals, recovery counts,
software HEAD, and raw log paths, is in
`data/p03d_autonomous_search/matrix_all_attempts.json`. This is an inventory
of observed runs, not an estimated success rate.

| Mode | Seed | Requested | Actual | Acquired | Grasp | Mission | Wall s | Recoveries | Evidence run |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | --- |
| FIXED | 0 | red | lane_1 | -- | held | COMPLETE | 166 | 0 | fixed_red_final |
| FIXED | 0 | green | lane_2 | -- | held | COMPLETE | 172 | 0 | fixed_green |
| FIXED | 0 | blue | lane_3 | -- | held | COMPLETE | 202 | 0 | fixed_blue |
| FIXED | 0 | yellow | lane_4 | -- | held | COMPLETE | 181 | 0 | fixed_yellow |
| COLOUR | 1 | red | lane_2 | lane_2 | held | COMPLETE | 361 | 1 | colours_s1_red_final |
| COLOUR | 2 | red | lane_4 | -- | no | DESCENT_TIMEOUT | 154 | 2 | colours_s2_red_r3 |
| COLOUR | 5 | red | lane_1 | lane_1 | held | COMPLETE | 191 | 0 | colours_s5_red |
| COLOUR | 6 | red | lane_4 | lane_4 | held | COMPLETE | 808 | 3 | colours_s6_red |
| COLOUR | 7 | red | lane_3 | lane_3 | held | COMPLETE | 526 | 2 | colours_s7_red_r4 |
| POSITION | 1 | red | lane_2 | lane_2 | held | COMPLETE | 370 | 1 | positions_s1_red |
| POSITION | 2 | red | lane_4 | -- | no | NAVIGATION_FAILED | 368 | 6 | positions_s2_red_r2 |
| POSITION | 5 | red | lane_1 | lane_1 | held | COMPLETE | 193 | 0 | positions_s5_red |
| POSITION | 6 | red | lane_4 | lane_4 | held | COMPLETE | 628 | 3 | positions_s6_red_r3 |
| POSITION | 7 | red | lane_3 | lane_3 | held | COMPLETE | 495 | 2 | positions_s7_red_r4 |

The deliberate adversarial case is COLOUR seed 1: the fixed rule would
choose lane_1 for red, while the generated episode spawned red in lane_2.
The robot visited lane_1, rejected its observation, took the Nav2 bypass,
then acquired red in lane_2 at perceived `base_footprint` point
`(1.2959, +0.0554, -0.2483)`. The matching RGB-D status was `VALID`,
`qual=1.0000`, `tf_age=0.0000`, and carried image stamp
`306176000000` ns. Approach completed, grasp was verified, and placement
completed on committed code with zero dirty paths.
`data/p03d_autonomous_search/adversarial_red_lane2.json` pairs
those events with the evaluator-only assignment and robot inputs.

COLOUR seed 6 searched lane_1 → lane_2 → lane_3 → lane_4 and completed
fetch. POSITION seed 6 repeated all four regions with red at world
`(4.0582, 0.7493)`, acquired from perception in lane_4, and completed
fetch. POSITION seed 1 and 5 also acquired targets displaced within their
validated region envelopes. No target coordinate from any manifest was
injected into mission control.

## Tests and observed limits

The final non-lint Python suites across nine packages had **1,886 passed,
7 skipped**, with 9 existing style checks deselected. The focused
`test_autonomous_search.py` suite had **20 passed**. Changed Python files
passed `flake8 --select=E,F`. The tests cover traversal order, all four
region exhaustion, colour matching, stale frame and pose rejection, invalid
depth and transforms, unavailable perception, safe handoff, fixed mode,
the manifest boundary, the off-centre world-frame corridor, and a
heading-adjusted corridor. Real runner checks confirmed one wheel controller
publisher (`cmd_vel_arbiter`) and the Nav2/monitor/relay/arbiter command
path. The arbiter remains the only wheel owner and search recovery sends
`STOP_ALL` before descent or a new navigation goal. The recorded command
path reported zero STOP breaches; several runs had no STOP-window samples,
so that counter alone is not a motion test.

Some repeated long searches hit an ODE `aabbBound` assertion in Gazebo during
descent, causing `CLOCK_STALLED`. Others stopped at the far-ramp seam around
world x = 4.50 m and ended in `DESCENT_TIMEOUT`. POSITION seed 2 had Nav2
`NAVIGATION_FAILED` after a descent in a run before the map-transform
handoff gate was added. These failures remain in the evidence; a later
successful seed does not erase them. The search domain is the four existing
lanes of one platform, and no moving obstacles or additional platforms were
evaluated.
