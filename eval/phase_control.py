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
        self.validator=PhaseValidator("red");self.records=[]
        self.create_subscription(String,"/perception/object_height",self.observe,10)
        self.create_subscription(String,"/grasp/status",self.state,10)
        self.controller_client=self.create_client(ListControllers,"/controller_manager/list_controllers")
        self.controller_future=None
        self.command_clients={name:self.create_client(Trigger,"/grasp/"+name) for name in ("stow","pick","place")}
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
            self.records.append(self.validator.record(self.observation,self.get_clock().now().nanoseconds))
    def state(self,msg):
        import re
        self.status={key:value.strip() for key,value in re.findall(r"(\w+)=(.*?)(?= \w+=|$)",msg.data)}
        stage=self.status.get("phase","")
        if stage.startswith("pick:"):
            if stage in ("pick:raise","pick:confirm","pick:carry"):self.phase("lift")
            else:self.phase("approach")
        if stage.startswith("place:"):self.phase("release")
    def wait(self, predicate, seconds):
        end=time.monotonic()+seconds
        while rclpy.ok() and time.monotonic()<end:
            rclpy.spin_once(self,timeout_sec=.05)
            if predicate():return True
        return False
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
                node.phase("approach");result=node.request("pick");results.append(result)
                if result.get("status",{}).get("outcome")=="held":
                    node.phase("release");results.append(node.request("place"))
            else:results.append(dict(error="BASELINE_NOT_CERTIFIED"))
    finally:
        (root/"control_result.json").write_text(json.dumps(dict(execution_class="NON_QUALIFYING",ground_truth_inputs=False,results=results,phase_events=node.events,records=node.records),indent=2,allow_nan=False))
        node.destroy_node();rclpy.shutdown()
