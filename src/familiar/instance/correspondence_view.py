# START_MODULE_CONTRACT: MOD-CORRESPONDENCE-VIEW
# PURPOSE: Declare the owner's literal correspondence projection, separate from reader delivery.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - original files, principals and research identifiers never enter visible prose [review: engine lead]
# - outgoing prose uses the same host-text scan as family letters; living details need human review [review: engine lead]
# CHANGES_WITH:
# - MOD-CORRESPONDENCE
# - MOD-PUBLICATION
# :END_MODULE_CONTRACT
import re

from familiar.desk.model import words

from .correspondence import address, rows, validate
from .host_language import HostData
from .publication import plain_text, scan


def project(instance):
    w = words(instance)['correspondence']
    entries = rows(instance)
    if not entries:
        return {'items': [], 'text': w['empty']}
    data = HostData(instance)
    projected, letters = [], []
    for _, row in entries:
        validate(row)
        if any(pid not in data.people for pid in row['people']):
            raise ValueError('Correspondence refers to an unknown person')
        for key, collection in (('question', 'versions'), ('request', 'questions')):
            if row.get(key) and not data.find(collection, row[key]):
                raise ValueError('Correspondence refers to an unknown ' + key)
        # References bind context, never become visible labels. Unlike generic
        # host fragments, literal letters can contain recipient URLs and filenames.
        def prose(value):
            value = plain_text(value or '')
            data._check_ids(value)
            if re.search(r'@I\d+@|[A-Za-z]:[\\/]|(?<![\w:/])(?:family|research|tree|work|originals)[\\/]', value):
                raise ValueError('Correspondence prose contains an internal locator')
            return value
        context = [data.name(pid) for pid in row['people']]
        request = data.find('questions', row.get('request'))
        question = data.find('versions', row.get('question') or request.get('question'))
        title = data.text(question.get('title'), row['people'])
        if title:
            context.append(title)
        sent = row.get('sent', {})
        item = {k: prose(row[k]) for k in ('title', 'recipient', 'text')}
        item.update(id=row['id'], state=row['state'], language=row['language'],
            destination=address(row['destination'], email=True), follow_up=address(row['follow_up']) if row.get('follow_up') else '',
            sender=prose(row['sender']['name']), context=' · '.join(context),
            sent_by=prose(sent.get('by', '')), sent_at=sent.get('at', ''),
            replies=[{k: prose(reply.get(k, '')) for k in ('text', 'by', 'at', 'meaning')} | {'feedback': reply.get('feedback', '')}
                     for reply in row.get('replies', [])])
        # Same declared text boundary used by family requests; no inference or
        # auto-redaction can certify the meaning of an agent's prose.
        scan(instance, {'text': item['text'], 'people': row['people']}, 'host-text')
        projected.append(item)
        if row['state'] != 'closed':
            sections = [item['title'], w['to'] + ': ' + item['recipient'],
                w['sender'] + ': ' + item['sender'], w['state_' + row['state']],
                w['destination'] + ': ' + row['destination'],
                row.get('follow_up') and w['follow_up'] + ': ' + row['follow_up'],
                item['context'] and w['about'] + ': ' + item['context'], item['text']]
            if sent:
                sections.append(w['sent_info'].format(by=item['sent_by'], at=item['sent_at']))
            for reply in item['replies']:
                sections.extend([reply['by'] + ' · ' + reply['at'], reply['text'], reply['meaning']])
            letters.append('\n\n'.join(filter(None, sections)))
    return {'items': projected, 'text': '\n\n—\n\n'.join(letters) or w['empty']}
