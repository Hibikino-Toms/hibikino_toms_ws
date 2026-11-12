"""Pico status decoding and a hardware-free NC rail homing model."""
import re

LEGACY_STATUS = re.compile(
    r'PWM=(-?\d+),(-?\d+),(-?\d+),(-?\d+).*?ENC4=(-?\d+)'
    r'.*?POT1=(\d+),.*?POT2=(\d+),.*?POT3=(\d+),')
COMPACT_STATUS = re.compile(
    r'PWM=(-?\d+),(-?\d+),(-?\d+),(-?\d+).*?ENC4=(-?\d+)'
    r'.*?POT1=(\d+),.*?SERVO_FB=(\d+),')
PROFILE_NAMES = {'legacy_four_dc': 'LEGACY_FOUR_DC',
                 'roll_rail_servo': 'ROLL_RAIL_SERVO_V1'}


def parse_status(line):
    compact = 'SERVO_FB=' in line
    match = (COMPACT_STATUS if compact else LEGACY_STATUS).search(line)
    if match is None:
        return None
    fields = list(map(int, match.groups()))
    result = dict(pwm=fields[:4], enc4=fields[4], pot1=fields[5])
    if compact:
        # The current wiring reports the hook servo's GP28 ADC explicitly.
        # Do not alias this value to POT3: no POT3 sensor is connected.
        result['servo_fb'] = fields[6]
    else:
        result.update(pot2=fields[6], pot3=fields[7])
    tokens = dict(re.findall(r'\b([A-Z_]+)=([A-Za-z0-9_-]+)', line))
    if compact:
        try:
            result['servo_us'] = int(tokens['SERVO_US'])
        except (KeyError, ValueError):
            result['servo_us'] = None
    result['profile'] = tokens.get('PROFILE', 'LEGACY_FOUR_DC')
    try:
        if tokens['LIMIT'] not in ('0', '1') or tokens['HOME_CAP'] != '1':
            raise ValueError('invalid switch or capability flag')
        result['homing'] = dict(
            supported=int(tokens['HOME_CAP']) == 1,
            request_id=int(tokens['HOME_ID']), phase=tokens['HOME'],
            error=tokens['HOME_ERROR'], limit_open=bool(int(tokens['LIMIT'])),
            encoder_sign=int(tokens['ENC_SIGN']))
    except (KeyError, ValueError):
        result['homing'] = dict(supported=False)
    return result


class SimulatedRailHoming:
    """Switch/encoder state machine used only by the in-process Pico model."""
    def __init__(self):
        self.phase, self.request_id, self.error = 'IDLE', 0, 'NONE'
        self.output = 0
        self.encoder_sign = 0
        self.stable_at = None

    @property
    def active(self):
        return self.phase in ('RELEASE', 'SEEK', 'CONTACT')

    def start(self, request_id, cfg, now, encoder, switch_open):
        self.request_id, self.cfg, self.started = request_id, cfg, now
        self.phase = 'RELEASE' if switch_open else 'SEEK'
        self.output = -cfg['retract_pwm'] if switch_open else cfg['retract_pwm']
        self.origin = self.progress_encoder = encoder
        self.release_delta = 0
        self.progress_at, self.stable_at = now, None
        self.error, self.encoder_sign = 'NONE', 0

    def fail(self, reason):
        self.phase, self.output, self.error = 'FAULT', 0, reason

    def cancel(self, reason='STOP'):
        if self.active:
            self.phase, self.error = 'CANCELLED', reason
        self.output = 0

    def update(self, now, encoder, switch_open):
        if not self.active:
            return
        if now-self.started >= self.cfg['timeout_sec']:
            return self.fail('TIMEOUT')
        if self.phase == 'RELEASE':
            if abs(encoder-self.origin) > self.cfg['release_max_counts']:
                return self.fail('SWITCH_DID_NOT_CLOSE')
            clear = not switch_open and abs(encoder-self.origin) >= 1
            self.output = 0 if clear else -self.cfg['retract_pwm']
            if not clear:
                self.stable_at = None
            elif self.stable_at is None:
                self.stable_at = now
            elif now-self.stable_at >= self.cfg['debounce_ms']/1000.:
                self.release_delta = encoder-self.origin
                self.phase, self.origin, self.progress_encoder = 'SEEK', encoder, encoder
                self.progress_at, self.stable_at = now, None
                self.output = self.cfg['retract_pwm']
        else:
            if abs(encoder-self.origin) > self.cfg['max_travel_counts']:
                return self.fail('SEEK_TRAVEL_LIMIT')
            if switch_open:
                self.output = 0
                if self.phase != 'CONTACT':
                    self.phase, self.stable_at = 'CONTACT', now
                elif now-self.stable_at >= self.cfg['debounce_ms']/1000.:
                    if encoder == self.origin and self.release_delta == 0:
                        self.phase, self.output = 'RELEASE', -self.cfg['retract_pwm']
                        self.origin = self.progress_encoder = encoder
                        self.progress_at, self.stable_at = now, None
                    else:
                        self.phase, self.encoder_sign = 'DONE', 1
            else:
                self.phase, self.output = 'SEEK', self.cfg['retract_pwm']
        if self.output:
            if encoder != self.progress_encoder:
                self.progress_encoder, self.progress_at = encoder, now
            elif now-self.progress_at >= self.cfg['progress_timeout_sec']:
                self.fail('NO_ENCODER_PROGRESS')
        else:
            self.progress_encoder, self.progress_at = encoder, now

    def status(self, switch_open):
        return dict(supported=True, request_id=self.request_id, phase=self.phase,
                    error=self.error, limit_open=switch_open, encoder_sign=self.encoder_sign)
