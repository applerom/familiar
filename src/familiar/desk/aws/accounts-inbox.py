# The personal feedback handler, composed with auth, access and the shared file rules.
# ruff: noqa: F821 -- the functions are defined in the composed sources.
import base64
import json
import os
import uuid
import re
from urllib.parse import unquote
from datetime import datetime, timezone
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
s3 = boto3.client('s3', config=Config(connect_timeout=2, read_timeout=4,
                  retries={'mode': 'standard', 'total_max_attempts': 2}))
def reply(status, value):
    return {'statusCode': status, 'headers': {'content-type': 'application/json',
        'cache-control': 'no-store', 'x-content-type-options': 'nosniff'},
        'body': json.dumps(value)}
ASK_FIELDS = {'wants', 'private', 'tender', 'via_child', 'ask_state', 'ask_context'}

def ask_valid(data):
    kind = data['kind']
    if kind not in {'ask_answer', 'ask_state'}:
        return not any(k in data for k in ASK_FIELDS)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,119}', data.get('ask_id', '')):
        return False
    wants = data.get('wants', {})
    state = data.get('ask_state', '')
    context = data.get('ask_context', '')
    if not all(type(data.get(k, False)) is bool for k in ('private', 'tender', 'via_child')):
        return False
    if not isinstance(context, str) or context and not re.fullmatch('[0-9a-f]{16}', context):
        return False
    if kind == 'ask_answer':
        return (not state and isinstance(wants, dict)
                and not set(wants) - {'name', 'patronymic', 'maiden', 'place', 'date', 'photo', 'story'}
                and all(isinstance(v, str) and len(v) <= 1000 for v in wants.values()))
    return (not wants and isinstance(state, str) and (state in ('dont_know', 'private')
            or state.startswith('will_ask:') and 0 < len(state[9:]) <= 200))

def owner_only(data):
    try:
        page = unquote(data.get('page', ''), errors='strict').lower().split('?', 1)[0]
        if '%' in page or '\\' in page or any(ord(c) < 32 for c in page):
            return True
        parts = []
        for part in page.split('/'):
            if part == '..':
                if parts:
                    parts.pop()
            elif part and part != '.':
                parts.append(part.rstrip('.'))
        page = '/' + '/'.join(parts)
    except (TypeError, ValueError, UnicodeError, AttributeError):
        return True
    return (data.get('kind') in {'correspondence_sent', 'correspondence_reply'}
            or data.get('screen', '').lower() == 'correspondence'
            or page.startswith('/desk/correspondence'))

