#!/usr/bin/env python3
"""Synthetic CAD ray probe; never a simulator/observation qualification proof.

Uses current URDF visual triangles and joint FK, plus Isaac's primitive chassis.
Object geometry is fixture truth ONLY. Nothing here publishes to ROS/autonomy.
"""
import ast
import json
import math
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation
from scipy.spatial import ConvexHull
import xacro

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'coco_config'), str(ROOT / 'coco_moveit_config/scripts')]
from coco_config import robot as r
import arm_ik


def constants(path, names):
    result = {}
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    result[target.id] = ast.literal_eval(node.value)
    return result


def origin(element):
    node = element.find('origin')
    t = np.eye(4)
    if node is not None:
        t[:3, 3] = list(map(float, node.get('xyz', '0 0 0').split()))
        t[:3, :3] = Rotation.from_euler('xyz', list(map(float, node.get('rpy', '0 0 0').split()))).as_matrix()
    return t


def transforms(tree, joints):
    result = {'base_footprint': np.eye(4)}
    pending = list(tree.findall('joint'))
    while pending:
        progressed = False
        for joint in pending[:]:
            parent = joint.find('parent').get('link')
            if parent not in result:
                continue
            t = origin(joint)
            q = joints.get(joint.get('name'), 0.)
            if joint.get('type') in ('revolute', 'continuous'):
                axis = np.array(list(map(float, joint.find('axis').get('xyz').split())))
                t[:3, :3] = t[:3, :3] @ Rotation.from_rotvec(q * axis / np.linalg.norm(axis)).as_matrix()
            result[joint.find('child').get('link')] = result[parent] @ t
            pending.remove(joint)
            progressed = True
        if not progressed:
            raise ValueError('Unresolved URDF chain')
    return result


def moved(points, transform):
    return points @ transform[:3, :3].T + transform[:3, 3]


def box_triangles(size):
    pts = np.array([[x, y, z] for x in [-.5, .5] for y in [-.5, .5] for z in [-.5, .5]]) * size
    return pts[ConvexHull(pts).simplices]


def meshes(tree, tf):
    result = []
    for link in tree.findall('link'):
        name = link.get('name')
        if name in ('camera_link', 'camera_optical_frame'):
            continue  # The old sensor is relocated, not left as an occluder.
        for visual in link.findall('visual'):
            source = visual.find('geometry/mesh')
            t = tf[name] @ origin(visual)
            if source is not None:
                path = ROOT / source.get('filename').replace('package://', '')
                raw = path.read_bytes()
                n = struct.unpack_from('<I', raw, 80)[0]
                dtype = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')])
                tri = np.frombuffer(raw, dtype=dtype, count=n, offset=84)['vertices'].astype(float)
                tri *= np.array(list(map(float, source.get('scale', '1 1 1').split())))
            else:
                box = visual.find('geometry/box')
                cylinder = visual.find('geometry/cylinder')
                if box is not None:
                    size = list(map(float, box.get('size').split()))
                elif cylinder is not None:
                    size = [2 * float(cylinder.get('radius'))] * 2 + [float(cylinder.get('length'))]
                else:
                    raise ValueError('Unmodeled visual: ' + name)
                tri = box_triangles(size)  # conservative for non-mesh cylinders
            result.append((name, moved(tri.reshape(-1, 3), t).reshape(-1, 3, 3)))
    # Isaac base visual is this solid cube instead of Gazebo's base CAD mesh.
    t = tf['base_link'].copy()
    t[:3, 3] += [0., 0., r.CHASSIS_SIZE[2] / 2]
    result.append(('isaac_chassis', moved(box_triangles(r.CHASSIS_SIZE).reshape(-1, 3), t).reshape(-1, 3, 3)))
    return [(name, prepare(tri)) for name, tri in result]


def prepare(tri):
    return (tri[:, 0], tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0],
            tri.min((0, 1)), tri.max((0, 1)))


