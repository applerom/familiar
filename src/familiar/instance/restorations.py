# START_MODULE_CONTRACT: MOD-PHOTO-RESTORATIONS
# PURPOSE: Bind generated restorations to deceased subjects, real frames and append-only recipes.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - named subjects must be dead everywhere; unnamed people require a dated historical period frame [test: tests/gate/test_data_guarantees.py::test_photo_treatment_stays_local_for_living_subject]
# - every version binds original and output bytes, crop, model and comparison recipe [review: engine lead]
# - family transactions append versions rather than replace their recipes or bytes [review: engine lead]
# CHANGES_WITH:
# - MOD-SUBJECT-CLOSURE
# - MOD-PUBLICATION
# - MOD-FAMILY-WRITER
# :END_MODULE_CONTRACT
import copy
import hashlib
import json
import math
import re
from datetime import date


def period_pair(image):
    """An archival period frame paired with a restoration, in either authored shape."""
    if image.get('kind') == 'photo-restoration':
        return (image.get('orig') or {}).get('kind') == 'period-picture'
    return image.get('kind') == 'period-picture' and (image.get('ours') or {}).get('kind') == 'photo-restoration'


def historical_frame(instance, record):
    """The corpus date is the latest date this camera could have seen the people."""
    from familiar.rules.cascade import Registry
    from familiar.rules.roles import method_root
    from familiar.tree.life import recorded

    when = record.get('date')
    if not isinstance(when, str) or not recorded(record):
        return False
    if re.fullmatch(r'[0-9]{4}', when):
        when += '-12-31'  # a bare year may mean its last day
    try:
        captured = date.fromisoformat(when)
    except ValueError:
        return False
    today = date.today()
    horizon = Registry(method_root() / 'rules', instance).resolve_setting('privacy.living_years').value
    return (captured.year + max(100, horizon), captured.month, captured.day) <= (today.year, today.month, today.day)


def restorations(value):
    if isinstance(value, dict):
        if value.get('kind') == 'photo-restoration':
            yield value
        for key, child in value.items():
            if key != 'orig':
                yield from restorations(child)
    elif isinstance(value, list):
        for child in value:
            yield from restorations(child)


