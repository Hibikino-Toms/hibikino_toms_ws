#!/usr/bin/env python
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from std_msgs.msg import String
import time
import numpy as np

from std_msgs.msg import Int32  # 累積エンコーダカウントのパブリッシュに使用
from toms_msg.srv import RailService

class RailClientNode(Node):
    def __init__(self):
        super().__init__('rail_client_node')
        self.rail_client = self.create_client(RailService,"rail_control")
        while not self.rail_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('サービスは利用できません．待機中...')
        self.rail_request =  RailService.Request()
        
        self.data = None

    def topic_callback(self, msg):
        """
        トピック 'railr_pulse' のコールバック関数
        """
        self.data = msg.data
        self.get_logger().info(f"Received pulse count: {self.data}")

    def rail_send_request_f(self):
        self.rail_request.req_dir = "f"
        self.future = self.rail_client.call_async(self.rail_request)
        #rclpy.spin_until_future_complete(node, self.rail_future)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()

    def rail_send_request_b(self):
        self.rail_request.req_dir = "b"
        self.future = self.rail_client.call_async(self.rail_request)
        #rclpy.spin_until_future_complete(node, self.future)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()

    def rail_send_request_s(self):
        self.rail_request.req_dir = "s"
        self.future = self.rail_client.call_async(self.rail_request)
        #rclpy.spin_until_future_complete(node, self.future)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()
    
    def execut(self):
        while 1:
        # トピック購読の追加
            rail_subscription = self.create_subscription(Int32, 'rail_pulse', self.topic_callback, 10)
            rail_subscription  # 未使用警告を防ぐため
            
            print(f'data: {self.data}')
        
            start_rail = input("送るリクエストを入力してください.  前進＝'f'/後退＝'b' : ").strip().lower()
            start_rail = str(start_rail)
            
            if start_rail == "f":
                rail_response = self.rail_send_request_f()
                print('前進のリクエストを送ったよー')
            elif start_rail == "b":
                rail_response = self.rail_send_request_b()
                print('後退のリクエストを送ったよー')
            else:
                rail_response = self.rail_send_request_s()
                print('止まれのリクエストを送ったよー')

            print(rail_response)
            


def main(args=None):
    rclpy.init(args=args)
    client_node = RailClientNode()
    

    try:
        client_node.execut()
    
    except KeyboardInterrupt:
        pass
    else:
        rclpy.shutdown()
    finally:
        client_node.destroy_node()




if __name__ == "__main__":
    main()
