# START_MODULE_CONTRACT: MOD-CORRESPONDENCE-VIEW
# PURPOSE: Declare the owner's literal correspondence projection, separate from reader delivery.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - original files, principals and research identifiers never enter visible prose [review: engine lead]
# - a missing destination projects no send link or address line [review: engine lead]
# - outgoing prose uses the same host-text scan as family letters; living details need human review [review: engine lead]
# - ranked owner letters follow current version weights; manual relevance takes precedence [review: engine lead]
# CHANGES_WITH:
# - MOD-CORRESPONDENCE
# - MOD-PUBLICATION
# :END_MODULE_CONTRACT
import re
from collections import defaultdict

from familiar.desk.model import words

from .correspondence import address, aim_versions, no_knowledge, reply_context, rows, validate, version_options
from .host_language import HostData
from .publication import plain_text, scan


SETTLED = {'decided', 'closed', 'settled', 'accepted', 'resolved'}
INACTIVE_OPTIONS = {'rejected', 'refuted', 'discarded', 'dropped', 'ruled-out', 'superseded'}
COST = {'free': 1, 'unknown': .8, 'paid': .6}
OPEN_LETTERS = {'draft', 'ready', 'sent'}


def rank(instance, data, entries, versions, w):
    from familiar.research.coverage import family_lines, settings, surname_keys
    from familiar.tree.builder import _build, read_json

    if not any(row.get('aim') for row, _ in entries):
        return
    _, _, mode, configured = settings(instance)
    main_lines = set().union(*(surname_keys(line, instance.source_language) for line in configured))
    graph = _build(instance)
    metadata = read_json(instance.path('tree_metadata'), {})
    root = metadata.get('root') or graph.get('root') or next(iter(graph['people']), None)
    root = graph.get('identityAliases', {}).get(root, root)
    _, collateral, _, _ = family_lines(graph, root)
    free, paid = defaultdict(list), []

    for row, item in entries:
        aim = row.get('aim') or {}
        if not aim:
            continue
        people = {data.people[pid]['id'] for pid in aim.get('people', [])}
        line = surname_keys(aim.get('line'), instance.source_language)
        line_weight = 1 if not main_lines or line & main_lines else .6
        if people and people <= collateral.keys():
            line_weight = {'off': 0, 'hints': .3, 'full': .5}[mode]

        question, option = versions.get(aim.get('version'), ({}, {}))
        options = [v for v in version_options(question)
                   if v.get('status', v.get('state')) not in INACTIVE_OPTIONS
                   and type(v.get('weight')) in (int, float) and 0 <= v['weight'] <= 1]
        leader = max(options, key=lambda v: v['weight'], default={})
        leading = leader.get('weight', .5)
        uncertainty = 1 - abs(2 * leading - 1)
        decided = any(v.get('status', v.get('state')) in SETTLED for v in (question, option))
        settled = decided or leading > .9
        if settled and not item['relevance']:
            summary = question.get('summary') if decided else None
            label = (leader if leading > .9 else option or leader).get('label')
            reason = next((text for value in (summary, label, question.get('title'))
                           if (text := data.text(value, people))), item['settles'])
            item['relevance'] = w['settled'].format(what=reason) if reason else w['settled_unknown']
        item['shelved'] |= settled
        reply = row['replies'][-1] if row.get('replies') else {}
        context = reply_context(row)
        stale = (reply.get('outcome') == 'dont_know' or no_knowledge(reply.get('text', ''))) and (
            reply.get('asked_with', context) == context)
        value = aim.get('value', 0)
        value = value if type(value) in (int, float) and 0 <= value <= 1 else 0
        if not item['shelved']:
            item['score'] = value * line_weight * uncertainty * COST.get(item['cost'], .8) * (.5 if stale else 1)
        if item['shelved'] or row['state'] not in OPEN_LETTERS:
            continue
        # A linked version identifies the goal across differently worded routes.
        key = (item['line'].casefold(), frozenset(people),
               question.get('id') or item['settles'].casefold())
        if not key[-1]:
            continue
        if item['cost'] == 'free' and item['score'] > 0:
            free[key].append(item['score'])
        elif item['cost'] == 'paid':
            paid.append((key, item))
    for key, item in paid:
        if key in free:
            item['free_first'] = True
            item['score'] = min(item['score'], max(free[key])) * .5


