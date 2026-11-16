"""Bounded real-hardware trial with rosbag and a final holding stop."""
import argparse,json,math,os,signal,subprocess,time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String,Empty
from std_srvs.srv import Trigger

p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--duration',type=float,default=90);p.add_argument('--home',action='store_true');p.add_argument('--current',action='store_true');p.add_argument('--harvest',action='store_true');args=p.parse_args()
root=Path(__file__).resolve().parent/args.name;root.mkdir(exist_ok=False)
import shutil
for package,name in [("arm_controller_pkg","xy_robot_config.yaml"),("arm_controller_pkg","xy_tracking_params.yaml"),("vision_pkg","realtime_detector.yaml")]:
    shutil.copyfile(Path(__file__).resolve().parents[1]/"src"/package/"config"/name,root/name)
rclpy.init();n=Node('tracking_trial_recorder');stream=(root/'observations.jsonl').open('w');latest={};stopped=False

def rec(topic):
    def cb(msg):
        if isinstance(msg,String):data=json.loads(msg.data)
        else:data=dict(x=msg.pose.position.x,y=msg.pose.position.y,z=msg.pose.position.z,qz=msg.pose.orientation.z,qw=msg.pose.orientation.w)
        latest[topic]=(time.monotonic(),data)
        stream.write(json.dumps(dict(received=time.time(),topic=topic,data=data),allow_nan=False)+'\n')
    return cb
subs=[]
for topic in ['/vision/servo_diagnostics','/arm_xy/diagnostics','/arm_xy/z/state','/arm_xy/harvest/state']:
    subs.append(n.create_subscription(String,topic,rec(topic),20))
for topic in ['/arm_xy/actual','/arm_xy/goal']:
    subs.append(n.create_subscription(PoseStamped,topic,rec(topic),qos_profile_sensor_data))
hold=n.create_publisher(Empty,'/arm_xy/hold',1);home=n.create_client(Trigger,'/arm_xy/z/home')
commands=['ros2','launch','vision_pkg','vision_xy_tracking.launch.py','backend:=can_mixed','startup_mode:='+('current' if args.current else 'configured'),'synthetic_camera:=false','harvest_cycle_enabled:='+str(args.harvest).lower(),'show_window:=true','z_tracking_enabled:=true']
logs=[];procs=[]
for fn,cmd in [('bag.log',['ros2','bag','record','-o',str(root/'bag'),'/vision/servo_diagnostics','/arm_xy/diagnostics','/arm_xy/z/state','/arm_xy/z/pixel_observation','/arm_xy/actual','/arm_xy/goal','/arm_xy/joints','/arm_xy/command_joints','/arm_xy/ready','/arm_xy/error','/arm_xy/harvest/state','/arm_xy/hold','/arm_xy/xy_hold','/rosout']),('console.log',commands)]:
    f=(root/fn).open('w');logs.append(f);procs.append(subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True))
start=time.monotonic();last_report=0;home_sent=False;stable=None;outcome='duration_limit';best=None

def stop(signum,frame):
    global stopped
    stopped=True
signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
try:
    while rclpy.ok() and time.monotonic()-start<args.duration and not stopped:
        rclpy.spin_once(n,timeout_sec=.03);now=time.monotonic()
        v=latest.get('/vision/servo_diagnostics',(0,{}))[1];a=latest.get('/arm_xy/diagnostics',(0,{}))[1];z=latest.get('/arm_xy/z/state',(0,{}))[1]
        if args.home and not home_sent and z.get('phase')=='NEEDS_HOME' and home.service_is_ready():
            home.call_async(Trigger.Request());home_sent=True;print('Requested Z home after backend state confirmation',flush=True)
        h=latest.get('/arm_xy/harvest/state',(0,{}))[1]
        if args.harvest and h.get('state')=='HARVEST_HOLD' and h.get('reason')=='approach_complete' and h.get('hold_ready'):
            outcome='verified_approach_complete_hold_ready';break
        if a.get('reason')=='backend_fault' or z.get('phase')=='FAULT':outcome='fault';break
        if procs[1].poll() is not None:outcome='launch_exited';break
        pixel=v.get('pixel_error');dist=v.get('distance_error_m');pose=a.get('actual_pose');goal=a.get('goal_pose')
        yawerr=abs(a.get('measured_yaw_error',99));gerr=math.hypot(goal[0]-pose[0],goal[1]-pose[1]) if goal and pose else 99
        good=(v.get('reason')=='tracking' and pixel and dist is not None and abs(pixel[0])<=50 and abs(pixel[1])<=24 and abs(dist)<=.01 and yawerr<=.1 and gerr<=.05 and z.get('phase')=='IDLE' and max(map(abs,z.get('joint_velocity_rad_s',[99])))<=.1 and now-latest.get('/vision/servo_diagnostics',(0,{}))[0]<.3)
        if dist is not None and (best is None or abs(dist)<abs(best['distance_error_m'])):
            best=dict(distance_error_m=dist,pixel_error=pixel,measured_yaw_error=yawerr,goal_pose_error_m=gerr,elapsed=now-start)
        if good and not args.harvest:
            if stable is None:stable=now
            if now-stable>=1.:outcome='arrival_within_current_tolerances';break
        else:stable=None
        if now-last_report>=2.:
            print(json.dumps(dict(elapsed=round(now-start,1),vision=v.get('reason'),mode=v.get('approach_mode'),pixels=pixel,depth=v.get('depth_m'),distance_error=dist,arm=a.get('reason'),ik=a.get('ik_reason'),z=z.get('phase'),z_reason=z.get('reason'),xy=pose,yaw_error=yawerr)),flush=True);last_report=now
finally:
    if stopped and outcome=='duration_limit':outcome='interrupted_after_observation'
    hold.publish(Empty())
    for proc in reversed(procs):
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=5)
    stream.close()
    summary=dict(outcome=outcome,elapsed=time.monotonic()-start,best=best,last={k:v[1] for k,v in latest.items()},command=commands)
    (root/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
    n.destroy_node();rclpy.shutdown()
