# START_MODULE_CONTRACT: MOD-FEED-CLI
# PURPOSE: Add feed build, status and empty authoring forms alongside the existing check command.
# PRD_REF: docs/PRD.md#PIPELINE
# INVARIANTS:
# - new feeds refuse to overwrite authored folders [review: engine lead]
# CHANGES_WITH:
# - docs/reader-export.md (reader-private review tickets and acceptance)
# - MOD-HOST-CLI (text pages and pre-acceptance explanation)
# - MOD-PUBLICATION (declared reader surfaces and default-deny policy)
# - MOD-FAMILY-WRITER (the sole filesystem and generation boundary)
# - MOD-CHECKS-CLI
# :END_MODULE_CONTRACT
import json
import sys
from pathlib import Path

from familiar.instance.model import Instance

from .service import build, folders, inspect


def execute(args):
    try:
        host_map = getattr(args, 'host_paths', None)
        instance = Instance(args.root, host_paths=json.loads(host_map.read_text(encoding='utf-8-sig'))
                            if host_map is not None else None)
        if args.feed_command == 'restorations':
            from familiar.instance.restorations import inventory
            print(json.dumps(inventory(instance), ensure_ascii=False, indent=2))
        elif args.feed_command == 'pages':
            if args.text:
                from familiar.instance.host_cli import deliver
                print(deliver(instance, 'pages', feed=args.feed, selection=args.page))
            else:
                from .pages import pages
                print(json.dumps(pages(instance, args.feed, preview=args.preview), ensure_ascii=False))
        elif args.feed_command in {'chapters', 'storyboard'}:
            from .studio import run
            run(instance, args)
        elif args.feed_command == 'rhythm':
            from familiar.rules.cascade import Registry
            from familiar.rules.roles import method_root

            from .rhythm import measure, report
            from .service import _materialize

            registry = Registry(method_root() / 'rules', instance)
            for folder in folders(instance, args.feed):
                feed, _ = _materialize(instance, folder)
                print(folder.name + '\n' + report(*measure(instance, feed, registry), feed_counts=True))
        elif args.feed_command == 'build':
            result = build(instance, args.out or instance.path('build') / 'feeds', args.feed)
            from .service import refresh_output
            status = refresh_output(instance, args.out or instance.path('build') / 'feeds')
            print(f'{status["state"]}: {len(result)} feeds built; unreviewed: {len(status.get("unreviewed", []))}')
        elif args.feed_command == 'status':
            from .service import refresh_output
            output = refresh_output(instance)
            from familiar.instance.gate import evaluate
            verdict = evaluate(instance)
            print(json.dumps({p.name: dict({'next': 'blocked'} if verdict['blocked'] else inspect(instance, p), output=output, trust=verdict) for p in folders(instance, args.feed)}, ensure_ascii=False, indent=2))
        elif args.feed_command == 'read':
            from .service import read_output
            print(json.dumps(read_output(instance, args.out), ensure_ascii=False))
        elif args.feed_command == 'person':
            from .feed_person import add
            print('\n'.join(add(instance, args.feed, args.person, source_name=args.name)))
        elif args.feed_command == 'doc':
            from .feed_doc import add
            if args.index is not None:
                if any((args.frame, args.box, args.reading)):
                    raise ValueError('--index cannot be combined with FRAME BOX READING')
                from .feed_doc import add_index
                print(add_index(instance, args.feed, args.key, args.index, args.source, args.where))
            else:
                if not args.record or not args.caption:
                    raise ValueError('provide --record CORPUS_ID and --caption TEXT')
                print('\n'.join(add(instance, args.feed, args.key, args.frame, args.box, args.reading, args.source, args.where, record=args.record, caption=args.caption)))
        elif args.feed_command == 'accept':
            ticket = json.loads(Path(args.ticket).read_text(encoding='utf-8')) if args.ticket else None
            accept(instance, args.feed, args.stage, args.pages, reviewer=args.reviewer, author=args.author,
                   kind=args.kind, ticket=ticket, languages=args.languages)
        elif args.feed_command == 'review':
            print(prepare_review(instance, args.feed, args.kind, args.out,
                                 host_private=args.kind == 'reader-private'))
            print('Inspect every selected page, language and image in this directory; confirm this ticket with feed accept.')
        elif args.feed_command == 'worklist':
            from familiar.instance.review import worklist
            print(json.dumps(worklist(instance, args.feed), ensure_ascii=False, indent=2))
        else:
            new(instance, args.feed)
        return 0
    except ImportError as exc:
        print(f'feed {args.feed_command}: missing optional image dependency; run with Pillow: {exc}', file=sys.stderr)
        return 2
    except (ValueError, OSError, KeyError) as exc:
        print(f'feed {args.feed_command}: {exc}', file=sys.stderr)
        return 2


from familiar.instance.gate import boundary


@boundary('output')
def prepare_review(instance, feed, kind, out, *, host_private=False):
    from familiar.instance.gate import publication
    from familiar.instance.writer import review_material
    material = publication(instance, kind, feed if kind == 'feeds' else None, for_review=True)
    return review_material(instance, out, material)


