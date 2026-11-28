"""Compile plain chapter strips into authored feed catalogs."""
from __future__ import annotations

import csv
import json
import re
from hashlib import sha256
from pathlib import Path, PurePosixPath
from subprocess import CalledProcessError, check_output
from urllib.parse import quote

from .service import folders

ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
FRAMES = {'drawing': 'drawing', 'map': 'map', 'real-image': 'period-picture',
          'family-photo': 'family-photograph'}
LABELS = {
    'en': {'guess': 'Guess', 'choice': 'Choose', 'count': 'Count', 'find': 'Find it',
           'trace': 'Trace the route', 'reveal': 'Show the answer'},
    'ru': {'guess': 'Угадай', 'choice': 'Сыграй и выбери', 'count': 'Посчитай',
           'find': 'Найди на картинке', 'trace': 'Проведи путь', 'reveal': 'Показать ответ'},
}


def relative(value):
    if not isinstance(value, str) or any(c in value for c in '\\:') or any(
            bit in ('', '.', '..') for bit in value.split('/')):
        raise ValueError(f'Expected a family-relative path: {value!r}')
    return value


class Sources:
    """Read the writer's files, optionally as published in one family commit."""

    def __init__(self, instance, ref):
        self.root = instance.root
        self.reads = {}
        self.listings = {}
        self.commit = self.git('rev-parse', '--verify', '--end-of-options', ref + '^{commit}').strip() if ref else None

    def git(self, *args):
        try:
            return check_output(('git', '-C', str(self.root), '-c', 'core.quotePath=false', *args)).decode('utf-8')
        except CalledProcessError as error:
            raise ValueError('Could not read the studio from Git: ' + ' '.join(args)) from error

    def files(self, folder, pattern):
        folder = folder.resolve()
        if not folder.is_relative_to(self.root):
            raise ValueError(f'Studio input leaves the family: {folder}')
        if not self.commit:
            listing = sorted(folder.glob(pattern))
            self.listings[folder, pattern] = listing
            return listing
        names = self.git('ls-tree', '-r', '--name-only', '-z', self.commit, '--',
                         folder.relative_to(self.root).as_posix())
        return sorted(self.root / n for n in names.split('\0')
                      if n and (self.root / n).parent == folder and Path(n).match(pattern))

    def text(self, path):
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError(f'Studio input leaves the family: {path}')
        if not self.commit:
            raw = self.data(path)
            if raw is None:
                raise ValueError(f'Missing studio input: {path}')
            return raw.decode('utf-8-sig')
        return self.git('show', f'{self.commit}:{resolved.relative_to(self.root).as_posix()}').removeprefix('\ufeff')

    def data(self, path):
        raw = path.read_bytes() if path.is_file() else None
        digest = sha256(raw).digest() if raw is not None else None
        if self.reads.setdefault(path, digest) != digest:
            raise ValueError(f'Studio input changed during import: {path}')
        return raw

    def json(self, path, default=None):
        raw = self.data(path)
        return default if raw is None else json.loads(raw)

    def verify(self):
        for path in self.reads:
            self.data(path)
        for (folder, pattern), listing in self.listings.items():
            if sorted(folder.glob(pattern)) != listing:
                raise ValueError(f'Studio input list changed during import: {folder / pattern}')


def fields(text, forms, where):
    values = {}
    for field in text.split(' | '):
        key, equals, value = field.strip().partition('=')
        if key in values or (not equals and key != 'placeholder') or (equals and not value.strip()):
            raise ValueError(f'{where}: invalid field {field!r}')
        values[key] = value.strip() if equals else True
    if not any(values.keys() == set(form) for form in forms):
        expected = ' or '.join(', '.join(form) for form in forms)
        raise ValueError(f'{where}: expected {expected}, got {", ".join(values)}')
    if 'file' in values:
        values['file'] = relative(values['file'])
    return values


