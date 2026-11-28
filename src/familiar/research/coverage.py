# START_MODULE_CONTRACT: MOD-RESEARCH-COVERAGE
# PURPOSE: Recover source visits and their scope from journals and read records, keeping identity and plan completeness separate from model strength.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - only local journals, records and the tree are read; no network and no new step for the researcher [review: engine lead]
# - unrecorded outcomes and access gaps never count as zero; an incomplete zero never counts as controlled [review: engine lead]
# - strength comes from the research.search_strength setting; an executor no key names has strength 0 (unknown), never a guess [review: engine lead]
# - rows not in the ledger form are counted aside, not mixed into the matrix [review: engine lead]
# - catalogue epoch/place mismatches leave the queue, never erase recorded searches; unknown geography remains eligible [review: engine lead]
# - a known birth window disjoint from the source's birth cohort excludes a cell by epoch [review: engine lead]
# - the life assessment excludes living and possibly living people from the recheck queue, counted separately [review: engine lead]
# - collateral descendants stay outside the main planning denominator and queue; the line front derives from tree, versions and existing cells [review: engine lead]
# - line fronts follow parent hypotheses from 0.30 and match questions by surname or explicit people; designated lines and ancestors' siblings lead the recheck queue [review: engine lead]
# - explicit people survive dictionary mismatch; local identity work precedes repeat searches and stopped sources wait [review: engine lead]
# - local reviews assess record links only; no search strength, forms, yield or availability comes from them [review: engine lead]
# - a cell leaves recheck after three completed distinct passes without a new read record [review: engine lead]
# CHANGES_WITH:
# - MOD-SEARCH-LEDGER (the ledger form it reads)
# - docs/research-coverage.md
# :END_MODULE_CONTRACT
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import NamedTuple

from familiar.desk.search_volume import domain, name_key
from familiar.instance.gate import boundary, fixed_inputs
from familiar.tree.surnames import birth_names, decisions, gender_form

from .search_ledger import (METHOD, Resolver, Tree, in_ledger_form, infer_people, is_review, read_rows,
                            read_versions, row_digest, row_tokens, search_files)
from .coverage_evidence import references, review_links
from .search_variants import norm
from .coverage_context import (contains, episode_fit, form_metadata, life_window, missing_forms, person_text,
                               planning_windows, record_visits, row_people, script_of, text)
from .search_variants import form_data
from .coverage_quality import availability, query_issues
from .search_plays import PlaySettings, links_to_living, query_label, query_places, source_classes

GAP_STATES = {'access-gap', 'refused', 'not_ready', 'app_error', 'help-stop', 'coverage-gap'}
RANK = {'none': 0, 'gap': 1, 'unrecorded': 2, 'query-dubious': 2.5, 'zero-uncontrolled': 3, 'zero-controlled': 4, 'read': 4.5, 'found': 5}
MARK = {'found': 'R', 'read': 'D', 'zero-controlled': 'Z', 'zero-uncontrolled': 'z', 'gap': '!', 'unrecorded': '?', 'query-dubious': 'Q', 'none': '.'}
REASON = {'identity-unestablished': 15, 'identity-conflict': 16, 'source-stopped': 0, 'query-dubious': 4, 'not-searched': 5, 'access-gap': 4, 'outcome-unrecorded': 4, 'weak-only': 4, 'zero-without-control': 3, 'forms-missing': 2, 'forms-unassessed': 2, 'source-grown': 1}
OPEN_EXCLUSIONS = {'accepted', 'closed', 'resolved', 'settled', 'rejected', 'superseded'}
CLOSED_OPTIONS = OPEN_EXCLUSIONS | {'accepted_evidence', 'firm', 'refuted', 'discarded', 'dropped', 'ruled-out'}


class SearchLine(NamedTuple):
    chain: list[str]
    surname: str
    forms: set[str]
    main_order: int
    secondary: bool
    focus_order: int


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
            registry.resolve_setting('research.collateral').value,
            registry.resolve_setting('research.main_lines').value)


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


def journal_read_places(row, kind, series):
    from .search_map import row_readings

    if kind in {'gap', 'query-dubious'}:
        return set()
    scope = row.get('coverage')
    if not isinstance(scope, dict):
        return set()
    readings = {series[sid] for sid, years, depth, _ in row_readings(row)
                if sid in series and years and depth}
    if readings:
        return readings
    read = scope.get('read')
    if type(read) not in (int, float) or read <= 0:
        return set()
    if isinstance(place := scope.get('place'), str) and place.strip():
        return {place.strip()}
    places = {p.strip() for p in query_places(row) if p.strip()}
    return places if len(places) == 1 else set()


