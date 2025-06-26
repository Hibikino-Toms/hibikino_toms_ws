import cv2
import numpy as np
import os
import sys

from predict_extraction import Predict_Extra

"""
2024/11/10 時点

@author 吉永

トマト認識後、果梗領域や主茎領域、周辺の情報から、EEの進入角度を決定するコード

クラス引数：画像サイズ
[入力]
・yoloの推論結果

[出力]
・熟していると判断されたトマトの中心点座標の配列（熟したトマトの個数行ある）

"""
debug=True

def overlay_images(original_img, mask_img):    # 重ね合わせ画像の生成
    alpha = 0.6  # オリジナル画像の透明度
    beta = 1.0 - alpha  # マスク画像の透明度
    combined_img = cv2.addWeighted(original_img, alpha, mask_img, beta, 0)
    return combined_img

def drawing_elli_and_center(overlay, mask, ellipses_base, ellipses_small, ellipses_large, centers_of_AND_area):
    # 楕円の描画
    for i, ellipse in enumerate(ellipses_base):
        overlay = cv2.ellipse(overlay, ellipse, (0, 0, 0), 1)
        mask    = cv2.ellipse(mask, ellipse, (255, 255, 255), 1)
        if centers_of_AND_area[i] is not None: # アプローチが正面方向でなく、果梗が周辺にある場合
            overlay = cv2.ellipse(overlay, ellipse, (0, 0, 0), 1)
            overlay = cv2.ellipse(overlay, ellipses_large[i], (0, 0, 255), 2)
            mask    = cv2.ellipse(mask, ellipses_large[i], (0, 0, 255), 1)
        else:
            overlay = cv2.ellipse(overlay, ellipses_small[i], (0, 255, 0), 2)
    
    # 重心点の描画
    for i, center_of_AND_area in enumerate(centers_of_AND_area):
        if center_of_AND_area is not None:
            center_point = (int(center_of_AND_area[0]), int(center_of_AND_area[1]))
            overlay = cv2.circle(overlay, center_point, 5, (0, 0, 255), -1)
            mask    = cv2.circle(mask, center_point, 5, (0, 0, 255), -1)
    return overlay, mask


