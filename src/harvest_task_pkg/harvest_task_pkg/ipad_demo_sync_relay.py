# import rclpy
# from rclpy.node import Node
# # rclpy.qos から qos_profile_services_default をインポート
# from rclpy.qos import qos_profile_services_default
# from toms_msg.srv import SuctionCommand, ArmService, VisionService, DetectTomato, HarvestTomato, ResetArmEnd

# from playsound import playsound
# import time
# import numpy as np
# import yaml

# from rclpy.executors import MultiThreadedExecutor
# from rclpy.callback_groups import ReentrantCallbackGroup

# class HarvestGatewayNode(Node):
#     def __init__(self):
#         super().__init__('harvest_gateway_node')

#         cbg = ReentrantCallbackGroup()

# # 検出サービス
#         self.detect_srv = self.create_service(
#             DetectTomato,
#             'detect_tomato',
#             self.handle_detect_tomato, callback_group = cbg
#         )

#         # 収穫サービス 
#         self.harvest_srv = self.create_service(
#             HarvestTomato,
#             'harvest_tomato',
#             self.handle_harvest_tomato, callback_group = cbg
#         )

        
        
#         # アームとエンドエフェクタのリセットサービス
#         self.reset_srv = self.create_service(
#             ResetArmEnd,
#             'reset_arm_end',
#             self.reset_arm_end, callback_group=cbg

#         )

#         self.vision_client = self.create_client(
#             VisionService,
#             "vision_service",
#             qos_profile = qos_profile_services_default, callback_group = cbg
#         )
#         # while not self.vision_client.wait_for_service(timeout_sec=1.0):
#         #     self.get_logger().info("ビジョンサーバ待機中...")
#         self.vision_request = VisionService.Request()

#         self.arm_client = self.create_client(
#             ArmService,
#             "arm_service",
#             qos_profile=qos_profile_services_default, callback_group = cbg)
#         # while not self.arm_client.wait_for_service(timeout_sec=1.0):
#         #     self.get_logger().info('アームサーバ待機中...')
#         self.arm_request =  ArmService.Request()

#         self.ee_client = self.create_client(
#             SuctionCommand,
#             'command',
#             qos_profile=qos_profile_services_default, callback_group = cbg)
#         # playsound("/home/ylab/toms_ws/src/end_effector_pkg/end_effector_pkg/sound/サクションモジュールクライアントノードを起動したのだ.wav")
#         # while not self.ee_client.wait_for_service(timeout_sec=1.0):
#         #     self.get_logger().info('EEサーバ待機中...')
#         # リクエストのインスタンスを生成
#         self.ee_request = SuctionCommand.Request()
        


#         # self.arm_and_ee_send_request_init()


#         # # 検出サービス
#         # self.detect_srv = self.create_service(
#         #     DetectTomato,
#         #     'detect_tomato',
#         #     self.handle_detect_tomato, callback_group = cbg
#         # )

#         # # 収穫サービス 
#         # self.harvest_srv = self.create_service(
#         #     HarvestTomato,
#         #     'harvest_tomato',
#         #     self.handle_harvest_tomato, callback_group = cbg
#         # )

        
        
#         # # アームとエンドエフェクタのリセットサービス
#         # self.reset_srv = self.create_service(
#         #     ResetArmEnd,
#         #     'reset_arm_end',
#         #     self.reset_arm_end, callback_group=cbg

#         # )


#     def vision_send_request_check(self):
#         self.get_logger().info("vision_send_request_check() -Start synchronous call")

#         # req = VisionService.Request()
#         self.vision_request.task = "detect_check"
#         self.vision_request.direction = "f"

#         if not self.vision_client.wait_for_service(timeout_sec=1.0):
#             self.get_logger().error("Vision service not available.")
#             return None
        
#         try:
#             # 同期呼び出し
#             res = self.vision_client.call(self.vision_request)
#             self.get_logger().info(f"[client] detect_check={res.detect_check}, len={len(res.target_pos.tomato_data)}")
#             return res
#         except Exception as e:
#             self.get_logger().error(f"Vision service call failed:{e!r}")
#             return None

#     def vision_send_request_tompos(self):
#         self.get_logger().info("vision_send_request_tompos() - Start syncrhonous call")

#         # req = VisionService.Request()
#         self.vision_request.task = "req_tomato_pose"
#         self.vision_request.direction = "f"

#         # サービスが利用可能かチェック
#         if not self.vision_client.wait_for_service(timeout_sec = 1.0):
#             self.get_logger().error("Vision service not available.")
#             return None
        
#         try:
#             #同期呼び出しを行う
#             res = self.vision_client.call(self.vision_request)
#             self.get_logger().info("Vision service call complete (tompos).")
#             return res
#         except Exception as e:
#             self.get_logger().error(f"Vision service call failed: {e!r}")
#             return None
#         # self.get_logger().info("vision_send_request_tomposを呼び出しました")
#         # self.vision_request.task = "req_tomato_pose"
#         # self.vision_request.direction = "f"
#         # self.vision_future = self.vision_client.call_async(self.vision_request)
#         # #rclpy.spin_until_future_complete(node, self.future)
#         # rclpy.spin_until_future_complete(self, self.vision_future)
#         # return self.vision_future.result()
    
#     # アームノードにリクエスト送信＆レスポンス受信
#     def arm_and_ee_send_request_init(self):
#         self.arm_request.task = "init_arm"
#         self.ee_request.command = '0'

#         # サービスが利用可能かチェック
#         if not self.arm_client.wait_for_service(timeout_sec=1.0) or not self.ee_client.wait_for_service(timeout_sec = 1.0):
#             self.get_logger().error("Arm or EE service not available for init")
#             return None
        
#         arm_res = None

#         try:
#             arm_res = self.arm_client.call(self.arm_request)
#             self.get_logger().info("Arm init complete")
#         except Exception as e:
#             self.get_logger().error(f"Arm init call failed:{e!r}")
        
#         try:
#             # 同期呼び出しに変更
#             self.ee_client.call(self.ee_request)
#             self.get_logger().info("EE init complete.")
#         except Exception as e:
#             self.get_logger().error(f"EE init call failed: {e!r}")
#         return arm_res

#         # self.arm_request.task = "init_arm"
#         # self.ee_request.command = '0'
#         # self.arm_future = self.arm_client.call_async(self.arm_request)
#         # self.ee_future = self.ee_client.call_async(self.ee_request)
#         # rclpy.spin_until_future_complete(self, self.arm_future)
#         # rclpy.spin_until_future_complete(self, self.ee_future)
#         # return self.arm_future.result()
    
#     def arm_send_request_target(self, target, pre_h):
#         self.arm_request.task = "move_to_target"
#         self.arm_request.target.x = target.x
#         self.arm_request.target.y = target.y
#         self.arm_request.target.z = target.z + pre_h.data
#         self.arm_request.target.approach_direction = target.approach_direction

#         # サービスが利用可能かチェック
#         if not self.arm_client.wait_for_service(timeout_sec=1.0):
#             self.get_logger().error("Arm service not available for move_to_target.")
#             return None
        
#         try:
#             arm_res = self.arm_client.call(self.arm_request)
#             return arm_res
#         except Exception as e:
#             self.get_logger().error(f"Arm move_to_target call failed: {e!r}")
#             return None

#         # self.arm_request.task = "move_to_target"
#         # self.arm_request.target.x = target.x
#         # self.arm_request.target.y = target.y
#         # self.arm_request.target.z = target.z + pre_h.data
#         # self.arm_request.target.approach_direction = target.approach_direction
        
#         # self.arm_future = self.arm_client.call_async(self.arm_request)
#         # rclpy.spin_until_future_complete(self, self.arm_future)
#         # return self.arm_future.result()

#     def arm_send_request_box(self):
#         self.arm_request.task = "move_to_box"

#         if not self.arm_client.wait_for_service(timeout_sec=1.0):
#             self.get_logger().error("Arm service not available for move_to_box")
#             return None
        
#         try:
#             # 同期呼び出しに変更
#             arm_res = self.arm_client.call(self.arm_request)
#             return arm_res
#         except Exception as e:
#             self.get_logger().error(f"Arm move_to_box call failed: {e!r}")
#             return None

#         # self.arm_future = self.arm_client.call_async(self.arm_request)
#         # rclpy.spin_until_future_complete(self, self.arm_future)
#         # return self.arm_future.result()
    
#     def arm_send_request_home(self, target):



#         self.arm_request.task = "home"
#         self.arm_request.target.x = target.x
#         self.arm_request.target.y = target.y
#         self.arm_request.target.z = target.z
#         self.arm_request.target.approach_direction = target.approach_direction

#         # サービスが利用可能かチェック
#         if not self.arm_client.wait_for_service(timeout_sec=1.0):
#             self.get_logger().error("Arm service not available for home")
#             return None
#         try :
#             # 同期呼び出しに変更
#             arm_res = self.arm_client.call(self.arm_request)
#             return arm_res
#         except Exception as e:
#             self.get_logger().error(f"Arm home call failed: {e!r}")
#             return None
#         # self.arm_future = self.arm_client.call_async(self.arm_request)
#         # rclpy.spin_until_future_complete(self, self.arm_future)
#         # return self.arm_future.result()

#     # EEノードにリクエスト送信＆レスポンス受信
#     def ee_send_request(self, mode):
#         self.ee_request.command = mode
#         # サービスが利用可能かチェック
#         if not self.ee_client.wait_for_service(timeout_sec=1.0):
#             self.get_logger().error("EE service not available for mode {mode}")
#             return None
        
#         try:
#             # 同期呼び出しに変更
#             ee_res = self.ee_client.call(self.ee_request)
#             return ee_res
#         except Exception as e:
#             self.get_logger().error(f"EE comand {mode} call failed: {e!r}")
#             return None
        
#         # self.ee_future = self.ee_client.call_async(self.ee_request)
#         # rclpy.spin_until_future_complete(self, self.ee_future)
#         # return self.ee_future.result()
    

#     def handle_detect_tomato(self, request, response):
#         self.get_logger().info("今からrud_detect_phaseを呼び出します")
#         result = self.run_detect_phase()

#         response.found = result["found"]
#         response.candidate_count = len(result["targets"])
#         response.x = [float(t.x) for t in result["targets"]]
#         response.y = [float(t.y) for t in result["targets"]]
#         response.z = [float(t.z) for t in result["targets"]]
#         response.message = result["message"]
#         self.get_logger().info(f"result : {response}")
#         return response
    
#     def handle_harvest_tomato(self, request, response):
#         self.get_logger().info("今からrun_harvest_phaseを呼び出します")
#         ok, msg = self.run_harvest_phase()
#         response.success = ok
#         response.message = msg

#         return response
    
#     def reset_arm_end(self, request, response):
#         self.get_logger().info("リセットを開始します")
#         result = self.arm_and_ee_send_request_init()
#         self.get_logger().info("リセット完了しました")
#         if result is None:
#             self.get_logger().error("リセット失敗")
#             response.success = False
#             response.message = "failure"

