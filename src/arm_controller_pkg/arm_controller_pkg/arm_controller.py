# import rclpy  # ROS2のPythonモジュールをインポート
# from rclpy.node import Node 
# # rclpy.qos から qos_profile_services_default をインポート
# from rclpy.qos import qos_profile_services_default

# import sys
# import numpy as np
# import yaml


# sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg")
# #from suction_unit import Suction_Unit
# sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/modules")
# #from .modules.ik_solver_ver4 import InverseKinematicsSolver
# from .modules.ik_solver_arm2 import InverseKinematicsSolver
# # from .modules.ik_solver_arm2_2 import InverseKinematicsSolver
# #from .modules.ik_solver_1201 import InverseKinematicsSolver
# # from .modules.route_planner_lib_ver2 import RoutePlanner
# from .modules.route_planner_simple_no_obs import RoutePlanner
# # from .modules.motor_controller_module import MotorController
# from .modules.motor_controller_module_5motor import MotorController
# from .modules.z_axis_controller_module import ZAxis
# from toms_msg.srv import ArmService, EndEffectorService
# import time
# from std_msgs.msg import Int32

# from .modules.angle_converter import AngleConverter
# """
# Arm_service_server
# アーム制御ノード

# @author : 吉永
# """

# """
# service通信

# [input]

# [output] 
# harvest success decision
# """


# class Arm_Controller(Node):  
#     def __init__(self):
#         super().__init__('arm_controller')
        
#         #service
#         self.srv = self.create_service(
#             ArmService,
#             "arm_service",
#             self.arm_host_server,
#             # QoSプロファイルを明示的に指定
#             qos_profile=qos_profile_services_default)

#         # パラメータ設定用のyamlファイル
#         yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
#         # YAMLファイルの読み込み
#         params = self.load_yaml(yaml_path)
#         dxl_params = params["dxl_params"]
#         ik_params = params["ik_solver_params"]
#         z_params = params["ZAxis_params"]
#         vision_params = params["vision_params"]
#         trans_params = params["coordinate_transform_params"]
        
#         self.BACK_CAM_HEIGHT = z_params["BACK_CAM_HEIGHT"]
        
#         # manipulator_function
#         self.arm_controller = MotorController(dxl_params)
#         self.z_controller = ZAxis(z_params)
#         self.solver = InverseKinematicsSolver(ik_params)
#         self.planner = RoutePlanner(params)
#         self.angle_converter = AngleConverter(dxl_params)
        
#         self.HOME_ANGLE = dxl_params["DXL_HOME_ANGLE"]
        
#         self.approach_ang_base = vision_params["APPROACH_ANG"]
#         self.HAND_CAM_ANG = trans_params["CAM_ANGLE"]
#         self.HAND_CAM_HEIGHT = trans_params["Z_DIFF_CAM2EE"]
        
#         # 何かしらの実験や検証を行う際のフラグに使ってください
#         self.EXPERIMENT_MODE = params["EXPERIMENT_MODE"]
        
#         INIT_X = params["arm_params"]["INIT_X"]
#         INIT_Y = params["arm_params"]["INIT_Y"]
#         INIT_ANG = params["arm_params"]["INIT_ANG"]
        
#         # ※アームの初期位置を変更する場合以下を実行すること※
#         """
#         HOME_ANGLE_IN_ARM = self.angle_converter.dxl_ang2ik_ang(self.HOME_ANGLE) # 順運動学を解くためにモータの角度系からアームの角度系に変換
#         # yamlファイルのアーム座標系でのホームポジションの各関節角度を書き換え
#         params["arm_params"]["HOME_ANGLE_IN_ARM"] = HOME_ANGLE_IN_ARM
        
#         # 初期位置と初期角度の設定
#         INIT_X, INIT_Y, INIT_ANG = self.solver.forward_kinematics(HOME_ANGLE_IN_ARM[0], HOME_ANGLE_IN_ARM[1], HOME_ANGLE_IN_ARM[2])# 初期位置と初期角度の取得
#         # yamlファイルの初期位置・初期角度を書き換え
#         params["arm_params"]["INIT_X"] = INIT_X
#         params["arm_params"]["INIT_Y"] = INIT_Y
#         params["arm_params"]["INIT_ANG"] = INIT_ANG
        
#         # 書き換えた内容を元のYAMLファイルに反映
#         with open(yaml_path, "w") as file:
#             yaml.dump(params, file, default_flow_style=False)
#         """
#         self.INIT_POS = [INIT_X, INIT_Y]
#         self.INIT_ANG = INIT_ANG
        
#         self.error_num = 0

#     @staticmethod
#     def load_yaml(file_path):
#         """YAMLファイルを読み込むヘルパー関数"""
#         try:
#             with open(file_path, "r") as file:
#                 return yaml.safe_load(file)
#         except FileNotFoundError:
#             raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
#         except yaml.YAMLError as e:
#             raise ValueError(f"YAMLファイルの解析エラー: {e}")

#     def move_to_target(self,target):
#         self.error_num = 0
#         target_x, target_y, target_z, alpha = target.x, target.y, target.z, target.approach_direction
#         motor_angles_list = []
#         route_list = np.empty((0, 2))
        
#         goal_posi = [target_x, target_y]
#         obstacles_posi = []
#         self.get_logger().info(f"goal_posi: {goal_posi}")
#         self.get_logger().info(f"approach_ang: {alpha}")

#         while True:
#             # 現在のモータの角度読み取り
#             pre_angles = self.arm_controller.read_positions()
#             # Dynamixel上の角度へ変更(アーム座標系じゃない)
#             pre_angles = [self.arm_controller.position_to_angle(pos) for pos in pre_angles]
#             pre_angles.pop(1)
#             # ↓モータ5個用
#             pre_angles.pop(2)
#             self.get_logger().info(f"Dynamixel上の現在位置: {pre_angles}")
#             check_threshold = all(
#                     abs(home - pre_angle) <= 10
#                     for home, pre_angle in zip(self.HOME_ANGLE, pre_angles)
#                 )
            
#             if check_threshold: # アームがホームポジションにあるとき
#                 self.planner.reset(self.INIT_POS, self.INIT_ANG)
#                 # アーム座標系の経路計画座標と角度のリストが返ってくる
#                 route_list = self.planner.solve_rrt(goal_posi, alpha, obstacles_posi) # 25/2/18時点：solve_rrt→簡素化されたシンプルな経路計画(障害物なし前提のrrtすらしていない単純経路生成処理ver.)
#                 self.get_logger().info(f"\n経路: \n{route_list}")
#                 """
#                 route_init = [self.INIT_POS[0], self.INIT_POS[1], self.INIT_ANG]
#                 route = np.hstack((target_x, target_y, approach_ang))
#                 route_list = np.vstack((route_init, route))
#                 print(f"route_list; {route_list}")
#                 """
#                 if route_list is not None:
#                     # 各経路点から次の経路点までの逆運動学解いて、各モータの目標位置を取得
#                     current_motor_angles = pre_angles # Dynamixel上の角度(モータ座標系)
#                     current_EE_posi_angle = route_list[0] # アーム座標の初期手先座標と角度 
                    
#                     current_motor_angles = self.angle_converter.dxl_ang2ik_ang(current_motor_angles) # Dynamixel上の角度からアーム座標系に変換
#                     # self.get_logger().info(f"\nアーム座標系での現在のアーム角度: \n{current_motor_angles}")
#                     for i in range(len(route_list) - 1):                        
#                         next_posi_EEangle, next_motor_angles, solve_done = self.solver.solve_ik(current_EE_posi_angle, route_list[i+1], current_motor_angles)
#                         # self.get_logger().info(f"\nnext_posi_EEangle, next_motor_angles: \n{next_posi_EEangle, next_motor_angles}")
                        
#                         next_motor_angles, check_angle = self.angle_converter.ik_ang2dxl_ang(next_motor_angles) # アーム座標系の角度からモータの角度系に変換する関数
#                         print(next_motor_angles)
#                         if solve_done == False:
#                             self.get_logger().info("特異点を通過 → このトマトは収穫できる位置にありません。")
#                             self.error_num = 1
#                             motor_angles_list = []
#                             break
#                         if check_angle == False:
#                             self.get_logger().info("この経路はモータ角度が可動範囲外です。")
#                             self.error_num = 2
#                             motor_angles_list = []
#                             break
#                         motor_angles_list.append(next_motor_angles)
#                         current_EE_posi_angle = next_posi_EEangle
#                         next_motor_angles = self.angle_converter.dxl_ang2ik_ang(next_motor_angles) # モータの角度系から逆運動学の角度系に変換する関数
#                         current_motor_angles = next_motor_angles
#                         # ｰーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーー
#                 else:
#                     continue
#             else:
#                 self.get_logger().info("アームがホームポジションではありません。")
#                 self.arm_controller.init_pos()
#                 continue

#             #　Z軸の制御
#             time.sleep(0.5)
#             self.z_controller.power_enable(0)
#             self.z_controller.power_enable(1)
#             self.z_controller.move2target(target_z)
            
#             # 一行ずつ、各モータの目標位置に各モータを制御
#             if len(motor_angles_list) != 0:
#                 send_angle_datas = []
#                 for i, motor_angles in enumerate(motor_angles_list):
#                     print(f"motor_angles: {motor_angles}")
#                     if motor_angles == None:
#                         return False
#                     send_data = self.arm_controller.move_motors(motor_angles, task="target")
#                     send_angle_datas.append(send_data)
#                 self.get_logger().info(f"アーム指令 : {send_angle_datas}")
#                 return True
#             else :
#                 return False
    
#     def cutting(self, target):
#         target_x, target_y, target_z, alpha = target.x, target.y, target.z, target.approach_direction
#         print(f"x, y, x, alpha: {target_x, target_y, target_z, alpha}")
#         action_dis = 75
#         if alpha == int(self.approach_ang_base):
#             cut_posi = [target_x - action_dis, target_y - action_dis]
#             beta = 45
        
