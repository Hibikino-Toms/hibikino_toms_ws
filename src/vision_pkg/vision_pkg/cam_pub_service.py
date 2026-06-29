#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage
import pyrealsense2 as rs  # RealSenseライブラリをインポート
import numpy as np
# qos_profile_sensor_dataはQuolity of Serivice(QoS)プロファイルを示している。QoSプロファイルは、メッセージ通信の
# 品質や信頼性に関する設定を提供する. qos_profile_sensor_dataは、センサーデータ伝送のための一般的なQoS設定をもつ、
# ROS2で予め定義されているプロファイルの一つ

from std_srvs.srv import SetBool  # サービス通信用

class RealSenseControlledDefaultOn(Node): # クラス名を変更
    def __init__(self):
        super().__init__('realsense_controlled_pub') # ノード名はそのまま

        # === パラメータの宣言 ===
        self.declare_parameter('serial_number', '230322272057')
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 15.0)
        self.declare_parameter('jpeg_quality', 70) 

        # === パラメータの取得 ===
        self.serial = self.get_parameter('serial_number').value
        self.width  = int(self.get_parameter('width').value)
        self.height = int(self.get_parameter('height').value)
        self.fps_int = int(self.get_parameter('fps').value)             # RealSEnesの設定は整数型を要求
        self.fps    = float(self.get_parameter('fps').value)            # タイマー用
        self.q      = int(self.get_parameter('jpeg_quality').value)

        self.pub = self.create_publisher(CompressedImage,
                                        '/camera/image/compressed',
                                        qos_profile_sensor_data)
        
        # === リソースの初期化 ===
        self.pipeline = None
        self.timer = None
        self.is_streaming = False
        
        # === サービスサーバーの生成 ===
        self.srv = self.create_service(SetBool, 'set_streaming', self.service_callback)
        self.get_logger().info('RealSenseノード起動。/set_streaming サービス (true/false) で制御してください。')

        # === <<< 追加: デフォルトで起動処理を呼び出す ===
        self.get_logger().info('デフォルト設定に基づき、ストリーミングを開始します...')
        self.start_camera() # ノード起動時にカメラ起動を試みる
        # (もしここで失敗してもノードは起動し続けます。サービスで再試行可能です)

    # === RealSense起動処理 (変更なし) ===
    def start_camera(self):
        """RealSenseパイプラインを開始し、タイマーを起動する"""
        if self.is_streaming:
            self.get_logger().warn('すでにストリーミング中です。')
            return False

        try:
            self.pipeline = rs.pipeline()
            config = rs.config()

            if self.serial:
                config.enable_device(self.serial)
                self.get_logger().info(f'シリアル番号 {self.serial} のカメラを検索します...')
            else:
                self.get_logger().info('シリアル番号が指定されていないため、最初に見つかったRealSenseを使います')

            # ストリームの設定
            # RealSenseに「カラー画像」を「指定した解像度・FPS」で要求する
            config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps_int)
            
            # ストリーミング開始
            # 設定(config)を使って、パイプラインを開始（カメラ起動）
            profile = self.pipeline.start(config)
            
            # 実際に接続されたデバイスのシリアル番号を確認（デバッグ用）
            device = profile.get_device()
            actual_serial = device.get_info(rs.camera_info.serial_number)
            self.get_logger().info(f'接続成功: S/N {actual_serial} @ {self.width}x{self.height}, q={self.q}')

            period = max(1.0 / max(self.fps, 0.1), 0.001) 
            self.timer = self.create_timer(period, self.loop)
            self.is_streaming = True
            return True

        except Exception as e:
            self.get_logger().error(f'RealSenseカメラの開始に失敗: {e}')
            if self.pipeline:
                try:
                    self.pipeline.stop()
                except Exception:
                    pass # 失敗時のstopエラーは無視
            self.pipeline = None
            self.is_streaming = False
            return False

    # === RealSense停止処理 (変更なし) ===
    def stop_camera(self):
        """タイマーを停止し、RealSenseパイプラインを停止する"""
        if not self.is_streaming:
            self.get_logger().warn('すでに停止しています。')
            return True

        try:
            if self.timer:
                self.timer.cancel()
                self.timer.destroy()
                self.timer = None
            
            if self.pipeline:
                self.pipeline.stop()
                self.pipeline = None
            
            self.is_streaming = False
            self.get_logger().info('RealSenseパイプラインを停止しました。')
            return True
        except Exception as e:
            self.get_logger().error(f'RealSense停止中にエラー: {e}')
            self.pipeline = None
            self.is_streaming = False
            return False

    # === サービスコールバック (変更なし) ===
    def service_callback(self, request, response):
        if request.data:  # 起動リクエスト
            if self.is_streaming:
                response.success = False
                response.message = 'すでに起動しています'
            else:
                self.get_logger().info('RealSense起動リクエストを受信...')
                success = self.start_camera()
                response.success = success
                response.message = 'RealSenseを起動しました' if success else 'RealSenseの起動に失敗しました'
        
        else:  # 停止リクエスト
            if not self.is_streaming:
                response.success = False
                response.message = 'すでに停止しています'
            else:
                self.get_logger().info('RealSense停止リクエストを受信...')
                success = self.stop_camera()
                response.success = success
                response.message = 'RealSenseを停止しました' if success else 'RealSenseの停止に失敗しました'
                
        return response

    # === loop関数 (変更なし) ===
    def loop(self):
        if not self.is_streaming or self.pipeline is None:
            return
            
        try:
            # RealSenseから新しいフレームが来るまで待つ
            frames = self.pipeline.wait_for_frames()
            if not frames:
                self.get_logger().warn('フレームセットが取得できませんでした')
                return
            
            # フレームセットから「カラーフレーム」だけを取り出す
            color_frame = frames.get_color_frame()
            if not color_frame:
                self.get_logger().warn('カラーフレームが取得できませんでした')
                return
            
            # データ形式の変換
            # openCVが扱えるNumpy配列に変換する
            frame = np.asanyarray(color_frame.get_data())

            # jpgにエンコードする
            ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.q])
            if not ok:
                self.get_logger().warn('imencode failed')
                return

            # ROS 2メッセージの作成と配信
            msg = CompressedImage()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.format = 'jpeg'
            msg.data = buf.tobytes()
            self.pub.publish(msg)

        except Exception as e:
            self.get_logger().warn(f'ループ処理中にエラー: {e}')

    # === destroy_node (変更なし) ===
    def destroy_node(self):
        self.stop_camera()
        super().destroy_node()

# === main関数 (変更なし) ===
def main():
    rclpy.init() 
    node = RealSenseControlledDefaultOn() # クラス名を変更

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()