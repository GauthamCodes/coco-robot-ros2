# Reproduction and guarded continuation

Start in `/home/gautham/coco-isaac-21`. All output directories/files must be new.
These commands do not change qualification, seeds, recording or safety reserves.

```bash
export COCO_WS=/home/gautham/coco_m1_ws
export COCO_MOVEIT_PREFIX='/home/gautham/ros2_ws(personal)/moveit_prefix/root/opt/ros/jazzy'
source setup_env.sh
```

## Offline reproduction (no simulator)

```bash
python3 -m pytest -q eval/tests/test_manipulation.py eval/tests/test_manipulation_tf.py eval/tests/test_replay.py eval/tests/test_resource_attribution.py eval/tests/test_bootstrap.py eval/tests/test_oracle.py eval/tests/test_invariants.py eval/tests/test_truth.py eval/tests/test_normalize.py coco_perception/test/test_observation_phase.py coco_perception/test/test_object_height.py coco_moveit_config/test/test_grasp_contract.py
python3 -m pytest -q eval/ros_tests/test_phase_runner.py eval/ros_tests/test_engineering_capture.py eval/ros_tests/test_nonfinite_capture.py eval/ros_tests/test_recorder_replay.py eval/tests/test_engineering_image_summary.py
./eval/bin/eval replay /home/gautham/coco_m1_runs/rgbd-phase-20261009/guarded-motion-06 --source-format mcap --output /home/gautham/coco_m1_runs/NEW-verification-replay
./eval/bin/eval replay docs/data/isaac_fetch/coco23/gazebo_seed6 --source-format historical --output /home/gautham/coco_m1_runs/NEW-historical-replay
python3 eval/manipulation.py /home/gautham/coco_m1_runs/NEW-verification-replay /home/gautham/coco_m1_runs/NEW-sidecar-verification.json
python3 eval/resource_attribution.py /home/gautham/coco_m1_runs/rgbd-light-20261009/acquisition-camera-only-02 /home/gautham/coco_m1_runs/rgbd-phase-20261009/acquisition-01 /home/gautham/coco_m1_runs/rgbd-phase-20261009/guarded-motion-06 /home/gautham/coco_m1_runs/rgbd-phase-20261009/guarded-motion-09 --output /home/gautham/coco_m1_runs/NEW-resource-comparison.json
```

Standalone manipulation.py checks sidecars and existing oracle output; it does
not certify MCAP integrity. Replay performs full CDR/sidecar comparison and
rejects incomplete MCAP boundary records. Invalid/truncated evidence is retained.
Synthetic tests prove evaluator behavior only. Historical replay is not a new run.

## Build and package test

```bash
colcon build --base-paths /home/gautham/coco-isaac-21 --build-base /home/gautham/coco_m1_ws/build --install-base /home/gautham/coco_m1_ws/install --packages-select coco_config coco_perception coco_moveit_config
colcon test --base-paths /home/gautham/coco-isaac-21 --build-base /home/gautham/coco_m1_ws/build --install-base /home/gautham/coco_m1_ws/install --packages-select coco_moveit_config
colcon test-result --test-result-base /home/gautham/coco_m1_ws/build/coco_moveit_config --verbose
```

## Controlled continuation — currently blocked

Commit a clean implementation and first run only the read-only gate:

```bash
./eval/bin/eval bootstrap --backend gazebo --profile rgbd_manipulation --fixture grasp_front_flank --domain 82 --seconds 180 --preflight-only --output /home/gautham/coco_m1_runs/NEW-manipulation-preflight
```

Inspect its manifest and safety envelope. A preflight PASS is only the emergency
reserve check: also require enough available headroom for the recorded essential
workload. Do not launch when the unchanged reserve is already crossed, GPU capacity
is unavailable, ownership is ambiguous, or expected startup cost crosses reserve.
Do not terminate foreign applications or repeat the same failed workload.

Only after those conditions have changed and the gate passes:

```bash
./eval/bin/eval bootstrap --backend gazebo --profile rgbd_manipulation --fixture grasp_front_flank --domain 82 --seconds 180 --output /home/gautham/coco_m1_runs/NEW-guarded-motion
./eval/bin/eval replay /home/gautham/coco_m1_runs/NEW-guarded-motion --source-format mcap --output /home/gautham/coco_m1_runs/NEW-guarded-motion-replay
```

Bootstrap reruns the gate, records first/stops recorder last, preserves manifests,
source truth, TF, exact consumer acceptance, checkpoints, resource samples and
owned teardown. Automatic reports are oracle.json, analysis.json, manipulation.json.
This is NON_QUALIFYING and excluded from every M1 denominator. A resource trip
ends this attempt; do not retry until the relevant condition changes.

Keep missing relative-motion/sample-gap/proximity calibration and finger-opening
witnesses explicit. A physical sequence alone is not full mission/authority proof.
Do not enter synthetic limits to obtain a physical PASS. Do not start Isaac until
Gazebo evidence supports continuation and Isaac's own current preflight permits it:

```bash
./eval/bin/eval preflight --backend isaac --output /home/gautham/coco_m1_runs/NEW-isaac-preflight.json
```

Production calibration remains0/19, smoke0/4 and M1.8=0/140. Resolve the bounded
manipulation evidence gap before returning to that original Master Plan sequence.
