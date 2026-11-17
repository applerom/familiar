"""Representative data and privacy failures with a successful control."""
import copy
import json

import pytest

from familiar.feeds import service
from familiar.instance.gate import evaluate, publication
from familiar.instance.publication import restrict_graph
from familiar.instance.review import attest, review_ticket
from familiar.instance.validation import _forms, check
from familiar.instance.writer import read_generation


def edit(family, relative, change):
    path = family.root / relative
    value = json.loads(path.read_text(encoding='utf-8'))
    change(value)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


def test_f1_shown_reference_resolves(family):
    from familiar.instance.writer import mutate
    from familiar.research.delivery import contribute, document
    contribute(family, {'id': 'new-person', 'schema': 1, 'author': 'researcher', 'people': {'p-new': {'name': 'Invented Ancestor'}}})
    record = json.loads(next(family.path('records').rglob('*.json')).read_text(encoding='utf-8'))
    record.update(id='new-paper', subjects=[])
    document(family, {'record': record, 'subjects': ['p-new']}, family.root / 'input.json', 'researcher')
    assert _forms(family)['valid']
    with pytest.raises(ValueError, match='unknown reference missing.*tree build'):
        mutate(family, {family.path('records') / 'new-paper.json': record | {'subjects': ['missing']}})


def test_dropped_contribution_blocks_delivery(family):
    from familiar.tree.builder import build
    path = family.path('contributions') / 'researcher/claim.json'
    path.parent.mkdir(parents=True)
    union = {'id': 'new-union', 'husband': 'p-amaro', 'wife': 'p-new', 'status': 'hypothesis', 'text': 'Named as spouses.', 'basis': 'The document names the wife.', 'sources': ['paper'], 'weight': .4}
    path.write_text(json.dumps({'schema': 1, 'author': 'researcher', 'people': {'p-new': {'name': 'Invented Spouse'}}, 'families': [union]}), encoding='utf-8')
    for paths in (None, [str(path.relative_to(family.root))]):
        report = check(family, paths=paths)
        assert not report['valid'] and any(str(path) == e['location'] and all(s in e['message'] for s in ('families[0]', 'paper', 'Named as spouses')) for e in report['errors'])
    for publish in (lambda: build(family, view='working'), lambda: publication(family, 'reader-private')):
        with pytest.raises(ValueError, match='paper'):
            publish()
    edit(family, str(path.relative_to(family.root)), lambda p: p.update(sources={'paper': {'kind': 'home-paper', 'record': 'doc-helena-baptism'}}))
    graph = json.loads(publication(family, 'reader-private').files()['graph.json'])
    added = next(f for f in graph['families'] if f['id'] == union['id'])
    assert check(family)['valid'] and 'p-new' in graph['people'] and added['weight'] == .4 and added['basis'] == union['basis'] and added['provenance'] == ['paper'] and not any(e['parent'] == 'p-new' for e in graph['edges'])


def test_f2_record_subject_cannot_be_omitted(family):
    scan = {'photo': False, 'asset': '/shared-scan.jpg'}
    graph = {'people': {'p-amaro': {'id': 'p-amaro', 'media': [scan]}}, 'sources': {}}
    for private in (False, True):
        assert restrict_graph(family, copy.deepcopy(graph), host_private=private)['people']['p-amaro']['media']
    graph['people']['p-daniel'] = {'id': 'p-daniel', 'media': [scan]}
    for private in (False, True):
        assert not restrict_graph(family, copy.deepcopy(graph), host_private=private)['people']['p-amaro']['media']
    record = family.path('records') / 'clip.json'
    for subject in ('p-amaro', 'p-daniel'):
        record.write_text(json.dumps({'id': 'clip', 'subjects': [subject]}), encoding='utf-8')
        doc = {'record': 'clip', 'subjects': [subject], 'asset': '/clip.png'}
        graph = {'people': {}, 'feeds': [{'id': 'story', 'chapters': [{'id': 'face', 'people': ['p-amaro', 'p-daniel'], 'records': [doc]}]}]}
        for private in (False, True):
            shown = restrict_graph(family, copy.deepcopy(graph), host_private=private)['feeds'][0]['chapters'][0]
            assert bool(shown['records']) == (subject == 'p-amaro')
    graph['feeds'][0]['chapters'][0]['records'][0]['subjects'] = ['p-amaro']
    with pytest.raises(ValueError, match='subjects disagree'):
        restrict_graph(family, graph)


