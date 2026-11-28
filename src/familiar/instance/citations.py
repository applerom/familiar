"""Find and keep family evidence cited through a temporary filesystem path."""
# START_MODULE_CONTRACT: MOD-TEMP-CITATIONS
# PURPOSE: Keep evidence found through temporary paths addressable from records and search journals.
# PRD_REF: docs/PRD.md#INSTANCE
# INVARIANTS:
# - the same locators drive advisory reporting and transfer [review: engine lead]
# - cited bytes stay unchanged, collisions refuse, and missing locators survive [review: engine lead]
# CHANGES_WITH:
# - MOD-INSTANCE-VALIDATION (grouped diagnostic)
# - MOD-FAMILY-WRITER (transaction for copies and locator edits)
# :END_MODULE_CONTRACT
import json
import re
from pathlib import PurePosixPath

from .gate import boundary

# Match relative paths in structured values and prose locators, skipping URLs and archive: locators.
_TEMP = re.compile(r"(?<![\w:/\\])(?:\.[/\\])?(?P<path>(?:tmp|temp|\.tmp)[/\\][^\s<>'\x22;,:()\[\]{}|?*#]+)",
                   re.IGNORECASE)
_JSON_STRING = re.compile(rb'"(?:[^"\\]|\\.)*"')
_JSON_KEY_END = re.compile(rb'\s*:')
_ARCHIVE = re.compile(r'(?<![\w/\\])archive:[^;|\r\n]*', re.IGNORECASE)


def _matches(value):
    # Quoted path fields can contain spaces. Paths embedded in prose use path tokens.
    exact = re.fullmatch(r'(?:\.[/\\])?(?P<path>(?:tmp|temp|\.tmp)[/\\][^<>:;"(),|?*#\r\n]+?\.[\w-]+)',
                         value, re.IGNORECASE)
    archives = [m.span() for m in _ARCHIVE.finditer(value)]
    for match in (exact,) if exact else _TEMP.finditer(value):
        if any(start <= match.start() < end for start, end in archives):
            continue
        path = match['path'].rstrip('.').replace('\\', '/')
        parts = PurePosixPath(path).parts
        if len(parts) > 1 and '..' not in parts:
            yield match, path


def _citations(instance):
    for key in ('records', 'searches'):
        base = instance.path(key)
        paths = sorted(base.rglob('*')) if base.is_dir() else [base]
        for path in paths:
            if path.suffix not in {'.json', '.jsonl'} or not path.is_file():
                continue
            if any(part.startswith('.') for part in path.relative_to(base.parent).parts):
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                continue  # Ordinary validation already owns read failures.
            lower = raw.lower()
            if not any(prefix in lower for prefix in (b'tmp/', b'tmp\\', b'temp/', b'temp\\')):
                continue
            try:
                if path.suffix == '.jsonl':
                    for line in raw.decode('utf-8-sig').splitlines():
                        if line.strip():
                            json.loads(line)
                else:
                    json.loads(raw)
            except ValueError:
                continue  # Ordinary validation already owns syntax findings.
            yield path, raw


def _rewrite(raw, replace):
    def string(token):
        original = token[0]
        if (not re.search(rb'(?:tmp|temp)[/\\]', original, flags=re.I)
                or _JSON_KEY_END.match(raw, token.end())):
            return original
        text = json.loads(original)
        result = text
        matches = list(_matches(text))
        for match, path in reversed(matches):
            target = replace(path)
            if target:
                end = match.start('path') + len(match['path'].rstrip('.'))
                result = result[:match.start()] + target + result[end:]
        return original if result == text else json.dumps(result, ensure_ascii=False).encode('utf-8')

    return _JSON_STRING.sub(string, raw)


def temporary_references(instance):
    """Unique temporary targets with an example citation, including missing targets."""
    refs = {}
    for file, raw in _citations(instance):
        def record(path):
            refs.setdefault(path, file)
        _rewrite(raw, record)
    return {name: path for name, path in refs.items()
            if PurePosixPath(name).suffix or (instance.root / name).is_file()}


@boundary('transaction')
def preserve(instance, *, apply):
    """Copy cited bytes to captures, then change their locators in the same writer transaction."""
    from .writer import mutate

    changes, expected, assets, missing, kept = {}, {}, {}, set(), {}
    home = instance.path('captures').resolve()
    if not home.is_relative_to(instance.root):
        raise ValueError('keep-citations requires a captures directory inside the instance')
    temp_files = {}

    def rewrite(name):
        if name in kept:
            return kept[name]
        if name in missing:
            return None
        source = instance.root / name
        if not source.is_file():
            if PurePosixPath(name).suffix:
                missing.add(name)
            return None
        directory, tail = name.split('/', 1)
        source = instance._inside(name)
        if not source.is_relative_to(instance.root / directory):
            raise ValueError(f'temporary citation escapes its directory: {name}')
        target = (home / 'evidence' / tail).resolve()
        if not target.is_relative_to(home):
            raise ValueError(f'evidence destination escapes captures: {name}')
        data = source.read_bytes()
        temp_files[source] = data
        existing = assets.get(target)
        if existing is None and target.is_file():
            existing = target.read_bytes()
            expected[target] = existing
        if existing is not None and existing != data:
            raise ValueError(f'evidence destination has different bytes: {target}')
        if target not in expected:
            assets[target] = data
        kept[name] = target.relative_to(instance.root).as_posix()
        return kept[name]

    for path, raw in _citations(instance):
        updated = _rewrite(raw, rewrite)
        if updated != raw:
            expected[path] = raw
            changes[path] = updated
    if apply and changes:
        def verify_sources():
            if any(path.read_bytes() != data for path, data in temp_files.items()):
                raise ValueError('cited file changed during transfer')
        mutate(instance, assets | changes, exclusive=assets, expect=expected, verify_inputs=verify_sources)
    return kept, sorted(missing), sorted(path.relative_to(instance.root).as_posix() for path in changes)
