# CODEX P0.2 hardening handoff — 2026-09-22

## Status and provenance

Implementation building blocks are ready for selective integration by Claude.
This is **not** a claim that the integrated P0.2 product is complete. Remaining
contract conflicts and required caller changes are listed below.

- Worktree: /home/gautham/coco-p02-hardening
- Branch: codex/p02-hardening
- Actual repository: /home/gautham/ros2_ws(personal)/src/coco-robot-ros2
- Authorized base: 921f6d0bef1aaac4a890df3fb14efe04608dee02. The user explicitly
  approved this correction after inspection showed d317d85 lacks P0.1.
- Runtime implementation tip: 980f7db. Evidence/replay scripts: fcefc1b.
- Scope evidence: `git diff --name-only 921f6d0..codex/p02-hardening`.
  No changes to main, Claude's worktrees, product web/*, platform_server.py,
  session.py, launch files, Nav2, the arbiter, or docs/RSE_ASSIGNMENT_PLAN_V2.md.
  No Claude branch was cherry-picked.

## Verification results

All numbers below are measured in this worktree, except the explicitly
identified historical baseline.

| Package | Passing | Failed/errors | Skipped |
|---|---:|---:|---:|
| coco_config | 70 | 0 | 0 |
| custom_teleop | 75 | 0 | 0 |
| coco_rl | 193 | 0 | 0 |
| coco_perception | 139 | 0 | 0 |
| gazebo_models | 181 | 0 | 0 |
| coco_moveit_config | 12 | 0 | 0 |
| coco_sim | 55 | 0 | 0 |
| coco_mission | 315 | 0 | 0 |
| coco_web | 470 | 0 | 0 |
| **Total** | **1510** | **0** | **0** |

Evidence: [validation.json](diagnostics/p02_hardening/evidence/validation.json)
and the adjacent per-package JUnit XML and log files. Tests ran per package on
ROS domain 97, using a private build/install tree under /tmp/coco-p02-validation.
Gazebo launch integration tests were excluded following the repository's
existing test procedure; these counts do not claim simulation integration.

The unchanged base's focused web suite was measured at **297 passed**:
[p02-baseline-web.log](diagnostics/p02_hardening/evidence/p02-baseline-web.log).
The base's 1334 total is historical documentation, not a separately rerun
full baseline in this sprint. The original brief's 1139 belongs to P0.1.

All nine selected packages built successfully:
[build.log](diagnostics/p02_hardening/evidence/build.log).
The final affected-package rebuild also passed:
[final-build.log](diagnostics/p02_hardening/evidence/final-build.log).
Build warnings about an unbuilt pytest-repeat egg and test warnings about
forking after threaded imports remain visible in the logs.

The web suite includes six Node subtests inside the cross-language pytest
wrapper, real localhost Tornado sockets with a fake robot node, pure helpers,
and existing lint/safety/executive-state drift checks.

### Live validation

[ros-smoke-final.log](diagnostics/p02_hardening/evidence/ros-smoke-final.log)
records the final runtime code, revision fcefc1b (whose runtime implementation
is 980f7db), on isolated ROS domain 98:

- Production CocoWebNode, Platform and ControlSocket running with real DDS.
- Synthetic BEST_EFFORT RGB8 and 32FC1 images at 320x240; 480-ray scan input.
- 14 telemetry and 14 binary LiDAR frames observed; the existing downsampling
  produced 240 rays per delivered scan.
- No camera/depth frames before opt-in; one of each observed after subscribing.
- No further camera/depth frames after unsubscribe acknowledgement during
  the bounded observation; the ROS subscriptions were destroyed.
- Recorder saw teleop intents [0.05, 0.0, 0.05, 0.0], proving a positive control
  before explicit STOP and before last-client-disconnect STOP.

This was synthetic ROS data, **not a Gazebo mission, physical robot, browser
rendering test, or performance measurement**. The smoke publishes no wheel
commands and starts no arbiter. Its server binds an ephemeral loopback port;
the node's normal configuration log still prints its default port.

No Gazebo was started or killed. At final inspection a simulator using
/home/gautham/coco_ws_build was running outside our private overlay; it was
left untouched. See process-observation.txt in the evidence directory.

Docker is unavailable on this machine. No Docker image build or runtime
success is claimed. **29 static/fake-process checks passed**:
[p02-docker-green.log](diagnostics/p02_hardening/evidence/p02-docker-green.log).

