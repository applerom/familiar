"""Build the family-only conversation page and reader links from ranked asks."""
import json
import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from html import escape

from familiar.instance import blanks
from familiar.instance.asks import (VISIBLE, WANTS, closed_line, context, current, horizons, latest_feedback, row_lines,
                                    validate, waiting)
from familiar.instance.correspondence import aim_versions
from familiar.instance.correspondence_view import rank
from familiar.instance.host_language import HostData
from familiar.instance.memory_visibility import require_displayable
from familiar.research.coverage import surname_keys

from .pages import page


def link(identity):
    return '/desk/asks.html#ask-' + identity


def years(person):
    """Tree-tile years: recorded birth/death years, else the guessed birth year."""
    def year(value):
        found = re.search(r'\b(\d{4})\b', value) if isinstance(value, str) else None
        return found[1] if found else ''

    shown = person.get('cardPresentation') or {}
    events = person.get('events', [])
    pick = lambda kinds: next((e.get('date') for e in events if e.get('type') in kinds and e.get('date')), '')
    born, died = year(shown.get('birth') or pick({'birth', 'BIRT'})), year(shown.get('death') or pick({'death', 'DEAT'}))
    if not born and (person.get('birthGuess') or {}).get('year'):
        born = '\u2248' + str(person['birthGuess']['year'])
    return born + ('\u2013' + died if died else '')


def exact_day(raw):
    """The day an ISO or imported date names, or None."""
    try:
        return date.fromisoformat(raw)
    except ValueError:
        parts = raw.upper().split()
        try:
            return date(int(parts[2]), 'JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split().index(parts[1]) + 1,
                        int(parts[0])) if len(parts) == 3 else None
        except ValueError:
            return None


def birthday(person, today, w, name=''):
    for event in person.get('events', []):
        raw = event.get('date', '')
        if (event.get('type') != 'birth' or event.get('open_question') or not isinstance(raw, str)
                or event.get('status') in {'possible', 'hypothesis', 'candidate'}):
            continue
        born = exact_day(raw)
        if born is None or born > today:
            continue
        for year in (today.year, today.year + 1):
            try:
                upcoming = born.replace(year=year)
            except ValueError:
                upcoming = date(year, 2, 28)
            if today <= upcoming <= today + timedelta(days=14):
                # No age and no "turns": the family may not have told us everything.
                return w['birthday'].format(day=upcoming.day, month=w['months'][upcoming.month - 1], name=name)
    return ''


def matching_steps(row, subjects, graph, data):
    def pattern(value):
        return re.compile(r'(?<!\w)' + re.escape(value.casefold()) + r'(?!\w)') if value else None

    language = data.instance.source_language
    about, aim = row['about'], row['aim']
    line_name = about.get('line') or aim.get('line')
    line = surname_keys(line_name, language)
    line_pattern, place_pattern = pattern(line_name), pattern(about.get('place'))
    aliases = graph.get('identityAliases', {})
    primary = about.get('person')
    targets = {aliases.get(primary, primary)} if primary else subjects
    for feed in graph.get('feeds', []):
        chapters = feed.get('chapters', [])
        if not chapters:
            continue
        same_line = bool(line & surname_keys(feed.get('line'), language))
        related = same_line
        for index, chapter in enumerate(chapters, 1):
            named = {aliases.get(pid, pid) for pid in [chapter.get('person'), *chapter.get('people', [])] if pid}
            if targets & named:
                yield feed['id'], str(index)
                break
            if line_pattern or place_pattern:
                fragments = [chapter.get(k) for k in ('title', 'text', 'more')]
                fragments.extend(p.get('name') for p in chapter.get('places', []))
                message = '\n'.join(data.text(value).casefold() for value in fragments if value)
                related = related or any(p and p.search(message) for p in (line_pattern, place_pattern))
        else:
            if related:
                yield feed['id'], 'end'


def subjects_for(row, aliases):
    about, aim = row['about'], row['aim']
    subjects = list(aim.get('people', []))
    if about.get('person'):
        subjects.append(about['person'])
    return {aliases.get(pid, pid) for pid in subjects}


