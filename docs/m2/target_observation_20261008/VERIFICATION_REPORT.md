# Manipulation verification session — 2026-10-10

Session start: `2f751ca0efb26e0285e19e1c6dda81d3caf39893`, branch
`coco-2.1-isaac-integration`, initially clean. Implementation checkpoints:
`f664282`, `9b5e1a9`; final closure commit contains this report.
Master Plans remain byte-identical and unchanged.

## Delivered

Executable offline ten-phase manipulation diagnostic, integrated after the existing
oracle and invariant analyzer. Command, plugin report, physical response and oracle
are separate assertions. Exact-time evaluator-only TF, observation acceptance
witnesses, explicit clock provenance, incomplete-evidence reports and deterministic
regressions are implemented. No ground truth enters autonomy. Existing oracle,
invariant thresholds, safety limits, campaigns and Test A remain unchanged.

Resource attribution reports host RAM/PSI, owned-process PSS/private/RSS/CPU and
lifetime bounds, GPU and receipt-clock RTF where available. Historical RSS cannot
recover shared-page attribution. The live recorder now actually invokes its existing
image-summary helper, preserving raw CDR and verifying image hashes on replay.
The NON_QUALIFYING runner captures phase checkpoints and evaluator truth, with
existing gates and owned teardown. Early capture aborts now emit UNSCORABLE reports.
See [contract](MANIPULATION_VERIFIER.md), [resource comparison](RESOURCE_ATTRIBUTION.md)
and [exact reproduction commands](VERIFICATION_RUNBOOK.md).

## Validation

- Focused suite: 240 passed; ROS capture/runner suite: 9 passed.
- Manipulation ROS package: 43 pytest cases; colcon reports 44 including wrapper.
- Three affected/dependency packages built; manipulation rebuilt after instrumentation.
- Final early-abort regression subset: 56 passed (overlaps the focused suite).
- Real guarded-motion-06 MCAP replay: 1730 records, 544 headers and 7 goal UUIDs,
  CDR/sidecar integrity checked. Plugin attachment PASS; physical phases UNVERIFIED;
  existing oracle UNSCORABLE because original engineering manifest lacks targets.
- Historical gazebo_seed6: 12326 records; mission ABORT, oracle FAIL; supported I19
  retained. Neither replay is a new qualified episode. Synthetic PASS fixtures prove
  evaluator behavior only. Remote CI was not run.

Logs, machine-readable reports and SHA256 external-evidence index are in
`validation/verification_20261009/`. Failed intermediate attempts are retained.

## Single controlled startup attempt

The initial read-only gate blocked at available RAM 8,104,574,976 bytes, below the
unchanged reserve 8,229,275,648. After host conditions changed, final read-only
Gazebo preflight passed; separate host snapshot showed 9,833,877,504 available bytes.
One controlled attempt at commit 9b5e1a9 was then made:
`/home/gautham/coco_m1_runs/manipulation-verification-20261009/controlled-gazebo-20261010-01`.

It exited 3, ABORTED_BOOTSTRAP_SAFETY: runtime inventory could not read
`/proc/96143/exe`. Only the recorder child started; it was interrupted during import.
Gazebo and fixture did not launch, no MCAP/events were captured, no robot motion
occurred. Teardown reports zero survivors and zero errors. No foreign processes
were signalled. Failed replay exits 1 with INCOMPLETE_EVIDENCE and original oracle /
verifier UNSCORABLE; this is an expected failure-path check, not successful replay.

First runtime sample: RAM available 9,364,979,712 bytes; CPU 20.67%; load 0.991;
GPU used 400,556,032 bytes, free 6,038,749,184; no simulation clock/RTF. Remaining
RAM margin was approximately 1.135 GB, less than the prior incomplete arm run's
observed 1.304 GB host-available decrease. Metadata PID subsequently disappeared;
its identity is unknown. No retry was made. Production Isaac preflight still rejects
uncalibrated RAM/VRAM requirements; Isaac was not launched.

## Outcome and continuation

No new grasp, attachment, lift, retention, release, placement or oracle PASS is
claimed. Historical guarded grasp motion/plugin confirmation remain the strongest
runtime evidence. Root cause OPEN: physical evidence and system-level closure absent.
Technical gaps include calibrated relative-motion/sample-gap/proximity limits,
finger-opening witness and live exact-TF coverage. Do not use synthetic limits to
obtain runtime PASS. Host ownership metadata and sustained workload headroom must
be resolved before one new gated attempt using the runbook. No safety change or
unrelated process termination is authorized or needed for this handoff.

M1 calibration 0/19, qualified smoke 0/4, M1.8 0/140 remain unchanged. Next action:
resolve the bounded host/evidence prerequisites, record and verify the guarded
physical sequence, then return to the original Master Plan qualification sequence.
