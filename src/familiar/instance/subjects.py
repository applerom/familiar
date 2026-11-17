# START_MODULE_CONTRACT: MOD-SUBJECT-CLOSURE
# PURPOSE: Resolve exact structured participants and corpus dependencies through every publication route.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - document, scan, cover and nested variants share record subject resolution [test: tests/gate/test_data_guarantees.py::test_f2_record_subject_cannot_be_omitted]
# - explicit record roles resolve across every document and picture path [review: engine lead]
# - retired facts retain the same corpus subject closure as current facts [review: engine lead]
# - typed literal excerpts cannot expose full records or substitute their text [review: engine lead]
# - linked document subjects accumulate across galleries, chapters and facts before any reader filtering [review: engine lead]
# - a narrator reference on reported kinship resolves to a canonical family person [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION
# - MOD-CHECKS-PRIVACY
# :END_MODULE_CONTRACT
import unicodedata
from dataclasses import dataclass, field


def normalized(value):
    if isinstance(value, str):
        return unicodedata.normalize('NFC', value)
    if isinstance(value, list):
        return [normalized(v) for v in value]
    if isinstance(value, dict):
        result = {normalized(k): normalized(v) for k, v in value.items()}
        if len(result) != len(value):
            raise ValueError('duplicate canonical NFC id or field')
        return result
    return value


def explicit_subjects(record):
    """Declared record references: people values, subjects.person, person.id, relatives.id."""
    subjects = []
    mapping = record.get('people', {})
    subjects.extend(mapping.values() if isinstance(mapping, dict) else mapping)
    subjects.extend(s.get('person') if isinstance(s, dict) else s for s in record.get('subjects', []))
    person = record.get('person')
    if isinstance(person, str):
        subjects.append(person)
    elif isinstance(person, dict) and person.get('id'):
        subjects.append(person['id'])
    unsupported = {'person', 'person_id', 'personId', 'canonical', 'canonical_id', 'subjects', 'people'}
    if isinstance(person, dict) and unsupported.intersection(person):
        raise ValueError('unsupported primary person reference; use person.id')
    for relative in record.get('relatives', []):
        if not isinstance(relative, dict):
            raise ValueError('record relatives must be objects; canonical reference is relatives[].id')  # noqa: TRY004
        if relative.get('id'):
            subjects.append(relative['id'])
        if unsupported.intersection(relative):
            raise ValueError('unsupported relative reference; use relatives[].id')
    return list(dict.fromkeys(normalized(s) for s in subjects if s))


@dataclass
class Closure:
    people: set = field(default_factory=set)
    records: dict = field(default_factory=dict)
    images: list = field(default_factory=list)


def _excerpt(data, fields):
    """A typed text excerpt selects literal fields, never a whole scan or reading."""
    if not isinstance(fields, list) or not fields or any(not isinstance(f, str) for f in fields):
        raise ValueError('TRUST-01: excerpt must name literal record fields')
    mapping = data.get('field_subjects', {})
    if any(f not in data.get('fields', {}) or f not in mapping or not isinstance(mapping[f], list) or not mapping[f] for f in fields):
        raise ValueError('TRUST-06: excerpt fields need recorded subjects; classify or separate the document first')
    return {'id': data['id'], 'kind': data.get('kind'), 'fictional': data.get('fictional', False),
            'fields': {f: data['fields'][f] for f in fields}, 'excerpt': fields,
            'subjects': list(dict.fromkeys(p for f in fields for p in mapping[f]))}


