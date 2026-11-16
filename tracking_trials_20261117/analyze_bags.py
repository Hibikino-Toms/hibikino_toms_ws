"""Read authoritative rosbag CDR recordings; summarize final physical trials."""
import json,math,collections
from pathlib import Path
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
root=Path(__file__).resolve().parent

def load(name):
 reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(root/name/'bag'),storage_id='sqlite3'),rosbag2_py.ConverterOptions('',''))
 types={t.name:get_message(t.type) for t in reader.get_all_topics_and_types()};rows=collections.defaultdict(list)
 while reader.has_next():
  topic,data,ns=reader.read_next();msg=deserialize_message(data,types[topic])
  if hasattr(msg,'data') and isinstance(msg.data,str):
   try:value=json.loads(msg.data)
   except (ValueError,TypeError):continue
  elif hasattr(msg,'data'):value=msg.data if isinstance(msg.data,(bool,int,float)) else list(msg.data)
  else:continue
  rows[topic].append((ns/1e9,value))
 return rows

def stat(values):
 a=np.asarray(values,float)
 return None if not len(a) else dict(mean=float(a.mean()),min=float(a.min()),max=float(a.max()),p95=float(np.percentile(a,95)))
reports={}
for name in ['trial_01','trial_02','trial_03','trial_04_arrival_gate','trial_05_arrival_fixed','trial_06_full_arrival']:
 rows=load(name);v=rows['/vision/servo_diagnostics'];a=rows['/arm_xy/diagnostics'];h=rows['/arm_xy/harvest/state'];z=rows['/arm_xy/z/state']
 arrival=[(t,d) for t,d in h if d['state']=='HARVEST_HOLD' and d['reason']=='approach_complete']
 hold=[(t,d) for t,d in arrival if d['hold_ready']]
 end=arrival[0][0] if arrival else (v[-1][0] if v else 0)
 window=[(t,d) for t,d in v if end-5<=t<=end and d.get('reason')=='tracking']
 final=[(t,d) for t,d in v if end-1<=t<=end and d.get('reason')=='tracking']
 armwindow=[(t,d) for t,d in a if end-5<=t<=end and d.get('reason')=='tracking']
 timestamps=[d['capture_stamp'] for t,d in window if d.get('capture_stamp')]
 checks=[(t,d['arrival_check']) for t,d in a if 'arrival_check' in d and d['arrival_check'].get('stable_sec',0)>.4]
 moving=[(t,d) for t,d in z if d['phase'] in ('MOVING_Z','STOPPING_Z')]
 cmds=rows['/arm_xy/command_joints'];active=[]
 # Compare the joint command used during each Z-motion interval with its predecessor.
 for t,d in moving:
  preceding=[c for ct,c in cmds if ct<=t]
  if preceding:active.append(preceding[-1])
 report=dict(topic_counts={k:len(v) for k,v in rows.items()},
  vision_reasons=dict(collections.Counter(d['reason'] for _,d in v)),
  arm_reasons=dict(collections.Counter(d['reason'] for _,d in a)),
  approach_complete=bool(arrival),hold_ready=bool(hold),
  arrival_stamp=arrival[0][0] if arrival else None,
  final_depth_m=stat([d['depth_m'] for _,d in final if d.get('depth_m') is not None]),
  final_horizontal_error_px=stat([d['pixel_error'][0] for _,d in final]),
  final_vertical_error_px=stat([d['pixel_error'][1] for _,d in final]),
  final_distance_error_m=stat([d['distance_error_m'] for _,d in final if d.get('distance_error_m') is not None]),
  measured_yaw_error_rad=stat([abs(d['measured_yaw_error']) for _,d in armwindow if d.get('measured_yaw_error') is not None]),
  commanded_yaw_error_rad=stat([abs(d['commanded_yaw_error']) for _,d in armwindow if d.get('commanded_yaw_error') is not None]),
  control_period_sec=stat([d['period_sec'] for _,d in armwindow if d.get('period_sec',0)>0]),
  compute_sec=stat([d['compute_sec'] for _,d in armwindow if 'compute_sec' in d]),
  compute_over_100ms=sum(d.get('compute_sec',0)>.1 for _,d in armwindow),
  period_over_100ms=sum(d.get('period_sec',0)>.1 for _,d in armwindow),
  goal_age_sec=stat([d['goal_age_sec'] for _,d in armwindow if d.get('goal_age_sec') is not None]),
  vision_processing_sec=stat([d['processing_sec'] for _,d in window]),
  vision_fps=(len(timestamps)-1)/(max(timestamps)-min(timestamps)) if len(timestamps)>1 else None,
  last_arrival_check=checks[-1][1] if checks else None,
  z_position_range_m=[min(d['position_m'] for _,d in z if d['position_m'] is not None),max(d['position_m'] for _,d in z if d['position_m'] is not None)] if z else None,
  z_moving_message_count=len(moving),
  final_harvest_state=h[-1][1] if h else None)
 reports[name]=report
 (root/name/'bag_analysis.json').write_text(json.dumps(report,indent=2))
 if name=='trial_06_full_arrival':
  print(json.dumps(report,indent=2))
  import matplotlib
  matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  good=[(t,d) for t,d in v if d.get('pixel_error') and d.get('capture_stamp')]
  t0=good[0][0];times=[t-t0 for t,d in good]
  fig,axs=plt.subplots(3,1,figsize=(9,8),sharex=True)
  axs[0].plot(times,[d.get('depth_m',float('nan')) for t,d in good]);axs[0].axhline(.15,color='r',ls='--');axs[0].axhspan(.14,.16,color='g',alpha=.15);axs[0].set_ylabel('Depth [m]')
  axs[1].plot(times,[d['pixel_error'][0] for t,d in good],label='horizontal');axs[1].plot(times,[d['pixel_error'][1] for t,d in good],label='vertical');axs[1].axhline(0,color='k',lw=.5);axs[1].legend();axs[1].set_ylabel('Pixel error [px]')
  axs[2].plot([t-t0 for t,d in a if d.get('actual_pose')],[d['actual_pose'][1] for t,d in a if d.get('actual_pose')]);axs[2].set_ylabel('FK Y [m]');axs[2].set_xlabel('Time from first image [s]')
  if arrival:
   for ax in axs:ax.axvline(arrival[0][0]-t0,color='orange',ls='--')
  fig.suptitle('Real hardware trial 06: measured approach and arrival hold');fig.tight_layout();fig.savefig(root/'trial_06_full_arrival.png',dpi=150);plt.close(fig)
(root/'bag_analysis_all.json').write_text(json.dumps(reports,indent=2))
