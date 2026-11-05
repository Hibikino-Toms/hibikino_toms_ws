"""Real D405 or synthetic fixed-target camera with the separate XY tracker."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from pathlib import Path


def nodes(context):
    backend = LaunchConfiguration('backend').perform(context)
    synthetic = LaunchConfiguration('synthetic_camera').perform(context).lower() == 'true'
    if synthetic and backend != 'sim':
        raise RuntimeError('synthetic_camera is allowed only with backend:=sim')
    harvest = LaunchConfiguration('harvest_cycle_enabled').perform(context).lower() == 'true'
    require_ee_ready = LaunchConfiguration('require_ee_ready').perform(context).lower() == 'true'
    arm = Path(get_package_share_directory('arm_controller_pkg'))
    return [Node(package='arm_controller_pkg', executable='arm_xy_tracker', output='screen',
                 parameters=[str(arm/'config/xy_tracking_params.yaml'), {
                     'config_file': str(arm/'config/xy_robot_config.yaml'), 'backend': backend,
                     'harvest_cycle_enabled': harvest,
                     'require_ee_ready': require_ee_ready,
                     'startup_mode': LaunchConfiguration('startup_mode').perform(context)}]),
            Node(package='vision_pkg', executable='vision_service_realtime', output='screen',
                 parameters=[{'config_file': LaunchConfiguration('vision_config').perform(context),
                              'synthetic_camera': synthetic, 'harvest_cycle_enabled': harvest,
                              'show_window': LaunchConfiguration('show_window').perform(context).lower() == 'true'}])]


def generate_launch_description():
    config = str(Path(get_package_share_directory('vision_pkg'))/'config/realtime_detector.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('backend', default_value='sim'),
        DeclareLaunchArgument('startup_mode', default_value='configured'),
        DeclareLaunchArgument('harvest_cycle_enabled', default_value='true'),
        DeclareLaunchArgument('require_ee_ready', default_value='false'),
        DeclareLaunchArgument('synthetic_camera', default_value='false'),
        DeclareLaunchArgument('show_window', default_value='true'),
        DeclareLaunchArgument('vision_config', default_value=config),
        OpaqueFunction(function=nodes),
    ])