def feedback_handler(event, context):
    principal = unsign(next((c.split('=', 1)[1] for c in event.get('cookies', []) if c.startswith('__Host-familiar=')), ''))
    if not principal.get('sub') or principal['sub'] != event.get('headers', {}).get('x-familiar-user'):
        return reply(403, {'error': 'principal'})
    method = event.get('requestContext', {}).get('http', {}).get('method')
    route = event.get('rawPath')
    headers = event.get('headers', {})
    if headers.get('origin') and headers['origin'] != 'https://' + headers.get('x-familiar-host', ''):
        return reply(403, {'error': 'origin'})
    if (route, method) in {('/api/feedback/files', 'POST'), ('/api/feedback/file', 'PUT'),
                           ('/api/feedback/receipt', 'GET')}:
        try:
            if files_signed_out(principal):
                return reply(403, {'error': 'session_required'})
            query = event.get('queryStringParameters') or {}
            if method == 'GET':
                identity = str(uuid.UUID(query['id']))
                return reply(200, {'accepted': files_receipt(principal, identity)})
            content_type = headers.get('content-type', '').split(';')[0].strip().lower()
            if method == 'PUT' and content_type == 'application/octet-stream':
                return reply(201, files_put(principal, query, event))
            if method != 'POST' or content_type != 'application/json':
                return reply(415, {'error': 'file_failed'})
            raw = event.get('body') or ''
            if len(raw) > 28000:
                return reply(413, {'error': 'file_failed'})
            return reply(200, files_slots(principal, base64.b64decode(raw, validate=True)
                         if event.get('isBase64Encoded') else raw.encode('utf-8')))
        except Refused as refusal:
            return reply(400, refusal.body())
        except (ValueError, TypeError, KeyError, UnicodeError):
            return reply(400, {'error': 'file_failed'})
    if event.get('rawPath') != '/api/feedback' or method not in {'POST', 'GET'}:
        return reply(404, {'error': 'not_found'})
    if method == 'GET':
        query = event.get('queryStringParameters') or {}
        subject = query.get('subject', '')
        identities = set(query.get('ids', '').split(',')) - {''}
        if not identities and (not subject or len(subject) > 200):
            return reply(400, {'error': 'subject_required'})
        items = []
        try:
            marks = json.loads(s3.get_object(Bucket=os.environ['BUCKET'], Key='site/desk/feedback.json')['Body'].read())
        except ClientError:
            marks = {}
        for page in s3.get_paginator('list_objects_v2').paginate(Bucket=os.environ['BUCKET'], Prefix='feedback/inbox/'):
            for obj in page.get('Contents', []):
                try:
                    item, _ = object_json(obj['Key'])
                    if not isinstance(item, dict):
                        continue
                except (ValueError, ClientError):
                    continue
                if item.get('kind') in {'ask_answer', 'ask_state'} or amendment_reply(item) or (principal['role'] != 'owner' and (owner_only(item) or item.get('sender', {}).get('sub') != principal['sub'])):
                    continue
                if item.get('id') in identities or subject and any(item.get(k) == subject for k in ('subject', 'anchor', 'question', 'ask_id', 'person')):
                    items.append({k: v for k, v in item.items() if k not in {'status', 'reply'}} | marks.get(item['id'], {}))
        return reply(200, {'items': items})
    headers = event.get('headers', {})
    if headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
        return reply(415, {'error': 'json_required'})
    raw = event.get('body') or ''
    if len(raw) > 28000:
        return reply(413, {'error': 'too_large'})
    try:
        body = base64.b64decode(raw, validate=True) if event.get('isBase64Encoded') else raw.encode('utf-8')
        if len(body) > 20000:
            return reply(413, {'error': 'too_large'})
        data = json.loads(body)
        files = declared(data['files']) if isinstance(data, dict) and 'files' in data else None
        single = isinstance(data, dict) and data.get('file_upload') is True
        allowed = ['amendment_revision', 'anchor', 'ask_id', 'build', 'client_time', 'engine_version', 'feed', 'finding', 'id', 'kind', 'language', 'page', 'person', 'place', 'question', 'relation', 'screen', 'selection', 'step', 'subject', 'text', 'text_mode', 'viewport', 'where']
        if not isinstance(data, dict):
            raise ValueError()
        if not all(isinstance(data.get(k, ''), str) for k in allowed):
            raise ValueError()
        if not (0 if files else 1) <= len(data.get('text', '').strip()) <= 6000 or len(data.get('text', '')) > 6000:
            raise ValueError()
        if not data.get('kind', '').strip() or not ask_valid(data):
            raise ValueError()
        if data.get('kind') == 'add_person' and (not data.get('anchor') or data.get('relation') not in {'child', 'spouse', 'parent', 'father', 'mother', 'sibling', 'relative', 'self'}):
            raise ValueError()
        person = data.get('new_person')
        if person is not None and (data.get('kind') != 'add_person' or not isinstance(person, dict) or set(person) - {'surname', 'given', 'patronymic', 'maiden_surname', 'birth', 'birth_place', 'living', 'death', 'death_place', 'known_from', 'told_by', 'kin_words', 'note'}
                or not all(isinstance(v, str) and len(v) <= (4000 if k == 'note' else 200) for k, v in person.items())
                or person.get('living', '') not in {'', 'alive', 'dead', 'unknown'} or person.get('known_from', '') not in {'', 'memory', 'told', 'document'}):
            raise ValueError()
        if any(len(data.get(k, '')) > limit for k, limit in
               [('page', 2048), ('person', 200), ('question', 200), ('ask_id', 200), ('finding', 1000), ('client_time', 40), ('subject', 200), ('anchor', 200), ('relation', 40), ('place', 200), ('where', 1000), ('screen', 80), ('feed', 200), ('step', 40), ('text_mode', 40), ('language', 40), ('selection', 300), ('viewport', 40), ('engine_version', 80), ('build', 100), ('amendment_revision', 64)]):
            raise ValueError()
        if not data.get('page', '').startswith('/') or data['page'].startswith('//'):
            raise ValueError()
        identity = str(uuid.UUID(data['id']))
    except (ValueError, TypeError, KeyError, UnicodeError):
        return reply(400, {'error': 'invalid_feedback'})
    if (owner_only(data)) and (principal['role'] != 'owner' or not data.get('subject')):
        return reply(403, {'error': 'owner_required'})
    data = {k: v for k, v in data.items() if k in allowed or k == 'new_person' or k in ASK_FIELDS}
    if amendment_reply(data):
        if files or not (principal['role'] == 'owner' or principal['role'] == 'reader' and principal.get('person')):
            return reply(403, {'error': 'invalid_feedback'})
        try:
            links, _ = object_json('site/desk/asks-links.json')
        except (ValueError, ClientError):
            return reply(409, {'error': 'invalid_feedback'})
        if not amendment_offered(data, links):
            try:
                previous = own_message(principal, identity)
            except Refused:
                previous = None
            if previous and amendment_reply(previous):
                return reply(200, {'id': identity, 'duplicate': True})
            return reply(409, {'error': 'invalid_feedback'})
        data['amendment_offered'] = True
    data['sender'] = {k: principal.get(k, '') for k in ('sub', 'username', 'role', 'person')}
    data.setdefault('text', '')
    data.update({'schema_version': 1, 'id': identity, 'received_at': datetime.now(timezone.utc).isoformat()})
    try:
        if files:
            if files_signed_out(principal):
                return reply(403, {'error': 'session_required'})
            created = (single_commit if single else files_commit)(principal, identity, data, files)
        else:
            previous = own_message(principal, identity)
            created = not previous and write_inbox(identity, data)
            if not previous and not created:
                previous = own_message(principal, identity)
    except Refused as refusal:
        return reply(400, refusal.body())
    if created:
        return reply(201, {'id': identity})
    return reply(200, {'id': identity, 'duplicate': True} | (
        {'text': previous.get('text', '')} if not files and previous and not amendment_reply(previous) else {}))


def write_inbox(identity, data):
    return put_once(inbox_key(identity), (json.dumps(data, ensure_ascii=False) + '\n').encode('utf-8'),
                    ContentType='application/json; charset=utf-8')


def handler(event, context):
    if event.get('rawPath', '').startswith('/auth/'):
        return auth(event)
    if event.get('rawPath', '').startswith('/api/access'):
        return access_handler(event, context)
    try:
        return feedback_handler(event, context)
    except (ClientError, BotoCoreError):
        return reply(503, {'error': 'file_failed'})
    except (ValueError, KeyError, TypeError):
        return reply(403, {'error': 'session_required'})