def picture(value, where):
    item = fields(value, [('placeholder', 'kind', 'ratio', 'says'), ('file', 'caption')], where)
    if 'file' in item:
        return item
    if (item['placeholder'] is not True or item['kind'] not in FRAMES
            or not re.fullmatch(r'[1-9]\d*:[1-9]\d*', item['ratio'])):
        raise ValueError(f'{where}: unknown frame kind or invalid ratio')
    return {'kind': FRAMES[item['kind']], 'ratio': list(map(int, item['ratio'].split(':'))),
            'says': item['says']}


def activity(value, where):
    common = ('kind', 'ask', 'options', 'after')
    item = fields(value, [common + ('answer',), common + ('answers',)], where)
    if item['kind'] not in LABELS['en'] or item['kind'] == 'reveal':
        raise ValueError(f'{where}: unknown activity {item["kind"]!r}')
    if 'answers' in item:
        options = item['options'].split(' / ')
        answers = item['answers'].split(' / ')
        if (item['kind'] != 'choice' or len(options) < 2 or len(answers) != len(options)
                or any(not part.strip() for part in options + answers)):
            raise ValueError(f'{where}: answers requires one answer per choice option')
    return item


def parse(path, source):
    lines = source.splitlines()
    name = re.fullmatch(r'(\d{2})-([a-z0-9-]+)\.md', path.name)
    header = re.fullmatch(r'# (\d{2}) · (.+?) · (.+)', lines[0] if lines else '')
    if not name or not header or name[1] != header[1] or not ID.fullmatch(name[2]):
        raise ValueError(f'{path.name}:1: expected matching NN-slug.md and # NN · Title · years')
    chapter = {'n': int(header[1]), 'id': name[2], 'title': header[2], 'year': header[3],
               'flow': [], 'more': []}
    section, explicit_id = 0, False
    footer = ['KIDS', 'ASK', 'MORE']
    for index, line in enumerate(lines[1:], 2):
        where = f'{path.name}:{index}'
        if not line.strip():
            continue
        if line == '---' and section < 2:
            section += 1
            continue
        tag, sep, rest = line.partition(':')
        rest = rest.strip()
        if section == 0 and tag == 'id' and not explicit_id and ID.fullmatch(rest):
            chapter['id'], explicit_id = rest, True
        elif section == 0 and tag == 'picture' and sep and 'picture' not in chapter:
            chapter['picture'] = (picture(rest, where), where)
        elif section == 1 and sep and rest and tag in {'T', 'L', 'R', 'D'}:
            if tag == 'L':
                rest = picture(rest, where)
            elif tag == 'R':
                rest = fields(rest, [('record', 'cut', 'reading', 'caption'), ('record', 'cut', 'reading'),
                                     ('file', 'caption', 'reading'), ('file', 'record', 'caption', 'reading')], where)
                if 'record' in rest and not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9._-]*', rest['record']):
                    raise ValueError(f'{where}: invalid record id')
            elif tag == 'D':
                rest = activity(rest, where)
            chapter['flow'].append((tag, rest, where))
        elif section == 2 and footer and tag == footer[0] and sep and bool(rest) == (tag != 'MORE'):
            footer.pop(0)
            if rest:
                chapter[tag.lower()] = rest
        elif section == 2 and not footer and line.startswith('- ') and line[2:].strip():
            chapter['more'].append(line[2:].strip())
        else:
            raise ValueError(f'{where}: unexpected chapter line: {line!r}')
    if 'picture' not in chapter or not any(tag == 'T' for tag, _, _ in chapter['flow']) or footer or not chapter['more']:
        raise ValueError(f'{path.name}: picture, T, KIDS, ASK and an entry under MORE are required')
    if explicit_id:
        chapter['explicit_id'] = True
    return chapter


