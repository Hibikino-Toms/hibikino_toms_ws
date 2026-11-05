"""base.pt throughput on a recorded screen image; never opens live devices."""
import argparse,json,time
from pathlib import Path
import cv2,numpy as np,torch
from ultralytics import YOLO
parser=argparse.ArgumentParser();parser.add_argument('image');parser.add_argument('--device',default='cpu');parser.add_argument('--roi',default='');args=parser.parse_args()
root=Path(__file__).resolve().parents[3]
image=cv2.imread(args.image)
if image is None:raise ValueError('image missing')
if args.roi:
    x1,y1,x2,y2=map(int,args.roi.split(','));image=image[y1:y2,x1:x2]
if image.size==0:raise ValueError('empty ROI')
torch.set_num_threads(4)
model=YOLO(str(root/'module/weights/base.pt'))
measure=[]
for i in range(25):
    start=time.monotonic()
    result=model.predict(image,imgsz=640,device=args.device,verbose=False)
    if args.device!='cpu':torch.cuda.synchronize()
    elapsed=time.monotonic()-start
    if i>=5:measure.append(elapsed)
detections=[]
for b in result[0].boxes:
    detections.append(dict(class_name=result[0].names[int(b.cls.item())],confidence=float(b.conf.item()),box=b.xyxy[0].cpu().tolist()))
report=dict(image_shape=list(image.shape),roi=args.roi,detections=detections,model='base.pt',image=args.image,device=args.device,samples=len(measure),
            mean_ms=1000*float(np.mean(measure)),max_ms=1000*max(measure),fps=1/float(np.mean(measure)),
            includes_live_camera=False,includes_ros=False,torch=str(torch.__version__))
(root/'src/vision_pkg/validation'/('inference_'+args.device+('_camera_crop' if args.roi else '')+'.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
