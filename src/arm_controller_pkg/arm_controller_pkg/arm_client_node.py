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
        super().__init__('arm_client_node')
        self.arm_client = self.create_client(ArmService,"arm_service")
        while not self.arm_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('サービスは利用できません．待機中...')
        self.arm_request =  ArmService.Request()

    def arm_send_request_init(self):
        self.arm_request.task = "init_arm"
        self.arm_future = self.arm_client.call_async(self.arm_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        return self.arm_future.result()

    def arm_send_request_move(self):
        self.arm_request.task = "move_to_target"
        # ユーザー入力
        self.arm_request.target.x = int(input("目標のx座標 (mm): "))
        self.arm_request.target.y = int(input("目標のy座標 (mm): "))
        self.arm_request.target.z = int(input("目標のz座標 (mm): "))
        self.arm_request.target.approach_direction = int(input("目標の手先角度 (°): "))
        self.arm_future = self.arm_client.call_async(self.arm_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        return self.arm_future.result()
    
    def arm_send_request_box(self):
        self.arm_request.task = "move_to_box"
        # ユーザー入力
        self.arm_request.target.x = int(input("噛み切り時のx座標 (mm): "))
        self.arm_request.target.y = int(input("噛み切り時のy座標 (mm): "))
        self.arm_request.target.z = int(input("噛み切り時のz座標 (mm): "))
        self.arm_request.target.approach_direction = int(input("噛み切り時の手先角度 (°): "))
        self.arm_future = self.arm_client.call_async(self.arm_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        return self.arm_future.result()
    
    def arm_send_request_home(self):
        self.arm_request.task = "home"
        self.arm_future = self.arm_client.call_async(self.arm_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        return self.arm_future.result()


def main(args=None):
    rclpy.init(args=args)
    client_node = ArmClientNode()

    try:
        while rclpy.ok():
            start_arm = input('アームサービスへリクエストを送信 (1:init, 2:move, 3:box, 4:home ▶ ')
            if start_arm == '1':
                arm_response = client_node.arm_send_request_init()
                print("アームを初期ポジションへ移動しました")
            elif start_arm == '2':
                arm_response = client_node.arm_send_request_move()
                print("アームを目標値へ移動しました")
            elif start_arm == '3':
                arm_response = client_node.arm_send_request_box()
                print("アームを収穫ボックスへ移動しました")
            elif start_arm == '4':
                arm_response = client_node.arm_send_request_home()
                print("アームをホームポジションへ移動しました")
            # elif start_arm == '5':
            #     arm_response = client_node.arm_send_request_cutting()
            #     print("噛み切り動作を行いました")
            else:
                print("エラーだよー")
    except KeyboardInterrupt:
        print("\nCtrl+C has been entered")  
        print("End of program")
    else:
        rclpy.shutdown()
    finally:
        client_node.destroy_node()




if __name__ == "__main__":
    main()