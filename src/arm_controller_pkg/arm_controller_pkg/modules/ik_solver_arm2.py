"""
@author hikaru
---------------------------------------------------------------------------
逆運動学を解くクラス
逆運動学のクラスの引数：ホームポジの各モータ角度
sole_ik
    引数：経路ノードの座標とEE進入角度の行列（route_nodes）
            配列：[現在のx座標, 現在のy座標, 現在のEEの角度]
            配列：[次のx座標, 次のy座標, EEの進入角度]
            配列：[link1の角度, link2の角度, link3の角度]
    返り値：計算後の座標，計算後のEE進入角度／各モータの角度／ブール
    
返り値のブールは、計算結果が特異点付近である場合にFalseを返す
2024/10/08 時点
メートルからミリメートルに変更しました。

2024/10/24 時点
numpyに変更するコードを追加:90行あたり
モータの角度系に変更する#!ik_ang2dxl_ang
逆運動学の角度系に変更する#!dxl_ang2ik_ang
をそれぞれ定義した。またモータの角度系で関節１の角度が90~270度の範囲外になったとき、Falseを返すようにした。


一番下にデバッグ用のコードを置いている。
このコードを実行することで計算できる。


"""
import math
import numpy as np

from angle_converter import AngleConverter
import yaml


class InverseKinematicsSolver():
    def __init__(self, ik_params):
        
        # # YAMLファイルの読み込み
        # params = self.load_yaml(yaml_path)
        # ik_params = params["ik_solver_params"]  # 必須キー: 存在しない場合 KeyError が発生
        
        # 各リンクの長さ (mm)
        self.L1 = ik_params["Link1"]
        self.L2 = ik_params["Link2"]
        self.L3 = ik_params["Link3"]
        self.L4 = ik_params["Link4"]
        
        self.MAX_LOOP_NUM = ik_params["MAX_LOOP_NUM"]
        self.GOAL_DIS = ik_params["GOAL_DIS"]
        self.GOAL_ANG = ik_params["GOAL_ANG"]
        self.P_DELTA_PARAM = ik_params["P_DELTA_PARAM"]
        self.A_DELTA_PARAM = ik_params["A_DELTA_PARAM"]
        
        self.dxl_cnnection = True

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

    # 角度を -180° ～ +180° に正規化する関数
    def normalize_angle(self, angle):
        return (angle + 180) % 360 - 180

    # 順運動学計算
    def forward_kinematics(self, q1, q2, q3):
        q1 = math.radians(q1)
        q2 = math.radians(q2)
        q3 = math.radians(q3)
        
        x = self.L1*math.cos(q1) - self.L2*math.sin(q1) + self.L3*math.cos(q1 + q2) + self.L4*math.cos(q1 + q2 + q3)
        y = self.L1*math.sin(q1) + self.L2*math.cos(q1) + self.L3*math.sin(q1 + q2) + self.L4*math.sin(q1 + q2 + q3)
        a = q1 + q2 + q3
        a = math.degrees(a)
        return x, y, a
    
    # 逆運動学計算
    def solve_ik(self, P_current, P_goal, pre_Q):
        P_current = np.array(P_current)
        P_current = P_current.astype(float)

        P_goal = np.array(P_goal)
        P_goal = P_goal.astype(float)

        pre_Q = np.array(pre_Q)
        pre_Q = pre_Q.astype(float)
        # if (dxl_cnnection==True):
            # print("Dynamixel上の角度をアーム座標系に変換")
            #pre_Q = self.dxl_ang2ik_ang(pre_Q) # Dynamixel上の角度をアーム座標の角度に変換

        x_target = P_goal[0]
        y_target = P_goal[1]
        a_target = math.radians(P_goal[2]) # degrer to radian

        # 初期角度
        q1 = pre_Q[0]
        q2 = pre_Q[1]
        q3 = pre_Q[2]

        # 現在の座標計算
        x_current, y_current, a_current = self.forward_kinematics(q1, q2, q3)
        # print(f"x_current, y_current, a_current: {x_current, y_current, a_current}")
        # print(f"x_target, y_target, a_target: {x_target, y_target, a_target}")

        for i in range(self.MAX_LOOP_NUM):  # 繰り返し計算 (最大100回まで)

            # 誤差計算
            dx = self.P_DELTA_PARAM * (x_target - x_current)
            dy = self.P_DELTA_PARAM * (y_target - y_current)
            da = self.A_DELTA_PARAM * (a_target - math.radians(a_current))
            # print(f"da: {da}")

            # 三角関数の計算
            S1 = math.sin(math.radians(q1))
            # print(f"S1: {S1}")
            S2 = math.sin(math.radians(q2))
            S3 = math.sin(math.radians(q3))
            S12 = math.sin(math.radians(q1 + q2))
            S123 = math.sin(math.radians(q1 + q2 + q3))
            C1 = math.cos(math.radians(q1))
            C2 = math.cos(math.radians(q2))
            C3 = math.cos(math.radians(q3))
            C12 = math.cos(math.radians(q1 + q2))
            C123 = math.cos(math.radians(q1 + q2 + q3))

            # ヤコビ行列の成分
            J = np.array([
                [self.L1*S1 - self.L2*C1 - self.L3*S12 - self.L4*S123, -self.L3*S12 - self.L4*S123, -self.L4*S123],
                [self.L1*C1 - self.L2*S1 + self.L3*C12 + self.L4*C123,  self.L3*C12 + self.L4*C123,  self.L4*C123],
                [1                                                   ,  1                         ,  1           ]
            ])

            # ヤコビ行列の逆行列
            # J_inv = np.linalg.pinv(J)
            # ↓特異点抑制？逆行列↓
            U, S, Vt = np.linalg.svd(J)
            S_inv = np.diag([1/s if s > 1e-6 else 0 for s in S])  # 小さい値をゼロにする
            J_inv = Vt.T @ S_inv @ U.T

            # 修正量計算
            delta_q = np.dot(J_inv, np.array([dx, dy, da]))
            # print(f"delta: {delta_q}")

            # 角度の更新
            q1 += math.degrees(delta_q[0])
            q2 += math.degrees(delta_q[1])
            q3 += math.degrees(delta_q[2])
            # print(f"更新量: [{math.degrees(delta_q[0])}, {math.degrees(delta_q[1])}, {math.degrees(delta_q[2])}]")

            # Q_currentとP_currentの更新
            # print(f"正規化前：[{q1}, {q2}, {q3}]")
            # 角度を正規化
            q1 = self.normalize_angle(q1)
            q2 = self.normalize_angle(q2)
            q3 = self.normalize_angle(q3)
            # print(f"正規化後：[{q1}, {q2}, {q3}]")
            x_current, y_current, a_current = self.forward_kinematics(q1, q2, q3)
            Q_current = np.array([q1,q2,q3])
            P_current = np.array([x_current, y_current, a_current])

            # 誤差が小さければ終了
            if (P_goal[0]-P_current[0])**2 + (P_goal[1]-P_current[1])**2 < self.GOAL_DIS**2 and abs(math.degrees(da)) < self.GOAL_ANG:
                break
        #! 第1関節が、アーム座標系で-10度より小さい、または190度より大きい場合、ハードウェアの都合上無理と判断するため、Falseを返す
        if Q_current[0]  < -10 or Q_current[0] > 180:
            print("link1が動作範囲外の角度")
            return P_current, Q_current, False
        
        # print(f"Q_current(ARM) = {Q_current}")
        
        return P_current, Q_current, True

    """
    #! アーム座標系の角度からモーターの角度系に変換する関数
    def ik_ang2dxl_ang(self, ik_angles_list):
        angles_lists_motor = []
        angles_lists_motor = [ik_angles_list[0] + 90, ik_angles_list[1] + 90, ik_angles_list[2] + 180]

        return angles_lists_motor
    
    #! モータの角度系から逆運動学の角度系に変換する関数
    def dxl_ang2ik_ang(self, motor_angles_list):
        angles_lists_ik = []
        angles_lists_ik = [motor_angles_list[0] - 90, motor_angles_list[1] - 90, motor_angles_list[2] - 180]

        return angles_lists_ik
    """

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

