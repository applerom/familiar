"""Advise on broken explicit WHY references and missing core contracts."""
import argparse
import ast
import json
import re
import tomllib
import xml.etree.ElementTree as ET
from fnmatch import fnmatchcase
from pathlib import Path

TEST_DEF = re.compile(r"(?m)^(?:    )?def (test_\w+)")


def validate(root):
    root = root.resolve()
    findings = []

    def issue(file, ident, rule, message):
        findings.append(dict(file=str(file), id=ident, rule=rule, message=message,
                             severity='warning', weight='why.' + rule))

    def read(path):
        try:
            return path.read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError) as exc:
            issue(path, '<reference>', 'reference', str(exc))
            return ''

    def reference(value, file, ident):
        part, sep, key = value.partition('#')
        path = (root / part).resolve()
        if not part or not path.is_relative_to(root) or not path.exists():
            issue(file, ident, 'reference', f'Missing or nonlocal file: {value}')
        elif sep and (not path.is_file() or not re.search(
                rf'<!--\s*PRD_ANCHOR:\s*{re.escape(key)}\s*-->', read(path))):
            issue(file, ident, 'reference', f'Missing PRD key: {value}')

    try:
        policy = json.loads(read(root / 'src/familiar/check-weights.json'))
    except ValueError:
        policy = {}
        issue('src/familiar/check-weights.json', '<weights>', 'reference', 'Check weights unreadable; checks without weights advise')
    graphs, nodes, modules = [], set(), {}
    for file in [root / 'docs/why-graph.xml', *sorted((root / 'docs/why-graph').glob('*.xml'))]:
        try:
            graph = ET.fromstring(read(file))
        except ET.ParseError as exc:
            issue(file, '<graph>', 'reference', str(exc))
            continue
        graphs.append((file, graph))
        for node in graph.iter():
            if ident := node.get('ID'):
                nodes.add(ident)
            if value := node.get('FILE'):
                modules[value] = node.get('ID')
    for file, graph in graphs:
        for node in graph.iter():
            ident = node.get('ID', '<graph>')
            for attribute in ('FILE', 'SHARD'):
                if value := node.get(attribute):
                    if node.get('STATE') != 'PLANNED' or (root / value).exists():
                        reference(value, file, ident)
            if node.tag == 'PRD_REF':
                reference((node.text or '').strip(), file, ident)
            if node.tag == 'REL' and node.get('TARGET') not in nodes:
                issue(file, ident, 'reference', f"Unresolved ID: {node.get('TARGET')}")
            if value := node.get('TEST'):
                test_reference(value, file, ident, root, issue)
    paths = {p for directory in ('src', 'method', 'scripts') for p in (root / directory).rglob('*')
             if p.is_file() and p.suffix not in {'.pyc', '.pyo'}
             and not any(part.startswith('.') or part == '__pycache__' for part in p.relative_to(root).parts)}
    paths.update(root / p for p in modules if (root / p).resolve().is_relative_to(root) and (root / p).is_file())
    for path in sorted(paths):
        text = read(path)
        relative = path.relative_to(root).as_posix()
        core = any(fnmatchcase(relative, pattern) for pattern in policy.get('core_paths', []))
        if path.name == '__init__.py':
            try:
                body = ast.parse(text).body
            except SyntaxError:
                body = [None]
            if not body or (len(body) == 1 and isinstance(body[0], ast.Expr)):
                continue
        start = re.search(r'(?m)^\s*(?:#\s*)?START_MODULE_CONTRACT:\s*(\S+)', text)
        ident = start[1] if start else modules.get(relative, '<core>')
        if core and (not start or modules.get(relative) != ident or ':END_MODULE_CONTRACT' not in text):
            issue(relative, ident, 'core-contract', 'Core requires a module contract and matching graph node in the code commit')
        # No absence, envelope, field-order, duplicate-prose or holder lint for surfaces.
        if not start:
            continue
        text = text[start.end():].partition(':END_MODULE_CONTRACT')[0]
        for value in re.findall(r'(?m)^\s*(?:#\s*)?PRD_REF:\s*(\S+)', text):
            reference(value, relative, ident)
        for value in re.findall(r'\[test:\s*([^\]]+)\]', text):
            test_reference(value, relative, ident, root, issue)
        block = text.partition('CHANGES_WITH:')[2].partition(':END_MODULE_CONTRACT')[0]
        for line in block.splitlines():
            match = re.match(r'\s*(?:#\s*)?-\s*(\S+)', line)
            if not match:
                continue
            value = match[1]
            if re.fullmatch(r'(?:MOD|CAP|FEAT|UC)-[A-Z0-9-]+', value):
                if value not in nodes:
                    issue(relative, ident, 'reference', f'Unresolved CHANGES_WITH ID: {value}')
            else:
                reference(value, relative, ident)
    return findings


