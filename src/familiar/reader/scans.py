# START_MODULE_CONTRACT: MOD-READER-SCANS
# PURPOSE: Resolve preserved captures named by adopted records and make web derivatives from their checked bytes.
# PRD_REF: docs/PRD.md#TRUST
# INVARIANTS:
# - selection and delivery resolve the same declared record references under the family or originals root [review: engine lead]
# - browser images and PDF pages are re-encoded pixels; source metadata and paths never become media payloads [review: engine lead]
# - derivatives bind the exact source bytes and do not modify permanent media [review: engine lead]
# CHANGES_WITH:
# - MOD-DISPLAY-INPUTS
# - MOD-READER-DOCUMENTS
# :END_MODULE_CONTRACT
import hashlib
import io
import math
import re
from contextlib import closing
from pathlib import Path
from typing import NamedTuple


class CaptureReference(NamedTuple):
    locator: str
    page: int | None = None


_FRAME_KEYS = ('locator', 'image', 'images', 'scan', 'scans', 'capture', 'captures',
               'saved_result', 'original', 'frame', 'full_frame', 'saved_frame',
               'file', 'path', 'crop', 'crops', 'saved_crop', 'rereadings')
_FRAME = re.compile(
    r'(?P<path>[^<>"|?*\r\n]+?\.(?:jpe?g|png|webp|tiff?|gif|bmp|pdf))'
    r'(?:#page=(?P<page>[1-9][0-9]{0,5}))?(?=$|[\s,#)\]])', re.IGNORECASE)
WEB_SIDE = 1800


def candidates(record):
    def extract(node):
        if isinstance(node, dict):
            for key in _FRAME_KEYS:
                yield from extract(node.get(key))
        elif isinstance(node, list):
            for item in node:
                yield from extract(item)
        elif isinstance(node, str):
            for part in re.split(r'[;\n]', node):
                value = part.strip(" \t`'\"")
                if '://' in value or value.startswith(('//', '\\\\')):
                    continue
                if match := _FRAME.match(value):
                    yield CaptureReference(match['path'], int(match['page']) if match['page'] else None)

    refs = dict.fromkeys(scan for section in (record.get('source'), record, record.get('collector_note'))
                         for scan in extract(section))
    # A saved page image is more precise and cheaper to serve than its whole book.
    return tuple(sorted(refs, key=lambda scan: scan.locator.lower().endswith('.pdf')))