@fixed_inputs()
def collect(instance, *, for_plan=False):
    """The journal as person-by-source cells, plus what could not be placed."""
    tree, resolver, versions = Tree(instance), Resolver(instance), read_versions(instance)
    from familiar.tree.birth_guess import apply as birth_guess
    birth_guess(instance, tree.graph, host_private=True)
    table, threshold, mode, configured_lines = settings(instance)
    prefs = PlaySettings(instance.config.get('research', {}))
    main_lines = [keys for name in configured_lines if (keys := surname_keys(name, instance.source_language))]
    focus_lines = [surname_keys(name, instance.source_language) for name in prefs.focus]
    cells, sources, legacy, no_people, unknown, titles, no_source = {}, {}, 0, 0, set(), {}, 0
    found_by_source, planning_events, source_access, access_journals = {}, {}, {}, {}
    reviews, observations, read_acts = {}, [], set()
    from .search_map import read_series
    series_places = {row['id']: row['place'] for row in read_series(instance)[1] or []}
    untied, place_searches, place_records = Counter(), {}, []
    place_search_rows = 0
    for path in search_files(instance):
        rows, _ = read_rows(path)
        for number, row in enumerate(rows or []):
            if not isinstance(row, dict):
                continue
            if not in_ledger_form(row):
                legacy += 1
                if for_plan and not is_review(row):
                    people, _ = infer_people(tree, versions, row)
                    sid = resolver.row_source(row)
                    observations.append({'source': sid, 'people': people, 'kind': outcome(row), 'row': row, 'cells': []})
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
                source_text = str(row.get('source'))
                if METHOD.search(source_text) or not row.get('source'):
                    if for_plan:
                        observations.append({'source': None, 'people': row['people'], 'kind': outcome(row), 'row': row, 'cells': []})
                    no_source += 1
                    continue
                sid = '~' + (domain(source_text) or name_key(source_text))[:60]
                titles.setdefault(sid, source_text[:80])
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
            if for_plan:
                observations.append({'source': sid, 'people': people, 'kind': kind, 'row': row,
                                     'cells': [(p['id'], sid) for pid in people if (p := tree.person(pid))]})
            no_people += not bool(people)
            if not people:
                untied[kind] += 1
                if places := journal_read_places(row, kind, series_places):
                    place_search_rows += 1
                    for place in places:
                        place_searches.setdefault(place, Counter())[sid] += 1
                continue
            words = row_tokens(row)
            forms = row['coverage'].get('forms') if isinstance(row.get('coverage'), dict) else None
            read = row['coverage'].get('read') if isinstance(row.get('coverage'), dict) else None
            completed = kind == 'found' or kind.startswith('zero-') and type(read) in (int, float) and read > 0
            attempt = (row.get('id_as_written') or row.get('id') or row_digest(row)) if completed else None
            play, _ = query_label(row, source_classes(sid, resolver.catalog.sources.get(sid, {})))
            saved = references(row.get('saved')) if completed else set()
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
                if play:
                    cell['plays'].add(play)
                if attempt:
                    cell['attempts'].setdefault(attempt, (str(row.get('at') or ''), path, number, saved))
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
                            known = tree.people[pid]['surnames' if key == 'surname' else 'givens']
                            cell['planned'].update(f for f in values if isinstance(f, str)
                                                   and norm(form_data(f)['text']) in known)
                if at:
                    cell['first'] = min(at, cell['first'] or at)
                    cell['last'] = max(at, cell['last'] or at)
                for form in forms if isinstance(forms, list) else [forms] if isinstance(forms, str) else []:
                    if isinstance(form, str) and form.strip():
                        cell['forms'][form.strip()[:80]] = True
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
        if scope := visit['place_scope']:
            place_records.append(scope | {'record': visit['record'], 'source': visit['source']})
        if not visit['source']:
            continue
        if for_plan and visit['act_names']:
            read_acts.update(pid for pid, link in visit['links'].items() if link['status'] == 'same')
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
            cell['record_events'].append((str(visit['at'] or ''), visit['references']))
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
    for cell in cells.values():
        cell['ceiling'] = stalled_passes(cell)
    named = {pid for pid, _ in cells} | {p['id'] for v in versions.values() for ident in v['people']
                                       if (p := tree.person(ident))}
    from familiar.tree.builder import read_json
    metadata = read_json(instance.path('tree_metadata'), {})
    root = (metadata.get('root') or tree.graph.get('root')
            or next(iter(tree.people), None))
    root = tree.aliases.get(root, root)
    distance = distances(tree.graph, root)
    lines, collateral, line_weights, ancestor_siblings = family_lines(tree.graph, root)
    main = {pid for line in lines for pid in line}
    side = sorted(collateral) if mode == 'full' else []
    data = {'tree': tree, 'resolver': resolver, 'versions': versions, 'table': table, 'threshold': threshold,
            'cells': cells, 'sources': sources, 'legacy': legacy, 'no_people': no_people, 'no_source': no_source, 'unknown': sorted(unknown),
            'side': side, 'named': named, 'lines': lines,
            'collateral': collateral, 'collateral_mode': mode, 'line_weights': line_weights,
            'main_lines': main_lines, 'focus_lines': focus_lines, 'play_settings': prefs,
            'ancestor_siblings': ancestor_siblings, 'surname_forms': decisions(metadata), 'language': instance.source_language,
            'observations': observations, 'read_acts': read_acts,
            'yield': found_by_source, 'titles': titles, 'distance': distance,
            'form_metadata': form_metadata(instance), 'planning_events': planning_events, 'source_access': source_access}
    data.update(untied=untied, place_searches=place_searches, place_search_rows=place_search_rows,
                place_records=place_records)
    queue_lines = {}
    if main_lines or focus_lines or prefs.overrides:
        for line in selected_lines(data):
            for pid in line_members(data, line.chain):
                queue_lines.setdefault(pid, line)
        if main_lines:
            main.update(pid for pid, line in queue_lines.items() if not line.secondary)
    focus = (main | named) - collateral.keys()
    data.update(focus=sorted(focus), queue_lines=queue_lines)
    # Each FamilySearch channel is independently eligible even if only one has a recorded visit.
    if any(s.startswith('familysearch') for s in sources):
        for sid in ('familysearch-tree', 'familysearch-records', 'familysearch-fulltext'):
            if sid in resolver.catalog.sources:
                sources.setdefault(sid, {'rows': 0, 'people': set()})
    contexts = {pid: planning_context(data, pid) for pid in [*focus, *side]}
    data['contexts'] = contexts
    data['not_applicable'] = {(pid, sid): applicability(data, pid, sid, context)
                              for pid, context in contexts.items() for sid in sources}
    return data


