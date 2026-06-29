import time
import cv2
import pyrealsense2 as rs
import numpy as np
import yaml

from ultralytics import YOLO

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

# カメラの初期化と画像取得
def capture_image():
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    pipeline.start(config)

    try:
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        color_image = np.asanyarray(color_frame.get_data())
    finally:
        pipeline.stop()

    return color_image

# トマトのセグメンテーション処理
def segment_tomatoes(image, weight_path):
    
    # YOLOv8モデルのロード（指定された重みを使用）
    model = YOLO(weight_path)
    yolo_results = model.predict(image)
    tomato_segments = []
    
    for result in yolo_results[0].boxes:
        class_id = int(result.cls[0])
        if class_id == 2:  # トマトクラスのみを対象とする
            x_min, y_min, x_max, y_max = result.xyxy[0]
            confidence = result.conf[0]
            tomato_segments.append({
                'bbox': (x_min, y_min, x_max, y_max),
                'confidence': confidence
            })
    
    return tomato_segments

# ピクセルごとの赤色度を計算
def calculate_by_pixel(hsv_pixel):
    h, s, v = hsv_pixel
    if 1 <= h <= 40:
        return 1 - (h - 1) * (0.95 / 39)
    elif 160 <= h <= 180:
        return 1 - (h - 160) * (0.95 / 19)
    return 0.0

# トマト領域の熟度を計算
def ripeness_calculator(hsv_image, mask):
    weights = [
        calculate_by_pixel(hsv_image[i, j])
        for i in range(hsv_image.shape[0])
        for j in range(hsv_image.shape[1]) if mask[i, j]
    ]
    return np.median(weights) if weights else 0

# 各トマトの熟度を判定
def judge_ripeness(image, segmentation_results):
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    ripeness_data = []

    for segment in segmentation_results:
        x_min, y_min, x_max, y_max = map(int, segment['bbox'])
        tomato_region = hsv_image[y_min:y_max, x_min:x_max]
        mask = np.ones((y_max - y_min, x_max - x_min), dtype=np.uint8)
        ripeness_value = ripeness_calculator(tomato_region, mask)
        ripeness_data.append({
            'x_center': (x_min + x_max) / 2,
            'ripeness': ripeness_value,
            'bbox': (x_min, y_min, x_max, y_max)
        })

    return ripeness_data

# 画像にセグメント結果を表示（別スレッドで表示を維持）
def display_image_with_segments(image, ripeness_data):
    for idx, data in enumerate(ripeness_data):
        x_min, y_min, x_max, y_max = data['bbox']
        ripeness = data['ripeness']

        # バウンディングボックスを青色で描画
        cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)

        # テキスト表示用の背景を白で描画
        text = f"{idx + 1}: {ripeness:.2f}"
        (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(image, (x_min, y_min - text_height - baseline - 5), 
        (x_min + text_width, y_min - 5), (255, 255, 255), -1)

        # 黒色の文字で熟度情報を表示
        result_image = cv2.putText(image, text, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    cv2.imwrite("/home/ylab/hibikino_toms_ws/src/vision_pkg/vision_pkg/img/ripeness_th/set_ripeness_image.png", result_image)
    cv2.imshow("Tomato Detection", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# 熟度しきい値の保存
def save_ripeness_threshold(threshold_value, filename='/home/toms/hibikino_toms_ws/src/vision_pkg/vision_pkg/modules/ripeness.txt'):
    with open(filename, 'w') as file:
        file.write(str(threshold_value))
    print("熟度判定基準値を保存しました。")

def main():
    # パラメータ設定用のyamlファイル
    yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
    # YAMLファイルの読み込み
    params = load_yaml(yaml_path)
    FILE_PATH = params["vision_params"]["RIPENESS_TH_PATH"]
    WEIGHT_PATH = params["vision_params"]["WEIGHT_PATH"]
    
    # image = capture_image()  # カメラ画像を取得
    image = cv2.imread("/home/ylab/3.jpg")
    cv2.imshow("Image", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    segmentation_results = segment_tomatoes(image, WEIGHT_PATH)  # トマトの検出

    # トマトが検出されなかった場合
    if not segmentation_results:
        print("トマトなし")
        return

    ripeness_data = judge_ripeness(image, segmentation_results)  # 各トマトの熟度を判定

    # x座標の中心値でソートして左から順に並べる
    sorted_ripeness_data = sorted(ripeness_data, key=lambda r: r['x_center'])

    # 画像にセグメント結果を表示（別スレッドで実行）
    display_image_with_segments(image, sorted_ripeness_data)

    # メインスレッドで熟度値の入力を促す
    print("取得したいトマトの番号を入力してください: ")
    index = int(input())  # トマトの番号を入力
    index_a = index - 1
    while 1:
        if 0 <= index_a < len(sorted_ripeness_data):
            selected_ripeness = sorted_ripeness_data[index_a]['ripeness']  # 選択したトマトの熟度値を取得
            print(f"選択された熟度値: {selected_ripeness}")

            # テキストファイルに保存
            save_ripeness_threshold(selected_ripeness, FILE_PATH)  # 熟度しきい値をテキストファイルに保存
            break
        else:
            print("入力された番号が無効です。")
            continue

if __name__ == "__main__":
    main()
