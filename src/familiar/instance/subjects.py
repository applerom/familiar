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
# - declared cut-out subjects cannot replace corpus subjects; chapter context is only a fallback [review: engine lead]
# - generated photo restorations bind real originals and deceased subjects before any privacy omission [review: engine lead]
# - attaching an archival photograph elsewhere cannot subtract its identified subjects [review: engine lead]
# - a protected person's citation closes the whole document unless its corpus record declares complete subjects and the citation is only an inference [test: tests/gate/test_data_guarantees.py::test_f2_record_subject_cannot_be_omitted]
# - a public census or family annex needs a complete participant list, including children [test: tests/gate/test_data_guarantees.py::test_f2_record_subject_cannot_be_omitted]
# CHANGES_WITH:
# - MOD-PUBLICATION
# - MOD-CHECKS-PRIVACY
# :END_MODULE_CONTRACT
import copy
import json
import re
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


def recorded_match(record):
    """A recorded identification can name a participant; a search candidate cannot."""
    from familiar.tree.life import recorded
    match = record.get('match') or {}
    if match.get('confidence') == 'same' and recorded(record) and recorded(match):
        return match.get('tree_id')
    return None


def feedback_record(record):
    """A home paper copied from a family member's feedback is their document."""
    locator = (record.get('source') or {}).get('locator')
    return (record.get('kind') == 'home-paper' and isinstance(locator, str)
            and locator.replace('\\', '/').removeprefix('./').startswith('family/feedback/inbox/'))


def protected_record(record):
    return feedback_record(record) or record.get('privacy') in {'living', 'living-possible'}


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
    elif pid := recorded_match(record):
        subjects.append(pid)
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
    for event in record.get('events', []):
        subjects.extend(s.get('person') if isinstance(s, dict) else s for s in event.get('subjects', []))
    for field_people in record.get('field_subjects', {}).values():
        subjects.extend(field_people)
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
    privacy = 'living' if protected_record(data) else data.get('privacy')
    return {'id': data['id'], 'kind': data.get('kind'), 'fictional': data.get('fictional', False),
            **({'privacy': privacy} if privacy else {}),
            'fields': {f: data['fields'][f] for f in fields}, 'excerpt': fields,
            'subjects': list(dict.fromkeys(p for f in fields for p in mapping[f]))}


def photo_pair(instance, image):
    """Bind a treatment to its real frame; dimensions cannot establish facial fidelity."""
    if image.get('kind') == 'photo-restoration':
        original = image.get('orig')
        if not isinstance(original, dict):
            raise ValueError('TRUST-08: photo restoration needs its real original frame')
        from .restorations import bind
        bind(instance, original, image)
        return
    if image.get('ours', {}).get('kind') == 'photo-restoration':
        from .restorations import bind
        bind(instance, image, image['ours'])
        return
    if image.get('kind') == 'photo-treatment':
        original = image.get('orig')
        if not isinstance(original, dict) or original.get('kind') == 'photo-treatment':
            raise ValueError('TRUST-08: photo treatment needs its real original frame')
        photo_pair(instance, dict(original, ours=image))
        return
    treatment = image.get('ours', {})
    if treatment.get('kind') != 'photo-treatment':
        return
    from familiar.checks.engine import generated, record_path
    from .archive import photograph_rights
    if image.get('kind') == 'family-photograph':
        rights = photograph_rights(instance, image)
        genuine = 'subjects' in image and rights and rights.get('holder') and rights.get('permissions', {}).get('family_app')
    else:
        genuine = image.get('kind') in {'period-picture', 'document-scan'} and record_path(instance, image.get('record')).is_file()
    if not genuine or generated(image) or image.get('reconstruction') or treatment.get('generated') or treatment.get('reconstruction'):
        raise ValueError('TRUST-10: photo treatment needs a real original with a corpus record or family-photo rights')
    if not treatment.get('disclosure') or not image.get('caption') or not treatment.get('caption'):
        raise ValueError('TRUST-08: photo treatment needs original and treatment captions and disclosure')
    original = {k: copy.deepcopy(v) for k, v in image.items() if k != 'ours'}
    reference = treatment.get('orig')
    if reference is not None and reference != image.get('asset') and not (isinstance(reference, dict) and reference.get('asset') == image.get('asset')):
        raise ValueError('TRUST-08: photo treatment must name the same original frame')
    for key in ('subjects', 'record'):
        if key in treatment and treatment[key] != image.get(key) and not image.get('_document_attributed'):
            raise ValueError('TRUST-06: photo treatment cannot change original subjects or record')
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError('Photo treatments require Pillow; install familiar[images]') from exc
    paths = [instance.media_file(item.get('asset', '')) for item in (image, treatment)]
    if not all(paths):
        raise ValueError('TRUST-10: photo treatment or original file is missing')
    with Image.open(paths[0]) as original_frame, Image.open(paths[1]) as edited:
        if original_frame.size != edited.size:
            raise ValueError('TRUST-08: photo treatment and original dimensions differ')
    treatment.update(orig=original, subjects=list(image.get('subjects', [])))
    if image.get('record'):
        treatment['record'] = image['record']


