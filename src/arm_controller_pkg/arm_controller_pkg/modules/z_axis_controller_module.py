"""
Z軸制御プログラム
著者：佐藤光
内容
    ・ステッピングモータの電力供給のON/OFF切り替え
    ・初期位置への移動
    ・Z軸の移動(mm単位)
        ・可動範囲: 0mm - 450mm
"""

import serial
import time
import serial.tools.list_ports
import sys
import yaml

class ZAxis():
    def __init__(self, ik_params):
        # 俯瞰カメラの取り付け高さ
        self.BACK_CAM_HEIGHT = ik_params["BACK_CAM_HEIGHT"]
        # デバイスの認識
        serial_number = ik_params['Z_PICO_SERIAL_NUMBER']
        DEVICENAME = self.select_device(serial_number)
        if DEVICENAME is None:
            raise RuntimeError("デバイスが接続されていません。")
        
        BAUDRATE= ik_params['BAUDRATE']
        self.ser = serial.Serial(DEVICENAME,BAUDRATE,timeout=None)
        
        self.power_enable(0)
        time.sleep(1)
        self.power_enable(1)

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

    def select_device(self, serial_number):
        """指定されたシリアル番号に対応するデバイス名を返す"""
        # 接続されているUSBデバイスのリストを取得
        ports = serial.tools.list_ports.comports()
        
        # 特定のシリアル番号を持つデバイスを検索
        for port in ports:
            if port.serial_number == serial_number:
                return port.device  # デバイス名を返す
        
        return None  # デバイスが見つからなかった場合

    def data2pico(self, send_data):
        # Picoへデータを送信
        self.ser.write(str.encode(send_data))
        self.ser.flush()
        try:
            # Picoからデータを受信
            line = self.ser.readline()
            # print(line)
            line_decoded = str(repr(line.decode())[1:-5])
            # print(line_decoded)
            # 配列に変換
            receive_data = line_decoded.split()
            # print("receive_data:", receive_data[1])
            recive_mode = int(receive_data[0])
            recive_val = int(receive_data[1])
            receive_line = [recive_mode,recive_val]
        except serial.serialutil.SerialTimeoutException:
            print("time_out")
        return receive_line

    # 初期位置へ移動する関数
    def init_pos(self):
        state = self.power_enable(1)
        send_data = str(2) +','+ str(0) +'\n'
        print('Z-axis :Move to initial position')
        result_data = self.data2pico(send_data)
        # print(result_data)
        return result_data
    
    # ホーム位置へ移動する関数
    def home_pos(self, tom_pos_from_z):
        self.move2target(tom_pos_from_z)
    
    # モータへの電力供給をON/OFFする関数
    def power_enable(self,state):
        send_data = str(state) +','+ str(0) +'\n'
        result_data = self.data2pico(send_data)
        return result_data

    # 0-450mmを動作させる関数
    def move2target(self,target_z):
        if target_z < 0 or target_z > 450:
            print("エラー: 目標位置は0から450の範囲内で指定してください。")
            return None
        
        state = self.power_enable(1)
        send_data = str(3) +','+ str(target_z) +'\n'
        result_data =  self.data2pico(send_data)
        return result_data

def main():
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
        
    yaml_path='/home/ylab/hibikino_toms_ws/module/set_params.yaml'
    params = load_yaml(yaml_path)
    z_params = params["ZAxis_params"]
    z_axis = ZAxis(z_params)
    # モータへ電力供給
    state = z_axis.power_enable(1) # 0:OFF,1:ON
    # 初期位置に移動
    pre_pos = z_axis.init_pos()
    print(f"現在の位置は{pre_pos[1]}mmです.")
    while True:
        print("modeを入力してください")
        z = input("初期位置へ移動：1、目標位置へ移動させる：2")
        if (z == "1"):
            pre_pos = z_axis.init_pos()
            print(f"現在の位置は{pre_pos[1]}mmです.")
        elif (z == "2"):
            # 移動量を入力
            print("目標位置(mm)を0から450で入力してください．")
            goal_pos = int(input("目標位置(mm) = "))
            pre_pos = z_axis.move2target(goal_pos)
            # pre_pos = z_axis.home_pos(goal_pos)
            print(f"現在の位置は{pre_pos[1]}mmです.")
        else:
            print("1か2を入力してください")


if __name__ == '__main__':
    main()