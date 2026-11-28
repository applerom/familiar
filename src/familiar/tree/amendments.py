# START_MODULE_CONTRACT: MOD-TREE-AMENDMENTS
# PURPOSE: Keep a proposed amendment beside the statement or reading it corrects, and let the card tell the leading reading.
# PRD_REF: docs/PRD.md#AMENDMENTS
# INVARIANTS:
# - the statement or reading is never edited: a proposal is its own file and names what it amends [review: engine lead]
# - the card tells a proposal from weight 0.5 or once a relative confirmed it; a declined one leaves the card as it was told [review: engine lead]
# - only a checked, personally attributed answer to the exact offer can settle it; a relative cannot undo a refusal [review: engine lead]
# - the reader receives only visible proposals and sources; the literal reply stays in the inbox [review: engine lead]
# CHANGES_WITH:
# - MOD-TREE-BUILDER (working proposals applied after the life assessment)
# - MOD-FAMILY-WRITER (proposal file, answers as inputs)
# - MOD-PUBLICATION (declared host-private surface)
# - MOD-FAMILY-BLANKS (one tap on the card)
# :END_MODULE_CONTRACT
import hashlib
import json
import re
from datetime import UTC, datetime

from familiar.instance.gate import boundary

FIELDS = ('name', 'patronymic', 'birth', 'death', 'place', 'spouse', 'occupation', 'siblings', 'other')
STATES = ('proposed', 'confirmed', 'declined')
ANSWERS = {'confirm': 'confirmed', 'decline': 'declined'}
LEADS_FROM, FIRM_FROM = .5, .9
TAGS = {'birth': 'BIRT', 'death': 'DEAT'}


def wording(value):
    return isinstance(value, str) and bool(value.strip()) or (
        isinstance(value, dict) and bool(value) and all(isinstance(v, str) and v.strip() for v in value.values()))


def said(value, language):
    return value if isinstance(value, str) else value.get(language) or next(iter(value.values()))


def problem(row):
    """What stops a proposal from being read, or ''."""
    if not isinstance(row, dict) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,119}', str(row.get('id', ''))):
        return 'id must be a portable filename slug'
    if not isinstance(row.get('person'), str) or not row['person']:
        return 'person must be a tree id'
    if row.get('field') not in FIELDS:
        return 'field is one of ' + ', '.join(FIELDS)
    original = row.get('original')
    if not isinstance(original, dict) or not wording(original.get('text')) or not isinstance(original.get('source'), str):
        return 'original needs the literal text and its source (memory item or record)'
    if not wording(row.get('value')) or not wording(row.get('basis')):
        return 'value and basis need text'
    if type(row.get('weight')) not in (int, float) or not 0 <= row['weight'] <= 1:
        return 'weight must be from 0 to 1'
    if not isinstance(row.get('sources', []), list) or not all(isinstance(s, str) and s for s in row.get('sources', [])):
        return 'sources must be a list of ids'
    if row.get('state', 'proposed') not in STATES:
        return 'state is one of ' + ', '.join(STATES)
    return ''


def read(instance):
    """[(path, row, problem)] of every proposal file."""
    found, folder = [], instance.path('amendments')
    for path in sorted(folder.glob('*.json')) if folder.is_dir() else ():
        try:
            row = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as exc:
            found.append((path, {}, str(exc)))
            continue
        found.append((path, row, problem(row) or ('' if row['id'] == path.stem else 'id must match the file name')))
    return found


def answer_files(instance):
    """Inbox envelopes that answer a proposal: inputs of the tree, unlike other unread remarks."""
    found = {}
    folder = instance.path('amendments')
    for path in sorted(instance._inside('family/feedback/inbox').glob('*.json')) if folder.is_dir() else ():
        try:
            row = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        if isinstance(row, dict) and row.get('kind') in ANSWERS and str(row.get('subject', '')).startswith('amendment:'):
            found[path] = row
    return found


def _when(value):
    try:
        at = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return at if at.tzinfo else at.replace(tzinfo=UTC)


