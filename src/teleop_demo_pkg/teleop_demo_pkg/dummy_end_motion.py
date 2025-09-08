# ファイル名: dummy_end_motion.py
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool

class DummyEndMotion(Node):
    def __init__(self):
        super().__init__('dummy_end_motion_node')
        # teleop_demo2からの吸引コマンドを受け取るSubscriber
        self.cmd_subscriber = self.create_subscription(String, 'suction_command', self.command_callback, 10)
        # teleop_demo2にリセット指令を送るPublisher
        self.teleop_reset_publisher = self.create_publisher(Bool, '/teleop/reset_state', 10)
        self.get_logger().info("Dummy End Motion has been started. (Hardware connection is disabled)")

    def command_callback(self, msg):
        self.get_logger().info(f"Received suction command: '{msg.data}'")
        if msg.data == 'START_SUCTION' or msg.data == 'STOP_SUCTION':
            self.get_logger().info("Publishing reset signal to /teleop/reset_state.")
            reset_msg = Bool()
            reset_msg.data = True
            self.teleop_reset_publisher.publish(reset_msg)

def main(args=None):
    rclpy.init(args=args)
    node = DummyEndMotion()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()