# PURPOSE: Present the owner's sealed letters as a phone-first mailbox.
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
    for key in ('versions', 'questions', 'tree_snapshot', 'contributions'):
        for p in instance.path(key).rglob('*.json'):
            inputs[p] = p.read_bytes()
    result = publication(instance, 'correspondence')
    result.check(instance)
    items, c = result.data()['items'], w['correspondence']
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
    content = '<p class="mail-intro">' + e(c['intro']) + '</p><nav class="mail-groups" aria-label="' + e(c['groups']) + '">'
    for group in ('ready', 'waiting', 'answers', 'unneeded'):
        content += '<button type="button" data-group="' + group + '" aria-pressed="' + str(group == 'ready').lower() + '">' + e(c[group]) + ' <span data-count></span></button>'
    content += '</nav><nav class="mail-kinds" aria-label="' + e(c['kinds']) + '">'
    for kind in ('all', 'archive', 'forum', 'person'):
        content += '<button type="button" data-kind="' + kind + '" aria-pressed="' + str(kind == 'all').lower() + '">' + e(c['kind_' + kind]) + '</button>'
    content += '</nav><div class="mailbox"><div class="mail-list">'
    for row in items:
        identity, state = e(row['id']), row['state']
        group = {'sent': 'waiting', 'answered': 'answers', 'closed': 'answers', 'not_needed': 'unneeded'}.get(state, 'ready')
        kind = 'forum' if row['kind'] == 'specialist' else row['kind']
        subject = row['subject'] or row['title']
        muted = ' mail-muted' if row['relevance'] or state == 'not_needed' else ''
        content += '<article class="mail-item' + muted + '" data-correspondence="' + identity + '" data-state="' + e(state) + '" data-mail-group="' + group + '" data-mail-kind="' + e(kind) + '">'
        content += '<button class="mail-row" type="button" aria-expanded="false" aria-controls="letter-' + identity + '"><span class="mail-recipient">' + e(row['recipient']) + '</span><strong>' + e(subject) + '</strong>'
        content += '<span class="mail-about">' + e(row['context']) + '</span><span class="mail-tags">'
        for label in (c.get('priority_' + row['priority'], c['priority_unset']), c.get('cost_' + row['cost'], c['cost_unknown'])):
            content += '<span class="mail-tag">' + e(label) + '</span>'
        content += '<span class="mail-state">' + e(c['state_' + state]) + '</span></span></button>'
        content += '<div class="mail-detail" id="letter-' + identity + '" hidden><h2 tabindex="-1">' + e(subject) + '</h2>'
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
        content += '<button type="button" data-remark' + ('' if state in {'answered', 'closed'} else ' hidden') + '>' + e(w['remark']) + '</button><p role="status" aria-live="polite"></p></div></article>'
    content += '<p class="mail-empty" hidden>' + e(c['empty_filter']) + '</p></div><aside class="mail-pane" aria-label="' + e(c['letter']) + '"></aside></div>'
    content += '<script defer src="/desk/correspondence.js"></script><link rel="stylesheet" href="/desk/correspondence.css">'
    return {'desk/correspondence.html': page(c['title'], content, instance.source_language)}, inputs, {(root, '*.json'): names}
