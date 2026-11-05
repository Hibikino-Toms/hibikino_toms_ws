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

    def update(self, pixel, point, desired_ray, pose, stamp):
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
        desired *= min(1., cap/max(np.linalg.norm(desired), 1e-12))
        dv = desired-self.velocity
        self.velocity += dv*min(1., self.cfg['max_acceleration_m_s2']*dt/max(np.linalg.norm(dv), 1e-12))
        delta = self.velocity*dt
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
