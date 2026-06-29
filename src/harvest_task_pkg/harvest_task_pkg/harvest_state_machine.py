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
import time

import sys
sys.path.append("/home/ylab/hibikino_toms_ws/src/behavior_planner/behavior_planner")

from toms_msg.srv import CrawlerService, RailService, VisionService, ArmService ,SuctionCommand
from toms_msg.msg import TomatoPos,TomatoData
from playsound import playsound

'''
・実行コマンド

立ち上げるサーバー
・ros2 run arm_controller_pkg arm_controller
・ros2 run end_effector_pkg suction_module_service_node
・ros2 run vision_pkg vision_service_node
・ros2 run cart_controller_pkg crawler_service_node または ros2 run cart_controller_pkg rail_service_node

ステートマシン
・ros2 run harvest_task_pkg harvest_state_machine
'''


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
        while not self.setup_ee_client.wait_for_service(timeout_sec=5.0):
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
        self.setup_ee_future = self.ee_send_request_init()
        self.logger.info(f'setup_ee_future : {self.setup_ee_future}')
        return 'setup_done'
    
class Move(smach.State):
    def __init__(self, node):
        smach.State.__init__(self, 
                                outcomes=['analyze_mode', 'continue_moving', 'fin_moving'], 
                                input_keys=['tomato_h_pos'],
                                output_keys=['tomato_h_pos'])  # `target_out`を出力
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
            while not self.cart_client.wait_for_service(timeout_sec=5.0):
                self.logger.info('カートサーバー待機中...')
            self.cart_request = CrawlerService.Request()
        else:
            self.cart_client = self.node.create_client(RailService,"rail_control")
            while not self.cart_client.wait_for_service(timeout_sec=5.0):
                self.logger.info('カートサーバー待機中...')
            self.cart_request = RailService.Request()
        self.cart_request.req_dir = ""
        
        # ビジョンのクライアントを作成
        self.vision_client = self.node.create_client(VisionService,"vision_service")
        while not self.vision_client.wait_for_service(timeout_sec=5.0):
            self.logger.info('ビジョンサーバー待機中...')
        self.vision_request =  VisionService.Request()
        self.vision_result = None
        

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
        
        self.topic_data = None  # 古いデータをリセット
        # mo
        # 次回移動後のカウントを予測
        if self.CURRENT_DIR == 'forward':
            next_pulse = self.total_pulse + self.DEF_PULSE_MOVEMENT
        else:
            next_pulse = self.total_pulse - self.DEF_PULSE_MOVEMENT

        # モード切替判定
        if next_pulse > self.PULSE_LIMIT_UPPER:
            self.CURRENT_DIR = 'back'
            self.logger.info(f"Mode switched to: back (next pulse {next_pulse} exceeds upper limit {self.PULSE_LIMIT_UPPER})")
        elif next_pulse < self.PULSE_LIMIT_LOWER:
            self.CURRENT_DIR = 'forward'
            self.logger.info(f"Mode switched to: forward (next pulse {next_pulse} below lower limit {self.PULSE_LIMIT_LOWER})")

        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/トマトを見つけるのだ.wav")
        if self.CART_TYPE == "crawler":
            response_crawler = self.crawler_send_request(self.CURRENT_DIR)
            pulse_data = response_crawler.pulse.data
            self.logger.info(f'response_cart_pulse: {pulse_data}')
        else :
            response_rail = self.rail_send_request(self.CURRENT_DIR)
            pulse_data = response_rail.pulse.data
            self.logger.info(f'response_cart: {pulse_data}')
        
        # 累積カウント値を更新
        self.total_pulse = pulse_data
        self.logger.info(f"Current total pulse count: {self.total_pulse}")
        
        # トマトがあるかチェック
        time.sleep(3)
        if self.CURRENT_DIR == 'forward':
            direction = 'f'
        elif self.CURRENT_DIR == 'back':
            direction = 'b'
        vision_response = self.vision_send_request_check(direction)
        if vision_response is not None:
            if vision_response.detect_check:
                # playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/トマトを見つけたのだ.wav")
                userdata.tomato_h_pos = vision_response.target_pos
                self.logger.info(f"userdata.tomato_h_pos: {userdata.tomato_h_pos}")
                state = 'analyze_mode'
            else :
                userdata.tomato_h_pos = [] # 元０
                state = 'continue_moving'
        else:
            print('e')
            userdata.tomato_h_pos = [] # 元０
            state = 'continue_moving'
        self.logger.info(f'next: {state}')
        
        print(f"userdata.tomato_h_pos: {userdata.tomato_h_pos}")
        return state