def project(active, graph, delivery, w, *, today=None, feedback=(), language=None, texts=None):
    from .model import listing

    today = today or date.today()
    week_ago = datetime.now(UTC) - timedelta(days=7)
    words_blanks, w = w['blanks'], w['asks']
    root = active.path('asks')
    paths, names = listing(root, '**/*.json')
    inputs = {p: p.read_bytes() for p in paths}
    listings = {(root, '**/*.json'): names}
    horizon_path = active.path('horizons')
    if horizon_path.is_file():
        inputs[horizon_path] = horizon_path.read_bytes()
    closed = horizons(active, inputs.get(horizon_path))
    data = HostData(active)
    # Another reader language: the same conversation with card translations and reader-language names.
    language, texts = language or active.source_language, texts or {}
    def tr(value):
        return texts.get(value.strip(), value) if isinstance(value, str) and value.strip() else value
    def local_name(pid, fallback):
        shown = (graph.get('people', {}).get(pid) or {}).get('namePresentation') or {}
        form = (shown.get('byLanguage') or {}).get(language)
        return form if language != active.source_language and isinstance(form, str) and form.strip() else fallback
    versions = aim_versions(data.rows['versions'])
    people = data.people
    aliases = graph.get('identityAliases', {})
    live = {pid: data.name(pid) for pid in graph.get('people', {})
            if people.get(pid, {}).get('life_assessment', {}).get('status') == 'living'}
    heard = list(feedback)
    feedback = latest_feedback(heard)
    entries, found_by_child, stale, seen, placed = [], [], set(), set(), []
    for path, raw in inputs.items():
        if path == horizon_path:
            continue
        row = json.loads(raw)
        validate(row, people, versions)
        identity = row['id']
        if identity in seen:
            raise ValueError('Duplicate ask ID: ' + identity)
        seen.add(identity)
        response = feedback.get(identity)
        state, last, expired = current(row, response)
        placed.append(row | {'state': state})
        if (state == 'answered' and last and response[2].get('kind') == 'ask_answer'
                and response[2].get('via_child') and not row.get('tender')):
            found_by_child.append(row)
        if state not in VISIBLE and not state.startswith('will_ask:'):
            continue
        if waiting(state) and closed_line(active, row_lines(row), closed):
            continue  # the family said nobody is left to ask on this line: no page, card or feed prompt
        if expired:
            stale.add(identity)
        aim, about = row['aim'], row['about']
        subjects = aim.get('people', [])
        holder = row['holder']
        if isinstance(holder, str):
            holder = aliases.get(holder, holder)
            name = local_name(holder, live.get(holder) or data.name(holder))
        else:
            name = data.text(holder.get('label')) or w['elders'].format(line=data.text(holder.get('line')))
            holder = 'group:' + name
        opener = row.get('opener')
        asset = None
        if isinstance(opener, dict) and 'text' in opener:
            source = opener.get('asset') or graph.get('sources', {}).get(opener.get('record'), {}).get('asset')
            if isinstance(source, str) and source.startswith('/') and source[1:] in delivery:
                asset = source
            opener = opener['text']
        person = aliases.get(about.get('person'), about.get('person'))
        shown = graph.get('people', {}).get(person) if person else None
        tile = ({'person': person, 'name': local_name(person, shown.get('treeName') or data.name(person)), 'years': years(shown)} if shown
                else {'person': '', 'name': data.name(person) if person else tr(data.text(about.get('line') or about.get('place'))),
                      'years': tr(data.text(about.get('place'))) if about.get('line') and not person else ''})
        item = {'id': identity, 'holder': holder, 'name': name, 'tile': tile,
                'question': tr(data.text(row['question'], subjects)), 'child': tr(data.text(row.get('question_child'), subjects)),
                'opener': tr(data.text(opener, subjects)), 'asset': asset,
                'hints': [tr(s) for h in row.get('hints', []) if (s := data.text(h, subjects))],
                'wants': [k for k in WANTS if k in row.get('wants', [])], 'tender': bool(row.get('tender')),
                'photo_note': tr(data.text(row.get('photo_note'), subjects)), 'next_hint': tr(data.text(row.get('next_hint'), subjects)),
                'occasion': tr(data.text(row.get('occasion'), subjects)), 'context': context(row), 'state': state,
                'eligible': last is None or last <= week_ago,
                'line': tr(data.text(aim.get('line') or about.get('line'))), 'settles': tr(data.text(aim.get('settles'), subjects)),
                'score': 0, 'cost': 'free', 'shelved': False, 'relevance': ''}
        if item['question'] and item['name']:
            entries.append((row, item))
    rank(active, data, entries, versions, {'settled': '{what}', 'settled_unknown': ''}, stale_asks=stale)
    ranked = sorted(((r, i) for r, i in entries if not i['shelved']), key=lambda pair: (-pair[1]['score'], pair[1]['id']))
    groups, cards, steps = defaultdict(list), defaultdict(list), defaultdict(lambda: defaultdict(list))
    reminders = []
    for row, item in ranked:
        holder = item['holder']
        groups[holder].append(item)
        if item['state'] not in VISIBLE:
            continue
        if item['eligible']:
            occasion = item['occasion'] or birthday(people.get(holder, {}), today, w, item['name'])
            if occasion:
                reminders.append({'id': item['id'], 'name': item['name'], 'question': item['question'],
                                  'holder': holder, 'child': item['child'],
                                  'occasion': occasion, 'birthday': not bool(item['occasion'])})
        entry = {'id': item['id'], 'text': w['prompt'].format(holder=item['name'], question=item['question']),
                 'child': item['child']}
        subject_ids = subjects_for(row, aliases)
        for pid in sorted(subject_ids & graph.get('people', {}).keys()):
            cards[pid].append(entry | {'own_question': item['question']} if pid == holder else entry)
        for feed, index in matching_steps(row, subject_ids, graph, data):
            steps[feed][index].append(entry)
    child_steps = defaultdict(set)
    for row in found_by_child:
        for feed, index in matching_steps(row, subjects_for(row, aliases), graph, data):
            child_steps[feed].add(index)
    summaries = [{'id': item['id'], 'text': item['question'], 'holder': item['name'],
                  'lane': (row['aim'].get('version') or '')} for row, item in ranked if item['state'] in VISIBLE][:3]
    links = {'cards': dict(cards), 'steps': dict(steps), 'child_steps': {k: sorted(v) for k, v in child_steps.items()}}
    if graph.get('people'):
        links['blanks'] = invitations(active, graph, data, placed, heard, words_blanks, w['months'], language, tr, local_name)
        paths, names = listing(active.path('versions'), '**/*.json')
        inputs.update({p: p.read_bytes() for p in paths})
        listings[(active.path('versions'), '**/*.json')] = names
    require_displayable(active, [list(groups.values()), reminders, links])
    return render(language, groups, w, faces(graph, groups)), links, reminders, summaries, inputs, listings


