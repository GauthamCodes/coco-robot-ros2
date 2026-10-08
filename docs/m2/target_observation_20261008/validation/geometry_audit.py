#!/usr/bin/env python3
"""Offline configuration bounds, NOT sensed geometry or a remount certificate."""
import ast
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'coco_config'))
from coco_config import robot as r


def audit():
    xacro_path = ROOT / 'gazebo_models/urdf/coco_robo2.xacro'
    model_path = ROOT / 'coco_sim/coco_sim/isaac/model.py'
    root = ET.parse(xacro_path).getroot()
    sensor = root.find("gazebo[@reference='camera_link']/sensor/camera")
    origin = root.find("joint[@name='camera_joint']/origin")
    mount = tuple(map(float, origin.attrib['xyz'].split()))
    attitude = tuple(map(float, origin.attrib['rpy'].split()))
    assert mount == r.CAMERA_MOUNT_XYZ
    assert attitude == r.CAMERA_RPY == (0., 0., 0.)
    assert r.CAMERA_XYZ == (mount[0], mount[1], mount[2] + r.CHASSIS_GROUND_CLEARANCE)
    isaac_clip = None
    for node in ast.walk(ast.parse(model_path.read_text())):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == 'CreateClippingRangeAttr':
                isaac_clip = [ast.literal_eval(x) for x in node.args[0].args]
    assert isaac_clip == list(r.CAMERA_DEPTH_CLIP)
    width, height = r.CAMERA_WH
    hfov = float(sensor.findtext('horizontal_fov'))
    assert hfov == r.CAMERA_HFOV
    assert (int(sensor.findtext('image/width')), int(sensor.findtext('image/height'))) == (width, height)
    vfov = 2 * math.atan(math.tan(hfov / 2) * height / width)
    current = []
    for colour in r.TARGET_COLOURS:
        radius = r.target_by_colour(colour).diameter / 2
        near, far = r.approach_window(colour)
        # Enclosing-box upper bound: every target surface lies inside this box.
        # Hypothesis is nominal upright rest on the robot's support plane.
        dx = max(abs(near - radius - r.CAMERA_XYZ[0]),
                 abs(far + radius - r.CAMERA_XYZ[0]))
        dy = r.GRASP_MAX_LATERAL + radius + abs(r.CAMERA_XYZ[1])
        dz = max(abs(r.CAMERA_XYZ[2]), abs(r.TARGET_HEIGHT - r.CAMERA_XYZ[2]))
        max_distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        current.append(dict(
            colour=colour, radius_m=radius, grasp_axis_window_m=[near, far],
            max_current_forward_depth_m=far + radius - r.CAMERA_XYZ[0],
            upper_bound_distance_to_any_surface_m=max_distance,
            pitch_yaw_only_cannot_reach_015m_depth=max_distance < .15))
    sources = [xacro_path, model_path, ROOT / 'coco_sim/coco_sim/isaac/runtime.py',
               ROOT / 'coco_config/coco_config/robot.py',
               ROOT / 'coco_perception/coco_perception/target_pose_node.py']
    return dict(
        evidence_kind='OFFLINE_CONFIGURATION_GEOMETRY_NOT_RUNTIME',
        camera_mount_base_link_m=mount, camera_base_footprint_m=r.CAMERA_XYZ,
        camera_rpy_rad=attitude, optical_frame='camera_optical_frame',
        resolution_px=[width, height], horizontal_fov_rad=hfov, vertical_fov_rad=vfov,
        intrinsics=list(r.camera_intrinsics()),
        gazebo_rgb_clip_m=[float(sensor.findtext('clip/near')), float(sensor.findtext('clip/far'))],
        gazebo_depth_clip_m=[float(sensor.findtext('depth_camera/clip/near')), float(sensor.findtext('depth_camera/clip/far'))],
        isaac_clip_m=isaac_clip, acquisition_accepted_depth_m=[.15, 2.],
        current_mount_bounds=current,
        interpretation='For any orientation, optical forward depth is at most Euclidean distance. Even the enclosing-box distance is below the unchanged 0.15 m acceptance bound. Translation is necessary; feasibility after translation is NOT established.',
        proposed_mount=None, rendered_visibility_proven=False,
        limitations=['Nominal upright target on shared support plane only',
                     'No arm/finger occlusion or swept-volume certificate',
                     'No baseline/raise/release sensor frames',
                     'Configured encoding and stamp behavior still require live verification'],
        source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})


if __name__ == '__main__':
    with Path(sys.argv[1]).open('x') as out:
        json.dump(audit(), out, indent=2, allow_nan=False)
        out.write('\n')
