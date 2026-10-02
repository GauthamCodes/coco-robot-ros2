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

"""Manipulation boundary guards: measured geometry, bad commands and grasp gaps."""

from pathlib import Path
import sys

import numpy as np
import pytest

from coco_config.joint_limits import ARM_LIMITS
from coco_sim.isaac.articulated import arm_transforms
from coco_sim.isaac.control import Trajectory, valid_positions
from coco_sim.isaac.grasp import can_attach, pinch_local

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def description():
    import xacro

    return xacro.process_file(
        str(ROOT / "gazebo_models/urdf/coco_robo2.xacro")
    ).toxml()


def test_urdf_fk_tracks_the_shared_analytic_ik(description):
    sys.path.insert(0, str(ROOT / "coco_moveit_config/scripts"))
    import arm_ik

    # The analytic reference is the closed fingertip pinch, not the lip centre.
    # Derive its fixed palm-frame point at zero; compare across the workspace.
    zero = arm_transforms(description)["m_link3"]
    x, z = arm_ik.fk(0, 0)
    local = np.linalg.inv(zero) @ [x, 0, z - 0.0135, 1]
    for q1, q2 in [(0.3, 0.58), (-1.2, -0.5), (0.1, 0.45), (0, 0)]:
        frame = arm_transforms(
            description, dict(zip(tuple(ARM_LIMITS)[:2], (q1, q2)))
        )["m_link3"]
        actual = frame @ local
        expected = arm_ik.fk(q1, q2)
        assert (actual[0], actual[2] + 0.0135) == pytest.approx(
            expected, abs=2e-6
        )
    assert np.linalg.norm(pinch_local(description) - local[:3]) < 0.02


@pytest.mark.parametrize(
    "names,positions",
    [
        (["m_link1_Revolute-6"], [float("nan")]),
        (["m_link1_Revolute-6"], [float("inf")]),
        (["m_link1_Revolute-6"], [1.01]),
        (["base_Revolute-1"], [0]),
        (["m_link1_Revolute-6"] * 2, [0, 0]),
        (["m_link1_Revolute-6"], []),
    ],
)
def test_manipulator_command_rejects_invalid_and_wheel_joints(
    names, positions
):
    assert not valid_positions(names, positions)


def test_trajectory_interpolates_and_holds_end():
    trajectory = Trajectory(
        ["m_link1_Revolute-6"], [(1, [0.2]), (2, [0.4])], [0]
    )
    assert trajectory.sample(0.5) == pytest.approx([0.1])
    assert trajectory.sample(1.5) == pytest.approx([0.3])
    assert trajectory.sample(5) == pytest.approx([0.4])


@pytest.mark.parametrize(
    "points",
    [
        [(1, [0]), (1, [0.2])],
        [(float("nan"), [0])],
        [(-1, [0])],
        [(1, [2])],
        [],
    ],
)
def test_invalid_trajectory_is_rejected(points):
    with pytest.raises(ValueError):
        Trajectory(["m_link1_Revolute-6"], points, [0])


def test_magnet_cannot_attach_at_a_distance_or_outside_target_band():
    target = (4.05, -0.75, 0.729)
    assert can_attach((4.05, -0.75, 0.778), target, 0.01, 0.158)
    assert not can_attach((4.05, -0.25, 0.778), target, 0.01, 0.158)
    assert not can_attach((4.05, -0.75, 0.9), target, 0.01, 0.158)
    assert not can_attach((float("nan"), -0.75, 0.778), target, 0.01, 0.158)
