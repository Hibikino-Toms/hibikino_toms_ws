#!/usr/bin/env python3
"""ROS + FK + fixed-world camera validation. Only simulated backends are used.

Run after sourcing install/setup.bash with the system Python. This script owns
an isolated ROS domain and starts just one simulated tracker subprocess.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time

os.environ['ROS_DOMAIN_ID'] = '183'
os.environ['ROS_LOCALHOST_ONLY'] = '1'
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
os.environ['ROS_LOG_DIR'] = str(OUT/'ros_logs')

import numpy as np
import pyrealsense2 as rs
import rclpy
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String
import yaml
from vision_pkg.vison_sevice_realtime import RealtimeTomatoDetector


def main():
    rows, scene_results = [], {}
    arm = yaml.safe_load((ROOT/'src/arm_controller_pkg/config/xy_robot_config.yaml').read_text())
    arm['initial_joints_deg'] = arm['startup']['demo_joints_deg']
    vision = yaml.safe_load((ROOT/'src/vision_pkg/config/realtime_detector.yaml').read_text())
    vision['detector']['weights'] = str(ROOT/'module/weights/base.pt')
    vision['target'].update(desired_distance_m=.25, gain_per_sec=2., max_speed_m_s=.025,
                            max_acceleration_m_s2=.08, max_step_m=.003)
    arm_rows, z_rows, vision_rows = [], [], []
    tracker = None
    node = executor = worker = None
    with tempfile.TemporaryDirectory(prefix='z_tracking_') as tmp:
        a, v = Path(tmp)/'arm.yaml', Path(tmp)/'vision.yaml'
        a.write_text(yaml.safe_dump(arm));v.write_text(yaml.safe_dump(vision))
        log = (OUT/'tracker.log').open('w')
        try:
            tracker = subprocess.Popen(['ros2', 'run', 'arm_controller_pkg', 'arm_xy_tracker',
                '--ros-args', '-p', 'backend:=sim', '-p', 'startup_mode:=current',
                '-p', 'z_tracking_enabled:=true', '-p', f'config_file:={a}',
                '-p', 'tracking_position_tolerance_m:=0.00001',
                '-p', 'tracking_angle_tolerance_rad:=0.0001'], stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True)
            rclpy.init(args=['--ros-args', '-p', f'config_file:={v}', '-p', 'synthetic_camera:=true',
                             '-p', 'show_window:=false', '-p', 'z_tracking_enabled:=true'])
            node = RealtimeTomatoDetector()
            subs = []
            for topic, destination in (('/arm_xy/diagnostics', arm_rows),
                    ('/arm_xy/z/state', z_rows), ('/vision/servo_diagnostics', vision_rows)):
                subs.append(node.create_subscription(String, topic,
                    lambda msg, dest=destination: dest.append(json.loads(msg.data)), 10))
            executor = SingleThreadedExecutor();executor.add_node(node)
            worker = threading.Thread(target=executor.spin, daemon=True);worker.start()
            def pump(seconds=None, condition=None, timeout=8.):
                end = time.monotonic()+(seconds if seconds is not None else timeout)
                deadline=time.monotonic()
                while time.monotonic()<end:
                    if tracker.poll() is not None:
                        raise AssertionError('simulated tracker exited')
                    node.process_frame()
                    rows.append(dict(time=time.monotonic(), vision=dict(node.diag),
                                     arm=arm_rows[-1] if arm_rows else None,
                                     z=z_rows[-1] if z_rows else None))
                    if condition is not None and condition():return
                    deadline+=1./15
                    time.sleep(max(0., deadline-time.monotonic()))
                if condition is not None:raise AssertionError('condition timed out')
            pump(condition=lambda: node.ready and node.actual_pose is not None and
                 z_rows and z_rows[-1]['phase']=='IDLE')
            def place(dx=0., optical_down=0.):
                pose=np.asarray(node.actual_pose)
                ray=np.asarray(rs.rs2_deproject_pixel_to_point(node.color_intrinsics,
                                                              node.servo.pixel.tolist(), 1.))
                origin=np.r_[pose[:2], node.actual_z_m]
                # Default matrix translation is zero; account for it if configured.
                from vision_pkg.modules.image_servo import rotation
                origin+=rotation(pose[2]-node.servo.reference)@node.camera_to_ee[:3,3]
                node.sim_world=origin+node.servo.camera_rotation(pose[2])@(ray*.25+[dx,optical_down,0.])
            place()
            initial=np.r_[node.actual_pose[:2], node.actual_z_m]
            start=len(z_rows);pump(seconds=2.)
            assert all(x['phase']=='IDLE' for x in z_rows[start:])
            displacement=float(np.linalg.norm(np.r_[node.actual_pose[:2], node.actual_z_m]-initial))
            assert displacement<1e-6
            scene_results['center_at_distance']={'displacement_m':displacement}
            for name, dz in (('up', -.015), ('down', .015)):
                place(dx=.010 if name=='up' else 0., optical_down=dz)
                start=len(arm_rows);before_z=node.actual_z_m
                pump(condition=lambda:z_rows[-1]['phase']=='MOVING_Z')
                pump(condition=lambda:z_rows[-1]['phase']=='IDLE')
                pump(seconds=2.)
                during=[x for x in arm_rows[start:] if x.get('z',{}).get('phase')=='MOVING_Z']
                assert len(during)>5
                joint_samples=np.array([x['measured_joints'] for x in during])
                drift=float(np.max(np.ptp(joint_samples,axis=0)))
                assert drift<1e-8, drift
                assert abs(node.diag['vertical_error_m'])<.010
                if name=='up':assert node.actual_z_m>before_z+.010
                else:assert node.actual_z_m<before_z-.010
                scene_results[name]={'z_change_m':node.actual_z_m-before_z,
                    'joint_drift_while_z_rad':drift, 'remaining_z_error_m':node.diag['vertical_error_m'],
                    'remaining_pixel_error':node.diag['pixel_error']}
            place(optical_down=.008)
            start=len(z_rows);before_z=node.actual_z_m;pump(seconds=2.)
            assert all(x['phase']=='IDLE' for x in z_rows[start:])
            assert abs(node.actual_z_m-before_z)<1e-9
            scene_results['below_threshold']={'z_change_m':node.actual_z_m-before_z}
            place(optical_down=-.015)
            pump(condition=lambda:z_rows[-1]['phase']=='MOVING_Z')
            node.sim_world=np.array([100.,100.,100.])
            pump(condition=lambda:z_rows[-1]['phase']=='FAULT')
            stopped=node.actual_z_m;pump(seconds=1.)
            assert abs(node.actual_z_m-stopped)<1e-9
            scene_results['target_lost_during_move']={'phase':z_rows[-1]['phase'],
                                                     'reason':z_rows[-1]['reason']}
            periods=[x['period_sec'] for x in arm_rows if x.get('period_sec') is not None]
            times=[x['stamp'] for x in vision_rows if x.get('reason') not in ('arm_not_ready','waiting_frame')]
            summary=dict(passed=True, scenes=scene_results, samples=len(rows),
                tracker_rate_hz=1./float(np.mean(periods)),
                tracker_period_max_ms=1000*max(periods),
                tracker_period_over_100ms=sum(t>.1 for t in periods),
                tracker_compute_max_ms=1000*max(x['compute_sec'] for x in arm_rows),
                simulated_vision_rate_hz=(len(times)-1)/(times[-1]-times[0]),
                vision_process_max_ms=1000*max(x['processing_sec'] for x in vision_rows),
                note='Synthetic camera only; no YOLO inference or real motors measured.')
            (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
            print(json.dumps(summary,indent=2))
        finally:
            (OUT/'diagnostics.json').write_text(json.dumps(rows,indent=2)+'\n')
            if executor is not None:executor.shutdown(timeout_sec=2.)
            if worker is not None:worker.join(timeout=2.)
            if node is not None:node.destroy_node()
            if rclpy.ok():rclpy.shutdown()
            if tracker is not None and tracker.poll() is None:
                os.killpg(tracker.pid,signal.SIGINT)
                try:tracker.wait(timeout=5.)
                except subprocess.TimeoutExpired:
                    os.killpg(tracker.pid,signal.SIGKILL);tracker.wait()
            log.close()


if __name__=='__main__':main()
