# M0.1 repository truth — stopped

M0 / M0.1; advances the verified starting-state and clean-build-count exit criteria.
M0 is incomplete. No robot behavior changed. M0.2–M0.6 were not started.

## Starting state (before installing the plan)

- Actual HEAD: `bc843c7c9927f730dfa0e994e2b5b45852eba222`.
- Branch: `coco-2.1-isaac-integration`.
- `git status --porcelain=v1`: empty; clean before edits.
- 2.5 instrumentation was committed before this session: HEAD `bc843c7`, including
  mission request/ack/result logging, runner diagnostic child support, and `docs/data/isaac_fetch/coco25`.
- Approved Downloads plan installed exactly as `docs/MASTER_PLAN.md`; SHA256
  `e2d899d3b4f1b96a3958ace3833e32318985cc4edbcd05e12858ec91698aa03d`.

### Last 15 commits

```
bc843c7c9927f730dfa0e994e2b5b45852eba222 Instrument far-region fetch diagnosis and record idle-host blocker
25e8fdc8781bb547a882d33ed14fc44dd60afc76 Preserve COCO 2.4 matched reruns and unresolved far-region limits
668190252d9e3e893a50ba785ed8fb5c169a07e6 Keep rejected search continuation on the near side and preserve diagnosis
e4ed2292440b03f17b25b50c91da664ec1fe0dac Fix rejected search transit by retreating through the climbed corridor
98744ce2153807c684acc8530c17541cd83561a9 docs: record COCO 2.3 matched five-seed repeatability evidence
2e15706875c4850fe3a00200a9c5fd878e4b312d Record matched physical fetch completion and bound Gazebo DDS discovery
70d3f38c0e99de8f35c8a419f16e4ae00b84f672 Close Isaac perception-to-placement fetch path
589e1f1b8225a857d7c03ed9f019f53a5bd1efb9 Record Isaac fetch failures, measurements and complete regression evidence
dab3115fa2d460b0faf9f51eca94db962d6b3f3e Integrate articulated Isaac fetch interfaces with shared P03D autonomy
569b81ff744c2542498bd37201ef509b3ec4b949 Validate Isaac navigation on P03D branch and record evidence
dd508584d7c3c8993bff20d105842475e37c4f03 Port committed Isaac backend onto P03D autonomy baseline
8e518cf99b50347568d9e7c303ec80b18ef8c223 Record final clean adversarial Gazebo proof
ded8e5666c08a8e3bd7eea8f38184f850e54f4fc Record autonomous search matrix and regression evidence
77f2f2cda20c9dea2bdedbb47eeff867977e6e23 Validate perceived targets in region world corridor
e3259d4dbbe9c1d632ad265e14aae4d73ac3ab0f Wait for Nav2 map transform after search exit relocalization
```

### Worktrees (read-only inventory)

```
worktree /home/gautham/ros2_ws(personal)/src/coco-robot-ros2
HEAD 9ee4a52dccf8afb94b5ad7f6098877383a785c40
branch refs/heads/main

worktree /home/gautham/coco-infra-worktree
HEAD 23f372c62811b5bef07d02b9f38234adc58d5fb3
branch refs/heads/claude/docker-reproducibility

worktree /home/gautham/coco-isaac-21
HEAD bc843c7c9927f730dfa0e994e2b5b45852eba222
branch refs/heads/coco-2.1-isaac-integration

worktree /home/gautham/coco-isaac-backend
HEAD ffb3fc66b4ad64ada36e4675278e5e2b3a90aa07
branch refs/heads/p03-isaac-backend

worktree /home/gautham/coco-p03c-consolidation
HEAD 917bc59d2107aad64d9c0183db325fb96d9e9e83
branch refs/heads/p03c-consolidation

worktree /home/gautham/coco-p03d-target-search
HEAD 8e518cf99b50347568d9e7c303ec80b18ef8c223
branch refs/heads/p03d-autonomous-target-search

worktree /home/gautham/ros2_ws(personal)/src/coco-robot-ros2/.claude/worktrees/c2nav0-diagnosis
HEAD 12355022260684a8aa01633ae9f28615bc150e92
branch refs/heads/worktree-c2nav0-diagnosis

worktree /home/gautham/ros2_ws(personal)/src/coco-robot-ros2/.claude/worktrees/c2nav43-integration
HEAD d317d85ee6f1575c2620f4e467d7e322d0310bc0
branch refs/heads/c2nav49-integration

worktree /home/gautham/ros2_ws(personal)/src/coco-robot-ros2/.claude/worktrees/episode-gazebo
HEAD dfcbc4bad02e78530e7bcd683e4ffddff9d8e186
branch refs/heads/p03c-episode-gazebo

worktree /home/gautham/ros2_ws(personal)/src/coco-robot-ros2/.claude/worktrees/isaac-compat
HEAD 20a9619aac8124ed8aede7623250074b5eafd73e
branch refs/heads/isaac-compat-4x

worktree /home/gautham/ros2_ws(personal)/src/coco-robot-ros2/.claude/worktrees/lab1
HEAD a63a4c84145470c2fde5b384ddb088e56d4cde4d
branch refs/heads/lab3

worktree /home/gautham/ros2_ws(personal)/src/coco-robot-ros2/.claude/worktrees/p0-consolidation-merge
HEAD b55f24fc9f600d3293f8f98de21223ab00b59892
branch refs/heads/p0-consolidation-merge

worktree /home/gautham/ros2_ws(personal)/src/coco-robot-ros2/.claude/worktrees/p01-platform
HEAD 921f6d0bef1aaac4a890df3fb14efe04608dee02
branch refs/heads/worktree-p01-platform

worktree /home/gautham/ros2_ws(personal)/src/coco-robot-ros2/.claude/worktrees/p02-browser
HEAD b3c65985de6aa68f4701687f9b35a51e04239595
branch refs/heads/p03-episode-spec
```

