# START_MODULE_CONTRACT: MOD-FAMILY-WRITER
# PURPOSE: Own engine filesystem mutation, staged item validation and checked atomic generations.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - engine modules cannot write around this component [review: engine lead]
# - upload staging excludes owner correspondence for shared login; loopback feedback origin is explicit [review: engine lead]
# - unadopted collector records and journals never enter output snapshots; selected-input race rejection remains complete [review: engine lead]
# - changed inputs cannot commit a clean generation [review: engine lead]
# - a pinned reader snapshot is invalidated by input additions, removals or metadata changes [review: engine lead]
# - absent or invalid-name dependencies stay absent in snapshots and watches until a real input appears [test: tests/journeys/test_installed_engine.py::test_installed_engine]
# - private diagnostics cannot alias declared family inputs [review: engine lead]
# - release provenance is stored only under the instance's work directory [review: engine lead]
# - competing publishers refuse clearly and can retry without corrupting generations [review: engine lead]
# - desk cloud locks are kernel-owned; transition intent is atomic non-data bookkeeping under .state [review: engine lead]
# - generated output is withdrawn on a living correction despite ordinary consent [review: engine lead]
# - desk cache integrity and metadata-bound media reuse are checked here; a cache never supplies public publication authority [test: tests/journeys/test_installed_engine.py::test_installed_engine]
# - build-local input projections bind file identity and metadata; referenced paths are resolved again by each dependency check [review: engine lead]
# - a search journal carry-over changes only paths.searches and keeps the race and input checks while old row flaws do not stop it [review: engine lead]
# - standalone demo desks require a fictional family and an empty output, retaining the checked reader and host decision [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE
# - MOD-OUTPUT-REVIEW
# - MOD-READER-BOOK (flat print artifacts consume a sealed reader directly)
# - docs/gate.md
# :END_MODULE_CONTRACT
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

from familiar.instance.research_forms import PREVIEW

from .gate import boundary
from .model import DEFAULTS, Instance

_REAPED = set()
_SNAPSHOT_LEASE = 'familiar-snapshot-v1'
_BUILD_CACHE = ContextVar('familiar_build_cache', default=None)
_SELECTED_ROOTS = {'captures', 'originals', 'imports', 'media', 'media_archive', 'records', 'searches'}


def _metadata(path, info=None):
    info = path.stat() if info is None else info
    return [info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino]


@dataclass(frozen=True)
class StoredFile:
    """Writer-verified immutable cache payload; consumers never open its body."""
    path: Path
    digest: str
    metadata: list


def content_digest(value):
    if isinstance(value, StoredFile):
        if _metadata(value.path) != value.metadata:
            raise ValueError('cached payload changed during build')
        return value.digest
    return hashlib.sha256(value).hexdigest()


def semantic_digest(value):
    return content_digest(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), default=str).encode())


