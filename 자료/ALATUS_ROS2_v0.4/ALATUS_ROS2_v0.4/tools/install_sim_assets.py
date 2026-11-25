"""Add a separate camera-equipped copy to NEW v1.17 checkout; upstream model untouched."""
from pathlib import Path
import argparse,shutil,subprocess,xml.etree.ElementTree as E
p=argparse.ArgumentParser();p.add_argument('--px4',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];px=a.px4.expanduser().resolve()
sha=subprocess.check_output(['git','-C',str(px),'rev-parse','HEAD'],text=True).strip()
if sha!='d6f12ad1c4f70ad3230afd7d86e971421e02fef4':raise SystemExit('Expected pinned v1.17.0 checkout')
models=px/'Tools/simulation/gz/models';src=models/'advanced_plane';dest=models/'advanced_plane_vision'
if dest.exists():raise SystemExit('Destination already exists; inspect it before replacing')
shutil.copytree(src,dest)
tree=E.parse(dest/'model.sdf');model=tree.getroot().find('model');model.set('name','advanced_plane_vision')
link=model.find("link[@name='base_link']")
if link is None:raise SystemExit('Upstream base_link missing')
link.append(E.parse(root/'sim/camera_sensor.sdf').getroot());tree.write(dest/'model.sdf',encoding='unicode',xml_declaration=True)
config=E.parse(dest/'model.config');config.getroot().find('name').text='advanced_plane_vision';config.write(dest/'model.config',encoding='unicode')
world=px/'Tools/simulation/gz/worlds/alatus_recovery.sdf'
if world.exists():raise SystemExit('World exists; inspect it before replacing')
shutil.copy2(root/'sim/alatus_recovery.sdf',world)
print('Installed separate advanced_plane_vision and alatus_recovery; physics NOT TESTED')
