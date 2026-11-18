import json
from pathlib import Path
from shutil import copytree
from familiar.cli import main


def test_old_journal_to_matrix_and_recheck_queue(family, capsys):
    base = {'at': '2026-11-10', 'question': 'rosa-birthplace', 'query': {'surname': 'Calhau', 'given': 'Rosa'}, 'hits': 0, 'coverage': {'years': '1800-1900', 'forms': ['Calhau'], 'read': 1}}
    rows = [dict(base, by='collector-a / GPT-6.2 Sol high', source='Geneteka', hits=1), dict(base, by='collector-b / GPT-6.1 Terra medium', source='FamilySearch', control='Amaro found'),
            dict(base, by={'agent': 'collector-c', 'model': 'codex', 'effort': None, 'provider': 'codex'}, source='MyHeritage', people=['p-rosa', 'p-amaro'], people_basis='inferred', people_from='question')]
    journal = family.path('searches') / 'old.jsonl'; journal.write_text('\n'.join(json.dumps(r) for r in rows), encoding='utf-8')
    executors = family.root.parent / 'executors.json'; executors.write_text(json.dumps({'collector-c': {'model': 'gpt-6.2-sol', 'effort': 'high'}}), encoding='utf-8')
    archive = family.root / 'research/team/wave/SEARCHES.jsonl'; archive.parent.mkdir(parents=True)
    archive.write_text('\n'.join(json.dumps(r) for r in [dict(base, by='collector-c', source='represii-by', state='refused', read=1)] * 2 + [dict(base, by='collector-c', source='geni', coverage={}, hits='0'), rows[0], {'query': 'broken'}]) + '\n{broken', encoding='utf-8'); original = archive.read_bytes()
    run = lambda *a: (main(['--root', str(family.root), 'research', *a]), capsys.readouterr().out)[1]
    args = ('migrate-searches', '--executors', str(executors)); dry = json.loads(run(*args)); applied = json.loads(run(*args, '--apply'))
    assert (dry['legacy_imported'], applied['executor_rows'], applied['people_refined'], applied['legacy_duplicates'], applied['legacy_unparsed']) == (2, 3, 1, 2, 2)
    assert json.loads(run(*args))['files'] == 0 and archive.read_bytes() == original
    done = [json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines()]; assert done[2]['people'] == ['p-rosa'] and done[2]['by_basis'] == 'executor-map' and done[2]['by']['provider'] == 'codex'
    cells = next(p for p in json.loads(run('coverage', '--json', '--save'))['people'] if p['id'] == 'p-rosa')['cells']
    assert [(cells[k]['outcome'], cells[k]['strength']) for k in ('geneteka', 'familysearch', 'myheritage', 'represii-by')] == [('found', 3), ('zero-controlled', 1), ('zero-uncontrolled', 3), ('gap', 0)]
    imported = [json.loads(line) for line in next(family.path('searches').glob('legacy-*.jsonl')).read_text(encoding='utf-8').splitlines()]; assert imported[0]['origin']['line'] == 1 and imported[0]['origin']['path'].endswith('wave/SEARCHES.jsonl') and all(r['id'] == 'legacy-' + r['origin']['sha256'] for r in imported)
    assert cells['geni']['outcome'] == 'zero-uncontrolled'
    from familiar.research.coverage import applicability, collect, outcome, person_card, recheck
    from familiar.research.coverage_context import row_people, life_window, record_visits
    assert row_people(dict(base, people=['p-rosa'], people_from='question', query={'surname': 'Ferrolho', 'place': 'Lajedo do Vento, Ilha Vaqueira'}), collect(family)['tree'], collect(family)['resolver'].catalog) == (['p-amaro', 'p-joaquina'], 'surname-place', 'surname')
    assert life_window({'notes': [{'text': 'Родился в мае 1935 года (по памяти)'}]}) == (1935, 2055)
    assert outcome(dict(base, coverage=base['coverage'] | {'note': 'Контроль Amaro успешен в этой серии'})) == 'zero-controlled'
    record = family.path('records') / 'coverage-visit.json'; record.write_text(json.dumps({'source': 'obd-memorial', 'person': {'id': 'p-rosa'}, 'fields': {'name': 'Rosa Calhau'}}), encoding='utf-8')
    data = collect(family); visit = next(s for s in person_card(data, 'p-rosa')['sources'] if s['id'] == 'obd-memorial')
    assert visit['records'] == ['records/coverage-visit.json'] and not visit['identified'] and not visit['plan_complete'] and not cells['geneteka']['identified']
    resolver = data['resolver']; assert [resolver.row_source({'source': 'familysearch', 'query': {'url': u}}) for u in ['https://familysearch.org/tree/person/A', 'https://familysearch.org/search/record/results', 'https://familysearch.org/search/full-text']] == ['familysearch-tree', 'familysearch-records', 'familysearch-fulltext'] and resolver.row_source({'source': 'web-search', 'query': 'FamilySearch Records Rosa'}) == 'web-search'
    data = collect(family); data['tree'].graph['people']['p-rosa']['events'] = [{'type': 'birth', 'date': '1800', 'place': 'Polska'}, {'type': 'death', 'date': '1860'}]
    data['resolver'].catalog.sources['represii-by'] = {'years': [1917, 1991], 'countries': ['BY']}; data['resolver'].catalog.coverage_places = [{'aliases': ['Polska'], 'countries': ['PL']}]
    data['not_applicable'] = {(p, s): applicability(data, p, s) for p in data['focus'] for s in data['sources']}; card = person_card(data, 'p-rosa')
    assert {'id': 'represii-by', 'reasons': ['epoch', 'region']} in card['not_applicable'] and all(s['id'] != 'represii-by' for s in card['never_looked']) and not any(q['person'] == 'p-rosa' and q['source'] == 'represii-by' for q in recheck(data))
    from familiar.instance.gate import publication
    graph = lambda kind: json.loads(publication(family, kind, for_review=True).files()['graph.json'])['people']
    assert graph('reader-private')['p-rosa']['coverage']['found'] >= 1 and not any('coverage' in p for p in graph('reader').values())
    original = {'source': {'url': 'https://obd-memorial.ru/record/alpha'}, 'person': {'name': 'Rosa', 'surname': 'Calhau'}, 'subjects': [{'person': 'p-amaro', 'role': 'candidate'}]}; record.write_text(json.dumps(original), encoding='utf-8'); data = collect(family); tree = data['tree']
    tree.graph['sources']['alpha'] = {'record': 'coverage-visit', 'url': original['source']['url']}; tree.graph['people']['p-rosa']['facts'].append({'status': 'verified', 'sources': ['alpha']})
    linked = next(v for v in record_visits(family, tree, data['resolver']) if v['record'] == 'records/coverage-visit.json')['links']
    assert linked['p-rosa']['status'] == 'same' and linked['p-amaro']['status'] == 'other'
    record.write_text(json.dumps(original | {'subjects': [{'person': 'p-amaro', 'role': 'co-defendant-candidate'}]}), encoding='utf-8'); assert next(v for v in record_visits(family, tree, data['resolver']) if v['record'] == 'records/coverage-visit.json')['links']['p-amaro']['status'] == 'mention'
    analysis = family.path('records') / 'comparison.json'; analysis.write_text(json.dumps({'source': 'obd-memorial', 'fields': {'comparisons': [{'target_ids': ['p-rosa'], 'record': 'coverage-visit', 'weights': {'same': 0.1}}]}}), encoding='utf-8')
    review = dict(base, id='local-review', people=['p-rosa'], source='obd-memorial', by={'agent': 'reviewer', 'model': 'gpt-6.2-sol', 'effort': 'xhigh'}, query={'mode': 'review'}, hits=0, record_links=[{'person': 'p-rosa', 'record': 'coverage-visit', 'status': 'same'}]); before = next(s for s in person_card(collect(family), 'p-rosa')['sources'] if s['id'] == 'obd-memorial')
    (family.path('searches') / 'review.jsonl').write_text(json.dumps(review), encoding='utf-8'); after = next(s for s in person_card(collect(family), 'p-rosa')['sources'] if s['id'] == 'obd-memorial')
    assert after['identity'] == 'same' and not after['identified'] and after['records'] == ['records/coverage-visit.json'] and all(after[k] == before[k] for k in ['strength', 'passes', 'plan_complete', 'forms', 'availability', 'last'])
    assert outcome(review) == outcome(review | {'query': {'review': 'saved records'}}) == 'none' and any(q['person'] == 'p-rosa' and q['source'] == 'obd-memorial' and q['action'] == 'search' for q in recheck(collect(family)))


