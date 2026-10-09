#!/usr/bin/env python3
"""Engineering-only RGB-D fixture with optional existing-controller arm motion.

Unchanged target SDF and robot visual geometry. Initial poses are fixture setup,
not autonomy inputs. No teleport/model-state queries. No navigation stack.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import xacro

REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'coco_sim'),str(REPO/'coco_config'),str(REPO/'scripts')]
from coco_sim.episode import generate_episode
from coco_sim.backends import GazeboBackend
from process_groups import stop

FIXTURES={
    "grasp_front_flank":dict(target_x=.153,camera_xyz=[.40,.30,.25],camera_rpy=None),
    'acquisition':dict(target_x=.35,camera_xyz=[.125,0,.055],camera_rpy=[0,0,0]),
    'grasp_original':dict(target_x=.153,camera_xyz=[.125,0,.055],camera_rpy=[0,0,0]),
    'grasp_flank':dict(target_x=.153,camera_xyz=[.15,.30,.25],camera_rpy=None),
}


def build(root,name,motion=False):
    root=Path(root);root.mkdir()
    cfg=dict(FIXTURES[name])
    if cfg['camera_rpy'] is None:
        delta=[cfg['target_x']-cfg['camera_xyz'][0],-cfg['camera_xyz'][1],.079-(cfg['camera_xyz'][2]+.0135)]
        cfg['camera_rpy']=[0,-math.atan2(delta[2],math.hypot(delta[0],delta[1])),math.atan2(delta[1],delta[0])]
    robot=ET.fromstring(xacro.process_file(str(REPO/'gazebo_models/urdf/coco_robo2.xacro')).toxml())
    origin=robot.find("joint[@name='camera_joint']/origin")
    origin.set('xyz',' '.join(map(str,cfg['camera_xyz'])))
    origin.set('rpy',' '.join(map(str,cfg['camera_rpy'])))
    # Controller/actuator and truth systems are not needed by a static optical
    # fixture. Remove plugins only; do not edit links/meshes/collision/sensors.
    for gazebo in robot.findall('gazebo'):
        for plugin in list(gazebo.findall('plugin')):
            keep=motion and ("ros2_control" in plugin.get("filename","") or plugin.findtext("child_model")=="target_red")
            if not keep:gazebo.remove(plugin)
            elif "ros2_control" in plugin.get("filename",""):
                from ament_index_python.packages import get_package_prefix
                plugin.set("filename",str(Path(get_package_prefix("gz_ros2_control"))/"lib/libgz_ros2_control-system.so"))
    for gazebo in robot.findall('gazebo'):
        for sensor in list(gazebo.findall('sensor')):
            if sensor.get('type') not in (("rgbd_camera","imu") if motion else ("rgbd_camera",)):gazebo.remove(sensor)
    robot_xml=ET.tostring(robot,encoding='unicode')
    (root/'robot.urdf').write_text(robot_xml)
    gz_xml=robot_xml.replace('package://gazebo_models/meshes/', 'file://'+str(REPO/'gazebo_models/meshes')+'/')
    (root/'robot-gz.urdf').write_text(gz_xml)
    converted=subprocess.check_output(['gz','sdf','-p',str(root/'robot-gz.urdf')],text=True)
    model=ET.fromstring(converted).find('model');model.set('name','coco')
    static=model.find('static')
    if static is None:static=ET.SubElement(model,'static')
    static.text="false" if motion else "true"
    # Optical-only profiles freeze the zero-joint pose; the motion profile
    # keeps the original dynamic body and receives controller joint-state TF.
    ET.SubElement(model,'pose').text='0 0 .0135 0 0 0'
    world_tree=ET.parse(REPO/'gazebo_models/worlds/coco_world.world')
    world=world_tree.getroot().find('world');world.set('name','rgbd_engineering')
    for item in list(world.findall('model')):
        if item.get('name')!='ground_plane':world.remove(item)
    spec=generate_episode(seed=5,level='positions',backend='gazebo',requested_colour='red')
    spawn=next(s for s in GazeboBackend().translate(spec).targets if s.name=='target_red')
    target=ET.fromstring(spawn.sdf).find('model')
    # Initial setup only; dimensions/inertia/material unchanged from backend.
    ET.SubElement(target,'pose').text=f"{cfg['target_x']} 0 .079 0 0 0"
    world.append(model);world.append(target)
    world_tree.write(root/'world.sdf')
    (root/'truth_manifest.json').write_text(json.dumps(dict(targets=[dict(model='target_red',diameter=2*float(target.find('.//collision/geometry/cylinder/radius').text),height=float(target.find('.//collision/geometry/cylinder/length').text))])))
    (root/'fixture.json').write_text(json.dumps(dict(cfg,fixture=name,
        execution_class='NON_QUALIFYING_ENGINEERING_RUNTIME',benchmark=False,
        robot_motion="real controller/MoveIt motion" if motion else "static zero-joint optical fixture; no physical grasp claim",
        target_sdf_source='unchanged GazeboBackend target_red body',
        geometry_priors_provided_to_observer=False,teleport_calls=False),indent=2))
    return robot_xml


def main():
    root=Path(sys.argv[1]);name=sys.argv[2];motion=len(sys.argv)>3 and sys.argv[3]=="rgbd_manipulation";robot_xml=build(root,name,motion)
    observer = "Node(package='coco_perception',executable='object_height_node',parameters=[{'use_sim_time':True,'target_colour':'red'}])," if len(sys.argv)<4 or sys.argv[3] in ('rgbd_observation','rgbd_manipulation') else ''
    import yaml
    bridge=yaml.safe_load((REPO/'gazebo_models/config/bridge.yaml').read_text())
    bridge=[b for b in bridge if b['ros_topic_name'] in ('/clock','/camera/image_raw','/camera/depth/image_raw','/camera/camera_info') or motion and (b['ros_topic_name']=='/imu' or b['ros_topic_name'].startswith('/magnet/target_red/'))]
    (root/'bridge.yaml').write_text(yaml.safe_dump(bridge))
    # ros2 launch parameter passing avoids URDF shell quoting; runner owns the
    # whole launch group and teardown of all children through the normal helper.
    extra="";driver_definition=""
    if motion:
        from moveit_configs_utils import MoveItConfigsBuilder
        config=(MoveItConfigsBuilder("coco",package_name="coco_moveit_config")
            .robot_description(file_path=str(root/"robot.urdf"))
            .robot_description_semantic(file_path="config/coco.srdf")
            .robot_description_kinematics(file_path="config/kinematics.yaml")
            .joint_limits(file_path="config/joint_limits.yaml")
            .trajectory_execution(file_path="config/moveit_controllers.yaml")
            .planning_pipelines(pipelines=["ompl"]).to_moveit_configs()).to_dict()
        extra=f"ExecuteProcess(cmd=['python3',{str(REPO/'eval/gazebo_truth.py')!r},{str(root/'truth_manifest.json')!r},'--world','rgbd_engineering']),"
        extra+="Node(package='controller_manager',executable='spawner',arguments=['joint_state_broadcaster','diff_drive_controller','arm_controller','gripper_controller','--controller-manager-timeout','120']),"
        extra+="Node(package='custom_teleop',executable='cmd_vel_arbiter',parameters=[{'use_sim_time':True}]),"
        extra+=f"Node(package='moveit_ros_move_group',executable='move_group',parameters=[{config!r},{{'use_sim_time':True}}]),"
        extra+="Node(package='gazebo_models',executable='magnet_release.py',arguments=['--models','target_red']),"
        extra+="Node(package='coco_perception',executable='target_finder',parameters=[{'use_sim_time':True,'target_colour':'red','publish_annotated':False}]),"
        extra+="Node(package='custom_teleop',executable='approach_server',parameters=[{'use_sim_time':True,'target_colour':'red'}]),"
        extra+="Node(package='coco_moveit_config',executable='grasp_server.py',parameters=[{'use_sim_time':True,'target_colour':'red','simulator':'gazebo'}]),"
        driver_definition=f"phase_process=ExecuteProcess(cmd=['python3',{str(REPO/'eval/phase_control.py')!r},{str(root)!r}])"
        extra+="phase_process,RegisterEventHandler(OnProcessExit(target_action=phase_process,on_exit=[EmitEvent(event=Shutdown(reason='phase control finished'))])),"
    launch=f'''from launch import LaunchDescription
from launch.actions import ExecuteProcess,RegisterEventHandler,EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch_ros.actions import Node

def generate_launch_description():
    {driver_definition}
    return LaunchDescription([
        ExecuteProcess(cmd=['python3',{str(REPO/'eval/rgbd_probe.py')!r},{str(root)!r}]),
        ExecuteProcess(cmd=['gz','sim','-r','-s','-v2',{str(root/'world.sdf')!r}]),
        Node(package='ros_gz_bridge',executable='parameter_bridge',parameters=[{{'config_file':{str(root/'bridge.yaml')!r},'use_sim_time':True}}]),
        {observer}
        {extra}
        Node(package='robot_state_publisher',executable='robot_state_publisher',parameters=[{{'robot_description':{robot_xml!r},'use_sim_time':True}}]),
    ])
'''
    (root/'fixture.launch.py').write_text(launch)
    env=dict(os.environ,GZ_PARTITION='coco-rgbd-'+root.parent.name)
    # The outer bootstrap already owns this PID/start identity and its process
    # group. Exec releases the now-unused builder interpreter instead of keeping
    # it resident alongside a second launch interpreter.
    os.execvpe('ros2',['ros2','launch',str(root/'fixture.launch.py')],env)

if __name__=='__main__':main()
