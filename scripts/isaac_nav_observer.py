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

"""Measure a Nav2 action, final pose, and the complete existing command chain."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.time import Time
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose
from lifecycle_msgs.srv import GetState
from tf2_ros import Buffer, TransformListener


def main():
    p = argparse.ArgumentParser()
    p.add_argument('output', type=Path)
    args = p.parse_args()
    rclpy.init()
    node = Node('coco_isaac_nav_test')
    buffer = Buffer()
    _listener = TransformListener(buffer, node)
    counts = Counter()
    nonzero = Counter()
    last = {}
    trace = []
    subscriptions = []
    command_topics = [
        '/cmd_vel_nav',
        '/cmd_vel_smoothed',
        '/cmd_vel',
        '/cmd_vel_gated',
        '/diff_drive_controller/cmd_vel',
    ]

    def cmd(topic, msg):
        counts[topic] += 1
        if abs(msg.twist.linear.x) + abs(msg.twist.angular.z) > 0.001:
            nonzero[topic] += 1

    for topic in command_topics:
        subscriptions.append(
            node.create_subscription(
                TwistStamped, topic, lambda msg, topic=topic: cmd(topic, msg), 10
            )
        )

    def odometry(msg):
        last['odom'] = msg
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if not trace or t - trace[-1]['time_sim_s'] >= 0.2:
            q = msg.pose.pose.orientation
            row = {
                'time_sim_s': t,
                'odom_xy': [msg.pose.pose.position.x, msg.pose.pose.position.y],
                'odom_yaw_rad': math.atan2(
                    2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)
                ),
            }
            try:
                transform = buffer.lookup_transform('map', 'odom', Time()).transform
                q = transform.rotation
                row.update(
                    map_to_odom_xy=[transform.translation.x, transform.translation.y],
                    map_to_odom_yaw_rad=math.atan2(
                        2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)
                    ),
                )
            except Exception:
                pass
            trace.append(row)

    subscriptions.append(
        node.create_subscription(Odometry, '/diff_drive_controller/odom', odometry, 10)
    )
    client = ActionClient(node, NavigateToPose, '/navigate_to_pose')
    start = time.monotonic()
    result = {'passed': False}
    try:

        def wait(predicate, timeout):
            deadline = time.monotonic() + timeout
            while not predicate():
                if time.monotonic() > deadline:
                    raise RuntimeError('Nav2 readiness/action timeout')
                rclpy.spin_once(node, timeout_sec=0.05)

        wait(
            lambda: client.server_is_ready()
            and 'odom' in last
            and buffer.can_transform('map', 'base_footprint', Time()),
            90,
        )
        lifecycle = [
            node.create_client(GetState, name + '/get_state')
            for name in (
                '/bt_navigator',
                '/controller_server',
                '/planner_server',
                '/collision_monitor',
            )
        ]
        active = {}
        deadline = time.monotonic() + 90
        while len(active) < len(lifecycle) or not all(active.values()):
            if time.monotonic() > deadline:
                raise RuntimeError('Nav2 lifecycle nodes did not become active: ' + repr(active))
            for index, service in enumerate(lifecycle):
                if not service.service_is_ready():
                    continue
                state = service.call_async(GetState.Request())
                wait(state.done, 5)
                active[index] = state.result().current_state.id == 3
            for _ in range(10):
                rclpy.spin_once(node, timeout_sec=0.05)
        result['lifecycle_active'] = active
        before = last['odom'].pose.pose.position
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.pose.position.x = 1.5
        goal.pose.pose.position.y = 0.5
        goal.pose.pose.orientation.w = 1.0
        future = client.send_goal_async(goal)
        wait(future.done, 15)
        handle = future.result()
        if not handle.accepted:
            raise RuntimeError('Nav2 rejected goal')
        future = handle.get_result_async()
        wait(future.done, 150)
        action = future.result()
        after = last['odom'].pose.pose.position
        tf = buffer.lookup_transform('map', 'base_footprint', Time())
        error = math.hypot(tf.transform.translation.x - 1.5, tf.transform.translation.y - 0.5)
        owners = [
            e.node_name
            for e in node.get_publishers_info_by_topic('/diff_drive_controller/cmd_vel')
        ]
        result.update(
            status=action.status,
            error_code=action.result.error_code,
            final_error_map_m=error,
            displacement_odom_m=math.hypot(after.x - before.x, after.y - before.y),
            wheel_publishers=owners,
            passed=action.status == 4
            and error < 0.35
            and all(nonzero[t] > 0 for t in command_topics)
            and owners == ['cmd_vel_arbiter'],
        )
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        result.update(
            counts=dict(counts),
            nonzero=dict(nonzero),
            trace=trace,
            elapsed_wall_s=time.monotonic() - start,
        )
        args.output.write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        node.destroy_node()
        rclpy.shutdown()
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
