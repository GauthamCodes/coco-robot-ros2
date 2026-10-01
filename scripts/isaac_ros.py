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

"""ROS-side adapter: plain Twist to the existing arbiter's teleop input.

Nav2's stamped /cmd_vel uses the existing cmd_vel_relay instead.
The backend only ever consumes the arbiter's final TwistStamped output.
"""
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped
from custom_teleop.cmd_vel_arbiter import CmdVelArbiter


class TwistInput(Node):
    """Provide a plain Twist smoke/teleop entry without bypassing arbitration."""

    def __init__(self):
        super().__init__('coco_isaac_twist_input')
        self.declare_parameter('input_topic', '/cmd_vel')
        self.declare_parameter('output_topic', '/cmd_vel_teleop')
        self.pub = self.create_publisher(
            TwistStamped, self.get_parameter('output_topic').value, 10
        )
        self.sub = self.create_subscription(
            Twist, self.get_parameter('input_topic').value, self.receive, 10
        )

    def receive(self, msg):
        stamped = TwistStamped()
        stamped.header.stamp = self.get_clock().now().to_msg()
        stamped.header.frame_id = 'base_footprint'
        stamped.twist = msg
        self.pub.publish(stamped)


def main():
    rclpy.init()
    executor = SingleThreadedExecutor()
    nodes = [TwistInput(), CmdVelArbiter()]
    for node in nodes:
        executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        for node in nodes:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