def intersects(start, end, triangles):
    """Two-sided segment/triangle intersection; epsilon is numerical, not a gate."""
    d = end - start
    v0, e1, e2, mins, maxs = prepare(triangles) if isinstance(triangles, np.ndarray) else triangles
    enter, leave = 0., 1.
    for axis in range(3):
        if d[axis] == 0:
            if not mins[axis] <= start[axis] <= maxs[axis]:
                return False
        else:
            a, b = sorted([(mins[axis] - start[axis]) / d[axis],
                           (maxs[axis] - start[axis]) / d[axis]])
            enter, leave = max(enter, a), min(leave, b)
            if enter > leave:
                return False
    h = np.cross(d, e2)
    a = np.einsum('ij,ij->i', e1, h)
    good = np.abs(a) > np.finfo(float).eps
    inv = np.zeros_like(a)
    inv[good] = 1. / a[good]
    s = start - v0
    u = inv * np.einsum('ij,ij->i', s, h)
    q = np.cross(s, e1)
    v = inv * (q @ d)
    along = inv * np.einsum('ij,ij->i', e2, q)
    return bool(np.any(good & (u >= 0) & (v >= 0) & (u + v <= 1) & (along > 0) & (along < 1)))


def stage_fixtures(tree):
    poses = constants(ROOT / 'coco_moveit_config/scripts/grasp_server.py', ['POSES'])['POSES']
    grips = constants(ROOT / 'coco_moveit_config/scripts/arm_control.py', ['GRIP_OPEN', 'GRIP_CLOSED'])
    result = []
    # All colours, both ends of the accepted grasp-axis window, lateral extremes.
    for colour in r.TARGET_COLOURS:
        radius = r.target_by_colour(colour).diameter / 2
        for x in r.approach_window(colour):
            for y in [-r.GRASP_MAX_LATERAL, r.GRASP_MAX_LATERAL]:
                grasp = arm_ik.ik_or_none(x, r.TARGET_GRASP_Z)
                assert grasp is not None
                def fk(q, finger):
                    return transforms(tree, dict(zip(['m_link1_Revolute-6', 'm_link2_Revolute-7', 'm_link3_Revolute-8', 'm_link3_Revolute-9'], [*q, *finger])))
                baseline = fk(grasp, grips['GRIP_OPEN'])
                target = np.eye(4)
                target[:3, 3] = [x, y, r.TARGET_HEIGHT / 2]
                for stage, q, finger, attached in [
                    ('baseline', grasp, grips['GRIP_OPEN'], False),
                    ('raised_attached', poses['raise'], grips['GRIP_CLOSED'], True),
                    ('raised_failed_grasp', poses['raise'], grips['GRIP_CLOSED'], False),
                    ('released_retreat', poses['lift'], grips['GRIP_OPEN'], False),
                    ('retained_retreat', poses['lift'], grips['GRIP_OPEN'], True)]:
                    tf = fk(q, finger)
                    object_tf = tf['m_link3'] @ np.linalg.inv(baseline['m_link3']) @ target if attached else target
                    # Box corners enclose the entire tilted target for a conservative frustum test.
                    corners = moved(np.array([[a, b, c] for a in [-radius, radius] for b in [-radius, radius] for c in [-r.TARGET_HEIGHT / 2, r.TARGET_HEIGHT / 2]]), object_tf)
                    result.append(dict(colour=colour, x=x, y=y, stage=stage, radius=radius, object_tf=object_tf, corners=corners, tf=tf))
    return result


def view(camera, corners):
    delta = corners - camera
    az = np.arctan2(delta[:, 1], delta[:, 0])
    if az.max() - az.min() > r.CAMERA_HFOV:
        return None
    yaw = (az.min() + az.max()) / 2
    yaw_rotation = Rotation.from_euler('z', yaw).as_matrix()
    v = delta @ yaw_rotation
    elev = np.arctan2(v[:, 2], v[:, 0])
    pitch = -(elev.min() + elev.max()) / 2
    rotation = Rotation.from_euler('xyz', [0., pitch, yaw]).as_matrix()
    local = delta @ rotation
    vfov = 2 * math.atan(math.tan(r.CAMERA_HFOV / 2) * r.CAMERA_WH[1] / r.CAMERA_WH[0])
    ok = ((local[:, 0] >= .15) & (np.abs(local[:, 1] / local[:, 0]) <= math.tan(r.CAMERA_HFOV / 2)) & (np.abs(local[:, 2] / local[:, 0]) <= math.tan(vfov / 2)))
    return (pitch, yaw, float(local[:, 0].min())) if ok.all() else None


