# #python tools
# import cv2 
# import numpy as np
# import yaml
# from shapely.geometry import Point, Polygon
# # デバッグ用
# # from test_transform import Transform_test

# """
# 2024/11/21 時点

# @author yoshinaga
# ----------------------
# 機能一覧
# [1] 収穫順番決定
# [2] 収穫可能トマト判定 
# [3] トマトへのアプローチ方向(入射角)決定 
# """

# # 座標変換ツール
# class Transform():
#     def __init__(self):
#         # YAMLファイルの読み込み
#         yaml_path='/home/ylab/hibikino_toms_ws/module/set_params.yaml'
#         params = self.load_yaml(yaml_path)
#         coordi_trans_params = params["coordinate_transform_params"]
        
#         # カメラからEE中心の距離…ロボット座標系（トマトに向かう方向がY）
#         X_DIFF_CAM2EE = coordi_trans_params['X_DIFF_CAM2EE']
#         Y_DIFF_CAM2EE = coordi_trans_params['Y_DIFF_CAM2EE']
#         Z_DIFF_CAM2EE = coordi_trans_params['Z_DIFF_CAM2EE']
#         # カメラの傾きを下向きから補正するための回転行列
#         CAM_ANGLE = coordi_trans_params['CAM_ANGLE']
#         CAM_THETA = np.deg2rad(CAM_ANGLE)  # 度→ラジアン
#         self.COS_THETA = np.cos(CAM_THETA)
#         self.SIN_THETA = np.sin(CAM_THETA)
#         # X軸の補正回転行列（35度上向きに補正）
#         self.ROTATION_MATRIX = np.array([
#             [1, 0, 0],
#             [0, self.COS_THETA, self.SIN_THETA],
#             [0, -self.SIN_THETA,  self.COS_THETA]
#         ])
#         # カメラからEEへの平行移動ベクトル
#         self.TRANSLATION_VECTOR_CAM2EE = np.array([X_DIFF_CAM2EE, Y_DIFF_CAM2EE, Z_DIFF_CAM2EE])
        
#         # EE中心からアーム付け根までの距離 ※アームがホームポジションのときの距離
#         X_DIFF_EE2ARM = coordi_trans_params['X_DIFF_EE2ARM']
#         Y_DIFF_EE2ARM = coordi_trans_params['Y_DIFF_EE2ARM']
#         Z_DIFF_EE2ARM = coordi_trans_params['Z_DIFF_EE2ARM']
#         # EEからアームへの平行移動ベクトル
#         self.TRANSLATION_VECTOR_EE2ARM = np.array([X_DIFF_EE2ARM, Y_DIFF_EE2ARM, Z_DIFF_EE2ARM])
    
#     @staticmethod
#     def load_yaml(file_path):
#         """YAMLファイルを読み込むヘルパー関数"""
#         try:
#             with open(file_path, "r") as file:
#                 return yaml.safe_load(file)
#         except FileNotFoundError:
#             raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
#         except yaml.YAMLError as e:
#             raise ValueError(f"YAMLファイルの解析エラー: {e}")

#     def pixel_to_mm(self, tom_h_pix, center_d):
#         # print(f'mask_height: {tom_h_pix}')
#         TAN_GAMMA = np.tan(np.deg2rad(29)) # 29°：RealSense D405 の縦の画角
#         tom_h_mm = (tom_h_pix/240) * center_d* TAN_GAMMA
#         # print(f'real_height: {tom_h_mm}')
#         return tom_h_mm
    
#     def transformation(self, cam_coordies, tom_heights_pixel, tomato_3d_posies):
#         tom_heights_mm = []
#         arm_coordies = np.empty((0,4))
#         ee_coordies = np.empty((0,3))
        
#         for tom_h_pix, pos in zip(tom_heights_pixel, tomato_3d_posies):
#             tom_h_mm = self.pixel_to_mm(tom_h_pix, pos[2]) # pos[2]:中心座標のデプス値
#             tom_heights_mm.append(tom_h_mm)
            
