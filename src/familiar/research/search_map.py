# START_MODULE_CONTRACT: MOD-SEARCH-MAP
# PURPOSE: Show, per family line, how much of the open record was read: record series year by year, name bases by form and place, and the empty cells ranked as the plan.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - the map reads the series list and existing journal rows only; it writes nothing and adds no step to a collector [review: engine lead]
# - a year read while looking for one name, or only in another's index, never counts as a read year [review: engine lead]
# - where the data cannot tell, the map says unknown, never a guess [review: engine lead]
# CHANGES_WITH:
# - MOD-RESEARCH-PLAN (open record in the frontier window keeps a line from its ceiling)
# - MOD-SEARCH-LEDGER (coverage.series and coverage.depth on a row)
# - MOD-DESK-SEARCH-MAP (the host's page)
# :END_MODULE_CONTRACT
"""The search map: what of the open record has been read for a line, and what has not."""
import json
import re

from familiar.instance.gate import boundary

from .coverage_context import contains

# Best reading first. A surname column serves people born with the surname, not brides, mothers or godparents;
# a named reading and someone else's index answer only the question they were made for.
DEPTHS = ('full', 'surname', 'named', 'index')
RANK = {'full': 5, 'surname': 4, 'named': 3, 'index': 2, 'unknown': 1}
READ_STATES = set(RANK)
EMPTY_STATES = ('online', 'login', 'archive', 'missing', 'blocked')
KINDS = (('birth', r'bapt|birth|christ|рожд|крещ|chrzt|urodz|nasc'),
         ('marriage', r'marri|banns|wedd|брак|венч|оглаш|ślub|slub|małż|malz|casam'),
         ('death', r'death|burial|buri|смерт|погреб|умер|zgon|pogrz|óbit|obit'))
LOGIN = {'host-login', 'login', 'paid', 'request'}
# What a person's own records say of their community: a faith, a rite, a parish or a baptism. A catalogue base
# that declares `communities` holds only those; it fits a line whose people are recorded in one of them.
COMMUNITIES = {
    'jewish': r'jew|jüd|juif|евре|иуде|синагог|кагал|kahal|kahał|żyd|zyd|izraelit|mojżesz|mosaic|старозакон',
    'christian': r'cathol|католи|костел|костёл|kości|kosci|rzymsk|orthodox|правосл|церк|cerk|prawosł|prawosl|'
                 r'uniat|униат|грекокат|greckokat|lutheran|лютер|ewangel|евангел|protestant|parafi|parish|'
                 r'приход|chrzest|chrzt|chrzcz|baptis|крещ|крест',
}


def years_of(value):
    """Years written as 1870, "1870-1879", "1870–1872, 1875", [1870, 1879] (a range) or a list of these."""
    if value is None or isinstance(value, bool):
        return set()
    if isinstance(value, int):
        return {value} if 1000 <= value <= 2100 else set()
    if isinstance(value, list):
        if len(value) == 2 and all(type(v) is int for v in value) and value[0] < value[1]:
            return set(range(value[0], value[1] + 1)) if value[1] - value[0] <= 400 else set()
        return set().union(*(years_of(v) for v in value)) if value else set()
    found = set()
    for first, last in re.findall(r'([12]\d{3})(?:\s*[-–—]\s*([12]\d{3}))?', str(value)):
        a, b = int(first), int(last or first)
        if a <= b <= a + 400:
            found.update(range(a, b + 1))
    return found


def runs(years):
    """Consecutive years as [first, last] pairs."""
    out = []
    for year in sorted(years):
        if out and year == out[-1][1] + 1:
            out[-1][1] = year
        else:
            out.append([year, year])
    return out


def run_label(pair):
    return str(pair[0]) if pair[0] == pair[1] else f'{pair[0]}–{pair[1]}'


def kind_class(kind):
    word = str(kind or '').casefold()
    return next((name for name, pattern in KINDS if re.search(pattern, word)), 'life')


