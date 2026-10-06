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


"""Planar differential-drive estimate from measured wheel angles only."""

import math

from coco_config import robot as r


class EncoderOdometry:
    """Four axle angles: right front/rear, left front/rear; zero-origin odom."""

    def __init__(self):
        self.x = self.y = self.yaw = self.linear = self.angular = 0.0
        self.previous = None
        self.stamp = None

    def update(self, angles, stamp):
        values = tuple(float(a) for a in angles)
        if (len(values) != 4 or not all(math.isfinite(a) for a in values)
                or not math.isfinite(stamp)):
            raise ValueError('Invalid encoder sample')
        if self.stamp is not None and stamp <= self.stamp:
            raise ValueError('Encoder stamps must increase')
        if self.previous is not None:
            dt = stamp - self.stamp
            right = r.WHEEL_RADIUS * sum(values[i] - self.previous[i]
                                         for i in (0, 1)) / 2
            left = r.WHEEL_RADIUS * sum(values[i] - self.previous[i]
                                        for i in (2, 3)) / 2
            distance = (right + left) / 2
            turn = (right - left) / (r.WHEEL_SEPARATION
                                     * r.WHEEL_SEPARATION_MULTIPLIER)
            # Exact differential-drive arc, including straight-line limit.
            scale = 1 if abs(turn) < 1e-12 else math.sin(turn / 2) / (turn / 2)
            self.x += distance * scale * math.cos(self.yaw + turn / 2)
            self.y += distance * scale * math.sin(self.yaw + turn / 2)
            self.yaw = math.atan2(math.sin(self.yaw + turn),
                                  math.cos(self.yaw + turn))
            self.linear, self.angular = distance / dt, turn / dt
        self.previous, self.stamp = values, stamp


def arena_xy(position):
    """Express odom in the existing nominal start prior, never actual truth.

    This fixed prior is the same configured start used by Gazebo and AMCL.
    It is not updated from simulator spawn manifests or world pose. Slip,
    displacement at startup and localization error remain estimator error.
    """
    return position.x + r.SPAWN_XY[0], position.y + r.SPAWN_XY[1]


def valid_encoder_message(msg):
    """Require the normal planar odometry contract, not evaluator world frames."""
    p, q = msg.pose.pose.position, msg.pose.pose.orientation
    values = (p.x, p.y, p.z, q.x, q.y, q.z, q.w,
              msg.twist.twist.linear.x, msg.twist.twist.angular.z)
    return (msg.header.frame_id == 'odom' and msg.child_frame_id == 'base_footprint'
            and all(math.isfinite(v) for v in values)
            and abs(sum(v * v for v in (q.x, q.y, q.z, q.w)) - 1) < 0.01
            and abs(q.x) < 1e-6 and abs(q.y) < 1e-6)
