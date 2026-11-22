# START_MODULE_CONTRACT: MOD-FAMILY-ASKS
# PURPOSE: Store family conversation prompts and the lines nobody can be asked about, carry over old requests and derive state from feedback.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - only a living tree person or a named group of relatives holds an ask [review: engine lead]
# - carry-over preserves old question IDs, literal replies and correspondence originals [review: engine lead]
# - a closed horizon hides and refuses only unanswered asks of its line; it never changes a weight [review: engine lead]
# CHANGES_WITH:
# - MOD-CORRESPONDENCE
# - MOD-DESK-FEEDBACK
# - MOD-FAMILY-WRITER
# :END_MODULE_CONTRACT
import hashlib
import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from .correspondence import aim_versions, no_knowledge, now, validate as validate_letter
from .gate import boundary

WANTS = ('name', 'patronymic', 'maiden', 'place', 'date', 'photo', 'story')
STATES = {'proposed', 'open', 'answered', 'dont_know', 'private', 'closed'}
VISIBLE = {'open', 'dont_know'}
FEEDBACK = {'ask_answer', 'ask_state'}
HORIZON = {'since', 'by', 'known', 'reopen_when'}


def key(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,119}', value):
        raise ValueError('Ask ID must be a portable filename slug')
    return value


def wording(value):
    return isinstance(value, str) and bool(value.strip())


def text(value):
    return wording(value) or (isinstance(value, dict) and bool(value) and all(wording(v) for v in value.values()))


def validate(row, people=None, versions=None):
    key(row.get('id'))
    holder, about, aim = (row.get(k) for k in ('holder', 'about', 'aim'))
    if isinstance(holder, str):
        historical = row.get('state') in ('answered', 'private', 'closed')
        if (not holder or people is not None and (holder not in people or not historical
                and people[holder].get('life_assessment', {}).get('status') != 'living')):
            raise ValueError('Ask holder must be a living person or a group of relatives')
    elif not (isinstance(holder, dict) and (wording(holder.get('line')) or wording(holder.get('label')))):
        raise ValueError('Ask holder needs a tree ID or a group with line or label')
    if (not isinstance(about, dict) or not about or set(about) - {'person', 'line', 'place'}
            or not all(wording(v) for v in about.values())):
        raise ValueError('Ask about must name a person, line or place')
    if about.get('person') and people is not None and about['person'] not in people:
        raise ValueError('Ask about.person is not in the tree')
    if not text(row.get('question')):
        raise ValueError('Ask requires a question')
    opener = row.get('opener')
    if opener and not text(opener.get('text') if isinstance(opener, dict) and 'text' in opener else opener):
        raise ValueError('Ask opener requires text')
    for name in ('question_child', 'next_hint', 'photo_note', 'occasion'):
        if row.get(name) and not text(row[name]):
            raise ValueError('Ask requires text in ' + name)
    hints = row.get('hints', [])
    if not isinstance(hints, list) or len(hints) > 4 or not all(text(h) for h in hints):
        raise ValueError('Ask needs up to four text hints')
    wants = row.get('wants', [])
    if not isinstance(wants, list) or any(not isinstance(w, str) or w not in WANTS for w in wants):
        raise ValueError('Unknown ask wants field')
    tender = row.get('tender', False)
    if type(tender) is not bool and not wording(tender):
        raise ValueError('Ask tender must be a boolean or a topic')
    if (not isinstance(aim, dict) or not isinstance(aim.get('people', []), list)
            or any(not wording(pid) or (people is not None and pid not in people) for pid in aim.get('people', []))
            or type(aim.get('value')) not in (int, float) or not 0 <= aim['value'] <= 1):
        raise ValueError('Ask aim needs known people and a value from 0 to 1')
    version = aim.get('version')
    if version is not None and (not wording(version) or versions is not None and version not in versions):
        raise ValueError('Ask aim refers to an unknown version')
    state = row.get('state')
    if not isinstance(state, str) or state not in STATES and not state.startswith('will_ask:'):
        raise ValueError('Unknown ask state')
    if state.startswith('will_ask:'):
        witness = state.partition(':')[2]
        if not witness or people is not None and people.get(witness, {}).get('life_assessment', {}).get('status') != 'living':
            raise ValueError('Ask will_ask state needs a living witness')


def waiting(state):
    """An ask nobody has answered yet: the family is still expected to say something."""
    return state in {'proposed', 'open', 'dont_know'} or state.startswith('will_ask:')


