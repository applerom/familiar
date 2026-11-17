# START_MODULE_CONTRACT: MOD-PERSON-CARD
# PURPOSE: Give a story author one bounded entrance to a person's family, competing identities and scattered literal observations.
# PRD_REF: docs/PRD.md#PERSON-CARD
# INVARIANTS:
# - retrieval never merges namesakes, assigns weights or promotes a record match to kinship [review: engine lead]
# - living and unknown canonical people expose only names and kinship; closures and budget omissions say why [review: engine lead]
# - identical literal observations share locators and retain import envelopes while distinct readings survive separately [review: engine lead]
# - canonical JSON and JSONL collections both contribute to the coverage manifest [review: engine lead]
# CHANGES_WITH:
# - MOD-TREE-BUILDER (private attributed graph and life assessment)
# - MOD-FAMILY-GATE (diagnostic boundary, never a reader publication)
# - docs/PRD.md#PERSON-CARD
# :END_MODULE_CONTRACT
import json
import re
import tomllib
from collections import Counter
from functools import lru_cache

from familiar.instance.gate import boundary
from familiar.tree.builder import _build, read_json

from .card_context import (
    compact_metadata,
    observation,
    references,
    summaries,
    table_view,
    text_fragments,
    value_tables,
)
from .card_sources import collect, copies, fold, matches


def configuration(instance, catalog=None):
    config = instance.config
    if catalog:
        with catalog.open('rb') as stream:
            config = tomllib.load(stream)
    research = config.get('research', {})
    if not isinstance(research, dict):
        raise TypeError('research must be a table')
    config = research.get('person_card', {})
    if not isinstance(config, dict) or set(config) - {'sources', 'aliases'}:
        raise ValueError('research.person_card accepts sources and aliases')
    if not isinstance(config.get('sources', []), list) or not isinstance(config.get('aliases', {}), dict):
        raise TypeError('person-card sources must be an array and aliases a table')
    if not all(isinstance(k, str) and isinstance(v, list) and all(isinstance(s, str) and s.strip() for s in v) for k, v in config.get('aliases', {}).items()):
        raise TypeError('person-card aliases must map names or IDs to arrays of spellings')
    ids = [source.get('id') for source in config.get('sources', []) if isinstance(source, dict)]
    if len(ids) != len(set(ids)):
        raise ValueError('person-card source ids must be unique')
    return config


def _names(person):
    values = [person.get('name', '')]
    values += [n.get('display') or ' '.join(filter(None, [n.get('given'), n.get('surname')])) for n in person.get('names', [])]
    return list(dict.fromkeys(n.split(' ·')[0] for n in values if n.strip()))


def _name_projection(person):
    return {'id': person.get('id'), 'name': person.get('name', '').split(' ·')[0],
            'names': [{k: n[k].split(' ·')[0] for k in ('given', 'surname', 'patronymic', 'display') if isinstance(n.get(k), str)} for n in person.get('names', [])]}


def _neighbours(graph, selected):
    relatives = {}
    def add(pid, role, basis):
        if pid and pid not in selected:
            relatives.setdefault(pid, []).append({'role': role, 'basis': {k: basis[k] for k in ('id', 'from', 'to', 'parent', 'child', 'type', 'status', 'confidence', 'weight', 'sources', 'provenance') if k in basis}})
    edges = graph.get('edges', [])
    parents = set()
    for edge in edges:
        parent, child = edge.get('parent', edge.get('from')), edge.get('child', edge.get('to'))
        if child in selected:
            add(parent, 'parent', edge)
            parents.add(parent)
        if parent in selected:
            add(child, 'child', edge)
    for edge in edges:
        if edge.get('parent', edge.get('from')) in parents:
            add(edge.get('child', edge.get('to')), 'sibling or half-sibling; conditional on both parent links', edge)
    for family in graph.get('families', []):
        partners = {family.get('husband'), family.get('wife')} - {None}
        children = set(family.get('children', []))
        if partners & selected:
            for pid in partners:
                add(pid, 'spouse', family)
            for pid in children:
                add(pid, 'child', family)
        if children & selected:
            for pid in partners:
                add(pid, 'parent', family)
            for pid in children:
                add(pid, 'sibling or half-sibling; derived from this family record', family)
    return relatives


def _protected(instance, graph):
    privacy = read_json(instance.path('privacy'), {})
    explicit = {r if isinstance(r, str) else r['id'] for r in privacy.get('living', [])}
    protected = {}
    for pid, person in graph['people'].items():
        if person.get('life_assessment', {}).get('status') == 'living':
            explicit.add(pid)
        if person.get('life_assessment', {}).get('status') != 'dead' or pid in explicit:
            protected[pid] = _names(person)
    return protected, explicit


