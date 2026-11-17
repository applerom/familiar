# START_MODULE_CONTRACT: MOD-FEED-DOC
# PURPOSE: Prepare local document crops and catalog readings from an explicitly supplied frame.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - authoring helpers reject paths outside their family catalogs [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (declared reader surfaces and default-deny policy)
# - MOD-FAMILY-WRITER (the sole filesystem and generation boundary)
# - docs/PRD.md#FORMS
# :END_MODULE_CONTRACT
import hashlib
import json
from pathlib import Path


def parse_box(text, size):
    parts = [float(x) for x in text.split(',')]
    if len(parts) != 4:
        raise SystemExit('box: four numbers x0,y0,x1,y1')
    if all(0 <= x <= 1 for x in parts):  # fractions of the frame
        parts = [parts[0] * size[0], parts[1] * size[1], parts[2] * size[0], parts[3] * size[1]]
    x0, y0, x1, y1 = (round(x) for x in parts)
    if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]):
        raise SystemExit(f'box {x0},{y0},{x1},{y1} is outside the frame {size[0]}x{size[1]}')
    return x0, y0, x1, y1


from familiar.instance.gate import boundary


@boundary('writer')
def add(instance, feed, key, frame, box, reading, source=None, where=None, dry_run=False, record=None, caption=None):
    if not all((frame, box, reading)):
        raise ValueError('provide FRAME BOX READING or --index READING')
    from PIL import Image
    folder = instance.path('feeds') / feed
    PUB = instance.path('media')
    if not key or any(c in key for c in '/\\:') or '..' in key:
        raise ValueError('invalid document key')
    if not folder.resolve().is_relative_to(instance.path('feeds')):
        raise ValueError('invalid feed')
    if not (folder / 'feed.json').exists():
        raise SystemExit(f'{folder}: no feed.json')
    if not (reading or '').strip():
        raise SystemExit('reading is empty: look at the crop and transcribe it (DOC-3)')
    frame = Path(frame)
    if not frame.is_file():
        raise SystemExit(f'{frame}: no such frame')
    report = []
    changes = {}
    docs_path = folder / 'documents.json'
    docs = json.loads(docs_path.read_text(encoding='utf-8-sig')) if docs_path.exists() else {}
    with Image.open(frame) as im:
        rect = parse_box(box, im.size)
        entry = docs.setdefault(key, {})
        if record:
            from familiar.checks.engine import record_path
            if not record_path(instance, record).is_file():
                raise ValueError('unknown corpus record: ' + record)
            entry['record'] = record
        if caption:
            entry['caption'] = caption
        if entry.get('kind') == 'index':
            raise SystemExit(f'{key}: an index document has no image')
        frame_hash = hashlib.sha256(frame.read_bytes()).hexdigest()
        if entry.get('snippets'):
            previous = entry.get('frame_sha256')
            if previous is None:
                old = PUB / entry.get('full', '').lstrip('/')
                previous = hashlib.sha256(old.read_bytes()).hexdigest() if old.is_file() else None
            if previous != frame_hash:
                raise ValueError(f'{key}: frame changed or unavailable; use a new document key and recrop')
        entry['frame_sha256'] = frame_hash
        full_rel = f'/records/{feed}/full/{key}{frame.suffix.lower()}'
        entry['full'] = full_rel
        snippets = entry.setdefault('snippets', [])
        boxes = entry.setdefault('boxes', [])  # catalog bookkeeping, parallel to snippets; the builder does not copy it
        boxes += [None] * (len(snippets) - len(boxes))
        at = boxes.index(list(rect)) if list(rect) in boxes else None
        if at is not None:
            snippets[at]['read'] = reading
            n = at + 1
            report.append(f'{key}: crop {n} has the same box; reading replaced')
        else:
            n = len(snippets) + 1
            snippets.append({'asset': f'/records/{feed}/snip/{key}-{n}.jpg', 'read': reading})
            boxes.append(list(rect))
            report.append(f'{key}: crop {n} added, box {rect}')
        asset = snippets[n - 1]['asset']
        if source:
            entry['source'] = source
        if where:
            entry['where'] = where
        for k in ('source', 'where'):
            if not entry.get(k):
                report.append(f'WARNING: {key} has no "{k}" (DOC-3 asks where to look); pass --{k}')
        if '**' not in reading:
            report.append('WARNING: the reading marks no words in **bold** (DOC-3)')
        if not dry_run:
            from io import BytesIO
            buffer = BytesIO()
            im.convert('RGB').crop(rect).save(buffer, 'JPEG', quality=92)
            changes[PUB / full_rel.lstrip('/')] = frame.read_bytes()
            changes[PUB / asset.lstrip('/')] = buffer.getvalue()
            report.append('Crop and full frame prepared; inspect the crop before trusting the reading')
    if not dry_run:
        from familiar.instance.writer import mutate
        changes[docs_path] = docs
        mutate(instance, changes)
    return report



@boundary('writer')
def add_index(instance, feed, key, reading, source, where):
    from .service import folders
    folder = folders(instance, feed)[0]
    if not key or any(c in key for c in '/\\:') or '..' in key:
        raise ValueError('invalid document key')
    if not all(isinstance(x, str) and x.strip() for x in (reading, source, where)):
        raise ValueError('index entry requires reading, --source and --where')
    path = folder / 'documents.json'
    docs = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if key in docs:
        raise ValueError('document already exists; use a new key')
    from familiar.instance.writer import mutate
    record_id = 'index-' + key
    record_path = instance.path('records') / (record_id + '.json')
    record = {'id': record_id, 'kind': 'index-entry', 'title': key,
              'source': {'description': source, 'locator': where}, 'language': [instance.source_language],
              'fields': {'Reading': reading}, 'reading': reading, 'subjects': [], 'saved_result': None}
    docs[key] = {'kind': 'index', 'read': reading, 'source': source, 'where': where,
                 'record': record_id, 'caption': key, 'snippets': [], 'subjects': [], 'image_seen': False}
    mutate(instance, {path: docs, record_path: record}, exclusive=[record_path])
    return f'{key}: index reading saved; image not seen'
