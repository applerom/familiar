# START_MODULE_CONTRACT: MOD-RESEARCH-COVERAGE
# PURPOSE: Recover source visits and their scope from journals and read records, keeping identity and plan completeness separate from model strength.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - only local journals, records and the tree are read; no network and no new step for the researcher [review: engine lead]
# - unrecorded outcomes and access gaps never count as zero; an incomplete zero never counts as controlled [review: engine lead]
# - strength comes from the research.search_strength setting; an executor no key names has strength 0 (unknown), never a guess [review: engine lead]
# - rows not in the ledger form are counted aside, not mixed into the matrix [review: engine lead]
# - catalogue epoch/place mismatches leave the queue, never erase recorded searches; unknown geography remains eligible [review: engine lead]
# - the life assessment excludes living and possibly living people from the recheck queue, counted separately [review: engine lead]
# - collateral descendants stay outside the main planning denominator and queue; the line front derives from tree, versions and existing cells [review: engine lead]
# - explicit people survive dictionary mismatch; local identity work precedes repeat searches and stopped sources wait [review: engine lead]
# - local reviews assess record links only; no search strength, forms, yield or availability comes from them [review: engine lead]
# CHANGES_WITH:
# - MOD-SEARCH-LEDGER (the ledger form it reads)
# - docs/research-coverage.md
# :END_MODULE_CONTRACT
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime

from familiar.desk.search_volume import domain, name_key
from familiar.instance.gate import boundary

from .search_ledger import METHOD, Resolver, Tree, in_ledger_form, is_review, read_rows, read_versions, row_tokens, search_files
from .coverage_evidence import references, review_links
from .search_variants import norm
from .coverage_context import (contains, episode_fit, form_metadata, life_window, missing_forms, person_text,
                               record_visits, row_people, script_of, text)
from .search_variants import form_data
from .coverage_quality import availability, query_issues

GAP_STATES = {'access-gap', 'refused', 'not_ready', 'app_error', 'help-stop', 'coverage-gap'}
RANK = {'none': 0, 'gap': 1, 'unrecorded': 2, 'query-dubious': 2.5, 'zero-uncontrolled': 3, 'zero-controlled': 4, 'read': 4.5, 'found': 5}
MARK = {'found': 'R', 'read': 'D', 'zero-controlled': 'Z', 'zero-uncontrolled': 'z', 'gap': '!', 'unrecorded': '?', 'query-dubious': 'Q', 'none': '.'}
REASON = {'identity-unestablished': 15, 'identity-conflict': 16, 'source-stopped': 0, 'query-dubious': 4, 'not-searched': 5, 'access-gap': 4, 'outcome-unrecorded': 4, 'weak-only': 4, 'zero-without-control': 3, 'forms-missing': 2, 'forms-unassessed': 2, 'source-grown': 1}
OPEN_EXCLUSIONS = {'accepted', 'closed', 'resolved', 'settled', 'rejected', 'superseded'}
CLOSED_OPTIONS = OPEN_EXCLUSIONS | {'accepted_evidence', 'firm', 'refuted', 'discarded', 'dropped', 'ruled-out'}
PARENT_QUESTION = re.compile(
    r'\b(?:parents?|parentage|father|mother|paternity|maternity|родител\w*|отец|отца|матери|мать|'
    r'отцовств\w*|материнств\w*|rodzic\w*|ojciec|ojca|matka|matki)\b', re.I)


def control_basis(row):
    for key in ('control', 'positive_control', 'zero_checks'):
        value = row.get(key)
        if not value:
            continue
        if isinstance(value, dict) and (any(value.get(k) is False for k in ('ok', 'found', 'success', 'control_ok'))
                or any(value.get(k) == 0 for k in ('hits', 'count') if k in value)
                or value.get('status') in {'failed', 'refused', 'not_ready'}):
            continue
        if isinstance(value, str) and re.search(r'(?i)not found|failed|не найден|неуспеш|без контрол', value):
            continue
        return 'field'
    coverage = row.get('coverage') if isinstance(row.get('coverage'), dict) else {}
    note = text([coverage.get('note'), row.get('meaning'), row.get('meaning_as_written')])
    # A positive observation, not a mention of a required/failed control.
    for clause in re.split(r'[.;\n]', note):
        if re.search(r'(?i)контрол|control', clause) and not re.search(r'(?i)\b(не|нет|без|no|not|failed|нужен|требуется)\b|неуспеш', clause):
            if re.search(r'(?i)успеш|найден|находится|находит|показано|\b[1-9]\d*\b|success|found|returns', clause):
                return 'text'
    return None


def settings(instance):
    from familiar.rules.cascade import Registry
    from familiar.rules.roles import method_root
    registry = Registry(method_root() / 'rules', instance)
    table = dict(registry.settings['research.search_strength']['default'])
    table.update(registry.resolve_setting('research.search_strength').value)
    return (table, registry.resolve_setting('research.recheck_strength').value,
            registry.resolve_setting('research.collateral').value)


