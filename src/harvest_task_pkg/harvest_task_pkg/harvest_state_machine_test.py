#!/usr/bin/env python
import rclpy
from rclpy.node import Node
import smach

from std_msgs.msg import Bool
from std_msgs.msg import String
import time
import smach_ros
import numpy as np
import yaml
from std_msgs.msg import Int32

import sys
sys.path.append("/home/ylab/hibikino_toms_ws/src/behavior_planner/behavior_planner")

import time
from toms_msg.srv import CrawlerService, RailService, VisionService, ArmService ,SuctionCommand
from toms_msg.msg import TomatoPos,TomatoData
from playsound import playsound

class Setup(smach.State):
    def __init__(self,node):
        smach.State.__init__(self, outcomes=['setup_done'])
        self.node = node
        self.logger = self.node.get_logger()
        # アームのクライアントを作成
        self.setup_arm_client = self.node.create_client(ArmService,"arm_service")
        while not self.setup_arm_client.wait_for_service(timeout_sec=5.0):
            self.logger.info('アームサーバー待機中...')
        self.setup_arm_request =  ArmService.Request()
        self.setup_arm_result = None
    
        # エンドエフェクタのクライアントを作成
        self.setup_ee_client = self.node.create_client(SuctionCommand, "command")
        while not self.setup_ee_client.wait_for_service(timeout_sec=1.0):
            self.logger.info('エンドエフェクタサーバー待機中...')
        self.setup_ee_request =  SuctionCommand.Request()
        self.setup_ee_result = None
    
    def __del__(self):
        self.logger.info("デスストラクタを実行")
    
    def arm_send_request_init(self):
        self.setup_arm_request.task = "init_arm"
        # サービスのリクエスト
        self.setup_arm_future = self.setup_arm_client.call_async(self.setup_arm_request)
        # サービスを動作させる処理
        rclpy.spin_until_future_complete(self.node, self.setup_arm_future)
        return self.setup_arm_future.result()

    def ee_send_request_init(self):
        self.setup_ee_request.command = "0"
        # サービスのリクエスト
        self.setup_ee_future = self.setup_ee_client.call_async(self.setup_ee_request)
        # サービスを動作させる処理
        rclpy.spin_until_future_complete(self.node, self.setup_ee_future)
        return self.setup_ee_future.result()

    def execute(self,userdata):
        self.logger.info('Setupステート')
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/セットアップステート.wav")
        # アームとエンドエフェクタを初期位置へ移動
        self.setup_arm_future = self.arm_send_request_init()
        self.logger.info(f'setup_arm_future : {self.setup_arm_future}')
        # self.setup_ee_future = self.ee_send_request_init()
        # self.logger.info(f'setup_ee_future : {self.setup_ee_future}')
        return 'setup_done'

