"""Render a studio strip as a private, self-contained reading layout."""

import os
import re
from html import escape
from urllib.parse import quote

from familiar.rules.cascade import Registry
from familiar.rules.roles import method_root

from .rhythm import WORDS, notes_for_rows, report
from .studio import Importer, LABELS, relative


def image_url(path, out):
    if not path:
        return None
    if path.drive != out.drive:
        return path.as_uri()
    return quote(os.path.relpath(path, out.parent).replace(os.sep, '/'), safe='/')


def marked_reading(text):
    parts = re.split(r'\*\*(.+?)\*\*', text)
    return ''.join(f'<mark>{escape(part)}</mark>' if index % 2 else escape(part)
                   for index, part in enumerate(parts))


class Page:
    def __init__(self, instance, loaded, out):
        folder, sources, self.config, self.chapters, self.meta = loaded
        self.importer = Importer(instance, sources, folder, self.config)
        self.instance, self.out = instance, out
        self.language = instance.source_language
        self.labels = LABELS.get(self.language, LABELS['en'])
        self.words = {
            'ru': ('Главы', 'Лента полосами', 'Детям', 'Подробнее', 'Ответ', 'Бумага семьи'),
            'en': ('Chapters', 'Reading strips', 'For children', 'More', 'Answer', 'Family paper'),
        }.get(self.language, ('Chapters', 'Reading strips', 'For children', 'More', 'Answer', 'Family paper'))

    def local_file(self, value):
        path = self.instance._inside(relative(value))
        return path if path.is_file() else None

    def visual(self, item):
        if 'file' in item:
            source = item['file']
            rel = self.importer.export(source)
            if rel.startswith('family-photos/'):
                try:
                    path = self.instance.media_file('/' + rel)
                except ValueError as exc:
                    if 'originals' not in self.instance.host_paths and 'original checksum mismatch' in str(exc):
                        raise ValueError(f'{exc}. If originals are outside the instance, pass --host-paths '
                                         'with the host path map.') from exc
                    raise
            else:
                path = self.local_file(source) or self.importer.media_file(rel)
            caption = escape(item['caption'])
            if url := image_url(path, self.out):
                return f'<figure><img src="{escape(url)}" alt="" loading="lazy"><figcaption>{caption}</figcaption></figure>'
            item = {'ratio': [3, 2], 'says': item['caption']}
        width, height = item['ratio']
        return f'<figure class="frame" style="aspect-ratio:{width}/{height}">{escape(item["says"])}</figure>'

    def paper(self, item):
        if 'file' in item:
            path = self.local_file(item['file']) or self.importer.media_file(self.importer.export(item['file']))
            caption = item['caption']
        else:
            rid = item['record']
            asset = self.config.get('cuts', {}).get(rid)
            if not asset:
                previous = self.importer.old_documents.get(rid, {})
                asset = (previous.get('snippets') or [{}])[0].get('asset')
            path = self.importer.media_file(relative(asset.lstrip('/'))) if asset else None
            caption = item.get('caption', '')
        url = image_url(path, self.out)
        image = f'<img src="{escape(url)}" alt="" loading="lazy">' if url else ''
        title = f'<figcaption>{escape(caption)}</figcaption>' if caption else ''
        cut = f'<p>{marked_reading(item["cut"])}</p>' if 'cut' in item else ''
        return (f'<figure class="record">{title}{image}{cut}'
                f'<p>{marked_reading(item["reading"])}</p></figure>')

    def game(self, item):
        options = item['options']
        if 'answers' in item:
            response = ''.join(f'<details><summary>{escape(option)}</summary><p>{escape(answer)}</p></details>'
                               for option, answer in zip(options.split(' / '), item['answers'].split(' / ')))
        else:
            listed = f'<p class="options">{escape(options)}</p>' if options not in ('-', '—') else ''
            response = (f'{listed}<details><summary>{self.words[4]}</summary>'
                        f'<p>{escape(item["answer"])}</p></details>')
        return (f'<div class="game"><b>{self.labels[item["kind"]]}</b><p>{escape(item["ask"])}</p>'
                f'<div class="responses">{response}</div>'
                f'<p class="closing">{escape(item["after"])}</p></div>')

    def chapter(self, ch):
        show = {'T': lambda text: f'<p class="text">{escape(text)}</p>',
                'L': self.visual, 'R': self.paper, 'D': self.game}
        body = ''.join(show[tag](item) for tag, item, _ in ch['flow'])
        more = ''.join(f'<li>{escape(line)}</li>' for line in ch['more'])
        return (f'<article id="{ch["id"]}"><p class="year">{escape(ch["year"])}</p>'
                f'<h2>{escape(ch["title"])}</h2>{self.visual(ch["picture"][0])}{body}'
                f'<details><summary>{self.words[2]}</summary><p>{escape(ch["kids"])}</p></details>'
                f'<p class="ask">{escape(ch["ask"])}</p>'
                f'<details><summary>{self.words[3]}</summary><ul>{more}</ul></details></article>')


