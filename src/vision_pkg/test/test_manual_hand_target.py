"""Selected-pixel targets through the real callback; no ROS node or hardware."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pyrealsense2 as rs
import pytest

from vision_pkg.modules.harvest_order import Transform
from vision_pkg.vision_service_ipad import Vision_Service
from arm_controller_pkg.modules.ik_solver_arm2 import InverseKinematicsSolver


def hand_target(*, pixel=(380, 360), cam2ee=(-7, 120, 60),
                ee2arm=(0, 320, 100), angle=0, offset=(0, 0)):
    config = dict(zip(
        ('X_DIFF_CAM2EE', 'Y_DIFF_CAM2EE', 'Z_DIFF_CAM2EE'), cam2ee))
    config.update(zip(('X_DIFF_EE2ARM', 'Y_DIFF_EE2ARM', 'Z_DIFF_EE2ARM'), ee2arm))
    config['CAM_ANGLE'] = angle
    with patch.object(Transform, 'load_yaml', return_value={
            'coordinate_transform_params': config}):
        transform = Transform()

    intrinsics = rs.intrinsics()
    intrinsics.width, intrinsics.height = 640, 480
    intrinsics.ppx, intrinsics.ppy = 320, 240
    intrinsics.fx, intrinsics.fy = 600, 600
    intrinsics.model = rs.distortion.none
    legacy_order = Mock(side_effect=AssertionError('legacy mixed Z must not be used'))
    node = SimpleNamespace(
        realsense_hand=SimpleNamespace(color_intrinsics=intrinsics),
        get_latest_frame=lambda *args: (np.zeros((480, 640, 3), np.uint8), None, None),
        harvest_order=SimpleNamespace(transform_tools=transform, order_decision=legacy_order),
        MANUAL_FIXED_DEPTH_MM=200.0,
        MANUAL_OFFSET_X_MM=offset[0], MANUAL_OFFSET_Z_MM=offset[1],
        get_logger=lambda: Mock())
    request = SimpleNamespace(pixel_x=pixel[0], pixel_y=pixel[1])
    response = Vision_Service.manual_hand_detect_callback(node, request, SimpleNamespace())
    assert response.found, response.message
    assert response.candidate_count == 1
    legacy_order.assert_not_called()
    return np.array([response.x[0], response.y[0], response.z[0]]), response.message


@pytest.mark.parametrize('offset, expected', [
    ((0, 0), [13, 640, 120]),
    ((5, -7), [18, 640, 113]),
])
def test_all_axes_reach_command_frame_before_manual_offsets(offset, expected):
    # This pixel at 200 mm is camera (20,40,200), EE (13,320,20).
    point, message = hand_target(offset=offset)
    np.testing.assert_allclose(point, expected, atol=1e-5)
    assert 'ee=(13.0,320.0,20.0)mm' in message
    assert 'arm_before=(13.0,640.0,120.0)mm' in message


def test_z_reference_change_reaches_target_and_negative_z_is_not_clamped():
    high, _ = hand_target(ee2arm=(0, 320, 100))
    low, _ = hand_target(ee2arm=(0, 320, -100))
    np.testing.assert_allclose(high - low, [0, 0, 200], atol=1e-5)
    assert low[2] == pytest.approx(-80)


def test_mount_rotation_precedes_both_translation_vectors():
    point, _ = hand_target(pixel=(320, 240), angle=90,
                           cam2ee=(0, 20, 50), ee2arm=(100, 200, 300))
    np.testing.assert_allclose(point, [100, 220, 150], atol=1e-5)


def test_selected_target_is_reached_by_link4_tip_in_active_ik_model():
    point, _ = hand_target(pixel=(620, 240), cam2ee=(0, 0, 0),
                           ee2arm=(-50, 150, 100))
    np.testing.assert_allclose(point, [50, 350, 100], atol=1e-5)
    ik = InverseKinematicsSolver(dict(
        Link1=270, Link2=61.75, Link3=275, Link4=130,
        MAX_LOOP_NUM=500, GOAL_DIS=0.01, GOAL_ANG=0.05,
        P_DELTA_PARAM=0.1, A_DELTA_PARAM=0.5))
    joints = [5, 150.4, -65.4]
    current = ik.forward_kinematics(*joints)
    _, result, success = ik.solve_ik(current, [point[0], point[1], 90], joints)
    assert success
    actual = ik.forward_kinematics(*result)
    np.testing.assert_allclose(actual[:2], point[:2], atol=0.01)
    assert actual[2] == pytest.approx(90, abs=0.05)
    # At yaw=90 the 130 mm tool offset lies along +Y; the wrist stops short.
    wrist_ik = InverseKinematicsSolver(dict(
        Link1=270, Link2=61.75, Link3=275, Link4=0,
        MAX_LOOP_NUM=500, GOAL_DIS=0.01, GOAL_ANG=0.05,
        P_DELTA_PARAM=0.1, A_DELTA_PARAM=0.5))
    wrist = wrist_ik.forward_kinematics(*result)
    np.testing.assert_allclose(np.array(actual[:2]) - wrist[:2], [0, 130], atol=0.02)
