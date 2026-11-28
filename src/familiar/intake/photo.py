# START_MODULE_CONTRACT: MOD-INTAKE-PHOTO
# PURPOSE: Attach one or a table of archival photos, or files relatives sent with a remark, in one family mutation.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - a rejected row leaves the gallery and original files untouched [review: engine lead]
# - replay preserves originals and does not duplicate photo attachments [review: engine lead]
# - a received original is checksum-verified and only a bounded worker raster is shown [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GALLERY
# - MOD-FAMILY-WRITER
# :END_MODULE_CONTRACT
import csv
import hashlib
import json
import re
from pathlib import Path

from familiar.instance import gallery
from familiar.instance.gate import boundary
from familiar.instance.writer import mutate
from familiar.reader.assets import publication_bytes
from familiar.reader.scans import derivative, first_page

from .core import safe


def _table(path):
    required = {'file', 'people', 'caption', 'received_from'}
    if path.suffix.lower() not in {'.csv', '.tsv'}:
        raise ValueError('expected a UTF-8 photo table in CSV or TSV format')
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t' if path.suffix.lower() == '.tsv' else ',', strict=True)
        fields = reader.fieldnames or []
        optional = {'when', 'sent_for', 'show', 'sheet', 'unnamed_faces', 'faces', 'crop'}
        if not required <= set(fields) or len(set(fields)) != len(fields) or set(fields) - required - optional:
            raise ValueError('photo table needs file, people, caption, received_from; optional ' + ', '.join(sorted(optional)))
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'photo table line {reader.line_num}: column count differs from header')
            yield (f'photo table line {reader.line_num}', path.parent / row['file'].strip(),
                   row['people'].split(), row['caption'], row.get('when', ''), row['received_from'], row)


def _flag(mark):
    value = mark.strip().casefold()
    if value not in {'', 'no', 'false', '0', 'yes', 'true', '1'}:
        raise ValueError('use yes or no for sheet and unnamed_faces')
    return value in {'yes', 'true', '1'}


def _faces(marks, subjects):
    """PERSON=x,y,w,h for each named person whose face a region shows, in the picture's own fractions."""
    faces = {}
    for mark in marks:
        pid, _, box = mark.partition('=')
        if pid.strip() not in subjects:
            raise ValueError(f'a face region names a person who is not on the photo: {pid.strip() or mark}')
        faces[pid.strip()] = gallery.region(box)
    return faces


def _rendition(path, raw):
    if raw.startswith(b'\xff\xd8'):
        suffix = 'jpg'
    elif raw.startswith(b'\x89PNG\r\n\x1a\n'):
        suffix = 'png'
    elif raw.startswith(b'RIFF') and raw[8:12] == b'WEBP':
        suffix = 'webp'
    else:
        suffix = None
    if suffix:
        try:
            return suffix, publication_bytes(raw, 'photo.' + suffix)
        except ValueError:
            pass  # Original metadata stays in the archive, outside the display.
    if path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff', '.gif', '.bmp',
                                   '.heic', '.heif', '.avif', '.pdf'}:
        raise ValueError('expected a local JPEG, PNG, WebP, HEIC, TIFF, GIF or BMP photograph or a PDF scan')
    clean = first_page(raw) if raw.startswith(b'%PDF-') else derivative(raw)
    if clean is None:
        raise ValueError('cannot make a display image; check the file and install Familiar with the images extra'
                         + (' and pypdfium2' if raw.startswith(b'%PDF-') else ''))
    return 'jpg', publication_bytes(clean, 'photo.jpg')


