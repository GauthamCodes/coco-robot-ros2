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
