"""
@author nagasaki taichi, 長﨑
---------------------------------------------------------------------------
RRT探索アルゴリズムのクラス
使用例:final_path = RoutePlanner(goal_posi, approach_angle).solve_rrt()
クラスの引数には、トマトの座標[x, y], エンドエフェクタの進入角度（度）を使うこと
solve.rrt()の返り値は、エンドエフェクタの先端が通る座標を返す[[x, y], [x1, y2]...]
最初の座標は[0,0](初期位置),最後の要素はゴール座標になっている
ノードを300個打って、ゴールに到達できなかったら、return Noneを返す


2024/10/06 時点

調整できる点としては、伸ばし幅
self.d = 3 ~ 5


"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as ani
import math


class Node():
    def __init__(self, x, y, parent, way_flag = True):
        self.x = x
        self.y = y
        self.xy = np.array([x,y])
        self.parent = parent 
        self.way_flag = way_flag


class RoutePlanner():
    def __init__(self, goal, approach_angle): #obstacles):
        #初期設定
        self.init_x = 0
        self.init_y = 0
        self.goal_x = goal[0]
        self.goal_y = goal[1]
        self.goal = goal
        self.prior_node = []
        self.approach_deg = approach_angle
        #self.obstacles = obstacles


        # 最初のエンドエフェクタの角度
        self.init_deg = math.pi/2

        # パラメータ群
        #　伸ばし幅
        self.d = 3
        # 10回に２回はゴールを選ぶ
        self.g_rate = 0.4
        # どこまでゴールに近づければいいか
        self.g_range = 5

        # 探索範囲
        self.MAX_x = 120
        self.MAX_y = 65

        # ノードを作成する
        # これはただのノード
        self.Nodes_list = [Node(self.init_x, self.init_y, None, way_flag=False)]
        self.Nodes_posi = np.array([[self.init_x, self.init_y]])
        # これはpath
        self.path_x = np.empty((0,2),float)
        self.path_y = np.empty((0,2), float)
        # samples
        self.samples = np.empty((0,2), float)

        self.nearest_node = None
        self.new_node = None
    
    def search(self):
        # 行動決定（何回かに一回はGoalを選ぶ）
        temp = np.random.randint(0, 10)
        
        if temp > 3:
            #s_x = (np.random.rand() * self.MAX_x) - self.MAX_x/2
            
            if self.approach_deg >= 90:
                s_x = np.random.uniform(self.goal[0], 60)

            else:
                s_x = np.random.uniform(-60, self.goal[0])
            
                
            s_y = (np.random.rand() * self.MAX_y)
            
            self.sample = np.array([s_x, s_y])
        else:
            # goalを選ぶ
            s_x = self.goal_x
            s_y = self.goal_y

            self.sample = np.array([s_x, s_y])

        #print("s_x,s_y",s_x,s_y)
        # ノード探索
        distance = float('inf')
        self.nearest_node = None
        #print("aaaaaaaaaaaaaa")
        #print("長さ",len(self.Nodes_list))

        
        for i in range(len(self.Nodes_list)):
            node = self.Nodes_list[i]
            #print("node",node)
            part_MSE = (self.sample - node.xy) * (self.sample - node.xy)
            RMSE = math.sqrt(sum(part_MSE))
            #print("RMSE", RMSE)

            # 距離が小さかったら追加
            if RMSE < distance:
                #print("distance",distance)
                distance = RMSE
                self.nearest_node = node # node type
                #print(self.nearest_node)

        # 新ノードを作成
        pull = self.sample - self.nearest_node.xy
        #print("pull",pull)
        grad = math.atan2(pull[1], pull[0])

        d_x = math.cos(grad) * self.d
        d_y = math.sin(grad) * self.d
        

        new_node_xy = self.nearest_node.xy + np.array([d_x, d_y])
        #print("new_node_xy",new_node_xy)

        self.new_node = Node(new_node_xy[0], new_node_xy[1], self.nearest_node)
        

        return self.nearest_node, self.new_node

    def check_obstacles(self):
        obstacle_flag = False
        for i in range(self.obstacles.shape[0]):
            # [i, :2]は、i行目の最初の２列要素を取得する
            obs_dis = np.sqrt(sum((self.new_node.xy - self.obstacles[i, :2]) * (self.new_node.xy - self.obstacles[i, :2])))
            # [i, 2]は、i行目の３番目の要素を取得する
            if obs_dis < self.obstacles[i, 2]:
                print('Collision!!')
                obstacle_flag = True

        return obstacle_flag

    def check_goal(self):

        dis = np.sqrt(sum((self.new_node.xy - self.goal) *  (self.new_node.xy - self.goal)))
        goal_flag = False
        #print('dis = {0}'.format(dis))
        if dis < self.g_range:
            print('GOAL!!')
            goal_flag = True

        return goal_flag

    def make_all_path(self):# 追加処理
        # 新ノードを追加
        self.Nodes_list.append(self.new_node)
        self.Nodes_posi =  np.vstack((self.Nodes_posi, self.new_node.xy))

        self.path_x = np.append(self.path_x, np.array([[self.nearest_node.x, self.new_node.x]]), axis=0)
        self.path_y = np.append(self.path_y, np.array([[self.nearest_node.y, self.new_node.y]]), axis=0)

        self.samples = np.append(self.samples, [[self.sample[0], self.sample[1]]], axis=0)

        #return self.Nodes_posi, self.path_x, self.path_y, self.samples

    def make_final_path(self):
        final_path = [[self.Nodes_list[-1].x, self.Nodes_list[-1].y]]
        

        lastindex = len(self.Nodes_list) - 1

        #print("aaaaa",lastindex)
        while self.Nodes_list[lastindex].way_flag:
        
            node = self.Nodes_list[lastindex]
            final_path = np.vstack((final_path, [[node.x, node.y]]))
            lastindex = self.Nodes_list.index(node.parent)
            print('last= {0}'.format(lastindex))

        final_path = np.vstack((final_path, [[self.init_x, self.init_y]]))
        final_path = np.delete(final_path, 0, axis = 0)

        #print(final_path)

        return final_path
    
    def prior_node_setting(self, Goal_Posi, Approach_Angle):

        rad = Approach_Angle*(math.pi/180) - math.pi

        self.prior_node.append(Goal_Posi)
        near_node = np.array(Goal_Posi)

        for i in range(2):
            prior_x = self.d * math.cos(rad)
            prior_y = self.d * math.sin(rad)
            near_node = near_node + [prior_x, prior_y]
            self.prior_node.append([near_node[0], near_node[1]])

        return self.prior_node
    
    def solve_rrt(self):
        count = 0
        prior_final_path = self.prior_node_setting(self.goal, self.approach_deg)
        new_goal_posi = prior_final_path[2]
        new_goal_posi_y = new_goal_posi[1]
        self.MAX_y = new_goal_posi_y
        self.goal = new_goal_posi
        print("goal:",self.goal)
        while True:
            count += 1
            self.search()
            flag = self.check_goal()
            # print("flag",flag)
            self.make_all_path()
            if flag:
                print("goal:",count)
                rest_path = self.make_final_path()
                final_path = np.vstack((prior_final_path,rest_path))
                final_path = final_path[::-1]
                return final_path
            
            if count >= 300:
                return None
        
    
    def solve_rrt_test(self):
        count = 0
        while True:
            count += 1
            self.search()
            flag = self.check_goal()
            # print("flag",flag)
            self.make_all_path()
            if flag:
                print("goal:",count)
                final_path = self.make_final_path()
                
                return final_path
            
            if count >= 300:
                return None
            
                
            


#以下デバッグ用
if __name__ == '__main__':

    
    goal_posi = [15, 30]
    approach_angle = 135
    #obstacles = np.array([[0, 20, 3]])

    #final_path = RoutePlanner(init, goal_posi,approach_angle).solve_rrt()
    final_path = RoutePlanner(goal_posi, approach_angle).solve_rrt()

    #path = path_planner.solve_rrt()

    print(final_path)

    # Extract x and y values
    x_values = final_path[:, 0]
    y_values = final_path[:, 1]

    # Plot the path
    plt.plot(x_values, y_values, '-o', color='blue', label='Path')

    # Mark the start and end points with different colors
    plt.plot(x_values[0], y_values[0], 'go', label='Start')  # Green for start
    plt.plot(x_values[-1], y_values[-1], 'ro', label='End')  # Red for end
    # Set equal scaling for both axes
    plt.gca().set_aspect('equal', adjustable='box')
    # Add labels and title
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.title('Path Plot with Start and End Points Highlighted')

    # Display the legend
    plt.legend()

    # Show the plot
    plt.grid(True)
    plt.show()
    