def validate(data):
    """Problems of a series list, as (series id or index, message); an empty list is a valid file."""
    problems = []
    if not isinstance(data, dict) or not isinstance(data.get('series'), list):
        return [('series', 'expected {"series": [ ... ]}; see research form series')]
    seen = set()
    for n, row in enumerate(data['series']):
        where = row.get('id') if isinstance(row, dict) and isinstance(row.get('id'), str) else f'#{n}'
        if not isinstance(row, dict):
            problems.append((where, 'a series is an object'))
            continue
        if not isinstance(row.get('id'), str) or not re.fullmatch(r'[a-z0-9][a-z0-9._-]*', row['id']):
            problems.append((where, 'id: lower-case slug, e.g. ponta-do-moinho-baptisms'))
        elif row['id'] in seen:
            problems.append((where, 'id repeats'))
        seen.add(row.get('id'))
        for key in ('kind', 'place'):
            if not isinstance(row.get(key), str) or not row[key].strip():
                problems.append((where, f'{key}: nonempty text'))
        if not years_of(row.get('years')):
            problems.append((where, 'years: which years exist, e.g. "1850-1900" or [[1850, 1876], 1880]'))
        if 'missing' in row and not years_of(row['missing']) and row['missing'] not in ([], '', None):
            problems.append((where, 'missing: years absent from the copy'))
        if not isinstance(row.get('lines', []), list) or not all(isinstance(v, str) for v in row.get('lines', [])):
            problems.append((where, 'lines: list of line surnames'))
        online = row.get('online', [])
        if not isinstance(online, list) or not all(isinstance(v, dict) and isinstance(v.get('source'), str)
                                                    for v in online):
            problems.append((where, 'online: list of {source, years?, access?}'))
        else:
            for item in online:
                if item.get('access') not in (None, 'open', 'login', 'paid', 'request', 'host-login'):
                    problems.append((where, f"online {item['source']}: access is open, login, paid or request"))
    return problems


def read_series(instance):
    path = instance.path('series')
    if not path.is_file():
        return path, None, []
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError, OSError) as exc:
        return path, None, [('series', f'unreadable: {exc}')]
    problems = validate(data)
    rows = [row for row in data.get('series', []) if isinstance(row, dict) and isinstance(row.get('id'), str)
            and years_of(row.get('years')) and isinstance(row.get('place'), str)] if isinstance(data, dict) else []
    return path, rows, problems


def row_readings(row):
    """(series id, years, depth, entries) a journal row names; depth is None when the row does not say."""
    coverage = row.get('coverage') if isinstance(row.get('coverage'), dict) else {}
    named = coverage.get('series')
    items = named if isinstance(named, list) else [named] if named else []
    out = []
    for item in items:
        if isinstance(item, str):
            item = {'id': item}
        if not isinstance(item, dict) or not isinstance(sid := item.get('id') or item.get('series'), str):
            continue
        depth = item.get('depth', coverage.get('depth'))
        out.append((sid, years_of(item.get('years', coverage.get('years'))),
                    depth if depth in DEPTHS else None, item.get('entries', coverage.get('entries'))))
    return out


def series_sources(series, resolver):
    """The ledger ids a row of this series' online copies carries: catalogue ids, or a site as the ledger groups it."""
    from familiar.desk.search_volume import domain, name_key
    ids = set()
    for item in series.get('online', []):
        sid = item['source']
        ids |= {sid, '~' + (domain(sid) or name_key(sid))[:60]}
        if resolver is not None and (resolved := resolver.row_source({'source': sid})):
            ids.add(resolved)
    return ids


def place_names(value):
    """The names a place is written with: "Parish (village, village)" gives each of them."""
    return [n for n in (re.sub(r'\s+', ' ', part).strip().casefold().replace('ё', 'е')
                        for part in re.split(r'[,;()/]+', str(value or ''))) if n]


def place_match(a, b):
    """Two places are one when one of their names is the same word, allowing a case ending; never a substring."""
    for x in place_names(a):
        for y in place_names(b):
            short, long = sorted((x, y), key=len)
            if x == y or (len(short) >= 5 and long.startswith(short) and len(long) - len(short) <= 2
                          and ' ' not in long[len(short):]):
                return True
    return False


