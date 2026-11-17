# START_MODULE_CONTRACT: MOD-RESEARCH-COVERAGE-CONTEXT
# PURPOSE: Recover planning context and source visits, retaining accepted tree links and contextual roles.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - analytical comparisons never become personal record visits [review: engine lead]
# - accepted tree references and explicit review assessments retain their provenance [review: engine lead]
# - contextual participants never become principal identity candidates [review: engine lead]
# :END_MODULE_CONTRACT
import json
import re
from fnmatch import fnmatchcase
from functools import lru_cache

from .search_ledger import parse_by, row_tokens, tokens
from .search_variants import _entries, form_data, norm
from .coverage_evidence import accepted_links, analytical, references


def text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return ' '.join(text(v) for v in value.values())
    if isinstance(value, list):
        return ' '.join(text(v) for v in value)
    return ''


@lru_cache(maxsize=4096)
def folded(value):
    return norm(value)


@lru_cache(maxsize=4096)
def pattern(needle):
    return re.compile(r'(?<!\w)' + re.escape(folded(needle)) + r'(?!\w)')


def contains(haystack, needle):
    return bool(needle and pattern(needle).search(folded(haystack)))


def person_text(person):
    return text({k: person.get(k) for k in ('events', 'cardPresentation', 'places', 'notes', 'facts', 'summary')})


def episode_fit(person, source):
    """Rank a dated personal episode, including attributed family memory, without making it fact."""
    classes = set(source.get('classes', []))
    terms = []
    if classes & {'military', 'award'}:
        terms.append(r'кавалер|служ(?:ба|ил)|полк|военн|army|military|cavalry|wojsk')
    if classes & {'emigration', 'forced-labour'}:
        terms.append(r'эмигра|пересел|переех|emigra|migrat|forced.labour|принудительн')
    if classes & {'repression', 'special-settlement'}:
        terms.append(r'репресс|арест|ссылк|депорт|repress|arrest|deport')
    years = source.get('years', [])
    if not terms or len(years) != 2:
        return 0
    known, overlap = False, False
    for item in [*person.get('events', []), *person.get('notes', []), *person.get('facts', [])]:
        if isinstance(item, dict) and item.get('status') in {'rejected', 'disproved'}:
            continue
        raw = text({k: item.get(k) for k in ('type', 'date', 'text', 'plain', 'label', 'public_fact')}) if isinstance(item, dict) else text(item)
        if re.search('|'.join(terms), raw, re.I):
            dates = [int(y) for y in re.findall(r'(?<!\d)(1[6-9]\d\d|20\d\d)(?!\d)', raw)]
            if dates:
                known = True
                overlap |= any(years[0] <= y <= years[1] for y in dates)
    return 8 if overlap else -3 if known else 0


def life_window(person):
    """Planning only: even an uncertain family birth note is useful, never a life-status decision."""
    from familiar.tree.life import _birth_bounds
    bounds = {'birth': [], 'death': []}
    for kind, tag in [('birth', 'BIRT'), ('death', 'DEAT')]:
        values = [e.get('date') for e in person.get('events', []) if (e.get('type') == kind or e.get('tag') == tag)
                  and e.get('status') not in {'hypothesis', 'rejected', 'disproved'}]
        values += [(person.get('cardPresentation') or {}).get(kind), person.get(kind)]
        # A year next to a personal birth/death verb, not arbitrary years in a biography.
        verbs = r'родил[а-я]*|рожден[а-яё]*|born|urodz\w*' if kind == 'birth' else r'умер[а-я]*|died|zmar\w*'
        for note in person.get('notes', []):
            if isinstance(note, dict) and note.get('status') in {'rejected', 'disproved'}:
                continue
            raw = note if isinstance(note, str) else note.get('plain') or note.get('text', '')
            values += [m[1] for m in re.findall(r'(?i)\b(' + verbs + r')\b([^.;\n]{0,90})', raw)
                       if not re.search(r'(?i)\b(сын|дочь|отец|мать|son|daughter)\b', m[1])]
        bounds[kind] = [b for v in values if (b := _birth_bounds(v))]
    births, deaths = bounds['birth'], bounds['death']
    if not births:
        guess = person.get('birth_guess') or person.get('birthGuess') or {}
        year = guess.get('year') if isinstance(guess, dict) else guess
        if isinstance(year, (int, float)):
            births = [(int(year) - 30, int(year) + 30)]
    return (min((b[0] for b in births), default=None),
            max((b[1] for b in deaths), default=max((b[1] + 120 for b in births), default=None)))