def strength(by, table):
    """1-4 by the most specific key of model:effort; 0 when no key names this executor."""
    model, effort = (by.get('model') or '').lower(), (by.get('effort') or '').lower()
    best, value = None, 0
    for key, level in table.items():
        name, _, wanted = key.partition(':')
        if name != '*' and not re.search(r'(?<![a-z0-9])' + re.escape(name) + r'(?![a-z0-9])', model):
            continue
        if wanted not in ('*', effort):
            continue
        rank = ((name != '*') + (wanted != '*'), len(name))
        if best is None or rank > best:
            best, value = rank, level
    return value


def outcome(row):
    if is_review(row):
        return 'none'
    state, hits = row.get('result_state'), row.get('hits')
    coverage = row.get('coverage') if isinstance(row.get('coverage'), dict) else {}
    if state in GAP_STATES:
        return 'gap'
    if query_issues(row):
        return 'query-dubious'
    if state == 'unrecorded' or hits is None:
        return 'unrecorded'
    if type(hits) in (int, float) and hits > 0:
        return 'found'
    if hits == 0:
        if state == 'zero-uncontrolled' or not coverage.get('years') or not coverage.get('forms') or not coverage.get('read'):
            return 'zero-uncontrolled'
        return 'zero-controlled' if control_basis(row) else 'zero-uncontrolled'
    return 'gap'


