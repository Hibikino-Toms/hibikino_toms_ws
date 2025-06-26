import rclpy
from rclpy.node import Node
from toms_msg.srv import SuctionCommand

from playsound import playsound

class SuctionModuleClientNode(Node):
    def __init__(self):
        super().__init__('suction_module_client_node')
        self.suction_client = self.create_client(SuctionCommand, 'command')
        # playsound("/home/ylab/hibikino_toms_ws/src/end_effector_pkg/end_effector_pkg/sound/サクションモジュールクライアントノードを起動したのだ.wav")
        while not self.suction_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('サービスは利用できません．待機中...')
        # リクエストのインスタンスを生成
        self.request = SuctionCommand.Request()

    def send_request(self, mode):
        self.request.command = mode
        self.future = self.suction_client.call_async(self.request)
        rclpy.spin_until_future_complete(self, self.future)

def main(args=None):
    rclpy.init(args=args)
    client_node = SuctionModuleClientNode()

    while rclpy.ok():
        print('Modeを入力')
        mode = input('mode = ')
        # print(type(mode))
        client_node.send_request(mode)
        # rclpy.spin_once(client_node)
        if client_node.future.done():  # サービスの処理が終了したら
            try:
                response = client_node.future.result()  # サービスの結果をレスポンスに代入    
                # response = mode
            except Exception as e:
                client_node.get_logger().info(f"サービスのよび出しは失敗しました．{e}")
            finally:                
                client_node.get_logger().info( # 結果の表示
                    f"\nリクエスト:{client_node.request} -> レスポンス: {response}")
                #break
    rclpy.shutdown()