## Commits and exact integration order

Apply these in order to Claude's chosen integration branch, which must already
contain 921f6d0. These are Codex commits; none imports Claude's product branch.

| Order | SHA | Change |
|---:|---|---|
| 1 | 992e5f8 | coco.v1 parser ambiguity, overflow and malformed-input guards |
| 2 | cc3a071 | Atomic subscription validation, cleanup and queue metrics |
| 3 | 34f04ae | Sensor metadata/length validation, LiDAR invalid returns |
| 4 | 806fe37 | Image shape/settings, padded rows and depth byte order |
| 5 | b007861 | Finite/nonnegative mission measurements |
| 6 | aa72cee | Real WebSocket routing and STOP tests |
| 7 | 43f8213 | Bound padded raw image buffers |
| 8 | c9d05f7 | Independent lifecycle/health vocabulary and policy validators |
| 9 | 09a77aa | Standalone frontend transport and cross-language tests |
| 10 | 54687e1 | Keep Docker launch PIDs waitable by their parent shell |
| 11 | 980f7db | Validate binary buffers before coercion/allocation |
| 12 | fcefc1b | Reproduction scripts and retained validation evidence |
| 13 | c0d2f11 | Declare Node as a test-only dependency |

The subsequent handoff/checkpoint commit adds this document and final smoke
evidence; discover its SHA with `git log -1 codex/p02-hardening`. This avoids
a circular attempt to embed a document's own commit hash in that document.

After the commits, perform the caller integration steps in the next section,
then run the [reproduction commands](diagnostics/p02_hardening/README.md).
Do not declare product readiness from helper tests alone.

## Files changed and public APIs

### Protocol — protocol.py

Existing typed platform commands remain the only control vocabulary.
hello, subscribe, unsubscribe, approved command types, and outbound ack/error
retain coco.v1. A generic `command` envelope is deliberately not added.
The server's current typed intents are the command concept in this contract.

Duplicate JSON keys, boolean correlation IDs, non-finite ping timestamps and
overflowing numeric inputs now raise ProtocolError rather than selecting an
ambiguous request or leaking an exception. Existing unknown-field, unknown-type
and arbitrary ROS-target refusals remain.

Evidence: test_protocol_hardening.py, existing test_protocol.py/test_safety.py,
and the real-socket test_transport.py. The pre-fix log records six failing
new behavioral cases; all are green in the final suite.

### Subscriptions/backpressure — streams.py

The existing Subscription API is retained. Constructor/subscribe/unsubscribe
now validate the whole stream list before mutation, including direct pure
calls that bypass protocol.decode. Invalid requests raise ValueError.
Unknown configure targets cannot allocate arbitrary config keys.

- One independent object per client.
- Default: telemetry, mission, lidar, map, path.
- Camera/depth require opt-in plus hello.binary=true.
- Duplicate membership updates are idempotent.
- Existing telemetry-pinned-on policy is preserved.
- New should_send(stream) is a deterministic membership/binary-capability
  query; due() and ready() remain separate rate/backpressure decisions.
- New close() is idempotent, removes membership and retained write futures,
  and does not cancel writes owned by Tornado.
- New queue_depth(stream), and as_dict().queue_depth/send_attempts.
  Send attempts are defined as sent + backpressure-dropped outcomes; they
  exclude unsubscribed/rate-suppressed candidates and write exceptions
  that occur before mark_sent.

The existing policy remains **one in-flight sensor write per stream/client**.
Candidates arriving while that write is pending are dropped, not queued.
At or above the existing 1 MiB socket-buffer threshold, ready() rejects another
sensor write. After the pending write completes, a fresh source frame may be
sent. The pure helper does not retain payload bytes or block on a future.

Evidence: test_streams_hardening.py exercises 10,000 rejected candidates and
client isolation; test_transport.py proves only one socket write occurs while
1,000 further candidates are dropped. Unsubscribe/resubscribe cannot bypass
the in-flight bound.

**This proves the sensor bound only.** The existing server's JSON/control
write path is not globally bounded; see integration blockers below.

### Binary — binary.py

The existing prefix and format version remain unchanged:

| Offset | Bytes | Meaning |
|---:|---:|---|
| 0 | 4 | ASCII COCO |
| 4 | 1 | format version 1 |
| 5 | 1 | kind: 1 LiDAR, 2 camera, 3 depth |
| 6 | 2 | big-endian uint16 JSON-header length H |
| 8 | H | UTF-8 JSON metadata |
| 8+H | remainder | payload |

