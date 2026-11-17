# START_MODULE_CONTRACT: MOD-DESK-ACCESS
# PURPOSE: Administer only this desk's personal identities after fresh owner and session verification.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - signed cookie, current Cognito owner role and KVS session are required on every call [review: engine lead]
# - reset, disable and removal revoke sessions before Cognito mutation; enable never revives cookies [review: engine lead]
# - temporary passwords are returned once without storage, email or logging [review: browser walk]
# - temporary passwords are plain (login + birth year, else this year), same rule as MOD-DESK-ACCOUNTS [review: engine lead]
# CHANGES_WITH:
# - MOD-DESK-ACCOUNTS (same pool and session format)
# :END_MODULE_CONTRACT
"""Owner-only account administration, composed into the desk Lambda."""
# ruff: noqa: F821
# Auth/feedback helpers and clients are defined by the composed Lambda prefix.
import re

session_store = boto3.client('cloudfront-keyvaluestore', region_name='us-east-1')


def access_principal(event):
    jar = dict(c.partition('=')[::2] for c in event.get('cookies', []))
    principal = unsign(jar.get('__Host-familiar', ''))
    if (principal.get('role') != 'owner' or principal.get('sub') !=
            event.get('headers', {}).get('x-familiar-user')):
        raise ValueError('owner_required')
    user = cognito.admin_get_user(UserPoolId=os.environ['USER_POOL'], Username=principal['username'])
    attr = {a['Name']: a['Value'] for a in user['UserAttributes']}
    record = json.loads(session_store.get_key(KvsARN=os.environ['SESSION_STORE'],
        Key='user:' + principal['sub'])['Value'])
    if (not user['Enabled'] or attr.get('custom:role') != 'owner' or
            attr.get('sub') != principal['sub'] or not record.get('enabled') or
            principal.get('session') != attr.get('custom:session') or
            record.get('session') != principal.get('session')):
        raise ValueError('session_revoked')
    return principal


def access_edge(sub, enabled, session):
    for attempt in range(3):
        etag = session_store.describe_key_value_store(KvsARN=os.environ['SESSION_STORE'])['ETag']
        try:
            session_store.put_key(KvsARN=os.environ['SESSION_STORE'], IfMatch=etag,
                Key='user:' + sub, Value=json.dumps({'enabled': enabled, 'session': session}))
            return
        except ClientError as exc:
            if attempt == 2 or exc.response['Error']['Code'] != 'ConflictException':
                raise


def access_graph():
    return json.loads(s3.get_object(Bucket=os.environ['BUCKET'], Key='site/graph.json')['Body'].read())


def access_password(username, person):
    year = ''
    for event in (person or {}).get('events') or []:
        if (event.get('tag') == 'BIRT' or event.get('type') == 'birth') and event.get('status') not in {
                'hypothesis', 'rejected', 'disproved'}:
            found = re.search(r'\b(1[89]\d\d|20\d\d)\b', str(event.get('date') or ''))
            if found:
                year = found.group(1)
                break
    if not year:
        found = re.search(r'\b(1[89]\d\d|20\d\d)\b', str(((person or {}).get('cardPresentation') or {}).get('birth') or ''))
        year = found.group(1) if found else str(time.gmtime().tm_year)
    base = re.sub(r'[^a-z]', '', username.split('-')[0].lower())
    return (base if len(base) >= 2 else 'family') + year


def access_people(graph=None):
    graph = graph or access_graph()
    people = []
    for identity, person in graph.get('people', {}).items():
        names = person.get('names') or [{}]
        name = person.get('placeholder') or names[0].get('display') or ' '.join(
            str(names[0].get(k) or '') for k in ('given', 'surname')).strip() or identity
        people.append({'id': identity, 'name': name})
    return people