class _BuildCache:
    """Disposable, per-instance memoization. Never a public publication authority."""

    def __init__(self, instance):
        self.root = instance.path('state') / 'build-cache'
        self.root.mkdir(parents=True, exist_ok=True)
        self.index = self.root / 'index.json'
        try:
            self.hashes = json.loads(self.index.read_bytes())
        except (OSError, ValueError):
            self.hashes = {}
        self.metrics = {}
        self.code = {}
        self.projections = {}

    def digest(self, path, info=None):
        info = path.stat() if info is None else info
        metadata = _metadata(path, info)
        # Hard-linked immutable media in a new snapshot have the same identity.
        key = f'{info.st_dev}:{metadata[3]}' if metadata[3] else str(path)
        old = self.hashes.get(key, {})
        if old.get('metadata') != metadata:
            old = {'metadata': metadata, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            if _metadata(path) != metadata:
                raise ValueError('file changed while hashing: ' + key)
            self.hashes[key] = old
        return old['sha256']

    def contract(self):
        if not self.code:
            from familiar.rules.roles import method_root
            package = Path(__file__).resolve().parents[1]
            # UI, CLI and the release number are provenance, not data dependencies.
            self.code = {p.relative_to(package).as_posix(): self.digest(p)
                         for folder in ('instance', 'tree', 'reader', 'feeds', 'checks', 'rules')
                         for p in sorted((package / folder).glob('*.py'))
                         if p.name not in {'cli.py', 'server.py', 'host_text.py'}}
            self.code.update({'method/' + p.relative_to(method_root()).as_posix(): self.digest(p)
                              for p in sorted(method_root().rglob('*')) if p.is_file()})
        if not hasattr(self, '_contract'):
            self._contract = semantic_digest(self.code)
        return self._contract

    def read(self, path):
        # Changed cache metadata triggers a byte check, never blind reuse.
        digest = self.digest(path)
        return StoredFile(path, digest, _metadata(path))

    def object(self, namespace, identity, dependencies, produce):
        key = semantic_digest([self.contract(), dependencies])
        slot = content_digest(encode([namespace, identity]))
        path = self.root / 'objects' / (slot + '.json')
        try:
            row = json.loads(path.read_bytes())
            if row['key'] == key and content_digest(encode(row['value'])) == row['sha256']:
                self.metrics[namespace + '_reused'] = self.metrics.get(namespace + '_reused', 0) + 1
                return row['value']
        except (OSError, ValueError, KeyError, TypeError):
            pass
        value = produce()
        self.metrics[namespace + '_rebuilt'] = self.metrics.get(namespace + '_rebuilt', 0) + 1
        _put(path, encode({'key': key, 'sha256': content_digest(encode(value)), 'value': value}))
        return json.loads(encode(value))

    def finish(self):
        _put(self.index, encode(self.hashes))
        _put(self.root / 'metrics.json', encode(self.metrics))


def cached(namespace, identity, dependencies, produce):
    """Pure projections only. The calling gate still validates/seals their result."""
    cache = _BUILD_CACHE.get()
    return produce() if cache is None else cache.object(namespace, identity, dependencies, produce)


def input_digest(path, info=None):
    cache = _BUILD_CACHE.get()
    return cache.digest(path, info) if cache else hashlib.sha256(path.read_bytes()).hexdigest()


def input_projection(path, context, produce):
    """Read-only derived references, reused only within this writer's build."""
    cache = _BUILD_CACHE.get()
    if cache is None:
        return produce()
    metadata = _metadata(path)
    key = (str(path), context)
    old = cache.projections.get(key)
    if old is None or old[0] != metadata:
        value = produce()
        if _metadata(path) != metadata:
            raise ValueError('input changed while reading references: ' + str(path))
        cache.projections[key] = (metadata, value)
    return cache.projections[key][1]


def reader_media(source, row, name):
    """Reuse checked media only inside a desk build; full export still reads bytes."""
    from familiar.reader.assets import publication_bytes
    cache = _BUILD_CACHE.get()
    if input_digest(source) != row['sha256']:
        raise ValueError('media changed during export: ' + name)
    if cache is None or name.endswith(('.html', '.svg')):
        content = source.read_bytes()
        publication_bytes(content, name)
        return content
    target = cache.root / 'media' / row['sha256']
    validation = 'media-contract:' + row['sha256']
    if (not target.is_file() or cache.digest(target) != row['sha256']
            or cache.hashes.get(validation) != cache.contract()):
        content = source.read_bytes()
        if content_digest(content) != row['sha256']:
            raise ValueError('media changed during read: ' + name)
        publication_bytes(content, name)
        # Replacing a cache entry must not edit hard-linked committed outputs.
        target.unlink(missing_ok=True)
        _put(target, content)
        key = f'{target.stat().st_dev}:{target.stat().st_ino}'
        cache.hashes[key] = {'metadata': _metadata(target), 'sha256': row['sha256']}
        cache.hashes[validation] = cache.contract()
        cache.metrics['media_rebuilt'] = cache.metrics.get('media_rebuilt', 0) + 1
    else:
        cache.metrics['media_reused'] = cache.metrics.get('media_reused', 0) + 1
    return cache.read(target)


def _process_alive(pid):
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() != 87  # Access denied/unknown is retained.
        try:
            code = wintypes.DWORD()
            return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


@boundary('writer')
def reap_snapshots(instance):
    """Only new, leased per-family snapshots; legacy system-temp directories are untouched."""
    root = (instance.path('state') / 'snapshots').resolve()
    if root in _REAPED:
        return
    _REAPED.add(root)
    removed = failed = 0
    for path in root.glob('familiar-gate-*'):
        if path.is_symlink() or not path.is_dir() or path.resolve().parent != root:
            continue
        try:
            lease = json.loads((path / 'owner.json').read_text(encoding='utf-8'))
            if (lease.get('format') != _SNAPSHOT_LEASE or type(lease.get('pid')) is not int
                    or not 0 < lease['pid'] <= 0xFFFFFFFF or type(lease.get('created')) not in (int, float)
                    or not 0 < lease['created'] < time.time() - 86400 or _process_alive(lease['pid'])):
                continue
        except (ValueError, OSError, TypeError):
            continue  # Unmarked, malformed and ambiguous directories are never ours to delete.
        try:
            shutil.rmtree(path)
            removed += 1
        except OSError:
            failed += 1
    if removed or failed:
        print(f'Familiar snapshots: removed {removed} expired directories; retained {failed} unavailable.', file=sys.stderr)


def _stage_input(source, target, digest, bulk_roots):
    """Copy mutable forms; link immutable archives, falling back to a verified copy."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if digest.startswith(PRESENT):
        # Existence is the whole dependency; its bytes never enter the snapshot.
        target.write_bytes(b'')
        return
    if (source.suffix.lower() not in {'.json', '.jsonl', '.toml', '.md'} and not source.is_symlink()
            and source.stat().st_mode & stat.S_IWRITE
            and any(source.is_relative_to(root) for root in bulk_roots)):
        try:
            os.link(source, target)
            return
        except OSError:
            pass
    content = source.read_bytes()
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValueError('family inputs changed while copying snapshot: ' + str(source))
    _put(target, content)
    shutil.copystat(source, target)  # Contribution ordering uses preserved source modification times.


def encode(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')


def fresh(instance):
    active = Instance(instance.root, host_paths={str(instance.root): instance.host_paths},
                      host_packs=instance._host_packs, legacy_rules=instance._legacy_rules)
    active._display_scope = getattr(instance, '_display_scope', False)
    active._research_work_scope = getattr(instance, '_research_work_scope', False)
    return active


def display_instance(instance):
    """Private display dependency policy; never used by public publication."""
    active = fresh(instance)
    active._display_scope = True
    return active


def _input_paths(instance):
    """Names, including absent and explicitly linked inputs, are dependencies."""
    return _inputs(instance)[0]


def _inputs(instance):
    """(all paths, presence-only paths, record refs); see display.dependencies."""
    from familiar.rules.roles import method_root
    instance = fresh(instance)
    paths = {instance.root / 'familiar.toml', instance.root / 'exceptions.toml'}
    for key in DEFAULTS:
        if key in {'build', 'state', 'export'} | _SELECTED_ROOTS:
            continue
        if instance._display_scope:
            from .display import EXCLUDED
            if key in EXCLUDED:
                continue
        base = instance.path(key)
        paths.update([base] if not base.is_dir() else (p for p in base.rglob('*') if p.is_file()))
    if instance._research_work_scope:
        # Own-item transactions may adopt another working record in this edit.
        # Output adapters never request this scope.
        paths.update(p for key in ('records', 'searches')
                     for p in instance.path(key).rglob('*') if p.is_file())
    paths.update(p for p in method_root().rglob('*') if p.is_file())
    for pack in [*instance.packs, *instance.language_pack_data.values()]:
        paths.update(p for p in pack['path'].parent.rglob('*') if p.is_file())
    def settings(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {'privacy.closed_topics_file', 'privacy.present_day_politics_file', 'lang.lexicon'} and isinstance(child, str) and child:
                    paths.add(instance._inside(child))
                else:
                    settings(child)
        elif isinstance(value, list):
            for child in value:
                settings(child)
    settings(instance.config)
    for pack in [*instance.packs, *instance.language_pack_data.values()]:
        settings(pack['data'])
    if instance._display_scope:
        from .display import dependencies
        files, refs, presence = dependencies(instance)
        paths.update(files)
        presence -= paths
        return paths | presence, presence, refs
    from .display import dependencies
    paths.update(instance.path('imports').rglob('*.json'))
    files, refs, presence = dependencies(instance, public=True)
    paths.update(files)
    presence -= paths
    return paths | presence, presence, refs


PRESENT = 'present:'


def fingerprints(instance):
    """Reload config and packs; names and bytes, including absence, are dependencies.

    A presence dependency of a private display binds name, size and time only:
    the reader tests that a research original exists and never reads it.
    """
    paths, presence, _ = _inputs(instance)
    def digest(p):
        try:
            info = p.stat()
        except OSError:
            if p.is_file():
                raise
            return None  # Preserve Path.is_file's invalid/missing-name policy.
        if not stat.S_ISREG(info.st_mode):
            return None
        if p in presence:
            return f'{PRESENT}{info.st_size}:{info.st_mtime_ns}'
        return input_digest(p, info)
    return {str(p): digest(p) for p in sorted(paths)}


class InputWatch:
    """Cheap invalidation, not byte verification. Recreate only after a checked read."""

    def __init__(self, instance):
        from familiar.rules.roles import method_root
        instance = fresh(instance)
        self.paths, _, refs = _inputs(instance)
        self.record_root = instance.path('records')
        self.import_root = None if instance._display_scope else instance.path('imports')
        from .display import EXCLUDED
        self.record_refs = refs
        excluded = ({'build', 'state', 'export'} | _SELECTED_ROOTS
                    | (EXCLUDED if instance._display_scope else set()))
        self.roots = [instance.path(key) for key in DEFAULTS if key not in excluded]
        self.roots += [method_root(), *(pack['path'].parent for pack in
                                      [*instance.packs, *instance.language_pack_data.values()])]

    def stamp(self):
        result = {}

        def visit(path, info=None, descend=True):
            name = str(path)
            if name in result:
                return
            try:
                info = info or path.stat()
            except OSError:
                if path.exists():
                    raise
                # Match Path.is_file() in fingerprints: Windows placeholders
                # such as <snapshot>/scan.jpg are absent, not a startup crash.
                # Permission and other unexpected errors still propagate from exists().
                result[name] = None
                return
            result[name] = (info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino)
            if stat.S_ISDIR(info.st_mode) and descend:
                with os.scandir(path) as entries:
                    for entry in entries:
                        visit(Path(entry.path), entry.stat(), not entry.is_symlink())

        for path in [*self.roots, *self.paths]:
            visit(path)
        if self.record_root:
            from .subjects import normalized
            for path in self.record_root.rglob('*.json'):
                if normalized(path.stem) in self.record_refs:
                    visit(path)  # Detect newly saved references, without reading draft contents.
        if self.import_root:
            for path in self.import_root.rglob('*.json'):
                visit(path)
        return result


def checked_snapshot(instance, out):
    """Pin verified bytes; metadata guards subsequent in-memory consumption."""
    _, manifest = _generation_manifest(instance, out)
    if manifest.get('review', {}).get('state') == 'host-private':
        instance = display_instance(instance)
    watch = InputWatch(instance)
    before = watch.stamp()
    files = read_generation(instance, out)
    if watch.stamp() != before:
        raise ValueError('reader inputs changed during verification; rebuild')
    return files, watch, before


def _put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, StoredFile):
        content_digest(data)
        try:
            os.link(data.path, path)
        except OSError:
            shutil.copyfile(data.path, path)
        content_digest(data)
    else:
        path.write_bytes(data)


def _relative(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('writer path escapes root')
    return path


def _mutation_target(instance, path):
    if any(part in {'.generations', 'CURRENT.json', 'generation.json', '.CURRENT.tmp'} for part in path.relative_to(instance.root).parts):
        raise ValueError('family mutation cannot manufacture a publication generation')
    if path in {instance.root / 'familiar.toml', instance.root / 'exceptions.toml'}:
        return
    if any(path.is_relative_to(instance._inside(base)) for base in ('inputs', 'family/feedback/read')):
        return
    for key, default in DEFAULTS.items():
        if key in {'build', 'export'}:
            continue
        base = instance.path(key)
        if path == base or (not Path(default).suffix and path.is_relative_to(base)):
            return
    # Explicit file-valued settings are authored family data too.
    def values(node):
        if isinstance(node, dict):
            for key, child in node.items():
                if key in {'privacy.closed_topics_file', 'privacy.present_day_politics_file', 'lang.lexicon'} and isinstance(child, str) and child:
                    yield instance._inside(child)
                else:
                    yield from values(child)
        elif isinstance(node, list):
            for child in node:
                yield from values(child)
    if path in set(values(instance.config)):
        return
    raise ValueError('family mutation target is not a declared family input')


def _output_root(instance, out):
    candidate = Path(out)
    if candidate.is_symlink():
        raise ValueError('output cannot be a symlink')
    out = candidate.resolve()
    if out == instance.root or instance.root.is_relative_to(out):
        raise ValueError('output overlaps family root')
    for key in DEFAULTS:
        if key in {'export', 'build'}:
            continue
        source = instance.path(key)
        if key == 'feed_graph' and not source.exists() and source.parent == out:
            continue
        if out == source or out.is_relative_to(source) or source.is_relative_to(out):
            raise ValueError('output overlaps family inputs: ' + key)
    return out


@contextmanager
def snapshot(instance):
    """Private input copy. Its fingerprint is checked before it is used and committed."""
    instance = fresh(instance)
    before = fingerprints(instance)
    reap_snapshots(instance)
    scratch = instance.path('state') / 'snapshots'
    scratch.mkdir(parents=True, exist_ok=True)
    bulk_roots = [instance.path(k) for k in ('originals', 'captures', 'imports', 'media', 'media_archive', 'feeds')]
    size = sum(Path(name).stat().st_size for name, digest in before.items()
               if digest is not None and not digest.startswith(PRESENT))
    if size >= 256 * 1024 * 1024:
        print(f'Familiar snapshot: {size / 1024**2:.1f} MiB declared inputs; archive files use hard links where possible ({scratch}).', file=sys.stderr)
    with tempfile.TemporaryDirectory(prefix='familiar-gate-', dir=scratch) as directory:
        _put(Path(directory) / 'owner.json', encode({'format': _SNAPSHOT_LEASE,
             'pid': os.getpid(), 'created': time.time()}))
        root = Path(directory) / 'family'
        root.mkdir()
        # Only fingerprinted, declared inputs belong to the private family copy.
        # Host mappings remain read-only in place; the final fingerprint rejects races.
        for name in before:
            source = Path(name)
            if source.is_relative_to(instance.root) and before[name] is not None:
                target = root / source.relative_to(instance.root)
                _stage_input(source, target, before[name], bulk_roots)
        state = instance.path('state') / 'attestations.json'
        if state.is_relative_to(instance.root) and state.is_file():
            _put(root / state.relative_to(instance.root), state.read_bytes())
        mapping = dict(instance.host_paths)
        for key in ('records', 'searches'):
            if key not in mapping:
                continue
            # A host-mapped corpus needs the same selected, immutable copy.
            record_root = instance.path(key)
            for name in before:
                source = Path(name)
                if source.is_relative_to(record_root) and before[name] is not None:
                    _stage_input(source, root / ('__selected_' + key) / source.relative_to(record_root), before[name], [])
            mapping[key] = str(root / ('__selected_' + key))
        active = Instance(root, host_paths={str(root): mapping}, host_packs=instance._host_packs,
                          legacy_rules=instance._legacy_rules)
        active._display_scope = instance._display_scope
        active._immutable_snapshot = True
        if before != fingerprints(instance):
            raise ValueError('family inputs changed while taking snapshot')
        if instance._display_scope:
            from .validation import _forms
            selected = {str(p) for key in ('records', 'searches') for p in active.path(key).rglob('*')
                        if p.is_file() and p.suffix in {'.json', '.jsonl'}}
            errors = _forms(active, selected)['errors']
            if errors:
                raise ValueError('; '.join(f"{e['location']}: {e['message']}" for e in errors))
        yield active, before


@boundary('transaction')
def mutate(instance, changes=None, *, exclusive=(), working_journals=False):
    """Validate the changed items before touching a destination file.

    working_journals: a carry-over of search journals, which are working research; the
    files must stay inside paths.searches and existing form flaws of old rows do not stop it.

    A failed in-process commit restores old bytes. Multi-file family edits are
    serialized by the host; a process/OS crash during that edit is not a database transaction.
    """
    if not changes:
        return
    changes = {Path(p).resolve(): encode(v) if not isinstance(v, bytes) else v for p, v in (changes or {}).items()}
    for path in changes:
        if not path.is_relative_to(instance.root):
            raise ValueError('family writer cannot modify host-mapped external inputs')
        _mutation_target(instance, path)
        if working_journals and not path.is_relative_to(instance.path('searches')):
            raise ValueError('working journal carry-over may only change paths.searches')
    if any(Path(p).exists() for p in exclusive):
        raise ValueError('refusing to replace existing family data')
    transaction = fresh(instance)
    transaction._research_work_scope = True
    with snapshot(transaction) as (staged, before):
        for path, value in changes.items():
            target = _relative(staged.root, path.relative_to(instance.root))
            target.unlink(missing_ok=True)  # Detach an archive hard link before a staged edit.
            _put(target, value)
        from .validation import validate_changes
        if not working_journals:
            validate_changes(staged, [staged.root / p.relative_to(instance.root) for p in changes])
        if fingerprints(transaction) != before:
            raise ValueError('family inputs changed before mutation')
        old = {p: p.read_bytes() if p.exists() else None for p in changes}
        try:
            for path, value in changes.items():
                _put(path, value)
        except BaseException:
            for path, value in old.items():
                if value is None:
                    path.unlink(missing_ok=True)
                else:
                    _put(path, value)
            raise


def initialize(root, config):
    """The only bootstrap: validate a config in isolation, then create exclusively."""
    root = Path(root)
    if (root / 'familiar.toml').exists():
        raise FileExistsError('family configuration already exists')
    with tempfile.TemporaryDirectory(prefix='familiar-init-') as directory:
        staged = Path(directory) / 'family'
        if root.exists():
            shutil.copytree(root, staged, ignore=shutil.ignore_patterns('.git', '.build', '.generations', '__pycache__'))
        _put(staged / 'familiar.toml', config.encode('utf-8'))
        from .gate import require
        require(Instance(staged))
    root.mkdir(parents=True, exist_ok=True)
    for name, content in {'.gitattributes': '* -text\n', '.gitignore': '.venv/\nvenv/\n__pycache__/\n.state/\n.build/\nexport/\nreader-bundles/\n.secrets/\n'}.items():
        if not (root / name).exists():
            with (root / name).open('xb') as stream:
                stream.write(content.encode('utf-8'))
    ignore = root / '.gitignore'
    ignored = ignore.read_text(encoding='utf-8')
    if '.secrets/' not in ignored.splitlines():
        with ignore.open('ab') as stream:
            stream.write(('' if ignored.endswith('\n') else '\n').encode() + b'.secrets/\n')
    with (root / 'familiar.toml').open('xb') as stream:
        stream.write(config.encode('utf-8'))


def legacy_exception(registry, text):
    """Rules-only compatibility has no family or publication capability."""
    from familiar.rules.cascade import Registry
    if 'schema_version' in registry.instance.config or 'family' in registry.instance.config:
        raise ValueError('legacy exception writer cannot modify a versioned family')
    path = registry.root / 'exceptions.toml'
    value = (path.read_bytes() if path.exists() else b'') + text.encode('utf-8')
    with tempfile.TemporaryDirectory(prefix='familiar-legacy-rules-') as directory:
        staged = Path(directory) / 'family'
        shutil.copytree(registry.root, staged)
        _put(staged / 'exceptions.toml', value)
        Registry(registry.engine, staged)
    _put(path, value)


def diagnostic(instance, name, value):
    """Private rejection reports cannot certify family state or become publications."""
    path = _relative(instance.path('state'), name)
    if path in {instance.root / 'familiar.toml', instance.root / 'exceptions.toml'} or any(
            part in {'.generations', 'CURRENT.json', 'generation.json', '.CURRENT.tmp'}
            for part in path.relative_to(instance.root).parts):
        raise ValueError('diagnostic cannot write family data or publication files')
    for key, default in DEFAULTS.items():
        if key not in {'state', 'build', 'export'}:
            base = instance.path(key)
            if path == base or (not Path(default).suffix and path.is_relative_to(base)):
                raise ValueError('diagnostic path overlaps family inputs')
    _put(path, encode({**value, 'output': {'state': PREVIEW}}))


@contextmanager
def _publisher(out):
    out.mkdir(parents=True, exist_ok=True)
    lock = out / '.publish.lock'
    try:
        stream = lock.open('xb')
    except FileExistsError as exc:
        raise ValueError('Publication in progress for this output; retry after the other publisher finishes') from exc
    try:
        with stream:
            yield
    finally:
        lock.unlink(missing_ok=True)


def publish(instance, out, publication):
    """One publisher per destination; contention is a retryable, explicit refusal."""
    from .publication import Publication
    if type(publication) is not Publication:
        raise TypeError('writer accepts only a gate Publication')
    if publication.working:
        raise ValueError('private working text cannot be published to readers')
    if publication.host_private:
        raise ValueError('host-private reader is not for publication or clean release')
    publication.check(instance)
    out = _output_root(instance, out)
    if (out / 'working-tree.json').exists():
        raise ValueError('reader publication needs a separate directory from the private working tree')
    with _publisher(out):
        return _publish(instance, out, publication)


def save_private_reader(instance, out, publication):
    """Store a labelled local generation; ordinary publish refuses this seal."""
    if not publication.host_private:
        raise ValueError('private reader writer requires a host-private seal')
    out = _output_root(instance, out)
    with _publisher(out):
        return _publish(instance, out, publication)


def _publish(instance, out, publication):
    """Commit an immutable generation, then atomically switch its only authority."""
    from .publication import Publication
    if type(publication) is not Publication:
        raise TypeError('writer accepts only a gate Publication')
    publication.check(instance)
    out = _output_root(instance, out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Build entirely aside, without exposing a half-written payload/manifest pair.
    with tempfile.TemporaryDirectory(prefix='familiar-generation-', dir=out.parent) as directory:
        staged = Path(directory) / 'generation'
        staged.mkdir()
        files = publication.files()
        for name, data in files.items():
            _put(_relative(staged, name), data)
        from importlib.metadata import version

        from familiar.rules.roles import method_root
        method_digest = hashlib.sha256(encode({p.relative_to(method_root()).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                              for p in sorted(method_root().rglob('*')) if p.is_file()})).hexdigest()
        manifest = {'inputs': publication.inputs, 'files': {k: content_digest(v) for k, v in files.items()},
                    'review': publication.manifest, 'engine': {'version': version('familiar'), 'method': method_digest}}
        identity = hashlib.sha256(encode(manifest)).hexdigest()
        _put(staged / 'generation.json', encode(manifest))
        publication.check(instance)
        out.mkdir(parents=True, exist_ok=True)
        target = out / '.generations' / identity
        target.parent.mkdir(exist_ok=True)
        if not target.parent.resolve().is_relative_to(out) or not target.resolve().is_relative_to(out):
            raise ValueError('generation directory escapes output root')
        if target.exists():
            expected = {**files, 'generation.json': encode(manifest)}
            try:
                valid = ({p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()} == set(expected)
                         and all(_relative(target, name).read_bytes() == value for name, value in expected.items()))
            except OSError:
                valid = False
            if not valid:
                # A corrupt generation is not reusable. Quarantine it aside so
                # the complete replacement is renamed into place in one step.
                target.rename(Path(directory) / 'rejected')
        if not target.exists():
            staged.rename(target)
        # This check occurs after all payload bytes and before the atomic commit.
        publication.check(instance)
        if (out / '.CURRENT.tmp').is_symlink():
            raise ValueError('generation pointer cannot be a symlink')
        pointer = _relative(out, '.CURRENT.tmp')
        _put(pointer, encode({'generation': identity}))
        try:
            publication.check(instance)
            os.replace(pointer, out / 'CURRENT.json')
        finally:
            pointer.unlink(missing_ok=True)
    return target


def review_material(instance, out, publication):
    """Store exact private preview bytes and their ticket together, never a generation."""
    from .review import review_ticket
    out = _output_root(instance, out)
    if out.exists():
        raise ValueError('review material directory already exists; use a new directory')
    publication.check(instance)
    try:
        for name, content in publication.files().items():
            _put(_relative(out, name), content)
        _put(out / 'review-ticket.json', encode(review_ticket(publication)))
        publication.check(instance)
    except BaseException:
        if out.exists():
            shutil.rmtree(out)
        raise
    return out / 'review-ticket.json'


def save_book(instance, out, publication, *, language, kids, page_size):
    """Commit a portable print artifact from checked reader bytes, never raw input.

    This is a final offline copy, not a reusable reader generation: it cannot
    recheck consent after leaving the machine, just like a printed paper book.
    """
    from familiar.reader.book import compose
    from familiar.reader.export import output_path

    from .publication import Publication
    if type(publication) is not Publication or publication.working:
        raise ValueError('book writer requires a sealed reader projection')
    if publication.manifest.get('kind') not in {'reader', 'reader-private'}:
        raise ValueError('book writer requires reader review material')
    out = output_path(instance, out)
    publication.check(instance)
    files, result = compose(instance, publication, language=language, kids=kids, page_size=page_size)
    out.parent.mkdir(parents=True, exist_ok=True)
    lock = out.parent / ('.' + out.name + '.book.lock')
    try:
        stream = lock.open('xb')
    except FileExistsError as exc:
        raise ValueError('Book build in progress for this output; use another empty directory') from exc
    try:
        with stream, tempfile.TemporaryDirectory(prefix='familiar-book-', dir=out.parent) as directory:
            staged = Path(directory) / 'book'
            staged.mkdir()
            for name, content in files.items():
                _put(_relative(staged, name), content)
            publication.check(instance)
            output_path(instance, out)
            if out.exists():
                out.rmdir()  # Only an empty destination; a concurrent file refuses.
            staged.rename(out)
    finally:
        lock.unlink(missing_ok=True)
    return dict(result, output=str(out))


def save_working(instance, out, graph, inputs):
    """A private working artifact has no generation pointer or publication verdict."""
    out = _output_root(instance, out)
    if (out / 'CURRENT.json').exists():
        raise ValueError('working tree needs a separate directory from reader generations')
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='familiar-working-', dir=out) as directory:
        staged = Path(directory) / 'working-tree.json'
        _put(staged, encode({'view': 'working', 'graph': graph}))
        if inputs != fingerprints(instance):
            raise ValueError('family inputs changed before saving working tree')
        os.replace(staged, out / 'working-tree.json')


def generation(instance, out):
    """The mandatory reader: checks live inputs and every byte on every use."""
    root, manifest = _generation_manifest(instance, out)
    _check_uses(instance, manifest)
    _check_file_set(root, manifest)
    for name, digest in manifest['files'].items():
        if hashlib.sha256(_relative(root, name).read_bytes()).hexdigest() != digest:
            raise ValueError('generation payload checksum mismatch')
    return root


def _generation_manifest(instance, out):
    out = _output_root(instance, out)
    pointer = json.loads((out / 'CURRENT.json').read_text(encoding='utf-8'))
    ident = pointer.get('generation', '')
    if not isinstance(ident, str) or len(ident) != 64 or any(c not in '0123456789abcdef' for c in ident):
        raise ValueError('invalid generation pointer')
    root = out / '.generations' / ident
    if not root.resolve().is_relative_to(out):
        raise ValueError('generation escapes output root')
    manifest = json.loads((root / 'generation.json').read_text(encoding='utf-8'))
    if hashlib.sha256(encode(manifest)).hexdigest() != ident:
        raise ValueError('generation manifest checksum mismatch')
    return root, manifest


def _check_file_set(root, manifest):
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != set(manifest['files']) | {'generation.json'}:
        raise ValueError('generation file set differs')


def read_generation(instance, out):
    """Read once, verify those exact immutable bytes, then recheck dependencies."""
    root, manifest = _generation_manifest(instance, out)
    _check_file_set(root, manifest)
    files = {name: _relative(root, name).read_bytes() for name in manifest['files']}
    for name, data in files.items():
        if hashlib.sha256(data).hexdigest() != manifest['files'][name]:
            raise ValueError('generation changed during read')
    _check_uses(instance, manifest)
    return files


def _check_uses(instance, manifest):
    from familiar.checks.engine import _known_people, life_status, load

    from .publication import INFO_FIELDS, allowed
    from .review import _safety_inputs, digest
    instance = fresh(instance)
    if manifest.get('review', {}).get('state') == 'host-private':
        if manifest['inputs'] != fingerprints(display_instance(instance)):
            raise ValueError('private reader inputs changed; rebuild the local view')
        return
    uses = manifest.get('review', {}).get('uses', [])
    known, privacy = _known_people(instance), load(instance.path('privacy'), {})
    removed = []
    review = manifest.get('review', {})
    for row in review.get('attestations', []):
        if row.get('inspection_digest') != digest([row.get('page'), row.get('language'), row.get('digest'), row.get('safety_digest')]):
            removed.append(str(row.get('page')) + ':review-again:inspection-ticket')
    for use in uses:
        pid, field = use['person'], use['field']
        if field == 'archive-rights':
            continue
        if field == 'document' and use.get('record'):
            from familiar.checks.engine import record_path

            from .subjects import closure
            path = record_path(instance, use['record'])
            record = load(path, {})
            resolved = closure(instance, {'record': use['record'], **({'excerpt': use['excerpt']} if use.get('excerpt') else {})}, shape='source', people=known)
            if (not use.get('excerpt') and record.get('privacy') in {'living', 'living-possible'}) or any(
                    life_status(known[subject], privacy) != 'dead' for subject in resolved.people):
                removed.append(use['item'] + ':document')
            continue
        status = life_status(known.get(pid, {'id': pid}), privacy)
        if use.get('generated') and (status != 'dead' or use.get('subject_child')):
            removed.append(use['item'] + ':generated:' + str(pid))
        if use.get('permission') == 'never-if-living' and status != 'dead':
            removed.append(use['item'] + ':' + field + ':' + str(pid))
        permission = allowed(privacy, pid)
        if pid not in known or (status != 'dead' and field not in {'name', 'kinship'} and
                (field not in INFO_FIELDS or (field not in permission and use.get('permission') not in permission))):
            removed.append(use['item'] + ':' + field + ':' + pid)
    safety = _safety_inputs(instance, {u['person'] for u in uses if u['person']}, uses)
    old = manifest.get('review', {}).get('safety', {})
    if safety.get('people') != old.get('people'):
        removed.extend(u['item'] + ':review-again:person-safety' for u in uses if u['person'])
    for key in ('closed_topics', 'lists', 'archive_rights', 'trust'):
        if safety.get(key) != old.get(key):
            removed.extend(u['item'] + ':review-again:' + key for u in uses if key != 'archive_rights' or u['field'] == 'archive-rights')
            if not uses:
                removed.extend(manifest['files'])
    if removed:
        raise ValueError('withdrawn generation; remove: ' + ', '.join(sorted(set(removed))))


def generation_status(instance, out):
    root = generation(instance, out)
    manifest = json.loads((root / 'generation.json').read_text(encoding='utf-8'))
    if manifest.get('review', {}).get('state') == 'host-private':
        instance = display_instance(instance)
    changed = manifest['inputs'] != fingerprints(instance)
    return {'state': 'outdated' if changed else manifest['review']['state'],
            'changed_inputs': [p for p, value in fingerprints(instance).items() if manifest['inputs'].get(p) != value],
            'remove': [], 'unreviewed': manifest['review']['unreviewed']}


@boundary('writer')
def engine_release(instance, value):
    """Record wheel provenance without changing the pinned release or family inputs."""
    requested = instance.root / 'work/engine-release.json'
    if requested.is_symlink() or requested.parent.is_symlink():
        raise ValueError('Engine release record cannot be a symlink')
    path = _relative(instance.root, 'work/engine-release.json')
    _put(path, encode(value))
    return path


def desk_secret(instance, value):
    """Desk credentials and deployment coordinates have exactly one ignored file."""
    from familiar.desk.model import secret_path
    path = secret_path(instance)
    ignore = instance.root / '.gitignore'
    if not ignore.is_file() or '.secrets/' not in ignore.read_text(encoding='utf-8').splitlines():
        raise ValueError('Add .secrets/ to the instance .gitignore before provisioning')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    if temporary.is_symlink() or path.is_symlink():
        raise ValueError('Desk secret cannot be a symlink')
    _put(temporary, encode(value))
    temporary.chmod(0o600)
    os.replace(temporary, path)


def desk_private(instance, name, value):
    """Ignored desk handouts and transient CLI inputs; never delivery files."""
    if not re.fullmatch(r'[A-Za-z0-9_.-]+\.json', name):
        raise ValueError('Unsafe private desk filename')
    path = instance._inside('.secrets/' + name)
    ignore = instance.root / '.gitignore'
    if not ignore.is_file() or '.secrets/' not in ignore.read_text(encoding='utf-8').splitlines():
        raise ValueError('Add .secrets/ to the instance .gitignore before managing users')
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError('Desk secret cannot be a symlink')
    if value is None:
        path.unlink(missing_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        _put(path, encode(value))
        path.chmod(0o600)
    return path


@contextmanager
def desk_cloud(instance, command):
    """One foreground cloud operation per family; kernel locks die with the process."""
    path = instance._inside('.state/desk-cloud.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the inode: unlinking a released lock permits two different lock owners.
    with path.open('a+b') as stream:
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            stream.seek(1)
            active = stream.read().decode('utf-8', errors='replace').strip() or 'desk cloud command'
            raise RuntimeError(f'{active} is running; retry {command} after it finishes') from None
        try:
            stream.seek(1)
            stream.truncate()
            stream.write(command.encode('utf-8'))
            stream.flush()
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def desk_transition(instance, value):
    """Resumable deployment bookkeeping, not a stored family data form."""
    path = instance._inside('.state/desk-transition.json')
    if value is None:
        path.unlink(missing_ok=True)
    else:
        temporary = path.with_suffix('.tmp')
        _put(temporary, encode(value))
        os.replace(temporary, path)


def _coverage_inputs(instance):
    """Name, size and time of every file the host-private coverage block reads."""
    paths = set()
    for key in ('searches', 'records', 'versions'):
        base = instance.path(key)
        if base.is_dir():
            paths.update(p for p in base.rglob('*') if p.suffix in {'.json', '.jsonl'})
    paths.update((instance.root / 'research' / 'team').glob('**/corpus/records/*.json'))
    paths.add(instance.path('variant_overrides'))
    found = {}
    for p in sorted(paths):
        try:
            info = p.stat()
        except OSError:
            continue
        found[str(p)] = f'{info.st_size}:{info.st_mtime_ns}'
    return found


@contextmanager
def desk_reader(instance, active):
    """Reuse a private seal only while all of its semantic dependencies still match."""
    from familiar.reader.export import export
    from familiar.rules.roles import method_root
    active = display_instance(active)
    cache = _BuildCache(active)
    with _publisher(cache.root):
        token = _BUILD_CACHE.set(cache)
        try:
            watch = InputWatch(active)
            stamp = watch.stamp()
            inputs = fingerprints(active)
            selected = dict(inputs)
            # Pack UI prose is not reader data. Pack rules and every other byte
            # remain dependencies; only the desk dictionary is separated here.
            for pack in active.language_pack_data.values():
                selected[str(pack['path'])] = semantic_digest(
                    {k: v for k, v in pack['data'].items() if k != 'desk'})
            config = dict(active.config)
            config.pop('engine', None)
            selected[str(active.root / 'familiar.toml')] = semantic_digest(config)
            # The "where it was looked for" block reads the host's own journals and
            # records, which the display snapshot does not hold.
            selected['coverage'] = _coverage_inputs(instance)
            from datetime import date
            key = content_digest(encode([selected, cache.contract(), date.today().isoformat(),
                {str(p): input_digest(p) for p in method_root().rglob('*') if p.is_file()}]))
            record = cache.root / 'reader.json'
            try:
                saved = json.loads(record.read_bytes())
            except (OSError, ValueError):
                saved = {}
            secrets_root = instance._inside('.secrets')
            secrets_root.mkdir(parents=True, exist_ok=True)
            out = secrets_root / 'desk-reader-cache'
            if saved.get('key') != key:
                # Existing private export/gate remains the only seal producer.
                with tempfile.TemporaryDirectory(prefix='desk-reader-', dir=secrets_root) as directory:
                    staged = Path(directory) / 'reader'
                    export(active, staged, host_private=True)
                    old = Path(directory) / 'old'
                    if out.exists():
                        out.rename(old)
                    staged.rename(out)
                _put(record, encode({'key': key}))
                cache.metrics['reader_rebuilt'] = 1
            else:
                cache.metrics['reader_reused'] = 1
            root, manifest = _generation_manifest(active, out)
            if manifest.get('review', {}).get('state') != 'host-private':
                raise ValueError('desk cache is not a private reader seal')
            _check_file_set(root, manifest)
            files = {}
            for name, digest in manifest['files'].items():
                path = _relative(root, name)
                value = cache.read(path)
                if value.digest != digest:
                    raise ValueError('desk cache payload checksum mismatch: ' + name)
                files[name] = value if not name.endswith(('.json', '.html', '.svg')) else path.read_bytes()
            if watch.stamp() != stamp or fingerprints(active) != inputs:
                raise ValueError('desk reader inputs changed during build')
            yield files, watch, stamp
            cache.finish()
        finally:
            _BUILD_CACHE.reset(token)


@boundary('writer')
def store_desk(instance, bundle):
    """Commit only a decision-bound desk delivery, separate from reader releases."""
    from familiar.desk.build import DeskBundle
    from familiar.desk.model import output, relative, secret_path
    if type(bundle) is not DeskBundle:
        raise TypeError('Desk writer requires a checked DeskBundle')
    bundle.check(instance)
    out = output(instance)
    secrets_root = instance._inside('.secrets')
    if not out.is_relative_to(secrets_root) or out == secrets_root or secret_path(instance).is_relative_to(out):
        raise ValueError('Desk output must be a separate directory below .secrets')
    # The lock belongs to the stable parent, never the directory being swapped.
    with _publisher(out.parent), tempfile.TemporaryDirectory(prefix='desk-build-', dir=out.parent) as directory:
        staged = Path(directory) / 'site'
        staged.mkdir()
        try:
            old_manifest = json.loads(instance._inside('.secrets/desk-build.json').read_bytes())
        except (OSError, ValueError):
            old_manifest = {}
        for name, content in bundle.files.items():
            old = _relative(out, relative(name))
            if (old.is_file() and old_manifest.get('files', {}).get(name) == content_digest(content)
                    and old_manifest.get('metadata', {}).get(name) == _metadata(old)):
                content = StoredFile(old, content_digest(content), _metadata(old))
            _put(_relative(staged, relative(name)), content)
        bundle.check(instance)
        previous = Path(directory) / 'previous'
        if out.exists():
            out.rename(previous)
        try:
            staged.rename(out)
        except BaseException:
            if previous.exists():
                previous.rename(out)
            raise
        from familiar.desk.model import decision, sha
        _, decision_bytes = decision(instance)
        from datetime import UTC, datetime

        from familiar import __version__
        # Which engine built this desk is visible per family without opening the site.
        manifest = {'schema_version': 1, 'family_id': instance.id,
                    'engine_version': __version__, 'built_at': datetime.now(UTC).isoformat(timespec='seconds'),
                    'decision_sha256': sha(decision_bytes),
                    'files': {name: sha(data) for name, data in bundle.files.items()},
                    'metadata': {name: _metadata(_relative(out, name)) for name in bundle.files}}
        _put(instance._inside('.secrets/desk-build.json'), encode(manifest))


@contextmanager
def desk_upload(instance, *, personal):
    """Stage only the verified hosted projection; local owner bytes stay intact."""
    from familiar.desk.build import CheckedDesk, hosted_files
    from familiar.desk.feedback import owner_only
    from familiar.desk.model import source
    checked = CheckedDesk(instance)
    public_ids = {p.stem for p in source(instance)._inside('family/feedback/inbox').glob('*.json')
                  if not owner_only(json.loads(p.read_bytes()))}
    files = hosted_files(checked.files, personal=personal, feedback_ids=public_ids)
    with tempfile.TemporaryDirectory(prefix='familiar-desk-upload-') as directory:
        root = Path(directory)
        for name, content in files.items():
            _put(_relative(root, name), content)
        checked.check()
        yield root, len(files)


@boundary('writer')
def save_demo_site(instance, out, bundle):
    """Store a checked fictional desk without granting real private publication."""
    from familiar.desk.build import DeskBundle
    if type(bundle) is not DeskBundle:
        raise TypeError('Demo writer requires a checked DeskBundle')
    if instance.config.get('family', {}).get('fictional') is not True:
        raise ValueError('Static demo export requires a fictional family')
    bundle.check(instance)
    out = _output_root(instance, out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError('output must be an empty directory')
    out.parent.mkdir(parents=True, exist_ok=True)
    with _publisher(out), tempfile.TemporaryDirectory(prefix='demo-site-', dir=out.parent) as directory:
        staged = Path(directory)
        for name, content in bundle.files.items():
            _put(_relative(staged, name), content)
        bundle.check(instance)
        for item in staged.iterdir():
            item.rename(out / item.name)


@boundary('writer')
def desk_feedback(instance, identity, content, *, local=False):
    """Incoming narrator words are append-only raw JSON, never accepted memory."""
    import uuid
    identity = str(uuid.UUID(identity))
    path = instance._inside('family/feedback/inbox/' + identity + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('xb') as stream:
            stream.write(content)
    except FileExistsError:
        if path.read_bytes() != content:
            raise ValueError('Feedback collision; original narrator words were retained') from None
    from .correspondence import apply_feedback
    return apply_feedback(instance, json.loads(content), local=local)
