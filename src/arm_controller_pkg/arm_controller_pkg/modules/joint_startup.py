"""Timer-driven joint initialization, independent of ROS and motor transport."""
import math


class JointStartup:
    def __init__(self, waypoints, limits, velocity, acceleration, minimum_duration=3.0,
                 timeout=60.0, tolerance=math.radians(1.0)):
        self.waypoints = [list(p) for p in waypoints]
        self.limits = limits
        self.velocity, self.acceleration = velocity, acceleration
        self.minimum_duration, self.timeout, self.tolerance = minimum_duration, timeout, tolerance
        if not self.waypoints:
            raise ValueError("startup requires at least one waypoint")
        for value in (velocity, acceleration, minimum_duration, timeout, tolerance):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("startup timing, limits and tolerance must be positive and finite")
        for point in self.waypoints:
            self.validate(point)
        self.index = 0
        self.started = None
        self.settled = 0
        self.done = False

    def validate(self, point):
        if len(point) != 3 or not all(math.isfinite(v) for v in point):
            raise ValueError("startup requires three finite joint angles")
        if any(not low <= q <= high for q, (low, high) in zip(point, self.limits)):
            raise ValueError("startup joint position outside configured limits")

    def step(self, measured, now):
        """Return one command and readiness; arrival never blocks the caller."""
        self.validate(measured)
        if self.done:
            return list(self.waypoints[-1]), True
        target = self.waypoints[self.index]
        if self.started is None:
            self.origin = list(measured) if self.index == 0 else list(self.waypoints[self.index - 1])
            delta = max(abs(b - a) for a, b in zip(self.origin, target))
            # Quintic blend maxima: |ds/du|=1.875, |d²s/du²|=10/sqrt(3).
            self.duration = max(self.minimum_duration, 1.875 * delta / self.velocity,
                                math.sqrt(10.0 / math.sqrt(3) * delta / self.acceleration))
            if self.duration >= self.timeout:
                raise RuntimeError("startup timeout shorter than velocity-limited motion duration")
            self.started = now
        elapsed = max(0., now - self.started)
        if elapsed > self.timeout:
            raise RuntimeError(f"startup waypoint {self.index + 1} arrival timed out")
        u = min(1., elapsed / self.duration)
        blend = 10*u**3 - 15*u**4 + 6*u**5
        command = [a + blend * (b - a) for a, b in zip(self.origin, target)]
        arrived = elapsed >= self.duration and max(abs(a - b) for a, b in zip(measured, target)) <= self.tolerance
        self.settled = self.settled + 1 if arrived else 0
        if self.settled >= 3:
            self.index += 1
            self.started = None
            self.settled = 0
            self.done = self.index == len(self.waypoints)
        return command, self.done