def access_handler(event, context):
    try:
        principal = access_principal(event)
    except (ValueError, KeyError, TypeError, ClientError):
        return reply(403, {'error': 'owner_required'})
    method = event.get('requestContext', {}).get('http', {}).get('method')
    if event.get('rawPath') != '/api/access' or method not in {'GET', 'POST'}:
        return reply(404, {'error': 'not_found'})
    pool = os.environ['USER_POOL']
    if method == 'GET':
        users = []
        for page in cognito.get_paginator('list_users').paginate(UserPoolId=pool):
            for user in page['Users']:
                attr = {a['Name']: a['Value'] for a in user.get('Attributes', [])}
                users.append({'username': user['Username'], 'person': attr.get('custom:person', ''),
                    'role': attr.get('custom:role', ''), 'enabled': user['Enabled'],
                    'self': attr.get('sub') == principal['sub']})
        return reply(200, {'users': users, 'people': access_people()})
    headers = event.get('headers', {})
    if (headers.get('origin') != 'https://' + headers.get('x-familiar-host', '') or
            headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json'):
        return reply(403, {'error': 'same_origin_json_required'})
    try:
        raw = event.get('body') or ''
        if len(raw) > 12000:
            raise ValueError('invalid_request')
        data = json.loads(base64.b64decode(raw, validate=True) if event.get('isBase64Encoded') else raw)
        if not isinstance(data, dict) or any(not isinstance(v, str) for v in data.values()):
            raise ValueError('invalid_request')
        action, username = data.get('action'), data.get('username', '')
        if action not in {'add', 'reset', 'disable', 'enable', 'remove'}:
            raise ValueError('invalid_action')
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}', username):
            raise ValueError('invalid_username')
        if action == 'add':
            if data.get('role', 'reader') not in {'reader', 'owner'}:
                raise ValueError('invalid_role')
            graph = access_graph()
            if data.get('person') not in graph.get('people', {}):
                raise ValueError('person_required')
            email = data.get('email', '').strip()
            if email and (len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email)):
                raise ValueError('invalid_email')
            password = access_password(username, graph['people'][data['person']])
            session = secrets.token_hex(16)
            attrs = {'custom:role': data.get('role', 'reader'), 'custom:person': data['person'],
                'custom:session': session}
            if email:
                attrs['email'] = email
            created = cognito.admin_create_user(UserPoolId=pool, Username=username,
                TemporaryPassword=password, MessageAction='SUPPRESS',
                UserAttributes=[{'Name': k, 'Value': v} for k, v in attrs.items()])['User']
            attr = {a['Name']: a['Value'] for a in created['Attributes']}
            access_edge(attr['sub'], True, session)
            return reply(201, {'username': username, 'temporary_password': password})
        user = cognito.admin_get_user(UserPoolId=pool, Username=username)
        attr = {a['Name']: a['Value'] for a in user['UserAttributes']}
        # Never let a browser action remove/reset/disable its own owner entry.
        if attr['sub'] == principal['sub']:
            raise ValueError('own_account_protected')
        session = secrets.token_hex(16)
        access_edge(attr['sub'], False, session)
        if action == 'remove':
            cognito.admin_delete_user(UserPoolId=pool, Username=username)
        else:
            cognito.admin_update_user_attributes(UserPoolId=pool, Username=username,
                UserAttributes=[{'Name': 'custom:session', 'Value': session}])
            if action == 'reset':
                password = access_password(username, access_graph().get('people', {}).get(attr.get('custom:person', ''), {}))
                cognito.admin_set_user_password(UserPoolId=pool, Username=username,
                    Password=password, Permanent=False)
                access_edge(attr['sub'], user['Enabled'], session)
                return reply(200, {'username': username, 'temporary_password': password})
            if action == 'enable':
                cognito.admin_enable_user(UserPoolId=pool, Username=username)
                access_edge(attr['sub'], True, session)
            else:
                cognito.admin_disable_user(UserPoolId=pool, Username=username)
        return reply(200, {'ok': True})
    except (ValueError, TypeError, KeyError, UnicodeError):
        return reply(400, {'error': 'invalid_request'})
    except ClientError as exc:
        code = exc.response['Error']['Code']
        # Never return/log AWS exception text or request bodies containing passwords.
        return reply(409 if code == 'UsernameExistsException' else 503,
            {'error': 'username_exists' if code == 'UsernameExistsException' else 'operation_incomplete'})
