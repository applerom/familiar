# START_MODULE_CONTRACT: MOD-FAMILY-GALLERY
# PURPOSE: Bind imported family photographs to identified people and exact local bytes.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - every identified person receives the same photo and the full subject list [review: engine lead]
# - original bytes stay private when a clean display rendition is needed [review: engine lead]
# - archival-only photographs have no reader asset and card photographs stay out of the album [review: engine lead]
# - a face region or a display crop names only a region of a pictured person's photo; display bytes and the original stay as received [review: engine lead]
# - unnamed faces stay home; outside portraits contain only the pixels of the person's marked region [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-EDITION
# - MOD-ARCHIVE-RIGHTS
# - MOD-READER-ASSETS
# :END_MODULE_CONTRACT
import json
import re
from hashlib import sha256
from io import BytesIO
from math import ceil, floor

from .archive import photograph_rights

KIND = 'family-photograph'
KEY = 'family_photographs'
PREFIX = 'family-photos/'
SHOW = ('gallery', 'card', 'private')


def region(value):
    """A part of the picture in its own coordinates: x, y, width, height as fractions of the whole."""
    if isinstance(value, str):
        value = [part.strip() for part in value.split(',')]
    try:
        box = [round(float(part), 4) for part in value]
    except (TypeError, ValueError):
        box = []
    if len(box) != 4 or min(box) < 0 or box[2] <= 0 or box[3] <= 0 or box[0] + box[2] > 1.0001 or box[1] + box[3] > 1.0001:
        raise ValueError('a region is x,y,w,h as fractions of the picture, inside 0..1')
    return box


def photographs(instance):
    immutable = getattr(instance, '_immutable_snapshot', False)
    if immutable and hasattr(instance, '_family_photographs'):
        return instance._family_photographs
    path = instance.path('gallery')
    if not path.is_file():
        return {}
    data = json.loads(path.read_bytes())
    rows = data.get(KEY, {}) if isinstance(data, dict) else {}
    if not isinstance(rows, dict):
        raise ValueError('gallery family_photographs must be an object')
    for asset, row in rows.items():
        match = re.fullmatch(r'family-photos/([a-f0-9]{32})\.(?:jpg|png|webp)', asset)
        if not match:
            raise ValueError('invalid family photograph asset: ' + asset)
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip()
                for k in ('caption', 'received_from', 'original', 'original_sha256', 'sha256')):
            raise ValueError('incomplete family photograph: ' + asset)
        if row.get('show', 'gallery') not in SHOW:
            raise ValueError('family photograph show must be gallery, card, or private: ' + asset)
        if not isinstance(row.get('subjects'), list) or (not row['subjects'] and row.get('show') != 'private') or any(
                not isinstance(pid, str) or not pid for pid in row['subjects']):
            raise ValueError('family photograph needs identified people: ' + asset)
        if not isinstance(row.get('sent_for', ''), str) or any(type(row.get(k, False)) is not bool for k in ('sheet', 'unnamed_faces')):
            raise ValueError('family photograph purpose must be text and sheet/unnamed_faces must be boolean: ' + asset)
        try:
            if 'crop' in row:
                region(row['crop'])
            faces = row.get('faces', {})
            if not isinstance(faces, dict) or any(pid not in row['subjects'] or region(box) != box for pid, box in faces.items()):
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError('family photograph crop and faces are regions of named people: ' + asset) from None
        if not isinstance(row.get('when', ''), str):
            raise ValueError('family photograph date or era must be text: ' + asset)
        if not re.fullmatch(r'family-photos/' + match[1] + r'/original\.[a-z0-9]{1,8}', row['original']):
            raise ValueError('invalid original family photograph path: ' + asset)
    if immutable:
        instance._family_photographs = rows
    return rows


def photograph(instance, asset):
    if isinstance(asset, str) and asset.startswith('/' + PREFIX):
        return photographs(instance).get(asset[1:])
    return None


def permits_display(instance):
    rights = photograph_rights(instance, {'kind': KIND})
    return bool(rights and rights['permissions']['family_app'])


def files(instance, asset, row):
    from familiar.reader.assets import contained
    original = contained(instance.path('originals'), row['original'])
    separate = row.get('received_raster') or row['original_sha256'] != row['sha256']
    rendition = contained(instance.path('media'), asset) if separate else original
    return original, rendition


