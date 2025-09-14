# master_control_node.py
# 接続確認と高信頼性通信を行う、最終版の司令塔ノード

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Point, Pose
from std_msgs.msg import String
import yaml
import time
import math
from tf_transformations import quaternion_from_euler
from toms_msg.srv import ArmService, RailService
from playsound import playsound #0910追加 音声ファイル再生用のライブラリ

class MasterControlNode(Node):
    def __init__(self):
        super().__init__('master_control_node')
        self.get_logger().info('teleop_demoを起動します。')
        
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        params = self.load_yaml(yaml_path)
        arm_params_yaml = params.get('arm_params', {'INIT_X': 0.0, 'INIT_Y': 180.0, 'INIT_ANG': 90.0})

        # 対策1: 高信頼性QoSプロファイルを作成
        # 最後のメッセージを記憶し(TRANSIENT_LOCAL)、確実に届ける(RELIABLE)設定
        reliable_qos = QoSProfile(
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        # === Publisher / Subscriber / Client の作成 ===
        self.pose_publisher = self.create_publisher(Pose, 'target_arm_pose', 10)
        self.ee_command_publisher = self.create_publisher(String, 'end_effector_command', reliable_qos) # ★★★ QoSを適用
        self.joy_subscriber = self.create_subscription(Joy, 'joy', self.joy_callback, 10)
        self.arm_client = self.create_client(ArmService, "arm_service")
        self.rail_client = self.create_client(RailService, 'rail_control')
        
        # 専門家ノードへの接続を待つ
        while not self.arm_client.wait_for_service(timeout_sec=1.0): self.get_logger().info('アームサービスを待機中...')
        while not self.rail_client.wait_for_service(timeout_sec=1.0): self.get_logger().info('レール制御サービスを待機中...')
        
        #対策2: エンドエフェクタドライバ(Subscriber)の接続を待つ
        self.get_logger().info('エンドエフェクタドライバの接続を待っています...')
        while self.count_subscribers('end_effector_command') == 0:
            time.sleep(0.5)
        self.get_logger().info('全てのノードに接続しました。')
        
        # === 内部変数の初期化 ===
        self.is_sequence_running = False
        self.is_resetting = False
        self.is_manual_locked = False
        self.latest_joy_msg = None
        self.rail_button_pressed = False
        self._reset_manual_state(arm_params_yaml)
        self.x_limit = {'min': -40.0, 'max': 250.0}
        self.y_limit = {'min': 0.0, 'max': 500.0}
        self.z_limit = {'min': 0.0, 'max': 450.0}
        self.angle_limit = {'min': -90.0, 'max': 90.0}
        self.sequence_step = 0
        self.wait_start_time = None
        self.wait_duration = None
        self.arm_future = None
        self.arm_request = ArmService.Request()

        self.declare_parameter('joy_params.x_axis', 0)
        self.declare_parameter('joy_params.y_axis', 1)
        self.declare_parameter('joy_params.z_axis', 5)
        self.declare_parameter('joy_params.angle_axis', 2)
        self.declare_parameter('joy_params.suction_start_button', 2)
        self.declare_parameter('joy_params.suction_stop_button', 3)
        self.declare_parameter('joy_params.rail_forward_button', 5)
        self.declare_parameter('joy_params.rail_backward_button', 4)
        self.declare_parameter('scale.xy', 50.0)
        self.declare_parameter('scale.z', 50.0) 
        self.declare_parameter('scale.angle', 90.0)
        self.timer = self.create_timer(0.05, self.main_loop)
        
        # 前回の各軸の値を記憶する変数
        self.previous_x_axis_value = 0.0
        self.previous_y_axis_value = 0.0
        self.previous_z_axis_value = 0.0
        
        # 接続確認後に初期コマンドを送信
        self.get_logger().info('初期化コマンドを送信します。')
        self.ee_command_publisher.publish(String(data='DISABLE_EDF'))

    def joy_callback(self, msg):
        self.latest_joy_msg = msg
        start_btn = self.get_parameter('joy_params.suction_start_button').value
        stop_btn = self.get_parameter('joy_params.suction_stop_button').value
        if msg.buttons[start_btn] == 1 and not self.is_sequence_running and not self.is_resetting:
            self.get_logger().info('======== 収穫シーケンスを開始します ========')
            playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/収穫シーケンス、開始なのだ.wav")
            self.is_sequence_running = True
            self.sequence_step = 0
        elif msg.buttons[stop_btn] == 1 and not self.is_resetting:
            self.get_logger().info('======== システムをリセットします ========')
            playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/システムリセットなのだ.wav")
            self.is_sequence_running = False
            self.arm_future = None
            self.wait_start_time = None
            self.is_resetting = True
            self.sequence_step = 100

    def main_loop(self):
        self.is_manual_locked = self.is_sequence_running or self.is_resetting
        if self.is_resetting: self.handle_reset_sequence()
        elif self.is_sequence_running: self.handle_harvest_sequence()
        self.handle_manual_control()
    
    def handle_manual_control(self):
        if self.latest_joy_msg is None: return
        forward_btn = self.get_parameter('joy_params.rail_forward_button').value
        backward_btn = self.get_parameter('joy_params.rail_backward_button').value
        if not self.is_manual_locked:
            if self.latest_joy_msg.buttons[forward_btn] == 1 and not self.rail_button_pressed: self.rail_button_pressed = True; playsound("/home/ylab/hibikino_toms_ws/src/cart_controller_pkg/cart_controller_pkg/sound/前.wav"); self.send_rail_request('f')
            elif self.latest_joy_msg.buttons[backward_btn] == 1 and not self.rail_button_pressed: self.rail_button_pressed = True; playsound("/home/ylab/hibikino_toms_ws/src/cart_controller_pkg/cart_controller_pkg/sound/後.wav"); self.send_rail_request('b')
            elif self.latest_joy_msg.buttons[forward_btn] == 0 and self.latest_joy_msg.buttons[backward_btn] == 0: self.rail_button_pressed = False
        else: self.rail_button_pressed = False
        if not self.is_manual_locked:
            x_axis = self.get_parameter('joy_params.x_axis').value
            y_axis = self.get_parameter('joy_params.y_axis').value
            z_axis = self.get_parameter('joy_params.z_axis').value
            angle_axis = self.get_parameter('joy_params.angle_axis').value
            scale_xy = self.get_parameter('scale.xy').value
            scale_z = self.get_parameter('scale.z').value
            scale_angle = self.get_parameter('scale.angle').value

            #0910追加 アーム上下・左右・前後・曲げ伸ばしで音声再生
            current_z_value = self.latest_joy_msg.axes[z_axis]
            current_x_value = self.latest_joy_msg.axes[x_axis]
            current_y_value = self.latest_joy_msg.axes[y_axis]
            deadzone = 0.1 # スティックの微小な動きを無視する閾値
            
            # Z軸の値が前回から変化した場合のみ、音声再生を試みる
            if current_z_value != self.previous_z_axis_value:
                # 入力値が閾値より大きい場合（上昇操作）
                if current_z_value > deadzone:
                    playsound("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/sound/上.wav")
                # 入力値が閾値より小さい場合（下降操作）
                elif current_z_value < -deadzone:
                    playsound("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/sound/下.wav")
            # 現在の値を"previous_z_axis_value"として保存する
            self.previous_z_axis_value = current_z_value

            # X軸の値が前回から変化した場合のみ、音声再生を試みる
            if current_x_value != self.previous_x_axis_value:
                # 入力値が閾値より大きい場合（左）
                if current_x_value > deadzone:
                    playsound("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/sound/左.wav")
                # 入力値が閾値より小さい場合（右）
                elif current_x_value < -deadzone:
                    playsound("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/sound/右.wav")
            # 現在の値を"previous_z_axis_value"として保存する
            self.previous_x_axis_value = current_x_value

            # Y軸の値が前回から変化した場合のみ、音声再生を試みる
            if current_y_value != self.previous_y_axis_value:
                # 入力値が閾値より大きい場合（伸ばし？）
                if current_y_value > deadzone:
                    playsound("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/sound/アームを伸ばすのだ.wav")
                # 入力値が閾値より小さい場合（曲げ？）
                elif current_y_value < -deadzone:
                    playsound("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/sound/アームを曲げるのだ.wav")
            # 現在の値を"previous_z_axis_value"として保存する
            self.previous_y_axis_value = current_y_value

            self.current_pos.x -= self.latest_joy_msg.axes[x_axis] * scale_xy * 0.1
            self.current_pos.y += self.latest_joy_msg.axes[y_axis] * scale_xy * 0.1
            self.current_pos.z += self.latest_joy_msg.axes[z_axis] * scale_z * 0.1
            self.current_angle_deg += self.latest_joy_msg.axes[angle_axis] * scale_angle * 0.1
            self.current_pos.x = max(self.x_limit['min'], min(self.x_limit['max'], self.current_pos.x))
            self.current_pos.y = max(self.y_limit['min'], min(self.y_limit['max'], self.current_pos.y))
            self.current_pos.z = max(self.z_limit['min'], min(self.z_limit['max'], self.current_pos.z))
            self.current_angle_deg = max(self.angle_limit['min'], min(self.angle_limit['max'], self.current_angle_deg))
            pose_msg = Pose()
            pose_msg.position = self.current_pos
            angle_rad = math.radians(self.current_angle_deg)
            q = quaternion_from_euler(0, 0, angle_rad)
            pose_msg.orientation.x, pose_msg.orientation.y, pose_msg.orientation.z, pose_msg.orientation.w = q[0], q[1], q[2], q[3]
            self.pose_publisher.publish(pose_msg)

    def _check_async_task_done(self):
        if self.arm_future and self.arm_future.done():
            try: result = self.arm_future.result()
            except Exception as e: self.get_logger().error(f"アームサービス呼び出しエラー: {e}"); self.trigger_reset_sequence(); return
            finally: self.arm_future, self.sequence_step = None, self.sequence_step + 1
        if self.wait_start_time and (time.time() - self.wait_start_time) >= self.wait_duration: self.wait_start_time, self.sequence_step = None, self.sequence_step + 1
        return self.arm_future or self.wait_start_time
        
    def handle_harvest_sequence(self):
        if self._check_async_task_done(): return
        if self.sequence_step == 0: self.get_logger().info('[STEP 0] 手動操作をロック'); self.arm_future = self.arm_send_request_lock_teleop_async()
        elif self.sequence_step == 1: cmd = 'ENABLE_EDF'; self.get_logger().info(f'[STEP 1] 吸引を開始 ({cmd})'); playsound("/home/ylab/hibikino_toms_ws/src/end_effector_pkg/end_effector_pkg/sound/ファンを起動するのだ.wav"); self.ee_command_publisher.publish(String(data=cmd)); self.set_wait_timer(8.0)
        elif self.sequence_step == 2: cmd = 'CLOSE_FINGER'; self.get_logger().info(f'[STEP 2] 顎を閉じます ({cmd})'); playsound("/home/ylab/hibikino_toms_ws/src/end_effector_pkg/end_effector_pkg/sound/顎を閉じるのだ.wav"); self.ee_command_publisher.publish(String(data=cmd)); self.set_wait_timer(8.0)
        elif self.sequence_step == 3: self.get_logger().info('[STEP 3] 収穫ボックスへ移動'); playsound("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/sound/トマトを収穫ボックスに入れるのだあ.wav"); self.arm_future = self.arm_send_request_box_async()
        elif self.sequence_step == 4: cmd = 'OPEN_FINGER'; self.get_logger().info(f'[STEP 4] 顎を開きます ({cmd})'); playsound("/home/ylab/hibikino_toms_ws/src/end_effector_pkg/end_effector_pkg/sound/顎を開くのだ.wav"); self.ee_command_publisher.publish(String(data=cmd)); self.set_wait_timer(8.0)
        elif self.sequence_step == 5: cmd = 'DISABLE_EDF'; self.get_logger().info(f'[STEP 5] 吸引を停止 ({cmd})');playsound("/home/ylab/hibikino_toms_ws/src/end_effector_pkg/end_effector_pkg/sound/ファンを停止するのだ.wav");  self.ee_command_publisher.publish(String(data=cmd)); self.set_wait_timer(6.0)
        elif self.sequence_step == 6: self.get_logger().info('[STEP 6] コントローラーの入力値をリセット'); self._reset_manual_state_from_yaml(); self.set_wait_timer(0.5)
        elif self.sequence_step == 7: self.get_logger().info('[STEP 7] アームとZ軸を初期位置へ移動します'); playsound("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/sound/アームをホームポジションに戻すのだあ.wav"); self.arm_future = self.arm_send_request_init_async()
        elif self.sequence_step == 8: self.get_logger().info('[STEP 8] 手動操作をアンロック'); self.arm_future = self.arm_send_request_unlock_teleop_async()
        elif self.sequence_step == 9: self.get_logger().info('======== 収穫シーケンスが完了しました ========'); self.is_sequence_running = False

    # (中略... handle_reset_sequence と ヘルパー関数群は変更なし)
    def handle_reset_sequence(self):
        if self._check_async_task_done(): return
        if self.sequence_step == 100: self.get_logger().info('[RESET 1] 手動操作をロック'); self.arm_future = self.arm_send_request_lock_teleop_async()
        elif self.sequence_step == 101: cmd = 'DISABLE_EDF'; self.get_logger().info(f'[RESET 2] エンドエフェクタをOFF ({cmd})'); self.ee_command_publisher.publish(String(data=cmd)); self.set_wait_timer(1.0)
        elif self.sequence_step == 102: cmd = 'OPEN_FINGER'; self.get_logger().info(f'[RESET 3] 顎を開きます ({cmd})');playsound("/home/ylab/hibikino_toms_ws/src/end_effector_pkg/end_effector_pkg/sound/顎を開くのだ.wav"); self.ee_command_publisher.publish(String(data=cmd)); self.set_wait_timer(5.0)
        elif self.sequence_step == 103: self.get_logger().info('[RESET 4] コントローラーの入力値をリセット'); self._reset_manual_state_from_yaml(); self.set_wait_timer(0.5)
        elif self.sequence_step == 104: self.get_logger().info('[RESET 5] アームとZ軸を初期位置へ移動します'); playsound("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/sound/アームをホームポジションに戻すのだあ.wav"); self.arm_future = self.arm_send_request_init_async()
        elif self.sequence_step == 105: self.get_logger().info('[RESET 6] 手動操作をアンロック'); self.arm_future = self.arm_send_request_unlock_teleop_async()
        elif self.sequence_step == 106: self.get_logger().info('======== システムのリセットが完了しました ========'); self.is_resetting = False
    def _reset_manual_state(self, arm_params):
        self.current_pos = Point(); self.current_pos.x = float(arm_params['INIT_X']); self.current_pos.y = float(arm_params['INIT_Y']); self.current_pos.z = 0.0; self.current_angle_deg = float(arm_params['INIT_ANG'])
        self.get_logger().info(f"コントローラーの入力値をリセット: Pos:[{self.current_pos.x:.1f},{self.current_pos.y:.1f},{self.current_pos.z:.1f}], Ang:{self.current_angle_deg:.1f}")
    def trigger_reset_sequence(self):
        if not self.is_resetting: self.is_sequence_running = False; self.arm_future = None; self.wait_start_time = None; self.is_resetting = True; self.sequence_step = 100
    def _reset_manual_state_from_yaml(self):
        try: yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'; file = open(yaml_path, 'r'); params = yaml.safe_load(file); arm_params_yaml = params['arm_params']; self._reset_manual_state(arm_params_yaml)
        except (FileNotFoundError, KeyError) as e: self.get_logger().error(f"YAML読み込みエラー: {e}")
    def set_wait_timer(self, duration_sec): self.get_logger().info(f'{duration_sec:.1f}秒待機...'); self.wait_start_time, self.wait_duration = time.time(), duration_sec
    def send_rail_request(self, direction): self.rail_client.call_async(RailService.Request(req_dir=direction))
    def arm_send_request_box_async(self): self.arm_request.task = "move_to_box"; return self.arm_client.call_async(self.arm_request)
    def arm_send_request_init_async(self): self.arm_request.task = "init_arm"; return self.arm_client.call_async(self.arm_request)
    def arm_send_request_lock_teleop_async(self): self.arm_request.task = "lock_teleop"; return self.arm_client.call_async(self.arm_request)
    def arm_send_request_unlock_teleop_async(self): self.arm_request.task = "unlock_teleop"; return self.arm_client.call_async(self.arm_request)
    @staticmethod
    def load_yaml(file_path):
        with open(file_path, "r") as file: return yaml.safe_load(file)

# (中略... main関数は変更なし)
def main(args=None):
    rclpy.init(args=args)
    node = MasterControlNode()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally: node.destroy_node()
    rclpy.shutdown()
if __name__ == '__main__':
    main()