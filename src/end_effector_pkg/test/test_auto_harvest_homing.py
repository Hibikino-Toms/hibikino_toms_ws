"""ROS node integration using the in-process Pico model, never serial hardware."""
import copy
import json
import tempfile
import time
import unittest
from pathlib import Path

import rclpy
import yaml
from std_msgs.msg import String

from end_effector_pkg.auto_harvest_node import AutoHarvestNode, load_settings


CONFIG = Path(__file__).resolve().parents[3]/'module/set_params.yaml'


class AutomaticRailHomeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='ee-home-test-')
        cls.path = Path(cls.temp.name)/'config.yaml'
        cls.source = yaml.safe_load(CONFIG.read_text())
        rclpy.init(args=['--ros-args', '-p', f'config_file:={cls.path}',
                         '-p', 'backend:=sim', '-p', 'keyboard_enabled:=false'])

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()
        cls.temp.cleanup()

    def setUp(self):
        self.node = None
        self.make_node()

    def make_node(self, calibrated=False):
        if self.node is not None:
            self.node.destroy_node()
        cfg = copy.deepcopy(self.source)
        cfg['auto_harvest']['hook_servo']['calibration_valid'] = calibrated
        if calibrated:
            # Synthetic, test-only endpoints. Never installed as hardware calibration.
            cfg['auto_harvest']['hook_servo'].update(
                calibration_valid=True, open_feedback=1000, closed_feedback=3000)
        self.path.write_text(yaml.safe_dump(cfg))
        self.node = AutoHarvestNode()

    def tearDown(self):
        self.node.destroy_node()

    def until(self, state):
        deadline = time.monotonic()+2.
        while time.monotonic() < deadline:
            self.node._tick()
            if self.node.state == state:
                return
            if self.node.state == self.node.FAULT:
                self.fail(self.node.reason)
            time.sleep(.01)
        self.fail(f'{self.node.state}: {self.node.reason}')

    def test_unreferenced_zero_is_not_home_then_auto_seek_and_calibration_wait(self):
        self.assertEqual(self.node.io.values['enc4'], 0)
        self.assertLess(self.node.io.physical_rail, 0)
        self.assertFalse(self.node.homing_verified)
        self.until(self.node.WAIT_CALIBRATION)
        self.assertTrue(self.node.homing_verified)
        self.assertEqual(self.node.io.values['enc4'], 0)
        self.assertEqual(self.node.io.physical_rail, 0)
        self.assertEqual(self.node.io.drive_values, [0, 0, 0, 0])
        self.assertEqual(self.node.telemetry['servo_us'], 1500)
        self.assertNotIn('pot2', self.node.telemetry)

    def test_calibrated_configuration_initializes_only_after_switch_home(self):
        self.make_node(calibrated=True)
        self.until(self.node.WAIT_ARM)
        self.assertTrue(self.node.homing_verified)
        self.assertEqual(self.node.active_axes, ('pot1', 'servo_fb', 'enc4'))
        self.assertEqual(self.node.io.drive_values[1], 0)

    def test_initially_at_limit_releases_then_retracts_without_c(self):
        self.node.io.physical_rail = 0
        self.node.io.values['enc4'] = 123
        self.node._tick()
        self.assertEqual(self.node.io.home.phase, 'RELEASE')
        self.until(self.node.WAIT_CALIBRATION)
        self.assertEqual(self.node.io.values['enc4'], 0)

    def test_old_firmware_never_starts_motion(self):
        value, seq, stamp = self.node.io.poll(time.monotonic())
        value['homing'] = {'supported': False}
        self.node.io.poll = lambda now: (value, seq+1, now)
        self.node._tick()
        self.assertEqual(self.node.state, self.node.FAULT)
        self.assertIn('lacks NC-switch homing', self.node.reason)
        self.assertEqual(self.node.io.drive_values, [0, 0, 0, 0])

    def test_c_does_not_establish_zero(self):
        self.node.io.values['enc4'] = 123
        self.node._handle_key('c')
        self.assertEqual(self.node.io.values['enc4'], 123)
        self.assertFalse(self.node.homing_verified)

    def test_old_done_token_is_not_current_completion(self):
        self.node._tick()
        value, _, _ = self.node.io.poll(time.monotonic())
        value['homing'].update(phase='DONE', request_id=self.node.homing_request_id-1)
        self.node._monitor_homing(value, True, self.node.stage_started+.1)
        self.assertEqual(self.node.state, self.node.HOMING)
        self.assertFalse(self.node.homing_verified)

    def test_stale_telemetry_stops_active_home(self):
        self.node._tick()
        value, seq, stamp = self.node.io.poll(time.monotonic())
        self.node.io.poll = lambda now: (value, seq+1, now-2.)
        self.node._tick()
        self.assertEqual(self.node.state, self.node.FAULT)
        self.assertEqual(self.node.io.drive_values, [0, 0, 0, 0])

    def test_space_stops_homing_and_cannot_be_resumed_by_n(self):
        self.node._tick()
        self.node._handle_key(' ')
        self.node._handle_key('n')
        self.assertEqual(self.node.state, self.node.ABORTED)
        self.assertEqual(self.node.io.drive_values, [0, 0, 0, 0])
        self.assertFalse(self.node.homing_verified)

    def test_missing_pitch_stage_is_skipped_not_faked(self):
        self.make_node(calibrated=True)
        self.node._begin_motion(self.node.HARVEST_PITCH, {'pot2': 3150})
        self.assertEqual(self.node.state, self.node.HARVEST_EXTEND)
        self.assertEqual(self.node.targets, {'enc4': -45})

    def test_arrival_callback_starts_rail_without_an_unused_pitch_setting(self):
        self.make_node(calibrated=True)
        self.assertNotIn('pot2', self.node.settings['harvest_pose'])
        self.node._transition(self.node.APPROACH, 'synthetic approach')
        self.node.eligible_approach_sequence = 10
        self.node._arm_state_callback(String(data=json.dumps(dict(
            state='HARVEST_HOLD', sequence=11, reason='approach_complete',
            hold_ready=True, stamp=self.node.get_clock().now().nanoseconds/1e9))))
        self.assertEqual(self.node.state, self.node.HARVEST_EXTEND)
        self.assertEqual(self.node.targets, {'enc4': -45})

    def test_simulated_pulses_match_the_actual_firmware_direction(self):
        for pwm, expected_us in ((255, 1600), (-255, 1350), (0, 1500)):
            self.node.io.drive([0, 0, pwm, 0])
            packet, _, _ = self.node.io.poll(time.monotonic())
            self.assertEqual(packet['servo_us'], expected_us)

    def test_reversal_after_overshoot_rebases_progress_but_real_wrong_motion_faults(self):
        self.make_node(calibrated=True)
        self.node._begin_motion(self.node.HARVEST_EXTEND, {'enc4': -20})
        values = dict(pot1=1800, servo_fb=1000, enc4=-10, pwm=[0, 0, 0, 0])
        self.node._drive_targets(time.monotonic(), values, True)
        self.assertLess(self.node.io.drive_values[3], 0)
        values['enc4'] = -28  # Previous extension overshot; now request retraction.
        self.node._drive_targets(time.monotonic()+.1, values, True)
        self.assertGreater(self.node.io.drive_values[3], 0)
        values['enc4'] = -34  # Still extending while positive retract PWM was active.
        with self.assertRaisesRegex(RuntimeError, 'wrong direction'):
            self.node._drive_targets(time.monotonic()+.2, values, True)

    def test_simulated_pico_watchdog_stops_home_without_host_heartbeat(self):
        self.node._tick()
        values, _, _ = self.node.io.poll(time.monotonic()+1.)
        self.assertEqual(values['homing']['phase'], 'CANCELLED')
        self.assertEqual(values['homing']['error'], 'HOST_TIMEOUT')
        self.assertEqual(values['pwm'], [0, 0, 0, 0])

    def test_negative_retract_pwm_is_rejected_for_confirmed_new_wiring(self):
        cfg = copy.deepcopy(self.source)
        cfg['auto_harvest']['encoder_homing']['retract_pwm'] = -140
        self.path.write_text(yaml.safe_dump(cfg))
        with self.assertRaisesRegex(ValueError, 'encoder_homing'):
            load_settings(self.path)


if __name__ == '__main__':
    unittest.main()
