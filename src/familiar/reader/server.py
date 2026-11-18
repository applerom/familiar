# START_MODULE_CONTRACT: MOD-READER-SERVER
# PURPOSE: Serve the packaged reader and checked family generation together without exposing family inputs.
# PRD_REF: docs/PRD.md#ARCH
# INVARIANTS:
# - requests consume pinned checked bytes only while input metadata remains unchanged; loopback aliases share origin checks and persistent conditional delivery [review: engine lead]
# - only delivery files and a path-free manifest are served on loopback [review: engine lead]
# - shell resources match the packaged digest and size manifest before delivery [review: engine lead]
# - the engine licence accompanies the shell without duplicating its source copyright text [review: engine lead]
# - the host-private label and engine version live at the lower edge and in delivered HTML [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-WRITER (checked generation consumption)
# - docs/reader-export.md
# :END_MODULE_CONTRACT
import hashlib
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files as package_files
from pathlib import Path, PurePosixPath
from threading import RLock
from urllib.parse import unquote, urlsplit

from familiar import __version__
from familiar.instance.gate import boundary
from familiar.instance.writer import checked_snapshot

from .export import encode


class LocalHandler(BaseHTTPRequestHandler):
    """Loopback names and conditional delivery shared by both local readers."""
    protocol_version = 'HTTP/1.1'
    disable_nagle_algorithm = True

    def local(self):
        host = self.headers.get('Host', '')
        name, separator, port = host.lower().rpartition(':')
        valid = (separator and port == str(self.server.server_port)
                 and (name in {'127.0.0.1', 'localhost'}
                      or name.endswith('.localhost') and all(
                          part and all(c.isascii() and (c.isalnum() or c == '-') for c in part)
                          for part in name.split('.'))))
        return bool(valid and self.headers.get('Origin', 'http://' + host) == 'http://' + host)

    def deliver_bytes(self, path, data, etag, *, immutable=False):
        tags = [tag.strip().removeprefix('W/')
                for tag in self.headers.get('If-None-Match', '').split(',')]
        unchanged = etag in tags or '*' in tags
        self.send_response(304 if unchanged else 200)
        mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        self.send_header('Content-Type', 'text/javascript' if path.endswith('.js') else mime)
        self.send_header('Content-Length', str(len(data)))
        immutable = ((immutable or etag.strip('"') in PurePosixPath(path).name)
                     and not path.endswith('.html'))
        self.send_header('Cache-Control', 'private, max-age=31536000, immutable'
                         if immutable else 'private, no-cache')
        self.send_header('ETag', etag)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        if self.command != 'HEAD' and not unchanged:
            self.wfile.write(data)
            self.wfile.flush()