@boundary('writer')
def accept(instance, feed, stage, page_ids=None, *, reviewer=None, author=None, kind='feeds', ticket=None, languages=None):
    from familiar.instance.writer import mutate

    if stage in {'reading', 'blind'}:
        from familiar.instance.host_cli import deliver
        from familiar.instance.host_language import LanguageGap
        try:
            print(deliver(instance, 'confirmation'))
        except LanguageGap as exc:
            print(str(exc), file=sys.stderr)
    from .builder import read
    folder = folders(instance, feed)[0]
    state = read(folder / 'state.json', {})
    from .service import _inspect
    fingerprints = _inspect(instance, folder)['fingerprints']
    if page_ids:
        if stage not in {'reading', 'blind'} or set(page_ids) - (fingerprints.keys() | {'__feed__'}):
            raise ValueError('unknown pages or stage; --pages requires reading')
        fingerprints = {k: v for k, v in fingerprints.items() if k in page_ids}
    state.setdefault('pipeline', {}).setdefault(stage, {}).update(fingerprints)
    if stage == 'reading':
        state.setdefault('build_fingerprints', {}).update(fingerprints)
    if stage in {'reading', 'blind'}:
        from familiar.instance.review import attest
        attest(instance, kind, reviewer=reviewer, author=author, feed=feed if kind == 'feeds' else None,
               pages=page_ids, languages=languages, stage=stage, ticket=ticket)
        selected = page_ids or list(ticket['review_units'])
        print(f'Review scope: {kind}; pages={selected}; languages={languages or ticket["languages"]}; reviewer={reviewer}; author={author}')
        print('Byte equality is checked. The engine cannot verify actual attention or independence; two names entered by the author are not independent reading.')
    mutate(instance, {folder / 'state.json': state})
    count = len(page_ids or ticket['review_units']) if stage in {'reading', 'blind'} else len(fingerprints)
    print(f'{stage}: accepted {count} units')


@boundary('writer')
def new(instance, feed):
    from familiar.instance.writer import mutate
    base = instance.path('feeds')
    folder = (base / feed).resolve()
    if not folder.is_relative_to(base) or folder == base or folder.exists():
        raise ValueError('invalid or existing feed id')
    meta = {'id': feed, 'title': feed, 'lead': 'Draft introduction', 'period': '', 'line': '',
            'persons': {}, 'people': [], 'profile': {'pictures': 'none', 'languages': list(instance.languages)}}
    mutate(instance, {folder / (name + '.json'): data for name, data in
           (('feed', meta), ('chapters', []), ('documents', {}), ('pictures', {}), ('translations', {}))})
    print('Draft feed created; author the introduction, people and chapters before publication.')


def register(commands):
    # Reuse the parser owned by checks; the check command remains unchanged.
    feed = commands.choices['feed']
    sub = next(a for a in feed._actions if hasattr(a, 'choices') and isinstance(a.choices, dict))
    for name in ('build', 'status', 'new', 'pages', 'read', 'worklist', 'review', 'restorations', 'rhythm'):
        command = sub.add_parser(name)
        command.add_argument('feed', nargs=None if name == 'new' else '?')
        if name == 'pages':
            command.add_argument('--preview', action='store_true', help='Unvalidated work preview; never export')
            command.add_argument('--text', action='store_true', help='Read aloud: title, story, children and support')
            command.add_argument('--page', help='Select a chapter for plain-text reading')
        if name in {'build', 'read'}:
            command.add_argument('--out')
        if name == 'review':
            command.add_argument('--out', required=True, help='New directory for exact private review bytes and ticket')
            command.add_argument('--kind', choices=('feeds', 'tree', 'reader', 'reader-private'), default='feeds')
        command.set_defaults(run=execute)
    for name, help_text in (
            ('chapters', 'Import studio chapter files as feed data'),
            ('storyboard', 'Render a private phone-width draft from studio chapter files')):
        command = sub.add_parser(name, help=help_text)
        command.add_argument('feed')
        command.add_argument('--studio', help='Studio folder relative to the family root')
        if name == 'storyboard':
            command.add_argument('--host-paths', type=Path,
                                 help='Explicit host path map for out-of-tree media and originals')
        command.add_argument('--config', type=Path, help='Use this import.json instead of the studio settings')
        command.add_argument('--source-ref', help='Read studio files and image lists from a family Git commit')
        command.add_argument('--out', type=Path, help='Scratch directory for chapters, or HTML file for storyboard')
        if name == 'chapters':
            command.add_argument('--allow-remove-chapters', action='store_true',
                                 help='Replace the catalogue even if installed or expected chapters are absent')
        command.set_defaults(run=execute)
    for name, fields in (('person', ('feed', 'person')), ('doc', ('feed', 'key', 'frame', 'box', 'reading')), ('accept', ('feed',))):
        command = sub.add_parser(name)
        for field in fields:
            command.add_argument(field, **({'nargs': '?'} if name == 'doc' and field in ('frame', 'box', 'reading') else {}))
        if name == 'person':
            command.add_argument('--name')
        if name == 'doc':
            command.add_argument('--record')
            command.add_argument('--caption')
            command.add_argument('--index', metavar='READING')
            command.add_argument('--source')
            command.add_argument('--where')
        if name == 'accept':
            command.add_argument('--pages', nargs='+', metavar='CHAPTER_ID')
            command.add_argument('--stage', required=True, choices=('scenario', 'text', 'cards', 'drawing', 'blind', 'reading', 'translation', 'connect'))
            command.add_argument('--reviewer', help='Named independent reviewer, required for reading/blind')
            command.add_argument('--author', help='Named page author, distinct from reviewer')
            command.add_argument('--ticket', help='review-ticket.json saved with the inspected material')
            command.add_argument('--languages', nargs='+', help='Languages actually inspected (default: all in ticket)')
            command.add_argument('--kind', choices=('feeds', 'tree', 'reader', 'reader-private'), default='feeds')
        command.set_defaults(run=execute)
