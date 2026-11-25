import copy
import hashlib
import unittest
from alatus_runtime.parameters import defaults
from alatus_runtime.compatibility import REQUIRED_FIELDS,validate_profile

class CompatibilityTests(unittest.TestCase):
    def example(self,version='v1.17.0',reference='release/1.17'):
        definition=b'uint64 timestamp\nuint8 arming_state\nbool failsafe\nuint8 nav_state\n'
        config=defaults('px4_status')
        config.update(firmware_tag=version,px4_msgs_ref=reference,contract_reviewed=True,
                      firmware_commit_sha='a'*40,px4_msgs_commit_sha='b'*40)
        profile={k:config[k] for k in ['firmware_tag','px4_msgs_ref','firmware_commit_sha','px4_msgs_commit_sha','expected_message_version']}
        profile.update(schema_version=1,reviewed=True,message_type='px4_msgs/msg/VehicleStatus',
                       required_fields=dict(REQUIRED_FIELDS),armed_constant=2,
                       vehicle_status_msg_sha256=hashlib.sha256(definition).hexdigest())
        return config,profile,definition

    def test_explicit_profile_supports_selected_versions(self):
        for version,ref in [('v1.16.0','release/1.16'),('v1.17.0','release/1.17')]:
            c,p,d=self.example(version,ref)
            self.assertTrue(validate_profile(c,p,1,REQUIRED_FIELDS,2,d))

    def test_no_automatic_latest_or_unreviewed_profile(self):
        for mutation in ['reviewed','latest','sha','schema']:
            c,p,d=self.example()
            if mutation=='reviewed': p['reviewed']=False
            elif mutation=='latest': c['firmware_tag']=p['firmware_tag']='latest'
            elif mutation=='sha':p['px4_msgs_commit_sha']='c'*40
            else:p['schema_version']=True
            with self.assertRaises(ValueError):validate_profile(c,p,1,REQUIRED_FIELDS,2,d)

    def test_definition_field_enum_and_version_mismatch(self):
        c,p,d=self.example()
        for version,fields,armed,definition in [(2,REQUIRED_FIELDS,2,d),(1,{**REQUIRED_FIELDS,'nav_state':'uint16'},2,d),
                                               (1,REQUIRED_FIELDS,3,d),(1,REQUIRED_FIELDS,2,d+b'# changed')]:
            with self.assertRaises(ValueError):validate_profile(c,p,version,fields,armed,definition)

    def test_topic_suffix_must_match_profile(self):
        c,p,d=self.example();c['status_topic']='/fmu/out/vehicle_status'
        with self.assertRaises(ValueError):validate_profile(c,p,1,REQUIRED_FIELDS,2,d)
