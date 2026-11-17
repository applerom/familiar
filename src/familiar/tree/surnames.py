# START_MODULE_CONTRACT: MOD-TREE-SURNAMES
# PURPOSE: Resolve an explicit family surname decision into reversible person display names and paternal inferences.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - source names remain literal; changing one clan decision recomputes all its display names [review: engine lead]
# - a surname inferred from children belongs only to an unambiguously identified father and retains its child basis [review: engine lead]
# - conflicting or undecided paternal spellings produce actionable nonblocking findings [review: engine lead]
# - clan membership and spelling compare birth names; married names remain literal source names [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (surname display and inferred-name projection)
# - MOD-INSTANCE-VALIDATION (nonblocking surname findings)
# - docs/reader-export.md (minimal tree cards)
# :END_MODULE_CONTRACT
from collections import Counter

from familiar.instance.gate import boundary


def _key(value):
    return value.strip().casefold() if isinstance(value, str) else ''


def gender_form(form, sex, language):
    """Only regular, gendered language endings; invariant surnames stay intact."""
    female = str(sex).lower() == 'f'
    pairs = {'ru': [('ский', 'ская'), ('цкий', 'цкая'), ('ской', 'ская'),
                    ('цкой', 'цкая'), ('ов', 'ова'), ('ев', 'ева'), ('ёв', 'ёва'),
                    ('ин', 'ина'), ('ын', 'ына')],
             'pl': [('ski', 'ska'), ('cki', 'cka'), ('dzki', 'dzka')]}
    for male, woman in pairs.get(language, []):
        if female and form.endswith(male):
            return form[:-len(male)] + woman
        if not female and str(sex).lower() == 'm' and form.endswith(woman):
            return form[:-len(woman)] + male
    return form


def names(person):
    return [n for n in person.get('names', []) if n and n.get('type') != 'derived-from-children']


def birth_names(graph, language=''):
    """Resolve surname roles in memory without correcting the attributed inputs."""
    people = graph['people']
    husbands = {}
    for family in graph.get('families', []):
        if family.get('status') not in {'rejected', 'disproved'}:
            husbands.setdefault(family.get('wife'), set()).add(family.get('husband'))
    result = {}
    for pid, person in people.items():
        spouse_names = {_key(gender_form(n['surname'], 'm', language))
                        for husband in husbands.get(pid, ()) if husband in people
                        for n in names(people[husband])
                        if n.get('surname') and n.get('type') != 'married'}
        own = [n for n in names(person) if n.get('type') != 'married' and
               (n.get('type') == 'birth' or not n.get('surname') or
                _key(gender_form(n['surname'], 'm', language)) not in spouse_names)]
        result[pid] = sorted(own, key=lambda n: n.get('type') != 'birth')
    return result


def _father(edge, people, husbands=()):
    parent = edge.get('parent', edge.get('from'))
    if edge.get('status') in {'rejected', 'disproved'} or parent not in people:
        return None
    role = edge.get('role')
    return parent if role == 'father' or (role != 'mother' and
                    (parent in husbands or str(people[parent].get('sex', '')).lower() == 'm')) else None


def decision_errors(metadata):
    rows = metadata.get('surname_forms', [])
    if not isinstance(rows, list):
        return ['tree_metadata.surname_forms: expected an array']
    errors = []
    seen, variants = set(), {}
    for i, row in enumerate(rows):
        where = f'tree_metadata.surname_forms[{i}]'
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k].strip()
                                                for k in ('id', 'form', 'basis')):
            errors.append(where + ': id, form and basis must be nonempty text')
            continue
        if row['id'] in seen:
            errors.append(where + ': duplicate clan id')
        seen.add(row['id'])
        if (not isinstance(row.get('variants'), list) or not row['variants'] or
                any(not isinstance(v, str) or not v.strip() for v in row['variants'])):
            errors.append(where + '.variants: expected nonempty surname spellings')
            continue
        if 'people' in row and (not isinstance(row['people'], list) or
                               any(not isinstance(p, str) or not p for p in row['people'])):
            errors.append(where + '.people: expected person ids')
            continue
        # Scoped clans can intentionally share a spelling; unscoped decisions cannot.
        if not row.get('people'):
            for variant in [row['form'], *row['variants']]:
                if _key(variant) in variants and variants[_key(variant)] != row['id']:
                    errors.append(where + ': overlapping surname decision; specify people')
                variants[_key(variant)] = row['id']
    return list(dict.fromkeys(errors))


