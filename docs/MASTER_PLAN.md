# COCO Master Plan — Road to v2.0

Oct 5, 2026 · @Gautham Anil

## How to use this document

This plan is the single authority for what COCO becomes and in what order. Prompts and agent sessions execute it; they never redesign it.

Export this document as Markdown and commit it to the repo as `docs/MASTER_PLAN.md`. Every coding session reads it, plus `docs/STATUS.md`, before touching code.

**Authority order** (a lower item may never contradict a higher one):

1. **The repository** (code plus committed evidence) is the truth about what COCO *is* today.
2. **This master plan** is the truth about what COCO *will become* and in which order.
3. **`docs/STATUS.md`** records where the project currently stands inside this plan: current SHA, milestone, checkpoint, open failure classes, plan-change log.
4. **A milestone prompt** (written by ChatGPT) carries instructions for one checkpoint. It quotes this plan; it does not extend it.
5. **Agent reports** are claims to verify, never facts. A report becomes fact only when its evidence is committed and re-checkable.

**Roles:**

- **Gautham** owns the plan. He is the only one who can change scope, reorder milestones or pass a decision gate.
- **ChatGPT** turns one checkpoint at a time into a prompt, following the prompt contract in this document.
- **Coding agents** (Codex, Claude Code, Antigravity) execute one milestone at a time, inside its scope fence, and stop at its stop conditions.

**Change control:**

- The plan changes only at a milestone boundary, unless a safety or correctness blocker forces it.
- Every change is a dated entry in the plan-change log in `STATUS.md`: what changed, why, which evidence forced it.
- Any new idea that appears mid-milestone goes to `docs/IDEAS.md` with one line of motivation. It is not implemented, prototyped or "quickly tried."
- `IDEAS.md` is reviewed only at milestone boundaries. An idea enters the plan only if it closes a gap named in the competency map or a decision gate.

## North star: what finished COCO is

Finished COCO is a perception-driven mobile manipulator whose single autonomy stack runs unchanged on Gazebo and Isaac Sim (and on the real robot if M6 passes its gate). Its reliability is measured with confidence intervals, every failure class is explained causally, and anyone can reproduce the results with one command.

**Identity line** (use everywhere: README, paper abstract, LinkedIn headline):

> COCO is a ROS 2 mobile manipulator that searches for a requested object using RGB-D perception, navigates with Nav2, grasps and returns it under a single safety-arbitrated command path, and is evaluated across Gazebo and Isaac Sim with every failure traced to its first cause.

**What COCO is not:**

- a language-model robot
- a multi-robot system
- a general robotics framework
- a web platform (that is COCO Labs, a separate project)

The depth of one complete, measured system is the point. Breadth is not.

### v1.0 release (end of M4): the portfolio cut

1. Tagged `v1.0` with:
   - a Docker image for the Gazebo stack
   - a pinned Isaac environment manifest
   - one reproduction command per experiment
2. A cross-simulator benchmark report:
   - at least 30 held-out episodes per backend
   - Wilson 95% intervals
   - stage-level metrics
   - a first-divergence failure taxonomy
3. A failure-analysis write-up: each root cause fixed in M2 with its first-divergence evidence, the general fix and its regression test.
4. An architecture document with diagrams, and a safety case linking every arbiter requirement to the test that proves it.
5. A 60–90 second demo video and a 3–5 minute technical walkthrough.
6. A complete draft of Paper 1, posted as a preprint.

### v2.0 release (end of M7): the masterpiece

v2.0 is v1.0 plus:

- the M5 research extension: robustness study, and learned control only if its gate passed
- sim-to-real results, if M6 passed its gate
- Paper 2
- a polished project page

### Final acceptance test

At v2.0, a stranger must be able to answer each question from the repo alone, without asking Gautham.

| Question | Answered by |
| --- | --- |
| What is COCO physically? | README, URDF/USD, hardware page |
| What is the ROS 2 architecture? | `docs/ARCHITECTURE.md` with node/topic/action diagram |
| How does it decide where to search? | P03D search doc |
| How does it detect and localize a target? | Perception doc with geometry and validation gates |
| How does it grasp and place? | Manipulation doc, MoveIt config, magnet semantics |
| How is command authority controlled? | Safety case with requirement-to-test table |
| Why two simulators? | Benchmark report, fidelity section |
| How well does it work? | Benchmark tables with intervals |
| Why does it fail when it fails? | Failure taxonomy and analyzer output |
| Where does learning add value? | M5 report, including a "no" if that is the result |
| Can I run it? | `REPRODUCE.md`, Docker image, CI badge |

## Non-negotiable rules

These rules apply in every milestone and override any prompt. An agent that cannot finish a task without breaking one must stop and report, not work around it.

### Evidence labels

Every capability claim in docs, reports, posts and papers carries exactly one label.

| Label | Means |
| --- | --- |
| NOT VERIFIED | Claimed or planned; no evidence committed |
| IMPLEMENTED | Code merged; no automated test proves the behaviour |
| TESTED | An automated test exercises the behaviour and passes in CI |
| RUNTIME VERIFIED | Observed in at least one full simulated run on a qualified host, with the log committed |
| MEASURED | A metric over N episodes on a qualified host, reported with n and a 95% interval, with raw data committed |

"Reliable" may only be said about something MEASURED, and always with its number and interval.

### Integrity rules

1. **No privileged information.** Autonomy never receives target coordinates, teleports, or reads simulator ground truth. Ground truth lives only under the `/eval` namespace, and a CI test fails if any autonomy node subscribes to it.
2. **No seed-specific behaviour.** No code may branch on a seed, a layout or a scenario name.
3. **No tuning on test seeds.** Debug and tune on dev seeds only; held-out seeds are evaluated, never inspected for fixes (see the measurement protocol).
4. **No relaxing to pass.** Perception gates, costmap settings, tolerances, timeouts and retry counts change only with a written causal argument backed by trace evidence.
5. **One command path.** Every wheel command passes through the arbiter. No experiment, test or simulator adapter may bypass it.
6. **No unexplained parameter changes.** A hypothesis is written in the checkpoint notes before any parameter changes; the result is recorded after.
7. **Evidence is append-only.** Failed and aborted runs are kept. Excluded runs are listed with the reason. Nothing is deleted to make a table look better.
8. **Only qualified runs count.** A run counts as evidence only if host preflight passed (see M1).
9. **No parity claims.** Say "cross-simulator functional validation" unless a dedicated physical calibration study exists.
10. **`--fast` Gazebo mode stays banned.** It produced 531 tip-overs in 533 runs.
11. **Git safety.**
    - No `git clean`, `git reset --hard` or force-push without Gautham's explicit approval.
    - Never modify other worktrees, archived tags or the `coco-labs` repo.