#             return response
        
#         response.success = True
#         response.message = "success"

#         return response 
        



            

#     def run_detect_phase(self):
#         logger = self.get_logger()
#         # self.arm_and_ee_send_request_init()
#         # 俯瞰カメラでトマトチェック
#         print("今からチェックしに行きます")
#         vis_res = self.vision_send_request_check()
#         print("俯瞰カメラでトマトをチェックしに行きましたよ")
#         print(f"vis_res = {vis_res}")
#         # logger().info(f"vis_res :{vis_res}")
#         if vis_res is None or (not vis_res.detect_check):
#             print("vis_res is None")
#             return {
#                 "found" : False,
#                 "message" : "トマトが見つかりませんでした",
#                 "targets" : [],
#                 "pre_arm_height" : None
#             }
        
#         # 俯瞰カメラで得た1個目を「狙うべき株」として仮決め
#         rough_target = vis_res.target_pos.tomato_data[0]

#         # 2. アームを移動させる
#         arm_home_res = self.arm_send_request_home(rough_target)
#         pre_arm_hight = arm_home_res.tom_hight

#         # 3. 手先カメラで詳細なトマト座標を得る
#         close_res = self.vision_send_request_tompos()
#         logger.info(f"手先カメラの詳細な情報を取得したよ: {close_res}")
#         # [x, y, z, 侵入角度]がトマトの個数分あるが、そのうち１個目を収穫ターゲットにする[0]
#         print("=========================================================")
#         precise_targets = close_res.target_pos.tomato_data # tomato_data[0]から変更した
#         logger.info(f"precese_targets : {precise_targets}")
#         # # 何もなかったら
#         # if len(precise_targets) == 0:
#         #     logger.info(f"近距離でトマトを再検出できませんでした")
#         #     return {
#         #         "found" : False,
#         #         "message" : "近距離でトマトを再検出できませんでした",
#         #         "targets" : [],
#         #         "pre_arm_height" : pre_arm_hight,
#         #     }
#         print("ここまで実行できました")
#         # 成功したので、ノード内に記憶しておく
#         # メンバ変数として記憶しておくことで、Harvest側でも使用できるようにしている
#         self.last_targets = precise_targets
#         self.last_pre_arm_height = pre_arm_hight

#         # ros2 のデバックで表示する
#         # logger.info(f"{len(precise_targets)}個のトマトを検出")

#         return {
#             "found" : True,
#             "message" : "収穫候補を検出しました",
#             "targets" : precise_targets,
#             "pre_arm_hight" : pre_arm_hight,
#         }
#     # "message" : f"{len(precise_targets)}個の収穫候補を検出しました",
    
#     def run_harvest_phase(self):
#         logger = self.get_logger()
#         flag = 0
#         logger.info(f"run_harvest_phaseに入りました")
#         # まず直近のターゲットがあるか確認
#         if not hasattr(self, "last_targets") or len(self.last_targets) == 0:
#             return (False, "収穫するものがない。先に検出してください")
#         logger.info(f"確認完了")
#         # とりあえず1番目のターゲットを狙う
#         targets = self.last_targets
#         pre_h = self.last_pre_arm_height

#         # demo.py と同じ方針で、targetsを順番に渡す
#         for i, target in enumerate(targets):
#         #1. アームをターゲットへ
#             logger.info(f"アームをターゲットへ動作させます")
#             arm_go_res = self.arm_send_request_target(target, pre_h)

#             print(f"arm_response.task_comp:{arm_go_res.task_comp}")


#             if arm_go_res.task_comp:
#                 mode = '1' # 吸引
#                 ee_response = self.ee_send_request(mode)

#                 while 1:
#                     if ee_response.answer == mode:
#                         print('吸引成功')
#                         break
#                     elif ee_response.answer == '666':
#                         print('タイムアウト→成功とみなします')
#                         break
#                     else:
#                         print('吸引失敗')
#                         continue
                    
#                 mode = '2'
#                 ee_response = self.ee_send_request(mode)

#                 while 1:
#                     if ee_response.answer == mode:
#                         print('顎閉じ成功')
#                         break
#                     elif ee_response.answer == '666' :
#                         print('タイムアウト ▶ 成功とします')
#                         break
#                     else :
#                         # トライしなおす？
#                         print('顎閉じ失敗')
#                         continue                    

#                 # ボックスへ移動
#                 arm_response = self.arm_send_request_box()
#                 mode = '3' #顎開く

#                 ee_response = self.ee_send_request(mode)
#                 while 1:
#                     if ee_response.answer == mode :
#                         print('顎開き成功')
#                         break
#                     elif ee_response.answer == '666' :
#                         print('タイムアウト ▶ 成功とします')
#                         break
#                     else :
#                         print('顎開き失敗')
#                         continue
                
#                 mode = '0' # 吸引停止
#                 ee_response = self.ee_send_request(mode)
#                 while 1:
#                     if ee_response.answer == mode :
#                         print('吸引停止成功')
#                         break
#                     elif ee_response.answer == '666' :
#                         print('タイムアウト ▶ 成功とします')
#                         break
#                     else :
#                         print('吸引停止失敗')
#                         continue

#                 flag = 1
                
#                 # return (True, "収穫完了しました")              
#             else :
#                 print("収穫動作を失敗しました。。。")
#                 mode = '0' # 吸引停止
#                 ee_response = self.ee_send_request(mode)
#                 while 1:
#                     if ee_response.answer == mode :
#                         print('吸引停止成功')
#                         break
#                     else :
#                         print('吸引停止失敗')
#                         continue
#                 mode = '3' # 顎開く
#                 ee_response = self.ee_send_request(mode)
#                 while 1:
#                     if ee_response.answer == mode :
#                         print('顎開き成功')
#                         break
#                     else :
#                         print('顎開き失敗')
#                         continue
#                 time.sleep(3)    
#                 # return (False, "トマトの収穫に失敗しました")

#         self.arm_and_ee_send_request_init()

#         if flag == 1:
#             return (True, "収穫完了しました")
#         else:
#             return (False, "トマトの収穫に失敗しました")



# def main(args=None):
#     rclpy.init(args=args)
#     node = HarvestGatewayNode()
#     executor = MultiThreadedExecutor() # 追加
#     executor.add_node(node) # 追加

#     try:
#         # rclpy.spin(node)
#         executor.spin()
#     except KeyboardInterrupt:
#         node.get_logger().info("Shutting down")
#     finally:
#         # node.destroy_node()
#         # rclpy.shutdown()
#         executor.shutdown()
#         node.destroy_node()
#         rclpy.shutdown()

# import rclpy
# from rclpy.node import Node
# # rclpy.qos から qos_profile_services_default をインポート
# from rclpy.qos import qos_profile_services_default
# from toms_msg.srv import SuctionCommand, ArmService, VisionService, DetectTomato, HarvestTomato, ResetArmEnd
# from toms_msg.msg import TomatoData

# from playsound import playsound
# import time
# import numpy as np
# import yaml

# from rclpy.executors import MultiThreadedExecutor
# from rclpy.callback_groups import ReentrantCallbackGroup

# class HarvestGatewayNode(Node):
#     def __init__(self):
#         super().__init__('harvest_gateway_node')

#         cbg = ReentrantCallbackGroup()

# # 検出サービス
#         self.detect_srv = self.create_service(
#             DetectTomato,
#             'detect_tomato',
#             self.handle_detect_tomato, callback_group = cbg
#         )

#         # 収穫サービス 
#         self.harvest_srv = self.create_service(
#             HarvestTomato,
#             'harvest_tomato',
#             self.handle_harvest_tomato, callback_group = cbg
#         )

        
        
#         # アームとエンドエフェクタのリセットサービス
#         self.reset_srv = self.create_service(
#             ResetArmEnd,
#             'reset_arm_end',
#             self.reset_arm_end, callback_group=cbg

#         )

#         self.vision_client = self.create_client(
#             VisionService,
#             "vision_service",
#             qos_profile = qos_profile_services_default, callback_group = cbg
#         )
#         # while not self.vision_client.wait_for_service(timeout_sec=1.0):
#         #     self.get_logger().info("ビジョンサーバ待機中...")
#         self.vision_request = VisionService.Request()

#         self.arm_client = self.create_client(
#             ArmService,
#             "arm_service",
#             qos_profile=qos_profile_services_default, callback_group = cbg)
#         # while not self.arm_client.wait_for_service(timeout_sec=1.0):
#         #     self.get_logger().info('アームサーバ待機中...')
#         self.arm_request =  ArmService.Request()

#         self.ee_client = self.create_client(
#             SuctionCommand,
#             'command',
#             qos_profile=qos_profile_services_default, callback_group = cbg)
#         # playsound("/home/ylab/toms_ws/src/end_effector_pkg/end_effector_pkg/sound/サクションモジュールクライアントノードを起動したのだ.wav")
#         # while not self.ee_client.wait_for_service(timeout_sec=1.0):
#         #     self.get_logger().info('EEサーバ待機中...')
#         # リクエストのインスタンスを生成
#         self.ee_request = SuctionCommand.Request()
        


#         # self.arm_and_ee_send_request_init()


#         # # 検出サービス
#         # self.detect_srv = self.create_service(
#         #     DetectTomato,
#         #     'detect_tomato',
#         #     self.handle_detect_tomato, callback_group = cbg
#         # )

#         # # 収穫サービス 
#         # self.harvest_srv = self.create_service(
#         #     HarvestTomato,
#         #     'harvest_tomato',
#         #     self.handle_harvest_tomato, callback_group = cbg
#         # )

        
        
#         # # アームとエンドエフェクタのリセットサービス
#         # self.reset_srv = self.create_service(
#         #     ResetArmEnd,
#         #     'reset_arm_end',
#         #     self.reset_arm_end, callback_group=cbg

#         # )


#     def vision_send_request_check(self):
#         self.get_logger().info("vision_send_request_check() -Start synchronous call")

#         # req = VisionService.Request()
#         self.vision_request.task = "detect_check"
#         self.vision_request.direction = "f"

#         if not self.vision_client.wait_for_service(timeout_sec=1.0):
#             self.get_logger().error("Vision service not available.")
#             return None
        
#         try:
#             # 同期呼び出し
#             res = self.vision_client.call(self.vision_request)
#             self.get_logger().info(f"[client] detect_check={res.detect_check}, len={len(res.target_pos.tomato_data)}")
#             return res
#         except Exception as e:
#             self.get_logger().error(f"Vision service call failed:{e!r}")
#             return None

#     def vision_send_request_tompos(self):
#         self.get_logger().info("vision_send_request_tompos() - Start syncrhonous call")

#         # req = VisionService.Request()
#         self.vision_request.task = "req_tomato_pose"
#         self.vision_request.direction = "f"

