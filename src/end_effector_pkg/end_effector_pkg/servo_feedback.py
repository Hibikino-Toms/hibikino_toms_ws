"""Filtering and finite-window direction checks for the GP28 hook feedback."""
from collections import deque
import math
from statistics import median


class AnalogFeedbackFilter:
    def __init__(self, name, samples=3, reject_wrap=False):
        if type(samples) is not int or samples not in (1, 3, 5, 7, 9):
            raise ValueError(f'{name}.feedback_median_samples must be an odd integer 1..9')
        self.name = name
        self.reject_wrap = reject_wrap
        self.history = deque(maxlen=samples)

    def update(self, packet):
        if self.name not in packet:
            return packet
        raw = packet[self.name]
        if type(raw) is not int or not 0 <= raw <= 4095:
            raise RuntimeError(f'{self.name} is not a 12-bit ADC reading: {raw}')
        if self.reject_wrap and self.history and abs(raw-self.history[-1]) > 2048:
            raise RuntimeError(f'{self.name} crossed the ADC wrap boundary or jumped over half a turn; stopped')
        self.history.append(raw)
        return dict(packet, **{self.name + '_raw': raw, self.name: int(median(self.history))})


class ServoFeedbackFilter(AnalogFeedbackFilter):
    def __init__(self, samples=3):
        super().__init__('servo_fb', samples, reject_wrap=True)


class ServoDirectionMonitor:
    """Reject sustained wrong motion, allowing isolated ADC reversals."""
    def __init__(self, window_sec=.6, name='servo_fb'):
        if not math.isfinite(window_sec) or not .2 <= window_sec <= 2.:
            raise ValueError(f'{name}.direction_window_sec must be within 0.2..2.0 seconds')
        self.window_sec = window_sec
        self.name = name
        self.reset()

    def reset(self):
        self.direction = None
        self.history = deque()

    def observe(self, now, value, direction, tolerance):
        if direction != self.direction:
            self.reset()
            self.direction = direction
        self.history.append((now, value))
        while len(self.history) > 1 and now-self.history[1][0] >= self.window_sec:
            self.history.popleft()
        started, initial = self.history[0]
        if now-started >= self.window_sec and (value-initial)*direction < -tolerance:
            raise RuntimeError(
                f'{self.name} moved in the wrong direction over {now-started:.2f}s: '
                f'previous={initial}, current={value}, expected_sign={direction}, '
                f'tolerance={tolerance:g}')
