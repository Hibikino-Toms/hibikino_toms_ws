"""Startup register ordering and failures, without importing/opening the SDK."""
from pathlib import Path
from types import SimpleNamespace
import threading
import time

import pytest
import yaml

from arm_controller_pkg.modules.stream_motor_backend import DynamixelFiveMotorBackend


class FakePacket:
    def __init__(self):
        self.registers = {(i, address): value for i in range(1, 6)
                          for address, value in ((11, 3), (10, 0), (64, 0))}
        self.events = []
        self.fail = None
        self.ignore = None
        self.read_sequences = {}

    def read(self, port, motor_id, address):
        event = ('read', motor_id, address)
        self.events.append(event)
        sequence = self.read_sequences.get((motor_id, address), [])
        if sequence:
            return sequence.pop(0), 0, int(event == self.fail)
        return self.registers.get((motor_id, address), 0), 0, int(event == self.fail)

    def write(self, port, motor_id, address, value):
        event = ('write', motor_id, address, value)
        self.events.append(event)
        if event != self.fail and (motor_id, address) != self.ignore:
            self.registers[motor_id, address] = value
        return 0, int(event == self.fail)

    read1ByteTxRx = read
    read4ByteTxRx = read
    write1ByteTxRx = write
    write4ByteTxRx = write


@pytest.fixture
def backend():
    config = Path(__file__).parents[1] / 'config' / 'xy_robot_config.yaml'
    obj = DynamixelFiveMotorBackend.__new__(DynamixelFiveMotorBackend)
    obj.params = yaml.safe_load(config.read_text())['dxl_params']
    obj.ids = [1, 2, 3, 4, 5]
    obj.min_tick, obj.max_tick, obj.max_angle = 0, 4095, 360.
    obj._comm_success = 0
    obj.packet = FakePacket()
    obj.port = SimpleNamespace(is_open=True)
    obj.port.closePort = lambda: setattr(obj.port, 'is_open', False)
    # Deliberately preserve small discrepancies between paired encoders.
    obj._read_ticks = lambda: [1200, 2890, 2200, 1890, 1800]
    for motor_id, tick in zip(obj.ids, obj._read_ticks()):
        obj.packet.registers[motor_id, 132] = tick
    return obj


def torque_writes(backend):
    return [e for e in backend.packet.events if e[0] == 'write' and e[2] == 64]


def test_stage_all_five_measured_positions_before_enabling(backend):
    assert backend.activate() == [1, 2, 3, 4, 5]
    events = backend.packet.events
    first_enable = next(i for i, e in enumerate(events) if e[0] == 'write' and e[2] == 64)
    for motor_id, tick in zip(backend.ids, backend._read_ticks()):
        assert ('write', motor_id, 116, tick) in events[:first_enable]
        assert ('read', motor_id, 116) in events[:first_enable]
        assert backend.packet.registers[motor_id, 64] == 1
    assert torque_writes(backend) == [('write', i, 64, 1) for i in backend.ids]
    assert events[-5:] == [('read', i, 64) for i in backend.ids]


def test_already_enabled_motors_are_not_toggled(backend):
    backend.packet.registers[2, 64] = 1
    backend.packet.registers[4, 64] = 1
    backend.activate()
    assert torque_writes(backend) == [('write', i, 64, 1) for i in (1, 3, 5)]


@pytest.mark.parametrize('address,value', [(11, 4), (10, 8), (64, 2)])
def test_invalid_mode_or_torque_aborts_before_writes(backend, address, value):
    backend.packet.registers[5, address] = value
    with pytest.raises(RuntimeError, match='DXL 5'):
        backend.activate()
    assert not any(e[0] == 'write' for e in backend.packet.events)


@pytest.mark.parametrize('tick', [-1, 5000, 0])
def test_invalid_position_aborts_before_writes(backend, tick):
    backend._read_ticks = lambda: [1200, 2890, 2200, 1890, tick]
    with pytest.raises(RuntimeError, match='DXL 5'):
        backend.activate()
    assert not any(e[0] == 'write' for e in backend.packet.events)


@pytest.mark.parametrize('failure', [('read', 5, 64), ('write', 3, 116, 2200),
                                   ('read', 4, 116)])
def test_communication_error_prevents_torque_enable(backend, failure):
    backend.packet.fail = failure
    with pytest.raises(RuntimeError, match='failed'):
        backend.activate()
    assert torque_writes(backend) == []


def test_hold_goal_readback_mismatch_prevents_enable(backend):
    backend.packet.ignore = (5, 116)
    backend.packet.registers[5, 132] = 1801
    with pytest.raises(RuntimeError, match='hold goal readback') as raised:
        backend.activate()
    assert torque_writes(backend) == []
    assert 'expected=1800' in str(raised.value)
    assert 'readbacks=[0,' in str(raised.value)
    assert 'present_now=1801, torque=0' in str(raised.value)


