import math,copy
from pathlib import Path
import numpy as np
import pytest,yaml
from alatus_vision.tracking import KalmanTracker,Detection
from alatus_vision.pid import PID,PIDConfig
from alatus_vision.geometry import pixel_ray,bearing,net_intersection
from alatus_vision.guidance import Guidance
from alatus_mavros.authority import validate_permit,eligible
ROOT=Path(__file__).resolve().parents[1]

def det(u=320,v=240,score=.9,cls=0):return Detection(cls,score,(u-5,v-5,u+5,v+5))
def locked():
 k=KalmanTracker()
 for i in range(5):k.update(1+i*.05,i,'test',640,480,[det()],1+i*.05)
 return k
@pytest.mark.parametrize('box',[Detection(1,.9,(0,0,10,10)),Detection(0,.1,(0,0,10,10)),Detection(0,.9,(0,0,0,10)),Detection(0,.9,(-1,0,10,10)),Detection(0,.9,(0,0,641,10)),Detection(0,float('nan'),(0,0,10,10)),Detection(0,.9,(0,0,float('inf'),10))])
def test_invalid_detection(box):assert not KalmanTracker().candidates([box],640,480)
def test_acquisition_ambiguity():
 k=KalmanTracker();assert not k.update(1,0,'a',640,480,[det(),det(400)],1);assert k.x is None

def test_stationary():
 k=locked();s=k.snapshot(1.2);assert s['valid'];np.testing.assert_allclose(s['x'],[320,240,0,0],atol=1e-9)
def test_variable_dt_motion():
 k=KalmanTracker(q=.01,r=.1)
 t=1.
 for i in range(100):
  t+=.02 if i%2 else .07;k.update(t,i,'a',640,480,[det(200+10*t)],t)
 assert abs(k.x[2]-10)<.1
 np.testing.assert_allclose(k.P,k.P.T,atol=1e-12);assert np.linalg.eigvalsh(k.P).min()>0

def test_outlier_missing_timeout():
 k=locked();k.update(1.25,5,'test',640,480,[det(600,400)],1.25)
 assert k.state=='PREDICTION_ONLY';assert abs(k.x[0]-320)<1
 assert k.snapshot(1.3)['valid'];assert not k.snapshot(1.4)['valid'];assert k.snapshot(1.8) is None

def test_covariance_growth():
 k=locked();assert np.trace(k.snapshot(1.3)['P'])>np.trace(k.snapshot(1.2)['P'])
@pytest.mark.parametrize('t,seq,now',[(float('nan'),6,1.3),(1.25,3,1.3),(.9,6,1.3),(2.,6,1.3),(1.25,6,2.)])
def test_invalid_timestamp(t,seq,now):
 k=locked();x=k.x.copy();assert not k.update(t,seq,'test',640,480,[det()],now);np.testing.assert_array_equal(k.x,x)
def test_reset_reacquire():
 k=locked();old=k.serial;k.reset();assert k.snapshot(3) is None
 k.update(3,0,'new',640,480,[det(100)],3);assert k.serial>old and k.hits==1

def test_kalman_prediction_against_analytic():
 k=locked();k.x=np.array([1.,2.,3.,4.]);k.P=np.eye(4);k.q=2.;k.t=5.
 k.predict(5.2)
 np.testing.assert_allclose(k.x,[1.6,2.8,3,4])
 assert k.P[0,0]==pytest.approx(1+.04+2*.2**4/4)
 assert k.P[0,2]==pytest.approx(.2+2*.2**3/2)

def test_kalman_update_scalar_closed_form():
 k=KalmanTracker(q=1,r=9,confirm=1)
 k.update(1,0,'x',640,480,[det(100,100)],1)
 k.update(1.1,1,'x',640,480,[det(102,100)],1.1)
 prior=9+400*.1**2+1*.1**4/4
 assert k.x[0]==pytest.approx(100+prior/(prior+9)*2)
@pytest.mark.parametrize('e',[0.,1.,-1.,10.,-10.])
def test_pid_proportional(e):
 p=PID(PIDConfig(kp=2,limit=100,slew=10000));u,_=p.step(e,.1);assert u==pytest.approx(2*e)
