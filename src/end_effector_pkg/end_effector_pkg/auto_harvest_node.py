"""Sensor-feedback end-effector harvest sequence and arm-cycle coordinator."""
import json
import math
import os
import re
import select
import sys
import termios
import threading
import time
import tty
from collections import deque

import rclpy
import serial
import serial.tools.list_ports
import yaml
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger


PARAMS_PATH = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
STATUS_RE = re.compile(
    r'PWM=(-?\d+),(-?\d+),(-?\d+),(-?\d+).*?ENC4=(-?\d+)'
    r'.*?POT1=(\d+),.*?POT2=(\d+),.*?POT3=(\d+),')
SENSOR_NAMES = ('pot1', 'pot2', 'pot3', 'enc4')
MOTOR_NUMBER = {'pot1': 1, 'pot2': 2, 'pot3': 3, 'enc4': 4}


def load_settings(path):
    with open(path, encoding='utf-8') as stream:
        root = yaml.safe_load(stream)
    settings = root.get('auto_harvest') if isinstance(root, dict) else None
    if not isinstance(settings, dict):
        raise ValueError('auto_harvest config must be a YAML mapping')
    result = dict(settings)
    for key in ('sensor_timeout_sec', 'stage_timeout_sec', 'progress_timeout_sec',
                'heartbeat_period_sec', 'serial_watchdog_sec', 'control_rate_hz'):
        value = float(result[key])
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f'auto_harvest.{key} must be positive and finite')
    for key in ('initial_pose', 'harvest_pose', 'sensor_limits', 'target_tolerance',
                'increase_pwm_sign', 'pwm', 'progress_min_delta',
                'home_stability_tolerance'):
        if not isinstance(result.get(key), dict):
            raise ValueError(f'auto_harvest.{key} must be a mapping')
    # Accept the previous scalar form for existing user configs, then expose
    # the normalized per-axis form to the controller.
    for bound in ('min', 'max'):
        configured = result['pwm'].get(bound)
        if isinstance(configured, dict):
            missing = [name for name in SENSOR_NAMES if name not in configured]
            if missing:
                raise ValueError(f'auto_harvest.pwm.{bound} is missing axes: {missing}')
            result['pwm'][bound] = {name: int(configured[name]) for name in SENSOR_NAMES}
        else:
            scalar = int(configured)
            result['pwm'][bound] = {name: scalar for name in SENSOR_NAMES}
    if int(result.get('sensor_stable_samples', 0)) < 1:
        raise ValueError('auto_harvest.sensor_stable_samples must be at least 1')
    for name in SENSOR_NAMES:
        low, high = result['sensor_limits'][name]
        target = result['initial_pose'][name]
        if not low <= target <= high:
            raise ValueError(f'initial target for {name} is outside configured limits')
        tol = int(result['target_tolerance'][name])
        sign = int(result['increase_pwm_sign'][name])
        if tol < 0 or sign not in (-1, 1):
            raise ValueError(f'invalid tolerance or direction for {name}')
        if int(result['home_stability_tolerance'][name]) < 0:
            raise ValueError(f'home stability tolerance for {name} must not be negative')
    for name in SENSOR_NAMES:
        min_pwm = int(result['pwm']['min'][name])
        max_pwm = int(result['pwm']['max'][name])
        if not 1 <= min_pwm <= max_pwm <= 255:
            raise ValueError(
                f'PWM limits for {name} must satisfy 1 <= min <= max <= 255')
    total_pwm_limit = int(result['pwm'].get('max_total_abs_pwm', 255))
    init_minimum_total = sum(int(result['pwm']['min'][name])
                             for name in ('pot1', 'pot2', 'pot3'))
    if total_pwm_limit < init_minimum_total:
        raise ValueError(
            'pwm.max_total_abs_pwm must be at least the sum of the '
            'POT1/POT2/POT3 minimum PWMs for 3-axis EE initialization')
    if float(result['heartbeat_period_sec']) >= float(result['serial_watchdog_sec'])/2.:
        raise ValueError('host heartbeat must run at least twice as often as Pico watchdog')
    return result


class SerialPico:
    """Owns the Pico serial port and translates its existing status protocol."""
    def __init__(self, settings):
        wanted = str(settings.get('serial_number', '')).strip()
        candidates = list(serial.tools.list_ports.comports())
        if wanted:
            candidates = [port for port in candidates if port.serial_number == wanted]
        else:
            candidates = [port for port in candidates if port.vid == 0x2E8A]
        if len(candidates) != 1:
            found = [(p.device, p.serial_number, p.vid, p.pid) for p in candidates]
            raise RuntimeError(f'Expected one configured Raspberry Pi Pico serial device; found {found}')
        self.port = serial.Serial(candidates[0].device,
                                  int(settings.get('baudrate', 115200)), timeout=0,
                                  write_timeout=.2)
        self.port.reset_input_buffer()
        self.buffer = bytearray()
        self.latest = None
        self.sample_seq = 0
        self.last_sample = None
        self.last_heartbeat = 0.
        self.lock = threading.Lock()

    def poll(self, now):
        with self.lock:
            count = self.port.in_waiting
            if count:
                self.buffer.extend(self.port.read(min(count, 4096)))
            while b'\n' in self.buffer:
                raw, _, rest = self.buffer.partition(b'\n')
                self.buffer = bytearray(rest)
                match = STATUS_RE.search(raw.decode('ascii', errors='ignore'))
                if match:
                    pwm1, pwm2, pwm3, pwm4, enc4, pot1, pot2, pot3 = (
                        int(v) for v in match.groups())
                    self.latest = dict(pot1=pot1, pot2=pot2, pot3=pot3, enc4=enc4,
                                       pwm=[pwm1, pwm2, pwm3, pwm4])
                    self.sample_seq += 1
                    self.last_sample = now
            if len(self.buffer) > 8192:
                self.buffer.clear()
            return self.latest, self.sample_seq, self.last_sample

    def send(self, command):
        with self.lock:
            self.port.write((command + '\n').encode('ascii'))

    def drive(self, values):
        self.send('DRIVE ' + ','.join(str(int(v)) for v in values))

    def heartbeat(self):
        self.send('KEEPALIVE')
        self.last_heartbeat = time.monotonic()

    def zero_encoder(self):
        self.send('ZERO_ENC4')

    def stop(self):
        self.send('STOP')

    def close(self):
        try:
            self.stop()
        finally:
            self.port.close()


