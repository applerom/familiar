# START_MODULE_CONTRACT: MOD-FAMILY-GATE
# PURPOSE: Separate own-item intake validation from family-wide publication form guarantees.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - draft frames may be read locally and prevent external release of their feeds [test: tests/gate/test_data_guarantees.py::test_draft_frames_stay_home]
# - public output adapters share the full class-F verdict; private displays validate their selected record inputs [review: engine lead]
# - chapter media omissions report the host and reader projections as advice [review: engine lead]
# - delivered feed status contains only public review state and page identifiers [test: tests/gate/test_data_guarantees.py::test_f8_review_binds_exact_bytes]
# - every engine function that mutates, publishes or reads family data is a registered boundary and serializes only the sealed projection [review: engine lead]
# - research lookups (forms, compare, person) are registered boundaries without the family verdict; they publish nothing [review: engine lead]
# - one verdict or one checked call reads fixed inputs: derived reads are shared inside it; the final fingerprint comparison still rejects any change [review: engine lead]
# CHANGES_WITH:
# - MOD-HOST-TEXT (private host views use snapshot and a non-publishable working seal)
# - MOD-RESEARCH-COVERAGE-DISPLAY (the host-private reader graph gets a person coverage block from the host instance)
# - MOD-CHECKS-ENGINE
# - MOD-INSTANCE-VALIDATION
# - MOD-OUTPUT-REVIEW
# - MOD-SUBJECT-CLOSURE
# - docs/reader-export.md (private review material uses current reader units)
# :END_MODULE_CONTRACT
"""The family gate: forms, recursive acceptance, and publication privacy together.

Registered adapters share validation. Reader serialization accepts only declared
projections produced here; the engine writer enforces own-item validation and
checked generation commits. Private transforms do not certify their inputs.
Historical truth and semantic interpretation of prose still require review.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

from familiar.instance.research_forms import CLEAN, PREVIEW

from .research_forms import acceptance_error

BOUNDARIES = {}
QUARANTINE = {}  # family root -> rows the last verdict left waiting; desk build names them, publish counts them
_FIXED = ContextVar('familiar_fixed_inputs', default=None)


@contextmanager
def fixed_inputs():
    """One verdict or one checked call reads fixed inputs: derived reads are computed once.

    Checked calls compare input fingerprints before and after, so a change during the
    scope still fails; writers and transactions never open it.
    """
    if _FIXED.get() is not None:
        yield
        return
    token = _FIXED.set({})
    try:
        yield
    finally:
        _FIXED.reset(token)


def shared(instance, name, produce):
    """produce() once per fixed-inputs scope and family view; callers treat the value as read-only."""
    memo = _FIXED.get()
    if memo is None:
        return produce()
    key = (name, str(instance.root), repr(sorted(instance.host_paths.items())),
           *(bool(getattr(instance, flag, False)) for flag in (
               '_display_scope', '_research_work_scope', '_carry_over_asks', '_immutable_snapshot')))
    if key not in memo:
        memo[key] = produce()
    return memo[key]


class GateBlocked(ValueError):
    pass


def boundary(kind):
    """Register adapters at their definition, and enforce before their body runs."""
    def decorate(fn):
        @wraps(fn)
        def guarded(instance, *args, **kwargs):
            private_display = (kwargs.get('host_private') is True or
                (kind == 'tree-view' and kwargs.get('view') == 'working') or
                (fn.__name__ == 'publication' and (args[0] if args else kwargs.get('kind')) == 'reader-private'))
            if private_display:
                from .writer import display_instance
                instance = display_instance(instance)
            elif kind in {'output', 'research', 'tree-view'} and getattr(instance, '_display_scope', False):
                from .writer import fresh
                instance = fresh(instance)
                instance._display_scope = False  # A private scope cannot narrow a public adapter.
            # Research lookups (forms, compare, person) answer the researcher from what they read and
            # publish nothing: no family-wide verdict, so a half-written record never blocks them.
            checked_output = kind in {'output', 'tree-view', 'working'}
            working_tree = (kind == 'working' or (kind == 'tree-view' and kwargs.get('view') == 'working') or
                            kwargs.get('host_private') is True or
                            (fn.__name__ == 'publication' and (args[0] if args else kwargs.get('kind')) in {'host', 'correspondence', 'reader-private'}))
            gated = kind not in {'diagnostic', 'transaction', 'writer', 'consume', 'research'} and not working_tree

            def verdict():
                active = getattr(instance, 'instance', instance)
                if not (getattr(active, '_legacy_rules', False) and 'schema_version' not in active.config):
                    require(active)
            if not checked_output:
                if gated:
                    verdict()
                return fn(instance, *args, **kwargs)
            from .writer import fingerprints
            with fixed_inputs():
                before = fingerprints(instance)
                if gated:
                    verdict()
                if before != fingerprints(instance):
                    raise GateBlocked('Family gate blocked: inputs changed during validation')
                result = fn(instance, *args, **kwargs)
                if before != fingerprints(instance):
                    raise GateBlocked('Family gate blocked: inputs changed during output')
                return result
        BOUNDARIES[fn.__module__ + '.' + fn.__qualname__] = (kind, guarded)
        return guarded
    return decorate


def assertions(value):
    if isinstance(value, dict):
        if error := acceptance_error(value):
            yield error
        for child in value.values():
            yield from assertions(child)
    elif isinstance(value, list):
        for child in value:
            yield from assertions(child)


def require_assertions(value):
    errors = list(assertions(value))
    if errors:
        raise ValueError('; '.join(errors))


def evaluate(instance, registry=None, *, editorial=False):
    with fixed_inputs():
        return _evaluate(instance, registry, editorial=editorial)


def _evaluate(instance, registry=None, *, editorial=False):
    from familiar.checks.engine import _inspect_family
    from familiar.rules.cascade import Registry
    from familiar.rules.roles import method_root

    from .validation import _forms
    from .writer import fresh
    from familiar.check_policy import decision, finding
    try:
        instance = fresh(instance)
        registry = Registry(method_root() / 'rules', instance)
    except (ValueError, OSError) as exc:
        forms = {'valid': False, 'errors': [{'location': 'configuration', 'message': str(exc), 'weight': 'family-gate'}],
                 'data_files': {}, 'first_chapter_missing': ['resolve validation errors'],
                 'full_cycle_missing': ['resolve validation errors'], 'unverified': []}
        configuration = finding({'certainty': 'finding', 'rule': 'FORMS', 'check': 'family-gate',
                              'scope': 'family', 'chapter_id': None, 'location': 'configuration',
                              'mode': 'block', 'exception': None, 'message': str(exc)}, 'family-gate')
        blocked = configuration['mode'] == 'block'
        return {'valid': not blocked, 'blocked': blocked, 'forms': forms, 'coverage': [],
                'findings': [configuration]}
    forms = _forms(instance)
    QUARANTINE[str(getattr(instance, '_snapshot_source_root', instance.root))] = forms.get('quarantine', [])
    try:
        result = _inspect_family(registry)
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        result = {'findings': [], 'coverage': [], 'blocked': True}
        forms['errors'].append({'location': 'family data', 'message': str(exc), 'weight': 'family-gate'})
    for error in forms['errors']:
        result['findings'].append({'certainty': 'finding', 'rule': 'TRUST-04' if 'accept' in error['message'] else 'FORMS',
            'check': 'family-gate', 'scope': 'family', 'chapter_id': None,
            'location': error['location'], 'mode': 'block', 'exception': None,
            'weight': error.get('weight'), 'message': error['message']})
    for advice in forms.get('advice', []):
        result['findings'].append(dict(advice, certainty='review', rule='UNWEIGHTED', check='unweighted',
                                       scope='family', chapter_id=None, mode='advise', exception=None))
    result['blocked'] = result['blocked'] or bool(forms['errors'])
    result['valid'] = not result['blocked']
    result['forms'] = forms
    if not result['blocked']:
        from familiar.feeds.service import _materialize, folders

        from .narrative import prose_review
        from .publication import media_omissions, scan, scan_assets
        asset_errors, asset_seen = [], set()
        feeds = []
        try:
            for folder in folders(instance):
                data, details = _materialize(instance, folder)
                if editorial:
                    from familiar.feeds.rhythm import advice, measure
                    result['findings'].append(dict(certainty='review', rule='UNWEIGHTED', check='feed-rhythm',
                        scope='feed:' + folder.name, chapter_id=None, location=folder.name,
                        mode='advise', exception=None, message=advice(data, *measure(instance, data, registry))))
                result['findings'].extend(dict(certainty='review', rule='UNWEIGHTED', check='unweighted',
                    scope='feed:' + folder.name, chapter_id=None, location=folder.name,
                    mode='advise', exception=None, message=note) for note in details.get('advice', []))
                result['findings'].extend(dict(certainty='review', rule='TRUST-06', check='narrative-attribution',
                    scope='feed:' + folder.name, chapter_id=None, location=where,
                    mode='advise', exception=None, message=note) for where, note in prose_review(instance, data))
                feeds.append(data)
                projected = scan(instance, data, 'feed')
                scan_assets(instance, projected, errors=asset_errors, seen=asset_seen)
                from familiar.checks.engine import inspect_text
                coverage = next(c for c in result['coverage'] if c['feed'] == folder.name)
                for i, chapter in enumerate(data['chapters']):
                    result['findings'].extend(inspect_text(registry, chapter,
                        f'feed:{folder.name}/chapter:{i}', coverage=coverage))
                result['findings'].extend(inspect_text(registry,
                    {k: v for k, v in data.items() if k != 'chapters'},
                    f'feed:{folder.name}', shape='feed', coverage=coverage))
            # The local desk reads all feeds together. Reuse one host projection
            # for its advice while still validating each public feed separately.
            for row in media_omissions(instance, feeds) if feeds else ():
                result['findings'].append(dict(certainty='review', rule='TRUST-06', check='media-omitted',
                    scope='feed:' + row['feed'], chapter_id=row['chapter'], location=row['field'],
                    mode='advise', exception=None, message=f"{row['view']}: {row['field']} {row['item']} withheld: {row['reason']}. Clarify life status; use a deceased-only public picture, or separate a deceased-only excerpt. Full living documents stay excluded.", omission=row))
        except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
            result['blocked'], result['valid'] = True, False
            message = str(exc)
            rule = next((f'TRUST-{n:02}' for n in range(1, 13) if f'TRUST-{n:02}' in message), 'FORMS')
            result['findings'].append({'certainty': 'finding', 'rule': rule, 'check': 'publication-projection',
                'scope': 'family', 'chapter_id': None, 'location': 'publication', 'mode': 'block',
                'exception': None, 'message': message})
        for error in asset_errors:
            result['blocked'], result['valid'] = True, False
            result['findings'].append({'certainty': 'finding', 'rule': 'FORMS',
                'check': 'publication-projection', 'scope': 'family', 'chapter_id': None,
                'location': error['location'], 'mode': 'block', 'exception': None,
                'message': error['message']})
    result['findings'] = [finding(f, f.get('weight', f['check'])) for f in result['findings']
                          if decision(f.get('weight', f['check'])) != 'delete']
    result['blocked'] = any(f['mode'] == 'block' and f['certainty'] == 'finding' for f in result['findings'])
    result['valid'] = not result['blocked']
    return result


def require(instance):
    try:
        result = evaluate(instance)
    except (ValueError, OSError, TypeError) as exc:
        raise GateBlocked('Family gate blocked: FORMS: ' + str(exc)) from exc
    if result['blocked']:
        raise GateBlocked('Family gate blocked: ' + '; '.join(f"{f['rule']}: {f['message']}" for f in result['findings'] if f['mode'] == 'block' and f['certainty'] == 'finding'))
    return result


@boundary('output')
def publication(instance, kind, feed=None, *, for_review=False, tree_enrich=None,
                host_view='summary', selection=None):
    """Only serializer input factory: closed output kinds, private immutable source copy."""
    import json

    from familiar.feeds import service
    from familiar.feeds.flow import require_finished

    from .publication import PaperWords, _seal, check_public_files, public_references, restrict_graph, scan, scan_assets
    from .review import _output_uses, _review_manifest, _review_units
    from .writer import snapshot

    if tree_enrich is not None and (kind != 'tree' or not callable(tree_enrich)):
        raise ValueError('tree_enrich must be callable and is only supported for tree publications')
    with snapshot(instance) as (active, inputs):
        private = kind == 'reader-private'
        paper_words = PaperWords()
        verdict = {'valid': True, 'state': 'host-private' if private else 'working'} if kind in {'host', 'correspondence', 'reader-private'} else require(active)
        def original_locations(value):
            if isinstance(value, dict):
                return {k: original_locations(v) for k, v in value.items()}
            if isinstance(value, list):
                return [original_locations(v) for v in value]
            if isinstance(value, str):
                return value.replace(str(active.root), str(instance.root))
            return value
        verdict = original_locations(verdict)
        if kind == 'correspondence':
            from .correspondence_view import project
            from .writer import encode
            data = scan(active, project(active), 'correspondence-view')
            result = _seal(inputs, {'correspondence.json': encode(data)}, data, verdict,
                           {'state': 'working', 'kind': 'correspondence'})
            result.check(instance)
            return result
        if kind == 'host':
            from .host_text import _build
            data, source_review, uses = _build(active, host_view, selection, feed)
            data = scan(active, data, 'host-text')
            files = {'host.txt': (data['text'] + '\n').encode('utf-8')}
            review = source_review or _review_manifest(
                active, _review_units(active, 'host', data, files), uses)
            review = dict(review, state='working', kind='host')
            result = _seal(inputs, files, data, verdict, review)
            result.check(instance)
            return result
        elif kind == 'feeds':
            data = []
            for folder in service.folders(active, feed):
                result, _ = service._materialize(active, folder)
                require_finished([result])
                data.append(scan(active, result, 'feed', paper_words=paper_words))
            uses = _output_uses(active, kind, data, feed)
            data = public_references(active, data)
            files = {'feeds.json': (json.dumps(data, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + '\n').encode()}
        elif kind == 'tree':
            from familiar.tree.builder import _build
            from familiar.tree.canonical import encode
            graph = _build(active, enrich=tree_enrich)
            for source in graph['sources'].values():
                source.pop('image', None)  # Only the checked reader document projection writes this field.
            data = scan(active, restrict_graph(active, graph, paper_words=paper_words), 'graph')
            scan_assets(active, data)
            uses = _output_uses(active, kind, data, feed)
            data = public_references(active, data, graph=data)
            files = {'graph.json': encode(data).encode('utf-8')}
        elif kind in {'reader', 'reader-private'}:
            from familiar.reader.assets import catalog, dependencies, used_assets
            from familiar.reader.documents import _local_sources
            from familiar.reader.export import encode, external_links
            from familiar.reader.graph import _assemble, paper_attribution, show_probable_identities
            from familiar.rules.cascade import Registry
            from familiar.rules.roles import method_root
            media = catalog(active)
            graph = _assemble(active, for_review=for_review, host_private=private,
                              paper_words=None if private else paper_words)
            if private:
                # The display snapshot holds no search journals; the host's own instance supplies the coverage block.
                from familiar.research.coverage_display import attach
                attach(instance, graph)
            documents, scan_sources = _local_sources(active, graph, media, host_private=private)
            paper_attribution(graph)
            if private:
                show_probable_identities(graph)
            allowed = Registry(method_root() / 'rules', active).resolve_setting('media.external_embeds').value
            graph = external_links(graph, allowed)
            graph = scan(active, graph, 'graph', host_private=private)
            family = dict(active.config['family'])
            family.setdefault('fictional', False)
            profile = scan(active, {'schema_version': 1, 'family': family, 'data': 'graph.json', 'reader_names': {}}, 'profile')
            # An older desk can register the very page we now generate. Its
            # references should resolve to the newly checked reading.
            for name in media.keys() & documents.keys():
                legacy = media[name][0]
                owner = graph['sources'].get(legacy.get('source_id'), {})
                if legacy.get('kind') == 'record-page' and owner.get('asset') == '/' + name:
                    del media[name]
            if clash := sorted(media.keys() & documents.keys()):
                raise ValueError(f'{len(clash)} registered media rows in media/manifest.json export a document page '
                                 f'the engine now generates ({", ".join(clash[:3])}{", ..." if len(clash) > 3 else ""}); '
                                 'run `familiar instance upgrade` or remove those rows (the files stay)')
            faces = {}
            if not private:
                from .gallery import external_faces, photographs
                from .writer import reader_media

                uses = _output_uses(active, kind, graph, feed)
                graph, faces, originals = external_faces(
                    graph, photographs(active), lambda name: reader_media(media[name][1], media[name][0], name))
                media = {name: item for name, item in media.items() if name not in originals}
                if faces.keys() & (media.keys() | documents.keys()):
                    raise ValueError('A face rendition takes a registered reader asset name')
                documents.update(faces)
            used = dependencies(used_assets(graph, media.keys() | documents.keys()), media, documents)
            if not private:
                graph = public_references(active, graph, graph=graph)
            files = {'graph.json': encode(graph), 'reader-profile.json': encode(profile),
                     **{key: value for key, value in documents.items() if key in used}}
            for name in sorted(used):
                if name in media:
                    row, source = media[name]
                    from .writer import reader_media
                    files[name] = reader_media(source, row, name)
            from .writer import content_digest
            manifest = {'schema_version': 1, 'family_id': active.id, 'state': 'host-private' if private else CLEAN,
                        'files': {name: {'sha256': content_digest(value),
                                          **({'source_sha256': scan_sources[name]} if name in scan_sources else {}),
                                          **({'id': media[name][0]['id'], 'kind': media[name][0]['kind']} if name in media else {})}
                                  for name, value in sorted(files.items())}}
            if private:
                manifest['inputs'] = inputs
            files['bundle.json'] = encode(manifest)
            data = manifest
        else:
            raise ValueError('unknown declared publication kind')
        if private:
            review = {'kind': kind, 'state': 'host-private', 'unreviewed': []}
            if for_review:
                # Review the exact local projection, using the reader's existing
                # units and binding. Never transfer approval of different bytes.
                review = _review_manifest(active, _review_units(active, 'reader', graph, files),
                                          _output_uses(active, 'reader', graph))
                review.update(kind=kind, feed=None, languages=list(active.languages), state='host-private')
            result = _seal(inputs, files, data, verdict, review)
            result.check(instance)
            return result
        content = graph if kind == 'reader' else data
        review = _review_manifest(active, _review_units(active, kind, content, files), uses)
        if kind == 'reader' and not for_review and review['state'] == PREVIEW:
            raise GateBlocked('Unreviewed reader pages: ' + ', '.join(review['unreviewed']))
        if kind == 'reader':
            data['state'] = review['state']
            files['bundle.json'] = encode(data)
        if kind == 'feeds':
            reports = {item['id']: {'output': {'state': review['state'], 'unreviewed': [
                page for page in review['unreviewed'] if page.startswith('feed:' + item['id'] + '/')]}}
                for item in data}
            if active.config.get('family', {}).get('fictional'):
                reports = {'_about': 'Build status of an invented family.', 'fictional': True, **reports}
            files['status.json'] = (json.dumps(reports, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + '\n').encode()
        check_public_files(active, files, paper_words)
        review['kind'] = kind
        review['feed'] = feed
        review['languages'] = list(active.languages)
        result = _seal(inputs, files, data, verdict, review)
        result.check(instance)
        return result
