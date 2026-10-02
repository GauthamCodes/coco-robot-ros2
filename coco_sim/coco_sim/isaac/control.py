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

"""Fail-closed manipulation command validation and trajectory interpolation."""

import math

from coco_config.joint_limits import ARM_LIMITS


def valid_positions(names, positions):
    return (
        bool(names)
        and len(names) == len(set(names))
        and len(names) == len(positions)
        and all(
            name in ARM_LIMITS
            and math.isfinite(value)
            and ARM_LIMITS[name][0] <= value <= ARM_LIMITS[name][1]
            for name, value in zip(names, positions)
        )
    )


class Trajectory:
    """Validated position trajectory; elapsed time is simulation time."""

    def __init__(self, names, points, initial):
        self.names = tuple(names)
        self.points = [(0.0, tuple(initial))]
        if not valid_positions(names, initial) or not points:
            raise ValueError("Invalid initial joint state or empty trajectory")
        last = -1.0
        for stamp, positions in points:
            if (
                not math.isfinite(stamp)
                or stamp < 0
                or stamp <= last
                or not valid_positions(names, positions)
            ):
                raise ValueError("Invalid positions or non-increasing times")
            if stamp == 0:
                self.points[0] = (stamp, tuple(positions))
            else:
                self.points.append((stamp, tuple(positions)))
            last = stamp
        self.duration = self.points[-1][0]

    def sample(self, elapsed):
        if elapsed >= self.duration:
            return self.points[-1][1]
        for (a, start), (b, end) in zip(self.points, self.points[1:]):
            if elapsed <= b:
                fraction = max(0.0, (elapsed - a) / (b - a))
                return tuple(
                    x + fraction * (y - x) for x, y in zip(start, end)
                )
        return self.points[-1][1]
