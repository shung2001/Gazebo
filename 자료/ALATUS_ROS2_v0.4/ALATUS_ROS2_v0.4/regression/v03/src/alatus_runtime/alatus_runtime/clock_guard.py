"""Monotonic observation of ROS clock progression; not a flight watchdog."""
from dataclasses import dataclass
from math import isfinite

@dataclass
class ClockGuard:
    last_ros: float = None
    last_progress: float = None
    failed: bool = False
    freeze_timeout_s: float = 0.5

    def update(self,ros_now,steady_now,sim_time):
        if self.failed: return False
        if not isfinite(ros_now) or not isfinite(steady_now): self.failed=True; return False
        if self.last_ros is None:
            self.last_ros,self.last_progress=ros_now,steady_now
            return True
        if ros_now<self.last_ros-1e-6:
            self.failed=True
        elif ros_now>self.last_ros:
            self.last_progress=steady_now
        elif sim_time and steady_now-self.last_progress>self.freeze_timeout_s:
            self.failed=True
        self.last_ros=ros_now
        return not self.failed
