"""Run one circle and record measured ROS telemetry. Default backend is sim."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=['sim', 'can_mixed'], default='sim')
    parser.add_argument('--radius', type=float, default=.05)
    parser.add_argument('--period', type=float, default=60.)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=False)
    command = ['ros2', 'launch', 'arm_controller_pkg', 'xy_circle_demo.launch.py',
               f'backend:={args.backend}', 'startup_mode:=configured',
               'center_mode:=current_start', f'radius:={args.radius}',
               f'period:={args.period}', 'revolutions:=1']
    diagnostics = []
    goals = []
    log_events = []
    rclpy.init()
    node = rclpy.create_node('circle_validation_observer')
    output = (folder/'telemetry.jsonl').open('w')

    def diagnostic(msg):
        data = json.loads(msg.data)
        diagnostics.append(data)
        output.write(json.dumps(dict(topic='/arm_xy/diagnostics', data=data))+'\n')
        output.flush()

    def goal(msg):
        p = msg.pose.position
        data = [p.x, p.y, p.z]
        goals.append(data)
        output.write(json.dumps(dict(topic='/arm_xy/goal', data=data,
                                     stamp=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9))+'\n')

    node.create_subscription(String, '/arm_xy/diagnostics', diagnostic, qos_profile_sensor_data)
    node.create_subscription(PoseStamped, '/arm_xy/goal', goal, qos_profile_sensor_data)
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, start_new_session=True)

    def read_log():
        with (folder/'console.log').open('w') as log:
            for line in proc.stdout:
                log.write(line)
                log.flush()
                log_events.append((time.monotonic(), line))
                print(line.rstrip(), flush=True)

    thread = threading.Thread(target=read_log, daemon=True)
    thread.start()
    completed = None
    failure = None
    deadline = time.monotonic()+args.period+100.
    try:
        while time.monotonic() < deadline and proc.poll() is None:
            rclpy.spin_once(node, timeout_sec=.05)
            for stamp, line in list(log_events):
                if 'Circle demo complete' in line:
                    completed = stamp
                if any(text in line for text in ('preflight failed', 'fault latched', 'activation failed', 'Traceback')):
                    failure = line.strip()
            if failure or (completed and time.monotonic()-completed > 2.):
                break
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.wait(timeout=10.)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=5.)
        thread.join(timeout=2.)
        node.destroy_node()
        rclpy.shutdown()
        output.close()

    tracking = [d for d in diagnostics if d.get('reason') == 'tracking']
    measured = [d['measured_joints'] for d in tracking]
    summary = dict(command=command, completed=completed is not None, failure=failure,
                   process_exit=proc.returncode, goals=len(goals), tracking_samples=len(tracking))
    if tracking:
        errors = [np.linalg.norm(np.array(d['actual_pose'][:2])-d['goal_pose'][:2]) for d in tracking]
        period = [d['period_sec'] for d in tracking if d['period_sec'] is not None]
        summary.update(position_error_max_m=float(max(errors)), position_error_rms_m=float(np.sqrt(np.mean(np.square(errors)))),
                       measured_joint_min_deg=np.degrees(np.min(measured, axis=0)).tolist(),
                       measured_joint_max_deg=np.degrees(np.max(measured, axis=0)).tolist(),
                       measured_yaw_error_max_rad=max(abs(d['measured_yaw_error']) for d in tracking),
                       commanded_yaw_error_max_rad=max(abs(d['commanded_yaw_error']) for d in tracking),
                       period_avg_sec=float(np.mean(period)), period_max_sec=max(period),
                       compute_max_sec=max(d['compute_sec'] for d in tracking),
                       compute_over_100ms=sum(d['compute_sec']>.1 for d in tracking),
                       period_over_100ms=sum(v>.1 for v in period),
                       goal_age_max_sec=max(d['goal_age_sec'] for d in tracking))
    summary['passed'] = bool(completed and not failure and len(tracking) >= args.period*8
                             and np.max(np.ptp(measured, axis=0)) > .05
                             and summary.get('position_error_max_m', 1.) < .03
                             and summary.get('measured_yaw_error_max_rad', 1.) < .1)
    (folder/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
