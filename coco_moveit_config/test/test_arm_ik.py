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

"""Analytic IK: FK/IK round-trips, limits, and the verified grasp pose."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import arm_ik  # noqa: E402


def test_fk_matches_verified_grasp():
    # The pedestal-top pinch point pick_place.py was verified at in sim
    x, z = arm_ik.fk(0.30, 0.58)
    assert math.hypot(x - 0.152, z - 0.128) < 0.002


def test_ik_recovers_verified_grasp():
    sols = arm_ik.ik(0.152, 0.128)
    assert sols, 'verified grasp point must be reachable'
    q1, q2 = sols[0]
    assert abs(q1 - 0.30) < 0.02 and abs(q2 - 0.58) < 0.02


def test_round_trip_over_workspace():
    random.seed(42)
    for _ in range(2000):
        q1 = random.uniform(*arm_ik.SHOULDER_LIMITS)
        q2 = random.uniform(*arm_ik.ELBOW_LIMITS)
        x, z = arm_ik.fk(q1, q2)
        sols = arm_ik.ik(x, z)
        assert sols, f'fk({q1}, {q2}) -> ({x}, {z}) not recovered'
        err = min(math.hypot(s1 - q1, s2 - q2) for s1, s2 in sols)
        assert err < 1e-9


def test_solutions_respect_joint_limits():
    random.seed(7)
    for _ in range(500):
        x = random.uniform(-0.3, 0.3)
        z = random.uniform(0.0, 0.4)
        for q1, q2 in arm_ik.ik(x, z):
            assert arm_ik.SHOULDER_LIMITS[0] <= q1 <= arm_ik.SHOULDER_LIMITS[1]
            assert arm_ik.ELBOW_LIMITS[0] <= q2 <= arm_ik.ELBOW_LIMITS[1]


def test_unreachable_returns_empty():
    assert arm_ik.ik(1.0, 1.0) == []
    assert arm_ik.ik_or_none(1.0, 1.0) is None


def test_place_clearance_preserves_weld_orientation_and_height():
    for x in (.145, .152, .156):
        grasp = arm_ik.ik_or_none(x, .128)
        place = arm_ik.place_clearance_pose(grasp, .015)
        assert place is not None
        assert abs(arm_ik.fk(*place)[1] - .143) < 1e-9
        assert abs((place[1] - place[0]) - (grasp[1] - grasp[0])) < 1e-9
        assert arm_ik.SHOULDER_LIMITS[0] <= place[0] <= arm_ik.SHOULDER_LIMITS[1]
        assert arm_ik.ELBOW_LIMITS[0] <= place[1] <= arm_ik.ELBOW_LIMITS[1]


def test_place_clearance_rejects_unreachable_or_invalid_motion():
    grasp = arm_ik.ik_or_none(.152, .128)
    assert arm_ik.place_clearance_pose(grasp, 5.) is None
    assert arm_ik.place_clearance_pose(grasp, -.01) is None
    assert arm_ik.place_clearance_pose((float('nan'), 0), .015) is None
    assert arm_ik.place_clearance_pose((0, 9), .015) is None
