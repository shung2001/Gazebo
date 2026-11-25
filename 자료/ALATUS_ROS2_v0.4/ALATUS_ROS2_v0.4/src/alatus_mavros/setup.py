from setuptools import setup
setup(name='alatus_mavros',version="0.4.0",packages=['alatus_mavros'],data_files=[("share/ament_index/resource_index/packages",["resource/alatus_mavros"]),("share/alatus_mavros",["package.xml"])],install_requires=["setuptools"],entry_points={"console_scripts":['state_adapter = alatus_mavros.state_node:main', 'sitl_sender = alatus_mavros.command_node:main']})