def faces(graph, groups):
    """{holder: CSS} for the family's own photograph of each person we ask, the marked face first."""
    found = {}
    for holder in groups:
        media = [m for m in (graph.get('people', {}).get(holder) or {}).get('media', [])
                 if m.get('photo') and m.get('kind') == 'family-photograph' and str(m.get('asset', '')).startswith('/')]
        media.sort(key=lambda m: (not (m.get('is_portrait') or m.get('face')), len(m.get('subjects') or [1])))
        if not media:
            continue
        m = media[0]
        x, y, w, h = m.get('face') or m.get('crop') or (0, 0, 1, 1)
        place = (f'background-size:{100 / w:.2f}% {100 / h:.2f}%;background-position:'
                 f'{x / (1 - w) * 100 if w < 1 else 50:.2f}% {y / (1 - h) * 100 if h < 1 else 30:.2f}%'
                 if m.get('face') or m.get('crop') else 'background-size:cover;background-position:50% 30%')
        found[holder] = f"background-image:url('{escape(m['asset'])}');{place}"
    return found


def invitations(active, graph, data, asks, feedback, w, months, language, tr, local_name):
    """{person: slots}: what a thin card lacks, and what we propose to amend, each one tap from the remark form."""
    family = blanks.Family(active, graph, living={
        data.people[pid]['id'] for pid in graph['people']
        if data.people.get(pid, {}).get('life_assessment', {}).get('status') == 'living'})
    from familiar.instance.subjects import protected_names
    deceased = {pid for pid, person in graph['people'].items() if person.get('living') is False}
    names = protected_names(active)
    result = defaultdict(list)

    def slot(pid, field, subject, **more):
        label = w['field_' + field + ('_' + (family.sex(pid) or 'm') if field == 'spouse' else '')]
        name = local_name(pid, graph['people'][pid].get('treeName') or graph['people'][pid].get('name', ''))
        values = {'person': name, 'field': label, 'value': more.get('guess', '')}
        result[pid].append({'label': label, 'subject': subject, 'start': w['start'].format(**values), **more,
                            **({'yes': w['yes_text'].format(**values)} if more.get('guess') else {})})

    def told(value, field, pid):
        shown = text(value, pid)
        if field in {'birth', 'death'} and (day := exact_day(shown)):
            return f"{day.day} {months[day.month - 1]} {day.year}"
        return shown

    def text(value, pid):
        return value.get(language) or tr(data.text(value, [pid])) if isinstance(value, dict) else tr(data.text(value, [pid]))

    for pid, person in graph['people'].items():
        for row in person.get('amendments', []) if pid in deceased and family.askable(pid) else ():
            if row['state'] == 'proposed' and row['weight'] >= blanks.GUESS_FROM:
                guess, original = told(row['value'], row['field'], pid), text(row['original'], pid)
                if not names.search(guess) and not names.search(original):
                    slot(pid, row['field'], 'amendment:' + row['id'], guess=guess,
                         told=w['told' if row['origin'] == 'memory' else 'read'].format(value=original),
                         amendment_revision=row['revision'])
    for pid, items in blanks.offers(family, data.rows['versions'], feedback, asks).items():
        for item in items:
            guess = (item.get('guess') or {}) if pid in deceased else {}
            value = local_name(guess['person'], guess['value']) if guess.get('person') else told(guess['value'], item['field'], pid) if guess else ''
            if not guess.get('person') and names.search(value):
                value, guess = '', {}
            slot(pid, item['field'], f"blank:{pid}:{item['field']}",
                 **({'guess': value} if value else {}), **({'version': guess['version']} if guess.get('version') else {}))
    return {pid: items for pid, items in result.items() if items}


