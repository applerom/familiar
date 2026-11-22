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


def place_match(a, b):
    return bool(a and b) and (contains(a, b) or contains(b, a))


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


def line_windows(data, line, people):
    """Birth windows of the frontier person and of the people of the line's open questions."""
    from .coverage_context import planning_windows
    graph = data['tree'].graph['people']
    members = {line.chain[-1]}
    for question in line_questions(data, line, people):
        members.update(data['tree'].aliases.get(p, p) for p in question.get('people', []))
    windows = []
    for pid in sorted(members):
        if pid in data.get('living', ()) or pid not in graph:
            continue
        person = graph[pid]
        (lo, hi), _ = planning_windows(person | {'events': person.get('events', []) + data['planning_events'].get(pid, [])})
        if lo is not None:
            windows.append({'person': pid, 'born': [lo, hi]})
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


def nearness(year, kind, windows):
    return min((abs(year - (a + b) / 2) for a, b in spans(kind, windows)), default=0)


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
        value = 2 * in_window(year, kind, windows) + lead
        cost = {'online': 0, 'login': 1, 'unknown': 0, 'index': 0, 'named': 0, 'surname': 0,
                'blocked': 1, 'archive': 2, 'missing': 2}[state]
        if state in {'unknown', 'index', 'named', 'surname'}:
            cost = 0 if year in online and online[year][1] == 'open' else 1 if year in online else 2
        gap = {'online': 3, 'login': 3, 'archive': 3, 'missing': 3, 'blocked': 3, 'unknown': 2, 'index': 2,
               'named': 2, 'surname': 1}[state]
        cells.append({'series': series['id'], 'year': year, 'state': state, 'value': value, 'cost': cost, 'gap': gap,
                      'near': nearness(year, kind, windows),
                      'where': online[year][0] if year in online else series.get('holder')})
    return cells


def ranked(cells, limit=8):
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
                           'cost': cell['cost'], 'gap': cell['gap'], 'where': cell['where'], 'near': cell['near'],
                           'years': [cell['year'], cell['year']]})
    flat = [run for bucket in groups.values() for run in bucket]
    flat.sort(key=lambda r: (-r['value'], r['cost'], -r['gap'], r['near'], -(r['years'][1] - r['years'][0]), r['years'][0]))
    return flat[:limit] if limit else flat


def name_bases(data, line, observations, people_places):
    """Catalogue name bases that fit the line's places and period, opened or not, with forms and rows."""
    from .coverage import applicability
    from .research_plan import recorded_places
    from .search_plays import query_places
    from .search_variants import _expand, norm
    catalogue = data['resolver'].catalog.sources
    graph = data['tree'].graph['people']
    instance = data['instance']
    dead = [pid for pid in line.chain if pid not in data.get('living', ()) and recorded_places(graph[pid])]
    known = list(dict.fromkeys(_expand(instance, line.surname, 'surname'))) if line.surname else []
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
        fits = any(not applicability(data, pid, sid, data['contexts'].get(pid)) for pid in dead)
        opened = rows.get(sid)
        if not fits and not opened:
            continue
        if source.get('kind') != 'index' and not opened:
            continue
        read_forms = {norm(f) for f in (opened or {}).get('forms', ())}
        item = {'source': sid, 'title': source.get('title') or sid, 'fits': fits, 'access': source.get('access'),
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
    out.sort(key=lambda b: (b['fits'] is False, b['opened'], -b.get('rows', 0), b['title']))
    return out, len(dead)


def map_line(data, line, series_rows):
    from .research_plan import line_observations, recorded_places, variants_for_place
    from .coverage import line_members
    from .search_ledger import row_digest
    members = line_members(data, line.chain)
    graph = data['tree'].graph['people']
    places = list(dict.fromkeys(p for pid in line.chain for p in recorded_places(graph[pid])))
    entries = data['place_entries']
    names = {form for entry in entries for form in entry['names']}
    leading = leading_places(data, line, members)
    known_places = places + leading
    for entry in variants_for_place(known_places, entries):
        known_places.extend(f['text'] for f in entry['forms'])
    groups, unplayed, _ = line_observations(data, line, members, names, set())
    observations = [obs for rows in groups.values() for obs in rows]
    unplayed = set(unplayed)
    observations += [obs for obs in data['observations']
                     if (obs['row'].get('id_as_written') or obs['row'].get('id') or row_digest(obs['row'])) in unplayed]
    # Rows that name a series belong to the line of that series, whatever their people say.
    mine = [s for s in series_rows or [] if series_for_line(s, line, data, known_places)]
    ids = {s['id'] for s in mine}
    seen = {id(obs['row']) for obs in observations}
    observations += [obs for obs in data['observations'] if id(obs['row']) not in seen
                     and any(r[0] in ids for r in row_readings(obs['row']))]
    windows = line_windows(data, line, members)
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
                            'window': sorted(y for y in grid if in_window(y, kind, windows)),
                            'read_by': {str(y): rows for y, rows in basis.items()}, 'note': series.get('note')})
        cells += empty_cells(series, grid, online, windows, leading)
    bases, fit_people = name_bases(data, line, observations, places)
    window_open = [c for c in cells if c['value'] >= 2 and c['cost'] == 0 and c['state'] in {'online', 'unknown', 'index', 'named'}]
    return {'surname': line.surname, 'start': line.chain[0], 'frontier': line.chain[-1], 'windows': windows,
            'leading_places': leading, 'series': view_series, 'bases': bases, 'fit_people': fit_people,
            'open_online_in_window': len(window_open), 'next': ranked(cells),
            'totals': {state: sum(s['counts'].get(state, 0) for s in view_series)
                       for state in (*RANK, *EMPTY_STATES)}}


