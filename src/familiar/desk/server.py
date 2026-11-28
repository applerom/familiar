# START_MODULE_CONTRACT: MOD-DESK-SERVER
# PURPOSE: Let the host use the owner desk on loopback with working narrator feedback.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - only a decision-bound built allowlist is served, on 127.0.0.1 exclusively [review: engine lead]
# - local feedback uses the family writer with explicit loopback origin, without editing accepted memory [review: engine lead]
# - localhost aliases require their own origin; consecutive feedback has no local cooldown [review: engine lead]
# - requested reader receipts reflect current read marks without rebuilding the checked desk [review: engine lead]
# - attached files wait in engine state until their message is accepted; only checked bytes reach the originals [review: engine lead]
# - account controls are assembled on loopback; cloud bundles never contain the page or handouts [review: engine lead]
# CHANGES_WITH:
# - MOD-DESK-AWS-TEMPLATE (feedback HTTP parity)
# - MOD-DESK-CLI (serve lifetime)
# - MOD-DESK-ATTACHMENTS (same limits as the hosted function)
# :END_MODULE_CONTRACT
import io
import json
import time
import uuid
from http.server import ThreadingHTTPServer
from importlib.resources import files
from types import SimpleNamespace
from urllib.parse import parse_qs, unquote, urlencode, urlsplit

from familiar.instance.writer import (attachment_catalog, attachment_path, desk_add_feedback_file,
                                      desk_attachment_parts, desk_attachment_stage, desk_expire_feedback_writes,
                                      desk_expire_uploads, desk_feedback, desk_loopback, desk_upload_ledger, encode)
from familiar.reader.server import LocalHandler

from .attachments import (LEGACY_PART_BYTES, PART_BYTES, UPLOAD_SECONDS, Refused, active_slot, assemble_parts,
                          check_file_slot, check_manifest, check_part, check_part_kind, file_slots, file_transfer,
                          part_sizes, quota_ledger, reserve, reserve_file, slot_request)
from .build import CheckedDesk
from .feedback import matches, preserve_tender, receipt, received, research_feedback, validate

USERS_PAGE = '/desk/local-users.html'
USERS_API = '/api/local-users'


def personal_desk(instance):
    publication = instance.config.get('publication', {})
    return publication.get('target') == 'aws' and publication.get('login') == 'personal'


def account_request(instance, desk, body):
    from .accounts import execute, living_name
    request = json.loads(body)
    action = request['action']
    if action not in {'list', 'add', 'reset', 'disable'}:
        raise ValueError('Unknown account action')
    args = SimpleNamespace(user_action=action, person=request.get('person'), username=request.get('username'),
                           role='reader', email=None)
    if action == 'add':
        if not isinstance(args.person, str) or args.username is not None:
            raise ValueError('Create a reader account by person')
    answer = execute(instance, args, owner_page=True)
    if action == 'list':
        graph = json.loads(desk.resource('graph.json')[0])
        people = graph['people']
        aliases = graph.get('identityAliases', {})
        existing = set()
        for user in answer['users']:
            pid = aliases.get(user['person'], user['person'])
            existing.add(pid)
            user['name'] = people.get(pid, {}).get('name') or ''
        answer['eligible'] = [{'id': pid, 'name': name} for pid, person in people.items()
                              if pid not in existing and (name := living_name(person))]
        answer.pop('last_login_note')
    return answer


def message_path(instance, identity):
    return instance._inside('family/feedback/inbox/' + identity + '.json')


def file_received(instance, identity, item, *, added=False):
    path = attachment_path(instance, identity, item['n'], item['kind'], item['sha256'] if added else None)
    return path.is_file() and path.stat().st_size == item['size']


def all_received(instance, identity, envelope):
    return all(file_received(instance, identity, item) for item in envelope.get('files', []))


