"""Build the family-only conversation page and reader links from ranked asks."""
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from html import escape

from familiar.instance.asks import VISIBLE, WANTS, context, current, latest_feedback, validate
from familiar.instance.correspondence import aim_versions
from familiar.instance.correspondence_view import rank
from familiar.instance.host_language import HostData
from familiar.instance.memory_visibility import require_displayable
from familiar.research.coverage import surname_keys

from .pages import page


def link(identity):
    return '/desk/asks.html#ask-' + identity


def question_count(w, count):
    singular = count == 1 if w.get('singular_one_only') else count % 10 == 1 and count % 100 != 11
    if singular:
        unit = w['question_one']
    elif count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        unit = w['question_few']
    else:
        unit = w['question_many']
    return f'{count} {unit}'


def birthday(person, today, w):
    for event in person.get('events', []):
        raw = event.get('date', '')
        if (event.get('type') != 'birth' or event.get('open_question') or not isinstance(raw, str)
                or event.get('status') in {'possible', 'hypothesis', 'candidate'}):
            continue
        try:
            born = date.fromisoformat(raw)
        except ValueError:
            try:
                parts = raw.upper().split()
                months = 'JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split()
                born = date(int(parts[2]), months.index(parts[1]) + 1, int(parts[0])) if len(parts) == 3 else None
            except (ValueError, IndexError):
                continue
            if born is None:
                continue
        if born > today:
            continue
        for year in (today.year, today.year + 1):
            try:
                upcoming = born.replace(year=year)
            except ValueError:
                upcoming = date(year, 2, 28)
            if today <= upcoming <= today + timedelta(days=14):
                return w['birthday'].format(day=upcoming.day, month=w['months'][upcoming.month - 1],
                                            age=year - born.year)
    return ''


def matching_steps(about, subjects, graph, data):
    def pattern(value):
        return re.compile(r'(?<!\w)' + re.escape(value.casefold()) + r'(?!\w)') if value else None

    language = data.instance.source_language
    line = surname_keys(about.get('line'), language)
    line_pattern, place_pattern = pattern(about.get('line')), pattern(about.get('place'))
    aliases = graph.get('identityAliases', {})
    for feed in graph.get('feeds', []):
        same_line = bool(line & surname_keys(feed.get('line'), language))
        for index, chapter in enumerate(feed.get('chapters', []), 1):
            named = {aliases.get(pid, pid) for pid in chapter.get('people', [])}
            if same_line or subjects & named:
                yield feed['id'], str(index)
                continue
            if line_pattern or place_pattern:
                fragments = [chapter.get(k) for k in ('title', 'text', 'more')]
                fragments.extend(p.get('name') for p in chapter.get('places', []))
                message = '\n'.join(data.text(value).casefold() for value in fragments if value)
                if any(p and p.search(message) for p in (line_pattern, place_pattern)):
                    yield feed['id'], str(index)


def subjects_for(row, aliases):
    about, aim = row['about'], row['aim']
    subjects = list(aim.get('people', []))
    if about.get('person'):
        subjects.append(about['person'])
    return {aliases.get(pid, pid) for pid in subjects}


