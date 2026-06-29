import numpy as np
import os
import sys
import time
import cv2

from ultralytics import YOLO
from modules.realsense_module import Realsense_Module
from modules.harvest_order import Harvest_Order
from modules.predict_extraction import Predict_Extra

# sys.path.append(os.path.join(os.path.dirname(__file__), '../../arm_controller_pkg/arm_controller_pkg/modules'))
# from ik_solver_ver4 import InverseKinematicsSolver
# from motor_controller_module import MotorController
# from z_axis_controller_module import ZAxis

def get_centers_from_masks(yolo_results):
    centers = []
    mask_heights = []
    min_area_threshold = 100
    
    for r in yolo_results:
        # マスクデータを取得
        masks = r.masks.data.cpu().numpy() if r.masks is not None else None
        if masks is None:
            continue
        
        for ci, mask in enumerate(masks):
            label = r.names[r.boxes.cls.tolist()[ci]]  # トマトのラベルを取得
            if label == "tomato":
                # マスクの面積を計算
                mask_area = np.sum(mask != 0)  # 255以外のピクセルがトマト領域を示す
                if mask_area < min_area_threshold:  # 面積がしきい値以下なら無視
                    continue

                mask = (mask * 255).astype(np.uint8)  # マスクを二値化

                # マスクの重心を計算
                mask_indices = np.where(mask != 0)
                center_y = int(np.mean(mask_indices[0]))
                center_x = int(np.mean(mask_indices[1]))
                height = int(np.max(mask_indices[0]) - np.min(mask_indices[0]))  # 高さの計算

                center = [center_x, center_y]  # 高さも含めて返す
                centers.append(center)
                mask_heights.append(height)

    return centers, mask_heights

def remove_small_mask_and_get_tom_height(results):
    removed_result_tomato = []
    mask_heights = []
    min_area_threshold = 100
    
    for r in results:
        masks = r.masks.data.cpu().numpy() if r.masks is not None else None
        if masks is None:
            continue
        
        for ci, mask in enumerate(masks):
            label = r.names[r.boxes.cls.tolist()[ci]]  # トマトのラベルを取得
            scores = r.boxes.conf.cpu().numpy()[ci]  # 各スコアを取得

            if label == "tomato" and scores > 0.3:
                # 各マスクの面積を計算
                mask_area = np.sum(mask != 0)  # 255以外のピクセルがトマト領域を示す
                if mask_area < min_area_threshold:  # 面積がしきい値以下なら無視
                    continue
                
                # マスクの高さを計算
                mask_indices = np.where(mask != 0)
                height = int(np.max(mask_indices[0]) - np.min(mask_indices[0]))  # 高さの計算

                # 高さをリストに追加
                mask_heights.append(height)
                removed_result_tomato.append(r)  # しきい値を超えるトマトの結果を追加
    
    return removed_result_tomato, mask_heights

def main():
    # Transformのインスタンス作成
    realsense = Realsense_Module()
    harvest_order = Harvest_Order()
    predict_extra = Predict_Extra(
    weight='/home/toms/hibikino_toms_ws/module/weights/best.pt',
    thres_conf_stem=0.6,
    thres_conf_ped=0.1,
    thres_conf_tom=0.3
    )
    
    img,depth_img,depth_frame = realsense.get_image()
    # print(type(img))
    cv2.imshow('', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    conf=0.1
    boxes=False
    iou=0.3
    # 推論実行
    yolo_results = predict_extra.run_predict(img, conf=conf, boxes=boxes, iou=iou)
    # print(f'yolo_results の中身：{yolo_results}')
    
    # 推論結果のうち、各クラス別に結果の情報を分割
    result_tomato    = [r for r in yolo_results if any(r.names[int(label)] == "tomato" for label in r.boxes.cls.cpu().numpy())]
    result_main_stem = [r for r in yolo_results if any(r.names[int(label)] == "main_stem" for label in r.boxes.cls.cpu().numpy())]
    result_peduncle  = [r for r in yolo_results if any(r.names[int(label)] == "peduncLe" for label in r.boxes.cls.cpu().numpy())]
    
    if yolo_results is not None:
        proc_times, color_mask, mask_main_stem, mask_peduncle, mask_tomato = predict_extra.extraction_and_color_mask(yolo_results)
        # cv2.imshow('mask', mask_tomato)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        # 熟度判定
        # 手先進入角度算出処理の実装
        
        centers, tom_heights_by_pixel = get_centers_from_masks(yolo_results)
        # print(centers)
        
        removed_result_tomato, tom_heights_by_pixel = remove_small_mask_and_get_tom_height(yolo_results)
        # print(tom_heights_by_pixel)
        
        for row in centers:
            row.append(1)
        
        with_approach_angle = centers
        print(with_approach_angle)
        # 77.5
        # トマトの座標を画像座標系からカメラ座標系に変換
        tomato_3d_posies = realsense.imgpoint_to_3dpoint(depth_frame, with_approach_angle)
        print(tomato_3d_posies)
        
        """----ここまで---"""
        # アーム座標に変換された、[トマトの3次元座標，手先進入角度]×熟したトマトの個数 の配列が返ってくる
        target_coordinates = harvest_order.order_decision(removed_result_tomato, depth_img, tomato_3d_posies, tom_heights_by_pixel)
        # print(target_coordinates)
        sys.exit()
    else:
        print('tomato なし')

# メイン関数を実行
if __name__ == "__main__":
    main()