def validate_horizons(data):
    if not isinstance(data, dict) or set(data) - {'lines'} or not isinstance(data.get('lines', {}), dict):
        raise ValueError('horizons: expected {"lines": {line: {since, by, known, reopen_when}}}')
    for line, entry in data.get('lines', {}).items():
        if not wording(line) or not isinstance(entry, dict) or set(entry) - HORIZON:
            raise ValueError(f'horizon {line!r}: expected since, by, known, reopen_when')
        try:
            date.fromisoformat(entry.get('since'))
        except (TypeError, ValueError):
            raise ValueError(f'horizon {line}: since must be a date YYYY-MM-DD') from None
        if not text(entry.get('by')):
            raise ValueError(f'horizon {line}: by names who said that nobody can be asked')
        for name in ('known', 'reopen_when'):
            if entry.get(name) and not text(entry[name]):
                raise ValueError(f'horizon {line}: {name} must be text')
    return data.get('lines', {})


def horizons(instance, raw=None):
    """Lines closed for questions to relatives: {line: entry}. The family said nobody is left to ask."""
    path = instance.path('horizons')
    if raw is None:
        raw = path.read_bytes() if path.is_file() else None
    return validate_horizons(json.loads(raw)) if raw else {}


def row_lines(row):
    aim, about, holder = row.get('aim') or {}, row.get('about') or {}, row.get('holder')
    return [v for v in (aim.get('line'), about.get('line'), row.get('line'),
                        holder.get('line') if isinstance(holder, dict) else None) if wording(v)]


def closed_line(instance, names, lines=None):
    """(line, entry) of a closed horizon matching any of these line names by surname form, else None."""
    from familiar.research.coverage import surname_keys
    lines = horizons(instance) if lines is None else lines
    language = instance.source_language
    for name in names if lines else ():
        keys = surname_keys(name, language)
        for line, entry in lines.items():
            if keys & surname_keys(line, language):
                return line, entry
    return None


def horizon_note(line, entry):
    note = f"line {line}: the family closed its horizon on {entry['since']} ({entry['by']}), nobody is left to ask"
    if entry.get('known'):
        note += f"; known: {entry['known']}"
    if entry.get('reopen_when'):
        note += f"; reopen when: {entry['reopen_when']}"
    return note


@boundary('transaction')
def set_horizon(instance, line, entry=None):
    """Close a line for questions (entry) or open it again (None). Weights and answered asks stay as they are."""
    from .writer import mutate
    path = instance.path('horizons')
    before = json.loads(path.read_bytes()) if path.is_file() else None
    lines = dict(validate_horizons(before or {}))
    if not wording(line):
        raise ValueError('A horizon needs a line name')
    if entry is None:
        if line not in lines:
            raise ValueError(f'line {line} has no closed horizon')
        lines.pop(line)
    else:
        lines[line] = {k: v for k, v in entry.items() if v}
    data = {'lines': lines}
    validate_horizons(data)
    mutate(instance, {path: data}, expect={path: before} if before is not None else None,
           exclusive=[] if before is not None else [path])
    return path


def rows(folder):
    for path in sorted(folder.rglob('*.json')):
        yield path, json.loads(path.read_bytes())


def get(instance, identity):
    identity = key(identity)
    return next(((path, row) for path, row in rows(instance.path('asks')) if row.get('id') == identity), (None, {}))


def context(row):
    value = [row.get(k) for k in ('holder', 'hints', 'next_hint', 'state_since')]
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:16]


def feedback_state(row):
    if row['kind'] == 'ask_state':
        return row['ask_state']
    return 'private' if row.get('private') or row.get('tender') else 'answered'


def latest_feedback(envelopes):
    latest = {}
    for row in envelopes:
        identity = row.get('ask_id') or row.get('question')
        if not identity or row.get('kind') not in FEEDBACK | {'answer'}:
            continue
        if row['kind'] == 'answer':
            row = (row | {'kind': 'ask_state', 'ask_state': 'dont_know'}
                   if no_knowledge(row.get('text', '')) else row | {'kind': 'ask_answer'})
        try:
            at = datetime.fromisoformat(row['received_at']).astimezone(UTC)
            feedback_state(row)
        except (KeyError, TypeError, ValueError):
            continue
        if identity not in latest or (at, row.get('id', '')) > latest[identity][:2]:
            latest[identity] = (at, row.get('id', ''), row)
    return latest


