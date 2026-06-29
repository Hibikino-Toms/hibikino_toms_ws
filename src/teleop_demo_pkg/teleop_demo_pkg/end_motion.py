import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
import serial, serial.tools.list_ports, time, yaml
from toms_msg.srv import ArmService

class SuctionControlNode(Node):
    def __init__(self):
        super().__init__('suction_control_node')
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        params, EE_params = self.load_yaml(yaml_path), self.load_yaml(yaml_path)["EE_params"]
        serial_number, BAUDRATE = EE_params["EE_PICO_SERIAL_NUMBER"], EE_params["BAUDRATE"]
        DEVICENAME = self.select_device(serial_number)
        if DEVICENAME is None: raise RuntimeError("EE用のマイコンが接続されていません。")
        self.end_effector_ser = serial.Serial(DEVICENAME, BAUDRATE, timeout=1.0)
        self.FOTO_VAL, self.EDF_VAL = EE_params["FOTO_VAL"], EE_params["EDF_VAL"]
        
        self.cmd_subscriber = self.create_subscription(String, 'suction_command', self.command_callback, 10)
        self.arm_client = self.create_client(ArmService, "arm_service")
        
        self.teleop_reset_publisher = self.create_publisher(Bool, '/teleop/reset_state', 10)
        # ★★★ 変更点 1/3: 手動操作のロック状態を配信するPublisherを追加 ★★★
        self.teleop_lock_publisher = self.create_publisher(Bool, '/teleop/lock_state', 10)

        while not self.arm_client.wait_for_service(timeout_sec=1.0): self.get_logger().info('アームサービスを待機中...')
        self.arm_request = ArmService.Request()
        
        self.is_sequence_running = False
        self.is_resetting = False
        
        self.sequence_step = 0
        self.wait_start_time = None
        self.wait_duration = None
        self.arm_future = None
        
        self.sequence_timer = self.create_timer(0.1, self.sequence_callback)
        self.get_logger().info('Suction Control Node has been started.')
        self.disable_edf()

    def command_callback(self, msg):
        command = msg.data
        if command == 'START_SUCTION':
            if self.is_resetting or self.is_sequence_running:
                self.get_logger().warn('他のシーケンスが実行中です。')
                return
            self.get_logger().info('======== 収穫シーケンスを開始します ========')
            self.is_sequence_running, self.sequence_step = True, 0
            
        elif command == 'STOP_SUCTION':
            if self.is_resetting:
                self.get_logger().warn('リセット動作は既に実行中です。')
                return
            self.get_logger().info('Yボタンが押されました。システムを安全に初期化します。')
            self.is_sequence_running = False
            self.arm_future = None
            self.wait_start_time = None
            self.is_resetting = True
            self.sequence_step = 100

    def sequence_callback(self):
        # 常にリセットシーケンスを優先
        if self.is_resetting:
            self.handle_reset_sequence()
            return
        if not self.is_sequence_running: return

        # --- 収穫シーケンスの状態管理 ---
        if self.arm_future and self.arm_future.done():
            try:
                result = self.arm_future.result()
                if not result.task_comp: self.get_logger().error("アームサービス失敗。中断します。"); self.start_reset_sequence(); return
            except Exception as e: self.get_logger().error(f"アームサービス呼び出しエラー: {e}"); self.start_reset_sequence(); return
            finally: self.arm_future, self.sequence_step = None, self.sequence_step + 1
        
        if self.wait_start_time and (time.time() - self.wait_start_time) >= self.wait_duration:
            self.wait_start_time, self.sequence_step = None, self.sequence_step + 1
        
        if self.arm_future or self.wait_start_time: return

        # --- 収穫シーケンスのステップ実行 ---
        # ★★★ 変更点 2/3: シーケンス開始時にロック有効、終了時にロック解除の信号を送る ★★★
        if self.sequence_step == 0:
            self.get_logger().info('[STEP 0] 手動操作をロック')
            lock_msg = Bool(); lock_msg.data = True
            self.teleop_lock_publisher.publish(lock_msg) # ロック有効を通知
            self.arm_future = self.arm_send_request_lock_teleop_async()
        elif self.sequence_step == 1: self.get_logger().info('[STEP 1] 吸引を開始'); self.enable_edf(); self.set_wait_timer(8.0)
        elif self.sequence_step == 2: self.get_logger().info('[STEP 2] 顎を閉じます'); self.close_finger(); self.set_wait_timer(8.0)
        elif self.sequence_step == 3: self.get_logger().info('[STEP 3] 収穫ボックスへ移動'); self.arm_future = self.arm_send_request_box_async()
        elif self.sequence_step == 4: self.get_logger().info('[STEP 4] 顎を開きます'); self.open_finger(); self.set_wait_timer(8.0)
        elif self.sequence_step == 5: self.get_logger().info('[STEP 5] 吸引を停止'); self.disable_edf(); self.set_wait_timer(6.0)
        elif self.sequence_step == 6: self.get_logger().info('[STEP 6] コントローラーをリセット'); self.reset_teleop_controller(); self.set_wait_timer(0.5)
        elif self.sequence_step == 7: self.get_logger().info('[STEP 7] 初期位置へ戻します'); self.arm_future = self.arm_send_request_init_async()
        elif self.sequence_step == 8:
            self.get_logger().info('[STEP 8] 手動操作のロックを解除')
            lock_msg = Bool(); lock_msg.data = False
            self.teleop_lock_publisher.publish(lock_msg) # ロック解除を通知
            self.arm_future = self.arm_send_request_unlock_teleop_async()
        elif self.sequence_step == 9:
            self.get_logger().info('======== 収穫シーケンスが完了しました ========')
            self.is_sequence_running = False

    def handle_reset_sequence(self):
        if self.arm_future and self.arm_future.done():
            try: self.arm_future.result()
            except Exception as e: self.get_logger().error(f"リセット中のアームサービス呼び出しエラー: {e}")
            finally: self.arm_future, self.sequence_step = None, self.sequence_step + 1
        if self.wait_start_time and (time.time() - self.wait_start_time) >= self.wait_duration: self.wait_start_time, self.sequence_step = None, self.sequence_step + 1
        if self.arm_future or self.wait_start_time: return

        # ★★★ 変更点 3/3: リセット完了時にもロック解除の信号を送る ★★★
        if self.sequence_step == 100: self.get_logger().info('[RESET 1] エンドエフェクタをOFFにします。'); self.disable_edf(); self.set_wait_timer(1.0)
        elif self.sequence_step == 101: self.get_logger().info('[RESET 2] 顎を開きます。'); self.open_finger(); self.set_wait_timer(5.0)
        elif self.sequence_step == 102: self.get_logger().info('[RESET 3] 手動操作コントローラーをリセットします。'); self.reset_teleop_controller(); self.set_wait_timer(0.5)
        elif self.sequence_step == 103: self.get_logger().info('[RESET 4] アームを初期位置へ戻します。'); self.arm_future = self.arm_send_request_init_async()
        elif self.sequence_step == 104:
            self.get_logger().info('[RESET 5] 手動操作のロックを解除します。')
            lock_msg = Bool(); lock_msg.data = False
            self.teleop_lock_publisher.publish(lock_msg) # ロック解除を通知
            self.arm_future = self.arm_send_request_unlock_teleop_async()
        elif self.sequence_step == 105:
            self.get_logger().info('======== システムのリセットが完了しました ========'); self.is_resetting = False
    
    def start_reset_sequence(self):
        """ ★★★ 失敗時にリセットシーケンスを開始するための関数 ★★★ """
        self.get_logger().info("シーケンス失敗のため、リセット動作に移行します。")
        self.is_sequence_running = False
        self.arm_future = None
        self.wait_start_time = None
        self.is_resetting = True
        self.sequence_step = 100

    def reset_teleop_controller(self):
        """ ★★★ コントローラーリセットの共通処理 ★★★ """
        reset_msg = Bool(); reset_msg.data = True
        self.teleop_reset_publisher.publish(reset_msg)

    def set_wait_timer(self, duration_sec): self.get_logger().info(f'{duration_sec:.1f}秒待機...'); self.wait_start_time, self.wait_duration = time.time(), duration_sec
    def arm_send_request_box_async(self): self.arm_request.task = "move_to_box"; return self.arm_client.call_async(self.arm_request)
    def arm_send_request_init_async(self): self.arm_request.task = "init_arm"; return self.arm_client.call_async(self.arm_request)
    def arm_send_request_lock_teleop_async(self): self.arm_request.task = "lock_teleop"; return self.arm_client.call_async(self.arm_request)
    def arm_send_request_unlock_teleop_async(self): self.arm_request.task = "unlock_teleop"; return self.arm_client.call_async(self.arm_request)
    
    def select_device(self, serial_number):
        for port in serial.tools.list_ports.comports():
            if port.serial_number == serial_number: return port.device
        return None
    @staticmethod
    def load_yaml(file_path):
        with open(file_path, "r") as file: return yaml.safe_load(file)
    def data2pico(self, send_data):
        self.end_effector_ser.write(str.encode(send_data)); self.end_effector_ser.flush(); line = self.end_effector_ser.readline().decode().strip(); return line
    def disable_edf(self): return self.data2pico(f"0,{self.FOTO_VAL},{self.EDF_VAL}\n")
    def enable_edf(self): return self.data2pico(f"1,{self.FOTO_VAL},{self.EDF_VAL}\n")
    def close_finger(self): return self.data2pico(f"2,{self.FOTO_VAL},{self.EDF_VAL}\n")
    def open_finger(self): return self.data2pico(f"3,{self.FOTO_VAL},{self.EDF_VAL}\n")

def main(args=None):
    rclpy.init(args=args)
    node = SuctionControlNode()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally: node.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()