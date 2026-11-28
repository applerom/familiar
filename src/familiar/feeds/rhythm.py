"""Measure the reading order in the family's source language."""
import copy
import re
from collections import Counter, defaultdict
from itertools import groupby
from statistics import median

from .flow import drafts


SETTINGS = {
    'words': ('max_words', 'chapter length'),
    'paragraph': ('max_paragraph_words', 'paragraph length'),
    'run': ('max_text_run', 'consecutive paragraphs'),
    'beats': ('min_look_do', 'visual or interactive beats'),
    'kids': ('max_kids_words', "children's text length"),
    'quiet': ('max_no_do_run', 'consecutive chapters without an activity'),
}
COLUMNS = ('words', 'kids', 'paragraphs', 'look', 'do', 'frame', 'run')
WORDS = re.compile(r"[^\W_]+(?:[’'\-][^\W_]+)*")


def text(value, language):
    if isinstance(value, dict):
        value = value.get(language)
    return str(value) if value is not None else ''


def chapter_strip(chapter, language, feed):
    paragraphs = re.split(r'\n{2,}', text(chapter.get('text'), language))
    figures = chapter.get('figures', [])
    records = chapter.get('records', [])
    placed = defaultdict(list)
    for beat in chapter.get('flow', []):
        if type(beat.get('after')) is int and -1 <= beat['after'] < len(paragraphs):
            placed[beat['after']].append(beat)
    activities = [beat['do'] for beats in placed.values() for beat in beats if 'do' in beat]
    moved = {(item['kind'], item['key']) for item in activities
             if item.get('game') or item.get('picture')}
    shown_figures, shown_records = set(), set()

    def picture(image):
        if image:
            yield 'look'
            visible = image.get('ours') or image
            for kind in ('spots', 'pano'):
                if visible.get(kind) and (kind, visible.get('asset')) not in moved:
                    yield 'do'

    strip = list(picture(chapter.get('picture')))
    lengths = []
    for index in range(-1, len(paragraphs)):
        if index >= 0 and (paragraph := paragraphs[index]).strip():
            lengths.append(len(WORDS.findall(paragraph)))
            strip.append('text')
        for beat in placed[index]:
            if index >= 0 and type(beat.get('figure')) is int and 0 <= beat['figure'] < len(figures):
                shown_figures.add(beat['figure'])
                strip.extend(picture(figures[beat['figure']]))
            if index >= 0 and type(beat.get('record')) is int and 0 <= beat['record'] < len(records):
                shown_records.add(beat['record'])
                strip.append('look')
            if beat.get('placeholder', {}).get('ratio'):
                strip.append('frame')
            if (activity := beat.get('do')) and (activity.get('game') or activity.get('picture')):
                strip.append('do')
    if chapter.get('game') and ('game', f"{feed}/{chapter['id']}") not in moved:
        strip.append('do')
    for index, image in enumerate(figures):
        if index not in shown_figures:
            strip.extend(picture(image))
    strip.extend(['look'] * (len(records) - len(shown_records)))
    kids = (chapter.get('kids') or {}).get('text') or chapter.get('text_kids')
    counts = Counter(strip)
    has_cut = any(type(beat.get('record')) is int and 0 <= beat['record'] < len(records)
                  and records[beat['record']].get('asset') for beat in chapter.get('flow', []))
    return {'id': chapter['id'], 'title': text(chapter.get('title'), language) or chapter['id'],
            'words': sum(lengths), 'kids': len(WORDS.findall(text(kids, language))),
            'paragraphs': len(lengths), 'paragraph': max(lengths, default=0), 'paper_cut': has_cut,
            **{k: counts[k] for k in ('look', 'do', 'frame')}, 'strip': strip,
            'run': max((sum(1 for _ in group) for beat, group in groupby(strip) if beat == 'text'), default=0)}


def measure(instance, feed, registry):
    from familiar.checks.engine import _known_people
    from familiar.reader.experiences import play

    feed = copy.deepcopy(feed)
    play(instance, {'feeds': [feed]})
    language = instance.source_language
    people = _known_people(instance)
    names = set()
    for person in people.values():
        names.update(text(value, language) for value in (person.get('name'), person.get('treeName')))
        for name in person.get('names', []):
            if name and name.get('given') and name.get('surname'):
                names.update((f"{name['given']} {name['surname']}", f"{name['surname']} {name['given']}"))
    patterns = sorted({r'\s+'.join(map(re.escape, name.split())) for name in names if len(name.split()) > 1})
    person_name = re.compile(r'(?<!\w)(?:' + '|'.join(patterns) + r')(?!\w)', re.I) if patterns else None
    rows = []
    for chapter in feed['chapters']:
        row = chapter_strip(chapter, language, feed['id'])
        blocks = chapter.get('_prose', {}).get('text', [])
        opening = next((p for p in re.split(r'\n{2,}', text(chapter.get('text'), language)) if p.strip()), '')
        first = next((block for block in blocks if text(block.get('text'), language).strip()), {})
        row['opening_person'] = bool(people.keys() & set(first.get('people', []))
                                     or person_name and person_name.search(opening))
        rows.append(row)
    return rows, notes_for_rows(registry, 'feed:' + feed['id'], rows)


def notes_for_rows(registry, scope, rows):
    limits = {key: registry.resolve_setting('story.' + setting, scope).value
              for key, (setting, _) in SETTINGS.items()}
    warnings = []
    quiet = 0
    for row in rows:
        for key in ('words', 'paragraph', 'run', 'kids'):
            if row[key] > limits[key]:
                warnings.append((row['id'], key, f'{row[key]} > {limits[key]}'))
        beats = row['look'] + row['do'] + row['frame']
        if beats < limits['beats']:
            warnings.append((row['id'], 'beats', f"{beats} < {limits['beats']}"))
        quiet = 0 if row['do'] else quiet + 1
        if quiet > limits['quiet']:
            warnings.append((row['id'], 'quiet', f"{quiet} > {limits['quiet']}"))
    return warnings


def report(rows, warnings, *, feed_counts=False):
    def line(values):
        return '| ' + ' | '.join(map(str, values)) + ' |'

    lines = ['Notes for the writer. The story can take its own pace.']
    if feed_counts:
        lines.extend((f"Chapters naming a person from the family tree in the first paragraph: {sum(row['opening_person'] for row in rows)}/{len(rows)}",
                      f"Chapters with a paper cut (R:): {sum(row['paper_cut'] for row in rows)}/{len(rows)}"))
    lines.extend(f'{chapter}: {SETTINGS[key][1]} ({value})' for chapter, key, value in warnings)
    lines.append('')
    lines.extend([line(('Chapter', 'Full', 'Kids', 'Paragraphs', 'Look', 'Do', 'Frames', 'Text run')),
                  line(['---'] * (len(COLUMNS) + 1))])
    lines.extend(line([row['id'], *(row[key] for key in COLUMNS)]) for row in rows)
    lines.append(line(['Median', *(f'{median(row[key] for row in rows):g}' if rows else '–' for key in COLUMNS)]))
    return '\n'.join(lines)


def advice(feed, rows, warnings):
    notes = len(warnings)
    pending = len(drafts([feed]))
    return (f"Rhythm · {len(rows)} chapters · {notes} notes for the writer"
            + (f" (familiar feed rhythm {feed['id']})" if notes else '')
            + (f" · {pending} chapters with home-only draft frames" if pending else ''))
