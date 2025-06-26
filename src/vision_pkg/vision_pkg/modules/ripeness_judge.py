import os
import cv2
import numpy as np
import copy
from ultralytics import YOLO
import yaml

"""
2024/10/8 時点

@author 藤岡、吉永

熟度判定を行うコード

クラス入力引数：熟度しきい値
[入力]
・元画像
・トマトの推論結果（yolo形式）

[出力]
・熟していると判断されたトマトの中心点座標の配列（熟したトマトの個数行ある）

"""


# 熟度判定を行うクラス
class Ripeness_Judge:
    def __init__(self, params):
        RIPENESS_TH_PATH = params["RIPENESS_TH_PATH"]
        with open(RIPENESS_TH_PATH, "r") as f:
            self.THRES = 100*(float(f.read().strip())) # 熟度しきい値
        
        self.IMG_WIDTH = params["camera_params"]["WIDTH"]
        self.IMG_HEIGHT = params["camera_params"]["HEIGHT"]

    # 赤色ピクセルの割合計算関数
    def calculate_by_pixel(self, hsv_pixel):
        h, s, v = hsv_pixel
        
        if 1 <= h <= 40:
            weight = 1 - (h - 1) * (0.95 / 39)  # 線形補間で計算
            return weight
        elif 160 <= h <= 180:
            weight = 1 - (h - 160) * (0.95 / 19)  # 160から180の範囲を線形補間
            return weight
        else:
            return 0.0  # 範囲外は0を返す

    def ripeness_calculator(self, hsv_image, mask):
        # maskの領域の全ピクセルの熟度値を計算する関数
        weights = []
        
        for i in range(hsv_image.shape[0]):
            for j in range(hsv_image.shape[1]):
                if mask[i, j]:
                    weight = self.calculate_by_pixel(hsv_image[i, j])  # 熟度値を計算する関数
                    weights.append(weight)
        
        if len(weights) > 0:
            red_pixel_median = np.median(weights)
        else:
            red_pixel_median = 0
        
        return red_pixel_median

    def judge_ripeness(self, image, yolo_results, conf_tom, MIN_AREA_TH, tomato_dict):
        """
        熟度を判定し、熟したトマトの中心座標をリストで返す
        """
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        centers_of_ripe_tomato = []  # 熟したトマトの情報を保存するリスト
        centers_of_unripe_tomato = [] # 未熟トマトの情報を保存するリスト
        results_ripe = []         # 熟したトマトのYOLO結果
        results_non_ripe = []     # 未熟なトマトのYOLO結果
        ripenesses = []
        
        # print(f'\nyolo_results: {yolo_results}')
        
        for r in yolo_results:
            # print(f'\n\nr: {r}')
            # YOLO結果のコピーを作成
            ripe_result = copy.deepcopy(r)
            non_ripe_result = copy.deepcopy(r)
            
            ripe_result.boxes = []  # 初期化
            ripe_result.masks = []
            non_ripe_result.boxes = []
            non_ripe_result.masks = []
            dict_i = 1
            
            # マスクデータを取得
            masks = r.masks.data.cpu().numpy() if r.masks is not None else None
            # print(f'mask: {masks}')
            # print(f'mask_len: {len(masks)}')
            if masks is None:
                continue
            
            for ci, mask in enumerate(masks):
                label = r.names[r.boxes.cls.tolist()[ci]]  # トマトのラベルを取得
                scores = r.boxes.conf.cpu().numpy()[ci]  # 各スコアを取得
                # print(f'\n\nlabel, scores: {label, scores}')
                
                if label == "tomato" and scores > conf_tom:
                    # 各マスクの面積を計算
                    mask_area = np.sum(mask != 0)  # 255以外のピクセルがトマト領域を示す
                    if mask_area < MIN_AREA_TH:  # 面積がしきい値以下なら無視
                        continue
                    
                    mask = (mask * 255).astype(np.uint8)  # マスクを処理
                    ripeness = self.ripeness_calculator(hsv_image, mask)
                    # print(f"熟度: {ripeness}")
                    # 熟度値のみをまとめる
                    ripenesses.append(ripeness)
                    
                    # しきい値以上のトマト(＝熟したトマト)の中心点座標をripe_tomato_resultsに格納
                    # マスクの重心を計算
                    mask_indices = np.where(mask != 0)
                    center_y = int(np.mean(mask_indices[0]))
                    center_x = int(np.mean(mask_indices[1]))
                    # print(f"r.boxes[ci]: {r.boxes[ci]}")
                    if ripeness * 100 >= self.THRES:
                        is_ripe = True
                        centers_of_ripe_tomato.append([center_x, center_y])
                        # 熟したトマトの情報を追加
                        ripe_result.boxes.append(r.boxes[ci])
                        ripe_result.masks.append(r.masks[ci])
                    else:
                        is_ripe = False
                        centers_of_unripe_tomato.append([center_x, center_y])
                        # 未熟なトマトの情報を追加
                        non_ripe_result.boxes.append(r.boxes[ci])
                        non_ripe_result.masks.append(r.masks[ci])
                    
                    # print(f"\nripe_result: {ripe_result.boxes}")
                    
                    # 辞書作成
                    tomato_dict.append({
                        "id": f"T{str(dict_i).zfill(2)}",
                        "conf": scores,
                        "image_coords": [center_x, center_y],
                        "ripeness": ripeness,
                        "is_ripe": is_ripe,
                        "approach_ang": None,  # 後処理で追加予定
                        "camera_coords": None,  # 後処理で追加予定
                        "arm_coords": None,  # 後処理で追加予定
                        "harvest_order": None,  # 後処理で追加予定
                    })
                    dict_i+=1
            
            # 各結果が空でなければそれぞれのリストに追加
            if len(ripe_result.boxes) > 0:
                results_ripe.append(ripe_result)
            if len(non_ripe_result.boxes) > 0:
                results_non_ripe.append(non_ripe_result)
        
        return centers_of_ripe_tomato, centers_of_unripe_tomato, ripenesses, results_ripe, tomato_dict


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

