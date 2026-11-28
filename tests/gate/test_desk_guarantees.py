import json
import runpy
import sys
from pathlib import Path
from shutil import copytree
from types import SimpleNamespace

import pytest

from familiar.desk.asks import project
from familiar.desk.model import output, words
from familiar.instance.gate import publication


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
    from familiar.cli import main
    from familiar.desk.build import assemble, hosted_files
    from familiar.instance.asks import migrate
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
    from familiar.instance.asks import change, set_horizon
    from familiar.research.research_plan import plan
    change(family, 'update', {'state': 'open'}, 'rosa-death-paper')
    page = lambda: project(family, {}, {}, words(family))[0].decode()
    assert 'ask-rosa-death-paper' in page()
    set_horizon(family, 'Ferrolho', {'since': '2026-11-22', 'by': 'the narrator'})
    ask = next(p for p in plan(family, line='Ferrolho')[0]['lines'][0]['plays'] if p['id'] == 'ask-family')
    assert 'ask-rosa-death-paper' not in page() and ask['state'] == 'closed' and 'next' not in ask
    with pytest.raises(ValueError, match='despite-horizon'):
        change(family, 'create', json.loads((family.path('asks') / 'rosa-death-paper.json').read_bytes()) | {'id': 'rosa-2'})


def test_attached_files_are_taken_by_content_within_bounds(monkeypatch):
    """A parallel reservation cannot overbook a day; a repeated send cannot replace its private original."""
    import base64, hashlib, io, uuid
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Lock
    from types import SimpleNamespace as NS
    from familiar.desk.accounts import template
    from familiar.desk.attachments import ATTACH_LIMITS, Refused, admit, original_key, remote_attachment_key
    jpeg, html = b'\xff\xd8\xff\xe0' + b'0' * 60, b'<html><script>alert(1)</script>'
    assert admit([{'size': 9, 'head': jpeg}, {'size': 9, 'head': b'\0\0\0\x18ftypheic'}]) == ['jpg', 'heic']
    for files, used, reason in [([{'size': 9, 'head': html}], 0, 'file_kind'), ([{'size': 9, 'head': jpeg}] * 11, 0, 'file_many'),
                                ([{'size': ATTACH_LIMITS['file_bytes'] + 1, 'head': jpeg}], 0, 'file_large'),
                                ([{'size': 9, 'head': jpeg}], ATTACH_LIMITS['day_files'], 'file_day')]:
        with pytest.raises(Refused, match=reason):
            admit(files, used)

    class ClientFailure(Exception):
        def __init__(self, code):
            self.response = {'Error': {'Code': code}}

    stored, lock = {}, Lock()
    broken = set()
    parallel_reads = None
    def put(Key, Body, IfMatch=None, IfNoneMatch=None, ChecksumSHA256=None, **_):
        if Key in broken:
            raise ClientFailure('ServiceUnavailable')
        raw = Body.read() if hasattr(Body, 'read') else Body
        with lock:
            if (IfNoneMatch and Key in stored) or (IfMatch and stored[Key][1] != IfMatch):
                raise ClientFailure('PreconditionFailed')
            if ChecksumSHA256:
                assert base64.b64encode(hashlib.sha256(raw).digest()).decode() == ChecksumSHA256
            stored[Key] = (raw, hashlib.sha256(raw).hexdigest())
    def get(Key, **_):
        with lock:
            found = stored.get(Key)
        if parallel_reads and Key.startswith('feedback-rate/v2/') and not getattr(get, 'released', False):
            # Both requests read the same quota version before either may attempt its conditional write.
            if not getattr(get, 'released', False):
                parallel_reads.wait(timeout=3)
                get.released = True
        if not found:
            raise ClientFailure('NoSuchKey')
        return {'Body': io.BytesIO(found[0]), 'ETag': found[1]}
    def listing(Prefix, **_):
        with lock:
            return {'Contents': [{'Key': key, 'Size': len(row[0])} for key, row in stored.items() if key.startswith(Prefix)]}
    s3 = NS(put_object=put, get_object=get, list_objects_v2=listing)
    monkeypatch.setitem(sys.modules, 'boto3', NS(client=lambda *a, **kw: s3))
    monkeypatch.setitem(sys.modules, 'botocore.exceptions', NS(ClientError=ClientFailure, BotoCoreError=RuntimeError))
    monkeypatch.setitem(sys.modules, 'botocore.config', NS(Config=lambda **kwargs: kwargs))
    monkeypatch.setenv('SESSION_KEY', 'fictional-signing-key'); monkeypatch.setenv('BUCKET', 'fictional')
    monkeypatch.setenv('COGNITO_DOMAIN', 'fictional.example.org'); monkeypatch.setenv('USER_CLIENT', 'fictional')
    runtime = {}; exec(json.loads(template())['Resources']['Feedback']['Properties']['Code']['ZipFile'], runtime)
    sub, identity = str(uuid.uuid4()), str(uuid.uuid4())
    cookie = '__Host-familiar=' + runtime['signed']({'sub': sub, 'role': 'reader', 'login': 'x' * 16, 'exp': 2 ** 40})
    def send(path, method='POST', body=None, *, query=None, signed=True):
        binary = isinstance(body, bytes)
        return runtime['handler']({'rawPath': path, 'requestContext': {'http': {'method': method}},
            'cookies': [cookie] if signed else [], 'queryStringParameters': query,
            'headers': {'content-type': 'application/octet-stream' if binary else 'application/json',
                        'x-familiar-user': sub, 'x-familiar-host': 'fictional.cloudfront.net'},
            'body': base64.b64encode(body).decode() if binary else json.dumps(body), 'isBase64Encoded': binary}, None)
    request_row = {'size': len(jpeg), 'name': '../photo.jpg', 'sha256': hashlib.sha256(jpeg).hexdigest(),
                   'head': base64.b64encode(jpeg).decode()}
    slots = '/api/feedback/files'
    ask = {'id': identity, 'files': [request_row]}
    assert send(slots, body=ask, signed=False)['statusCode'] == 403
    assert send(slots, body=ask)['statusCode'] == 200
    query = {'id': identity, 'n': '1', 'part': '0'}
    assert json.loads(send('/api/feedback/file', 'PUT', html.ljust(len(jpeg)), query=query)['body']) == {'error': 'file_kind', 'file': 1}
    assert send('/api/feedback/file', 'PUT', jpeg, query=query)['statusCode'] == 201
    assert json.loads(send(slots, body=ask)['body']) == {'uploads': []}
    declared = dict(request_row, n=1)
    del declared['head']
    remark = {'id': identity, 'kind': 'remark', 'page': '/', 'files': [declared]}
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(lambda _: send('/api/feedback', body=remark)['statusCode'], range(2))) == [200, 201]
    row = json.loads(stored['feedback/inbox/' + identity + '.json'][0])
    assert row['text'] == '' and stored[remote_attachment_key(identity, row['files'][0], 2)][0] == jpeg
    assert json.loads(send('/api/feedback/receipt', 'GET', query={'id': identity})['body']) == {'accepted': True}
    runtime['ATTACH_LIMITS'] = ATTACH_LIMITS | {'day_files': 2}
    parallel_reads = Barrier(2, action=lambda: setattr(get, 'released', True))
    with ThreadPoolExecutor(2) as pool:
        codes = pool.map(lambda _: send(slots, body={'id': str(uuid.uuid4()), 'files': [request_row]})['statusCode'], range(2))
        assert sorted(codes) == [200, 400]
    runtime['ATTACH_LIMITS'] = ATTACH_LIMITS
    identity = str(uuid.uuid4())
    words = {'id': identity, 'kind': 'remark', 'page': '/', 'text': 'Here is the family photograph.'}
    envelope = 'feedback/inbox/' + identity + '.json'
    assert send('/api/feedback', body=words)['statusCode'] == 201
    first_words = stored[envelope][0]
    ask = {'id': identity, 'single': True, 'files': [request_row]}
    upload = json.loads(send(slots, body=ask)['body'])['uploads'][0]['url']
    assert 'sha=' in upload
    query = {'id': identity, 'n': '1', 'part': '0', 'sha': declared['sha256']}
    assert send('/api/feedback/file', 'PUT', jpeg, query=query)['statusCode'] == 201
    original = original_key(identity, sub, declared | {'kind': 'jpg'})
    broken.add(original)
    with_file = words | {'file_upload': True, 'files': [declared]}
    assert send('/api/feedback', body=with_file)['statusCode'] == 503 and stored[envelope][0] == first_words
    assert json.loads(send('/api/feedback', body=words | {'text': 'Edited retry'})['body'])['text'] == words['text']
    assert json.loads(send(slots, body=ask)['body']) == {'uploads': []}
    broken.remove(original)
    assert send('/api/feedback', body=with_file)['statusCode'] == 200 and stored[original][0] == jpeg
    assert json.loads(send(slots, body=ask)['body']) == {'accepted': True} and stored[envelope][0] == first_words
    revocation = f"feedback-rate/revoked/{sub}/{'x' * 16}"
    broken.add(revocation)
    logout = send('/auth/logout', 'GET')
    assert logout['statusCode'] == 302 and all('Max-Age=0' in c for c in logout['cookies'])
    broken.remove(revocation)
    assert send('/auth/logout', 'GET')['statusCode'] == 302
    assert send('/api/feedback/file', 'PUT', jpeg, query=query)['statusCode'] == 403


