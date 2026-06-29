import rclpy
from rclpy.node import Node
import sys
import yaml
import serial
import serial.tools.list_ports
import time  # 待機用にtimeをインポート
from std_msgs.msg import Int32
from toms_msg.srv import RailService

class RailServiceNode(Node):
    def __init__(self):
        super().__init__('rail_service_node')
        self.get_logger().info('rail_teleopを起動します（ドライバモード）。')
        
        # サービスの設定
        self.srv = self.create_service(RailService, 'rail_control', self.control_callback)
        
        # YAMLファイルの読み込み
        yaml_path = ('/home/ylab/hibikino_toms_ws/module/set_params.yaml')
        params = self.load_yaml(yaml_path)
        rail_params = params["rail_params"]

        # デバイスの認識
        serial_number = rail_params['RAIL_PICO_SERIAL_NUMBER']
        DEVICENAME = self.select_device(serial_number)
        if DEVICENAME is None:
            raise RuntimeError("レール用のマイコンが接続されていません。")
        BAUDRATE = rail_params["BAUDRATE"]
        
        # シリアルポートの設定
        # timeoutを0.1秒に短縮し、何度も読みに行く方式に変更
        self.serial_port = serial.Serial(DEVICENAME, BAUDRATE, timeout=0.1)
        if self.serial_port.is_open:
            self.get_logger().info(f"シリアルポート {DEVICENAME} が開きました。")
        
        # 1回の移動量
        distance = rail_params["DEFAULT_DISTANCE_MOVEMENT"]
        self.DEF_PULSE_MOVEMENT = int((distance * 450)/(50 * 3.14))
        self.DEF_PWM = rail_params["DEFAULT_PWM"]

    def select_device(self, serial_number):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.serial_number == serial_number:
                return port.device
        return None
        
    @staticmethod
    def load_yaml(file_path):
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        except Exception as e:
            raise ValueError(f"YAML読み込みエラー: {e}")

    def control_callback(self, request, response):
        """
        サービスリクエストを処理
        """
        command = request.req_dir.lower()
        self.get_logger().info(f"Received command: {command}")
        
        current_pulse_movement = 0
        
        # コマンド判定
        if command == "f":
            current_pulse_movement = self.DEF_PULSE_MOVEMENT
            response.res_dir = "f"
        elif command == "b":
            current_pulse_movement = -self.DEF_PULSE_MOVEMENT
            response.res_dir = "b"
        elif command == "s":
            current_pulse_movement = 0
            self.DEF_PWM = 0
            response.res_dir = "s"
        else:
            self.get_logger().warning(f"Invalid command: {command}")
            response.res_dir = "I"
            response.pulse = Int32(data=0)
            return response

        # マイコン送信と受信
        pulse_data_str = "0"
        try:
            # 入力バッファをクリア（古いデータを捨てる）
            self.serial_port.reset_input_buffer()
            
            # データ送信
            data_to_send = f"{current_pulse_movement},{self.DEF_PWM}\n"
            self.serial_port.write(data_to_send.encode('utf-8'))
            
            # 受信待機ループ (最大2秒待つ)
            start_time = time.time()
            received_valid_data = False
            
            while (time.time() - start_time) < 2.0:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline()
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line:
                        pulse_data_str = decoded_line
                        self.get_logger().info(f"Microcontroller response: {pulse_data_str}")
                        received_valid_data = True
                        break
                time.sleep(0.01) # CPU負荷を下げるための微小ウェイト

            if not received_valid_data:
                self.get_logger().warning("Microcontroller response Timed Out (Empty)")

        except Exception as e:
            self.get_logger().error(f"Serial communication error: {e}")

        # レスポンス作成 (Int32型に確実に変換)
        pulse_msg = Int32()
        try:
            # 受信データが数値変換可能かチェック
            pulse_val = int(float(pulse_data_str))
            pulse_msg.data = pulse_val
        except ValueError:
            self.get_logger().error(f"Invalid number format: {pulse_data_str}")
            pulse_msg.data = 0
        
        response.pulse = pulse_msg
        self.get_logger().info(f"Sending response back to client: dir={response.res_dir}, pulse={response.pulse.data}")
        return response

def main(args=None):
    rclpy.init(args=args)
    node = RailServiceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if hasattr(node, 'serial_port') and node.serial_port.is_open:
            node.serial_port.close()
        node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()