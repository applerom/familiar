# START_MODULE_CONTRACT: MOD-ACCESS-LEDGER
# PURPOSE: Keep, per place of the family's lines, which papers exist, whether we have read them and how to reach them, so "no access" is never read as "not found".
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - read, unread, unreachable from home and unknown stay different states in every output [review: engine lead]
# - a verdict names its date and author; recording one changes only the named row [test: tests/research/test_coverage_ledger.py::test_access_ledger_steers_plan_and_check]
# - the claims check advises and never refuses [review: engine lead]
# - the Markdown beside the ledger is its print, renewed with every verdict and never a second ledger [test: tests/research/test_coverage_ledger.py::test_access_ledger_steers_plan_and_check]
# CHANGES_WITH:
# - MOD-RESEARCH-PLAN (the three states and the next step)
# - MOD-DESK-SEARCH-MAP (the family's page)
# - forms/access.json
# :END_MODULE_CONTRACT
"""The access ledger: place, kind of paper, years -> home, copy, room, letter, unknown, read or none."""
import json
import re
from datetime import date

from familiar.instance.gate import boundary

from .search_map import place_match, years_of

# Reachable first. `none` says there is nothing to read: the book is lost, or this holder has none.
# `copy`: the archive sells a copy remotely, ordered from a chair.
STATES = ('home', 'copy', 'room', 'letter', 'unknown', 'read', 'none')
UNREAD = {'home', 'copy', 'room', 'letter', 'unknown'}
MARKS_ORDER = ('read', 'home', 'copy', 'room', 'letter', 'unknown')  # as the family reads it: what we know first
# Somebody's later compilation: useful, never the books of the place.
SECONDARY = {'memorial-book', 'name-base', 'researcher', 'web'}
WORDED = ('title', 'holder', 'reference', 'online', 'unit', 'look_for', 'note', 'price', 'needs')
PRINT = '<!-- familiar: printed from access.json -->'
FIELDS = {'id', 'kind', 'years', 'state', 'read', 'of', 'letter', 'order', 'doubtful', 'at', 'by', 'report', *WORDED}
# Approaches that stand on the books themselves, and passes over name bases and other people's pages.
BOOK_PLAYS = {'place-nest', 'household-fingerprint', 'neighbors-godparents'}
BASE_PLAYS = {'surname-place', 'generation-events', 'cemeteries', 'forums'}


def worded(value):
    return isinstance(value, str) and bool(value.strip()) or isinstance(value, dict) and bool(value) and all(
        isinstance(v, str) and v.strip() for v in value.values())


def say(value, language='', texts=None, *, strict=False):
    """The words in a reader's language; strict leaves out words written only in another language."""
    if isinstance(value, dict):
        return value.get(language) or ('' if strict else next(iter(value.values()), ''))
    value = '' if value is None else str(value)
    return (texts or {}).get(value.strip()) or ('' if strict else value)