def year_grid(series, observations, resolver):
    """Year → best reading, with the rows that support it."""
    exists = years_of(series['years'])
    missing = years_of(series.get('missing')) & exists
    online = {}
    for item in series.get('online', []):
        years = years_of(item.get('years')) & exists if item.get('years') else set(exists)
        access = item.get('access')
        if access is None and resolver is not None:
            access = resolver.catalog.sources.get(resolver.row_source({'source': item['source']}) or '', {}).get('access')
        for year in years - missing:
            if online.get(year, ('', 'login'))[1] != 'open':
                online[year] = (item['source'], 'login' if access in LOGIN else 'open')
    sources = series_sources(series, resolver)
    best, basis, blocked = {}, {}, set()
    for obs in observations:
        row = obs['row']
        named = [r for r in row_readings(row) if r[0] == series['id']]
        if not named and obs['source'] in sources and not row_readings(row):
            # A row that does not name its series still touched this place in this source: depth unknown.
            query = row.get('query') if isinstance(row.get('query'), dict) else {}
            places = [v for k, v in query.items() if isinstance(v, str) and re.search(r'place|parish|village|town|loc', k)]
            if any(place_match(p, series['place']) for p in places):
                named = [(series['id'], years_of((row.get('coverage') or {}).get('years')), None, None)]
        for _, years, depth, entries in named:
            years = years & exists
            if obs['kind'] == 'gap':
                blocked |= years
                continue
            state = depth or 'unknown'
            for year in years:
                if RANK[state] > RANK.get(best.get(year), 0):
                    best[year] = state
                basis.setdefault(year, []).append({'id': row.get('id'), 'depth': state, 'entries': entries,
                                                   'at': str(row.get('at') or '')[:10]})
    grid = {}
    for year in sorted(exists):
        if year in best:
            grid[year] = best[year]
        elif year in blocked:
            grid[year] = 'blocked'
        elif year in missing:
            grid[year] = 'missing'
        elif year in online:
            grid[year] = online[year][1] if online[year][1] == 'login' else 'online'
        else:
            grid[year] = 'archive'
    return grid, basis, online


def line_questions(data, line, people):
    """Open questions of the line: named for it, or about one of its people."""
    from .coverage import OPEN_EXCLUSIONS
    from .research_plan import matches_line
    aliases = data['tree'].aliases
    return [q for q in data['versions'].values() if q.get('status', q.get('state')) not in OPEN_EXCLUSIONS and (
        matches_line(line, people, data, q) or any(aliases.get(p, p) in people for p in q.get('people', [])))]


# How much a year can move the line's open question: the frontier person's own years first, then the people
# of the open versions about him, then anyone else an open question of the line names.
FRONTIER, ABOUT_FRONTIER, OTHER_QUESTION = 1.0, 0.6, 0.3


def line_windows(data, line, people):
    """Birth windows, weighted: the frontier person, the people of open questions about him, other question people."""
    from .coverage_context import planning_windows
    graph = data['tree'].graph['people']
    aliases = data['tree'].aliases
    frontier = line.chain[-1]
    weights = {frontier: FRONTIER}
    for question in line_questions(data, line, people):
        named = [aliases.get(p, p) for p in question.get('people', [])]
        weight = ABOUT_FRONTIER if frontier in named else OTHER_QUESTION
        for pid in named:
            weights[pid] = max(weights.get(pid, 0), weight)
    windows = []
    for pid, weight in sorted(weights.items()):
        if pid in data.get('living', ()) or pid not in graph:
            continue
        person = graph[pid]
        (lo, hi), _ = planning_windows(person | {'events': person.get('events', []) + data['planning_events'].get(pid, [])})
        if lo is not None:
            windows.append({'person': pid, 'born': [lo, hi], 'weight': weight})
    return windows


def spans(kind, windows):
    """Years in which a record of this kind can name the window's people: birth, marriage, death or life."""
    out = []
    for window in windows:
        lo, hi = window['born']
        out.append({'birth': (lo - 2, hi + 2), 'marriage': (lo + 15, hi + 45), 'death': (lo, hi + 90)}.get(kind, (lo, hi + 60)))
    return out


def in_window(year, kind, windows):
    return any(a <= year <= b for a, b in spans(kind, windows))


def window_weight(year, kind, windows):
    """The weight of the most telling window this year of this kind of record falls in; 0 outside all."""
    return max((w.get('weight', FRONTIER) for w, (a, b) in zip(windows, spans(kind, windows)) if a <= year <= b), default=0)


CORE = 12  # years either side of the most telling birth: his own baptism, his parents' marriage, his siblings


def nearness(year, windows):
    """Distance to the middle of the most telling person's birth window, whatever the kind of record."""
    top = max((w.get('weight', FRONTIER) for w in windows), default=0)
    return min((abs(year - sum(w['born']) / 2) for w in windows if w.get('weight', FRONTIER) == top), default=0)


def leading_places(data, line, people):
    from .coverage import CLOSED_OPTIONS
    places = []
    for question in line_questions(data, line, people):
        options = [o for o in question.get('versions') or [] if isinstance(o, dict)
                   and o.get('status', o.get('state')) not in CLOSED_OPTIONS | {'disproved'}]
        chosen = (question.get('story_choice') or {}).get('version')
        lead = next((o for o in options if o.get('id') == chosen), None) or max(
            options, key=lambda o: o.get('weight') if type(o.get('weight')) in (int, float) else 0, default=None)
        if lead and isinstance(lead.get('place'), str):
            places.append(lead['place'])
    return places