def load(instance, feed, studio=None, config=None, source_ref=None, *, draft=False):
    if not ID.fullmatch(feed):
        raise ValueError('Invalid feed id: ' + feed)
    if draft:
        folder = (instance.path('feeds') / feed).resolve()
        if not folder.is_relative_to(instance.path('feeds')):
            raise ValueError('Feed folder leaves the family catalog')
    else:
        folder, = folders(instance, feed)
    sources = Sources(instance, source_ref)
    from familiar.instance.model import load_config
    sources.data(instance.root / 'familiar.toml')
    if load_config(instance.root) != instance.config:
        raise ValueError('Family configuration changed before studio import')
    studio = instance._inside(studio) if studio else folder / 'studio'
    default = studio / 'import.json'
    if config is not None:
        config = sources.json(config.resolve())
        if config is None:
            raise ValueError('Studio import configuration is missing')
    elif sources.commit:
        config = json.loads(sources.text(default)) if default in sources.files(studio, 'import.json') else {}
    else:
        config = sources.json(default, {})
    chapters = [parse(path, sources.text(path)) for path in sources.files(studio / 'chapters', '[0-9]*.md')]
    chapters.sort(key=lambda chapter: chapter['n'])
    if not chapters:
        raise ValueError(f'{studio / "chapters"}: no numbered chapter files')
    for ch in chapters:
        if not ch.pop('explicit_id', False):
            ch['id'] = config.get('chapter_ids', {}).get(ch['id'], ch['id'])
    if any(not ID.fullmatch(ch['id']) for ch in chapters):
        raise ValueError('Invalid chapter id in studio settings')
    if len({ch['id'] for ch in chapters}) != len(chapters) or len({ch['n'] for ch in chapters}) != len(chapters):
        raise ValueError('Duplicate chapter id or number')
    meta = sources.json(folder / 'feed.json')
    if meta is None and draft:
        readme = folder / 'README.md'
        heading = next((line[2:].strip() for line in sources.text(readme).splitlines()
                        if line.startswith('# ')), feed) if readme.is_file() and not sources.commit else feed
        meta = {'id': feed, 'title': config.get('title', heading)}
    if meta['id'] != feed:
        raise ValueError(f'{folder / "feed.json"}: expected feed id {feed}')
    return folder, sources, config, chapters, meta


def credits(sources, owners, supplements):
    rows = {}
    aliases = {credit: source for source, credit in supplements.items() if isinstance(credit, str)}
    for owner in owners:
        for path in sources.files(sources.root / 'captures' / relative(owner), 'images.tsv'):
            for row in csv.DictReader(sources.text(path).splitlines(), delimiter='\t'):
                source = next(iter(row.values()))
                if source == '—':
                    source = aliases.get(row['Что на изображении'])
                if source:
                    rows[source] = row
    for source, credit in supplements.items():
        if isinstance(credit, dict):
            rows[source] = credit
        elif source not in rows:
            raise ValueError(f'No credit in the image lists for {source}: {credit}')
    return rows


def frame(kind, ratio, says):
    return {'placeholder': {'kind': kind, 'ratio': ratio, 'says': says}}


def retain_text(previous, original, language):
    if isinstance(previous, dict) and previous.get(language) == original:
        return previous
    return original


def part_starts(config, meta, raw, old, language):
    starts = config.get('parts')
    if starts is not None:
        starts = {int(n): title for n, title in starts.items()}
        numbers = {ch['n'] for ch in raw}
        if set(starts) - numbers or starts and min(starts) != raw[0]['n']:
            raise ValueError('Parts must start at existing chapters, including the first chapter')
        labels = meta.get('parts', [])
        meta['parts'] = [
            (retain_text(labels[i], title, language) if i < len(labels) else title)
            if isinstance(title, str) else title
            for i, title in enumerate(title for _, title in sorted(starts.items()))
        ]
        meta['parts'] = [{language: x} if isinstance(x, str) else x for x in meta['parts']]
        return starts
    starts = {}
    last = None
    for ch in raw:
        part = old.get(ch['id'], {}).get('part')
        if part is not None and part != last:
            starts[ch['n']] = part
            last = part
    return starts


