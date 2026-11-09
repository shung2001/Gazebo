"""Build a local Gazebo visual environment from the supplied QGIS OBJ and SHPs.

Only Python's standard library is required. Source assets are never modified.
"""
from pathlib import Path
import argparse
from collections import defaultdict, deque
import hashlib
import json
import math
import struct
import xml.etree.ElementTree as ET


def shp_geometry(path):
    data = path.read_bytes()
    if struct.unpack_from('>i', data)[0] != 9994:
        raise ValueError(f'Not a shapefile: {path}')
    bbox = struct.unpack_from('<4d', data, 36)
    points = []
    offset = 100
    while offset < len(data):
        size = struct.unpack_from('>i', data, offset + 4)[0] * 2
        record = data[offset + 8:offset + 8 + size]
        offset += 8 + size
        kind = struct.unpack_from('<i', record)[0]
        if kind == 0:
            continue
        if kind != 5:
            raise ValueError('This conversion expects Polygon (type 5) SHP data')
        parts, count = struct.unpack_from('<ii', record, 36)
        start = 44 + 4 * parts
        points.extend(struct.iter_unpack('<dd', record[start:start + 16 * count]))
    return bbox, points


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8', newline='\n')


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def area(points):
    return abs(sum(a[0]*b[1]-b[0]*a[1]
                   for a, b in zip(points, points[1:] + points[:1]))) / 2


def hull(points):
    points = sorted(set(points))
    halves = []
    for sequence in (points, list(reversed(points))):
        half = []
        for p in sequence:
            while len(half) >= 2 and cross(half[-2], half[-1], p) <= 1e-9:
                half.pop()
            half.append(p)
        halves.append(half[:-1])
    return tuple(halves[0] + halves[1])


def convex_collision_cells(mesh_lines):
    """Extrude actual roof triangles, merging only convex adjacent unions.

    A single city mesh can be convexified by physics backends. Separate convex
    prisms retain streets and concave building outlines without that assumption.
    """
    vertices, groups = [], defaultdict(set)
    for line in mesh_lines:
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'v':
            vertices.append(tuple(map(float, fields[1:4])))
        elif fields[0] == 'f':
            indices = [int(t.split('/')[0]) for t in fields[1:]]
            points = [vertices[i-1 if i > 0 else len(vertices)+i] for i in indices]
            if len(points) != 3 or max(p[2] for p in points)-min(p[2] for p in points) > 1e-4:
                continue
            z = round(sum(p[2] for p in points)/3, 4)
            if z <= 0.05:
                continue
            xy = hull([(round(p[0], 4), round(p[1], 4)) for p in points])
            if len(xy) == 3 and area(xy) > 1e-5:
                groups[z].add(xy)
    triangle_count = sum(map(len, groups.values()))
    result = []
    for z, triangles in sorted(groups.items()):
        polygons = dict(enumerate(sorted(triangles)))
        edges = defaultdict(set)
        pending = deque()

        def polygon_edges(poly):
            return [tuple(sorted((a, b))) for a, b in zip(poly, poly[1:]+poly[:1])]

        def add(pid, poly):
            for edge in polygon_edges(poly):
                edges[edge].add(pid)
                if len(edges[edge]) == 2:
                    pending.append(edge)

        for pid, poly in polygons.items():
            add(pid, poly)
        next_id = len(polygons)
        while pending:
            edge = pending.popleft()
            ids = edges[edge]
            if len(ids) != 2:
                continue
            a, b = sorted(ids)
            merged = hull(polygons[a] + polygons[b])
            sum_area = area(polygons[a]) + area(polygons[b])
            if abs(area(merged)-sum_area) > max(0.0002, sum_area*1e-7):
                continue
            for pid in (a, b):
                for old_edge in polygon_edges(polygons[pid]):
                    edges[old_edge].discard(pid)
                del polygons[pid]
            polygons[next_id] = merged
            add(next_id, merged)
            next_id += 1
        result.extend({'height_m': z, 'footprint': list(poly)} for poly in polygons.values())
    if not result:
        raise ValueError('No horizontal building roofs found for collision construction')
    return result, triangle_count


