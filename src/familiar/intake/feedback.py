# START_MODULE_CONTRACT: MOD-INTAKE-FEEDBACK
# PURPOSE: Make an editable memory draft from literal feedback, without accepting it.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - feedback anchors resolve applied research people and identity successors [review: engine lead]
# - original messages remain traceable and relationships are proposed hypotheses [review: engine lead]
# CHANGES_WITH:
# - MOD-INTAKE-CORE
# - MOD-INTAKE-TABLE
# - MOD-FAMILY-WRITER
# :END_MODULE_CONTRACT
import json
import re
from datetime import date
from uuid import UUID, uuid4

from familiar.instance.gate import boundary
from familiar.instance.writer import attachment_catalog, mutate
from .core import read, safe, token
from .table import toml


def ask_private(instance, row):
    from familiar.instance.asks import FEEDBACK, get
    if row.get('kind') not in FEEDBACK:
        return False
    _, ask = get(instance, row['ask_id'])
    return bool(row.get('private') or row.get('ask_state') == 'private' or ask.get('tender') or row.get('tender'))


@boundary('writer')
def prepare(instance, identities, output, ident=None, told_by='Рассказчик; уточнить исследователю'):
    ident = token(ident or 'feedback-' + uuid4().hex[:12])
    target = (output if output.is_absolute() else instance.root / output).resolve()
    if not target.is_relative_to(instance.root) or target.exists():
        raise ValueError('Draft must be a new file inside the family')
    from familiar.tree.builder import _build, people_index
    graph = _build(instance)
    people, families = people_index(graph), graph['families']
    data = {'id': ident, 'told_by': told_by, 'date': date.today().isoformat(), 'items': [], 'people': [], 'families': []}
    comments, refs, seen, inferred_families = [], {}, set(), {}
    from familiar.instance.asks import FEEDBACK, get

    def existing(pid):
        if pid not in people:
            raise ValueError(f'Unknown anchor or parent: {pid}; inspect ids with tree build --view working')
        pid = people[pid]['id']
        if pid not in refs:
            refs[pid] = f'existing{len(refs) + 1}'
            data['people'].append({'id': refs[pid], 'existing': pid, 'names': [], 'events': [], 'notes': []})
        return refs[pid]

    for raw in identities:
        identity = str(UUID(raw))
        if identity in seen:
            raise ValueError('Duplicate feedback ID')
        seen.add(identity)
        original = f'family/feedback/inbox/{identity}.json'
        row = json.loads(instance._inside(original).read_text(encoding='utf-8-sig'))
        if (row.get('id') == identity and not row.get('text')
                and (row.get('files') or attachment_catalog(instance, identity))):
            raise ValueError(f'Feedback {identity} contains photographs; use intake attachment {identity}')
        if row.get('id') != identity or not isinstance(row.get('text'), str) or not row['text']:
            raise ValueError(f'Invalid feedback: {identity}')
        source = 'feedback-' + identity
        np = row.get('new_person')
        strength = 'firm' if isinstance(np, dict) and np.get('known_from') == 'memory' else 'hearsay'
        data['items'].append({'id': source, 'text': row['text'], 'received_at': row.get('received_at', ''),
                              'original': original, 'witness': told_by, 'strength': strength})
        about, _, rest = str(row.get('subject') or '').partition(':')
        if about in {'blank', 'amendment'} and row.get('kind') in {'correction', 'confirm', 'decline'}:
            # A line of the card filled in, or our proposal answered with one tap: the person and the field came with it.
            item = data['items'][-1]
            if row.get('person') in people:
                item['person'] = people[row['person']]['id']
            item.update({'amendment': rest} if about == 'amendment' else {'field': rest.rpartition(':')[2]})
            if row['kind'] != 'correction':
                item['answer'] = 'yes' if row['kind'] == 'confirm' else 'no'
            if row.get('question'):
                item['version'] = row['question']
            comments.append(f"# {identity}: {about} {rest} · {item.get('answer', row['kind'])}")
        if row.get('kind') in FEEDBACK:
            _, ask = get(instance, row['ask_id'])
            item = data['items'][-1]
            for field in ('ask_id', 'wants', 'via_child', 'ask_state'):
                if field in row:
                    item[field] = row[field]
            pid = ask.get('about', {}).get('person')
            if pid in people:
                item['person'] = people[pid]['id']
            if ask_private(instance, row):
                data['visibility'] = 'search-only'
        if row.get('kind') != 'add_person' or not isinstance(np, dict) or not np:
            comments.extend([f'# {identity}: свободный текст — заполните вручную:', '# [[people]]', f'# id = "person{len(seen)}"', f'# names = [{{given = "", type = "reported", provenance = ["{source}"]}}]', '# events = []', '# notes = []'])
            continue
        anchor = row.get('anchor', '')
        a = existing(anchor)
        local = 'person' + str(len(seen))
        provenance = [source]
        name = {k: np[k] for k in ('given', 'surname', 'patronymic') if np.get(k)}
        names = [name | {'type': 'reported', 'provenance': provenance}] if name else []
        if np.get('maiden_surname'):
            names.append({**{k: v for k, v in name.items() if k != 'surname'}, 'surname': np['maiden_surname'], 'type': 'birth', 'provenance': provenance})
        events = []
        for kind in ('birth', 'death'):
            fields = {k: v for k, v in [('date', np.get(kind)), ('place', np.get(kind + '_place'))] if v}
            if fields:
                events.append({'type': kind, **fields, 'provenance': provenance})
        notes = [{'text': np[k], 'provenance': provenance} for k in ('note', 'told_by', 'kin_words') if np.get(k)]
        person = {'id': local, 'names': names, 'events': events, 'notes': notes}
        if np.get('living') in ('alive', 'dead'):
            person['living'] = np['living'] == 'alive'
        data['people'].append(person)
        rel = row.get('relation')
        fam = {'id': 'relation' + str(len(seen)), 'status': 'hypothesis', 'provenance': provenance}
        if rel in ('father', 'mother', 'parent'):
            fam.update({('wife' if rel == 'mother' else 'husband'): local, 'children': [a]})
            if rel == 'parent':
                comments.append(f'# {identity}: уточните роль родителя (husband/wife).')
        elif rel == 'child':
            fam.update({'husband': a, 'children': [local]})
            comments.append(f'# {identity}: уточните роль якоря (husband/wife).')
        elif rel == 'spouse':
            fam.update({'husband': a, 'wife': local, 'children': []})
            comments.append(f'# {identity}: уточните роли супругов (husband/wife).')
        elif rel == 'sibling':
            parent_families = [f for f in families if anchor in f.get('children', []) and (f.get('husband') or f.get('wife'))]
            if parent_families:
                for n, old in enumerate(parent_families):
                    proposal = dict(fam, id=f"{fam['id']}-{n + 1}", children=[a, local])
                    for role in ('husband', 'wife'):
                        if old.get(role):
                            proposal[role] = existing(old[role])
                    data['families'].append(proposal)
                continue
            anchor_pat = next((n.get('patronymic', '') for n in people[anchor].get('names', []) if n.get('patronymic')), '')
            def stem(value):
                return re.sub(r'(ович|евич|овна|евна)$', '', value.casefold().replace('ё', 'е'))
            p = np.get('patronymic', '')
            if p and anchor_pat and stem(p) == stem(anchor_pat) and stem(p) != p.casefold().replace('ё', 'е'):
                key = (anchor, stem(p))
                if key in inferred_families:
                    previous, father_row = inferred_families[key]
                    previous['children'].append(local)
                    previous['provenance'].append(source)
                    father_row['names'][0]['provenance'].append(source)
                    father_row['notes'][0]['provenance'].append(source)
                    continue
                father = 'inferred' + str(len(seen))
                inferred = re.sub(r'(ович|евич|овна|евна)$', '', p, flags=re.I)
                father_row = {'id': father, 'sex': 'M', 'names': [{'given': inferred, 'type': 'inferred', 'provenance': [source]}], 'events': [], 'notes': [{'text': 'Имя предположено по совпадающим отчествам; проверить.', 'provenance': [source]}]}
                data['people'].append(father_row)
                fam.update({'husband': father, 'children': [a, local]})
                inferred_families[key] = (fam, father_row)
                comments.append(f'# {identity}: имя общего отца выведено из отчества; проверить.')
            else:
                comments.append(f'# {identity}: кто общие родители якоря и нового человека? Добавьте [[families]] вручную.')
                continue
        else:
            comments.append(f'# {identity}: уточните родство {rel!r}, добавьте [[families]] вручную.')
            continue
        data['families'].append(fam)
    data.setdefault('visibility', 'family')
    content = ('# Черновик: проверьте рассказчика, людей, родство и источники перед приёмом.\n' + '\n'.join(comments) + '\n').encode('utf-8') + toml(data)
    mutate(instance, {target: content}, exclusive=[target])
    return {'status': 'draft', 'draft': str(target), 'id': ident, 'items': len(data['items']), 'people': len(data['people']), 'families': len(data['families'])}
