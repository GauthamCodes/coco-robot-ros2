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

from coco_perception.candidate_diagnostics import candidates
from coco_perception.target_finder import TargetFinder

import numpy as np

import pytest


def image():
    hsv = np.zeros((30, 30, 3), dtype=np.uint8)
    hsv[0:15, 0:8] = [0, 200, 200]
    hsv[20:25, 20:25] = [0, 200, 200]
    return hsv, np.ones((30, 30), dtype=np.float32)


def test_every_component_stamp_frame_edge_and_depth_geometry():
    hsv, depth = image()
    a = hsv.copy()
    b = depth.copy()
    values = candidates(
        hsv,
        depth,
        'red',
        (400, 400, 15, 15),
        0.15,
        2,
        0.5,
        100,
        'camera_optical_frame',
        1,
        'VALID',
        100,
    )
    assert len(values) == 2
    assert values[0]['accepted'] and values[0]['touches_image_edge']
    assert not values[1]['touches_image_edge']
    assert values[0]['frame'] == 'camera_optical_frame' and values[0]['stamp_ns'] == 100
    assert values[0]['extents_m'] is not None and values[0]['point_count'] > 0
    assert np.array_equal(a, hsv) and np.array_equal(b, depth)


@pytest.mark.parametrize(
    'depth', [None, np.zeros((30, 30)), np.ones((2, 2)), np.full((30, 30), np.nan)]
)
def test_missing_invalid_mismatched_depth_is_explicit(depth):
    hsv, _ = image()
    r = candidates(hsv, depth, 'red', (400, 400, 15, 15), 0.15, 2, 0.5, 1, 'camera')
    assert all(v['reason'] == 'DEPTH_INVALID' and v['centroid'] is None for v in r)


def test_diagnostics_do_not_change_actual_locate_result():
    hsv, depth = image()
    node = object.__new__(TargetFinder)
    node.intrinsics = (400, 400, 15, 15)
    node.min_range = 0.15
    node.max_range = 2.0
    node.width_tolerance = 0.5
    before = node._locate(hsv, depth, 'red')
    candidates(hsv, depth, 'red', node.intrinsics, 0.15, 2.0, 0.5, 1, 'camera')
    assert node._locate(hsv, depth, 'red') == before
