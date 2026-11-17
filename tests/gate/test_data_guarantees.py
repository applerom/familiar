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
    assert _forms(family)['valid']
    edit(family, 'feeds/ferrolho/documents.json',
         lambda d: d['doc-helena-baptism'].update(record='not-saved-yet'))
    with pytest.raises(ValueError, match='TRUST-01'):
        publication(family, 'feeds')


def test_dropped_contribution_blocks_delivery(family):
    from familiar.tree.builder import build
    path = family.path('contributions') / 'researcher/claim.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'schema': 1, 'author': 'researcher', 'facts': {'p-amaro': [{'text': 'Kinship claim', 'status': 'verified', 'sources': ['paper']}]}}), encoding='utf-8')
    for paths in (None, [str(path.relative_to(family.root))]):
        report = check(family, paths=paths)
        assert not report['valid'] and any(str(path) == e['location'] and all(s in e['message'] for s in ('facts[p-amaro][0]', 'paper', 'Kinship claim')) for e in report['errors'])
    with pytest.raises(ValueError, match='paper'):
        build(family, view='working')
    with pytest.raises(ValueError, match='paper'):
        publication(family, 'reader-private')
    edit(family, str(path.relative_to(family.root)), lambda p: p.update(sources={'paper': {'kind': 'home-paper', 'record': 'doc-helena-baptism'}}))
    assert check(family)['valid'] and any(f['text'] == 'Kinship claim' for f in build(family, view='working')['people']['p-amaro']['facts'])


def test_f2_record_subject_cannot_be_omitted(family):
    scan = {'photo': False, 'asset': '/shared-scan.jpg'}
    graph = {'people': {'p-amaro': {'id': 'p-amaro', 'media': [scan]}}, 'sources': {}}
    for private in (False, True):
        assert restrict_graph(family, copy.deepcopy(graph), host_private=private)['people']['p-amaro']['media']
    graph['people']['p-daniel'] = {'id': 'p-daniel', 'media': [scan]}
    for private in (False, True):
        assert not restrict_graph(family, copy.deepcopy(graph), host_private=private)['people']['p-amaro']['media']


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
    edit(family, 'feeds/ferrolho/chapters.json', lambda cs: cs[0]['records'][0].update(kids=True))
    chapter = publication(family, 'feeds').data()[0]['chapters'][0]
    assert chapter['kidsSelection'] is True and chapter['records'][0]['kids'] is True; assert chapter['text']['en'] == 'The public story.\n\nThe public story continues.'
    assert [p['name']['en'] for p in chapter['places']] == ['Public village']
    from familiar.instance.writer import publish
    edit(family, 'records/home/doc-helena-baptism.json', lambda r: r.update(subjects=[{'person': 'p-daniel', 'role': 'child', 'written': 'Invented child'}]))
    private = publication(family, 'reader-private')
    graph = json.loads(private.files()['graph.json'])
    assert [e['type'] for e in graph['people']['p-daniel']['events']] == ['birth']
    assert 'Private detail.' in graph['feeds'][0]['chapters'][0]['text']['en']
    assert not any((r.get('record') == 'doc-helena-baptism' for r in graph['feeds'][0]['chapters'][0]['records']))
    assert graph['feeds'][0]['chapters'][0]['kidsSelection'] is True
    with pytest.raises(ValueError, match='not for publication or clean release'):
        publish(family, family.root / 'rejected', private)


def test_f4_acceptance_requires_auditable_strong_grounds(family):
    fact = {'text': 'An invented conclusion', 'status': 'accepted', 'accepted': True,
            'weight': .9, 'sources': ['memory-name'], 'basis': 'A record', 'decision': 'Compared'}
    edit(family, 'feeds/ferrolho/chapters.json', lambda cs: cs[0]['facts'].append(fact))
    assert not evaluate(family)['blocked']
    edit(family, 'feeds/ferrolho/chapters.json', lambda cs: cs[0]['facts'][-1].update(weight=.05, status='possible'))
    assert evaluate(family)['blocked']


def test_f5_undeclared_reader_fields_stay_private(family, monkeypatch):
    from familiar.instance.publication import scan
    from familiar.instance.correspondence import change
    from familiar.rules.roles import method_root
    row = json.loads((method_root().parent / 'forms/correspondence.json').read_text(encoding='utf-8'))
    row.update(people=['p-daniel'], state='ready', text='Daniel is my cousin. PRIVATE LETTER')
    change(family, 'create', value=row)
    working = publication(family, 'correspondence')
    assert working.working and 'PRIVATE LETTER' in working.data()['text']
    shown = scan(family, {'correspondence': row, 'people': {'p-amaro': {'id': 'p-amaro', 'name': 'Example', 'author': 'SECRET'}}}, 'graph')
    assert shown['people']['p-amaro']['name'] == 'Example' and 'SECRET' not in json.dumps(shown)
    assert 'PRIVATE LETTER' not in json.dumps(publication(family, 'reader-private').data())
    assert scan(family, row, 'correspondence') == {}
    import io, sys, textwrap
    from pathlib import Path
    from types import SimpleNamespace as NS
    from familiar.desk.build import hosted_files
    files = {'desk/correspondence.html': b'PRIVATE LETTER', 'index.html': b'<a data-desk-label="nav_correspondence" href="/desk/correspondence.html">Letters</a>', 'desk/feedback.json': b'{"private":{"reply":"PRIVATE LETTER"}}'}
    shared = hosted_files(files, personal=False)
    assert 'desk/correspondence.html' not in shared and b'correspondence.html' not in shared['index.html'] and b'PRIVATE LETTER' not in b''.join(shared.values())
    assert hosted_files(files, personal=True) == files
    private = {'kind': 'correspondence_reply', 'id': '11111111-1111-4111-8111-111111111111', 'subject': row['id'], 'text': 'PRIVATE LETTER', 'page': '/desk/correspondence.html'}
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
    from familiar.research.source_search import parse
    response = lambda body: parse({'list_reader': 'geneteka'}, {'responses': [('https://example.invalid/', '', json.dumps(body))]}, {})[0]
    assert response({'data': [], 'error': 'database unavailable'}) == response({'data': []}) == 'not_ready'
    assert response({'data': [], 'recordsFiltered': 0}) == 'empty'
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
    from familiar.rules.cascade import Registry
    from familiar.rules.exceptions import waive
    from familiar.rules.roles import method_root
    registry = Registry(method_root() / 'rules', family)
    waive(registry, 'TRUST-02', 'feed:ferrolho/chapter:0', 'The text cue was read.')
    assert registry.rule_mode('TRUST-02', 'feed:ferrolho/chapter:0').value == 'block'
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
    journal = family.path('searches') / 'unfinished.jsonl'
    journal.write_text('{', encoding='utf-8')
    report = _forms(family)
    assert report['valid'] and report['research_in_progress']['count']
    assert not check(family, paths=['searches/unfinished.jsonl'])['valid']
    edit(family, 'versions/rosa-birthplace.json', lambda v: v['versions'][0]['for'][0].update(sources=['unfinished']))
    assert not _forms(family)['valid']
    (family.root / 'new-scan.png').write_bytes(b'A newly saved original')
    assert watch.stamp() != before
    with pytest.raises(ValueError, match='inputs changed'):
        read_generation(family, out)
