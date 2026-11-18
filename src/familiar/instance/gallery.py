# START_MODULE_CONTRACT: MOD-FAMILY-GALLERY
# PURPOSE: Bind imported family photographs to identified people and exact local bytes.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - every identified person receives the same photo and the full subject list [review: engine lead]
# - original bytes stay private when a clean display rendition is needed [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-EDITION
# - MOD-ARCHIVE-RIGHTS
# - MOD-READER-ASSETS
# :END_MODULE_CONTRACT
import json
import re

from .archive import photograph_rights

KIND = 'family-photograph'
KEY = 'family_photographs'
PREFIX = 'family-photos/'


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
        if not isinstance(row.get('subjects'), list) or not row['subjects'] or any(
                not isinstance(pid, str) or not pid for pid in row['subjects']):
            raise ValueError('family photograph needs identified people: ' + asset)
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
    rendition = (original if row['original_sha256'] == row['sha256'] else
                 contained(instance.path('media'), asset))
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
        subjects = list(dict.fromkeys(aliases.get(pid, pid) for pid in row['subjects']))
        image = {'kind': KIND, 'photo': True, 'asset': '/' + asset, 'sid': asset,
                 'title': row['caption'], 'caption': row['caption'], 'subjects': subjects}
        if row.get('when'):
            image['description'] = row['when']
        for pid in subjects:
            media = people[pid].setdefault('media', [])
            if not any(isinstance(other, dict) and other.get('asset') == image['asset'] for other in media):
                media.append(image)
