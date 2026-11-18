# START_MODULE_CONTRACT: MOD-TREE-PERSON
# PURPOSE: Gather one person with attributed claims and unresolved research without selecting a winning version.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - attached records and versions follow merged ids to their working successor [review: engine lead]
# - author commands preserve explicit evidence boundaries [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (declared reader surfaces and default-deny policy)
# - MOD-FAMILY-WRITER (the sole filesystem and generation boundary)
# - docs/PRD.md#FORMS
# :END_MODULE_CONTRACT
import json

from familiar.instance.gate import boundary
from familiar.research.packet import _collect, _relative

from .builder import _build, read_json


@boundary('research')
def person(instance, ident):
    snapshot = instance.path('tree_snapshot') / 'people.json'
    graph = _build(instance)
    ident = graph.get('identityAliases', {}).get(ident, ident)
    if ident not in graph['people']:
        raise ValueError(f'unknown person: {ident}; inspect ids with tree build --view working')
    snapshot = instance.path('tree_snapshot') / 'people.json'
    raw = read_json(snapshot, {'people': []})
    cards = raw['people']
    card = next((p for p in cards if p['id'] == ident), {})
    aliases = graph.get('identityAliases', {})
    def canonical(ids):
        return {aliases.get(pid, pid) for pid in ids}
    versions = [r for r in _collect(instance.path('versions')) if ident in canonical(r['data'].get('people', []))]
    questions = {r['data']['id'] for r in versions}
    def touches(row):
        data = row['data']
        from familiar.instance.subjects import explicit_subjects
        return ident in canonical(explicit_subjects(data)) or (data.get('question') or data.get('aim', {}).get('version')) in questions
    result = {'id': ident, 'person': graph['people'][ident],
              'names': card.get('names', []), 'events': card.get('events', []),
              'snapshot_locator': str(snapshot.relative_to(instance.root)) if card else None,
              'links': [e for e in graph['edges'] if ident in (e.get('child'), e.get('parent'), e.get('from'), e.get('to'))],
              'unions': [f for f in graph['families'] if ident in (f.get('husband'), f.get('wife')) or ident in f.get('children', [])],
              'identity_decisions': read_json(instance.path('identity_decisions'), {}),
              'versions': versions, 'sources': graph['sources'],
              'weight_note': 'Absent weights remain unknown. GEDCOM claims are unverified hypotheses recorded in another tree; firm attributed family memory is testimony, not documentary confirmation.'}
    for key in ('cases', 'asks', 'records'):
        result[key] = [r for r in _collect(instance.path(key)) if touches(r)]
    # Preserve claims verbatim; never assign a probability to an unweighted fact.
    from familiar.instance.gate import evaluate
    from familiar.instance.research_forms import PREVIEW
    result['output'] = {'state': PREVIEW}
    result['trust'] = evaluate(instance)
    return _relative(json.loads(json.dumps(result)), str(instance.root))
