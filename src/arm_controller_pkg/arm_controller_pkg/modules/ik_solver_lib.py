import numpy as np
from math import atan2, sin, cos


import numpy as np
from math import sin, cos

"""
2024/10/6 時点

3リンク水平マニピュレータの逆運動学ライブラリ
@autor yoshida

去年のコード
今年度は、長崎作成のコードに変更
"""


"""
[input]

[output]

"""

class InverseKinematicsSolver:
    def __init__(self):
        self.L1 = 300.0   #[mm]
        self.L2 = 300.0   #[mm]
        self.L3 = 150.0   #[mm]
        
        # 角度制約
        self.min_angle_1 = np.radians(0)  
        self.max_angle_1 = np.radians(110)
        self.min_angle_2 = np.radians(-40)  
        self.max_angle_2 = np.radians(130)
        self.min_angle_3 = np.radians(-80)  
        self.max_angle_3 = np.radians(80)

        # 初期角度
        self.theta1 = np.radians(30.0)
        self.theta2 = np.radians(60.0)
        self.theta3 = np.radians(0.0)

        self.algorithms ={
            "newton_raphson":self.newton_raphson_ik,
            "gradient_descent":self.gradient_descent_ik 
        }

    def forward_kinematics(self, theta1, theta2, theta3):
        x = self.L1 * cos(theta1) + self.L2 * cos(theta1 + theta2) + self.L3 * cos(theta1 + theta2 + theta3)
        y = self.L1 * sin(theta1) + self.L2 * sin(theta1 + theta2) + self.L3 * sin(theta1 + theta2 + theta3)
        return x, y

    def solve_ik(self, x_target, z_target, alpha_target, method="newton_raphson", max_iterations=100):
        if method in self.algorithms:
            return self.algorithms[method](x_target, z_target, np.radians(alpha_target), max_iterations=max_iterations)
        else:
            print("Invalid method specified.")
            return None

    def newton_raphson_ik(self, x_target, z_target, alpha_target, max_iterations=100, tolerance=10,tolerance_alpha=0.03):
        # if z_target >7000 :
        #     return None
        for i in range(max_iterations):
            x_end_effector, y_end_effector = self.forward_kinematics(self.theta1, self.theta2, self.theta3)
            error_x = x_target - x_end_effector
            error_y = z_target - y_end_effector
            error_alpha = alpha_target - (self.theta1 + self.theta2 + self.theta3)

            if (abs(error_x) < tolerance and abs(error_y) < tolerance and abs(error_alpha) < tolerance_alpha):
                print(f"Converged after {i} iterations.")
                return self.theta1,self.theta2,self.theta3

            J11 = -self.L1 * sin(self.theta1) - self.L2 * sin(self.theta1 + self.theta2) - self.L3 * sin(self.theta1 + self.theta2 + self.theta3)
            J12 = -self.L2 * sin(self.theta1 + self.theta2) - self.L3 * sin(self.theta1 + self.theta2 + self.theta3)
            J13 = -self.L3 * sin(self.theta1 + self.theta2 + self.theta3)
            J21 = self.L1 * cos(self.theta1) + self.L2 * cos(self.theta1 + self.theta2) + self.L3 * cos(self.theta1 + self.theta2 + self.theta3)
            J22 = self.L2 * cos(self.theta1 + self.theta2) + self.L3 * cos(self.theta1 + self.theta2 + self.theta3)
            J23 = self.L3 * cos(self.theta1 + self.theta2 + self.theta3)
            J31 = 1

            J = np.array([[J11, J12, J13],
                          [J21, J22, J23],
                          [J31, J31, J31]])

            J_pseudo_inv = np.linalg.pinv(J)
            # ニュートン・ラフソン法の更新
            delta_theta = np.dot(J_pseudo_inv, np.array([error_x, error_y, error_alpha]))
            self.theta1 = np.clip(self.theta1 + delta_theta[0], self.min_angle_1, self.max_angle_1)
            self.theta2 = np.clip(self.theta2 + delta_theta[1], self.min_angle_2, self.max_angle_2)
            self.theta3 = np.clip(self.theta3 + delta_theta[2], self.min_angle_3, self.max_angle_3)

        self.theta1 = np.radians(20.0)
        self.theta2 = np.radians(70.0)
        self.theta3 = np.radians(0.0)

            
        
    def gradient_descent_ik(self, x_target, z_target, alpha_target,max_iterations=100, convergence_threshold = 0.01, learning_rate = 0.01):
        for i in range(max_iterations):
            x_end_effector, y_end_effector = self.forward_kinematics(self.theta1, self.theta2, self.theta3)
            error_x = x_target - x_end_effector
            error_y = z_target - y_end_effector
            error_alpha = alpha_target - (self.theta1 + self.theta2 + self.theta3)
            
            # 誤差ベクトルのノルムを計算
            error_norm = np.sqrt(error_x**2 + error_y**2 + error_alpha**2)

            # 収束判定
            if error_norm < convergence_threshold:
                print(f"Converged after {i} iterations")
                break
                
            epsilon = 1e-6  # 数値微分の微小値
            grad_theta1 = (error_norm - np.sqrt((x_target - x - epsilon)**2 + (z_target - y)**2 + (alpha_target - alpha)**2)) / epsilon
            grad_theta2 = (error_norm - np.sqrt((x_target - x **2 + (z_target - y - epsilon)**2 + (alpha_target - alpha)**2))) / epsilon
            grad_theta3 = (error_norm - np.sqrt((x_target - x )**2 + (z_target - y)**2 + (alpha_target - alpha - epsilon)**2)) / epsilon

            self.theta1 -= learning_rate * grad_theta1
            self.theta2 -= learning_rate * grad_theta2
            self.theta3 -= learning_rate * grad_theta3

        return self.theta1,self.theta2,self.theta3