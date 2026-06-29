#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime
import yaml
import traceback  # ★ 追加
import time

# ros2_library
import rclpy
from rclpy.node import Node
# rclpy.qos から qos_profile_services_default をインポート
from rclpy.qos import qos_profile_services_default
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
        self.vision_host_server_object = self.create_service(
            VisionService,
            "vision_service",
            self.vision_host_server,
            # QoSプロファイルを明示的に指定
            qos_profile=qos_profile_services_default)
        
        # パラメータ設定用のyamlファイル
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        # YAMLファイルの読み込み

        try:
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

        except Exception as e:
            self.get_logger().error(f"初期化中にエラーが発生しました: {e}")
            raise e
    
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
        # ★ エラー回避: imageがNoneなら保存しない
        if image is None: return None

        # 実行時の時間でファイル名を生成
        self.time_str = datetime.now().strftime("%H-%M-%S")
        file_name = f"{self.time_str}_{prefix}.jpg"
        file_path = os.path.join(self.IMG_SAVE_DIL, file_name)

        # OpenCVを使用して画像を保存
        try:
            cv2.imwrite(file_path, image)
        except Exception as e:
            self.get_logger().warn(f"画像保存失敗: {e}")
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
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()  # ヘッダーを記録
                if len(empty_data) > 0:
                    writer.writerows(empty_data)  # 空でない場合はデータを記録
                # print(f"データをCSVとして保存しました: {file_path}")
        except Exception as e:
             self.get_logger().warn(f"CSV保存失敗: {e}")
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
        try:
            self.realsense.setup("827312071693") # D435(俯瞰カメラ)のID: realsense-viewerで確認
            
            self.get_logger().info("detect_check")
            check = None
            harvestable_tom_pos = []
            tom_3d_pos = []
            tom_pos_msg = TomatoPos() # 初期化

            # 俯瞰カメラによる撮影で画像を取得する
            color_img,depth_img,depth_frame = self.realsense.get_image(self.SHOW_RESULT_FLAG)

            if color_img is not None :
                harvestable_tom_pos = self.predict_extra.check_predict(F_or_B, color_img, conf= self.CONF_BASE_TH, iou= self.IOU_TH)
                if harvestable_tom_pos is not None and len(harvestable_tom_pos) != 0:
                    print("トマトがロボットの前付近に存在します")
                    mode = 0 # detect_check
                    empty_dict = []
                    
                    # ★ 深度フレームの確認を追加
                    if depth_frame:
                        tom_3d_pos, _ = self.realsense.imgpoint_to_3dpoint(depth_frame, harvestable_tom_pos, mode, empty_dict)
                        check = True
                    else:
                        self.get_logger().warn("深度フレームが取得できませんでした")
                        check = False
                else:
                    print("トマトは無いようです。。。")
                    check = False
            else:
                self.get_logger().warn("画像が取得できませんでした")
                check = False

            print(f"tom_3d_pos: {tom_3d_pos}")
            if tom_3d_pos is not None and len(tom_3d_pos) > 0:
                tom_pos_msg = self.create_tomatopos_msg(tom_3d_pos)
            return tom_pos_msg, check

        except Exception as e:
            self.get_logger().error(f"detect_check エラー: {e}")
            return TomatoPos(), False

    def select_filter(self):
        filter = None
        param = []
        match self.FILITER_TYPE:
            case "ssr":
                print("Filter type is SSR")
                filter = Filter_SSR()
            case "msr":
                print("Filter type is MSR")
                filter = Filter_MSR()
            case "msrcr":
                print("Filter type is MSRCR")
                filter = Filter_MSRCR()
        
        return filter, param
    
    def remove_small_mask_and_get_tom_height(self, results):
        removed_result_tomato = []
        mask_heights = []
        
        for r in results:
            if r.masks is None: continue

            masks = r.masks.data.cpu().numpy() 
            
            for ci, mask in enumerate(masks):
                # ★ 配列インデックス範囲外ガード
                if ci >= len(r.boxes.cls): continue

                label = r.names[r.boxes.cls.tolist()[ci]]  # トマトのラベルを取得
                scores = r.boxes.conf.cpu().numpy()[ci]  # 各スコアを取得

                if label == "tomato" and scores > self.predict_extra.CONF_TOM:
                    # 各マスクの面積を計算
                    mask_area = np.sum(mask != 0)  # 255以外のピクセルがトマト領域を示す
                    if mask_area < self.MIN_AREA_TH:  # 面積がしきい値以下なら無視
                        continue
                    
                    # マスクの高さを計算
                    mask_indices = np.where(mask != 0)
                    if len(mask_indices[0]) > 0: # ★ 空チェック
                        height = int(np.max(mask_indices[0]) - np.min(mask_indices[0]))  # 高さの計算
                        mask_heights.append(height)
                        removed_result_tomato.append(r)  # しきい値を超えるトマトの結果を追加
        
        return removed_result_tomato, mask_heights
    
    def draw_ripe_tomato_angle(self, image, tomato_dict):
        if image is None: return None
        h, w = image.shape[:2] # 画像サイズ取得

        for tomato in tomato_dict:
            # トマトが熟している場合（is_ripeがTrue）のみ処理を実行
            if tomato.get('is_ripe', False):
                # 画像内座標
                coord = tomato['image_coords']
                # ★ 座標を画像範囲内にクリップ (ここが重要！)
                x = max(0, min(int(coord[0]), w - 1))
                y = max(0, min(int(coord[1]), h - 1))

                # approach_ang に応じた L/F/R を決定
                approach_ang = tomato['approach_ang']
                if approach_ang == -1:
                    direction = "L"
                    text_position = (max(0, x - 50), y)  # 範囲外ガード
                elif approach_ang == 0:
                    direction = "F"
                    text_position = (max(0, x - 25), min(h-1, y + 25))
                elif approach_ang == 1:
                    direction = "R"
                    text_position = (min(w-1, x + 25), y)
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
        
        try:
            mode = 1
            tomato_pos_msg = TomatoPos()
            tomato_dict = []
            # ★ 全体の計測開始
            total_start = time.time()

            # --------------------------------------------------
            # 1. カメラ初期化
            # --------------------------------------------------
            step_start = time.time()
            self.realsense.setup("230322272057") # 手先カメラ
            self.get_logger().info(f"[TIME] 1. カメラsetup処理: {time.time() - step_start:.3f} 秒")

            # --------------------------------------------------
            # 2. 画像取得
            # --------------------------------------------------
            step_start = time.time()
            color_img,depth_img,depth_frame = self.realsense.get_image(self.SHOW_RESULT_FLAG)
            self.save_image(color_img, "orig_img")
            self.get_logger().info(f"[TIME] 2. カメラ画像取得＆保存: {time.time() - step_start:.3f} 秒")
            # # 画像取得
            # self.realsense.setup("230322272057") # 手先カメラ
            # color_img,depth_img,depth_frame = self.realsense.get_image(self.SHOW_RESULT_FLAG)
            # self.save_image(color_img, "orig_img")

            if color_img is not None :
                # --------------------------------------------------
                # 3. フィルター処理
                # --------------------------------------------------
                step_start = time.time()  
                if self.FILITER_TYPE == "non_filter":
                    self.get_logger().info('Retinexフィルタ: OFF')
                    filtered_img = color_img
                else:
                    filter, param = self.select_filter()
                    if filter:
                        filtered_img = filter.retinex_filter(color_img, param)
                    else:
                        filtered_img = color_img

                self.save_image(filtered_img, "filtered_img")
                self.get_logger().info(f"[TIME] 3. フィルター処理: {time.time() - step_start:.3f} 秒")
                
                #  --------------------------------------------------
                # 4. YOLO推論実行
                # --------------------------------------------------
                self.get_logger().info('推論実行')
                step_start = time.time()
                yolo_results = self.predict_extra.run_predict(filtered_img, conf= self.CONF_BASE_TH, iou= self.IOU_TH)
                self.get_logger().info(f"[TIME] 4. YOLO推論実行: {time.time() - step_start:.3f} 秒")

                if yolo_results is not None:
                    # --------------------------------------------------
                    # 5. マスク抽出と画像生成
                    # --------------------------------------------------
                    step_start = time.time()
                    results_tomato, tom_heights_by_pixel = self.remove_small_mask_and_get_tom_height(yolo_results) # 奥にあるトマトを認識した場合、マスク面積のしきい値処理で除外
                    proc_times, color_mask, mask_main_stem, mask_peduncle, mask_tomato = self.predict_extra.extraction_and_color_mask(results_tomato)
                    
                    if filtered_img is not None and color_mask is not None:
                        overlay_img = self.predict_extra.overlay_images(filtered_img, color_mask)
                        self.save_image(overlay_img, "overlay_img")
                        self.save_image(color_mask, "color_mask")
                        self.get_logger().info(f"[TIME] 5. マスク抽出＆画像生成: {time.time() - step_start:.3f} 秒")

                        if self.SHOW_RESULT_FLAG:
                            cv2.imshow('overlay_image', overlay_img)
                            cv2.waitKey(500)
                            cv2.destroyAllWindows()
                    else:
                        overlay_img = filtered_img # フォールバック

                    # --------------------------------------------------
                    # 6. 熟度判定
                    # -------------------------------------------------- 
                    self.get_logger().info('熟度判定')
                    step_start = time.time()
                    centers_of_ripe, centers_of_unripe, ripenesses, resuls_ripe_tom, tomato_dict = self.ripeness_judge.judge_ripeness(filtered_img, yolo_results, self.predict_extra.CONF_TOM, self.MIN_AREA_TH, tomato_dict)
                    
                    debug_tomato_dict = copy.deepcopy(tomato_dict)
                    self.get_logger().info(f"熟度判定後: {json.dumps(debug_tomato_dict, indent=4, default=self.convert_to_serializable)}")
                    # print(f"熟度判定後: {tomato_dict}")
                    
                    self.get_logger().info(f"認識したトマトの熟度: \n{ripenesses}")
                    if len(centers_of_ripe) == 0:
                        self.get_logger().info(f"熟したトマトはありませんでした")
                        return tomato_pos_msg
                    self.get_logger().info(f"  → 結果(熟したトマトの中心座標): \n{centers_of_ripe}")
                    self.get_logger().info(f"[TIME] 6. 熟度判定: {time.time() - step_start:.3f} 秒")

                    # --------------------------------------------------
                    # 7. 手先進入角度決定処理
                    # -------------------------------------------------- 
                    self.get_logger().info('\n手先進入角度決定処理')
                    step_start = time.time()
                    tom_pos_with_approach_angle, tomato_dict = self.angle_determiner.determine_angle(resuls_ripe_tom, mask_main_stem, mask_peduncle, mask_tomato, centers_of_ripe, tomato_dict)
                    self.get_logger().info(f"  → 結果（[トマト中心座標] + [進入角度]）: \n{tom_pos_with_approach_angle}")
                    # print(f"角度決定後: {tomato_dict}")
                    # print(f"角度決定後: {json.dumps(tomato_dict, indent=4, default=self.convert_to_serializable)}")
                    self.get_logger().info(f"[TIME] 7. 手先進入角度決定処理: {time.time() - step_start:.3f} 秒")

                    # トマトの座標を画像座標系からカメラ座標系に変換
                    # ★ 深度エラー対策
                    self.get_logger().info('\n座標変換（画像系 → カメラ系）処理')
                    step_start = time.time()
                    if depth_frame:
                        tomato_3d_posi, tomato_dict = self.realsense.imgpoint_to_3dpoint(depth_frame, tom_pos_with_approach_angle, mode, tomato_dict)
                        print(f"  → 結果: \n{tomato_3d_posi}")
                    else:
                        self.get_logger().error("深度フレームが無効なため、3D座標変換をスキップします")
                        return tomato_pos_msg
                    
                    # print(f"座標変換後: \n{json.dumps(tomato_dict, indent=4, default=self.convert_to_serializable)}")

                    # アーム座標に変換された、[トマトの3次元座標，手先進入角度]×熟したトマトの個数 の配列が返ってくる
                    self.get_logger().info('\n座標変換（カメラ系 → アーム系）処理')
                    target_coordinates, tomato_dict = self.harvest_order.order_decision(tomato_3d_posi, tom_heights_by_pixel, tomato_dict)
                    self.get_logger().info(f"  → 結果: \n{target_coordinates}")

                    result_image = self.draw_ripe_tomato_angle(overlay_img, tomato_dict)
                    self.save_image(result_image, "result_image")

                    # 各処理の結果のリストを保存
                    self.save_result_data(tomato_dict)
                    
                    debug_tomato_dict = copy.deepcopy(tomato_dict)
                    self.get_logger().info(f"最終結果: {json.dumps(debug_tomato_dict, indent=4, default=self.convert_to_serializable)}")
                    self.get_logger().info(f"[TIME] 8. 座標変換（画像系 → カメラ系 → アーム系）処理: {time.time() - step_start:.3f} 秒")


                    # メッセージ型に変換
                    tomato_pos_msg = self.create_tomatopos_msg(target_coordinates)
                    #tomato_pos_msg = target_coordinates # デバッグ用
                    
                    return tomato_pos_msg
                else :
                    return tomato_pos_msg
            return tomato_pos_msg
        
        except Exception as e:
            self.get_logger().error(f"main_process 実行中エラー: {e}")
            self.get_logger().error(traceback.format_exc())
            return TomatoPos()

    def create_tomatopos_msg(self,target_coordinates):
        tomato_pos_msg = TomatoPos()
        if target_coordinates is None: return tomato_pos_msg

        for target_coordinate in target_coordinates:
            if len(target_coordinate) >= 4:
                tomato_data = TomatoData()
                tomato_data.x = int(target_coordinate[0])
                tomato_data.y = int(target_coordinate[1])
                tomato_data.z = int(target_coordinate[2])
                tomato_data.approach_direction = int(target_coordinate[3])
                tomato_pos_msg.tomato_data.append(tomato_data)
        return tomato_pos_msg

    # ★★★ 修正: サービス全体を try-except で保護 ★★★
    def vision_host_server(self, request, response):
        try:
            if request.task == "detect_check" :
                if request.direction == "f":
                    forward_or_back = "f"
                elif request.direction == "b":
                    forward_or_back = "b"
                else:
                    forward_or_back = "f"
                
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
                
                # ★ 追加: リストが空でなければ True とする処理
                if len(target_coordinates.tomato_data) > 0:
                    response.detect_check = True
                else:
                    response.detect_check = False
            
            return response

        except Exception as e:
            self.get_logger().error(f"Vision Service 致命的エラー: {e}")
            self.get_logger().error(traceback.format_exc())
            # エラー時もレスポンスを返してクライアントを止めない
            response.detect_check = False
            response.target_pos = TomatoPos()
            return response

def main():
    rclpy.init() 
    node=Vision_Service() 
    try :
        rclpy.spin(node)       
    except KeyboardInterrupt :
        print("\nCtrl+C has been typed")
    except Exception as e:
        print(f"Main loop error: {e}")
    finally:
        sys.stdout = sys.__stdout__
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()