12. **Every public number is traceable.** Any figure in a README, post or paper links to a committed evidence file and the SHA that produced it.

## Scope fence

The in-scope list below is exhaustive: work not on it does not happen before v2.0.

**The drift test.** Before any task starts, the agent states three things:

- the milestone
- the checkpoint
- the exit criterion the task advances

If it cannot name all three, the task is out of scope.

### Frozen components

These change only to fix a proven bug, and every change ships with a regression test.

- **`cmd_vel_arbiter` semantics.** The M3 C++ port must pass the same behavioural test suite as the Python version before it replaces it.
- **The `coco.v1` protocol.** Clients express intents, never ROS topics.
- **The P03D search architecture** and its region abstraction (lane\_1 to lane\_4).
- **Arm IK and the MoveIt trajectory interface.**
- **The 2.4 rejected-search retreat behaviour.**
- **The perception validation gate structure.** Individual thresholds change only under integrity rule 4.
- **Historical evidence directories** (`docs/data/...`). They are append-only.
- **The MuJoCo and PPO ramp work.** Archived and read-only, unless M5's gate explicitly reopens it.

### In scope

| Work | Milestone |
| --- | --- |
| Repo truth audit, `STATUS.md`, environment manifest, single success definition | M0 |
| Evaluation harness, host qualification, ground-truth oracle, trace capture, invariant analyzer | M1 |
| Root-cause fixes for measured failure classes, with regression tests | M2 |
| Isaac wheel odometry, IMU noise model, Isaac world/map alignment | M3 |
| C++ arbiter port, latency measurement, fault-injection tests, Docker, CI, observability | M3 |
| Cross-simulator benchmark, v1.0 release, Paper 1 | M4 |
| Perturbation robustness study; learned control only if its gate passes | M5 |
| ros2\_control hardware interface and real-robot runs, only if the hardware gate passes | M6 |
| v2.0 packaging, Paper 2, project page | M7 |

### Non-goals

These are rejected without discussion before v2.0.

- Vision-language models, LLM planners, natural-language commands
- Multi-robot or fleet behaviour
- New sensors beyond the current RGB-D camera, LiDAR, IMU and wheel encoders
- A new arm, a new base or new task types (doors, stacking, shelves)
- A third simulator, or extending MuJoCo beyond M5 needs
- Learned high-level search policy (four regions do not justify RL)
- COCO Labs or any web UI changes
- Cloud, Kubernetes, fleet dashboards
- Package renames, framework rewrites or restructures done for aesthetics
- Rendering or photorealism upgrades, unless the M4 benchmark shows perception fidelity drives failures

### Idea parking lot

`docs/IDEAS.md` holds one line per idea in this form:

```
date | idea | gap it would close | earliest milestone
```

Rules for the parking lot:

- Ideas are reviewed only at milestone boundaries.
- An idea that names no gap from the competency map or a decision gate stays parked.
- Agents may add to `IDEAS.md`. They never act on it.

## Robotics software engineer competency map

COCO already proves most of the robotics stack. The visible gaps are four:

- production C++
- system-level testing and observability
- deployment and reproducibility
- statistically credible evaluation

Those four gaps, not new features, decide the milestone content.

| Competency | Already proven in COCO | Gap | Closed in |
| --- | --- | --- | --- |
| ROS 2 architecture (nodes, actions, TF, lifecycle) | Full mission stack, `coco.v1` protocol | Executor, clock-domain and QoS correctness under slow sim time | M2 |
| Navigation (Nav2, AMCL, costmaps) | 10/10 goal set, P03D search | Far-region failures unexplained | M2 |
| Perception (RGB-D geometry, validation) | 16/16 grid tests within about ±2 mm, adversarial lane-2 run | IMPLAUSIBLE\_SIZE unexplained | M2 |
| Manipulation (IK, MoveIt, grasp) | IK error about 1e-16 m, physical grasp and release in both simulators | None; frozen | — |
| Safety-critical design | Single arbitrated command path | No written safety case, no fault-injection or latency evidence | M3 |
| C++ | Little in COCO | Arbiter port; ros2\_control hardware interface if M6 runs | M3, M6 |
| Simulation | Gazebo and Isaac backends under one contract | Isaac ideal odometry, noiseless IMU, placement offset | M3 |
| Testing | Thousands of unit tests | No automated full-mission regression with a trustworthy oracle | M1 |
| Debugging and observability | Manual log forensics | Synchronized traces, MCAP bags, first-divergence analyzer, executor tracing | M1 |
| Deployment and DevOps | Partial CI | Docker image, pinned environment, one-command reproduction, CI on every PR | M3 |
| Evaluation science | Small matched runs (n = 5) | Held-out seeds, n ≥ 30, intervals, ablations | M1, M4 |
| Learning | PPO ramp; classical PD matched it | A justified learned-vs-classical comparison, or a documented "not needed" | M5 |
| Hardware integration | ESP32 firmware skills (outside COCO) | Real-robot evidence | M6 (gated) |
| Technical communication | Detailed internal reports | Paper, demo video, architecture docs | M4, M7 |

The two rows hiring managers for robotics software and deployment roles probe hardest are C++ and deployment. That is why M3 exists as its own milestone, rather than being folded into the release work.

## Milestone overview

Eight milestones run strictly in order, and v1.0 at the end of M4 is the portfolio cut.

&#91;embedded content: COCO roadmap · 8 milestones, 5 gates\]

M6 runs only if G6 passes; otherwise M5 leads straight to M7. Week numbers are estimates counted from the start of M0.

## M0 — Ground truth and project control plane

M0 establishes the verified starting state and the files that keep every later session on the rails. It changes no robot behaviour.

Estimated effort: about 1 week.

**Why first:** the 2.5 report did not record its final SHA, and the 2.3 observer disagreed with physical completion. Nothing measured later is trustworthy until the starting point and the definition of success are pinned.

### Checkpoints