def run(output, refine=False):
    tree = ET.fromstring(xacro.process_file(str(ROOT / 'gazebo_models/urdf/coco_robo2.xacro')).toxml())
    fixtures = stage_fixtures(tree)
    # Forward acquisition volume is a diagnostic constraint, not changed scene placement.
    acquisition = np.array([[x, y, z] for x in [.6, 2.] for y in [-.016, .016] for z in [0., r.TARGET_HEIGHT]])
    corners = np.concatenate([f['corners'] for f in fixtures] + [acquisition])
    candidates = []
    # Hypothesis: the 50 mm grid misses flank views clearing the front chassis.
    # Grid resolution is diagnostic sampling, never an autonomy tolerance.
    xs = [.05, .06, .07, .08, .09, .1] if refine else [-.2, -.15, -.1, -.05, 0., .05, .1, .125, .15]
    ys = [-.35, -.3, -.25, -.2, .2, .25, .3, .35] if refine else [-.25, -.2, -.15, -.1, 0., .1, .15, .2, .25]
    zs = [.25, .3, .35, .4, .45, .5] if refine else [.08, .1, .15, .2, .25, .3, .35, .4]
    for x in xs:
        for y in ys:
            for z in zs:
                camera = np.array([x, y, z])
                projection = view(camera, corners)
                if projection is not None:
                    candidates.append((float(np.linalg.norm(camera - r.CAMERA_XYZ)), camera, projection))
    candidates.sort(key=lambda item: item[0])
    # Nominal middle-axis blue target for mesh-ray screening, not an all-volume proof.
    screen = [f for f in fixtures if f['colour'] == 'blue' and f['x'] == r.approach_window('blue')[0] and f['y'] == -r.GRASP_MAX_LATERAL]
    scenes = [(f, meshes(tree, f['tf'])) for f in screen]
    tested = []
    for displacement, camera, projection in candidates:
        stages = []
        for f, scene in scenes:
            inv = np.linalg.inv(f['object_tf'])
            c = moved(camera[None, :], inv)[0]
            angle = math.atan2(c[1], c[0])
            # Three camera-facing surface rays at each end and the middle.
            pts = np.array([[f['radius'] * math.cos(a), f['radius'] * math.sin(a), z]
                for z in [-r.TARGET_HEIGHT / 2, 0., r.TARGET_HEIGHT / 2]
                for a in [angle - math.pi / 6, angle, angle + math.pi / 6]])
            pts = moved(pts, f['object_tf'])
            blockers = [[name for name, tri in scene if intersects(camera, end, tri)] for end in pts]
            stages.append(dict(stage=f['stage'], blocked_rays=sum(bool(b) for b in blockers), total_rays=len(pts), blockers=blockers))
        tested.append(dict(camera_base_footprint_m=camera.tolist(), displacement_m=displacement,
                           rpy_rad=[0., *projection[:2]], min_optical_depth_m=projection[2], stages=stages))
        if sum(all(s['blocked_rays'] == 0 for s in t['stages']) for t in tested) >= 3:
            break
    result = dict(kind='SYNTHETIC_CAD_SCREEN_NOT_RUNTIME', grid_candidates=len(xs)*len(ys)*len(zs), grid_xyz=[xs, ys, zs],
                  frustum_candidates=len(candidates), screened_candidates=tested,
                  limitations=['Discrete placement grid, not a minimum-mount optimization proof',
                               'Frustum volumes include all colours/window extremes; mesh rays cover one blue window corner only',
                               'Sparse rays cannot certify full mask/end visibility or uncertainty',
                               'No camera body clearance or trajectory swept-volume certificate',
                               'No rendered RGB-D, timing, TF delivery, sensor noise, or physical attachment evidence',
                               'Ideal rigid attachment is a fixture hypothesis, never an autonomy input'],
                  approved_mount=None)
    with Path(output).open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'frustum_candidates':len(candidates), 'screened':len(tested),
        'fully_unblocked_sparse_screens': [t['camera_base_footprint_m'] for t in tested if all(s['blocked_rays'] == 0 for s in t['stages'])]}))


if __name__ == '__main__':
    run(sys.argv[1], refine='--refine' in sys.argv[2:])