def test_photo_treatment_stays_local_for_living_subject(family, monkeypatch):
    from PIL import Image
    from familiar.instance.publication import scan
    family.path('media').mkdir(exist_ok=True)
    for name in ('original.png', 'treated.png'):
        Image.new('RGB', (12, 16)).save(family.path('media') / name)
    original = {'kind': 'family-photograph', 'asset': '/original.png', 'caption': 'Original photograph',
        'holder': 'Fictional family', 'subjects': ['p-daniel'], 'ours': {'kind': 'photo-treatment', 'asset': '/treated.png', 'caption': 'Same frame', 'disclosure': 'Colour added'}}
    graph = {'people': {}, 'feeds': [{'id': 'story', 'chapters': [{'id': 'face', 'figures': [original]}]}]}
    edit(family, 'family/privacy.json', lambda p: p['living'][0].update(allowed=['pictures'], consent={'by': 'subject', 'at': '2026-11-17'}))
    for private in (False, True):
        shown = scan(family, restrict_graph(family, copy.deepcopy(graph), host_private=private), 'graph', host_private=private)
        assert bool(shown['feeds'][0]['chapters'][0]['figures']) == private
    edit(family, 'family/privacy.json', lambda p: p['living'][0].update(allowed=[]))
    assert not restrict_graph(family, copy.deepcopy(graph), host_private=True)['feeds'][0]['chapters'][0]['figures']
    import hashlib
    from pathlib import Path
    from familiar.checks.engine import _known_people
    from familiar.instance.restorations import preserve
    original = json.loads((Path(__file__).parents[2] / 'forms/photo-restoration.json').read_bytes())
    original.update(asset='/original.png', subjects=['p-amaro'])
    for i, version in enumerate(original['ours']['versions']):
        Image.new('RGB', (24, 32)).save(family.path('media') / f'v{i}.png')
        version.update(asset=f'/v{i}.png'); version['recipe'].update(original_asset='/original.png', crop=[0, 0, 12, 16], original_sha256=hashlib.sha256((family.path('media') / 'original.png').read_bytes()).hexdigest(), sha256=hashlib.sha256((family.path('media') / f'v{i}.png').read_bytes()).hexdigest())
    graph['feeds'][0]['chapters'][0]['figures'] = [original]
    for private in (False, True):
        pair = scan(family, restrict_graph(family, copy.deepcopy(graph), host_private=private), 'graph', host_private=private)['feeds'][0]['chapters'][0]['figures'][0]
        assert pair['ours']['asset'] == '/v0.png' and pair['ours']['orig']['asset'] == '/original.png' and len(pair['ours']['versions']) == 2
        for broken in ({'kind': 'photo-restoration'}, dict(original, ours=dict(original['ours'], versions=[]))):
            with pytest.raises(ValueError, match='original|recipe'): scan(family, {'people': {'p-amaro': {'id': 'p-amaro', 'illustrations': [broken]}}}, 'graph', host_private=private)
    with pytest.raises(ValueError, match='append-only'): preserve(original, dict(original, ours=dict(original['ours'], versions=[])))
    edit(family, 'family/privacy.json', lambda p: p['living'][0].update(allowed=['pictures']))
    known = _known_people(family)
    for subject, status in (('p-daniel', 'living'), ('p-amaro', 'unknown')):
        original['subjects'] = [subject]; known[subject]['life_assessment'] = {'status': status}
        monkeypatch.setattr('familiar.checks.engine._known_people', lambda _: known)
        for private in (False, True):
            with pytest.raises(ValueError, match='deceased'): restrict_graph(family, copy.deepcopy(graph), host_private=private)