def closure(instance, value, *, shape='chapter', documents=None, pictures=None, people=None):
    """Author lists add subjects; no route can subtract a linked record's subjects."""
    from familiar.checks.engine import _known_people, load, record_path

    from .publication import SCHEMAS
    known = _known_people(instance) if people is None else people
    documents, pictures = documents or {}, pictures or {}
    result = Closure()

    def person(pid):
        pid = normalized(pid)
        row = known.get(pid)
        if row is None:
            raise ValueError('TRUST-01: unknown canonical person id: ' + str(pid))
        result.people.add(row.get('id', pid))

    def record(rid, excerpt=None):
        rid = normalized(rid)
        if rid in documents and documents[rid].get('record') != rid:
            walk(documents[rid], 'document')
            return
        path = record_path(instance, rid)
        if not path.is_file():
            raise ValueError('TRUST-01: unknown canonical record id: ' + str(rid))
        data = load(path, {})
        if excerpt is not None:
            data = _excerpt(data, excerpt)
        if rid not in result.records or excerpt is None:
            result.records[rid] = data
        elif result.records[rid].get('excerpt'):
            result.records[rid] = _excerpt(load(path, {}), list(dict.fromkeys(result.records[rid]['excerpt'] + excerpt)))
        for pid in explicit_subjects(data):
            person(pid)

    person_fields = {
        'chapter': {'people'}, 'feed': {'people'}, 'image': {'subjects'},
        'document': {'subjects'}, 'source': {'subjects'}, 'node': {'id'}, 'small-tree': {'highlight'},
        'clan': {'parents'}, 'clan-family': {'head', 'spouse', 'kids'}, 'gen': {'ids'},
        'family': {'husband', 'wife', 'children'}, 'edge': {'from', 'to', 'parent', 'child'},
        'reported-kinship': {'viewer'},
        'hardship': {'people'}, 'graph': {'root'},
        'fact': {'people'}, 'variant': {'people'}, 'place': {'people'},
        'extra': {'people'}, 'link': {'people'}, 'kids': {'people'},
    }

    def walk(node, kind):
        if kind == 'retired-fact':
            kind = 'fact'
        if node is None:
            return
        if isinstance(kind, list):
            for child in node:
                walk(child, kind[0])
            return
        if isinstance(kind, tuple):
            for child in node.values():
                walk(child, kind[1])
            return
        if kind not in SCHEMAS or not isinstance(node, dict):
            return
        if kind == 'person':
            person(node['id'])
        if kind == 'image':
            result.images.append(node)
        if (kind in {'document', 'image', 'source', 'fact'} and node.get('record') and
                (kind != 'source' or node.get('kind') not in {'memory', 'import', 'gedcom'})):
            selection = node.get('excerpt')
            if selection is not None:
                if kind not in {'document', 'source'} or node.get('full') or node.get('asset') or any(p.get('asset') for p in node.get('parts', node.get('snippets', []))):
                    raise ValueError('TRUST-06: text excerpt cannot include a scan or full document')
                source = _excerpt(load(record_path(instance, node['record']), {}), selection)
                for part in ([node] + node.get('parts', []) if node.get('read') else node.get('snippets', [])):
                    if part.get('field') not in source['fields'] or part.get('read') != source['fields'][part['field']]:
                        raise ValueError('TRUST-02: excerpt reading must equal its selected literal field')
            record(node['record'], selection)
        if kind in {'chapter', 'feed'}:
            for blocks in node.get('prose', node.get('_prose', {})).values():
                for block in blocks:
                    for pid in block['people']:
                        person(pid)
                    for pid in block.get('otherwise', {}).get('people', []):
                        person(pid)
        if kind == 'chapter':
            for ref in node.get('records', []):
                if 'doc' in ref:
                    if ref['doc'] not in documents:
                        raise ValueError('TRUST-01: unknown document id: ' + str(ref['doc']))
                    walk(documents[ref['doc']], 'document')
        for key, child in node.items():
            if key in person_fields.get(kind, set()):
                for pid in child if isinstance(child, list) else [child]:
                    if pid:
                        person(pid)
            elif kind == 'feed' and key == 'cover' and child in pictures:
                walk(pictures[child], 'image')
            elif key in SCHEMAS[kind]:
                target = SCHEMAS[kind][key].shape
                if kind == 'image' and key == 'orig' and isinstance(child, str):
                    child = {'asset': child}
                if target == 'image' and isinstance(child, str):
                    if child not in pictures:
                        raise ValueError('TRUST-01: unknown picture id: ' + child)
                    child = pictures[child]
                if target == ['image']:
                    child = [pictures.get(v, v) if isinstance(v, str) else v for v in child]
                walk(child, target)
        if kind == 'extra':
            for ref in node.get('records', []):
                if ref.get('doc') in documents:
                    walk(documents[ref['doc']], 'document')
    walk(normalized(value), shape)
    return result


