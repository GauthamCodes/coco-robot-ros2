"""Read-only live Nav2 snapshot for investigating a long return route."""
import argparse
import json
import time

from nav_msgs.msg import OccupancyGrid, Path
import rclpy
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener

p=argparse.ArgumentParser();p.add_argument('output');args=p.parse_args()
rclpy.init();node=rclpy.create_node('coco24_read_only_nav_snapshot');records={}
buffer=Buffer();listener=TransformListener(buffer,node)

def path(msg):
    records['plan']=dict(frame=msg.header.frame_id,xy=[[v.pose.position.x,v.pose.position.y] for v in msg.poses])

def grid(msg,key):
    records[key]=dict(frame=msg.header.frame_id,width=msg.info.width,height=msg.info.height,resolution=msg.info.resolution,origin=[msg.info.origin.position.x,msg.info.origin.position.y],data=list(msg.data))

node.create_subscription(Path,'/plan',path,10)
node.create_subscription(OccupancyGrid,'/global_costmap/costmap',lambda msg:grid(msg,'global_costmap'),qos_profile_sensor_data)
node.create_subscription(OccupancyGrid,'/local_costmap/costmap',lambda msg:grid(msg,'local_costmap'),qos_profile_sensor_data)
for topic in ['/localization/health','/mission/state']:
    node.create_subscription(String,topic,lambda msg,t=topic:records.update({t:msg.data}),10)
deadline=time.monotonic()+5
while time.monotonic()<deadline:
    rclpy.spin_once(node,timeout_sec=.1)
for source in ['odom','base_footprint']:
    try:
        tf=buffer.lookup_transform('map',source,rclpy.time.Time())
        t=tf.transform;records['map_to_'+source]=dict(xyz=[t.translation.x,t.translation.y,t.translation.z],quaternion=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w])
    except Exception as exc:records['map_to_'+source]=str(exc)
with open(args.output,'w') as f:json.dump(records,f,indent=2)
node.destroy_node();rclpy.shutdown()
print({k:(len(v['xy']) if k=='plan' else 'grid' if 'costmap' in k else v) for k,v in records.items()})
