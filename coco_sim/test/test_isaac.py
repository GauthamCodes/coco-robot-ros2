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

"""Guard physical provenance, drive semantics and startup order."""
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from coco_config import robot as r
from coco_sim.isaac.config import DriveCommand, wheel_layout, wheel_speeds
from coco_sim.isaac.model import robot_description


def test_generated_geometry_tracks_authority(monkeypatch):
    monkeypatch.setattr(r, "WHEEL_RADIUS", 0.071)
    monkeypatch.setattr(r, "WHEELBASE", 0.22)
    monkeypatch.setattr(r, "CHASSIS_SIZE", (0.3, 0.28, 0.07))
    root = ET.fromstring(robot_description())
    assert (
        root.find(".//link[@name='wheel1']/visual/geometry/cylinder").get(
            "radius"
        )
        == "0.071"
    )
    assert (
        root.find(".//joint[@name='wheel1_joint']/origin")
        .get("xyz")
        .split()[0]
        == "0.11"
    )
    assert (
        root.find(".//link[@name='base_link']/visual/geometry/box").get("size")
        == "0.3 0.28 0.07"
    )


def test_forward_and_positive_yaw_wheel_signs():
    assert wheel_speeds(0.5, 0) == pytest.approx([0.5 / r.WHEEL_RADIUS] * 4)
    spin = wheel_speeds(0, 0.5)
    assert spin[0] == spin[1] > 0
    assert spin[2] == spin[3] < 0
    assert spin[0] == pytest.approx(-spin[2])


def test_timeout_and_future_stamp_fail_closed():
    command = DriveCommand()
    command.receive(0.5, 0.0, 3.0)
    assert any(command.step(3.1, 0.1))
    assert command.step(3.501, 0.1) == [0.0] * 4
    command.receive(0.5, 0.0, 5.0)
    assert command.step(4.0, 0.1) == [0.0] * 4


def test_acceleration_and_nonfinite_input():
    command = DriveCommand()
    command.receive(0.5, 0.5, 0.0)
    command.step(0.1, 0.1)
    assert command.velocity == pytest.approx(
        (r.MAX_LINEAR_ACCEL * 0.1, r.MAX_ANGULAR_ACCEL * 0.1)
    )
    command.receive(float("nan"), 0, 0.1)
    assert command.stamp == 0.0


def test_minimal_tree_has_single_parent_and_correct_optical_rotation():
    root = ET.fromstring(robot_description())
    children = [j.find("child").get("link") for j in root.findall("joint")]
    assert len(children) == len(set(children))
    assert "base_footprint" not in children
    joint = root.find(".//joint[@name='camera_optical_joint']")
    assert list(
        map(float, joint.find("origin").get("rpy").split())
    ) == pytest.approx([-math.pi / 2, 0, -math.pi / 2])
    assert len(wheel_layout()) == 4


def test_runtime_never_teleports_body_and_scene_precedes_bridge():
    source = (
        Path(__file__).parents[1] / "coco_sim/isaac/runtime.py"
    ).read_text()
    assert source.index("build_scene(ctx.get_stage()") < source.index(
        "em.set_extension_enabled_immediate("
    )
    for forbidden in (
        "set_linear_velocity(",
        "set_angular_velocity(",
        "set_world_pose(",
    ):
        assert forbidden not in source
    assert "joint_velocities=" in source


def test_controller_velocity_and_timeout_match_existing_yaml():
    import yaml
    from coco_sim.isaac import config

    path = (
        Path(__file__).parents[2] / "gazebo_models/urdf/coco_controllers.yaml"
    )
    params = yaml.safe_load(path.read_text())["diff_drive_controller"][
        "ros__parameters"
    ]
    assert config.MAX_LINEAR == params["linear.x.max_velocity"]
    assert config.MAX_ANGULAR == params["angular.z.max_velocity"]
    assert config.COMMAND_TIMEOUT == params["cmd_vel_timeout"]
