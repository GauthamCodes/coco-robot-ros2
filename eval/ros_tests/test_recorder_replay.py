"""ROS -> production recorder -> real MCAP replay, without simulator or motion."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import rclpy
from rclpy.context import Context
from rclpy.serialization import deserialize_message
from std_msgs.msg import String
from action_msgs.msg import GoalStatusArray,GoalStatus
from nav_msgs.msg import OccupancyGrid
import rosbag2_py
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from topics import TOPICS


def test_real_mcap_uuid_stamps_and_costmap_throttle(tmp_path):
    (tmp_path/'logs').mkdir()
    env=dict(os.environ,ROS_DOMAIN_ID='182')
    out=(tmp_path/'logs/recorder.log').open('w')
    process=subprocess.Popen([sys.executable,str(Path(__file__).resolve().parents[1]/'recorder.py'),str(tmp_path)],env=env,stdout=out,stderr=subprocess.STDOUT)
    context=Context();rclpy.init(context=context,domain_id=182)
    node=rclpy.create_node('synthetic_trace_source',namespace='/eval',context=context)
    truth=node.create_publisher(String,'/eval/ground_truth/state',10)
    from rclpy.qos import QoSProfile,DurabilityPolicy
    status=node.create_publisher(GoalStatusArray,'/follow_path/_action/status',QoSProfile(depth=10,durability=DurabilityPolicy.TRANSIENT_LOCAL))
    grid=node.create_publisher(OccupancyGrid,'/global_costmap/costmap',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
    try:
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            if (tmp_path/'logs/recorder_ready.json').exists() and truth.get_subscription_count() and status.get_subscription_count() and grid.get_subscription_count():break
            if process.poll() is not None:raise AssertionError((tmp_path/'logs/recorder.log').read_text())
            time.sleep(.1)
        else:raise AssertionError('recorder subscriptions not ready')
        msg=GoalStatusArray();s=GoalStatus();s.goal_info.goal_id.uuid=list(range(16));s.goal_info.stamp.sec=7;s.status=2;msg.status_list=[s]
        cost=OccupancyGrid();cost.header.stamp.sec=7;cost.header.frame_id='map';cost.info.width=2;cost.info.height=2;cost.info.resolution=.1;cost.data=[0,0,100,0]
        for i in range(20):
            truth.publish(String(data=json.dumps({'schema_version':1,'sim_s':7+i/10,'objects':{}})))
            status.publish(msg);grid.publish(cost);time.sleep(.1)
    finally:
        process.send_signal(signal.SIGINT);process.wait(timeout=10);out.close()
        node.destroy_node();rclpy.shutdown(context=context)
    assert process.returncode==0,(tmp_path/'logs/recorder.log').read_text()
    reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(tmp_path/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    records=[]
    while reader.has_next():records.append(reader.read_next())
    statuses=[deserialize_message(data,GoalStatusArray) for topic,data,_ in records if topic=='/follow_path/_action/status']
    assert statuses and bytes(statuses[0].status_list[0].goal_info.goal_id.uuid).hex()=='000102030405060708090a0b0c0d0e0f'
    assert statuses[0].status_list[0].goal_info.stamp.sec==7
    grids=[r for r in records if r[0]=='/global_costmap/costmap']
    assert 1<=len(grids)<=3
    assert all(t in TOPICS for t,_,_ in records)
    health=[json.loads(line) for line in (tmp_path/'logs/events.jsonl').read_text().splitlines() if '/eval/trace_health' in line]
    assert health and json.loads(health[-1]['data']['data'])['missing_topics']
