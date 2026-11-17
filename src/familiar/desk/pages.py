# START_MODULE_CONTRACT: MOD-DESK-PAGES
# PURPOSE: Keep the optional authored journal and family stories available below the investigation show.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - journal and story wording is rendered literally with escaped markup, never rewritten [review: engine lead]
# CHANGES_WITH:
# - MOD-DESK-SHOW (supplemental journal link)
# :END_MODULE_CONTRACT
import html
import re
from datetime import date


def journal_date(value, instance):
    """Present a dated filename with the family's words, independently of OS locale."""
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return value
    pack = instance.language_pack_data.get(instance.source_language, {}).get('data', {})
    if not pack and instance.source_language == 'en':
        from familiar.instance.packs import bundled_root, read
        pack = read(bundled_root() / 'demo-english' / 'pack.toml')
    months = pack.get('host_format', {}).get('months', [])
    template = pack.get('host', {}).get('date')
    if len(months) != 12 or not template:
        raise ValueError('Language pack gap: host date/months')
    return template.format(day=parsed.day, month=months[parsed.month - 1], year=parsed.year)


def _inline(text):
    text = html.escape(text)
    # Deliberately small Markdown subset: no raw HTML or active/external URLs.
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', text)


def markdown(text, *, level=2):
    result, paragraph = [], []
    def flush():
        if paragraph:
            result.append('<p>' + _inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()
    for line in text.splitlines():
        heading = re.match(r'^(#{1,6})\s+(.+)', line)
        item = re.match(r'^(?:[-*]|\d+\.)\s+(.+)', line)
        if not line.strip():
            flush()
        elif heading:
            flush()
            h = min(6, level + len(heading[1]) - 1)
            result.append(f'<h{h}>' + _inline(heading[2]) + f'</h{h}>')
        elif line.strip() == '---':
            flush()
            result.append('<hr>')
        elif item:
            flush()
            result.append('<p class="desk-list-item">' + _inline(line) + '</p>')
        else:
            paragraph.append(line.strip())
    flush()
    return ''.join(result)


def _title(text, fallback):
    first, _, rest = text.partition('\n')
    if first.startswith('# '):
        return first[2:].strip(), rest
    return fallback, text


def page(title, content, language):
    return ('<!doctype html><html lang="' + html.escape(language) + '"><head>'
            '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,nofollow,noarchive"><title>' + html.escape(title)
            + '</title></head><body><main class="desk-page"><h1>' + html.escape(title)
            + '</h1>' + content + '</main></body></html>').encode()


def project(active, config, w):
    inputs, listings, pages = {}, {}, {}
    def read(path):
        raw = path.read_bytes() if path.is_file() else None
        inputs[path] = raw
        return raw
    def select(root, pattern):
        from .model import listing
        paths, listings[root, pattern] = listing(root, pattern)
        return paths
    progress = '<h2>' + html.escape(w['journal']) + '</h2>'
    journals = select(active._inside('desk/journal'), '*.md')
    for path in reversed(journals):
        progress += '<article><small>' + html.escape(journal_date(path.stem, active)) + '</small>'
        progress += markdown(read(path).decode('utf-8-sig')) + '</article>'
    stories = select(active._inside('desk/stories'), '*.md')
    if stories:
        progress += '<h2>' + html.escape(w['stories']) + '</h2><ul>'
    for path in stories:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', path.stem):
            raise ValueError('Desk story filenames must be portable URL slugs')
        title, body = _title(read(path).decode('utf-8-sig'), w['story'])
        name = 'desk/stories/' + path.stem + '.html'
        pages[name] = page(title, markdown(body), active.source_language)
        progress += '<li><a href="/' + name + '">' + html.escape(title) + '</a></li>'
    if stories:
        progress += '</ul>'
    if journals or stories:
        pages['desk/journal.html'] = page(w['journal'], progress, active.source_language)
    return pages, inputs, listings
