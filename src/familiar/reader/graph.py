# START_MODULE_CONTRACT: MOD-READER-GRAPH
# PURPOSE: Adapt attributed family snapshots and current feed catalogs to the reader's ordered graph.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - a one-person family and the fictional family's chapters need no pilot defaults [review: engine lead]
# - tentative card details cannot replace a sourced event [review: engine lead]
# - reader cards retain names and claims unified by a cross-intake identity decision [review: engine lead]
# - superseded claims retain their retirement explanation through reader projection [review: engine lead]
# - narrator kin words, inferred name parts and event-kind uncertainty survive as distinct, attributed reader surfaces [review: engine lead]
# - generated intake notices use the family language pack without rewriting family prose [review: engine lead]
# - prose and date adaptation use current normalized fields and directly cited sources without per-person disk reads [review: engine lead]
# CHANGES_WITH:
# - MOD-LANGUAGE-RU (reader_intake notice keys, also supplied by other language packs)
# - MOD-PUBLICATION (declared reader surfaces and default-deny policy)
# - MOD-FAMILY-WRITER (the sole filesystem and generation boundary)
# - MOD-FEED-SERVICE (materialization supplies the exact reviewed reader bytes)
# - docs/reader-export.md
# :END_MODULE_CONTRACT
import copy
import hashlib
import json

from familiar.feeds.service import _materialize, folders
from familiar.tree.builder import _build, read_json


def intake_prose(instance, graph):
    """Present stored intake assertions; keep originals and provenance untouched."""
    from familiar.instance.memory_visibility import select
    memories = {}
    for _, memory in select(instance)[0]:
        for item in memory.get('items', []):
            memories[item['id']] = (memory, item)
    records = {r.get('id'): r for path in instance.path('records').rglob('*.json')
               if (r := read_json(path, {}))}
    wording = instance.language_pack_data.get(instance.source_language, {}).get('data', {}).get('reader_intake', {})
    if instance.source_language == 'en' and 'en' not in instance.language_pack_data:
        # English is the initial instance language, with no explicit pack mapping.
        from familiar.instance.packs import bundled_root, read
        wording = read(bundled_root() / 'demo-english' / 'pack.toml')['reader_intake']
    for collection in ('updates', 'highlights'):
        for update in graph.get('research', {}).get(collection, []):
            if update.get('title') != 'Family intake':
                continue
            kinds = {graph.get('sources', {}).get(sid, {}).get('kind') for sid in update.get('sources', [])}
            kind = next(iter(kinds)) if len(kinds) == 1 else None
            if kind not in wording:
                # A missing translation is a pack gap, never English reader prose.
                raise ValueError(f'Language pack gap ({instance.source_language}): reader_intake.{kind}')
            update['text'] = wording[kind]
    graph['readerLabels'] = {key: wording[key] for key in (
        'unknownName', 'familyFirm', 'familyUncertain', 'derivedVersion',
        'basisLabel', 'spouseVersion', 'storiesEmpty', 'deathEvent', 'deathCause',
        'graphKinship', 'inferredNameParts', 'placeEventUnknown') if key in wording}
    labels = {'names': wording.get('name_label'), 'notes': wording.get('notes_label'), 'events': wording.get('event_label')}
    aliases = graph.get('identityAliases', {})
    for sid, (memory, item) in memories.items():
        pid = aliases.get(item.get('person'), item.get('person'))
        if pid not in graph['people']:
            continue
        kin = item.get('kinship') or (item.get('text', '').partition(' - ')[2]
              if item.get('role') == 'person_kin' else item.get('text') if item.get('role') == 'kin' else '')
        viewer = memory.get('narrator') or graph.get('narrator')
        viewer = aliases.get(viewer, viewer)
        if kin and viewer in graph['people']:
            row = {'viewer': viewer, 'text': kin, 'sources': [sid]}
            if row not in graph['people'][pid].setdefault('reportedKinship', []):
                graph['people'][pid]['reportedKinship'].append(row)
        source = graph.get('sources', {}).get(sid)
        if source is not None:
            witness = item.get('witness') or memory.get('told_by', '')
            if witness in graph['people']:
                from familiar.instance.publication import confirmed_name
                witness = confirmed_name(graph['people'][witness]) or wording['narratorLabel']
            if witness.casefold() in {'operator', 'оператор', 'host', 'intake', 'researcher'}:
                witness = wording['narratorLabel']
            source['title'] = (wording['familyFirm'] if witness == wording['narratorLabel'] else
                               wording['memorySource'].format(witness=witness, date=memory.get('date', '')))
    for sid, source in graph.get('sources', {}).items():
        record = records.get(source.get('record', sid))
        if record:
            source.setdefault('title', record.get('title', ''))
    for pid, person in graph['people'].items():
        sids = {sid for fact in person.get('facts', []) for sid in fact.get('sources', [])}
        sources = {sid: graph.get('sources', {}).get(sid, {}) for sid in sids}
        linked = {s.get('record', sid) for sid, s in sources.items()} | sids
        docs = {rid: records[rid] for rid in linked if rid in records}
        telling = {sid: memories[sid][1] for sid in sids if sid in memories}
        graph['people'][pid] = _intake_person(person, sources, docs, telling, wording, labels)


