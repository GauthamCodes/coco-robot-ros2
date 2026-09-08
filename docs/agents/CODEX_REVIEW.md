# C2-NAV.33 — independent verification

Reviewed 2026-09-09 (Asia/Kolkata). Validation: **offline analysis, installed-library execution, and unit/static tests**. No simulator, live robot, ROS parameter service, or navigation action was started.

**Decision: interval 2 can expose a subset of normalized weights, but the proposed path does not observe every pre-resampling state or preserve historical interval-1 behavior. The full instrumentation gate is NOT validated. This delivery is review-only; existing instrumentation and experiments are preserved.**

## CLAUDE CLAIM

The C2-NAV.32/33 entries in `docs/SESSION_LOG.md`, pre-registration commit `5bc214c`, and `docs/data/c2nav33_weights.py` propose raising `resample_interval` from 1 to 2 to expose pre-resampling importance weights. Equal weights are classified as `post`, unequal weights as `pre`, with alternation described as a live falsifier. Verdict B treats a mean confidence interval crossing zero as evidence that weighting does not favor south.

Commit `d44041a` already contains Claude's reported experiment, frozen derived statistics, and further analysis. The assigned checkout is not an empty implementation branch.

## INDEPENDENT EVIDENCE

### Worktree and instructions

- Assigned worktree: `.codex/worktrees/c2nav0-implementation`, initially clean and detached at `d44041a2eaf2b1879bfadaff9530f986f6471b60`.
- Main initially points to `ea66155330af26b322758d094eb881ebedac843a`. Its directory contains existing modifications and untracked files. Neither those files nor the locked Claude diagnosis worktree were edited.
- Inspected root `AGENTS.md`, root/worktree `CLAUDE.md`, project constraints, and historical evidence/scripts. Root TASK says no active task; HANDOFF says no active handoff; RESULTS and DECISIONS are placeholders. Those agent-state files were absent in this worktree. The explicit user assignment supplies the task scope.

### C2-NAV.28–32 evidence assessment

| Evidence | What it supports and what it does not establish |
| --- | --- |
| C2-NAV.28, `5e0b660` / `a1b04d3` | AMCL trace and place-dependent error. Historical schema tests no longer match the subsequently extended recorder. A spatial association does not establish a cause. |
| C2-NAV.29, `91e5f3a` | Scan/map comparison uses reconstructed scans; raw scans were not recorded. Historical and measured frame conventions must remain distinct. |
| C2-NAV.30, `266e4cd` | Recorded published cloud geometry and flat weights concern the post-resampling population. They cannot reconstruct the original weighted population or lost particles. |
| C2-NAV.31, `572b392` | Offline likelihood reweighting uses reconstructed scans and already-resampled particles, not the original live update inputs. |
| C2-NAV.32, `8f15982` | Installed motion-model oracle is useful, but ground-truth motion substitutes for the wheel-odometry TF actually consumed by AMCL. This limits the claimed elimination of the live motion chain. |

### Installed implementation

`dpkg-query -W ros-jazzy-nav2-amcl` returned `1.3.11-1noble.20260412.054619`. SHA-256 measured this session:

| Library under `/opt/ros/jazzy/lib` | SHA-256 |
| --- | --- |
| libamcl_core.so | 5b17902144fd474985ddebf771e2d1dff58c464112c80cc707c3ba7d38e6139f |
| libpf_lib.so | e9367fddc3cc48fcd66a3caed0d2869a88e3baa27fbc37e1b863f68218d933e8 |
| libsensors_lib.so | 732e664bbbeae2cc57a842d4c58aba409a213d8e3779484fd19d2447cf20187f |

Independently inspected actual branch destinations with `objdump -d --no-show-raw-insn -C`, not merely Claude's regex results. In `laserReceived`, `updateFilter` is called at `0xe4034`; the counter increments and divides by the interval at `0xe4050`. Zero remainder branches at `0xe4058` to resampling at `0xe4391`. Both paths reach current-set selection at `0xe4061`. The force-update test at `0xe4106` can reach cloud publication at `0xe43ac` without resampling. A compiled ABI probe gives current_set offset 24, sets offset 32, set size 144, and sample weight offset 24, matching installed addressing.

