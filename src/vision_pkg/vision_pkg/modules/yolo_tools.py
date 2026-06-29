import os
import sys
import cv2
import numpy as np

import torch
import torch.backends.cudnn as cudnn

#yolo_lib
from ultralytics import YOLO
sys.path.append("/home/toms/hibikino_toms_ws/module/yolov5")
from models.common import DetectMultiBackend
from utils.general import (check_img_size, check_imshow, check_requirements,non_max_suppression, print_args, scale_coords)
from utils.plots import Annotator, colors
from utils.torch_utils import select_device
from utils.augmentations import letterbox

class Result:
    def __init__(self, xyxy=(0.0, 0.0, 0.0, 0.0), name='', conf=0.0):
        self.u1 = float(xyxy[0])
        self.v1 = float(xyxy[1])
        self.u2 = float(xyxy[2])
        self.v2 = float(xyxy[3])
        self.name = name
        self.conf = float(conf)

# TODO: v8に変更する
# 今回の認識器に必要な処理を、調べながら取捨選択する
class Yolov5():
    def __init__(self,device,weights,data,conf_thres,iou_thres,line_thickness,view_img,hide_labels,hide_conf):

        self.conf_thres =  conf_thres         #Confidence threshold
        self.iou_thres =  iou_thres           # NMS IOU threshold
        self.line_thickness = line_thickness  # bounding box thickness (pixels)
        self.view_img = view_img             # show results
        self.hide_labels = hide_labels        # hide labels
        self.hide_conf = hide_conf            # hide confidences


        """
        yolov5_setup
        """
        check_requirements(exclude=('tensorboard', 'thop'))

        #yolo model param
        dnn=False # use OpenCV DNN for ONNX inference     
        self.device = select_device(device)
        self.model = DetectMultiBackend(weights, device=self.device, dnn=dnn, data=data)
        self.stride = self.model.stride
        self.names = self.model.names
        self.pt = self.model.pt
        self.jit = self.model.jit
        self.onnx = self.model.onnx
        self.engine = self.model.engine
        #self.declare_parameter('imgsz',640) 
        #imgsz =  self.get_parameter('imgsz').get_parameter_value().integer_value # image size
        imgsz = (640, 640)
        self.imgsz = check_img_size(imgsz, s=self.stride)  # check image size


        #etc... 
        self.classes = None       # filter by class: --class 0, or --class 0 2 3
        self.augment = False      # augmented inference
        self.visualize = False    # visualize features
        self.agnostic_nms = False # class-agnostic NMS
        self.max_det = 1000       # maximum detections per image
        self.half = False         # use FP16 half-precision inference

        # Half
        # FP16 supported on limited backends with CUDA
        self.half &= ((self.pt or self.jit or self.onnx or self.engine)and self.device.type != 'cpu')
        if self.pt or self.jit:
            self.model.model.half() if self.half else self.model.model.float()

        # Dataloader
        self.view_img = True  # check_imshow()
        # set True to speed up constant image size inference
        cudnn.benchmark = True
        self.model.warmup(imgsz=(1, 3, *imgsz))  # warmup

    @torch.no_grad()
    def detect(self, img0):
        img = letterbox(img0, self.imgsz, stride=self.stride)[0]
        img = img.transpose((2, 0, 1))[::-1]  # HWC to CHW, BGR to RGB
        img = np.ascontiguousarray(img)
        img = torch.from_numpy(img).to(self.device)
        img = img.half() if self.half else img.float()  # uint8 to fp16/32
        img /= 255  # 0 - 255 to 0.0 - 1.0
        img = img[None]  # expand for batch dim
        #estimate
        pred = self.model(img, augment=self.augment, visualize=self.visualize)
        #NMS(bounding_boxの重なりを除去)
        pred = non_max_suppression(pred, self.conf_thres, self.iou_thres, self.classes,self.agnostic_nms, max_det=self.max_det)
        det = pred[0]
        s = '%gx%g ' % img.shape[2:]  # print string
        torch.tensor(img0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
        annotator = Annotator(img0, line_width=self.line_thickness, example=str(self.names))
        if len(det):
            # Rescale boxes from img_size to im0 size
            det[:, :4] = scale_coords(
                img.shape[2:], det[:, :4], img0.shape).round()
            # Print results
            for c in det[:, -1].unique():
                n = (det[:, -1] == c).sum()  # detections per class
                # add to string
                s += f"{n} {self.names[int(c)]}{'s' * (n > 1)}, "
            result = []
            for *xyxy, conf, cls in reversed(det):
                result.append(Result(xyxy, self.names[int(cls)], conf)) #結果追加
                if self.view_img:  # Add bbox to image
                    c = int(cls)  # integer class
                    label = None if self.hide_labels else (
                        self.names[c] if self.hide_conf else (
                            f'{self.names[c]} {conf:.2f}'))
                    annotator.box_label(xyxy, label, color=colors(c, True))

            return img0, result
        else:
            return img0, None

    def infor(self,image_raw):
        outputs,result = self.detect(image_raw)  
        cv2.imshow('yolo_result',outputs)   
        cv2.waitKey(1)  
        return result