def prepare(instance, data=None):
    from .coverage import collect
    from .research_plan import place_entries
    from .search_plays import links_to_living
    if data is None:
        data = collect(instance, for_plan=True)
        data['living'], data['linked'] = links_to_living(data['tree'].graph)
    data['instance'] = instance
    data.setdefault('place_entries', place_entries(instance))
    return data


@boundary('diagnostic')
def search_map(instance, *, line=None):
    view = build(instance, line=line)
    return view, markdown_map(view, 'ru' if instance.source_language == 'ru' else 'en')


def build(instance, *, line=None):
    """The map view itself; the desk page and the plan read it inside their own gate."""
    from .coverage import selected_lines
    path, series_rows, problems = read_series(instance)
    data = prepare(instance)
    lines = [map_line(data, row, series_rows) for row in selected_lines(data, line)]
    view = {'schema': 1, 'series_file': path.relative_to(instance.root).as_posix() if path.is_relative_to(instance.root) else str(path),
            'series_list': series_rows is not None, 'problems': [{'series': w, 'message': m} for w, m in problems],
            'lines': lines}
    return view


WORDS = {
    'en': {'title': 'Search map', 'no_list': 'No series list yet ({file}): record series are unknown. Write one with `research form series`.',
           'series': 'Record series', 'bases': 'Name bases', 'next': 'Where to read next', 'none': 'nothing',
           'states': {'full': 'read in full', 'surname': 'surname column', 'named': 'named entries', 'index': 'index only',
                      'unknown': 'depth unknown', 'online': 'online, unread', 'login': 'online with login, unread',
                      'archive': 'archive only', 'missing': 'missing from the copy', 'blocked': 'did not open'},
           'window': 'window', 'opened': 'opened', 'never': 'fits, never opened', 'rows': 'returned {hits} · read {read}',
           'forms': 'forms', 'missing_forms': 'not read', 'open_online': 'Open online years in the window, unread: {n}',
           'fit_unknown': 'Which bases fit is unknown: no person of the line has a recorded place.',
           'cost': {0: 'online now', 1: 'needs the host login', 2: 'needs a letter to the archive'}},
    'ru': {'title': 'Карта поиска', 'no_list': 'Списка рядов книг ещё нет ({file}): что существует — неизвестно. Форма: `research form series`.',
           'series': 'Ряды книг', 'bases': 'Базы имён', 'next': 'Что читать дальше', 'none': 'ничего',
           'states': {'full': 'целиком', 'surname': 'графа фамилий', 'named': 'по именам', 'index': 'только индекс',
                      'unknown': 'глубина неизвестна', 'online': 'онлайн, не читано', 'login': 'онлайн со входом, не читано',
                      'archive': 'только в архиве', 'missing': 'нет в копии', 'blocked': 'не открылось'},
           'window': 'окно', 'opened': 'открыта', 'never': 'подходит, не открывали', 'rows': 'выдано {hits} · прочитано {read}',
           'forms': 'формы', 'missing_forms': 'не читали', 'open_online': 'Открытых онлайн-лет в окне не прочитано: {n}',
           'fit_unknown': 'Какие базы подходят, неизвестно: ни у кого в линии не записано место.',
           'cost': {0: 'онлайн сейчас', 1: 'нужен вход хозяина', 2: 'нужно письмо в архив'}},
}


