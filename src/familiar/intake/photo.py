# START_MODULE_CONTRACT: MOD-INTAKE-PHOTO
# PURPOSE: Attach one or a table of archival photos in a single family mutation.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - a rejected row leaves the gallery and original files untouched [review: engine lead]
# - replay preserves originals and does not duplicate photo attachments [review: engine lead]
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
from familiar.reader.scans import derivative

from .core import safe


def _table(path):
    required = {'file', 'people', 'caption', 'received_from'}
    if path.suffix.lower() not in {'.csv', '.tsv'}:
        raise ValueError('expected a UTF-8 photo table in CSV or TSV format')
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t' if path.suffix.lower() == '.tsv' else ',', strict=True)
        fields = reader.fieldnames or []
        if not required <= set(fields) or len(set(fields)) != len(fields) or set(fields) - required - {'when'}:
            raise ValueError('photo table needs file, people, caption, received_from; optional when')
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'photo table line {reader.line_num}: column count differs from header')
            yield (f'photo table line {reader.line_num}', path.parent / row['file'].strip(),
                   row['people'].split(), row['caption'], row.get('when', ''), row['received_from'])


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
    if path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff', '.gif', '.bmp'}:
        raise ValueError('expected a local JPEG, PNG, WebP, TIFF, GIF or BMP photograph')
    clean = derivative(raw)
    if clean is None:
        raise ValueError('cannot make a display image; check the file and install Familiar with the images extra')
    return 'jpg', publication_bytes(clean, 'photo.jpg')


@boundary('writer')
def ingest(instance, path, *, table=False, people=(), caption='', when='', received_from=''):
    from familiar.checks.engine import _known_people
    if not gallery.permits_display(instance):
        raise ValueError('declare effective family_app permission at paths.archive_rights before attaching photographs')
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
    rows = _table(path) if table else [(str(path), path, people, caption, when, received_from)]
    for location, file, subject_ids, label, era, witness in rows:
        try:
            if not subject_ids or not label.strip() or not witness.strip():
                raise ValueError('supply at least one person ID, a caption and who provided the photograph')
            if unknown := sorted(set(subject_ids) - known.keys()):
                raise ValueError('unknown person IDs: ' + ', '.join(unknown) + '; inspect tree build --view working')
            subjects = sorted({known[pid]['id'] for pid in subject_ids})
            raw = file.read_bytes()
            original_sha256 = hashlib.sha256(raw).hexdigest()
            metadata = {'subjects': subjects, 'caption': label, 'when': era,
                        'received_from': witness, 'original_sha256': original_sha256}
            identity = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
            ident = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]
            if asset := asset_ids.get(ident):
                saved = stored[asset]
                if any(saved.get(key) != value for key, value in metadata.items()):
                    raise ValueError('photo asset id collides with a different attachment: ' + asset)
                if asset not in staged:
                    gallery.asset_file(instance, asset, saved)
                status = 'already-attached'
            else:
                suffix, clean = _rendition(file, raw)
                asset = f'{gallery.PREFIX}{ident}.{suffix}'
                if instance.media_file('/' + asset):
                    raise ValueError('photo output would replace an existing asset: ' + asset)
                extension = file.suffix.lower()
                if not re.fullmatch(r'\.[a-z0-9]{1,8}', extension):
                    extension = '.image'
                original = f'{gallery.PREFIX}{ident}/original{extension}'
                changes[safe(instance, 'originals', original)] = raw
                if clean != raw:
                    changes[safe(instance, 'media', asset)] = clean
                stored[asset] = dict(metadata, original=original, sha256=hashlib.sha256(clean).hexdigest())
                staged.add(asset)
                asset_ids[ident] = asset
                status = 'attached'
            result.append({'status': status, 'asset': '/' + asset, 'people': subjects,
                           'original': stored[asset]['original'], 'original_sha256': original_sha256})
        except (OSError, ValueError) as exc:
            raise ValueError(f'{location}: {exc}') from exc
    if not result:
        raise ValueError('photo table has no rows')
    if changes:
        exclusive = list(changes)
        if original_gallery is None:
            exclusive.append(target)
        changes[target] = data
        mutate(instance, changes, exclusive=exclusive,
               expect={target: original_gallery} if original_gallery is not None else None)
    return {'kind': 'photo', 'attached': sum(row['status'] == 'attached' for row in result), 'photos': result}