def new_cell():
    return {'rank': 0, 'passes': 0, 'first': None, 'last': None, 'forms': {}, 'words': set(),
            'who': {}, 'strength': 0, 'basis': set(), 'planned': set(), 'scopes': set(),
            'records': [], 'record_links': [], 'identified': False, 'controls': set(), 'phrases': set(),
            'dictionary_mismatches': [], 'query_issues': [], 'query_scripts': set(), 'latest_refusal': None,
            'attempts': {}, 'record_events': [], 'plays': set()}


def stalled_passes(cell):
    """Count completed, distinct searches since the last newly saved record."""
    attempts = cell['attempts'].values()
    new_records = []
    for read_at, refs in cell['record_events']:
        linked = [(at, journal, number) for at, journal, number, saved in attempts if at and refs & saved]
        if linked:
            # The earliest row naming this record is enough to date its presence.
            first = min(linked)
            if not read_at or first[0][:10] <= read_at[:10]:
                new_records.append(first)
                continue
        if read_at:
            new_records.append((read_at, None, None))

    def after(pass_at, journal, number, record):
        at, other_journal, other_number = record
        if pass_at[:10] != at[:10]:
            return pass_at[:10] > at[:10]
        if len(pass_at) > 10 and len(at) > 10 and pass_at != at:
            return pass_at > at
        # A day-only date does not order two independent journals.
        return journal == other_journal and number > other_number

    return sum(all(after(at, journal, number, record) for record in new_records)
               for at, journal, number, _ in attempts)


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
    fathers, mothers = defaultdict(dict), defaultdict(dict)
    excluded = {'conflict', 'rejected', 'disproved'}
    edges = graph.get('edges', [])
    explicit = {(e.get('child'), e.get('parent')) for e in edges}
    family_roles = {}
    for family in graph.get('families', []):
        if family.get('status') in excluded | {'hypothesis'}:
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
                    pair = child, parent
                    family_roles[pair] = role
                    if pair not in explicit:
                        role[child][parent] = None
                        children[parent].add(child)

    # Parent edges can stand on their own. A probable edge retains its weight.
    for edge in edges:
        parent, child = edge.get('parent'), edge.get('child')
        status = edge.get('status')
        if parent not in people or child not in people or parent == child or status in excluded:
            continue
        weight = edge.get('weight') if status == 'hypothesis' else None
        if status == 'hypothesis' and (type(weight) not in (int, float) or not .30 <= weight <= 1):
            continue
        roles = family_roles.get((child, parent))
        if roles is None:
            role = edge.get('role')
            is_father = role in {'father', 'отец', 'ojciec'} or (
                role not in {'mother', 'мать', 'matka'} and str(people[parent].get('sex')).lower() == 'm')
            roles = fathers if is_father else mothers
        parents = roles[child]
        if parent not in parents or (parents[parent] is not None and (weight is None or weight > parents[parent])):
            parents[parent] = weight
        children[parent].add(child)

    def ranked(parents):
        return sorted(parents, key=lambda pid: (parents[pid] is not None, -(parents[pid] or 0), pid))

    starts = [(p, None) for p in [root, *sorted(spouses[root] - {root})]] if root in people else []
    lines, line_weights, ancestors, started = [], {}, set(), set()
    for start, weight in starts:
        if start in started:
            continue
        started.add(start)
        chain, weights, pid = [], [], start
        while pid and pid not in chain:
            chain.append(pid)
            weights.append(weight)
            paternal, maternal = ranked(fathers[pid]), sorted(mothers[pid])
            starts.extend((mother, mothers[pid][mother]) for mother in maternal)
            starts.extend((father, fathers[pid][father]) for father in paternal[1:])
            ancestors.update([*paternal, *maternal])
            pid, weight = (paternal[0], fathers[pid][paternal[0]]) if paternal else (None, None)
        lines.append(chain)
        line_weights[start] = weights

    main = {pid for chain in lines for pid in chain}
    for pid in main:
        for parent in fathers[pid].keys() | mothers[pid].keys():
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
    return (lines, {pid: anchors for pid, anchors in collateral.items() if pid not in primary_siblings},
            line_weights, {pid: siblings[pid] for pid in ancestors})


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
    return planning_windows(person), raw, countries, regions


