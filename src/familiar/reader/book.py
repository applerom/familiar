# START_MODULE_CONTRACT: MOD-READER-BOOK
# PURPOSE: Select independently read chapters from the sealed reader projection for an offline print book.
# PRD_REF: docs/PRD.md#PRINT-BOOK
# INVARIANTS:
# - book admission consumes current reader attestations, never pipeline marks or host releases [review: engine lead]
# - the flat print delivery contains only its selected semantic HTML, one replaceable stylesheet and local images [review: engine lead]
# - document crops preserve authored paragraph placement and their literal original readings [review: engine lead]
# - English interaction cues require a UI object or direction, preserving narrative nouns such as tap and press [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE (private review material retains the exact local reader binding)
# - MOD-OUTPUT-REVIEW (canonical units and independent attestations)
# - MOD-FAMILY-WRITER (atomic flat delivery from a checked publication)
# - MOD-FEED-TRANSLATIONS (reader retains stale translations until replacement)
# - MOD-BOOK-STYLE (semantic print class names)
# - docs/reader-export.md
# :END_MODULE_CONTRACT
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

from familiar.instance.gate import boundary, publication

from .export import output_path


@boundary('consume')
def export_book(instance, out, *, language=None, kids=False, page_size='A5', host_private=False):
    # This adapter consumes the factory's checked seal. Re-running the full
    # family gate here would duplicate publication() without adding authority.
    from familiar.instance.writer import save_book
    language = language or instance.source_language
    if language not in instance.languages:
        raise ValueError('book language must be one of: ' + ', '.join(instance.languages))
    if page_size not in {'A5', 'A4'}:
        raise ValueError('book page size must be A5 or A4')
    out = output_path(instance, out)
    material = publication(instance, 'reader-private' if host_private else 'reader', for_review=True)
    return save_book(instance, out, material, language=language, kids=kids, page_size=page_size)


