import rclpy
from rclpy.node import Node
import smach

from playsound import playsound
from std_msgs.msg import Bool
from std_msgs.msg import String
import time
import numpy as np

from toms_msg.srv import CartService

from toms_msg.msg import TomatoPos,TomatoData
from toms_msg.srv import VisionService
from toms_msg.srv import ArmService, EndEffectorService
from toms_msg.srv import SuctionCommand

# アームとカメラの位置補正パラメータ
setup_x = 250
setup_y = -234
setup_z = 145.0
global MOVE_VAL
MOVE_VAL = 0.0

# harvestタスクのステートマシーンを実行するノードを定義
class HarvestTaskCartState(Node):
    def __init__(self):
        # ノード名をharvest_task_cart_stateとして登録
        super().__init__('harvest_task_cart_state')

    def execute(self):
        # ステートマシーンを作成
        sm = smach.StateMachine(outcomes = ['succeeded'])

        # コンテナに状態を追加
        with sm: # 状態同士のつながりを定義
            smach.StateMachine.add(
                'SETUP',
                Setup(self),
                {'next': 'ANALYZE'})

            smach.StateMachine.add(
                'ANALYZE',
                Analyze(self),
                {'succeeded': 'HARVEST', 'next': 'MOVE'})

            smach.StateMachine.add(
                'HARVEST',
                Harvest(self),
                {'next': 'ANALYZE','exit': 'MOVE'})
            
            smach.StateMachine.add(
                'MOVE',
                Move(self),
                {'next': 'ANALYZE','exit': 'succeeded'}
                )


        # Smachプランを実行
        sm.execute()

def main():
    rclpy.init()
    # ステートマシーンのノードを初期化
    node = HarvestTaskCartState()
    # ステートマシーン実行
    node.execute()
    
    

############################################ステート############################################################
# セットアップ
class Setup(smach.State):
    """
    アームを初期位置に移動させる。
    """
    def __init__(self, node):
        smach.State.__init__(self, outcomes = ['next'])
        
        # Nodeを作成
        self.node = node
        # ロガーの定義
        self.logger = self.node.get_logger()
        # アームのサービスにおけるクライアントを作成
        self.setup_arm_client = self.node.create_client(ArmService,"arm_service_d435")
        while not self.setup_arm_client.wait_for_service(timeout_sec=10.0):
            self.logger().info("アームサーバー待機中...")
        self.setup_arm_request =  ArmService.Request()
        self.setup_arm_result = None
        
        # エンドエフェクタのサービスにおけるクライアントを作成
        self.setup_suction_client = self.node.create_client(SuctionCommand, 'command')
        while not self.setup_suction_client.wait_for_service(timeout_sec=10.0):
            self.logger().info("サービスは利用できません．待機中...")
        # リクエストのインスタンスを生成
        self.setup_suction_request = SuctionCommand.Request()
        self.setup_suction_result = None
    
    def __del__(self):
        self.logger().info("セットアップのデストラクタを実行しました")
    
    # アームへのリクエスト
    def arm_send_request_init(self):
        self.setup_arm_request.task = "init_arm"
        # サービスのリクエスト
        self.setup_arm_future = self.setup_arm_client.call_async(self.setup_arm_request)
        # サービスを動作させる処理
        rclpy.spin_until_future_complete(self.node, self.setup_arm_future)
        return self.setup_arm_future.result()
    
    # エンドエフェクタへのリクエスト
    def suction_send_request_init(self):
        self.setup_suction_request.command = "0"
        # サービスのリクエスト
        self.setup_suction_future = self.setup_suction_client.call_async(self.setup_suction_request)
        # サービスを動作させる処理
        rclpy.spin_until_future_complete(self.node, self.setup_suction_future)
        return self.setup_suction_future.result()

    def execute(self, userdata):
        self.logger.info("Setupステート")
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/セットアップステート.wav")
        # アームとエンドエフェクタを初期位置へ移動
        self.setup_arm_future = self.arm_send_request_init()
        self.logger.info(f"setup_arm_future : {self.setup_arm_future}")
        self.setup_suction_future = self.suction_send_request_init()
        self.logger.info(f'setup_suction_future : {self.setup_suction_future}')
        return 'next'
    
