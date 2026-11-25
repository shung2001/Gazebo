"""Source/document contract checks, no ROS mocking or runtime compatibility claims."""
import ast
import json
from pathlib import Path
import unittest
from alatus_runtime.parameter_specs import SPECS

ROOT = Path(__file__).resolve().parents[1]

class DesignConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.records = json.loads((ROOT/'design/parameter_registry.json').read_text(encoding='utf-8'))['records']

    def test_declared_parameters_match_registry(self):
        actual={(node,name):s['default'] for node,params in SPECS.items() for name,s in params.items()}
        documented = {(r['node'],r['name']):r['default'] for r in self.records if r['status']=='implemented'}
        self.assertEqual(actual,documented)

    def test_all_message_fields_documented(self):
        doc=(ROOT/'docs/TOPIC_FIELD_CONTRACTS_KO.md').read_text(encoding='utf-8')
        for source in (ROOT/'src/alatus_interfaces/msg').glob('*.msg'):
            expected=[]
            for line in source.read_text().splitlines():
                words=line.split('#')[0].split()
                if words: expected.append({'name':words[1],'type':words[0]})
            recorded=json.loads((ROOT/'design/interfaces'/f'{source.stem}.json').read_text())
            self.assertEqual(recorded['fields'],expected)
            for field in expected:
                self.assertIn('| '+field['name']+' | '+field['type']+' |',doc)

    def test_registry_completeness_and_uniqueness(self):
        keys=set()
        for r in self.records:
            key=(r['node'],r['name'])
            self.assertNotIn(key,keys)
            keys.add(key)
            self.assertEqual(set(r),{'node','name','type','default','unit','allowed','mutability','status','purpose','verification'})
            self.assertIn(r['status'],['implemented','framework','proposed_not_implemented'])
            self.assertIn(r['type'],['bool','int64','float64','string'])
            for field in ['allowed','mutability','purpose','verification']:
                self.assertTrue(r[field])
        self.assertEqual({n for n,p in keys},set(SPECS))

    def test_design_cannot_enable_control(self):
        for r in self.records:
            self.assertNotIn(r['name'],{'enable_control','control_allowed','arm_on_start'})
        registry_doc=(ROOT/'docs/IMPLEMENTED_PARAMETERS_V03_KO.md').read_text(encoding='utf-8')
        for r in self.records:
            if r['status']!='framework': self.assertIn('| '+r['name']+' |',registry_doc)
