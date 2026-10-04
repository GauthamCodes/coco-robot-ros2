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

"""Generate the minimal physical COCO base in USD from coco_config.

The navigation fixture has a fixed arm payload; fetch mode builds the URDF arm.
No manipulator control or cosmetic CAD conversion is attempted.
"""
import math

from coco_config import robot as r
from .config import FIXTURES, wheel_layout


def build_scene(stage, episode, description=None, share=None):
    """Create the entire physical scene before the ROS bridge is loaded."""
    from pxr import Gf, UsdGeom, UsdLux, UsdPhysics, UsdShade, PhysxSchema

    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.Xform.Define(stage, "/World")
    physics = UsdPhysics.Scene.Define(stage, "/World/physics")
    physics.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
    physics.CreateGravityMagnitudeAttr(9.81)
    PhysxSchema.PhysxSceneAPI.Apply(
        physics.GetPrim()
    ).CreateTimeStepsPerSecondAttr(120)
    PhysxSchema.PhysxSceneAPI.Apply(physics.GetPrim()).CreateEnableCCDAttr(True)
    material = UsdShade.Material.Define(stage, "/World/contact")
    mat = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
    mat.CreateStaticFrictionAttr(0.7)
    mat.CreateDynamicFrictionAttr(0.7)
    mat.CreateRestitutionAttr(0.0)

    def collision(prim):
        UsdPhysics.CollisionAPI.Apply(prim)
        PhysxSchema.PhysxCollisionAPI.Apply(prim).CreateContactOffsetAttr(
            0.002
        )
        PhysxSchema.PhysxCollisionAPI.Apply(prim).CreateRestOffsetAttr(0.0)
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(
            material, UsdShade.Tokens.weakerThanDescendants, "physics"
        )

    def cube(path, centre, size, colour):
        obj = UsdGeom.Cube.Define(stage, path)
        obj.CreateSizeAttr(1.0)
        obj.AddTranslateOp().Set(Gf.Vec3d(*centre))
        obj.AddScaleOp().Set(Gf.Vec3f(*size))
        obj.CreateDisplayColorAttr([Gf.Vec3f(*colour)])
        collision(obj.GetPrim())
        return obj

    if description is None:
        cube("/World/ground", (0, 0, -0.05), (20, 20, 0.1), (0.4, 0.4, 0.4))
    else:
        # Match coco_world's plane. Thin target cylinders passed through the
        # scaled box floor even in a free-drop probe; triangle contact works.
        floor = UsdGeom.Mesh.Define(stage, "/World/ground")
        floor.CreatePointsAttr([(-10, -10, 0), (10, -10, 0),
                               (10, 10, 0), (-10, 10, 0)])
        floor.CreateFaceVertexCountsAttr([3, 3])
        floor.CreateFaceVertexIndicesAttr([0, 1, 2, 0, 2, 3])
        floor.CreateSubdivisionSchemeAttr("none")
        floor.CreateDisplayColorAttr([Gf.Vec3f(0.4, 0.4, 0.4)])
        collision(floor.GetPrim())
    if description is None:
        for name, centre, size, colour in FIXTURES:
            cube("/World/" + name, centre, size, colour)
    else:
        from .articulated import build_fetch_world

        build_fetch_world(stage, episode, share, cube, collision)
    UsdLux.DistantLight.Define(stage, "/World/sun").CreateIntensityAttr(3000.0)
    UsdGeom.Xform.Define(stage, "/World/coco")
    base = UsdGeom.Xform.Define(stage, "/World/coco/base_link")
    start = episode.robot_start
    # Episode z is base_footprint; base_link is clearance above it.
    origin = (start.x, start.y, start.z + r.CHASSIS_GROUND_CLEARANCE)
    base.AddTranslateOp().Set(Gf.Vec3d(*origin))
    base.AddOrientOp().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
    UsdPhysics.RigidBodyAPI.Apply(base.GetPrim())
    UsdPhysics.ArticulationRootAPI.Apply(base.GetPrim())
    api = PhysxSchema.PhysxArticulationAPI.Apply(base.GetPrim())
    api.CreateEnabledSelfCollisionsAttr(description is not None)
    api.CreateSolverPositionIterationCountAttr(16)
    api.CreateSolverVelocityIterationCountAttr(4)
    cube(
        "/World/coco/base_link/chassis",
        (0, 0, r.CHASSIS_SIZE[2] / 2),
        r.CHASSIS_SIZE,
        (0.9, 0.45, 0.1),
    )
    # Fixed payload masses: full mass retained; primitive chassis inertia
    # plus point-mass parallel-axis terms (not CAD inertia equivalence).
    lumps = [
        (r.CHASSIS_MASS, (0.0, 0.0, r.CHASSIS_SIZE[2] / 2)),
        *(
            ([(r.ARM_CHAIN_MASS, r.ARM_MOUNT_XYZ)])
            if description is None
            else []
        ),
        (r.LIDAR_MASS, r.LIDAR_MOUNT_XYZ),
        (r.CAMERA_MASS, r.CAMERA_MOUNT_XYZ),
        (r.IMU_MASS, r.IMU_MOUNT_XYZ),
    ]
    mass = sum(m for m, _ in lumps)
    com = [sum(m * xyz[i] for m, xyz in lumps) / mass for i in range(3)]
    # Diagonal approximation explicitly documented; off-diagonal terms omitted.
    inertia = []
    for i in range(3):
        other = [j for j in range(3) if j != i]
        inertia.append(
            r.CHASSIS_MASS * sum(r.CHASSIS_SIZE[j] ** 2 for j in other) / 12
            + sum(
                m * sum((xyz[j] - com[j]) ** 2 for j in other)
                for m, xyz in lumps
            )
        )
    mass_api = UsdPhysics.MassAPI.Apply(base.GetPrim())
    mass_api.CreateMassAttr(mass)
    mass_api.CreateCenterOfMassAttr(Gf.Vec3f(*com))
    mass_api.CreateDiagonalInertiaAttr(Gf.Vec3f(*inertia))
    for name, xyz, _ in wheel_layout():
        path = "/World/coco/" + name
        wheel = UsdGeom.Mesh.Define(stage, path)
        # Explicit convex wheel collider avoids an implicit approximation.
        count = 64
        points = [
            Gf.Vec3f(
                r.WHEEL_RADIUS * math.cos(2 * math.pi * i / count),
                side * r.WHEEL_WIDTH / 2,
                r.WHEEL_RADIUS * math.sin(2 * math.pi * i / count),
            )
            for side in (-1, 1)
            for i in range(count)
        ]
        faces = [list(reversed(range(count))), list(range(count, 2 * count))]
        faces += [
            [i, (i + 1) % count, (i + 1) % count + count, i + count]
            for i in range(count)
        ]
        wheel.CreatePointsAttr(points)
        wheel.CreateFaceVertexCountsAttr([len(f) for f in faces])
        wheel.CreateFaceVertexIndicesAttr([i for f in faces for i in f])
        wheel.CreateSubdivisionSchemeAttr("none")
        UsdPhysics.MeshCollisionAPI.Apply(
            wheel.GetPrim()
        ).CreateApproximationAttr("convexHull")
        wheel.AddTranslateOp().Set(
            Gf.Vec3d(*(origin[i] + xyz[i] for i in range(3)))
        )
        wheel.AddOrientOp().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
        wheel.CreateDisplayColorAttr([Gf.Vec3f(0.05, 0.05, 0.05)])
        collision(wheel.GetPrim())
        UsdPhysics.RigidBodyAPI.Apply(wheel.GetPrim())
        ma = UsdPhysics.MassAPI.Apply(wheel.GetPrim())
        ma.CreateMassAttr(r.WHEEL_MASS)
        radial = r.WHEEL_MASS * (3 * r.WHEEL_RADIUS**2 + r.WHEEL_WIDTH**2) / 12
        axial = r.WHEEL_MASS * r.WHEEL_RADIUS**2 / 2
        ma.CreateDiagonalInertiaAttr(Gf.Vec3f(radial, axial, radial))
        joint = UsdPhysics.RevoluteJoint.Define(
            stage, "/World/coco/" + name + "_joint"
        )
        joint.CreateBody0Rel().SetTargets([base.GetPath()])
        joint.CreateBody1Rel().SetTargets([wheel.GetPath()])
        joint.CreateAxisAttr("Y")
        joint.CreateLocalPos0Attr(Gf.Vec3f(*xyz))
        joint.CreateLocalPos1Attr(Gf.Vec3f(0))
        drive = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), "angular")
        drive.CreateTypeAttr("force")
        drive.CreateStiffnessAttr(0.0)
        # Gain-20 experiment did not improve mission arrival (run 008).
        # Retain the fixture gain until low-speed tracking is calibrated.
        drive.CreateDampingAttr(1.0)
        effort = 2.0
        if description is not None:
            import xml.etree.ElementTree as ET

            number = int(name[-1])
            limit = ET.fromstring(description).find(
                f"joint[@name='base_Revolute-{number}']/limit"
            )
            # Retain the validated Isaac foundation motor ceiling. Gazebo's
            # velocity interface and PhysX force drives are different motors;
            # copying the URDF effort ceiling stalled skid steering in run 003.
            PhysxSchema.PhysxJointAPI.Apply(
                joint.GetPrim()
            ).CreateMaxJointVelocityAttr(
                math.degrees(float(limit.get("velocity")))
            )
        drive.CreateMaxForceAttr(effort)
        drive.CreateTargetVelocityAttr(0.0)
    if description is not None:
        from .articulated import build_arm

        build_arm(stage, description, origin, collision, share)
        import xml.etree.ElementTree as ET

        # Respect the same allowed self-contact pairs used by MoveIt.
        for pair in (
            ET.parse(share.parent / "coco_moveit_config/config/coco.srdf")
            .getroot()
            .findall("disable_collisions")
        ):
            names = [pair.get("link1"), pair.get("link2")]
            names = ["base_link" if n == "chassis_link" else n for n in names]
            paths = ["/World/coco/" + n for n in names]
            if all(stage.GetPrimAtPath(p).IsValid() for p in paths):
                UsdPhysics.FilteredPairsAPI.Apply(
                    stage.GetPrimAtPath(paths[0])
                ).CreateFilteredPairsRel().AddTarget(paths[1])
    # Camera prim exists before ROS. USD camera -Z forward, +Y up.
    cam = UsdGeom.Camera.Define(stage, "/World/coco/base_link/camera")
    xf = UsdGeom.XformCommonAPI(cam)
    xf.SetTranslate(Gf.Vec3d(*r.CAMERA_MOUNT_XYZ))
    xf.SetRotate(Gf.Vec3f(90, 0, -90))
    cam.CreateHorizontalApertureAttr(20.0)
    cam.CreateVerticalApertureAttr(20.0 * r.CAMERA_WH[1] / r.CAMERA_WH[0])
    cam.CreateFocalLengthAttr(10.0 / math.tan(r.CAMERA_HFOV / 2))
    cam.CreateClippingRangeAttr(Gf.Vec2f(0.1, 8.0))
    return "/World/coco/base_link"