def series_for_line(series, line, data, places):
    from .coverage import surname_keys
    if series.get('lines'):
        return any(surname_keys(name, data['language']) & line.forms for name in series['lines'])
    return any(place_match(series['place'], place) for place in places)


def empty_cells(series, grid, online, windows, leading):
    kind = kind_class(series['kind'])
    lead = any(place_match(series['place'], place) for place in leading)
    cells = []
    for year, state in grid.items():
        if state in {'full', 'surname'} and not (state == 'surname' and kind == 'marriage'):
            continue
        weight = window_weight(year, kind, windows)
        near = nearness(year, windows)
        value = round(weight * (1.5 if weight and near <= CORE else 1) + .25 * lead, 2)
        cost = {'online': 0, 'login': 1, 'unknown': 0, 'index': 0, 'named': 0, 'surname': 0,
                'blocked': 1, 'archive': 2, 'missing': 2}[state]
        if state in {'unknown', 'index', 'named', 'surname'}:
            cost = 0 if year in online and online[year][1] == 'open' else 1 if year in online else 2
        gap = {'online': 3, 'login': 3, 'archive': 3, 'missing': 3, 'blocked': 3, 'unknown': 2, 'index': 2,
               'named': 2, 'surname': 1}[state]
        cells.append({'series': series['id'], 'year': year, 'state': state, 'value': value, 'cost': cost, 'gap': gap,
                      'in_window': weight >= ABOUT_FRONTIER,
                      'near': near,
                      'where': online[year][0] if year in online else series.get('holder')})
    return cells


def ranked(cells, limit=10):
    """Runs of neighbouring empty years of one series and state, by value, then cost, then how unread."""
    groups = {}
    for cell in sorted(cells, key=lambda c: (c['series'], c['state'], c['value'], c['cost'], c['year'])):
        key = (cell['series'], cell['state'], cell['value'], cell['cost'])
        bucket = groups.setdefault(key, [])
        if bucket and cell['year'] == bucket[-1]['years'][1] + 1:
            bucket[-1]['years'][1] = cell['year']
            bucket[-1]['near'] = min(bucket[-1]['near'], cell['near'])
        else:
            bucket.append({'series': cell['series'], 'state': cell['state'], 'value': cell['value'],
                           'in_window': cell['in_window'],
                           'cost': cell['cost'], 'gap': cell['gap'], 'where': cell['where'], 'near': cell['near'],
                           'years': [cell['year'], cell['year']]})
    flat = [run for bucket in groups.values() for run in bucket]
    flat.sort(key=lambda r: (-r['value'], r['cost'], r['near'], -r['gap'], -(r['years'][1] - r['years'][0]), r['years'][0]))
    return flat[:limit] if limit else flat


def line_communities(data, members):
    """Communities the line's people are recorded in, from their own records' words; empty when none says."""
    from .coverage_context import person_text
    graph = data['tree'].graph['people']
    found = set()
    for pid in members:
        person = graph.get(pid)
        if not person:
            continue
        words = ' '.join(str(person.get(k) or '') for k in ('religion', 'faith', 'rite', 'confession'))
        raw = (person_text(person | {'events': person.get('events', []) + data['planning_events'].get(pid, [])})
               + ' ' + words).casefold()
        found |= {name for name, pattern in COMMUNITIES.items() if re.search(pattern, raw)}
    return found