#         elif alpha == int(180 - int(self.approach_ang_base)):
#             cut_posi = [target_x + action_dis, target_y - action_dis]
#             beta = 135
        
#         else :
#             # cut_posi = [target_x, target_y - action_dis]
#             # beta = alpha
#             cut_posi = [target_x , target_y - action_dis]
#             beta = alpha
        
#         # 現在のモータの角度読み取り
#         pre_angles = self.arm_controller.read_positions()
#         # Dynamixel上の角度へ変更(アーム座標系じゃない)
#         pre_angles = [self.arm_controller.position_to_angle(pos) for pos in pre_angles]
#         pre_angles.pop(1)
#         pre_angles.pop(2)
        
#         route_list = np.empty((0, 2))
#         route_list = [[target_x, target_y, alpha], [cut_posi[0], cut_posi[1], beta]]
        
#         current_motor_angles = self.angle_converter.dxl_ang2ik_ang(pre_angles) # Dynamixel上の角度からアーム座標系に変換
#         current_EE_posi_angle = route_list[0] # アーム座標の初期手先座標と角度 
        
#         next_posi_EEangle, next_motor_angles, solve_done = self.solver.solve_ik(current_EE_posi_angle, route_list[1], current_motor_angles)
#         motor_angles, check_ang = self.angle_converter.ik_ang2dxl_ang(next_motor_angles) # アーム座標系の角度からモータの角度系に変換する関数
#         if solve_done == False:
#             self.get_logger().info("特異点を通過 → 噛み切り動作できる位置ではありません。")
#             return False
#         if check_ang == False:
#             self.get_logger().info("この経路はモータ角度が可動範囲外です。")
#             return False
        
#         self.arm_controller.move_motors(motor_angles, task="cutting")
#         return True

#     def debug_ik_result(self,theta1, theta2, theta3):
#         self.get_logger().info("モータ角度") 
#         self.get_logger().info("---------------------------")
#         self.get_logger().info(f"θ1: {round((theta1))} degrees")
#         self.get_logger().info(f"θ2: {round((theta2))} degrees")
#         self.get_logger().info(f"θ3: {round((theta3))} degrees")
#         self.get_logger().info(f"α: {round((theta1) + (theta2) + (theta3))} degrees")
#         # self.get_logger().info("アーム位置")
#         # self.get_logger().info("---------------------------")
#         # x,z = self.solver.forward_kinematics(theta1, theta2, theta3)
#         # self.get_logger().info(f"x : {round(x)} z : {round(z)}")

#     def arm_host_server(self,request, response):
#         if request.task == "init_arm":
#             # ログを追加
#             self.get_logger().info("'init_arm' request received. Starting arm init...")
#             self.arm_controller.init_pos()
            
#             # ログを追加
#             self.get_logger().info("Arm init complete. Starting Z-axis init...")
#             self.z_controller.init_pos()
            
#             # ログを追加
#             self.get_logger().info("Z-axis init complete. Sending response.")
            
#             self.get_logger().info("初期化完了")
#             response.task_comp = True 

#         elif request.task == "move_to_target":
#             target = request.target
#             self.get_logger().info("move_to_target")
#             task_comp = self.move_to_target(target)
#             if self.error_num != 0:
#                 match self.error_num:
#                     case 1:
#                         self.get_logger().info("特異点通過により失敗")
#                     case 2:
#                         self.get_logger().info("モータ角度の動作範囲外により失敗")
#             response.task_comp = task_comp
        
#         elif request.task == "move_to_box":
#             target = request.target
#             task_comp = self.cutting(target)
#             if task_comp == False:
#                 self.get_logger().info("噛み切り動作できませんでした") 
#             self.arm_controller.move_to_box()
#             response.task_comp = True
            
#         elif request.task == "home":
#             if self.EXPERIMENT_MODE: # 2025/2/1（吉永）：実験のため、zのhome_posの高さを手入力で設定
#                 tom_hight_from_z = request.target.z
#             else:
#                 first_tom_pos_from_backcam = request.target
#                 # カメラ座標系
#                 tom_hight_from_backcam = first_tom_pos_from_backcam.y
#                 self.get_logger().info(f"端のトマトの高さ(カメラ座標)：{tom_hight_from_backcam}") 
#                 # カメラ座標系
#                 if self.HAND_CAM_ANG == 0: # 手先カメラのマウントが垂直タイプの場合
#                     tom_hight_from_z = self.BACK_CAM_HEIGHT - tom_hight_from_backcam - (130 + self.HAND_CAM_HEIGHT) # 130…アーム高さの基準になる点（リミットスイッチとの接触点）からEE中心までのz方向の差
#                 else :
#                     tom_hight_from_z = self.BACK_CAM_HEIGHT - tom_hight_from_backcam
            
#             self.get_logger().info(f"端のトマトの高さ(Z座標)：{tom_hight_from_z}") 
            
#             self.arm_controller.move_to_home()
#             self.z_controller.home_pos(tom_hight_from_z) 
#             response.task_comp = True
#             tom_hight = Int32()
#             tom_hight.data = int(tom_hight_from_z)
#             response.tom_hight = tom_hight
#         return response
    
# def main():
#     rclpy.init() 
#     node=Arm_Controller() 
#     try :
#         rclpy.spin(node) 
#     except KeyboardInterrupt :
#         print("\nCtrl+C has been entered")
#     else:
#         rclpy.shutdown()
#     finally:
#         node.destroy_node()

# if __name__ == '__main__':
#     main()














# ここから別の

# import rclpy  # ROS2のPythonモジュールをインポート
# from rclpy.node import Node 
# # rclpy.qos から qos_profile_services_default をインポート
# from rclpy.qos import qos_profile_services_default

# import sys
# import numpy as np
# import yaml


# sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg")
# #from suction_unit import Suction_Unit
# sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/modules")
# #from .modules.ik_solver_ver4 import InverseKinematicsSolver
# from .modules.ik_solver_arm2 import InverseKinematicsSolver
# # from .modules.ik_solver_arm2_2 import InverseKinematicsSolver
# #from .modules.ik_solver_1201 import InverseKinematicsSolver
# # from .modules.route_planner_lib_ver2 import RoutePlanner
# from .modules.route_planner_simple_no_obs import RoutePlanner
# # from .modules.motor_controller_module import MotorController
# from .modules.motor_controller_module_5motor import MotorController
# from .modules.z_axis_controller_module import ZAxis
# from toms_msg.srv import ArmService, EndEffectorService
# import time
# from std_msgs.msg import Int32

# from .modules.angle_converter import AngleConverter
# """
# Arm_service_server
# アーム制御ノード

# @author : 吉永
# """

# """
# service通信

# [input]

# [output] 
# harvest success decision
# """


# class Arm_Controller(Node):  
#     def __init__(self):
#         super().__init__('arm_controller')
        
#         #service
#         self.srv = self.create_service(
#             ArmService,
#             "arm_service",
#             self.arm_host_server,
#             # QoSプロファイルを明示的に指定
#             qos_profile=qos_profile_services_default)

#         # パラメータ設定用のyamlファイル
#         yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
#         # YAMLファイルの読み込み
#         params = self.load_yaml(yaml_path)
#         dxl_params = params["dxl_params"]
#         ik_params = params["ik_solver_params"]
#         z_params = params["ZAxis_params"]
#         vision_params = params["vision_params"]
#         trans_params = params["coordinate_transform_params"]
        
#         self.BACK_CAM_HEIGHT = z_params["BACK_CAM_HEIGHT"]
        
#         # manipulator_function
#         self.arm_controller = MotorController(dxl_params)
#         self.z_controller = ZAxis(z_params)
#         self.solver = InverseKinematicsSolver(ik_params)
#         self.planner = RoutePlanner(params)
#         self.angle_converter = AngleConverter(dxl_params)
        
#         self.HOME_ANGLE = dxl_params["DXL_HOME_ANGLE"]
        
#         self.approach_ang_base = vision_params["APPROACH_ANG"]
#         self.HAND_CAM_ANG = trans_params["CAM_ANGLE"]
#         self.HAND_CAM_HEIGHT = trans_params["Z_DIFF_CAM2EE"]
        
#         # 何かしらの実験や検証を行う際のフラグに使ってください
#         self.EXPERIMENT_MODE = params["EXPERIMENT_MODE"]
        
#         INIT_X = params["arm_params"]["INIT_X"]
#         INIT_Y = params["arm_params"]["INIT_Y"]
#         INIT_ANG = params["arm_params"]["INIT_ANG"]
        
#         # ※アームの初期位置を変更する場合以下を実行すること※
#         """
#         HOME_ANGLE_IN_ARM = self.angle_converter.dxl_ang2ik_ang(self.HOME_ANGLE) # 順運動学を解くためにモータの角度系からアームの角度系に変換
#         # yamlファイルのアーム座標系でのホームポジションの各関節角度を書き換え
#         params["arm_params"]["HOME_ANGLE_IN_ARM"] = HOME_ANGLE_IN_ARM
        
#         # 初期位置と初期角度の設定
#         INIT_X, INIT_Y, INIT_ANG = self.solver.forward_kinematics(HOME_ANGLE_IN_ARM[0], HOME_ANGLE_IN_ARM[1], HOME_ANGLE_IN_ARM[2])# 初期位置と初期角度の取得
#         # yamlファイルの初期位置・初期角度を書き換え
#         params["arm_params"]["INIT_X"] = INIT_X
#         params["arm_params"]["INIT_Y"] = INIT_Y
#         params["arm_params"]["INIT_ANG"] = INIT_ANG
        
#         # 書き換えた内容を元のYAMLファイルに反映
#         with open(yaml_path, "w") as file:
#             yaml.dump(params, file, default_flow_style=False)
#         """
#         self.INIT_POS = [INIT_X, INIT_Y]
#         self.INIT_ANG = INIT_ANG
        
#         self.error_num = 0

#         # サービスコールを無期限に待たせないため、ホーム復帰の再試行回数を制限する。
#         self.HOME_RECOVERY_ATTEMPTS = 2

