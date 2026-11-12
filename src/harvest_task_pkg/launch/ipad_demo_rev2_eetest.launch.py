"""iPad hand-target demo with the existing automatic end-effector controller."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('ee_backend', default_value='serial'),
        DeclareLaunchArgument('ee_cycle_timeout_sec', default_value='180.0'),
        Node(package='arm_controller_pkg', executable='arm_controller',
             name='arm_controller', output='screen'),
        Node(package='vision_pkg', executable='vision_service_ipad',
             name='vision_service_ipad', output='screen',
             parameters=[{'enable_over_camera': False}]),
        Node(package='end_effector_pkg', executable='auto_harvest',
             name='auto_harvest', output='screen', emulate_tty=True,
             ros_arguments=['--log-level', 'WARN'],
             parameters=[{
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
