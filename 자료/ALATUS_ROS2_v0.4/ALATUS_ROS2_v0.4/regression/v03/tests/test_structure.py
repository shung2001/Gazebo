import ast
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
class StructureTests(unittest.TestCase):
    def test_python_syntax(self):
        for directory in ['src','tools','integration','tests']:
            for p in (ROOT/directory).rglob('*.py'): ast.parse(p.read_text(encoding='utf-8'))
    def test_package_manifests(self):
        packages=list((ROOT/'src').glob('alatus_*/package.xml'))
        self.assertEqual(len(packages),4)
        for p in packages: self.assertEqual(ET.parse(p).getroot().tag,'package')
    def test_publishers_are_diagnostics(self):
        count=0
        for p in (ROOT/'src').rglob('*.py'):
            tree=ast.parse(p.read_text(encoding='utf-8'))
            for call in ast.walk(tree):
                if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='create_publisher':
                    topic=call.args[1]
                    self.assertIsInstance(topic,ast.Constant)
                    self.assertTrue(topic.value.startswith('/alatus/'))
                    count+=1
        self.assertEqual(count,8)
    def test_entrypoints_exist(self):
        for p in (ROOT/'src').glob('*/setup.py'):
            tree=ast.parse(p.read_text())
            for n in ast.walk(tree):
                if isinstance(n,ast.Constant) and isinstance(n.value,str) and ' = alatus_' in n.value:
                    module,fn=n.value.split(' = ')[1].split(':')
                    target=p.parent/Path(*module.split('.')).with_suffix('.py')
                    defs={d.name for d in ast.parse(target.read_text()).body if isinstance(d,ast.FunctionDef)}
                    self.assertIn(fn,defs)
if __name__=='__main__': unittest.main()
