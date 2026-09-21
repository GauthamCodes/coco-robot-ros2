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

"""Cross-language wire fixtures and deterministic frontend lifecycle tests."""

import base64
import json
import os
from pathlib import Path
import subprocess

from coco_web import binary


def test_node_transport_with_python_wire_fixtures(tmp_path):
    """Run the standalone module against actual Python-encoded bytes."""
    valid = {
        'lidar': binary.lidar_frame(7, 12.5, {'ranges': [1.234, None, 2.0]}),
        'camera': binary.image_frame('camera', 7, 12.5, 8, 8, b'jpeg'),
        'depth': binary.image_frame('depth', 7, 12.5, 8, 8, b'jpeg',
                                    extra={'min_m': 0.1, 'max_m': 8}),
    }
    invalid = [b'', b'COCO', valid['camera'][:-1], valid['depth'] + b'x',
               valid['lidar'][:-2]]
    wrong_kind = bytearray(valid['camera'])
    wrong_kind[5] = 99
    invalid.append(bytes(wrong_kind))
    encode = lambda blob: base64.b64encode(blob).decode('ascii')  # noqa: E731
    path = tmp_path / 'frames.json'
    path.write_text(json.dumps({
        'valid': {key: encode(value) for key, value in valid.items()},
        'invalid': [encode(value) for value in invalid],
    }))
    script = Path(__file__).resolve().parents[1] / 'transport/client.test.mjs'
    result = subprocess.run(
        ['node', '--test', str(script)], capture_output=True, text=True,
        env={**os.environ, 'COCO_FRAME_FIXTURES': str(path)}, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
