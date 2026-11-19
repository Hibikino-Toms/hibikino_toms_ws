"""Automatic harvest entry point using the unified three-node launch."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    share = Path(get_package_share_directory('vision_pkg'))
    arguments = {
        'config_file': str(share/'config/vision_xy_tracking.yaml'),
        'backend': 'sim', 'startup_mode': 'configured',
        'synthetic_camera': 'true', 'show_window': 'true',
        'z_tracking_enabled': 'true', 'vision_config': '',
    }
    declarations = [DeclareLaunchArgument(name, default_value=value) for name, value in arguments.items()]
    tracking = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(share/'launch/vision_xy_tracking.launch.py')),
        launch_arguments=dict(
            {name: LaunchConfiguration(name) for name in arguments},
            auto_harvest_enabled='true', harvest_cycle_enabled='true', require_ee_ready='true').items())
    return LaunchDescription(declarations+[tracking])
