# START_MODULE_CONTRACT: MOD-INTAKE-TABLE-REVIEW
# PURPOSE: Separate forwardable table questions, attributed card prose and removable kinship proposals.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - a shared birth/death place column questions the event kind without weakening a firm place assertion [review: engine lead]
# - kin proposals cite patronymics, surname context and generation constraints, without creating people [review: engine lead]
# CHANGES_WITH:
# - MOD-INTAKE-TABLE
# - MOD-INTAKE-CORE
# - regions/ru/pack.toml
# - regions/pl/pack.toml
# - regions/demo-english/pack.toml
# :END_MODULE_CONTRACT
import re
from difflib import SequenceMatcher


def bridge_label(path, pack):
    explicit = pack['placeholders'].get(path)
    if explicit:
        return explicit
    words = pack['bridge_words']
    if not path:
        return words['narrator']
    labels = {'f': 'father', 'm': 'mother'}
    return ' '.join([words[labels[path[-1]]],
                     *(words[labels[step] + '_genitive'] for step in reversed(path[:-1])),
                     words['narrator_genitive']])


def describe(person, item, role, ledger, pack, report, ask):
    w = pack['words']
    text = item['text']
    urls = re.findall(r'(?:https?://|www\.)[^\s<>]+', text)
    if item.get('link'):
        urls.append(item['link'])
    if urls:
        report['research_leads'].append({'cell': item['cell'], 'links': list(dict.fromkeys(urls))})
        text = w['link'].format(cell=item['cell'])
    elif role in {'person', 'person_kin'}:
        kin = person['_kin'].strip()
        text = w['kin'] + ': ' + kin if kin else w['no_kin']
    elif ledger['fields']:
        item['display_text'] = f"{w.get(role, w['notes'])} ({w['reported']}): {text}"
        return  # Exact event is already shown; never duplicate it as a note.
    elif role in {'birth_place', 'death_place', 'place'} and re.fullmatch(r'[\d\s?./()\-]+', text) and re.search(r'\d{4}', text):
        ask(item['cell'], 'ask_place', value=text)
        text = w['misplaced'].format(value=text)
        item['status'] = 'possible'
        item['derived'] = True
        item['basis'] = pack['bridge_words']['place_basis']
    else:
        uncertain = item['status'] == 'possible'
        label = w.get(role, w['notes'])
        if uncertain and role in {'birth', 'death'}:
            years = list(dict.fromkeys(re.findall(r'\b\d{4}\b', text)))
            short = re.search(r'\b(\d{2})\d{2}\s*\((\d{2})\)', text)
            if short:
                years.append(short[1] + short[2])
            if len(years) > 1:
                ask(item['cell'], 'ask_years', years=' / '.join(years))
            else:
                ask(item['cell'], 'ask_date', label=label, value=text)
        elif role == 'place' and not uncertain:
            ask(item['cell'], 'ask_place_event', value=text)
        elif role in {'birth', 'death', 'birth_place', 'death_place', 'place'}:
            ask(item['cell'], 'ask_date', label=label, value=text)
        text = f"{label} ({w['reported']}" + (', ' + w['uncertain'] if uncertain else '') + '): ' + text
    item['display_text'] = text
    person['notes'].append({'text': text, 'provenance': [item['id']],
                            **({k: item[k] for k in ('derived', 'basis')} if item.get('derived') is True else {}),
                            'status': 'hypothesis' if item['strength'] == 'hearsay' or item['status'] == 'possible' else 'export'})


