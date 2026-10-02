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

"""The ROS controller must finish from measured feedback and stop on loss."""
import time
from types import SimpleNamespace

import pytest
import rclpy
from rclpy.action import GoalResponse
from rclpy.task import Future
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from coco_config.joint_limits import ARM_LIMITS
from coco_sim.isaac.trajectory_node import Controller


@pytest.fixture
def controller():
    rclpy.init()
    node = Controller()
    msg = JointState()
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.name = list(ARM_LIMITS)
    msg.position = [0.0] * 4
    node.feedback(msg)
    yield node
    node.destroy_node()
    rclpy.shutdown()


def goal():
    trajectory = JointTrajectory()
    trajectory.joint_names = list(ARM_LIMITS)[:2]
    point = JointTrajectoryPoint()
    point.positions = [0.2, 0.1]
    point.time_from_start.sec = 1
    trajectory.points = [point]
    return SimpleNamespace(trajectory=trajectory)


def test_rejects_stale_feedback_wheels_and_overlapping_goals(controller):
    request = goal()
    controller.feedback_wall -= 3
    assert controller.accept(request) == GoalResponse.REJECT
    controller.feedback_wall = time.monotonic()
    request.trajectory.joint_names[0] = "base_Revolute-1"
    assert controller.accept(request) == GoalResponse.REJECT
    assert controller.accept(goal()) == GoalResponse.ACCEPT
    assert controller.accept(goal()) == GoalResponse.REJECT


@pytest.mark.parametrize("case", ["arrived", "stale", "cancel", "late"])
def test_completion_and_abort_use_measurements(controller, case):
    request = goal()
    trajectory = controller.trajectory(
        request.trajectory, tuple(ARM_LIMITS)[:2]
    )
    outcome = []
    handle = SimpleNamespace(
        is_cancel_requested=case == "cancel",
        succeed=lambda: outcome.append("success"),
        abort=lambda: outcome.append("abort"),
        canceled=lambda: outcome.append("cancel"),
    )
    finished = Future()
    elapsed = 4 if case == "late" else 1.1
    controller.active = (
        handle,
        trajectory,
        controller.now() - elapsed,
        time.monotonic(),
        finished,
    )
    if case == "arrived":
        controller.measured.update(zip(trajectory.names, [0.2, 0.1]))
    if case == "stale":
        controller.feedback_wall -= 3
    controller.tick()
    assert outcome == [
        {
            "arrived": "success",
            "stale": "abort",
            "cancel": "cancel",
            "late": "abort",
        }[case]
    ]
    assert finished.done()
    assert controller.active is None
    assert (finished.result()[0] == 0) == (case == "arrived")
