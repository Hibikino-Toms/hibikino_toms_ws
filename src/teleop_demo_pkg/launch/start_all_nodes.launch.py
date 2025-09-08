from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # ros2 run teleop_demo_pkg teleop_demo2
        Node(
            package='teleop_demo_pkg',
            executable='teleop_demo2',
            name='teleop_demo2',
            output='screen'
        ),
        # ros2 run joy joy_node
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            output='screen'
        ),
        # ros2 run arm_controller_pkg arm_controller_teleop2
        Node(
            package='arm_controller_pkg',
            executable='arm_controller_teleop2',
            name='arm_controller_teleop2',
            output='screen'
        ),
        # ros2 run teleop_demo_pkg end_motion
        Node(
            package='teleop_demo_pkg',
            executable='end_motion',
            name='end_motion',
            output='screen'
        ),

        # ros2 run cart_controller_pkg rail_service_node
        Node(
            package='cart_controller_pkg',
            executable='rail_service_node',
            name='rail_service_node',
            output='screen'
        ),
    ])