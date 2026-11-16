"""HighGUI lifecycle regression: camera/GUI must stay on main thread."""
from concurrent.futures import ThreadPoolExecutor
import threading
from unittest.mock import Mock
import numpy as np
import pytest
from vision_pkg import vison_sevice_realtime as realtime


def test_gui_is_single_main_thread_and_headless_does_not_open_window(monkeypatch):
    node=object.__new__(realtime.RealtimeTomatoDetector)
    node.show_window=True;node.window_created=False;node.window_name='test'
    events=[]
    monkeypatch.setattr(realtime.cv2,'namedWindow',lambda *a:events.append(('create',threading.current_thread())))
    monkeypatch.setattr(realtime.cv2,'imshow',lambda *a:events.append(('show',threading.current_thread())))
    monkeypatch.setattr(realtime.cv2,'waitKey',lambda *a:-1)
    img=np.zeros((10,10,3),np.uint8)
    node._show_window(img);node._show_window(img)
    assert [x[0] for x in events]==['create','show','show']
    assert all(x[1] is threading.main_thread() for x in events)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(RuntimeError,match='main thread'):
            pool.submit(node._show_window,img).result()
    node.show_window=False
    node._show_window(img)
    assert len(events)==3
    pipeline=Mock();node.pipeline=pipeline
    monkeypatch.setattr(realtime.cv2,'destroyAllWindows',lambda:events.append(('destroy',threading.current_thread())))
    monkeypatch.setattr(realtime.Node,'destroy_node',lambda _:None)
    node.destroy_node()
    pipeline.stop.assert_called_once()
    assert node.pipeline is None
    assert events[-1]==('destroy',threading.main_thread())


def frame_rig():
    from collections import deque
    from types import SimpleNamespace
    import yaml
    from pathlib import Path
    from vision_pkg.modules.image_servo import ImageServo
    cfg=yaml.safe_load((Path(__file__).parents[1]/'config/realtime_detector.yaml').read_text())['target']
    cfg=dict(cfg,desired_distance_m=.25,target_pixel=None,target_pixel_offset_x_px=0.,goal_yaw_deg=100.)
    node=object.__new__(realtime.RealtimeTomatoDetector)
    node.synthetic=True;node.ready=True;node.target_cfg=cfg
    node.servo=ImageServo(cfg,640,480);node.pose_history=deque([(10.,np.array([0.,.23,np.radians(100)]))])
    node.actual_max_age=.25;node.last_capture=None;node.last_frame_time=0.
    node.depth_scale=.0001;node.capture_stamp=10.
    node.color_intrinsics=realtime.rs.intrinsics();node.color_intrinsics.fx=node.color_intrinsics.fy=600.
    node.color_intrinsics.ppx=320.;node.color_intrinsics.ppy=240.
    node.frame_count=0;node.rate_samples=[];node.last_rate_log=realtime.time.monotonic();node.last_cycle_error_log=0.
    node.diag_pub=Mock();node.hold_pub=Mock();node._publish_goal=Mock();node._draw=Mock();node._show_status=Mock()
    node.get_logger=lambda:Mock()
    node.get_clock=lambda:SimpleNamespace(now=lambda:SimpleNamespace(nanoseconds=10_000_000_000))
    image=np.zeros((480,640,3),np.uint8);depth=np.full((480,640),2500,np.uint16)
    detections=[dict(center=(319.5,239.5),box=(300,220,340,260),confidence=.9,mask=None,center_source='bbox')]
    node._synthetic_frame=lambda:(image,depth,detections,10.)
    return node,image,depth,detections


def test_valid_frame_center_hold_and_stale_duplicate_lost():
    node,image,depth,detections=frame_rig()
    node.process_frame()
    goal=node._publish_goal.call_args.args[0]
    np.testing.assert_allclose(goal,[0.,.23,np.radians(100)])
    assert node._draw.call_count==1
    node.process_frame()
    assert node.diag['reason']=='duplicate_image'
    node.last_capture=None
    node._synthetic_frame=lambda:(image,depth,detections,9.)
    node.process_frame()
    assert node.diag['reason']=='stale_image'
    node._synthetic_frame=lambda:(image,depth,[],10.)
    node.process_frame()
    assert node.diag['reason']=='target_lost_or_ambiguous'
    assert node._publish_goal.call_count==1


def test_invalid_depth_inference_failure_and_pose_gap_hold():
    node,image,depth,detections=frame_rig()
    depth[:]=0
    node.process_frame();assert node.diag['reason']=='invalid_mask_depth'
    node.last_capture=None;depth[:]=2500
    node.pose_history.clear()
    node.process_frame();assert node.diag['reason']=='stale_or_unsynchronized_pose'
    def fail():raise RuntimeError('inference failed')
    node._synthetic_frame=fail
    node.process_frame();assert node.diag['reason']=='camera_or_inference_error'
    node._publish_goal.assert_not_called()


