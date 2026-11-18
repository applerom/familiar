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
    photo = actions.add_parser('photo', help='Attach one family photo or a CSV/TSV of photos')
    photo.add_argument('input', type=Path)
    photo.add_argument('--table', action='store_true', help='Columns: file, people, caption, received_from, when (optional)')
    photo.add_argument('--person', action='append', default=[], help='Working-tree person ID; repeat for a group photo')
    photo.add_argument('--caption', default='')
    photo.add_argument('--when', default='', help='Date or era as written in the archive')
    photo.add_argument('--received-from', default='')
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
        if kind == 'photo':
            from .photo import ingest as ingest_photo
            if args.table and (args.person or args.caption or args.when or args.received_from):
                raise ValueError('put people, caption, date or era and attribution in the table')
            report = ingest_photo(instance, args.input, table=args.table, people=args.person,
                                  caption=args.caption, when=args.when, received_from=args.received_from)
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
        report = ingest(instance, data, kind, original, accepted_by=getattr(args, "by", None))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, RootNotFound, csv.Error) as exc:
        reason = f'{args.input}: {exc}'
        if isinstance(exc, KeyError):
            reason += '; check required fields and local person keys: [[people]] id="local", existing="canonical-id"; record.people values use local keys'
        report = {"status": "rejected", "input": str(args.input), "reason": reason}
        if instance:
            diagnostic(instance, f"intake/rejected-{uuid4().hex}.json", report)
        print(json.dumps(report), file=sys.stderr)
        return 1
