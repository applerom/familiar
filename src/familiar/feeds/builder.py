# START_MODULE_CONTRACT: MOD-FEED-BUILDER
# PURPOSE: Materialize authored feed catalogs without executing family programs or writing family inputs.
# PRD_REF: docs/PRD.md#PIPELINE
# INVARIANTS:
# - feed references resolve from working people rather than a delivered graph [review: engine lead]
# - unresolved people and documents stop output [test: tests/gate/test_data_guarantees.py::test_f1_shown_reference_resolves]
# - document subjects reach reader export as canonical people rather than feed symbols [test: tests/journeys/test_installed_engine.py::test_installed_engine]
# - photo pairs bind canonical subjects and a real original before materialization [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#FORMS
# - MOD-INSTANCE-MODEL (the same registered asset path as the trust gate)
# - MOD-NARRATIVE-DISCLOSURE (subject-linked alternatives and nested passages)
# - MOD-INSTANCE-RESEARCH-FORMS (same file containers as the gate)
# :END_MODULE_CONTRACT
import copy
import re
import json
from contextvars import ContextVar
from pathlib import Path

from . import translations

context = ContextVar('feed_instance')

def _feed_tr():
    return translations

def read(p, default=None):
    from familiar.instance.research_forms import require_container
    from familiar.instance.subjects import normalized
    return require_container(p, normalized(json.loads(p.read_text(encoding='utf-8')))) if p.exists() else default


def row(s):
    return {context.get().source_language: s.strip()} if isinstance(s, str) else dict(s)


def asset_exists(asset):
    return context.get().media_file(asset) is not None


def osm(lat, lon, z=17):
    return f'https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map={z}/{lat}/{lon}'


