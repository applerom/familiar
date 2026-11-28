# START_MODULE_CONTRACT: MOD-CHECKS-ENGINE
# PURPOSE: Keep mandatory feed data findings separate from scoped, dismissible invitations to read the text.
# PRD_REF: docs/PRD.md#PIPELINE
# INVARIANTS:
# - chapter fact references resolve to corpus files [review: engine lead]
# - typed images find parked files without demanding an open family-photo licence [review: engine lead]
# - pristine fictional feeds have no trust findings and each trust check detects a broken copy [review: engine lead]
# - checks cannot read settings absent from their rule's reads declaration [review: engine lead]
# - off modes disappear and recorded exceptions remain visible [review: engine lead]
# - safe media omissions advise while invalid photo pairs and conflicting subjects refuse output [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (declared reader surfaces and default-deny policy)
# - MOD-FAMILY-WRITER (the sole filesystem and generation boundary)
# - MOD-RULES-CASCADE
# - MOD-INSTANCE-MODEL
# - MOD-TREE-BUILDER (built people and identity aliases)
# - MOD-INSTANCE-RESEARCH-FORMS (file container diagnostics)
# :END_MODULE_CONTRACT
from __future__ import annotations

import json
import copy
import re
import tomllib



def load(path, default=None):
    from familiar.instance.research_forms import require_container
    from familiar.instance.subjects import normalized
    try:
        return require_container(path, normalized(json.loads(path.read_text(encoding='utf-8')))) if path.exists() else default
    except json.JSONDecodeError as exc:
        raise ValueError(f'{path}:{exc.lineno}:{exc.colno}: {exc.msg}') from exc


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


class Context:
    def __init__(self, registry, rule, scope):
        self.registry, self.rule, self.scope = registry, rule, scope

    def setting(self, key):
        if key not in self.rule['reads']:
            raise ValueError(f"{self.rule['id']}: undeclared setting read {key}")
        return self.registry.resolve_setting(key, self.scope).value


def generated(pic):
    return (pic.get('generated') is True or pic.get('kind') in
            {'ours-drawing', 'reconstruction', 'generated', 'generated-reconstruction', 'photo-restoration'} or
            (pic.get('kind') != 'photo-treatment' and '/gen/' in pic.get('asset', '')))


def record_paths(instance):
    from familiar.instance.gate import shared
    from familiar.instance.subjects import normalized
    def records():
        return {normalized(p.stem): p for p in instance.path('records').rglob('*.json')}
    return shared(instance, 'record-paths', records)


def record_path(instance, value):
    # Only stable record IDs, never path aliases or arbitrary family JSON.
    from familiar.instance.subjects import normalized
    missing = instance.path('records') / '__unresolved_record__'
    if not isinstance(value, str) or any(c in value for c in '/\\'):
        return missing
    return record_paths(instance).get(normalized(value), missing)


def media_exists(instance, asset):
    return instance.media_file(asset) is not None


def life_status(person, privacy):
    ident = person.get('id')
    if ident in {p if isinstance(p, str) else p['id'] for p in privacy.get('living', [])}:
        return 'living'
    if person.get('life_assessment'):
        return person['life_assessment']['status']
    from familiar.tree.life import decision_scope, explicit_alive, recorded
    if explicit_alive(person):
        return 'living'
    decision = next((row for row in reversed(privacy.get('life_decisions', []))
                     if row.get('person') == ident and not row.get('revoked')
                     and decision_scope(row) == 'everywhere'), None)
    if decision:
        return decision['status']
    if person.get('living') is False and person.get('life_origin') != 'gedcom':
        return 'dead'
    events = person.get('events', [])
    if any((e.get('type') == 'death' or e.get('tag') == 'DEAT') and recorded(e) for e in events):
        return 'dead'
    # Graph facts carry localized labels, so never guess a date's meaning from prose.
    return 'unknown'


def _known_people(instance, *, family_display=False):
    # Only a writer-owned immutable snapshot permits this in-memory index.
    from familiar.tree.builder import people_index, read_graph
    immutable = getattr(instance, '_immutable_snapshot', False)
    cached = getattr(instance, '_known_cache', {}) if immutable else {}
    if family_display in cached:
        return cached[family_display]
    from familiar.instance.gate import shared
    # References in immutable imported records remain usable after an explicit
    # merge; every lookup resolves to the active card's canonical id.
    result = shared(instance, ('known-people', family_display),
                    lambda: people_index(read_graph(instance, family_display=family_display)))
    if immutable:
        cached[family_display] = result
        instance._known_cache = cached
    return result


def record_subjects(record, known):
    """Compatibility helper: only supplied IDs establish structured subjects."""
    from familiar.instance.subjects import explicit_subjects
    return explicit_subjects(record)


