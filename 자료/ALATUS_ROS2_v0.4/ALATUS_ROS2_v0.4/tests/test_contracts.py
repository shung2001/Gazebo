from pathlib import Path
import ast,json,xml.etree.ElementTree as E
import pytest,yaml
ROOT=Path(__file__).resolve().parents[1]
def test_preserved_legacy_messages():
 for old in (ROOT/'regression/v03/src/alatus_interfaces/msg').glob('*.msg'):
  assert (ROOT/'src/alatus_interfaces/msg'/old.name).read_bytes()==old.read_bytes()
def test_legacy_pure_logic_unchanged():
 for name in ['core.py','clock_guard.py','perception_protocol.py']:
  assert (ROOT/'src/alatus_runtime/alatus_runtime'/name).read_bytes()==(ROOT/'regression/v03/src/alatus_runtime/alatus_runtime'/name).read_bytes()
def test_dds_not_in_default_source_tree():assert not (ROOT/'src/alatus_px4_status').exists()
def test_new_manifests():
 for p in (ROOT/'src').glob('*/package.xml'):
  t=E.parse(p).getroot();assert t.findtext('version')=='0.4.0'
 assert len(list((ROOT/'src').glob('*/package.xml')))==5
def test_shadow_launch_never_sender():
 for p in (ROOT/'src/alatus_bringup/launch').glob('*shadow.launch.py'):
  assert 'sitl_sender' not in p.read_text()
 assert 'sitl_sender' not in (ROOT/'src/alatus_bringup/launch/onboard_shadow.launch.py').read_text()
def test_message_generation_list():
 c=(ROOT/'src/alatus_interfaces/CMakeLists.txt').read_text()
 for p in (ROOT/'src/alatus_interfaces/msg').glob('*.msg'):assert 'msg/'+p.name in c
def test_configs_install_copy_consistent():
 for p in (ROOT/'config').glob('*.yaml'):
  other=ROOT/'src/alatus_bringup/config/v04'/p.name
  assert p.read_bytes()==other.read_bytes()
def test_shell_lf():
 for p in (ROOT/'tools').glob('*.sh'):assert b'\r\n' not in p.read_bytes()
def test_sim_xml():
 for p in (ROOT/'sim').glob('*.sdf'):E.parse(p)
def test_all_entrypoints_parse():
 for p in (ROOT/'src').rglob('*.py'):ast.parse(p.read_text())