# アナライズ(画像処理)の状態
class Analyze(smach.State):
    def __init__(self, node):
        # アナライズの状態における結果と他の状態に値を渡す際の名前を事前に定義
        smach.State.__init__(
            self,
            output_keys = ['target_object_pos'],
            outcomes = ['succeeded', 'next'])
        # Nodeを作成
        self.node = node
        # ロガーの定義
        self.logger = self.node.get_logger()
        # サービスにおけるクライアントを作成
        self.vision_client = self.node.create_client(VisionService,"vision_service_d435")
        while not self.vision_client.wait_for_service(timeout_sec=10.0):
            self.logger().info("サービスは利用できません．待機中...")
        self.vision_request =  VisionService.Request()
        self.vision_result = None
        
        # アームのサービスにおけるクライアントを作成
        self.analyze_arm_client = self.node.create_client(ArmService,"arm_service_d435")
        while not self.analyze_arm_client.wait_for_service(timeout_sec=10.0):
            self.logger().info("アームサーバー待機中...")
        self.analyze_arm_request =  ArmService.Request()
        self.analyze_arm_result = None
        
    def __del__(self):
        self.logger().info("アナライズのデストラクタを実行しました")
        
    def vision_send_request_check(self):
        self.vision_request.task = "detect_check"
        self.vision_request.direction = "f"
        self.vision_future = self.vision_client.call_async(self.vision_request)
        rclpy.spin_until_future_complete(self.node, self.vision_future)
        return self.vision_future.result()

    def vision_send_request_pos(self):
        self.vision_request.task = "req_tomato_pose"
        self.vision_request.direction = "f"
        self.future = self.vision_client.call_async(self.vision_request)
        rclpy.spin_until_future_complete(self.node, self.future)
        return self.future.result()
    
    def arm_send_request_home(self):
        self.analyze_arm_request.task = "home"
        self.analyze_arm_future = self.analyze_arm_client.call_async(self.analyze_arm_request)
        rclpy.spin_until_future_complete(self.node, self.analyze_arm_future)
        return self.analyze_arm_future.result()
    
    def execute(self,userdata):
        self.logger.info("ANALYZEステートを開始します")
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/アナライズステート.wav")
        # アームをトマトが認識可能な高さに移動
        self.analyze_arm_future = self.arm_send_request_home()
        self.logger.info(f'analyze_arm_future : {self.analyze_arm_future}')
        # トマトの検出をリクエスト
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/トマトを見つけるのだ.wav")
        vision_response = self.vision_send_request_pos()
        if vision_response is not None:
            if vision_response.detect_check:
                self.logger.info("トマトを見つけたのだ")
                playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/トマトを見つけたのだ.wav")
                # トマトの座標をリクエスト
                self.logger.info("熟したトマトを見つけるのだ")
                playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/熟したトマトを見つけるのだ.wav")
                vision_response_pos = self.vision_send_request_pos()
                userdata.target_object_pos = vision_response_pos.target_pos
                return 'succeeded'
            else:
                self.logger.info("熟したトマトはないのだ")
                playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/熟したトマトはないのだ.wav")
                return 'next'
                    
        else:
            self.logger.info("トマトが見つからないのだ")
            playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/トマトが見つからないのだ.wav")
            return 'next'
        