@boundary('writer')
def ingest(instance, path, *, table=False, people=(), caption='', when='', received_from='', expected_sha256=None,
           sent_for='', show=None, sheet=False, unnamed_faces=False, faces=(), crop=''):
    from familiar.checks.engine import _known_people
    known = _known_people(instance)
    target = safe(instance, 'gallery')
    original_gallery = target.read_bytes() if target.is_file() else None
    data = json.loads(original_gallery) if original_gallery is not None else {}
    if not isinstance(data, dict):
        raise ValueError('paths.gallery must hold a JSON object')
    stored = data.setdefault(gallery.KEY, {})
    if not isinstance(stored, dict):
        raise ValueError('gallery family_photographs must be an object')
    asset_ids = {Path(asset).stem: asset for asset in stored}
    changes, result, staged = {}, [], set()
    if not table and not people and not caption.strip() and not received_from.strip() and path.is_file():
        # The host returns to a photograph already taken in (a face or a crop later): the original file finds its record.
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        saved = next((row for row in stored.values() if isinstance(row, dict) and row.get('original_sha256') == digest), None)
        if saved:
            people, caption, when, received_from = saved['subjects'], saved['caption'], saved.get('when', ''), saved['received_from']
    rows = _table(path) if table else [(str(path), path, people, caption, when, received_from, {})]
    rights = None
    for location, file, subject_ids, label, era, witness, row in rows:
        try:
            is_sheet = sheet or _flag(row.get('sheet', ''))
            unnamed = unnamed_faces or _flag(row.get('unnamed_faces', '')) or not subject_ids
            purpose = (row.get('sent_for', '').strip() or sent_for.strip())
            choice = row.get('show', '').strip() or show
            if choice is not None and choice not in gallery.SHOW:
                raise ValueError('show must be gallery, card, or private')
            if not label.strip() or not witness.strip():
                raise ValueError('supply a caption and who provided the photograph')
            if unknown := sorted(set(subject_ids) - known.keys()):
                raise ValueError('unknown person IDs: ' + ', '.join(unknown) + '; inspect tree build --view working')
            subjects = sorted({known[pid]['id'] for pid in subject_ids})
            marks = [m for m in (row.get('faces', '').split(';') if row.get('faces') else faces) if m.strip()]
            regions = _faces([f"{known.get(m.partition('=')[0].strip(), {}).get('id', m.partition('=')[0].strip())}={m.partition('=')[2]}"
                              for m in marks], subjects)
            frame = gallery.region(row.get('crop') or crop) if (row.get('crop') or crop) else None
            raw = read_received(file, expected_sha256) if expected_sha256 is not None else file.read_bytes()
            original_sha256 = expected_sha256 or hashlib.sha256(raw).hexdigest()
            metadata = {'subjects': subjects, 'caption': label, 'when': era,
                        'received_from': witness, 'original_sha256': original_sha256}
            identity = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
            ident = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]
            asset = asset_ids.get(ident)
            saved = stored.get(asset, {})
            private_default = ((is_sheet and not saved.get('sheet')) or (unnamed and not saved.get('unnamed_faces'))
                               or (purpose and purpose != saved.get('sent_for')))
            purpose = purpose or saved.get('sent_for', '')
            is_sheet = is_sheet or saved.get('sheet', False)
            unnamed = unnamed or saved.get('unnamed_faces', False)
            display = choice or ('private' if private_default else saved.get('show', 'gallery'))
            if display != 'private':
                if not subjects:
                    raise ValueError('showing a photo requires at least one identified person')
                if rights is None:
                    rights = gallery.permits_display(instance)
                if not rights:
                    rights_path = instance.path('archive_rights')
                    raise ValueError(f'to show family photographs, the host declares effective permissions.family_app = true '
                                     f'in {rights_path} (paths.archive_rights); use --show private to archive this photo')
            preferences = {key: value for key, value in {'sent_for': purpose, 'sheet': is_sheet,
                           'unnamed_faces': unnamed, 'show': display if display != 'gallery' or choice else None,
                           'faces': dict(saved.get('faces', {}), **regions) or None, 'crop': frame or saved.get('crop')}.items() if value}
            if asset:
                saved = stored[asset]
                if any(saved.get(key) != value for key, value in metadata.items()):
                    raise ValueError('photo asset id collides with a different attachment: ' + asset)
                if expected_sha256 is not None and not saved.get('received_raster'):
                    raise ValueError('run instance upgrade to render this previously attached photograph')
                if asset not in staged:
                    gallery.asset_file(instance, asset, saved)
                status = 'already-attached'
                if any(saved.get(key) != value for key, value in preferences.items()):
                    saved.update(preferences)
                    status = 'updated'
            else:
                if expected_sha256 is None:
                    suffix, clean = _rendition(file, raw)
                else:
                    from familiar.reader.received_scan import raster
                    suffix, clean = 'jpg', publication_bytes(raster(raw), 'photo.jpg')
                asset = f'{gallery.PREFIX}{ident}.{suffix}'
                if instance.media_file('/' + asset):
                    raise ValueError('photo output would replace an existing asset: ' + asset)
                extension = file.suffix.lower()
                if not re.fullmatch(r'\.[a-z0-9]{1,8}', extension):
                    extension = '.image'
                original = f'{gallery.PREFIX}{ident}/original{extension}'
                changes[safe(instance, 'originals', original)] = raw
                if clean != raw or expected_sha256 is not None:
                    changes[safe(instance, 'media', asset)] = clean
                stored[asset] = dict(metadata, original=original, sha256=hashlib.sha256(clean).hexdigest(), **preferences)
                if expected_sha256 is not None:
                    stored[asset]['received_raster'] = True
                staged.add(asset)
                asset_ids[ident] = asset
                status = 'attached'
            result.append({'status': status, 'asset': '/' + asset, 'people': subjects,
                           'original': stored[asset]['original'], 'original_sha256': original_sha256,
                           'show': display, **{key: value for key, value in preferences.items() if key != 'show'}})
        except (OSError, ValueError) as exc:
            raise ValueError(f'{location}: {exc}') from exc
    if not result:
        raise ValueError('photo table has no rows')
    if changes or any(row['status'] == 'updated' for row in result):
        exclusive = list(changes)
        if original_gallery is None:
            exclusive.append(target)
        changes[target] = data
        mutate(instance, changes, exclusive=exclusive,
               expect={target: original_gallery} if original_gallery is not None else None)
    return {'kind': 'photo', 'attached': sum(row['status'] == 'attached' for row in result), 'photos': result}


