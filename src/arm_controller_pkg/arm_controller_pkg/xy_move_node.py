#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from toms_msg.srv import ArmService

class XYMoveNode(Node):
    def __init__(self):
        super().__init__('xy_move_node')

        self.client = self.create_client(ArmService, "arm_service")
        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("アームサービス待機中...")

        self.req = ArmService.Request()

    def move_xy(self, x_mm, y_mm):
        self.req.task = "move_to_target"
        self.req.target.x = x_mm
        self.req.target.y = y_mm
        self.req.target.z = 0      # Z は固定
        self.req.target.approach_direction = 0

        future = self.client.call_async(self.req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

def main(args=None):
    rclpy.init(args=args)
    node = XYMoveNode()

    while rclpy.ok():
        x = int(input("X方向(mm) ▶ "))
        y = int(input("Y方向(mm) ▶ "))
        res = node.move_xy(x, y)
        print("返り値:", res)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