def collect(instance):
    """The journal as person-by-source cells, plus what could not be placed."""
    tree, resolver, versions = Tree(instance), Resolver(instance), read_versions(instance)
    from familiar.tree.birth_guess import apply as birth_guess
    birth_guess(instance, tree.graph, host_private=True)
    table, threshold, mode = settings(instance)
    cells, sources, legacy, no_people, unknown, titles, no_source = {}, {}, 0, 0, set(), {}, 0
    found_by_source, planning_events, source_access, access_journals = {}, {}, {}, {}
    reviews = {}
    for path in search_files(instance):
        rows, _ = read_rows(path)
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            if not in_ledger_form(row):
                legacy += 1
                continue
            unknown.update(p for p in row['people'] if not tree.person(p))
            sid = resolver.row_source(row)
            if is_review(row):
                for link in review_links(instance, row):
                    if not (person := tree.person(link.get('person'))):
                        continue
                    for key in references(link.get('record')):
                        ident = (person['id'], sid, key)
                        assessment = link | {'search': row.get('id'), 'at': str(row.get('at') or '')}
                        if assessment['at'] >= reviews.get(ident, {}).get('at', ''):
                            reviews[ident] = assessment
                continue
            if not sid:
                text = str(row.get('source'))
                if METHOD.search(text) or not row.get('source'):
                    no_source += 1
                    continue
                sid = '~' + (domain(text) or name_key(text))[:60]
                titles.setdefault(sid, text[:80])
            kind = outcome(row)
            issues = query_issues(row, tree)
            if issues and kind != 'gap':
                kind = 'query-dubious'
            if kind != 'unrecorded':
                event = availability(row, kind == 'gap')
                previous = source_access.get(sid, {})
                same_day_unordered = (event['at'][:10] == previous.get('at', '')[:10]
                                      and (len(event['at']) <= 10 or len(previous.get('at', '')) <= 10)
                                      and access_journals.get(sid) != path)
                if (event['at'] >= previous.get('at', '') or same_day_unordered and kind == 'gap') and not (
                        previous.get('state') == 'stopped' and event['state'] == 'available'
                        and (same_day_unordered or previous.get('route') == 'search' and event['route'] == 'page')):
                    source_access[sid] = event
                    access_journals[sid] = path
            by = row['by']
            level = strength(by, table) if kind not in {'gap', 'unrecorded'} else 0
            at = str(row.get('at') or '')[:10]
            used = sources.setdefault(sid, {'rows': 0, 'people': set()})
            used['rows'] += 1
            people, basis, scope = row_people(row, tree, resolver.catalog)
            no_people += not bool(people)
            words = row_tokens(row)
            forms = row['coverage'].get('forms') if isinstance(row.get('coverage'), dict) else None
            for pid in people:
                person = tree.person(pid)
                if not person:
                    unknown.add(pid)
                    continue
                pid = person['id']
                used['people'].add(pid)
                cell = cells.setdefault((pid, sid), new_cell())
                cell['rank'] = max(cell['rank'], RANK[kind])
                cell['passes'] += 1
                cell['basis'].add(basis)
                cell['scopes'].add(scope)
                if kind == 'gap':
                    refused = availability(row, True)
                    if refused['at'] >= (cell['latest_refusal'] or {}).get('at', ''):
                        cell['latest_refusal'] = refused
                if issues:
                    cell['query_issues'].append({'search': row.get('id'), 'issues': issues})
                if basis != 'question' and not set(words).intersection(tree.people[pid]['surnames']):
                    cell['dictionary_mismatches'].append(row.get('id'))
                if control := control_basis(row):
                    cell['controls'].add(control)
                candidate = row.get('candidate_forms') or {}
                if isinstance(candidate, dict):
                    for key, values in candidate.items():
                        if key in {'surname', 'given_name'} and isinstance(values, list):
                            cell['planned'].update(f for f in values if isinstance(f, str))
                if isinstance(forms, list):
                    cell['planned'].update(f for f in forms if isinstance(f, str))
                if at:
                    cell['first'] = min(at, cell['first'] or at)
                    cell['last'] = max(at, cell['last'] or at)
                for form in forms if isinstance(forms, list) else [forms] if isinstance(forms, str) else []:
                    if isinstance(form, str) and form.strip():
                        cell['forms'][form.strip()[:80]] = True
                read = row['coverage'].get('read') if isinstance(row.get('coverage'), dict) else None
                if kind in {'found', 'zero-controlled', 'zero-uncontrolled'} and type(read) in (int, float) and read > 0:
                    cell['words'].update(words)
                    query = row.get('query')
                    values = [v for k, v in query.items() if re.search(r'name|surname|фамил|имя', k, re.I)] if isinstance(query, dict) else [query]
                    cell['query_scripts'].update(s for v in values if isinstance(v, str) and (s := script_of(v)))
                    if isinstance(forms, list):
                        cell['phrases'].update(norm(form_data(f)['text']) for f in forms if isinstance(f, str))
                who = cell['who'].setdefault((by.get('agent'), by.get('model'), by.get('effort')), {'passes': 0, 'strength': level})
                who['passes'] += 1
                who['strength'] = max(who['strength'], level)
                cell['strength'] = max(cell['strength'], level)
                if kind == 'found':
                    found_by_source[sid] = found_by_source.get(sid, 0) + 1
    for visit in record_visits(instance, tree, resolver, reviews):
        for pid, events in visit['planning_events'].items():
            planning_events.setdefault(pid, []).extend(events)
        sid = visit['source']
        used = sources.setdefault(sid, {'rows': 0, 'people': set()})
        for pid in visit['people']:
            used['people'].add(pid)
            cell = cells.setdefault((pid, sid), new_cell())
            cell['rank'] = max(cell['rank'], RANK['read'])
            cell['passes'] += 1
            cell['records'].append(visit['record'])
            cell['record_links'].append({'record': visit['record'], **visit['links'][pid]})
            cell['basis'].add('record-person')
            cell['identified'] |= pid in visit['established']
            cell['scopes'].add('record')
            if at := str(visit['at'])[:10]:
                cell['first'] = min(at, cell['first'] or at)
                cell['last'] = max(at, cell['last'] or at)
            by = visit['by']; level = strength(by, table)
            who = cell['who'].setdefault((by.get('agent'), by.get('model'), by.get('effort')), {'passes': 0, 'strength': 0})
            who['passes'] += 1; who['strength'] = max(who['strength'], level)
            cell['strength'] = max(cell['strength'], level)
    named = {pid for pid, _ in cells} | {p['id'] for v in versions.values() for ident in v['people']
                                       if (p := tree.person(ident))}
    from familiar.tree.builder import read_json
    root = (read_json(instance.path('tree_metadata'), {}).get('root') or tree.graph.get('root')
            or next(iter(tree.people), None))
    root = tree.aliases.get(root, root)
    distance = distances(tree.graph, root)
    lines, collateral = family_lines(tree.graph, root)
    main = {pid for line in lines for pid in line}
    focus = (main | named) - collateral.keys()
    side = sorted(collateral) if mode == 'full' else []
    data = {'tree': tree, 'resolver': resolver, 'versions': versions, 'table': table, 'threshold': threshold,
            'cells': cells, 'sources': sources, 'legacy': legacy, 'no_people': no_people, 'no_source': no_source, 'unknown': sorted(unknown),
            'focus': sorted(focus), 'side': side, 'named': named, 'lines': lines,
            'collateral': collateral, 'collateral_mode': mode,
            'yield': found_by_source, 'titles': titles, 'distance': distance,
            'form_metadata': form_metadata(instance), 'planning_events': planning_events, 'source_access': source_access}
    # Each FamilySearch channel is independently eligible even if only one has a recorded visit.
    if any(s.startswith('familysearch') for s in sources):
        for sid in ('familysearch-tree', 'familysearch-records', 'familysearch-fulltext'):
            if sid in resolver.catalog.sources:
                sources.setdefault(sid, {'rows': 0, 'people': set()})
    contexts = {pid: planning_context(data, pid) for pid in [*focus, *side]}
    data['not_applicable'] = {(pid, sid): applicability(data, pid, sid, context)
                              for pid, context in contexts.items() for sid in sources}
    return data


def new_cell():
    return {'rank': 0, 'passes': 0, 'first': None, 'last': None, 'forms': {}, 'words': set(),
            'who': {}, 'strength': 0, 'basis': set(), 'planned': set(), 'scopes': set(),
            'records': [], 'record_links': [], 'identified': False, 'controls': set(), 'phrases': set(),
            'dictionary_mismatches': [], 'query_issues': [], 'query_scripts': set(), 'latest_refusal': None}


