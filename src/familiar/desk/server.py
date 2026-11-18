# START_MODULE_CONTRACT: MOD-DESK-SERVER
# PURPOSE: Let the host use the owner desk on loopback with working narrator feedback.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - only a decision-bound built allowlist is served, on 127.0.0.1 exclusively [review: engine lead]
# - local feedback uses the family writer with explicit loopback origin, without editing accepted memory [review: engine lead]
# - localhost aliases require their own origin; consecutive feedback has no local cooldown [review: engine lead]
# - requested reader receipts reflect current read marks without rebuilding the checked desk [review: engine lead]
# CHANGES_WITH:
# - MOD-DESK-AWS-TEMPLATE (feedback HTTP parity)
# - MOD-DESK-CLI (serve lifetime)
# :END_MODULE_CONTRACT
import json
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from familiar.instance.writer import desk_feedback, encode
from familiar.reader.server import LocalHandler

from .build import CheckedDesk
from .feedback import matches, preserve_tender, receipt, received, research_feedback, validate


def server(instance, port=0):
    desk = CheckedDesk(instance)
    class Handler(LocalHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, body=b'', content_type='application/json; charset=utf-8'):
            if self.command == 'POST' and status >= 400:
                self.close_connection = True
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Robots-Tag', 'noindex,nofollow,noarchive')
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)

        def do_GET(self):
            if not self.local():
                return self.reply(403)
            parsed = urlsplit(self.path)
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
                    item = json.loads(path.read_bytes())
                    if not research_feedback(item) and (item.get('id') in identities or matches(item, subject)):
                        items.append(item | receipt(instance, item['id']))
                return self.reply(200, encode({'items': items}))
            try:
                name = unquote(parsed.path).lstrip('/') or 'index.html'
                data, etag = desk.resource(name)
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
            if urlsplit(self.path).path != '/api/feedback':
                return self.reply(404)
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                return self.reply(415)
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 20000:
                    return self.reply(413)
                data = validate(self.rfile.read(size))
                path = instance._inside('family/feedback/inbox/' + data['id'] + '.json')
                if path.exists():
                    desk_feedback(instance, data['id'], path.read_bytes(), local=True)
                    return self.reply(200, encode({'id': data['id'], 'duplicate': True}))
                from .model import decision
                host = json.loads(decision(instance)[1])['host']
                envelope = received(preserve_tender(instance, data)) | {'sender': {'role': 'owner', 'username': host}}
                desk_feedback(instance, data['id'], encode(envelope), local=True)
                return self.reply(201, encode({'id': data['id']}))
            except (ValueError, TypeError, KeyError, UnicodeError):
                return self.reply(400, encode({'error': 'invalid_feedback'}))

    http = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    http.daemon_threads = True
    return http


def serve(instance, port=0):
    with server(instance, port) as http:
        print(f'Desk: http://127.0.0.1:{http.server_port}/ — Ctrl+C to stop', flush=True)
        try:
            http.serve_forever()
        except KeyboardInterrupt:
            pass