New encoders add `payload_bytes`; LiDAR also explicitly adds
`enc: "uint16be-mm"`. Metadata retains stream, seq, t, dropped; images carry
w/h/enc and optional quality; depth carries min_m/max_m and optional palette.
LiDAR retains count, angle_min, angle_step, scale=1000, floor and no_return=0.

- Exact new payload length is verified; LiDAR always requires count*2 bytes.
- Stream/prefix disagreement, missing required metadata, invalid numeric
  values, malformed depth ranges, unknown encodings and ROS target fields
  are refused with BinaryFrameError.
- Header <=8192 bytes; payload <=8 MiB; image dimensions each <=8192 and
  total pixels <=8 Mi; seq is a nonnegative browser-safe integer.
- Byte-buffer type/size is checked before coercion/copying.
- NaN/infinite/nonpositive/absent LiDAR returns become zero; valid ranges are
  millimetres, clamped at uint16 capacity. No ROS serialization is used.
- Previously emitted complete P0.2 frames are supported without payload_bytes:
  LiDAR is checked by count and legacy images by JPEG start/end markers.
  Legacy LiDAR's implicit encoding is accepted.
- Minimal/incomplete headers used by old generic envelope tests are now
  refused; those tests use complete fixture metadata while retaining their
  prefix-corruption assertions.
- The decoder validates framing/metadata, not the full JPEG bitstream.
  Legacy JPEG marker validation is weaker than an explicit byte count.

Evidence: test_binary.py, test_binary_hardening.py, Node cross-language fixtures,
and the live ROS smoke. Pre-fix binary tests recorded 28 failures.

### Imaging — imaging.py

colour_jpeg adds keyword-only step=None. depth_jpeg adds keyword-only step=None
and is_bigendian=False. Defaults preserve tightly packed current sensor data.
Invalid dimensions/settings/stride are rejected as ImageError. Row padding
is removed before decoding; depth byte order is explicit. Packed pixel and
raw-layout allocations are bounded (raw layout <=32 MiB).

JPEG camera delivery and grayscale depth visualization are preserved.
No QoS or navigation configuration changed. Evidence: existing imaging tests,
test_imaging_hardening.py and the real ROS smoke. Pre-fix new tests recorded
22 failures and two passes.

### Mission/session helpers

mission_view.py now maps invalid/non-finite/negative measurements to None and
refuses to truncate fractional retry counts. State/result/colour/reason are
preserved; no overall progress or ETA is added. Existing exhaustive mapping
and AST drift checks against all actual executive states remain green.
Evidence: test_mission_view.py and test_mission_hardening.py.

New lifecycle.py exports LIFECYCLES, HEALTH, validate_axes(lifecycle, health)
and validate_transition(current, target, allowed_edges). Both axes use the
locked vocabularies. Duplicates are no-ops; invalid states/edges raise
ValueError. **Allowed edges, including restart policy, must be supplied by
Claude.** The helper neither derives lifecycle from health nor replaces
session.py. Evidence: test_lifecycle.py.

### Frontend candidate

