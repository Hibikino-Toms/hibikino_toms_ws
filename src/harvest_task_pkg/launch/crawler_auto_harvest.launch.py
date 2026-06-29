from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    
    # 1. アーム制御ノード (executable を修正済み)
    arm_node = Node(
        package='arm_controller_pkg',
        executable='arm_controller', # 'arm_service_node.py' ではない
        name='arm_controller'
    )

    # # 2. レール制御ノード (executable を修正済み)
    # rail_node = Node(
    #     package='cart_controller_pkg',
    #     executable='rail_service_node', # 'rail_control_node.py' ではない
    #     name='rail_service_node'
    # )

    # 3. エンドエフェクタ制御ノード (executable を修正済み)
    ee_node = Node(
        package='end_effector_pkg',
        executable='suction_module_service_node', # 'end_effector_node.py' ではない
        name='suction_module_service_node'
    )

    # 4. ビジョンサービスノード (executable を修正済み)
    vision_node = Node(
        package='vision_pkg',
        executable='vision_service', # 'vision_service_node.py' ではない
        name='vision_service',
        output='screen'
    )

    # 5. 自動収穫司令塔ノード (package を修正済み)
    auto_harvest_node = Node(
        package='teleop_demo_pkg', # 'harvest_task_pkg' ではない
        executable='crawler_automation', # (この名前を setup.py に登録する必要がある)
        name='crawler_automation',
        output='screen'
    )

    # 起動するノードのリスト
    return LaunchDescription([
        arm_node,
        # rail_node,
        ee_node,
        vision_node,
        auto_harvest_node
    ])