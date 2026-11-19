"""Discrete Z corrections with exclusive ownership of Z and the planar arm.

Public distances are metres. Firmware position is a pulse-count estimate, not
an independent encoder measurement. Serial I/O is owned by the tracker timer.
"""
import math
import time
from collections import deque


def _home_speed(config):
    speed = float(config.get('home_speed_m_s', .005))
    if not math.isfinite(speed) or not .0005 <= speed <= .020:
        raise ValueError('z_tracking.home_speed_m_s must be within 0.0005..0.020 m/s')
    return speed


class SimulatedZBackend:
    def __init__(self, config):
        self.position = float(config.get('sim_initial_position_m', .225))
        self.homed = bool(config.get('sim_homed', True))
        self.target = self.position
        self.speed = float(config.get('speed_m_s', .01))
        self.home_speed = _home_speed(config)
        self.busy = False
        self.command_id = 0
        self.last = None
        self.state = None

    def tick(self, now):
        dt = 0. if self.last is None else max(0., min(.2, now-self.last))
        self.last = now
        delta = max(-self.speed*dt, min(self.speed*dt, self.target-self.position))
        self.position += delta
        if abs(self.target-self.position) < 1e-8:
            self.busy = False
        self.state = dict(position_m=self.position, homed=self.homed, busy=self.busy,
                          command_id=self.command_id, fault='NONE', position_source='simulated',
                          received_monotonic=now)
        return self.state

    def move(self, target, speed):
        self.command_id += 1
        self.target, self.speed, self.busy = target, speed, True
        return self.command_id

    def home(self):
        self.homed = True
        return self.move(.005, self.home_speed)

    def stop(self):
        self.target = self.position
        self.busy = False

    def close(self):
        self.stop()


class SerialZBackend:
    """Requires z_axis_tracking firmware; never falls back to legacy motion."""
    def __init__(self, config):
        self.home_speed = _home_speed(config)
        self.configurable_home_speed = 'home_speed_m_s' in config
        import serial
        from serial.tools import list_ports
        matches = [p for p in list_ports.comports()
                   if p.serial_number == str(config['serial_number'])]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one Z Pico serial={config['serial_number']!r}; found {matches}")
        if 'Z_TRACKING_V1' not in str(matches[0].product):
            raise RuntimeError('Z Pico requires z_axis_tracking firmware (USB product Z_TRACKING_V1); '
                               'old firmware was not opened or sent any commands')
        self.port = serial.Serial(matches[0].device, int(config.get('baudrate', 115200)),
                                  timeout=0, write_timeout=.1, exclusive=True)
        self.buffer = bytearray()
        self.state = None
        self.command_id = 0
        self.last_query = -math.inf
        self.last_received = time.monotonic()
        self.timeout = float(config.get('communication_timeout_sec', .6))
        self.started = None

    def _write(self, line):
        self.port.write((line+'\n').encode('ascii'))

    def tick(self, now):
        if self.started is None:
            self.started = self.last_received = now
        if now-self.last_query >= .1:
            self._write('ZINFO')  # Also the host heartbeat; no movement.
            self.last_query = now
        self.buffer.extend(self.port.read(min(2048, self.port.in_waiting)))
        if len(self.buffer) > 8192:
            raise RuntimeError('Z Pico serial line overflow')
        while b'\n' in self.buffer:
            line, _, rest = self.buffer.partition(b'\n')
            self.buffer = bytearray(rest)
            line = line.decode('ascii', errors='replace').strip()
            if line.startswith('ZERR,'):
                raise RuntimeError(f'Z Pico rejected command: {line}')
            if not line.startswith('ZTRACK_V1,STATE,'):
                continue
            parts = line.split(',')
            if len(parts) != 9:
                raise RuntimeError(f'Malformed Z Pico state: {line}')
            steps, homed, busy, powered, limit, command = map(int, parts[2:8])
            if homed not in (0, 1) or busy not in (0, 1) or powered != 1 or limit not in (0, 1):
                raise RuntimeError(f'Invalid Z Pico state: {line}')
            if steps < 0 or steps > 90000:
                raise RuntimeError(f'Z pulse-count position out of range: {steps}')
            self.state = dict(position_m=steps/200000., homed=bool(homed), busy=bool(busy),
                              powered=True, limit_active=bool(limit), command_id=command,
                              fault=parts[8], position_source='pulse_count_estimate',
                              received_monotonic=now)
            self.last_received = now
            if parts[8] != 'NONE':
                raise RuntimeError(f"Z firmware fault: {parts[8]}")
        timeout = self.timeout if self.state is not None else 3.
        if now-self.last_received > timeout:
            raise TimeoutError('Z Pico status timeout; requires ZTRACK_V1 firmware (z_axis_tracking), not z_axis_pico2.ino')
        return self.state

    def move(self, target, speed):
        self.command_id += 1
        self._write(f'ZMOVE,{self.command_id},{round(target*1000)},{speed*1000:.3f}')
        return self.command_id

    def home(self):
        self.command_id += 1
        command = f'ZHOME,{self.command_id}'
        if self.configurable_home_speed:
            command += f',{self.home_speed*1000:.3f}'
        self._write(command)
        return self.command_id

    def stop(self):
        if self.port.is_open:
            self._write('ZSTOP')  # Keep holding power enabled.

    def close(self):
        try:
            self.stop()
        finally:
            self.port.close()


