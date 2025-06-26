import os
import cv2
import numpy as np
from ultralytics import YOLO

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

ripenesses = []
cXes = []
cYs = []

# 熟度判定を行うクラス
class Ripeness_Judge:
    def __init__(self, ripeness_threshold=70):
        self.thres = ripeness_threshold  # 熟度判定の閾値

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

    def judge_ripeness(self, image, results):
        """
        熟度を判定し、熟したトマトの中心座標をリストで返す
        """
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        ripe_tomato_results = []  # 熟したトマトの情報を保存するリスト

        # print(f"推論結果の数: {len(results)}")  # デバッグ用: 推論結果の数を出力
        for r in results:
            # マスクデータを取得
            masks = r.masks.data.cpu().numpy() if r.masks is not None else None
            if masks is None:
                continue
            
            for ci, mask in enumerate(masks):
                label = r.names[r.boxes.cls.tolist()[ci]]  # トマトのラベルを取得
                if label == "tomato":
                    mask = (mask * 255).astype(np.uint8)  # マスクを処理
                    ripeness = self.ripeness_calculator(hsv_image, mask)
                    # print(f"熟度: {ripeness}")
                    ripenesses.append(ripeness)

                    # しきい値以上のトマト(＝熟したトマト)の中心点座標をripe_tomato_resultsに格納
                    if ripeness * 100 >= self.thres:
                        # マスクの重心を計算
                        mask_indices = np.where(mask != 0)
                        center_y = int(np.mean(mask_indices[0]))
                        center_x = int(np.mean(mask_indices[1]))
                        center = [center_x, center_y]
                        ripe_tomato_results.append(center)
                    
        # print(ripe_tomato_results)
        return ripe_tomato_results


if __name__ == "__main__":
    # 推論モデルの設定
    weight = '/home/toms/hibikino_toms_ws/module/weights/best.pt'
    model = YOLO(weight)
    # 閾値を設定
    ripeness_threshold = 80
    # 画像を読み込み
    image = cv2.imread("/home/toms/hibikino_toms_ws/src/vision_pkg/vision_pkg/img/image-2.png")
    image = resized_image = cv2.resize(image, (640, 480))

    tomato_segmentation = Ripeness_Judge(ripeness_threshold)

    if image is not None:
        count = 0 # 描画用カウンタ
        # 推論
        yolo_results = model.predict(image, boxes=False, save=False, conf=0.8)

        # 推論結果のうち、トマトの情報だけを抽出
        result_tomato = [r for r in yolo_results if any(r.names[int(label)] == "tomato" for label in r.boxes.cls.cpu().numpy())]

        # 熟度を判定
        result_tomato_centers = tomato_segmentation.judge_ripeness(image, result_tomato)
        
        
        # 画像に描画
        for i, r in enumerate(result_tomato):
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
            # print(ripeness)

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