def main(): 
    yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
    params = load_yaml(yaml_path)
    ik_params = params["ik_solver_params"]
    dxl_params = params["dxl_params"]
    arm_params = params["arm_params"]

    ik_solver = InverseKinematicsSolver(ik_params)
    angle_converter = AngleConverter(dxl_params)

    a = ik_solver.forward_kinematics(5, 170, -85)
    print(f'posi: {a}')

    P_current_input = np.array([a[0], a[1], a[2]])        #[現在のx座標, 現在のy座標, 現在のEEの角度]
    Q_current_input = np.array([5, 170, -85]) #現在の関節の角度：[link1の角度, link2の角度, link3の角度]

    while True:
        try:
            print(f"現在の座標：[x,y,a]=[{'{:.2f}'.format(P_current_input[0])},{'{:.2f}'.format(P_current_input[1])},{'{:.2f}'.format(P_current_input[2])}]")
            print(f"現在の関節角度：[q1,q2,q3]=[{'{:.2f}'.format(Q_current_input[0])},{'{:.2f}'.format(Q_current_input[1])},{'{:.2f}'.format(Q_current_input[2])}]")
            # ユーザー入力
            x_target = float(input("目標のx座標 (mm): "))
            y_target = float(input("目標のy座標 (mm): "))
            a_target = float(input("目標の手先角度 (°): "))
            P_goal_input = np.array([x_target, y_target , a_target])      #[目標のx座標, 目標のy座標, EEの進入角度]
            
            P_c, Q_c, success = ik_solver.solve_ik(P_current_input, P_goal_input, Q_current_input)
            
            if success:
                print(f"初期座標：[{'{:.2f}'.format(P_current_input[0])},{'{:.2f}'.format(P_current_input[1])},{'{:.2f}'.format(P_current_input[2])}]")
                print(f"目標の手先座標とEE角度：[{'{:.2f}'.format(P_goal_input[0])},{'{:.2f}'.format(P_goal_input[1])},{'{:.2f}'.format(P_goal_input[2])}]")
                print(f"計算結果の座標と角度：[{'{:.2f}'.format(P_c[0])},{'{:.2f}'.format(P_c[1])},{'{:.2f}'.format(P_c[2])}]")
                print(f"新しい逆運動学の角度系におけるリンク角度:[{'{:.2f}'.format(Q_c[0])},{'{:.2f}'.format(Q_c[1])},{'{:.2f}'.format(Q_c[2])}]")
                Q_c, check_limit = angle_converter.ik_ang2dxl_ang(Q_c) # 逆運動学（アーム）の座標系から、モータの座標系に変換する関数
                print(f"新しいモーターにおけるリンク角度: {Q_c}")
                
                Q_c = angle_converter.dxl_ang2ik_ang(Q_c) # モーターの座標系から、逆運動学（アーム）の座標系に変換する関数
                P_current_input = np.array(P_c)
                Q_current_input = np.array(Q_c)
            
            else:
                print("アームの可動域外です")

        except ValueError:
            print("無効な入力です。再試行してください。")
        except KeyboardInterrupt:
            print("\nプログラムを終了します。")
            break

#以下はデバッグ用のコード
if __name__ == '__main__':
    main()


