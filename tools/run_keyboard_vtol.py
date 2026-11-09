"""Launch the campus VTOL simulator and keyboard window as one local session."""
from pathlib import Path
import fcntl
import os
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != 'linux':
        raise SystemExit('Run this launcher inside Ubuntu WSL, not Windows Python.')
    os.environ.setdefault('GZ_PARTITION', 'inha_songdo_vtol')
    os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')
    paths = [str(ROOT / 'models'), str(ROOT / 'vendor' / 'px4-gazebo-models' / 'models')]
    if os.environ.get('GZ_SIM_RESOURCE_PATH'):
        paths.append(os.environ['GZ_SIM_RESOURCE_PATH'])
    os.environ['GZ_SIM_RESOURCE_PATH'] = ':'.join(paths)
    # Imports happen after setting the transport partition.
    from vtol_keyboard import FlightControl, KeyboardWindow
    lock_file = open(f'/tmp/inha_vtol_{os.getuid()}_{os.environ["GZ_PARTITION"]}.lock', 'a')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('A VTOL keyboard session is already running. Close it first.')
    model = ROOT / 'models' / 'keyboard_vtol' / 'model.sdf'
    if not model.exists():
        raise SystemExit('Run tools/fetch_vtol_assets.py and tools/build_keyboard_vtol.py first.')
    (ROOT / 'logs').mkdir(exist_ok=True)
    log_path = ROOT / 'logs' / 'vtol_latest.log'
    control = None
    server = None
    stop_requested = False
    def request_stop(_signal, _frame):
        nonlocal stop_requested
        stop_requested = True
    old_handlers = {number: signal.signal(number, request_stop)
                    for number in (signal.SIGINT, signal.SIGTERM)}
    try:
        with log_path.open('w') as log:
            print('Starting campus + PX4 Standard VTOL. Log:', log_path, flush=True)
            print('Keyboard window: arrows move; Shift+arrows altitude/yaw; Space hold.', flush=True)
            server = subprocess.Popen(['gz', 'sim', '-v', '3', str(ROOT / 'worlds' / 'inha_songdo_vtol.sdf')],
                                      stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            control = FlightControl()
            window = KeyboardWindow(control)
            def check_server():
                if window.closed:
                    return
                if stop_requested:
                    window.close()
                    return
                if server.poll() is not None:
                    print('Gazebo exited. Check', log_path, flush=True)
                    window.close()
                    return
                window.root.after(500, check_server)
            window.root.after(500, check_server)
            window.run()
    except KeyboardInterrupt:
        pass
    finally:
        if control:
            control.close()
        if server and server.poll() is None:
            os.killpg(server.pid, signal.SIGINT)
            try:
                server.wait(timeout=6)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid, signal.SIGTERM)
                try:
                    server.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(server.pid, signal.SIGKILL)
                    server.wait()
        lock_file.close()
        for number, handler in old_handlers.items():
            signal.signal(number, handler)


if __name__ == '__main__':
    main()
