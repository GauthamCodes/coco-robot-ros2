#!/usr/bin/env python3
"""Bounded ROS replay of captured sensor bytes; no simulator, no qualification.
Original sensor timestamps, intrinsics and recorded static TF are retained.
"""
import argparse,json,time,subprocess
from pathlib import Path
import cv2,numpy as np,rclpy
from rclpy.parameter import Parameter
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import CameraInfo
from std_msgs.msg import String
from tf2_msgs.msg import TFMessage
from tf2_ros import StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped
from cv_bridge import CvBridge
from coco_perception.object_height_node import ObjectHeightNode
p=argparse.ArgumentParser();p.add_argument('inspection',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
s=json.loads((a.inspection/'sensor_inspection.json').read_text());f=s['frames'][20]
rclpy.init();observer=ObjectHeightNode();observer.set_parameters([Parameter('use_sim_time',value=True)])
source=rclpy.create_node('recorded_rgbd_replay');outputs=[]
source.create_subscription(String,'/perception/object_height',lambda m:outputs.append(json.loads(m.data)),10)
clock=source.create_publisher(Clock,'/clock',10);bridge=CvBridge()
rgbpub=source.create_publisher(type(bridge.cv2_to_imgmsg(np.zeros((1,1,3),dtype=np.uint8),'bgr8')),'/camera/image_raw',qos_profile_sensor_data)
depthpub=source.create_publisher(type(bridge.cv2_to_imgmsg(np.zeros((1,1),dtype=np.float32),'32FC1')),'/camera/depth/image_raw',qos_profile_sensor_data)
infopub=source.create_publisher(CameraInfo,'/camera/camera_info',qos_profile_sensor_data)
broadcaster=StaticTransformBroadcaster(source);tfs=[]
for record in json.loads((a.inspection/'sensor_tf.json').read_text()):
 for t in record['data']['transforms']:
  m=TransformStamped();m.header.frame_id=t['header']['frame_id'];m.child_frame_id=t['child_frame_id']
  for field in ('translation','rotation'):
   for k,v in t['transform'][field].items():setattr(getattr(m.transform,field),k,v)
  tfs.append(m)
broadcaster.sendTransform(tfs)
rgb=bridge.cv2_to_imgmsg(cv2.imread(str(a.inspection/'rgb-020.png')),'bgr8');depth=bridge.cv2_to_imgmsg(np.load(a.inspection/'depth-020.npy').astype(np.float32),'32FC1')
info=CameraInfo();info.width=rgb.width;info.height=rgb.height;info.k=f['camera_info']['k']
for msg,stamp in ((rgb,f['rgb_stamp_ns']),(depth,f['depth_stamp_ns']),(info,f['rgb_stamp_ns'])):
 msg.header.frame_id=f['frame'];msg.header.stamp.sec=stamp//10**9;msg.header.stamp.nanosec=stamp%10**9
executor=SingleThreadedExecutor();executor.add_node(source);executor.add_node(observer)
start=time.monotonic()
while time.monotonic()-start<3:
 c=Clock();c.clock=rgb.header.stamp;clock.publish(c);executor.spin_once(timeout_sec=.02)
for _ in range(30):
 infopub.publish(info);rgbpub.publish(rgb);depthpub.publish(depth);executor.spin_once(timeout_sec=.02)
for _ in range(50):executor.spin_once(timeout_sec=.02)
graph=[]
for argv in (['ros2','node','list','--no-daemon'],['ros2','node','info','/object_height_node','--no-daemon'],['ros2','topic','list','--no-daemon'],['ros2','topic','info','-v','/perception/object_height','--no-daemon']):
 q=subprocess.run(argv,capture_output=True,text=True,timeout=5);graph.append(dict(argv=argv,returncode=q.returncode,stdout=q.stdout,stderr=q.stderr))
c=Clock();new=f['rgb_stamp_ns']+300_000_000;c.clock.sec=new//10**9;c.clock.nanosec=new%10**9;clock.publish(c)
for _ in range(40):executor.spin_once(timeout_sec=.02)
result=dict(execution_class='NON_QUALIFYING_ENGINEERING_REPLAY',simulator=False,source=str(a.inspection),original_sensor_timestamps=True,outputs=outputs,ros_graph=graph,valid_count=sum(o['valid'] for o in outputs),stale_rejection=any(o['reason']=='STALE_OR_UNAVAILABLE' and o['stamp_ns']==f['rgb_stamp_ns'] for o in outputs))
(a.output/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False));print(json.dumps({k:v for k,v in result.items() if k not in ('outputs','ros_graph')}))
executor.shutdown();observer.destroy_node();source.destroy_node();rclpy.shutdown()
assert result['valid_count']>0 and result['stale_rejection'],result