@pytest.mark.parametrize('e,dt',[(math.nan,.1),(math.inf,.1),(1.,0.),(1.,-.1),(1.,2.),(1.,math.nan)])
def test_pid_invalid_resets(e,dt):
 p=PID(PIDConfig(kp=1,ki=1,limit=2,slew=10));p.step(1,.1);assert p.step(e,dt)==(0.,False);assert p.integral==0

def test_pid_derivative():
 p=PID(PIDConfig(kd=1,limit=100,slew=10000,derivative_tau=.1));p.step(0,.1)
 u,_=p.step(1,.1);assert u==pytest.approx(5.)

def test_pid_windup_slew_reset():
 p=PID(PIDConfig(kp=1,ki=1,limit=1,slew=1))
 for _ in range(100):u,sat=p.step(100,.1)
 assert abs(u)<=1;assert p.integral==0;p.reset();assert p.output==0
 assert p.step(1,.1,enabled=False)==(0.,False)

def config():return yaml.safe_load((ROOT/'config/mock_shadow.yaml').read_text())
def test_optical_flu():
 c=config()['camera'];np.testing.assert_allclose(pixel_ray(320,240,c,640,480),[1,0,0])
 assert pixel_ray(400,240,c,640,480)[1]<0;assert pixel_ray(320,100,c,640,480)[2]>0

def test_attitude_stabilized_bearing():
 c=config()['camera'];q=[0,0,math.sin(math.pi/4),math.cos(math.pi/4)]
 az,el,_=bearing(320,240,c,640,480,q);assert az==pytest.approx(math.pi/2);assert el==pytest.approx(0)

def test_uncalibrated_rejected():
 c=config()['camera'];c['calibrated']=False
 with pytest.raises(ValueError):pixel_ray(320,240,c,640,480)

def setup_guidance(u=320,v=240):
 c=config();g=Guidance(c);k=locked();s=k.snapshot(1.2);s['x'][0:2]=u,v;s['dimensions']=(640,480)
 a=dict(connected=True,position_valid=True,attitude_valid=True,velocity_valid=True,airspeed_valid=True,position=[0.,0.,30.],velocity=[15.,0.,0.],q=[0,0,0,1],airspeed=15.)
 return g,s,a
@pytest.mark.parametrize('u,sign',[(200,1),(440,-1),(320,0)])
def test_left_right(u,sign):
 g,s,a=setup_guidance(u);o=g.compute(s,a,.05,True);assert o['valid']
 assert np.sign(o['course_rate'])==sign;assert np.sign(o['bank'])==-sign
@pytest.mark.parametrize('v,sign',[(100,1),(400,-1),(240,0)])
def test_above_below(v,sign):
 g,s,a=setup_guidance(v=v);o=g.compute(s,a,.05,True);assert np.sign(o['gamma'])==sign
@pytest.mark.parametrize('field',['connected','position_valid','attitude_valid','velocity_valid','airspeed_valid'])
def test_invalid_aircraft(field):
 g,s,a=setup_guidance();a[field]=False;assert not g.compute(s,a,.05,True)['valid']
@pytest.mark.parametrize('speed',[9.,15.,25.])
def test_speed_bank_limit(speed):
 g,s,a=setup_guidance(500);a['velocity']=[speed,0,0];a['airspeed']=speed
 for _ in range(50):o=g.compute(s,a,.05,True)
 assert abs(o['bank'])<=g.c['bank_limit_rad']+1e-9

def test_target_loss_resets_controller():
 g,s,a=setup_guidance(440);assert g.compute(s,a,.05,True)['valid'];s['valid']=False
 assert not g.compute(s,a,.05,True)['valid'];assert g.lat.output==0

def test_net_geometry_requires_plane():
 v=net_intersection([0,0,0],[1,0,0],[10,0,0],[1,0,0],1,1,[0,1,0],[0,0,1]);assert v['inside']
 np.testing.assert_allclose(v['point'],[10,0,0])
def test_unreviewed_permit_denies():
 with pytest.raises(ValueError):validate_permit(__import__('json').loads((ROOT/'config/sitl_permit.example.json').read_text()))
def test_yolo_missing_model():
 from alatus_vision.yolo import Yolo
 with pytest.raises(ValueError,match='MODEL_FILE_NOT_PROVIDED'):Yolo('',0)

def test_duplicate_capture_timestamp():
 k=locked();assert not k.update(1.2,10,'test',640,480,[det()],1.2)
