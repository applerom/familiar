# START_MODULE_CONTRACT: MOD-METHOD-CLI
# PURPOSE: Read the installed role sheets and skills without opening a family or accepting paths.
# PRD_REF: docs/PRD.md#ROLES
# INVARIANTS:
# - resource kinds and identifiers are closed vocabularies; family state is never opened [review: engine lead]
# CHANGES_WITH:
# - MOD-RULES-ROLES (role ids and method resource root)
# - MOD-CLI (startup bypass and registration)
# - pyproject.toml (wheel method resources)
# :END_MODULE_CONTRACT
import sys

from familiar.rules.roles import ROLES, method_root

SKILLS = ('blind-check', 'branch-abroad', 'drawing', 'game', 'generation-review',
          'memory-first', 'research-versions', 'second-look', 'shot-card',
          'story-reading', 'story-scenario', 'story-text', 'translation', 'wide-hypotheses')


def register(commands):
    parser = commands.add_parser('method', help='Read bundled roles and skills; no family needed')
    actions = parser.add_subparsers(dest='method_action', required=True)
    actions.add_parser('list')
    show = actions.add_parser('show')
    show.add_argument('kind', choices=('role', 'skill'))
    show.add_argument('id', help='Identifier from method list; paths are not accepted')
    parser.set_defaults(run=execute)


def execute(args):
    if args.method_action == 'list':
        print('\n'.join(f'role {name}' for name in ROLES))
        print('\n'.join(f'skill {name}' for name in SKILLS))
        return 0
    allowed = ROLES if args.kind == 'role' else SKILLS
    if args.id not in allowed:
        print(f'Unknown {args.kind} id; use familiar method list. Paths are not accepted',
              file=sys.stderr)
        return 2
    resource = (method_root() / 'roles' / (args.id + '.md') if args.kind == 'role'
                else method_root() / 'skills' / args.id / 'SKILL.md')
    try:
        print(resource.read_text(encoding='utf-8'), end='')
        return 0
    except OSError:
        print('Bundled method resource is missing; reinstall the Familiar wheel', file=sys.stderr)
        return 2
