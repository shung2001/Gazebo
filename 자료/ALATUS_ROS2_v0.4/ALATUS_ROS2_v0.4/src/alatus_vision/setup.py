from setuptools import setup
setup(name='alatus_vision',version="0.4.0",packages=['alatus_vision'],data_files=[("share/ament_index/resource_index/packages",["resource/alatus_vision"]),("share/alatus_vision",["package.xml"])],install_requires=["setuptools"],entry_points={"console_scripts":['pipeline = alatus_vision.ros_nodes:pipeline_main', 'perception = alatus_vision.perception_node:main']})
