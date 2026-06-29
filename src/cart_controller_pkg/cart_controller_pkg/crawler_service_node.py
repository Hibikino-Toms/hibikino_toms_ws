#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@author Renshi Kato
-----------------------------------------
crawler service node
カートの指令値を受取り、指定距離カートを移動させる
"""
import rclpy
from rclpy.node import Node

import sys
import yaml
import serial
import serial.tools.list_ports

from std_msgs.msg import Int32  # 累積エンコーダカウントのパブリッシュに使用
sys.path.append("/home/ylab/hibikino_toms_ws/src")
from toms_msg.srv import CrawlerService  # サービス定義ファイルのインポート

class CrawlerServiceNode(Node):
    """
    ROS2ノード: CrawlerServiceNode
    サービス通信で移動指令を受け取り、カートを指定距離移動させる
    """
    def __init__(self):
        super().__init__('crawler_service_node')
        # サービスサーバーの作成
        self.srv = self.create_service(CrawlerService, 'crawler_control', self.control_callback)
        
        # YAMLファイルの読み込み
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        params = self.load_yaml(yaml_path)
        crawler_params = params["crawler_params"]  # 必須キー: 存在しない場合 KeyError が発生

        # デバイスの認識
        serial_number = crawler_params['CRAWLER_PICO_SERIAL_NUMBER']
        DEVICENAME = self.select_device(serial_number)
        if DEVICENAME is None:
            raise RuntimeError("クローラ用のマイコンが接続されていません。")
        BAUDRATE = crawler_params["BAUDRATE"]
        self.serial_port = serial.Serial(DEVICENAME,BAUDRATE,timeout=1)
        
        # パラメータの初期化
        distance = crawler_params["DEFAULT_DISTANCE_MOVEMENT"]
        self.DEF_PULSE_MOVEMENT = (distance * 10000)/ 610 # 移動指令で使用するパルス量
        self.DEF_PWM = crawler_params["DEFAULT_PWM"]  # PWMの規定値
        self.TOTAL_PULSE = crawler_params["TOTAL_PULSE"]  # 累積エンコーダカウントを0に初期化

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
        サービスコールバック関数
        サービスリクエストのコマンドを処理し、カートの移動を制御する

        Args:
            request: サービスリクエスト (command: str)
            response: サービスレスポンス (res_dir: str)

        Returns:
            response: 処理結果としての移動方向をレスポンス
        """
        # サービスリクエストのコマンドを取得
        command = request.req_dir.lower()
        self.get_logger().info(f"Received command: {command}")

        if command == "f":
            # "forward" コマンドの場合、正の移動パルス量を送信
            current_pulse_movement = self.DEF_PULSE_MOVEMENT
            response.res_dir = "f"
        elif command == "b":
            # "back" コマンドの場合、負の移動パルス量を送信
            current_pulse_movement = -self.DEF_PULSE_MOVEMENT
            response.res_dir = "b"
        else:
            # 無効なコマンドの場合の処理
            self.get_logger().warning(f"Invalid command: {command}")
            response.res_dir = "I"
            return response

        # データをマイコンに送信
        self.serial_port.write(f"{current_pulse_movement},{self.DEF_PWM}\n".encode('utf-8'))
        self.get_logger().info(f"Sent to microcontroller: Pulses={current_pulse_movement}, PWM={self.DEF_PWM}")
        # マイコンからデータ受信
        while 1:
            if self.serial_port.in_waiting > 0:
                pulse_data = self.serial_port.readline().strip().decode('utf-8')
                self.get_logger().info(f"Receive from microcontroller: pulse_data={pulse_data}")
                break
            else:
                self.get_logger().info(f"Wait for Receive from microcontroller...")
        pulse_data = 300
        pulse_msg = Int32()
        pulse_msg.data = int(pulse_data)
        response.pulse = pulse_msg
        
        return response
    
def main(args=None):
    """
    メイン関数
    ノードを初期化し、実行を開始する
    """
    rclpy.init(args=args)
    node = CrawlerServiceNode()
    try :
        rclpy.spin(node)  # ノードを実行
    except KeyboardInterrupt :
        print("Ctrl+C has been entered")
        print("End of program")
    finally:
        print("\n")
        if node.serial_port.is_open:
            node.serial_port.close()  # シリアルポートを閉じる
            node.get_logger().info("シリアルポートを閉じました。")
    rclpy.shutdown()  # ノード終了時にROS2をシャットダウン

if __name__ == '__main__':
    main()

