import math,threading,json
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import numpy as np
from arm_controller_pkg.arm_controller_xy_tracker import XYTracker
from arm_controller_pkg.modules.harvest_cycle import HarvestCycle
q=np.array([.5,1.,math.pi/2-1.5]);limits=np.array([[-2,2]]*3)
cycle=HarvestCycle({},q,limits,.25,.8);cycle.ready(q,99.)
obs=dict(capture_stamp=200.,received=100.05,pixel_error=[0.,0.],distance_error_m=0.,goal_yaw=sum(q),track_id=1)
n=SimpleNamespace(harvest=cycle,goal_lock=threading.Lock(),harvest_observation=obs,latest=(.1,.3,sum(q),100.05,200.),
    get_clock=lambda:SimpleNamespace(now=lambda:SimpleNamespace(nanoseconds=200080000000)),
    harvest_ik_ok=True,harvest_epoch=190.,solver=SimpleNamespace(forward_kinematics=lambda v:np.array([.1,.3,sum(v)])),
    last_command=None,diag={})
with patch('arm_controller_pkg.arm_controller_xy_tracker.time.monotonic',return_value=100.08):
    assert not XYTracker.step_harvest(n,q,100.)
assert cycle.stable_since==100.08
assert n.diag['arrival_check']['checks']['observation_fresh']
assert abs(n.diag['arrival_check']['observation_age_sec']-.03)<1e-9
print(json.dumps(n.diag,indent=2));Path('tracking_trials_20261117/arrival_timing_check.json').write_text(json.dumps(n.diag,indent=2))