#         # サービスが利用可能かチェック
#         if not self.vision_client.wait_for_service(timeout_sec = 1.0):
#             self.get_logger().error("Vision service not available.")
#             return None
        
#         try:
#             #同期呼び出しを行う
#             res = self.vision_client.call(self.vision_request)
#             self.get_logger().info("Vision service call complete (tompos).")
#             return res
#         except Exception as e:
#             self.get_logger().error(f"Vision service call failed: {e!r}")
#             return None
#         # self.get_logger().info("vision_send_request_tomposを呼び出しました")
#         # self.vision_request.task = "req_tomato_pose"
#         # self.vision_request.direction = "f"
#         # self.vision_future = self.vision_client.call_async(self.vision_request)
#         # #rclpy.spin_until_future_complete(node, self.future)
#         # rclpy.spin_until_future_complete(self, self.vision_future)
#         # return self.vision_future.result()
    
#     # アームノードにリクエスト送信＆レスポンス受信
#     def arm_and_ee_send_request_init(self):
#         self.arm_request.task = "init_arm"
#         self.ee_request.command = '0'

#         # サービスが利用可能かチェック
#         if not self.arm_client.wait_for_service(timeout_sec=1.0) or not self.ee_client.wait_for_service(timeout_sec = 1.0):
#             self.get_logger().error("Arm or EE service not available for init")
#             return None
        
#         arm_res = None

#         try:
#             arm_res = self.arm_client.call(self.arm_request)
#             self.get_logger().info("Arm init complete")
#         except Exception as e:
#             self.get_logger().error(f"Arm init call failed:{e!r}")
        
#         try:
#             # 同期呼び出しに変更
#             self.ee_client.call(self.ee_request)
#             self.get_logger().info("EE init complete.")
#         except Exception as e:
#             self.get_logger().error(f"EE init call failed: {e!r}")
#         return arm_res

#         # self.arm_request.task = "init_arm"
#         # self.ee_request.command = '0'
#         # self.arm_future = self.arm_client.call_async(self.arm_request)
#         # self.ee_future = self.ee_client.call_async(self.ee_request)
#         # rclpy.spin_until_future_complete(self, self.arm_future)
#         # rclpy.spin_until_future_complete(self, self.ee_future)
#         # return self.arm_future.result()
    
#     def arm_send_request_target(self, target, pre_h):
#         self.arm_request.task = "move_to_target"
#         self.arm_request.target.x = target.x
#         self.arm_request.target.y = target.y
#         self.arm_request.target.z = target.z + pre_h.data
#         self.arm_request.target.approach_direction = target.approach_direction

#         # サービスが利用可能かチェック
#         if not self.arm_client.wait_for_service(timeout_sec=1.0):
#             self.get_logger().error("Arm service not available for move_to_target.")
#             return None
        
#         try:
#             arm_res = self.arm_client.call(self.arm_request)
#             return arm_res
#         except Exception as e:
#             self.get_logger().error(f"Arm move_to_target call failed: {e!r}")
#             return None

#         # self.arm_request.task = "move_to_target"
#         # self.arm_request.target.x = target.x
#         # self.arm_request.target.y = target.y
#         # self.arm_request.target.z = target.z + pre_h.data
#         # self.arm_request.target.approach_direction = target.approach_direction
        
#         # self.arm_future = self.arm_client.call_async(self.arm_request)
#         # rclpy.spin_until_future_complete(self, self.arm_future)
#         # return self.arm_future.result()

#     def arm_send_request_box(self):
#         self.arm_request.task = "move_to_box"

#         if not self.arm_client.wait_for_service(timeout_sec=1.0):
#             self.get_logger().error("Arm service not available for move_to_box")
#             return None
        
#         try:
#             # 同期呼び出しに変更
#             arm_res = self.arm_client.call(self.arm_request)
#             return arm_res
#         except Exception as e:
#             self.get_logger().error(f"Arm move_to_box call failed: {e!r}")
#             return None

#         # self.arm_future = self.arm_client.call_async(self.arm_request)
#         # rclpy.spin_until_future_complete(self, self.arm_future)
#         # return self.arm_future.result()
    
#     def arm_send_request_home(self, target):



#         self.arm_request.task = "home"
#         self.arm_request.target.x = target.x
#         self.arm_request.target.y = target.y
#         self.arm_request.target.z = target.z
#         self.arm_request.target.approach_direction = target.approach_direction

#         # サービスが利用可能かチェック
#         if not self.arm_client.wait_for_service(timeout_sec=1.0):
#             self.get_logger().error("Arm service not available for home")
#             return None
#         try :
#             # 同期呼び出しに変更
#             arm_res = self.arm_client.call(self.arm_request)
#             return arm_res
#         except Exception as e:
#             self.get_logger().error(f"Arm home call failed: {e!r}")
#             return None
#         # self.arm_future = self.arm_client.call_async(self.arm_request)
#         # rclpy.spin_until_future_complete(self, self.arm_future)
#         # return self.arm_future.result()

#     # EEノードにリクエスト送信＆レスポンス受信
#     def ee_send_request(self, mode):
#         self.ee_request.command = mode
#         # サービスが利用可能かチェック
#         if not self.ee_client.wait_for_service(timeout_sec=1.0):
#             self.get_logger().error("EE service not available for mode {mode}")
#             return None
        
#         try:
#             # 同期呼び出しに変更
#             ee_res = self.ee_client.call(self.ee_request)
#             return ee_res
#         except Exception as e:
#             self.get_logger().error(f"EE comand {mode} call failed: {e!r}")
#             return None
        
#         # self.ee_future = self.ee_client.call_async(self.ee_request)
#         # rclpy.spin_until_future_complete(self, self.ee_future)
#         # return self.ee_future.result()
    

#     def handle_detect_tomato(self, request, response):
#         self.get_logger().info("今からrud_detect_phaseを呼び出します")
#         result = self.run_detect_phase()

#         response.found = result["found"]
#         response.candidate_count = len(result["targets"])
#         response.x = [float(t.x) for t in result["targets"]]
#         response.y = [float(t.y) for t in result["targets"]]
#         response.z = [float(t.z) for t in result["targets"]]
#         response.message = result["message"]
#         self.get_logger().info(f"result : {response}")
#         return response
    
#     def handle_harvest_tomato(self, request, response):
#         self.get_logger().info("今からrun_harvest_phaseを呼び出します")
#         ok, msg = self.run_harvest_phase()
#         response.success = ok
#         response.message = msg

#         return response
    
#     def reset_arm_end(self, request, response):
#         self.get_logger().info("リセットを開始します")
#         result = self.arm_and_ee_send_request_init()
#         self.get_logger().info("リセット完了しました")
#         if result is None:
#             self.get_logger().error("リセット失敗")
#             response.success = False
#             response.message = "failure"

#             return response
        
#         response.success = True
#         response.message = "success"

#         return response 
        



            

#     # def run_detect_phase(self):
#     #     logger = self.get_logger()
#     #     # self.arm_and_ee_send_request_init()
#     #     # 俯瞰カメラでトマトチェック
#     #     print("今からチェックしに行きます")
#     #     vis_res = self.vision_send_request_check()
#     #     print("俯瞰カメラでトマトをチェックしに行きましたよ")
#     #     print(f"vis_res = {vis_res}")
#     #     # logger().info(f"vis_res :{vis_res}")
#     #     if vis_res is None or (not vis_res.detect_check):
#     #         print("vis_res is None")
#     #         return {
#     #             "found" : False,
#     #             "message" : "トマトが見つかりませんでした",
#     #             "targets" : [],
#     #             "pre_arm_height" : None
#     #         }
        
#     #     # 俯瞰カメラで得た1個目を「狙うべき株」として仮決め
#     #     rough_target = vis_res.target_pos.tomato_data[0]

#     #     # 2. アームを移動させる
#     #     arm_home_res = self.arm_send_request_home(rough_target)
#     #     pre_arm_hight = arm_home_res.tom_hight

#     #     # 3. 手先カメラで詳細なトマト座標を得る
#     #     close_res = self.vision_send_request_tompos()
#     #     logger.info(f"手先カメラの詳細な情報を取得したよ: {close_res}")
#     #     # [x, y, z, 侵入角度]がトマトの個数分あるが、そのうち１個目を収穫ターゲットにする[0]
#     #     print("=========================================================")
#     #     precise_targets = close_res.target_pos.tomato_data # tomato_data[0]から変更した
#     #     logger.info(f"precese_targets : {precise_targets}")
#     #     # # 何もなかったら
#     #     # if len(precise_targets) == 0:
#     #     #     logger.info(f"近距離でトマトを再検出できませんでした")
#     #     #     return {
#     #     #         "found" : False,
#     #     #         "message" : "近距離でトマトを再検出できませんでした",
#     #     #         "targets" : [],
#     #     #         "pre_arm_height" : pre_arm_hight,
#     #     #     }
#     #     print("ここまで実行できました")
#     #     # 成功したので、ノード内に記憶しておく
#     #     # メンバ変数として記憶しておくことで、Harvest側でも使用できるようにしている
#     #     self.last_targets = precise_targets
#     #     self.last_pre_arm_height = pre_arm_hight

#     #     # ros2 のデバックで表示する
#     #     # logger.info(f"{len(precise_targets)}個のトマトを検出")

#     #     return {
#     #         "found" : True,
#     #         "message" : "収穫候補を検出しました",
#     #         "targets" : precise_targets,
#     #         "pre_arm_hight" : pre_arm_hight,
#     #     }
#     # # "message" : f"{len(precise_targets)}個の収穫候補を検出しました",

#     def run_detect_phase(self):
#             logger = self.get_logger()
#             logger.info("【テスト】画像認識をバイパスし、指定座標をセットします")

#             # ==========================================
#             # 🎯 アームを動かしたい座標
#             # ==========================================
#             target_x = 69
#             target_y = 400
#             target_z = 150    # Z座標（安全な高さ）
#             target_dir = 90   # 侵入角度（真正面）
#             # ==========================================

#             dummy_target = TomatoData()
#             dummy_target.x = int(target_x)
#             dummy_target.y = int(target_y)
#             dummy_target.z = int(target_z)
#             dummy_target.approach_direction = int(target_dir)

#             logger.info("アームを初期(Home)位置へ移動させます...")
#             arm_home_res = self.arm_send_request_home(dummy_target)
            
#             if arm_home_res is None:
#                 logger.error("アームのHome移動に失敗しました。")
#                 return {
#                     "found" : False,
#                     "message" : "アームのホーム移動応答なし",
#                     "targets" : [],
#                     "pre_arm_hight" : None,
#                 }

#             # 🌟修正: ROS 2の型エラーを防ぐため、確実に「整数(int)」として 0 を渡す
#             class DummyPreHeight:
#                 def __init__(self, val):
#                     self.data = int(val) # ここで強制的に整数化
                    
#             self.last_targets = [dummy_target]
#             self.last_pre_arm_height = DummyPreHeight(0) # 0.0ではなく 0 に変更！

