# START_MODULE_CONTRACT: MOD-RESEARCH-DELIVERY
# PURPOSE: Save a research decision or a literal document and its captioned cut-outs through the family writer.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - document intake preserves literal reading and registers checksummed media with every named subject [review: engine lead]
# - an existing contribution or record is never silently replaced [review: engine lead]
# - document subjects resolve against working people, including merged research ids [review: engine lead]
# CHANGES_WITH:
# - MOD-TREE-REVISIONS (contribution revision fields)
# - MOD-READER-ASSETS (permanent manifest)
# :END_MODULE_CONTRACT
import copy
import hashlib
import json
import re

from familiar.instance.writer import mutate

from .coverage_evidence import place_scope


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
    subjects = data.get('subjects', [])
    if not isinstance(subjects, list):
        raise ValueError('Document subjects must be an array of working person IDs')
    scope = place_scope(record)
    if ('place_scope' in record or not subjects) and scope is None:
        raise ValueError('Give record.place_scope with place and surname for a record without tree subjects')
    if subjects:
        from familiar.tree.builder import build, people_index
        people = people_index(build(instance, view='working'))
        if any(not isinstance(p, str) or p not in people for p in subjects):
            raise ValueError('Document subjects must name working people; inspect ids with tree build --view working or tree person')
        subjects = list(dict.fromkeys(people[p]['id'] for p in subjects))
    record['subjects'] = list(record.get('subjects', [])) + list(subjects)
    if scope:
        record['place_scope'] = scope
    if not subjects:
        from familiar.instance.subjects import explicit_subjects
        if explicit_subjects(record):
            raise ValueError('List the record’s tree subjects in the form’s subjects array')
        if not record.get('read'):
            record['read'] = {'by': author}
    source = {'kind': record['kind'], 'record': rid, 'title': record['title'], 'subjects': subjects}
    package = {'schema': 1, 'author': author, 'sources': {rid: source}, 'media': {}, 'facts': {}}
    changes = {record_path: record}
    manifest_path = instance.path('media') / 'manifest.json'
    snippets = data.get('snippets', [])
    manifest_raw = manifest_path.read_bytes() if subjects and snippets and manifest_path.exists() else None
    manifest = json.loads(manifest_raw) if manifest_raw is not None else {'schema_version': 1, 'assets': []}
    exclusive = [record_path]
    for index, snippet in enumerate(snippets, 1):
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
        media_path = instance.path('media') / name if subjects else instance.path('records') / 'crops' / rid / (str(index) + path.suffix.lower())
        if media_path.exists():
            raise ValueError('Document media already exists: ' + name)
        changes[media_path] = raw
        exclusive.append(media_path)
        if not subjects:
            record.setdefault('crops', []).append({'image': media_path.relative_to(instance.root).as_posix(),
                'caption': snippet['caption'], 'reading': snippet['read'], 'sha256': hashlib.sha256(raw).hexdigest()})
            continue
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
        record['reading'] = '\n\n'.join(s['read'] for s in snippets)
    if not package['facts']:
        for pid in subjects:
            package['facts'][pid] = [{'label': 'document', 'text': record.get('reading') or
                '\n'.join(f'{key}: {value}' for key, value in record['fields'].items()),
                'status': 'export', 'sources': [rid]}]
    if subjects and snippets:
        changes[manifest_path] = manifest
        if manifest_raw is None:
            exclusive.append(manifest_path)
    if subjects:
        changes[target] = package
        exclusive.append(target)
    mutate(instance, changes, exclusive=exclusive,
           expect={manifest_path: manifest_raw} if manifest_raw is not None else None)
    return {'record': str(record_path.relative_to(instance.root)),
            'contribution': str(target.relative_to(instance.root)) if subjects else None, 'subjects': subjects}
