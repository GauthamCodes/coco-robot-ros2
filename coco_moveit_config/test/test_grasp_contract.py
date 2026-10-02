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

"""Construct the real shared grasp server; invalid perception fails closed."""

from pathlib import Path
import sys

import pytest
import rclpy
from geometry_msgs.msg import PointStamped

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
try:
    from grasp_server import GraspServer, check_target_pose
except ImportError as exc:
    pytest.skip(str(exc), allow_module_level=True)


@pytest.fixture
def server():
    rclpy.init()
    node = GraspServer()
    node._select("red")
    yield node
    node.destroy_node()
    rclpy.shutdown()


def fix(server):
    msg = PointStamped()
    msg.header.frame_id = "base_footprint"
    msg.header.stamp = server.get_clock().now().to_msg()
    msg.point.x, msg.point.y, msg.point.z = 0.149, 0.0, 0.128
    return msg


def test_missing_fix_never_falls_back_to_nominal(server):
    assert server._target_pose() is None


def test_valid_fix_and_colour_change_invalidate_previous_target(server):
    server._on_fix(fix(server))
    assert server._target_pose() == (0.149, 0.0)
    server._select("blue")
    assert server._target_pose() is None


@pytest.mark.parametrize(
    "fault", ["frame", "nan", "future", "stale", "height"]
)
def test_invalid_fix_clears_previous_valid_fix(server, fault):
    msg = fix(server)
    server._on_fix(msg)
    if fault == "frame":
        msg.header.frame_id = "camera_optical_frame"
    elif fault == "nan":
        msg.point.x = float("nan")
    elif fault == "future":
        msg.header.stamp.sec += 10
    elif fault == "stale":
        msg.header.stamp.sec -= 121
    else:
        msg.point.z = 4.0
    server._on_fix(msg)
    assert server._target_pose() is None


def test_nonfinite_y_cannot_pass_the_grasp_window():
    assert check_target_pose("red", 0.149, float("nan")) is not None


def test_unavailable_lift_and_release_measurements_fail(server, monkeypatch):
    monkeypatch.setattr(server, "target_height", lambda: None)
    server._grasp_z = None
    assert not server.grasp_magnet()
    assert not server.check_lifted()
    assert not server.check_released()


@pytest.mark.parametrize('simulator', ['gazebo', 'isaac'])
def test_nonfinite_height_cannot_verify_a_grasp(server, monkeypatch, simulator):
    import time
    import arm_control

    server.simulator = simulator
    monkeypatch.setattr(arm_control, 'model_z', lambda _: float('nan'))
    server._heights[server.magnet_model] = (float('nan'), time.monotonic())
    assert server.target_height() is None
