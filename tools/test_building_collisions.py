"""Actual physics acceptance: roof support, open ground, VTOL impact on a wall."""
from pathlib import Path
import json
import math
import os
import signal
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
os.environ['GZ_PARTITION'] = f'inha_collision_acceptance_{os.getpid()}'
os.environ['GZ_SIM_RESOURCE_PATH'] = ':'.join([
    str(ROOT / 'models'), str(ROOT / 'vendor/px4-gazebo-models/models')])
from gz.msgs10.odometry_pb2 import Odometry
from vtol_keyboard import FlightControl


def inside(x, y, polygon):
    return all((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]) >= -1e-5
               for a, b in zip(polygon, polygon[1:]+polygon[:1]))


def select_wall_and_roof():
    cells = json.loads((ROOT / 'collision_cells.json').read_text())
    def occupied(x, y, z):
        return any(c['height_m'] > z and inside(x, y, c['footprint']) for c in cells)
    vertices, walls, roofs = [], [], []
    for line in (ROOT / 'models/inha_songdo_scene/meshes/scene.obj').read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'v':
            vertices.append(tuple(map(float, fields[1:4])))
        elif fields[0] == 'f':
            ids = [int(p.split('/')[0]) for p in fields[1:]]
            a, b, c = [vertices[i-1 if i > 0 else len(vertices)+i] for i in ids]
            u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
            normal = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
            zs = [a[2], b[2], c[2]]
            if max(zs)-min(zs) < 1e-4 and min(zs) > 5:
                roofs.append((abs(normal[2])/2, tuple((a[i]+b[i]+c[i])/3 for i in range(3))))
            elif min(zs) < 0.1 and max(zs) > 12 and abs(normal[2]) < 1e-4:
                xy = sorted(set((p[0], p[1]) for p in [a, b, c]))
                if len(xy) != 2 or math.dist(*xy) < 12:
                    continue
                length = math.hypot(normal[0], normal[1])
                nx, ny = normal[0]/length, normal[1]/length
                mx, my = (xy[0][0]+xy[1][0])/2, (xy[0][1]+xy[1][1])/2
                if not occupied(mx+nx*7, my+ny*7, 8) and occupied(mx-nx*2, my-ny*2, 8):
                    walls.append((mx, my, nx, ny))
    if not walls or not roofs:
        raise AssertionError('No suitable real wall or roof found')
    return walls[0], max(roofs)[1]


def add_probe(world, name, xyz):
    model = ET.SubElement(world, 'model', {'name': name})
    ET.SubElement(model, 'pose').text = ' '.join(map(str, xyz)) + ' 0 0 0'
    link = ET.SubElement(model, 'link', {'name': 'body'})
    inertial = ET.SubElement(link, 'inertial')
    ET.SubElement(inertial, 'mass').text = '1'
    inertia = ET.SubElement(inertial, 'inertia')
    for key in ('ixx', 'iyy', 'izz'):
        ET.SubElement(inertia, key).text = '0.025'
    collision = ET.SubElement(link, 'collision', {'name': 'sphere'})
    geometry = ET.SubElement(collision, 'geometry')
    ET.SubElement(ET.SubElement(geometry, 'sphere'), 'radius').text = '0.25'
    odom = ET.SubElement(model, 'plugin', {'filename': 'gz-sim-odometry-publisher-system',
                                         'name': 'gz::sim::systems::OdometryPublisher'})
    ET.SubElement(odom, 'dimensions').text = '3'
    ET.SubElement(odom, 'odom_topic').text = f'/{name}/odometry'


def main():
    logs = ROOT / 'logs'
    logs.mkdir(exist_ok=True)
    report = {'status': 'RUNNING'}
    control, server = None, None
    wall, roof = select_wall_and_roof()
    mx, my, nx, ny = wall
    spawn = (mx+nx*7, my+ny*7, 8)
    heading = math.atan2(-ny, -nx)
    report.update({'wall_midpoint_xy': [mx, my], 'wall_outward_normal': [nx, ny],
                   'aircraft_spawn': spawn, 'roof_xyz': roof})
    probes = {}
    try:
        with tempfile.TemporaryDirectory(prefix='inha_collision_') as directory, \
                (logs / 'building_collision_server.log').open('w') as log:
            tree = ET.parse(ROOT / 'worlds/inha_songdo_vtol.sdf')
            world = tree.getroot().find('world')
            for include in world.findall('include'):
                if include.findtext('name') == 'keyboard_vtol':
                    include.find('pose').text = ' '.join(map(str, (*spawn, 0, 0, heading)))
            add_probe(world, 'roof_probe', (roof[0], roof[1], roof[2]+3))
            add_probe(world, 'gap_probe', (-110, -90, 6))
            path = Path(directory) / 'collision.sdf'
            tree.write(path, encoding='utf-8', xml_declaration=True)
            server = subprocess.Popen(['gz', 'sim', '-s', str(path)], stdout=log,
                                      stderr=subprocess.STDOUT, start_new_session=True)
            control = FlightControl(takeoff_height=8)
            for name in ['roof_probe', 'gap_probe']:
                control.node.subscribe(Odometry, f'/{name}/odometry',
                                       lambda msg, key=name: probes.__setitem__(key, msg.pose.position.z))
            deadline = time.monotonic()+35
            while control.snapshot() is None:
                if time.monotonic() > deadline or server.poll() is not None:
                    raise AssertionError('Collision world did not start')
                control.resume_world()
                time.sleep(0.1)
            start = control.snapshot().sim_time
            distances = []
            wall_deadline = time.monotonic()+70
            while control.snapshot().sim_time-start < 9:
                if time.monotonic() > wall_deadline:
                    raise AssertionError('Collision simulation stopped advancing')
                snapshot = control.snapshot()
                elapsed = snapshot.sim_time-start
                control.set_input(x=3 if elapsed > 3 else 0)
                distances.append((snapshot.x-mx)*nx+(snapshot.y-my)*ny)
                time.sleep(0.04)
            report['roof_probe_z_m'] = probes.get('roof_probe')
            report['gap_probe_z_m'] = probes.get('gap_probe')
            report['minimum_wall_distance_m'] = min(distances)
            report['final_wall_distance_m'] = distances[-1]
            assert abs(probes['roof_probe']-(roof[2]+0.25)) < 0.15, 'Probe fell through the roof'
            assert abs(probes['gap_probe']-0.25) < 0.15, 'Open ground was blocked by a city-wide hull'
            assert min(distances) > -0.15, 'VTOL center crossed the wall'
            assert min(distances) < 1.8, 'VTOL did not approach the wall closely enough'
            report['status'] = 'PASS'
            print(json.dumps(report, indent=2), flush=True)
    except Exception as error:
        report['status'] = 'FAIL'
        report['error'] = repr(error)
        raise
    finally:
        (logs / 'building_collision_acceptance.json').write_text(json.dumps(report, indent=2)+'\n')
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
