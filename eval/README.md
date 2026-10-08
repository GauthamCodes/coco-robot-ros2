# Evaluation control plane

These modules are offline evaluator utilities, outside autonomy. They are not
ROS nodes and have no publisher, client or control interface. No robot package
imports them. M1 supplies run orchestration and trace capture.

Record the environment **before every run**, in the exact sourced environment
used by that run (including runner DDS overrides):

```bash
python3 eval/environment.py --run-dir /path/to/new-run
```

`env.json` includes OS, ROS/Nav2 package versions and dpkg inventory, Gazebo,
Isaac metadata and both Python locks, GPU/driver/VRAM, RMW and DDS values/content
and hashes. It refuses to overwrite prior evidence. Missing tools/installations
are explicit unavailable records, not assumed versions. Use `--isaac-python` for
another install. It reads package metadata without importing simulator modules.
The normal ROS environment and Isaac's process-local bridge environment differ;
record the launched bridge's DDS/RMW overrides in the run manifest (see
`scripts/isaac_sim_coco.sh`, Humble bridge against the Jazzy robot stack).
A package inventory is a version lock, not a Docker image or proof that apt/pip
artifacts remain available; deployment packaging belongs to M3.

Run offline unit tests from a fresh checkout: `python3 -m pytest -q eval/tests`.

`python3 eval/status.py` prints the exact live HEAD, branch and clean state,
then the committed STATUS. Static checkpoint provenance names input commits;
a commit cannot embed its own SHA without changing that SHA.

`python3 eval/seed_policy.py` validates disjoint pools without generating layouts.
`python3 eval/hygiene_inventory.py NEW_JSON` reproduces tracked-source searches
and syntax checks without executing optional runtime entry points.

## M1 runner (implementation; qualified runtime not yet validated)

The new evaluator ROS nodes run under `/eval`; normal robot nodes never import
this directory or consume truth. `topics.py` is the fixed capture contract.
`qualification.py` reads host state without starting a simulator. Null production
limits in `host_policy.json` deliberately reject launch pending justified
full-stack calibration. A clean process list alone does not qualify this host.
No foreign process is automatically killed. Explicit background-app exceptions
match UID, comm and argv; runner children require PID/start-time identity and
observed parentage. Unowned DDS segments and unknown process metadata block runs.
CPU/RAM/VRAM/clock-derived RTF are sampled at 1 Hz during an episode; a resource
violation interrupts and preserves the unqualified attempt.

Source the isolated ROS overlay before ROS capture. Add the CLI to PATH (Bash
also has an `eval` builtin, so invoke the executable explicitly):

```bash
export COCO_WS=/home/gautham/coco_m1_ws
export COCO_MOVEIT_PREFIX='/home/gautham/ros2_ws(personal)/moveit_prefix/root/opt/ros/jazzy'
source setup_env.sh
export PATH="$PWD/eval/bin:$PATH"
./eval/bin/eval preflight --backend isaac --output /tmp/coco-new-preflight.json
./eval/bin/eval run --backend gazebo --seeds list --seed-list 5,8 --repeats 1 \
  --campaign eval/campaigns/m1_smoke.yaml --output /home/gautham/coco_m1_runs/smoke-gazebo
```

The four-run smoke and subsequent exact baseline commands are:

```bash
./eval/bin/eval campaign eval/campaigns/m1_smoke.yaml --output /home/gautham/coco_m1_runs/smoke
./eval/bin/eval validate-smoke /home/gautham/coco_m1_runs/smoke --output eval/runtime_validation.json
./eval/bin/eval campaign eval/campaigns/m1_determinism.yaml --output /home/gautham/coco_m1_runs/determinism
./eval/bin/eval campaign eval/campaigns/m1_breadth.yaml --output /home/gautham/coco_m1_runs/breadth
./eval/bin/eval campaign eval/campaigns/m1_test_a.yaml --output /home/gautham/coco_m1_runs/test-a
```

These currently **refuse runtime/baseline launch**, as appropriate: production
resource calibration and raw invariant coverage are incomplete. A failed
`validate-smoke` artifact is not authorization; the runner requires validated
true with matching policy/threshold/topic hashes. Do not run large campaigns
until the full M1 validation gaps in `docs/m1/BASELINE.md` are closed.