def enrich(data, pack, report, ask):
    vocab, w = pack['vocabulary'], pack['words']
    items = {i['id']: i for i in data['items']}
    generations, fathers = {}, {}
    for p in data['people']:
        kin = p['_kin'].casefold().strip()
        tokens = re.findall(r'\w+', kin)
        generations[p['id']] = next((vocab['generations'][t] for t in tokens if t in vocab['generations']), None)
        if kin in vocab['self']:
            generations[p['id']] = 0
        patronymic = next((n.get('patronymic', '') for n in p['names']), '')
        sexes = set()
        for sex, key in [('M', 'male'), ('F', 'female')]:
            if any(t in vocab[key] for t in tokens) or any(patronymic.casefold().endswith(s) for s in vocab[key + '_suffix']):
                sexes.add(sex)
        if len(sexes) == 1:
            p['sex'] = sexes.pop()
        elif len(sexes) > 1:
            report['reviewer_hints'].append({'person': p['id'], 'hint': 'Kin word and patronymic disagree on sex; left unknown.'})
        father = vocab['fathers'].get(patronymic.casefold())
        if father:
            fathers[p['id']] = (father, patronymic)
        elif patronymic:
            source = p['names'][0]['provenance']
            p['notes'].append({'text': w['father_unknown'].format(patronymic=patronymic), 'provenance': source, 'status': 'hypothesis', 'derived': True, 'basis': w['father_unknown'].format(patronymic=patronymic)})
            ask(items[source[0]]['cell'], 'ask_father', patronymic=patronymic)
        source_items = [i for i in data['items'] if i.get('person') == p['id']]
        if p.get('living') is None and (any(any(t in i['text'].casefold() for t in vocab['death_words']) for i in source_items)
                                      or (generations[p['id']] or 0) >= 3):
            report['life_status_candidates'].append({'person': p['id'], 'basis': [i['cell'] for i in source_items],
                'reason': 'Older generation or reported death/disappearance; reviewer must record a motivated life-status decision, never infer automatically.'})
    proposals = []
    for p in data['people']:
        if p['id'] not in fathers:
            continue
        father, patronymic = fathers[p['id']]
        surnames = {n['surname'].casefold() for n in p['names']}
        candidates = []
        for other in data['people']:
            if other is p or other.get('sex') == 'F':
                continue
            for n in other['names']:
                if n['given'].casefold() != father.casefold():
                    continue
                surname = n['surname'].casefold()
                generation = generations[p['id']]
                parent_generation = generations[other['id']]
                if surname in surnames and generation is not None and parent_generation in {None, generation + 1}:
                    candidates.append(other)
                elif generation is not None and parent_generation == generation + 1 and not any(n.get('type') == 'birth' for n in p['names']):
                    # A married surname is not evidence against a father. Require a
                    # neighbouring same-surname woman of his generation as a second clue.
                    index = data['people'].index(other)
                    neighbours = data['people'][max(0, index-1):index+2]
                    if any(q is not other and q.get('sex') == 'F' and generations[q['id']] == parent_generation
                           and any(n['surname'].casefold() == surname for n in q['names']) for q in neighbours):
                        candidates.append(other)
                elif surname not in surnames:
                    for original in surnames:
                        if SequenceMatcher(None, original, surname).ratio() >= .55:
                            text = w['variant'].format(first=original.title(), second=n['surname'])
                            source = p['names'][0]['provenance']
                            p['notes'].append({'text': text, 'provenance': source, 'status': 'hypothesis', 'derived': True, 'basis': text})
                            ask(items[source[0]]['cell'], 'ask_variant', first=original.title(), second=n['surname'])
        candidates = list({c['id']: c for c in candidates}.values())
        source = p['names'][0]['provenance']
        if not candidates:
            # Do not say absent when a same-name father is present but unresolved.
            if not any(n['given'].casefold() == father.casefold() for other in data['people'] for n in other['names']):
                p['notes'].append({'text': w['father'].format(father=father), 'provenance': source, 'status': 'hypothesis', 'derived': True, 'basis': pack['bridge_words']['patronymic_basis'].format(patronymic=patronymic)})
            continue
        if len(candidates) != 1:
            report['reviewer_hints'].append({'person': p['id'], 'hint': 'Multiple father candidates; no family proposed.'})
            continue
        parent = candidates[0]
        grounds = list(dict.fromkeys(source + parent['names'][0]['provenance']))
        shared = any(n['surname'].casefold() in surnames for n in parent['names'])
        if not shared:
            index = data['people'].index(parent)
            for neighbour in data['people'][max(0, index-1):index+2]:
                if neighbour is not parent and neighbour.get('sex') == 'F' and generations[neighbour['id']] == generations[parent['id']]:
                    for name in neighbour['names']:
                        if name['surname'] == parent['names'][0]['surname']:
                            grounds = list(dict.fromkeys(grounds + name['provenance']))
        text = w['hypothesis' if shared else 'hypothesis_context'].format(parent=parent['_name'].title(), child=p['_name'].title(), patronymic=patronymic,
                                      surname=next((n['surname'] for n in parent['names'] if n['surname'].casefold() in surnames),
                                                   parent['names'][0]['surname'] + ' (?)'))
        proposal_id = 'kin-hypothesis-' + str(len(proposals) + 1)
        proposals.append({'id': proposal_id, 'enabled': True,
            'family': {'id': proposal_id, 'husband': parent['id'], 'children': [p['id']], 'provenance': grounds, 'status': 'hypothesis', 'derived': True, 'basis': text.split(pack['bridge_words']['basis_separator'], 1)[-1]},
            'notes': {pid: {'text': text, 'provenance': grounds, 'status': 'hypothesis', 'derived': True, 'basis': text.split(pack['bridge_words']['basis_separator'], 1)[-1]} for pid in (p['id'], parent['id'])}})
    # An adjacent ancestor generation plus an exact birth surname offers a
    # maternal bridge too. No path is asserted when several mothers fit.
    for child in data['people']:
        birth_names = {n['surname'].casefold() for n in child['names'] if n.get('type') == 'birth'}
        generation = generations[child['id']]
        mothers = [p for p in data['people'] if p is not child and p.get('sex') == 'F'
                   and generation is not None and generations[p['id']] == generation + 1
                   and any(n['surname'].casefold() in birth_names for n in p['names'])]
        if len(mothers) != 1:
            continue
        mother = mothers[0]
        grounds = list(dict.fromkeys(child['names'][0]['provenance'] + mother['names'][0]['provenance']))
        text = w['mother_hypothesis'].format(parent=mother['_name'].title(), child=child['_name'].title())
        proposal_id = 'kin-hypothesis-' + str(len(proposals) + 1)
        proposals.append({'id': proposal_id, 'enabled': True,
            'family': {'id': proposal_id, 'wife': mother['id'], 'children': [child['id']], 'provenance': grounds, 'status': 'hypothesis', 'derived': True, 'basis': text.split(pack['bridge_words']['basis_separator'], 1)[-1]},
            'notes': {pid: {'text': text, 'provenance': grounds, 'status': 'hypothesis', 'derived': True, 'basis': text.split(pack['bridge_words']['basis_separator'], 1)[-1]} for pid in (child['id'], mother['id'])}})
    data['relationship_hypotheses'] = proposals
    for index, p in enumerate(data['people']):
        for other in data['people'][index+1:]:
            if generations[p['id']] != generations[other['id']] or not p['names'] or not other['names']:
                continue
            a, b = p['names'][0]['surname'], other['names'][0]['surname']
            if a != b and .55 <= SequenceMatcher(None, a.casefold(), b.casefold()).ratio() < .9:
                text = w['variant'].format(first=a, second=b)
                for participant in (p, other):
                    participant['notes'].append({'text': text, 'provenance': participant['names'][0]['provenance'], 'status': 'hypothesis', 'derived': True, 'basis': text})
                ask(items[p['names'][0]['provenance'][0]]['cell'], 'ask_variant', first=a, second=b)
    report['reviewer_hints'].append({'hint': 'Check all strengths, narrator, life status and kin hypotheses. Set enabled=false to remove a proposal and its two card facts before intake.'})
