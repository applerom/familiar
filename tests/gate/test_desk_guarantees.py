import runpy
import sys
from pathlib import Path
from types import SimpleNamespace


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


def test_desk_requires_host_decision(family):
    import json, pytest; from familiar.desk.model import decision
    with pytest.raises(ValueError, match='recorded host decision'): decision(family)
    path = family.root / 'family/desk-access.json'; row = {'schema_version': 1, 'family_id': family.id, 'projection': 'reader-private', 'host': 'demo host', 'recipient': 'demo narrator', 'decided_at': '2026-11-13', 'reason': 'Invented personal review', 'dataset': 'accepted-family-reader', 'pages': ['reader', 'journal', 'stories', 'cases', 'plan', 'questions']}; path.write_text(json.dumps(row), encoding='utf-8')
    assert decision(family)[1]; row['revoked'] = True; path.write_text(json.dumps(row), encoding='utf-8'); pytest.raises(ValueError, decision, family)


def test_documents_rank_current_aims(family):
    from shutil import copytree
    from familiar.desk.correspondence import project
    from familiar.desk.model import words
    copytree(Path(__file__).with_name('fixtures') / 'documents', family.root, dirs_exist_ok=True)
    page = project(family, words(family))[0]['desk/correspondence.html'].decode()
    assert page.index('data-recommend="free-route"') < page.index('data-recommend="paid-route"') < page.index('data-recommend="other-line"')
    assert page.index('>Ferrolho</h2>') < page.index('>Calhau</h2>') < page.index('>Set aside</h2>') < page.index('Already established:') < page.index('>No aim</h2>')
