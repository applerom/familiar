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
    from familiar.desk.model import words
    from familiar.desk.search_map import project
    people = family.path('tree_snapshot') / 'people.json'
    tree = json.loads(people.read_bytes())
    next(p for p in tree['people'] if p['id'] == 'p-daniel')['names'].extend([{'display': 'Daniel'}, {'display': 'Amaro Ferrolho'}])
    people.write_text(json.dumps(tree), encoding='utf-8')
    path = family.path('access')
    ledger = json.loads(path.read_bytes())
    ledger['places'][0]['books'][1].update(title='Daniel Pike in the register', look_for='Daniel asks about Amaro Ferrolho')
    path.write_text(json.dumps(ledger), encoding='utf-8')
    shown = project(family, words(family))['desk/search-map.html'].decode()
    assert 'books 5-6' in shown and 'Daniel Pike' not in shown and 'Daniel asks about Amaro Ferrolho' in shown
    assert main(['--root', str(family.root), 'research', 'plan', '--line', 'Calhau']) == 0 and 'Daniel Pike' not in capsys.readouterr().out
    run = lambda *a: (main(['--root', str(family.root), 'research', *a, '--line', 'Calhau', '--json']), json.loads(capsys.readouterr().out))[1]
    line = run('map')['lines'][0]; series = {s['id']: s['years'] for s in line['series']}
    assert (series['ponta-do-moinho-baptisms']['1900'], series['ponta-do-moinho-baptisms']['1903'], series['ponta-das-garcas-baptisms']['1901']) == ('full', 'surname', 'unknown')
    plan = run('plan')['lines'][0]
    assert plan['open_record']['years'] > 0 and 'Ponta do Moinho' in plan['open_record']['read_first'][0]['title'] and not any(p['state'] == 'exhausted' for p in plan['plays'])


def test_access_ledger_steers_plan_and_check(family, capsys):
    run = lambda *a: (main(['--root', str(family.root), 'research', *a]), capsys.readouterr().out)
    record = lambda *a: json.loads(run('access', 'record', *a, '--by', 'collector-a', '--at', '2026-11-24')[1])
    family.path('series').unlink()
    assert record('--id', 'a1', '--state', 'copy', '--price', '2 a page')['years'] == '1880-1910'  # only the given fields change
    copy = json.loads(run('plan', '--line', 'Calhau', '--json')[1])['lines'][0]; assert copy['next'].startswith('Order a copy: Baptisms') and '2 a page' in copy['next'] and all(p['state'] != 'no-access' for p in copy['plays'])
    record('--id', 'a1', '--needs', 'sheet numbers'); assert 'Find out: sheet numbers' in run('plan', '--line', 'Calhau')[1] and '# Copies to order' in run('access', '--order')[1]
    record('--id', 'a1', '--needs', '', '--price', '', '--state', 'letter')
    missing = lambda: {p['id']: p['missing'] for p in json.loads(run('plan', '--line', 'Calhau', '--json')[1])['lines'][0]['plays']}
    assert missing()['forums'] == ['parish'] and record('--id', 'a1', '--title', 'Baptisms of the parish church') and not missing()['forums']
    page = family.root / 'research/ACCESS.md'; page.write_text('by hand', encoding='utf-8'); assert run('access', '--markdown', '--save')[0] == 1 and page.read_text() == 'by hand'; page.unlink(); assert run('access', '--markdown', '--save')[0] == 0 and run('access', 'note', 'What we read.')[0] == 0
    record('--id', 'a1', '--note', 'two volumes'); shown = page.read_text(encoding='utf-8'); assert 'What we read.' in shown and 'two volumes' in shown and 'collector-a, 2026-11-24' in shown
    line = json.loads(run('plan', '--line', 'Calhau', '--json')[1])['lines'][0]
    states = {p['id']: p['state'] for p in line['plays']}
    assert states['place-nest'] == 'no-access' and line['next'].startswith('Order in the reading room: Baptisms 1911–1915')
    note = family.root / 'research/STRATEGY.md'; note.write_text('# Plan\n\nThe Calhau line is exhausted.\n', encoding='utf-8')
    from familiar.instance.validation import check
    said = lambda: [a['message'] for a in check(family)['advice'] if a['location'].startswith(str(note))]
    assert 'Ponta do Moinho, Ilha Vaqueira 3' in said()[0]
    note.write_text('The Calhau line: name bases are exhausted; the parish books are unread.\n', encoding='utf-8'); assert not said()
    assert record('--place', 'Ponta do Moinho', '--kind', 'parish', '--years', '1911-1915', '--state', 'read')['id'] == 'a2'
    assert record('--id', 'a1', '--state', 'home') and 'no-access' not in run('plan', '--line', 'Calhau', '--json')[1]
    assert run('access', 'record', '--id', 'a9', '--state', 'read', '--by', 'x')[0] == 1
