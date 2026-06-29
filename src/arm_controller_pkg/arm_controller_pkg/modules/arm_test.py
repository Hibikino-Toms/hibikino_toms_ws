import sys
import numpy as np

# from ik_solver import InverseKinematicsSolver
# from ik_solver_ver3 import InverseKinematicsSolver
from ik_solver_ver4 import InverseKinematicsSolver
from route_planner_lib_ver2 import RoutePlanner
from motor_controller_module import MotorController
#from z_axis_controller_module import ZAxis
import time


def controlle_arm():
    motor_controller = MotorController()
    #z_controller = ZAxis()
    solver = InverseKinematicsSolver()
    
    # init = [0, 180.51] # homeポジションのときのEEの先端, 11/16 100から180.51に変更（これはhome_anglesに基づいている）
    init = [0, 162.5] # homeポジションのときのアーム1軸目とEE吸引口までの距離, 11/17 180.51から162.5に変更（これはhome_anglesに基づいている）
    init_deg = 90
    route_planner = RoutePlanner(init, init_deg) # 初期位置座標と初期位置のEEの角度
    
    home_angles = [100, 340, 100]
    target_posi = [80, 400, 50] # Z軸初期位置に対して、z= 350
    motor_angles_list = []
    
    goal_posi = [target_posi[0],target_posi[1]]
    print(goal_posi)
    approach_ang = 135
    # obstacles_posi = np.array([[50, 200, 30],[200,300,30]]) # 障害物がない場合は空[]
    obstacles_posi = []
    
    # 初期化
    motor_controller.init_pos()
    #z_controller.init_pos()
    
    while True:
        # 現在のモータの角度読み取り
        pre_angles = motor_controller.read_positions()
        pre_angles = [motor_controller.position_to_angle(pos) for pos in pre_angles]
        pre_angles.pop(1)
        print(f"現在位置: {pre_angles}")
        
        check_threshold = all(
                        abs(home - pre_angle) <= 10
                        for home, pre_angle in zip(home_angles, pre_angles)
                        )
        
        # デバッグ用
        # check_threshold = True
        # pre_angles = [100, 340, 100]
        
        #　Z軸の制御
        time.sleep(0.5)
        #z_controller.move2target(target_posi[2])
        
        if check_threshold:  # アームがホームポジションにあるときのみ処理を進める
            # 経路計画を立てて経路生成
            route_list = route_planner.solve_rrt(goal_posi, approach_ang, obstacles_posi)
            print(f'route: {route_list}')
            # # 本来は関数 ※85…EEの長さ
            # route_list =[[0, 0, 90],
            #             [0, 115+85, 90],
            #             [0, 190+85, 90],
            #             [0, 265+85, 90]]
            
            if route_list is not None:
                # 各経路点から次の経路点までの逆運動学解いて、各モータの目標位置を取得
                current_motor_angles = pre_angles
                current_EE_posi_angle = route_list[0]
                for i in range(len(route_list) - 1):
                    # 行列の1行目は、「ホームポジション座標」（→2段階収穫の場合は1段階目の移動後の座標）
                    
                    # 逆運動学を解く
                    next_posi_EEangle, next_motor_angles, solve_done = solver.solve_ik(current_EE_posi_angle, route_list[i+1], current_motor_angles)
                    if solve_done == False:
                        print("特異点を通過、もしくは計算不可 → 経路計画やり直し")
                        sys.exit()
                        break
                    motor_angles_list.append(next_motor_angles)
                    current_EE_posi_angle = next_posi_EEangle
                    current_motor_angles = next_motor_angles
                if solve_done == False:
                    continue
            else:
                continue
        else:
                print("アームがホームポジションではありません。")
                continue
        
        print(f"逆運動学解析結果: {motor_angles_list}")
        # break
        # 一行ずつ、各モータの目標位置に各モータを制御
        if motor_angles_list:
            send_angle_datas = []
            for i, motor_angles in enumerate(motor_angles_list):
                send_data = motor_controller.move_motors(motor_angles, task="target") # 単位：度で渡す
                # z_controller.move2target(target_posi[2]) # ④target_yで指定するz軸の制御処理実装
                send_angle_datas.append(send_data)
        
        motor_controller.__del__()
        break

def main():
    controlle_arm()

if __name__ == '__main__':
    main()
