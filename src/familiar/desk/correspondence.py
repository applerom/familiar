# PURPOSE: Present ranked research letters by family line and person.
import html
import json

from familiar.instance.gate import publication

from .model import listing
from .pages import journal_date, page


STATE_ICON = {'draft': '○', 'ready': '●', 'sent': '◷', 'answered': '✓', 'closed': '✓', 'not_needed': '−'}


def project(instance, w, *, language=None, texts=None, local_names=None):
    """The letters page; another reader language translates the family's notes, never the letter itself."""
    language, texts, local_names = language or instance.source_language, texts or {}, local_names or {}
    tr = lambda value: texts.get(value.strip(), value) if isinstance(value, str) and value.strip() else value
    root = instance.path('correspondence')
    paths, names = listing(root, '*.json')
    listings = {(root, '*.json'): names}
    inputs = {p: p.read_bytes() for p in paths}
    for raw in list(inputs.values()):
        for reply in json.loads(raw).get('replies', []):
            original = instance._inside(reply['original'])
            inputs[original] = original.read_bytes()
    for key in ('versions', 'questions', 'tree_snapshot', 'contributions'):
        location = instance.path(key)
        paths, listings[location, '**/*.json'] = listing(location, '**/*.json')
        for p in paths:
            inputs[p] = p.read_bytes()
    for key in ('evidence', 'tree_metadata', 'identity_decisions'):
        p = instance.path(key)
        inputs[p] = p.read_bytes() if p.is_file() else None
    result = publication(instance, 'correspondence')
    result.check(instance)
    items, c = result.data()['items'], w['correspondence']
    if language != instance.source_language:
        shown = ('settles', 'title', 'why_now', 'relevance', 'recipient', 'context', 'cost_note', 'how', 'sender', 'line')
        # The letter keeps its own subject: the translated title never becomes the subject sent to an archive.
        items = [row | {k: tr(row.get(k)) for k in shown if k in row} | {'subject': row.get('subject') or row.get('title')}
                 | {'people': [p | {'name': local_names.get(p.get('id')) or tr(p.get('name'))} for p in row.get('people') or []]}
                 for row in items]
    e = lambda v: html.escape(str(v), quote=True)
    def text(value, cls='desk-prose'):
        return '<p class="' + cls + '">' + e(value) + '</p>' if value else ''
    def link(href, label):
        return '<a target="_blank" rel="noopener noreferrer" href="' + e(href) + '">' + e(label) + '</a>' if href else ''
    def copy_field(key, value, language=''):
        if not value:
            return ''
        return ('<div class="mail-field"><div class="mail-field-heading"><h3>' + e(c[key])
                + '</h3><button type="button" data-copy="' + key + '" aria-label="' + e(c['copy'] + ': ' + c[key]) + '">'
                + e(c['copy']) + '</button></div><div class="desk-prose" data-value="' + key
                + '" lang="' + e(language or instance.source_language) + '">' + e(value) + '</div></div>')

    def detail(row, identity):
        state = row['state']
        subject = row['subject'] or row['title']
        content = '<div class="mail-detail" id="letter-' + identity + '" hidden><h2 tabindex="-1">' + e(subject) + '</h2>'
        content += text(c['to'] + ': ' + row['recipient'], 'mail-meta') + text(row['context'] and c['about'] + ': ' + row['context'], 'mail-meta')
        content += text(row['relevance'], 'mail-relevance') + text(row['cost_note'], 'mail-meta')
        content += copy_field('destination', row['destination']) + link(row['destination_link'], c['open'])
        content += copy_field('subject', subject) + copy_field('letter', row['text'], row['language'])
        content += text(row['how'] and c['how'] + ': ' + row['how'], 'mail-meta') + text(c['sender'] + ': ' + row['sender'], 'mail-meta')
        content += '<p class="mail-meta" data-sent-info data-sender="' + e(row['sender']) + '"' + (' hidden' if not row['sent_by'] else '') + '>' + e(c['sent_info'].format(by=row['sent_by'], at=journal_date(row['sent_at'][:10], instance) if row['sent_at'] else '')) + '</p>'
        content += '<button type="button" data-sent' + ('' if state == 'ready' else ' hidden') + '>' + e(c['sent']) + '</button>'
        content += '<div data-follow' + ('' if state in {'sent', 'answered', 'closed'} else ' hidden') + '>' + (link(row['follow_up'], c['follow_up']) or text(c['follow_up_own'], 'mail-meta')) + '</div><div data-replies>'
        for reply in row['replies']:
            content += '<div class="mail-reply" data-feedback="' + e(reply['feedback']) + '">' + text(reply['by'] + ' · ' + reply['at'][:10], 'mail-meta') + text(reply['text']) + '<h3>' + e(c['meaning']) + '</h3>' + text(reply['meaning'] or c['pending_meaning']) + '</div>'
        content += '</div><form data-reply' + ('' if state in {'sent', 'answered'} else ' hidden') + '><label>' + e(c['reply']) + '<textarea rows="5" maxlength="6000" required></textarea></label><button type="submit">' + e(c['save_reply']) + '</button></form>'
        content += '<button type="button" data-remark' + ('' if state in {'answered', 'closed'} else ' hidden') + '>' + e(w['remark']) + '</button><p role="status" aria-live="polite"></p></div>'
        return content

    rendered = set()

    def card(row):
        identity, state = e(row['id']), row['state']
        first = identity not in rendered
        rendered.add(identity)
        kind = c.get('kind_' + row['kind'], c['kind_person'])
        cost = row['cost'] if row['cost'] in {'free', 'paid'} else 'unknown'
        content = ('<article class="mail-item"' + (' id="document-' + identity + '" data-state="' + e(state) + '"' if first else '') + '>'
                   '<button class="mail-row" type="button" data-letter="' + identity + '" aria-expanded="false"'
                   ' aria-controls="letter-' + identity + '"><strong>' + e(row['settles'] or row['title']) + '</strong>')
        for value, cls in ((row['why_now'], 'mail-why'), (row['relevance'], 'mail-reason'),
                           (c['free_first'] if row['free_first'] else '', 'mail-free-first')):
            if value:
                content += '<span class="' + cls + '">' + e(value) + '</span>'
        content += ('<span class="mail-tags"><span class="mail-state" data-status="' + e(state) + '">'
                    '<span data-state-icon aria-hidden="true">' + STATE_ICON[state] + '</span> '
                    '<span data-state-label>' + e(c['state_' + state]) + '</span></span>'
                    '<span class="mail-tag cost-' + cost + '">' + e(c['cost_' + cost]) + '</span>'
                    '<span class="mail-kind">' + e(kind) + ' · ' + e(row['recipient']) + '</span></span></button>')
        return content + (detail(row, identity) if first else '') + '</article>'

    def groups(rows, level=2):
        lines = {}
        for row in rows:
            line = (row['line'] or c['line_unknown']).casefold()
            _, people = lines.setdefault(line, (row['line'] or c['line_unknown'], {}))
            for person in row['people'] or [{'id': '', 'name': c['person_unknown']}]:
                name, letters = people.setdefault(person['id'], (person['name'], []))
                letters.append(row)
        return ''.join(f'<section class="mail-line"><h{level}>' + e(line) + f'</h{level}>'
                       + ''.join(f'<section class="mail-person"><h{level + 1}>' + e(name) + f'</h{level + 1}>'
                                 + ''.join(map(card, rows)) + '</section>' for name, rows in people.values())
                       + '</section>' for line, people in lines.values())

    ready = [row for row in items if row['state'] == 'ready' and row['score'] > 0]
    content = ''
    if items:
        content = '<section class="mail-now"><h2>' + e(c['send_now']) + '</h2><ol>'
        for i, row in enumerate(ready):
            content += ('<li' + (' hidden' if i >= 3 else '') + '><a data-recommend="' + e(row['id'])
                        + '" href="#document-' + e(row['id']) + '">' + e(row['settles'] or row['title'])
                        + '</a><span>' + e(row['recipient']) + '</span></li>')
        content += ('</ol><p class="mail-now-empty"' + (' hidden' if ready else '') + '>'
                    + e(c['empty_ready']) + '</p></section>')
    content += '<div class="mailbox"><div class="mail-list">'
    content += groups(row for row in items if row['has_aim'] and not row['shelved'])
    if shelved := [row for row in items if row['has_aim'] and row['shelved']]:
        content += '<section class="mail-shelved"><h2>' + e(c['shelved']) + '</h2>' + groups(shelved, 3) + '</section>'
    if unassigned := [row for row in items if not row['has_aim']]:
        content += ('<section class="mail-unassigned"><h2>' + e(c['no_aim']) + '</h2>'
                    + text(c['add_aim'], 'mail-meta') + ''.join(map(card, unassigned)) + '</section>')
    if not items:
        content += text(c['empty'])
    content += '</div><aside class="mail-pane" aria-label="' + e(c['letter']) + '"></aside></div>'
    content += '<script defer src="/desk/correspondence.js"></script><link rel="stylesheet" href="/desk/correspondence.css">'
    name = 'desk/correspondence.html' if language == instance.source_language else f'desk/correspondence.{language}.html'
    return {name: page(c['title'], content, language)}, inputs, listings
