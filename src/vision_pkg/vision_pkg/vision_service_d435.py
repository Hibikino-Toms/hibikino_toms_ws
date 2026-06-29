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

from ultralytics import YOLO

sys.path.append('/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/modules')
from .modules.realsense_module import Realsense_Module
from .modules.ripeness_judge import Ripeness_Judge
from .modules.filter_tools import Filter_SSR, Filter_MSR, Filter_MSRCR
from .modules.harvest_order import Harvest_Order
from .modules.predict_extraction import Predict_Extra
from .modules.appro_angle_determiner import Approach_Angle_Determiner

from playsound import playsound


"""
@author Hikaru SATO
-----------------------------------------
vision service d435 node
画像処理司令を受け取って,要求された情報を返すノード

"""

class Vision_Service_D435(Node):  
    def __init__(self):
        super().__init__('vision_service_d435') 

        #service
        self.vision_host_server = self.create_service(VisionService,"vision_service_d435", self.vision_host_server)
        self.get_logger().info('vision_service_d435ノードを起動したのだ')
        playsound("/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/sound/ビジョンサービスディー435ノードを起動したのだ.wav")
        
        # パラメータ設定用のyamlファイル
        yaml_path = '/home/ylab/hibikino_toms_ws/module/vision_service_d435_param.yaml'
        # YAMLファイルの読み込み
        params = self.load_yaml(yaml_path)
        vision_params = params["vision_d435_param"]
        
        self.SHOW_RESULT_FLAG = vision_params["SHOW_RESULT"]
        self.FILITER_TYPE = vision_params["FILITER_TYPE"]
        RIPENESS_TH_PATH = vision_params["RIPENESS_TH_PATH"]
        with open(RIPENESS_TH_PATH, "r") as f:
            RIPENESS_TH = 100*(float(f.read().strip())) # 熟度しきい値
        
        # 推論パラメータ
        WEIGHT_PATH = vision_params["WEIGHT_PATH"]     # 最終的に仕様する重みのパスを入力
        self.CONF_BASE_TH = vision_params["CONF_BASE_TH"]
        self.IOU_TH = vision_params["IOU_TH"]
        self.MIN_AREA_TH = vision_params["MIN_AREA_TH"]
        
        # 処理に利用するための信頼度のしきい値
        CONF_MAIN_STEM_TH = vision_params["CONF_MAIN_STEM_TH"]
        CONF_PED_TH = vision_params["CONF_PED_TH"]
        CONF_TOM_TH = vision_params["CONF_TOM_TH"]
        
        # 画像の保存先
        self.IMG_SAVE_DIR_PATH = vision_params["IMG_SAVE_DIR_PATH"]
        self.SAVE_DIL = self.create_output_directory()

        #library
        self.realsense = Realsense_Module()
        self.harvest_order = Harvest_Order()
        self.ripeness_judge = Ripeness_Judge(RIPENESS_TH)
        self.predict_extra = Predict_Extra(WEIGHT_PATH, CONF_MAIN_STEM_TH, CONF_PED_TH, CONF_TOM_TH)
        self.angle_determiner = Approach_Angle_Determiner()
    
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
    
    def create_output_directory(self):
        # 実行時の日付でディレクトリ名を作成
        date_str = datetime.now().strftime("%Y_%m_%d")
        directory_path = os.path.join(self.IMG_SAVE_DIR_PATH, date_str)

        # ディレクトリが存在しなければ作成
        os.makedirs(directory_path, exist_ok=True)
        return directory_path
    
    def save_image(self, image, prefix="image"):
        # 実行時の時間でファイル名を生成
        time_str = datetime.now().strftime("%H-%M-%S")
        file_name = f"{time_str}_{prefix}.jpg"
        file_path = os.path.join(self.SAVE_DIL, file_name)

        # OpenCVを使用して画像を保存
        cv2.imwrite(file_path, image)
        return file_path

    def detect_check(self, F_or_B):
        self.realsense.setup("814412070380") # D435(俯瞰カメラ)
        self.get_logger().info("detect_check")
        check = None
        # 俯瞰カメラによる撮影で画像を取得する
        self.get_logger().info("画像を取得")
        color_img,depth_img,depth_frame = self.realsense.get_image(self.SHOW_RESULT_FLAG)
        
        if color_img is not None :
            harvestable_tom_pos = self.predict_extra.check_predict(F_or_B, color_img, conf= self.CONF_BASE_TH, iou= self.IOU_TH)
            if len(harvestable_tom_pos) != 0:
                print("トマトがロボットの前付近に存在します")
                playsound("/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/sound/トマトを見つけたのだあ.wav")
                mode = 0 # detect_check
                tom_3d_pos = self.realsense.imgpoint_to_3dpoint(depth_frame, harvestable_tom_pos, mode)
                tom_pos_msg = self.create_tomatopos_msg(tom_3d_pos)
                check = True
                print(f"tom_3d_pos: {tom_3d_pos}")
            else:
                print("トマトは無いようです。。。")
                tom_pos_msg = TomatoPos()
                check = False
        else:
            tom_pos_msg = TomatoPos()
            check = False
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
    
    def main_process(self, F_B):
        self.realsense.setup("814412070380") # D435(俯瞰カメラ)
        self.get_logger().info("main_process")
        
        mode = 1
        # 画像取得
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
                proc_times, color_mask, mask_main_stem, mask_peduncle, mask_tomato = self.predict_extra.extraction_and_color_mask(yolo_results)
                overlay_img = self.predict_extra.overlay_images(filtered_img, color_mask)
                self.save_image(overlay_img, "overlay_img")
                self.save_image(color_mask, "color_mask")
                
                if self.SHOW_RESULT_FLAG:
                    cv2.imshow('overlay_image', overlay_img)
                    cv2.waitKey(100)
                    cv2.destroyAllWindows()

                save_flag = False
                
                # 熟度判定
                self.get_logger().info('熟度判定')
                center_of_ripe_toms, ripenesses, resuls_ripe_tom, resuls_non_ripe_tom = self.ripeness_judge.judge_ripeness(filtered_img, yolo_results, self.predict_extra.CONF_TOM, self.MIN_AREA_TH)
                self.get_logger().info(f"認識したトマトの熟度: \n{ripenesses}")
                if len(center_of_ripe_toms) == 0:
                    self.get_logger().info(f"収穫できるトマトがないのだ")
                    playsound("/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/sound/収穫できるトマトがないのだあ.wav")
                    tomato_pos_msg = TomatoPos()
                    return tomato_pos_msg
                self.get_logger().info(f"熟したトマトを見つけたのだ")
                playsound("/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/sound/熟したトマトを見つけたのだあ.wav")
                self.get_logger().info(f"  → 結果(熟したトマトの中心座標): \n{center_of_ripe_toms}")
                
                # 手先進入角度算出処理の実装
                print('\n手先進入角度決定処理')
                tom_pos_with_approach_angle = self.angle_determiner.determine_angle(resuls_ripe_tom, filtered_img.shape[:2], mask_peduncle, mask_tomato, center_of_ripe_toms)
                print(f"  → 結果（[トマト中心座標] + [進入角度]）: \n{tom_pos_with_approach_angle}")
                
                # トマトの座標を画像座標系からカメラ座標系に変換
                print('\n座標変換（画像系 → カメラ系）処理')
                tomato_3d_posi = self.realsense.imgpoint_to_3dpoint(depth_frame, tom_pos_with_approach_angle, mode)
                print(f"  → 結果: \n{tomato_3d_posi}")
                
                # メッセージ型に変換
                tomato_pos_msg = self.create_tomatopos_msg(tomato_3d_posi)
                #tomato_pos_msg = target_coordinates # デバッグ用
                return tomato_pos_msg
            else :
                tomato_pos_msg = TomatoPos()
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
    node=Vision_Service_D435() 
    try :
        rclpy.spin(node)       
    except KeyboardInterrupt :
        print("Ctrl+C has been typed")  
        print("End of Program")  
    finally:
        node.destroy_node()


if __name__ == "__main__":
    main()