def closure(instance, value, *, shape='chapter', documents=None, pictures=None, people=None):
    """Author lists add subjects; no route can subtract a linked record's subjects."""
    from familiar.checks.engine import _known_people, load, record_path

    from .publication import SCHEMAS
    from .gallery import photograph
    known = _known_people(instance) if people is None else people
    documents, pictures = documents or {}, pictures or {}
    result = Closure()

    from .restorations import restorations
    restored_assets = {v.get('asset') for r in restorations(value)
                       for v in (r['versions'] if isinstance(r.get('versions'), list) else [])
                       if isinstance(v, dict)}

    def person(pid):
        pid = normalized(pid)
        row = known.get(pid)
        if row is None:
            raise ValueError('TRUST-01: unknown canonical person id: ' + str(pid) + '; inspect ids with tree build --view working')
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
        if kind in {'document', 'source', 'snippet'} and (node.get('kind') == 'photo-restoration' or
                any(node.get(k) in restored_assets for k in ('asset', 'full') if node.get(k)) or
                any(restorations(node))):
            raise ValueError('TRUST-08: photo restoration is never a document or source')
        if kind == 'person':
            person(node['id'])
        if kind == 'image':
            photo_pair(instance, node)
            if photo := photograph(instance, node.get('asset')):
                for pid in photo['subjects']:
                    person(pid)
            if node.get('kind') == 'photo-treatment' and not node.get('orig'):
                raise ValueError('TRUST-08: photo treatment needs its original frame')
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
            if kind in {'document', 'image'} and node.get('subjects') and not node.get('_document_attributed'):
                declared = {known[p].get('id', p) for p in node['subjects'] if p in known}
                actual = {known[p].get('id', p) for p in explicit_subjects(result.records[node['record']]) if p in known}
                if actual - declared:
                    raise ValueError('TRUST-06: declared subjects disagree with corpus record: ' + node['record'])
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


def historical_records(resolved):
    return bool(resolved.records) and all(record.get('privacy') == 'dead' and not protected_record(record)
                                          for record in resolved.records.values())


def fileless_memory(source):
    return source.get('kind') in {'memory', 'family-memory'} and not any(
        source.get(k) for k in ('record', 'asset', 'assetIn', 'local', 'url', 'image', 'capture', 'full'))


def complete_subjects(record):
    """Only the corpus record can attest that its list covers the whole document."""
    rows = record.get('subjects') or []
    return (record.get('subjects_complete') is True and bool(rows)
            and all(s if isinstance(s, str) else isinstance(s, dict) and s.get('person') for s in rows))


GROUP_RECORD = re.compile(r'\b(?:census|household|family[- ]annex|перепис\w*|семейн\w+ приложен\w*|'
                          r'spis ludności|folkräkning)\b', re.I)


def unreviewed_group(record):
    """A group sheet may name children or unnamed-in-the-tree relatives."""
    if record.get('excerpt') or complete_subjects(record):
        return False
    labels = [record.get(k, '') for k in ('id', 'kind', 'title', 'type')]
    labels.extend(event.get('type', '') for event in record.get('events', []))
    return (any(GROUP_RECORD.search(str(label)) for label in labels)
            or any(not relative.get('id') for relative in record.get('relatives', [])))


def own_papers(person):
    """Sources of the person's own names and events: a paper that records them is about this person."""
    return {sid for key in ('names', 'events') for row in person.get(key) or [] if isinstance(row, dict)
            for field in ('provenance', 'sources') for sid in row.get(field) or [] if isinstance(sid, str)}


