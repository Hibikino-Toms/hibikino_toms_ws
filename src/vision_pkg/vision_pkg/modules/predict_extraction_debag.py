"""
指定した条件でインスタンセグメンテーション推論を実行し、
・推論結果のカラーマスク画像
・推論結果をクラス別に分けたカラーマスク画像
・推論結果のカラーマスク画像と元画像を重ね合わせた画像
を作成するコード。
結果の保存や結果の表示、実行情報（実行した日時や推論にかかった処理時間など）をテキストファイルに保存することが可能。

〜使い方〜
① コード最下部の「if __name__ == "__main__":」内の、入力項目にそれぞれ必要な情報を入力して実行する
② 実行設定（結果の表示/結果の保存/実行時・結果の情報の保存）を尋ねられるのでキー入力で回答する（Enterのみ → Noで入力される）
③ 推論が実行され、"データを保存する"場合、データが指定した場所に保存される

Author: 吉永
"""
from pathlib import Path
import os

import cv2
import numpy as np
from ultralytics import YOLO
import random
import time
import sys

from realsense_module import Realsense_Module

"""
Predict_Extraクラスの引数:
1. 推論モデルの重みファイルのパス
2. main-stemの信頼度しきい値
3. peduncleの信頼度しきい値
4. tomatoの信頼度しきい値
"""
class Predict_Extra():
    def __init__(self, weight, thres_conf_stem, thres_conf_ped, thres_conf_tom):
        self.model = YOLO(weight)
        self.conf_stem = thres_conf_stem
        self.conf_ped = thres_conf_ped
        self.conf_tom = thres_conf_tom

        # tomatoのうち、「領域の面積が小さいものは除外する」処理のしきい値
        self.MIN_AREA_TH = 1000

    # カラーマスクのためのBGR値を作成
    def generate_color_code(self, counter, label):
        while True:
            # 近い色の生成を避けるために5刻みで乱数生成
            if label == "main-stem": # 赤っぽい色
                random.seed(counter) # シードを一定の数値にする→実行のたびに同じ乱数生成を行い、適応される色の順序が同じ
                num_R = random.randint(40, 51) * 5  # Rを高めに設定
                num_G = random.randint(0, 20) * 5    # Gを低めに設定
                num_B = random.randint(0, 20) * 5    # Bを低めに設定

            elif label == "peduncLe": # 青っぽい色
                random.seed(counter)
                num_R = random.randint(0, 10) * 5    # Rを低めに設定
                num_G = random.randint(0, 51) * 5    # Gを低めに設定
                num_B = random.randint(40, 51) * 5  # Bを高めに設定
                
            elif label == "tomato": # 緑っぽい色
                random.seed(counter)
                num_R = random.randint(0, 40) * 5  # Rを高めに設定
                num_G = random.randint(36, 51) * 5  # Gを高めに設定
                num_B = random.randint(0, 20) * 5    # Bを低めに設定

            color = (num_B, num_G, num_R)
            return color
    
    # テキストファイルに情報を保存する
    def write_to_file(self, dir, proc_times, num_images, conf_stem, conf_ped, conf_tom): 
        file_name = "Running_information.txt"
        file_path = os.path.join(dir, file_name)

        proc_time_ave = sum(proc_times) / num_images

        # ファイルに追記
        with open(file_path, 'w') as file:  # 'a' モード：追記
            current_datetime = time.strftime("%Y-%m-%d %H:%M:%S")    # 現在の日付と時刻を取得
            file.write(f"Running date: {current_datetime}\n")
            file.write(f"Confidence value of main-stem: {conf_stem}\n")
            file.write(f"Confidence value of peduncle: {conf_ped}\n")
            file.write(f"Confidence value of tomato: {conf_tom}\n")
            file.write(f"Total processing time(ms): {sum(proc_times):.3f}\n")
            file.write(f"Number of processed images: {num_images}\n")
            file.write(f"Average processing time(ms): {proc_time_ave:.2f}\n")
            file.write("\n")

        print(f"ファイル '{file_name}' に情報を追記しました。\n")
    
    # ユーザに実行設定（結果表示や保存など）を尋ねる
    def set_running(self):  
        while True:
            response_show_image = input("推論結果を画面に表示させますか？ [y/n]: ").strip().lower()
            if not response_show_image:  # Enterが押された場合、'n'として扱う
                show_img = False
                show_time = None
                break
            elif response_show_image in ('y', 'n'):
                show_img = response_show_image == 'y'
                show_time = float(input("      →何秒間表示させますか？ [数字のみ]: ")) if show_img else None
                break
            else:
                print("無効な入力です。")
        
        while True:
            response_run_info = input("推論実行の情報をテキストファイルに保存しますか？ [y/n]: ").strip().lower()
            if not response_run_info:  # Enterが押された場合、'n'として扱う
                save_run_info = False
                break
            elif response_run_info in ('y', 'n'):
                save_run_info = response_run_info == 'y'
                break
            else:
                print("無効な入力です。")

        while True:
            response_result_img = input("推論結果の画像を保存しますか？ [y/n]: ").strip().lower()
            if not response_result_img:  # Enterが押された場合、'n'として扱う
                save_result_img = False
                break
            elif response_result_img in ('y', 'n'):
                save_result_img = response_result_img == 'y'
                break
            else:
                print("無効な入力です。")

        return show_img, show_time, save_run_info, save_result_img
    
    # 重ね合わせ画像の生成
    def overlay_images(self, original_img, mask_img):
        # 透明度を指定して画像を重ね合わせる
        alpha = 0.5  # オリジナル画像の透明度
        beta = 1.0 - alpha  # マスク画像の透明度

        combined_img = cv2.addWeighted(original_img, alpha, mask_img, beta, 0)

        return combined_img

    # 推論の実行とその結果を返す
    def run_predict(self, image, conf=0.1, boxes=False, iou=0.3):
        result =  self.model.predict(source=image, conf=conf, boxes=boxes, iou=iou, save=False)
        return result

    # 領域分割・カラーマスク作成
    def extraction_and_color_mask(self, results):
        proc_times = []
        for r in results:
            proc_time = sum(r.speed.values())
            proc_times.append(proc_time) # 処理時間の保存
            counter_main_stem = 1
            counter_peduncle = 1
            counter_tomato = 1

            img = np.copy(r.orig_img)

            # マスク画像のもとになる黒い画像を生成
            color_mask = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
            color_mask_main_stem = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
            color_mask_peduncle = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
            color_mask_tomato = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)

            # iterate each object contour 
            for ci,c in enumerate(r):
                # print(type(ci), type(c))
                label = c.names[c.boxes.cls.tolist().pop()]
                score = c.boxes.conf.tolist().pop()
                # print(f"{label}: {score}")
                # クラス別に領域分割
                match label:
                    case "main-stem":
                        # print(f"しきい値 :{self.conf_stem} → ", end="")
                        if score >= self.conf_stem:
                            # print("以上")
                            counter_main_stem += 1
                            color = self.generate_color_code(counter_main_stem, label)
                            contour_main_stem = c.masks.xy.pop().astype(np.int32).reshape(-1, 1, 2)
                            color_mask_main_stem = cv2.drawContours(color_mask_main_stem, [contour_main_stem], -1, color, cv2.FILLED)
                            mask_indices = color_mask_main_stem != 0
                            color_mask[mask_indices] = color_mask_main_stem[mask_indices]
                        # else:
                        #     print("未満")
                    
                    case "peduncLe":
                        # print(f"しきい値 :{self.conf_ped} → ", end="")
                        if score >= self.conf_ped:
                            # print("以上")
                            counter_peduncle += 1
                            color = self.generate_color_code(counter_peduncle, label)
                            contour_peduncle = c.masks.xy.pop().astype(np.int32).reshape(-1, 1, 2)
                            color_mask_peduncle = cv2.drawContours(color_mask_peduncle, [contour_peduncle], -1, color, cv2.FILLED)
                            mask_indices = color_mask_peduncle != 0
                            color_mask[mask_indices] = color_mask_peduncle[mask_indices]
                        # else:
                        #     print("未満")

                    case "tomato":
                        # print(f"しきい値 :{self.conf_tom} → ", end="")
                        if score >= self.conf_tom:
                            mask_areas = [mask.data.cpu().numpy().sum() for mask in c.masks]  # マスクの面積（ピクセル数）を計算
                            # if all(area > self.MIN_AREA_TH for area in mask_areas):
                            counter_tomato += 1
                            color = self.generate_color_code(counter_tomato, label)
                            contour_tomato = c.masks.xy.pop().astype(np.int32).reshape(-1, 1, 2)
                            color_mask_tomato = cv2.drawContours(color_mask_tomato, [contour_tomato], -1, color, cv2.FILLED)
                            mask_indices = color_mask_tomato != 0
                            color_mask[mask_indices] = color_mask_tomato[mask_indices]
                        # else:
                        #     print("未満")
        
        return proc_time, color_mask, color_mask_main_stem, color_mask_peduncle, color_mask_tomato

    # 画像を画面に表示する（set_runningで「表示する」を選択した場合）
    def show_result(self, show_time, color_mask, color_mask_main_stem, color_mask_peduncle, color_mask_tomato, overlay_image):
        # 推論結果の表示
        # cv2.imshow("Original Image", img)
        cv2.imshow("Color Mask - main_stem", color_mask_main_stem)
        cv2.imshow("Color Mask - peduncle", color_mask_peduncle)
        cv2.imshow("Color Mask - tomato", color_mask_tomato)
        cv2.imshow("Color Mask", color_mask)
        cv2.imshow("Overlay", overlay_image)
        # print(color_mask.shape)
        show_time = int(show_time)
        cv2.waitKey(show_time * 1000)
        cv2.destroyAllWindows()

    # 画像を指定したディレクトリに保存する（set_runningで「保存する」を選択した場合）
    def save_result(self, output_dir, image_file, color_mask, color_mask_main_stem, color_mask_peduncle, color_mask_tomato, overlay_image):
        # 保存するディレクトリの指定/ない場合作成
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            output_dir_mask = output_dir + "/color_mask"
            output_dir_main_stem = output_dir + "/main_stem"
            output_dir_peduncle = output_dir + "/peduncle"
            output_dir_tomato = output_dir + "/tomato"
            output_dir_overlay = output_dir + "/overlay"
            if not os.path.exists(output_dir_mask):
                os.makedirs(output_dir_mask)
            if not os.path.exists(output_dir_main_stem):
                os.makedirs(output_dir_main_stem)
            if not os.path.exists(output_dir_peduncle):
                os.makedirs(output_dir_peduncle)
            if not os.path.exists(output_dir_tomato):
                os.makedirs(output_dir_tomato)
            if not os.path.exists(output_dir_overlay):
                os.makedirs(output_dir_overlay)

            output_path_color = os.path.join(output_dir_mask, f"mask_{image_file}")
            output_path_main_stem_color = os.path.join(output_dir_main_stem, f"main_stem_{image_file}")
            output_path_peduncle_color = os.path.join(output_dir_peduncle, f"peduncle_{image_file}")
            output_path_tomato_color = os.path.join(output_dir_tomato, f"tomato_{image_file}")
            output_path_overlay_color = os.path.join(output_dir_overlay, f"overlay_{image_file}")
            
            # 保存
            cv2.imwrite(output_path_color, color_mask)
            cv2.imwrite(output_path_main_stem_color, color_mask_main_stem)
            cv2.imwrite(output_path_peduncle_color, color_mask_peduncle)
            cv2.imwrite(output_path_tomato_color, color_mask_tomato)
            cv2.imwrite(output_path_overlay_color, overlay_image)

        # 俯瞰カメラ用でトマトがあるかのチェック用の推論実行結果
    
    def check_predict(self, F_B, image, conf=0.1, boxes=False, iou=0.3):
        # 推論を実行
        yolo_result = self.model.predict(source=image, conf=conf, boxes=boxes, iou=iou, save=False)
        
        tom_pos = []  # トマトの中心座標を格納するリスト
        
        # 画像の高さと幅を取得
        img_height, img_width = image.shape[:2]
        
        # 中央領域の幅と高さを設定
        central_area_left = img_width * 0.2  # 画像幅の20%（中央領域の左端）
        central_area_right = img_width * 0.8  # 画像幅の80%（中央領域の右端）
        central_area_top = 0  # 高さ方向の中央領域上端（画像の最上部）
        central_area_bottom = img_height  # 高さ方向の中央領域下端（画像の最下部）
        
        # "tomato"が検出されているか確認
        for r in yolo_result:
            for c in r:
                label = c.names[c.boxes.cls.tolist().pop()]  # クラス名
                score = c.boxes.conf.tolist().pop()  # 信頼度
                if label == "tomato" and score > 0.6:  # "tomato"が検出され、信頼度が指定以上の場合
                    # トマトの座標（ボックス）を取得
                    x1, y1, x2, y2 = c.boxes.xyxy.tolist()[0]  # バウンディングボックスの座標（左上・右下）
                    center_x = (x1 + x2) / 2  # バウンディングボックスの中心X座標
                    center_y = (y1 + y2) / 2  # バウンディングボックスの中心Y座標
                    
                    # トマトが中央領域に収まっているかを確認
                    if central_area_left <= center_x <= central_area_right and central_area_top <= center_y <= central_area_bottom:
                        print("トマトがロボットの前にありやす")
                        # F_Bの条件に応じて最も左または右のトマトを選択
                        if F_B == 'f':  # 一番左端のトマト
                            if not tom_pos or center_x < tom_pos[0][0]:  # 最も左のトマトを選ぶ
                                tom_pos = [(center_x, center_y)]
                        elif F_B == 'b':  # 一番右端のトマト
                            if not tom_pos or center_x > tom_pos[0][0]:  # 最も右のトマトを選ぶ
                                tom_pos = [(center_x, center_y)]
        
        print(f"toms: {tom_pos}")
        return tom_pos


    def main(self, imgsize, input_type, Input, output_dir):
        show_img, show_time, save_run_info, save_result_img = self.set_running()

        # 入力となる画像ファイルの設定
        if input_type == "directory":
            image_files = [f for f in os.listdir(Input) if f.endswith(('.jpg', '.jpeg', '.png'))]
            num_images = len(image_files)
        elif input_type == "file":
            image_files = [Path(Input).name]
            num_images = 1

        cnt = 0
        while 1:
            # 一枚ずつ、「推論実行 → クラス別に領域抽出 → 保存」
            for image_file in image_files:
                input_path = os.path.join(Input, image_file) if input_type == "directory" else Input
                print(f"\n{image_file}")
                # resize
                img = cv2.imread(input_path)
                height, width = img.shape[:2]
                # 画像の大きい方のサイズを640にリサイズする
                if max(width, height) > imgsize:
                    if width > height:
                        new_width = imgsize
                        new_height = int((height / width) * imgsize)
                    else:
                        new_height = imgsize
                        new_width = int((width / height) * imgsize)

                    # アスペクト比を維持してリサイズ
                    img = cv2.resize(img, (new_width, new_height))

                # 推論の実行
                results = self.run_predict(img, boxes=False, conf=0.1, iou=0.3)

                # 領域分割とカラーマスク画像の生成
                proc_times, color_mask, color_mask_main_stem, color_mask_peduncle, color_mask_tomato = self.extraction_and_color_mask(results)

                # 重ね合わせ画像の生成
                overlay_image = self.overlay_images(img, color_mask)
                
                if show_img:
                    self.show_result(show_time, color_mask, color_mask_main_stem, color_mask_peduncle, color_mask_tomato, overlay_image)

                if save_result_img:
                    self.save_result(output_dir, image_file, color_mask, color_mask_main_stem, color_mask_peduncle, color_mask_tomato, overlay_image)
            
            # print(f"\n推論処理時間(ms): {proc_times}")
            cnt += 1
            time.sleep(5)
            if cnt >= 1:
                break
        if save_run_info:
            self.write_to_file(output_dir, proc_times, num_images, self.conf_stem, self.conf_ped, self.conf_tom)