def _inspect(ctx, chapter, documents, pictures, instance, people):
    """Yield (location, explanation); structural checks only, no language heuristics."""
    check = ctx.rule['check'].removeprefix('check:')
    refs = list(chapter.get('records') or [])
    for extra in chapter.get('extras') or []:
        refs.extend(extra.get('records') or [])
    pics = []
    for key in [chapter.get('picture'), *(chapter.get('figures') or [])]:
        if isinstance(key, dict):
            pics.append(key)
        elif key and key in pictures:
            pics.append(pictures[key])
    for extra in chapter.get('extras') or []:
        key = extra.get('picture')
        if isinstance(key, dict):
            pics.append(key)
        elif key in pictures:
            pics.append(pictures[key])
    def variants(pic):
        from familiar.instance.publication import SCHEMAS
        from familiar.instance.subjects import photo_pair
        pic = copy.deepcopy(pic)
        photo_pair(instance, pic)
        yield pic
        for key, field in SCHEMAS['image'].items():
            child = pic.get(key)
            if field.shape == 'image' and isinstance(child, dict):
                yield from variants(child)
    pics = [item for pic in pics for item in variants(pic)]
    if check == 'document-reference-resolves':
        for n, ref in enumerate(refs):
            doc = documents.get(ref.get('doc'))
            if not isinstance(doc, dict):
                yield f'records[{n}]', 'Document reference has no entry in documents.json.'
                continue
            record = doc.get('record')
            if not record:
                yield f'records[{n}]', 'Document/cut-out has no corpus record reference; existence is unverified.'
            else:
                path = record_path(instance, record)
                allowed = path.is_relative_to(instance.root) or path.is_relative_to(instance.path('records'))
                if not allowed or not path.is_file():
                    yield f'records[{n}]', 'Referenced corpus record does not exist locally.'
                elif (data := load(path, {})).get('kind') == 'index-entry' and not data.get('saved_result'):
                    yield f'records[{n}].saved_result', 'Index entry has no saved result; evidence is a locator only.'
            snippets = doc.get('snippets', [])
            base = ref.get('index_base', doc.get('index_base', 1))
            if type(base) is not int or base not in (0, 1):
                yield f'records[{n}].index_base', 'Cut-out index base must be explicitly zero or one.'
                continue
            for pick in ref.get('pick', []):
                if type(pick) is not int or not base <= pick < len(snippets) + base:
                    yield f'records[{n}].pick', 'Selected cut-out index is outside the document.'
        for n, fact in enumerate(chapter.get('facts') or []):
            if isinstance(fact, dict) and fact.get('record'):
                value = fact['record']
                doc = documents.get(value)
                value = doc.get('record') if isinstance(doc, dict) else value
                path = record_path(instance, value) if isinstance(value, str) else None
                if path is None or not path.is_file() or not (path.is_relative_to(instance.root) or path.is_relative_to(instance.path('records'))):
                    yield f'facts[{n}].record', 'Fact record reference does not resolve to a local corpus record.'
    elif check == 'reader-surface':
        for n, ref in enumerate(refs):
            doc = documents.get(ref.get('doc'), {})
            path = record_path(instance, doc.get('record', '__missing__'))
            if not path.is_relative_to(instance.root) and not path.is_relative_to(instance.path('records')):
                continue
            record = load(path, {}) if path.is_file() else {}
            for snippet in doc.get('snippets', []):
                if 'field' in snippet and record:
                    field = snippet['field']
                    expected = str(record.get('fields', {}).get(field, ''))
                    if snippet.get('read') not in (expected, f'{field}: {expected}'):
                        yield f'records[{n}]', 'Cut-out reading differs from the literal corpus field.'
                if not snippet.get('read', '').strip():
                    yield f'records[{n}]', 'Cut-out has no literal reading.'
    elif check == 'living-protected':
        from .privacy import _violations
        yield from _violations(chapter, refs, pics, documents, instance, people, pictures)
    elif check == 'generated-not-portrait':
        for pic in pics:
            if generated(pic):
                if pic.get('role') in {'portrait', 'document'} or pic.get('is_portrait'):
                    yield 'picture', 'A reconstruction is presented as a portrait or document.'
                marker = pic.get('reconstruction') is True
                if not marker:
                    yield 'picture', 'Generated image lacks explicit reconstruction metadata/disclosure.'
        for ref in refs:
            doc = documents.get(ref.get('doc'), {})
            if generated(doc):
                yield 'records', 'Generated image is placed among documents.'
    elif check == 'local-and-licensed':
        ctx.setting('media.external_embeds')  # documents/pictures never qualify as embeds
        for n, item in enumerate([*(documents.get(r.get('doc'), {}) for r in refs), *pics]):
            for key in ('asset', 'full'):
                asset = item.get(key)
                if asset:
                    if re.match(r'^(?:https?:)?//', asset):
                        yield f'media[{n}].{key}', 'Document or picture is hot-linked.'
                    else:
                        if not media_exists(instance, asset):
                            yield f'media[{n}].{key}', 'Local media file is missing.'
            for snippet in item.get('snippets', []):
                asset = snippet.get('asset')
                if asset and (re.match(r'^(?:https?:)?//', asset) or
                              not media_exists(instance, asset)):
                    yield f'media[{n}]', 'Cut-out is external or its local file is missing.'
            if item in pics and item.get('kind') == 'family-photograph':
                from familiar.instance.archive import photograph_rights
                rights = photograph_rights(instance, item)
                if not rights or not rights.get('holder') or not rights.get('permissions', {}).get('family_app'):
                    yield f'media[{n}]', 'Family photograph needs a holder and permission for the family app.'
            if item in pics and item.get('kind') == 'document-scan' and (not item.get('record') or not record_path(instance, item['record']).is_file()):
                yield f'media[{n}]', 'Document scan needs a corpus record reference.'


