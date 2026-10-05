#!/usr/bin/env python3
"""Read-only graph evidence using the production GraspServer, no simulator.

Run after setup_env.sh with the COCO overlay and explicit MoveIt prefix.
Creates no command publisher beyond those owned by the production node;
never invokes a grasp, MoveIt goal, magnet command or wheel command.
"""
import json
from pathlib import Path
import sys
import time

import rclpy

sys.path.insert(0, str(Path(__file__).resolve().parents[3]
                       / 'coco_moveit_config' / 'scripts'))
from grasp_server import GraspServer

records = []
for backend in ('gazebo', 'isaac'):
    rclpy.init(args=['--ros-args', '-p', f'simulator:={backend}'])
    node = GraspServer()
    node._select('red')
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
    subscriptions = []
    for topic, types in node.get_topic_names_and_types():
        for endpoint in node.get_subscriptions_info_by_topic(topic):
            if endpoint.node_name == node.get_name():
                subscriptions.append({'topic': topic, 'types': types})
    records.append({'backend_parameter': backend,
                    'node': node.get_name(),
                    'subscriptions': sorted(subscriptions,
                                            key=lambda item: item['topic'])})
    node.destroy_node()
    rclpy.shutdown()
print(json.dumps(records, indent=2))
