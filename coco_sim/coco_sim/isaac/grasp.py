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

"""PhysX fixed-joint magnet matching Gazebo DetachableJoint semantics.

Objects are never snapped or repositioned. Attachment preserves the measured
relative pose and requires the target cylinder to intersect the pinch band.
"""

import numpy as np
from scipy.spatial.transform import Rotation

from .articulated import arm_transforms, origin
import xml.etree.ElementTree as ET


def pinch_local(description):
    """Midpoint of the two closed fingertip lips in the palm frame."""
    transforms = arm_transforms(
        description, {"m_link3_Revolute-8": 0.02, "m_link3_Revolute-9": -0.02}
    )
    tree = ET.fromstring(description)
    points = []
    for name in ("grip1", "grip2"):
        lip = tree.find(f"link[@name='{name}']/collision[@name='{name}_lip']")
        points.append((transforms[name] @ origin(lip))[:3, 3])
    return (
        np.linalg.inv(transforms["m_link3"])
        @ np.r_[np.mean(points, axis=0), 1]
    )[:3]


def can_attach(pinch, target, radius, height):
    return (
        all(np.isfinite(pinch))
        and all(np.isfinite(target))
        and np.linalg.norm(np.array(pinch[:2]) - target[:2]) <= radius + 0.015
        and target[2] - height / 2 <= pinch[2] <= target[2] + height / 2
    )


class Magnet:
    def __init__(self, stage, node, targets, description, log):
        from isaacsim.core.prims import SingleRigidPrim
        from std_msgs.msg import Empty, String, Float64
        from rclpy.qos import QoSProfile, DurabilityPolicy

        self.stage, self.log, self.node = stage, log, node
        self.palm = SingleRigidPrim("/World/coco/m_link3")
        self.palm.initialize()
        self.pinch = pinch_local(description)
        self.targets = targets
        self.bodies, self.states, self.heights = {}, {}, {}
        self.attached = None
        latched = QoSProfile(
            depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL
        )
        for target in targets:
            body = SingleRigidPrim(target.path)
            body.initialize()
            self.bodies[target.name] = body
            self.states[target.name] = node.create_publisher(
                String, f"/magnet/{target.name}/state", latched
            )
            self.heights[target.name] = node.create_publisher(
                Float64, f"/grasp/{target.name}/height", 10
            )
            node.create_subscription(
                Empty,
                f"/magnet/{target.name}/attach",
                lambda _, t=target: self.attach(t),
                10,
            )
            node.create_subscription(
                Empty,
                f"/magnet/{target.name}/detach",
                lambda _, t=target: self.detach(t),
                10,
            )
            self.states[target.name].publish(String(data="detached"))

    def attach(self, target):
        from pxr import Gf, UsdPhysics
        from std_msgs.msg import String

        if self.attached == target.name:
            self.states[target.name].publish(String(data="attached"))
            return
        p, q = self.palm.get_world_pose()
        t, tq = self.bodies[target.name].get_world_pose()
        rotation = Rotation.from_quat((*q[1:], q[0])).as_matrix()
        pinch = p + rotation @ self.pinch
        if self.attached or not can_attach(
            pinch, t, target.radius, target.height
        ):
            self.log(
                "attach_rejected",
                target=target.name,
                pinch_world_m=pinch.tolist(),
                target_world_m=t.tolist(),
            )
            return
        joint = UsdPhysics.FixedJoint.Define(self.stage, "/World/magnet_joint")
        joint.CreateBody0Rel().SetTargets(["/World/coco/m_link3"])
        joint.CreateBody1Rel().SetTargets([target.path])
        joint.CreateLocalPos0Attr(Gf.Vec3f(*map(float, rotation.T @ (t - p))))
        relative = Rotation.from_matrix(rotation.T) * Rotation.from_quat(
            (*tq[1:], tq[0])
        )
        rq = relative.as_quat()
        joint.CreateLocalRot0Attr(Gf.Quatf(float(rq[3]), *map(float, rq[:3])))
        joint.CreateExcludeFromArticulationAttr(True)
        # A fixed-joint magnet is a welded cluster, not a friction pinch.
        # Internal finger/palm contact must not fight that rigid constraint.
        # World and ground contacts remain enabled throughout.
        filtered = UsdPhysics.FilteredPairsAPI.Apply(
            self.stage.GetPrimAtPath(target.path)).CreateFilteredPairsRel()
        for link in ('m_link3', 'grip1', 'grip2'):
            filtered.AddTarget('/World/coco/' + link)
        self.attached = target.name
        self.states[target.name].publish(String(data="attached"))
        self.log("attached", target=target.name, target_world_m=t.tolist(),
                 pinch_world_m=pinch.tolist())

    def detach(self, target):
        from std_msgs.msg import String

        if self.attached == target.name:
            from pxr import UsdPhysics

            self.stage.RemovePrim("/World/magnet_joint")
            filtered = UsdPhysics.FilteredPairsAPI(
                self.stage.GetPrimAtPath(target.path)).GetFilteredPairsRel()
            for link in ('m_link3', 'grip1', 'grip2'):
                filtered.RemoveTarget('/World/coco/' + link)
            self.attached = None
            self.log("detached", target=target.name)
        self.states[target.name].publish(String(data="detached"))

    def publish(self):
        from std_msgs.msg import Float64

        for name, body in self.bodies.items():
            p, _ = body.get_world_pose()
            self.heights[name].publish(Float64(data=float(p[2])))