def upload_slots(instance, body):
    identity, files, single = slot_request(body)
    path = message_path(instance, identity)
    if single:
        item = files[0]
        digest = item['sha256']
        catalog = attachment_catalog(instance, identity)
        saved = {row['sha256']: row['size'] for row in catalog}
        if any(row['sha256'] == digest and file_received(instance, identity, row, added=True) for row in catalog):
            return {'accepted': True} if path.is_file() else {'uploads': []}
        if path.is_file():
            legacy = json.loads(path.read_bytes()).get('files', [])
            if any(row['sha256'] == digest and file_received(instance, identity, row) for row in legacy):
                return {'accepted': True}
            saved.update((row['sha256'], row['size']) for row in legacy)
        ledger, slot = reserve_file(desk_upload_ledger(instance), identity, item, saved, int(time.time()), 'local')
        desk_upload_ledger(instance, ledger)
        transfer = file_transfer(identity, digest)
        return file_slots(identity, item, desk_attachment_parts(instance, transfer, slot['first']))
    if path.is_file():
        envelope = json.loads(path.read_bytes())
        if all_received(instance, identity, envelope):
            return {'accepted': True}
        if files != envelope.get('files'):
            raise Refused('file_failed')
    ledger, slot = reserve(desk_upload_ledger(instance), identity, files, int(time.time()), 'local')
    desk_upload_ledger(instance, ledger)
    staged = desk_attachment_parts(instance, identity, slot['first'])
    uploads = []
    for item in files:
        n = item['n']
        if path.is_file() and file_received(instance, identity, item):
            continue
        for part in range(len(part_sizes(item['size']))):
            if f'{n}.{part}' not in staged:
                query = urlencode({'id': identity, 'n': n, 'part': part})
                uploads.append({'n': n, 'part': part, 'url': '/api/feedback/file?' + query})
    return {'uploads': uploads}


def accept_feedback(instance, body, *, desk=None):
    from .feedback_offer import amendment_offered, amendment_reply
    data = validate(body)
    identity = data['id']
    path = message_path(instance, identity)
    content = path.read_bytes() if path.is_file() else None
    previous = json.loads(content) if content else None
    is_amendment = amendment_reply(data)
    if is_amendment and not previous:
        from .build import CheckedDesk
        links, _ = (desk or CheckedDesk(instance)).resource('desk/asks-links.json')
        if not amendment_offered(data, json.loads(links)) or 'files' in data:
            raise ValueError('invalid_feedback')
    single = data.pop('file_upload', False) is True and 'files' in data
    if single:
        files = data.pop('files')
        if len(files) != 1:
            raise Refused('file_many')
        item = files[0]
        if not any(row['sha256'] == item['sha256'] and file_received(instance, identity, row, added=True)
                   for row in attachment_catalog(instance, identity)):
            transfer = file_transfer(identity, item['sha256'])
            slot = active_slot(desk_upload_ledger(instance), transfer, int(time.time()), 'local')
            item = check_file_slot(slot, identity, item)
            output = io.BytesIO()
            assemble_parts(item, lambda p: desk_attachment_stage(instance, transfer, slot['first'], 1, p),
                           output, PART_BYTES)
            desk_add_feedback_file(instance, previous or data, item, output.getvalue())
    if previous and (single or 'files' not in data or all_received(instance, identity, previous)):
        desk_feedback(instance, identity, content, local=True)
        return 200, {'id': identity, 'duplicate': True} | (
            {} if amendment_reply(previous) else {'text': previous.get('text', '')})
    attachments = []
    if 'files' in data:
        slot = active_slot(desk_upload_ledger(instance), identity, int(time.time()), 'local')
        data['files'] = check_manifest(slot, data['files'])
        if previous and previous.get('files') != data['files']:
            raise Refused('file_failed')
        for item in data['files']:
            n = item['n']
            if previous and file_received(instance, identity, item):
                continue
            output = io.BytesIO()
            assemble_parts(item, lambda part: desk_attachment_stage(instance, identity, slot['first'], n, part), output)
            attachments.append((n, item['kind'], output.getvalue()))
    if content is None:
        from .model import decision
        host = json.loads(decision(instance)[1])['host']
        envelope = received(preserve_tender(instance, data)) | {'sender': {'role': 'owner', 'username': host, 'loopback': True}}
        if is_amendment:
            envelope['amendment_offered'] = True
        content = encode(envelope)
    desk_feedback(instance, identity, content, local=True, attachments=attachments)
    return 201, {'id': identity}