def distances(graph, root):
    """Steps from the tree's root person through marriages and parent links; absent for people the root does not reach."""
    people = graph.get('people', {})
    near = {}
    for family in graph.get('families', []):
        members = [family.get('husband'), family.get('wife'), *family.get('children', [])]
        parents = [m for m in members[:2] if m]
        for a in parents:
            near.setdefault(a, set()).update(m for m in members if m and m != a)
        for child in members[2:]:
            if child:
                near.setdefault(child, set()).update(parents)
    seen = {root: 0} if root in people else {}
    queue = list(seen)
    for pid in queue:  # the list grows while it is read: breadth-first order
        for other in sorted(near.get(pid, ())):
            if other not in seen:
                seen[other] = seen[pid] + 1
                queue.append(other)
    return seen


def family_lines(graph, root):
    """Father chains split at mothers; collateral people retain their ancestor anchors."""
    people = graph['people']
    children, spouses, siblings = (defaultdict(set) for _ in range(3))
    fathers, mothers = defaultdict(set), defaultdict(set)
    unsettled = {'hypothesis', 'conflict', 'rejected', 'disproved'}
    for family in graph.get('families', []):
        if family.get('status') in unsettled:
            continue
        father, mother = family.get('husband'), family.get('wife')
        kids = set(family.get('children', [])) & people.keys()
        if father in people and mother in people:
            spouses[father].add(mother)
            spouses[mother].add(father)
        for child in kids:
            siblings[child].update(kids)
            for parent, role in ((father, fathers), (mother, mothers)):
                if parent in people and parent != child:
                    role[child].add(parent)
                    children[parent].add(child)

    # The working tree can have an accepted parent edge without a family group.
    for edge in graph.get('edges', []):
        parent, child = edge.get('parent'), edge.get('child')
        if parent not in people or child not in people or parent == child or edge.get('status') in unsettled:
            continue
        if parent not in fathers[child] and parent not in mothers[child]:
            role = edge.get('role')
            is_father = role in {'father', 'отец', 'ojciec'} or (
                role not in {'mother', 'мать', 'matka'} and str(people[parent].get('sex')).lower() == 'm')
            (fathers if is_father else mothers)[child].add(parent)
        children[parent].add(child)

    starts = [root, *sorted(spouses[root] - {root})] if root in people else []
    lines, ancestors, started = [], set(), set()
    for start in starts:
        if start in started:
            continue
        started.add(start)
        chain, pid = [], start
        while pid and pid not in chain:
            chain.append(pid)
            paternal, maternal = sorted(fathers[pid]), sorted(mothers[pid])
            starts.extend([*maternal, *paternal[1:]])
            ancestors.update([*paternal, *maternal])
            pid = next(iter(paternal), None)
        lines.append(chain)

    main = {pid for chain in lines for pid in chain}
    for pid in main:
        for parent in fathers[pid] | mothers[pid]:
            siblings[pid].update(children[parent])
    collateral = defaultdict(set)
    for ancestor in sorted(ancestors):
        for sibling in sorted(siblings[ancestor] - main):
            pending = sorted(children[sibling])
            seen = main | {sibling}
            for pid in pending:
                if pid in seen:
                    continue
                seen.add(pid)
                for relative in {pid, *spouses[pid]} - main:
                    collateral[relative].add(ancestor)
                pending.extend(sorted(children[pid]))
    primary_siblings = set().union(*(siblings[pid] for pid in main))
    return lines, {pid: anchors for pid, anchors in collateral.items() if pid not in primary_siblings}


def planning_context(data, pid):
    person = data['tree'].graph['people'][pid]
    if events := data.get('planning_events', {}).get(pid):
        person = person | {'events': person.get('events', []) + events}
    raw = person_text(person)
    countries, regions = set(), set()
    for entry in data['resolver'].catalog.coverage_places:
        if any(contains(raw, a) for a in entry.get('aliases', [])):
            countries.update(entry.get('countries', []))
            regions.update(entry.get('regions', []))
    return life_window(person), raw, countries, regions


def applicability(data, pid, sid, context=None):
    """Planning fit only: generous life window; unknown dates/places never exclude a source."""
    source = data['resolver'].catalog.sources.get(sid, {})
    (lower, upper), raw, countries, regions = context or planning_context(data, pid)
    years = source.get('years', [])
    reasons = []
    person = data['tree'].graph['people'][pid]
    guess = person.get('birth_guess') or person.get('birthGuess') or {}
    birth = guess.get('year') if isinstance(guess, dict) else guess
    # The uncertainty envelope remains useful for overlap, but not as a reason
    # to prioritize a person who was already about a century old.
    birth = birth if isinstance(birth, (int, float)) else lower
    if len(years) == 2 and ((lower is not None and lower > years[1]) or (upper is not None and upper < years[0])):
        reasons.append('epoch')
    elif len(years) == 2 and birth is not None and years[0] - birth > 100:
        reasons.append('age-at-source-start')
    if (countries and source.get('countries') and not countries.intersection(source['countries'])) or (
            regions and source.get('regions') and not regions.intersection(source['regions'])):
        reasons.append('region')
    for field in ('parishes', 'episodes'):
        if source.get(field) and not any(contains(raw, a) for a in source[field]):
            reasons.append('parish' if field == 'parishes' else 'episode')
    requires = source.get('planning_requires')
    if requires and not source.get(requires + 's'):
        terms = source.get('planning_terms', [])
        known = any(contains(raw, term) for term in terms)
        if requires == 'parish':
            known |= bool(re.search(r'(?i)приход|paraf|parish', raw))
            known |= bool(data['cells'].get((pid, sid)))  # an existing targeted visit is a reason to revisit, never an index claim
        if not known:
            reasons.append(requires + '-unestablished')
    return reasons