def validate(data):
    """Problems of a ledger as (place or row, message); an empty list is a valid file."""
    if not isinstance(data, dict) or not isinstance(data.get('places'), list):
        return [('access', 'expected {"places": [{"place", "lines", "books": [...]}]}; see research form access')]
    problems, seen = [], set()
    sections = data.get('sections', [])
    if not isinstance(sections, list) or any(not isinstance(s, dict) or not worded(s.get('title')) or not worded(s.get('about', '-'))
                                             for s in sections):
        problems.append(('sections', 'list of {title, about}; about is optional words'))
    for key in ('title', 'about', 'room'):
        if key in data and not worded(data[key]):
            problems.append((key, 'nonempty text or a row by language'))
    for n, place in enumerate(data['places']):
        if not isinstance(place, dict) or not isinstance(place.get('place'), str) or not place['place'].strip():
            problems.append((f'#{n}', 'place: the village or parish as the family writes it'))
            continue
        where, lines = place['place'], place.get('lines', [])
        for key, what in (('title', 'the place in the family\'s languages'), ('about', 'words about the place'),
                          ('section', 'the title of its section in the print')):
            if key in place and not worded(place[key]):
                problems.append((where, f'{key}: {what}'))
        if not isinstance(lines, list) or not all(isinstance(v, str) and v for v in lines):
            problems.append((where, 'lines: list of line surnames'))
        if not isinstance(place.get('books'), list):
            problems.append((where, 'books: list of rows'))
            continue
        for row in place['books']:
            if not isinstance(row, dict):
                problems.append((where, 'a book row is an object'))
                continue
            at = f"{where} {row.get('id') or '?'}"
            if not isinstance(row.get('id'), str) or not row['id'].strip() or row['id'] in seen:
                problems.append((at, 'id: unique short text'))
            else:
                seen.add(row['id'])
            if unknown := sorted(row.keys() - FIELDS):
                problems.append((at, f"unknown field {', '.join(unknown)}"))
            if not isinstance(row.get('kind'), str) or not row['kind'].strip():
                problems.append((at, 'kind: parish, revision, census, household, estate, civil ... or your own word'))
            if row.get('state') not in STATES:
                problems.append((at, f"state is one of {', '.join(STATES)}"))
            if row.get('years') not in (None, '') and not years_of(row['years']):
                problems.append((at, 'years: e.g. "1860-1918" or "1816; 1858"'))
            for key in WORDED:
                if key in row and not worded(row[key]):
                    problems.append((at, f'{key}: nonempty text or a row by language'))
            for key in ('read', 'of', 'order'):
                if key in row and (type(row[key]) is not int or row[key] < 0):
                    problems.append((at, f'{key}: a whole number'))
            try:
                date.fromisoformat(row.get('at'))
            except (TypeError, ValueError):
                problems.append((at, 'at: date of the verdict, YYYY-MM-DD'))
            if not isinstance(row.get('by'), str) or not row['by'].strip():
                problems.append((at, 'by: who gave the verdict'))
            if not isinstance(row.get('doubtful', False), bool):
                problems.append((at, 'doubtful: true when it is not sure that the book holds our place'))
            for key in ('report', 'letter'):
                if key in row and (not isinstance(row[key], str) or not row[key].strip()):
                    problems.append((at, f'{key}: nonempty text'))
    return problems


def read(instance):
    """(path, usable places, problems). No file is no problem: nothing is recorded yet."""
    path = instance.path('access')
    if not path.is_file():
        return path, [], []
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError, OSError) as exc:
        return path, [], [('access', f'unreadable: {exc}')]
    rows = data.get('places') if isinstance(data, dict) else None
    places = [dict(p, books=[r for r in p['books'] if isinstance(r, dict) and r.get('state') in STATES
                             and isinstance(r.get('kind'), str) and isinstance(r.get('order', 0), int)])
              for p in (rows if isinstance(rows, list) else [])
              if isinstance(p, dict) and isinstance(p.get('place'), str) and isinstance(p.get('books'), list)]
    return path, places, validate(data)


def primary(row):
    return row['kind'] not in SECONDARY


def unread(place):
    return [row for row in place['books'] if row['state'] in UNREAD and primary(row)]


def first_year(row):
    return min(years_of(row.get('years')) or {9999})


def in_order(rows):
    return sorted(rows, key=lambda r: (r.get('doubtful', False), STATES.index(r['state']), r.get('order', 10**6), first_year(r)))


def named(place, keys, language):
    from .coverage import surname_keys
    return any(surname_keys(name, language) & keys for name in place.get('lines') or [])


def line_places(data, places, line, members, extra=()):
    """Places of one planning line: those that name it; a place without `lines` by the line's people and versions."""
    from .research_plan import recorded_places
    from .search_map import leading_places
    if not places:
        return []
    known = [p for pid in line.chain for p in recorded_places(data['tree'].graph['people'][pid])]
    known += [p for p in [*leading_places(data, line, members), *extra] if p]
    return [place for place in places if (named(place, line.forms, data['language']) if place.get('lines') else
                                          any(place_match(place['place'], other) for other in known))]


