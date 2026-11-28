"""Read the family lines and summarize the research approaches available to each."""
import re
from collections import defaultdict

from familiar.instance import asks, blanks, correspondence
from familiar.instance.gate import boundary, fixed_inputs
from familiar.tree.life import _birth_bounds

from .coverage import (CLOSED_OPTIONS, OPEN_EXCLUSIONS, applicability, collect, control_basis, line_members,
                       selected_lines, surname_keys)
from .coverage_context import contains, episode_fit, planning_windows, script_of, text
from .search_ledger import row_digest
from .search_plays import (bridge_link, links_to_living, place_term, query_label, query_mode, query_places,
                           query_surnames, registry, source_classes)
from .search_variants import _entries, norm


def matches_line(line, people, data, row):
    aim = row.get('aim') or {}
    about = row.get('about') or {}
    surname = aim.get('line') or about.get('line') or row.get('line')
    if surname:
        return bool(surname_keys(surname, data['language']) & line.forms)
    ids = [*row.get('people', []), *aim.get('people', []), about.get('person')]
    aliases = data['tree'].aliases
    return any(aliases.get(pid, pid) in people for pid in ids)


def recorded_places(person):
    card = person.get('cardPresentation') or {}
    places = [card.get('place'), *person.get('places', []),
              *(event.get('place') for event in person.get('events', [])
                if event.get('status') not in {'hypothesis', 'rejected', 'disproved'})]
    return list(dict.fromkeys(v.strip() for v in places if isinstance(v, str) and v.strip()))


def variants_for_place(places, entries, *, prefixes=False):
    return [entry for entry in entries if any(
        place_term(place, entry['names']) if prefixes else any(contains(place, form) for form in entry['names'])
        for place in places)]


def place_entries(instance):
    entries = []
    for entry in _entries(instance):
        if entry.get('kind') != 'place':
            continue
        name = entry.get('canonical') or next((f['text'] for f in entry['forms'] if f['text']), '')
        if name:
            forms = [f for f in entry['forms'] if f.get('status') not in {'rejected', 'disproved'} and f['text']]
            entries.append({'name': name, 'forms': forms, 'names': {norm(name), *(norm(f['text']) for f in forms)}})
    return entries


def weighted_place(claim, entries):
    """An origin claim can guide a search while remaining a version."""
    if not isinstance(claim, dict):
        return None
    weight = claim.get('weight')
    if (type(weight) not in (int, float) or not .3 <= weight <= 1
            or claim.get('status', claim.get('state')) in CLOSED_OPTIONS | {'disproved', 'conflict'}):
        return None
    if isinstance(place := claim.get('place'), str) and place.strip():
        return weight, place.strip()
    # Older labels may name the origin directly. Limit dictionary matching to
    # the origin phrase, leaving out parenthetical parishes and supporting prose.
    label = text(claim.get('label') or claim.get('text'))
    origin = re.search(r'\b(?:from|born in|native of|из|родил\w* в|урожен\w*)\s+([^,();.\n]+)', label, re.I)
    phrase = origin[1] if origin and not re.search(r'\b(?:not|never|не|никогда)\b', label[:origin.start()], re.I) else ''
    exact = norm(label)
    matches = {entry['name'] for entry in entries if exact in entry['names'] or
               phrase and any(contains(phrase, name) for name in entry['names'])}
    if len(matches) == 1:
        return weight, matches.pop()
    return None


def nest_target(data, line, members, entries):
    tree = data['tree']
    versions = defaultdict(list)
    for question in data['versions'].values():
        if (question.get('status', question.get('state')) in OPEN_EXCLUSIONS
                or not matches_line(line, members, data, question)):
            continue
        for option in question.get('versions') or []:
            if not (place := weighted_place(option, entries)):
                continue
            for pid in option.get('people') or question['people']:
                if isinstance(pid, str):
                    versions[tree.aliases.get(pid, pid)].append(place)
    for pid in reversed(line.chain):
        if pid in data['living']:
            continue
        person = tree.graph['people'][pid]
        if places := recorded_places(person):
            return places[0], None
        claims = versions[pid] + [place for fact in person.get('facts', []) if (place := weighted_place(fact, entries))]
        if claims:
            weight, place = max(claims, key=lambda item: item[0])
            return place, weight
    return None, None


def same_place(places, names):
    return any(contains(place, name) for place in places for name in names)


def nest_row_matches(row, names):
    query = row.get('query')
    if not isinstance(query, dict):
        return False
    if place := text(query.get('place')):
        return same_place([place], names)
    return same_place(query_places(row), names) or norm(text(query.get('query'))) in names