def name_bases(data, line, observations, people_places, communities=frozenset()):
    """Catalogue name bases that fit the line's places, period and community, opened or not, with forms and rows.

    A base that holds one community's records fits only a line recorded in it; where nobody's community is
    recorded, its fit is unknown (None), never a hole."""
    from .coverage import applicability
    from .research_plan import recorded_places
    from .search_plays import query_places
    from .search_variants import _expand, norm
    catalogue = data['resolver'].catalog.sources
    graph = data['tree'].graph['people']
    instance = data['instance']
    dead = [pid for pid in line.chain if pid not in data.get('living', ()) and recorded_places(graph[pid])]
    known = []
    # The line's name may be a plural ("the Smiths"); the forms come from the surname its people were born with.
    for name in [line.surname, *(n for pid in line.chain for n in data['tree'].people[pid]['surnames'])] if line.surname else []:
        if len(forms := list(dict.fromkeys(_expand(instance, name, 'surname')))) > len(known):
            known = forms
        if len(known) > 1:
            break
    rows = {}
    for obs in observations:
        sid = obs['source']
        if not sid or row_readings(obs['row']):
            continue  # a row that reads a record series is a reading of frames, not a name-base search
        entry = rows.setdefault(sid, {'rows': 0, 'read': 0, 'hits': 0, 'unknown_counts': 0, 'gaps': 0,
                                      'forms': set(), 'places': set(), 'last': ''})
        row = obs['row']
        coverage = row.get('coverage') if isinstance(row.get('coverage'), dict) else {}
        entry['rows'] += 1
        entry['gaps'] += obs['kind'] == 'gap'
        read, hits = coverage.get('read'), row.get('hits')
        if type(read) in (int, float) and type(hits) in (int, float):
            entry['read'] += read
            entry['hits'] += hits
        else:
            entry['unknown_counts'] += obs['kind'] != 'gap'
        forms = coverage.get('forms')
        entry['forms'].update(f.strip() for f in (forms if isinstance(forms, list) else [forms]) if isinstance(f, str) and f.strip())
        entry['places'].update(query_places(row))
        entry['last'] = max(entry['last'], str(row.get('at') or '')[:10])
    out = []
    for sid, source in catalogue.items():
        if source.get('kind') in {'archive', 'finding-aid', 'registry'}:
            continue
        fits = any(not applicability(data, pid, sid, data['contexts'].get(pid)) for pid in dead) if dead else None
        held = set(source.get('communities') or ())
        doubt = bool(dead and fits is not False and held and not communities)
        if held and fits is not False:
            fits = None if doubt else fits if held & communities else False
        opened = rows.get(sid)
        if not fits and not opened and not doubt:
            continue
        if source.get('kind') != 'index' and not opened:
            continue
        read_forms = {norm(f) for f in (opened or {}).get('forms', ())}
        item = {'source': sid, 'title': source.get('title') or sid, 'fits': fits, 'access': source.get('access'),
                'catalogued': True, 'communities': sorted(held), 'community_unknown': doubt,
                'opened': bool(opened), 'forms_known': known,
                'forms_missing': [f for f in known if norm(f) not in read_forms]}
        if opened:
            item.update({k: opened[k] for k in ('rows', 'read', 'hits', 'unknown_counts', 'gaps', 'last')},
                        forms_read=[f for f in known if norm(f) in read_forms], words_read=len(opened['forms']),
                        places=sorted(opened['places']),
                        places_missing=[p for p in people_places if not any(place_match(p, q) for q in opened['places'])])
        out.append(item)
    for sid, opened in rows.items():
        if sid in catalogue:
            continue
        # A site outside the catalogue: opened, its fit is unknown.
        read_forms = {norm(f) for f in opened['forms']}
        out.append({'source': sid, 'title': data['titles'].get(sid, sid.lstrip('~')), 'fits': None, 'access': None,
                    'opened': True, 'forms_known': known, 'forms_missing': [f for f in known if norm(f) not in read_forms],
                    **{k: opened[k] for k in ('rows', 'read', 'hits', 'unknown_counts', 'gaps', 'last')},
                    'forms_read': [f for f in known if norm(f) in read_forms], 'words_read': len(opened['forms']),
                    'places': sorted(opened['places']),
                    'places_missing': [p for p in people_places if not any(place_match(p, q) for q in opened['places'])]})
    out.sort(key=lambda b: (b['fits'] is not True, b['opened'], -b.get('rows', 0), b['title']))
    return out, len(dead)