CHURCH = re.compile(r'церк|костёл|костел|приход|храм|church|parish|chapel|kości|cerk|parafi|kyrk|församling|igreja|paróquia', re.I)


def names_parish(places):
    """The line's parish is known when its parish books name their church."""
    return any(row['kind'] == 'parish' and any(CHURCH.search(text) for key in ('title', 'holder', 'look_for')
               for text in (row[key].values() if isinstance(row.get(key), dict) else [row.get(key) or '']))
               for place in places for row in place['books'])


def answers_letters(places):
    return any(row['state'] == 'letter' and row.get('holder') for place in places for row in place['books'])


def reading_room(places):
    """What a visitor orders: rows waiting in a reading room, and unread rows the ledger gives an `order` there. A copy
    with an `order` joins: a visitor reads it for nothing, or finds the sheet numbers to order it by."""
    rows = [(place, row) for place in places for row in place['books']
            if row['state'] == 'room' or row['state'] in UNREAD and 'order' in row]
    return sorted(rows, key=lambda pair: pair[1].get('order', 10**6))  # equal places keep the ledger's own order


def copies(places):
    """What can be ordered from a chair: ready to order first, then rows that wait for a detail (sheet numbers)."""
    rows = [(place, row) for place in places for row in place['books'] if row['state'] == 'copy']
    return sorted(rows, key=lambda pair: ('needs' in pair[1], pair[1].get('doubtful', False), pair[1].get('order', 10**6)))


def title(row, words, language, texts=None, *, strict=False):
    name = say(row.get('title'), language, texts, strict=strict) or words['kinds'].get(row['kind'], row['kind'])
    years = row.get('years') or ''
    years = ', '.join(str(v) for v in years) if isinstance(years, list) else str(years)
    years = re.sub(r'(?<=\d)\s*-\s*(?=\d)', '–', years)
    return name[:1].upper() + name[1:] + (f' {years}' if years and years not in name else '')


def progress(row, words, language, texts=None):
    if 'read' not in row:
        return ''
    if 'of' not in row:
        return words['read_some'].format(read=row['read'], unit=say(row.get('unit'), language, texts)).strip()
    return words['read_of'].format(read=row['read'], of=row['of'], unit=say(row.get('unit'), language, texts)).strip()


def state_words(row, words, language):
    """One line a lead cannot misread: opens from home, no access from home, unknown where, read, nothing to read."""
    state, w = row['state'], words['plan']
    holder = say(row.get('holder'), language)
    if state in {'copy', 'room', 'letter'}:
        parts = [w[state].format(holder=holder or w['some'])]
    else:
        parts = [w[state], holder]
    if state == 'home':
        parts += [say(row.get('online'), language), progress(row, words, language) or (w['unread'] if primary(row) else '')]
    elif state == 'read' and (count := progress(row, words, language)):
        parts[0] = count
    parts.append(say(row.get('reference'), language))
    parts.append(say(row.get('price'), language))
    if row.get('needs'):
        parts.append(w['needs'].format(needs=say(row['needs'], language)))
    if row.get('letter'):
        parts.append(w['draft'].format(id=row['letter']))
    if row.get('doubtful'):
        parts.append(w['doubtful'])
    return ' · '.join(part for part in parts if part)


def words_for(instance, language=None):
    from familiar.desk.model import words
    return words(instance, language)['search_map']['books']


def plan_lines(places, words, language):
    """The books of the line's places, shown above its approaches."""
    out = []
    if not places:
        return [f"**{words['heading']}** · {words['plan']['nothing']}", '']
    for place in places:
        known = [r for r in place['books'] if primary(r) and r['state'] != 'none']
        tally = words['plan']['tally'].format(read=sum(r['state'] == 'read' for r in known), total=len(known))
        out += [f"**{words['heading']} · {place['place']}** · {tally}", '']
        out += [f"- {title(r, words, language)} — {state_words(r, words, language)} "
                f"({', '.join(v for v in (r.get('by'), r.get('at')) if v)})" for r in in_order(place['books'])]
        out.append('')
    return out


