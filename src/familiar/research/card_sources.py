# START_MODULE_CONTRACT: MOD-PERSON-CARD-SOURCES
# PURPOSE: Recover independently located observations from a family's declared research collections.
# PRD_REF: docs/PRD.md#PERSON-CARD
# INVARIANTS:
# - local discovery never fetches a URL or writes a source, and SQLite opens read-only [review: engine lead]
# - whole observations retain JSON pointers, line ranges or database keys and unreadable sources remain visible [review: engine lead]
# - matching retrieves candidates without deciding identity or discarding contrary dates [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#PERSON-CARD (collection configuration)
# :END_MODULE_CONTRACT
import copy
import fnmatch
import json
import re
import sqlite3
import unicodedata
from functools import lru_cache
from pathlib import Path


def fold(text):
    text = unicodedata.normalize('NFKD', str(text).casefold().replace('ł', 'l'))
    return ' '.join(re.findall(r'[^\W_]+', ''.join(c for c in text if not unicodedata.combining(c))))


@lru_cache(maxsize=1024)
def _words(term):
    return frozenset(fold(term).split())


def matches(value, terms):
    text = ' ' + fold(json.dumps(value, ensure_ascii=False)) + ' '
    words = set(text.split())
    return [term for term in terms if _words(term) and _words(term) <= words]


def locator(instance, path):
    path = path.resolve()
    if path.is_relative_to(instance.root):
        return path.relative_to(instance.root).as_posix()
    for key, base in instance.host_paths.items():
        if path.is_relative_to(Path(base).resolve()):
            return f'host:{key}/' + path.relative_to(Path(base).resolve()).as_posix()
    raise ValueError('source outside declared family and host roots')


def location(instance, source):
    """A collection uses either a family path or a confined declared path key."""
    base = instance.path(source['path_key']) if source.get('path_key') else instance.root
    path = (base / source.get('path', '')).resolve()
    if not path.is_relative_to(base):
        raise ValueError('person-card collection leaves its declared root')
    return path


def observations(value, pointer='$'):
    """Split containers, never the fields of an observation or a version argument."""
    if isinstance(value, list):
        if value and all(not isinstance(row, (list, dict)) for row in value):
            yield pointer, value
            return
        for index, row in enumerate(value):
            yield from observations(row, f'{pointer}/{index}')
    elif isinstance(value, dict):
        # An evidence/graph map is a container; a record, frame or version is atomic.
        if not any(k in value for k in ('id', 'source', 'person', 'reading', 'acts', 'versions', 'fields', 'year', 'act', 'name', 'surname', 'father', 'mother', 'text', 'literal', 'status', 'state', 'coverage', 'error', 'note', 'summary', 'title', 'description', 'fate')) and any(isinstance(v, (list, dict)) for v in value.values()):
            for key, row in value.items():
                if isinstance(row, (list, dict)):
                    escaped = str(key).replace('~', '~0').replace('/', '~1')
                    yield from observations(row, f'{pointer}/{escaped}')
        else:
            yield pointer, value
    elif value is not None:
        yield pointer, value


def _at(value, pointer):
    for part in pointer.strip('/').split('/'):
        if part:
            part = part.replace('~1', '/').replace('~0', '~')
            value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def _remove(value, pointer):
    head, _, tail = pointer.rpartition('/')
    parent = _at(value, head)
    key = tail.replace('~1', '/').replace('~0', '~')
    if isinstance(parent, list):
        del parent[int(key)]
    else:
        del parent[key]


def _json_rows(value, prefix, source):
    for ref, row in observations(value, prefix):
        arrays, children, data = [], [], row
        if isinstance(row, dict):
            for pointer, payload in source.get('record_arrays', {}).items():
                try:
                    entries = _at(row, pointer)
                except (KeyError, IndexError):
                    continue
                if not isinstance(entries, list):
                    raise TypeError('record_arrays pointers must select arrays')
                if data is row:
                    data = copy.deepcopy(row)
                _remove(data, pointer)
                arrays.append({'pointer': pointer, 'payload': payload, 'items': len(entries)})
                for index, entry in enumerate(entries):
                    child = _at(entry, payload)
                    context = copy.deepcopy(entry) if payload else {}
                    if payload:
                        _remove(context, payload)
                    for child_ref, record, metadata in _json_rows(child, ref + pointer + '/' + str(index) + payload, source):
                        children.append((child_ref, record, {**metadata, 'container_context': [context, *metadata.get('container_context', [])], '_parent_data': row}))
        yield ref, data, {'expanded_arrays': arrays} if arrays else {}
        yield from children


