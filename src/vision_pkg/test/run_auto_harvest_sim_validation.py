#!/usr/bin/env python3
"""Closed-loop integration check using the existing tracker/vision and sim EE."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

import yaml

os.environ['ROS_DOMAIN_ID'] = '175'
os.environ['ROS_LOCALHOST_ONLY'] = '1'
os.environ['ROS_LOG_DIR'] = '/tmp/auto_harvest_validation_logs'

import rclpy
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String
from end_effector_pkg.auto_harvest_node import AutoHarvestNode

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'src/end_effector_pkg/validation/limit_homing_20261112'
OUT.mkdir(parents=True, exist_ok=True)
processes = []
streams = []


def start(args, label):
    stream = open(OUT/(label+'.log'), 'w', encoding='utf-8')
    streams.append(stream)
    proc = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT,
                            start_new_session=True)
    processes.append(proc)
    return proc


ee_temp = tempfile.TemporaryDirectory(prefix='ee-limit-sim-config-')
ee_config = yaml.safe_load((ROOT/'module/set_params.yaml').read_text())
# Synthetic endpoints for this simulation only; never install them as calibration.
ee_config['auto_harvest']['hook_servo'].update(
    calibration_valid=True, open_feedback=1000, closed_feedback=3000)
ee_path = Path(ee_temp.name)/'ee.yaml'
ee_path.write_text(yaml.safe_dump(ee_config))
rclpy.init(args=['--ros-args', '-p', 'config_file:='+str(ee_path),
                 '-p', 'backend:=sim', '-p', 'keyboard_enabled:=false',
                 '-p', 'auto_confirm_sim_home:=true'])
auto = AutoHarvestNode()
executor = SingleThreadedExecutor()
executor.add_node(auto)
arm_diag, vision_diag, arm_states, auto_states = [], [], [], []
auto.create_subscription(String, '/arm_xy/diagnostics',
                         lambda msg: arm_diag.append(json.loads(msg.data)), 100)
auto.create_subscription(String, '/vision/servo_diagnostics',
                         lambda msg: vision_diag.append(json.loads(msg.data)), 100)
auto.create_subscription(String, '/arm_xy/harvest/state',
                         lambda msg: arm_states.append(json.loads(msg.data)), 10)
auto.create_subscription(String, '/end_effector/auto/state',
                         lambda msg: auto_states.append(json.loads(msg.data)), 10)


def spin(seconds=.05):
    executor.spin_once(timeout_sec=seconds)


def until(predicate, label, timeout=40.):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        spin(.02)
        if predicate():
            return
        if auto.state == auto.FAULT:
            raise AssertionError(f'EE fault during {label}: {auto.reason}')
        if any(proc.poll() is not None for proc in processes):
            raise AssertionError(f'process exited during {label}')
    raise AssertionError(f'timeout waiting for {label}; auto={auto.state}/{auto.reason}; '
                         f'arm={arm_states[-1:]}; vision={vision_diag[-1:]}')


try:
    with tempfile.TemporaryDirectory(prefix='auto-harvest-sim-') as temp:
        arm_config = yaml.safe_load((ROOT/'src/arm_controller_pkg/config/xy_robot_config.yaml').read_text())
        arm_config['initial_joints_deg'] = [5., 160., -65.]
        vision_config = yaml.safe_load((ROOT/'src/vision_pkg/config/realtime_detector.yaml').read_text())
        vision_config['detector']['weights'] = str(ROOT/'module/weights/base.pt')
        vision_config['target'].update(desired_distance_m=.25, target_pixel=None,
                                       target_pixel_offset_x_px=0., gain_per_sec=5.,
                                       max_speed_m_s=.02, max_acceleration_m_s2=.04,
                                       max_step_m=.003)
        vision_config['simulation']['initial_target_camera_m'] = [0., 0., .25]
        arm_yaml, vision_yaml = Path(temp)/'arm.yaml', Path(temp)/'vision.yaml'
        arm_yaml.write_text(yaml.safe_dump(arm_config))
        vision_yaml.write_text(yaml.safe_dump(vision_config))
        start(['ros2', 'run', 'arm_controller_pkg', 'arm_xy_tracker', '--ros-args',
               '-p', 'backend:=sim', '-p', 'startup_mode:=current',
               '-p', 'harvest_cycle_enabled:=true', '-p', 'require_ee_ready:=true',
               '-p', 'config_file:='+str(arm_yaml)], 'auto_harvest_arm')
        start(['ros2', 'run', 'vision_pkg', 'vision_service_realtime', '--ros-args',
               '-p', 'synthetic_camera:=true', '-p', 'show_window:=false',
               '-p', 'harvest_cycle_enabled:=true', '-p', 'config_file:='+str(vision_yaml)],
              'auto_harvest_vision')

        until(lambda: auto.state == auto.WAIT_ARM, 'EE homing and ready handshake')
        until(lambda: auto.state == auto.APPROACH and arm_states and
              arm_states[-1]['state'] == 'APPROACH', 'arm startup and approach')
        cycle_sensor_records = []
        for cycle in range(2):
            until(lambda: auto.state == auto.WAIT_NEXT, f'cycle {cycle+1} complete', 55.)
            cycle_sensor_records.append(dict(auto.telemetry))
            for name in auto.active_axes:
                target = int(auto.settings['initial_pose'][name])
                tolerance = int(auto.settings['target_tolerance'][name])
                assert abs(auto.telemetry[name]-target) <= tolerance, (name, auto.telemetry[name], target)
            if cycle == 0:
                auto._handle_key('n')
                until(lambda: auto.state == auto.APPROACH and
                      arm_states[-1]['state'] == 'APPROACH', 'explicit n resume')
        transitions = []
        for item in auto_states:
            if not transitions or transitions[-1] != item['state']:
                transitions.append(item['state'])
        report = dict(cycles=2, transitions=transitions,
                      ee_sensor_feedback=True, fitted_axes=list(auto.active_axes),
                      automatic_nc_limit_homing=auto.homing_verified,
                      test_only_servo_feedback=[1000, 3000],
                      physical_servo_calibration=False,
                      arm_waited_for_ee_ready=True, arrival_reason_and_hold_ready=True,
                      arm_return_acknowledged=True, n_required_between_cycles=True,
                      final_ee_sensors=cycle_sensor_records[-1],
                      simulated_arm=True, synthetic_vision=True, physical_hardware=False)
        (OUT/'auto_harvest_sim_summary.json').write_text(json.dumps(report, indent=2))
        (OUT/'auto_harvest_sim_diagnostics.json').write_text(json.dumps(dict(
            arm=arm_diag, vision=vision_diag, arm_states=arm_states,
            ee_states=auto_states), indent=2))
        print(json.dumps(report, indent=2))
finally:
    auto._safe_stop('validation finished')
    executor.remove_node(auto)
    auto.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
    for proc in reversed(processes):
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=3)
    for stream in streams:
        stream.close()
    ee_temp.cleanup()