def place_groups(raw, catalog):
    return {i for i, e in enumerate(catalog.coverage_places) if any(contains(raw, a) for a in e.get('aliases', []))}


def row_people(row, tree, catalog):
    """Separate the searched surname population from the people of a question. No journal mutation."""
    query = row.get('query')
    relatives = {k: v for k, v in query.items() if re.search(r'parent|father|mother', k, re.I)} if isinstance(query, dict) else {}
    target = {k: v for k, v in query.items() if k not in relatives} if isinstance(query, dict) else query
    words = set(row_tokens({'query': target}))
    if not hasattr(tree, '_coverage_surnames'):
        tree._coverage_surnames = {}
        for pid, p in tree.people.items():
            for s in p['surnames']:
                tree._coverage_surnames.setdefault(s, set()).add(pid)
    candidates = set()
    for w in words:
        if '*' in w or '?' in w:
            for s, people in tree._coverage_surnames.items():
                if fnmatchcase(s, w):
                    candidates.update(people)
        else:
            candidates.update(tree._coverage_surnames.get(w, ()))
    candidates = sorted(candidates)
    named = [p for p in candidates if tree.people[p]['givens'] & words]
    declared = [p['id'] for ident in row.get('people', []) if (p := tree.person(ident))]
    # A researcher's explicit addressee outranks dictionary retrieval. Question-only
    # migration remains refinable; it was never an explicit attribution.
    if declared and row.get('people_from') != 'question':
        return declared, row.get('people_from') or row.get('people_basis') or 'declared', 'person'
    if named:
        if row.get('people_from') == 'question':
            return named, 'name', 'person'
        return (declared or named), row.get('people_from') or row.get('people_basis') or 'name', 'person'
    raw = text([row.get('query'), row.get('coverage')])
    if not candidates:
        place_values = [v for k, v in query.items() if re.search(r'place|parish|town', k, re.I) and isinstance(v, str)] if isinstance(query, dict) else []
        if place_values and not hasattr(tree, '_coverage_raw'):
            tree._coverage_raw = {pid: person_text(p) for pid, p in tree.graph['people'].items()}
        matched = [pid for pid, raw_person in getattr(tree, '_coverage_raw', {}).items() if any(contains(raw_person, v) for v in place_values if len(v) > 3)]
        if matched:
            return matched, 'place', 'place'
        return declared, row.get('people_from') or row.get('people_basis') or 'declared', 'person'
    groups = place_groups(raw, catalog)
    years = row.get('coverage', {}).get('years') if isinstance(row.get('coverage'), dict) else None
    from familiar.tree.life import _birth_bounds
    interval = _birth_bounds(years)
    result = []
    if not hasattr(tree, '_coverage_places'):
        tree._coverage_places = {}
    for pid in candidates:
        p = tree.graph['people'][pid]
        if pid not in tree._coverage_places:
            places = person_text(p)
            tree._coverage_places[pid] = (places, place_groups(places, catalog), life_window(p))
        places, person_groups, window = tree._coverage_places[pid]
        # The same alias group, or a literal specific place, ties a surname visit to this family place.
        same = bool(groups & person_groups)
        same |= any(contains(raw, v) for v in [
            (p.get('cardPresentation') or {}).get('place', ''),
            *(e.get('place', '') for e in p.get('events', [])), *p.get('places', [])] if isinstance(v, str) and len(v) > 3)
        # An explicit scope may already name the population; question-only attribution is not such a scope.
        same |= pid in declared and row.get('people_from') != 'question'
        if relatives:
            parent_words = set(tokens(text(relatives)))
            parents = [par for f in tree.graph.get('families', []) if pid in f.get('children', [])
                       for par in (f.get('husband'), f.get('wife')) if par in tree.people]
            # A surname plus a parent's name searches that parent's descendants, not the parent.
            same = bool(any(tree.people[par]['givens'] & parent_words for par in parents)) and bool(places)
        lo, hi = window
        if same and not (interval and ((lo is not None and lo > interval[1]) or (hi is not None and hi < interval[0]))):
            result.append(pid)
    return result, 'surname-place', 'surname'


