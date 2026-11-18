# START_MODULE_CONTRACT: MOD-RESEARCH-PACKET
# PURPOSE: Recover primary line evidence independently of an owner's selection and stage its argument for review.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - packet selection uses applied working people rather than unvalidated declarations [review: engine lead]
# - graph-only people and additive evidence retain their contribution locators [review: engine lead]
# - reviewer evidence excludes owner weights until the argument stage [review: engine lead]
# - bounded packets name omitted entries and missing collections [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (declared reader surfaces and default-deny policy)
# - MOD-FAMILY-WRITER (the sole filesystem and generation boundary)
# - docs/PRD.md#FORMS
# :END_MODULE_CONTRACT
import json
from pathlib import Path


def _collect(path):
    if not path.exists():
        return []
    files = [path] if path.is_file() else sorted(path.rglob('*'))
    result = []
    for file in files:
        if any(part.startswith('.') for part in file.relative_to(path.parent).parts):
            continue
        if file.suffix not in {'.json', '.jsonl'}:
            continue
        try:
            text = file.read_text(encoding='utf-8')
            values = [json.loads(s) for s in text.splitlines() if s.strip()] if file.suffix == '.jsonl' else [json.loads(text)]
        except (ValueError, OSError) as exc:
            raise ValueError(f'unreadable collection {path}, file {file}: {exc}') from exc
        for value in values:
            for row in value if isinstance(value, list) else [value]:
                if not isinstance(row, dict):
                    raise TypeError(f'expected object: {file}')
                result.append({'locator': str(file), 'data': row})
    return result


from familiar.instance.gate import boundary


@boundary('diagnostic')
def packet(instance, *, case=None, people=(), mode='owner', stage='evidence', max_chars=24000):
    """Assemble the line packet; locators are relative to the family root, never host paths."""
    from familiar.instance.gate import evaluate
    verdict = evaluate(instance)
    envelope = {'output': {'state': 'preview'}, 'trust': {'blocked': verdict['blocked'], 'findings_count': len(verdict['findings'])}}
    reserve = len(json.dumps(envelope)) + 4
    result = _relative(_packet(instance, case=case, people=people, mode=mode, stage=stage,
                               max_chars=max_chars - reserve), str(instance.root))
    result.update(envelope)
    return result


def _relative(value, root):
    if isinstance(value, dict):
        return {k: _locator(v, root) if k == 'locator' else _relative(v, root)
                for k, v in value.items()}
    if isinstance(value, list):
        return [_relative(v, root) for v in value]
    return value


def _locator(text, root):
    path, base = Path(str(text)), Path(root)
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return 'host:' + path.name