if __name__ == "__main__":
    params = load_yaml("/home/ylab/hibikino_toms_ws/module/set_params.yaml")
    vision_params = params["vision_params"]
    CONF_TOM = vision_params["CONF_TOM_TH"]
    MIN_AREA_TH = vision_params["MIN_AREA_TH"]

    cXes = []
    cYs = []
    tomato_dict = []

    # 推論モデルの設定
    weight = '/home/ylab/hibikino_toms_ws/module/weights/base.pt'
    model = YOLO(weight)
    # 閾値を設定
    ripeness_threshold = 80
    # 画像を読み込み
    image = cv2.imread("/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/result/img/2025_02_02/16-51-53_orig_img.jpg")

    tomato_segmentation = Ripeness_Judge(vision_params)

    if image is not None:
        count = 0 # 描画用カウンタ
        # 推論
        yolo_results = model.predict(image, show_boxes=False, save=False, conf=0.3)

        # # 推論結果のうち、トマトの情報だけを抽出
        # result_tomato = [r for r in yolo_results if any(r.names[int(label)] == "tomato" for label in r.boxes.cls.cpu().numpy())]
        # print(f"\nresult_tomato : {result_tomato}")

        # 熟度を判定
        centers_of_ripe, centers_of_unripe, ripenesses, resuls_ripe_tom, tomato_dict = tomato_segmentation.judge_ripeness(image, yolo_results, CONF_TOM, MIN_AREA_TH, tomato_dict)

        print(f"ripenesses:{ripenesses}")
        # 画像に描画
        for i, r in enumerate(resuls_ripe_tom):
            masks = r.masks.data.cpu().numpy() if r.masks is not None else None  # マスクデータを取得
            if masks is None:
                continue

            for ci, mask in enumerate(masks):
                label = r.names[r.boxes.cls.tolist()[ci]]  # ラベルを確認
                if label == "tomato":  # トマトのみを描画
                    mask = (mask * 255).astype(np.uint8)  # マスクを処理
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.drawContours(image, contours, -1, (0, 0, 255), 2)  # 赤色で太さ1の輪郭を描画

                    # 輪郭の重心を計算
                    M = cv2.moments(contours[0])
                    if M["m00"] != 0:
                        cX = int(M["m10"] / M["m00"])
                        cXes.append(cX)
                        cY = int(M["m01"] / M["m00"])
                        cYs.append(cY)
                    else:
                        cX, cY = contours[0][0][0][0], contours[0][0][0][1]
        for i, ripeness in enumerate(ripenesses):
            ripeness = ripenesses[count]
            print(ripeness)

            # 文字の背景を白にするための矩形を描画
            background_width = 60  # 背景の幅
            background_height = 14  # 背景の高さ
            background_position = (cXes[count] - 51, cYs[count] + 12 - background_height)  # 背景の左上の位置

            cv2.rectangle(image, background_position, (background_position[0] + background_width, background_position[1] + background_height), (255, 255, 255), -1)  # 白い矩形を描画

            cv2.putText(image, f"{ripeness * 100:.2f}%", (cXes[count] - 50, cYs[count] + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)  # 文字を描画
            count = count + 1

        # 結果を表示
        cv2.imshow("Ripeness Detection", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