class Importer:
    def __init__(self, instance, sources, feed, config):
        self.instance, self.sources, self.config = instance, sources, config
        self.line = feed.name
        self.lang = instance.source_language
        self.labels = LABELS.get(self.lang, LABELS['en'])
        self.media = instance.path('media')
        self.manifest_path = self.media / 'manifest.json'
        self.manifest = sources.json(self.manifest_path, {'assets': []})
        self.assets = {row['export']: row for row in self.manifest['assets']}
        self.gallery = sources.json(instance.path('gallery'), {}).get('family_photographs', {})
        self.credits = credits(sources, config.get('credits', []), config.get('supplemental_credits', {}))
        self.old_pictures = sources.json(feed / 'pictures.json', {})
        self.old_documents = sources.json(feed / 'documents.json', {})
        old_play = sources.json(feed / 'play.json', {})
        self.play = {'spots': {}, 'games': {}, 'panos': old_play.get('panos', {})}
        self.pictures, self.documents, self.notes = {}, {}, []
        self.new_media = {}

    def people(self, raw, passage):
        matches = []
        for pid, rule in self.config.get('mentions', {}).items():
            # Existing studios use one [chapters, pattern] pair; a subject may also have several.
            rules = [rule] if len(rule) == 2 and isinstance(rule[1], str) else rule
            for chapters, pattern, *condition in rules:
                if (raw['id'] in chapters or raw['n'] in chapters) and re.search(
                        rf'(?<!\w)(?:{pattern})(?!\w)', passage, re.I):
                    if not condition or re.search(condition[0], passage, re.I):
                        matches.append(pid)
                        break
        return sorted(set(matches))

    def export(self, source):
        if source in self.config.get('exports', {}):
            return relative(self.config['exports'][source])
        if source.startswith('family-photos/'):
            return source
        if source.startswith('media/'):
            return source.removeprefix('media/')
        if source.startswith(('captures/', 'feeds/')):
            return f'records/{self.line}/strip/{PurePosixPath(source).name}'
        return source

    def media_file(self, rel):
        row = self.assets.get(rel)
        if row is None:
            return None
        path = (self.media / relative(row['file'])).resolve()
        return path if path.is_relative_to(self.media.resolve()) and path.is_file() else None

    def figure(self, item, where, raw, previous_key=None):
        rel = self.export(item['file'])
        asset = '/' + rel
        credit = self.credits.get(item['file'])
        photo = self.gallery.get(rel)
        if rel.startswith('family-photos/'):
            if not photo or photo.get('show') == 'private':
                self.notes.append(f'{where}: photograph unavailable in the gallery')
                return frame('family-photograph', [3, 2], item['caption'])
        elif rel not in self.assets and credit:
            local = (self.media / rel).resolve()
            if local.is_relative_to(self.media.resolve()) and local.is_file():
                row = {'id': f'{self.line}-strip-' + local.stem, 'kind': 'period-picture',
                       'file': rel, 'export': rel, 'sha256': sha256(self.sources.data(local)).hexdigest(),
                       'origin': {'description': credit['Что на изображении'],
                                  'holder': credit['Хранитель'], 'source': credit['Страница']}}
                self.manifest['assets'].append(row)
                self.assets[rel] = row
        if not photo and not self.media_file(rel):
            self.notes.append(f'{where}: picture is missing or unregistered: {item["file"]}')
            return frame('period-picture', [3, 2], item['caption'])

        aliases = self.config.get('picture_ids', {})
        existing = f'{raw["n"]:02d}-{PurePosixPath(rel).stem}'
        if self.old_pictures.get(previous_key, {}).get('asset') != asset:
            previous_key = existing if self.old_pictures.get(existing, {}).get('asset') == asset else None
        key = (previous_key or aliases.get(asset) or f'{raw["id"]}-{PurePosixPath(rel).stem}')
        original = self.pictures.get(key) or self.old_pictures.get(key, {})
        if original and original.get('asset') != asset:
            raise ValueError(f'{where}: picture key {key} is already used for another asset')
        result = {**original, 'asset': asset, 'caption': retain_text(
            original.get('caption'), item['caption'], self.lang)}
        if isinstance(result['caption'], str):
            result['caption'] = {self.lang: result['caption']}
        if photo:
            result.update(kind='family-photograph', photo=True, subjects=photo['subjects'],
                          credit=photo['received_from'])
            if 'crop' in photo:
                result['crop'] = photo['crop']
        elif credit:
            result.update(kind='period-picture', credit=credit['Автор'], holder=credit['Хранитель'],
                          license=credit['Лицензия или основание'])
        elif self.assets[rel].get('kind') == 'diagram':
            result.pop('kind', None)
        else:
            result.setdefault('kind', 'period-picture')
        if not photo and not result.get('credit'):
            self.notes.append(f'{where}: picture has no credit in the catalog or image lists')
        if key in self.pictures and self.pictures[key] != result:
            key = f'{key}-{sha256(item["caption"].encode()).hexdigest()[:8]}'
        self.pictures[key] = result
        return {'picture': key}

    def cut_asset(self, source, where):
        from familiar.reader.assets import publication_bytes

        rel = self.export(source)
        if local := self.media_file(rel):
            self.sources.data(local)
            return rel
        if self.media / rel in self.new_media:
            return rel
        if rel in self.assets:
            raise ValueError(f'{where}: registered cut file is missing: {source}')
        path = self.instance._inside(source)
        suffix = path.suffix.lower()
        if not path.is_file() or suffix not in {'.png', '.jpg', '.jpeg', '.webp'}:
            raise ValueError(f'{where}: cut must name a PNG, JPEG or WebP file: {source}')
        data = self.sources.data(self.instance.root / source)
        digest = sha256(data).hexdigest()
        # A registered derivative may have stripped metadata from the studio original.
        matches = [key for key, row in self.assets.items() if row.get('kind') in {'crop', 'document-scan'}
                   and digest in (row.get('sha256'), row.get('source_sha256'))]
        if len(matches) > 1:
            named = [key for key in matches if PurePosixPath(key).name == path.name]
            if len(named) != 1:
                raise ValueError(f'{where}: set exports in studio/import.json for this cut: {source}')
            matches = named
        if matches:
            rel, = matches
            if local := self.media_file(rel):
                self.sources.data(local)
                return rel
            raise ValueError(f'{where}: registered cut file is missing: {source}')

        publication_bytes(data, path.name.lower())
        rel = f'documents/{self.line}/cuts/{digest}{suffix}'
        target = self.media / rel
        if target in self.new_media:
            return rel
        existing = self.sources.data(target)
        if existing is not None and existing != data:
            raise ValueError(f'{where}: existing cut file has different bytes: {target}')
        if rel in self.assets:
            if existing is None:
                raise ValueError(f'{where}: registered cut file is missing: {source}')
            return rel
        if existing is None:
            self.new_media[target] = data
        row = {'id': f'{self.line}-cut-{digest}{suffix}', 'kind': 'crop', 'file': rel,
               'export': rel, 'sha256': digest, 'origin': 'chapter strip'}
        self.manifest.setdefault('schema_version', 1)
        self.manifest['assets'].append(row)
        self.assets[rel] = row
        return rel

    def record(self, item, where, raw):
        from familiar.checks.engine import record_path
        rid = item.get('record')
        caption = item.get('caption', '')
        asset = None
        if 'file' in item:
            rel = self.cut_asset(item['file'], where)
            asset = '/' + rel
            row = self.assets[rel]
            origin = row.get('origin')
            registered_record = origin.get('record') if isinstance(origin, dict) else None
            if registered_record and rid and registered_record != rid:
                raise ValueError(f'{where}: cut is registered to {registered_record}, not {rid}')
            rid = rid or registered_record
        elif rid:
            previous = self.old_documents.get(rid, {})
            registered = self.config.get('cuts', {}).get(rid)
            asset = '/' + relative(registered) if registered else (previous.get('snippets') or [{}])[0].get('asset')
        if not caption:
            self.notes.append(f'{where}: MISSING CAPTION for {rid}; add caption= to the R: line')
        record = self.sources.json(record_path(self.instance, rid), {}) if rid else {}
        fictional = self.instance.config['family'].get('fictional') is True and record.get('fictional') is True
        if (rid and not record) or not (asset or fictional) or ('file' not in item and asset
                and not self.media_file(relative(asset.lstrip('/'))) and not fictional):
            if 'file' in item:
                raise ValueError(f'{where}: unknown corpus record: {rid}')
            self.notes.append(f'{where}: record or registered crop is missing: {rid}')
            return frame('period-picture', [4, 3], f'{item["cut"]} — {item["reading"]}')
        if 'file' not in item and asset and (local := self.media_file(relative(asset.lstrip('/')))):
            self.sources.data(local)
        if rid and record.get('id') != rid:
            raise ValueError(f'{where}: record ID differs from {rid}')
        reading = '\n\n'.join(item[field] for field in ('cut', 'reading') if field in item)
        source = record.get('source', {})
        defaults = {'source': source.get('holder', ''), 'where': source.get('locator', '').split('; archive:', 1)[0]}
        details = defaults | self.config.get('cut_details', {}).get(rid, {})
        doc = {'caption': caption, 'snippets': [{'asset': asset, 'read': reading}],
               'source': details['source'], 'where': details['where']}
        if rid:
            doc['record'] = rid
        else:
            doc['kind'] = 'studio-cut'
        if fictional:
            doc.update(fictional=True, source=source.get('invented') or details['source'])
        key = rid or raw['id'] + '-cut'
        if 'file' in item or key in self.documents and self.documents[key] != doc:
            digest = sha256(json.dumps([asset, caption, reading]).encode()).hexdigest()[:16]
            key = f'{key}-{digest}'
        self.documents[key] = doc
        return {'doc': key, 'title': caption, 'pick': [1]}

    def game(self, item, key, preceding_picture):
        kind, question = item['kind'], item['ask']
        options = item['options'].split(' / ')
        answer = item.get('answer')
        asset = self.pictures.get(preceding_picture, {}).get('asset')
        targets = self.config.get('spots', {}).get(asset, [])
        if kind == 'find' and options == [label for label, _ in targets] and asset not in self.play['spots']:
            prefix = 'Найди: ' if self.lang == 'ru' else 'Find: '
            self.play['spots'][asset] = [
                {**dict(zip(('x', 'y', 'w', 'h'), rectangle)), 'label': {self.lang: label},
                 'find': {self.lang: question if i == 0 else prefix + label + '.'},
                 'text': {self.lang: answer + '\n\n' + item['after'] if i == len(targets) - 1 else label}}
                for i, (label, rectangle) in enumerate(targets)
            ]
            return {'do': {'kind': 'spots', 'key': asset}}
        if kind == 'trace':
            answer = item['options'] + '\n\n' + answer
        if kind == 'find':
            question += '\n' + ', '.join(options)
        if kind not in ('guess', 'choice') or item['options'] in ('-', '—'):
            options = [self.labels['reveal']]
        answers = item['answers'].split(' / ') if 'answers' in item else [answer] * len(options)
        title = self.config.get('game_titles', {}).get(key, self.labels[kind])
        self.play['games'][key] = {'title': {self.lang: title}, 'intro': {self.lang: item['ask']},
                                  'steps': [{'q': {self.lang: question}, 'choices': [
                                      {'text': {self.lang: opt}, 'outcome': {self.lang: reply}}
                                      for opt, reply in zip(options, answers)]}],
                                  'truth': {'text': {self.lang: item['after']}}}
        return {'do': {'kind': 'game', 'key': key}}

    def chapter(self, raw, part, previous):
        chapter = {'id': raw['id'], 'year': retain_text(previous.get('year'), raw['year'], self.lang),
                   'part': part, 'title': retain_text(previous.get('title'), raw['title'], self.lang),
                   'people': [], 'prose': {}, 'flow': [], 'figures': [], 'records': []}
        replaced = chapter.keys() | {'picture', 'text', 'ask', 'more', 'kids'}
        chapter.update({key: value for key, value in previous.items() if key not in replaced})
        previous_blocks = previous.get('prose', {})
        previous_figures = iter(previous.get('figures', []))
        text = []

        def figure(item, where, old_key=None):
            return self.figure(item, where, raw, old_key) if 'file' in item else {'placeholder': item}

        def block(passage, old=None):
            if not isinstance(old, dict):
                old = {}
            unchanged = old.get('text') == passage
            subjects = self.people(raw, passage)
            if 'mentions' not in self.config and unchanged:
                subjects = old.get('people', [])
            chapter['people'].extend(subjects)
            return {**(old if unchanged else {}), 'text': passage, 'people': subjects}

        def old_block(key, index):
            old = previous_blocks.get(key, [])
            return old[index] if index < len(old) else None

        def place(beat):
            chapter['flow'].append({'after': len(text) - 1, **beat})

        lead_item, location = raw['picture']
        lead = figure(lead_item, location, previous.get('picture'))
        preceding_picture = lead.get('picture')
        if preceding_picture:
            chapter.update(lead)
        else:
            place(lead)

        games = 0
        for tag, item, where in raw['flow']:
            if tag == 'T':
                text.append(block(item, old_block('text', len(text))))
            elif tag == 'L':
                beat = figure(item, where, next(previous_figures, None) if 'file' in item else None)
                preceding_picture = beat.get('picture')
                if preceding_picture:
                    chapter['figures'].append(preceding_picture)
                    beat = {'figure': len(chapter['figures']) - 1}
                place(beat)
            elif tag == 'R':
                beat = self.record(item, where, raw)
                if 'doc' in beat:
                    chapter['records'].append(beat)
                    beat = {'record': len(chapter['records']) - 1}
                place(beat)
            else:
                games += 1
                prefix = f'{self.line}/{raw["id"]}'
                key = prefix if games == 1 else f'{prefix}-{games}'
                if key in self.play['games']:
                    raise ValueError(f'{where}: activity id collision: {key}')
                place(self.game(item, key, preceding_picture))
            if isinstance(item, dict):
                for field in ('caption', 'says', 'cut', 'reading', 'ask', 'options', 'answer', 'answers', 'after'):
                    chapter['people'].extend(self.people(raw, item.get(field, '')))
        chapter['people'].extend(self.people(raw, lead_item.get('caption') or lead_item.get('says', '')))
        kids = previous.get('kids', {})
        chapter['kids'] = {**{k: v for k, v in kids.items() if k not in {'text', 'people'}},
                           **block(raw['kids'], kids)}
        chapter['prose'] = {'text': text, 'ask': [block(raw['ask'], old_block('ask', 0))],
                            'more': [block('\n'.join('- ' + line for line in raw['more']), old_block('more', 0))]}
        for key, blocks in chapter['prose'].items():
            passage = '\n\n'.join(p['text'] for p in blocks)
            chapter[key] = retain_text(previous.get(key), passage, self.lang)
        if 'mentions' not in self.config:
            chapter['people'].extend(previous.get('people', []))
        chapter['people'] = sorted(set(chapter['people']))
        return chapter


