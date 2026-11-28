# START_MODULE_CONTRACT: MOD-INTAKE-CLI
# PURPOSE: Give a new family's agent explicit intake commands and durable rejection reports.
# PRD_REF: docs/PRD.md#INSTANCE
# INVARIANTS:
# - fresh initialization reaches a graph through the public intake command [test: tests/journeys/test_installed_engine.py::test_installed_engine]
# CHANGES_WITH:
# - docs/PRD.md#FORMS
# :END_MODULE_CONTRACT
import csv
import json
import sys
import tomllib
from argparse import RawDescriptionHelpFormatter
from pathlib import Path
from uuid import uuid4

from familiar.instance.model import Instance
from familiar.instance.root import RootNotFound
from familiar.instance.writer import diagnostic

from .core import ingest
from .gedcom import parse


def register(commands):
    parser = commands.add_parser("intake")
    actions = parser.add_subparsers(dest="intake_kind", required=True)
    for kind in ("memory", "paper", "gedcom", "table"):
        sub = actions.add_parser(kind)
        if kind == "paper":
            sub.formatter_class = RawDescriptionHelpFormatter
            sub.epilog = '''Example paper.toml (attach the preserved original with --original FILE):

id = "bea-paper"
[record]
title = "Invented city certificate"
source = {holder = "host"}
language = ["en"]
fields = {Name = "Bea Example"}
reading = "Name: Bea Example"
people = {Bea = "bea-person"}
[record.interest]
level = 0.6
tell = "A home paper preserves a name alongside family memory."
[[people]]
id = "bea-person"
existing = "bea-telling-bea-person"
'''
        sub.add_argument("input", type=Path)
        if kind in {"paper", "memory"}:
            sub.add_argument("--original", required=kind == "paper", type=Path)
        if kind == "memory":
            sub.add_argument("--by", help="Name of the person accepting the feedback (default: OS user)")
        if kind == "table":
            sub.add_argument("--id", required=True)
            sub.add_argument("--told-by", required=True)
            sub.add_argument("--date", required=True)
            sub.add_argument("--language", default="ru")
            sub.add_argument("--mapping", type=Path)
        if kind == "gedcom":
            sub.add_argument("--id", required=True)
            sub.add_argument("--living-years", type=int, help='Must match the family registry privacy.living_years')
            sub.add_argument("--as-of")
            sub.add_argument("--own", action="store_true", help="The family's own tree: its claims are the family's word, not another tree's hypotheses")
    case = actions.add_parser('kinship-case', help='Preview a kinship research case migration')
    case.add_argument('input', type=Path, metavar='CASE')
    case.add_argument('--id', required=True, help='Namespace for the imported case')
    case.add_argument('--apply', action='store_true', help='Preserve and import the case (default: preview)')
    photo = actions.add_parser('photo', help='Attach one family photo or a CSV/TSV of photos')
    photo.add_argument('input', type=Path)
    photo.add_argument('--table', action='store_true', help='Columns: file, people, caption, received_from; optional when, sent_for, show, sheet, unnamed_faces (yes/no), faces (PERSON=x,y,w,h;...), crop')
    photo.add_argument('--person', action='append', default=[], help='Working-tree person ID; repeat for a group photo')
    photo.add_argument('--caption', default='')
    photo.add_argument('--when', default='', help='Date or era as written in the archive')
    photo.add_argument('--received-from', default='')
    photo.add_argument('--for', dest='sent_for', default='', help='Why the sender gave this photograph (archive note)')
    photo.add_argument('--show', choices=('gallery', 'card', 'private'),
                       help='Show in the gallery and cards, cards only, or keep in the archive. Sheets, unnamed faces and purpose notes default to private.')
    photo.add_argument('--sheet', action='store_true', help='This file is a sheet of several photographs')
    photo.add_argument('--unnamed-faces', action='store_true', help='Some or all of the people pictured are unnamed')
    photo.add_argument('--face', action='append', default=[], metavar='PERSON=x,y,w,h',
                       help="Where this person's face is, as fractions of the picture; repeat for each named face. "
                            'Run again on an attached original with only --face/--crop to add them later')
    photo.add_argument('--crop', default='', metavar='x,y,w,h',
                       help='Show only this part of the picture (a print re-shot by phone); the original stays whole')
    sent = actions.add_parser('attachment', help="List files relatives attached to remarks, or take one remark's files in")
    sent.add_argument('input', nargs='?', metavar='ID', help='Remark ID (without it: list files waiting)')
    sent.add_argument('--file', type=int, action='append', default=[], help='Only this attached file number; repeatable')
    sent.add_argument('--person', action='append', default=[], help="Working-tree person ID (default: the remark's person)")
    sent.add_argument('--caption', default='', help='Default: the first line of the remark')
    sent.add_argument('--when', default='', help='Date or era as written in the archive')
    sent.add_argument('--received-from', default='', help='Default: the signed sender and the remark')
    draft = actions.add_parser("feedback-draft", help="Prepare editable memory TOML from inbox feedback IDs")
    draft.add_argument("input", nargs="+", metavar="ID")
    draft.add_argument("--output", required=True, type=Path)
    draft.add_argument("--id", help="Intake ID (default: generated)")
    draft.add_argument("--told-by", default="Рассказчик; уточнить исследователю")
    parser.set_defaults(run=run)


