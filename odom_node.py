import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Quaternion
from tf2_ros import TransformBroadcaster
import serial
import math
import threading

class TomatoOdomNode(Node):
    def __init__(self):
        super().__init__('tomato_odom_node')

        # --- 設定パラメータ (必要に応じて変更してください) ---
        # シリアルポート: Jetsonに接続したデバイスパスを確認してください (ls /dev/tty*)
        self.declare_parameter('serial_port', '/dev/ttyUSB0') 
        # ボーレート: マイコン側のSerial.begin()の値と合わせる必要があります
        self.declare_parameter('baud_rate', 115200)
        # トレッド幅: 40cm = 0.4m と仮定
        self.declare_parameter('tread_width', 0.40) 

        self.serial_port = self.get_parameter('serial_port').get_parameter_value().string_value
        self.baud_rate = self.get_parameter('baud_rate').get_parameter_value().integer_value
        self.tread_width = self.get_parameter('tread_width').get_parameter_value().double_value

        # 定数: 1mあたりのカウント数 (0-17400 = 1m)
        self.COUNTS_PER_METER = 17400.0

        # --- 内部変数 ---
        self.x = 0.0
        self.y = 0.0
        self.th = 0.0  # ロボットの向き (rad)
        
        self.prev_left_count = None
        self.prev_right_count = None
        self.last_time = self.get_clock().now()

        # --- ROS 2 通信設定 ---
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # --- シリアル通信接続 ---
        try:
            self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            self.get_logger().info(f"Connected to serial: {self.serial_port} at {self.baud_rate}")
        except serial.SerialException as e:
            self.get_logger().error(f"Failed to connect to serial: {e}")
            # 実運用ではここで終了するか、再接続ロジックを入れる
            return

        # 受信ループを別スレッドで開始（メインスレッドをブロックしないため）
        self.read_thread = threading.Thread(target=self.read_serial_loop)
        self.read_thread.daemon = True
        self.read_thread.start()

    def read_serial_loop(self):
        """シリアルデータを読み込み続けるループ"""
        while rclpy.ok():
            try:
                if self.ser.in_waiting > 0:
                    # decodeエラーを無視して読み込む
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.process_data(line)
            except Exception as e:
                self.get_logger().warn(f"Serial read error: {e}")

    def process_data(self, line):
        """
        受信データ解析とオドメトリ計算
        想定フォーマット: "LeftVal,RightVal" (例: "17400,-500")
        """
        try:
            parts = line.split(',')
            if len(parts) != 2:
                # データの数が合わない場合は無視（ノイズ対策）
                return
            
            # 順序が「左, 右」であると仮定しています
            current_left_count = float(parts[0])
            current_right_count = float(parts[1])

            # 初回受信時は前回値がないので初期化のみ
            if self.prev_left_count is None:
                self.prev_left_count = current_left_count
                self.prev_right_count = current_right_count
                self.last_time = self.get_clock().now()
                return

            # --- オドメトリ計算 (Differential Drive) ---
            current_time = self.get_clock().now()
            dt = (current_time - self.last_time).nanoseconds / 1e9
            
            # dtが極端に小さい場合（バースト受信など）は計算スキップ
            if dt < 0.0001:
                return

            # 1. カウントの増分を計算
            delta_l_count = current_left_count - self.prev_left_count
            delta_r_count = current_right_count - self.prev_right_count

            # 2. 距離に変換 (m)
            d_left = delta_l_count / self.COUNTS_PER_METER
            d_right = delta_r_count / self.COUNTS_PER_METER

            # 3. 移動距離と回転角の計算
            # 右車輪が多く進むと左に曲がる(反時計回り正)ため (R - L) / W
            d_center = (d_right + d_left) / 2.0
            delta_th = (d_right - d_left) / self.tread_width

            # 4. 速度計算 (m/s, rad/s)
            vx = d_center / dt
            vth = delta_th / dt

            # 5. 現在位置(x, y, th)の更新
            # わずかな移動の場合は直線近似でOKだが、高精度にするならRunge-Kutta法などを使う
            if d_center != 0:
                delta_x = d_center * math.cos(self.th + delta_th / 2.0)
                delta_y = d_center * math.sin(self.th + delta_th / 2.0)
                self.x += delta_x
                self.y += delta_y
            
            self.th += delta_th

            # --- パブリッシュ処理 ---
            self.publish_odom(current_time, vx, vth)

            # 次回のために変数を更新
            self.prev_left_count = current_left_count
            self.prev_right_count = current_right_count
            self.last_time = current_time

        except ValueError:
            # 数値変換に失敗した場合（文字化けなど）は無視
            pass 

    def publish_odom(self, current_time, vx, vth):
        q = self.euler_to_quaternion(0, 0, self.th)

        # 1. TFの発行 (odom -> base_link)
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation = q
        self.tf_broadcaster.sendTransform(t)

        # 2. /odom トピックの発行
        odom = Odometry()
        odom.header.stamp = current_time.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'

        # 位置
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation = q

        # 速度
        odom.twist.twist.linear.x = vx
        odom.twist.twist.angular.z = vth

        self.odom_pub.publish(odom)

    def euler_to_quaternion(self, roll, pitch, yaw):
        qx = math.sin(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) - math.cos(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
        qy = math.cos(roll/2) * math.sin(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.cos(pitch/2) * math.sin(yaw/2)
        qz = math.cos(roll/2) * math.cos(pitch/2) * math.sin(yaw/2) - math.sin(roll/2) * math.sin(pitch/2) * math.cos(yaw/2)
        qw = math.cos(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
        return Quaternion(x=qx, y=qy, z=qz, w=qw)

def main(args=None):
    rclpy.init(args=args)
    node = TomatoOdomNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
