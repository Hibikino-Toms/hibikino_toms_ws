#
# @file suction_module_service_node.py
# @brief エンドエフェクタ（吸引・把持機構）制御用ROS2サービスノード
#
# @details
# 本プログラムは、ロボットアーム先端のエンドエフェクタを制御するためのROS2サービスサーバーです。
# "SuctionCommand"というサービスを通じて、外部ノードからのコマンド（ファンのON/OFF、顎の開閉）を受け付けます。
# 受け取ったコマンドに基づき、シリアル通信を介して接続されたRaspberry Pi Picoを制御し、
# 物理的なハードウェア（EDFファン、サーボモーター）を操作します。
#

import rclpy
from rclpy.node import Node
from toms_msg.srv import SuctionCommand

import serial
import serial.tools.list_ports
import time
from playsound import playsound
import yaml

class SuctionModuleServiceNode(Node):
    """
    @class SuctionModuleServiceNode
    @brief 吸引モジュール制御ノードのメインクラス
    """
    def __init__(self):
        """
        @brief コンストラクタ。ノードの初期化、パラメータ読み込み、シリアル通信設定、ROS2サービスの作成を行う。
        @param[in] self インスタンス自身
        @param[out] なし
        @details
        - 'suction_module_service_node'という名前のノードを作成します。
        - YAMLファイルからパラメータ（音声の有効/無効、エンドエフェクタのシリアル番号など）を読み込みます。
        - 指定されたシリアル番号を持つデバイス（Raspberry Pi Pico）を検索し、シリアル通信を確立します。
        - 'command'という名前でSuctionCommandのサービスサーバーを起動し、コールバック関数を登録します。
        """
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
        """
        @brief 指定されたシリアル番号に一致するシリアルポートのデバイス名を検索する。
        @param[in] serial_number 検索対象のデバイスのシリアル番号
        @param[out] str or None 見つかったデバイス名(e.g., '/dev/ttyACM0')、見つからない場合はNone
        @details
        PCに接続されている全てのシリアルポートをスキャンし、引数で与えられたシリアル番号を持つポートを探します。
        """
        # 接続されているUSBデバイスのリストを取得
        ports = serial.tools.list_ports.comports()

        # 特定のシリアル番号を持つデバイスを検索
        for port in ports:
            if port.serial_number == serial_number:
                return port.device  # デバイス名を返す
        
        return None  # デバイスが見つからなかった場合
    
    @staticmethod
    def load_yaml(file_path):
        """
        @brief YAMLファイルを読み込む静的ヘルパー関数。
        @param[in] file_path 読み込むYAMLファイルのパス
        @param[out] dict YAMLファイルの内容を格納した辞書
        @details
        指定されたパスのYAMLファイルを安全に読み込み、Pythonの辞書オブジェクトとして返します。
        """
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"YAMLファイルの解析エラー: {e}")

    def data2pico(self, send_data):
        """
        @brief Raspberry Pi Picoへデータをシリアル送信し、応答を受信する。
        @param[in] send_data Picoへ送信するデータ文字列
        @param[out] str Picoから受信した応答データの先頭部分（モード）
        @details
        データをPicoに送信後、Picoからの応答を1行受信します。
        受信したデータは整形され、応答コマンドの種別を表す先頭部分が返されます。
        """
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
        """
        @brief EDF（ファン）を停止させるコマンドをPicoに送信する。
        @param[in] self インスタンス自身
        @param[out] str Picoからの応答データ
        """
        send_data = str(0) +','+ str(self.FOTO_VAL) +','+ str(self.EDF_VAL) +'\n'
        result_data = self.data2pico(send_data)
        self.get_logger().info(result_data)
        return result_data
    
    # EDF起動
    def enable_edf(self):
        """
        @brief EDF（ファン）を起動させるコマンドをPicoに送信する。
        @param[in] self インスタンス自身
        @param[out] str Picoからの応答データ
        """
        send_data = str(1) +','+ str(self.FOTO_VAL) +','+ str(self.EDF_VAL) +'\n'
        result_data = self.data2pico(send_data)
        return result_data

    # 下顎閉じる
    def close_finger(self):
        """
        @brief 下顎（フィンガー）を閉じるコマンドをPicoに送信する。
        @param[in] self インスタンス自身
        @param[out] str Picoからの応答データ
        """
        send_data = str(2) +','+ str(self.FOTO_VAL) +','+ str(self.EDF_VAL) +'\n'
        result_data =  self.data2pico(send_data)
        return result_data
    
    # 下顎開く＋EDF起動
    def open_finger(self):
        """
        @brief 下顎（フィンガー）を開くコマンドをPicoに送信する。
        @param[in] self インスタンス自身
        @param[out] str Picoからの応答データ
        """
        send_data = str(3) +','+ str(self.FOTO_VAL) +','+ str(self.EDF_VAL) +'\n'
        result_data =  self.data2pico(send_data)
        return result_data

    def callback(self, request, response):
        """
        @brief SuctionCommandサービスのコールバック関数。リクエストに応じて各機能を実行する。
        @param[in] request クライアントからのリクエストデータ (SuctionCommand.Request)
        @param[in] response サーバーからクライアントへのレスポンスデータ (SuctionCommand.Response)
        @param[out] response 処理結果を格納したレスポンスデータ
        @details
        リクエストコマンド('0'～'3')に応じて、対応するメソッド（disable_edf, enable_edfなど）を呼び出します。
        処理結果はPicoからの応答となり、response.answerに格納されてクライアントに返されます。
        不正なコマンドの場合は'9'を返します。
        """
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
    """
    @brief メイン関数。ROS2ノードの初期化と実行を行う。
    @param なし
    @param なし
    @details
    1. rclpyを初期化します。
    2. SuctionModuleServiceNodeクラスのインスタンスを生成してノードを作成します。
    3. rclpy.spin()でノードを起動し、サービスリクエストを待ち受けます。
    4. プログラムが終了する際に、クリーンアップ処理を行い、ノードを破棄します。
    """
    rclpy.init()
    node = SuctionModuleServiceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print("\nCtrl+C has been typed")
    finally:
        node.destroy_node()


if __name__ == "__main__":
    """
    @brief スクリプトのエントリーポイント。
    @details
    このスクリプトが直接実行された場合にmain()関数を呼び出します。
    """
    main()
