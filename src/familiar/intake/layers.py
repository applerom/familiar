# START_MODULE_CONTRACT: MOD-INTAKE-LAYERS
# PURPOSE: Say of every family statement what in it holds (the skeleton), what drifts (attributes) and what was left empty (blanks).
# PRD_REF: docs/PRD.md#BLANKS
# INVARIANTS:
# - a layer is how far a search may lean on the statement, never its truth: no strength, status or weight changes [review: engine lead]
# - statements taken in by an earlier release carry no layer and are read by the same rule [review: engine lead]
# CHANGES_WITH:
# - MOD-INTAKE-CORE (layers are written at intake)
# - MOD-RESEARCH-PLAN (a thin line is searched by its skeleton)
# :END_MODULE_CONTRACT
import json

LAYERS = ('skeleton', 'attribute')
# Who is whose parent, surnames, villages and a father's name read from a child's patronymic hold; years, the exact
# form of an old name, deaths and the number of brothers and sisters drift.
ROLES = {'person': 'skeleton', 'person_kin': 'skeleton', 'kin': 'skeleton', 'birth_place': 'skeleton', 'place': 'skeleton',
         'birth': 'attribute', 'death': 'attribute', 'death_place': 'attribute', 'living': 'attribute',
         'note': 'attribute', 'notes': 'attribute', 'witness': 'attribute'}
BLANKS = ('name', 'patronymic', 'birth', 'death', 'place', 'spouse', 'occupation', 'siblings')
CELLS = {'birth': 'birth', 'birth_place': 'place'}  # table columns whose empty cell is an explicit blank


def of(item, data=None):
    """The layers of one statement: its own, its table column's, else of what was taken from it."""
    if item.get('layers'):
        return list(item['layers'])
    if item.get('role') in ROLES:
        return [ROLES[item['role']]]
    cited, found = item.get('id'), set()
    for person in (data or {}).get('people', []):
        for field, layer in (('names', 'skeleton'), ('events', 'attribute'), ('notes', 'attribute')):
            for claim in person.get(field) or []:
                if cited in (claim.get('provenance') or []):
                    found.add(layer)
                    if field == 'events' and claim.get('type') == 'birth' and claim.get('place'):
                        found.add('skeleton')
    if any(cited in (f.get('provenance') or []) for f in (data or {}).get('families', [])):
        found.add('skeleton')
    return [layer for layer in LAYERS if layer in found] or ['attribute']


def problem(data):
    for item in data.get('items', []):
        named = item.get('layers', ['attribute'])
        if not isinstance(named, list) or not named or set(map(str, named)) - set(LAYERS):
            return f"memory item {item.get('id')}: layers are " + ' and '.join(LAYERS)
    local = {p.get('id') for p in data.get('people', [])}
    for blank in data.get('blanks', []):
        if not isinstance(blank, dict) or blank.get('person') not in local or blank.get('field') not in BLANKS:
            return 'a blank names a person of this telling and one of ' + ', '.join(BLANKS)
    return ''


def statements(instance, ids):
    """(id, layers) of the family's statements with these ids; a telling taken in before layers has none of its own."""
    found = []
    for path in sorted(instance.path('memory').rglob('*.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        for row in data if isinstance(data, list) else [data]:
            found += [(i['id'], of(i, row) if i.get('layers') or i.get('role') else []) for i in row.get('items', [])
                      if i.get('id') in ids]
    return found
