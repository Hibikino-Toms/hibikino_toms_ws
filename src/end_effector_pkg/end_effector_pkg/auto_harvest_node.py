"""Sensor-feedback end-effector harvest sequence and arm-cycle coordinator."""
import json
import math
import os
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

from .ee_homing import PROFILE_NAMES, SimulatedRailHoming, parse_status
from .servo_feedback import AnalogFeedbackFilter, ServoDirectionMonitor, ServoFeedbackFilter


PARAMS_PATH = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
LEGACY_SENSOR_NAMES = ('pot1', 'pot2', 'pot3', 'enc4')
ROLL_RAIL_SERVO_SENSOR_NAMES = ('pot1', 'servo_fb', 'enc4')
# Logical DRIVE slots, not physical motor numbers in the new wiring.
MOTOR_NUMBER = {'pot1': 1, 'pot2': 2, 'pot3': 3, 'servo_fb': 3, 'enc4': 4}


def _select_profile_axis_names(mapping, profile):
    """Normalize the old logical hook key while keeping telemetry explicit."""
    if not isinstance(mapping, dict):
        return
    if profile == 'roll_rail_servo':
        if 'servo_fb' not in mapping and 'pot3' in mapping:
            mapping['servo_fb'] = mapping['pot3']  # Compatibility with old YAML only.
        mapping.pop('pot3', None)
    else:
        if 'pot3' not in mapping and 'servo_fb' in mapping:
            mapping['pot3'] = mapping['servo_fb']
        mapping.pop('servo_fb', None)


