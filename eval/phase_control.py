#!/usr/bin/env python3
"""One engineering control through existing guarded services; no truth inputs."""
import json
from pathlib import Path
import sys
import time
import rclpy
from rclpy.parameter import Parameter
from std_msgs.msg import String
from std_srvs.srv import Trigger
from controller_manager_msgs.srv import ListControllers
from coco_config.ros_boundary import AutonomyNode
from coco_config.object_observation import validated_height
from coco_config.observation_phase import PhaseValidator

class Control(AutonomyNode):
    def __init__(self, root):
        super().__init__("observation_phase_control",parameter_overrides=[Parameter("use_sim_time",value=True)])
        self.root=root;self.status={};self.observation=None;self.events=[]
        self.checkpoint_pub=self.create_publisher(String,"/diagnostics/manipulation_checkpoints",10)
        self.checkpoint_stream=(root/"manipulation_checkpoints.jsonl").open("x")
        self.mode="idle";self.approach_status={}
        self.mode_pub=self.create_publisher(String,"/mission/mode",10)
        self.create_timer(.2,lambda:self.mode_pub.publish(String(data=self.mode)))
        self.create_subscription(String,"/approach/status",self.approach_state,10)
        self.approach_client=self.create_client(Trigger,"/approach/run")
        self.validator=PhaseValidator("red");self.records=[]
        self.stream=(root/"phase_observations.jsonl").open("x")
        self.create_subscription(String,"/perception/object_height",self.observe,10)
        self.create_subscription(String,"/grasp/status",self.state,10)
        self.controller_client=self.create_client(ListControllers,"/controller_manager/list_controllers")
        self.controller_future=None
        self.command_clients={name:self.create_client(Trigger,"/grasp/"+name) for name in ("stow","pick","place")}
    def checkpoint(self, name, **details):
        value=dict(checkpoint=name,stamp_ns=self.get_clock().now().nanoseconds,
                   receive_monotonic_s=time.monotonic(),execution_class="NON_QUALIFYING",**details)
        self.checkpoint_stream.write(json.dumps(value,allow_nan=False)+"\n");self.checkpoint_stream.flush()
        self.checkpoint_pub.publish(String(data=json.dumps(value,allow_nan=False)))
    def observation_checkpoint(self,name):
        o=self.observation or {};now=self.get_clock().now().nanoseconds
        valid=validated_height(o,now_ns=now,colour="red") is not None
        self.checkpoint(name,observation_contract_valid=valid,observation_stamp_ns=o.get("stamp_ns"),
                        track_id=o.get("track_id"),reference_id=o.get("reference_id"))
    def phase(self, name):
        now=self.get_clock().now().nanoseconds
        if now<=0:return
        if self.validator.phase!=name:
            self.validator.transition(name,now)
            self.events.append(dict(phase=name,stamp_ns=now))
            (self.root/"phase_events.json").write_text(json.dumps(self.events,indent=2))
    def observe(self,msg):
        self.observation=json.loads(msg.data)
        if self.validator.phase:
            record=self.validator.record(self.observation,self.get_clock().now().nanoseconds)
            self.records.append(record)
            self.stream.write(json.dumps(record,allow_nan=False)+"\n");self.stream.flush()
    def state(self,msg):
        import re
        self.status={key:value.strip() for key,value in re.findall(r"(\w+)=(.*?)(?= \w+=|$)",msg.data)}
        stage=self.status.get("phase","")
        if stage.startswith("pick:"):
            if stage in ("pick:close gripper","pick:release the scene object","pick:raise","pick:confirm lift","pick:carry"):self.phase("lift")
            else:self.phase("approach")
        if stage.startswith("place:"):self.phase("release")
    def wait(self, predicate, seconds):
        end=time.monotonic()+seconds
        while rclpy.ok() and time.monotonic()<end:
            rclpy.spin_once(self,timeout_sec=.05)
            if predicate():return True
        return False
    def approach_state(self,msg):
        import re
        self.approach_status={key:value.strip() for key,value in re.findall(r"(\w+)=(.*?)(?= \w+=|$)",msg.data)}
    def approach(self):
        if not self.wait(lambda:self.approach_client.service_is_ready(),30):return dict(error="APPROACH_SERVICE_UNAVAILABLE")
        self.phase("approach");self.mode="approach"
        self.mode_pub.publish(String(data=self.mode));self.approach_status={}
        future=self.approach_client.call_async(Trigger.Request())
        try:
            if not self.wait(future.done,5):return dict(error="APPROACH_REPLY_TIMEOUT")
            response=future.result()
            if not response.success:return dict(error="APPROACH_REJECTED",message=response.message)
            complete=self.wait(lambda:self.approach_status.get("phase")=="idle" and self.approach_status.get("outcome") not in (None,"--"),100)
            return dict(command="approach",completed=complete,status=self.approach_status)
        finally:
            self.mode="idle";self.mode_pub.publish(String(data=self.mode))
    def controllers_active(self):
        if not self.controller_client.service_is_ready():return False
        if self.controller_future is None:
            self.controller_future=self.controller_client.call_async(ListControllers.Request())
            return False
        if not self.controller_future.done():return False
        result=self.controller_future.result();self.controller_future=None
        active={c.name for c in result.controller if c.state=="active"}
        return {"arm_controller","gripper_controller","joint_state_broadcaster","diff_drive_controller"}<=active
    def request(self,name):
        if not self.wait(self.controllers_active,30):return dict(error="CONTROLLERS_NOT_ACTIVE",command=name)
        client=self.command_clients[name]
        if not self.wait(lambda:client.service_is_ready(),30):return dict(error="SERVICE_UNAVAILABLE",command=name)
        self.status={}
        if name in ("pick","place"):self.checkpoint("grasp_request" if name=="pick" else "release_request")
        future=client.call_async(Trigger.Request())
        if not self.wait(future.done,5):return dict(error="SERVICE_REPLY_TIMEOUT",command=name)
        response=future.result()
        if not response.success:return dict(error="COMMAND_REJECTED",command=name,message=response.message)
        complete=self.wait(lambda:self.status.get("phase")=="idle" and self.status.get("outcome") not in (None,"--"),100)
        return dict(command=name,acceptance=response.message,completed=complete,status=self.status)

if __name__=="__main__":
    root=Path(sys.argv[1]);rclpy.init();node=Control(root);results=[]
    try:
        # Normal magnet_release node handles initial detach; no hidden API here.
        result=node.request("stow");results.append(result)
        if result.get("completed") and result.get("status",{}).get("outcome")=="done":
            node.validator.reacquire("red");node.phase("baseline")
            def enough():
                return sum(r["contract_valid"] for r in node.records if r["phase"]=="baseline")>=5
            if node.wait(enough,20):
                node.observation_checkpoint("observation_acquired")
                result=node.approach();results.append(result)
                if result.get("status",{}).get("outcome")=="arrived":
                    node.observation_checkpoint("approach_complete")
                    result=node.request("pick");results.append(result)
                    if result.get("status",{}).get("outcome")=="held":
                        node.phase("release");results.append(node.request("place"))
            else:results.append(dict(error="BASELINE_NOT_CERTIFIED"))
    finally:
        (root/"control_result.json").write_text(json.dumps(dict(execution_class="NON_QUALIFYING",ground_truth_inputs=False,results=results,phase_events=node.events,records_path="phase_observations.jsonl",sample_count=len(node.records)),indent=2,allow_nan=False))
        node.stream.close();node.checkpoint_stream.close()
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
