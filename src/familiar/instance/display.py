# START_MODULE_CONTRACT: MOD-DISPLAY-INPUTS
# PURPOSE: Select adopted research and archive dependencies without copying unrelated collector work.
# PRD_REF: docs/PRD.md#INSTANCE
# INVARIANTS:
# - display references select corpus records recursively by exact normalized filename stem [review: engine lead]
# - original, capture, import and media files enter a display snapshot only through declared references or its media manifest [review: engine lead]
# - a path reference that the reader only tests for existence is a presence dependency: its name, size and time bind the snapshot, never its bytes [review: engine lead]
# - selected captures that supply reader scan pixels bind content as well as presence [review: engine lead]
# - absolute originals resolve only within the family or its host-mapped originals root [test: tests/journeys/test_installed_engine.py::test_installed_engine]
# - build-local reference indexes reuse unchanged JSON; each check resolves distinct local paths anew [review: engine lead]
# - only explicitly adopted research records and search files enter output snapshots and watches [review: engine lead]
# - correspondence reply originals bind literal bytes, not existence placeholders [review: engine lead]
# - the gallery binds both archive pixels and any display derivative [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-WRITER
# - MOD-READER-ASSETS
# :END_MODULE_CONTRACT
import json
import os
import re
import stat
from functools import cache
from familiar.reader.scans import candidates, capture_path

from .subjects import normalized

EXCLUDED = {'records', 'searches', 'originals', 'captures', 'imports', 'media', 'media_archive',
            'cases', 'versions', 'asks', 'questions', 'answers', 'correspondence', 'research_permission', 'variant_overrides',
            'working_version', 'card_reviews', 'associations'}


def _within(path, root):
    """Component boundary on already absolute paths, without walking Path.parents."""
    path, root = os.path.normcase(str(path)), os.path.normcase(str(root))
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def _references(path, record, derived, *, literal_originals=False):
    refs, assets, local = set(), set(), set()

    def walk(value, key='', owner=False):
        if isinstance(value, dict):
            if key == 'sources':
                refs.update(normalized(k) for k in value)
            mine = owner or any(isinstance(v, str) and v in derived
                                for v in (value.get('id'), value.get('sid'), key))
            for k, child in value.items():
                walk(child, k, mine and k == 'local')
        elif isinstance(value, list):
            for child in value:
                walk(child, key)
        elif isinstance(value, str):
            if key in {'record', 'records', 'sources', 'provenance', 'intake', 'basis', 'saved'}:
                refs.add(normalized(value))
            if not record and key in {'local', 'saved_result', 'original', 'image', 'scan'} and value and not re.match(r'(?:[a-z]+:)?//|[a-z]+://', value, re.IGNORECASE):
                local.add((value, owner or literal_originals and key == 'original'))
            if key in {'asset', 'full', 'orig', 'originalAsset', 'cover'} and value.startswith('/') and not value.startswith('//'):
                assets.add(value[1:])
            assets.update(re.findall(r'(?:src=["\']|\]\()/([^"\'\s)<>]+)', value))

    values = []
    try:
        text = path.read_text(encoding='utf-8-sig')
        for line in text.splitlines() if path.suffix == '.jsonl' else [text]:
            try:
                values.append(json.loads(line))
            except ValueError:
                pass  # Copied forms own their complete diagnostics, including partial lines.
    except OSError:
        pass
    for value in values:
        walk(value)
    value = values[0] if values else None
    if (record and isinstance(value, dict) and value.get('kind') == 'index-entry'
            and isinstance(value.get('saved_result'), str) and value['saved_result'].strip()):
        local.add((value['saved_result'], False))
    captures = candidates(value) if record and isinstance(value, dict) else ()
    return refs, assets, local, captures


def reference_paths(instance):
    """Authored state can adopt research by exact reference, regardless of directory."""
    roots = [instance.path(k) for k in ('tree_snapshot', 'tree_metadata', 'feed_graph',
        'evidence', 'contributions', 'feeds', 'edition', 'gallery', 'world_map', 'memory',
        'identity_decisions', 'privacy', 'versions', 'cases')]
    if not getattr(instance, '_display_scope', False):
        roots.append(instance.path('correspondence'))
    return {p for root in roots for p in ([root] if root.is_file() else root.rglob('*'))
            if p.is_file() and p.suffix in {'.json', '.jsonl'}}


def research_inputs(instance):
    """The same adoption closure used by validation, life assessment and snapshots."""
    if getattr(instance, '_immutable_snapshot', False) and hasattr(instance, '_research_inputs'):
        return instance._research_inputs
    files, _, _ = dependencies(instance, research_only=True)
    if getattr(instance, '_immutable_snapshot', False):
        instance._research_inputs = files
    return files


