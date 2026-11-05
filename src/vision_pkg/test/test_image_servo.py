"""No camera or motors: fixed world points projected through FK of moving arm."""
from pathlib import Path
import json
import time
import numpy as np
import pytest
import yaml
from vision_pkg.modules.image_servo import ImageServo, resolve_weights, robust_depth
from arm_controller_pkg.modules.ik_solver_arm3 import InverseKinematicsSolver
from arm_controller_pkg.modules.yaw_joint_limiter import joint_step

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT/'src/vision_pkg/config/realtime_detector.yaml'
CFG = dict(yaml.safe_load(CONFIG.read_text())['target'], target_pixel=None,
           target_pixel_offset_x_px=0., desired_distance_m=0., gain_per_sec=2.,
           max_speed_m_s=.025, max_acceleration_m_s2=.08, max_step_m=.003)
ARM = yaml.safe_load((ROOT/'src/arm_controller_pkg/config/xy_robot_config.yaml').read_text())


def solver(**kwargs):
    return InverseKinematicsSolver(dict(ARM['ik_solver_params'], position_tolerance_m=1e-5,
                                       angle_tolerance_rad=1e-4, **kwargs))


def closed_loop(offset, vertical=0., depth=.25, seconds=60):
    servo = ImageServo(dict(CFG, desired_distance_m=.25), 640, 480)
    ik = solver()
    q = np.radians([5., 160., -65.]); command=q.copy(); vel=np.zeros(3)
    initial=ik.forward_kinematics(q)
    world=np.r_[initial[:2], 0.]+servo.camera_rotation(initial[2])@np.array([
        offset-.5*depth/600, vertical-.5*depth/600, depth])
    rows=[]
    for step in range(int(seconds/.1)):
        pose=ik.forward_kinematics(q)
        point=servo.camera_rotation(pose[2]).T@(world-np.r_[pose[:2],0.])
        pixel=point[:2]/point[2]*600+[320,240]
        goal,diag=servo.update(pixel,point,[-.5/600,-.5/600,1],pose,step*.1)
        assert goal is not None
        result=ik.solve(goal,q)
        assert result.success, result
        previous_velocity=vel.copy()
        command,vel=joint_step(command,vel,result.joints,servo.yaw,ik.limits,.1,.25,.8)
        assert np.max(abs(vel)) <= .25+1e-10
        assert np.max(abs(vel-previous_velocity))/.1 <= .8+1e-10
        assert np.all(command>=ik.limits[:,0]-1e-10) and np.all(command<=ik.limits[:,1]+1e-10)
        # First-order physical lag common to all joints; measured state is never
        # substituted with the IK solution. Additional joint-dependent lag below.
        q += .7*(command-q)
        rows.append(dict(t=step*.1, pixel_error=(pixel-servo.pixel).tolist(), depth=float(point[2]),
                         actual_yaw=float(sum(q)),command_yaw=float(sum(command)),
                         xy=pose[:2].tolist(),goal=goal.tolist()))
    return rows


@pytest.mark.parametrize('offset',[-.025,0.,.025])
def test_closed_loop_horizontal(offset):
    rows=closed_loop(offset)
    assert abs(rows[-1]['pixel_error'][0]) < 3.6
    assert abs(rows[-1]['depth']-.25) < .004
    assert max(abs(r['command_yaw']-np.radians(100)) for r in rows)<1e-10
    assert max(abs(r['actual_yaw']-np.radians(100)) for r in rows)<1e-10
    assert np.linalg.norm(np.array(rows[-1]['xy'])-rows[-50]['xy']) < .0002
    if offset==0:
        assert np.linalg.norm(np.array(rows[-1]['xy'])-rows[0]['xy']) < 1e-10


def test_uncontrolled_vertical_does_not_retreat():
    rows=closed_loop(0.,vertical=.04,seconds=5.)
    assert abs(rows[-1]['pixel_error'][1])>90
    assert np.linalg.norm(np.array(rows[-1]['xy'])-rows[0]['xy'])<1e-10


def test_distance_error_is_reduced_not_full_depth_approach():
    rows=closed_loop(0.,depth=.275)
    assert abs(rows[-1]['depth']-.25)<.0045
    assert rows[-1]['depth']>.245


