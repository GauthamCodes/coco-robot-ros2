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

"""Launch one Isaac 4.5 process with a generated base and the ROS contract."""
import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import signal
import time

from coco_config import robot as r
from coco_sim.episode import resolve_episode
from .config import (
    DriveCommand,
    COMMAND_TIMEOUT,
    FRAMES,
    PHYSICS_DT,
    RENDER_DT,
    TOPICS,
    wheel_layout,
)
from .model import build_scene, robot_description


def sensors(stage, app):
    """Configure the proven 4.5 PhysX LiDAR and reliable RTX image bridge."""
    import omni.graph.core as og
    import omni.kit.commands
    import omni.replicator.core as rep
    import usdrt
    from pxr import Gf

    root = "/World/coco/base_link"
    ok, lidar = omni.kit.commands.execute(
        "RangeSensorCreateLidar",
        path="/lidar",
        parent=root,
        min_range=0.15,
        max_range=12.0,
        draw_points=False,
        draw_lines=False,
        horizontal_fov=360.0,
        vertical_fov=1.0,
        horizontal_resolution=0.75,
        vertical_resolution=1.0,
        rotation_rate=0.0,
        high_lod=False,
        yaw_offset=0.0,
        enable_semantics=True,
    )
    if not ok:
        raise RuntimeError("PhysX LiDAR creation failed")
    lidar.GetPrim().GetAttribute("xformOp:translate").Set(
        Gf.Vec3d(*r.LIDAR_MOUNT_XYZ)
    )
    rp = rep.create.render_product(root + "/camera", r.CAMERA_WH)
    br = "isaacsim.ros2.bridge."
    px = "isaacsim.sensors.physx."
    core = "isaacsim.core.nodes."
    nodes = [
        ("Tick", "omni.graph.action.OnPlaybackTick"),
        ("Time", core + "IsaacReadSimulationTime"),
        ("Gate", core + "IsaacSimulationGate"),
        ("Beams", px + "IsaacReadLidarBeams"),
        ("Scan", br + "ROS2PublishLaserScan"),
    ]
    values = [
        ("Gate.inputs:step", 3),
        ("Beams.inputs:lidarPrim", [usdrt.Sdf.Path(str(lidar.GetPath()))]),
        ("Scan.inputs:topicName", TOPICS["scan"]),
        ("Scan.inputs:frameId", FRAMES["lidar"]),
    ]
    connections = [
        ("Tick.outputs:tick", "Gate.inputs:execIn"),
        ("Gate.outputs:execOut", "Beams.inputs:execIn"),
        ("Beams.outputs:execOut", "Scan.inputs:execIn"),
        ("Time.outputs:simulationTime", "Scan.inputs:timeStamp"),
    ]
    connections += [
        ("Beams.outputs:" + a, "Scan.inputs:" + a)
        for a in (
            "azimuthRange",
            "depthRange",
            "horizontalFov",
            "horizontalResolution",
            "intensitiesData",
            "linearDepthData",
            "numCols",
            "numRows",
            "rotationRate",
        )
    ]
    for name, kind, topic in [
        ("RGB", "rgb", "rgb"),
        ("Depth", "depth", "depth"),
        ("Info", "camera_info", "info"),
    ]:
        nodes.append(
            (
                name,
                br
                + (
                    "ROS2CameraInfoHelper"
                    if name == "Info"
                    else "ROS2CameraHelper"
                ),
            )
        )
        values += [
            (name + ".inputs:renderProductPath", rp.path),
            (name + ".inputs:topicName", TOPICS[topic]),
            (name + ".inputs:frameId", FRAMES["optical"]),
            (name + ".inputs:useSystemTime", False),
            (name + ".inputs:frameSkipCount", 1),
            (name + ".inputs:queueSize", 2),
        ]
        if name != "Info":
            values.append((name + ".inputs:type", kind))
        connections.append(("Tick.outputs:tick", name + ".inputs:execIn"))
    keys = og.Controller.Keys
    og.Controller.edit(
        {"graph_path": "/World/Sensors", "evaluator_name": "execution"},
        {
            keys.CREATE_NODES: nodes,
            keys.SET_VALUES: values,
            keys.CONNECT: connections,
        },
    )
    return rp


