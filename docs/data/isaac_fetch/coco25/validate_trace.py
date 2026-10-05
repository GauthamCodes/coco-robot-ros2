"""Exercise recorder message handling on a private synthetic ROS graph.

This is instrumentation validation, never episode/runtime validation.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np
import rclpy
from rclpy.qos import QoSProfile, DurabilityPolicy
from cv_bridge import CvBridge
from geometry_msgs.msg import TransformStamped, PoseWithCovarianceStamped
from nav2_msgs.msg import Costmap, BehaviorTreeLog, BehaviorTreeStatusChange
from nav_msgs.msg import OccupancyGrid, Odometry
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
from tf2_ros import StaticTransformBroadcaster
from vision_msgs.msg import Detection3DArray
from coco_config.robot import camera_intrinsics, target_by_colour


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    recorder = subprocess.Popen(['python3', str(Path(__file__).with_name('diagnostic_trace.py')),
                                 str(args.output), '--seconds', '8'], env=os.environ)
    rclpy.init()
    node = rclpy.create_node('coco25_synthetic_recorder_validation')
    qos = QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    messages = []

    def add(kind, topic, msg):
        publisher = node.create_publisher(kind, topic, qos)
        messages.append((publisher, msg))

    try:
        clock = Clock()
        clock.clock.sec = 1
        add(Clock, '/clock', clock)
        add(String, '/mission/state', String(data='state=SEARCH_TARGET'))
        add(String, '/mission/search_region', String(data='lane_test'))
        add(String, '/mission/target_colour', String(data='red'))
        tf_pub = StaticTransformBroadcaster(node)
        transforms = []
        for parent, child in [('map', 'odom'), ('odom', 'base_footprint'),
                              ('base_footprint', 'camera_optical_frame')]:
            tf = TransformStamped()
            tf.header.frame_id, tf.child_frame_id = parent, child
            tf.transform.rotation.w = 1.
            transforms.append(tf)
        tf_pub.sendTransform(transforms)
        grid = OccupancyGrid()
        grid.header.frame_id = 'map'
        grid.header.stamp.sec = 1
        grid.info.width = grid.info.height = 20
        grid.info.resolution = .125
        grid.info.origin.position.x = grid.info.origin.position.y = -1.
        grid.info.origin.orientation.w = 1.
        grid.data = [0]*400
        grid.data[168] = 100
        add(OccupancyGrid, '/global_costmap/costmap', grid)
        raw = Costmap()
        raw.header = grid.header
        raw.metadata.size_x = raw.metadata.size_y = 20
        raw.metadata.resolution = .125
        raw.metadata.origin = grid.info.origin
        raw.data = [0]*400
        raw.data[168] = 254
        add(Costmap, '/global_costmap/costmap_raw', raw)
        odom = Odometry()
        odom.header = grid.header
        odom.pose.pose.orientation.w = 1.
        odom.twist.twist.linear.x = .1
        add(Odometry, '/diff_drive_controller/odom', odom)
        amcl = PoseWithCovarianceStamped()
        amcl.header = grid.header
        amcl.pose.pose = odom.pose.pose
        add(PoseWithCovarianceStamped, '/amcl_pose', amcl)
        event = BehaviorTreeStatusChange()
        event.node_name, event.previous_status, event.current_status = 'ComputePathToPose', 'IDLE', 'RUNNING'
        event.timestamp.sec = 1
        bt = BehaviorTreeLog()
        bt.event_log = [event]
        add(BehaviorTreeLog, '/behavior_tree_log', bt)
        detected = Detection3DArray()
        detected.header = grid.header
        add(Detection3DArray, '/perception/target_pose', detected)
        fx, fy, cx, cy = camera_intrinsics()
        info = CameraInfo()
        info.header.frame_id = 'camera_optical_frame'
        info.k = [fx, 0., cx, 0., fy, cy, 0., 0., 1.]
        add(CameraInfo, '/camera/camera_info', info)
        bridge = CvBridge()
        width = round(target_by_colour('red').diameter*fx)
        rgb = np.zeros((480,640,3), dtype=np.uint8)
        rgb[200:280,320:320+width,2] = 255
        depth = bridge.cv2_to_imgmsg(np.ones((480,640), dtype=np.float32), encoding='32FC1')
        depth.header = info.header
        depth.header.stamp.sec = 1
        image = bridge.cv2_to_imgmsg(rgb, encoding='bgr8')
        image.header = depth.header
        add(Image, '/camera/depth/image_raw', depth)
        add(Image, '/camera/image_raw', image)
        deadline = time.monotonic()+4
        while time.monotonic() < deadline:
            for publisher, msg in messages:
                publisher.publish(msg)
            rclpy.spin_once(node, timeout_sec=.1)
        recorder.terminate()
        assert recorder.wait(timeout=10) == 0
        rows = [json.loads(s) for s in gzip.open(args.output/'diagnostic.jsonl.gz', 'rt')]
        candidates = [r['data'] for r in rows if r['topic'] == 'candidate' and r['data'].get('candidates')]
        assert candidates and candidates[-1]['candidates'][0]['width_gate_passed']
        assert candidates[-1]['tf']['available']
        samples = [r['data'] for r in rows if r['topic'] == 'sample' and r['data']['costmaps']]
        assert any(s['costmaps']['/global_costmap/costmap_raw']['cost'] == 254 for s in samples)
        assert any(s['motion'].get('/diff_drive_controller/odom', {}).get('linear') == [.1,0.,0.] for s in samples)
        assert any(r['topic'] == '/behavior_tree_log' for r in rows)
        assert any(r['topic'] == '/amcl_pose' for r in rows)
        assert any(r['topic'] == '/perception/target_pose' for r in rows)
        assert all(r['wall_epoch_ns'] > 0 and r['sim_ns'] >= 0 for r in rows)
        print(json.dumps(dict(passed=True, synthetic_only=True, records=len(rows),
                              candidate_records=len(candidates), costmap_samples=len(samples))))
    finally:
        if recorder.poll() is None:
            recorder.terminate()
            recorder.wait(timeout=10)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