def project(active, graph, delivery, w, *, today=None, feedback=()):
    from .model import listing

    today = today or date.today()
    week_ago = datetime.now(UTC) - timedelta(days=7)
    w = w['asks']
    root = active.path('asks')
    paths, names = listing(root, '**/*.json')
    inputs = {p: p.read_bytes() for p in paths}
    listings = {(root, '**/*.json'): names}
    data = HostData(active)
    versions = aim_versions(data.rows['versions'])
    people = data.people
    aliases = graph.get('identityAliases', {})
    live = {pid: data.name(pid) for pid in graph.get('people', {})
            if people.get(pid, {}).get('life_assessment', {}).get('status') == 'living'}
    feedback = latest_feedback(feedback)
    entries, found_by_child, stale, seen = [], [], set(), set()
    for path, raw in inputs.items():
        row = json.loads(raw)
        validate(row, people, versions)
        identity = row['id']
        if identity in seen:
            raise ValueError('Duplicate ask ID: ' + identity)
        seen.add(identity)
        response = feedback.get(identity)
        state, last, expired = current(row, response)
        if (state == 'answered' and last and response[2].get('kind') == 'ask_answer'
                and response[2].get('via_child') and not row.get('tender')):
            found_by_child.append(row)
        if state not in VISIBLE and not state.startswith('will_ask:'):
            continue
        if expired:
            stale.add(identity)
        aim, about = row['aim'], row['about']
        subjects = aim.get('people', [])
        holder = row['holder']
        if isinstance(holder, str):
            holder = aliases.get(holder, holder)
            name = live.get(holder) or data.name(holder)
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
        labels = [data.name(about['person']) if about.get('person') else '', data.text(about.get('line')),
                  data.text(about.get('place'))]
        item = {'id': identity, 'holder': holder, 'name': name, 'about': ' · '.join(filter(None, labels[:1] + labels[2:])) or labels[1],
                'question': data.text(row['question'], subjects), 'child': data.text(row.get('question_child'), subjects),
                'opener': data.text(opener, subjects), 'asset': asset,
                'hints': [s for h in row.get('hints', []) if (s := data.text(h, subjects))],
                'wants': [k for k in WANTS if k in row.get('wants', [])], 'tender': bool(row.get('tender')),
                'photo_note': data.text(row.get('photo_note'), subjects), 'next_hint': data.text(row.get('next_hint'), subjects),
                'occasion': data.text(row.get('occasion'), subjects), 'context': context(row), 'state': state,
                'eligible': last is None or last <= week_ago,
                'line': data.text(aim.get('line') or about.get('line')), 'settles': data.text(aim.get('settles'), subjects),
                'score': 0, 'cost': 'free', 'shelved': False, 'relevance': ''}
        if item['question'] and item['name']:
            entries.append((row, item))
    rank(active, data, entries, versions, {'settled': '{what}', 'settled_unknown': ''}, stale_asks=stale)
    ranked = sorted(((r, i) for r, i in entries if not i['shelved']), key=lambda pair: (-pair[1]['score'], pair[1]['id']))
    groups, cards, steps = defaultdict(list), defaultdict(list), defaultdict(dict)
    counts, reminders = Counter(), []
    for row, item in ranked:
        holder = item['holder']
        groups[holder].append(item)
        if item['state'] not in VISIBLE:
            continue
        if holder in live:
            counts[holder] += 1
        if item['eligible']:
            occasion = item['occasion'] or birthday(people.get(holder, {}), today, w)
            if occasion:
                reminders.append({'id': item['id'], 'name': item['name'], 'question': item['question'],
                                  'holder': holder, 'child': item['child'],
                                  'occasion': occasion, 'birthday': not bool(item['occasion'])})
        entry = {'id': item['id'], 'text': w['prompt'].format(holder=item['name'], question=item['question']),
                 'child': item['child']}
        subject_ids = subjects_for(row, aliases)
        for pid in sorted(subject_ids & graph.get('people', {}).keys()):
            cards[pid].append(entry)
        for feed, index in matching_steps(row['about'], subject_ids, graph, data):
            steps[feed].setdefault(index, entry)
    child_steps = defaultdict(set)
    for row in found_by_child:
        for feed, index in matching_steps(row['about'], subjects_for(row, aliases), graph, data):
            child_steps[feed].add(index)
    summaries = [{'id': item['id'], 'text': item['question'], 'holder': item['name'],
                  'lane': (row['aim'].get('version') or '')} for row, item in ranked if item['state'] in VISIBLE][:3]
    links = {'cards': dict(cards), 'steps': dict(steps), 'child_steps': {k: sorted(v) for k, v in child_steps.items()},
             'counts': {pid: question_count(w, count) for pid, count in counts.items()}}
    require_displayable(active, [list(groups.values()), reminders, links])
    return render(active.source_language, groups, live, w), links, reminders, summaries, inputs, listings


