# RGB-D prerequisite execution — qualification gate reached

**The requested observation repair is NOT IMPLEMENTED and the minimum success
criteria were not reached.** Both entry backend preflights refuse launch for
uncalibrated RAM/VRAM requirements. Final preflights additionally find a foreign
Gazebo process and unreadable process metadata. No simulator ran in this session.
The approved patch requires
rendered visibility evidence before implementing the consumer and independent
sensor validation before enabling valid height observations. Proceeding through
this gate would require changing the qualification policy, which this session
has not done.

Start SHA: `e8bb85ffec8a5ed1e5a0aad89748a04ecf9aa0de`.
Branch: `coco-2.1-isaac-integration`.
Worktree: `/home/gautham/coco-isaac-21`, clean at entry.
End SHA/cleanliness: recorded in the session's final response; live verification
is `git rev-parse HEAD` and `git status --short`.
Both Master Plan copies are byte-identical, SHA256
`e2d899d3b4f1b96a3958ace3833e32318985cc4edbcd05e12858ec91698aa03d`.
Neither was edited. The user's bounded M2 prerequisite authorization is recorded
in STATUS; historical scope-stop statements do not override that authorization.

## Root cause

Confirmed existing capability gap: `target_height()` still returns None; fresh
synthetic execution accepts the target/fix/IK and rejects at `pick:magnet attach`.
There is no attach or raise command in its stubbed-actuator call log. It reproduces
the 45.814262 mm framing-dependent centroid difference. This is a new execution
of the existing synthetic diagnostic, **not replay of real RGB-D or qualified
runtime**. Its fixture writer was redirected to the new external evidence root
so the old blocker package remained untouched.

Rejected alternatives remain missing-scalar wiring, fixed Z, actuator state and
simulator truth. No production fallback, oracle change or relaxed safety gate was
introduced. This issue is not recorded as fixed.

## Sensor geometry

Both configured cameras: base_footprint `(0.125, 0, 0.0685)` m; forward camera-link
orientation; REP-103 optical frame; 320×240; horizontal/vertical FOV
1.25/0.9919896804 rad. Gazebo RGB near=0.05 m, depth near=0.1 m;
Isaac camera near=0.1 m; existing acquisition min depth=0.15 m.
See `DESIGN.md` and source-hashed `validation/geometry.json` for the complete
configuration, TF, encoding and timestamp audit.

Maximum nominal grasp forward depth remains 41.5–47.5 mm. New enclosing-box
distance bounds are 100.66–104.61 mm: no rotation alone at this origin can produce
150 mm optical depth. A translation is necessary. Near-plane resolution remains
unproven, and no mount was changed.

The executable CAD screen expands the actual robot xacro and tests its visual
triangles with unchanged joint poses, including ideal failed-grasp/retained-object
fixtures and Isaac's different chassis visual. The coarse grid checks 648
placements: 285 fit the frustum, but all have a blocked sampled ray. The 288-point
refined flank grid has zero frustum candidates under this screen's combined
constraints. These are conservative, discrete diagnostic searches, **not a proof
that every compliant mount is impossible**. They do not establish full end
observability, physical sensor-body clearance, support fit or rendered visibility.

Current-code correction: `coco_sim/coco_sim/isaac/runtime.py` also owns static
camera TF publication and must remain consistent with any future camera prim /
robot-description extrinsic change. The lift estimator must handle palm-induced
target rotation; an upright-only model for every phase would be incorrect.

## Observation, ROS 2 and manipulation

Algorithm/publisher/consumer: not implemented; the visibility gate was not passed.
Proposed sensor inputs, measured centre/support quantities, frames, source stamps,
validity and failure semantics are recorded in `OBSERVATION_CONTRACT.md` with
explicit unimplemented status. No QoS instance or live observer graph exists.

Old/new production behaviour is identical: missing independent height rejects
attachment, lift and release checks. No grasp, attachment, lift or release has
been physically executed in this session. No `/eval`, world-pose query, sensor,
task geometry, IK, search, physics or attachment behaviour was changed.

## Local tests and evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Existing focused grasp safety regressions | 8 passed, 10 deselected | `validation/fail-closed.log` |
| Existing null-resource qualification rejection | 1 passed, 16 deselected | `validation/qualification-test.log` |
| New CAD segment/frustum instrument checks | 4 passed | `validation/geometry-tests-optimized.log` |
| Existing synthetic end-to-end gate diagnostic | Valid acquisition/fix/IK, height=None, rejection before attachment | external `reproduction.json` |
| New observer positive/negative tests | Not run: no observer implemented | `regression_results.json` |
| Real sensor replay / live ROS graph | Not run | no qualified sensor trace available |

These are 13 distinct local tests, not CI verification or simulator evidence.
No build was needed because production sources and installed packages are
unchanged. The MCAP storage package is installed and `mcap` is a registered
writer; recording a complete robot-control episode is not verified here.

