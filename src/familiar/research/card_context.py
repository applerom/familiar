# START_MODULE_CONTRACT: MOD-PERSON-CARD-CONTEXT
# PURPOSE: Expose literal family configurations and recorded version weights before a story author reads the observation mass.
# PRD_REF: docs/PRD.md#PERSON-CARD
# INVARIANTS:
# - kinship summaries group written fields, never identities, and do not infer a parent surname [review: engine lead]
# - import envelopes stay recoverable while copied literal observations share one entry [review: engine lead]
# - version summaries quote supplied weights without inventing or normalising them [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#PERSON-CARD (private card representation)
# :END_MODULE_CONTRACT
import copy
import json
import re
from collections import Counter
from itertools import pairwise
from os.path import commonprefix


def references(value):
    result = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {'sources', 'provenance', 'record'}:
                result.update(x for x in (child if isinstance(child, list) else [child]) if isinstance(x, str))
            result.update(references(child))
    elif isinstance(value, list):
        for child in value:
            result.update(references(child))
    return result


def observation(value):
    """Separate canonical import envelopes from an unchanged corpus observation."""
    if isinstance(value, dict) and isinstance(value.get('source'), dict) and isinstance(value.get('person'), dict):
        wrapper = {k: value[k] for k in ('id', 'kind', 'title', 'language', 'saved_result', 'intake_packet') if k in value}
        if not value.get('reading') and 'reading' in value:
            wrapper['reading'] = value['reading']
        return {k: v for k, v in value.items() if k not in wrapper}, wrapper
    return value, {}


KINSHIP = re.compile(r'father|mother|parent|spouse|husband|wife|child|godparent|chrzest|groom|bride|родител|отец|мать|супруг|дети|кр[её]ст', re.IGNORECASE)


def summaries(rows):
    families, versions = {}, []
    for row in rows:
        data = row['data']
        if not isinstance(data, dict):
            continue
        fields = data.get('fields', data)
        fields = fields if isinstance(fields, dict) else {}
        person = data.get('person', {})
        person = person if isinstance(person, dict) else {}
        name = person.get('norm') or ' '.join(str(person.get(k) or fields.get(k) or '') for k in ('name', 'surname')).strip() or fields.get('Name', '')
        kinship = {k: v for k, v in fields.items() if KINSHIP.search(k) and v not in (None, '', [])}
        relatives = data.get('relatives', [])
        if (kinship or relatives) and row['retrieval'] in {'query name or alias', 'relative name'}:
            family = {'person_as_written': name, 'kinship_fields_as_written': kinship, 'relatives_as_written': relatives}
            key = json.dumps(family, ensure_ascii=False, sort_keys=True)
            if key not in families:
                families[key] = {**family, 'locators': [], 'recorded_matches': []}
            families[key]['locators'].extend(row['locators'])
            if isinstance(data.get('match'), dict):
                match = {k: data['match'][k] for k in ('tree_id', 'confidence', 'weight', 'status') if k in data['match']}
                if match not in families[key]['recorded_matches']:
                    families[key]['recorded_matches'].append(match)
        if isinstance(data.get('versions'), list):
            versions.append({'locators': row['locators'], 'question': data.get('title', data.get('id')),
                             'people': data.get('people', []),
                             'versions': [{k: v[k] for k in ('id', 'label', 'title', 'weight', 'state', 'status') if k in v} for v in data['versions'] if isinstance(v, dict)],
                             **({'unknown_weight': data['unknown_weight']} if 'unknown_weight' in data else {})})
    return list(families.values()), versions


