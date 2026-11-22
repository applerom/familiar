# START_MODULE_CONTRACT: MOD-RESEARCH-CLI
# PURPOSE: Expose research forms, search forms by key, the identity score, source coverage, line plans, the search map, offline replay, and research delivery.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - packet failures return an error without writing family data [review: engine lead]
# - replay refusals explain permission and region recipe requirements without a traceback [review: engine lead]
# - journal migration is a dry run unless --apply; coverage reads files only and stores JSON only with --save [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#FORMS
# - MOD-SOURCE-SEARCH
# - MOD-SEARCH-LEDGER
# - MOD-RESEARCH-COVERAGE
# - MOD-MATCH-SCORE
# - MOD-SEARCH-MAP
# :END_MODULE_CONTRACT
import json
import sys
from pathlib import Path

from familiar.instance.model import Instance

from .packet import packet


def register(commands):
    parser = commands.add_parser('research')
    actions = parser.add_subparsers(dest='action', required=True)
    template = actions.add_parser('form')
    template.add_argument('name', help='memory.toml, paper.toml or a JSON form: search-request, capture, documents, chapters, evidence (JSON suffix optional)')
    template.set_defaults(run=print_form)
    review = actions.add_parser('validate-review')
    review.add_argument('input', type=Path)
    vocabulary = actions.add_parser('vocabulary')
    vocabulary.set_defaults(run=print_vocabulary)
    contribution = actions.add_parser('contribute', help='Apply a sourced contribution or documentary decision JSON')
    contribution.add_argument('input', type=Path)
    doc = actions.add_parser('document', help='Attach a literal corpus record and captioned cut-outs to people')
    doc.add_argument('input', type=Path)
    doc.add_argument('--author', required=True)
    replay = actions.add_parser('replay', help='Replay a local captured response; no network access')
    replay.add_argument('--request', required=True, type=Path)
    replay.add_argument('--capture', required=True, type=Path)
    replay.add_argument('--allow-replay', action='store_true', help='Explicit host permission for this family replay')
    command = actions.add_parser('packet')
    selection = command.add_mutually_exclusive_group(required=True)
    selection.add_argument('--case')
    selection.add_argument('--people', nargs='+')
    command.add_argument('--mode', choices=['owner', 'second-look'], default='owner')
    command.add_argument('--stage', choices=['evidence', 'argument'], default='evidence')
    command.add_argument('--max-chars', type=int, default=24000)
    command.add_argument('--json', action='store_true')
    card = actions.add_parser('person', help='One private discovery card with relatives, namesakes and local source locators')
    card.add_argument('person', help='Exact tree ID or a name, including a person absent from the tree')
    card.add_argument('--alias', action='append', default=[], help='Additional recorded spelling; repeatable')
    card.add_argument('--relative', action='append', default=[], help='Tree ID to search as a candidate relative; does not assert kinship')
    card.add_argument('--catalog', type=Path, help='Read-only trial of a TOML research.person_card configuration')
    card.add_argument('--max-chars', type=int, default=800000)
    card.add_argument('--inline', action='store_true', help='Repeat literal data values instead of sharing them within the card')
    card.add_argument('--full', action='store_true', help='Include literal bodies and import envelopes instead of the compact reading card')
    card.add_argument('--observation', type=int, help='Read one overview row by its zero-based index, with literal body and original locators')
    migrate = actions.add_parser('migrate-searches', help='One-time: add people, catalogue source and parsed executor to old search journal rows (dry run unless --apply)')
    migrate.add_argument('--apply', action='store_true', help='Write the migrated journals through the family writer')
    migrate.add_argument('--executors', metavar='FILE', help='JSON map of executor labels or prefixes to recorded model and effort')
    migrate.add_argument('--legacy', action='append', metavar='PATH', help='Legacy SEARCHES*.jsonl file or directory inside the family (default: research/team)')
    cover = actions.add_parser('coverage', help='Searches, read records and remaining gaps by person, source or family line')
    cover.add_argument('--person', help='One person: every source with dates and executors')
    cover.add_argument('--family', action='store_true', help='The whole person-by-source matrix (the default)')
    cover.add_argument('--recheck', nargs='?', type=int, const=15, metavar='N', help='The N most useful cells to look at again (default 15)')
    cover.add_argument('--line', help='Limit --recheck to one surname line or its starting person ID')
    cover.add_argument('--lines', action='store_true', help='Ancestral chains, open questions and coverage gaps by surname line')
    cover.add_argument('--json', action='store_true', help='JSON instead of markdown')
    cover.add_argument('--save', action='store_true', help='Also store the matrix and full queue in coverage.json in the instance state directory')
    plan = actions.add_parser('plan', help='Research approaches and next step for each family line')
    plan.add_argument('--line', help='Surname line or its starting person ID')
    plan.add_argument('--json', action='store_true', help='JSON instead of markdown')
    plan.set_defaults(run=run_plan)
    smap = actions.add_parser('map', help='The search map: record series year by year, name bases, and the empty cells ranked')
    smap.add_argument('--line', help='Surname line or its starting person ID')
    smap.add_argument('--json', action='store_true', help='JSON instead of markdown')
    smap.set_defaults(run=run_map)
    forms = actions.add_parser('forms', help='Search forms of names or places: dictionary forms, then forms the family wrote that share the key (suggestions)')
    forms.add_argument('words', nargs='+')
    forms.add_argument('--kind', choices=['surname', 'place', 'given_name'], default='surname')
    forms.add_argument('--year', type=int)
    forms.add_argument('--json', action='store_true')
    forms.set_defaults(run=run_forms)
    match = actions.add_parser('compare', help='Score one person or two: {"a", "b"} or {"target", "candidates"}, optional "pool"; never merges')
    match.add_argument('input', type=Path)
    match.add_argument('--json', action='store_true')
    match.set_defaults(run=run_compare)
    parser.set_defaults(run=run)
    migrate.set_defaults(run=run_migrate)
    cover.set_defaults(run=run_coverage)
    template.set_defaults(run=print_form)
    review.set_defaults(run=validate_review)
    card.set_defaults(run=run_person)
    contribution.set_defaults(run=deliver)
    doc.set_defaults(run=deliver)
    replay.set_defaults(run=run_replay)


