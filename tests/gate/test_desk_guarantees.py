import runpy
import sys
from pathlib import Path
from types import SimpleNamespace


def test_correspondence_mailbox(family, tmp_path):
    import json; from familiar.cli import main; from familiar.desk.correspondence import project; from familiar.desk.model import words
    form = tmp_path / 'letter.json'; row = json.loads((Path(__file__).parents[2] / 'forms/correspondence.json').read_bytes()); row.update(state='ready', people=['p-amaro'], destination='1 Example Square, Imaginary Town')
    def command(action, value):
        form.write_text(json.dumps(value), encoding='utf-8')
        assert main(['--root', str(family.root), 'family', 'correspondence', action, *([] if action == 'create' else [row['id']]), str(form)]) == 0
    command('create', row); command('update', dict(subject='Register copy', priority='later', cost='free', kind='specialist', how='Open profile'))
    page = project(family, words(family))[0]['desk/correspondence.html'].decode(); assert all(value in page for value in ('data-mail-kind="forum"', 'data-copy="destination"', 'data-copy="subject"', 'data-copy="letter"', 'Example Square', 'Register copy', 'Later', 'Free', 'Open profile'))
    command('update', dict(relevance='The record was found elsewhere.', state='not_needed')); page = project(family, words(family))[0]['desk/correspondence.html'].decode(); assert 'data-mail-group="unneeded"' in page and 'The record was found elsewhere.' in page



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
