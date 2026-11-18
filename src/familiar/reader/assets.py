# START_MODULE_CONTRACT: MOD-READER-ASSETS
# PURPOSE: Resolve permanent family media by stable identifier and verify every delivered byte.
# PRD_REF: docs/PRD.md#INSTANCE
# INVARIANTS:
# - media paths and digests cannot escape or silently change [review: engine lead]
# - embedded metadata cannot cross an unrecognized binary format [review: engine lead]
# - asset collection follows declared reference fields, never same-named prose [review: engine lead]
# - a document's anchor to the reader root is navigation, never a media dependency [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (all reachable asset text is scanned by the projection)
# - docs/reader-export.md
# :END_MODULE_CONTRACT
import json
import posixpath
from html.parser import HTMLParser
from pathlib import PurePosixPath


def sha256(path):
    from familiar.instance.writer import input_digest
    return input_digest(path)


def publication_bytes(data, name):
    """Default-deny embedded metadata; original bytes are never edited.

    Only rendering chunks are declared for binary images. Opaque formats need
    a supported derivative; changing a file extension does not grant publication.
    """
    if name.endswith(('.html', '.svg', '.txt')):
        data.decode('utf-8-sig')
        return data
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        allowed = {b'IHDR', b'PLTE', b'IDAT', b'IEND', b'tRNS', b'sRGB', b'gAMA', b'cHRM', b'pHYs', b'sBIT'}
        at = 8
        while at + 12 <= len(data):
            length = int.from_bytes(data[at:at + 4], 'big')
            kind = data[at + 4:at + 8]
            if kind not in allowed or at + length + 12 > len(data):
                raise ValueError(f'undeclared embedded PNG metadata or invalid chunk: {kind!r}')
            at += length + 12
            if kind == b'IEND':
                if at != len(data):
                    raise ValueError('undeclared trailing image metadata')
                return data
        raise ValueError('incomplete PNG')
    if data.startswith(b'\xff\xd8'):
        if not data.endswith(b'\xff\xd9'):
            raise ValueError('incomplete JPEG or undeclared trailing metadata')
        # Entropy coding escapes literal FF bytes; these sequences are markers.
        for marker in [*range(0xE1, 0xEE), 0xEF, 0xFE]:
            if bytes([0xFF, marker]) in data:
                raise ValueError('undeclared embedded JPEG metadata; use a clean derivative')
        for marker, signature in [(0xE0, b'JFIF\x00'), (0xEE, b'Adobe')]:
            at = 0
            while (at := data.find(bytes([0xFF, marker]), at)) >= 0:
                if data[at + 4:at + 9] != signature:
                    raise ValueError('undeclared JPEG application segment')
                length = int.from_bytes(data[at + 2:at + 4], 'big')
                if (marker == 0xE0 and (at + 18 > len(data) or length != 16 + 3 * data[at + 16] * data[at + 17])) or (marker == 0xEE and length != 14):
                    raise ValueError('undeclared JPEG application metadata length')
                at += 2
        return data
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        at = 12
        while at + 8 <= len(data):
            kind = data[at:at + 4]
            length = int.from_bytes(data[at + 4:at + 8], 'little')
            if kind not in {b'VP8 ', b'VP8L', b'VP8X', b'ALPH', b'ANIM', b'ANMF'}:
                raise ValueError('undeclared embedded WebP metadata')
            at += 8 + length + length % 2
        if at == len(data):
            return data
        raise ValueError('invalid WebP')
    raise ValueError('unsupported opaque reader media; supply PNG, JPEG, WebP or checked textual derivative')


def relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('invalid bundle path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ('', '.', '..') for p in value.split('/')):
        raise ValueError('invalid bundle path')
    return path.as_posix()


def contained(root, value):
    path = (root / relative(value)).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('media path escapes its root')
    return path


def catalog(instance):
    root = instance.path('media')
    file = root / 'manifest.json'
    if not file.is_file():
        return {}
    data = json.loads(file.read_text(encoding='utf-8'))
    if data.get('schema_version') != 1 or type(data.get('schema_version')) is not int:
        raise ValueError('unsupported media manifest version')
    result, ids = {}, set()
    for row in data['assets']:
        if not isinstance(row.get('id'), str) or not row['id'] or row['id'] in ids:
            raise ValueError('media ids must be unique nonempty strings')
        ids.add(row['id'])
        public = relative(row['export'])
        if public in result or public in {'graph.json', 'reader-profile.json', 'bundle.json'}:
            raise ValueError('duplicate or reserved media output')
        if not row.get('kind') or not row.get('origin'):
            raise ValueError('media kind and family origin are required')
        source = contained(root, row['file'])
        if not source.is_file() or sha256(source) != row['sha256']:
            raise ValueError(f'media checksum mismatch: {row["id"]}')
        result[public] = (row, source)
    return result


def used_assets(value, assets):
    """Collect local references, including inline HTML and Markdown image URLs."""
    import re

    from familiar.instance.publication import SCHEMAS
    used = set()
    def walk(node, shape='graph'):
        if node is None:
            return
        if isinstance(shape, tuple):
            for child in node.values():
                walk(child, shape[1])
            return
        if isinstance(shape, list):
            for child in node:
                walk(child, shape[0])
            return
        if isinstance(node, dict):
            schema = SCHEMAS.get(shape, {})
            for key, child in node.items():
                child_shape = schema[key].shape if key in schema else 'text'
                direct = key in {'asset', 'full', 'cover', 'orig', 'originalAsset'}
                direct |= (shape, key) in {('game-truth', 'record'), ('source', 'image')}
                if direct and child_shape == 'reference' and isinstance(child, str) and child:
                    if not child.startswith('/') or child.startswith('//'):
                        raise ValueError('reader asset must be a registered local absolute URL')
                    ref = relative(child[1:])
                    if ref not in assets:
                        raise ValueError(f'unregistered local asset: {ref}')
                    used.add(ref)
                else:
                    walk(child, child_shape)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            for ref in re.findall(r'(?:src=["\']|\]\()/([^"\'\s)<>]+)', node):
                ref = relative(ref)
                if ref not in assets:
                    raise ValueError(f'unregistered inline asset: {ref}')
                used.add(ref)
    walk(value)
    return used


def dependencies(used, media, pages):
    """A local record page can reference its preserved scan: copy that too."""
    import re
    from urllib.parse import urlsplit

    from .documents import BACK_SCRIPT
    pending = list(used)
    known = set(media) | set(pages)
    class References(HTMLParser):
        in_style = False

        def handle_starttag(self, tag, attrs):
            if tag == 'script' and name in pages and attrs == [('defer', None), ('src', '/' + BACK_SCRIPT)]:
                refs.append('/' + BACK_SCRIPT)
                return
            if tag in {'script', 'iframe', 'object', 'embed', 'base'}:
                raise ValueError('active document content is not a reader asset')
            self.in_style = tag == 'style'
            for key, value in attrs:
                if key.startswith('on'):
                    raise ValueError('event handler in reader asset')
                if (key.rsplit(':', 1)[-1] in {'href', 'src', 'poster'} and value
                        and not (tag == 'a' and key == 'href' and value == '/')):
                    refs.append(value)
                if key == 'srcset' and value:
                    refs.extend(part.strip().split()[0] for part in value.split(',') if part.strip())
                if key == 'style' and value:
                    self.css(value)

        def handle_endtag(self, tag):
            if tag == 'style':
                self.in_style = False

        def handle_data(self, text):
            if self.in_style:
                self.css(text)

        def css(self, text):
            if re.search(r'@import', text, re.IGNORECASE):
                raise ValueError('stylesheet imports are not self-contained')
            refs.extend(re.findall(r'url\(["\']?([^\)"\']+)', text, flags=re.IGNORECASE))
    while pending:
        name = pending.pop()
        if not name.endswith(('.html', '.svg')):
            continue
        data = pages[name] if name in pages else media[name][1].read_bytes()
        refs = []
        References().feed(data.decode('utf-8-sig'))
        for ref in refs:
            parsed = urlsplit(ref)
            if parsed.scheme or parsed.netloc or ref.startswith('//'):
                raise ValueError('external reference inside a document asset')
            if not parsed.path:
                continue
            path = relative(posixpath.normpath(posixpath.join(posixpath.dirname(name), parsed.path))
                            if not parsed.path.startswith('/') else parsed.path[1:])
            if path not in known:
                raise ValueError('unregistered document dependency: ' + path)
            if path not in used:
                used.add(path)
                pending.append(path)
    return used
