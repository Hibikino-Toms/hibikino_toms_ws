import rclpy  # ROS2のPythonモジュールをインポート
from rclpy.node import Node 

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
        self.srv = self.create_service(ArmService, "arm_service", self.arm_host_server)

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

    def move_to_target(self,target):
        self.error_num = 0
        target_x, target_y, target_z, alpha = target.x, target.y, target.z, target.approach_direction
        motor_angles_list = []
        route_list = np.empty((0, 2))
        
        goal_posi = [target_x, target_y]
        obstacles_posi = []
        self.get_logger().info(f"goal_posi: {goal_posi}")
        self.get_logger().info(f"approach_ang: {alpha}")

        while True:
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
            
            if check_threshold: # アームがホームポジションにあるとき
                self.planner.reset(self.INIT_POS, self.INIT_ANG)
                # アーム座標系の経路計画座標と角度のリストが返ってくる
                route_list = self.planner.solve_rrt(goal_posi, alpha, obstacles_posi) # 25/2/18時点：solve_rrt→簡素化されたシンプルな経路計画(障害物なし前提のrrtすらしていない単純経路生成処理ver.)
                self.get_logger().info(f"\n経路: \n{route_list}")
                """
                route_init = [self.INIT_POS[0], self.INIT_POS[1], self.INIT_ANG]
                route = np.hstack((target_x, target_y, approach_ang))
                route_list = np.vstack((route_init, route))
                print(f"route_list; {route_list}")
                """
                if route_list is not None:
                    # 各経路点から次の経路点までの逆運動学解いて、各モータの目標位置を取得
                    current_motor_angles = pre_angles # Dynamixel上の角度(モータ座標系)
                    current_EE_posi_angle = route_list[0] # アーム座標の初期手先座標と角度 
                    
                    current_motor_angles = self.angle_converter.dxl_ang2ik_ang(current_motor_angles) # Dynamixel上の角度からアーム座標系に変換
                    # self.get_logger().info(f"\nアーム座標系での現在のアーム角度: \n{current_motor_angles}")
                    for i in range(len(route_list) - 1):                        
                        next_posi_EEangle, next_motor_angles, solve_done = self.solver.solve_ik(current_EE_posi_angle, route_list[i+1], current_motor_angles)
                        # self.get_logger().info(f"\nnext_posi_EEangle, next_motor_angles: \n{next_posi_EEangle, next_motor_angles}")
                        
                        next_motor_angles, check_angle = self.angle_converter.ik_ang2dxl_ang(next_motor_angles) # アーム座標系の角度からモータの角度系に変換する関数
                        print(next_motor_angles)
                        if solve_done == False:
                            self.get_logger().info("特異点を通過 → このトマトは収穫できる位置にありません。")
                            self.error_num = 1
                            motor_angles_list = []
                            break
                        if check_angle == False:
                            self.get_logger().info("この経路はモータ角度が可動範囲外です。")
                            self.error_num = 2
                            motor_angles_list = []
                            break
                        motor_angles_list.append(next_motor_angles)
                        current_EE_posi_angle = next_posi_EEangle
                        next_motor_angles = self.angle_converter.dxl_ang2ik_ang(next_motor_angles) # モータの角度系から逆運動学の角度系に変換する関数
                        current_motor_angles = next_motor_angles
                        # ｰーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーー
                else:
                    continue
            else:
                self.get_logger().info("アームがホームポジションではありません。")
                self.arm_controller.init_pos()
                continue

            #　Z軸の制御
            time.sleep(0.5)
            self.z_controller.power_enable(0)
            self.z_controller.power_enable(1)
            self.z_controller.move2target(target_z)
            
            # 一行ずつ、各モータの目標位置に各モータを制御
            if len(motor_angles_list) != 0:
                send_angle_datas = []
                for i, motor_angles in enumerate(motor_angles_list):
                    print(f"motor_angles: {motor_angles}")
                    if motor_angles == None:
                        return False
                    send_data = self.arm_controller.move_motors(motor_angles, task="target")
                    send_angle_datas.append(send_data)
                self.get_logger().info(f"アーム指令 : {send_angle_datas}")
                return True
            else :
                return False
    
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
        
        self.arm_controller.move_motors(motor_angles, task="cutting")
        return True

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

    def arm_host_server(self,request, response):
        if request.task == "init_arm":
            self.arm_controller.init_pos()
            self.z_controller.init_pos()
            self.get_logger().info("初期化完了")
            response.task_comp = True 

        elif request.task == "move_to_target":
            target = request.target
            self.get_logger().info("move_to_target")
            task_comp = self.move_to_target(target)
            if self.error_num != 0:
                match self.error_num:
                    case 1:
                        self.get_logger().info("特異点通過により失敗")
                    case 2:
                        self.get_logger().info("モータ角度の動作範囲外により失敗")
            response.task_comp = task_comp
        
        elif request.task == "move_to_box":
            target = request.target
            task_comp = self.cutting(target)
            if task_comp == False:
                self.get_logger().info("噛み切り動作できませんでした") 
            self.arm_controller.move_to_box()
            response.task_comp = True
            
        elif request.task == "home":
            if self.EXPERIMENT_MODE: # 2025/2/1（吉永）：実験のため、zのhome_posの高さを手入力で設定
                tom_hight_from_z = request.target.z
            else:
                first_tom_pos_from_backcam = request.target
                # カメラ座標系
                tom_hight_from_backcam = first_tom_pos_from_backcam.y
                self.get_logger().info(f"端のトマトの高さ(カメラ座標)：{tom_hight_from_backcam}") 
                # カメラ座標系
                if self.HAND_CAM_ANG == 0: # 手先カメラのマウントが垂直タイプの場合
                    tom_hight_from_z = self.BACK_CAM_HEIGHT - tom_hight_from_backcam - (130 + self.HAND_CAM_HEIGHT) # 130…アーム高さの基準になる点（リミットスイッチとの接触点）からEE中心までのz方向の差
                else :
                    tom_hight_from_z = self.BACK_CAM_HEIGHT - tom_hight_from_backcam
            
            self.get_logger().info(f"端のトマトの高さ(Z座標)：{tom_hight_from_z}") 
            
            self.arm_controller.move_to_home()
            self.z_controller.home_pos(tom_hight_from_z) 
            response.task_comp = True
            tom_hight = Int32()
            tom_hight.data = int(tom_hight_from_z)
            response.tom_hight = tom_hight
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
