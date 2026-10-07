"""Evaluator truth schema and publisher, with no autonomy/control interface."""
import json

ROOT = '/eval/ground_truth'


def gazebo_packet(row, dimensions, attached=None):
    stamp = (row.get('header') or {}).get('stamp', {})
    poses = {p['name']: p for p in row.get('pose', [])}
    def convert(p):
        return {'xyz_m':[float(p.get('position', {}).get(k,0)) for k in ('x','y','z')],
                'quaternion_wxyz':[float(p.get('orientation', {}).get(k,0)) for k in ('w','x','y','z')]}
    return {'schema_version':1, 'sim_s':float(stamp.get('sec',0))+float(stamp.get('nsec',0))*1e-9,
            'frame':'world', 'robot_frame':'base_footprint', 'robot':convert(poses['coco']) if 'coco' in poses else None,
            'objects':{name:dict(convert(poses[name]), dimensions_m=dim,
                                 attached=(attached or {}).get(name))
                       for name, dim in dimensions.items() if name in poses}}


class TruthPublisher:
    def __init__(self, node, dimensions):
        from std_msgs.msg import String
        from geometry_msgs.msg import PoseStamped, Vector3Stamped
        self.String, self.PoseStamped, self.Vector3Stamped = String, PoseStamped, Vector3Stamped
        self.dimensions = dimensions
        self.state = node.create_publisher(String, ROOT+'/state', 10)
        self.robot = node.create_publisher(PoseStamped, ROOT+'/robot/pose', 10)
        self.objects = {name:(node.create_publisher(PoseStamped, ROOT+f'/objects/{name}/pose',10),
                              node.create_publisher(Vector3Stamped,ROOT+f'/objects/{name}/dimensions',10))
                        for name in dimensions}

    def publish(self, packet):
        def stamped(kind):
            msg=kind(); ns=round(packet['sim_s']*1e9)
            msg.header.stamp.sec=ns//10**9; msg.header.stamp.nanosec=ns%10**9
            msg.header.frame_id=packet['frame']
            return msg
        def pose(value, publisher):
            if value is None:
                return
            msg=stamped(self.PoseStamped)
            msg.pose.position.x,msg.pose.position.y,msg.pose.position.z=value['xyz_m']
            q=value['quaternion_wxyz']
            msg.pose.orientation.w,msg.pose.orientation.x,msg.pose.orientation.y,msg.pose.orientation.z=q
            publisher.publish(msg)
        self.state.publish(self.String(data=json.dumps(packet,allow_nan=False)))
        pose(packet['robot'],self.robot)
        for name,value in packet['objects'].items():
            pose(value,self.objects[name][0])
            msg=stamped(self.Vector3Stamped)
            msg.vector.x,msg.vector.y,msg.vector.z=self.dimensions[name]
            self.objects[name][1].publish(msg)