1. **M0.1 Repo truth.** Record a set of facts in `docs/m0/AUDIT.md` without modifying anything:
   - `git status`, branch, last 15 commits and HEAD SHA in `/home/gautham/coco-isaac-21`
   - the list of worktrees (read-only)
   - whether the 2.5 instrumentation is committed
   - which evidence directories exist
   - which test suites pass from a clean build, with counts
2. **M0.2 Control files.** Commit `docs/MASTER_PLAN.md` (this document), `docs/STATUS.md` and an empty `docs/IDEAS.md`. `STATUS.md` holds:
   - current SHA
   - current milestone and checkpoint
   - the capability table with evidence labels
   - open failure classes with evidence paths
   - the seed policy
   - the plan-change log
3. **M0.3 Environment manifest.** Write a script that records the environment and stores the output with every run:
   - Ubuntu, ROS 2, Nav2, Gazebo and Isaac Sim versions
   - NVIDIA driver, GPU and VRAM
   - Python package lock
   - the RMW implementation and DDS configuration
4. **M0.4 Single success oracle.** Write `docs/SUCCESS_DEFINITION.md` and implement it as one evaluator module, scored from ground truth, not from the mission's self-report. A run is a physical success only if all of these hold:
   - the requested target is at rest inside the home placement zone (radius chosen and justified in the doc)
   - no non-requested cylinder moved more than a set displacement
   - the robot ended inside the home zone
   - no arbiter violation was logged
   - the run finished within the episode time budget
5. **M0.4b Oracle back-check.** The mission's own verdict is recorded beside the oracle verdict, never instead of it. Re-score the 2.3 and 2.4 runs where data allows, and document every disagreement.
6. **M0.5 Seed policy.** Commit `eval/seeds.yaml`:
   - **Dev seeds:** every seed already run (including 0–9 and the P03D seeds) is a dev seed.
   - **Held-out test seeds:** a fresh, disjoint range of at least 60 seeds, never used for debugging.
   - **Reserve:** a second untouched range kept for M4.
7. **M0.6 Hygiene audit.** Search for the items listed in the original handoff:
   - duplicated mission logic or region definitions
   - colour-to-lane leftovers
   - hardcoded machine paths
   - duplicate launch files and joint limits
   - stale docs and CI omissions
   - scripts that fail from a fresh checkout

   Classify each finding as *blocks M1* (fix now), *M3 cleanup* or *historical, keep*. Nothing is deleted in M0.

### Exit criteria

- `STATUS.md` names the true HEAD SHA, and the worktree is clean.
- Clean-build test counts are recorded.
- The success oracle is implemented, unit-tested, and has re-scored the historical runs.
- `eval/seeds.yaml` is committed.
- The audit report is committed, with every finding classified.

### Stop conditions

Stop and report to Gautham if any of these is true:

- HEAD is not on `coco-2.1-isaac-integration`.
- Uncommitted work exists.
- The test suites fail on a clean build.
- The repo contradicts the handoff in a way that changes this plan.

## M1 — Evaluation harness and failure taxonomy

M1 builds one command that runs a qualified batch on either backend, records synchronized traces with ground truth, scores each run with the oracle, and labels every failure with its first violated invariant. Then it measures the baseline.

Estimated effort: about 3 weeks, including 2–3 nights of batch runs.

**Why before any fix:** the four known failing seeds (Isaac 6/7, Gazebo 6/7) may not be the dominant failure modes. Fixing them blind risks overfitting to layouts. The harness is also the instrument every later milestone reuses: M2 regression, M3 ablations, M4 benchmark, M5 sweeps and M6 real-robot runs.

### Checkpoints

1. **M1.1 Host qualification preflight.** The runner refuses to start unless all of these hold:
   - no foreign gazebo, isaac or ROS 2 processes outside an allowlist
   - 1-minute load average and free RAM/VRAM within committed thresholds
   - no orphaned DDS shared-memory segments

   During the run it samples CPU, RAM, VRAM and the sim real-time factor at 1 Hz. A mid-run violation marks the run *unqualified*. The preflight itself must never launch a simulator.
2. **M1.2 Ground-truth oracle.** Both backends publish robot pose, every cylinder pose and target dimensions under `/eval/ground_truth/...`. A launch test inspects the ROS graph and fails if any non-eval node subscribes to `/eval`.
3. **M1.3 Trace capture.** Each run writes MCAP rosbag2 data to a fixed topic list:
   - mission, search and recovery state
   - Nav2 action goal, status, feedback and result, with UUIDs
   - `/amcl_pose`, `/tf`, odometry
   - throttled global and local costmap snapshots
   - velocity before and after the arbiter
   - perception diagnostics
   - `/eval`

   Each run gets a standard directory: `manifest.json`, `env.json`, `host_metrics.csv`, `logs/`, `bag/`, `oracle.json`, `analysis.json`. Summaries are committed; full bags are kept outside git, with a hash in the manifest. Bags are retained for all failures and for 2 controls per batch.
4. **M1.4 Perception diagnostics.** A new diagnostic message is published for every candidate, logging only, with no behaviour change. It records:
   - stamp, frame and colour
   - centroid and 3D extents
   - point count and depth statistics
   - range and bearing
   - whether the mask touches the image edge
   - the accept or reject reason
5. **M1.5 Nav2 server-side evidence.** Record what the server side saw, not just the client:
   - lifecycle state of `planner_server`, `controller_server` and `bt_navigator` at each goal
   - server-side goal receipt and acceptance
   - mission-executive callback durations

   For runs reproducing the acknowledgement failure, capture executor timing with `ros2_tracing` if it runs on the host.
6. **M1.6 Invariant analyzer.** An offline tool reads a run directory, evaluates the invariant catalog (section below) in time order, and writes `analysis.json`. Its output names:
   - the first violated invariant
   - the mission stage
   - the sim timestamp
   - the 10-second context window

   Every invariant has a passing and a failing synthetic fixture in unit tests. The analyzer is replayed on historical failing runs where their data allows.
7. **M1.7 Batch runner.** One command:

   ```
   eval run --backend {gazebo|isaac} --seeds {dev|testA|list} --repeats k
   ```

   It runs sequentially and verifies teardown between runs (no orphan processes). It is resumable after a crash. Each batch writes a summary table: oracle verdict, mission verdict, invariant label, sim time, wall time and mean RTF.
