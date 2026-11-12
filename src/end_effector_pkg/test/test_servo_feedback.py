"""Regression for the observed FB reversal and sustained wrong rotation."""
import unittest

from end_effector_pkg.servo_feedback import AnalogFeedbackFilter, ServoDirectionMonitor, ServoFeedbackFilter


class ServoFeedbackTest(unittest.TestCase):
    def test_roll_filter_preserves_raw_value_and_rejects_a_single_spike(self):
        filter_ = AnalogFeedbackFilter('pot1', 3)
        for value in (2140, 2144, 2138):
            filter_.update(dict(pot1=value))
        packet = filter_.update(dict(pot1=2174))
        self.assertEqual(packet['pot1_raw'], 2174)
        self.assertEqual(packet['pot1'], 2144)

    def test_roll_direction_monitor_rejects_sustained_reverse_motion(self):
        monitor = ServoDirectionMonitor(.4, 'pot1')
        with self.assertRaisesRegex(RuntimeError, 'pot1 moved in the wrong direction'):
            for index in range(6):
                monitor.observe(index*.1, 2000+index*40, -1, 35)

    def test_measured_jitter_does_not_stop_genuinely_increasing_feedback(self):
        filter_ = ServoFeedbackFilter(3)
        monitor = ServoDirectionMonitor(.6)
        # Real first-run trace failed at 946 -> 860; subsequent motion increases.
        raw_trace = [774, 774, 784, 946, 860, 990, 1050, 1100, 1200, 1250]
        for index, raw in enumerate(raw_trace):
            packet = filter_.update(dict(servo_fb=raw))
            self.assertEqual(packet['servo_fb_raw'], raw)
            monitor.observe(index*.1, packet['servo_fb'], 1, 30)

    def test_actual_wrong_rotation_still_stops_within_one_window(self):
        monitor = ServoDirectionMonitor(.6)
        with self.assertRaisesRegex(RuntimeError, 'wrong direction'):
            for index in range(8):
                monitor.observe(index*.1, 2000-index*50, 1, 30)

    def test_intentional_reversal_starts_new_observation_window(self):
        monitor = ServoDirectionMonitor(.6)
        for index in range(8):
            monitor.observe(index*.1, 1000+index*30, 1, 30)
        for index in range(8):
            monitor.observe(.8+index*.1, 1210-index*30, -1, 30)
        monitor.reset()
        self.assertFalse(monitor.history)

    def test_wrap_is_rejected_instead_of_selecting_a_different_turn(self):
        filter_ = ServoFeedbackFilter()
        filter_.update(dict(servo_fb=4090))
        with self.assertRaisesRegex(RuntimeError, 'wrap boundary'):
            filter_.update(dict(servo_fb=5))

    def test_invalid_feedback_and_settings_are_rejected(self):
        with self.assertRaises(ValueError):
            ServoFeedbackFilter(4)
        with self.assertRaises(ValueError):
            ServoDirectionMonitor(float('nan'))
        with self.assertRaises(RuntimeError):
            ServoFeedbackFilter().update(dict(servo_fb=4096))

    def test_legacy_pot3_is_not_substituted_for_servo_feedback(self):
        packet = dict(pot3=1234)
        self.assertEqual(ServoFeedbackFilter().update(packet), packet)


if __name__ == '__main__':
    unittest.main()
