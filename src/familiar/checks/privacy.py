# START_MODULE_CONTRACT: MOD-CHECKS-PRIVACY
# PURPOSE: Resolve every structured chapter participant and enforce living-person publication permissions.
# PRD_REF: docs/PRD.md#TRUST
# INVARIANTS:
# - merged participants retain their recorded publication permissions [review: engine lead]
# - subjects outside chapter.people cannot bypass privacy [test: tests/gate/test_data_guarantees.py::test_f2_record_subject_cannot_be_omitted]
# - nested and cover images obey the same prohibitions [test: tests/gate/test_data_guarantees.py::test_f6_reconstruction_cannot_be_a_portrait]
# - withheld living documents and pictures advise without granting their publication [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION
# - MOD-CHECKS-ENGINE
# - MOD-SUBJECT-CLOSURE
# :END_MODULE_CONTRACT


def _violations(chapter, refs, pics, documents, instance, people, pictures=None):
    from familiar.instance.subjects import closure

    from .engine import generated, life_status, load
    privacy = load(instance.path('privacy'), {})
    from familiar.instance.publication import allowed as recorded_permissions
    def permissions(person):
        return recorded_permissions(privacy, person)
    try:
        resolved = closure(instance, dict(chapter, figures=pics, picture=None), documents=documents, pictures=pictures, people=people)
    except ValueError as exc:
        yield 'people.subjects', str(exc)
        return
    participants = resolved.people
    # Structured people in mini-trees, clans, generation strips and images count too.
    pics = resolved.images
    for symbol in participants:
        person = people.get(symbol, {'id': symbol})
        status = life_status(person, privacy)
        if status == 'unknown':
            yield f'people[{person.get("id", symbol)}].unknown', f'Life status unknown: {person.get("name", symbol)}; review dates or privacy classification.'
        if status != 'dead':
            declared = chapter.get('published_fields', {})
            projection = declared.get(symbol, declared.get(person.get('id')))
            if projection is None:
                projection = next((v for k, v in declared.items() if people.get(k, {}).get('id') == person.get('id')), None)
            if projection is None:
                # A newly discovered living participant must not silently widen disclosure.
                yield 'people.subjects-unknown', 'Living participant has no declared publication fields; review prose.'
                projection = []
            for field in projection:
                from familiar.instance.publication import INFO_FIELDS
                if field not in INFO_FIELDS:
                    yield 'people', f'Living person {field} is excluded regardless of consent.'
                elif field not in {'name', 'kinship'} and field not in permissions(person):
                    yield 'people.permission-review', f'Living person {field} is omitted without recorded consent; review prose for this information.'
                # Ordinary unpermitted structured fields are removed by projection;
                # the meaning of prose is the independent reader's R1 worklist.
            for ref in refs:
                doc = documents.get(ref.get('doc'), {})
                if 'subjects' not in doc:
                    yield 'records.subjects-unknown', 'Document subjects undeclared; review required.'
                elif person.get('id') in {people.get(x, {'id': x}).get('id') for x in doc['subjects']}:
                    yield 'records.omitted', 'Living person document is withheld: ' + str(ref.get('doc'))
            if any('subjects' not in p for p in pics):
                yield 'picture.subjects-unknown', 'Picture subjects undeclared beside a living person; association is unverified.'
    by_id = {p.get('id'): p for p in people.values()}
    for n, pic in enumerate(pics):
        for symbol in pic.get('subjects', []):
            person = people.get(symbol, by_id.get(symbol))
            if person is None:
                yield f'picture[{n}].subjects', 'Unknown picture subject; resolve the canonical person ID.'
                continue
            status = life_status(person, privacy)
            if status == 'unknown':
                yield f'picture[{n}].subjects.unknown', 'Picture subject life status unknown.'
            if status != 'dead' and 'pictures' not in permissions(person):
                yield f'picture[{n}].omitted', 'Living picture subject has no recorded picture permission: ' + str(pic.get('asset'))
            if generated(pic) and status != 'dead':
                yield f'picture[{n}]', 'Generated image uses a living person as subject.'
        if generated(pic) and (pic.get('subject_living') or pic.get('subject_child')):
            yield f'picture[{n}]', 'Generated image uses a living person or child as subject.'
    # Document subjects are independent of an author's chapter.people list.
    for rid, record in resolved.records.items():
        from familiar.instance.subjects import explicit_subjects
        if record.get('privacy') in {'living', 'living-possible'}:
            yield 'records.omitted', 'Living or possibly living corpus records are withheld.'
        for symbol in explicit_subjects(record):
            person = people.get(symbol, by_id.get(symbol))
            if person is None:
                yield 'records.subjects', 'Unknown document subject; resolve the canonical person ID.'
            elif life_status(person, privacy) != 'dead':
                yield 'records.omitted', ('Living person document is withheld: ' + rid + '; ' + str(record.get('title', '')) +
                                  '; protected subject: ' + str(person.get('name', symbol)) +
                                  '. Separate literal fields about deceased people; consent cannot release this full document.')