#     @staticmethod
#     def load_yaml(file_path):
#         """YAMLファイルを読み込むヘルパー関数"""
#         try:
#             with open(file_path, "r") as file:
#                 return yaml.safe_load(file)
#         except FileNotFoundError:
#             raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
#         except yaml.YAMLError as e:
#             raise ValueError(f"YAMLファイルの解析エラー: {e}")

#     def move_to_target(self, target):
#         self.error_num = 0
#         target_x, target_y, target_z, alpha = target.x, target.y, target.z, target.approach_direction

#         target_values = [target_x, target_y, target_z, alpha]
#         if not all(np.isfinite(value) for value in target_values):
#             self.get_logger().error(f"目標値にNaNまたはinfがあります: {target_values}")
#             self.error_num = 6
#             return False
#         if target_z < 0 or target_z > 450:
#             self.get_logger().error(
#                 f"Z軸目標位置{target_z}mmは可動範囲0..450mmの外です")
#             self.error_num = 4
#             return False
        
#         goal_posi = [target_x, target_y]
#         obstacles_posi = []
#         self.get_logger().info(f"goal_posi: {goal_posi}")
#         self.get_logger().info(f"approach_ang: {alpha}")

#         pre_angles = None
#         for home_attempt in range(self.HOME_RECOVERY_ATTEMPTS + 1):
#             # 現在のモータの角度読み取り
#             pre_angles = self.arm_controller.read_positions()
#             # Dynamixel上の角度へ変更(アーム座標系じゃない)
#             pre_angles = [self.arm_controller.position_to_angle(pos) for pos in pre_angles]
#             pre_angles.pop(1)
#             # ↓モータ5個用
#             pre_angles.pop(2)
#             self.get_logger().info(f"Dynamixel上の現在位置: {pre_angles}")
#             check_threshold = all(
#                     abs(home - pre_angle) <= 10
#                     for home, pre_angle in zip(self.HOME_ANGLE, pre_angles)
#                 )
            
#             if check_threshold:
#                 break

#             if home_attempt >= self.HOME_RECOVERY_ATTEMPTS:
#                 self.get_logger().error(
#                     "ホーム位置へ復帰できません。Dynamixelの電源・通信・干渉を確認してください。")
#                 self.error_num = 3
#                 return False

#             self.get_logger().warning(
#                 f"アームがホーム位置ではありません。復帰を試します "
#                 f"({home_attempt + 1}/{self.HOME_RECOVERY_ATTEMPTS})")
#             if self.arm_controller.init_pos() is not True:
#                 self.get_logger().error("ホーム位置への移動がタイムアウトしました。")
#                 self.error_num = 3
#                 return False

#         self.planner.reset(self.INIT_POS, self.INIT_ANG)
#         route_list = self.planner.solve_rrt(goal_posi, alpha, obstacles_posi)
#         self.get_logger().info(f"\n経路: \n{route_list}")
#         if route_list is None or len(route_list) < 2:
#             self.get_logger().error("目標までの経路を生成できませんでした。")
#             self.error_num = 7
#             return False

#         motor_angles_list = []
#         current_motor_angles = self.angle_converter.dxl_ang2ik_ang(pre_angles)
#         current_EE_posi_angle = route_list[0]
#         for i in range(len(route_list) - 1):
#             next_posi_EEangle, next_motor_angles, solve_done = self.solver.solve_ik(
#                 current_EE_posi_angle, route_list[i + 1], current_motor_angles)

#             if solve_done is False:
#                 self.get_logger().error(
#                     "特異点を通過するため、このトマトは収穫できる位置にありません。")
#                 self.error_num = 1
#                 return False

#             next_motor_angles, check_angle = self.angle_converter.ik_ang2dxl_ang(
#                 next_motor_angles)
#             if check_angle is False:
#                 self.get_logger().error("この経路はモータ角度が可動範囲外です。")
#                 self.error_num = 2
#                 return False
#             if next_motor_angles is None:
#                 self.get_logger().error("逆運動学の結果が空です。")
#                 self.error_num = 1
#                 return False

#             motor_angles_list.append(next_motor_angles)
#             current_EE_posi_angle = next_posi_EEangle
#             current_motor_angles = self.angle_converter.dxl_ang2ik_ang(
#                 next_motor_angles)

#         if not motor_angles_list:
#             self.get_logger().error("送信できるアーム経路がありません。")
#             self.error_num = 7
#             return False

#         # move2target内でZ軸電源を有効化する。Pico無応答時は例外で即座に失敗へ戻る。
#         self.z_controller.move2target(target_z)

#         for motor_angles in motor_angles_list:
#             self.get_logger().info(f"motor_angles: {motor_angles}")
#             if self.arm_controller.move_motors(motor_angles, task="target") is not True:
#                 self.get_logger().error("Dynamixelが目標角度へ到達できませんでした。")
#                 self.error_num = 5
#                 return False

#         self.get_logger().info(
#             f"アーム指令完了: 経路点{len(motor_angles_list)}件")
#         return True
    
#     def cutting(self, target):
#         target_x, target_y, target_z, alpha = target.x, target.y, target.z, target.approach_direction
#         print(f"x, y, x, alpha: {target_x, target_y, target_z, alpha}")
#         action_dis = 75
#         if alpha == int(self.approach_ang_base):
#             cut_posi = [target_x - action_dis, target_y - action_dis]
#             beta = 45
        
#         elif alpha == int(180 - int(self.approach_ang_base)):
#             cut_posi = [target_x + action_dis, target_y - action_dis]
#             beta = 135
        
#         else :
#             # cut_posi = [target_x, target_y - action_dis]
#             # beta = alpha
#             cut_posi = [target_x , target_y - action_dis]
#             beta = alpha
        
#         # 現在のモータの角度読み取り
#         pre_angles = self.arm_controller.read_positions()
#         # Dynamixel上の角度へ変更(アーム座標系じゃない)
#         pre_angles = [self.arm_controller.position_to_angle(pos) for pos in pre_angles]
#         pre_angles.pop(1)
#         pre_angles.pop(2)
        
#         route_list = np.empty((0, 2))
#         route_list = [[target_x, target_y, alpha], [cut_posi[0], cut_posi[1], beta]]
        
#         current_motor_angles = self.angle_converter.dxl_ang2ik_ang(pre_angles) # Dynamixel上の角度からアーム座標系に変換
#         current_EE_posi_angle = route_list[0] # アーム座標の初期手先座標と角度 
        
#         next_posi_EEangle, next_motor_angles, solve_done = self.solver.solve_ik(current_EE_posi_angle, route_list[1], current_motor_angles)
#         motor_angles, check_ang = self.angle_converter.ik_ang2dxl_ang(next_motor_angles) # アーム座標系の角度からモータの角度系に変換する関数
#         if solve_done == False:
#             self.get_logger().info("特異点を通過 → 噛み切り動作できる位置ではありません。")
#             return False
#         if check_ang == False:
#             self.get_logger().info("この経路はモータ角度が可動範囲外です。")
#             return False
        
#         return self.arm_controller.move_motors(motor_angles, task="cutting") is True

#     def debug_ik_result(self,theta1, theta2, theta3):
#         self.get_logger().info("モータ角度") 
#         self.get_logger().info("---------------------------")
#         self.get_logger().info(f"θ1: {round((theta1))} degrees")
#         self.get_logger().info(f"θ2: {round((theta2))} degrees")
#         self.get_logger().info(f"θ3: {round((theta3))} degrees")
#         self.get_logger().info(f"α: {round((theta1) + (theta2) + (theta3))} degrees")
#         # self.get_logger().info("アーム位置")
#         # self.get_logger().info("---------------------------")
#         # x,z = self.solver.forward_kinematics(theta1, theta2, theta3)
#         # self.get_logger().info(f"x : {round(x)} z : {round(z)}")

#     def arm_host_server(self, request, response):
#         # 例外をROSサービスの失敗応答へ変換し、呼び出し側を待たせ続けない。
#         response.task_comp = False
#         try:
#             if request.task == "init_arm":
#                 self.get_logger().info("'init_arm' request received. Starting arm init...")
#                 if self.arm_controller.init_pos() is not True:
#                     raise RuntimeError("Dynamixelの初期位置移動がタイムアウトしました")

#                 self.get_logger().info("Arm init complete. Starting Z-axis init...")
#                 self.z_controller.init_pos()
#                 self.get_logger().info("初期化完了")
#                 response.task_comp = True

#             elif request.task == "move_to_target":
#                 self.get_logger().info("move_to_target")
#                 response.task_comp = self.move_to_target(request.target)
#                 error_messages = {
#                     1: "特異点通過により失敗",
#                     2: "モータ角度の動作範囲外により失敗",
#                     3: "ホーム位置への復帰失敗",
#                     4: "Z軸目標位置が可動範囲外",
#                     5: "Dynamixelの目標位置到達タイムアウト",
#                     6: "目標座標が不正",
#                     7: "経路生成失敗",
#                 }
#                 if self.error_num in error_messages:
#                     self.get_logger().error(error_messages[self.error_num])

#             elif request.task == "move_to_box":
#                 cutting_done = self.cutting(request.target)
#                 if not cutting_done:
#                     self.get_logger().error("噛み切り動作できませんでした")
#                     return response
#                 response.task_comp = self.arm_controller.move_to_box() is True

#             elif request.task == "home":
#                 if self.EXPERIMENT_MODE:
#                     tom_hight_from_z = request.target.z
#                 else:
#                     tom_hight_from_backcam = request.target.y
#                     self.get_logger().info(
#                         f"端のトマトの高さ(カメラ座標)：{tom_hight_from_backcam}")
#                     if self.HAND_CAM_ANG == 0:
#                         tom_hight_from_z = (
#                             self.BACK_CAM_HEIGHT - tom_hight_from_backcam
#                             - (130 + self.HAND_CAM_HEIGHT))
#                     else:
#                         tom_hight_from_z = self.BACK_CAM_HEIGHT - tom_hight_from_backcam