8. **M1.8 Baseline campaign.** Three parts, about 140 runs, run unattended over several nights:
   - **Determinism:** seeds 6 and 7 × 3 repeats per backend, plus control seeds 5 and 8 × 2 repeats per backend (20 runs).
   - **Breadth:** 30 new dev seeds per backend (60 runs), producing a frequency-ranked failure taxonomy.
   - **Held-out "before" number:** test set A, 30 seeds per backend (60 runs). Reported only as aggregates with Wilson intervals; individual held-out traces are not opened for debugging.

### Exit criteria

- One command runs a qualified batch on either backend; the preflight provably blocks a dirty host (tested).
- The `/eval` isolation test passes in CI.
- Every dev failure carries an invariant label. Failures marked UNCLASSIFIED are listed explicitly as analyzer work items, and stay under 10% of failures.
- Every failing seed has a determinism verdict: deterministic, intermittent or not reproduced.
- `docs/m1/BASELINE.md` holds the failure Pareto per backend and the held-out set A completion rates with intervals.

### Forbidden in M1

No autonomy behaviour changes, even when a cause looks obvious. Obvious causes are written into `STATUS.md` as M2 hypotheses.

### Stop conditions

- The host cannot be qualified for Isaac runs (for example, VRAM limits make most runs unqualified).
- A single batch exceeds the disk budget.
- The oracle and the physical outcome disagree on any run.

## M2 — Reliability closure

M2 fixes failure classes in the order M1's Pareto ranks them. Each fix needs a proven cause, a general fix and a regression test.

Estimated effort: 3–5 weeks, time-boxed at 6.

### The root-cause loop (one pass per failure class)

1. **Hypothesis.** Write the hypothesis and the observation that would *distinguish* it from the alternatives. Do this before touching code.
2. **Reproduce.** Reproduce on dev seeds, using M1's determinism verdict.
3. **Prove.** Show the first-divergence trace, plus one discriminating experiment that changes a single variable. Its outcome must match the hypothesis and contradict the alternatives.
4. **Fix.** Fix the mechanism, never the scenario.
5. **Regression test.** Add a test that fails before the fix and passes after, using a synthetic or replayed trace.
6. **Rerun.** Rerun the affected dev seeds × 3 and the control seeds × 2 on both backends.
7. **Record.** Add an entry to `docs/m2/ROOT_CAUSES.md`: hypothesis, evidence, rejected alternatives, fix, test, before and after.

### Starting hypotheses from existing evidence

M1 may reorder or replace these. They are where to look first, not conclusions.

**Class A: Isaac Nav2 acknowledgement failures.**

- **A1 Clock domain** (test first). A timeout or rate in the mission or action-client path runs on wall time while Isaac runs at roughly 0.35–0.6× real time. Precedent: 2.2 found perception aged with wall time.
  - *Discriminator:* the failures correlate with low RTF, and ack latency is normal when measured in sim time.
  - *Fix shape:* every timeout in the autonomy path uses the node's sim-aware clock, enforced by a lint or test.
- **A2 Executor starvation** (test first). The mission executive blocks inside a callback while waiting on a future, so the goal response is never processed. Precedent: 2.2 found callback starvation.
  - *Discriminator:* the server logs show the goal accepted while the client never handles the response.
- **A3 Server not ready.** The server is not active, or its costmap is not current.
  - *Discriminator:* lifecycle state and server receipt logs.
- **A4 Discovery.** A DDS discovery or participant problem.
  - *Discriminator:* the server never saw the goal, and the graph shows missing or duplicate endpoints.

**Class B: Gazebo planner start occupied after handoff.**

- **B1** The retreat ends physically inside the inflation zone (ground-truth pose against the costmap).
- **B2** AMCL accepted a wrong pose (AMCL against ground truth at handoff).
- **B3** The costmap holds stale marks (snapshot against ground-truth occupancy).
- **B4** TF timing at handoff.

Allowed fix shapes for class B:

- a handoff precondition that queries start-cell cost and continues the retreat until it is below the inscribed cost
- a correct reseed path
- a costmap clear, if staleness is proven

Shrinking inflation or footprint is not allowed.

**Class C: Gazebo IMPLAUSIBLE\_SIZE.**

- **C1** The mask is truncated at the image edge.
- **C2** Clusters merged with an adjacent or occluding object.
- **C3** The target was really tipped or displaced (ground-truth orientation).
- **C4** The size computation is wrong at range or at an oblique angle (measured extents against the expected projected size from ground truth).

Allowed fix shapes for class C:

- correct the geometry
- a re-centre-and-reobserve step for truncated views

Widening the size gate without evidence is not allowed.

**Physics-induced failures** (Isaac DESCENT\_TIMEOUT, Gazebo ODE CLOCK\_STALLED):

- A failure counts as simulator-induced only with direct evidence, such as an ODE assertion or a solver error in the log.
- Simulator-induced failures stay in the denominator. Reports give the all-runs rate as the headline and the excluding-simulator rate beside it.

### Exit criteria

- Every failure class at 10% or more of dev failures, and every safety-relevant one, is in one of three states:
  - root-caused and fixed
  - proven simulator-induced
  - explicitly deferred through gate G2, with its reason
- Held-out set A is rerun, and before and after rates are reported with Wilson intervals.
- Target: at least 27/30 physical completions per backend (lower 95% bound about 0.74).
- No safety regression: the arbiter suite passes, and retreats displace zero non-requested cylinders.

### Gate G2 (end of M2)

If the target is missed:

- Gautham chooses one more M2 iteration, at most two in total, or accepts the measured number and documents it.
- M2 never runs open-ended.
- An honestly reported 80% with explained failures is a stronger result than a 95% nobody can explain.

## M3 — Fidelity and production engineering

M3 removes the Isaac shortcuts that confound the cross-simulator comparison and adds the C++, safety-case, Docker and CI evidence that industry roles look for. It runs as two tracks.

Estimated effort: 3–4 weeks.

### Track 1: Isaac fidelity

Each change is a controlled ablation: same dev seeds, old configuration against new, with results in `docs/m3/FIDELITY_ABLATIONS.md`. This table later becomes a paper section on how simulator fidelity choices change measured reliability.