Equivalent single-backend breadth/held-out commands use `eval run --backend
{gazebo|isaac} --seeds {dev|testA} --repeats 1 --output EXTERNAL_NEW_ROOT`.
Dev here selects the preregistered breadth subset; historical lists require the
matching committed campaign and exact repeat count. Pools stay governed by
`seeds.yaml`. No reserve seeds are runnable in M1. Test A is preregistered to the
first 30 untouched seeds; inspect aggregates only, never individual traces for
debugging. A change of seed governance requires the Master Plan process.

Resume by repeating the exact command, same runtime content, campaign, policy and
output root. A filesystem lock enforces sequential ownership. Completed qualified
jobs are skipped; blocked/interrupted attempts are appended, never overwritten.
Saved live processes or process groups require explicit ownership reconciliation
before another launch. The runner does not kill saved PIDs after a crash.

Each attempt has `manifest.json`, `env.json`, `host_metrics.csv`, `logs/`, `bag/`,
`oracle.json`, `analysis.json`. Preflight-blocked attempts have an empty bag and
explicit BLOCKED state; they are not simulated runs. Manifest records source,
seed governance, qualification reasons, owned identities, timing and streaming
SHA256 per bag file/aggregate. `logs/events.jsonl` preserves source ROS fields and
receive simulation/wall timestamps; analysis orders simulation time with receive
order as tie-breaker and includes stage and centered ten-second context.
Corrupt/truncated input is evidence loss, never a clean trace. Full bags/CTF/raw
runtime logs stay outside git; commit compact batch summaries and selected
analysis/env/manifests with provenance. `summary.json` contains Dev attempts and only aggregate held-out outcomes,
qualified/unqualified/blocked counts, Dev Pareto/determinism and separate Test A
aggregates. UNCLASSIFIED is visible analyzer work, not forced attribution.

`storage_policy.json`: 1 GiB/run, 8 GiB/batch, 2 GiB free-disk reserve. Preflight
reserves capacity for one run; runtime checks total evidence size each second.
Retain every failure, interrupted/unqualified/unknown attempt and the first two
qualified fully passing controls per batch. Only extra completely passing bags
may be removed, with hashes/retention decision retained. Capacity exhaustion
stops the batch rather than deleting failed evidence. No camera-image streams;
costmap writes throttled to 1 wall Hz, producer behavior unchanged.

The single scorer remains `oracle.py`. `normalize.py` refuses safety PASS when
correlated arbiter authority is absent. `invariants.py` contains I01–I25 from the
committed plan. Every invariant has passing/failing/missing synthetic tests.
`calibration.py` accepts qualified oracle-PASS Dev controls only, derives P99
ceilings/P1 floors with explicitly justified margins and trace hashes; null
limits remain unknown. Do not invent limits or tune on held-out results.
`historical_replay.py` only labels breaches historical evidence actually supports.
First supported breaches cannot establish causal precedence across missing data.

Local tests: `python3 -m pytest -q eval/tests`; sourced ROS integration:
`python3 -m pytest -q eval/ros_tests`. Neither launches a simulator. CI includes
both, but local passing results do not claim remote CI execution.


## Current guarded continuation (2026-10-07)

Use only this explicit overlay, starting in a clean shell:

```bash
cd /home/gautham/coco-isaac-21
export COCO_WS=/home/gautham/coco_m1_ws
export COCO_MOVEIT_PREFIX='/home/gautham/ros2_ws(personal)/moveit_prefix/root/opt/ros/jazzy'
source setup_env.sh
./eval/bin/eval preflight --backend isaac --output /tmp/coco-m1-resume-preflight-isaac.json
```

Preflight is read-only and currently fails. Do not launch simulation until
resource/control prerequisites and remaining catalog gaps in BASELINE.md are
resolved with legitimate evidence. Then execute the smoke commands above. Inspect
actual evidence, run validate-smoke, commit proof/status, and only then execute
the registered three baseline campaigns. Commands are resumable, not proof of a
validated handoff. Output arguments are exclusive; preserve existing evidence.