class Analyze(smach.State):
    def __init__(self, node):
        smach.State.__init__(self, 
                                outcomes=['task_comp', 'continue_moving'], 
                                input_keys=['tomato_h_pos', 'target_out'],  # `Move`からデータを受け取る
                                output_keys=['tomato_hight', 'target_out'])  # 処理結果を`Harvest`に渡す
        self.node = node
        self.logger = self.node.get_logger()
        
        # アームのクライアントを作成
        self.arm_client = self.node.create_client(ArmService,"arm_service")
        while not self.arm_client.wait_for_service(timeout_sec=5.0):
            self.logger.info('ビジョンサーバー待機中...')
        self.arm_request =  ArmService.Request()
        
        # ビジョンのクライアントを作成
        self.vision_client = self.node.create_client(VisionService,"vision_service")
        while not self.vision_client.wait_for_service(timeout_sec=5.0):
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
        # Z軸を動作させて、アームを、最初のトマトを認識できる高さに
        print(f"userdata.tomato_h_pos: {userdata.tomato_h_pos}")
        # data = userdata.tomato_h_pos.tomato_data
        # for d in data:
        #     print(f"d.tomato_data.x: {d.x}")
        #print(f"userdata.tomato_h_pos - x: {userdata.tomato_h_pos.tomato_data.x}")
        target_from_camera = userdata.tomato_h_pos.tomato_data
        # print(f"userdata.tomato_h_pos.X: {target_from_camera.x}")
        for i, target_out in enumerate(target_from_camera):
            arm_response = self.arm_send_request_home(target_out)
            self.logger.info(f'arm_res: {arm_response}')
            userdata.tomato_hight = arm_response.tom_hight
        # ↑Z軸はトマトの高さに合わせて動作”済み”
        
        # トマトの検出をリクエスト
        # playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/トマトを見つけるのだ.wav")
        vision_response = self.vision_send_request_tompos()
        if vision_response is not None:
            if vision_response.detect_check:
                self.logger.info('トマトを見つけたのだ')
                playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/トマトを見つけたのだ.wav")
                # トマトの座標をリクエスト
                self.logger.info('熟したトマトを見つけるのだ')
                # playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/熟したトマトを見つけるのだ.wav")
                vision_response_pos = self.vision_send_request_tompos()
                userdata.target_out = vision_response_pos.target_pos
                # for Target_pos in vision_response_pos:
                #     self.logger.info(f'res: {Target_pos}')
                #     userdata.target_out.x = Target_pos.tomato_data.x
                #     userdata.target_out.y = Target_pos.tomato_data.y
                #     userdata.target_out.z = Target_pos.tomato_datatomato_data.z
                #     userdata.target_out.approach_direction = Target_pos.tomato_data.approach_direction
                if userdata.target_out is not None:
                    # playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/熟したトマトの座標を取得するのだ.wav")
                    state = 'task_comp'
                    # state = 'continue_moving'
                    
                else:
                    self.logger.info('熟したトマトはないのだ')
                    playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/熟したトマトはないのだ.wav")
                    state = 'continue_moving'
                    
            else:
                self.logger.info('トマトが見つからないのだ')
                playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/トマトが見つからないのだ.wav")
                state = 'continue_moving'
                
        print(f" userdata.target_out: { userdata.target_out}")
        self.logger.info(f'next: {state}')
        return state