if __name__ == "__main__":
    # 信頼値のしきい値
    CONF_MAIN_STEM_TH = 0.6
    CONF_PED_TH = 0.1
    CONF_TOM_TH = 0.3

    rs = Realsense_Module()
    # 入力項目１：使用する重みのパスを入力
    weight = "/home/ylab/hibikino_toms_ws/module/weights/best_Add_data.pt"

    pre_ext = Predict_Extra(weight, CONF_MAIN_STEM_TH, CONF_PED_TH, CONF_TOM_TH)
    # 入力項目２：推論したい画像のパス、または画像が格納されたディレクトリパス
    rs.setup("230322272057")
    # img, depth_img, depth_frame = rs.get_image(show=True)
    # cv2.imwrite('/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/img/orig_imga.png', img)
    
    Input = "/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/img/2024_12_21/16-00-28_filtered_img.jpg"
    img = Input

    # 入力項目３：推論結果の画像等を保存するディレクトリパス
    output_dir = "/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/img"

    output_dir = os.path.join(output_dir, f"conf={CONF_MAIN_STEM_TH}_{CONF_PED_TH}_{CONF_TOM_TH}")

    imgsize = 640
    # imgsize = input("画像サイズを入力： ")
    # dir_name = input("学習結果を保存したディレクトリと同じ名前を入力(ex. : v8_l_500)： ")

    p = Path(Input)
    if p.is_file():
        input_type = "file"
    elif p.is_dir():
        input_type = "directory"
    else:
        print("正しいパスを入力してください")
        sys.exit(0)
    
    # pre_ext.run_predict(F_B="f", image=img, conf=0.1, boxes=False, iou=0.3)
    
    pre_ext.main(imgsize, input_type, Input, output_dir)
