"""Physical Gazebo acceptance: takeoff, hover, 4 directions, yaw, height, land."""
from pathlib import Path
import json
import math
import os
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
os.environ['GZ_PARTITION'] = f'inha_vtol_acceptance_{os.getpid()}'
os.environ['GZ_SIM_RESOURCE_PATH'] = ':'.join([
    str(ROOT / 'models'), str(ROOT / 'vendor' / 'px4-gazebo-models' / 'models')])
from vtol_keyboard import FlightControl


def main():
    logs = ROOT / 'logs'
    logs.mkdir(exist_ok=True)
    report = {'status': 'RUNNING', 'measurements': {}, 'partition': os.environ['GZ_PARTITION']}
    control = None
    server = None
    started = time.monotonic()

    def state():
        value = control.snapshot()
        if not value or time.monotonic() - value.received > 2:
            raise AssertionError('No fresh odometry')
        if not all(math.isfinite(v) for v in (value.x, value.y, value.z)):
            raise AssertionError('Nonfinite state')
        if abs(value.roll) > 0.8 or abs(value.pitch) > 0.8:
            raise AssertionError(f'Excessive attitude: {value}')
        return value

    def run(seconds, **inputs):
        first = state()
        deadline = time.monotonic() + max(20, seconds * 4)
        while state().sim_time - first.sim_time < seconds:
            if time.monotonic() > deadline:
                raise AssertionError('Simulation did not advance in time')
            control.set_input(**inputs)
            time.sleep(0.04)
        return first, state()

    try:
        with (logs / 'vtol_acceptance_server.log').open('w') as log:
            server = subprocess.Popen(['gz', 'sim', '-s', '-v', '3',
                                       str(ROOT / 'worlds' / 'inha_songdo_vtol.sdf')],
                                      stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            control = FlightControl(takeoff_height=5)
            deadline = time.monotonic() + 25
            while control.snapshot() is None:
                if server.poll() is not None:
                    raise AssertionError('Server exited; read vtol_acceptance_server.log')
                if time.monotonic() > deadline:
                    raise AssertionError('Odometry startup timeout')
                control.resume_world()
                time.sleep(0.1)
            run(6)
            value = state()
            report['measurements']['takeoff_z_m'] = value.z
            assert abs(value.z - 5) < 0.7, f'Takeoff did not reach target: {value}'
            print('TAKEOFF PASS', value.z, flush=True)
            a, b = run(2)
            drift = math.hypot(a.x - b.x, a.y - b.y)
            report['measurements']['hover_xy_drift_2s_m'] = drift
            assert drift < 1, f'Hover drift {drift}'
            for label, inputs, axis, direction in [
                ('forward', {'x': 2}, 'x', 1),
                ('backward', {'x': -2}, 'x', -1),
                ('left', {'y': 2}, 'y', 1),
                ('right', {'y': -2}, 'y', -1),
            ]:
                run(1.5)
                a, b = run(2.5, **inputs)
                delta = getattr(b, axis) - getattr(a, axis)
                report['measurements'][f'{label}_displacement_m'] = delta
                assert direction * delta > 1.5, f'{label} wrong displacement: {delta}'
                print(label.upper(), 'PASS', delta, flush=True)
            run(2)
            a, b = run(2.5, yaw=0.4)
            yaw_delta = math.atan2(math.sin(b.yaw - a.yaw), math.cos(b.yaw - a.yaw))
            report['measurements']['positive_yaw_change_rad'] = yaw_delta
            assert yaw_delta > 0.4, f'Yaw did not turn left: {yaw_delta}'
            run(1.5)
            a, b = run(2.5, yaw=-0.4)
            yaw_delta = math.atan2(math.sin(b.yaw - a.yaw), math.cos(b.yaw - a.yaw))
            report['measurements']['negative_yaw_change_rad'] = yaw_delta
            assert yaw_delta < -0.4, f'Yaw did not turn right: {yaw_delta}'
            a = state()
            run(2.5, z=1.2)
            run(2)
            delta = state().z - a.z
            report['measurements']['climb_m'] = delta
            assert delta > 1.8, f'Climb was only {delta}'
            # A single input must expire even if no subsequent key release arrives.
            control.set_input(x=2)
            time.sleep(0.7)
            report['measurements']['expired_input_x_command'] = control.last_command[0]
            assert control.last_command[0] == 0, 'Input heartbeat failed to expire'
            print('CLIMB / INPUT EXPIRY PASS', flush=True)
            control.land()
            deadline = time.monotonic() + 70
            while control.mode != 'LANDED':
                state()
                if time.monotonic() > deadline:
                    raise AssertionError(f'Landing timeout at z={state().z}')
                time.sleep(0.05)
            report['measurements']['landed_z_m'] = state().z
            assert state().z < 0.2
            report['status'] = 'PASS'
            print('LANDING PASS', state().z, flush=True)
    except Exception as error:
        report['status'] = 'FAIL'
        report['error'] = repr(error)
        raise
    finally:
        report['wall_seconds'] = time.monotonic() - started
        (logs / 'vtol_acceptance.json').write_text(json.dumps(report, indent=2) + '\n')
        if control:
            control.close()
        if server and server.poll() is None:
            os.killpg(server.pid, signal.SIGINT)
            try:
                server.wait(timeout=6)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid, signal.SIGKILL)
                server.wait()


if __name__ == '__main__':
    main()
