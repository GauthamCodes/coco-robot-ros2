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

"""Bounded live ROS/WebSocket smoke with synthetic sensors on an isolated graph.

Requires ROS_DOMAIN_ID explicitly; does not launch a simulator or an arbiter.
A recorder observes teleop intents only in that domain. No wheel publisher is
created. Run after sourcing the private validation overlay.
"""

import asyncio
from collections import Counter, deque
import json
import math
import os
import threading
import time

from coco_web import binary
from coco_web.platform_server import CocoWebNode, Platform, make_app

from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Image, LaserScan
from std_msgs.msg import String
from tornado.ioloop import PeriodicCallback
from tornado.websocket import websocket_connect


async def main():
    """Run one bounded smoke and always shut down resources it owns."""
    assert int(os.environ['ROS_DOMAIN_ID']) > 0, 'choose an isolated ROS domain'
    rclpy.init(args=['--ros-args', '-p',
                    'depth_topic:=/camera/depth/image_raw'])
    node = CocoWebNode()
    fixture = Node('p02_synthetic_sensor_fixture')
    executor = SingleThreadedExecutor()
    server = socket = ticker = thread = None
    report = {'source': 'synthetic ROS sensors; no simulator or hardware',
              'ros_domain_id': os.environ['ROS_DOMAIN_ID']}
    received = Counter()
    commands = deque(maxlen=100)
    try:
        executor.add_node(node)
        executor.add_node(fixture)
        odom = Odometry()
        odom.pose.pose.orientation.w = 1.0
        scan = LaserScan()
        scan.angle_min = -math.radians(120)
        scan.angle_max = math.radians(120)
        scan.angle_increment = (scan.angle_max - scan.angle_min) / 479
        scan.range_min, scan.range_max = 0.15, 12.0
        scan.ranges = [1.234] * 480
        camera = Image()
        camera.width, camera.height = 320, 240
        camera.encoding, camera.step = 'rgb8', 960
        camera.data = bytes([255, 0, 0]) * (320 * 240)
        depth = Image()
        depth.width, depth.height = 320, 240
        depth.encoding, depth.step = '32FC1', 1280
        depth.data = np.full((240, 320), 2.0, dtype='<f4').tobytes()
        publishers = [
            (fixture.create_publisher(Odometry, '/diff_drive_controller/odom', 10),
             odom),
            (fixture.create_publisher(Odometry, '/model/coco/odometry', 10), odom),
            (fixture.create_publisher(Clock, '/clock', 10), Clock()),
            (fixture.create_publisher(String, '/cmd_vel_arbiter/status', 10),
             String(data='mode=idle active=none')),
            (fixture.create_publisher(LaserScan, '/scan', qos_profile_sensor_data),
             scan),
            (fixture.create_publisher(Image, '/camera/image_raw',
                                      qos_profile_sensor_data), camera),
            (fixture.create_publisher(Image, '/camera/depth/image_raw',
                                      qos_profile_sensor_data), depth),
        ]
        fixture.create_subscription(
            TwistStamped, '/cmd_vel_teleop',
            lambda msg: commands.append(msg.twist.linear.x), 10)

        def publish():
            for publisher, message in publishers:
                publisher.publish(message)

        fixture.create_timer(0.067, publish)
        thread = threading.Thread(target=executor.spin, daemon=True)
        thread.start()
        platform = Platform(node)
        server = make_app(platform, '.').listen(0, address='127.0.0.1')
        port = next(iter(server._sockets.values())).getsockname()[1]
        ticker = PeriodicCallback(platform.tick, 100)
        ticker.start()
        socket = await websocket_connect(f'ws://127.0.0.1:{port}/ws')

        async def read_until(predicate, timeout=8):
            deadline = time.monotonic() + timeout
            while True:
                raw = await asyncio.wait_for(
                    socket.read_message(), deadline - time.monotonic())
                assert raw is not None, 'unexpected close'
                if isinstance(raw, bytes):
                    stream, header, payload = binary.decode_frame(raw)
                    received[stream] += 1
                    frame = {'type': 'binary', 'stream': stream, 'header': header}
                    assert payload
                else:
                    frame = json.loads(raw)
                    received[frame['type']] += 1
                if predicate(frame):
                    return frame

        async def request(kind, **fields):
            await socket.write_message(json.dumps(
                dict(type=kind, id=kind, **fields)))
            return await read_until(
                lambda frame: frame.get('type') == 'ack'
                and frame.get('id') == kind)

        async def wait_for(predicate, timeout=3):
            deadline = time.monotonic() + timeout
            while not predicate():
                assert time.monotonic() < deadline, 'observation timed out'
                await asyncio.sleep(0.01)

        await read_until(lambda f: f.get('type') == 'welcome')
        await request('hello', binary=True)
        await read_until(lambda f: f.get('type') == 'telemetry'
                         and f['robot']['online'])
        lidar = await read_until(lambda f: f.get('stream') == 'lidar')
        assert lidar['header']['count'] == 240  # existing downsampling
        assert received['camera'] == received['depth'] == 0
        report['default_opt_in'] = True
        await request('subscribe', streams=['camera', 'depth'])
        await read_until(lambda f: f.get('stream') == 'camera')
        await read_until(lambda f: f.get('stream') == 'depth')
        report['camera_and_depth_received'] = True
        await request('unsubscribe', streams=['camera', 'depth'])
        before = (received['camera'], received['depth'])
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            await read_until(lambda f: f.get('type') == 'telemetry')
        assert before == (received['camera'], received['depth'])
        await wait_for(lambda: not node._open_streams)
        report['unsubscribe_stopped_delivery_and_ros_subscriptions'] = True

        # Positive control proves the recorder can observe nonzero commands.
        await request('drive', linear=0.05, angular=0)
        await wait_for(lambda: commands and commands[-1] == 0.05)
        await request('stop')
        await wait_for(lambda: commands[-1] == 0)
        report['stop_observed_after_nonzero_drive'] = True
        await request('drive', linear=0.05, angular=0)
        await wait_for(lambda: commands[-1] == 0.05)
        socket.close()
        await wait_for(lambda: not platform.clients)
        await wait_for(lambda: commands[-1] == 0)
        report['disconnect_stop_observed_after_nonzero_drive'] = True
        report['frames'] = dict(received)
        report['teleop_samples'] = list(commands)
        report['publisher_qos'] = 'BEST_EFFORT sensor data profile'
        report['result'] = 'PASS'
        print(json.dumps(report, indent=2), flush=True)
    finally:
        if socket:
            socket.close()
        if ticker:
            ticker.stop()
        if server:
            server.stop()
            await server.close_all_connections()
        executor.shutdown(timeout_sec=3)
        if thread:
            thread.join(timeout=3)
        fixture.destroy_node()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    asyncio.run(asyncio.wait_for(main(), timeout=30))
