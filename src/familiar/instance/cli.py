# START_MODULE_CONTRACT: MOD-INSTANCE-CLI
# PURPOSE: Expose family initialization, structural readiness and resolved path provenance to the host.
# PRD_REF: docs/PRD.md#INSTANCE
# INVARIANTS:
# - initialization creates config and byte-preserving git defaults without replacing existing files [test: tests/journeys/test_installed_engine.py::test_installed_engine]
# - scoped diagnostics list every selected finding and cannot imply family publication readiness [review: engine lead]
# - whole-instance reports count and name working research findings separately from blocking errors [review: engine lead]
# - release drift is visible in text and JSON diagnostics [review: engine lead]
# - recorded wheel provenance requires matching installed package bytes [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#INSTANCE
# - MOD-INSTANCE-PACKS (question source cards and language answers)
# :END_MODULE_CONTRACT
import json
import sys
from pathlib import Path
from uuid import uuid4

from .model import DEFAULTS, Instance
from .root import RootNotFound


def register(commands):
    parser = commands.add_parser("instance")
    actions = parser.add_subparsers(dest="action", required=True)
    check = actions.add_parser("check")
    check.add_argument("--json", action="store_true")
    selection = check.add_mutually_exclusive_group()
    selection.add_argument('--path', action='append', help='Own JSON/JSONL file or directory, relative to family root; repeatable')
    selection.add_argument('--prefix', help='Own path/filename prefix, relative to family root')
    actions.add_parser("paths")
    release = actions.add_parser('record-release', help='Record an installed wheel and its source commit')
    release.add_argument('--wheel', type=Path, required=True)
    release.add_argument('--commit', required=True)
    init = actions.add_parser("init")
    init.add_argument("directory", type=Path)
    init.add_argument("--title", default="Untitled family")
    init.add_argument("--language", default="en")
    init.add_argument("--address", choices=('formal', 'informal'), default='formal',
                      help='How to address relatives: formal (вы) or informal (ты)')
    register_pack(commands)
    parser.set_defaults(run=run)


def run(args):
    try:
        if args.action == "init":
            from familiar import __version__

            from .writer import initialize
            config = args.directory / 'familiar.toml'
            pack = {'ru': 'ru', 'pl': 'pl', 'en': 'demo-english'}.get(args.language)
            packs = f'language_packs = {{ {json.dumps(args.language)} = {json.dumps(pack)} }}\n' if pack else ''
            initialize(args.directory, f'schema_version = 1\nregion_packs = []\n{packs}\n'
                       f'[engine]\nversion = "{__version__}"\n\n[family]\n'
                       f'id = "{uuid4()}"\ntitle = {json.dumps(args.title)}\n'
                       f'source_language = {json.dumps(args.language)}\n'
                       f'languages = [{json.dumps(args.language)}]\n\n[settings]\n'
                       f'"host.address" = {json.dumps(args.address)}\n')
            print(str(config.resolve()))
            return 0
        instance = Instance(args.root)
        if args.action == 'record-release':
            print(record_release(instance, args.wheel, args.commit))
            return 0
        if args.action == "check":
            from .validation import check
            report = check(instance, paths=args.path, prefix=args.prefix)
            from familiar import __version__
            report['engine_version'] = __version__
            report['pinned_engine_version'] = instance.engine_version
            report['warnings'] = [message] if (message := instance.engine_warning()) else []
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                from familiar import __version__
                print(f"instance: {'valid' if report['valid'] else 'invalid'}; "
                      f"{len(report['errors'])} errors; engine: Familiar {__version__}")
                if report.get('scope'):
                    print(f"scope: {report['scope']}; {len(report['files'])} files; not a publication check")
                for error in report['errors']:
                    print(f"{error['location']}: {error['message']}")
                for advice in report.get('advice', []):
                    print(f"ADVICE: {advice['location']}: {advice['message']}")
                if work := report.get('research_in_progress'):
                    print(f"исследование в работе: {work['count']} findings; {len(work['paths'])} files")
                    for path in work['paths']:
                        print(f'  {path}')
                for finding in report.get('surname_findings', []):
                    print(f"{finding['location']}: {', '.join(finding['spellings'])}; {finding['message']}")
                for warning in report['warnings']:
                    print(f'WARNING: {warning}', file=sys.stderr)
                for key in (() if report.get('scope') else ('first_chapter_missing', 'full_cycle_missing')):
                    print(f"{key}: {', '.join(report[key]) or 'ready'}")
                if not report.get('scope'):
                    print(f"research_ready: {report.get('research_ready', False)}; next: {report.get('research_next', 'lead: resolve validation errors')}")
            return int(not report['valid'])
        else:
            print(json.dumps([{ "key": key, "path": str(instance.path(key)),
                                "exists": instance.path(key).exists(),
                                "origin": "host" if key in instance.host_paths else
                                "set" if key in instance.overrides else "default"}
                              for key in DEFAULTS if key != 'questions'] + [
                                  {"key": "pack:" + pack['id'], "path": str(pack['path']),
                                   "exists": pack['path'].exists(), "origin": pack['origin']}
                                  for pack in [*instance.packs, *instance.language_pack_data.values()]
                              ], indent=2))
        return 0
    except (ValueError, OSError, RootNotFound) as error:
        if getattr(args, 'json', False):
            print(json.dumps({'valid': False, 'errors': [
                {'location': 'configuration', 'message': str(error)}]}))
            return 1
        print(f"instance: {error}", file=sys.stderr)
        return 1