class Move(smach.State):
    def __init__(self, node):
        smach.State.__init__(self, 
                                outcomes=['analyze_mode', 'continue_moving', 'fin_moving'], 
                                input_keys=['target_out'],
                                output_keys=['target_out'])  # `target_out`を出力
        self.node = node
        self.logger = self.node.get_logger()
        
        self.total_pulse = 0
        self.topic_data = None
        self.subscription = None
        
        # YAMLファイルの読み込み
        yaml_path='/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        params = self.load_yaml(yaml_path)
        # 走行タイプの設定
        self.CART_TYPE = params["CART_TYPE"]
        
        # パラメータの設定
        if self.CART_TYPE == "crawler":
            cart_params = params["crawler_params"]
        elif self.CART_TYPE == "rail":
            cart_params = params["rail_params"]
            
        self.CURRENT_DIR = cart_params["INIT_DIR"]
        distance_movement = cart_params["DEFAULT_DISTANCE_MOVEMENT"]
        distance_limit_upper = cart_params["DISTANCE_LIMIT_UPPER"]
        self.PULSE_LIMIT_LOWER = cart_params["PULSE_LIMIT_LOWER"]
        if self.CART_TYPE == "crawler":
            self.DEF_PULSE_MOVEMENT =  (distance_movement * 10000)/ 610 
            self.PULSE_LIMIT_UPPER =  (distance_limit_upper * 10000)/ 610 # 移動指令令で使用するパルス量
        else :
            self.DEF_PULSE_MOVEMENT =  (distance_movement * 450)/(50 * 3.14)
            self.PULSE_LIMIT_UPPER =  (distance_limit_upper * 450)/(50 * 3.14)
        
        # カートのクライアントを作成 ※クローラ走行かレール走行かで立ち上げるクライアントを切り替え
        if self.CART_TYPE == "crawler":
            self.cart_client = self.node.create_client(CrawlerService,"crawler_control")
            while not self.cart_client.wait_for_service(timeout_sec=1.0):
                self.logger.info('カートサーバー待機中...')
            self.cart_request = CrawlerService.Request()
        else:
            self.cart_client = self.node.create_client(RailService,"rail_control")
            while not self.cart_client.wait_for_service(timeout_sec=1.0):
                self.logger.info('カートサーバー待機中...')
            self.cart_request = RailService.Request()
        self.cart_request.req_dir = ""
        
        self.vision_client = self.node.create_client(VisionService,"vision_service")
        while not self.vision_client.wait_for_service(timeout_sec=1.0):
            self.logger.info('ビジョンサーバー待機中...')
        self.vision_request =  VisionService.Request()
        self.vision_result = None
        
        # サブスクライバーの作成
        # self.subscription = self.node.create_subscription(Int32, 'crawler_pulse', self.topic_callback, 10)

    def __del__(self):
        self.logger.info("デスストラクタを実行")
        
    @staticmethod
    def load_yaml(file_path):
        """YAMLファイルを読み込むヘルパー関数"""
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"YAMLファイルの解析エラー: {e}")

    def crawler_send_request(self, direction):
        if direction == "forward":
            self.cart_request.req_dir = "f"
        else :
            self.cart_request.req_dir = "b"
        # サービスのリクエスト
        self.future = self.cart_client.call_async(self.cart_request)
        rclpy.spin_until_future_complete(self.node, self.future)
        return self.future.result()

    def rail_send_request(self, direction):
        if direction == "forward":
            self.cart_request.req_dir = "f"
        else :
            self.cart_request.req_dir = "b"
        # サービスのリクエスト
        self.future = self.cart_client.call_async(self.cart_request)
        rclpy.spin_until_future_complete(self.node, self.future)
        return self.future.result()

    def vision_send_request_check(self, direction):
        self.vision_request.task = "detect_check"
        self.vision_request.direction = direction
        # サービスのリクエスト
        self.vision_future = self.vision_client.call_async(self.vision_request)
        rclpy.spin_until_future_complete(self.node, self.vision_future)
        return self.vision_future.result()

    def execute(self,userdata):
        self.logger.info('Moveステート')
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/ムーブステート.wav")
        # time.sleep(2)
        
        direction = "f"
        vision_response = self.vision_send_request_check(direction)
        if vision_response is not None:
            if vision_response.detect_check:
                userdata.target_out = vision_response.target_pos
                # self.logger.info(f"ユーザーデータのtarget_out: {userdata.target_out}")
                state = 'analyze_mode'
                # state = 'continue_moving' # デバッグ用
            else :
                userdata.target_out = 0
                state = 'continue_moving'
        else:
            print('e')
            userdata.target_out = 0
            state = 'continue_moving'
            
        self.logger.info(f'next: {state}')
        
        print(f"Analyzeに送るデータ: {userdata.target_out}")
        return state