def write_convex_prism(path, xy, height):
    """Closed, explicitly triangulated prism; avoids polyline ear-clipping loss."""
    vertices = [(x, y, 0.0) for x, y in xy] + [(x, y, height) for x, y in xy]
    n = len(xy)
    faces = []
    for i in range(1, n-1):
        faces.extend([(0, i+1, i), (n, n+i, n+i+1)])
    for i in range(n):
        j = (i+1) % n
        faces.extend([(i, j, n+j), (i, n+j, n+i)])
    data = bytearray(b'QGIS building convex collision prism'.ljust(80, b'\0'))
    data.extend(struct.pack('<I', len(faces)))
    for indices in faces:
        a, b, c = [vertices[i] for i in indices]
        u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
        normal = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        length = math.sqrt(sum(x*x for x in normal))
        if length <= 0:
            raise ValueError('Degenerate convex collision face')
        normal = [x/length for x in normal]
        data.extend(struct.pack('<12fH', *normal, *a, *b, *c, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def build(project, output, collisions=True):
    source = project / 'QGIS' / 'Scene.obj'
    reference = project / 'QGIS' / '인하대_송도캠.shp'
    focus = project / 'QGIS' / '인하대_송도캠_찐.shp'
    # This export contains CP949 object names, without UVs/material definitions.
    text = source.read_text(encoding='cp949')
    vertices = [tuple(map(float, line.split()[1:4]))
                for line in text.splitlines() if line.startswith('v ')]
    lo = [min(v[i] for v in vertices) for i in range(3)]
    hi = [max(v[i] for v in vertices) for i in range(3)]
    box, reference_points = shp_geometry(reference)
    focus_box, _ = shp_geometry(focus)
    center = [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2]
    origin = [(focus_box[0] + focus_box[2]) / 2,
              (focus_box[1] + focus_box[3]) / 2]
    # Recover this export's uniform normalization from its XY extents.
    sx = (box[2] - box[0]) / (hi[0] - lo[0])
    sy = (box[3] - box[1]) / (hi[1] - lo[1])
    if abs(sx / sy - 1) > 0.001:
        raise ValueError('OBJ and reference SHP extents disagree; scale requires review')
    scale = sy
    # Verify north-positive Y against real footprint vertices, rather than assume
    # a QGIS/OpenGL axis rotation. This sample is deterministic.
    samples = vertices[::max(1, len(vertices) // 100)]
    errors = []
    for x, y, _ in samples:
        e, n = x * scale + center[0], y * scale + center[1]
        errors.append(min(math.hypot(e - pe, n - pn)
                          for pe, pn in reference_points))
    if max(errors) > 0.1:
        raise ValueError('OBJ footprint does not match SHP to 0.1m; review axes/scale')

    def local(v):
        return (v[0] * scale + center[0] - origin[0],
                v[1] * scale + center[1] - origin[1],
                (v[2] - lo[2]) * scale)

    model = output / 'models' / 'inha_songdo_scene'
    lines = ['# Derived from QGIS/Scene.obj; local metres, +X east, +Y north, +Z up.',
             'mtllib scene.mtl']
    objects = []
    normal_count = face_count = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        kind = line.split()[0]
        if kind == 'mtllib':
            continue
        if kind == 'o':
            original_name = line[2:]
            highlighted = '_찐_' in original_name
            name = f'campus_{len(objects)}' if highlighted else f'surroundings_{len(objects)}'
            objects.append({'name': name, 'highlighted': highlighted})
            lines.extend([f'o {name}',
                          'usemtl campus_red' if highlighted else 'usemtl buildings_gray'])
        elif kind == 'v':
            xyz = local(tuple(map(float, line.split()[1:4])))
            lines.append('v ' + ' '.join(f'{value:.6f}' for value in xyz))
        elif kind == 'vn':
            normal_count += 1
            lines.append(line)
        elif kind == 'f':
            # Uniform positive scale + translation preserve normals and winding.
            face_count += 1
            lines.append(line)
        else:
            lines.append(line)
    write(model / 'meshes' / 'scene.obj', '\n'.join(lines) + '\n')
    write(model / 'meshes' / 'scene.mtl', '''# Display colours based on the QGIS project's layer styles.
newmtl campus_red
Ka 0.3 0.04 0.04
Kd 0.85 0.12 0.12
Ks 0.05 0.05 0.05
Ns 10
d 1
illum 2

newmtl buildings_gray
Ka 0.2 0.2 0.2
Kd 0.7 0.7 0.7
Ks 0.05 0.05 0.05
Ns 10
d 1
illum 2
''')
    cells, roof_triangles = convex_collision_cells(lines) if collisions else ([], 0)
    collision_parts = []
    for index, cell in enumerate(cells):
        xy = cell['footprint']
        cx = sum(p[0] for p in xy)/len(xy)
        cy = sum(p[1] for p in xy)/len(xy)
        name = f'cell_{index:05d}.stl'
        write_convex_prism(model / 'meshes' / 'collisions' / name,
                           [(x-cx, y-cy) for x, y in xy], cell['height_m']+0.02)
        collision_parts.append(f'''
      <collision name="building_cell_{index}">
        <pose>{cx:.6f} {cy:.6f} -0.02 0 0 0</pose>
        <geometry><mesh><uri>meshes/collisions/{name}</uri></mesh></geometry>
      </collision>''')
    collision = ''.join(collision_parts)
    write(output / 'collision_cells.json', json.dumps(cells, separators=(',', ':')) + '\n')
    write(model / 'model.sdf', f'''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="inha_songdo_scene">
    <static>true</static>
    <link name="buildings">
      <visual name="buildings_visual">
        <geometry><mesh><uri>meshes/scene.obj</uri></mesh></geometry>
        <cast_shadows>true</cast_shadows>
      </visual>{collision}
    </link>
  </model>
</sdf>
''')
    write(model / 'model.config', '''<?xml version="1.0"?>
<model>
  <name>INHA Songdo QGIS Buildings</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>Local QGIS import</name></author>
  <description>Local metre-scale visual environment derived from QGIS/Scene.obj.</description>
</model>
''')
    write(output / 'worlds' / 'inha_songdo.sdf', '''<?xml version="1.0"?>
<sdf version="1.9">
  <world name="inha_songdo">
    <physics name="default_physics" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1</real_time_factor>
    </physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <scene>
      <ambient>0.55 0.55 0.55 1</ambient>
      <background>0.65 0.78 0.9 1</background>
      <shadows>true</shadows>
      <grid>false</grid>
    </scene>
    <gui fullscreen="false">
      <plugin filename="MinimalScene" name="3D View">
        <gz-gui>
          <title>3D View</title>
          <property type="bool" key="showTitleBar">false</property>
          <property type="string" key="state">docked</property>
        </gz-gui>
        <engine>ogre2</engine>
        <scene>scene</scene>
        <ambient_light>0.55 0.55 0.55</ambient_light>
        <background_color>0.65 0.78 0.9</background_color>
        <camera_pose>300 -400 250 0 0.46365 2.2143</camera_pose>
        <camera_clip><near>0.1</near><far>10000</far></camera_clip>
      </plugin>
      <plugin filename="GzSceneManager" name="Scene Manager"/>
      <plugin filename="InteractiveViewControl" name="Interactive view control"/>
      <plugin filename="EntityContextMenuPlugin" name="Entity context menu"/>
      <plugin filename="CameraTracking" name="Camera tracking"/>
      <plugin filename="EntityTree" name="Entity tree"/>
      <plugin filename="WorldControl" name="World control">
        <play_pause>true</play_pause><step>true</step><start_paused>true</start_paused>
      </plugin>
    </gui>
    <light name="sun" type="directional">
      <pose>0 0 1000 0 0 0</pose>
      <cast_shadows>true</cast_shadows>
      <diffuse>0.85 0.85 0.85 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.4 0.2 -0.9</direction>
      <attenuation><range>10000</range><constant>0.9</constant><linear>0.01</linear><quadratic>0.001</quadratic></attenuation>
    </light>
    <model name="ground_plane">
      <static>true</static>
      <link name="ground">
        <collision name="ground_collision">
          <geometry><plane><normal>0 0 1</normal><size>4000 4000</size></plane></geometry>
        </collision>
        <visual name="ground_visual">
          <geometry><plane><normal>0 0 1</normal><size>4000 4000</size></plane></geometry>
          <material><ambient>0.22 0.28 0.22 1</ambient><diffuse>0.34 0.42 0.34 1</diffuse></material>
        </visual>
      </link>
    </model>
    <include><uri>model://inha_songdo_scene</uri></include>
  </world>
</sdf>
''')
    converted = [local(v) for v in vertices]
    info = {
        'source': 'QGIS/Scene.obj',
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'source_encoding': 'cp949',
        'vertices': len(vertices), 'normals': normal_count, 'triangles': face_count,
        'source_bounds': {'min': lo, 'max': hi},
        'uniform_scale_m_per_obj_unit': scale,
        'scale_recovery': 'Reference SHP northing span / OBJ Y span; X agreement checked',
        'horizontal_match_sample_max_error_m': max(errors),
        'horizontal_match_sample_mean_error_m': sum(errors) / len(errors),
        'horizontal_crs': 'EPSG:5186',
        'origin_easting_northing_m': origin,
        'axes': ['east', 'north', 'up'],
        'ground_z_m': 0,
        'height_datum': 'Relative to source mesh minimum Z; not surveyed elevation',
        'size_m': [(hi[i] - lo[i]) * scale for i in range(3)],
        'local_bounds': {'min': [min(v[i] for v in converted) for i in range(3)],
                         'max': [max(v[i] for v in converted) for i in range(3)]},
        'objects': objects,
        'building_collisions': collisions,
        'building_collision_cells': len(cells),
        'collision_roof_triangles': roof_triangles,
        'collision_method': 'convex roof-footprint prisms' if collisions else 'none',
        'textures': False,
    }
    write(output / 'scene_metadata.json', json.dumps(info, ensure_ascii=False, indent=2) + '\n')
    for path in [model / 'model.sdf', model / 'model.config', output / 'worlds' / 'inha_songdo.sdf']:
        ET.parse(path)
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group()
    options.add_argument('--building-collisions', dest='building_collisions', action='store_true',
                         help='Enable building mesh collisions (the default)')
    options.add_argument('--no-building-collisions', dest='building_collisions', action='store_false',
                         help='Create a visual-only building model')
    parser.set_defaults(building_collisions=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    build(root, root / 'Gazebo', args.building_collisions)
