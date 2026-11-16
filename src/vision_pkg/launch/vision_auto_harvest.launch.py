"""Start the automatic EE, arm tracker, and realtime vision without teleop."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def nodes(context):
    backend = LaunchConfiguration('backend').perform(context)
    synthetic = LaunchConfiguration('synthetic_camera').perform(context).lower() == 'true'
    if backend not in ('sim', 'dynamixel', 'can_mixed'):
        raise RuntimeError('backend must be sim, dynamixel, or can_mixed')
    if synthetic and backend != 'sim':
        raise RuntimeError('synthetic_camera is allowed only with backend:=sim')
    ee_backend = 'sim' if backend == 'sim' else 'serial'
    vision_share = Path(get_package_share_directory('vision_pkg'))
    ee_node = Node(
        package='end_effector_pkg', executable='auto_harvest', name='auto_harvest',
        output='screen', emulate_tty=True,
        parameters=[{
            'backend': ee_backend,
            'keyboard_enabled': True,
            'auto_confirm_sim_home': True,
        }])
    tracking = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(vision_share/'launch/vision_xy_tracking.launch.py')),
        launch_arguments={
            'backend': backend,
            'startup_mode': LaunchConfiguration('startup_mode'),
            'harvest_cycle_enabled': 'true',
            'require_ee_ready': 'true',
            'synthetic_camera': str(synthetic).lower(),
            'show_window': LaunchConfiguration('show_window'),
            'vision_config': LaunchConfiguration('vision_config'),
            'z_tracking_enabled': LaunchConfiguration('z_tracking_enabled'),
        }.items())
    return [ee_node, tracking]


def generate_launch_description():
    vision = Path(get_package_share_directory('vision_pkg'))
    return LaunchDescription([
        DeclareLaunchArgument('backend', default_value='sim'),
        DeclareLaunchArgument('startup_mode', default_value='configured'),
        DeclareLaunchArgument('synthetic_camera', default_value='true'),
        DeclareLaunchArgument('show_window', default_value='true'),
        DeclareLaunchArgument('z_tracking_enabled', default_value='false'),
        DeclareLaunchArgument('vision_config',
            default_value=str(vision/'config/realtime_detector.yaml')),
        OpaqueFunction(function=nodes),
    ])
