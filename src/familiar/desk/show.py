# START_MODULE_CONTRACT: MOD-DESK-SHOW
# PURPOSE: Derive a dateless investigation from recorded alternatives, search coverage and accepted tree changes.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - historical research labels use the shared effective life status after merges [review: engine lead]
# - commit messages, search queries, paths and unaccepted person details never enter the show [test: tests/gate/test_desk_guarantees.py::test_desk_requires_host_decision]
# - output contains ordered event pages and numeric weight history, never research timestamps [review: engine lead]
# - absent reasons, source types and readings are never invented [review: engine lead]
# - unfinished collector records and journal lines do not block or invalidate the derived investigation summary [review: engine lead]
# - open, dropped, confirmed awaiting tree and included outcomes are distinct in the work-volume summary [review: browser walk]
# - letters moved from owner correspondence do not become shared prompts [review: engine lead]
# CHANGES_WITH:
# - MOD-DESK-BUILD (selected inputs and history binding)
# - MOD-DESK-SHOW-CLIENT (show.json contract)
# - MOD-DESK-TREE-ADD (pending and reviewed feedback)
# :END_MODULE_CONTRACT
import hashlib
import html
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

FIRM = {'firm', 'accepted', 'established'}
DROPPED = {'rejected', 'refuted', 'discarded', 'dropped', 'ruled-out'}
PAGE_SIZE = 24


def public_line(value, fallback=''):
    """Literal short editorial fields only; dated or internal lines stay private."""
    if not isinstance(value, str):
        return fallback
    if (len(value) > 240 or re.search(
            r'[/\\`]|\b\w+\.(?:jsonl?|md|csv|py)\b|https?:|[A-Z]:|'
            r'\b\d{4}[-.]\d{2}[-.]\d{2}|\b\d{1,2}:\d{2}', value)):
        return fallback
    return value.strip() or fallback


def weight(value):
    if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value):
        return max(0, min(1, value))
    return 0


