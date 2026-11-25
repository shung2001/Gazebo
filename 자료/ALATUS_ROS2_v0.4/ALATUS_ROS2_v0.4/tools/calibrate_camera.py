"""Offline OpenCV calibration from real checkerboard images; no default measurements."""
import argparse,glob,json
import cv2,numpy as np,yaml
p=argparse.ArgumentParser();p.add_argument('--images',required=True);p.add_argument('--cols',type=int,required=True);p.add_argument('--rows',type=int,required=True);p.add_argument('--square-m',type=float,required=True);p.add_argument('--output',required=True);a=p.parse_args()
if min(a.cols,a.rows)<3 or a.square_m<=0:raise SystemExit('Invalid checkerboard geometry')
obj=np.zeros((a.cols*a.rows,3),np.float32);obj[:,:2]=np.mgrid[0:a.cols,0:a.rows].T.reshape(-1,2)*a.square_m
objects=[];points=[];size=None
for f in sorted(glob.glob(a.images)):
 im=cv2.imread(f)
 if im is None:continue
 gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY);dims=(gray.shape[1],gray.shape[0])
 if size is not None and size!=dims:raise SystemExit('Mixed image resolution')
 size=dims;ok,corners=cv2.findChessboardCorners(gray,(a.cols,a.rows))
 if ok:
  corners=cv2.cornerSubPix(gray,corners,(11,11),(-1,-1),(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_MAX_ITER,40,.001))
  objects.append(obj.copy());points.append(corners)
if len(points)<12:raise SystemExit('Need at least 12 detected real checkerboard views; collect diverse views')
rms,K,D,rv,tv=cv2.calibrateCamera(objects,points,size,None,None)
result=dict(calibrated=True,fx=float(K[0,0]),fy=float(K[1,1]),cx=float(K[0,2]),cy=float(K[1,2]),resolution=list(size),distortion_model='plumb_bob',distortion=list(map(float,D.ravel())),reprojection_rms_px=float(rms),views=len(points),optical_to_body_flu=None,position_body_flu_m=None)
with open(a.output,'w') as f:yaml.safe_dump(result,f,sort_keys=False)
print(json.dumps({'views':len(points),'rms_px':rms,'output':a.output,'extrinsics':'TBD; measure mounting separately'}))
