# START_MODULE_CONTRACT: MOD-DESK-ACCOUNTS
# PURPOSE: Manage host-created Cognito identities and revocable edge sessions for an owned desk.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - every identity mutation verifies the exact tagged stack and pool before use [review: engine lead]
# - host CLI identity operations share the family's cloud-command lock [review: engine lead]
# - temporary passwords travel through a private CLI input file and ignored writer storage only [review: engine lead]
# - temporary passwords are plain to read and type (login + birth year, else this year); first sign-in replaces them [review: engine lead]
# - disabling, removal and reset revoke edge sessions before changing Cognito [review: engine lead]
# - the signing runtime is hash-pinned and its layer is owned by the same desk stack [review: engine lead]
# CHANGES_WITH:
# - MOD-DESK-AWS (personal template and outputs)
# - MOD-FAMILY-WRITER (ignored credentials)
# :END_MODULE_CONTRACT
import json
import re
import secrets
import unicodedata
from datetime import date
from importlib.resources import files

from familiar.instance.gate import boundary

from .model import publication
from .aws import cloud_command


def mode(instance):
    choice = publication(instance).get('login', 'shared')
    if choice not in {'shared', 'personal'}:
        raise ValueError('publication.login must be shared or personal')
    return choice


def template():
    root = files('familiar.desk').joinpath('aws')
    data = json.loads(root.joinpath('stack-accounts.json').read_text(encoding='utf-8'))
    data['Resources']['Login']['Properties']['FunctionCode'] = root.joinpath('accounts-edge.js').read_text(encoding='utf-8')
    data['Resources']['Feedback']['Properties']['Code']['ZipFile'] = (
        data['Resources']['Feedback']['Properties']['Code']['ZipFile'] + '\n' +
        root.joinpath('accounts-auth.py').read_text(encoding='utf-8') + '\n' +
        root.joinpath('accounts-access.py').read_text(encoding='utf-8'))
    return json.dumps(data, ensure_ascii=False)


# SigV4A signing requires AWS CRT, which is absent from the managed Python SDK.
# Pin the official CPython 3.13/arm64 wheel; the layer belongs to this same stack.
CRT_SHA256 = '3718daa98190bd829ea403c5633bf1f97bbd76be32d7065182dd177013192143'
CRT_URL = ('https://files.pythonhosted.org/packages/64/24/'
    '91fe77fd1a39d3a7da78dad45ac34cb3472b733ccf7ef8893c356df8bae2/'
    'awscrt-0.38.1-cp313-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl')
CRT_KEY = 'runtime/awscrt-0.38.1-arm64-' + CRT_SHA256 + '.zip'


def runtime_key(stack):
    return next((p.get('ParameterValue', '') for p in (stack or {}).get('Parameters', [])
        if p['ParameterKey'] == 'AccessRuntimeKey'), '')


def access_runtime(instance, current, state):
    """Bootstrap the owned bucket, then attach its stack-managed signing layer."""
    if runtime_key(current) == CRT_KEY:
        return current
    import hashlib
    import io
    import tempfile
    import time
    import urllib.request
    from pathlib import Path
    from zipfile import ZipFile
    from familiar.instance.writer import desk_private
    from .aws import _aws, _outputs, _stack
    print('Preparing the pinned AWS signing runtime for this desk', flush=True)
    with urllib.request.urlopen(CRT_URL, timeout=30) as response:
        wheel = response.read(12 * 1024 * 1024)
    if hashlib.sha256(wheel).hexdigest() != CRT_SHA256:
        raise ValueError('AWS signing runtime digest differs; no deployment performed')
    with tempfile.TemporaryDirectory(prefix='familiar-signing-') as temporary:
        path = Path(temporary) / 'runtime.zip'
        with ZipFile(io.BytesIO(wheel)) as archive, ZipFile(path, 'w') as layer:
            for item in archive.infolist():
                if item.filename.startswith('/') or '..' in item.filename.split('/'):
                    raise ValueError('Invalid signing runtime archive')
                layer.writestr('python/' + item.filename, archive.read(item))
        _aws(instance, 's3api', 'put-object', '--bucket', _outputs(current)['Bucket'],
            '--key', CRT_KEY, '--body', str(path))
    payload = {'StackName': current['StackId'], 'TemplateBody': template(),
        'Capabilities': ['CAPABILITY_IAM'],
        'Parameters': [{'ParameterKey': 'SessionKey', 'ParameterValue': state['session_key']},
            {'ParameterKey': 'FamilyTag', 'ParameterValue': publication(instance)['family_tag']},
            {'ParameterKey': 'AccessRuntimeKey', 'ParameterValue': CRT_KEY}]}
    request = desk_private(instance, 'desk-runtime.json', payload)
    try:
        _aws(instance, 'cloudformation', 'update-stack', '--cli-input-json', 'file://' + str(request))
    finally:
        desk_private(instance, 'desk-runtime.json', None)
    deadline = time.monotonic() + 540
    while True:
        stack = _stack(instance)
        if stack and stack['StackId'] == current['StackId'] and stack['StackStatus'] == 'UPDATE_COMPLETE':
            return stack
        if not stack or not stack['StackStatus'].endswith('_IN_PROGRESS') or time.monotonic() > deadline:
            raise RuntimeError('Signing runtime deployment incomplete; rerun desk provision')
        print('Desk signing runtime: ' + stack['StackStatus'], flush=True)
        time.sleep(15)