## Gazebo and Isaac qualification

Clean shell: explicit coco_m1_ws overlay, ROS Jazzy, domain 82,
rmw_cyclonedds_cpp on loopback, GZ Harmonic on loopback. Diagnostic node tests
used domain 187. Environment and exact package paths are recorded in
`validation/clean-environment.json`.

Both entry `./eval/bin/eval preflight` invocations exit 3. Their only reasons:

- `<backend>/preflight: uncalibrated requirement min_ram_available_bytes`
- `<backend>/preflight: uncalibrated requirement min_vram_free_bytes`

No foreign robotics process, DDS segment or inventory-error rejection appears.
Load1=2.50732421875 on 12 CPUs. Available RAM was 9,364,389,888 bytes (Gazebo
snapshot) / 9,355,980,800 bytes (Isaac); free VRAM=5,662,310,400 bytes of
6,439,305,216. These are idle inventory values, **not workload measurements**.

The final preflights, after the offline probes and node tests, also exit 3 and
find new external blockers: foreign Gazebo PID111827/start2051123, declared
domain115, cwd `/home/gautham/ros2_ws`, executable `/usr/bin/ruby3.2`, argv
`gz sim server`. Isaac additionally rejects SIMULATOR_BACKEND_CONFLICT.
PID60465 executable metadata is unreadable; read-only ps identifies a UID1000
`ssh-agent -D -a /run/user/1000/keyring/.ssh`, which is not an allowed unreadable
process in the current policy. No ownership/staleness assumption, signal or
allowlist change was made. See `validation/preflight-final-*.json`.

| Backend | Qualified | Observation/grasp/attachment/lift/release | Oracle | RTF |
| --- | --- | --- | --- | --- |
| Gazebo | No; preflight blocked | Not executed | No verdict | Not measured |
| Isaac | No; preflight blocked | Not executed | No verdict | Not measured |

Both qualification attempts occurred; neither is a controlled simulator
validation attempt or a simulated-run denominator. Functional cross-backend
validation is not claimed. No foreign process was signalled.

## M1 dependencies and milestone state

19 calibration dependencies inspected, 0 resolved, 19 remain. Every key names
its exact required control/witness in `validation/calibration_dependency_audit.json`.
All still require qualified oracle-PASS Dev controls and explicit justified
margins. The obsolete foreign-workload blocker was replaced with the fresh
null-resource/visibility/control dependency. No numeric threshold was fabricated.

All nine passive witnesses have exactly one state, **REQUIRES QUALIFIED RUNTIME**,
in `validation/passive_witnesses.json`; each retains its specific missing witness
and explicitly notes the unresolved producer/association work. No runtime claim
was manufactured from CAD fixtures. Full-stack 1 Hz CPU/RAM/VRAM/RTF resource
bootstrap was not performed. Existing partial measurements were not reused as
an envelope.

M1 smoke: not run; prerequisites fail. M1.8: not started, 0/140. Campaigns,
seeds, thresholds, oracle and Test A remain untouched. M1 is incomplete.

ROOT_CAUSES entry: `docs/m2/ROOT_CAUSES.md` does not exist at the input revision
and was not created: the user requires an entry once the implementation is
validated, which has not happened.

## Exact remaining blocker and next action

Technical: no approved remount, actual RGB-D feasibility frames, validated
height estimator or consumer. Nine passive witnesses and all 19 calibration
dependencies remain downstream work.

External: the final host is no longer free of foreign simulator work. The owner
of domain115 Gazebo must release it; unreadable PID60465 must be resolved under
the existing qualification rules. Neither process belongs to this session.

Policy: production preflight requires measured RAM/VRAM limits before
any simulator launch, while the requested full-stack measurement needs that
launch. The approved patch additionally requires rendered feasibility before
consumer implementation. No bootstrap profile exists. This is a qualification
policy cycle, not evidence of inadequate hardware or impossible RGB-D geometry.

Human input required: external workload owner release and an approved bootstrap
qualification policy or independently validated full-stack resource envelope.
General instructions to continue do not
supply the missing limits. Authorizing a sensor remount does not define a safe
resource profile. The session requested this missing policy without assuming a
waiver of the explicit no-safety-gate-removal rule.

Next Master Plan action: resolve that bootstrap gate, obtain qualified sensor
feasibility evidence, implement/validate the bounded observer and guarded consumer,
then return to the existing M1 calibration → smoke → M1.8 sequence. There is no
claim that this evidence checkpoint satisfies the requested implementation.

Evidence root: `docs/m2/target_observation_20261008/`.
Raw evidence: `/home/gautham/coco_m1_runs/target-observation-20261008/`.
`validation/external_evidence.json` records exact file hashes. Failed/negative
and intermediate probe results remain retained outside Git.
