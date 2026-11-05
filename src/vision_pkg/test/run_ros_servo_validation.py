#!/usr/bin/env python3
"""Explicitly SIM ONLY, isolated DDS domain. Run after build and source install."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import numpy as np
os.environ['ROS_LOG_DIR']='/tmp/tomato_servo_ros_logs'
os.environ['ROS_DOMAIN_ID']='172'
os.environ['ROS_LOCALHOST_ONLY']='1'
import rclpy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from std_srvs.srv import Trigger

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'src/vision_pkg/validation'
OUT.mkdir(exist_ok=True)
processes=[];streams=[]

def start(args,name):
    stream=open(OUT/(name+'.log'),'w');streams.append(stream)
    proc=subprocess.Popen(args,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    processes.append(proc)
    return proc

def stop(proc):
    if proc.poll() is None:
        os.killpg(proc.pid,signal.SIGINT)
        try:proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=3)

rclpy.init();node=rclpy.create_node('servo_validation_observer')
vision=[];arm=[]
node.create_subscription(String,'/vision/servo_diagnostics',lambda m:vision.append(json.loads(m.data)),1000)
node.create_subscription(String,'/arm_xy/diagnostics',lambda m:arm.append(json.loads(m.data)),1000)
goalpub=node.create_publisher(PoseStamped,'/arm_xy/goal',1)

def spin(seconds):
    until=time.monotonic()+seconds
    while time.monotonic()<until:rclpy.spin_once(node,timeout_sec=.05)

def send_goal(x,y,yaw):
    msg=PoseStamped();msg.header.frame_id='arm_base';msg.header.stamp=node.get_clock().now().to_msg()
    msg.pose.position.x=x;msg.pose.position.y=y
    msg.pose.orientation.z=float(np.sin(yaw/2));msg.pose.orientation.w=float(np.cos(yaw/2))
    goalpub.publish(msg)

try:
    tracker=start(['ros2','run','arm_controller_pkg','arm_xy_tracker','--ros-args',
        '-p','backend:=sim','-p','config_file:='+str(ROOT/'src/arm_controller_pkg/config/xy_robot_config.yaml')], 'ros_tracker')
    detector=start(['ros2','run','vision_pkg','vision_service_realtime','--ros-args',
        '-p','synthetic_camera:=true','-p','show_window:=false'], 'ros_vision')
    spin(78.)
    assert tracker.poll() is None and detector.poll() is None,'node exited'
    tracking=[d for d in vision if d.get('reason')=='tracking']
    commands=[d for d in arm if d.get('reason')=='tracking']
    assert len(tracking)>500 and len(commands)>400,(len(tracking),len(commands))
    assert abs(tracking[-1]['pixel_error'][0])<5., tracking[-1]
    assert max(abs(d['commanded_yaw_error']) for d in commands)<1e-6
    assert abs(tracking[-1]['distance_error_m'])<.005
    stop(detector);spin(1.)
    assert arm[-1]['reason']=='goal_timeout',arm[-1]
    actual=arm[-1]['actual_pose'];yaw=float(np.radians(100))
    # Three replacements before the next control callback. Only final slot matters.
    for dx in [.002,.001,.0005]:send_goal(actual[0]+dx,actual[1],yaw)
    spin(.3)
    assert np.isclose(arm[-1]['goal_pose'][0],actual[0]+.0005)
    latest_ok=True
    send_goal(.9,.3,yaw);spin(.25)
    assert arm[-1]['reason']=='ik_hold',arm[-1]
    ik_hold=True
    service=node.create_service(Trigger,'/arm_service',lambda req,res:res)
    spin(1.)
    assert arm[-1]['reason']=='control_conflict',arm[-1]
    node.destroy_service(service)
    periods=np.array([d['period_sec'] for d in commands if d['period_sec'] is not None])
    stamps=np.array([d['stamp'] for d in tracking])
    summary=dict(vision_synthetic_fps=float(1/np.mean(np.diff(stamps))),control_hz=float(1/np.mean(periods)),
        vision_processing_avg_ms=float(1000*np.mean([d['processing_sec'] for d in tracking])),
        control_processing_avg_ms=float(1000*np.mean([d['compute_sec'] for d in commands])),
        control_processing_max_ms=float(1000*max(d['compute_sec'] for d in commands)),
        period_max_ms=float(1000*max(periods)),period_over_100ms=int(sum(periods>.1)),
        compute_over_100ms=int(sum(d['compute_sec']>.1 for d in commands)),
        initial_pixel_error=tracking[0]['pixel_error'],final_pixel_error=tracking[-1]['pixel_error'],
        final_distance_error_m=tracking[-1]['distance_error_m'],
        max_command_yaw_error_rad=max(abs(d['commanded_yaw_error']) for d in commands),
        max_measured_yaw_error_rad=max(abs(d['measured_yaw_error']) for d in commands),
        observation_age_avg_ms=float(1000*np.mean([d['observation_age_sec'] for d in tracking])),
        pose_gap_max_ms=float(1000*max(d['pose_gap_sec'] for d in tracking)),
        timeout_hold=True,latest_only=latest_ok,ik_failure_hold=ik_hold,competing_service_inhibited=True,
        real_camera=False,real_motors=False)
    (OUT/'ros_summary.json').write_text(json.dumps(summary,indent=2))
    (OUT/'ros_diagnostics.json').write_text(json.dumps(dict(vision=vision,arm=arm)))
    print(json.dumps(summary,indent=2))
finally:
    for proc in reversed(processes):stop(proc)
    for stream in streams:stream.close()
    node.destroy_node()
    if rclpy.ok():rclpy.shutdown()
