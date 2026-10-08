# Deterministic target-height diagnostic

From the repository root:

```bash
env -i HOME=/home/gautham USER=gautham PATH=/usr/bin:/bin LANG=C.UTF-8 \
  bash --noprofile --norc -c '
    export COCO_WS=/home/gautham/coco_m1_ws
    export COCO_MOVEIT_PREFIX="/home/gautham/ros2_ws(personal)/moveit_prefix/root/opt/ros/jazzy"
    source setup_env.sh
    export ROS_DOMAIN_ID=187
    python3 docs/m2/gate_target_height_20261008/reproduction/reproduce.py /tmp/coco-height-new-result.json
    python3 -m pytest -q coco_moveit_config/test/test_grasp_contract.py \
      -k "attachment_failure or unavailable_lift or valid_fix"
  '
```

`result.json` is the captured diagnostic; `final_command.log` records its final
execution. `command.log` includes the focused tests: **8 passed, 10 deselected**.
`rgbd_fixture.npz` contains synthetic BGR/depth frames (95/115 are visible-mask
row labels). It is regenerated deterministically by the script. Depth outside
the observed patch is unavailable, never defaulted to a physical measurement.

The script runs production colour masking, connected components, depth/size
validation, deprojection, configured optical-to-base geometry, candidate
diagnostics, approach phases, approach-fix validation, IK/window validation,
pick sequence and height gates. It uses real ROS message types and constructs
the shared GraspServer on private domain187. No executor or simulator is started.
It destroys the node and shuts down ROS in `finally`.

Transport/actuation seams are stubbed: fixture encoder integration, level IMU
input, MoveGroup availability, pre-grasp posture, collision-scene operations,
arm/finger motion and magnet transport. Production height/attachment/lift/release
gates are **not** stubbed. No actual motor, trajectory or magnet command is
published. This isolates the downstream blocker after valid upstream inputs;
it does not establish physical mission success or live TF correctness.

Fixture visible bands idealize different observed subsets at one fixed surface
range; these are not physically rendered cylinder images. They demonstrate centroid
dependence on framing, not a claim that a real recorded cylinder moved. The
camera near-plane proof separately uses the full permitted grasp-axis interval
and known radius, with clipping values parsed from each backend's source.

`provenance.json` records actual starting SHA, Master Plan equality and a
read-only domain66 snapshot. `result.json` hashes the production sources used.
Evidence is **SYNTHETIC DIAGNOSTIC**, not replay, control calibration, qualified
smoke, live full-stack graph validation or Test A evidence.