def family_connection(graph, root):
    """People connected to the family through parentage or unions at weight ≥0.5."""
    neighbors = defaultdict(set)
    edges = graph.get('edges', [])
    explicit = {(edge['parent'], edge['child']) for edge in edges}
    pairs = [(edge['parent'], edge['child']) for edge in edges if bridge_link(edge)]
    for family in graph.get('families', []):
        if bridge_link(family, default_status='export'):
            parents = family.get('husband'), family.get('wife')
            pairs.append(parents)
            pairs.extend((parent, child) for parent in parents for child in family.get('children', [])
                         if (parent, child) not in explicit)
    for left, right in pairs:
        if left in graph['people'] and right in graph['people']:
            neighbors[left].add(right)
            neighbors[right].add(left)
    connected, pending = {root}, [root]
    for pid in pending:
        new = neighbors[pid] - connected
        connected.update(new)
        pending.extend(new)
    return connected


def nest_candidates(data, line, names, entries):
    tree = data['tree']
    excluded = data['family_connection'] | set(line.chain) | data['living']
    count = 0
    for pid, person in tree.graph['people'].items():
        if pid in excluded or not person.get('author'):
            continue
        forms = tree.people[pid]['surnames']
        surname = (any(surname_keys(form, data['language']) & line.forms for form in forms) if forms
                   else any(contains(person.get('name', ''), form) for form in line.forms))
        if not surname:
            continue
        places = recorded_places(person) + [place[1] for fact in person.get('facts', [])
                                            if (place := weighted_place(fact, entries))]
        count += same_place(places, names)
    return count


def journal_period(value):
    """Use a single year or a bounded interval written as the read scope."""
    if isinstance(value, list) and len(value) == 2 and all(type(year) is int for year in value):
        value = f'{value[0]}-{value[1]}'
    if match := re.fullmatch(r'([12]\d{3})(?:\s*[-–—]\s*([12]\d{3}))?', str(value).strip()):
        first, last = int(match[1]), int(match[2] or match[1])
        return range(first, last + 1)
    return range(0)


def nest_open_period(observations, closed):
    """A completed scope can only cover years at its own source and place."""
    logged, complete = defaultdict(set), defaultdict(set)
    for obs in observations:
        sid = obs['source']
        coverage = obs['row'].get('coverage')
        if not sid or not isinstance(coverage, dict):
            continue
        years = journal_period(coverage.get('years'))
        logged[sid].update(years)
        if coverage.get('complete') is True and obs['kind'] in {'found', 'zero-controlled', 'zero-uncontrolled'}:
            complete[sid].update(years)
    open_years = set()
    for sid, years in logged.items():
        remaining = years - complete[sid]
        if remaining:
            closed.discard(sid)
            open_years.update(remaining)
    if open_years:
        first = last = min(open_years)
        while last % 10 < 9 and last + 1 in open_years:
            last += 1
        return [first, last]
    return None


def keeper_matrix(places, place_forms, sources):
    """The area covered by a collection is separate from its catalogue language."""
    grouped = defaultdict(lambda: {'sources': set(), 'languages': set(), 'scripts': set()})
    for sid, source in sources.items():
        if country := source.get('holder_country'):
            entry = grouped[country]
            entry['sources'].add(sid)
            entry['languages'].update(source.get('catalogue_languages', source.get('search_languages', [])))
            entry['scripts'].update(source.get('catalogue_scripts', source.get('search_scripts', [])))

    rows = []
    known_names = set()
    for entry in place_forms:
        known_names.update(entry['names'])
        place = entry['name']
        rows.append((place, entry['forms']))
    rows.extend((place, [{'text': place}]) for place in places
                if not any(contains(place, name) for name in known_names))
    gaps = []
    for place, forms in rows:
        languages = {form.get('language') for form in forms} - {None, '', 'und'}
        scripts = {form.get('script') or script_of(form['text']) for form in forms}
        for country, entry in sorted(grouped.items()):
            missing_languages = sorted(entry['languages'] - languages)
            missing_scripts = sorted(entry['scripts'] - scripts)
            if missing_languages or missing_scripts:
                gaps.append({'place': place, 'country': country, 'sources': sorted(entry['sources']),
                             'missing_languages': missing_languages, 'missing_scripts': missing_scripts,
                             'has_untagged_forms': any(f.get('language') in {None, '', 'und'} for f in forms)})
    return gaps


