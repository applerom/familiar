# START_MODULE_CONTRACT: MOD-CORRESPONDENCE
# PURPOSE: Keep human-sent correspondence and literal replies beside family questions.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - only the family writer changes records, original replies and feedback receipts [review: engine lead]
# - feedback is applied once with its authenticated sender; no reply accepts a tree assertion [review: engine lead]
# - owner correspondence is a sealed working view, never a reader field [review: engine lead]
# - hosted marks require an identified personal owner; loopback origin is explicit [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE
# - MOD-DESK-FEEDBACK
# :END_MODULE_CONTRACT
import copy
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from .gate import boundary

STATES = {'draft', 'ready', 'sent', 'answered', 'closed'}
CHANNELS = {'forum', 'archive', 'message', 'relative'}
EDITABLE = {'title', 'recipient', 'channel', 'destination', 'follow_up', 'language',
            'text', 'people', 'question', 'request', 'sender'}
ACTIONS = {'correspondence_sent', 'correspondence_reply'}


def token(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,119}', value):
        raise ValueError('Correspondence ID must be a portable filename slug')
    return value


def address(value, *, email=False):
    if not isinstance(value, str) or not value.strip() or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError('Expected an HTTP(S) address' + (' or email' if email else ''))
    if email and re.fullmatch(r'[^@:/?#]+@[^@:/?#]+\.[^@:/?#]+', value):
        return 'mailto:' + value
    parsed = urlsplit(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Only HTTP(S) links without credentials are allowed')
    return value


def validate(row):
    if not isinstance(row, dict):
        raise ValueError('Correspondence must be an object; use research form correspondence')
    token(row.get('id'))
    for key in ('title', 'recipient', 'language', 'text'):
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError('Correspondence requires text: ' + key)
    if row.get('state') not in STATES or row.get('channel') not in CHANNELS:
        raise ValueError('Unknown correspondence state or channel')
    address(row.get('destination'), email=True)
    # Null: the answer returns to the sender's own mailbox, which is not ours to name.
    if row.get('follow_up') is not None:
        address(row['follow_up'])
    if not isinstance(row.get('people'), list) or any(not isinstance(p, str) for p in row['people']):
        raise ValueError('Correspondence people must be an array of person IDs')
    sender = row.get('sender')
    if (not isinstance(sender, dict) or sender.get('kind') not in {'host', 'relative'}
            or not isinstance(sender.get('name'), str) or not sender['name'].strip()):
        raise ValueError('Sender requires kind (host/relative) and name')
    if row['state'] in {'sent', 'answered'}:
        sent = row.get('sent', {})
        if not isinstance(sent, dict) or any(not isinstance(sent.get(k), str) or not sent[k].strip() for k in ('by', 'at')):
            raise ValueError('Sent correspondence requires who sent it and when')
        datetime.fromisoformat(sent['at'])
    replies = row.get('replies', [])
    if not isinstance(replies, list) or any(not isinstance(r, dict) for r in replies):
        raise ValueError('Correspondence replies must be an array of objects')
    for reply in replies:
        if any(not isinstance(reply.get(k), str) or not reply[k].strip()
               for k in ('text', 'by', 'at', 'source', 'original')):
            raise ValueError('Reply requires literal text, by, at, source and original')
        if not isinstance(reply.get('meaning', ''), str):
            raise ValueError('Reply meaning must be text')
        if type(reply.get('transcript', False)) is not bool:
            raise ValueError('Reply transcript flag must be boolean')
        if reply.get('original_sha256') is not None and not re.fullmatch(r'[0-9a-f]{64}', str(reply['original_sha256'])):
            raise ValueError('Reply original digest must be SHA-256')
        datetime.fromisoformat(reply['at'])
    if row['state'] == 'answered' and not replies:
        raise ValueError('Answered correspondence needs a literal reply')


def rows(instance):
    return [(p, json.loads(p.read_text(encoding='utf-8')))
            for p in sorted(instance.path('correspondence').glob('*.json'))]


def record(instance, identity):
    path = instance.path('correspondence') / (token(identity) + '.json')
    if not path.is_file():
        raise ValueError('No such correspondence')
    row = json.loads(path.read_text(encoding='utf-8'))
    validate(row)
    if row['id'] != identity:
        raise ValueError('Correspondence ID differs from its filename')
    return path, row


def now():
    return datetime.now(UTC).isoformat(timespec='seconds')


def sent(row, by, at, **extra):
    if row['state'] != 'ready':
        raise ValueError('Only ready correspondence can be marked sent')
    row.update(state='sent', sent={'by': by, 'at': at, **extra})


def reply_changes(instance, row, raw, *, by, at, source, meaning='', literal_text=None,
                  extension='.txt', **extra):
    if row['state'] not in {'sent', 'answered'}:
        raise ValueError('Mark correspondence sent before adding a reply')
    try:
        text = raw.decode('utf-8-sig') if literal_text is None else literal_text
    except UnicodeError as exc:
        raise ValueError('For a non-UTF-8 original supply its literal transcript with --text together with --file') from exc
    if not text.strip():
        raise ValueError('Reply is empty; supply UTF-8 text')
    digest = hashlib.sha256(raw).hexdigest()
    extension = extension.lower() if re.fullmatch(r'\.[a-zA-Z0-9]{1,12}', extension) else '.bin'
    original = instance.path('originals') / 'correspondence' / row['id'] / (digest + extension)
    if original.exists() and original.read_bytes() != raw:
        raise ValueError('Original reply collision')
    row.setdefault('replies', []).append({'text': text, 'by': by, 'at': at, 'source': source,
        'meaning': meaning, 'original': original.relative_to(instance.root).as_posix(),
        'original_sha256': digest, 'transcript': literal_text is not None, **extra})
    row['state'] = 'answered'
    return {original: raw}


@boundary('transaction')
def apply_feedback(instance, data, *, local=False):
    if data.get('kind') not in ACTIONS:
        return
    principal = data.get('sender', {})
    from familiar.desk.accounts import mode
    if not local and (mode(instance) != 'personal' or not principal.get('sub') or principal.get('role') != 'owner'):
        raise ValueError('Only the family owner can mark correspondence')
    from .writer import mutate
    mark = instance._inside('family/feedback/read/' + data['id'] + '.json')
    if mark.exists():
        return
    path, row = record(instance, data.get('subject'))
    by = principal.get('username') or row['sender']['name']
    at = data['received_at']
    changes = {}
    if data['kind'] == 'correspondence_sent':
        sent(row, by, at, principal=principal, feedback=data['id'])
    else:
        changes.update(reply_changes(instance, row, data['text'].encode('utf-8'),
            by=row['recipient'], at=at, source=row.get('follow_up') or row['destination'],
            received_by=principal, feedback=data['id']))
    changes.update({path: row, mark: {'status': 'addressed', 'reply': '', 'at': at,
                                     'correspondence': row['id']}})
    mutate(instance, changes)


@boundary('transaction')
def change(instance, action, *, identity=None, value=None, by=None, at=None,
           raw=None, source=None, meaning='', reply_number=None, literal_text=None, extension='.txt'):
    from .writer import mutate
    changes, exclusive = {}, ()
    if action == 'create':
        row = copy.deepcopy(value)
        row.setdefault('state', 'draft')
        row.setdefault('replies', [])
        if row['state'] not in {'draft', 'ready'} or row['replies'] or row.get('sent'):
            raise ValueError('Create a draft or ready letter; use sent/reply for later steps')
        validate(row)
        path = instance.path('correspondence') / (row['id'] + '.json')
        exclusive = (path,)
    else:
        path, row = record(instance, identity)
        if action == 'update':
            if not isinstance(value, dict) or set(value) - EDITABLE - {'state'}:
                raise ValueError('Update only letter fields; use sent, reply, interpret or close for history')
            if row['state'] not in {'draft', 'ready'}:
                raise ValueError('A sent letter is literal history; create a new letter to send again')
            row.update(value)
            if row['state'] not in {'draft', 'ready'}:
                raise ValueError('Use sent, reply or close to change the correspondence state')
        elif action == 'sent':
            sent(row, by, at or now())
        elif action == 'reply':
            changes.update(reply_changes(instance, row, raw, by=by, at=at or now(),
                source=source, meaning=meaning, literal_text=literal_text, extension=extension))
        elif action == 'interpret':
            if not 1 <= reply_number <= len(row.get('replies', [])):
                raise ValueError('Reply number is outside this correspondence')
            row['replies'][reply_number - 1]['meaning'] = meaning
        elif action == 'close':
            row.update(state='closed', closed_at=at or now())
        else:
            raise ValueError('Unknown correspondence action')
    validate(row)
    changes[path] = row
    mutate(instance, changes, exclusive=exclusive)
    return row['id']


def register(actions):
    parser = actions.add_parser('correspondence', help='Letters prepared by agents and sent by people')
    commands = parser.add_subparsers(dest='correspondence_action')
    parser.add_argument('--text', action='store_true', help='List open correspondence as plain text')
    parser.set_defaults(run=execute)
    for name in ('create', 'update', 'sent', 'reply', 'interpret', 'close'):
        command = commands.add_parser(name)
        if name != 'create':
            command.add_argument('identity')
        if name in {'create', 'update'}:
            command.add_argument('input', type=Path, help='JSON form or patch')
        if name in {'sent', 'reply'}:
            command.add_argument('--by', required=True, help='Who sent the letter / wrote the reply')
        if name in {'sent', 'reply', 'close'}:
            command.add_argument('--at')
        if name == 'reply':
            command.add_argument('--text', dest='reply_text', help='Literal reply, or transcript supplied beside a binary original')
            command.add_argument('--file', type=Path, help='Original file, saved byte for byte; non-UTF-8 needs --text as well')
            command.add_argument('--source', required=True, help='Where the reply was obtained')
        if name in {'reply', 'interpret'}:
            command.add_argument('--meaning', default='' if name == 'reply' else None, required=name == 'interpret')
        if name == 'interpret':
            command.add_argument('--reply', dest='reply_number', type=int, required=True)
        command.set_defaults(run=execute)


def execute(args):
    from .model import Instance
    try:
        instance = Instance(args.root)
        action = args.correspondence_action
        if action is None:
            from .gate import publication
            result = publication(instance, 'correspondence')
            result.check(instance)
            print(result.data()['text'])
        else:
            options = {k: getattr(args, k) for k in ('identity', 'by', 'at', 'source', 'meaning', 'reply_number')
                       if hasattr(args, k)}
            if action in {'create', 'update'}:
                options['value'] = json.loads(args.input.read_text(encoding='utf-8-sig'))
            if action == 'reply':
                if not args.file and args.reply_text is None:
                    raise ValueError('Supply --text or --file (with --text for a binary original)')
                options['raw'] = args.file.read_bytes() if args.file else args.reply_text.encode('utf-8')
                if args.file:
                    options.update(literal_text=args.reply_text, extension=args.file.suffix)
            print(change(instance, action, **options))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