def _text_rows(text, terms, include=False, heading_context=True):
    lines = text.splitlines(keepends=True)
    # Paragraphs preserve the heading's local context without copying a whole report.
    blocks, start, headings = [], 0, {}
    for i in range(len(lines) + 1):
        if i < len(lines) and (head := re.match(r'^(#{1,6})\s+(.*)', lines[i])):
            level = len(head[1])
            headings = {k: v for k, v in headings.items() if k < level}
            headings[level] = head[2]
        if i == len(lines) or not lines[i].strip():
            if i > start:
                block = ''.join(lines[start:i])
                heading = ' / '.join(headings.values())
                # Tables are independent rows, not one enormous paragraph.
                if block.lstrip().startswith('|'):
                    blocks.extend((j + 1, j + 1, heading, lines[j]) for j in range(start, i))
                else:
                    blocks.append((start + 1, i, heading, block))
            start = i + 1
    for first, last, heading, block in blocks:
        if include or matches(block, terms) or (heading_context and matches(heading, terms)):
            yield f'L{first}-L{last}', {'heading': heading, 'literal': block}


def _rows(path, source, terms):
    fmt = source.get('format', path.suffix.lstrip('.'))
    if fmt in {'sqlite', 'sqlite3'}:
        query = source.get('query')
        if not isinstance(query, str) or not query.lstrip().lower().startswith('select '):
            raise ValueError('SQLite collection needs a SELECT query')
        wal = path.with_name(path.name + '-wal')
        if wal.exists() and wal.stat().st_size:
            raise ValueError('SQLite WAL is present; use a checkpointed read-only snapshot')
        with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
            db.execute('PRAGMA query_only=ON')
            db.row_factory = sqlite3.Row
            for index, row in enumerate(db.execute(query)):
                data = dict(row)
                key = data.get(source.get('key', 'id'), index)
                for field in source.get('decode', []):
                    if isinstance(data.get(field), str):
                        data[field] = json.loads(data[field])
                yield f'row:{index};key:{key}', data, {}
    elif fmt in {'json', 'jsonl'}:
        text = path.read_text(encoding='utf-8-sig')
        values = [(f'L{i}', json.loads(line)) for i, line in enumerate(text.splitlines(), 1) if line.strip()] if fmt == 'jsonl' else [('$', json.loads(text))]
        for prefix, data in values:
            for part in source.get('pointer', '').strip('/').split('/'):
                if part:
                    part = part.replace('~1', '/').replace('~0', '~')
                    data = data[int(part)] if isinstance(data, list) else data[part]
            yield from _json_rows(data, prefix + source.get('pointer', ''), source)
    else:
        for ref, data in _text_rows(path.read_text(encoding='utf-8-sig'), terms, source.get('include', False), source.get('heading_context', source.get('kind') != 'context')):
            yield ref, data, {}


