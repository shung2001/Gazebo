"""Read the running VTOL camera and verify an aft, body-relative view."""
from pathlib import Path
import argparse
import json
import math
import os
import threading
import time

os.environ.setdefault('GZ_PARTITION', 'inha_songdo_vtol')
from gz.transport13 import Node
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.cameratrack_pb2 import CameraTrack
from gz.msgs10.odometry_pb2 import Odometry
from gz.msgs10.pose_pb2 import Pose
from gz.msgs10.stringmsg_pb2 import StringMsg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore', action='store_true', help='Request the centered rear view before checking')
    parser.add_argument('--screenshot', action='store_true', help='Also save a Gazebo 3D screenshot')
    args = parser.parse_args()
    node = Node()
    if args.restore:
        publisher = node.advertise('/gui/track', CameraTrack)
        deadline = time.monotonic()+5
        while not publisher.has_connections() and time.monotonic() < deadline:
            time.sleep(0.1)
        if not publisher.has_connections():
            raise SystemExit('No CameraTracking topic subscriber')
        request = CameraTrack(track_mode=CameraTrack.FOLLOW)
        request.follow_target.name = 'keyboard_vtol'
        request.follow_offset.x, request.follow_offset.z = -8, 1
        request.follow_pgain = request.track_pgain = 1
        for _ in range(3):
            publisher.publish(request)
            time.sleep(0.2)
    messages = {}
    lock = threading.Lock()
    def receive(key, msg):
        with lock:
            messages[key] = (time.monotonic(), msg)
    node.subscribe(Odometry, '/keyboard_vtol/odometry', lambda msg: receive('aircraft', msg))
    node.subscribe(Pose, '/gui/camera/pose', lambda msg: receive('camera', msg))
    deadline = time.monotonic()+12
    pairs = []
    while time.monotonic() < deadline and len(pairs) < 15:
        with lock:
            if len(messages) == 2:
                a, c = messages['aircraft'], messages['camera']
                if abs(a[0]-c[0]) < 0.2:
                    pairs.append((a[1], c[1]))
        time.sleep(0.1)
    if not pairs:
        raise SystemExit('No synchronized aircraft/camera data; run Gazebo/run_vtol.sh first')
    offsets = []
    for aircraft, camera in pairs:
        p, q = aircraft.pose.position, aircraft.pose.orientation
        x, y, z, w = q.x, q.y, q.z, q.w
        rotation = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                    [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                    [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
        delta = [camera.position.x-p.x, camera.position.y-p.y, camera.position.z-p.z]
        offsets.append([sum(rotation[i][j]*delta[i] for i in range(3)) for j in range(3)])
    value = [sum(p[i] for p in offsets)/len(offsets) for i in range(3)]
    report = {'status': 'PASS', 'partition': os.environ['GZ_PARTITION'],
              'samples': len(offsets), 'mean_camera_offset_body_m': value,
              'expected_offset_body_m': [-8, 0, 1],
              'aircraft_heading_rad': math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))}
    if abs(value[0]+8) > 0.3 or abs(value[1]) > 0.2 or abs(value[2]-1) > 0.3:
        report['status'] = 'FAIL'
    destination = Path(__file__).resolve().parents[1] / 'validation'
    destination.mkdir(exist_ok=True)
    (destination / 'rear_camera_check.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    assert report['status'] == 'PASS', 'Camera is not centered aft of the aircraft'
    if not args.screenshot:
        return
    before = set(destination.glob('*.png'))
    ok, response = node.request('/gui/screenshot', StringMsg(data=str(destination)),
                                StringMsg, Boolean, 2000)
    if ok and response.data:
        for _ in range(100):
            new = set(destination.glob('*.png'))-before
            if new:
                candidate = next(iter(new))
                if candidate.stat().st_size > 100:
                    candidate.replace(destination/'vtol_rear.png')
                    break
            time.sleep(0.1)


if __name__ == '__main__':
    main()
