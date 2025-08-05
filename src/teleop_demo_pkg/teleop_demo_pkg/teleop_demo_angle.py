#
# @file joy_teleop_node.py
# @brief Joyパッドでアームとエンドエフェクタを遠隔操作するためのノード (関節空間操作版)
#
# @details
# /joyトピックからコントローラ入力を受け取り、各モーターの目標角度と
# Z軸の目標位置、エンドエフェクタへのコマンドをそれぞれのトピックに配信します。
#
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import String, Float32MultiArray, Float32
import yaml
import os

class JoyTeleopAngleNode(Node):
    """
    @class JoyTeleopAngleNode
    @brief Joyパッド入力を各モーターの目標角度とコマンドに変換するクラス
    """
    def __init__(self):
        """
        @brief コンストラクタ。ノード、Publisher、Subscriber、パラメータの初期化を行う。
        """
        super().__init__('joy_teleop_angle_node')

        # --- パラメータとYAMLファイルの読み込み ---
        # パスはご自身の環境に合わせて修正してください
        yaml_path = os.path.expanduser('~/hibikino_toms_ws/module/set_params.yaml')
        params = self.load_yaml(yaml_path)
        dxl_params = params.get("dxl_params", {})

        # モーターのホーム角度と可動範囲を読み込む
        # set_params.yamlのDXL_HOME_ANGLEはモーターID[1,3,5]に対応すると想定
        self.home_angles = dxl_params.get("DXL_HOME_ANGLE", [95.0, 260.0, 95.0])
        self.current_angles = list(self.home_angles) # 現在角度をホーム角度で初期化

        # 可動範囲 [ (min1, max1), (min3, max3), (min5, max5) ]
        self.angle_limits = [
            (dxl_params.get("DXL_1_MIN_DEG", 0), dxl_params.get("DXL_1_MAX_DEG", 360)),
            (dxl_params.get("DXL_3_MIN_DEG", 0), dxl_params.get("DXL_3_MAX_DEG", 360)),
            (dxl_params.get("DXL_5_MIN_DEG", 0), dxl_params.get("DXL_5_MAX_DEG", 360)),
        ]
        
        # Z軸の現在位置
        self.current_z = 0.0

        # --- PublisherとSubscriberの作成 ---
        # 変更点：目標座標ではなく、目標角度とZ軸位置を配信する
        self.angle_publisher = self.create_publisher(Float32MultiArray, 'target_arm_angles', 10)
        self.z_pos_publisher = self.create_publisher(Float32, 'target_z_pos', 10)
        self.cmd_publisher = self.create_publisher(String, 'suction_command', 10)
        self.joy_subscriber = self.create_subscription(Joy, 'joy', self.joy_callback, 10)

        # --- パラメータ設定 (Logicool F310 D-Inputモードを想定) ---
        # 操作系をモーター角度の増減に割り当て
        self.declare_parameter('motor1_axis', 0)  # 左スティック左右 -> Motor 1
        self.declare_parameter('motor3_axis', 1)  # 左スティック上下 -> Motor 3
        self.declare_parameter('motor5_axis', 4)  # 右スティック上下 -> Motor 5
        self.declare_parameter('z_axis', 5)       # 十字キー上下 -> Z軸
        
        self.declare_parameter('suction_start_button', 1) # Bボタン
        self.declare_parameter('suction_stop_button', 3)  # Yボタン
        
        self.declare_parameter('angle_scale', 20.0) # 角度の移動スケール (deg/s)
        self.declare_parameter('z_scale', 50.0)     # Z方向の移動スケール (mm/s)

        # タイマーの作成 (20Hzで指令を配信)
        self.timer = self.create_timer(0.05, self.publish_commands)
        self.latest_joy_msg = None
        
        self.get_logger().info("Joy Teleop Angle Node has been started.")
        self.get_logger().info("左スティック:モータ1,3 / 右スティック:モータ5 / 十字キー:Z軸 / B:吸引開始 / Y:吸引停止")

    def joy_callback(self, msg):
        """
        @brief /joyトピックを受信した際のコールバック関数
        """
        self.latest_joy_msg = msg
        
        start_btn = self.get_parameter('suction_start_button').value
        stop_btn = self.get_parameter('suction_stop_button').value
        
        # ボタン入力は即座にコマンドをPublish
        cmd_msg = String()
        if msg.buttons[start_btn] == 1:
            cmd_msg.data = 'START_SUCTION'
            self.cmd_publisher.publish(cmd_msg)
            self.get_logger().info(f"Published command: {cmd_msg.data}")
        elif msg.buttons[stop_btn] == 1:
            cmd_msg.data = 'STOP_SUCTION'
            self.cmd_publisher.publish(cmd_msg)
            self.get_logger().info(f"Published command: {cmd_msg.data}")

    def publish_commands(self):
        """
        @brief タイマーで定期的に呼ばれ、目標角度とZ位置を更新・配信する関数
        """
        if self.latest_joy_msg is None:
            return

        # パラメータの取得
        axes = [
            self.get_parameter('motor1_axis').value,
            self.get_parameter('motor3_axis').value,
            self.get_parameter('motor5_axis').value,
        ]
        z_axis = self.get_parameter('z_axis').value
        angle_scale = self.get_parameter('angle_scale').value
        z_scale = self.get_parameter('z_scale').value
        dt = 0.05 # タイマー周期

        # --- モーター角度の更新 ---
        # スティック入力で目標角度を更新
        for i in range(3):
            # F310の軸入力は-1.0から1.0。スティックの方向とモーターの回転方向を合わせるため-1を乗算
            increment = -self.latest_joy_msg.axes[axes[i]] * angle_scale * dt
            self.current_angles[i] += increment
            # 可動範囲内に角度を制限する (clamp)
            self.current_angles[i] = max(self.angle_limits[i][0], min(self.angle_limits[i][1], self.current_angles[i]))

        # --- Z軸位置の更新 ---
        self.current_z -= self.latest_joy_msg.axes[z_axis] * z_scale * dt
        # Z軸の可動範囲も必要であればここで制限を追加
        
        # --- メッセージの作成と配信 ---
        # 角度メッセージ
        angle_msg = Float32MultiArray()
        angle_msg.data = self.current_angles
        self.angle_publisher.publish(angle_msg)
        
        # Z位置メッセージ
        z_msg = Float32()
        z_msg.data = self.current_z
        self.z_pos_publisher.publish(z_msg)

    @staticmethod
    def load_yaml(file_path):
        """YAMLファイルを読み込むヘルパー関数"""
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        except (FileNotFoundError, yaml.YAMLError) as e:
            print(f"Error loading YAML file: {e}")
            return {}