def applicability(data, pid, sid, context=None):
    """Planning fit only: generous life window; unknown dates/places never exclude a source."""
    source = data['resolver'].catalog.sources.get(sid, {})
    ((born_from, born_to), (lower, upper)), raw, countries, regions = context or planning_context(data, pid)
    years = source.get('years', [])
    born = source.get('born', [])
    reasons = []
    person = data['tree'].graph['people'][pid]
    guess = person.get('birth_guess') or person.get('birthGuess') or {}
    birth = guess.get('year') if isinstance(guess, dict) else guess
    # The uncertainty envelope remains useful for overlap, but not as a reason
    # to prioritize a person who was already about a century old.
    birth = birth if isinstance(birth, (int, float)) else lower
    outside_cohort = len(born) == 2 and born_from is not None and (born_from > born[1] or born_to < born[0])
    outside_life = len(years) == 2 and ((lower is not None and lower > years[1]) or (upper is not None and upper < years[0]))
    if outside_cohort or outside_life:
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
            'ceiling': cell['ceiling'] >= 3, 'passes_without_new_records': cell['ceiling'],
            'not_applicable': data['not_applicable'].get((pid, sid), []),
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


def recheck(data, limit=None, *, line=None):
    """Cells worth another look, most useful first within each search scope."""
    tree, threshold = data['tree'], data['threshold']
    catalog = data['resolver'].catalog.sources
    prefs = data['play_settings']
    selected = {}
    if line is not None:
        for match in selected_lines(data, line):
            for pid in line_members(data, match.chain):
                selected.setdefault(pid, match)
    queue_lines = selected if line is not None else data['queue_lines']
    choice_cache = {}
    linked = None
    people = [pid for pid in [*data['focus'], *data['side']] if line is None or pid in selected]
    open_people = {p['id'] for v in data['versions'].values()
                   if v.get('status', v.get('state')) not in OPEN_EXCLUSIONS
                   for ident in v['people'] if (p := tree.person(ident))}
    queue = []
    for pid, sid in eligible_cells(data, people):
        cell = data['cells'].get((pid, sid))
        if cell and cell['ceiling'] >= 3:
            continue
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
        known = cell['plays'] if cell else set()
        if action != 'link-record' and 'deep-inventories' in known:
            if linked is None:
                linked = links_to_living(tree.graph)[1]
            if pid not in linked:
                known = known - {'deep-inventories'}
                if not known:
                    continue
        play = None
        order = 0
        if prefs.overrides and action != 'link-record':
            match = queue_lines.get(pid)
            key = match.chain[0] if match else None
            if key not in choice_cache:
                choice_cache[key] = prefs.choices(match.forms if match else set(),
                                                  lambda name: surname_keys(name, data['language']))
            choices = choice_cache[key]
            classes = set(source_classes(sid, catalog.get(sid, {})).get('classes', []))
            if known:
                choices = [choice for choice in choices if choice[2]['id'] in known]
            else:
                choices = [choice for choice in choices if classes.intersection(choice[2]['classes'])
                           and choice[2]['id'] not in {'ask-family', 'archive-letters', 'deep-inventories', 'place-nest',
                                                       'neighbors-godparents', 'household-fingerprint'}]
                direct = {'cemetery': 'cemeteries', 'forum': 'forums'}
                if direct.keys() & classes:
                    choices = [choice for choice in choices if choice[2]['id'] in
                               {direct[cls] for cls in direct.keys() & classes}]
            if choices:
                enabled = [choice for choice in choices if choice[1]]
                if not enabled:
                    continue
                order, _, play = enabled[0]
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
        queue.append((order, {'person': pid, 'name': tree.people[pid]['name'], 'source': sid, 'title': title(data, sid),
                      'reasons': reasons, 'score': score, 'outcome': kind, 'strength': view['strength'],
                      'last': view['last'], 'missing_forms': view['missing_forms'], 'action': action,
                      'availability': view['availability'], 'record_links': view['record_links'],
                      'latest_refusal': view['latest_refusal'],
                      'query_issues': view['query_issues']} | ({'play': play['id']} if play else {})))
    def priority(entry):
        order, item = entry
        pid = item['person']
        line = queue_lines.get(pid)
        focus = line.focus_order if line else len(data['focus_lines'])
        return (focus, pid in data['collateral'], line is None or line.secondary,
                prefs.overrides and item['action'] != 'link-record', order, -item['score'], pid, item['source'])

    queue.sort(key=priority)
    rows = []
    for _, item in queue:
        if item['person'] in queue_lines:
            surname = queue_lines[item['person']].surname
            if surname:
                item['line'] = surname
        rows.append(item)
    return rows[:limit] if limit else rows


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


