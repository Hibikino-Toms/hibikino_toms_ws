from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    default_config = PathJoinSubstitution([
        FindPackageShare("vision_pkg"), "config", "realtime_detector.yaml"])
    return LaunchDescription([
        DeclareLaunchArgument("config_file", default_value=default_config),
        Node(package="vision_pkg", executable="vision_service_realtime",
             name="vision_service_realtime", output="screen",
             parameters=[{"config_file": LaunchConfiguration("config_file")}]),
    ])