def strips(chapters):
    from itertools import groupby

    rows = []
    for ch in chapters:
        sequence = ['L' if 'file' in ch['picture'][0] else 'frame']
        lengths = [len(WORDS.findall(item)) for tag, item, _ in ch['flow'] if tag == 'T']
        sequence.extend('frame' if tag == 'L' and 'file' not in item else tag for tag, item, _ in ch['flow'])
        rows.append({'id': ch['id'], 'title': ch['title'], 'strip': sequence,
                     'words': sum(lengths), 'paragraphs': len(lengths), 'paragraph': max(lengths, default=0),
                     'kids': len(WORDS.findall(ch['kids'])), 'look': sequence.count('L') + sequence.count('R'),
                     'frame': sequence.count('frame'), 'do': sequence.count('D'),
                     'run': max((sum(1 for _ in group) for tag, group in groupby(sequence) if tag == 'T'), default=0)})
    return rows


def render(instance, loaded, out):
    page = Page(instance, loaded, out)
    registry = Registry(method_root() / 'rules', instance)
    rows = strips(page.chapters)
    notes = report(rows, notes_for_rows(registry, 'feed:' + page.meta['id'], rows))

    def localized(key):
        value = page.meta.get(key, '')
        return escape(value.get(page.language, '') if isinstance(value, dict) else value)

    title = localized('title')
    lead = localized('lead')
    introduction = ''.join(f'<p>{part}</p>' for part in lead.split('\n\n') if part)
    links = ''.join(f'<li><a href="#{ch["id"]}">{escape(ch["title"])}</a></li>' for ch in page.chapters)
    strip_rows = []
    symbols = {'T': '¶', 'L': '▧', 'frame': '□', 'R': '▤', 'D': '?'}
    for row in rows:
        cells = ''.join(f'<span class="{tag}">{symbols[tag]}</span>' for tag in row['strip'])
        strip_rows.append(f'<li><a href="#{row["id"]}">{escape(row["title"])}</a><div>{cells}</div></li>')
    html = (
        f'<!doctype html>\n<html lang="{escape(page.language)}"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        'img-src file:; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
        f'<title>{title}</title><style>{CSS}</style><main><h1>{title}</h1>{introduction}'
        f'<nav aria-label="{page.words[0]}"><ol>{links}</ol></nav>'
        + ''.join(page.chapter(ch) for ch in page.chapters)
        + f'<h2>{page.words[1]}</h2><ol class="strips">{"".join(strip_rows)}</ol>'
        f'<pre>{escape(notes)}</pre></main></html>\n')
    return html, notes


CSS = """
*{box-sizing:border-box}
body{margin:0;background:#f6f1e7;color:#222b27;font:18px/1.6 Georgia,serif}
main{max-width:560px;margin:auto;padding:1rem 18px 3rem}
h1,h2{line-height:1.15;font-weight:600}h1{font-size:32px}h2{font-size:27px;margin-top:0}
a{color:#295944}p{margin:0 0 1em}article{border-top:5px solid #ddd3c1;margin:2rem 0;padding:1rem 0}
.year,figcaption,summary,.ask,.strips,nav{font:600 15px/1.5 system-ui,sans-serif}
.year{color:#794619;margin-bottom:.4rem}figure{margin:0 0 1em}img{display:block;width:100%;max-height:520px;object-fit:contain}
figcaption{padding:.35rem 0;color:#4a544f}
.frame{display:grid;place-items:center;text-align:center;padding:1.2rem;max-height:480px;
background:repeating-linear-gradient(135deg,#e0dcd3 0 12px,#d8d3ca 12px 24px);border-radius:6px}
.record,.game{border:1px solid #e3d3b7;border-radius:12px;background:#fbf4dc;padding:.7rem .85rem;margin:0 0 1em}
.record p,.game p{margin:.4rem 0}.record mark{background:#f3dc8a;color:inherit}
.game{background:#fff7eb;border-color:#e5c9a6;font:16px/1.5 system-ui,sans-serif}
.game b{color:#794619}.game details{background:#fffdf8;border:1px solid #ebd7ba;border-radius:8px;margin:.5rem 0;padding:.4rem .55rem}
.game .closing{display:none;color:#3c503f}.game:has(details[open]) .closing{display:block}
summary{cursor:pointer;padding:.25rem 0}summary:focus-visible{outline:2px solid #295944}
.ask{margin:1em 0}.strips li{margin:0 0 .7rem}.strips span{display:inline-grid;place-items:center;
width:1.5em;height:1.5em;background:#e6deca;border:1px solid #c7baa0;border-radius:3px;margin:2px}
.strips .frame{border:1px dashed #776f5b;background:none;padding:0}.strips .D{background:#ffddae}.strips .R{background:#ead79e}.strips .L{background:#cddcde}
pre{white-space:pre-wrap;font-size:.8rem;color:#48554c}
"""
