"""Evaluate matched actual replay/GT centers; no synthetic performance defaults."""
import argparse,csv,json,math
p=argparse.ArgumentParser();p.add_argument('--track',required=True);p.add_argument('--truth',required=True);a=p.parse_args()
# truth columns: frame,u_px,v_px. Only explicit GT entries are evaluated.
with open(a.truth) as f:gt={int(x['frame']):(float(x['u_px']),float(x['v_px'])) for x in csv.DictReader(f)}
err=[];age=[];valid=0;matched=0
with open(a.track) as f:
 for x in csv.DictReader(f):
  frame=int(x['frame'])
  if frame not in gt:continue
  matched+=1
  if x['valid'].lower() not in ['true','1'] or not x['u_px']:continue
  u,v=float(x['u_px']),float(x['v_px']);u0,v0=gt[frame]
  if not all(math.isfinite(z) for z in (u,v,u0,v0)):continue
  valid+=1;err.append((u-u0)**2+(v-v0)**2)
if not err:raise SystemExit('No valid matched labelled frames; cannot report RMSE')
print(json.dumps({'rmse_2d_px':math.sqrt(sum(err)/len(err)),'valid_labelled_frames':valid,'all_labelled_frames_matched':matched,'valid_fraction':valid/matched},indent=2))
