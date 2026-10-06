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

Resume by repeating the exact command, same source commit, campaign, policy and
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
analysis/env/manifests with provenance. `summary.json` contains every attempt,
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