## Inspection

Read/inspected README, PROJECT_STATE, CLAUDE, HOW_TO_RUN, architecture and episode
architecture, P03D search documentation, Isaac capability documentation,
RUNNING/setup and Docker instructions, CI, build script, historical 2.3/2.4/2.5
reports, git history and evidence directories. Historical documentation is not
substituted for current code. `evidence_directories.txt` records directories that
exist; it includes ignored runtime/cache-independent folders, not a claim that
all contents are committed. No other worktree was modified.

## Clean build and tests

Fresh, previously absent build/install destination: `/tmp/coco-m0-clean-build-20261005`.
Used `scripts/build_overlay.sh` with all nine CI packages and symlink install.
Explicit read-only dependency prefix:
`/home/gautham/ros2_ws(personal)/moveit_prefix/root/opt/ros/jazzy` because system
MoveIt is absent. Build passed 9/9; warnings retained in `clean_build_events.log`.
Then sourced this overlay and ran `colcon test` sequentially for the same nine
packages, followed by `colcon test-result --verbose`. No simulator launched.
No explicit ROS_DOMAIN_ID isolation was added to this invocation; results are
reported as observed, not as proof of runtime host qualification.

| Suite | Passed | Failed | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| coco_config | 92 | 0 | 0 | 0 |
| coco_mission | 365 | 0 | 0 | 0 |
| coco_moveit_config | 28 | 0 | 0 | 0 |
| coco_perception | 139 | 0 | 0 | 0 |
| coco_rl | 236 | 0 | 0 | 0 |
| coco_sim | 228 | 0 | 0 | 0 |
| coco_web | 574 | 1 | 0 | 0 |
| custom_teleop | 78 | 0 | 0 | 0 |
| gazebo_models | 220 | 0 | 0 | 0 |

Underlying pytest: **1961 tests, 1960 passed, 1 failed, 0 errors, 0 skipped**.
Colcon aggregation: **1964 tests, 1 failure, 0 errors, 0 skipped**, including
three CTest wrapper entries. Do not add these wrappers to the pytest count.
Raw XML is preserved in `test_results/`; counts in `test_counts.json`;
console and result logs beside this audit. CI execution for this session is
NOT VERIFIED; local passing suites are not promoted to the TESTED label.
Simulator bringup integration test was disabled by the existing default.

## Stop conditions and findings

1. **blocks M1** — clean-build suite failure:
   `coco_web/test/test_mission_view.py::test_no_executive_reason_is_missing_from_our_copy`.
   The committed mission constants RETREAT, RETREAT_FAILED,
   RETREAT_POSE_UNVERIFIED and RETREAT_TIMEOUT are missing from the mission view's
   REASONS inventory. Exact assertion retained in XML and clean_test_results.log.
   No fix applied because M0 explicitly says stop on clean-build test failure.
2. **blocks M1; plan-owner decision required** — current autonomy consumes
   simulator ground truth, contradicting non-negotiable rule 1 and the handoff's
   no-privileged-information assumption:
   - `gazebo_models/urdf/coco_robo2.xacro:556–563` defines the simulator
     OdometryPublisher at `/model/coco/odometry`.
   - `coco_sim/coco_sim/isaac/runtime.py:336` publishes the corresponding world
     odometry for fetch.
   - `coco_mission/scripts/mission_executive.py:284–285` subscribes;
     `observe()` passes that pose to the state machine at line 477, and navigation
     arrival checks explicitly use it (lines 513 onward).
   - `coco_rl/coco_rl/ramp_driver.py:274,296–312,359–374` uses ground-truth lateral
     position for autonomous region-centre control.
   - `coco_rl/coco_rl/ramp_env.py:264,389–407` prefers that ground-truth stream.
   - `docs/ARCHITECTURE.md` explicitly describes ground truth as an existing
     arrival-verification input. This is active control, not evaluator-only data.
   Moving these inputs out of autonomy requires behavior changes that M0 forbids.
   M1's planned evaluator publication/graph isolation alone does not remove the
   existing privileged inputs. Gautham must reconcile the plan with this baseline.
3. **M3 cleanup** — stale current-state claims: README and P03D document say Isaac
   full fetch is not demonstrated, while committed coco22/23/24 evidence records
   completion. PROJECT_STATE's current-branch header predates those results;
   CLAUDE still names main as the sole branch. Historical sections remain preserved.

These are preliminary M0.1 findings, not a completed M0.6 hygiene audit.
Duplicated mission/regions, all colour-lane paths, machine paths, duplicate launch
files/joint limits, full CI omissions and fresh-checkout scripts remain unaudited
because the stop condition fired. No deletion or behavior correction was made.

## Work not performed

No oracle implemented; no historical runs rescored; no oracle/mission disagreements
computed. Historical observer disagreements in the existing 2.3/2.4 reports were
read but are not new oracle verdicts. No environment mechanism or seed file created;
no ideas parked. No new simulation episodes or campaigns.

## Next step under the Master Plan

Resolve the M0 stop conditions with Gautham, resume remaining M0 checkpoints,
then independent milestone review and G0 decision. The next milestone after M0
is M1 — Evaluation harness and failure taxonomy; M1 has not started.
