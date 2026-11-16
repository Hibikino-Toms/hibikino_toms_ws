"""Z feature geometry: optical-down sign and coupled camera rotations."""
from pathlib import Path

import numpy as np
import pytest
import yaml

from vision_pkg.modules.image_servo import ImageServo


@pytest.mark.parametrize('error_m', [-.02, -.01, -.009, 0., .009, .01, .02])
def test_optical_down_is_negative_base_z(error_m):
    cfg = yaml.safe_load((Path(__file__).parents[1]/'config/realtime_detector.yaml').read_text())['target']
    servo = ImageServo(cfg, 640, 480)
    point = [0., -error_m, .25]
    correction = servo.vertical_correction(point, [0., 0., 1.], servo.reference)
    assert correction == pytest.approx(error_m)


def test_tilted_mount_satisfies_projection_after_z_only_move():
    cfg = yaml.safe_load((Path(__file__).parents[1]/'config/realtime_detector.yaml').read_text())['target']
    servo = ImageServo(cfg, 640, 480)
    theta = .1
    tilt = np.array([[1.,0.,0.], [0.,np.cos(theta),-np.sin(theta)], [0.,np.sin(theta),np.cos(theta)]])
    servo.matrix[:3,:3] = servo.matrix[:3,:3] @ tilt
    point = np.array([.01, .02, .25])
    ray = np.array([.03, .01, 1.])
    yaw = servo.reference+.2
    correction = servo.vertical_correction(point, ray, yaw)
    after = point-servo.camera_rotation(yaw).T[:,2]*correction
    assert after[1]/after[2] == pytest.approx(ray[1]/ray[2])
    # Relative correction does not double-add the mounting translation.
    servo.matrix[:3,3] = [1.,2.,3.]
    assert servo.vertical_correction(point, ray, yaw) == pytest.approx(correction)


def test_uncontrollable_mount_and_invalid_data_rejected():
    cfg = yaml.safe_load((Path(__file__).parents[1]/'config/realtime_detector.yaml').read_text())['target']
    servo = ImageServo(cfg, 640, 480)
    servo.matrix = np.eye(4)
    assert servo.vertical_correction([0., .01, .25], [0.,0.,1.], servo.reference) is None
    assert servo.vertical_correction([0., float('nan'), .25], [0.,0.,1.], servo.reference) is None
