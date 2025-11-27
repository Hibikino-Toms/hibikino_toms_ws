import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():

    # 3D点群を2Dスキャンに変換するノード
    pointcloud_to_laserscan_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        remappings=[('cloud_in', '/livox/lidar'), # 入力トピック
                    ('scan_out', '/scan')],      # 出力トピック
        parameters=[{
            'target_frame': 'livox_frame', # 2Dスキャンを生成する基準フレーム
            'transform_tolerance': 0.01,
            'min_height': 0.1,  # 地面から0.1m以上
            'max_height': 1.5,  # 1.5m以下の点群をスライスする
            'angle_min': -3.1415, # -180度
            'angle_max': 3.1415,  # +180度
            'range_min': 0.3,   #0.3
            'range_max': 20.0,  #20.0
            'use_inf': True,
        }]
    )

    # SLAM Toolboxノード
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',

        parameters=[
            os.path.join(
                get_package_share_directory('my_nav_package'), 
                'config', 'slam_params.yaml'
            )
        ],

        remappings=[('scan', '/scan')] # SLAMは /scan を購読する
    )

    tf_link_to_foot = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='tf_odom_to_base',
        arguments=['--x', '0.0', '--y', '0.0', '--z', '0.0', '--yaw', '0.0', '--pitch', '0.0', '--roll', '0.0', '--frame-id', 'base_link', '--child-frame-id', 'base_footprint']
    )
    
    tf_base_to_livox = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='tf_base_to_livox',
        arguments=['--x', '0.14', '--y', '0.0', '--z', '0.4', '--yaw', '0.0', '--pitch', '0.0', '--roll', '0.0', '--frame-id', 'base_footprint', '--child-frame-id', 'livox_frame']
    )

    return LaunchDescription([
        pointcloud_to_laserscan_node,
        slam_toolbox_node,
        tf_link_to_foot,
        tf_base_to_livox
    ])
    
