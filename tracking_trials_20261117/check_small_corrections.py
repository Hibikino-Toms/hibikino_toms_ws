import json, math
from pathlib import Path
import numpy as np, yaml
from arm_controller_pkg.modules.ik_solver_arm3 import InverseKinematicsSolver
config=yaml.safe_load(Path('src/arm_controller_pkg/config/xy_robot_config.yaml').read_text())
params=dict(config['ik_solver_params'],joint_limits_deg=config['joint_limits_deg'],position_tolerance_m=.02,angle_tolerance_rad=.05)
s=InverseKinematicsSolver(params)
q=np.radians(config['startup']['demo_joints_deg']); pose=s.forward_kinematics(q)
rows=[]
for delta in ([-.001,0,0],[.001,0,0],[0,.001,0],[0,-.001,0]):
    goal=pose+delta; old=s.solve(goal,q); new=s.solve_tracking(goal,q)
    assert old.iterations==0
    assert new.success and new.iterations>0 and np.max(np.abs(new.joints-q))>1e-5
    assert new.position_error_m<=.0001
    rows.append(dict(delta=delta,normal_iterations=old.iterations,tracking_iterations=new.iterations,
        tracking_position_error_m=new.position_error_m,delta_joints_deg=np.degrees(new.joints-q).tolist()))
print(json.dumps(rows,indent=2));Path('tracking_trials_20261117/small_corrections.json').write_text(json.dumps(rows,indent=2))
