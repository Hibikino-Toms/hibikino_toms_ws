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
import random
import time
import sys
import yaml

from ultralytics import YOLO

"""
Predict_Extraクラスの引数:
1. 推論モデルの重みファイルのパス
2. main-stemの信頼度しきい値
3. peduncleの信頼度しきい値
4. tomatoの信頼度しきい値
"""
class Predict_Extra():
    def __init__(self, vision_params):
        WEIGHT_PATH = vision_params["WEIGHT_PATH"]     # 最終的に仕様する重みのパスを入力
        self.model = YOLO(WEIGHT_PATH)
        
        # 信頼度しきい値
        self.CONF_STEM = vision_params["CONF_MAIN_STEM_TH"]
        self.CONF_PED = vision_params["CONF_PED_TH"]
        self.CONF_TOM = vision_params["CONF_TOM_TH"]

        # 画像サイズ
        self.IMG_WIDTH = vision_params["camera_params"]["WIDTH"]
        self.IMG_HEIGHT = vision_params["camera_params"]["HEIGHT"]
        
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
        result = self.model.predict(source=image,
                                    retina_masks=True,
                                    conf=conf,
                                    show_boxes=boxes,
                                    iou=iou,
                                    save=False)
        return result

    # 俯瞰カメラ用でトマトがあるかのチェック用の推論実行結果
    def check_predict(self, F_B, image, conf=0.1, boxes=False, iou=0.3):
        # 中央領域の幅と高さを設定
        central_area_left = self.IMG_WIDTH * 0  # 画像幅の %（中央領域の左端）
        central_area_right = self.IMG_WIDTH * 0.4  # 画像幅の %（中央領域の右端）
        central_area_top = 0  # 高さ方向の中央領域上端（画像の最上部）
        central_area_bottom = self.IMG_HEIGHT  # 高さ方向の中央領域下端（画像の最下部）

        # 推論を実行
        yolo_result = self.model.predict(source=image,
                                        retina_masks=True,
                                        conf=conf,
                                        show_boxes=boxes,
                                        iou=iou,
                                        save=False)

        # "tomato"の情報を格納するリスト
        detected_tomatoes = []

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
                    
                    # トマトがロボットの前に相当する領域に収まっているかを確認
                    if central_area_left <= center_x <= central_area_right and central_area_top <= center_y <= central_area_bottom:
                        detected_tomatoes.append((center_x, center_y))

        # F_Bに基づいて一番端のトマトを見つける
        target_tomato = None
        if F_B == 'f':  # 一番左端のトマト
            target_tomato = min(detected_tomatoes, key=lambda t: t[0], default=None)
        elif F_B == 'b':  # 一番右端のトマト
            target_tomato = max(detected_tomatoes, key=lambda t: t[0], default=None)

        # 重心計算の準備
        if target_tomato:
            radius = 150  # 半径150ピクセル
            close_tomatoes = []  # 半径150ピクセル以内のトマト→房の考慮。認識したトマト全部だと、別のところにあるトマトも含むので大きすぎたり小さい

            for tomato in detected_tomatoes:
                dx = tomato[0] - target_tomato[0]
                dy = tomato[1] - target_tomato[1]
                distance = (dx**2 + dy**2)**0.5
                if distance <= radius:
                    close_tomatoes.append(tomato)

            # 重心を計算→房の下のほうにあるトマトが「一番端のトマト」だった場合、房全部を捉えられない場合があるから
            if close_tomatoes:
                center_x = sum(t[0] for t in close_tomatoes) / len(close_tomatoes)
                center_y = sum(t[1] for t in close_tomatoes) / len(close_tomatoes)
                return [(int(center_x), int(center_y))]

        # トマトが見つからない場合は None を返す
        return None


    # 領域分割・カラーマスク作成
    def extraction_and_color_mask(self, results):
        proc_times = []
        proc_time = 0
        for r in results:
            proc_time = sum(r.speed.values())
            proc_times.append(proc_time) # 処理時間の保存
            cnt_main_stem = 1
            cnt_peduncle = 1
            cnt_tomato = 1
            
            img = np.copy(r.orig_img)
            print(f"img.shape: {img.shape}") 
            
            # マスク画像のもとになる黒い画像を生成
            color_mask = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
            color_mask_main_stem = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
            color_mask_peduncle = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
            color_mask_tomato = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
            
            masks = r.masks.data.cpu().numpy() # 画像上で認識したすべてのマスク情報
            
            for ci, (c, mask) in enumerate(zip(r, masks)): # 認識した一つのセグメント一つあたりを取り扱う。一つのセグメント…「c」
                label = c.names[r.boxes.cls.tolist()[ci]]  # そのセグメントのラベル
                score = c.boxes.conf.tolist().pop()  # そのセグメントの信頼度
                mask = (mask * 255).astype(np.uint8)  # マスクを処理
                
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) # そのセグメントの輪郭情報
                match label: # そのセグメントのラベルが...
                    case "main-stem": # 主茎の場合、
                        if score >= self.CONF_STEM: # かつしきい値以上の信頼値の場合、
                            cnt_main_stem += 1
                            color = self.generate_color_code(cnt_main_stem, label)
                            color_mask_main_stem = cv2.drawContours(color_mask_main_stem, contours, -1, color, cv2.FILLED)
                            mask_indices = color_mask_main_stem != 0
                            color_mask[mask_indices] = color_mask_main_stem[mask_indices]
                    case "peduncLe": # 果梗の場合、
                        if score >= self.CONF_PED: # かつしきい値以上の信頼値の場合、
                            cnt_peduncle += 1
                            color = self.generate_color_code(cnt_peduncle, label)
                            color_mask_peduncle = cv2.drawContours(color_mask_peduncle, contours, -1, color, cv2.FILLED)
                            mask_indices = color_mask_peduncle != 0
                            color_mask[mask_indices] = color_mask_peduncle[mask_indices]
                    case "tomato":
                        if score >= self.CONF_TOM:
                            cnt_tomato += 1
                            color = self.generate_color_code(cnt_tomato, label)
                            color_mask_tomato = cv2.drawContours(color_mask_tomato, contours, -1, color, cv2.FILLED)
                            mask_indices = color_mask_tomato != 0
                            color_mask[mask_indices] = color_mask_tomato[mask_indices]
        
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

    def main(self, imgsize, input_type, Input, output_dir):
        show_img, show_time, save_run_info, save_result_img = self.set_running()

        # 入力となる画像ファイルの設定
        if input_type == "directory":
            image_files = [f for f in os.listdir(Input) if f.endswith(('.jpg', '.jpeg', '.png'))]
            num_images = len(image_files)
        elif input_type == "file":
            image_files = [Path(Input).name]
            num_images = 1

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
        
        print(f"\n推論処理時間(ms): {proc_times}")

        if save_run_info:
            self.write_to_file(output_dir, proc_times, num_images, self.CONF_STEM, self.CONF_PED, self.CONF_TOM)


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
    # 信頼値のしきい値
    # print("各クラスの信頼値しきい値を入力してください。[0~1の浮動小数]")
    # conf_main_stem = float(input("main_stem: "))
    # conf_peduncle = float(input("peduncle: "))
    # conf_tomato = float(input("tomato: "))
    conf_main_stem = 0.5
    conf_peduncle = 0.1
    conf_tomato = 0.5

    params = load_yaml('/home/ylab/hibikino_toms_ws/module/set_params.yaml')
    params = params["vision_params"]

    # 入力項目１：使用する重みのパスを入力
    weight = "/home/ylab/hibikino_toms_ws/module/weights/best.pt"

    pre_ext = Predict_Extra(params)
    # 入力項目２：推論したい画像のパス、または画像が格納されたディレクトリパス
    Input = "/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/result/img/2025_01_31/05-36-23_orig_img.jpg"

    # 入力項目３：推論結果の画像等を保存するディレクトリパス
    output_dir = "/home/yasukawa_lab/yoshinaga/tomato/post_processing"

    output_dir = os.path.join(output_dir, f"conf={conf_main_stem}_{conf_peduncle}_{conf_tomato}")

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
    
    pre_ext.main(imgsize, input_type, Input, output_dir)
