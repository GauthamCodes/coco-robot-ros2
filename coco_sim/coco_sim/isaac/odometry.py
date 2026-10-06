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


"""ROS encoder odometry serialization; no simulator-world input."""

import math

from nav_msgs.msg import Odometry

from .config import FRAMES


def encoder_message(estimator, angles, now, stamp):
    """Update solely from joint angles and time; publish zero-origin planar odom."""
    estimator.update(angles, now)
    msg = Odometry()
    msg.header.stamp, msg.header.frame_id = stamp, FRAMES['odom']
    msg.child_frame_id = FRAMES['base']
    msg.pose.pose.position.x, msg.pose.pose.position.y = estimator.x, estimator.y
    msg.pose.pose.orientation.w = math.cos(estimator.yaw / 2)
    msg.pose.pose.orientation.z = math.sin(estimator.yaw / 2)
    msg.twist.twist.linear.x = estimator.linear
    msg.twist.twist.angular.z = estimator.angular
    for index, value in zip((0, 7, 14, 21, 28, 35),
                            (0.001, 0.001, 0.001, 0.001, 0.001, 0.01)):
        msg.pose.covariance[index] = value
        msg.twist.covariance[index] = value
    return msg
