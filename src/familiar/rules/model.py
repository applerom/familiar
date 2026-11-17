# START_MODULE_CONTRACT: MOD-RULES-MODEL
# PURPOSE: Load the engine's rule and setting records and refuse data that breaks the declared shape, so every later decision starts from a valid registry.
# PRD_REF: docs/PRD.md#RULES-MODEL
# INVARIANTS:
# - a rule's default mode is one its kind allows [review: engine lead]
# - trust rules live only in trust.toml, other kinds only in catalog.toml [review: engine lead]
# - a rule cannot read a setting the registry does not declare [review: engine lead]
# - a setting's default has its declared type [review: engine lead]
# - executable rule/setting types stay valid; role spelling is not a family gate [review: engine lead]
# - privacy values are validated; invalid presentation values fall back without blocking a family [review: engine lead]
# - rule-file edits are observed and caller mutations never contaminate another load [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#RULES-MODEL (field names and what each kind allows)
# - MOD-RULES-ROLES (role vocabulary and shipped sheets)
# - MOD-RULES-TRUST-DATA (loaded by file name)
# - MOD-RULES-CATALOG-DATA (loaded by file name)
# - MOD-RULES-SETTINGS-DATA (loaded by file name)
# - pyproject.toml (method resource packaging)
# :END_MODULE_CONTRACT
import re
import tomllib
from copy import deepcopy
from functools import lru_cache
from pathlib import Path




class RulesError(ValueError):
    pass


MODES = {'trust': {'block'}, 'craft': {'advise', 'off'},
         'taste': {'block', 'advise', 'off'}, 'process': {'block', 'advise', 'off'}}
TYPES = {'string': str, 'integer': int, 'float': float, 'boolean': bool,
         'array': list, 'table': dict}


@lru_cache(maxsize=64)
def _parse(content):
    return tomllib.loads(content.decode('utf-8'))


def read(path):
    # Cache parsing, never filesystem reads or a caller's mutable records.
    return deepcopy(_parse(Path(path).read_bytes()))


def require(condition, message):
    if not condition:
        raise RulesError(message)


def scope_valid(scope):
    return isinstance(scope, str) and re.fullmatch(
        r'(?:language:[A-Za-z0-9-]+|feed:[^/\s]+(?:/(?:chapter:[0-9]+|item:[^/\s]+))?(?:/language:[A-Za-z0-9-]+)?)', scope)


def check_value(setting, value):
    from familiar.check_policy import decision
    if decision('setting:' + setting['id']) == 'block':
        _typed_value(setting, value)


def presentation_value(setting, value):
    """Use a safe default for malformed presentation preferences, without findings."""
    from familiar.check_policy import decision
    if decision('setting:' + setting['id']) == 'block':
        return value
    try:
        _typed_value(setting, value)
    except (RulesError, TypeError, ValueError):
        return deepcopy(setting['default'])
    return value


def _typed_value(setting, value):
    require(type(value) is TYPES[setting['type']], f"wrong type for {setting['id']}")
    for bound, compare in (('minimum', lambda a, b: a >= b),
                           ('maximum', lambda a, b: a <= b)):
        if bound in setting:
            require(setting['type'] in ('integer', 'float') and
                    type(setting[bound]) is TYPES[setting['type']], 'invalid numeric bound')
            require(compare(value, setting[bound]), f"{setting['id']} outside {bound}")
    if 'choices' in setting:
        require(value in setting['choices'], f"invalid choice for {setting['id']}")
    if 'item_choices' in setting:
        require(setting['type'] == 'array' and all(x in setting['item_choices'] for x in value),
                f"invalid item for {setting['id']}")


def load_engine(directory):
    rules = {}
    for filename in ('trust.toml', 'catalog.toml'):
        for rule in read(Path(directory) / filename).get('rule', []):
            require(isinstance(rule, dict), 'rule must be a table')
            for key in ('id', 'kind', 'statement', 'roles', 'serves', 'check', 'mode', 'reads'):
                require(key in rule, f'missing rule field {key}')
            for key in ('id', 'kind', 'statement', 'serves', 'mode'):
                require(isinstance(rule[key], str), f'rule {key} must be a string')
            checks = [rule['check']] if isinstance(rule['check'], str) else rule['check']
            require(isinstance(checks, list) and all(
                isinstance(x, str) and (not x or x.startswith(('check:', 'review:')))
                for x in checks), 'rule check must be check:<id> or review:<role>, or a list of them')
            for key in ('roles', 'reads'):
                require(isinstance(rule[key], list) and all(isinstance(x, str) for x in rule[key]),
                        f'rule {key} must be a string array')
            require(rule['id'] not in rules, f"duplicate rule {rule['id']}")
            require(rule['kind'] in MODES, 'unknown rule kind')
            require(rule['mode'] in MODES[rule['kind']], 'mode forbidden for kind')
            require((filename == 'trust.toml') == (rule['kind'] == 'trust'),
                    'trust rules belong only in trust.toml')
            rules[rule['id']] = rule
    settings = read(Path(directory) / 'settings.toml').get('setting', {})
    for ident, setting in settings.items():
        require(setting.get('id', ident) == ident, 'setting id differs from table key')
        setting['id'] = ident
        for key in ('type', 'default', 'help', 'serves', 'scopes'):
            require(key in setting, f'missing setting field {key}')
        require(setting['type'] in TYPES, 'unknown setting type')
        require(isinstance(setting['scopes'], list) and
                all(x in ('language', 'region', 'family', 'feed') for x in setting['scopes']),
                'invalid setting scopes')
        _typed_value(setting, setting['default'])
    for rule in rules.values():
        require(all(x in settings for x in rule['reads']), 'rule reads undeclared setting')
    return rules, settings
