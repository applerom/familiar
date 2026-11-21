# START_MODULE_CONTRACT: MOD-TREE-SURNAMES
# PURPOSE: Resolve an explicit family surname decision into reversible person display names and paternal inferences.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - source names remain literal; changing one clan decision recomputes all its display names [review: engine lead]
# - a surname inferred from children belongs only to an unambiguously identified father and retains its child basis [review: engine lead]
# - conflicting or undecided paternal spellings produce actionable nonblocking findings [review: engine lead]
# - clan membership and spelling compare birth names; married names remain literal source names [review: engine lead]
# - a woman whose birth name is another clan keeps the name she is called by; her birth clan is her maiden surname [review: engine lead]
# - male, female and Polish maiden forms of one spelling share one clan key, by the script the surname is written in [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (surname display and inferred-name projection)
# - MOD-INSTANCE-VALIDATION (nonblocking surname findings)
# - docs/reader-export.md (minimal tree cards)
# :END_MODULE_CONTRACT
from collections import Counter

from familiar.instance.gate import boundary


def _key(value):
    return value.strip().casefold() if isinstance(value, str) else ''


# Regular gendered endings by the script a surname is written in, not by the family's language: a Russian family's
# tree carries Polish acts (Korniejew, Korniejewa) and a Polish family's carries Russian ones.
GENDER_PAIRS = {'cyrillic': [('ский', 'ская'), ('цкий', 'цкая'), ('ской', 'ская'), ('цкой', 'цкая'), ('ов', 'ова'),
                             ('ев', 'ева'), ('ёв', 'ёва'), ('ин', 'ина'), ('ын', 'ына'), ('ый', 'ая')],
                'latin': [('ski', 'ska'), ('cki', 'cka'), ('dzki', 'dzka'), ('ow', 'owa'), ('ew', 'ewa'), ('in', 'ina'),
                          ('yn', 'yna')]}
# A Polish maiden form: the father's surname with -ówna (Kowalczyk → Kowalczykówna), also in Cyrillic acts.
MAIDEN_SUFFIXES = ('ówna', 'owna', 'увна')


def gender_form(form, sex, language=''):
    """Only regular, gendered endings; invariant surnames stay intact."""
    female = str(sex).lower() == 'f'
    for male, woman in GENDER_PAIRS['cyrillic' if _cyrillic(form) else 'latin']:
        if female and form.endswith(male):
            return form[:-len(male)] + woman
        if not female and str(sex).lower() == 'm' and form.endswith(woman):
            return form[:-len(woman)] + male
    return form


def clan_key(surname):
    """One key for a clan's male, female and maiden forms of one spelling: Корнеева, Korniejewa, Kowalczykówna."""
    key = _key(gender_form(_key(surname), 'm'))
    for suffix in MAIDEN_SUFFIXES:
        if key.endswith(suffix) and len(key) > len(suffix) + 2:
            return key[:-len(suffix)]
    return key


def names(person):
    return [n for n in person.get('names', []) if n and n.get('type') != 'derived-from-children']


def shown_first(person):
    """Names in display order: a document's own spelling comes after every form written for the family."""
    from .identities import DOCUMENT_NAME_TYPES
    return sorted(names(person), key=lambda n: n.get('type') in DOCUMENT_NAME_TYPES)


OLD_LETTERS = set('ѣѳіѵѢѲІѴ')
CYRILLIC_LANGUAGES = {'ru', 'uk', 'be', 'bg', 'sr', 'mk'}
# Male given names that end in -а/-я in the nominative; any other such male name on a tile may be the act's case.
MALE_IN_A = {'никита', 'илья', 'фома', 'кузьма', 'савва', 'лука', 'иона', 'михайла', 'данила', 'гаврила',
             'фока', 'сила', 'зосима', 'вавила', 'мина', 'ахилла'}


def _cyrillic(text):
    return any('Ѐ' <= c <= 'ӿ' for c in text)


def name_findings(graph, languages, source_language):
    """Hint where a tile would show a name its reader may not recognize: old letters, another script, an act's case."""
    result = []
    for pid, person in graph.get('people', {}).items():
        if person.get('living') is True or person.get('placeholder'):
            continue
        np = person.get('namePresentation') or {}
        for lang in languages:
            local = (np.get('byLanguage') or {}).get(lang)
            if not local and lang != source_language:
                continue  # the family's main name stands in; that is the agreed fallback, not a finding
            tile = (local or np.get('display') or person.get('name') or '').strip()
            given = tile.split(' ')[0] if tile else ''
            why = ('old orthography' if set(tile) & OLD_LETTERS or any(w.endswith('ъ') for w in tile.split())
                   else 'another script' if '[' not in tile and _cyrillic(tile) != (lang in CYRILLIC_LANGUAGES)
                   and any(c.isalpha() for c in tile)
                   else 'possibly the case of the act' if (str(person.get('sex')).lower() == 'm' and _cyrillic(given)
                                                           and given[-1:] in 'ая' and given.casefold() not in MALE_IN_A)
                   else '')
            if why:
                result.append({'location': f'person:{pid}', 'language': lang, 'name': tile, 'message':
                               f'tile name in {lang} is {why}; add a reader form: name_forms '
                               f'"display" (main language) or "by_language".{{"{lang}": ...}} (docs/language-checks.md)'})
    return result


