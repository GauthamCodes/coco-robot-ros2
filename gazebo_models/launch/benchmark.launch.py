"""One fresh simulation and bounded navigation tour; all processes owned by launch."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory, get_package_prefix
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, EmitEvent, ExecuteProcess,
                            IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def setup(context):
    share = Path(get_package_share_directory('gazebo_models'))
    executable = Path(get_package_prefix('gazebo_models')) / 'lib/gazebo_models/nav_bench.py'
    value = lambda name: LaunchConfiguration(name).perform(context)
    args = ['python3', '-P', str(executable), '--tag', value('run_id'),
            '--only', value('scenarios'), '--timeout', value('leg_timeout'),
            '--repeats', '1', '--out', value('out')]
    if value('gt_capture'):
        args += ['--odom-gt-jsonl', value('gt_capture')]
    bench = ExecuteProcess(cmd=args, output='screen')
    return [
        RegisterEventHandler(OnProcessExit(target_action=bench, on_exit=[
            EmitEvent(event=Shutdown(reason='benchmark finished'))])),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            str(share / 'launch/full_world_robo.launch.py')),
            launch_arguments={'gui': 'false'}.items()),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(share / 'launch/nav.launch.py')),
                                 launch_arguments={'params_file': value('params_file')}.items()),
        bench,
    ]


def generate_launch_description():
    share = Path(get_package_share_directory('gazebo_models'))
    return LaunchDescription([
        DeclareLaunchArgument('run_id', default_value='run'),
        DeclareLaunchArgument('out'),
        DeclareLaunchArgument('params_file', default_value=str(share / 'config/nav2_params.yaml')),
        DeclareLaunchArgument('scenarios', default_value='open_space,wall_adjacent'),
        DeclareLaunchArgument('leg_timeout', default_value='75'),
        DeclareLaunchArgument('gt_capture', default_value=''),
        OpaqueFunction(function=setup),
    ])