#         for cam_pos, tom_h in zip(cam_coordies, tom_heights_mm) :
#             # カメラ座標→EE座標
#             ee_coordi = self.camera_to_ee(cam_pos, tom_h)
#             ee_coordies = np.vstack((ee_coordies, ee_coordi))
#             # print(f'ee_coordi: {ee_coordi}')
            
#             # EE座標→アーム座標
#             arm_coordi = self.ee_to_arm(ee_coordi)
#             # print(f'arm_coordi: {arm_coordi}')
#             # if not all(arm_coordi):
#             #     ee_coordies = np.delete(ee_coordies, -1, axis=0)
#             #     continue
#             # else:
#             arm_coordi = np.append(arm_coordi, cam_pos[3]) # cam_pos[3]: アプローチ角度
#             arm_coordies = np.vstack((arm_coordies, arm_coordi))
#         return arm_coordies, ee_coordies
    
#     def camera_to_ee(self, cam_pos, tom_h):
#         X, Y, Z = cam_pos[0],cam_pos[2],-cam_pos[1] # 座標軸の変換（小文字：カメラ座標系/大文字：EE座標系 → Y=z、Z=y）
#         ee_coordi = np.array([X, Y, Z])
#         # 回転行列を適応して回転
#         cam_coordi_rotat = self.ROTATION_MATRIX @ ee_coordi
        
#         # 平行移動ベクトルを適用してEE座標に変換
#         ee_coordi = cam_coordi_rotat + self.TRANSLATION_VECTOR_CAM2EE
#         ee_coordi[1] = ee_coordi[1] - (tom_h/2)* (1 - self.COS_THETA)  # 斜め上から見たトマトの中心≠正面（EE）から見たトマトの中心なので、変換
#         ee_coordi[2] = ee_coordi[2] - (tom_h/2)* self.SIN_THETA
#         return ee_coordi
    
#     def ee_to_arm(self, ee_coordi):        
#         # 平行移動ベクトルを適用してARM座標に変換
#         arm_coordi = ee_coordi + self.TRANSLATION_VECTOR_EE2ARM
#         # if arm_coordi[1] > 550:
#         #     return [False, False, False]
#         return arm_coordi

# class Harvest_Order():  
#     def __init__(self, params):
#         #param
#         self.transform_tools = Transform()
#         self.threshold_distanse = 60
#         APRCH_ANG = params["APPROACH_ANG"]
#         self.left = int(APRCH_ANG)
#         self.right = int(180 - int(APRCH_ANG))
#         self.front = 90

#         #収穫可能エリア
#         harvestable_area = {
#             "bottom": [(0,180), (0,380), (350,380), (350,780), (-250,780), (-250,180)], # 底面の頂点座標
#             "hight": [(50, 600)]
#             }
#         self.harvestable_bottom = Polygon(harvestable_area["bottom"])
#         self.harvestable_hight = harvestable_area["hight"]

#     def set_approach_angle(self, tomato_posi): #harvest_judg
        
#         for tom_posi in tomato_posi:
#             print(f"tom_posi[3]: {tom_posi[3]}")
#             match tom_posi[3]:
#                 case -1:
#                     approach_ang = self.left
#                 case 0:
#                     approach_ang = self.front
#                 case 1:
#                     approach_ang = self.right
            
#             # approach_ang = self.right
#             tom_posi[3] = approach_ang
        
#         return tomato_posi
    
#     def obj_area_chech(self,bbox,seg_img):
#         area_chech = [0,0,0]
#         x_min = int(bbox[0])
#         x_max = int(bbox[1])
#         w = int(x_max - x_min)
#         y_min = int(bbox[2])
#         y_max = int(bbox[3])
#         h = int(y_max - y_min) 
#         if not np.any(seg_img[x_min:x_min+int(w/3),y_min:y_max] > 0) :
#             area_chech[0] == 1
#         if not np.any(seg_img[x_min+int(w/3):x_min+2*int(w/3),y_min:y_max] > 0) :
#             area_chech[1] == 1
#         if not np.any(seg_img[x_min+2*int(w/3):x_max,y_min:y_max] > 0) :
#             area_chech[2] == 1
#         return area_chech
    