def cell_words(run, series, w):
    title = series.get('title') or f"{series['kind']} · {series['place']}"
    return f"{title} {run_label(run['years'])}: {w['states'][run['state']]} · {w['cost'][run['cost']]}" + (
        f" ({run['where']})" if run.get('where') else '')


def strip_text(grid):
    marks = {'full': '█', 'surname': '▓', 'named': '▒', 'index': '░', 'unknown': '?', 'online': '·', 'login': ':',
             'archive': 'a', 'missing': 'x', 'blocked': '!'}
    out = []
    for decade in sorted({int(y) // 10 * 10 for y in grid}):
        out.append(f'{decade} ' + ''.join(marks[grid[str(y)]] if str(y) in grid else ' ' for y in range(decade, decade + 10)))
    return out


def markdown_map(view, lang):
    w = WORDS[lang]
    out = [f"# {w['title']}", '']
    if not view['series_list']:
        out += [w['no_list'].format(file=view['series_file']), '']
    for problem in view['problems']:
        out.append(f"- {problem['series']}: {problem['message']}")
    for line in view['lines']:
        out += [f"## {line['surname'] or line['start']}", '']
        if line['series']:
            out += [f"### {w['series']}", '']
            for series in line['series']:
                counts = ', '.join(f"{w['states'][k]} {v}" for k, v in series['counts'].items())
                out += [f"**{series.get('title') or series['kind'] + ' · ' + series['place']}** — {counts}", '```',
                        *strip_text(series['years']), '```']
            out += ['█ ' + w['states']['full'] + ' · ▓ ' + w['states']['surname'] + ' · ▒ ' + w['states']['named']
                    + ' · ░ ' + w['states']['index'] + ' · ? ' + w['states']['unknown'] + ' · · ' + w['states']['online']
                    + ' · : ' + w['states']['login'] + ' · a ' + w['states']['archive'] + ' · x ' + w['states']['missing']
                    + ' · ! ' + w['states']['blocked'], '']
        out += [f"### {w['bases']}", '']
        if not line['fit_people']:
            out.append(w['fit_unknown'])
        for base in line['bases']:
            if base['opened']:
                rows = w['rows'].format(read=base['read'], hits=base['hits'])
                missing = f" · {w['missing_forms']}: {', '.join(base['forms_missing'])}" if base['forms_missing'] else ''
                forms = f"{w['forms']} {len(base['forms_read'])}/{len(base['forms_known'])}" if base['forms_known'] else ''
                out.append(f"- {base['title']} · {w['opened']} · {rows} · {forms}{missing}")
            else:
                out.append(f"- {base['title']} · {w['never']}")
        if not line['bases']:
            out.append(f"- {w['none']}")
        out += ['', f"### {w['next']}", '']
        by_id = {s['id']: s for s in line['series']}
        out += [f"{n}. {cell_words(run, by_id[run['series']], w)}" for n, run in enumerate(line['next'], 1)] or [f"- {w['none']}"]
        if line['open_online_in_window']:
            out += ['', w['open_online'].format(n=line['open_online_in_window'])]
        out.append('')
    return '\n'.join(out)
