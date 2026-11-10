"""Autonomous VTOL target approach with a 3200 px Gazebo camera and YOLO UI."""
import argparse
from collections import deque
import csv
from datetime import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_target_detection_scene import (ALTITUDE, CAMERA_PITCH, CAMERA_SIZE,
                                          CAMERA_TOPIC, CAMERA_X, FORWARD,
                                          HORIZONTAL_RANGE, OUTWARD, START,
                                          START_RANGE, START_YAW, TARGET,
                                          WALL_YAW, build)


def clamp(value, limit):
    return max(-limit, min(limit, value))


def rotate(q, v):
    """Rotate a vector using a w,x,y,z unit quaternion."""
    w, x, y, z = q
    vx, vy, vz = v
    tx, ty, tz = 2*(y*vz-z*vy), 2*(z*vx-x*vz), 2*(x*vy-y*vx)
    return (vx+w*tx+y*tz-z*ty, vy+w*ty+z*tx-x*tz,
            vz+w*tz+x*ty-y*tx)


def multiply(a, b):
    aw,ax,ay,az = a
    bw,bx,by,bz = b
    return (aw*bw-ax*bx-ay*by-az*bz,
            aw*bx+ax*bw+ay*bz-az*by,
            aw*by-ax*bz+ay*bw+az*bx,
            aw*bz+ax*by-ay*bx+az*bw)


def camera_position(state):
    offset = rotate(state['q'], (CAMERA_X,0,0))
    return tuple(state['position'][i]+offset[i] for i in range(3))


def range_to_target(state):
    return math.dist(camera_position(state), TARGET)


def target_box(state):
    """Project four known 2 x 2 m target corners into the camera image."""
    camera = camera_position(state)
    tilt = (math.cos(CAMERA_PITCH/2),0,math.sin(CAMERA_PITCH/2),0)
    q = multiply(state['q'], tilt)
    inverse = (q[0], -q[1], -q[2], -q[3])
    focal = CAMERA_SIZE / (2*math.tan(math.pi/6))
    points = []
    for horizontal in (-1, 1):
        for dz in (-1, 1):
            world = (TARGET[0]+horizontal*math.cos(WALL_YAW),
                     TARGET[1]+horizontal*math.sin(WALL_YAW),TARGET[2]+dz)
            local = rotate(inverse, tuple(world[i]-camera[i] for i in range(3)))
            if local[0] <= 0.1:
                return None
            points.append((CAMERA_SIZE/2-focal*local[1]/local[0],
                           CAMERA_SIZE/2-focal*local[2]/local[0]))
    return (min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points))


def target_match(box, expected):
    if expected is None:
        return False
    x1, y1, x2, y2 = box
    a, b, c, d = expected
    intersection = max(0, min(x2,c)-max(x1,a))*max(0,min(y2,d)-max(y1,b))
    gt_area = max(1,(c-a)*(d-b))
    pred_area = max(1,(x2-x1)*(y2-y1))
    return intersection/gt_area >= 0.25 and pred_area <= 12*gt_area


