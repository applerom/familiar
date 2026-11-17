# START_MODULE_CONTRACT: MOD-PERSON-CARD-OVERVIEW
# PURPOSE: Fit the author's discovery entrance into one reading while retaining every observation locator.
# PRD_REF: docs/PRD.md#PERSON-CARD
# INVARIANTS:
# - every open observation has a row locator that recovers its whole body and original source locators [review: engine lead]
# - summaries report retrieval and supplied qualifications without adjudicating namesakes [review: engine lead]
# CHANGES_WITH:
# - MOD-PERSON-CARD (uncompressed private diagnostic)
# :END_MODULE_CONTRACT
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict

from .card_context import table_view
from .card_relations import SCRIPT


def short(value, limit=160):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    text = re.sub(r'<[^>]+>', ' ', text)
    text = ' '.join(text.split())
    return text if len(text) <= limit else text[:limit - 1] + '…'


def describe(data, limit=160):
    if not isinstance(data, dict):
        return short(data, limit)
    bits = []
    for parent in ('fields', 'source'):
        nested = data.get(parent)
        if isinstance(nested, dict):
            for key in ('year', 'date', 'type', 'place', 'parish'):
                if nested.get(key):
                    bits.append(f'{key}: {short(nested[key], 35)}')
    # Stable typed facts precede prose; no inference from a matching name.
    for key in ('year', 'date', 'event', 'type', 'place', 'parish', 'literal', 'text', 'reading',
                'person', 'fields', 'title', 'label', 'summary', 'note', 'heading'):
        if key in data and data[key] not in (None, '', {}, []):
            bits.append((f'{key}: ' if key not in {'literal', 'text', 'reading', 'title'} else '') + short(data[key], limit))
    return short('; '.join(bits) or data, limit)


def host_relations(graph, selected):
    if not selected:
        return {'unestablished': 'Query is absent from the canonical tree; no relationship to the family host is asserted.'}
    node = shutil.which('node')
    if not node:
        return {'unavailable': 'Reader relationship calculation requires Node.js; no substitute calculation used.'}
    result = subprocess.run([node, '--input-type=module', '-e', SCRIPT], check=False,
                            input=json.dumps({'graph': graph, 'selected': sorted(selected)}, ensure_ascii=False),
                            capture_output=True, text=True, encoding='utf-8', timeout=15)
    if result.returncode:
        raise ValueError('reader relationship calculation failed: ' + result.stderr[:500])
    return json.loads(result.stdout)


def overview(card, entries, graph, selected, max_chars):
    card['relationship_to_host'] = host_relations(graph, selected)
    card['reading_mode'] = 'overview; truncated prose is marked …; every body and qualification is at its locator or in --full --max-chars 10000000'
    card['complete_bodies'] = False
    card['folded'] = {'literal_bodies': len(entries),
                      'import_envelopes': sum(len(e.get('representations', [])) for e in entries),
                      'container_contexts': sum(len(e.get('origins', [])) for e in entries),
                      'copy_pointers': sum(len(e.get('copies', [])) for e in entries)}
    # Literal family configurations already live in observations; reference those
    # rows instead of repeating their fields and source manifests a second time.
    by_locator = {ref: i for i, entry in enumerate(entries) for ref in entry['locators']}
    card['folded']['literal_family_configurations'] = len(card['families_as_recorded'])
    card['family_configuration_rows'] = sorted({by_locator[ref] for row in card.pop('families_as_recorded') for ref in row['locators'] if ref in by_locator})
    for row in card['people_and_nearest']:
        person = row['person']
        row['person'] = {k: person[k] for k in ('id', 'name', 'names', 'events', 'life_assessment', 'confirmation', 'relationshipUncertain') if k in person}
        row['full_person_locator'] = 'built-tree#people/' + row['id']
    # Each group is a retrieval neighbourhood, never a proposed merged identity.
    groups = defaultdict(list)
    stories = []
    for i, entry in enumerate(entries):
        data = entry['data']
        name = data.get('person', {}) if isinstance(data, dict) else {}
        group = (name.get('norm') or ' '.join(str(name.get(k) or '') for k in ('name', 'surname')).strip()) if isinstance(name, dict) else short(name, 60)
        group = group or entry['retrieval']
        groups[group].append(i)
        if entry['kind'] in {'author_argument', 'context', 'versions'} or any('/feeds/' in ref for ref in entry['locators']):
            stories.append(i)
    card['namesake_groups'] = dict(groups)
    card['group_note'] = 'Same written name or retrieval scope only; not an identity decision. Row indices refer to observations.'
    card['already_told_or_context'] = stories
    card['already_told_closed'] = [i for i, row in enumerate(card['closed']) if any('/feeds/' in ref or '/story/' in ref for ref in row['locators'])]
    # The manifest and qualifications survive even when excerpts must be shortened.
    collections = sorted({e['collection'] for e in entries})
    scopes = sorted({e['retrieval'] for e in entries})
    card['collections'], card['retrieval_scopes'] = collections, scopes
    card['observations'] = [{'locators': e['locators'], 'collection': collections.index(e['collection']),
                                 'retrieval': scopes.index(e['retrieval']), 'summary': describe(e['data'], 65),
                                 'qualification': short(e['data'].get('match', {}), 60) if isinstance(e['data'], dict) and e['data'].get('match') else ''} for e in entries]
    card['row_codes'] = 'collection and retrieval are zero-based indices in collections and retrieval_scopes.'
    counts = Counter(row[k] for row in card['observations'] for k in ('summary', 'qualification'))
    shared = sorted(s for s, n in counts.items() if len(s) > 10 and n > 1)
    card['overview_values'] = shared
    ids = {s: i for i, s in enumerate(shared)}
    for row in card['observations']:
        for key in ('summary', 'qualification'):
            row[key] = ids.get(row[key], row[key])
    card['row_codes'] += ' Integer summary/qualification cells index overview_values.'
    card['omitted'] = []
    for row in card['closed']:
        row.pop('copies', None)
        row.pop('names_and_kinship', None)
    reasons = sorted({r['reason'] for r in card['closed']})
    card['closure_reasons'] = {str(i): reason for i, reason in enumerate(reasons)}
    for row in card['closed']:
        row['reason'] = str(reasons.index(row['reason']))
    card['folded']['source_locators'] = sum(len(e['locators']) for e in entries)
    for i, row in enumerate(card['observations']):
        row.pop('locators')
    for i, row in enumerate(card['closed']):
        row['locators'] = [i]
    card['locator_note'] = 'The zero-based observations ROW INDEX N is its locator: use the SAME query, aliases, relative seeds and catalog plus --observation N. It returns every original file/line/JSON/SQLite locator, copy, body and import envelope. Closed integer locators point into --full --inline closed[N]. Inputs must be unchanged between calls.'
    result = table_view(card)
    if len(json.dumps(result, ensure_ascii=False, separators=(',', ':'))) > max_chars:
        raise ValueError('overview locator manifest exceeds budget; increase --max-chars or narrow collections')
    return result
