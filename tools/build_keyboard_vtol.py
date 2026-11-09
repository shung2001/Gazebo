"""Adapt PX4 Standard VTOL to Gazebo's rotor-based hover velocity controller."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MODEL_NAME = 'keyboard_vtol'


def child(parent, tag, text):
    node = ET.SubElement(parent, tag)
    node.text = str(text)
    return node


def save(root, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space='  ')
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def main():
    vendor = ROOT / 'vendor' / 'px4-gazebo-models'
    source = vendor / 'models' / 'standard_vtol' / 'model.sdf'
    if not source.exists():
        raise SystemExit('Run python3 Gazebo/tools/fetch_vtol_assets.py first')
    tree = ET.parse(source)
    root = tree.getroot()
    model = root.find('model')
    model.set('name', MODEL_NAME)
    model.find('pose').text = '0 0 0 0 0 0'
    # Cover the nose and upper fuselage too: upstream's thin wing-only box
    # allowed visible parts to enter a wall before contact was resolved.
    body_collision = model.find('./link[@name="base_link"]/collision')
    body_collision.find('pose').text = '0.025 0 0.055 0 0 0'
    body_collision.find('geometry/box/size').text = '1.10 2.20 0.34'
    # No PX4 sensor bridge is used in this hover-only Gazebo controller.
    for link in model.findall('link'):
        for sensor in link.findall('sensor'):
            link.remove(sensor)
    for plugin in list(model.findall('plugin')):
        if 'multicopter-motor-model' not in plugin.get('filename', ''):
            continue
        if plugin.findtext('jointName') == 'rotor_puller_joint':
            # Hover controller has four outputs; the forward motor stays passive.
            model.remove(plugin)
            continue
        old = plugin.find('motorNumber')
        old.tag = 'actuator_number'
        child(plugin, 'robotNamespace', MODEL_NAME)

    control = ET.SubElement(model, 'plugin', {
        'filename': 'gz-sim-multicopter-control-system',
        'name': 'gz::sim::systems::MulticopterVelocityControl'})
    for key, value in {
        'robotNamespace': MODEL_NAME,
        'commandSubTopic': 'cmd_vel',
        'enableSubTopic': 'enable',
        'comLinkName': 'base_link',
        'velocityGain': '8 8 12',
        'attitudeGain': '3 3 0.8',
        'angularRateGain': '1.2 1.2 1.2',
        'maximumLinearAcceleration': '3 3 3',
        'maximumLinearVelocity': '12 12 3',
        'maximumAngularVelocity': '0 0 0.8',
    }.items():
        child(control, key, value)
    rotors = ET.SubElement(control, 'rotorConfiguration')
    for index, direction in enumerate([1, 1, -1, -1]):
        rotor = ET.SubElement(rotors, 'rotor')
        for key, value in {'jointName': f'rotor_{index}_joint',
                           'forceConstant': '2e-05', 'momentConstant': '0.06',
                           'direction': direction}.items():
            child(rotor, key, value)
    odom = ET.SubElement(model, 'plugin', {
        'filename': 'gz-sim-odometry-publisher-system',
        'name': 'gz::sim::systems::OdometryPublisher'})
    for key, value in {'dimensions': 3, 'odom_publish_frequency': 30,
                       'odom_topic': f'/{MODEL_NAME}/odometry',
                       'odom_frame': 'world', 'robot_base_frame': 'base_link'}.items():
        child(odom, key, value)
    save(root, ROOT / 'models' / MODEL_NAME / 'model.sdf')
    config = ET.Element('model')
    child(config, 'name', 'PX4 Standard VTOL - Keyboard Hover')
    child(config, 'version', '1.0')
    child(config, 'sdf', 'model.sdf').set('version', root.get('version'))
    author = ET.SubElement(config, 'author')
    child(author, 'name', 'PX4 contributors; local Gazebo hover adaptation')
    child(config, 'description', 'PX4 Standard VTOL, four-rotor Gazebo velocity control. BSD-3-Clause upstream assets.')
    save(config, ROOT / 'models' / MODEL_NAME / 'model.config')

    scene = ET.parse(ROOT / 'worlds' / 'inha_songdo.sdf').getroot()
    world = scene.find('world')
    world.set('name', 'inha_songdo_vtol')
    # A close initial view; the controller can also request following the aircraft.
    world.find('./gui/plugin[@filename="MinimalScene"]/camera_pose').text = '-118 -90 1.6 0 0.124355 0'
    gui = world.find('gui')
    screenshot = ET.SubElement(gui, 'plugin', {'filename': 'Screenshot', 'name': 'Screenshot'})
    properties = ET.SubElement(screenshot, 'gz-gui')
    for key, type_, value in [('state', 'string', 'floating'), ('width', 'double', '40'),
                              ('height', 'double', '40'), ('showTitleBar', 'bool', 'false')]:
        prop = ET.SubElement(properties, 'property', {'key': key, 'type': type_})
        prop.text = value
    include = ET.SubElement(world, 'include')
    child(include, 'uri', 'model://keyboard_vtol')
    child(include, 'name', MODEL_NAME)
    child(include, 'pose', '-110 -90 0.6 0 0 0')
    save(scene, ROOT / 'worlds' / 'inha_songdo_vtol.sdf')
    manifest = json.loads((vendor / 'SOURCE.json').read_text())
    provenance = {
        'repository': manifest['repository'], 'commit': manifest['commit'],
        'license': 'BSD-3-Clause', 'original_model': 'standard_vtol',
        'source_manifest': '../../vendor/px4-gazebo-models/SOURCE.json',
        'changes': [
            'Model renamed keyboard_vtol, spawn assigned by world',
            'Conservative 1.10 x 2.20 x 0.34m airframe collision box covers nose and fuselage',
            'PX4 sensor elements removed from local derivative',
            'Four vertical motor actuator indices normalized for Harmonic',
            'Forward pusher motor plugin removed; rotor remains passive',
            'Original lift-drag, airframe inertia, meshes and control surfaces retained',
            'Gazebo MulticopterVelocityControl and 30Hz ground-truth odometry added',
        ],
        'scope': 'Hover/multicopter-mode keyboard control; no fixed-wing transition or PX4 autopilot',
    }
    (ROOT / 'models' / MODEL_NAME / 'ADAPTATION.json').write_text(
        json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print('Created keyboard_vtol model and inha_songdo_vtol.sdf')
    print('Upstream commit:', manifest['commit'])


if __name__ == '__main__':
    main()