def test_initial_distance_lock_and_depth_jump():
    s=ImageServo(dict(CFG,desired_distance_m=0.0),640,480)
    for i in range(6):
        goal,d=s.update([319.5,239.5],[-.25*.5/600,-.25*.5/600,.25],[-.5/600,-.5/600,1], [0,.23,np.radians(100)],i*.1)
    assert goal is not None and s.distance==.25
    goal,d=s.update([319.5,239.5],[0,0,.8],[0,0,1],[0,.23,np.radians(100)],1.)
    assert goal is None and d['reason']=='depth_jump'
    assert s.distance==.25
    assert s.update([319.5,239.5],[0,0,.25],[0,0,1],[0,.23,np.radians(100)],1.1)[0] is not None


def detection(x,confidence=.9):
    return dict(center=(x,240.),box=(x-10,230,x+10,250),confidence=confidence)


def test_identity_loss_reacquisition_and_bad_detections():
    s=ImageServo(CFG,640,480)
    slender=dict(center=(319.5,239.5),box=(300,100,330,300),confidence=.95)
    assert s.select([slender],0.) is None
    assert s.select([detection(310),detection(380)],0)['center'][0]==310
    assert s.select([detection(305),detection(323)],.1)['center'][0]==305
    assert s.select([detection(380)],.2) is None
    assert s.select([detection(309)],.3)['center'][0]==309 and s.track_id==1
    assert s.select([detection(308),detection(310)],.4) is None # ambiguous overlap
    assert s.select([detection(312, .1)],.5) is None
    assert s.select([detection(380)],2.) is not None and s.track_id==2


def test_invalid_mask_depth_never_uses_background():
    depth=np.full((480,640),2500,np.uint16);mask=np.zeros_like(depth,bool)
    assert robust_depth(depth,mask,(320,240),.0001,CFG) is None
    assert robust_depth(depth,None,(320,240),.0001,CFG)==.25
    depth[235:246,315:320]=5000
    assert robust_depth(depth,None,(320,240),.0001,CFG) is None


def test_principal_point_and_image_center_are_distinct():
    s=ImageServo(dict(CFG,desired_distance_m=.25),640,480)
    ray=np.array([(319.5-326)/610,(239.5-232)/605,1.])
    goal,_=s.update(s.pixel,ray*.25,ray,[.1,.2,s.yaw],0.)
    np.testing.assert_allclose(goal,[.1,.2,s.yaw],atol=1e-12)


def test_horizontal_target_pixel_offset_from_image_center():
    center=ImageServo(dict(CFG,desired_distance_m=.25),640,480)
    right=ImageServo(dict(CFG,desired_distance_m=.25,target_pixel_offset_x_px=40.),640,480)
    left=ImageServo(dict(CFG,desired_distance_m=.25,target_pixel_offset_x_px=-25.),640,480)
    np.testing.assert_allclose(center.pixel,[319.5,239.5])
    np.testing.assert_allclose(right.pixel,[359.5,239.5])
    np.testing.assert_allclose(left.pixel,[294.5,239.5])


def test_horizontal_offset_is_added_to_explicit_pixel_and_validated():
    shifted=ImageServo(dict(CFG,desired_distance_m=.25,target_pixel=[300.,200.],
                            target_pixel_offset_x_px=12.5),640,480)
    np.testing.assert_allclose(shifted.pixel,[312.5,200.])
    with pytest.raises(ValueError,match='inside image'):
        ImageServo(dict(CFG,target_pixel_offset_x_px=400.),640,480)
    with pytest.raises(ValueError,match='finite'):
        ImageServo(dict(CFG,target_pixel_offset_x_px=float('nan')),640,480)


def test_transform_translation_cancels_and_rotated_mount():
    cfg=dict(CFG,desired_distance_m=.25)
    cfg['camera_to_end_effector']=np.array(cfg['camera_to_end_effector'],float).copy()
    cfg['camera_to_end_effector'][:3,3]=[.3,-.2,.1]
    a,b=ImageServo(cfg,640,480),ImageServo(dict(CFG,desired_distance_m=.25),640,480)
    args=([350,240],[.02,0,.25],[0,0,1],[0,.23,np.radians(110)],0.)
    np.testing.assert_allclose(a.update(*args)[0],b.update(*args)[0])


def test_ik_jacobian_bounds_and_unreachable():
    ik=solver();q=np.radians([5,160,-65]);h=1e-6
    fd=np.column_stack([(ik.forward_kinematics(q+np.eye(3)[i]*h)-ik.forward_kinematics(q-np.eye(3)[i]*h))/(2*h) for i in range(3)])
    np.testing.assert_allclose(fd,ik.jacobian(q),atol=1e-9)
    assert ik.solve(ik.forward_kinematics(q),q).success
    assert not ik.solve([10,10,0],q).success
    assert not ik.solve([0,.23,1.7],np.radians([-20,160,-65])).success
    for invalid in ([1,2],[1,float('nan'),3]):
        with pytest.raises(ValueError):ik.solve(invalid,q)
    # Nearly singular seed: updates remain bounded; failure is not success.
    res=ik.solve([0.,0.,0.],np.array([0.,0.,0.]))
    assert np.isfinite(res.joints).all()
    assert np.all(res.joints>=ik.limits[:,0]) and np.all(res.joints<=ik.limits[:,1])