def decisions(metadata):
    if errors := decision_errors(metadata):
        raise ValueError('; '.join(errors))
    rows = metadata.get('surname_forms', [])
    return rows


def choose_form(graph, variants, members=(), language=''):
    """Family memory first, then the most frequent literal documentary surname."""
    wanted = {_key(v) for v in variants}
    memory, documents = Counter(), Counter()
    for pid, own in birth_names(graph, language).items():
        if members and pid not in members:
            continue
        for name in own:
            surname = name.get('surname', '')
            if _key(surname) not in wanted:
                continue
            sources = [graph.get('sources', {}).get(s, {}) for s in name.get('provenance', [])]
            if any(s.get('kind') == 'memory' for s in sources):
                memory[surname] += 1
            elif name.get('type') == 'as-written' or any(
                    s.get('kind') in {'archive-record', 'home-paper', 'record', 'document'} for s in sources):
                documents[surname] += 1
    selected = memory or documents
    if not selected:
        raise ValueError('No attributed family or documentary surname; supply --form')
    return selected.most_common(1)[0][0], 'family-memory' if memory else 'document-frequency'


def apply(instance, graph, metadata):
    people, assigned = graph['people'], {}
    own = birth_names(graph, instance.source_language)
    rows = decisions(metadata)
    aliases = graph.get('identityAliases', {})
    errors = []
    for i, row in enumerate(rows):
        variants = {_key(v) for v in [row['form'], *row['variants']]}
        # Include ordinary feminine/male forms without equating unrelated spellings.
        variants |= {_key(gender_form(v, sex, instance.source_language))
                     for v in [row['form'], *row['variants']] for sex in ('m', 'f')}
        members = {aliases.get(p, p) for p in row.get('people', [])}
        if members - people.keys():
            errors.append(f'tree_metadata.surname_forms[{i}].people: unknown people ' + ', '.join(sorted(members - people.keys())))
        for pid, person in people.items():
            primary = next((n['surname'] for n in own[pid] if n.get('surname')), '')
            if (not members or pid in members) and _key(primary) in variants:
                if pid in assigned and assigned[pid]['id'] != row['id']:
                    errors.append(f'tree_metadata.surname_forms[{i}]: {pid} belongs to conflicting clans')
                assigned[pid] = row
    if errors:
        raise ValueError('; '.join(errors))
    children = {}
    fathers = {}
    husbands = {f.get('husband') for f in graph.get('families', [])}
    for edge in graph.get('edges', []):
        if parent := _father(edge, people, husbands):
            child = edge.get('child', edge.get('to'))
            if child in people:
                children.setdefault(parent, set()).add(child)
                fathers.setdefault(child, set()).add(parent)
    inferred = {}
    direct = dict(assigned)
    # Inferences do not cascade: only children assigned by a saved decision count.
    for parent, kids in children.items():
        person = people[parent]
        if any(n.get('surname') for n in names(person)) or not any(n.get('given') for n in names(person)):
            continue
        clans = {direct[k]['id'] for k in kids if k in direct}
        if len(clans) != 1 or any(len(fathers[k]) != 1 for k in kids if k in direct):
            continue
        basis_kids = sorted(k for k in kids if k in direct)
        if any(any(n.get('surname') for n in own[k]) and k not in direct for k in kids):
            continue
        row = direct[basis_kids[0]]
        if parent in assigned and assigned[parent]['id'] != row['id']:
            continue
        inferred[parent] = basis_kids
        assigned[parent] = row
    for pid, row in assigned.items():
        person = people[pid]
        original = names(person)
        first = next((n for n in original if n.get('given')), {})
        if not first:
            continue  # A literal owner placeholder must remain whole.
        surname = gender_form(row['form'], person.get('sex'), instance.source_language)
        full = ' '.join(filter(None, [first.get('given'), first.get('patronymic'), surname]))
        tree = ' '.join(filter(None, [first.get('given'), surname]))
        written = []
        for n in original:
            sources = [graph.get('sources', {}).get(s, {}) for s in n.get('provenance', [])]
            if (n.get('surname') and n['surname'] not in written and
                    (n.get('type') == 'as-written' or any(s.get('kind') in {
                        'archive-record', 'home-paper', 'record', 'document'} for s in sources))):
                written.append(n['surname'])
        display = {'clan': row['id'], 'form': surname, 'written': written,
                   'origin': 'clan-decision', 'children': []}
        if pid in inferred:
            display.update(origin='derived-from-children', children=inferred[pid])
            derived = {k: first[k] for k in ('given', 'patronymic') if first.get(k)}
            derived.update(surname=surname, type='derived-from-children', provenance=[],
                           inferred_parts={'surname': {'basis': 'Surname from children',
                                                       'provenance': inferred[pid]}})
            person['names'] = original + [derived]
        person['surnameDisplay'] = display
        person['name'] = full
        person.setdefault('namePresentation', {}).update(display=tree, full=full)
    for person in people.values():
        first = next((n for n in names(person) if n.get('given')), {})
        if first:
            surname = person.get('surnameDisplay', {}).get('form', first.get('surname', ''))
            person['treeName'] = ' '.join(filter(None, [first['given'], surname]))
    return graph