class Harvest(smach.State):
    def __init__(self, node):
        smach.State.__init__(self,input_keys=['target_object_pos'],outcomes=['next', 'exit'])
        # Nodeを作成
        self.node = node
        self.logger = self.node.get_logger() #[*] ロガーを定義します．
        
        # アームのクライアントを作成
        self.arm_client = self.node.create_client(ArmService,"arm_service_d435")
        while not self.arm_client.wait_for_service(timeout_sec=5.0):
            self.logger.info("アームサーバー待機中...")
        self.arm_req =  ArmService.Request()
        self.arm_result = None
        
        # エンドエフェクタのクライアントを作成
        self.suction_client = self.node.create_client(SuctionCommand,"command")
        while not self.suction_client.wait_for_service(timeout_sec=5.0):
            self.logger.info("EEサーバー待機中...")
        self.suction_req = SuctionCommand.Request()
        self.suction_result = None
        
    def __del__(self):
        self.logger().info("ハーベストのデストラクタを実行しました")
        
    def arm_send_request_init(self):
        self.arm_req.task = "init_arm"
        self.arm_future = self.arm_client.call_async(self.arm_req)
        rclpy.spin_until_future_complete(self.node, self.arm_future)
        return self.arm_future.result()

    def arm_send_request_move(self, coordinates):
        self.arm_req.task = "move_to_target"
        # ユーザー入力
        self.arm_req.target.x = int(coordinates[0])
        self.arm_req.target.y = int(coordinates[1])
        self.arm_req.target.z = int(coordinates[2])
        self.arm_req.target.approach_direction = int(coordinates[3])
        self.arm_future = self.arm_client.call_async(self.arm_req)
        rclpy.spin_until_future_complete(self.node, self.arm_future)
        return self.arm_future.result()
    
    def arm_send_request_box(self):
        self.arm_req.task = "move_to_box"
        self.arm_future = self.arm_client.call_async(self.arm_req)
        rclpy.spin_until_future_complete(self.node, self.arm_future)
        return self.arm_future.result()
    
    def arm_send_request_home(self):
        self.arm_req.task = "home"
        self.arm_future = self.arm_client.call_async(self.arm_req)
        rclpy.spin_until_future_complete(self.node, self.arm_future)
        return self.arm_future.result()
    
    def suction_send_request(self, mode):
        self.suction_req.command = mode
        # サービスのリクエスト
        self.suction_future = self.suction_client.call_async(self.suction_req)
        # サービスを動作させる処理
        rclpy.spin_until_future_complete(self.node, self.suction_future)
        return self.suction_future.result()
    
    def execute(self,userdata):
        self.logger.info("Harvestステート")
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/ハーベストステート.wav")
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/熟したトマトを収穫するのだ.wav")
        # Analyzeステートからトマトの座標を受け取る
        targets = userdata.target_object_pos.tomato_data
        self.logger.info("ANALYZEステートからトマト座標を受け取りました")
        self.logger.info(f"トマト座標：{targets}")
        if not targets:
            return  'exit'
        for i, target in enumerate(targets):
            self.logger.info(f"{i+1}個目のトマトを収穫")
            self.logger.info(f"目標x：{target.x}")
            self.logger.info(f"目標y：{target.y}")
            self.logger.info(f"目標z：{target.z}")
            self.logger.info(f"目標侵入角度：{target.approach_direction}")
            
            #カメラ座標系からアーム座標系に座標変換
            x = float(target.x+(setup_x))
            y = float(target.z+(setup_y))
            z = float(-target.y+(setup_z))
            
            self.logger.info(f"変換後目標(x,y,z,α)：({x},{y},{z},{target.approach_direction})")
            coordinates =[x,y,z,target.approach_direction]
            arm_res = self.arm_send_request_move(coordinates)
            
            ##################エンドエフェクタによる収穫######################
            if arm_res.task_comp:
                mode = '1' # 吸引
                suction_response = self.suction_send_request(mode)
                time.sleep(3)
                if suction_response.answer == mode :
                    self.logger.info("吸引成功")
                else :
                    self.logger.info("吸引失敗")
                mode = '2' # 顎閉じる
                suction_response = self.suction_send_request(mode)
                time.sleep(3)
                if suction_response.answer == mode :
                    self.logger.info("顎閉じ成功")
                else :
                    self.logger.info("顎閉じ失敗")
                
                arm_res = self.arm_send_request_box()
                mode = '3' # 顎開く
                suction_response = self.suction_send_request(mode)
                time.sleep(3)
                if suction_response.answer == mode :
                    self.logger.info("顎開成功")
                else :
                    self.logger.info("顎開失敗")
                
                mode = '0' # 吸引停止
                suction_response = self.suction_send_request(mode)
                time.sleep(3)
                if suction_response.answer == mode :
                    self.logger.info("吸引停止成功")
                else :
                    self.logger.info("吸引停止失敗")
                
                time.sleep(0.5)
            
            else :
                mode = '0' # 吸引停止
                suction_response = self.suction_send_request(mode)
                time.sleep(0.5)
        
        arm_res = self.arm_send_request_home()
        time.sleep(3)
        return 'next'
    
class Move(smach.State):
    def __init__(self, node):
        smach.State.__init__(self, outcomes=['next', 'exit'])
        # Nodeを作成
        self.node = node
        # ロガーを定義
        self.logger = self.node.get_logger()

        # サービスにおけるクライアントを作成
        self.move_client = self.node.create_client(CartService, 'cart')
        while not self.move_client.wait_for_service(timeout_sec=2.0):
            self.logger.info("カートノードのサービスへの接続待ちです・・・")
        # リクエストのインスタンスを生成
        self.move_request = CartService.Request()
        self.move_result = None
    
    def move_send_request(self,move_x,pwm_value):
        self.move_request.move_value = move_x
        self.move_request.pwm_value = pwm_value
        self.move_future = self.move_client.call_async(self.move_request)
        # サービスを動作させる処理
        while rclpy.ok():
            rclpy.spin_once(self.node)
            if self.move_future.done():
                res = self.move_future.result()
                self.res2 = res.move_result
                self.logger.info(f"response = {res}")
                self.logger.info(f"response2 = {self.res2}")
                break
        if res:
            return True
        else:
            return False
    
    def execute(self,userdata):
        global MOVE_VAL
        self.logger.info("Moveステート")
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/ムーブステート.wav")
        x = int(200)
        pwm = int(80)
        goal_point = 1200.0
        self.logger.info(f"移動量：{x}mm")
        self.move_result = self.move_send_request(x,pwm)
        if self.move_result:
            MOVE_VAL = MOVE_VAL+float(self.res2)
            self.logger.info(f"{self.res2}mm移動しました.")
            if MOVE_VAL>=goal_point:
                self.logger.info("最終地点に到達しました")
                self.logger.info(f"走行距離：{MOVE_VAL}")
                self.logger.info("Cartステートを終了し、プログラムを終了します")
                return 'exit'
            self.logger.info("Cartステートを終了し、VISIONステートに移動します")
            return 'next'
        else:
            self.logger.infoa("Cartステートを終了し、プログラムを終了します")
            return 'exit'