def test_pose_interpolation_wraps_only_yaw():
    node,*_=frame_rig()
    node.pose_history.clear()
    node.pose_history.extend([(10.,np.array([0.,.2,np.radians(179)])),
                              (10.1,np.array([.01,.2,np.radians(-179)]))])
    pose,gap=node._capture_pose(10.05)
    np.testing.assert_allclose(pose,[.005,.2,np.pi],atol=1e-10)
    assert node._capture_pose(11.)[0] is None


def test_draw_accepts_subpixel_boxes_and_shows_once():
    node,image,depth,detections=frame_rig()
    detections[0]['box']=(300.1,220.2,340.3,260.4)
    node.diag={'reason':'tracking'};node._show_window=Mock()
    realtime.RealtimeTomatoDetector._draw(node,image,detections,detections[0],None,.25)
    node._show_window.assert_called_once()


def test_no_camera_frames_shows_status_holds_and_publishes_zero_fps():
    node,*_=frame_rig()
    node.synthetic=False
    node.pipeline=Mock()
    node.pipeline.poll_for_frames.return_value=None
    node.last_frame_time=realtime.time.monotonic()-3.
    node.last_rate_log=realtime.time.monotonic()-6.
    node._maybe_reconnect_camera=Mock()
    logger=Mock();node.get_logger=lambda:logger
    node.process_frame()
    assert node.diag['reason']=='camera_timeout'
    node._show_status.assert_called_once()
    node._maybe_reconnect_camera.assert_called_once()
    node._publish_goal.assert_not_called()
    node.hold_pub.publish.assert_called_once()
    node.diag_pub.publish.assert_called_once()
    assert '0.00fps' in logger.info.call_args.args[0]


def test_camera_reconnect_is_throttled_and_waits_for_fresh_frame():
    node,*_=frame_rig()
    node.frame_timeout=2.;node.reconnect_interval=3.
    node.last_frame_time=realtime.time.monotonic()-4.
    node.last_camera_reconnect=-float('inf');node.camera_reconnect_count=0
    node._stop_camera=Mock();node._open_d405=Mock()
    node.diag={}
    node._maybe_reconnect_camera()
    assert node.diag['reason']=='camera_reconnecting'
    assert node.last_capture is None
    assert node.camera_reconnect_count==1
    node._stop_camera.assert_called_once()
    node._open_d405.assert_called_once()
    node._publish_goal.assert_not_called()
    node._maybe_reconnect_camera()
    assert node._open_d405.call_count==1


def test_camera_reconnect_failure_keeps_hold_and_reports_failure():
    node,*_=frame_rig()
    node.frame_timeout=2.;node.reconnect_interval=3.
    node.last_frame_time=realtime.time.monotonic()-4.
    node.last_camera_reconnect=-float('inf');node.camera_reconnect_count=0
    node._stop_camera=Mock();node._open_d405=Mock(side_effect=RuntimeError('USB device missing'))
    node.diag={}
    node._maybe_reconnect_camera()
    assert node.diag['reason']=='camera_reconnecting'
    assert node.diag['camera_reconnect_error']=='USB device missing'
    node._publish_goal.assert_not_called()


def z_frame_rig(phase='IDLE'):
    node,image,depth,detections=frame_rig()
    node.z_enabled=True;node.z_pub=Mock();node.frame_id='arm_base'
    node.z_status=(dict(stamp=10.,homed=True,xy_inhibited=phase!='IDLE',
                       phase=phase,trigger_error_m=.010), realtime.time.monotonic())
    return node,image,depth,detections


@pytest.mark.parametrize('offset_px,correction', [(0.,0.),(36.,-.015),(-36.,.015)])
def test_z_observation_uses_target_pixel_and_depth(offset_px,correction):
    node,image,depth,detections=z_frame_rig()
    detections[0]['center']=(319.5,239.5+offset_px)
    node.process_frame()
    msg=node.z_pub.publish.call_args.args[0]
    assert msg.vector.z==pytest.approx(correction,abs=1e-8)
    assert msg.header.frame_id=='arm_base' and msg.header.stamp.sec==10
    if abs(correction)>=.010:
        node._publish_goal.assert_not_called()
        node.hold_pub.publish.assert_not_called()  # A Z observation is not a stop request.
        assert node.diag['reason']=='z_motion_hold'
    else:node._publish_goal.assert_called_once()


def test_z_moving_keeps_observations_flowing_but_no_xy_goals():
    node,*_=z_frame_rig('MOVING_Z')
    node.process_frame()
    node.z_pub.publish.assert_called_once()
    node._publish_goal.assert_not_called()
    node.hold_pub.publish.assert_not_called()
    assert node.diag['reason']=='z_motion_hold'


def test_z_depth_jump_and_stale_state_issue_hold_not_motion():
    node,*_=z_frame_rig('MOVING_Z')
    node.z_previous_depth=.40;node.z_depth_track_id=1
    node.process_frame()
    assert node.diag['reason']=='depth_jump'
    node.z_pub.publish.assert_not_called()
    node.hold_pub.publish.assert_called_once()
    node,*_=z_frame_rig()
    node.z_status[0]['stamp']=9.
    node.process_frame()
    assert node.diag['reason']=='z_state_unavailable'
    node.z_pub.publish.assert_not_called()