def collect(instance, sources, terms):
    rows, coverage = [], []
    seen = set()
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get('id'), str):
            raise TypeError('each person-card source needs an id and a path or path_key')
        allowed = {'id', 'path', 'path_key', 'glob', 'exclude', 'format', 'query', 'key', 'decode', 'pointer', 'kind', 'terms', 'include', 'people', 'historical', 'heading_context', 'reference_roots', 'context_fields', 'record_arrays'}
        if source.keys() - allowed:
            raise ValueError('unknown person-card source keys: ' + ', '.join(sorted(source.keys() - allowed)))
        for key in ('decode', 'exclude', 'terms', 'people', 'reference_roots', 'context_fields'):
            if key in source and (not isinstance(source[key], list) or not all(isinstance(v, str) and v.strip() for v in source[key])):
                raise TypeError(f'person-card source {key} must be an array of text')
        for key in ('historical', 'include', 'heading_context'):
            if key in source and type(source[key]) is not bool:
                raise TypeError(f'person-card source {key} must be boolean')
        if not isinstance(source.get('record_arrays', {}), dict) or not all(isinstance(k, str) and k.startswith('/') and isinstance(v, str) and (not v or v.startswith('/')) for k, v in source.get('record_arrays', {}).items()):
            raise TypeError('record_arrays must map array JSON pointers to payload JSON pointers')
        if not source.get('path') and not source.get('path_key'):
            raise ValueError('person-card source needs path or path_key; whole-root scans are not implicit')
        base = location(instance, source)
        note = {'id': source['id'], 'path': locator(instance, base), 'files': 0, 'observations': 0, 'matched': 0, 'errors': []}
        coverage.append(note)
        if source.get('people') and not {fold(p) for p in source['people']} & {fold(term) for term in terms}:
            note['selection'] = 'outside declared person scope; not read'
            continue
        files = [base] if base.is_file() else sorted(base.glob(source.get('glob', '**/*')))
        files = [p for p in files if p.is_file() and not any(x.startswith('.') for x in p.relative_to(base if base.is_dir() else base.parent).parts)
                 and not any(fnmatch.fnmatch(p.as_posix(), pattern) for pattern in source.get('exclude', []))]
        if not base.exists():
            note['errors'].append({'reason': 'missing collection'})
        for path in files:
            if not path.resolve().is_relative_to(base if base.is_dir() else base.parent):
                note['errors'].append({'reason': 'linked file escapes collection root; not opened'})
                continue
            if path.suffix.lower() not in {'.json', '.jsonl', '.md', '.txt', '.csv', '.tsv', '.sqlite', '.sqlite3'}:
                continue
            identity = (path.resolve(), source.get('query'), source.get('pointer'))
            if identity in seen:
                continue
            seen.add(identity)
            note['files'] += 1
            before = (path.stat().st_size, path.stat().st_mtime_ns)
            start, matched = len(rows), note['matched']
            try:
                source_terms = [*terms, *source.get('terms', [])]
                for ref, data, metadata in _rows(path, source, source_terms):
                    note['observations'] += 1
                    parent = metadata.pop('_parent_data', {})
                    found = matches(data, source_terms) or matches(parent, source_terms)
                    if found or source.get('include', False):
                        note['matched'] += 1
                        projection = []
                        if source.get('context_fields') is not None:
                            if source.get('kind') != 'context' or not isinstance(data, dict):
                                raise ValueError('context_fields is only for dictionary observations in context collections')
                            keep = source['context_fields']
                            projection = [k for k in data if k not in keep]
                            data = {k: v for k, v in data.items() if k in keep}
                        rows.append({'locators': [locator(instance, path) + '#' + ref],
                                     'collection': source['id'], 'kind': source.get('kind', 'observation'),
                                     'matched_on': found, 'data': data,
                                     **metadata,
                                     'context_fields_at_locator': projection,
                                     '_historical': source.get('historical', False), '_origin': path,
                                     '_reference_roots': source.get('reference_roots', [])})
            except (OSError, UnicodeError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
                note['errors'].append({'locator': locator(instance, path), 'reason': exc.strerror if isinstance(exc, OSError) else str(exc)})
            if not path.exists() or before != (path.stat().st_size, path.stat().st_mtime_ns):
                del rows[start:]
                note['matched'] = matched
                note['errors'].append({'locator': locator(instance, path), 'reason': 'source changed during read; its observations were discarded'})
    return rows, coverage


def copies(instance, value, *, origin=None, reference_roots=()):
    """Inventory declared local copies and remote pointers; do not certify an image."""
    found = []
    suffix = r'\.(?:jsonl?|md|txt|png|jpe?g|webp|pdf|tiff?)(?:#[^\s]*)?$'
    roots = [instance.root]
    if origin:
        roots.append(origin.parent)
    roots.extend(instance._inside(root) for root in reference_roots)
    def reference(raw):
        raw = raw.strip().strip('<>').replace('\\', '/')
        if raw.startswith(('https://', 'http://')):
            found.append({'reference': raw, 'state': 'remote; not fetched'})
            return
        if not re.search(suffix, raw, re.IGNORECASE):
            return
        path = Path(raw.split('#')[0])
        options = [path.resolve()] if path.is_absolute() else [(base / path).resolve() for base in roots]
        if not path.is_absolute():
            try:
                options.insert(0, instance.local(path.as_posix()))  # kept outside git: through the map
            except ValueError:
                pass
        options = [p for p in options if p.is_relative_to(instance.root) or any(p.is_relative_to(Path(base).resolve()) for base in instance.host_paths.values())]
        if not options:
            found.append({'reference': 'undeclared-host:' + path.name, 'state': 'outside declared roots; not opened'})
            return
        path = next((p for p in options if p.is_file()), options[0])
        found.append({'reference': locator(instance, path), 'state': 'local' if path.is_file() else 'missing local copy'})
    def walk(item):
        if isinstance(item, dict):
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
        elif isinstance(item, str):
            for url in re.findall(r'https?://[^\s<>"\)\]\x27]+', item):
                reference(url.rstrip('.,;'))
            for ref in re.findall(r'\[[^\]]*\]\(([^)]+)\)|`([^`\n]+)`', item):
                reference(ref[0] or ref[1])
            if '\n' not in item and len(item) < 1000 and (not re.search(r'\s', item) or re.match(r'^[A-Za-z]:[/\\]', item)):
                reference(item)
    walk(value)
    return list({json.dumps(r, sort_keys=True): r for r in found}.values())