def untied_journal(data):
    return {'rows': data['no_people'], 'outcomes': dict(data['untied']),
            'rows_with_place_reading': data['place_search_rows']}


def place_coverage(data, *, includes=None, includes_record=None):
    places = {place: {'place': place, 'journal_rows': dict(rows), 'records': []}
              for place, rows in data['place_searches'].items() if includes is None or includes(place)}
    for record in data['place_records']:
        place = record['place']
        if includes_record is None or includes_record(record):
            places.setdefault(place, {'place': place, 'journal_rows': {}, 'records': []})['records'].append(record)
    return sorted(places.values(), key=lambda p: p['place'].casefold())


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
            'sources': sources, 'people': main['people'], 'collateral': collateral,
            'place_coverage': place_coverage(data), 'untied_journal': untied_journal(data)}


def line_surname(surname, language):
    """Use the regular Russian family plural where the ending determines it."""
    masculine = gender_form(surname, 'm', language)
    if language == 'ru':
        if masculine.endswith(('ский', 'цкий', 'ской', 'цкой')):
            return masculine[:-2] + 'ие'
        if masculine.endswith(('ов', 'ев', 'ёв', 'ин', 'ын')):
            return masculine + 'ы'
    return masculine


def surname_keys(surname, language):
    if not isinstance(surname, str) or not (key := surname.strip().casefold()):
        return set()
    return {key, gender_form(key, 'm', language), gender_form(key, 'f', language), line_surname(key, language)}


