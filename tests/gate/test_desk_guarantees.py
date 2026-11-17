import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from familiar.desk.model import decision, words
from familiar.desk.show import project


def test_personal_login_flow_is_not_replaced_by_ambient_requests(monkeypatch):
    monkeypatch.setitem(sys.modules, 'boto3', SimpleNamespace(client=lambda _: None))
    monkeypatch.setitem(sys.modules, 'botocore.exceptions', SimpleNamespace(ClientError=RuntimeError))
    for key in ('SESSION_KEY', 'USER_POOL', 'SESSION_STORE'):
        monkeypatch.setenv(key, 'fictional-signing-key')
    monkeypatch.setenv('COGNITO_DOMAIN', 'fictional.example.org')
    monkeypatch.setenv('USER_CLIENT', 'fictional-client')
    auth = runpy.run_path(str(Path(__file__).parents[2] / 'src/familiar/desk/aws/accounts-auth.py'))
    event = {'rawPath': '/auth/start', 'headers': {'x-familiar-host': 'fictional.cloudfront.net'}}
    started = auth['auth'](event)
    event['cookies'] = [started['cookies'][0].split(';')[0]]
    assert started['statusCode'] == 302 and 'code_challenge=' in started['headers']['location']
    event['rawPath'] = '/auth/login'
    assert 'cookies' not in auth['auth'](event)
    event.update(rawPath='/auth/callback', queryStringParameters={'code': 'fictional', 'state': 'wrong'})
    assert auth['auth'](event)['statusCode'] == 400
    person = '@fictional@/;\r\n' + '\U0001f332' * 185
    signed = auth['signed']({'person': person, 'exp': 9999999999})
    assert auth['unsign'](signed)['person'] == person and len(signed) < 3000
    # The new identity API must refuse reader and revoked-owner cookies before mutation.
    calls = []
    attr = {'sub': 'host', 'custom:role': 'owner', 'custom:session': 'current'}
    user = {'Enabled': True, 'UserAttributes': [{'Name': k, 'Value': v} for k, v in attr.items()]}
    cognito = SimpleNamespace(admin_get_user=lambda **kw: calls.append('get') or user)
    store = SimpleNamespace(get_key=lambda **kw: {'Value': json.dumps({'enabled': True, 'session': 'current'})})
    access = runpy.run_path(str(Path(auth['__file__']).with_name('accounts-access.py')), init_globals=auth | {
        'boto3': SimpleNamespace(client=lambda *a, **kw: store), 'cognito': cognito,
        'reply': lambda status, body: {'statusCode': status}})
    event = {'rawPath': '/api/access', 'headers': {'x-familiar-user': 'host'},
        'requestContext': {'http': {'method': 'POST'}}}
    for role, session in [('reader', 'current'), ('owner', 'revoked')]:
        token = auth['signed']({'sub': 'host', 'username': 'host', 'role': role,
            'session': session, 'exp': 9999999999})
        event['cookies'] = ['__Host-familiar=' + token]
        assert access['access_handler'](event, None)['statusCode'] == 403
    assert calls == ['get']
    event['cookies'] = ['__Host-familiar=' + auth['signed']({'sub': 'host', 'username': 'host',
        'role': 'owner', 'session': 'current', 'exp': 9999999999})]
    assert access['access_principal'](event)['role'] == 'owner'


def test_desk_requires_host_decision(family):
    with pytest.raises(ValueError, match='recorded host decision'):
        decision(family)

    row = {'schema_version': 1, 'family_id': family.id, 'projection': 'reader-private',
           'host': 'demo host', 'recipient': 'demo narrator', 'decided_at': '2026-11-13',
           'reason': 'Invented personal review', 'dataset': 'accepted-family-reader',
           'pages': ['reader', 'journal', 'stories', 'cases', 'plan', 'questions']}
    (family.root / 'family/desk-access.json').write_text(json.dumps(row), encoding='utf-8')
    assert decision(family)[1]
    row['revoked'] = True
    (family.root / 'family/desk-access.json').write_text(json.dumps(row), encoding='utf-8')
    with pytest.raises(ValueError, match='does not authorize'):
        decision(family)

    family.path('versions').mkdir(exist_ok=True)
    for person in ('accepted', 'not-in-reader'):
        (family.path('versions') / (person + '.json')).write_text(json.dumps({'id': person,
            'people': [person], 'title': 'D:/private/research.json',
            'versions': [{'id': 'v', 'label': 'versions/private.json', 'weight': .4,
                          'status': 'rejected', 'against': [{'text': 'D:/private/rejected.md'}]}]}), encoding='utf-8')
    result, _, _ = project(family, {'people': {'accepted': {'living': False}}}, words(family)['show'] | {'tree': 'Tree'})
    assert len(result['versions']) == 1 and not any(s in json.dumps(result) for s in (
        'research.json', 'versions/private.json', 'rejected.md', 'not-in-reader'))
    assert result['summary']['dropped'] == 1 and result['versions'][0]['reason'] == ''
