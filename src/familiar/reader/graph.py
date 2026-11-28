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
# - a possible identity lends dates and papers only when both cards are deceased and the found card can show those details [test: tests/gate/test_data_guarantees.py::test_only_recorded_events_open_a_card]
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
import re

from familiar.feeds.service import _materialize, folders
from familiar.tree.builder import _build, read_json
from familiar.tree.identities import DRAWN_LINK


FOREIGN_CLAIM = 'Recorded in another tree (unverified): '
WORKSHOP = re.compile(r'\b(?:HTTP\s+[1-5]\d\d|recordsFiltered|локальн\w*\s+проверк\w*|'
                      r'(?:(?:официальн\w*|архивн\w*)\s+)?опись\s*(?:\d+|содержит)|'
                      r'local check|local verification)\b', re.IGNORECASE)


def _workshop(value):
    return isinstance(value, str) and WORKSHOP.search(value)

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
                fact['_paper_heading'] = documents[0]['id']
        if fact.get('derived') and field == 'notes':
            fact['detailOnly'] = True  # Generated reasoning stays outside the ordinary card view.
        if isinstance(field, str) and not fact.get('eventType'):
            # Older family cards used a life-event heading with a version suffix.
            heading = field.partition(' · ')[0]
            if kind := next((k for k in ('birth', 'death') if wording.get(k) == heading), None):
                fact['eventType'] = kind
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
        if any(i.get('role') == 'note' and i['text'] == fact.get('text') for i in memory_items):
            continue  # An archive note is literal, even if it looks like a JSON claim.
        if not (any(s.get('kind') in {'memory', 'home-paper', 'gedcom'} for s in sources)
                or any(sid in records for sid in fact.get('sources', []))):
            continue
        raw = fact.get('text', '')
        if isinstance(raw, str) and raw.startswith(FOREIGN_CLAIM):
            # Intakes before 0.41.1 prefixed another tree's claims. The dotted status and the
            # source already say whose claim it is; the family reads the claim itself.
            raw = fact['text'] = raw[len(FOREIGN_CLAIM):]
        if fact.get('status') == 'hypothesis' and sources and all(s.get('kind') == 'gedcom' for s in sources):
            # What only another tree says is a version for the investigation, not a line of the card.
            fact['detailOnly'] = True
        try:
            claim = json.JSONDecoder().raw_decode(raw)[0]
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
        fact['text'] = text
        if any(sid in records for sid in fact.get('sources', [])):
            fact['_paper_attribution'] = wording['paper_label']
    return person


def paper_attribution(graph):
    """Only sources surviving the reader's document projection supply titles."""
    sources = graph['sources']
    for person in graph['people'].values():
        for fact in person.get('facts', []):
            heading = fact.pop('_paper_heading', None)
            wording = fact.pop('_paper_attribution', None)
            if not (heading or wording):
                continue
            shown = [sources[sid] for sid in fact.get('sources', [])
                     if sid in sources and sources[sid].get('record') and isinstance(sources[sid].get('title'), str)]
            if heading:
                if title := next((s['title'] for s in shown if s['record'] == heading), ''):
                    fact['label'] = title
            if wording:
                labels = dict.fromkeys(wording.format(title=s['title']) for s in shown
                                       if s['record'] in fact['sources'] and s['title'])
                if labels:
                    fact['text'] += '. ' + '; '.join(labels)




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


def _assemble(instance, *, for_review=False, host_private=False, paper_words=None):
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
    if not host_private:
        from familiar.feeds.flow import require_finished
        require_finished(graph['feeds'])
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
    graph = restrict_graph(instance, graph, host_private=host_private, paper_words=paper_words)
    for person in graph['people'].values():
        if person.get('living') is False:
            if _workshop(person.get('summary')):
                person.pop('summary')
            for fact in person.get('facts', []):
                if not fact.get('eventType') and (_workshop(fact.get('label')) or _workshop(fact.get('text'))):
                    fact['detailOnly'] = True
    # after the restriction: hidden dates cannot anchor a guess, protected people receive none
    from familiar.tree.birth_guess import apply as guess_births
    guess_births(instance, graph, host_private=host_private)
    translate_cards(instance, graph)
    for key in ('originalPeople', 'originalEdges', 'workingVersion', 'gallerySelection', 'distinct', 'plan', 'validation', 'context'):
        graph.pop(key, None)
    return graph