def dependencies(instance, *, public=False, research_only=False):
    """Return (content files, record refs, presence files) for snapshot selection.

    The reader binds the bytes of selected record captures, registered media and
    originals that a registered derivative uses. Other reference checks bind presence.
    """
    refs, files, assets, presence = set(), set(), set(), set()
    record_root, search_root = instance.path('records'), instance.path('searches')
    manifest = instance.path('media') / 'manifest.json'
    rows = []
    if not research_only and manifest.is_file():
        try:
            value = json.loads(manifest.read_text(encoding='utf-8-sig'))
            rows = value.get('assets', []) if isinstance(value, dict) else []
        except ValueError:
            pass  # The manifest itself is fingerprinted; its consumer owns diagnostics.
    rows = [row for row in rows if isinstance(row, dict)
            and isinstance(row.get('file'), str)] if isinstance(rows, list) else []
    derived = {row['source_id'] for row in rows if isinstance(row.get('source_id'), str)}

    originals = None if research_only else instance.path('originals')

    @cache
    def directory(path):
        return path.resolve()

    def resolve(path):
        # Recheck final reparse points; shared parent directories resolve once
        # per dependency check, never across checks that might observe a retarget.
        try:
            info = path.lstat()
        except OSError:
            return path.resolve()
        if (path.name == '..' or stat.S_ISLNK(info.st_mode) or
                getattr(info, 'st_file_attributes', 0) &
                getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)):
            return path.resolve()
        return directory(path.parent) / path.name

    @cache
    def local(value, needed=True):
        target = files if needed else presence
        if value.startswith('archive:'):
            root, relative = originals, value[8:]
            path = resolve(root / relative)
            if not _within(path, root):
                raise ValueError('display archive reference escapes originals')
            target.add(path)
        else:
            path = resolve(instance.root / value)
            if 'originals' in instance.host_paths and _within(path, originals):
                target.add(path)
            else:
                if not _within(path, instance.root):
                    raise ValueError('path leaves family root: ' + value)
                target.add(path)

    context = tuple(sorted(derived))
    def read(path, *, record=False):
        from .writer import input_projection
        literal_originals = path.is_relative_to(instance.path('correspondence'))
        found, media, links, captures = input_projection(path, (record, context, literal_originals),
            lambda: _references(path, record, derived, literal_originals=literal_originals))
        refs.update(found)
        assets.update(media)
        if not research_only:
            for value, needed in links:
                local(value, needed or public and record)
            for reference in captures:
                capture = capture_path(instance, reference, resolve=resolve)
                if capture is not None:
                    files.add(capture)
                    if capture.is_file():
                        break

    for path in reference_paths(instance):
        read(path)
    records, candidates = set(), list(record_root.rglob('*.json'))
    searches = []
    for path in search_root.rglob('*'):
        if path.is_file() and path.suffix in {'.json', '.jsonl'}:
            # Malformed/unreferenced working rows never become dependencies.
            try:
                text = path.read_text(encoding='utf-8-sig')
                ids = set()
                for line in text.splitlines() if path.suffix == '.jsonl' else [text]:
                    try:
                        row = json.loads(line)
                        if isinstance(row, dict) and isinstance(row.get('id'), str):
                            ids.add('search:' + normalized(row['id']))
                    except ValueError:
                        pass
                searches.append((path, ids))
            except OSError:
                pass
    while added := ({p for p in candidates if normalized(p.stem) in refs} |
                    {p for p, ids in searches if ids & refs}) - records:
        records.update(added)
        for path in added:
            read(path, record=_within(path, record_root))
    files.update(records)
    if research_only:
        return files, refs, set()
    for path in instance.path('imports').glob('*.json'):
        if normalized(path.stem) in refs:
            files.add(path)
    files.add(manifest)  # Absence is also a dependency, including legacy media.
    from .gallery import files as photo_files, photographs
    try:
        for asset, photo in photographs(instance).items():
            files.update(photo_files(instance, asset, photo))
    except (ValueError, OSError, TypeError):
        pass  # The staged gallery check names invalid rows.
    if manifest.is_file():
        for row in rows:
            path = resolve(manifest.parent / row['file'])
            if not _within(path, manifest.parent):
                raise ValueError('display media path escapes its root')
            files.add(path)
    else:
        for asset in assets:
            for key in instance.config.get('media_roots', ['media', 'media_archive']):
                root = instance.path(key)
                path = (root / asset).resolve()
                if not path.is_relative_to(root):
                    raise ValueError('display asset escapes its root')
                files.add(path)
    return files, refs, presence - files
