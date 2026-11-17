# PURPOSE: Render the owner's sealed correspondence as large phone-first actions.
import html
import json

from familiar.instance.gate import publication

from .model import listing
from .pages import journal_date, page


def project(instance, w):
    root = instance.path('correspondence')
    paths, names = listing(root, '*.json')
    inputs = {p: p.read_bytes() for p in paths}
    for raw in list(inputs.values()):
        for reply in json.loads(raw).get('replies', []):
            original = instance._inside(reply['original'])
            inputs[original] = original.read_bytes()
    # The context titles/names come from these declared inputs, too.
    for key in ('versions', 'questions', 'tree_snapshot', 'contributions'):
        base = instance.path(key)
        for p in base.rglob('*.json'):
            inputs[p] = p.read_bytes()
    result = publication(instance, 'correspondence')
    result.check(instance)
    items = result.data()['items']
    c = w['correspondence']
    e = lambda v: html.escape(str(v), quote=True)
    def text(value, cls='desk-prose'):
        return '<p class="' + cls + '">' + e(value) + '</p>' if value else ''
    def link(href, label):
        return '<a class="correspondence-action" target="_blank" rel="noopener noreferrer" href="' + e(href) + '">' + e(label) + '</a>'
    def date(value):
        return journal_date(value[:10], instance) if value else ''
    def card(row, group):
        content = '<article class="correspondence-card" data-correspondence="' + e(row['id']) + '" data-state="' + e(row['state']) + '">'
        content += '<h3>' + e(row['title']) + '</h3>' + text(c['to'] + ': ' + row['recipient'], 'correspondence-meta')
        content += text(row['context'] and c['about'] + ': ' + row['context'], 'correspondence-meta')
        content += text(c['sender'] + ': ' + row['sender'], 'correspondence-meta')
        content += '<p class="correspondence-meta" data-sent-info data-sender="' + e(row['sender']) + '"' + (' hidden' if not row['sent_by'] else '') + '>'
        content += e(c['sent_info'].format(by=row['sent_by'], at=date(row['sent_at']))) + '</p>'
        if group == 'ready':
            content += '<div class="desk-prose correspondence-letter" lang="' + e(row['language']) + '">' + e(row['text']) + '</div>'
            content += '<div class="correspondence-actions"><button type="button" data-copy>' + e(c['copy']) + '</button>'
            content += link(row['destination'], c['destination'])
            content += '<button type="button" data-sent>' + e(c['sent']) + '</button></div>'
        else:
            content += '<details><summary>' + e(c['letter']) + '</summary><div class="desk-prose correspondence-letter" lang="' + e(row['language']) + '">' + e(row['text']) + '</div></details>'
        content += '<div data-follow' + (' hidden' if group == 'ready' else '') + '>' + (link(row['follow_up'], c['follow_up']) if row['follow_up'] else text(c['follow_up_own'], 'correspondence-meta')) + '</div>'
        for reply in row['replies']:
            content += '<div class="correspondence-reply" data-feedback="' + e(reply['feedback']) + '">' + text(reply['by'] + ' · ' + date(reply['at']), 'correspondence-meta')
            content += text(reply['text']) + '<h4>' + e(c['meaning']) + '</h4>'
            content += text(reply['meaning'] or c['pending_meaning']) + '</div>'
        if row['state'] != 'closed':
            content += '<form data-reply' + (' hidden' if group == 'ready' else '') + '><label>' + e(c['reply']) + '<textarea rows="5" maxlength="6000" required></textarea></label>'
            content += '<button type="submit">' + e(c['save_reply']) + '</button></form>'
        content += '<button type="button" data-remark' + (' hidden' if group != 'answers' else '') + '>' + e(w['remark']) + '</button>'
        content += '<p role="status" aria-live="polite"></p></article>'
        return content
    content = '<p>' + e(c['intro']) + '</p><nav class="correspondence-tabs">'
    for group in ('ready', 'waiting', 'answers'):
        content += '<a href="#' + group + '">' + e(c[group]) + '</a>'
    content += '</nav>'
    for group, states in (('ready', {'ready'}), ('waiting', {'sent'}), ('answers', {'answered', 'closed'})):
        selected = [r for r in items if r['state'] in states]
        content += '<section id="' + group + '"><h2>' + e(c[group]) + '</h2>'
        content += ''.join(card(r, group) for r in selected) or '<p class="correspondence-empty">' + e(c['empty_' + group]) + '</p>'
        content += '</section>'
    content += '<script defer src="/desk/correspondence.js"></script><link rel="stylesheet" href="/desk/correspondence.css">'
    return {'desk/correspondence.html': page(c['title'], content, instance.source_language)}, inputs, {(root, '*.json'): names}