class Mission:
    def __init__(self, model_path, confidence):
        import numpy as np
        from PIL import Image as PILImage
        from ultralytics import YOLO
        from gz.transport13 import Node
        from gz.msgs10.boolean_pb2 import Boolean
        from gz.msgs10.image_pb2 import Image
        from gz.msgs10.odometry_pb2 import Odometry
        from gz.msgs10.twist_pb2 import Twist
        from gz.msgs10.world_control_pb2 import WorldControl
        self.np, self.PILImage = np, PILImage
        self.Boolean, self.Twist, self.WorldControl = Boolean, Twist, WorldControl
        self.model = YOLO(str(model_path))
        target_classes = {name for name in self.model.names.values()
                          if name.strip().lower().replace('_', ' ') == 'target board'}
        if not target_classes:
            raise ValueError(f'{model_path} has no target board class: {self.model.names}')
        self.target_classes = target_classes
        self.device = 0 if __import__('torch').cuda.is_available() else 'cpu'
        print(f'YOLO device: {self.device}; camera: {CAMERA_SIZE} x {CAMERA_SIZE}', flush=True)
        self.confidence = confidence
        self.node = Node()
        self.cmd = self.node.advertise('/keyboard_vtol/cmd_vel', Twist)
        self.enable = self.node.advertise('/keyboard_vtol/enable', Boolean)
        self.states = deque(maxlen=300)
        self.state_lock = threading.Lock()
        self.frames = queue.Queue(maxsize=1)
        self.outputs = queue.Queue(maxsize=1)
        self.first = None
        self.latest = None
        self.frame_count = 0
        self.reached_at = None
        self.seconds = {}
        self.seconds_lock = threading.Lock()
        self.running = True
        self.started = time.monotonic()
        self.node.subscribe(Odometry, '/keyboard_vtol/odometry', self.on_odom)
        self.node.subscribe(Image, CAMERA_TOPIC, self.on_image)
        self.control_thread = threading.Thread(target=self.control_loop, daemon=True)
        self.infer_thread = threading.Thread(target=self.infer_loop, daemon=True)
        self.control_thread.start()
        self.infer_thread.start()

    def on_odom(self, msg):
        p, q = msg.pose.position, msg.pose.orientation
        state = {'stamp': msg.header.stamp.sec + msg.header.stamp.nsec*1e-9,
                 'position': (p.x,p.y,p.z), 'q': (q.w,q.x,q.y,q.z)}
        if not all(math.isfinite(v) for v in (*state['position'],*state['q'])):
            return
        with self.state_lock:
            self.states.append(state)
        second = int(state['stamp'])
        with self.seconds_lock:
            row = self.seconds.setdefault(second,{})
            row.update({'sim_second':second,'sim_time_s':round(state['stamp'],3),
                        'x_m':round(p.x,3),'y_m':round(p.y,3),
                        'altitude_m':round(p.z,3),
                        'range_m':round(range_to_target(state),3),
                        'yaw_rad':round(math.atan2(2*(q.w*q.z+q.x*q.y),
                                                   1-2*(q.y*q.y+q.z*q.z)),4)})

    def on_image(self, msg):
        if msg.width != CAMERA_SIZE or msg.height != CAMERA_SIZE:
            return
        # Gazebo RGB_INT8 has three bytes per pixel. Process one frame at a time.
        if msg.step != CAMERA_SIZE*3 or len(msg.data) != CAMERA_SIZE*CAMERA_SIZE*3:
            return
        stamp = msg.header.stamp.sec + msg.header.stamp.nsec*1e-9
        with self.state_lock:
            state = min(self.states, key=lambda s: abs(s['stamp']-stamp)) if self.states else None
        if state is None:
            return
        while self.frames.full():
            try: self.frames.get_nowait()
            except queue.Empty: break
        try: self.frames.put_nowait((bytes(msg.data), state))
        except queue.Full: pass

    def control_loop(self):
        while self.running:
            with self.state_lock:
                state = self.states[-1] if self.states else None
            twist = self.Twist()
            if state:
                x,y,z = state['position']
                camera = camera_position(state)
                remaining = ((TARGET[0]-camera[0])*FORWARD[0]
                             +(TARGET[1]-camera[1])*FORWARD[1])
                progress = clamp(HORIZONTAL_RANGE-remaining,HORIZONTAL_RANGE)
                desired_z = ALTITUDE-(ALTITUDE-TARGET[2])*max(0,progress)/HORIZONTAL_RANGE
                distance = range_to_target(state)
                # The multicopter descends much more slowly than it travels
                # horizontally. Wait for altitude to catch up so the camera
                # and aircraft stay on the same straight 3D approach line.
                advancing = remaining > 18*math.cos(CAMERA_PITCH)
                on_line = z-desired_z < 1.0
                twist.linear.x = float(min(4.0,max(0.0,remaining-18*math.cos(CAMERA_PITCH)))
                                       if advancing and on_line else 0.0)
                lateral = ((x-START[0])*(-FORWARD[1])
                           +(y-START[1])*FORWARD[0])
                twist.linear.y = float(clamp(-1.0*lateral,2.0))
                descent = -2.8 if advancing else 0.0
                twist.linear.z = float(clamp(descent+1.2*(desired_z-z),3.0))
                if distance <= 15 and self.reached_at is None:
                    self.reached_at = time.monotonic()
                q = state['q']
                yaw = math.atan2(2*(q[0]*q[3]+q[1]*q[2]),
                                 1-2*(q[2]*q[2]+q[3]*q[3]))
                yaw_error = math.atan2(math.sin(START_YAW-yaw),
                                       math.cos(START_YAW-yaw))
                twist.angular.z = float(clamp(1.2*yaw_error,0.5))
            self.enable.publish(self.Boolean(data=True))
            self.cmd.publish(twist)
            time.sleep(1/30)

    def resume(self):
        request = self.WorldControl()
        request.pause = False
        for _ in range(20):
            result, reply = self.node.request('/world/target_detection/control', request,
                                              self.WorldControl, self.Boolean, 1000)
            if result and reply.data:
                return True
            time.sleep(0.5)
        return False

    def infer_loop(self):
        from PIL import ImageDraw, ImageFont
        while self.running:
            try: data, state = self.frames.get(timeout=0.3)
            except queue.Empty: continue
            image = self.PILImage.frombytes('RGB', (CAMERA_SIZE,CAMERA_SIZE), data)
            start = (CAMERA_SIZE-1280)//2
            crop = image.crop((start,start,start+1280,start+1280))
            result = self.model.predict(self.np.asarray(crop), imgsz=1280,
                                        conf=self.confidence, device=self.device,
                                        verbose=False)[0]
            expected = target_box(state)
            distance = range_to_target(state)
            detections = []
            for box, cls, conf in zip(result.boxes.xyxy.tolist(),
                                      result.boxes.cls.tolist(),
                                      result.boxes.conf.tolist()):
                full_box = tuple(v+start for v in box)
                detections.append({'box':full_box, 'class':self.model.names[int(cls)],
                                   'confidence':float(conf),
                                   'target_overlap':self.model.names[int(cls)] in self.target_classes
                                   and target_match(full_box,expected)})
            matched = [d for d in detections if d['target_overlap']]
            best = max(matched,key=lambda d:d['confidence']) if matched else None
            with self.seconds_lock:
                row = self.seconds.setdefault(int(state['stamp']),
                                              {'sim_second':int(state['stamp'])})
                row['camera_frames'] = row.get('camera_frames',0)+1
                row['yolo_boxes'] = row.get('yolo_boxes',0)+len(detections)
                row['target_detected'] = int(bool(best) or row.get('target_detected',0))
                if best and best['confidence'] > float(row.get('target_confidence') or 0):
                    row['target_confidence'] = round(best['confidence'],4)
                    row['target_box_xyxy'] = json.dumps([round(v,1) for v in best['box']])
                    row['camera_range_m'] = round(distance,3)
            if matched and self.first is None:
                self.first = {'distance_m':round(distance,2),
                              'sim_time_s':round(state['stamp'],3),
                              'class':best['class'],
                              'confidence':round(best['confidence'],4)}
                print('FIRST TARGET-OVERLAPPING YOLO BOX:',self.first,flush=True)
            self.frame_count += 1
            preview = image.resize((800,800))
            draw = ImageDraw.Draw(preview)
            scale = 800/CAMERA_SIZE
            if expected:
                draw.rectangle(tuple(v*scale for v in expected),outline='#00e5ff',width=2)
            for d in detections:
                coords = tuple(v*scale for v in d['box'])
                color = '#20e040' if d['target_overlap'] else '#ffd040'
                draw.rectangle(coords,outline=color,width=3)
                label = f"{d['class']} {d['confidence']:.2f}"
                draw.text((coords[0],max(0,coords[1]-18)),label,fill=color,
                          stroke_width=2,stroke_fill='black')
            if matched and self.first and self.first['sim_time_s'] == round(state['stamp'],3):
                preview.save(ROOT/'logs'/'target_detection_first.png')
            self.latest = {'distance_m':round(distance,2),
                           'sim_time_s':round(state['stamp'],3),
                           'position_m':tuple(round(v,2) for v in state['position']),
                           'detections':detections,'first_detection':self.first,
                           'frames_processed':self.frame_count}
            while self.outputs.full():
                try: self.outputs.get_nowait()
                except queue.Empty: break
            self.outputs.put((preview,self.latest))

    def close(self):
        self.running = False
        self.control_thread.join(timeout=1)
        self.infer_thread.join(timeout=1)

    def save_csv(self, path):
        fields = ['sim_second','sim_time_s','x_m','y_m','altitude_m','range_m',
                  'yaw_rad','camera_frames','camera_range_m','yolo_boxes',
                  'target_detected','target_confidence','target_box_xyxy',
                  'first_detection_range_m']
        with self.seconds_lock:
            rows = [dict(self.seconds[second]) for second in sorted(self.seconds)]
        for row in rows:
            row.setdefault('camera_frames',0)
            row.setdefault('yolo_boxes',0)
            row.setdefault('target_detected',0)
            row['first_detection_range_m'] = (
                self.first['distance_m'] if self.first
                and row['sim_second'] >= int(self.first['sim_time_s']) else '')
        with path.open('w',newline='',encoding='utf-8-sig') as output:
            writer = csv.DictWriter(output,fieldnames=fields,extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless',action='store_true',help='run without Tk preview')
    parser.add_argument('--confidence',type=float,default=0.15)
    parser.add_argument('--model',type=Path,
                        default=ROOT/'YOLO11m_best.pt',
                        help='YOLO segmentation checkpoint with a target board class')
    parser.add_argument('--duration',type=float,default=180,
                        help='maximum wall clock seconds')
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise SystemExit('Run through Ubuntu WSL: wsl -d Ubuntu-22.04 -- bash /mnt/c/.../run_target_detection.sh')
    model = args.model.resolve()
    if not model.exists(): raise SystemExit(f'Missing model: {model}')
    world = build()
    os.environ.setdefault('GZ_PARTITION','target_detection')
    os.environ.setdefault('QT_QPA_PLATFORM','xcb')
    if shutil.which('nvidia-smi'):
        os.environ.setdefault('MESA_D3D12_DEFAULT_ADAPTER_NAME','NVIDIA')
    paths = [str(ROOT/'models'),str(ROOT/'vendor'/'px4-gazebo-models'/'models')]
    if os.environ.get('GZ_SIM_RESOURCE_PATH'): paths.append(os.environ['GZ_SIM_RESOURCE_PATH'])
    os.environ['GZ_SIM_RESOURCE_PATH'] = ':'.join(paths)
    logs = ROOT/'logs'
    logs.mkdir(exist_ok=True)
    results = ROOT/'result'
    results.mkdir(exist_ok=True)
    lock = open(f'/tmp/target_detection_{os.getuid()}.lock','a')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit('Target detection is already running')
    log_path = logs/'target_detection_gazebo.log'
    server = None
    mission = None
    stop = False
    def stop_signal(*_):
        nonlocal stop
        stop = True
    for number in (signal.SIGINT,signal.SIGTERM): signal.signal(number,stop_signal)
    try:
        with log_path.open('w') as log:
            print('Starting automatic target approach. Gazebo log:',log_path,flush=True)
            server = subprocess.Popen(['gz','sim','-s','-r','--headless-rendering',
                                       '-v','3',str(world)],stdout=log,
                                      stderr=subprocess.STDOUT,start_new_session=True)
            mission = Mission(model,args.confidence)
            if not mission.resume():
                raise RuntimeError('Gazebo world control service did not respond')
            if args.headless:
                while not stop and server.poll() is None and time.monotonic()-mission.started<args.duration:
                    latest = mission.latest
                    if mission.reached_at: break
                    time.sleep(0.5)
            else:
                import tkinter as tk
                from tkinter import ttk
                from PIL import ImageTk
                print('Opening target detection preview window...', flush=True)
                window = tk.Tk()
                window.title('VTOL YOLO11m target detection')
                photo_label = ttk.Label(window)
                photo_label.pack()
                status = tk.StringVar(value='Waiting for 3200 x 3200 camera frames...')
                ttk.Label(window,textvariable=status,font=('Arial',13),justify='left').pack(padx=12,pady=8)
                def update():
                    nonlocal stop
                    try:
                        preview,latest = mission.outputs.get_nowait()
                        photo = ImageTk.PhotoImage(preview)
                        photo_label.configure(image=photo)
                        photo_label.image = photo
                        first = latest['first_detection']
                        first_text = (f"{first['distance_m']:.2f} m, {first['class']} "
                                      f"{first['confidence']:.2f}") if first else 'None yet'
                        status.set(f"Range: {latest['distance_m']:.2f} m | "
                                   f"Altitude: {latest['position_m'][2]:.2f} m | "
                                   f"Frames: {latest['frames_processed']}\n"
                                   f"First target-overlapping YOLO box: {first_text}\n"
                                   'Cyan: projected 2 x 2 m target  |  Green: overlapping YOLO box  |  Yellow: other YOLO box')
                    except queue.Empty: pass
                    if stop or server.poll() is not None or time.monotonic()-mission.started>=args.duration:
                        if server.poll() is not None:
                            reason = f'Gazebo stopped (exit code {server.returncode}).'
                        elif stop:
                            reason = 'Stopped by signal.'
                        else:
                            reason = f'Time limit reached ({args.duration:g} s).'
                        print(reason, flush=True)
                        status.set(status.get() + '\n' + reason + ' Close this window to save results.')
                        mission.close()
                        if server.poll() is None:
                            os.killpg(server.pid, signal.SIGINT)
                    else: window.after(100,update)
                window.after(100,update)
                window.protocol('WM_DELETE_WINDOW',window.destroy)
                window.mainloop()
    finally:
        if mission:
            mission.close()
            report = mission.latest or {'frames_processed':0,'first_detection':None}
            report['first_detection'] = mission.first
            report['setup'] = {
                'model': model.name,
                'camera_resolution': [CAMERA_SIZE,CAMERA_SIZE],
                'inference_crop': [1280,1280],
                'initial_camera_target_distance_m': 100.0,
                'initial_altitude_m': ALTITUDE,
                'target_size_m': [2,2],
                'commanded_approach_speed_mps': 4.0,
                'confidence_threshold': args.confidence,
                'target_world_xyz_m': TARGET,
                'start_world_xyz_m': START,
                'camera_pitch_rad': CAMERA_PITCH,
            }
            csv_path = results/f"target_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            count = mission.save_csv(csv_path)
            report['csv_path'] = str(csv_path)
            report['seconds_recorded'] = count
            print(f'Second-by-second CSV ({count} rows):',csv_path,flush=True)
            (logs/'target_detection_result.json').write_text(
                json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print('Result:',logs/'target_detection_result.json',flush=True)
        if server and server.poll() is None:
            os.killpg(server.pid,signal.SIGINT)
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid,signal.SIGKILL)
                server.wait()
        lock.close()


if __name__ == '__main__': main()
