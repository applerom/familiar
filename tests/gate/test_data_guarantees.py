import copy
import hashlib
import json
from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from familiar.feeds import service
from familiar.instance.gate import evaluate, publication
from familiar.instance.publication import restrict_graph, scan
from familiar.instance.review import attest, review_ticket
from familiar.instance.validation import _forms, check
from familiar.instance.writer import generation, mutate, publish, read_generation
from familiar.tree.builder import _build, build


def edit(family, relative, change):
    path = family.root / relative
    value = json.loads(path.read_text(encoding='utf-8'))
    change(value)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


def test_draft_frames_stay_home(family):
    edit(family, 'feeds/ferrolho/chapters.json', lambda chapters: chapters[0]['flow'].append({
        'after': 1, 'placeholder': {'kind': 'map', 'ratio': [4, 3], 'says': 'The island and its harbour'}}))
    with pytest.raises(ValueError, match='home-only.*ferrolho/amaro-1921'):
        publication(family, 'reader', for_review=True)


def test_play_in_flow(family):
    game = {'title': 'Where does the ship go?', 'steps': [], 'truth': {'text': 'To the mainland'}}
    mutate(family, {family.path('feeds') / 'ferrolho/play.json': {'games': {'riddle': game | {
        'route': {'asset': '/unshown.png', 'points': [{'x': 12, 'y': 60}, {'x': 75, 'y': 30}]}}}}})
    edit(family, 'feeds/ferrolho/chapters.json', lambda chapters: chapters[0]['flow'].append({
        'after': 1, 'do': {'kind': 'game', 'key': 'riddle'}}))
    chapter = json.loads(publication(family, 'reader-private').files()['graph.json'])['feeds'][0]['chapters'][0]
    assert chapter['flow'][-1] == {'after': 1, 'do': {'kind': 'game', 'key': 'riddle', 'game': game}}


def test_f1_shown_reference_resolves(family):
    from familiar.research.delivery import contribute, document
    contribute(family, {'id': 'new-person', 'schema': 1, 'author': 'researcher', 'people': {'p-new': {'name': 'Invented Ancestor'}}})
    record = json.loads(next(family.path('records').rglob('*.json')).read_text(encoding='utf-8'))
    record.update(id='new-paper', subjects=[])
    document(family, {'record': record, 'subjects': ['p-new']}, family.root / 'input.json', 'researcher')
    assert _forms(family)['valid']
    with pytest.raises(ValueError, match='unknown reference missing.*tree build'):
        mutate(family, {family.path('records') / 'new-paper.json': record | {'subjects': ['missing']}})


def test_waiting_contribution_is_quarantined_then_applied_and_never_quietly_lost(family):

    path = family.path('contributions') / 'researcher/claim.json'
    path.parent.mkdir(parents=True)
    union = {'id': 'new-union', 'husband': 'p-amaro', 'wife': 'p-new', 'status': 'hypothesis', 'text': 'Named as spouses.', 'basis': 'The document names the wife.', 'sources': ['paper'], 'weight': .4}
    path.write_text(json.dumps({'schema': 1, 'author': 'researcher', 'people': {'p-new': {'name': 'Invented Spouse'}}, 'families': [union], 'relations': []}), encoding='utf-8')
    report = check(family)  # another wave has not committed 'paper' yet: named, not applied, nothing blocks
    assert report['valid'] and report['quarantine'][0]['waits'] == ['paper'] and report['quarantine'][0]['author'] == 'researcher'
    # A key the engine never reads (a wave once wrote links as `relations`) is named, not silently dropped.
    assert any(a['location'] == str(path) and 'relations' in a['message'] and '`edges`' in a['message'] for a in report['advice'])
    assert 'p-new' not in json.loads(publication(family, 'reader-private').files()['graph.json'])['people']
    edit(family, str(path.relative_to(family.root)), lambda p: p.update(sources={'paper': {'kind': 'home-paper', 'record': 'doc-helena-baptism'}}))
    graph = json.loads(publication(family, 'reader-private').files()['graph.json'])
    added = next(f for f in graph['families'] if f['id'] == union['id'])
    assert check(family)['valid'] and 'p-new' in graph['people'] and added['weight'] == .4 and added['basis'] == union['basis'] and added['provenance'] == ['paper'] and not any(e['parent'] == 'p-new' for e in graph['edges'])
    edit(family, str(path.relative_to(family.root)), lambda p: p.pop('sources'))  # shown kinship lost: an error
    for _ in range(2):
        report = check(family)
        assert not report['valid'] and any(str(path) == e['location'] and all(s in e['message'] for s in ('families[0]', 'paper', 'applied before')) for e in report['errors'])
    for publish in (lambda: build(family, view='working'), lambda: publication(family, 'reader-private')):
        with pytest.raises(ValueError, match='paper'):
            publish()