#                 self.get_logger().info(
#                     f"端のトマトの高さ(Z座標)：{tom_hight_from_z}")
#                 arm_done = self.arm_controller.move_to_home() is True
#                 if not arm_done:
#                     raise RuntimeError("Dynamixelのホーム移動がタイムアウトしました")
#                 self.z_controller.home_pos(tom_hight_from_z)
#                 response.task_comp = True
#                 tom_hight = Int32()
#                 tom_hight.data = int(tom_hight_from_z)
#                 response.tom_hight = tom_hight

#             else:
#                 self.get_logger().error(f"未対応のアームタスクです: {request.task!r}")

#         except Exception as error:
#             self.get_logger().error(
#                 f"アームサービス失敗 ({type(error).__name__}): {error}")
#             response.task_comp = False

#         return response
    
# def main():
#     rclpy.init() 
#     node=Arm_Controller() 
#     try :
#         rclpy.spin(node) 
#     except KeyboardInterrupt :
#         print("\nCtrl+C has been entered")
#     else:
#         rclpy.shutdown()
#     finally:
#         node.destroy_node()

# if __name__ == '__main__':
#     main()





# import rclpy  # ROS2のPythonモジュールをインポート
# from rclpy.node import Node 
# # rclpy.qos から qos_profile_services_default をインポート
# from rclpy.qos import qos_profile_services_default

# import sys
# import numpy as np
# import yaml


# sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg")
# #from suction_unit import Suction_Unit
# sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/modules")
# #from .modules.ik_solver_ver4 import InverseKinematicsSolver
# from .modules.ik_solver_arm2 import InverseKinematicsSolver
# # from .modules.ik_solver_arm2_2 import InverseKinematicsSolver
# #from .modules.ik_solver_1201 import InverseKinematicsSolver
# # from .modules.route_planner_lib_ver2 import RoutePlanner
# from .modules.route_planner_simple_no_obs import RoutePlanner
# # from .modules.motor_controller_module import MotorController
# from .modules.motor_controller_module_5motor import MotorController
# from .modules.z_axis_controller_module import ZAxis
# from toms_msg.srv import ArmService, EndEffectorService
# import time
# from std_msgs.msg import Int32

# from .modules.angle_converter import AngleConverter
# """
# Arm_service_server
# アーム制御ノード

# @author : 吉永
# """

# """
# service通信

# [input]

# [output] 
# harvest success decision
# """


# class Arm_Controller(Node):  
#     def __init__(self):
#         super().__init__('arm_controller')
        
#         #service
#         self.srv = self.create_service(
#             ArmService,
#             "arm_service",
#             self.arm_host_server,
#             # QoSプロファイルを明示的に指定
#             qos_profile=qos_profile_services_default)

#         # パラメータ設定用のyamlファイル
#         yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
#         # YAMLファイルの読み込み
#         params = self.load_yaml(yaml_path)
#         dxl_params = params["dxl_params"]
#         ik_params = params["ik_solver_params"]
#         z_params = params["ZAxis_params"]
#         vision_params = params["vision_params"]
#         trans_params = params["coordinate_transform_params"]
        
#         self.BACK_CAM_HEIGHT = z_params["BACK_CAM_HEIGHT"]
        
#         # manipulator_function
#         self.arm_controller = MotorController(dxl_params)
#         self.z_controller = ZAxis(z_params)
#         self.solver = InverseKinematicsSolver(ik_params)
#         self.planner = RoutePlanner(params)
#         self.angle_converter = AngleConverter(dxl_params)
        
#         self.HOME_ANGLE = dxl_params["DXL_HOME_ANGLE"]
        
#         self.approach_ang_base = vision_params["APPROACH_ANG"]
#         self.HAND_CAM_ANG = trans_params["CAM_ANGLE"]
#         self.HAND_CAM_HEIGHT = trans_params["Z_DIFF_CAM2EE"]
        
#         # 何かしらの実験や検証を行う際のフラグに使ってください
#         self.EXPERIMENT_MODE = params["EXPERIMENT_MODE"]
        
#         INIT_X = params["arm_params"]["INIT_X"]
#         INIT_Y = params["arm_params"]["INIT_Y"]
#         INIT_ANG = params["arm_params"]["INIT_ANG"]
        
#         # ※アームの初期位置を変更する場合以下を実行すること※
#         """
#         HOME_ANGLE_IN_ARM = self.angle_converter.dxl_ang2ik_ang(self.HOME_ANGLE) # 順運動学を解くためにモータの角度系からアームの角度系に変換
#         # yamlファイルのアーム座標系でのホームポジションの各関節角度を書き換え
#         params["arm_params"]["HOME_ANGLE_IN_ARM"] = HOME_ANGLE_IN_ARM
        
#         # 初期位置と初期角度の設定
#         INIT_X, INIT_Y, INIT_ANG = self.solver.forward_kinematics(HOME_ANGLE_IN_ARM[0], HOME_ANGLE_IN_ARM[1], HOME_ANGLE_IN_ARM[2])# 初期位置と初期角度の取得
#         # yamlファイルの初期位置・初期角度を書き換え
#         params["arm_params"]["INIT_X"] = INIT_X
#         params["arm_params"]["INIT_Y"] = INIT_Y
#         params["arm_params"]["INIT_ANG"] = INIT_ANG
        
#         # 書き換えた内容を元のYAMLファイルに反映
#         with open(yaml_path, "w") as file:
#             yaml.dump(params, file, default_flow_style=False)
#         """
#         self.INIT_POS = [INIT_X, INIT_Y]
#         self.INIT_ANG = INIT_ANG
        
#         self.error_num = 0

#         # サービスコールを無期限に待たせないため、ホーム復帰の再試行回数を制限する。
#         self.HOME_RECOVERY_ATTEMPTS = 2

#     @staticmethod
#     def load_yaml(file_path):
#         """YAMLファイルを読み込むヘルパー関数"""
#         try:
#             with open(file_path, "r") as file:
#                 return yaml.safe_load(file)
#         except FileNotFoundError:
#             raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
#         except yaml.YAMLError as e:
#             raise ValueError(f"YAMLファイルの解析エラー: {e}")

#     def move_to_target(self, target):
#         self.error_num = 0
#         target_x, target_y, target_z, alpha = target.x, target.y, target.z, target.approach_direction

#         target_values = [target_x, target_y, target_z, alpha]
#         if not all(np.isfinite(value) for value in target_values):
#             self.get_logger().error(f"目標値にNaNまたはinfがあります: {target_values}")
#             self.error_num = 6
#             return False
#         if target_z < 0 or target_z > 450:
#             self.get_logger().error(
#                 f"Z軸目標位置{target_z}mmは可動範囲0..450mmの外です")
#             self.error_num = 4
#             return False
        
#         goal_posi = [target_x, target_y]
#         obstacles_posi = []
#         self.get_logger().info(f"goal_posi: {goal_posi}")
#         self.get_logger().info(f"approach_ang: {alpha}")

#         pre_angles = None
#         for home_attempt in range(self.HOME_RECOVERY_ATTEMPTS + 1):
#             # 現在のモータの角度読み取り
#             pre_angles = self.arm_controller.read_positions()
#             # Dynamixel上の角度へ変更(アーム座標系じゃない)
#             pre_angles = [self.arm_controller.position_to_angle(pos) for pos in pre_angles]
#             pre_angles.pop(1)
#             # ↓モータ5個用
#             pre_angles.pop(2)
#             self.get_logger().info(f"Dynamixel上の現在位置: {pre_angles}")
#             check_threshold = all(
#                     abs(home - pre_angle) <= 10
#                     for home, pre_angle in zip(self.HOME_ANGLE, pre_angles)
#                 )
            
#             if check_threshold:
#                 break

#             if home_attempt >= self.HOME_RECOVERY_ATTEMPTS:
#                 self.get_logger().error(
#                     "ホーム位置へ復帰できません。Dynamixelの電源・通信・干渉を確認してください。")
#                 self.error_num = 3
#                 return False

#             self.get_logger().warning(
#                 f"アームがホーム位置ではありません。復帰を試します "
#                 f"({home_attempt + 1}/{self.HOME_RECOVERY_ATTEMPTS})")
#             if self.arm_controller.init_pos() is not True:
#                 self.get_logger().error("ホーム位置への移動がタイムアウトしました。")
#                 self.error_num = 3
#                 return False

#         self.planner.reset(self.INIT_POS, self.INIT_ANG)
#         route_list = self.planner.solve_rrt(goal_posi, alpha, obstacles_posi)
#         self.get_logger().info(f"\n経路: \n{route_list}")
#         if route_list is None or len(route_list) < 2:
#             self.get_logger().error("目標までの経路を生成できませんでした。")
#             self.error_num = 7
#             return False

#         motor_angles_list = []
#         current_motor_angles = self.angle_converter.dxl_ang2ik_ang(pre_angles)
#         current_EE_posi_angle = route_list[0]
#         for i in range(len(route_list) - 1):
#             next_posi_EEangle, next_motor_angles, solve_done = self.solver.solve_ik(
#                 current_EE_posi_angle, route_list[i + 1], current_motor_angles)

#             if solve_done is False:
#                 self.get_logger().error(
#                     "逆運動学を解けませんでした。目標が可動範囲外、特異点付近、または計算未収束です。")
#                 self.error_num = 1
#                 return False

#             next_motor_angles, check_angle = self.angle_converter.ik_ang2dxl_ang(
#                 next_motor_angles)
#             if check_angle is False:
#                 self.get_logger().error("この経路はモータ角度が可動範囲外です。")
#                 self.error_num = 2
#                 return False
#             if next_motor_angles is None:
#                 self.get_logger().error("逆運動学の結果が空です。")
#                 self.error_num = 1
#                 return False

#             motor_angles_list.append(next_motor_angles)
#             current_EE_posi_angle = next_posi_EEangle
#             current_motor_angles = self.angle_converter.dxl_ang2ik_ang(
#                 next_motor_angles)

#         if not motor_angles_list:
#             self.get_logger().error("送信できるアーム経路がありません。")
#             self.error_num = 7
#             return False