def script_of(form):
    return 'Cyrl' if re.search('[\u0400-\u052f]', form) else 'Latn' if re.search('[A-Za-zÀ-ž]', form) else None


def form_allowed(form, source, window, metadata, person=None, observed_scripts=()):
    clean = form_data(form)['text']
    details = metadata.get(norm(clean), [])
    scripts = source.get('search_scripts', [])
    script = script_of(clean)
    if scripts and script not in scripts:
        return False
    if not scripts and observed_scripts and script not in observed_scripts:
        return False  # foreign writing is not mandatory without catalogue evidence
    languages = source.get('search_languages', [])
    eras = source.get('search_language_eras', [])
    lo, hi = window
    if eras:
        languages = list({lang for era in eras if (lo is None or lo <= era['years'][1])
                          and (hi is None or hi >= era['years'][0]) for lang in era['languages']})
    sex = str((person or {}).get('sex') or '').upper()
    def applicable(f):
        gender = str(f.get('sex') or f.get('gender') or '').upper()
        if sex in {'M', 'F'} and gender in {'M', 'F', 'MALE', 'FEMALE'} and gender[0] != sex:
            return False
        people = f.get('people') or ([f['person']] if f.get('person') else [])
        if people and (person or {}).get('id') not in people:
            return False
        episode = f.get('episode')
        if episode:
            episodes = episode if isinstance(episode, list) else [episode]
            source_episodes = source.get('search_episodes', []) + source.get('episodes', [])
            if 'emigration' in source.get('classes', []):
                source_episodes = [*source_episodes, 'emigration-us']
            if not any(e in source_episodes for e in episodes):
                return False
        return True
    return not details or any(applicable(f) and (not languages or f.get('language') in languages or f.get('language') in {None, 'und'})
                             and (not f.get('years') or (lo is None or lo <= f['years'][1])
                                  and (hi is None or hi >= f['years'][0])) for f in details)


def form_metadata(instance):
    result = {}
    for e in _entries(instance):
        for f in e['forms']:
            result.setdefault(norm(f['text']), []).append(f)
    return result


def missing_forms(data, pid, sid, cell):
    required = list(data['tree'].people[pid]['required_forms'].values()) + list(cell['planned'])
    if cell['scopes'] == {'surname'}:
        givens = data['tree'].people[pid]['givens']
        required = [f for f in required if norm(f) not in givens]
    source = data['resolver'].catalog.sources.get(sid, {})
    window = life_window(data['tree'].graph['people'][pid])
    words = cell['words'] | cell['phrases']
    person = data['tree'].graph['people'][pid] | {'id': pid}
    def covered(form):
        target = norm(form_data(form)['text'])
        return any(fnmatchcase(target, w) if '*' in w or '?' in w else target == w
                   or source.get('search_match') == 'prefix' and target.startswith(w) for w in words)
    missing = set(form_data(f)['text'] for f in required if form_allowed(f, source, window, data['form_metadata'], person, cell.get('query_scripts', ()))
                  and not covered(f))
    order = {form: i for i, form in enumerate(data['form_metadata'])}
    return sorted(missing, key=lambda f: (norm(f) not in {norm(p) for p in cell['planned']}, order.get(norm(f), -1), norm(f)))