def translations(old, meta, chapters, pictures, play, language, languages):
    sources = {f'feed:{key}': meta[key] for key in ('title', 'lead')}
    for chapter in chapters:
        cid = chapter['id']
        for key in ('title', 'text', 'more', 'ask', 'year'):
            sources[f'{cid}:{key}'] = chapter[key]
        sources[f'{cid}:kids.text'] = chapter['kids']['text']
        for index, spec in enumerate(chapter['records']):
            sources[f'{cid}:records.{index}'] = spec['title']
        for group in ('facts', 'places', 'extras'):
            for index, node in enumerate(chapter.get(group, [])):
                prefix = f'{cid}:{group}.{index}'
                if isinstance(node, str):
                    sources[prefix] = node
                elif isinstance(node, dict):
                    sources.update({f'{prefix}.{key}': value for key, value in node.items()
                                    if isinstance(value, (str, dict))})

    def catalog(node, path):
        if isinstance(node, dict):
            if language in node and isinstance(node[language], str):
                key = 'catalog:' + '/'.join(quote(str(x), safe='') for x in path)
                sources[key] = node[language]
                saved = old.get(key, {})
                if saved.get('_source') == node[language]:
                    node.update({lang: saved[lang] for lang in languages
                                 if lang != language and saved.get(lang)})
            else:
                for key, value in node.items():
                    catalog(value, [*path, key])
        elif isinstance(node, list):
            for index, value in enumerate(node):
                catalog(value, [*path, index])

    for key, item in pictures.items():
        catalog(item['caption'], ['pictures', key, 'caption'])
    catalog(play, ['play'])
    return {key: row for key, row in old.items()
            if key.startswith('_') or (
                key in sources and row.get('_source') ==
                (sources[key].get(language) if isinstance(sources[key], dict) else sources[key]))}


