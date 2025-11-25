# coding: utf-8

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
import time
import serial
import serial.tools.list_ports
import yaml
import math
# --- 追加ライブラリ ---
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
# --------------------

class CrawlerControllerSerial(Node):
    """
    /crawler_pwms トピックを購読し、PWM値をマイコンに送信。
    同時にマイコンからパルス値を受信し、/odomトピックをパブリッシュするノード。
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
        super().__init__('crawler_controller_serial')
        self.get_logger().info('クローラー制御＆オドメトリノードを起動します。')
        
        self.serial_port = None
        self.initialized_successfully = False 
        
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        self.get_logger().info(f'YAMLパスをコード内で設定: {yaml_path}')
        
        try:
            params = self.load_yaml(yaml_path)
            crawler_params = params["crawler_params"]
            self.serial_number = crawler_params['CRAWLER_PICO_SERIAL_NUMBER']
            self.baudrate = crawler_params['BAUDRATE']
            # --- YAMLパラメータの追加 ---
            self.pulses_per_meter = float(crawler_params.get('PULSES_PER_METER', 17400.0))
            self.tread = float(crawler_params.get('TREAD', 0.40)) # クローラーの幅 (m)
            # --------------------------

            self.get_logger().info(f" -> pulse/m: {self.pulses_per_meter}")
            self.get_logger().info(f" -> tread: {self.tread} m")

        except (FileNotFoundError, KeyError, ValueError) as e:
            self.get_logger().fatal(f"設定ファイルの読み込みに失敗しました: {e}")
            self.get_logger().fatal("ノードの初期化を中断します。")
            return
        
        self.initialized_successfully = True

        # --- オドメトリ状態変数の初期化 ---
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.last_time = self.get_clock().now()
        
        # --- パブリッシャーとブロードキャスタの作成 ---
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        # ------------------------------------------

        self.setup_serial()

        # Subscriberの作成: /crawler_pwms を購読 (既存)
        self.subscription = self.create_subscription(
            Float32MultiArray,
            '/crawler_pwms',
            self.pwm_callback, 
            10)
            
        # 安全停止のためのタイマー (既存)
        self.last_received_time = self.get_clock().now()
        self.timeout_timer = self.create_timer(0.1, self.timeout_callback)

        # --- シリアル受信ポーリング用のタイマー (追加) ---
        # マイコンからのパルスデータを受信するためのタイマー
        self.read_serial_timer = self.create_timer(0.01, self.read_serial_data) 
        # ------------------------------------------------

    # (select_device と setup_serial は省略 - 既存コードから変更なし)

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
        if not self.initialized_successfully:
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
            # タイムアウトを設定
            self.serial_port = serial.Serial(device_name, self.baudrate, timeout=0.01) 
            self.get_logger().info(f'{device_name} とのシリアル通信を開始しました。')
        except serial.SerialException as e:
            self.get_logger().fatal(f'シリアルポートを開けませんでした: {e}')
            self.initialized_successfully = False
    
    def pwm_callback(self, msg: Float32MultiArray):
        """/crawler_pwms トピックのコールバック関数。受信したPWM値をマイコンに送信する。"""
        if not self.initialized_successfully or not self.serial_port or not self.serial_port.is_open:
            return

        self.last_received_time = self.get_clock().now()
        
        pwm_left = msg.data[0]
        pwm_right = msg.data[1]

        # マイコンにPWM値を送信 (モーター制御)
        self.send_command_to_mcu(pwm_left, pwm_right)
        
    def send_command_to_mcu(self, pwm_left, pwm_right):
        """計算されたPWM値に基づいてマイコンにコマンドを送信する (既存)"""
        if self.serial_port and self.serial_port.is_open:
            command = f"{int(pwm_left)},{int(pwm_right)}\n"
            try:
                self.serial_port.write(command.encode('utf-8'))
            except serial.SerialException as e:
                self.get_logger().error(f"シリアル書き込みエラー: {e}")

    # --- パルスデータ受信と処理のロジック (新規) ---
    def read_serial_data(self):
        """シリアルポートからパルスデータを受信し、オドメトリを更新する"""
        if not self.initialized_successfully or not self.serial_port or not self.serial_port.is_open:
            return
        
        try:
            # シリアルバッファに残っているデータを一行だけ読み込む
            if self.serial_port.in_waiting > 0:
                line = self.serial_port.readline().decode('utf-8').strip()
                if line:
                    self.process_pulse_data(line)
                    
        except serial.SerialException as e:
            self.get_logger().error(f"シリアル読み込みエラー: {e}")
            self.stop_motors()
            
    def process_pulse_data(self, data_str):
        """受信した文字列をパルス値として解析し、オドメトリを計算する"""
        try:
            # マイコンが "pulse_L,pulse_R" の形式で送信していると仮定
            pulse_data = [float(p.strip()) for p in data_str.split(',')]
            pulse_left = pulse_data[0]
            pulse_right = pulse_data[1]
            
            self.calculate_and_publish_odom(pulse_left, pulse_right)

        except ValueError:
            # self.get_logger().warn(f"不正なパルスデータを受信しました: {data_str}") # デバッグ用
            pass
        except IndexError:
            # self.get_logger().warn(f"パルスデータが不完全です: {data_str}") # デバッグ用
            pass


    def calculate_and_publish_odom(self, pulse_left, pulse_right):
        """パルス値からオドメトリを計算し、/odomとしてパブリッシュする"""
        current_time = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9
        
        if dt == 0:
            return
            
        # 1. 左右の移動距離 (m)
        distance_left = pulse_left / self.pulses_per_meter
        distance_right = pulse_right / self.pulses_per_meter

        # 2. ロボット中心の移動距離と回転量 (差動駆動モデル)
        distance_center = (distance_left + distance_right) / 2.0
        delta_theta = (distance_right - distance_left) / self.tread
        
        # 3. 速度 (m/s と rad/s)
        vx = distance_center / dt
        vth = delta_theta / dt
        
        # 4. 絶対座標の更新 (オイラー積分)
        # ロボットのローカル座標系での移動を、現在の向き (theta) に基づきグローバル座標系に変換
        if distance_center != 0:
            # 平均角度を使用して円弧移動を近似 (精度向上)
            d_x = distance_center * math.cos(self.theta + delta_theta / 2.0)
            d_y = distance_center * math.sin(self.theta + delta_theta / 2.0)
            
            self.x += d_x
            self.y += d_y
        
        self.theta += delta_theta
        
        # 5. TFブロードキャスト (odom -> base_footprint)
        # オドメトリは base_footprint を使うのが慣習
        q = self.euler_to_quaternion(0.0, 0.0, self.theta)
        
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_footprint' # Launchファイルで設定したフレーム名に合わせる
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation.x = q[0]
        t.transform.rotation.y = q[1]
        t.transform.rotation.z = q[2]
        t.transform.rotation.w = q[3]
        self.tf_broadcaster.sendTransform(t)

        # 6. Odometryメッセージのパブリッシュ
        odom = Odometry()
        odom.header.stamp = current_time.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_footprint'
        
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.x = q[0]
        odom.pose.pose.orientation.y = q[1]
        odom.pose.pose.orientation.z = q[2]
        odom.pose.pose.orientation.w = q[3]
        
        # 速度情報
        odom.twist.twist.linear.x = vx
        odom.twist.twist.angular.z = vth
        
        # 共分散 (ここでは簡単のため固定値を設定。実運用では調整が必要)
        odom.pose.covariance[0] = 0.001
        odom.pose.covariance[7] = 0.001
        odom.pose.covariance[35] = 0.005
        
        self.odom_pub.publish(odom)
        
        self.last_time = current_time

    def euler_to_quaternion(self, roll, pitch, yaw):
        """オイラー角 (ラジアン) をクォータニオンに変換する"""
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)

        q = [0] * 4
        q[0] = sr * cp * cy - cr * sp * sy  # x
        q[1] = cr * sp * cy + sr * cp * sy  # y
        q[2] = cr * cp * sy - sr * sp * cy  # z
        q[3] = cr * cp * cy + sr * sp * sy  # w
        return q

    # (stop_motors, timeout_callback, destroy_node, main は省略 - 必要な変更はなし)

    def stop_motors(self):
        """全てのモーターを停止するコマンドを送信する"""
        if self.initialized_successfully and self.serial_port and self.serial_port.is_open:
            self.send_command_to_mcu(0.0, 0.0)

    def timeout_callback(self):
        """速度指令のタイムアウトを監視するコールバック"""
        if not self.initialized_successfully:
            return
            
        duration = (self.get_clock().now() - self.last_received_time).nanoseconds / 1e9
        if duration > 0.5: # 0.5秒間コマンドが来なければ停止
            self.stop_motors()

    def destroy_node(self):
        """ノード終了時のクリーンアップ処理"""
        self.get_logger().info('クリーンアップ処理を実行します。')
        if hasattr(self, 'initialized_successfully') and self.initialized_successfully:
            self.stop_motors()
            time.sleep(0.1)
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                self.get_logger().info("シリアルポートを閉じました。")
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CrawlerControllerSerial()
    if hasattr(node, 'initialized_successfully') and node.initialized_successfully:
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.destroy_node()
    else:
        node.get_logger().fatal("ノードの初期化に失敗したため、実行を中断します。")
        if hasattr(node, 'serial_port') and node.serial_port and node.serial_port.is_open:
            node.serial_port.close()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