class Approach_Angle_Determiner():
    def __init__(self, params):
        self.IMG_HEIGHT = params["HEIGHT"]
        self.IMG_WIDTH = params["WIDTH"]
        
    def calculate_contour_center(self, contour):
        """
        輪郭の重心を計算する関数
        """
        moments = cv2.moments(contour)
        if moments["m00"] != 0:
            center_x = int(moments["m10"] / moments["m00"])
            center_y = int(moments["m01"] / moments["m00"])
            return (center_x, center_y)
        return None  # 面積が0の場合はNoneを返す

    def is_within_central_region(self, point):
        """
        与えられた点（重心）が中央領域に含まれているか判定
        """
        x, y = point
        return (self.margin_x <= x <= self.IMG_WIDTH - self.margin_x and
                self.margin_y <= y <= self.IMG_HEIGHT - self.margin_y)

    def calculate_ANDarea_and_center(self, peduncle_mask, ellipse):
        # 楕円マスクを生成
        ellipse_mask = np.zeros((self.IMG_HEIGHT, self.IMG_WIDTH), np.uint8)
        cv2.ellipse(ellipse_mask, ellipse, 255, -1)  # 指定の楕円でマスクを生成
        ellipse_mask = cv2.cvtColor(ellipse_mask, cv2.COLOR_GRAY2BGR)
        
        # 楕円領域と果梗領域の論理積領域を計算
        AND_mask = cv2.bitwise_and(peduncle_mask, ellipse_mask)
        
        # 重心を計算
        mask_gray = cv2.cvtColor(AND_mask, cv2.COLOR_BGR2GRAY)
        moments = cv2.moments(mask_gray, binaryImage=True)
        if moments['m00'] != 0:
            center_x = int(moments['m10'] / moments['m00'])
            center_y = int(moments['m01'] / moments['m00'])
            center_of_mass = (center_x, center_y)
        else:
            center_of_mass = None
        
        return center_of_mass

    def check(self, color_mask_peduncle, ellipse_large, ellipse_small):
        # 小さい楕円と果梗領域の論理積および重心を計算
        center_of_AND_area = self.calculate_ANDarea_and_center(color_mask_peduncle, ellipse_small)
        
        if center_of_AND_area is not None: # 小さい楕円で果梗あり → 大きい楕円で同様に計算して書き換える
            center_of_AND_area = self.calculate_ANDarea_and_center(color_mask_peduncle, ellipse_large)
        
        return center_of_AND_area

    def create_combined_mask(self, peduncle_mask, color_mask):
        mask_img = np.copy(peduncle_mask)
        mask_indices = color_mask != 0
        mask_img[mask_indices] = color_mask[mask_indices]
        
        return mask_img

    def numbering(self, image, contour_tomato, index): # 画像に処理順番を描画する関数
        # トマトの外接矩形の左上に認識順を描画
        x, y, w, h = cv2.boundingRect(contour_tomato)
        image = cv2.putText(
            image, str(index), 
            (x+int(w/2), y+h+30), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2
        )
        return image

    def calculate_ellipse_and_peduncle(self, results, mask_main_stem, mask_peduncle, mask_tomato):
        boundary_color = (0, 255, 0)
        # self.margin_y = self.IMG_HEIGHT // 30
        # self.margin_x = self.IMG_WIDTH // 30
        self.margin_y = 0
        self.margin_x = self.IMG_WIDTH // 10

        centers_of_AND_area = []
        ellipses_base = []
        ellipses_large = []
        ellipses_small = []
        
        for r in results:
            # Combine the color masks and create the combined mask
            # mask_img = self.create_combined_mask(mask_peduncle, mask_tomato)
            mask_ped_and_stem = self.create_combined_mask(mask_main_stem, mask_peduncle)

            # if debug:
            #     overlay_image = overlay_images(img, mask_img)
            # mask_img = cv2.rectangle(mask_img, (self.margin_x, self.margin_y), (self.IMG_WIDTH - self.margin_x, self.IMG_HEIGHT - self.margin_y), boundary_color, 2)
            # overlay_image = cv2.rectangle(overlay_image, (self.margin_x, self.margin_y), (self.IMG_WIDTH - self.margin_x, self.IMG_HEIGHT - self.margin_y), boundary_color, 2)

            tomato_index = 1  # トマトの順番カウンタを初期化

            for ci, c in enumerate(r):
                contour_tomato = c.masks.xy.pop().astype(np.int32).reshape(-1, 1, 2)
                if len(contour_tomato) >= 5:
                    center_of_contour = self.calculate_contour_center(contour_tomato)
                    if center_of_contour is not None and self.is_within_central_region(center_of_contour):
                        ellipse_base = cv2.fitEllipse(contour_tomato)
                        ellipses_base.append(ellipse_base)

                        ellipse_small = (
                            ellipse_base[0],
                            (ellipse_base[1][0] * 0.8, ellipse_base[1][1] * 0.8),
                            ellipse_base[2]
                        )
                        ellipse_large = (
                            ellipse_base[0],
                            (ellipse_base[1][0] * 1.2, ellipse_base[1][1] * 1.2),
                            ellipse_base[2]
                        )

                        ellipses_small.append(ellipse_small)
                        ellipses_large.append(ellipse_large)

                        # AND領域と重心を計算する関数の使用
                        center_of_AND_area = self.check(mask_ped_and_stem, ellipse_large, ellipse_small)
                        centers_of_AND_area.append(center_of_AND_area)
                    else : # 輪郭情報がない、もしくはマスク重心が縁領域にある
                        center_of_AND_area = False
                        ellipse_large = []
                        centers_of_AND_area.append(center_of_AND_area)
                        ellipses_large.append(ellipse_large)
        
        return centers_of_AND_area, ellipses_large

    def calculate_approach_angle(self, centers_ANDarea, ellipses, tom_pos, tomato_dict):
        angles = []
        indexes = []
        indexes_to_remove = []
        updated_tomato_dict = []  # IDを調整した新しいリスト
        idx = 0

        print(f"tomato_dict : {tomato_dict}")
        if len(tom_pos) != 0:
            for i, tom_data in enumerate(tomato_dict):
                print(f"i= {i}")
                if tom_data["is_ripe"] == True: # 熟してるトマト
                    if centers_ANDarea[idx] == False: # トマトが縁領域にある場合
                        print(f"c_point: {centers_ANDarea[idx]}")
                        angle = False
                    elif centers_ANDarea[idx] == None: # 果梗が手前に無い場合
                        print(f"c_point: {centers_ANDarea[idx]}")
                        angle = 0
                    else :
                        print(f"c_point: {centers_ANDarea[idx]}")
                        elli_center_x, elli_center_y = ellipses[idx][0]
                        dis_center2point = elli_center_x - centers_ANDarea[idx][0]
                        if dis_center2point < 0: # AND領域の中心が右にある場合
                            angle = -1
                        else: # AND領域の中心が左にある場合
                            angle = 1
                    angles.append(angle)
                    print(f"Assigned angle: {angle}")
                    tom_data["approach_ang"] = angle
                    idx += 1
                else: # 未熟トマト
                    pass
            print(f"tomato_dict : {tomato_dict}")

            angles = np.array(angles)
            angles = angles.reshape(-1, 1)
            # print(f'tom_pos: {tom_pos}')
            # print(f'angles : {angles}')
            tom_pos = np.hstack((tom_pos, angles))
        print(f"tom_pos: {tom_pos}")
        # angleがNoneのトマト（画像の縁にあるトマト）を排除
        tom_pos[tom_pos[:, -1] != False]
        print(f"tom_pos: {tom_pos}")
        tomato_dict = [item for item in tomato_dict if item["approach_ang"] is not False]
        for i, tom_data in enumerate(tomato_dict):
            tom_data["id"] = f"T{str(i+1).zfill(2)}"

        return tom_pos, tomato_dict
    
    def determine_angle(self, results, mask_main_stem, mask_peduncle, mask_tomato, tom_pos, tomato_dict):
        # トマト領域と果梗領域の論理積領域を計算
        # 論理積領域があればその重心を、なければNoneを配列に格納する．判断に使われた楕円（フィッティングした楕円より少し大きい楕円）も返ってくる
        centers_of_AND_area, ellipses_large = self.calculate_ellipse_and_peduncle(results, mask_main_stem, mask_peduncle, mask_tomato)
        print(f'楕円と果梗の論理積領域の中心座標（論理積領域がないもの=None）: {centers_of_AND_area}')
        print(f"tom_pos:{tom_pos}")

        # 手先進入角度を決める処理
        tom_pos_with_approach_angs, tomato_dict = self.calculate_approach_angle(centers_of_AND_area, ellipses_large, tom_pos, tomato_dict)
        # print(f'手先進入角度（左方向:負、右方向:正 / 左右1段階で設定）: \n{tom_pos_with_approach_angs}')

        return tom_pos_with_approach_angs, tomato_dict

