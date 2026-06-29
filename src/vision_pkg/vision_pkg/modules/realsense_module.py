import os
#python tools
import pyrealsense2 as rs
import numpy as np
import cv2
"""
RealSenseモジュール

2024/9/22 時点
去年のコードのまま

@author: yoshida keisuke, 吉永

"""
class Realsense_Module():
    def __init__(self, params, device = None) :
        self.WIDTH = params["WIDTH"]
        self.HEIGHT = params["HEIGHT"]
        self.FPS = params["FPS"]
        self.setup(device)

    def setup(self,device=None):
        self.conf = rs.config()
        if device is not None:
            self.conf.enable_device(device)
        self.conf.enable_stream(rs.stream.color, self.WIDTH, self.HEIGHT, rs.format.bgr8, self.FPS)
        self.conf.enable_stream(rs.stream.depth, self.WIDTH, self.HEIGHT, rs.format.z16, self.FPS)
        #start_stream
        self.pipe = rs.pipeline()
        self.profile = self.pipe.start(self.conf)
        #Align_objetc
        self.align_to = rs.stream.color
        self.align = rs.align(self.align_to)
        #get_camera_param
        self.depth_intrinsics = rs.video_stream_profile(self.profile.get_stream(rs.stream.depth)).get_intrinsics()
        self.color_intrinsics = rs.video_stream_profile(self.profile.get_stream(rs.stream.color)).get_intrinsics()

    def get_cam_param(self):
        fx, fy = self.color_intrinsics.fx, self.color_intrinsics.fy
        cx, cy = self.color_intrinsics.ppx, self.color_intrinsics.ppy
        return fx,fy,cx,cy,self.WIDTH, self.HEIGHT

    def get_image(self, show) :
        try :
            #waiting for a frame
            for i in range(30):
                frames = self.pipe.wait_for_frames()
            #get_frame_data
            aligned_frames = self.align.process(frames)
            color_frame = aligned_frames.get_color_frame()
            depth_frame = aligned_frames.get_depth_frame()
            depth_frame = self.depth_filter(depth_frame)
            if not depth_frame or not color_frame:
                return
            #conversion unit16⇨numpy
            color_image = np.asanyarray(color_frame.get_data())
            depth_image = np.asanyarray(depth_frame.get_data())
            if show:
                cv2.imshow('color_image',color_image)   
                cv2.waitKey(1000)
                cv2.destroyAllWindows()
            return color_image,depth_image,depth_frame
        except Exception as e :
            print(e)
            color_image=None
            depth_image=None
            depth_frame=None
            return color_image,depth_image,depth_frame

    def m2mm(self,point):
        x = int(round(point[0]*1000))
        y = int(round(point[1]*1000))
        z = int(round(point[2]*1000))
        return np.array([x,y,z])

    def imgpoint_to_3dpoint(self, depth_frame, tomatoes, mode, tomato_dict):
        result_pos = np.empty((0, 4))
        if mode == 0: # detect_check
            if len(tomatoes) != 0:
                for tomato in tomatoes:
                    u = tomato[0]
                    v = tomato[1]
                    
                    # 深度推定
                    i_d = depth_frame.get_distance(int(u), int(v))
                    
                    # カメラ座標の x, y, z 取得
                    point = rs.rs2_deproject_pixel_to_point(self.color_intrinsics, [u, v], i_d)
                    result_pos = np.vstack((result_pos, np.append(self.m2mm(point), 0)))
            else:
                result_pos = None
        
        elif mode == 1: # harvest
            idx = 0
            if len(tomatoes) != 0:
                for tomato in tomatoes:
                    u = tomato[0]
                    v = tomato[1]
                    
                    # 深度推定
                    i_d = depth_frame.get_distance(int(u), int(v))
                    
                    # カメラ座標の x, y, z 取得
                    point = rs.rs2_deproject_pixel_to_point(self.color_intrinsics, [u, v], i_d)
                    result_pos = np.vstack((result_pos, np.append(self.m2mm(point), tomato[2])))
                    
                for tom_data in tomato_dict:
                    if tom_data["is_ripe"]:
                        tom_data["camera_coords"] = [result_pos[idx][0], result_pos[idx][1], result_pos[idx][2]]
                        idx += 1
            else:
                result_pos = None
        print(f"result_pos: {result_pos}")

        return result_pos, tomato_dict

    def depth_filter(self,depth_frame):
        #TODO recursive median filterを入れる
        # decimarion_filter param
        decimate = rs.decimation_filter()
        decimate.set_option(rs.option.filter_magnitude, 1)
        # spatial_filter param
        spatial = rs.spatial_filter()
        spatial.set_option(rs.option.filter_magnitude, 1)
        spatial.set_option(rs.option.filter_smooth_alpha, 0.25)
        spatial.set_option(rs.option.filter_smooth_delta, 50)
        # hole_filling_filter param
        hole_filling = rs.hole_filling_filter()
        # disparity
        depth_to_disparity = rs.disparity_transform(True)
        disparity_to_depth = rs.disparity_transform(False)
        # filter
        filter_frame = decimate.process(depth_frame)
        filter_frame = depth_to_disparity.process(filter_frame)
        filter_frame = spatial.process(filter_frame)
        filter_frame = disparity_to_depth.process(filter_frame)
        filter_frame = hole_filling.process(filter_frame)
        result_frame = filter_frame.as_depth_frame()
        return result_frame