class SimulatedPico:
    """In-process sensor/motor model; no additional ROS node or USB access."""
    def __init__(self, settings):
        self.settings = settings
        self.values = {key: int(value) for key, value in settings['initial_pose'].items()}
        self.drive_values = [0, 0, 0, 0]
        self.sample_seq = 0
        self.last_sample = time.monotonic()
        self.last_update = self.last_sample
        self.rate = float(settings.get('simulated_counts_per_sec', 900.))

    def poll(self, now):
        dt = min(.1, max(0., now-self.last_update))
        self.last_update = now
        for name, index in MOTOR_NUMBER.items():
            pwm = self.drive_values[index-1]
            delta = pwm * self.settings['increase_pwm_sign'][name] * self.rate/255.*dt
            low, high = self.settings['sensor_limits'][name]
            self.values[name] = max(low, min(high, self.values[name]+delta))
        self.last_sample = now
        self.sample_seq += 1
        values = {name: int(round(value)) for name, value in self.values.items()}
        return dict(values, pwm=list(self.drive_values)), self.sample_seq, self.last_sample

    def drive(self, values):
        self.drive_values = [max(-255, min(255, int(v))) for v in values]

    def heartbeat(self):
        pass

    def zero_encoder(self):
        self.values['enc4'] = 0

    def stop(self):
        self.drive_values = [0, 0, 0, 0]

    def close(self):
        self.stop()


