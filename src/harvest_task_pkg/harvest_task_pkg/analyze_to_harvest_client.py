import rclpy
from rclpy.node import Node
from toms_msg.srv import SuctionCommand, ArmService, VisionService
from toms_msg.msg import TomatoPos,TomatoData

from playsound import playsound
import time
import numpy as np
import yaml

class AnalizeToHarvestNode(Node):
    def __init__(self):
        super().__init__('analyze2harvest_node')
        self.vision_client = self.create_client(VisionService,"vision_service")
        while not self.vision_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('ビジョンサーバ待機中...')
        self.vision_request =  VisionService.Request()
        
        self.arm_client = self.create_client(ArmService,"arm_service")
        while not self.arm_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('アームサーバ待機中...')
        self.arm_request =  ArmService.Request()
        
        self.ee_client = self.create_client(SuctionCommand, 'command')
        # playsound("/home/ylab/toms_ws/src/end_effector_pkg/end_effector_pkg/sound/サクションモジュールクライアントノードを起動したのだ.wav")
        while not self.ee_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('EEサーバ待機中...')
        # リクエストのインスタンスを生成
        self.ee_request = SuctionCommand.Request()
        
        self.arm_and_ee_send_request_init()
    
    # ビジョンノードにリクエスト送信＆レスポンス受信
    def vision_send_request_check(self):
        self.vision_request.task = "detect_check"
        self.vision_request.direction = "f"
        self.vision_future = self.vision_client.call_async(self.vision_request)
        #rclpy.spin_until_future_complete(node, self.vision_future)
        rclpy.spin_until_future_complete(self, self.vision_future)
        return self.vision_future.result()

    def vision_send_request_tompos(self):
        self.vision_request.task = "req_tomato_pose"
        self.vision_request.direction = "f"
        self.vision_future = self.vision_client.call_async(self.vision_request)
        #rclpy.spin_until_future_complete(node, self.future)
        rclpy.spin_until_future_complete(self, self.vision_future)
        return self.vision_future.result()

    # アームノードにリクエスト送信＆レスポンス受信
    def arm_and_ee_send_request_init(self):
        self.arm_request.task = "init_arm"
        self.ee_request.command = '0'
        self.arm_future = self.arm_client.call_async(self.arm_request)
        self.ee_future = self.ee_client.call_async(self.ee_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        rclpy.spin_until_future_complete(self, self.ee_future)
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
    
    def arm_send_request_box(self, target):
        self.arm_request.task = "move_to_box"
        self.arm_request.target.z = target.z - 20
        self.arm_future = self.arm_client.call_async(self.arm_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        return self.arm_future.result()
    
    def arm_send_request_home(self, init_h):
        self.arm_request.task = "home"
        self.arm_request.target.x = 0
        self.arm_request.target.y = 0
        self.arm_request.target.z = int(init_h)
        self.arm_request.target.approach_direction = 0
        self.arm_future = self.arm_client.call_async(self.arm_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        return self.arm_future.result()

    # EEノードにリクエスト送信＆レスポンス受信
    def ee_send_request(self, mode):
        self.ee_request.command = mode
        self.ee_future = self.ee_client.call_async(self.ee_request)
        rclpy.spin_until_future_complete(self, self.ee_future)
        return self.ee_future.result()
    

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

def main(args=None):
    rclpy.init(args=args)
    node = AnalizeToHarvestNode()
    logger = node.get_logger()
    
    # YAMLファイルの読み込み
    yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
    params = load_yaml(yaml_path)

    VOICE = params["ZUNDA_VOICE"]  # 必須キー: 存在しない場合 KeyError が発生
    if VOICE:
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/おいしそうなトマトを収穫するのだ.wav")
    
    EXPERIMENT_MODE = params["EXPERIMENT_MODE"]

    try:
        init_h = input('最初の高さは？ ▶ ')
        
        while rclpy.ok():
            if VOICE:
                playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/トマトを見つけたのだ.wav")
            
            # アームを指定した高さにあげる
            arm_response = node.arm_send_request_home(init_h)
            logger.info(f'arm_res: {arm_response}')
            pre_arm_hight = arm_response.tom_hight
            
            # 手先カメラで認識
            vision_response = node.vision_send_request_tompos()
            targets = vision_response.target_pos.tomato_data
            if VOICE:
                playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/熟したトマトを収穫するのだ.wav")
            
            for i, target in enumerate(targets):
                arm_response = node.arm_send_request_target(target, pre_arm_hight)
                print(f"arm_response.task_comp: {arm_response.task_comp}")
                if arm_response.task_comp :
                    mode = '1' # 吸引
                    ee_response = node.ee_send_request(mode)
                    while 1:
                        if ee_response.answer == mode :
                            print('吸引成功')
                            break
                        elif ee_response.answer == '666' :
                            print('タイムアウト ▶ 成功とします')
                            break
                        else :
                            print('吸引失敗')
                            continue
                    
                    mode = '2' # 顎閉じる
                    ee_response = node.ee_send_request(mode)
                    while 1:
                        if ee_response.answer == mode :
                            print('顎閉じ成功')
                            break
                        elif ee_response.answer == '666' :
                            print('タイムアウト ▶ 成功とします')
                            break
                        else :
                            # トライしなおす？
                            print('顎閉じ失敗')
                            continue
                    
                    arm_response = node.arm_send_request_box(target)
                    mode = '3' # 顎開く
                    ee_response = node.ee_send_request(mode)
                    while 1:
                        if ee_response.answer == mode :
                            print('顎開き成功')
                            break
                        elif ee_response.answer == '666' :
                            print('タイムアウト ▶ 成功とします')
                            break
                        else :
                            print('顎開き失敗')
                            continue
                    
                    mode = '0' # 吸引停止
                    ee_response = node.ee_send_request(mode)
                    while 1:
                        if ee_response.answer == mode :
                            print('吸引停止成功')
                            break
                        elif ee_response.answer == '666' :
                            print('タイムアウト ▶ 成功とします')
                            break
                        else :
                            print('吸引停止失敗')
                            continue
                
                else :
                    print("収穫動作に失敗しました。。。")
                    time.sleep(1)
            arm_response = node.arm_and_ee_send_request_init()

    except KeyboardInterrupt:
        print("\nCtrl+C has been entered")
    finally:
        node.destroy_node()