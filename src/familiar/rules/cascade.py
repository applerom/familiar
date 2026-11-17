# START_MODULE_CONTRACT: MOD-RULES-CASCADE
# PURPOSE: Decide the effective value of a setting or mode of a rule for a scope from engine, language, region, family, feed and exception, and say which layer decided.
# PRD_REF: docs/PRD.md#SETTINGS
# INVARIANTS:
# - no layer or exception can change a mandatory trust mode; text-review dismissals affect cues only [test: tests/gate/test_data_guarantees.py::test_f9_trust_mode_cannot_be_changed]
# - privacy settings and trust modes stay strict; malformed presentation preferences use engine defaults [review: engine lead]
# - a craft rule cannot be raised to block [review: engine lead]
# - every resolution carries the chain of layers, engine first, winner last [review: engine lead]
# - feed tables win over base tables; on one level the region is applied before the family [review: engine lead]
# - a language pack applies only to explicitly tagged text [review: engine lead]
# - family preferred words default to the source language and explicit language tables win [review: engine lead]
# - regular surname inflection requires an explicit class and gender [review: engine lead]
# CHANGES_WITH:
# - MOD-RULES-MODEL (record fields)
# - docs/PRD.md#RULES-MODEL (layer tables, scope syntax)
# - docs/PRD.md#ARCH (the names familiar.toml, pack.toml, exceptions.toml)
# :END_MODULE_CONTRACT
from dataclasses import dataclass
from datetime import date

from familiar.instance.model import Instance

from .model import MODES, check_value, load_engine, presentation_value, read, require, scope_valid


@dataclass(frozen=True)
class Resolution:
    value: object
    layer: str
    chain: list