if __name__ == "__main__":
    import sys
    from ultralytics import YOLO
    
    sys.path.append("/home/toms/hibikino_toms_ws/src/vision_pkg/vision_pkg")
    from modules.harvest_order import Harvest_Order
    from modules.ripeness_judge import Ripeness_Judge
    ripe = Ripeness_Judge(80)
    harvest_order = Harvest_Order()
    realsense = Realsense_Module()
    
    # 画像取得
    color_img,depth_img,depth_frame = realsense.get_image()
    color_img = cv2.imread("/home/toms/test_ws/src/vision_pkg/image/image-2.png")
    image = cv2.resize(color_img, (640, 480))
    
    model = YOLO("/home/toms/test_ws/module/weights/best.pt")
    yolo_results = model.predict(image, conf= 0.8, iou= 0.4)
    
    # 推論結果のうち、各クラス別に結果の情報を分割
    result_tomato = [r for r in yolo_results if any(r.names[int(label)] == "tomato" for label in r.boxes.cls.cpu().numpy())]
    result_main_stem = [r for r in yolo_results if any(r.names[int(label)] == "main_stem" for label in r.boxes.cls.cpu().numpy())]
    result_peduncle = [r for r in yolo_results if any(r.names[int(label)] == "peduncLe" for label in r.boxes.cls.cpu().numpy())]

    center_of_ripe_tomatoes = ripe.judge_ripeness(image, result_tomato)
    
    # center_of_ripe_tomatoes = [[320, 240], [300, 200]]
    print(f"center_of_ripe_tomatoes : {center_of_ripe_tomatoes}")
    
    # トマトの座標を画像座標系からカメラ座標系に変換
    tomato_3d_posi = realsense.imgpoint_to_3dpoint(depth_frame, center_of_ripe_tomatoes, mode=1) # mode：0…トマトがロボットの前にあるかどうかの確認、1…収穫動作
    print(f"カメラ座標に変換 :  {tomato_3d_posi}")
    
    # アーム座標に変換された、[トマトの3次元座標，手先進入角度]×熟したトマトの個数 の配列が返ってくる
    target_coordinates = harvest_order.order_decision(result_tomato, result_main_stem, result_peduncle, depth_img, tomato_3d_posi)
    print(f"アーム座標に変換 :  {target_coordinates}")

    file_path = "/home/toms/hibikino_toms_ws/src/vision_pkg/vision_pkg/modules/target_coordinates.npy"
    np.save(file_path, target_coordinates)