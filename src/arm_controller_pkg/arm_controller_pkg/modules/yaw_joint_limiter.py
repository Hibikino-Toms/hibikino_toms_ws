"""Joint command state, bounded acceleration and coupled yaw constraint."""
import numpy as np


def joint_step(previous, velocity, target, yaw, limits, dt, vmax, amax):
    q, v, target, limits = map(lambda x: np.asarray(x, float), (previous, velocity, target, limits))
    if q.shape != (3,) or v.shape != (3,) or target.shape != (3,) or limits.shape != (3, 2):
        raise ValueError('invalid joint limiter shapes')
    if not np.isfinite(np.r_[q, v, target, limits.ravel(), dt, vmax, amax, yaw]).all() or min(dt, vmax, amax) <= 0:
        raise ValueError('invalid joint limiter values')
    # Critically damped setpoint follower. Limit velocity BEFORE integration.
    wanted = v + (16.*(target-q)-8.*v)*dt
    lo = np.maximum.reduce([-np.full(3, vmax), v-amax*dt, (limits[:, 0]-q)/dt])
    hi = np.minimum.reduce([np.full(3, vmax), v+amax*dt, (limits[:, 1]-q)/dt])
    if np.any(lo > hi+1e-12):
        raise ValueError('joint limit/acceleration constraints infeasible; hold required')
    # Wrapped yaw error, never wrap individual mechanical joint coordinates.
    yaw_error = (yaw-float(sum(q))+np.pi) % (2*np.pi)-np.pi
    total = np.clip(yaw_error/dt, sum(lo), sum(hi))
    # Euclidean projection on a box intersected with sum(v)=total. Independent
    # clipping would change q1+q2+q3 even with an exactly constant IK yaw.
    left, right = float(min(wanted-hi)-1.), float(max(wanted-lo)+1.)
    for _ in range(60):
        mid = (left+right)/2.
        if sum(np.clip(wanted-mid, lo, hi)) > total:
            left = mid
        else:
            right = mid
    new_v = np.clip(wanted-(left+right)/2., lo, hi)
    return q+new_v*dt, new_v
