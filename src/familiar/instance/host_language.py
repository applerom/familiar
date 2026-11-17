# START_MODULE_CONTRACT: MOD-HOST-LANGUAGE
# PURPOSE: Resolve private working prose and host wording from the family's language pack.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - missing host wording never silently falls back to another language [review: engine lead]
# - exact dates and elapsed integer days use the selected pack's forms [review: cold reviewer]
# - private prose never becomes a reader publication [review: engine lead]
# - word-shaped ids in prose survive; explicit references are hidden without suppressing other text [review: engine lead]
# - numeric dates, folio fractions and slash years remain ordinary historical prose [review: engine lead]
# - one compiled identifier matcher preserves exact token boundaries across fragments and the final surface [review: engine lead]
# CHANGES_WITH:
# - regions/demo-english/pack.toml (host template keys)
# - regions/pl/pack.toml (host template keys)
# - regions/ru/pack.toml (host template keys)
# - MOD-RULES-SETTINGS-DATA (host.address)
# - MOD-REGION-CONTRACT (host_format and address overrides)
# - MOD-PUBLICATION (host text declaration)
# :END_MODULE_CONTRACT
import re
from datetime import date
from string import Formatter

from familiar.checks.engine import _known_people, life_status, load

from .publication import plain_text


class LanguageGap(ValueError):
    pass


class HostWords:
    def __init__(self, instance):
        from familiar.rules.cascade import Registry
        from familiar.rules.roles import method_root
        self.tag = instance.source_language
        pack = instance.language_pack_data.get(self.tag, {}).get('data', {})
        self.format = pack.get('host_format', {})
        self.address = Registry(method_root() / 'rules', instance).resolve_setting(
            'host.address', 'language:' + self.tag).value
        self.words = dict(pack.get('host', {}))
        if self.address not in self.format.get('address_forms', []):
            raise LanguageGap(f'Language pack gap ({self.tag}): host.address {self.address}; no host text produced.')
        self.words.update(pack.get('host_' + self.address, {}))

    def days(self, count):
        return self('days_' + self.plural(count), days=count)

    def number(self, noun, count):
        return self(noun + '_' + self.plural(count), count=count)

    def plural(self, count):
        for rule in self.format.get('plurals', []):
            value = count % rule['modulo'] if rule.get('modulo') else count
            if value in rule['values'] and count % 100 not in rule.get('except_mod100', []):
                return rule['category']
        category = self.format.get('plural_default')
        if not category:
            raise LanguageGap(f'Language pack gap ({self.tag}): host_format.plurals.')
        return category

    def date(self, value):
        if isinstance(value, dict):
            value = value.get(self.tag, '')
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            return value
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return value  # Do not reinterpret an invalid or approximate family date.
        months = self.format.get('months', [])
        if len(months) != 12:
            raise LanguageGap(f'Language pack gap ({self.tag}): host_format.months.')
        return self('date', day=parsed.day, month=months[parsed.month - 1], year=parsed.year)

    def __call__(self, key, **values):
        template = self.words.get(key)
        if not isinstance(template, str) or not template.strip():
            raise LanguageGap(f'Language pack gap ({self.tag}): host.{key}; no host text produced.')
        expected = {field for _, field, _, _ in Formatter().parse(template) if field is not None}
        if expected != set(values) or any('.' in f or '[' in f for f in expected):
            raise LanguageGap(f'Language pack gap ({self.tag}): invalid host.{key} placeholders.')
        try:
            return plain_text(template.format(**values))
        except (KeyError, ValueError) as exc:
            raise LanguageGap(f'Language pack gap ({self.tag}): invalid host.{key}.') from exc


