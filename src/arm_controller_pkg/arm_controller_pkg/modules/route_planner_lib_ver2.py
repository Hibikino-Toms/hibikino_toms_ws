import numpy as np
import matplotlib.pyplot as plt

import math

#10/29 単位をcmからmmに変更



class Node():
    def __init__(self, x, y, parent, way_flag = True):
        self.x = x
        self.y = y
        self.xy = np.array([x,y])
        self.parent = parent 
        self.way_flag = way_flag


class RoutePlanner():
    def reset(self, init_posi, init_deg):
        # 最初のエンドエフェクタの角度
        self.init_deg = init_deg
        #ホームポジションの座標
        self.init = init_posi
        self.init_x = self.init[0]
        self.init_y = self.init[1]
        # 障害物の定義
        self.prior_node = []
        #self.obstacles = obstacles

        # パラメータ群
        self.d = 50 # 伸ばし幅
        self.g_range = 60 # どこまでゴールに近づければいいか
        
        # 探索範囲
        # self.MAX_x = 1200
        self.MAX_y = 650
        
        # ノード
        self.Nodes_list = [Node(self.init_x, self.init_y, None, way_flag=False)]
        self.Nodes_posi = np.array([[self.init_x, self.init_y]])
        # path
        self.path_x = np.empty((0,2),float)
        self.path_y = np.empty((0,2), float)
        # samples
        self.samples = np.empty((0,2), float)
        self.nearest_node = None
        self.new_node = None
        
    def search(self,New_goal_posi,random_search_ena, approach_deg):
        # random_search_enaがTrueのとき、ランダムにノードを探索する
        
        if random_search_ena == True:
            # print("ランダムにノードを打つ")   
            if approach_deg >= 90:
                s_x = np.random.uniform(self.goal[0], 500)

            else:
                s_x = np.random.uniform(-500, self.goal[0])
            
                
            s_y = (np.random.rand() * self.MAX_y)
            
            self.sample = np.array([s_x, s_y])
        # Falseのとき、ゴールに向かってノードを打つ
        else:
            # print("新しく打つノードでゴールを選択")
            s_x = New_goal_posi[0]
            s_y = New_goal_posi[1]

            self.sample = np.array([s_x, s_y])


        distance = float('inf')
        self.nearest_node = None

        for i in range(len(self.Nodes_list)):
            node = self.Nodes_list[i]
            #print("self.node", self.Nodes_list)
            #print("node",node.x)
            part_MSE = (self.sample - node.xy) * (self.sample - node.xy)
            RMSE = math.sqrt(sum(part_MSE))
            #print("RMSE", RMSE)

            # 距離が小さかったら追加
            if RMSE < distance:
                #print("distance",distance)
                distance = RMSE
                self.nearest_node = node # node type

        #print("node.x, node.y", self.nearest_node.xy)

        # 新ノードを作成
        pull = self.sample - self.nearest_node.xy
        #print("pull",pull)
        grad = math.atan2(pull[1], pull[0])

        d_x = math.cos(grad) * self.d
        d_y = math.sin(grad) * self.d
        

        new_node_xy = self.nearest_node.xy + np.array([d_x, d_y])
        

        self.new_node = Node(new_node_xy[0], new_node_xy[1], self.nearest_node)

        
        near = self.nearest_node  # 新しいノードに一番近いノード
        new = self.new_node       # 新しいノード

        
        return near, new    

    def check_goal(self): # ゴールしたかどうかを確かめる関数

        dis = np.sqrt(sum((self.new_node.xy - self.goal) *  (self.new_node.xy - self.goal)))
        goal_flag = False
        #print('dis = {0}'.format(dis))
        if dis < self.g_range:
            # print('GOAL!!')
            goal_flag = True

        return goal_flag

    def make_all_path(self):# 追加処理
        # 新ノードを追加
        self.Nodes_list.append(self.new_node)
        #self.Nodes_posi =  np.vstack((self.Nodes_posi, self.new_node.xy))

        #self.path_x = np.append(self.path_x, np.array([[self.nearest_node.x, self.new_node.x]]), axis=0)
        #self.path_y = np.append(self.path_y, np.array([[self.nearest_node.y, self.new_node.y]]), axis=0)

        #self.samples = np.append(self.samples, [[self.sample[0], self.sample[1]]], axis=0)

    def make_final_path(self):
        # ノードリストの一番最後、つまりgoal位置を代入
        final_path = [[self.Nodes_list[-1].x, self.Nodes_list[-1].y]]
        
        lastindex = len(self.Nodes_list) - 1

        # Nodes_listの数だけwhileを回す。way_flagは最後の要素、つまり初期位置までTrue.
        while self.Nodes_list[lastindex].way_flag:
            # 一番最後に打ったノードはゴールに最も近づいたノードであるため、そのままlastindexから代入
            node = self.Nodes_list[lastindex]
            # final_pathに"node"座標の行を加える。
            final_path = np.vstack((final_path, [[node.x, node.y]]))
            # そのノードの親になっているノードの索引をlastindexに代入する。
            # parent:このノードがどのノードから生成されたかを示す参照
            lastindex = self.Nodes_list.index(node.parent)
            # print('last= {0}'.format(lastindex))

        #　初期位置を追加している
        final_path = np.vstack((final_path, [[self.init_x, self.init_y]]))
        final_path = np.delete(final_path, 0, axis = 0)
    
        return final_path
    
    def prior_node_setting(self, Goal_Posi, Approach_Angle): # 指定した進入角度で収穫するために、事前にノードを打つ関数

        rad = Approach_Angle*(math.pi/180) - math.pi

        self.prior_node.append(Goal_Posi)
        near_node = np.array(Goal_Posi)

        # 2回ループを回して、2個の事前ノードを進入角度で打っている。
        for i in range(2):
            prior_x = 20 * math.cos(rad)
            prior_y = 20 * math.sin(rad)
            near_node = near_node + [prior_x, prior_y]
            self.prior_node.append([near_node[0], near_node[1]])

        return self.prior_node
    
    def check_collision(self, obstacles, current_node, previous_node):

        #現在のノードと過去のノードから角度を計算する
        delta_x = current_node.x - previous_node.x
        delta_y = current_node.y - previous_node.y
        angle = np.arctan2(delta_y, delta_x)

        #矩形の先端から中心に向かって50mm伸ばすオフセット
        offset_distance = 50

        #オフセットのx, y成分を計算する
        offset_x = offset_distance *np.cos(angle)
        offset_y = offset_distance *np.sin(angle)

        # 矩形の中心の座標を求める
        center_x = current_node.x - offset_x
        center_y = current_node.y - offset_y

        rx = center_x
        ry = center_y
        rw = 100
        rh = 120

        #回転角度のコサインとサインを計算する
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)

        for obstacle in obstacles:
            cx, cy, r = obstacle #円の中心座標(cx, cy)

            # 円の中心を矩形のローカル座標に変換する
            local_cx = cos_angle*(cx - rx) + sin_angle*(cy - ry)
            local_cy = -sin_angle*(cx -rx) + cos_angle*(cy -ry)

            if local_cx < -rw / 2:
                closest_x = -rw / 2 # 左端
            elif local_cx > rw / 2:
                closest_x = rw / 2 # 右端
            else:
                closest_x = local_cx
            
            if local_cy < -rh / 2:
                closest_y = -rh / 2
            elif local_cy > rh / 2:
                closest_y = rh / 2
            else:
                closest_y = local_cy
            
            #円の中心と、最も近い点との距離を計算する
            distance_x = local_cx - closest_x
            distance_y = local_cy - closest_y

            #距離が円の半径より小さい場合、交差が発生している
            distance_squared = distance_x **2 + distance_y**2
            # print(f"障害物 {obstacle} に対する矩形の最も近い点: ({closest_x}, {closest_y})")
            # print(f"距離の平方: {distance_squared}, 障害物の半径の平方: {r ** 2}")

            # 求めた距離が障害物の半径より短い時、衝突したと判定し、Trueを返す
            if distance_squared <= r **2:
                return True
    
        return False
    
    def solve_rrt(self, goal, approach_angle, obstacles):
        # 障害物があるときlenは0ではない。
        if len(obstacles) == 0:
            has_obstacle = False # 障害物がない時False
        else:
            has_obstacle = True # 障害物がある時True

        count = 0
        random_search_ena = False
        
        # 事前に指定した角度で収穫するために、事前にゴールから2つのノードを置いている。
        prior_final_path = self.prior_node_setting(goal, approach_angle)
        new_goal_posi = prior_final_path[2]
        new_goal_posi_y = new_goal_posi[1]

        self.MAX_y = new_goal_posi_y
        
        self.goal = new_goal_posi # 新しいゴールを事前に設定したノードに変更している。　

        # print("goal:",self.goal)
        while True:
            count += 1
            # print("count", count)
            # 探索する。ゴール座標と、ランダム(True) or ゴールを選択してノードを置く(False)かのbool変数。最初のループはFalse固定
            old, current = self.search(new_goal_posi, random_search_ena, approach_angle)
            # 障害物に接触した時だけランダムになってほしいので、この変数がTrueだった場合にFalseに変える必要がある。
            random_search_ena = False
            
            # 障害物がある時のみTrueになる
            if has_obstacle == True:
                
                # EFの矩形と障害物（円）の接触判定, 接触したらTrueを返す
                contact_with_obstacles = self.check_collision(obstacles, current, old)

                if contact_with_obstacles == True:
                    #接触したら、次のwhile loopによるノードの探索をランダムに行う。
                    random_search_ena = True
                    print("＞＞＞＞＞＞＞＞＞＞＞EFと障害物との接触＜＜＜＜＜＜＜＜＜＜＜＜＜＜＜")
                    #いつまでたってもルートが見つからないときはNoneを返して、ルート探索不可を示す。
                    if count > 300:
                        return None
                    #print("------------------------------------")
                    continue


            # ゴールしたかどうかのチェック. ゴールしたらTrueを返す
            flag = self.check_goal()

            # あたしく追加していっているノードをNode_listに格納するための関数
            self.make_all_path()
            # flagがTrueのとき、ゴールしている。
            if flag:
                #print("goal:",count)
                rest_path = self.make_final_path()
                final_path = np.vstack((prior_final_path,rest_path))
                final_path = final_path[::-1]
                
                #final_path = np.insert(final_path[0], 2, self.init_deg)
                degree = [self.init_deg]
                for j in range(len(final_path) -1):
                    # print(f"{len(final_path)-1}のうち、{j}回目のループはじめ")
                    deg = final_path[j+1] - final_path[j]

                        
                    grad = math.atan2(deg[1], deg[0])
                    degree.append(grad* 180/math.pi)
                    #print("degree",degree)
                    # degree = grad * 180/math.pi
                    # final_path = np.insert(final_path[j+1], 2, degree)

                final_path_degree = np.column_stack((final_path, degree))
                #print("-------final_path-------:",final_path_degree)

                return final_path_degree
            
            #いつまでたってもルートが見つからないときはNoneを返して、ルート探索不可を示す。
            if count > 300:
                return None
            # print("-----------------------------------------")


