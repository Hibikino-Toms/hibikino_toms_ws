import pyrealsense2 as rs
import numpy as np
import cv2
import sys


# realsense.setup("814412070380")

# パイプラインの設定と初期化
pipeline = rs.pipeline()
config = rs.config()

# ストリーミングの設定（深度とカラー）
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# ストリーミングの開始
pipeline.start(config)

try:
    while True:
        # フレームの取得
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()

        if not depth_frame or not color_frame:
            continue

        # 深度データとカラーデータをNumPy配列に変換
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        print(depth_image[320,240])

        # 60cm以上のデータを黒く塗りつぶす
        #distance_threshold = 500  # 600mm = 60cm
        #black_mask = depth_image > distance_threshold
        #color_image[black_mask] = [0, 0, 0]

        # 結果を表示
        cv2.imshow('Filtered Depth Image', color_image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    # ストリーミングの停止
    pipeline.stop()
    cv2.destroyAllWindows()