def title(data, sid):
    entry = data['resolver'].catalog.sources.get(sid)
    return entry.get('title', sid) if entry else data['titles'].get(sid, sid)


def cell_view(data, pid, sid):
    cell = data['cells'].get((pid, sid))
    access = data.get('source_access', {}).get(sid)
    if not cell:
        return {'outcome': 'none', 'strength': 0, 'passes': 0, 'first': None, 'last': None, 'forms': [],
                'missing_forms': [], 'who': [], 'person_basis': [], 'identified': False,
                'records': [], 'record_links': [], 'scope': [], 'plan_complete': False,
                'availability': access, 'latest_refusal': None, 'identity': 'unassessed', 'query_issues': [], 'dictionary_mismatches': [],
                'script_status': 'catalogue' if data['resolver'].catalog.sources.get(sid, {}).get('search_scripts') else 'unverified'}
    missing = missing_forms(data, pid, sid, cell)
    statuses = {r['status'] for r in cell['record_links']}
    identity = ('conflict' if 'conflict' in statuses else 'unestablished' if 'unestablished' in statuses
                else 'same' if 'same' in statuses else 'other' if 'other' in statuses
                else 'context-only' if statuses == {'mention'} else 'unassessed')
    return {'outcome': next(k for k, v in RANK.items() if v == cell['rank']), 'strength': cell['strength'],
            'passes': cell['passes'], 'first': cell['first'], 'last': cell['last'],
            'forms': list(cell['forms']), 'missing_forms': missing, 'person_basis': sorted(cell['basis']),
            'people_basis': 'surname-place' if cell['basis'] == {'surname-place'} else sorted(cell['basis']),
            'scope': sorted(cell['scopes']), 'identified': cell['identified'], 'records': cell['records'],
            'record_links': cell['record_links'], 'identity': identity, 'availability': access,
            'latest_refusal': cell['latest_refusal'],
            'query_issues': cell['query_issues'], 'dictionary_mismatches': cell['dictionary_mismatches'],
            'script_status': 'catalogue' if data['resolver'].catalog.sources.get(sid, {}).get('search_scripts') else 'unverified',
            'control_basis': sorted(cell['controls']),
            'plan_complete': bool(cell['words']) and not missing,
            'who': sorted(({'agent': a, 'model': m, 'effort': e, 'strength': v['strength'], 'passes': v['passes']}
                           for (a, m, e), v in cell['who'].items()), key=lambda w: (-w['strength'], str(w['agent'])))}


def planning_sources(data):
    # A reference work (a dictionary, a law text) holds no person to look for.
    catalog = data['resolver'].catalog.sources
    return sorted(s for s in data['sources'] if not s.startswith('~') and catalog.get(s, {}).get('kind') != 'reference')


def planning_people(data, people):
    return (pid for pid in people if data['tree'].graph['people'][pid].get('life_assessment', {}).get('status') == 'dead')


def eligible_cells(data, people):
    sources = planning_sources(data)
    return ((pid, sid) for pid in planning_people(data, people) for sid in sources
            if not data['not_applicable'].get((pid, sid)))


