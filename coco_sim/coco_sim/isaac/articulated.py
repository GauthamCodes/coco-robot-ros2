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

"""URDF-derived manipulation geometry and the existing COCO fetch arena.

Only simulator construction lives here. No target pose is sent to autonomy.
The expanded Gazebo URDF is the authority for arm frames, inertia and limits.
"""

import math
import struct
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation

from coco_config import robot as r
from coco_config.joint_limits import ARM_LIMITS
from coco_sim.backends.isaac import IsaacBackend

ARM_LINKS = ("m_link1", "m_link2", "m_link3", "grip1", "grip2")


def pose(xyz=(0, 0, 0), rpy=(0, 0, 0)):
    result = np.eye(4)
    result[:3, :3] = Rotation.from_euler("xyz", rpy).as_matrix()
    result[:3, 3] = xyz
    return result


def origin(element):
    node = element.find("origin")
    if node is None:
        return np.eye(4)
    return pose(
        *[
            tuple(map(float, node.get(key, "0 0 0").split()))
            for key in ("xyz", "rpy")
        ]
    )


def arm_joints(description):
    tree = ET.fromstring(description)
    joints = [
        j
        for j in tree.findall("joint")
        if j.find("child").get("link") in ARM_LINKS
    ]
    if len(joints) != 5:
        raise ValueError("URDF must contain the complete COCO arm and gripper")
    return joints


def arm_transforms(description, positions=None):
    """URDF FK relative to base_link, including CAD mounting frames."""
    positions = positions or {}
    transforms = {"base_link": np.eye(4), "m_link1": None}
    # m_link1 is fixed to chassis_link; include the two fixed mounting joints.
    tree = ET.fromstring(description)
    for name in ("chassis_joint", "base_Rigid-5"):
        joint = tree.find(f"joint[@name='{name}']")
        transforms[joint.find("child").get("link")] = transforms[
            joint.find("parent").get("link")
        ] @ origin(joint)
    for joint in arm_joints(description):
        parent = joint.find("parent").get("link")
        child = joint.find("child").get("link")
        motion = np.eye(4)
        if joint.get("type") == "revolute":
            axis = np.array(
                list(map(float, joint.find("axis").get("xyz").split()))
            )
            motion[:3, :3] = Rotation.from_rotvec(
                axis
                / np.linalg.norm(axis)
                * positions.get(joint.get("name"), 0)
            ).as_matrix()
        transforms[child] = transforms[parent] @ origin(joint) @ motion
    return {name: transforms[name] for name in ARM_LINKS}


def quaternion(matrix):
    q = Rotation.from_matrix(matrix[:3, :3]).as_quat()
    return (float(q[3]), *map(float, q[:3]))