def revision(row, person):
    """Bind the exact stored proposal, including translations, to the card it was offered on."""
    return hashlib.sha256(json.dumps([person, row], ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def settled(row, answers, person, offered, aliases):
    """An authored decision wins until reopened by the owner."""
    state = row.get('state', 'proposed')
    if state != 'proposed':
        return state
    since = _when(row.get('at'))
    eligible = []
    for answer in answers:
        at = _when(answer.get('received_at'))
        sender = answer.get('sender')
        if not isinstance(sender, dict):
            continue
        owner = sender.get('role') == 'owner' and (sender.get('sub') or sender.get('loopback') is True)
        relative = sender.get('role') == 'reader' and sender.get('sub') and sender.get('person')
        exact = answer.get('amendment_revision') == offered and (since is None or at is not None and at >= since)
        original = answer.get('person')
        refuses = (answer['kind'] == 'decline' and bool(answer.get('amendment_revision'))
                   and aliases.get(original, original) == person)
        if (answer.get('subject') == 'amendment:' + row['id'] and (refuses or exact and original == person)
                and answer.get('amendment_offered') is True
                and (owner or relative) and at is not None):
            eligible.append((at, answer.get('id', ''), answer['kind'], owner))
    for _, _, kind, owner in sorted(eligible):
        if state != 'declined' or owner:
            state = ANSWERS[kind]
    return state


def current(instance, graph):
    """Readable proposals about people of the graph, with their effective states."""
    rows = read(instance)
    answers = list(answer_files(instance).values()) if rows else []
    aliases = graph.get('identityAliases', {})
    for _, row, why in rows:
        person = aliases.get(row.get('person'), row.get('person'))
        if not why and person in graph['people']:
            offered = revision(row, person)
            state = settled(row, answers, person, offered, aliases)
            leading = state == 'confirmed' or state == 'proposed' and row['weight'] >= LEADS_FROM
            yield row | {'person': person, 'state': state, 'leading': leading, 'revision': offered}


def apply(instance, graph, *, visible=None, shown=True):
    """Apply working proposals or the subset that passed the publication gate."""
    from familiar.checks.engine import record_path

    for row in current(instance, graph):
        if visible is not None and (row['state'] == 'declined' or not visible(row)):
            continue
        person = graph['people'][row['person']]
        sources = [s for s in row.get('sources', []) if s in graph['sources']]
        if shown:
            original = row['original']['source']
            kind = graph['sources'].get(original, {}).get('kind')
            paper = kind not in (None, 'memory') or record_path(instance, original).is_file()
            person.setdefault('amendments', []).append(
                {'id': row['id'], 'field': row['field'], 'original': row['original']['text'], 'value': row['value'],
                 'origin': 'record' if paper else 'memory',
                 'weight': row['weight'], 'basis': row['basis'], 'state': row['state'], 'leading': row['leading'],
                 'sources': sources, **({'revision': row['revision']} if row['state'] == 'proposed' else {})})
        if row['leading']:
            lead(person, row, sources, instance.source_language, with_basis=shown)
    return graph


def lead(person, row, sources, language, *, with_basis):
    field, value = row['field'], said(row['value'], language)
    firm = row['state'] == 'confirmed' or row['weight'] >= FIRM_FROM
    if field in {'name', 'patronymic'}:
        from .surnames import shown_first
        part = {}
        if field == 'patronymic':
            named = next((n for n in shown_first(person) if n.get('given')), {})
            part = {k: v for k, v in (('given', named.get('given')), ('patronymic', value),
                                      ('surname', named.get('surname'))) if v}
            value = ' '.join(part.values())
        person['names'] = [{**part, 'display': value, 'type': 'amended', 'provenance': sources}, *person.get('names', [])]
        person['name'] = value
        shown = person.setdefault('namePresentation', {})
        shown.update(display=value, full=value, decided=True)
        if isinstance(row['value'], dict) and field == 'name':
            shown.setdefault('byLanguage', {}).update({k: v for k, v in row['value'].items() if k != language})
        return
    source, text = row['original']['source'], said(row['original']['text'], language)
    for fact in person.get('facts', []):
        # What was told stays in "More": only the fact that tells this very statement steps back.
        if source in fact.get('sources', []) and (fact.get('eventType') == field or text in str(fact.get('text', ''))):
            fact['detailOnly'] = True
    if field in TAGS:
        event = {'type': field, 'tag': TAGS[field], 'date': value, 'sources': sources, 'provenance': sources,
                 'amendment': row['id']}
        person['events'] = [event, *(person.get('events') or [])]
        person['cardPresentation'] = {**(person.get('cardPresentation') or {}), field: value,
                                      field + 'Kind': 'source' if firm else 'inferred'}
    person.setdefault('facts', []).insert(0, {
        'label': 'events' if field in TAGS else 'notes', **({'eventType': field} if field in TAGS else {}), 'text': value,
        'status': 'export' if firm else 'hypothesis', 'weight': row['weight'], 'sources': sources,
        **({'basis': row['basis']} if with_basis else {})})


def statements(instance):
    """Ids of what the family told and of what was read: memory items and records."""
    found = {p.stem for p in instance.path('records').rglob('*.json')}
    for path in instance.path('memory').rglob('*.json'):
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        rows = data if isinstance(data, list) else [data]
        found.update(i['id'] for d in rows if isinstance(d, dict) for i in d.get('items', [])
                     if isinstance(i, dict) and isinstance(i.get('id'), str))
    return found


def check(instance, graph, chosen, fail):
    """Advice only: a proposal that cannot be read, or that amends a statement nobody can find."""
    rows = [row for row in read(instance) if chosen(row[0])]
    known = statements(instance) | graph.get('sources', {}).keys() if rows else set()
    for path, row, why in rows:
        if why:
            fail(path, f'{why}; research form amendment')
        elif graph.get('identityAliases', {}).get(row['person'], row['person']) not in graph['people']:
            fail(path, f"unknown person {row['person']}")
        elif missing := [s for s in (row['original']['source'], *row.get('sources', [])) if s not in known]:
            fail(path, f"no memory item, record or source {', '.join(missing)}")


@boundary('transaction')
def record(instance, values):
    """Write one proposal (research amend). The amended statement and other proposals are not touched."""
    from familiar.instance.writer import amendment_proposal

    from .builder import _build
    graph = _build(instance)
    row = {'id': '', 'state': 'proposed', 'at': datetime.now(UTC).isoformat(timespec='seconds')} | {
        k: v for k, v in values.items() if v not in (None, '', [])}
    if not row['id']:
        row['id'] = re.sub(r'[^A-Za-z0-9_-]+', '-', f"{row.get('person', '')}-{row.get('field', '')}").strip('-')[:110]
    if why := problem(row):
        raise ValueError(why)
    if graph.get('identityAliases', {}).get(row['person'], row['person']) not in graph['people']:
        raise ValueError(f"unknown person {row['person']}; inspect ids with tree build --view working")
    known = statements(instance) | graph['sources'].keys()
    if missing := [s for s in (row['original']['source'], *row.get('sources', [])) if s not in known]:
        raise ValueError(f"no memory item, record or source {', '.join(missing)}")
    amendment_proposal(instance, row)
    return row