if __name__ == "__main__":
    # ----------------以下デバッグ用-------------------------
    for i in range(0,2):
        print("debug now")
        init = [0,162.5]
        init_deg = 90
        goal_posi = [80, 400]
        approach_angle = 135
        # obstacles = np.array([[50, 200, 30],[200,300,30]])
        obstacles = []

        final_path_instance = RoutePlanner(init,init_deg) #! ホームポジションの座標（EFの先端座標）と　EFの角度
        final_path = final_path_instance.solve_rrt(goal_posi,approach_angle,obstacles) #! ゴール座標, 進入角度, 障害物の座標
        print(final_path)
    # i = 0

    # if final_path is None:
    #     print("None")
    # else:
    #     width, height = 120, 100

    #     print(final_path)

    #     # Extract x and y values
    #     x_values = final_path[:, 0]
    #     y_values = final_path[:, 1]

    #     # Plot the path
    #     plt.plot(x_values, y_values, '-o', color='blue', label='Path')

    #     # Mark the start and end points with different colors
    #     plt.plot(x_values[0], y_values[0], 'go', label='Start')  # Green for start
    #     plt.plot(x_values[-1], y_values[-1], 'ro', label='Tomato')  # Red for end

    #     plt.plot(x_values[-2], y_values[-2], 'yo', label='Second-to-last')  # Yellow for second-to-last
    #     plt.plot(x_values[-3], y_values[-3], 'co', label='Third-to-last')   # Cyan for third-to-last

    #     # 障害物（円）の描画
    #     for obstacle in obstacles:
    #         center_x, center_y, diameter = obstacle
    #         radius = diameter
    #         circle = plt.Circle((center_x, center_y), radius, color='b', fill=False)
    #         plt.gca().add_patch(circle)  # axを使わず描画

    #     # Set equal scaling for both axes
    #     plt.gca().set_aspect('equal', adjustable='box')

    #     # Set fixed limits for x and y axes
    #     plt.xlim(-300, 300)  # Fix x-axis range from -30 to 30
    #     plt.ylim(-50, 600)  # Fix y-axis range from -30 to 30
    #     # Add labels and title
    #     plt.xlabel('X')
    #     plt.ylabel('Y')
    #     plt.title('Path Plot with Start and End Points Highlighted')

    #     # Display the legend
    #     plt.legend()

    #     # Show the plot
    #     plt.grid(True)
    #     plt.show()