def compose(instance, material, *, language, kids, page_size):
    """Consume only the factory's sealed bytes; no family prose is reread here."""
    files, review = material.files(), material.manifest
    graph = json.loads(files['graph.json'])
    profile = json.loads(files['reader-profile.json'])
    accepted = {(r['page'], r['language']) for r in review['attestations']}
    # The reader requires all configured languages. Selecting a print language
    # does not weaken that requirement, or accept a host-release substitution.
    def admitted(unit):
        return all((unit, lang) in accepted for lang in instance.languages)

    from familiar.checks.engine import load
    saved = load(instance.path('state') / 'attestations.json', {})
    def reason(unit):
        rows = [saved.get(unit + '@' + lang, {}) for lang in instance.languages]
        if any(r.get('digest') and r['digest'] != review['review_units'].get(unit) for r in rows):
            return 'changed-after-reading'
        if any(r for r in rows):
            return 'no-current-independent-reading (safety, language or verdict changed)'
        return 'not-independently-read'

    renderer = BookHTML(files, language, kids)
    included, excluded, parts = [], [], []
    profile_unit = 'reader:file:reader-profile.json'
    for feed in graph.get('feeds', []):
        chapters = []
        for chapter in feed['chapters']:
            unit = 'feed:' + feed['id'] + '/' + chapter['id']
            dependencies = [unit, 'feed:' + feed['id'] + '/__feed__', profile_unit]
            failures = [{'unit': key, 'reason': reason(key)} for key in dependencies if not admitted(key)]
            if not renderer.text(chapter.get('title')).strip() or not renderer.text(chapter.get('text')).strip():
                failures.append({'unit': unit, 'reason': 'withheld-by-reader'})
            if failures:
                excluded.append({'chapter': unit, 'reasons': failures})
                continue
            included.append(unit)
            chapters.append(chapter)
        if chapters:
            parts.append(dict(feed, chapters=chapters))
    if not included:
        raise ValueError(json.dumps({'included': 0, 'excluded': len(excluded), 'omissions': excluded,
                                     'error': 'No independently read chapters; no book written'}, ensure_ascii=False, indent=2))
    html = renderer.document(profile['family'], parts, host_private=material.host_private, page_size=page_size)
    # Preserve SVG dependency paths, but never copy unused documents or games.
    from .assets import dependencies
    media = {name: content for name, content in files.items()
             if name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.svg'))}
    # Reader delivery already checked SVG dependencies. The local names are kept
    # so a relative reference inside an SVG resolves identically offline.
    from html.parser import HTMLParser
    class SVGReferences(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key.rsplit(':', 1)[-1] in {'href', 'src'} and value and value.startswith('/'):
                    raise ValueError('print SVG needs relative image references: ' + self.name)
                if key == 'style' and value:
                    self.handle_data(value)
        def handle_data(self, data):
            if re.search(r'url\([\s\"\x27]*/', data):
                raise ValueError('print SVG needs relative CSS references: ' + self.name)
    used = dependencies(set(renderer.images), {}, media)
    for name in used:
        if name.endswith('.svg'):
            parser = SVGReferences(); parser.name = name; parser.feed(files[name].decode('utf-8-sig'))
    output = {'index.html': html.encode('utf-8'),
              'book.css': Path(__file__).with_name('book.css').read_bytes(),
              **{name: files[name] for name in sorted(used)}}
    # Retain the reader's documented translation policy: old translations stay
    # until the next batch, missing ones fall back as in reader tr(). Report gaps.
    warnings = list(renderer.warnings)
    if language != instance.source_language:
        from familiar.feeds.service import _materialize, folders
        for folder in folders(instance):
            _, detail = _materialize(instance, folder)
            status = detail['translations'].get(language, {})
            if status.get('stale') or status.get('missing'):
                warnings.append({'feed': folder.name, 'translation': status,
                                 'policy': 'reader: retain stale until replacement; fallback en/ru for missing'})
    return output, {'state': 'host-private' if material.host_private else 'clean',
                    'language': language, 'layer': 'kids' if kids else 'full', 'page_size': page_size,
                    'included': len(included), 'excluded': len(excluded), 'chapters': included,
                    'omissions': excluded, 'warnings': warnings,
                    'entry': 'index.html'}


LABELS = {
    'en': ('Contents', 'Grounds and versions', 'Fictional family', 'Family only', 'Full text', "Children's text"),
    'ru': ('Оглавление', 'Основания и версии', 'Вымышленная семья', 'Только для семьи', 'Полный текст', 'Детский текст'),
    'pl': ('Spis treści', 'Podstawy i wersje', 'Fikcyjna rodzina', 'Tylko dla rodziny', 'Pełny tekst', 'Tekst dla dzieci'),
    'sv': ('Innehåll', 'Underlag och versioner', 'Påhittad familj', 'Endast familjen', 'Fullständig text', 'Barntext'),
}
INTERACTION = re.compile(
    r'\b(?:(?:click|tap|press)\s+(?:here\b|on\b|this\b|to\s+(?:open|view|see)\b|'
    r'the\s+(?:button|image|picture|link|icon|screen|tab)\b)|swipe\s+(?:left|right|up|down)\b|'
    r'нажм\w*|нажим\w*|клик\w*|щёлк\w*|щелк\w*|'
    r'коснит\w*|свайп\w*|kliknij|naciśnij|przesuń|klicka|tryck|svep)\b', re.IGNORECASE)


class BookHTML:
    def __init__(self, files, language, kids):
        self.files, self.language, self.kids = files, language, kids
        self.labels = LABELS.get(language.split('-')[0], LABELS['en'])
        self.images, self.warnings = set(), []
        self.removed_prompts = 0

    def text(self, value):
        # Same language lookup as reader-src/app/feed.tsx:tr. Literal document
        # readings are strings and remain in their original language.
        if isinstance(value, dict):
            return value.get(self.language) or value.get('en') or value.get('ru') or ''
        return str(value) if value is not None else ''

    def clean(self, value, *, literal=False):
        text = self.text(value)
        text = re.sub(r'(?:https?:)?//[^\s<>\"\x27)\]]+', '', text, flags=re.IGNORECASE)
        if not literal:
            paragraphs = re.split(r'\n\s*\n', text)
            kept_paragraphs = [p for p in paragraphs if not re.match(r'^\s*(?:game|игра|gra|spel)\s*:', p, re.IGNORECASE)]
            self.removed_prompts += len(paragraphs) - len(kept_paragraphs)
            text = '\n\n'.join(kept_paragraphs)
            pieces = re.split(r'(?<=[.!?])(?=\s)|(?<=\n)', text)
            kept = [p for p in pieces if not INTERACTION.search(p)]
            self.removed_prompts += len(pieces) - len(kept)
            text = ''.join(kept)
        return text.strip()

    def inline(self, value, *, literal=False):
        escaped = html.escape(self.clean(value, literal=literal))
        return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)

    def prose(self, value, *, literal=False):
        text = self.clean(value, literal=literal)
        result = []
        for paragraph in re.split(r'\n\s*\n', text):
            if not paragraph.strip():
                continue
            lines = paragraph.splitlines()
            if all(re.match(r'^[-•] ', line) for line in lines):
                result.append('<ul>' + ''.join('<li>' + self.inline(x[2:], literal=literal) + '</li>' for x in lines) + '</ul>')
            else:
                result.append('<p>' + self.inline(paragraph, literal=literal) + '</p>')
        return ''.join(result)

    def image(self, asset, caption=''):
        name = asset.lstrip('/')
        if name not in self.files or not name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.svg')):
            raise ValueError('book image needs a checked local image derivative: ' + name)
        self.images.add(name)
        return f'<img class="book-image" src="{html.escape(quote(name, safe="/"))}" alt="{html.escape(self.clean(caption))}">'

    def picture(self, value):
        if not value or not value.get('asset'):
            return ''
        caption = self.inline(value.get('caption', ''))
        credits = ' · '.join(self.clean(value.get(k, '')) for k in ('credit', 'license') if value.get(k))
        disclosure = ''
        if value.get('generated') or value.get('reconstruction'):
            label = {'ru': 'Реконструкция, не документ', 'pl': 'Rekonstrukcja, nie dokument',
                     'sv': 'Rekonstruktion, inte ett dokument'}.get(self.language.split('-')[0], 'Reconstruction, not a document')
            disclosure = '<span class="book-disclosure">' + label + '</span>'
        return ('<figure class="book-figure">' + self.image(value['asset'], value.get('caption', ''))
                + '<figcaption class="book-caption">' + caption
                + disclosure + ('<span class="book-credit">' + html.escape(credits) + '</span>' if credits else '') + '</figcaption></figure>')

    def record(self, value):
        title = self.inline(value.get('title', ''))
        pieces = []
        for part in [value, *value.get('parts', [])]:
            picture = self.image(part['asset'], value.get('title', '')) if part.get('asset') else ''
            reading = '<blockquote class="book-reading">' + self.prose(part.get('read', ''), literal=True) + '</blockquote>'
            pieces.append('<figure class="book-document">' + picture
                          + '<figcaption class="book-caption">' + title + '</figcaption>' + reading + '</figure>')
        return ''.join(pieces)

    def chapter_title(self, chapter):
        return (chapter.get('kids', {}).get('title') if self.kids else None) or chapter.get('title', '')

    def chapter(self, chapter, anchor):
        title = self.inline(self.chapter_title(chapter))
        out = [f'<article class="book-chapter" id="{anchor}"><header class="book-chapter-header">',
               '<p class="book-year">' + self.inline(chapter.get('year', '')) + '</p>', '<h2>' + title + '</h2></header>',
               self.picture(chapter.get('picture'))]
        text = (chapter.get('kids', {}).get('text') or chapter.get('text_kids') or chapter.get('text', '')) if self.kids else chapter.get('text', '')
        if self.kids and not chapter.get('kids', {}).get('text') and not chapter.get('text_kids'):
            self.warnings.append({'chapter': chapter['id'], 'reason': 'no-kids-layer; reader uses full text'})
        records = chapter.get('records', [])
        if self.kids:
            marked = [r for r in records if r.get('kids') is True]
            if chapter.get('kidsRecords') is False:
                records = []
            elif chapter.get('kidsSelection') or marked:
                records = []
                remaining = 4
                for record in marked:
                    if not remaining:
                        break
                    parts = record.get('parts', [])[:remaining - 1]
                    records.append(dict(record, parts=parts))
                    remaining -= 1 + len(parts)
            else:
                records = [dict(r, parts=r.get('parts', [])[:1]) for r in records[:1]]
        figures = chapter.get('figures', [])
        # Flow belongs to full text only, as in the reader. Unplaced items remain
        # after the prose; privacy projection may have removed flow completely.
        flow = [] if self.kids else chapter.get('flow', [])
        placed_records, placed_figures = set(), set()
        for index, paragraph in enumerate(re.split(r'\n\s*\n', self.text(text))):
            out.append(self.prose(paragraph))
            for placement in flow:
                if placement['after'] != index:
                    continue
                for key, values, placed, render in (('record', records, placed_records, self.record),
                                                    ('figure', figures, placed_figures, self.picture)):
                    item = placement.get(key)
                    if item is not None and 0 <= item < len(values) and item not in placed:
                        out.append(render(values[item])); placed.add(item)
        if chapter.get('ask'):
            out.append('<aside class="book-question">' + self.prose(chapter['ask']) + '</aside>')
        if not self.kids:
            out.extend('<p class="book-fact">' + self.inline(f['text']) + '</p>' for f in chapter.get('facts', []))
        out.extend(self.picture(f) for i, f in enumerate(figures) if i not in placed_figures)
        out.extend(self.record(r) for i, r in enumerate(records) if i not in placed_records)
        details = [self.prose(chapter.get('more', ''))]
        for fact in chapter.get('facts', []):
            grounds = [self.clean(fact.get(k, '')) for k in ('basis', 'decision') if fact.get(k)]
            weight = fact.get('weight', fact.get('confidence'))
            if weight is not None:
                label = {'ru': 'Вес', 'pl': 'Waga', 'sv': 'Vikt'}.get(self.language.split('-')[0], 'Weight')
                grounds.append(f'{label}: {weight}')
            if grounds:
                details.append('<p class="book-fact-basis"><strong>' + self.inline(fact['text']) + '</strong>: ' + html.escape(' · '.join(grounds)) + '</p>')
        for variant in chapter.get('variants', []):
            details += ['<section class="book-version"><h4>' + self.inline(variant.get('title', '')) + '</h4>',
                        self.prose(variant.get('text', '')), self.prose(variant.get('more', '')), '</section>']
        for place in chapter.get('places', []):
            details.append('<p class="book-place"><strong>' + self.inline(place.get('name', '')) + '</strong> ' + self.inline(place.get('note', '')) + '</p>')
        for record in chapter.get('records', []):
            details.append(self.prose(record.get('source', '')) + self.prose(record.get('where', '')))
        for extra in chapter.get('extras', []):
            if self.kids and not extra.get('kids'):
                continue
            details += ['<section class="book-extra"><h4>' + self.inline(extra.get('title', '')) + '</h4>',
                        self.picture(extra.get('picture')), self.prose(extra.get('kids') if self.kids else extra.get('text', ''))]
            if not self.kids:
                details += [self.prose(extra.get('more', '')), *(self.record(r) for r in extra.get('records', []))]
            details.append('</section>')
        if any(details):
            out += ['<aside class="book-evidence"><h3>' + self.labels[1] + '</h3>', *details, '</aside>']
        out.append('</article>')
        return ''.join(out)

    def document(self, family, feeds, *, host_private, page_size):
        title = self.inline(family['title'])
        cover = ['<header class="book-cover"><h1>' + title + '</h1>',
                 '<p class="book-edition">' + self.labels[5 if self.kids else 4] + '</p>']
        if family.get('fictional'):
            cover.append('<p class="book-fictional">' + self.labels[2] + '</p>')
        if host_private:
            cover.append('<p class="book-private">' + self.labels[3] + '</p>')
        cover += ['<ul class="book-feed-titles">', *('<li>' + self.inline(f['title']) + '</li>' for f in feeds), '</ul></header>']
        toc, body = [], []
        for fi, feed in enumerate(feeds, 1):
            toc.append('<li><a href="#part-' + str(fi) + '">' + self.inline(feed['title']) + '</a><ol>')
            body.append(f'<section class="book-part" id="part-{fi}"><header class="book-part-header"><h1>' + self.inline(feed['title']) + '</h1>' + self.prose(feed.get('lead', '')) + '</header>')
            for ci, chapter in enumerate(feed['chapters'], 1):
                anchor = f'chapter-{fi}-{ci}'
                toc.append(f'<li><a href="#{anchor}">' + self.inline(self.chapter_title(chapter)) + '</a></li>')
                body.append(self.chapter(chapter, anchor))
            toc.append('</ol></li>'); body.append('</section>')
        if self.removed_prompts:
            self.warnings.append({'removed_interaction_passages': self.removed_prompts})
        return ('<!doctype html><html lang="' + html.escape(self.language) + '"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\'; style-src \'self\'">'
                '<title>' + title + '</title><link rel="stylesheet" href="book.css"></head>'
                f'<body class="book book-{page_size.lower()} {"book-kids" if self.kids else "book-full"}">'
                + ''.join(cover) + '<nav class="book-toc"><h1>' + self.labels[0] + '</h1><ol>'
                + ''.join(toc) + '</ol></nav><main class="book-body">' + ''.join(body) + '</main></body></html>')