if __name__ == "__main__":
    img_path = "/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/img/2025_01_20/09-12-42_filtered_img.jpg"
    img = cv2.imread(img_path)
    # img_height, img_width = img.shape[:2]
    # img_shape = img.shape[:2]

    angle_determiner = Approach_Angle_Determiner()
    
    predict_extra = Predict_Extra(
    weight='/home/ylab/hibikino_toms_ws/module/weights/best.pt',
    thres_conf_stem=0.6,
    thres_conf_ped=0.1,
    thres_conf_tom=0.3
    )

    conf=0.1
    boxes=False
    iou=0.3
    tomato_dict = []
    # 推論実行
    results = predict_extra.run_predict(img, conf=conf, boxes=boxes, iou=iou)
    # マスク画像生成
    proc_time, color_mask, mask_main_stem, mask_peduncle, mask_tomato = predict_extra.extraction_and_color_mask(results)
    
    tomato_dict.append({
            "id": f"T{str(1).zfill(2)}",
            "conf": 1.000,
            "image_coords": (300, 200),
            "ripeness": 1.0000,
            "is_ripe": True,
            "approach_ang": None,  # 後処理で追加予定
            "camera_coords": None,  # 後処理で追加予定
            "world_coords": None,  # 後処理で追加予定
        })
    tom_pos = [[340,240]]
    # 手先進入角度の決定
    angle = angle_determiner.determine_angle(results, img.shape[:2], mask_main_stem, mask_peduncle, mask_tomato, tom_pos, tomato_dict)
    print("辞書型のトマトデータは適当に作成してるので注意")
    print(angle)