class _Feed:
    def __init__(self, folder):
        self.dir = Path(folder)
        self.meta = read(self.dir / 'feed.json')
        if self.meta is None:
            raise SystemExit(f'{self.dir}: no feed.json')
        if not isinstance(self.meta.get('profile', {}), dict):
            self.meta['profile'] = {}
        self.chapters = read(self.dir / 'chapters.json', [])
        self.pictures = read(self.dir / 'pictures.json', {})
        self.documents = read(self.dir / 'documents.json', {})
        self.tr = read(self.dir / 'translations.json', {})
        self.links = read(self.dir / 'links.json', {})
        self.names = read(self.dir / 'names.json', {})
        self.holes = []
        self.notes = []
        from familiar.checks.engine import _known_people
        self.people = _known_people(context.get())
        self.tree = set(self.people)

    def hole(self, where, what, check=None):
        from familiar.check_policy import decision
        target = self.holes if decision(check) == 'block' else self.notes
        target.append(f'{where}: {what}')

    # references -----------------------------------------------------------------------------------------------
    def person(self, sym, where):
        pid = self.meta.get('persons', {}).get(sym, sym)  # a symbol from feed.json "persons", or a tree id as is
        if sym not in self.meta.get('persons', {}) and sym not in self.tree:
            self.hole(where, f'person "{sym}" is not in feed.json persons', 'feed.person-reference')
        elif pid not in self.tree:
            self.hole(where, f'person {sym} = {pid} is not in the tree (public/graph.json)', 'feed.person-reference')
        return self.people[pid]['id'] if pid in self.people else pid

    def picture(self, key, where):
        """A picture key, or a list of candidate keys (the first that exists wins)."""
        keys = key if isinstance(key, list) else [key]
        for k in keys:
            p = self.pictures.get(k)
            if p and p.get('kind') == 'photo-restoration':
                from familiar.instance.subjects import photo_pair
                p = copy.deepcopy(p)
                photo_pair(context.get(), p)
            if p and asset_exists(p['asset']):
                p = copy.deepcopy(p)
                p.pop('card', None)
                if p.get('ours'): p['ours'].pop('card', None)
                def subjects(image):
                    if 'subjects' in image:
                        image['subjects'] = [self.person(pid, where) for pid in image['subjects']]
                    for child in ('ours', 'orig'):
                        if isinstance(image.get(child), dict):
                            subjects(image[child])
                subjects(p)
                from familiar.instance.subjects import photo_pair
                photo_pair(context.get(), p)
                return p
        for k in keys:
            if k not in self.pictures:
                self.hole(where, f'picture "{k}" is not in pictures.json', 'feed.local-asset')
            else:
                self.hole(where, f'picture "{k}": file {self.pictures[k]["asset"]} is missing', 'feed.local-asset')
        return None

    def record(self, spec, where):
        d = self.documents.get(spec['doc'])
        if d and d.get('kind') == 'index':  # an index entry without an image (DOC-6): the reading only, marked "image not seen"
            if not (d.get('read') or '').strip():
                self.hole(where, f'index document "{spec["doc"]}" has no reading', 'feed.source-reading')
                return None
            r = {'kind': 'index', 'read': d['read'], 'title': row(spec['title'])}
            if spec.get('kids') is True:
                r['kids'] = True
            for k in ('source', 'where'):
                if d.get(k):
                    r[k] = d[k]
            return r
        if not d or not d.get('snippets'):
            self.hole(where, f'document "{spec["doc"]}" has no crops in documents.json', 'feed.source-selection')
            return None
        sn = d['snippets']
        pick = spec.get('pick')
        base = spec.get('index_base', d.get('index_base', 1))
        if type(base) is not int or base not in (0, 1) or (pick is not None and (
                not isinstance(pick, list) or not pick or any(type(n) is not int for n in pick))):
            self.hole(where, f'document "{spec["doc"]}": invalid crop selection/index_base', 'feed.source-selection')
            return None
        pick = [n + 1 - base for n in pick] if pick is not None else list(range(1, len(sn) + 1))
        if any(n < 1 or n > len(sn) for n in pick):
            self.hole(where, f'document "{spec["doc"]}": crop numbers {pick} outside 1..{len(sn)}', 'feed.source-selection')
            return None
        s = [sn[n - 1] for n in pick]
        for x in s:
            if x.get('asset') and not asset_exists(x['asset']):
                self.hole(where, f'crop file {x["asset"]} is missing', 'feed.source-selection')
        if d.get('full') and not asset_exists(d['full']):
            self.hole(where, f'full page {d["full"]} is missing', 'feed.local-asset')
        r = {'asset': s[0]['asset'], 'read': s[0]['read']}
        if 'field' in s[0]:
            r['field'] = s[0]['field']
        if len(s) > 1:
            r['parts'] = s[1:]
        r['title'] = row(spec['title'])
        if spec.get('kids') is True:
            r['kids'] = True
        for k in ('full', 'source', 'where', 'record', 'fictional', 'subjects', 'excerpt'):
            if d.get(k):
                r[k] = d[k]
        if 'subjects' in r:
            r['subjects'] = [self.person(pid, where) for pid in r['subjects']]
        return r

    def records(self, specs, where):
        return [r for r in (self.record(s, where) for s in specs) if r]

    def link(self, key, where):
        """A link from the feed's catalog links.json: label (four languages, like a picture caption), url, kind."""
        if isinstance(key, dict):
            source = key
        elif key in self.links:
            source = self.links[key]
        else:
            return None
        result = copy.deepcopy(source)
        result.pop('people', None)
        return self.attributed(source, result, where)

    def node(self, n, where):
        """A node of a chapter's small tree: a person (symbol or tree id) and/or a name without a card, with a year."""
        o = {}
        if n.get('id'):
            o['id'] = self.person(n['id'], where)
        for k in ('name', 'year'):
            if k in n:
                o[k] = row(n[k]) if isinstance(n[k], dict) else n[k]
        return o

    def gen_label(self, v):
        """`who` / `where` of the generation strip: a source-language string localized by the profile table, or a ready row."""
        return dict(v) if isinstance(v, dict) else self.localize(v) if v else v

    def localize(self, s):
        """Names in the generation strip: Source forms get configured target forms from the profile."""
        table = self.meta.get('profile', {}).get('localize', {})
        out = {context.get().source_language: s}
        for lang in tuple(x for x in context.get().languages if x != context.get().source_language):
            v = s
            for k in sorted(table, key=len, reverse=True):
                v = v.replace(k, table[k][lang])
            out[lang] = v
        return out if any(out[lang] != s for lang in tuple(x for x in context.get().languages if x != context.get().source_language)) else s

    # chapters ---------------------------------------------------------------------------------------------------
    def attributed(self, source, output, where, *, block=False):
        if 'people' in source:
            output['people' if block else '_people'] = [self.person(p, where) for p in source['people']]
        return output

    def prose(self, source, output, fields, where):
        for field, blocks in source.get('prose', {}).items():
            if field not in fields:
                raise ValueError('unsupported subject-linked prose field: ' + field)
            target = output.setdefault('_prose', {})
            target[field] = []
            for block in blocks:
                built = self.attributed(block, {'text': row(block['text'])}, where, block=True)
                if 'people' not in built:
                    raise ValueError('prose block needs explicit people')
                if 'otherwise' in block:
                    alternative = block['otherwise']
                    if 'people' not in alternative:
                        raise ValueError('otherwise passage needs explicit people')
                    built['otherwise'] = self.attributed(alternative, {'text': row(alternative['text'])}, where, block=True)
                target[field].append(built)
            output[field] = {lang: '\n\n'.join(b['text'].get(lang, '') for b in target[field]) for lang in context.get().languages}

    def chapter(self, c):
        i = c['id']
        year = c.get('year', '')
        # A year in words ("before 1914") is a translation unit; a bare number stays as written.
        year = row(year) if isinstance(year, str) and re.search(r'[^\W\d_]', year) else year
        o = {'id': i, 'year': year, 'title': row(c.get('title', '')), 'text': row(c.get('text', ''))}
        if 'hardships' in c:
            o['hardships'] = copy.deepcopy(c['hardships'])
        if c.get('text_kids'):
            o['text_kids'] = row(c['text_kids'])
        if c.get('kind'):
            o['kind'] = c['kind']
        if c.get('more'):
            o['more'] = row(c['more'])
        if c.get('variants'):
            o['variants'] = [self.attributed(v, {**{k: row(v[k]) for k in ('title', 'text', 'more') if v.get(k)},
                              **({'version': v['version']} if 'version' in v else {})}, i) for v in c['variants']]
        if c.get('places'):
            o['places'] = [self.attributed(p, {'name': row(p['name']), **({'note': row(p['note'])} if p.get('note') else {}),
                            **({'url': osm(*p['map'])} if p.get('map') else {'url': p['url']} if p.get('url') else {})}, i) for p in c['places']]
        if c.get('picture'):
            p = self.picture(c['picture'], i)
            if p:
                o['picture'] = p
        if c.get('people'):
            o['people'] = [self.person(s, i) for s in c['people']]
        if c.get('facts'):
            o['facts'] = [{'text': row(f)} if isinstance(f, str) else self.attributed(f, {
                'text': row(f['text']), **{k: f[k] for k in ('record', 'status', 'accepted', 'basis', 'sources', 'decision', 'weight') if k in f}}, i) for f in c['facts']]
        if c.get('figures'):
            o['figures'] = [p for p in (self.picture(k, i) for k in c['figures']) if p]
        if c.get('clan'):
            cl = c['clan']
            o['clan'] = {'parents': [self.person(s, i) for s in cl['parents']],
                         'families': [{'head': self.person(f['head'], i), **({'spouse': self.person(f['spouse'], i)} if f.get('spouse') else {}),
                                       'kids': [self.person(k, i) for k in f.get('kids', [])]} for f in cl['families']]}
        if c.get('part'):
            parts = self.meta.get('parts', [])
            if 1 <= c['part'] <= len(parts):
                o['part'] = dict(parts[c['part'] - 1])
        if any(r.get('kids') is True for r in c.get('records', [])):
            o['kidsSelection'] = True
        recs = self.records(c.get('records', []), i)
        if recs:
            o['records'] = recs
        if 'kidsRecords' in c:
            o['kidsRecords'] = c['kidsRecords']
        if c.get('flow'):
            nr, nf = len(recs), len(o.get('figures', []))
            ok = [f for f in c['flow'] if ('figure' not in f or f['figure'] < nf) and ('record' not in f or f['record'] < nr)]
            o['flow'] = ok
        if c.get('extras'):
            xs = []
            for x in c['extras']:
                e = {'title': row(x['title']), 'text': row(x['text'])}
                if x.get('more'):
                    e['more'] = row(x['more'])
                if x.get('picture'):
                    p = self.picture(x['picture'], i)
                    if p:
                        e['picture'] = p
                if x.get('records'):
                    xr = self.records(x['records'], i)
                    if xr:
                        e['records'] = xr
                if x.get('kids'):
                    e['kids'] = row(x['kids'])
                xs.append(self.attributed(x, e, i))
            o['extras'] = xs
        if c.get('links'):
            o['links'] = [x for k in c['links'] if (x := self.link(k, i))]
        if c.get('tree'):
            t = c['tree']
            o['tree'] = {'parents': [self.node(n, i) for n in t.get('parents', [])], 'children': [self.node(n, i) for n in t.get('children', [])]}
            if t.get('highlight'):
                o['tree']['highlight'] = [self.person(s, i) for s in t['highlight']]
        if c.get('ask'):
            o['ask'] = row(c['ask'])
        if c.get('kids'):
            o['kids'] = self.attributed(c['kids'], {**({'title': row(c['kids']['title'])} if c['kids'].get('title') else {}), 'text': row(c['kids']['text'])}, i)
        if c.get('gen'):
            g = c['gen']
            o['gen'] = {'at': g['at'], **{k: self.gen_label(g[k]) for k in ('who', 'where') if k in g}}
        self.prose(c, o, {'title', 'text', 'more', 'ask', 'text_kids'}, i)
        return o

    def _build(self):
        m = self.meta
        profile = m.get('profile', {})
        if not isinstance(profile, dict):
            profile = {}
        chapters = [self.chapter(c) for c in self.chapters]
        gens = []
        for g in m.get('gens', []):
            o = {'name': row(g['name']), 'years': g['years']}
            for lang in tuple(x for x in context.get().languages if x != context.get().source_language):
                o['name'].setdefault(lang, o['name'][context.get().source_language])
            if g.get('kids'):
                o['kids'] = row(g['kids'])
            if g.get('ids'):
                o['ids'] = [self.person(s, 'gens') for s in g['ids']]
            gens.append(o)
        cover = self.pictures.get(m.get('cover'), {}).get('asset') or m.get('cover')
        if cover and not asset_exists(cover):
            self.hole('feed', f'cover {m.get("cover")} is missing', 'feed.local-asset')
        cover = cover or ''
        feed = {'id': m['id'], 'title': row(m.get('title', '')), 'lead': row(m.get('lead', '')), 'cover': cover, 'period': m.get('period', ''), 'line': m.get('line', ''),
                'people': [self.person(s, 'feed') for s in m.get('people', [])], 'gens': gens, 'chapters': chapters}
        self.prose(m, feed, {'title', 'lead', 'period', 'line'}, 'feed')
        if not gens:
            del feed['gens']
        if self.names:
            feed['names'] = self.name_table()
        self.units = units(feed)
        ft = _feed_tr()
        self.units.extend(ft.catalog_units(self.dir))
        self.stale = ft.apply(self.units, self.tr)  # an old translation stays until the next batch (author, 21.10.2026)
        self.ft = ft
        return feed

    def name_table(self):
        """names.json: person (symbol or tree id) -> how to sign the person in the reader's language, for the chapter's small
        tree and the clan diagram (LANG-2: the tree keeps the original spelling, the feed signs in the reader's language).
        Each entry uses the configured languages (missing languages fall back to the source) and an optional `short` with the same languages."""
        out = {}
        registry = None
        for sym, v in self.names.items():
            if sym.startswith('_'):
                continue
            pid = self.person(sym, 'names')
            out[pid] = {lang: v.get(lang) or v.get(context.get().source_language) for lang in context.get().languages}
            for lang, spec in v.get('_surname_forms', {}).items():
                if lang in out[pid]:
                    if registry is None:
                        from familiar.rules.cascade import Registry
                        from familiar.rules.roles import method_root
                        registry = Registry(method_root() / 'rules', context.get())
                    surname = spec['surname']
                    rendered = registry.surname_form(surname, spec['gender'], spec['paradigm'],
                                                     spec.get('case', 'nom'), f'language:{lang}')
                    out[pid][lang] = out[pid][lang].removesuffix(surname) + rendered if out[pid][lang].endswith(surname) else out[pid][lang]
            if v.get('short'):  # the label of the chapter's small tree, where the story goes by the first name
                out[pid]['short'] = {lang: v['short'].get(lang) or v['short'].get(context.get().source_language) for lang in context.get().languages}
        return out

