"""Explicit read-only telemetry contract; no automatic 'latest' selection."""
import hashlib
import json
import re
from pathlib import Path

REQUIRED_FIELDS={'timestamp':'uint64','arming_state':'uint8','failsafe':'boolean','nav_state':'uint8'}

def load_profile(path):
    if not path: raise ValueError('contract_profile_path is required')
    raw=Path(path).read_bytes()
    if len(raw)>16384: raise ValueError('Oversize compatibility profile')
    profile=json.loads(raw)
    if not isinstance(profile,dict): raise ValueError('Profile must be an object')
    return profile

def validate_profile(config,profile,message_version,fields,armed_constant,message_definition):
    if type(profile.get('schema_version')) is not int or profile.get('schema_version')!=1 or profile.get('reviewed') is not True or config['contract_reviewed'] is not True:
        raise ValueError('Compatibility review incomplete')
    if profile.get('message_type')!='px4_msgs/msg/VehicleStatus': raise ValueError('Wrong profile message type')
    if not config['firmware_tag'] or config['firmware_tag'] in ['latest','main','master','nightly']:
        raise ValueError('An explicit firmware version is required')
    for key in ['firmware_tag','px4_msgs_ref','firmware_commit_sha','px4_msgs_commit_sha','expected_message_version']:
        if key not in profile or profile[key]!=config[key]: raise ValueError('Profile mismatch: '+key)
    if type(profile['expected_message_version']) is not int: raise ValueError('Invalid profile message version type')
    for key in ['firmware_commit_sha','px4_msgs_commit_sha']:
        if not re.fullmatch('[0-9a-fA-F]{40}',config[key]): raise ValueError('Full commit SHA required')
    if type(message_version) is not int or message_version!=config['expected_message_version']:
        raise ValueError('Generated MESSAGE_VERSION mismatch')
    if profile.get('required_fields')!=REQUIRED_FIELDS:
        raise ValueError('Adapter field types changed; review implementation')
    if any(fields.get(key)!=kind for key,kind in REQUIRED_FIELDS.items()): raise ValueError('Generated field type mismatch')
    if type(armed_constant) is not int or armed_constant!=profile.get('armed_constant'):
        raise ValueError('Arming enum mismatch')
    expected_hash=profile.get('vehicle_status_msg_sha256','')
    if not re.fullmatch('[0-9a-f]{64}',expected_hash): raise ValueError('Reviewed message definition SHA256 required')
    if hashlib.sha256(message_definition).hexdigest()!=expected_hash:
        raise ValueError('Installed VehicleStatus.msg differs from reviewed definition')
    suffix='' if message_version==0 else '_v'+str(message_version)
    if not config['status_topic'].endswith('/vehicle_status'+suffix): raise ValueError('Topic/version suffix mismatch')
    return True
