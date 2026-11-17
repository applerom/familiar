# START_MODULE_CONTRACT: MOD-RULES-CLI
# PURPOSE: Give a role the rules that apply to it, resolved for its family and feed, so no role has to read a rule book.
# PRD_REF: docs/PRD.md#ROLES
# INVARIANTS:
# - the size of what a role receives is printed together with it [review: engine lead]
# - without a family root the commands answer with engine defaults [review: engine lead]
# CHANGES_WITH:
# - MOD-CLI (registered there by module name, not by import)
# - MOD-RULES-ROLES (role ids and method resource layout)
# - pyproject.toml (bundled method)
# :END_MODULE_CONTRACT
import json
import sys
from dataclasses import asdict
from pathlib import Path

from familiar.instance.root import RootNotFound, find_root

from .cascade import Registry
from .exceptions import report, waive
from .model import RulesError, require
from .roles import ROLES, method_root


def register(commands):
    parser = commands.add_parser('rules')
    parser.add_argument('--engine', type=Path, default=method_root() / 'rules', help='engine rule data directory')
    subs = parser.add_subparsers(dest='action', required=True)
    subs.add_parser('check')
    role = subs.add_parser('for')
    role.add_argument('role')
    role.add_argument('--feed')
    role.add_argument('--json', action='store_true')
    explain = subs.add_parser('explain')
    explain.add_argument('id')
    explain.add_argument('--scope')
    exception = subs.add_parser('waive')
    exception.add_argument('rule')
    exception.add_argument('--scope', required=True)
    exception.add_argument('--reason', required=True)
    exception.add_argument('--by')
    subs.add_parser('report')
    parser.set_defaults(run=run)


def role_rules(registry, role, scope):
    require(role in ROLES, 'unknown role ' + role + '; valid ids: ' + ', '.join(ROLES))
    groups = {kind: [] for kind in ('trust', 'craft', 'taste', 'process')}
    for rule in registry.rules.values():
        if role not in rule['roles'] and '*' not in rule['roles']:
            continue
        groups[rule['kind']].append({
            'id': rule['id'], 'statement': rule['statement'],
            'check': rule['check'], 'serves': rule['serves'],
            'mode': asdict(registry.rule_mode(rule['id'], scope)),
            'settings': {ident: asdict(registry.resolve_setting(ident, scope))
                      for ident in rule['reads']}})
    return groups


def run(args):
    try:
        try:
            root = find_root(args.root)
        except RootNotFound:
            if args.root or __import__('os').environ.get('FAMILIAR_ROOT'):
                raise
            root = None
        registry = Registry(args.engine, root)
        if args.action == 'check':
            print('rules: valid')
        elif args.action == 'for':
            scope = f'feed:{args.feed}' if args.feed else None
            groups = role_rules(registry, args.role, scope)
            if args.json:
                output = json.dumps(groups, ensure_ascii=False, default=str, indent=2)
            else:
                lines = [f'# Rules for {args.role}']
                for kind, rules in groups.items():
                    lines.append(f'\n## {kind}')
                    for rule in rules:
                        lines.append(f"- {rule['id']} [{rule['mode']['value']}]: "
                                     + rule['statement'] + f" ({rule['check']})")
                        for ident, resolved in rule['settings'].items():
                            origin = (f" ({resolved['layer']})" if resolved['value'] !=
                                      registry.settings[ident]['default'] else '')
                            lines.append(f"  - {ident}: {resolved['value']}{origin}")
                output = '\n'.join(lines)
            print(output)
            print(f'{len((output + chr(10)).encode("utf-8"))} bytes', file=sys.stderr)
        elif args.action == 'explain':
            result = (registry.resolve_setting(args.id, args.scope) if args.id in
                      registry.settings else registry.rule_mode(args.id, args.scope))
            print(json.dumps(asdict(result), ensure_ascii=False, default=str, indent=2))
        elif args.action == 'waive':
            print(json.dumps(waive(registry, args.rule, args.scope, args.reason, args.by), ensure_ascii=False))
        else:
            print(json.dumps(report(registry), indent=2))
        return 0
    except (RulesError, RootNotFound, OSError, ValueError, TypeError, KeyError) as error:
        print(f'rules: {error}', file=sys.stderr)
        return 1
