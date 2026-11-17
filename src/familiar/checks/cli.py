# START_MODULE_CONTRACT: MOD-CHECKS-CLI
# PURPOSE: Give feed authors a bounded console report or complete JSON with a blocking exit status.
# PRD_REF: docs/PRD.md#PIPELINE
# INVARIANTS:
# - JSON reports and exit status agree on blocking trust findings [review: engine lead]
# - unavailable checks are named with reasons beside the executed-check count [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#PIPELINE
# :END_MODULE_CONTRACT
import json
import sys
from pathlib import Path

from familiar.instance.model import Instance
from familiar.rules.cascade import Registry
from familiar.rules.roles import method_root

from .engine import inspect_text, run


def execute(args):
    try:
        if not args.all and not args.feed and not args.text:
            raise ValueError('Specify a feed, --all or --text FILE')
        registry = Registry(method_root() / 'rules', Instance(args.root))
        if args.text:
            text = args.text.read_text(encoding='utf-8-sig')
            chapter = {'id': 'draft', 'text': text}
            coverage = {'feed': 'draft', 'checks_run': 0, 'checks_skipped': {}}
            report = {'findings': inspect_text(registry, chapter, 'feed:draft/chapter:0', coverage=coverage),
                      'coverage': [coverage], 'blocked': False, 'text_only': True}
        else:
            report = run(registry, [args.feed] if args.feed else None)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            for f in report['findings'][:50]:
                label = 'снято автором' if f['exception'] else ('прочитай это место' if f['certainty'] == 'review' else f['mode'])
                reason = f" Причина: {f['exception']['reason']}" if f['exception'] else ''
                print(f"{label} {f['rule']} {f['scope']} {f['location']}: {f['message']}{reason}")
            if args.text:
                print('Проверки оформления текста удалены; текст принимает человек. Гарантии данных здесь не проверялись.')
                return 0
            ran = sum(c.get('checks_run', 0) for c in report['coverage'])
            missing = [(c['feed'], key, reason) for c in report['coverage']
                       for key, reason in (c.get('language_unavailable', {}) | c.get('checks_skipped', {})).items()]
            for feed, key, reason in missing:
                print(f'not run {feed} {key}: {reason}')
            verdict = f"{len(report['findings'])} findings" if ran else 'Checks did not run; findings unknown'
            print(f"{verdict}; {ran} checks run; {len(missing)} checks not run; blocked={report['blocked']}; "
                  f"{len(report['coverage'])} feeds (use --json for all findings)")
        return int(report['blocked'])
    except (ValueError, OSError, KeyError) as exc:
        print(f'feed check: {exc}', file=sys.stderr)
        return 2


def register(commands):
    feed = commands.add_parser('feed').add_subparsers(dest='feed_command', required=True)
    check = feed.add_parser('check')
    choice = check.add_mutually_exclusive_group()
    choice.add_argument('feed', nargs='?')
    choice.add_argument('--all', action='store_true')
    choice.add_argument('--text', type=Path, metavar='FILE', help='Read a chapter draft outside the feed; text cues only, using this family’s settings')
    check.add_argument('--json', action='store_true')
    check.set_defaults(run=execute)