New transport/client.mjs and transport/client.test.mjs are isolated from
web/*. The module provides decodeFrame and Transport: subscribe/unsubscribe,
binary support declaration, connection state, heartbeat deadline, bounded
reconnect delay, desired-stream restoration, stale-socket suppression, and
intentional-close cleanup. Robot commands are not buffered or replayed.

Python-produced fixtures test decoding in Node, including uint16 byte order,
length corruption, defaults, reconnect and heartbeat. The helper is **not**
loaded by index.html or installed by setup.py; Claude chooses the UI wiring
and installation path. Browser rendering remains unverified.
Evidence: test_frontend_transport.py and transport/client.test.mjs.
coco_web/package.xml declares nodejs as a test dependency; catkin_pkg parsed
the manifest successfully and rosdep resolves it to the nodejs apt package
(evidence/nodejs-rosdep.txt). No Node runtime dependency is introduced.

### Docker

docker/entrypoint.sh now calls launch_bg in the parent shell and assigns
LAUNCHED_PID directly. Previously, command substitution placed the launched
process in a subshell, making the parent's wait invalid. Tests run a fake ros2
child with exit 7 and verify the parent can wait for that exact status.
Deployment strategy, Dockerfile and compose configuration are unchanged.
Evidence: coco_rl/test/test_entrypoint_children.py and the Docker red/green logs.

### Added test/replay files

New Python tests:
test_protocol_hardening.py, test_streams_hardening.py,
test_binary_hardening.py, test_imaging_hardening.py,
test_mission_hardening.py, test_transport.py, test_lifecycle.py,
test_frontend_transport.py, and coco_rl/test/test_entrypoint_children.py.
Existing test_binary.py fixtures were updated as described above.

diagnostics/p02_hardening contains README.md, run_checks.sh, ros_smoke.py,
and the evidence logs/XML/JSON. This handoff and a docs/SESSION_LOG.md
checkpoint complete the repository documentation.

## Integration blockers and required caller changes

These are deliberately exposed rather than silently changing Claude's
architecture or overstating what the tests prove.

1. **Session semantics remain an owner task.** session.py still exposes
   legacy readiness strings, not the locked health axis. A pure probe
   measured fail() returning CREATED on a new session and READY on a ready
   session; losing all components after readiness returns CREATED.
   [session-observations.json](diagnostics/p02_hardening/evidence/session-observations.json)
   records these results. Claude must supply the legal transition graph and
   integrate the distinct health axis; lifecycle.py deliberately supplies
   no invented default graph.

2. **Global slow-client memory is not yet bounded.** ControlSocket.send_stream
   writes telemetry/JSON unconditionally; send_binary alone applies the
   pending-write and socket-buffer checks. This is derived directly from
   platform_server.py, not a measured whole-process memory guarantee.
   Claude must choose the control/telemetry transport bound while preserving
   STOP acknowledgement semantics. The existing policy also drops incoming
   sensor candidates, whereas the brief mentioned dropping old/replacing
   latest: the existing one-in-flight policy was preserved, not redesigned.

3. **Wire drop counters need server integration.** Platform.push_sensors encodes
   a shared frame with dropped=0, then sends it to all clients. Per-client
   counters are accurate in Subscription, but those shared headers do not
   carry each client's losses. This is a source-level finding, not fixed by
   helper-only work.

4. **Call Subscription.close() from the retained handler's close path.**
   Existing on_close removes the client/session and recomputes demand, so
   disconnect STOP remains correct and is socket-tested. The new explicit
   cleanup is available for Claude to wire in; platform_server.py was not edited.

5. **Pass image layout metadata at the ROS boundary.** For padded/big-endian
   inputs, _encode_image must pass step=msg.step and
   is_bigendian=bool(msg.is_bigendian) to the new helpers. Current native
   packed 320x240 inputs passed the smoke unchanged. Do not change QoS.

6. **Public MJPEG descriptors still expose ROS topic names.** _stream returns
   topic and a topic-bearing URL. This conflicts with the locked public
   message rule; the legacy MJPEG integration needs an owner-selected alias
   or proxy solution. No alternate video architecture was introduced.

7. **Timestamp provenance needs care.** Sensor t remains the existing server
   timestamp. mission_view.changed_at is still derived from supplied now
   minus executive elapsed, not an observed transition stamp. The current
   server passes wall time while executive elapsed uses ROS time; under
   non-unit simulation rate these cannot establish an exact wall transition
   time. Preserve explicit provenance or pass compatible clocks during
   integration; the helper does not manufacture a new mission timestamp.

8. **Telemetry remains non-unsubscribable**, per existing WEB_API.md and tests.
   Confirm this retained policy against the brief before changing it.

9. **Transport keepalive configuration warns at runtime.** The installed
   Tornado clamps the existing 30-second ping timeout to the 10-second interval.
   This warning is retained in both smoke logs. Claude owns server settings.

10. **Frontend integration remains explicit.** Install/import the isolated
    candidate only after reviewing it against Claude's existing transport.
    It is not a replacement UI. Its native JSON.parse uses browser duplicate
    key semantics; the Python boundary additionally rejects duplicate keys.
    The helper's client callbacks must not be treated as protocol validation
    for robot control; protocol.decode remains the server authority.

## Next action

Claude: review the blockers, apply the listed commits in order, integrate
the new helper calls and owner-selected session/transport policies, then run
diagnostics/p02_hardening/README.md. Docker runtime, actual Gazebo mission
regression, browser rendering, and deployment remain unverified here.