def closed_road(rows, words, language):
    """What to do about books that do not open from home: order them, write for them, find who keeps them."""
    w, parts = words['plan'], []

    def some(picked, limit):
        listed = []
        for row in picked[:limit]:
            where = ' '.join(v for v in (say(row.get('holder'), language), say(row.get('reference'), language)) if v)
            wanted = say(row.get('look_for'), language)
            listed.append(title(row, words, language) + (f' ({where})' if where else '') + (f' — {wanted}' if wanted else ''))
        if len(picked) > limit:
            listed.append(w['more'].format(n=len(picked) - limit))
        return '; '.join(listed)

    for state, key, limit in (('room', 'order', 3), ('letter', 'write', 2), ('unknown', 'find', 1)):
        picked = sorted((r for r in rows if r['state'] == state),
                        key=lambda r: (r.get('order', 10**6), 'letter' not in r, first_year(r)))
        if picked:
            parts.append(w[key].format(rows=some(picked, limit)))
    return ' '.join(parts)


def copy_step(rows, words, language):
    """Order a copy, with its price; where a detail is missing, find that out instead."""
    w, parts = words['plan'], []
    for key, picked in (('order_copy', [r for r in rows if 'needs' not in r]), ('find_out', [r for r in rows if 'needs' in r])):
        listed = []
        for row in picked[:3]:
            where = ', '.join(v for v in (' '.join(v for v in (say(row.get('holder'), language), say(row.get('reference'), language)) if v),
                                          say(row.get('price'), language)) if v)
            named = title(row, words, language) + (f' ({where})' if where else '')
            wanted = say(row.get('look_for'), language)
            listed.append(f"{say(row['needs'], language)} — {named}" if 'needs' in row else named + (f' — {wanted}' if wanted else ''))
        if len(picked) > 3:
            listed.append(w['more'].format(n=len(picked) - 3))
        if listed:
            parts.append(w[key].format(rows='; '.join(listed)))
    return ' '.join(parts)


def steer(line, places, record_map, words, language):
    """Let the ledger speak in a line's plan: a closed road is not "untried", and no pass over bases follows it."""
    line['access'] = [{'place': p['place'], 'unread': len(unread(p)), 'books': in_order(p['books'])} for p in places]
    rows = [row for place in places for row in unread(place)]
    if not rows:
        return
    home = in_order(row for row in rows if row['state'] == 'home' and not row.get('doubtful'))
    orderable = [row for _, row in copies(places) if primary(row) and not row.get('doubtful')]
    copying = copy_step(orderable, words, language)
    road = closed_road([row for row in rows if row['state'] not in {'home', 'copy'}], words, language)
    if not home and orderable and not (record_map and record_map['open_online_in_window']):
        current = next((p for p in line['plays'] if 'next' in p), None)
        for play in line['plays']:
            play.pop('next', None)
        if current and current['id'] not in BASE_PLAYS | {'archive-letters'}:
            line['meanwhile'] = current['step']
        line['next'] = copying
        if road:
            line['closed_road'] = road
    elif not home and not (record_map and record_map['open_online_in_window']):
        for play in line['plays']:
            if play['id'] in BOOK_PLAYS and play['state'] in {'untried', 'in-progress', 'exhausted'}:
                play['state_before_access'], play['state'] = play['state'], 'no-access'
                play['holders'] = list(dict.fromkeys(say(r['holder'], language) for r in in_order(rows) if r.get('holder')))
        current = next((p for p in line['plays'] if p['state'] in {'untried', 'in-progress'}), None)
        for play in line['plays']:
            play.pop('next', None)
        if current and current['id'] not in BASE_PLAYS | {'archive-letters'}:
            line['meanwhile'] = current['step']
        line['next'] = road
    else:
        if road:
            line['closed_road'] = road
        current = next((p for p in line['plays'] if 'next' in p), None)
        if home and not line.get('next') and (current is None or current['id'] in BASE_PLAYS | {'ask-family', 'archive-letters'}):
            if current and current['id'] == 'ask-family':
                line['meanwhile'] = current['step']
            if current:
                current.pop('next')
            line['next'] = words['plan']['read_home'].format(rows=title(home[0], words, language),
                                                             where=state_words(home[0], words, language))
        if copying:
            line['meanwhile'] = ' '.join(filter(None, [copying, line.get('meanwhile')]))


