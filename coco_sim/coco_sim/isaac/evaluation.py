"""Evaluator-only simulator state export. No control or normal state outputs."""
import json


class GroundTruth:
    def __init__(self, node, magnet):
        from std_msgs.msg import String
        from geometry_msgs.msg import PoseStamped, Vector3Stamped
        self.String,self.PoseStamped,self.Vector3Stamped=String,PoseStamped,Vector3Stamped
        self.magnet=magnet
        root='/eval/ground_truth'
        self.state=node.create_publisher(String,root+'/state',10)
        self.robot=node.create_publisher(PoseStamped,root+'/robot/pose',10)
        self.outputs={t.name:(node.create_publisher(PoseStamped,root+f'/objects/{t.name}/pose',10),
                              node.create_publisher(Vector3Stamped,root+f'/objects/{t.name}/dimensions',10))
                      for t in magnet.targets}

    def publish(self, now, position, quaternion):
        def stamped(kind):
            msg=kind(); ns=round(now*1e9)
            msg.header.stamp.sec=ns//10**9;msg.header.stamp.nanosec=ns%10**9
            msg.header.frame_id='world';return msg
        def pose(p,q,pub):
            msg=stamped(self.PoseStamped)
            msg.pose.position.x,msg.pose.position.y,msg.pose.position.z=map(float,p)
            msg.pose.orientation.w,msg.pose.orientation.x,msg.pose.orientation.y,msg.pose.orientation.z=map(float,q)
            pub.publish(msg)
            return dict(xyz_m=list(map(float,p)),quaternion_wxyz=list(map(float,q)))
        packet=dict(schema_version=1,sim_s=now,frame='world',robot=pose(position,quaternion,self.robot),objects={})
        for t in self.magnet.targets:
            p,q=self.magnet.bodies[t.name].get_world_pose()
            dims=[2*t.radius,2*t.radius,t.height]
            packet['objects'][t.name]=dict(pose(p,q,self.outputs[t.name][0]),dimensions_m=dims,
                                           attached=self.magnet.attached==t.name)
            msg=stamped(self.Vector3Stamped);msg.vector.x,msg.vector.y,msg.vector.z=dims
            self.outputs[t.name][1].publish(msg)
        self.state.publish(self.String(data=json.dumps(packet,allow_nan=False)))
