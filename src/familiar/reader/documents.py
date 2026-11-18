# START_MODULE_CONTRACT: MOD-READER-DOCUMENTS
# PURPOSE: Pair locally preserved records with their checked capture and literal reading.
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
from pathlib import Path

from .assets import publication_bytes, sha256
from .scans import derivative, selected_capture

BACK_SCRIPT = 'sources/document-back.js'
_BACK = b"""document.getElementById('document-back').addEventListener('click', (event) => {
  if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  if (window.navigation?.canGoBack || (document.referrer && history.length > 1)) {
    event.preventDefault();
    history.back();
  } else if (window.opener || history.length <= 1) {
    // Opened in its own tab from a story or a card: going back means returning to that tab.
    event.preventDefault();
    window.close();
    setTimeout(() => { location.href = event.target.href; }, 150);
  }
});
"""


def record_page(record, title='', language='en', fictional_family=False, *, scan=None):
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
        'ru': ('Назад', 'Вымышленная семья · демонстрация', 'Открыть снимок в полном размере', 'Открыть PDF'),
        'pl': ('Wróć', 'Fikcyjna rodzina · demonstracja', 'Otwórz skan w pełnym rozmiarze', 'Otwórz PDF'),
        'sv': ('Tillbaka', 'Påhittad familj · demonstration', 'Öppna bilden i full storlek', 'Öppna PDF'),
        'en': ('Back', 'Fictional family · demonstration', 'Open scan at full size', 'Open PDF'),
    }
    back, demo, enlarge, pdf = labels.get(language, labels['en'])
    fictional = f'<p role="note">{demo}</p>' if record.get('fictional') or fictional_family else ''
    if isinstance(title, dict):
        title = title.get(language) or next(iter(title.values()), '')
    visual = ''
    if scan:
        url = esc(scan)
        visual = (f'<p><a href="{url}">{pdf}</a></p>' if scan.endswith('.pdf') else
                  f'<a class="document-scan" href="{url}" aria-label="{enlarge}"><img src="{url}" alt="{esc(title)}"></a>')
    reading = record.get('reading')
    if isinstance(reading, dict):
        reading = reading.get(language) or next(iter(reading.values()), '')
    content = (f'<p>{literal(reading)}</p>' if reading else '')
    content += f'<table>{rows}</table>' if rows else ''
    content += f'<ul>{events}</ul>' if events else ''
    content = f'<div class="document-reading">{content}</div>' if content else ''
    return (f'<!doctype html><html lang="{esc(language)}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title>'
            '<style>body{margin:0;background:var(--paper,#f6f1e7);color:var(--ink,#1f2a26);'
            'font:var(--t-ui,15px)/1.5 var(--font-ui,system-ui)}'
            '.document-page{box-sizing:content-box;max-width:var(--measure,680px);margin:auto;'
            'padding:var(--s5,24px) var(--gutter,20px) var(--s8,64px);overflow-wrap:anywhere}'
            '.document-page a{color:var(--act,#2f5b48)}'
            '.document-page h1{margin:var(--s4,16px) 0;'
            'font:500 var(--t-xl,30px)/var(--lh-tight,1.18) var(--font-story,Georgia)}'
            '.document-scan{display:block;margin-bottom:var(--s5,24px);background:var(--paper-deep,#ece4d4)}'
            '.document-scan img{width:100%;height:auto;display:block;border-radius:var(--r-xs,4px)}'
            '.document-reading{background:var(--doc-paper,#fbf5e4);color:var(--doc-ink,#4a3a26);'
            'padding:var(--s4,16px);border-radius:var(--r-xs,4px)}'
            '.document-reading p{white-space:pre-wrap;margin-top:0}'
            '.document-page table{width:100%;table-layout:fixed;border-collapse:collapse}'
            '.document-page th,.document-page td{padding:.4rem;text-align:start;vertical-align:top;'
            'border-bottom:1px solid var(--rule,#ddd3c1)}'
            '.document-page th{width:32%}.document-page td table{font-size:inherit}</style>'
            f'<script defer src="/{BACK_SCRIPT}"></script></head><body><main class="document-page">'
            f'<a id="document-back" href="/">← {back}</a>{fictional}<h1>{esc(title)}</h1>{visual}'
            f'{content}</main></body></html>').encode()


