#!/usr/bin/env python3
"""Measured simulator-free ROS/MCAP workload. No simulator, mission or actuator."""
import argparse
import csv
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from evidence import atomic_json, bag_hash, file_hash, outside_git
from qualification import inventory, identity, cpu_percent


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=30)
    args=parser.parse_args()
    if args.seconds<15:parser.error('Each phase requires at least 15 one-Hz samples')
    root=outside_git(args.output);root.mkdir(parents=True,exist_ok=False)
    run=root/'fixture';run.mkdir();(run/'logs').mkdir()
    repo=Path(__file__).resolve().parents[1]
    atomic_json(run/'manifest.json',dict(seed=5,seed_group='dev',qualified=False,
        backend='synthetic',requested_colour='red',home_xy_m=[0.,0.],
        targets=[dict(model='target_red',height=.1),dict(model='target_blue',height=.1)],
        evidence_label='SYNTHETIC_ROS_NO_SIMULATOR'))
    env=dict(os.environ,ROS_DOMAIN_ID='184',ROS2CLI_NO_DAEMON='1')
    children=[];handles=[];samples=[];owned=[]
    def spawn(name,argv):
        handle=(root/f'{name}.log').open('x');handles.append(handle)
        child=subprocess.Popen(argv,env=env,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
        children.append((name,child));owned.append(identity(child.pid));return child
    def sample(phase):
        snap=inventory();groups={c.pid for _,c in children};members=[p for p in snap['processes'] if p['pgid'] in groups]
        rss=0
        for p in members:
            try:rss+=int(next(l.split()[1] for l in (Path('/proc')/str(p['pid'])/'status').read_text().splitlines() if l.startswith('VmRSS:')))*1024
            except (OSError,StopIteration):pass
            if (p['pid'],p['start_ticks']) not in {(q['pid'],q['start_ticks']) for q in owned}:owned.append(p)
        previous= samples[-1]['snapshot'] if samples else snap
        row=dict(phase=phase,wall_epoch_ns=snap['wall_epoch_ns'],monotonic_s=snap['monotonic_s'],
                 cpu_percent=cpu_percent(previous,snap),load1=snap['load1'],
                 ram_available_bytes=snap['ram_available_bytes'],vram_free_bytes=snap['gpu']['free_bytes'] if snap['gpu'] else None,
                 owned_rss_sum_bytes=rss,owned_process_count=len(members),snapshot=snap)
        samples.append(row)
    def phase(name,publish=None):
        deadline=time.monotonic()+args.seconds;tick=time.monotonic()
        while time.monotonic()<deadline:
            if publish:publish()
            if time.monotonic()>=tick:sample(name);tick+=1
            time.sleep(.05)
    node=None;context=None;executor=None
    try:
        phase('idle')
        from ament_index_python.packages import get_package_prefix
        for package,executable in [('custom_teleop','cmd_vel_arbiter'),('coco_perception','target_finder')]:
            spawn(executable,[str(Path(get_package_prefix(package))/'lib'/package/executable),
                              '--ros-args','-p','use_sim_time:=true'])
        spawn('nav2',['ros2','launch','gazebo_models','nav.launch.py'])
        import rclpy
        from rclpy.context import Context
        from rclpy.qos import QoSProfile,DurabilityPolicy
        from std_msgs.msg import String
        from rosgraph_msgs.msg import Clock
        from sensor_msgs.msg import LaserScan
        from tf2_msgs.msg import TFMessage
        from geometry_msgs.msg import TransformStamped
        from action_msgs.msg import GoalStatusArray,GoalStatus
        context=Context();rclpy.init(context=context,domain_id=184)
        node=rclpy.create_node('non_sim_source',namespace='/eval',context=context)
        from rclpy.executors import SingleThreadedExecutor
        executor=SingleThreadedExecutor(context=context);executor.add_node(node)
        clock=node.create_publisher(Clock,'/clock',10)
        truth=node.create_publisher(String,'/eval/ground_truth/state',10)
        mission=node.create_publisher(String,'/mission/state',10)
        status=node.create_publisher(GoalStatusArray,'/execute_trajectory/_action/status',QoSProfile(depth=10,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        scan=node.create_publisher(LaserScan,'/scan',10)
        tf=node.create_publisher(TFMessage,'/tf_static',QoSProfile(depth=10,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        transforms=[]
        for parent,child in [('map','odom'),('odom','base_footprint'),('base_footprint','base_link'),('base_link','lidar_link')]:
            t=TransformStamped();t.header.frame_id=parent;t.child_frame_id=child;t.transform.rotation.w=1.;transforms.append(t)
        tf.publish(TFMessage(transforms=transforms))
        started=time.monotonic();terminal=False;recording=False
        def publish():
            sim=time.monotonic()-started+1
            stamp=Clock();stamp.clock.sec=int(sim);stamp.clock.nanosec=int((sim-int(sim))*1e9);clock.publish(stamp)
            laser=LaserScan();laser.header.stamp=stamp.clock;laser.header.frame_id='lidar_link'
            laser.angle_min=-3.14;laser.angle_max=3.14;laser.angle_increment=6.28/359;laser.range_min=.05;laser.range_max=12.;laser.ranges=[10.]*360;scan.publish(laser)
            if recording:
                stage='ABORT' if terminal else 'LOCALIZE'
                mission.publish(String(data=f'state={stage} reason=synthetic_fixture'))
                packet=dict(schema_version=1,sim_s=sim,robot_frame='base_footprint',
                            robot=dict(xyz_m=[0.,0.,0.],quaternion_wxyz=[1.,0.,0.,0.]),
                            objects={n:dict(xyz_m=[0. if n=='target_red' else .02,.0,.05],
                                      quaternion_wxyz=[1.,0.,0.,0.],attached=False) for n in ['target_red','target_blue']})
                # Explicit controlled failing physical outcome: target outside home.
                packet['objects']['target_red']['xyz_m'][0]=2.
                truth.publish(String(data=json.dumps(packet)))
                s=GoalStatus();s.goal_info.goal_id.uuid=list(range(16));s.goal_info.stamp=stamp.clock;s.status=6
                status.publish(GoalStatusArray(status_list=[s]))
            executor.spin_once(timeout_sec=0)
        phase('ros_nav2_perception_arbiter',publish)
        spawn('recorder',[sys.executable,str(repo/'eval/recorder.py'),str(run)])
        deadline=time.monotonic()+15
        while not (run/'logs/recorder_ready.json').exists():
            publish();time.sleep(.05)
            if time.monotonic()>deadline:raise RuntimeError('Recorder did not become ready')
        # Allow fixed-topic discovery before the episode begins.
        discovery=time.monotonic()+2
        while time.monotonic()<discovery:publish();time.sleep(.05)
        recording=True
        phase('ros_plus_mcap_20hz_synthetic',publish)
        terminal=True
        for _ in range(30):publish();time.sleep(.05)
        from graph import snapshot,violations
        graph=snapshot(node)
        atomic_json(root/'graph.json',dict(graph,violations=violations(graph)))
        commands=[['node','list','--no-daemon'],['node','info','/cmd_vel_arbiter'],
                  ['node','info','/controller_server'],['node','info','/eval/trace_recorder'],
                  ['topic','info','-v','/diff_drive_controller/cmd_vel'],
                  ['topic','info','-v','/cmd_vel_gated'],['topic','info','-v','/eval/ground_truth/state'],
                  ['action','list','-t'],['action','info','/navigate_to_pose'],
                  ['action','info','/compute_path_to_pose'],['service','list'],['lifecycle','nodes'],
                  *[['lifecycle','get',name] for name in ['/planner_server','/controller_server','/bt_navigator']]]
        for i,command in enumerate(commands):
            argv=['ros2',*command]
            # Installed ros2action lacks --no-daemon. Keep its CLI and daemon
            # in a registered owned process group, and stop that group below.
            if command[0]!='action' and '--no-daemon' not in argv:argv.append('--no-daemon')
            child=subprocess.Popen(argv,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                   text=True,start_new_session=True)
            children.append((f'cli-{i:02d}',child));owned.append(identity(child.pid))
            stdout,stderr=child.communicate(timeout=15)
            for p in inventory()['processes']:
                if p['pgid']==child.pid and (p['pid'],p['start_ticks']) not in {(q['pid'],q['start_ticks']) for q in owned}:
                    owned.append(p)
            atomic_json(root/f'ros2-{i:02d}.json',dict(argv=argv,returncode=child.returncode,stdout=stdout,stderr=stderr))
    finally:
        for name,child in reversed(children):
            # A CLI can exit while its owned daemon survives in the group.
            members=[p for p in inventory()['processes'] if p['pgid']==child.pid]
            if members:os.killpg(child.pid,signal.SIGINT)
            try:child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=10)
        if executor:executor.shutdown()
        if node:node.destroy_node();rclpy.shutdown(context=context)
        for handle in handles:handle.close()
        survivors=[]
        for saved in owned:
            try:current=identity(saved['pid'])
            except OSError:continue
            if current['start_ticks']==saved['start_ticks'] and current['state']!='Z':survivors.append(current)
        atomic_json(root/'teardown.json',dict(owned=owned,survivors=survivors,
                                            exits={name:c.returncode for name,c in children}))
        fields=[k for k in samples[0] if k!='snapshot']
        with (root/'metrics.csv').open('x') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
            writer.writerows({k:v for k,v in row.items() if k!='snapshot'} for row in samples)
        summary={}
        for name in sorted({r['phase'] for r in samples}):
            rows=[r for r in samples if r['phase']==name]
            summary[name]={'samples':len(rows),'duration_s':rows[-1]['monotonic_s']-rows[0]['monotonic_s'],
                          'metrics':{k:dict(min=min(v),max=max(v),median=sorted(v)[len(v)//2])
                                     for k in fields if k not in ['phase','wall_epoch_ns','monotonic_s']
                                     and (v:=[r[k] for r in rows if r[k] is not None])}}
        atomic_json(root/'resources.json',dict(phases=summary,sampling='1 Hz /proc and nvidia-smi; CPU tick deltas; owned RSS sum includes shared pages',
            resource_policy_changed=False,qualified=False,simulator_rtf=None,
            missing_resource_measurement='Full simulator + unchanged mission + ROS + MCAP combined envelope and clock RTF on an exclusively released host',
            limitation='Synthetic scan/TF and truth; no images or MoveIt/mission; cannot calibrate full-stack production limits',
            metrics_sha256=file_hash(root/'metrics.csv'),bag_hash=bag_hash(run/'bag') if (run/'bag').exists() else None))
        if survivors:raise RuntimeError('Owned probe processes survived teardown')


if __name__=='__main__':main()
