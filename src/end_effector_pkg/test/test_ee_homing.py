"""No ROS/USB: decode real protocol and exercise NC switch fault conditions."""
import unittest

from end_effector_pkg.ee_homing import SimulatedRailHoming, parse_status


class HomingProtocolTest(unittest.TestCase):
    def test_new_status_has_real_sensors_and_no_fabricated_pitch(self):
        values = parse_status(
            '[STATUS] PWM=0,0,0,0 ENC4=0 POT1=1800,raw SERVO_FB=2031,raw '
            'SERVO_US=1500 LIMIT=1 HOME_CAP=1 PROFILE=ROLL_RAIL_SERVO_V1 '
            'HOME=DONE HOME_ID=123 HOME_ERROR=NONE ENC_SIGN=-1')
        self.assertEqual(values['servo_fb'], 2031)
        self.assertNotIn('pot3', values)
        self.assertNotIn('pot2', values)
        self.assertEqual(values['homing']['request_id'], 123)
        self.assertEqual(values['homing']['encoder_sign'], -1)

    def test_old_firmware_does_not_gain_homing_capability(self):
        values = parse_status('[STATUS] PWM=0,0,0,0 ENC4=0 POT1=1800,1V POT2=3930,2V POT3=1500,1V')
        self.assertFalse(values['homing']['supported'])


class SimulatedHomingTest(unittest.TestCase):
    def setUp(self):
        self.home = SimulatedRailHoming()
        self.cfg = dict(retract_pwm=140, timeout_sec=20., progress_timeout_sec=3.,
                        debounce_ms=40, release_max_counts=4, max_travel_counts=70)

    def test_contact_debounce_and_bounce(self):
        h = self.home
        h.start(1, self.cfg, 0., 0, False)
        h.update(.1, 1, True)
        self.assertEqual(h.output, 0)
        h.update(.12, 1, False)
        self.assertEqual(h.phase, 'SEEK')
        h.update(.2, 2, True)
        h.update(.239, 2, True)
        self.assertEqual(h.phase, 'CONTACT')
        h.update(.25, 2, True)
        self.assertEqual(h.phase, 'DONE')

    def test_initially_open_switch_must_close_then_reopen(self):
        h = self.home
        h.start(1, self.cfg, 0., 0, True)
        self.assertLess(h.output, 0)
        h.update(.1, -1, False)
        h.update(.15, -1, False)
        self.assertEqual(h.phase, 'SEEK')
        h.update(.2, 0, True)
        h.update(.25, 0, True)
        self.assertEqual(h.phase, 'DONE')

    def test_open_wire_is_not_accepted_as_home(self):
        self.home.start(1, self.cfg, 0., 0, True)
        self.home.update(.1, -5, True)
        self.assertEqual(self.home.error, 'SWITCH_DID_NOT_CLOSE')
        self.assertEqual(self.home.output, 0)

    def test_contact_before_one_count_requires_bounded_encoder_clearance(self):
        h = self.home
        h.start(1, self.cfg, 0., 0, False)
        h.update(.1, 0, True)
        h.update(.15, 0, True)
        self.assertEqual(h.phase, 'RELEASE')
        h.update(.2, 0, False)
        self.assertLess(h.output, 0)
        h.update(.3, -1, False)
        h.update(.35, -1, False)
        h.update(.4, 0, True)
        h.update(.45, 0, True)
        self.assertEqual(h.phase, 'DONE')

    def test_stuck_closed_switch_travel_limit(self):
        self.home.start(1, self.cfg, 0., 0, False)
        self.home.update(.1, 71, False)
        self.assertEqual(self.home.error, 'SEEK_TRAVEL_LIMIT')

    def test_no_encoder_progress_and_timeout(self):
        self.home.start(1, self.cfg, 0., 0, False)
        self.home.update(3., 0, False)
        self.assertEqual(self.home.error, 'NO_ENCODER_PROGRESS')
        self.home.start(2, self.cfg, 0., 0, False)
        self.home.update(20., 1, False)
        self.assertEqual(self.home.error, 'TIMEOUT')

    def test_cancel_does_not_complete_on_later_switch(self):
        self.home.start(1, self.cfg, 0., 0, False)
        self.home.cancel('HOST_TIMEOUT')
        self.home.update(.1, 1, True)
        self.assertEqual(self.home.phase, 'CANCELLED')
        self.assertEqual(self.home.output, 0)


if __name__ == '__main__':
    unittest.main()