# The claims check: words that say a search is over, and words that say which books nobody has read yet.
OVER = re.compile(r'исчерпан|не найден[аоы]?\b|не нашл|бумаг нет|exhausted|not found|found nothing|wyczerpan|nie znalezion', re.I)
SAYS_UNREAD = re.compile(r'не ?(?:про)?чит|копи\w+ по заказу|order(?:ed)? (?:a )?cop|zamówi\w* kopi|читальн|\bзал[аеу]?\b|нет доступа|не открыва|неизвестно|unread|not (?:yet )?read|'
                         r'no access|reading.room|nie (?:prze)?czyt|czyteln', re.I)
ALL_LINES = re.compile(r'\bлини(?:я|и|й|ям|ях|ями)\b|\bрод(?:ы|ам|ов)\b|\b(?:all|the) lines\b|\blini(?:e|i|ach)\b', re.I)
MANY = 30  # journal rows of a line after which the ledger must know what its place holds


def stem(name):
    return re.split(r'[,(;]', name)[0].strip().casefold().replace('ё', 'е').rstrip('аеиоуыэюяйьaeiouy')


def mentions(text, stems):
    folded = text.casefold().replace('ё', 'е')
    return any(len(s) >= 4 and re.search(r'\b' + re.escape(s), folded) for s in stems)


def claim(text, context, stems, everyone):
    """The sentence that closes a search of these names (or of all lines) and does not say what stays unread."""
    if not OVER.search(text) or SAYS_UNREAD.search(text):
        return ''
    if not mentions(f'{context} {text}', stems) and (mentions(text, everyone) or not ALL_LINES.search(text)):
        return ''
    # A sentence with its own years names what was read; it closes that scope, not the line.
    return next((s.strip()[:140] for s in re.split(r'(?<=[.!?;])\s+', text)
                 if OVER.search(s) and not re.search(r'\b1[5-9]\d\d\b', s)), '')


def blocks(text):
    """(line number, heading, block): a table row, a list item or a paragraph under its nearest heading."""
    heading, out, held, start = '', [], [], 1
    for n, raw in enumerate([*text.splitlines(), ''], 1):
        line = raw.strip()
        if held and (not line or line.startswith(('#', '|', '- ', '* ')) or re.match(r'\d+[а-яa-z]?\. ', line)):
            out.append((start, heading, ' '.join(held)))
            held = []
        if line.startswith('#'):
            heading = line.lstrip('# ')
        elif line:
            start = start if held else n
            held.append(line)
    return out