def show_probable_identities(graph):
    """Coalesce the family display after life assessment and document delivery."""
    people, sources = graph['people'], graph['sources']
    candidates = [(pid, match) for pid, person in people.items() if not person.get('placeholder')
                  for match in person.get('probableIdentities', [])
                  if match['weight'] >= DRAWN_LINK and match['alias'] in people]
    aliases, selected = {}, {}
    # Keep one leading card per group. An accepted alias is resolved upstream;
    # an ambiguous chain of probable junctions does not silently collapse.
    for pid, match in sorted(candidates, key=lambda pair: -pair[1]['weight']):
        alias = match['alias']
        if alias == pid or pid in aliases or alias in aliases or alias in selected:
            continue
        aliases[alias] = pid
        selected.setdefault(pid, []).append(match)
    if not aliases:
        return
    for pid, matches in selected.items():
        for match in matches:
            other = people[match['alias']]
            match.pop('card', None)
            if people[pid].get('living') is not False or other.get('living') is not False:
                match.pop('basis', None)
                match.pop('sources', None)
            if people[pid].get('living') is False:
                if other.get('living') is False:
                    match['card'] = _possible_card(other, sources)
                elif facts := _possible_claims(other, match['weight']):
                    match['card'] = {'facts': facts}
    _present_kinship(graph, aliases, {m['alias']: m['weight'] for rows in selected.values() for m in rows})
    graph['presentationAliases'] = aliases
    for alias in aliases:
        people.pop(alias)
        graph.get('cardStatuses', {}).pop(alias, None)

def _possible_claims(person, weight):
    # The family can read the person's already filtered claims. A possible
    # double carries the words alone; an attached closed paper stays on its side.
    return [dict(text=fact['text'], label=fact.get('label', ''), status='hypothesis',
                 weight=min(weight, fact.get('weight') if fact.get('weight') is not None else 1))
            for fact in person.get('facts', [])
            if fact.get('text') and not any(fact.get(k) for k in ('detailOnly', 'record', 'eventType'))
            and fact.get('scope') != 'search'
            and (fact.get('weight') is None or fact['weight'] >= DRAWN_LINK)]


def _possible_card(person, sources):
    # The source table is already restricted and document paths bound. A stub
    # has no title, image or paper and cannot travel through a different card.
    visible = lambda sid: any(sources.get(sid, {}).get(k) for k in ('title', 'asset', 'image'))
    refs = lambda row: [*(row.get('sources') or []), *(row.get('provenance') or [])]
    displayable = lambda row: not row.get('record') or visible(row['record']) or any(map(visible, refs(row)))
    events = [e for e in person.get('events', []) if all(map(visible, refs(e)))]
    facts = [f for f in person.get('facts', []) if displayable(f) and all(map(visible, refs(f)))
             and not f.get('detailOnly') and (f.get('weight') is None or f['weight'] >= DRAWN_LINK)]
    card = {}
    for key, tag in (('birth', 'BIRT'), ('death', 'DEAT')):
        events_of_kind = [e for e in person.get('events', []) if e.get('type') == key or e.get('tag') == tag]
        # An attributed event's protected sources cannot be bypassed by its card heading.
        if all(event in events for event in events_of_kind):
            date = person.get('cardPresentation', {}).get(key) or next(
                (e['date'] for e in events_of_kind if e.get('date') and e.get('status') != 'hypothesis'), '')
            if date and date.casefold() not in {'unknown', '?'}:
                card[key] = date
    papers = {sid: None for row in [*facts, *events, *person.get('names', []), *person.get('notes', [])]
              for sid in refs(row) if visible(sid)}
    papers.update({sid: None for sid, source in sources.items() if person['id'] in (source.get('subjects') or ()) and visible(sid)})
    media = [m for m in person.get('media', []) if m.get('asset') and not m.get('photo')
             and m.get('kind') != 'photo-restoration' and (m.get('ours') or {}).get('kind') != 'photo-restoration']
    other_events = [e for e in events if not {e.get('type'), e.get('tag')} & {'birth', 'death', 'BIRT', 'DEAT'}]
    names = [n.get('display') or ' '.join(n[k] for k in ('given', 'patronymic', 'surname') if n.get(k))
             for n in person.get('names', []) if all(map(visible, refs(n)))]
    if not person.get('names') and (written := (person.get('namePresentation') or {}).get('sourceName')):
        names.append(written)
    return {**card, 'summary': person.get('summary', ''), 'names': list(dict.fromkeys(filter(None, names))),
            'facts': facts, 'events': other_events, 'papers': list(papers), 'media': media}