class Harvest(smach.State):
    def __init__(self, node):
        smach.State.__init__(self, 
                                outcomes=['continue_moving', 'continue_harvest'], 
                                input_keys=['target_out', 'tomato_hight'])
        self.node = node
        self.logger = self.node.get_logger()
        
        # アームのクライアントを作成
        self.arm_client = self.node.create_client(ArmService,"arm_service")
        while not self.arm_client.wait_for_service(timeout_sec=5.0):
            self.logger.info('アームサーバー待機中...')
        self.arm_req =  ArmService.Request()
        
        # EEのクライアントを作'
        self.ee_client = self.node.create_client(SuctionCommand,"command")
        while not self.ee_client.wait_for_service(timeout_sec=5.0):
            self.logger.info('EEサーバー待機中...')
        self.ee_req = SuctionCommand.Request()
        
    def __del__(self):
        self.logger.info("デスストラクタを実行")

    def arm_send_request_init(self):
        self.arm_req.task = "init_arm"
        self.future = self.arm_client.call_async(self.arm_req)
        rclpy.spin_until_future_complete(self.node, self.future)
        return self.future.result()

    # def arm_send_request_home(self):
    #     self.arm_req.task = "home"
    #     self.future = self.arm_client.call_async(self.arm_req)
    #     rclpy.spin_until_future_complete(self.node, self.future)
    #     return self.future.result()

    def arm_send_request_target(self, target, pre_h):
        self.arm_req.task = "move_to_target"
        for t in target:
            self.arm_req.target.x = t.x
            self.arm_req.target.y = t.y
            self.arm_req.target.z = t.z + pre_h
            self.arm_req.target.approach_direction = t.approach_direction
        self.future = self.arm_client.call_async(self.arm_req)
        rclpy.spin_until_future_complete(self.node, self.future)
        return self.future.result()

    def arm_send_request_box(self):
        self.arm_req.task = "move_to_box"
        self.future = self.arm_client.call_async(self.arm_req)
        rclpy.spin_until_future_complete(self.node, self.future)
        return self.future.result()

    def ee_send_request(self, mode):
        self.ee_req.command = mode
        # サービスのリクエスト
        self.future = self.ee_client.call_async(self.ee_req)
        # サービスを動作させる処理
        rclpy.spin_until_future_complete(self.node, self.future)
        return self.future.result()

    def execute(self,userdata):
        self.logger.info('Harvestステート')
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/ハーベストステート.wav")
        # playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/熟したトマトを収穫するのだ.wav")

        pre_arm_hight = userdata.tomato_hight.data
        if pre_arm_hight == None:
            pre_arm_hight = 0
        targets = userdata.target_out.tomato_data
        self.logger.info(f'targets: {targets}')
        for i, target in enumerate(targets):
            target_z = target.z
            self.logger.info(f'Arm response: {target_z}')
            Hight =  target_z + pre_arm_hight
            self.logger.info(f'Arm response: {Hight}')
            
            arm_response = self.arm_send_request_target(targets, pre_arm_hight)
            
            if arm_response.task_comp :
                mode = '1' # 吸引
                ee_response = self.ee_send_request(mode)
                while 1:
                    if ee_response.answer == mode :
                        print('吸引成功')
                        break
                    else :
                        print('吸引失敗')
                        continue
                
                mode = '2' # 顎閉じる
                ee_response = self.ee_send_request(mode)
                while 1:
                    if ee_response.answer == mode :
                        print('顎閉じ成功')
                        break
                    else :
                        # トライしなおす？
                        print('顎閉じ失敗')
                        continue
                
                arm_response = self.arm_send_request_box()
                mode = '3' # 顎開く
                ee_response = self.ee_send_request(mode)
                while 1:
                    if ee_response.answer == mode :
                        print('顎開き成功')
                        break
                    else :
                        print('顎開き失敗')
                        continue
                
                mode = '0' # 吸引停止
                ee_response = self.ee_send_request(mode)
                while 1:
                    if ee_response.answer == mode :
                        print('吸引停止成功')
                        break
                    else :
                        print('吸引停止失敗')
                        continue
                
                time.sleep(3)
            
            else :
                mode = '0' # 吸引停止
                ee_response = self.ee_send_request(mode)
                while 1:
                    if ee_response.answer == mode :
                        print('吸引停止成功')
                        break
                    else :
                        print('吸引停止失敗')
                        continue
                time.sleep(3)
        
        arm_response = self.arm_send_request_init()
        # 収穫ボックスに持っていく処理
        state = 'continue_moving'
        self.logger.info(f'next: {state}')
        return state

# ステートマシンを実行するノードを定義
class HarvestStateMashine(Node):
    def __init__(self):
        super().__init__('harvest_state_machine')
        # playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/ステートマシンを起動したのだ.wav")
        # playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/おいしそうなトマトを収穫するのだ.wav")

    def execute(self):
        # ステートマシンを作成
        sm = smach.StateMachine(outcomes = ['END'])
        sm.userdata.target_out = None
        sm.userdata.tomato_hight = None

        with sm :
            smach.StateMachine.add('SETUP', Setup(self), 
                            transitions={'setup_done': 'MOVE'}
                                        )
            smach.StateMachine.add('MOVE', Move(self), 
                                    transitions={'analyze_mode': 'ANALYZE',
                                        'continue_moving': 'MOVE',
                                        'fin_moving': 'END'},
                                    remapping={'target_out': 'target_pose',
                                        'tomato_h_pos': 'tomato_hight_pos'}
                                        )
            smach.StateMachine.add('ANALYZE', Analyze(self), 
                                    transitions={'task_comp': 'HARVEST',
                                        'continue_moving': 'MOVE'},
                                    remapping={'tomato_h_pos':'tomato_hight_pos', 
                                        'tomato_hight':'z_hight', 
                                        'target_out':'target_pose'}
                                        )
            smach.StateMachine.add('HARVEST', Harvest(self), 
                                    transitions={'continue_moving': 'MOVE',
                                        'continue_harvest': 'HARVEST'},
                                    remapping={'tomato_hight': 'z_hight',
                                        'target_out': 'target_pose'}
                                        )
        sm.execute()
        
def main():
    rclpy.init()
    node = HarvestStateMashine()
    node.execute()

if __name__ == '__main__':
    main()
