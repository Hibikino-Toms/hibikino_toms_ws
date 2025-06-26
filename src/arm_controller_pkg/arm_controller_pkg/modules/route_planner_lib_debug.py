import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as ani
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
    def __init__(self, init, init_deg): #obstacles):
        #初期設定
        #ホームポジションの座標
        self.init_x = init[0]
        self.init_y = init[1]
        # 最初のエンドエフェクタの角度
        self.init_deg = init_deg
        """
        self.goal_x = goal[0]
        self.goal_y = goal[1]
        self.goal = goal
        """
        self.prior_node = []
        self.approach_deg = approach_angle
        #self.obstacles = obstacles


        # 最初のエンドエフェクタの角度


        # パラメータ群
        #　伸ばし幅
        self.d = 30
        # 10回に２回はゴールを選ぶ
        self.g_rate = 0.4
        # どこまでゴールに近づければいいか
        self.g_range = 60

        # 探索範囲
        # self.MAX_x = 1200
        self.MAX_y = 650

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
    
    def search(self,New_goal_posi, ob_flag):
        # 行動決定（何回かに一回はGoalを選ぶ）
        temp = np.random.randint(0, 10)

        #障害物がない時はゴールに直線的に移動させる
        if ob_flag == False:
            
            if temp > 2:
                #s_x = (np.random.rand() * self.MAX_x) - self.MAX_x/2
                
                if self.approach_deg >= 90:
                    s_x = np.random.uniform(self.goal[0], 500)

                else:
                    s_x = np.random.uniform(-500, self.goal[0])
                
                    
                s_y = (np.random.rand() * self.MAX_y)
                
                self.sample = np.array([s_x, s_y])
            else:
                # goalを選ぶ
                s_x = New_goal_posi[0]
                s_y = New_goal_posi[1]

                self.sample = np.array([s_x, s_y])
        
        else:

            s_x = New_goal_posi[0]
            s_y = New_goal_posi[1]

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
        

        self.new_node = Node(new_node_xy[0], new_node_xy[1], self.nearest_node)
        

        return self.nearest_node, self.new_node

    #障害物がある時に使う
    
    def check_obstacles(self, obstacles):
        obstacle_flag = False
        for i in range(obstacles.shape[0]):
            # [i, :2]は、i行目の最初の２列要素を取得する
            obs_dis = np.sqrt(sum((self.new_node.xy - obstacles[i, :2]) * (self.new_node.xy - obstacles[i, :2])))
            # [i, 2]は、i行目の３番目の要素を取得する
            if obs_dis < obstacles[i, 2]:
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
            print('last= {0}'.format(lastindex))

        final_path = np.vstack((final_path, [[self.init_x, self.init_y]]))
        final_path = np.delete(final_path, 0, axis = 0)
        print("final_path:",final_path)
    
        return final_path
    
    def prior_node_setting(self, Goal_Posi, Approach_Angle):

        rad = Approach_Angle*(math.pi/180) - math.pi

        self.prior_node.append(Goal_Posi)
        near_node = np.array(Goal_Posi)

        for i in range(2):
            prior_x = 50 * math.cos(rad)
            prior_y = 50 * math.sin(rad)
            near_node = near_node + [prior_x, prior_y]
            self.prior_node.append([near_node[0], near_node[1]])

        return self.prior_node
    
    def solve_rrt(self, goal, approach_angle, obstacles):

        if len(obstacles) == 0:
            obstacle_flag = True
        else:
            obstacle_flag = False
        
        print(obstacle_flag)

        count = 0
        prior_final_path = self.prior_node_setting(goal, approach_angle)
        new_goal_posi = prior_final_path[2]
        new_goal_posi_y = new_goal_posi[1]


        self.MAX_y = new_goal_posi_y
        self.goal = new_goal_posi

        print("goal:",self.goal)
        while True:
            count += 1
            self.search(new_goal_posi, obstacle_flag)
            if obstacle_flag == False:

                obstacle_touch_flag = self.check_obstacles(obstacles)
                
                if obstacle_touch_flag:
                    # 障害物に接触したら、この時点でこのループの処理は終了し、次のループを開始する。
                    continue


            flag = self.check_goal()
            # print("flag",flag)
            self.make_all_path()
            if flag:
                print("goal:",count)
                rest_path = self.make_final_path()
                final_path = np.vstack((prior_final_path,rest_path))
                final_path = final_path[::-1]
                
                #final_path = np.insert(final_path[0], 2, self.init_deg)
                degree = [self.init_deg]
                for j in range(len(final_path) -1):
                    print(f"{len(final_path)-1}のうち、{j}回目のループはじめ")
                    deg = final_path[j+1] - final_path[j]
                    #print("deg", deg)

                        
                    grad = math.atan2(deg[1], deg[0])
                    degree.append(grad* 180/math.pi)
                    #print("degree",degree)
                    # degree = grad * 180/math.pi
                    # final_path = np.insert(final_path[j+1], 2, degree)

                final_path_degree = np.column_stack((final_path, degree))

                return final_path_degree
            print("-----------------------------------------")

            if count >= 300:
                return None
    
    """
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
            print("-----------------------------------------")
    """
            



init = [0,100]
goal_posi = [0, 350]
init_deg = 135
approach_angle = 135
obstacles = np.array([[0, 250, 60], [200, 150 , 60]])
#obstacles = []
final_path_instance = RoutePlanner(init,init_deg)
final_path = final_path_instance.solve_rrt(goal_posi,approach_angle,obstacles)

if final_path is None:
    print("None")
else:


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

    plt.plot(x_values[-2], y_values[-2], 'yo', label='Second-to-last')  # Yellow for second-to-last
    plt.plot(x_values[-3], y_values[-3], 'co', label='Third-to-last')   # Cyan for third-to-last


    # 障害物（円）の描画
    for obstacle in obstacles:
        center_x, center_y, diameter = obstacle
        radius = diameter / 2
        circle = plt.Circle((center_x, center_y), radius, color='b', fill=False)
        plt.gca().add_patch(circle)  # axを使わず描画

    # Set equal scaling for both axes
    plt.gca().set_aspect('equal', adjustable='box')

    # Set fixed limits for x and y axes
    plt.xlim(-300, 300)  # Fix x-axis range from -30 to 30
    plt.ylim(-50, 600)  # Fix y-axis range from -30 to 30
    # Add labels and title
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.title('Path Plot with Start and End Points Highlighted')

    # Display the legend
    plt.legend()

    # Show the plot
    plt.grid(True)
    plt.show()

