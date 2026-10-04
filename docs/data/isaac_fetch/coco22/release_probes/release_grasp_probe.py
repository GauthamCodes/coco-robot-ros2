"""Native arm-only contact diagnostic. No mission, wheel commands or teleport.

Physically actuate the existing arm, then CREATE a diagnostic cylinder near
its pinch; use production proximity gating and weld. Canonical targets stay
untouched. This fixture can never count as a fetch episode.
"""
import argparse,json,os
from pathlib import Path
from types import SimpleNamespace
p=argparse.ArgumentParser();p.add_argument('order',choices=['detach_first','open_first']);p.add_argument('output',type=Path);p.add_argument('--target-offset',type=float,nargs=3,default=[-.0027627806442671135,-.0072276127197618304,-.0520822]);p.add_argument('--robot-urdf',type=Path,required=True);p.add_argument('--repo',type=Path,default=Path.cwd());a=p.parse_args();a.output.mkdir()
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'create_new_stage':False,'multi_gpu':False,'fast_shutdown':True})
try:
 import omni.usd,omni.kit.app
 import numpy as np
 from pxr import Gf,UsdGeom,UsdPhysics,PhysxSchema,UsdShade
 from isaacsim.core.api import SimulationContext
 from isaacsim.core.prims import SingleArticulation,SingleRigidPrim
 from isaacsim.core.utils.types import ArticulationAction
 from coco_sim.episode import generate_episode
 from coco_sim.isaac.model import build_scene
 from coco_sim.isaac.grasp import Magnet,pinch_local
 from coco_config.joint_limits import ARM_LIMITS
 from scipy.spatial.transform import Rotation
 import sys
 repo=a.repo.resolve();sys.path.insert(0,str(repo/'coco_moveit_config/scripts'));import arm_ik
 desc=a.robot_urdf.read_text()
 ctx=omni.usd.get_context();ctx.new_stage();stage=ctx.get_stage()
 for _ in range(3):app.update()
 root=build_scene(stage,generate_episode(seed=5,level='colours',backend='isaac',requested_colour='red'),desc,repo/'gazebo_models')
 em=omni.kit.app.get_app().get_extension_manager();em.set_extension_enabled_immediate('isaacsim.ros2.bridge',True)
 for _ in range(3):app.update()
 import rclpy
 rclpy.init();node=rclpy.create_node('coco22_release_grasp_physics_probe')
 sim=SimulationContext(physics_dt=1/120,rendering_dt=1/30,stage_units_in_meters=1,physics_prim_path='/World/physics');sim.initialize_physics();sim.play()
 robot=SingleArticulation(root);robot.initialize();idx=np.array([robot.get_dof_index(n.replace('-','_')) for n in ARM_LIMITS]);palm=SingleRigidPrim('/World/coco/m_link3');palm.initialize()
 logs=[];magnet=None
 def log(event,**kw):logs.append(dict(event=event,sim_s=sim.current_time,**kw))
 def step(count,pose):
  for _ in range(count):
   robot.apply_action(ArticulationAction(joint_positions=np.array(pose),joint_indices=idx));sim.step(render=False)
   if magnet and int(round(sim.current_time*120))%12==0:
    t,tq=magnet.bodies['release_probe'].get_world_pose();b,bq=robot.get_world_pose();logs.append({'event':'sample','sim_s':sim.current_time,'target_xyz':t.tolist(),'target_wxyz':tq.tolist(),'base_xyz':b.tolist(),'base_wxyz':bq.tolist(),'gripper':robot.get_joint_positions()[idx].tolist(),'attached':magnet.attached})
 grasp=list(arm_ik.ik_or_none(.15412,.128));place=list(arm_ik.place_clearance_pose(grasp,.015));log('poses',grasp=grasp,place=place)
 step(600,grasp+[.5,-.5])
 pos,q=palm.get_world_pose();pinch=pos+Rotation.from_quat([*q[1:],q[0]]).apply(pinch_local(desc));centre=pinch+np.array(a.target_offset);path='/World/release_probe'
 cyl=UsdGeom.Cylinder.Define(stage,path);cyl.CreateRadiusAttr(.01);cyl.CreateHeightAttr(.158);cyl.AddTranslateOp().Set(Gf.Vec3d(*centre));cyl.AddOrientOp().Set(Gf.Quatf(1,0,0,0))
 UsdPhysics.CollisionAPI.Apply(cyl.GetPrim());UsdPhysics.RigidBodyAPI.Apply(cyl.GetPrim());mass=UsdPhysics.MassAPI.Apply(cyl.GetPrim());mass.CreateMassAttr(.05);mass.CreateDiagonalInertiaAttr(Gf.Vec3f(.05*(3*.01**2+.158**2)/12,.05*(3*.01**2+.158**2)/12,.05*.01**2/2))
 PhysxSchema.PhysxRigidBodyAPI.Apply(cyl.GetPrim()).CreateEnableCCDAttr(True);PhysxSchema.PhysxCollisionAPI.Apply(cyl.GetPrim()).CreateContactOffsetAttr(.002);PhysxSchema.PhysxCollisionAPI.Apply(cyl.GetPrim()).CreateRestOffsetAttr(0.)
 material=UsdShade.Material.Define(stage,'/World/probe_material');mat=UsdPhysics.MaterialAPI.Apply(material.GetPrim());mat.CreateStaticFrictionAttr(1.5);mat.CreateDynamicFrictionAttr(1.5);UsdShade.MaterialBindingAPI.Apply(cyl.GetPrim()).Bind(material,UsdShade.Tokens.weakerThanDescendants,'physics')
 step(3,grasp+[.5,-.5]);target=SimpleNamespace(name='release_probe',path=path,radius=.01,height=.158);magnet=Magnet(stage,node,[target],desc,log);magnet.attach(target)
 if magnet.attached is None:raise RuntimeError('Diagnostic creation did not intersect measured pinch; no fake attach')
 step(360,grasp+[.02,-.02]);step(360,place+[.02,-.02]);log('release_pose')
 if a.order=='detach_first':magnet.detach(target)
 step(360,place+[.5,-.5]);log('fingers_open')
 if a.order=='open_first':magnet.detach(target)
 step(600,place+[.5,-.5]);log('finished')
 (a.output/'trace.json').write_text(json.dumps(logs,indent=2));stage.Export(str(a.output/'scene.usda'));sim.stop();node.destroy_node();rclpy.shutdown()
finally:app.close()