1. **M3.1 Wheel-encoder odometry.** Isaac odometry is computed from wheel joint states through the same differential-drive kinematics node every backend uses. One implementation, not one per simulator. Ideal pose odometry survives only as a labelled ablation configuration.
2. **M3.2 IMU noise.** The IMU noise and bias parameters match the Gazebo sensor configuration, are documented in one place, and are shared by both backends.
3. **M3.3 Isaac placement offset.** Isaac places about 3× worse than Gazebo (mean 0.289 m against 0.093 m), despite having ideal odometry. Use ground truth to separate three causes:
   - robot final-pose error, which points at map/world misalignment or goal tolerance and skid-steer overshoot
   - object offset at release, which points at magnet or detach dynamics
   - map-frame offset

   Fix the proven cause.
4. **M3.4 Drive ceiling.** Measure the fraction of time the 2 Nm wheel-torque ceiling saturates. Change it only if it is shown to bind and a physical motor spec justifies another value.

### Track 2: Production engineering

1. **M3.5 C++ arbiter.** Port `cmd_vel_arbiter` to an `rclcpp` lifecycle component with the same interface and parameters.
   - **Equivalence.** The existing behavioural tests become black-box launch tests that run against both implementations. The C++ version replaces Python only when every test passes, and the Python version is archived, not deleted.
   - **Latency.** Measure input-to-output latency and jitter (P50 and P99) for both versions, labelled host-dependent.
   - **Fault injection.** Stale source, source timeout, non-finite velocities, priority conflict, command burst, upstream node crash.
2. **M3.6 Safety case.** `docs/SAFETY_CASE.md` lists numbered requirements, for example: single authority, stop within a stated time after source timeout, non-finite rejection, priority order, stop latch. Each requirement links to the test that proves it. Coverage target: every requirement has at least one test.
3. **M3.7 Docker and reproducibility.** A reproducible image for the Gazebo stack (ROS 2 Jazzy, Gazebo, Nav2, MoveIt, COCO) and a devcontainer. For Isaac: a documented install and the pinned environment manifest. Containerize Isaac only if it fits the 6 GB GPU and the time box.
4. **M3.8 CI.** GitHub Actions on every PR:
   - `colcon` build
   - unit tests and lint
   - C++ built with warnings as errors, plus `clang-tidy`
   - the `/eval` isolation test
   - Docker image build

   Simulator smoke runs go on a nightly self-hosted runner on the laptop if that proves stable; otherwise they run before each release. GPU simulation is not attempted on hosted runners.
5. **M3.9 Observability.** A committed Foxglove layout for COCO's MCAP traces, and a short guide: "open a failed run and find its first divergence in 5 minutes".
6. **M3.10 Cleanup.** Resolve the M0.6 items classified *M3 cleanup*.

### Exit criteria

- Wheel odometry is the Isaac default, and the ablation table is committed.
- The placement offset is explained, and fixed if its cause is in autonomy or the world model.
- The C++ arbiter is live with all behavioural and fault-injection tests passing, and latency is reported.
- Every safety requirement maps to a test.
- The Docker image builds from scratch in CI, and CI is green on main.
- Dev control seeds still pass on both backends.

If the fidelity changes expose new failure classes, apply the M2 root-cause loop inside M3, time-boxed at 2 weeks. Anything left over is carried into M4 as a documented limitation.

Held-out set A is not rerun in M3. The next held-out measurement is M4's.

## M4 — Cross-simulator benchmark and v1.0 release

M4 produces the headline numbers on untouched seeds, packages COCO as a release a stranger can reproduce, and drafts Paper 1. v1.0 is the portfolio cut: after M4, COCO is presentable even if nothing else ships.

Estimated effort: about 3 weeks.

### Checkpoints

1. **M4.1 Final benchmark.** Run held-out set B, the reserve that has never been touched: at least 30 seeds per backend, 50 if the nights allow. The report is generated by script from committed data, with no hand-typed numbers.

   | Stage | Metrics |
   | --- | --- |
   | Navigation | goal success, path length, final pose error against ground truth, time, recovery count |
   | Localization | AMCL error against ground truth (distribution) |
   | Perception | detection rate, target pose error, false rejection rate; false acceptances (must be 0) |
   | Manipulation | grasp success, lift height, retention through carry, placement error |
   | Mission | completion with Wilson 95% interval, failure-stage distribution, sim and wall time, mean RTF |
   | Safety | arbiter violations and non-requested cylinder displacements (both must be 0) |
2. **M4.2 Cross-simulator agreement.** Pair outcomes per seed (both succeed, both fail, disagree) and test the disagreement with McNemar's test. Explain every disagreeing seed with its analyzer label. Report the evidence trail as set A in M1, set A after M2, and set B in M4.
3. **M4.3 Documentation.** Write the release documents:
   - `README.md` rewritten around the identity line
   - `docs/ARCHITECTURE.md` with node, topic and action diagrams and the simulator boundary
   - `REPRODUCE.md` with the exact command that regenerates each table
   - `RESULTS.md`
   - `LIMITATIONS.md` listing every known approximation, from magnet semantics to the drive ceiling and world differences
4. **M4.4 Videos.** Two videos:
   - **60–90 second demo:** a colour is requested, the robot rejects a wrong lane, detects the target with the camera overlay, grasps, returns and places. Split-screen Gazebo and Isaac, ending on the measured completion rate.
   - **3–5 minute technical walkthrough:** architecture, the harness, one real failure traced to its first divergence in Foxglove, and the results.
5. **M4.5 Paper 1.** A full draft, posted as a preprint (see the publication plan).
6. **M4.6 Release.** Tag `v1.0`. The GitHub release carries the evidence summaries and the Docker image reference.

### Exit criteria

- Every number in `RESULTS.md` regenerates from committed data with one command.
- Every limitation is listed.
- Both videos are published.
- The Paper 1 draft is complete.
- `v1.0` is tagged.

No new capability is added in M4.

## M5 — Research extension: robustness and gated learned control

M5 asks one research question: **how robust is a full classical autonomy stack to changes in physics, sensing and timing, across two simulators, and where (if anywhere) does learned control earn its place?** The robustness study always runs; learned control runs only if gate G5 passes.

Estimated effort: about 6 weeks.

### M5.1 Perturbation robustness study (always runs)

1. **Choose factors.** After M4, choose at most 4 perturbation factors, aimed at the weakest stage the M4 benchmark identified. Candidates:
   - floor friction
   - payload mass
   - depth and LiDAR noise
   - command latency
   - wheel torque ceiling
   - target placement jitter
