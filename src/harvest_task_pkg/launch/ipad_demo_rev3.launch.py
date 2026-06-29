# launch/ipad_demo.py

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():

    #1. アーム制御ノード
    arm_node = Node(
        package='arm_controller_pkg',
        executable='arm_controller',
        name='arm_controller'
    )

    # 2. レール制御ノード 
    rail_node = Node(
        package='cart_controller_pkg',
        executable='rail_service_node', # 'rail_control_node.py' ではない
        name='rail_service_node'
    )
    # 3. エンドエフェクタ制御ノード
    ee_node = Node(
        package='end_effector_pkg',
        executable='suction_module_service_node', # 'end_effector_node.py' ではない
        name='suction_module_service_node'
    )
    # # 4. 映像ストリーミングノード
    # vision_node = Node(
    #     package='vision_pkg',
    #     executable='cam_pub_service_rev2', # 'vision_service_node.py' ではない
    #     name='cam_pub_service_rev2',
    #     output='screen'
    # )

    #5.ビジョンサービスノード （物体検出）
    vision_streaming_node = Node(
        package='vision_pkg',
        executable='vision_service_ipad_rev2',
        name='vision_service_ipad_rev2'
    ) 

    #6. webからのリクエストを中継するノード
    ipad_demo_sync_node = Node(
        package='harvest_task_pkg',
        executable='ipad_demo_sync_relay_rev2'
    )

    return LaunchDescription([
        arm_node,
        rail_node,
        ee_node,
        # vision_node,
        vision_streaming_node,
        ipad_demo_sync_node
    ])