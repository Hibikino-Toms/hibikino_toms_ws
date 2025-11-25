# coding: utf-8

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray # /crawler_pwms トピックのメッセージ型
import time
import serial
import serial.tools.list_ports
import yaml

class CrawlerControllerSerial(Node):
    """
    /crawler_pwms トピックを購読し、受信した左右のPWM値を
    シリアル通信でRaspberry Pi Pico Wに送信するノード。
    シリアル番号とボーレートはYAMLファイルから読み込む。
    """
    
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

    def __init__(self):
        # ノード名はパッケージ内で一意に、かつ分かりやすいものに設定
        super().__init__('crawler_controller_serial') 
        self.get_logger().info('クローラー制御ノード (シリアル通信) を起動します。')
        
        self.serial_port = None

        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        self.get_logger().info(f'YAMLパスをコード内で設定: {yaml_path}')
        
        # このノードでは、TREADやMAX_LINEAR_SPEEDはPWM値の計算には使用しません。
        # それらは上位の twist_to_crawler_converter_node で計算されます。

        try:
            params = self.load_yaml(yaml_path)
            crawler_params = params["crawler_params"]
            self.serial_number = crawler_params['CRAWLER_PICO_SERIAL_NUMBER']
            self.baudrate = crawler_params['BAUDRATE']

            self.get_logger().info(f"YAMLファイルから設定を読み込みました: {yaml_path}")
            self.get_logger().info(f" -> 使用するシリアル番号: {self.serial_number} (YAMLから)")
            self.get_logger().info(f" -> ボーレート: {self.baudrate} (YAMLから)")

        except (FileNotFoundError, KeyError, ValueError) as e:
            self.get_logger().fatal(f"設定ファイルの読み込みに失敗しました: {e}")
            self.get_logger().fatal("ノードの初期化を中断します。")
            # 初期化失敗時にノードを安全に終了させるためのフラグ
            self.initialized_successfully = False 
            return
        
        self.initialized_successfully = True # 初期化成功フラグ

        # シリアルポートの初期化
        self.setup_serial()

        # Subscriberの作成: Float32MultiArray 型の /crawler_pwms を購読
        self.subscription = self.create_subscription(
            Float32MultiArray,
            '/crawler_pwms',
            self.pwm_callback, 
            10)
            
        # 安全停止のためのタイマー
        # /crawler_pwms が一定時間来なくなった場合に、モーターを停止する
        self.last_received_time = self.get_clock().now()
        self.timeout_timer = self.create_timer(0.1, self.timeout_callback)

    def select_device(self, serial_number):
        """指定されたシリアル番号に対応するデバイス名を返す"""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.serial_number == serial_number:
                self.get_logger().info(f'デバイスが見つかりました: {port.device}')
                return port.device
        self.get_logger().error(f"シリアル番号 '{serial_number}' を持つデバイスが見つかりませんでした。")
        return None

    def setup_serial(self):
        """シリアルポートのセットアップを行う"""
        if not self.initialized_successfully: # 初期化に失敗していれば何もしない
            return

        if not hasattr(self, 'serial_number') or not self.serial_number:
            self.get_logger().error("シリアル番号が設定されていないため、シリアル通信を初期化できません。")
            self.initialized_successfully = False
            return
            
        device_name = self.select_device(self.serial_number)
        if device_name is None:
            self.initialized_successfully = False
            return
        
        try:
            self.serial_port = serial.Serial(device_name, self.baudrate, timeout=1.0)
            self.get_logger().info(f'{device_name} とのシリアル通信を開始しました。')
        except serial.SerialException as e:
            self.get_logger().fatal(f'シリアルポートを開けませんでした: {e}')
            self.initialized_successfully = False

    def pwm_callback(self, msg: Float32MultiArray):
        """/crawler_pwms トピックのコールバック関数。受信したPWM値をマイコンに送信する。"""
        if not self.initialized_successfully or not self.serial_port or not self.serial_port.is_open:
            # ノードが正しく初期化されていないか、シリアルポートが開いていなければ何もしない
            return

        self.last_received_time = self.get_clock().now()
        
        # Float32MultiArrayのdata配列から左右のPWM値を取得
        pwm_left = msg.data[0]
        pwm_right = msg.data[1]

        self.send_command_to_mcu(pwm_left, pwm_right)

    def send_command_to_mcu(self, pwm_left, pwm_right):
        """計算されたPWM値に基づいてマイコンにコマンドを送信する"""
        if self.serial_port and self.serial_port.is_open:
            # マイコンの期待する形式に合わせて、左右のPWM値をカンマ区切りで送信
            # 例: "80,-80\n"
            command = f"{int(pwm_left)},{int(pwm_right)}\n"
            try:
                self.serial_port.write(command.encode('utf-8'))
                # self.get_logger().info(f"Sent: {command.strip()}") # デバッグ用ログ (大量に出るので注意)
            except serial.SerialException as e:
                self.get_logger().error(f"シリアル書き込みエラー: {e}")
            except Exception as e:
                self.get_logger().error(f"コマンド送信中に予期せぬエラー: {e}")
        else:
            self.get_logger().warn('シリアルポートが開いていないため、コマンドを送信できません。')


    def stop_motors(self):
        """全てのモーターを停止するコマンドを送信する"""
        # 初期化成功時のみ実行
        if self.initialized_successfully and self.serial_port and self.serial_port.is_open:
            # self.get_logger().info('モーターを停止します。') # ログが多すぎる場合はコメントアウト
            self.send_command_to_mcu(0.0, 0.0)

    def timeout_callback(self):
        """速度指令のタイムアウトを監視するコールバック"""
        if not self.initialized_successfully: # 初期化に失敗していれば何もしない
            return
            
        duration = (self.get_clock().now() - self.last_received_time).nanoseconds / 1e9
        if duration > 0.5: # 0.5秒間コマンドが来なければ停止
            self.stop_motors()

    def destroy_node(self):
        """ノード終了時のクリーンアップ処理"""
        self.get_logger().info('クリーンアップ処理を実行します。')
        if hasattr(self, 'initialized_successfully') and self.initialized_successfully:
            self.stop_motors()
            time.sleep(0.1) # 停止コマンドが送信されるのを少し待つ
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                self.get_logger().info("シリアルポートを閉じました。")
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CrawlerControllerSerial()
    # node.initialized_successfully フラグを確認
    if hasattr(node, 'initialized_successfully') and node.initialized_successfully:
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.destroy_node()
    else:
        node.get_logger().fatal("ノードの初期化に失敗したため、実行を中断します。")
        # エラー発生時はdestroy_nodeを呼ぶ前にシリアルポートが確実に閉じられているか確認
        if hasattr(node, 'serial_port') and node.serial_port and node.serial_port.is_open:
            node.serial_port.close()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
