#!/usr/bin/env python3
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

"""MoveIt FollowJointTrajectory contract for the Isaac position drives.

This is a controller adapter, not a mission. Completion requires fresh measured
joint feedback. The bundled Humble bridge lacks control_msgs, so actions remain
on Jazzy and only validated JointState commands cross the process boundary.
"""
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from coco_config.ros_boundary import AutonomyNode as Node
from rclpy.task import Future
from control_msgs.action import FollowJointTrajectory
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory

from coco_config.joint_limits import ARM_LIMITS
from coco_sim.isaac.control import Trajectory


class Controller(Node):
    def __init__(self):
        super().__init__("coco_isaac_trajectory")
        self.measured = {}
        self.feedback_at = -1e9
        self.feedback_wall = -1e9
        self.active = None
        self.pending = False
        self.gripper = None
        self.command = self.create_publisher(
            JointState, "/isaac/manipulator_command", 10
        )
        self.create_subscription(
            JointState, "/joint_states", self.feedback, 10
        )
        self.create_subscription(
            JointTrajectory,
            "/gripper_controller/joint_trajectory",
            self.grip,
            10,
        )
        self.server = ActionServer(
            self,
            FollowJointTrajectory,
            "/arm_controller/follow_joint_trajectory",
            self.execute,
            goal_callback=self.accept,
            cancel_callback=lambda _: CancelResponse.ACCEPT,
        )
        self.create_timer(1 / 30, self.tick)

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def feedback(self, msg):
        self.measured.update(zip(msg.name, msg.position))
        self.feedback_at = (
            msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        )
        self.feedback_wall = time.monotonic()

    def fresh(self):
        return (
            0 <= self.now() - self.feedback_at <= 0.5
            and time.monotonic() - self.feedback_wall <= 2
        )

    def trajectory(self, msg, allowed):
        if set(msg.joint_names) != set(allowed) or not self.fresh():
            raise ValueError("Wrong joint set or stale measured feedback")
        if msg.header.stamp.sec or msg.header.stamp.nanosec:
            # No silent reinterpretation of scheduled trajectories.
            raise ValueError("Only immediate trajectories are supported")
        return Trajectory(
            msg.joint_names,
            [
                (
                    p.time_from_start.sec + p.time_from_start.nanosec * 1e-9,
                    p.positions,
                )
                for p in msg.points
            ],
            [self.measured[n] for n in msg.joint_names],
        )

    def accept(self, goal):
        if self.pending or self.active is not None:
            return GoalResponse.REJECT
        try:
            self.trajectory(goal.trajectory, tuple(ARM_LIMITS)[:2])
        except (ValueError, KeyError):
            return GoalResponse.REJECT
        self.pending = True
        return GoalResponse.ACCEPT

    async def execute(self, handle):
        self.pending = False
        result = FollowJointTrajectory.Result()
        try:
            trajectory = self.trajectory(
                handle.request.trajectory, tuple(ARM_LIMITS)[:2]
            )
        except (ValueError, KeyError) as exc:
            handle.abort()
            result.error_code = result.INVALID_GOAL
            result.error_string = str(exc)
            return result
        finished = Future()
        self.active = (
            handle,
            trajectory,
            self.now(),
            time.monotonic(),
            finished,
        )
        code, reason = await finished
        result.error_code, result.error_string = code, reason
        return result

    def grip(self, msg):
        try:
            self.gripper = (
                self.trajectory(msg, tuple(ARM_LIMITS)[2:]),
                self.now(),
            )
        except (ValueError, KeyError) as exc:
            self.get_logger().error(f"Rejected gripper command: {exc}")

    def publish(self, names, positions):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name, msg.position = list(names), list(positions)
        self.command.publish(msg)

    def tick(self):
        if self.gripper:
            trajectory, start = self.gripper
            if self.fresh():
                self.publish(
                    trajectory.names, trajectory.sample(self.now() - start)
                )
            if self.now() - start >= trajectory.duration:
                self.gripper = None
        if self.active is None:
            return
        handle, trajectory, start, wall, finished = self.active
        elapsed = self.now() - start
        reason = None
        if handle.is_cancel_requested:
            handle.canceled()
            reason = (-4, "Canceled; hold measured position")
        elif not self.fresh() or time.monotonic() - wall > 120 or elapsed < 0:
            handle.abort()
            reason = (-4, "Lost feedback, clock reset, or wall timeout")
        elif elapsed > trajectory.duration + 2:
            handle.abort()
            reason = (
                -5,
                "Measured joints did not reach goal within tolerance",
            )
        else:
            self.publish(trajectory.names, trajectory.sample(elapsed))
            if elapsed >= trajectory.duration and all(
                abs(self.measured[n] - p) < 0.01
                for n, p in zip(trajectory.names, trajectory.sample(elapsed))
            ):
                handle.succeed()
                reason = (0, "")
        if reason:
            if self.fresh():
                self.publish(
                    trajectory.names,
                    [self.measured[n] for n in trajectory.names],
                )
            self.active = None
            finished.set_result(reason)


def main():
    rclpy.init()
    node = Controller()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
