# M1 execution sprint — evidence and precise stop

Input SHA: `551d532090b25438dda83d58fd9431f186a616e2`. Branch:
`coco-2.1-isaac-integration`; clean entry; Master Plans byte-identical.
Final live SHA/cleanliness: `python3 eval/status.py`. No simulator launched.

## Executed results

| Checkpoint | Evidence-backed state |
| --- | --- |
| M1.1 | Foreign/owned/domain/simulator classifier locally verified; both real preflights blocked; production resources uncalibrated |
| M1.2 | Live simulator-free production Nav2/perception/arbiter /eval isolation checked; whole mission/simulator graph not verified |
| M1.3 | Production MCAP recording and actual CDR replay with stamps/UUIDs verified; full mission topic completeness not verified |
| M1.4 | Existing diagnostic instrumentation preserved; no real image/candidate runtime this sprint |
| M1.5 | Nav2 action/services and active lifecycle verified; native UST synthetic spans verified; qualified mission timing absent |
| M1.6 | Historical and MCAP evaluator CLI executed; pre/post-episode scope defect fixed; incomplete catalogs remain UNCLASSIFIED; 19 controls precisely accounted for |
| M1.7 | Guarded smoke command executable; actual registered smoke command exits3, with one BLOCKED preflight and no child launched; qualified runner/teardown still unverified |
| M1.8 | Not started: determinism0/20, Dev0/60, Test A0/60 |

### Qualification

`preflight_isaac.json` and `preflight_gazebo.json`: foreign domain66 daemon
PID260322/start8029900 plus null RAM/VRAM requirements. No simulator conflicts,
DDS segments or inventory errors. Domain metadata is declarative, not proof of
all ROS contexts. Foreign ROS blocks under MASTER_PLAN regardless of domain.
Reparenting never proves orphanhood/cleanup ownership. No rule relaxed, no
foreign signal, and no daemon forensic investigation repeated.

### Resources

`resources.json`, `measurement_summary.json`: three30-second phases,90 samples
at1Hz, using /proc CPU tick deltas/memory/RSS and nvidia-smi. Idle → unchanged
production Nav2/perception/arbiter with synthetic scan/TF → same plus MCAP
recording and20Hz synthetic clock/truth/status. No actuator/mission/MoveIt/image
processing or simulator. ROS child RSS peak505262080 bytes; with MCAP602116096
bytes; median child RSS recording increment96796672 bytes. RSS double-counts
shared pages and excludes source probe. Host CPU peak84.738%, load1 peak5.8364,
available RAM minimum8086917120 bytes, free VRAM minimum5479858176 bytes.
Background activity confounds attribution; CPU/GPU changes are not causal
recorder overhead estimates. RTF/simulator overhead unmeasured. Earlier corrected
probe and failed context-start probe preserved with separate paths.

Exactly one missing combined resource measurement: **simulator + frozen full
mission + ROS + MCAP envelope, including simulator-clock RTF, on an exclusively
released host**. Partial RSS/idle VRAM and historical foundation lower bounds do
not qualify production resource limits. No threshold values changed.

### Evaluator execution and manual checks

Historical input `docs/data/isaac_fetch/coco23/gazebo_seed6`:12326 records →
existing historical oracle adapter + production normalizer/analyzer → ABORT/FAIL,
agreement. First supported I19 in DESCEND at61.726 sim seconds. Independent raw
XYZ calculation: previous packet61.712,2.351465mm displacement; next packet
61.726,5.170432mm against5mm frozen contract (`manual_historical_check.json`).
Final earliest-invariant classification UNCLASSIFIED because other catalog
witnesses are missing. Ten-second context preserved. Historical UUID/MCAP absent
and never fabricated. Full output external; selected committed historical
analysis excerpts ten of7815 supported violations and hashes the full analysis.

Synthetic production MCAP:3169 CDR records,107 source headers, UUID
`000102030405060708090a0b0c0d0e0f`; exact receive-nanosecond/payload sidecar
comparison. Reconstructed wall receipts from validated sidecars, not guessed
from bag time. ABORT/FAIL, agreement: target deliberately2m from home. Injected
failed MoveIt status yields supported I20 at34.564697456 sim seconds, LOCALIZE.
The first pre-mission latched status stays context after the scope correction.
Unknown command-authority coverage remains unknown, separate from the passing
production-authority test. Full catalog result UNCLASSIFIED, not an earliest
causal proof. Corrupt MCAP/sidecar payload disagreement fails closed.

Production replay does not qualify history or fixtures or authorize baseline.

### Real ROS graph and tracing

`ros_cli/`:15 real ros2 node/topic/action/service/lifecycle commands exit0.
Planner/controller/bt_navigator all `active [3]`; NavigateToPose server
/bt_navigator and ComputePathToPose server/planner_server discovered. Relay alone
publishes /cmd_vel_gated; root arbiter alone publishes final wheel command.
All /eval truth subscribers are /eval. Recorder dependencies present for this
fixture; missing full mission/controller/manipulation topics remain explicit
trace-health gaps in raw MCAP. No actuator subscribes to final commands.

