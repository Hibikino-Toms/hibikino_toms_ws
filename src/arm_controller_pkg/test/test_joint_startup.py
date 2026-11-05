"""Initialization profiles and circle start gating, without hardware."""
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from arm_controller_pkg.modules.joint_startup import JointStartup
from arm_controller_pkg.modules.ik_solver_arm3 import InverseKinematicsSolver


def make_motion(**kwargs):
    return JointStartup([[0.4, -0.2, 0.1], [0.5, 0.1, 0.2]],
                        [[-1, 1]] * 3, 0.25, 0.8, **kwargs)


def test_waypoints_wait_for_measurement_and_velocity_acceleration_bounds():
    motion = make_motion()
    measured = [0., 0., 0.]
    commands = []
    dt = .01
    for i in range(2000):
        command, done = motion.step(measured, i * dt)
        commands.append(command)
        measured = command
        if done:
            break
    assert done and motion.index == 2
    assert commands[0] == [0., 0., 0.]
    assert np.allclose(commands[-1], [0.5, 0.1, 0.2])
    velocity = np.diff(commands, axis=0) / dt
    acceleration = np.diff(velocity, axis=0) / dt
    assert np.max(np.abs(velocity)) <= .25 + 1e-6
    assert np.max(np.abs(acceleration)) <= .8 + 1e-6


def test_no_arrival_no_ready_and_bounded_timeout():
    motion = make_motion(timeout=8.)
    motion.step([0., 0., 0.], 0.)
    command, done = motion.step([0., 0., 0.], 7.)
    assert command == motion.waypoints[0] and not done
    with pytest.raises(RuntimeError, match='timed out'):
        motion.step([0., 0., 0.], 8.1)


@pytest.mark.parametrize('points', [[[math.nan, 0, 0]], [[2., 0, 0]], [[0, 0]], []])
def test_invalid_waypoints(points):
    with pytest.raises(ValueError):
        JointStartup(points, [[-1, 1]]*3, .25, .8)


def test_configured_demo_circle_preflight_both_directions():
    config = yaml.safe_load((Path(__file__).parents[1] / 'config/xy_robot_config.yaml').read_text())
    params = dict(config['ik_solver_params'], joint_limits_deg=[[-10, 180], [-30, 175], [-165, 135]])
    solver = InverseKinematicsSolver(params)
    home = config['startup']['home_joints_deg']
    assert home == [5., 170., -75.]
    initial = np.radians(config['startup']['demo_joints_deg'])
    pose = solver.forward_kinematics(initial)
    assert sum(config['startup']['demo_joints_deg']) == sum(home)
    for direction in (-1, 1):
        q = initial
        for i in range(145):
            theta = direction * 2 * math.pi * i / 144
            goal = [pose[0] - .05 + .05 * math.cos(theta), pose[1] + .05 * math.sin(theta), pose[2]]
            result = solver.solve(goal, q)
            assert result.success, (direction, i, result.reason)
            q = result.joints


def test_circle_waits_for_ready_and_refreshes_cached_measurements():
    from arm_controller_pkg.xy_circle_demo import XYCircleDemo
    node = SimpleNamespace(tracker_ready=False, current=(1, 2, 0, 0), current_joints=[0, 0, 0])
    XYCircleDemo.start_when_ready(node)  # No parameter or timer access while not ready.
    XYCircleDemo.ready_callback(node, SimpleNamespace(data=True))
    assert node.tracker_ready and node.current is None and node.current_joints is None
    XYCircleDemo.start_when_ready(node)


@pytest.mark.parametrize('turns,finishes', [(0, False), (1, True), (2, False)])
def test_circle_repeat_option(turns, finishes):
    from arm_controller_pkg.xy_circle_demo import XYCircleDemo
    published, stopped = [], []
    node = SimpleNamespace(tracker_ready=True, circle=(0., 0., 0., 0., .05, 2., 1., 0., turns, 0.),
        started_ns=0, start_pose=(.05, 0., 0., 0.), timer=object(),
        get_clock=lambda: SimpleNamespace(now=lambda: SimpleNamespace(nanoseconds=3_000_000_000)),
        publish_pose=lambda *args: published.append(args),
        get_logger=lambda: SimpleNamespace(info=lambda msg: None),
        destroy_timer=lambda timer: stopped.append(timer))
    XYCircleDemo.publish_tick(node)
    assert bool(stopped) == finishes
    assert len(published) == 1