class AutoHarvestNode(Node):
    """One ROS node owns the EE serial link and its automatic state machine."""
    WAIT_HOME = 'WAIT_ENCODER_HOME'
    WAIT_ZERO = 'WAIT_ENCODER_ZERO'
    INITIALIZING = 'EE_INITIALIZING'
    WAIT_ARM = 'WAIT_ARM_STARTUP'
    APPROACH = 'APPROACH'
    HARVEST_PITCH = 'HARVEST_PITCH'
    HARVEST_EXTEND = 'HARVEST_EXTEND'
    HARVEST_CLOSE = 'HARVEST_CLOSE'
    HARVEST_AXIS_BY_STATE = {
        HARVEST_PITCH: 'pot2',  # Motor 2
        HARVEST_EXTEND: 'enc4',  # Motor 4
        HARVEST_CLOSE: 'pot3',  # Motor 3
    }
    WAIT_RETURN = 'WAIT_ARM_RETURN'
    RESET_EE = 'EE_RESET'
    WAIT_NEXT = 'WAIT_NEXT_CYCLE'
    WAIT_RESUME = 'WAIT_ARM_RESUME'
    ABORTED = 'ABORTED'
    FAULT = 'FAULT'

    def __init__(self):
        super().__init__('auto_harvest')
        self.declare_parameter('config_file', '')
        self.declare_parameter('backend', 'sim')
        self.declare_parameter('keyboard_enabled', True)
        self.declare_parameter('auto_confirm_sim_home', True)
        config_path = self.get_parameter('config_file').value
        if not config_path:
            raise RuntimeError('Set config_file (see config/auto_harvest.yaml)')
        self.settings = load_settings(config_path)
        backend = str(self.get_parameter('backend').value)
        self.io = SimulatedPico(self.settings) if backend == 'sim' else SerialPico(self.settings) if backend == 'serial' else None
        if self.io is None:
            raise ValueError('backend must be sim or serial')
        self.state = self.WAIT_HOME
        self.reason = 'confirm rail retracted reference with c' if backend == 'serial' else 'simulated home reference'
        self.targets = None
        self.stage_started = time.monotonic()
        self.arm_start_wait = self.stage_started
        self.target_stable = {name: 0 for name in SENSOR_NAMES}
        self.last_sample_seq = -1
        self.valid_sensor_samples = 0
        self.sensor_stable_samples = 0
        self.home_sensor_window = deque(maxlen=int(self.settings['sensor_stable_samples']))
        self.progress_at = {name: time.monotonic() for name in SENSOR_NAMES}
        self.last_progress_value = {}
        self.range_recovery_active = False
        self.active_target_name = None
        self.telemetry = None
        self.sample_seq = 0
        self.sample_time = None
        self.arm_status = None
        self.arm_ready = False
        self.last_arm_sequence = -1
        self.eligible_approach_sequence = None
        self.cycle_sequence = None
        self.request_future = None
        self.request_started = 0.
        self.last_hb = 0.
        self.last_diag = 0.
        self.last_info = 0.
        self.exit_requested = False
        self.keyboard_enabled = bool(self.get_parameter('keyboard_enabled').value)
        self.terminal = sys.stdin
        self.terminal_settings = None
        self.owns_terminal = False
        if self.keyboard_enabled and not self.terminal.isatty():
            try:
                self.terminal = open('/dev/tty', 'rb', buffering=0)
                self.owns_terminal = True
            except OSError:
                self.keyboard_enabled = False
                self.get_logger().warning(
                    'No controlling terminal; keyboard input is disabled. Use '
                    '/end_effector/auto/key for c, n, or space commands.')
        if self.keyboard_enabled:
            self.terminal_settings = termios.tcgetattr(self.terminal.fileno())
            tty.setcbreak(self.terminal.fileno())
        self.control_lock = threading.Lock()
        self.ready_pub = self.create_publisher(Bool, '/end_effector/ready', QoSProfile(
            depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE))
        self.alive_pub = self.create_publisher(Bool, '/arm_xy/harvest/ee_alive', 1)
        self.state_pub = self.create_publisher(String, '/end_effector/auto/state', 10)
        self.key_sub = self.create_subscription(
            String, '/end_effector/auto/key', self._key_callback, 10)
        self.arm_sub = self.create_subscription(String, '/arm_xy/harvest/state',
            self._arm_state_callback, QoSProfile(depth=1,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE))
        self.arm_clients = {action: self.create_client(Trigger, f'/arm_xy/harvest/{action}')
                            for action in ('hold', 'pull', 'resume')}
        self.ready_pub.publish(Bool(data=False))
        self.timer = self.create_timer(1./float(self.settings['control_rate_hz']), self._tick)
        self.get_logger().info(
            f'Automatic EE harvest started: backend={backend}, state={self.state}. '
            'Space=abort and hold, n=resume only after cycle reset, c=confirm encoder reference.')
        if backend == 'serial':
            self.get_logger().warning(
                'Manually place the rail at its fully retracted reference with all motors stopped, '
                'then press c. No encoder limit switch is available.')
        if backend == 'sim' and bool(self.get_parameter('auto_confirm_sim_home').value):
            self.io.zero_encoder()

    def _arm_state_callback(self, msg):
        try:
            data = json.loads(msg.data)
            state = str(data['state'])
            seq = int(data['sequence'])
            stamp = float(data['stamp'])
            if state not in ('STARTUP', 'APPROACH', 'HARVEST_HOLD', 'RETURNING',
                             'RETURNED', 'FAULT', 'DISABLED') or not math.isfinite(stamp):
                return
            ros_now = self.get_clock().now().nanoseconds/1e9
            if abs(ros_now-stamp) > .7:
                return
            previous = self.arm_status
            if previous is not None and seq < previous['sequence']:
                return
            self.arm_status = dict(state=state, sequence=seq, reason=str(data.get('reason','')),
                                   hold_ready=bool(data.get('hold_ready', False)),
                                   stamp=stamp, received=time.monotonic())
            self.last_arm_sequence = seq
            if state == 'FAULT' and self.state not in (self.FAULT, self.ABORTED):
                self._fault(f'arm entered FAULT: {self.arm_status["reason"]}')
                return
            moving_ee = (self.HARVEST_PITCH, self.HARVEST_EXTEND, self.HARVEST_CLOSE)
            if self.state in moving_ee and state != 'HARVEST_HOLD':
                self._fault(f'arm left harvest hold during EE action: {state}')
                return
            if self.state == self.WAIT_RETURN and state not in ('HARVEST_HOLD', 'RETURNING', 'RETURNED'):
                self._fault(f'unexpected arm state while waiting for return: {state}')
                return
            if self.state in (self.RESET_EE, self.WAIT_NEXT) and state != 'RETURNED':
                self._fault(f'arm left returned pose before EE reset/resume: {state}')
                return
            if self.state == self.APPROACH and state == 'HARVEST_HOLD' and self.arm_status['reason'] != 'approach_complete':
                self._transition(self.ABORTED, 'arm was manually held; no automatic harvest started')
                return
            if self.state in (self.WAIT_ARM, self.WAIT_RESUME) and state == 'APPROACH' and (
                    self.arm_status['reason'] == ('startup_complete' if self.state == self.WAIT_ARM else 'operator_resume')):
                self.eligible_approach_sequence = seq
                self._transition(self.APPROACH, 'arm startup and vision tracking ready')
            if self.state == self.APPROACH and state == 'HARVEST_HOLD':
                new_cycle = (self.eligible_approach_sequence is not None and
                             seq > self.eligible_approach_sequence and
                             self.arm_status['reason'] == 'approach_complete' and
                             self.arm_status['hold_ready'])
                if new_cycle and self.cycle_sequence != seq:
                    self.cycle_sequence = seq
                    self._begin_motion(self.HARVEST_PITCH, {'pot2': self.settings['harvest_pose']['pot2']})
            if self.state == self.WAIT_RETURN and state == 'RETURNED' and self.arm_status['reason'] == 'return_complete_wait_for_n':
                self._begin_motion(self.RESET_EE, self.settings['initial_pose'])
            if self.state == self.WAIT_NEXT and state == 'RETURNED' and self.arm_status['reason'] == 'return_complete_wait_for_n':
                self.arm_ready = True
            if self.state == self.WAIT_ARM and state == 'FAULT':
                self._fault('arm entered FAULT during startup')
            if self.state in (self.HARVEST_PITCH, self.HARVEST_EXTEND, self.HARVEST_CLOSE,
                              self.WAIT_RETURN, self.RESET_EE, self.WAIT_NEXT):
                if previous is not None and state == 'FAULT':
                    self._fault('arm harvest control entered FAULT')
        except (ValueError, KeyError, TypeError):
            return

    def _transition(self, state, reason):
        self.state, self.reason = state, reason
        self.stage_started = time.monotonic()
        self.target_stable = {name: 0 for name in SENSOR_NAMES}
        self.progress_at = {name: self.stage_started for name in SENSOR_NAMES}
        self.last_progress_value = {}
        self.range_recovery_active = False
        self.active_target_name = None
        self.targets = None
        self.get_logger().info(f'Auto harvest: {state} ({reason})')

    def _begin_motion(self, state, targets):
        # Harvest stages must remain strictly sequential. The Pico stops other
        # axes when it receives a drive command, so each stage owns one motor.
        expected_axis = self.HARVEST_AXIS_BY_STATE.get(state)
        if expected_axis is not None and (len(targets) != 1 or expected_axis not in targets):
            self._fault(
                f'{state} must move only {expected_axis} '
                f'(motor {MOTOR_NUMBER[expected_axis]}); got {list(targets)}')
            return
        for name, target in targets.items():
            low, high = self.settings['sensor_limits'][name]
            if not low <= float(target) <= high:
                self._fault(f'{name} target {target} outside configured limits {low}..{high}')
                return
        self._transition(state, 'closed-loop sensor move')
        self.targets = dict(targets)

    def _fresh_arm_state(self):
        status = self.arm_status
        if status is None or time.monotonic()-status['received'] > .7:
            return None
        return status

    def _request_arm(self, action):
        client = self.arm_clients[action]
        if not client.service_is_ready():
            self._fault(f'arm {action} service unavailable')
            return
        self.request_started = time.monotonic()
        self.request_future = client.call_async(Trigger.Request())
        self.request_future.add_done_callback(self._arm_request_result)

    def _arm_request_result(self, future):
        if future is not self.request_future or future.cancelled():
            return
        try:
            response = future.result()
            if not response.success:
                self._fault(f'arm request rejected: {response.message}')
        except Exception as exc:  # noqa: BLE001
            self._fault(f'arm service failed: {exc}')

    def _arm_wait_check(self, now):
        if self.state == self.WAIT_ARM and self._fresh_arm_state() is None:
            if now-self.arm_start_wait > float(self.settings['arm_startup_timeout_sec']):
                self._fault('arm startup-state heartbeat timeout')
                return False
            return True
        if self.state in (self.WAIT_ARM, self.WAIT_RESUME, self.APPROACH, self.HARVEST_PITCH,
                          self.HARVEST_EXTEND, self.HARVEST_CLOSE, self.WAIT_RETURN,
                          self.RESET_EE, self.WAIT_NEXT):
            if self._fresh_arm_state() is None:
                self._fault('arm harvest-state heartbeat lost')
                return False
            status = self._fresh_arm_state()
            if self.state == self.WAIT_RESUME and status['state'] not in ('RETURNED', 'APPROACH'):
                self._fault(f'unexpected arm state while waiting to resume: {status["state"]}')
                return False
            if self.state == self.APPROACH and status['state'] not in ('APPROACH', 'HARVEST_HOLD'):
                self._fault(f'unexpected arm state while approaching: {status["state"]}')
                return False
            if self.state in (self.HARVEST_PITCH, self.HARVEST_EXTEND,
                              self.HARVEST_CLOSE) and status['state'] != 'HARVEST_HOLD':
                self._fault(f'arm is not holding during EE action: {status["state"]}')
                return False
        return True

    def _pwm_for(self, name, target, current, apply_tolerance=True):
        error = float(target)-float(current)
        low, high = self.settings['sensor_limits'][name]
        below_range = float(current) < low
        above_range = float(current) > high
        # Goal tolerance is relative to the requested target, not the sensor
        # operating range. A small excursion beyond a configured limit is
        # acceptable when the actual goal is already within tolerance.
        if (apply_tolerance and
                abs(error) <= float(self.settings['target_tolerance'][name])):
            return 0
        if below_range and error <= 0:
            return 0  # Never command farther below the configured minimum.
        if above_range and error >= 0:
            return 0  # Never command farther above the configured maximum.
        sign = int(math.copysign(1, error))*int(self.settings['increase_pwm_sign'][name])
        band = float(self.settings['pwm']['slow_band'][name])
        fraction = min(1., abs(error)/max(1., band))
        pwm_min = int(self.settings['pwm']['min'][name])
        pwm_max = int(self.settings['pwm']['max'][name])
        magnitude = int(pwm_min + fraction*(pwm_max-pwm_min))
        return sign*magnitude

    def _wrong_direction_tolerance(self, name):
        # Ignore a single sensor fluctuation within the measured stationary
        # jitter. Persistent opposite movement is still caught by the progress
        # timeout or once it exceeds this cumulative margin.
        return max(float(self.settings['progress_wrong_direction_tolerance']),
                   float(self.settings['home_stability_tolerance'][name]))

    def _drive_targets(self, now, values, new_sample):
        if self.targets is None:
            return
        if now-self.stage_started > float(self.settings['stage_timeout_sec']):
            raise TimeoutError(f'{self.state} exceeded stage timeout')
        commands = [0, 0, 0, 0]
        # During startup, each potentiometer axis computes its own safe motion
        # toward the configured home target. Do this before the generic
        # single-axis range recovery so one slightly out-of-range pot does not
        # serialize the requested 3-axis initialization.
        if self.state == self.INITIALIZING:
            self.active_target_name = None
            self._drive_initial_pose_axes(now, values, new_sample)
            return

        if self.state in self.HARVEST_AXIS_BY_STATE:
            unrelated_out_of_range = next(
                (name for name in SENSOR_NAMES
                 if name not in self.targets and
                 (values[name] < self.settings['sensor_limits'][name][0] or
                  values[name] > self.settings['sensor_limits'][name][1]) and
                 abs(float(values[name])-float(self.settings['initial_pose'][name])) >
                 float(self.settings['target_tolerance'][name])), None)
            if unrelated_out_of_range is not None:
                raise RuntimeError(
                    f'{unrelated_out_of_range} is outside its configured range and beyond '
                    f'initial-pose tolerance during '
                    f'{self.state}; stopping instead of interrupting the '
                    f'motor {MOTOR_NUMBER[self.HARVEST_AXIS_BY_STATE[self.state]]} sequence')

        # Recover any sensor that is outside its configured operating range
        # before continuing the active stage. The Pico accepts one drive
        # command for the four axes, so recover one axis at a time.
        recovery_name = next((name for name in SENSOR_NAMES
                              if (values[name] < self.settings['sensor_limits'][name][0]
                                  or values[name] > self.settings['sensor_limits'][name][1])
                              and (name not in self.targets
                                   or abs(float(self.targets[name])-float(values[name])) >
                                   float(self.settings['target_tolerance'][name]))), None)
        if recovery_name is not None:
            self.range_recovery_active = True
            low, high = self.settings['sensor_limits'][recovery_name]
            current = values[recovery_name]
            recovery_target = low if current < low else high
            # This is a sensor-range boundary target, not the stage goal.
            # Ignore goal tolerance so an axis whose real goal is still far
            # away can recover fully into its configured operating range.
            pwm = self._pwm_for(recovery_name, recovery_target, current,
                                apply_tolerance=False)
            commands[MOTOR_NUMBER[recovery_name]-1] = pwm
            if new_sample:
                previous = self.last_progress_value.get(recovery_name)
                if previous is None:
                    self.last_progress_value[recovery_name] = current
                    self.progress_at[recovery_name] = now
                else:
                    delta = float(current)-float(previous)
                    expected_sign = 1 if recovery_target > current else -1
                    min_delta = float(self.settings['progress_min_delta'][recovery_name])
                    if abs(delta) >= min_delta:
                        if delta*expected_sign < -self._wrong_direction_tolerance(recovery_name):
                            raise RuntimeError(
                                f'{recovery_name} recovery moved farther out of range: delta={delta:g}')
                        if delta*expected_sign > 0:
                            self.progress_at[recovery_name] = now
                            self.last_progress_value[recovery_name] = current
                    if now-self.progress_at[recovery_name] > float(self.settings['progress_timeout_sec']):
                        raise TimeoutError(f'{recovery_name} made no progress back into range')
            self._set_drive(commands)
            return
        if self.range_recovery_active:
            # Recovery changes its target at the configured range boundary.
            # Rebase progress here so the intentional direction change toward
            # the stage target is not compared with the earlier recovery move.
            for name in self.targets:
                self.last_progress_value[name] = values[name]
                self.progress_at[name] = now
                self.target_stable[name] = 0
            self.range_recovery_active = False
            self.active_target_name = None

        stable_required = int(self.settings['target_stable_samples'])
        if (self.active_target_name not in self.targets or
                self.target_stable[self.active_target_name] >= stable_required):
            self.active_target_name = next(
                (name for name in self.targets
                 if self.target_stable[name] < stable_required), None)
        if self.active_target_name is None:
            self._set_drive(commands)
            if new_sample:
                self._motion_complete()
            return

        # Drive only one axis at a time. This keeps its PWM above the configured
        # minimum instead of scaling a multi-axis command to max_total_abs_pwm.
        name = self.active_target_name
        target = self.targets[name]
        current = values[name]
        error = float(target)-float(current)
        pwm = self._pwm_for(name, target, current)
        commands[MOTOR_NUMBER[name]-1] = pwm
        if new_sample:
            if pwm == 0:
                self.target_stable[name] += 1
                self.last_progress_value.pop(name, None)
                if self.target_stable[name] >= stable_required:
                    self.active_target_name = None
            else:
                self.target_stable[name] = 0
                previous = self.last_progress_value.get(name)
                if previous is None:
                    self.last_progress_value[name] = current
                    self.progress_at[name] = now
                else:
                    delta = float(current)-float(previous)
                    min_delta = float(self.settings['progress_min_delta'][name])
                    expected_sign = int(math.copysign(1, error))
                    if abs(delta) >= min_delta:
                        if delta*expected_sign < -self._wrong_direction_tolerance(name):
                            raise RuntimeError(
                                f'{name} moved in the wrong direction while driven: '
                                f'previous={previous:g}, current={current:g}, '
                                f'delta={delta:g}, pwm={pwm}, '
                                f'tolerance={self._wrong_direction_tolerance(name):g}')
                        if delta*expected_sign > 0:
                            self.progress_at[name] = now
                            self.last_progress_value[name] = current
                if now-self.progress_at[name] > float(self.settings['progress_timeout_sec']):
                    raise TimeoutError(f'{name} made no sensor progress toward {target}')
        self._set_drive(commands)
        if new_sample and all(self.target_stable[name] >= stable_required
                              for name in self.targets):
            self._set_drive([0, 0, 0, 0])
            self._motion_complete()

    def _drive_initial_pose_axes(self, now, values, new_sample):
        """Move the three potentiometer axes together during startup only."""
        commands = [0, 0, 0, 0]
        stable_required = int(self.settings['target_stable_samples'])
        for name, target in self.targets.items():
            current = values[name]
            if name == 'enc4':
                # The rail is manually homed and its encoder zeroed before
                # initialization; never move it as part of the 3-axis startup.
                if abs(float(target)-float(current)) > float(self.settings['target_tolerance'][name]):
                    raise RuntimeError('ENC4 changed after its manual zero reference')
                pwm = 0
            else:
                error = float(target)-float(current)
                pwm = self._pwm_for(name, target, current)
                commands[MOTOR_NUMBER[name]-1] = pwm

            if not new_sample:
                continue
            if pwm == 0:
                self.target_stable[name] += 1
                self.last_progress_value.pop(name, None)
                continue

            self.target_stable[name] = 0
            previous = self.last_progress_value.get(name)
            if previous is None:
                self.last_progress_value[name] = current
                self.progress_at[name] = now
                continue
            delta = float(current)-float(previous)
            min_delta = float(self.settings['progress_min_delta'][name])
            expected_sign = int(math.copysign(1, error))
            if abs(delta) >= min_delta:
                if delta*expected_sign < -self._wrong_direction_tolerance(name):
                    raise RuntimeError(f'{name} moved in the wrong direction: delta={delta:g}')
                if delta*expected_sign > 0:
                    self.progress_at[name] = now
                    self.last_progress_value[name] = current
            if now-self.progress_at[name] > float(self.settings['progress_timeout_sec']):
                raise TimeoutError(f'{name} made no sensor progress toward {target}')

        self._set_drive(commands)
        if new_sample and all(self.target_stable[name] >= stable_required
                              for name in self.targets):
            self._set_drive([0, 0, 0, 0])
            self._motion_complete()

    def _set_drive(self, values):
        values = [int(v) for v in values]
        total = sum(abs(v) for v in values)
        budget = int(self.settings['pwm'].get('max_total_abs_pwm', 255))
        if total > budget:
            active = [i for i, value in enumerate(values) if value != 0]
            motor_names = ('pot1', 'pot2', 'pot3', 'enc4')
            floors = [int(self.settings['pwm']['min'][motor_names[i]]) for i in active]
            floor_total = sum(floors)
            extra_budget = budget-floor_total
            extras = [max(0, abs(values[i])-floor)
                      for i, floor in zip(active, floors)]
            extra_total = sum(extras)
            if extra_budget < 0:
                raise RuntimeError(
                    'PWM total budget is below the configured minimums '
                    'for the active motors')
            if extra_total > 0:
                scaled = [
                    floor + (extra*extra_budget)//extra_total
                    for floor, extra in zip(floors, extras)
                ]
                for index, magnitude in zip(active, scaled):
                    values[index] = int(math.copysign(magnitude, values[index]))
        if values != getattr(self, 'last_drive', None):
            self.io.drive(values)
            self.last_drive = values
        if any(values):
            now = time.monotonic()
            if now-self.last_hb >= float(self.settings['heartbeat_period_sec']):
                self.io.heartbeat()
                self.last_hb = now

    def _motion_complete(self):
        self.targets = None
        if self.state == self.INITIALIZING:
            self.ready_pub.publish(Bool(data=True))
            self._transition(self.WAIT_ARM, 'EE initial pose confirmed')
        elif self.state == self.HARVEST_PITCH:
            # Motor 2 must finish and settle before motor 4 is started.
            self._begin_motion(self.HARVEST_EXTEND, {'enc4': self.settings['harvest_pose']['enc4']})
        elif self.state == self.HARVEST_EXTEND:
            # Motor 4 must finish and settle before motor 3 is started.
            self._begin_motion(self.HARVEST_CLOSE, {'pot3': self.settings['harvest_pose']['pot3']})
        elif self.state == self.HARVEST_CLOSE:
            self._transition(self.WAIT_RETURN, 'hook closed; requesting arm return')
            self._request_arm('pull')
        elif self.state == self.RESET_EE:
            self._transition(self.WAIT_NEXT, 'EE initial pose restored; waiting for n')
            status = self._fresh_arm_state()
            self.arm_ready = bool(status and status['state'] == 'RETURNED' and
                                  status['reason'] == 'return_complete_wait_for_n')

    def _safe_stop(self, reason):
        try:
            self.io.stop()
            self.last_drive = [0, 0, 0, 0]
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f'EE STOP command failed; Pico watchdog must stop drive: {exc}')
        self.get_logger().warning(reason)

    def _fault(self, reason):
        if self.state == self.FAULT:
            return
        self._safe_stop(reason)
        self._transition(self.FAULT, reason)
        self.ready_pub.publish(Bool(data=False))
        self.alive_pub.publish(Bool(data=False))
        if self._fresh_arm_state() is not None:
            self._request_arm('hold')

    def _abort(self):
        self._safe_stop('operator interrupted the automatic sequence')
        self._transition(self.ABORTED, 'Space pressed; waiting for operator restart')
        if self._fresh_arm_state() is not None:
            self._request_arm('hold')

    def _handle_key(self, key):
        if key == ' ' and self.state not in (self.ABORTED, self.FAULT):
            self._abort()
        elif key.lower() == 'c' and self.state == self.WAIT_HOME:
            if self.telemetry is None or self.sample_time is None or time.monotonic()-self.sample_time > float(self.settings['sensor_timeout_sec']):
                self.get_logger().warning('センサー値が新鮮ではないため原点を登録できません')
                return
            if self.sensor_stable_samples < int(self.settings['sensor_stable_samples']):
                allowed = self.settings['home_stability_tolerance']
                self.get_logger().warning(
                    f'センサー変動幅が許容値を超えているため原点を登録できません: '
                    f'span={self._home_sensor_spans()}, allowed={allowed}')
                return
            if any(int(pwm) != 0 for pwm in self.telemetry.get('pwm', [])):
                self.get_logger().warning('EE駆動中はENC4原点を登録できません')
                return
            self.io.zero_encoder()
            self.zero_sample_seq = self.sample_seq
            self._transition(self.WAIT_ZERO, 'manual retracted-reference confirmation received')
        elif key.lower() == 'n' and self.state == self.WAIT_NEXT and self.arm_ready:
            self._request_arm('resume')
            self._transition(self.WAIT_RESUME, 'n pressed; waiting for arm resume acknowledgement')
        elif key.lower() == 'n':
            self.get_logger().warning('n is accepted only after arm return and EE reset are complete')

    def _key_callback(self, msg):
        value = msg.data.strip()
        if value.lower() == 'space':
            self._handle_key(' ')
        elif len(value) == 1:
            self._handle_key(value)
        else:
            self.get_logger().warning('key input must be one key: c, n, or space')

    def _keyboard(self):
        if not self.keyboard_enabled:
            return
        ready, _, _ = select.select([self.terminal], [], [], 0)
        if ready:
            key = os.read(self.terminal.fileno(), 1).decode('ascii', errors='ignore')
            if key:
                self._handle_key(key)

    def _validate_values(self, values):
        if not isinstance(values, dict) or not isinstance(values.get('pwm'), list) or len(values['pwm']) != 4:
            raise RuntimeError('Pico status packet is malformed')
        if any(not isinstance(pwm, int) or not -255 <= pwm <= 255 for pwm in values['pwm']):
            raise RuntimeError(f'Pico PWM status is invalid: {values["pwm"]}')
        for name in ('pot1', 'pot2', 'pot3'):
            value = values.get(name)
            if not isinstance(value, int) or not 0 <= value <= 4095:
                raise RuntimeError(f'{name} sensor value is not a 12-bit ADC reading: {value}')
        encoder = values.get('enc4')
        if not isinstance(encoder, int) or not -(2**31) <= encoder < 2**31:
            raise RuntimeError(f'enc4 sensor value is not a signed 32-bit count: {encoder}')

    def _update_home_sensor_stability(self, values):
        """Accept bounded sensor jitter using the recent sample window span."""
        self.home_sensor_window.append({name: values[name] for name in SENSOR_NAMES})
        required = int(self.settings['sensor_stable_samples'])
        if len(self.home_sensor_window) < required:
            self.sensor_stable_samples = len(self.home_sensor_window)
            return
        spans = self._home_sensor_spans()
        stable = all(spans[name] <= int(self.settings['home_stability_tolerance'][name])
                     for name in SENSOR_NAMES)
        self.sensor_stable_samples = required if stable else 0

    def _home_sensor_spans(self):
        if not self.home_sensor_window:
            return None
        return {name: max(sample[name] for sample in self.home_sensor_window) -
                min(sample[name] for sample in self.home_sensor_window)
                for name in SENSOR_NAMES}

    def _tick(self):
        now = time.monotonic()
        try:
            self._keyboard()
            values, seq, sample_time = self.io.poll(now)
            self.telemetry, self.sample_seq, self.sample_time = values, seq, sample_time
            new_sample = seq != self.last_sample_seq
            self.last_sample_seq = seq
            if values is not None:
                self._validate_values(values)
                if new_sample:
                    self.valid_sensor_samples += 1
                    self._update_home_sensor_stability(values)
            if self.state not in (self.WAIT_HOME, self.WAIT_ZERO, self.ABORTED, self.FAULT):
                if values is None or sample_time is None or now-sample_time > float(self.settings['sensor_timeout_sec']):
                    raise TimeoutError('Pico sensor telemetry is missing or stale')
                if not self._arm_wait_check(now):
                    return
            if self.state == self.WAIT_HOME:
                if values is not None and self.get_parameter('backend').value == 'sim' and bool(self.get_parameter('auto_confirm_sim_home').value):
                    self.io.zero_encoder()
                    self._begin_motion(self.INITIALIZING, self.settings['initial_pose'])
                elif values is None or now-sample_time > float(self.settings['sensor_timeout_sec']):
                    self.reason = 'waiting for fresh Pico sensor telemetry'
            elif self.state == self.WAIT_ZERO:
                if new_sample and seq > getattr(self, 'zero_sample_seq', seq) and abs(values['enc4']) <= int(self.settings['target_tolerance']['enc4']):
                    self._begin_motion(self.INITIALIZING, self.settings['initial_pose'])
                elif now-self.stage_started > float(self.settings['sensor_timeout_sec'])*3:
                    raise TimeoutError('Pico did not report ENC4 zero after ZERO_ENC4')
            elif self.state in (self.INITIALIZING, self.RESET_EE, self.HARVEST_PITCH,
                                self.HARVEST_EXTEND, self.HARVEST_CLOSE):
                # Each harvest axis is commanded to its target in its own
                # stage. Once that stage completes, later load-induced
                # movement is allowed; sensor validity and configured
                # operating-range handling remain active.
                self._drive_targets(now, values, new_sample)
            elif self.state == self.WAIT_ARM:
                pass
            elif self.state == self.APPROACH:
                if self.arm_status and self.arm_status['state'] == 'HARVEST_HOLD':
                    pass  # State callback will validate completion reason, sequence and settling.
            elif self.state == self.WAIT_RETURN:
                if now-self.stage_started > float(self.settings['arm_return_timeout_sec']):
                    raise TimeoutError('arm did not finish its return in time')
                if self.request_future is not None and not self.request_future.done() and now-self.request_started > 2.:
                    raise TimeoutError('arm return request timed out')
            elif self.state == self.WAIT_NEXT:
                if self.arm_status and self.arm_status['state'] != 'RETURNED':
                    self.arm_ready = False
                elif self.arm_status and self.arm_status['state'] == 'RETURNED':
                    self.arm_ready = True
            elif self.state == self.WAIT_RESUME:
                if now-self.stage_started > 2.:
                    raise TimeoutError('arm did not acknowledge n/resume')
            if self.state in (self.HARVEST_PITCH, self.HARVEST_EXTEND, self.HARVEST_CLOSE,
                              self.WAIT_RETURN, self.RESET_EE):
                if now-self.last_hb >= float(self.settings['heartbeat_period_sec']):
                    self.io.heartbeat()
                    self.last_hb = now
            if self.state not in (self.FAULT, self.ABORTED, self.WAIT_HOME):
                self.alive_pub.publish(Bool(data=True))
            if now-self.last_diag >= .2:
                if now-self.last_info >= 1.0:
                    self.get_logger().info(
                        f'EE state={self.state}, sensors={values}, targets={self.targets}, '
                        f'drive={getattr(self, "last_drive", [0, 0, 0, 0])}, reason={self.reason}')
                    self.last_info = now
                self.state_pub.publish(String(data=json.dumps(dict(
                    state=self.state, reason=self.reason, sensor=values,
                    sensor_out_of_range=self._sensor_range_status(values),
                    home_sensor_span=self._home_sensor_spans(),
                    sensor_age_sec=None if sample_time is None else now-sample_time,
                    arm_state=None if self.arm_status is None else self.arm_status['state'],
                    arm_reason=None if self.arm_status is None else self.arm_status['reason'],
                    targets=self.targets, drive=getattr(self, 'last_drive', [0, 0, 0, 0]),
                    cycle_sequence=self.cycle_sequence), allow_nan=False)))
                self.last_diag = now
        except Exception as exc:  # noqa: BLE001
            self._fault(str(exc))

    def _sensor_range_status(self, values):
        if values is None:
            return None
        result = {}
        for name in SENSOR_NAMES:
            low, high = self.settings['sensor_limits'][name]
            value = values[name]
            if value < low:
                result[name] = dict(status='below_min', value=value, limit=low,
                                    allowed_recovery='increase_sensor_value')
            elif value > high:
                result[name] = dict(status='above_max', value=value, limit=high,
                                    allowed_recovery='decrease_sensor_value')
            else:
                result[name] = dict(status='in_range', value=value)
        return result

    def destroy_node(self):
        try:
            if rclpy.ok():
                self.ready_pub.publish(Bool(data=False))
                self.alive_pub.publish(Bool(data=False))
            self._safe_stop('node shutdown')
            self.io.close()
        finally:
            if self.terminal_settings is not None:
                try:
                    termios.tcsetattr(self.terminal.fileno(), termios.TCSADRAIN,
                                      self.terminal_settings)
                except (termios.error, OSError):
                    pass
            if self.owns_terminal:
                self.terminal.close()
            super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = AutoHarvestNode()
        executor = rclpy.executors.MultiThreadedExecutor(num_threads=2)
        executor.add_node(node)
        try:
            executor.spin()
        finally:
            executor.shutdown()
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
