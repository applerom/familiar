"""The single installed journey: memory and a paper, independent reading, a checked reader page."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.installed
def test_installed_engine(tmp_path):
    uv = shutil.which('uv')
    assert uv, 'installed test requires uv'
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('AWS_', 'FAMILIAR_')) and k not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV')}
    for key in ('AWS_CONFIG_FILE', 'AWS_SHARED_CREDENTIALS_FILE'):
        env[key] = str(tmp_path / key); Path(env[key]).touch()
    env['AWS_EC2_METADATA_DISABLED'] = 'true'

    def run(*args, check=True):
        result = subprocess.run(args, cwd=tmp_path, env=env, check=False,
                                capture_output=True, text=True, encoding='utf-8')
        assert not check or result.returncode == 0, result.stdout + result.stderr

    run(uv, 'build', '--wheel', '--out-dir', str(tmp_path / 'dist'), str(REPO))
    venv = tmp_path / 'venv'
    run(uv, 'venv', str(venv))
    python = str(venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))
    run(uv, 'pip', 'install', '--python', python, str(next((tmp_path / 'dist').glob('*.whl'))))
    shutil.copyfile(REPO / 'demo-russian/inputs/relatives.xlsx', tmp_path / 'relatives.xlsx')
    run(python, '-X', 'utf8', '-c', INSTALLED_PATH, str(tmp_path), str(next((tmp_path / 'dist').glob('*.whl'))))


INSTALLED_PATH = r"""
import base64, contextlib, hashlib, importlib, io, json, os, shutil, subprocess, sys
import threading, tomllib, urllib.request, uuid
from pathlib import Path
from familiar.cli import main
from unittest.mock import patch
tmp_path = Path(sys.argv[1])
family = tmp_path / 'family'

def cli(*args, check=True):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(['--root', str(family), *args])
    result = subprocess.CompletedProcess(args, code, out.getvalue(), err.getvalue())
    assert not check or code == 0, result.stdout + result.stderr
    return result

assert main(['instance', 'init', str(family), '--title', 'Invented example', '--language', 'en']) == 0
config = family / 'familiar.toml'
form = lambda name: cli('research', 'form', name).stdout
for name in ('memory.toml', 'paper.toml'):
    (tmp_path / name).write_text(form(name), encoding='utf-8')
original = tmp_path / 'home-paper.txt'; original.write_text('Name: Bea Example\n', encoding='utf-8')
cli('intake', 'memory', str(tmp_path / 'memory.toml'))
cli('intake', 'paper', str(tmp_path / 'paper.toml'), '--original', str(original))
cli('instance', 'check'); cli('tree', 'build')
cli('feed', 'new', 'bea-city')
for name in ('feed', 'chapters', 'documents'):
    (family / 'feeds/bea-city' / (name + '.json')).write_text(form(name + '.json'), encoding='utf-8')