def compile_chapters(instance, folder, sources, config, raw, meta):
    expected = config.get('chapter_count')
    if expected is not None and [ch['n'] for ch in raw] != list(range(expected)):
        raise ValueError(f'Expected chapters 00 through {expected - 1:02d}, once each')
    importer = Importer(instance, sources, folder, config)
    old = {ch['id']: ch for ch in sources.json(folder / 'chapters.json', [])}
    starts = part_starts(config, meta, raw, old, instance.source_language)
    part = 0
    chapters = []
    for ch in raw:
        if ch['n'] in starts:
            part = part + 1 if 'parts' in config else starts[ch['n']]
        chapters.append(importer.chapter(ch, part, old.get(ch['id'], {})))
    if config.get('cover_from_first', True) and 'picture' in chapters[0]:
        meta['cover'] = chapters[0]['picture']
    persons = meta.setdefault('persons', {})
    for pid in sorted({pid for chapter in chapters for pid in chapter['people']}):
        persons.setdefault(pid, pid)
    result = {folder / 'feed.json': meta, folder / 'chapters.json': chapters,
              folder / 'pictures.json': importer.pictures, folder / 'documents.json': importer.documents,
              folder / 'play.json': importer.play}
    if importer.manifest_path.is_file() or importer.manifest['assets']:
        result[importer.manifest_path] = importer.manifest
    localized = folder / 'translations.json'
    if (old_translations := sources.json(localized)) is not None:
        result[localized] = translations(old_translations, meta, chapters, importer.pictures, importer.play,
                                         instance.source_language, instance.languages)
    for note in importer.notes:
        print(note)
    return result | importer.new_media


def run(instance, args):
    from familiar.instance.writer import write_studio
    loaded = load(instance, args.feed, args.studio, args.config, args.source_ref,
                  draft=args.feed_command == 'storyboard')
    folder, sources, config, chapters, meta = loaded
    if args.feed_command == 'storyboard':
        from .storyboard import render
        out = args.out or instance.path('build') / 'storyboards' / (args.feed + '.html')
        page, notes = render(instance, loaded, out.resolve())
        write_studio(instance, {out: page.encode('utf-8')}, out=out.parent)
        print(notes)
        print(out)
        return
    changes = compile_chapters(instance, *loaded)
    changes = {path: data if isinstance(data, bytes) else (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
               for path, data in changes.items()}
    if args.out:
        media = instance.path('media')
        changes = {args.out / ('media' / path.relative_to(media) if path.is_relative_to(media)
                               and path.name != 'manifest.json' else path.name): content
                   for path, content in changes.items()}
    write_studio(instance, changes, out=args.out, feed=folder, verify_inputs=sources.verify)
    print(f'{folder.name}: {len(chapters)} chapters')
