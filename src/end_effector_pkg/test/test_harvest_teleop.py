"""EE interlocks use measured hold acknowledgements; no serial port or ROS graph."""
import json
from types import SimpleNamespace
from unittest.mock import Mock
from end_effector_pkg import pull_module_teleop as module


def make_node(monkeypatch):
    node=object.__new__(module.PullModuleTeleop)
    node.harvest_link=True;node.harvest_status=('APPROACH',100.,10.)
    node.request_started=100.
    node.selected_motor=1;node.motor_pwm=180
    node.get_clock=lambda:SimpleNamespace(now=lambda:SimpleNamespace(nanoseconds=10_100_000_000))
    node.get_logger=lambda:Mock()
    node._send=Mock();node._request_action=Mock(return_value=True)
    monkeypatch.setattr(module.time,'monotonic',lambda:100.)
    return node


def status(state,ready,stamp):
    return SimpleNamespace(data=json.dumps(dict(state=state,hold_ready=ready,stamp=stamp)))


def test_ee_operates_independently_in_approach(monkeypatch):
    node=make_node(monkeypatch)
    node._handle_key('w')
    node._send.assert_called_once_with('M1,180')
    node._request_action.assert_not_called()


def test_ee_operates_independently_during_startup_returned_fault_and_stale_state(monkeypatch):
    node=make_node(monkeypatch)
    for state in ('STARTUP', 'RETURNING', 'RETURNED', 'FAULT'):
        node.harvest_status=(state,100.,10.)
        node._handle_key('s')
    node.harvest_status=None
    node._handle_key('w')
    assert node._send.call_count == 5
    assert node._send.call_args_list[-1].args == ('M1,180',)
    node._request_action.assert_not_called()


def test_return_resume_keys_and_space_send_explicit_stop(monkeypatch):
    node=make_node(monkeypatch)
    node._handle_key('r')
    node._request_action.assert_called_with('pull')
    node._send.assert_called_with('STOP')
    node._handle_key('n')
    node._request_action.assert_called_with('resume')
    node._send.reset_mock()
    node._handle_key(' ')
    node._send.assert_called_once_with('STOP')
    node._request_action.assert_called_with('hold')


def test_link_disabled_keeps_original_ee_commands(monkeypatch):
    node=make_node(monkeypatch);node.harvest_link=False
    node._handle_key('w')
    node._send.assert_called_once_with('M1,180')
    node._request_action.assert_not_called()