def test_stale_readback_then_exact_value_allows_activation(backend):
    backend.packet.read_sequences[2, 116] = [2000, 2000]
    assert backend.activate() == backend.ids
    report = backend.startup_readback_report[1]
    assert report['samples'] == [2000, 2000, 2890]
    assert report['expected'] == 2890
    # Exactly one write; reads may repeat. Every hold is checked before torque.
    assert backend.packet.events.count(('write', 2, 116, 2890)) == 1
    first_enable = next(i for i, e in enumerate(backend.packet.events)
                        if e[0] == 'write' and e[2] == 64)
    assert backend.packet.events[:first_enable].count(('read', 2, 116)) == 4


def test_one_tick_mismatch_without_matching_present_is_rejected(backend):
    backend.packet.ignore = (1, 116)
    backend.packet.registers[1, 116] = 1201
    backend.params['startup_readback_timeout_ms'] = 10
    with pytest.raises(RuntimeError, match='expected=1200, readbacks=\\[1201,'):
        backend.activate()
    assert torque_writes(backend) == []


def test_reported_2180_2181_torque_off_case(backend):
    backend._read_ticks = lambda: [1200, 2890, 2180, 1890, 1800]
    backend.packet.ignore = (3, 116)
    backend.packet.registers[3, 116] = 2181
    backend.packet.registers[3, 132] = 2181
    assert backend.activate() == backend.ids
    report = backend.startup_readback_report[2]
    assert report['reason'] == 'current_hold'
    assert report['expected'] == 2180 and report['present'] == 2181
    assert report['samples'] == [2181, 2181]
    assert all(backend.packet.registers[i, 64] == 1 for i in backend.ids)


def test_configured_start_accepts_hand_motion_without_strict_readback(backend):
    backend.params['startup_hold_check'] = 'acknowledged'
    backend.packet.registers[5, 132] = 1803
    backend.packet.read_sequences[3, 116] = [2201, 2200, 2201, 2201]
    assert backend.activate() == backend.ids
    assert ('write', 5, 116, 1803) in backend.packet.events
    assert not any(e[0] == 'read' and e[2] == 116 for e in backend.packet.events)
    assert all(backend.packet.registers[i, 64] == 1 for i in backend.ids)


@pytest.mark.parametrize('failure', [('read', 3, 132), ('write', 3, 116, 2200)])
def test_configured_start_still_checks_communication(backend, failure):
    backend.params['startup_hold_check'] = 'acknowledged'
    backend.packet.fail = failure
    with pytest.raises(RuntimeError, match='failed'):
        backend.activate()
    assert torque_writes(backend) == []


def test_configured_start_checks_fresh_position_range(backend):
    backend.params['startup_hold_check'] = 'acknowledged'
    backend.packet.registers[5, 132] = 5000
    with pytest.raises(RuntimeError, match='outside single-turn'):
        backend.activate()
    assert torque_writes(backend) == []


@pytest.mark.parametrize('delta', [-1, 1])
def test_one_count_current_hold_allowed_in_both_directions(backend, delta):
    backend.packet.ignore = (1, 116)
    backend.packet.registers[1, 116] = 1200 + delta
    backend.packet.registers[1, 132] = 1200 + delta
    assert backend.activate() == backend.ids


@pytest.mark.parametrize('torque,tolerance,delta', [(1, 1, 1), (0, 0, 1), (0, 1, 2), (0, 1, -2)])
def test_mismatch_rejected_for_on_strict_or_larger_delta(backend, torque, tolerance, delta):
    backend.packet.ignore = (1, 116)
    backend.packet.registers[1, 64] = torque
    backend.packet.registers[1, 116] = 1200 + delta
    backend.packet.registers[1, 132] = 1200 + delta
    backend.params['startup_hold_tolerance_ticks'] = tolerance
    backend.params['startup_readback_timeout_ms'] = 10
    with pytest.raises(RuntimeError, match='hold goal readback mismatch'):
        backend.activate()
    assert torque_writes(backend) == []


def test_final_check_rejects_drift_after_exact_goal_verification(backend):
    backend.packet.registers[5, 132] = 1803
    with pytest.raises(RuntimeError, match='startup hold changed before torque ON'):
        backend.activate()
    assert torque_writes(backend) == []


def test_one_count_cannot_cross_configured_limit(backend):
    backend.params['DXL_1_MAX_DEG'] = 1200.5 / 4095 * 360
    backend.packet.ignore = (1, 116)
    backend.packet.registers[1, 116] = 1201
    backend.packet.registers[1, 132] = 1201
    with pytest.raises(RuntimeError, match='outside'):
        backend.activate()
    assert torque_writes(backend) == []


@pytest.mark.parametrize('tolerance', [-1, 2, 0.5, float('nan'), True, '1'])
def test_invalid_tolerance_rejected_before_io(backend, tolerance):
    backend.params['startup_hold_tolerance_ticks'] = tolerance
    with pytest.raises(ValueError, match='startup_hold_tolerance_ticks'):
        backend.activate()
    assert backend.packet.events == []


