#
# @file teleop_node.py
# @brief Joyパッドでアーム、エンドエフェクタ、レールを遠隔操作するためのノード
#
# @details
# /joyトピックからコントローラ入力を受け取り、アーム、エンドエフェクタ、
# レールへのコマンドを配信/送信します。
#
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Point
from std_msgs.msg import String, Float32, Bool
import yaml
from toms_msg.srv import RailService
import time

class TeleopNode(Node):
    """
    @class TeleopNode
    @brief Joyパッド入力を目標座標、目標角度、コマンドに変換するクラス
    """
    def __init__(self):
        """
        @brief コンストラクタ。
        """
        super().__init__('teleop_node')
                
        # --- PublisherとSubscriberの作成 ---
        self.pos_publisher = self.create_publisher(Point, 'target_arm_pos', 10)
        self.angle_publisher = self.create_publisher(Float32, 'target_arm_angle', 10)
        self.cmd_publisher = self.create_publisher(String, 'suction_command', 10)
        self.joy_subscriber = self.create_subscription(Joy, 'joy', self.joy_callback, 10)
        self.reset_subscriber = self.create_subscription(Bool, '/teleop/reset_state', self.reset_callback, 10)
        
        # ★★★ 変更点 1/5: ロック状態を管理する変数と、状態を受け取るSubscriberを追加 ★★★
        self.is_locked = False
        self.lock_subscriber = self.create_subscription(Bool, '/teleop/lock_state', self.lock_state_callback, 10)

        # レール制御サービスのクライアントを作成
        self.rail_client = self.create_client(RailService, 'rail_control')
        while not self.rail_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('レール制御サービスが見つかりません。待機中...')
        self.get_logger().info('レール制御サービスに接続しました。')
        self.rail_button_pressed = False

        # --- パラメータ設定 ---
        self.declare_parameter('x_axis', 0)
        self.declare_parameter('y_axis', 1)
        self.declare_parameter('z_axis', 5)
        self.declare_parameter('angle_axis', 2)
        self.declare_parameter('suction_start_button', 2)
        self.declare_parameter('suction_stop_button', 3)
        self.declare_parameter('rail_forward_button', 5)
        self.declare_parameter('rail_backward_button', 4)
        
        self.declare_parameter('scale_xy', 50.0)
        self.declare_parameter('scale_z', 50.0)
        self.declare_parameter('scale_angle', 90.0)

        self._reset_state_from_yaml()

        self.timer = self.create_timer(0.06, self.publish_position)
        self.latest_joy_msg = None

        # 可動範囲の制限を定義
        self.x_limit = {'min': -40.0, 'max': 250.0}
        self.y_limit = {'min': 0.0, 'max': 500.0}
        self.z_limit = {'min': 0.0, 'max': 450.0}
        self.angle_limit = {'min': -90.0, 'max': 90.0}
        
        self.log_period = 1.0
        self.last_log_time = time.time()
        
        self.get_logger().info("Teleop Node with Rail Control has been started.")
        self.get_logger().info("左スティック:XY, 十字キー上下:Z, 右スティック左右:角度")
        self.get_logger().info("B:吸引開始, Y:吸引停止, LB/RB:レール移動")

    def _reset_state_from_yaml(self):
        # ... (変更なし)
        self.get_logger().info('コントローラーの状態をYAMLファイルからリセットします。')
        try:
            yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
            with open(yaml_path, 'r') as file:
                params = yaml.safe_load(file)
            arm_params = params['arm_params']
        except (FileNotFoundError, KeyError) as e:
            self.get_logger().error(f"YAMLからアームのパラメータを読み込めませんでした: {e}")
            self.get_logger().info("デフォルトの初期値を使用します。")
            arm_params = {'INIT_X': 0.0, 'INIT_Y': 180.0, 'INIT_ANG': 90.0}

        self.current_pos = Point()
        self.current_pos.x = float(arm_params['INIT_X'])
        self.current_pos.y = float(arm_params['INIT_Y'])
        self.current_pos.z = 0.0
        self.current_angle = float(arm_params['INIT_ANG'])
        self.get_logger().info(f"リセット後の状態: Pos: [X:{self.current_pos.x:.2f}, Y:{self.current_pos.y:.2f}, Z:{self.current_pos.z:.2f}], Angle: {self.current_angle:.2f}")

    def reset_callback(self, msg):
        # ... (変更なし)
        if msg.data:
            self.get_logger().info('/teleop/reset_state トピックを受信。状態をリセットします。')
            self._reset_state_from_yaml()

    # ★★★ 変更点 2/5: ロック状態を更新するためのコールバック関数を追加 ★★★
    def lock_state_callback(self, msg):
        """ロック状態を受け取り、フラグを更新するコールバック"""
        if self.is_locked != msg.data:
            self.is_locked = msg.data
            if self.is_locked:
                self.get_logger().warn('収穫シーケンス中のため、手動操作はロックされました。')
            else:
                self.get_logger().info('手動操作のロックが解除されました。')

    def joy_callback(self, msg):
        self.latest_joy_msg = msg
        start_btn = self.get_parameter('suction_start_button').value
        stop_btn = self.get_parameter('suction_stop_button').value
        cmd_msg = String()
        
        # Bボタン(吸引開始)とYボタン(吸引停止)の操作はロック状態に関わらず常に許可
        if msg.buttons[start_btn] == 1:
            cmd_msg.data = 'START_SUCTION'
            self.cmd_publisher.publish(cmd_msg)
            self.get_logger().info(f"Published command: {cmd_msg.data}")
        elif msg.buttons[stop_btn] == 1:
            cmd_msg.data = 'STOP_SUCTION'
            self.cmd_publisher.publish(cmd_msg)
            self.get_logger().info(f"Published command: {cmd_msg.data}")

        # ★★★ 変更点 3/5: ロック状態でない場合のみ、レール移動を許可 ★★★
        if not self.is_locked:
            forward_btn = self.get_parameter('rail_forward_button').value
            backward_btn = self.get_parameter('rail_backward_button').value
            if msg.buttons[forward_btn] == 1 and not self.rail_button_pressed:
                self.rail_button_pressed = True
                self.send_rail_request('f')
            elif msg.buttons[backward_btn] == 1 and not self.rail_button_pressed:
                self.rail_button_pressed = True
                self.send_rail_request('b')
            elif msg.buttons[forward_btn] == 0 and msg.buttons[backward_btn] == 0:
                self.rail_button_pressed = False
        else:
            # ロック中はボタンが押されていない状態として扱う
            self.rail_button_pressed = False

    def send_rail_request(self, direction):
        # ... (変更なし)
        request = RailService.Request()
        request.req_dir = direction
        future = self.rail_client.call_async(request)
        self.get_logger().info(f"レールを '{direction}' 方向へ動かすリクエストを送信。")

    def publish_position(self):
        # ★★★ 変更点 4/5: ロック中はジョイスティックによるアーム/Z軸操作も無視する ★★★
        if self.latest_joy_msg is None or self.is_locked:
            return

        x_axis = self.get_parameter('x_axis').value
        y_axis = self.get_parameter('y_axis').value
        z_axis = self.get_parameter('z_axis').value
        angle_axis = self.get_parameter('angle_axis').value
        scale_xy = self.get_parameter('scale_xy').value
        scale_z = self.get_parameter('scale_z').value
        scale_angle = self.get_parameter('scale_angle').value

        self.current_pos.x -= self.latest_joy_msg.axes[x_axis] * scale_xy * 0.1
        self.current_pos.y += self.latest_joy_msg.axes[y_axis] * scale_xy * 0.1
        self.current_pos.z += self.latest_joy_msg.axes[z_axis] * scale_z * 0.1
        self.current_angle += self.latest_joy_msg.axes[angle_axis] * scale_angle * 0.1

        self.current_pos.x = max(self.x_limit['min'], min(self.x_limit['max'], self.current_pos.x))
        self.current_pos.y = max(self.y_limit['min'], min(self.y_limit['max'], self.current_pos.y))
        self.current_pos.z = max(self.z_limit['min'], min(self.z_limit['max'], self.current_pos.z))
        self.current_angle = max(self.angle_limit['min'], min(self.angle_limit['max'], self.current_angle))

        self.pos_publisher.publish(self.current_pos)
        
        angle_msg = Float32()
        angle_msg.data = self.current_angle
        self.angle_publisher.publish(angle_msg)

        current_time = time.time()
        if current_time - self.last_log_time >= self.log_period:
            self.get_logger().info(
                f"Publishing -> Pos: [X:{self.current_pos.x:.2f}, Y:{self.current_pos.y:.2f}, Z:{self.current_pos.z:.2f}], Angle: {self.current_angle:.2f}"
            )
            self.last_log_time = current_time

# ★★★ 変更点 5/5: インポート文のtimeを削除（元からあったため修正なし） ★★★
# main関数は変更ありません

def main(args=None):
    rclpy.init(args=args)
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