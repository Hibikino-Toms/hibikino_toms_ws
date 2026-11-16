import json,math
from pathlib import Path
import numpy as np,yaml
from vision_pkg.modules.image_servo import ImageServo
cfg=yaml.safe_load(Path('src/vision_pkg/config/realtime_detector.yaml').read_text())['target']
s=ImageServo(cfg,640,480);s.track_id=1
pixel=s.pixel.copy();ray=np.array([.1,0.,1.]);pose=np.array([.08,.3,math.pi/2]);rows=[]
for i,depth in enumerate([.349,.356,.358]):
    goal,d=s.update_approach(pixel,ray,ray,pose,100+i/15,depth)
    rows.append(dict(depth=depth,reason=d['reason'],mode=d['approach_mode'],has_goal=goal is not None))
assert rows[-1]['has_goal'] and s.depth_control_ready
assert np.linalg.norm(goal[:2]-pose[:2])<=.015
_,d=s.update_approach(pixel,ray,ray,pose,100.3,None)
assert d['reason']=='near_depth_lost_hold'
s.reject_approach_observation()
_,d=s.update_approach(pixel,ray,ray,pose,100.4,.6)
assert d['reason']=='confirming_near_depth' and not s.depth_control_ready
far=ImageServo(cfg,640,480);far.track_id=1
for i in range(6):g,d=far.update_approach(pixel,ray,ray,pose,200+i/15,None)
assert g is not None and d['reason']=='image_approach' and np.linalg.norm(g[:2]-pose[:2])>0
far.update_approach(pixel,ray,ray,pose,220,None)
assert far.approach_mode=='LIMIT_HOLD'
print(json.dumps(rows,indent=2));Path('tracking_trials_20261117/image_handover_checks.json').write_text(json.dumps(dict(boundary_sequence=rows,near_loss_hold=True,far_depth_optional=True,time_limit_hold=True),indent=2))