@pytest.mark.parametrize('timeout', [0, -1, float('nan'), float('inf'), 1001])
def test_invalid_readback_timeout_rejected_before_io(backend, timeout):
    backend.params['startup_readback_timeout_ms'] = timeout
    with pytest.raises(ValueError, match='startup_readback_timeout_ms'):
        backend.activate()
    assert backend.packet.events == []


def test_diagnostic_read_failure_preserves_mismatch(backend):
    backend.packet.ignore = (1, 116)
    backend.packet.fail = ('read', 1, 132)
    backend.params['startup_readback_timeout_ms'] = 10
    with pytest.raises(RuntimeError, match='hold goal readback mismatch') as raised:
        backend.activate()
    assert 'present_now=unavailable' in str(raised.value)
    assert torque_writes(backend) == []


@pytest.mark.parametrize('failure_kind', ['error', 'ignored'])
def test_torque_failure_aborts_without_disabling_any_motor(backend, failure_kind):
    if failure_kind == 'error':
        backend.packet.fail = ('write', 3, 64, 1)
    else:
        backend.packet.ignore = (3, 64)
    with pytest.raises(RuntimeError, match='DXL 3'):
        backend.activate()
    assert backend.packet.registers[1, 64] == 1
    assert all(e[3] == 1 for e in torque_writes(backend))


def test_close_keeps_torque_enabled(backend):
    backend.activate()
    before = list(backend.packet.events)
    backend.close()
    assert not backend.port.is_open
    assert backend.packet.events == before


def test_tracker_activation_conflict_and_failure_latch(backend):
    # Invoke the callback without creating a ROS context or a serial port.
    from arm_controller_pkg.arm_controller_xy_tracker import XYTracker

    errors = []
    tracker = SimpleNamespace(
        activation_failed=False, backend_active=False, previous_tick=None,
        io_lock=threading.Lock(), goal_lock=threading.Lock(), latest=None,
        backend=backend, last_tick=time.monotonic(), last_metric_log=time.monotonic(),
        periods=[], over_100ms=0, diag={},
        get_parameter=lambda name: SimpleNamespace(value=['/arm_service']),
        get_service_names_and_types=lambda: [('/arm_service', [])],
        get_logger=lambda: SimpleNamespace(error=errors.append),
    )
    XYTracker._control_tick(tracker)
    assert not backend.packet.events  # Competing controller blocks even activation.
    assert not tracker.backend_active
    tracker.get_service_names_and_types = lambda: []
    backend.packet.registers[1, 11] = 4
    XYTracker._control_tick(tracker)
    assert tracker.activation_failed
    assert not tracker.backend_active
    assert 'activation failed' in errors[-1]
    before = list(backend.packet.events)
    XYTracker._control_tick(tracker)
    assert backend.packet.events == before  # No repeated torque-on attempts.


def test_active_tracker_communication_fault_latches_without_torque_off():
    from unittest.mock import Mock
    from arm_controller_pkg.arm_controller_xy_tracker import XYTracker
    backend=Mock()
    backend.read_joints.side_effect=RuntimeError('bus timeout')
    tracker=SimpleNamespace(
        activation_failed=False,backend_active=True,tracking_ready=True,previous_tick=None,
        io_lock=threading.Lock(),goal_lock=threading.Lock(),latest=None,backend=backend,
        last_tick=time.monotonic(),last_metric_log=time.monotonic(),periods=[],over_100ms=0,diag={},
        get_parameter=lambda name:SimpleNamespace(value=[]),get_service_names_and_types=lambda:[],
        ready_pub=Mock(),send_command=Mock(),get_logger=lambda:Mock())
    XYTracker._control_tick(tracker)
    assert tracker.activation_failed and tracker.diag['reason']=='backend_fault'
    assert tracker.ready_pub.publish.call_args.args[0].data is False
    tracker.send_command.assert_not_called()
    count=backend.read_joints.call_count
    XYTracker._control_tick(tracker)
    assert backend.read_joints.call_count==count


def test_goal_slot_rejects_out_of_order_observations():
    from geometry_msgs.msg import PoseStamped
    from arm_controller_pkg.arm_controller_xy_tracker import XYTracker
    params=dict(frame_id='arm_base',stamp_max_age_sec=2.,stamp_future_tolerance_sec=.2,
                plane_z_m=0.,max_goal_xy_m=1.)
    clock=SimpleNamespace(now=lambda:SimpleNamespace(nanoseconds=10_000_000_000,to_msg=lambda:None))
    tracker=SimpleNamespace(tracking_ready=True,get_clock=lambda:clock,
        get_parameter=lambda key:SimpleNamespace(value=params[key]),goal_lock=threading.Lock(),
        last_accepted_stamp=0.,latest=None,rejected=0)
    msg=PoseStamped();msg.header.frame_id='arm_base';msg.header.stamp.sec=10
    msg.pose.orientation.w=1.;msg.pose.position.x=.1
    XYTracker.goal_callback(tracker,msg)
    msg.header.stamp.sec=9;msg.header.stamp.nanosec=900_000_000;msg.pose.position.x=.2
    XYTracker.goal_callback(tracker,msg)
    assert tracker.latest[0]==.1 and tracker.rejected==1