Graph is not proof of command lineage: separate actual production arbiter test
proves correlated wheel/diagnostic records, preemption, stop and logging-failure
output preservation (`authority_evidence.json`). Native UST:22 matched callback
spans, zero unmatched starts, owned synthetic C++ PIDs only. No qualified mission
executor timing claim. Probe production/CLI processes all exit0; owned CLI daemon
is registered by inherited group; teardown survivors empty. Domain66 untouched.

### Validation

Evaluator suite180 pass (`eval_tests_final.log`); command authority/native trace
2 pass (`ros_authority_tracing.log`); production MCAP decoder/negative corruption
check1 pass (`ros_mcap_replay_tests.log`). No robot rebuild or repeated full robot
suite. Campaign files/seed policy unchanged: smoke4, determinism20, Dev60, Test A60.

## Remaining gates — no rediscovery required

1. External owner releases its own domain66 ROS workload. No M1 process may stop it.
2. Full combined resource measurement above is missing; production preflight
   deliberately refuses null limits. The current repository has no executable
   qualified full-stack resource-calibration bootstrap. Foreign release alone
   does not resolve this circular prerequisite.
3. `calibration_dependency_audit.json`: all19 threshold keys classified
   REQUIRES QUALIFIED RUNTIME, exact episode/witness named, zero unexplained
   unknown entries. Unchanged calibration.py requires qualified oracle-PASS Dev
   full-run controls plus justified margins. Frozen ArmControl.target_height()
   returns None; GraspServer inherits grasp_magnet(), which rejects before
   attachment. A successful fetch control is unavailable under this behavior.
   Synthetic/historical/unqualified controls cannot legitimately substitute.
4. Nine incomplete raw witnesses are named in that audit: I07 motion association,
   I12 independent occupancy, I13 request/return timing, I14 clearance, I16 true
   projection, I18 physical identity, I21 proximity, I23 finger-before-detach,
   I25 progress. They require source/association implementation and then the
   specified runtime controls. They are not represented as measurement-only gaps.

No behavior repair, privileged autonomy input, threshold relaxation or policy
change is authorized to remove these gates. A future owner-approved calibration
bootstrap/control-policy decision and the named passive witness work are needed
before a zero-implementation handoff is honest. M1.8/M2 remain closed.

## Exact commands

Use a new output path for each preflight and independent proof; campaign roots
resume append-only. Clean shell qualification (documented project mechanism):

```bash
env -i HOME=/home/gautham USER=gautham \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  bash --noprofile --norc -c '
cd /home/gautham/coco-isaac-21
export COCO_WS=/home/gautham/coco_m1_ws
export COCO_MOVEIT_PREFIX="/home/gautham/ros2_ws(personal)/moveit_prefix/root/opt/ros/jazzy"
export ROS_DOMAIN_ID=82
source setup_env.sh
./eval/bin/eval preflight --backend isaac --output /tmp/NEW-m1-preflight.json
'
```

After ALL gates actually pass, exact registered sequential smoke command:

```bash
./eval/bin/eval campaign eval/campaigns/m1_smoke.yaml \
  --output /home/gautham/coco_m1_runs/sprint-20261007/smoke
./eval/bin/eval validate-smoke /home/gautham/coco_m1_runs/sprint-20261007/smoke \
  --output eval/runtime_validation.json
```

The first command is executable now and must refuse launch while blocked.
It is not a claim that release alone can resume qualified runtime. Then, only
with trustworthy complete smoke proof/oracle agreement/calibration, execute the
three existing M1.8 campaign commands in eval/README.md.

Independent reruns: `eval replay` and `non_sim_probe.py` commands in eval/README.md.
Raw evidence root: `/home/gautham/coco_m1_runs/sprint-20261007`. Full retained
MCAP/CTF, normalized inputs, analysis/context, manifests, unsuccessful probes
and logs indexed by SHA256 in `external_evidence_index.json`.

Behavior changes: **NONE**. Test A/reserve inspection: **NONE**. Real smoke:
Gazebo not launched; Isaac not launched. Qualified simulated episodes0.
Stop condition: **YES**, foreign host gate plus the independent calibration/
passive witness prerequisites above.

Final status: **M1 BLOCKED — ADDITIONAL ENGINEERING REQUIRED**.
M1 is not complete and the requested runtime-ready prepared outcome was not
achieved. Real evaluator/graph/resource results above are preserved; no generic
external-only handoff or fabricated qualified success.

## Final actual runner/validation commands

Checkpoint input `d63b7df7e06e743bc4e3a1a799639d35c338ecae`. Registered smoke
command ran, exited3, preserved one BLOCKED Gazebo5 attempt before any child
launch. Owned process list empty, bag empty;0 qualified/0 unqualified simulated
runs. It stopped before Isaac, which remains independently preflight-blocked.
`validate-smoke` ran and exited3: analyzer calibration incomplete, host resource
profile not validated, both backends/four registered jobs absent. No stale-smoke
source rejection. Compact proofs `runner_gate.json`, `blocked_smoke_*.json` link
full external artifacts. No sentinel removed or attempt overwritten. The exact
smoke command above is resumable after prerequisites are legitimately met.

Post-measurement environment inventory is retained externally at
`non-sim-probe-final/env.json`: equivalent clean source shell with domain184,
captured after the measured workload, not falsely labeled a pre-run inventory.