#             return {
#                 "found" : True,
#                 "message" : f"手動座標（X:{dummy_target.x}, Y:{dummy_target.y}, Z:{dummy_target.z}）のセット完了",
#                 "targets" : self.last_targets,
#                 "pre_arm_hight" : self.last_pre_arm_height,
#             }




    
#     def run_harvest_phase(self):
#         logger = self.get_logger()
#         flag = 0
#         logger.info(f"run_harvest_phaseに入りました")
#         # まず直近のターゲットがあるか確認
#         if not hasattr(self, "last_targets") or len(self.last_targets) == 0:
#             return (False, "収穫するものがない。先に検出してください")
#         logger.info(f"確認完了")
#         # とりあえず1番目のターゲットを狙う
#         targets = self.last_targets
#         pre_h = self.last_pre_arm_height

#         # demo.py と同じ方針で、targetsを順番に渡す
#         for i, target in enumerate(targets):
#         #1. アームをターゲットへ
#             logger.info(f"アームをターゲットへ動作させます")
#             arm_go_res = self.arm_send_request_target(target, pre_h)

#             print(f"arm_response.task_comp:{arm_go_res.task_comp}")


#             if arm_go_res.task_comp:
#                 mode = '1' # 吸引
#                 ee_response = self.ee_send_request(mode)

#                 while 1:
#                     if ee_response.answer == mode:
#                         print('吸引成功')
#                         break
#                     elif ee_response.answer == '666':
#                         print('タイムアウト→成功とみなします')
#                         break
#                     else:
#                         print('吸引失敗')
#                         continue
                    
#                 mode = '2'
#                 ee_response = self.ee_send_request(mode)

#                 while 1:
#                     if ee_response.answer == mode:
#                         print('顎閉じ成功')
#                         break
#                     elif ee_response.answer == '666' :
#                         print('タイムアウト ▶ 成功とします')
#                         break
#                     else :
#                         # トライしなおす？
#                         print('顎閉じ失敗')
#                         continue                    

#                 # ボックスへ移動
#                 arm_response = self.arm_send_request_box()
#                 mode = '3' #顎開く

#                 ee_response = self.ee_send_request(mode)
#                 while 1:
#                     if ee_response.answer == mode :
#                         print('顎開き成功')
#                         break
#                     elif ee_response.answer == '666' :
#                         print('タイムアウト ▶ 成功とします')
#                         break
#                     else :
#                         print('顎開き失敗')
#                         continue
                
#                 mode = '0' # 吸引停止
#                 ee_response = self.ee_send_request(mode)
#                 while 1:
#                     if ee_response.answer == mode :
#                         print('吸引停止成功')
#                         break
#                     elif ee_response.answer == '666' :
#                         print('タイムアウト ▶ 成功とします')
#                         break
#                     else :
#                         print('吸引停止失敗')
#                         continue

#                 flag = 1
                
#                 # return (True, "収穫完了しました")              
#             else :
#                 print("収穫動作を失敗しました。。。")
#                 mode = '0' # 吸引停止
#                 ee_response = self.ee_send_request(mode)
#                 while 1:
#                     if ee_response.answer == mode :
#                         print('吸引停止成功')
#                         break
#                     else :
#                         print('吸引停止失敗')
#                         continue
#                 mode = '3' # 顎開く
#                 ee_response = self.ee_send_request(mode)
#                 while 1:
#                     if ee_response.answer == mode :
#                         print('顎開き成功')
#                         break
#                     else :
#                         print('顎開き失敗')
#                         continue
#                 time.sleep(3)    
#                 # return (False, "トマトの収穫に失敗しました")

#         self.arm_and_ee_send_request_init()

#         if flag == 1:
#             return (True, "収穫完了しました")
#         else:
#             return (False, "トマトの収穫に失敗しました")



# def main(args=None):
#     rclpy.init(args=args)
#     node = HarvestGatewayNode()
#     executor = MultiThreadedExecutor() # 追加
#     executor.add_node(node) # 追加

#     try:
#         # rclpy.spin(node)
#         executor.spin()
#     except KeyboardInterrupt:
#         node.get_logger().info("Shutting down")
#     finally:
#         # node.destroy_node()
#         # rclpy.shutdown()
#         executor.shutdown()
#         node.destroy_node()
#         rclpy.shutdown()

# """Manual target gateway v7: register a crosshair target, then move the arm.

# The original provisional 640x480 / 150 mm coordinate model is retained.
# Depth integration and camera-to-robot calibration are NOT implemented here.
# Detection stores coordinates only. Harvest commands move_to_target only.
# The end effector, rail and home-height sequence are not used.
# Timeouts do not cancel commands already sent to hardware.
# """

















# import math
# import threading
# from pathlib import Path
# from types import SimpleNamespace

# import rclpy
# from rclpy.node import Node
# from rclpy.executors import MultiThreadedExecutor
# from rclpy.callback_groups import ReentrantCallbackGroup
# from rclpy.qos import qos_profile_services_default
# from toms_msg.srv import (
#     SuctionCommand, ArmService, VisionService,
#     DetectTomato, HarvestTomato, ResetArmEnd,
# )
# from toms_msg.msg import TomatoData

# VERSION = 'ipad-relay-v8-vision-delegation'

# class GatewayError(RuntimeError):
#     pass

# class HarvestGatewayNode(Node):
#     def __init__(self):
#         super().__init__('harvest_gateway_node')
#         self._operation_lock = threading.Lock()
#         self._fault_reason = ''
#         self.last_targets = []
#         self.last_pre_arm_height = None
#         self._timeouts = {}
        
#         self._service_discovery_timeout = float(
#             self.declare_parameter('service_discovery_timeout_sec', 10.0).value)
#         if (not math.isfinite(self._service_discovery_timeout) or self._service_discovery_timeout <= 0):
#             raise ValueError('service_discovery_timeout_sec must be finite and positive')
            
#         for key, default in [('arm', 60.0), ('ee', 15.0), ('vision', 15.0)]:
#             value = float(self.declare_parameter(f'{key}_timeout_sec', default).value)
#             if not math.isfinite(value) or value <= 0:
#                 raise ValueError(f'{key}_timeout_sec must be finite and positive')
#             self._timeouts[key] = value
            
#         self._service_group = ReentrantCallbackGroup()
#         self._client_group = ReentrantCallbackGroup()
        
#         self.detect_srv = self.create_service(
#             DetectTomato, 'detect_tomato', self.handle_detect_tomato,
#             callback_group=self._service_group)
#         self.harvest_srv = self.create_service(
#             HarvestTomato, 'harvest_tomato', self.handle_harvest_tomato,
#             callback_group=self._service_group)
#         self.reset_srv = self.create_service(
#             ResetArmEnd, 'reset_arm_end', self.reset_arm_end,
#             callback_group=self._service_group)
            
#         self.arm_client = self.create_client(
#             ArmService, 'arm_service', qos_profile=qos_profile_services_default,
#             callback_group=self._client_group)
#         self.ee_client = self.create_client(
#             SuctionCommand, 'command', qos_profile=qos_profile_services_default,
#             callback_group=self._client_group)
#         self.vision_client = self.create_client(
#             VisionService, 'vision_service', qos_profile=qos_profile_services_default,
#             callback_group=self._client_group)
            
#         self.get_logger().info(f'[{VERSION}] loaded from {Path(__file__).resolve()}')
#         self.get_logger().info('座標変換は Vision Service (RealSense深度) に委譲します')

#     def _clear_targets(self):
#         self.last_targets = []
#         self.last_pre_arm_height = None

#     def _fail_actuator(self, message):
#         self._fault_reason = message
#         self._clear_targets()
#         self.get_logger().error(message)
#         raise GatewayError(message)

#     def _call(self, client, request, label, kind):
#         """デッドロックを回避する安全な通信ラッパー"""
#         if self._fault_reason:
#             raise GatewayError(f'追加指令を保留中: {self._fault_reason}')
#         if not client.wait_for_service(timeout_sec=self._service_discovery_timeout):
#             raise GatewayError(f'{label}: {self._service_discovery_timeout:g}秒待ってもサービスを発見できません')
            
#         timeout = self._timeouts[kind]
#         self.get_logger().info(f'[WAIT] {label} / 応答上限 {timeout:g}秒')
#         finished = threading.Event()
        
#         try:
#             future = client.call_async(request)
#             future.add_done_callback(lambda _: finished.set())
#             if not future.done():
#                 finished.wait(timeout)
#             if not future.done():
#                 message = f'{label}: {timeout:g}秒以内に応答なし。実機状態を確認してください'
#                 if kind != 'vision':
#                     self._fail_actuator(message)
#                 raise GatewayError(message)
#             result = future.result()
#             if result is None:
#                 raise RuntimeError('応答がNoneです')
#         except GatewayError:
#             raise
#         except Exception as error:
#             message = f'{label}: サービス例外 {type(error).__name__}: {error}'
#             if kind != 'vision':
#                 self._fail_actuator(message)
#             raise GatewayError(message) from error
            
#         self.get_logger().info(f'[DONE] {label}')
#         return result

#     def _arm(self, task, target=None, height=0):
#         request = ArmService.Request()
#         request.task = task
#         if target is not None:
#             request.target.x = target.x
#             request.target.y = target.y
#             request.target.z = target.z + height
#             request.target.approach_direction = target.approach_direction
#             self.get_logger().info(f'[TARGET] task={task} x={request.target.x} y={request.target.y} z={request.target.z}')
        
#         result = self._call(self.arm_client, request, f'arm_service/{task}', 'arm')
#         if not getattr(result, 'task_comp', False):
#             self._fail_actuator(f'arm_service/{task}: task_compがFalseです')
#         return result

#     def arm_send_request_target(self, target, pre_h):
#         return self._arm('move_to_target', target, pre_h.data)

#     def arm_send_request_box(self):
#         return self._arm('move_to_box')

#     def arm_send_request_init(self):
#         result = self._arm('init_arm')
#         self._clear_targets()
#         return result
        
#     def arm_and_ee_send_request_init(self):
#         result = self.arm_send_request_init()
#         self.ee_send_request('0')
#         return result

#     def ee_send_request(self, mode):
#         request = SuctionCommand.Request()
#         request.command = mode
#         result = self._call(self.ee_client, request, f'command/{mode}', 'ee')
#         ans = getattr(result, 'answer', None)
#         # ハードウェア側のタイムアウト応答(666)も成功として許容する安全設計
#         if ans != mode and ans != '666':
#             self._fail_actuator(f'command/{mode}: 応答不一致 answer={ans}')
#         return result

#     def _handle(self, request, response, action, detect=False):
#         if detect:
#             response.found = False
#             response.candidate_count = 0
#             response.x, response.y, response.z = [], [], []
#         else:
#             response.success = False
            
#         if not self._operation_lock.acquire(blocking=False):
#             response.message = '別の処理を実行中です'
#             return response
            
