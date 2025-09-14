import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():

    # set_params.yamlファイルへのパスを取得
    # 'your_workspace' と 'your_module_name' は実際の環境に合わせてください。
    # この例では、アップロードされたリポジトリの構造に基づいています。
    # yaml_file = os.path.join(
    #     '/home/ylab/hibikino_toms_ws/module', # ワークスペースのルートからの絶対パス
    #     'set_params.yaml'
    # )

    # パッケージの共有ディレクトリからパスを取得するより堅牢な方法
    # ただし、'module'はROSパッケージではないため、この方法は使えません。
    # 上記の絶対パス指定を使用してください。

    # TwistからPWMに変換するノード
    twist_converter_node = Node(
        package='cart_controller_pkg',
        executable='twist_to_crawler_converter',
        name='twist_to_crawler_converter',
        output='screen',
        parameters=[{
            'tread': 0.21,                # クローラーのトレッド幅(m)をここに設定
            'max_linear_speed': 0.5,      # 最大速度(m/s)をここに設定
        }]
    )

    # PWM値をシリアル経由でPicoに送信するノード
    serial_controller_node = Node(
        package='crawler_robot_pkg',
        executable='crawler_controller_serial',
        name='crawler_controller_serial',
        output='screen',
        parameters=[{
            # YAMLファイルの絶対パスを指定
            'yaml_file_path': '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        }]
    )

    # teleop_twist_keyboardノード（キーボード操作用）
    # このノードは別のターミナルで手動で起動しても良いですが、
    # launchファイルに含めると便利です。
    teleop_keyboard_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        output='screen',
        prefix='xterm -e'  # 新しいターミナルウィンドウで起動
    )

    return LaunchDescription([
        twist_converter_node,
        serial_controller_node,
        teleop_keyboard_node
    ])
