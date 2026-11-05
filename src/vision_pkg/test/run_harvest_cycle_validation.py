#!/usr/bin/env python3
"""Three EXISTING nodes only. Synthetic camera, simulated arm/EE, two cycles."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import numpy as np
import yaml
os.environ['ROS_DOMAIN_ID']='174'
os.environ['ROS_LOCALHOST_ONLY']='1'
os.environ['ROS_LOG_DIR']='/tmp/harvest_cycle_validation_logs'
import rclpy
from std_msgs.msg import String, Bool
from geometry_msgs.msg import PoseStamped
from end_effector_pkg.pull_module_teleop import PullModuleTeleop

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'src/vision_pkg/validation';OUT.mkdir(exist_ok=True)
processes=[];streams=[]

def start(args,name):
    stream=open(OUT/(name+'.log'),'w');streams.append(stream)
    proc=subprocess.Popen(args,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    processes.append(proc);return proc

rclpy.init(args=['--ros-args','-p','simulate_hardware:=true','-p','keyboard_enabled:=false',
                '-p','harvest_link_enabled:=true'])
ee=PullModuleTeleop();arm=[];vision=[];states=[]
ee.create_subscription(String,'/arm_xy/diagnostics',lambda m:arm.append(json.loads(m.data)),100)
ee.create_subscription(String,'/vision/servo_diagnostics',lambda m:vision.append(json.loads(m.data)),100)
ee.create_subscription(String,'/arm_xy/harvest/state',lambda m:states.append(json.loads(m.data)),100)
goals=ee.create_publisher(PoseStamped,'/arm_xy/goal',1)

def spin(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:rclpy.spin_once(ee,timeout_sec=.02)

def until(predicate,label,timeout=50.):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        rclpy.spin_once(ee,timeout_sec=.02)
        if predicate():return
        if any(p.poll() is not None for p in processes):raise AssertionError('node exited')
    raise AssertionError(f'timeout: {label}; mode={ee._mode()}; vision={vision[-1:]}; arm={arm[-1:]}')

try:
    with tempfile.TemporaryDirectory(prefix='harvest-cycle-') as temp:
        arm_cfg=yaml.safe_load((ROOT/'src/arm_controller_pkg/config/xy_robot_config.yaml').read_text())
        arm_cfg['initial_joints_deg']=[8.,158.,-66.]
        vision_cfg=yaml.safe_load((ROOT/'src/vision_pkg/config/realtime_detector.yaml').read_text())
        vision_cfg['detector']['weights']=str(ROOT/'module/weights/base.pt')
        vision_cfg['target'].update(desired_distance_m=.25,target_pixel=None,target_pixel_offset_x_px=0.,
            gain_per_sec=10.,max_speed_m_s=.04,max_acceleration_m_s2=.08,max_step_m=.006)
        vision_cfg['simulation']['initial_target_camera_m']=[0.,0.,.25]
        ap=Path(temp)/'arm.yaml';vp=Path(temp)/'vision.yaml'
        ap.write_text(yaml.safe_dump(arm_cfg));vp.write_text(yaml.safe_dump(vision_cfg))
        start(['ros2','run','arm_controller_pkg','arm_xy_tracker','--ros-args',
               '-p','backend:=sim','-p','startup_mode:=current','-p','harvest_cycle_enabled:=true',
               '-p','config_file:='+str(ap)],'harvest_arm')
        start(['ros2','run','vision_pkg','vision_service_realtime','--ros-args',
               '-p','synthetic_camera:=true','-p','show_window:=false','-p','harvest_cycle_enabled:=true',
               '-p','config_file:='+str(vp)],'harvest_vision')
        until(lambda:ee._mode()=='HARVEST_HOLD','first approach complete')
        spin(.2)
        for iteration in range(2):
            held=np.array(arm[-1]['measured_joints'])
            # A valid but unrelated incoming goal cannot release harvest hold.
            msg=PoseStamped();msg.header.frame_id='arm_base';msg.header.stamp=ee.get_clock().now().to_msg()
            msg.pose.position.x=.2;msg.pose.position.y=.25
            msg.pose.orientation.z=float(np.sin(np.radians(100)/2));msg.pose.orientation.w=float(np.cos(np.radians(100)/2))
            goals.publish(msg);spin(.4)
            assert ee._mode()=='HARVEST_HOLD'
            np.testing.assert_allclose(arm[-1]['measured_joints'],held,atol=1e-8)
            ee._handle_key('w');assert ee.ee_running
            spin(.1)
            ee._handle_key('r')
            until(lambda:ee._mode()=='RETURNING','pull accepted',5.)
            if iteration==0:
                # Lost EE heartbeat must stop, not finish the retreat unattended.
                ee.harvest_link=False
                until(lambda:ee._mode()=='HARVEST_HOLD','EE watchdog',3.)
                spin(.1)
                assert states[-1]['reason']=='ee_heartbeat_lost'
                ee.harvest_link=True;spin(.3)
                ee._handle_key('r')
                until(lambda:ee._mode()=='RETURNING','pull after watchdog',5.)
                ee._handle_key(' ')
                until(lambda:ee._mode()=='HARVEST_HOLD','Space interrupts pull',5.)
                spin(.2);ee._handle_key('r')
                until(lambda:ee._mode()=='RETURNING','pull after pause',5.)
            # Vision publishes loss/hold continuously while RETURNING; ownership
            # must prevent those messages from stopping the return.
            until(lambda:ee._mode()=='RETURNED','measured home arrival',20.)
            spin(.4)
            np.testing.assert_allclose(arm[-1]['measured_joints'],np.radians([5.,160.,-65.]),atol=.018)
            assert not ee.ee_running
            spin(.8);assert ee._mode()=='RETURNED'  # No automatic approach.
            ee._handle_key('n')
            until(lambda:ee._mode()=='APPROACH','manual resume',5.)
            until(lambda:ee._mode()=='HARVEST_HOLD','next approach complete',50.)
            spin(.2)
        # EE w/s remain directly operable during APPROACH without changing arm mode.
        ee._handle_key('n');until(lambda:ee._mode()=='APPROACH','resume for EE independence',5.)
        spin(.1);ee._handle_key('w')
        assert ee.ee_running and ee._mode()=='APPROACH'
        ee._handle_key(' ');spin(.2)
        changes=[]
        for item in states:
            if not changes or changes[-1]!=item['state']:changes.append(item['state'])
        report=dict(cycles=2,states=changes,held_despite_vision_goal=True,
            return_despite_vision_hold=True,return_to_initial_joints=True,manual_resume_required=True,
            ee_heartbeat_stop=True,space_interrupt=True,ee_independent_of_arm_state=True,
            real_camera=False,real_arm=False,real_ee=False,new_production_nodes=0)
        (OUT/'harvest_cycle_summary.json').write_text(json.dumps(report,indent=2))
        (OUT/'harvest_cycle_diagnostics.json').write_text(json.dumps(dict(arm=arm,vision=vision,states=states)))
        print(json.dumps(report,indent=2))
finally:
    ee.harvest_link=True
    if rclpy.ok():ee.alive_pub.publish(Bool(data=False));spin(.15)
    ee.destroy_node()
    if rclpy.ok():rclpy.shutdown()
    for proc in reversed(processes):
        if proc.poll() is None:
            os.killpg(proc.pid,signal.SIGINT)
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=3)
    for stream in streams:stream.close()