#     # 呼び出し元の引数：result_tomato, result_main_stem, result_peduncle, depth_img, tomato_3d_posi
#     # def order_decision(self, result_tomato, depth_img, tomato_3d_posies, tom_heights_pixel):
#     def order_decision(self, tomato_3d_posies, tom_heights_pixel, tomato_dict):
#         target_poses = np.empty((0, 4))
#         idx = 0
#         if tomato_3d_posies is not None :
#             # カメラ座標＋EE進入角度
#             tom_pos_direction = self.set_approach_angle(tomato_3d_posies)
#             print(f'tom_pos_direction(カメラ座標 + EE進入角度): \n{tom_pos_direction}')
            
#             # カメラ座標からアーム座標に変換
#             # target_coordinates = self.transform_tools.transformation(tom_pos_direction_num)
#             arm_coordinates, ee_coordinates = self.transform_tools.transformation(tom_pos_direction, tom_heights_pixel, tomato_3d_posies)
#             print(f"arm_coordinates, ee_coordinates: \n{arm_coordinates, ee_coordinates}")

#             for tomato in tomato_dict:
#                 if tomato["is_ripe"]:  # "is_ripe"がTrueのトマトだけ処理
#                     # アーム座標を辞書に保存
#                     tomato["arm_coords"] = [arm_coordinates[idx][0],arm_coordinates[idx][1],arm_coordinates[idx][2]]
#                     # {
#                     #     "x": arm[0],
#                     #     "y": arm[1],
#                     #     "z": arm[2] # 適切な値が入っていない
#                     # }
                    
#                     # アーム座標+EE進入角度をtarget_posesに保存
#                     target_pos = [arm_coordinates[idx][0], arm_coordinates[idx][1], ee_coordinates[idx][2], arm_coordinates[idx][3]]
#                     target_poses = np.vstack((target_poses, target_pos))
#                     idx += 1
#             print(f'arm_coordinates(アーム座標): \n{target_poses}')
            
#             # 収穫順番決定
#             target_poses, tomato_dict = self.sorting(target_poses, tomato_dict)
#             print(f'target_poses sorted(並び替え後): \n{target_poses}')
            
#             return target_poses, tomato_dict
#         else :
#             return target_poses, tomato_dict
        
#     def sorting(self, tom_pos_matrix, tomato_dict):
#         # Step 1: アーム座標系y軸（第2要素）の昇順ソート
#         sorted_indices = np.argsort(tom_pos_matrix[:, 1])  # y軸（奥行き）の値で昇順ソート
#         tom_pos_matrix = tom_pos_matrix[sorted_indices]

#         # Step 2: グループ化準備（αの順序付けと条件に応じた並び替え）
#         # ソート優先順位を定義
#         sort_priority = {self.front: 0, int(self.left): 1, int(self.right): 2}  # αの優先順位を定義
        
#         # αを優先順位にマッピングする新しい列を追加
#         alpha_priority = np.array([sort_priority[alpha] for alpha in tom_pos_matrix[:, 3]])
#         tom_pos_matrix = np.hstack((tom_pos_matrix, alpha_priority.reshape(-1, 1)))

#         # Step 3: 各αの条件でのソート処理
#         # 最終的な並び替え順（優先度：y軸 -> α -> x軸の条件）
#         def custom_sort_key(row):
#             y = row[1]  # y軸（奥行き）
#             alpha_priority = row[4]  # α優先順位（第5要素）
#             x = row[0]  # x軸
#             alpha = row[3]  # α
            
#             # αが右方向の角度の場合のみx軸で降順、それ以外は昇順
#             if alpha == self.right:
#                 x = -x  # xをマイナスでソート基準化（降順にするため）
            
#             return (y, alpha_priority, x)
        
#         # ソート結果から元のインデックス情報を保持
#         original_indices = np.arange(len(tom_pos_matrix)).reshape(-1, 1)
#         tom_pos_matrix = np.hstack((tom_pos_matrix, original_indices))
        
#         # Step 4: 並べ替え
#         tom_pos_matrix = np.array(sorted(tom_pos_matrix, key=custom_sort_key))
#         # print("Sorted tom_pos_matrix:")
#         # print(tom_pos_matrix)
        