Version-tagged upstream sources were downloaded into `/tmp/c2nav33-review`:
[amcl_node.cpp](https://github.com/ros-navigation/navigation2/blob/1.3.11/nav2_amcl/src/amcl_node.cpp),
[pf.c](https://github.com/ros-navigation/navigation2/blob/1.3.11/nav2_amcl/src/pf/pf.c), and
[likelihood_field_model.cpp](https://github.com/ros-navigation/navigation2/blob/1.3.11/nav2_amcl/src/sensors/laser/likelihood_field_model.cpp).
They corroborate the inspected mechanism; this does not prove the installed Debian package has no source patches.

Downloaded SHA-256, respectively:

- `11c801a2bf290d299046ace3bdc7f6be4317e07da8d43010d6c50f7102fa6d4b`
- `6747b6f528bd1e3727ebab79eece7ea52379737127ad4431276901ac88d82b6e`
- `84a4542b6891cd665139fcc75dc6b71fa0d2175f167de5c11df463d2f6fe101d`

The source's sensor score multiplies incoming weights; the PF normalizes them. Resampling creates equally weighted particles. Published values are normalized importance weights, not raw scan likelihoods. Skipping resampling permits weights to accumulate across sensor updates.

### Observability and independent counterexample

At interval 2, an ordinary skipped-resample update publishes its normalized weights. The next update performs another weighting and resamples before publication, hiding those weights. Thus these are intermediate weights from a changed filter, not the full sequence of weights consumed by resampling. Changing interval also changes particle ancestry, RNG scheduling and ordinarily pose/TF estimate update cadence. Similar cloud medians do not prove unchanged filter behavior.

`gazebo_models/scripts/nav_bench.py::_cloud_cb` already preserves float64 weights. It records callback receipt time via `now()`, not the scan acquisition stamp, and has no explicit update ID or resampling event. Analysis joins the nearest trace row within 0.5 s. This cannot provide exact update attribution; an unweighted centroid proxy is not a simultaneous published AMCL hypothesis.

The existing installed-library oracle compiled and passed. A separate two-particle probe linked against the installed PF measured all of the following (assertions passed):

1. Equal sensor factors yield weights `0.5, 0.5` without resampling or a set flip.
2. Two multiplicative updates with factors `1, 3` yield `0.25, 0.75`, then `0.1, 0.9`.
3. Zero-total sensor fallback yields `0.5, 0.5` without resampling.
4. Resampling also yields flat weights, with a set flip.

**Flat weights therefore do not identify resampling.** Equal scores are possible in the actual likelihood-field model, for example when all beams are ignored at maximum range. The generic zero-total fallback counterexample is not evidence that this positive-score laser configuration encountered zero total.

## AGREEMENTS

- Ordinary interval-1 publications follow resampling and lose weight contrast.
- Interval 2 can expose non-flat normalized weights on skipped-resample updates.
- Float64 capture and explicit missing-data handling are appropriate.
- Weighted-minus-unweighted centroid on the same population is a useful descriptive statistic; south mass alone confounds the existing population bias.
- `paramdiff` confirms one changed leaf, 38 identical guarded AMCL leaves, and no changed navigation leaves.
- Interval-2 results must remain diagnostic observations, not tuning evidence.

## DISAGREEMENTS

1. **Interval 2 is insufficient for historical-behavior diagnosis.** It misses the weights on resampling updates and changes the filter it observes.
2. **The phase classifier is not exact.** Flat sensor updates are classified as post-resampling. Packet loss also defeats parity inference. `cmd_phase` prints alternation counts but does not enforce them: a planted `pre, pre` sequence returns 0 and claims weights are present; all-flat records also return 0. The matrix does not enforce the claimed complete gate before launching.
3. **The binary regex gate is corroboration, not a control-flow proof.** It checks instruction presence and manually modeled offsets, not all branch relationships. Independent branch/ABI inspection supports the narrow claim for this build.
4. **Verdict B overclaims.** Reprocessing the committed bundle gives wall-adjacent median shift `-0.00266 m`, mean `-0.00250 m`, normal interval `[-0.00638, +0.00139]`, with 6 of 9 shifts southward. These are reproduced historical statistics, not a new live measurement. They do not establish a northward average tilt or equivalence to zero. Failure to reject a negative effect is not proof of absence. Serial samples from one run do not establish the independence assumed by the nominal mean interval.
5. **Pose and stationary statements need exceptions.** Source/control flow allow initialization and forced pose publication; ordinary pose updates follow resampling, but “only on resample updates” is too absolute. Initialization and no-motion update requests permit stationary updates; the recorded run did not test them. Stopped commands also do not prove zero accumulated odometry since the preceding update.
6. **Causal eliminations are too broad.** Small instantaneous centroid changes do not exclude accumulated, coupled, or unobserved-update effects. Correlation alone cannot distinguish a driver from a restoring response. C2-NAV.29–32's input proxies remain limitations.

## MISSING EVIDENCE

- Exact installed-package source/patch provenance beyond the matched version, binary hashes, tested PF behavior and inspected branches.
- Raw scans, AMCL-consumed odometry/TF, original input particles/weights and per-update metadata for the interval-1 historical sequence.
- The committed derived bundle is present; this worktree has no `.navbench` raw archive. Reprocessing summaries cannot validate original subscription delivery, packet loss, timing or live parameter readback.
- Independent replicates, a declared equivalence margin and dependence-aware statistics. The localization cause remains unresolved.
- A built and validated interval-1 diagnostic hook with capture-on/off equivalence.

## IMPLEMENTATION PLAN

**This delivery is review-only.** The proposed instrumentation path fails the complete observability/historical-behavior gate. No existing analysis, verdict, parameter file, runtime code or test is edited. The alternative below is a concrete follow-up plan, not a claimed implementation.

The smallest useful alternative is an opt-in, separate diagnostic snapshot after successful sensor normalization and before the existing resampling branch in an isolated, version-matched `nav2_amcl` source overlay. Keep interval 1, filter math, RNG calls, resampling order and existing cloud/pose/TF publication unchanged. Do not move the existing publisher or repurpose `/particle_cloud`; historical consumers depend on its semantics.

Record explicit phase, update sequence, scan stamp/frame, receipt stamp, particle count, poses, normalized float64 weights and resample-due status. A post-resampling record with the same update ID allows comparison without guessing from flatness. If incremental sensor effects with nonuniform priors are needed, capture incoming weights too. Do not equate entry to a function that can return early with a successful sensor update. Preserve actual AMCL pose separately from any proxy and join by update/scan identity.

Default-disabled capture should avoid allocations/I/O in the original path. Enabled I/O still affects timing and must be measured even when filter mathematics is unchanged. A publisher needs lifecycle creation/activation/cleanup; “one statement” understates the full change. ABI-specific preload/interposition is another possible route, but is more fragile than a source hook and is not selected here.

## TEST PLAN

For a future overlay: exercise uniform, nonuniform, zero-total, near-flat and missing/invalid inputs; verify event IDs through dropped messages and initialization; preserve old recorder schema/defaults. With fixed seed and identical scans/odometry, compare capture-off/on filter states, counts, poses and subsequent RNG draws. Build/test the isolated AMCL package and recorder and verify the loaded-library identity. Only after completeness and offline equivalence pass should a fresh bounded simulation collect every interval-1 update.

### Exact results from this review

All commands are relative to the assigned worktree except where specified.

| Check | Result |
| --- | --- |
| `python3 -P docs/data/c2nav33_weights.py gate` | Exit 0; existing C++ oracle built and ran; binary checks passed with limitations above |
| `python3 -P docs/data/c2nav33_weights.py selftest` | Exit 0; 62 passed, 0 failed |
| `python3 -P docs/data/c2nav33_weights.py paramdiff` | Exit 0; ONE LEAF, interval 1 to 2 |
| `python3 -P docs/data/c2nav33_weights.py phase` | Exit 0; frozen open_space inferred pre/post 10/11; wall_adjacent 9/9; not new live evidence |
| `python3 -P docs/data/c2nav33_weights.py verdict` | Exit 0; B and negative statistics reproduced; interpretation rejected |
| `python3 -P docs/data/c2nav31_lf.py selftest` | Exit 0; 48/48 |
| `python3 -P docs/data/c2nav32_mm.py selftest` | Exit 0; 43/43 |
| `python3 -P docs/data/c2nav29_scanmap.py --selftest` | Exit 0; 21/21 |
| `python3 -P docs/data/c2nav28_amcl.py selftest` | Exit 1; 5 existing failures: appended schema/count, historical file allow-list, before/after write_trace byte-identity assumptions |
| `python3 -P docs/data/c2nav30_cloud.py selftest` | Exit 1; 1 existing historical file allow-list failure on C2-NAV.31–33 files |
| `source /opt/ros/jazzy/setup.bash`, then `python3 -m pytest -q --ignore=test_integration` from `gazebo_models` | Exit 0; 41 passed in 0.71 s |
| `python3 -m flake8 --isolated --select=E9,F63,F7,F82 docs/data/c2nav33_weights.py docs/data/c2nav33_selftest.py docs/data/c2nav33_extra.py gazebo_models/scripts/nav_bench.py` | Exit 0; focused Python error checks, not full style lint |
| `bash -n docs/data/c2nav33_matrix.sh docs/data/c2nav33_liveparam.sh` | Exit 0 |
| `g++ -std=c++17 -Wall -Wextra -Wpedantic -Werror -fsyntax-only docs/data/c2nav33_oracle.cpp -I/opt/ros/jazzy/include` | Exit 0 |
| Independent PF probe build/run below | Exit 0; four counterexample/control assertions passed; ABI offsets match |
| Monkeypatched `cmd_phase`: two consecutive pre records / all-flat records | Both return 0; nonalternating pre records print success |

No ROS package implementation changed, so no overlay/colcon build is claimed. The relevant existing C++ diagnostic was built by `gate`; the independent probe was compiled with warnings as errors. Live/runtime equivalence is not yet measured.

Failed investigation commands are recorded: initial sandbox execution failed with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`; subsequent shell commands used approved escalation. Initial C2-NAV.29 invocation used positional `selftest` (exit 2); corrected `--selftest` passes. A library lookup used nonexistent `liblasers_lib.so`; package enumeration located `libsensors_lib.so`. A recorder lookup under `coco_mission` failed; the file is under `gazebo_models/scripts`. An initial review-file apply_patch also failed because the sandbox helper could not initialize; the file was then written through approved shell execution.

### Reproduce the independent PF counterexample

Save the following as `/tmp/c2nav33-probe.cpp`:

```cpp
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstddef>
#include "nav2_amcl/pf/pf.hpp"
static pf_vector_t pose(void *) { return pf_vector_t{}; }
static double sensor(void *data, pf_sample_set_t *set) {
  const auto factors = static_cast<double *>(data);
  double total = 0;
  for (int i = 0; i < set->sample_count; ++i) {
    set->samples[i].weight *= factors[i];
    total += set->samples[i].weight;
  }
  return total;
}
int main() {
  auto pf = pf_alloc(2, 2, 0, 0, pose);
  pf_vector_t mean{};
  pf_matrix_t cov{};
  pf_init(pf, mean, cov);
  const int initial = pf->current_set;
  double flat[] = {1, 1}, tilted[] = {1, 3}, zero[] = {0, 0};
  pf_update_sensor(pf, sensor, flat);
  auto s = pf->sets + pf->current_set;
  assert(pf->current_set == initial && s->samples[0].weight == .5 && s->samples[1].weight == .5);
  puts("PASS flat sensor weights WITHOUT resampling: 0.5 0.5");
  pf_update_sensor(pf, sensor, tilted);
  assert(s->samples[0].weight == .25 && s->samples[1].weight == .75);
  pf_update_sensor(pf, sensor, tilted);
  assert(std::abs(s->samples[0].weight - .1) < 1e-15 && s->samples[1].weight == .9);
  puts("PASS two multiplicative sensor updates: 0.25/0.75 -> 0.1/0.9");
  pf_update_sensor(pf, sensor, zero);
  assert(pf->current_set == initial && s->samples[0].weight == .5 && s->samples[1].weight == .5);
  puts("PASS zero-total fallback WITHOUT resampling: 0.5 0.5");
  pf_update_resample(pf, nullptr);
  s = pf->sets + pf->current_set;
  assert(pf->current_set != initial && s->samples[0].weight == .5 && s->samples[1].weight == .5);
  puts("PASS resampling also yields flat weights and flips current_set");
  std::printf("ABI current_set=%zu sets=%zu set_size=%zu weight=%zu\n", offsetof(pf_t, current_set), offsetof(pf_t, sets), sizeof(pf_sample_set_t), offsetof(pf_sample_t, weight));
  pf_free(pf);
}

```

Build and run:

```bash
g++ -std=c++17 -Wall -Wextra -Wpedantic -Werror -O2 /tmp/c2nav33-probe.cpp -I/opt/ros/jazzy/include -L/opt/ros/jazzy/lib -lpf_lib -Wl,-rpath,/opt/ros/jazzy/lib -o /tmp/c2nav33-probe
/tmp/c2nav33-probe
```

For the phase-gate counterexample, import `c2nav33_weights` from `docs/data`, temporarily replace `wsnaps` with a function returning two dictionaries `{'phase': 'pre', 'ess_ratio': 0.9}`, call `cmd_phase(None)` and restore it. Repeat with `phase='post', ess_ratio=1.0`. Neither fixture involves ROS.

## WHETHER LIVE EXPERIMENT IS JUSTIFIED

**Not with the current instrumentation as a test of historical weighting.** Another interval-2 run cannot fill the structural gap or preserve the baseline. No live experiment was run. Recommended next action: review and implement the isolated interval-1 pre-resampling hook, then validate it offline before a bounded simulation. Real robot hardware testing is not justified by this review.

## Delivery

Only this review and the required `docs/SESSION_LOG.md` checkpoint change. No instrumentation implementation occurred, so no implementation entry is added to RESULTS.md. The review is committed in the assigned detached worktree; its hash is reported after creation rather than embedded self-referentially here. No main change, merge, reset, rebase or diagnosis-worktree edit.