def test_f3_living_fields_require_permission_and_exclude_addresses(family):
    family.path('edition').parent.mkdir(exist_ok=True)
    family.path('edition').write_text(json.dumps({'people': {p: {'story': {'en': 'A card story.'}} for p in ['p-amaro', 'p-daniel']}}), encoding='utf-8')
    edit(family, 'tree/snapshot/people.json', lambda p: p['people'][-1].update(events=[{'type': kind, 'date': '2011', 'place': 'Private town', 'provenance': ['host']} for kind in ('birth', 'residence')]))
    source = {'people': {pid: {'id': pid, 'name': 'Example', 'events': [{'type': kind, 'date': '2011', 'place': 'Private town'} for kind in ('birth', 'residence')]} for pid in ('p-amaro', 'p-daniel')}}
    shown = restrict_graph(family, copy.deepcopy(source))['people']
    assert shown['p-amaro']['story']['en'] == 'A card story.' and 'story' not in shown['p-daniel'] and (not shown['p-daniel']['events'])
    edit(family, 'family/privacy.json', lambda p: p['living'][0].update(allowed=['events', 'birth'], consent={'by': 'subject', 'at': '2026-11-12'}))
    events = restrict_graph(family, copy.deepcopy(source))['people']['p-daniel']['events']
    assert [event['type'] for event in events] == ['birth']
    edit(family, 'feeds/ferrolho/feed.json', lambda f: f['persons'].update(DANIEL='p-daniel'))
    edit(family, 'feeds/ferrolho/chapters.json', lambda cs: cs[0].update(people=['AMARO', 'DANIEL'], prose={'text': [{'people': ['p-amaro'], 'text': 'The public story.'}, {'people': ['p-daniel'], 'text': 'Private detail.', 'otherwise': {'people': ['p-amaro'], 'text': 'The public story continues.'}}, {'people': ['p-daniel'], 'text': 'Another private detail.', 'otherwise': {'people': ['p-daniel'], 'text': 'A private alternative.'}}]}, places=[{'name': 'Public village', 'people': ['p-amaro']}, {'name': 'Private place', 'people': ['p-daniel']}]))
    chapter = publication(family, 'feeds').data()[0]['chapters'][0]
    assert chapter['text']['en'] == 'The public story.\n\nThe public story continues.'
    assert [p['name']['en'] for p in chapter['places']] == ['Public village']
    from familiar.instance.writer import publish
    edit(family, 'records/home/doc-helena-baptism.json', lambda r: r.update(subjects=[{'person': 'p-daniel', 'role': 'child', 'written': 'Invented child'}]))
    private = publication(family, 'reader-private')
    graph = json.loads(private.files()['graph.json'])
    assert [e['type'] for e in graph['people']['p-daniel']['events']] == ['birth']
    assert 'Private detail.' in graph['feeds'][0]['chapters'][0]['text']['en']
    assert not any((r.get('record') == 'doc-helena-baptism' for r in graph['feeds'][0]['chapters'][0]['records']))
    with pytest.raises(ValueError, match='not for publication or clean release'):
        publish(family, family.root / 'rejected', private)
    for target, alias, flag in [('p-modern', 'p-amaro', {}), ('p-amaro', 'p-modern', {}), ('p-modern', 'p-amaro', {'living': True}), ('p-amaro', 'p-modern', {'living': True})]:
        edit(family, 'tree/snapshot/people.json', lambda p: p.update(people=[r for r in p['people'] if r['id'] != 'p-modern'] + [dict(id='p-modern', name='Invented', events=[{'type': 'birth', 'date': '1990'}], **flag)]))
        family.path('identity_decisions').write_text(json.dumps({'merges': [dict(canonical=target, alias=alias, status='accepted_family_confirmation', sources=['doc-helena-baptism'], name='Invented', summary='Duplicate', birth='1990')]}), encoding='utf-8')
        shown = restrict_graph(family, {'identityAliases': {alias: target}, 'people': {target: {'id': target, 'name': 'Invented', 'facts': [{'text': 'PRIVATE MERGED FACT'}]}, 'p-daniel': {'id': 'p-daniel'}}})
        assert 'PRIVATE MERGED FACT' not in json.dumps(shown)


def test_f4_acceptance_requires_auditable_strong_grounds(family):
    fact = {'text': 'An invented conclusion', 'status': 'accepted', 'accepted': True,
            'weight': .9, 'sources': ['memory-name'], 'basis': 'A record', 'decision': 'Compared'}
    edit(family, 'feeds/ferrolho/chapters.json', lambda cs: cs[0]['facts'].append(fact))
    assert not evaluate(family)['blocked']
    edit(family, 'feeds/ferrolho/chapters.json', lambda cs: cs[0]['facts'][-1].update(weight=.05, status='possible'))
    assert evaluate(family)['blocked']