def record_visits(instance, tree, resolver, reviews=None):
    """Read records and corpus records as visits; name retrieval never establishes identity."""
    base = instance.path('records')
    paths = set(base.rglob('*.json')) if base.exists() else set()
    paths.update((instance.root / 'research' / 'team').glob('**/corpus/records/*.json'))
    seen = set()
    accepted = accepted_links(tree)
    reviews = reviews or {}
    for path in sorted(paths):
        if not path.resolve().is_relative_to(instance.root):
            continue
        try:
            record = json.loads(path.read_text(encoding='utf-8-sig'))
        except (ValueError, OSError):
            continue
        if not isinstance(record, dict) or analytical(record):
            continue
        digest = json.dumps(record, sort_keys=True, ensure_ascii=False)
        if digest in seen:
            continue
        seen.add(digest)
        source = record.get('source', {})
        sid = resolver.row_source({'source': source})
        if isinstance(source, dict):
            sid = sid or resolver.row_source({'source': source.get('kind'), 'url': source.get('url')})
            if not sid and (source.get('dgs') or source.get('fs_ark')):
                sid = 'familysearch-records'
        if not sid:
            continue
        # Only fields actually read, not links in a version, query or a collector's speculation.
        actual = {k: record[k] for k in ('person', 'people', 'subjects', 'fields', 'acts', 'reading', 'literal', 'text') if k in record}
        if not actual:
            continue
        primary = record.get('person')
        primary_words = tokens(text(primary))
        if isinstance(primary, dict):
            given = primary.get('name') or primary.get('given') or ''
            # A secondary name or a parent's name in a note is not the principal's given name.
            primary_words = tokens(text([primary.get('surname'), given.split()[0] if given else '']))
        primary_names = set(tree.match(primary_words)) if primary else set()
        names = tree.match(tokens(text(actual)))
        attributed, established = set(), set()
        keys = references(path.relative_to(instance.root).as_posix()) | references(record.get('id')) | references(source)
        for key in keys:
            established.update(accepted.get(key, ()))
        def walk(node):
            if isinstance(node, dict):
                for key in ('person', 'tree_id', 'id'):
                    value = node.get(key)
                    if isinstance(value, str) and (p := tree.person(value)):
                        attributed.add(p['id'])
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
            elif isinstance(node, str) and (p := tree.person(node)):
                attributed.add(p['id'])
        walk(actual)
        match = record.get('match') or {}
        if isinstance(match, dict) and (p := tree.person(match.get('tree_id'))):
            attributed.add(p['id'])
            if match.get('confidence') == 'same':
                established.add(p['id'])
        assessments = {pid: assessment for (pid, source_id, key), assessment in reviews.items() if source_id == sid and key in keys}
        attributed.update(established | assessments.keys())
        planning = {}
        primary_id = primary.get('id') if isinstance(primary, dict) else primary if isinstance(primary, str) else None
        primary_id = primary_id or (match.get('tree_id') if isinstance(match, dict) and match.get('confidence') == 'same' else None)
        if (p := tree.person(primary_id)) and record.get('status') not in {'rejected', 'disproved', 'hypothesis'} and (
                not isinstance(match, dict) or match.get('confidence') not in {'hypothesis', 'possible', 'probable', 'unknown', 'different', 'other'}):
            events = [e for e in record.get('events', []) if e.get('type') in {'birth', 'death'} and e.get('status') not in {'hypothesis', 'rejected', 'disproved'}]
            if isinstance(primary, dict):
                for kind in ('birth', 'death'):
                    value = primary.get(kind)
                    value = value.get('date') if isinstance(value, dict) else value
                    if value:
                        events.append({'type': kind, 'date': value})
            planning[p['id']] = events
        reading = record.get('read') or {}
        by = parse_by(reading.get('by') if isinstance(reading, dict) else reading)
        if isinstance(reading, dict) and reading.get('model'):
            by = parse_by(str(reading.get('by', '')) + ' / ' + reading['model'])
        # An already retrieved candidate may have a different surname but the
        # same given name; show its direct date/parent differences as well.
        given_words = set(tokens((primary.get('name') or primary.get('given') or '').split()[0])) if isinstance(primary, dict) and (primary.get('name') or primary.get('given')) else set()
        links = {pid: record_link(record, tree, pid, pid in primary_names or bool(given_words & tree.people[pid]['givens'])
                                  or primary_id == pid, pid in established, pid in attributed,
                                  pid in primary_names or primary_id == pid)
                 for pid in set(names) | attributed}
        for pid, link in links.items():
            if established and pid not in established and link['status'] == 'unestablished':
                link['status'] = 'other'
                link['linked_people'] = sorted(established)
            if assessment := assessments.get(pid):
                status = assessment['status']
                # A review cannot silently replace an accepted tree assertion.
                link['status'] = 'conflict' if (pid in established and status == 'other' or status == 'same' and link['differences']) else status
                link['review'] = assessment['search']
        yield {'source': sid, 'people': sorted(links), 'established': established, 'links': links,
               'by': by, 'at': reading.get('at', '') if isinstance(reading, dict) else '',
               'planning_events': planning,
               'record': path.relative_to(instance.root).as_posix()}