def attribute_documents(instance, graph):
    """Add contextual subjects to every shared document route, without changing inputs.

    Resource identities join only structured references, never titles or prose.
    A shared scan inherits all its uses, including protected gallery owners.
    Literal excerpts remain separate from the full record's identity.
    """
    from familiar.checks.engine import _known_people
    known = _known_people(instance)
    record_ids = {normalized(p.stem) for p in instance.path('records').rglob('*.json')}
    parents, subjects, uses, protected = {}, {}, [], set()

    def root(key):
        parents.setdefault(key, key)
        if parents[key] != key:
            parents[key] = root(parents[key])
        return parents[key]

    def bind(keys, people):
        if not keys:
            return None
        first = root(keys[0])
        for key in keys[1:]:
            other = root(key)
            if other != first:
                parents[other] = first
                subjects.setdefault(first, set()).update(subjects.pop(other, set()))
        subjects.setdefault(first, set()).update(people)
        return first

    def document(node, shape, context=(), sid=None):
        keys = [('source', sid)] if sid else []
        if node.get('record') and 'excerpt' not in node:
            keys.append(('record', node['record']))
        keys += [('source', node[k]) for k in ('sid', 'sourceSid') if node.get(k)]
        keys += [('asset', node[k]) for k in ('asset', 'full', 'originalAsset') if isinstance(node.get(k), str) and node[k]]
        keys += [('asset', part['asset']) for part in node.get('parts', node.get('snippets', [])) if part.get('asset')]
        for child in ('orig', 'ours'):
            value = node.get(child)
            if isinstance(value, str):
                keys.append(('asset', value))
            elif isinstance(value, dict) and value.get('asset'):
                keys.append(('asset', value['asset']))
        value = dict(node, kind='archive-record') if shape == 'source' and node.get('record') in record_ids else node
        resolved = closure(instance, value, shape=shape, people=known)
        people = set(context) | resolved.people
        key = bind(keys, people)
        if key is not None and any(r.get('privacy') in {'living', 'living-possible'} for r in resolved.records.values()):
            protected.add(key)
        uses.append((node, key, people))

    def fact(row, context):
        people = set(context) | set(row.get('_people', row.get('people', [])))
        if row.get('record'):
            document(row, 'fact', people)
        for sid in row.get('sources', []):
            bind([('source', sid)], people)

    def story(node, context=()):
        people = node.get('_people', node.get('people', context))
        for row in node.get('records', []):
            document(row, 'document', people)
        for collection in ('picture', 'figures'):
            values = node.get(collection, [])
            for image in values if isinstance(values, list) else [values]:
                if isinstance(image, dict) and (image.get('record') or image.get('kind') == 'document-scan' or image.get('photo') is False):
                    document(image, 'image', people)
        for row in node.get('facts', []):
            fact(row, people)
        for child in node.get('extras', []) + node.get('chapters', []):
            story(child, people)

    for sid, source in graph.get('sources', {}).items():
        if not source.get('record') and sid in record_ids:
            source['record'] = sid
        document(source, 'source', sid=sid)
    for pid, person in graph.get('people', {}).items():
        for collection in ('media', 'illustrations'):
            for image in person.get(collection, []):
                if image.get('record') or image.get('kind') == 'document-scan' or image.get('photo') is False:
                    document(image, 'image', [pid])
        for row in person.get('facts', []) + person.get('retiredFacts', []):
            fact(row, [pid])
    for feed in graph.get('feeds', []):
        story(feed)
    for node, key, people in uses:
        # Facts carry context to sources, but their subjects are not reader fields.
        if key is not None:
            people |= subjects[root(key)]
            if any(root(k) == root(key) for k in protected):
                node['_document_private'] = True
        node['subjects'] = sorted(people)