def check(instance, versions_rows, searches, chosen, fail):
    """Advice only: a malformed ledger, "exhausted" over unread books, and long searches that never asked about them."""
    from .coverage import surname_keys
    path, places, problems = read(instance)
    language = instance.source_language
    if chosen(path):
        for where, message in problems:
            fail(path, f'access ledger {where}: {message}')
    page = print_path(instance)
    if places and not problems and chosen(page) and page.is_file():
        kept = page.read_text(encoding='utf-8-sig')
        if PRINT not in kept:
            fail(page, 'kept by hand beside access.json: two ledgers drift apart. Bring its words into the ledger (research access note), '
                 'move the file away and print it (research access --markdown --save)')
        elif kept.replace('\r\n', '\n') != printed(instance, json.loads(path.read_text(encoding='utf-8-sig'))):
            fail(page, 'the print is behind access.json, or was edited by hand: research access --markdown --save')
    waiting = [p for p in places if unread(p)]
    names = {p['place']: {stem(v) for v in (p['place'], *(p.get('lines') or []))} for p in places}
    everyone = set().union(*names.values()) if names else set()
    words = words_for(instance) if waiting else None

    def hint(where, quote, held):
        rows = [f"{p['place']} {len(unread(p))}" for p in held]
        first = in_order(unread(held[0]))[0]
        fail(where, f'"{quote}" — but kinds of books unread: {", ".join(rows)} (first: {title(first, words, language)} — '
             f'{state_words(first, words, language)}); name the kind of source that ran out and say beside it what is unread '
             '(familiar research access)')

    line_of, options = {}, {}
    for where, row in versions_rows:
        line = row.get('line') if isinstance(row.get('line'), str) else ''
        line_of[row.get('id')] = line
        stood = [v['place'] for v in row.get('versions') or [] if isinstance(v, dict) and isinstance(v.get('place'), str)]
        options.setdefault(line, []).extend(stood)
        if not chosen(where) or row.get('status') in {'closed', 'rejected', 'disproved'}:
            continue
        keys = surname_keys(line, language)
        for place in waiting:
            if named(place, keys, language) or any(place_match(place['place'], other) for other in stood):
                from familiar.checks.engine import strings
                if quote := next((q for text in strings(row) if (q := claim(text, '', names[place['place']], everyone))), ''):
                    hint(where, quote, [place])
                    break
    desk = instance.config.get('desk', {}).get('plan')
    files = [*sorted((instance.root / 'research').glob('*.md')), *([instance._inside(desk)] if isinstance(desk, str) else [])]
    for file in files if waiting else ():
        if not file.is_file() or not chosen(file):
            continue
        said = set()
        for n, heading, block in blocks(file.read_text(encoding='utf-8-sig')):
            held, quote = [], ''
            for place in waiting:
                if place['place'] not in said and (found := claim(block, heading, names[place['place']], everyone)):
                    said.add(place['place'])
                    held.append(place)
                    quote = found
            if held:
                hint(f'{file}:{n}', quote, held)
    counts = {}
    for _, row in searches:
        if isinstance(row, dict) and (line := line_of.get(row.get('question'))):
            counts[line] = counts.get(line, 0) + 1
    silent = [f'{line} ({n})' for line, n in sorted(counts.items(), key=lambda item: -item[1]) if n >= MANY and not any(
        named(p, surname_keys(line, language), language) or any(place_match(p['place'], other) for other in options[line])
        for p in places)]
    if silent and chosen(path):
        fail(path, 'many journal rows and no row of the access ledger for the place of the line: ' + ', '.join(silent)
             + '; record which books of the place exist and whether they open (familiar research access record)')


@boundary('transaction')
def record(instance, place, values, *, identity=None, lines=()):
    """Add a verdict, or change only the given fields of an existing row. Empty text removes a field."""
    from familiar.instance.writer import access_verdict
    written = {}

    def change(data):
        data = {'schema_version': 1, 'places': []} if data is None else data
        if problems := validate(data):
            raise ValueError(f'{problems[0][0]}: {problems[0][1]}')
        rows = {row['id']: (entry, row) for entry in data['places'] for row in entry['books']}
        if identity:
            if identity not in rows:
                raise ValueError(f'no row {identity}; list the rows with research access')
            entry, row = rows[identity]
        elif not place:
            raise ValueError('name the place (--place), or the row to change (--id)')
        else:
            entry = next((p for p in data['places'] if place_match(p['place'], place)), None)
            if entry is None:
                entry = {'place': place, 'books': []}
                data['places'].append(entry)
            row = next((r for r in entry['books'] if r['kind'] == values.get('kind')
                        and years_of(r.get('years')) == years_of(values.get('years'))
                        and all(values.get(k) in (None, r.get(k)) for k in ('holder', 'reference'))), None)
            if row is None:
                number = max((int(m[1]) for i in rows if (m := re.fullmatch(r'a(\d+)', i))), default=0) + 1
                row = {'id': f'a{number}'}
                entry['books'].append(row)
        if lines:
            entry['lines'] = list(dict.fromkeys([*entry.get('lines', []), *lines]))
        row.update({k: v for k, v in values.items() if v is not None})
        for key in [k for k, v in row.items() if v == '']:
            row.pop(key)
        if problems := validate(data):
            raise ValueError(f'{problems[0][0]}: {problems[0][1]}')
        written.update(row)
        return data

    access_verdict(instance, change, lambda data: printed(instance, data))
    return written


