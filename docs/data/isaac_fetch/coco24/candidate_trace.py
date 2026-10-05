"""Read-only candidate size/depth recorder; uses no manifests or wheel publishers.

Run alongside an episode in its sourced ROS environment/domain. Records the
same colour mask/depth statistics as perception but makes no validity decisions
for the mission. Existing nav_snapshot.py captures TF/costmaps separately.
"""
import argparse
import json
import time

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
from coco_config.robot import target_by_colour
from coco_perception.target_finder import blob_stats, colour_mask
from coco_perception import target_pose as tp

parser = argparse.ArgumentParser()
parser.add_argument('output')
parser.add_argument('--seconds', type=float, default=300)
args = parser.parse_args()
rclpy.init()
node = rclpy.create_node('coco24_read_only_candidate_trace')
bridge = CvBridge()
frames = {}
context = {'fx': None, 'selected': 'red', 'mission': None, 'region': None}
out = open(args.output, 'w')


def stamp(msg):
    return msg.header.stamp.sec * 10**9 + msg.header.stamp.nanosec


def depth(msg):
    frames[stamp(msg)] = bridge.imgmsg_to_cv2(msg, desired_encoding='32FC1')
    for key in sorted(frames)[:-5]:
        del frames[key]


def status(msg):
    values = dict(v.split('=', 1) for v in msg.data.split() if '=' in v)
    context['selected'] = values.get('sel', context['selected'])
    context['pose_status'] = msg.data


def rgb(msg):
    if context['fx'] is None or 'SEARCH_TARGET' not in (context['mission'] or ''):
        return
    key = stamp(msg)
    matched = min(frames, key=lambda k: abs(k-key)) if frames else None
    if matched is None or abs(matched-key) > 100_000_000:
        return
    image = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
    mask = colour_mask(cv2.cvtColor(image, cv2.COLOR_BGR2HSV), context['selected'])
    blobs, labels = blob_stats(mask)
    target = target_by_colour(context['selected'])
    candidates = []
    for area, u, v, width, height, label in blobs:
        estimate = tp.depth_statistics(frames[matched][labels == label], .15, 2.,
                                       target.diameter / 2)
        expected = tp.expected_width_px(target.diameter, estimate.axis, context['fx']) if estimate else None
        candidates.append(dict(area=area, uv=[u, v], width=width, height=height,
            axis_m=estimate.axis if estimate else None, expected_width_px=expected,
            width_ratio=width/expected if expected else None))
    out.write(json.dumps(dict(wall_epoch=time.time(), stamp_ns=key,
        depth_stamp_ns=matched, **context, candidates=candidates))+'\n')
    out.flush()


node.create_subscription(Image, '/camera/depth/image_raw', depth, qos_profile_sensor_data)
node.create_subscription(Image, '/camera/image_raw', rgb, qos_profile_sensor_data)
node.create_subscription(CameraInfo, '/camera/camera_info', lambda m: context.update(fx=m.k[0]), qos_profile_sensor_data)
node.create_subscription(String, '/perception/target_pose/status', status, 10)
for topic, key in [('/mission/state', 'mission'), ('/mission/search_region', 'region')]:
    node.create_subscription(String, topic, lambda m, k=key: context.update({k: m.data}), 10)
try:
    deadline = time.monotonic() + args.seconds
    while rclpy.ok() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.1)
finally:
    out.close()
    node.destroy_node()
    rclpy.shutdown()