def test_reference(value, file, ident, root, issue):
    path, *names = value.strip().split('::')
    target = (root / path).resolve()
    try:
        if not target.is_relative_to(root) or not names:
            raise ValueError('Expected a local test path and definition')
        scope = ast.parse(target.read_text(encoding='utf-8-sig'))
        for name in names:
            scope = next(n for n in scope.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name)
    except (OSError, SyntaxError, StopIteration, ValueError, AttributeError) as exc:
        issue(file, ident, 'reference', f'Broken explicit test link: {value}: {exc}')


def budget_figures(root: Path) -> dict | None:
    """Test size and level budgets shared with tests/conftest.py."""
    try:
        limits = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["familiar"]["test-budget"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return None

    def lines(paths):
        return sum(1 for p in paths for line in p.read_text(encoding="utf-8").splitlines() if line.strip())
    tests = [p for p in (root / "tests").rglob("*.py") if "__pycache__" not in p.parts]
    code = [*(root / "src").rglob("*.py"), *(root / "scripts").glob("*.py")]
    test_lines, code_lines = lines(tests), lines(code)
    return {"functions": sum(len(TEST_DEF.findall(p.read_text(encoding="utf-8")))
                             for p in tests if p.name.startswith("test_")),
            "test_lines": test_lines, "code_lines": code_lines,
            "ratio": test_lines / max(code_lines, 1), "max_ratio": limits["max_test_code_ratio"],
            "max_seconds": limits["max_full_run_seconds"],
            "max_fast_seconds": limits.get("max_fast_run_seconds", limits["max_full_run_seconds"])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    findings = validate(args.repo_root)
    figures = budget_figures(args.repo_root)
    oversized = bool(figures and figures['ratio'] > figures['max_ratio'])
    if args.json:
        print(json.dumps(dict(ok=not oversized, findings=findings, budget=figures), indent=2))
    else:
        for f in findings:
            print(f"advice: {f['file']} [{f['id']}] {f['rule']}: {f['message']}")
        if figures:
            print(f"test budget: {figures['functions']} functions, {figures['test_lines']}/{figures['code_lines']} nonempty lines, ratio {figures['ratio']:.4f} (max {figures['max_ratio']}); timing advisory")
        print(f'WHY: {len(findings)} advice; ' + ('test size exceeded' if oversized else 'no blocking findings'))
    return int(oversized)


def cpu_times():
    """System idle/total seconds, or None when the host cannot measure load."""
    import os
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        idle, kernel, user = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            return None
        def seconds(value):
            return ((value.dwHighDateTime << 32) | value.dwLowDateTime) / 10_000_000
        return seconds(idle), seconds(kernel) + seconds(user)
    try:
        ticks = [int(n) / os.sysconf('SC_CLK_TCK')
                 for n in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
        return ticks[3] + ticks[4], sum(ticks)
    except (OSError, ValueError, AttributeError):
        return None


def competing_load(start, end, own_seconds):
    if start is None or end is None or end[1] <= start[1]:
        return None
    total = end[1] - start[1]
    busy = total - (end[0] - start[0])
    return max(0, (busy - own_seconds) / total)




if __name__ == "__main__":
    raise SystemExit(main())