def register_pack(commands):
    parser = commands.add_parser('pack')
    actions = parser.add_subparsers(dest='action', required=True)
    ask = actions.add_parser('ask')
    ask.add_argument('question')
    ask.add_argument('--country')
    ask.add_argument('--year', type=int)
    ask.add_argument('--language', help='Read the explicitly selected language pack')
    calendar = actions.add_parser('calendar')
    calendar.add_argument('date', help='YYYY-MM-DD in the explicitly selected style')
    calendar.add_argument('--country', required=True)
    calendar.add_argument('--style', choices=('julian', 'gregorian'), required=True)
    parser.set_defaults(run=ask_pack)


def ask_pack(args):
    import re

    from .packs import answer_sources, question_coverage
    try:
        instance = Instance(args.root)
        if args.action == 'calendar':
            from .calendar import calendar
            print(json.dumps(calendar(instance, args.date, args.country, args.style), ensure_ascii=False, indent=2, default=str))
            return 0
        if not re.fullmatch(r'RP-[0-9]+', args.question):
            raise ValueError('question must be RP-n')
        if args.language:
            pack = instance.language_pack_data.get(args.language)
            if pack is None:
                print('Language pack gap: no selected pack for ' + args.language)
                return 0
            coverage = question_coverage(pack)
            if args.question not in coverage:
                raise ValueError('unknown registered question: ' + args.question)
            row = coverage[args.question]
            print(f"pack: {pack['id']} ({pack['origin']}); language {args.language}")
            print(row['text'] if row['state'] == 'answered' else json.dumps(row, ensure_ascii=False))
            return 0
        if args.country is None or args.year is None:
            raise ValueError('region questions require --country and --year; language questions use --language')
        for pack in reversed(instance.packs):
            meta = pack['data'].get('pack', {})
            years = meta.get('years', [])
            if args.country not in meta.get('countries', []) or len(years) != 2:
                continue
            if not years[0] <= args.year <= years[1]:
                continue
            print(f"pack: {pack['id']} ({pack['origin']}); {args.country}, {args.year}")
            coverage = question_coverage(pack)
            if args.question not in coverage:
                raise ValueError('unknown registered question: ' + args.question)
            row = coverage[args.question]
            if row['state'] == 'answered':
                print(row['text'])
                for source in answer_sources(pack, row['text'], args.country, args.year):
                    print(json.dumps(source, ensure_ascii=False, default=str))
            else:
                print('Pack gap (implicit)' if row['implicit'] else 'Pack gap (declared)')
                print(json.dumps(row, ensure_ascii=False, default=str))
            return 0
        print('No region pack covers this country and year.')
        return 0
    except (ValueError, OSError, RootNotFound) as error:
        print(f'pack: {error}', file=sys.stderr)
        return 1


def record_release(instance, wheel, commit):
    import re

    if not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', commit):
        raise ValueError('engine commit must be a full lowercase Git object id')
    if message := instance.engine_warning():
        raise ValueError(message)
    import hashlib
    import io
    from email.parser import BytesParser
    from importlib.metadata import distribution
    from zipfile import ZipFile

    from familiar import __version__

    raw = wheel.read_bytes()
    installed = distribution('familiar')
    with ZipFile(io.BytesIO(raw)) as archive:
        metadata = [n for n in archive.namelist() if n.endswith('.dist-info/METADATA')]
        if len(metadata) != 1:
            raise ValueError('wheel must contain one Familiar distribution')
        meta = BytesParser().parsebytes(archive.read(metadata[0]))
        if meta['Name'] != 'familiar' or meta['Version'] != __version__:
            raise ValueError(f'wheel is not the installed Familiar {__version__}')
        names = [n for n in archive.namelist() if n.startswith('familiar/') and not n.endswith('/')]
        if not names or any(not installed.locate_file(n).is_file() or
                            installed.locate_file(n).read_bytes() != archive.read(n) for n in names):
            raise ValueError('wheel bytes differ from the installed engine; install this wheel first')
    value = {'engine_version': __version__, 'commit': commit, 'wheel': wheel.name,
             'sha256': hashlib.sha256(raw).hexdigest()}
    from .writer import engine_release
    return engine_release(instance, value)
