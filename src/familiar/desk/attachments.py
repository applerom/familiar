# START_MODULE_CONTRACT: MOD-DESK-ATTACHMENTS
# PURPOSE: One rule for the scans and photographs a relative attaches to a remark, on loopback and hosted.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - a file is accepted by its first bytes, never by its name or declared type; names are display text only [review: engine lead]
# - message limits and each sender's rolling quota are reserved together; retries pin an immutable manifest [review: engine lead]
# - standard library only: the hosted function carries this file verbatim, so both paths share one table [review: engine lead]
# CHANGES_WITH:
# - MOD-DESK-SERVER (loopback upload and commit)
# - MOD-DESK-ACCOUNTS (hosted composition with aws/accounts-files.py)
# - MOD-DESK-FEEDBACK (envelope `files`)
# :END_MODULE_CONTRACT
import base64
import hashlib
import json
import re
import unicodedata
import uuid

MB = 1024 * 1024
PART_BYTES = MB  # Retry a small slice of a photograph after an interruption.
LEGACY_PART_BYTES = 3 * MB
SLOT_SECONDS = 900
UPLOAD_SECONDS = 86400
# A phone photograph is 3-12 MB, a multi-page scan from a phone app can be larger.
ATTACH_LIMITS = {'file_bytes': 30 * MB, 'message_files': 10, 'message_bytes': 100 * MB,
                 'day_files': 40, 'day_bytes': 300 * MB, 'head_bytes': 64,
                 'part_bytes': LEGACY_PART_BYTES, 'single_part_bytes': PART_BYTES}
ATTACH_KINDS = {'jpg', 'png', 'webp', 'heic', 'avif', 'tif', 'pdf'}
HEIF_BRANDS = {b'heic', b'heix', b'heim', b'heis', b'hevc', b'hevx', b'hevm', b'hevs', b'mif1', b'msf1'}


class Refused(ValueError):
    """A plain reason for the sender: file_kind, file_large, file_many, file_day, file_failed."""

    def __init__(self, reason, n=0):
        super().__init__(reason)
        self.reason, self.n = reason, n

    def body(self):
        return {'error': self.reason} | ({'file': self.n} if self.n else {})


def attachment_kind(head):
    """The picture or scan a file is, by content; None for anything else."""
    if head.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if head.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return 'webp'
    if head[4:8] == b'ftyp' and head[8:12] in HEIF_BRANDS:
        return 'heic'
    if head[4:8] == b'ftyp' and head[8:12] in {b'avif', b'avis'}:
        return 'avif'
    if head[:4] in {b'II*\x00', b'MM\x00*'}:
        return 'tif'
    if head.startswith(b'%PDF-'):
        return 'pdf'
    return None


def display_name(value):
    """A sender's file name as words to show the host, never a path."""
    text = unicodedata.normalize('NFC', value if isinstance(value, str) else '')
    text = text.replace('\\', '/').rsplit('/', 1)[-1]
    return ''.join(c for c in text if unicodedata.category(c)[0] != 'C').strip()[:120]


def admit(files, used_files=0, used_bytes=0):
    """Kinds for the files of one message, or Refused; `head` is the file's first bytes."""
    if not isinstance(files, list) or not files:
        raise Refused('file_failed')
    if len(files) > ATTACH_LIMITS['message_files'] or used_files + len(files) > ATTACH_LIMITS['day_files']:
        raise Refused('file_many' if len(files) > ATTACH_LIMITS['message_files'] else 'file_day')
    kinds, total = [], 0
    for n, item in enumerate(files, 1):
        size = item.get('size') if isinstance(item, dict) else None
        if type(size) is not int or size <= 0 or not isinstance(item.get('head'), bytes):
            raise Refused('file_kind', n)
        if size > ATTACH_LIMITS['file_bytes']:
            raise Refused('file_large', n)
        kind = attachment_kind(item['head'])
        if not kind:
            raise Refused('file_kind', n)
        kinds.append(kind)
        total += size
    if total > ATTACH_LIMITS['message_bytes']:
        raise Refused('file_large')
    if used_bytes + total > ATTACH_LIMITS['day_bytes']:
        raise Refused('file_day')
    return kinds