class HostData:
    """Private snapshot reader; only gate.publication may deliver its result."""
    def __init__(self, instance):
        self.instance, self.words = instance, HostWords(instance)
        self.used_people, self.used_records = {}, set()
        self.hidden = False
        self.people = _known_people(instance)
        privacy = load(instance.path('privacy'), {})
        self.living = {pid for pid, p in self.people.items() if life_status(p, privacy) != 'dead'}
        self.unknown = {pid for pid, p in self.people.items() if life_status(p, privacy) == 'unknown'}
        self.ids = set(self.people)
        self.id_locations = {pid: instance.path('tree_snapshot') / 'people.json'
                             for pid in self.people}
        self.rows = {key: self._rows(key) for key in
                     ('questions', 'answers', 'versions', 'cases', 'memory', 'records', 'correspondence')}
        for name in ('people', 'families'):
            path = instance.path('tree_snapshot') / (name + '.json')
            self._ids(load(path, {}), path)
        for folder in instance.path('feeds').glob('*'):
            for name in ('feed', 'chapters', 'documents', 'pictures'):
                path = folder / (name + '.json')
                value = load(path, {})
                self._ids(value, path)
                if name == 'feed':
                    for ident in value.get('persons', {}):
                        self.ids.add(ident)
                        self.id_locations[ident] = path
        self.internal_ids = re.compile(r'(?<![\w-])(?:'
                                       + '|'.join(re.escape(ident) for ident in sorted(self.ids))
                                       + r')(?![\w-])') if self.ids else re.compile(r'(?!)')

    def _rows(self, key):
        path = self.instance.path(key)
        if not path.exists():
            return []
        values = []
        for source in sorted(path.rglob('*.json')) if path.is_dir() else [path]:
            value = load(source, {})
            self._ids(value, source)
            values.append(value)
        return [row for value in values for row in (value if isinstance(value, list) else [value])]

    def _ids(self, value, path):
        if isinstance(value, dict):
            if isinstance(value.get('id'), str):
                self.ids.add(value['id'])
                self.id_locations[value['id']] = path
            for child in value.values():
                self._ids(child, path)
        elif isinstance(value, list):
            for child in value:
                self._ids(child, path)

    def text(self, value, subjects=()):
        if isinstance(value, dict):
            value = value.get(self.instance.source_language, '')
        if not isinstance(value, str):
            return ''
        value = plain_text(value).strip()
        value = self._check_ids(self._locators(value))
        for pid in set(subjects) & self.people.keys():
            self.used_people.setdefault(pid, set()).add('prose')
        return value

    def name(self, ident):
        if ident in {'host', 'relative'}:
            return self.words(ident)
        if ident in self.people:
            # Names alone are permitted; never treat a raw id as a name.
            value = self.people[ident].get('name', '')
            self.used_people.setdefault(ident, set()).add('name')
            return plain_text(value) if isinstance(value, str) and value not in self.ids else self.words('relative')
        return self.text(ident) or self.words('relative')

    def call_as(self, request):
        return self.personal_name(request.get('call_as'), request.get('addressee'))

    def personal_name(self, value, ident=None):
        # Like name(), this is explicitly a name, never arbitrary subject prose.
        # The final surface still rejects internal identifiers and paths.
        if isinstance(value, str) and value.strip():
            if ident in self.people:
                self.used_people.setdefault(ident, set()).add('name')
            for pid, person in self.people.items():
                if value == person.get('name'):
                    self.used_people.setdefault(pid, set()).add('name')
            return plain_text(value).strip()
        return ''

    def find(self, key, ident):
        return next((row for row in self.rows[key] if row.get('id') == ident), {})

    def subjects(self, row):
        from .subjects import explicit_subjects
        ids = set(explicit_subjects(row))
        ids.update(p for p in row.get('people', []) if isinstance(p, str))
        return ids

    def _check_ids(self, text):
        def replace(match):
            ident = match.group()
            before, after = text[:match.start()], text[match.end():]
            delimited = (before[-1:] in ('`', '@', '#', '/', '\\', '[', '{') or
                         after[:1] in ('`', '@', '/', '\\', ']', '}'))
            typed = re.search(r'(?i)\b(?:id|person|people|version|question|case|record|source|'
                              r'человек|версия|версии|вопрос|дело|запись|источник)\s*[=:№#]?\s*[\"\x27]?$', before)
            if ident.isalpha() and not (delimited or typed):
                return ident
            self.hidden = True
            return self.words('internal_hidden')
        return self.internal_ids.sub(replace, text)

    def _locators(self, text):
        def replace(match):
            # Numeric calendar/folio notation is prose, even when it contains slashes.
            if re.fullmatch(r'\d+(?:[./\\–—-](?:\d+|[IVXLCDM]+))+(?:[rv]|об)?\.?', match.group(), re.IGNORECASE):
                return match.group()
            self.hidden = True
            return self.words('internal_hidden')
        return re.sub(r'@I\d+@|\b\w+_\w+\b|[A-Za-z]:[\\/]\S*|'
                      r'(?:[\w.-]+[\\/])+[\w.-]+|\b[\w.-]+\.(?:jsonl?|toml|md|jpg|png)\b', replace, text)

    def finish(self, text):
        # Recheck the final surface, including pack wording, not just input fragments.
        plain_text(text)
        text = self._check_ids(self._locators(text))
        if self.hidden:
            text += '\n\n' + self.words('internal_notice')
        return text

    def uses(self, view):
        uses = [{'item': 'host:' + view, 'person': pid, 'field': field,
                 'permission': None}
                for pid, fields in sorted(self.used_people.items()) for field in sorted(fields)]
        uses.extend({'item': 'host:' + view, 'person': None, 'field': 'document', 'record': rid}
                    for rid in sorted(self.used_records))
        return uses
