import rclpy
from rclpy.node import Node
# rclpy.qos から qos_profile_services_default をインポート
from rclpy.qos import qos_profile_services_default
from toms_msg.srv import SuctionCommand, ArmService, VisionService, DetectTomato, HarvestTomato, ResetArmEnd

from playsound import playsound
import time
import numpy as np
import yaml

from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup

class HarvestGatewayNode(Node):
    def __init__(self):
        super().__init__('harvest_gateway_node')

        cbg = ReentrantCallbackGroup()
        self.vision_client = self.create_client(
            VisionService,
            "vision_service",
            qos_profile = qos_profile_services_default, callback_group = cbg
        )
        while not self.vision_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("ビジョンサーバ待機中...")
        self.vision_request = VisionService.Request()

        self.arm_client = self.create_client(
            ArmService,
            "arm_service",
            qos_profile=qos_profile_services_default, callback_group = cbg)
        while not self.arm_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('アームサーバ待機中...')
        self.arm_request =  ArmService.Request()

        self.ee_client = self.create_client(
            SuctionCommand,
            'command',
            qos_profile=qos_profile_services_default, callback_group = cbg)
        # playsound("/home/ylab/toms_ws/src/end_effector_pkg/end_effector_pkg/sound/サクションモジュールクライアントノードを起動したのだ.wav")
        while not self.ee_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('EEサーバ待機中...')
        # リクエストのインスタンスを生成
        self.ee_request = SuctionCommand.Request()
        


        # self.arm_and_ee_send_request_init()


        # 検出サービス
        self.detect_srv = self.create_service(
            DetectTomato,
            'detect_tomato',
            self.handle_detect_tomato, callback_group = cbg
        )

        # 収穫サービス 
        self.harvest_srv = self.create_service(
            HarvestTomato,
            'harvest_tomato',
            self.handle_harvest_tomato, callback_group = cbg
        )

        
        
        # アームとエンドエフェクタのリセットサービス
        self.reset_srv = self.create_service(
            ResetArmEnd,
            'reset_arm_end',
            self.reset_arm_end, callback_group=cbg

        )


    def vision_send_request_check(self):
        self.get_logger().info("vision_send_request_check() -Start synchronous call")

        # req = VisionService.Request()
        self.vision_request.task = "detect_check"
        self.vision_request.direction = "f"

        if not self.vision_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error("Vision service not available.")
            return None
        
        try:
            # 同期呼び出し
            res = self.vision_client.call(self.vision_request)
            self.get_logger().info(f"[client] detect_check={res.detect_check}, len={len(res.target_pos.tomato_data)}")
            return res
        except Exception as e:
            self.get_logger().error(f"Vision service call failed:{e!r}")
            return None

    def vision_send_request_tompos(self):
        self.get_logger().info("vision_send_request_tompos() - Start syncrhonous call")

        # req = VisionService.Request()
        self.vision_request.task = "req_tomato_pose"
        self.vision_request.direction = "f"

        # サービスが利用可能かチェック
        if not self.vision_client.wait_for_service(timeout_sec = 1.0):
            self.get_logger().error("Vision service not available.")
            return None
        
        try:
            #同期呼び出しを行う
            res = self.vision_client.call(self.vision_request)
            self.get_logger().info("Vision service call complete (tompos).")
            return res
        except Exception as e:
            self.get_logger().error(f"Vision service call failed: {e!r}")
            return None
        # self.get_logger().info("vision_send_request_tomposを呼び出しました")
        # self.vision_request.task = "req_tomato_pose"
        # self.vision_request.direction = "f"
        # self.vision_future = self.vision_client.call_async(self.vision_request)
        # #rclpy.spin_until_future_complete(node, self.future)
        # rclpy.spin_until_future_complete(self, self.vision_future)
        # return self.vision_future.result()
    
    # アームノードにリクエスト送信＆レスポンス受信
    def arm_and_ee_send_request_init(self):
        self.arm_request.task = "init_arm"
        self.ee_request.command = '0'

        # サービスが利用可能かチェック
        if not self.arm_client.wait_for_service(timeout_sec=1.0) or not self.ee_client.wait_for_service(timeout_sec = 1.0):
            self.get_logger().error("Arm or EE service not available for init")
            return None
        
        arm_res = None

        try:
            arm_res = self.arm_client.call(self.arm_request)
            self.get_logger().info("Arm init complete")
        except Exception as e:
            self.get_logger().error(f"Arm init call failed:{e!r}")
        
        try:
            # 同期呼び出しに変更
            self.ee_client.call(self.ee_request)
            self.get_logger().info("EE init complete.")
        except Exception as e:
            self.get_logger().error(f"EE init call failed: {e!r}")
        return arm_res

        # self.arm_request.task = "init_arm"
        # self.ee_request.command = '0'
        # self.arm_future = self.arm_client.call_async(self.arm_request)
        # self.ee_future = self.ee_client.call_async(self.ee_request)
        # rclpy.spin_until_future_complete(self, self.arm_future)
        # rclpy.spin_until_future_complete(self, self.ee_future)
        # return self.arm_future.result()
    
    def arm_send_request_target(self, target, pre_h):
        self.arm_request.task = "move_to_target"
        self.arm_request.target.x = target.x
        self.arm_request.target.y = target.y
        self.arm_request.target.z = target.z + pre_h.data
        self.arm_request.target.approach_direction = target.approach_direction

        # サービスが利用可能かチェック
        if not self.arm_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error("Arm service not available for move_to_target.")
            return None
        
        try:
            arm_res = self.arm_client.call(self.arm_request)
            return arm_res
        except Exception as e:
            self.get_logger().error(f"Arm move_to_target call failed: {e!r}")
            return None

        # self.arm_request.task = "move_to_target"
        # self.arm_request.target.x = target.x
        # self.arm_request.target.y = target.y
        # self.arm_request.target.z = target.z + pre_h.data
        # self.arm_request.target.approach_direction = target.approach_direction
        
        # self.arm_future = self.arm_client.call_async(self.arm_request)
        # rclpy.spin_until_future_complete(self, self.arm_future)
        # return self.arm_future.result()

    def arm_send_request_box(self):
        self.arm_request.task = "move_to_box"

        if not self.arm_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error("Arm service not available for move_to_box")
            return None
        
        try:
            # 同期呼び出しに変更
            arm_res = self.arm_client.call(self.arm_request)
            return arm_res
        except Exception as e:
            self.get_logger().error(f"Arm move_to_box call failed: {e!r}")
            return None

        # self.arm_future = self.arm_client.call_async(self.arm_request)
        # rclpy.spin_until_future_complete(self, self.arm_future)
        # return self.arm_future.result()
    
    def arm_send_request_home(self, target):



        self.arm_request.task = "home"
        self.arm_request.target.x = target.x
        self.arm_request.target.y = target.y
        self.arm_request.target.z = target.z
        self.arm_request.target.approach_direction = target.approach_direction

        # サービスが利用可能かチェック
        if not self.arm_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error("Arm service not available for home")
            return None
        try :
            # 同期呼び出しに変更
            arm_res = self.arm_client.call(self.arm_request)
            return arm_res
        except Exception as e:
            self.get_logger().error(f"Arm home call failed: {e!r}")
            return None
        # self.arm_future = self.arm_client.call_async(self.arm_request)
        # rclpy.spin_until_future_complete(self, self.arm_future)
        # return self.arm_future.result()

    # EEノードにリクエスト送信＆レスポンス受信
    def ee_send_request(self, mode):
        self.ee_request.command = mode
        # サービスが利用可能かチェック
        if not self.ee_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error("EE service not available for mode {mode}")
            return None
        
        try:
            # 同期呼び出しに変更
            ee_res = self.ee_client.call(self.ee_request)
            return ee_res
        except Exception as e:
            self.get_logger().error(f"EE comand {mode} call failed: {e!r}")
            return None
        
        # self.ee_future = self.ee_client.call_async(self.ee_request)
        # rclpy.spin_until_future_complete(self, self.ee_future)
        # return self.ee_future.result()
    

    def handle_detect_tomato(self, request, response):
        self.get_logger().info("今からrud_detect_phaseを呼び出します")
        result = self.run_detect_phase()

        response.found = result["found"]
        response.candidate_count = len(result["targets"])
        response.x = [float(t.x) for t in result["targets"]]
        response.y = [float(t.y) for t in result["targets"]]
        response.z = [float(t.z) for t in result["targets"]]
        response.message = result["message"]
        self.get_logger().info(f"result : {response}")
        return response
    
    def handle_harvest_tomato(self, request, response):
        self.get_logger().info("今からrun_harvest_phaseを呼び出します")
        ok, msg = self.run_harvest_phase()
        response.success = ok
        response.message = msg

        return response
    
    def reset_arm_end(self, request, response):
        self.get_logger().info("リセットを開始します")
        result = self.arm_and_ee_send_request_init()
        self.get_logger().info("リセット完了しました")
        if result is None:
            self.get_logger().error("リセット失敗")
            response.success = False
            response.message = "failure"

            return response
        
        response.success = True
        response.message = "success"

        return response 
        



            

    def run_detect_phase(self):
        logger = self.get_logger()
        self.arm_and_ee_send_request_init()
        # 俯瞰カメラでトマトチェック
        print("今からチェックしに行きます")
        vis_res = self.vision_send_request_check()
        print("俯瞰カメラでトマトをチェックしに行きましたよ")
        print(f"vis_res = {vis_res}")
        # logger().info(f"vis_res :{vis_res}")
        if vis_res is None or (not vis_res.detect_check):
            print("vis_res is None")
            return {
                "found" : False,
                "message" : "トマトが見つかりませんでした",
                "targets" : [],
                "pre_arm_height" : None
            }
        
        # 俯瞰カメラで得た1個目を「狙うべき株」として仮決め
        rough_target = vis_res.target_pos.tomato_data[0]

        # 2. アームを移動させる
        arm_home_res = self.arm_send_request_home(rough_target)
        pre_arm_hight = arm_home_res.tom_hight

        # 3. 手先カメラで詳細なトマト座標を得る
        close_res = self.vision_send_request_tompos()
        logger.info(f"手先カメラの詳細な情報を取得したよ: {close_res}")
        # [x, y, z, 侵入角度]がトマトの個数分あるが、そのうち１個目を収穫ターゲットにする[0]
        print("=========================================================")
        precise_targets = close_res.target_pos.tomato_data # tomato_data[0]から変更した
        logger.info(f"precese_targets : {precise_targets}")
        # # 何もなかったら
        # if len(precise_targets) == 0:
        #     logger.info(f"近距離でトマトを再検出できませんでした")
        #     return {
        #         "found" : False,
        #         "message" : "近距離でトマトを再検出できませんでした",
        #         "targets" : [],
        #         "pre_arm_height" : pre_arm_hight,
        #     }
        print("ここまで実行できました")
        # 成功したので、ノード内に記憶しておく
        # メンバ変数として記憶しておくことで、Harvest側でも使用できるようにしている
        self.last_targets = precise_targets
        self.last_pre_arm_height = pre_arm_hight

        # ros2 のデバックで表示する
        # logger.info(f"{len(precise_targets)}個のトマトを検出")

        return {
            "found" : True,
            "message" : "収穫候補を検出しました",
            "targets" : precise_targets,
            "pre_arm_hight" : pre_arm_hight,
        }
    # "message" : f"{len(precise_targets)}個の収穫候補を検出しました",
    
    def run_harvest_phase(self):
        logger = self.get_logger()
        flag = 0
        logger.info(f"run_harvest_phaseに入りました")
        # まず直近のターゲットがあるか確認
        if not hasattr(self, "last_targets") or len(self.last_targets) == 0:
            return (False, "収穫するものがない。先に検出してください")
        logger.info(f"確認完了")
        # とりあえず1番目のターゲットを狙う
        targets = self.last_targets
        pre_h = self.last_pre_arm_height

        # demo.py と同じ方針で、targetsを順番に渡す
        for i, target in enumerate(targets):
        #1. アームをターゲットへ
            logger.info(f"アームをターゲットへ動作させます")
            arm_go_res = self.arm_send_request_target(target, pre_h)

            print(f"arm_response.task_comp:{arm_go_res.task_comp}")


            if arm_go_res.task_comp:
                mode = '1' # 吸引
                ee_response = self.ee_send_request(mode)

                while 1:
                    if ee_response.answer == mode:
                        print('吸引成功')
                        break
                    elif ee_response.answer == '666':
                        print('タイムアウト→成功とみなします')
                        break
                    else:
                        print('吸引失敗')
                        continue
                    
                mode = '2'
                ee_response = self.ee_send_request(mode)

                while 1:
                    if ee_response.answer == mode:
                        print('顎閉じ成功')
                        break
                    elif ee_response.answer == '666' :
                        print('タイムアウト ▶ 成功とします')
                        break
                    else :
                        # トライしなおす？
                        print('顎閉じ失敗')
                        continue                    

                # ボックスへ移動
                arm_response = self.arm_send_request_box()
                mode = '3' #顎開く

                ee_response = self.ee_send_request(mode)
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
                ee_response = self.ee_send_request(mode)
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

                flag = 1
                
                # return (True, "収穫完了しました")              
            else :
                print("収穫動作を失敗しました。。。")
                mode = '0' # 吸引停止
                ee_response = self.ee_send_request(mode)
                while 1:
                    if ee_response.answer == mode :
                        print('吸引停止成功')
                        break
                    else :
                        print('吸引停止失敗')
                        continue
                mode = '3' # 顎開く
                ee_response = self.ee_send_request(mode)
                while 1:
                    if ee_response.answer == mode :
                        print('顎開き成功')
                        break
                    else :
                        print('顎開き失敗')
                        continue
                time.sleep(3)    
                # return (False, "トマトの収穫に失敗しました")

        self.arm_and_ee_send_request_init()

        if flag == 1:
            return (True, "収穫完了しました")
        else:
            return (False, "トマトの収穫に失敗しました")



def main(args=None):
    rclpy.init(args=args)
    node = HarvestGatewayNode()
    executor = MultiThreadedExecutor() # 追加
    executor.add_node(node) # 追加

    try:
        # rclpy.spin(node)
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down")
    finally:
        # node.destroy_node()
        # rclpy.shutdown()
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()