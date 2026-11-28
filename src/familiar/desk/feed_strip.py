"""The local investigation's strip of chapter beats."""
from html import escape
from urllib.parse import quote

from familiar.feeds.rhythm import chapter_strip, text


PAGE = 'desk/feed-strip.html'
WORDS = {
    'en': ('Feed rhythm', 'Text', 'Look', 'Do', 'Draft frame'),
    'ru': ('Ритм лент', 'Текст', 'Смотри', 'Сделай', 'Серая рамка'),
    'pl': ('Rytm opowieści', 'Tekst', 'Spójrz', 'Zrób', 'Szara ramka'),
    'sv': ('Berättelsernas rytm', 'Text', 'Titta', 'Gör', 'Grå ruta'),
}
CSS = """
.strip-main{max-width:780px;margin:0 auto;padding:24px 18px 100px;color:var(--ink,#262821);
 font:16px/1.45 system-ui,sans-serif}
.strip-nav,.strip-legend,.strip-beats{display:flex;align-items:center;flex-wrap:wrap;gap:6px}
.strip-nav a{padding:8px 12px;border:1px solid #848479;border-radius:8px;color:inherit}
.strip-legend{font-size:.86rem;gap:8px 14px;margin:12px 0 20px}
.strip-legend span{display:inline-flex;align-items:center;gap:5px}
.strip-panel{display:none}
.strip-panel:target,.strip-main:not(:has(.strip-panel:target)) .strip-panel:first-of-type{display:block}
.strip-list{list-style:none;padding:0}
.strip-list li{display:grid;grid-template-columns:minmax(9rem,1fr) 2fr;gap:8px 20px;
 padding:10px 0;border-top:1px solid #aaa59766}
.strip-list a{color:inherit;text-decoration:none}
.strip-list a:hover{text-decoration:underline}
.strip-number{display:inline-block;width:2.25em;font-variant-numeric:tabular-nums;color:var(--ink-mute,#5d6258)}
.strip-square{display:inline-block;flex:0 0 12px;height:12px;border-radius:2px;box-sizing:border-box}
.strip-text{background:#34453f}.strip-look{background:#418568}.strip-do{background:#d78b28}
.strip-frame{background:#d5d5d2;border:1px dashed #72736e}
@media(max-width:540px){.strip-list li{grid-template-columns:1fr}.strip-beats{padding-left:2.25em}}
"""


def words(language):
    return WORDS.get(language, WORDS['en'])


def page(feeds, language):
    heading, *labels = words(language)
    kinds = dict(zip(('text', 'look', 'do', 'frame'), labels))

    def square(kind):
        return f'<i class="strip-square strip-{kind}" aria-hidden="true"></i>'

    legend = ''.join('<span>' + square(kind) + escape(label) + '</span>' for kind, label in kinds.items())
    links, panels = [], []
    for index, feed in enumerate(feeds, 1):
        target = f'feed-{index}'
        title = escape(text(feed['title'], language) or feed['id'])
        links.append(f'<a href="#{target}">{title}</a>')
        rows = []
        for number, chapter in enumerate(feed['chapters'], 1):
            row = chapter_strip(chapter, language, feed['id'])
            href = '/#feed=' + quote(feed['id'], safe='') + '&amp;step=' + str(number)
            beats = ''.join(square(kind) for kind in row['strip'])
            alt = escape(', '.join(kinds[kind] for kind in row['strip']), quote=True)
            rows.append(f'<li><a href="{href}"><span class="strip-number">{number:02}</span>'
                        f'{escape(row["title"])}</a><span class="strip-beats" role="img" aria-label="{alt}">'
                        f'{beats}</span></li>')
        panels.append(f'<section class="strip-panel" id="{target}"><h2>{title}</h2>'
                      '<ol class="strip-list">' + ''.join(rows) + '</ol></section>')
    nav = '<nav class="strip-nav">' + ''.join(links) + '</nav>' if len(links) > 1 else ''
    return (f'<!doctype html><html lang="{escape(language)}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(heading)}</title><style>{CSS}</style></head><body>'
            f'<main class="strip-main"><h1>{escape(heading)}</h1>{nav}'
            f'<div class="strip-legend">{legend}</div>' + ''.join(panels) + '</main></body></html>')
