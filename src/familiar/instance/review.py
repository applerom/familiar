# START_MODULE_CONTRACT: MOD-OUTPUT-REVIEW
# PURPOSE: Bind independent reading attestations to projected page bytes and scoped safety inputs.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - photo treatments retain dead-only public permission uses for later withdrawal [review: engine lead]
# - review uses the active person permissions for merged references [review: engine lead]
# - unrelated records preserve reading while changed display bytes lapse it [review: engine lead]
# - namesakes are review cues, not canonical subject identities [review: engine lead]
# - confirmation compares an inspected ticket instead of certifying a replacement build [test: tests/gate/test_data_guarantees.py::test_f8_checked_generation_rechecks_used_permissions]
# - unnamed role labels and narrator kin words bind respectively to name and kinship uses, without event or narrative permission [review: engine lead]
# - copied chapters cannot overwrite a reviewed unit [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE
# - MOD-FAMILY-WRITER
# - MOD-SUBJECT-CLOSURE
# - MOD-NARRATIVE-DISCLOSURE (only the permitted original or alternative passage is shown)
# :END_MODULE_CONTRACT
import hashlib
import html
import json
import re
from datetime import UTC, datetime

from .gate import boundary

RULES = ('R1', 'R2', 'R3', 'R4')
BLIND_SPOTS = 'Name/term matches are cues: paraphrase, another language, namesakes and image content need eyes.'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')).hexdigest()