def project(instance):
    w = words(instance)['correspondence']
    entries = rows(instance)
    if not entries:
        return {'items': [], 'text': w['empty']}
    data = HostData(instance)
    versions = aim_versions(data.rows['versions'])
    projected, letters = [], []
    for _, row in entries:
        validate(row)
        if any(pid not in data.people for pid in row['people']):
            raise ValueError('Correspondence refers to an unknown person; inspect ids with tree build --view working')
        aim = row.get('aim') or {}
        people = aim.get('people', [])
        if any(pid not in data.people for pid in people):
            raise ValueError('Correspondence aim refers to an unknown person; inspect ids with tree build --view working')
        if aim.get('version') is not None and aim['version'] not in versions:
            raise ValueError('Correspondence aim refers to an unknown version; inspect research versions')
        for key, collection in (('question', 'versions'), ('request', 'questions')):
            if row.get(key) and not data.find(collection, row[key]):
                raise ValueError('Correspondence refers to an unknown ' + key)
        # References bind context, never become visible labels. Unlike generic
        # host fragments, literal letters can contain recipient URLs and filenames.
        def prose(value):
            value = plain_text(value or '')
            def hide(match):
                data.hidden = True
                return data.words('internal_hidden')
            value = re.sub(r'@I\d+@|(?<!\w)[A-Za-z]:[\\/]\S*|(?<![\w:/])(?:family|research|tree|work|originals)[\\/]\S*', hide, value)
            value = data._check_ids(value)
            return value
        context = [data.name(pid) for pid in row['people']]
        request = data.find('questions', row.get('request'))
        question = data.find('versions', row.get('question') or request.get('question'))
        title = data.text(question.get('title'), row['people'])
        if title:
            context.append(title)
        sent = row.get('sent', {})
        item = {k: prose(row.get(k, '')) for k in
                ('title', 'recipient', 'text', 'subject', 'how', 'relevance', 'cost_note', 'destination')}
        item.update({k: prose(aim[k]).strip() if isinstance(aim.get(k), str) else ''
                     for k in ('line', 'settles', 'why_now')})
        item.update(has_aim=bool(aim), score=0, free_first=False,
                    shelved=bool(item['relevance']) or row['state'] in {'closed', 'not_needed'},
                    people=[{'id': pid, 'name': data.name(pid)} for pid in
                            dict.fromkeys(data.people[p]['id'] for p in people)])
        try:
            destination_link = address(row.get('destination'), email=True)
        except ValueError:
            destination_link = ''  # A postal address is copyable, never an invented URL.
        item.update(id=row['id'], state=row['state'], language=row['language'],
            destination_link=destination_link, follow_up=address(row['follow_up']) if row.get('follow_up') else '',
            cost=row.get('cost') or 'unknown',
            kind=row.get('kind') or {'archive': 'archive', 'forum': 'forum'}.get(row['channel'], 'person'),
            sender=prose(row['sender']['name']), context=' · '.join(context),
            sent_by=prose(sent.get('by', '')), sent_at=sent.get('at', ''),
            replies=[{k: prose(reply.get(k, '')) for k in ('text', 'by', 'at', 'meaning')} | {'feedback': reply.get('feedback', '')}
                     for reply in row.get('replies', [])])
        # Same declared text boundary used by family requests; no inference or
        # auto-redaction can certify the meaning of an agent's prose.
        scan(instance, {'text': item['text'], 'people': list(dict.fromkeys(row['people'] + people))}, 'host-text')
        projected.append((row, item))
    rank(instance, data, projected, versions, w)
    projected.sort(key=lambda pair: (not pair[1]['has_aim'], pair[1]['shelved'], -pair[1]['score'],
                                     pair[1]['title'].casefold(), pair[1]['id']))
    for row, item in projected:
        sent = row.get('sent', {})
        if row['state'] not in {'closed', 'not_needed'}:
            sections = [item['subject'] or item['title'], w['to'] + ': ' + item['recipient'],
                w['sender'] + ': ' + item['sender'], w['state_' + row['state']],
                item['settles'], item['why_now'], w.get('cost_' + item['cost'], w['cost_unknown']),
                w['free_first'] if item['free_first'] else '', item['cost_note'], item['how'], item['relevance'],
                item['destination'] and w['destination'] + ': ' + item['destination'],
                item['follow_up'] and w['follow_up'] + ': ' + item['follow_up'],
                item['context'] and w['about'] + ': ' + item['context'], item['text']]
            if sent:
                sections.append(w['sent_info'].format(by=item['sent_by'], at=item['sent_at']))
            for reply in item['replies']:
                sections.extend([reply['by'] + ' · ' + reply['at'], reply['text'], reply['meaning']])
            letters.append('\n\n'.join(filter(None, sections)))
    text = '\n\n—\n\n'.join(letters) or w['empty']
    if data.hidden:
        text += '\n\n' + data.words('internal_notice')
    return {'items': [item for _, item in projected], 'text': text}
