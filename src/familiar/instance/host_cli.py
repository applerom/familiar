# START_MODULE_CONTRACT: MOD-HOST-CLI
# PURPOSE: Give the family private text views and human-sent correspondence commands.
# PRD_REF: docs/PRD.md#USE-CASES
# INVARIANTS:
# - host text views deliver a sealed publication; correspondence edits use the writer [review: engine lead]
# - requests in the mistaken default folder cannot yield a silent empty request list [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE (declared host publication view)
# - MOD-CLI (family command registration)
# :END_MODULE_CONTRACT
import sys

from .gate import boundary, publication
from .model import Instance


def register(commands):
    family = commands.add_parser('family', help='Read requests, next steps and a family summary as plain text')
    actions = family.add_subparsers(dest='host_view', required=True)
    from .correspondence import register as correspondence_commands
    correspondence_commands(actions)
    for name, help_text in (
        ('requests', 'Letters ready for the host to forward to relatives'),
        ('summary', 'What rests on papers, memory and open questions'),
        ('next', 'One or two next actions from the current family state'),
        ('confirmation', 'What you or your reader confirm before accepting a page'),
    ):
        action = actions.add_parser(name, help=help_text)
        action.add_argument('--text', action='store_true', help='Plain text (the default)')
        if name == 'requests':
            action.add_argument('selection', nargs='?', help='Select a single request')
        action.set_defaults(run=execute)


@boundary('working')
def deliver(instance, view='summary', *, selection=None, feed=None):
    from .research_forms import request_storage_errors
    if view == 'requests':
        errors = request_storage_errors(instance)
        if errors:
            raise ValueError('; '.join(f'{path}: {message}' for path, message in errors))
    result = publication(instance, 'host', feed, host_view=view, selection=selection)
    result.check(instance)
    return result.data()['text']


def execute(args):
    try:
        instance = Instance(args.root)
        if args.host_view in {'next', 'summary'}:
            from familiar.desk.model import feedback_count, words
            if count := feedback_count(instance):
                print(words(instance)['unread'].format(count=count) + '\n')
        print(deliver(instance, args.host_view, selection=getattr(args, 'selection', None)))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
