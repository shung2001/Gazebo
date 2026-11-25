"""Bounded outer-loop PID; derivative may be supplied in error-units/s."""
from dataclasses import dataclass
import math

@dataclass
class PIDConfig:
    kp: float=0.0
    ki: float=0.0
    kd: float=0.0
    limit: float=0.0
    slew: float=0.0
    derivative_tau: float=0.1
    integral_limit: float=1.0
    max_dt: float=0.5

class PID:
    def __init__(self, config):
        self.c=config
        if not all(math.isfinite(v) for v in vars(config).values()): raise ValueError('Nonfinite config')
        if min(config.limit,config.slew,config.derivative_tau,config.integral_limit)<0 or config.max_dt<=0:
            raise ValueError('Invalid PID bounds')
        self.reset()
    def reset(self):
        self.integral=0.;self.previous=None;self.derivative=0.;self.output=0.
    def step(self,error,dt,enabled=True,rate=None,reset=False):
        if reset:self.reset()
        if not enabled or not math.isfinite(error) or not math.isfinite(dt) or not 0<dt<=self.c.max_dt or (rate is not None and not math.isfinite(rate)):
            self.reset();return 0.,False
        c=self.c
        raw_d=(0. if self.previous is None else (error-self.previous)/dt) if rate is None else rate
        a=dt/(c.derivative_tau+dt);self.derivative+=a*(raw_d-self.derivative)
        candidate=max(-c.integral_limit,min(c.integral_limit,self.integral+error*dt))
        def bounded(i):
            raw=c.kp*error+c.ki*i+c.kd*self.derivative
            clipped=max(-c.limit,min(c.limit,raw))
            final=max(self.output-c.slew*dt,min(self.output+c.slew*dt,clipped))
            return raw,final
        raw,out=bounded(candidate)
        # Conditional integration includes both magnitude and slew saturation.
        if (raw-out)*c.ki*error<=0: self.integral=candidate
        else: raw,out=bounded(self.integral)
        self.previous=error;self.output=out
        return out,abs(raw-out)>1e-9
