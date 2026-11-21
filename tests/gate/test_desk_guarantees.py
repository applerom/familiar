import runpy
import sys
from pathlib import Path
from shutil import copytree
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


def test_family_asks_carry_over_and_private_memory(family):
    import json, pytest
    from familiar.cli import main
    from familiar.desk.build import assemble, hosted_files
    from familiar.instance.asks import migrate
    from familiar.instance.gate import publication
    with pytest.raises(ValueError, match='recorded host decision'): assemble(family)
    fixture = Path(__file__).with_name('fixtures') / 'asks'
    copytree(fixture / 'family', family.root / 'family', dirs_exist_ok=True)
    assert migrate(family) == 2 and migrate(family) == 0
    envelope = json.loads(next((fixture / 'inbox').glob('*.json')).read_bytes())
    copytree(fixture / 'inbox', family.root / 'family/feedback/inbox')
    cli = lambda *args: main(['--root', str(family.root), *args])
    assert cli('intake', 'feedback-draft', envelope['id'], '--output', 'inputs/reply.toml', '--id', 'private-telling') == 0
    assert cli('intake', 'memory', str(family.root / 'inputs/reply.toml')) == 0
    saved = json.loads((family.path('memory') / 'private-telling.json').read_bytes())
    assert saved['visibility'] == 'search-only' and saved['items'][0]['text'] == envelope['text']
    shared = hosted_files(assemble(family).files, personal=False, feedback_ids={envelope['id']})
    reader = publication(family, 'reader', for_review=True).files()
    assert all(envelope['text'].encode() not in raw for raw in (*shared.values(), *reader.values()))
