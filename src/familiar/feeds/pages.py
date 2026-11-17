# START_MODULE_CONTRACT: MOD-FEED-PAGES
# PURPOSE: Expose authored reading pages and explicit hardship annotations alongside materialized documents.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - unassessed hardship pages stay visible to the reader [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE (the shared family boundary contract)
# - docs/PRD.md#FORMS
# :END_MODULE_CONTRACT
from familiar.instance.gate import boundary
from familiar.instance.research_forms import PREVIEW

from .builder import read
from .service import _materialize, folders


@boundary('diagnostic')
def pages(instance, feed=None, *, preview=False):
    from familiar.instance.gate import evaluate, require

    from .service import input_fingerprints, refresh_output
    refresh_output(instance)
    verdict = evaluate(instance) if preview else require(instance)
    result = []
    publications = []
    for folder in folders(instance, feed):
        try:
            built, _ = _materialize(instance, folder)
            if not preview:
                from familiar.instance.gate import publication
                published = publication(instance, 'feeds', folder.name)
                built = published.data()[0]
                publications.append(published)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            if not preview:
                raise ValueError(f'materialization failed: {exc}') from exc
            result.append({'output': {'state': PREVIEW, 'inputs': input_fingerprints(instance)},
                           'trust': verdict, 'feed': folder.name, 'materialization_error': str(exc),
                           'pages': read(folder / 'chapters.json', [])})
            continue
        authored = {c['id']: c for c in read(folder / 'chapters.json', [])}
        rows, troubles = [], []
        for number, chapter in enumerate(built['chapters'], 1):
            events = chapter.get('hardships', [])
            rows.append({'page': number, **chapter, 'hardships': events})
            troubles.extend({'page': number, 'chapter': chapter['id'], **event} for event in events)
        result.append({'output': {'state': PREVIEW if preview else published.manifest['state'], 'unreviewed': [] if preview else published.manifest['unreviewed'], 'inputs': input_fingerprints(instance) if preview else published.inputs}, 'trust': verdict, 'feed': folder.name, 'pages': rows, 'hardship_map': troubles,
                       'hardship_coverage': 'Explicit chapters[].hardships only; missing annotations mean unassessed, not no hardship.',
                       'unassessed_pages': [c['id'] for c in built['chapters'] if 'hardships' not in authored[c['id']]]})
    for published in publications:
        published.check(instance)
    return result
