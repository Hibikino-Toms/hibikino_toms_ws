import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray # 左右PWM値を送信するためのメッセージ

class TwistToCrawlerConverter(Node):
    def __init__(self):
        super().__init__('twist_to_crawler_converter')
        self.get_logger().info('TwistToCrawlerConverterノードを起動します。')

        # パラメータ (YAMLからの読み込みは不要。Launchファイル等で設定可能)
        self.declare_parameter('tread', 0.21)  # 左右クローラー間の距離 [m]
        self.declare_parameter('max_linear_speed', 0.3)  # 最大並進速度 [m/s]
        
        self.tread = self.get_parameter('tread').get_parameter_value().double_value
        self.max_linear_speed = self.get_parameter('max_linear_speed').get_parameter_value().double_value

        # Subscriber: /cmd_vel (Twist型)
        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10)
        
        # Publisher: /crawler_pwms (Float32MultiArray型)
        self.publisher = self.create_publisher(
            Float32MultiArray,
            '/crawler_pwms', # 左右のPWM値を送る新しいトピック名
            10)

        self.last_cmd_vel_time = self.get_clock().now()
        self.timeout_timer = self.create_timer(0.1, self.timeout_callback)

    def cmd_vel_callback(self, msg):
        self.last_cmd_vel_time = self.get_clock().now()

        v = msg.linear.x
        omega = msg.angular.z

        # 運動学モデルに基づいて左右のクローラーの速度を計算
        v_right = v + (omega * self.tread / 2.0)
        v_left = v - (omega * self.tread / 2.0)

        # 速度をPWMデューティ比 (-25.0 ~ 25.0) に変換
        # クリップもここで実施
        pwm_right = (v_right / self.max_linear_speed) * 25.0
        pwm_left = (v_left / self.max_linear_speed) * 25.0
        
        pwm_right = max(min(pwm_right, 25.0), -25.0)
        pwm_left = max(min(pwm_left, 25.0), -25.0)

        # Float32MultiArrayメッセージを作成し、発行
        pwm_msg = Float32MultiArray()
        pwm_msg.data = [float(pwm_left), float(pwm_right)]
        self.publisher.publish(pwm_msg)
        # self.get_logger().info(f'発行: Left={pwm_msg.data[0]:.2f}, Right={pwm_msg.data[1]:.2f}')

    def timeout_callback(self):
        """タイムアウト時に停止コマンドを発行"""
        duration = (self.get_clock().now() - self.last_cmd_vel_time).nanoseconds / 1e9
        if duration > 0.5:
            # 停止コマンド (PWM = 0, 0) を発行
            stop_pwm_msg = Float32MultiArray()
            stop_pwm_msg.data = [0.0, 0.0]
            self.publisher.publish(stop_pwm_msg)
            # self.get_logger().info('タイムアウト: 停止コマンド発行')

    def destroy_node(self):
        # 終了時にも停止コマンドを発行
        stop_pwm_msg = Float32MultiArray()
        stop_pwm_msg.data = [0.0, 0.0]
        self.publisher.publish(stop_pwm_msg)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = TwistToCrawlerConverter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()