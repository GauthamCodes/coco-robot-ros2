# Offline manipulation verification contract

Hypothesis before implementation: plugin attachment messages and mission state
cannot establish object-to-palm rigidity; the engineering composition also lacks
an evaluator truth publisher. Discriminator: retain identical command/plugin
traces while changing only independently recorded object motion. Physical results
must change, command/report results must not.

The diagnostic extends the existing normalizer, oracle and I20–I23 engine.
It never changes the oracle verdict. PASS is a supported phase assertion, FAIL
an observed violation, UNVERIFIED missing witnesses/calibration, UNSCORABLE
corrupt or ambiguous clocks. Synthetic fixtures are evaluator tests only.

Truth packets retain world target pose and optionally same-source world gripper
pose (m_link3), with provenance and source simulation time. Plugin `attached`
remains a report, never an independent constraint witness. Relative translation
and quaternion motion are measured offline. No dynamic TF extrapolation or clock
substitution is permitted. Missing world gripper poses remain missing.

The catalog fixes lift at 30mm and placement rest at 5mm/2s. Attachment proximity
is still null. There is no approved relative-transform tolerance in the repository;
relative translation/rotation tolerance and maximum truth sample gap therefore
remain null by default. Tests may supply explicitly SYNTHETIC_ONLY limits; those
are not production calibration. No PASS for physical attachment or retention is
possible without these evidence-quality limits and a moving gripper witness.
Independent motion diagnostics do not replace the existing I21/I22/I23 definitions.

Every phase includes source/receive clocks, original sequence references,
measurements with units, required/missing evidence, invariant results and reasons.
A full manipulation diagnostic PASS requires all phases and the existing oracle
PASS. The oracle's original behavior and mission disagreement remain visible.

## Implemented refinements (2026-10-10)

`evaluation.evaluate_recording` is the shared post-run sequence used by replay
and engineering bootstrap: existing normalization/oracle, existing invariant
analyzer, diagnostic verifier. Structural parsing errors produce UNSCORABLE
rather than disappearing. `eval analyze` also adds the diagnostic report.
Production campaigns, Test A behavior and the success oracle are unchanged.

Source and receive clocks have separate extrema. MCAP nanosecond receipt stamps,
original sidecar receive sequence, decoded order and source headers are retained.
Clock epochs are not silently merged. TF reconstruction is exact-time only and
includes its chain/provenance in evidence references. Unknown rigidity/sample-gap
limits remain null; `--limits FILE` accepts explicit diagnostic calibration with
provenance. Synthetic-only limits in tests never become production thresholds.
Proximity is measured as world target-center to palm-origin distance at the
pre-attachment sample; its existing catalog limit remains uncalibrated.

`phase_sequence_result` describes the ten phase assertions. Overall `result`
additionally requires the existing I21–I23 conjunctions and oracle PASS. A
phase's local partial invariant results may be unknown; final `catalog_results`
combines the evidenced multi-phase fields. Missing opening-before-detach witness
remains unknown; no command is promoted to measured fingers. I20 evidence remains
in the existing analyzer output. No alternate mission success definition exists.

The driver checkpoint includes the entire sensor observation and phase epoch;
the evaluator reruns the shared observation contract and identity continuity.
`/diagnostics/manipulation_observation_acceptance` passively records the exact
sample accepted by ArmControl.target_height. Publication failure cannot alter
acceptance, and repeat calls on the same sample/phase do not flood the recorder.
This diagnostic has no new subscription or truth input. Old traces cannot gain
this witness retroactively.

The engineering driver publishes observation/request/plugin/consumer checkpoints,
with each report's assertion layer explicit. Physical checks occur offline only.
Checkpoint QoS retains up to100 records for late recorder discovery; the record
keeps source ROS and monotonic emission clocks. After successful guarded placement,
the driver only observes for2 simulation seconds (bounded20 wall seconds); it
issues no extra motion. Missing clock progress leaves rest evidence insufficient.
The existing owned-launch teardown remains responsible for every child.

A NON_QUALIFYING rgbd_manipulation run can pass actual recorded start/finish
boundaries to the existing oracle adapter. Source monotonic times are converted
to the recorder-relative wall domain using its recorded monotonic origin; both
source and receive times remain intact. Mission verdict remains UNOBSERVED.
Other profiles/production use the original mission boundaries. No COMPLETE event
is synthesized. The physical checks, authority requirement, placement radius,
rest test, time budget and oracle verdict logic are unchanged.

Limitations: complete finger-opening derivation/calibration is still absent;
exact-time TF availability needs real capture validation; joint-TF reconstruction
is kinematic gripper evidence, not a separately calibrated simulator link pose.
The generated engineering truth adapter is wired and fixture generation/tests
pass, but its new live stream remains runtime-pending under the resource gate.
