#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_services_default
from geometry_msgs.msg import Twist, PoseStamped, PoseWithCovarianceStamped
from std_msgs.msg import Bool  # ★ Bool型のインポートを追加
from toms_msg.srv import SuctionCommand, ArmService, VisionService, RailService

from playsound import playsound
import time
import yaml
import sys

def load_yaml(file_path):
    try:
        with open(file_path, "r") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"YAMLファイルの解析エラー: {e}")

class HarvestMissionControllerNode(Node):
    def __init__(self):
        super().__init__('harvest_mission_controller') # ノード名を変更

        self.detect_tomato = False

        # === 往復移動用の変数を初期化 ===
        self.pose_a = None  
        self.pose_b = None  
        self.next_target = 'B' 
        self.is_patrolling = False 

        # === 各種サービスクライアント設定 ===
        self.vision_client = self.create_client(VisionService, "vision_service", qos_profile=qos_profile_services_default)
        while not self.vision_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('ビジョンサーバ待機中...')
        self.vision_request = VisionService.Request()

        self.arm_client = self.create_client(ArmService, "arm_service", qos_profile=qos_profile_services_default)
        while not self.arm_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('アームサーバ待機中...')
        self.arm_request = ArmService.Request()

        self.ee_client = self.create_client(SuctionCommand, 'command', qos_profile=qos_profile_services_default)
        while not self.ee_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('EEサーバ待機中...')
        self.ee_request = SuctionCommand.Request()

        # === Pub/Sub 設定 ===
        # 停止判定のためにcmd_velは監視のみ行う
        self.sub_cmd_vel = self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, 10)
        self.latest_cmd_vel = Twist() 

        # ★ 変更箇所: 足回り制御ノードへ収穫モード(True/False)をパブリッシュする
        self.pub_harvest_mode = self.create_publisher(Bool, 'harvest_mode', 10)

        # Nav2/Rviz連携用
        self.sub_goal_pose = self.create_subscription(PoseStamped, 'rviz_goal_pose', self.callback_rviz_goal, 10)
        self.sub_initial_pose = self.create_subscription(PoseWithCovarianceStamped, 'initialpose', self.callback_rviz_initial, 10)
        self.pub_nav_goal = self.create_publisher(PoseStamped, 'goal_pose', 10)

        # 初期化実行
        self.arm_and_ee_send_request_init()

    # ★ 追加: 足回り制御ノードへ指示を出すヘルパー関数
    def set_harvest_mode(self, mode: bool):
        msg = Bool()
        msg.data = mode
        self.pub_harvest_mode.publish(msg)
        self.detect_tomato = mode

    def callback_rviz_initial(self, msg):
        self.get_logger().info("【地点A】初期位置を登録しました。")
        goal_msg = PoseStamped()
        goal_msg.header = msg.header
        goal_msg.pose = msg.pose.pose 
        self.pose_a = goal_msg
        self.check_start_patrol()

    def callback_rviz_goal(self, msg):
        self.get_logger().info("【地点B】目的地を登録しました。")
        self.pose_b = msg
        self.next_target = 'B'
        self.check_start_patrol()

    # === リクエスト関数群 (変更なし) ===
    def vision_send_request_check(self):
        self.vision_request.task = "detect_check"
        self.vision_request.direction = "f" 
        self.vision_future = self.vision_client.call_async(self.vision_request)
        rclpy.spin_until_future_complete(self, self.vision_future)
        return self.vision_future.result()

    def vision_send_request_tompos(self):
        self.vision_request.task = "req_tomato_pose"
        self.vision_request.direction = "f"
        self.vision_future = self.vision_client.call_async(self.vision_request)
        rclpy.spin_until_future_complete(self, self.vision_future)
        return self.vision_future.result()

    def arm_and_ee_send_request_init(self):
        self.arm_request.task = "init_arm"
        self.ee_request.command = '0' 
        self.arm_future = self.arm_client.call_async(self.arm_request)
        self.ee_future = self.ee_client.call_async(self.ee_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        rclpy.spin_until_future_complete(self, self.ee_future)
        self.ee_send_request('3') 
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

    def ee_send_request(self, mode):
        self.ee_request.command = mode
        self.ee_future = self.ee_client.call_async(self.ee_request)
        rclpy.spin_until_future_complete(self, self.ee_future)
        return self.ee_future.result()

    # === メイン制御用関数 ===
    def check_start_patrol(self):
        if self.pose_a is not None and self.pose_b is not None:
            if not self.is_patrolling:
                self.get_logger().info(">>> 地点AとBが設定されました。往復移動を開始します！")
                self.is_patrolling = True

    def cmd_vel_callback(self, msg):
        self.latest_cmd_vel = msg

    def check_and_move_next(self):
        is_stopped = (abs(self.latest_cmd_vel.linear.x) < 0.001 and 
                      abs(self.latest_cmd_vel.angular.z) < 0.001)

        if not self.detect_tomato and is_stopped and self.is_patrolling:       
            self.publish_next_goal()
            time.sleep(2.0) 

    def publish_next_goal(self):
        if self.next_target == 'B':
            self.get_logger().info(f"移動開始 >>> 地点B (GoalPose) へ向かいます")
            self.pub_nav_goal.publish(self.pose_b)
            self.next_target = 'A'
        elif self.next_target == 'A':
            self.get_logger().info(f"移動開始 >>> 地点A (初期位置) へ戻ります")
            self.pub_nav_goal.publish(self.pose_a)
            self.next_target = 'B'

def main(args=None):
    rclpy.init(args=args)
    node = HarvestMissionControllerNode()
    logger = node.get_logger()

    try:
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
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
            vision_response = node.vision_send_request_check()

            # 動作状況チェック
            node.check_and_move_next()

            if vision_response is not None:
                if vision_response.detect_check:
                    # === トマトが見つかった場合 (停止して収穫) ===
                    logger.info("トマト検出: 足回りを停止して収穫を開始します。")
                    
                    # ★ 変更箇所: 収穫モードをTrueにして足回り制御ノードに停止させる
                    node.set_harvest_mode(True)

                    if VOICE:
                        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/トマトを見つけたのだ.wav")

                    target = vision_response.target_pos.tomato_data[0]
                    arm_response = node.arm_send_request_home(target)
                    logger.info(f'アーム認識位置 到達: {arm_response}')
                    pre_arm_hight = arm_response.tom_hight

                    vision_response = node.vision_send_request_tompos()
                    targets = vision_response.target_pos.tomato_data
                    
                    if not targets:
                        logger.warn("手先カメラでターゲットを見失いました。探索に戻ります。")
                        node.arm_and_ee_send_request_init()
                        logger.info("次に行きます。")
                        
                        # ★ 変更箇所: 探索モードに戻して1.5秒待機
                        node.set_harvest_mode(False)
                        start_time = time.time()
                        while time.time() - start_time < 1.0:
                            # 待機中もコールバック処理(cmd_velの更新など)を回す
                            rclpy.spin_once(node, timeout_sec=0.1)
                        continue

                    if VOICE:
                        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/熟したトマトを収穫するのだ.wav")

                    for i, target in enumerate(targets):
                        logger.info(f"{i+1}個目のトマトへ移動します。")
                        arm_response = node.arm_send_request_target(target, pre_arm_hight)

                        if arm_response.task_comp:
                            time.sleep(0.5)
                            logger.info("吸引開始 (mode 1)")
                            ee_response = node.ee_send_request('1')
                            if ee_response.answer not in ['1', '666']:
                                logger.warn("吸引失敗。次のターゲットへ。")
                                continue 

                            logger.info("顎閉じ (mode 2)")
                            ee_response = node.ee_send_request('2')
                            if ee_response.answer not in ['2', '666']:
                                logger.warn("顎閉じ失敗。吸引を停止します。")
                                node.ee_send_request('0')
                                continue

                            logger.info("収穫ボックスへ移動")
                            node.arm_send_request_box()
                            logger.info("顎開き (mode 3)")
                            node.ee_send_request('3')
                            logger.info("吸引停止 (mode 0)")
                            node.ee_send_request('0')
                            logger.info(f"{i+1}個目のトマト収穫完了。")

                        else:
                            logger.error("アームのターゲット移動に失敗しました。")
                            node.ee_send_request('0')
                            node.ee_send_request('3')
                            time.sleep(1)

                    logger.info("このエリアの収穫が完了。アームを初期位置に戻します。")
                    node.arm_and_ee_send_request_init()
                    logger.info("このエリアの収穫が完了。次に行きます。")
                    
                    # ★ 変更箇所: 探索モードに戻して1.5秒待機
                    node.set_harvest_mode(False)
                    start_time = time.time()
                    while time.time() - start_time < 1.0:
                        rclpy.spin_once(node, timeout_sec=0.1)

                else:
                    # === トマトが見つからなかった場合 ===
                    logger.info("トマト未検出: 探索移動中")                    
                    
                    # ★ 変更箇所: 探索モードにして1.5秒待機
                    node.set_harvest_mode(False)
                    start_time = time.time()
                    while time.time() - start_time < 1.0:
                        rclpy.spin_once(node, timeout_sec=0.1)

            else:
                logger.error("ビジョンノードからの応答がありません。")
                node.set_harvest_mode(True) # 異常時は安全のため停止
                time.sleep(1.0)

    except KeyboardInterrupt:
        logger.info("Ctrl+Cが押されました。プログラムを終了します。")
    finally:
        logger.info("終了処理中... アームを初期化し停止します。")
        node.set_harvest_mode(True)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()