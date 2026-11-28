# START_MODULE_CONTRACT: MOD-INTAKE-TABLE
# PURPOSE: Prepare a private, editable memory telling and complete cell ledger before table acceptance.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - preparation retains literal kin words separately from graph-derived relationships and accounts for every nonempty cell [review: engine lead]
# - dictionary paths create bridges; named kin hypotheses remain explicitly removable and never merge identity [review: engine lead]
# CHANGES_WITH:
# - MOD-INTAKE-CORE
# - MOD-INTAKE-SHEET
# - MOD-FAMILY-WRITER
# - regions/ru/pack.toml
# - regions/pl/pack.toml
# - regions/demo-english/pack.toml
# :END_MODULE_CONTRACT
import hashlib
import json
import re
import tomllib
from collections import defaultdict
from datetime import date as calendar_date

from familiar.instance.gate import boundary
from familiar.instance.packs import bundled_root
from familiar.instance.writer import mutate

from .core import safe, token
from .layers import CELLS, ROLES
from .sheet import cells
from .table_review import bridge_label, describe, enrich


def toml(data):
    """Small encoder for this JSON-shaped memory form, including nested arrays."""
    def value(v):
        if isinstance(v, dict):
            return '{' + ', '.join(json.dumps(k) + '=' + value(x) for k, x in v.items()) + '}'
        if isinstance(v, list):
            return '[' + ', '.join(value(x) for x in v) + ']'
        return json.dumps(v, ensure_ascii=False)
    lines = []
    # Root scalars must precede [[tables]]; otherwise TOML binds them to the last row.
    for key, v in sorted(data.items(), key=lambda pair: bool(isinstance(pair[1], list) and pair[1] and isinstance(pair[1][0], dict))):
        if isinstance(v, list) and v and isinstance(v[0], dict):
            for row in v:
                lines += ['', '# ' + row.get('cell', row.get('id', key)), '[[' + key + ']]']
                lines += [k + '=' + value(x) for k, x in row.items()]
        else:
            lines.append(key + '=' + value(v))
    return ('\n'.join(lines) + '\n').encode('utf-8')


def exact_date(text, pack):
    text = text.strip()
    if re.fullmatch(r'\d{4}', text):
        return text
    match = re.fullmatch(r'(\d{4})\s*\([^?]*\)', text)
    if match:
        return match[1]
    match = re.fullmatch(r'(\d{1,2})\s+(\w+)\s+(\d{4})(?:\s+года)?', text)
    if match and match[2].casefold() in pack.get('months', []):
        try:
            return calendar_date(int(match[3]), pack['months'].index(match[2].casefold()) + 1, int(match[1])).isoformat()
        except ValueError:
            return None
    try:
        return calendar_date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def doubtful(text):
    return bool(re.search(r'\?|\(\d|\b(?:около|примерно|about|circa)\b', text, re.IGNORECASE))