def line_names(data):
    """Resolve chain surnames and their position in the configured main lines."""
    tree, language = data['tree'], data['language']
    own_names = birth_names(tree.graph, language)
    clans = {row['id']: row for row in data['surname_forms']}
    main_lines, focus_lines = data['main_lines'], data['focus_lines']
    for chain in data['lines']:
        surname, forms = '', set()
        for pid in chain:
            display = tree.graph['people'][pid].get('surnameDisplay', {})
            clan = clans.get(display.get('clan'))
            surname = clan['form'] if clan else next((n['surname'] for n in own_names[pid] if n.get('surname')), '')
            if surname:
                for form in [surname, *(clan['variants'] if clan else [])]:
                    forms.update(surname_keys(form, language))
                break
        order = next((i for i, keys in enumerate(main_lines) if keys & forms), len(main_lines))
        focus = next((i for i, keys in enumerate(focus_lines) if keys & forms), len(focus_lines))
        yield SearchLine(chain, line_surname(surname, language), forms, order,
                         bool(main_lines) and order == len(main_lines), focus)


def selected_lines(data, name=None):
    lines = sorted(line_names(data), key=lambda line: (line.focus_order, line.main_order))
    if name is None:
        return lines
    keys = surname_keys(name, data['language'])
    matches = [line for line in lines if line.chain[0] == name or keys & line.forms]
    if not matches:
        names = {norm(key) for key in keys}
        variants = names.union(*(data['tree'].surname_groups.get(key, ()) for key in names))
        matches = [line for line in lines if any(norm(form) in variants for form in line.forms)]
    if not matches:
        raise ValueError(f'unknown family line: {name}; list names with research coverage --lines')
    return matches


def line_members(data, chain):
    return set(chain).union(*(data['ancestor_siblings'].get(pid, ()) for pid in chain))


def line_front(data):
    """Derive frontier questions and planning gaps without adding ledger rows."""
    tree, language = data['tree'], data['language']
    questions = []
    for ident, question in data['versions'].items():
        if question.get('status', question.get('state')) in OPEN_EXCLUSIONS:
            continue
        subjects = sorted({tree.aliases.get(pid, pid) for pid in question['people']})
        weights = [weight for option in question.get('versions') or []
                   if isinstance(option, dict) and option.get('status', option.get('state')) not in CLOSED_OPTIONS
                   and type(weight := option.get('weight')) in (int, float) and 0 <= weight <= 1]
        if weights:
            line = question.get('line')
            questions.append((line, surname_keys(line, language),
                              {'question': ident, 'label': question.get('title') or ident,
                               'weight': max(weights), 'people': subjects}))
    hints = collateral_hints(data)
    lines = []
    for chain, surname, forms, order, secondary, focus in line_names(data):
        gaps = Counter()
        for key in eligible_cells(data, chain):
            cell = data['cells'].get(key)
            if cell and cell['ceiling'] >= 3:
                continue
            if not cell or cell['rank'] == RANK['none']:
                gaps['not_searched'] += 1
            elif cell['rank'] >= RANK['zero-uncontrolled'] and cell['strength'] < data['threshold']:
                gaps['weak'] += 1
        start, end = chain[0], chain[-1]
        members = set(chain)
        versions = [v for line, keys, v in questions if (bool(keys & forms) if line else
                                                          not members.isdisjoint(v['people']))]
        versions.sort(key=lambda v: -v['weight'])
        steps = [{'id': pid, 'name': tree.people[pid]['name'], 'weight': weight}
                 for pid, weight in zip(chain, data['line_weights'][start], strict=True)]
        line = {'start': {'id': start, 'name': tree.people[start]['name']},
                'frontier': {'id': end, 'name': tree.people[end]['name']}, 'people': chain, 'chain': steps,
                'surname': surname, 'secondary': secondary,
                'versions': versions[:3], 'not_searched': gaps['not_searched'], 'weak': gaps['weak'],
                'collateral_hints': sum(not members.isdisjoint(h['ancestors']) for h in hints)}
        if data['main_lines']:
            line['living_or_possibly_living'] = len(chain) - sum(1 for _ in planning_people(data, chain))
        lines.append((focus, order, line))

    def priority(entry):
        focus, order, line = entry
        weight = line['versions'][0]['weight'] if line['versions'] else 0
        return (focus, order, -(line['not_searched'] + line['weak']) * (1 + weight), -weight, line['start']['id'])

    return {'schema': 1, 'collateral_mode': data['collateral_mode'],
            'lines': [line for _, _, line in sorted(lines, key=priority)]}


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
        if s['ceiling']:
            notes.append(f"ceiling: {s['passes_without_new_records']} passes without a new record")
        if s['not_applicable']:
            notes.append('not applicable: ' + ', '.join(s['not_applicable']))
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
        person = f"{q['name']} ({q['person']})"
        if line := q.get('line'):
            label = line.replace('|', r'\|').replace('\n', ' ')
            person += f' · {label}'
        out.append(f"| {n} | {person} | {q['source']} | {q.get('action', 'search')}: {', '.join(q['reasons'])} | {now} |")
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
           '? = the person was inferred from the question only, not from the names searched. ⊣ = repeat ceiling.', '']
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
                 MARK[c['outcome']] + str(c['strength']) + ('+F' if c['identified'] else '') + ('≠' if c['identity'] == 'other' else '') + ('!' if (c.get('availability') or {}).get('state') == 'stopped' else '') + ('~' if 'surname' in c['scope'] else '') + ('?' if c['person_basis'] == ['question'] else '') + ('⊣' if c['ceiling'] else '')
                 for s, c in zip([*sources, {'id': 'other'}], cells)]
        out.append(f"| {person['name']} ({person['id']}) | " + ' | '.join(marks) + ' |')
    return out


