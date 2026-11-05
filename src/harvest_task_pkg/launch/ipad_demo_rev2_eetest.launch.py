"""iPad hand-target demo with the existing automatic end-effector controller."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    ee_share = Path(get_package_share_directory('end_effector_pkg'))

    return LaunchDescription([
        DeclareLaunchArgument('ee_backend', default_value='serial'),
        DeclareLaunchArgument('ee_cycle_timeout_sec', default_value='180.0'),
        Node(package='arm_controller_pkg', executable='arm_controller',
             name='arm_controller', output='screen'),
        Node(package='vision_pkg', executable='vision_service_ipad',
             name='vision_service_ipad', output='screen'),
        Node(package='end_effector_pkg', executable='auto_harvest',
             name='auto_harvest', output='screen', emulate_tty=True,
             parameters=[{
                 'config_file': str(ee_share / 'config' / 'auto_harvest.yaml'),
                 'backend': LaunchConfiguration('ee_backend'),
                 'keyboard_enabled': True,
                 'auto_confirm_sim_home': True,
             }]),
        Node(package='harvest_task_pkg', executable='ipad_demo_sync_relay_eetest',
             name='harvest_gateway_node', output='screen',
             parameters=[{
                 'ee_cycle_timeout_sec': LaunchConfiguration('ee_cycle_timeout_sec'),
             }]),
    ])
