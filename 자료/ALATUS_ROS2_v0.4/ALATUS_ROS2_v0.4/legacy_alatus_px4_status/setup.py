from glob import glob
from setuptools import setup, find_packages
setup(name='alatus_px4_status', version='0.3.0', packages=find_packages(exclude=['test']),
      data_files=[('share/ament_index/resource_index/packages', ['resource/alatus_px4_status']),
                  ('share/alatus_px4_status', ['package.xml']),
                  ('share/alatus_px4_status/launch', glob('launch/*.launch.py')),
                  ('share/alatus_px4_status/config', glob('config/*.yaml'))],
      install_requires=['setuptools'], zip_safe=True,
      maintainer='ALATUS Team', maintainer_email='maintainers@example.invalid',
      description='Shadow-only starter', license='Apache-2.0',
      entry_points={'console_scripts': ['px4_status = alatus_px4_status.adapter:main']})