def run(args):
    instance = None
    try:
        instance = Instance(args.root)
        kind = args.intake_kind
        if kind == 'kinship-case':
            from .kinship_case import intake_case
            report = intake_case(instance, args.input, args.id, apply=args.apply)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if kind == 'photo':
            from .photo import ingest as ingest_photo
            if args.table and (args.person or args.caption or args.when or args.received_from or args.sheet or args.unnamed_faces):
                raise ValueError('put people, caption, date or era, attribution, sheet and unnamed faces in the table')
            report = ingest_photo(instance, args.input, table=args.table, people=args.person,
                                  caption=args.caption, when=args.when, received_from=args.received_from,
                                  sent_for=args.sent_for, show=args.show, sheet=args.sheet, unnamed_faces=args.unnamed_faces,
                                  faces=args.face, crop=args.crop)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if kind == 'attachment':
            from .photo import from_feedback, waiting
            report = ({'waiting': waiting(instance)} if not args.input else from_feedback(
                instance, args.input, numbers=args.file, people=args.person, caption=args.caption,
                when=args.when, received_from=args.received_from))
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if kind == "feedback-draft":
            from .feedback import prepare
            report = prepare(instance, args.input, args.output, args.id, args.told_by)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if kind == "table":
            from .table import prepare
            report = prepare(instance, args.input, args.id, args.told_by, args.date, args.language, args.mapping)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1 if report['status'] == 'rejected' else 0
        if kind == "gedcom":
            from familiar.rules.cascade import Registry
            from familiar.rules.roles import method_root
            years = Registry(method_root() / 'rules', instance).resolve_setting('privacy.living_years').value
            if args.living_years is not None and args.living_years != years:
                raise ValueError('Set privacy.living_years in family settings; GEDCOM must use the same horizon')
            data = parse(args.input, args.id, years, args.as_of)
        elif kind == 'memory' and args.input.suffix.lower() == '.json':
            data = json.loads(args.input.read_text(encoding='utf-8-sig'))
        else:
            data = tomllib.loads(args.input.read_text(encoding="utf-8-sig"))
        original = args.input if kind == "gedcom" else getattr(args, "original", None)
        report = ingest(instance, data, kind, original, accepted_by=getattr(args, "by", None), own=getattr(args, "own", False))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, RootNotFound, csv.Error) as exc:
        reason = f'{args.input}: {exc}'
        if isinstance(exc, KeyError) and args.intake_kind != 'kinship-case':
            reason += '; check required fields and local person keys: [[people]] id="local", existing="canonical-id"; record.people values use local keys'
        report = {"status": "rejected", "input": str(args.input), "reason": reason}
        if instance and args.intake_kind != 'kinship-case':
            diagnostic(instance, f"intake/rejected-{uuid4().hex}.json", report)
        print(json.dumps(report), file=sys.stderr)
        return 1
