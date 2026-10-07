#!/usr/bin/env python3
"""Passive fixed-topic MCAP recorder; evaluator-owned lifecycle/graph observations."""
import argparse
import json
from pathlib import Path
import signal
import time
from graph import snapshot,violations
from topics import TOPICS
from evidence import atomic_json


def main():
    import rclpy
    from rclpy.clock import Clock
    from rclpy.parameter import Parameter
    from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
    from rclpy.serialization import serialize_message
    from rosidl_runtime_py.utilities import get_message
    from rosidl_runtime_py.convert import message_to_ordereddict
    from std_msgs.msg import String
    from lifecycle_msgs.srv import GetState
    import rosbag2_py
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path)
    args=parser.parse_args();run=args.run
    rclpy.init();node=rclpy.create_node('trace_recorder',namespace='/eval',parameter_overrides=[Parameter('use_sim_time',value=True)])
    writer=rosbag2_py.SequentialWriter()
    writer.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    trace=(run/'logs/events.jsonl').open('x')
    subscribed={};created=set();last={};stop=False
    from tf2_ros import Buffer,TransformListener
    tf_buffer=Buffer();tf_listener=TransformListener(tf_buffer,node)
    publisher={t:node.create_publisher(String,t,10) for t in ('/eval/nav2/lifecycle','/eval/tf','/eval/graph','/eval/trace_health')}
    start=time.monotonic()
    latest_clock=None
    latest_clock_wall=None
    mission_stage='UNKNOWN'
    def halt(*_):
        nonlocal stop;stop=True
    signal.signal(signal.SIGINT,halt);signal.signal(signal.SIGTERM,halt)
    def record(topic,type_name,msg):
        nonlocal latest_clock,latest_clock_wall,mission_stage
        if topic=='/clock':
            latest_clock=msg.clock.sec+msg.clock.nanosec/1e9
            latest_clock_wall=time.monotonic()
        if topic=='/mission/state':
            mission_stage=next((s.split('=',1)[1] for s in msg.data.split() if s.startswith('state=')),mission_stage)
        mono=time.monotonic();interval=TOPICS[topic]
        if interval and mono-last.get(topic,-interval)<interval:return
        last[topic]=mono
        if topic not in created:
            writer.create_topic(rosbag2_py.TopicMetadata(id=len(created),name=topic,type=type_name,serialization_format='cdr'))
            created.add(topic)
        now=node.get_clock().now().nanoseconds
        writer.write(topic,serialize_message(msg),now)
        trace.write(json.dumps({'topic':topic,'sim_s':now/1e9,'wall_s':mono-start,
                                'wall_epoch_ns':time.time_ns(),'data':message_to_ordereddict(msg)},allow_nan=False)+'\n')
        trace.flush()
    def publish(topic,value):publisher[topic].publish(String(data=json.dumps(value,allow_nan=False)))
    def discover():
        atomic_json(run/'logs/clock_latest.json',{'sim_s':latest_clock,'clock_receive_monotonic_s':latest_clock_wall,
                                               'ros_clock_sim_s':node.get_clock().now().nanoseconds/1e9,'mission_stage':mission_stage})
        for topic,types in node.get_topic_names_and_types():
            if topic not in TOPICS or topic in subscribed:continue
            if len(types)!=1:continue
            kind=get_message(types[0])
            # BEST_EFFORT matches reliable and best-effort producers; transient
            # local only for known latched topics, to capture startup metadata.
            durable=(topic in ('/tf_static','/amcl_pose') or topic.endswith('/status') and '/_action/' in topic
                     or topic.startswith('/magnet/') or 'costmap' in topic)
            reliability=(ReliabilityPolicy.RELIABLE if topic in ('/diagnostics/arbiter_commands','/diff_drive_controller/cmd_vel')
                         else ReliabilityPolicy.BEST_EFFORT)
            qos=QoSProfile(depth=100,reliability=reliability,
                           durability=DurabilityPolicy.TRANSIENT_LOCAL if durable else DurabilityPolicy.VOLATILE)
            subscribed[topic]=node.create_subscription(kind,topic,lambda m,t=topic,k=types[0]:record(t,k,m),qos)
        publish('/eval/trace_health',{'observed_topics':sorted(subscribed),'missing_topics':sorted(set(TOPICS)-set(subscribed))})
        transforms={}
        from rclpy.time import Time
        for source in ('base_footprint','odom'):
            try:
                tf=tf_buffer.lookup_transform('map',source,Time())
                transforms[source]={'available':True,'stamp_s':tf.header.stamp.sec+tf.header.stamp.nanosec/1e9,
                                    'message':message_to_ordereddict(tf)}
            except Exception as exc:transforms[source]={'available':False,'error':str(exc)}
        publish('/eval/tf',{'transforms':transforms})
        g=snapshot(node);publish('/eval/graph',g)
        # Store all violations; missing arbiter during startup is not silently
        # considered clean. Runner/analyzer decide stage/coverage later.
        atomic_json(run/'logs/graph_latest.json',dict(g,violations=violations(g)))
    clients={n:node.create_client(GetState,f'/{n}/get_state') for n in ('planner_server','controller_server','bt_navigator')}
    pending={}
    def lifecycle():
        for name,client in clients.items():
            future=pending.get(name)
            if future is not None and future.done():
                try:
                    response=future.result()
                    publish('/eval/nav2/lifecycle',{'server':name,'state':response.current_state.label if response else None})
                except Exception as exc:publish('/eval/nav2/lifecycle',{'server':name,'error':str(exc)})
                pending.pop(name,None)
            if name not in pending and client.service_is_ready():pending[name]=client.call_async(GetState.Request())
    node.create_timer(1.0,discover,clock=Clock());node.create_timer(1.0,lifecycle,clock=Clock())
    atomic_json(run/'logs/recorder_ready.json',{'storage':'mcap','pid':__import__('os').getpid()})
    try:
        while rclpy.ok() and not stop:rclpy.spin_once(node,timeout_sec=.1)
    finally:
        trace.close();del writer
        atomic_json(run/'logs/recorder_end.json',{'topics':sorted(created),'stopped':stop})
        node.destroy_node();rclpy.shutdown()

if __name__=='__main__':main()