def line_observations(data, line, members, known_places, nest_names):
    groups = defaultdict(list)
    unknown, seen, visited = [], set(), set()
    catalogue = data['resolver'].catalog.sources
    surnames = line.forms | {name for pid in members for name in data['tree'].people[pid]['surnames']}
    for obs in data['observations']:
        row = obs['row']
        question = data['versions'].get(row.get('question'), {})
        assigned_line = question.get('line')
        sid = obs['source']
        source = source_classes(sid, catalogue.get(sid, {}))
        if assigned_line:
            if not surname_keys(assigned_line, data['language']) & line.forms:
                continue
        elif members.isdisjoint(obs['people']) and members.isdisjoint(question.get('people', [])):
            if (row.get('people') or question.get('people') or not (
                    nest_row_matches(row, nest_names) and query_label(row, source)[0] == 'place-nest'
                    and any(contains(value, form) for value in query_surnames(row) for form in surnames))):
                continue
        ident = row.get('id_as_written') or row.get('id') or row_digest(row)
        if ident in seen:
            continue
        seen.add(ident)
        play, basis = query_label(row, source, known_places, surnames)
        if play is None:
            unknown.append(ident)
        else:
            groups[play].append(obs | {'attribution': basis})
        if sid:
            visited.add(sid)
    return groups, unknown, visited


def home_and_archive(instance):
    feedback = asks.latest_feedback(row for _, row in asks.rows(instance._inside('family/feedback/inbox')))
    local_asks = [row | {'state': asks.current(row, feedback.get(row['id']))[0]}
                  for _, row in asks.rows(instance.path('asks'))]
    letters = [row for _, row in correspondence.rows(instance)
               if (row.get('kind') or row.get('channel')) == 'archive' and row.get('state') != 'not_needed']
    return local_asks, letters


def subject_inputs(data, line, members, source_options, witness, sent_or_drafted, line_place=False, ledger=()):
    """`line_place`: the ledger, a version or a told fact places the line; `ledger`: the access ledger's places of it."""
    from . import access_ledger
    parish, keeper = access_ledger.names_parish(ledger), access_ledger.answers_letters(ledger)
    graph = data['tree'].graph
    people = graph['people']
    household = set()
    for family in graph.get('families', []):
        if family.get('status') in {'conflict', 'rejected', 'disproved', 'hypothesis'}:
            continue
        ids = {family.get('husband'), family.get('wife'), *family.get('children', [])} & people.keys()
        names = {norm(next((n['given'] for n in people[pid].get('names', []) if n.get('given')), ''))
                 for pid in ids} - {''}
        if len(names) >= 3:
            household.update(ids & members)
    living, linked = data['living'], data['linked']
    subjects = {}
    frontier = line.chain[-1]
    for pid in [frontier, *sorted(members - {frontier})]:
        person = people[pid]
        events = person.get('events', []) + data['planning_events'].get(pid, [])
        fields = person | {'events': events}
        ((lo, hi), _) = planning_windows(fields)
        known_birth = lo is not None and hi - lo <= 20
        death = [e for e in events if e.get('type') == 'death' or e.get('tag') == 'DEAT']
        places = recorded_places(fields)
        placed = bool(places) or line_place and pid not in living
        context = data['contexts'].get(pid)
        relevant = [source for sid, source in source_options.items()
                    if not {'epoch', 'region'}.intersection(applicability(data, pid, sid, context))]
        subjects[pid] = {
            'surname': bool(line.surname), 'place': placed, 'historical_place': placed and pid not in living,
            'witness': witness or pid in living,
            'registrar': sent_or_drafted or keeper or any(src.get('kind') in {'archive', 'registry'}
                                                for src in relevant),
            'year_or_household': known_birth or pid in household or
                                 any(_birth_bounds(e.get('date')) for e in events),
            'household': pid in household,
            'parish': parish and pid not in living or bool(fields.get('parish') or any(e.get('parish') for e in events)),
            'birth_year': known_birth,
            'episode': any(episode_fit(fields, source) > 0 for source in relevant)
                       or any(e.get('type') in {'military', 'emigration', 'deportation', 'repression', 'refugee'}
                              and e.get('place') for e in events),
            'burial': any((e.get('type') == 'burial' or e.get('tag') == 'BURI') and e.get('place') for e in events),
            'death_years': any(_birth_bounds(e.get('date')) for e in death) or bool(_birth_bounds(fields.get('death'))),
            'act_names': pid in data['read_acts'],
            'guide': any(src.get('kind') in {'archive', 'finding-aid', 'reference'}
                         and {'archive-guide', 'inventory', 'census-revision', 'consistory'} & set(src.get('classes', []))
                         for src in relevant),
            'bridge': pid in linked and placed,
        }
    return subjects


def missing_inputs(play, subjects, line, groups, open_people, nest_place):
    pid = play['id']
    required = play['requires']
    choices = list(subjects.values())
    if pid == 'place-nest':
        choices = [{'surname': bool(line.surname), 'nest_place': bool(nest_place)}]
    elif pid == 'deep-inventories':
        choices = [subjects[line.chain[-1]]]
    elif pid == 'generation-events':
        choices = [values for subject, values in subjects.items()
                   if subject == line.chain[-1] or subject in open_people and values['episode']]
    # A deliberately selected parish is a usable search target even before identity is resolved.
    parish_selected = any(isinstance(obs['row'].get('query'), dict) and obs['row']['query'].get('parish')
                          for obs in groups.get('household-fingerprint', []) + groups.get('surname-place', []))
    return min(([key for key in required if not facts[key] and not (key == 'parish' and parish_selected)]
                for facts in choices), key=len)