#         try:
#             if self._fault_reason:
#                 raise GatewayError(f'追加指令を保留中: {self._fault_reason}')
#             result = action(request)
#             if detect:
#                 targets = result['targets']
#                 response.found = result['found']
#                 response.candidate_count = len(targets)
#                 response.x = [float(t.x) for t in targets]
#                 response.y = [float(t.y) for t in targets]
#                 response.z = [float(t.z) for t in targets]
#                 response.message = result['message']
#             else:
#                 response.success, response.message = result
#             self.get_logger().info(f'[RESPONSE] {response.message}')
            
#         except (GatewayError, ValueError) as error:
#             self._clear_targets()
#             response.message = str(error)
#             self.get_logger().error(f'[RESPONSE ERROR] {error}')
#         except Exception as error:
#             self._clear_targets()
#             self._fault_reason = f'{type(error).__name__}: {error}'
#             response.message = f'処理例外: {self._fault_reason}'
#             self.get_logger().error(response.message)
#         finally:
#             self._operation_lock.release()
#         return response

#     def handle_detect_tomato(self, request, response):
#         return self._handle(request, response, self.run_detect_phase, detect=True)

#     def handle_harvest_tomato(self, request, response):
#         return self._handle(request, response, lambda _: self.run_harvest_phase())

#     def reset_arm_end(self, request, response):
#         def reset(_):
#             self._clear_targets()
#             self.arm_and_ee_send_request_init()
#             return True, 'リセット完了'
#         return self._handle(request, response, reset)

#     # =========================================================================
#     # 🌟 検出フェーズ: Visionサーバへ座標変換と深度取得を丸投げする
#     # =========================================================================
#     def run_detect_phase(self, request):
#         self._clear_targets()
        
#         if request is None or not hasattr(request, 'pixel_x') or not hasattr(request, 'pixel_y'):
#             raise ValueError('DetectTomato.srvのリクエストにpixel_xとpixel_yが必要です')
        
#         pixel_x, pixel_y = request.pixel_x, request.pixel_y
#         self.get_logger().info(f"iPadからピクセル座標を受信: X={pixel_x}, Y={pixel_y}")

#         # Visionサーバ(vision_service.py)にリクエストを作成
#         req = VisionService.Request()
#         req.task = "manual_detect"
#         req.direction = "f" 
#         req.pixel_x = int(pixel_x)
#         req.pixel_y = int(pixel_y)

#         # 安全な非同期通信(_call)でデッドロックを回避してVisionサーバの計算結果を待つ
#         res = self._call(self.vision_client, req, 'vision_service/manual_detect', 'vision')

#         if not getattr(res, 'detect_check', False) or not getattr(res, 'target_pos', None) or len(res.target_pos.tomato_data) == 0:
#             raise GatewayError("Visionサーバでの深度取得・座標変換に失敗しました。カメラの反射や画角外の可能性があります。")
        
#         # Visionサーバから、完璧に計算されたアーム座標(Zに実際の深度が反映済み)を受け取る
#         target = res.target_pos.tomato_data[0]
#         self.get_logger().info(f"Visionサーバからアーム座標を受信: X={target.x}, Y={target.y}, Z={target.z}")
        
#         # 検出フェーズでは動かさず、座標を保持するだけ (iPadの「収穫開始」ボタンで動く)
#         self.last_targets = [target]
#         self.last_pre_arm_height = SimpleNamespace(data=0)

#         return {
#             'found': True, 'targets': self.last_targets,
#             'message': f'Vision変換完了 (実深度適用済み) X:{target.x}, Y:{target.y}, Z:{target.z} を登録',
#         }

#     # =========================================================================
#     # 🌟 収穫フェーズ: 無限ループ(フリーズ)を完全に排除した安全なシーケンス
#     # =========================================================================
#     def run_harvest_phase(self):
#         logger = self.get_logger()
#         if not self.last_targets or self.last_pre_arm_height is None:
#             raise GatewayError('収穫対象がありません。先に検出してください')
            
#         targets = list(self.last_targets)
#         pre_h = self.last_pre_arm_height
#         self._clear_targets()
        
#         target = targets[0]
#         logger.info("アームを目標座標へ移動させます...")
        
#         # 1. アームの移動
#         arm_go_res = self.arm_send_request_target(target, pre_h)

#         if getattr(arm_go_res, 'task_comp', False):
#             try:
#                 # 2. 収穫アクション (順番に実行し、無限ループを排除)
#                 self.ee_send_request('1')   # 吸引開始
#                 self.ee_send_request('2')   # 顎閉じ (切断)
#                 self.arm_send_request_box() # ボックスへ移動
#                 self.ee_send_request('3')   # 顎開く (リリース)
#                 self.ee_send_request('0')   # 吸引停止
                
#                 # 3. アームを初期位置へ戻す
#                 self.arm_and_ee_send_request_init()
#                 return True, '収穫が完了し、アームが初期位置に戻りました'
                
#             except Exception as e:
#                 # 万が一途中でエラーが起きた場合の安全なリカバリ
#                 logger.error(f"収穫アクション中にエラー発生: {e}")
#                 self.ee_send_request('0') # 吸引停止
#                 self.ee_send_request('3') # 顎開き
#                 self.arm_send_request_init()
#                 raise GatewayError(f"収穫動作エラー: {e}")
                
#         else:
#             logger.warn("アームが目標座標へ到達できませんでした。収穫アクションを中止します。")
#             self.ee_send_request('0') # 吸引停止
#             self.ee_send_request('3') # 顎開き
#             self.arm_send_request_init()
#             return False, 'アーム移動に失敗したため、収穫を中止しました'

# def main(args=None):
#     rclpy.init(args=args)
#     node = HarvestGatewayNode()
#     executor = MultiThreadedExecutor(num_threads=4)
#     executor.add_node(node)
#     try:
#         executor.spin()
#     except KeyboardInterrupt:
#         node.get_logger().info('Shutting down')
#     finally:
#         executor.shutdown()
#         node.destroy_node()
#         if rclpy.ok():
#             rclpy.shutdown()

# if __name__ == '__main__':
#     main()




# ここから

# """Manual target gateway v10: direct hand-camera crosshair selection.

# Detection reads the hand-camera crosshair and converts its live Depth through the
# existing hand-camera-to-arm calibration. Harvest commands move_to_target directly.
# The end effector, rail, box sequence and automatic reset are not used.
# Timeouts do not cancel commands already sent to hardware.
# """

# import math
# import threading
# from pathlib import Path
# from types import SimpleNamespace

# import rclpy
# from rclpy.node import Node
# from rclpy.executors import MultiThreadedExecutor
# from rclpy.callback_groups import ReentrantCallbackGroup
# from rclpy.qos import qos_profile_services_default
# from toms_msg.srv import (
#     SuctionCommand, ArmService, VisionService,
#     DetectTomato, HarvestTomato, ResetArmEnd,
# )
# from toms_msg.msg import TomatoData


# VERSION = 'ipad-relay-hand-v10'


# class GatewayError(RuntimeError):
#     pass


# class HarvestGatewayNode(Node):
#     def __init__(self):
#         super().__init__('harvest_gateway_node')
#         self._operation_lock = threading.Lock()
#         self._fault_reason = ''
#         self.last_targets = []
#         self.last_pre_arm_height = None
#         self._timeouts = {}
#         self._service_discovery_timeout = float(
#             self.declare_parameter('service_discovery_timeout_sec', 10.0).value)
#         if (not math.isfinite(self._service_discovery_timeout)
#                 or self._service_discovery_timeout <= 0):
#             raise ValueError('service_discovery_timeout_sec must be finite and positive')
#         for key, default in [('arm', 60.0), ('ee', 15.0), ('vision', 15.0)]:
#             value = float(self.declare_parameter(f'{key}_timeout_sec', default).value)
#             if not math.isfinite(value) or value <= 0:
#                 raise ValueError(f'{key}_timeout_sec must be finite and positive')
#             self._timeouts[key] = value
#         # Service callbacks and client completions can run on separate workers.
#         self._service_group = ReentrantCallbackGroup()
#         self._client_group = ReentrantCallbackGroup()
#         self.detect_srv = self.create_service(
#             DetectTomato, 'detect_tomato', self.handle_detect_tomato,
#             callback_group=self._service_group)
#         self.harvest_srv = self.create_service(
#             HarvestTomato, 'harvest_tomato', self.handle_harvest_tomato,
#             callback_group=self._service_group)
#         self.reset_srv = self.create_service(
#             ResetArmEnd, 'reset_arm_end', self.reset_arm_end,
#             callback_group=self._service_group)
#         self.arm_client = self.create_client(
#             ArmService, 'arm_service', qos_profile=qos_profile_services_default,
#             callback_group=self._client_group)
#         self.vision_client = self.create_client(
#             VisionService, 'vision_service', qos_profile=qos_profile_services_default,
#             callback_group=self._client_group)
#         self.manual_hand_vision_client = self.create_client(
#             DetectTomato, 'vision_manual_detect_hand',
#             qos_profile=qos_profile_services_default,
#             callback_group=self._client_group)
#         self.get_logger().info(f'[{VERSION}] loaded from {Path(__file__).resolve()}')
#         self.get_logger().info(
#             'YOLOと俯瞰位置合わせを使わず、手先十字のDepth座標へ直接移動します。')

#     def _clear_targets(self):
#         self.last_targets = []

#     def _reset_manual_flow(self):
#         self.last_targets = []
#         self.last_pre_arm_height = None

#     def _fail_actuator(self, message):
#         self._fault_reason = message
#         self._reset_manual_flow()
#         self.get_logger().error(message)
#         raise GatewayError(message)

#     def _call(self, client, request, label, kind):
#         if self._fault_reason:
#             raise GatewayError(f'追加指令を保留中: {self._fault_reason}')
#         if not client.wait_for_service(timeout_sec=self._service_discovery_timeout):
#             raise GatewayError(
#                 f'{label}: {self._service_discovery_timeout:g}秒待っても'
#                 'サービスを発見できません')
#         timeout = self._timeouts[kind]
#         self.get_logger().info(f'[WAIT] {label} / 応答上限 {timeout:g}秒')
#         finished = threading.Event()
#         try:
#             future = client.call_async(request)
#             future.add_done_callback(lambda _: finished.set())
#             if not future.done():
#                 finished.wait(timeout)
#             if not future.done():
#                 message = (f'{label}: {timeout:g}秒以内に応答なし。'
#                            '送信済み指令は取り消していません。実機状態を確認してください')
#                 if kind != 'vision':
#                     self._fail_actuator(message)
#                 raise GatewayError(message)
#             result = future.result()
#             if result is None:
#                 raise RuntimeError('応答がNoneです')
#         except GatewayError:
#             raise
#         except Exception as error:
#             message = f'{label}: サービス例外 {type(error).__name__}: {error}'
#             if kind != 'vision':
#                 self._fail_actuator(message)
#             raise GatewayError(message) from error
#         self.get_logger().info(f'[DONE] {label}')
#         return result

