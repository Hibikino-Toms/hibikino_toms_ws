import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():

    # TwistからPWMに変換するノード
    twist_converter_node = Node(
        package='cart_controller_pkg',
        executable='twist_to_crawler_converter',
        name='twist_to_crawler_converter',
        output='screen',
        remappings=[('/cmd_vel', '/cmd_vel_cr'),]
    )

    # PWM値をシリアル経由でPicoに送信するノード
    serial_controller_node = Node(
        package='crawler_robot_pkg',
        executable='crawler_controller_serial',
        name='crawler_controller_serial',
        output='screen'
    )

    # teleop_twist_keyboardノード（キーボード操作用）
    # このノードは別のターミナルで手動で起動しても良いですが、
    # launchファイルに含めると便利です。
    teleop_keyboard_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        output='screen',
        prefix='xterm -e',  # 新しいターミナルウィンドウで起動
        remappings=[('/cmd_vel', '/cmd_vel_cr'),]
    )

    return LaunchDescription([
        twist_converter_node,
        serial_controller_node,
        teleop_keyboard_node
    ])