def closed_sources(pid, observations, gaps):
    """Only a recorded end of the relevant scope can close an approach."""
    if pid == 'keeper-forms' and gaps:
        return set()
    # Earlier partial searches remain history. Close a route only after the
    # latest observation that explicitly covers its date and place scope.
    by_source = defaultdict(list)
    for obs in observations:
        by_source[obs['source']].append(obs)
    closed = set()
    for sid, history in by_source.items():
        obs = max(reversed(history), key=lambda item: str(item['row'].get('at') or ''))
        row = obs['row']
        coverage = row.get('coverage') or {}
        clean = [item['row'] for item in history if item['kind'] in {'found', 'zero-controlled', 'zero-uncontrolled'}]
        controlled = any(control_basis(item) for item in clean)
        if pid == 'forums':
            topics_read = any(isinstance(r.get('query'), dict) and query_mode(r['query']) == 'read-topic'
                              and r.get('hits', 0) > 0 for r in clean)
            if controlled and topics_read:
                closed.add(sid)
                continue
        if not isinstance(coverage, dict) or coverage.get('complete') is not True:
            continue
        if obs['kind'] in {'unrecorded', 'query-dubious'}:
            continue
        if obs['kind'] == 'gap' and not (pid in {'generation-events', 'household-fingerprint'} and
                                         coverage.get('available_online') is False):
            continue
        if pid not in {'keeper-forms', 'forums'} or controlled:
            closed.add(sid)
    return closed


