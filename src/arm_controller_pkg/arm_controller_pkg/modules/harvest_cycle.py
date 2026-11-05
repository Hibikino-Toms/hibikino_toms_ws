"""Harvest ownership/state machine, used inside the existing XY tracker."""
import math
import numpy as np
from .joint_startup import JointStartup


class HarvestCycle:
    def __init__(self, settings, return_joints, limits, velocity, acceleration):
        self.settings = dict(settings)
        defaults = dict(arrival_pixel_tolerance_px=20., arrival_distance_tolerance_m=.006,
                        arrival_joint_speed_rad_s=.03, arrival_yaw_tolerance_rad=.03,
                        arrival_goal_pose_tolerance_m=.005,
                        settle_sec=.6, observation_timeout_sec=.25, ee_timeout_sec=1.,
                        return_min_duration_sec=3., return_timeout_sec=60.,
                        return_tolerance_rad=.017453292519943295)
        for key, value in defaults.items():
            self.settings.setdefault(key, value)
            if not math.isfinite(float(self.settings[key])) or float(self.settings[key]) <= 0:
                raise ValueError(f'harvest_cycle.{key} must be positive and finite')
        self.return_joints = list(return_joints)
        self.limits, self.velocity, self.acceleration = limits, velocity, acceleration
        self._motion()  # Validate return target and limits before activation.
        self.state, self.sequence = 'STARTUP', 0
        self.reason = 'initializing'
        self.pending = None
        self.hold_joints = None
        self.hold_settled = 0
        self.motion = None
        self.stable_since = None
        self.target_id = None
        self.previous = None
        self.previous_time = None
        self.ee_seen = None
        self.sample_after = 0.

    def _motion(self):
        s = self.settings
        return JointStartup([self.return_joints], self.limits, self.velocity, self.acceleration,
                            s['return_min_duration_sec'], s['return_timeout_sec'],
                            s['return_tolerance_rad'])

    def transition(self, state, reason, now):
        self.state, self.reason = state, reason
        self.sequence += 1
        self.stable_since = None
        self.target_id = None
        self.sample_after = now

    def ready(self, measured, now):
        self.previous, self.previous_time = np.asarray(measured).copy(), now
        self.transition('APPROACH', 'startup_complete', now)

    def ee_alive(self, now):
        return self.ee_seen is not None and 0 <= now-self.ee_seen <= self.settings['ee_timeout_sec']

    def request(self, action, now):
        if self.state in ('STARTUP', 'FAULT'):
            return False, f'command rejected in {self.state}'
        if action == 'hold':
            self.pending = 'hold'  # Stop takes priority over another pending command.
        elif self.pending is not None:
            return False, 'another command is pending'
        elif action == 'pull' and self.state == 'HARVEST_HOLD':
            if self.hold_settled < 3:
                return False, 'arm hold is still settling'
            if not self.ee_alive(now):
                return False, 'EE heartbeat missing/stale'
            self.pending = action
        elif action == 'resume' and self.state in ('HARVEST_HOLD', 'RETURNED'):
            self.pending = action
        else:
            return False, f'{action} rejected in {self.state}'
        return True, f'{action} accepted; wait for state acknowledgement'

    def freeze(self, measured, reason, now, state='HARVEST_HOLD'):
        self.hold_joints = list(measured)
        # Every hold, including arrival, must demonstrate that the arm has
        # settled before the EE is allowed to begin its sequence.
        self.hold_settled = 0
        self.motion = None
        self.pending = None
        self.transition(state, reason, now)

    def fault(self, reason, now):
        self.pending = None
        self.transition('FAULT', reason, now)

    def step(self, measured, now, observation=None):
        """Return a commanded hold/return position, or None while vision owns XY.

        Observation is supplied only after timestamp/IK/goal checks by tracker.
        Returning never consumes a vision goal or a visual hold message.
        """
        q = np.asarray(measured, float)
        speed = float('inf')
        if self.previous is not None and now > self.previous_time:
            speed = float(np.max(abs(q-self.previous))/(now-self.previous_time))
        self.previous, self.previous_time = q.copy(), now
        action, self.pending = self.pending, None
        if action == 'hold':
            self.freeze(q, 'operator_hold', now)
        elif action == 'pull':
            if self.ee_alive(now):
                self.motion = self._motion()
                self.transition('RETURNING', 'operator_pull', now)
            else:
                self.freeze(q, 'ee_heartbeat_lost', now)
        elif action == 'resume':
            self.hold_joints = None
            self.transition('APPROACH', 'operator_resume', now)
        if self.state == 'RETURNING':
            if not self.ee_alive(now):
                self.freeze(q, 'ee_heartbeat_lost', now)
            else:
                command, done = self.motion.step(q, now)
                if done:
                    self.hold_joints = list(self.return_joints)
                    self.transition('RETURNED', 'return_complete_wait_for_n', now)
                return command
        if self.state in ('HARVEST_HOLD', 'RETURNED'):
            settled = (speed <= self.settings['arrival_joint_speed_rad_s'] and
                       max(abs(q-self.hold_joints)) <= self.settings['return_tolerance_rad'])
            self.hold_settled = self.hold_settled+1 if settled else 0
            return list(self.hold_joints)
        if self.state != 'APPROACH':
            return None
        s = self.settings
        valid = observation is not None
        if valid:
            valid = (observation['received'] > self.sample_after and
                     0 <= now-observation['received'] <= s['observation_timeout_sec'] and
                     abs(observation['pixel_error'][0]) <= s['arrival_pixel_tolerance_px'] and
                     abs(observation['distance_error_m']) <= s['arrival_distance_tolerance_m'] and
                     abs((observation['goal_yaw']-sum(q)+math.pi) % (2*math.pi)-math.pi) <= s['arrival_yaw_tolerance_rad'] and
                     speed <= s['arrival_joint_speed_rad_s'])
        if valid:
            if self.stable_since is None or self.target_id != observation['track_id']:
                self.stable_since, self.target_id = now, observation['track_id']
            if now-self.stable_since >= s['settle_sec']:
                self.freeze(q, 'approach_complete', now)
                return list(self.hold_joints)
        else:
            self.stable_since = None
            self.target_id = None
        return None
