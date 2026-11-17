# START_MODULE_CONTRACT: MOD-TREE-BUILDER
# PURPOSE: Build the evidence graph exclusively from the declared family instance inputs.
# PRD_REF: docs/PRD.md#TRUST
# INVARIANTS:
# - package languages and presentation come from instance metadata [review: engine lead]
# - an isolated snapshot and an empty family need no research files [review: engine lead]
# - consumers may enrich cards before one identity pass [review: engine lead]
# - the private working view retains living data beside unfinished publications [review: engine lead]
# - cheap normalization is recomputed before global identity and relationship checks; it requires no per-person cache files [review: engine lead]
# - no working or reader graph is returned when a contribution was rejected [review: engine lead]
# - one reference index includes active people and resolves every merged id to its successor [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (declared reader surfaces and default-deny policy)
# - MOD-FAMILY-WRITER (the sole filesystem and generation boundary)
# - docs/PRD.md#INSTANCE
# - MOD-TREE-LIFE (independent participant and post-identity assessment)
# - MOD-INSTANCE-RESEARCH-FORMS (evidence container)
# - MOD-TREE-CONTRIBUTIONS (declaration owner paths)
# - MOD-TREE-SURNAMES (reversible clan display after identity resolution)
# :END_MODULE_CONTRACT
import copy
import json

from .identities import _apply_identities


def read_json(path, default=None):
    from familiar.instance.subjects import normalized
    return normalized(json.loads(path.read_text(encoding="utf-8-sig"))) if path.exists() else default


def people_index(graph):
    """Working people, including immutable references to explicitly merged cards."""
    people = graph['people']
    return people | {alias: people[target] for alias, target in graph.get('identityAliases', {}).items()}


def _snapshot_graph(instance, raw, *, apply_identity=True):
    """Canonical attributed snapshots retain names/events while adapting UI keys."""
    if not isinstance(raw, dict):
        raise TypeError('snapshot must use the people[] object form')
    people = {}
    for person in raw.get('people', []):
        p = copy.deepcopy(person)
        p['name'] = p.get('name') or next((n.get('display') or ' '.join(filter(None, [n.get('given'), n.get('patronymic'), n.get('surname')]))
                          for n in p.get('names', []) if n), '')
        p.setdefault('facts', [])
        for event in p.get('events', []):
            event.setdefault('tag', {'birth': 'BIRT', 'death': 'DEAT', 'marriage': 'MARR'}.get(event.get('type'), event.get('type', '')))
        people[p['id']] = p
    from familiar.instance.research_forms import require_container
    evidence = require_container(instance.path('evidence'), read_json(instance.path('evidence'), {}), form='evidence')
    sources = {s['id']: s for s in evidence.get('sources', [])}
    edges, associations = [], []
    for edge in evidence.get('edges', []):
        e = copy.deepcopy(edge)
        if e.get('type') == 'parent':
            e.update(parent=e['from'], child=e['to'])
            e.setdefault('status', {'same': 'verified', 'probable': 'hypothesis', 'possible': 'hypothesis'}.get(e.get('confidence'), 'hypothesis'))
            edges.append(e)
        elif 'child' in e and 'parent' in e:
            edges.append(e)
        else:
            associations.append(e)
    graph = {'people': people, 'sources': sources, 'edges': edges, 'associations': evidence.get('associations', associations), 'research': {}}
    for key in ('root', 'cardStatuses'):
        if key in evidence: graph[key] = copy.deepcopy(evidence[key])
    if raw.get('identityAliases'): graph['identityAliases'] = copy.deepcopy(raw['identityAliases'])
    graph['families'] = read_json(instance.path('tree_snapshot') / 'families.json', {'families': []})['families']
    if not evidence.get('edges'):
        for family in graph['families']:
            for child in family.get('children', []):
                for role in ('husband', 'wife'):
                    parent = family.get(role)
                    if child in people and parent in people:
                        edges.append({'child': child, 'parent': parent, 'type': 'parent',
                                      'from': parent, 'to': child, 'status': family.get('status', 'export'),
                                      'sources': family.get('provenance', []),
                                      **({k: family[k] for k in ('derived', 'basis')} if family.get('derived') is True else {})})
    # Existing snapshot relationships must exist before a contribution can decide them.
    from familiar.tree.contributions import _merge_contributions
    _merge_contributions(instance.path('contributions'), people, edges, sources, graph['research'], instance.root,
                        languages=instance.languages, families=graph['families'],
                        record_ids={p.stem for p in instance.path('records').rglob('*.json')},
                        evidence_path=instance.path('evidence'))
    return _apply_identities(graph, read_json(instance.path('identity_decisions'), {})) if apply_identity else graph


def _build_pre_identity(instance):
    """Canonical attributed forms, before one explicit identity pass."""
    raw = read_json(instance.path("tree_snapshot") / "people.json", {"people": []})
    if not isinstance(raw, dict) or not isinstance(raw.get('people'), list):
        raise TypeError('snapshot must use the people[] object form')
    graph = _snapshot_graph(instance, raw, apply_identity=False)
    errors = graph['research']['contributions']['errors']
    if errors:
        raise ValueError('Contributions were not applied: ' + '; '.join(
            error['file'] + ': ' + error['error'] for error in errors))
    return graph


def _build(instance, *, enrich=None):
    data = _build_pre_identity(instance)
    if enrich is not None:
        # In-place presentation enrichment is inside the publication snapshot;
        # it never returns an unprojected graph to the external consumer.
        enrich(data)
        from familiar.instance.gate import require_assertions
        require_assertions(data)
    metadata = read_json(instance.path("tree_metadata"), {})
    if metadata.get('root') in data['people']:
        data['root'] = metadata['root']
    from .life import _assess
    result = _assess(instance, _apply_identities(_assess(instance, data), read_json(instance.path("identity_decisions"), {}),
                            labels=metadata.get("labels", {})))
    if metadata.get('narrator'):
        narrator = result.get('identityAliases', {}).get(metadata['narrator'], metadata['narrator'])
        if narrator in result['people']:
            result['narrator'] = narrator
            result['defaultViewer'] = narrator
    from .surnames import apply
    apply(instance, result, metadata)
    return result


from familiar.instance.gate import boundary


@boundary('tree-view')
def build(instance, *, enrich=None, view='reader'):
    """Build a reader projection, or the private full graph with view='working'.

    The callback mutates presentation in place, without writing family files.
    Reader fields remain subject to the declared projection and trust checks.
    A working graph never carries a clean/reviewed publication state.
    """
    if view == 'working':
        from familiar.instance.gate import require_assertions
        from familiar.instance.writer import snapshot
        with snapshot(instance) as (active, inputs):
            graph = _build(active, enrich=enrich)
            require_assertions(graph)
        from familiar.instance.writer import fingerprints
        if inputs != fingerprints(instance):
            raise ValueError('family inputs changed during working tree build')
        return graph
    if view != 'reader':
        raise ValueError('tree view must be working or reader')
    from familiar.instance.gate import publication
    return publication(instance, 'tree', tree_enrich=enrich).data()


@boundary('tree-view')
def save(instance, out, *, view='reader'):
    from familiar.instance.gate import publication
    from familiar.instance.writer import fingerprints, publish, save_working
    if view == 'working':
        before = fingerprints(instance)
        return save_working(instance, out, build(instance, view='working'), before)
    if view != 'reader':
        raise ValueError('tree view must be working or reader')
    publish(instance, out, publication(instance, 'tree'))
