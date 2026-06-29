#
# @file suction_control_node.py
# @brief 遠隔操作用のエンドエフェクタ制御ノード
#
# @details
# /suction_commandトピックからコマンドを受け取り、吸引・把持機構を制御します。
# 元のsuction_module_service_node.pyをトピックベースに改造したものです。
#
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import serial
import serial.tools.list_ports
import time
import yaml

class SuctionControlNode(Node):
    """
    @class SuctionControlNode
    @brief コマンドに基づき吸引機構を制御するクラス
    """
    def __init__(self):
        """
        @brief コンストラクタ。パラメータ読み込み、シリアル通信の確立、Subscriberの作成を行う。
        """
        super().__init__('suction_control_node')
        
        # YAMLファイルの読み込み
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        params = self.load_yaml(yaml_path)
        EE_params = params["EE_params"]
        
        # デバイスの認識とシリアル通信の確立
        serial_number = EE_params["EE_PICO_SERIAL_NUMBER"]
        DEVICENAME = self.select_device(serial_number)
        if DEVICENAME is None:
            self.get_logger().error("EE用のマイコンが接続されていません。")
            raise RuntimeError("EE用のマイコンが接続されていません。")
        BAUDRATE = EE_params["BAUDRATE"]
        self.end_effector_ser = serial.Serial(DEVICENAME, BAUDRATE, timeout=1.0)
        
        self.FOTO_VAL = EE_params["FOTO_VAL"]
        self.EDF_VAL = EE_params["EDF_VAL"]
        
        # コマンドを受け取るSubscriber
        self.cmd_subscriber = self.create_subscription(String, 'suction_command', self.command_callback, 10)
        
        self.get_logger().info('Suction Control Node has been started.')
        self.disable_edf() # 初期状態としてファンを停止

    def command_callback(self, msg):
        """
        @brief /suction_command受信時のコールバック関数
        @param[in] msg std_msgs/msg/String型のメッセージ
        @details
        受信したコマンドに応じて、吸引開始・停止の処理を呼び出す。
        """
        command = msg.data
        if command == 'START_SUCTION':
            self.get_logger().info('吸引動作を開始します。')
            self.enable_edf()
            time.sleep(1.0) # ファンが安定するまで待機
            self.close_finger()
        elif command == 'STOP_SUCTION':
            self.get_logger().info('吸引動作を停止します。')
            self.disable_edf()
            self.open_finger()
        else:
            self.get_logger().warn(f'未定義のコマンドです: {command}')
    
    # --- 以下、suction_module_service_node.pyから流用したメソッド群 ---
    
    def select_device(self, serial_number):
        """指定されたシリアル番号に対応するデバイス名を返す"""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.serial_number == serial_number:
                return port.device
        return None

    @staticmethod
    def load_yaml(file_path):
        """YAMLファイルを読み込むヘルパー関数"""
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        except (FileNotFoundError, yaml.YAMLError) as e:
            raise e

    def data2pico(self, send_data):
        """Picoへデータをシリアル送信し、応答を受信する"""
        self.get_logger().info(f"Picoへ送信 -> {send_data.strip()}")
        self.end_effector_ser.write(str.encode(send_data))
        self.end_effector_ser.flush()
        line = self.end_effector_ser.readline().decode().strip()
        if line:
            self.get_logger().info(f"Picoから受信 <- {line}")
            return line
        return None

    def disable_edf(self):
        send_data = str(0) + ',' + str(self.FOTO_VAL) + ',' + str(self.EDF_VAL) + '\n'
        return self.data2pico(send_data)
    
    def enable_edf(self):
        send_data = str(1) + ',' + str(self.FOTO_VAL) + ',' + str(self.EDF_VAL) + '\n'
        return self.data2pico(send_data)

    def close_finger(self):
        send_data = str(2) + ',' + str(self.FOTO_VAL) + ',' + str(self.EDF_VAL) + '\n'
        return self.data2pico(send_data)
    
    def open_finger(self):
        send_data = str(3) + ',' + str(self.FOTO_VAL) + ',' + str(self.EDF_VAL) + '\n'
        return self.data2pico(send_data)

def main(args=None):
    rclpy.init(args=args)
    node = SuctionControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        node.get_logger().error(f"エラーが発生しました: {e}")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()