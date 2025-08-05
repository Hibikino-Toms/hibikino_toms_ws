#
# @file teleop_node.py
# @brief Joyパッドでアームとエンドエフェクタを遠隔操作するためのノード
#
# @details
# /joyトピックからコントローラ入力を受け取り、アームの目標座標、目標角度、
# エンドエフェクタへのコマンドをそれぞれのトピックに配信します。
#
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Point
from std_msgs.msg import String, Float32
import yaml

class TeleopNode(Node):
    """
    @class TeleopNode
    @brief Joyパッド入力を目標座標、目標角度、コマンドに変換するクラス
    """
    def __init__(self):
        """
        @brief コンストラクタ。ノード、Publisher、Subscriberの初期化を行う。
        @param[in] self インスタンス自身
        @param[out] なし
        @details
        - ノード、Publisher、Subscriberを初期化します。
        - Logicool F310の軸・ボタン配置をパラメータとして設定します。
        - アームの現在座標と角度を保持する変数を初期化します。
        """
        super().__init__('teleop_node')

        # YAMLファイルから初期値を読み込み
        try:
            yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
            with open(yaml_path, 'r') as file:
                params = yaml.safe_load(file)
            arm_params = params['arm_params']
            self.get_logger().info(f"Loaded initial arm parameters from {yaml_path}")
        except (FileNotFoundError, KeyError) as e:
            self.get_logger().error(f"Failed to load arm parameters from YAML: {e}")
            self.get_logger().info("Using default initial values as fallback.")
            # ファイル読み込み失敗時のデフォルト値
            arm_params = {'INIT_X': 0.0, 'INIT_Y': 180.0, 'INIT_ANG': 90.0}
                
        # PublisherとSubscriberの作成
        self.pos_publisher = self.create_publisher(Point, 'target_arm_pos', 10)
        self.angle_publisher = self.create_publisher(Float32, 'target_arm_angle', 10) # 角度用のPublisherを追加
        self.cmd_publisher = self.create_publisher(String, 'suction_command', 10)
        self.joy_subscriber = self.create_subscription(Joy, 'joy', self.joy_callback, 10)

        # パラメータ設定 (Logicool F310 D-Inputモードを想定)
        self.declare_parameter('x_axis', 0) # 左スティック左右 (正が左)
        self.declare_parameter('y_axis', 1) # 左スティック上下 (正が上)
        self.declare_parameter('z_axis', 5) # 十字ボタン上下 (正が上)
        self.declare_parameter('angle_axis', 2) # 右スティック左右 (正が左) を角度に割当
        self.declare_parameter('suction_start_button', 2) # Bボタン
        self.declare_parameter('suction_stop_button', 3)  # Yボタン
        self.declare_parameter('scale_xy', 50.0) # XY方向の移動スケール (mm/s)
        self.declare_parameter('scale_z', 50.0)  # Z方向の移動スケール (mm/s)
        self.declare_parameter('scale_angle', 90.0) # 角度の移動スケール (deg/s)

        # アームの現在位置と角度をYAMLから読み込んだ値で初期化
        self.current_pos = Point()
        self.current_pos.x = float(arm_params['INIT_X'])
        self.current_pos.y = float(arm_params['INIT_Y'])
        self.current_pos.z = 0.0  # Z軸の初期値は0.0に設定
        self.current_angle = float(arm_params['INIT_ANG'])

        # タイマーの作成 (10Hzで座標と角度を配信)
        self.timer = self.create_timer(0.1, self.publish_position)
        self.latest_joy_msg = None
        
        self.get_logger().info("Teleop Node has been started.")
        self.get_logger().info("左スティック:XY, 十字キー上下:Z, 右スティック左右:角度, B:吸引開始, Y:吸引停止")

    def joy_callback(self, msg):
        """
        @brief /joyトピックを受信した際のコールバック関数
        @param[in] msg sensor_msgs/msg/Joy型のメッセージ
        @details
        受信した最新のJoyメッセージを保持し、ボタン入力があった場合は即座にコマンドを配信します。
        座標と角度の更新・配信はタイマーコールバックで行います。
        """
        self.latest_joy_msg = msg
        
        start_btn = self.get_parameter('suction_start_button').value
        stop_btn = self.get_parameter('suction_stop_button').value
        
        # ボタン入力でコマンドをPublish
        cmd_msg = String()
        if msg.buttons[start_btn] == 1:
            cmd_msg.data = 'START_SUCTION'
            self.cmd_publisher.publish(cmd_msg)
            self.get_logger().info(f"Published command: {cmd_msg.data}")
        elif msg.buttons[stop_btn] == 1:
            cmd_msg.data = 'STOP_SUCTION'
            self.cmd_publisher.publish(cmd_msg)
            self.get_logger().info(f"Published command: {cmd_msg.data}")

    def publish_position(self):
        """
        @brief タイマーで定期的に呼ばれ、目標座標と角度を更新・配信する関数
        @param[in] self インスタンス自身
        @param[out] なし
        @details
        最新のJoyメッセージに基づきアームの目標座標と角度を計算し、
        それぞれのトピックで配信します。
        """
        if self.latest_joy_msg is None:
            return

        # パラメータの取得
        x_axis = self.get_parameter('x_axis').value
        y_axis = self.get_parameter('y_axis').value
        z_axis = self.get_parameter('z_axis').value
        angle_axis = self.get_parameter('angle_axis').value # 角度用の軸パラメータを取得
        scale_xy = self.get_parameter('scale_xy').value
        scale_z = self.get_parameter('scale_z').value
        scale_angle = self.get_parameter('scale_angle').value # 角度用のスケールを取得

        # スティック入力で目標座標を更新 (アーム座標系の軸方向と合わせるため、xに-1を乗算)
        # アーム座標系 X:正が右 Y:正が前方 Z:正が上
        # 0.1はタイマー周期(10Hz)
        self.current_pos.x -= self.latest_joy_msg.axes[x_axis] * scale_xy * 0.1
        self.current_pos.y += self.latest_joy_msg.axes[y_axis] * scale_xy * 0.1
        self.current_pos.z += self.latest_joy_msg.axes[z_axis] * scale_z * 0.1
        
        # スティック入力で目標角度を更新
        self.current_angle += self.latest_joy_msg.axes[angle_axis] * scale_angle * 0.1

        # 目標座標をPublish
        self.pos_publisher.publish(self.current_pos)
        
        # 目標角度をPublish
        angle_msg = Float32()
        angle_msg.data = self.current_angle
        self.angle_publisher.publish(angle_msg)

        # ターミナルに現在の配信値を表示
        self.get_logger().info(
        f"Publishing -> "
        f"Pos: [X:{self.current_pos.x:8.2f}, Y:{self.current_pos.y:8.2f}, Z:{self.current_pos.z:8.2f}], "
        f"Angle: {self.current_angle:8.2f}"
        )

def main(args=None):
    rclpy.init(args=args)
    # joyノードを起動するのを忘れないように注意
    # ros2 run joy joy_node
    node = TeleopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()