def plan_line(data, line, entries, asks_on_disk, letters_on_disk, lang, horizon=None):
    chain, surname, forms = line.chain, line.surname, line.forms
    members = line_members(data, chain)
    people = data['tree'].graph['people']
    places = list(dict.fromkeys(place for pid in chain for place in recorded_places(people[pid])))
    name_forms = {form for entry in entries for form in entry['names']}
    nest_place, nest_weight = nest_target(data, line, members, entries)
    from . import access_ledger
    ledger = access_ledger.line_places(data, data.get('ledger', []), line, members, [nest_place])
    if nest_place is None and ledger:
        nest_place = max(ledger, key=lambda p: len(access_ledger.unread(p)))['place']
    # The line has a place when the ledger, a version from 0.3 up or a told fact gives one, whatever the cards record.
    told = [place[1] for pid in chain if pid not in data['living'] for fact in people[pid].get('facts', [])
            if (place := weighted_place(fact, entries))]
    line_place = bool(nest_place or ledger or told)
    places = list(dict.fromkeys([*places, *(p['place'] for p in ledger), *filter(None, [nest_place]), *told]))
    place_forms = variants_for_place(places, entries)
    nest_names = {norm(nest_place)} if nest_place else set()
    if nest_names:
        nest_names |= {name for entry in entries if norm(nest_place) in entry['names'] for name in entry['names']}
    groups, unknown, visited = line_observations(data, line, members, name_forms, nest_names)
    open_people = {data['tree'].aliases.get(pid, pid) for q in data['versions'].values()
                   if q.get('status', q.get('state')) not in OPEN_EXCLUSIONS and matches_line(line, members, data, q)
                   for pid in q['people']}
    local_asks = [row for row in asks_on_disk if matches_line(line, members, data, row)]
    letters = [row for row in letters_on_disk if matches_line(line, members, data, row)]
    sources = {sid: source for sid, source in data['resolver'].catalog.sources.items()
               if sid in visited or any(not applicability(data, pid, sid, data['contexts'].get(pid))
                                        for pid in chain if recorded_places(people[pid]))}
    known_witness = any(isinstance(row.get('holder'), str) and
                        data['tree'].aliases.get(row['holder'], row['holder']) in data['living']
                        for row in local_asks)
    subjects = subject_inputs(data, line, members, sources, known_witness, bool(letters), line_place, ledger)
    keeper_rows = [obs['row'] for obs in groups.get('keeper-forms', []) if isinstance(obs['row'].get('query'), dict)]
    query_terms = [p for row in keeper_rows for p in [*query_places(row), row['query'].get('query')] if isinstance(p, str)]
    extra_places = variants_for_place(query_terms, entries, prefixes=True)
    considered_places = {entry['name']: entry for entry in [*place_forms, *extra_places]}
    gaps = keeper_matrix(places, list(considered_places.values()), sources)

    plays = []
    for order, enabled, play in data['play_settings'].choices(forms, lambda name: surname_keys(name, data['language'])):
        pid = play['id']
        observations = groups.get(pid, [])
        searched = sorted({obs['source'] for obs in observations if obs['source']})
        cells = {key for obs in observations for key in obs['cells'] if key[0] in members and key in data['cells']
                 and not data['not_applicable'].get(key)}
        ceilings = sorted(sid for sid in {sid for _, sid in cells}
                          if all(data['cells'][key]['ceiling'] >= 3 for key in cells if key[1] == sid))
        missing = missing_inputs(play, subjects, line, groups, open_people, nest_place)
        scoped = ([obs for obs in observations if obs['source'] and nest_row_matches(obs['row'], nest_names)]
                  if pid == 'place-nest' else observations)
        closed = closed_sources(pid, scoped, gaps)
        period = nest_open_period(scoped, closed) if pid == 'place-nest' else None
        tried, exhausted = bool(observations), bool(closed) and all(obs['source'] in closed for obs in scoped)
        draft_count = 0
        if pid == 'surname-place':
            exhausted = bool(ceilings) and ceilings == searched
        if pid == 'ask-family' and local_asks:
            states = {row.get('state') for row in local_asks}
            tried |= bool(states - {'proposed'})
            exhausted = bool(states) and states <= {'answered', 'dont_know'}
        if pid == 'ask-family' and horizon:
            missing, state = [], 'closed'  # the family said nobody is left to ask: not a missing input, a decision
        if pid == 'archive-letters' and letters:
            states = {row.get('state') for row in letters}
            draft_count = sum(r.get('state') in {'draft', 'ready'} for r in letters)
            tried |= bool(states & {'sent', 'answered'}) or any(row.get('replies') for row in letters)
            exhausted = all(row.get('state') == 'answered' or row.get('state') == 'closed' and row.get('replies')
                            for row in letters)
        if not (pid == 'ask-family' and horizon):
            state = ('disabled' if not enabled else 'exhausted' if exhausted and pid == 'ask-family'
                     else 'not-applicable' if missing else 'exhausted' if exhausted
                     else 'in-progress' if tried else 'untried')
        result = {'id': pid, 'title': play['title'][lang], 'purpose': play['purpose'][lang], 'order': order,
                  'state': state, 'missing': missing, 'needs': [registry()['inputs'][key][lang] for key in missing],
                  'source_classes': play['classes'], 'sources_tried': searched, 'ceiling_sources': ceilings,
                  'journal_passes': len(observations), 'inferred_passes': sum(o['attribution'] == 'inferred' for o in observations),
                  'exhaustion': play['exhaustion'][lang], 'cost': play['cost'][lang], 'next': play['next'][lang]}
        if closed - {None}:
            result['closed_sources'] = sorted(closed - {None})
        if state == 'in-progress' and 'continue' in play:
            result['next'] = play['continue'][lang]
        if draft_count:
            result['drafts'] = draft_count
        if pid == 'keeper-forms':
            result['place_form_gaps'] = gaps
        if pid == 'place-nest' and nest_place:
            result['place'] = nest_place
            result['candidate_count'] = nest_candidates(data, line, nest_names, entries)
            if nest_weight is not None:
                result['place_weight'] = nest_weight
            result['next'] = f"{nest_place} · {result['next']}"
            if period:
                result['earliest_open_period'] = period
                years = period_label(period)
                result['next'] = (f'{nest_place} · Начни с периода {years} и проследи дворы до разрыва, '
                                  'заглядывая в соседние приходы.' if lang == 'ru' else
                                  f'{nest_place} · Start with {years} and trace the households to the break, '
                                  'checking neighboring parishes.')
        plays.append(result)
    found = {}
    if horizon:
        # Gathered material is the story now: indirect signs first, letters and inventories as options.
        closed = registry()['closed_horizon']
        for play in plays:
            play['option'] = play['id'] in closed['options']
        rank = {pid: n for n, pid in enumerate(closed['first'])}
        plays.sort(key=lambda p: (p['id'] == 'ask-family', p['option'], rank.get(p['id'], len(rank))))
        found = {'horizon': {k: data['text'](v) for k, v in horizon[1].items()} | {'line': horizon[0]},
                 'signs': [sign[lang] for sign in closed['signs']]}
    next_play = next((p for p in plays if p['state'] in {'untried', 'in-progress'}), None)
    for play in plays:
        play['step'] = play['next']
        if play is not next_play:
            play.pop('next')
    return {'surname': surname, 'start': chain[0], 'frontier': chain[-1], 'people': chain, 'plays': plays,
            'unrecorded_play': unknown, 'ledger': ledger} | found