def load_settings(path, homing_only=False):
    with open(path, encoding='utf-8') as stream:
        root = yaml.safe_load(stream)
    settings = root.get('auto_harvest') if isinstance(root, dict) else None
    if not isinstance(settings, dict):
        raise ValueError('auto_harvest config must be a YAML mapping')
    result = dict(settings)
    ee_params = root.get('EE_params', {})
    if isinstance(ee_params, dict):
        result.setdefault('serial_number', ee_params.get('EE_PICO_SERIAL_NUMBER', ''))
        result.setdefault('baudrate', ee_params.get('BAUDRATE', 115200))
    profile = result.setdefault('hardware_profile', 'legacy_four_dc')
    if profile not in PROFILE_NAMES:
        raise ValueError('unknown EE hardware_profile')
    axis_names = (LEGACY_SENSOR_NAMES if profile == 'legacy_four_dc'
                  else ROLL_RAIL_SERVO_SENSOR_NAMES)
    result['active_axes'] = axis_names
    result['hook_feedback_axis'] = 'pot3' if profile == 'legacy_four_dc' else 'servo_fb'
    # Accept old YAML which called the servo ADC "pot3", but expose and
    # consume it as servo_fb for the current hardware profile.
    for key in ('initial_pose', 'harvest_pose', 'sensor_limits', 'target_tolerance',
                'increase_pwm_sign', 'progress_min_delta', 'home_stability_tolerance'):
        _select_profile_axis_names(result.get(key), profile)
    pwm_config = result.get('pwm')
    if isinstance(pwm_config, dict):
        for key in ('min', 'max', 'slow_band'):
            _select_profile_axis_names(pwm_config.get(key), profile)
    homing = result.get('encoder_homing')
    if not isinstance(homing, dict):
        raise ValueError('encoder_homing configuration is required; manual c zero is removed')
    for key in ('timeout_sec', 'progress_timeout_sec', 'initial_telemetry_timeout_sec'):
        if not math.isfinite(float(homing[key])) or float(homing[key]) <= 0:
            raise ValueError(f'encoder_homing.{key} must be positive and finite')
    if (not 1 <= abs(int(homing['retract_pwm'])) <= 255 or
            (profile == 'roll_rail_servo' and int(homing['retract_pwm']) <= 0) or
            not 1 <= float(homing['timeout_sec']) <= 60 or
            not 5 <= int(homing['debounce_ms']) <= 500 or
            not 1 <= int(homing['release_max_counts']) <= 50 or
            not 1 <= int(homing['max_travel_counts']) <= 100000 or
            not .1 <= float(homing['progress_timeout_sec']) <= float(homing['timeout_sec'])):
        raise ValueError('invalid encoder_homing PWM, debounce, timeout or travel limits')
    result['servo_calibrated'] = profile == 'legacy_four_dc'
    if profile == 'roll_rail_servo':
        roll = result.get('roll_motor', {})
        AnalogFeedbackFilter('pot1', roll.get('feedback_median_samples', 3))
        ServoDirectionMonitor(float(roll.get('direction_window_sec', .4)), 'pot1')
        servo = result.get('hook_servo', {})
        ServoFeedbackFilter(servo.get('feedback_median_samples', 3))
        ServoDirectionMonitor(float(servo.get('direction_window_sec', .6)))
        neutral_us = int(servo.get('neutral_us', 0))
        close_us = int(servo.get('close_us', 0))
        open_us = int(servo.get('open_us', 0))
        if (neutral_us != 1500 or not 1000 <= close_us <= 2000 or
                not 1000 <= open_us <= 2000 or close_us == neutral_us or
                open_us == neutral_us or close_us == open_us):
            raise ValueError('hook_servo pulses must be distinct valid values in the 1000-2000 us range')
        if not homing_only and (close_us != 1600 or open_us != 1350):
            raise ValueError('hook_servo pulses must match the current Pico profile (neutral=1500, close=1600, open=1350 us); use homing_only for rail homing')
        result['servo_calibrated'] = servo.get('calibration_valid') is True
        if result['servo_calibrated']:
            opened, closed = servo.get('open_feedback'), servo.get('closed_feedback')
            if (type(opened) is not int or type(closed) is not int or
                    not 0 <= opened <= 4095 or not 0 <= closed <= 4095 or opened == closed):
                raise ValueError('calibrate two distinct, non-wrapping hook servo feedback endpoints')
            hook_axis = result['hook_feedback_axis']
            result['initial_pose'] = dict(result['initial_pose'], **{hook_axis: opened})
            result['harvest_pose'] = dict(result['harvest_pose'], **{hook_axis: closed})
            result['increase_pwm_sign'] = dict(result['increase_pwm_sign'],
                                               **{hook_axis: 1 if closed > opened else -1},
                                               enc4=1)
        else:
            # No feedback target is issued until the servo endpoints are calibrated.
            hook_axis = result['hook_feedback_axis']
            result['initial_pose'] = dict(result['initial_pose'], **{hook_axis: None})
            result['harvest_pose'] = dict(result['harvest_pose'], **{hook_axis: None})
        if result['initial_pose'].get('enc4') != 0:
            raise ValueError('rail initial_pose.enc4 must be the homed zero')
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
            missing = [name for name in axis_names if name not in configured]
            if missing:
                raise ValueError(f'auto_harvest.pwm.{bound} is missing axes: {missing}')
            result['pwm'][bound] = {name: int(configured[name]) for name in axis_names}
        else:
            scalar = int(configured)
            result['pwm'][bound] = {name: scalar for name in axis_names}
    if int(result.get('sensor_stable_samples', 0)) < 1:
        raise ValueError('auto_harvest.sensor_stable_samples must be at least 1')
    for name in axis_names:
        low, high = result['sensor_limits'][name]
        target = result['initial_pose'][name]
        if (name in result['active_axes'] and
                not (name == result['hook_feedback_axis'] and not result['servo_calibrated']) and
                not low <= target <= high):
            raise ValueError(f'initial target for {name} is outside configured limits')
        tol = int(result['target_tolerance'][name])
        sign = int(result['increase_pwm_sign'][name])
        if tol < 0 or sign not in (-1, 1):
            raise ValueError(f'invalid tolerance or direction for {name}')
        if int(result['home_stability_tolerance'][name]) < 0:
            raise ValueError(f'home stability tolerance for {name} must not be negative')
    for name in axis_names:
        min_pwm = int(result['pwm']['min'][name])
        max_pwm = int(result['pwm']['max'][name])
        if not 1 <= min_pwm <= max_pwm <= 255:
            raise ValueError(
                f'PWM limits for {name} must satisfy 1 <= min <= max <= 255')
    total_pwm_limit = int(result['pwm'].get('max_total_abs_pwm', 255))
    init_minimum_total = sum(int(result['pwm']['min'][name])
                             for name in result['active_axes'] if name != 'enc4')
    if total_pwm_limit < init_minimum_total:
        raise ValueError(
            'pwm.max_total_abs_pwm must be at least the sum of the '
            'fitted non-rail axis minimum PWMs for EE initialization')
    if not (result['pwm']['min']['enc4'] <= abs(int(homing['retract_pwm'])) <=
            result['pwm']['max']['enc4']):
        raise ValueError('encoder_homing.retract_pwm must respect the rail PWM bounds')
    if float(result['heartbeat_period_sec']) >= float(result['serial_watchdog_sec'])/2.:
        raise ValueError('host heartbeat must run at least twice as often as Pico watchdog')
    if profile == 'roll_rail_servo' and abs(float(result['serial_watchdog_sec'])-.6) > 1e-9:
        raise ValueError('serial_watchdog_sec must match the Pico firmware: 0.6 seconds')
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
        self.servo_feedback_filter = ServoFeedbackFilter(
            settings.get('hook_servo', {}).get('feedback_median_samples', 3))
        self.roll_feedback_filter = (AnalogFeedbackFilter('pot1', settings.get('roll_motor', {}).get('feedback_median_samples', 3))
                                     if settings['hardware_profile'] == 'roll_rail_servo' else None)

    def poll(self, now):
        with self.lock:
            count = self.port.in_waiting
            if count:
                self.buffer.extend(self.port.read(min(count, 4096)))
            while b'\n' in self.buffer:
                raw, _, rest = self.buffer.partition(b'\n')
                self.buffer = bytearray(rest)
                decoded = parse_status(raw.decode('ascii', errors='ignore'))
                if decoded is not None:
                    if self.roll_feedback_filter:
                        decoded = self.roll_feedback_filter.update(decoded)
                    self.latest = self.servo_feedback_filter.update(decoded)
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

    def home_encoder(self, request_id, cfg):
        self.send('HOME_ENC4 ' + ','.join(map(str, (
            request_id, int(cfg['retract_pwm']), round(cfg['timeout_sec']*1000),
            int(cfg['debounce_ms']), int(cfg['release_max_counts']),
            int(cfg['max_travel_counts']), round(cfg['progress_timeout_sec']*1000)))))

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
        self.values = {key: int(value) if value is not None else 2048
                       for key, value in settings['initial_pose'].items()
                       if key in settings['active_axes']}
        self.drive_values = [0, 0, 0, 0]
        self.sample_seq = 0
        self.last_sample = time.monotonic()
        self.last_update = self.last_sample
        self.rate = float(settings.get('simulated_counts_per_sec', 900.))
        self.rail_rate = float(settings.get('simulated_encoder_counts_per_sec', 30.))
        self.physical_rail = -10.  # Reset ENC4=0 does not imply a retracted rail.
        self.home = SimulatedRailHoming()
        self.last_host_time = self.last_sample
        self.servo_feedback_filter = ServoFeedbackFilter(
            settings.get('hook_servo', {}).get('feedback_median_samples', 3))
        self.roll_feedback_filter = (AnalogFeedbackFilter('pot1', settings.get('roll_motor', {}).get('feedback_median_samples', 3))
                                     if settings['hardware_profile'] == 'roll_rail_servo' else None)

    def poll(self, now):
        dt = min(.1, max(0., now-self.last_update))
        self.last_update = now
        if ((self.home.active or any(self.drive_values)) and
                now-self.last_host_time > self.settings['serial_watchdog_sec']):
            self.home.cancel('HOST_TIMEOUT')
            self.drive_values = [0, 0, 0, 0]
        homing_at_start = self.home.active
        if homing_at_start:
            # Model the Pico's local switch loop, not a ROS-rate hard-stop.
            steps = max(1, math.ceil(dt/.001))
            for step in range(steps):
                local_time = now-dt+(step+1)*dt/steps
                old = self.physical_rail
                direction = 1 if self.settings['hardware_profile'] == 'roll_rail_servo' else self.settings['increase_pwm_sign']['enc4']
                self.physical_rail = max(-50., min(0., old+self.home.output*direction*self.rail_rate/255.*dt/steps))
                self.values['enc4'] += self.physical_rail-old
                self.home.update(local_time, int(round(self.values['enc4'])), self.physical_rail >= 0.)
                self.drive_values = [0, 0, 0, self.home.output]
                if not self.home.active:
                    if self.home.phase == 'DONE':
                        self.values['enc4'] = 0
                    break
        for name in self.settings['active_axes']:
            if homing_at_start:
                break  # Homing owns every output; no other axis may move.
            index = MOTOR_NUMBER[name]
            pwm = self.drive_values[index-1]
            delta = pwm * self.settings['increase_pwm_sign'][name] * self.rate/255.*dt
            low, high = self.settings['sensor_limits'][name]
            if name == 'enc4':
                # Compact firmware normalizes encoder counts to +retract.
                direction = 1 if self.settings['hardware_profile'] == 'roll_rail_servo' else self.settings['increase_pwm_sign']['enc4']
                delta = pwm*direction*self.rail_rate/255.*dt
                old = self.physical_rail
                self.physical_rail = max(float(low), min(0., old+delta))
                self.values[name] += self.physical_rail-old
            else:
                self.values[name] = max(low, min(high, self.values[name]+delta))
        self.last_sample = now
        self.sample_seq += 1
        values = {name: int(round(value)) for name, value in self.values.items()}
        servo_pwm = self.drive_values[2]
        servo = self.settings.get('hook_servo', {})
        neutral_us = int(servo.get('neutral_us', 1500))
        endpoint = int(servo.get('close_us', 1600) if servo_pwm >= 0
                       else servo.get('open_us', 1350))
        servo_us = neutral_us + int((endpoint-neutral_us)*abs(servo_pwm)/255.)
        if self.roll_feedback_filter:
            values = self.roll_feedback_filter.update(values)
        values = self.servo_feedback_filter.update(values)
        return dict(values, pwm=list(self.drive_values), servo_us=servo_us,
                    profile=PROFILE_NAMES[self.settings['hardware_profile']],
                    homing=self.home.status(self.physical_rail >= 0.)), self.sample_seq, self.last_sample

    def drive(self, values):
        self.drive_values = [max(-255, min(255, int(v))) for v in values]
        self.last_host_time = time.monotonic()

    def heartbeat(self):
        self.last_host_time = time.monotonic()

    def home_encoder(self, request_id, cfg):
        self.home.start(request_id, cfg, time.monotonic(), int(round(self.values['enc4'])), self.physical_rail >= 0.)
        self.drive_values = [0, 0, 0, self.home.output]
        self.last_host_time = time.monotonic()

    def stop(self):
        self.home.cancel()
        self.drive_values = [0, 0, 0, 0]
        self.last_host_time = time.monotonic()

    def close(self):
        self.stop()


