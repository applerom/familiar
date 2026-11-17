# START_MODULE_CONTRACT: MOD-FEED-SERVICE
# PURPOSE: Build isolated feed artifacts and compare chapter dependencies with recorded approvals.
# PRD_REF: docs/PRD.md#PIPELINE
# INVARIANTS:
# - output is refused before writing on a blocking trust finding [review: engine lead]
# - permission content changes invalidate chapter approvals [review: engine lead]
# - builds write only beneath the selected output directory [review: engine lead]
# - desk materialization depends on feed catalogs, registered media, rules and referenced tree membership rather than unrelated biographies [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE (the shared family boundary contract)
# - MOD-OUTPUT-REVIEW (display-byte and scoped-safety approval bindings)
# - docs/PRD.md#FORMS
# - MOD-INSTANCE-MODEL (manifest-backed media resolution)
# :END_MODULE_CONTRACT
import copy
import hashlib
import json
from pathlib import Path

from familiar.instance.research_forms import PREVIEW, STALE
from familiar.rules.cascade import Registry
from familiar.rules.roles import method_root

from .builder import _Feed, asset_exists, context, read


def digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def folders(instance, feed=None):
    base = instance.path('feeds')
    if feed:
        path = (base / feed).resolve()
        if not path.is_relative_to(base) or not (path / 'feed.json').is_file():
            raise ValueError('unknown feed')
        return [path]
    return sorted(p.parent for p in base.glob('*/feed.json'))


def _materialize(instance, folder):
    from familiar.instance.writer import _BUILD_CACHE, cached
    if _BUILD_CACHE.get() is None or not (instance.path('media') / 'manifest.json').is_file():
        return _materialize_uncached(instance, folder)
    tree = read(instance.path('feed_graph'), {})
    if tree:
        ids = sorted(set(tree.get('people', {})) | set(tree.get('identityAliases', {})))
    else:
        raw = read(instance.path('tree_snapshot') / 'people.json', {})
        ids = sorted(p['id'] for p in raw.get('people', []))
        evidence = read(instance.path('evidence'), {})
        extra = evidence.get('people', {})
        ids += sorted(p['id'] for p in extra) if isinstance(extra, list) else sorted(extra)
    # Materialization looks up membership, not a person's biographical fields.
    dependencies = [ids, instance.languages, instance.source_language, instance.config.get('settings'),
                    instance.config.get('feed'),
                    {name: read(folder / (name + '.json')) for name in
                     ('feed', 'chapters', 'pictures', 'documents', 'translations', 'links', 'names')},
                    [{k: v for k, v in pack['data'].items() if k != 'desk'}
                     for pack in [*instance.packs, *instance.language_pack_data.values()]],
                    (instance.root / 'exceptions.toml').read_text(encoding='utf-8')
                        if (instance.root / 'exceptions.toml').is_file() else None,
                    read(instance.path('media') / 'manifest.json', {})]
    return cached('feeds', folder.name, dependencies, lambda: _materialize_uncached(instance, folder))


def _materialize_uncached(instance, folder):
    Registry(method_root() / 'rules', instance)
    profile = read(folder / 'feed.json', {}).get('profile', {})
    selected = profile.get('languages') if isinstance(profile, dict) else None
    active = copy.copy(instance)
    if isinstance(selected, list):
        active.languages = tuple(dict.fromkeys([instance.source_language,
            *(lang for lang in selected if isinstance(lang, str) and lang in instance.languages)]))
    token = context.set(active)
    try:
        obj = _Feed(folder)
        result = obj._build()
        def validate(value, where):
            if isinstance(value, dict):
                for key, child in value.items():
                    location = f'{where}.{key}'
                    if key in ('asset', 'full') and child and not asset_exists(child):
                        obj.hole(location, f'file {child} is missing', 'feed.local-asset')
                    else:
                        validate(child, location)
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    validate(child, f'{where}[{index}]')
        validate(result, folder.name)
        if obj.holes:
            raise ValueError('\n'.join(obj.holes))
        status = obj.ft.status(obj.units, obj.stale, obj.tr)
        return result, {'translations': status, 'stale_units': sorted(obj.stale), 'advice': obj.notes}
    finally:
        context.reset(token)