@boundary('diagnostic')
@fixed_inputs()
def plan(instance, *, line=None):
    data = collect(instance, for_plan=True)
    data['living'], data['linked'] = links_to_living(data['tree'].graph)
    data['family_connection'] = family_connection(data['tree'].graph, data['lines'][0][0] if data['lines'] else None)
    entries = place_entries(instance)
    data['place_entries'] = entries
    local_asks, letters = home_and_archive(instance)
    lang = 'ru' if instance.source_language == 'ru' else 'en'
    closed = asks.horizons(instance)
    data['text'] = lambda value: value if isinstance(value, str) else (value or {}).get(instance.source_language) or next(
        iter((value or {}).values()), '')
    chosen = selected_lines(data, line)
    from . import access_ledger
    _, data['ledger'], _ = access_ledger.read(instance)
    lines = [plan_line(data, row, entries, local_asks, letters, lang,
                       next(((name, entry) for name, entry in closed.items() if surname_keys(name, data['language'])
                             & row.forms), None))
             for row in chosen]
    from .search_map import map_line, prepare, read_series
    _, series_rows, _ = read_series(instance)
    if series_rows:
        prepare(instance, data)
    family = blanks.Family(instance, data['tree'].graph, data['living'])
    feedback = blanks.inbox(instance)
    words = access_ledger.words_for(instance, instance.source_language if lang == 'ru' else 'en')
    for view_line, row in zip(lines, chosen):
        record_map = map_line(data, row, series_rows) if series_rows else None
        open_record(view_line, record_map, lang)
        access_ledger.steer(view_line, view_line.pop('ledger'), record_map, words, lang)
        thin_first(view_line, family, list(data['versions'].values()), feedback, local_asks, lang)
        for play in view_line['plays']:
            play.pop('step')
    view = {'schema': 1, 'lines': lines}
    from familiar.instance.subjects import protected_names
    from familiar.tree.builder import people_index
    return view, protected_names(instance, people=people_index(data['tree'].graph)).sub('…', markdown_plan(view, lang, words))


SKELETON_PLAYS = ('place-nest', 'role-lists', 'place-administration', 'keeper-forms')


def thin_first(line, family, versions, feedback, local_asks, lang):
    """A person known by little more than a name: the relatives see the card first, then the place and the small
    lists; a surname in name bases is no first move."""
    from familiar.desk.model import words
    pid = next((p for p in line['people'] if family.people[p].get('life_assessment', {}).get('status') == 'dead'
                and blanks.thin(family, p)), None)
    if pid is None:
        return
    w, person, ru = words(family.instance, 'ru' if lang == 'ru' else 'en')['blanks'], family.people[pid], lang == 'ru'

    def label(field):
        return w['field_' + field + ('_' + (family.sex(pid) or 'm') if field == 'spouse' else '')]

    def said(value):
        return value if isinstance(value, str) else value.get(lang) or next(iter(value.values()), '')

    missing, father = family.missing(pid), family.father_guess(pid)
    guesses = [f"{label('father')}: {father['value']} ({father['weight']:g})"] if father else []
    guesses += [f"{label(field)}: {said(g['value'])} ({g['weight']:g})" for (who, field), g
                in blanks.version_guesses(versions, family.aliases).items() if who == pid and field in missing]
    skeleton, drifting = layered(family, pid)
    reachable = family.askable(pid) and not line.get('horizon')
    shown = blanks.shown_before(family, pid, feedback, local_asks)
    line['thin'] = {'person': pid, 'name': person.get('name') or pid, 'missing': missing, 'guesses': guesses,
                    'labels': [label(field) for field in missing], 'reachable': reachable, 'shown': shown,
                    'skeleton': skeleton, 'attributes': drifting}
    current = next((p for p in line['plays'] if 'next' in p), None)
    if current and current['id'] == 'surname-place' and not line.get('next') and (better := next(
            (p for p in line['plays'] if p['id'] in SKELETON_PLAYS and p['state'] in {'untried', 'in-progress'}), None)):
        current.pop('next')
        better['next'] = better['step']
        current = better
    if reachable and not shown:
        step = line.get('next') or (current or {}).get('next', '')
        for play in line['plays']:
            play.pop('next', None)
        line['next'] = (f"Показать родным карточку «{line['thin']['name']}» с пустыми местами и нашей догадкой: одно слово "
                        'заменяет сотни запросов. Место и малые списки — следом, базы по фамилии — после них.' if ru else
                        f"Show the relatives the card of {line['thin']['name']} with its blanks and our guess: one word replaces "
                        'hundreds of queries. The place and the small lists come next, surname bases after them.')
        line['meanwhile'] = ' '.join(filter(None, [step, line.get('meanwhile')]))