def record_link(record, tree, pid, principal, established, attributed=False, named=True):
    """A queue assessment, never an identity decision saved to the family."""
    match = record.get('match') if isinstance(record.get('match'), dict) else {}
    roles = [s.get('role') for s in record.get('subjects', []) if isinstance(s, dict) and s.get('person') == pid]
    result = {'status': 'same' if established else 'unestablished' if principal or attributed else 'mention',
              'confidence': match.get('confidence'), 'roles': roles, 'differences': []}
    if match.get('confidence') in {'other', 'different'} and (principal or attributed):
        result['status'] = 'conflict' if established else 'other'
    if roles and all(r in {'father', 'mother', 'witness', 'relative', 'context', 'mention'} or
                     isinstance(r, str) and r.startswith('co-defendant') for r in roles) and not established:
        result['status'] = 'mention'
        return result
    if not principal:
        return result
    from familiar.tree.life import _birth_bounds
    person = record.get('person')
    person = person if isinstance(person, dict) else {}
    birth = person.get('birth')
    birth = birth.get('date') if isinstance(birth, dict) else birth
    actual = _birth_bounds(birth)
    target = tree.graph['people'][pid]
    known = [b for e in target.get('events', []) if (e.get('type') == 'birth' or e.get('tag') == 'BIRT')
             and e.get('status') not in {'hypothesis', 'rejected', 'disproved'} and (b := _birth_bounds(e.get('date')))]
    if actual and known and all(actual[1] < b[0] or actual[0] > b[1] for b in known):
        result['differences'].append({'field': 'birth', 'record': birth,
                                      'person': [list(b) for b in known]})
    parents = {role: tree.graph['people'].get(f.get(role)) for f in tree.graph.get('families', [])
               if pid in f.get('children', []) for role in ('husband', 'wife') if f.get(role)}
    for relative in record.get('relatives', []):
        if not isinstance(relative, dict):
            continue
        role = {'father': 'husband', 'отец': 'husband', 'mother': 'wife', 'мать': 'wife'}.get(relative.get('relation'))
        if role in parents and parents[role]:
            expected = set(tokens(text(parents[role].get('names'))))
            observed = set(tokens(relative.get('name') or ''))
            # Distinct given names are useful only after dictionary expansion.
            givens = {v for n in parents[role].get('names', []) for v in tokens(n.get('given') or '')}
            allowed = givens | {v for g in givens for v in tree.groups.get(g, ())}
            if observed and givens and not observed.intersection(allowed):
                result['differences'].append({'field': role, 'record': relative.get('name'),
                                              'person': sorted(expected)})
    if result['differences']:
        result['status'] = 'other' if not established else 'conflict'
    elif not named and not attributed and not established and result['status'] != 'other':
        result['status'] = 'mention'
    return result
