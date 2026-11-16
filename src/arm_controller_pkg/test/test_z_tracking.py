"""Discrete Z threshold, ownership, freshness and fault checks without hardware."""
import math
from unittest.mock import Mock

import pytest

from arm_controller_pkg.modules.z_tracking import SimulatedZBackend, ZTrackingCoordinator


def make_control(**config):
    backend = SimulatedZBackend(config)
    return ZTrackingCoordinator(config, backend), backend


JOINTS = [.3, 1., -.3]


def advance(control, t, error=None, joints=JOINTS):
    if error is not None:
        control.observe(error, 100.+t, t)
    return control.step(t, 100.+t, joints)


@pytest.mark.parametrize('error', [-.00999, 0., .00999])
def test_under_10mm_never_commands_z(error):
    control, backend = make_control()
    for i in range(20):
        assert not advance(control, i*.1, error)
    assert backend.command_id == 0
    assert backend.position == .225


@pytest.mark.parametrize('error', [-.01, .01, -.04, .04])
def test_z_correction_waits_for_xy_stop_and_is_capped(error):
    control, backend = make_control()
    advance(control, 0.)
    assert advance(control, .1, error)
    assert control.phase == 'STOPPING_XY'
    assert backend.command_id == 0
    advance(control, .2, error, [.32, 1., -.3])
    assert backend.command_id == 0
    for i in range(3, 7):
        advance(control, i*.1, error)
    assert control.phase == 'MOVING_Z'
    assert backend.command_id == 1
    assert abs(backend.target-.225) <= .02000001
    assert math.copysign(1, backend.target-.225) == math.copysign(1, error)
    # Subsequent observations cannot retarget an in-flight correction.
    target = backend.target
    advance(control, .7, -error)
    assert backend.target == target and backend.command_id == 1


def test_completion_discards_old_targets_and_requires_new_observation():
    control, backend = make_control()
    advance(control, 0.)
    for i in range(1, 40):
        advance(control, i*.1, .015 if backend.position == .225 else .002)
        if control.reason == 'z_complete_waiting_fresh_goal':
            break
    assert control.phase == 'IDLE' and backend.command_id == 1
    assert backend.position == pytest.approx(.240)
    assert control.observation is None
    control.observe(.04, 100., i*.1)
    assert control.observation is None
    assert not advance(control, (i+1)*.1)


def test_stale_observation_before_move_cancels_without_z_motion():
    control, backend = make_control()
    advance(control, 0.)
    advance(control, .1, .02)
    for i in range(2, 7):
        advance(control, i*.1, joints=[.3+i*.01, 1., -.3])
    for i in range(7, 12):
        advance(control, i*.1, joints=[.36, 1., -.3])
    assert backend.command_id == 0
    assert control.phase == 'IDLE'


def test_loss_during_move_stops_and_latches_fault():
    control, backend = make_control()
    for i in range(5):
        advance(control, i*.1, .02)
    assert control.phase == 'MOVING_Z'
    advance(control, 1.)
    assert control.phase == 'FAULT' and not backend.busy
    position = backend.position
    for i in range(11, 20):
        advance(control, i*.1, .02)
    assert backend.position == position and backend.command_id == 1


def test_limits_are_rejected_instead_of_clamping_or_repeated_recovery():
    control, backend = make_control(sim_initial_position_m=.445)
    for i in range(5):
        advance(control, i*.1, .02)
    assert control.phase == 'FAULT'
    assert control.reason == 'z_target_outside_configured_limits'
    assert backend.command_id == 0


def test_not_homed_requires_explicit_request_and_xy_stop():
    control, backend = make_control(sim_homed=False, sim_initial_position_m=.005)
    assert advance(control, 0.)
    assert control.phase == 'NEEDS_HOME' and backend.command_id == 0
    control.home_pending = True
    for i in range(1, 12):
        advance(control, i*.1)
    assert backend.command_id == 1 and backend.homed
    assert control.phase == 'IDLE'


def test_manual_stop_and_harvest_preempt_z():
    control, backend = make_control()
    for i in range(5):
        advance(control, i*.1, .02)
    control.step(.5, 100.5, JOINTS, allowed=False)
    assert control.phase == 'FAULT' and not backend.busy
    control, backend = make_control()
    advance(control, 0.)
    control.stop_pending = True
    advance(control, .1)
    assert control.phase == 'FAULT'


def test_nonfinite_inputs_and_invalid_settings():
    control, _ = make_control()
    control.observe(float('nan'), 100., 0.)
    assert control.observation is None
    for cfg in ({'trigger_error_m': .009}, {'speed_m_s': .03}, {'max_position_m': .5}):
        with pytest.raises(ValueError):
            make_control(**cfg)


def test_old_firmware_is_rejected_without_opening_serial(monkeypatch):
    from types import SimpleNamespace
    from arm_controller_pkg.modules.z_tracking import SerialZBackend
    import serial
    import serial.tools.list_ports
    monkeypatch.setattr(serial.tools.list_ports, 'comports', lambda: [
        SimpleNamespace(serial_number='test', device='/dev/fake', product='Pico')])
    opened = Mock()
    monkeypatch.setattr(serial, 'Serial', opened)
    with pytest.raises(RuntimeError, match='old firmware was not opened'):
        SerialZBackend({'serial_number': 'test'})
    opened.assert_not_called()


def test_serial_status_protocol_and_nonblocking_timeout(monkeypatch):
    import serial
    import serial.tools.list_ports
    from types import SimpleNamespace
    from arm_controller_pkg.modules.z_tracking import SerialZBackend
    port=Mock(is_open=True)
    port.in_waiting=0;port.read.return_value=b''
    monkeypatch.setattr(serial.tools.list_ports, 'comports', lambda:[SimpleNamespace(
        serial_number='test', device='/dev/fake', product='Z_TRACKING_V1')])
    monkeypatch.setattr(serial,'Serial',lambda *args,**kw:port)
    backend=SerialZBackend(dict(serial_number='test', communication_timeout_sec=.6))
    # Delayed activation (EE initialization) does not consume the startup timeout.
    assert backend.tick(1000.) is None
    port.read.return_value=b'ZTRACK_V1,STATE,45000,1,0,1,0,3,NONE\n'
    state=backend.tick(1000.1)
    assert state['position_m']==.225 and state['homed'] and not state['busy']
    assert backend.move(.245,.01)==1
    assert port.write.call_args.args[0]==b'ZMOVE,1,245,10.000\n'
    port.read.return_value=b''
    with pytest.raises(TimeoutError):backend.tick(1000.8)
    backend.stop()
    assert port.write.call_args.args[0]==b'ZSTOP\n'


def test_hold_callback_invalid_observation_stops_z_but_homing_is_explicit():
    import threading
    from types import SimpleNamespace
    from arm_controller_pkg.arm_controller_xy_tracker import XYTracker
    control,_=make_control()
    node=SimpleNamespace(z_control=control,tracking_ready=True,goal_lock=threading.Lock(),
                         harvest=None,latest='old',hold_requested=False)
    control.phase='MOVING_Z'
    XYTracker.hold_callback(node,None)
    assert control.stop_pending and node.latest is None
    control.stop_pending=False;control.phase='HOMING';control.homing=True
    XYTracker.hold_callback(node,None)
    assert not control.stop_pending