def _present_kinship(graph, aliases, weights):
    for pid, person in graph['people'].items():
        if guess := person.get('birthGuess'):
            for anchor in guess['anchors']:
                anchor['id'] = aliases.get(anchor['id'], anchor['id'])
            if any(anchor['id'] == pid for anchor in guess['anchors']):
                person.pop('birthGuess')
    for key in ('root', 'narrator', 'defaultViewer'):
        if graph.get(key) in aliases:
            graph[key] = aliases[graph[key]]
    for collection, first, second in (('edges', 'child', 'parent'), ('associations', 'from', 'to')):
        seen, kept, pending = set(), [], []
        for row in graph.get(collection, []):
            key = (row.get(first), row.get(second), row.get('role') or row.get('type'))
            if key[0] in aliases or key[1] in aliases:
                pending.append(row)
            else:
                kept.append(row)
                seen.add(key)
        for row in pending:
            weight = min([row.get('weight') if row.get('weight') is not None else 1.0,
                          *(weights[row[k]] for k in (first, second) if row.get(k) in weights)])
            moved = {k: aliases.get(v, v) if k in ('child', 'parent', 'from', 'to') else v for k, v in row.items()}
            key = (moved.get(first), moved.get(second), row.get('role') or row.get('type'))
            if key[0] != key[1] and key not in seen and row.get('status') not in {'rejected', 'disproved', 'conflict'}:
                kept.append(moved | {'status': 'hypothesis', 'weight': weight})
                seen.add(key)
        graph[collection] = kept
    for family in graph.get('families', []):
        changed = [pid for pid in (family.get('husband'), family.get('wife'), *family.get('children', [])) if pid in aliases]
        if not changed:
            continue
        for key in ('husband', 'wife'):
            if family.get(key) in aliases:
                family[key] = aliases[family[key]]
        spouses = {family.get('husband'), family.get('wife')}
        family['children'] = list(dict.fromkeys(aliases.get(pid, pid) for pid in family.get('children', [])))
        family['children'] = [pid for pid in family['children'] if pid not in spouses]
        if family.get('status') not in {'conflict', 'rejected', 'disproved'}:
            own = family.get('weight') if family.get('weight') is not None else 1.0
            family.update(status='hypothesis', weight=min([own, *(weights[pid] for pid in changed)]))


def card_memory(instance):
    """{language: {exact main-language text: translation}} from tree/translations/<lang>.json."""
    memory = {}
    for lang in instance.languages:
        if lang != instance.source_language:
            data = read_json(instance.path('translations') / f'{lang}.json', {})
            texts = data.get('texts') if isinstance(data, dict) else None
            if isinstance(texts, dict):
                memory[lang] = {k: v for k, v in texts.items() if isinstance(v, str) and v.strip()}
    return {lang: texts for lang, texts in memory.items() if texts}


def translate_cards(instance, graph):
    """Card texts in the family's other languages (docs/language-checks.md#card-translations).

    `tree/translations/<lang>.json` holds `texts`: an exact source-language text and its translation. A matching
    field becomes a language row; a changed source text shows the family's language until translated again.
    """
    memory = card_memory(instance)

    def one(value, lang):
        hit = memory[lang].get(value.strip())
        if hit is None and ' · ' in value:  # a generated "date · place" line: translate its parts
            parts = [memory[lang].get(part.strip(), part) for part in value.split(' · ')]
            hit = ' · '.join(parts) if parts != value.split(' · ') else None
        return hit

    def row(value):
        if not memory or not isinstance(value, str) or not value.strip():
            return value
        hits = {lang: hit for lang in memory if (hit := one(value, lang))}
        return {instance.source_language: value, **hits} if hits else value

    for person in graph['people'].values():
        for key in ('summary',):
            if key in person:
                person[key] = row(person[key])
        for fact in person.get('facts', []) + person.get('retiredFacts', []):
            for key in ('label', 'text', 'basis'):
                if key in fact:
                    fact[key] = row(fact[key])
        for amendment in person.get('amendments', []):
            for key in ('original', 'value', 'basis'):
                if key in amendment:
                    amendment[key] = row(amendment[key])
        for event in person.get('events', []):
            if 'place' in event:
                event['place'] = row(event['place'])
        if isinstance(person.get('cardPresentation'), dict) and 'place' in person['cardPresentation']:
            person['cardPresentation']['place'] = row(person['cardPresentation']['place'])
    for source in graph.get('sources', {}).values():
        if 'title' in source:
            source['title'] = row(source['title'])
    research = graph.get('research') or {}
    for fact in research.get('updates', []) + research.get('highlights', []):
        for key in ('label', 'text'):
            if key in fact:
                fact[key] = row(fact[key])


def _protect_people(instance, graph):
    """The tree also obeys name-and-kinship disclosure, not just feed prose."""
    from familiar.instance.publication import restrict_graph
    restrict_graph(instance, graph)
