"""
@author nagasaki taichi, 長﨑
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

一番下にデバッグ用のコードを置いている。
このコードを実行することで計算できる。


"""
import math
import numpy as np

class InverseKinematicsSolver:
    
    def __init__(self,
                    link1_length = 275,
                    link2_length = 275,
                    link3_length = 85,
                    max_loop_num = 500,
                    goal_dis = 1,
                    P_delta_param = 0.1):
        
        self.link1_length = link1_length
        self.link2_length = link2_length
        self.link3_length = link3_length
        self.max_loop_num = max_loop_num
        self.goal_dis = goal_dis
        self.P_delta_param = P_delta_param
    
    def forward_kinematics2d(self, link_length, theta):
        x = link_length * np.cos(theta)
        y = link_length * np.sin(theta)

        return x,y
    
    def make_jacobian_matrix(self,  theta1, theta2, theta3):

        J = np.array([[-self.link1_length * math.sin(theta1) - self.link2_length * math.sin(theta1 + theta2) - self.link3_length * math.sin(theta1 + theta2 + theta3),
                        -self.link2_length * math.sin(theta1 + theta2) - self.link3_length * math.sin(theta1 + theta2 + theta3),
                        -self.link3_length * math.sin(theta1 + theta2 + theta3)],
                      [self.link1_length * math.cos(theta1) + self.link2_length * math.cos(theta1 + theta2) + self.link3_length * math.cos(theta1 + theta2 + theta3),
                        self.link2_length * math.cos(theta1 + theta2) + self.link3_length * math.cos(theta1 + theta2 + theta3),
                        self.link3_length * math.cos(theta1 + theta2 + theta3)],
                        [1, 1, 1]])
        return J

    def make_inverse_matrix(self, mat):
        determinant = np.linalg.det(mat)
    
        inverse_mat_ver2 = np.linalg.inv(mat)
    
        return inverse_mat_ver2, determinant
    
    def solve_ik(self, P_current, P_goal, pre_Q):
        x1 = 0
        y1 = 0

        P_current = np.array(P_current)
        P_current = P_current.astype(float)
        P_goal = np.array(P_goal)
        P_goal = P_goal.astype(float)
        pre_Q = np.array(pre_Q)
        pre_Q = pre_Q.astype(float)

        P_current[2] = np.deg2rad(P_current[2])
        P_goal[2] = np.deg2rad(P_goal[2])
        pre_Q = np.deg2rad(pre_Q)
        
        Q_current = pre_Q
        

        for i in range(self.max_loop_num):
            
            jacobian = self.make_jacobian_matrix( Q_current[0],
                                                    Q_current[1],
                                                    Q_current[2])
            
            jacobian_inverse, abs_jaco_data = self.make_inverse_matrix(jacobian)
            """
            if abs(abs_jaco_data) < 1:
                print("行列式が１より小さいので特異点になりやすく危険")
                return P_current, Q_current, False
            """
            
            P_current_to_P_goal = P_goal - P_current

            P_delta = P_current_to_P_goal * self.P_delta_param
            Q_delta = jacobian_inverse @ P_delta
            Q_new = Q_current + Q_delta

            Q_new = Q_new  % (2*math.pi)

            #print("link3の角度;", Q_new[2]*(180/math.pi))

            x1_to_2, y1_to_2 = self.forward_kinematics2d(self.link1_length, Q_new[0])

            # link2の根本から見た時の、link2の先端位置
            x2_to_3, y2_to_3 = self.forward_kinematics2d(self.link2_length, Q_new[0] + Q_new[1])

            # link3の根本から見たときの、link3の先端位置（=エンドエフェクタの位置）
            x3_to_e, y3_to_e = self.forward_kinematics2d(self.link3_length, Q_new[0] + Q_new[1] + Q_new[2])

            dege = (Q_new[0] + Q_new[1] + Q_new[2]) % (2*math.pi)

            # link1の根本（原点座標）から見た時の，エンドエフェクタの位置
            x2 = x1 + x1_to_2
            y2 = y1 + y1_to_2
            x3 = x2 + x2_to_3
            y3 = y2 + y2_to_3
            xe = x3 + x3_to_e
            ye = y3 + y3_to_e

            P_new = np.array([xe,ye,dege])

            Q_current = Q_new
            P_current = P_new

            #計算のループ中に特異点付近を通る時のチェッカー, 関節２が0,180,360度になるときは結構な頻度であるため、以下のチェッカーを使うかは再考する必要がある。
            #link2_deg = Q_current[1][0]*(180/math.pi)
            """
            if (abs(link2_deg - 0) < 3) or (abs(link2_deg - 180) < 3) or (abs(link2_deg - 360) < 3):
                print("aaaaaa",Q_current)
                print(f"{link2_deg}度であり、特異点付近なので危険です.{i}回目のループです")
                return P_current, Q_current, False
            """


            # 目標手先P_goalに到達したら終了
            if (P_goal[0]-P_current[0])**2  + (P_goal[1]-P_current[1])**2 <  self.goal_dis**2: # 2点間の距離の公式を使用（ただし、sqrt関数は処理が重いので、両辺を2乗した値で比較）
                print("何回ループしたか",i)

                #計算結果が特異点付近かどうかを確認するためのrad >> degree
                singu_check_link2_deg = Q_current[1]*(180/math.pi)
                
                #特異点は関節２が0,180,360度のとき。その付近は値が発散して解が求まらないのと、180度はハードウェア的に不可能なため。
                if (abs(singu_check_link2_deg - 0) <= 5) or (abs(singu_check_link2_deg - 180) <= 5) or (abs(singu_check_link2_deg - 360) <= 5):
                    print("特異点付近なので危険です", singu_check_link2_deg)
                    return P_current, Q_current, False
                P_current[2] = np.rad2deg(P_current[2])
                
                Q_current = np.rad2deg(Q_current)

                """
                if link1_deg > 180:
                    link1_deg = link1_deg - 360
                elif link2_deg > 180:
                    link2_deg = link2_deg - 360
                elif link3_deg > 180:
                    link3_deg = link3_deg - 360
            
                """
                i = 0

                return P_current, Q_current, True
            
            if i == self.max_loop_num-1:
                print("位置を計算できませんでした（特異点，もしくは実現不可能な座標の可能性があります）",i)
                return P_current, Q_current, False

#以下はデバッグ用のコード
if __name__ == '__main__':
    ik_solver = InverseKinematicsSolver()

    
    P_current_input = np.array([0, 0, 90])        #[現在のx座標, 現在のy座標, 現在のEEの角度]
    P_goal_input = np.array([0, 200 , 90])      #[目標のx座標, 目標のy座標, EEの進入角度]
    Q_current_input = np.array([170 , -170 , 90 ]) #[link1の角度, link2の角度, link3の角度]
    
    print("P_current_input[2]",np.deg2rad(P_current_input[2]))

    P_c, Q_c, success = ik_solver.solve_ik(P_current_input, P_goal_input, Q_current_input)
    
    if success:

        print("現在の手先位置と現在のEE角度", P_current_input)
        print("目標の手先座標とEE角度,P_goal_input", P_goal_input)
        print("計算結果の座標と角度",P_c)
        print("新しいリンク角度:", Q_c)
        print("問題なく解けました。")
    else:
        print("特異点を通過しました。解けませんでした。")


