from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # ros2 run teleop_demo_pkg teleop_demo2
        Node(
            package='teleop_demo_pkg',
            executable='teleop_demo',
            name='teleop_demo',
            output='screen'
        ),
        # ros2 run joy joy_node
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            output='screen'
        ),
        # ros2 run arm_controller_pkg arm_controller_teleop
        Node(
            package='arm_controller_pkg',
            executable='arm_controller_teleop',
            name='arm_controller_teleop',
            output='screen'
        ),
        # ros2 run end_effector_pkg end_effector_teleop
        Node(
            package='end_effector_pkg',
            executable='end_effector_teleop',
            name='end_effector_teleop',
            output='screen'
        ),

        # ros2 run cart_controller_pkg rail_teleop
        Node(
            package='cart_controller_pkg',
            executable='rail_teleop',
            name='rail_teleop',
            output='screen'
        ),
    ])