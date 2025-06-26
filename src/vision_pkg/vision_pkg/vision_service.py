#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime
import yaml

# ros2_library
import rclpy
from rclpy.node import Node
from toms_msg.msg import TomatoPos,TomatoData
from toms_msg.srv import VisionService

# python library
import cv2
import numpy as np
import json
import csv
import copy

from ultralytics import YOLO

sys.path.append('/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/modules')
from .modules.realsense_module import Realsense_Module
from .modules.ripeness_judge import Ripeness_Judge
from .modules.filter_tools import Filter_SSR, Filter_MSR, Filter_MSRCR
from .modules.harvest_order import Harvest_Order
from .modules.predict_extraction import Predict_Extra
from .modules.appro_angle_determiner import Approach_Angle_Determiner


"""
@author yoshida keisuke, 吉永
-----------------------------------------
vision service node
画像処理司令を受け取って,要求された情報を返すノード

2025/1/20時点
TODO: Retinexフィルターの種類選択とパラメータ設定処理
TODO: yolo_toolsの実装 →YOLOの設定ファイル。動作開始直後の初回の認識時間を短縮できる。
TODO: 2段階収穫動作の処理実装
"""

class Vision_Service(Node):  
    def __init__(self):
        super().__init__('vision_service') 

        #service
        self.vision_host_server = self.create_service(VisionService,"vision_service", self.vision_host_server)
        
        # パラメータ設定用のyamlファイル
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        # YAMLファイルの読み込み

        # print文を無効化（ログの出力はされる）
        params = self.load_yaml(yaml_path)
        DEBUG = params["DEBUG"]
        if DEBUG:
            sys.stdout = open(os.devnull, 'w')
        else:
            sys.stdout = sys.__stdout__

        vision_params = params["vision_params"]
        camera_params = vision_params["camera_params"]
        
        self.SHOW_RESULT_FLAG = vision_params["SHOW_RESULT"]
        self.FILITER_TYPE = vision_params["FILITER_TYPE"]
        
        # 推論パラメータ
        WEIGHT_PATH = vision_params["WEIGHT_PATH"]     # 最終的に仕様する重みのパスを入力
        self.CONF_BASE_TH = vision_params["CONF_BASE_TH"]
        self.IOU_TH = vision_params["IOU_TH"]
        self.MIN_AREA_TH = vision_params["MIN_AREA_TH"]

        # データの保存先
        IMG_SAVE_DIR_PATH = vision_params["IMG_SAVE_DIR_PATH"]
        self.IMG_SAVE_DIL = self.create_output_directory(IMG_SAVE_DIR_PATH)
        RESULT_SAVE_DIR_PATH = vision_params["PROC_RESULT_SAVE_DIR_PATH"]
        self.RESULT_SAVE_DIL = self.create_output_directory(RESULT_SAVE_DIR_PATH)

        # 処理時のパラメータ
        self.APPROACH_ANG = vision_params["APPROACH_ANG"]

        #library
        self.realsense = Realsense_Module(camera_params)
        self.harvest_order = Harvest_Order(vision_params)
        self.ripeness_judge = Ripeness_Judge(vision_params)
        self.predict_extra = Predict_Extra(vision_params)
        self.angle_determiner = Approach_Angle_Determiner(camera_params)
        self.get_logger().info('ビジョンサーバ起動')
    
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
    
    @staticmethod
    def convert_to_serializable(obj):
        if obj is None:  # None をそのまま返す
            return None
        if isinstance(obj, np.ndarray):
            return obj.tolist()  # NumPy配列をリストに変換
        if isinstance(obj, (np.float32, np.float64)): 
            return float(obj)  # NumPyのfloatをPythonのfloatに変換
        if isinstance(obj, (np.int32, np.int64)): 
            return int(obj)  # NumPyのintをPythonのintに変換
        raise TypeError(f"Type {type(obj)} not serializable")

    
    def create_output_directory(self, IMG_SAVE_DIR_PATH):
        # 実行時の日付でディレクトリ名を作成
        date_str = datetime.now().strftime("%Y_%m_%d")
        directory_path = os.path.join(IMG_SAVE_DIR_PATH, date_str)

        # ディレクトリが存在しなければ作成
        os.makedirs(directory_path, exist_ok=True)
        return directory_path
    
    def save_image(self, image, prefix="image"):
        # 実行時の時間でファイル名を生成
        self.time_str = datetime.now().strftime("%H-%M-%S")
        file_name = f"{self.time_str}_{prefix}.jpg"
        file_path = os.path.join(self.IMG_SAVE_DIL, file_name)

        # OpenCVを使用して画像を保存
        cv2.imwrite(file_path, image)
        return file_path
    

    def save_result_data(self, data):
        # 実行時の時間でファイル名を生成
        file_name = f"{self.time_str}_result.csv"
        file_path = os.path.join(self.RESULT_SAVE_DIL, file_name)
        # データをフラット化
        flat_data = [self.flatten_json(item) for item in data]
        empty_data =[]
        
        # CSVのヘッダー（最初の行）としてキーを取得
        if len(data) == 0:
            keys = ["id","conf","image_coords","ripeness","is_ripe","approach_ang","camera_coords","arm_coords","harvest_order"]  # 空のデータに対応するデフォルトのキー
            empty_data = []
        else:
            keys = flat_data[0].keys()
            empty_data = data
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()  # ヘッダーを記録
            if len(empty_data) > 0:
                writer.writerows(empty_data)  # 空でない場合はデータを記録
            # print(f"データをCSVとして保存しました: {file_path}")
        return file_path
    
    def flatten_json(self, nested_json):
        """ネストされたJSONを平坦化"""
        flat_dict = {}
        
        def flatten(item, name=''):
            if type(item) is dict:
                for key in item:
                    flatten(item[key], name + key + '_')
            else:
                flat_dict[name[:-1]] = item
            
        flatten(nested_json)
        return flat_dict

    def detect_check(self, F_or_B):
        self.realsense.setup("814412070380") # D435(俯瞰カメラ)
        
        self.get_logger().info("detect_check")
        check = None
        harvestable_tom_pos = []
        tom_3d_pos = []
        # 俯瞰カメラによる撮影で画像を取得する
        color_img,depth_img,depth_frame = self.realsense.get_image(self.SHOW_RESULT_FLAG)

        if color_img is not None :
            harvestable_tom_pos = self.predict_extra.check_predict(F_or_B, color_img, conf= self.CONF_BASE_TH, iou= self.IOU_TH)
            if harvestable_tom_pos is not None and len(harvestable_tom_pos) != 0:
                print("トマトがロボットの前付近に存在します")
                mode = 0 # detect_check
                empty_dict = []
                tom_3d_pos, _ = self.realsense.imgpoint_to_3dpoint(depth_frame, harvestable_tom_pos, mode, empty_dict)
                check = True
            else:
                print("トマトは無いようです。。。")
                check = False
        print(f"tom_3d_pos: {tom_3d_pos}")
        if tom_3d_pos is not None:
            tom_pos_msg = self.create_tomatopos_msg(tom_3d_pos)
        return tom_pos_msg, check

    def select_filter(self):
        match self.FILITER_TYPE:
            case "ssr":
                print("Filter type is SSR")
                filter = Filter_SSR()
                param = [] # 任意のパラメータを設定
            case "msr":
                print("Filter type is MSR")
                filter = Filter_MSR()
                param = [] # 任意のパラメータを設定
            case "msrcr":
                print("Filter type is MSRCR")
                filter = Filter_MSRCR()
                param = [] # 任意のパラメータを設定
        
        return filter, param
    
    def remove_small_mask_and_get_tom_height(self, results):
        removed_result_tomato = []
        mask_heights = []
        
        for r in results:
            masks = r.masks.data.cpu().numpy() if r.masks is not None else None
            if masks is None:
                continue
            
            for ci, mask in enumerate(masks):
                label = r.names[r.boxes.cls.tolist()[ci]]  # トマトのラベルを取得
                scores = r.boxes.conf.cpu().numpy()[ci]  # 各スコアを取得

                if label == "tomato" and scores > self.predict_extra.CONF_TOM:
                    # 各マスクの面積を計算
                    mask_area = np.sum(mask != 0)  # 255以外のピクセルがトマト領域を示す
                    if mask_area < self.MIN_AREA_TH:  # 面積がしきい値以下なら無視
                        continue
                    
                    # マスクの高さを計算
                    mask_indices = np.where(mask != 0)
                    height = int(np.max(mask_indices[0]) - np.min(mask_indices[0]))  # 高さの計算

                    # 高さをリストに追加
                    mask_heights.append(height)
                    removed_result_tomato.append(r)  # しきい値を超えるトマトの結果を追加
        
        return removed_result_tomato, mask_heights
    
    def draw_ripe_tomato_angle(self, image, tomato_dict):
        for tomato in tomato_dict:
            # トマトが熟している場合（is_ripeがTrue）のみ処理を実行
            if tomato.get('is_ripe', False):
                # 画像内座標
                coord = tomato['image_coords']
                x = coord[0]
                y = coord[1]

                # approach_ang に応じた L/F/R を決定
                approach_ang = tomato['approach_ang']
                if approach_ang == -1:
                    direction = "L"
                    text_position = (x - 50, y)  # トマト中心より左に描画
                elif approach_ang == 0:
                    direction = "F"
                    text_position = (x - 25, y + 25)  # トマト中心より下に描画
                elif approach_ang == 1:
                    direction = "R"
                    text_position = (x + 25, y)  # トマト中心より右に描画
                else:
                    direction = "?"  # 万が一、-1/0/1以外の値があった場合
                    text_position = (x, y)  # デフォルトは中心に描画

                # harvest_order を取得
                harvest_order = tomato.get('harvest_order', "?")

                # 描画する文字列を生成（例: L-1, F-2, R-3）
                text = f"{direction}"

                # 文字の色と太さなどを設定
                font = cv2.FONT_HERSHEY_SIMPLEX
                color = (0, 0, 0)  # 黒色
                thickness = 2
                font_scale = 0.7

                # 文字を画像に描画
                cv2.putText(image, text, text_position, font, font_scale, color, thickness, cv2.LINE_AA)
        return image


    def main_process(self, F_B):
        self.get_logger().info("main_process")
        
        mode = 1
        tomato_pos_msg = TomatoPos()
        tomato_dict = []

        # 画像取得
        self.realsense.setup("230322272057") # 手先カメラ
        color_img,depth_img,depth_frame = self.realsense.get_image(self.SHOW_RESULT_FLAG)
        self.save_image(color_img, "orig_img")

        if color_img is not None :
            # Rerinexフィルタ処理
            # TODO: Retinexフィルターのパラメータ設定
            if self.FILITER_TYPE == "non_filter":
                self.get_logger().info('Retinexフィルタ: OFF')
                filtered_img = color_img
            else:
                filter, param = self.select_filter()
                filtered_img = filter.retinex_filter(color_img, param)
            self.save_image(filtered_img, "filtered_img")
            
            # 推論実行
            self.get_logger().info('推論実行')
            yolo_results = self.predict_extra.run_predict(filtered_img, conf= self.CONF_BASE_TH, iou= self.IOU_TH)
            
            if yolo_results is not None:
                results_tomato, tom_heights_by_pixel = self.remove_small_mask_and_get_tom_height(yolo_results) # 奥にあるトマトを認識した場合、マスク面積のしきい値処理で除外
                proc_times, color_mask, mask_main_stem, mask_peduncle, mask_tomato = self.predict_extra.extraction_and_color_mask(results_tomato)
                overlay_img = self.predict_extra.overlay_images(filtered_img, color_mask)
                self.save_image(overlay_img, "overlay_img")
                self.save_image(color_mask, "color_mask")
                
                if self.SHOW_RESULT_FLAG:
                    cv2.imshow('overlay_image', overlay_img)
                    cv2.waitKey(500)
                    cv2.destroyAllWindows()
                
                # 熟度判定
                self.get_logger().info('熟度判定')
                centers_of_ripe, centers_of_unripe, ripenesses, resuls_ripe_tom, tomato_dict = self.ripeness_judge.judge_ripeness(filtered_img, yolo_results, self.predict_extra.CONF_TOM, self.MIN_AREA_TH, tomato_dict)
                
                debug_tomato_dict = copy.deepcopy(tomato_dict)
                print(f"熟度判定後: {json.dumps(debug_tomato_dict, indent=4, default=self.convert_to_serializable)}")
                # print(f"熟度判定後: {tomato_dict}")
                
                self.get_logger().info(f"認識したトマトの熟度: \n{ripenesses}")
                if len(centers_of_ripe) == 0:
                    self.get_logger().info(f"熟したトマトはありませんでした")
                    return tomato_pos_msg
                self.get_logger().info(f"  → 結果(熟したトマトの中心座標): \n{centers_of_ripe}")
                
                # 手先進入角度算出処理
                print('\n手先進入角度決定処理')
                tom_pos_with_approach_angle, tomato_dict = self.angle_determiner.determine_angle(resuls_ripe_tom, mask_main_stem, mask_peduncle, mask_tomato, centers_of_ripe, tomato_dict)
                print(f"  → 結果（[トマト中心座標] + [進入角度]）: \n{tom_pos_with_approach_angle}")
                # print(f"角度決定後: {tomato_dict}")
                # print(f"角度決定後: {json.dumps(tomato_dict, indent=4, default=self.convert_to_serializable)}")
                
                # トマトの座標を画像座標系からカメラ座標系に変換
                print('\n座標変換（画像系 → カメラ系）処理')
                tomato_3d_posi, tomato_dict = self.realsense.imgpoint_to_3dpoint(depth_frame, tom_pos_with_approach_angle, mode, tomato_dict)
                print(f"  → 結果: \n{tomato_3d_posi}")
                
                # print(f"座標変換後: \n{json.dumps(tomato_dict, indent=4, default=self.convert_to_serializable)}")

                # アーム座標に変換された、[トマトの3次元座標，手先進入角度]×熟したトマトの個数 の配列が返ってくる
                print('\n座標変換（カメラ系 → アーム系）処理')
                target_coordinates, tomato_dict = self.harvest_order.order_decision(tomato_3d_posi, tom_heights_by_pixel, tomato_dict)
                print(f"  → 結果: \n{target_coordinates}")
                
                result_image = self.draw_ripe_tomato_angle(overlay_img, tomato_dict)
                self.save_image(result_image, "result_image")

                # 各処理の結果のリストを保存
                self.save_result_data(tomato_dict)
                
                debug_tomato_dict = copy.deepcopy(tomato_dict)
                print(f"最終結果: {json.dumps(debug_tomato_dict, indent=4, default=self.convert_to_serializable)}")

                # メッセージ型に変換
                tomato_pos_msg = self.create_tomatopos_msg(target_coordinates)
                #tomato_pos_msg = target_coordinates # デバッグ用
                
                return tomato_pos_msg
            else :
                return tomato_pos_msg

    def create_tomatopos_msg(self,target_coordinates):
        tomato_pos_msg = TomatoPos()
        for target_coordinate in target_coordinates:
            tomato_data = TomatoData()
            tomato_data.x = int(target_coordinate[0])
            tomato_data.y = int(target_coordinate[1])
            tomato_data.z = int(target_coordinate[2])
            tomato_data.approach_direction = int(target_coordinate[3])
            tomato_pos_msg.tomato_data.append(tomato_data)
        return tomato_pos_msg

    def vision_host_server(self, request, response):
        if request.task == "detect_check" :
            if request.direction == "f":
                forward_or_back = "f"
            elif request.direction == "b":
                forward_or_back = "b"
            
            # ロボット正面付近にトマトがあるかcheck
            self.get_logger().info('ロボット正面付近にトマトがあるかcheck')
            tom_pos, check_tomato = self.detect_check(forward_or_back)
            self.get_logger().info(f'check_tomato: {check_tomato}')
            print(f"tomato : {tom_pos}")
            if check_tomato == True:
                self.get_logger().info('トマト発見！！！')
                response.detect_check = True
                response.target_pos = tom_pos
            elif check_tomato == False:
                self.get_logger().info('トマトは無いみたい・・・。')
                response.detect_check = False
            else:
                self.get_logger().info('認識器の問題でトマトを認識できませんでした')
                response.detect_check = False
        
        else :
            forward_or_back = str(request.direction)
            target_coordinates = self.main_process(forward_or_back)
            self.get_logger().info(f'target_coordinates: {target_coordinates}')
            response.target_pos = target_coordinates
            response.detect_check = True
        
        return response

def main():
    rclpy.init() 
    node=Vision_Service() 
    try :
        rclpy.spin(node)       
    except KeyboardInterrupt :
        print("\nCtrl+C has been typed")
    finally:
        sys.stdout = sys.__stdout__
        node.destroy_node()


if __name__ == "__main__":
    main()