def run_replay(args):
    from .search_host import SingleFamilyHost
    from .source_search import search
    try:
        if not args.allow_replay:
            raise ValueError('Повтор не разрешён: добавьте --allow-replay после разрешения хозяина для этой семьи.')
        instance = Instance(args.root)
        request = json.loads(args.request.read_text(encoding='utf-8-sig'))
        capture = json.loads(args.capture.read_text(encoding='utf-8-sig'))
        if not isinstance(request, dict) or not isinstance(capture, dict):
            raise TypeError('Запрос и захват должны быть JSON-объектами; примеры: research form search-request и research form capture.')
        request.pop('_about', None)
        host = SingleFamilyHost(instance.id, lambda url: capture, allow=True)
        print(json.dumps(search(instance, host=host, **request), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research replay: {exc}', file=sys.stderr)
        return 1


def run_migrate(args):
    from .search_ledger import migrate
    try:
        print(json.dumps(migrate(Instance(args.root), apply=args.apply, executors=args.executors, legacy=args.legacy), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research migrate-searches: {exc}', file=sys.stderr)
        return 1


def run_coverage(args):
    from .coverage import coverage
    try:
        if args.line is not None and (args.recheck is None or args.lines or args.person):
            raise ValueError('--line goes with --recheck')
        data, text = coverage(Instance(args.root), person=args.person, queue=args.recheck, lines=args.lines, save=args.save,
                              line=args.line)
        print(json.dumps(data, ensure_ascii=False, indent=1) if args.json else text)
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research coverage: {exc}', file=sys.stderr)
        return 1


def run_forms(args):
    from .search_variants import forms
    try:
        data = forms(Instance(args.root), args.words, args.kind, args.year)
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=1))
        for word, rows in ({} if args.json else data).items():
            table = [r['text'] for r in rows if r['via'] in {'word', 'dictionary'}]
            print(f"{word}: {', '.join(table)}")
            if clan := [r['text'] for r in rows if r['via'] == 'clan']:
                print(f"  by clan decision {next(r['from'] for r in rows if r['via'] == 'clan')}: {', '.join(clan)}")
            for r in rows:
                if r['via'] == 'key':
                    print(f"  by key ({r['key']}, {r['from']}): {r['text']}")
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research forms: {exc}', file=sys.stderr)
        return 1


def run_compare(args):
    from .match_score import compare, rank
    try:
        data = json.loads(args.input.read_text(encoding='utf-8-sig'))
        instance = Instance(args.root)
        result = (rank(instance, data['target'], data['candidates'], data.get('pool')) if 'target' in data else
                  compare(instance, data['a'], data['b'], data.get('pool')))
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=1))
        elif 'target' in data:
            for row in result['candidates']:
                print(f"{row['id']}: share {row['share']:.3f}, weight {row['weight']:.3f}; {row['words']}")
            print(f"unseen: {result['unseen']['count']} men of the pool {result['pool']}, share {result['unseen']['share']:.3f}")
        else:
            print(f"weight {result['weight']:.3f} among {result['pool']} ({result['pool_basis']}); {result['words']}")
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research compare: {exc}', file=sys.stderr)
        return 1


