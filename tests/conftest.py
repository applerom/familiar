"""Isolated fictional families; only data failures and the size budget block."""
import importlib.util
import json
import shutil
import time
from pathlib import Path

import pytest

from familiar.instance.model import Instance
from familiar.check_policy import decision, weight

REPO = Path(__file__).resolve().parents[1]
DEMO = REPO / 'demo'
_STARTED = time.monotonic()
spec = importlib.util.spec_from_file_location('validate_why', REPO / 'scripts/validate_why.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
_CPU_STARTED = validator.cpu_times()
_PROCESS_STARTED = time.process_time()


def pytest_addoption(parser):
    parser.addoption('--full', action='store_true', help='Include the isolated installed-wheel journey')
    parser.addoption('--busy-host', metavar='REASON', help='Declare known concurrent work; timing is advisory')


def pytest_collection_modifyitems(config, items):
    for item in items:
        if weight(item.nodeid) is None:
            import warnings
            warnings.warn(pytest.PytestWarning(f'CHECK ADVICE: no weight for {item.nodeid}'), stacklevel=1)
    if not config.getoption('--full'):
        excluded = [item for item in items if item.get_closest_marker('installed')]
        config.hook.pytest_deselected(items=excluded)
        items[:] = [item for item in items if item not in excluded]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    report = (yield).get_result()
    if report.failed and decision(item.nodeid) != 'block':
        import warnings
        warnings.warn(pytest.PytestWarning(f'CHECK ADVICE: {item.nodeid}: {report.longrepr}'), stacklevel=1)
        report.outcome = 'passed'


@pytest.fixture
def family(tmp_path):
    root = tmp_path / 'family'
    shutil.copytree(DEMO, root, ignore=shutil.ignore_patterns(
        '.state', '.secrets', 'state.json', 'desk-access.json'))
    # Publication guarantees start from a finished feed. The desk demo also
    # shows draft frames, which the draft-frame test adds at its own location.
    path = root / 'feeds/ferrolho/chapters.json'
    chapters = json.loads(path.read_bytes())
    for chapter in chapters:
        chapter['flow'] = [beat for beat in chapter['flow'] if 'placeholder' not in beat]
    path.write_text(json.dumps(chapters, ensure_ascii=False), encoding='utf-8')
    return Instance(root)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    # Explicit paths or marker/name filters do not measure a level's budget.
    if [Path(a).resolve() for a in config.args] not in ([REPO / 'tests'], [REPO]):
        return
    if config.option.markexpr or config.option.keyword:
        return
    figures = validator.budget_figures(REPO)
    seconds = time.monotonic() - _STARTED
    load = validator.competing_load(_CPU_STARTED, validator.cpu_times(), time.process_time() - _PROCESS_STARTED)
    busy = config.getoption('--busy-host')
    level = 'full' if config.getoption('--full') else 'fast'
    limit = figures['max_seconds' if level == 'full' else 'max_fast_seconds']
    terminalreporter.write_sep('-', (
        f"test budget: {figures['functions']} functions, {terminalreporter._session.testscollected} cases, "
        f"{figures['test_lines']}/{figures['code_lines']} test/code lines = {figures['ratio']:.2f} "
        f"(max {figures['max_ratio']}), {level} run {seconds:.1f} s (max {limit})"))
    terminalreporter.write_line(
        'competing CPU load: ' + (f'{load:.0%}' if load is not None else 'unavailable')
        + '; timing is advisory under every load')
    if busy:
        terminalreporter.write_line('declared concurrent work: ' + busy)
    if seconds > limit:
        terminalreporter.write_line('TIME WARNING: inspect cost before adding checks', yellow=True)
    if figures['ratio'] > figures['max_ratio']:
        terminalreporter.write_line(
            'OVER BUDGET: prune before adding; see docs/why-layer.md section 9',
            yellow=True, bold=True)
        if terminalreporter._session.exitstatus == pytest.ExitCode.OK:
            terminalreporter._session.exitstatus = pytest.ExitCode.TESTS_FAILED