class ZTrackingCoordinator:
    """IDLE -> STOPPING_XY -> MOVING_Z -> SETTLING -> IDLE, no queue."""
    def __init__(self, config, backend):
        self.cfg = dict(config)
        defaults = dict(trigger_error_m=.010, max_correction_m=.020, speed_m_s=.010,
                        min_position_m=.005, max_position_m=.450,
                        observation_timeout_sec=.30, xy_stop_speed_rad_s=.02,
                        xy_stop_samples=3, xy_stop_timeout_sec=5.,
                        settle_sec=.3, move_timeout_sec=15., home_timeout_sec=120.)
        for key, default in defaults.items():
            self.cfg.setdefault(key, default)
        for key in defaults:
            value = float(self.cfg[key])
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f'z_tracking.{key} must be positive and finite')
        if (self.cfg['min_position_m'] >= self.cfg['max_position_m'] or
                self.cfg['max_position_m'] > .450 or self.cfg['speed_m_s'] > .020 or
                self.cfg['trigger_error_m'] < .010):
            raise ValueError('invalid Z range, speed (>20mm/s), or trigger (<10mm)')
        self.backend = backend
        self.phase = 'WAITING_STATUS'
        self.reason = 'waiting_for_z_status'
        self.observation = None
        self.home_pending = False
        self.stop_pending = False
        self.stop_reason = None
        self.state = None
        self.target = None
        self.active_id = None
        self.previous = None
        self.joint_velocity = None
        self.phase_started = 0.
        self.stopped_samples = 0
        self.epoch_ros = 0.
        self.homing = False

    @property
    def owns_xy(self):
        return self.phase != 'IDLE'

    def observe(self, error_m, capture_stamp, received):
        if not all(math.isfinite(v) for v in (error_m, capture_stamp, received)):
            return
        if capture_stamp <= self.epoch_ros:
            return
        if self.observation is not None and capture_stamp <= self.observation[1]:
            return
        self.observation = (float(error_m), capture_stamp, received)

    def _fresh(self, now, ros_now):
        obs = self.observation
        return (obs is not None and obs[1] > self.epoch_ros and
                -.05 <= ros_now-obs[1] <= self.cfg['observation_timeout_sec'] and
                0. <= now-obs[2] <= self.cfg['observation_timeout_sec'])

    def fail(self, reason):
        # Preserve the first cause when the tracker catches and wraps a Z fault.
        if self.phase != 'FAULT':
            self.phase, self.reason = 'FAULT', str(reason)
        self.backend.stop()

    def _reset_stop_measurement(self, joints, now):
        """Hook for an estimator whose window starts after the hold request."""

    def _stationary(self, joints, now):
        self.joint_velocity = None
        if self.previous is not None:
            before, before_time = self.previous
            dt = now-before_time
            if dt > 0:
                self.joint_velocity = [(a-b)/dt for a, b in zip(joints, before)]
        self.previous = (list(joints), now)
        return (self.joint_velocity is not None and
                max(map(abs, self.joint_velocity)) <= self.cfg['xy_stop_speed_rad_s'])

    def step(self, now, ros_now, joints, allowed=True):
        self.state = self.backend.tick(now)
        if self.phase == 'FAULT':
            return True
        if self.stop_pending:
            self.fail(self.stop_reason or 'explicit_stop_or_invalid_observation')
            return True
        if self.state is None:
            return True
        if self.state.get('fault', 'NONE') != 'NONE':
            self.fail(self.state['fault'])
            return True
        if not allowed:
            if self.phase in ('STOPPING_XY', 'MOVING_Z', 'HOMING', 'SETTLING'):
                self.fail('harvest_or_controller_owns_arm')
            return self.owns_xy
        stationary = self._stationary(joints, now)
        if self.phase == 'WAITING_STATUS':
            self.phase = 'IDLE' if self.state['homed'] else 'NEEDS_HOME'
        if self.home_pending:
            if self.phase not in ('IDLE', 'NEEDS_HOME'):
                self.home_pending = False
            else:
                self.home_pending = False
                self.homing = True
                self.phase, self.phase_started = 'STOPPING_XY', now
                self.stopped_samples = 0
                self._reset_stop_measurement(joints, now)
        if self.phase == 'NEEDS_HOME':
            self.reason = 'call_/arm_xy/z/home_to_establish_origin'
            return True
        if self.phase == 'IDLE':
            self.reason = 'below_10mm_or_no_fresh_observation'
            if self._fresh(now, ros_now) and abs(self.observation[0]) >= self.cfg['trigger_error_m']:
                self.phase, self.phase_started = 'STOPPING_XY', now
                self.stopped_samples = 0
                self.homing = False
                self._reset_stop_measurement(joints, now)
            else:
                return False
        if self.phase == 'STOPPING_XY':
            self.reason = 'waiting_for_measured_xy_stop'
            if now-self.phase_started > self.cfg['xy_stop_timeout_sec']:
                self.fail('xy_failed_to_stop')
                return True
            self.stopped_samples = self.stopped_samples+1 if stationary else 0
            if self.stopped_samples < self.cfg['xy_stop_samples']:
                return True
            if self.homing:
                self.active_id = self.backend.home()
                self.phase, self.phase_started = 'HOMING', now
                return True
            if not self._fresh(now, ros_now):
                self.phase, self.reason = 'IDLE', 'z_observation_expired_before_move'
                return False
            error = self.observation[0]
            if abs(error) < self.cfg['trigger_error_m']:
                self.phase, self.reason = 'IDLE', 'z_error_below_trigger'
                return False
            correction = max(-self.cfg['max_correction_m'], min(self.cfg['max_correction_m'], error))
            target = round((self.state['position_m']+correction)*1000)/1000
            if not self.cfg['min_position_m'] <= target <= self.cfg['max_position_m']:
                self.fail('z_target_outside_configured_limits')
                return True
            self.target = target
            self.active_id = self.backend.move(target, self.cfg['speed_m_s'])
            self.phase, self.phase_started = 'MOVING_Z', now
        if self.phase in ('MOVING_Z', 'HOMING'):
            self.reason = 'z_homing_xy_held' if self.homing else 'discrete_z_correction_xy_held'
            timeout = self.cfg['home_timeout_sec'] if self.homing else self.cfg['move_timeout_sec']
            if now-self.phase_started > timeout:
                self.fail('z_motion_timeout')
            elif not self.homing and not self._fresh(now, ros_now):
                self.fail('observation_lost_during_z_move')
            elif self.state['command_id'] == self.active_id and not self.state['busy']:
                if not self.state['homed'] or (not self.homing and abs(self.state['position_m']-self.target) > .0011):
                    self.fail('z_completion_position_mismatch')
                else:
                    self.phase, self.phase_started = 'SETTLING', now
            return True
        if self.phase == 'SETTLING':
            self.reason = 'waiting_for_z_settle_and_fresh_image'
            if now-self.phase_started >= self.cfg['settle_sec']:
                self.phase, self.reason = 'IDLE', 'z_complete_waiting_fresh_goal'
                self.epoch_ros = ros_now
                self.observation = None
                self.homing = False
                return False
        return self.owns_xy

    def diagnostics(self, stamp):
        return dict(stamp=stamp, phase=self.phase, reason=self.reason,
                    trigger_error_m=self.cfg['trigger_error_m'],
                    xy_inhibited=self.owns_xy, homed=False if self.state is None else self.state['homed'],
                    position_m=None if self.state is None else self.state['position_m'],
                    position_source=None if self.state is None else self.state.get('position_source'),
                    target_m=self.target, correction_error_m=None if self.observation is None else self.observation[0])


