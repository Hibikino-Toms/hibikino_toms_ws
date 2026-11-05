#!/usr/bin/env python
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from std_msgs.msg import String
import time
import numpy as np
from toms_msg.srv import ArmService, EndEffectorService


class ArmClientNode(Node):
    def __init__(self):
        super().__init__('manual_arm_client')

        self.client = self.create_client(
            ArmService,
            "arm_service",
            qos_profile=qos_profile_services_default)

        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("ArmService 待機中...")

        self.req = ArmService.Request()

    def move_to_xyz(self, x, y, z, ang=0):
        self.req.task = "move_to_target"
        self.req.target.x = x
        self.req.target.y = y
        self.req.target.z = z
        self.req.target.approach_direction = ang

        future = self.client.call_async(self.req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

def main(args=None):
    rclpy.init(args=args)
    node = ArmClientNode()

    while rclpy.ok():
        x = float(input("X(mm) ▶ "))
        y = float(input("Y(mm) ▶ "))
        z = float(input("Z(mm) ▶ "))
        res = node.move_to_xyz(x, y, z)
        print("結果:", res.task_comp)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
