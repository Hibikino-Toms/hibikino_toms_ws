#!/usr/bin/env python
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from std_msgs.msg import String
import time
import numpy as np

from std_msgs.msg import Int32  # 累積エンコーダカウントのパブリッシュに使用
from toms_msg.srv import CrawlerService

class CrawlerClientNode(Node):
    def __init__(self):
        super().__init__('crawler_client_node')
        self.crawler_client = self.create_client(CrawlerService,"crawler_control")
        while not self.crawler_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('サービスは利用できません．待機中...')
        self.crawler_request =  CrawlerService.Request()
        
        self.data = None

    def topic_callback(self, msg):
        """
        トピック 'crawler_pulse' のコールバック関数
        """
        self.data = msg.data
        self.get_logger().info(f"Received pulse count: {self.data}")

    def crawler_send_request_f(self):
        self.crawler_request.req_dir = "f"
        self.crawler_future = self.crawler_client.call_async(self.crawler_request)
        #rclpy.spin_until_future_complete(node, self.crawler_future)
        rclpy.spin_until_future_complete(self, self.crawler_future)
        return self.crawler_future.result()

    def crawler_send_request_b(self):
        self.crawler_request.req_dir = "b"
        self.future = self.crawler_client.call_async(self.crawler_request)
        #rclpy.spin_until_future_complete(node, self.future)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()
    
    def execut(self):
        while 1:
        # トピック購読の追加
            subscription = self.create_subscription(Int32, 'crawler_pulse', self.topic_callback, 10)
            subscription  # 未使用警告を防ぐため
            
            print(f'data: {self.data}')
        
            start_crawler = str(input("送るリクエストを入力してください.  前進＝'f'/後退＝'b' : ").strip().lower())
            
            if start_crawler == "f":
                crawler_response = self.crawler_send_request_f()
                print('前進のリクエストを送ったよー')
            else:
                crawler_response = self.crawler_send_request_b()
                print('後退のリクエストを送ったよー')
            
            print(crawler_response)
            


def main(args=None):
    rclpy.init(args=args)
    client_node = CrawlerClientNode()

    try:
        client_node.execut()
    
    except KeyboardInterrupt:
        pass
    else:
        rclpy.shutdown()
    finally:
        print("\n")
        client_node.destroy_node()




if __name__ == "__main__":
    main()