def infers(fact):
    """A told conclusion, not the person's own name or event read from the paper."""
    return not any(fact.get(k) for k in ('eventType', 'event_correction', 'card_details', 'record'))         and fact.get('label') not in ('names', 'events', 'document')


def check(instance, graph, records, fail):
    """Advice only: a paper is off a dead relative's card only because a living person's fact infers from it."""
    from familiar.checks.engine import life_status, load
    from familiar.tree.life import _assess
    people = graph['people']
    inferring, owners, own = {}, {}, {}
    for pid, person in people.items():
        papers = own_papers(person)
        for fact in person.get('facts', []):
            for sid in fact.get('sources') or []:
                owners.setdefault(sid, set()).add(pid)
                (inferring if infers(fact) and sid not in papers else own).setdefault(sid, set()).add(pid)
    def waiting(sid, dead):
        source = graph['sources'].get(sid, {})
        record = records.get(source.get('record', sid))
        living = inferring[sid] - dead
        named = any(names(written(source, record), people[p]) for p in living)
        return (record and living and owners[sid] & dead and (named or not complete_subjects(record))
                and not (own.get(sid, set()) - dead) and not protected_record(record)
                and not {p for p in explicit_subjects(record) if p in people} - dead)
    privacy = load(instance.path('privacy'), {})
    gone = lambda view: {pid for pid, p in view.items() if life_status(p, privacy) == 'dead'}
    if not any(waiting(sid, gone(people)) for sid in inferring):
        return
    # Reuse the recorded evidence for the family's display horizon.
    seen = _assess(instance, graph | {'people': {pid: dict(p) for pid, p in people.items()}}, family_display=True)['people']
    dead = gone(seen)
    for sid in sorted(inferring):
        if waiting(sid, dead):
            name = lambda ids: ', '.join(sorted(people[p].get('name') or p for p in ids))
            source = graph['sources'].get(sid, {})
            theirs, kept = sorted(owners[sid] & dead), inferring[sid] - dead
            named = [p for p in kept if names(written(source, records[source.get('record', sid)]), people[p])]
            fail(instance.path('contributions'), f"{source.get('title') or records[source.get('record', sid)].get('title') or sid}: "
                 f"not shown on the card of {name(theirs)} only because a fact on the card of {name(kept)} "
                 '(living) cites it. ' + (f"Its own words name {name(named)}: if that is our note, move it to collector_note"
                                          if named else f'If the paper is about the dead alone, review all participants in the '
                                          f'corpus record and write "subjects": {json.dumps(theirs)}, "subjects_complete": true'))