def units(feed):
    """Translation units "<chapter>:<path>" (the same keys as the old builders' units())."""
    out = []

    def g(key, r):
        if isinstance(r, dict) and r.get(context.get().source_language):
            out.append((key, r))
    g('feed:title', feed['title'])
    g('feed:lead', feed['lead'])
    for c in feed['chapters']:
        i = c['id']
        for k in ('title', 'text', 'more', 'text_kids', 'year'):  # text_kids: the chapter's separate text for children
            g(f'{i}:{k}', c.get(k))
        for k in ('title', 'text'):
            g(f'{i}:kids.{k}', (c.get('kids') or {}).get(k))
        g(f'{i}:ask', c.get('ask'))
        for n, r in enumerate(c.get('records', [])):
            g(f'{i}:records.{n}', r.get('title'))
        for n, x in enumerate(c.get('facts', [])):
            g(f'{i}:facts.{n}', x.get('text'))
        for n, v in enumerate(c.get('variants', [])):
            for k in ('title', 'text', 'more'):
                g(f'{i}:variants.{n}.{k}', v.get(k))
        for n, x in enumerate(c.get('extras', [])):
            for k in ('title', 'text', 'more', 'kids'):
                g(f'{i}:extras.{n}.{k}', x.get(k))
            for m, r in enumerate(x.get('records', [])):
                g(f'{i}:extras.{n}.records.{m}', r.get('title'))
        for n, p in enumerate(c.get('places', [])):
            for k in ('name', 'note'):
                g(f'{i}:places.{n}.{k}', p.get(k))
    return out