class AutoHarvestNode(Node):
    """One ROS node owns the EE serial link and its automatic state machine."""
    WAIT_HOME = 'WAIT_ENCODER_HOME'
    HOMING = 'ENCODER_HOMING'
    WAIT_CALIBRATION = 'WAIT_SERVO_CALIBRATION'
    HOMING_ONLY_DONE = 'HOMING_ONLY_DONE'
    INITIALIZING = 'EE_INITIALIZING'
    WAIT_ARM = 'WAIT_ARM_STARTUP'
    APPROACH = 'APPROACH'
    HARVEST_PITCH = 'HARVEST_PITCH'
    HARVEST_EXTEND = 'HARVEST_EXTEND'
    HARVEST_CLOSE = 'HARVEST_CLOSE'
    HARVEST_AXIS_BY_STATE = {
        HARVEST_PITCH: 'pot2',  # Legacy-only pitch; absent in the new wiring.
        HARVEST_EXTEND: 'enc4',  # Logical slot 4, physical M2 for roll_rail_servo.
    }
    WAIT_RETURN = 'WAIT_ARM_RETURN'
    WAIT_LIFT = 'WAIT_POST_ARRIVAL_LIFT'
    RESET_RETRACT = 'EE_STOW_RETRACT'
    RESET_OPEN = 'EE_STOW_OPEN'
    WAIT_Z_HOME = 'WAIT_Z_HOME'
    RESET_EE = 'EE_RESET'
    WAIT_NEXT = 'WAIT_NEXT_CYCLE'
    WAIT_RESUME = 'WAIT_ARM_RESUME'
    ABORTED = 'ABORTED'
    FAULT = 'FAULT'

    def __init__(self):
        super().__init__('auto_harvest')
        self.declare_parameter('config_file', PARAMS_PATH)
        self.declare_parameter('backend', 'sim')
        self.declare_parameter('keyboard_enabled', True)
        self.declare_parameter('auto_confirm_sim_home', True)
        self.declare_parameter('homing_only', False)
        self.declare_parameter('sequenced_z_cycle', False)
        self.sequenced_z_cycle = bool(self.get_parameter('sequenced_z_cycle').value)
        self.homing_only = bool(self.get_parameter('homing_only').value)
        config_path = self.get_parameter('config_file').value or PARAMS_PATH
        if not config_path:
            raise RuntimeError('Set config_file (default: module/set_params.yaml)')
        self.settings = load_settings(config_path, homing_only=self.homing_only)
        for key, default in (('arm_lift_timeout_sec', 45.), ('z_home_timeout_sec', 140.)):
            self.settings.setdefault(key, default)
            if not math.isfinite(float(self.settings[key])) or float(self.settings[key]) <= 0:
                raise ValueError(f'auto_harvest.{key} must be positive and finite')
        self.active_axes = self.settings['active_axes']
        self.servo_direction = ServoDirectionMonitor(float(
            self.settings.get('hook_servo', {}).get('direction_window_sec', .6)))
        self.roll_direction = ServoDirectionMonitor(float(
            self.settings.get('roll_motor', {}).get('direction_window_sec', .4)), 'pot1')
        backend = str(self.get_parameter('backend').value)
        self.io = SimulatedPico(self.settings) if backend == 'sim' else SerialPico(self.settings) if backend == 'serial' else None
        if self.io is None:
            raise ValueError('backend must be sim or serial')
        self.state = self.WAIT_HOME
        self.reason = 'waiting for switch-capable Pico telemetry before automatic rail homing'
        self.homing_request_id = None
        self.homing_verified = False
        self.targets = None
        self.stage_started = time.monotonic()
        self.arm_start_wait = self.stage_started
        self.target_stable = {name: 0 for name in self.active_axes}
        self.last_sample_seq = -1
        self.valid_sensor_samples = 0
        self.sensor_stable_samples = 0
        self.home_sensor_window = deque(maxlen=int(self.settings['sensor_stable_samples']))
        self.progress_at = {name: time.monotonic() for name in self.active_axes}
        self.last_progress_value = {}
        self.last_progress_direction = {}
        self.servo_direction.reset()
        self.roll_direction.reset()
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
                    '/end_effector/auto/key for c (sequenced cycle), n (legacy) or space.')
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
                            for action in ('hold', 'pull', 'resume', 'lift', 'home_z')}
        self.ready_pub.publish(Bool(data=False))
        self.io.stop()
        self.timer = self.create_timer(1./float(self.settings['control_rate_hz']), self._tick)
        self.get_logger().info(
            f'Automatic EE harvest started: backend={backend}, state={self.state}. '
            'Rail homes automatically using the NC switch. '
            + ('Space=abort and hold, c=next cycle only after EE stow and Z homing.'
               if self.sequenced_z_cycle else
               'Space=abort and hold, n=resume only after cycle reset; c does not zero ENC4.'))

    def _allowed_arm_states(self):
        return {
            self.APPROACH: ('APPROACH', 'HARVEST_HOLD'),
            self.WAIT_LIFT: ('HARVEST_HOLD', 'LIFTING'),
            self.HARVEST_PITCH: ('HARVEST_HOLD',),
            self.HARVEST_EXTEND: ('HARVEST_HOLD',),
            self.HARVEST_CLOSE: ('HARVEST_HOLD',),
            self.WAIT_RETURN: ('HARVEST_HOLD', 'RETURNING', 'RETURNED'),
            self.RESET_EE: ('RETURNED',),
            self.RESET_RETRACT: ('RETURNED',),
            self.RESET_OPEN: ('RETURNED',),
            self.WAIT_Z_HOME: ('RETURNED', 'Z_HOMING', 'CYCLE_READY'),
            self.WAIT_NEXT: ('CYCLE_READY',) if self.sequenced_z_cycle else ('RETURNED',),
            self.WAIT_RESUME: ('CYCLE_READY', 'APPROACH') if self.sequenced_z_cycle else ('RETURNED', 'APPROACH'),
        }.get(self.state)

    def _arm_state_callback(self, msg):
        try:
            data = json.loads(msg.data)
            state = str(data['state'])
            seq = int(data['sequence'])
            stamp = float(data['stamp'])
            if state not in ('STARTUP', 'APPROACH', 'HARVEST_HOLD', 'LIFTING', 'Z_HOMING',
                             'CYCLE_READY', 'RETURNING', 'RETURNED', 'FAULT', 'DISABLED') or not math.isfinite(stamp):
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
            if self.sequenced_z_cycle and data.get('automatic_sequence') is not True:
                self._fault('sequenced EE cycle requires harvest_cycle.automatic_sequence=true in tracker config')
                return
            if state == 'FAULT' and self.state not in (self.FAULT, self.ABORTED):
                self._fault(f'arm entered FAULT: {self.arm_status["reason"]}')
                return
            allowed = self._allowed_arm_states()
            if allowed is not None and state not in allowed:
                self._fault(f'unexpected arm state during {self.state}: {state}')
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
                    if self.sequenced_z_cycle:
                        self._transition(self.WAIT_LIFT, 'approach complete; requesting bounded Z lift')
                        self._request_arm('lift')
                    else:
                        self._begin_motion(self.HARVEST_PITCH,
                                           {'pot2': self.settings['harvest_pose'].get('pot2')})
            if (self.state == self.WAIT_LIFT and state == 'HARVEST_HOLD' and
                    self.arm_status['reason'] == 'post_arrival_lift_complete' and
                    seq > self.cycle_sequence and self.arm_status['hold_ready']):
                self._begin_motion(self.HARVEST_EXTEND, {'enc4': self.settings['harvest_pose']['enc4']})
            return_reason = 'return_complete_wait_for_ee_reset' if self.sequenced_z_cycle else 'return_complete_wait_for_n'
            if (self.state == self.WAIT_RETURN and state == 'RETURNED' and self.arm_status['reason'] == return_reason
                    and (not self.sequenced_z_cycle or self.arm_status['hold_ready'])):
                if self.sequenced_z_cycle:
                    self._begin_motion(self.RESET_RETRACT, {'enc4': self.settings['initial_pose']['enc4']})
                else:
                    self._begin_motion(self.RESET_EE, self.settings['initial_pose'])
            if (self.state == self.WAIT_Z_HOME and state == 'CYCLE_READY' and
                    self.arm_status['reason'] == 'cycle_complete_wait_for_c' and self.arm_status['hold_ready']):
                self._transition(self.WAIT_NEXT, 'EE stowed and Z homed; waiting for c')
                self.arm_ready = True
            if self.state == self.WAIT_NEXT and not self.sequenced_z_cycle and state == 'RETURNED' and self.arm_status['reason'] == return_reason:
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
        self.target_stable = {name: 0 for name in self.active_axes}
        self.progress_at = {name: self.stage_started for name in self.active_axes}
        self.last_progress_value = {}
        self.last_progress_direction = {}
        self.servo_direction.reset()
        self.roll_direction.reset()
        self.range_recovery_active = False
        self.active_target_name = None
        self.targets = None
        self.get_logger().info(f'Auto harvest: {state} ({reason})')

    def _begin_motion(self, state, targets):
        if state == self.HARVEST_PITCH and 'pot2' not in self.active_axes:
            self._begin_motion(self.HARVEST_EXTEND,
                               {'enc4': self.settings['harvest_pose']['enc4']})
            return
        targets = {name: target for name, target in targets.items() if name in self.active_axes}
        # Harvest stages must remain strictly sequential. The Pico stops other
        # axes when it receives a drive command, so each stage owns one motor.
        expected_axis = self.HARVEST_AXIS_BY_STATE.get(
            state, 'enc4' if state == self.RESET_RETRACT else
            self.settings['hook_feedback_axis'] if state in (self.HARVEST_CLOSE, self.RESET_OPEN) else None)
        if expected_axis is not None and (len(targets) != 1 or expected_axis not in targets):
            self._fault(
                f'{state} must move only {expected_axis} '
                f'(logical DRIVE slot {MOTOR_NUMBER[expected_axis]}); got {list(targets)}')
            return
        for name, target in targets.items():
            low, high = self.settings['sensor_limits'][name]
            if target is None or not math.isfinite(float(target)) or not low <= float(target) <= high:
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
        if self.state == self.WAIT_ARM and now-self.arm_start_wait > float(self.settings['arm_startup_timeout_sec']):
            self._fault('arm startup completion timeout')
            return False
        if self.state == self.WAIT_ARM and self._fresh_arm_state() is None:
            if now-self.arm_start_wait > float(self.settings['arm_startup_timeout_sec']):
                self._fault('arm startup-state heartbeat timeout')
                return False
            return True
        allowed = self._allowed_arm_states()
        if self.state == self.WAIT_ARM or allowed is not None:
            if self._fresh_arm_state() is None:
                self._fault('arm harvest-state heartbeat lost')
                return False
            status = self._fresh_arm_state()
            if allowed is not None and status['state'] not in allowed:
                self._fault(f'unexpected arm state during {self.state}: {status["state"]}')
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

    def _direction_monitor(self, name):
        if name == 'servo_fb':
            return self.servo_direction
        if name == 'pot1' and self.settings['hardware_profile'] == 'roll_rail_servo':
            return self.roll_direction
        return None

    def _observe_servo_direction(self, name, current, expected_sign, now):
        monitor = self._direction_monitor(name)
        if monitor:
            monitor.observe(now, current, expected_sign, self._wrong_direction_tolerance(name))

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

        harvest_axis_by_state = dict(
            self.HARVEST_AXIS_BY_STATE,
            **{self.HARVEST_CLOSE: self.settings['hook_feedback_axis'],
               self.RESET_RETRACT: 'enc4', self.RESET_OPEN: self.settings['hook_feedback_axis']})
        if self.state in harvest_axis_by_state:
            unrelated_out_of_range = next(
                (name for name in self.active_axes
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
                    f'logical slot {MOTOR_NUMBER[harvest_axis_by_state[self.state]]} sequence')

        # Recover any sensor that is outside its configured operating range
        # before continuing the active stage. The Pico accepts one drive
        # command for the four axes, so recover one axis at a time.
        recovery_name = next((name for name in self.active_axes
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
                self._observe_servo_direction(
                    recovery_name, current, 1 if recovery_target > current else -1, now)
                previous = self.last_progress_value.get(recovery_name)
                expected_sign = 1 if recovery_target > current else -1
                if self.last_progress_direction.get(recovery_name) != expected_sign:
                    previous = None  # First sample after an intentional reversal.
                self.last_progress_direction[recovery_name] = expected_sign
                if previous is None:
                    self.last_progress_value[recovery_name] = current
                    self.progress_at[recovery_name] = now
                else:
                    delta = float(current)-float(previous)
                    min_delta = float(self.settings['progress_min_delta'][recovery_name])
                    if abs(delta) >= min_delta:
                        if (self._direction_monitor(recovery_name) is None and
                                delta*expected_sign < -self._wrong_direction_tolerance(recovery_name)):
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
                if self._direction_monitor(name):
                    self._direction_monitor(name).reset()
                self.target_stable[name] += 1
                self.last_progress_value.pop(name, None)
                if self.target_stable[name] >= stable_required:
                    self.active_target_name = None
            else:
                self.target_stable[name] = 0
                previous = self.last_progress_value.get(name)
                expected_sign = int(math.copysign(1, error))
                self._observe_servo_direction(name, current, expected_sign, now)
                if self.last_progress_direction.get(name) != expected_sign:
                    previous = None
                self.last_progress_direction[name] = expected_sign
                if previous is None:
                    self.last_progress_value[name] = current
                    self.progress_at[name] = now
                else:
                    delta = float(current)-float(previous)
                    min_delta = float(self.settings['progress_min_delta'][name])
                    if abs(delta) >= min_delta:
                        if (self._direction_monitor(name) is None and
                                delta*expected_sign < -self._wrong_direction_tolerance(name)):
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
        """Initialize only fitted axes; the homed rail must remain stopped."""
        commands = [0, 0, 0, 0]
        stable_required = int(self.settings['target_stable_samples'])
        for name, target in self.targets.items():
            current = values[name]
            if name == 'enc4':
                # The switch homing has already zeroed the rail.
                if abs(float(target)-float(current)) > float(self.settings['target_tolerance'][name]):
                    raise RuntimeError('ENC4 changed after its switch home reference')
                pwm = 0
            else:
                error = float(target)-float(current)
                pwm = self._pwm_for(name, target, current)
                commands[MOTOR_NUMBER[name]-1] = pwm

            if not new_sample:
                continue
            if pwm == 0:
                if self._direction_monitor(name):
                    self._direction_monitor(name).reset()
                self.target_stable[name] += 1
                self.last_progress_value.pop(name, None)
                continue

            self.target_stable[name] = 0
            previous = self.last_progress_value.get(name)
            expected_sign = int(math.copysign(1, error))
            self._observe_servo_direction(name, current, expected_sign, now)
            if self.last_progress_direction.get(name) != expected_sign:
                previous = None
            self.last_progress_direction[name] = expected_sign
            if previous is None:
                self.last_progress_value[name] = current
                self.progress_at[name] = now
                continue
            delta = float(current)-float(previous)
            min_delta = float(self.settings['progress_min_delta'][name])
            if abs(delta) >= min_delta:
                if (self._direction_monitor(name) is None and
                        delta*expected_sign < -self._wrong_direction_tolerance(name)):
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
            motor_names = ('pot1', 'pot2', self.settings['hook_feedback_axis'], 'enc4')
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
            # Legacy pitch must settle before rail extension starts.
            self._begin_motion(self.HARVEST_EXTEND, {'enc4': self.settings['harvest_pose']['enc4']})
        elif self.state == self.HARVEST_EXTEND:
            # Rail extension must settle before hook closure starts.
            hook_axis = self.settings['hook_feedback_axis']
            self._begin_motion(self.HARVEST_CLOSE,
                               {hook_axis: self.settings['harvest_pose'][hook_axis]})
        elif self.state == self.HARVEST_CLOSE:
            self._transition(self.WAIT_RETURN, 'hook closed; requesting arm return')
            self._request_arm('pull')
        elif self.state == self.RESET_RETRACT:
            hook_axis = self.settings['hook_feedback_axis']
            self._begin_motion(self.RESET_OPEN, {hook_axis: self.settings['initial_pose'][hook_axis]})
        elif self.state == self.RESET_OPEN:
            self._transition(self.WAIT_Z_HOME, 'rail retracted and hook opened; requesting Z home')
            self._request_arm('home_z')
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
        self.ready_pub.publish(Bool(data=False))
        self.alive_pub.publish(Bool(data=False))
        if self._fresh_arm_state() is not None:
            self._request_arm('hold')

    def _handle_key(self, key):
        if key == ' ' and self.state not in (self.ABORTED, self.FAULT):
            self._abort()
        elif self.sequenced_z_cycle and key.lower() == 'c':
            status = self._fresh_arm_state()
            if (self.state == self.WAIT_NEXT and self.arm_ready and status is not None and
                    status['state'] == 'CYCLE_READY' and status['hold_ready']):
                self.arm_ready = False
                self._transition(self.WAIT_RESUME, 'c pressed; waiting for arm resume acknowledgement')
                self._request_arm('resume')
            else:
                self.get_logger().warning('c is accepted only after EE stow and Z homing; input was discarded')
        elif key.lower() == 'c':
            self.get_logger().warning('cで原点を登録する機能は廃止しました。原点はリミット検出で設定します')
        elif key.lower() == 'n' and not self.sequenced_z_cycle and self.state == self.WAIT_NEXT and self.arm_ready:
            self._request_arm('resume')
            self._transition(self.WAIT_RESUME, 'n pressed; waiting for arm resume acknowledgement')
        elif key.lower() == 'n':
            self.get_logger().warning('use c after EE stow and Z homing' if self.sequenced_z_cycle else
                                      'n is accepted only after arm return and EE reset are complete')

    def _key_callback(self, msg):
        value = msg.data.strip()
        if value.lower() == 'space':
            self._handle_key(' ')
        elif len(value) == 1:
            self._handle_key(value)
        else:
            self.get_logger().warning('key input must be c (sequenced cycle), n (legacy) or space')

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
        for name in self.active_axes:
            if name == 'enc4':
                continue
            value = values.get(name)
            if not isinstance(value, int) or not 0 <= value <= 4095:
                raise RuntimeError(f'{name} sensor value is not a 12-bit ADC reading: {value}')
        encoder = values.get('enc4')
        if not isinstance(encoder, int) or not -(2**31) <= encoder < 2**31:
            raise RuntimeError(f'enc4 sensor value is not a signed 32-bit count: {encoder}')

    def _update_home_sensor_stability(self, values):
        """Accept bounded sensor jitter using the recent sample window span."""
        self.home_sensor_window.append({name: values[name] for name in self.active_axes})
        required = int(self.settings['sensor_stable_samples'])
        if len(self.home_sensor_window) < required:
            self.sensor_stable_samples = len(self.home_sensor_window)
            return
        spans = self._home_sensor_spans()
        stable = all(spans[name] <= int(self.settings['home_stability_tolerance'][name])
                     for name in self.active_axes)
        self.sensor_stable_samples = required if stable else 0

    def _home_sensor_spans(self):
        if not self.home_sensor_window:
            return None
        return {name: max(sample[name] for sample in self.home_sensor_window) -
                min(sample[name] for sample in self.home_sensor_window)
                for name in self.active_axes}

    def _request_homing(self, values, now):
        if values.get('profile') != PROFILE_NAMES[self.settings['hardware_profile']]:
            raise RuntimeError('Pico hardware profile mismatch; install the new GP19 limit firmware')
        if not values.get('homing', {}).get('supported'):
            raise RuntimeError('Pico firmware lacks NC-switch homing; c/ZERO_ENC4 fallback is disabled')
        if any(values['pwm']):
            raise RuntimeError('Pico outputs must be stopped before rail homing')
        self.homing_request_id = time.monotonic_ns() % 2000000000 + 1
        self.io.home_encoder(self.homing_request_id, self.settings['encoder_homing'])
        self._transition(self.HOMING, 'retracting rail to the NC limit switch (GP19)')

    def _monitor_homing(self, values, new_sample, now):
        elapsed = now-self.stage_started
        home = values.get('homing', {})
        if not home.get('supported'):
            raise RuntimeError('Pico lost homing-capable telemetry')
        if elapsed > float(self.settings['encoder_homing']['timeout_sec']) + float(self.settings['sensor_timeout_sec']):
            raise TimeoutError('Pico rail homing did not complete before its deadline')
        if home.get('request_id') != self.homing_request_id:
            if elapsed > float(self.settings['sensor_timeout_sec'])*3:
                raise TimeoutError('Pico did not acknowledge this rail homing request')
            return
        self.last_drive = list(values['pwm'])
        if any(values['pwm'][:3]):
            raise RuntimeError('non-rail EE output active during rail homing')
        if self.settings['hardware_profile'] == 'roll_rail_servo' and values.get('servo_us') != 1500:
            raise RuntimeError('hook servo must remain at 1500us during rail homing')
        if home.get('phase') in ('FAULT', 'CANCELLED'):
            raise RuntimeError(f'rail homing stopped: {home.get("error", "unknown")}')
        if home.get('phase') == 'DONE' and new_sample:
            if (not home.get('limit_open') or home.get('encoder_sign') not in (-1, 1) or
                    any(values['pwm']) or abs(values['enc4']) > self.settings['target_tolerance']['enc4']):
                raise RuntimeError('invalid rail home completion: switch, encoder reference or stopped outputs')
            self.homing_verified = True
            self._safe_stop('rail limit confirmed; ENC4 zero reference verified')
            if self.homing_only:
                self._transition(self.HOMING_ONLY_DONE,
                    'homing-only requested; rail reference confirmed and all EE outputs stopped')
            elif not self.settings['servo_calibrated']:
                self._transition(self.WAIT_CALIBRATION,
                    'rail homed; hook servo stopped at 1500us: set open/closed FB values '
                    'and hook_servo.calibration_valid in YAML, then restart')
            else:
                self._begin_motion(self.INITIALIZING, self.settings['initial_pose'])
        elif home.get('phase') not in ('RELEASE', 'SEEK', 'CONTACT', 'DONE'):
            raise RuntimeError(f'unexpected Pico homing phase: {home.get("phase")}')

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
            if self.state not in (self.WAIT_HOME, self.ABORTED, self.FAULT):
                if values is None or sample_time is None or now-sample_time > float(self.settings['sensor_timeout_sec']):
                    raise TimeoutError('Pico sensor telemetry is missing or stale')
                if not self._arm_wait_check(now):
                    return
            if self.state == self.WAIT_HOME:
                if now-self.stage_started > float(self.settings['encoder_homing']['initial_telemetry_timeout_sec']):
                    raise TimeoutError('no fresh switch-capable Pico telemetry before automatic homing')
                if values is None or sample_time is None or now-sample_time > float(self.settings['sensor_timeout_sec']):
                    self.reason = 'waiting for fresh Pico sensor telemetry'
                elif new_sample:
                    self._request_homing(values, now)
            elif self.state == self.HOMING:
                self._monitor_homing(values, new_sample, now)
            elif self.state == self.WAIT_CALIBRATION:
                pass  # Restart after real hook feedback endpoints are configured.
            elif self.state in (self.INITIALIZING, self.RESET_EE, self.RESET_RETRACT, self.RESET_OPEN, self.HARVEST_PITCH,
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
            elif self.state in (self.WAIT_LIFT, self.WAIT_Z_HOME):
                key = 'arm_lift_timeout_sec' if self.state == self.WAIT_LIFT else 'z_home_timeout_sec'
                if now-self.stage_started > float(self.settings[key]):
                    raise TimeoutError(f'{self.state} completion timeout')
                if self.request_future is not None and not self.request_future.done() and now-self.request_started > 2.:
                    raise TimeoutError(f'{self.state} service acknowledgement timeout')
            elif self.state == self.WAIT_NEXT:
                ready_state = 'CYCLE_READY' if self.sequenced_z_cycle else 'RETURNED'
                self.arm_ready = bool(self.arm_status and self.arm_status['state'] == ready_state
                                      and (not self.sequenced_z_cycle or self.arm_status['hold_ready']))
            elif self.state == self.WAIT_RESUME:
                if now-self.stage_started > 2.:
                    raise TimeoutError('arm did not acknowledge cycle resume')
            if self.state in (self.HOMING, self.HARVEST_PITCH, self.HARVEST_EXTEND, self.HARVEST_CLOSE,
                              self.WAIT_RETURN, self.RESET_EE, self.RESET_RETRACT, self.RESET_OPEN,
                              self.WAIT_LIFT, self.WAIT_Z_HOME):
                if now-self.last_hb >= float(self.settings['heartbeat_period_sec']):
                    self.io.heartbeat()
                    self.last_hb = now
            if self.state not in (self.FAULT, self.ABORTED, self.WAIT_HOME, self.HOMING, self.WAIT_CALIBRATION):
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
                    hardware_profile=self.settings['hardware_profile'],
                    sequenced_z_cycle=self.sequenced_z_cycle,
                    homing_verified=self.homing_verified,
                    homing=None if values is None else values.get('homing'),
                    servo_calibrated=self.settings['servo_calibrated'],
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
        for name in self.active_axes:
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