def test_estimate_agrees_with_what_the_card_tells(family):
    from familiar.tree import birth_guess
    def card(weight, child='1930', text='Amaro was wounded in 1915.'):
        people = {p: {'id': p, 'sex': 'M', 'names': [{'given': p.title()}], 'facts': [], 'events': []} for p in ('grandfather', 'amaro', 'son')}
        graph = {'people': people, 'edges': [{'parent': 'amaro', 'child': 'son', 'status': 'export'}, {'parent': 'grandfather', 'child': 'amaro', 'weight': .4}], 'families': []}
        people['son']['events'], people['amaro']['facts'] = [{'type': 'birth', 'date': child}], [{'text': text, 'label': 'The war', 'status': 'hypothesis', 'weight': weight}]
        said = []; birth_guess.apply(family, graph, host_private=True); birth_guess.check(family, graph, lambda where, message: said.append(message))
        return [people[p]['birthGuess']['year'] for p in ('amaro', 'grandfather')], said
    plain, moved = card(.29), card(.4)
    assert moved[0][0] == 1895 < plain[0][0] and moved[0][1] < plain[0][1] and not moved[1]
    assert card(.4, text='His father was wounded in 1915.') == card(.4, text='The front came in 1915.') == plain
    assert card(.4, child='1975')[0] == card(.1, child='1975')[0] and '1975' in card(.4, child='1975')[1][0]


def test_f2_record_subject_cannot_be_omitted(family):
    from familiar.reader.documents import _local_sources
    def telling(graph):
        graph['sources']['voice'] = {'id': 'voice', 'kind': 'memory', 'text': 'A private telling'}
    assert 'A private telling' not in json.dumps(publication(family, 'tree', tree_enrich=telling, for_review=True).data())
    record = family.path('records') / 'clip.json'
    def sheet(private, *, subjects, complete, weight=None):
        case = json.loads(Path(__file__).with_name('fixtures').joinpath('document-context.json').read_bytes())
        record.write_text(json.dumps(case['record'] | {'type': 'census', 'subjects': subjects, 'subjects_complete': complete}), encoding='utf-8')
        graph = case['graph']
        if weight is not None:
            graph['edges'][0].update(sources=['clip'], weight=weight)
        shown = restrict_graph(family, graph, host_private=private)
        pages, _ = _local_sources(family, shown, {}, host_private=private)
        records = shown['feeds'][0]['chapters'][0]['records']
        assert records[-1]['read'] == case['record']['fields']['place'] and (len(records) == 2) == bool(pages)
        assert ('both witnesses' in str(shown['people']['p-amaro']['notes'])) == bool(pages)
        person = shown['people']['p-amaro']
        assert person['name'] == case['record']['fields']['fate']
        assert person['facts'][0]['text'] == ('missing in action; «both witnesses beside»' if pages else 'missing in action; «…»')
        assert {sid: 'text' in shown['sources'][sid] for sid in ('son', 'voice')} == {'son': private, 'voice': private}
        game = shown['feeds'][0]['chapters'][0].get('game', {})
        assert bool(game.get('truth', {}).get('record')) == (private and bool(pages))
        return bool(pages)
    for private in (False, True):
        assert sheet(private, subjects=['p-amaro'], complete=True, weight=.29)
        assert not sheet(private, subjects=['p-amaro'], complete=False)
        assert not sheet(private, subjects=['p-amaro'], complete=True, weight=.30)
    with pytest.raises(ValueError, match='subjects disagree'):
        sheet(False, subjects=['p-daniel'], complete=True)


