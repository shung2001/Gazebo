from glob import glob
from setuptools import setup, find_packages
setup(name='alatus_bringup', version='0.3.0', packages=find_packages(exclude=['test']),
      data_files=[('share/ament_index/resource_index/packages', ['resource/alatus_bringup']),
                  ('share/alatus_bringup', ['package.xml']),
                  ('share/alatus_bringup/launch', glob('launch/*.launch.py')),
                  ('share/alatus_bringup/config', glob('config/*.yaml'))],
      install_requires=['setuptools'], zip_safe=True,
      maintainer='ALATUS Team', maintainer_email='maintainers@example.invalid',
      description='Shadow-only starter', license='Apache-2.0',
      entry_points={'console_scripts': []})