2. **Design.** Sweep each factor one at a time across 3 levels around nominal. Add one small interaction design for the two strongest factors. Use at least 20 runs per cell per backend.
3. **Budget.** At most 40 hours of qualified runs, roughly 500 episodes at about 4.5 minutes each. Factor count shrinks before n per cell does.
4. **Outputs.** For each backend:
   - completion and failure-stage distribution against each factor
   - the factor level where completion first drops below the M4 interval
   - whether the two simulators break at the same place for the same reason (sim-to-sim robustness)

### Gate G5: does learned control get built?

Learned control is built only if the M4 or M5.1 evidence shows all three of these:

1. A measured control-layer gap: a low-level sub-skill (for example, skid-steer yaw tracking on the ramp, or traversal under friction and payload variation) that degrades below the M4 interval under a factor.
2. A reasonable classical effort fails to close it: gain scheduling or feedforward tried, and documented.
3. A pilot shows training fits the laptop: Isaac Lab, camera-free, headless, with enough parallel environments on 6 GB VRAM; otherwise the existing MuJoCo setup (about 3,712 steps/s measured).

If G5 fails, M5 publishes the robustness study plus a short, evidence-backed note on why learned control is not justified for COCO's task. That is a legitimate result, consistent with the earlier finding that a classical PD reached about 98% where PPO was expected to be needed.

### M5.2 Learned versus classical control (only if G5 passes)

1. **Scope.** Train a policy for the one sub-skill G5 identified, never the whole mission. Its output still passes through the arbiter.
2. **Baselines.** The current classical controller and the best classical improvement from G5's attempt.
3. **Protocol.** Train in one simulator and evaluate zero-shot in the others with the M1 harness, same seeds and same perturbation levels.
4. **Report.** Completion, tracking error and failure stage, with intervals. A null or negative result is published, not hidden.

### Exit criteria

- The robustness report is committed with its raw data.
- G5's decision is recorded with its evidence.
- If G5 passed, the learned-versus-classical comparison is committed with intervals.
- A Paper 2 draft exists (see the publication plan).

## M6 — Sim-to-real (gated)

M6 runs only if gate G6 passes. Otherwise it is skipped and written up as future work, and v2.0 ships without it.

Estimated effort: 6–8 weeks if it runs.

### Gate G6

All of these must hold:

- M4 is complete.
- A physical COCO exists whose dimensions, wheel layout, arm and sensors (RGB-D, LiDAR, IMU, encoders) match the URDF closely enough that one robot description serves both, after calibration.
- Its motor drivers work.
- A hardware emergency stop exists that is independent of software.
- A safe, repeatable test area can reproduce the lane layout.

If the real robot differs, the URDF is updated to match it *before* M6 starts, and M4's simulation numbers are not reinterpreted.

### Checkpoints (if G6 passes)

1. **M6.1 Hardware interface.** A C++ `ros2_control` `SystemInterface` for the base and arm, talking to the ESP32 over serial or micro-ROS. It uses the same controllers and kinematics as simulation, and every command still passes through the arbiter.
2. **M6.2 System identification.** Identify the physical parameters:
   - wheel radius and track width (UMBmark-style square test)
   - motor step response
   - command latency
   - camera intrinsics and extrinsics

   Simulation parameters change only through this documented identification.
3. **M6.3 Staged bring-up.** One stage at a time, each with its own logged evidence:
   - teleop through the arbiter
   - odometry accuracy
   - Nav2 goals
   - perception at measured target placements
   - grasp and lift
   - full fetch
4. **M6.4 Real benchmark.** At least 20 real full-fetch runs, scored by the same success definition with physically measured placement. Fewer runs are reported honestly as what they are.
5. **M6.5 Gap table.** The same stage metrics side by side for Gazebo, Isaac and the real robot. Every gap gets a stated cause or is marked unexplained.

### Exit criteria

- Gap table committed.
- Real-run videos and logs archived.
- Hardware setup documented well enough to rebuild.

## M7 — v2.0 final release

M7 closes the project: every question in the final acceptance test is answered from the repo, Paper 2 is submitted, and COCO is frozen.

Estimated effort: about 2 weeks.

1. **M7.1 Acceptance pass.** Walk the acceptance-test table question by question, with a fresh reader (a friend or a fresh agent session given only the repo). Fix every gap they hit.
2. **M7.2 Project page.** A GitHub Pages site for the COCO robot, separate from COCO Labs. It carries the identity line, the demo video, the architecture diagram, the results with intervals, links to both papers and the reproduction guide.
3. **M7.3 Data archive.** Archive the benchmark summaries and selected MCAP traces with a citable DOI (for example, Zenodo), so the papers can cite the data.
4. **M7.4 Papers.** Paper 2 submitted, and Paper 1 revised from reviewer or reader feedback.
5. **M7.5 Release.** Tag `v2.0`, with a final 2–3 minute video covering the whole story: problem, system, failures found, numbers, simulator comparison, and the real robot if M6 ran.
6. **M7.6 Freeze.** COCO enters maintenance mode. Ideas left in `IDEAS.md` seed a new project; they are not added to COCO.

## Measurement protocol

Every campaign is pre-registered, runs on qualified hosts, is scored by the one oracle, and is reported with n and a 95% interval. Anything else is an anecdote, not a result.

### Pre-registration

Before any batch, commit a campaign file (`eval/campaigns/<name>.yaml`) holding:

- the seed set
- backends and configurations
- the hypothesis
- the primary metric
- the run count

Results are written against that file. Changing the plan after seeing results means a new campaign, never an edit.

### Seed sets

| Set | Size | Allowed use | Used in |
| --- | --- | --- | --- |
| Dev | all seeds run so far + 30 new | Debugging, tuning, ablations | M1–M3, M5 |
| Test A | 30 | Aggregate before/after only; traces never opened for fixes | M1 (before), M2 (after) |
| Test B | 30–50 | Final benchmark and M5 nominal reference only | M4, M5 |

If a test-set trace must be opened to understand a failure, that seed moves to dev permanently and is replaced.

### Statistics

Completion rates are reported as k/n with the Wilson 95% interval:

```latex
\frac{\hat p + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat p(1-\hat p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}, \quad z = 1.96
```

The other metrics:

- **Paired cross-simulator outcomes** (same seed, two backends) use McNemar's test.
- **Continuous metrics** (pose error, time, lift height) are reported as median and IQR, plus a bootstrap 95% interval on the mean.
- **Configuration comparisons** report the difference with its interval. "Improved" is claimed only when that interval excludes zero.

Reference intervals, to keep claims honest:

| Result | Wilson 95% interval |
| --- | --- |
| 3/5 (Isaac in 2.3) | 0.23 – 0.88 |
| 4/5 (Gazebo in 2.3) | 0.38 – 0.96 |
| 24/30 | 0.63 – 0.91 |
| 27/30 (M2 target) | 0.74 – 0.97 |
| 30/30 | 0.89 – 1.00 |
| 45/50 | 0.79 – 0.96 |

### Run hygiene

- Every run records:
  - SHA
  - environment manifest
  - host metrics
  - mean RTF
  - oracle verdict
  - mission verdict
  - analyzer label
- Unqualified runs are excluded from rates but listed with the reason.
- Every table cell links back to its run IDs and the generating script.

## Invariant catalog

The analyzer checks these invariants in time order and labels each run with the first one violated. This list is the starting catalog for M1.

Thresholds are not invented here. They are derived from successful control runs in M1 (for example, the P99 of the control distribution plus a stated margin) and committed alongside the analyzer. Invariants that use ground truth exist only in the analyzer, never in autonomy.

| ID | Invariant | Stage | Uses ground truth |
| --- | --- | --- | --- |
| I01 | Host qualified; RTF above floor | All | No |
| I02 | Sim clock advancing; no stall beyond limit | All | No |
| I03 | Required TF chains present and fresh (sim time) | All | No |
| I04 | AMCL pose within limit of the true pose | All | Yes |
| I05 | Odometry displacement agrees with true displacement over a window | All | Yes |
| I06 | Arbiter output follows the selected source within latency; nothing bypasses it | All | No |
| I07 | Non-zero command produces base motion within a window (no stall or push) | Motion | Yes |
| I08 | Nav2 servers active before each goal | Navigation | No |
| I09 | Goal acknowledged within limit (sim time), server receipt logged | Navigation | No |
| I10 | Planner start-cell cost below inscribed at request time | Navigation | No |
| I11 | Planner goal cell free | Navigation | No |
| I12 | Costmap fresh; no lethal marks where the true world is free near the robot | Navigation | Yes |
| I13 | Plan returned within limit | Navigation | No |
| I14 | Retreat ends with clearance above limit and start cost below inscribed | Recovery | Yes |
| I15 | RGB and depth fresh and synchronized | Perception | No |
| I16 | Candidate extents consistent with expected projected size | Perception | Yes |
| I17 | Accepted target pose within limit of the true pose | Perception | Yes |
| I18 | No false acceptance (accepted candidate is the requested target) | Perception | Yes |
| I19 | No non-requested cylinder displaced beyond limit | All | Yes |
| I20 | MoveIt execution succeeds, joint tracking error within limit | Manipulation | No |
| I21 | Attachment only inside the proximity gate; lift reaches minimum height | Grasp | Yes |
| I22 | Target stays attached through carry | Carry | Yes |
| I23 | Fingers open before detach; target at rest after placement | Place | Yes |
| I24 | Physics sane: no solver errors, no non-finite poses, roll and pitch within tip limit | All | Yes |
| I25 | No stage exceeds its time budget without progress | All | No |

When a failure stays UNCLASSIFIED, the fix is a new invariant (with fixtures), never a relabel. Catalog changes are logged in `STATUS.md`.

## Prompt contract for ChatGPT and coding agents

ChatGPT writes **one prompt per milestone**, and the agent works through all of that milestone's checkpoints without pausing unless a stop condition fires. A milestone may be split into at most two prompts, and only where a human action sits in the middle: overnight batch runs, or a gate decision.

### What ChatGPT must and must not do

ChatGPT **must**:

- copy the milestone's objective, checkpoints, exit criteria and stop conditions verbatim from this plan
- take the starting SHA from `STATUS.md`

ChatGPT **must not**:

- add objectives, features or "while you're there" improvements
- merge milestones, or rename them
- soften exit criteria
- invent numbers or thresholds
- recommend tools or approaches this plan does not name

If ChatGPT thinks the plan is wrong, it says so to Gautham in plain text outside the prompt. The prompt itself still follows the plan.

### Required prompt sections

1. **Header:** milestone ID and title, plan date, starting SHA, branch, worktree path.
2. **Read first:** `docs/MASTER_PLAN.md`, `docs/STATUS.md`, and the milestone's input documents.
3. **Objective:** verbatim.
4. **Checkpoints:** verbatim, each with the evidence it must produce.
5. **Scope fence:** packages and files the agent may change, the frozen-component list, and the non-goals list.
6. **Integrity rules:** the full list, by reference, with the ones most relevant to this milestone restated.
7. **Resource rules:**
   - 6 GB VRAM and 16 GB RAM
   - never run Isaac and Gazebo at the same time
   - focused tests during work, the full suite only at checkpoint end
   - no expensive rerun without a written hypothesis
8. **Git rules:**
   - one or more commits per checkpoint, prefixed `[M1.3]`-style
   - `STATUS.md` updated at each checkpoint
   - no destructive commands; never touch other worktrees or `coco-labs`
9. **Exit criteria** and **stop conditions:** verbatim.
10. **Final report format:** the template below.

### Agent final report template

```
Milestone / checkpoints completed:
Start SHA → end SHA (branch, worktree clean? y/n):
Per checkpoint: what changed | evidence file(s) | evidence label
Tests run: suite → passed / failed / skipped
Sim runs: campaign file | qualified / unqualified counts | results
Deviations from the plan (and why):
Hypotheses opened / confirmed / rejected:
Ideas parked in IDEAS.md:
Stop condition hit? which one:
Next step according to MASTER_PLAN.md:
```

### Verification after every milestone

A separate review session (a fresh agent, ideally a different product from the one that did the work) receives only the repo, this plan and the report. It checks three things:

- that the commits exist and the worktree is clean
- that a sample of the claimed tests pass
- that every evidence file named in the report exists and supports its label

The milestone is closed in `STATUS.md` only after this review passes.

## Publication plan

COCO supports two papers. Neither contribution is a new algorithm; both are honest empirical systems contributions, which is exactly what the evidence can carry. More than two papers from one project reads as salami-slicing and weakens both.