class DeskHTTPServer(ThreadingHTTPServer):
    next_cleanup = 0

    def service_actions(self):
        now = int(time.time())
        if now < self.next_cleanup:
            return
        self.next_cleanup = now + 60
        try:
            with desk_loopback(self.instance):
                desk_expire_feedback_writes(self.instance, now)
                ledger = desk_upload_ledger(self.instance)
                active = quota_ledger(ledger, now)
                desk_expire_uploads(self.instance, {k: v for k, v in active.items() if v['first'] + UPLOAD_SECONDS > now})
                if active != ledger:
                    desk_upload_ledger(self.instance, active)
        except (OSError, ValueError, RuntimeError) as error:
            print(f'Desk upload cleanup: {error}', flush=True)


def server(instance, port=0):
    desk = CheckedDesk(instance)
    class Handler(LocalHandler):
        timeout = 30

        def upload_origin(self):
            return self.local() and self.headers.get('Origin') == 'http://' + self.headers['Host']

        def log_message(self, *_):
            pass

        def reply(self, status, body=b'', content_type='application/json; charset=utf-8'):
            if self.command in {'PUT', 'POST'} and status >= 400:
                self.close_connection = True
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Robots-Tag', 'noindex,nofollow,noarchive')
            if urlsplit(self.path).path == USERS_PAGE:
                self.send_header('Content-Security-Policy',
                                 "default-src 'none'; script-src 'self'; connect-src 'self'; style-src 'unsafe-inline'; "
                                 "frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            try:
                self.end_headers()
                if self.command != 'HEAD':
                    self.wfile.write(body)
            except ConnectionError:
                self.close_connection = True  # A retry can query the stored receipt.

        def do_GET(self):
            if not self.local():
                return self.reply(403)
            parsed = urlsplit(self.path)
            if personal_desk(instance) and parsed.path in {USERS_PAGE, '/desk/local-users.js'}:
                name = parsed.path.rsplit('/', 1)[1]
                payload = files('familiar.desk').joinpath('assets', name).read_bytes()
                content_type = 'text/html' if name.endswith('.html') else 'text/javascript'
                return self.reply(200, payload, content_type + '; charset=utf-8')
            if parsed.path == '/api/feedback/receipt':
                try:
                    identity = str(uuid.UUID(parse_qs(parsed.query)['id'][0]))
                    path = message_path(instance, identity)
                    accepted = path.is_file() and all_received(instance, identity, json.loads(path.read_bytes()))
                    return self.reply(200, encode({'accepted': accepted}))
                except (KeyError, ValueError, OSError):
                    return self.reply(400, encode({'error': 'invalid_feedback'}))
            if parsed.path == '/api/feedback':
                try:
                    desk.check()
                except (OSError, ValueError):
                    return self.reply(409, encode({'error': 'desk_changed_rebuild'}))
                query = parse_qs(parsed.query)
                subject = query.get('subject', [''])[0]
                identities = set(query.get('ids', [''])[0].split(',')) - {''}
                if not identities and (not subject or len(subject) > 200):
                    return self.reply(400, encode({'error': 'subject_required'}))
                items = []
                for path in sorted(instance._inside('family/feedback/inbox').glob('*.json')):
                    try:
                        item = json.loads(path.read_bytes())
                        if not isinstance(item, dict):
                            continue
                    except (OSError, ValueError):
                        continue
                    if not research_feedback(item) and (item.get('id') in identities or matches(item, subject)):
                        items.append(item | receipt(instance, item['id']))
                return self.reply(200, encode({'items': items}))
            try:
                name = unquote(parsed.path).lstrip('/') or 'index.html'
                data, etag = desk.resource(name)
                if personal_desk(instance) and name.endswith('.html') and b'<nav id="desk-more" hidden>' in data:
                    label = 'Входы для родных' if instance.source_language == 'ru' else 'Family logins'
                    entry = f'<nav id="desk-more" hidden><a href="{USERS_PAGE}">{label}</a>'.encode('utf-8')
                    data = data.replace(b'<nav id="desk-more" hidden>', entry, 1)
                    etag = etag[:-1] + '-local-users-' + instance.source_language + '"'
                return self.deliver_bytes(name, data, etag, immutable=name in desk.immutable_paths)
            except KeyError:
                return self.reply(404)
            except (OSError, ValueError):
                return self.reply(409, encode({'error': 'desk_changed_rebuild'}))

        def do_HEAD(self):
            self.do_GET()

        def do_POST(self):
            if not self.local():
                return self.reply(403)
            try:
                desk.check()
            except (OSError, ValueError):
                return self.reply(409, encode({'error': 'desk_changed_rebuild'}))
            route = urlsplit(self.path).path
            if route == USERS_API and personal_desk(instance):
                return self.account_post()
            if route not in {'/api/feedback', '/api/feedback/files'}:
                return self.reply(404)
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                return self.reply(415)
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 20000:
                    return self.reply(413)
                body = self.rfile.read(size)
                with desk_loopback(instance):
                    if route == '/api/feedback/files':
                        if not self.upload_origin():
                            return self.reply(403)
                        return self.reply(200, encode(upload_slots(instance, body)))
                    result, answer = accept_feedback(instance, body, desk=desk)
                return self.reply(result, encode(answer))
            except Refused as refusal:
                return self.reply(400, encode(refusal.body()))
            except (ValueError, TypeError, KeyError, UnicodeError):
                return self.reply(400, encode({'error': 'invalid_feedback'}))
            except (OSError, RuntimeError):
                return self.reply(503, encode({'error': 'file_failed'}))

        def account_post(self):
            if not self.upload_origin():
                return self.reply(403)
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                return self.reply(415)
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 2048:
                    return self.reply(413)
                return self.reply(200, encode(account_request(instance, desk, self.rfile.read(size))))
            except (KeyError, TypeError, ValueError):
                return self.reply(400, encode({'error': 'account_request_refused'}))
            except (OSError, RuntimeError):
                return self.reply(503, encode({'error': 'account_service_unavailable'}))

        def do_PUT(self):
            if not self.upload_origin():
                return self.reply(403)
            parsed = urlsplit(self.path)
            if parsed.path != '/api/feedback/file':
                return self.reply(404)
            if self.headers.get('Content-Type') != 'application/octet-stream':
                return self.reply(415)
            try:
                query = parse_qs(parsed.query)
                identity = str(uuid.UUID(query['id'][0]))
                digest = query.get('sha', [None])[0]
                transfer = file_transfer(identity, digest) if digest is not None else identity
                n, part = int(query['n'][0]), int(query['part'][0])
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= (PART_BYTES if digest is not None else LEGACY_PART_BYTES):
                    raise Refused('file_large', n)
                with desk_loopback(instance):
                    slot = active_slot(desk_upload_ledger(instance), transfer, int(time.time()), 'local')
                    if slot.get('remark') != (identity if digest is not None else None):
                        raise Refused('file_failed')
                    check_part(slot, n, part, size)
                first = slot['first']
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise Refused('file_failed', n)
                with desk_loopback(instance):
                    slot = active_slot(desk_upload_ledger(instance), transfer, int(time.time()), 'local')
                    if slot['first'] != first or slot.get('remark') != (identity if digest is not None else None):
                        raise Refused('file_failed', n)
                    item = check_part(slot, n, part, size)
                    check_part_kind(item, part, raw)
                    desk_attachment_stage(instance, transfer, slot['first'], n, part, raw)
                return self.reply(201, encode({'n': n}))
            except Refused as refusal:
                return self.reply(400, encode(refusal.body()))
            except (ValueError, TypeError, KeyError, IndexError):
                return self.reply(400, encode({'error': 'file_failed'}))
            except (OSError, RuntimeError):
                return self.reply(503, encode({'error': 'file_failed'}))

    http = DeskHTTPServer(('127.0.0.1', port), Handler)
    http.instance = instance
    http.daemon_threads = True
    return http


def serve(instance, port=0):
    with server(instance, port) as http:
        print(f'Desk: http://127.0.0.1:{http.server_port}/ — Ctrl+C to stop', flush=True)
        try:
            http.serve_forever()
        except KeyboardInterrupt:
            pass