def test_collateral_modes_and_line_fronts(tmp_path, capsys):
    root = copytree(Path(__file__).parent / 'fixtures/line-fronts', tmp_path / 'family')
    config = root / 'familiar.toml'
    default = config.read_text(encoding='utf-8')
    for mode in ('hints', 'off', 'full'):
        chosen = f'"research.collateral" = "{mode}"\n"research.main_lines" = ["Морецкий", "Луногравова"]\n'
        config.write_text(default + ('' if mode == 'hints' else chosen), encoding='utf-8')
        assert main(['--root', str(root), 'research', 'coverage', '--lines', '--json', '--save']) == 0, capsys.readouterr().err
        lines = json.loads(capsys.readouterr().out)['lines']
        matrix = json.loads((root / '.state/coverage.json').read_bytes())
        side = matrix['collateral']
        assert [h['record'] for h in side['hints']] == ([] if mode == 'off' else ['records/side-record.json'])
        queue = [r['person'] for r in matrix['recheck']]
        expected = ['elder', 'father', 'root', 'spouse', 'spouse-father', 'sibling']
        expected.insert(2 if mode == 'hints' else len(expected), 'mother')
        assert queue == expected + (['cousin', 'grandchild', 'inlaw'] if mode == 'full' else [])
        assert [r['start']['id'] for r in lines] == (['root', 'spouse', 'mother'] if mode == 'hints' else ['spouse', 'root', 'mother'])
        assert [r['secondary'] for r in lines] == [False, False, mode != 'hints']
        paternal = next(r for r in lines if r['start']['id'] == 'root')
        assert [(p['id'], p['weight']) for p in paternal['chain']] == [('root', None), ('father', None), ('elder', .6)]
        assert [(v['question'], v['weight']) for v in paternal['versions']] == [('elder-parents', .7), ('elder-birthplace', .5)]