def layered(family, pid):
    """What the family told around this person: names, villages and parentage hold, dates may drift. A statement
    marked as an attribute at intake moves what rests on it to the drifting side."""
    from familiar.intake.layers import statements
    people, circle = family.people, [pid, *family.down(pid)]
    cited = {s for p in circle for key in ('names', 'events') for row in people[p].get(key) or [] for s in row.get('provenance') or []}
    soft = {ident for ident, layers in statements(family.instance, cited) if layers == ['attribute']}
    holds, drifts = [], []
    for p in circle:
        for name in family.names(p)[:1]:
            text = name.get('display') or ' '.join(filter(None, (name.get('given'), name.get('surname'))))
            (drifts if set(name.get('provenance') or ['']) <= soft else holds).append(text)
        for event in people[p].get('events') or []:
            if isinstance(event.get('place'), str) and event['place'].strip():
                holds.append(event['place'].strip())
            if event.get('type') in {'birth', 'death'} and isinstance(event.get('date'), str) and event['date'].strip():
                drifts.append(f"{family.given(p)}: {event['date'].strip()}")
    return [list(dict.fromkeys(filter(None, values)))[:7] for values in (holds, drifts)]


def thin_lines(thin, lang):
    ru = lang == 'ru'
    head = f"**{'Тонкое звено' if ru else 'Thin link'} · {thin['name']}** · "
    head += ('не хватает: ' if ru else 'missing: ') + ', '.join(v.lower() for v in thin['labels'])
    if thin['guesses']:
        head += ('; догадка — ' if ru else '; our guess: ') + ', '.join(thin['guesses'])
    if not thin['reachable']:
        head += '; спросить некого' if ru else '; nobody alive to ask'
    elif thin['shown']:
        head += '; родные о нём уже говорили' if ru else '; relatives have already spoken of it'
    else:
        head += '; родным карточку не показывали' if ru else '; no relative has seen the card'
    out = [head + '.']
    if thin['skeleton']:
        out.append(('Каркас, на него опираться: ' if ru else 'Skeleton, lean on it: ') + '; '.join(thin['skeleton']))
    if thin['attributes']:
        out.append(('Признаки, могут плыть: ' if ru else 'Attributes, they may drift: ') + '; '.join(thin['attributes']))
    return [*out, '']


RECORD_PLAYS = {'ask-family', 'archive-letters'}


def open_record(line, record_map, lang):
    """Exhausted is a statement about the search map: open online years in the window keep the line open."""
    if record_map is None:
        if any(p['state'] == 'exhausted' for p in line['plays']):
            line['record_map'] = 'unknown'  # no series list: whether the open record is read is not known
        return
    runs = [r for r in record_map['next'] if r['in_window'] and r['cost'] <= 1]
    if not record_map['open_online_in_window']:
        return
    titles = {s['id']: s.get('title') or f"{s['kind']} · {s['place']}" for s in record_map['series']}
    line['open_record'] = {'years': record_map['open_online_in_window'],
                           'read_first': [{'series': r['series'], 'title': titles[r['series']], 'years': r['years'],
                                           'state': r['state']} for r in runs[:3]]}
    for play in line['plays']:
        if play['state'] == 'exhausted' and play['id'] not in RECORD_PLAYS:
            play['state'] = 'in-progress'
            play['reopened_by'] = 'search-map'
        if play['ceiling_sources']:
            play['repeat_ceiling'], play['ceiling_sources'] = play['ceiling_sources'], []
    current = next((p for p in line['plays'] if 'next' in p), None)
    if runs and (current is None or current['id'] in RECORD_PLAYS):
        first = runs[0]
        years = period_label(first['years'])
        if current:
            current.pop('next')
        line['next'] = (f"Прочитать {titles[first['series']]} {years} целиком: книги онлайн, в окне вопроса."
                        if lang == 'ru' else
                        f"Read {titles[first['series']]} {years} in full: the books are online, in the question's window.")


def horizon_lines(horizon, signs, lang):
    ru = lang == 'ru'
    head = (f"**Семья больше ничего не скажет** с {horizon['since']} ({horizon['by']}). Вопросы родным не ставим; "
            'историю составляем из собранного, ведущую версию называем в `story_choice`.' if ru else
            f"**The family can say no more** since {horizon['since']} ({horizon['by']}). We ask relatives nothing; "
            'the story is told from what we gathered, its leading version named in `story_choice`.')
    out = [head]
    if horizon.get('known'):
        out.append(('Косвенно известно: ' if ru else 'Known indirectly: ') + horizon['known'])
    if horizon.get('reopen_when'):
        out.append(('Открыть снова: ' if ru else 'Open again when: ') + horizon['reopen_when'])
    out.extend(['', 'Косвенные признаки:' if ru else 'Indirect signs:', *(f'- {sign}' for sign in signs), ''])
    return out


def period_label(period):
    first, last = period
    return str(first) if first == last else f'{first}–{last}'


