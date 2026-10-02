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

"""A failed launcher must not leave an extra wheel-command publisher alive."""

import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "process_groups", ROOT / "scripts/process_groups.py"
)
groups = importlib.util.module_from_spec(spec)
spec.loader.exec_module(groups)


def test_shutdown_reaps_orphan_of_an_already_exited_launcher(tmp_path):
    marker = tmp_path / "child_pid"
    code = (
        "import subprocess, pathlib; p = subprocess.Popen(['"
        + sys.executable
        + "', '-c', 'import time; time.sleep(120)']); "
        + "pathlib.Path("
        + repr(str(marker))
        + ").write_text(str(p.pid))"
    )
    parent = subprocess.Popen(
        [sys.executable, "-c", code], start_new_session=True
    )
    try:
        parent.wait(timeout=5)
        assert marker.exists()
        assert groups.group_alive(parent.pid)
        groups.stop("mission", parent)
        assert not groups.group_alive(parent.pid)
    finally:
        groups.stop("mission", parent)