def _taken(instance):
    target = safe(instance, 'gallery')
    stored = json.loads(target.read_bytes()).get(gallery.KEY, {}) if target.is_file() else {}
    return {row.get('original_sha256') for row in stored.values() if isinstance(row, dict)}


def read_received(path, digest):
    from familiar.desk.attachments import ATTACH_LIMITS
    with path.open('rb') as stream:
        raw = stream.read(ATTACH_LIMITS['file_bytes'] + 1)
    if len(raw) > ATTACH_LIMITS['file_bytes'] or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('received original differs from its recorded size limit or checksum')
    return raw


def received(instance):
    """List received originals with the remark and their stable local numbers."""
    from familiar.desk.attachments import stored_attachment
    from familiar.instance.writer import attachment_catalog, attachment_path
    taken = _taken(instance)
    for path in sorted(instance._inside('family/feedback/inbox').glob('*.json')):
        try:
            row = json.loads(path.read_bytes())
        except (OSError, ValueError):
            continue
        if not isinstance(row, dict) or not isinstance(row.get('files', []), list):
            continue
        try:
            catalog = attachment_catalog(instance, row['id'])
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            catalog = []
        added_digests = {item.get('sha256') for item in catalog if isinstance(item, dict)}
        old = [(item, False) for item in row.get('files', [])
               if isinstance(item, dict) and item.get('sha256') not in added_digests]
        for item, added in old + [(item, True) for item in catalog]:
            try:
                stored_attachment(item)
                original = attachment_path(instance, row['id'], item['n'], item['kind'],
                                           item['sha256'] if added else None)
            except (ValueError, TypeError, KeyError, AttributeError):
                continue
            if added or row.get('attachment_storage') != 2 or original.is_file():
                yield row, item, original, item['sha256'] in taken


def waiting(instance):
    return [{'id': row['id'], 'file': item['n'], 'kind': item['kind'], 'size': item['size'], 'name': item.get('name', ''),
             'received_at': row.get('received_at', ''), 'from': row.get('sender', {}).get('username', ''),
             'where': row.get('where', ''), 'person': _people(instance, row)[:1], 'text': row.get('text', ''),
             'path': str(path)} for row, item, path, taken in received(instance) if not taken]


def _people(instance, row):
    """The person a remark was written on: its card, its anchor, its subject or its ask."""
    found = [row[key] for key in ('person', 'anchor') if row.get(key)]
    if row.get('subject') and not row.get('ask_id'):
        found.append(row['subject'].split(':fact:')[0])
    if row.get('ask_id'):
        from familiar.instance.asks import get
        found.append(get(instance, row['ask_id'])[1].get('about', {}).get('person', ''))
    return [pid for pid in dict.fromkeys(found) if pid]


@boundary('writer')
def from_feedback(instance, identity, *, numbers=(), people=(), caption='', when='', received_from=''):
    """Take files a relative attached to a remark into the family photographs, with the remark's context."""
    row = next((r for r, *_ in received(instance) if r['id'] == identity), None)
    if row is None:
        raise ValueError('no remark with attached files: ' + identity + '; list them with intake attachment')
    people = list(people) or _people(instance, row)[:1]
    caption = caption or row.get('text', '').strip().split('\n')[0][:300]
    sender = row.get('sender', {})
    received_from = received_from or ', '.join(
        x for x in (sender.get('username', ''), sender.get('person', ''), 'remark ' + identity[:8]) if x)
    if not people:
        raise ValueError('the remark names no person; add --person ID')
    photos = []
    for row, item, path, _ in received(instance):
        if row['id'] == identity and (not numbers or item['n'] in numbers):
            if not path.is_file():
                raise ValueError(f'attachment {identity}/{item["n"]} is missing; run desk fetch-feedback')
            label = caption or item.get('name') or f'Attachment {item["n"]}'
            photos += ingest(instance, path, people=people, caption=label, when=when,
                             received_from=received_from, expected_sha256=item['sha256'])['photos']
    if not photos:
        raise ValueError('no such attached file in this remark')
    return {'kind': 'attachment', 'attached': sum(p['status'] == 'attached' for p in photos), 'photos': photos}
