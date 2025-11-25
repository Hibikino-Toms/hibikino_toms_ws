# coding: utf-8

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Quaternion
from tf2_ros import TransformBroadcaster
import time
import serial
import serial.tools.list_ports
import yaml
import threading
import math

class CrawlerControllerSerial(Node):
    """
    /crawler_pwms トピックを購読し、PWM値をマイコンへ送信する。
    同時に、マイコンからエンコーダ値を受信し、オドメトリを計算して /odom を発行する。
    """
    
    # 定数: 1mあたりのカウント数 (0-17400 = 1m)
    COUNTS_PER_METER = 17400.0

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
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        self.get_logger().info(f'YAMLパス: {yaml_path}')
        
        # --- パラメータ読み込み ---
        try:
            params = self.load_yaml(yaml_path)
            crawler_params = params["crawler_params"]
            self.serial_number = crawler_params['CRAWLER_PICO_SERIAL_NUMBER']
            self.baudrate = crawler_params['BAUDRATE']
            
            # オドメトリ計算に必要なトレッド幅を追加で読み込み
            # YAMLに "TREAD": 0.4 のように記述されている前提
            self.tread_width = crawler_params.get('TREAD', 0.4) 

            self.get_logger().info(f" -> シリアル番号: {self.serial_number}")
            self.get_logger().info(f" -> ボーレート: {self.baudrate}")
            self.get_logger().info(f" -> トレッド幅: {self.tread_width} m")

        except (FileNotFoundError, KeyError, ValueError) as e:
            self.get_logger().fatal(f"設定ファイルの読み込みに失敗しました: {e}")
            self.initialized_successfully = False 
            return
        
        self.initialized_successfully = True

        # --- オドメトリ用変数の初期化 ---
        self.x = 0.0
        self.y = 0.0
        self.th = 0.0
        self.prev_left_count = None
        self.prev_right_count = None
        self.last_odom_time = self.get_clock().now()

        # --- ROS通信設定 ---
        # 1. Subscriber (PWM送信)
        self.subscription = self.create_subscription(
            Float32MultiArray,
            '/crawler_pwms',
            self.pwm_callback, 
            10)
            
        # 2. Publisher & TF (オドメトリ受信)
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # 3. 安全停止タイマー
        self.last_received_time = self.get_clock().now()
        self.timeout_timer = self.create_timer(0.1, self.timeout_callback)

        # --- シリアルポート接続と受信スレッド開始 ---
        self.setup_serial()
        
        # シリアル接続が成功していたら受信スレッドを開始
        if self.initialized_successfully and self.serial_port and self.serial_port.is_open:
            self.read_thread = threading.Thread(target=self.read_serial_loop)
            self.read_thread.daemon = True
            self.read_thread.start()

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

        device_name = self.select_device(self.serial_number)
        if device_name is None:
            self.initialized_successfully = False
            return
        
        try:
            # timeoutは読み込みスレッドのために少し短めでも良いが、1.0でも動作はする
            self.serial_port = serial.Serial(device_name, self.baudrate, timeout=1.0)
            self.get_logger().info(f'{device_name} とのシリアル通信を開始しました。')
        except serial.SerialException as e:
            self.get_logger().fatal(f'シリアルポートを開けませんでした: {e}')
            self.initialized_successfully = False

    def pwm_callback(self, msg: Float32MultiArray):
        """/crawler_pwms 受信コールバック"""
        if not self.initialized_successfully or not self.serial_port or not self.serial_port.is_open:
            return

        self.last_received_time = self.get_clock().now()
        pwm_left = msg.data[0]
        pwm_right = msg.data[1]
        self.send_command_to_mcu(pwm_left, pwm_right)

    def send_command_to_mcu(self, pwm_left, pwm_right):
        """マイコンへコマンド送信"""
        if self.serial_port and self.serial_port.is_open:
            # フォーマット: "PWM_L,PWM_R\n" (例: "80,-80\n")
            command = f"{int(pwm_left)},{int(pwm_right)}\n"
            try:
                self.serial_port.write(command.encode('utf-8'))
            except Exception as e:
                self.get_logger().error(f"シリアル書き込みエラー: {e}")

    def read_serial_loop(self):
        """
        [別スレッド] マイコンからのデータを常時読み込むループ
        想定受信フォーマット: "Encoder_L,Encoder_R" (例: "17400,-500")
        """
        while rclpy.ok() and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.process_odom_data(line)
            except Exception as e:
                self.get_logger().warn(f"シリアル読み込みエラー: {e}")
                time.sleep(0.1)

    def process_odom_data(self, line):
        """受信データを解析してオドメトリを更新"""
        try:
            parts = line.split(',')
            # カンマ区切りで要素数が2以外なら無視（PWMのエコーバックなどが混ざる可能性を考慮）
            if len(parts) != 2:
                return
            
            # 左, 右 の順で来ると仮定
            current_left_count = float(parts[0])
            current_right_count = float(parts[1])

            # 初回受信時は初期化のみ
            if self.prev_left_count is None:
                self.prev_left_count = current_left_count
                self.prev_right_count = current_right_count
                self.last_odom_time = self.get_clock().now()
                return

            # --- オドメトリ計算 ---
            current_time = self.get_clock().now()
            dt = (current_time - self.last_odom_time).nanoseconds / 1e9

            if dt < 0.0001: return

            delta_l_count = current_left_count - self.prev_left_count
            delta_r_count = current_right_count - self.prev_right_count

            # カウント -> メートル変換
            d_left = delta_l_count / self.COUNTS_PER_METER
            d_right = delta_r_count / self.COUNTS_PER_METER

            d_center = (d_right + d_left) / 2.0
            delta_th = (d_right - d_left) / self.tread_width

            vx = d_center / dt
            vth = delta_th / dt

            if d_center != 0:
                delta_x = d_center * math.cos(self.th + delta_th / 2.0)
                delta_y = d_center * math.sin(self.th + delta_th / 2.0)
                self.x += delta_x
                self.y += delta_y
            
            self.th += delta_th

            # パブリッシュ
            self.publish_odom(current_time, vx, vth)

            # 更新
            self.prev_left_count = current_left_count
            self.prev_right_count = current_right_count
            self.last_odom_time = current_time

        except ValueError:
            pass

    def publish_odom(self, current_time, vx, vth):
        """/odom と TF を発行"""
        q = self.euler_to_quaternion(0, 0, self.th)

        # TF (odom -> base_link)
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation = q
        self.tf_broadcaster.sendTransform(t)

        # Odom Msg
        odom = Odometry()
        odom.header.stamp = current_time.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation = q
        odom.twist.twist.linear.x = vx
        odom.twist.twist.angular.z = vth
        self.odom_pub.publish(odom)

    def euler_to_quaternion(self, roll, pitch, yaw):
        qx = math.sin(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) - math.cos(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
        qy = math.cos(roll/2) * math.sin(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.cos(pitch/2) * math.sin(yaw/2)
        qz = math.cos(roll/2) * math.cos(pitch/2) * math.sin(yaw/2) - math.sin(roll/2) * math.sin(pitch/2) * math.cos(yaw/2)
        qw = math.cos(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
        return Quaternion(x=qx, y=qy, z=qz, w=qw)

    def stop_motors(self):
        """停止コマンド送信"""
        if self.initialized_successfully and self.serial_port and self.serial_port.is_open:
            self.send_command_to_mcu(0.0, 0.0)

    def timeout_callback(self):
        """タイムアウト監視"""
        if not self.initialized_successfully:
            return
        duration = (self.get_clock().now() - self.last_received_time).nanoseconds / 1e9
        if duration > 0.5:
            self.stop_motors()

    def destroy_node(self):
        """終了処理"""
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
        node.get_logger().fatal("初期化失敗により中断")
        if hasattr(node, 'serial_port') and node.serial_port and node.serial_port.is_open:
            node.serial_port.close()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
