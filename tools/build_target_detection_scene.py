"""Build a campus facade experiment with a 100 m, 60 m VTOL start.

The existing keyboard world and model remain untouched. Generated files are
kept in their own model/world paths so the launcher can validate them.
"""
from pathlib import Path
import math
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / 'models' / 'target_detection_vtol'
WORLD_PATH = ROOT / 'worlds' / 'target_detection.sdf'
CAMERA_X = 0.6
ALTITUDE = 60.0
TARGET = (-65.380811, -5.656304, 8.0)
WALL_YAW = -0.658892054
OUTWARD = (math.sin(WALL_YAW), -math.cos(WALL_YAW))
FORWARD = (-OUTWARD[0], -OUTWARD[1])
START_RANGE = 100.0
HORIZONTAL_RANGE = math.sqrt(START_RANGE**2 - (ALTITUDE-TARGET[2])**2)
START_YAW = math.atan2(FORWARD[1], FORWARD[0])
CAMERA_PITCH = math.atan2(ALTITUDE-TARGET[2], HORIZONTAL_RANGE)
START = (TARGET[0]+OUTWARD[0]*(HORIZONTAL_RANGE+CAMERA_X),
         TARGET[1]+OUTWARD[1]*(HORIZONTAL_RANGE+CAMERA_X), ALTITUDE)
CAMERA_SIZE = 3200
CAMERA_TOPIC = '/target_detection/camera'


def element(parent, tag, value=None, **attributes):
    child = ET.SubElement(parent, tag, attributes)
    if value is not None:
        child.text = str(value)
    return child


def build():
    source = ROOT / 'models' / 'keyboard_vtol' / 'model.sdf'
    if not source.exists():
        raise FileNotFoundError(f'Missing VTOL model: {source}')
    if not (ROOT / 'models' / 'wall_target' / 'model.sdf').exists():
        raise FileNotFoundError('Missing models/wall_target; build the target first')
    tree = ET.parse(source)
    model = tree.getroot().find('model')
    model.set('name', 'target_detection_vtol')
    link = model.find("link[@name='base_link']")
    sensor = element(link, 'sensor', name='fuselage_camera', type='camera')
    element(sensor, 'pose', f'{CAMERA_X} 0 0 0 {CAMERA_PITCH:.9f} 0')
    element(sensor, 'always_on', 1)
    element(sensor, 'update_rate', 1)
    element(sensor, 'topic', CAMERA_TOPIC)
    camera = element(sensor, 'camera')
    element(camera, 'horizontal_fov', '1.0471975512')
    image = element(camera, 'image')
    element(image, 'width', CAMERA_SIZE)
    element(image, 'height', CAMERA_SIZE)
    element(image, 'format', 'R8G8B8')
    clip = element(camera, 'clip')
    element(clip, 'near', 0.1)
    element(clip, 'far', 250)
    MODEL_DIR.mkdir(exist_ok=True)
    ET.indent(tree)
    tree.write(MODEL_DIR / 'model.sdf', encoding='utf-8', xml_declaration=True)
    (MODEL_DIR / 'model.config').write_text(
        '<model><name>Target Detection VTOL</name><version>1.0</version>'
        '<sdf version="1.10">model.sdf</sdf></model>\n', encoding='utf-8')

    world_tree = ET.parse(ROOT / 'worlds' / 'inha_songdo_vtol.sdf')
    sdf = world_tree.getroot()
    world = sdf.find('world')
    world.set('name', 'target_detection')
    sensors = element(world, 'plugin', filename='gz-sim-sensors-system',
                      name='gz::sim::systems::Sensors')
    element(sensors, 'render_engine', 'ogre2')
    vtol = next(item for item in world.findall('include')
                if item.findtext('name') == 'keyboard_vtol')
    vtol.find('uri').text = 'model://target_detection_vtol'
    vtol.find('pose').text = (f'{START[0]:.9f} {START[1]:.9f} {START[2]:.3f} '
                              f'0 0 {START_YAW:.9f}')
    ET.indent(sdf)
    world_tree.write(WORLD_PATH, encoding='utf-8', xml_declaration=True)
    return WORLD_PATH


if __name__ == '__main__':
    print(build())
