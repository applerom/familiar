import json
from pathlib import Path

from familiar.cli import main


def test_kinship_case_keeps_research_and_its_evidence(tmp_path, capsys):
    case = Path(__file__).with_name('fixtures') / 'kinship-case'
    family = tmp_path / 'family'
    args = ['--root', str(family)]
    assert main([*args, 'instance', 'init', str(family)]) == 0
    capsys.readouterr()
    assert main([*args, 'intake', 'kinship-case', str(case), '--id', 'loom', '--apply']) == 0
    assert json.loads(capsys.readouterr().out)['tree_links'] == 1
    assert main([*args, 'tree', 'build']) == 0
    edge, = json.loads(capsys.readouterr().out)['edges']
    assert edge['status'] == 'hypothesis' and edge['weight'] < .3
    assert main([*args, 'research', 'coverage', '--person', 'kinship-loom-person-p1', '--json']) == 0
    assert {row['outcome'] for row in json.loads(capsys.readouterr().out)['sources']} >= {'zero-uncontrolled', 'gap'}