@pytest.mark.parametrize('scenario', ['historical', 'citation', 'same'])
def test_only_recorded_events_open_a_card(family, scenario):
    fixture = Path(__file__).with_name('fixtures').joinpath('parent-life.json').read_text(encoding='utf-8')
    case = json.loads(fixture.replace('RECENT', str(date.today().year - 60)).replace('OLDER', str(date.today().year - 90)))[scenario]
    edit(family, 'tree/snapshot/people.json', lambda g: g.update(people=[p for p in g['people'] if p['id'] not in case['expected']] + case['people']))
    edit(family, 'tree/evidence.json', lambda g: g['edges'].extend(case['edges']))
    edit(family, 'records/home/doc-helena-baptism.json', lambda r: r.update(case['record']))
    edit(family, 'family/amendments/walter-death.json', lambda p: p.update(weight=1, state='confirmed'))
    family.path('identity_decisions').write_text(json.dumps({'merges': case.get('merges', [])}), encoding='utf-8')
    for private in (False, True):
        people = _build(family, family_display=private)['people']
        assert {p: people[p]['life_assessment']['status'] for p in case['expected']} == {p: modes[int(private)] for p, modes in case['expected'].items()}
        if 'sealed_living' in case:
            graph = json.loads(publication(family, 'reader-private' if private else 'reader', for_review=True).files()['graph.json'])
            shown = next(p for p in graph['people'].values() if p['name'] == people['p-citer']['name'])
            assert shown.get('living') is case['sealed_living']
    if scenario == 'same':
        assert graph['identityAliases']['p-named'] == 'p-citer' and not graph.get('presentationAliases')
        assert [e['weight'] for e in graph['edges'] if 'p-citer' in (e['parent'], e['child'])] == [.5, .99]
        decision = case['merges'][0] | {'status': 'probable', 'weight': .45}
        family.path('identity_decisions').write_text(json.dumps({'merges': [decision]}), encoding='utf-8')
        paper = 'doc-candidate'
        edit(family, 'tree/evidence.json', lambda g: g['sources'].append({'id': paper, 'kind': 'home-paper', 'record': paper}))
        edit(family, 'tree/snapshot/people.json', lambda g: next(p for p in g['people'] if p['id'] == 'p-named').update(
            living=False, events=[{'type': 'birth', 'date': 'ABT 1890'}, {'type': 'baptism', 'date': '1891', 'provenance': [paper]}]))
        edit(family, 'tree/snapshot/people.json', lambda g: next(p for p in g['people'] if p['id'] == 'p-citer').update(living=False))
        for protected in (False, True):
            (family.path('records') / f'home/{paper}.json').write_text(json.dumps(case['candidate_paper'] | {'privacy': 'living-possible' if protected else 'dead'}), encoding='utf-8')
            graph = json.loads(publication(family, 'reader-private').files()['graph.json'])
            match, = graph['people']['p-citer']['probableIdentities']
            assert 'p-named' not in graph['people'] and graph['presentationAliases'] == {'p-named': 'p-citer'}
            assert match['weight'] == .45 and match['card']['birth'] == 'ABT 1890'
            assert (paper in match['card']['papers'], bool(graph['sources'][paper].get('asset'))) == (not protected, not protected)



def test_only_visible_amendments_leave_the_inbox(family):
    path = 'family/amendments/walter-death.json'
    literal = json.loads((family.root / path).read_bytes())['basis']
    assert literal.encode() in publication(family, 'reader-private').files()['graph.json']
    edit(family, 'records/home/doc-helena-baptism.json', lambda row: row.update(privacy='living-possible'))
    for change in ({'state': 'declined'}, {'state': 'proposed', 'weight': 1, 'sources': ['doc-helena-baptism']}):
        edit(family, path, lambda row: row.update(change))
        assert literal.encode() not in b''.join(publication(family, 'reader-private').files().values())


def test_photo_treatment_stays_local_for_living_subject(family, monkeypatch):
    family.path('media').mkdir(exist_ok=True)
    for name in ('original.png', 'treated.png'):
        Image.new('RGB', (12, 16)).save(family.path('media') / name)
    original = {'kind': 'family-photograph', 'asset': '/original.png', 'caption': 'Original photograph',
        'holder': 'Fictional family', 'subjects': ['p-daniel'], 'ours': {'kind': 'photo-treatment', 'asset': '/treated.png', 'caption': 'Same frame', 'disclosure': 'Colour added'}}
    graph = {'people': {}, 'feeds': [{'id': 'story', 'chapters': [{'id': 'face', 'figures': [original]}]}]}
    for private in (False, True):
        shown = scan(family, restrict_graph(family, copy.deepcopy(graph), host_private=private), 'graph', host_private=private)
        assert bool(shown['feeds'][0]['chapters'][0]['figures']) == private
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
    frame = family.path('records') / 'invented-period-frame.json'
    period = dict(original, kind='period-picture', record=frame.stem, subjects=[], unidentified_people=True)
    graph['feeds'][0]['chapters'][0]['figures'] = [period]
    record = {'id': frame.stem, 'kind': 'index-entry', 'title': 'Fictional harbour', 'date': '1915',
              'source': {'holder': 'Invented archive', 'locator': 'Print 12'}}
    frame.write_text(json.dumps(record), encoding='utf-8')
    shown = scan(family, restrict_graph(family, copy.deepcopy(graph)), 'graph')
    assert shown['feeds'][0]['chapters'][0]['figures'][0]['ours']['orig']['subjects'] == []
    for change, error in (({'date': str(date.today().year)}, 'capture date'),
                          ({'privacy': 'living-possible'}, 'protected original'),
                          ({'subjects': ['p-daniel']}, 'deceased')):
        frame.write_text(json.dumps(record | change), encoding='utf-8')
        for private in (False, True):
            with pytest.raises(ValueError, match=error):
                restrict_graph(family, copy.deepcopy(graph), host_private=private)
    graph['feeds'][0]['chapters'][0]['figures'] = [original]
    known = _known_people(family)
    for subject, status in (('p-daniel', 'living'), ('p-amaro', 'unknown')):
        original['subjects'] = [subject]; known[subject]['life_assessment'] = {'status': status}
        monkeypatch.setattr('familiar.checks.engine._known_people', lambda _, **kwargs: known)
        for private in (False, True):
            with pytest.raises(ValueError, match='deceased'): restrict_graph(family, copy.deepcopy(graph), host_private=private)


