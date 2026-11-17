# START_MODULE_CONTRACT: MOD-CHECKS-PRIVACY
# PURPOSE: Resolve every structured chapter participant and exclude protected documents and generated images.
# PRD_REF: docs/PRD.md#TRUST
# INVARIANTS:
# - subjects outside chapter.people cannot bypass privacy [test: tests/gate/test_data_guarantees.py::test_f2_record_subject_cannot_be_omitted]
# - nested and cover images obey the same prohibitions [test: tests/gate/test_data_guarantees.py::test_f6_reconstruction_cannot_be_a_portrait]
# - withheld living documents advise without granting their publication [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION
# - MOD-CHECKS-ENGINE
# - MOD-SUBJECT-CLOSURE
# :END_MODULE_CONTRACT


def _violations(chapter, refs, pics, documents, instance, people, pictures=None):
    from familiar.instance.subjects import closure

    from .engine import generated, life_status, load
    privacy = load(instance.path('privacy'), {})
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
        if status != 'dead':
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
                                  '. Separate literal fields about deceased people.')