def render(language, groups, w, portraits=None):
    """A conversation, not a form: what we think, then one field for how it really was."""
    def label(key):
        return escape(w[key])

    def tile(about):
        inner = f'<b>{escape(about["name"])}</b>' + (f'<small>{escape(about["years"])}</small>' if about['years'] else '')
        if about['person']:
            return f'<a class="ask-who" href="/#person={escape(about["person"])}">{inner}</a>'
        return f'<span class="ask-who">{inner}</span>'

    def card(item, first=False):
        hints = ''.join(f'<button type="button" class="ask-hint" data-hint="{escape(hint)}">{escape(hint)}</button>'
                        for hint in item['hints'])
        opener = escape(item['opener'])
        if item['asset']:
            opener += f' <a href="{escape(item["asset"])}">{label("show_opener")}</a>'
        opener = f'<p class="ask-opener">{opener}</p>' if opener else ''
        tender = f'<p class="ask-tender">{label("tender_notice")}</p>' if item['tender'] else ''
        child = f'<span class="ask-child" hidden>{escape(item["child"])}</span>' if item['child'] else ''
        photo = ('<p class="ask-photo">' + escape(item['photo_note']) + '</p>'
                 if 'photo' in item['wants'] and item['photo_note'] else '')
        mark = ' data-tender="true"' if item['tender'] else ''
        status = label('saved_will_ask') if item['state'].startswith('will_ask:') else ''
        return (f'<details id="ask-{escape(item["id"])}" class="ask-card{" ask-first" if first else ""}" data-ask="{escape(item["id"])}" '
                f'data-context="{item["context"]}"{mark}><summary>{tile(item["tile"])}'
                f'<span class="ask-q"><span class="ask-adult">{escape(item["question"])}</span>{child}</span></summary>'
                f'<div class="ask-body">{opener}' + (f'<div class="ask-hints">{hints}</div>' if hints else '') + tender
                + f'<form class="ask-answer"><label>{label("write")}<textarea required maxlength="6000" rows="3"></textarea></label>'
                + photo + f'<div class="ask-send"><button type="submit" class="ask-primary">{label("send")}</button></div></form>'
                + f'<p class="ask-status" role="status">{status}</p></div></details>')

    sections = []
    for items in groups.values():
        lines = ' · '.join(escape(line) for line in dict.fromkeys(i['line'] for i in items) if line)
        # One person, one card: whom to ask before what to ask; the first question large, the others folded.
        face = (portraits or {}).get(items[0]['holder'])
        avatar = (f'<span class="ask-face" style="{face}" aria-hidden="true"></span>' if face
                  else f'<span aria-hidden="true">{escape(items[0]["name"][:1])}</span>')
        rest = items[1:]
        more = (f'<details class="ask-more"><summary>{escape(w["more_questions"].format(n=len(rest)))}</summary>'
                + ''.join(card(item) for item in rest) + '</details>') if rest else ''
        sections.append(f'<section class="ask-holder"><header>{avatar}'
                        f'<div><h2>{escape(items[0]["name"])}</h2>' + (f'<small>{lines}</small>' if lines else '')
                        + '</div></header>' + card(items[0], True) + more + '</section>')
    content = (f'<div class="ask-page"><p class="ask-lead">{label("lead")}</p><p class="ask-today" hidden></p>'
               f'<div class="ask-modes" hidden><button type="button" data-action="kids" aria-pressed="false">{label("kids")}</button></div>'
               + (''.join(sections) if sections else f'<p class="ask-empty">{label("empty")}</p>') + '</div>')
    return page(w['title'], content, language)