def current(row, latest):
    state = row['state']
    if not latest or state in {'proposed', 'private', 'closed'}:
        return state, None, state == 'dont_know'
    at, _, feedback = latest
    if row.get('state_since') and at < datetime.fromisoformat(row['state_since']):
        return state, None, state == 'dont_know'
    state = feedback_state(feedback)
    return state, at, state == 'dont_know' and feedback.get('ask_context', context(row)) == context(row)


@boundary('transaction')
def change(instance, action, value, identity=None, *, despite_horizon=False):
    from familiar.tree.builder import _build, people_index

    from .writer import mutate
    if not isinstance(value, dict):
        raise ValueError('Ask input must be a JSON object')
    identity = key(value.get('id') if identity is None else identity)
    path, before = get(instance, identity)
    if action == 'create' and path:
        raise ValueError('Ask already exists')
    if action == 'update' and not path:
        raise ValueError('No such ask')
    if value.get('id', identity) != identity:
        raise ValueError('An ask ID cannot change')
    row = {'state': 'proposed'} | before | value | {'id': identity}
    if 'state' in value:
        row['state_since'] = now()
    if (waiting(row['state']) and not despite_horizon and (action == 'create' or not waiting(before.get('state', '')))
            and (closed := closed_line(instance, row_lines(row)))):
        raise ValueError(horizon_note(*closed) + '. The story is told from what we gathered; '
                         'record this ask anyway with --despite-horizon (say why in next_hint), '
                         'or open the line again with family horizon open')
    versions = aim_versions([r for _, r in rows(instance.path('versions'))])
    validate(row, people_index(_build(instance)), versions)
    target = path or instance.path('asks') / (identity + '.json')
    mutate(instance, {target: row}, exclusive=[] if path else [target], expect={path: before} if path else None)
    return identity


@boundary('transaction')
def migrate(instance):
    from familiar.desk.model import words
    from familiar.tree.builder import _build, people_index

    from .writer import mutate
    retired = instance.path('questions')
    old = {p: p.read_bytes() for p in retired.rglob('*') if p.is_file() and p.suffix in {'.json', '.jsonl'}}
    letters = {p: r for p, r in rows(instance.path('correspondence')) if r.get('channel') == 'relative'}
    if not old and not letters:
        return 0
    graph = _build(instance)
    people = people_index(graph)
    versions = aim_versions([r for _, r in rows(instance.path('versions'))])
    chosen = {r['id']: r for _, r in rows(instance.path('asks'))}
    answers = {r['id']: r for _, r in rows(instance.path('answers'))}
    w = words(instance)['asks']
    new = {}

    def carry(prior, identity, letter=None):
        original = {'question': prior} if prior else {}
        letter = letter or prior.get('migrated_correspondence')
        if letter:
            original['correspondence'] = letter
        if identity in chosen and chosen[identity].get('legacy') == original:
            return
        while identity in chosen:
            identity = key('relative-' + identity) if letter and not prior else identity
            if prior or len(identity) > 110:
                raise ValueError('Ask ID already in use: ' + identity)
        aim = dict((letter or {}).get('aim') or {})
        version = aim.get('version') or (letter or {}).get('question') or prior.get('question')
        base = versions.get(version, ({}, {}))[0]
        subjects = list(dict.fromkeys([*aim.get('people', []), *prior.get('people', []),
                                       *(letter or {}).get('people', []), *base.get('people', [])]))
        line = aim.get('line') or base.get('line')
        value = aim.get('value', prior.get('priority', .5))
        if type(value) not in (int, float) or not 0 <= value <= 1:
            value = .5
        aim.update(people=subjects, value=value,
                   settles=aim.get('settles') or prior.get('why_this_paper') or '', why_now=aim.get('why_now', ''))
        if version in versions:
            aim['version'] = version
        else:
            aim.pop('version', None)
        if line:
            aim['line'] = line
        who = prior.get('addressee')
        if who == 'narrator':
            who = graph.get('narrator')
        if who == 'host':
            who = graph.get('root')
        if people.get(who, {}).get('life_assessment', {}).get('status') != 'living':
            label = prior.get('call_as') or (letter or {}).get('recipient')
            who = {'label': label} if label else {'line': line} if line else {'label': w['relatives']}
        about = ({'person': subjects[0]} if subjects else {}) | ({'line': line} if line else {})
        if not about:
            about = {'line': w['relatives']}
        paper = prior.get('paper')
        old_state = prior.get('state', 'draft') if prior else letter['state']
        state = {'draft': 'proposed', 'ready': 'proposed', 'asked': 'open', 'sent': 'open',
                 'not_needed': 'closed', 'not-presented': 'closed'}.get(old_state, old_state)
        question = prior.get('witness_question') or (letter or {}).get('text')
        if not question:
            question = w['paper_question'].format(paper=paper) if paper else base.get('title') or w['relatives']
        row = {'id': identity, 'holder': who, 'about': about, 'opener': prior.get('our_version') or '',
               'question': question, 'hints': (prior.get('options') or [])[:4], 'wants': ['photo'] if paper else [],
               'photo_note': '\n'.join(v for k in ('paper', 'paper_description', 'look_in', 'photograph')
                                       if isinstance(v := prior.get(k), str) and v),
               'next_hint': prior.get('host_next') or prior.get('fallback') or '', 'aim': aim, 'state': state,
               'legacy': original}
        for field in ('case', 'answer', 'asked_at', 'answered_at'):
            if prior.get(field):
                row[field] = prior[field]
        if letter and letter.get('sent') and not row.get('asked_at'):
            row['asked_at'] = letter['sent']['at']
        if letter and letter.get('replies') and not row.get('answer'):
            reply = letter['replies'][-1]
            payload = {k: reply[k] for k in ('by', 'at', 'text', 'source', 'original')} | {'request': identity}
            answer_id = identity + '-reply'
            while answer_id in answers and answers[answer_id] != payload | {'id': answer_id}:
                answer_id = 'relative-' + answer_id
            if answer_id not in answers:
                answers[answer_id] = payload | {'id': answer_id}
                new[instance.path('answers') / (answer_id + '.json')] = answers[answer_id]
            row.update(answer=answer_id, answered_at=reply['at'])
        validate(row, people, versions)
        chosen[identity] = row
        new[instance.path('asks') / (identity + '.json')] = row

    for path, raw in old.items():
        if path.suffix == '.jsonl':
            values = [json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip()]
        else:
            value = json.loads(raw)
            values = value if isinstance(value, list) else [value]
        for row in values:
            carry(row, key(row.get('id')))
    for row in letters.values():
        validate_letter(row, migrating=True)
        if not any(r.get('legacy', {}).get('correspondence') == row for r in chosen.values()):
            carry({}, key(row['id']), row)
    mutate(instance, new, exclusive=new, remove=old | letters)
    return sum(p.is_relative_to(instance.path('asks')) for p in new)


