# START_MODULE_CONTRACT: MOD-READER-DOCUMENTS
# PURPOSE: Turn locally preserved literal records into escaped, self-contained document pages.
# PRD_REF: docs/PRD.md#TRUST
# INVARIANTS:
# - document pages render nested literal fields without losing keys, escape text and contain no research hyperlinks [review: engine lead]
# - a preserved document derivative cannot outlive its source checksum [review: engine lead]
# - arbitrary local JSON cannot substitute for a canonical record [review: engine lead]
# - feed document provenance and local page links follow the canonical record; excerpts never gain full links [review: engine lead]
# - document pages retain the record title, a local return link and the fictional-family notice [review: engine lead]
# - local source delivery retains inferred subjects and cannot restore an excluded document [review: engine lead]
# - delivering a local asset preserves its evidentiary source kind [review: engine lead]
# - private memory captions identify the telling without acquiring a document delivery route [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (declared reader surfaces, including private document exclusion)
# - MOD-FAMILY-WRITER (the sole filesystem and generation boundary)
# - docs/reader-export.md
# :END_MODULE_CONTRACT
import hashlib
import html
import json
import re

from .assets import sha256


def record_page(record, title='', language='en', fictional_family=False):
    esc = lambda value: html.escape(str(value))
    # An address inside a literal field remains text, never an active link.
    clean = lambda value: re.sub(r'https?://[^\s<>"\']+', '[reference retained in research]', str(value))
    def literal(value):
        if isinstance(value, dict):
            return '<table>' + ''.join(f'<tr><th>{esc(k)}</th><td>{literal(v)}</td></tr>'
                                      for k, v in value.items()) + '</table>'
        if isinstance(value, list):
            return '<ol>' + ''.join(f'<li>{literal(v)}</li>' for v in value) + '</ol>'
        return '' if value is None else esc(clean(value))
    rows = ''.join(f'<tr><th>{esc(k)}</th><td>{literal(v)}</td></tr>'
                   for k, v in record.get('fields', {}).items() if v not in (None, '', {}, []))
    events = ''.join(f'<li>{esc(clean(e.get("date", "")))} {esc(clean(e.get("place_text", "")))} {esc(clean(e.get("text", "")))}</li>'
                     for e in record.get('events', []))
    labels = {
        'ru': ('Вернуться к семейной истории', 'Вымышленная семья · демонстрация'),
        'pl': ('Wróć do historii rodziny', 'Fikcyjna rodzina · demonstracja'),
        'sv': ('Tillbaka till familjehistorien', 'Påhittad familj · demonstration'),
        'en': ('Back to the family story', 'Fictional family · demonstration'),
    }
    back, demo = labels.get(language, labels['en'])
    fictional = f'<p role="note">{demo}</p>' if record.get('fictional') or fictional_family else ''
    return (f'<!doctype html><html lang="{esc(language)}"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><style>body{{font:16px/1.5 system-ui;max-width:46rem;margin:1rem auto;padding:0 1rem}}'
            'table{max-width:100%;border-collapse:collapse}th,td{padding:.4rem;text-align:left;vertical-align:top;border-bottom:1px solid #ddd;overflow-wrap:anywhere}h1{font-size:1.6rem;overflow-wrap:anywhere}</style>'
            f'<a href="/">← {back}</a>{fictional}<h1>{esc(title)}</h1><table>{rows}</table><ul>{events}</ul></html>').encode()