def markdown_plan(view, lang, words):
    from .access_ledger import plan_lines
    heading = 'План поиска' if lang == 'ru' else 'Research plan'
    table = '| Подход | Состояние | Журнал |' if lang == 'ru' else '| Approach | State | Journal |'
    states = {'disabled': 'выключен', 'not-applicable': 'не применим', 'exhausted': 'исчерпан',
              'in-progress': 'идёт', 'untried': 'не пробовали', 'closed': 'спросить некого',
              'no-access': 'нет доступа из дома'} if lang == 'ru' else {
              'disabled': 'disabled', 'not-applicable': 'not applicable', 'exhausted': 'exhausted',
              'in-progress': 'in progress', 'untried': 'untried', 'closed': 'nobody left to ask',
              'no-access': 'no access from home'}
    write_next = 'Следующий шаг' if lang == 'ru' else 'Next step'
    no_play = 'Подход не записан' if lang == 'ru' else 'Approach not recorded'
    out = [f'# {heading}', '']
    for line in view['lines']:
        out.extend([f"## {line['surname'] or line['start']}", ''])
        if horizon := line.get('horizon'):
            out.extend(horizon_lines(horizon, line['signs'], lang))
        if line.get('thin'):
            out.extend(thin_lines(line['thin'], lang))
        out.extend(plan_lines(line['access'], words, lang))
        out.extend([table, '|---|---|---|'])
        for play in line['plays']:
            state = states[play['state']]
            if play['state'] == 'not-applicable':
                state += ' · ' + ', '.join(play['needs'])
            if play.get('holders'):
                state += ' · ' + '; '.join(play['holders'])
            if play.get('option'):
                state += ' · ' + ('опция' if lang == 'ru' else 'option')
            activity = str(play['journal_passes'])
            if play['ceiling_sources']:
                activity += ' · ' + ('потолок ' if lang == 'ru' else 'ceiling ') + ', '.join(play['ceiling_sources'])
            if play.get('closed_sources'):
                activity += ' · ' + ('закрыто ' if lang == 'ru' else 'closed ') + ', '.join(play['closed_sources'])
            if play.get('drafts'):
                activity += ' · ' + str(play['drafts']) + (' черновика' if lang == 'ru' else ' drafts')
            if play.get('place'):
                activity += ' · ' + play['place']
                if 'place_weight' in play:
                    weight = f"{play['place_weight']:g}"
                    activity += (f" (версия {weight.replace('.', ',')})" if lang == 'ru' else f' (hypothesis {weight})')
            if play.get('candidate_count'):
                label = 'кандидатов' if lang == 'ru' else 'candidates'
                activity += f" · {label} {play['candidate_count']}"
            if period := play.get('earliest_open_period'):
                label = 'открытый период' if lang == 'ru' else 'open period'
                activity += f' · {label} {period_label(period)}'
            out.append(f"| {play['title']} | {state} | {activity} |")
        out.extend(['', f"{no_play} · {len(line['unrecorded_play'])}"])
        next_play = next((p for p in line['plays'] if 'next' in p), None)
        if record := line.get('open_record'):
            first = ', '.join(f"{r['title']} {period_label(r['years'])}" for r in record['read_first'])
            out.extend(['', (f"**Открытые книги** · в окне вопроса не прочитано онлайн-лет: {record['years']}; "
                             f"сначала {first} (`research map`)" if lang == 'ru' else
                             f"**Open record** · online years unread in the question's window: {record['years']}; "
                             f"first {first} (`research map`)")])
        elif line.get('record_map') == 'unknown':
            out.extend(['', 'Ряды книг не описаны: прочитано ли открытое, неизвестно (`research map`).' if lang == 'ru'
                        else 'No series list: whether the open record is read is unknown (`research map`).'])
        if line.get('next'):
            out.extend(['', f"**{write_next}** · {line['next']}"])
        elif next_play:
            out.extend(['', f"**{write_next}** · {next_play['next']}"])
        if line.get('meanwhile'):
            out.extend(['', f"**{words['plan']['meanwhile']}** · {line['meanwhile']}"])
        if line.get('closed_road'):
            out.extend(['', f"**{words['plan']['closed_road']}** · {line['closed_road']}"])
        if any(play.get('place_form_gaps') for play in line['plays']):
            out.extend(['', 'Формы места у хранителя' if lang == 'ru' else 'Place forms by keeper'])
        for play in line['plays']:
            for gap in play.get('place_form_gaps', []):
                axes = [*gap['missing_languages'], *gap['missing_scripts']]
                marker = (' (язык форм не размечен)' if lang == 'ru' else ' (forms lack language tags)') if gap['has_untagged_forms'] else ''
                out.append(f"- {gap['place']} × {gap['country']} · {', '.join(axes)}{marker}")
        out.append('')
    return '\n'.join(out)