class Registry:
    def __init__(self, engine, root=None):
        self.engine = engine
        self.rules, self.settings = load_engine(engine)
        self.instance = (root if isinstance(root, Instance) else
                         Instance(root, legacy_rules=True)) if root else None
        self.root = self.instance.root if self.instance else None
        self.layers = []
        self.exceptions = []
        if self.root:
            config = self.instance.config
            for tag, pack in self.instance.language_pack_data.items():
                self._layer(f'language:{tag}', 'language', pack['data'])
            for index, pack in enumerate(self.instance.packs):
                self._layer(f"region:{index}:{pack['id']}", 'region', pack['data'])
            self._layer('family', 'family', config)
            path = self.root / 'exceptions.toml'
            if path.exists():
                self.exceptions = read(path).get('exception', [])
                require(isinstance(self.exceptions, list), 'exception must be an array')
                for entry in self.exceptions:
                    self.validate_exception(entry)

    def _layer(self, name, kind, data):
        self._validate(kind, data)
        self.layers.append((name, None, data))
        for tag, values in data.get('language_settings', {}).items():
            require(scope_valid(f'language:{tag}'), 'invalid settings language')
            self._validate(kind, {'settings': values})
        feeds = data.get('feed', {})
        require(isinstance(feeds, dict), 'feed must be a table')
        for feed, values in feeds.items():
            require(scope_valid(f'feed:{feed}'), 'invalid feed id')
            self._validate('feed', values)
            for tag, settings in values.get('language_settings', {}).items():
                require(scope_valid(f'language:{tag}'), 'invalid settings language')
                self._validate('feed', {'settings': settings})
            self.layers.append((name + f'/feed:{feed}', f'feed:{feed}', values))

    def _validate(self, kind, data):
        from familiar.check_policy import decision
        require(isinstance(data, dict), 'layer must be a table')
        for table in ('settings', 'modes'):
            require(isinstance(data.get(table, {}), dict), f'{table} must be a table')
        for ident, value in data.get('settings', {}).items():
            if ident not in self.settings:
                continue
            require(ident in self.settings, f'undeclared setting {ident}')
            setting = self.settings[ident]
            if decision('setting:' + ident) == 'block':
                require(kind in setting['scopes'], f'{ident} cannot be set by {kind}')
            check_value(setting, value)
            if self.instance and ident in {
                'privacy.closed_topics_file', 'privacy.present_day_politics_file'
            }:
                self.instance.data_file(value)
        for ident, mode in data.get('modes', {}).items():
            if ident not in self.rules:
                continue
            require(ident in self.rules, f'undeclared rule {ident}')
            rule = self.rules[ident]
            require(rule['kind'] != 'trust', f'trust rule {ident} cannot be touched')

    def validate_exception(self, entry):
        require(isinstance(entry, dict), 'exception must be a table')
        for field in ('rule', 'scope', 'reason', 'date', 'by'):
            require(field in entry and str(entry[field]).strip(), f'exception needs {field}')
        require(all(isinstance(entry[x], str) for x in ('rule', 'scope', 'reason', 'by')),
                'exception fields must be text')
        try:
            date.fromisoformat(str(entry['date']))
        except ValueError:
            require(False, 'exception date must be an ISO date')
        require(entry['rule'] in self.rules, 'exception names undeclared rule')
        if self.rules[entry['rule']]['kind'] == 'trust':
            from familiar.checks.language import CHECKS, SUPPLEMENTS
            check = str(self.rules[entry['rule']]['check']).removeprefix('check:')
            require(entry.get('kind') == 'text-review' and
                    check in CHECKS | SUPPLEMENTS | {'closed-topics-and-politics'},
                    'trust cannot be waived; only a text-review cue can be dismissed')
        require(scope_valid(entry['scope']), 'invalid exception scope')
        require(isinstance(entry['reason'], str), 'reason must be text')

    def _resolve(self, ident, table, scope):
        if scope is not None:
            require(scope_valid(scope), 'invalid resolution scope')
        records = self.settings if table == 'settings' else self.rules
        require(ident in records, f'undeclared id {ident}')
        value = records[ident]['default' if table == 'settings' else 'mode']
        chain = [{'layer': 'engine', 'value': value}]
        # All base layers precede all feed layers, irrespective of pack order.
        for scoped in (False, True):
            for name, target, data in self.layers:
                if name.startswith('language:') and name.split('/', 1)[0] not in (scope or '').split('/'):
                    continue
                if bool(target) != scoped:
                    continue
                if target and not (scope == target or (scope or '').startswith(target + '/')):
                    continue
                if ident in data.get(table, {}):
                    tag = next((p[9:] for p in (scope or '').split('/') if p.startswith('language:')), None)
                    foreign_terms = (table == 'settings' and ident == 'lang.preferred_terms'
                            and not name.startswith('language:') and tag
                            and self.instance and tag != self.instance.source_language)
                    if not foreign_terms:
                        value = data[table][ident]
                        if table == 'settings':
                            value = presentation_value(records[ident], value)
                        elif not isinstance(value, str) or value not in MODES[records[ident]['kind']]:
                            value = records[ident]['mode']
                        chain.append({'layer': name, 'value': value})
                if table == 'settings':
                    tag = next((p[9:] for p in (scope or '').split('/') if p.startswith('language:')), None)
                    localized = data.get('language_settings', {}).get(tag, {})
                    if ident in localized:
                        chain.append({'layer': name + f'/language:{tag}',
                                      'value': presentation_value(records[ident], localized[ident])})
        if table == 'modes':
            matches = [e for e in self.exceptions if e.get('kind') != 'text-review' and e['rule'] == ident and
                       (scope == e['scope'] or (scope or '').startswith(e['scope'] + '/'))]
            for entry in sorted(matches, key=lambda e: e['scope'].count('/')):
                chain.append({'layer': 'exception', 'value': 'off', 'exception': entry})
        return Resolution(chain[-1]['value'], chain[-1]['layer'], chain)

    def language_data(self, scope):
        """Language-pack word lists and forms; no family-relative lexicon path."""
        require(scope_valid(scope), 'invalid resolution scope')
        tag = next((part[9:] for part in scope.split('/') if part.startswith('language:')), None)
        pack = self.instance.language_pack_data.get(tag) if self.instance else None
        return pack['data'].get('language', {}) if pack else {}

    def surname_form(self, surname, gender, paradigm, case, scope):
        """Inflect an explicitly selected regular class; never infer identity or gender."""
        import re
        data = self.language_data(scope)
        order = data.get('surnames', {}).get('case_order', [])
        for form in data.get('surname_forms', []):
            if form['id'] == paradigm and form['gender'] == gender and case in order:
                match = re.search(form['pattern'], surname)
                if match:
                    return surname[:match.start()] + form['suffixes'][order.index(case)]
        return surname

    def resolve_setting(self, ident, scope=None):
        return self._resolve(ident, 'settings', scope)

    def rule_mode(self, ident, scope=None):
        return self._resolve(ident, 'modes', scope)

    def text_exception(self, ident, scope):
        matches = [e for e in self.exceptions if e['rule'] == ident and
                   (scope == e['scope'] or scope.startswith(e['scope'] + '/'))]
        return max(matches, key=lambda e: e['scope'].count('/'), default=None)
