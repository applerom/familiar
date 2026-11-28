# START_MODULE_CONTRACT: MOD-NARRATIVE-DISCLOSURE
# PURPOSE: Project subject-linked story passages for family and public readers.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - unattributed nested prose conservatively inherits its chapter's subjects [review: engine lead]
# - public prose and games inherit the protection of their declared papers [review: engine lead]
# - protected canonical names in feed signatures and tree nodes exclude inferred components [review: engine lead]
# - instance check names passages with missing privacy attribution separately from restricted blocks [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (default-deny reader fields and private attribution)
# - MOD-FEED-BUILDER (canonical blocks and optional otherwise passage)
# - MOD-OUTPUT-REVIEW (shown alternatives and attributed items enter generation uses)
# - docs/gate.md
# :END_MODULE_CONTRACT
import copy
import re
from datetime import date


DETAIL = re.compile(
    r'\b(?:[12]\d{3}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|родил\w*|жив[еёу]\w*|прожива\w*|'
    r'лет|года|born|lives?|aged|years? old|urodzi\w*|mieszka\w*|lat|född\w*|bor|år gammal)\b', re.I)
RELATIVE = re.compile(
    r'\b(?:бабушк\w*|дедушк\w*|т[её]щ\w*|внук\w*|дочк\w*|дети|потомки|семь[яюеёи]|'
    r'grand(?:mother|father|children)|mother.in.law|children|daughter|'
    r'babci\w*|wnuk\w*|dzieci|córk\w*|barn(?:barn)?|dotter)\b', re.I)
YEAR = re.compile(r'\b(?:1\d{3}|20\d{2})\b')
AGE = re.compile(r'\b(?:лет|lat|old|gammal)\b', re.I)
PARAGRAPH = re.compile(r'\n\s*\n|\n(?=[-–•] )')
LIVES_IN = re.compile(r'\b(?:живут|прожива\w*|live in|mieszkaj\w*|bor i)\b', re.I)


def prose_review(instance, feed):
    """Find review candidates without deciding whom a sentence is about."""
    from familiar.checks.engine import _known_people, life_status, strings
    from .gate import shared
    from .subjects import protected_names

    known = _known_people(instance)
    match = shared(instance, 'public-protected-names', lambda: protected_names(instance, include_short=True))
    current_year = date.today().year

    def protected(ids):
        return any(life_status(known.get(pid, {'id': pid}), {}) != 'dead' for pid in ids)

    def reason(text, recent_chapter=False):
        if DETAIL.search(text):
            if match.search(text):
                return 'protected name near a date, age or place cue'
            if RELATIVE.search(text) and (AGE.search(text) or any(
                    int(year) >= current_year - 100 for year in YEAR.findall(text))):
                return 'kinship wording with a recent year or age cue'
            if recent_chapter and LIVES_IN.search(text):
                return 'place cue in a recent chapter'
        return None

    def paragraphs(value, field, recent_chapter=False):
        for lang, text in value.items() if isinstance(value, dict) else [(instance.source_language, value or '')]:
            for index, paragraph in enumerate(PARAGRAPH.split(text), 1):
                if why := reason(paragraph, recent_chapter):
                    yield f'{field} paragraph {index} ({lang}): {why}; name its people in prose and keep names and kinship in otherwise'

    for chapter in [feed, *feed.get('chapters', [])]:
        is_feed = chapter is feed
        fields = ('title', 'lead', 'period', 'line') if is_feed else ('title', 'text', 'more', 'ask', 'text_kids')
        where = feed['id'] if is_feed else f"{feed['id']}/{chapter['id']}"
        year = str(chapter.get('year', ''))
        recent_chapter = re.fullmatch(r'\d{4}', year) and int(year) >= current_year - 25
        for field in fields:
            if (blocks := chapter.get('_prose', {}).get(field)) is not None:
                for index, block in enumerate(blocks, 1):
                    if protected(block['people']):
                        yield where, f'{field} paragraph {index}: protected subjects; public uses only a permitted otherwise passage'
                continue
            if protected(chapter.get('people', [])):
                continue  # The existing chapter attribution already withholds the unsplit field.
            yield from ((where, note) for note in paragraphs(chapter.get(field), field, recent_chapter))
        if not is_feed:
            kids = chapter.get('kids', {})
            if 'text_kids' not in chapter.get('_prose', {}) and not protected(kids.get('_people', chapter.get('people', []))):
                yield from ((where, note + ' (use prose.text_kids)') for note in paragraphs(kids.get('text'), 'kids.text'))
            for field in ('places', 'facts'):
                for index, item in enumerate(chapter.get(field, []), 1):
                    if not protected(item.get('_people', chapter.get('people', []))):
                        if why := next(filter(None, map(reason, strings(item))), None):
                            yield where, f'{field} item {index}: {why}; attribute its people or keep only names and kinship'


def text_sources(value):
    sources = value.get('sources', [])
    if not isinstance(sources, list) or any(not isinstance(ref, str) or not ref for ref in sources):
        raise ValueError('Narrative sources must be a list of record or tree source IDs')
    return sources


def restrict_feed(instance, feed, *, host_private=False, withheld=lambda ref: False):
    from familiar.checks.engine import _known_people, life_status, load
    from familiar.reader.experiences import game_sources

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

    def show(block):
        return not restricted(block['people']) and (
            host_private or not any(map(withheld, text_sources(block))))

    def withhold_game(game):
        return not host_private and any(map(withheld, game_sources(game)))

    for chapter in [feed, *feed.get('chapters', [])]:
        defaults = chapter.get('people', [])
        nodes(chapter.get('tree', {}))
        for field in (('title', 'lead', 'period', 'line') if chapter is feed else ('title', 'text', 'more', 'ask', 'text_kids')):
            blocks = chapter.get('_prose', {}).get(field)
            if blocks is not None:
                shown = []
                for block in blocks:
                    if show(block):
                        shown.append(block['text'])
                        continue
                    alternative = block.get('otherwise')
                    if alternative and show(alternative):
                        shown.append(alternative['text'])
                if field == 'text' and len(shown) != len(blocks):
                    # Paragraph positions belonged to the complete story. The
                    # reader places the surviving papers after the shorter text.
                    chapter.pop('flow', None)
                chapter[field] = {lang: '\n\n'.join(
                    b.get(lang, '') for b in shown if b.get(lang, '').strip())
                    for lang in instance.languages}
                if field == 'text_kids' and chapter.get('kids'):
                    chapter['kids']['text'] = chapter[field]
            elif chapter.get(field) and restricted(defaults):
                chapter.pop(field)
        for field in ('facts', 'variants', 'places', 'extras', 'links', 'kids'):
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
        if (game := chapter.get('game')) and (
                restricted(game.get('_people', defaults)) or withhold_game(game)):
            chapter.pop('game')
        if flow := chapter.get('flow'):
            protected = restricted(defaults)
            for beat in flow:
                game = beat.get('do', {}).get('game', {})
                if protected or withhold_game(game):
                    beat.pop('do', None)
        # Authoring classification is not part of the reader's story.
        chapter.pop('kind', None)
    return feed