def recheck(data, limit=None):
    """Cells worth another look, most useful first within each search scope."""
    tree, threshold = data['tree'], data['threshold']
    catalog = data['resolver'].catalog.sources
    open_people = {p['id'] for v in data['versions'].values()
                   if v.get('status', v.get('state')) not in OPEN_EXCLUSIONS
                   for ident in v['people'] if (p := tree.person(ident))}
    queue = []
    for pid, sid in eligible_cells(data, [*data['focus'], *data['side']]):
        view = cell_view(data, pid, sid)
        kind, reasons = view['outcome'], []
        action = 'search'
        if view['identity'] in {'unestablished', 'conflict'}:
            reasons.append('identity-conflict' if view['identity'] == 'conflict' else 'identity-unestablished')
            action = 'link-record'
        elif view['identity'] in {'same', 'other', 'context-only'} and not any(r.get('review') for r in view['record_links']):
            continue
        elif view['availability'] and view['availability']['state'] == 'stopped':
            reasons.append('source-stopped')
            action = 'wait-for-access'
        elif kind == 'none':
            reasons.append('not-searched')
        elif kind == 'query-dubious':
            reasons.append('query-dubious')
        elif kind in {'gap', 'unrecorded'}:
            reasons.append('access-gap' if kind == 'gap' else 'outcome-unrecorded')
        else:
            if view['strength'] < threshold:
                reasons.append('weak-only')
            if kind == 'zero-uncontrolled':
                reasons.append('zero-without-control')
            if view['missing_forms']:
                reasons.append('forms-missing')
            elif not view['plan_complete']:
                reasons.append('forms-unassessed')
        updated = str(catalog.get(sid, {}).get('updated') or '')
        if action == 'search' and updated and kind != 'none' and view['last'] and updated > view['last']:
            reasons.append('source-grown')
        if not reasons:
            continue
        score = sum(REASON[r] for r in reasons) + (pid in open_people) + (data['yield'].get(sid, 0) > 0)
        if action == 'search':
            source = catalog.get(sid, {})
            fit = episode_fit(tree.graph['people'][pid], source)
            score += fit
            if fit > 0:
                reasons.append('known-episode')
            years = source.get('years', [])
            lower, _ = life_window(tree.graph['people'][pid])
            if lower and len(years) == 2 and set(source.get('classes', [])) & {'military', 'award'} and years[1] - lower < 16:
                score -= 6
                reasons.append('child-at-source-epoch')
        queue.append({'person': pid, 'name': tree.people[pid]['name'], 'source': sid, 'title': title(data, sid),
                      'reasons': reasons, 'score': score, 'outcome': kind, 'strength': view['strength'],
                      'last': view['last'], 'missing_forms': view['missing_forms'], 'action': action,
                      'availability': view['availability'], 'record_links': view['record_links'],
                      'latest_refusal': view['latest_refusal'],
                      'query_issues': view['query_issues']})
    queue.sort(key=lambda q: (q['person'] in data['collateral'], -q['score'], q['person'], q['source']))
    return queue[:limit] if limit else queue


def matrix_group(data, group):
    people = [{'id': pid, 'name': data['tree'].people[pid]['name'], 'distance': data['distance'].get(pid),
               'not_applicable': [sid for sid in data['sources'] if data['not_applicable'].get((pid, sid))],
               'cells': {sid: cell_view(data, pid, sid) for sid in data['sources'] if (pid, sid) in data['cells']}}
              for pid in group]
    excluded = [data['not_applicable'][pid, sid] for pid in group for sid in data['sources']
                if data['not_applicable'].get((pid, sid))]
    return {'people': people, 'totals': {'people': len(people),
            'cells': sum(len(p['cells']) for p in people),
            'eligible_cells': sum(1 for _ in eligible_cells(data, group)),
            'living_or_possibly_living': len(group) - sum(1 for _ in planning_people(data, group)),
            'not_applicable': len(excluded), 'not_applicable_epoch': sum('epoch' in r for r in excluded),
            'not_applicable_region': sum('region' in r for r in excluded)}}


def collateral_hints(data):
    if data['collateral_mode'] == 'off':
        return []
    hints = {}
    for (pid, _), cell in data['cells'].items():
        if pid in data['collateral']:
            for link in cell['record_links']:
                if link['status'] != 'other':
                    hints[pid, link['record']] = link['status']
    return [{'person': pid, 'name': data['tree'].people[pid]['name'], 'record': record,
             'status': status, 'ancestors': sorted(data['collateral'][pid])}
            for (pid, record), status in sorted(hints.items())]


def matrix(data):
    main = matrix_group(data, data['focus'])
    sources = [{'id': sid, 'title': title(data, sid), 'catalogued': not sid.startswith('~'),
                'rows': used['rows'], 'people': len(used['people'])}
               for sid, used in sorted(data['sources'].items(), key=lambda kv: -kv[1]['rows'])]
    collateral = {'mode': data['collateral_mode'], 'hints': collateral_hints(data)}
    if data['collateral_mode'] == 'full':
        collateral.update(matrix_group(data, data['side']))
    return {'schema': 1, 'generated_at': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'strength_table': data['table'], 'recheck_strength': data['threshold'],
            'totals': main['totals'] | {'sources': len(sources),
                       'rows_not_in_ledger_form': data['legacy'], 'rows_without_people': data['no_people'],
                       'unknown_people': data['unknown'],
                       'rows_without_source': data['no_source']},
            'sources': sources, 'people': main['people'], 'collateral': collateral}


