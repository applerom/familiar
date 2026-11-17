# START_MODULE_CONTRACT: MOD-RESEARCH-DELIVERY
# PURPOSE: Save a research decision or a literal document and its captioned cut-outs through the family writer.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - document intake preserves literal reading and registers checksummed media with every named subject [review: engine lead]
# - an existing contribution or record is never silently replaced [review: engine lead]
# CHANGES_WITH:
# - MOD-TREE-REVISIONS (contribution revision fields)
# - MOD-READER-ASSETS (permanent manifest)
# :END_MODULE_CONTRACT
import copy
import hashlib
import json
import re

from familiar.instance.writer import mutate


def token(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', value):
        raise ValueError('Use an ASCII id beginning with a letter (maximum 64 characters)')
    return value


def contribute(instance, data):
    data = copy.deepcopy(data)
    target = instance.path('contributions') / token(data['author']) / (token(data.pop('id')) + '.json')
    mutate(instance, {target: data}, exclusive=[target])
    return {'contribution': str(target.relative_to(instance.root))}


def document(instance, data, input_path, author):
    record = copy.deepcopy(data['record'])
    rid, author = token(record['id']), token(author)
    record_path = instance.path('records') / (rid + '.json')
    target = instance.path('contributions') / author / (rid + '.json')
    from familiar.tree.builder import build
    graph = build(instance, view='working')
    subjects = data.get('subjects', [])
    if not isinstance(subjects, list) or not subjects or any(p not in graph['people'] for p in subjects):
        raise ValueError('Document subjects must name existing canonical people')
    record['subjects'] = list(record.get('subjects', [])) + list(subjects)
    source = {'kind': record['kind'], 'record': rid, 'title': record['title'], 'subjects': subjects}
    package = {'schema': 1, 'author': author, 'sources': {rid: source}, 'media': {}, 'facts': {}}
    changes = {record_path: record}
    manifest_path = instance.path('media') / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {'schema_version': 1, 'assets': []}
    for index, snippet in enumerate(data.get('snippets', []), 1):
        if not snippet.get('caption') or not snippet.get('read'):
            raise ValueError(f'snippets[{index}]: caption and literal read are required')
        path = (input_path.parent / snippet['file']).resolve()
        raw = path.read_bytes()
        from familiar.reader.assets import publication_bytes
        if path.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp'}:
            raise ValueError('A cut-out must be PNG, JPEG or WebP')
        publication_bytes(raw, path.name.lower())
        name = f'documents/{rid}/{index}{path.suffix.lower()}'
        asset_id = f'{rid}-{index}'
        if any(r.get('id') == asset_id or r.get('export') == name for r in manifest['assets']):
            raise ValueError('Document media already registered: ' + asset_id)
        media_path = instance.path('media') / name
        if media_path.exists():
            raise ValueError('Document media already exists: ' + name)
        changes[media_path] = raw
        manifest['assets'].append({'id': asset_id, 'file': name, 'export': name,
            'sha256': hashlib.sha256(raw).hexdigest(), 'kind': 'document-scan',
            'origin': 'research', 'subjects': subjects})
        for pid in subjects:
            package['media'].setdefault(pid, []).append({'sid': asset_id, 'sourceSid': rid, 'record': rid,
                'asset': '/' + name, 'title': snippet['caption'], 'caption': snippet['caption'],
                'description': snippet['read'], 'kind': 'document-scan', 'photo': False, 'subjects': subjects})
            package['facts'].setdefault(pid, []).append({'label': 'document',
                'text': snippet['read'], 'status': 'export', 'sources': [rid]})
    if not record.get('reading') and not record.get('fields'):
        record['reading'] = '\n\n'.join(s['read'] for s in data.get('snippets', []))
    if not package['facts']:
        for pid in subjects:
            package['facts'][pid] = [{'label': 'document', 'text': record.get('reading') or
                '\n'.join(f'{key}: {value}' for key, value in record['fields'].items()),
                'status': 'export', 'sources': [rid]}]
    if data.get('snippets'):
        changes[manifest_path] = manifest
    changes[target] = package
    mutate(instance, changes, exclusive=[record_path, target])
    return {'record': str(record_path.relative_to(instance.root)),
            'contribution': str(target.relative_to(instance.root)), 'subjects': subjects}
