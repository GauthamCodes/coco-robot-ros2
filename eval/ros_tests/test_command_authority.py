"""Real arbiter/ROS graph/command correlation, with no simulator or actuator."""
import json
import time
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import rclpy
from rclpy.executors import SingleThreadedExecutor
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import String
from rosidl_runtime_py.convert import message_to_ordereddict
from custom_teleop.cmd_vel_arbiter import CmdVelArbiter
from command_evidence import authority
from normalize import payload
from graph import snapshot,violations


def test_real_arbiter_lineage_preemption_stop_and_logging_failure(tmp_path):
    rclpy.init(domain_id=183)
    arbiter=CmdVelArbiter()
    probe=rclpy.create_node('command_evidence_probe',namespace='/eval')
    executor=SingleThreadedExecutor();executor.add_node(arbiter);executor.add_node(probe)
    start=time.monotonic();events=[]
    def record(topic,data):
        events.append(dict(topic=topic,sim_s=probe.get_clock().now().nanoseconds/1e9,
                           wall_s=time.monotonic()-start,data=data))
    probe.create_subscription(TwistStamped,'/diff_drive_controller/cmd_vel',
                              lambda msg:record('/diff_drive_controller/cmd_vel',message_to_ordereddict(msg)),100)
    probe.create_subscription(String,'/diagnostics/arbiter_commands',
                              lambda msg:record('/diagnostics/arbiter_commands',{'data':msg.data}),100)
    mode=probe.create_publisher(String,'/mission/mode',10)
    nav=probe.create_publisher(TwistStamped,'/cmd_vel_gated',10)
    teleop=probe.create_publisher(TwistStamped,'/cmd_vel_teleop',10)
    def spin(seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:executor.spin_once(timeout_sec=.01)
    try:
        spin(.5)
        record('/eval/graph',snapshot(probe));begin=dict(wall_s=events[-1]['wall_s'])
        mode.publish(String(data='nav'));spin(.05)
        command=TwistStamped();command.twist.linear.x=.1
        nav.publish(command);spin(.12)
        nav.publish(command);spin(.12)
        manual=TwistStamped();manual.twist.linear.x=-.05
        teleop.publish(manual);spin(.05)
        nav.publish(command);spin(.12)
        spin(.5)
        record('/eval/graph',snapshot(probe));end=dict(wall_s=events[-1]['wall_s'])
        result=authority(events,payload,begin,end,violations)
        assert result['covered'],result
        diagnostics=[payload(e) for e in events if e['topic']=='/diagnostics/arbiter_commands']
        assert {'nav','teleop',None}<={d['selected'] for d in diagnostics}
        assert any(d['selected'] is None and d['output_twist']==[0.]*6 for d in diagnostics)
        # A failed diagnostic publisher cannot suppress or alter the wheel output.
        class BrokenPublisher:
            def publish(self,_):raise RuntimeError('synthetic diagnostic failure')
        arbiter._evidence_pub=BrokenPublisher()
        count=sum(e['topic']=='/diff_drive_controller/cmd_vel' for e in events)
        nav.publish(command);spin(.15)
        new=[e for e in events if e['topic']=='/diff_drive_controller/cmd_vel'][count:]
        assert any(e['data']['twist']['linear']['x']==.1 for e in new)
        (tmp_path/'authority_evidence.json').write_text(json.dumps({'qualification':'synthetic ROS only; no simulator',
            'authority':result,'graph':payload(next(e for e in events if e['topic']=='/eval/graph')),
            'emissions':diagnostics,'diagnostic_failure_preserves_output':True},indent=2))
    finally:
        executor.shutdown();arbiter.destroy_node();probe.destroy_node();rclpy.shutdown()
