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

"""Stop only process groups created by a COCO runner, including orphan children."""

import os
from pathlib import Path
import signal
import subprocess
import time


def group_alive(pgid):
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != "Z":
                return True
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    return False


def stop(name, process):
    """Allow launch/Isaac graceful shutdown, then reap surviving group members."""
    pgid = process.pid  # Popen(start_new_session=True), recorded at creation.
    if process.poll() is None:
        try:
            if name in ("nav2", "mission"):
                process.send_signal(
                    signal.SIGINT
                )  # launch forwards to children
            else:
                os.killpg(pgid, signal.SIGINT)
            process.wait(timeout=45)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            pass
    # An exited ros2 launch may leave nodes alive after a launch exception.
    for sig, grace in ((signal.SIGTERM, 5), (signal.SIGKILL, 2)):
        if not group_alive(pgid):
            break
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            break
        deadline = time.monotonic() + grace
        while group_alive(pgid) and time.monotonic() < deadline:
            time.sleep(0.1)
    if process.poll() is None:
        process.wait(timeout=5)
    if group_alive(pgid):
        raise RuntimeError(
            f"{name}: owned process group {pgid} survived shutdown"
        )
