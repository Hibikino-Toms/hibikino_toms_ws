#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage
import pyrealsense2 as rs
import numpy as np
from std_srvs.srv import SetBool 

class RealSenseSwitcher(Node):
    def __init__(self):
        super().__init__('realsense_switcher_node')

        # === パラメータの宣言 (2台分) ===
        self.declare_parameter('serial_1', '230322272057') # 1台目のS/N
        self.declare_parameter('serial_2', '827312071693') # 2台目のS/N (書き換えてください)
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 15.0)
        self.declare_parameter('jpeg_quality', 70) 

        # パラメータ取得
        self.serials = {
            True: self.get_parameter('serial_1').value,
            False: self.get_parameter('serial_2').value
        }
        self.width = int(self.get_parameter('width').value)
        self.height = int(self.get_parameter('height').value)
        self.fps_int = int(self.get_parameter('fps').value)
        self.q = int(self.get_parameter('jpeg_quality').value)

        # 配信設定
        self.pub = self.create_publisher(CompressedImage, '/camera/image/compressed', qos_profile_sensor_data)
        
        # 状態管理
        self.pipeline = None
        self.timer = None
        self.active_camera_is_1 = True # True: Camera1, False: Camera2
        
        # サービス: Trueが送られたらCamera1、FalseならCamera2へ切り替え
        # self.srv = self.create_service(SetBool, 'switch_camera', self.switch_service_callback)
        self.srv_onoff = self.create_service(SetBool, 'set_streaming', self.onoff_callback)
        self.srv_select = self.create_service(SetBool, 'switch_camera', self.select_callback)

        self.current_id = True # True:カメラ1, False:カメラ2
        self.is_running = True # 今、実際にカメラが動いているか


        # 初期起動
        self.get_logger().info('初期カメラ(Camera 1)を開始します...')
        self.start_camera(self.serials[self.active_camera_is_1])

    def onoff_callback(self, request, response):
        # WebUIのcallDetectから呼ばれる(ON/OFF)
        if request.data: 
            self.start_camera(self.serials[self.current_id])
            self.is_running = True
        else:
            self.stop_camera()
            self.is_running = False
        response.success = True
        return response
    
    def select_callback(self, request, response):
    # 新しく作るボタンから呼ばれる(1ch / 2ch の切り替え)
        self.get_logger().info('切り替えを開始します')
        self.current_id = request.data # 選択を保存
        if self.is_running:
            # 今動いているなら、一旦止めて新しい方で再起動
            self.stop_camera()
            self.start_camera(self.serials[self.current_id])
        response.success = True
        return response
    
    def start_camera(self, serial):
        """指定したシリアル番号でカメラを開始"""
        try:
            self.pipeline = rs.pipeline()
            config = rs.config()
            config.enable_device(serial)
            config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps_int)
            
            self.pipeline.start(config)
            self.get_logger().info(f'カメラ開始成功: S/N {serial}')

            period = max(1.0/max(self.fps_int, 0.1), 0.001)
            self.timer = self.create_timer(period, self.loop)
            return True
        except Exception as e:
            self.get_logger().error(f'カメラ(S/N {serial})の開始に失敗: {e}')
            self.pipeline = None
            return False

    def stop_camera(self):
        """現在のパイプラインを安全に停止"""
        if self.timer:
            self.timer.cancel()
            self.timer.destroy()
            self.timer = None
        if self.pipeline:
            try:
                self.pipeline.stop()
            except:
                pass
            self.pipeline = None



    def loop(self):
        if self.pipeline is None:
            return
        try:
            frames = self.pipeline.wait_for_frames(timeout_ms=1000)
            color_frame = frames.get_color_frame()
            if not color_frame:
                return

            frame = np.asanyarray(color_frame.get_data())
            ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.q])
            
            if ok:
                msg = CompressedImage()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.format = 'jpeg'
                msg.data = buf.tobytes()
                self.pub.publish(msg)
        except Exception as e:
            self.get_logger().debug(f'Loop Error: {e}')

    def destroy_node(self):
        self.stop_camera()
        super().destroy_node()

def main():
    rclpy.init()
    node = RealSenseSwitcher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()