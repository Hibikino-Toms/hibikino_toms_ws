# ファイル名: dummy_arm_controller.py
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from std_msgs.msg import Float32
from toms_msg.srv import ArmService

class DummyArmController(Node):
    def __init__(self):
        super().__init__('dummy_arm_controller')
        # teleop_demo2からの指令を受け取るSubscriber
        self.pos_subscriber = self.create_subscription(Point, 'target_arm_pos', self.pos_callback, 10)
        self.angle_subscriber = self.create_subscription(Float32, 'target_arm_angle', self.angle_callback, 10)
        # end_motionからのサービス呼び出しに対応するService Server
        self.srv = self.create_service(ArmService, "arm_service", self.service_callback)
        self.get_logger().info("Dummy Arm Controller has been started. (Hardware connection is disabled)")

    def pos_callback(self, msg):
        self.get_logger().info(f"Received target arm position: [x={msg.x:.2f}, y={msg.y:.2f}, z={msg.z:.2f}]")

    def angle_callback(self, msg):
        self.get_logger().info(f"Received target arm angle: {msg.data:.2f}")

    def service_callback(self, request, response):
        self.get_logger().info(f"Received arm_service request: '{request.task}'. Pretending to succeed.")
        response.task_comp = True # 常に「成功」を返す
        return response

def main(args=None):
    rclpy.init(args=args)
    node = DummyArmController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()