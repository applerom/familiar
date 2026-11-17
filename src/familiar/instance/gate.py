# START_MODULE_CONTRACT: MOD-FAMILY-GATE
# PURPOSE: Separate own-item intake validation from family-wide publication form guarantees.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - public output adapters share the full class-F verdict; private displays validate their selected record inputs [review: engine lead]
# - every engine function that mutates, publishes or reads family data is a registered boundary and serializes only the sealed projection [review: engine lead]
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
from functools import wraps

from familiar.instance.research_forms import CLEAN, PREVIEW

from .research_forms import acceptance_error

BOUNDARIES = {}


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
            checked_output = kind in {'output', 'research', 'tree-view', 'working'}
            if checked_output:
                from .writer import fingerprints
                before = fingerprints(instance)
            working_tree = (kind == 'working' or (kind == 'tree-view' and kwargs.get('view') == 'working') or
                            kwargs.get('host_private') is True or
                            (fn.__name__ == 'publication' and (args[0] if args else kwargs.get('kind')) in {'host', 'correspondence', 'reader-private'}))
            if kind not in {'diagnostic', 'transaction', 'writer', 'consume'} and not working_tree:
                active = getattr(instance, 'instance', instance)
                if not (getattr(active, '_legacy_rules', False) and 'schema_version' not in active.config):
                    require(active)
            if checked_output:
                if before != fingerprints(instance):
                    raise GateBlocked('Family gate blocked: inputs changed during validation')
                result = fn(instance, *args, **kwargs)
                if before != fingerprints(instance):
                    raise GateBlocked('Family gate blocked: inputs changed during output')
                return result
            return fn(instance, *args, **kwargs)
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


def evaluate(instance, registry=None):
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

        from .publication import scan, scan_assets
        asset_errors, asset_seen = [], set()
        try:
            for folder in folders(instance):
                data, details = _materialize(instance, folder)
                result['findings'].extend(dict(certainty='review', rule='UNWEIGHTED', check='unweighted',
                    scope='feed:' + folder.name, chapter_id=None, location=folder.name,
                    mode='advise', exception=None, message=note) for note in details.get('advice', []))
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

    from .publication import _seal, restrict_graph, scan, scan_assets
    from .writer import snapshot

    if tree_enrich is not None and (kind != 'tree' or not callable(tree_enrich)):
        raise ValueError('tree_enrich must be callable and is only supported for tree publications')
    with snapshot(instance) as (active, inputs):
        private = kind == 'reader-private'
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
            from .review import _review_manifest, _review_units
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
            data, reports = [], {}
            for folder in service.folders(active, feed):
                result, _ = service._materialize(active, folder)
                data.append(scan(active, result, 'feed'))
                reports[folder.name] = service._inspect(active, folder)
            for report in reports.values():
                report['trust'] = verdict
                report['output'] = {'state': CLEAN, 'inputs': inputs}
            if active.config.get('family', {}).get('fictional'):
                reports = {'_about': 'Build status of an invented family.', 'fictional': True, **reports}
            files = {name: (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + '\n').encode()
                     for name, value in [('feeds.json', data), ('status.json', reports)]}
        elif kind == 'tree':
            from familiar.tree.builder import _build
            from familiar.tree.canonical import encode
            data = scan(active, restrict_graph(active, _build(active, enrich=tree_enrich)), 'graph')
            scan_assets(active, data)
            files = {'graph.json': encode(data).encode('utf-8')}
        elif kind in {'reader', 'reader-private'}:
            from familiar.reader.assets import catalog, dependencies, used_assets
            from familiar.reader.documents import _local_sources
            from familiar.reader.export import encode, external_links
            from familiar.reader.graph import _assemble
            from familiar.rules.cascade import Registry
            from familiar.rules.roles import method_root
            media = catalog(active)
            graph = _assemble(active, for_review=for_review, host_private=private)
            if private:
                # The display snapshot holds no search journals; the host's own instance supplies the coverage block.
                from familiar.research.coverage_display import attach
                attach(instance, graph)
            pages = _local_sources(active, graph, media, host_private=private)
            allowed = Registry(method_root() / 'rules', active).resolve_setting('media.external_embeds').value
            graph = external_links(graph, allowed)
            graph = scan(active, graph if private else restrict_graph(active, graph), 'graph', host_private=private)
            family = dict(active.config['family'])
            family.setdefault('fictional', False)
            profile = scan(active, {'schema_version': 1, 'family': family, 'data': 'graph.json', 'reader_names': {}}, 'profile')
            used = dependencies(used_assets(graph, {**media, **{key: None for key in pages}}), media, pages)
            files = {'graph.json': encode(graph), 'reader-profile.json': encode(profile),
                     **{key: value for key, value in pages.items() if key in used}}
            for name in sorted(used):
                if name in media:
                    row, source = media[name]
                    from .writer import reader_media
                    files[name] = reader_media(source, row, name)
            from .writer import content_digest
            manifest = {'schema_version': 1, 'family_id': active.id, 'state': 'host-private' if private else CLEAN, 'inputs': inputs,
                        'files': {name: {'sha256': content_digest(value),
                                          **({'id': media[name][0]['id'], 'kind': media[name][0]['kind']} if name in media else {})}
                                  for name, value in sorted(files.items())}}
            files['bundle.json'] = encode(manifest)
            data = manifest
        else:
            raise ValueError('unknown declared publication kind')
        if private:
            review = {'kind': kind, 'state': 'host-private', 'unreviewed': []}
            if for_review:
                from .review import _output_uses, _review_manifest, _review_units
                # Review the exact local projection, using the reader's existing
                # units and binding. Never transfer approval of different bytes.
                review = _review_manifest(active, _review_units(active, 'reader', graph, files),
                                          _output_uses(active, 'reader', graph))
                review.update(kind=kind, feed=None, languages=list(active.languages), state='host-private')
            result = _seal(inputs, files, data, verdict, review)
            result.check(instance)
            return result
        from .review import _output_uses, _review_manifest, _review_units
        content = graph if kind == 'reader' else data
        uses = _output_uses(active, kind, content, feed)
        review = _review_manifest(active, _review_units(active, kind, content, files), uses)
        if kind == 'reader' and not for_review and review['state'] == PREVIEW:
            raise GateBlocked('Unreviewed reader pages: ' + ', '.join(review['unreviewed']))
        if kind == 'reader':
            data['state'] = review['state']
            files['bundle.json'] = encode(data)
        if kind == 'feeds':
            for report in reports.values():
                if isinstance(report, dict):
                    report['output'] = {'state': review['state'], 'unreviewed': review['unreviewed']}
            files['status.json'] = (json.dumps(reports, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + '\n').encode()
        review['kind'] = kind
        review['feed'] = feed
        review['languages'] = list(active.languages)
        result = _seal(inputs, files, data, verdict, review)
        result.check(instance)
        return result
