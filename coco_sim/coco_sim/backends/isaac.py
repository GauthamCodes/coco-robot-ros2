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

"""Pure episode-to-USD target specifications, consumed by isaac.articulated.

The fetch runtime builds coco_world from the committed arena and ramp geometry.
The foundation smoke fixture remains a separate explicit runtime mode.
No simulator or ROS import is needed to translate or test an episode.
"""

from dataclasses import dataclass

from .common import SimulatorBackend


@dataclass(frozen=True)
class IsaacPrim:
    """One rigid cylinder to create on an Isaac stage.

    Units are SI and the frame is the episode's world frame (z-up,
    metres), which is Isaac's stage convention with ``metersPerUnit`` 1.
    """

    path: str             # USD prim path, e.g. /World/Targets/target_red
    name: str             # the model name the grasp binds to
    radius: float
    height: float
    mass: float
    diagonal_inertia: tuple   # (ixx, iyy, izz) about the centre of mass
    static_friction: float
    dynamic_friction: float
    display_color: tuple      # (r, g, b)
    position: tuple           # (x, y, z) of the centre of mass


@dataclass(frozen=True)
class IsaacScene:
    """What an Isaac stage builder needs to instantiate an episode."""

    episode_id: str
    world_variant: str
    robot_start: tuple        # (x, y, z, yaw)
    targets: tuple            # of IsaacPrim, in manifest order
    missing: tuple            # world pieces the Isaac runtime cannot build


TARGET_ROOT = '/World/Targets'


class IsaacBackend(SimulatorBackend):
    """Translate an episode into Isaac primitive specs (data only)."""

    name = 'isaac'

    def translate(self, spec):
        """Return the :class:`IsaacScene` for `spec`."""
        self.check(spec)
        prims = tuple(
            IsaacPrim(
                path=f'{TARGET_ROOT}/{body.name}', name=body.name,
                radius=body.radius, height=body.height, mass=body.mass,
                diagonal_inertia=(body.ixx, body.ixx, body.izz),
                # One coefficient in SDF's ODE model; Isaac's PhysX
                # material takes both. Same number, stated twice.
                static_friction=body.friction,
                dynamic_friction=body.friction,
                display_color=body.rgb,
                position=(body.x, body.y, body.z))
            for body in self.bodies(spec))
        start = spec.robot_start
        return IsaacScene(
            episode_id=spec.episode_id,
            world_variant=spec.world_variant,
            robot_start=(start.x, start.y, start.z, start.yaw),
            targets=prims,
            missing=(() if spec.world_variant == 'coco_world' else (spec.world_variant,)))