def missing_images(instance, graph):
    """Records the tree cites whose named images are neither in the family nor in the source archive.

    Without the image the document page shows its reading alone; a hint, never a blocker.
    """
    import json
    cited = {source.get('record', sid) for sid, source in graph.get('sources', {}).items()}
    originals, result = instance.path('originals'), []
    for file in sorted(instance.path('records').rglob('*.json')):
        try:
            record = json.loads(file.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        if not isinstance(record, dict) or record.get('id') not in cited or not (refs := candidates(record)):
            continue
        if not any((p := capture_path(instance, r)) and p.is_file() or (originals / r.locator).is_file() for r in refs):
            # An archive reference whose file sits in the family instead is a wrong prefix, not a lost image.
            moved = [r.locator[8:] for r in refs if r.locator.startswith('archive:')
                     and _present(instance, r.locator[8:])]
            result.append({'location': f"record:{record['id']}", 'images': [r.locator for r in refs][:3],
                           'message': (f'the image is in the family at {moved[0]}, not in originals; '
                                       'write that path without archive:') if moved else
                                      'names an image that is neither in the family nor in originals; '
                                      'the document page shows the reading without it'})
    return result


def _present(instance, value):
    try:
        return instance.local(value).is_file()
    except ValueError:
        return False


def capture_path(instance, reference, *, resolve=Path.resolve):
    locator = reference.locator
    originals = instance.path('originals')
    if locator.startswith('archive:'):
        path = resolve(originals / locator[8:])
        return path if path.is_relative_to(originals) else None
    requested = instance.root / locator
    source_root = getattr(instance, '_snapshot_source_root', instance.root)
    if Path(locator).is_absolute() and requested.is_relative_to(source_root):
        requested = instance.root / requested.relative_to(source_root)
    if not Path(locator).is_absolute():
        try:
            mapped = instance.local(locator)  # captures/originals kept outside git resolve through the map
        except ValueError:
            mapped = None
        if mapped is not None and not mapped.is_relative_to(instance.root):
            return mapped
    path = resolve(requested)
    return path if path.is_relative_to(instance.root) or path.is_relative_to(originals) else None


def selected_capture(instance, record):
    for reference in candidates(record):
        path = capture_path(instance, reference)
        if path and path.is_file():
            return reference, path
    return None, None


def _jpeg(image):
    from PIL import Image, ImageOps

    image = ImageOps.exif_transpose(image)
    image.thumbnail((WEB_SIDE, WEB_SIDE), Image.Resampling.LANCZOS)
    pixels = image.convert('RGBA')
    clean = Image.new('RGB', pixels.size, 'white')
    clean.paste(pixels, mask=pixels.getchannel('A'))
    out = io.BytesIO()
    clean.save(out, 'JPEG', quality=89, optimize=True)
    return out.getvalue()


def first_page(raw):
    """A scan sent as PDF shows as its first page; None without the PDF reader."""
    try:
        import pypdfium2 as pdf
        with pdf.PdfDocument(raw) as source, closing(source[0]) as page:
            width, height = page.get_size()
            if not all(math.isfinite(side) and side > 0 for side in (width, height)):
                return None
            with closing(page.render(scale=min(2, WEB_SIDE / max(width, height)),
                                     may_draw_forms=False, draw_annots=False)) as bitmap:
                return _jpeg(bitmap.to_pil())
    except (ImportError, OSError, ValueError, IndexError):
        return None
    except Exception as error:  # pypdfium2 raises its own error type for a damaged file
        if type(error).__name__ == 'PdfiumError':
            return None
        raise


def _pdf(raw, number):
    import pypdfium2 as pdf

    stream = io.BytesIO()
    with pdf.PdfDocument(raw) as source, pdf.PdfDocument.new() as clean:
        if number is not None and number > len(source):
            return None
        for index in range(len(source)) if number is None else (number - 1,):
            with closing(source[index]) as page:
                width, height = page.get_size()
                with closing(page.render(scale=min(2, WEB_SIDE / max(width, height)),
                                         may_draw_forms=False, draw_annots=False)) as bitmap:
                    jpeg = _jpeg(bitmap.to_pil())
                with closing(clean.new_page(width, height)) as leaf:
                    image = pdf.PdfImage.new(clean)
                    image.load_jpeg(io.BytesIO(jpeg), inline=True)
                    image.set_matrix(pdf.PdfMatrix().scale(width, height))
                    leaf.insert_obj(image)
                    leaf.gen_content()
        clean.save(stream)
    body, trailer, tail = stream.getvalue().rpartition(b'\r\ntrailer\r\n')
    # PDFium assigns a random trailer ID to new PDFs. Keep the hex width so the
    # serialized offsets stay valid and identical pages produce identical bytes.
    identifier = hashlib.sha256(body).hexdigest()[:32].encode('ascii')
    tail = re.sub(rb'/ID\[<[0-9A-F]{32}><[0-9A-F]{32}>\]',
                  b'/ID[<' + identifier + b'><' + identifier + b'>]', tail, count=1)
    return body + trailer + tail


def derivative(raw, *, pdf=False, page=None):
    """A missing decoder or unreadable image leaves the canonical reading available."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()  # A phone photograph (HEIC, AVIF) opens like any other picture.
    except ImportError:
        pass
    try:
        if pdf:
            from pypdfium2 import PdfiumError
            try:
                return _pdf(raw, page)
            except PdfiumError:
                return None
        with Image.open(io.BytesIO(raw)) as image:
            return _jpeg(image)
    except (ImportError, OSError, ValueError, Image.DecompressionBombError):
        return None