def line_front(data):
    """Derive frontier questions and planning gaps without adding ledger rows."""
    tree = data['tree']
    by_person = defaultdict(list)
    for ident, question in data['versions'].items():
        if question.get('status', question.get('state')) in OPEN_EXCLUSIONS:
            continue
        if not PARENT_QUESTION.search(ident.replace('_', ' ') + ' ' + str(question.get('title', ''))):
            continue
        subjects = sorted({tree.aliases.get(pid, pid) for pid in question['people']})
        for option in question.get('versions') or []:
            if not isinstance(option, dict) or option.get('status', option.get('state')) in CLOSED_OPTIONS:
                continue
            weight = option.get('weight')
            if type(weight) not in (int, float) or not 0 <= weight <= 1:
                continue
            version = {'question': ident, 'id': option.get('id'), 'label': option.get('label') or option.get('id'),
                       'weight': weight, 'people': subjects}
            for pid in subjects:
                by_person[pid].append(version)
    hints = collateral_hints(data)
    lines = []
    for chain in data['lines']:
        gaps = Counter()
        for key in eligible_cells(data, chain):
            cell = data['cells'].get(key)
            if not cell or cell['rank'] == RANK['none']:
                gaps['not_searched'] += 1
            elif cell['rank'] >= RANK['zero-uncontrolled'] and cell['strength'] < data['threshold']:
                gaps['weak'] += 1
        start, end = chain[0], chain[-1]
        members = set(chain)
        versions = sorted(by_person[end], key=lambda v: -v['weight'])
        lines.append({'start': {'id': start, 'name': tree.people[start]['name']},
                      'frontier': {'id': end, 'name': tree.people[end]['name']}, 'people': chain,
                      'versions': versions, 'not_searched': gaps['not_searched'], 'weak': gaps['weak'],
                      'collateral_hints': sum(not members.isdisjoint(h['ancestors']) for h in hints)})
    def priority(line):
        weight = max((v['weight'] for v in line['versions']), default=0)
        return (-(line['not_searched'] + line['weak']) * (1 + weight), -weight, line['start']['id'])
    return {'schema': 1, 'collateral_mode': data['collateral_mode'], 'lines': sorted(lines, key=priority)}


def person_card(data, pid):
    person = data['tree'].person(pid)
    if not person:
        raise ValueError(f'unknown person: {pid}; inspect ids with tree build --view working')
    pid = person['id']
    seen = {sid: cell_view(data, pid, sid) for sid in data['sources'] if (pid, sid) in data['cells']}
    excluded = {sid: applicability(data, pid, sid) for sid in data['sources'] if not sid.startswith('~')}
    planned = pid not in data['collateral'] or data['collateral_mode'] == 'full'
    never = [{'id': sid, 'title': title(data, sid)} for sid, reasons in sorted(excluded.items())
             if planned and sid not in seen and not reasons and data['resolver'].catalog.sources.get(sid, {}).get('kind') != 'reference']
    return {'schema': 1, 'person': pid, 'name': person['name'], 'recheck_strength': data['threshold'],
            'sources': [{'id': sid, 'title': title(data, sid), **view} for sid, view in sorted(seen.items(), key=lambda kv: kv[1]['last'] or '', reverse=True)],
            'never_looked': never,
            'not_applicable': [{'id': sid, 'reasons': r} for sid, r in sorted(excluded.items()) if r],
            'recheck': [q for q in recheck(data) if q['person'] == pid][:15]}


def who_line(view):
    return ', '.join(' '.join(filter(None, [w['agent'], w['model'], w['effort']])) + f" (s{w['strength']})" for w in view['who'][:3])


def markdown_card(card):
    out = [f"# {card['name']} ({card['person']}): where it was looked for", '',
           f"Strength 1-4 (0 unknown); a pass below {card['recheck_strength']} is weak.", '',
           '| Source | Outcome / identity | Passes | Dates | Strength | Who | Forms read | Forms missing | Quality / access |', '|---|---|---|---|---|---|---|---|---|']
    for s in card['sources']:
        notes = []
        if s['script_status'] == 'unverified':
            notes.append('письменность не проверена')
        if s['dictionary_mismatches']:
            notes.append('пополнить словарь: ' + ', '.join(str(v) for v in s['dictionary_mismatches']))
        if s['query_issues']:
            notes.append('форма запроса сомнительна')
        access = s.get('availability') or {}
        if access.get('state') == 'stopped':
            notes.append(f"! {access['at']} {access['kind']}: wait-for-access")
        refused = s.get('latest_refusal') or {}
        if refused:
            notes.append(f"last cell refusal: {refused['at']} {refused['kind']}")
        out.append(f"| {s['title']} | {s['outcome']} / {s['identity']} ({', '.join(s['scope'])}) | {s['passes']} | {s['first']}..{s['last']} | {s['strength']} | "
                   f"{who_line(s)} | {', '.join(s['forms'][:6])} | {', '.join(s['missing_forms'][:4])}{' …' if len(s['missing_forms']) > 4 else ''} | {'; '.join(notes)} |")
        for link in s['record_links']:
            out.append(f"  {link['record']}: {link['status']}; confidence={link.get('confidence')}; roles={link.get('roles', [])}; differences={json.dumps(link['differences'], ensure_ascii=False)}")
    out += ['', 'Never looked in: ' + (', '.join(s['id'] for s in card['never_looked']) or 'nothing in the catalogue'),
            f"Not applicable by epoch/region: {len(card['not_applicable'])}.", '']
    return '\n'.join(out + markdown_queue(card['recheck'], 'Worth another look for this person'))


def markdown_queue(queue, heading):
    out = [f'## {heading}', '', '| # | Person | Source | Why | Now |', '|---|---|---|---|---|']
    for n, q in enumerate(queue, 1):
        now = q['outcome'] + (f", s{q['strength']}, {q['last']}" if q['last'] else '')
        access = q.get('latest_refusal') or q.get('availability') or {}
        if access.get('state') == 'stopped':
            now += f"; ! {access['at']} {access['kind']}"
        out.append(f"| {n} | {q['name']} ({q['person']}) | {q['source']} | {q.get('action', 'search')}: {', '.join(q['reasons'])} | {now} |")
    return out if queue else [f'## {heading}', '', 'Nothing to recheck.']


