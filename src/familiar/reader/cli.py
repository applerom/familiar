# START_MODULE_CONTRACT: MOD-READER-CLI
# PURPOSE: Expose isolated reader export, verification and checked local delivery through the installed command.
# PRD_REF: docs/PRD.md#ARCH
# INVARIANTS:
# - preview exposes the permission-filtered projection without a generation or publication authority [review: engine lead]
# CHANGES_WITH:
# - MOD-CLI (capability registration)
# - docs/reader-export.md (print command and private review preparation)
# :END_MODULE_CONTRACT
import json
import sys
from pathlib import Path

from familiar.instance.model import Instance

from .export import export, verify


def register(commands):
    parser = commands.add_parser('reader')
    actions = parser.add_subparsers(dest='reader_action', required=True)
    for action in ('export', 'verify', 'serve', 'preview', 'book'):
        command = actions.add_parser(action)
        command.add_argument('--output', type=Path)
        if action in ('export', 'serve', 'preview', 'book'):
            command.add_argument('--host-private', action='store_true', help='Local host view; never for publication')
        if action == 'book':
            command.add_argument('--language', help='Reader language; default: family source language')
            command.add_argument('--kids', action='store_true', help="Use the reader's children's layer")
            command.add_argument('--page-size', choices=('A5', 'A4'), default='A5')
        if action == 'serve':
            command.add_argument('--port', type=int, default=8768)
        command.set_defaults(run=run)


def run(args):
    try:
        if args.reader_action == 'book':
            from .book import export_book
            if args.output is None:
                raise ValueError('reader book requires an explicit empty --output directory')
            result = export_book(Instance(args.root), args.output, language=args.language,
                                 kids=args.kids, page_size=args.page_size, host_private=args.host_private)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.reader_action == 'preview':
            from familiar.instance.gate import publication
            from familiar.instance.writer import review_material
            instance = Instance(args.root)
            material = publication(instance, 'reader-private' if args.host_private else 'reader', for_review=True)
            if args.output:
                ticket = review_material(instance, args.output, material)
                print(json.dumps({'state': 'preview', 'review_ticket': str(ticket), 'publication': False}))
            else:
                files = material.files()
                print(json.dumps({'state': 'preview', 'publication': False,
                    'profile': json.loads(files['reader-profile.json']),
                    'graph': json.loads(files['graph.json'])}, ensure_ascii=False, indent=2))
            return 0
        if args.reader_action == 'serve':
            from .server import serve
            instance = Instance(args.root)
            if args.host_private and args.output is None:
                raise ValueError('host-private reader requires a separate explicit --output directory')
            if args.host_private and not ((args.output or instance.path('export')) / 'CURRENT.json').exists():
                export(instance, args.output, host_private=True)
            serve(instance, args.output if args.output is not None else instance.path('export'), args.port,
                  host_private=args.host_private)
            return 0
        result = (export(Instance(args.root), args.output, host_private=args.host_private)
                  if args.reader_action == 'export' else verify(Instance(args.root), args.output))
        print(json.dumps({'schema_version': result['schema_version'], 'state': result['state'], 'files': len(result['files'])}))
        if args.reader_action == 'export' and result['state'] == 'clean':
            from familiar.instance.publication import PUBLIC_SCAN_SCOPE
            print(PUBLIC_SCAN_SCOPE, file=sys.stderr)
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(str(exc))
        return 1