#         # move2target内でZ軸電源を有効化する。Pico無応答時は例外で即座に失敗へ戻る。
#         self.z_controller.move2target(target_z)

#         for motor_angles in motor_angles_list:
#             self.get_logger().info(f"motor_angles: {motor_angles}")
#             if self.arm_controller.move_motors(motor_angles, task="target") is not True:
#                 self.get_logger().error("Dynamixelが目標角度へ到達できませんでした。")
#                 self.error_num = 5
#                 return False

#         self.get_logger().info(
#             f"アーム指令完了: 経路点{len(motor_angles_list)}件")
#         return True
    
#     def cutting(self, target):
#         target_x, target_y, target_z, alpha = target.x, target.y, target.z, target.approach_direction
#         print(f"x, y, x, alpha: {target_x, target_y, target_z, alpha}")
#         action_dis = 75
#         if alpha == int(self.approach_ang_base):
#             cut_posi = [target_x - action_dis, target_y - action_dis]
#             beta = 45
        
#         elif alpha == int(180 - int(self.approach_ang_base)):
#             cut_posi = [target_x + action_dis, target_y - action_dis]
#             beta = 135
        
#         else :
#             # cut_posi = [target_x, target_y - action_dis]
#             # beta = alpha
#             cut_posi = [target_x , target_y - action_dis]
#             beta = alpha
        
#         # 現在のモータの角度読み取り
#         pre_angles = self.arm_controller.read_positions()
#         # Dynamixel上の角度へ変更(アーム座標系じゃない)
#         pre_angles = [self.arm_controller.position_to_angle(pos) for pos in pre_angles]
#         pre_angles.pop(1)
#         pre_angles.pop(2)
        
#         route_list = np.empty((0, 2))
#         route_list = [[target_x, target_y, alpha], [cut_posi[0], cut_posi[1], beta]]
        
#         current_motor_angles = self.angle_converter.dxl_ang2ik_ang(pre_angles) # Dynamixel上の角度からアーム座標系に変換
#         current_EE_posi_angle = route_list[0] # アーム座標の初期手先座標と角度 
        
#         next_posi_EEangle, next_motor_angles, solve_done = self.solver.solve_ik(current_EE_posi_angle, route_list[1], current_motor_angles)
#         motor_angles, check_ang = self.angle_converter.ik_ang2dxl_ang(next_motor_angles) # アーム座標系の角度からモータの角度系に変換する関数
#         if solve_done == False:
#             self.get_logger().info("特異点を通過 → 噛み切り動作できる位置ではありません。")
#             return False
#         if check_ang == False:
#             self.get_logger().info("この経路はモータ角度が可動範囲外です。")
#             return False
        
#         return self.arm_controller.move_motors(motor_angles, task="cutting") is True

#     def debug_ik_result(self,theta1, theta2, theta3):
#         self.get_logger().info("モータ角度") 
#         self.get_logger().info("---------------------------")
#         self.get_logger().info(f"θ1: {round((theta1))} degrees")
#         self.get_logger().info(f"θ2: {round((theta2))} degrees")
#         self.get_logger().info(f"θ3: {round((theta3))} degrees")
#         self.get_logger().info(f"α: {round((theta1) + (theta2) + (theta3))} degrees")
#         # self.get_logger().info("アーム位置")
#         # self.get_logger().info("---------------------------")
#         # x,z = self.solver.forward_kinematics(theta1, theta2, theta3)
#         # self.get_logger().info(f"x : {round(x)} z : {round(z)}")

#     def arm_host_server(self, request, response):
#         # 例外をROSサービスの失敗応答へ変換し、呼び出し側を待たせ続けない。
#         response.task_comp = False
#         try:
#             if request.task == "init_arm":
#                 self.get_logger().info("'init_arm' request received. Starting arm init...")
#                 if self.arm_controller.init_pos() is not True:
#                     raise RuntimeError("Dynamixelの初期位置移動がタイムアウトしました")

#                 self.get_logger().info("Arm init complete. Starting Z-axis init...")
#                 self.z_controller.init_pos()
#                 self.get_logger().info("初期化完了")
#                 response.task_comp = True

#             elif request.task == "move_to_target":
#                 self.get_logger().info("move_to_target")
#                 response.task_comp = self.move_to_target(request.target)
#                 error_messages = {
#                     1: "逆運動学失敗（可動範囲外・特異点・未収束）",
#                     2: "モータ角度の動作範囲外により失敗",
#                     3: "ホーム位置への復帰失敗",
#                     4: "Z軸目標位置が可動範囲外",
#                     5: "Dynamixelの目標位置到達タイムアウト",
#                     6: "目標座標が不正",
#                     7: "経路生成失敗",
#                 }
#                 if self.error_num in error_messages:
#                     self.get_logger().error(error_messages[self.error_num])

#             elif request.task == "move_to_box":
#                 cutting_done = self.cutting(request.target)
#                 if not cutting_done:
#                     self.get_logger().error("噛み切り動作できませんでした")
#                     return response
#                 response.task_comp = self.arm_controller.move_to_box() is True

#             elif request.task == "home":
#                 if self.EXPERIMENT_MODE:
#                     tom_hight_from_z = request.target.z
#                 else:
#                     tom_hight_from_backcam = request.target.y
#                     self.get_logger().info(
#                         f"端のトマトの高さ(カメラ座標)：{tom_hight_from_backcam}")
#                     if self.HAND_CAM_ANG == 0:
#                         tom_hight_from_z = (
#                             self.BACK_CAM_HEIGHT - tom_hight_from_backcam
#                             - (130 + self.HAND_CAM_HEIGHT))
#                     else:
#                         tom_hight_from_z = self.BACK_CAM_HEIGHT - tom_hight_from_backcam

#                 self.get_logger().info(
#                     f"端のトマトの高さ(Z座標)：{tom_hight_from_z}")
#                 arm_done = self.arm_controller.move_to_home() is True
#                 if not arm_done:
#                     raise RuntimeError("Dynamixelのホーム移動がタイムアウトしました")
#                 self.z_controller.home_pos(tom_hight_from_z)
#                 response.task_comp = True
#                 tom_hight = Int32()
#                 tom_hight.data = int(tom_hight_from_z)
#                 response.tom_hight = tom_hight

#             else:
#                 self.get_logger().error(f"未対応のアームタスクです: {request.task!r}")

#         except Exception as error:
#             self.get_logger().error(
#                 f"アームサービス失敗 ({type(error).__name__}): {error}")
#             response.task_comp = False

#         return response
    
# def main():
#     rclpy.init() 
#     node=Arm_Controller() 
#     try :
#         rclpy.spin(node) 
#     except KeyboardInterrupt :
#         print("\nCtrl+C has been entered")
#     else:
#         rclpy.shutdown()
#     finally:
#         node.destroy_node()

# if __name__ == '__main__':
#     main()















# import rclpy  # ROS2のPythonモジュールをインポート
# from rclpy.node import Node 
# # rclpy.qos から qos_profile_services_default をインポート
# from rclpy.qos import qos_profile_services_default

# import sys
# import numpy as np
# import yaml


# sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg")
# #from suction_unit import Suction_Unit
# sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/modules")
# #from .modules.ik_solver_ver4 import InverseKinematicsSolver
# from .modules.ik_solver_arm2 import InverseKinematicsSolver
# # from .modules.ik_solver_arm2_2 import InverseKinematicsSolver
# #from .modules.ik_solver_1201 import InverseKinematicsSolver
# # from .modules.route_planner_lib_ver2 import RoutePlanner
# from .modules.route_planner_simple_no_obs import RoutePlanner
# # from .modules.motor_controller_module import MotorController
# from .modules.motor_controller_module_5motor import MotorController
# from .modules.z_axis_controller_module import ZAxis
# from toms_msg.srv import ArmService, EndEffectorService
# import time
# from std_msgs.msg import Int32

# from .modules.angle_converter import AngleConverter
# """
# Arm_service_server
# アーム制御ノード

# @author : 吉永
# """

# """
# service通信

# [input]

# [output] 
# harvest success decision
# """


# class Arm_Controller(Node):  
#     def __init__(self):
#         super().__init__('arm_controller')
        
#         #service
#         self.srv = self.create_service(
#             ArmService,
#             "arm_service",
#             self.arm_host_server,
#             # QoSプロファイルを明示的に指定
#             qos_profile=qos_profile_services_default)

#         # パラメータ設定用のyamlファイル
#         yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
#         # YAMLファイルの読み込み
#         params = self.load_yaml(yaml_path)
#         required = ('dxl_params', 'ik_solver_params', 'ZAxis_params',
#                     'vision_params', 'coordinate_transform_params', 'arm_params')
#         missing = [key for key in required if key not in params]
#         if missing:
#             raise KeyError(f'{yaml_path} に必須設定がありません: {missing}')
#         dxl_params = params["dxl_params"]
#         ik_params = params["ik_solver_params"]
#         z_params = params["ZAxis_params"]
#         vision_params = params["vision_params"]
#         trans_params = params["coordinate_transform_params"]
        
#         self.BACK_CAM_HEIGHT = z_params["BACK_CAM_HEIGHT"]
        
#         # manipulator_function
#         self.arm_controller = MotorController(dxl_params)
#         self.z_controller = ZAxis(z_params)
#         self.solver = InverseKinematicsSolver(ik_params)
#         self.planner = RoutePlanner(params)
#         self.angle_converter = AngleConverter(dxl_params)
        
#         self.HOME_ANGLE = dxl_params["DXL_HOME_ANGLE"]
        
#         self.approach_ang_base = vision_params["APPROACH_ANG"]
#         self.HAND_CAM_ANG = trans_params["CAM_ANGLE"]
#         self.HAND_CAM_HEIGHT = trans_params["Z_DIFF_CAM2EE"]
        
#         # 何かしらの実験や検証を行う際のフラグに使ってください
#         self.EXPERIMENT_MODE = params["EXPERIMENT_MODE"]
        
#         INIT_X = params["arm_params"]["INIT_X"]
#         INIT_Y = params["arm_params"]["INIT_Y"]
#         INIT_ANG = params["arm_params"]["INIT_ANG"]
        