def slot_request(body):
    """The sender asks to upload: message id and, per file, its size, name and first bytes."""
    if len(body) > 20000:
        raise Refused('file_many')
    data = json.loads(body)
    if not isinstance(data, dict) or not isinstance(data.get('files'), list):
        raise Refused('file_failed')
    identity = str(uuid.UUID(data['id']))
    files = data['files']
    single = data.get('single') is True
    if len(files) > ATTACH_LIMITS['message_files'] or single and len(files) != 1:
        raise Refused('file_many')
    heads = []
    for n, item in enumerate(files, 1):
        if not isinstance(item, dict) or not isinstance(item.get('head'), str) or len(item['head']) > 88:
            raise Refused('file_kind', n)
        heads.append({'size': item.get('size'), 'head': base64.b64decode(item['head'], validate=True)})
    kinds = admit(heads)
    manifest = declared([{'n': n, 'size': item['size'], 'sha256': item.get('sha256'), 'name': item.get('name')}
                         for n, item in enumerate(files, 1)])
    return identity, [item | {'kind': kind} for item, kind in zip(manifest, kinds)], single


def declared(files):
    """The envelope's `files` as the sender declares them before the server checks the bytes."""
    if not isinstance(files, list) or not 1 <= len(files) <= ATTACH_LIMITS['message_files']:
        raise ValueError('invalid_feedback')
    result = []
    for n, item in enumerate(files, 1):
        if (not isinstance(item, dict) or set(item) - {'n', 'size', 'sha256', 'name'} or item.get('n') != n
                or type(item.get('size')) is not int or not 0 < item['size'] <= ATTACH_LIMITS['file_bytes']
                or not isinstance(item.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
            raise ValueError('invalid_feedback')
        result.append({'n': n, 'size': item['size'], 'sha256': item['sha256'], 'name': display_name(item.get('name'))})
    return result


def quota_ledger(ledger, now):
    return {key: slot for key, slot in ledger.items() if slot['until'] + UPLOAD_SECONDS > now}


def reserve(ledger, identity, files, now, login):
    """One charge per manifest, kept for a full day after its last active grant."""
    ledger = quota_ledger(ledger, now)
    slot = ledger.get(identity)
    if slot:
        if slot['files'] != files or slot['first'] + UPLOAD_SECONDS <= now:
            raise Refused('file_failed')
    else:
        reserved = [item for old in ledger.values() for item in old['files']]
        if (len(reserved) + len(files) > ATTACH_LIMITS['day_files']
                or sum(f['size'] for f in reserved + files) > ATTACH_LIMITS['day_bytes']):
            raise Refused('file_day')
        slot = {'first': now, 'files': files}
    slot = slot | {'login': login, 'until': min(now + SLOT_SECONDS, slot['first'] + UPLOAD_SECONDS)}
    return ledger | {identity: slot}, slot


def file_transfer(identity, digest):
    if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
        raise Refused('file_failed')
    return str(uuid.uuid5(uuid.UUID(identity), digest))


def reserve_file(ledger, identity, item, saved, now, login):
    """Count durable and in-flight files together. A digest can only use one place."""
    key = file_transfer(identity, item['sha256'])
    ledger = quota_ledger(ledger, now)
    related = {s['files'][0]['sha256']: s['files'][0]['size'] for s in ledger.values()
               if s.get('remark') == identity and s['first'] + UPLOAD_SECONDS > now}
    related.update(saved)
    related[item['sha256']] = item['size']
    if len(related) > ATTACH_LIMITS['message_files']:
        raise Refused('file_many')
    if sum(related.values()) > ATTACH_LIMITS['message_bytes']:
        raise Refused('file_batch_large')
    old = ledger.get(key)
    if old and old.get('remark') != identity:
        raise Refused('file_failed')
    if old and old['first'] + UPLOAD_SECONDS > now:
        item = check_file_slot(old, identity, item)
    elif old:
        ledger.pop(key)
    result, slot = reserve(ledger, key, [item], now, login)
    slot = slot | {'remark': identity, 'until': min(now + 35 * 60, slot['first'] + UPLOAD_SECONDS)}
    return result | {key: slot}, slot


def check_file_slot(slot, identity, item):
    saved = slot['files'][0]
    if (slot.get('remark') != identity or item['sha256'] != saved['sha256'] or item['size'] != saved['size']):
        raise Refused('file_failed')
    return saved


def file_slots(identity, item, staged):
    digest = item['sha256']
    return {'uploads': [{'n': 1, 'part': p, 'url': f'/api/feedback/file?id={identity}&n=1&part={p}&sha={digest}'}
                        for p in range(len(part_sizes(item['size'], PART_BYTES))) if f'1.{p}' not in staged]}


def active_slot(ledger, identity, now, login):
    slot = ledger.get(identity)
    if not slot or slot['until'] <= now or slot['login'] != login:
        raise Refused('file_failed')
    return slot


def part_sizes(size, part_bytes=LEGACY_PART_BYTES):
    return [min(part_bytes, size - offset) for offset in range(0, size, part_bytes)]


def check_part(slot, n, part, length):
    if not 1 <= n <= len(slot['files']):
        raise Refused('file_failed', n)
    item = slot['files'][n - 1]
    sizes = part_sizes(item['size'], PART_BYTES if slot.get('remark') else LEGACY_PART_BYTES)
    if not 0 <= part < len(sizes) or length != sizes[part]:
        raise Refused('file_large', n)
    return item


def check_manifest(slot, files):
    if [{k: row[k] for k in ('n', 'size', 'sha256', 'name')} for row in slot['files']] != files:
        raise Refused('file_failed')
    return slot['files']


def check_part_kind(item, part, raw):
    if part == 0 and attachment_kind(raw[:ATTACH_LIMITS['head_bytes']]) != item['kind']:
        raise Refused('file_kind', item['n'])


def assemble_parts(item, read, output, part_bytes=LEGACY_PART_BYTES):
    digest, length = hashlib.sha256(), 0
    for part, size in enumerate(part_sizes(item['size'], part_bytes)):
        raw = read(part)
        if raw is None or len(raw) != size:
            raise Refused('file_failed', item['n'])
        check_part_kind(item, part, raw)
        digest.update(raw)
        output.write(raw)
        length += len(raw)
    if length != item['size'] or digest.hexdigest() != item['sha256']:
        raise Refused('file_failed', item['n'])
    output.seek(0)


def remote_attachment_key(identity, item, version=1):
    suffix = '-' + item['sha256'] if version == 2 else ''
    return f"feedback/attachments/{identity}/{item['n']}{suffix}.{item['kind']}"


def original_prefix(identity, sender):
    return f'feedback/attachments/{uuid.UUID(identity)}/v3/{uuid.UUID(sender)}/'


def original_key(identity, sender, item):
    return original_prefix(identity, sender) + item['sha256'] + '.' + item['kind']


def original_rows(prefix, objects):
    for obj in objects:
        match = re.fullmatch(r'([0-9a-f]{64})\.([a-z]{3,4})', obj['Key'].removeprefix(prefix))
        if match:
            yield {'sha256': match[1], 'kind': match[2], 'size': obj['Size']}


def stored_attachment(item):
    n, kind, size, digest = (item[k] for k in ('n', 'kind', 'size', 'sha256'))
    if (type(n) is not int or not 1 <= n <= ATTACH_LIMITS['message_files']
            or kind not in ATTACH_KINDS or type(size) is not int or not 0 < size <= ATTACH_LIMITS['file_bytes']
            or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)):
        raise ValueError('invalid attachment metadata')