def target(instance):
    from .aws import _stack, _outputs
    from .model import secrets as read_secrets
    if mode(instance) != 'personal':
        raise ValueError('Personal users require publication.login = "personal"; provision that desk first')
    state = read_secrets(instance)
    current = _stack(instance)
    outputs = _outputs(current) if current else {}
    if (not current or current['StackId'] != state.get('stack_id') or
            not outputs.get('UserPool') or outputs.get('UserPool') != state.get('user_pool') or
            outputs.get('SessionStore') != state.get('session_store')):
        raise ValueError('Personal identity target differs from the owned desk stack; run desk provision')
    return state


def put_edge(instance, state, key, value):
    from .aws import _aws
    # Optimistic updates preserve simultaneous changes to other users.
    for attempt in range(3):
        etag = _aws(instance, 'cloudfront-keyvaluestore', 'describe-key-value-store',
                    '--kvs-arn', state['session_store'])['ETag']
        try:
            _aws(instance, 'cloudfront-keyvaluestore', 'put-key', '--kvs-arn', state['session_store'],
                 '--if-match', etag, '--key', key, '--value', json.dumps(value, separators=(',', ':'))
                 if isinstance(value, dict) else value)
            return
        except RuntimeError as exc:
            if attempt == 2 or 'ConflictException' not in str(exc):
                raise


def configure(instance, state):
    from .aws import _aws
    app = _aws(instance, 'cognito-idp', 'describe-user-pool-client',
        '--user-pool-id', state['user_pool'], '--client-id', state['user_client'])['UserPoolClient']
    if app.get('CallbackURLs') != [state['url'] + '/auth/callback']:
        # These are the same immutable settings as the template, plus the actual
        # distribution URL (which cannot be referenced without a CFN cycle).
        _aws(instance, 'cognito-idp', 'update-user-pool-client', '--cli-input-json', json.dumps({
            'UserPoolId': state['user_pool'], 'ClientId': state['user_client'],
            'SupportedIdentityProviders': ['COGNITO'], 'AllowedOAuthFlowsUserPoolClient': True,
            'AllowedOAuthFlows': ['code'], 'AllowedOAuthScopes': ['openid', 'aws.cognito.signin.user.admin'],
            'CallbackURLs': [state['url'] + '/auth/callback'], 'LogoutURLs': [state['url'] + '/auth/login'],
            'ReadAttributes': ['sub', 'email', 'custom:role', 'custom:person', 'custom:session'],
            'WriteAttributes': ['email'], 'PreventUserExistenceErrors': 'ENABLED',
            'EnableTokenRevocation': True, 'AccessTokenValidity': 1, 'IdTokenValidity': 1,
            'RefreshTokenValidity': 1, 'TokenValidityUnits': {'AccessToken': 'hours', 'IdToken': 'hours',
                'RefreshToken': 'days'}, 'ExplicitAuthFlows': ['ALLOW_REFRESH_TOKEN_AUTH']}))
    put_edge(instance, state, 'session-key', state['session_key'])


def attributes(user):
    return {a['Name']: a['Value'] for a in user.get('UserAttributes', user.get('Attributes', []))}


def username_for(person, identity):
    name = (person.get('names') or [{}])[0]
    name = name.get('given') or name.get('display') or identity
    cyrillic = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
        ['a','b','v','g','d','e','e','zh','z','i','i','k','l','m','n','o','p','r','s','t','u','f','kh','ts','ch','sh','shch','','y','','e','yu','ya']))
    latin = ''.join(cyrillic.get(c, c) for c in name.lower()).replace('ł', 'l')
    latin = unicodedata.normalize('NFKD', latin).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', latin).strip('-')[:30] or 'relative'


def _birth_year(person):
    for event in (person or {}).get('events') or []:
        if (event.get('tag') == 'BIRT' or event.get('type') == 'birth') and event.get('status') not in {
                'hypothesis', 'rejected', 'disproved'}:
            found = re.search(r'\b(1[89]\d\d|20\d\d)\b', str(event.get('date') or ''))
            if found:
                return found.group(1)
    found = re.search(r'\b(1[89]\d\d|20\d\d)\b', str(((person or {}).get('cardPresentation') or {}).get('birth') or ''))
    return found.group(1) if found else ''


def _password(username, person):
    """A first-sign-in password an elderly relative can read aloud and type: login letters + birth year.

    Strength is not the goal here: Cognito forces a new password at first sign-in, and long random
    strings with symbols broke selection and typing in practice (16.11.2026)."""
    base = re.sub(r'[^a-z]', '', username.split('-')[0].lower())
    return (base if len(base) >= 2 else 'family') + (_birth_year(person) or str(date.today().year))


