# C2-NAV.35 implementation result — 2026-09-11

**Implemented and verified offline; publication blocked by concurrent remote advancement.**

- Added a pinned, isolated AMCL overlay preparer and compile-time default-disabled
  capture at the actual odometry lookup, prediction arguments and differential
  motion decomposition. No approximation replaces AMCL.
- Added bounded event/GT JSONL sidecars and an offline synchronized joiner. Legacy
  GT receipt semantics and the existing 58-column trace remain unchanged.
- Dedicated offline tests: **12/12 passed**. Installed and rebuilt motion models
  produced identical tested particles, weights and RNG progression with capture
  off/on. Missing TF, timestamp preservation, unknown anchors and loss accounting
  were tested with synthetic inputs.
- Both AMCL build modes pass with compiler warnings as errors. The enabled overlay
  and affected `gazebo_models` package install into isolated local prefixes.
  `gazebo_models` baseline: **41 passed**. Syntax and scoped flake8 checks pass.
- Historical analysis checks: .29 **21/21**, .31 **48/48**, .32 **43/43**,
  .33 **62/62**, .34 **18/18**. .28/.30 retain five/one historical scope/schema
  failures. No historical analysis/data file was edited.
- AMCL/controller configs, geometry, maps/costmaps, goals/waypoints, BT,
  PolygonSlow/Stop and DWB are unchanged. Main remains `ea66155`. The pre-existing
  untracked `base_footprint` file is untouched.
- No ROS initialization, node, AMCL, simulator, mission or live experiment was run.
  The odometry hypothesis remains **UNKNOWN**.

Limits: no pre-callback MessageFilter drop API in installed Jazzy; one AMCL instance
per process; live timing neutrality is not claimed; verified GT/model extrinsics
and sufficient timestamp precision are required. Full implementation/schema,
commands, artifact hashes and test details are in `CODEX_REVIEW.md` and
`diagnostics/c2nav35/README.md`.

The remote target advanced to `efde9a0` while this work was underway, containing a
separate `coco_nav_diag` implementation and pre-flight fix. This result is committed
locally for review, not merged/rebased or pushed over that work. Publication and
selection of the diagnostic implementation need direction before the separately
approved single baseline approach/wall traversal.