#     def _arm(self, task, target=None, height=0):
#         request = ArmService.Request()
#         request.task = task
#         if target is not None:
#             request.target.x = target.x
#             request.target.y = target.y
#             request.target.z = target.z + height
#             request.target.approach_direction = target.approach_direction
#             self.get_logger().info(
#                 f'[TARGET] task={task} x={request.target.x} y={request.target.y} '
#                 f'z={request.target.z} direction={request.target.approach_direction}')
#         result = self._call(self.arm_client, request, f'arm_service/{task}', 'arm')
#         if not getattr(result, 'task_comp', False):
#             self._fail_actuator(f'arm_service/{task}: task_compがFalse（または項目なし）です')
#         return result

#     def arm_send_request_home(self, target):
#         return self._arm('home', target)

#     def arm_send_request_target(self, target, pre_h):
#         return self._arm('move_to_target', target, pre_h.data)

#     def arm_send_request_box(self):
#         return self._arm('move_to_box')

#     def arm_send_request_init(self):
#         result = self._arm('init_arm')
#         self._clear_targets()
#         return result

#     def vision_send_request_check(self):
#         request = VisionService.Request()
#         request.task = 'detect_check'
#         request.direction = 'f'
#         return self._call(self.vision_client, request, 'vision_service/detect_check', 'vision')

#     def vision_send_request_tompos(self):
#         request = VisionService.Request()
#         request.task = 'req_tomato_pose'
#         request.direction = 'f'
#         return self._call(self.vision_client, request, 'vision_service/req_tomato_pose', 'vision')

#     def _handle(self, request, response, action, detect=False):
#         if detect:
#             response.found = False
#             response.candidate_count = 0
#             response.x, response.y, response.z = [], [], []
#         else:
#             response.success = False
#         if not self._operation_lock.acquire(blocking=False):
#             response.message = '別の検出・収穫・リセットを処理中です'
#             return response
#         try:
#             if self._fault_reason:
#                 raise GatewayError(f'追加指令を保留中: {self._fault_reason}')
#             result = action(request)
#             if detect:
#                 targets = result['targets']
#                 response.found = result['found']
#                 response.candidate_count = len(targets)
#                 response.x = [float(t.x) for t in targets]
#                 response.y = [float(t.y) for t in targets]
#                 response.z = [float(t.z) for t in targets]
#                 response.message = result['message']
#             else:
#                 response.success, response.message = result
#             self.get_logger().info(f'[RESPONSE] {response.message}')
#         except (GatewayError, ValueError) as error:
#             self._clear_targets()
#             response.message = str(error)
#             self.get_logger().error(f'[RESPONSE ERROR] {error}')
#         except Exception as error:
#             self._clear_targets()
#             self._fault_reason = f'{type(error).__name__}: {error}'
#             response.message = f'処理例外: {self._fault_reason}。実機状態を確認してください'
#             self.get_logger().error(response.message)
#         finally:
#             self._operation_lock.release()
#         return response

#     def handle_detect_tomato(self, request, response):
#         return self._handle(request, response, self.run_detect_phase, detect=True)

#     def handle_harvest_tomato(self, request, response):
#         return self._handle(request, response, lambda _: self.run_harvest_phase())

#     def reset_arm_end(self, request, response):
#         def reset(_):
#             self.arm_send_request_init()
#             self._reset_manual_flow()
#             return True, 'リセット完了'
#         return self._handle(request, response, reset)

#     def run_detect_phase(self, request):
#         if request is None or not hasattr(request, 'pixel_x') or not hasattr(request, 'pixel_y'):
#             raise ValueError('DetectTomato.srvのリクエストにpixel_xとpixel_yが必要です')
#         pixel_x, pixel_y = request.pixel_x, request.pixel_y
#         if not (math.isfinite(pixel_x) and math.isfinite(pixel_y)
#                 and int(pixel_x) == pixel_x and int(pixel_y) == pixel_y
#                 and pixel_x >= 0 and pixel_y >= 0):
#             raise ValueError('pixel_xとpixel_yには0以上の整数が必要です')

#         manual_request = DetectTomato.Request()
#         manual_request.pixel_x = int(pixel_x)
#         manual_request.pixel_y = int(pixel_y)

#         result = self._call(
#             self.manual_hand_vision_client,
#             manual_request,
#             'vision_manual_detect_hand',
#             'vision')
#         if (not getattr(result, 'found', False)
#                 or getattr(result, 'candidate_count', 0) < 1
#                 or not result.x or not result.y or not result.z):
#             self._clear_targets()
#             return {
#                 'found': False,
#                 'targets': [],
#                 'message': (getattr(result, 'message', '')
#                             or '手先Depthから座標を取得できませんでした'),
#             }

#         target = TomatoData()
#         target.x = int(round(result.x[0]))
#         target.y = int(round(result.y[0]))
#         target.z = int(round(result.z[0]))
#         target.approach_direction = 90
#         self.get_logger().info(
#             f'[PIXEL] stage=hand ({pixel_x},{pixel_y}) -> arm XYZ '
#             f'({target.x},{target.y},{target.z}); {VERSION}')
#         self.last_targets = [target]
#         self.last_pre_arm_height = SimpleNamespace(data=0)
#         message = (
#             f'手先アーム座標 X:{target.x}, Y:{target.y}, Z:{target.z} を登録。'
#             '「収穫開始」でこの座標へ移動します')
#         return {
#             'found': True, 'targets': self.last_targets,
#             'message': message,
#         }

#     def run_harvest_phase(self):
#         if not self.last_targets or self.last_pre_arm_height is None:
#             raise GatewayError('手先視点で十字を合わせ、先に「トマト検出」を押してください')
#         target = self.last_targets[0]
#         pre_h = self.last_pre_arm_height
#         self._clear_targets()
#         self.get_logger().info(
#             f'[HAND DIRECT] target x={target.x} y={target.y} z={target.z} '
#             f'direction={target.approach_direction}')
#         self.arm_send_request_target(target, pre_h)
#         self._reset_manual_flow()
#         return True, '手先十字で指定した目標座標へのアーム移動完了'


# def main(args=None):
#     rclpy.init(args=args)
#     node = HarvestGatewayNode()
#     executor = MultiThreadedExecutor(num_threads=4)
#     executor.add_node(node)
#     try:
#         executor.spin()
#     except KeyboardInterrupt:
#         node.get_logger().info('Shutting down')
#     finally:
#         executor.shutdown()
#         node.destroy_node()
#         if rclpy.ok():
#             rclpy.shutdown()


# if __name__ == '__main__':
#     main()



# """Manual target gateway v10: direct hand-camera crosshair selection.

# Detection reads the hand-camera crosshair and converts its live Depth through the
# existing hand-camera-to-arm calibration. Harvest commands move_to_target directly.
# The end effector, rail, box sequence and automatic reset are not used.
# Timeouts do not cancel commands already sent to hardware.
# """

# import math
# import threading
# from pathlib import Path
# from types import SimpleNamespace
# import yaml

# import rclpy
# from rclpy.node import Node
# from rclpy.executors import MultiThreadedExecutor
# from rclpy.callback_groups import ReentrantCallbackGroup
# from rclpy.qos import qos_profile_services_default
# from toms_msg.srv import (
#     SuctionCommand, ArmService, VisionService,
#     DetectTomato, HarvestTomato, ResetArmEnd,
# )
# from toms_msg.msg import TomatoData


# VERSION = 'ipad-relay-hand-v11-range-guard'


# class GatewayError(RuntimeError):
#     pass


# class HarvestGatewayNode(Node):
#     def __init__(self):
#         super().__init__('harvest_gateway_node')
#         self._operation_lock = threading.Lock()
#         self._fault_reason = ''
#         self.last_targets = []
#         self.last_pre_arm_height = None
#         with open('/home/ylab/hibikino_toms_ws/module/set_params.yaml', 'r') as stream:
#             params = yaml.safe_load(stream)
#         ik_params = params['ik_solver_params']
#         self._arm_lengths = (
#             float(ik_params['Link1']),
#             float(ik_params['Link2']),
#             float(ik_params['Link3']),
#             float(ik_params['Link4']))
#         self._z_range = (0.0, 450.0)
#         self._timeouts = {}
#         self._service_discovery_timeout = float(
#             self.declare_parameter('service_discovery_timeout_sec', 10.0).value)
#         if (not math.isfinite(self._service_discovery_timeout)
#                 or self._service_discovery_timeout <= 0):
#             raise ValueError('service_discovery_timeout_sec must be finite and positive')
#         for key, default in [('arm', 60.0), ('ee', 15.0), ('vision', 15.0)]:
#             value = float(self.declare_parameter(f'{key}_timeout_sec', default).value)
#             if not math.isfinite(value) or value <= 0:
#                 raise ValueError(f'{key}_timeout_sec must be finite and positive')
#             self._timeouts[key] = value
#         # Service callbacks and client completions can run on separate workers.
#         self._service_group = ReentrantCallbackGroup()
#         self._client_group = ReentrantCallbackGroup()
#         self.detect_srv = self.create_service(
#             DetectTomato, 'detect_tomato', self.handle_detect_tomato,
#             callback_group=self._service_group)
#         self.harvest_srv = self.create_service(
#             HarvestTomato, 'harvest_tomato', self.handle_harvest_tomato,
#             callback_group=self._service_group)
#         self.reset_srv = self.create_service(
#             ResetArmEnd, 'reset_arm_end', self.reset_arm_end,
#             callback_group=self._service_group)
#         self.arm_client = self.create_client(
#             ArmService, 'arm_service', qos_profile=qos_profile_services_default,
#             callback_group=self._client_group)
#         self.vision_client = self.create_client(
#             VisionService, 'vision_service', qos_profile=qos_profile_services_default,
#             callback_group=self._client_group)
#         self.manual_hand_vision_client = self.create_client(
#             DetectTomato, 'vision_manual_detect_hand',
#             qos_profile=qos_profile_services_default,
#             callback_group=self._client_group)
#         self.get_logger().info(f'[{VERSION}] loaded from {Path(__file__).resolve()}')
#         self.get_logger().info(
#             'YOLOと俯瞰位置合わせを使わず、手先十字のDepth座標へ直接移動します。')

#     def _clear_targets(self):
#         self.last_targets = []

#     def _target_range_error(self, target):
#         """Return a user-facing reason when a target cannot be harvested."""
#         values = (
#             float(target.x), float(target.y), float(target.z),
#             float(target.approach_direction))
#         if not all(math.isfinite(value) for value in values):
#             return f'座標にNaNまたはinfがあります: {values}'

#         x, y, z, approach_deg = values
#         z_min, z_max = self._z_range
#         if not z_min <= z <= z_max:
#             return f'Z={z:.0f}mmはZ軸範囲{z_min:.0f}〜{z_max:.0f}mmの外です'

