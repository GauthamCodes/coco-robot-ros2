#!/usr/bin/env python3
# Copyright 2026 Gautham Anil
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Run one fresh Isaac fetch through the shared ROS mission; own only children."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from process_groups import stop

from coco_sim.episode import generate_episode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--domain", type=int, default=82)
    parser.add_argument(
        "--level", choices=["colours", "positions"], default="colours"
    )
    parser.add_argument("--seed", type=int, default=5)
    parser.add_argument("--colour", default="red")
    parser.add_argument("--timeout", type=float, default=1200)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[1]
    env = dict(os.environ, ROS_DOMAIN_ID=str(args.domain))
    episode = generate_episode(
        seed=args.seed,
        level=args.level,
        backend="isaac",
        requested_colour=args.colour,
    )
    (out / "manifest.json").write_text(episode.to_json())
    # The mission receives the task only; the world/evaluator retains the manifest.
    (out / "robot_inputs.json").write_text(
        json.dumps(episode.task_view(), indent=2)
    )
    description = subprocess.check_output(
        ["xacro", str(repo / "gazebo_models/urdf/coco_robo2.xacro")], env=env
    )
    (out / "robot.urdf").write_bytes(description)
    meta = {
        "head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip(),
        "dirty": subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=repo, text=True
        ),
        "command": __import__("sys").argv,
        "domain": args.domain,
    }
    source_paths = (
        subprocess.check_output(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            cwd=repo,
        )
        .decode()
        .split("\0")
    )
    meta["source_sha256"] = {
        name: hashlib.sha256((repo / name).read_bytes()).hexdigest()
        for name in source_paths
        if name
        and (repo / name).is_file()
        and not name.startswith("docs/data/")
        and Path(name).suffix
        in (".py", ".sh", ".yaml", ".yml", ".xacro", ".xml", ".srdf", ".cfg")
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    (out / "source.patch").write_bytes(
        subprocess.check_output(["git", "diff", "HEAD"], cwd=repo)
    )
    handles, children, exits = [], [], {}

    def spawn(name, command):
        handle = (out / (name + ".log")).open("w")
        handles.append(handle)
        process = subprocess.Popen(
            command,
            cwd=repo,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        children.append((name, process))
        return process

    try:
        sim = spawn(
            "isaac",
            [
                "bash",
                str(repo / "scripts/isaac_sim_coco.sh"),
                "--fetch",
                "--robot-urdf",
                str(out / "robot.urdf"),
                "--episode-manifest",
                str(out / "manifest.json"),
                "--output",
                str(out / "sim"),
            ],
        )
        deadline = time.monotonic() + 300
        while not (out / "sim/settled_targets.json").exists():
            if sim.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError("Isaac startup failed or timed out")
            time.sleep(1)
        if not json.loads((out / "sim/settled_targets.json").read_text())[
            "ok"
        ]:
            raise RuntimeError(
                "Measured target placement does not match episode"
            )
        mission = spawn(
            "mission",
            [
                "ros2",
                "launch",
                "coco_mission",
                "mission.launch.py",
                "simulator:=isaac",
                "rviz:=false",
                "web:=false",
                "use_composition:=False",
                "episode_level:=" + args.level,
                "episode_seed:=" + str(args.seed),
                "target_colour:=" + args.colour,
            ],
        )
        observer = spawn(
            "observer",
            [
                "python3",
                str(repo / "scripts/isaac_fetch_observer.py"),
                str(out),
                "--timeout",
                str(args.timeout),
            ],
        )
        deadline = time.monotonic() + args.timeout + 330
        while observer.poll() is None:
            if (
                sim.poll() is not None
                or mission.poll() is not None
                or time.monotonic() > deadline
            ):
                raise RuntimeError("A required child exited or run timed out")
            time.sleep(1)
        exits["observer"] = observer.returncode
    except BaseException as exc:
        (out / "runner_failure.txt").write_text(repr(exc))
    finally:
        for name, process in reversed(children):
            stop(name, process)
            exits[name] = process.returncode
        for handle in handles:
            handle.close()
        (out / "exits.json").write_text(json.dumps(exits, indent=2))
    result_path = out / "result.json"
    passed = result_path.exists() and json.loads(result_path.read_text()).get(
        "passed"
    )
    return 0 if passed and all(code == 0 for code in exits.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
