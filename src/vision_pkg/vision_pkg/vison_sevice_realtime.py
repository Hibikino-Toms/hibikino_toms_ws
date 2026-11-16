#!/usr/bin/env python3
"""Realtime D405 tomato detector and XY tracker goal publisher.

The legacy spelling in the requested module name is retained intentionally.
Far approach uses horizontal pixel error and bounded forward velocity without
metric depth. Confirmed near depth enables standoff control. Opt-in discrete Z
correction holds XY while the Z axis moves.
"""
import math
import json
from collections import deque
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import pyrealsense2 as rs
import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.impl.implementation_singleton import rclpy_implementation as _rclpy
from rclpy.qos import qos_profile_sensor_data

from std_msgs.msg import Bool, Empty, String
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from .modules.image_servo import ImageServo, resolve_weights, robust_depth, rotation


def _positive(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite")
    return value


class RealtimeTomatoDetector(Node):
    def __init__(self):
        super().__init__("vision_service_realtime")
        default_config = (Path(get_package_share_directory("vision_pkg")) /
                          "config" / "realtime_detector.yaml")
        self.declare_parameter("config_file", str(default_config))
        config_file = self.get_parameter("config_file").value
        if not config_file:
            raise RuntimeError(f"config_file is empty; expected {default_config}")
        self.config_path = Path(config_file).expanduser().resolve()
        with self.config_path.open(encoding="utf-8") as stream:
            self.config = yaml.safe_load(stream)
        if not isinstance(self.config, dict):
            raise ValueError("realtime detector config must be a YAML mapping")
        cfg = self.config

        self.camera_cfg = cfg["camera"]
        self.detector_cfg = cfg["detector"]
        self.target_cfg = cfg["target"]
        self.rate_hz = _positive(cfg["processing_rate_hz"], "processing_rate_hz")
        if not 10.0 <= self.rate_hz <= 20.0:
            raise ValueError("processing_rate_hz must be between 10 and 20 Hz")
        self.width, self.height = int(self.camera_cfg["width"]), int(self.camera_cfg["height"])
        self.camera_fps = int(self.camera_cfg["fps"])
        self.frame_timeout = _positive(self.camera_cfg.get("frame_timeout_sec", 2.0),
                                       "camera.frame_timeout_sec")
        self.reconnect_interval = _positive(self.camera_cfg.get("reconnect_interval_sec", 3.0),
                                            "camera.reconnect_interval_sec")
        self.last_camera_reconnect = -math.inf
        self.camera_reconnect_count = 0
        if min(self.width, self.height, self.camera_fps) <= 0:
            raise ValueError("camera width, height and fps must be positive")

        matrix = np.asarray(self.target_cfg["camera_to_end_effector"], dtype=float)
        if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
            raise ValueError("camera_to_end_effector must be a finite 4x4 matrix")
        if not np.allclose(matrix[3], [0., 0., 0., 1.], atol=1e-8):
            raise ValueError("camera_to_end_effector last row must be [0,0,0,1]")
        self.servo = ImageServo(self.target_cfg, self.width, self.height)
        self.camera_to_ee = matrix
        self.frame_id = str(self.target_cfg["frame_id"])
        self.fixed_z_m = float(self.target_cfg["fixed_z_m"])
        self.camera_reference_yaw = math.radians(float(
            self.target_cfg.get("camera_reference_yaw_deg", 100.0)))
        if not math.isfinite(self.camera_reference_yaw):
            raise ValueError("camera_reference_yaw_deg must be finite")
        self.class_name = str(self.detector_cfg.get("tomato_class_name", "tomato"))
        self.confidence = float(self.detector_cfg.get("confidence", 0.25))
        self.iou = float(self.detector_cfg.get("iou", 0.45))
        self.image_size = int(self.detector_cfg.get("image_size", 640))
        self.depth_radius = int(self.target_cfg.get("depth_patch_radius_px", 5))
        self.max_depth = _positive(self.target_cfg.get("max_depth_m", 2.0), "max_depth_m")
        self.actual_max_age = _positive(self.target_cfg.get("actual_max_age_sec", 0.25),
                                        "actual_max_age_sec")
        self.window_name = str(cfg.get("window_name", "D405 tomato realtime"))
        self.last_cycle_error_log = 0.0

        self.declare_parameter("harvest_cycle_enabled", False)
        self.harvest_enabled = bool(self.get_parameter("harvest_cycle_enabled").value)
        self.harvest_status = None
        self.harvest_main_token = None
        self.harvest_mode = "WAITING_STATE" if self.harvest_enabled else "DISABLED"
        self.harvest_state_sub = self.create_subscription(String, "/arm_xy/harvest/state",
            self.harvest_state_callback, QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                                                  reliability=ReliabilityPolicy.RELIABLE))
        self.declare_parameter("synthetic_camera", False)
        self.declare_parameter("show_window", True)
        self.declare_parameter('z_tracking_enabled', False)
        self.z_enabled = bool(self.get_parameter('z_tracking_enabled').value)
        self.z_status = None
        self.actual_z_m = self.fixed_z_m
        self.synthetic = bool(self.get_parameter("synthetic_camera").value)
        self.show_window = bool(self.get_parameter("show_window").value)
        self.ready = False
        self.pose_history = deque(maxlen=100)
        self.sim_world = None
        self.last_capture = None
        self.last_frame_time = time.monotonic()
        self.diag = {}
        weights = resolve_weights(self.config_path, self.detector_cfg["weights"])
        self.device = "synthetic"
        if not self.synthetic:
            import torch
            from ultralytics import YOLO
            self.model = YOLO(str(weights))
            device = self.detector_cfg.get("device", "auto")
            self.device = (0 if torch.cuda.is_available() else "cpu") if device == "auto" else device

        self.actual_pose = None
        self.actual_received_at = None
        self.actual_sub = self.create_subscription(
            PoseStamped, str(self.target_cfg.get("actual_topic", "/arm_xy/actual")),
            self.actual_callback, qos_profile_sensor_data)
        self.goal_pub = self.create_publisher(
            PoseStamped, str(self.target_cfg.get("goal_topic", "/arm_xy/goal")), 1)
        self.hold_pub = self.create_publisher(Empty, "/arm_xy/hold", 1)
        self.xy_hold_pub = self.create_publisher(Empty, '/arm_xy/xy_hold', 1)
        self.diag_pub = self.create_publisher(String, "/vision/servo_diagnostics", 10)
        self.ready_sub = self.create_subscription(Bool, "/arm_xy/ready", self.ready_callback,
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                       reliability=ReliabilityPolicy.RELIABLE))
        if self.z_enabled:
            self.z_pub = self.create_publisher(String, '/arm_xy/z/pixel_observation', 1)
            self.z_sub = self.create_subscription(String, '/arm_xy/z/state',
                self.z_state_callback, 1)

        self.pipeline = None
        self.window_created = False
        self.frame_count = 0
        self.last_rate_log = time.monotonic()
        self.rate_samples = []
        if self.synthetic:
            self.color_intrinsics = rs.intrinsics()
            self.color_intrinsics.width, self.color_intrinsics.height = self.width, self.height
            self.color_intrinsics.fx = self.color_intrinsics.fy = 600.
            self.color_intrinsics.ppx, self.color_intrinsics.ppy = self.width/2., self.height/2.
            self.depth_scale = .0001
        else:
            self._open_d405()
        # Warmup is included in initial FPS. Slow results fail the age check.
        # ROS pose reception runs separately; camera/inference/HighGUI stay on main.
        self.get_logger().info(
            f"Realtime tomato detector started: weights={weights}, target={self.rate_hz:g} Hz, "
            f"device={self.device}, goal={self.target_cfg.get('goal_topic', '/arm_xy/goal')}")
        self.get_logger().warning(
            "XY output uses the camera transform relative to the configured reference yaw "
            f"({math.degrees(self.camera_reference_yaw):.2f} deg) and live /arm_xy/actual pose; "
            "no detection or stale arm pose means no new goal")
        self._show_status("Waiting for D405 frames" if not self.synthetic else "Starting synthetic camera")

    def _open_d405(self):
        wanted_serial = str(self.camera_cfg.get("serial_number", "")).strip()
        wanted_pid_text = str(self.camera_cfg.get("usb_product_id", "0b5b")).strip()
        try:
            wanted_pid = int(wanted_pid_text, 16)
        except ValueError as exc:
            raise ValueError("camera.usb_product_id must be a hexadecimal USB product ID") from exc
        try:
            context = rs.context()
            devices = list(context.query_devices())
        except RuntimeError as exc:
            raise RuntimeError(
                "RealSense SDK could not enumerate USB devices. Check librealsense/udev "
                f"setup and device permissions. SDK error: {exc}") from exc
        matches = []
        found = []
        for device in devices:
            serial = (device.get_info(rs.camera_info.serial_number)
                      if device.supports(rs.camera_info.serial_number) else "unknown")
            product = (device.get_info(rs.camera_info.product_id)
                       if device.supports(rs.camera_info.product_id) else "unknown")
            product_line = (device.get_info(rs.camera_info.product_line)
                            if device.supports(rs.camera_info.product_line) else "unknown")
            name = (device.get_info(rs.camera_info.name)
                    if device.supports(rs.camera_info.name) else "unknown")
            found.append(f"name={name} product={product} line={product_line} serial={serial}")
            try:
                pid = int(str(product), 16)
            except ValueError:
                continue
            matched = pid == wanted_pid and (not wanted_serial or serial == wanted_serial)
            if matched:
                matches.append((device, serial, product, product_line))
        if len(matches) != 1:
            visibility = (f"SDK-visible devices: {found}" if found else
                          "RealSense SDK returned zero devices")
            raise RuntimeError(
                f"Expected one D405 (USB product ID {wanted_pid:04x}, "
                f"serial={wanted_serial or 'auto'}), found {len(matches)} match(es). "
                f"{visibility}. If lsusb lists 8086:{wanted_pid:04x} but this list is "
                "empty, the USB device is visible to Linux but not to librealsense; "
                "check the installed SDK, its udev rules, and USB permissions, then "
                "unplug/replug the camera. Check camera config only if another SDK-visible "
                "device is listed.")
        device, self.camera_serial, product, product_line = matches[0]
        for sensor in device.query_sensors():
            if sensor.supports(rs.option.global_time_enabled):
                sensor.set_option(rs.option.global_time_enabled, 1.)
        config = rs.config()
        config.enable_device(self.camera_serial)
        config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8,
                             self.camera_fps)
        config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16,
                             self.camera_fps)
        self.pipeline = rs.pipeline(context)
        self.profile = self.pipeline.start(config)
        self.align = rs.align(rs.stream.color)
        self.color_intrinsics = rs.video_stream_profile(
            self.profile.get_stream(rs.stream.color)).get_intrinsics()
        self.depth_scale = self.profile.get_device().first_depth_sensor().get_depth_scale()
        self.last_frame_time = time.monotonic()
        self.get_logger().info(
            f"Opened RealSense product={product} line={product_line}, "
            f"serial={self.camera_serial}, "
            f"color/depth={self.width}x{self.height}@{self.camera_fps}fps, "
            f"depth_scale={self.depth_scale:g}m/unit")

    def _stop_camera(self):
        pipeline, self.pipeline = self.pipeline, None
        if pipeline is not None:
            try:
                pipeline.stop()
            except RuntimeError as exc:
                self.get_logger().warning(f"D405 stop after disconnect: {exc}")

    def _maybe_reconnect_camera(self):
        """Reopen a lost SDK pipeline on the camera/main thread, without USB reset."""
        now = time.monotonic()
        if (now - self.last_frame_time < self.frame_timeout or
                now - self.last_camera_reconnect < self.reconnect_interval):
            return
        self.last_camera_reconnect = now
        self.camera_reconnect_count += 1
        self.get_logger().warning(
            f"No D405 frames for {now-self.last_frame_time:.1f}s; "
            f"reopening camera (attempt {self.camera_reconnect_count}). "
            "Check USB disconnect/errors with journalctl -k.")
        self._hold('camera_reconnecting')
        self._show_status("D405 disconnected/no frames; reconnecting. Check USB cable/hub.")
        self._stop_camera()
        try:
            self._open_d405()
        except RuntimeError as exc:
            self.diag['camera_reconnect_error'] = str(exc)
            self.get_logger().warning(f"D405 reopen failed: {exc}")
            self._stop_camera()
            return
        self.last_capture = None
        self.get_logger().info("D405 reopened; waiting for a fresh synchronized image before sending goals")

    def harvest_state_callback(self, msg):
        try:
            data = json.loads(msg.data)
            state, sequence, stamp = data['state'], int(data['sequence']), float(data['stamp'])
            if state not in ('STARTUP', 'APPROACH', 'HARVEST_HOLD', 'RETURNING', 'RETURNED', 'FAULT', 'DISABLED') or not math.isfinite(stamp):
                return
            if self.harvest_status is not None and stamp <= self.harvest_status[3]:
                return
            self.harvest_status = (state, sequence, time.monotonic(), stamp)
        except (ValueError, KeyError, TypeError):
            return

    def harvest_allows_vision(self):
        if not getattr(self, 'harvest_enabled', False):
            return True
        status = self.harvest_status
        if status is None or time.monotonic()-status[2] > .5 or abs(self.get_clock().now().nanoseconds/1e9-status[3]) > .5:
            self.harvest_mode = 'WAITING_STATE'
            self.harvest_main_token = None
            return False
        state, sequence = status[:2]
        token = (state, sequence)
        if state == 'APPROACH' and token != self.harvest_main_token:
            # Reset association/distance only on explicit approach entry, on the
            # camera thread. Subscription callbacks never touch servo state.
            self.servo = ImageServo(self.target_cfg, self.width, self.height)
            self.last_capture = None
        self.harvest_main_token = token
        self.harvest_mode = state
        return state == 'APPROACH'

    def ready_callback(self, msg):
        self.ready = msg.data

    def z_state_callback(self, msg):
        try:
            data = json.loads(msg.data)
            if (not isinstance(data['xy_inhibited'], bool) or not isinstance(data['homed'], bool) or
                    not math.isfinite(float(data['stamp'])) or
                    data.get('control_mode') != 'pixel' or
                    not all(math.isfinite(float(data[k])) for k in ('trigger_ratio', 'stop_ratio')) or
                    not 0 < data['stop_ratio'] < data['trigger_ratio'] <= 1.):
                return
            if self.z_status is None or data['stamp'] > self.z_status[0]['stamp']:
                self.z_status = (data, time.monotonic())
        except (ValueError, KeyError, TypeError):
            return

    def actual_callback(self, msg):
        if msg.header.frame_id != self.frame_id:
            return
        p, q = msg.pose.position, msg.pose.orientation
        values = (p.x, p.y, p.z, q.x, q.y, q.z, q.w)
        if not all(math.isfinite(v) for v in values):
            return
        norm = math.sqrt(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w)
        if abs(norm - 1.0) > 1e-3:
            return
        yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1 - 2*(q.y*q.y + q.z*q.z))
        stamp = msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        if not stamp or abs(q.x) > 1e-3 or abs(q.y) > 1e-3:
            return
        if self.pose_history and stamp <= self.pose_history[-1][0]:
            return
        self.pose_history.append((stamp, np.asarray([p.x, p.y, yaw])))
        self.actual_pose = (p.x, p.y, yaw)
        self.actual_z_m = p.z
        self.actual_received_at = time.monotonic()

    def _tomato_detections(self, result):
        if result.boxes is None or len(result.boxes) == 0:
            return []
        boxes = result.boxes.xyxy.cpu().numpy()
        classes = result.boxes.cls.cpu().numpy().astype(int)
        scores = result.boxes.conf.cpu().numpy()
        names = result.names
        mask_polygons = result.masks.xy if result.masks is not None else None
        detections = []
        for i, (box, class_id, score) in enumerate(zip(boxes, classes, scores)):
            if str(names[int(class_id)]).lower() != self.class_name.lower():
                continue
            x1, y1, x2, y2 = [int(round(v)) for v in box]
            mask = None
            if mask_polygons is not None and i < len(mask_polygons):
                # Ultralytics' .xy polygons are already rescaled to the original
                # frame; resizing masks.data directly would distort letterboxing.
                mask = np.zeros((self.height, self.width), dtype=np.uint8)
                polygon = np.asarray(mask_polygons[i], dtype=np.float32)
                if polygon.ndim == 2 and polygon.shape[0] >= 3:
                    polygon[:, 0] = np.clip(polygon[:, 0], 0, self.width - 1)
                    polygon[:, 1] = np.clip(polygon[:, 1], 0, self.height - 1)
                    cv2.fillPoly(mask, [np.rint(polygon).astype(np.int32)], 1)
                mask = mask.astype(bool)
                ys, xs = np.nonzero(mask)
                if xs.size:
                    u, v = float(np.mean(xs)), float(np.mean(ys))
                else:
                    continue  # Empty segmentation is not a valid object center.
            else:
                u, v = (x1+x2)/2., (y1+y2)/2.
            if 0 <= u < self.width and 0 <= v < self.height:
                distance2 = (u-self.width/2.)**2 + (v-self.height/2.)**2
                detections.append({"box": (x1, y1, x2, y2), "center": (u, v),
                                   "distance2": distance2, "confidence": float(score),
                                   "mask": mask, "center_source": "mask" if mask is not None else "bbox"})
        return detections

    def _depth_at(self, depth_image, u, v, mask):
        return robust_depth(depth_image, mask, (u, v), self.depth_scale, self.target_cfg)

    def _capture_pose(self, stamp):
        history = list(self.pose_history)
        if not history:
            return None, None
        nearest = min(history, key=lambda item: abs(item[0]-stamp))
        gap = abs(nearest[0]-stamp)
        if gap > self.target_cfg['pose_sync_tolerance_sec']:
            return None, gap
        for (ta, pa), (tb, pb) in zip(history, history[1:]):
            if ta <= stamp <= tb and tb-ta <= 2*self.target_cfg['pose_sync_tolerance_sec']:
                delta = pb-pa
                delta[2] = (delta[2]+math.pi) % (2*math.pi)-math.pi
                return pa + delta*((stamp-ta)/(tb-ta)), gap
        return nearest[1].copy(), gap

    def _synthetic_frame(self):
        # A fixed world target, projected through the MOVING measured camera.
        # This is a camera simulation, not a prerecorded sequence of goals.
        image = np.full((self.height, self.width, 3), 35, np.uint8)
        depth = np.zeros((self.height, self.width), np.uint16)
        if not self.pose_history or not self.ready:
            return image, depth, [], self.get_clock().now().nanoseconds/1e9
        _, pose = self.pose_history[-1]
        stamp = self.get_clock().now().nanoseconds/1e9
        r = self.servo.camera_rotation(pose[2])
        z = self.actual_z_m if getattr(self, 'z_enabled', False) else self.fixed_z_m
        origin = np.r_[pose[:2], z] + rotation(pose[2]-self.servo.reference) @ self.camera_to_ee[:3, 3]
        if self.sim_world is None:
            sim = self.config.get('simulation', {})
            self.sim_world = origin + r @ np.asarray(sim.get('initial_target_camera_m', [.025, .015, .25]))
        point = r.T @ (self.sim_world-origin)
        if point[2] <= 0:
            return image, depth, [], stamp
        u, v = rs.rs2_project_point_to_pixel(self.color_intrinsics, point.tolist())
        detections = []
        if 10 <= u < self.width-10 and 10 <= v < self.height-10:
            mask = np.zeros((self.height, self.width), np.uint8)
            cv2.circle(mask, (round(u), round(v)), 12, 1, -1)
            depth[mask.astype(bool)] = round(point[2]/self.depth_scale)
            image[mask.astype(bool)] = (0, 0, 220)
            detections = [dict(box=(u-12, v-12, u+12, v+12), center=(u, v), confidence=.99,
                               mask=mask.astype(bool), center_source='synthetic')]
        return image, depth, detections, stamp

    def _publish_goal(self, xy_yaw):
        x, y, yaw = xy_yaw
        msg = PoseStamped()
        # Preserve the observation stamp: tracker must not mistake old inference
        # for a newly captured goal.
        sec = int(self.capture_stamp)
        msg.header.stamp.sec = sec
        msg.header.stamp.nanosec = int((self.capture_stamp-sec)*1e9)
        msg.header.frame_id = self.frame_id
        msg.pose.position.x, msg.pose.position.y = x, y
        msg.pose.position.z = self.actual_z_m if getattr(self, 'z_enabled', False) else self.fixed_z_m
        msg.pose.orientation.z, msg.pose.orientation.w = math.sin(yaw/2.), math.cos(yaw/2.)
        self.goal_pub.publish(msg)

    def _z_observation(self, pixel, pose, stamp, image_height):
        """Depth-free pixel feedback; move only between the outer/inner bands."""
        status = self.z_status
        ros_now = self.get_clock().now().nanoseconds/1e9
        if (status is None or time.monotonic()-status[1] > .5 or
                abs(ros_now-status[0]['stamp']) > .5):
            return 'z_state_unavailable', False
        self.diag['z_phase'] = status[0]['phase']
        if not status[0]['homed']:
            return 'z_not_homed', False
        if status[0].get('control_mode') != 'pixel':
            return 'z_control_mode_mismatch', False
        ray = rs.rs2_deproject_pixel_to_point(self.color_intrinsics, self.servo.pixel.tolist(), 1.)
        direction = self.servo.vertical_pixel_direction(ray, pose[2])
        if direction is None:
            return 'uncontrollable_vertical_geometry', False
        error = float(pixel[1]-self.servo.pixel[1])
        height = int(image_height)
        trigger = height*status[0]['trigger_ratio']
        stop = height*status[0]['stop_ratio']
        self.diag.update(vertical_error_px=error, z_trigger_px=trigger, z_stop_px=stop,
                         z_control_mode='pixel', z_depth_required=False)
        payload = dict(frame_id=self.frame_id, capture_stamp=stamp,
                       error_px=error, image_height=height, direction_per_error=direction,
                       track_id=self.servo.track_id)
        self.z_pub.publish(String(data=json.dumps(payload, allow_nan=False)))
        if status[0]['xy_inhibited'] or abs(error) >= trigger:
            # Keep observations flowing during Z moves, but freeze the XY servo
            # velocity and never generate a backlog of planar targets.
            self.servo.hold()
            self.diag['reason'] = 'z_motion_hold'
            return None, True
        return None, False

    def _hold(self, reason, xy_only=False):
        self.servo.hold()
        if reason not in ('confirming_near_depth', 'locking_initial_distance'):
            self.servo.reject_approach_observation()
        if self.servo.distance is None and reason != 'locking_initial_distance':
            self.servo.depths.clear()
        if xy_only:
            self.xy_hold_pub.publish(Empty())
        else:
            self.hold_pub.publish(Empty())
        self.diag['reason'] = reason
        self.diag['hold_scope'] = 'xy_only' if xy_only else 'all_axes'
        # A single rejected frame can stop Z. The 5-second FPS summary cannot
        # explain that event, so record its reason and measurements at source.
        if reason != 'arm_not_ready' and not reason.startswith('harvest_'):
            now = time.monotonic()
            times = getattr(self, 'hold_reason_log_times', {})
            if now-times.get(reason, -math.inf) >= 1.:
                times[reason] = now
                self.hold_reason_log_times = times
                fields = ('capture_stamp', 'observation_age_sec', 'pose_gap_sec',
                          'track_id', 'detection_count', 'pixel_error', 'depth_m',
                          'previous_z_depth_m', 'z_phase')
                context = {key: self.diag.get(key) for key in fields}
                self.get_logger().warning(
                    f"Vision hold requested: reason={reason} scope={self.diag['hold_scope']}; "
                    + json.dumps(context, default=str))

    def process_frame(self):
        cycle_start = time.monotonic()
        self.diag = dict(reason='waiting_frame', synthetic=self.synthetic,
                         target_pixel=self.servo.pixel.tolist(), desired_distance_m=self.servo.distance,
                         goal_yaw_rad=self.servo.yaw, vertical_controlled=getattr(self, 'z_enabled', False))
        allow_approach = self.harvest_allows_vision()
        self.diag['harvest_state'] = getattr(self, 'harvest_mode', 'DISABLED')
        try:
            if self.synthetic:
                image, depth_image, detections, stamp = self._synthetic_frame()
            else:
                frames = self.pipeline.poll_for_frames() if self.pipeline is not None else None
                if not frames:
                    if time.monotonic()-self.last_frame_time > self.target_cfg['observation_max_age_sec']:
                        self._hold('camera_timeout')
                    self._show_status("Waiting for D405 color/depth frames. No arm goal is sent.")
                    self._maybe_reconnect_camera()
                    return
                # RGB-only approach does not require a depth frame to align.
                aligned = (frames if self.servo.image_approach_enabled and not frames.get_depth_frame()
                           else self.align.process(frames))
                color_frame, depth_frame = aligned.get_color_frame(), aligned.get_depth_frame()
                if not color_frame or (not depth_frame and not (
                        getattr(self, 'z_enabled', False) or self.servo.image_approach_enabled)):
                    self._hold('missing_color_or_depth')
                    self._show_status("D405 color or depth frame missing; no arm goal is sent.")
                    self._maybe_reconnect_camera()
                    return
                image = np.asanyarray(color_frame.get_data()).copy()
                depth_image = np.asanyarray(depth_frame.get_data()) if depth_frame else None
                self.last_frame_time = time.monotonic()
                domain = color_frame.get_frame_timestamp_domain()
                if domain not in (rs.timestamp_domain.system_time, rs.timestamp_domain.global_time):
                    self._hold('camera_timestamp_not_global')
                    self._show_status('Waiting for RealSense global timestamp synchronization')
                    return
                # SDK global timestamp is Unix milliseconds; map wall to ROS
                # clock. Physical camera with use_sim_time is unsupported.
                stamp = color_frame.get_timestamp()/1000. + self.get_clock().now().nanoseconds/1e9-time.time()
                result = self.model.predict(source=image, imgsz=self.image_size,
                    conf=self.confidence, iou=self.iou, device=self.device, verbose=False)[0]
                detections = self._tomato_detections(result)
            self.last_frame_time = time.monotonic()
            self.capture_stamp = float(stamp)
            now = self.get_clock().now().nanoseconds/1e9
            age = now-stamp
            pose, gap = self._capture_pose(stamp)
            self.diag.update(capture_stamp=stamp, observation_age_sec=age, pose_gap_sec=gap,
                             actual_pose=None if pose is None else pose.tolist(),
                             detection_count=len(detections))
            can_associate = (allow_approach and self.ready and -.02 <= age <= self.target_cfg['observation_max_age_sec']
                             and pose is not None and self.pose_history
                             and now-self.pose_history[-1][0] <= self.actual_max_age
                             and (self.last_capture is None or stamp > self.last_capture))
            selected = self.servo.select(detections, stamp) if can_associate else None
            target, depth_m = None, None
            reason = None
            xy_only_hold = False
            if not allow_approach:
                reason = 'harvest_' + self.harvest_mode.lower()
            elif not self.ready:
                reason = 'arm_not_ready'
            elif age > self.target_cfg['observation_max_age_sec'] or age < -.02:
                reason = 'stale_image'
            elif self.last_capture is not None and stamp <= self.last_capture:
                reason = 'duplicate_image'
            elif pose is None or not self.pose_history or now-self.pose_history[-1][0] > self.actual_max_age:
                reason = 'stale_or_unsynchronized_pose'
            elif selected is None:
                reason = 'target_lost_or_ambiguous'
            elif self.servo.image_approach_enabled and not self.servo.accept_approach_target():
                # This must precede _z_observation: previously a reacquired ID
                # could start Z motion before update_approach rejected its ID.
                reason = self.servo.approach_fault
                self.diag.update(track_id=self.servo.track_id,
                    locked_track_id=self.servo.approach_track_id,
                    center=list(map(float, selected['center'])),
                    pixel_error=(np.asarray(selected['center'])-self.servo.pixel).tolist(),
                    approach_mode=self.servo.approach_mode)
            else:
                u, v = selected['center']
                depth_m = self._depth_at(depth_image, u, v, selected['mask']) if depth_image is not None else None
                if self.servo.image_approach_enabled:
                    self.servo.note_approach_depth(depth_m)
                self.diag.update(track_id=self.servo.track_id, center_source=selected['center_source'],
                                 confidence=selected['confidence'], bbox=list(selected['box']),
                                 center=[float(u), float(v)],
                                 pixel_error=(np.array([u, v])-self.servo.pixel).tolist(), depth_m=depth_m)
                z_holds_xy = False
                if getattr(self, 'z_enabled', False):
                    # Z uses the 2-D detection independently of depth validity.
                    reason, z_holds_xy = self._z_observation((u, v), pose, stamp, image.shape[0])
                if reason is None and not z_holds_xy:
                    ray = rs.rs2_deproject_pixel_to_point(self.color_intrinsics, [float(self.servo.pixel[0]), float(v)], 1.)
                    if self.servo.image_approach_enabled:
                        observed_ray = rs.rs2_deproject_pixel_to_point(self.color_intrinsics, [float(u), float(v)], 1.)
                        target, details = self.servo.update_approach((u, v), observed_ray, ray, pose, stamp, depth_m)
                        self.diag.update(details)
                        if target is None:
                            reason = details['reason']
                            xy_only_hold = getattr(self, 'z_enabled', False)
                    elif depth_m is None:
                        reason = 'invalid_mask_depth'
                        xy_only_hold = getattr(self, 'z_enabled', False)
                    else:
                        point = rs.rs2_deproject_pixel_to_point(self.color_intrinsics, [float(u), float(v)], depth_m)
                        target, details = self.servo.update((u, v), point, ray, pose, stamp)
                        self.diag.update(details)
                        if target is None:
                            reason = details['reason']
                            xy_only_hold = getattr(self, 'z_enabled', False)
                    self.diag['vertical_controlled'] = getattr(self, 'z_enabled', False)
                    mode = self.diag.get('approach_mode')
                    if mode is not None and mode != getattr(self, 'last_logged_approach_mode', None):
                        self.last_logged_approach_mode = mode
                        self.get_logger().info(
                            f"XY approach mode={mode} depth_m={depth_m} "
                            f"confirmed={self.servo.depth_control_ready} blind_travel_m={self.servo.blind_travel:.3f}")
            self.last_capture = stamp
            if reason:
                self._hold(reason, xy_only=xy_only_hold)
            elif target is not None:
                self._publish_goal(target)
                self.diag['goal_pose'] = target.tolist()
            self._draw(image, detections, selected, target, depth_m)
            self.frame_count += 1
            self.rate_samples.append(time.monotonic()-cycle_start)
        except Exception as exc:
            self._hold('camera_or_inference_error')
            self.diag['detail'] = str(exc)
            if time.monotonic()-self.last_cycle_error_log >= 5.:
                self.get_logger().error(str(exc))
                self.last_cycle_error_log = time.monotonic()
            self._show_status(str(exc)[:160])
        finally:
            self.diag.update(processing_sec=time.monotonic()-cycle_start,
                             stamp=self.get_clock().now().nanoseconds/1e9,
                             camera_frame_age_sec=max(0., time.monotonic()-self.last_frame_time),
                             camera_reconnect_count=getattr(self, 'camera_reconnect_count', 0))
            try:
                self.diag_pub.publish(String(data=json.dumps(self.diag, allow_nan=False)))
            except _rclpy.RCLError:
                if rclpy.ok():
                    raise
            if time.monotonic()-self.last_rate_log >= 5.:
                elapsed = time.monotonic()-self.last_rate_log
                average_ms = 1000*float(np.mean(self.rate_samples)) if self.rate_samples else 0.
                self.get_logger().info(f"vision rate={len(self.rate_samples)/elapsed:.2f}fps "
                    f"cycle_avg={average_ms:.1f}ms reason={self.diag['reason']} "
                    f"frame_age={self.diag['camera_frame_age_sec']:.1f}s")
                self.last_rate_log = time.monotonic()
                self.rate_samples.clear()

    def _show_status(self, message):
        image = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        cv2.putText(image, "D405 REALTIME VIEW", (18, 38), cv2.FONT_HERSHEY_SIMPLEX,
                    .8, (255, 255, 255), 2)
        lines = [message[i:i + 58] for i in range(0, len(message), 58)] or [""]
        for index, line in enumerate(lines[:5]):
            cv2.putText(image, line, (18, 90 + index * 34), cv2.FONT_HERSHEY_SIMPLEX,
                        .55, (0, 220, 255), 1)
        self._show_window(image)

    def _show_window(self, image):
        if not self.show_window:
            return
        # A mutually-exclusive ROS callback group prevents overlap, but a
        # thread pool can still move successive callbacks between workers.
        # Qt-backed HighGUI requires a stable GUI thread, including cleanup.
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("OpenCV GUI must run on the main thread; use SingleThreadedExecutor")
        if not self.window_created:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            self.window_created = True
        cv2.imshow(self.window_name, image)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):
            rclpy.shutdown()

    def _draw(self, image, detections, selected, target, depth_m):
        center = tuple(np.rint(self.servo.pixel).astype(int))
        cv2.drawMarker(image, center, (255, 255, 0), cv2.MARKER_CROSS, 24, 2)
        if getattr(self, 'z_enabled', False):
            for key, color in (('z_trigger_px', (0, 180, 255)), ('z_stop_px', (0, 200, 0))):
                band = self.diag.get(key)
                if band is not None:
                    for sign in (-1, 1):
                        y = round(self.servo.pixel[1]+sign*band)
                        if 0 <= y < image.shape[0]:
                            cv2.line(image, (0, y), (image.shape[1]-1, y), color, 1)
        for det in detections:
            x1, y1, x2, y2 = [int(round(value)) for value in det["box"]]
            u, v = [int(round(v)) for v in det["center"]]
            chosen = det is selected
            color = (0, 0, 255) if chosen else (0, 200, 0)
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2 if chosen else 1)
            cv2.circle(image, (u, v), 5, color, -1)
            cv2.putText(image, f"tomato {det['confidence']:.2f}", (x1, max(20, y1-6)),
                        cv2.FONT_HERSHEY_SIMPLEX, .55, color, 2)
        text = [f"ID={self.servo.track_id} {self.diag.get('center_source', '-')} {self.diag.get('reason')}",
                f"pixel error={self.diag.get('pixel_error', '-')} Zerror={self.diag.get('vertical_error_px', '-')}px",
                f"{self.servo.approach_mode if self.servo.image_approach_enabled else 'DEPTH'} depth={depth_m} desired={self.servo.distance}",
                f"target pixel={tuple(self.servo.pixel)} yaw={math.degrees(self.servo.yaw):.1f} deg"]
        for i, line in enumerate(text):
            cv2.putText(image, line, (10, 25+25*i), cv2.FONT_HERSHEY_SIMPLEX, .45, (255,255,255), 1)
        # Show exactly one fully annotated image per successful cycle. A raw
        # preview here and another imshow after inference causes flickering.
        self._show_window(image)

    def destroy_node(self):
        try:
            self._stop_camera()
        finally:
            if self.window_created:
                cv2.destroyAllWindows()
            super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    executor = None
    try:
        node = RealtimeTomatoDetector()
        # Only ROS subscriptions run on the worker. HighGUI, SDK and inference
        # remain on main, including shutdown, avoiding Qt cross-thread hangs.
        executor = SingleThreadedExecutor()
        executor.add_node(node)
        def receive():
            try:
                executor.spin()
            except ExternalShutdownException:
                pass
            except _rclpy.RCLError:
                if rclpy.ok():
                    raise
        worker = threading.Thread(target=receive, daemon=True)
        worker.start()
        deadline = time.monotonic()
        while rclpy.ok():
            node.process_frame()
            deadline += 1./node.rate_hz
            time.sleep(max(0., deadline-time.monotonic()))
            if time.monotonic()-deadline > 1./node.rate_hz:
                deadline = time.monotonic()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except _rclpy.RCLError:
        if rclpy.ok():
            raise
    finally:
        # Stop subscriptions before destroying node; GUI cleanup remains on main.
        if executor is not None:
            executor.shutdown(timeout_sec=2.0)
            if "worker" in locals():
                worker.join(timeout=2.)
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