def license_bytes(manifest):
    try:
        data = package_files('familiar').joinpath('_licenses/LICENSE').read_bytes()
    except FileNotFoundError:
        data = (Path(__file__).resolve().parents[3] / 'LICENSE').read_bytes()
    expected = manifest['license']
    if len(data) != expected['size'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
        raise ValueError('Engine licence damaged; reinstall Familiar')
    return data


def shell_files():
    root = package_files('familiar').joinpath('_reader_shell')
    manifest = json.loads(root.joinpath('shell-manifest.json').read_bytes())
    result = {}
    for path, expected in manifest['files'].items():
        if (not path or '\\' in path or PurePosixPath(path).is_absolute()
                or any(part in ('.', '..') for part in path.split('/'))):
            raise ValueError('Invalid shell resource path')
        data = root.joinpath(path).read_bytes()
        if len(data) != expected['size'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
            raise ValueError('Reader shell damaged; reinstall Familiar')
        result[path] = data
    if 'index.html' not in result:
        raise ValueError('Reader shell entry missing')
    if 'LICENSE' in result:
        raise ValueError('Engine licence collides with shell resources')
    result['LICENSE'] = license_bytes(manifest)
    return result


@boundary('consume')
def response(instance, out, path):
    return CheckedReader(instance, out).resource(path)[0]


def _resources(instance, files):
    bundle = json.loads(files['bundle.json'])
    def labelled(data):
        if bundle.get('state') != 'host-private':
            return data
        import html

        from familiar.instance.packs import bundled_root, read
        language = instance.source_language
        pack = instance.language_pack_data.get(language, {}).get('data', {})
        if language == 'en' and not pack:
            pack = read(bundled_root() / 'demo-english' / 'pack.toml')
        notice = pack.get('reader_intake', {}).get('private_notice')
        if not notice:
            raise ValueError('Language pack gap: reader_intake.private_notice')
        banner = ('<style>#host-private-notice{position:fixed;bottom:0;left:0;'
                  'z-index:2147483647;background:var(--sheet,#fffdf8);color:var(--ink-mute,#666b64);'
                  'padding:5px 9px;'
                  'font:400 11px/1.2 var(--font-ui,system-ui)}#host-private-notice small{font-weight:400;opacity:.75;margin-left:.5em}</style>'
                  '<div id="host-private-notice" role="note">' + html.escape(notice)
                  + '<small>Familiar ' + html.escape(__version__) + '</small></div>')
        return data.replace(b'<body>', ('<body>' + banner).encode(), 1) if b'<body>' in data else data + banner.encode()
    shell = shell_files()
    if set(shell) & set(bundle['files']):
        raise ValueError('Family delivery collides with packaged shell resources')
    result = dict(shell)
    result['index.html'] = labelled(shell['index.html'])
    tokens = ''.join(f'<link rel="stylesheet" href="/{name}">'
                     for name in shell if name.startswith('assets/tokens-') and name.endswith('.css')).encode()
    # The internal bundle includes private dependency paths. It and generation
    # metadata are not browser resources, even if their names are guessed.
    for path in bundle['files']:
        content = files[path]
        if path.startswith('sources/') and path.endswith('.html'):
            content = content.replace(b'</head>', tokens + b'</head>', 1)
        result[path] = labelled(content) if path.endswith('.html') else content
    result['reader-manifest.json'] = encode({key: bundle[key] for key in ('schema_version', 'family_id', 'state')}
        | {'profile': 'reader-profile.json', 'files': {
            name: (dict(row, sha256=hashlib.sha256(result[name]).hexdigest())
                   if name.endswith('.html') else row)
            for name, row in bundle['files'].items()}})
    return result, {name for name in shell if name.startswith('assets/')}


class CheckedReader:
    def __init__(self, instance, out):
        self.instance, self.out = instance, out
        self.lock = RLock()
        self.reverify()

    @staticmethod
    @boundary('consume')
    def _load(instance, out):
        return checked_snapshot(instance, out)

    def reverify(self):
        """Explicit in-process equivalent of restarting reader serve."""
        with self.lock:
            self.invalid = True
            files, watch, stamp = CheckedReader._load(self.instance, self.out)
            state = json.loads(files['bundle.json'])['state']
            if hasattr(self, 'state') and (state == 'host-private') != (self.state == 'host-private'):
                raise ValueError('reader privacy mode changed; restart with the intended mode')
            resources, self.immutable_paths = _resources(self.instance, files)
            self.resources = {name: (data, '"' + hashlib.sha256(data).hexdigest() + '"')
                              for name, data in resources.items()}
            self.watch, self.stamp = watch, stamp
            self.state = state
            self.invalid = False

    def resource(self, path):
        with self.lock:
            if self.invalid or self.watch.stamp() != self.stamp:
                self.invalid = True
                raise ValueError('reader inputs changed; rebuild and restart the reader')
            try:
                return self.resources[path or 'index.html']
            except KeyError:
                raise FileNotFoundError(path) from None


def server(instance, out, port=0, *, host_private=None):
    reader = CheckedReader(instance, out)
    if host_private is not None and (reader.state == 'host-private') != host_private:
        raise ValueError('host-private reader requires explicit --host-private; rebuild to change mode')
    class Handler(LocalHandler):
        def do_GET(self):
            self.deliver()

        def do_HEAD(self):
            self.deliver(head=True)

        def deliver(self, head=False):
            if not self.local():
                self.send_error(403, 'Loopback origin required')
                return
            path = unquote(urlsplit(self.path).path).lstrip('/')
            try:
                data, etag = reader.resource(path)
            except FileNotFoundError:
                self.send_error(404, 'No reader resource')
                return
            except (ValueError, OSError, KeyError, TypeError):
                self.send_error(409, 'Reader inputs changed or unavailable; rebuild and restart')
                return
            self.deliver_bytes(path or 'index.html', data, etag,
                               immutable=path in reader.immutable_paths)

    httpd = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    httpd.reverify = reader.reverify
    return httpd


def serve(instance, out, port, *, host_private=None):
    with server(instance, out, port, host_private=host_private) as httpd:
        print(f'Family reader: http://127.0.0.1:{httpd.server_port}/', flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