#         # ※アームの初期位置を変更する場合以下を実行すること※
#         """
#         HOME_ANGLE_IN_ARM = self.angle_converter.dxl_ang2ik_ang(self.HOME_ANGLE) # 順運動学を解くためにモータの角度系からアームの角度系に変換
#         # yamlファイルのアーム座標系でのホームポジションの各関節角度を書き換え
#         params["arm_params"]["HOME_ANGLE_IN_ARM"] = HOME_ANGLE_IN_ARM
        
#         # 初期位置と初期角度の設定
#         INIT_X, INIT_Y, INIT_ANG = self.solver.forward_kinematics(HOME_ANGLE_IN_ARM[0], HOME_ANGLE_IN_ARM[1], HOME_ANGLE_IN_ARM[2])# 初期位置と初期角度の取得
#         # yamlファイルの初期位置・初期角度を書き換え
#         params["arm_params"]["INIT_X"] = INIT_X
#         params["arm_params"]["INIT_Y"] = INIT_Y
#         params["arm_params"]["INIT_ANG"] = INIT_ANG
        
#         # 書き換えた内容を元のYAMLファイルに反映
#         with open(yaml_path, "w") as file:
#             yaml.dump(params, file, default_flow_style=False)
#         """
#         self.INIT_POS = [INIT_X, INIT_Y]
#         self.INIT_ANG = INIT_ANG
        
#         self.error_num = 0

#         # サービスコールを無期限に待たせないため、ホーム復帰の再試行回数を制限する。
#         self.HOME_RECOVERY_ATTEMPTS = 2

#     @staticmethod
#     def load_yaml(file_path):
#         """YAMLファイルを読み込むヘルパー関数"""
#         try:
#             with open(file_path, "r") as file:
#                 return yaml.safe_load(file)
#         except FileNotFoundError:
#             raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
#         except yaml.YAMLError as e:
#             raise ValueError(f"YAMLファイルの解析エラー: {e}")

#     def move_to_target(self, target):
#         self.error_num = 0
#         target_x, target_y, target_z, alpha = target.x, target.y, target.z, target.approach_direction

#         target_values = [target_x, target_y, target_z, alpha]
#         if not all(np.isfinite(value) for value in target_values):
#             self.get_logger().error(f"目標値にNaNまたはinfがあります: {target_values}")
#             self.error_num = 6
#             return False
#         if target_z < 0 or target_z > 450:
#             self.get_logger().error(
#                 f"Z軸目標位置{target_z}mmは可動範囲0..450mmの外です")
#             self.error_num = 4
#             return False
        
#         goal_posi = [target_x, target_y]
#         obstacles_posi = []
#         self.get_logger().info(
#             f"[XY HEIGHT TARGET] x={target_x:.1f} y={target_y:.1f} "
#             f"height_z={target_z:.1f} approach={alpha:.1f}deg")
#         self.get_logger().info(f"goal_posi: {goal_posi}")
#         self.get_logger().info(f"approach_ang: {alpha}")

#         pre_angles = None
#         for home_attempt in range(self.HOME_RECOVERY_ATTEMPTS + 1):
#             # 現在のモータの角度読み取り
#             pre_angles = self.arm_controller.read_positions()
#             # Dynamixel上の角度へ変更(アーム座標系じゃない)
#             pre_angles = [self.arm_controller.position_to_angle(pos) for pos in pre_angles]
#             pre_angles.pop(1)
#             # ↓モータ5個用
#             pre_angles.pop(2)
#             self.get_logger().info(f"Dynamixel上の現在位置: {pre_angles}")
#             check_threshold = all(
#                     abs(home - pre_angle) <= 10
#                     for home, pre_angle in zip(self.HOME_ANGLE, pre_angles)
#                 )
            
#             if check_threshold:
#                 break

#             if home_attempt >= self.HOME_RECOVERY_ATTEMPTS:
#                 self.get_logger().error(
#                     "ホーム位置へ復帰できません。Dynamixelの電源・通信・干渉を確認してください。")
#                 self.error_num = 3
#                 return False

#             self.get_logger().warning(
#                 f"アームがホーム位置ではありません。復帰を試します "
#                 f"({home_attempt + 1}/{self.HOME_RECOVERY_ATTEMPTS})")
#             if self.arm_controller.init_pos() is not True:
#                 self.get_logger().error("ホーム位置への移動がタイムアウトしました。")
#                 self.error_num = 3
#                 return False

#         self.planner.reset(self.INIT_POS, self.INIT_ANG)
#         route_list = self.planner.solve_rrt(goal_posi, alpha, obstacles_posi)
#         self.get_logger().info(f"\n経路: \n{route_list}")
#         if route_list is None or len(route_list) < 2:
#             self.get_logger().error("目標までの経路を生成できませんでした。")
#             self.error_num = 7
#             return False

#         motor_angles_list = []
#         current_motor_angles = self.angle_converter.dxl_ang2ik_ang(pre_angles)
#         current_EE_posi_angle = route_list[0]
#         for i in range(len(route_list) - 1):
#             next_posi_EEangle, next_motor_angles, solve_done = self.solver.solve_ik(
#                 current_EE_posi_angle, route_list[i + 1], current_motor_angles)

#             if solve_done is False:
#                 self.get_logger().error(
#                     "逆運動学を解けませんでした。目標が可動範囲外、特異点付近、または計算未収束です。")
#                 self.error_num = 1
#                 return False

#             next_motor_angles, check_angle = self.angle_converter.ik_ang2dxl_ang(
#                 next_motor_angles)
#             if check_angle is False:
#                 self.get_logger().error("この経路はモータ角度が可動範囲外です。")
#                 self.error_num = 2
#                 return False
#             if next_motor_angles is None:
#                 self.get_logger().error("逆運動学の結果が空です。")
#                 self.error_num = 1
#                 return False

#             motor_angles_list.append(next_motor_angles)
#             current_EE_posi_angle = next_posi_EEangle
#             current_motor_angles = self.angle_converter.dxl_ang2ik_ang(
#                 next_motor_angles)

#         if not motor_angles_list:
#             self.get_logger().error("送信できるアーム経路がありません。")
#             self.error_num = 7
#             return False

#         # move2target内でZ軸電源を有効化する。Pico無応答時は例外で即座に失敗へ戻る。
#         self.z_controller.move2target(target_z)

#         for motor_angles in motor_angles_list:
#             self.get_logger().info(f"motor_angles: {motor_angles}")
#             if self.arm_controller.move_motors(motor_angles, task="target") is not True:
#                 self.get_logger().error("Dynamixelが目標角度へ到達できませんでした。")
#                 self.error_num = 5
#                 return False

#         self.get_logger().info(
#             f"アーム指令完了: 経路点{len(motor_angles_list)}件")
#         return True
    
#     def cutting(self, target):
#         target_x, target_y, target_z, alpha = target.x, target.y, target.z, target.approach_direction
#         print(f"x, y, x, alpha: {target_x, target_y, target_z, alpha}")
#         action_dis = 75
#         if alpha == int(self.approach_ang_base):
#             cut_posi = [target_x - action_dis, target_y - action_dis]
#             beta = 45
        
#         elif alpha == int(180 - int(self.approach_ang_base)):
#             cut_posi = [target_x + action_dis, target_y - action_dis]
#             beta = 135
        
#         else :
#             # cut_posi = [target_x, target_y - action_dis]
#             # beta = alpha
#             cut_posi = [target_x , target_y - action_dis]
#             beta = alpha
        
#         # 現在のモータの角度読み取り
#         pre_angles = self.arm_controller.read_positions()
#         # Dynamixel上の角度へ変更(アーム座標系じゃない)
#         pre_angles = [self.arm_controller.position_to_angle(pos) for pos in pre_angles]
#         pre_angles.pop(1)
#         pre_angles.pop(2)
        
#         route_list = np.empty((0, 2))
#         route_list = [[target_x, target_y, alpha], [cut_posi[0], cut_posi[1], beta]]
        
#         current_motor_angles = self.angle_converter.dxl_ang2ik_ang(pre_angles) # Dynamixel上の角度からアーム座標系に変換
#         current_EE_posi_angle = route_list[0] # アーム座標の初期手先座標と角度 
        
#         next_posi_EEangle, next_motor_angles, solve_done = self.solver.solve_ik(current_EE_posi_angle, route_list[1], current_motor_angles)
#         motor_angles, check_ang = self.angle_converter.ik_ang2dxl_ang(next_motor_angles) # アーム座標系の角度からモータの角度系に変換する関数
#         if solve_done == False:
#             self.get_logger().info("特異点を通過 → 噛み切り動作できる位置ではありません。")
#             return False
#         if check_ang == False:
#             self.get_logger().info("この経路はモータ角度が可動範囲外です。")
#             return False
        
#         return self.arm_controller.move_motors(motor_angles, task="cutting") is True

#     def debug_ik_result(self,theta1, theta2, theta3):
#         self.get_logger().info("モータ角度") 
#         self.get_logger().info("---------------------------")
#         self.get_logger().info(f"θ1: {round((theta1))} degrees")
#         self.get_logger().info(f"θ2: {round((theta2))} degrees")
#         self.get_logger().info(f"θ3: {round((theta3))} degrees")
#         self.get_logger().info(f"α: {round((theta1) + (theta2) + (theta3))} degrees")
#         # self.get_logger().info("アーム位置")
#         # self.get_logger().info("---------------------------")
#         # x,z = self.solver.forward_kinematics(theta1, theta2, theta3)
#         # self.get_logger().info(f"x : {round(x)} z : {round(z)}")

#     def arm_host_server(self, request, response):
#         # 例外をROSサービスの失敗応答へ変換し、呼び出し側を待たせ続けない。
#         response.task_comp = False
#         try:
#             if request.task == "init_arm":
#                 self.get_logger().info("'init_arm' request received. Starting arm init...")
#                 if self.arm_controller.init_pos() is not True:
#                     raise RuntimeError("Dynamixelの初期位置移動がタイムアウトしました")

