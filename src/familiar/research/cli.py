# START_MODULE_CONTRACT: MOD-RESEARCH-CLI
# PURPOSE: Expose research forms, amendment proposals, search forms by key, the identity score, source coverage, line plans, the search map, the access ledger, offline replay, and research delivery.
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
# - MOD-ACCESS-LEDGER
# :END_MODULE_CONTRACT
import json
import sys
from pathlib import Path

from familiar.instance.model import Instance

from .packet import packet


def register(commands):
    from .access_ledger import STATES
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
    doc = actions.add_parser('document', help='Save a literal corpus record and cut-outs for tree subjects or a place and surname')
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
    cover.add_argument('--family', action='store_true', help='The whole person-by-source matrix')
    cover.add_argument('--recheck', nargs='?', type=int, const=15, metavar='N', help='The N most useful cells to look at again (default 15)')
    cover.add_argument('--line', help='One surname line or its starting person ID; also filters --recheck')
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
    access = actions.add_parser('access', help='The access ledger: which books of a place exist, read or not, and how to reach them')
    access.add_argument('--line', help='Only places that name this surname line')
    access.add_argument('--place')
    access.add_argument('--order', action='store_true', help='The reading-room order list')
    access.add_argument('--json', action='store_true', help='JSON instead of markdown')
    access.add_argument('--markdown', action='store_true', help='The whole ledger as one page: every row with its verdict, copies to order, the reading-room list')
    access.add_argument('--save', action='store_true', help='With --markdown: write it beside the ledger (ACCESS.md); every later verdict renews it')
    access.set_defaults(run=run_access)
    commands = access.add_subparsers(dest='verdict')
    words = commands.add_parser('note', help='Words around the rows: the header, a section, a place or the reading-room list')
    words.add_argument('text', nargs='?', help='The words, or a JSON row by language; empty text removes them')
    words.add_argument('--file', type=Path, help='Read the words from a UTF-8 file')
    words.add_argument('--place', help='Words about this place; with --section also files it there')
    words.add_argument('--section', help='Title of a section of the print')
    words.add_argument('--room', action='store_true', help='Words above the reading-room list')
    words.add_argument('--title', help='Title of the page, or of the place in the print')
    words.set_defaults(run=run_access_note)
    verdict = commands.add_parser('record', help='Record one verdict; with --id only the given fields change. Words may be a JSON row by language')
    verdict.add_argument('--id', help='Row to change, as research access prints it')
    verdict.add_argument('--place', help='Village or parish')
    verdict.add_argument('--line', action='append', default=[], help='Surname line of the place; repeatable')
    verdict.add_argument('--kind', help='parish, revision, census, household, estate, civil, tax, voters, commission ... or your own word')
    verdict.add_argument('--state', choices=STATES, help='home: opens from home; copy: the archive sells a copy remotely; room: reading room only; letter: the archive answers letters; '
                         'unknown: not settled where it is; read; none: lost, or this holder has none')
    for name, text in (('title', 'What it is, if the kind is not enough'), ('years', '"1860-1918" or "1816; 1858"'),
                       ('holder', 'Archive'), ('reference', 'Call number'), ('online', 'Where it opens from home'),
                       ('unit', 'What --read counts: pages, years'), ('price', 'What a copy costs'),
                       ('needs', 'What is missing to order it, e.g. the sheet numbers of the village'), ('letter', 'Correspondence ID'),
                       ('look-for', 'What to look for in the reading room'), ('report', 'File of the verdict'), ('note', 'Note')):
        verdict.add_argument('--' + name, help=text)
    for name in ('read', 'of', 'order'):
        verdict.add_argument('--' + name, type=int)
    verdict.add_argument('--doubtful', action='store_true', default=None, help='Not sure the book holds our place: it neither opens nor closes the road')
    verdict.add_argument('--by', required=True, help='Who gave the verdict')
    verdict.add_argument('--at', help='Date YYYY-MM-DD (default today)')
    verdict.set_defaults(run=run_access_record)
    from familiar.tree.amendments import FIELDS
    amend = actions.add_parser('amend', help='Keep a proposed amendment beside a family statement or a document reading; the original is not touched')
    amend.add_argument('--id', help='Name of the proposal (default PERSON-FIELD); an existing one is restated')
    amend.add_argument('--person', required=True, help='Tree ID')
    amend.add_argument('--field', required=True, choices=FIELDS)
    amend.add_argument('--original', required=True, help='What was told or read, literally')
    amend.add_argument('--of', required=True, help='Memory item or record that says so')
    amend.add_argument('--value', required=True, help='What we propose instead')
    amend.add_argument('--weight', required=True, type=float, help='From 0.5 the card tells it')
    amend.add_argument('--basis', required=True, help='Why, in words the family reads: the stone, the act, a later word')
    amend.add_argument('--source', action='append', default=[], help='Record or memory item of the basis; repeatable')
    amend.add_argument('--by', required=True, help='Who proposes')
    amend.add_argument('--report', help='File of the argument')
    amend.add_argument('--state', choices=('proposed', 'confirmed', 'declined'), help='Decided outside the site')
    amend.set_defaults(run=run_amend)
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
        if args.line is not None and (args.lines or args.person or args.family):
            raise ValueError('--line cannot be combined with --lines, --person or --family')
        data, text = coverage(Instance(args.root), person=args.person, queue=args.recheck, lines=args.lines, save=args.save,
                              line=args.line, family=args.family)
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


def worded(value):
    """A text, or a row by language given as JSON."""
    return json.loads(value) if isinstance(value, str) and value.lstrip().startswith('{') else value


def run_access_note(args):
    from .access_ledger import note
    try:
        text = args.file.read_text(encoding='utf-8-sig').strip() if args.file else args.text
        note(Instance(args.root), worded(text), place=args.place, section=args.section, room=args.room, title=worded(args.title))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research access note: {exc}', file=sys.stderr)
        return 1


def run_access(args):
    from .access_ledger import printed, read, save_print, show
    try:
        if args.markdown:
            instance = Instance(args.root)
            path, _, problems = read(instance)
            if problems:
                raise ValueError(f'{problems[0][0]}: {problems[0][1]}')
            if args.save:
                print(save_print(instance))
            else:
                print(printed(instance, json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else {'places': []}))
            return 0
        data, text = show(Instance(args.root), line=args.line, place=args.place, order=args.order)
        print(json.dumps(data, ensure_ascii=False, indent=1) if args.json else text)
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research access: {exc}', file=sys.stderr)
        return 1


def run_access_record(args):
    from datetime import date
    from .access_ledger import record
    try:
        values = {k: worded(getattr(args, k)) for k in ('kind', 'title', 'years', 'state', 'holder', 'reference', 'online', 'read', 'of',
                                                'unit', 'letter', 'look_for', 'price', 'needs', 'order', 'doubtful', 'by', 'report', 'note')}
        row = record(Instance(args.root), args.place, values | {'at': args.at or date.today().isoformat()},
                     identity=args.id, lines=args.line)
        print(json.dumps(row, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research access record: {exc}', file=sys.stderr)
        return 1


def run_amend(args):
    from familiar.tree.amendments import record
    try:
        row = record(Instance(args.root), {
            'id': args.id, 'person': args.person, 'field': args.field, 'original': {'text': args.original, 'source': args.of},
            'value': args.value, 'weight': args.weight, 'basis': args.basis, 'sources': args.source, 'by': args.by,
            'report': args.report, 'state': args.state})
        print(json.dumps(row, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'research amend: {exc}', file=sys.stderr)
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
