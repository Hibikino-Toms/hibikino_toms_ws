"""Harvest ownership, dwell, repeated cycles and lost EE heartbeat; no devices."""
import math
import numpy as np
from arm_controller_pkg.modules.harvest_cycle import HarvestCycle

TARGET=np.radians([5.,160.,-65.])
NEAR=np.radians([8.,158.,-66.])
LIMITS=np.radians([[-10,180],[-30,175],[-165,135]])


def cycle():
    return HarvestCycle({},TARGET,LIMITS,.25,.8)


def observation(now,track=1):
    return dict(received=now,track_id=track,pixel_error=[2.,90.],distance_error_m=.002,
                goal_yaw=math.radians(100))


def arrive(c,q,start):
    for t in np.arange(start+.1,start+1.,.1):
        cmd=c.step(q,float(t),observation(float(t)))
        if c.state=='HARVEST_HOLD':
            np.testing.assert_allclose(cmd,q)
            return float(t)
    raise AssertionError('arrival not detected')


def test_arrival_needs_continuous_fresh_same_target_and_low_velocity():
    c=cycle();c.ready(NEAR,0.)
    for t in [.1,.2,.3]:assert c.step(NEAR,t,observation(t)) is None
    assert c.step(NEAR,.4,None) is None
    for t in [.5,.6,.7]:assert c.step(NEAR,t,observation(t)) is None
    assert c.step(NEAR,.8,observation(.8,track=2)) is None
    assert c.state=='APPROACH'
    for i,t in enumerate([.9,1.,1.1]):
        assert c.step(NEAR+np.array([.02*i,0,-.02*i]),t,observation(t,track=2)) is None
    assert c.state=='APPROACH'


def test_two_complete_cycles_reject_vision_and_require_resume_key():
    c=cycle();c.ready(NEAR,0.)
    now=arrive(c,NEAR,0.);q=NEAR.copy()
    for run in range(2):
        # Occlusion, changed target, or a new observation cannot release hold.
        for _ in range(5):
            now+=.1
            np.testing.assert_allclose(c.step(q,now,None),q)
        assert not c.request('pull',now)[0]  # No live EE client.
        c.ee_seen=now
        assert c.request('pull',now)[0]
        assert not c.request('pull',now)[0]  # Duplicate pending action rejected.
        old=q.copy();velocity=np.zeros(3)
        for _ in range(100):
            now+=.1;c.ee_seen=now
            command=c.step(q,now,None)
            newvelocity=(np.array(command)-old)/.1
            assert max(abs(newvelocity))<=.25+1e-8
            assert max(abs(newvelocity-velocity))/.1<=.8+1e-6
            old=np.array(command);velocity=newvelocity;q=old.copy()
            if c.state=='RETURNED':break
        assert c.state=='RETURNED'
        np.testing.assert_allclose(q,TARGET)
        for _ in range(5):
            now+=.1
            np.testing.assert_allclose(c.step(q,now,observation(now)),TARGET)
        assert c.state=='RETURNED'
        assert not c.request('pull',now)[0]
        assert c.request('resume',now)[0]
        now+=.1
        assert c.step(q,now,None) is None
        assert c.state=='APPROACH'
        now=arrive(c,q,now)
        c.ee_seen=None


def test_return_heartbeat_loss_freezes_and_requires_explicit_command():
    c=cycle();c.ready(NEAR,0.);now=arrive(c,NEAR,0.)
    c.ee_seen=now;assert c.request('pull',now)[0]
    command=c.step(NEAR,now+.1)
    assert c.state=='RETURNING'
    command=c.step(command,now+1.2)
    assert c.state=='HARVEST_HOLD' and c.reason=='ee_heartbeat_lost'
    c.ee_seen=now+1.3
    np.testing.assert_allclose(c.step(command,now+1.3),command)
    assert c.state=='HARVEST_HOLD'


def test_operator_hold_interrupts_return_fault_cannot_resume():
    c=cycle();c.ready(NEAR,0.);now=arrive(c,NEAR,0.)
    c.ee_seen=now;assert c.request('pull',now)[0]
    command=c.step(NEAR,now+.1)
    assert c.request('hold',now+.2)[0]
    np.testing.assert_allclose(c.step(command,now+.2),command)
    assert c.state=='HARVEST_HOLD'
    c.fault('communication',now+.3)
    assert not c.request('resume',now+.4)[0]


def test_manual_hold_requires_measured_settling_before_pull():
    c=cycle();c.ready(NEAR,0.)
    assert c.request('hold',.1)[0]
    moved=NEAR+np.array([.02,0.,-.02])
    c.step(moved,.1)
    c.ee_seen=.1
    assert c.state=='HARVEST_HOLD' and c.hold_settled==0
    assert not c.request('pull',.1)[0]
    for t in [.2,.3,.4]:c.step(moved,t)
    assert c.hold_settled==3
    c.ee_seen=.4
    assert c.request('pull',.4)[0]
