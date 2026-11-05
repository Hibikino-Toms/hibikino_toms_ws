from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    params = PathJoinSubstitution([FindPackageShare("arm_controller_pkg"), "config", "xy_tracking_params.yaml"])
    config = PathJoinSubstitution([FindPackageShare("arm_controller_pkg"), "config", "xy_robot_config.yaml"])
    return LaunchDescription([
        DeclareLaunchArgument("backend", default_value="sim", description="sim, dynamixel, or can_mixed"),
        DeclareLaunchArgument("startup_mode", default_value="configured", description="configured home/demo poses or current"),
        DeclareLaunchArgument("radius", default_value="0.05"),
        DeclareLaunchArgument("center_x", default_value="0.0"),
        DeclareLaunchArgument("center_y", default_value="0.0"),
        DeclareLaunchArgument("center_mode", default_value="current_start"),
        DeclareLaunchArgument("period", default_value="20.0"),
        DeclareLaunchArgument("publish_rate", default_value="10.0"),
        DeclareLaunchArgument("initial_phase", default_value="0.0"),
        DeclareLaunchArgument("direction", default_value="1.0"),
        DeclareLaunchArgument("revolutions", default_value="0", description="0 repeats until Ctrl-C"),
        DeclareLaunchArgument("frame_id", default_value="arm_base"),
        Node(package="arm_controller_pkg", executable="arm_xy_tracker", name="arm_xy_tracker",
             output="screen", parameters=[params, {"config_file": config, "backend": LaunchConfiguration("backend"),
                                                   "startup_mode": LaunchConfiguration("startup_mode")}]),
        Node(package="arm_controller_pkg", executable="arm_xy_circle_demo", name="arm_xy_circle_demo",
             output="screen", parameters=[{"config_file": config,
                 "radius": LaunchConfiguration("radius"),
                 "center_x": LaunchConfiguration("center_x"),
                 "center_y": LaunchConfiguration("center_y"),
                 "center_mode": LaunchConfiguration("center_mode"),
                 "period": LaunchConfiguration("period"),
                 "publish_rate": LaunchConfiguration("publish_rate"),
                 "initial_phase": LaunchConfiguration("initial_phase"),
                 "direction": LaunchConfiguration("direction"),
                 "revolutions": LaunchConfiguration("revolutions"),
                 "frame_id": LaunchConfiguration("frame_id")}]),
    ])
