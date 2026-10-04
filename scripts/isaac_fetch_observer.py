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

"""Record the existing P03D mission, with no target-coordinate input."""
import argparse
from collections import Counter
import json
from pathlib import Path
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from geometry_msgs.msg import (
    PointStamped,
    PoseWithCovarianceStamped,
    TwistStamped,
)
from moveit_msgs.action import MoveGroup
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, Imu, JointState, LaserScan
from std_msgs.msg import String, Float64
from std_srvs.srv import Trigger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--timeout", type=float, default=1200)
    args = parser.parse_args()
    rclpy.init()
    node = Node(
        "coco_isaac_fetch_observer",
        parameter_overrides=[Parameter("use_sim_time", value=True)],
    )
    counts, first, last = Counter(), {}, {}
    latest = {}
    states = []
    stop_breaches = 0
    stop_samples = 0
    handle = (args.output / "observations.jsonl").open("w")
    start = time.monotonic()

    def stamp():
        return node.get_clock().now().nanoseconds * 1e-9

    def record(topic, data):
        counts[topic] += 1
        first.setdefault(topic, stamp())
        last[topic] = stamp()
        latest[topic] = data
        handle.write(
            json.dumps(
                {
                    "wall_s": time.monotonic() - start,
                    "sim_s": stamp(),
                    "topic": topic,
                    "data": data,
                }
            )
            + "\n"
        )

    frames = {}
    captured = set()

    def image(topic, msg):
        record(topic, "sample")
        frames[topic] = msg

    def snapshot(label):
        # Evaluator-only raw images; no additional input to robot nodes.
        if label in captured or not frames:
            return
        import cv2
        import numpy as np
        from cv_bridge import CvBridge

        bridge = CvBridge()
        folder = args.output / "images"
        folder.mkdir(exist_ok=True)
        for topic, msg in frames.items():
            if "depth" in topic:
                np.save(
                    folder / (label + "_depth.npy"), bridge.imgmsg_to_cv2(msg)
                )
            else:
                cv2.imwrite(
                    str(folder / (label + ".png")),
                    bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8"),
                )
        captured.add(label)

    def status(topic, msg):
        record(topic, msg.data)
        if topic == "/mission/state":
            state = dict(
                part.split("=", 1) for part in msg.data.split() if "=" in part
            ).get("state")
            if state and (not states or states[-1] != state):
                states.append(state)
                snapshot(state)
                print("STATE " + msg.data, flush=True)

    for topic in (
        "/mission/state",
        "/mission/mode",
        "/mission/search_region",
        "/grasp/status",
        "/perception/target_pose/status",
        "/perception/status",
        "/ramp/status",
        "/approach/status",
        "/cmd_vel_arbiter/status",
    ):
        node.create_subscription(
            String, topic, lambda msg, t=topic: status(t, msg), 10
        )

    def point(msg, topic="/perception/target"):
        record(
            topic,
            {
                "frame": msg.header.frame_id,
                "stamp_ns": msg.header.stamp.sec * 10**9
                + msg.header.stamp.nanosec,
                "xyz": [msg.point.x, msg.point.y, msg.point.z],
            },
        )

    node.create_subscription(PointStamped, "/perception/target", point, 10)
    node.create_subscription(
        PointStamped, "/approach/target",
        lambda msg: point(msg, "/approach/target"), 10)
    # Volatile readers receive live state changes from both the Gazebo
    # volatile bridge and Isaac's transient-local publisher.
    magnet_qos = QoSProfile(depth=10)
    for colour in ("red", "green", "blue", "yellow"):
        topic = f"/magnet/target_{colour}/state"
        node.create_subscription(
            String, topic, lambda msg, t=topic: status(t, msg), magnet_qos)
        topic = f"/grasp/target_{colour}/height"
        node.create_subscription(
            Float64, topic, lambda msg, t=topic: record(t, msg.data), 10)
    for topic in ("/diff_drive_controller/odom", "/model/coco/odometry"):

        def odom(msg, t=topic):
            p, q = msg.pose.pose.position, msg.pose.pose.orientation
            record(
                t,
                {
                    "xyz": [p.x, p.y, p.z],
                    "quaternion_xyzw": [q.x, q.y, q.z, q.w],
                },
            )

        node.create_subscription(Odometry, topic, odom, 10)

    def wheel(msg, topic):
        nonlocal stop_breaches, stop_samples
        v, w = msg.twist.linear.x, msg.twist.angular.z
        record(topic, [v, w])
        if (
            topic == "/diff_drive_controller/cmd_vel"
            and latest.get("/mission/mode") == "idle"
        ):
            stop_samples += 1
            stop_breaches += abs(v) + abs(w) > 1e-6

    commands = (
        "/cmd_vel_nav",
        "/cmd_vel_smoothed",
        "/cmd_vel",
        "/cmd_vel_gated",
        "/cmd_vel_rl",
        "/cmd_vel_approach",
        "/diff_drive_controller/cmd_vel",
    )
    for topic in commands:
        node.create_subscription(
            TwistStamped, topic, lambda msg, t=topic: wheel(msg, t), 10
        )
    node.create_subscription(
        JointState,
        "/joint_states",
        lambda msg: record("/joint_states", dict(zip(msg.name, msg.position))),
        10,
    )
    for topic, kind in [
        ("/camera/image_raw", Image),
        ("/camera/depth/image_raw", Image),
        ("/scan", LaserScan),
        ("/imu", Imu),
    ]:
        node.create_subscription(
            kind,
            topic,
            lambda msg, t=topic: (
                image(t, msg)
                if isinstance(msg, Image)
                else record(t, "sample")
            ),
            qos_profile_sensor_data,
        )
    latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_subscription(
        PoseWithCovarianceStamped,
        "/amcl_pose",
        lambda msg: record(
            "amcl",
            {
                "xyz": [
                    msg.pose.pose.position.x,
                    msg.pose.pose.position.y,
                    msg.pose.pose.position.z,
                ],
                "quaternion_xyzw": [
                    msg.pose.pose.orientation.x,
                    msg.pose.pose.orientation.y,
                    msg.pose.pose.orientation.z,
                    msg.pose.pose.orientation.w,
                ],
            },
        ),
        latched,
    )
    services = {
        name: node.create_client(Trigger, name)
        for name in (
            "/mission/start",
            "/grasp/stow",
            "/grasp/pick",
            "/grasp/place",
            "/ramp/climb",
            "/ramp/descend",
            "/approach/run",
        )
    }
    nav = ActionClient(node, NavigateToPose, "/navigate_to_pose")
    move = ActionClient(node, MoveGroup, "/move_action")
    result = {"passed": False, "mission": "NOT_STARTED"}
    lifecycle = {
        name: node.create_client(GetState, f"/{name}/get_state")
        for name in (
            "map_server",
            "amcl",
            "controller_server",
            "planner_server",
            "bt_navigator",
            "behavior_server",
            "velocity_smoother",
            "collision_monitor",
        )
    }
    active = {}
    queried = -1e9
    inflight = set()

    def lifecycle_result(future, name):
        inflight.discard(name)
        response = future.result()
        if response is not None:
            active[name] = response.current_state.id == 3

    begin_wall = begin_sim = None
    try:
        while time.monotonic() - start < 300:
            rclpy.spin_once(node, timeout_sec=0.05)
            # Let Nav2's own manager finish initial transitions before
            # querying readiness; avoid overlapping requests per client.
            if (
                time.monotonic() - start > 15
                and time.monotonic() - queried > 1
            ):
                for name, client in lifecycle.items():
                    if client.service_is_ready() and name not in inflight:
                        inflight.add(name)
                        client.call_async(
                            GetState.Request()
                        ).add_done_callback(
                            lambda future, n=name: lifecycle_result(future, n)
                        )
                queried = time.monotonic()
            if (
                all(active.get(n) for n in lifecycle)
                and all(c.service_is_ready() for c in services.values())
                and nav.server_is_ready()
                and move.server_is_ready()
                and latest.get("amcl")
                and counts["/joint_states"] > 10
            ):
                break
        else:
            raise RuntimeError("Shared stack did not become ready")
        graph = {
            t: [i.node_name for i in node.get_publishers_info_by_topic(t)]
            for t in commands
        }
        (args.output / "command_graph.json").write_text(
            json.dumps(graph, indent=2)
        )
        if graph["/diff_drive_controller/cmd_vel"] != ["cmd_vel_arbiter"]:
            raise RuntimeError(
                "Arbiter is not the sole wheel command publisher"
            )
        begin_wall, begin_sim = time.monotonic(), stamp()
        future = services["/mission/start"].call_async(Trigger.Request())
        while not future.done() and time.monotonic() - begin_wall < 10:
            rclpy.spin_once(node, timeout_sec=0.05)
        if not future.done() or not future.result().success:
            raise RuntimeError("Mission start rejected or timed out")
        while time.monotonic() - begin_wall < args.timeout:
            rclpy.spin_once(node, timeout_sec=0.05)
            if states and states[-1] in ("COMPLETE", "ABORT"):
                break
        result["mission"] = states[-1] if states else "UNOBSERVED"
        result["passed"] = (
            result["mission"] == "COMPLETE" and stop_breaches == 0
        )
    except Exception as exc:
        result["error"] = repr(exc)
    finally:
        result.update(
            states=states,
            counts=dict(counts),
            final=latest,
            stop_samples=stop_samples,
            stop_breaches=stop_breaches,
            mission_wall_s=(
                time.monotonic() - begin_wall if begin_wall else None
            ),
            mission_sim_s=(
                stamp() - begin_sim if begin_sim is not None else None
            ),
            rates_sim_hz={
                t: (counts[t] - 1) / (last[t] - first[t])
                for t in counts
                if last[t] > first[t]
            },
        )
        (args.output / "result.json").write_text(json.dumps(result, indent=2))
        handle.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
