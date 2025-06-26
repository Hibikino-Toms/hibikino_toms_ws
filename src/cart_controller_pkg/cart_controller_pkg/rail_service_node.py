import rclpy
from rclpy.node import Node

import sys
import yaml
import serial
import serial.tools.list_ports

from std_msgs.msg import Int32  # 累積エンコーダカウントのパブリッシュに使用
from toms_msg.srv import RailService  # サービス定義ファイルのインポート

class RailServiceNode(Node):
    def __init__(self):
        super().__init__('rail_service_node')
        
        # サービスの設定
        self.srv = self.create_service(RailService, 'rail_control', self.control_callback)
        
        # YAMLファイルの読み込み
        yaml_path = ('/home/ylab/hibikino_toms_ws/module/set_params.yaml')
        params = self.load_yaml(yaml_path)
        rail_params = params["rail_params"]  # 必須キー: 存在しない場合 KeyError が発生

        # デバイスの認識
        serial_number = rail_params['RAIL_PICO_SERIAL_NUMBER']
        DEVICENAME = self.select_device(serial_number)
        if DEVICENAME is None:
            raise RuntimeError("レール用のマイコンが接続されていません。")
        BAUDRATE = rail_params["BAUDRATE"]
        
        # シリアルポートの設定
        self.serial_port = serial.Serial(DEVICENAME, BAUDRATE, timeout=1)
        if self.serial_port.is_open:  # シリアルポートが開いたか確認
            self.get_logger().info(f"シリアルポート {DEVICENAME} が開きました。ボーレート: {BAUDRATE}")
        else:
            self.get_logger().error(f"シリアルポート {DEVICENAME} を開くことができませんでした。")
            
        # パラメータの初期化
        distance = rail_params["DEFAULT_DISTANCE_MOVEMENT"]
        self.DEF_PULSE_MOVEMENT = int((distance * 450)/(50 * 3.14))
        self.DEF_PWM = rail_params["DEFAULT_PWM"]
        self.TOTAL_PULSE = rail_params["TOTAL_PULSE"]

        # パブリッシャー作成
        # self.rail_encoder_publisher = self.create_publisher(Int32, 'rail_pulse', 10)

        # タイマーの作成 (パルスカウントを定期的にパブリッシュ)
        # self.create_timer(0.5, self.timer_callback)
        
    def select_device(self, serial_number):
        """指定されたシリアル番号に対応するデバイス名を返す"""
        # 接続されているUSBデバイスのリストを取得
        ports = serial.tools.list_ports.comports()

        # 特定のシリアル番号を持つデバイスを検索
        for port in ports:
            if port.serial_number == serial_number:
                return port.device  # デバイス名を返す
        
        return None  # デバイスが見つからなかった場合
        
    @staticmethod
    def load_yaml(file_path):
        """YAMLファイルを読み込むヘルパー関数"""
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"YAMLファイルの解析エラー: {e}")
            
    def control_callback(self, request, response):
        """
        サービスリクエストを処理
        """
        # サービスリクエストのコマンドを取得
        command = request.req_dir.lower()
        self.get_logger().info(f"Received command: {command}")

        if command == "f":
            print(type(command))
            # "forward" コマンドの場合、正の移動パルス量を送信
            current_pulse_movement = self.DEF_PULSE_MOVEMENT
            response.res_dir = "f"
        elif command == "b":
            # "back" コマンドの場合、負の移動パルス量を送信
            current_pulse_movement = -self.DEF_PULSE_MOVEMENT
            response.res_dir = "b"
        elif command == "s":
            # "stop" コマンドの場合、止まる
            current_pulse_movement = self.DEF_PULSE_MOVEMENT
            self.DEF_PWM = 0
            response.res_dir = "s"
        else:
            # 無効なコマンドの場合の処理
            self.get_logger().warning(f"Invalid command: {command}")
            response.res_dir = "I"
            return response

        # データをマイコンに送信
        print(current_pulse_movement,self.DEF_PWM)
        data_to_send = f"{current_pulse_movement},{self.DEF_PWM}\n"
        self.serial_port.write(data_to_send.encode('utf-8'))
        self.get_logger().info(f"Sent to microcontroller: {data_to_send.strip()}")  # 送信内容を表示
        
        while 1:
            if self.serial_port.in_waiting > 0:
                pulse_data = self.serial_port.readline().decode('utf-8').strip()
                if pulse_data != "":
                    self.get_logger().info(f"Received from microcontroller: {pulse_data}")  # 受信内容を表示
                    break
                else :
                    continue
            else :
                self.get_logger().info(f"Wait for Receive from microcontroller...")
        pulse_msg = Int32()
        pulse_msg.data = int(pulse_data)
        response.pulse = pulse_msg

        return response
        
    # def timer_callback(self):
    #     """
    #     タイマーコールバック関数
    #     マイコンから受信したエンコーダカウントをパブリッシュする
    #     """
    #     if self.serial_port.in_waiting > 0:
    #         pulse_data = self.serial_port.readline().decode('utf-8').strip()
    #         self.get_logger().info(f"Received from microcontroller: {pulse_data}")  # 受信内容を表示
    #         try:
    #             # マイコンから受信したエンコーダカウントをパブリッシュ
    #             # pulse_data = 300
    #             self.TOTAL_PULSE = int(pulse_data)
    #             msg = Int32()
    #             msg.data = self.TOTAL_PULSE
    #             self.rail_encoder_publisher.publish(msg)
    #             self.get_logger().info(f"Published pulse count: {self.TOTAL_PULSE}")
    #         except ValueError:
    #             self.get_logger().error("Failed to decode pulse data")
        
def main(args=None):
    rclpy.init(args=args)
    node = RailServiceNode()
    
    try:
        rclpy.spin(node)  # ノードを実行
    except KeyboardInterrupt:
        print("Ctrl+C has been entered")
        print("End of program")
    finally:
        if node.serial_port.is_open:
            node.serial_port.close()  # シリアルポートを閉じる
            node.get_logger().info("シリアルポートを閉じました。")
    rclpy.shutdown()  # ノード終了時にROS2をシャットダウン

if __name__ == '__main__':
    main()