@boundary('writer')
def prepare(instance, path, ident, witness, date, language, mapping=None):
    token(ident)
    blob = path.read_bytes()
    rows = cells(blob, path.suffix)
    pack = instance.language_pack_data.get(language, {}).get('data', {}).get('table_intake', {})
    if not pack and language in {'ru', 'pl', 'en'}:
        ref = 'demo-english' if language == 'en' else language
        pack = tomllib.loads((bundled_root() / ref / 'pack.toml').read_text(encoding='utf-8'))['table_intake']
    if not pack:
        raise ValueError(f'Language pack has no table_intake: {language}')
    overrides = tomllib.loads(mapping.read_text(encoding='utf-8-sig')) if mapping else {}
    aliases = {s.casefold().strip(): k for k, names in pack['headers'].items() for s in names}
    paths = pack.get('kin_paths', {})
    data = {'id': ident, 'told_by': witness, 'date': date, 'table_sha256': hashlib.sha256(blob).hexdigest(),
            'items': [], 'people': [], 'families': [], 'blanks': []}
    report = {'format': 'Kin Sheet 1', 'status': 'draft', 'cells': [], 'questions': [], 'losses': [],
              'policy': 'Unambiguous parent/grandparent and no doubt: firm (assumed acquaintance); otherwise hearsay. Reviewer must check witness/strength.',
              'assumptions': ['First nonempty row of each sheet is the header; UTF-8 CSV/TSV.',
                              'Excel date display locale is assumed Russian for d mmmm yyyy.'],
              'variants': [], 'reviewer_hints': [], 'research_leads': [], 'life_status_candidates': []}
    words = pack['words']
    def ask(cell, key, **values):
        question = {'cell': cell, 'question': words[key].format(**values)}
        if question not in report['questions']:
            report['questions'].append(question)
    groups = defaultdict(list)
    for c in rows:
        groups[c['sheet']].append(c)
    kin_people, kin_basis = {}, {}
    for sheet, sheet_cells in groups.items():
        header_row = min(c['row'] for c in sheet_cells)
        roles = {}
        for c in sheet_cells:
            if c['row'] != header_row:
                continue
            role = overrides.get('columns', {}).get(sheet + '!' + c['col'])
            role = role or aliases.get(c['text'].casefold().strip())
            # Compound A/B headers can identify a person + relationship column.
            if not role:
                parts = [aliases.get(p.strip().casefold()) for p in c['text'].split('/')]
                if 'person' in parts and 'kin' in parts:
                    role = 'person_kin'
            roles[c['col']] = role or 'notes'
        roles.update({k.split('!')[-1]: v for k, v in overrides.get('columns', {}).items() if k.startswith(sheet + '!')})
        allowed = {'person', 'person_kin', 'kin', 'birth', 'death', 'birth_place', 'death_place', 'place', 'notes', 'witness', 'living'}
        for col, role in roles.items():
            if role not in allowed:
                report['losses'].append({'cell': sheet + '!' + col + str(header_row), 'reason': f'Invalid mapped role: {role}'})
        has_person = any(r in {'person', 'person_kin'} for r in roles.values())
        if not has_person:
            report['losses'].append({'cell': sheet, 'reason': 'No person column; supply --mapping columns."Sheet!A"="person"'})
        by_row = defaultdict(list)
        for c in sheet_cells:
            by_row[c['row']].append(c)
        footnotes = []
        for number, group in sorted(by_row.items()):
            if number == header_row:
                for c in group:
                    report['cells'].append({**c, 'outcome': 'loss', 'role': roles.get(c['col'], 'notes'), 'reason': 'Header, not a personal assertion'})
                continue
            person_cell = next((c for c in group if roles.get(c['col']) in {'person', 'person_kin'}), None)
            footnote = person_cell and person_cell['text'].lstrip().startswith('*')
            person = None
            kin = ''
            if person_cell and not footnote and has_person:
                name, _sep, kin = person_cell['text'].partition(' - ') if roles[person_cell['col']] == 'person_kin' else (person_cell['text'], '', '')
                kin_cell = next((c for c in group if roles.get(c['col']) == 'kin'), None)
                if kin_cell:
                    kin = kin_cell['text']
                person = {'id': f'p{len(data["people"]) + 1}', 'names': [], 'events': [], 'notes': []}
                data['people'].append(person)
                person['_name'] = name
                person['_kin'] = kin
                told = {roles.get(c['col']) for c in group if c['text'].strip() not in {'', '-'}}
                data['blanks'] += [{'person': person['id'], 'field': field} for role, field in CELLS.items()
                                   if role in roles.values() and role not in told]
            for c in group:
                if c['text'].strip() == '-':
                    report['cells'].append({**c, 'outcome': 'loss', 'reason': 'Dash means empty, not a memory assertion'})
                    continue
                item_id = f'{ident}-c{len(data["items"]) + 1}'
                role = roles.get(c['col'], 'notes')
                close = bool(paths.get(kin.casefold().strip()))
                strength = 'firm' if close and not doubtful(c['text']) and not footnote else 'hearsay'
                rule = 'close-kin-assumed-acquaintance' if strength == 'firm' else 'doubt-or-distant-or-unknown'
                row_witness = next((x['text'] for x in group if roles.get(x['col']) == 'witness' and x['text'].strip()), witness)
                item = {'id': item_id, 'text': c['text'] or c.get('formula') or c.get('link'),
                        'cell': c['address'], 'strength': strength, 'witness': row_witness,
                        'status': 'possible' if doubtful(c['text']) else 'reported', 'rule': rule}
                if not footnote and role in ROLES:
                    item['layers'] = [ROLES[role]]
                for key in ('raw_number', 'number_format', 'date', 'formula', 'link', 'display_gap', 'display_rule'):
                    if key in c:
                        item[key] = c[key]
                data['items'].append(item)
                ledger = {**c, 'outcome': 'assertion', 'item': item_id, 'role': role,
                          'strength': strength, 'rule': item['rule'], 'fields': []}
                report['cells'].append(ledger)
                if c.get('display_gap') or c.get('formula'):
                    report['losses'].append({'cell': c['address'], 'reason': c.get('display_gap', 'Formula not evaluated; cached value only')})
                if footnote:
                    footnotes.append(item)
                    report['variants'].append({'cell': c['address'], 'text': item['text']})
                if not person:
                    if not footnote:
                        report['questions'].append({'cell': c['address'], 'question': words['ask_person'].format(value=c['text'])})
                    continue
                prov = [item_id]
                item['person'] = person['id']
                item['role'] = role
                if role in {'person_kin', 'kin'} and person['_kin'].strip():
                    item['kinship'] = person['_kin'].strip()
                if role in {'person', 'person_kin'}:
                    name = person['_name']
                    maiden = re.search(r'\(([^)]+)\)', name)
                    clean = re.sub(r'\([^)]*\)', '', name).title().split()
                    if len(clean) >= 2:
                        person['names'].append({'surname': clean[0], 'given': clean[1], 'patronymic': ' '.join(clean[2:]), 'type': 'reported', 'provenance': prov})
                        ledger['fields'].append('names (normalized case; literal item retained)')
                        if maiden:
                            if 'девичестве' in maiden[1]:
                                person['names'][0]['type'] = 'birth'
                            else:
                                person['names'].append({**person['names'][0], 'surname': maiden[1].title(), 'type': 'birth'})
                    else:
                        report['questions'].append({'cell': c['address'], 'question': words['ask_name'].format(value=c['text'])})
                if role in {'birth', 'death'} and not doubtful(c['text']):
                    parsed = c.get('date') or exact_date(c['text'], pack)
                    if parsed and not c.get('formula'):
                        event = {'type': role, 'date': parsed, 'provenance': prov}
                        if role == 'death' and '(' in c['text']:
                            event['cause'] = c['text'].split('(', 1)[1].rstrip(')')
                        person['events'].append(event)
                        ledger['fields'].append('events.' + role)
                if role in {'birth_place', 'death_place'} and not doubtful(c['text']) and not re.search(r'\d{4}', c['text']):
                    person['events'].append({'type': role.split('_')[0], 'place': c['text'], 'provenance': prov})
                    ledger['fields'].append('events.' + role)
                describe(person, item, role, ledger, pack, report, ask)
                if role == 'living':
                    living = c['text'].casefold().strip()
                    if living in pack.get('alive', []):
                        person['living'] = True
                    elif living in pack.get('dead', []):
                        person['living'] = False
                    else:
                        report['reviewer_hints'].append({'cell': c['address'], 'hint': 'Unknown life status remains protected; review an explicit decision.'})
            if person:
                path_key = paths.get(kin.casefold().strip())
                source = next(i['id'] for i in data['items'] if i['cell'] == person_cell['address'])
                if kin.casefold().strip() in pack['vocabulary']['self']:
                    path_key = ''
                    person['living'] = True
                    data['narrator'] = person['id']
                if path_key is not None and path_key not in kin_people:
                    kin_people[path_key], kin_basis[path_key] = person['id'], source
                else:
                    ask(person_cell['address'], 'ask_kin', value=kin)
                    report['reviewer_hints'].append({'cell': person_cell['address'], 'hint': 'Missing, ambiguous or duplicate kin path; no automatic merge.'})
        for item in footnotes:
            # A variant note stays a telling, attached only to explicitly named surnames.
            matched = False
            for p in data['people']:
                if any(n['surname'].casefold() in item['text'].casefold() for n in p['names']):
                    describe(p, item, 'notes', {'fields': []}, pack, report, ask)
                    matched = True
            if not matched:
                report['questions'].append({'cell': item['cell'], 'question': words['ask_person'].format(value=item['text'])})
    enrich(data, pack, report, ask)
    for path_key, person_id in list(kin_people.items()):
        for depth in range(len(path_key)):
            prefix = path_key[:depth]
            if prefix not in kin_people:
                pid = 'bridge' + str(len(data['people']))
                data['people'].append({'id': pid, 'names': [], 'events': [], 'notes': []})
                kin_people[prefix], kin_basis[prefix] = pid, kin_basis[path_key]
    for child_path, child_id in kin_people.items():
        parents = {sex: kin_people[child_path + step] for sex, step in [('husband', 'f'), ('wife', 'm')]
                   if child_path + step in kin_people}
        if parents:
            grounds = sorted({kin_basis[child_path + step] for step in ('f', 'm') if child_path + step in kin_people})
            data['families'].append({'id': f'f{len(data["families"]) + 1}', **parents, 'children': [child_id], 'provenance': grounds})
    if '' in kin_people:
        data['narrator'] = kin_people['']
        next(p for p in data['people'] if p['id'] == data['narrator'])['living'] = True
    for path_key, pid in kin_people.items():
        person = next(p for p in data['people'] if p['id'] == pid)
        if not person['names']:
            person['placeholder'] = bridge_label(path_key, pack)
    for p in data['people']:
        p.pop('_name', None)
        p.pop('_kin', None)
    # Headers and unsupported formats are explicit losses; fatal structure is reported in one pass.
    fatal = not data['people'] or any('No person column' in x['reason'] or 'Invalid mapped' in x['reason'] for x in report['losses'])
    report['status'] = 'rejected' if fatal else 'draft'
    report['losses'] += [{'cell': c['address'], 'reason': c['reason']} for c in report['cells'] if c['outcome'] == 'loss']
    base = safe(instance, 'state', f'intake/table-{ident}')
    files = {base / 'reading.json': report, base / ('original' + path.suffix.lower()): blob}
    if mapping:
        files[base / 'mapping.toml'] = mapping.read_bytes()
    if not fatal:
        files[base / 'memory.toml'] = toml(data)
    for target, content in files.items():
        encoded = content if isinstance(content, bytes) else (json.dumps(content, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode()
        if target.exists() and target.read_bytes() != encoded:
            raise ValueError('Table draft already exists with different content; use a new --id')
    mutate(instance, files)
    return {**report, 'draft': str(base / 'memory.toml') if not fatal else None,
            'reading': str(base / 'reading.json'), 'original': str(base / ('original' + path.suffix.lower()))}
