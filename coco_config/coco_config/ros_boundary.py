# Copyright 2026 Gautham Anil
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Robot-side ROS subscription boundary, including resolved launch remaps."""

from rclpy.node import Node


def privileged_topic(topic):
    """Recognize evaluator/simulator transport, not arbitrary sensor values."""
    return (any(topic == prefix or topic.startswith(prefix + '/')
                for prefix in ('/eval', '/model', '/world'))
            or (topic.startswith('/grasp/') and topic.endswith('/height')))


class AutonomyNode(Node):
    """Reject privileged subscriptions before creating a DDS endpoint."""

    FINAL_WHEEL_AUTHORITY = False

    def create_publisher(self, msg_type, topic, qos_profile, **kwargs):
        resolved = self.resolve_topic_name(topic)
        if resolved == '/diff_drive_controller/cmd_vel' and not self.FINAL_WHEEL_AUTHORITY:
            raise ValueError('Only cmd_vel_arbiter may publish final wheel commands')
        return super().create_publisher(msg_type, topic, qos_profile, **kwargs)

    def create_subscription(self, msg_type, topic, callback, qos_profile,
                            **kwargs):
        resolved = self.resolve_topic_name(topic)
        if privileged_topic(resolved):
            raise ValueError(f'Privileged autonomy subscription: {resolved}')
        return super().create_subscription(msg_type, topic, callback,
                                           qos_profile, **kwargs)
