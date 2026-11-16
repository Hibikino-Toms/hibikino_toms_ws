"""Assembly-reference, inverse-command and zero-offset geometry regressions."""
import copy
import math
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
import yaml

from arm_controller_pkg.modules.can_mixed_backend import CanMixedMotorBackend, _DynamixelQ3
from arm_controller_pkg.modules.ik_solver_arm3 import InverseKinematicsSolver


def robot_config():
    path = Path(__file__).parents[1] / "config/xy_robot_config.yaml"
    return yaml.safe_load(path.read_text())


def calibrated_backend(config):
    backend = CanMixedMotorBackend(config["can_mixed_backend"], config["dxl_params"],
                                   np.radians(config["joint_limits_deg"]).tolist())
    backend.calibration = {
        name: backend._calibration_axis(backend.params, name) for name in ("q1", "q2")}
    return backend


def fake_q3(trim=0.0):
    """Use the real conversion methods without constructing any serial device."""
    adapter = _DynamixelQ3.__new__(_DynamixelQ3)
    adapter.params = robot_config()["dxl_params"]
    adapter.angle_trim_deg = trim
    adapter.min_tick, adapter.max_tick = 0, 4095
    adapter.max_angle = 360.0
    adapter.min_deg, adapter.max_deg = 15.0, 315.0
    adapter._read = Mock(return_value=2048)
    adapter._write = Mock()
    return adapter


def test_operator_straight_reference_maps_to_y_axis_and_back():
    config = robot_config()
    backend = calibrated_backend(config)
    q = [backend._joint_from_position(-11000, "q1"),
         backend._joint_from_position(17000, "q2"), 0.0]
    assert np.degrees(q) == pytest.approx([90.0, 0.0, 0.0])
    assert backend._motor_target(q[0], "q1") == -11000
    assert backend._motor_target(q[1], "q2") == 17000

    solver = InverseKinematicsSolver(config["ik_solver_params"])
    assert config["ik_solver_params"]["Link2"] == 0
    assert solver.forward_kinematics(q) == pytest.approx([0.0, 0.620, math.pi / 2], abs=1e-12)
    # Joint centres, excluding the final 75 mm tool link.
    assert (0.270 * math.cos(q[0]) + 0.275 * math.cos(q[0] + q[1])) == pytest.approx(0, abs=1e-12)
    assert (0.270 * math.sin(q[0]) + 0.275 * math.sin(q[0] + q[1])) == pytest.approx(0.545)


@pytest.mark.parametrize("direction", [-1, 1])
@pytest.mark.parametrize("trim", [-0.75, 0, 0.5])
def test_rmd_trim_direction_inverse_and_bound_round_trip(direction, trim):
    config = copy.deepcopy(robot_config())
    for name in ("q1", "q2"):
        config["can_mixed_backend"][name].update(direction=direction, angle_trim_deg=trim)
    backend = calibrated_backend(config)
    bounds = backend._derive_bounds()
    for index, name in enumerate(("q1", "q2")):
        axis = config["can_mixed_backend"][name]
        raw_ref = axis["reference_motor_cdeg"]
        assert math.degrees(backend._joint_from_position(raw_ref, name)) == pytest.approx(
            axis["reference_joint_deg"] + trim)
        assert backend._motor_target(math.radians(axis["reference_joint_deg"] + trim), name) == raw_ref
        endpoints = []
        for q in backend.joint_limits_rad[index]:
            target = backend._motor_target(q, name)
            endpoints.append(target)
            assert abs(backend._joint_from_position(target, name) - q) <= math.radians(0.00501)
        assert bounds[2 * index:2 * index + 2] == [min(endpoints), max(endpoints)]
    # Large multi-turn angles are never folded into +/-180 degrees.
    raw = backend._motor_target(math.radians(278.31), "q2")
    assert math.degrees(backend._joint_from_position(raw, "q2")) == pytest.approx(278.31)


@pytest.mark.parametrize("trim", [-1.5, 0.0, 0.75])
def test_q3_feedback_and_command_use_inverse_trim(trim):
    q3 = fake_q3(trim)
    joint = q3.read_joint()
    assert math.degrees(joint) == pytest.approx(2048 / 4095 * 360 - 180 + trim)
    q3.send_joint(joint)
    q3._write.assert_called_once_with(116, 2048, 4)


def test_q3_trim_does_not_bypass_physical_motor_limit():
    q3 = fake_q3(trim=-2.0)
    # Logical 134deg would require motor angle316deg, beyond the315deg limit.
    with pytest.raises(ValueError, match="outside"):
        q3.send_joint(math.radians(134.0))
    q3._write.assert_not_called()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_calibration_trim_is_rejected(value):
    config = robot_config()
    config["can_mixed_backend"]["q1"]["angle_trim_deg"] = value
    with pytest.raises(ValueError, match="finite"):
        CanMixedMotorBackend._calibration_axis(config["can_mixed_backend"], "q1")
    with pytest.raises(ValueError, match="finite"):
        _DynamixelQ3({}, angle_trim_deg=value)


@pytest.mark.parametrize("offset", [-1.0, float("nan"), float("inf")])
def test_invalid_transverse_offset_rejected(offset):
    params = robot_config()["ik_solver_params"]
    params["Link2"] = offset
    with pytest.raises(ValueError):
        InverseKinematicsSolver(params)


@pytest.mark.parametrize("offset", [0.0, 61.75])
def test_jacobian_matches_finite_difference_with_and_without_offset(offset):
    params = robot_config()["ik_solver_params"]
    params["Link2"] = offset
    solver = InverseKinematicsSolver(params)
    q = np.radians([84.0, 25.0, -10.0])
    h = 1e-6
    fd = np.column_stack([
        (solver.forward_kinematics(q + np.eye(3)[i] * h) -
         solver.forward_kinematics(q - np.eye(3)[i] * h)) / (2 * h)
        for i in range(3)])
    assert np.allclose(solver.jacobian(q), fd, atol=1e-9)
    result = solver.solve(solver.forward_kinematics(q), q + np.radians([1.0, -2.0, 1.0]))
    assert result.success


def test_existing_calibration_without_trim_remains_compatible():
    config = robot_config()
    config["can_mixed_backend"].pop("q3", None)
    for name in ("q1", "q2"):
        config["can_mixed_backend"][name].pop("angle_trim_deg", None)
    backend = calibrated_backend(config)
    assert backend.q3_trim_deg == 0.0
    assert math.degrees(backend._joint_from_position(-11000, "q1")) == pytest.approx(90.0)


@pytest.mark.parametrize("direction", [-1, 1])
def test_default_circle_is_reachable_after_offset_removal(direction):
    config = robot_config()
    params = dict(config["ik_solver_params"], joint_limits_deg=config["joint_limits_deg"])
    solver = InverseKinematicsSolver(params)
    q = np.radians(config["startup"]["demo_joints_deg"])
    pose = solver.forward_kinematics(q)
    for i in range(145):
        theta = direction * 2 * math.pi * i / 144
        result = solver.solve([pose[0] - .05 + .05 * math.cos(theta),
                               pose[1] + .05 * math.sin(theta), pose[2]], q)
        assert result.success, (i, result.reason)
        q = result.joints
