# START_MODULE_CONTRACT: MOD-FEED-PERSON
# PURPOSE: Attach an existing graph person and language forms to authored feed data.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - attachment resolves working research people and merged ids [review: engine lead]
# - person insertion refuses a feed outside the instance feed directory [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (declared reader surfaces and default-deny policy)
# - MOD-FAMILY-WRITER (the sole filesystem and generation boundary)
# - docs/PRD.md#FORMS
# :END_MODULE_CONTRACT
import json
import re
import unicodedata


def load(p, default=None):
    return json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else default


def resolve(graph, pid):
    pid = graph.get('identityAliases', {}).get(pid, pid)
    return pid, graph.get('people', {}).get(pid)


def birth_year(person):
    for e in person.get('events') or []:
        if e.get('tag') == 'BIRT':
            m = re.search(r'\b(\d{4})\b', e.get('date') or '')
            if m:
                return m.group(1)
    return None


def ascii_upper(s):
    s = unicodedata.normalize('NFKD', s).replace('ł', 'l').replace('Ł', 'L')
    return re.sub(r'[^A-Z0-9]+', '_', s.encode('ascii', 'ignore').decode().upper()).strip('_')


def make_symbol(name, year, taken):
    first = ascii_upper(name.split()[0]) or 'PERSON'
    base = f'{first}_{year}' if year else first
    sym, n = base, 2
    while sym in taken:
        sym, n = f'{base}_{n}', n + 1
    return sym


from familiar.instance.gate import boundary


@boundary('writer')
def add(instance, feed_id, tree_id, symbol=None, source_name=None, year=None, chapter=None, role=None, highlight=False, dry_run=False):
    """Returns the report lines; writes the feed files unless dry_run."""
    folder = instance.path('feeds') / feed_id
    if not folder.resolve().is_relative_to(instance.path('feeds')):
        raise ValueError('invalid feed')
    meta = load(folder / 'feed.json')
    if meta is None:
        raise SystemExit(f'{folder}: no feed.json')
    from familiar.checks.engine import _known_people
    people = _known_people(instance)
    person = people.get(tree_id)
    if person is None:
        raise SystemExit(f'{tree_id}: unknown working person; inspect ids with tree build --view working')
    pid = person['id']
    source, targets = instance.source_language, [x for x in instance.languages if x != instance.source_language]
    name = person.get('name') or pid
    if name == pid and person.get('names'):
        n = person['names'][0]
        name = ' '.join(n.get(k, '') for k in ('given', 'surname')).strip() or pid
    year = year or birth_year(person)
    report = []
    new_persons, new_localize = {}, {}

    persons = meta.setdefault('persons', {})
    taken = [s for s, v in persons.items() if v == pid]
    if taken:
        sym = taken[0]
        report.append(f'persons: {pid} is already {sym}')
    else:
        sym = symbol or make_symbol(name, year, persons)
        if sym in persons and persons[sym] != pid:
            raise SystemExit(f'symbol {sym} already means {persons[sym]}')
        persons[sym] = pid
        new_persons[sym] = pid
        report.append(f'persons: {sym} = {pid}')

    profile = meta.setdefault('profile', {})
    table = profile.setdefault('localize', {})
    reverse = {v[targets[0]]: k for k, v in table.items() if targets and targets[0] in v}  # the first target language names the token
    tokens = name.split()
    if source_name:
        ru_tokens = source_name.split()
    else:
        ru_tokens = [reverse.get(t, t) for t in tokens]
    unknown = [] if source_name else [t for t in tokens if t not in reverse]
    if unknown:
        report.append(f'WARNING: no source-language form for {", ".join(unknown)}; pass --name "…" (LANG-2)')
    names = load(folder / 'names.json', {})
    if sym not in names and len(ru_tokens) == len(tokens):  # forms of a person who is already signed are not touched
        for r, t in zip(ru_tokens, tokens):
            if r != t and r not in table:
                table[r] = new_localize[r] = {lang: t for lang in targets}
                report.append(f'localize: {r} -> {t}')

    if sym in names:
        report.append(f'names: {sym} is already signed')
    else:
        full = ' '.join(ru_tokens)
        row = {source: full, **{lang: name for lang in targets}}
        row['short'] = {source: ru_tokens[0], **{lang: tokens[0] for lang in targets}}
        names[sym] = row
        report.append(f'names: {sym} = {full} / {name}')

    chapters = None
    if chapter:
        if role not in ('parent', 'child'):
            raise SystemExit('--chapter needs --as parent|child')
        chapters = load(folder / 'chapters.json', [])
        c = next((x for x in chapters if x.get('id') == chapter), None)
        if c is None:
            raise SystemExit(f'chapter {chapter}: not in chapters.json')
        t = c.setdefault('tree', {'parents': [], 'children': []})
        side = t.setdefault('parents' if role == 'parent' else 'children', [])
        if any(n.get('id') == sym for n in side):
            report.append(f'tree: {sym} is already in {chapter}')
        else:
            node = {'id': sym, 'name': tokens[0]}
            if year:
                node['year'] = year
            side.append(node)
            report.append(f'tree: {chapter} {role}s += {node}')
        if highlight and sym not in t.setdefault('highlight', []):
            t['highlight'].append(sym)
            report.append(f'tree: {chapter} highlight += {sym}')
    if not dry_run:
        from familiar.instance.writer import mutate
        changes = {folder / 'feed.json': meta, folder / 'names.json': names}
        if chapters is not None:
            changes[folder / 'chapters.json'] = chapters
        mutate(instance, changes)
    return report

