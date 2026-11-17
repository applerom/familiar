# START_MODULE_CONTRACT: MOD-ARCHIVE-RIGHTS
# PURPOSE: Resolve a family's archive declaration without treating ownership as a subject's consent.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - archive defaults never cover a different provider or living-person consent [review: engine lead]
# - malformed declarations cannot supply photograph rights [review: engine lead]
# CHANGES_WITH:
# - MOD-INSTANCE-VALIDATION
# - MOD-CHECKS-ENGINE
# - MOD-FEED-SERVICE
# :END_MODULE_CONTRACT
import json
from datetime import date


def declaration(instance):
    path = instance.path('archive_rights')
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(value, dict) or type(value.get('schema_version')) is not int or
            value['schema_version'] != 1 or value.get('kind') != 'family-photograph'):
        raise ValueError('archive declaration needs schema_version=1 and kind=family-photograph')
    for key in ('holder', 'declared_by', 'declared_at', 'effective_from'):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ValueError('archive declaration needs ' + key)
    for key in ('declared_at', 'effective_from'):
        date.fromisoformat(value[key])
    permissions = value.get('permissions')
    if (not isinstance(permissions, dict) or
            set(permissions) != {'family_app', 'processing', 'colourisation'} or
            any(type(v) is not bool for v in permissions.values())):
        raise ValueError('archive permissions must declare family_app, processing and colourisation as booleans')
    if value.get('living_subject_consent') is not False:
        raise ValueError('archive ownership does not grant living subject consent')
    return value


def photograph_rights(instance, image):
    if image.get('kind') != 'family-photograph':
        return None
    # A specific holder/provider/rights decision always wins over the default.
    if any(key in image for key in ('holder', 'received_from', 'rights')):
        return {'holder': image.get('holder'),
                'permissions': image.get('rights', {'family_app': bool(image.get('holder'))})}
    value = declaration(instance)
    return value if value and date.fromisoformat(value['effective_from']) <= date.today() else None