def map_line(data, group, series_rows):
    """One section for every chain of one surname: their people, searches and series together."""
    from .research_plan import line_observations, recorded_places, variants_for_place
    from .access_ledger import line_places
    from .coverage import line_members
    from .search_ledger import row_digest
    group = group if isinstance(group, list) else [group]  # the plan maps one chain
    line = group[0]
    if len(group) > 1:
        chain = list(dict.fromkeys(pid for one in group for pid in one.chain))
        line = line._replace(chain=chain, forms=set().union(*(one.forms for one in group)),
                             main_order=min(one.main_order for one in group),
                             secondary=all(one.secondary for one in group),
                             focus_order=min(one.focus_order for one in group))
    members = set().union(*(line_members(data, one.chain) for one in group))
    graph = data['tree'].graph['people']
    places = list(dict.fromkeys(p for pid in line.chain for p in recorded_places(graph[pid])))
    entries = data['place_entries']
    names = {form for entry in entries for form in entry['names']}
    leading = list(dict.fromkeys(p for one in group for p in leading_places(data, one, members)))
    known_places = places + leading
    for entry in variants_for_place(known_places, entries):
        known_places.extend(f['text'] for f in entry['forms'])
    observations, seen, unplayed = [], set(), set()
    for one in group:
        groups, unknown, _ = line_observations(data, one, members, names, set())
        unplayed.update(unknown)
        for obs in (obs for rows in groups.values() for obs in rows):
            if id(obs['row']) not in seen:
                seen.add(id(obs['row']))
                observations.append(obs)
    observations += [obs for obs in data['observations'] if id(obs['row']) not in seen
                     and (obs['row'].get('id_as_written') or obs['row'].get('id') or row_digest(obs['row'])) in unplayed]
    # Rows that name a series belong to the line of that series, whatever their people say.
    mine = [s for s in series_rows or [] if series_for_line(s, line, data, known_places)]
    ids = {s['id'] for s in mine}
    seen = {id(obs['row']) for obs in observations}
    observations += [obs for obs in data['observations'] if id(obs['row']) not in seen
                     and any(r[0] in ids for r in row_readings(obs['row']))]
    windows = {}
    for one in group:
        for window in line_windows(data, one, members):
            if window['weight'] > windows.get(window['person'], {}).get('weight', 0):
                windows[window['person']] = window
    windows = list(windows.values())
    view_series, cells = [], []
    for series in mine:
        grid, basis, online = year_grid(series, observations, data['resolver'])
        counts = {}
        for state in grid.values():
            counts[state] = counts.get(state, 0) + 1
        kind = kind_class(series['kind'])
        view_series.append({'id': series['id'], 'kind': series['kind'], 'place': series['place'],
                            'title': series.get('title'), 'holder': series.get('holder'),
                            'online': [item['source'] for item in series.get('online', [])],
                            'years': {str(y): s for y, s in grid.items()}, 'counts': counts,
                            'window': sorted(y for y in grid if window_weight(y, kind, windows) >= ABOUT_FRONTIER),
                            'read_by': {str(y): rows for y, rows in basis.items()}, 'note': series.get('note')})
        cells += empty_cells(series, grid, online, windows, leading)
    communities = line_communities(data, members)
    bases, fit_people = name_bases(data, line, observations, places, communities)
    # Online with the host's login is online: FamilySearch years count.
    window_open = [c for c in cells if c['in_window'] and c['cost'] <= 1
                   and c['state'] in {'online', 'login', 'unknown', 'index', 'named'}]
    questions = {q.get('id') or n for one in group for n, q in enumerate(line_questions(data, one, members))}
    return {'surname': line.surname, 'start': line.chain[0], 'frontier': group[0].chain[-1],
            'chains': len(group), 'main': not line.secondary, 'order': (line.focus_order, line.main_order),
            'questions': len(questions), 'last': max((str(o['row'].get('at') or '')[:10] for o in observations), default=''),
            'access': line_places(data, data['access'], line, members),
            'communities': sorted(communities), 'windows': windows,
            'leading_places': leading, 'series': view_series, 'bases': bases, 'fit_people': fit_people,
            'open_online_in_window': len(window_open), 'next': ranked(cells),
            'totals': {state: sum(s['counts'].get(state, 0) for s in view_series)
                       for state in (*RANK, *EMPTY_STATES)}}


def line_groups(lines):
    """Chains of one surname are one line of the family; a chain without a surname stays alone."""
    groups = {}
    for line in lines:
        groups.setdefault(line.surname.casefold() or id(line), []).append(line)
    return list(groups.values())


def working_first(lines):
    """The lines the family works on now open the map: its main lines, then open questions, then recent searches."""
    return sorted(lines, key=lambda l: (not l['main'], not l['questions'], l['order'],
                                        not l['last'], [-ord(c) for c in l['last']], not l['surname']))


def prepare(instance, data=None):
    from .coverage import collect
    from .research_plan import place_entries
    from .search_plays import links_to_living
    if data is None:
        data = collect(instance, for_plan=True)
        data['living'], data['linked'] = links_to_living(data['tree'].graph)
    data['instance'] = instance
    data.setdefault('place_entries', place_entries(instance))
    from .access_ledger import read
    data['access'] = read(instance)[1]
    return data


@boundary('diagnostic')
def search_map(instance, *, line=None):
    view = build(instance, line=line)
    from familiar.instance.subjects import protected_names
    return view, protected_names(instance).sub('…', markdown_map(view, 'ru' if instance.source_language == 'ru' else 'en'))


