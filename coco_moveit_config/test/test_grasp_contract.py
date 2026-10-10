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

"""Construct the real shared grasp server; invalid perception fails closed."""

from pathlib import Path
import sys

import pytest
import rclpy
from geometry_msgs.msg import PointStamped

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
try:
    from grasp_server import GraspServer, check_target_pose
except ImportError as exc:
    pytest.skip(str(exc), allow_module_level=True)


@pytest.fixture
def server():
    rclpy.init()
    node = GraspServer()
    node._select("red")
    yield node
    node.destroy_node()
    rclpy.shutdown()


def fix(server):
    msg = PointStamped()
    msg.header.frame_id = "base_footprint"
    msg.header.stamp = server.get_clock().now().to_msg()
    msg.point.x, msg.point.y, msg.point.z = 0.149, 0.0, 0.128
    return msg


def test_missing_fix_never_falls_back_to_nominal(server):
    assert server._target_pose() is None


def test_valid_fix_and_colour_change_invalidate_previous_target(server):
    server._on_fix(fix(server))
    assert server._target_pose() == (0.149, 0.0)
    server._select("blue")
    assert server._target_pose() is None


@pytest.mark.parametrize(
    "fault", ["frame", "nan", "future", "stale", "height"]
)
def test_invalid_fix_clears_previous_valid_fix(server, fault):
    msg = fix(server)
    server._on_fix(msg)
    if fault == "frame":
        msg.header.frame_id = "camera_optical_frame"
    elif fault == "nan":
        msg.point.x = float("nan")
    elif fault == "future":
        msg.header.stamp.sec += 10
    elif fault == "stale":
        msg.header.stamp.sec -= 121
    else:
        msg.point.z = 4.0
    server._on_fix(msg)
    assert server._target_pose() is None


def test_nonfinite_y_cannot_pass_the_grasp_window():
    assert check_target_pose("red", 0.149, float("nan")) is not None


def test_unavailable_lift_and_release_measurements_fail(server, monkeypatch):
    monkeypatch.setattr(server, "target_height", lambda: None)
    server._grasp_z = None
    assert not server.grasp_magnet()
    assert not server.check_lifted()
    assert not server.check_released()


@pytest.mark.parametrize('simulator', ['gazebo', 'isaac'])
def test_nonfinite_height_cannot_verify_a_grasp(server, monkeypatch, simulator):
    import time
    import arm_control

    server.simulator = simulator
    monkeypatch.setattr(arm_control, 'model_z', lambda _: float('nan'))
    server._heights[server.magnet_model] = (float('nan'), time.monotonic())
    assert server.target_height() is None


@pytest.mark.parametrize('height', [-.011, .079, 99.0])
def test_simulator_height_cache_cannot_verify_a_release(server, height):
    import time

    server._heights[server.magnet_model] = (height, time.monotonic())
    server._grasp_z = 0.0
    assert server.target_height() is None
    assert not server.grasp_magnet()
    assert not server.check_lifted()
    assert not server.check_released()


def test_open_failure_leaves_physical_attachment_intact(server, monkeypatch):
    server._holding = True
    server.poses['grasp'] = [0.277058, 0.516736]
    calls = []
    monkeypatch.setattr(server.move_client, 'wait_for_server', lambda **kw: True)
    monkeypatch.setattr(server, 'check_robot_pose', lambda *a, **kw: True)
    monkeypatch.setattr(server, 'publish_scene', lambda _: None)
    monkeypatch.setattr(server, 'move_arm', lambda *a, **kw: True)
    monkeypatch.setattr(server, 'move_gripper', lambda *a, **kw: False)
    monkeypatch.setattr(server, 'magnet', lambda want: calls.append(want))
    assert not server._do_place()
    assert server.holding
    assert calls == []


def test_gripper_render_pause_does_not_count_as_physical_stall(monkeypatch):
    from types import SimpleNamespace
    import arm_control

    wall = [0.0]
    ticks = [0]
    logs = []
    joints = {name: .4 * sign for name, sign in zip(
        arm_control.GRIPPER_JOINTS, (1, -1))}
    node = SimpleNamespace(
        _joints=joints, _joint_at=0.0,
        grip_pub=SimpleNamespace(publish=lambda _: None),
        get_logger=lambda: SimpleNamespace(info=logs.append, error=logs.append),
        get_clock=lambda: SimpleNamespace(now=lambda: SimpleNamespace(nanoseconds=0)))

    def pump(_):
        wall[0] += .1
        ticks[0] += 1
        node._joint_at = wall[0]
        if ticks[0] >= 10:
            node._joints.update(zip(arm_control.GRIPPER_JOINTS, (.5, -.5)))

    node.pump = pump
    monkeypatch.setattr(arm_control, 'time', SimpleNamespace(monotonic=lambda: wall[0]))
    assert arm_control.ArmControl.move_gripper(node, (.5, -.5), 'open') is True
    assert not any('stalled' in line for line in logs)


def test_attachment_failure_emits_no_magnet_command(server, monkeypatch):
    def forbidden_command(*args, **kwargs):
        raise AssertionError('Missing observation must not issue attachment')

    monkeypatch.setattr(server, 'magnet', forbidden_command)
    assert not server.grasp_magnet()
    assert server._grasp_z is None


def test_missing_or_stale_imu_cannot_be_replaced_by_planar_encoder_attitude(server):
    import time
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import Imu

    odom = Odometry()
    odom.header.frame_id, odom.child_frame_id = 'odom', 'base_footprint'
    odom.pose.pose.orientation.w = 1.0
    server._odom_cb(odom)
    assert not server.check_robot_pose('no attitude', expect_xy=None)
    imu = Imu()
    imu.orientation.w = 1.0
    server._imu_cb(imu)
    assert server.check_robot_pose('upright', expect_xy=None)
    server._imu_at = time.monotonic() - 3
    assert not server.check_robot_pose('stale attitude', expect_xy=None)