Resume compares all tracked runtime/data content plus campaign/policy/job hashes.
Docs and runtime_validation.json proof changes may change HEAD without changing
runtime identity; original batch.json stays immutable and resume_sources.json
records the new source. A runtime change requires new registration and renewed
smoke evidence. STOP.json prevents continuation after integrity/disk stop;
resolve the recorded cause rather than removing the sentinel to continue.

Clock contract: bag receive stamps use ROS simulation time; message source/header
stamps are retained; host sampling uses wall epoch and monotonic time. RTF divides
successive simulator-clock values by their source receipt monotonic deltas, not
poll scheduling. Missing clock data stays unknown. Ten-second invariant context
uses simulation time; wall clock stall lengths remain explicitly wall durations.
Arbiter diagnostics are observational, emitted after wheel publication, and
matched to actual stamped commands before authority can be attested. A sampled
ROS graph cannot alone prove command lineage. Native UST span attribution is
restricted to owned PIDs. Synthetic evidence cannot calibrate production limits.

Held-out public output is aggregate-only. Manual held-out/reserve analysis is
blocked; any exceptional inspection must follow Master Plan seed replacement.
Automatic offline scoring remains part of the locked batch and never tunes
behavior. UNCLASSIFIED repeats cannot establish failure-class determinism.

## Executed replay and simulator-free resource probe

These commands do not launch a simulator and never qualify an episode. Source
the explicit clean M1 overlay above. Output directories must be new; prior
evidence is preserved. Manual replay refuses Test A/reserve seeds.

```bash
./eval/bin/eval replay docs/data/isaac_fetch/coco23/gazebo_seed6 \
  --source-format historical --output /home/gautham/coco_m1_runs/NEW/historical-gazebo6
python3 eval/non_sim_probe.py --seconds 30 \
  --output /home/gautham/coco_m1_runs/NEW/non-sim
./eval/bin/eval replay /home/gautham/coco_m1_runs/NEW/non-sim/fixture \
  --source-format mcap --output /home/gautham/coco_m1_runs/NEW/mcap-replay
```

The probe measures 30 seconds each of idle, production Nav2/perception/arbiter
with synthetic scan/TF, and the same workload plus production fixed-topic MCAP
recording. It runs in private domain184, with no actuator or mission executive.
It queries the real ROS graph, actions, services and lifecycle; CLI processes
and any CLI-created daemon are registered in owned process groups and stopped.
RSS is a sum of child processes and counts shared pages; it excludes the probe
source process. Host CPU/load/RAM/VRAM include background activity. No camera
images, MoveIt or simulator overhead is represented. The single missing resource
measurement is the combined simulator/unchanged mission/ROS/MCAP envelope and
simulator-clock RTF. These partial values do not establish production thresholds.

MCAP replay decodes CDR and checks every payload and ROS receipt timestamp
against its recorder wall-time sidecar. Source headers and UUIDs stay intact.
Historical replay uses the existing historical oracle adapter; historical UUIDs
and MCAP do not exist and are not invented. Both run the unchanged oracle and
normalizer/analyzer, retain ten-second supported-divergence context and keep
incomplete catalog classification UNCLASSIFIED. `replay.json` hashes the results.

The sprint evidence is in `docs/m1/validation/sprint_20261007/`. Foreign workload
release alone is insufficient: production RAM/VRAM still need the full workload
measurement; current calibration requires oracle-PASS Dev controls, unavailable
under the frozen fail-closed grasp; nine catalog witnesses remain incomplete.
Do not treat these replay commands or partial resource measurements as smoke
validation, baseline authorization, or a zero-engineering runtime handoff.

## NON_QUALIFYING engineering bootstrap (2026-10-08)

`eval bootstrap` is a separate bounded engineering command. It never calls
`run_batch`, registers no campaign and writes no production validation artifact.
Every manifest and preflight verdict has `qualified=false`,
`execution_class=NON_QUALIFYING`, `m1_denominator_eligible=false`,
`satisfies_m1_8=false`. It uses Dev5 only; no Test A/reserve/seed override exists.
A successful bootstrap is never a qualified control, smoke job or M1.8 result.
The unchanged calibration module rejects it even if the oracle reports PASS.

Start from the explicit sourced overlay above and a committed clean worktree:

```bash
./eval/bin/eval bootstrap --backend gazebo --seconds 120 --domain 82 \
  --output /home/gautham/coco_m1_runs/NEW/bootstrap-gazebo
./eval/bin/eval bootstrap --backend isaac --seconds 120 --domain 82 \
  --output /home/gautham/coco_m1_runs/NEW/bootstrap-isaac
```

Use `--preflight-only` for a read-only safety check. Output directories are
exclusive: retry with a new path, preserving blocked/failed evidence. Never run
backends concurrently. The command refuses any foreign robotics process,
unknown process metadata, opposite backend or unowned DDS segment using the
unchanged production process checks. It requires Jazzy, explicit loopback
CycloneDDS/Gazebo and a sourced overlay. No foreign PID is signalled.

Emergency reserves are derived from inventory: half physical RAM (or 16 times
kernel min_free_kbytes if larger), one third physical VRAM, and load no higher
than logical CPU count or the committed load ceiling. These conservative budgets
reserve capacity for the OS/background applications; they are not measured
simulator requirements. Stricter committed limits still win. Production resource
requirements remain untouched/null. The original 1GiB run/8GiB root budgets and
2GiB disk reserve apply. CPU, load, RAM, VRAM, disk and clock-derived RTF are
sampled at1Hz, including recorder startup. A resource violation stops owned
workload and records `ABORTED_BOOTSTRAP_RESOURCE_LIMIT`. Allocation spikes
between samples cannot be prevented by a userspace watchdog; no kernel quota or
proof of hardware suitability is claimed. Wall duration is bounded to600s.

Existing MCAP recorder and unchanged episode/teardown scripts are reused.
`bootstrap_recorder.py` extends capture only inside its own process with real
RGB/depth/CameraInfo at1Hz; production `topics.py` stays unchanged. Existing TF,
candidates, mission and evaluator evidence remain captured. Owned roots use new
process sessions; observed descendants require exact parentage and PID/start
identity. Recorder stops last; survivors/errors remain in teardown evidence.
Oracle scoring is evaluator-only after teardown and disagreement stops further
work. A run ending/budget expiration does not prove visibility, complete mission,
valid height or a full-stack resource envelope. Those require inspecting actual
sensor frames and physical outcome. No observer/consumer is enabled by bootstrap.

**IMPLEMENTED; local policy/abort tests pass. Simulator lifecycle NOT VERIFIED.**
Current foreign Gazebo/unknown-metadata blockers must clear before execution.

### Non-finite ROS fields in trace evidence

Real Gazebo JointState messages can report unavailable effort as NaN. The MCAP
writer preserves the original CDR unchanged. JSON sidecars represent unavailable
floating values as `{"$ros_nonfinite_float":"NaN"}`, `+Infinity` or `-Infinity`
inside the same tagged object. These are not finite measurements or substitutes.
Replay uses identical encoding for decoded CDR and retains strict payload equality;
changing a tagged unknown to zero fails integrity validation. The fix prevents a
raw NaN from crashing strict JSON recording. It does not repair previously
incomplete bags/sidecars, qualify a run, or change autonomy or oracle semantics.

### Lightweight RGB-D engineering fixtures

`eval bootstrap --backend gazebo --profile rgbd_capture --fixture acquisition`
launches only the existing camera, Gazebo, four-topic bridge, static robot TF and
recorder. `--profile rgbd_observation` additionally launches the physical observer.
Bound with `--seconds 30 --domain 82 --output <new-external-directory>`.
Fixtures `acquisition`, `grasp_original` and `grasp_flank` are static optical
experiments, not benchmark or physical manipulation controls. Candidate camera
extrinsics apply only to generated fixture assets. Isaac lightweight profile is
not implemented; unsupported backend/profile combinations refuse execution.

Every run remains NON_QUALIFYING with M1 denominator eligibility false and the
same bootstrap emergency resource/ownership/DDS/disk protections. A sensor window
ending at its wall budget is not an episode success. See
`docs/m2/target_observation_20261008/REPORT.md` for real-data results, explicit
remaining gates and recorded-frame ROS observer replay commands. Engineering
resources cannot establish full-stack production limits.
