"""Shared check weights; an unregistered check can only advise."""
# START_MODULE_CONTRACT: MOD-CHECK-POLICY
# PURPOSE: Give tests, runtime findings and release checks one value-based blocking policy.
# PRD_REF: docs/PRD.md#DOD
# INVARIANTS:
# - only registered core data/privacy/install checks and the single journey block [review: engine lead]
# - missing weights advise without granting a new blocking requirement [review: engine lead]
# CHANGES_WITH:
# - src/familiar/check-weights.json (weights and core file ownership)
# - MOD-FAMILY-GATE (finding modes)
# :END_MODULE_CONTRACT
import json
from fnmatch import fnmatchcase
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def registry():
    return json.loads(Path(__file__).with_name('check-weights.json').read_text(encoding='utf-8'))


def weight(check):
    return registry()['checks'].get(check)


def decision(check):
    record = weight(check)
    if record is None:
        return 'advise'
    if check == 'pytest.size' and record.get('blocking_exception') == 'test-size':
        return 'block'
    if record.get('removed'):
        return 'delete'
    if record.get('advisory_exception'):
        return 'advise'
    if record['guards'] == 'journey':
        return 'block' if check == registry()['journey'] else 'delete'
    if record['base'] == 'core' and record['guards'] in {'data', 'privacy', 'install'}:
        return 'block'
    return 'advise' if record.get('build_reference') else 'delete'


def is_core(path):
    return any(fnmatchcase(path, pattern) for pattern in registry()['core_paths'])


def finding(row, check):
    """Attach the weight without turning semantic judgements into data failures."""
    record = weight(check)
    return dict(row, weight=check, guards=record['guards'] if record else None,
                mode='block' if decision(check) == 'block' and row.get('certainty') == 'finding'
                else 'advise')