def build(instance, *, line=None):
    """The map view itself; the desk page and the plan read it inside their own gate."""
    from .coverage import selected_lines
    path, series_rows, problems = read_series(instance)
    data = prepare(instance)
    lines = working_first([map_line(data, group, series_rows) for group in line_groups(selected_lines(data, line))])
    view = {'schema': 1, 'series_file': path.relative_to(instance.root).as_posix() if path.is_relative_to(instance.root) else str(path),
            'series_list': series_rows is not None, 'access': data['access'], 'problems': [{'series': w, 'message': m} for w, m in problems],
            'lines': lines}
    return view


def base_groups(line):
    """The field of a line: bases that fit (holes first, then the least read); the rest sits behind a tap."""
    known = bool(line['fit_people'])
    field = [b for b in line['bases'] if b['fits'] is True or (not known and b.get('catalogued') and not b.get('communities'))]
    rest = [b for b in line['bases'] if b not in field]

    def share(b):
        return len(b.get('forms_read', [])) / len(b['forms_known']) if b['forms_known'] else 1
    field.sort(key=lambda b: (b['opened'], share(b) if b['opened'] else 0, -b.get('rows', 0), b['title']))
    return field, rest


def line_name(line, w):
    return line['surname'] or w['no_surname']


def line_counts(line):
    read = sum(line['totals'].get(s, 0) for s in ('full', 'surname'))
    years = sum(sum(s['counts'].values()) for s in line['series'])
    return {'opened': sum(b['opened'] for b in line['bases']), 'read': read, 'years': years}


def working(line):
    """A line the family works on now: a main line with a surname, or one with open questions."""
    return line['main'] and bool(line['surname'] or line['questions'])


WORDS = {
    'en': {'title': 'Search map', 'no_list': 'No series list yet ({file}): which books exist is unknown; list them with `research form series`.',
           'series': 'Record series', 'bases': 'Name bases', 'next': 'Where to read next', 'none': 'nothing',
           'states': {'full': 'read in full', 'surname': 'surname column', 'named': 'named entries', 'index': 'index only',
                      'unknown': 'depth unknown', 'online': 'online, unread', 'login': 'online with login, unread',
                      'archive': 'archive only', 'missing': 'missing from the copy', 'blocked': 'did not open'},
           'window': 'window', 'opened': 'opened', 'never': 'fits, never opened', 'rows': 'returned {hits} · read {read}',
           'forms': 'forms', 'missing_forms': 'not read', 'open_online': 'Open online years in the window, unread: {n}',
           'fit_unknown': 'Which bases fit is unknown: no person of the line has a recorded place.',
           'field': 'fit and opened {opened} of {fit}', 'holes': 'never opened', 'partial': 'not every form',
           'rest': 'also opened, outside the catalogue or not for this line: {n}',
           'community': 'only if the line was {c}: {names}', 'no_surname': 'Line without a surname',
           'others': 'Other lines', 'questions': 'open questions', 'last': 'last search',
           'one_row': 'bases opened {opened} · years read {read} of {years}',
           'cost': {0: 'online now', 1: 'needs the host login', 2: 'needs a letter to the archive'}},
    'ru': {'title': 'Карта поиска', 'no_list': 'Списка рядов книг ещё нет ({file}): что существует — неизвестно; составить: `research form series`.',
           'series': 'Ряды книг', 'bases': 'Базы имён', 'next': 'Что читать дальше', 'none': 'ничего',
           'states': {'full': 'целиком', 'surname': 'графа фамилий', 'named': 'по именам', 'index': 'только индекс',
                      'unknown': 'глубина неизвестна', 'online': 'онлайн, не читано', 'login': 'онлайн со входом, не читано',
                      'archive': 'только в архиве', 'missing': 'нет в копии', 'blocked': 'не открылось'},
           'window': 'окно', 'opened': 'открыта', 'never': 'подходит, не открывали', 'rows': 'выдано {hits} · прочитано {read}',
           'forms': 'формы', 'missing_forms': 'не читали', 'open_online': 'Открытых онлайн-лет в окне не прочитано: {n}',
           'fit_unknown': 'Какие базы подходят, неизвестно: ни у кого в линии не записано место.',
           'field': 'подходят и открыты {opened} из {fit}', 'holes': 'не открывали', 'partial': 'не все формы',
           'rest': 'ещё открывали, вне каталога или не для этой линии: {n}',
           'community': 'только если линия — {c}: {names}', 'no_surname': 'Линия без фамилии',
           'others': 'Другие линии', 'questions': 'открытых вопросов', 'last': 'последний поиск',
           'one_row': 'баз открыто {opened} · лет прочитано {read} из {years}',
           'cost': {0: 'онлайн сейчас', 1: 'нужен вход хозяина', 2: 'нужно письмо в архив'}},
}
COMMUNITY_WORDS = {'en': {'jewish': 'Jewish', 'christian': 'Christian'},
                   'ru': {'jewish': 'еврейская', 'christian': 'христианская'}}


