"""Image horizontal/standoff servo. No ROS, camera or motor side effects."""
from collections import deque
from pathlib import Path
import math
import numpy as np


def resolve_weights(config_path, setting):
    path = Path(setting).expanduser()
    config_path = Path(config_path).resolve()
    candidates = [path] if path.is_absolute() else [(config_path.parent / path).resolve()]
    if not path.is_absolute():
        parts = list(path.parts)
        while parts and parts[0] in ('.', '..'):
            parts.pop(0)
        if parts:
            candidates += [parent / Path(*parts) for parent in config_path.parents]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError('YOLO weights not found; searched: ' + ', '.join(map(str, candidates)))


def rotation(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s, 0.], [s, c, 0.], [0., 0., 1.]])


class ImageServo:
    def __init__(self, cfg, width, height):
        self.cfg = cfg
        self.image_width = int(width)
        self.matrix = np.asarray(cfg['camera_to_end_effector'], float)
        if (self.matrix.shape != (4, 4) or not np.isfinite(self.matrix).all() or
                not np.allclose(self.matrix[3], [0, 0, 0, 1]) or
                not np.allclose(self.matrix[:3, :3].T @ self.matrix[:3, :3], np.eye(3), atol=1e-6) or
                not np.isclose(np.linalg.det(self.matrix[:3, :3]), 1.)):
            raise ValueError('camera_to_end_effector must be a proper rigid transform')
        self.reference = math.radians(float(cfg['camera_reference_yaw_deg']))
        self.yaw = math.radians(float(cfg['goal_yaw_deg']))
        configured_pixel = cfg.get('target_pixel')
        if configured_pixel is None:
            configured_pixel = [(width-1)/2., (height-1)/2.]
        self.pixel = np.asarray(configured_pixel, float)
        if self.pixel.shape != (2,) or not np.isfinite(self.pixel).all():
            raise ValueError('target_pixel must contain two finite pixel coordinates')
        pixel_offset_x = float(cfg.get('target_pixel_offset_x_px', 0.0))
        if not math.isfinite(pixel_offset_x):
            raise ValueError('target_pixel_offset_x_px must be finite')
        self.pixel[0] += pixel_offset_x
        pixel_offset_y = float(cfg.get('target_pixel_offset_y_px', 0.0))
        if not math.isfinite(pixel_offset_y):
            raise ValueError('target_pixel_offset_y_px must be finite')
        self.pixel[1] += pixel_offset_y
        if not (0 <= self.pixel[0] < width and 0 <= self.pixel[1] < height):
            raise ValueError('target_pixel must be inside image')
        positive = ('min_bbox_aspect', 'max_bbox_aspect', 'tracking_confidence', 'ambiguity_margin_px', 'min_bbox_area_px',
                    'max_bbox_area_px', 'depth_patch_radius_px', 'gain_per_sec', 'pixel_deadband_px', 'distance_deadband_m',
                    'max_speed_m_s', 'max_acceleration_m_s2', 'max_step_m',
                    'min_depth_m', 'max_depth_m', 'depth_jump_m', 'association_gate_px',
                    'lost_timeout_sec', 'stable_depth_spread_m', 'observation_max_age_sec',
                    'pose_sync_tolerance_sec', 'actual_max_age_sec', 'depth_spread_m')
        for key in positive:
            if not math.isfinite(float(cfg[key])) or float(cfg[key]) <= 0:
                raise ValueError(f'{key} must be finite and positive')
        if not np.isfinite([self.reference, self.yaw, cfg['fixed_z_m']]).all():
            raise ValueError('invalid pose settings')
        if cfg['tracking_confidence'] > 1 or cfg['min_bbox_area_px'] >= cfg['max_bbox_area_px'] or cfg['min_bbox_aspect'] >= cfg['max_bbox_aspect']:
            raise ValueError('invalid detection bounds')
        if cfg['min_depth_m'] >= cfg['max_depth_m']:
            raise ValueError('depth interval is empty')
        distance = float(cfg['desired_distance_m'])
        if not math.isfinite(distance) or distance < 0 or (distance and not cfg['min_depth_m'] <= distance <= cfg['max_depth_m']):
            raise ValueError('desired_distance_m must be 0 (initial lock) or within depth interval')
        if int(cfg['stable_depth_frames']) < 2:
            raise ValueError('stable_depth_frames must be at least 2')
        self.depths = deque(maxlen=int(cfg['stable_depth_frames']))
        self.distance = distance or None
        self.track = None
        self.track_id = 0
        self.seen = None
        self.previous_depth = None
        self.velocity = np.zeros(2)
        self.last_time = None
        far = cfg.get('image_approach', {})
        if not isinstance(far, dict) or not isinstance(far.get('enabled', False), bool):
            raise ValueError('image_approach must be a mapping with a boolean enabled')
        self.image_approach_enabled = far.get('enabled', False)
        self.far_cfg = dict(forward_speed_m_s=.04, lateral_gain_m_s_per_rad=.25,
                            forward_gate_ratio=.25, max_speed_m_s=.06,
                            max_acceleration_m_s2=.15, goal_horizon_sec=.25,
                            max_step_m=.015, max_blind_travel_m=.20,
                            max_blind_time_sec=15., travel_deadband_m=.001, depth_switch_max_m=.35,
                            depth_confirm_frames=3, depth_confirm_spread_m=.015,
                            depth_switch_hysteresis_m=.03,
                            depth_control_max_speed_m_s=.04)
        self.far_cfg.update(far)
        for key in self.far_cfg:
            if key == 'enabled':
                continue
            value = float(self.far_cfg[key])
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f'image_approach.{key} must be positive and finite')
            self.far_cfg[key] = value
        f = self.far_cfg
        if (not 0 < f['forward_gate_ratio'] <= .5 or f['goal_horizon_sec'] > .5 or
                f['forward_speed_m_s'] > f['max_speed_m_s'] or
                f['travel_deadband_m'] >= f['max_blind_travel_m'] or
                not cfg['min_depth_m'] < f['depth_switch_max_m'] <= cfg['max_depth_m'] or
                f['depth_switch_max_m']+f['depth_switch_hysteresis_m'] > cfg['max_depth_m'] or
                f['depth_confirm_frames'] < 2 or int(f['depth_confirm_frames']) != f['depth_confirm_frames'] or
                (distance and distance >= f['depth_switch_max_m'])):
            if self.image_approach_enabled:
                raise ValueError('invalid image_approach bounds, confirmation count, or desired distance')
        self.approach_mode = 'IMAGE_APPROACH'
        self.approach_track_id = None
        self.blind_started = None
        self.blind_previous_pose = None
        self.blind_travel = 0.
        self.close_depth_seen = False
        self.close_depths = deque(maxlen=int(f['depth_confirm_frames']))
        self.close_last_stamp = None
        self.depth_control_ready = False
        self.approach_fault = None

    def camera_rotation(self, yaw):
        return rotation(yaw-self.reference) @ self.matrix[:3, :3]

    def select(self, detections, stamp):
        # Keep ID through short occlusions. Never immediately switch to another
        # center-nearest object when the current object disappears.
        if self.seen is not None and stamp-self.seen > self.cfg['lost_timeout_sec']:
            self.track = None
            self.depths.clear()
            self.distance = float(self.cfg['desired_distance_m']) or None
            self.previous_depth = None
        eligible = []
        for d in detections:
            box = np.asarray(d['box'], float)
            area = (box[2]-box[0])*(box[3]-box[1])
            if not np.isfinite([*box, *d['center'], d['confidence']]).all():
                continue
            if not self.cfg['min_bbox_area_px'] <= area <= self.cfg['max_bbox_area_px']:
                continue
            aspect = (box[2]-box[0])/max(box[3]-box[1], 1e-12)
            if not self.cfg['min_bbox_aspect'] <= aspect <= self.cfg['max_bbox_aspect']:
                continue
            if d['confidence'] < self.cfg['tracking_confidence']:
                continue
            if self.track is not None:
                shift = np.linalg.norm(np.asarray(d['center'])-self.track['center'])
                old = self.track['box']
                old_area = (old[2]-old[0])*(old[3]-old[1])
                if shift > self.cfg['association_gate_px'] or not .5 <= area/old_area <= 2.:
                    continue
            eligible.append(d)
        if not eligible:
            return None
        anchor = self.pixel if self.track is None else np.asarray(self.track['center'])
        selected = min(eligible, key=lambda d: np.linalg.norm(np.asarray(d['center'])-anchor))
        # Ambiguous crossing/overlapping identities: hold, do not guess.
        distances = sorted(np.linalg.norm(np.asarray(d['center'])-anchor) for d in eligible)
        if self.track is not None and len(distances) > 1 and distances[1]-distances[0] < self.cfg['ambiguity_margin_px']:
            return None
        if self.track is None:
            self.track_id += 1
        self.track = selected
        self.seen = stamp
        return selected

    def hold(self):
        self.velocity[:] = 0.
        self.last_time = None

    def vertical_correction(self, point, desired_ray, yaw):
        """Z-only displacement that aligns the vertical feature at fixed XY/yaw.

        p_camera' = p_camera - R_camera_from_base[:,2] * delta_z.
        Solve p_y' - desired_ray_y/desired_ray_z * p_z' = 0.
        Camera translation cancels; no guessed mounting sign is introduced.
        """
        point, ray = np.asarray(point, float), np.asarray(desired_ray, float)
        if (point.shape != (3,) or ray.shape != (3,) or ray[2] <= 0 or point[2] <= 0 or
                not np.isfinite(np.r_[point, ray, yaw]).all()):
            return None
        slope = ray[1]/ray[2]
        camera_from_base = self.camera_rotation(yaw).T
        effectiveness = camera_from_base[1, 2]-slope*camera_from_base[2, 2]
        if abs(effectiveness) < .5:
            return None  # Reject a mount where Z has little vertical authority.
        return float((point[1]-slope*point[2])/effectiveness)

    def vertical_pixel_direction(self, desired_ray, yaw):
        """Sign of base-Z motion for a positive downward pixel error, no depth.

        dv/dZ = -fy/depth * (R.T[1,2] - target_slope*R.T[2,2]).
        Only its sign is used; pixels are never converted into metres here.
        """
        ray = np.asarray(desired_ray, float)
        if ray.shape != (3,) or not np.isfinite(np.r_[ray, yaw]).all() or ray[2] <= 0:
            return None
        r = self.camera_rotation(yaw).T
        effectiveness = r[1, 2] - ray[1]/ray[2]*r[2, 2]
        if abs(effectiveness) < .5:
            return None
        return 1 if effectiveness > 0 else -1

    def accept_approach_target(self):
        """Lock identity before either Z observations or XY goals are emitted."""
        if self.approach_track_id is None:
            self.approach_track_id = self.track_id
        elif self.track_id != self.approach_track_id:
            self.approach_fault = 'approach_target_changed'
        if self.approach_fault is not None:
            self.approach_mode = 'LIMIT_HOLD'
            self.hold()
            return False
        return True

    def update_approach(self, pixel, observed_ray, desired_ray, pose, stamp, depth=None):
        """Image-only lateral alignment/forward motion, then confirmed depth servo.

        Rays are optical directions, never a fabricated metric target. Speed
        gains are commands in m/s, not an estimate of the missing target depth.
        Once near depth is seen, missing/unstable depth cannot resume blind
        forward motion. Limits latch until a new explicit approach cycle.
        """
        pixel, ray, desired_ray, pose = map(lambda v: np.asarray(v, float),
                                           (pixel, observed_ray, desired_ray, pose))
        if (pixel.shape != (2,) or ray.shape != (3,) or desired_ray.shape != (3,) or pose.shape != (3,) or
                not np.isfinite(np.r_[pixel, ray, desired_ray, pose, stamp]).all() or
                ray[2] <= 0 or desired_ray[2] <= 0):
            self.hold()
            return None, dict(reason='nonfinite_observation')
        self.accept_approach_target()
        f = self.far_cfg
        diag = dict(track_id=self.track_id, center=pixel.tolist(), target_pixel=self.pixel.tolist(),
                    pixel_error=(pixel-self.pixel).tolist(), depth_m=depth,
                    desired_distance_m=self.distance, approach_mode=self.approach_mode,
                    blind_travel_m=self.blind_travel, depth_control_ready=self.depth_control_ready,
                    depth_confirm_count=len(self.close_depths))
        def withheld(reason):
            self.hold()
            return None, dict(diag, reason=reason, approach_mode=self.approach_mode)
        if self.approach_fault is not None:
            self.approach_mode = 'LIMIT_HOLD'
            return withheld(self.approach_fault)
        valid_depth = (depth is not None and math.isfinite(float(depth)) and
                       self.cfg['min_depth_m'] <= depth <= self.cfg['max_depth_m'])
        candidate = valid_depth and depth <= f['depth_switch_max_m']
        if candidate:
            # Stop unmeasured forward motion on the FIRST credible near sample.
            self.close_depth_seen = True
        if self.close_depth_seen:
            if not self.depth_control_ready:
                self.approach_mode = 'DEPTH_CONFIRMING'
                if self.close_last_stamp is not None and stamp-self.close_last_stamp > self.cfg['observation_max_age_sec']:
                    self.close_depths.clear()
                self.close_last_stamp = stamp
                # Once triggered, boundary noise must not keep a stationary
                # target just above the trigger distance in confirmation forever.
                confirmable = valid_depth and depth <= f['depth_switch_max_m']+f['depth_switch_hysteresis_m']
                if confirmable:
                    self.close_depths.append(float(depth))
                else:
                    self.close_depths.clear()
                diag['depth_confirm_count'] = len(self.close_depths)
                if (len(self.close_depths) < self.close_depths.maxlen or
                        np.ptp(self.close_depths) > f['depth_confirm_spread_m']):
                    return withheld('confirming_near_depth')
                self.depth_control_ready = True
                self.previous_depth = float(np.median(self.close_depths))
                self.hold()  # Metric control restarts with zero commanded velocity.
            self.approach_mode = 'DEPTH_CONTROL' if valid_depth else 'DEPTH_HOLD'
            if not valid_depth:
                return withheld('near_depth_lost_hold')
            point = ray/ray[2]*float(depth)
            goal, details = self.update(pixel, point, desired_ray, pose, stamp,
                                         speed_limit=f['depth_control_max_speed_m_s'],
                                         horizon_sec=f['goal_horizon_sec'])
            details.update(approach_mode=self.approach_mode, depth_control_ready=True,
                           depth_confirm_count=len(self.close_depths), blind_travel_m=self.blind_travel)
            return goal, details

        self.approach_mode = 'IMAGE_APPROACH'
        if self.blind_started is None:
            self.blind_started = stamp
            self.blind_previous_pose = pose[:2].copy()
        else:
            displacement = float(np.linalg.norm(pose[:2]-self.blind_previous_pose))
            if displacement >= f['travel_deadband_m']:
                self.blind_travel += displacement
                self.blind_previous_pose = pose[:2].copy()
        diag.update(approach_mode=self.approach_mode, blind_elapsed_sec=stamp-self.blind_started,
                    blind_travel_m=self.blind_travel)
        if self.blind_travel >= f['max_blind_travel_m'] or stamp-self.blind_started >= f['max_blind_time_sec']:
            self.approach_fault = 'image_approach_distance_or_time_limit'
            self.approach_mode = 'LIMIT_HOLD'
            return withheld(self.approach_fault)
        e_u = float(pixel[0]-self.pixel[0])
        angle = math.atan(ray[0]/ray[2])-math.atan(desired_ray[0]/desired_ray[2])
        angle *= max(0., abs(e_u)-self.cfg['pixel_deadband_px'])/max(abs(e_u), 1e-12)
        gate_px = f['forward_gate_ratio']*self.image_width
        forward = f['forward_speed_m_s']*max(0., 1.-abs(e_u)/gate_px)
        r = self.camera_rotation(pose[2]).T
        # du/dt depends on vx - observed_slope*vz. Include forward coupling
        # so a non-central target pixel does not create a persistent side drift.
        a = np.vstack([r[0, :2]-(ray[0]/ray[2])*r[2, :2], r[2, :2]])
        if np.linalg.cond(a) > 30:
            return withheld('uncontrollable_mount_geometry')
        desired = np.linalg.solve(a, [f['lateral_gain_m_s_per_rad']*angle, forward])
        cap = min(f['max_speed_m_s'], self.cfg['max_speed_m_s'], f['max_step_m']/f['goal_horizon_sec'])
        desired *= min(1., cap/max(np.linalg.norm(desired), 1e-12))
        dt = min(.15, max(.001, stamp-self.last_time)) if self.last_time is not None else 1./15
        self.last_time = stamp
        dv = desired-self.velocity
        self.velocity += dv*min(1., f['max_acceleration_m_s2']*dt/max(np.linalg.norm(dv), 1e-12))
        delta = self.velocity*f['goal_horizon_sec']
        # Enforce the travel budget before issuing the next look-ahead target.
        remaining = max(0., f['max_blind_travel_m']-self.blind_travel)
        delta *= min(1., remaining/max(np.linalg.norm(delta), 1e-12))
        return np.r_[pose[:2]+delta, self.yaw], dict(diag, reason='image_approach',
            angular_error_rad=angle, forward_speed_m_s=forward,
            command_velocity_xy_m_s=self.velocity.tolist(), delta_xy_m=delta.tolist(),
            depth_control_ready=False, distance_error_m=None)

    def note_approach_depth(self, depth):
        """Remember a near observation even while Z owns the arm."""
        if (depth is not None and math.isfinite(float(depth)) and
                self.cfg['min_depth_m'] <= depth <= self.far_cfg['depth_switch_max_m']):
            self.close_depth_seen = True

    def reject_approach_observation(self):
        """A lost/rejected image breaks depth confirmation, not the travel budget."""
        self.close_depths.clear()
        self.close_last_stamp = None
        if self.close_depth_seen:
            self.depth_control_ready = False

    def update(self, pixel, point, desired_ray, pose, stamp, speed_limit=None, horizon_sec=None):
        """point is optical XYZ in m; pose is capture-time arm XY/yaw.

        With yaw fixed: dp_camera = -R.T[:, :2] dXY. Use ONLY horizontal
        feature p_x - ray_target_x*p_z and optical depth; never vertical error.
        Translation offsets cancel in this relative displacement equation.
        """
        pixel = np.asarray(pixel, float)
        point, desired_ray, pose = map(lambda x: np.asarray(x, float), (point, desired_ray, pose))
        if pixel.shape != (2,) or point.shape != (3,) or desired_ray.shape != (3,) or pose.shape != (3,) or desired_ray[2] <= 0 or not np.isfinite(np.r_[point, desired_ray, pose, pixel, stamp]).all():
            self.hold()
            return None, {'reason': 'nonfinite_observation'}
        depth = float(point[2])
        diag = dict(track_id=self.track_id, center=list(map(float, pixel)), target_pixel=self.pixel.tolist(),
                    pixel_error=(np.asarray(pixel)-self.pixel).tolist(), depth_m=depth,
                    desired_distance_m=self.distance, vertical_controlled=False)
        reason = None
        if not self.cfg['min_depth_m'] <= depth <= self.cfg['max_depth_m']:
            reason = 'invalid_depth'
        elif self.previous_depth is not None and abs(depth-self.previous_depth) > self.cfg['depth_jump_m']:
            reason = 'depth_jump'
        if reason:
            self.hold()
            return None, dict(diag, reason=reason)
        self.previous_depth = depth
        if self.distance is None:
            self.depths.append(depth)
            if len(self.depths) < self.depths.maxlen or np.ptp(self.depths) > self.cfg['stable_depth_spread_m']:
                self.hold()
                return None, dict(diag, reason='locking_initial_distance')
            self.distance = float(np.median(self.depths))
        diag['desired_distance_m'] = self.distance
        diag['distance_error_m'] = depth-self.distance
        error_u = float(pixel[0]-self.pixel[0])
        lateral = float(point[0] - desired_ray[0]/desired_ray[2]*depth)
        # Continuous dead zones prevent a discontinuous step at the boundary.
        lateral *= max(0., abs(error_u)-self.cfg['pixel_deadband_px'])/max(abs(error_u), 1e-12)
        dz = math.copysign(max(0., abs(depth-self.distance)-self.cfg['distance_deadband_m']), depth-self.distance)
        r = self.camera_rotation(pose[2]).T
        a = np.vstack([r[0, :2]-desired_ray[0]/desired_ray[2]*r[2, :2], r[2, :2]])
        if np.linalg.cond(a) > 30:
            self.hold()
            return None, dict(diag, reason='uncontrollable_mount_geometry')
        dt = min(.15, max(.001, stamp-self.last_time)) if self.last_time is not None else 1./15
        self.last_time = stamp
        desired = np.linalg.solve(a, [lateral, dz])*self.cfg['gain_per_sec']
        cap = min(self.cfg['max_speed_m_s'], self.cfg['max_step_m']/.15)
        if speed_limit is not None:
            cap = min(cap, float(speed_limit))
        desired *= min(1., cap/max(np.linalg.norm(desired), 1e-12))
        dv = desired-self.velocity
        self.velocity += dv*min(1., self.cfg['max_acceleration_m_s2']*dt/max(np.linalg.norm(dv), 1e-12))
        # A frame interval of look-ahead is too short for the slower joint/motor
        # follower and makes receding goals nearly stationary. Use a bounded
        # look-ahead in the hybrid approach; retain legacy update semantics.
        horizon = dt if horizon_sec is None else float(horizon_sec)
        if not math.isfinite(horizon) or not 0 < horizon <= .5:
            raise ValueError('goal horizon must be finite and in (0,0.5] seconds')
        delta = self.velocity*horizon
        delta *= min(1., self.cfg['max_step_m']/max(np.linalg.norm(delta), 1e-12))
        return np.r_[pose[:2]+delta, self.yaw], dict(diag, reason='tracking', delta_xy_m=delta.tolist())


def robust_depth(depth_image, mask, pixel, scale, cfg):
    u, v = np.rint(pixel).astype(int)
    r = int(cfg['depth_patch_radius_px'])
    y0, y1 = max(0, v-r), min(depth_image.shape[0], v+r+1)
    x0, x1 = max(0, u-r), min(depth_image.shape[1], u+r+1)
    patch = depth_image[y0:y1, x0:x1].astype(float)*scale
    valid = (patch >= cfg['min_depth_m']) & (patch <= cfg['max_depth_m']) & np.isfinite(patch)
    if mask is not None:
        valid &= mask[y0:y1, x0:x1]
    values = patch[valid]
    if len(values) < 3 or np.ptp(np.percentile(values, [10, 90])) > cfg['depth_spread_m']:
        return None  # Never substitute background outside a failed mask.
    return float(np.median(values))
