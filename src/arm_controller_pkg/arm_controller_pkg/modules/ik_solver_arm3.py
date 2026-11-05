"""Bounded damped-least-squares IK for the existing planar arm.

Public coordinates use metres and radians. The geometry preserves the legacy
FK convention: link 1 has the fixed perpendicular offset ``(L1, L2)``.
"""
from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class IKResult:
    success: bool
    reason: str
    joints: np.ndarray
    position_error_m: float
    angle_error_rad: float
    iterations: int


class InverseKinematicsSolver:
    def __init__(self, params):
        self.lengths = np.asarray([
            float(params[k]) / 1000.0
            for k in ("Link1", "Link2", "Link3", "Link4")
        ])
        if self.lengths.shape != (4,) or not np.all(np.isfinite(self.lengths)) or np.any(self.lengths <= 0):
            raise ValueError("link lengths must be four positive finite millimetre values")
        self.max_iterations = int(params.get("MAX_LOOP_NUM", 80))
        self.position_tolerance = float(params.get("position_tolerance_m", 0.002))
        self.angle_tolerance = float(params.get("angle_tolerance_rad", math.radians(1.0)))
        self.max_step = float(params.get("max_joint_step_rad", 0.08))
        self.damping = float(params.get("damping", 0.025))
        self.angle_length = float(params.get("angle_length_m", 0.15))
        limits_to_check = [self.position_tolerance, self.angle_tolerance,
                           self.max_step, self.damping, self.angle_length]
        if (self.max_iterations < 1 or not all(math.isfinite(v) for v in limits_to_check) or
                self.position_tolerance <= 0 or self.angle_tolerance <= 0 or
                self.max_step <= 0 or self.damping <= 0 or self.angle_length <= 0):
            raise ValueError("invalid IK solver limits")
        # Intervals are populated from calibrated Dynamixel limits by the node.
        default_deg = params.get("joint_limits_deg", [[-10, 180], [-30, 175], [-165, 135]])
        limits = np.asarray(default_deg, dtype=float)
        if limits.shape != (3, 2) or not np.all(np.isfinite(limits)) or np.any(limits[:, 0] >= limits[:, 1]):
            raise ValueError("joint_limits_deg must be three finite [min,max] intervals")
        self.limits = np.radians(limits)

    @staticmethod
    def _vector(values, shape, label):
        result = np.asarray(values, dtype=float)
        if result.shape != shape or not np.all(np.isfinite(result)):
            raise ValueError(f"{label} must have shape {shape} and finite values")
        return result

    def forward_kinematics(self, joints):
        q = self._vector(joints, (3,), "joints")
        q1, q2, q3 = q
        l1, l2, l3, l4 = self.lengths
        t1, t12, t123 = q1, q1 + q2, q1 + q2 + q3
        x = l1 * math.cos(t1) - l2 * math.sin(t1) + l3 * math.cos(t12) + l4 * math.cos(t123)
        y = l1 * math.sin(t1) + l2 * math.cos(t1) + l3 * math.sin(t12) + l4 * math.sin(t123)
        return np.asarray([x, y, t123])

    def jacobian(self, joints):
        q1, q2, q3 = self._vector(joints, (3,), "joints")
        l1, l2, l3, l4 = self.lengths
        t1, t12, t123 = q1, q1 + q2, q1 + q2 + q3
        return np.asarray([
            [-l1 * math.sin(t1) - l2 * math.cos(t1) - l3 * math.sin(t12) - l4 * math.sin(t123),
             -l3 * math.sin(t12) - l4 * math.sin(t123), -l4 * math.sin(t123)],
            [l1 * math.cos(t1) - l2 * math.sin(t1) + l3 * math.cos(t12) + l4 * math.cos(t123),
             l3 * math.cos(t12) + l4 * math.cos(t123), l4 * math.cos(t123)],
            [1., 1., 1.],
        ])

    @staticmethod
    def wrap(angle):
        return (angle + math.pi) % (2.0 * math.pi) - math.pi

    def solve(self, goal, current_joints):
        goal = self._vector(goal, (3,), "goal [x_m,y_m,yaw_rad]")
        q = self._vector(current_joints, (3,), "current_joints").copy()
        if np.any(q < self.limits[:, 0]) or np.any(q > self.limits[:, 1]):
            pose = self.forward_kinematics(q)
            return IKResult(False, "current_joint_limit", q, float(np.linalg.norm(goal[:2] - pose[:2])), abs(self.wrap(goal[2] - pose[2])), 0)
        for iteration in range(self.max_iterations + 1):
            pose = self.forward_kinematics(q)
            error = np.asarray([goal[0] - pose[0], goal[1] - pose[1], self.wrap(goal[2] - pose[2])])
            pos_error = float(np.linalg.norm(error[:2]))
            ang_error = abs(float(error[2]))
            if pos_error <= self.position_tolerance and ang_error <= self.angle_tolerance:
                return IKResult(True, "converged", q.copy(), pos_error, ang_error, iteration)
            if iteration == self.max_iterations:
                break
            scale = np.diag([1., 1., self.angle_length])
            j_scaled = scale @ self.jacobian(q)
            e_scaled = scale @ error
            # DLS avoids unbounded updates as the smallest singular value falls.
            delta = j_scaled.T @ np.linalg.solve(j_scaled @ j_scaled.T + self.damping**2 * np.eye(3), e_scaled)
            largest = float(np.max(np.abs(delta)))
            if largest > self.max_step:
                delta *= self.max_step / largest
            candidate = q + delta
            q = np.clip(candidate, self.limits[:, 0], self.limits[:, 1])
        pose = self.forward_kinematics(q)
        at_limit = np.any(np.isclose(q, self.limits[:, 0], atol=1e-7) |
                          np.isclose(q, self.limits[:, 1], atol=1e-7))
        return IKResult(False, "joint_limit" if at_limit else "no_convergence",
                        q.copy(), float(np.linalg.norm(goal[:2] - pose[:2])),
                        abs(self.wrap(goal[2] - pose[2])), self.max_iterations)

    def _error(self, goal, joints):
        pose = self.forward_kinematics(joints)
        return np.asarray([goal[0] - pose[0], goal[1] - pose[1], self.wrap(goal[2] - pose[2])])

    # Legacy-shaped wrapper: all three legacy vectors are mm/degree.
    def solve_ik(self, P_current, P_goal, pre_Q):
        del P_current  # FK state always comes from the supplied joint vector.
        result = self.solve([float(P_goal[0]) / 1000., float(P_goal[1]) / 1000., math.radians(float(P_goal[2]))], np.radians(pre_Q))
        pose = self.forward_kinematics(result.joints)
        return np.asarray([pose[0] * 1000., pose[1] * 1000., math.degrees(pose[2])]), np.degrees(result.joints), result.success
