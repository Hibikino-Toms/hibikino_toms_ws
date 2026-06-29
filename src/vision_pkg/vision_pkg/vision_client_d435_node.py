#!/usr/bin/env python
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from std_msgs.msg import String
import time
import numpy as np

from toms_msg.msg import TomatoPos,TomatoData
from toms_msg.srv import VisionService

class VisionClientD435Node(Node):
    def __init__(self):
        super().__init__('vision_client_d435_node')
        self.vision_client = self.create_client(VisionService,"vision_service_d435")
        while not self.vision_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('サービスは利用できません．待機中...')
        self.vision_request =  VisionService.Request()

    def vision_send_request_check(self):
        self.vision_request.task = "detect_check"
        self.vision_request.direction = "f"
        self.vision_future = self.vision_client.call_async(self.vision_request)
        #rclpy.spin_until_future_complete(node, self.vision_future)
        rclpy.spin_until_future_complete(self, self.vision_future)
        return self.vision_future.result()

    def vision_send_request_pos(self):
        self.vision_request.task = "req_tomato_pose"
        self.vision_request.direction = "f"
        self.future = self.vision_client.call_async(self.vision_request)
        #rclpy.spin_until_future_complete(node, self.future)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()


def main(args=None):
    rclpy.init(args=args)
    client_node = VisionClientD435Node()

    try:
        while rclpy.ok():
            start_vision = input('detect_checkをする場合は1を、req_tomato_poseをする場合は2を入力してください ')
            if(start_vision == "1"):
                vision_response = client_node.vision_send_request_check()
                if vision_response is not None:
                    if vision_response.detect_check:
                        print("トマトを見つけたよ")
                    else:
                        print("トマトが見つからねえよ")
                else:
                    print("エラーだよー")
            elif(start_vision == "2"):
                vision_response2 = client_node.vision_send_request_pos()
                print(vision_response2.target_pos)
            else:
                print("1か2を入力してください")

    
    except KeyboardInterrupt:
        print("\n")
        pass
    else:
        rclpy.shutdown()
    finally:
        client_node.destroy_node()




if __name__ == "__main__":
    main()