def _shown_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def _safety_inputs(instance, ids, uses=()):
    from familiar.checks.engine import _known_people, life_status, load
    from familiar.rules.cascade import Registry
    from familiar.rules.roles import method_root
    known, privacy = _known_people(instance), load(instance.path('privacy'), {})
    rows = {p['id']: p for p in privacy.get('living', []) if isinstance(p, dict)}
    registry = Registry(method_root() / 'rules', instance)
    lists = {}
    for scope in [None] + ['feed:' + p.name for p in instance.path('feeds').glob('*') if p.is_dir()]:
        for key in ('privacy.closed_topics_file', 'privacy.present_day_politics_file'):
            if name := registry.resolve_setting(key, scope).value:
                path = instance._inside(name)
                lists[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    photo_assets = {u['asset'] for u in uses if u.get('field') == 'archive-rights'}
    photo_rights = {}
    if photo_assets:
        from familiar.instance.archive import photograph_rights
        def photographs(value):
            if isinstance(value, dict):
                if value.get('kind') == 'family-photograph' and value.get('asset') in photo_assets:
                    photo_rights.setdefault(value['asset'], []).append(photograph_rights(instance, value))
                for child in value.values():
                    photographs(child)
            elif isinstance(value, list):
                for child in value:
                    photographs(child)
        feed_names = {u['item'].split('/', 1)[0].removeprefix('feed:')
                      for u in uses if u.get('field') == 'archive-rights' and u['item'].startswith('feed:')}
        for name in sorted(feed_names):
            # Valid materialized feed images come from their picture catalogue;
            # unrelated drafts/catalogues do not supply this generation's rights.
            photographs(load(instance.path('feeds') / name / 'pictures.json', {}))
        photographs(known)
    return {'people': {pid: {'life': life_status(known.get(pid, {'id': pid}), privacy),
                             'permission': [rows[p] for p in [pid, *known.get(pid, {}).get('identityAliases', [])]
                                            if p in rows]} for pid in sorted(ids)},
            'closed_topics': privacy.get('closed_topics', []), 'lists': lists,
            'archive_rights': photo_rights,
            'trust': digest([r for r in registry.rules.values() if r['kind'] == 'trust'])}


def _output_uses(instance, kind, data, feed=None):
    from familiar.checks.engine import _known_people, life_status, load
    from familiar.feeds import service

    from .subjects import closure
    known, privacy = _known_people(instance), load(instance.path('privacy'), {})
    uses = []
    def add(item, pid, field, permission=None, **semantics):
        use = {'item': item, 'person': pid, 'field': field, 'permission': permission,
                   'life': life_status(known.get(pid, {'id': pid}), privacy), **semantics}
        if use not in uses:
            uses.append(use)
    def image_rights(item, pic):
        if pic.get('kind') == 'family-photograph':
            uses.append({'item': item, 'person': None, 'field': 'archive-rights', 'asset': pic.get('asset')})
    def image_use(item, pic, people):
        from familiar.checks.engine import generated
        image_rights(item, pic)
        for pid in closure(instance, pic, shape='image', people=people).people:
            add(item, pid, 'pictures', permission='never-if-living' if pic.get('kind') == 'photo-treatment' else None,
                generated=generated(pic), subject_child=pic.get('subject_child', False))
    if kind in {'tree', 'reader'}:
        resolved = closure(instance, data, shape='graph', people=known)
        for pid, status in data.get('cardStatuses', {}).items():
            add('person:' + pid, pid, 'cardStatuses', 'never-if-living')
            for key in ('documented_relationships', 'candidate_relationships'):
                for edge in status.get(key, []):
                    for member in (edge.get(k) for k in ('from', 'to', 'parent', 'child')):
                        if member:
                            add('person:' + pid, member, 'cardStatuses', 'never-if-living')
        for pid, person in data.get('people', {}).items():
            for key, value in person.items():
                if value not in (None, '', [], {}) and key not in {'id', 'living', 'origin'}:
                    if key == 'events':
                        from .publication import event_kind
                        for event in value:
                            add('person:' + pid, pid, event_kind(event), 'events')
                    else:
                        add('person:' + pid, pid, {'names': 'name', 'placeholder': 'name', 'reportedKinship': 'kinship', 'media': 'pictures', 'cardPresentation': 'birth'}.get(key, key))
        for rid, record in resolved.records.items():
            uses.append({'item': 'record:' + rid, 'person': None, 'field': 'document', 'record': rid, **({'excerpt': record['excerpt']} if record.get('excerpt') else {})})
            from .subjects import explicit_subjects
            for pid in explicit_subjects(record):
                add('record:' + rid, pid, 'document', 'never-if-living')
        for image in resolved.images:
            image_use('image:' + str(image.get('asset')), image, known)
        for family in data.get('families', []):
            for pid in [family.get('husband'), family.get('wife'), *family.get('children', [])]:
                if pid:
                    for event in family.get('events', []):
                        from .publication import event_kind
                        add('family:' + family['id'], pid, event_kind(event), 'events')
        for edge in [*data.get('edges', []), *data.get('associations', [])]:
            if edge.get('text') or edge.get('note'):
                for key in ('from', 'to', 'parent', 'child'):
                    if edge.get(key):
                        add('edge:' + str(edge.get('from', edge.get('parent'))), edge[key], 'edge-text', 'never-if-living')
    for folder in service.folders(instance, feed) if kind in {'feeds', 'reader'} else []:
        shown = next((f for f in (data if kind == 'feeds' else data.get('feeds', [])) if f['id'] == folder.name), {})
        meta = load(folder / 'feed.json', {})
        aliases = known | {k: known[v] for k, v in meta.get('persons', {}).items() if v in known}
        docs, pics = load(folder / 'documents.json', {}), load(folder / 'pictures.json', {})
        chapters = load(folder / 'chapters.json', [])
        for chapter in [dict(meta, id='__feed__', chapters=[]), *chapters]:
            item = 'feed:' + folder.name + '/' + chapter['id']
            shape = 'feed' if chapter['id'] == '__feed__' else 'chapter'
            resolved = closure(instance, chapter, shape=shape, documents=docs, pictures=pics, people=aliases)
            for pid in resolved.people:
                add(item, pid, 'name')
            from .publication import allowed
            def subjects(block, aliases=aliases, chapter=chapter):
                return [aliases.get(p, {'id': p})['id'] for p in block.get('people', chapter.get('people', []))]
            def permitted(block):
                return all(life_status(known.get(pid, {'id': pid}), privacy) == 'dead' or
                           'summary' in allowed(privacy, known.get(pid, {'id': pid})) for pid in subjects(block))
            fields = ('title', 'lead', 'period', 'line') if shape == 'feed' else ('title', 'text', 'more', 'ask', 'text_kids')
            for field in fields:
                blocks = chapter.get('prose', {}).get(field, [chapter] if chapter.get(field) else [])
                for block in blocks:
                    shown_block = block if permitted(block) else block.get('otherwise')
                    if shown_block and permitted(shown_block):
                        for pid in subjects(shown_block):
                            add(item, pid, 'summary')
            for field in ('facts', 'variants', 'places', 'extras', 'kids'):
                values = chapter.get(field, [])
                for value in values if isinstance(values, list) else [values]:
                    if isinstance(value, dict) and permitted(value):
                        for pid in subjects(value):
                            add(item, pid, 'summary')
            links = load(folder / 'links.json', {})
            for link in chapter.get('links', []):
                value = links.get(link, {}) if isinstance(link, str) else link
                if value and permitted(value):
                    for pid in subjects(value):
                        add(item, pid, 'summary')
            for alias, fields in chapter.get('published_fields', {}).items():
                pid = aliases.get(alias, {}).get('id', alias)
                for field in fields:
                    if life_status(known.get(pid, {'id': pid}), privacy) == 'dead' or field in {'name', 'kinship'} or field in allowed(privacy, known.get(pid, {'id': pid})):
                        add(item, pid, field)
            visible = dict(shown, chapters=[]) if shape == 'feed' else next((c for c in shown.get('chapters', []) if c['id'] == chapter['id']), {})
            displayed = closure(instance, visible, shape=shape, people=known)
            for rid, record in displayed.records.items():
                uses.append({'item': item + '/record:' + rid, 'person': None, 'field': 'document', 'record': rid, **({'excerpt': record['excerpt']} if record.get('excerpt') else {})})
                from .subjects import explicit_subjects
                for pid in explicit_subjects(record):
                    add(item + '/record:' + rid, pid, 'document', 'never-if-living')
            for pic in displayed.images:
                image_use(item + '/image', pic, aliases)
        for group in shown.get('gens', []):
            if group.get('years'):
                for pid in group.get('ids', []):
                    add('feed:' + folder.name + '/generation', pid, 'birth')
        def dates(node, item):
            if isinstance(node, dict):
                if node.get('id') and node.get('year'):
                    add(item, node['id'], 'birth')
                for child in node.values():
                    dates(child, item)
            elif isinstance(node, list):
                for child in node:
                    dates(child, item)
        for page in shown.get('chapters', []):
            dates(page.get('tree', {}), 'feed:' + folder.name + '/' + page['id'])
    return uses


def _review_units(instance, kind, data, files):
    """Canonical page serialization plus exact reachable media bytes, all languages."""
    units = {}
    def unit(key, value):
        if key in units:
            raise ValueError('duplicate review unit: ' + key)
        units[key] = value
    def assets(value):
        found = {}
        def walk(node):
            if isinstance(node, dict):
                for key, child in node.items():
                    if key in {'asset', 'full', 'cover'} and isinstance(child, str) and child:
                        name = child.lstrip('/')
                        if name in files:
                            found[name] = hashlib.sha256(files[name]).hexdigest()
                        elif path := instance.media_file(child):
                            found[name] = hashlib.sha256(path.read_bytes()).hexdigest()
                    else:
                        walk(child)
            elif isinstance(node, list):
                for child in node:
                    walk(child)
        walk(value)
        return found
    feeds = data if kind == 'feeds' else data.get('feeds', [])
    for feed in feeds:
        shell = {k: v for k, v in feed.items() if k != 'chapters'}
        prefix = 'feed:' + feed['id'] + '/'
        unit(prefix + '__feed__', _shown_digest([shell, assets(shell)]))
        for page in feed['chapters']:
            if page['id'].startswith('__'):
                raise ValueError('reserved chapter id: ' + page['id'])
            unit(prefix + page['id'], _shown_digest([page, assets(page)]))
    if kind != 'feeds':
        graph = {k: v for k, v in data.items() if k != 'feeds'}
        unit(kind + ':tree', _shown_digest([graph, assets(graph)]))
        for name, content in files.items():
            if name not in {'graph.json', 'bundle.json'}:
                unit(kind + ':file:' + name, hashlib.sha256(content).hexdigest())
    return units


def _review_manifest(instance, units, uses):
    from familiar.checks.engine import load
    safety = _safety_inputs(instance, {u['person'] for u in uses if u['person']}, uses)
    saved = load(instance.path('state') / 'attestations.json', {})
    attestations, missing, releases = [], [], []
    for page, byte_digest in units.items():
        for language in instance.languages:
            key = page + '@' + language
            row = saved.get(key, {})
            valid = (row.get('digest') == byte_digest and row.get('safety_digest') == digest(safety) and
                     row.get('inspection_digest') == digest([page, language, byte_digest, digest(safety)]) and
                     row.get('reviewer') and row.get('author') and row['reviewer'] != row['author'] and
                     row.get('verdict') == 'pass' and row.get('at') and set(row.get('rules', [])) == set(RULES) and
                     row.get('page') == page and row.get('language') == language)
            if valid:
                attestations.append(row)
            else:
                release = saved.get('host-release:' + key, {})
                if (release.get('by') and release.get('at') and release.get('digest') == byte_digest and
                        release.get('safety_digest') == digest(safety)):
                    releases.append(release)
                else:
                    missing.append(key)
    return {'state': 'preview' if missing else 'host release' if releases else 'clean',
            'unreviewed': missing, 'attestations': attestations, 'host_releases': releases,
            'safety': safety, 'uses': uses, 'review_units': units}


def review_ticket(material):
    """Retain this ticket alongside the exact Publication.files() you inspect."""
    manifest = material.manifest
    return {'kind': manifest['kind'], 'feed': manifest['feed'],
            'languages': manifest['languages'], 'review_units': dict(manifest['review_units']),
            'safety_digest': digest(manifest['safety'])}


@boundary('writer')
def attest(instance, kind, *, reviewer, author, ticket=None, feed=None, pages=None, languages=None, stage='reading', at=None):
    """An explicit independent verdict; the engine verifies binding, not judgement."""
    if not reviewer or not author or reviewer == author:
        raise ValueError('reviewer must be named and independent of the author')
    if not isinstance(ticket, dict):
        raise ValueError('Confirm the review ticket saved with the material you inspected; prepare new material first')  # noqa: TRY004
    from familiar.checks.engine import load

    from .gate import publication
    from .writer import mutate
    result = publication(instance, kind, feed, for_review=True)
    current = review_ticket(result)
    units = result.manifest['review_units']
    languages = current['languages'] if languages is None else languages
    if not languages or set(languages) - set(ticket['languages']):
        raise ValueError('unknown attestation language')
    if stage not in {'reading', 'blind'}:
        raise ValueError('attestation stage must be reading or blind')
    if pages:
        selected = {k: v for k, v in units.items() if k in pages or k.rsplit('/', 1)[-1] in pages}
        if not selected or any(p not in selected and not any(k.endswith('/' + p) for k in selected) for p in pages):
            raise ValueError('unknown attestation page')
        units = selected
    if (any(ticket.get(key) != current[key] for key in ('kind', 'feed', 'safety_digest', 'languages')) or
            any(ticket.get('review_units', {}).get(key) != value for key, value in units.items())):
        raise ValueError('review material changed; inspect replacement material and confirm its new ticket')
    path = instance.path('state') / 'attestations.json'
    rows = load(path, {})
    for page, byte_digest in units.items():
        for language in languages:
            rows[page + '@' + language + (':blind' if stage == 'blind' else '')] = {'page': page, 'language': language, 'reviewer': reviewer, 'author': author,
                'digest': byte_digest, 'safety_digest': digest(result.manifest['safety']), 'rules': ['R3'] if stage == 'blind' else list(RULES),
                'inspection_digest': digest([page, language, byte_digest, digest(result.manifest['safety'])]),
                'verdict': 'pass', 'at': at or datetime.now(UTC).isoformat(), 'stage': stage}
    result.check(instance)
    mutate(instance, {path: rows})
    return rows


@boundary('writer')
def host_release(instance, kind, *, by, feed=None, pages=None, at=None):
    from familiar.checks.engine import load

    from .gate import publication
    from .writer import mutate
    if not by:
        raise ValueError('host release requires a named host decision')
    result = publication(instance, kind, feed, for_review=True)
    rows = load(instance.path('state') / 'attestations.json', {})
    for page, byte_digest in result.manifest['review_units'].items():
        if pages is not None and page not in pages:
            continue
        for language in instance.languages:
            key = page + '@' + language
            rows['host-release:' + key] = {'page': page, 'language': language, 'by': by,
                'at': at or datetime.now(UTC).isoformat(), 'digest': byte_digest,
                'safety_digest': digest(result.manifest['safety'])}
    result.check(instance)
    mutate(instance, {instance.path('state') / 'attestations.json': rows})


def recent_unmapped(record, horizon=110):
    years = [int(y) for e in record.get('events', []) for y in re.findall(r'\b(\d{4})\b', str(e.get('date', '')))]
    if not years or max(years) < datetime.now(UTC).year - horizon:
        return False
    mapping = record.get('people', {})
    written = set(mapping) if isinstance(mapping, dict) else set()
    written.update(s.get('written') for s in record.get('subjects', []) if isinstance(s, dict) and s.get('person'))
    rows = [record['person']] if isinstance(record.get('person'), dict) else []
    rows += [r for r in record.get('relatives', []) if isinstance(r, dict)]
    return any(' '.join(filter(None, [r.get('given', r.get('name', '')), r.get('surname', '')])) not in written
               and not r.get('id') for r in rows)


@boundary('diagnostic')
def worklist(instance, feed=None):
    from familiar.checks.engine import _known_people, life_status, load
    from familiar.feeds import service

    from .publication import project
    from .subjects import closure, normalized
    known, privacy = _known_people(instance), load(instance.path('privacy'), {})
    out = []
    def cue(page, kind, **details):
        out.append(dict(page=page, kind=kind, blind_spots=BLIND_SPOTS, **details))
    for folder in service.folders(instance, feed):
        meta = load(folder / 'feed.json', {})
        aliases = known | {k: known[v] for k, v in meta.get('persons', {}).items() if v in known}
        docs, pics = load(folder / 'documents.json', {}), load(folder / 'pictures.json', {})
        built, _ = service._materialize(instance, folder)
        chapters = load(folder / 'chapters.json', [])
        terms = _safety_inputs(instance, set()).get('closed_topics', [])
        for name in _safety_inputs(instance, set())['lists']:
            path = instance._inside(name)
            import tomllib
            data = tomllib.loads(path.read_text(encoding='utf-8')) if path.suffix == '.toml' else load(path, {})
            terms += data.get('terms', data.get('closed_topics', []))
        for raw, shown in [(dict(meta, id='__feed__', chapters=[]), {k: v for k, v in built.items() if k != 'chapters'}), *zip(chapters, built['chapters'], strict=True)]:
            page = 'feed:' + folder.name + '/' + raw['id']
            resolved = closure(instance, raw, shape='feed' if raw['id'] == '__feed__' else 'chapter', documents=docs, pictures=pics, people=aliases)
            cue(page, 'subject-closure', people=sorted(resolved.people))
            for pid in sorted(resolved.people):
                if life_status(known[pid], privacy) == 'unknown':
                    cue(page, 'unknown-life', person=pid)
            for n, pic in enumerate(resolved.images):
                cue(page, 'picture', index=n, asset=pic.get('asset'), subjects=pic.get('subjects', []))
            surfaces = []
            project(shown, 'feed' if raw['id'] == '__feed__' else 'chapter', instance.languages, surfaces)
            text = normalized(html.unescape('\n'.join(t for _, t in surfaces)))
            records_text = json.dumps(list(resolved.records.values()), ensure_ascii=False)
            for record in resolved.records.values():
                rows = [record['person']] if isinstance(record.get('person'), dict) else []
                rows += record.get('relatives', [])
                records_text += '\n'.join(' '.join(filter(None, [r.get('given', r.get('name', '')), r.get('surname', '')])) for r in rows if isinstance(r, dict))
            for pid, person in known.items():
                names = [person.get('name', '')] + [n.get('display', '') for n in person.get('names', [])]
                if any(name and name.casefold() in (text + records_text).casefold() for name in names):
                    cue(page, 'name-match', person=pid)
            for term in terms:
                word = term.get('term') if isinstance(term, dict) else term
                if word and re.search(r'(?<!\w)' + re.escape(normalized(html.unescape(word))) + r'(?!\w)', text, re.IGNORECASE):
                    cue(page, 'restricted-term', term=word)
            for rid, record in resolved.records.items():
                if recent_unmapped(record):
                    cue(page, 'recent-unmapped-name', record=rid)
    return out