def cell_words(run, series, w):
    title = series.get('title') or f"{series['kind']} · {series['place']}"
    return f"{title} {run_label(run['years'])}: {w['states'][run['state']]} · {w['cost'][run['cost']]}" + (
        f" ({run['where']})" if run.get('where') else '')


def strip_text(grid):
    """One row per series: the first decade, then ten marks a decade, decades apart."""
    marks = {'full': '█', 'surname': '▓', 'named': '▒', 'index': '░', 'unknown': '?', 'online': '·', 'login': ':',
             'archive': 'a', 'missing': 'x', 'blocked': '!'}
    decades = sorted({int(y) // 10 * 10 for y in grid})
    return f'{decades[0]} ' + ' '.join(''.join(marks[grid[str(y)]] if str(y) in grid else ' ' for y in range(d, d + 10))
                                      for d in range(decades[0], decades[-1] + 10, 10)) if decades else ''


def markdown_map(view, lang):
    w = WORDS[lang]
    out = [f"# {w['title']}", '']
    if not view['series_list']:
        out += [w['no_list'].format(file=view['series_file']), '']
    for problem in view['problems']:
        out.append(f"- {problem['series']}: {problem['message']}")
    shown = [line for line in view['lines'] if line['series'] or line['bases']]
    main = [line for line in shown if working(line)] or shown[:1]
    for line in main:
        facts = [f"{w['questions']} {line['questions']}" if line['questions'] else '',
                 f"{w['last']} {line['last']}" if line['last'] else '']
        out += [f"## {line_name(line, w)}" + ''.join(f' · {f}' for f in facts if f), '']
        if line['series']:
            out += [f"### {w['series']}", '', '```']
            for series in line['series']:
                read = sum(series['counts'].get(k, 0) for k in ('full', 'surname'))
                out += [f"{series.get('title') or series['kind'] + ' · ' + series['place']} · {read}/{sum(series['counts'].values())}",
                        strip_text(series['years'])]
            out.append('```')
            out += [' · '.join(f'{m} {w["states"][k]}' for k, m in (
                ('full', '█'), ('surname', '▓'), ('named', '▒'), ('index', '░'), ('unknown', '?'), ('online', '·'),
                ('login', ':'), ('archive', 'a'), ('missing', 'x'), ('blocked', '!'))), '']
        field, rest = base_groups(line)
        if not line['fit_people']:
            out.append(w['fit_unknown'])
        out.append(f"{w['bases']}: {w['field'].format(opened=sum(b['opened'] for b in field), fit=len(field))}")
        if holes := [b['title'] for b in field if not b['opened']]:
            out.append(f"- {w['holes']}: {', '.join(holes)}")
        if partial := [f"{b['title']} {len(b.get('forms_read', []))}/{len(b['forms_known'])}" for b in field
                       if b['opened'] and b['forms_missing']]:
            out.append(f"- {w['partial']}: {', '.join(partial)}")
        doubt = {}
        for b in rest:
            if b.get('community_unknown') and not b['opened']:
                doubt.setdefault(tuple(b['communities']), []).append(b['title'])
        for held, names in doubt.items():
            c = ', '.join(COMMUNITY_WORDS[lang].get(x, x) for x in held)
            out.append(f"- {w['community'].format(c=c, names=', '.join(names))}")
        if opened_rest := [b for b in rest if b['opened']]:
            out.append(f"- {w['rest'].format(n=len(opened_rest))}")
        by_id = {s['id']: s for s in line['series']}
        if line['next']:
            out += ['', f"### {w['next']}", '']
            out += [f"{n}. {cell_words(run, by_id[run['series']], w)}" for n, run in enumerate(line['next'], 1)]
        if line['open_online_in_window']:
            out += ['', w['open_online'].format(n=line['open_online_in_window'])]
        out.append('')
    if others := [line for line in shown if line not in main]:
        out += [f"## {w['others']}", '']
        out += [f"- {line_name(line, w)}: {w['one_row'].format(**line_counts(line))}" for line in others]
        out.append('')
    return '\n'.join(out)
