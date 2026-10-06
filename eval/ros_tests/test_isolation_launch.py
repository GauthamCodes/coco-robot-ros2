"""Launch real perception + evaluator; inspect real discovered ROS graph."""
import os
from pathlib import Path
import sys
import time
import unittest
import pytest
import launch_testing.markers
import launch
import launch.actions
import launch_testing
import launch_testing.actions
import rclpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from graph import snapshot,violations


@pytest.mark.launch_test
@launch_testing.markers.keep_alive
def generate_test_description():
    env=dict(os.environ,ROS_DOMAIN_ID='181')
    evaluator=launch.actions.ExecuteProcess(cmd=[sys.executable,str(Path(__file__).resolve().parents[1]/'graph_fixture.py')],env=env)
    perception=launch.actions.ExecuteProcess(cmd=['ros2','run','coco_perception','target_finder'],env=env)
    return launch.LaunchDescription([evaluator,perception,launch_testing.actions.ReadyToTest()])


class TestGraph(unittest.TestCase):
    def test_live_subscriptions(self):
        # A private Context/domain avoids affecting foreign domains.
        from rclpy.context import Context
        context=Context();rclpy.init(context=context,domain_id=181)
        node=rclpy.create_node('launch_graph_probe',context=context,namespace='/eval')
        from rclpy.executors import SingleThreadedExecutor
        executor=SingleThreadedExecutor(context=context);executor.add_node(node)
        try:
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                executor.spin_once(timeout_sec=.1)
                g=snapshot(node)
                names={e['name'] for e in g['nodes']}
                if {'target_finder','isolation_fixture'}<=names and g['topics'].get('/eval/ground_truth/state',{}).get('subscriptions'):
                    break
            else:self.fail('Required launched production/evaluator endpoints not discovered')
            self.assertEqual(violations(g,require_arbiter=False),[])
            from std_msgs.msg import String
            rogue=rclpy.create_node('non_eval',context=context)
            rogue.create_subscription(String,'/eval/ground_truth/state',lambda _:None,10)
            try:
                deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    executor.spin_once(timeout_sec=.1)
                    if violations(snapshot(node),require_arbiter=False):break
                else:self.fail('Negative control illicit subscription not detected')
            finally:rogue.destroy_node()
        finally:executor.shutdown();node.destroy_node();rclpy.shutdown(context=context)