cli('instance', 'check'); cli('feed', 'build', 'bea-city')
cli('feed', 'review', 'bea-city', '--kind', 'reader', '--out', str(tmp_path / 'tutorial-review'))
cli('family', 'summary'); cli('family', 'next')
wheel = Path(sys.argv[2]); cli('instance', 'record-release', '--wheel', str(wheel), '--commit', 'a' * 40)
cli('intake', 'table', str(tmp_path / 'relatives.xlsx'), '--id', 'table', '--told-by', 'Invented narrator', '--date', '2026-11-13')
draft = family / '.state/intake/table-table'
from familiar.intake.table import toml
memory = tomllib.loads((draft / 'memory.toml').read_text(encoding='utf-8'))
memory['people'][0]['names'][0]['inferred_parts'] = {'patronymic': {'basis': 'An invented inference from the father row'}}
(draft / 'memory.toml').write_bytes(toml(memory))
cli('intake', 'memory', str(draft / 'memory.toml'), '--original', str(draft / 'original.xlsx'))
assert (family / 'originals/table/original.xlsx').read_bytes() == (tmp_path / 'relatives.xlsx').read_bytes()
unions = family / 'tree/snapshot/families.json'; rows = json.loads(unions.read_text(encoding='utf-8'))
rows['families'].append({'id': 'invented-union', 'husband': 'table-p4', 'wife': 'table-p3', 'children': ['table-p2'], 'events': [], 'provenance': ['table-c7'], 'status': 'hypothesis', 'derived': True, 'basis': 'Shared child in the family account.'})
unions.write_text(json.dumps(rows), encoding='utf-8')
doc = json.loads(form('card-document.json')); doc.update(subjects=['table-p3', 'table-p4'], snippets=[])
doc['record'].update(id='bea-marriage', fields={'Name': 'Bea Example', 'Birth': '1880'}, reading='Name: Bea Example')
(tmp_path / 'doc.json').write_text(json.dumps(doc), encoding='utf-8'); cli('research', 'document', str(tmp_path / 'doc.json'), '--author', 'reader')
image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aV1sAAAAASUVORK5CYII=')
(tmp_path / 'dot.png').write_bytes(image)
(family / 'family/archive-rights.json').write_text(json.dumps({'schema_version': 1, 'kind': 'family-photograph', 'holder': 'Invented family', 'declared_by': 'Host', 'declared_at': '2000-01-01', 'effective_from': '2000-01-01', 'permissions': {'family_app': True, 'processing': False, 'colourisation': False}, 'living_subject_consent': False}))
carrier = tmp_path / 'archive.json'; carrier.write_bytes(b'{"status":"accepted","weight":0}')
note = '{"text":"Bea &amp; family in the old archive"}'
mapping = tmp_path / 'mapping.json'; mapping.write_text(json.dumps({'id': 'old-archive', 'date': '2026-11-14', 'told_by': 'Previous archive', 'items': [{'id': 'old-note', 'person': 'table-p3', 'role': 'note', 'text': note, 'status': 'possible', 'strength': 'firm'}]}))
cli('intake', 'memory', str(mapping), '--original', str(carrier))
assert (family / 'originals/old-archive/archive.json').read_bytes() == carrier.read_bytes()
table = tmp_path / 'photos.csv'; table.write_text('file,people,caption,when,received_from\ndot.png,table-p1 table-p3,An old photo,1940s,Previous archive\n')
photos = lambda: json.loads(cli('intake', 'photo', str(table), '--table').stdout)
receipt = photos()['photos'][0]; asset = receipt['asset']
assert (family / 'originals' / receipt['original']).read_bytes() == image and photos()['attached'] == 0
assert json.loads(cli('intake', 'photo', str(tmp_path / 'dot.png'), '--face', 'table-p1=0,0,1,1', '--crop', '0,0,1,1').stdout)['photos'][0]['faces'] == {'table-p1': [0.0, 0.0, 1.0, 1.0]} and photos()['photos'][0]['status'] == 'already-attached'
assert asset not in cli('tree', 'build', '--view', 'reader').stdout
archive = tmp_path / 'host-originals'; shutil.copytree(family / 'originals', archive)
scan = archive / 'certificate.txt'; scan.write_text('Invented original', encoding='utf-8')
evidence = family / 'tree/evidence.json'
saved = json.loads(evidence.read_text(encoding='utf-8')) if evidence.exists() else {}
saved.setdefault('sources', []).append({'id': 'external-original', 'kind': 'archive-record', 'record': 'bea-marriage', 'local': str(scan), 'subjects': ['table-p3']})
saved['sources'].append({'id': 'placeholder-original', 'kind': 'archive-record', 'record': 'bea-marriage', 'local': '<snapshot>/media/absent.jpg', 'subjects': ['table-p3']})
evidence.write_text(json.dumps(saved), encoding='utf-8')
record = family / 'records/bea-marriage.json'; literal = json.loads(record.read_text(encoding='utf-8'))
literal['source']['image'] = str(tmp_path / 'undeclared-legacy-image.jpg'); record.write_text(json.dumps(literal), encoding='utf-8')
assert cli('reader', 'export', '--host-private', '--output', str(tmp_path / 'private'), check=False).returncode != 0
os.environ['FAMILIAR_HOST_PATHS'] = json.dumps({str(family): {'originals': str(archive)}})
from familiar.instance.model import Instance
from familiar.tree.builder import build
before = build(Instance(family), view='working'); union = next(f for f in before['families'] if f['id'] == 'invented-union')
old = next(f for f in before['people']['table-p3']['facts'] if any(s.startswith('table-') for s in f['sources']))
decision = {'id': 'settled', 'author': 'reader', 'schema': 1, 'relationship_decisions': [{'family': union['id'], 'previous_status': union['status'], 'status': 'verified', 'text': 'The entry establishes the union.', 'basis': 'Both people are named.', 'sources': ['bea-marriage']}], 'fact_replacements': [{'person': 'table-p3', 'prior': {'text': old['text'], 'sources': old['sources']}, 'reason': 'Read the certificate.', 'fact': {'label': 'document', 'text': 'Born in 1880.', 'status': 'verified', 'sources': ['bea-marriage']}}], 'events': {'table-p3': [{'type': 'birth', 'date': '1880', 'provenance': ['bea-marriage']}], 'table-p4': [{'type': 'birth', 'date': '1878', 'provenance': ['bea-marriage']}]}}
(tmp_path / 'decision.json').write_text(json.dumps(decision), encoding='utf-8'); cli('research', 'contribute', str(tmp_path / 'decision.json'))
review = tmp_path / 'review'
assert json.loads(cli('reader', 'preview', '--output', str(review)).stdout)['state'] == 'preview'
assert not (review / 'CURRENT.json').exists()
cli('feed', 'accept', 'bea-city', '--stage', 'reading', '--kind', 'reader',
    '--reviewer', 'reader', '--author', 'writer', '--ticket', str(review / 'review-ticket.json'))
