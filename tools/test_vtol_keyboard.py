"""Exercise actual Tk key/release/unmap events against the Gazebo controller."""
from pathlib import Path
import json
import os
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
os.environ['GZ_PARTITION'] = f'inha_vtol_keyboard_check_{os.getpid()}'
os.environ['GZ_SIM_RESOURCE_PATH'] = ':'.join([
    str(ROOT / 'models'), str(ROOT / 'vendor' / 'px4-gazebo-models' / 'models')])
from vtol_keyboard import FlightControl, KeyboardWindow


def main():
    logs = ROOT / 'logs'
    logs.mkdir(exist_ok=True)
    results = []
    failure = []
    control = None
    server = None
    with (logs / 'vtol_keyboard_check_server.log').open('w') as log:
        try:
            server = subprocess.Popen(['gz', 'sim', '-s', str(ROOT / 'worlds' / 'inha_songdo_vtol.sdf')],
                                      stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            control = FlightControl(takeoff_height=3)
            window = KeyboardWindow(control)
            window.followed = True  # No Gazebo GUI in this test's partition.
            started = time.monotonic()
            def press(key):
                # Shared desktops can move focus while a long physics step is
                # running. Re-establish test focus before each injected press.
                window.root.focus_force()
                window.root.update()
                window.root.event_generate(f'<KeyPress-{key}>')

            def later(ms, action):
                def checked():
                    try:
                        action()
                    except Exception as error:
                        failure.append(repr(error))
                        window.close()
                window.root.after(ms, checked)

            def require(condition, label):
                if not condition:
                    raise AssertionError(label)
                results.append(label)
                print('PASS:', label, flush=True)

            def press_up():
                snapshot = control.snapshot()
                if snapshot is None:
                    if time.monotonic() - started > 45:
                        raise AssertionError('No odometry during UI test')
                    later(200, press_up)
                    return
                initial_x = snapshot.x
                initial_time = snapshot.sim_time
                deadline = time.monotonic()+25
                press('Up')
                later(300, lambda: require(control.last_command[0] > 1, 'Up key publishes forward command'))
                def check_movement():
                    current = control.snapshot()
                    if current.sim_time-initial_time < 2:
                        if time.monotonic() > deadline:
                            raise AssertionError('UI test simulation did not advance')
                        later(100, check_movement)
                        return
                    require(current.x-initial_x > 0.4, 'Up key moves the physical aircraft')
                    window.root.event_generate('<KeyRelease-Up>')
                    later(250, lambda: require(control.last_command[0] == 0, 'Key release clears forward command'))
                    later(350, lambda: press('Left'))
                    later(650, lambda: require(control.last_command[1] > 1, 'Left key publishes lateral command'))
                    later(700, window.root.withdraw)
                    later(950, lambda: require(not window.pressed and control.last_command[0] == 0
                                               and control.last_command[1] == 0, 'Minimizing clears held keys'))
                    later(1050, shift_up)
                later(400, check_movement)

            def shift_up():
                window.root.deiconify()
                altitude_target = control.target_z
                initial_time = control.snapshot().sim_time
                deadline = time.monotonic()+20
                press('Shift_L')
                press('Up')
                def check_altitude():
                    if control.snapshot().sim_time-initial_time < 0.9:
                        if time.monotonic() > deadline:
                            raise AssertionError('UI climb test simulation did not advance')
                        later(100, check_altitude)
                        return
                    require(control.target_z-altitude_target > 0.5, 'Shift+Up raises the altitude target')
                    window.root.event_generate('<KeyRelease-Up>')
                    window.root.event_generate('<KeyRelease-Shift_L>')
                    later(250, window.close)
                later(300, check_altitude)

            later(1200, press_up)
            window.run()
            if failure:
                raise AssertionError('; '.join(failure))
            assert len(results) == 6
        finally:
            (logs / 'vtol_keyboard_check.json').write_text(json.dumps({
                'status': 'FAIL' if failure or len(results) != 6 else 'PASS',
                'checks': results, 'errors': failure}, indent=2) + '\n')
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