#                 self.get_logger().info("Arm init complete. Starting Z-axis init...")
#                 self.z_controller.init_pos()
#                 self.get_logger().info("初期化完了")
#                 response.task_comp = True

#             elif request.task == "move_to_target":
#                 self.get_logger().info("move_to_target")
#                 response.task_comp = self.move_to_target(request.target)
#                 error_messages = {
#                     1: "逆運動学失敗（可動範囲外・特異点・未収束）",
#                     2: "モータ角度の動作範囲外により失敗",
#                     3: "ホーム位置への復帰失敗",
#                     4: "Z軸目標位置が可動範囲外",
#                     5: "Dynamixelの目標位置到達タイムアウト",
#                     6: "目標座標が不正",
#                     7: "経路生成失敗",
#                 }
#                 if self.error_num in error_messages:
#                     self.get_logger().error(error_messages[self.error_num])

#             elif request.task == "move_to_box":
#                 cutting_done = self.cutting(request.target)
#                 if not cutting_done:
#                     self.get_logger().error("噛み切り動作できませんでした")
#                     return response
#                 response.task_comp = self.arm_controller.move_to_box() is True

#             elif request.task == "home":
#                 if self.EXPERIMENT_MODE:
#                     tom_hight_from_z = request.target.z
#                 else:
#                     tom_hight_from_backcam = request.target.y
#                     self.get_logger().info(
#                         f"端のトマトの高さ(カメラ座標)：{tom_hight_from_backcam}")
#                     if self.HAND_CAM_ANG == 0:
#                         tom_hight_from_z = (
#                             self.BACK_CAM_HEIGHT - tom_hight_from_backcam
#                             - (130 + self.HAND_CAM_HEIGHT))
#                     else:
#                         tom_hight_from_z = self.BACK_CAM_HEIGHT - tom_hight_from_backcam

#                 self.get_logger().info(
#                     f"端のトマトの高さ(Z座標)：{tom_hight_from_z}")
#                 arm_done = self.arm_controller.move_to_home() is True
#                 if not arm_done:
#                     raise RuntimeError("Dynamixelのホーム移動がタイムアウトしました")
#                 self.z_controller.home_pos(tom_hight_from_z)
#                 response.task_comp = True
#                 tom_hight = Int32()
#                 tom_hight.data = int(tom_hight_from_z)
#                 response.tom_hight = tom_hight

#             else:
#                 self.get_logger().error(f"未対応のアームタスクです: {request.task!r}")

#         except Exception as error:
#             self.get_logger().error(
#                 f"アームサービス失敗 ({type(error).__name__}): {error}")
#             response.task_comp = False

#         return response
    
# def main():
#     rclpy.init() 
#     node=Arm_Controller() 
#     try :
#         rclpy.spin(node) 
#     except KeyboardInterrupt :
#         print("\nCtrl+C has been entered")
#     else:
#         rclpy.shutdown()
#     finally:
#         node.destroy_node()

# if __name__ == '__main__':
#     main()





# 10がつ5か

import rclpy  # ROS2のPythonモジュールをインポート
from rclpy.node import Node 
# rclpy.qos から qos_profile_services_default をインポート
from rclpy.qos import qos_profile_services_default

import sys
import numpy as np
import yaml


sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg")
#from suction_unit import Suction_Unit
sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/modules")
#from .modules.ik_solver_ver4 import InverseKinematicsSolver
from .modules.ik_solver_arm2 import InverseKinematicsSolver
# from .modules.ik_solver_arm2_2 import InverseKinematicsSolver
#from .modules.ik_solver_1201 import InverseKinematicsSolver
# from .modules.route_planner_lib_ver2 import RoutePlanner
from .modules.route_planner_simple_no_obs import RoutePlanner
# from .modules.motor_controller_module import MotorController
from .modules.motor_controller_module_5motor import MotorController
from .modules.z_axis_controller_module import ZAxis
from toms_msg.srv import ArmService, EndEffectorService
import time
from std_msgs.msg import Int32

from .modules.angle_converter import AngleConverter
"""
Arm_service_server
アーム制御ノード

@author : 吉永
"""

"""
service通信

[input]

[output] 
harvest success decision
"""