def register(actions):
    parser = actions.add_parser('ask', help='Family conversations and carry-over')
    commands = parser.add_subparsers(dest='ask_action', required=True)
    for name in ('create', 'update', 'migrate'):
        command = commands.add_parser(name)
        if name == 'update':
            command.add_argument('identity')
        if name != 'migrate':
            command.add_argument('input', type=Path)
            command.add_argument('--despite-horizon', action='store_true',
                                 help='Record an unanswered ask on a line whose horizon the family closed')
    parser.set_defaults(run=execute)
    horizon = actions.add_parser('horizon', help='A line nobody in the family can be asked about any more')
    steps = horizon.add_subparsers(dest='horizon_action', required=True)
    close = steps.add_parser('close', help='Close the line for questions to relatives')
    close.add_argument('line')
    close.add_argument('--by', required=True, help='Who said so: a tree ID or words')
    close.add_argument('--since', default=None, help='Date YYYY-MM-DD (default today)')
    close.add_argument('--known', default='', help='What is known indirectly; it becomes arguments of versions')
    close.add_argument('--reopen-when', default='', help='The event that opens the line again')
    reopen = steps.add_parser('open', help='Open the line again: new answers can come')
    reopen.add_argument('line')
    horizon.set_defaults(run=execute_horizon)


def execute_horizon(args):
    from .model import Instance
    try:
        instance = Instance(args.root)
        if args.horizon_action == 'open':
            print(set_horizon(instance, args.line))
        else:
            print(set_horizon(instance, args.line, {'since': args.since or date.today().isoformat(), 'by': args.by,
                                                    'known': args.known, 'reopen_when': args.reopen_when}))
        return 0
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


def execute(args):
    from .model import Instance
    try:
        instance = Instance(args.root)
        if args.ask_action == 'migrate':
            print(f'Moved {migrate(instance)} asks')
        else:
            print(change(instance, args.ask_action, json.loads(args.input.read_bytes()), getattr(args, 'identity', None),
                         despite_horizon=args.despite_horizon))
        return 0
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