def build_arm(stage, description, base_origin, collision, share):
    from pxr import Gf, UsdGeom, UsdPhysics, PhysxSchema

    tree = ET.fromstring(description)
    transforms = arm_transforms(description)
    paths = {name: "/World/coco/" + name for name in ARM_LINKS}
    paths["base_link"] = "/World/coco/base_link"
    for name, matrix in transforms.items():
        link = tree.find(f"link[@name='{name}']")
        body = UsdGeom.Xform.Define(stage, paths[name])
        body.AddTranslateOp().Set(Gf.Vec3d(*(matrix[:3, 3] + base_origin)))
        body.AddOrientOp().Set(Gf.Quatf(*quaternion(matrix)))
        UsdPhysics.RigidBodyAPI.Apply(body.GetPrim())
        mass = UsdPhysics.MassAPI.Apply(body.GetPrim())
        inertial = link.find("inertial")
        mass.CreateMassAttr(float(inertial.find("mass").get("value")))
        mass.CreateCenterOfMassAttr(Gf.Vec3f(*origin(inertial)[:3, 3]))
        tensor = inertial.find("inertia")
        inertia = np.array(
            [
                [
                    float(tensor.get("i" + a + b if a <= b else "i" + b + a))
                    for b in "xyz"
                ]
                for a in "xyz"
            ]
        )
        eigenvalues, axes = np.linalg.eigh(inertia)
        if np.linalg.det(axes) < 0:
            axes[:, 0] *= -1
        mass.CreateDiagonalInertiaAttr(Gf.Vec3f(*map(float, eigenvalues)))
        q = Rotation.from_matrix(axes).as_quat()
        mass.CreatePrincipalAxesAttr(Gf.Quatf(float(q[3]), *map(float, q[:3])))
        for index, collider in enumerate(link.findall("collision")):
            box = collider.find("geometry/box")
            if box is None:
                raise ValueError("COCO arm collision must be a primitive box")
            shape = UsdGeom.Cube.Define(
                stage, paths[name] + f"/collision_{index}"
            )
            shape.CreateSizeAttr(1)
            matrix_c = origin(collider)
            shape.AddTranslateOp().Set(Gf.Vec3d(*matrix_c[:3, 3]))
            shape.AddOrientOp().Set(Gf.Quatf(*quaternion(matrix_c)))
            shape.AddScaleOp().Set(
                Gf.Vec3f(*map(float, box.get("size").split()))
            )
            shape.CreateDisplayColorAttr([Gf.Vec3f(0.7, 0.7, 0.72)])
            collision(shape.GetPrim())
            shape.CreateVisibilityAttr(UsdGeom.Tokens.invisible)
        # Collision bounds are intentionally conservative; rendering them as
        # solids creates camera occlusions absent from the canonical CAD robot.
        for index, visual in enumerate(link.findall("visual")):
            source = visual.find("geometry/mesh")
            if source is None:
                raise ValueError("COCO arm visual must reference its CAD mesh")
            prefix = "package://gazebo_models/"
            uri = source.get("filename")
            if not uri.startswith(prefix):
                raise ValueError("Unsupported arm mesh package")
            raw = (share / uri[len(prefix):]).read_bytes()
            count = struct.unpack_from("<I", raw, 80)[0]
            if len(raw) != 84 + count * 50:
                raise ValueError("Expected canonical binary STL")
            mesh = UsdGeom.Mesh.Define(stage, paths[name] + f"/visual_{index}")
            mesh.CreatePointsAttr(
                [
                    Gf.Vec3f(
                        *struct.unpack_from(
                            "<3f", raw, 84 + i * 50 + 12 + j * 12
                        )
                    )
                    for i in range(count)
                    for j in range(3)
                ]
            )
            mesh.CreateFaceVertexCountsAttr([3] * count)
            mesh.CreateFaceVertexIndicesAttr(list(range(count * 3)))
            mesh.CreateSubdivisionSchemeAttr("none")
            mesh.CreateDoubleSidedAttr(True)
            matrix_v = origin(visual)
            mesh.AddTranslateOp().Set(Gf.Vec3d(*matrix_v[:3, 3]))
            mesh.AddOrientOp().Set(Gf.Quatf(*quaternion(matrix_v)))
            mesh.AddScaleOp().Set(
                Gf.Vec3f(*map(float, source.get("scale").split()))
            )
            mesh.CreateDisplayColorAttr([Gf.Vec3f(0.7, 0.7, 0.72)])
    for joint in arm_joints(description):
        name = joint.get("name")
        parent, child = [
            joint.find(key).get("link") for key in ("parent", "child")
        ]
        fixed = joint.get("type") == "fixed"
        # Collapse only the fixed chassis mounting frames, keeping their transform.
        mount = transforms[child] if fixed else origin(joint)
        parent = "base_link" if fixed else parent
        schema = UsdPhysics.FixedJoint if fixed else UsdPhysics.RevoluteJoint
        usd = schema.Define(stage, "/World/coco/" + name.replace("-", "_"))
        usd.CreateBody0Rel().SetTargets([paths[parent]])
        usd.CreateBody1Rel().SetTargets([paths[child]])
        usd.CreateLocalPos0Attr(Gf.Vec3f(*mount[:3, 3]))
        rotation = np.eye(4)
        if not fixed:
            axis = Gf.Vec3d(*map(float, joint.find("axis").get("xyz").split()))
            align = Gf.Rotation(Gf.Vec3d(1, 0, 0), axis).GetQuat()
            aq = (align.GetReal(), *align.GetImaginary())
            rotation[:3, :3] = Rotation.from_quat((*aq[1:], aq[0])).as_matrix()
            usd.CreateAxisAttr("X")
        usd.CreateLocalRot0Attr(Gf.Quatf(*quaternion(mount @ rotation)))
        usd.CreateLocalRot1Attr(Gf.Quatf(*quaternion(rotation)))
        if not fixed:
            limit = joint.find("limit")
            usd.CreateLowerLimitAttr(math.degrees(float(limit.get("lower"))))
            usd.CreateUpperLimitAttr(math.degrees(float(limit.get("upper"))))
            PhysxSchema.PhysxJointAPI.Apply(
                usd.GetPrim()
            ).CreateMaxJointVelocityAttr(
                math.degrees(float(limit.get("velocity")))
            )
            drive = UsdPhysics.DriveAPI.Apply(usd.GetPrim(), "angular")
            drive.CreateTypeAttr("force")
            drive.CreateStiffnessAttr(20.0)
            drive.CreateDampingAttr(2.0)
            drive.CreateMaxForceAttr(float(limit.get("effort")))
            drive.CreateTargetPositionAttr(0.0)
    return {name: name.replace("-", "_") for name in ARM_LIMITS}