def compact_metadata(card, rows):
    """Alias repeated locator prefixes, leaving literal source data untouched."""
    candidates = sorted({r['path'] for r in card['coverage'] if len(r['path']) > 30}, key=lambda s: (-len(s), s))
    roots, counts, citations, reference_counts = {}, {}, {}, {}
    def visit(value, replace=False):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {'data', 'envelope', 'person', 'kinship_fields_as_written', 'relatives_as_written', 'recorded_matches'}:
                    continue
                if key == 'locators' and isinstance(child, list):
                    for i, ref in enumerate(child):
                        child[i] = alias(ref, replace)
                elif key in {'reference', 'packet'} and isinstance(child, str):
                    value[key] = alias(child, replace)
                else:
                    visit(child, replace)
        elif isinstance(value, list):
            for child in value:
                visit(child, replace)
    def alias(ref, replace):
        if citations:
            return '$C' + citations[ref] if replace and ref in citations else ref
        prefix = next((p for p in candidates if ref == p or ref.startswith((p + '/', p + '#'))), None)
        if prefix:
            if replace and prefix in roots:
                return '@' + roots[prefix] + ref[len(prefix):]
            if not replace:
                counts[prefix] = counts.get(prefix, 0) + 1
        return ref
    visit([card, rows])
    roots = {prefix: 'L' + str(i + 1) for i, prefix in enumerate(sorted(p for p, n in counts.items() if n > 1))}
    visit([card, rows], replace=True)
    card['locator_roots'] = {ident: prefix for prefix, ident in roots.items()}
    # Repeated complete locators (including shared raw copies) need one spelling.
    def count_references(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {'data', 'envelope', 'person', 'kinship_fields_as_written', 'relatives_as_written', 'recorded_matches'}:
                    continue
                if key == 'locators' and isinstance(child, list):
                    for ref in child:
                        reference_counts[ref] = reference_counts.get(ref, 0) + 1
                elif key in {'reference', 'packet'} and isinstance(child, str):
                    reference_counts[child] = reference_counts.get(child, 0) + 1
                else:
                    count_references(child)
        elif isinstance(value, list):
            for child in value:
                count_references(child)
    count_references([card, rows])
    citations = {ref: str(i + 1) for i, ref in enumerate(sorted(ref for ref, count in reference_counts.items() if count > 1 and len(ref) > 15))}
    visit([card, rows], replace=True)
    card['locator_values'] = {ident: ref for ref, ident in citations.items()}
    card['locator_note'] = 'Resolve $Cx in locator_values[x], then replace @Lx with locator_roots[Lx]. Literal source data is unchanged.'
    reasons = sorted({r['reason'] for r in card['closed']})
    card['closure_reasons'] = {'R' + str(i + 1): reason for i, reason in enumerate(reasons)}
    for row in card['closed']:
        row['reason'] = 'R' + str(reasons.index(row['reason']) + 1)


def table_view(card):
    """Write repeated metadata keys once, as the column header of each table."""
    result, columns = dict(card), {}
    for key in ('people_and_nearest', 'families_as_recorded', 'recorded_version_questions', 'closed', 'observations'):
        rows = card.get(key, [])
        if not rows:
            continue
        columns[key] = list(dict.fromkeys(k for row in rows for k in row))
        result[key] = [[row.get(k) for k in columns[key]] for row in rows]
    result['table_columns'] = columns
    result['table_note'] = 'Sections named in table_columns use rows in that column order. Null means absent summary metadata; original observation data retains its exact fields.'
    return result


def value_tables(rows, shared):
    """Share recurring record field layouts, keeping every key and literal value."""
    counts = Counter()
    def count(value):
        if isinstance(value, dict):
            if '$literal' in value or '$ref' in value:
                return
            keys = tuple(value)
            if sum(len(k) for k in keys) > 60:
                counts[keys] += 1
            for child in value.values():
                count(child)
        elif isinstance(value, list):
            for child in value:
                count(child)
    for row in rows:
        count(row['data'])
        count(row['copies'])
    for value in shared.values():
        count(value)
    layouts = {keys: str(i + 1) for i, keys in enumerate(sorted(k for k, n in counts.items() if n > 2))}
    def encode(value):
        if isinstance(value, dict):
            if '$literal' in value or '$ref' in value:
                return value
            keys = tuple(value)
            if keys in layouts:
                return {'$row': [layouts[keys], [encode(value[k]) for k in keys]]}
            return {k: encode(v) for k, v in value.items()}
        return [encode(v) for v in value] if isinstance(value, list) else value
    return ([dict(row, data=encode(row['data']), copies=encode(row['copies'])) for row in rows],
            {k: encode(v) for k, v in shared.items()}, {ident: list(keys) for keys, ident in layouts.items()})


def text_fragments(rows, shared):
    """Share repeated HTML/URL/line fragments without changing a single character."""
    counts, parts, strings = Counter(), {}, set()
    def count(value):
        if isinstance(value, dict):
            if '$literal' not in value and '$ref' not in value:
                for child in value.values():
                    count(child)
        elif isinstance(value, list):
            for child in value:
                count(child)
        elif isinstance(value, str) and len(value) > 100:
            strings.add(value)
    for row in rows:
        count(row['data'])
        count(row['copies'])
    for value in shared.values():
        count(value)
    ordered = sorted(strings)
    prefixes = {commonprefix(pair) for pair in pairwise(ordered)}
    prefixes = sorted((p for p in prefixes if len(p) >= 60 and sum(s.startswith(p) for s in strings) > 2), key=lambda p: (-len(p), p))
    for string in ordered:
        prefix = next((p for p in prefixes if len(p) < len(string) and string.startswith(p)), '')
        pieces = ([prefix] if prefix else []) + re.split(r'(?=<)|(?<=>)|(?<=&)|(?<=\n)|(?<=\[)|(?<=\])|(?<=\|)|(?<=;)', string[len(prefix):])
        if sum(bool(piece) for piece in pieces) > 1:
            parts[string] = pieces
            counts.update(piece for piece in pieces if len(piece) > 40)
    repeated = {piece for piece, n in counts.items() if n > 2}
    ids = {v: k for k, v in shared.items() if isinstance(v, str)}
    bank = dict(shared)
    def encode(value):
        if isinstance(value, dict):
            if '$literal' in value or '$ref' in value:
                return value
            return {k: encode(v) for k, v in value.items()}
        if isinstance(value, list):
            return [encode(v) for v in value]
        if isinstance(value, str) and value in parts and any(p in repeated for p in parts[value]):
            pieces = []
            for part in parts[value]:
                if part in repeated:
                    if part not in ids:
                        ids[part] = str(len(bank) + 1)
                        bank[ids[part]] = part
                    pieces.append({'$ref': ids[part]})
                else:
                    pieces.append(part)
            return {'$text': pieces}
        return value
    encoded = [dict(row, data=encode(row['data']), copies=encode(row['copies'])) for row in rows]
    for key, value in shared.items():
        bank[key] = encode(value)
    return encoded, bank


def expand_card(card):
    """Recover object rows and literal values without reading a family or a URL."""
    result = copy.deepcopy(card)
    shared, layouts = result.get('shared_values', {}), result.get('value_columns', {})
    def value(item):
        if isinstance(item, dict):
            if '$literal' in item:
                return item['$literal']
            if '$ref' in item:
                return value(shared[item['$ref']])
            if '$text' in item:
                return ''.join(value(piece) for piece in item['$text'])
            if '$row' in item:
                ident, cells = item['$row']
                return {k: value(v) for k, v in zip(layouts[ident], cells, strict=True)}
            return {k: value(v) for k, v in item.items()}
        return [value(v) for v in item] if isinstance(item, list) else item
    for section, columns in result.get('table_columns', {}).items():
        result[section] = [{k: v for k, v in zip(columns, row, strict=True) if v is not None} for row in result[section]]
    for row in result.get('observations', []):
        for key, bank in (('collection', 'collections'), ('retrieval', 'retrieval_scopes')):
            if isinstance(row.get(key), int):
                row[key] = result[bank][row[key]]
        for key in ('summary', 'qualification'):
            if isinstance(row.get(key), int):
                row[key] = result['overview_values'][row[key]]
    for row in result.get('observations', []):
        if 'data' in row:
            row['data'], row['copies'] = value(row['data']), value(row['copies'])
    def locator(ref):
        if isinstance(ref, int):
            return 'full#/closed/' + str(ref)
        if re.fullmatch(r'\$C\d+', ref) and ref[2:] in result.get('locator_values', {}):
            ref = result['locator_values'][ref[2:]]
        if (head := re.match(r'@(L\d+)(.*)', ref)) and head[1] in result.get('locator_roots', {}):
            ref = result['locator_roots'][head[1]] + head[2]
        return ref
    def walk(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if key in {'data', 'envelope', 'person', 'kinship_fields_as_written', 'relatives_as_written', 'recorded_matches', 'shared_values', 'value_columns', 'locator_values', 'locator_roots', 'closure_reasons'}:
                    continue
                if key == 'locators':
                    item[key] = [locator(ref) for ref in child]
                elif key in {'reference', 'packet'} and isinstance(child, str):
                    item[key] = locator(child)
                else:
                    walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
    walk(result)
    for row in result.get('closed', []):
        row['reason'] = result.get('closure_reasons', {}).get(row['reason'], row['reason'])
    for key in ('shared_values', 'value_columns', 'encoding', 'table_columns', 'table_note', 'locator_roots', 'locator_values', 'locator_note', 'closure_reasons'):
        result.pop(key, None)
    return result