def asset_file(instance, asset, row):
    from .writer import input_digest
    original, rendition = files(instance, asset, row)
    if not original.is_file() or input_digest(original) != row['original_sha256']:
        raise ValueError('family photograph original checksum mismatch: ' + asset)
    if not rendition.is_file() or input_digest(rendition) != row['sha256']:
        raise ValueError('family photograph display checksum mismatch: ' + asset)
    return rendition


def attach(instance, graph):
    rows = photographs(instance)
    if not rows or not permits_display(instance):
        return
    aliases, people = graph.get('identityAliases', {}), graph['people']
    for asset, row in rows.items():
        if row.get('show') == 'private':
            continue
        subjects = list(dict.fromkeys(aliases.get(pid, pid) for pid in row['subjects']))
        image = {'kind': KIND, 'photo': True, 'asset': '/' + asset, 'sid': asset,
                 'title': row['caption'], 'caption': row['caption'], 'subjects': subjects}
        if row.get('when'):
            image['description'] = row['when']
        if row.get('show') == 'card':
            image['cardOnly'] = True
        if row.get('crop'):
            image['crop'] = row['crop']
        faces = {aliases.get(pid, pid): box for pid, box in row.get('faces', {}).items()}
        for pid in subjects:
            media = people[pid].setdefault('media', [])
            if not any(isinstance(other, dict) and other.get('asset') == image['asset'] for other in media):
                media.append(dict(image, face=faces[pid]) if pid in faces else image)


def external_faces(graph, photos, read):
    """Project a checked gallery to face files and remove the protected originals."""
    blocked = {asset: photo for asset, photo in photos.items()
               if photo.get('unnamed_faces') or photo.get('show') == 'private'
               or photo.get('faces') or len(photo['subjects']) > 1}
    if not blocked:
        return graph, {}, set()
    derived, crops = {}, {}

    def portrait(image):
        original = image['asset'][1:]
        photo, box = blocked[original], image.get('face')
        if (photo.get('unnamed_faces') or photo.get('show') == 'private'
                or image.get('kind') != KIND or box not in photo.get('faces', {}).values()):
            return None
        key = original, tuple(box)
        if key not in crops:
            data = _face_bytes(read(original), box)
            crops[key] = None
            if data:
                name = 'family-faces/' + sha256(data).hexdigest() + '.png'
                derived[name] = data
                crops[key] = name
        if name := crops[key]:
            return {k: v for k, v in image.items()
                    if k not in {'face', 'crop', 'full', 'originalAsset', 'orig', 'ours', 'sourceSid', 'url'}
                    } | {'asset': '/' + name, 'sid': name, 'cardOnly': True, 'is_portrait': True}
        return None

    originals = {'/' + name for name in blocked}
    refs = re.compile('(?:' + '|'.join(re.escape(name) for name in sorted(originals)) + r')(?![\w./-])')

    def clean(value):
        if isinstance(value, dict):
            if isinstance(value.get('asset'), str) and value['asset'] in originals:
                return None
            return {k: safe for k, child in value.items() if
                    (safe := clean(child)) is not None or child is None}
        if isinstance(value, list):
            return [safe for child in value if (safe := clean(child)) is not None or child is None]
        if isinstance(value, str):
            return None if value in originals or value in blocked else refs.sub('', value)
        return value

    people = {}
    for pid, person in graph.get('people', {}).items():
        if not any(isinstance(img.get('asset'), str) and img['asset'] in originals for img in person.get('media', [])):
            people[pid] = person
            continue
        people[pid] = dict(person, media=[
            picked for img in person['media'] if (picked := portrait(img)
                if isinstance(img.get('asset'), str) and img['asset'] in originals else img) is not None])
    return clean(dict(graph, people=people)), derived, set(blocked)


def _face_bytes(raw, box):
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError('Cropping an outside portrait needs Pillow. Install familiar[images].') from exc

    with Image.open(BytesIO(raw)) as source:
        width, height = source.size
        x, y, w, h = box
        rect = ceil(x * width), ceil(y * height), floor((x + w) * width), floor((y + h) * height)
        left, top, right, bottom = rect
        if left >= right or top >= bottom or rect == (0, 0, width, height):
            return None
        face = source.crop(rect).convert('RGB')
        face.info.clear()
        face.thumbnail((640, 640))
        out = BytesIO()
        face.save(out, 'PNG')
        return out.getvalue()
