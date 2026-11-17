# START_MODULE_CONTRACT: MOD-DESK-CLI
# PURPOSE: Offer separate local build, AWS publication and feedback retrieval operations.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - only explicit user add/reset prints that user's temporary password once; deployment credentials stay private [review: engine lead]
# - provisioning can finish and prove the anonymous gate before any family upload [review: engine lead]
# - cloud selection precedes even an explicitly requested local rebuild [review: engine lead]
# CHANGES_WITH:
# - MOD-CLI (desk registration)
# :END_MODULE_CONTRACT
import sys
from pathlib import Path

from familiar.instance.model import Instance


def register(commands):
    desk = commands.add_parser('desk', help='Private narrator desk')
    actions = desk.add_subparsers(dest='desk_action', required=True)
    for name in ('build', 'provision', 'publish', 'fetch-feedback', 'verify', 'delete-stack'):
        action = actions.add_parser(name)
        if name == 'publish':
            action.add_argument('--build', action='store_true', help='Rebuild locally, then publish in one command')
        action.set_defaults(run=execute)
    local = actions.add_parser('serve', help='Review the exact publication directory on loopback')
    local.add_argument('--build', action='store_true', help='Build before serving')
    local.add_argument('--port', type=int, default=0)
    local.set_defaults(run=execute)
    demo = actions.add_parser('export-demo', help='Export a fictional desk as a standalone static site')
    demo.add_argument('--output', required=True, type=Path)
    demo.add_argument('--public-reader', action='store_true',
                      help='Use the accepted public reader, excluding living-person prose')
    demo.set_defaults(run=execute)
    users = actions.add_parser('user', help='Host-managed personal Cognito logins')
    user_actions = users.add_subparsers(dest='user_action', required=True)
    add = user_actions.add_parser('add')
    add.add_argument('--person', required=True)
    add.add_argument('--username')
    add.add_argument('--email')
    add.add_argument('--role', choices=('reader', 'owner'), default='reader')
    add.set_defaults(run=execute)
    for name in ('list', 'reset', 'disable', 'enable', 'remove'):
        action = user_actions.add_parser(name)
        if name != 'list':
            action.add_argument('username')
        action.set_defaults(run=execute)


def execute(args):
    try:
        instance = Instance(args.root)
        if args.desk_action == 'user':
            from .accounts import execute as user_execute
            print(user_execute(instance, args))
        elif args.desk_action == 'serve':
            if args.build:
                from .build import build
                print(f'Desk built: {build(instance)} delivery files')
            from .server import serve
            serve(instance, args.port)
        elif args.desk_action == 'export-demo':
            from .build import export_demo
            print(f'Demo exported: {export_demo(instance, args.output, public_reader=args.public_reader)} delivery files')
        elif args.desk_action == 'build':
            from .build import build
            print(f'Desk built: {build(instance)} delivery files')
        else:
            from .model import publication
            publication(instance)
            from . import aws
            if args.desk_action == 'publish' and args.build:
                from .build import build
                print(f'Desk built: {build(instance)} delivery files')
            result = {'provision': aws.provision, 'publish': aws.publish,
                      'fetch-feedback': aws.fetch_feedback, 'verify': aws.verify,
                      'delete-stack': aws.delete_stack}[args.desk_action](instance)
            print(result)
        return 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc:
        # AWS errors can contain resource addresses. Its adapter deliberately
        # returns only safe operation/status diagnostics.
        print(str(exc), file=sys.stderr)
        return 2