def bind(instance, original, restored):
    from PIL import Image
    from familiar.checks.engine import _known_people, generated, life_status, load, record_path
    from .archive import photograph_rights
    from .gallery import PREFIX
    from .subjects import closure, protected_record
    fail = 'TRUST-08: photo restoration '
    source = {k: copy.deepcopy(v) for k, v in original.items() if k != 'ours'}
    reference = restored.get('orig')
    if reference is not None and (not isinstance(reference, dict) or reference.get('asset') != source.get('asset')):
        raise ValueError(fail + 'must name the same original frame')
    rights = photograph_rights(instance, source)
    genuine = (source.get('kind') == 'family-photograph' and 'subjects' in source and rights and
               rights.get('holder') and rights.get('permissions', {}).get('family_app'))
    genuine = genuine or (source.get('kind') in {'period-picture', 'document-scan'} and
                          record_path(instance, source.get('record')).is_file())
    if not genuine or generated(source) or source.get('reconstruction') or source.get('orig'):
        raise ValueError(fail + 'needs a real original with corpus reference or family-photo rights')
    known, privacy = _known_people(instance), load(instance.path('privacy'), {})
    resolved = closure(instance, source, shape='image', people=known)
    period = source.get('kind') == 'period-picture' and not (source.get('asset') or '').startswith('/' + PREFIX)
    if source.get('subject_living') or any(life_status(known[p], privacy) != 'dead' for p in resolved.people):
        raise ValueError(fail + 'requires deceased subjects; living or unknown is forbidden everywhere')
    if any(map(protected_record, resolved.records.values())):
        raise ValueError(fail + 'cannot use a protected original')
    if 'unidentified_people' in source and type(source['unidentified_people']) is not bool:
        raise ValueError(fail + 'unidentified_people must be a boolean')
    if source.get('unidentified_people') and not (
            period and isinstance(source.get('subjects'), list)
            and historical_frame(instance, resolved.records[source['record']])):
        raise ValueError(fail + 'unnamed people require a corpus capture date at least a century old')
    if not resolved.people and not (period and source.get('subjects') == []):
        raise ValueError(fail + 'requires deceased subjects or an explicit subject list for a period picture')
    source['subjects'] = sorted(resolved.people)
    for key in ('subjects', 'record'):
        if key in restored and restored[key] != source.get(key) and not source.get('_document_attributed'):
            raise ValueError(fail + 'cannot change original subjects or record')
    versions = restored.get('versions')
    if not restored.get('id') or not source.get('caption') or not isinstance(versions, list) or not versions:
        raise ValueError(fail + 'needs an id, original caption and version recipes')
    original_path = instance.media_file(source.get('asset', ''))
    if not original_path:
        raise ValueError(fail + 'original file is missing')
    with Image.open(original_path) as frame:
        width, height = frame.size
    ids, assets = set(), set()
    for version in versions:
        if not isinstance(version, dict):
            raise ValueError(fail + 'versions must contain objects with recipes')
        recipe = version.get('recipe', {})
        ident, asset = version.get('id'), version.get('asset')
        if not isinstance(ident, str) or not ident or ident in ids or not asset or asset in assets or asset == source.get('asset'):
            raise ValueError(fail + 'needs unique version ids and separate immutable assets')
        ids.add(ident)
        assets.add(asset)
        if not version.get('caption') or not version.get('disclosure') or not isinstance(recipe, dict):
            raise ValueError(fail + 'needs version captions, disclosure and recipe')
        if (type(recipe.get('version')) is not int or recipe['version'] < 1 or
                not isinstance(recipe.get('model'), str) or not recipe['model'].strip() or
                not isinstance(recipe.get('prompt'), str) or not recipe['prompt'].strip() or
                recipe.get('original_asset') != source.get('asset') or
                not isinstance(recipe.get('invented'), list) or not recipe['invented'] or
                any(not isinstance(s, str) or not s.strip() for s in recipe['invented'])):
            raise ValueError(fail + 'recipe needs version, model, prompt, original and invented details')
        try:
            date.fromisoformat(recipe['date'])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(fail + 'recipe needs an ISO model-run date') from exc
        numbers = recipe.get('comparison', {})
        keys = ('attempts', 'chosen_attempt', 'reduced_width_px', 'blur_radius_px', 'mean_absolute_error')
        if not isinstance(numbers, dict) or any(type(numbers.get(k)) not in (int, float) or not math.isfinite(numbers[k]) or numbers[k] < 0 for k in keys):
            raise ValueError(fail + 'recipe needs finite numeric comparison measurements')
        if (not 1 <= numbers['chosen_attempt'] <= numbers['attempts'] or numbers['reduced_width_px'] < 1 or
                numbers['mean_absolute_error'] > 255):
            raise ValueError(fail + 'comparison attempt or reduced size is invalid')
        crop = recipe.get('crop', [0, 0, width, height])
        if not isinstance(crop, list) or len(crop) != 4 or any(type(n) not in (int, float) or not math.isfinite(n) for n in crop):
            raise ValueError(fail + 'crop must be pixel [left, top, width, height]')
        x, y, w, h = crop
        if min(x, y) < 0 or min(w, h) <= 0 or x + w > width or y + h > height:
            raise ValueError(fail + 'crop is outside original frame')
        path = instance.media_file(asset)
        if not path:
            raise ValueError(fail + 'version file is missing')
        for field, file in [('original_sha256', original_path), ('sha256', path)]:
            if recipe.get(field) != hashlib.sha256(file.read_bytes()).hexdigest():
                raise ValueError(fail + 'recipe hash differs from original or version bytes')
        with Image.open(path) as edited:
            if abs((edited.width / edited.height) / (w / h) - 1) > .02:
                raise ValueError(fail + 'aspect ratio differs from the original crop by over 2%')
    selected = next((v for v in versions if v['id'] == restored.get('primary')), None)
    if selected is None:
        raise ValueError(fail + 'primary must name a saved version')
    restored.update({k: copy.deepcopy(selected[k]) for k in ('asset', 'caption', 'disclosure')})
    restored.update(orig=source, subjects=sorted(resolved.people), reconstruction=True)
    if source.get('record'):
        restored['record'] = source['record']


def preserve(before, after):
    """A family writer may select or append a version, never edit a saved one."""
    current = {r.get('id'): r for r in restorations(after)}
    for old in restorations(before):
        new = current.get(old.get('id'), {})
        versions = {v['id']: v for v in new.get('versions', [])}
        if any(versions.get(v['id']) != v for v in old.get('versions', [])):
            raise ValueError('Photo restoration versions are append-only; save a new version and asset')


def inventory(instance):
    """List authored recipes, including previous and alternative versions, without generating."""
    from .writer import _input_paths
    rows = []
    for path in sorted(_input_paths(instance)):
        if path.suffix != '.json' or not path.is_file() or not path.is_relative_to(instance.root):
            continue
        for restored in restorations(json.loads(path.read_text(encoding='utf-8'))):
            for version in restored.get('versions', []):
                recipe = version.get('recipe', {})
                rows.append({'file': path.relative_to(instance.root).as_posix(), 'restoration': restored.get('id'),
                             'id': version.get('id'), 'primary': version.get('id') == restored.get('primary'),
                             'age_days': (date.today() - date.fromisoformat(recipe['date'])).days,
                             'asset': version.get('asset'), 'recipe': recipe})
    return rows
