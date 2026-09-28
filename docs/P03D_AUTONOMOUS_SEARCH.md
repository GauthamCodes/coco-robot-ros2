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
Other reachability faults are rejected. The approach and grasp servers retain
their measured final reach, lateral, self-collision, and grasp-window checks.

A miss or rejected observation times out with a named reason. Recovery stops
the drivers and confirms the arbiter is idle, then the existing ramp driver
descends. Nav2 visits a measured clear south-side bypass waypoint, returns
HOME, then takes the robot to the next candidate's pre-ramp pose. A direct
far-side to pre-ramp goal stalled at the ramp's southwest corner in the first
adversarial run. A direct lane_2 return chose the north side and ended with
AMCL's estimated start in an occupied map cell in the second run.
After
the fourth miss, the robot descends and returns home with `SEARCH_FAILED`.
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