def _closed_terms(instance):
    from familiar.rules.cascade import Registry
    from familiar.rules.roles import method_root
    registry = Registry(method_root() / 'rules', instance)
    terms = []
    for key in ('privacy.closed_topics_file', 'privacy.present_day_politics_file'):
        ref = registry.resolve_setting(key).value
        if ref:
            path = instance._inside(ref)
            text = path.read_text(encoding='utf-8-sig')
            data = tomllib.loads(text) if path.suffix == '.toml' else json.loads(text)
            rows = data.get('terms', data.get('closed_topics')) if isinstance(data, dict) else None
            if not isinstance(rows, list):
                raise TypeError(f'{key}: expected terms or closed_topics array')
            for row in rows:
                term = row.get('term') if isinstance(row, dict) else row
                if not isinstance(term, str) or not term.strip():
                    raise ValueError(f'{key}: terms must be nonempty strings')
                terms.append(term)
    return terms


@lru_cache(maxsize=16)
def _protected_ids(ids):
    return re.compile(r'(?<![\w-])(?:' + '|'.join(re.escape(pid) for pid in ids) + r')(?![\w-])') if ids else None


def _living_record(value):
    if isinstance(value, dict):
        flag = value.get('privacy')
        return (isinstance(flag, str) and flag in {'living', 'living-possible'}) or any(_living_record(v) for v in value.values())
    return any(_living_record(v) for v in value) if isinstance(value, list) else False


