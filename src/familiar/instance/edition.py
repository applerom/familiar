# START_MODULE_CONTRACT: MOD-FAMILY-EDITION
# PURPOSE: Carry authored card decisions and selected local galleries into privacy-governed reader projections.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - editorial input cannot override document, address or public-display exclusions [review: engine lead]
# - every selected gallery file must resolve even when its owner is private [review: engine lead]
# - canonical card decisions win over an alias without losing distinct alias facts [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (card schema and disclosure policies)
# - MOD-INSTANCE-VALIDATION (editorial references are checked at intake)
# - docs/reader-export.md
# :END_MODULE_CONTRACT
import copy
import json

CARD_FIELDS = {'name', 'namePresentation', 'cardPresentation', 'story', 'storyMore',
               'summary', 'facts', 'media', 'illustrations', 'relationshipUncertain'}


def cards(instance):
    """Optional file or directory; legacy people/feeds/updates envelopes select only people."""
    from .publication import project
    from .subjects import normalized
    result = {}
    base = instance.path('edition')
    if not base.exists() and ('edition' in instance.overrides or 'edition' in instance.host_paths):
        raise ValueError(f'edition: declared input is missing: {base}')
    paths = sorted(base.rglob('*.json')) if base.is_dir() else [base] if base.is_file() else []
    for path in paths:
        data = normalized(json.loads(path.read_text(encoding='utf-8')))
        if not isinstance(data, dict) or not isinstance(data.get('people'), dict):
            raise TypeError(f'{path}: edition requires a people map')
        if 'schema_version' in data and (type(data['schema_version']) is not int or data['schema_version'] != 1):
            raise ValueError(f'{path}: unsupported edition schema_version')
        for pid, patch in data['people'].items():
            if not isinstance(patch, dict):
                raise ValueError(f'{path}: editorial card must be an object: {pid}')
            patch = {key: value for key, value in patch.items() if key in CARD_FIELDS}
            if pid in result:
                raise ValueError(f'{path}: duplicate editorial card: {pid}')
            project(patch, 'person', instance.languages)  # validate declared shapes/text
            result[pid] = patch
    return result


def errors(instance):
    """Check the entire authored selection, not just today's public subset."""
    from familiar.checks.engine import _known_people

    patches = cards(instance)
    if not patches:
        return
    known = _known_people(instance)

    def assets(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {'asset', 'full', 'originalAsset'} and child:
                    if not instance.media_file(child):
                        yield f'edition: missing local gallery file: {child}'
                else:
                    yield from assets(child)
        elif isinstance(value, list):
            for child in value:
                yield from assets(child)

    for pid, patch in patches.items():
        if pid not in known:
            yield f'edition: unknown person: {pid}; inspect ids with tree build --view working'
        for key in ('media', 'illustrations'):
            for image in patch.get(key, []):
                if not isinstance(image, dict) or not image.get('asset'):
                    yield f'edition: gallery requires declared image fields and a local asset: {pid}'
                yield from assets(image)


def apply(instance, graph):
    """Overlay only card fields; restrict_graph subsequently enforces display exclusions."""
    aliases = graph.get('identityAliases', {})
    patches = copy.deepcopy(cards(instance))
    for alias, target in aliases.items():
        patch = patches.pop(alias, None)
        if patch is None:
            continue
        kept = patches.setdefault(target, {})
        for key, value in patch.items():
            if key not in kept:
                kept[key] = value
            elif key == 'facts':
                kept[key] += [f for f in value if f not in kept[key]]
            elif isinstance(value, dict) and key != 'story':
                kept[key] = value | kept[key]
    for pid, patch in patches.items():
        if pid not in graph.get('people', {}):
            raise ValueError(f'edition: unknown projected person: {pid}')
        person = graph['people'][pid]
        for key, value in patch.items():
            if key in {'namePresentation', 'cardPresentation'}:
                person.setdefault(key, {}).update(value)
            elif key == 'facts':
                labels = {f.get('label') for f in value}
                person[key] = value + [f for f in person.get(key, []) if f.get('card') and f.get('label') not in labels]
            else:
                person[key] = value
    return graph