@boundary('transaction')
def note(instance, text=None, *, place=None, section=None, room=False, title=None):
    """The words around the rows: the header, a section, a place or the reading-room list. Empty text removes them."""
    from familiar.instance.writer import access_verdict

    def change(data):
        data = {'schema_version': 1, 'places': []} if data is None else data
        if place:
            target, key = next((p for p in data['places'] if place_match(p['place'], place)), None), 'about'
            if target is None:
                raise ValueError(f'no place {place} in the ledger; record its first row with research access record')
            if section:
                target['section'] = section
        elif section:
            target, key = next((s for s in data.get('sections', []) if s['title'] == section), None), 'about'
            if target is None:
                target = {'title': section}
                data.setdefault('sections', []).append(target)
        else:
            target, key = data, 'room' if room else 'about'
        if title:
            target['title'] = title
        if text is not None:
            target[key] = text
            if text == '':
                target.pop(key)
        if problems := validate(data):
            raise ValueError(f'{problems[0][0]}: {problems[0][1]}')
        return data

    access_verdict(instance, change, lambda data: printed(instance, data))


def print_path(instance):
    path = instance.path('access')
    return path.with_name(path.stem.upper() + '.md')


def printed(instance, data):
    """The whole ledger as one Markdown page for the research, in the family's main language."""
    language, words = instance.source_language, words_for(instance)
    p, places = words.get('print') or words_for(instance, 'en')['print'], data['places']
    listed = {row['id']: row for _, row in reading_room(places)}
    cell = lambda parts, sep=' · ': sep.join(v for v in parts if v).replace('|', '/').replace('\n', ' ')

    def verdict(row):
        report = row.get('report', '')
        shown = report.removeprefix('research/') if report.startswith('research/') else '../' + report
        return cell([row.get('by'), row.get('at')], ', ') + (f" · [{p['report']}]({shown})" if report else '')

    def state(row):
        count, done = progress(row, words, language), row['state'] == 'read'
        words_of = [f"**{count or p['read']}**" if done else p[row['state']], '' if done else count,
                    say(row.get('price'), language), p['needs'].format(needs=say(row['needs'], language)) if row.get('needs') else '',
                    words['plan']['draft'].format(id=row['letter']) if row.get('letter') else '',
                    words['plan']['doubtful'] if row.get('doubtful') else '', say(row.get('note'), language),
                    p['sought'].format(what=say(row['look_for'], language)) if row.get('look_for') and row['id'] not in listed else '']
        return cell(words_of)

    out = [f"# {say(data.get('title'), language) or words['heading']}", '', f"{PRINT} {p['made']}", '']
    if data.get('about'):
        out += [say(data['about'], language), '']
    sections = [s['title'] for s in data.get('sections', [])]
    groups = [(s, [q for q in places if q.get('section') == s['title']]) for s in data.get('sections', [])]
    groups.append((None, [q for q in places if q.get('section') not in sections]))
    for section, held in groups:
        if section:
            out += [f"## {say(section['title'], language)}", '']
            if section.get('about'):
                out += [say(section['about'], language), '']
        for place in held:
            out += [f"### {say(place.get('title'), language) or place['place']}"
                    + (f" — {', '.join(place['lines'])}" if place.get('lines') else ''), '']
            if place.get('about'):
                out += [say(place['about'], language), '']
            out += ['| ' + ' | '.join(p[k] for k in ('row', 'paper', 'where', 'state', 'verdict')) + ' |', '|---|---|---|---|---|']
            out += [f"| {row['id']} | {cell([title(row, words, language)])} | "
                    f"{cell([say(row.get(k), language) for k in ('holder', 'reference', 'online')])} | {state(row)} | {verdict(row)} |"
                    for row in place['books']]
            out.append('')
    if rows := copies(places):
        out += [f"## {words['copy_title']}", '']
        out += [f"- [{r['id']}] {cell([say(q.get('title'), language) or q['place'], title(r, words, language)])} — "
                f"{state_words(r, words, language)}" + (f". {say(r['look_for'], language)}" if r.get('look_for') else '') for q, r in rows]
        out.append('')
    if rows := reading_room(places):
        out += [f"## {words['order_title']}", '']
        if data.get('room'):
            out += [say(data['room'], language), '']
        archives = {}
        for q, r in rows:
            archives.setdefault(say(r.get('holder'), language) or words['order_any'], []).append(
                f"**{say(r.get('reference'), language) or '?'}** — "
                + cell([say(q.get('title'), language) or q['place'], title(r, words, language)])
                + (f": {say(r['look_for'], language)}" if r.get('look_for') else '') + f" [{r['id']}]")
        for holder, lines in archives.items():
            out += [f'**{holder}**', '', *(f'{n}. {line}' for n, line in enumerate(lines, 1)), '']
    return '\n'.join(out).rstrip() + '\n'


