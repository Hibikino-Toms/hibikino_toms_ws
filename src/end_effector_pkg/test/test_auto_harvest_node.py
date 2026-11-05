#!/usr/bin/env python3
"""Small ROS-free-hardware checks for auto harvest fault gates."""
import json
import time
import unittest
from pathlib import Path

import rclpy
from std_msgs.msg import String

from end_effector_pkg.auto_harvest_node import AutoHarvestNode


CONFIG = Path(__file__).resolve().parents[1]/'config/auto_harvest.yaml'


class AutoHarvestGatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init(args=['--ros-args', '-p', f'config_file:={CONFIG}', '-p',
                         'backend:=sim', '-p', 'keyboard_enabled:=false'])

    @classmethod
    def tearDownClass(cls):
        if rclpy.ok():
            rclpy.shutdown()

    def setUp(self):
        self.node = AutoHarvestNode()

    def tearDown(self):
        self.node.destroy_node()

    def test_valid_sensor_values_outside_operating_limits_are_recoverable(self):
        sample = dict(pot1=1800, pot2=3930, pot3=1500, enc4=-51, pwm=[0, 0, 0, 0])
        self.node._validate_values(sample)
        self.assertEqual(self.node._sensor_range_status(sample)['enc4']['status'], 'below_min')

    def test_out_of_range_goal_inside_tolerance_is_accepted(self):
        # POT3=1476 is below its configured minimum, but only 24 counts from
        # the requested goal; its 35-count goal tolerance applies out of range.
        self.node._begin_motion(self.node.RESET_EE, {'pot3': 1500})
        values = dict(pot1=1800, pot2=3930, pot3=1476, enc4=0,
                      pwm=[0, 0, 0, 0])
        self.node._drive_targets(time.monotonic(), values, new_sample=True)
        self.assertFalse(self.node.range_recovery_active)
        self.assertEqual(self.node.io.drive_values, [0, 0, 0, 0])

    def test_out_of_range_sensor_never_receives_command_farther_out(self):
        self.assertEqual(self.node._pwm_for('pot3', 1400, 1476), 0)
        self.assertEqual(self.node._pwm_for('pot2', 4000, 3945), 0)
        # With the current run's polarity, positive PWM decreases POT2 and
        # therefore moves an above-range value back toward its upper limit.
        self.assertGreater(self.node._pwm_for('pot2', 3930, 3975), 0)

    def test_out_of_range_axis_is_recovered_before_current_stage(self):
        self.node._begin_motion(self.node.HARVEST_EXTEND, {'enc4': -45})
        values = dict(pot1=1800, pot2=3930, pot3=1476, enc4=0,
                      pwm=[0, 0, 0, 0])
        self.node._drive_targets(time.monotonic(), values, new_sample=True)
        self.assertLess(self.node.io.drive_values[2], 0)
        self.assertEqual(self.node.io.drive_values[3], 0)

    def test_startup_initialization_drives_three_pot_axes_together(self):
        self.node._begin_motion(self.node.INITIALIZING, self.node.settings['initial_pose'])
        # POT3 is slightly below its configured operating range. Startup must
        # still send all three independent, inward-to-home commands together.
        values = dict(pot1=1700, pot2=2800, pot3=1400, enc4=0,
                      pwm=[0, 0, 0, 0])
        self.node._drive_targets(time.monotonic(), values, new_sample=True)
        self.assertTrue(all(abs(value) >= 140 for value in self.node.io.drive_values[:3]))
        self.assertEqual(self.node.io.drive_values[3], 0)
        self.assertLessEqual(sum(abs(value) for value in self.node.io.drive_values), 540)

    def test_recovery_boundary_crossing_rebases_progress_before_stage_target(self):
        # Re-entering the operating range can overshoot the range boundary.
        # The next command then intentionally reverses toward the stage target.
        # That reversal must use the new boundary sample as its progress base.
        self.node._begin_motion(self.node.RESET_EE, {'pot3': 1500})
        values = dict(pot1=1800, pot2=3000, pot3=1440, enc4=0,
                      pwm=[0, 0, 0, 0])
        self.node._drive_targets(time.monotonic(), values, new_sample=True)
        self.assertTrue(self.node.range_recovery_active)
        self.assertLess(self.node.io.drive_values[2], 0)

        values['pot3'] = 1582
        self.node._drive_targets(time.monotonic()+0.2, values, new_sample=True)
        self.assertFalse(self.node.range_recovery_active)
        self.assertEqual(self.node.state, self.node.RESET_EE)
        self.assertGreater(self.node.io.drive_values[2], 0)

    def test_sensor_jitter_does_not_trigger_wrong_direction_fault(self):
        self.node._begin_motion(self.node.INITIALIZING, {'pot3': 3000})
        values = dict(pot1=1800, pot2=3000, pot3=2000, enc4=0,
                      pwm=[0, 0, 0, 0])
        self.node._drive_targets(time.monotonic(), values, new_sample=True)
        values['pot3'] = 1987  # 13 counts of reverse fluctuation; log shows more.
        self.node._drive_targets(time.monotonic(), values, new_sample=True)
        self.assertEqual(self.node.state, self.node.INITIALIZING)
        self.assertLess(self.node.io.drive_values[2], 0)

    def test_persistent_wrong_direction_beyond_sensor_jitter_still_faults(self):
        self.node._begin_motion(self.node.RESET_EE, {'pot3': 1600})
        values = dict(pot1=1800, pot2=3000, pot3=1483, enc4=0,
                      pwm=[0, 0, 0, 0])
        self.node._drive_targets(time.monotonic(), values, new_sample=True)
        values['pot3'] = 1447  # 36 counts opposite the requested recovery.
        with self.assertRaisesRegex(RuntimeError, 'recovery moved farther out'):
            self.node._drive_targets(time.monotonic(), values, new_sample=True)

    def test_home_reference_accepts_logged_sensor_jitter(self):
        samples = [
            dict(pot1=1865, pot2=2679, pot3=1461, enc4=49),
            dict(pot1=1888, pot2=2707, pot3=1477, enc4=49),
            dict(pot1=1874, pot2=2690, pot3=1467, enc4=49),
            dict(pot1=1893, pot2=2719, pot3=1487, enc4=49),
        ]
        for sample in samples:
            self.node._update_home_sensor_stability(sample)
        self.assertEqual(self.node.sensor_stable_samples, 4)
        self.node.state = self.node.WAIT_HOME
        self.node.telemetry = dict(samples[-1], pwm=[0, 0, 0, 0])
        self.node.sample_time = time.monotonic()
        self.node._handle_key('c')
        self.assertEqual(self.node.state, self.node.WAIT_ZERO)

    def test_home_reference_waits_when_sensor_jitter_exceeds_configured_span(self):
        samples = [
            dict(pot1=1860, pot2=2679, pot3=1461, enc4=49),
            dict(pot1=1900, pot2=2707, pot3=1477, enc4=49),
            dict(pot1=1874, pot2=2690, pot3=1467, enc4=49),
            dict(pot1=1893, pot2=2719, pot3=1487, enc4=49),
        ]
        for sample in samples:
            self.node._update_home_sensor_stability(sample)
        self.assertEqual(self.node.sensor_stable_samples, 0)
        self.node.state = self.node.WAIT_HOME
        self.node.telemetry = dict(samples[-1], pwm=[0, 0, 0, 0])
        self.node.sample_time = time.monotonic()
        self.node._handle_key('c')
        self.assertEqual(self.node.state, self.node.WAIT_HOME)

    def test_impossible_raw_sensor_value_is_rejected(self):
        sample = dict(pot1=1800, pot2=3930, pot3=4096, enc4=0, pwm=[0, 0, 0, 0])
        with self.assertRaisesRegex(RuntimeError, '12-bit ADC'):
            self.node._validate_values(sample)

    def test_stale_approach_completion_does_not_start_harvest(self):
        self.node.state = self.node.APPROACH
        self.node.eligible_approach_sequence = 7
        stamp = self.node.get_clock().now().nanoseconds/1e9
        self.node._arm_state_callback(String(data=json.dumps(dict(
            state='HARVEST_HOLD', sequence=7, stamp=stamp,
            reason='approach_complete', hold_ready=True))))
        self.assertEqual(self.node.state, self.node.APPROACH)
        self.assertIsNone(self.node.cycle_sequence)

    def test_unreachable_target_faults_without_driving(self):
        self.node._begin_motion(self.node.HARVEST_PITCH, {'pot2': 4000})
        self.assertEqual(self.node.state, self.node.FAULT)
        self.assertEqual(self.node.io.drive_values, [0, 0, 0, 0])

    def test_space_stops_and_aborts(self):
        self.node.state = self.node.HARVEST_EXTEND
        self.node.io.drive([0, 0, 0, 80])
        self.node._handle_key(' ')
        self.assertEqual(self.node.state, self.node.ABORTED)
        self.assertEqual(self.node.io.drive_values, [0, 0, 0, 0])

    def test_stale_sensor_sample_faults(self):
        values = dict(pot1=1800, pot2=3930, pot3=1500, enc4=0, pwm=[0, 0, 0, 0])
        self.node.state = self.node.APPROACH
        self.node.io.poll = lambda now: (values, 1, now-2.)
        self.node._tick()
        self.assertEqual(self.node.state, self.node.FAULT)
        self.assertEqual(self.node.io.drive_values, [0, 0, 0, 0])


if __name__ == '__main__':
    unittest.main()
