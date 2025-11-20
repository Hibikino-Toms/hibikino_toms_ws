from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    
    # ... (既存のコード: pointcloud_to_laserscan_node など) ...

    # --- 【追加部分 1】 odom -> base_footprint のTF ---
    tf_odom_to_base = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='tf_odom_to_base',
        arguments=['--x', '0.0', '--y', '0.0', '--z', '0.0',
                   '--yaw', '0.0', '--pitch', '0.0', '--roll', '0.0',
                   '--frame-id', 'odom', '--child-frame-id', 'base_footprint']
    )

    # --- 【追加部分 2】 base_footprint -> livox_frame のTF ---
    tf_base_to_livox = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='tf_base_to_livox',
        arguments=['--x', '0.0', '--y', '0.0', '--z', '0.2',
                   '--yaw', '0.0', '--pitch', '0.0', '--roll', '0.0',
                   '--frame-id', 'base_footprint', '--child-frame-id', 'livox_frame']
    )

    return LaunchDescription([
        # ... (既存のノード) ...
        
        tf_odom_to_base,  # <--- これを追加！
        tf_base_to_livox, # <--- これも追加！
        
        # pointcloud_to_laserscan_node,
        # slam_toolbox_node, 
    ])
