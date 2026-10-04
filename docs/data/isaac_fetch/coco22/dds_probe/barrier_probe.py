"""ROS-only diagnostic: hold every ready participant until the parent releases it.

Source setup_env.sh first. No mission, simulator or velocity publishers run.
The output directory must be new; children are owned by this diagnostic.
"""
import argparse
import json
import os
from pathlib import Path
import selectors
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
parser.add_argument('--domain', type=int, default=89)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
code = ("import rclpy,sys;rclpy.init();n=rclpy.create_node('fetch_dds_barrier_probe');"
        "print('READY',flush=True);sys.stdin.readline();n.destroy_node();rclpy.shutdown()")
for mode in ('baseline', 'expanded'):
    env = dict(os.environ, ROS_DOMAIN_ID=str(args.domain))
    if mode == 'expanded':
        env['CYCLONEDDS_URI'] = (
            '<CycloneDDS><Domain><General><Interfaces>'
            '<NetworkInterface name="lo" multicast="true"/></Interfaces></General>'
            '<Discovery><ParticipantIndex>auto</ParticipantIndex>'
            '<MaxAutoParticipantIndex>119</MaxAutoParticipantIndex>'
            '</Discovery></Domain></CycloneDDS>')
    children = [subprocess.Popen(
        ['python3', '-c', code], env=env, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) for _ in range(40)]
    ready, ended, outputs = set(), set(), [''] * 40
    selector = selectors.DefaultSelector()
    for i, child in enumerate(children):
        selector.register(child.stdout, selectors.EVENT_READ, i)
    deadline = time.monotonic() + 40
    while len(ready | ended) < 40 and time.monotonic() < deadline:
        for key, _ in selector.select(.2):
            i = key.data
            line = key.fileobj.readline()
            outputs[i] += line
            if line.strip() == 'READY':
                ready.add(i)
            if not line:
                ended.add(i)
                selector.unregister(key.fileobj)
        ended.update(i for i, child in enumerate(children) if child.poll() is not None)
    peak = sum(children[i].poll() is None for i in ready)
    for child in children:
        if child.poll() is None:
            try:
                child.stdin.write('\n')
                child.stdin.flush()
            except BrokenPipeError:
                pass
    for i, child in enumerate(children):
        try:
            output, _ = child.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            child.kill()
            output, _ = child.communicate()
        outputs[i] += output
    result = dict(mode=mode, processes=40, simultaneously_ready=peak,
                  exit_codes=[child.returncode for child in children],
                  cyclonedds_uri=env['CYCLONEDDS_URI'])
    (args.output / (mode + '_barrier.json')).write_text(json.dumps(result, indent=2) + '\n')
    (args.output / (mode + '_barrier.log')).write_text('\n'.join(outputs))
    print(mode, peak, flush=True)