def _inspect(instance, folder):
    result, details = _materialize(instance, folder)
    from familiar.instance.publication import scan
    from familiar.instance.review import _output_uses, _review_units, _safety_inputs
    shown = scan(instance, result, 'feed')
    uses = _output_uses(instance, 'feeds', [shown], folder.name)
    safety = _safety_inputs(instance, {u['person'] for u in uses if u['person']}, uses)
    units = _review_units(instance, 'feeds', [shown], {})
    fingerprints = {c['id']: digest([units['feed:' + folder.name + '/' + c['id']], safety])
                    for c in shown['chapters']}
    old = read(folder / 'state.json', {}).get('build_fingerprints', {})
    stale = [key for key, value in fingerprints.items() if old.get(key) != value]
    waiting = read(folder / 'feed.json', {}).get('waiting_family')
    state = read(folder / 'state.json', {})
    stage_names = ('scenario', 'text', 'cards', 'drawing', 'blind', 'reading', 'translation', 'connect')
    stages = {name: [cid for cid, fp in fingerprints.items()
                     if state.get('pipeline', {}).get(name, {}).get(cid) != fp] for name in stage_names}
    registry = Registry(method_root() / 'rules', instance)
    if (not registry.resolve_setting('drawing.enabled', 'feed:' + folder.name).value or
            read(folder / 'feed.json', {}).get('profile', {}).get('pictures') in ('none', 'period')):
        for key in ('cards', 'drawing', 'blind'):
            stages[key] = []
    return {**details, 'fingerprints': fingerprints, 'stale_chapters': stale,
            'stages': stages,
            'translation_dependencies_stale': stale,
            'waiting_family': waiting,
            'next': 'waiting_family' if waiting else next((name for name, pending in stages.items() if pending),
                    'translation' if any(s['missing'] or s['stale'] for s in details['translations'].values()) else 'ready')}


from familiar.instance.gate import boundary


@boundary('output')
def materialize(instance, folder):
    from familiar.instance.gate import publication
    result = publication(instance, 'feeds', Path(folder).name).data()
    return result[0], _inspect(instance, folder)


@boundary('output')
def build(instance, out, feed=None):
    from familiar.instance.gate import publication
    from familiar.instance.writer import publish
    result = publication(instance, 'feeds', feed)
    out = Path(out).resolve()
    publish(instance, out, result)
    return result.data()


def input_fingerprints(instance):
    from familiar.instance.writer import fingerprints
    return fingerprints(instance)


@boundary('consume')
def read_output(instance, out=None):
    from familiar.instance.writer import read_generation
    files = read_generation(instance, out or instance.path('build') / 'feeds')
    return json.loads(files['feeds.json'])


def refresh_output(instance, out=None):
    from familiar.instance.writer import generation, generation_status
    out = Path(out) if out else instance.path('build') / 'feeds'
    if not (out / 'CURRENT.json').is_file():
        return {'state': PREVIEW, 'reason': 'No validated output'}
    try:
        generation(instance, out)
    except (ValueError, OSError) as exc:
        return {'state': 'withdrawn' if 'withdrawn' in str(exc) else STALE, 'reason': str(exc), 'remove': ['feeds.json']}
    return generation_status(instance, out)


@boundary('diagnostic')
def inspect(instance, folder=None):
    from familiar.instance.gate import evaluate
    verdict = evaluate(instance)
    if verdict['blocked']:
        return {'output': {'state': PREVIEW}, 'trust': verdict, 'next': 'blocked'}
    folder = folder if folder is not None else folders(instance)[0]
    return dict(_inspect(instance, folder), output={'state': PREVIEW}, trust=verdict)
