"""Launch only the nodes required for the tomato approach test."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    standoff = LaunchConfiguration('standoff_y_mm')
    max_iterations = LaunchConfiguration('max_iterations')
    arm_xy_step = LaunchConfiguration('arm_max_xy_step_mm')
    arm_z_step = LaunchConfiguration('arm_max_z_step_mm')
    return_home = LaunchConfiguration('return_home_on_finish')

    return LaunchDescription([
        DeclareLaunchArgument(
            'standoff_y_mm',
            default_value='100.0',
            description='Distance to stop before the detected tomato center'),
        DeclareLaunchArgument(
            'max_iterations',
            default_value='30',
            description='Maximum number of detect-and-move cycles'),
        DeclareLaunchArgument(
            'arm_max_xy_step_mm',
            default_value='10.0',
            description='Maximum planar arm displacement per observation'),
        DeclareLaunchArgument(
            'arm_max_z_step_mm',
            default_value='5.0',
            description='Maximum Z displacement per observation'),
        DeclareLaunchArgument(
            'return_home_on_finish',
            default_value='false',
            description='Return to the initial arm pose after a successful test'),

        Node(
            package='arm_controller_pkg',
            executable='arm_controller_continuous',
            name='arm_controller',
            output='screen',
            parameters=[{
                'visual_servo_max_xy_step_mm': ParameterValue(
                    arm_xy_step, value_type=float),
                'visual_servo_max_z_step_mm': ParameterValue(
                    arm_z_step, value_type=float),
                'visual_servo_max_angle_step_deg': 10.0,
            }]),
        Node(
            package='vision_pkg',
            executable='vision_service_bench',
            name='vision_service',
            output='screen'),
        Node(
            package='teleop_demo_pkg',
            executable='visual_servo_approach_test',
            name='visual_servo_approach_test',
            output='screen',
            on_exit=Shutdown(reason='Visual servo approach test finished'),
            parameters=[{
                'standoff_y_mm': ParameterValue(
                    standoff, value_type=float),
                'max_iterations': ParameterValue(
                    max_iterations, value_type=int),
                'return_home_on_finish': ParameterValue(
                    return_home, value_type=bool),
            }]),
    ])
