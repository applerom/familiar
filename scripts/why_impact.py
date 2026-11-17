"""Look up declared change impact; undeclared coupling still requires search."""
# START_MODULE_CONTRACT: MOD-GOVERN-IMPACT
# PURPOSE: Assemble declared consumers, guarantees and hidden coupling before an edit.
# PRD_REF: docs/PRD.md#DOD
# INVARIANTS:
# - lookup includes incoming edges, feature checks and reverse contracts [review: engine lead]
# - unknown targets fail explicitly [review: engine lead]
# CHANGES_WITH:
# - docs/why-layer.md (lookup promise)
# - MOD-GOVERN-VALIDATE-WHY (graph and contract vocabulary)
# :END_MODULE_CONTRACT
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def lookup(root: Path, target: str) -> dict[str, list[str]]:
    root = root.resolve()
    nodes, owners, contracts = {}, {}, {}
    for path in [root / 'docs/why-graph.xml', *sorted((root / 'docs/why-graph').glob('*.xml'))]:
        graph = ET.parse(path).getroot()
        for node in graph.iter():
            ident = node.get('ID')
            if ident:
                nodes[ident] = node
                owners[ident] = ident if ident.startswith('CAP-') else graph.get('CAPABILITY')
    for ident, node in nodes.items():
        if not ident.startswith('MOD-') or not node.get('FILE'):
            continue
        path = root / node.get('FILE')
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8-sig')
        match = re.search(r'START_MODULE_CONTRACT:.*?\n(.*?):END_MODULE_CONTRACT', text, re.DOTALL)
        if match:
            contracts[ident] = re.sub(r'(?m)^\s*#\s?', '', match[1])
    key = target.replace('\\', '/')
    if Path(target).is_absolute():
        try:
            key = Path(target).resolve().relative_to(root).as_posix()
        except ValueError:
            pass
    selected = {i for i, n in nodes.items() if i == key or n.get('FILE') == key
                or any((r.text or '').strip() in {key, 'docs/PRD.md#' + key}
                       for r in n.findall('PRD_REF'))
                or re.search(r'(?m)^PRD_REF:\s*(?:docs/PRD.md#)?' + re.escape(key) + r'\s*$',
                             contracts.get(i, ''))}
    if not selected:
        raise ValueError(f'Unknown module, path, feature or PRD key: {target}')
    features = {i for i, n in nodes.items() if i.startswith('FEAT-') and
                (i in selected or any(r.get('TYPE') == 'IMPLEMENTED_BY' and
                                     r.get('TARGET') in selected for r in n.findall('REL')))}
    modules = {i for i in selected if i.startswith('MOD-')}
    for feature in features & selected:
        modules.update(r.get('TARGET') for r in nodes[feature].findall('REL')
                       if r.get('TYPE') == 'IMPLEMENTED_BY')
    scope = selected | modules
    capabilities = {owners[i] for i in scope if owners[i]}
    result = {k: [] for k in ('Targets', 'Depends on / outgoing', 'Consumers / incoming',
                              'Features and invariants', 'Tests', 'Contracts naming target',
                              'Declared changes with', 'PRD keys')}

    def label(ident):
        node = nodes[ident]
        return ident + (f" ({node.get('FILE')})" if node.get('FILE') else '')

    result['Targets'] = [label(i) for i in sorted(scope)]
    for ident, node in nodes.items():
        for rel in node.findall('REL'):
            dest, kind = rel.get('TARGET'), rel.get('TYPE')
            if kind in {'COVERS', 'IMPLEMENTED_BY'}:
                continue
            edge = f'{label(ident)} --{kind}--> {label(dest)}'
            if ident in scope or ident in capabilities:
                result['Depends on / outgoing'].append(edge)
            if dest in scope or dest in capabilities:
                result['Consumers / incoming'].append(edge)
    for feature in sorted(features):
        result['Features and invariants'].append(feature)
        for inv in nodes[feature].findall('INVARIANT'):
            result['Features and invariants'].append(f"{feature}: {inv.text} [{inv.get('TEST') or 'review: ' + str(inv.get('REVIEW'))}]")
            if inv.get('TEST'):
                result['Tests'].append(inv.get('TEST'))
    aliases = scope | {nodes[i].get('FILE') for i in scope}
    for ident, block in contracts.items():
        coupling = block.partition('CHANGES_WITH:')[2]
        for line in coupling.splitlines():
            value = line.strip().removeprefix('- ').split(' (', 1)[0]
            if value in aliases:
                result['Contracts naming target'].append(f'{label(ident)}: {line.strip()}')
            if ident in modules and value:
                result['Declared changes with'].append(f'{ident}: {value}')
        if ident in modules:
            result['Tests'].extend(re.findall(r'\[test:\s*([^\]]+)\]', block))
    for ident in scope | features | capabilities:
        result['PRD keys'].extend((r.text or '').strip() for r in nodes[ident].findall('PRD_REF'))
        result['PRD keys'].extend(re.findall(r'(?m)^PRD_REF:\s*(\S+)', contracts.get(ident, '')))
    for group, values in result.items():
        result[group] = sorted(set(values))
    # Multiple fixed strings keep the command usable in PowerShell too.
    terms = sorted({*scope, *(nodes[i].get('FILE') for i in modules)} - {None, ''})
    terms = sorted(set(terms) | {part.lower() for ident in scope
                                for part in ident.split('-')[1:] if len(part) > 3})
    quote = lambda s: "'" + s.replace("'", "'\"'\"'") + "'"
    result['Search'] = [
        'rg -n --hidden -i -F ' + ' '.join('-e ' + quote(t) for t in terms)
        + ' -g ' + quote('!.git/**') + ' .']
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target')
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = lookup(args.repo_root, args.target)
    except (ValueError, OSError, ET.ParseError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for group, lines in result.items():
            print(group + ':')
            print('\n'.join('  ' + line for line in lines) if lines else '  (none declared)')
        print('Limit: direct declared links only; imports, undeclared coupling and runtime semantics '
              'require source search. Add target vocabulary to the search above.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
