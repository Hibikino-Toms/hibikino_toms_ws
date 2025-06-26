import rclpy
from rclpy.node import Node

from toms_msg.srv import CartService

class MoveCartClient(Node):
    def __init__(self):
        super().__init__('move_cart_client')
        self.client = self.create_client(CartService, 'cart')
        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('サービスは利用できません．待機中...')
        # リクエストのインスタンスを生成
        self.request = CartService.Request()

    def send_request(self,move_x,pwm_value):
        self.request.move_value = move_x
        self.request.pwm_value = pwm_value
        self.future = self.client.call_async(self.request)

def main(args=None):
    rclpy.init(args=args)
    client_node = MoveCartClient()

    while rclpy.ok():
        print('移動量を入力[mm]')
        x = int(input('x = '))
        print('パルスを入力(0~255)')
        p = int(input('p = '))
        client_node.send_request(x,p)
        rclpy.spin_once(client_node)
        if client_node.future.done():  # サービスの処理が終了したら
            try:
                response = client_node.future.result()  # サービスの結果をレスポンスに代入                  
            except Exception as e:
                client_node.get_logger().info(f"サービスのよび出しは失敗しました．{e}")
            else:                
                client_node.get_logger().info( # 結果の表示
                    f"\nリクエスト:{client_node.request} -> レスポンス: {response}")
                break  
    rclpy.shutdown()