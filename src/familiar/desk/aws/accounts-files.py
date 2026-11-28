# Composed after attachments.py and accounts-auth.py in the personal desk Lambda.
# ruff: noqa: F821 -- the source comes from the feedback function and the shared attachment rule.
import time
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryFile

MISSING_OBJECT = {'NoSuchKey', 'NotFound', '404'}
S3_CONFLICT = {'PreconditionFailed', 'ConditionalRequestConflict', '412', '409'}
PICTURE_TYPE = {'jpg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp', 'heic': 'image/heic',
                'avif': 'image/avif', 'tif': 'image/tiff', 'pdf': 'application/pdf'}


def storage(operation, **arguments):
    return getattr(s3, operation)(Bucket=os.environ['BUCKET'], **arguments)


def object_keys(prefix, **arguments):
    return {row['Key'] for row in storage('list_objects_v2', Prefix=prefix, **arguments).get('Contents', [])}


def object_json(key):
    try:
        row = storage('get_object', Key=key)
    except ClientError as exc:
        code = exc.response['Error']['Code']
        # Prefix-scoped ListBucket may cause S3 to report a missing object as 403.
        if code in MISSING_OBJECT or (code == 'AccessDenied' and key not in object_keys(key, MaxKeys=1)):
            return None, None
        raise
    with row['Body'] as body:
        return json.load(body), row['ETag']


def put_once(key, raw, **arguments):
    try:
        storage('put_object', Key=key, Body=raw, IfNoneMatch='*', **arguments)
    except ClientError as exc:
        if exc.response['Error']['Code'] not in {'PreconditionFailed', '412'}:
            raise
        return False
    return True


def logout_key(principal):
    if not re.fullmatch(r'[0-9a-f-]{36}', principal['sub']) or not re.fullmatch(r'[A-Za-z0-9_-]{16}', principal['login']):
        raise ValueError('session')
    return f"feedback-rate/revoked/{principal['sub']}/{principal['login']}"


def files_signed_out(principal):
    key = logout_key(principal)
    return key in object_keys(key, MaxKeys=1)


def files_end_session(principal):
    put_once(logout_key(principal), b'')


def upload_prefix(principal, identity, slot):
    return f"feedback-rate/upload/v2/{principal['sub']}/{identity}/{slot['first']}/"


def quota_key(principal):
    return f"feedback-rate/v2/{principal['sub']}.json"


def inbox_key(identity):
    return f'feedback/inbox/{identity}.json'


def own_message(principal, identity):
    message, _ = object_json(inbox_key(identity))
    if message and message.get('sender', {}).get('sub') != principal['sub']:
        raise Refused('file_failed')
    return message


def missing_originals(identity, message):
    if not message or message.get('attachment_storage') != 2:
        return set()  # Legacy inbox envelopes were written after their attachments.
    saved = object_keys(f'feedback/attachments/{identity}/')
    return {item['n'] for item in message['files'] if remote_attachment_key(identity, item, 2) not in saved}


def files_slots(principal, body):
    identity, files, single = slot_request(body)
    message = own_message(principal, identity)
    if single:
        return single_slots(principal, identity, files[0], message)
    missing = missing_originals(identity, message)
    if message:
        if not missing:
            return {'accepted': True}
        if files != message['files']:
            raise Refused('file_failed')
    slot = update_quota(principal, lambda ledger, now: reserve(ledger, identity, files, now, principal['login']))
    prefix = upload_prefix(principal, identity, slot)
    staged = object_keys(prefix)
    uploads = []
    for item in files:
        n = item['n']
        if message and n not in missing:
            continue
        for part in range(len(part_sizes(item['size']))):
            if f'{prefix}{n}.{part}' not in staged:
                uploads.append({'n': n, 'part': part,
                                'url': f'/api/feedback/file?id={identity}&n={n}&part={part}'})
    return {'uploads': uploads}


def update_quota(principal, edit):
    key = quota_key(principal)
    for attempt in range(8):
        ledger, tag = object_json(key)
        updated, slot = edit(ledger or {}, int(time.time()))
        try:
            if updated != ledger:
                storage('put_object', Key=key, Body=json.dumps(updated).encode(),
                        **({'IfMatch': tag} if tag else {'IfNoneMatch': '*'}))
            return slot
        except ClientError as exc:
            if exc.response['Error']['Code'] not in S3_CONFLICT or attempt == 7:
                raise
            time.sleep((attempt + 1) / 100)