def _intake_person(person, source_map, records, telling, wording, labels):
    graph = {'sources': source_map}
    memories = {sid: (None, item) for sid, item in telling.items()}
    for fact in person.get('facts', []):
        sources = [graph.get('sources', {}).get(sid, {}) for sid in fact.get('sources', [])]
        memory_items = [memories[sid][1] for sid in fact.get('sources', []) if sid in memories]
        # A saved copy of the family's own answer carries the telling; it is not a document about the person.
        carriers = {i['original'] for i in memory_items if i.get('original')}
        documents = [records[s.get('record', sid)] for sid, s in zip(fact.get('sources', []), sources)
                     if s.get('record', sid) in records
                     and (records[s.get('record', sid)].get('source') or {}).get('locator') not in carriers]
        if not documents and (memory_items or any(s.get('kind') == 'memory' for s in sources)):
            fact['testimony'] = 'uncertain' if (fact.get('status') in {'hypothesis', 'conflict'} or
                any(item.get('strength') == 'hearsay' for item in memory_items)) else 'firm'
        field = fact.get('label')
        if labels.get(field):
            fact['label'] = labels[field]
        if documents:
            fact.pop('testimony', None)
            if field in {'document', 'notes'}:
                fact['label'] = documents[0].get('title', '')
        if fact.get('derived') and field == 'notes':
            fact['detailOnly'] = True  # Generated reasoning stays outside the ordinary card view.
        event_type = fact.get('eventType') or next((i.get('role') for i in memory_items
                     if i.get('role') in {'birth', 'death', 'birth_place', 'death_place'}), None)
        if field == 'events' and event_type:
            fact['eventType'] = event_type.removesuffix('_place')
            event_label = wording.get(fact['eventType'], wording.get('event_label', ''))
            fact['label'] = event_label
        if memory_items and all(i.get('role') == 'place' and not i.get('derived') for i in memory_items):
            fact['uncertainty'] = 'event-kind'
            fact['label'] = wording['placeEventUnknown']
            if all(i.get('strength') == 'firm' and i.get('status') != 'possible' for i in memory_items):
                fact.update(status='export', testimony='firm')
        if not (any(s.get('kind') in {'memory', 'home-paper', 'gedcom'} for s in sources)
                or any(sid in records for sid in fact.get('sources', []))):
            continue
        try:
            claim = json.loads(fact.get('text', ''))
        except (ValueError, TypeError):
            continue
        if not isinstance(claim, dict):
            continue
        if field == 'names':
            text = ' '.join(str(claim[k]) for k in ('given', 'patronymic', 'surname', 'married_name') if claim.get(k))
        elif field == 'events':
            fact['eventType'] = claim.get('type')
            event_label = wording.get(claim.get('type'), wording.get('event_label', ''))
            fact['label'] = event_label
            text = ' · '.join(str(claim[k]) for k in ('date', 'place', 'value', 'note', 'text', 'cause') if claim.get(k))
        elif field == 'notes':
            text = claim.get('text') or claim.get('plain', '')
        else:
            continue
        if not text:
            continue
        attribution = [wording['paper_label'].format(title=records[sid].get('title', ''))
                       for sid in fact.get('sources', []) if sid in records]
        fact['text'] = text + ('. ' + '; '.join(dict.fromkeys(attribution)) if attribution else '')
    return person




