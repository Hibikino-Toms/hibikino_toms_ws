#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from ultralytics import YOLO

# python library
import cv2
import numpy as np

from realsense_module import Realsense_Module
from ripeness_judge import Ripeness_Judge
from filter_tools import Filter_SSR, Filter_MSR, Filter_MSRCR
# from yolo_tools import Yolov8
from harvest_order import Harvest_Order
from predict_extraction_debag import Predict_Extra
# from predict_extraction import Predict_Extra
from appro_angle_determiner import Approach_Angle_Determiner


"""
@author yoshida keisuke, 吉永
-----------------------------------------
vision service node
画像処理司令を受け取って,要求された情報を返すノード

2024/10/6 時点
残り、以下の箇所（# TODOは後回し）
TODO: Retinexフィルターの種類選択とパラメータ設定処理

# TODO: yolo_toolsの実装
→YOLOの物体検出とセマンティックセグメンテーションを使用していたので、その部分をYOLOv8のインスタンセグメンテーションに変更する
# TODO: 2段階収穫動作の処理未実装
# TODO: 「進入角度」決定処理
"""

class Vision_Service():  
    def __init__(self):
        # #service
        # self.vision_host_server = self.create_service(VisionService,"vision_service", self.vision_host_server)

        self.FILITER_TYPE = "non_filter"        # Retinexフィルタの種類（初期設定：フィルターなし）
        with open('/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/modules/ripeness_th.txt', "r") as f:
            RIPENESS_TH = 100*(float(f.read().strip())) # 熟度しきい値
        WEIGHT = "/home/ylab/hibikino_toms_ws/module/weights/best.pt"     # 最終的に仕様する重みのパスを入力
        CONF_MAIN_STEM_TH = 0.6
        CONF_PED_TH = 0.1
        CONF_TOM_TH = 0.3
        self.CONF_BASE_TH = 0.1
        self.IOU_TH = 0.3
        self.MIN_AREA_TH = 1100

        #library
        self.realsense = Realsense_Module()
        self.harvest_order = Harvest_Order()
        self.ripeness_judge = Ripeness_Judge(RIPENESS_TH)
        self.predict_extra = Predict_Extra(WEIGHT, CONF_MAIN_STEM_TH, CONF_PED_TH, CONF_TOM_TH)
        self.predict_extra_de = Predict_Extra(WEIGHT, CONF_MAIN_STEM_TH, CONF_PED_TH, CONF_TOM_TH)
        self.angle_determiner = Approach_Angle_Determiner()
        # self.yolov8_setup()

        # learning model
        # self.model = YOLO(WEIGHT)
        # self.device, self.data, self.conf_thres, self.IOU_TH, self.line_thickness, self.view_img, self.hide_labels, self.hide_conf = self.yolov8_setup()

        # timer
        # timer_period = 0.01  #(s)
        # self.timer = self.create_timer(timer_period, self.timer_callback)

    # TODO: ↓推論時の引数を設定する関数→適切な内容に書き換える
    # def yolov8_setup(self):
        
    #     # device parameter
    #     self.declare_parameter('device', "")
    #     device = self.get_parameter('device').get_parameter_value().string_value

    #     # weights and data paths
    #     self.declare_parameter('weights', "") 
    #     self.declare_parameter('data', "") 
    #     weights = self.get_parameter('weights').get_parameter_value().string_value  # WEIGHT path
    #     data = self.get_parameter('data').get_parameter_value().string_value  # dataset.yaml path

    #     # Result Parameters
    #     self.declare_parameter('conf_thres', 0.3) 
    #     self.declare_parameter('iou_thres', 0.45) 
    #     conf_thres = self.get_parameter('conf_thres').get_parameter_value().double_value  # Confidence threshold
    #     iou_thres = self.get_parameter('iou_thres').get_parameter_value().double_value  # NMS IOU threshold

    #     # View Parameters
    #     self.declare_parameter('line_thickness', 3) 
    #     self.declare_parameter('view_img', False) 
    #     self.declare_parameter('hide_labels', False) 
    #     self.declare_parameter('hide_conf', False) 
    #     line_thickness = self.get_parameter('line_thickness').get_parameter_value().integer_value  # bounding box thickness (pixels)
    #     view_img = self.get_parameter('view_img').get_parameter_value().bool_value  # show results
    #     hide_labels = self.get_parameter('hide_labels').get_parameter_value().bool_value  # hide labels
    #     hide_conf = self.get_parameter('hide_conf').get_parameter_value().bool_value  # hide confidences

    #     # Initialize YOLOv8
    #     return device, data, conf_thres, iou_thres, line_thickness, view_img, hide_labels, hide_conf

    # def timer_callback(self):
    #     color_img,depth_img,depth_frame = self.realsense.get_image()
    #     if color_img is not None :
    #         # seg_img = self.segmentation.infor(color_img)

    #         # TODO: ↓「トマトが検出されている場合」に書き換える
    #         if yolo_result is not None:
    #             device, data, conf_thres, iou_thres, line_thickness, view_img, hide_labels, hide_conf = self.yolov8_setup()
    #             yolo_result = self.model.predict(color_img, conf= conf_thres, iou= iou_thres)
    #             result_pos =self.realsense.imgpoint_to_3dpoint(depth_frame,yolo_result)
    #             #self.get_logger().info(f"{result_pos}")
    #             # TODO: 収穫順番の決定処理
    #             target_coordinates = self.harvest_order.order_decision(seg_img,depth_img,result_pos)
    #             #self.get_logger().info(f"{target_coordinates}")

    def detect_check(self):
        color_img,depth_img,depth_frame = self.realsense.get_image() 
        if color_img is not None :
            yolo_result = self.predict_extra.run_predict(color_img, conf= self.CONF_BASE_TH, iou= self.IOU_TH)
            for r in yolo_result:
                for c in r:
                    label = c.names[c.boxes.cls.tolist().pop()]
                    if label == "tomato":
                        return True
            return False
        else :
            return None

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

                if label == "tomato" and scores > self.predict_extra.conf_tom:
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

    def main_process(self):
        tomato_pos_msg = []
        # 画像取得
        print('\n画像取得')
        self.realsense.setup("230322272057") # 手先カメラ
        color_img,depth_img,depth_frame = self.realsense.get_image(show=True)
        
        # デバッグ
        # color_img_path = "/home/yasukawa_lab/yoshinaga/tomato/evaluation_images/in_GoogleDrive/1_c_img_10.png"
        # depth_img_path = "/home/yasukawa_lab/yoshinaga/tomato/evaluation_images/depth_in_GoogleDrive/1_d_img_10.png"
        # color_img = cv2.imread(color_img_path)
        # depth_img = cv2.imread(depth_img_path)
        # cv2.imshow('color', color_img)
        # cv2.imshow('depth', depth_img)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        
        # depth_frame = depth_img
        
        if color_img is not None :
            # Rerinexフィルタ処理
            # TODO: Retinexフィルターのパラメータ設定
            if self.FILITER_TYPE == "non_filter":
                print('Retinexフィルタ: NO')
                filtered_img = color_img
            else:
                filter, param = self.select_filter()
                filtered_img = filter.retinex_filter(color_img, param)
            
            # 推論実行
            print('推論実行\n')
            # device, data, conf_thres, iou_thres, line_thickness, view_img, hide_labels, hide_conf = self.yolov8_setup()
            yolo_results = self.predict_extra.run_predict(filtered_img, conf= self.CONF_BASE_TH, iou= self.IOU_TH)
            
            """追加・変更した箇所"""
            if yolo_results is not None:
                results_tomato, tom_heights_by_pixel = self.remove_small_mask_and_get_tom_height(yolo_results) # 奥にあるトマトを認識した場合、マスク面積のしきい値処理で除外
                proc_times, color_mask, mask_main_stem, mask_peduncle, mask_tomato = self.predict_extra.extraction_and_color_mask(yolo_results)
                cv2.imshow('color_mask', color_mask)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
                
                # 熟度判定
                print('\n熟度判定処理')
                center_of_ripe_toms, ripenesses, resuls_ripe_tom, resuls_non_ripe_tom = self.ripeness_judge.judge_ripeness(filtered_img, yolo_results, self.predict_extra.conf_tom, self.MIN_AREA_TH)
                # print(f"熟したトマトのyolo結果: {resuls_ripe_tom}")
                print(f"認識したトマトの熟度: {ripenesses}")
                if len(center_of_ripe_toms) == 0:
                    print('熟したトマトはありませんでした。')
                    return tomato_pos_msg, None
                
                print(f"  →結果(熟したトマトの中心座標): {center_of_ripe_toms}")
                # self.plot_points_on_image(filtered_img, center_of_ripe_tomatoes)
                
                
                # 手先進入角度算出処理の実装
                print('\n手先進入角度決定処理')
                tom_pos_with_approach_angle = self.angle_determiner.determine_angle(resuls_ripe_tom, filtered_img.shape[:2], mask_peduncle, mask_tomato, center_of_ripe_toms)
                print(f"  →結果（[トマト中心座標]＋[進入角度]）: \n{tom_pos_with_approach_angle}")
                
                # トマトの座標を画像座標系からカメラ座標系に変換
                print('\n座標変換（画像系 → カメラ系）処理')
                tomato_3d_posi =self.realsense.imgpoint_to_3dpoint(depth_frame, tom_pos_with_approach_angle, mode=1)
                print(f"  →結果{tomato_3d_posi}")

                # アーム座標に変換された、[トマトの3次元座標，手先進入角度]×熟したトマトの個数 の配列が返ってくる
                print('\n座標変換（カメラ系 → アーム系）処理')
                target_coordinates = self.harvest_order.order_decision(tomato_3d_posi, tom_heights_by_pixel)
                print(f"  → 結果: \n{target_coordinates}")
                
                tomato_pos_msg = target_coordinates # デバッグ用
                
                return tomato_pos_msg
            else :
                # tomato_pos_msg = TomatoPos()
                return tomato_pos_msg, None

    # def create_tomatopos_msg(self,target_coordinates):
    #     tomato_pos_msg = TomatoPos()
    #     for target_coordinate in target_coordinates:
    #         tomato_data = TomatoData()
    #         tomato_data.x = int(target_coordinate[0])
    #         tomato_data.y = int(target_coordinate[1])
    #         tomato_data.z = int(target_coordinate[2])
    #         tomato_data.approach_direction = int(target_coordinate[3])
    #         tomato_pos_msg.tomato_data.append(tomato_data)
    #     return tomato_pos_msg

    def vision_host_server(self, request_task):
        if request_task == "detect_check" :
            check_tomato = self.detect_check()
            if check_tomato:
                response_detect_check = True
            else :
                response_detect_check = False
            response_target_pos = []
        else :
            response_detect_check = None
            target_coordinates = self.main_process()
            response_target_pos = target_coordinates
        return response_detect_check, response_target_pos
    
    def plot_points_on_image(self, image, coordinates):
        """
        指定された画像上に、座標リストに格納された位置に点をプロットする関数。
        
        Parameters:
        image (numpy.ndarray): 画像データ（OpenCV形式）。
        coordinates (list): 各プロット位置を(x, y)形式のタプルで格納したリスト。

        Returns:
        None
        """
        # 各座標に対してプロット
        for (x, y) in coordinates:
            # 座標上に赤い円を描画
            cv2.circle(image, (int(x), int(y)), radius=5, color=(0, 0, 255), thickness=-1)
        
        # 画像を表示
        cv2.imshow("Image with Points", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

def main():
    vision_node = Vision_Service()
    arm_reqs = []
    request_task = ""
    res_detect_check, res_target_pos = vision_node.vision_host_server(request_task)
        
    print(f'arm_pos: {res_target_pos}')
    print(f'arm_req : {arm_reqs}')
    # np.save("/home/toms/hibikino_toms_ws/src/tom_pos.npy", res_target_pos)
    # print('\n')
    # print(np.load("/home/toms/hibikino_toms_ws/src/tom_pos.npy"))

if __name__ == '__main__':
    main()