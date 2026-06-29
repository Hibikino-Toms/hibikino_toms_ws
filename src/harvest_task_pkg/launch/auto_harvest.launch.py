from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    
    # 1. アーム制御ノード
    arm_node = Node(
        package='arm_controller_pkg',
        executable='arm_controller',
        name='arm_controller',
        output='screen'
    )

    # 2. レール制御ノード
    rail_node = Node(
        package='cart_controller_pkg',
        executable='rail_service_node',
        name='rail_service_node',
        output='screen'
    )

    # 3. エンドエフェクタ制御ノード
    ee_node = Node(
        package='end_effector_pkg',
        executable='suction_module_service_node',
        name='suction_module_service_node',
        output='screen'
    )

    # 4. ビジョンサービスノード
    vision_node = Node(
        package='vision_pkg',
        executable='vision_service',
        name='vision_service',
        output='screen'
    )

    # 5. 自動収穫司令塔ノード
    auto_harvest_node = Node(
        package='teleop_demo_pkg',
        executable='teleop_automation',
        name='analyze2harvest_node',
        output='screen'
    )

    # 起動するノードのリスト
    return LaunchDescription([
        arm_node,
        rail_node,
        ee_node,
        vision_node,
        auto_harvest_node
    ])