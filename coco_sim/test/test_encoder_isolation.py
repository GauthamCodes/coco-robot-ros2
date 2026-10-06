"""Measured joints produce normal odometry, independently of world truth."""
import ast
import math
from pathlib import Path

from builtin_interfaces.msg import Time
from coco_config import robot as r
from coco_config.encoder_odometry import EncoderOdometry
from coco_sim.isaac.odometry import encoder_message
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_stationary_encoders_remain_stationary_and_forward_distance_is_physical():
    state = EncoderOdometry()
    encoder_message(state, [4.0] * 4, 0.0, Time())
    stationary = encoder_message(state, [4.0] * 4, 1.0, Time(sec=1))
    assert stationary.pose.pose.position.x == 0
    assert stationary.twist.twist.linear.x == 0
    forward = encoder_message(state, [6.0] * 4, 2.0, Time(sec=2))
    assert forward.pose.pose.position.x == pytest.approx(2 * r.WHEEL_RADIUS)
    assert forward.twist.twist.linear.x == pytest.approx(2 * r.WHEEL_RADIUS)
    assert forward.pose.pose.position.z == 0
    assert forward.header.frame_id == 'odom'
    assert forward.child_frame_id == 'base_footprint'


def test_exact_arc_and_in_place_rotation_from_side_displacement():
    state = EncoderOdometry()
    state.update([0] * 4, 0.0)
    track = r.WHEEL_SEPARATION * r.WHEEL_SEPARATION_MULTIPLIER
    state.update([track / r.WHEEL_RADIUS] * 2 + [0.0] * 2, 1.0)
    assert state.yaw == pytest.approx(1.0)
    assert state.x == pytest.approx(track / 2 * math.sin(1.0))
    assert state.y == pytest.approx(track / 2 * (1 - math.cos(1.0)))
    spin = EncoderOdometry()
    spin.update([0] * 4, 0.0)
    spin.update([1, 1, -1, -1], 1.0)
    assert (spin.x, spin.y) == (0, 0)
    assert spin.angular > 0


@pytest.mark.parametrize('angles,stamp', [([0, 0, 0], 1),
                                          ([float('nan')] * 4, 1),
                                          ([0] * 4, 0),
                                          ([0] * 4, float('inf'))])
def test_invalid_encoders_or_clock_cannot_inject_pose(angles, stamp):
    state = EncoderOdometry()
    state.update([0] * 4, 0)
    with pytest.raises(ValueError):
        state.update(angles, stamp)
    assert (state.x, state.y, state.yaw) == (0, 0, 0)


def test_gazebo_and_isaac_have_same_feedback_geometry_and_odom_contract():
    config = yaml.safe_load((ROOT / 'gazebo_models/urdf/coco_controllers.yaml').read_text())
    params = config['diff_drive_controller']['ros__parameters']
    assert params['open_loop'] is False
    assert params.get('position_feedback', True) is True
    assert params['wheel_radius'] == r.WHEEL_RADIUS
    assert params['wheel_separation'] == r.WHEEL_SEPARATION
    assert params['wheel_separation_multiplier'] == r.WHEEL_SEPARATION_MULTIPLIER
    msg = encoder_message(EncoderOdometry(), [0] * 4, 0, Time())
    assert msg.header.frame_id == params['odom_frame_id']
    assert msg.child_frame_id == params['base_frame_id']
    assert list(msg.pose.covariance)[::7] == params['pose_covariance_diagonal']


def test_deployed_isaac_publisher_and_base_tf_use_encoder_state():
    source = (ROOT / 'coco_sim/coco_sim/isaac/runtime.py').read_text()
    tree = ast.parse(source)
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'odom' for t in node.targets)]
    assert len(assignments) == 1
    call = assignments[0].value
    assert isinstance(call, ast.Call) and call.func.id == 'encoder_message'
    assert [argument.id for argument in call.args] == ['wheel_odom', 'angles', 'now', 'stamp']
    assert 'odom_pub.publish(odom)' in source
    assert '(wheel_odom.x, wheel_odom.y, 0.0)' in source
    assert 'math.cos(wheel_odom.yaw / 2)' in source
    assert 'measured_yaw = float(imu.angular_velocity.z)' in source
    assert 'measured_yaw = float(angular[2])' not in source
    assert '"/eval/robot/odometry"' in source


def test_gazebo_truth_is_only_bridged_into_eval():
    bridge = yaml.safe_load((ROOT / 'gazebo_models/config/bridge.yaml').read_text())
    worlds = [item for item in bridge if item.get('gz_type_name') == 'gz.msgs.Odometry']
    assert [item['ros_topic_name'] for item in worlds] == ['/eval/robot/odometry']
    assert [item['gz_topic_name'] for item in worlds] == ['/eval/robot/odometry']
    assert '<odom_topic>/eval/robot/odometry</odom_topic>' in (
        ROOT / 'gazebo_models/urdf/coco_robo2.xacro').read_text()
