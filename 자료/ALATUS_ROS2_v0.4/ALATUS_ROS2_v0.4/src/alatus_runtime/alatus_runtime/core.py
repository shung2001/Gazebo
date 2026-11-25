"""Pure Python logic; no ROS or flight control dependencies."""
from dataclasses import dataclass
from math import isfinite

def fresh(now, stamp, timeout=0.5):
    return all(isfinite(v) for v in (now, stamp, timeout)) and timeout > 0 and 0 <= now-stamp <= timeout

def observation_ok(valid, confidence, x, y, minimum=0.7):
    return bool(valid and all(isfinite(v) for v in (confidence, x, y))
                and minimum <= confidence <= 1 and 0 <= x <= 1 and 0 <= y <= 1)

@dataclass
class Tracker:
    hits: int = 0
    last_stamp: float = -1.0
    target_id: int = -1
    confirm_hits: int = 3
    max_age_s: float = 0.5
    max_gap_s: float = 0.5
    min_confidence: float = 0.7

    def reset(self):
        self.hits, self.last_stamp, self.target_id = 0, -1.0, -1

    def update(self, now, stamp, valid, confidence, x, y, target_id):
        ok = (fresh(now, stamp, self.max_age_s) and stamp > self.last_stamp
              and observation_ok(valid, confidence, x, y, self.min_confidence))
        contiguous = target_id == self.target_id and fresh(stamp, self.last_stamp, self.max_gap_s)
        self.hits = (self.hits + 1 if contiguous else 1) if ok else 0
        if ok:
            self.last_stamp = stamp
            self.target_id = target_id
        return ok and self.hits >= self.confirm_hits

@dataclass
class Mission:
    state: str = 'IDLE'
    requested: bool = False

    def request(self, start):
        if start and self.state == 'ABORT':
            return False  # Reset first: stop request acknowledges the latched abort.
        self.requested = start
        if not start:
            self.state = 'IDLE'
        return True

    def step(self, target_ok, status_ok):
        if self.state == 'ABORT':
            return self.state
        if not self.requested:
            self.state = 'IDLE'
        elif not status_ok:
            self.state = 'ABORT'
        elif target_ok:
            self.state = 'TRACK_SHADOW'
        elif self.state == 'TRACK_SHADOW':
            self.state = 'ABORT'
        else:
            self.state = 'SEARCH'
        return self.state

def proposal(x, y, allowed, center_x=0.5, center_y=0.5, gain=0.5, limit=0.2):
    if not allowed or not observation_ok(True, 1.0, x, y):
        return False, 0.0, 0.0, 0.0
    ex, ey = x-center_x, y-center_y
    return True, ex, ey, max(-limit, min(limit, -gain*ex))

def gate(proposal_ok, mission_ok, status_ok, shadow_only, correction, limit=0.2):
    inputs = bool(proposal_ok and mission_ok and status_ok and shadow_only
                  and isfinite(correction) and abs(correction) <= limit+1e-6)
    return inputs, False  # Immutable prohibition: no configuration can enable control.