def run_plan(args):
    from .research_plan import plan
    try:
        data, text = plan(Instance(args.root), line=args.line)
        print(json.dumps(data, ensure_ascii=False, indent=1) if args.json else text)
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research plan: {exc}', file=sys.stderr)
        return 1


def run_map(args):
    from .search_map import search_map
    try:
        data, text = search_map(Instance(args.root), line=args.line)
        print(json.dumps(data, ensure_ascii=False, indent=1) if args.json else text)
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research map: {exc}', file=sys.stderr)
        return 1


def deliver(args):
    from .delivery import contribute, document
    try:
        data = json.loads(args.input.read_text(encoding='utf-8-sig'))
        instance = Instance(args.root)
        result = (document(instance, data, args.input, args.author) if args.action == 'document'
                  else contribute(instance, data))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research {args.action}: {exc}', file=sys.stderr)
        return 1


def run_person(args):
    from .person_card import person_card
    try:
        result = person_card(Instance(args.root), args.person, catalog=args.catalog,
                             aliases=args.alias, relatives=args.relative, max_chars=args.max_chars, inline=args.inline, full=args.full, observation_index=args.observation)
        print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research person: {exc}', file=sys.stderr)
        return 1


def print_vocabulary(args):
    from familiar.instance.research_forms import VOCABULARY
    print(json.dumps(VOCABULARY, ensure_ascii=False, indent=2))
    return 0


def validate_review(args):
    print('Review completeness is judged by the reader; method form lint was removed.')
    return 0


def print_form(args):
    from familiar.rules.roles import method_root
    base = method_root().parent
    directory = base / ('_forms' if (base / '_forms').exists() else 'forms')
    name = args.name if Path(args.name).suffix else args.name + '.json'
    path = directory / name
    if Path(name).name != name or not path.is_file():
        print('Unknown form; available: ' + ', '.join(p.name for p in directory.iterdir()), file=sys.stderr)
        return 1
    print(path.read_text(encoding='utf-8'), end='')
    return 0


def run(args):
    try:
        result = packet(Instance(args.root), case=args.case, people=args.people or (), mode=args.mode, stage=args.stage, max_chars=args.max_chars)
        if not args.json:
            print('Line packet: primary evidence first; omission manifest is mandatory.')
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research: {exc}', file=sys.stderr)
        return 1