def render(language, groups, live, w):
    def label(key):
        return escape(w[key])

    def button(action, name, cls=''):
        return f'<button type="button" data-action="{action}" class="{cls}">{label(name)}</button>'

    live_options = ''.join(f'<option value="{escape(pid)}">{escape(name)}</option>'
                           for pid, name in sorted(live.items(), key=lambda pair: pair[1].casefold()))

    def card(item):
        hints = ''.join(f'<li>{escape(hint)}</li>' for hint in item['hints'])
        opener = escape(item['opener'])
        if item['asset']:
            opener += f' <a href="{escape(item["asset"])}">{label("show_opener")}</a>'
        opener = f'<p class="ask-opener">{opener}</p>' if opener else ''
        tender = f'<p class="ask-tender">{label("tender_notice")}</p>' if item['tender'] else ''
        child = f'<span class="ask-child" hidden>{escape(item["child"])}</span>' if item['child'] else ''
        extras = ''.join(f'<label>{label(k)}<input name="{k}" maxlength="1000"></label>'
                         for k in item['wants'] if k != 'photo')
        if extras:
            extras = f'<details><summary>{label("details")}</summary><div class="ask-fields">{extras}</div></details>'
        photo = ('<details class="ask-photo"><summary>' + label('photo_button') + '</summary><p>'
                 + label('photo_note') + '</p><p>' + escape(item['photo_note']) + '</p></details>') if 'photo' in item['wants'] else ''
        private = ('<p>' + label('private_default') + '</p>') if item['tender'] else (
            '<label class="ask-private-choice"><input name="private" type="checkbox">' + label('private_default') + '</label>')
        next_hint = escape(item['next_hint'])
        hint_hidden = '' if (next_hint and item['state'] == 'dont_know') else ' hidden'
        mark = ' data-tender="true"' if item['tender'] else ''
        return (f'<article id="ask-{escape(item["id"])}" class="ask-card" data-ask="{escape(item["id"])}" '
                f'data-context="{item["context"]}"{mark}><p class="ask-about">{escape(item["about"])}</p>{opener}'
                f'<h3><span class="ask-adult">{escape(item["question"])}</span>{child}</h3>'
                + (f'<ul class="ask-hints">{hints}</ul>' if hints else '') + tender
                + f'<p class="ask-next"{hint_hidden}>{next_hint}</p><div class="ask-actions" hidden>'
                + button('tell', 'tell', 'ask-primary') + button('dont_know', 'dont_know')
                + (button('handoff', 'handoff') if live_options else '') + button('private', 'private') + '</div>'
                + f'<form class="ask-answer" hidden><label>{label("write")}<textarea required maxlength="6000" rows="4"></textarea></label>'
                + extras + private + f'<button type="submit" class="ask-primary">{label("send")}</button></form>'
                + (f'<form class="ask-handoff" hidden><label>{label("choose")}<select required><option value=""></option>{live_options}</select></label>'
                   f'<button type="submit">{label("send")}</button></form>' if live_options else '')
                + photo + '<p class="ask-status" role="status">'
                + (label('saved_will_ask') if item['state'].startswith('will_ask:') else '') + '</p></article>')

    sections = []
    for items in groups.values():
        name = escape(items[0]['name'])
        lines = ' · '.join(escape(line) for line in dict.fromkeys(i['line'] for i in items) if line)
        count = escape(question_count(w, len(items)))
        child_count = escape(question_count(w, sum(bool(i['child']) for i in items)))
        cards = ''.join(card(item) for item in items)
        sections.append(f'<section class="ask-holder"><header><span aria-hidden="true">{escape(items[0]["name"][:1])}</span>'
                        f'<div><h2>{name}</h2><small><span class="ask-mode-count" data-adults="{count}" data-kids="{child_count}">'
                        f'{count}</span>{(" · " + lines) if lines else ""}</small></div></header>{cards}</section>')
    content = ('<div class="ask-page">'
               '<div class="ask-modes" hidden>' + button('adults', 'adults') + button('kids', 'kids') + '</div>'
               f'<section class="ask-today" hidden><h2>{label("today")}</h2><ul></ul></section>'
               + (''.join(sections) if sections else f'<p class="ask-empty">{label("empty")}</p>') + '</div>')
    return page(w['title'], content, language)