def single_slots(principal, identity, item, message):
    prefix = original_prefix(identity, principal['sub'])
    digest = item['sha256']
    legacy = (message or {}).get('files', [])
    old = next((row for row in legacy if row['sha256'] == digest), None)
    if old and old['n'] not in missing_originals(identity, message):
        return {'accepted': True}

    def reserve_one(ledger, now):
        saved = {row['sha256']: row['size'] for row in original_rows(prefix,
                 storage('list_objects_v2', Prefix=prefix).get('Contents', []))}
        if digest in saved:
            return ledger, None
        saved.update((row['sha256'], row['size']) for row in legacy)
        return reserve_file(ledger, identity, item, saved, now, principal['login'])

    slot = update_quota(principal, reserve_one)
    if slot is None:
        return {'accepted': True} if message else {'uploads': []}
    prefix = upload_prefix(principal, file_transfer(identity, digest), slot)
    return file_slots(identity, item, {key.removeprefix(prefix) for key in object_keys(prefix)})


def current_slot(principal, identity):
    ledger, _ = object_json(quota_key(principal))
    return active_slot(ledger or {}, identity, int(time.time()), principal['login'])


def files_put(principal, query, event):
    identity = str(uuid.UUID(query['id']))
    digest = query.get('sha')
    transfer = file_transfer(identity, digest) if digest is not None else identity
    part_bytes = PART_BYTES if digest is not None else LEGACY_PART_BYTES
    n, part = int(query['n']), int(query['part'])
    raw = event.get('body') or ''
    if not event.get('isBase64Encoded') or len(raw) > 4 * ((part_bytes + 2) // 3):
        raise Refused('file_large', n)
    raw = base64.b64decode(raw, validate=True)
    slot = current_slot(principal, transfer)
    if slot.get('remark') != (identity if digest is not None else None):
        raise Refused('file_failed')
    item = check_part(slot, n, part, len(raw))
    check_part_kind(item, part, raw)
    key = f'{upload_prefix(principal, transfer, slot)}{n}.{part}'
    if not put_once(key, raw):
        with storage('get_object', Key=key)['Body'] as stream:
            if stream.read(part_bytes + 1) != raw:
                raise Refused('file_failed', n)
    return {'n': n}


def files_receipt(principal, identity):
    previous, _ = object_json(inbox_key(identity))
    return bool(previous and previous.get('sender', {}).get('sub') == principal['sub']
                and not missing_originals(identity, previous))


def files_commit(principal, identity, data, files):
    previous = own_message(principal, identity)
    missing = missing_originals(identity, previous)
    if previous and not missing:
        return False
    slot = current_slot(principal, identity)
    rows = check_manifest(slot, files)
    if previous and rows != previous['files']:
        raise Refused('file_failed')

    prefix = upload_prefix(principal, identity, slot)
    created = False
    for item in rows:
        if previous and item['n'] not in missing:
            continue
        with TemporaryFile() as stream:
            read_original(prefix, item, stream, LEGACY_PART_BYTES)
            if slot['until'] <= time.time() or files_signed_out(principal):
                raise Refused('file_failed')
            if previous is None:
                data.update(files=rows, attachment_storage=2)
                created = write_inbox(identity, data)
                previous = data if created else own_message(principal, identity)
                if not previous or previous.get('attachment_storage') != 2 or previous.get('files') != rows:
                    raise Refused('file_failed')
                missing = {r['n'] for r in rows}
            put_original(remote_attachment_key(identity, item, 2), item, stream)
    return created


def read_original(prefix, item, stream, part_bytes):
    def read(part):
        try:
            with storage('get_object', Key=f"{prefix}{item['n']}.{part}")['Body'] as body:
                return body.read(part_bytes + 1)
        except ClientError as exc:
            if exc.response['Error']['Code'] in MISSING_OBJECT | {'AccessDenied'}:
                return None
            raise
    with ThreadPoolExecutor(max_workers=4) as pool:
        parts = pool.map(read, range(len(part_sizes(item['size'], part_bytes))))
        assemble_parts(item, lambda _: next(parts), stream, part_bytes)


def put_original(key, item, stream, **metadata):
    put_once(key, stream, ContentLength=item['size'], ContentType=PICTURE_TYPE[item['kind']],
             ChecksumSHA256=base64.b64encode(bytes.fromhex(item['sha256'])).decode(), **metadata)


def single_commit(principal, identity, data, files):
    if len(files) != 1:
        raise Refused('file_many')
    previous = own_message(principal, identity)
    item = files[0]
    prefix = original_prefix(identity, principal['sub'])
    digest = item['sha256']
    if not object_keys(prefix + digest, MaxKeys=1):
        transfer = file_transfer(identity, digest)
        slot = current_slot(principal, transfer)
        item = check_file_slot(slot, identity, item)
        with TemporaryFile() as stream:
            read_original(upload_prefix(principal, transfer, slot), item, stream, PART_BYTES)
            if slot['until'] <= time.time() or files_signed_out(principal):
                raise Refused('file_failed')
            put_original(original_key(identity, principal['sub'], item), item, stream,
                         Metadata={'name64': b64(item['name'].encode('utf-8'))})
    # Photo-only remarks become visible only after the first verified original.
    if previous is None:
        created = write_inbox(identity, data)
        if not created:
            own_message(principal, identity)
        return created
    return False