def build_fetch_world(stage, episode, share, cube, collision):
    """Read arena collisions and the committed ramp mesh; instantiate targets."""
    from pxr import Gf, UsdGeom, UsdPhysics, UsdShade, PhysxSchema

    world = ET.parse(share / "worlds/coco_world.world").getroot().find("world")
    for model in world.findall("model"):
        if model.get("name") == "ground_plane":
            continue
        xyz = tuple(
            map(float, model.findtext("pose", "0 0 0 0 0 0").split()[:3])
        )
        geometry = model.find("link/collision/geometry")
        if geometry is None:
            continue
        box = geometry.find("box/size")
        if box is not None:
            cube(
                "/World/" + model.get("name"),
                xyz,
                tuple(map(float, box.text.split())),
                (0.55, 0.55, 0.57),
            )
        else:
            cyl = geometry.find("cylinder")
            if cyl is None:
                raise ValueError("Unsupported arena collider")
            obj = UsdGeom.Cylinder.Define(stage, "/World/" + model.get("name"))
            obj.CreateRadiusAttr(float(cyl.findtext("radius")))
            obj.CreateHeightAttr(float(cyl.findtext("length")))
            obj.AddTranslateOp().Set(Gf.Vec3d(*xyz))
            collision(obj.GetPrim())
    rise = r.RAMP_RUN * math.tan(math.radians(r.RAMP_ANGLE_DEG))
    cube(
        "/World/platform",
        (r.RAMP_SUMMIT_X + r.PLATFORM_LEN / 2, 0, rise / 2),
        (r.PLATFORM_LEN, r.RAMP_WIDTH, rise),
        (0.6, 0.6, 0.62),
    )
    raw = (share / f"meshes/ramp_wedge_{r.RAMP_ANGLE_DEG}.stl").read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    vertices = [
        Gf.Vec3f(*struct.unpack_from("<3f", raw, 84 + i * 50 + 12 + j * 12))
        for i in range(count)
        for j in range(3)
    ]
    for name, x, yaw in [
        ("ramp_up", r.RAMP_FOOT_X, 0),
        ("ramp_down", r.RAMP_SUMMIT_X + r.PLATFORM_LEN + r.RAMP_RUN, math.pi),
    ]:
        mesh = UsdGeom.Mesh.Define(stage, "/World/" + name)
        mesh.CreatePointsAttr(vertices)
        mesh.CreateFaceVertexCountsAttr([3] * count)
        mesh.CreateFaceVertexIndicesAttr(list(range(count * 3)))
        mesh.CreateSubdivisionSchemeAttr("none")
        mesh.AddTranslateOp().Set(Gf.Vec3d(x, 0, 0))
        mesh.AddRotateZOp().Set(math.degrees(yaw))
        mesh.CreateDisplayColorAttr([Gf.Vec3f(0.55, 0.55, 0.6)])
        collision(mesh.GetPrim())
    scene = IsaacBackend().translate(episode)
    for target in scene.targets:
        body = UsdGeom.Cylinder.Define(stage, target.path)
        body.CreateRadiusAttr(target.radius)
        body.CreateHeightAttr(target.height)
        body.AddTranslateOp().Set(Gf.Vec3d(*target.position))
        body.CreateDisplayColorAttr([Gf.Vec3f(*target.display_color)])
        collision(body.GetPrim())
        UsdPhysics.RigidBodyAPI.Apply(body.GetPrim())
        mass = UsdPhysics.MassAPI.Apply(body.GetPrim())
        # Thin targets can tunnel through the floor on release impulses.
        PhysxSchema.PhysxRigidBodyAPI.Apply(
            body.GetPrim()).CreateEnableCCDAttr(True)
        mass.CreateMassAttr(target.mass)
        mass.CreateDiagonalInertiaAttr(Gf.Vec3f(*target.diagonal_inertia))
        material = UsdShade.Material.Define(stage, target.path + "_material")
        api = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
        api.CreateStaticFrictionAttr(target.static_friction)
        api.CreateDynamicFrictionAttr(target.dynamic_friction)
        UsdShade.MaterialBindingAPI.Apply(body.GetPrim()).Bind(
            material, UsdShade.Tokens.weakerThanDescendants, "physics"
        )
    return scene
