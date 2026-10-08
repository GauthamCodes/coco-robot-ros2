#!/usr/bin/env python3
"""Diagnostic only: production geometry/approach/grasp, synthetic sensor fixture.

No simulator, executor, motor command or attachment publication is used.
Transport and actuator seams are stubbed; production safety gates are not.
"""
import hashlib
import ast
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
for package in ('coco_config', 'coco_perception', 'custom_teleop'):
    sys.path.insert(0, str(ROOT / package))
sys.path.insert(0, str(ROOT / 'coco_moveit_config/scripts'))
import rclpy
import cv2
import numpy as np
from coco_config import robot as r
from coco_perception import target_pose as tp
from coco_perception import target_finder, candidate_diagnostics
from coco_perception.target_finder import optical_to_base, colour_mask, blob_stats
from coco_perception.candidate_diagnostics import candidates
from custom_teleop import approach_server as approach
from grasp_server import GraspServer, check_target_pose
import arm_control


def run():
    assert os.environ.get('ROS_DOMAIN_ID') == '187', 'Use isolated diagnostic domain 187'
    rclpy.init()
    node = GraspServer()
    try:
        node._select('red')
        intrinsics = r.camera_intrinsics()
        axis = .5 + .8 * r.target_by_colour('red').diameter / 2
        width = r.target_by_colour('red').diameter * intrinsics[0] / axis
        observations = []
        diagnostics = []
        fixture_arrays = {}
        # Two idealized visible bands at the same fixed surface depth.
        # These are synthetic occlusion witnesses, not qualified runtime samples.
        for v in (95., 115.):
            hsv = np.zeros((240, 320, 3), dtype=np.uint8)
            hsv[int(v)-6:int(v)+6, 156:165] = (0, 255, 255)
            bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            depth = np.full((240, 320), np.nan, dtype=np.float32)
            depth[int(v)-6:int(v)+6, 156:165] = .5
            blobs, labels = blob_stats(colour_mask(hsv, 'red'))
            assert len(blobs) == 1
            observation = tp.observe(blobs, lambda label: depth[labels == label], 'red',
                                     intrinsics, .15, 2.)
            observation = tp.transform_observation(
                observation, lambda p: optical_to_base(*p), 'base_footprint')
            assert observation.is_valid
            observations.append({'visible_row': v, 'point': observation.point,
                                 'grasp_point': observation.grasp_point,
                                 'validity': observation.validity})
            diagnostics.extend(candidates(hsv, depth, 'red', intrinsics, .15, 2.,
                                          .5, 1000000000, 'camera_optical_frame',
                                          selected_label=blobs[0][-1],
                                          selected_reason='VALID',
                                          depth_stamp_ns=1000000000))
            fixture_arrays[f'rgb_{int(v)}'] = bgr
            fixture_arrays[f'depth_{int(v)}'] = depth
        np.savez_compressed(Path(__file__).with_name('rgbd_fixture.npz'), **fixture_arrays)
        assert abs(observations[0]['point'][2] - observations[1]['point'][2]) > arm_control.LIFT_MIN_RISE
        assert all(not candidate['touches_image_edge'] for candidate in diagnostics)

        # Execute the real approach phases with deterministic encoder/IMU inputs.
        # _tick integrates commanded linear speed into fixture odometry only.
        # No ROS velocity publisher exists in this fake transport.
        clock = SimpleNamespace(value=1.)
        pose = [0., 0., 0.]
        messages = []
        fake = SimpleNamespace(colour='red', _abort=threading.Event(),
                               _handoff_x=approach.SERVO_HANDOFF_X,
                               _wait_for_inputs=lambda: True,
                               _pose=lambda: tuple(pose), _pitch=lambda: 0.,
                               get_logger=node.get_logger, get_clock=node.get_clock,
                               _publish=lambda *args: None,
                               _estimate_pub=SimpleNamespace(publish=messages.append))
        original_point = observations[0]['point']
        fake._fresh_target = lambda: approach.reproject_target(
            original_point, (0., 0., 0.), tuple(pose))
        def tick(linear, angular):
            assert abs(angular) < 1e-9
            pose[0] += linear * .1
            clock.value += .1
        fake._tick = tick
        saved_time = approach.time
        approach.time = SimpleNamespace(monotonic=lambda: clock.value,
                                        sleep=lambda duration: setattr(
                                            clock, 'value', clock.value + duration))
        try:
            approach.ApproachServer._run_phases(fake)
        finally:
            approach.time = saved_time
        assert fake.outcome == 'arrived', fake.outcome
        assert len(messages) == 1
        fix = messages[0]
        node._on_fix(fix)
        xy = node._target_pose()
        assert xy is not None
        assert check_target_pose('red', *xy) is None

        calls = []
        def actuator(label):
            def call(*args, **kwargs):
                calls.append({'call': label, 'args': list(args)})
                return True
            return call
        node.move_client = SimpleNamespace(wait_for_server=lambda **kw: True)
        node.check_robot_pose = lambda *args, **kw: True
        node.move_arm = actuator('move_arm')
        node.move_gripper = actuator('move_gripper')
        node.remove_scene_objects = actuator('remove_scene_objects')
        node.publish_scene = actuator('publish_scene')
        # Scene values are tested separately in existing tests; avoid serializing
        # ROS collision objects in this diagnostic actuator log.
        node.box = lambda *args: 'ground'
        node.cylinder = lambda *args: 'target'
        node.allow_gripper_target_contact = actuator('allow_contact')
        node.magnet = actuator('MAGNET_MUST_NOT_BE_CALLED')
        pick_result = node._do_pick()
        assert not pick_result and node.phase == 'pick:magnet attach'
        assert not any(c['call'] == 'MAGNET_MUST_NOT_BE_CALLED' for c in calls)
        assert not any(c['call'] == 'move_arm' and c['args'][0] == 'raise' for c in calls)
        visibility = []
        sensor = ET.parse(ROOT / 'gazebo_models/urdf/coco_robo2.xacro').find(
            ".//sensor[@type='rgbd_camera']")
        gazebo_rgb_near = float(sensor.findtext('camera/clip/near'))
        gazebo_depth_near = float(sensor.findtext('camera/depth_camera/clip/near'))
        isaac_ast = ast.parse((ROOT / 'coco_sim/coco_sim/isaac/model.py').read_text())
        clipping = [n for n in ast.walk(isaac_ast) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr == 'CreateClippingRangeAttr']
        assert len(clipping) == 1
        isaac_camera_near = ast.literal_eval(clipping[0].args[0].args[0])
        for colour in ('red', 'green', 'blue', 'yellow'):
            target = r.target_by_colour(colour)
            near, far = r.approach_window(colour)
            # Zero-pitch upright nominal camera: optical forward Z = base X-camera X.
            furthest = far + target.diameter / 2 - r.CAMERA_XYZ[0]
            assert furthest < gazebo_rgb_near and furthest < gazebo_depth_near
            assert furthest < isaac_camera_near and furthest < .15
            visibility.append({'colour': colour, 'grasp_axis_window_m': [near, far],
                               'radius_m': target.diameter / 2,
                               'maximum_optical_forward_depth_m': furthest,
                               'gazebo_rgb_near_m': gazebo_rgb_near,
                               'gazebo_depth_near_m': gazebo_depth_near,
                               'isaac_camera_near_m': isaac_camera_near,
                               'perception_min_range_m': .15,
                               'entire_target_inside_near_planes': True})
        sources = [tp.__file__, target_finder.__file__, candidate_diagnostics.__file__,
                   approach.__file__, arm_control.__file__,
                   ROOT / 'coco_moveit_config/scripts/grasp_server.py',
                   r.__file__, ROOT / 'gazebo_models/urdf/coco_robo2.xacro',
                   ROOT / 'coco_sim/coco_sim/isaac/model.py']
        return {'kind': 'SYNTHETIC_DIAGNOSTIC_NOT_QUALIFIED_RUNTIME',
                'source_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                                     cwd=ROOT, text=True).strip(),
                'ros_domain': os.environ['ROS_DOMAIN_ID'],
                'sources': {str(Path(p).resolve().relative_to(ROOT)):
                            hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources},
                'fixture': {'depth_samples_m': [.5] * 120, 'intrinsics': intrinsics,
                            'blob_width_pixels': width, 'blob_height_pixels': 12,
                            'visible_rows': [95, 115]},
                'perception': observations,
                'candidate_diagnostics': diagnostics,
                'visible_centroid_z_difference_m': abs(
                    observations[0]['point'][2] - observations[1]['point'][2]),
                'approach': {'result': fake.outcome,
                             'frame': fix.header.frame_id,
                             'point': [fix.point.x, fix.point.y, fix.point.z],
                             'production_phases_executed': True},
                'grasp': {'target_height': node.target_height(), 'fix_accepted': True,
                          'window_and_ik_accepted': True, 'pick_result': pick_result,
                          'phase': node.phase, 'outcome': node.outcome,
                          'lift_check': node.check_lifted(),
                          'release_check': node.check_released(), 'actuator_stub_calls': calls},
                'visibility': visibility,
                'limitations': ['Synthetic synchronized geometry, not actual sensor replay',
                                'MoveGroup, upright, scene and actuator transport stubbed',
                                'No physical success, TF timing or simulator claim',
                                'Near-plane proof is for nominal upright grasp geometry']}
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    result = run()
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('result.json')
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'result': result['grasp']['outcome'],
                      'target_height': result['grasp']['target_height']}))
