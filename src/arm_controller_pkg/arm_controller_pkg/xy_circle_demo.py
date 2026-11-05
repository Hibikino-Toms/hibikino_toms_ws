"""Publish a preflighted, fixed-Z XY circle as PoseStamped targets."""
import math

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import Bool, Float64MultiArray

from .arm_controller_xy_tracker import load_config
from .modules.ik_solver_arm3 import InverseKinematicsSolver


class XYCircleDemo(Node):
    def __init__(self):
        super().__init__("arm_xy_circle_demo")
        self.declare_parameter("config_file", "")
        self.declare_parameter("goal_topic", "/arm_xy/goal")
        self.declare_parameter("actual_topic", "/arm_xy/actual")
        self.declare_parameter("frame_id", "arm_base")
        self.declare_parameter("radius", 0.05)
        self.declare_parameter("center_x", 0.0)
        self.declare_parameter("center_y", 0.0)
        self.declare_parameter("center_mode", "current_start")
        self.declare_parameter("period", 20.0)
        self.declare_parameter("publish_rate", 10.0)
        self.declare_parameter("initial_phase", 0.0)
        self.declare_parameter("direction", 1.0)
        self.declare_parameter("revolutions", 0)
        self.declare_parameter("fixed_yaw_rad", 0.0)
        self.declare_parameter("follow_start_yaw", True)
        self.declare_parameter("approach_duration", 3.0)
        config_path = self.get_parameter("config_file").value
        if not config_path:
            raise RuntimeError("Set config_file (see config/xy_tracking.yaml)")
        self.config = load_config(config_path)
        settings = dict(self.config["ik_solver_params"])
        dxl = self.config["dxl_params"]
        settings["joint_limits_deg"] = self.config.get("joint_limits_deg") or [
            [float(dxl[k + "_MIN_DEG"]) - offset, float(dxl[k + "_MAX_DEG"]) - offset]
            for k, offset in (("DXL_1", 90), ("DXL_3", 90), ("DXL_5", 180))]
        self.solver = InverseKinematicsSolver(settings)
        self.current = None
        self.tracker_ready = False
        self.current_joints = None
        self.start_pose = None
        self.timer = None
        qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.actual_sub = self.create_subscription(PoseStamped, self.get_parameter("actual_topic").value,
                                                   self.actual_callback, qos)
        self.joint_sub = self.create_subscription(Float64MultiArray, "/arm_xy/joints", self.joint_callback, qos)
        self.pub = self.create_publisher(PoseStamped, self.get_parameter("goal_topic").value, 1)
        self.ready_sub = self.create_subscription(Bool, "/arm_xy/ready", self.ready_callback,
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                       reliability=ReliabilityPolicy.RELIABLE))
        rate = float(self.get_parameter("publish_rate").value)
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError("publish_rate must be positive and finite")
        self.rate = rate
        self.start_timer = self.create_timer(1.0 / rate, self.start_when_ready)
        self.get_logger().info("Waiting for /arm_xy/ready and measured pose before circle preflight")

    def ready_callback(self, msg):
        self.tracker_ready = msg.data
        # Require new measurements following initialization, not a cached pose.
        self.current = None
        self.current_joints = None

    def actual_callback(self, msg):
        p, q = msg.pose.position, msg.pose.orientation
        yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1 - 2*(q.y*q.y + q.z*q.z))
        self.current = (p.x, p.y, p.z, yaw)

    def joint_callback(self, msg):
        if len(msg.data) == 3 and all(math.isfinite(v) for v in msg.data):
            self.current_joints = list(msg.data)

    def start_when_ready(self):
        if not self.tracker_ready or self.current is None or self.current_joints is None:
            return
        self.destroy_timer(self.start_timer)
        radius = float(self.get_parameter("radius").value)
        period = float(self.get_parameter("period").value)
        direction = float(self.get_parameter("direction").value)
        turns = int(self.get_parameter("revolutions").value)
        phase = float(self.get_parameter("initial_phase").value)
        mode = self.get_parameter("center_mode").value
        approach = float(self.get_parameter("approach_duration").value)
        if (not all(math.isfinite(v) for v in (radius, period, direction, phase, approach)) or
                radius <= 0 or period <= 0 or approach < 0 or abs(abs(direction) - 1.0) > 1e-9 or turns < 0 or
                mode not in ("current_start", "configured")):
            self.get_logger().error("Invalid circle parameters; no goals published")
            self.timer = None
            return
        sx, sy, z, start_yaw = self.current
        self.start_pose = (sx, sy, z, start_yaw)
        if self.get_parameter("follow_start_yaw").value:
            yaw = start_yaw
        else:
            yaw = float(self.get_parameter("fixed_yaw_rad").value)
        if mode == "current_start":
            cx, cy = sx - radius * math.cos(phase), sy - radius * math.sin(phase)
            position_approach = 0.0
        else:
            cx, cy = float(self.get_parameter("center_x").value), float(self.get_parameter("center_y").value)
            position_approach = approach
        if not math.isfinite(cx) or not math.isfinite(cy) or not math.isfinite(yaw):
            self.get_logger().error("Center/yaw must be finite; no goals published")
            return
        yaw_delta = (yaw - start_yaw + math.pi) % (2.0 * math.pi) - math.pi
        yaw_approach = approach if abs(yaw_delta) > 1e-3 else 0.0
        approach = max(position_approach, yaw_approach)
        self.circle = (cx, cy, z, yaw, radius, period, direction, phase, turns, approach)
        start_result = self.solver.solve([sx, sy, start_yaw], self.current_joints)
        if not start_result.success:
            self.get_logger().error(f"Circle preflight failed at measured start: {start_result.reason}")
            self.timer = None
            return
        q = start_result.joints
        approach_points = max(1, math.ceil(approach * self.rate))
        for i in range(1, approach_points + 1):
            f = i / approach_points
            x = sx + f * (cx + radius * math.cos(phase) - sx)
            y = sy + f * (cy + radius * math.sin(phase) - sy)
            step_yaw = start_yaw + f * yaw_delta
            result = self.solver.solve([x, y, step_yaw], q)
            if not result.success:
                self.get_logger().error(f"Circle approach unreachable at sample {i}: {result.reason}")
                self.timer = None
                return
            q = result.joints
        for i in range(1, 145):
            theta = phase + direction * 2.0 * math.pi * i / 144
            result = self.solver.solve([cx + radius*math.cos(theta), cy + radius*math.sin(theta), yaw], q)
            if not result.success:
                joints_deg = [round(math.degrees(v), 3) for v in result.joints]
                limits_deg = [[round(math.degrees(v), 3) for v in row]
                                               for row in self.solver.limits]
                self.get_logger().error(
                    f"Circle preflight failed at {math.degrees(theta):.1f}deg: {result.reason}; "
                    f"joints_deg={joints_deg}, limits_deg={limits_deg}, "
                    f"position_error_m={result.position_error_m:.6f}, "
                    f"yaw_error_rad={result.angle_error_rad:.6f}; no goals published")
                self.timer = None
                return
            q = result.joints
        self.started_ns = self.get_clock().now().nanoseconds
        self.first_point = (cx + radius*math.cos(phase), cy + radius*math.sin(phase))
        self.get_logger().info(f"Preflight passed: center=({cx:.3f},{cy:.3f})m radius={radius:.3f}m, yaw={yaw:.3f}rad, fixed z={z:.3f}m")
        self.timer = self.create_timer(1.0 / self.rate, self.publish_tick)
        self.publish_pose(sx, sy, z, start_yaw)

    def publish_tick(self):
        if not self.tracker_ready:
            return
        cx, cy, z, yaw, radius, period, direction, phase, turns, approach = self.circle
        elapsed = (self.get_clock().now().nanoseconds - self.started_ns) / 1e9
        start_x, start_y, start_z, start_yaw = self.start_pose
        if approach > 0 and elapsed < approach:
            f = max(0., elapsed / approach)
            x = start_x + f * (self.first_point[0] - start_x)
            y = start_y + f * (self.first_point[1] - start_y)
            yaw_delta = (yaw - start_yaw + math.pi) % (2.0 * math.pi) - math.pi
            output_yaw = start_yaw + f * yaw_delta
        else:
            circle_elapsed = max(0., elapsed - approach)
            if turns and circle_elapsed >= turns * period:
                theta = phase + direction * 2. * math.pi * turns
            else:
                theta = phase + direction * 2. * math.pi * circle_elapsed / period
            x, y = cx + radius*math.cos(theta), cy + radius*math.sin(theta)
            output_yaw = yaw
        self.publish_pose(x, y, z, output_yaw)
        if turns and elapsed >= approach + turns * period:
            self.get_logger().info("Circle demo complete; last target remains held")
            self.destroy_timer(self.timer)
            self.timer = None

    def publish_pose(self, x, y, z, yaw):
        msg = PoseStamped()
        msg.header.frame_id = self.get_parameter("frame_id").value
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = x, y, z
        msg.pose.orientation.z, msg.pose.orientation.w = math.sin(yaw/2.), math.cos(yaw/2.)
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = XYCircleDemo()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except rclpy.exceptions.RCLError:
                pass
