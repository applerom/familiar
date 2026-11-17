# START_MODULE_CONTRACT: MOD-TREE-CLI
# PURPOSE: Expose graph inspection and explicit family surname decisions to the host.
# PRD_REF: docs/PRD.md#FEATURES
# INVARIANTS:
# - comparison returns failure for a different baseline [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE (the shared family boundary contract)
# - docs/PRD.md#INSTANCE
# :END_MODULE_CONTRACT
import json
from pathlib import Path

from familiar.instance.model import Instance

from .builder import build
from .canonical import canonical, encode, stats


def register(commands):
    parser = commands.add_parser("tree")
    actions = parser.add_subparsers(dest="tree_action", required=True)
    for action in ("build", "stats"):
        sub = actions.add_parser(action)
        sub.add_argument("--output", type=Path)
        sub.add_argument("--compare", type=Path)
        sub.add_argument('--view', choices=('working', 'reader'), default='working',
                         help='Private working graph (default), or permission-filtered reader graph')
    person = actions.add_parser("person")
    person.add_argument("person")
    surname = actions.add_parser('surname', help='One reversible display spelling per clan')
    surname_actions = surname.add_subparsers(dest='surname_action', required=True)
    surname_set = surname_actions.add_parser('set')
    surname_set.add_argument('clan')
    surname_set.add_argument('--form', help='Spelling adopted in family memory; otherwise select by attributed sources')
    surname_set.add_argument('--variant', action='append', required=True,
                             help='Equivalent literal surname spelling; repeat for every variant')
    surname_set.add_argument('--person', action='append', default=[],
                             help='Limit the decision to these person ids; otherwise match equivalent surnames')
    parser.set_defaults(run=run)


def run(args):
    instance = Instance(args.root)
    if args.tree_action == 'surname':
        from .surnames import set_form
        try:
            print(json.dumps(set_form(instance, args.clan, args.form, args.variant, args.person),
                             ensure_ascii=False, indent=2))
            return 0
        except (ValueError, OSError, TypeError) as exc:
            print(str(exc))
            return 1
    if args.tree_action == "person":
        from .person import person
        try:
            print(json.dumps(person(instance, args.person), ensure_ascii=False, indent=2))
            return 0
        except ValueError as exc:
            print(str(exc))
            return 1
    try:
        data = build(instance, view=args.view)
    except ValueError as exc:
        print(str(exc))
        return 1
    errors = data.get("research", {}).get("contributions", {}).get("errors", [])
    if errors:
        print(json.dumps({"contribution_errors": errors}, ensure_ascii=False, indent=2))
        return 1
    result = encode(data)
    summary = stats(data)
    if args.output:
        from .builder import save
        save(instance, args.output, view=args.view)
    if args.compare:
        from familiar.instance.writer import generation
        if args.view == 'working' and (args.compare / 'working-tree.json').is_file():
            baseline = json.loads((args.compare / 'working-tree.json').read_text(encoding='utf-8'))['graph']
        else:
            path = generation(instance, args.compare) / 'graph.json' if args.compare.is_dir() else args.compare
            baseline = json.loads(path.read_text(encoding='utf-8'))
        summary["matches"] = canonical(data) == canonical(baseline)
    print(
        json.dumps(summary, indent=2)
        if args.tree_action == "stats" or args.output or args.compare
        else result
    )
    return 1 if summary.get("matches") is False else 0
