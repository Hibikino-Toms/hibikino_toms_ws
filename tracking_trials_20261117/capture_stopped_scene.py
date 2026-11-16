"""Camera-only check after the arm/vision launch has stopped. No motor commands."""
import json,time,cv2,rclpy,numpy as np
from pathlib import Path
from vision_pkg.vison_sevice_realtime import RealtimeTomatoDetector
root=Path(__file__).resolve().parent;rclpy.init(args=['--ros-args','-p','show_window:=false']);n=RealtimeTomatoDetector();records=[]
try:
 deadline=time.monotonic()+18
 while len(records)<8 and time.monotonic()<deadline:
  frames=n.pipeline.poll_for_frames()
  if not frames:time.sleep(.01);continue
  aligned=n.align.process(frames);cf,df=aligned.get_color_frame(),aligned.get_depth_frame()
  if not cf:continue
  image=np.asanyarray(cf.get_data()).copy();depth=np.asanyarray(df.get_data()) if df else None
  result=n.model.predict(source=image,imgsz=n.image_size,conf=n.confidence,iou=n.iou,device=n.device,verbose=False)[0]
  ds=n._tomato_detections(result)
  if not ds:continue
  d=min(ds,key=lambda d:np.linalg.norm(np.asarray(d['center'])-n.servo.pixel));u,v=d['center'];z=n._depth_at(depth,u,v,d['mask']) if depth is not None else None
  record=dict(center=[u,v],target_pixel=n.servo.pixel.tolist(),pixel_error=(np.array([u,v])-n.servo.pixel).tolist(),depth_m=z,distance_error_m=None if z is None else z-n.servo.distance,confidence=float(d['confidence']))
  records.append(record);pic=result.plot();cv2.drawMarker(pic,tuple(np.rint(n.servo.pixel).astype(int)),(255,255,0),cv2.MARKER_CROSS,24,2);cv2.imwrite(str(root/'final_stopped_scene.jpg'),pic)
 (root/'final_stopped_scene.json').write_text(json.dumps(records,indent=2));print(json.dumps(records,indent=2))
finally:n.destroy_node();rclpy.shutdown()
