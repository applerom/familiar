# START_MODULE_CONTRACT: MOD-NARRATIVE-DISCLOSURE
# PURPOSE: Project subject-linked story passages for family and public readers.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - unattributed nested prose conservatively inherits its chapter's subjects [review: engine lead]
# - protected canonical names in feed signatures and tree nodes exclude inferred components [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (default-deny reader fields and private attribution)
# - MOD-FEED-BUILDER (canonical blocks and optional otherwise passage)
# - MOD-OUTPUT-REVIEW (shown alternatives and attributed items enter generation uses)
# - docs/gate.md
# :END_MODULE_CONTRACT
import copy


def restrict_feed(instance, feed, *, host_private=False):
    from familiar.checks.engine import _known_people, life_status, load

    from .publication import confirmed_name
    privacy, known = load(instance.path('privacy'), {}), _known_people(instance)
    feed = copy.deepcopy(feed)
    safe_names = {pid: confirmed_name(person) for pid, person in known.items()
                  if not host_private and life_status(person, privacy) != 'dead'
                  and any(n.get('inferred_parts') for n in person.get('names', []))}
    for pid, name in safe_names.items():
        if pid in feed.get('names', {}):
            feed['names'][pid] = {**{lang: name for lang in instance.languages},
                                  'short': {lang: name for lang in instance.languages}}

    def restricted(ids):
        if host_private:
            return []
        result = []
        for pid in ids:
            if pid not in known:
                raise ValueError('TRUST-01: unknown narrative subject: ' + str(pid))
            if life_status(known[pid], privacy) != 'dead':
                result.append(known[pid].get('id', pid))
        return list(dict.fromkeys(result))

    for group in feed.get('gens', []):
        if restricted(group.get('ids', [])):
            group['years'] = ''

    def nodes(value):
        if isinstance(value, dict):
            if value.get('id') in safe_names and 'name' in value:
                value['name'] = {lang: safe_names[value['id']] for lang in instance.languages}
            if value.get('id') and value.get('year') and restricted([value['id']]):
                value.pop('year')
            for child in value.values():
                nodes(child)
        elif isinstance(value, list):
            for child in value:
                nodes(child)

    for chapter in [feed, *feed.get('chapters', [])]:
        defaults = chapter.get('people', [])
        nodes(chapter.get('tree', {}))
        for field in (('title', 'lead', 'period', 'line') if chapter is feed else ('title', 'text', 'more', 'ask', 'text_kids')):
            blocks = chapter.get('_prose', {}).get(field)
            if blocks is not None:
                shown = []
                for block in blocks:
                    ids = restricted(block['people'])
                    if not ids:
                        shown.append(block['text'])
                        continue
                    alternative = block.get('otherwise')
                    if alternative and not restricted(alternative['people']):
                        shown.append(alternative['text'])
                chapter[field] = {lang: '\n\n'.join(
                    b.get(lang, '') for b in shown if b.get(lang, '').strip())
                    for lang in instance.languages}
            elif chapter.get(field) and restricted(defaults):
                chapter.pop(field)
        for field in ('facts', 'variants', 'places', 'extras', 'links', 'kids', 'game'):
            if not chapter.get(field):
                continue
            items = chapter[field] if isinstance(chapter[field], list) else [chapter[field]]
            kept = []
            for item in items:
                ids = restricted(item.get('_people', defaults))
                if not ids:
                    kept.append(item)
            if not kept:
                chapter.pop(field)
            else:
                chapter[field] = kept if isinstance(chapter[field], list) else kept[0]
        # Authoring classification is not part of the reader's story.
        chapter.pop('kind', None)
    return feed
