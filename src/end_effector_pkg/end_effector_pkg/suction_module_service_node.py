import rclpy
from rclpy.node import Node
from toms_msg.srv import SuctionCommand

import serial
import serial.tools.list_ports
import time
from playsound import playsound
import yaml

class SuctionModuleServiceNode(Node):
    def __init__(self):
        super().__init__('suction_module_service_node')
        
        
        # YAMLファイルの読み込み
        yaml_path='/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        params = self.load_yaml(yaml_path)
        self.VOICE = params["ZUNDA_VOICE"]
        EE_params = params["EE_params"]
        
        # デバイスの認識とシリアル通信
        serial_number = EE_params["EE_PICO_SERIAL_NUMBER"]
        DEVICENAME = self.select_device(serial_number)
        if DEVICENAME is None:
            raise RuntimeError("EE用のマイコンが接続されていません。")
        BAUDRATE = EE_params["BAUDRATE"]
        self.end_effector_ser = serial.Serial(DEVICENAME,BAUDRATE,timeout=None)
        
        # EEのパラメータの設定
        self.FOTO_VAL = EE_params["FOTO_VAL"]
        self.EDF_VAL = EE_params["EDF_VAL"]
        time.sleep(1)
        # playsound("/home/ylab/hibikino_toms_ws/src/end_effector_pkg/end_effector_pkg/sound/サクションモジュールサービスノードを起動したのだ.wav")
        self.suction_service = self.create_service(SuctionCommand, 'command', self.callback)
        self.get_logger().info('suction_module_service_node：active')


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

    def data2pico(self, send_data):
        # Picoへデータを送信
        self.get_logger().info(f"Picoへデータを送信 ▶▶▶ {str.encode(send_data)}")
        self.end_effector_ser.write(str.encode(send_data))
        self.end_effector_ser.flush()
        try:
            # Picoからデータを受信
            line = self.end_effector_ser.readline()
            line_decoded = str(repr(line.decode())[1:-5])
            # 配列に変換
            print(f"PICO_data: {line_decoded}")
            receive_data = line_decoded.split()
            print(f"receive_data: {receive_data}")
            receive_mode = str(receive_data[0])
            self.get_logger().info(f"Picoからデータを受信 ◁◁◁ {receive_mode}")
            receive_line = [receive_mode]
        except serial.serialutil.SerialTimeoutException:
            print("time_out")
        return receive_mode

    # EDF停止
    def disable_edf(self):
        send_data = str(0) +','+ str(self.FOTO_VAL) +','+ str(self.EDF_VAL) +'\n'
        result_data = self.data2pico(send_data)
        self.get_logger().info(result_data)
        return result_data
    
    # EDF起動
    def enable_edf(self):
        send_data = str(1) +','+ str(self.FOTO_VAL) +','+ str(self.EDF_VAL) +'\n'
        result_data = self.data2pico(send_data)
        return result_data

    # 下顎閉じる
    def close_finger(self):
        send_data = str(2) +','+ str(self.FOTO_VAL) +','+ str(self.EDF_VAL) +'\n'
        result_data =  self.data2pico(send_data)
        return result_data
    
    # 下顎開く＋EDF起動
    def open_finger(self):
        send_data = str(3) +','+ str(self.FOTO_VAL) +','+ str(self.EDF_VAL) +'\n'
        result_data =  self.data2pico(send_data)
        return result_data

    def callback(self, request, response):
        suction_request = request.command
        if (suction_request == '0'):
            self.get_logger().info('ファンを停止するのだ')
            if self.VOICE:
                # playsound("/home/ylab/toms_ws/src/end_effector_pkg/end_effector_pkg/sound/ファンを停止するのだ.wav")
                pass
            response.answer = self.disable_edf()
        elif (suction_request == '1'):
            self.get_logger().info('ファンを起動するのだ')
            if self.VOICE:
                # playsound("/home/ylab/toms_ws/src/end_effector_pkg/end_effector_pkg/sound/ファンを起動するのだ.wav")
                pass
            response.answer = self.enable_edf()
        elif (suction_request == '2'):
            self.get_logger().info('顎を閉じるのだ')
            if self.VOICE:
                # playsound("/home/ylab/toms_ws/src/end_effector_pkg/end_effector_pkg/sound/顎を閉じるのだ.wav")
                pass
            response.answer = self.close_finger()
        elif (suction_request == '3'):
            self.get_logger().info('顎を開くのだ')
            if self.VOICE:
                # playsound("/home/ylab/toms_ws/src/end_effector_pkg/end_effector_pkg/sound/顎を開くのだ.wav")
                pass
            response.answer = self.open_finger()
        else:
            self.get_logger().info('コマンドが違うのだ')
            if self.VOICE:
                # playsound("/home/ylab/toms_ws/src/end_effector_pkg/end_effector_pkg/sound/コマンドが違うのだ.wav")
                pass
            response.answer = '9'
        time.sleep(3)
        return response


def main():
    rclpy.init()
    node = SuctionModuleServiceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print("\nCtrl+C has been typed")
    finally:
        node.destroy_node()


if __name__ == "__main__":
    main()
