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

"""Jazzy assertions against live Isaac ROS messages."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import CameraInfo, Image, JointState, LaserScan
from tf2_msgs.msg import TFMessage
from coco_sim.isaac.config import TOPICS, FIXTURES
from coco_config import robot as robot_config


def scan_geometry(scan, pose):
    """Compare bearings to independent analytic ray/rectangle intersections."""
    yaw = pose["yaw"]
    c, sn = math.cos(yaw), math.sin(yaw)
    mount = robot_config.LIDAR_MOUNT_XYZ
    origin = np.array(
        [
            robot_config.SPAWN_XY[0]
            + pose["x"]
            + c * mount[0]
            - sn * mount[1],
            robot_config.SPAWN_XY[1]
            + pose["y"]
            + sn * mount[0]
            + c * mount[1],
        ]
    )
    angles = scan["angle_min"] + np.arange(480) * scan["angle_increment"] + yaw
    direction = np.column_stack((np.cos(angles), np.sin(angles)))
    direction[np.abs(direction) < 1e-12] = 1e-12
    expected = np.full(480, 12.0)
    for _, centre, size, _ in FIXTURES:
        low = np.array(centre[:2]) - np.array(size[:2]) / 2
        high = np.array(centre[:2]) + np.array(size[:2]) / 2
        t1, t2 = (low - origin) / direction, (high - origin) / direction
        near, far = np.minimum(t1, t2).max(axis=1), np.maximum(t1, t2).min(
            axis=1
        )
        expected = np.minimum(
            expected, np.where((near > 0) & (far >= near), near, 12.0)
        )
    residual = np.abs(np.array(scan["ranges_m"]) - expected)
    return dict(
        median_error_m=float(np.median(residual)),
        p95_error_m=float(np.percentile(residual, 95)),
        expected_ranges_m=expected.tolist(),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rclpy.init()
    node = Node("coco_isaac_smoke")
    pub = node.create_publisher(Twist, "/cmd_vel", 10)
    counts = Counter()
    samples = {}
    latest = {}
    edges = set()
    errors = []
    stamps = {}
    first_stamps = {}
    wall_start = time.monotonic()

    def sec(stamp):
        return stamp.sec + stamp.nanosec * 1e-9

    def receive(key, msg):
        counts[key] += 1
        latest[key] = msg
        t = sec(msg.clock if key == "clock" else msg.header.stamp)
        if key in stamps and t < stamps[key]:
            errors.append(key + " timestamp went backwards")
        stamps[key] = t
        first_stamps.setdefault(key, t)
        if key == "odom":
            p, q = msg.pose.pose.position, msg.pose.pose.orientation
            samples[key] = dict(
                x=p.x,
                y=p.y,
                z=p.z,
                yaw=math.atan2(
                    2 * (q.w * q.z + q.x * q.y),
                    1 - 2 * (q.y * q.y + q.z * q.z),
                ),
                vx=msg.twist.twist.linear.x,
                wz=msg.twist.twist.angular.z,
                frame=msg.header.frame_id,
                child=msg.child_frame_id,
                time_sim_s=t,
            )
        elif key == "scan":
            ranges = np.array(msg.ranges)
            samples[key] = dict(
                beams=len(ranges),
                angle_min=msg.angle_min,
                angle_max=msg.angle_max,
                angle_increment=msg.angle_increment,
                finite=int(np.isfinite(ranges).sum()),
                min_m=float(np.nanmin(ranges)),
                forward_m=float(
                    ranges[
                        np.argmin(
                            np.abs(
                                msg.angle_min
                                + np.arange(len(ranges)) * msg.angle_increment
                            )
                        )
                    ]
                ),
                frame=msg.header.frame_id,
                time_sim_s=t,
                ranges_m=ranges.tolist(),
            )
        elif key in ("rgb", "depth"):
            # Copy once, then use bounded numpy operations on pixels.
            raw = np.frombuffer(msg.data, dtype=np.uint8)
            result = dict(
                width=msg.width,
                height=msg.height,
                encoding=msg.encoding,
                frame=msg.header.frame_id,
                bytes=len(msg.data),
                time_sim_s=t,
            )
            if key == "depth" and msg.encoding == "32FC1":
                depth = np.frombuffer(
                    msg.data, dtype=">f4" if msg.is_bigendian else "<f4"
                ).reshape(msg.height, msg.step // 4)[:, : msg.width]
                result.update(
                    finite=int(np.isfinite(depth).sum()),
                    centre_m=float(np.median(depth[110:130, 150:170])),
                )
            elif key == "rgb" and msg.encoding == "rgb8":
                image = raw.reshape(msg.height, msg.step)[
                    :, : msg.width * 3
                ].reshape(msg.height, msg.width, 3)
                centre = image[90:150, 120:200].mean(axis=(0, 1))
                result.update(
                    centre_rgb=centre.tolist(),
                    nonzero=int(np.count_nonzero(raw)),
                )
            samples[key] = result
        elif key == "info":
            samples[key] = dict(
                width=msg.width,
                height=msg.height,
                k=list(msg.k),
                frame=msg.header.frame_id,
            )
        elif key == "joints":
            samples[key] = dict(
                names=list(msg.name), velocities=list(msg.velocity)
            )
        elif key == "clock":
            samples[key] = dict(time_sim_s=t)

    subscriptions = []
    for key, cls in [
        ("odom", Odometry),
        ("clock", Clock),
        ("rgb", Image),
        ("depth", Image),
        ("scan", LaserScan),
        ("info", CameraInfo),
        ("joints", JointState),
    ]:
        subscriptions.append(
            node.create_subscription(
                cls, TOPICS[key], lambda msg, key=key: receive(key, msg), 10
            )
        )  # RELIABLE images, required here.

    def tf(msg):
        counts["tf"] += 1
        edges.update(
            (t.header.frame_id, t.child_frame_id) for t in msg.transforms
        )

    subscriptions.append(node.create_subscription(TFMessage, "/tf", tf, 10))
    subscriptions.append(
        node.create_subscription(
            TFMessage,
            "/tf_static",
            tf,
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL),
        )
    )
    checks = {}
    phases = {}

    def spin_until(predicate, wall_timeout=150):
        deadline = time.monotonic() + wall_timeout
        while not predicate():
            if time.monotonic() > deadline:
                raise RuntimeError(
                    "Timed out waiting for ROS samples/simulation time"
                )
            rclpy.spin_once(node, timeout_sec=0.03)

    def drive(linear, angular, duration, publish=True):
        start = stamps["clock"]
        snapshot = dict(samples["odom"])
        next_pub = 0.0
        deadline = time.monotonic() + max(45, duration * 8)
        while stamps["clock"] - start < duration:
            if time.monotonic() > deadline:
                raise RuntimeError("Simulation clock stopped during motion")
            if publish and time.monotonic() >= next_pub:
                msg = Twist()
                msg.linear.x, msg.angular.z = float(linear), float(angular)
                pub.publish(msg)
                next_pub = time.monotonic() + 0.05
            rclpy.spin_once(node, timeout_sec=0.01)
        return dict(
            start=snapshot,
            end=dict(samples["odom"]),
            duration_sim_s=stamps["clock"] - start,
        )

    try:
        spin_until(
            lambda: all(counts[k] >= 10 for k in TOPICS if k != "command")
            and counts["tf"] > 10
        )
        drive(0, 0, 1.0)
        samples_initial = json.loads(json.dumps(samples))
        checks["ground_contact_height"] = (
            abs(samples_initial["odom"]["z"]) < 0.003
        )
        scan = samples_initial["scan"]
        checks["full_angle_scan"] = (
            scan["beams"] == 480
            and abs(scan["angle_min"] + math.pi) < 0.02
            and abs(scan["angle_increment"] * 480 - 2 * math.pi) < 0.02
            and abs(
                scan["angle_max"]
                - (scan["angle_min"] + 479 * scan["angle_increment"])
            )
            < 0.02
        )
        samples_initial["scan_geometry"] = scan_geometry(
            scan, samples_initial["odom"]
        )
        checks["lidar_bearings_match_geometry"] = (
            samples_initial["scan_geometry"]["p95_error_m"] < 0.08
        )
        checks["lidar_known_east_wall"] = abs(scan["forward_m"] - 7.04) < 0.2
        depth = samples_initial["depth"]
        checks["depth_geometry"] = (
            depth["encoding"] == "32FC1"
            and (depth["width"], depth["height"]) == (320, 240)
            and abs(depth.get("centre_m", 0) - 6.825) < 0.25
        )
        rgb = samples_initial["rgb"]
        colour = rgb.get("centre_rgb", [0, 0, 0])
        checks["rgb_red_wall"] = (
            rgb["encoding"] == "rgb8"
            and (rgb["width"], rgb["height"]) == (320, 240)
            and colour[0] > 1.4 * colour[1]
            and colour[0] > 1.4 * colour[2]
        )
        checks["optical_frames"] = all(
            samples_initial[k]["frame"] == "camera_optical_frame"
            for k in ("rgb", "depth", "info")
        )
        phases["forward"] = drive(0.5, 0, 8.0)
        drive(0, 0, 1.0)
        phase = phases["forward"]
        dx = phase["end"]["x"] - phase["start"]["x"]
        dy = phase["end"]["y"] - phase["start"]["y"]
        checks["forward_motion"] = 2.8 < dx < 4.6 and abs(dy) < 0.5
        checks["forward_twist"] = phase["end"]["vx"] > 0.25
        phases["angular"] = drive(0, 0.5, 3.0)
        drive(0, 0, 1.0)
        phase = phases["angular"]
        yaw = math.atan2(
            math.sin(phase["end"]["yaw"] - phase["start"]["yaw"]),
            math.cos(phase["end"]["yaw"] - phase["start"]["yaw"]),
        )
        checks["positive_yaw"] = 0.3 < yaw < 2.2
        phases["dropout_command"] = drive(0.2, 0, 1.0)
        phases["dropout"] = drive(0, 0, 2.0, publish=False)
        samples["scan_geometry"] = scan_geometry(
            samples["scan"], samples["odom"]
        )
        checks["lidar_bearings_after_motion"] = (
            samples["scan_geometry"]["p95_error_m"] < 0.08
        )
        fx, fy, cx, cy = robot_config.camera_intrinsics()
        k = samples_initial["info"]["k"]
        checks["camera_calibration"] = np.allclose(
            [k[0], k[4], k[2], k[5]], [fx, fy, cx, cy], atol=0.5
        )
        samples["rates_sim_hz"] = {
            k: (counts[k] - 1) / (stamps[k] - first_stamps[k])
            for k in ("rgb", "depth", "scan", "odom")
        }
        checks["sensor_rates"] = all(
            low < samples["rates_sim_hz"][k] < high
            for k, low, high in [
                ("rgb", 12, 17),
                ("depth", 12, 17),
                ("scan", 8, 12),
                ("odom", 25, 35),
            ]
        )
        checks["command_dropout_stops"] = abs(samples["odom"]["vx"]) < 0.03
        checks["tf_tree"] = {
            ("odom", "base_footprint"),
            ("base_footprint", "base_link"),
            ("base_link", "lidar_link"),
            ("base_link", "camera_link"),
            ("camera_link", "camera_optical_frame"),
        } <= edges
        checks["no_localization_tf"] = not any(
            parent == "map" for parent, _ in edges
        )
        checks["single_owners"] = all(
            len(node.get_publishers_info_by_topic(topic)) == 1
            for topic in (
                TOPICS["command"],
                TOPICS["odom"],
                "/clock",
                "/tf",
                "/tf_static",
            )
        )
        checks["simulation_timestamps"] = not errors and all(
            abs(stamps[k] - stamps["clock"]) < 0.3
            for k in ("odom", "scan", "rgb", "depth")
        )
        checks["sensor_streams_continue"] = all(
            counts[k] > 50 for k in ("rgb", "depth", "scan")
        )
        samples["topic_endpoints"] = {
            topic: [
                dict(
                    node=e.node_name,
                    reliability=str(e.qos_profile.reliability),
                    durability=str(e.qos_profile.durability),
                )
                for e in node.get_publishers_info_by_topic(topic)
            ]
            for topic in TOPICS.values()
        }
    except Exception as exc:
        errors.append(repr(exc))
        samples_initial = locals().get("samples_initial", {})
    finally:
        pub.publish(Twist())
        result = dict(
            checks=checks,
            errors=errors,
            counts=dict(counts),
            initial=samples_initial,
            final=samples,
            phases=phases,
            tf_edges=sorted(edges),
            graph=node.get_topic_names_and_types(),
            elapsed_wall_s=time.monotonic() - wall_start,
        )
        result["passed"] = bool(checks) and all(checks.values()) and not errors
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False))
        print(
            json.dumps(
                {
                    "passed": result["passed"],
                    "checks": checks,
                    "errors": errors,
                },
                indent=2,
            )
        )
        node.destroy_node()
        rclpy.shutdown()
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