class Arm_Controller(Node):  
    def __init__(self):
        super().__init__('arm_controller')
        
        #service
        self.srv = self.create_service(
            ArmService,
            "arm_service",
            self.arm_host_server,
            # QoSプロファイルを明示的に指定
            qos_profile=qos_profile_services_default)

        # パラメータ設定用のyamlファイル
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        # YAMLファイルの読み込み
        params = self.load_yaml(yaml_path)
        dxl_params = params["dxl_params"]
        ik_params = params["ik_solver_params"]
        z_params = params["ZAxis_params"]
        vision_params = params["vision_params"]
        trans_params = params["coordinate_transform_params"]
        
        self.BACK_CAM_HEIGHT = z_params["BACK_CAM_HEIGHT"]
        
        # manipulator_function
        self.arm_controller = MotorController(dxl_params)
        self.z_controller = ZAxis(z_params)
        # Pico起動直後は現在位置が未確定（pre_pos=-1）。
        # アームがホーム位置にある状態で、最初の収穫指令時にZ原点復帰する。
        self.z_axis_homed = False
        self.solver = InverseKinematicsSolver(ik_params)
        self.planner = RoutePlanner(params)
        self.angle_converter = AngleConverter(dxl_params)
        
        self.HOME_ANGLE = dxl_params["DXL_HOME_ANGLE"]
        
        self.approach_ang_base = vision_params["APPROACH_ANG"]
        self.HAND_CAM_ANG = trans_params["CAM_ANGLE"]
        self.HAND_CAM_HEIGHT = trans_params["Z_DIFF_CAM2EE"]
        
        # 何かしらの実験や検証を行う際のフラグに使ってください
        self.EXPERIMENT_MODE = params["EXPERIMENT_MODE"]
        
        INIT_X = params["arm_params"]["INIT_X"]
        INIT_Y = params["arm_params"]["INIT_Y"]
        INIT_ANG = params["arm_params"]["INIT_ANG"]
        
        # ※アームの初期位置を変更する場合以下を実行すること※
        """
        HOME_ANGLE_IN_ARM = self.angle_converter.dxl_ang2ik_ang(self.HOME_ANGLE) # 順運動学を解くためにモータの角度系からアームの角度系に変換
        # yamlファイルのアーム座標系でのホームポジションの各関節角度を書き換え
        params["arm_params"]["HOME_ANGLE_IN_ARM"] = HOME_ANGLE_IN_ARM
        
        # 初期位置と初期角度の設定
        INIT_X, INIT_Y, INIT_ANG = self.solver.forward_kinematics(HOME_ANGLE_IN_ARM[0], HOME_ANGLE_IN_ARM[1], HOME_ANGLE_IN_ARM[2])# 初期位置と初期角度の取得
        # yamlファイルの初期位置・初期角度を書き換え
        params["arm_params"]["INIT_X"] = INIT_X
        params["arm_params"]["INIT_Y"] = INIT_Y
        params["arm_params"]["INIT_ANG"] = INIT_ANG
        
        # 書き換えた内容を元のYAMLファイルに反映
        with open(yaml_path, "w") as file:
            yaml.dump(params, file, default_flow_style=False)
        """
        self.INIT_POS = [INIT_X, INIT_Y]
        self.INIT_ANG = INIT_ANG
        
        self.error_num = 0

        # サービスコールを無期限に待たせないため、ホーム復帰の再試行回数を制限する。
        self.HOME_RECOVERY_ATTEMPTS = 2

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

    @staticmethod
    def require_z_reply(reply, operation):
        """Picoの応答が2整数であることを確認する。到達完了までは保証しない。"""
        if (not isinstance(reply, (list, tuple)) or len(reply) != 2
                or any(not isinstance(value, (int, np.integer)) for value in reply)):
            raise RuntimeError(f"Z軸Picoの{operation}応答が不正です: {reply!r}")
        return [int(reply[0]), int(reply[1])]

    def move_to_target(self, target):
        self.error_num = 0
        target_x, target_y, target_z, alpha = target.x, target.y, target.z, target.approach_direction

        target_values = [target_x, target_y, target_z, alpha]
        if not all(np.isfinite(value) for value in target_values):
            self.get_logger().error(f"目標値にNaNまたはinfがあります: {target_values}")
            self.error_num = 6
            return False
        if target_z < 0 or target_z > 450:
            self.get_logger().error(
                f"Z軸目標位置{target_z}mmは可動範囲0..450mmの外です")
            self.error_num = 4
            return False
        
        goal_posi = [target_x, target_y]
        obstacles_posi = []
        self.get_logger().info(f"goal_posi: {goal_posi}")
        self.get_logger().info(f"approach_ang: {alpha}")

        pre_angles = None
        for home_attempt in range(self.HOME_RECOVERY_ATTEMPTS + 1):
            # 現在のモータの角度読み取り
            pre_angles = self.arm_controller.read_positions()
            # Dynamixel上の角度へ変更(アーム座標系じゃない)
            pre_angles = [self.arm_controller.position_to_angle(pos) for pos in pre_angles]
            pre_angles.pop(1)
            # ↓モータ5個用
            pre_angles.pop(2)
            self.get_logger().info(f"Dynamixel上の現在位置: {pre_angles}")
            check_threshold = all(
                    abs(home - pre_angle) <= 10
                    for home, pre_angle in zip(self.HOME_ANGLE, pre_angles)
                )
            
            if check_threshold:
                break

            if home_attempt >= self.HOME_RECOVERY_ATTEMPTS:
                self.get_logger().error(
                    "ホーム位置へ復帰できません。Dynamixelの電源・通信・干渉を確認してください。")
                self.error_num = 3
                return False

            self.get_logger().warning(
                f"アームがホーム位置ではありません。復帰を試します "
                f"({home_attempt + 1}/{self.HOME_RECOVERY_ATTEMPTS})")
            if self.arm_controller.init_pos() is not True:
                self.get_logger().error("ホーム位置への移動がタイムアウトしました。")
                self.error_num = 3
                return False

        # Pico側は原点復帰前（pre_pos=-1）の3,<高さ>指令を無視し、返事もしない。
        # 先にZ軸を原点復帰させ、正しい応答を確認してから目標高さへ進む。
        if not self.z_axis_homed:
            self.get_logger().info("[Z HOME] 初回移動前にZ軸を原点復帰します")
            z_home_reply = self.require_z_reply(
                self.z_controller.init_pos(), "原点復帰")
            if z_home_reply[0] != 2 or not (0 <= z_home_reply[1] <= 450):
                raise RuntimeError(
                    f"Z軸原点復帰の応答が想定外です: {z_home_reply!r} (期待: [2, 0..450])")
            self.z_axis_homed = True
            self.get_logger().info(f"[Z HOME REPLY] {z_home_reply}")

        self.planner.reset(self.INIT_POS, self.INIT_ANG)
        route_list = self.planner.solve_rrt(goal_posi, alpha, obstacles_posi)
        self.get_logger().info(f"\n経路: \n{route_list}")
        if route_list is None or len(route_list) < 2:
            self.get_logger().error("目標までの経路を生成できませんでした。")
            self.error_num = 7
            return False

        motor_angles_list = []
        current_motor_angles = self.angle_converter.dxl_ang2ik_ang(pre_angles)
        current_EE_posi_angle = route_list[0]
        for i in range(len(route_list) - 1):
            next_posi_EEangle, next_motor_angles, solve_done = self.solver.solve_ik(
                current_EE_posi_angle, route_list[i + 1], current_motor_angles)

            if solve_done is False:
                self.get_logger().error(
                    "特異点を通過するため、このトマトは収穫できる位置にありません。")
                self.error_num = 1
                return False

            next_motor_angles, check_angle = self.angle_converter.ik_ang2dxl_ang(
                next_motor_angles)
            if check_angle is False:
                self.get_logger().error("この経路はモータ角度が可動範囲外です。")
                self.error_num = 2
                return False
            if next_motor_angles is None:
                self.get_logger().error("逆運動学の結果が空です。")
                self.error_num = 1
                return False

            motor_angles_list.append(next_motor_angles)
            current_EE_posi_angle = next_posi_EEangle
            current_motor_angles = self.angle_converter.dxl_ang2ik_ang(
                next_motor_angles)

        if not motor_angles_list:
            self.get_logger().error("送信できるアーム経路がありません。")
            self.error_num = 7
            return False

        # 旧画像処理版の動作順を維持し、目標移動の直前にZ軸をOFF→ONする。
        # 各応答が確認できない場合は、状態不明のまま次の指令へ進まない。
        self.get_logger().info("[Z PREP] power cycle OFF -> ON")
        self.require_z_reply(self.z_controller.power_enable(0), "電源OFF")
        time.sleep(0.5)
        self.require_z_reply(self.z_controller.power_enable(1), "電源ON")

        # Z軸の応答を確認してから平面アームを動かす。無応答時に高さ違いで進入しない。
        self.get_logger().info(f"[Z WAIT] target_z={target_z}mm")
        z_reply = self.require_z_reply(
            self.z_controller.move2target(target_z), "目標移動")
        self.get_logger().info(
            f"[Z REPLY] mode={z_reply[0]} value={z_reply[1]} "
            "(Pico応答を受信。物理的な到達完了は別途未確認)")

        for motor_angles in motor_angles_list:
            self.get_logger().info(f"motor_angles: {motor_angles}")
            if self.arm_controller.move_motors(motor_angles, task="target") is not True:
                self.get_logger().error("Dynamixelが目標角度へ到達できませんでした。")
                self.error_num = 5
                return False

        self.get_logger().info(
            f"アーム指令完了: 経路点{len(motor_angles_list)}件")
        return True
    
    def cutting(self, target):
        target_x, target_y, target_z, alpha = target.x, target.y, target.z, target.approach_direction
        print(f"x, y, x, alpha: {target_x, target_y, target_z, alpha}")
        action_dis = 75
        if alpha == int(self.approach_ang_base):
            cut_posi = [target_x - action_dis, target_y - action_dis]
            beta = 45
        
        elif alpha == int(180 - int(self.approach_ang_base)):
            cut_posi = [target_x + action_dis, target_y - action_dis]
            beta = 135
        
        else :
            # cut_posi = [target_x, target_y - action_dis]
            # beta = alpha
            cut_posi = [target_x , target_y - action_dis]
            beta = alpha
        
        # 現在のモータの角度読み取り
        pre_angles = self.arm_controller.read_positions()
        # Dynamixel上の角度へ変更(アーム座標系じゃない)
        pre_angles = [self.arm_controller.position_to_angle(pos) for pos in pre_angles]
        pre_angles.pop(1)
        pre_angles.pop(2)
        
        route_list = np.empty((0, 2))
        route_list = [[target_x, target_y, alpha], [cut_posi[0], cut_posi[1], beta]]
        
        current_motor_angles = self.angle_converter.dxl_ang2ik_ang(pre_angles) # Dynamixel上の角度からアーム座標系に変換
        current_EE_posi_angle = route_list[0] # アーム座標の初期手先座標と角度 
        
        next_posi_EEangle, next_motor_angles, solve_done = self.solver.solve_ik(current_EE_posi_angle, route_list[1], current_motor_angles)
        motor_angles, check_ang = self.angle_converter.ik_ang2dxl_ang(next_motor_angles) # アーム座標系の角度からモータの角度系に変換する関数
        if solve_done == False:
            self.get_logger().info("特異点を通過 → 噛み切り動作できる位置ではありません。")
            return False
        if check_ang == False:
            self.get_logger().info("この経路はモータ角度が可動範囲外です。")
            return False
        
        return self.arm_controller.move_motors(motor_angles, task="cutting") is True

    def debug_ik_result(self,theta1, theta2, theta3):
        self.get_logger().info("モータ角度") 
        self.get_logger().info("---------------------------")
        self.get_logger().info(f"θ1: {round((theta1))} degrees")
        self.get_logger().info(f"θ2: {round((theta2))} degrees")
        self.get_logger().info(f"θ3: {round((theta3))} degrees")
        self.get_logger().info(f"α: {round((theta1) + (theta2) + (theta3))} degrees")
        # self.get_logger().info("アーム位置")
        # self.get_logger().info("---------------------------")
        # x,z = self.solver.forward_kinematics(theta1, theta2, theta3)
        # self.get_logger().info(f"x : {round(x)} z : {round(z)}")

    def arm_host_server(self, request, response):
        # 例外をROSサービスの失敗応答へ変換し、呼び出し側を待たせ続けない。
        response.task_comp = False
        try:
            if request.task == "init_arm":
                self.get_logger().info("'init_arm' request received. Starting arm init...")
                if self.arm_controller.init_pos() is not True:
                    raise RuntimeError("Dynamixelの初期位置移動がタイムアウトしました")

                self.get_logger().info("Arm init complete. Starting Z-axis init...")
                z_reply = self.require_z_reply(
                    self.z_controller.init_pos(), "原点復帰")
                self.get_logger().info(f"[Z REPLY] init={z_reply}")
                self.get_logger().info("初期化完了")
                response.task_comp = True

            elif request.task == "move_to_target":
                self.get_logger().info("move_to_target")
                response.task_comp = self.move_to_target(request.target)
                error_messages = {
                    1: "特異点通過により失敗",
                    2: "モータ角度の動作範囲外により失敗",
                    3: "ホーム位置への復帰失敗",
                    4: "Z軸目標位置が可動範囲外",
                    5: "Dynamixelの目標位置到達タイムアウト",
                    6: "目標座標が不正",
                    7: "経路生成失敗",
                }
                if self.error_num in error_messages:
                    self.get_logger().error(error_messages[self.error_num])

            elif request.task == "move_to_box":
                cutting_done = self.cutting(request.target)
                if not cutting_done:
                    self.get_logger().error("噛み切り動作できませんでした")
                    return response
                response.task_comp = self.arm_controller.move_to_box() is True

            elif request.task == "home":
                if self.EXPERIMENT_MODE:
                    tom_hight_from_z = request.target.z
                else:
                    tom_hight_from_backcam = request.target.y
                    self.get_logger().info(
                        f"端のトマトの高さ(カメラ座標)：{tom_hight_from_backcam}")
                    if self.HAND_CAM_ANG == 0:
                        tom_hight_from_z = (
                            self.BACK_CAM_HEIGHT - tom_hight_from_backcam
                            - (130 + self.HAND_CAM_HEIGHT))
                    else:
                        tom_hight_from_z = self.BACK_CAM_HEIGHT - tom_hight_from_backcam

                self.get_logger().info(
                    f"端のトマトの高さ(Z座標)：{tom_hight_from_z}")
                if (not np.isfinite(tom_hight_from_z)
                        or not 0 <= tom_hight_from_z <= 450):
                    raise ValueError(
                        f"Z軸目標位置{tom_hight_from_z}mmは可動範囲0..450mmの外です")
                arm_done = self.arm_controller.move_to_home() is True
                if not arm_done:
                    raise RuntimeError("Dynamixelのホーム移動がタイムアウトしました")
                z_reply = self.require_z_reply(
                    self.z_controller.home_pos(tom_hight_from_z), "高さ移動")
                self.get_logger().info(f"[Z REPLY] home={z_reply}")
                response.task_comp = True
                tom_hight = Int32()
                tom_hight.data = int(tom_hight_from_z)
                response.tom_hight = tom_hight

            else:
                self.get_logger().error(f"未対応のアームタスクです: {request.task!r}")

        except Exception as error:
            self.get_logger().error(
                f"アームサービス失敗 ({type(error).__name__}): {error}")
            response.task_comp = False

        return response
    
def main():
    rclpy.init() 
    node=Arm_Controller() 
    try :
        rclpy.spin(node) 
    except KeyboardInterrupt :
        print("\nCtrl+C has been entered")
    else:
        rclpy.shutdown()
    finally:
        node.destroy_node()

if __name__ == '__main__':
    main()