def project(active, graph, w):
    """Read once; dates order events internally and are discarded before delivery."""
    inputs, listings = {}, {}
    collector_roots = {active.path(k) for k in ('records', 'searches')}
    def read(path):
        raw = path.read_bytes() if path.is_file() else None
        inputs[path] = raw
        return raw
    def select(root, pattern):
        from .model import listing
        paths, listings[root, pattern] = listing(root, pattern)
        return paths
    def rows(root, pattern='*.json'):
        working = root in collector_roots
        for path in sorted(root.glob(pattern)) if working else select(root, pattern):
            try:
                raw = path.read_bytes() if working else read(path)
            except OSError:
                if not working:
                    raise
                continue
            for line in raw.splitlines() if path.suffix == '.jsonl' else [raw]:
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except ValueError:
                    if not working:
                        raise
                    continue
                if (not working or isinstance(value, dict)
                        or (root == active.path('searches') and isinstance(value, list))):
                    yield path, value
    def git(*args, payload=None):
        try:
            result = subprocess.run(['git', '-C', str(active.root), *args], input=payload,
                                    capture_output=True, timeout=30, check=False)
            return result.stdout if result.returncode == 0 else b''
        except (OSError, subprocess.TimeoutExpired):
            return b''
    def opaque(value):
        return hashlib.sha256(str(value).encode()).hexdigest()[:16]
    def relative(path):
        return path.relative_to(active.root).as_posix()
    people = graph.get('people', {})
    from familiar.checks.engine import _known_people, life_status
    known = _known_people(active)
    events, versions, lanes, asks, pending = [], [], [], [], []
    lanes.append({'id': 'tree', 'title': w['tree'], 'kind': 'tree'})
    lane_ids, version_paths = {}, {}
    def event(at, lane, kind, line, **extra):
        events.append({'_order': (str(at), len(events)), 'lane': lane, 'kind': kind,
                       'line': line, **extra})
    for index, (path, row) in enumerate(rows(active.path('versions')), 1):
        subjects = row.get('people', [])
        if not subjects or not set(subjects) <= set(people):
            continue
        identity = row.get('id', path.stem)
        lane = opaque(identity)
        lane_ids[identity] = lane
        historical = all(life_status(known.get(p, {'id': p}), {}) == 'dead' for p in subjects)
        title = public_line(row.get('headline') or (row.get('title') if historical else ''),
                            w['branch'].format(n=index))
        # The real question ID is needed by the researcher's feedback inbox, but
        # only safe opaque/token IDs may cross this boundary, never file paths.
        question = identity if re.fullmatch(r'[\w.-]{1,160}', str(identity)) else lane
        lanes.append({'id': lane, 'question': question, 'title': title, 'kind': 'question',
                      'open': row.get('status', row.get('state')) not in {'closed', 'resolved'}})
        version_paths[path] = (lane, historical, row)
    repository = git('rev-parse', '--show-toplevel').decode().strip()
    owns_history = bool(repository and Path(repository).resolve() == active.root)
    git_dir = git('rev-parse', '--absolute-git-dir').decode().strip() if owns_history else ''
    if git_dir:
        head = Path(git_dir) / 'HEAD'
        raw = read(head)
        if raw and raw.startswith(b'ref: '):
            read(Path(git_dir) / raw.decode().strip()[5:])
        read(Path(git_dir) / 'packed-refs')
    watched = [relative(active.path(k)) for k in ('versions', 'records', 'contributions', 'evidence')]
    log = git('log', '--reverse', '--no-renames', '--raw', '--no-abbrev',
              '--format=%x01%H %cI', '--', *watched).decode('utf-8', 'replace') if owns_history else ''
    changes = defaultdict(list)
    at = ''
    for line in log.splitlines():
        if line.startswith('\x01'):
            at = line.partition(' ')[2]
        elif line.startswith(':'):
            metadata, _, name = line.partition('\t')
            fields = metadata.split()
            if len(fields) == 5:
                changes[name].append((at, fields[4], fields[3]))
    # One batch process reads all selected historical blobs, rather than one
    # git show per commit. Raw blob bytes never leave this projection.
    objects = {oid for path in version_paths for _, status, oid in changes[relative(path)]
               if status != 'D'}
    blobs, offset = {}, 0
    raw = git('cat-file', '--batch', payload=('\n'.join(sorted(objects)) + '\n').encode()) if objects else b''
    while offset < len(raw):
        end = raw.index(b'\n', offset)
        header = raw[offset:end].split()
        if len(header) != 3:
            break
        size = int(header[2])
        blobs[header[0].decode()] = json.loads(raw[end + 1:end + 1 + size])
        offset = end + size + 2
    latest = max((entries[-1][0] for entries in changes.values() if entries), default='') + '~'
    for path, (lane, historical, row) in version_paths.items():
        items, history = {}, []
        for at, status, oid in changes[relative(path)]:
            if status != 'D' and oid in blobs:
                old = blobs[oid]
                # Do not recover details of formerly unaccepted/living subjects.
                if old.get('people') == row.get('people'):
                    history.append((at, old.get('versions', [])))
        history.append((latest, row.get('versions', [])))
        for at, entries in history:
            born = []
            for n, item in enumerate(entries, 1):
                key, value = item.get('id', str(n)), weight(item.get('weight'))
                status = item.get('status', item.get('state'))
                refs = set(item.get('sources', []))
                for argument in item.get('for', []):
                    if isinstance(argument, dict):
                        refs.update(argument.get('sources', []))
                state = ('firm' if status in FIRM and refs & graph.get('sources', {}).keys()
                         else 'confirmed' if status in FIRM else 'dropped'
                         if status in DROPPED or value < .05 else 'open')
                target = items.get(key)
                previous = target['w'] if target else None
                previous_state = target['state'] if target else None
                if target is None:
                    target = {'id': opaque(lane + ':' + str(key)), 'lane': lane, 'series': []}
                    items[key] = target
                    born.append(target['id'])
                target.update(label=public_line(item.get('headline') or (item.get('label') if historical else ''),
                                                 w['version_n'].format(n=n)), w=value, state=state)
                # Only literal contrary arguments, never test plans or inferred reasons.
                target['reason'] = next((text for a in item.get('against', [])
                    if historical and (text := public_line(a.get('text') if isinstance(a, dict) else a))), '')
                if previous != value:
                    target['series'].append(value)
                if previous is not None and (abs(value - previous) >= .05 - 1e-9 or state != previous_state):
                    kind = ('settle' if state == 'firm' else 'cool' if value < previous or state == 'dropped' else 'weight')
                    word = ('version_confirmed' if state in {'firm', 'confirmed'} else 'version_dropped'
                            if state == 'dropped' else 'version_strengthened' if value > previous else 'version_weakened')
                    event(at, lane, kind, w[word], w_from=previous, w_to=value, versions=[target['id']])
            if born:
                event(at, lane, 'fork', w['version_started'] if len(born) == 1 else w['versions_started'].format(n=len(born)), versions=born)
        versions.extend(items.values())
    source_counts, outcomes = Counter(), Counter()
    searches = []
    for pattern in ('**/*.json', '**/*.jsonl'):
        for _, data in rows(active.path('searches'), pattern):
            searches.extend(data if isinstance(data, list) else [data])
    from .search_volume import Sources, coverage
    catalog = Sources(active, read)
    searched = coverage(searches, catalog)
    searches = [r for r in searches if isinstance(r, dict)
                if isinstance(r.get('source_id') or r.get('source'), (str, dict))
                and isinstance(r.get('question'), str)
                and type(r.get('hits')) in (int, float) and math.isfinite(r['hits'])
                and r['hits'] >= 0]
    sources, sheets, sheets_known = set(), 0, False
    batch = None
    for row in sorted(searches, key=lambda r: str(r.get('at', ''))):
        source = row.get('source_id') or row.get('source')
        if source:
            sources.add(catalog.canonical(source))
        source_info = graph.get('sources', {}).get(source, {}) if isinstance(source, str) else source or {}
        kind = row.get('source_kind') or row.get('source_type') or source_info.get('kind')
        kind = {'archive-record': 'archive', 'index-entry': 'index', 'document': 'archive'}.get(kind, kind) if isinstance(kind, str) else 'unknown'
        kind = kind if kind in {'archive', 'index', 'database', 'home-paper', 'website', 'memory'} else 'unknown'
        source_counts[kind] += 1
        state = row.get('result_state')
        outcome = 'gap' if state == 'access-gap' else 'zero' if row.get('hits') == 0 else 'results'
        outcomes[outcome] += 1
        pages = row.get('sheets_read', row.get('pages'))
        if isinstance(pages, int) and not isinstance(pages, bool) and pages >= 0:
            sheets_known = True
            sheets += pages
        lane = lane_ids.get(row.get('question'), 'tree')
        # Bounded portions preserve recorded order, without hourly/day buckets.
        if batch is None or batch['lane'] != lane or batch['source_kind'] != kind or batch['count'] == 60:
            batch = {'_order': (str(row.get('at', '')), len(events)), 'lane': lane,
                     'kind': 'work', 'source_kind': kind, 'count': 0, 'zero': 0, 'gap': 0}
            events.append(batch)
        batch['count'] += 1
        batch['zero'] += outcome == 'zero'
        batch['gap'] += outcome == 'gap'
        batch['_order'] = (str(row.get('at', '')), batch['_order'][1])
        batch['line'] = w['checks'].format(n=batch['count'])
    record_rows = [(p, r) for p, r in rows(active.path('records'), '**/*.json')
                   if r.get('kind') in ('archive-record', 'home-paper', 'index-entry')
                   and isinstance(r.get('fields'), dict)]
    documents_read = 0
    for path, row in record_rows:
        if row.get('kind') in {'archive-record', 'home-paper'} and (row.get('reading') or row.get('fields')):
            documents_read += 1
        entries = changes.get(relative(path), [])
        event(next((at for at, status, _ in entries if status == 'A'), latest), 'tree', 'record', w['record_found'])
    documents = {sid for sid, s in graph.get('sources', {}).items()
                 if s.get('kind') in {'record', 'archive-record', 'home-paper', 'document', 'document-scan'} or s.get('type') == 'document'}
    for name, entries in changes.items():
        if name.startswith(relative(active.path('contributions')) + '/'):
            for at, status, _ in entries:
                if status == 'A':
                    event(at, 'tree', 'person', w['tree_extended'])
    for _, row in rows(active.path('questions')):
        if row.get('state') == 'closed' or row.get('addressee') == 'host' or row.get('migrated_correspondence'):
            continue
        text = public_line(row.get('witness_question'))
        if text and len(asks) < 3:
            asks.append({'id': row['id'], 'lane': lane_ids.get(row.get('lane') or row.get('question'), 'tree'),
                         'text': text, 'why': public_line(row.get('why_this_paper')),
                         'options': [public_line(o) for o in row.get('options', []) if public_line(o)][:4]})
    reviewed_pending, answered = [], set()
    for path, row in rows(active._inside('family/feedback/inbox')):
        if row.get('kind') == 'answer':
            answered.add(row.get('ask_id') or row.get('question'))
        if row.get('kind') != 'add_person':
            continue
        if read(active._inside('family/feedback/read/' + path.name)):
            reviewed_pending.append(row.get('id', path.stem))
        elif row.get('anchor') in people or (not people and row.get('anchor') == 'self'):
            pending.append({k: row.get(k, '') for k in ('id', 'anchor', 'relation', 'text', 'place', 'client_time')})
    events.sort(key=lambda e: e['_order'], reverse=True)
    shifts, latest_changes = [], {}
    by_id = {v['id']: v for v in versions}
    for e in events:
        if e['kind'] in {'weight', 'cool', 'settle'}:
            prior = latest_changes.get(e['lane'])
            if prior is None or (e['_order'][0], e['w_to']) > (prior['_order'][0], prior['w_to']):
                latest_changes[e['lane']] = e.copy()
        e.pop('_order')
    for e in sorted(latest_changes.values(), key=lambda e: e['_order'], reverse=True):
        v = by_id[e['versions'][0]]
        shifts.append({'lane': e['lane'], 'label': v['label'], 'w_from': e['w_from'],
                       'w_to': e['w_to'], 'state': v['state'], 'line': e['line']})
    states = Counter(v['state'] for v in versions)
    return {'counters': {'queries': len(searches), 'sources': len(sources),
                         'sheets': sheets if sheets_known else None, 'grains': len(record_rows),
                         'finds': len(documents), 'documents_read': documents_read},
            'summary': {'questions': len(lanes) - 1, 'versions': len(versions),
                        'dropped': states['dropped'], 'firm': states['firm'],
                        'open': states['open'], 'confirmed': states['confirmed']},
            'source_counts': dict(source_counts), 'outcomes': dict(outcomes), 'search_coverage': searched,
            'lanes': lanes, 'versions': versions, 'shifts': shifts[:4],
            'event_pages': [events[i:i + PAGE_SIZE] for i in range(0, len(events), PAGE_SIZE)],
            'asks': [a for a in asks if a['id'] not in answered],
            'pending': pending, 'reviewed_pending': reviewed_pending}, inputs, listings


