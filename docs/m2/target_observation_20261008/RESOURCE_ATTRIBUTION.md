# Resource attribution — verification continuation

Historical workloads are NON_QUALIFYING and not paired experiments. Values are bytes; no causal component subtraction or production requirement is inferred.

| Component | Sensor-only capture02 RSS peak | Observer acquisition01 RSS peak | Guarded arm06 RSS peak | Guarded startup09 RSS peak |
|---|---:|---:|---:|---:|
| gazebo_including_sensor_plugins | 841072640 | 868466688 | 890712064 | 169979904 |
| launch_or_runtime_overhead | 68489216 | 155582464 | 708440064 | 388009984 |
| moveit_manipulation | not recorded | not recorded | 219598848 | 193036288 |
| observer | not recorded | 252649472 | 258150400 | 147341312 |
| recorder | 91594752 | 145178624 | 104280064 | 86532096 |
| robot_tf | 20586496 | 20971520 | 23642112 | 21852160 |
| ros_bridge_middleware | 43323392 | 43724800 | 47538176 | 42385408 |

Historical PSS was not recorded. RSS shares pages and peaks are not simultaneous. The new sampler reads PSS/private/swap-PSS by verified PID/start identity and reports permission failures as unavailable. `live_pss_probe.json` exercises this on this evaluator process only; it is not robot resource evidence.

| Run | Available RAM minimum | Host CPU peak % | Load1 peak | Host VRAM used peak | Receipt-delta RTF min–max |
|---|---:|---:|---:|---:|---|
| acquisition-camera-only-02 | 8638615552 | 39.768019884009945 | 2.6591796875 | 1030750208 | 0.7270423758360464–1.2963387804700823 |
| acquisition-01 | 8672575488 | 84.05207485760782 | 4.3388671875 | 1155530752 | 0.004938259765308851–1.7114747093008371 |
| guarded-motion-06 | 8400928768 | 96.69937555753792 | 9.35107421875 | 1034944512 | 0.2543590056120691–0.9829388015135558 |
| guarded-motion-09 | 8120913920 | 98.25511432009627 | 7.07373046875 | 839909376 | unavailable |

Full stack and Isaac: no calibrated complete-workload measurement. Partial startup/carry samples do not establish settled RTF or machine requirements. Host GPU/RAM/CPU include background activity; GPU per-process graphics allocation, plugin allocation and DDS queue occupancy remain unavailable. Recording disk bytes and configured queue limits are captured separately. Process first/last observations bound lifetimes; they do not assert exact exit times.

Observed removable cost: recorder callback called full message-to-dict conversion rather than the already implemented image-summary helper. Fixed the call site; actual ROS test proves byte hash validation and unchanged raw MCAP payload. No measured runtime RAM saving is claimed without a new controlled workload. Other previous buffer/queue/spawner optimizations are retained.

Gazebo read-only preflight at commit f664282: available RAM 8,104,574,976 < unchanged reserve 8,229,275,648 (shortfall 124,700,672). Load1 0.658203125; GPU free 5,566,889,984. No simulator launched. Production Isaac preflight separately rejects uncalibrated RAM/VRAM and unreadable process metadata.

Reproduce: `python3 eval/resource_attribution.py RUN1 RUN2 RUN3 RUN4 --output NEW.json`. Exact source paths and hashes are in `validation/verification_20261009/resource_comparison_final.json`.


### Final controlled startup evidence — 2026-10-10

After changed-host read-only preflight passed, one NON_QUALIFYING controlled
attempt exited ABORTED_BOOTSTRAP_SAFETY on unreadable `/proc/96143/exe`. Only the
recorder started; Gazebo never launched and capture never began. Owned teardown:
zero survivors/errors; foreign signals NONE. Oracle/verifier UNSCORABLE. No retry:
runtime available RAM margin ~1.135 GB was below the previous incomplete arm run's
observed 1.304 GB decrease. Production Isaac RAM/VRAM calibration remains null.
Early-abort automatic reporting regression: 56 passed. Root cause remains OPEN;
physical attachment/lift/retention/release/placement unverified, all M1 counts
unchanged. Full report: `docs/m2/target_observation_20261008/VERIFICATION_REPORT.md`.
