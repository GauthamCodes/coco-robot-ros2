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