def markdown_matrix(view):
    """Catalogue sources as columns; every other source a person was looked for in is one last column."""
    sources = [s for s in view['sources'] if s['catalogued']]
    other = sum(1 for s in view['sources'] if s['people'] and not s['catalogued'])
    t = view['totals']
    out = ['# Search coverage: people by source', '',
           f"{t['people']} people, {len(sources)} catalogue sources and {other} others, {t['cells']} recorded cells, {t['eligible_cells']} eligible for planning; "
           f"{t['rows_not_in_ledger_form']} journal rows not in ledger form, {t['rows_without_people']} rows name no person; "
           f"{t['not_applicable']} cells not applicable by epoch/region; {t['living_or_possibly_living']} living/possibly living people outside recheck; {t['rows_without_source']} rows without a source.",
           'Cell: R result rows, D read record, +F established identity, Z zero with control, z zero without control, ? outcome unrecorded, ! access gap, . not looked, - planning fit unestablished/outside scope; digit = strongest pass (1-4, 0 = executor model not recorded); '
           '? = the person was inferred from the question only, not from the names searched.', '']
    out += matrix_table(view['people'], sources)
    collateral = view['collateral']
    out += ['', f"Collateral research: `{collateral['mode']}`."]
    if 'totals' in collateral:
        t = collateral['totals']
        out += ['', '## Collateral coverage', '',
                f"{t['people']} people, {t['cells']} recorded cells, {t['eligible_cells']} eligible for planning.", '']
        out += matrix_table(collateral['people'], sources)
    if collateral['mode'] != 'off':
        hints = collateral['hints']
        out += ['', '## Collateral hints', '']
        out += [f"- {h['name']} ({h['person']}) · `{h['record']}` · {h['status']} · via {', '.join(h['ancestors'])}"
                for h in hints] or ['No hints from read records.']
    return '\n'.join(out)


def matrix_table(people, sources):
    out = ['| ' + ' | '.join(['Person', *(s['id'] for s in sources), 'other']) + ' |', '|' + '---|' * (len(sources) + 2)]
    ids = {s['id'] for s in sources}
    for person in people:
        cells = [person['cells'].get(s['id']) for s in sources]
        rest = [c for sid, c in person['cells'].items() if sid not in ids]
        cells.append(max(rest, key=lambda c: (RANK[c['outcome']], c['strength'])) if rest else None)
        marks = [('-' if s['id'] in person['not_applicable'] else '.') if not c else
                 MARK[c['outcome']] + str(c['strength']) + ('+F' if c['identified'] else '') + ('≠' if c['identity'] == 'other' else '') + ('!' if (c.get('availability') or {}).get('state') == 'stopped' else '') + ('~' if 'surname' in c['scope'] else '') + ('?' if c['person_basis'] == ['question'] else '')
                 for s, c in zip([*sources, {'id': 'other'}], cells)]
        out.append(f"| {person['name']} ({person['id']}) | " + ' | '.join(marks) + ' |')
    return out


def markdown_lines(view):
    def column(value):
        return str(value).replace('|', r'\|').replace('\n', ' ')

    out = ['# Family line fronts', '', f"Collateral research: `{view['collateral_mode']}`.", '',
           '| Line starts at | Farthest known ancestor | Open parent versions (weight) | Not searched | Weak | Collateral hints |',
           '|---|---|---|---:|---:|---:|']
    for line in view['lines']:
        versions = ', '.join(f"{v['label']} ({v['weight']:g})" for v in line['versions']) or '—'
        out.append('| ' + ' | '.join(map(column, [line['start']['name'], line['frontier']['name'], versions,
                   line['not_searched'], line['weak'], line['collateral_hints']])) + ' |')
    return '\n'.join(out)


@boundary('diagnostic')
def coverage(instance, *, person=None, queue=None, lines=False, save=False):
    """Read a coverage view; save always writes the matrix and complete queue."""
    data = collect(instance)
    view = matrix(data) if save or (not lines and not person and queue is None) else None
    if save:
        from familiar.instance.writer import mutate
        saved = view | {'recheck': recheck(data)}
        mutate(instance, {instance.path('state') / 'coverage.json': json.dumps(saved, ensure_ascii=False, indent=1).encode('utf-8')})
    if lines:
        front = line_front(data)
        return front, markdown_lines(front)
    if person:
        card = person_card(data, person)
        return card, markdown_card(card)
    if queue is not None:
        rows = recheck(data, queue)
        excluded = sum(bool(r) for r in data['not_applicable'].values())
        return rows, '\n'.join(markdown_queue(rows, f'Recheck queue: top {len(rows)}') +
                               ['', f'Not applicable by epoch/region: {excluded} cells (see matrix JSON totals).'])
    return view, markdown_matrix(view)
