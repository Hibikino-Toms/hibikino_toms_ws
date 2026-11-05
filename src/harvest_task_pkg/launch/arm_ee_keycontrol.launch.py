from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('harvest_link_enabled', default_value='true'),
        DeclareLaunchArgument('simulate_hardware', default_value='false'),
        Node(package='end_effector_pkg', executable='pull_module_teleop',
             name='pull_module_teleop', output='screen', emulate_tty=True,
             parameters=[{
                 'harvest_link_enabled': ParameterValue(LaunchConfiguration('harvest_link_enabled'), value_type=bool),
                 'simulate_hardware': ParameterValue(LaunchConfiguration('simulate_hardware'), value_type=bool),
             }]),
    ])