def main(args=None):
    rclpy.init(args=args)
    node = JoyTeleopAngleNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

# ===================================================================
# このノードに合わせて、arm_control_node.pyは以下のように変更する必要があります。
#
# 1. Subscriberの変更:
#    - geometry_msgs/msg/Point の代わりに std_msgs/msg/Float32MultiArray と std_msgs/msg/Float32 をインポート
#    - Subscriberを2つ作成
#      self.angle_subscriber = self.create_subscription(Float32MultiArray, 'target_arm_angles', self.angle_callback, 10)
#      self.z_pos_subscriber = self.create_subscription(Float32, 'target_z_pos', self.z_pos_callback, 10)
#
# 2. コールバック関数の変更:
#    - 逆運動学の計算はすべて不要になります。
#    - angle_callback:
#      - 受け取ったメッセージ (msg.data) には、モーターID[1,3,5]の目標角度が直接入っています。
#      - このままだとモーターID[2,4]の角度が足りないので、現在の角度を読み込むか、固定値を設定する必要があります。
#      - 例： all_motor_angles = [0.0] * 5
#            all_motor_angles[0] = msg.data[0] # ID 1
#            all_motor_angles[2] = msg.data[1] # ID 3
#            all_motor_angles[4] = msg.data[2] # ID 5
#            # ID 2, 4 は固定値または現在の値を設定
#            all_motor_angles[1] = 180.0 # 例
#            all_motor_angles[3] = 180.0 # 例
#      - self.arm_controller.move_motors(all_motor_angles, task="target") を呼び出す。
#    - z_pos_callback:
#      - 受け取ったメッセージ (msg.data) はZ軸の目標位置です。
#      - self.z_controller.move2target(msg.data) を呼び出す。
# ===================================================================