def _closure(row, protected, explicit, terms):
    data = row['data']
    if _living_record([data, row.get('container_context')]):
        return 'record classified living or possibly living; name and kinship only'
    checked = [data, row.get('container_context')]
    raw = json.dumps(checked, ensure_ascii=False)
    ids = _protected_ids(tuple(sorted(protected)))
    if ids and ids.search(raw):
        return 'contains a protected canonical ID; inspect privately'
    protected_terms = [n for pid, names in protected.items() for n in names if pid in explicit and len(fold(n).split()) > 1]
    # Unknown *name* matches are a review cue, not a subject identity decision.
    if matches(checked, protected_terms):
        return 'contains a known living name; inspect privately'
    if isinstance(data, dict) and isinstance(data.get('literal'), str) and re.search(r'\(\s*жив(?:ой|ая|ые|ых)\b|\bжив(?:ой|ая|ые|ых)\s*[,;:—–-]|\bliving(?:-| )possible\b|\bis living\b', data['literal'], re.IGNORECASE):
        return 'living-status cue in prose; inspect privately before exposing details'
    if any(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', raw, re.IGNORECASE) for term in terms):
        return 'closed-topic cue; inspect privately'
    if not row.pop('_historical', False):
        return 'legacy subjects unclassified; declare a reviewed historical collection or use canonical records'
    return None


def _safe_names(data):
    if not isinstance(data, dict):
        return {}
    person = data.get('person', {})
    result = {k: person[k] for k in ('name', 'surname', 'norm') if k in person} if isinstance(person, dict) else {}
    # Only typed kinship/name fields survive a closed record. Free prose does not.
    fields = data.get('fields', data)
    if isinstance(fields, dict):
        result['names_and_kinship'] = {k: fields[k] for k in ('name', 'surname', 'father', 'mother', 'msur', 'husband', 'wife') if k in fields and isinstance(fields[k], str)}
    return result


def _share(entries):
    """Lossless common values: one copy of boilerplate, never a shorter reading."""
    counts, bank, known = Counter(), {}, {}
    encode = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    def count(value):
        key = encode(value)
        if len(key) > 100:
            counts[key] += 1
        for child in value.values() if isinstance(value, dict) else value if isinstance(value, list) else []:
            count(child)
    for entry in entries:
        count(entry['data'])
        count(entry['copies'])
    def pack(value, own=False):
        key = encode(value)
        if not own and counts[key] > 1 and len(key) > 100:
            if key not in known:
                ident = str(len(known) + 1)
                known[key] = ident
                bank[ident] = pack(value, own=True)
            return {'$ref': known[key]}
        if isinstance(value, dict):
            if '$ref' in value or '$literal' in value or '$row' in value or '$text' in value:
                return {'$literal': value}
            return {k: pack(v) for k, v in value.items()}
        return [pack(v) for v in value] if isinstance(value, list) else value
    return [dict(entry, data=pack(entry['data']), copies=pack(entry['copies'])) for entry in entries], bank


def _shared_dependencies(value, bank):
    result = set()
    if isinstance(value, dict):
        if '$literal' in value:
            return result
        if '$ref' in value:
            ident = value['$ref']
            result.add(ident)
            result.update(_shared_dependencies(bank[ident], bank))
        else:
            for child in value.values():
                result.update(_shared_dependencies(child, bank))
    elif isinstance(value, list):
        for child in value:
            result.update(_shared_dependencies(child, bank))
    return result


def _budget(result, entries, max_chars, inline):
    if max_chars < 4000:
        raise ValueError('person-card max_chars must be at least 4000')
    # A locator for every retrieved observation is mandatory, even when its body cannot fit.
    result['observations'] = []
    result['omitted'] = [{'locators': e['locators'], 'reason': 'body exceeds reading budget'} for e in entries]
    bank = {}
    if not inline:
        entries, bank = _share(entries)
        entries, bank = text_fragments(entries, bank)
        entries, bank, result['value_columns'] = value_tables(entries, bank)
        result['encoding'] = 'In observations.data/copies and shared_values, {$ref: ID} resolves in shared_values; {$row: [ID, cells]} uses value_columns[ID]; {$text: parts} concatenates resolved string parts; {$literal: VALUE} escapes a source object. No character is changed.'
        result['shared_values'] = {}
    view = lambda: result if inline else table_view(result)
    encode = lambda: json.dumps(view(), ensure_ascii=False, separators=(',', ':'))
    # Most cards fit in full. Avoid serialising the growing card once per row.
    result['observations'], result['omitted'] = entries, []
    if not inline:
        result['shared_values'] = bank
    result['complete_bodies'] = True
    if len(encode()) <= max_chars:
        return view()
    result['observations'] = []
    result['omitted'] = [{'locators': e['locators'], 'reason': 'body exceeds reading budget'} for e in entries]
    if not inline:
        result['shared_values'] = {}
    result['complete_bodies'] = False
    if len(encode()) > max_chars:
        raise ValueError('person-card locator manifest exceeds budget; increase --max-chars or narrow the declared collections')
    pending = result['omitted']
    result['omitted'] = []
    for index, entry in enumerate(entries):
        stub = pending[index]
        omitted = result['omitted']
        result['omitted'] = omitted + pending[index + 1:]
        result['observations'].append(entry)
        added = _shared_dependencies([entry['data'], entry['copies']], bank) - result.get('shared_values', {}).keys() if bank else set()
        for ident in sorted(added):
            result['shared_values'][ident] = bank[ident]
        fits = len(encode()) <= max_chars
        result['omitted'] = omitted
        if not fits:
            result['observations'].pop()
            result['omitted'].append(stub)
            for ident in added:
                del result['shared_values'][ident]
    result['complete_bodies'] = not result['omitted']
    if len(encode()) > max_chars:
        raise ValueError('person-card metadata exceeds the reading budget')
    return view()


@boundary('diagnostic')
def person_card(instance, query, *, catalog=None, aliases=(), relatives=(), max_chars=800000, inline=False, full=False, observation_index=None):
    """Private research diagnostic. No gate bypass is represented as publication."""
    config = configuration(instance, catalog)
    if not query.strip() or any(not alias.strip() for alias in aliases):
        raise ValueError('person query and aliases must be nonempty text')
    graph = _build(instance)
    query = graph.get('identityAliases', {}).get(query, query)
    people = graph['people']
    selected = {query} if query in people else {pid for pid, p in people.items() if fold(query) in {fold(n) for n in _names(p)}}
    unknown = set(relatives) - people.keys()
    if unknown:
        raise ValueError('unknown relative seeds: ' + ', '.join(sorted(unknown)))
    near = _neighbours(graph, selected)
    for pid in relatives:
        near.setdefault(pid, []).append({'role': 'research seed; kinship not established', 'basis': 'explicit --relative'})
    canonical_names = [name for pid in sorted(selected) for name in _names(people[pid])]
    configured_aliases = [alias for key in [query, *sorted(selected), *canonical_names] for alias in config.get('aliases', {}).get(key, [])]
    focus = list(dict.fromkeys([query, *canonical_names, *aliases, *configured_aliases]))
    relative_terms = [n for pid in near for n in _names(people.get(pid, {}))]
    # Surname retrieval is deliberately broad; no year or place rejects a namesake.
    # Aliases may put the surname first. Never turn their final given name into
    # a surname search (e.g. retrieving every unrelated Alexander in a region).
    names = [n for pid in selected for n in _names(people[pid])] or [query]
    surnames = [n.split()[-1] for n in names if len(n.split()) > 1]
    search = list(dict.fromkeys([*focus, *sorted(selected), *relative_terms, *surnames]))
    sources = config.get('sources', [])
    defaults = [{'id': key, 'path_key': key, 'glob': '**/*.json*', 'historical': key not in {'memory', 'answers', 'questions', 'searches'}, 'kind': key}
                for key in ('records', 'versions', 'cases', 'memory', 'answers', 'questions', 'searches', 'contributions', 'evidence', 'associations', 'identity_decisions')]
    rows, coverage = collect(instance, [*sources, *defaults], search)
    refs = references([people[pid] for pid in selected | near.keys() if pid in people] + [r['data'] for r in rows])
    for ref in sorted(refs & graph['sources'].keys()):
        rows.append({'locators': ['built-tree#sources/' + ref], 'collection': 'tree-citations',
                     'kind': 'source-citation', 'matched_on': [ref], 'data': graph['sources'][ref], '_historical': True})
    (protected, explicit), closed_terms = _protected(instance, graph), _closed_terms(instance)
    cards = []
    for pid in sorted(selected | near.keys()):
        person = people.get(pid, {'id': pid})
        is_protected = pid in protected
        reason = 'living or unknown; only name and kinship' if is_protected else _closure({'data': person, '_historical': True}, protected, explicit, closed_terms)
        cards.append({'id': pid, 'relation': 'query-name candidate; not an identity decision' if pid in selected else near[pid],
                      'person': _name_projection(person) if reason else person, 'closed': reason})
    unique, closed = {}, {}
    for row in rows:
        direct_terms = [n for n in focus if len(fold(n).split()) > 1 or n == query]
        row['retrieval'] = ('declared context' if not row['matched_on'] else 'query name or alias' if matches(row['data'], direct_terms) else 'relative name' if matches(row['data'], relative_terms) else 'surname neighbourhood')
        reason = _closure(row, protected, explicit, closed_terms)
        copy_data = row['data']
        if reason:
            copy_data = {k: copy_data[k] for k in ('source', 'local', 'raw', 'image', 'current_file_description') if k in copy_data} if isinstance(copy_data, dict) else {}
        row['copies'] = copies(instance, copy_data, origin=row.pop('_origin', None),
                               reference_roots=row.pop('_reference_roots', ()))
        row.pop('_historical', None)
        context = {k: row.pop(k) for k in ('expanded_arrays', 'container_context') if k in row}
        if context:
            row['origins'] = [{'locators': row['locators'][:], **context}]
        data, envelope = observation(row['data'])
        key = json.dumps(data, sort_keys=True, ensure_ascii=False)
        if reason:
            closed_key = (reason, key)
            if closed_key in closed:
                closed[closed_key]['locators'].extend(row['locators'])
            else:
                closed[closed_key] = {'locators': row['locators'], 'reason': reason,
                                      'names_and_kinship': _safe_names(row['data']), 'copies': row['copies']}
            continue
        row['data'] = data
        if envelope:
            row['representations'] = [{'locators': row['locators'][:], 'envelope': envelope}]
        if key in unique:
            unique[key]['locators'].extend(row['locators'])
            unique[key].setdefault('representations', []).extend(row.get('representations', []))
            unique[key].setdefault('origins', []).extend(row.get('origins', []))
            unique[key]['copies'] = list({json.dumps(c, sort_keys=True): c for c in [*unique[key]['copies'], *row['copies']]}.values())
        else:
            unique[key] = row
    entries = sorted(unique.values(), key=lambda r: (['query name or alias', 'relative name', 'surname neighbourhood', 'declared context'].index(r['retrieval']), r['locators'][0]))
    if observation_index is not None:
        if not 0 <= observation_index < len(entries):
            raise ValueError('observation index outside retrieved open observations')
        return {'output': {'state': 'preview', 'purpose': 'private research observation'},
                'query': query, 'observation_index': observation_index, 'observation': entries[observation_index]}
    families, versions = summaries(entries)
    # Relation bases are subject-linked graph claims, not a licence to reveal living dates.
    for card in cards:
        if card['closed'] and isinstance(card['relation'], list):
            card['relation'] = [{'role': r['role']} for r in card['relation']]
    result = {'output': {'state': 'preview', 'purpose': 'private research person card; not a publication'},
              'query': query, 'search_terms': search, 'people_and_nearest': cards,
              'families_as_recorded': families, 'recorded_version_questions': versions,
              'family_table_note': 'Grouped literal kinship fields, not merged people. Unlabelled cells and prose are not interpreted. See each observation for dates, godparents, doubts and arguments.',
              'selection': 'All name/alias, relative and surname hits in declared collections. Dates never filter. Identical observation content shares locators; import envelopes remain in representations. Different readings remain separate. Weights and identity levels are recorded claims, never computed here.',
              'coverage': coverage, 'closed': list(closed.values()), 'retrieved_observations': len(rows),
              'distinct_open_observations': len(entries), 'complete_bodies': False,
              'limitations': ['Local copies and images are pointers, not inspected originals.',
                              'Unconfigured collections are not searched. Text matching cannot establish identity or exhaust every spelling.',
                              'Historical collection declarations and free prose require family review; unknown canonical people remain protected.']}
    if not full:
        from .card_overview import overview
        return overview(result, entries, graph, selected, max_chars=min(max_chars, 85000))
    # Reserve the final boolean and avoid repeated graph payloads outside the same budget.
    if not inline:
        compact_metadata(result, entries)
    return _budget(result, entries, max_chars, inline)
