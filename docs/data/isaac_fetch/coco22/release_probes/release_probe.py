"""Isolated native physics diagnostic, not a P03D mission or fetch result.

Spawn a NEW diagnostic cylinder at the stationary tool's initial pinch.
Never moves an existing body by pose/velocity, and commands no wheel.
Compare contact restoration before versus after physical finger opening.
"""
import argparse,json,os
from pathlib import Path
from types import SimpleNamespace
p=argparse.ArgumentParser();p.add_argument('order',choices=['detach_first','open_first','free']);p.add_argument('output',type=Path);p.add_argument('--repo',type=Path,default=Path.cwd());p.add_argument('--robot-urdf',type=Path,required=True);p.add_argument('--auto-inertia',action='store_true');p.add_argument('--floor-mesh',action='store_true');p.add_argument('--tilt',type=float,default=0);p.add_argument('--height',type=float,default=.2);a=p.parse_args();a.output.mkdir()
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'create_new_stage':False,'multi_gpu':False,'fast_shutdown':True})
try:
 import omni.usd,omni.kit.app
 import numpy as np
 from pxr import Gf,UsdGeom,UsdPhysics,PhysxSchema,UsdShade
 from isaacsim.core.api import SimulationContext
 from isaacsim.core.prims import SingleArticulation
 from isaacsim.core.utils.types import ArticulationAction
 from coco_sim.episode import generate_episode
 from coco_sim.isaac.model import build_scene
 from coco_sim.isaac.articulated import arm_transforms
 from coco_sim.isaac.grasp import Magnet,pinch_local
 from coco_config import robot as r
 from coco_config.joint_limits import ARM_LIMITS
 repo=a.repo.resolve();desc=a.robot_urdf.read_text()
 ctx=omni.usd.get_context();ctx.new_stage();stage=ctx.get_stage()
 for _ in range(3):app.update()
 root=build_scene(stage,generate_episode(seed=5,level='colours',backend='isaac',requested_colour='red'),desc,repo/'gazebo_models')
 stage.RemovePrim('/World/ground')
 if a.floor_mesh:
  floor=UsdGeom.Mesh.Define(stage,'/World/ground')
  floor.CreatePointsAttr([(-10,-10,0),(10,-10,0),(10,10,0),(-10,10,0)])
  floor.CreateFaceVertexCountsAttr([3,3]);floor.CreateFaceVertexIndicesAttr([0,1,2,0,2,3]);floor.CreateSubdivisionSchemeAttr('none')
  UsdPhysics.CollisionAPI.Apply(floor.GetPrim())
  PhysxSchema.PhysxCollisionAPI.Apply(floor.GetPrim()).CreateContactOffsetAttr(.002)
  PhysxSchema.PhysxCollisionAPI.Apply(floor.GetPrim()).CreateRestOffsetAttr(0.)
  UsdShade.MaterialBindingAPI.Apply(floor.GetPrim()).Bind(UsdShade.Material.Get(stage,'/World/contact'),UsdShade.Tokens.weakerThanDescendants,'physics')
 else:
  floor=UsdGeom.Cube.Define(stage,'/World/ground');floor.CreateSizeAttr(1.)
  floor.AddTranslateOp().Set(Gf.Vec3d(0,0,-.05));floor.AddScaleOp().Set(Gf.Vec3f(20,20,.1))
  UsdPhysics.CollisionAPI.Apply(floor.GetPrim())
  PhysxSchema.PhysxCollisionAPI.Apply(floor.GetPrim()).CreateContactOffsetAttr(.002)
  PhysxSchema.PhysxCollisionAPI.Apply(floor.GetPrim()).CreateRestOffsetAttr(0.)
  UsdShade.MaterialBindingAPI.Apply(floor.GetPrim()).Bind(UsdShade.Material.Get(stage,'/World/contact'),UsdShade.Tokens.weakerThanDescendants,'physics')
 # Creation pose is declared test setup, not movement/teleportation of a target.
 T=arm_transforms(desc)['m_link3'];pinch=(T@np.r_[pinch_local(desc),1])[:3]+[r.SPAWN_XY[0],r.SPAWN_XY[1],r.SPAWN_Z+r.CHASSIS_GROUND_CLEARANCE]
 centre=np.array([-3.,-1.,a.height]) if a.order=='free' else pinch-[0,0,.05];path='/World/release_probe'
 cyl=UsdGeom.Cylinder.Define(stage,path);cyl.CreateRadiusAttr(.01);cyl.CreateHeightAttr(.158);cyl.AddTranslateOp().Set(Gf.Vec3d(*centre));cyl.AddOrientOp().Set(Gf.Quatf(np.cos(a.tilt/2),0,np.sin(a.tilt/2),0))
 UsdPhysics.CollisionAPI.Apply(cyl.GetPrim());UsdPhysics.RigidBodyAPI.Apply(cyl.GetPrim());mass=UsdPhysics.MassAPI.Apply(cyl.GetPrim());mass.CreateMassAttr(.05)
 if not a.auto_inertia:mass.CreateDiagonalInertiaAttr(Gf.Vec3f(.05*(3*.01**2+.158**2)/12,.05*(3*.01**2+.158**2)/12,.05*.01**2/2))
 PhysxSchema.PhysxRigidBodyAPI.Apply(cyl.GetPrim()).CreateEnableCCDAttr(True)
 PhysxSchema.PhysxCollisionAPI.Apply(cyl.GetPrim()).CreateContactOffsetAttr(.002)
 em=omni.kit.app.get_app().get_extension_manager();em.set_extension_enabled_immediate('isaacsim.ros2.bridge',True)
 for _ in range(3):app.update()
 import rclpy
 rclpy.init();node=rclpy.create_node('coco22_release_physics_probe')
 sim=SimulationContext(physics_dt=1/120,rendering_dt=1/30,stage_units_in_meters=1,physics_prim_path='/World/physics');sim.initialize_physics();sim.play()
 robot=SingleArticulation(root);robot.initialize();idx=np.array([robot.get_dof_index(n.replace('-','_')) for n in ARM_LIMITS])
 logs=[]
 def log(event,**kw):logs.append(dict(event=event,sim_s=sim.current_time,**kw))
 target=SimpleNamespace(name='release_probe',path=path,radius=.01,height=.158)
 magnet=Magnet(stage,node,[target],desc,log)
 if a.order!='free':magnet.attach(target)
 def step(count,pose):
  for _ in range(count):
   robot.apply_action(ArticulationAction(joint_positions=np.array(pose),joint_indices=idx));sim.step(render=False)
   if int(round(sim.current_time*120))%12==0:
    t,tq=magnet.bodies[target.name].get_world_pose();b,bq=robot.get_world_pose();logs.append({'event':'sample','sim_s':sim.current_time,'target_xyz':t.tolist(),'target_wxyz':tq.tolist(),'base_xyz':b.tolist(),'base_wxyz':bq.tolist(),'gripper':robot.get_joint_positions()[idx].tolist(),'attached':magnet.attached})
 step(360,[0,0,.02,-.02]);log('settled')
 if a.order=='detach_first':magnet.detach(target)
 step(360,[0,0,.5,-.5]);log('fingers_open')
 if a.order=='open_first':magnet.detach(target)
 step(600,[0,0,.5,-.5]);log('finished')
 (a.output/'trace.json').write_text(json.dumps(logs,indent=2));stage.Export(str(a.output/'scene.usda'));sim.stop();node.destroy_node();rclpy.shutdown()
finally:app.close()