#         # Step 5: harvest_order を更新
#         order = 1
#         for row in tom_pos_matrix:
#             original_index = int(row[5])  # ID列を使用して元の配列の順序を参照
#             tomato_entry = tomato_dict[original_index]
#             if tomato_entry["is_ripe"]:  # "is_ripe" が True の場合のみ処理
#                 tomato_entry["harvest_order"] = order
#                 order += 1
        
#         # Step 6: 余分なα優先順位列とID列を削除
#         tom_pos_matrix = tom_pos_matrix[:, :4]
        
#         return tom_pos_matrix, tomato_dict

#     def calculate_distance(self,matrix1, matrix2):
#         x1, y1 = matrix1[0],matrix1[1]
#         x2, y2 = matrix2[0],matrix2[1]
#         distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
#         if distance < self.threshold_distanse:
#             return True
#         else :
#             return False


#python tools
import cv2 
import numpy as np
import yaml
from shapely.geometry import Point, Polygon

"""
2024/11/21 時点

@author yoshinaga
----------------------
機能一覧
[1] 収穫順番決定
[2] 収穫可能トマト判定 
[3] トマトへのアプローチ方向(入射角)決定 
"""

# 座標変換ツール
class Transform():
    def __init__(self):
        # YAMLファイルの読み込み
        yaml_path='/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        params = self.load_yaml(yaml_path)
        coordi_trans_params = params["coordinate_transform_params"]
        
        # カメラからEE中心の距離…ロボット座標系（トマトに向かう方向がY）
        X_DIFF_CAM2EE = coordi_trans_params['X_DIFF_CAM2EE']
        Y_DIFF_CAM2EE = coordi_trans_params['Y_DIFF_CAM2EE']
        Z_DIFF_CAM2EE = coordi_trans_params['Z_DIFF_CAM2EE']
        # カメラの傾きを下向きから補正するための回転行列
        CAM_ANGLE = coordi_trans_params['CAM_ANGLE']
        CAM_THETA = np.deg2rad(CAM_ANGLE)  # 度→ラジアン
        self.COS_THETA = np.cos(CAM_THETA)
        self.SIN_THETA = np.sin(CAM_THETA)
        # X軸の補正回転行列（35度上向きに補正）
        self.ROTATION_MATRIX = np.array([
            [1, 0, 0],
            [0, self.COS_THETA, self.SIN_THETA],
            [0, -self.SIN_THETA,  self.COS_THETA]
        ])
        # カメラからEEへの平行移動ベクトル
        self.TRANSLATION_VECTOR_CAM2EE = np.array([X_DIFF_CAM2EE, Y_DIFF_CAM2EE, Z_DIFF_CAM2EE])
        
        # EE中心からアーム付け根までの距離 ※アームがホームポジションのときの距離
        X_DIFF_EE2ARM = coordi_trans_params['X_DIFF_EE2ARM']
        Y_DIFF_EE2ARM = coordi_trans_params['Y_DIFF_EE2ARM']
        Z_DIFF_EE2ARM = coordi_trans_params['Z_DIFF_EE2ARM']
        # EEからアームへの平行移動ベクトル
        self.TRANSLATION_VECTOR_EE2ARM = np.array([X_DIFF_EE2ARM, Y_DIFF_EE2ARM, Z_DIFF_EE2ARM])
    
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

    def pixel_to_mm(self, tom_h_pix, center_d):
        TAN_GAMMA = np.tan(np.deg2rad(29)) # 29°：RealSense D405 の縦の画角
        tom_h_mm = (tom_h_pix/240) * center_d* TAN_GAMMA
        return tom_h_mm
    
    def transformation(self, cam_coordies, tom_heights_pixel, tomato_3d_posies):
        tom_heights_mm = []
        arm_coordies = np.empty((0,4))
        ee_coordies = np.empty((0,3))
        
        for tom_h_pix, pos in zip(tom_heights_pixel, tomato_3d_posies):
            tom_h_mm = self.pixel_to_mm(tom_h_pix, pos[2]) # pos[2]:中心座標のデプス値
            tom_heights_mm.append(tom_h_mm)
            
        for cam_pos, tom_h in zip(cam_coordies, tom_heights_mm) :
            # カメラ座標→EE座標
            ee_coordi = self.camera_to_ee(cam_pos, tom_h)
            ee_coordies = np.vstack((ee_coordies, ee_coordi))
            
            # EE座標→アーム座標
            arm_coordi = self.ee_to_arm(ee_coordi)
            arm_coordi = np.append(arm_coordi, cam_pos[3]) # cam_pos[3]: アプローチ角度
            arm_coordies = np.vstack((arm_coordies, arm_coordi))
        return arm_coordies, ee_coordies
    
    def camera_to_ee(self, cam_pos, tom_h):
        X, Y, Z = cam_pos[0],cam_pos[2],-cam_pos[1] # 座標軸の変換
        ee_coordi = np.array([X, Y, Z])
        # 回転行列を適応して回転
        cam_coordi_rotat = self.ROTATION_MATRIX @ ee_coordi
        
        # 平行移動ベクトルを適用してEE座標に変換
        ee_coordi = cam_coordi_rotat + self.TRANSLATION_VECTOR_CAM2EE
        ee_coordi[1] = ee_coordi[1] - (tom_h/2)* (1 - self.COS_THETA)
        ee_coordi[2] = ee_coordi[2] - (tom_h/2)* self.SIN_THETA
        return ee_coordi
    
    def ee_to_arm(self, ee_coordi):        
        # 平行移動ベクトルを適用してARM座標に変換
        arm_coordi = ee_coordi + self.TRANSLATION_VECTOR_EE2ARM
        return arm_coordi

