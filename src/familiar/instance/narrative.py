# START_MODULE_CONTRACT: MOD-NARRATIVE-DISCLOSURE
# PURPOSE: Project subject-linked story passages quietly for readers and retain the exact omissions for private family action.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - an author's alternative passage obeys the same canonical subject permissions as the original [test: tests/gate/test_data_guarantees.py::test_f3_living_fields_require_permission_and_exclude_addresses]
# - unattributed nested prose conservatively inherits its chapter's subjects [review: engine lead]
# - protected canonical names in feed signatures and tree nodes exclude inferred components [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (default-deny reader fields and private attribution)
# - MOD-FEED-BUILDER (canonical blocks and optional otherwise passage)
# - MOD-OUTPUT-REVIEW (shown alternatives and attributed items enter generation uses)
# - MOD-HOST-TEXT (private next actions)
# - docs/gate.md
# :END_MODULE_CONTRACT
import copy


def restrict_feed(instance, feed, *, hidden=None, host_private=False):
    from familiar.checks.engine import _known_people, life_status, load

    from .publication import allowed, confirmed_name
    privacy, known = load(instance.path('privacy'), {}), _known_people(instance)
    feed = copy.deepcopy(feed)
    safe_names = {pid: confirmed_name(person) for pid, person in known.items()
                  if not host_private and life_status(person, privacy) != 'dead'
                  and any(n.get('inferred_parts') for n in person.get('names', []))}
    for pid, name in safe_names.items():
        if pid in feed.get('names', {}):
            feed['names'][pid] = {**{lang: name for lang in instance.languages},
                                  'short': {lang: name for lang in instance.languages}}

    def restricted(ids, field='summary'):
        if host_private:
            return []
        result = []
        for pid in ids:
            if pid not in known:
                raise ValueError('TRUST-01: unknown narrative subject: ' + str(pid))
            if life_status(known[pid], privacy) != 'dead' and field not in allowed(privacy, pid):
                result.append(known[pid].get('id', pid))
        return list(dict.fromkeys(result))

    def paragraphs(value):
        if isinstance(value, dict):
            if instance.source_language in value:
                return paragraphs(value[instance.source_language])
            return sum(paragraphs(value.get(key)) for key in ('text', 'more', 'kids'))
        return sum(bool(p.strip()) for p in value.split('\n\n')) if isinstance(value, str) else 0

    def passage(value):
        if isinstance(value, dict):
            if instance.source_language in value:
                return passage(value[instance.source_language])
            return '\n\n'.join(filter(None, (passage(value.get(k)) for k in
                ('title', 'name', 'label', 'text', 'more', 'note', 'kids'))))
        return value if isinstance(value, str) else ''

    def omit(ids, chapter, field, value=None):
        if hidden is not None and ids:
            hidden.append({'people': ids, 'feed': feed['id'], 'chapter': chapter,
                           'field': field, 'paragraphs': 0 if field in {'title', 'period', 'line', 'years', 'places', 'links'} else paragraphs(value),
                           'text': passage(value)})

    for group in feed.get('gens', []):
        if ids := restricted(group.get('ids', []), 'birth'):
            if group.get('years'):
                omit(ids, '__feed__', 'years', group['years'])
            group['years'] = ''

    def nodes(value, chapter):
        if isinstance(value, dict):
            if value.get('id') in safe_names and 'name' in value:
                value['name'] = {lang: safe_names[value['id']] for lang in instance.languages}
            if value.get('id') and value.get('year') and (ids := restricted([value['id']], 'birth')):
                omit(ids, chapter, 'years', value['year'])
                value.pop('year')
            for child in value.values():
                nodes(child, chapter)
        elif isinstance(value, list):
            for child in value:
                nodes(child, chapter)

    for chapter in [feed, *feed.get('chapters', [])]:
        cid = '__feed__' if chapter is feed else chapter['id']
        defaults = chapter.get('people', [])
        nodes(chapter.get('tree', {}), cid)
        for field in (('title', 'lead', 'period', 'line') if chapter is feed else ('title', 'text', 'more', 'ask', 'text_kids')):
            blocks = chapter.get('_prose', {}).get(field)
            if blocks is not None:
                shown = []
                for block in blocks:
                    ids = restricted(block['people'])
                    if not ids:
                        shown.append(block['text'])
                        continue
                    omit(ids, cid, field, block['text'])
                    alternative = block.get('otherwise')
                    if alternative and not restricted(alternative['people']):
                        shown.append(alternative['text'])
                chapter[field] = {lang: '\n\n'.join(
                    b.get(lang, '') for b in shown if b.get(lang, '').strip())
                    for lang in instance.languages}
            elif chapter.get(field) and (ids := restricted(defaults)):
                omit(ids, cid, field, chapter[field])
                chapter.pop(field)
        for field in ('facts', 'variants', 'places', 'extras', 'links', 'kids', 'game'):
            if not chapter.get(field):
                continue
            items = chapter[field] if isinstance(chapter[field], list) else [chapter[field]]
            kept = []
            for item in items:
                ids = restricted(item.get('_people', defaults))
                if ids:
                    omit(ids, cid, field, item)
                else:
                    kept.append(item)
            if not kept:
                chapter.pop(field)
            else:
                chapter[field] = kept if isinstance(chapter[field], list) else kept[0]
        # Authoring classification is not part of the reader's story.
        chapter.pop('kind', None)
    return feed


def omissions(instance, feed=None):
    """Private, unsealed metadata; callers deliver it only through the host view."""
    from familiar.feeds.service import _materialize, folders
    hidden = []
    for folder in folders(instance, feed):
        built, _ = _materialize(instance, folder)
        restrict_feed(instance, built, hidden=hidden)
    result = {}
    for row in hidden:
        for pid in row['people']:
            summary = result.setdefault(pid, {'chapters': set(), 'paragraphs': 0, 'fields': set(), 'passages': []})
            if row['chapter'] != '__feed__':
                summary['chapters'].add((row['feed'], row['chapter']))
            summary['paragraphs'] += row['paragraphs']
            summary['fields'].add(row['field'])
            if row['text'] and row['text'] not in summary['passages']:
                summary['passages'].append(row['text'])
    return result