def written(source, record):
    """The paper's own words: its title, reading and literal fields, never a researcher's note beside them."""
    from familiar.checks.engine import strings
    record = record or {}

    def literal(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from literal(child)
        elif isinstance(value, list):
            for child in value:
                yield from literal(child)
        elif isinstance(value, str):
            yield value

    subject_names = [s.get('written') for s in record.get('subjects', []) if isinstance(s, dict)]
    return ' '.join([*strings([source.get('title'), *subject_names,
                               *(record.get(k) for k in ('title', 'reading', 'events', 'relatives'))]),
                     *literal(record.get('fields'))]).casefold()


def names(text, person):
    """Whether these words name the person: a given name and a surname of one of their written names, by their roots."""
    rows = [f"{n.get('given') or ''} {n.get('surname') or ''}".split() for n in person.get('names') or [] if n]
    return any(all(re.search(r'\b' + re.escape(word.casefold()[:max(3, len(word) - 2)]), text) for word in (row[0], row[-1]))
               for row in [*rows, str(person.get('name') or '').split()] if len(row) > 1)


def protected_names(instance, *, include_short=False):
    """Match names of people still protected, including alternate written forms and name order."""
    from familiar.checks.engine import _known_people, life_status
    living, historical = set(), set()
    for person in _known_people(instance).values():
        forms = historical if life_status(person, {}) == 'dead' else living
        shown = person.get('namePresentation') or {}
        values = [person.get('name'), shown.get('full'), *(shown.get('byLanguage') or {}).values()]
        for row in person.get('names') or []:
            given, patronymic, surname = row.get('given'), row.get('patronymic'), row.get('surname')
            values.append(row.get('display'))
            if given and surname:
                values.extend((f'{given} {surname}', f'{surname} {given}',
                               ' '.join(filter(None, (surname, given, patronymic)))))
            if include_short and given and patronymic:
                values.extend((f'{given} {patronymic}', f'{patronymic} {given}'))
        for value in values:
            if not isinstance(value, str) or not value.strip():
                continue
            bits = tuple(re.findall(r'[^\W\d_]+', value.casefold()))
            if len(bits) >= 2:
                forms.add(bits)
                if len(bits) > 2:
                    forms.add((bits[0], bits[-1]))
                    if include_short:
                        forms.add(bits[:2])
    patterns, historical_stems = set(), {tuple(w[:-2] for w in bits) for bits in historical}
    for bits in living - historical:
        patterns.add(r'[\W_]+'.join(map(re.escape, bits)))
        stems = tuple(w[:-2] for w in bits)
        if stems not in historical_stems and all(re.fullmatch(r'[а-яё]{4,}', w) for w in bits):
            patterns.add(r'[\W_]+'.join(re.escape(w) + r'[а-яё]{1,4}' for w in stems))
    return re.compile(r'(?<!\w)(?:' + '|'.join(sorted(patterns)) + r')(?!\w)' if patterns else r'(?!)', re.I)


def attribute_documents(instance, graph, *, family_display=False):
    """Add contextual subjects to every shared document route, without changing inputs.

    Resource identities join only structured references, never titles or prose.
    A shared scan inherits all its uses, including protected gallery owners.
    Literal excerpts remain separate from the full record's identity.
    """
    from familiar.checks.engine import _known_people, life_status, load
    from .gate import shared
    known, privacy = _known_people(instance, family_display=family_display), load(instance.path('privacy'), {})
    stated = {}
    record_paths = {normalized(p.stem): p for p in instance.path('records').rglob('*.json')}
    parents, subjects, uses, protected = {}, {}, [], set()
    mentioned = None if family_display else shared(
        instance, 'public-protected-names', lambda: protected_names(instance, include_short=True))
    paper_safety = {}

    def blocked_record(rid, record):
        if protected_record(record):
            return True
        if family_display or record.get('excerpt'):
            return False
        if rid not in paper_safety:
            paper_safety[rid] = unreviewed_group(record) or bool(mentioned.search(written({}, record)))
        return paper_safety[rid]

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

    def document(node, shape, context=(), sid=None, *, chapter=False):
        from .restorations import period_pair

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
        value = dict(node, kind='archive-record') if shape == 'source' and node.get('record') in record_paths else node
        resolved = closure(instance, value, shape=shape, people=known)
        if 'excerpt' not in node and (record := resolved.records.get(node.get('record'))):
            from familiar.reader.scans import selected_capture
            _, capture = selected_capture(instance, record)
            if capture:
                keys.append(('capture', capture))
        if shape in {'document', 'image'} and node.get('subjects') and not node.get('_document_attributed') and node.get('record') in resolved.records:
            actual = closure(instance, {'record': node['record'], **({'excerpt': node['excerpt']} if 'excerpt' in node else {})}, shape=shape, people=known).people
            declared = {known[p].get('id', p) for p in node['subjects']}
            if actual and declared != actual:
                raise ValueError('TRUST-06: declared subjects disagree with corpus record: ' + node['record'])
        if shape == 'source' and sid and 'excerpt' not in node and complete_subjects(resolved.records.get(node.get('record'), {})):
            stated[sid] = written(node, resolved.records[node['record']])
        # The checked period frame already identifies who is pictured independently of the story.
        use_context = not chapter or not (node.get('subjects') or shape == 'image' and period_pair(node)
                                          or family_display and historical_records(resolved))
        people = resolved.people | (set(context) if use_context else set())
        key = bind(keys, people)
        if any(blocked_record(rid, data) for rid, data in resolved.records.items()):
            node['_document_private'] = True
            if key is not None:
                protected.add(key)
        uses.append((node, key, people))

    sources = graph.get('sources', {})
    manifest = load(instance.path('media') / 'manifest.json', {})
    attached = {row['source_id'] for row in manifest.get('assets', []) if row.get('source_id') and row.get('export')}
    attached.update(image[key] for person in graph.get('people', {}).values() for field in ('media', 'illustrations')
                    for image in person.get(field, []) if image.get('asset') for key in ('sid', 'sourceSid') if image.get(key))
    tellings = {sid for sid, source in sources.items()
                if family_display and fileless_memory(source) and sid not in record_paths and sid not in attached}

    def cite(sid, people, *, inference=False):
        if sid in tellings:
            return
        alias = sources.get(sid, {}).get('record', sid)
        if inference and sid not in stated and alias in record_paths:
            record = load(record_paths[alias], {})
            if complete_subjects(record):
                stated[sid] = written(sources.get(sid, {}), record)
        if inference and sid in stated:
            people = {p for p in people if life_status(known.get(p, {'id': p}), privacy) == 'dead'
                      or names(stated[sid], known.get(p, {}))}
        if sources.get(sid, {}).get('excerpt'):
            bind([('source', sid)], people)
        else:
            bind([('source', sid)] + ([('record', alias)] if alias in record_paths else []), people)

    def fact(row, context, own=()):
        people = set(context) | set(row.get('_people', row.get('people', [])))
        if row.get('record'):
            document(row, 'fact', people)
        for sid in row.get('sources', []):
            cite(sid, people, inference=sid not in own and infers(row))

    def story(node, context=()):
        people = node.get('_people', node.get('people', context))
        for row in node.get('records', []):
            document(row, 'document', people, chapter=True)
        for collection in ('picture', 'figures'):
            values = node.get(collection, [])
            for image in values if isinstance(values, list) else [values]:
                if isinstance(image, dict):
                    photo_pair(instance, image)
                if isinstance(image, dict) and (image.get('record') or image.get('kind') == 'document-scan' or image.get('photo') is False):
                    document(image, 'image', people, chapter=True)
        for row in node.get('facts', []):
            fact(row, people)
        for child in node.get('extras', []) + node.get('chapters', []):
            story(child, people)

    for sid, source in sources.items():
        if not source.get('record') and sid in record_paths:
            source['record'] = sid
        if sid not in tellings:
            document(source, 'source', sid=sid)
    for row in manifest.get('assets', []):
        if row.get('source_id') and row.get('export'):
            sid = row['source_id']
            bind([('source', sid), ('asset', '/' + row['export'].lstrip('/'))]
                 + ([('record', sid)] if sid in record_paths else []), ())
    for pid, person in graph.get('people', {}).items():
        for collection in ('media', 'illustrations'):
            for image in person.get(collection, []):
                photo_pair(instance, image)
                if image.get('record') or image.get('kind') == 'document-scan' or image.get('photo') is False:
                    document(image, 'image', [pid])
        own = own_papers(person)
        if life_status(known.get(pid, {'id': pid}), privacy) != 'dead':
            for sid in own:
                cite(sid, {pid})
            for row in person.get('notes', []):
                for sid in [*(row.get('sources') or []), *(row.get('provenance') or [])]:
                    cite(sid, {pid})
        for row in person.get('facts', []):
            fact(row, [pid], own)
        # A retired fact stays on record, but its papers are no longer papers about this person:
        # a namesake's sheet must not sit among the documents of the card it was once tried on.
        for row in person.get('retiredFacts', []):
            fact(row, [])
    from familiar.tree.life import attributed_link, relation_people
    for relation in [*graph.get('edges', []), *graph.get('associations', []), *graph.get('families', [])]:
        if not attributed_link(relation):
            continue
        members = {p for p in relation_people(relation) if life_status(known.get(p, {'id': p}), privacy) != 'dead'}
        if not members:
            continue  # A citation can protect a sheet, but cannot establish all its subjects.
        for sid in [*relation.get('sources', []), *relation.get('provenance', [])]:
            cite(sid, members, inference=relation.get('derived') is True or relation.get('status') in {'hypothesis', 'possible', 'probable'})
        for event in relation.get('events', []):
            for sid in [*event.get('sources', []), *event.get('provenance', [])]:
                cite(sid, members)
    for feed in graph.get('feeds', []):
        story(feed)
    for node, key, people in uses:
        # Facts carry context to sources, but their subjects are not reader fields.
        if key is not None:
            people |= subjects[root(key)]
            if any(root(k) == root(key) for k in protected):
                node['_document_private'] = True
        node['subjects'] = sorted(people)
        node['_document_attributed'] = True
    from .restorations import restorations
    if any(restorations(graph)):
        closure(instance, graph, shape='graph', people=known)
    private = {root(key) for key in protected}
    return {key for key in parents if root(key) in private or any(
        life_status(known.get(p, {'id': p}), privacy) != 'dead' for p in subjects[root(key)])}