def test_noise_filter_reduces_measurement_rmse():
 rng=np.random.default_rng(7);k=KalmanTracker(q=.1,r=16.,gate=100.)
 raw=[];filtered=[]
 for i in range(200):
  z=320+rng.normal(0,4);t=1+i*.05;k.update(t,i,'a',640,480,[det(z)],t)
  if i>20:raw.append(z-320);filtered.append(k.x[0]-320)
 assert np.mean(np.square(filtered))<np.mean(np.square(raw))
def test_source_change_reconfirms():
 k=locked();k.update(2,0,'other',640,480,[det()],2);assert not k.snapshot(2)['valid']
def test_prediction_age_does_not_refresh_observation():
 k=locked();assert k.snapshot(1.3)['stamp']==pytest.approx(1.2)
def authority_fixture():
 p=dict(minimum_airspeed_m_s=10.,minimum_altitude_enu_m=10.,maximum_altitude_enu_m=100.,maximum_bank_rad=.5,maximum_pitch_rad=.3,maximum_target_distance_m=100.)
 s=dict(stamp=1.,source='MAVROS',connected=True,armed=True,position_valid=True,attitude_valid=True,velocity_valid=True,airspeed_valid=True,failsafe=False,manual_override_active=False,mode='OFFBOARD',position=[0.,0.,30.],q=[0,0,0,1],airspeed=15.)
 c=dict(stamp=1.,observation_stamp=1.,valid=True,target=[40.,0.,30.])
 return p,s,c
@pytest.mark.parametrize('field',['connected','armed','position_valid','attitude_valid','velocity_valid','airspeed_valid'])
def test_authority_invalid_flags(field):
 p,s,c=authority_fixture();s[field]=False;assert not eligible(p,s,c,True,'TRACK_SHADOW',1.,0.)[0]
@pytest.mark.parametrize('mode',['MANUAL','AUTO.RTL','AUTO.MISSION',''])
def test_manual_or_mode_change(mode):
 p,s,c=authority_fixture();s['mode']=mode;assert not eligible(p,s,c,True,'TRACK_SHADOW',1.,0.)[0]
def test_authority_positive_and_stale():
 p,s,c=authority_fixture();assert eligible(p,s,c,True,'TRACK_SHADOW',1.,0.)[0]
 assert not eligible(p,s,c,True,'TRACK_SHADOW',1.3,0.)[0]
 assert not eligible(p,s,c,True,'TRACK_SHADOW',1.,1.)[0]
def test_authority_target_lost():
 p,s,c=authority_fixture();assert not eligible(p,s,c,False,'TRACK_SHADOW',1.,0.)[0]
def test_authority_no_stall_or_altitude_escape():
 p,s,c=authority_fixture();s['airspeed']=2.;assert not eligible(p,s,c,True,'TRACK_SHADOW',1.,0.)[0]
 p,s,c=authority_fixture();c['target'][2]=1000.;assert not eligible(p,s,c,True,'TRACK_SHADOW',1.,0.)[0]

def test_pure_pipeline_acquire_loss_abort_reset():
 from alatus_runtime.core import Mission
 m=Mission();m.request(True);k=KalmanTracker();g=Guidance(config());last=None
 state=dict(connected=True,position_valid=True,attitude_valid=True,velocity_valid=True,airspeed_valid=True,position=[0,0,30],velocity=[15,0,0],q=[0,0,0,1],airspeed=15.)
 for i in range(20):
  t=1+i*.05;k.update(t,i,'synthetic',640,480,[det(350)],t);snap=k.snapshot(t)
  if snap:snap['dimensions']=(640,480)
  ms=m.step(bool(snap and snap['valid']),True)
  last=g.compute(snap,state,.05,ms=='TRACK_SHADOW')
 assert last['valid'] and m.state=='TRACK_SHADOW'
 snap=k.snapshot(2.3)
 m.step(bool(snap and snap['valid']),True)
 out=g.compute(snap,state,.05,m.state=='TRACK_SHADOW')
 assert m.state=='ABORT' and not out['valid'] and g.lat.output==0
 assert not m.request(True);assert m.request(False);assert m.request(True)

def test_configuration_unreviewed_and_reviewed_invalid():
 from alatus_vision.configuration import validate
 c=config();validate(c)
 c['controller_reviewed']=True;c['lookahead_m']=0
 with pytest.raises(ValueError):validate(c)