def measured_height(server, height=.079):
    from coco_config.object_observation import HEIGHT_SCHEMA
    now=server.get_clock().now().nanoseconds
    return dict(schema=HEIGHT_SCHEMA, valid=True, reason='VALID', units='m',
        colour='red',stamp_ns=now,depth_stamp_ns=now,frame_id='base_footprint',
        source_frame='camera_optical_frame',track_id='observed-red-1',reference_id='support-1',
        center_m=[.153,0.,height],support_height_m=0.,
        center_height_above_support_m=height,uncertainty_m=.002,transform_valid=True,
        depth_sample_count=200,inlier_count=200,valid_fraction=1.,measured_radius_m=.01,measured_axis_extent_m=.158)


def test_measured_observation_enables_baseline_without_privileged_input(server,monkeypatch):
    import json
    from std_msgs.msg import String
    calls=[]
    monkeypatch.setattr(server,'magnet',lambda state:calls.append(state) or True)
    o=measured_height(server)
    server._on_object_height(String(data=json.dumps(o)))
    assert server.target_height()==pytest.approx(.079)
    assert server.grasp_magnet()
    assert calls==['attached']
    # A later independent height needs the same measured support/association.
    raised=measured_height(server,.12)
    server._on_object_height(String(data=json.dumps(raised)))
    assert server.check_lifted()


@pytest.mark.parametrize('fault',['stale','wrong_frame','wrong_target','invalid','nan','replayed'])
def test_observation_consumer_rejects_invalid_inputs(server,fault,monkeypatch):
    import json
    from std_msgs.msg import String
    o=measured_height(server)
    if fault=='stale':o['stamp_ns']-=1_000_000_000;o['depth_stamp_ns']=o['stamp_ns']
    if fault=='wrong_frame':o['frame_id']='world'
    if fault=='wrong_target':o['colour']='blue'
    if fault=='invalid':o['valid']=False
    if fault=='nan':o['center_height_above_support_m']=float('nan')
    if fault=='replayed':server._height_observation=dict(o)
    server._on_object_height(String(data=json.dumps(o)))
    monkeypatch.setattr(server,'magnet',lambda _:pytest.fail('invalid measurement attached'))
    assert server.target_height() is None
    assert not server.grasp_magnet()


def test_lift_requires_new_sample_same_track_and_uncertainty_margin(server,monkeypatch):
    import json
    from std_msgs.msg import String
    monkeypatch.setattr(server,'magnet',lambda _:True)
    o=measured_height(server)
    server._on_object_height(String(data=json.dumps(o)));assert server.grasp_magnet()
    assert not server.check_lifted()  # baseline reused, not lift
    raised=measured_height(server,.111)
    server._on_object_height(String(data=json.dumps(raised)))
    assert not server.check_lifted()  # 32mm mean rise minus4mm uncertainty <30mm
    raised=measured_height(server,.14);raised['track_id']='other-red'
    server._on_object_height(String(data=json.dumps(raised)))
    assert not server.check_lifted()


def test_phase_transition_clears_live_height_but_keeps_historical_baseline(server,monkeypatch):
    import json
    from std_msgs.msg import String
    monkeypatch.setattr(server,'magnet',lambda _:True)
    o=measured_height(server)
    server._on_object_height(String(data=json.dumps(o)))
    assert server.grasp_magnet()
    server.begin_observation_phase('lift')
    assert server.target_height() is None
    assert server._grasp_observation==o
    server._on_object_height(String(data=json.dumps(o)))
    assert server.target_height() is None
    raised=measured_height(server,.12)
    server._on_object_height(String(data=json.dumps(raised)))
    assert server.check_lifted()


def test_release_compares_to_measured_baseline_with_both_uncertainties(server,monkeypatch):
    import json
    from std_msgs.msg import String
    monkeypatch.setattr(server,'magnet',lambda _:True)
    baseline=measured_height(server,.11)
    server._on_object_height(String(data=json.dumps(baseline)))
    assert server.grasp_magnet()
    server.begin_observation_phase('post_release')
    assert not server.check_released()
    returned=measured_height(server,.11)
    server._on_object_height(String(data=json.dumps(returned)))
    assert server.check_released()
    borderline=measured_height(server,.128)
    server._on_object_height(String(data=json.dumps(borderline)))
    assert not server.check_released()  # 18mm difference + 4mm sensing budget >20mm


def test_acceptance_diagnostic_preserves_sample_and_cannot_change_decision(server,monkeypatch):
    import json
    from std_msgs.msg import String
    captured=[]
    class Publisher:
        def publish(self,msg):captured.append(json.loads(msg.data))
    server._observation_diagnostics=Publisher()
    o=measured_height(server);server._on_object_height(String(data=json.dumps(o)))
    assert server.target_height()==pytest.approx(.079)
    assert captured[0]['observation']==o
    assert captured[0]['accepted_by']=='ArmControl.target_height'
    server.target_height();assert len(captured)==1
    class BrokenPublisher:
        def publish(self,msg):raise RuntimeError('diagnostic unavailable')
    server._observation_diagnostics=BrokenPublisher();server._last_observation_diagnostic=None
    assert server.target_height()==pytest.approx(.079)
    invalid=dict(o,valid=False);server._on_object_height(String(data=json.dumps(invalid)))
    assert server.target_height() is None
