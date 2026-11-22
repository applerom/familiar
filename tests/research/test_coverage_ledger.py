import json
from pathlib import Path
from familiar.cli import main


def test_old_journals_carry_over_and_coverage_stays_private(family, capsys):
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
    imported = [json.loads(line) for line in next(family.path('searches').glob('legacy-*.jsonl')).read_text(encoding='utf-8').splitlines()]; assert imported[0]['origin']['line'] == 1 and imported[0]['origin']['path'].endswith('wave/SEARCHES.jsonl') and all(r['id'] == 'legacy-' + r['origin']['sha256'] for r in imported)
    from familiar.instance.gate import publication
    graph = lambda kind: json.loads(publication(family, kind, for_review=True).files()['graph.json'])['people']
    assert graph('reader-private')['p-rosa']['coverage']['found'] >= 1 and not any('coverage' in p for p in graph('reader').values())


def test_search_map_tells_reading_depth_and_keeps_line_open(family, capsys):
    run = lambda *a: (main(['--root', str(family.root), 'research', *a, '--line', 'Calhau', '--json']), json.loads(capsys.readouterr().out))[1]
    line = run('map')['lines'][0]; series = {s['id']: s['years'] for s in line['series']}
    assert (series['ponta-do-moinho-baptisms']['1900'], series['ponta-do-moinho-baptisms']['1903'], series['ponta-das-garcas-baptisms']['1901']) == ('full', 'surname', 'unknown')
    plan = run('plan')['lines'][0]
    assert plan['open_record']['years'] > 0 and 'Ponta do Moinho' in plan['open_record']['read_first'][0]['title'] and not any(p['state'] == 'exhausted' for p in plan['plays'])
