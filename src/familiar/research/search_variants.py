# START_MODULE_CONTRACT: MOD-SEARCH-VARIANTS
# PURPOSE: Compare independent candidate fields using shared and family search forms without accepting identity.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - repeated evidence groups cannot promote a candidate to probable [review: engine lead]
# - legacy form annotations remain metadata; sex/person/episode applicability never changes identity [review: engine lead]
# CHANGES_WITH:
# - MOD-INSTANCE-PACKS
# :END_MODULE_CONTRACT
import json
import re
import unicodedata

from familiar.instance.packs import pack_file, read


def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold().replace('ł', 'l'))
                   if not unicodedata.combining(c)).strip()


def form_data(value, kind=None):
    """Legacy editorial brackets are carried as metadata, never search letters."""
    data = dict(value) if isinstance(value, dict) else {'text': value}
    raw = str(data.get('text') or '')
    notes = re.findall(r'\s+\[([^]]*)\]', raw)
    clean = re.sub(r'\s+\[[^]]*\]', '', raw)
    # An inline supplied letter is a reading, not a wildcard character class.
    clean = re.sub(r'(?<=\w)\[([\w])\](?=\w)', r'\1', clean)
    data['text'] = clean.strip()
    data.setdefault('as_written', raw)
    if notes:
        data['annotation'] = '; '.join(filter(None, [data.get('annotation'), *notes]))
    if kind == 'surname' and not data.get('sex') and not data.get('gender'):
        if re.search(r'(?:[оеё]ва|[сц]кая|owa|ówna|ianka|[sc]ka)$', clean, re.I):
            data['sex'] = 'F'
    annotation = data.get('annotation', '')
    if not data.get('episode') and re.search(r'(?i)\bСША\b|\bUSA\b|судовой лист|ship manifest', annotation):
        data['episode'] = 'emigration-us'
    return data


def _entries(instance):
    rows = []
    for pack in instance.packs:
        file = pack['data'].get('pack', {}).get('files', {}).get('variants')
        if file:
            rows.extend(read(pack_file(pack, file)).get('variant', []))
    path = instance.path('variant_overrides')
    if path.exists():
        rows.extend(json.loads(path.read_text(encoding='utf-8')).get('variant', []))
    return [e | {'forms': [form_data(f, e.get('kind')) for f in e.get('forms', [])]} for e in rows]


from familiar.instance.gate import boundary


@boundary('research')
def expand(instance, word, kind, year=None):
    result = [word]
    for entry in _entries(instance):
        if entry['kind'] != kind:
            continue
        forms = [f['text'] for f in entry['forms']
                 if year is None or not f.get('years') or f['years'][0] <= year <= f['years'][1]]
        if norm(word) in {norm(f) for f in forms}:
            result.extend(forms)
    return list(dict.fromkeys(result))


def compare(instance, fields, year=None):
    """fields: left/right/kind/dependency_group; caller declares independence."""
    matched, groups = [], set()
    for field in fields:
        forms = expand(instance, field['left'], field['kind'], year)
        if norm(field['right']) in {norm(f) for f in forms}:
            matched.append(field)
            groups.add(field['dependency_group'])
    return {'status': 'probable' if len(groups) >= 2 else 'possible' if groups else 'unmatched',
                'matched': matched, 'independent_fields': len(groups), 'accepted': False}