from familiar.instance.packs import bundled_root
desk = importlib.import_module('familiar.desk.build')
pack = family / '.secrets/test-pack'; shutil.copytree(bundled_root() / 'demo-english', pack)
os.environ['FAMILIAR_HOST_PACKS'] = json.dumps({'demo-english': str(pack)})
config.write_text(config.read_text() + '\n[desk]\nsource="."\n', encoding='utf-8')
assert 'desk serve --build' in cli('desk', 'serve', check=False).stderr
fingerprint = lambda: {p.relative_to(family): p.read_bytes() for p in family.rglob('*') if p.is_file()}
before_cloud = fingerprint()
with patch('subprocess.run', side_effect=AssertionError('cloud subprocess')), patch('urllib.request.urlopen', side_effect=AssertionError('cloud HTTP')), patch('familiar.instance.writer.reap_snapshots', side_effect=AssertionError('cloud maintained family')):
    assert 'Publication is not configured' in cli('desk', 'publish', '--build', check=False).stderr
assert fingerprint() == before_cloud
access = family / 'family/desk-access.json'
access.write_text(json.dumps({'schema_version': 1, 'family_id': Instance(family).id, 'projection': 'reader-private', 'host': 'Invented host', 'recipient': 'Invented narrator', 'decided_at': '2026-11-14', 'reason': 'Fictional check', 'dataset': 'accepted-family-reader', 'pages': ['reader', 'journal', 'stories', 'cases', 'plan', 'questions']}))
legacy = family / 'media/migrated/legacy-page.html'; legacy.parent.mkdir(parents=True, exist_ok=True); legacy.write_bytes(b'<p>A page an old release kept</p>')
registry_file = family / 'media/manifest.json'; registry = json.loads(registry_file.read_text(encoding='utf-8')) if registry_file.exists() else {'schema_version': 1, 'assets': []}
registry['assets'].append({'id': 'legacy-page', 'kind': 'record-page', 'file': 'migrated/legacy-page.html', 'sha256': hashlib.sha256(legacy.read_bytes()).hexdigest(), 'origin': {'file': 'old-release'}, 'source_id': 'external-original', 'source_sha256': hashlib.sha256(scan.read_bytes()).hexdigest(), 'export': 'sources/' + hashlib.sha256(b'external-original').hexdigest()[:20] + '.html'})
registry_file.write_text(json.dumps(registry), encoding='utf-8')
assert '1 registered document pages' in cli('instance', 'upgrade').stdout and legacy.is_file()  # an old release's form carried over
desk.build(Instance(family))
from familiar.desk.server import server
with server(Instance(family), 0) as http:
    http.timeout = 5
    worker = threading.Thread(target=lambda: http.serve_forever(poll_interval=.01)); worker.start()
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{http.server_port}/', timeout=5) as response:
            assert response.status == 200 and response.read()
        headers = {'Host': f'invented.localhost:{http.server_port}', 'Origin': f'http://invented.localhost:{http.server_port}'}
        for kind in ('correction',):
            identity = str(uuid.uuid4())
            body = json.dumps({'id': identity, 'text': 'An invented correction', 'kind': kind, 'page': '/#person=table-p3', 'where': 'Invented person', 'selection': 'A line', 'future_context': {'kept': True}}).encode()
            request = urllib.request.Request(f'http://127.0.0.1:{http.server_port}/api/feedback', data=body, headers=headers | {'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=5) as response:
                assert response.status == 201
        marks = family / 'family/feedback/read'; marks.mkdir(parents=True, exist_ok=True)
        (marks / (identity + '.json')).write_text(json.dumps({'status': 'addressed', 'reply': 'Thank you; corrected.', 'internal': 'not for delivery'}))
        with urllib.request.urlopen(f'http://127.0.0.1:{http.server_port}/api/feedback?ids={identity}', timeout=5) as response:
            item = json.load(response)['items'][0]
            assert item['status'] == 'addressed' and item['reply'] == 'Thank you; corrected.' and 'internal' not in item and item['future_context']['kept']
    finally:
        http.shutdown()
        worker.join(timeout=6)
        assert not worker.is_alive()
from familiar.reader.server import CheckedReader
private_graph = json.loads(CheckedReader(Instance(family), family / '.secrets/desk-reader-cache').resource('graph.json')[0]); private = private_graph['people']
assert all(any(m['asset'] == asset and m['title'] == 'An old photo' and set(m['subjects']) == {'table-p1', 'table-p3'} for m in private[pid]['media']) for pid in ('table-p1', 'table-p3'))
assert any(f['text'] == note and f['status'] == 'hypothesis' for f in private['table-p3']['facts'])
assert private_graph['sources']['external-original']['asset'].endswith('.html')
assert next(f for f in private_graph['families'] if f['id'] == union['id'])['status'] == 'verified' and all(e['status'] != 'verified' for e in private_graph['edges'] if (e['parent'], e['child']) == ('table-p4', 'table-p2'))
assert any(f['text'] == old['text'] for f in private['table-p3']['retiredFacts']) and private['table-p3']['events'][0]['date'] == '1880'

"""