#         link1, link2, link3, link4 = self._arm_lengths
#         approach_rad = math.radians(approach_deg)
#         wrist_x = x - link4 * math.cos(approach_rad)
#         wrist_y = y - link4 * math.sin(approach_rad)
#         wrist_distance = math.hypot(wrist_x, wrist_y)
#         effective_link1 = math.hypot(link1, link2)
#         wrist_min = abs(effective_link1 - link3)
#         wrist_max = effective_link1 + link3
#         if not wrist_min <= wrist_distance <= wrist_max:
#             return (
#                 f'目標(X={x:.0f}, Y={y:.0f})はアーム範囲外です '
#                 f'(手首距離={wrist_distance:.0f}mm、許容={wrist_min:.0f}〜{wrist_max:.0f}mm)')
#         return None

#     def _reset_manual_flow(self):
#         self.last_targets = []
#         self.last_pre_arm_height = None

#     def _fail_actuator(self, message):
#         self._fault_reason = message
#         self._reset_manual_flow()
#         self.get_logger().error(message)
#         raise GatewayError(message)

#     def _call(self, client, request, label, kind):
#         if self._fault_reason:
#             raise GatewayError(f'追加指令を保留中: {self._fault_reason}')
#         if not client.wait_for_service(timeout_sec=self._service_discovery_timeout):
#             raise GatewayError(
#                 f'{label}: {self._service_discovery_timeout:g}秒待っても'
#                 'サービスを発見できません')
#         timeout = self._timeouts[kind]
#         self.get_logger().info(f'[WAIT] {label} / 応答上限 {timeout:g}秒')
#         finished = threading.Event()
#         try:
#             future = client.call_async(request)
#             future.add_done_callback(lambda _: finished.set())
#             if not future.done():
#                 finished.wait(timeout)
#             if not future.done():
#                 message = (f'{label}: {timeout:g}秒以内に応答なし。'
#                            '送信済み指令は取り消していません。実機状態を確認してください')
#                 if kind != 'vision':
#                     self._fail_actuator(message)
#                 raise GatewayError(message)
#             result = future.result()
#             if result is None:
#                 raise RuntimeError('応答がNoneです')
#         except GatewayError:
#             raise
#         except Exception as error:
#             message = f'{label}: サービス例外 {type(error).__name__}: {error}'
#             if kind != 'vision':
#                 self._fail_actuator(message)
#             raise GatewayError(message) from error
#         self.get_logger().info(f'[DONE] {label}')
#         return result

#     def _arm(self, task, target=None, height=0):
#         request = ArmService.Request()
#         request.task = task
#         if target is not None:
#             request.target.x = target.x
#             request.target.y = target.y
#             request.target.z = target.z + height
#             request.target.approach_direction = target.approach_direction
#             self.get_logger().info(
#                 f'[TARGET] task={task} x={request.target.x} y={request.target.y} '
#                 f'z={request.target.z} direction={request.target.approach_direction}')
#         result = self._call(self.arm_client, request, f'arm_service/{task}', 'arm')
#         if not getattr(result, 'task_comp', False):
#             self._fail_actuator(f'arm_service/{task}: task_compがFalse（または項目なし）です')
#         return result

#     def arm_send_request_home(self, target):
#         return self._arm('home', target)

#     def arm_send_request_target(self, target, pre_h):
#         return self._arm('move_to_target', target, pre_h.data)

#     def arm_send_request_box(self):
#         return self._arm('move_to_box')

#     def arm_send_request_init(self):
#         result = self._arm('init_arm')
#         self._clear_targets()
#         return result

#     def vision_send_request_check(self):
#         request = VisionService.Request()
#         request.task = 'detect_check'
#         request.direction = 'f'
#         return self._call(self.vision_client, request, 'vision_service/detect_check', 'vision')

#     def vision_send_request_tompos(self):
#         request = VisionService.Request()
#         request.task = 'req_tomato_pose'
#         request.direction = 'f'
#         return self._call(self.vision_client, request, 'vision_service/req_tomato_pose', 'vision')

#     def _handle(self, request, response, action, detect=False):
#         if detect:
#             response.found = False
#             response.candidate_count = 0
#             response.x, response.y, response.z = [], [], []
#         else:
#             response.success = False
#         if not self._operation_lock.acquire(blocking=False):
#             response.message = '別の検出・収穫・リセットを処理中です'
#             return response
#         try:
#             if self._fault_reason:
#                 raise GatewayError(f'追加指令を保留中: {self._fault_reason}')
#             result = action(request)
#             if detect:
#                 targets = result['targets']
#                 response.found = result['found']
#                 response.candidate_count = len(targets)
#                 response.x = [float(t.x) for t in targets]
#                 response.y = [float(t.y) for t in targets]
#                 response.z = [float(t.z) for t in targets]
#                 response.message = result['message']
#             else:
#                 response.success, response.message = result
#             self.get_logger().info(f'[RESPONSE] {response.message}')
#         except (GatewayError, ValueError) as error:
#             self._clear_targets()
#             response.message = str(error)
#             self.get_logger().error(f'[RESPONSE ERROR] {error}')
#         except Exception as error:
#             self._clear_targets()
#             self._fault_reason = f'{type(error).__name__}: {error}'
#             response.message = f'処理例外: {self._fault_reason}。実機状態を確認してください'
#             self.get_logger().error(response.message)
#         finally:
#             self._operation_lock.release()
#         return response

#     def handle_detect_tomato(self, request, response):
#         return self._handle(request, response, self.run_detect_phase, detect=True)

#     def handle_harvest_tomato(self, request, response):
#         return self._handle(request, response, lambda _: self.run_harvest_phase())

#     def reset_arm_end(self, request, response):
#         def reset(_):
#             self.arm_send_request_init()
#             self._reset_manual_flow()
#             return True, 'リセット完了'
#         return self._handle(request, response, reset)

#     def run_detect_phase(self, request):
#         if request is None or not hasattr(request, 'pixel_x') or not hasattr(request, 'pixel_y'):
#             raise ValueError('DetectTomato.srvのリクエストにpixel_xとpixel_yが必要です')
#         pixel_x, pixel_y = request.pixel_x, request.pixel_y
#         if not (math.isfinite(pixel_x) and math.isfinite(pixel_y)
#                 and int(pixel_x) == pixel_x and int(pixel_y) == pixel_y
#                 and pixel_x >= 0 and pixel_y >= 0):
#             raise ValueError('pixel_xとpixel_yには0以上の整数が必要です')

#         manual_request = DetectTomato.Request()
#         manual_request.pixel_x = int(pixel_x)
#         manual_request.pixel_y = int(pixel_y)

#         result = self._call(
#             self.manual_hand_vision_client,
#             manual_request,
#             'vision_manual_detect_hand',
#             'vision')
#         if (not getattr(result, 'found', False)
#                 or getattr(result, 'candidate_count', 0) < 1
#                 or not result.x or not result.y or not result.z):
#             self._clear_targets()
#             return {
#                 'found': False,
#                 'targets': [],
#                 'message': (getattr(result, 'message', '')
#                             or '手先Depthから座標を取得できませんでした'),
#             }

#         target = TomatoData()
#         target.x = int(round(result.x[0]))
#         target.y = int(round(result.y[0]))
#         target.z = int(round(result.z[0]))
#         target.approach_direction = 90
#         self.get_logger().info(
#             f'[PIXEL] stage=hand ({pixel_x},{pixel_y}) -> arm XYZ '
#             f'({target.x},{target.y},{target.z}); {VERSION}')

#         range_error = self._target_range_error(target)
#         if range_error:
#             self._clear_targets()
#             self.last_pre_arm_height = None
#             self.get_logger().warning(f'[TARGET REJECTED] {range_error}')
#             return {
#                 'found': False,
#                 'targets': [],
#                 'message': f'収穫範囲外: {range_error}。十字を近いトマトへ合わせて再検出してください',
#             }

#         self.last_targets = [target]
#         self.last_pre_arm_height = SimpleNamespace(data=0)
#         message = (
#             f'手先アーム座標 X:{target.x}, Y:{target.y}, Z:{target.z} を登録。'
#             '「収穫開始」でこの座標へ移動します')
#         return {
#             'found': True, 'targets': self.last_targets,
#             'message': message,
#         }

#     def run_harvest_phase(self):
#         if not self.last_targets or self.last_pre_arm_height is None:
#             raise GatewayError('手先視点で十字を合わせ、先に「トマト検出」を押してください')
#         target = self.last_targets[0]
#         pre_h = self.last_pre_arm_height
#         self._clear_targets()
#         self.get_logger().info(
#             f'[HAND DIRECT] target x={target.x} y={target.y} z={target.z} '
#             f'direction={target.approach_direction}')
#         self.arm_send_request_target(target, pre_h)
#         self._reset_manual_flow()
#         return True, '手先十字で指定した目標座標へのアーム移動完了'


# def main(args=None):
#     rclpy.init(args=args)
#     node = HarvestGatewayNode()
#     executor = MultiThreadedExecutor(num_threads=4)
#     executor.add_node(node)
#     try:
#         executor.spin()
#     except KeyboardInterrupt:
#         node.get_logger().info('Shutting down')
#     finally:
#         executor.shutdown()
#         node.destroy_node()
#         if rclpy.ok():
#             rclpy.shutdown()


# if __name__ == '__main__':
#     main()















# 10-07
"""Manual target gateway v12: direct hand-camera target range guard.

Detection reads the hand-camera crosshair and converts its live Depth through the
existing hand-camera-to-arm calibration. Harvest commands move_to_target directly.
The end effector, rail, box sequence and automatic reset are not used.
Timeouts do not cancel commands already sent to hardware.
"""

import math
import threading
from pathlib import Path
from types import SimpleNamespace
import yaml

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.qos import qos_profile_services_default
from toms_msg.srv import (
    SuctionCommand, ArmService, VisionService,
    DetectTomato, HarvestTomato, ResetArmEnd,
)
from toms_msg.msg import TomatoData


VERSION = 'ipad-relay-hand-v12-range-guard'


class GatewayError(RuntimeError):
    pass


