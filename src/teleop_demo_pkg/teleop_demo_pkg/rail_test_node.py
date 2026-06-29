import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from toms_msg.srv import RailService # RailServiceの型をインポート

class RailTestNode(Node):
    """
    @class RailTestNode
    @brief JoyパッドのLB/RBボタンでレールを連続的に操作するテスト用クラス
    """
    def __init__(self):
        super().__init__('rail_test_node')

        # --- パラメータ設定 ---
        self.declare_parameter('rail_forward_button', 5)  # RBボタン
        self.declare_parameter('rail_backward_button', 4) # LBボタン

        # --- SubscriberとService Clientの作成 ---
        self.joy_subscriber = self.create_subscription(Joy, 'joy', self.joy_callback, 10)
        self.rail_client = self.create_client(RailService, 'rail_control')

        while not self.rail_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('レール制御サービスが見つかりません。待機中...')
        self.get_logger().info('レール制御サービスに接続しました。')

        # ★★★ 変更点：状態を管理するための変数を追加 ★★★
        self.is_service_running = False # サービス呼び出し中かどうかのフラグ
        self.latest_joy_msg = None      # 最新のJoyメッセージを保持する変数

        self.get_logger().info("Rail Test Node has been started.")
        self.get_logger().info("LBボタンを長押し: 後退 / RBボタンを長押し: 前進")

    def joy_callback(self, msg):
        """Joyパッドの最新の状態を常に保持し、連続動作のきっかけを作る"""
        # 最新のコントローラー状態を保存
        self.latest_joy_msg = msg

        # 既に連続動作中（サービス呼び出し中）であれば、ここでは何もしない
        # (動作の継続はレスポンス受信後に行う)
        if self.is_service_running:
            return

        # --- 連続動作の「開始トリガー」 ---
        forward_btn = self.get_parameter('rail_forward_button').value
        backward_btn = self.get_parameter('rail_backward_button').value

        # RBボタンが押されていれば、前進の連続動作を開始
        if msg.buttons[forward_btn] == 1:
            self.is_service_running = True # 連続動作フラグをON
            self.send_rail_request('f')
        # LBボタンが押されていれば、後退の連続動作を開始
        elif msg.buttons[backward_btn] == 1:
            self.is_service_running = True # 連続動作フラグをON
            self.send_rail_request('b')

    def send_rail_request(self, direction):
        """レール制御サービスにリクエストを非同期で送信する"""
        request = RailService.Request()
        request.req_dir = direction
        
        future = self.rail_client.call_async(request)
        future.add_done_callback(self.rail_response_callback)
        # ログが流れすぎないように、リクエスト送信時のログはコメントアウト
        # self.get_logger().info(f"レールを '{direction}' 方向へ動かすリクエストを送信しました。")

    def rail_response_callback(self, future):
        """
        ★★★ 変更点：サービスからの応答を受け取った後の処理 ★★★
        前の動作が完了した時点で、まだボタンが押されているかを確認し、
        押されていれば次の動作リクエストを送信する（連鎖させる）。
        """
        try:
            response = future.result()
            self.get_logger().info(f"レールサービスからの応答: Direction='{response.res_dir}', Pulse={response.pulse.data}")
        except Exception as e:
            self.get_logger().error(f'サービスコールに失敗しました: {e}')
            self.is_service_running = False # エラー時は連続動作を中断
            return

        # 最新のコントローラー情報がなければ、処理を中断
        if self.latest_joy_msg is None:
            self.is_service_running = False
            return

        forward_btn = self.get_parameter('rail_forward_button').value
        backward_btn = self.get_parameter('rail_backward_button').value

        # --- 連続動作の「継続判定」 ---
        # まだRBボタンが押されていれば、次の前進リクエストを送る
        if self.latest_joy_msg.buttons[forward_btn] == 1:
            self.send_rail_request('f')
        # まだLBボタンが押されていれば、次の後退リクエストを送る
        elif self.latest_joy_msg.buttons[backward_btn] == 1:
            self.send_rail_request('b')
        # どちらのボタンも離されていれば、連続動作を終了
        else:
            self.is_service_running = False
            self.get_logger().info("ボタンが離されたため、連続動作を停止します。")

def main(args=None):
    rclpy.init(args=args)
    node = RailTestNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()