def is_woman(person):
    return str(person.get('sex', '')).lower() == 'f' or (person.get('namePresentation') or {}).get('isWoman') is True


def married_surname(person):
    """The surname a woman is called by when her birth name belongs to another clan: she shows it, her father's
    clan is hers."""
    birth = next((n['surname'] for n in names(person) if n.get('type') == 'birth' and n.get('surname')), '')
    shown = next((n for n in shown_first(person) if n.get('surname')), {})
    if not birth or not is_woman(person) or shown.get('type') == 'birth' or clan_key(shown['surname']) == clan_key(birth):
        return ''
    return shown['surname']


def birth_names(graph, language=''):
    """Resolve surname roles in memory without correcting the attributed inputs."""
    people = graph['people']
    husbands = {}
    for family in graph.get('families', []):
        if family.get('status') not in {'rejected', 'disproved'}:
            husbands.setdefault(family.get('wife'), set()).add(family.get('husband'))
    result = {}
    for pid, person in people.items():
        spouse_names = {clan_key(n['surname'])
                        for husband in husbands.get(pid, ()) if husband in people
                        for n in names(people[husband])
                        if n.get('surname') and n.get('type') != 'married'}
        own = [n for n in names(person) if n.get('type') != 'married' and
               (n.get('type') == 'birth' or not n.get('surname') or clan_key(n['surname']) not in spouse_names)]
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
        # Ordinary feminine, male and maiden forms belong to the spelling without equating unrelated spellings.
        variants = {clan_key(v) for v in [row['form'], *row['variants']]}
        members = {aliases.get(p, p) for p in row.get('people', [])}
        if members - people.keys():
            errors.append(f'tree_metadata.surname_forms[{i}].people: unknown people ' + ', '.join(sorted(members - people.keys())))
        for pid, person in people.items():
            primary = next((n['surname'] for n in own[pid] if n.get('surname')), '')
            if (not members or pid in members) and primary and clan_key(primary) in variants:
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
        first = next((n for n in shown_first(person) if n.get('given')), {})
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
        display = {'clan': row['id'], 'form': surname, 'written': written, 'variants': row['variants'],
                   'origin': 'clan-decision', 'children': []}
        if pid in inferred:
            display.update(origin='derived-from-children', children=inferred[pid])
            derived = {k: first[k] for k in ('given', 'patronymic') if first.get(k)}
            derived.update(surname=surname, type='derived-from-children', provenance=[],
                           inferred_parts={'surname': {'basis': 'Surname from children',
                                                       'provenance': inferred[pid]}})
            person['names'] = original + [derived]
        person['surnameDisplay'] = display
        if married_surname(person):
            # She keeps the name the family calls her by; the clan form is her maiden name.
            person.setdefault('namePresentation', {})['maidenSurname'] = surname
            continue
        if (person.get('namePresentation') or {}).get('decided'):
            continue  # a decided name form (identity decisions) is whole; the clan form does not rebuild it
        person['name'] = full
        person.setdefault('namePresentation', {}).update(display=tree, full=full)
    for person in people.values():
        if married := married_surname(person):
            # A woman's own birth name, even without a clan decision, is the clan she comes from.
            person.setdefault('namePresentation', {}).setdefault('maidenSurname', next(
                n['surname'] for n in names(person) if n.get('type') == 'birth' and n.get('surname')))
        if (person.get('namePresentation') or {}).get('decided'):
            shown = person['namePresentation']['display']
            patronymic = next((n['patronymic'] for n in shown_first(person) if n.get('patronymic')), '')
            person['treeName'] = ' '.join(shown.replace(patronymic, '').split()) if patronymic else shown
            continue
        first = next((n for n in shown_first(person) if n.get('given')), {})
        if first:
            surname = married or person.get('surnameDisplay', {}).get('form', first.get('surname', ''))
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
        forms = {clan_key(s) for s in spellings}
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
    # The command changes what it was asked to: an existing decision keeps its written basis, its people and the rest;
    # only the command's own marker of how the form was chosen follows the new choice.
    prior = next((dict(r) for r in decisions(metadata) if r['id'] == ident), {})
    if prior.get('basis') in (None, 'family-memory', 'document-frequency'):
        prior['basis'] = basis
    row = {**prior, 'id': ident, 'form': form, 'variants': list(dict.fromkeys([form, *variants]))}
    if members:
        row['people'] = list(dict.fromkeys(members))
    metadata['surname_forms'] = [r for r in decisions(metadata) if r['id'] != ident] + [row]
    apply(instance, graph, metadata)
    mutate(instance, {instance.path('tree_metadata'): metadata})
    return row