def test_f3_public_name_and_kinship_and_private_address_exclusion(family):
    family.path('edition').parent.mkdir(exist_ok=True)
    family.path('edition').write_text(json.dumps({'people': {p: {'story': {'en': 'A card story.'}} for p in ['p-amaro', 'p-daniel']}}), encoding='utf-8')
    edit(family, 'tree/snapshot/people.json', lambda p: p['people'][-1].update(living=None,
        events=[{'type': kind, 'date': str(date.today().year - 75), 'place': 'Private town', 'provenance': ['host']} for kind in ('birth', 'residence')]))
    source = {'people': {pid: {'id': pid, 'name': 'Example', 'events': [{'type': kind, 'date': '2011', 'place': 'Private town'} for kind in ('birth', 'residence')]} for pid in ('p-amaro', 'p-daniel')}}
    shown = restrict_graph(family, copy.deepcopy(source))['people']
    assert shown['p-amaro']['story']['en'] == 'A card story.' and 'story' not in shown['p-daniel'] and (not shown['p-daniel']['events'])
    edit(family, 'feeds/ferrolho/feed.json', lambda f: f['persons'].update(DANIEL='p-daniel'))
    edit(family, 'feeds/ferrolho/chapters.json', lambda cs: cs[0].update(people=['AMARO', 'DANIEL'], prose={'text': [{'people': ['p-amaro'], 'text': 'The public story.'}, {'people': ['p-daniel'], 'text': 'Private detail.', 'otherwise': {'people': ['p-amaro'], 'text': 'The public story continues.'}}, {'people': ['p-daniel'], 'text': 'Another private detail.', 'otherwise': {'people': ['p-daniel'], 'text': 'A private alternative.'}}]}, places=[{'name': 'Public village', 'people': ['p-amaro']}, {'name': 'Private place', 'people': ['p-daniel']}]))
    chapter = publication(family, 'feeds').data()[0]['chapters'][0]
    assert chapter['text']['en'] == 'The public story.\n\nThe public story continues.'
    assert [p['name']['en'] for p in chapter['places']] == ['Public village']
    capture = family.root / 'fictional-paper.png'
    Image.new('RGB', (2200, 400)).save(capture)
    edit(family, 'records/home/doc-helena-baptism.json', lambda r: r.update(
        subjects=[{'person': 'p-daniel', 'role': 'child', 'written': 'Invented child'}], source={'kind': 'home', 'holder': 'host', 'locator': capture.name + '; whole sheet'}))
    private = publication(family, 'reader-private')
    graph = json.loads(private.files()['graph.json'])
    assert [e['type'] for e in graph['people']['p-daniel']['events']] == ['birth']
    assert 'Private detail.' in graph['feeds'][0]['chapters'][0]['text']['en']
    assert 'asset' not in graph['sources']['doc-helena-baptism'] and {d['record'] for d in graph['feeds'][0]['chapters'][0]['records']} == {'rec-santa-ludovina-1921-14'}
    with pytest.raises(ValueError, match='not for publication or clean release'):
        publish(family, family.root / 'rejected', private)
    edit(family, 'family/privacy.json', lambda p: p.update(living=[]))
    files = publication(family, 'reader-private').files()
    scan = json.loads(files['graph.json'])['sources']['doc-helena-baptism']['image'][1:]
    assert scan in files and json.loads(files['bundle.json'])['files'][scan]['source_sha256'] == hashlib.sha256(capture.read_bytes()).hexdigest()
    for target, alias, flag in [('p-modern', 'p-amaro', {}), ('p-amaro', 'p-modern', {}), ('p-modern', 'p-amaro', {'living': True}), ('p-amaro', 'p-modern', {'living': True})]:
        edit(family, 'tree/snapshot/people.json', lambda p: p.update(people=[r for r in p['people'] if r['id'] != 'p-modern'] + [dict(id='p-modern', name='Invented', events=[{'type': 'birth', 'date': '1810' if flag else '1990'}], **flag)]))
        family.path('identity_decisions').write_text(json.dumps({'merges': [dict(canonical=target, alias=alias, status='accepted_family_confirmation', sources=['doc-helena-baptism'], name='Invented', summary='Duplicate', birth='1990')]}), encoding='utf-8')
        shown = restrict_graph(family, {'identityAliases': {alias: target}, 'people': {target: {'id': target, 'name': 'Invented', 'facts': [{'text': 'PRIVATE MERGED FACT'}]}, 'p-daniel': {'id': 'p-daniel'}}})
        assert 'PRIVATE MERGED FACT' not in json.dumps(shown)