def line_section(active, graph, w):
    from familiar.research.coverage import collect, format_line_chain, line_front, planning_people

    try:
        data = collect(active)
        front = line_front(data)
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        return ''  # The private reader tolerates unreadable working coverage as well.
    people, esc = graph.get('people', {}), html.escape
    historical = people.keys() & set(planning_people(data, data['tree'].people))
    mode = front['collateral_mode']
    rows = []
    for line in front['lines']:
        if not people.keys() >= set(line['people']):
            continue
        name = line['surname'] or '—'
        if line['secondary']:
            name += f" ({w['lines_secondary']})"
        chain = [step | {'name': people[step['id']].get('name') or ''} for step in line['chain']]
        chain_label = format_line_chain(chain, w['lines_decimal'])
        counts = w['lines_counts'].format(**line)
        if 'living_or_possibly_living' in line:
            counts += ' · ' + w['lines_outside_queue'].format(**line)
        versions = [f"{public_line(v['label'], w['branch'].format(n=n))} ({v['weight'] * 100:g}%)"
                    for n, v in enumerate(line['versions'], 1) if historical.issuperset(v['people'])]
        details = ' · '.join(versions) or ('—' if line['versions'] else w['lines_no_versions'])
        rows.append(f'<li><div><strong>{esc(name)}</strong><div>{esc(chain_label)}</div></div>'
                    f'<span>{esc(details)}</span><small>{esc(counts)}</small></li>')
    return ('<section class="line-front" aria-labelledby="line-front-title"><h3 id="line-front-title" class="h2">'
            + esc(w['lines_title']) + '</h3><p class="sub">' + esc(w['collateral_' + mode])
            + ' <code>familiar.toml</code> · <code>[settings]</code> · '
            + f'<code>"research.collateral" = "{mode}"</code> (off / hints / full)</p>'
            + ('<ul>' + ''.join(rows) + '</ul>' if rows else '<p>' + esc(w['lines_empty']) + '</p>') + '</section>')