def main():
    """Run the backend; shutdown is graceful on SIGINT, SIGTERM or duration."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true")
    parser.add_argument(
        "--seconds",
        type=float,
        default=0,
        help="Simulation seconds after initialization; 0 is unlimited",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New evidence directory (must not exist)",
    )
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--robot-urdf", type=Path)
    parser.add_argument("--episode-manifest", default="")
    parser.add_argument(
        "--episode-level",
        default="colours",
        choices=["fixed", "colours", "positions"],
    )
    parser.add_argument("--episode-seed", type=int, default=5)
    parser.add_argument("--colour", default="red")
    args = parser.parse_args()
    if args.fetch and not args.robot_urdf:
        parser.error("--fetch requires the canonical expanded --robot-urdf")
    description = args.robot_urdf.read_text() if args.fetch else None
    share = Path(os.environ["COCO_GAZEBO_SHARE"]) if args.fetch else None
    if importlib.metadata.version("isaacsim") != "4.5.0.0":
        raise RuntimeError("Only the validated Isaac Sim 4.5.0.0 is allowed")
    args.output.mkdir(parents=True, exist_ok=False)
    episode = resolve_episode(
        seed=args.episode_seed if args.fetch else 0,
        level=args.episode_level if args.fetch else "fixed",
        backend="isaac",
        requested_colour=args.colour,
        manifest_path=args.episode_manifest,
    )
    if args.fetch and episode.world_variant != "coco_world":
        raise ValueError("Isaac fetch currently supports only coco_world")
    (args.output / "episode.json").write_text(episode.to_json())
    (args.output / "scene.json").write_text(
        json.dumps(
            {
                "kind": "fetch_arena" if args.fetch else "foundation_fixture",
                "episode_layout_instantiated": args.fetch,
                "robot_start_from_episode": True,
                "time_source": "simulation",
                "physics_dt_sim_s": PHYSICS_DT,
                "render_dt_sim_s": RENDER_DT,
            },
            indent=2,
        )
    )
    (args.output / "robot.urdf").write_text(description or robot_description())
    wall_start = time.monotonic()

    def log(event, **data):
        print(
            json.dumps(
                {
                    "event": event,
                    "elapsed_wall_s": time.monotonic() - wall_start,
                    **data,
                }
            ),
            flush=True,
        )

    from isaacsim import SimulationApp

    app = SimulationApp(
        {
            "headless": not args.gui,
            "create_new_stage": False,
            "width": 640,
            "height": 480,
            "multi_gpu": False,
            "fast_shutdown": True,
        }
    )
    node = None
    sim = None
    try:
        import omni.usd
        import omni.kit.app
        import numpy as np
        from isaacsim.core.api import SimulationContext
        from isaacsim.core.prims import SingleArticulation
        from isaacsim.core.utils.types import ArticulationAction

        ctx = omni.usd.get_context()
        ctx.new_stage()
        for _ in range(3):
            app.update()
        root = build_scene(ctx.get_stage(), episode, description, share)
        ctx.get_stage().Export(str(args.output / "scene.usda"))
        log("scene_created")
        # No new_stage after this boundary; preserve the tested ordering.
        em = omni.kit.app.get_app().get_extension_manager()
        for extension in ("isaacsim.sensors.physx", "isaacsim.ros2.bridge"):
            if not em.set_extension_enabled_immediate(extension, True):
                raise RuntimeError("Could not enable " + extension)
        for _ in range(3):
            app.update()
        log("bridge_enabled")
        render_product = sensors(ctx.get_stage(), app)
        if not render_product.path:
            raise RuntimeError("Camera render product has no path")
        sim = SimulationContext(
            physics_dt=PHYSICS_DT,
            rendering_dt=RENDER_DT,
            stage_units_in_meters=1.0,
            physics_prim_path="/World/physics",
        )
        sim.initialize_physics()
        sim.play()
        robot = SingleArticulation(root)
        robot.initialize()
        indices = [
            robot.get_dof_index(name + "_joint")
            for name, _, _ in wheel_layout()
        ]

        # This rclpy belongs to the bridge's bundled Humble, never host Jazzy.
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import QoSProfile, DurabilityPolicy
        from builtin_interfaces.msg import Time
        from geometry_msgs.msg import TwistStamped, TransformStamped
        from nav_msgs.msg import Odometry
        from rosgraph_msgs.msg import Clock
        from sensor_msgs.msg import JointState, Imu
        from std_msgs.msg import String
        from tf2_msgs.msg import TFMessage

        arm_names, arm_indices = [], []
        magnet = None
        if args.fetch:
            from coco_config.joint_limits import ARM_LIMITS
            from .articulated import origin, quaternion
            from scipy.spatial.transform import Rotation
            from .control import valid_positions

            arm_names = list(ARM_LIMITS)
            arm_indices = [
                robot.get_dof_index(n.replace("-", "_")) for n in arm_names
            ]
            arm_targets = dict(
                zip(arm_names, robot.get_joint_positions()[arm_indices])
            )

        rclpy.init()
        node = Node("coco_isaac_backend")
        drive = DriveCommand()

        def command(msg):
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            drive.receive(msg.twist.linear.x, msg.twist.angular.z, stamp)

        node.create_subscription(TwistStamped, TOPICS["command"], command, 1)
        if args.fetch:
            from .grasp import Magnet
            from coco_sim.backends.isaac import IsaacBackend

            magnet = Magnet(
                ctx.get_stage(),
                node,
                IsaacBackend().translate(episode).targets,
                description,
                log,
            )

            def arm_command(msg):
                stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
                if (
                    0 <= sim.current_time - stamp <= COMMAND_TIMEOUT
                    and valid_positions(msg.name, msg.position)
                ):
                    arm_targets.update(zip(msg.name, msg.position))

            node.create_subscription(
                JointState, "/isaac/manipulator_command", arm_command, 10
            )
        gt_pub = (
            node.create_publisher(Odometry, "/model/coco/odometry", 10)
            if args.fetch
            else None
        )
        imu_pub = (
            node.create_publisher(Imu, "/imu", 10) if args.fetch else None
        )
        odom_pub = node.create_publisher(Odometry, TOPICS["odom"], 10)
        clock_pub = node.create_publisher(Clock, TOPICS["clock"], 10)
        tf_pub = node.create_publisher(TFMessage, "/tf", 10)
        joint_pub = node.create_publisher(JointState, TOPICS["joints"], 10)
        latched = QoSProfile(
            depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL
        )
        static_pub = node.create_publisher(TFMessage, "/tf_static", latched)
        description_pub = node.create_publisher(
            String, "/robot_description", latched
        )
        description_pub.publish(
            String(data=description or robot_description())
        )

        def transform(parent, child, xyz, quat, stamp):
            msg = TransformStamped()
            msg.header.frame_id, msg.child_frame_id = parent, child
            msg.header.stamp = stamp
            (
                msg.transform.translation.x,
                msg.transform.translation.y,
                msg.transform.translation.z,
            ) = map(float, xyz)
            (
                msg.transform.rotation.w,
                msg.transform.rotation.x,
                msg.transform.rotation.y,
                msg.transform.rotation.z,
            ) = map(float, quat)
            return msg

        static_pub.publish(
            TFMessage(
                transforms=[
                    transform(
                        FRAMES["base"],
                        FRAMES["body"],
                        (0, 0, r.CHASSIS_GROUND_CLEARANCE),
                        (1, 0, 0, 0),
                        Time(),
                    ),
                    transform(
                        FRAMES["body"],
                        FRAMES["lidar"],
                        r.LIDAR_MOUNT_XYZ,
                        (1, 0, 0, 0),
                        Time(),
                    ),
                    transform(
                        FRAMES["body"],
                        FRAMES["camera"],
                        r.CAMERA_MOUNT_XYZ,
                        (1, 0, 0, 0),
                        Time(),
                    ),
                    transform(
                        FRAMES["camera"],
                        FRAMES["optical"],
                        (0, 0, 0),
                        (0.5, -0.5, 0.5, -0.5),
                        Time(),
                    ),
                ]
            )
        )
        if args.fetch:
            import xml.etree.ElementTree as ET

            tree = ET.fromstring(description)
            # Re-publish one complete static message (latched history depth=1).
            static_transforms = []
            for joint in tree.findall("joint"):
                if joint.get("type") != "fixed":
                    continue
                matrix = origin(joint)
                static_transforms.append(
                    transform(
                        joint.find("parent").get("link"),
                        joint.find("child").get("link"),
                        matrix[:3, 3],
                        quaternion(matrix),
                        Time(),
                    )
                )
            static_pub.publish(TFMessage(transforms=static_transforms))
        stop = [False]
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: stop.__setitem__(0, True))
        (args.output / "ready.marker").write_text("ready")
        log("ready", joints=robot.dof_names)
        initial_time = sim.current_time
        last_log = -10.0
        previous_linear_world = None
        layout_checked = False
        while app.is_running() and not stop[0]:
            loop_start = time.monotonic()
            now = sim.current_time
            if args.seconds and now - initial_time >= args.seconds:
                break
            rclpy.spin_once(node, timeout_sec=0.0)
            robot.apply_action(
                ArticulationAction(
                    joint_velocities=np.array(drive.step(now, RENDER_DT)),
                    joint_indices=np.array(indices),
                )
            )
            if args.fetch:
                robot.apply_action(
                    ArticulationAction(
                        joint_positions=np.array(
                            [arm_targets[n] for n in arm_names]
                        ),
                        joint_indices=np.array(arm_indices),
                    )
                )
            sim.step(render=True)
            now = sim.current_time
            stamp = Time(sec=int(now), nanosec=int((now % 1) * 1e9))
            clock_pub.publish(Clock(clock=stamp))
            position, q = robot.get_world_pose()
            qw, qx, qy, qz = map(float, q)
            # base_link -> footprint offset rotated into world coordinates.
            offset = r.CHASSIS_GROUND_CLEARANCE * np.array(
                [
                    2 * (qx * qz + qw * qy),
                    2 * (qy * qz - qw * qx),
                    1 - 2 * (qx * qx + qy * qy),
                ]
            )
            position = (
                position
                - offset
                - np.array([episode.robot_start.x, episode.robot_start.y, 0.0])
            )
            yaw = math.atan2(
                2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz)
            )
            linear_world = robot.get_linear_velocity()
            angular_world = robot.get_angular_velocity()
            # Odometry twist is in child frame, not world frame.
            rot = np.array(
                [
                    [
                        1 - 2 * (qy * qy + qz * qz),
                        2 * (qx * qy - qw * qz),
                        2 * (qx * qz + qw * qy),
                    ],
                    [
                        2 * (qx * qy + qw * qz),
                        1 - 2 * (qx * qx + qz * qz),
                        2 * (qy * qz - qw * qx),
                    ],
                    [
                        2 * (qx * qz - qw * qy),
                        2 * (qy * qz + qw * qx),
                        1 - 2 * (qx * qx + qy * qy),
                    ],
                ]
            )
            linear = rot.T @ (linear_world - np.cross(angular_world, offset))
            angular = rot.T @ angular_world
            odom = Odometry()
            odom.header.stamp, odom.header.frame_id = stamp, FRAMES["odom"]
            odom.child_frame_id = FRAMES["base"]
            (
                odom.pose.pose.position.x,
                odom.pose.pose.position.y,
                odom.pose.pose.position.z,
            ) = map(float, position)
            (
                odom.pose.pose.orientation.w,
                odom.pose.pose.orientation.x,
                odom.pose.pose.orientation.y,
                odom.pose.pose.orientation.z,
            ) = map(float, q)
            (
                odom.twist.twist.linear.x,
                odom.twist.twist.linear.y,
                odom.twist.twist.linear.z,
            ) = map(float, linear)
            (
                odom.twist.twist.angular.x,
                odom.twist.twist.angular.y,
                odom.twist.twist.angular.z,
            ) = map(float, angular)
            odom_pub.publish(odom)
            if gt_pub:
                import copy

                gt = copy.deepcopy(odom)
                gt.header.frame_id = "world"
                gt.pose.pose.position.x += episode.robot_start.x
                gt.pose.pose.position.y += episode.robot_start.y
                gt_pub.publish(gt)
                imu = Imu()
                imu.header.stamp, imu.header.frame_id = stamp, "imu_link"
                imu.orientation = odom.pose.pose.orientation
                imu.angular_velocity = odom.twist.twist.angular
                # Ideal body-mounted IMU specific force, including gravity.
                previous = (
                    previous_linear_world
                    if previous_linear_world is not None
                    else linear_world
                )
                acceleration = rot.T @ (
                    (linear_world - previous) / RENDER_DT
                    + np.array([0, 0, 9.81])
                )
                previous_linear_world = linear_world.copy()
                (
                    imu.linear_acceleration.x,
                    imu.linear_acceleration.y,
                    imu.linear_acceleration.z,
                ) = map(float, acceleration)
                imu_pub.publish(imu)
                magnet.publish()
            angles = robot.get_joint_positions()[indices]
            velocities = robot.get_joint_velocities()[indices]
            joint = JointState()
            joint.header.stamp = stamp
            joint.name = [name + "_joint" for name, _, _ in wheel_layout()]
            joint.position, joint.velocity = list(map(float, angles)), list(
                map(float, velocities)
            )
            if args.fetch:
                joint.name = [f"base_Revolute-{i + 1}" for i in range(4)]
                joint.name += arm_names
                joint.position = list(joint.position) + list(
                    map(float, robot.get_joint_positions()[arm_indices])
                )
                joint.velocity = list(joint.velocity) + list(
                    map(float, robot.get_joint_velocities()[arm_indices])
                )
            joint_pub.publish(joint)
            transforms = [
                transform(FRAMES["odom"], FRAMES["base"], position, q, stamp)
            ]
            transforms += (
                []
                if args.fetch
                else [
                    transform(
                        FRAMES["body"],
                        name,
                        xyz,
                        (math.cos(a / 2), 0, math.sin(a / 2), 0),
                        stamp,
                    )
                    for (name, xyz, _), a in zip(wheel_layout(), angles)
                ]
            )
            if args.fetch:
                positions = dict(
                    zip(arm_names, robot.get_joint_positions()[arm_indices])
                )
                for j in tree.findall("joint"):
                    if j.get("type") == "fixed":
                        continue
                    matrix = origin(j)
                    motion = np.eye(4)
                    axis = np.array(
                        list(map(float, j.find("axis").get("xyz").split()))
                    )
                    value = positions.get(j.get("name"))
                    if value is None:
                        value = angles[
                            int(j.get("name").rsplit("-", 1)[1]) - 1
                        ]
                    motion[:3, :3] = Rotation.from_rotvec(
                        axis / np.linalg.norm(axis) * value
                    ).as_matrix()
                    matrix = matrix @ motion
                    transforms.append(
                        transform(
                            j.find("parent").get("link"),
                            j.find("child").get("link"),
                            matrix[:3, 3],
                            quaternion(matrix),
                            stamp,
                        )
                    )
            tf_pub.publish(TFMessage(transforms=transforms))
            if args.fetch and not layout_checked and now >= 2:
                from coco_sim.backends.common import (
                    ObservedPose,
                    check_instantiation,
                )

                observed = {}
                for name, body in magnet.bodies.items():
                    p, quat = body.get_world_pose()
                    roll, pitch, _ = Rotation.from_quat(
                        (*quat[1:], quat[0])
                    ).as_euler("xyz")
                    observed[name] = ObservedPose(
                        *map(float, p), float(roll), float(pitch)
                    )
                report = check_instantiation(episode, observed)
                (args.output / "settled_targets.json").write_text(
                    json.dumps(report, indent=2)
                )
                log("target_layout", **report)
                layout_checked = True
            if now - last_log >= 2:
                from isaacsim.sensors.physx import _range_sensor

                interface = _range_sensor.acquire_lidar_sensor_interface()
                hit_paths = interface.get_prim_data(
                    "/World/coco/base_link/lidar"
                )
                own_hits = [
                    str(p)
                    for p in np.asarray(hit_paths).ravel()
                    if str(p).startswith("/World/coco/")
                ]
                log(
                    "lidar_self_hits",
                    count=len(own_hits),
                    paths=sorted(set(own_hits)),
                )
                log(
                    "state",
                    time_sim_s=now,
                    position_odom_m=list(map(float, position)),
                    yaw_rad=yaw,
                    measured_wheels_rad_s=list(joint.velocity[:4]),
                    measured_arm_rad=list(joint.position[4:]),
                    targets_world_m=(
                        {
                            name: list(map(float, body.get_world_pose()[0]))
                            for name, body in magnet.bodies.items()
                        }
                        if magnet
                        else {}
                    ),
                    command_m_s_rad_s=drive.velocity,
                    command_age_sim_s=now - drive.stamp,
                )
                last_log = now
            # Never accelerate sim time beyond wall delivery.
            time.sleep(max(0.0, RENDER_DT - (time.monotonic() - loop_start)))
        robot.apply_action(
            ArticulationAction(
                joint_velocities=np.zeros(4), joint_indices=np.array(indices)
            )
        )
        log("stopping", time_sim_s=sim.current_time)
    except BaseException:
        import traceback

        traceback.print_exc()
        (args.output / "failure.txt").write_text(traceback.format_exc())
        raise
    finally:
        if sim is not None:
            sim.stop()
        if node is not None:
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
        if not (args.output / "failure.txt").exists():
            (args.output / "shutdown_requested.json").write_text(
                json.dumps({"normal_close": True})
            )
        app.close()
    (args.output / "shutdown.json").write_text(json.dumps({"clean": True}))
    log("closed")


if __name__ == "__main__":
    main()