class Analyze(smach.State):
    def __init__(self, node):
        smach.State.__init__(self, 
                                outcomes=['task_comp', 'continue_moving'], 
                                input_keys=['target_out'],  # `Move`からデータを受け取る
                                output_keys=['target_out'])  # 処理結果を`Harvest`に渡す
        self.node = node
        self.logger = self.node.get_logger()
        
        # アームのクライアントを作成
        self.arm_client = self.node.create_client(ArmService,"arm_service")
        while not self.arm_client.wait_for_service(timeout_sec=1.0):
            self.logger.info('ビジョンサーバー待機中...')
        self.arm_request =  ArmService.Request()
        
        # ビジョンのクライアントを作成
        self.vision_client = self.node.create_client(VisionService,"vision_service")
        while not self.vision_client.wait_for_service(timeout_sec=1.0):
            self.logger.info('ビジョンサーバー待機中...')
        self.vision_request =  VisionService.Request()
        self.vision_result = None

    def __del__(self):
        self.logger.info("デスストラクタを実行")
    
    def arm_send_request_home(self, target):
        self.arm_request.task = "home"
        self.arm_request.target.x = target.x
        self.arm_request.target.y = target.y
        self.arm_request.target.z = target.z
        self.arm_request.target.approach_direction = target.approach_direction
        print('アームにクエストを送信')
        # サービスのリクエスト
        self.future = self.arm_client.call_async(self.arm_request)
        rclpy.spin_until_future_complete(self.node, self.future)
        return self.future.result()

    def vision_send_request_tompos(self):
        self.vision_request.task = "req_tomato_pose"
        print('リクエストした')
        # サービスのリクエスト
        self.future = self.vision_client.call_async(self.vision_request)
        rclpy.spin_until_future_complete(self.node, self.future)
        return self.future.result()

    def execute(self,userdata):
        self.logger.info('Analyzeステート')
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/アナライズステート.wav")
        
        self.logger.info(f"Analyzeが受け取ったデータ: {userdata.target_out}")

        state = 'task_comp'
        self.logger.info(f'next: {state}')
        return state

class Harvest(smach.State):
    def __init__(self, node):
        smach.State.__init__(self, 
                                outcomes=['continue_moving', 'continue_harvest'], 
                                input_keys=['target_out'])  # `Analyze`からデータを受け取る
        self.node = node
        self.logger = self.node.get_logger()

    def __del__(self):
        self.logger.info("デスストラクタを実行")

    def execute(self,userdata):
        self.logger.info('Harvestステート')
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/ハーベストステート.wav")
        
        self.logger.info(f"Harvetsが受け取ったデータ: {userdata.target_out}")
        self.logger.info("Moveステートに戻ります。\n\n")
        
        state = 'continue_moving'
        return state

# ステートマシンを実行するノードを定義
class HarvestStateMashine(Node):
    def __init__(self):
        super().__init__('harvest_state_machine')
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/ステートマシンを起動したのだ.wav")
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/おいしそうなトマトを収穫するのだ.wav")

    def execute(self):
        # ステートマシンを作成
        sm = smach.StateMachine(outcomes = ['END'])
        sm.userdata.target_pose = None

        with sm :
            smach.StateMachine.add('SETUP', Setup(self), 
                            transitions={'setup_done': 'MOVE'}
                                        )
            smach.StateMachine.add('MOVE', Move(self), 
                                    transitions={'analyze_mode': 'ANALYZE',
                                        'continue_moving': 'MOVE',
                                        'fin_moving': 'END'},
                                    remapping={'target_out': 'target_pose'}
                                        )
            smach.StateMachine.add('ANALYZE', Analyze(self), 
                                    transitions={'task_comp': 'HARVEST',
                                        'continue_moving': 'MOVE'},
                                    remapping={'target_in':'target_pose', 
                                        'target_out':'target_pose'}
                                        )
            smach.StateMachine.add('HARVEST', Harvest(self), 
                                    transitions={'continue_moving': 'MOVE',
                                        'continue_harvest': 'HARVEST'},
                                    remapping={'target_out': 'target_pose'})
        sm.execute()
        
def main():
    rclpy.init()
    node = HarvestStateMashine()
    node.execute()

if __name__ == '__main__':
    main()
