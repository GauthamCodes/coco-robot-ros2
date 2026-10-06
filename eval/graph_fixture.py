"""Launch-test fixture: a real evaluator endpoint, never simulation or motion."""
import rclpy
from std_msgs.msg import String
rclpy.init()
node=rclpy.create_node('isolation_fixture',namespace='/eval')
node.create_publisher(String,'/eval/ground_truth/state',10)
node.create_subscription(String,'/eval/ground_truth/state',lambda _:None,10)
rclpy.spin(node)
