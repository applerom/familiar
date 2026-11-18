# START_MODULE_CONTRACT: MOD-MEMORY-VISIBILITY
# PURPOSE: Select tellings for display and guard publication against private source reuse.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - display selection excludes search-only tellings and publication refuses their contents [test: tests/gate/test_desk_guarantees.py::test_family_asks_carry_over_and_private_memory]
# CHANGES_WITH:
# - MOD-PUBLICATION
# - MOD-INTAKE-CORE
# :END_MODULE_CONTRACT
import json
import re
from html import unescape

FAMILY = 'family'
SEARCH_ONLY = 'search-only'


def select(instance):
    if hasattr(instance, '_display_memory'):
        return instance._display_memory
    visible, protected, phrases = [], set(), set()
    for path, memory in _tellings(instance.path('memory')):
        if memory.get('visibility', FAMILY) == FAMILY:
            visible.append((path, memory))
            continue
        protected.add(memory['id'])
        if path.is_relative_to(instance.root):
            protected.add(path.relative_to(instance.root).as_posix())
        for row in [memory, *memory.get('items', [])]:
            protected.update(row[k] for k in ('id', 'original') if isinstance(row.get(k), str) and row[k])
            wants = row.get('wants', {})
            for value in [row.get('text'), row.get('display_text'), *(wants.values() if isinstance(wants, dict) else ())]:
                if isinstance(value, str) and len(value.strip()) >= 16:
                    phrases.add(' '.join(unescape(value).split()))
    result = visible, protected, phrases
    if getattr(instance, '_immutable_snapshot', False):
        instance._display_memory = result
    return result


def _tellings(root):
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.suffix not in {'.json', '.jsonl'}:
            continue
        raw = path.read_text(encoding='utf-8-sig')
        if path.suffix == '.jsonl':
            rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        else:
            parsed = json.loads(raw)
            rows = parsed if isinstance(parsed, list) else [parsed]
        yield from ((path, memory) for memory in rows)


def stamp(instance):
    from .writer import _metadata
    return {path: _metadata(path) for path in instance.path('memory').rglob('*')
            if path.suffix in {'.json', '.jsonl'} and path.is_file()}


def require_displayable(instance, value, *, selection=None):
    _, protected, phrases = selection if selection is not None else select(instance)
    if not protected:
        return

    def contains(value):
        if isinstance(value, dict):
            return any(k in protected or contains(v) for k, v in value.items())
        if isinstance(value, (list, tuple)):
            return any(contains(v) for v in value)
        if isinstance(value, str):
            if value in protected or value.replace('\\', '/') in protected:
                return True
            folded = ' '.join(unescape(value).split())
            return any(phrase in folded for phrase in phrases)
        return False

    if contains(value):
        raise ValueError('Display refers to search-only memory. Remove the private source and its wording from the display material.')


def check_delivery(instance, files):
    selection = select(instance)
    if not selection[1]:
        return
    for name, raw in files.items():
        if name.endswith('.json') and name not in {'bundle.json', 'reader-manifest.json'}:
            require_displayable(instance, json.loads(raw), selection=selection)
        elif name.endswith(('.html', '.txt')):
            require_displayable(instance, re.sub(r'<[^>]*>', ' ', raw.decode('utf-8')), selection=selection)