def _rendition(file, reference, record, name, generated, bindings, rendered):
    suffix = Path(name).suffix.lower()
    if suffix not in {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.tif', '.tiff', '.bmp', '.pdf'}:
        return None
    selector = reference.page if reference else None
    key = file, selector
    if key not in rendered:
        raw = file.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != sha256(file):
            raise ValueError('record capture changed during read')
        rendered[key] = digest, derivative(raw, pdf=suffix == '.pdf', page=selector)
    digest, content = rendered[key]
    if reference:
        note = record.get('collector_note')
        checks = note.get('frame_sha256') if isinstance(note, dict) else None
        expected = checks.get(reference.locator) if isinstance(checks, dict) else None
        if expected and expected != digest:
            return None
    if content is None:
        return None
    extension = 'pdf' if suffix == '.pdf' else 'jpg'
    derivative_digest = hashlib.sha256(content).hexdigest()
    name = f'sources/scans/{digest[:20]}-{derivative_digest}.{extension}'
    if extension == 'jpg':
        publication_bytes(content, name)
    generated[name] = content
    bindings[name] = digest
    return '/' + name


def _local_sources(instance, graph, media, *, host_private=False):
    """Return document pages, their web derivatives, and original-byte digests."""
    generated, bindings, rendered = {}, {}, {}
    records = {}
    from familiar.checks.engine import _known_people, life_status
    from familiar.instance.subjects import closure
    from familiar.tree.builder import read_json
    privacy = read_json(instance.path('privacy'), {})
    known = _known_people(instance, family_display=host_private)
    registered = {}
    for name, (row, _) in media.items():
        if row.get('source_id'):
            registered.setdefault(row['source_id'], name)
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
        source.pop('image', None)  # Output-only reference, never an authored delivery path.
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
        entry = registered.get(sid)
        if (host_private and source.get('kind') == 'memory' and not record and not source_file
                and not entry and sid not in attached and not source.get('asset')):
            continue  # An attributed telling is not a living person's document.
        if living_document or (record and record.get('privacy') in {'living', 'living-possible'}) or not subjects:
            for key in list(source):
                if key not in {'id', 'kind'}:
                    source.pop(key)
            continue
        capture_ref, capture = selected_capture(instance, record) if record and 'excerpt' not in source else (None, None)
        if entry and (original := source_file or capture) and media[entry][0].get('source_sha256') != sha256(original):
            raise ValueError('preserved document derivative is stale; regenerate and register it')
        entry = entry or attached.get(sid)
        if not entry and source.get('asset', '').lstrip('/') in media:
            entry = source['asset'].lstrip('/')
        image = None
        # The source's own registered picture (a cut-out) comes before the whole sheet its record names.
        if entry and 'excerpt' not in source:
            image = _rendition(media[entry][1], None, None, entry, generated, bindings, rendered)
        elif capture:
            image = _rendition(capture, capture_ref, record, capture_ref.locator, generated, bindings, rendered)
        if record or image:
            name = 'sources/' + hashlib.sha256(sid.encode()).hexdigest()[:20] + '.html'
            from familiar.instance.publication import scan
            from familiar.instance.writer import cached
            title = source.get('title') or (record or {}).get('title') or sid
            fictional = instance.config['family'].get('fictional', False)
            def render(record=record, title=title, fictional=fictional, image=image):
                return record_page(scan(instance, record or {}, 'record'), title,
                                   instance.source_language, fictional, scan=image).decode('utf-8')
            generated[name] = cached('documents', sid,
                [record, title, instance.source_language, instance.languages, fictional, privacy,
                 instance.config.get('settings'), image], render).encode('utf-8')
            generated[BACK_SCRIPT] = _BACK
            source['asset'] = '/' + name
            if image and not image.endswith('.pdf'):
                source['image'] = image
            source.setdefault('kind', 'record' if record else 'document' if image.endswith('.pdf') else 'image')
        elif entry and not record:
            source['asset'] = '/' + entry
            source.setdefault('kind', 'document' if media[entry][0]['kind'] == 'pdf' else 'image')
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
    return generated, bindings