def card_dates(people, evidence):
    for pid, person in people.items():
        people[pid] = _card_dates(pid, person, evidence)


def _card_dates(pid, person, evidence):
    facts = evidence.get(pid, {}).get('facts', [])
    trusted = [f for f in facts if f.get('status') in ('verified', 'export') and f.get('sources')]
    details, weak = {}, set()
    for fact in facts:
        if fact not in trusted:
            weak.update(fact.get('card_details', {}))
    for fact in trusted:
        details.update(fact.get('card_details', {}))
        if correction := fact.get('event_correction'):
            events = person.setdefault('events', [])
            event = next((e for e in events if e.get('tag') == correction['tag']), None)
            if event is None:
                event = {}
                events.append(event)
            event.update(copy.deepcopy(correction))
            event['sources'] = fact['sources']
    cp = person.setdefault('cardPresentation', {})
    events = person.get('events', [])
    for field, tag in (('birth', 'BIRT'), ('death', 'DEAT')):
        event = next((e for e in events if e.get('tag') == tag), {})
        if field in details:
            cp.update({field: details[field], field + 'Kind': 'source'})
        elif field in weak:
            cp[field] = event.get('date', '')
    if 'place' in details:
        cp.update(place=details['place'], placeRole=details.get('place_role', 'record'))
    elif 'place' in weak:
        event = next((e for e in events if e.get('tag') == 'BIRT'), {})
        cp.update(place=event.get('place', ''), placeRole='birth' if event.get('place') else '')

    return person


def _assemble(instance, *, for_review=False, host_private=False):
    graph = _build(instance, family_display=host_private)
    errors = graph.get('research', {}).get('contributions', {}).get('errors', [])
    if errors:
        raise ValueError('contribution errors prevent reader export')
    evidence = copy.deepcopy(graph['people'])
    # Use the builder's finalized families; rereading the snapshot would undo
    # identity/correction work. Reinsert only to preserve serialization order.
    graph['families'] = graph.pop('families', [])
    graph.pop('familyCorrections', None)
    metadata = read_json(instance.path('tree_metadata'), {})
    graph.setdefault('root', metadata.get('root') or next(iter(graph['people']), None))
    if not graph.get('root'):
        graph['root'] = next(iter(graph['people']), None)
    graph.setdefault('cardStatuses', {})
    from familiar.rules.roles import method_root
    from familiar.rules.cascade import Registry
    if Registry(method_root() / 'rules', instance).resolve_setting('tree.import_is_family_memory').value:
        # The tree the narrator kept is the family's own memory; research additions are not.
        for status in graph['cardStatuses'].values():
            if status.get('in_original_tree'):
                status['family_memory'] = True
    graph['feeds'] = []
    for folder in folders(instance):
        feed, _ = _materialize(instance, folder)
        graph['feeds'].append(feed)
    from familiar.reader.experiences import play, world
    play(instance, graph)
    world(instance, graph, host_private=host_private)
    intake_prose(instance, graph)
    for person in graph['people'].values():
        for key in ('identityHistory', 'working'):
            person.pop(key, None)
        for fact in person.get('facts', []):
            fact.pop('_contribution_file', None)
            fact['eventKey'] = hashlib.sha256(json.dumps([fact.get('label'), fact.get('text'), fact.get('sources')], ensure_ascii=False).encode()).hexdigest()[:24]
    card_dates(graph['people'], evidence)
    from familiar.instance.publication import restrict_graph
    graph = restrict_graph(instance, graph, host_private=host_private)
    # after the restriction: hidden dates cannot anchor a guess, protected people receive none
    from familiar.tree.birth_guess import apply as guess_births
    guess_births(instance, graph, host_private=host_private)
    for key in ('originalPeople', 'originalEdges', 'workingVersion', 'gallerySelection', 'distinct', 'plan', 'validation', 'context'):
        graph.pop(key, None)
    return graph


def _protect_people(instance, graph):
    """The tree also obeys name-and-kinship disclosure, not just feed prose."""
    from familiar.instance.publication import restrict_graph
    restrict_graph(instance, graph)