def _local_sources(instance, graph, media, *, host_private=False):
    """Return generated pages; research-only URLs and local paths never reach a reader."""
    pages = {}
    records = {}
    from familiar.checks.engine import _known_people, life_status
    from familiar.instance.subjects import closure
    from familiar.tree.builder import read_json
    privacy = read_json(instance.path('privacy'), {})
    known = _known_people(instance, family_display=host_private)
    attached = {}
    for person in graph.get('people', {}).values():
        for image in person.get('media', []) + person.get('illustrations', []):
            asset = image.get('asset', '').lstrip('/')
            if asset in media:
                for key in ('sid', 'sourceSid'):
                    if image.get(key):
                        attached[image[key]] = asset
    for file in sorted(instance.path('records').rglob('*.json')):
        value = json.loads(file.read_text(encoding='utf-8-sig'))
        if value.get('id'):
            records[value['id']] = value
    for sid, source in graph.get('sources', {}).items():
        source.pop('url', None)
        local = source.pop('local', None)
        record = records.get(source.get('record', sid))
        source_file = None
        if local:
            if local.startswith('archive:'):
                root, rel = instance.path('originals'), local[8:]
            else:
                root, rel = instance.root, local
            file = (root / rel).resolve()
            allowed = [root.resolve()] if local.startswith('archive:') else [instance.root, instance.path('originals')]
            if not any(file.is_relative_to(base) for base in allowed):
                raise ValueError('source local path escapes its declared root')
            if file.is_file():
                source_file = file
        subjects = closure(instance, source, shape='source', people=known).people
        if record and source.get('record') != record['id']:
            subjects |= closure(instance, {'record': record['id']}, shape='source', people=known).people
        living_document = any(life_status(known.get(pid, {'id': pid}), privacy) != 'dead' for pid in subjects if pid)
        entry = next((name for name, (row, _) in media.items() if row.get('source_id') == sid), None)
        if (host_private and source.get('kind') == 'memory' and not record and not source_file
                and not entry and sid not in attached and not source.get('asset')):
            continue  # An attributed telling is not a living person's document.
        if living_document or (record and record.get('privacy') in {'living', 'living-possible'}) or not subjects:
            for key in list(source):
                if key not in {'id', 'kind'}:
                    source.pop(key)
            continue
        if entry:
            row = media[entry][0]
            if source_file and row.get('source_sha256') != sha256(source_file):
                raise ValueError('preserved document derivative is stale; regenerate and register it')
            source['asset'] = '/' + entry
            source.setdefault('kind', 'document' if row['kind'] == 'pdf' else 'image')
            continue
        if sid in attached and not record:
            # Reuse the already projected, registered gallery asset. This is not
            # a new derivative inferred from an arbitrary source.local path.
            source['asset'] = '/' + attached[sid]
            source.setdefault('kind', 'image')
            continue
        if record:
            name = 'sources/' + hashlib.sha256(sid.encode()).hexdigest()[:20] + '.html'
            from familiar.instance.publication import scan
            from familiar.instance.writer import cached
            title = source.get('title') or record.get('title') or sid
            fictional = instance.config['family'].get('fictional', False)
            def render(record=record, title=title, fictional=fictional):
                return record_page(scan(instance, record, 'record'), title,
                                   instance.source_language, fictional).decode('utf-8')
            pages[name] = cached('documents', sid,
                [record, title, instance.source_language, instance.languages, fictional, privacy,
                 instance.config.get('settings')], render).encode('utf-8')
            source['asset'] = '/' + name
            source.setdefault('kind', 'record')
    def link_documents(node):
        if isinstance(node, list):
            for child in node:
                link_documents(child)
        elif isinstance(node, dict):
            rid = node.get('record')
            if rid in records and ('read' in node or 'parts' in node):
                record = records[rid]
                if record.get('kind') == 'home-paper':
                    node['kind'] = 'home-paper'
                elif record.get('kind') == 'index-entry':
                    node['kind'] = 'index'
                elif node.get('asset'):
                    node['kind'] = 'archive-scan'
                source = next((s for sid, s in graph.get('sources', {}).items()
                               if s.get('record', sid) == rid and s.get('asset')), {})
                if 'excerpt' not in node and source.get('asset'):
                    node.setdefault('full', source['asset'])
            for child in node.values():
                link_documents(child)
    link_documents(graph.get('feeds', []))
    return pages
