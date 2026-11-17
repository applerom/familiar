# START_MODULE_CONTRACT: MOD-HOST-PAGES
# PURPOSE: Render the host's full private story with its current reader review state.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - reader acceptance is checked against current reader bytes and reported separately from feed acceptance [review: cold reviewer]
# - private story text is labelled as working material before it is shown [review: cold reviewer]
# - withheld chapter media name the affected item, display audience and next action [review: engine lead]
# CHANGES_WITH:
# - MOD-FEED-CLI (plain-text pages option)
# - MOD-OUTPUT-REVIEW (source-page review units)
# - MOD-FAMILY-GATE (current reader review manifest)
# - MOD-REGION-DEMO-ENGLISH (separate reader and feed status wording, also ru/pl)
# :END_MODULE_CONTRACT
from .publication import project
from .review import _output_uses, _review_manifest, _review_units


def _pages(data, feed=None, selection=None, *, titles_only=False):
    from familiar.feeds.service import _materialize, folders

    instance, w = data.instance, data.words
    feeds = [project(_materialize(instance, folder)[0], 'feed', instance.languages)
             for folder in folders(instance, feed)]
    from .publication import media_omissions
    omitted = media_omissions(instance, [_materialize(instance, folder)[0] for folder in folders(instance, feed)])
    uses = _output_uses(instance, 'feeds', feeds, feed)
    review = _review_manifest(instance, _review_units(instance, 'feeds', feeds, {}), uses)
    # Reader and feeds have different projections and safety scopes. Never transfer
    # an attestation between them; recompute the reader's own checked manifest.
    from familiar.checks.engine import load
    saved = load(instance.path('state') / 'attestations.json', {})
    reader_review = None
    if any(key.startswith('reader:') for key in saved):
        from .gate import publication
        try:
            reader_review = publication(instance, 'reader', for_review=True).manifest
        except (ValueError, OSError, TypeError, KeyError):
            pass  # Working prose remains available; an unavailable reader is not confirmed.
    result = []
    found = False
    for row in feeds:
        for chapter in row['chapters']:
            if selection and chapter['id'] != selection:
                continue
            found = True
            unit = 'feed:' + row['id'] + '/' + chapter['id']
            unreviewed = any(key.startswith(unit + '@') for key in review['unreviewed'])
            released = any(r['page'] == unit for r in review['host_releases'])
            label = w('draft') if unreviewed or released else w('reviewed')
            reader_confirmed = (reader_review is not None and unit in reader_review['review_units']
                                and not any(key.startswith(unit + '@') for key in reader_review['unreviewed'])
                                and not any(r['page'] == unit for r in reader_review['host_releases']))
            if (unreviewed or released) and reader_confirmed:
                label = w('reader_confirmed_feed_pending')
            subjects = set(chapter.get('people', []))
            title = data.text(chapter.get('title'), subjects)
            if not title:
                result.append((w('withheld') + '\n' + label if reader_confirmed else w('withheld'))
                              if titles_only else label + '\n' + w('withheld'))
                continue
            if titles_only:
                result.append(w('story_ready', title=title) if label == w('reviewed') else
                              title + '\n' + label if reader_confirmed else w('story_draft', title=title))
                continue
            parts = [label, title, data.text(chapter.get('text'), subjects)]
            for extra in chapter.get('extras', []):
                parts.extend([data.text(extra.get('title'), subjects), data.text(extra.get('text'), subjects)])
            kids = chapter.get('kids', {})
            children = [data.text(chapter.get(key), subjects) for key in ('text_kids', 'ask')]
            if isinstance(kids, dict):
                children.extend(data.text(kids.get(k), subjects) for k in ('title', 'text'))
            children = list(filter(None, children))
            if children:
                # An authored children's heading already supplies the label.
                heading = w('children').strip().rstrip(':').casefold()
                first_lines = [text.splitlines()[0].strip().casefold() for text in children]
                labelled = any(line.rstrip(':') == heading or line.startswith(heading + ':') for line in first_lines)
                parts += ([] if labelled else [w('children')]) + ['\n\n'.join(children)]
            support = data.text(chapter.get('more'), subjects)
            parts += [w('support'), support or w('withheld' if chapter.get('more') else 'support_missing')]
            for document in chapter.get('records', []):
                parts += [data.text(document.get('title')), data.text(document.get('read'))]
                parts += [data.text(p.get('read')) for p in document.get('parts', [])]
            for omission in omitted:
                if omission['feed'] == row['id'] and omission['chapter'] == chapter['id']:
                    parts.append(w('media_omitted', view=w('media_' + omission['view']),
                        item=w('media_' + omission['field']) + ': ' + data.text(omission['label']),
                        reason=data.text(omission['reason']).replace('(living)', '(' + w('media_living') + ')').replace('(unknown)', '(' + w('media_unknown') + ')')
                            if omission['reason'] not in {'protected document or undeclared subjects', 'withheld document'} else w('media_protected'),
                        action=w('media_action_' + omission['action'])))
            result.append('\n\n'.join(filter(None, parts)))
    if selection and not found:
        raise ValueError('No such story page.')
    return (result if titles_only else '\n\n'.join(result) or w('no_pages')), review