def page(active, w, supplemental=False, *, lines=''):
    esc, s = html.escape, w['show']
    title = active.config['family']['title']
    extras = ('<p class="desk-extra"><a href="/desk/journal.html">' + esc(w['journal'])
              + ' · ' + esc(w['stories']) + '</a></p>') if supplemental else ''
    return ('<!doctype html><html lang="' + esc(active.source_language) + '"><head>'
            '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,nofollow,noarchive"><title>' + esc(s['progress'])
            + ' · ' + esc(title) + '</title><link rel="stylesheet" href="/desk/show.css">'
            '<script defer src="/desk/show.js"></script></head><body class="familiar-show">'
            '<main class="wrap"><section class="since">'
            '<div class="kicker">' + esc(s['ongoing']) + '</div><h1>' + esc(s['latest_shifts'])
            + '</h1><ul id="show-shifts"></ul></section>'
            '<section id="show-added" class="added" hidden><h2 class="h2">' + esc(s['added_title'])
            + '</h2><ul id="show-added-list"></ul></section>'
            '<section class="volume"><h2 class="h2">' + esc(s['work_volume']) + '</h2>'
            '<div class="counts" id="show-summary"></div><p id="show-volume"></p>'
            '<section id="show-searched" class="searched" hidden aria-labelledby="searched-title">'
            '<h3 id="searched-title" class="h2">' + esc(s['searched_title']) + '</h3>'
            '<div class="searched-layout"><div><p id="searched-sources" class="searched-total"></p>'
            '<p id="searched-growth" class="sub"></p><p id="searched-repeat"></p></div>'
            '<div><p id="searched-requests" class="searched-total"></p>'
            '<div id="searched-days" class="searched-days" role="list"></div>'
            '<p id="searched-undated" class="sub" hidden></p></div></div>'
            '<p class="sub">' + esc(s['searched_categories']) + '</p><div id="show-sources"></div>'
            '<p class="searched-note">' + esc(s['searched_note']) + '</p></section>'
            + lines + '</section>'
            '<div class="show"><section><h2 class="h2">' + esc(s['log']) + '</h2><p class="sub">'
            + esc(s['log_hint']) + '</p><div class="log"><ol id="show-asks"></ol><ol id="show-log"></ol></div>'
            '<nav id="show-pagination" aria-label="' + esc(s['log']) + '"></nav></section><aside class="rail">'
            '<section><h2 class="h2">' + esc(s['versions']) + '</h2><p class="sub">'
            + esc(s['versions_hint']) + '</p><div class="vmap" id="show-versions"></div></section></aside></div>'
            + extras + '</main></body></html>').encode()
