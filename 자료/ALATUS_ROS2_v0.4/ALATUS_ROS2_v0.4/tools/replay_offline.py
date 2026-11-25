"""Actual video -> YOLO -> KF with CSV, overlay and original video timeline. No ROS/PX4."""
import argparse,csv,time
from pathlib import Path
import cv2
from alatus_vision.yolo import Yolo
from alatus_vision.tracking import KalmanTracker,Detection
p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--video',required=True);p.add_argument('--class-id',type=int,required=True);p.add_argument('--output',required=True);p.add_argument('--show',action='store_true');p.add_argument('--imgsz',type=int,default=640);a=p.parse_args()
if not Path(a.video).is_file():raise SystemExit('Video file missing')
m=Yolo(a.model,a.class_id,imgsz=a.imgsz);k=KalmanTracker(class_id=a.class_id)
v=cv2.VideoCapture(a.video);fps=v.get(cv2.CAP_PROP_FPS)
if not v.isOpened() or not 0<fps<1000:raise SystemExit('Cannot open video/FPS invalid')
with open(a.output,'w',newline='') as f:
 w=csv.writer(f);w.writerow(['frame','video_time_s','inference_s','u_px','v_px','valid','prediction_age_s','variance_u','variance_v'])
 i=0
 while True:
  ok,img=v.read()
  if not ok:break
  t=1+i/fps;start=time.perf_counter();raw=m.detect(img);elapsed=time.perf_counter()-start
  k.update(t,i,'offline',img.shape[1],img.shape[0],[Detection(c,s,xy) for c,s,xy in raw],t);s=k.snapshot(t)
  w.writerow([i,t-1,elapsed,*([float(s['x'][0]),float(s['x'][1]),s['valid'],s['age'],float(s['P'][0,0]),float(s['P'][1,1])] if s else ['', '',False,'','',''])])
  if a.show:
   if s:cv2.circle(img,tuple(map(int,s['x'][:2])),6,(0,255,0),2)
   cv2.imshow('YOLO/KF replay',img)
   if cv2.waitKey(1)==27:break
  i+=1
v.release();cv2.destroyAllWindows();print('Frames processed:',i,'Output:',a.output,'No flight commands sent')