def robot_description():
    """Generate a matching minimal RViz model from shared dimensions."""
    from xml.etree.ElementTree import Element, SubElement, tostring

    robot = Element("robot", name="coco_isaac_base")

    def link(name, shape=None, xyz=(0, 0, 0), rpy=(0, 0, 0)):
        node = SubElement(robot, "link", name=name)
        if shape:
            visual = SubElement(node, "visual")
            SubElement(
                visual,
                "origin",
                xyz=" ".join(map(str, xyz)),
                rpy=" ".join(map(str, rpy)),
            )
            geometry = SubElement(visual, "geometry")
            SubElement(geometry, shape[0], **shape[1])

    def joint(name, parent, child, xyz, rpy=(0, 0, 0), kind="fixed"):
        node = SubElement(robot, "joint", name=name, type=kind)
        SubElement(node, "parent", link=parent)
        SubElement(node, "child", link=child)
        SubElement(
            node,
            "origin",
            xyz=" ".join(map(str, xyz)),
            rpy=" ".join(map(str, rpy)),
        )
        if kind == "continuous":
            SubElement(node, "axis", xyz="0 1 0")

    link("base_footprint")
    link(
        "base_link",
        ("box", {"size": " ".join(map(str, r.CHASSIS_SIZE))}),
        (0, 0, r.CHASSIS_SIZE[2] / 2),
    )
    joint(
        "base_footprint_joint",
        "base_footprint",
        "base_link",
        (0, 0, r.CHASSIS_GROUND_CLEARANCE),
    )
    for name, xyz, _ in wheel_layout():
        link(
            name,
            (
                "cylinder",
                {"radius": str(r.WHEEL_RADIUS), "length": str(r.WHEEL_WIDTH)},
            ),
            rpy=(math.pi / 2, 0, 0),
        )
        joint(name + "_joint", "base_link", name, xyz, kind="continuous")
    for name, xyz in [
        ("lidar_link", r.LIDAR_MOUNT_XYZ),
        ("camera_link", r.CAMERA_MOUNT_XYZ),
    ]:
        link(name)
        joint(name + "_joint", "base_link", name, xyz)
    link("camera_optical_frame")
    joint(
        "camera_optical_joint",
        "camera_link",
        "camera_optical_frame",
        (0, 0, 0),
        (-math.pi / 2, 0, -math.pi / 2),
    )
    return tostring(robot, encoding="unicode")
