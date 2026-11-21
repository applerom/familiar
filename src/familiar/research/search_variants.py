# START_MODULE_CONTRACT: MOD-SEARCH-VARIANTS
# PURPOSE: Expand a name or a place into the shared and family search forms; mark forms proposed by the key apart.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - forms by key are marked and stay out of the default expansion, so they never become a required search form [review: engine lead]
# - legacy form annotations remain metadata; sex/person/episode applicability never changes identity [review: engine lead]
# CHANGES_WITH:
# - MOD-INSTANCE-PACKS
# - MOD-NAME-KEY
# - MOD-MATCH-SCORE (identity score; replaces the former field-count compare)
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
def expand(instance, word, kind, year=None, by_key=False):
    return _expand(instance, word, kind, year, by_key)


@boundary('research')
def forms(instance, words, kind, year=None):
    """Marked forms of several words behind one family gate (the gate reads the whole family)."""
    return {word: _expand(instance, word, kind, year, True) for word in words}


def _expand(instance, word, kind, year=None, by_key=False):
    """Dictionary forms of every entry holding the word. With by_key: marked rows, plus forms the family already
    wrote whose key matches (via 'key'); those are suggestions, never required forms."""
    entries = _entries(instance)
    result, rows = [word], [{'text': word, 'via': 'word'}]
    for entry in entries:
        if entry['kind'] != kind:
            continue
        forms = [f['text'] for f in entry['forms']
                 if year is None or not f.get('years') or f['years'][0] <= year <= f['years'][1]]
        if norm(word) in {norm(f) for f in forms}:
            result.extend(forms)
            rows.extend({'text': f, 'via': 'dictionary', 'from': entry.get('id')} for f in forms)
    result = list(dict.fromkeys(result))
    if not by_key:
        return result
    from .name_key import key_forms
    seen, marked = set(), []
    for row in rows:
        if row['text'] not in seen:
            seen.add(row['text'])
            marked.append(row)
    if kind == 'surname':
        # A clan decision joins spellings the family decided are one surname: offered, marked, never required.
        from familiar.tree.builder import read_json
        from familiar.tree.surnames import clan_key
        for row in read_json(instance.path('tree_metadata'), {}).get('surname_forms', []):
            spellings = [row.get('form', ''), *row.get('variants', [])]
            if clan_key(word) in {clan_key(f) for f in spellings}:
                for text in spellings:
                    if text and text not in seen:
                        seen.add(text)
                        marked.append({'text': text, 'via': 'clan', 'from': row.get('id')})
    return marked + key_forms(instance, word, kind, seen, entries)