def test_life_decision_scope(family):
    ident = 'p-daniel'
    edit(family, 'tree/snapshot/people.json', lambda g: next(p for p in g['people'] if p['id'] == ident).update(
        living=None, events=[{'type': 'birth', 'date': str(date.today().year - 70)}]))
    decision = {'person': ident, 'status': 'dead', 'by': 'host', 'at': '2025-01-01'}
    for scope, basis in [('home', 'Family age judgement'), ('everywhere', 'Recorded death')]:
        family.path('privacy').write_text(json.dumps({'life_decisions': [decision | {'scope': scope, 'basis': basis}]}), encoding='utf-8')
        assert _build(family, family_display=True)['people'][ident]['life_assessment']['status'] == 'dead'
        graph = publication(family, 'reader', for_review=True).files()['graph.json']
        assert (ident.encode() in graph) is (scope == 'everywhere')


def test_f4_acceptance_requires_auditable_strong_grounds(family):
    fact = {'text': 'An invented conclusion', 'status': 'accepted', 'accepted': True,
            'weight': .9, 'sources': ['memory-name'], 'basis': 'A record', 'decision': 'Compared'}
    edit(family, 'feeds/ferrolho/chapters.json', lambda cs: cs[0]['facts'].append(fact))
    assert not evaluate(family)['blocked']
    edit(family, 'feeds/ferrolho/chapters.json', lambda cs: cs[0]['facts'][-1].update(weight=.05, status='possible'))
    assert evaluate(family)['blocked']


def test_f5_undeclared_reader_fields_stay_private(family, monkeypatch, capsys):
    row = {'id': 'fictional-letter', 'text': 'PRIVATE LETTER'}
    shown = scan(family, {'correspondence': row, 'people': {'p-amaro': {'id': 'p-amaro', 'name': 'Example', 'author': 'SECRET'}}}, 'graph')
    assert shown['people']['p-amaro']['name'] == 'Example' and all(word not in json.dumps(shown) for word in ('SECRET', 'PRIVATE LETTER'))
    import contextlib, io, subprocess, sys, textwrap
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
    assert runtime['handler'](event | {'body': json.dumps(private | {'page': '/', 'kind': 'confirm', 'subject': 'amendment:example'})}, None)['statusCode'] == 403
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


def test_f8_review_binds_exact_bytes(family, tmp_path):
    birthday = '1980-04-17'
    location = 'feeds/ferrolho/chapters.json'
    edit(family, location, lambda cs: cs[0]['records'][0].update(title='Private paper dated ' + birthday))
    material = publication(family, 'feeds', for_review=True)
    assert material.manifest['state'] == 'preview'
    ticket = review_ticket(material)
    with pytest.raises(ValueError, match='reviewer'):
        attest(family, 'feeds', reviewer='writer', author='writer', ticket=ticket)
    attest(family, 'feeds', reviewer='reader', author='writer', ticket=ticket)
    out = tmp_path / 'checked'
    service.build(family, out)
    packet = read_generation(family, out)
    assert {p.name for p in generation(family, out).iterdir()} == set(packet)
    assert json.loads(packet['status.json'])['ferrolho'] == {'output': {'state': 'clean', 'unreviewed': []}}
    assert all(birthday.encode() not in raw for raw in packet.values())
    edit(family, location, lambda cs: cs[0]['prose']['text'][0].update(text='A date copied elsewhere: ' + birthday))
    with pytest.raises(ValueError, match=r'feeds\.json contains wording from a withheld paper'):
        publication(family, 'feeds')
    edit(family, location, lambda cs: cs[0]['prose']['text'][0].update(text='Edited while reading'))
    with pytest.raises(ValueError, match='review material changed'):
        attest(family, 'feeds', reviewer='reader', author='writer', ticket=ticket)


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