@boundary('transaction')
def save_print(instance):
    """Write the print beside the ledger; a page somebody keeps by hand is never overwritten."""
    from familiar.instance.writer import access_verdict
    path = print_path(instance)
    if path.is_file() and PRINT not in path.read_text(encoding='utf-8-sig'):
        raise ValueError(f'{path.name} is kept by hand: bring its words into the ledger (research access record, research access note), '
                         'move the file away, then print')
    access_verdict(instance, lambda data: data if data else {'schema_version': 1, 'places': []},
                   lambda data: printed(instance, data), first=True)
    return path


@boundary('diagnostic')
def show(instance, *, line=None, place=None, order=False):
    from .coverage import surname_keys
    language = instance.source_language
    _, places, problems = read(instance)
    if line:
        places = [p for p in places if named(p, surname_keys(line, language), language)]
    if place:
        places = [p for p in places if place_match(p['place'], place)]
    words = words_for(instance)
    wanted, orderable = reading_room(places), copies(places)
    view = {'schema': 1, 'places': places, 'order': [dict(r, place=p['place']) for p, r in wanted],
            'copies': [dict(r, place=p['place']) for p, r in orderable],
            'problems': [{'where': w, 'message': m} for w, m in problems]}
    out = [*(f'- {w}: {m}' for w, m in problems)]
    if order and orderable:
        out += [f"# {words['copy_title']}", '', *(f"- [{r['id']}] {p['place']} · {title(r, words, language)} — {state_words(r, words, language)}"
                for p, r in orderable), '']
    out[:0] = [] if order else [f"# {words['heading']}", '']
    if order:
        out += [f"# {words['order_title']}", '']
    for p, r in wanted if order else ():
        parts = [say(r.get('holder'), language), say(r.get('reference'), language), p['place'], title(r, words, language)]
        out.append(f"- [{r['id']}] " + ' · '.join(v for v in parts if v)
                   + (f" — {say(r['look_for'], language)}" if r.get('look_for') else ''))
    if not order and not places:
        out.append(words['plan']['nothing'])
    for p in () if order else places:
        out += [f"## {p['place']}" + (f" · {', '.join(p['lines'])}" if p.get('lines') else ''), '']
        out += [f"- [{r['id']}] {title(r, words, language)} — {state_words(r, words, language)} "
                f"({', '.join(v for v in (r.get('by'), r.get('at'), r.get('report')) if v)})"
                + (f". {say(r['note'], language)}" if r.get('note') else '') for r in in_order(p['books'])]
        out.append('')
    return view, '\n'.join(out)