class PixelZTrackingCoordinator(ZTrackingCoordinator):
    """Depth-free image-band Z control, with exclusive XY ownership.

    Start at the outer pixel band, latch the correction cycle through bounded
    Z segments, stop at the inner band. Never queue segments or estimate distance
    from pixels. The legacy class is retained for its old metric interface.
    """
    def __init__(self, config, backend):
        super().__init__(config, backend)
        for key, default in dict(trigger_ratio=.10, stop_ratio=.05, step_m=.005,
                                 max_cycle_travel_m=.100, xy_stop_window_sec=.5,
                                 xy_stop_position_tolerance_rad=.0035,
                                 xy_stop_max_sample_gap_sec=.25).items():
            value = float(config.get(key, default))
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f'z_tracking.{key} must be positive and finite')
            self.cfg[key] = value
        if (not self.cfg['stop_ratio'] < self.cfg['trigger_ratio'] <= 1. or
                self.cfg['step_m'] < .001 or self.cfg['step_m'] > self.cfg['max_cycle_travel_m']):
            raise ValueError('invalid pixel bands or Z step/travel bounds')
        samples = config.get('observation_recovery_samples', 3)
        if isinstance(samples, bool) or not isinstance(samples, int) or not 1 <= samples <= 30:
            raise ValueError('z_tracking.observation_recovery_samples must be an integer in 1..30')
        self.cfg['observation_recovery_samples'] = samples
        self.pixel_meta = None
        self.active_track_id = None
        self.cycle_started = None
        self.cycle_travel = 0.
        self.move_direction = 0
        self.stop_history = deque()
        self.stop_reference = None
        self.xy_hold_target = None
        self.stop_check = dict(ready=False, blocking_joints=[], reason='not_waiting')
        self.observation_hold_pending = None
        self.observation_hold_started = None
        self.observation_stop_confirmed = False
        self.recovery_samples = 0
        self.recovery_stamp = None
        self.sequence_action = None

    def step_sequence(self, now, ros_now, joints, action, lift_m=0.):
        """Measured-stop -> bounded lift/home -> settling, owned by harvest.

        Runs only in the tracker I/O timer; visual observations never drive this
        operation. Return True only when firmware completion and settling agree.
        """
        self.state = self.backend.tick(now)
        if self.phase == 'FAULT':
            return False
        if self.stop_pending:
            self.fail(self.stop_reason or 'explicit_stop_during_sequence_z')
            return False
        if self.state is None:
            return False
        if self.state.get('fault', 'NONE') != 'NONE':
            self.fail(self.state['fault'])
            return False
        if self.sequence_action is None:
            if self.phase != 'IDLE' or action not in ('lift', 'home'):
                self.fail('sequence_z_requires_idle_coordinator')
                return False
            if not math.isfinite(lift_m) or lift_m < 0:
                self.fail('invalid_sequence_z_lift')
                return False
            if action == 'lift':
                if not self.state['homed']:
                    self.fail('sequence_z_lift_requires_homed_axis')
                    return False
                self.target = round((self.state['position_m']+lift_m)*1000)/1000
                if not self.cfg['min_position_m'] <= self.target <= self.cfg['max_position_m']:
                    self.fail('sequence_z_lift_outside_configured_limits')
                    return False
            else:
                self.target = None
            self.sequence_action = action
            self.phase, self.phase_started = 'STOPPING_XY', now
            self.reason = 'sequence_z_waiting_for_xy_stop'
            self.observation = None
            self.cycle_started = None
            self.observation_hold_pending = None
            self.stopped_samples = 0
            self._reset_stop_measurement(joints, now)
        if action != self.sequence_action:
            self.fail('sequence_z_action_changed')
            return False
        if (self.phase in ('SEQUENCE_LIFT', 'SEQUENCE_HOMING', 'SEQUENCE_SETTLING') and
                self.stop_reference is not None and
                max(abs(q-ref) for q, ref in zip(joints, self.stop_reference)) >
                self.cfg['xy_stop_position_tolerance_rad']):
            self.fail('sequence_z_xy_hold_position_changed')
            return False
        if self.phase == 'STOPPING_XY':
            stationary = self._stationary(joints, now)
            self.stopped_samples = self.stopped_samples+1 if stationary else 0
            if now-self.phase_started > self.cfg['xy_stop_timeout_sec']:
                self.fail('xy_failed_to_stop')
            elif self.stopped_samples >= self.cfg['xy_stop_samples']:
                self.active_id = (self.backend.home() if action == 'home' else
                                  self.backend.move(self.target, self.cfg['speed_m_s']))
                self.phase, self.phase_started = ('SEQUENCE_HOMING' if action == 'home' else 'SEQUENCE_LIFT'), now
                self.reason = 'sequence_z_'+action+'_xy_held'
            return False
        if self.phase in ('SEQUENCE_LIFT', 'SEQUENCE_HOMING'):
            timeout = self.cfg['home_timeout_sec'] if action == 'home' else self.cfg['move_timeout_sec']
            if now-self.phase_started > timeout:
                self.fail('sequence_z_motion_timeout')
            elif self.state['command_id'] == self.active_id and not self.state['busy']:
                if (not self.state['homed'] or
                        not self.cfg['min_position_m'] <= self.state['position_m'] <= self.cfg['max_position_m'] or
                        (action == 'lift' and abs(self.state['position_m']-self.target) > .0011)):
                    self.fail('sequence_z_completion_mismatch')
                else:
                    self.target = self.state['position_m']
                    self.phase, self.phase_started = 'SEQUENCE_SETTLING', now
                    self.reason = 'sequence_z_'+action+'_settling'
            return False
        if self.phase == 'SEQUENCE_SETTLING':
            if self.state['busy'] or not self.state['homed'] or abs(self.state['position_m']-self.target) > .0011:
                self.fail('sequence_z_unstable_after_stop')
            elif now-self.phase_started >= self.cfg['settle_sec']:
                self.phase, self.reason = 'IDLE', 'sequence_z_'+action+'_complete'
                self.sequence_action = None
                self.observation = None
                self.epoch_ros = ros_now
                self.homing = False
                return True
        return False

    def request_observation_hold(self, reason):
        """Callback side: record a request; only step() performs motor I/O."""
        if not self.homing and not self.home_pending and self.phase not in ('FAULT', 'NEEDS_HOME', 'WAITING_STATUS'):
            self.observation_hold_pending = str(reason)

    def _hold_for_observation(self, now, ros_now, reason):
        if self.phase != 'OBSERVATION_HOLD':
            self.backend.stop()
            self.observation_hold_started = now
            self.observation_stop_confirmed = False
            self.phase, self.phase_started = 'OBSERVATION_HOLD', now
        self.reason = 'observation_hold:'+str(reason)
        self.observation = None
        self.epoch_ros = ros_now
        self.recovery_samples = 0
        self.recovery_stamp = None

    def _reset_stop_measurement(self, joints, now):
        self.stop_reference = list(joints if self.xy_hold_target is None else self.xy_hold_target)
        self.stop_history.clear()
        self.stop_history.append((now, list(joints)))
        self.stop_check = dict(ready=False, blocking_joints=[], reason='collecting_post_hold_window',
                               window_sec=0.)

    def _stationary(self, joints, now):
        super()._stationary(joints, now)
        if self.phase != 'STOPPING_XY':
            return False
        if self.stop_reference is None:
            self._reset_stop_measurement(joints, now)
            return False
        if self.stop_history and now-self.stop_history[-1][0] > self.cfg['xy_stop_max_sample_gap_sec']:
            self.stop_history.clear()  # Missing samples cannot prove a stop.
            self.stopped_samples = 0
        if not self.stop_history or now > self.stop_history[-1][0]:
            self.stop_history.append((now, list(joints)))
        cutoff = now-self.cfg['xy_stop_window_sec']
        # Keep one sample at/before the window boundary; do not differentiate
        # encoder noise over just the most recent 100 ms interval.
        while len(self.stop_history) > 2 and self.stop_history[1][0] <= cutoff:
            self.stop_history.popleft()
        elapsed = now-self.stop_history[0][0]
        self.stop_check = dict(ready=False, reason='collecting_post_hold_window',
                              window_sec=elapsed, blocking_joints=[])
        if elapsed+1e-9 < self.cfg['xy_stop_window_sec']:
            return False
        oldest = self.stop_history[0][1]
        velocity = [(q-old)/elapsed for q, old in zip(joints, oldest)]
        span = [max(q[i] for _, q in self.stop_history)-min(q[i] for _, q in self.stop_history)
                for i in range(len(joints))]
        error = [abs(q-ref) for q, ref in zip(joints, self.stop_reference)]
        tolerance = self.cfg['xy_stop_position_tolerance_rad']
        blocked = [i+1 for i in range(len(joints))
                   if abs(velocity[i]) > self.cfg['xy_stop_speed_rad_s'] or
                   span[i] > tolerance or error[i] > tolerance]
        self.stop_check = dict(ready=not blocked, reason='within_stop_bounds' if not blocked else 'joint_motion_or_hold_error',
                              window_sec=elapsed, blocking_joints=blocked,
                              window_velocity_rad_s=velocity, position_span_rad=span, hold_error_rad=error,
                              speed_limit_rad_s=self.cfg['xy_stop_speed_rad_s'],
                              position_tolerance_rad=tolerance)
        return not blocked

    def observe_pixel(self, error_px, image_height, direction_per_error, track_id,
                      capture_stamp, received):
        values = (error_px, image_height, direction_per_error, track_id, capture_stamp, received)
        if (not all(math.isfinite(v) for v in values) or image_height < 1 or
                int(image_height) != image_height or abs(error_px) > image_height or
                direction_per_error not in (-1, 1) or track_id < 1 or int(track_id) != track_id):
            return
        before = self.observation
        super().observe(error_px/image_height, capture_stamp, received)
        if self.observation is before:
            return
        self.pixel_meta = dict(error_px=error_px, image_height=int(image_height),
                               direction_per_error=int(direction_per_error), track_id=int(track_id))
        if self.cycle_started is not None and track_id != self.active_track_id:
            self.stop_reason = 'target_identity_changed_during_z'
            self.stop_pending = True

    def _begin_segment(self, now):
        direction = (1 if self.observation[0] > 0 else -1)*self.pixel_meta['direction_per_error']
        distance = self.cfg['step_m']
        if self.cycle_travel+distance > self.cfg['max_cycle_travel_m']+1e-9:
            self.fail('z_pixel_cycle_travel_limit')
            return
        target = round((self.state['position_m']+direction*distance)*1000)/1000
        if not self.cfg['min_position_m'] <= target <= self.cfg['max_position_m']:
            self.fail('z_target_outside_configured_limits')
            return
        self.target = target
        self.cycle_travel += abs(target-self.state['position_m'])
        self.move_direction = direction
        self.active_id = self.backend.move(target, self.cfg['speed_m_s'])
        self.phase, self.phase_started = 'MOVING_Z', now
        self.reason = 'pixel_z_segment_xy_held'

    def _wait_new_image(self, now, ros_now):
        self.phase, self.phase_started = 'WAITING_IMAGE', now
        self.reason = 'z_segment_stopped_waiting_fresh_image'
        self.epoch_ros = ros_now
        self.observation = None

    def step(self, now, ros_now, joints, allowed=True):
        # Explicit homing and its settling retain the existing bounded protocol.
        # Hide pixel observations from the metric parent's trigger calculation.
        if self.phase in ('WAITING_STATUS', 'NEEDS_HOME') or self.home_pending or self.homing:
            saved = self.observation
            self.observation = None
            owns = super().step(now, ros_now, joints, allowed)
            if self.phase != 'IDLE':
                self.observation = saved
            else:
                self.cycle_started = None
                self.reason = 'inside_outer_pixel_band_or_no_observation'
            return owns
        self.state = self.backend.tick(now)
        if self.phase == 'FAULT':
            return True
        if self.stop_pending:
            self.fail(self.stop_reason or 'explicit_stop_or_invalid_observation')
            return True
        if self.state is None:
            return True
        if self.state.get('fault', 'NONE') != 'NONE':
            self.fail(self.state['fault'])
            return True
        if not allowed:
            if self.owns_xy:
                self.fail('harvest_or_controller_owns_arm')
            return self.owns_xy
        if self.observation_hold_pending is not None:
            self._hold_for_observation(now, ros_now, self.observation_hold_pending)
            self.observation_hold_pending = None
        if self.phase == 'OBSERVATION_HOLD':
            # Keep XY held throughout loss, and prove Z has stopped before
            # accepting a new image. Never complete an old in-flight segment.
            awaiting_stop = (self.state['busy'] or
                self.state.get('received_monotonic', now) <= self.phase_started or
                (self.cycle_started is not None and self.state['command_id'] != self.active_id))
            if awaiting_stop:
                if now-self.phase_started > self.cfg['move_timeout_sec']:
                    self.fail('z_observation_hold_failed_to_stop')
                return True
            if not self.observation_stop_confirmed:
                self.observation_stop_confirmed = True
                self.epoch_ros = ros_now
                self.observation = None
                return True
            if not self._fresh(now, ros_now):
                self.recovery_samples = 0
                self.recovery_stamp = None
                return True
            if self.observation[1] != self.recovery_stamp:
                self.recovery_samples += 1
                self.recovery_stamp = self.observation[1]
            if self.recovery_samples < self.cfg['observation_recovery_samples']:
                return True
            if self.cycle_started is not None:
                if self.pixel_meta['track_id'] != self.active_track_id:
                    self.fail('target_identity_changed_during_z')
                    return True
                # Time spent stopped without observations is not motion time.
                # Retain the cycle's travel budget and original target identity.
                self.cycle_started += now-self.observation_hold_started
            elif abs(self.observation[0]) < self.cfg['trigger_ratio']:
                self.phase, self.reason = 'IDLE', 'observation_recovered_waiting_fresh_goal'
                return False
            else:
                self.active_track_id = self.pixel_meta['track_id']
                self.cycle_travel = 0.
            self.phase, self.phase_started = 'STOPPING_XY', now
            self.stopped_samples = 0
            self._reset_stop_measurement(joints, now)
        stationary = self._stationary(joints, now)
        fresh = self._fresh(now, ros_now)
        if self.phase == 'IDLE':
            self.reason = 'inside_outer_pixel_band_or_no_observation'
            if not fresh or abs(self.observation[0]) < self.cfg['trigger_ratio']:
                return False
            self.phase, self.phase_started = 'STOPPING_XY', now
            self.stopped_samples = 0
            self.active_track_id = self.pixel_meta['track_id']
            self.cycle_started = None
            self.cycle_travel = 0.
            self._reset_stop_measurement(joints, now)
        if self.phase == 'STOPPING_XY':
            self.reason = 'waiting_for_measured_xy_stop'
            if now-self.phase_started > self.cfg['xy_stop_timeout_sec']:
                self.fail('xy_failed_to_stop')
                return True
            self.stopped_samples = self.stopped_samples+1 if stationary else 0
            if self.stopped_samples < self.cfg['xy_stop_samples']:
                return True
            if not fresh:
                self._hold_for_observation(now, ros_now, 'pixel_observation_expired_before_move')
                return True
            if abs(self.observation[0]) <= self.cfg['stop_ratio']:
                self.phase, self.reason = 'IDLE', 'z_not_started_observation_expired_or_inside_band'
                self.cycle_started = None
                return False
            self.active_track_id = self.pixel_meta['track_id']
            if self.cycle_started is None:
                self.cycle_started = now
            self._begin_segment(now)
        if self.cycle_started is not None:
            if now-self.cycle_started > self.cfg['move_timeout_sec']:
                self.fail('z_pixel_cycle_timeout')
                return True
            if self.phase in ('MOVING_Z', 'STOPPING_Z', 'WAITING_IMAGE', 'SETTLING') and not fresh:
                # A completed segment explicitly clears the old observation.
                if self.phase != 'WAITING_IMAGE' or now-self.phase_started > self.cfg['observation_timeout_sec']:
                    self._hold_for_observation(now, ros_now, 'pixel_observation_lost_during_z')
                    return True
        if self.phase == 'MOVING_Z':
            error = self.observation[0]
            direction = (1 if error > 0 else -1)*self.pixel_meta['direction_per_error']
            if abs(error) <= self.cfg['stop_ratio'] or direction != self.move_direction:
                self.backend.stop()
                self.phase, self.phase_started = 'STOPPING_Z', now
                self.reason = 'inner_pixel_band_or_direction_change_stop'
            elif self.state['command_id'] == self.active_id and not self.state['busy']:
                if abs(self.state['position_m']-self.target) > .0011:
                    self.fail('z_completion_position_mismatch')
                else:
                    self._wait_new_image(now, ros_now)
            return True
        if self.phase == 'STOPPING_Z':
            if self.state['command_id'] == self.active_id and not self.state['busy']:
                self._wait_new_image(now, ros_now)
            return True
        if self.phase == 'WAITING_IMAGE':
            if not fresh:
                return True
            if abs(self.observation[0]) <= self.cfg['stop_ratio']:
                self.phase, self.phase_started = 'SETTLING', now
                self.reason = 'inside_inner_pixel_band_settling'
            else:
                self._begin_segment(now)
            return True
        if self.phase == 'SETTLING':
            if abs(self.observation[0]) > self.cfg['stop_ratio']:
                self._begin_segment(now)
            elif now-self.phase_started >= self.cfg['settle_sec']:
                self.phase, self.reason = 'IDLE', 'z_complete_waiting_fresh_goal'
                self.observation = None
                self.epoch_ros = ros_now
                self.cycle_started = None
                return False
        return self.owns_xy

    def diagnostics(self, stamp):
        meta = self.pixel_meta or {}
        height = meta.get('image_height')
        return dict(stamp=stamp, control_mode='pixel', phase=self.phase, reason=self.reason,
                    trigger_ratio=self.cfg['trigger_ratio'], stop_ratio=self.cfg['stop_ratio'],
                    trigger_px=None if height is None else height*self.cfg['trigger_ratio'],
                    stop_px=None if height is None else height*self.cfg['stop_ratio'],
                    error_px=None if self.observation is None else meta.get('error_px'),
                    track_id=self.active_track_id, cycle_travel_m=self.cycle_travel,
                    sequence_action=self.sequence_action,
                    recovery_samples=self.recovery_samples,
                    required_recovery_samples=self.cfg['observation_recovery_samples'],
                    xy_inhibited=self.owns_xy, homed=False if self.state is None else self.state['homed'],
                    position_m=None if self.state is None else self.state['position_m'],
                    position_source=None if self.state is None else self.state.get('position_source'),
                    target_m=self.target, xy_stop=self.stop_check,
                    joint_velocity_rad_s=self.joint_velocity,
                    stopped_samples=self.stopped_samples,
                    required_stopped_samples=self.cfg['xy_stop_samples'])
