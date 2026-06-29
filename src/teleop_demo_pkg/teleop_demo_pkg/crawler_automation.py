import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_services_default
# ★★★ Twistメッセージのインポートを追加 ★★★
from geometry_msgs.msg import Twist, PoseStamped, PoseWithCovarianceStamped
from toms_msg.srv import SuctionCommand, ArmService, VisionService, RailService

from playsound import playsound
import time
import numpy as np
import yaml
import sys

# YAML読み込み関数をクラスの外に定義（mainからも呼べるようにするため）
def load_yaml(file_path):
    try:
        with open(file_path, "r") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"YAMLファイルの解析エラー: {e}")

class AnalizeToHarvestNode(Node):
    def __init__(self):
        super().__init__('crawler_automation') # ノード名を変更
        
        self.detect_tomato = False

        # === 往復移動用の変数を初期化 ===
        self.pose_a = None  # 初期位置 (Initial Pose)
        self.pose_b = None  # 目的地 (Goal Pose)
        self.next_target = 'B' # 次に向かう場所 ('A' or 'B')
        self.is_patrolling = False # 往復モードが有効かどうか

        # === VisionService クライアント ===
        self.vision_client = self.create_client(
            VisionService,
            "vision_service",
            qos_profile=qos_profile_services_default)
        while not self.vision_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('ビジョンサーバ待機中...')
        self.vision_request =  VisionService.Request()
        
        # === ArmService クライアント ===
        self.arm_client = self.create_client(
            ArmService,
            "arm_service",
            qos_profile=qos_profile_services_default)
        while not self.arm_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('アームサーバ待機中...')
        self.arm_request =  ArmService.Request()
        
        # === SuctionCommand (EE) クライアント ===
        self.ee_client = self.create_client(
            SuctionCommand,
            'command',
            qos_profile=qos_profile_services_default)
        while not self.ee_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('EEサーバ待機中...')
        self.ee_request = SuctionCommand.Request()
        
        # ★★★ cmd_vel サブスクライバー (入力) ★★★
        self.sub_cmd_vel = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            10
        )
        self.latest_cmd_vel = Twist() # 受信した最新の速度を保存する変数

        # ★★★ cmd_vel_cr パブリッシャー (出力：クローラーへ) ★★★
        self.pub_cmd_vel_cr = self.create_publisher(
            Twist,
            'cmd_vel_cr',
            10
        )
        

        # === Nav2/Rviz連携用 ===
        # 1. Rvizからの入力を受け取る (Topic名はRviz側で変更してください)
        self.sub_goal_pose = self.create_subscription(
            PoseStamped,
            'rviz_goal_pose', # Rvizの2D Goal Poseツールがpublishするトピックを確認してください（通常 /goal_pose）
            self.callback_rviz_goal,
            10
        )
        self.sub_initial_pose = self.create_subscription(
            PoseWithCovarianceStamped,
            'initialpose', # Rvizの2D Pose Estimateツールがpublishするトピック
            self.callback_rviz_initial,
            10
        )
        # 2. Nav2へ目標を送る
        self.pub_nav_goal = self.create_publisher(
            PoseStamped,
            'goal_pose',
            10
        )

        # === 初期化実行 ===
        self.arm_and_ee_send_request_init()


    # ★★★ Rvizからの座標取得コールバック ★★★
    def callback_rviz_initial(self, msg):
        """
        Rvizの [2D Pose Estimate] から受信
        これを「地点A（戻ってくる場所）」として保存します。
        """
        self.get_logger().info("【地点A】初期位置を登録しました。")
        
        # InitialPose(PoseWithCovarianceStamped) を Goal(PoseStamped) の形式に変換して保存
        goal_msg = PoseStamped()
        goal_msg.header = msg.header
        goal_msg.pose = msg.pose.pose # 共分散(covariance)を取り除いて座標だけ抽出
        
        self.pose_a = goal_msg
        self.check_start_patrol()
        
    def callback_rviz_goal(self, msg):
        """
        Rvizの [2D Goal Pose] から受信
        これを「地点B（最初に向かう場所）」として保存します。
        """
        self.get_logger().info("【地点B】目的地を登録しました。")
        self.pose_b = msg
        
        # Goalが来たら、まずはそこへ向かうようにセット
        self.next_target = 'B'
        
        # 両方揃っていればパトロール開始フラグを立てる
        self.check_start_patrol()

    # === ビジョンノードへのリクエスト関数 ===
    def vision_send_request_check(self):
        """俯瞰カメラでのトマト検出をリクエスト"""
        self.vision_request.task = "detect_check"
        self.vision_request.direction = "f" 
        self.vision_future = self.vision_client.call_async(self.vision_request)
        # spinすることで、待機中に cmd_vel のコールバックも処理されます
        rclpy.spin_until_future_complete(self, self.vision_future)
        return self.vision_future.result()

    def vision_send_request_tompos(self):
        """手先カメラでのトマト位置特定をリクエスト"""
        self.vision_request.task = "req_tomato_pose"
        self.vision_request.direction = "f"
        self.vision_future = self.vision_client.call_async(self.vision_request)
        rclpy.spin_until_future_complete(self, self.vision_future)
        return self.vision_future.result()

    # === アームノードへのリクエスト関数 ===
    def arm_and_ee_send_request_init(self):
        """アーム初期化とEE吸引停止・顎開きをリクエスト"""
        self.arm_request.task = "init_arm"
        self.ee_request.command = '0' # 吸引停止
        self.arm_future = self.arm_client.call_async(self.arm_request)
        self.ee_future = self.ee_client.call_async(self.ee_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        rclpy.spin_until_future_complete(self, self.ee_future)
        self.ee_send_request('3') # 顎開く
        return self.arm_future.result()
    
    def arm_send_request_target(self, target, pre_h):
        self.arm_request.task = "move_to_target"
        self.arm_request.target.x = target.x
        self.arm_request.target.y = target.y
        self.arm_request.target.z = target.z + pre_h.data
        self.arm_request.target.approach_direction = target.approach_direction
        
        self.arm_future = self.arm_client.call_async(self.arm_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        return self.arm_future.result()
    
    def arm_send_request_box(self):
        self.arm_request.task = "move_to_box"
        self.arm_future = self.arm_client.call_async(self.arm_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        return self.arm_future.result()
    
    def arm_send_request_home(self, target):
        self.arm_request.task = "home"
        self.arm_request.target.x = target.x
        self.arm_request.target.y = target.y
        self.arm_request.target.z = target.z
        self.arm_request.target.approach_direction = target.approach_direction
        self.arm_future = self.arm_client.call_async(self.arm_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        return self.arm_future.result()

    # === EEノードへのリクエスト関数 ===
    def ee_send_request(self, mode):
        self.ee_request.command = mode
        self.ee_future = self.ee_client.call_async(self.ee_request)
        rclpy.spin_until_future_complete(self, self.ee_future)
        return self.ee_future.result()
    

    # =============================================================
    # ★★★ メイン制御ループ (cmd_vel監視 & 次のゴール送信) ★★★
    # =============================================================

    def check_start_patrol(self):
        """AとBの両方がセットされたら往復モードをONにする"""
        # ★★★ 修正箇所：インデントを修正しました ★★★
        if self.pose_a is not None and self.pose_b is not None:
            if not self.is_patrolling:
                self.get_logger().info(">>> 地点AとBが設定されました。往復移動を開始します！")
                self.is_patrolling = True
                # 即座に最初の移動を開始したい場合はここで呼び出す
                # self.publish_next_goal()

    def cmd_vel_callback(self, msg):
        self.latest_cmd_vel = msg
        # if self.detect_tomato:
        #     self.latest_cmd_vel = Twist() 
        # self.pub_cmd_vel_cr.publish(self.latest_cmd_vel)

    def check_and_move_next(self):
        """
        ロボットが停止しており、かつ往復モードなら次の場所へ移動指令を出す
        """
        # 1. 速度がほぼ0か判定
        is_stopped = (abs(self.latest_cmd_vel.linear.x) < 0.001 and 
                      abs(self.latest_cmd_vel.angular.z) < 0.001)

        # 2. 収穫中でなく、停止していて、往復モードがONの場合
        if not self.detect_tomato and is_stopped and self.is_patrolling:       
            self.publish_next_goal()
            # 連続送信を防ぐため少し待機
            time.sleep(2.0) 

    def publish_next_goal(self):
        """現在のターゲットに応じてGoalをPublishし、ターゲットを入れ替える"""
        
        if self.next_target == 'B':
            self.get_logger().info(f"移動開始 >>> 地点B (GoalPose) へ向かいます")
            self.pub_nav_goal.publish(self.pose_b)
            # 送信したら、次はAに向かうようセット
            self.next_target = 'A'
            
        elif self.next_target == 'A':
            self.get_logger().info(f"移動開始 >>> 地点A (初期位置) へ戻ります")
            self.pub_nav_goal.publish(self.pose_a)
            # 送信したら、次はBに向かうようセット
            self.next_target = 'B'


def main(args=None):
    rclpy.init(args=args)
    node = AnalizeToHarvestNode()
    logger = node.get_logger()
    
    # YAMLファイルの読み込み
    try:
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        # ★★★ 修正箇所：クラス外に出した関数を呼び出す ★★★
        params = load_yaml(yaml_path)
        VOICE = params.get("ZUNDA_VOICE", False)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"YAML読み込みエラー: {e}")
        VOICE = False

    if VOICE:
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/おいしそうなトマトを収穫するのだ.wav")

    try:
        while rclpy.ok():
            # 1. 俯瞰カメラで認識
            # ※ここでspin_until_future_completeが呼ばれるため、cmd_velの更新も行われます
            vision_response = node.vision_send_request_check()
        
            # ★ここで動作状況チェック、止まってたら目的地設定
            node.check_and_move_next()

            if vision_response is not None:
                if vision_response.detect_check:
                    # === トマトが見つかった場合 (停止して収穫) ===
                    logger.info("トマト検出: 足回りを停止して収穫を開始します。")
                    
                    # ★★★ 【仕様】detect_checkがTrue(Noneでない)なら、cmd_vel_crに0をパブリッシュ ★★★
                    stop_twist = Twist() # 全要素0で初期化される
                    node.pub_cmd_vel_cr.publish(stop_twist)

                    if VOICE:
                        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/トマトを見つけたのだ.wav")
                    
                    # 2. アームを認識用ホーム位置へ
                    target = vision_response.target_pos.tomato_data[0]
                    arm_response = node.arm_send_request_home(target)
                    logger.info(f'アーム認識位置 到達: {arm_response}')
                    pre_arm_hight = arm_response.tom_hight
                    
                    # 3. 手先カメラで認識
                    vision_response = node.vision_send_request_tompos()
                    targets = vision_response.target_pos.tomato_data
                    if not targets:
                        logger.warn("手先カメラでターゲットを見失いました。探索に戻ります。")
                        
                        # ここでアームを初期化するコマンドを追加
                        node.arm_and_ee_send_request_init()
                        #次へ行く
                        logger.info("手先カメラでターゲットを見失いました。次に行きます。")
                        start_time = time.time()
                        duration = 1.5
                        while time.time() - start_time < duration:
                            node.pub_cmd_vel_cr.publish(node.latest_cmd_vel)
                            pass

                        continue

                    if VOICE:
                        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/熟したトマトを収穫するのだ.wav")
                    
                    # 4. 見つけたトマトを順番に収穫
                    for i, target in enumerate(targets):
                        logger.info(f"{i+1}個目のトマトへ移動します。")
                        arm_response = node.arm_send_request_target(target, pre_arm_hight)
                        
                        if arm_response.task_comp:
                            time.sleep(0.5)
                            # 5. 吸引 (EE)
                            logger.info("吸引開始 (mode 1)")
                            ee_response = node.ee_send_request('1')
                            if ee_response.answer not in ['1', '666']:
                                logger.warn("吸引失敗。次のターゲットへ。")
                                continue 

                            # 6. 顎閉じる (EE)
                            logger.info("顎閉じ (mode 2)")
                            ee_response = node.ee_send_request('2')
                            if ee_response.answer not in ['2', '666']:
                                logger.warn("顎閉じ失敗。吸引を停止します。")
                                node.ee_send_request('0')
                                continue

                            # 7. ボックスへ移動 (Arm)
                            logger.info("収穫ボックスへ移動")
                            node.arm_send_request_box()
                            
                            # 8. 顎開く (EE)
                            logger.info("顎開き (mode 3)")
                            node.ee_send_request('3')
                            
                            # 9. 吸引停止 (EE)
                            logger.info("吸引停止 (mode 0)")
                            node.ee_send_request('0')
                            
                            logger.info(f"{i+1}個目のトマト収穫完了。")
                        
                        else:
                            logger.error("アームのターゲット移動に失敗しました。")
                            node.ee_send_request('0')
                            node.ee_send_request('3')
                            time.sleep(1)
                    
                    # 10. 全てのターゲット収穫後、アームを初期化
                    logger.info("このエリアの収穫が完了。アームを初期位置に戻します。")
                    node.arm_and_ee_send_request_init()
                    #次へ行く
                    logger.info("このエリアの収穫が完了。次に行きます。")
                    start_time = time.time()
                    duration = 1.5
                    while time.time() - start_time < duration:
                        node.pub_cmd_vel_cr.publish(node.latest_cmd_vel)
                        pass
                    node.detect_tomato = False
                    
                else:
                    # === トマトが見つからなかった場合 (手動操作パススルー) ===
                    logger.info("トマト未検出: 探索移動中 (cmd_velをパススルー)")                    
                    node.detect_tomato = False
                    # ★★★ 【仕様】detect_checkがFalse(None)なら、cmd_velをcmd_vel_crにパブリッシュ ★★★
                    # コールバックで更新された最新の cmd_vel をそのまま流す
                    start_time = time.time()
                    duration = 1.5

                    while time.time() - start_time < duration:
                        node.pub_cmd_vel_cr.publish(node.latest_cmd_vel)
                        pass
                    

            else:
                logger.error("ビジョンノードからの応答がありません。")
                # 安全のため停止
                node.detect_tomato = True
                node.pub_cmd_vel_cr.publish(Twist())
                time.sleep(1.0)
                
    except KeyboardInterrupt:
        logger.info("Ctrl+Cが押されました。プログラムを終了します。")
    finally:
        logger.info("終了処理中... アームを初期化し停止します。")
        # node.arm_and_ee_send_request_init() # エラーになることがあるためコメントアウト推奨
        # 最後に安全のため停止コマンドを送信
        node.pub_cmd_vel_cr.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()