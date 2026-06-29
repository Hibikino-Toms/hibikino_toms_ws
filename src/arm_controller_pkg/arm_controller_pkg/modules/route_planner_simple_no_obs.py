import math
import numpy as np

class RoutePlanner():
    def __init__(self, params):
        self.init_x = None
        self.init_y = None
        self.init_deg = None
        self.goal = None
        
        vision_params = params["vision_params"]
        arm_params = params["arm_params"]
        self.ANGLE = vision_params["APPROACH_ANG"]
        self.OFFSET_X = arm_params["OFFSET_X"]

    def reset(self, init_posi, init_deg):
        """
        初期位置と初期角度を設定する。
        :param init_posi: 初期位置の座標 [x, y]
        :param init_deg: 初期角度 (degree)
        """
        self.init_x = init_posi[0]
        self.init_y = init_posi[1]
        self.init_deg = init_deg

    def solve_rrt(self, goal, approach_angle, obstacles):
        """
        注意：RRTは使用していない。単純な経路生成のみ
        :param goal: ゴール位置の座標 [x, y]
        :param approach_angle: アプローチ角度 (degree)
        :param obstacles: 障害物（ここでは必ず空配列が入る）
        :return: 経路点 [x, y, degree] の配列
        """
        # 障害物がない前提なのでスキップ
        if len(obstacles) != 0:
            raise ValueError("障害物は存在しない前提です。空の配列を入力してください。")
        
        # # アーム制御時、x座標がself.OFFSET_Xの分、左（ロボット進行方向と反対）に誤差あり。
        # goal[0] += self.OFFSET_X
        self.goal = goal
        
        # スタート位置とゴール点のユークリッド距離を計算
        d_start_goal_squa = ((goal[0] - self.init_x) ** 2 + (goal[1] - self.init_y) ** 2)
        # print(f"d_start_goal_squa: {d_start_goal_squa}")
        
        # 事前ノードのサイズを決定
        if 30**2 > d_start_goal_squa:
            prior_node_size = math.sqrt(d_start_goal_squa)
        else:
            prior_node_size = 30
        
        rad = math.radians(approach_angle) - math.pi
        
        # アプローチ角度から事前ノードを計算
        if approach_angle != 90:
            prior_x = goal[0] + prior_node_size * math.cos(rad)
            prior_y = goal[1] + prior_node_size * math.sin(rad)
            prior_node = [prior_x, prior_y, approach_angle]
            second_node = [prior_x, prior_y-30, 90] # 接触回避用ノード
            # 出力経路: 初期位置→接触回避用ノード→事前ノード→ゴール
            path = [
                [self.init_x, self.init_y, self.init_deg],
                second_node,
                prior_node,
                [goal[0], goal[1], approach_angle]
            ]
        else:
            prior_node = [goal[0], goal[1]-prior_node_size, approach_angle]
            # 出力経路: 初期位置→事前ノード→ゴール
            path = [
                [self.init_x, self.init_y, self.init_deg],
                prior_node,
                [goal[0], goal[1], approach_angle]
            ]
        
        return np.array(path)

# 使用例
if __name__ == "__main__":
    planner = RoutePlanner()
    planner.reset(init_posi=[0, 0], init_deg=0)

    goal = [200, 200]
    approach_angle = 45
    obstacles = []

    path = planner.solve_rrt(goal, approach_angle, obstacles)
    print("Generated Path:")
    print(path)