def findings(graph, metadata, language=''):
    """Compare only paternal sibling groups; a difference invites a decision."""
    people = graph['people']
    own = birth_names(graph, language)
    groups = {}
    husbands = {f.get('husband') for f in graph.get('families', [])}
    for edge in graph.get('edges', []):
        if parent := _father(edge, people, husbands):
            child = edge.get('child', edge.get('to'))
            if child in people:
                groups.setdefault(parent, set()).update({parent, child})
    decisions(metadata)
    result = []
    for parent, members in groups.items():
        spellings = {surname for pid in members for surname in
                     ([people[pid]['surnameDisplay']['form']] if people[pid].get('surnameDisplay') else
                      [n['surname'] for n in own[pid] if n.get('surname')])}
        spellings.discard('')
        # Gender variants of an explicit single clan are one form.
        clans = {people[pid].get('surnameDisplay', {}).get('clan') for pid in members
                 if any(n.get('surname') for n in own[pid])}
        forms = {_key(gender_form(s, 'm', language)) for s in spellings}
        if len(forms) > 1 and not (len(clans) == 1 and None not in clans):
            result.append({'location': 'tree_metadata.surname_forms', 'father': parent,
                           'people': sorted(members), 'spellings': sorted(spellings),
                           'message': 'Назови форму рода: familiar tree surname set ID --variant FORM ...; '
                                      'принятая память семьи имеет приоритет, иначе частая форма документов.'})
    return result


@boundary('diagnostic')
def set_form(instance, ident, form, variants, members=()):
    from familiar.instance.writer import mutate

    from .builder import _build, read_json
    metadata = read_json(instance.path('tree_metadata'), {})
    graph = _build(instance)
    if form:
        basis = 'family-memory'
    else:
        form, basis = choose_form(graph, variants, members, instance.source_language)
    row = {'id': ident, 'form': form, 'variants': list(dict.fromkeys([form, *variants])),
           'basis': basis}
    if members:
        row['people'] = list(dict.fromkeys(members))
    metadata['surname_forms'] = [r for r in decisions(metadata) if r['id'] != ident] + [row]
    apply(instance, graph, metadata)
    mutate(instance, {instance.path('tree_metadata'): metadata})
    return row
