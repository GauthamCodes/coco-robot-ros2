"""Bounded, read-only recorder for far-region causal diagnosis.

No manifest input, action goals or wheel publishers. Receive epoch and ROS
time on every record; retain message stamps separately. Camera geometry is
recomputed with the shipped default perception policy and labelled as such.
Actual perception status/detections are recorded independently.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import signal
import time

import cv2
from cv_bridge import CvBridge
import numpy as np
import rclpy
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from rclpy.time import Time
from action_msgs.msg import GoalStatusArray
from geometry_msgs.msg import PoseWithCovarianceStamped, TwistStamped
from lifecycle_msgs.srv import GetState
from nav2_msgs.msg import BehaviorTreeLog, Costmap
from nav_msgs.msg import OccupancyGrid, Odometry, Path as NavPath
from rcl_interfaces.msg import Log
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener
from vision_msgs.msg import Detection3DArray

from coco_config.robot import target_by_colour
from coco_perception import target_pose as tp
from coco_perception.target_finder import blob_stats, colour_mask, match_depth


def stamp(msg):
    return msg.header.stamp.sec * 10**9 + msg.header.stamp.nanosec


def pose(p):
    q = p.orientation
    return dict(xyz=[p.position.x, p.position.y, p.position.z],
                quaternion=[q.x, q.y, q.z, q.w],
                yaw=math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--seconds', type=float, default=1530)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('coco25_diagnostic_trace', parameter_overrides=[
        Parameter('use_sim_time', value=True)])
    bridge = CvBridge()
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    trace = gzip.open(args.output/'diagnostic.jsonl.gz', 'wt')
    grids = gzip.open(args.output/'costmaps.jsonl.gz', 'wt')
    latest, context, depths, maps, digests = {}, {}, {}, {}, {}
    captured, subscriptions = set(), []
    start = time.monotonic()
    stopped = False

    def stop(*_):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def record(topic, data, destination=trace):
        destination.write(json.dumps(dict(
            wall_epoch_ns=time.time_ns(), wall_elapsed_s=time.monotonic()-start,
            sim_ns=node.get_clock().now().nanoseconds, topic=topic, data=data),
            allow_nan=False)+'\n')
        destination.flush()

    def sub(kind, topic, cb, qos=10):
        subscriptions.append(node.create_subscription(kind, topic, cb, qos))

    def status(msg, topic):
        context[topic] = msg.data
        record(topic, msg.data)

    for topic in ['/mission/state', '/mission/search_region', '/mission/mode',
                  '/mission/target_colour', '/localization/health',
                  '/ramp/status', '/cmd_vel_arbiter/status',
                  '/perception/target_pose/status']:
        sub(String, topic, lambda m, t=topic: status(m, t))

    def amcl(msg, topic):
        record(topic, dict(stamp_ns=stamp(msg), frame=msg.header.frame_id,
                           **pose(msg.pose.pose), covariance=list(msg.pose.covariance)))

    latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    sub(PoseWithCovarianceStamped, '/amcl_pose', lambda m: amcl(m, '/amcl_pose'), latched)
    sub(PoseWithCovarianceStamped, '/initialpose', lambda m: amcl(m, '/initialpose'))

    def odom(msg, topic):
        v = msg.twist.twist
        latest[topic] = dict(stamp_ns=stamp(msg), frame=msg.header.frame_id,
                             **pose(msg.pose.pose), linear=[v.linear.x, v.linear.y, v.linear.z],
                             angular=[v.angular.x, v.angular.y, v.angular.z])

    for topic in ['/diff_drive_controller/odom', '/model/coco/odometry']:
        sub(Odometry, topic, lambda m, t=topic: odom(m, t), qos_profile_sensor_data)
    for topic in ['/cmd_vel_nav', '/cmd_vel_smoothed', '/cmd_vel', '/cmd_vel_gated',
                  '/cmd_vel_rl', '/cmd_vel_approach', '/diff_drive_controller/cmd_vel']:
        sub(TwistStamped, topic, lambda m, t=topic: latest.update({t: dict(
            stamp_ns=stamp(m), v=m.twist.linear.x, w=m.twist.angular.z)}))

    def action_status(msg, topic):
        record(topic, [dict(uuid=bytes(s.goal_info.goal_id.uuid).hex(), status=s.status,
                            goal_stamp_ns=s.goal_info.stamp.sec*10**9+s.goal_info.stamp.nanosec)
                       for s in msg.status_list])

    for action in ['navigate_to_pose', 'compute_path_to_pose', 'follow_path']:
        topic = '/'+action+'/_action/status'
        sub(GoalStatusArray, topic, lambda m, t=topic: action_status(m, t),
            QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL))

    sub(BehaviorTreeLog, '/behavior_tree_log', lambda m: record('/behavior_tree_log', [
        dict(node=e.node_name, previous=e.previous_status, current=e.current_status,
             stamp_ns=e.timestamp.sec*10**9+e.timestamp.nanosec) for e in m.event_log]))

    def rosout(msg):
        if msg.name in ('mission_executive', 'planner_server', 'bt_navigator',
                        'controller_server', 'amcl'):
            if (msg.level >= Log.WARN or msg.name == 'mission_executive' or
                    any(k in msg.msg.lower() for k in ('goal', 'path', 'initial', 'pose'))):
                record('/rosout', dict(name=msg.name, level=msg.level, text=msg.msg,
                                      stamp_ns=msg.stamp.sec*10**9+msg.stamp.nanosec))
    sub(Log, '/rosout', rosout, QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    sub(NavPath, '/plan', lambda m: record('/plan', dict(stamp_ns=stamp(m),
        frame=m.header.frame_id, xy=[[p.pose.position.x, p.pose.position.y] for p in m.poses])))

    def grid(msg, topic, raw=False):
        info = msg.metadata if raw else msg.info
        width = info.size_x if raw else info.width
        height = info.size_y if raw else info.height
        data = np.asarray(msg.data, dtype=np.int16).reshape(height, width)
        digest = hashlib.sha256(data.tobytes()).hexdigest()
        meta = dict(stamp_ns=stamp(msg), frame=msg.header.frame_id,
                    width=width, height=height, resolution=info.resolution,
                    origin=pose(info.origin), digest=digest,
                    encoding='nav2_uint8' if raw else 'occupancy_int8')
        maps[topic] = (meta, data)
        if digests.get(topic) != digest:
            record(topic, dict(**meta, data=data.ravel().tolist()), grids)
            digests[topic] = digest

    for topic in ['/global_costmap/costmap', '/local_costmap/costmap', '/map']:
        sub(OccupancyGrid, topic, lambda m, t=topic: grid(m, t), latched)
    for topic in ['/global_costmap/costmap_raw', '/local_costmap/costmap_raw']:
        sub(Costmap, topic, lambda m, t=topic: grid(m, t, True), latched)

    def tf_record(target, source, when=Time()):
        try:
            tf = buffer.lookup_transform(target, source, when)
            t = tf.transform
            q = t.rotation
            return dict(stamp_ns=stamp(tf), xyz=[t.translation.x, t.translation.y, t.translation.z],
                        quaternion=[q.x, q.y, q.z, q.w], available=True)
        except Exception as exc:
            return dict(available=False, error=str(exc))

    def sample():
        transforms = {s: tf_record('map', s) for s in ['base_footprint', 'odom']}
        p = transforms['base_footprint'].get('xyz')
        patches = {}
        if p:
            for topic, (meta, data) in maps.items():
                origin = meta['origin']
                dx, dy = p[0]-origin['xyz'][0], p[1]-origin['xyz'][1]
                yaw = origin['yaw']
                x = math.floor((math.cos(yaw)*dx+math.sin(yaw)*dy)/meta['resolution'])
                y = math.floor((-math.sin(yaw)*dx+math.cos(yaw)*dy)/meta['resolution'])
                inside = 0 <= x < meta['width'] and 0 <= y < meta['height']
                patches[topic] = dict(**meta, cell=[x, y],
                    cost=int(data[y, x]) if inside else None,
                    patch_origin=[max(0, x-5), max(0, y-5)],
                    patch=data[max(0,y-5):max(0,y+6), max(0,x-5):max(0,x+6)].tolist() if inside else [])
        record('sample', dict(context=context, motion=latest, tf=transforms, costmaps=patches))

    sub(CameraInfo, '/camera/camera_info', lambda m: context.update(
        intrinsics=[m.k[0], m.k[4], m.k[2], m.k[5]], camera_frame=m.header.frame_id), qos_profile_sensor_data)

    def depth(msg):
        depths[stamp(msg)] = bridge.imgmsg_to_cv2(msg, desired_encoding='32FC1')
        for k in sorted(depths)[:-5]:
            del depths[k]
    sub(Image, '/camera/depth/image_raw', depth, qos_profile_sensor_data)
    sub(Detection3DArray, '/perception/target_pose', lambda m: record('/perception/target_pose',
        dict(stamp_ns=stamp(m), frame=m.header.frame_id, accepted=bool(m.detections),
             poses=[pose(d.bbox.center) for d in m.detections])))

    def rgb(msg):
        if 'SEARCH_TARGET' not in context.get('/mission/state', ''):
            return
        intrinsics = context.get('intrinsics')
        if intrinsics is None:
            record('candidate', dict(stamp_ns=stamp(msg), error='NO_CAMERA_INFO'))
            return
        key = stamp(msg)
        matched = match_depth(key, list(depths), .1)
        colour = context.get('/mission/target_colour', 'red')
        target = target_by_colour(colour)
        image = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        mask = colour_mask(cv2.cvtColor(image, cv2.COLOR_BGR2HSV), colour)
        blobs, labels = blob_stats(mask)
        candidates = []
        for area, u, v, width, height, label in blobs:
            values = None if matched is None else depths[matched][labels == label]
            estimate = None if values is None else tp.depth_statistics(values, .15, 2., target.diameter/2)
            expected = None if estimate is None else tp.expected_width_px(target.diameter, estimate.axis, intrinsics[0])
            reason = tp.DEPTH_INVALID if estimate is None else (
                tp.VALID if tp.plausible_width(width, target.diameter, estimate.axis, intrinsics[0]) else tp.IMPLAUSIBLE_SIZE)
            finite = np.array([]) if values is None else values[np.isfinite(values)]
            candidates.append(dict(label=label, area=area, uv=[u, v], width=width, height=height,
                surface_m=estimate.surface if estimate else None, axis_m=estimate.axis if estimate else None,
                valid_fraction=estimate.valid_fraction if estimate else None,
                spread_m=estimate.spread if estimate else None,
                depth_quantiles_m=np.quantile(finite, [.1,.5,.9]).tolist() if finite.size else [],
                expected_width_px=expected, width_ratio=width/expected if expected else None,
                implied_diameter_m=width*estimate.axis/intrinsics[0] if estimate else None,
                optical_xyz=list(tp.deproject(u,v,estimate.axis,*intrinsics)) if estimate else None,
                geometry_reason=reason, width_gate_passed=reason == tp.VALID))
        tf = tf_record('base_footprint', 'camera_optical_frame', Time(nanoseconds=key))
        record('candidate', dict(stamp_ns=key, depth_stamp_ns=matched, frame=msg.header.frame_id,
            colour=colour, region=context.get('/mission/search_region'), intrinsics=intrinsics,
            target_diameter_m=target.diameter, policy=dict(near=.15,far=2.,width_tolerance=.5),
            candidates=candidates, tf=tf, actual_status=context.get('/perception/target_pose/status')))
        # One raw frame per region and geometry outcome, rather than camera streams.
        signature = (context.get('/mission/search_region'), tuple(c['geometry_reason'] for c in candidates))
        if signature not in captured and len(captured) < 24:
            captured.add(signature)
            folder = args.output/'diagnostic_images'
            folder.mkdir(exist_ok=True)
            name = str(key)
            cv2.imwrite(str(folder/(name+'.png')), image)
            if matched is not None:
                np.savez_compressed(folder/(name+'.npz'), depth=depths[matched], mask=mask,
                                    intrinsics=intrinsics, stamp_ns=key, depth_stamp_ns=matched)
    sub(Image, '/camera/image_raw', rgb, qos_profile_sensor_data)

    clients = {name: node.create_client(GetState, '/'+name+'/get_state')
               for name in ['planner_server', 'controller_server', 'bt_navigator']}
    pending = set()

    def lifecycle():
        for name, client in clients.items():
            record('action_server', dict(name=name, lifecycle_service_ready=client.service_is_ready()))
            if name not in pending and client.service_is_ready():
                pending.add(name)
                def done(future, n=name):
                    pending.discard(n)
                    result = future.result()
                    record('lifecycle', dict(name=n, state=result.current_state.label if result else None))
                client.call_async(GetState.Request()).add_done_callback(done)
    node.create_timer(.2, sample, clock=rclpy.clock.Clock())
    node.create_timer(5., lifecycle, clock=rclpy.clock.Clock())
    record('recorder', dict(policy='shipped defaults; recomputed candidates, actual verdicts separate',
                            sample_wall_hz=5, max_saved_camera_frames=24))
    try:
        while rclpy.ok() and not stopped and time.monotonic()-start < args.seconds:
            rclpy.spin_once(node, timeout_sec=.1)
    finally:
        record('recorder_end', dict(stopped=stopped))
        trace.close()
        grids.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
