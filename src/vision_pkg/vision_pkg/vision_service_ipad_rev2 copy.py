#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import time
from datetime import datetime
import yaml

# ros2_library
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_services_default, qos_profile_sensor_data
from toms_msg.msg import TomatoPos,TomatoData
from toms_msg.srv import VisionService
# --- 追加：ストリーミング用 ---
from std_srvs.srv import SetBool
from sensor_msgs.msg import CompressedImage

# python library
import cv2
import numpy as np
import json
import csv
import copy

from ultralytics import YOLO

sys.path.append('/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/modules')
from .modules.realsense_module_ipad import Realsense_Module
from .modules.ripeness_judge import Ripeness_Judge
from .modules.filter_tools import Filter_SSR, Filter_MSR, Filter_MSRCR
from .modules.harvest_order import Harvest_Order
from .modules.predict_extraction import Predict_Extra
from .modules.appro_angle_determiner import Approach_Angle_Determiner

class Vision_Service(Node):  
    def __init__(self):
        super().__init__('vision_service_ipad') # 統合ノード

        #service
        self.vision_host_server_object = self.create_service(
            VisionService,
            "vision_service",
            self.vision_host_server,
            qos_profile=qos_profile_services_default)
        
        # --- 追加：ストリーミング用パブリッシャーとサービス ---
        self.pub = self.create_publisher(CompressedImage, '/camera/image/compressed', qos_profile_sensor_data)
        self.srv_onoff = self.create_service(SetBool, 'set_streaming', self.onoff_callback)
        self.srv_select = self.create_service(SetBool, 'switch_camera', self.select_callback)

        self.is_streaming = True
        self.serial_hand = "230322272057" # 手先
        self.serial_over = "827312071693" # 俯瞰
        self.current_serial = None
        self.q = 70 # JPEG quality
        # --------------------------------------------------

        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
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
        
        WEIGHT_PATH = vision_params["WEIGHT_PATH"]
        self.CONF_BASE_TH = vision_params["CONF_BASE_TH"]
        self.IOU_TH = vision_params["IOU_TH"]
        self.MIN_AREA_TH = vision_params["MIN_AREA_TH"]

        IMG_SAVE_DIR_PATH = vision_params["IMG_SAVE_DIR_PATH"]
        self.IMG_SAVE_DIL = self.create_output_directory(IMG_SAVE_DIR_PATH)
        RESULT_SAVE_DIR_PATH = vision_params["PROC_RESULT_SAVE_DIR_PATH"]
        self.RESULT_SAVE_DIL = self.create_output_directory(RESULT_SAVE_DIR_PATH)

        self.APPROACH_ANG = vision_params["APPROACH_ANG"]

        #library
        self.realsense = Realsense_Module(camera_params)
        self.harvest_order = Harvest_Order(vision_params)
        self.ripeness_judge = Ripeness_Judge(vision_params)
        self.predict_extra = Predict_Extra(vision_params)
        self.angle_determiner = Approach_Angle_Determiner(camera_params)

        # --- 追加：初期化時にカメラを起動し、ストリーミングループ開始 ---
        self.ensure_realsense(self.serial_hand)
        self.timer = self.create_timer(1.0 / 15.0, self.streaming_loop)

        self.get_logger().info('統合ビジョンサーバ起動')
    
    # --- 追加：ストリーミングとカメラ切り替えのコールバック ---
    def onoff_callback(self, request, response):
        self.is_streaming = request.data
        response.success = True
        return response
    
    def select_callback(self, request, response):
        self.get_logger().info('カメラ切り替えリクエスト受信')
        target_serial = self.serial_hand if request.data else self.serial_over
        self.ensure_realsense(target_serial)
        response.success = True
        return response

    def streaming_loop(self):
        # 配信OFF時、またはカメラ未起動時はスキップ
        if not self.is_streaming or self.current_serial is None:
            return
        try:
            color_img, _, _ = self.realsense.get_image(False)
            if color_img is not None:
                ok, buf = cv2.imencode('.jpg', color_img, [int(cv2.IMWRITE_JPEG_QUALITY), self.q])
                if ok:
                    msg = CompressedImage()
                    msg.header.stamp = self.get_clock().now().to_msg()
                    msg.format = 'jpeg'
                    msg.data = buf.tobytes()
                    self.pub.publish(msg)
        except Exception as e:
            pass
    # ----------------------------------------------------

    @staticmethod
    def load_yaml(file_path):
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"YAMLファイルの解析エラー: {e}")
    
    @staticmethod
    def convert_to_serializable(obj):
        if obj is None:
            return None
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.float32, np.float64)): 
            return float(obj)
        if isinstance(obj, (np.int32, np.int64)): 
            return int(obj)
        raise TypeError(f"Type {type(obj)} not serializable")

    # --- 変更：現在のカメラと同じなら再起動しない ---
    def ensure_realsense(self, serial_no : str):
        if self.current_serial != serial_no:
            self.release_realsense()
            self.get_logger().info(f"カメラ(S/N: {serial_no})に切り替えます...")
            self.realsense.setup(serial_no)
            self.current_serial = serial_no
            time.sleep(1.0) # 露出安定待ち
    
    def release_realsense(self):
        if self.realsense is not None and self.current_serial is not None:
            self.realsense.stop()
            self.current_serial = None

    def create_output_directory(self, IMG_SAVE_DIR_PATH):
        date_str = datetime.now().strftime("%Y_%m_%d")
        directory_path = os.path.join(IMG_SAVE_DIR_PATH, date_str)
        os.makedirs(directory_path, exist_ok=True)
        return directory_path
    
    def save_image(self, image, prefix="image"):
        self.time_str = datetime.now().strftime("%H-%M-%S")
        file_name = f"{self.time_str}_{prefix}.jpg"
        file_path = os.path.join(self.IMG_SAVE_DIL, file_name)
        cv2.imwrite(file_path, image)
        return file_path
    
    def save_result_data(self, data):
        file_name = f"{self.time_str}_result.csv"
        file_path = os.path.join(self.RESULT_SAVE_DIL, file_name)
        flat_data = [self.flatten_json(item) for item in data]
        empty_data =[]
        if len(data) == 0:
            keys = ["id","conf","image_coords","ripeness","is_ripe","approach_ang","camera_coords","arm_coords","harvest_order"]
            empty_data = []
        else:
            keys = flat_data[0].keys()
            empty_data = data
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            if len(empty_data) > 0:
                writer.writerows(empty_data)
        return file_path
    
    def flatten_json(self, nested_json):
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
        self.ensure_realsense(self.serial_over) # 俯瞰カメラを確保
        self.get_logger().info("detect_check")
        check = None
        harvestable_tom_pos = []
        tom_3d_pos = []
        
        color_img,depth_img,depth_frame = self.realsense.get_image(self.SHOW_RESULT_FLAG)

        if color_img is not None :
            harvestable_tom_pos = self.predict_extra.check_predict(F_or_B, color_img, conf= self.CONF_BASE_TH, iou= self.IOU_TH)
            if harvestable_tom_pos is not None and len(harvestable_tom_pos) != 0:
                print("トマトがロボットの前付近に存在します")
                mode = 0
                empty_dict = []
                tom_3d_pos, _ = self.realsense.imgpoint_to_3dpoint(depth_frame, harvestable_tom_pos, mode, empty_dict)
                check = True
            else:
                print("トマトは無いようです。。。")
                check = False
        print(f"tom_3d_pos: {tom_3d_pos}")
        if tom_3d_pos is not None:
            tom_pos_msg = self.create_tomatopos_msg(tom_3d_pos)

        # 変更：release_realsense() は呼ばない！裏でストリーミングを続けるため
        return tom_pos_msg, check

    def select_filter(self):
        match self.FILITER_TYPE:
            case "ssr":
                filter = Filter_SSR()
                param = []
            case "msr":
                filter = Filter_MSR()
                param = []
            case "msrcr":
                filter = Filter_MSRCR()
                param = []
        return filter, param
    
    def remove_small_mask_and_get_tom_height(self, results):
        removed_result_tomato = []
        mask_heights = []
        for r in results:
            masks = r.masks.data.cpu().numpy() if r.masks is not None else None
            if masks is None:
                continue
            for ci, mask in enumerate(masks):
                label = r.names[r.boxes.cls.tolist()[ci]]
                scores = r.boxes.conf.cpu().numpy()[ci]
                if label == "tomato" and scores > self.predict_extra.CONF_TOM:
                    mask_area = np.sum(mask != 0)
                    if mask_area < self.MIN_AREA_TH:
                        continue
                    mask_indices = np.where(mask != 0)
                    height = int(np.max(mask_indices[0]) - np.min(mask_indices[0]))
                    mask_heights.append(height)
                    removed_result_tomato.append(r)
        return removed_result_tomato, mask_heights
    
    def draw_ripe_tomato_angle(self, image, tomato_dict):
        for tomato in tomato_dict:
            if tomato.get('is_ripe', False):
                coord = tomato['image_coords']
                x, y = coord[0], coord[1]
                approach_ang = tomato['approach_ang']
                if approach_ang == -1:
                    direction = "L"
                    text_position = (x - 50, y)
                elif approach_ang == 0:
                    direction = "F"
                    text_position = (x - 25, y + 25)
                elif approach_ang == 1:
                    direction = "R"
                    text_position = (x + 25, y)
                else:
                    direction = "?"
                    text_position = (x, y)
                
                text = f"{direction}"
                font = cv2.FONT_HERSHEY_SIMPLEX
                color = (0, 0, 0)
                thickness = 2
                font_scale = 0.7
                cv2.putText(image, text, text_position, font, font_scale, color, thickness, cv2.LINE_AA)
        return image

    def main_process(self, F_B):
        self.get_logger().info("main_process")
        mode = 1
        tomato_pos_msg = TomatoPos()
        tomato_dict = []

        self.ensure_realsense(self.serial_hand) # 手先カメラを確保
        color_img,depth_img,depth_frame = self.realsense.get_image(self.SHOW_RESULT_FLAG)
        self.save_image(color_img, "orig_img")

        if color_img is not None :
            if self.FILITER_TYPE == "non_filter":
                self.get_logger().info('Retinexフィルタ: OFF')
                filtered_img = color_img
            else:
                filter, param = self.select_filter()
                filtered_img = filter.retinex_filter(color_img, param)
            self.save_image(filtered_img, "filtered_img")
            
            self.get_logger().info('推論実行')
            yolo_results = self.predict_extra.run_predict(filtered_img, conf= self.CONF_BASE_TH, iou= self.IOU_TH)
            
            if yolo_results is not None:
                results_tomato, tom_heights_by_pixel = self.remove_small_mask_and_get_tom_height(yolo_results)
                proc_times, color_mask, mask_main_stem, mask_peduncle, mask_tomato = self.predict_extra.extraction_and_color_mask(results_tomato)
                overlay_img = self.predict_extra.overlay_images(filtered_img, color_mask)
                self.save_image(overlay_img, "overlay_img")
                self.save_image(color_mask, "color_mask")
                
                if self.SHOW_RESULT_FLAG:
                    cv2.imshow('overlay_image', overlay_img)
                    cv2.waitKey(500)
                    cv2.destroyAllWindows()
                
                self.get_logger().info('熟度判定')
                centers_of_ripe, centers_of_unripe, ripenesses, resuls_ripe_tom, tomato_dict = self.ripeness_judge.judge_ripeness(filtered_img, yolo_results, self.predict_extra.CONF_TOM, self.MIN_AREA_TH, tomato_dict)
                
                self.get_logger().info(f"認識したトマトの熟度: \n{ripenesses}")
                if len(centers_of_ripe) == 0:
                    self.get_logger().info(f"熟したトマトはありませんでした")
                    return tomato_pos_msg # release_realsenseは呼ばない
                self.get_logger().info(f"  → 結果(熟したトマトの中心座標): \n{centers_of_ripe}")
                
                print('\n手先進入角度決定処理')
                tom_pos_with_approach_angle, tomato_dict = self.angle_determiner.determine_angle(resuls_ripe_tom, mask_main_stem, mask_peduncle, mask_tomato, centers_of_ripe, tomato_dict)
                print(f"  → 結果（[トマト中心座標] + [進入角度]）: \n{tom_pos_with_approach_angle}")
                
                print('\n座標変換（画像系 → カメラ系）処理')
                tomato_3d_posi, tomato_dict = self.realsense.imgpoint_to_3dpoint(depth_frame, tom_pos_with_approach_angle, mode, tomato_dict)
                print(f"  → 結果: \n{tomato_3d_posi}")
                
                print('\n座標変換（カメラ系 → アーム系）処理')
                target_coordinates, tomato_dict = self.harvest_order.order_decision(tomato_3d_posi, tom_heights_by_pixel, tomato_dict)
                print(f"  → 結果: \n{target_coordinates}")
                
                result_image = self.draw_ripe_tomato_angle(overlay_img, tomato_dict)
                self.save_image(result_image, "result_image")

                self.save_result_data(tomato_dict)

                tomato_pos_msg = self.create_tomatopos_msg(target_coordinates)
                return tomato_pos_msg # release_realsenseは呼ばない
            else :
                return tomato_pos_msg # release_realsenseは呼ばない

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
            forward_or_back = request.direction
            self.get_logger().info('ロボット正面付近にトマトがあるかcheck')
            tom_pos, check_tomato = self.detect_check(forward_or_back)
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
    node = Vision_Service() 
    try :
        rclpy.spin(node)       
    except KeyboardInterrupt :
        print("\nCtrl+C has been typed")
    finally:
        sys.stdout = sys.__stdout__
        node.release_realsense() # 終了時にカメラを手放す
        node.destroy_node()

if __name__ == "__main__":
    main()