### Paper 1: cross-simulator failure analysis (drafted in M4)

**Working title:** *One Autonomy Stack, Two Simulators: Invariant-Based Failure Attribution for Perception-Driven Mobile Manipulation in Gazebo and Isaac Sim.*

Contributions:

1. An open ROS 2 mobile-manipulation stack that runs unchanged on two simulators behind one contract, with a single arbitrated command path.
2. An invariant-based first-divergence analyzer that labels the first cause of failure in long-horizon missions, using simulator ground truth that the autonomy is provably isolated from.
3. A pre-registered paired benchmark on held-out seeds, with intervals, a failure taxonomy, before-and-after root-cause case studies, and fidelity ablations (ideal against wheel odometry, noiseless against noisy IMU).

Structure:

- Introduction and related work
- System
- Method: oracle, invariants, protocol
- Experiments: baseline, root-cause studies, ablations, final benchmark, cross-simulator agreement
- Limitations
- Reproducibility statement

Related work must cover at least runtime monitoring and verification for ROS, simulator benchmarking and sim-to-sim gaps, and mobile-manipulation benchmarks. Do this literature review at the start of M4.5. If prior work already does exactly contribution 2, reframe around contribution 3 rather than overclaiming.

### Paper 2: robustness and learned control (drafted in M5)

**Working title:** *Where Does a Classical Mobile-Manipulation Stack Break? A Cross-Simulator Perturbation Study.*

If G5 passed, add the learned-versus-classical comparison with zero-shot cross-simulator transfer. If M6 ran, the sim-to-real gap table becomes a section of this paper, not a third paper.

### Venues and route

1. **Preprint.** Post Paper 1 to arXiv (cs.RO) at the end of M4, and Paper 2 at the end of M5.
2. **Peer review.** Target workshops at major robotics conferences (themes such as benchmarking, simulation, reproducibility or field robotics), or an IEEE conference. Check the current calls for papers at the start of M4; deadlines decide the order, not this plan.
3. **Software paper (optional, after v1.0).** The Journal of Open Source Software. Check its current scope and requirements first.
4. **Advisor.** Ask a faculty member at Amrita to review and co-author. This adds credibility and submission experience at little cost to the work.

No paper text claims more than the measurement protocol supports.

## LinkedIn and media plan

One strong post per milestone exit beats a stream of progress updates. Reach can't be guaranteed, but robotics audiences reliably engage with three things: real robot behaviour on video, a specific failure story, and a measured number. Every post carries at least two of them.

**Posting rules:**

- GitHub link in the first comment.
- 3–5 niche hashtags.
- Post at your usual IST slot.
- Every number traces to committed evidence (integrity rule 12).
- Posts never drive scope: no feature is built because it would make good content.

Videos are hosted on YouTube and embedded or clipped for LinkedIn. The README gets a 10-second hero GIF at v1.0.

| After | Post angle | Asset |
| --- | --- | --- |
| M1 | "I ran \~140 autonomous missions and classified every failure by its first cause" | Failure Pareto chart, Foxglove screenshot of one divergence |
| M2 | The root-cause story of the biggest failure class: symptom, false leads, proof, fix | 20–30 s before/after clip, before/after rate with intervals |
| M3 | Safety-critical C++: the arbiter port, latency numbers, fault injection, safety case | Latency chart, requirement-to-test table snippet |
| M3 | "Reproduce my robot in one command" | Terminal recording of the Docker run |
| M4 | Launch: COCO v1.0 + preprint (the flagship post) | 60–90 s split-screen demo, PDF carousel: architecture → method → results |
| M5 | "Where does a classical robot stack break?", including the RL verdict either way | Perturbation chart |
| M6 | The same stack on the real robot (only if M6 ran) | Real-run video, gap table |
| M7 | Retrospective: what months of building one robot properly taught me | Project page link, both papers |

The M4 post is the one to invest in most. Have the video, preprint, README and project page live before posting, so every click lands on finished work.

## Timeline, decision gates and risks

At the estimated pace, v1.0 lands about 16 weeks after M0 starts. v2.0 follows around week 24 without sim-to-real, or week 32 with it. These are planning estimates for part-time work with coding agents; the gates, not the calendar, decide progress.

### Decision gates

Only Gautham passes a gate, and each decision is logged in `STATUS.md` with its evidence.

| Gate | When | Question | If no |
| --- | --- | --- | --- |
| G0 | End of M0 | Does the repo match the handoff's assumptions? | Update this plan first, then start M1 |
| G1 | End of M1 | Can Isaac and Gazebo batches run qualified on this laptop? | Smaller Isaac n, headless Isaac, or a documented second host profile (never pooled with laptop results) |
| G2 | End of M2 | At least 27/30 per backend on test set A? | One more M2 iteration (at most two in total), or accept and document |
| G4 | End of M4 | Is v1.0 fully shipped (release, videos, preprint)? | No research work starts until it is |
| G5 | Mid M5 | Measured control-layer gap, classical attempt failed, training fits the hardware? | Publish the robustness study and the "RL not justified" note |
| G6 | Before M6 | Matching hardware, working drivers, hardware e-stop, test area? | Skip M6; record it as future work |

### Risks

| Risk | Early signal | Response |
| --- | --- | --- |
| Laptop cannot run Isaac batches qualified | Many unqualified Isaac runs in M1 | G1 options above; never mix host profiles in one rate |
| Root causes resist proof | M2 hits its time box | G2; publish the open class with its evidence. Explained-but-open beats hidden |
| Wheel odometry lowers Isaac reliability | Dev control seeds fail after M3.1 | Run the M2 loop inside M3; the drop itself is a reportable fidelity finding |
| Agents drift into new features | A report lists work outside the checkpoint list | Drift test, review session, revert out-of-scope commits |
| Agents overclaim | A report claims files or tests that do not exist | Milestone stays open until the review session verifies |
| Bags fill the disk | Batch exceeds the disk budget | Retention policy from M1.3 |
| Tool upgrades break parity mid-project | Isaac Sim, ROS or Nav2 version change | Pin all versions in the manifest until v2.0 |
| Prior work overlaps Paper 1 | Found in the M4.5 literature review | Reframe around the benchmark and ablations |
| Job-hunt time pressure | Interviews compete with milestone time | v1.0 is the portfolio cut; everything after it is optional |