class Harvest_Order():  
    def __init__(self, params):
        #param
        self.transform_tools = Transform()
        self.threshold_distanse = 60
        APRCH_ANG = params["APPROACH_ANG"]
        self.left = int(APRCH_ANG)
        self.right = int(180 - int(APRCH_ANG))
        self.front = 90

        #収穫可能エリア
        harvestable_area = {
            "bottom": [(0,180), (0,380), (350,380), (350,780), (-250,780), (-250,180)], 
            "hight": [(50, 600)]
            }
        self.harvestable_bottom = Polygon(harvestable_area["bottom"])
        self.harvestable_hight = harvestable_area["hight"]

    def set_approach_angle(self, tomato_posi): 
        for tom_posi in tomato_posi:
            # print(f"tom_posi[3]: {tom_posi[3]}")
            match tom_posi[3]:
                case -1:
                    approach_ang = self.left
                case 0:
                    approach_ang = self.front
                case 1:
                    approach_ang = self.right
            
            tom_posi[3] = approach_ang
        return tomato_posi
    
    def obj_area_chech(self,bbox,seg_img):
        area_chech = [0,0,0]
        x_min = int(bbox[0])
        x_max = int(bbox[1])
        w = int(x_max - x_min)
        y_min = int(bbox[2])
        y_max = int(bbox[3])
        if not np.any(seg_img[x_min:x_min+int(w/3),y_min:y_max] > 0) :
            area_chech[0] == 1
        if not np.any(seg_img[x_min+int(w/3):x_min+2*int(w/3),y_min:y_max] > 0) :
            area_chech[1] == 1
        if not np.any(seg_img[x_min+2*int(w/3):x_max,y_min:y_max] > 0) :
            area_chech[2] == 1
        return area_chech
    
    def order_decision(self, tomato_3d_posies, tom_heights_pixel, tomato_dict):
        # index 4まで格納できるように初期化 (x, y, z, ang, original_index)
        target_poses = np.empty((0, 5)) 
        
        # NOTE: tomato_3d_posies は熟したトマトのみの座標配列
        # tomato_dict は全トマトの辞書。両者の対応を取るためにカウンタを使用
        ripe_idx = 0 
        
        if tomato_3d_posies is not None :
            # カメラ座標＋EE進入角度
            tom_pos_direction = self.set_approach_angle(tomato_3d_posies)
            # print(f'tom_pos_direction: \n{tom_pos_direction}')
            
            # 座標変換
            arm_coordinates, ee_coordinates = self.transform_tools.transformation(tom_pos_direction, tom_heights_pixel, tomato_3d_posies)
            # print(f"arm_coordinates, ee_coordinates: \n{arm_coordinates, ee_coordinates}")

            # tomato_dictをループし、熟しているものに対して座標を紐づけ
            for i, tomato in enumerate(tomato_dict):
                if tomato["is_ripe"]:
                    # アーム座標を辞書に保存
                    tomato["arm_coords"] = [arm_coordinates[ripe_idx][0], arm_coordinates[ripe_idx][1], arm_coordinates[ripe_idx][2]]
                    
                    # ソート用配列を作成: [x, y, z, ang, original_index]
                    # z には ee_coordinates の高さ情報を使用
                    target_pos = [
                        arm_coordinates[ripe_idx][0], # x
                        arm_coordinates[ripe_idx][1], # y
                        ee_coordinates[ripe_idx][2],  # z (高さ)
                        arm_coordinates[ripe_idx][3], # ang
                        i                             # original_index (tomato_dictのインデックス)
                    ]
                    
                    target_poses = np.vstack((target_poses, target_pos))
                    ripe_idx += 1 # 熟したトマトのカウンタを進める

            # print(f'arm_coordinates(アーム座標一覧): \n{target_poses}')
            
            # 収穫順番決定
            target_poses, tomato_dict = self.sorting(target_poses, tomato_dict)
            print(f'target_poses sorted(並び替え後): \n{target_poses}')
            
            return target_poses, tomato_dict
        else :
            return target_poses, tomato_dict
        
    def sorting(self, tom_pos_matrix, tomato_dict):
        # Step 1: αの優先順位付け
        sort_priority = {self.front: 0, int(self.left): 1, int(self.right): 2}
        
        # α(3列目)に対応する優先度配列を作成
        alpha_priority = np.array([sort_priority.get(alpha, 99) for alpha in tom_pos_matrix[:, 3]])
        
        # 行列に結合: [x, y, z, ang, original_index] + [alpha_priority]
        # col index: 0, 1, 2, 3,   4,                 5
        tom_pos_matrix = np.hstack((tom_pos_matrix, alpha_priority.reshape(-1, 1)))

        # Step 2: ソートキーの定義 (ここが重要)
        def custom_sort_key(row):
            z = row[2]           # 高さ (Z軸) -> 最優先 (下から順 = 昇順)
            y = row[1]           # 奥行き (Y軸) -> 次点 (手前優先)
            alpha_priority = row[5]  # α優先順位
            x = row[0]           # X軸
            alpha = row[3]       # α(角度)
            
            # αが右方向の角度の場合のみx軸で降順 (右にあるものを右から取るため)
            if alpha == self.right:
                x = -x 
            
            return (z, y, alpha_priority, x)
        
        # Step 3: 並べ替え実行
        tom_pos_matrix = np.array(sorted(tom_pos_matrix, key=custom_sort_key))
        
        # Step 4: harvest_order を更新 (tomato_dictへの書き込み)
        order = 1
        for row in tom_pos_matrix:
            original_index = int(row[4])  # 保持しておいた元のインデックス(col 4)を使用
            
            # 安全策: インデックスが範囲外でないか確認
            if original_index < len(tomato_dict):
                tomato_entry = tomato_dict[original_index]
                if tomato_entry.get("is_ripe", False):
                    tomato_entry["harvest_order"] = order
                    order += 1
        
        # Step 5: 余分な列(original_index, alpha_priority)を削除して元の形(x,y,z,ang)に戻す
        # 返却するのは x, y, z, ang の4要素
        # ※ Zの値は arm_coords ではなく ee_coords 由来になっている点に注意（受信側でどう扱うかによる）
        final_poses = tom_pos_matrix[:, :4]
        
        return final_poses, tomato_dict

    def calculate_distance(self,matrix1, matrix2):
        x1, y1 = matrix1[0],matrix1[1]
        x2, y2 = matrix2[0],matrix2[1]
        distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if distance < self.threshold_distanse:
            return True
        else :
            return False