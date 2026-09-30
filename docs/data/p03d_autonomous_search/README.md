# P03D Gazebo evidence

`matrix_all_attempts.json` contains one row for each of the 28 completed
runner attempts, including the final fixed-mode recheck. A row includes
the exact mode, seed, requested colour, evaluator-only target pose and region,
observed search sequence, perception verdict counts, acquired pose and region,
grasp outcome, mission outcome, failure reason, recoveries, timing, software
HEAD and dirty-path count, runner checks, and the raw evidence directory.
Failed and crashed
attempts remain in the file. Rebuild it with:

```bash
python3 docs/data/p03d_evidence.py /home/gautham/coco_p03d_runs \
  > docs/data/p03d_autonomous_search/matrix_all_attempts.json
```

`adversarial_red_lane2.json` joins the evaluator's red-in-lane-2 assignment
with the **robot inputs** (requested colour only, empty region map), one
stamped `VALID` RGB-D observation, the mission's region transition, acquired
`base_footprint` point, verified grasp, and completed placement. Its raw
directory retains `mission.log`, `target_pose_status.txt`, `cmdpath.log`,
Nav2 goals, process logs, topic samples, and spawned-target readback.

These files are evaluator evidence. The episode manifest and its world
coordinates are not inputs to the mission executive or ramp driver in
randomized mode.
