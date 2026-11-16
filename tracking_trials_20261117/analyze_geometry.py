import json,math
from pathlib import Path
import numpy as np, pyrealsense2 as rs
p=Path(__file__).resolve().parent
records=[json.loads(l) for l in (p/'trial_02/observations.jsonl').read_text().splitlines()]
cfg=json.loads((p/'intrinsics.json').read_text());intr=rs.intrinsics();intr.width=640;intr.height=480
for k in ['fx','fy','ppx','ppy','coeffs']:setattr(intr,k,cfg[k])
intr.model=rs.distortion.inverse_brown_conrady
values=[];used=set()
for r in records:
 d=r['data']
 if r['topic']!='/vision/servo_diagnostics' or d.get('reason') not in ('tracking','image_approach') or not d.get('depth_m') or not d.get('actual_pose'):continue
 pose=np.array(d['actual_pose']);cell=tuple(np.round(pose[:2]/.002).astype(int))
 if cell in used:continue
 used.add(cell)
 c=np.array(rs.rs2_deproject_pixel_to_point(intr,d['center'],d['depth_m']))
 values.append((pose,c,d))
def reconstruct(ref):
 pts=[]
 for pose,c,_ in values:
  a=pose[2]-math.radians(ref);R=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
  pts.append(pose[:2]+R@c[[0,2]])
 return np.array(pts)
rows=[]
for ref in np.arange(70,131,.25):
 pts=reconstruct(ref);spread=np.mean(np.sum((pts-np.median(pts,axis=0))**2,axis=1))**.5
 rows.append((spread,float(ref)))
spread,ref=min(rows);pts=reconstruct(100);target=np.median(pts,axis=0)
yaw=math.pi/2;a=yaw-math.radians(100);R=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
ray=np.array(rs.rs2_deproject_pixel_to_point(intr,[369.5,239.5],1.))[[0,2]]
goal=target-R@ray*.15;wrist=goal-.075*np.array([math.cos(yaw),math.sin(yaw)])
# Smallest standoff along the target ray that leaves wrist radius <= .4 m.
D=R@ray;W=target-.075*np.array([math.cos(yaw),math.sin(yaw)])
roots=np.roots([D@D,-2*D@W,W@W-.4**2])
result=dict(distinct_positions=len(values),configured_reference_deg=100,
 configured_world_target_xy_m=target.tolist(),configured_target_spread_m=float(np.mean(np.sum((pts-target)**2,axis=1))**.5),
 motion_fit_reference_deg=ref,motion_fit_spread_m=spread,
 requested_150mm_goal_xy_m=goal.tolist(),requested_wrist_radius_m=float(np.linalg.norm(wrist)),
 maximum_wrist_radius_m=.4,theoretical_standoff_bounds_m=roots.tolist())
print(json.dumps(result,indent=2));(p/'trial_02/geometry.json').write_text(json.dumps(result,indent=2))
