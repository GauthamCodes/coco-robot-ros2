"""Real ROS graph: divergent evaluator truth cannot reach autonomy.

Construct production nodes without a simulator or MoveIt server. The synthetic
publisher uses the same encoder serialization that the Isaac runtime uses.
"""
import json
import os
from pathlib import Path
import sys
import time

import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from std_msgs.msg import Float64, String

from coco_config.encoder_odometry import EncoderOdometry, arena_xy
from coco_config.ros_boundary import AutonomyNode, privileged_topic
from coco_sim.isaac.odometry import encoder_message
from coco_rl.ramp_driver import RampDriver
from coco_rl.ramp_env import CocoRampEnv
from coco_rl.terrain_observer_node import TerrainObserverNode
from coco_perception.target_finder import TargetFinder
from coco_perception.target_pose_node import TargetPoseNode
from custom_teleop.approach_server import ApproachServer
from custom_teleop.cmd_vel_arbiter import CmdVelArbiter
from custom_teleop.cmd_vel_relay import CmdVelRelay

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'coco_mission/scripts'))
sys.path.insert(0, str(ROOT / 'coco_moveit_config/scripts'))
from mission_executive import MissionExecutive
from localization_monitor import LocalizationMonitor
from grasp_server import GraspServer


def spin_until(executor, predicate, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.02)
        if predicate():
            return
    raise AssertionError('ROS graph/message condition did not arrive')


@pytest.mark.parametrize('backend', ['gazebo', 'isaac'])
def test_production_graph_and_divergent_truth(backend):
    rclpy.init(args=['--ros-args', '-p', f'simulator:={backend}'],
               domain_id=120 + os.getpid() % 80)
    nodes = []
    executor = SingleThreadedExecutor()
    try:
        mission = MissionExecutive(colour='red')
        nodes.append(mission)
        ramp = RampDriver()
        nodes.append(ramp)
        env = CocoRampEnv(randomize=False, teleport=False)
        nodes.append(env.node)
        grasp = GraspServer()
        nodes.append(grasp)
        grasp._select('red')
        for constructor in (TerrainObserverNode, TargetFinder, TargetPoseNode,
                            ApproachServer, LocalizationMonitor,
                            CmdVelRelay, CmdVelArbiter):
            nodes.append(constructor())
        probe = Node('isolation_probe')
        nodes.append(probe)
        for node in nodes:
            executor.add_node(node)
        odom_pub = probe.create_publisher(Odometry, '/diff_drive_controller/odom', 10)
        truth_pub = probe.create_publisher(Odometry, '/eval/robot/odometry', 10)
        height_pub = probe.create_publisher(Float64, '/eval/objects/target_red/height', 10)
        imu_pub = probe.create_publisher(Imu, '/imu', 10)
        magnet_pub = probe.create_publisher(String, '/magnet/target_red/state', 10)
        received = []
        # Positive control: evaluator fixture really receives the contradictory truth.
        probe.create_subscription(Odometry, '/eval/robot/odometry', received.append, 10)
        state = EncoderOdometry()
        encoder_message(state, [0.0] * 4, 0.0, probe.get_clock().now().to_msg())
        legitimate = encoder_message(state, [2.0] * 4, 1.0,
                                     probe.get_clock().now().to_msg())
        truth = Odometry()
        truth.header.frame_id = 'world'
        truth.child_frame_id = 'base_footprint'
        truth.pose.pose.position.x = 1000.0
        truth.pose.pose.position.y = -1000.0
        truth.pose.pose.orientation.w = 1.0
        imu = Imu()
        imu.orientation.w = 1.0
        imu.header.frame_id = 'imu_link'

        def deliver():
            odom_pub.publish(legitimate)
            truth_pub.publish(truth)
            height_pub.publish(Float64(data=99.0))
            imu_pub.publish(imu)
            magnet_pub.publish(String(data="attached"))
            return (bool(received) and mission._pose is not None
                    and ramp._world_y is not None and env._odom is not None
                    and env._imu is not None and grasp._odom is not None
                    and grasp._imu is not None)

        spin_until(executor, deliver)
        assert received[-1].pose.pose.position.x == 1000.0
        assert mission.observe().pose[:2] == pytest.approx(arena_xy(legitimate.pose.pose.position))
        assert ramp._world_y == pytest.approx(arena_xy(legitimate.pose.pose.position)[1])
        env._x0 = env._y0 = 0.0
        assert env._state()[0] == pytest.approx(legitimate.pose.pose.position.x)
        mission._on_odom(truth)
        assert mission.observe().pose[:2] == pytest.approx(arena_xy(legitimate.pose.pose.position))
        assert grasp.check_robot_pose('graph', expect_xy=None)
        # Poison even the former cache; no current gate consults it.
        grasp._heights['target_red'] = (99.0, time.monotonic())
        grasp._grasp_z = 0.0
        assert not grasp.grasp_magnet()
        assert not grasp.check_lifted()
        assert not grasp.check_released()
        # Retention/placement cannot be claimed with no verified lift.
        assert grasp.lifted is not True
        assert not grasp.holding
        subscriptions = {}
        for topic, _ in probe.get_topic_names_and_types():
            for info in probe.get_subscriptions_info_by_topic(topic):
                if info.node_name in {node.get_name() for node in nodes[:-1]}:
                    subscriptions.setdefault(info.node_name, []).append(topic)
                    assert not privileged_topic(topic), (info.node_name, topic)
        assert set(subscriptions) == {node.get_name() for node in nodes[:-1]}
        authorities = probe.get_publishers_info_by_topic('/diff_drive_controller/cmd_vel')
        assert [info.node_name for info in authorities] == ['cmd_vel_arbiter']
        evidence = os.environ.get('COCO_GTI_EVIDENCE')
        if evidence:
            Path(evidence).mkdir(parents=True, exist_ok=True)
            (Path(evidence) / f'{backend}_graph.json').write_text(json.dumps({
                'subscriptions': subscriptions, 'wheel_authorities': ['cmd_vel_arbiter'],
                'truth_x': 1000.0, 'encoder_x': legitimate.pose.pose.position.x,
                'mission_xy': mission.observe().pose[:2], 'gates_fail_closed': True,
            }, indent=2) + '\n')
    finally:
        for node in reversed(nodes):
            executor.remove_node(node)
            node.destroy_node()
        executor.shutdown()
        rclpy.shutdown()