class HarvestGatewayNode(Node):
    def __init__(self):
        super().__init__('harvest_gateway_node')
        self._operation_lock = threading.Lock()
        self._fault_reason = ''
        self.last_targets = []
        self.last_pre_arm_height = None
        with open('/home/ylab/hibikino_toms_ws/module/set_params.yaml', 'r') as stream:
            params = yaml.safe_load(stream)
        ik_params = params['ik_solver_params']
        self._arm_lengths = (
            float(ik_params['Link1']),
            float(ik_params['Link2']),
            float(ik_params['Link3']),
            float(ik_params['Link4']))
        self._z_range = (0.0, 450.0)
        self._timeouts = {}
        self._service_discovery_timeout = float(
            self.declare_parameter('service_discovery_timeout_sec', 10.0).value)
        if (not math.isfinite(self._service_discovery_timeout)
                or self._service_discovery_timeout <= 0):
            raise ValueError('service_discovery_timeout_sec must be finite and positive')
        for key, default in [('arm', 60.0), ('ee', 15.0), ('vision', 15.0)]:
            value = float(self.declare_parameter(f'{key}_timeout_sec', default).value)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f'{key}_timeout_sec must be finite and positive')
            self._timeouts[key] = value
        # Service callbacks and client completions can run on separate workers.
        self._service_group = ReentrantCallbackGroup()
        self._client_group = ReentrantCallbackGroup()
        self.detect_srv = self.create_service(
            DetectTomato, 'detect_tomato', self.handle_detect_tomato,
            callback_group=self._service_group)
        self.harvest_srv = self.create_service(
            HarvestTomato, 'harvest_tomato', self.handle_harvest_tomato,
            callback_group=self._service_group)
        self.reset_srv = self.create_service(
            ResetArmEnd, 'reset_arm_end', self.reset_arm_end,
            callback_group=self._service_group)
        self.arm_client = self.create_client(
            ArmService, 'arm_service', qos_profile=qos_profile_services_default,
            callback_group=self._client_group)
        self.vision_client = self.create_client(
            VisionService, 'vision_service', qos_profile=qos_profile_services_default,
            callback_group=self._client_group)
        self.manual_hand_vision_client = self.create_client(
            DetectTomato, 'vision_manual_detect_hand',
            qos_profile=qos_profile_services_default,
            callback_group=self._client_group)
        self.get_logger().info(f'[{VERSION}] loaded from {Path(__file__).resolve()}')
        self.get_logger().info(
            'YOLOと俯瞰位置合わせを使わず、手先十字のDepth座標へ直接移動します。')

    def _clear_targets(self):
        self.last_targets = []

    def _target_range_error(self, target):
        """Return a user-facing reason when a target cannot be harvested."""
        values = (
            float(target.x), float(target.y), float(target.z),
            float(target.approach_direction))
        if not all(math.isfinite(value) for value in values):
            return f'座標にNaNまたはinfがあります: {values}'

        x, y, z, approach_deg = values
        z_min, z_max = self._z_range
        if not z_min <= z <= z_max:
            return f'Z={z:.0f}mmはZ軸範囲{z_min:.0f}〜{z_max:.0f}mmの外です'

        link1, link2, link3, link4 = self._arm_lengths
        approach_rad = math.radians(approach_deg)
        wrist_x = x - link4 * math.cos(approach_rad)
        wrist_y = y - link4 * math.sin(approach_rad)
        wrist_distance = math.hypot(wrist_x, wrist_y)
        effective_link1 = math.hypot(link1, link2)
        wrist_min = abs(effective_link1 - link3)
        wrist_max = effective_link1 + link3
        if not wrist_min <= wrist_distance <= wrist_max:
            return (
                f'目標(X={x:.0f}, Y={y:.0f})はアーム範囲外です '
                f'(手首距離={wrist_distance:.0f}mm、許容={wrist_min:.0f}〜{wrist_max:.0f}mm)')
        return None

    def _reset_manual_flow(self):
        self.last_targets = []
        self.last_pre_arm_height = None

    def _fail_actuator(self, message):
        self._fault_reason = message
        self._reset_manual_flow()
        self.get_logger().error(message)
        raise GatewayError(message)

    def _call(self, client, request, label, kind):
        if self._fault_reason:
            raise GatewayError(f'追加指令を保留中: {self._fault_reason}')
        if not client.wait_for_service(timeout_sec=self._service_discovery_timeout):
            raise GatewayError(
                f'{label}: {self._service_discovery_timeout:g}秒待っても'
                'サービスを発見できません')
        timeout = self._timeouts[kind]
        self.get_logger().info(f'[WAIT] {label} / 応答上限 {timeout:g}秒')
        finished = threading.Event()
        try:
            future = client.call_async(request)
            future.add_done_callback(lambda _: finished.set())
            if not future.done():
                finished.wait(timeout)
            if not future.done():
                message = (f'{label}: {timeout:g}秒以内に応答なし。'
                           '送信済み指令は取り消していません。実機状態を確認してください')
                if kind != 'vision':
                    self._fail_actuator(message)
                raise GatewayError(message)
            result = future.result()
            if result is None:
                raise RuntimeError('応答がNoneです')
        except GatewayError:
            raise
        except Exception as error:
            message = f'{label}: サービス例外 {type(error).__name__}: {error}'
            if kind != 'vision':
                self._fail_actuator(message)
            raise GatewayError(message) from error
        self.get_logger().info(f'[DONE] {label}')
        return result

    def _arm(self, task, target=None, height=0):
        request = ArmService.Request()
        request.task = task
        if target is not None:
            request.target.x = target.x
            request.target.y = target.y
            request.target.z = target.z + height
            request.target.approach_direction = target.approach_direction
            self.get_logger().info(
                f'[TARGET] task={task} x={request.target.x} y={request.target.y} '
                f'z={request.target.z} direction={request.target.approach_direction}')
        result = self._call(self.arm_client, request, f'arm_service/{task}', 'arm')
        if not getattr(result, 'task_comp', False):
            self._fail_actuator(f'arm_service/{task}: task_compがFalse（または項目なし）です')
        return result

    def arm_send_request_home(self, target):
        return self._arm('home', target)

    def arm_send_request_target(self, target, pre_h):
        return self._arm('move_to_target', target, pre_h.data)

    def arm_send_request_box(self):
        return self._arm('move_to_box')

    def arm_send_request_init(self):
        result = self._arm('init_arm')
        self._clear_targets()
        return result

    def vision_send_request_check(self):
        request = VisionService.Request()
        request.task = 'detect_check'
        request.direction = 'f'
        return self._call(self.vision_client, request, 'vision_service/detect_check', 'vision')

    def vision_send_request_tompos(self):
        request = VisionService.Request()
        request.task = 'req_tomato_pose'
        request.direction = 'f'
        return self._call(self.vision_client, request, 'vision_service/req_tomato_pose', 'vision')

    def _handle(self, request, response, action, detect=False):
        if detect:
            response.found = False
            response.candidate_count = 0
            response.x, response.y, response.z = [], [], []
        else:
            response.success = False
        if not self._operation_lock.acquire(blocking=False):
            response.message = '別の検出・収穫・リセットを処理中です'
            return response
        try:
            if self._fault_reason:
                raise GatewayError(f'追加指令を保留中: {self._fault_reason}')
            result = action(request)
            if detect:
                targets = result['targets']
                response.found = result['found']
                response.candidate_count = len(targets)
                response.x = [float(t.x) for t in targets]
                response.y = [float(t.y) for t in targets]
                response.z = [float(t.z) for t in targets]
                response.message = result['message']
            else:
                response.success, response.message = result
            self.get_logger().info(f'[RESPONSE] {response.message}')
        except (GatewayError, ValueError) as error:
            self._clear_targets()
            response.message = str(error)
            self.get_logger().error(f'[RESPONSE ERROR] {error}')
        except Exception as error:
            self._clear_targets()
            self._fault_reason = f'{type(error).__name__}: {error}'
            response.message = f'処理例外: {self._fault_reason}。実機状態を確認してください'
            self.get_logger().error(response.message)
        finally:
            self._operation_lock.release()
        return response

    def handle_detect_tomato(self, request, response):
        return self._handle(request, response, self.run_detect_phase, detect=True)

    def handle_harvest_tomato(self, request, response):
        return self._handle(request, response, lambda _: self.run_harvest_phase())

    def reset_arm_end(self, request, response):
        def reset(_):
            self.arm_send_request_init()
            self._reset_manual_flow()
            return True, 'リセット完了'
        return self._handle(request, response, reset)

    def run_detect_phase(self, request):
        if request is None or not hasattr(request, 'pixel_x') or not hasattr(request, 'pixel_y'):
            raise ValueError('DetectTomato.srvのリクエストにpixel_xとpixel_yが必要です')
        pixel_x, pixel_y = request.pixel_x, request.pixel_y
        if not (math.isfinite(pixel_x) and math.isfinite(pixel_y)
                and int(pixel_x) == pixel_x and int(pixel_y) == pixel_y
                and pixel_x >= 0 and pixel_y >= 0):
            raise ValueError('pixel_xとpixel_yには0以上の整数が必要です')

        manual_request = DetectTomato.Request()
        manual_request.pixel_x = int(pixel_x)
        manual_request.pixel_y = int(pixel_y)

        result = self._call(
            self.manual_hand_vision_client,
            manual_request,
            'vision_manual_detect_hand',
            'vision')
        if (not getattr(result, 'found', False)
                or getattr(result, 'candidate_count', 0) < 1
                or not result.x or not result.y or not result.z):
            self._clear_targets()
            return {
                'found': False,
                'targets': [],
                'message': (getattr(result, 'message', '')
                            or '手先Depthから座標を取得できませんでした'),
            }

        target = TomatoData()
        target.x = int(round(result.x[0]))
        target.y = int(round(result.y[0]))
        target.z = int(round(result.z[0]))
        target.approach_direction = 90
        self.get_logger().info(
            f'[PIXEL] stage=hand ({pixel_x},{pixel_y}) -> arm XYZ '
            f'({target.x},{target.y},{target.z}); {VERSION}')

        range_error = self._target_range_error(target)
        if range_error:
            self._clear_targets()
            self.last_pre_arm_height = None
            self.get_logger().warning(f'[TARGET REJECTED] {range_error}')
            return {
                'found': False,
                'targets': [],
                'message': f'収穫範囲外: {range_error}。十字を近いトマトへ合わせて再検出してください',
            }

        self.last_targets = [target]
        self.last_pre_arm_height = SimpleNamespace(data=0)
        message = (
            f'手先アーム座標 X:{target.x}, Y:{target.y}, Z:{target.z} を登録。'
            '「収穫開始」でこの座標へ移動します')
        return {
            'found': True, 'targets': self.last_targets,
            'message': message,
        }

    def run_harvest_phase(self):
        if not self.last_targets or self.last_pre_arm_height is None:
            raise GatewayError('手先視点で十字を合わせ、先に「トマト検出」を押してください')
        target = self.last_targets[0]
        pre_h = self.last_pre_arm_height
        self._clear_targets()
        self.get_logger().info(
            f'[HAND DIRECT] target x={target.x} y={target.y} z={target.z} '
            f'direction={target.approach_direction}')
        self.arm_send_request_target(target, pre_h)
        # 目標到達後は、既存のinit_arm手順でアームを初期位置へ戻し、
        # 続けてZ軸をリミットスイッチ基準位置へ戻す。
        self.get_logger().info('[AUTO RETURN] 収穫目標への移動後、初期位置へ戻します')
        self.arm_send_request_init()
        self._reset_manual_flow()
        return True, '目標へ移動後、アームとZ軸を初期位置へ戻しました'


def main(args=None):
    rclpy.init(args=args)
    node = HarvestGatewayNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down')
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
