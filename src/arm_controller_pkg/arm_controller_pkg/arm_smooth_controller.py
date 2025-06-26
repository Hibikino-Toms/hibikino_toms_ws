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
生成された経路に対して、各経路間を“なめらかに”動作させるアーム制御ノード
→2025/1/18時点: 未完成  ---  複数ある経路を滑らかに辿るように動作させることができていない。
→試したこと: タイマーコールバック機能を使用し、モータ制御関数を回す、かつ経路間に中間点のような点（に対応する関節角度）を生成しながら動作させる・・・結局は中間点や経路点をカクカク動作で辿っていく。タイマーコールバックをうまく使えていない？

@author : 吉永
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
        
        self.BACK_CAM_HIGHT = z_params["BACK_CAM_HIGHT"]
        
        # manipulator_function
        self.arm_controller = MotorController(dxl_params)
        self.z_controller = ZAxis(z_params)
        self.solver = InverseKinematicsSolver(ik_params)
        self.planner = RoutePlanner()
        self.angle_converter = AngleConverter()
        
        #self.HOME_ANGLE = [95 ,260, 95]
        self.HOME_ANGLE = dxl_params["DXL_HOME_ANGLE"]
        # self.HOME_ANGLE = [90+56.84, 90+165.86, 180-132.7]
        #self.INIT_POS = [6.47, 193.56] # homeポジションのときのアーム1軸目とEE吸引口までの距離, 11/17 180.51から162.5に変更（これはhome_anglesに基づいている）
        
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
        
        self.current_index = 0
        self.TIMER_PERIOD = 0.5  # 制御周期：50ms
        # self.timer = self.create_timer(self.TIMER_PERIOD, self.control_loop)
        self.step_size = 10
        self.timer_cancel = False
    
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

    def control_loop(self, motor_angles_list):
        # while 1:
        if self.current_index >= len(motor_angles_list):
            self.get_logger().info("全経路点を追従しました")
            self.timer_cancel = self.timer.cancel()
            return
        
        # 現在位置（角度） の取得
        now_angles = self.read_now_angles()
        # 次の経路点の角度を取得
        route_point_angles = motor_angles_list[self.current_index]
        
        # （経路点角度 - 現在角度）で現在角度と経路点角度の位置関係を取得
        diff_route_ang2now_ang = [route_ang - now_ang for (route_ang, now_ang) in zip(route_point_angles, now_angles)]
        self.get_logger().info(f"経路点と現在角度との差: {diff_route_ang2now_ang}")
        next_route = [abs(diff) < self.step_size for diff in diff_route_ang2now_ang]
        print(f"next_route: {next_route}")
        
        # link1~3のすべての角度において、現在点から経路点までがself.step_sizeより小さい場合、経路点を次へ進める
        is_all_True = all(next_route)
        print(f"is_all_True: {is_all_True}")
        if is_all_True:
            self.current_index += 1
            self.get_logger().info(f"Reached {route_point_angles}. Next ▶")
            # アーム動作
            self.arm_controller.move_motors(route_point_angles, task="target")
            return
        
        # 中間点の生成
        next_angles = self.interpolate_position(now_angles, route_point_angles, diff_route_ang2now_ang, next_route)
        # アーム動作
        self.arm_controller.move_motors(next_angles, task="target")
        # 現在位置（角度）の更新
        now_angles = self.read_now_angles()
        self.get_logger().info(f"今の角度: {now_angles}")
        
        return
    
    def read_now_angles(self):
        now_angles = self.arm_controller.read_positions()
        now_angles = [self.arm_controller.position_to_angle(pos) for pos in now_angles]
        now_angles.pop(1)
        now_angles.pop(2)
        return now_angles
    
    def interpolate_position(self, current, goal, diff, next):
        print(f"current, goal, self.step_size:{current, goal, self.step_size}")
        diff_signs = []
        # 線形補間アルゴリズム
        for i, step in enumerate(next):
            if step:
                diff_signs.append(0)
            else:
                if diff[i] > 0:
                    diff_signs.append(1)
                elif diff[i] < 0:
                    diff_signs.append(-1)
        # diffの各要素の符号を取得→step_sizeを加える方向と同義
        # diff_signs = [1 if x > 0 else -1 if x < 0 else 0 for x in diff]

        # 次の角度を、diff_signに基づいて、現在角度にstep_size分加えた角度で定義
        next_angles = [c + d_s * self.step_size for (c, d_s) in zip(current, diff_signs)]
        # for i, d in enumerate(diff):
        #     if current < goal:
        #         # return min(current + self.step_size, goal)
        #         next_angles = min([c + self.step_size for c in current], goal)
        #     else:
        #         # return max(current - self.step_size, goal)
        #         next_angles = max([c - self.step_size for c in current], goal)
        
        return next_angles
    
    def reached_goal(self, goal_angles):
        # 仮の判定：現在位置と目標位置の誤差が0.1以下なら到達とみなす
        now_angles = self.arm_controller.read_positions()
        now_angles = [self.arm_controller.position_to_angle(pos) for pos in now_angles]
        now_angles.pop(1)
        now_angles.pop(2)
        
        return all(abs(g - c) < 1 for g, c in zip(goal_angles, now_angles))

    def move_to_target(self,target):
        target_x, target_y, target_z, alpha = target.x, target.y, target.z, target.approach_direction
        motor_angles_list = []
        
        goal_posi = [target_x, target_y]
        approach_ang = alpha
        approach_ang = 90
        obstacles_posi = []
        timer_cancel = False
        # self.get_logger().info(f"goal_posi: {goal_posi}")
        # self.get_logger().info(f"approach_ang: {approach_ang}")
        # self.get_logger().info(f"obstacles_posi: {obstacles_posi}")
        
        while True:
            # 現在のモータの角度読み取り
            now_angles = self.read_now_angles()
            self.get_logger().info(f"現在位置(DXL角度): {now_angles}")
            check_threshold = all(
                    abs(home - now_angle) <= 10
                    for home, now_angle in zip(self.HOME_ANGLE, now_angles)
                )
            
            #　Z軸の制御
            time.sleep(0.5)
            self.z_controller.power_enable(0)
            self.z_controller.power_enable(1)
            self.z_controller.move2target(target_z)
            
            route_list = np.empty((0, 2))
            
            if check_threshold: # アームがホームポジションにあるときのみ処理を進める
                # 経路計画を立てて、通る経路の点を格納した行列を取得
                # print("経路計画内部の変数を初期化します", self.INIT_POS, self.INIT_ANG)
                self.planner.reset(self.INIT_POS, self.INIT_ANG)
                # アーム座標系の経路計画座標と角度のリストが返ってくる
                route_list = self.planner.solve_rrt(goal_posi, approach_ang, obstacles_posi)
                """
                route_init = [self.INIT_POS[0], self.INIT_POS[1], self.INIT_ANG]
                route = np.hstack((target_x, target_y, approach_ang))
                route_list = np.vstack((route_init, route))
                print(f"route_list; {route_list}")
                """
                if route_list is not None:
                    # self.get_logger().info("経路計画結果")
                    # self.get_logger().info(f"{route_list}")
                    
                    # 各経路点から次の経路点までの逆運動学解いて、各モータの目標位置を取得
                    current_motor_angles = now_angles # Dynamixel上の角度(アーム座標系じゃない)
                    current_EE_posi_angle = route_list[0] # アーム座標の初期手先座標と角度 
                    
                    current_motor_angles = self.angle_converter.dxl_ang2ik_ang(current_motor_angles) # Dynamixel上の角度からアーム座標系に変換
                    
                    for i in range(len(route_list) - 1):
                        # 行列の1行目は、「ホームポジション座標」（→2段階収穫の場合は1段階目の移動後の座標）
                        # 逆運動学を解く self.solver.solve_ik(cu[現在のx座標, 現在のy座標, 現在のEEの角度], [目標のx座標, 目標のy座標, EEの進入角度], 現在の各モータの角度：[link1の角度, link2の角度, link3の角度])
                        
                        next_posi_EEangle, next_motor_angles, solve_done = self.solver.solve_ik(current_EE_posi_angle, route_list[i+1], current_motor_angles)
                        next_motor_angles = self.angle_converter.ik_ang2dxl_ang(next_motor_angles) # アーム座標系の角度からモータの角度系に変換する関数
                        print(next_motor_angles)
                        if solve_done == False:
                            self.get_logger().info("特異点を通過 → 経路計画やり直し")
                            break
                        motor_angles_list.append(next_motor_angles)
                        current_EE_posi_angle = next_posi_EEangle
                        next_motor_angles = self.angle_converter.dxl_ang2ik_ang(next_motor_angles) # モータの角度系から逆運動学の角度系に変換する関数
                        current_motor_angles = next_motor_angles
                        # ｰーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーー
                    if solve_done == False:
                        continue
                else:
                    continue
            else:
                self.get_logger().info("アームがホームポジションではありません。")
                self.arm_controller.init_pos()
                continue
            # self.get_logger().info(f"逆運動学計算結果(MOTOR): \n{motor_angles_list}")
            
            if motor_angles_list:
            # 一行ずつ、各モータの目標位置に各モータを制御
                while 1:
                    self.timer = self.create_timer(self.TIMER_PERIOD, lambda: self.control_loop(motor_angles_list))
                    # self.control_loop(motor_angles_list)
                    # return True
                    if self.timer_cancel:
                        print("タイマーコールバックが終了しました。")
                        break
                    else:
                        print("タイマーコールバックが終了していません。")
                        self.timer_cancel = self.timer.cancel()
                        continue
            
            return True
    
    def debug_ik_result(self,theta1, theta2, theta3):
        self.get_logger().info("モータ角度") 
        self.get_logger().info("---------------------------")
        self.get_logger().info(f"θ1: {round((theta1))} degrees")
        self.get_logger().info(f"θ2: {round((theta2))} degrees")
        self.get_logger().info(f"θ3: {round((theta3))} degrees")
        self.get_logger().info(f"α : {round((theta1) + (theta2) + (theta3))} degrees")
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
            # self.get_logger().info(f"{target.x},{target.y},{target.z},{target.approach_direction}") 
            task_comp = self.move_to_target(target)
            response.task_comp = task_comp

        elif request.task == "move_to_box":
            self.arm_controller.move_to_box()
            # self.z_controller.init_pos()
            response.task_comp = True 
            
        elif request.task == "home":
            first_tom_pos_from_backcam = request.target
            # カメラ座標系
            tom_hight_from_backcam = first_tom_pos_from_backcam.y
            self.get_logger().info(f"端のトマトの高さ(基準:ボディカメラ中心(下向き正)): {tom_hight_from_backcam}") 
            # カメラ座標系
            tom_hight_from_z = self.BACK_CAM_HIGHT - tom_hight_from_backcam
            self.get_logger().info(f"端のトマトの高さ(基準:Z軸ゼロ点)                 : {tom_hight_from_z}") 
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
        print("Ctrl+C has been entered")  
        print("End of program")
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()