def test_bare_card_invites_and_a_tap_settles_the_amendment(family):
    import uuid
    from familiar.desk.build import build
    from familiar.desk.server import accept_feedback
    from familiar.tree.amendments import current, revision
    card = lambda: json.loads(publication(family, 'reader-private').files()['graph.json'])['people']['p-walter']
    (family.root / 'family/desk-access.json').write_bytes((Path(__file__).parents[2] / 'demo/family/desk-access.json').read_bytes())
    build(family)
    slots = json.loads((output(family) / 'desk/asks-links.json').read_bytes())['blanks']['p-walter']
    shown = next(slot for slot in slots if slot['subject'] == 'amendment:walter-death')
    offer = {k: shown[k] for k in ('subject', 'amendment_revision')}
    def tap(person, identity):
        return accept_feedback(family, json.dumps(
            offer | {'id': str(identity), 'page': '/', 'person': person, 'text': 'said', 'kind': 'confirm'}).encode())
    with pytest.raises(ValueError, match='invalid_feedback'):
        tap('p-daniel', uuid.uuid4())
    identity = tap('p-walter', uuid.uuid4())[1]['id']
    assert card()['events'][0]['date'] == '1991'
    proposal = family.path('amendments') / 'walter-death.json'
    new = json.loads(proposal.read_bytes()) | {'value': '1993'}
    proposal.write_text(json.dumps(new), encoding='utf-8')
    assert card()['events'][0]['date'] == '1990'
    path = family._inside(f'family/feedback/inbox/{identity}.json')
    answer = json.loads(path.read_bytes()) | {'kind': 'decline', 'sender': {'role': 'reader', 'sub': 'relative', 'person': 'p-daniel'}}
    path.write_text(json.dumps(answer), encoding='utf-8')
    path.with_name(str(uuid.uuid4()) + '.json').write_text(json.dumps(answer | {
        'kind': 'confirm', 'amendment_revision': revision(new, 'p-walter'), 'received_at': '2099-01-01'}), encoding='utf-8')
    assert not card().get('amendments')
    merged = {'people': {'successor': {}}, 'identityAliases': {'p-walter': 'successor'}}
    assert next(row for row in current(family, merged) if row['id'] == new['id'])['state'] == 'declined'


def test_unknown_ancestor_is_never_offered_a_guess(family):
    family.path('privacy').write_text('{"life_decisions": [{"person": "p-walter", "status": "unknown", "basis": "Unresolved"}]}', encoding='utf-8')
    graph = json.loads(publication(family, 'reader-private').files()['graph.json'])
    assert not any(slot.get('guess') for slot in project(family, graph, {}, words(family))[1]['blanks'].get('p-walter', []))
