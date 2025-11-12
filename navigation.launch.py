import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # パッケージのディレクトリパス
    pkg_share = get_package_share_directory('my_nav_package')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    # --- 引数の設定 ---
    map_file_arg = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(pkg_share, 'maps', 'my_map.yaml'),
        description='Full path to map file to load')

    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(pkg_share, 'config', 'nav2_params.yaml'),
        description='Full path to Nav2 parameters file')

    # --- LaunchConfigurationの取得 ---
    map_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')

    # 1. 3D点群を2Dスキャンに変換するノード (SLAM時と同じ)
    pointcloud_to_laserscan_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        remappings=[('cloud_in', '/livox/lidar'),
                    ('scan_out', '/scan')],
        parameters=[{
            'target_frame': 'livox_frame',
            'transform_tolerance': 0.01,
            'min_height': 0.1,
            'max_height': 1.5,
            'angle_min': -3.1415,
            'angle_max': 3.1415,
            'range_min': 0.3,
            'range_max': 20.0,
            'use_inf': True,
        }]
    )

    # 2. Nav2スタック本体の起動
    nav2_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': map_file,
            'params_file': params_file,
            'use_sim_time': 'False' # 実機ロボットなのでFalse
        }.items()
    )

    return LaunchDescription([
        map_file_arg,
        params_file_arg,
        pointcloud_to_laserscan_node, # 2Dスキャン変換ノードを起動
        nav2_bringup_launch          # Nav2スタックを起動
    ])
