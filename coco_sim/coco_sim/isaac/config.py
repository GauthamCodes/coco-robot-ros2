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

"""COCO-facing backend contract and deterministic foundation scene."""

from coco_config import robot as r

TOPICS = {
    'command': '/diff_drive_controller/cmd_vel',
    'odom': '/diff_drive_controller/odom',
    'clock': '/clock',
    'rgb': '/camera/image_raw',
    'depth': '/camera/depth/image_raw',
    'info': '/camera/camera_info',
    'scan': '/scan',
    'joints': '/joint_states',
}
FRAMES = {
    'odom': 'odom',
    'base': 'base_footprint',
    'body': 'base_link',
    'camera': 'camera_link',
    'optical': 'camera_optical_frame',
    'lidar': 'lidar_link',
}
PHYSICS_DT = 1 / 120
RENDER_DT = 1 / 30
COMMAND_TIMEOUT = 0.5
# Controller velocity limits from coco_controllers.yaml, regression-pinned.
MAX_LINEAR = 1.0
MAX_ANGULAR = 2.0
# Foundation fixture, NOT a generated COCO fetch arena. World coordinates.
# name, centre, size, RGB. The red east wall is the range/image reference.
FIXTURES = (
    ('landmark', (1.0, 1.0, 0.3), (0.5, 0.5, 0.6), (0.1, 0.2, 0.9)),
    ('east', (5.0, 0.0, 1.0), (0.1, 8.0, 2.0), (0.9, 0.08, 0.08)),
    ('west', (-5.0, 0.0, 1.0), (0.1, 8.0, 2.0), (0.3, 0.3, 0.3)),
    ('north', (0.0, 4.0, 1.0), (10.0, 0.1, 2.0), (0.3, 0.3, 0.3)),
    ('south', (0.0, -4.0, 1.0), (10.0, 0.1, 2.0), (0.3, 0.3, 0.3)),
)


def wheel_layout():
    """Return name, centre, and side sign in base_link coordinates."""
    return [
        (f'wheel{i + 1}', (x, y, r.AXLE_Z_IN_BASE_LINK), side)
        for i, (x, y, side) in enumerate(
            (
                (r.WHEELBASE / 2, -r.WHEEL_SEPARATION / 2, -1),
                (-r.WHEELBASE / 2, -r.WHEEL_SEPARATION / 2, -1),
                (r.WHEELBASE / 2, r.WHEEL_SEPARATION / 2, 1),
                (-r.WHEELBASE / 2, r.WHEEL_SEPARATION / 2, 1),
            )
        )
    ]


def wheel_speeds(linear, angular):
    """Convert base x/yaw velocity to four positive-Y axle rates (rad/s)."""
    half_track = r.WHEEL_SEPARATION * r.WHEEL_SEPARATION_MULTIPLIER / 2
    return [
        (linear - side * angular * half_track) / r.WHEEL_RADIUS for _, _, side in wheel_layout()
    ]


class DriveCommand:
    """Age stamped commands in sim time; bound acceleration like ros2_control."""

    def __init__(self):
        self.command = (0.0, 0.0)
        self.stamp = -1e9
        self.velocity = (0.0, 0.0)

    def receive(self, linear, angular, stamp):
        """Reject non-finite commands, preserving the last valid sample."""
        import math

        if all(math.isfinite(v) for v in (linear, angular, stamp)):
            self.command = (
                max(-MAX_LINEAR, min(MAX_LINEAR, linear)),
                max(-MAX_ANGULAR, min(MAX_ANGULAR, angular)),
            )
            self.stamp = stamp

    def step(self, now, dt):
        """Return wheel targets; stale or future commands stop immediately."""
        if not 0 <= now - self.stamp <= COMMAND_TIMEOUT:
            self.velocity = (0.0, 0.0)
        else:
            self.velocity = tuple(
                old + max(-a * dt, min(a * dt, new - old))
                for old, new, a in zip(
                    self.velocity, self.command, (r.MAX_LINEAR_ACCEL, r.MAX_ANGULAR_ACCEL)
                )
            )
        return wheel_speeds(*self.velocity)
