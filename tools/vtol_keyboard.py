"""Arrow-key control of the simulated PX4 VTOL using Gazebo Transport.

The inner controller is Gazebo MulticopterVelocityControl. This module provides
an altitude outer loop and a keyboard UI; it does not issue PX4/MAVLink commands.
"""
from dataclasses import dataclass
import math
import threading
import time

from gz.transport13 import Node
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.cameratrack_pb2 import CameraTrack
from gz.msgs10.odometry_pb2 import Odometry
from gz.msgs10.twist_pb2 import Twist
from gz.msgs10.world_control_pb2 import WorldControl

MODEL = 'keyboard_vtol'
WORLD = 'inha_songdo_vtol'


def clamp(value, limit):
    return max(-limit, min(limit, value))


@dataclass(frozen=True)
class FlightState:
    received: float
    sim_time: float
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float


class FlightControl:
    def __init__(self, takeoff_height=8.0):
        self.node = Node()
        self.twist = self.node.advertise(f'/{MODEL}/cmd_vel', Twist)
        self.enable = self.node.advertise(f'/{MODEL}/enable', Boolean)
        self.camera_track = self.node.advertise('/gui/track', CameraTrack)
        self.lock = threading.RLock()
        self.state = None
        self.target_z = takeoff_height
        self.mode = 'TAKEOFF'
        self.enabled = True
        self.input = (0.0, 0.0, 0.0, 0.0)
        self.input_received = 0.0
        self.last_error = ''
        self.last_command = (0.0, 0.0, 0.0, 0.0)
        self.alive = True
        self.node.subscribe(Odometry, f'/{MODEL}/odometry', self.odometry)
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def odometry(self, msg):
        p, q = msg.pose.position, msg.pose.orientation
        roll = math.atan2(2 * (q.w * q.x + q.y * q.z), 1 - 2 * (q.x*q.x + q.y*q.y))
        pitch = math.asin(max(-1, min(1, 2 * (q.w*q.y - q.z*q.x))))
        yaw = math.atan2(2 * (q.w*q.z + q.x*q.y), 1 - 2 * (q.y*q.y + q.z*q.z))
        stamp = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        values = (p.x, p.y, p.z, roll, pitch, yaw, stamp)
        if not all(math.isfinite(x) for x in values):
            return
        with self.lock:
            self.state = FlightState(time.monotonic(), stamp, p.x, p.y, p.z, roll, pitch, yaw)

    def snapshot(self):
        with self.lock:
            return self.state

    def set_input(self, x=0.0, y=0.0, z=0.0, yaw=0.0):
        with self.lock:
            self.input = (clamp(x, 12), clamp(y, 12), clamp(z, 2), clamp(yaw, 0.6))
            self.input_received = time.monotonic()

    def hover(self):
        with self.lock:
            if self.state:
                self.target_z = max(0.25, self.state.z)
            self.input = (0.0, 0.0, 0.0, 0.0)
            self.mode = 'HOVER'

    def takeoff(self):
        with self.lock:
            self.target_z = max(8.0, self.state.z if self.state else 0.0)
            self.mode = 'TAKEOFF'
            self.enabled = True

    def land(self):
        with self.lock:
            self.input = (0.0, 0.0, 0.0, 0.0)
            self.target_z = 0.10
            self.mode = 'LANDING'

    def resume_world(self):
        request = WorldControl()
        request.pause = False
        result, reply = self.node.request(f'/world/{WORLD}/control', request,
                                          WorldControl, Boolean, 1000)
        return bool(result and reply.data)

    def follow(self):
        # FOLLOW uses the aircraft's local frame. Zero lateral offset keeps the
        # camera directly aft even after a heading change. Unit gains eliminate
        # the diagonal lag of a smoothed chase camera during turns.
        request = CameraTrack(track_mode=CameraTrack.FOLLOW)
        request.follow_target.name = MODEL
        request.follow_offset.x = -8.0
        request.follow_offset.y = 0.0
        request.follow_offset.z = 1.0
        request.follow_pgain = 1.0
        request.track_pgain = 1.0
        if not self.camera_track.has_connections():
            return False
        self.camera_track.publish(request)
        return True

    def loop(self):
        last_sim_time = None
        while self.alive:
            now = time.monotonic()
            with self.lock:
                state = self.state
                # UI heartbeat stops planar input if the window/event loop stalls.
                x, y, z, yaw = self.input if now - self.input_received < 0.3 else (0, 0, 0, 0)
                fresh = state is not None and now - state.received < 1.0
                # Integrate altitude requests using simulation time, not wall time.
                dt = 0.0
                if fresh and last_sim_time is not None:
                    dt = max(0.0, min(0.1, state.sim_time - last_sim_time))
                if fresh:
                    last_sim_time = state.sim_time
                    if self.mode == 'LANDING':
                        x = y = yaw = 0.0
                        z = 0.0
                        if state.z < 0.18:
                            self.enabled = False
                            self.mode = 'LANDED'
                    elif self.enabled:
                        self.target_z = max(0.25, min(250, self.target_z + z * dt))
                    vz = clamp(1.2 * (self.target_z - state.z), 1.8)
                    if self.mode == 'LANDING':
                        vz = max(-0.8, vz)
                    if self.mode == 'TAKEOFF' and abs(self.target_z - state.z) < 0.3:
                        self.mode = 'HOVER'
                else:
                    x = y = yaw = vz = 0.0
                if not self.enabled:
                    x = y = yaw = vz = 0.0
                command = Twist()
                command.linear.x, command.linear.y, command.linear.z = float(x), float(y), float(vz)
                command.angular.z = float(yaw)
                enabled = self.enabled
                self.last_command = (x, y, vz, yaw)
            try:
                self.enable.publish(Boolean(data=enabled))
                self.twist.publish(command)
            except Exception as error:
                self.last_error = str(error)
            time.sleep(1 / 30)

    def close(self):
        self.alive = False
        self.thread.join(timeout=1)
        # Zero velocity keeps the rotor controller hovering until the launcher
        # terminates this simulation; it is not a motor-cut command in midair.
        for _ in range(3):
            self.twist.publish(Twist())
            time.sleep(0.03)


