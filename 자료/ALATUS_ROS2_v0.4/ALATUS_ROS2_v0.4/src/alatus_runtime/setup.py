from glob import glob
from setuptools import setup, find_packages
setup(name='alatus_runtime', version='0.4.0', packages=find_packages(exclude=['test']),
      data_files=[('share/ament_index/resource_index/packages', ['resource/alatus_runtime']),
                  ('share/alatus_runtime', ['package.xml']),
                  ('share/alatus_runtime/launch', glob('launch/*.launch.py')),
                  ('share/alatus_runtime/config', glob('config/*.yaml'))],
      install_requires=['setuptools'], zip_safe=True,
      maintainer='ALATUS Team', maintainer_email='maintainers@example.invalid',
      description='Shadow-only starter', license='Apache-2.0',
      entry_points={'console_scripts': ['mock_perception = alatus_runtime.nodes:mock_perception_main', 'tracker = alatus_runtime.nodes:tracker_main', 'mock_status = alatus_runtime.nodes:mock_status_main', 'mission = alatus_runtime.nodes:mission_main', 'guidance = alatus_runtime.nodes:guidance_main', 'safety_gate = alatus_runtime.nodes:safety_gate_main', 'perception_socket = alatus_runtime.perception_socket:main']})