CHECKS = {'document-reference-resolves', 'reader-surface', 'living-protected',
          'generated-not-portrait', 'local-and-licensed'}


def inspect_text(registry, chapter, scope, *, shape='chapter', coverage=None):
    """Compatibility entry point: prose and presentation are accepted by a reader."""
    if coverage is not None:
        coverage['checks_skipped']['text-form'] = 'Text and presentation lint was removed; read the page manually.'
    return []


def _inspect_family(registry, feed_ids=None):
    instance = registry.instance
    known = _known_people(instance)
    findings, coverage = [], []
    for folder in sorted(instance.path('feeds').glob('*')):
        if not (folder / 'feed.json').is_file() or (feed_ids and folder.name not in feed_ids):
            continue
        feed = load(folder / 'feed.json')
        documents = load(folder / 'documents.json', {})
        pictures = load(folder / 'pictures.json', {})
        people = dict(known) | {s: known.get(p, {'id': p}) for s, p in feed.get('persons', {}).items()}
        chapters = load(folder / 'chapters.json', [])
        coverage.append({'feed': folder.name, 'chapters': len(chapters),
                         'people_resolved': sum(p in known for p in feed.get('persons', {}).values()),
                         'people_declared': len(people),
                         'privacy_present': instance.path('privacy').is_file(),
                         'privacy_list_configured': bool(registry.resolve_setting(
                             'privacy.closed_topics_file', f'feed:{folder.name}').value),
                         'checks_run': 0, 'checks_skipped': {}})
        # Feed cover and generation-strip people participate in the same checks.
        cover = pictures.get(feed.get('cover'))
        if isinstance(cover, dict):
            chapters = [*chapters, {'id': '__cover__', 'title': feed.get('title', ''),
                                    'text': feed.get('lead', ''), 'picture': cover,
                                    'people': feed.get('people', []), 'more': 'Cover'}]
        for i, chapter in enumerate(chapters):
            scope = f'feed:{folder.name}/chapter:{i}'
            for rule in registry.rules.values():
                if not isinstance(rule['check'], str) or rule['check'].removeprefix('check:') not in CHECKS:
                    continue
                mode = registry.rule_mode(rule['id'], scope)
                if mode.value == 'off' and mode.layer != 'exception':
                    coverage[-1]['checks_skipped'][rule['id']] = 'Rule mode is off.'
                    continue
                coverage[-1]['checks_run'] += 1
                ctx = Context(registry, rule, scope)
                for location, message in _inspect(ctx, chapter, documents, pictures, instance, people):
                    signal = (rule['kind'] != 'trust' or location.endswith(('unknown', 'subjects-unknown', '.omitted')) or
                              rule['check'].removeprefix('check:') == 'closed-topics-and-politics')
                    exception = (registry.text_exception(rule['id'], scope)
                                 if rule['check'] == 'check:closed-topics-and-politics'
                                 else mode.chain[-1].get('exception'))
                    findings.append({'certainty': 'review' if signal else 'finding', 'rule': rule['id'], 'check': rule['check'], 'scope': scope,
                                     'chapter_id': chapter.get('id'), 'location': location,
                                     'mode': mode.value, 'message': message,
                                     'exception': exception})
    if feed_ids and set(feed_ids) - {c['feed'] for c in coverage}:
        raise ValueError('Requested feed does not exist')
    unique, life = [], {}
    for finding in findings:
        if finding['location'].startswith('people[') and finding['location'].endswith('].unknown'):
            key = finding['location']
            if key in life:
                life[key]['chapters'].append({'scope': finding['scope'], 'id': finding['chapter_id']})
                continue
            finding['chapters'] = [{'scope': finding['scope'], 'id': finding['chapter_id']}]
            life[key] = finding
        unique.append(finding)
    findings = unique
    from familiar.check_policy import decision, finding
    findings = [finding(f, f['check']) for f in findings if decision(f['check']) != 'delete']
    return {'findings': findings, 'coverage': coverage,
            'blocked': any(f['mode'] == 'block' and f['certainty'] == 'finding' for f in findings)}


from familiar.instance.gate import boundary


@boundary('diagnostic')
def run(registry, feed_ids=None):
    from familiar.instance.gate import evaluate
    # Validation is family-wide even when the caller selects one output feed.
    instance = getattr(registry, 'instance', registry)
    if feed_ids and any(not (instance.path('feeds') / f / 'feed.json').is_file() for f in feed_ids):
        raise ValueError('Requested feed does not exist')
    return evaluate(instance, registry)