class KeyboardWindow:
    def __init__(self, control):
        import tkinter as tk
        from tkinter import ttk
        self.tk = tk
        self.control = control
        self.root = tk.Tk()
        self.root.title('VTOL Keyboard Controller')
        self.root.geometry('510x420')
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.pressed = set()
        self.pending_release = {}
        self.closed = False
        self.unpaused = False
        self.followed = False
        self.last_follow_attempt = 0.0
        self.started = time.monotonic()
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='PX4 STANDARD VTOL', font=('Sans', 16, 'bold')).pack(anchor='w')
        ttk.Label(outer, text='Gazebo hover flight  |  Keep this window focused').pack(anchor='w', pady=(2, 12))
        ttk.Label(outer, text='ARROWS: forward / back / left / right\nSHIFT + UP / DOWN: climb / descend\nSHIFT + LEFT / RIGHT: turn\nSPACE: hold current altitude and stop',
                  font=('Sans', 11), justify='left').pack(anchor='w')
        self.status = tk.StringVar(value='Connecting to simulation...')
        ttk.Label(outer, textvariable=self.status, font=('Monospace', 10), justify='left').pack(anchor='w', pady=14)
        row = ttk.Frame(outer)
        row.pack(fill='x')
        ttk.Button(row, text='Take off (8m)', command=self.takeoff).pack(side='left')
        ttk.Button(row, text='Hold / Space', command=self.hold).pack(side='left', padx=6)
        ttk.Button(row, text='Land', command=self.land).pack(side='left')
        ttk.Button(row, text='Rear camera', command=self.follow).pack(side='left', padx=6)
        self.speed = tk.DoubleVar(value=4.0)
        ttk.Label(outer, text='Horizontal speed (m/s)').pack(anchor='w', pady=(12, 0))
        ttk.Scale(outer, from_=1, to=10, variable=self.speed, takefocus=False).pack(fill='x')
        ttk.Label(outer, text='Release keys or switch windows to stop horizontal movement.\nAuto takeoff to 8m; vertical rotors remain active to hover.',
                  justify='left').pack(anchor='w', pady=(10, 0))
        self.root.bind('<KeyPress>', self.key_down)
        self.root.bind('<KeyRelease>', self.key_up)
        self.root.bind('<FocusOut>', self.focus_out)
        self.root.bind('<Unmap>', lambda _: self.clear())
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.after(100, self.tick)
        self.root.after(200, self.root.focus_force)

    def key_down(self, event):
        key = event.keysym
        if key in self.pending_release:
            self.root.after_cancel(self.pending_release.pop(key))
        if key in {'Up', 'Down', 'Left', 'Right', 'Shift_L', 'Shift_R'}:
            self.pressed.add(key)
            return 'break'
        if key == 'space':
            self.hold()
            return 'break'
        if key == 'Escape':
            self.close()
            return 'break'

    def key_up(self, event):
        key = event.keysym
        if key not in self.pressed:
            return
        def release():
            self.pending_release.pop(key, None)
            self.pressed.discard(key)
        # X11 auto-repeat can emit synthetic release/press pairs.
        if key in self.pending_release:
            self.root.after_cancel(self.pending_release[key])
        self.pending_release[key] = self.root.after(35, release)
        return 'break'

    def focus_out(self, _):
        self.root.after(30, lambda: self.clear() if self.root.focus_displayof() is None else None)

    def clear(self):
        self.pressed.clear()
        self.control.set_input()

    def hold(self):
        self.clear()
        self.control.hover()

    def takeoff(self):
        self.clear()
        self.control.takeoff()

    def land(self):
        self.clear()
        self.control.land()

    def follow(self):
        self.followed = self.control.follow()

    def tick(self):
        if self.closed:
            return
        state = self.control.snapshot()
        # During a large collision-mesh load the service may acknowledge an
        # unpause before the first physics update. Retry until odometry proves
        # startup completed; respect manual pause after the first observation.
        if not self.unpaused or state is None:
            self.unpaused = self.control.resume_world()
        now = time.monotonic()
        if state and now - self.started < 15 and now - self.last_follow_attempt > 1:
            self.last_follow_attempt = now
            self.followed = self.control.follow()
        up = int('Up' in self.pressed) - int('Down' in self.pressed)
        left = int('Left' in self.pressed) - int('Right' in self.pressed)
        shifted = bool({'Shift_L', 'Shift_R'} & self.pressed)
        if shifted:
            self.control.set_input(z=up * 1.5, yaw=left * 0.5)
        else:
            # Normalize diagonals so their magnitude matches the speed slider.
            scale = self.speed.get() / max(1.0, math.hypot(up, left))
            self.control.set_input(x=up * scale, y=left * scale)
        if state:
            with self.control.lock:
                target, mode, command = self.control.target_z, self.control.mode, self.control.last_command
            self.status.set(f'{mode}  |  Alt {state.z:6.2f}m  -> {target:5.1f}m\n'
                            f'X {state.x:7.1f}m  Y {state.y:7.1f}m\n'
                            f'CMD forward {command[0]:+.1f}  left {command[1]:+.1f} m/s')
        else:
            self.status.set('Waiting for VTOL odometry...\n' + self.control.last_error)
        self.root.after(50, self.tick)

    def close(self):
        self.closed = True
        self.clear()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
