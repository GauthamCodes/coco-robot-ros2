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

"""Own exactly one Isaac and ROS peer process; archive logs and exit evidence."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('output', type=Path)
    p.add_argument('--domain', type=int, default=78)
    p.add_argument('--gui', action='store_true')
    p.add_argument('--rviz', action='store_true')
    p.add_argument('--nav', action='store_true')
    p.add_argument(
        '--nav-composed',
        action='store_true',
        help='reproduce composed navigation; known shutdown failure',
    )
    p.add_argument('--raw-evidence', type=Path)
    args = p.parse_args()
    if args.nav:
        if not args.raw_evidence or not json.loads(args.raw_evidence.read_text()).get('passed'):
            p.error('--nav requires --raw-evidence from a passing smoke run')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[1]
    env = dict(os.environ, ROS_DOMAIN_ID=str(args.domain))
    handles, processes = [], []
    rc = {}
    gpu = []
    start = time.monotonic()

    def spawn(name, command):
        handle = (out / (name + '.log')).open('w')
        handles.append(handle)
        process = subprocess.Popen(
            command,
            cwd=repo,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        processes.append((name, process))
        return process

    def stop(name, process):
        if process.poll() is None:
            if name == 'nav2':
                # Launch forwards shutdown to its children; avoid double signalling.
                process.send_signal(signal.SIGINT)
            else:
                os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)

    try:
        isaac = spawn(
            'launch',
            [
                '/usr/bin/time',
                '-v',
                '-o',
                str(out / 'resources.txt'),
                'bash',
                str(repo / 'scripts/isaac_sim_coco.sh'),
                '--output',
                str(out / 'sim'),
                *(['--gui'] if args.gui else []),
            ],
        )
        deadline = time.monotonic() + 1200  # allow cold shader compilation
        while not (out / 'sim/ready.marker').exists():
            if isaac.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('Isaac exited or initialization timed out')
            time.sleep(1)
        wanted = (
            'ROS_DISTRO',
            'RMW_IMPLEMENTATION',
            'ROS_DOMAIN_ID',
            'CYCLONEDDS_URI',
            'AMENT_PREFIX_PATH',
            'COLCON_PREFIX_PATH',
            'PYTHONPATH',
            'LD_LIBRARY_PATH',
        )
        environment = {'jazzy_runner': {k: env.get(k, '<unset>') for k in wanted}}
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():
                continue
            try:
                command = (proc / 'cmdline').read_bytes().split(b'\0')
                if (
                    b'coco_sim.isaac.runtime' not in command
                    or str(out / 'sim').encode() not in command
                ):
                    continue
                values = dict(
                    x.split(b'=', 1)
                    for x in (proc / 'environ').read_bytes().split(b'\0')
                    if b'=' in x
                )
                environment['isaac_process'] = {
                    k: values.get(k.encode(), b'<unset>').decode() for k in wanted
                }
            except (FileNotFoundError, PermissionError):
                continue
        (out / 'environment.json').write_text(json.dumps(environment, indent=2))
        spawn(
            'ros_peer',
            [
                'python3',
                str(repo / 'scripts/isaac_ros.py'),
                '--ros-args',
                '-p',
                'use_sim_time:=true',
                '-p',
                'initial_mode:=' + ('nav' if args.nav else 'idle'),
            ],
        )
        if args.rviz:
            rviz = spawn(
                'rviz',
                [
                    '/opt/ros/jazzy/lib/rviz2/rviz2',
                    '-d',
                    str(repo / 'coco_sim/rviz/isaac.rviz'),
                    '--ros-args',
                    '-p',
                    'use_sim_time:=true',
                ],
            )
        if args.nav:
            from isaac_fixture_map import write_map

            write_map(out / 'map')
            # Pin only the fixture filename in a run-local copy: the installed
            # noncomposed launch retained map.yaml despite its map argument.
            import yaml

            params = yaml.safe_load((repo / 'gazebo_models/config/nav2_params.yaml').read_text())
            params['map_server']['ros__parameters']['yaml_filename'] = str(
                out / 'map/fixture.yaml'
            )
            (out / 'nav2_params.yaml').write_text(yaml.safe_dump(params))
            spawn(
                'nav2',
                [
                    'ros2',
                    'launch',
                    'gazebo_models',
                    'nav.launch.py',
                    'arbiter:=true',
                    'use_composition:=' + ('True' if args.nav_composed else 'False'),
                    'params_file:=' + str(out / 'nav2_params.yaml'),
                    'map:=' + str(out / 'map/fixture.yaml'),
                ],
            )
        observer_script = 'isaac_nav_observer.py' if args.nav else 'isaac_smoke_observer.py'
        observer = spawn(
            'observer',
            ['python3', str(repo / 'scripts' / observer_script), str(out / 'result.json')],
        )
        deadline = time.monotonic() + 300
        capture_after = time.monotonic() + 8
        while observer.poll() is None:
            if isaac.poll() is not None:
                raise RuntimeError('Isaac exited during smoke test')
            if time.monotonic() > deadline:
                raise RuntimeError('Observer timeout')
            if args.rviz and time.monotonic() > capture_after and not (out / 'rviz.png').exists():
                try:
                    from PIL import Image
                    import struct
                    import numpy as np

                    windows = subprocess.check_output(
                        ['xdotool', 'search', '--onlyvisible', '--pid', str(rviz.pid)], text=True
                    ).split()
                    for window in windows:
                        geometry = dict(
                            line.split('=', 1)
                            for line in subprocess.check_output(
                                ['xdotool', 'getwindowgeometry', '--shell', window], text=True
                            ).splitlines()
                        )
                        x, y, width, height = (
                            int(geometry[k]) for k in ('X', 'Y', 'WIDTH', 'HEIGHT')
                        )
                        if width > 600 and height > 400:
                            raw = subprocess.check_output(['xwd', '-silent', '-id', window])
                            header = struct.unpack('>25I', raw[:100])
                            width, height, order, bpp, stride = (
                                header[i] for i in (4, 5, 7, 11, 12)
                            )
                            if bpp != 32:
                                raise RuntimeError('Unsupported XWD pixel layout')
                            offset = header[0] + 12 * header[19]
                            pixels = np.frombuffer(
                                raw[offset:], dtype='<u4' if order == 0 else '>u4'
                            )
                            pixels = pixels.reshape(height, stride // 4)[:, :width]
                            rgb = []
                            for mask in header[14:17]:
                                shift = (mask & -mask).bit_length() - 1
                                rgb.append(((pixels & mask) >> shift).astype(np.uint8))
                            Image.fromarray(np.stack(rgb, axis=-1)).save(out / 'rviz.png')
                            break
                except Exception as exc:
                    (out / 'capture_error.txt').write_text(repr(exc))
                capture_after = time.monotonic() + 5
            sample = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
            )
            gpu.append(
                {
                    'elapsed_wall_s': time.monotonic() - start,
                    'total_gpu_used_mib': sample.stdout.strip(),
                }
            )
            time.sleep(1)
        rc['observer'] = observer.returncode
    finally:
        # Stop producers before RViz destroys image/render subscriptions.
        order = {'observer': 0, 'nav2': 1, 'ros_peer': 2, 'launch': 3, 'rviz': 4}
        for name, process in sorted(processes, key=lambda item: order[item[0]]):
            stop(name, process)
            rc[name] = process.returncode
        for handle in handles:
            handle.close()
        (out / 'process_exit.json').write_text(json.dumps(rc, indent=2))
        (out / 'gpu.json').write_text(json.dumps(gpu, indent=2))
    result = json.loads((out / 'result.json').read_text())
    clean = (out / 'sim/shutdown_requested.json').exists() and not (
        out / 'sim/failure.txt'
    ).exists()
    result['clean_shutdown'] = clean and rc['launch'] == 0
    result['behavior_passed'] = result['passed']
    child_failures = []
    if args.nav:
        import re

        child_failures = re.findall(
            r'process has died.*exit code (-?\d+)', (out / 'nav2.log').read_text()
        )
    result['child_exit_failures'] = child_failures
    result['auxiliary_clean_shutdown'] = (
        all(value == 0 for value in rc.values()) and not child_failures
    )
    result['passed'] &= result['clean_shutdown'] and result['auxiliary_clean_shutdown']
    (out / 'result.json').write_text(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