def test_f5_undeclared_reader_fields_stay_private(family, monkeypatch, capsys):
    from familiar.instance.publication import scan
    row = {'id': 'fictional-letter', 'text': 'PRIVATE LETTER'}
    shown = scan(family, {'correspondence': row, 'people': {'p-amaro': {'id': 'p-amaro', 'name': 'Example', 'author': 'SECRET'}}}, 'graph')
    assert shown['people']['p-amaro']['name'] == 'Example' and all(word not in json.dumps(shown) for word in ('SECRET', 'PRIVATE LETTER'))
    import contextlib, io, subprocess, sys, textwrap
    from pathlib import Path
    from types import SimpleNamespace as NS
    from familiar.desk.build import hosted_files
    files = {'desk/correspondence.html': b'PRIVATE LETTER', 'index.html': b'<a data-desk-label="nav_correspondence" href="/desk/correspondence.html">Letters</a>', 'desk/feedback.json': b'{"private":{"reply":"PRIVATE LETTER"}}'}
    shared = hosted_files(files, personal=False)
    assert 'desk/correspondence.html' not in shared and b'correspondence.html' not in shared['index.html'] and b'PRIVATE LETTER' not in b''.join(shared.values())
    private = {'schema_version': 1, 'kind': 'correspondence_reply', 'id': '11111111-1111-4111-8111-111111111111', 'subject': row['id'], 'text': 'PRIVATE LETTER', 'page': '/desk/correspondence.html'}
    s3 = NS(get_paginator=lambda _: NS(paginate=lambda **kw: [{'Contents': [{'Key': 'private'}, {'Key': 'ordinary'}]}]),
            get_object=lambda **kw: {'Body': io.BytesIO(json.dumps(private if kw['Key'] == 'private' else {'subject': row['id'], 'text': 'Ordinary'}).encode())})
    monkeypatch.setitem(sys.modules, 'boto3', NS(client=lambda _: s3))
    monkeypatch.setitem(sys.modules, 'botocore.exceptions', NS(ClientError=RuntimeError))
    monkeypatch.setenv('BUCKET', 'fictional')
    block = (Path(__file__).parents[2] / 'src/familiar/desk/aws/stack.yaml').read_text(encoding='utf-8').split('ZipFile: |', 1)[1].split('\n  FeedbackUrl:', 1)[0]
    runtime = {}; exec(textwrap.dedent(block), runtime)
    event = {'rawPath': '/api/feedback', 'requestContext': {'http': {'method': 'POST'}}, 'headers': {'content-type': 'application/json'}, 'body': json.dumps(private | {'sender': {'role': 'owner', 'sub': 'spoofed'}})}
    assert runtime['handler'](event, None)['statusCode'] == 403
    event.update(requestContext={'http': {'method': 'GET'}}, queryStringParameters={'subject': row['id']})
    assert json.loads(runtime['handler'](event, None)['body']) == {'items': [{'subject': row['id'], 'text': 'Ordinary'}]}
    from familiar.desk import aws
    state = {'login': 'test', 'password': 'fictional', 'login_mode': 'personal', 'stack_id': 'test', 'bucket': 'test', 'distribution': 'test', 'url': 'https://test.invalid'}
    stack = {'StackId': 'test', 'StackStatus': 'UPDATE_COMPLETE', 'Outputs': [{'OutputKey': k, 'OutputValue': 'https://test.invalid' if k in ('Url', 'FeedbackUrl') else 'test'} for k in ('Bucket', 'Distribution', 'Url', 'FeedbackUrl')]}
    family.config['publication'] = {'target': 'aws'}
    secret = family.root / '.secrets/desk.txt'; secret.parent.mkdir(exist_ok=True)
    (family.root / '.gitignore').write_text('.secrets/\n'); secret.write_text(json.dumps(state))
    for name, value in {'_target': lambda _: ('familiar-test', 'test'), '_stack': lambda _: stack, '_anonymous': lambda _: None}.items():
        monkeypatch.setattr(aws, name, value)
    monkeypatch.setattr('familiar.instance.writer.desk_upload', lambda *a, **kw: contextlib.nullcontext((family.root, 0)))
    calls = []; waiting = [True]; lost = [True]
    def cloud(instance, *args, **kw):
        calls.append(args[:2])
        if args[:2] == ('cloudfront', 'wait') and waiting[0]: raise RuntimeError('CDN pending')
        if args[:2] == ('cloudformation', 'update-stack') and lost[0]: lost[0] = False; raise RuntimeError('response lost')
        return {'Invalidation': {'Id': 'test'}}
    monkeypatch.setattr(aws, '_aws', cloud)
    with pytest.raises(RuntimeError, match='Shared login was not opened'): aws.provision(family)
    assert ('cloudformation', 'update-stack') not in calls and json.loads(secret.read_bytes())['login_mode'] == 'personal'
    calls.clear(); waiting[0] = False
    with pytest.raises(RuntimeError, match='response lost'): aws.provision(family)
    assert calls == [('s3', 'sync'), ('cloudfront', 'create-invalidation'), ('cloudfront', 'wait'), ('cloudformation', 'update-stack')]
    calls.clear(); aws.provision(family)
    assert calls == [('cloudformation', 'update-stack')] and not family._inside('.state/desk-transition.json').exists()
    with (family.root / 'familiar.toml').open('a', encoding='utf-8') as config: config.write('\n[publication]\ntarget="aws"\n')
    with pytest.raises(ValueError, match='stale'): aws._upload(family, state, personal=True)
    edge = Path(__file__).parents[2] / 'src/familiar/desk/aws'
    program = r"""
const fs=require('fs'),vm=require('vm'),crypto=require('crypto'),root=process.argv[1],key='test';
const auth='Basic '+Buffer.from('test:fictional').toString('base64'), token=Buffer.from(JSON.stringify({sub:'reader',username:'reader',role:'reader',session:'v1',exp:9999999999})).toString('base64url');
const personal={crypto,Buffer,Date,cf:{kvs:()=>({get:async k=>k==='session-key'?key:JSON.stringify({enabled:true,session:'v1'})})}},shared={require};
vm.createContext(personal);vm.runInContext(fs.readFileSync(root+'/accounts-edge.js','utf8').replace(/^import .*;\r?\n/gm,''),personal);
vm.createContext(shared);vm.runInContext(fs.readFileSync(root+'/stack.yaml','utf8').split('FunctionCode: !Sub |')[1].split(/\r?\n  FeedbackRole:/)[0].replace(/^        /gm,'').replace('${AuthHash}',crypto.createHash('sha256').update(auth).digest('hex')),shared);
(async()=>{for(const name of ['correspondence.html','correspondence.js','correspondence.css','feedback.json','questions.html','progress.html','access.html'])for(const uri of ['/desk/'+name,'/%64esk/'+name,'/desk%2f'+name,('/desk/'+name).toUpperCase(),'//desk//'+name,'/desk/../desk/'+name,'/desk/'+name+'.','/desk/'+name+'/','/desk/%zz','/desk/%FF'])for(const [mode,ctx] of [['reader',personal],['shared',shared]]){if(mode==='shared'&&!name.startsWith('correspondence')&&!name.startsWith('access'))continue;const r=await ctx.handler({request:{uri,headers:{host:{value:'test.invalid'},authorization:{value:auth}},cookies:{'__Host-familiar':{value:token+'.'+crypto.createHmac('sha256',key).update(token).digest('hex')}}}});if(![400,403].includes(r.statusCode))throw Error(mode+' '+uri)}})().catch(e=>{console.error(e);process.exitCode=1});
"""
    result = subprocess.run(['node', '-e', program, str(edge)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_f6_reconstruction_cannot_be_a_portrait(family):
    media = family.path('media')
    media.mkdir(exist_ok=True)
    (media / 'scene.svg').write_text('<svg/>', encoding='utf-8')
    pics = family.path('feeds') / 'ferrolho/pictures.json'
    pics.write_text(json.dumps({'scene': {'asset': '/scene.svg', 'kind': 'generated-reconstruction',
        'reconstruction': True, 'caption': 'A reconstruction', 'subjects': ['p-amaro']}}), encoding='utf-8')
    edit(family, 'feeds/ferrolho/chapters.json', lambda cs: cs[0].update(picture='scene'))
    assert not evaluate(family)['blocked']
    edit(family, 'feeds/ferrolho/pictures.json', lambda p: p['scene'].update(role='portrait'))
    assert evaluate(family)['blocked']


def test_f7_not_found_requires_read_coverage(family):
    path = family.path('searches') / 'searches.jsonl'
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    rows[-1]['coverage']['read'] = 0
    path.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    assert not check(family, paths=['searches/searches.jsonl'])['valid']
    rows[-1].update(result_state='access-gap', meaning='access-gap')
    path.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    assert check(family, paths=['searches/searches.jsonl'])['valid']


def test_f8_checked_generation_rechecks_used_permissions(family, tmp_path):
    edit(family, 'feeds/ferrolho/feed.json', lambda f: f['persons'].update(DANIEL='p-daniel'))
    edit(family, 'feeds/ferrolho/chapters.json', lambda cs: cs[0].update(
        people=['DANIEL'], published_fields={'DANIEL': ['birth']}))
    edit(family, 'family/privacy.json', lambda p: p['living'][0].update(
        allowed=['birth', 'summary'], consent={'by': 'subject', 'at': '2026-11-12'}))
    material = publication(family, 'feeds', for_review=True)
    assert material.manifest['state'] == 'preview'
    ticket = review_ticket(material)
    with pytest.raises(ValueError, match='reviewer'):
        attest(family, 'feeds', reviewer='writer', author='writer', ticket=ticket)
    attest(family, 'feeds', reviewer='reader', author='writer', ticket=ticket)
    out = tmp_path / 'checked'
    service.build(family, out)
    edit(family, 'feeds/ferrolho/chapters.json', lambda cs: cs[0].update(text='Edited while reading'))
    with pytest.raises(ValueError, match='review material changed'):
        attest(family, 'feeds', reviewer='reader', author='writer', ticket=ticket)
    edit(family, 'family/privacy.json', lambda p: p['living'][0].update(allowed=['summary']))
    with pytest.raises(ValueError, match='withdrawn.*birth:p-daniel'):
        read_generation(family, out)


def test_f9_trust_mode_cannot_be_changed(family):
    assert not evaluate(family)['blocked']
    path = family.root / 'familiar.toml'
    path.write_text(path.read_text(encoding='utf-8') + '\n[modes]\n"TRUST-06"="off"\n', encoding='utf-8')
    verdict = evaluate(family)
    assert verdict['blocked']
    assert any('trust' in f['message'].lower() and 'cannot' in f['message'].lower() for f in verdict['findings'])


def test_private_display_is_independent_of_unreferenced_drafts(family, tmp_path, monkeypatch):
    from familiar.instance.writer import checked_snapshot
    from familiar.reader import graph
    from familiar.reader.export import export
    original = graph._assemble
    edit(family, 'tree/evidence.json', lambda e: e['sources'].append({
        'id': 'absent-scan', 'kind': 'archive-record', 'record': 'doc-helena-baptism',
        'local': 'new-scan.png', 'subjects': ['p-helena']}))
    draft = family.path('records') / 'unfinished.json'
    def changing(*args, **kwargs):
        family.path('captures').mkdir(exist_ok=True)
        (family.path('captures') / 'collecting.html').write_bytes(b'Unreferenced raw capture')
        draft.write_text('{"unfinished":', encoding='utf-8')
        (family.path('searches') / 'unfinished.jsonl').write_text('{', encoding='utf-8')
        return original(*args, **kwargs)
    monkeypatch.setattr(graph, '_assemble', changing)
    out = tmp_path / 'private'
    export(family, out, host_private=True)
    files, watch, before = checked_snapshot(family, out)
    assert 'unfinished' not in files['graph.json'].decode()
    draft.write_text('{"another unfinished":', encoding='utf-8')
    assert watch.stamp() == before
    assert read_generation(family, out) == files
    report = _forms(family)
    assert report['valid'] and report['research_in_progress']['count']
    assert not check(family, paths=['searches/unfinished.jsonl'])['valid']
    edit(family, 'versions/rosa-birthplace.json', lambda v: v['versions'][0]['for'][0].update(sources=['unfinished']))
    assert not _forms(family)['valid']
    (family.root / 'new-scan.png').write_bytes(b'A newly saved original')
    assert watch.stamp() != before
    with pytest.raises(ValueError, match='inputs changed'):
        read_generation(family, out)
