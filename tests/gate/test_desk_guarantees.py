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


def test_closed_horizon_tells_the_story_without_asking(family):
    import json, pytest
    from familiar.desk.asks import project
    from familiar.desk.model import words
    from familiar.instance.asks import change, set_horizon
    from familiar.instance.validation import check
    from familiar.research.research_plan import plan
    change(family, 'update', {'state': 'open'}, 'rosa-death-paper')
    page = lambda: project(family, {}, {}, words(family))[0].decode()
    assert 'ask-rosa-death-paper' in page()
    set_horizon(family, 'Ferrolho', {'since': '2026-11-22', 'by': 'the narrator'})
    ask = next(p for p in plan(family, line='Ferrolho')[0]['lines'][0]['plays'] if p['id'] == 'ask-family')
    assert 'ask-rosa-death-paper' not in page() and ask['state'] == 'closed' and 'next' not in ask
    with pytest.raises(ValueError, match='despite-horizon'):
        change(family, 'create', json.loads((family.path('asks') / 'rosa-death-paper.json').read_bytes()) | {'id': 'rosa-2'})
    path = family.path('versions') / 'rosa-birthplace.json'
    row = json.loads(path.read_bytes())
    row['versions'][1]['weight'], row['unknown_weight'] = .2, .3
    row['story_choice'] = {'version': 'ponta-das-garcas', 'by': 'interest', 'basis': 'An island bride.', 'date': '2026-11-22'}
    path.write_text(json.dumps(row), encoding='utf-8')
    assert any('weaker than half' in e['message'] for e in check(family)['errors'])
