#!/usr/bin/env python3
# Copyright 2026 Gautham Anil
# SPDX-License-Identifier: Apache-2.0
"""Read-only world poses for matched-fetch physical evidence."""
import json
from pathlib import Path
import signal
import subprocess
import sys


def main():
    child = subprocess.Popen(
        ["gz", "topic", "--json-output", "-e", "-t", "/world/coco_world/pose/info"],
        stdout=subprocess.PIPE, text=True)
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        del signum, frame
        stopped = True
        if child.poll() is None:
            child.send_signal(signal.SIGINT)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        with Path(sys.argv[1]).open('w') as output:
            for line in child.stdout:
                if stopped:
                    break
                try:
                    data = json.loads(line)
                except ValueError:
                    continue
                poses = [p for p in data.get('pose', [])
                         if p.get('name') in ('coco', 'target_red', 'target_green',
                                              'target_blue', 'target_yellow',
                                              'm_link3', 'coco::m_link3')]
                if poses:
                    output.write(json.dumps({'header': data.get('header'),
                                             'pose': poses}) + '\n')
                    output.flush()
    finally:
        stop(None, None)
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
