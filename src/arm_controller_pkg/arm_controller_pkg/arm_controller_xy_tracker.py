"""Latest-goal planar tracker. Harvest services remain a separate executable."""
import math
import json
import numpy as np
import threading
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.node import Node
from rclpy.impl.implementation_singleton import rclpy_implementation as _rclpy
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, Empty, Float64MultiArray, String
from std_srvs.srv import Trigger

from .modules.ik_solver_arm3 import InverseKinematicsSolver
from .modules.stream_motor_backend import DynamixelFiveMotorBackend, SimulatedMotorBackend
from .modules.can_mixed_backend import CanMixedMotorBackend
from .modules.joint_startup import JointStartup
from .modules.harvest_cycle import HarvestCycle
from .modules.yaw_joint_limiter import joint_step
from .modules.z_tracking import SerialZBackend, SimulatedZBackend, PixelZTrackingCoordinator


def load_config(path):
    import yaml
    with open(path, encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError("configuration must be a YAML mapping")
    return data


class XYTracker(Node):
    def __init__(self):
        super().__init__("arm_xy_tracker")
        self.declare_parameter("config_file", "")
        self.declare_parameter("backend", "")
        self.declare_parameter("startup_mode", "configured")
        self.declare_parameter("harvest_cycle_enabled", False)
        self.declare_parameter("require_ee_ready", False)
        self.declare_parameter("z_tracking_enabled", False)
        self.declare_parameter("control_rate_hz", 10.0)
        self.declare_parameter("goal_topic", "/arm_xy/goal")
        self.declare_parameter("frame_id", "arm_base")
        self.declare_parameter("goal_timeout_sec", 0.5)
        self.declare_parameter("max_joint_velocity_rad_s", 0.25)
        self.declare_parameter("max_joint_acceleration_rad_s2", 0.8)
        self.declare_parameter("plane_z_m", 0.0)
        self.declare_parameter("stamp_max_age_sec", 2.0)
        self.declare_parameter("stamp_future_tolerance_sec", 0.2)
        self.declare_parameter("max_goal_xy_m", 1.0)
        self.declare_parameter("control_conflict_services", ["/arm_service", "/arm_service_d435"])
        positive_params = ("goal_timeout_sec", "stamp_max_age_sec", "max_goal_xy_m",
                           "max_joint_velocity_rad_s", "max_joint_acceleration_rad_s2")
        for name in positive_params:
            value = float(self.get_parameter(name).value)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite")
        future_tolerance = float(self.get_parameter("stamp_future_tolerance_sec").value)
        plane_z = float(self.get_parameter("plane_z_m").value)
        if not math.isfinite(future_tolerance) or future_tolerance < 0 or not math.isfinite(plane_z):
            raise ValueError("timestamp tolerance and fixed Z configuration are invalid")
        config_path = self.get_parameter("config_file").value
        if not config_path:
            raise RuntimeError("Set config_file (see config/xy_tracking.yaml)")
        self.config = load_config(config_path)
        settings = self.config["ik_solver_params"]
        dxl = self.config["dxl_params"]
        # Joint-space limits are shared across hardware backends. Older configs
        # can still derive them from the legacy paired-Dynamixel calibration.
        limits = self.config.get("joint_limits_deg")
        if limits is None:
            limits = [[float(dxl[k + "_MIN_DEG"]) - off, float(dxl[k + "_MAX_DEG"]) - off]
                      for k, off in (("DXL_1", 90), ("DXL_3", 90), ("DXL_5", 180))]
        settings = dict(settings, joint_limits_deg=limits)
        self.declare_parameter("tracking_position_tolerance_m", 0.00001)
        self.declare_parameter("tracking_angle_tolerance_rad", 0.0001)
        # Small image corrections must survive widening application/IK acceptance.
        self.declare_parameter('tracking_correction_resolution_m', 0.0001)
        self.declare_parameter('tracking_correction_resolution_rad', 0.001)
        self.correction_resolution_m = float(self.get_parameter('tracking_correction_resolution_m').value)
        self.correction_resolution_rad = float(self.get_parameter('tracking_correction_resolution_rad').value)
        if not all(math.isfinite(v) and v > 0 for v in
                   (self.correction_resolution_m, self.correction_resolution_rad)):
            raise ValueError('tracking correction resolutions must be positive and finite')
        self.declare_parameter("max_following_error_rad", 0.15)
        following = float(self.get_parameter("max_following_error_rad").value)
        if not math.isfinite(following) or following <= 0:
            raise ValueError("max_following_error_rad must be positive and finite")
        settings.update(position_tolerance_m=float(self.get_parameter("tracking_position_tolerance_m").value),
                        angle_tolerance_rad=float(self.get_parameter("tracking_angle_tolerance_rad").value))
        self.solver = InverseKinematicsSolver(settings)
        self.startup_mode = self.get_parameter("startup_mode").value
        if self.startup_mode not in ("configured", "current"):
            raise ValueError("startup_mode must be configured or current")
        startup = self.config.get("startup", {})
        self.startup_motion = None
        if self.startup_mode == "configured":
            waypoints = [[math.radians(float(v)) for v in startup[name]]
                         for name in ("home_joints_deg", "demo_joints_deg")]
            self.startup_motion = JointStartup(
                waypoints, self.solver.limits,
                float(self.get_parameter("max_joint_velocity_rad_s").value),
                float(self.get_parameter("max_joint_acceleration_rad_s2").value),
                float(startup.get("minimum_segment_duration_sec", 3.0)),
                float(startup.get("segment_timeout_sec", 60.0)),
                float(startup.get("arrival_tolerance_rad", math.radians(1.0))))
        self.harvest = None
        if self.get_parameter("harvest_cycle_enabled").value:
            self.harvest = HarvestCycle(self.config.get("harvest_cycle", {}),
                [math.radians(float(q)) for q in startup["demo_joints_deg"]], self.solver.limits,
                float(self.get_parameter("max_joint_velocity_rad_s").value),
                float(self.get_parameter("max_joint_acceleration_rad_s2").value))
        self.harvest_observation = None
        self.harvest_epoch = 0.
        self.harvest_ik_ok = False
        self.harvest_published_sequence = -1
        # Keep the old, strict hold path available for current-position starts.
        dxl = dict(dxl, startup_hold_check="acknowledged" if self.startup_motion else "strict")
        backend_name = str(self.get_parameter("backend").value or self.config.get("backend", "sim"))
        initial = [math.radians(v) for v in self.config.get("initial_joints_deg", [5, 170, -85])]
        if len(initial) != 3 or not all(math.isfinite(v) for v in initial):
            raise ValueError("initial_joints_deg must contain three finite values")
        self.backend = (SimulatedMotorBackend(self.config.get("simulator", {}), initial)
                        if backend_name == "sim" else DynamixelFiveMotorBackend(dxl)
                        if backend_name == "dynamixel" else CanMixedMotorBackend(
                            self.config.get("can_mixed_backend", {}), dxl,
                            np.radians(limits).tolist())
                        if backend_name == "can_mixed" else None)
        if self.backend is None:
            raise ValueError("backend must be sim, dynamixel, or can_mixed")
        self.z_enabled = bool(self.get_parameter('z_tracking_enabled').value)
        self.z_control = None
        self.z_hold_command = None
        if self.z_enabled:
            z_config = self.config.get('z_tracking', {})
            z_backend = SimulatedZBackend(z_config) if backend_name == 'sim' else SerialZBackend(z_config)
            self.z_control = PixelZTrackingCoordinator(z_config, z_backend)
            # Request once, even if the Pico already reports homed. The existing
            # coordinator waits for valid status and measured XY stop, then
            # holds XY until homing completion and settling. Faults latch.
            self.z_control.home_pending = self.startup_mode == 'configured'
        self.goal_lock = threading.Lock()
        self.io_lock = threading.Lock()
        self.backend_active = False
        self.activation_failed = False
        self.tracking_ready = False
        self.require_ee_ready = bool(self.get_parameter("require_ee_ready").value)
        self.ee_ready = not self.require_ee_ready
        self.initialization_started = time.monotonic()
        self.latest = None
        self.last_accepted_stamp = 0.0
        self.last_command = None
        self.last_velocity = [0.0, 0.0, 0.0]
        self.hold_sent = False
        self.hold_requested = False
        self.diag = {}
        self.last_tick = time.monotonic()
        self.previous_tick = None
        self.last_metric_log = self.last_tick
        self.periods = []
        self.over_100ms = 0
        self.rejected = 0
        qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1,
                         reliability=ReliabilityPolicy.BEST_EFFORT)
        self.goal_group = ReentrantCallbackGroup()
        self.control_group = MutuallyExclusiveCallbackGroup()
        self.goal_sub = self.create_subscription(PoseStamped, self.get_parameter("goal_topic").value,
                                                 self.goal_callback, qos, callback_group=self.goal_group)
        self.hold_sub = self.create_subscription(Empty, "/arm_xy/hold", self.hold_callback,
                                                 qos, callback_group=self.goal_group)
        self.xy_hold_sub = self.create_subscription(Empty, '/arm_xy/xy_hold',
            self.xy_hold_callback, qos, callback_group=self.goal_group)
        self.command_pub = self.create_publisher(Float64MultiArray, "/arm_xy/command_joints", 10)
        self.diagnostic_pub = self.create_publisher(String, "/arm_xy/diagnostics", 10)
        self.actual_pub = self.create_publisher(PoseStamped, "/arm_xy/actual", 10)
        self.error_pub = self.create_publisher(Float64MultiArray, "/arm_xy/error", 10)
        self.joints_pub = self.create_publisher(Float64MultiArray, "/arm_xy/joints", 10)
        self.ready_pub = self.create_publisher(Bool, "/arm_xy/ready", QoSProfile(
            depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE))
        self.harvest_state_pub = self.create_publisher(String, "/arm_xy/harvest/state", QoSProfile(
            depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE))
        if self.z_enabled:
            self.z_state_pub = self.create_publisher(String, '/arm_xy/z/state', 1)
            self.z_sub = self.create_subscription(String, '/arm_xy/z/pixel_observation',
                self.z_observation_callback, qos, callback_group=self.goal_group)
            self.z_home_service = self.create_service(Trigger, '/arm_xy/z/home',
                self.z_home_callback, callback_group=self.goal_group)
            self.z_stop_service = self.create_service(Trigger, '/arm_xy/z/stop',
                self.z_stop_callback, callback_group=self.goal_group)
        if self.harvest is not None:
            if self.require_ee_ready:
                self.ee_ready_sub = self.create_subscription(Bool, "/end_effector/ready",
                    self.ee_ready_callback, QoSProfile(depth=1,
                        durability=DurabilityPolicy.TRANSIENT_LOCAL,
                        reliability=ReliabilityPolicy.RELIABLE),
                    callback_group=self.control_group)
            self.harvest_obs_sub = self.create_subscription(String, "/vision/servo_diagnostics",
                self.harvest_observation_callback, 1, callback_group=self.goal_group)
            self.harvest_alive_sub = self.create_subscription(Bool, "/arm_xy/harvest/ee_alive",
                self.harvest_alive_callback, 1, callback_group=self.control_group)
            self.harvest_services = [self.create_service(Trigger, "/arm_xy/harvest/"+action,
                lambda req, res, action=action: self.harvest_request(action, res),
                callback_group=self.control_group) for action in ("hold", "pull", "resume")]
        self.ready_pub.publish(Bool(data=False))
        rate = float(self.get_parameter("control_rate_hz").value)
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError("control_rate_hz must be positive and finite")
        self.timer = self.create_timer(1.0 / rate, self.control_tick, callback_group=self.control_group)
        self.get_logger().info(f"XY tracker starting: backend={backend_name}, startup_mode={self.startup_mode}, {rate:g} Hz, goal={self.get_parameter('goal_topic').value}")
        if self.z_enabled and self.startup_mode == 'configured':
            self.get_logger().info(
                'Configured startup: automatic Z homing after backend activation and measured XY stop; '
                'XY home/demo motion starts only after Z homing and settling complete')

    def goal_callback(self, msg):
        """Validate and replace the single latest target; never performs motor I/O."""
        if not self.tracking_ready or (getattr(self, "harvest", None) is not None and self.harvest.state != "APPROACH"):
            return  # Startup owns the arm; targets received during it are discarded.
        if getattr(self, 'z_control', None) is not None and self.z_control.owns_xy:
            return
        now_msg = self.get_clock().now().to_msg()
        now = self.get_clock().now().nanoseconds / 1e9
        p, q, stamp = msg.pose.position, msg.pose.orientation, msg.header.stamp
        values = [p.x, p.y, p.z, q.x, q.y, q.z, q.w]
        reason = None
        if msg.header.frame_id != self.get_parameter("frame_id").value:
            reason = "frame_id mismatch"
        elif not all(math.isfinite(v) for v in values):
            reason = "NaN/Inf in pose"
        elif not stamp.sec and not stamp.nanosec:
            reason = "zero timestamp"
        else:
            age = now - (stamp.sec + stamp.nanosec * 1e-9)
            if age > float(self.get_parameter("stamp_max_age_sec").value):
                reason = "stale timestamp"
            elif age < -float(self.get_parameter("stamp_future_tolerance_sec").value):
                reason = "future timestamp"
        norm = math.sqrt(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w)
        if reason is None and abs(norm - 1.0) > 1e-3:
            reason = "orientation quaternion must be normalized"
        if reason is None:
            roll = math.atan2(2*(q.w*q.x + q.y*q.z), 1 - 2*(q.x*q.x + q.y*q.y))
            pitch = math.asin(max(-1., min(1., 2*(q.w*q.y - q.z*q.x))))
            if abs(roll) > 1e-3 or abs(pitch) > 1e-3:
                reason = "only planar yaw is supported"
        expected_z = XYTracker.current_z(self)
        if reason is None and abs(p.z - expected_z) > 0.002:
            reason = "Z is fixed in XY tracking mode"
        if reason is None and math.hypot(p.x, p.y) > float(self.get_parameter("max_goal_xy_m").value):
            reason = "XY target exceeds configured input bound"
        if reason:
            self.rejected += 1
            self.get_logger().warning(f"Rejected XY goal ({reason}); rejected_total={self.rejected}")
            return
        yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1 - 2*(q.y*q.y + q.z*q.z))
        received = time.monotonic()
        with self.goal_lock:
            if getattr(self, 'z_control', None) is not None and self.z_control.owns_xy:
                return
            if getattr(self, "harvest", None) is not None and self.harvest.state != "APPROACH":
                return
            observation_stamp = stamp.sec + stamp.nanosec*1e-9
            if observation_stamp <= max(self.last_accepted_stamp, getattr(self, "harvest_epoch", 0.)):
                self.rejected += 1
                return
            self.last_accepted_stamp = observation_stamp
            self.latest = (p.x, p.y, yaw, received, observation_stamp)
            self.hold_requested = False

    def current_z(self):
        control = getattr(self, 'z_control', None)
        if control is not None and control.state is not None and control.state['homed']:
            return control.state['position_m']
        return float(self.get_parameter('plane_z_m').value)

    def z_observation_callback(self, msg):
        if not self.tracking_ready:
            return
        try:
            data = json.loads(msg.data)
            stamp = float(data['capture_stamp'])
            now = self.get_clock().now().nanoseconds/1e9
            values = [float(data[key]) for key in ('error_px', 'image_height', 'direction_per_error', 'track_id')]
            if (data['frame_id'] != self.get_parameter('frame_id').value or not math.isfinite(stamp) or
                    stamp <= 0 or not -.05 <= now-stamp <= self.z_control.cfg['observation_timeout_sec']):
                return
        except (ValueError, KeyError, TypeError):
            return
        with self.goal_lock:
            self.z_control.observe_pixel(*values, stamp, time.monotonic())

    def z_home_callback(self, request, response):
        with self.goal_lock:
            can_home = (not self.activation_failed and
                        self.z_control.phase in ('IDLE', 'NEEDS_HOME') and
                        (self.harvest is None or self.harvest.state in ('STARTUP', 'APPROACH')))
            response.success = can_home
            response.message = 'Homing requested; XY will be held before Z moves' if can_home else 'Z is busy, faulted, or owned by harvest'
            if can_home:
                self.z_control.home_pending = True
        return response

    def z_stop_callback(self, request, response):
        with self.goal_lock:
            self.z_control.stop_reason = 'explicit_z_stop_service'
            self.z_control.stop_pending = True
        response.success, response.message = True, 'Z stop requested; XY held; restart required'
        return response

    def step_z_tracking(self, measured, now):
        control = getattr(self, 'z_control', None)
        if control is None:
            return False
        ros_now = self.get_clock().now().nanoseconds/1e9
        with self.goal_lock:
            # Targets can arrive during the preceding motor-state read. Use
            # post-I/O time so a new observation never has a negative age.
            control_now = time.monotonic()
            ros_now = self.get_clock().now().nanoseconds/1e9
            control.xy_hold_target = list(measured if self.z_hold_command is None else self.z_hold_command)
            owns = control.step(control_now, ros_now, measured,
                allowed=self.harvest is None or self.harvest.state in ('STARTUP', 'APPROACH'))
            if owns or self.z_hold_command is not None:
                self.latest = None
                self.last_velocity = [0., 0., 0.]
                self.last_accepted_stamp = max(self.last_accepted_stamp, ros_now)
        if control.phase != getattr(self, 'last_logged_z_phase', None):
            self.last_logged_z_phase = control.phase
            self.get_logger().info(
                f"Z phase={control.phase} reason={control.reason} "
                f"position_m={None if control.state is None else control.state['position_m']} "
                f"target_m={control.target}")
            if control.phase == 'FAULT' and control.reason == 'xy_failed_to_stop':
                self.get_logger().error('XY stop check: '+json.dumps(
                    control.diagnostics(ros_now), allow_nan=False))
        if control.phase == 'STOPPING_XY' and control_now-getattr(self, 'last_z_stop_log', -math.inf) >= 1.:
            self.last_z_stop_log = control_now
            self.get_logger().info('Z waiting for XY stop: '+json.dumps(
                control.diagnostics(ros_now), allow_nan=False))
        if owns:
            if self.z_hold_command is None:
                self.z_hold_command = list(measured)
                self.send_command(measured)
                self.last_command = list(measured)
            self.diag.update(reason='z_'+control.phase.lower(), z=control.diagnostics(ros_now))
            self.last_tick = now
            if control.phase == 'FAULT':
                raise RuntimeError('Z fault: '+control.reason)
            return True
        self.z_hold_command = None
        self.last_tick = now if control.reason == 'z_complete_waiting_fresh_goal' else self.last_tick
        return False

    def harvest_observation_callback(self, msg):
        try:
            data = json.loads(msg.data)
            values = [data["capture_stamp"], *data["pixel_error"], data["distance_error_m"],
                      *data["goal_pose"], data["track_id"]]
            if data["reason"] != "tracking" or len(data["pixel_error"]) != 2 or len(data["goal_pose"]) != 3 or not all(math.isfinite(v) for v in values):
                raise ValueError("invalid harvest observation")
            data["received"] = time.monotonic()
            data["goal_yaw"] = data["goal_pose"][2]
        except (ValueError, KeyError, TypeError):
            data = None
        with self.goal_lock:
            self.harvest_observation = data

    def harvest_alive_callback(self, msg):
        self.harvest.ee_seen = time.monotonic() if msg.data else None
        if not msg.data and self.harvest.state in ("APPROACH", "RETURNING"):
            self.harvest.request("hold", time.monotonic())

    def ee_ready_callback(self, msg):
        self.ee_ready = bool(msg.data)

    def harvest_request(self, action, response):
        response.success, response.message = self.harvest.request(action, time.monotonic())
        return response

    def publish_harvest_state(self):
        cycle = self.harvest
        payload = dict(state="DISABLED" if cycle is None else cycle.state,
                       sequence=0 if cycle is None else cycle.sequence,
                       hold_ready=False if cycle is None else cycle.hold_settled >= 3,
                       reason="disabled" if cycle is None else cycle.reason,
                       stamp=self.get_clock().now().nanoseconds/1e9)
        self.harvest_state_pub.publish(String(data=json.dumps(payload)))
        if cycle is not None:
            self.diag["harvest"] = payload
            if cycle.sequence != self.harvest_published_sequence:
                self.get_logger().info(f"Harvest: {cycle.state} ({cycle.reason})")
                self.harvest_published_sequence = cycle.sequence

    def step_harvest(self, measured, now):
        if self.harvest is None:
            return False
        cycle = self.harvest
        with self.goal_lock:
            observation, latest = self.harvest_observation, self.latest
            # An observation can arrive during the blocking motor-state read.
            # Its receive timestamp must not be compared with the old tick start.
            now = time.monotonic()
        ros_now = self.get_clock().now().nanoseconds/1e9
        timeout = cycle.settings['observation_timeout_sec']
        pose_error = (None if latest is None else
            float(np.linalg.norm(self.solver.forward_kinematics(measured)[:2]-latest[:2])))
        age = None if observation is None else now-observation['received']
        capture_age = None if observation is None else ros_now-observation['capture_stamp']
        checks = dict(has_observation=observation is not None, ik_ok=bool(self.harvest_ik_ok),
            has_goal=latest is not None,
            current_epoch=observation is not None and observation['capture_stamp'] > self.harvest_epoch,
            observation_fresh=age is not None and 0 <= age <= timeout,
            capture_fresh=capture_age is not None and 0 <= capture_age <= timeout,
            goal_fresh=latest is not None and 0 <= now-latest[3] <= timeout,
            goal_pose_close=pose_error is not None and pose_error <= cycle.settings['arrival_goal_pose_tolerance_m'])
        if not all(checks.values()):
            observation = None
        if cycle.state == "RETURNING" and self.last_command is not None:
            if max(abs(np.asarray(self.last_command)-measured)) > float(self.get_parameter("max_following_error_rad").value):
                raise RuntimeError("return joint following error exceeds configured bound")
        old_sequence = cycle.sequence
        command = cycle.step(measured, now, observation)
        self.diag['arrival_check'] = dict(checks=checks, observation_age_sec=age,
            capture_age_sec=capture_age, goal_pose_error_m=pose_error,
            stable_sec=0. if cycle.stable_since is None else now-cycle.stable_since,
            required_stable_sec=cycle.settings['settle_sec'])
        if cycle.sequence != old_sequence:
            with self.goal_lock:
                self.latest = None
                self.harvest_observation = None
                self.harvest_epoch = ros_now
            self.harvest_ik_ok = False
            self.last_velocity = [0., 0., 0.]
            self.last_command = list(measured)
        if command is not None:
            self.send_command(command)
            self.last_command = list(command)
            self.last_velocity = [0., 0., 0.]
            self.last_tick = now
            self.diag["reason"] = cycle.state.lower()
            return True
        return False

    def send_command(self, command):
        self.backend.send_joints(command)
        self.command_pub.publish(Float64MultiArray(data=list(command)))
        self.diag.update(command_joints=list(command),
                         commanded_pose=self.solver.forward_kinematics(command).tolist())

    def xy_hold_callback(self, msg):
        self.hold_callback(msg, stop_z=False)

    def hold_callback(self, _msg, stop_z=True):
        with self.goal_lock:
            control = getattr(self, 'z_control', None)
            if (stop_z and control is not None and self.tracking_ready and
                    control.phase in ('STOPPING_XY', 'MOVING_Z', 'STOPPING_Z', 'WAITING_IMAGE', 'SETTLING')
                    and not control.homing):
                if not control.stop_pending:
                    control.stop_reason = 'arm_xy_hold_received_during_z'
                control.stop_pending = True
            if getattr(self, "harvest", None) is not None and self.harvest.state != "APPROACH":
                return  # Visual loss never interrupts an owned harvest/return.
            self.latest = None
            self.hold_requested = True

    def control_tick(self):
        start = time.monotonic()
        previous = getattr(self, "previous_diagnostic_tick", None)
        self.previous_diagnostic_tick = start
        self.diag = {"stamp": self.get_clock().now().nanoseconds/1e9,
                     "reason": "startup", "period_sec": None if previous is None else start-previous}
        try:
            self._control_tick()
        finally:
            # SIGINT can invalidate the ROS context while a timer callback is
            # unwinding. Do not publish diagnostics after shutdown has begun.
            if not rclpy.ok():
                return
            try:
                self.publish_harvest_state()
                if getattr(self.backend, "last_state", None) is not None:
                    self.diag["motor_state"] = self.backend.last_state
                if getattr(self, 'z_control', None) is not None:
                    state = self.z_control.diagnostics(self.get_clock().now().nanoseconds/1e9)
                    self.diag['z'] = state
                    self.z_state_pub.publish(String(data=json.dumps(state, allow_nan=False)))
                self.diag.update(compute_sec=time.monotonic()-start, period_over_100ms=self.over_100ms)
                self.diagnostic_pub.publish(String(data=json.dumps(self.diag, allow_nan=False)))
            except _rclpy.RCLError:
                return

    def _control_tick(self):
        if self.activation_failed:
            self.diag["reason"] = "fault_latched"
            self.diag["detail"] = getattr(self, "fault_detail", "activation failed")
            return
        if not getattr(self, 'ee_ready', True):
            self.diag["reason"] = "waiting_for_ee_initial_pose"
            return
        tick_start = time.monotonic()
        if self.previous_tick is not None:
            period = tick_start - self.previous_tick
            self.periods.append(period)
            self.periods = self.periods[-600:]
            if period > 0.1:
                self.over_100ms += 1
        self.previous_tick = tick_start
        try:
            with self.io_lock:
                conflict_names = self.get_parameter("control_conflict_services").value
                active_services = {name for name, _types in self.get_service_names_and_types()}
                conflicts = sorted(set(conflict_names) & active_services)
                if conflicts:
                    if getattr(self, 'z_control', None) is not None:
                        self.z_control.fail('competing_arm_controller')
                    if not getattr(self, "control_conflict_logged", False):
                        self.get_logger().error(f"Control inhibited: competing arm service is active: {conflicts}")
                        self.control_conflict_logged = True
                    if self.backend_active and not self.tracking_ready:
                        raise RuntimeError("competing controller appeared during initialization")
                    if getattr(self, "harvest", None) is not None and self.backend_active:
                        self.harvest.fault("control_conflict", tick_start)
                        self.activation_failed = True
                    self.diag["reason"] = "control_conflict"
                    self.last_tick = tick_start
                    self.last_velocity = [0.0, 0.0, 0.0]
                    return
                self.control_conflict_logged = False
                if not self.backend_active:
                    motor_ids = self.backend.activate()
                    for report in getattr(self.backend, "startup_readback_report", []):
                        if report["reason"] == "current_hold":
                            self.get_logger().warning(
                                f"DXL {report['id']} startup hold confirmed at current position: "
                                f"sent={report['expected']}, goal=present={report['present']}, "
                                f"delta={report['present'] - report['expected']} tick, torque=OFF")
                        elif len(report["samples"]) > 1:
                            self.get_logger().warning(
                                f"DXL {report['id']} hold goal confirmed after re-read: "
                                f"expected={report['expected']}, readbacks={report['samples']}, "
                                f"elapsed_ms={report['elapsed_ms']:.1f}")
                    # Torque-on may change the encoder representation; read again
                    # before announcing a usable pose to the circle generator.
                    measured = self.backend.read_joints()
                    self.backend_active = True
                    if motor_ids:
                        self.get_logger().info(
                            f"Backend activation verified: {motor_ids}; startup_mode={self.startup_mode}")
                else:
                    measured = self.backend.read_joints()
                z_owns_xy = XYTracker.step_z_tracking(self, measured, tick_start)
                actual = self.solver.forward_kinematics(measured)
                self.publish_actual(actual)
                self.diag.update(actual_pose=actual.tolist(), measured_joints=list(measured))
                self.joints_pub.publish(Float64MultiArray(data=list(measured)))
                if z_owns_xy:
                    return
                if not self.tracking_ready:
                    if self.startup_motion is not None:
                        segment = self.startup_motion.index
                        command, done = self.startup_motion.step(measured, time.monotonic())
                        self.send_command(command)
                        self.last_command = command
                        if segment != getattr(self, "logged_startup_segment", None):
                            self.get_logger().info(
                                f"Startup waypoint {segment + 1}/2: "
                                f"joints_deg={[round(math.degrees(v), 2) for v in self.startup_motion.waypoints[segment]]}")
                            self.logged_startup_segment = segment
                        if not done:
                            self.last_tick = time.monotonic()
                            return
                    # Announce readiness only after measured arrival at both poses.
                    with self.goal_lock:
                        self.latest = None
                        self.tracking_ready = True
                    self.last_command = list(measured)
                    self.last_velocity = [0., 0., 0.]
                    self.last_tick = time.monotonic()
                    self.previous_tick = None
                    self.periods.clear()
                    self.over_100ms = 0
                    self.last_metric_log = self.last_tick
                    if self.harvest is not None:
                        self.harvest.ready(measured, time.monotonic())
                        self.harvest_epoch = self.get_clock().now().nanoseconds/1e9
                    self.ready_pub.publish(Bool(data=True))
                    self.get_logger().info(
                        f"XY tracking ready after {self.last_tick - self.initialization_started:.2f}s initialization; "
                        f"goals may start (Z tracking {'enabled' if self.z_enabled else 'disabled'})")
                    return
                if self.step_harvest(measured, tick_start):
                    return
                # Read the latest slot after potentially blocking state I/O so
                # an update received during that read takes effect this cycle.
                with self.goal_lock:
                    goal = self.latest
                if self.last_command is None:
                    self.last_command = list(measured)
                goal_age = None if goal is None else self.get_clock().now().nanoseconds/1e9-goal[4]
                self.diag.update(goal_pose=None if goal is None else list(goal[:3]), goal_age_sec=goal_age,
                                 reason="no_goal")
                if goal is not None and max(time.monotonic()-goal[3], goal_age) <= float(self.get_parameter("goal_timeout_sec").value):
                    result = self.solver.solve_tracking(goal[:3], measured,
                        self.correction_resolution_m, self.correction_resolution_rad)
                    self.diag.update(ik_position_error_m=result.position_error_m,
                        ik_angle_error_rad=result.angle_error_rad,
                        correction_resolution_m=min(self.solver.position_tolerance, self.correction_resolution_m),
                        correction_resolution_rad=min(self.solver.angle_tolerance, self.correction_resolution_rad))
                    self.harvest_ik_ok = result.success
                    if result.success:
                        dt = min(.15, max(1e-3, tick_start - self.last_tick))
                        v_limit = float(self.get_parameter("max_joint_velocity_rad_s").value)
                        a_limit = float(self.get_parameter("max_joint_acceleration_rad_s2").value)
                        if max(abs(np.asarray(self.last_command)-measured)) > float(self.get_parameter("max_following_error_rad").value):
                            raise RuntimeError("joint following error exceeds configured bound")
                        command, velocity = joint_step(self.last_command, self.last_velocity,
                            result.joints, goal[2], self.solver.limits, dt, v_limit, a_limit)
                        command_pose = self.solver.forward_kinematics(command)
                        self.diag.update(reason="tracking", ik_reason=result.reason, ik_iterations=result.iterations,
                            ik_pose=self.solver.forward_kinematics(result.joints).tolist(), ik_joints=result.joints.tolist(),
                            commanded_pose=command_pose.tolist(), command_joints=command.tolist(),
                            commanded_yaw_error=self.solver.wrap(goal[2]-command_pose[2]),
                            measured_yaw_error=self.solver.wrap(goal[2]-actual[2]))
                        self.send_command(command)
                        self.last_command, self.last_velocity = command, velocity
                        self.hold_sent = False
                        err = Float64MultiArray(data=[goal[0] - actual[0], goal[1] - actual[1],
                                                       self.solver.wrap(goal[2] - actual[2]),
                                                       float(result.iterations)])
                        self.error_pub.publish(err)
                    else:
                        self.diag.update(reason="ik_hold", ik_reason=result.reason, ik_iterations=result.iterations)
                        if not self.hold_sent:
                            self.send_command(measured)
                            self.last_command = list(measured)
                            self.hold_sent = True
                        self.last_velocity = [0.0, 0.0, 0.0]
                        self.get_logger().warning(f"IK hold: {result.reason}; pos={result.position_error_m:.4f}m yaw={result.angle_error_rad:.4f}rad")
                elif goal is not None or self.hold_requested:
                    self.harvest_ik_ok = False
                    self.diag["reason"] = "observation_hold" if self.hold_requested else "goal_timeout"
                    # Retarget the current measured position once to stop the previous
                    # profile trajectory. Torque remains enabled for position hold.
                    if not self.hold_sent:
                        self.send_command(measured)
                        self.last_command = list(measured)
                        self.hold_sent = True
                    self.last_velocity = [0.0, 0.0, 0.0]
                self.last_tick = tick_start
        except Exception as exc:  # communication failure: stop issuing new goals, preserve servo hold
            if getattr(self, 'z_control', None) is not None:
                try:
                    self.z_control.fail(str(exc))
                except Exception:
                    pass
            self.fault_detail = str(exc)
            self.diag.update(reason="backend_fault", detail=self.fault_detail)
            self.last_velocity = [0.0, 0.0, 0.0]
            if getattr(self, "harvest", None) is not None:
                self.harvest.fault(str(exc), tick_start)
            if not self.backend_active or not self.tracking_ready:
                self.activation_failed = True
                self.get_logger().error(
                    f"XY tracker activation failed; tracking disabled, no automatic retry. "
                    f"Torque states left unchanged after failure: {exc}")
            else:
                self.activation_failed = True
                self.diag.update(reason="backend_fault", detail=str(exc))
                # One best-effort measured hold, then latch. A broken bus cannot
                # guarantee physical stopping; never retry movement or torque OFF.
                try:
                    self.send_command(self.backend.read_joints())
                except Exception:
                    pass
                self.ready_pub.publish(Bool(data=False))
                self.get_logger().error(f"XY tracker fault latched; restart required: {exc}")
        elapsed = time.monotonic() - tick_start
        if tick_start - self.last_metric_log >= 5.0:
            recent = self.periods[-50:]
            avg = sum(recent) / max(1, len(recent))
            with self.goal_lock:
                age = time.monotonic() - self.latest[3] if self.latest else float("inf")
            maximum = max(recent, default=0.0)
            hz = 1.0 / avg if avg else 0.0
            self.get_logger().info(f"tracker metrics: compute={elapsed*1000:.1f}ms period_avg={avg*1000:.2f}ms period_max={maximum*1000:.2f}ms rate_avg={hz:.2f}Hz goal_age={age*1000:.1f}ms >100ms={self.over_100ms}")
            self.last_metric_log = tick_start

    def publish_actual(self, pose):
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.get_parameter("frame_id").value
        msg.pose.position.x, msg.pose.position.y = float(pose[0]), float(pose[1])
        msg.pose.position.z = self.current_z()
        msg.pose.orientation.z = math.sin(float(pose[2]) / 2.)
        msg.pose.orientation.w = math.cos(float(pose[2]) / 2.)
        self.actual_pub.publish(msg)

    def destroy_node(self):
        try:
            if self.z_control is not None:
                self.z_control.backend.close()
        finally:
            try:
                self.backend.close()
            finally:
                super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = XYTracker()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            executor.shutdown()
        except KeyboardInterrupt:
            pass
        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except rclpy.exceptions.RCLError:
                pass
