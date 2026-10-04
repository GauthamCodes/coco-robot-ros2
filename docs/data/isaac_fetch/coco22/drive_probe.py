import json,time,math,subprocess,os,sys
from pathlib import Path
sys.path.insert(0,'/home/gautham/coco-isaac-21/scripts')
from process_groups import stop
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from geometry_msgs.msg import Twist
out=Path(sys.argv[1]);out.mkdir()
repo=Path('/home/gautham/coco-isaac-21');children=[];handles=[]
def spawn(name,cmd):
 h=(out/(name+'.log')).open('w');handles.append(h)
 p=subprocess.Popen(cmd,stdout=h,stderr=subprocess.STDOUT,start_new_session=True);children.append((name,p));return p
try:
 sim=spawn('isaac',['bash',str(repo/'scripts/isaac_sim_coco.sh'),'--fetch','--robot-urdf','/tmp/coco-isaac-fetch-006/robot.urdf','--episode-manifest','/tmp/coco-isaac-fetch-006/manifest.json','--output',str(out/'sim')])
 deadline=time.monotonic()+240
 while not (out/'sim/settled_targets.json').exists():
  if sim.poll()!=None or time.monotonic()>deadline:raise RuntimeError('startup')
  time.sleep(1)
 spawn('adapter',['python3',str(repo/'scripts/isaac_ros.py'),'--ros-args','-p','use_sim_time:=true'])
 rclpy.init();n=Node('coco22_drive_probe',parameter_overrides=[Parameter('use_sim_time',value=True)])
 od=[];js=[]
 n.create_subscription(Odometry,'/diff_drive_controller/odom',lambda m:od.append(m),10)
 n.create_subscription(JointState,'/joint_states',lambda m:js.append(m),10)
 pub=n.create_publisher(Twist,'/cmd_vel',10)
 def pose():
  m=od[-1];q=m.pose.pose.orientation;p=m.pose.pose.position
  return [p.x,p.y,math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))]
 while not od:rclpy.spin_once(n,timeout_sec=.1)
 results=[]
 for v,w,duration in [(0,0,2),(0,.1,6),(0,0,2),(0,.2,6),(0,0,2),(0,.35,6),(0,0,2),(.03,0,5),(0,0,2)]:
  start=n.get_clock().now().nanoseconds*1e-9;p0=pose();samples=[];wall=time.monotonic()
  while n.get_clock().now().nanoseconds*1e-9-start<duration:
   if time.monotonic()-wall>60:raise RuntimeError('probe timeout')
   m=Twist();m.linear.x=float(v);m.angular.z=float(w);pub.publish(m)
   rclpy.spin_once(n,timeout_sec=.03)
   samples.append([od[-1].twist.twist.linear.x,od[-1].twist.twist.angular.z])
  dt=n.get_clock().now().nanoseconds*1e-9-start;p1=pose()
  r={'command':[v,w],'duration':dt,'start':p0,'end':p1,'yaw_rate':math.atan2(math.sin(p1[2]-p0[2]),math.cos(p1[2]-p0[2]))/dt,'speed':math.hypot(p1[0]-p0[0],p1[1]-p0[1])/dt}
  results.append(r);print(json.dumps(r),flush=True);(out/'result.json').write_text(json.dumps(results,indent=2))
finally:
 for name,p in reversed(children):stop(name,p)
 for h in handles:h.close()
