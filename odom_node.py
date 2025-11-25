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
import math

class CrawlerControllerSerial(Node):
    """
    ユーザー指定の while 1 ループを用いて同期的にデータを受信し、
    オドメトリを計算・配信するノード。
    """
    
    # 定数: 1mあたりのカウント数
    COUNTS_PER_METER = 17400.0

    @staticmethod
    def load_yaml(file_path):
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"YAMLファイルの解析エラー: {e}")

    def __init__(self):
        super().__init__('crawler_controller_serial') 
        self.get_logger().info('クローラー制御＆オドメトリノード (Whileループ版) を起動します。')
        
        self.serial_port = None
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        
        try:
            params = self.load_yaml(yaml_path)
            crawler_params = params["crawler_params"]
            self.serial_number = crawler_params['CRAWLER_PICO_SERIAL_NUMBER']
            self.baudrate = crawler_params['BAUDRATE']
            self.tread_width = crawler_params.get('TREAD', 0.4)

            self.get_logger().info(f"設定読み込み完了: BAUDRATE={self.baudrate}, TREAD={self.tread_width}")

        except (FileNotFoundError, KeyError, ValueError) as e:
            self.get_logger().fatal(f"設定エラー: {e}")
            self.initialized_successfully = False 
            return
        
        self.initialized_successfully = True

        # --- オドメトリ用変数 ---
        self.x = 0.0
        self.y = 0.0
        self.th = 0.0
        self.prev_left_count = None
        self.prev_right_count = None
        self.last_odom_time = self.get_clock().now()

        # --- ROS通信 ---
        self.subscription = self.create_subscription(
            Float32MultiArray,
            '/crawler_pwms',
            self.pwm_callback, 
            10)
        
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # 安全停止用タイマー
        self.last_received_time = self.get_clock().now()
        self.timeout_timer = self.create_timer(0.1, self.timeout_callback)

        self.setup_serial()

    def select_device(self, serial_number):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.serial_number == serial_number:
                return port.device
        return None

    def setup_serial(self):
        if not self.initialized_successfully: return
        
        if not hasattr(self, 'serial_number') or not self.serial_number:
            self.initialized_successfully = False
            return
            
        device_name = self.select_device(self.serial_number)
        if device_name is None:
            self.initialized_successfully = False
            return
        
        try:
            # whileループで待つため、timeoutは長めでも動作します
            self.serial_port = serial.Serial(device_name, self.baudrate, timeout=1.0)
            self.get_logger().info(f'{device_name} 接続成功')
        except serial.SerialException as e:
            self.get_logger().fatal(f'接続失敗: {e}')
            self.initialized_successfully = False

    def pwm_callback(self, msg: Float32MultiArray):
        """指定のコードブロックを組み込んだコールバック"""
        if not self.initialized_successfully or not self.serial_port or not self.serial_port.is_open:
            return

        self.last_received_time = self.get_clock().now()
        
        # 1. バッファクリア (推奨: これがないと古いデータとズレて計算してしまいます)
        self.serial_port.reset_input_buffer()

        # 2. PWM送信
        pwm_left = msg.data[0]
        pwm_right = msg.data[1]
        self.send_command_to_mcu(pwm_left, pwm_right)

        # 3. 指定された while 1 ループによる受信待ち・計算処理
        # ---------------------------------------------------------
        while 1:
            if self.serial_port.in_waiting > 0:
                try:
                    # decodeエラーで落ちないよう errors='ignore' を推奨しますが、指定通り記述します
                    pulse_data = self.serial_port.readline().strip().decode('utf-8', errors='ignore')
                    
                    # ログ出力 (指定コード)
                    # self.get_logger().info(f"Receive from microcontroller: pulse_data={pulse_data}")

                    # ★ここでオドメトリ計算を実行します★
                    self.calculate_and_publish_odom(pulse_data)
                    
                    break # データを受け取ったらループを抜ける
                except Exception as e:
                    self.get_logger().error(f"Parse Error: {e}")
                    break
            else:
                # 指定のログ出力
                # 注意: データが来るまでこのログが大量に(秒間数千回)出続ける可能性があります
                # self.get_logger().info(f"Wait for Receive from microcontroller...")
                pass # ログが多すぎる場合は pass にしてください
        # ---------------------------------------------------------

    def calculate_and_publish_odom(self, pulse_data):
        """受信データを使ってオドメトリ計算"""
        try:
            parts = pulse_data.split(',')
            if len(parts) != 2:
                return

            current_left_count = float(parts[0])
            current_right_count = float(parts[1])

            if self.prev_left_count is None:
                self.prev_left_count = current_left_count
                self.prev_right_count = current_right_count
                self.last_odom_time = self.get_clock().now()
                return

            current_time = self.get_clock().now()
            dt = (current_time - self.last_odom_time).nanoseconds / 1e9
            
            if dt < 0.0001: return

            # 移動量計算
            delta_l = (current_left_count - self.prev_left_count) / self.COUNTS_PER_METER
            delta_r = (current_right_count - self.prev_right_count) / self.COUNTS_PER_METER

            d_center = (delta_r + delta_l) / 2.0
            delta_th = (delta_r - delta_l) / self.tread_width

            vx = d_center / dt
            vth = delta_th / dt

            # 位置更新
            if d_center != 0:
                self.x += d_center * math.cos(self.th + delta_th / 2.0)
                self.y += d_center * math.sin(self.th + delta_th / 2.0)
            self.th += delta_th

            # Publish
            self.publish_odom_msg(current_time, vx, vth)

            # 更新
            self.prev_left_count = current_left_count
            self.prev_right_count = current_right_count
            self.last_odom_time = current_time

        except ValueError:
            pass

    def publish_odom_msg(self, current_time, vx, vth):
        q = self.euler_to_quaternion(0, 0, self.th)

        # TF
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation = q
        self.tf_broadcaster.sendTransform(t)

        # Odom
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

    def send_command_to_mcu(self, pwm_left, pwm_right):
        if self.serial_port and self.serial_port.is_open:
            command = f"{int(pwm_left)},{int(pwm_right)}\n"
            try:
                self.serial_port.write(command.encode('utf-8'))
            except Exception as e:
                self.get_logger().error(f"Write Error: {e}")

    def stop_motors(self):
        if self.initialized_successfully and self.serial_port and self.serial_port.is_open:
            self.send_command_to_mcu(0.0, 0.0)

    def timeout_callback(self):
        if not self.initialized_successfully: return
        duration = (self.get_clock().now() - self.last_received_time).nanoseconds / 1e9
        if duration > 0.5:
            self.stop_motors()

    def destroy_node(self):
        if hasattr(self, 'initialized_successfully') and self.initialized_successfully:
            self.stop_motors()
            time.sleep(0.1)
            if self.serial_port: self.serial_port.close()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = CrawlerControllerSerial()
    if hasattr(node, 'initialized_successfully') and node.initialized_successfully:
        try:
            rclpy.spin(node)
        except KeyboardInterrupt: pass
        finally: node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
