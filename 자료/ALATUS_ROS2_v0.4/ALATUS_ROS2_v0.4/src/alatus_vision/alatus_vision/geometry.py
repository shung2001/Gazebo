"""Optical x-right/y-down/z-forward -> body FLU -> world ENU."""
import math
import numpy as np

def rotation(q):
    q=np.asarray(q,float)
    if q.shape!=(4,) or not np.isfinite(q).all() or abs(np.linalg.norm(q)-1)>0.01:
        raise ValueError('Quaternion must be normalized xyzw')
    x,y,z,w=q/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def pixel_ray(u,v,camera,width,height):
    if not camera.get('calibrated',False): raise ValueError('CAMERA_CALIBRATION_TBD')
    fx,fy,cx,cy=[float(camera[k]) for k in ('fx','fy','cx','cy')]
    if not all(math.isfinite(v) for v in (u,v,fx,fy,cx,cy)) or min(fx,fy)<=0:raise ValueError('Invalid intrinsics')
    if [width,height]!=camera['resolution'] or not (0<=u<width and 0<=v<height):raise ValueError('Image dimensions/bounds')
    d=camera.get('distortion',[])
    if camera.get('distortion_model','plumb_bob')!='plumb_bob':raise ValueError('Unsupported distortion model')
    if d and any(d):
        import cv2
        xy=cv2.undistortPoints(np.array([[[u,v]]],dtype=float),np.array([[fx,0,cx],[0,fy,cy],[0,0,1]],float),np.array(d,float))[0,0]
        ray=np.r_[xy,1.]
    else:ray=np.array([(u-cx)/fx,(v-cy)/fy,1.])
    R=np.asarray(camera['optical_to_body_flu'],float)
    if R.shape!=(3,3) or not np.isfinite(R).all() or not np.allclose(R.T@R,np.eye(3),atol=1e-6) or not np.isclose(np.linalg.det(R),1):raise ValueError('Invalid extrinsic rotation')
    return R@ray/np.linalg.norm(ray)

def bearing(u,v,camera,width,height,q):
    body=pixel_ray(u,v,camera,width,height);world=rotation(q)@body
    return math.atan2(world[1],world[0]),math.atan2(world[2],math.hypot(world[0],world[1])),body

def wrap(x): return math.atan2(math.sin(x),math.cos(x))

def net_intersection(camera_position,ray_world,net_center,net_normal,half_width,half_height,right,up):
    """Requires surveyed geometry/range. Not inferred from one bounding box."""
    c,d,n,o,r,u=map(lambda a:np.asarray(a,float),(camera_position,ray_world,net_normal,net_center,right,up))
    if not all(np.isfinite(a).all() for a in (c,d,n,o,r,u)):raise ValueError('Nonfinite net geometry')
    if any(a.shape!=(3,) for a in (c,d,n,o,r,u)) or not (math.isfinite(half_width) and math.isfinite(half_height) and min(half_width,half_height)>0):raise ValueError('Invalid net dimensions')
    basis=np.column_stack((r,u,n))
    if not np.allclose(basis.T@basis,np.eye(3),atol=1e-6):raise ValueError('Net basis must be orthonormal')
    den=float(d@n)
    if abs(den)<1e-8:raise ValueError('Parallel ray')
    t=float((o-c)@n)/den
    if t<=0:raise ValueError('Intersection behind camera')
    x=c+t*d-o
    return dict(point=c+t*d,inside=abs(x@r)<=half_width and abs(x@u)<=half_height)
