# START_MODULE_CONTRACT: MOD-FEED-TRANSLATIONS
# PURPOSE: Keep translation source snapshots visible alongside the rendered language rows.
# PRD_REF: docs/PRD.md#PIPELINE
# INVARIANTS:
# - changed source snapshots are reported stale [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#FORMS
# :END_MODULE_CONTRACT
import json
from urllib.parse import quote

from .builder_context import instance


def catalog_units(folder):
    """Localized rows in picture captions and interactive content, addressed by JSON pointer."""
    out = []
    def walk(value, path):
        if isinstance(value, dict):
            if isinstance(value.get(instance().source_language), str):
                out.append(('catalog:' + '/'.join(quote(str(x), safe='') for x in path), value))
            else:
                for key, child in value.items(): walk(child, [*path, key])
        elif isinstance(value, list):
            for i, child in enumerate(value): walk(child, [*path, i])
    pictures = json.loads((folder / 'pictures.json').read_text(encoding='utf-8')) if (folder / 'pictures.json').exists() else {}
    for key, picture in pictures.items():
        for part, item in (('', picture), ('ours', picture.get('ours') or {})):
            if isinstance(item.get('caption'), dict): walk(item['caption'], ['pictures', key, *([part] if part else []), 'caption'])
    play = folder / 'play.json'
    if play.exists(): walk(json.loads(play.read_text(encoding='utf-8')), ['play'])
    return out


def apply(units, tr):
    """Apply configured translations and return keys with a changed source snapshot."""
    stale = set()
    for key, row in units:
        t = tr.get(key) or {}
        translated = any(t.get(lang) or row.get(lang) for lang in instance().languages if lang != instance().source_language)
        if translated and t.get('_source') != row[instance().source_language]:
            stale.add(key)
        for lang, v in t.items():
            if lang in (x for x in instance().languages if x != instance().source_language) and not key.startswith('catalog:'):
                row[lang] = v
    return stale


def todo(units, stale):
    """Units for the next batch: stale, or missing in any language."""
    return {k: r[instance().source_language] for k, r in units if k in stale or not all(r.get(lang) for lang in (x for x in instance().languages if x != instance().source_language))}


def status(units, stale, tr):
    meta = tr.get('_meta', {})
    out = {}
    for lang in (x for x in instance().languages if x != instance().source_language):
        have = [k for k, r in units if r.get(lang)]
        out[lang] = {'units': len(units), 'current': sum(k not in stale for k in have),
                     'stale': sum(k in stale for k in have), 'missing': len(units) - len(have), 'last': meta.get(lang, '')}
    return out