def _private_call(instance, operation, payload):
    # AWS CLI errors and process command lines must never contain the password.
    from familiar.instance.writer import desk_private
    from .aws import _aws
    path = desk_private(instance, 'cognito-request.json', payload)
    try:
        return _aws(instance, 'cognito-idp', operation, '--cli-input-json', 'file://' + str(path))
    finally:
        desk_private(instance, 'cognito-request.json', None)


@boundary('consume')
@cloud_command
def execute(instance, args):
    from familiar.instance.writer import desk_private
    from .aws import _aws
    state = target(instance)
    pool = state['user_pool']
    action = args.user_action
    if action == 'list':
        users = _aws(instance, 'cognito-idp', 'list-users', '--user-pool-id', pool).get('Users', [])
        rows = []
        for user in users:
            attr = attributes(user)
            rows.append({'username': user['Username'], 'role': attr.get('custom:role', ''),
                'person': attr.get('custom:person', ''), 'enabled': user['Enabled'],
                'status': user['UserStatus'], 'last_login': None})
        return json.dumps({'users': rows, 'last_login_note': 'Cognito does not return last sign-in in ListUsers'},
                          ensure_ascii=False, indent=2)
    if action == 'add':
        from .build import read_build
        paths = read_build(instance)
        graph = json.loads(paths['graph.json'].read_bytes())
        if args.person not in graph['people']:
            raise ValueError('Person is absent from the checked desk graph; build the desk and use its person ID')
        username = args.username or username_for(graph['people'][args.person], args.person)
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}', username):
            raise ValueError('Username must contain 1–64 Latin letters, digits, dots, hyphens or underscores')
        existing = {u['Username'].lower() for u in
            _aws(instance, 'cognito-idp', 'list-users', '--user-pool-id', pool).get('Users', [])}
        if username.lower() in existing:
            if args.username:
                raise ValueError('Username already exists; choose another --username or use desk user reset')
            username += '-' + secrets.token_hex(3)
        password, session = _password(username, graph['people'][args.person]), secrets.token_hex(16)
        attrs = {'custom:role': args.role, 'custom:person': args.person, 'custom:session': session}
        if args.email:
            attrs.update({'email': args.email, 'email_verified': 'true'})
        # Save first, so interrupted creation still leaves a recoverable handout.
        desk_private(instance, 'desk-user-' + username + '.json',
                     {'username': username, 'temporary_password': password, 'person': args.person, 'role': args.role})
        result = _private_call(instance, 'admin-create-user', {'UserPoolId': pool, 'Username': username,
            'TemporaryPassword': password, 'MessageAction': 'SUPPRESS',
            'UserAttributes': [{'Name': k, 'Value': v} for k, v in attrs.items()]})
        sub = attributes(result['User'])['sub']
        put_edge(instance, state, 'user:' + sub, {'enabled': True, 'session': session})
        return f'Username: {username}\nInitial password (shown once): {password}\nChange it on first sign-in. Private handout: .secrets/desk-user-{username}.json'
    username = args.username
    user = _aws(instance, 'cognito-idp', 'admin-get-user', '--user-pool-id', pool, '--username', username)
    attr = attributes(user)
    session = secrets.token_hex(16)
    # Revocation happens before Cognito mutation. A partial failure stays closed.
    put_edge(instance, state, 'user:' + attr['sub'], {'enabled': False, 'session': session})
    if action == 'remove':
        _aws(instance, 'cognito-idp', 'admin-delete-user', '--user-pool-id', pool, '--username', username)
        desk_private(instance, 'desk-user-' + username + '.json', None)
        return 'User removed; previous sessions revoked'
    _aws(instance, 'cognito-idp', 'admin-update-user-attributes', '--user-pool-id', pool, '--username', username,
         '--user-attributes', json.dumps([{'Name': 'custom:session', 'Value': session}]))
    if action == 'reset':
        from .build import read_build
        people = json.loads(read_build(instance)['graph.json'].read_bytes())['people']
        password = _password(username, people.get(attr.get('custom:person', ''), {}))
        desk_private(instance, 'desk-user-' + username + '.json',
            {'username': username, 'temporary_password': password, 'person': attr.get('custom:person', ''),
             'role': attr.get('custom:role', '')})
        _private_call(instance, 'admin-set-user-password', {'UserPoolId': pool, 'Username': username,
                                                        'Password': password, 'Permanent': False})
        put_edge(instance, state, 'user:' + attr['sub'], {'enabled': user['Enabled'], 'session': session})
        return f'Username: {username}\nInitial password (shown once): {password}\nChange it on next sign-in. Private handout: .secrets/desk-user-{username}.json'
    _aws(instance, 'cognito-idp', 'admin-' + action + '-user', '--user-pool-id', pool, '--username', username)
    if action == 'enable':
        put_edge(instance, state, 'user:' + attr['sub'], {'enabled': True, 'session': session})
    return 'User ' + ('enabled' if action == 'enable' else 'disabled') + '; previous sessions revoked'