def _packet(instance, *, case=None, people=(), mode='owner', stage='evidence', max_chars=24000):
    if max_chars < 600:
        raise ValueError('max_chars must be at least 1000 including the diagnostic envelope')
    keys = ('cases', 'versions', 'memory', 'answers', 'records', 'searches', 'asks')
    collections = {k: _collect(instance.path(k)) for k in keys}
    selected_cases = [r for r in collections['cases'] if r['data'].get('id') == case] if case else []
    if case and not selected_cases:
        raise ValueError(f'unknown case {case}')
    qids = {r['data']['question'] for r in selected_cases}
    from familiar.checks.engine import _known_people
    known = _known_people(instance)
    def canonical(ids):
        return {known[p]['id'] if p in known else p for p in ids}
    selected_people = set(people)
    versions = [r for r in collections['versions'] if r['data'].get('id') in qids or canonical(selected_people).intersection(canonical(r['data'].get('people', [])))]
    for row in versions:
        qids.add(row['data']['id'])
        selected_people.update(row['data']['people'])
    if not case:
        selected_cases = [r for r in collections['cases'] if r['data'].get('question') in qids]
    snapshot = instance.path('tree_snapshot') / 'people.json'
    cards = list({p['id']: p for p in known.values()}.values())
    contributions = _collect(instance.path('contributions'))
    locators = {pid: row['locator'] for row in contributions for pid in row['data'].get('people', {})}
    if selected_people - known.keys():
        raise ValueError(f'unknown people: {sorted(selected_people - known.keys())}; inspect ids with tree build --view working')
    selected_people = {known[p]['id'] for p in selected_people}
    if not selected_people:
        raise ValueError('select a case or at least one person')
    ask_versions = qids | {v['id'] for row in versions for v in row['data'].get('versions', []) if v.get('id')}
    requests = [r for r in collections['asks'] if r['data'].get('aim', {}).get('version') in ask_versions or r['data'].get('case') == case and case]
    request_ids = {r['data']['id'] for r in requests}
    # Memory often has no person tags. Include every telling, marked as a superset,
    # rather than losing an unlinked old family observation by text matching.
    def observed(value):
        if isinstance(value, dict):
            return {k: observed(v) for k, v in value.items()
                    if k not in {'weight', 'accepted', 'decision', 'verdict', 'confidence'}}
        if isinstance(value, list):
            return [observed(v) for v in value]
        return value
    primary = {
        'contributions_superset': observed(contributions),
        'evidence_superset': _collect(instance.path('evidence')),
        'associations_superset': _collect(instance.path('associations')),
        'person_cards': [{'locator': locators.get(r['id'], str(snapshot)), 'data': observed(r)} for r in cards if r['id'] in selected_people],
        'memory_superset': collections['memory'],
        'answers': [r for r in collections['answers'] if r['data'].get('request') in request_ids or set(r['data'].get('people', [])).intersection(selected_people)],
        'records_superset': collections['records'],
        'searches': [r for r in collections['searches'] if r['data'].get('question') in qids],
        'requests': requests,
    }
    # Unlinked answers may refer to old requests absent from the selected case.
    primary['answers_superset'] = collections['answers']
    primary.pop('answers')
    if mode == 'second-look':
        selected_cases = [dict(r, data={k: v for k, v in r['data'].items() if k not in {'second_looks', 'narrative'}}) for r in selected_cases]
    argument = {'cases': selected_cases, 'versions': versions,
                'contribution_arguments': contributions,
                'identity_decisions': _collect(instance.path('identity_decisions'))}
    result = {'mode': mode, 'stage': stage, 'people': sorted(selected_people),
              'missing_collections': [k for k in keys if not instance.path(k).exists()] + ([] if snapshot.exists() else ['person_cards']),
              'selection_note': 'Memory, answers and records include unlinked entries as a conservative superset. Images are locators, not inspected originals.',
              'omitted': [], 'primary_evidence': {}}
    sections = [('primary_evidence', primary)]
    if mode == 'owner' or stage == 'argument':
        result['owner_argument_open_after_own_evidence_table'] = {}
        sections.append(('owner_argument_open_after_own_evidence_table', argument))
    else:
        result['argument_gate'] = 'Make and save your own evidence table, then request --stage argument. Other verdicts and stories remain closed.'
    # Reserve space for a complete omission manifest before adding whole entries.
    candidates = [(section, kind, row) for section, groups in sections for kind, rows in groups.items() for row in rows]
    result['omitted'] = [{'section': s, 'kind': k, 'locator': r['locator'], 'id': r['data'].get('id')} for s, k, r in candidates]
    if len(json.dumps(result, ensure_ascii=False)) > max_chars:
        result['omitted'] = [{'reason': 'manifest exceeds budget', 'entries': len(candidates)}]
        if len(json.dumps(result, ensure_ascii=False)) > max_chars:
            raise ValueError('selection metadata exceeds budget; narrow people or increase max_chars')
        return result
    pending = result['omitted']
    result['omitted'] = []
    for index, (s, k, row) in enumerate(candidates):
        result[s].setdefault(k, []).append(row)
        omitted = pending[index]
        if len(json.dumps(result, ensure_ascii=False)) + len(json.dumps(pending[index:], ensure_ascii=False)) > max_chars:
            result[s][k].pop()
            result['omitted'].append(omitted)
    return result