@pytest.mark.parametrize('topic', ['/eval', '/eval/robot/odometry', '/world/x',
                                   '/model/coco/odometry', '/grasp/target_red/height'])
def test_resolved_remaps_cannot_create_privileged_endpoints(topic):
    rclpy.init(args=['--ros-args', '-r', f'/diff_drive_controller/odom:={topic}'])
    node = AutonomyNode('remap_guard')
    try:
        with pytest.raises(ValueError, match='Privileged autonomy'):
            node.create_subscription(Odometry, '/diff_drive_controller/odom', lambda _: None, 10)
        assert not any(privileged_topic(t) for t, _ in node.get_topic_names_and_types())
    finally:
        node.destroy_node()
        rclpy.shutdown()


def test_direct_wheel_output_remap_is_rejected():
    rclpy.init(args=['--ros-args', '-r', '/cmd_vel_rl:=/diff_drive_controller/cmd_vel'])
    node = AutonomyNode('command_guard')
    try:
        from geometry_msgs.msg import TwistStamped
        with pytest.raises(ValueError, match='Only cmd_vel_arbiter'):
            node.create_publisher(TwistStamped, '/cmd_vel_rl', 10)
    finally:
        node.destroy_node()
        rclpy.shutdown()


def test_legacy_ramp_teleport_is_rejected_before_ros_initialization():
    assert not rclpy.ok()
    with pytest.raises(ValueError, match='teleport reset'):
        CocoRampEnv(teleport=True)
    assert not rclpy.ok()


def test_robot_sources_have_no_direct_simulator_pose_calls():
    import ast

    paths = [ROOT / 'coco_mission/scripts/mission_executive.py',
             ROOT / 'coco_moveit_config/scripts/arm_control.py',
             ROOT / 'coco_rl/coco_rl/ramp_driver.py',
             ROOT / 'coco_rl/coco_rl/ramp_env.py',
             ROOT / 'custom_teleop/custom_teleop/approach_server.py',
             ROOT / 'coco_perception/coco_perception/target_finder.py',
             ROOT / 'coco_perception/coco_perception/target_pose_node.py']
    forbidden = {'get_world_pose', 'get_local_pose', 'get_linear_velocity',
                 'get_angular_velocity', 'get_model_state', 'set_world_pose'}
    for path in paths:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden, (path, node.lineno)
            if isinstance(node, ast.List):
                tokens = [item.value for item in node.elts if isinstance(item, ast.Constant)]
                assert tokens[:2] != ['gz', 'model'], (path, node.lineno)