def format_line_chain(chain, decimal='.'):
    return ' → '.join(step['name'] + (' ≈' + format(step['weight'], 'g').replace('.', decimal)
                                      if step['weight'] is not None else '') for step in chain)


def markdown_lines(view, language='en'):
    def column(value):
        return str(value).replace('|', r'\|').replace('\n', ' ')

    secondary = {'ru': 'второй план', 'pl': 'drugi plan'}.get(language, 'secondary')
    decimal = ',' if language in {'ru', 'pl'} else '.'
    out = ['# Family line fronts', '', f"Collateral research: `{view['collateral_mode']}`.", '',
           '| Line | Chain to farthest ancestor | Open questions (weight) | Not searched | Weak | Collateral hints |',
           '|---|---|---|---:|---:|---:|']
    if view['lines'] and 'living_or_possibly_living' in view['lines'][0]:
        excluded = {'ru': 'Вне очереди: живые или статус неизвестен',
                    'pl': 'Poza kolejką: żyjący lub o nieznanym statusie'}
        out[-2] += f" {excluded.get(language, 'Outside queue: living or unknown status')} |"
        out[-1] += '---:|'
    for line in view['lines']:
        versions = ', '.join(f"{v['label']} ({v['weight']:g})" for v in line['versions']) or '—'
        surname = line['surname'] or '—'
        if line['secondary']:
            surname += f' ({secondary})'
        cells = [surname, format_line_chain(line['chain'], decimal), versions,
                 line['not_searched'], line['weak'], line['collateral_hints']]
        if 'living_or_possibly_living' in line:
            cells.append(line['living_or_possibly_living'])
        out.append('| ' + ' | '.join(map(column, cells)) + ' |')
    return '\n'.join(out)


def home_coverage(instance, data, name):
    from . import access_ledger as access
    from .research_plan import place_entries
    from .search_map import leading_places, line_groups, place_match

    data['place_entries'] = place_entries(instance)
    _, ledger, _ = access.read(instance)
    words, lang = access.words_for(instance), data['language']
    lines = []
    for group in line_groups(selected_lines(data, name)):
        line = group[0]
        places, known = {}, set()
        forms = set().union(*(one.forms for one in group))
        for one in group:
            members = line_members(data, one.chain)
            matched = access.line_places(data, ledger, one, members)
            places.update((p['place'], p) for p in matched)
            if name:
                known.update(access.line_place_names(data, members, leading_places(data, one, members)))
        books = [dict(row, place=p['place']) for p in places.values() for row in access.in_order(p['books'])
                 if row['state'] == 'home' and not access.fully_read(row)]
        label = line.surname or line.chain[0]
        entry = {'line': label, 'start': line.chain[0], 'open_cells': len(books)}
        if name:
            known.update(places)

            def includes(place):
                return any(place_match(place, p) for p in known)

            entry.update(books=books, place_coverage=place_coverage(data, includes=includes,
                includes_record=lambda r: includes(r['place']) or bool(surname_keys(r['surname'], lang) & forms)))
        lines.append(entry)
    view = {'schema': 1, 'lines': lines, 'untied_journal': untied_journal(data)}
    if not name:
        view['place_coverage'] = place_coverage(data)
    return view, markdown_home_coverage(view, words, lang, detail=bool(name))


