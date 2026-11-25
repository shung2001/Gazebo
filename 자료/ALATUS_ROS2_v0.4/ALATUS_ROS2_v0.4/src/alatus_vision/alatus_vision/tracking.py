"""Image CV Kalman filter. Units px, px/s, seconds. No ROS dependency."""
from dataclasses import dataclass
import math
import numpy as np

@dataclass(frozen=True)
class Detection:
    class_id: int
    confidence: float
    xyxy: tuple

class KalmanTracker:
    def __init__(self, class_id=0, confidence=0.7, q=25., r=9., gate=9.21,
                 timeout=0.5, max_prediction=0.15, max_variance=2500., confirm=3):
        if not (q>0 and r>0 and gate>0 and timeout>=max_prediction>0 and max_variance>0 and confirm>=1):
            raise ValueError('Invalid filter configuration')
        self.class_id,self.confidence=class_id,confidence
        self.q,self.r,self.gate=q,r,gate
        self.timeout,self.max_prediction,self.max_variance,self.confirm=timeout,max_prediction,max_variance,confirm
        self.serial=0; self.reset()
    def reset(self):
        self.x=None;self.P=None;self.t=None;self.last_measurement=None
        self.hits=0;self.source=None;self.sequence=-1;self.dimensions=None
        self.state='LOST';self.innovation=None;self.last_confidence=0.
    def candidates(self, detections, width, height):
        if not (isinstance(width,int) and isinstance(height,int) and 0<width<=16384 and 0<height<=16384):
            return []
        out=[]
        for d in detections:
            if d.class_id!=self.class_id or len(d.xyxy)!=4: continue
            x1,y1,x2,y2=d.xyxy
            if (all(math.isfinite(v) for v in (*d.xyxy,d.confidence)) and
                self.confidence<=d.confidence<=1 and 0<=x1<x2<=width and 0<=y1<y2<=height):
                out.append((np.array([(x1+x2)/2,(y1+y2)/2]),d.confidence))
        return out
    def predict(self, stamp):
        if not math.isfinite(stamp) or self.t is None or stamp<self.t: raise ValueError('Non-monotonic time')
        dt=stamp-self.t
        if self.x is None: return
        F=np.eye(4);F[0,2]=F[1,3]=dt
        # Piecewise constant random acceleration; acceleration variance q.
        G=np.array([[dt*dt/2,0],[0,dt*dt/2],[dt,0],[0,dt]])
        self.x=F@self.x;self.P=F@self.P@F.T+self.q*(G@G.T);self.t=stamp
    def update(self, stamp, sequence, source, width, height, detections, now):
        if (not all(math.isfinite(v) for v in (stamp,now)) or not 0<=now-stamp<=self.timeout
            or not isinstance(sequence,int) or sequence<0 or not source):
            return False
        if self.source is not None and (source!=self.source or (width,height)!=self.dimensions):
            self.reset()  # New stream/resolution requires reconfirmation.
        if sequence<=self.sequence or (self.t is not None and stamp<=self.t): return False
        self.source=source;self.dimensions=(width,height);self.sequence=sequence
        if self.last_measurement is not None and stamp-self.last_measurement>self.timeout:
            self.x=None;self.P=None;self.hits=0;self.last_measurement=None
        candidates=self.candidates(detections,width,height)
        if self.x is None:
            self.t=stamp
            if not candidates: self.state='LOST';return False
            # Ambiguous acquisition: do not choose between multiple plausible targets.
            if len(candidates)!=1: self.state='AMBIGUOUS';return False
            z,self.last_confidence=candidates[0];self.x=np.r_[z,[0.,0.]]
            self.P=np.diag([self.r,self.r,400.,400.]);self.serial+=1;self.hits=1
        else:
            self.predict(stamp)
            H=np.array([[1,0,0,0],[0,1,0,0]],float);R=np.eye(2)*self.r
            S=H@self.P@H.T+R
            ranked=sorted(((float((z-H@self.x)@np.linalg.solve(S,z-H@self.x)),z) for z,_ in candidates),key=lambda a:a[0])
            accepted=[(d,z) for d,z in ranked if d<=self.gate]
            if not accepted: self.state='PREDICTION_ONLY';return False
            if len(accepted)>1 and abs(accepted[1][0]-accepted[0][0])<1.0:
                self.state='AMBIGUOUS';return False
            _,z=accepted[0];self.last_confidence=next(score for point,score in candidates if np.array_equal(point,z));innovation=z-H@self.x;self.innovation=innovation.copy()
            K=np.linalg.solve(S,(self.P@H.T).T).T
            self.x+=K@innovation
            A=np.eye(4)-K@H
            self.P=A@self.P@A.T+K@R@K.T  # Joseph covariance update
            self.P=(self.P+self.P.T)/2;self.hits+=1
        self.last_measurement=stamp
        self.state='TRACKED' if self.hits>=self.confirm else 'TENTATIVE'
        return True
    def snapshot(self, now):
        if self.x is None or self.last_measurement is None: return None
        if not math.isfinite(now) or now<self.t: return None
        age=now-self.last_measurement
        if age>self.timeout:
            self.state='LOST';return None
        # Projection never alters filter's measurement-time state.
        dt=now-self.t;F=np.eye(4);F[0,2]=F[1,3]=dt
        G=np.array([[dt*dt/2,0],[0,dt*dt/2],[dt,0],[0,dt]])
        P=F@self.P@F.T+self.q*G@G.T
        valid=(self.hits>=self.confirm and age<=self.max_prediction and
               np.isfinite(P).all() and max(P[0,0],P[1,1])<=self.max_variance and self.state!='AMBIGUOUS')
        return dict(x=F@self.x,P=P,age=age,valid=bool(valid),track_id=self.serial,
                    confidence=self.last_confidence,state=self.state if age<0.001 else 'PREDICTION_ONLY',stamp=self.last_measurement)