def test_joint_limiter_midpoints_and_independent_physical_lag():
    ik=solver();q=np.radians([5,160,-65]);actual=q.copy();v=np.zeros(3)
    target=q+np.array([.2,-.35,.15]);error=[]
    for _ in range(150):
        prev=q.copy();oldv=v.copy()
        q,v=joint_step(q,v,target,np.radians(100),ik.limits,.1,.25,.8)
        assert max(abs(v-oldv))<=.080000001
        assert abs(sum((prev+q)/2)-np.radians(100))<1e-12
        actual += np.array([.5,.7,.6])*(q-actual)
        error.append(abs(sum(actual)-np.radians(100)))
    # Physical unequal lag remains measurable even when commanded yaw is exact.
    assert max(error) > 1e-4 and error[-1]<1e-6
    with pytest.raises(ValueError):joint_step([np.nan,0,0],v,target,0,ik.limits,.1,.25,.8)
    q=ik.limits[:,1].copy()
    with pytest.raises(ValueError):joint_step(q,[.25]*3,q,0,ik.limits,.1,.25,.8)


def test_weight_resolution_source_and_install():
    for config in [CONFIG,ROOT/'install/vision_pkg/share/vision_pkg/config/realtime_detector.yaml']:
        assert resolve_weights(config,'../../../module/weights/base.pt')==ROOT/'module/weights/base.pt'


if __name__=='__main__':
    summary={}
    for offset in [0.,-.025,.025]:
        start=time.monotonic();rows=closed_loop(offset)
        summary[str(offset)]={'initial_pixel_error':rows[0]['pixel_error'], 'final_pixel_error':rows[-1]['pixel_error'],
                             'final_depth_m':rows[-1]['depth'], 'max_command_yaw_error_rad':max(abs(r['command_yaw']-np.radians(100)) for r in rows),
                             'compute_sec':time.monotonic()-start, 'simulated_sec':60}
    out=ROOT/'src/vision_pkg/validation/closed_loop.json';out.write_text(json.dumps(summary,indent=2))
    print(out.read_text())


def test_uncontrollable_mount_and_invalid_values():
    cfg=dict(CFG,desired_distance_m=.25,camera_to_end_effector=np.eye(4))
    s=ImageServo(cfg,640,480)
    goal,d=s.update([330,240],[.01,0,.25],[0,0,1],[0,.23,s.yaw],0.)
    assert goal is None and d['reason']=='uncontrollable_mount_geometry'
    assert s.update([float('nan'),240],[0,0,.25],[0,0,1],[0,.23,s.yaw],1.)[0] is None
    for key in ['gain_per_sec','max_speed_m_s','goal_yaw_deg']:
        with pytest.raises(ValueError):ImageServo(dict(CFG,**{key:float('nan')}),640,480)


def test_wrapped_yaw_and_no_convergence_are_not_joint_wrapping():
    ik=solver();q=np.radians([5,160,-65]);goal=ik.forward_kinematics(q);goal[2]+=2*np.pi
    assert ik.solve(goal,q).success
    limited,_=joint_step(q,[0,0,0],q,goal[2],ik.limits,.1,.25,.8)
    np.testing.assert_allclose(limited,q,atol=1e-12)
    assert not solver(MAX_LOOP_NUM=1).solve([.1,.3,np.radians(100)],q).success


def test_image_velocity_acceleration_and_step_limits():
    s=ImageServo(dict(CFG,desired_distance_m=.25),640,480)
    previous=np.zeros(2)
    for i in range(50):
        pixel=[600 if i<25 else 40,240];point=[.1 if i<25 else -.1,0,.25]
        goal,_=s.update(pixel,point,[0,0,1],[0,.23,s.yaw],i*.1)
        assert np.linalg.norm(s.velocity)<=CFG['max_speed_m_s']+1e-10
        assert np.linalg.norm(s.velocity-previous)<CFG['max_acceleration_m_s2']*.1+1e-10
        assert np.linalg.norm(goal[:2]-[0,.23])<=CFG['max_step_m']+1e-10
        previous=s.velocity.copy()