def markdown_home_coverage(view, words, language, *, detail):
    ru = language == 'ru'
    out = ['# Из дома: книги и источники с открытым чтением' if ru else '# Coverage: open from home', '']
    for line in view['lines']:
        out.append(f"{'##' if detail else '-'} {line['line']} · {line['open_cells']}")
        if not detail:
            continue
        for book in line['books']:
            out.append(f"- [{book['id']}] {book['place']} · {access_title(book, words, language)}")
        if not line['books']:
            out.append('В учёте нет открытых строк.' if ru else 'No open entries in the access ledger.')
        out += markdown_place_coverage(line['place_coverage'], language, detail=True)
        out.append('')
    if not detail:
        out += ['', 'Одна строка учёта — одна ячейка. Подробнее: research coverage --line ИМЯ.' if ru else
                'Each access-ledger entry is one cell. Details: research coverage --line NAME.']
        out += markdown_place_coverage(view['place_coverage'], language, detail=False)
    return '\n'.join([*out, '', journal_summary(view['untied_journal'], ru)])


def access_title(book, words, language):
    from .access_ledger import say, state_words, title

    parts = [f'{title(book, words, language)} — {state_words(book, words, language)}', say(book.get('look_for'), language)]
    return ' · '.join(filter(None, parts))


def markdown_place_coverage(places, language, *, detail):
    if not places:
        return []
    ru = language == 'ru'
    out = ['', '### Чтение по месту' if ru else '### Place readings']
    for place in places:
        searches, records = sum(place['journal_rows'].values()), len(place['records'])
        if not detail and not records:
            continue
        label = f'{searches} строк журнала, {records} записей' if ru else f'{searches} journal rows, {records} records'
        out.append(f"- {place['place']} · {label}")
        if detail:
            out.extend(f"  - {record['surname']} · `{record['record']}`" for record in place['records'])
    return out if len(out) > 2 else []


def journal_summary(journal, ru):
    total, placed = journal['rows'], journal['rows_with_place_reading']
    gaps = journal['outcomes'].get('gap', 0)
    other = total - placed - gaps
    if ru:
        return (f'Журнал: {total} строк без привязки к человеку. Из них {placed} дают чтение в указанном месте. '
                f'{gaps} отмечают разрыв доступа или охвата. Ещё {other} — общие поиски или строки без места либо объёма чтения. '
                'Охват целой книги берётся из учёта доступа.')
    return (f'Journal: {total} rows without a tree person. Of these, {placed} document reading at a named place. '
            f'{gaps} record an access or coverage gap. Another {other} are broad searches or lack a place or reading scope. '
            'Book completion comes from the access ledger.')


@boundary('diagnostic')
def coverage(instance, *, person=None, queue=None, lines=False, save=False, line=None, family=False):
    """Read a coverage view; save always writes the matrix and complete queue."""
    data = collect(instance)
    view = matrix(data) if save or family else None
    if save:
        from familiar.instance.writer import mutate
        saved = view | {'recheck': recheck(data)}
        mutate(instance, {instance.path('state') / 'coverage.json': json.dumps(saved, ensure_ascii=False, indent=1).encode('utf-8')})
    if lines:
        front = line_front(data)
        return front, markdown_lines(front, data['language'])
    if person:
        card = person_card(data, person)
        return card, markdown_card(card)
    if queue is not None:
        rows = recheck(data, queue, line=line)
        excluded = sum(bool(r) for r in data['not_applicable'].values())
        return rows, '\n'.join(markdown_queue(rows, f'Recheck queue: top {len(rows)}') +
                               ['', f'Not applicable by epoch/region: {excluded} cells (see matrix JSON totals).'])
    if family:
        return view, '\n'.join([markdown_matrix(view), '', journal_summary(view['untied_journal'], False),
                               *markdown_place_coverage(view['place_coverage'], data['language'], detail=True)])
    return home_coverage(instance, data, line)
