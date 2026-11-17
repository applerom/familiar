# START_MODULE_CONTRACT: MOD-RULES-EXCEPTIONS
# PURPOSE: Make "this rule does not apply here, because" a record instead of a workaround, and turn repeated exceptions into a signal about the check.
# PRD_REF: docs/PRD.md#SETTINGS
# INVARIANTS:
# - an exception without a reason is refused on write and on load [review: engine lead]
# - exceptions reaching the configured alarm for one rule are reported as a probably wrong check [review: engine lead]
# - a trust text-review dismissal never changes a data finding or rule mode [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (declared reader surfaces and default-deny policy)
# - MOD-FAMILY-WRITER (the sole filesystem and generation boundary)
# - docs/PRD.md#RULES-MODEL (exception fields)
# :END_MODULE_CONTRACT
import json
from collections import Counter
from datetime import date

from familiar.instance.gate import boundary

from .model import require


@boundary('writer')
def waive(registry, rule, scope, reason, by=None):
    require(registry.root is not None, 'waive requires a family root')
    entry = {'rule': rule, 'scope': scope, 'reason': reason, 'date': date.today().isoformat(),
                 'by': by or 'host'}
    if registry.rules.get(rule, {}).get('kind') == 'trust':
        entry['kind'] = 'text-review'
    registry.validate_exception(entry)
    text = '\n[[exception]]\n' + ''.join(
        f'{key} = {json.dumps(value, ensure_ascii=False)}\n' for key, value in entry.items())
    from familiar.instance.writer import legacy_exception, mutate
    path = registry.root / 'exceptions.toml'
    previous = path.read_bytes() if path.exists() else b''
    if 'schema_version' not in registry.instance.config:
        legacy_exception(registry, text)
    else:
        mutate(registry.instance, {path: previous + text.encode('utf-8')})
    registry.exceptions.append(entry)
    return entry


def report(registry):
    return [{'rule': rule, 'count': count,
             'assessment': 'the check is probably wrong' if count >= registry.resolve_setting('rules.exception_alarm').value else ''}
            for rule, count in sorted(Counter(e['rule'] for e in registry.exceptions).items())]
