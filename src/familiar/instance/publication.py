# START_MODULE_CONTRACT: MOD-PUBLICATION
# PURPOSE: Declare reader fields and seal distinct public and non-publishable host-private projections.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - draft frames and photographs with unnamed faces have no public reader path [review: engine lead]
# - publication asset failures retain each unique URL across feeds [review: engine lead]
# - both reader modes exclude protected documents and their record-linked card details [review: engine lead]
# - photo treatments inherit original privacy [review: engine lead]
# - living name parts inferred by researchers are omitted from canonical names; reported kin wording remains permissible kinship [review: engine lead]
# - the delivered public graph has only bundle-local references for protected people and closed sources [test: tests/gate/test_data_guarantees.py::test_life_decision_scope]
# - the person's `coverage` (where it was looked for) and `amendments` (what was told beside what we propose) are declared for the host-private reader only and are dropped from every public projection [review: engine lead]
# - undeclared nested fields have no publication path [test: tests/gate/test_data_guarantees.py::test_f5_undeclared_reader_fields_stay_private]
# - declared strings remain literal NFC text; only restricted-list data shape is checked, not text style [review: engine lead]
# - spouse union weights reach the reader unchanged [review: engine lead]
# - card serialization runs in memory; its declared fields and complete privacy checks do not depend on cache entries [review: engine lead]
# - correspondence aims and migrated letters are storage-only; the ranked owner seal declares its rendered fields [review: engine lead]
# CHANGES_WITH:
# - MOD-HOST-LANGUAGE (declared host text and private subject references)
# - MOD-TREE-LIFE (effective reader life classification replaces imported flags)
# - MOD-FAMILY-GATE
# - MOD-FAMILY-WRITER
# - MOD-SUBJECT-CLOSURE
# - MOD-NARRATIVE-DISCLOSURE (public narrative projection)
# - MOD-TREE-SURNAMES (clan display is applied after editorial name patches)
# - docs/PRD.md#FORMS (reader card surface dictionary and disclosure policies)
# - docs/gate.md
# :END_MODULE_CONTRACT
import copy
import hashlib
import json
import re
import tomllib
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    shape: object = 'text'
    policy: str = 'always'


def fields(names, shape='text', policy='always'):
    return {key: Field(shape, policy) for key in names.split()}


# text is a scalar or a language row; scalar has no reader prose; refs are IDs.
# Lists have one member declaration; ('map', schema) means a keyed collection.
SCHEMAS = {}
SCHEMAS['name'] = fields('given patronymic surname display type') | fields('provenance', ['reference']) | fields('source_text', ['text']) | fields('status lang', 'scalar')
SCHEMAS['name-part-inference'] = fields('basis') | fields('provenance', ['reference'])
SCHEMAS['inferred-name-parts'] = fields('given patronymic surname', 'name-part-inference')
SCHEMAS['name']['inferred_parts'] = Field('inferred-name-parts')
SCHEMAS['event'] = fields('type tag date place value note text place_text cause') | fields('provenance sources', ['reference']) | fields('source_text', ['text']) | fields('open_question status', 'scalar')
SCHEMAS['note'] = fields('text plain') | fields('provenance', ['reference'])
SCHEMAS['fact'] = fields('text label basis decision') | fields('record eventKey', 'reference') | fields('status accepted weight confidence derived testimony', 'scalar') | fields('sources', ['reference'])
SCHEMAS['fact'] |= fields('uncertainty eventType detailOnly', 'scalar')
SCHEMAS['snippet'] = fields('asset', 'reference') | fields('field read')
SCHEMAS['document'] = fields('kind caption source where read title field') | fields('asset full record', 'reference') | fields('fictional image_seen kids', 'scalar') | fields('subjects excerpt', ['reference']) | fields('parts snippets', ['snippet'])
SCHEMAS['image'] = fields('caption alt title description source credit holder license url disclosure') | fields('asset full record', 'reference') | fields('generated kind role is_portrait reconstruction subject_living subject_child fictional', 'scalar') | fields('subjects', ['reference']) | fields('orig ours', 'image')
SCHEMAS['restoration-comparison'] = fields('attempts chosen_attempt reduced_width_px blur_radius_px mean_absolute_error', 'scalar')
SCHEMAS['restoration-recipe'] = fields('model date prompt original_sha256 sha256') | fields('original_asset', 'reference') | fields('version', 'scalar') | fields('invented', ['text']) | fields('crop', ['scalar']) | fields('comparison', 'restoration-comparison')
SCHEMAS['restoration-version'] = fields('id', 'scalar') | fields('asset', 'reference') | fields('caption disclosure label') | fields('recipe', 'restoration-recipe')
SCHEMAS['image'] |= fields('id primary unidentified_people', 'scalar') | fields('versions', ['restoration-version'])
SCHEMAS['link'] = fields('label title text') | fields('url kind', 'scalar')
SCHEMAS['place'] = fields('name note') | fields('url', 'scalar')
SCHEMAS['variant'] = fields('title text more') | fields('version', 'scalar')
SCHEMAS['kids'] = fields('title text')
SCHEMAS['hardship'] = fields('kind description') | fields('people', ['reference'])
SCHEMAS['flow'] = fields('after record figure', 'scalar')
SCHEMAS['flow']['placeholder'] = Field('placeholder')
SCHEMAS['placeholder'] = fields('kind', 'scalar') | fields('ratio', ['scalar']) | fields('says')
SCHEMAS['node'] = fields('name year') | fields('id', 'reference')
SCHEMAS['small-tree'] = fields('parents children', ['node']) | fields('highlight', ['reference'])
SCHEMAS['clan-family'] = fields('head spouse', 'reference') | fields('kids', ['reference'])
SCHEMAS['clan'] = fields('parents', ['reference']) | fields('families', ['clan-family'])
SCHEMAS['gen-position'] = fields('at', ['reference']) | fields('who where')
SCHEMAS['gen'] = fields('name years kids') | fields('ids', ['reference'])
SCHEMAS['part'] = fields('title text name') | fields('id', 'reference') | fields('number', 'scalar')
SCHEMAS['extra'] = fields('title text more kids') | fields('picture', 'image') | fields('records', ['document'])
SCHEMAS['chapter'] = fields('title text more ask text_kids year') | fields('id', 'reference') | fields('kidsRecords kidsSelection', 'scalar') | fields('people', ['reference']) | fields('picture', 'image') | fields('figures', ['image']) | fields('records', ['document']) | fields('facts', ['fact']) | fields('variants', ['variant']) | fields('places', ['place']) | fields('extras', ['extra']) | fields('links', ['link']) | fields('kids', 'kids') | fields('part', 'part') | fields('flow', ['flow']) | fields('clan', 'clan') | fields('tree', 'small-tree') | fields('gen', 'gen-position')
SCHEMAS['spot'] = fields('label text kids find') | fields('x y w h', 'scalar')
SCHEMAS['pano'] = fields('asset', 'reference') | fields('title enter') | fields('yaw pitch', 'scalar') | fields('spots', ['spot'])
SCHEMAS['choice'] = fields('text outcome icon gain')
SCHEMAS['draw'] = fields('low high button stampLow stampHigh') | fields('from to cut', 'scalar')
SCHEMAS['game-step'] = fields('q') | fields('choices', ['choice']) | fields('draw', 'draw')
SCHEMAS['game-truth'] = fields('text') | fields('record', 'reference')
SCHEMAS['route-point'] = fields('x y', 'scalar') | fields('label')
SCHEMAS['game-route'] = fields('asset', 'reference') | fields('points', ['route-point'])
SCHEMAS['game'] = (fields('title intro kids reward') | fields('steps', ['game-step'])
                   | fields('truth', 'game-truth') | fields('route', 'game-route'))
SCHEMAS['image'] |= fields('spots', ['spot']) | fields('pano', 'pano')
SCHEMAS['chapter']['game'] = Field('game')
SCHEMAS['flow']['do'] = Field('activity')
SCHEMAS['activity'] = fields('kind key', 'scalar') | fields('game', 'game') | fields('picture', 'image')
SCHEMAS['world-person'] = fields('id person_id', 'reference') | fields('name kin') | fields('card_status', 'scalar')
SCHEMAS['world-home'] = fields('id', 'reference') | fields('place') | fields('lat lon group', 'scalar')
SCHEMAS['world-chapter'] = fields('feed id', 'reference')
SCHEMAS['world-story'] = fields('title text more evidence') | fields('paragraphs', ('map', ['text']))
SCHEMAS['world-place'] = SCHEMAS['world-home'] | fields('people', ['reference']) | fields('years interest evidence') | fields('km_from_home regional uncertain', 'scalar') | fields('chapter', 'world-chapter') | fields('story', 'world-story')
SCHEMAS['world-path'] = fields('id person', 'reference') | fields('stops', ['reference']) | fields('years') | fields('group uncertain', 'scalar')
SCHEMAS['world'] = fields('schema_version', 'scalar') | fields('homes', ['world-home']) | fields('people', ('map', 'world-person')) | fields('places', ['world-place']) | fields('paths', ['world-path']) | fields('unlocated', ['world-person'])
SCHEMAS['names'] = fields('short', 'text')
SCHEMAS['chapter']['hardships'] = Field(['hardship'])
SCHEMAS['feed'] = fields('title lead period line') | fields('id cover', 'reference') | fields('people', ['reference']) | fields('gens', ['gen']) | fields('chapters', ['chapter']) | fields('names', ('map', 'name-row'))
SCHEMAS['person'] = fields('id', 'reference') | fields('sex living origin', 'scalar') | fields('name placeholder') | fields('names', ['name']) | fields('events', ['event']) | fields('notes', ['note']) | fields('facts', ['fact']) | fields('summary', 'text') | fields('media', ['image']) | fields('cardPresentation', 'card')
SCHEMAS['reported-kinship'] = fields('viewer', 'reference') | fields('text') | fields('sources', ['reference'])
SCHEMAS['person']['reportedKinship'] = Field(['reported-kinship'])
SCHEMAS['person']['treeName'] = Field()
SCHEMAS['surname-display'] = fields('clan', 'reference') | fields('form origin') | fields('written variants', ['text']) | fields('children', ['reference'])
SCHEMAS['person']['surnameDisplay'] = Field('surname-display')
SCHEMAS['person'] |= fields('namePresentation', 'name-presentation') | fields('confirmation', 'confirmation') | fields('retiredFacts', ['retired-fact']) | fields('public_fact status') | fields('identityAliases', ['reference']) | fields('living_basis author imported_context', policy='never')
SCHEMAS['birth-guess-anchor'] = fields('id', 'reference') | fields('year guessed age offset', 'scalar')
SCHEMAS['birth-guess-told'] = fields('year kind latest before', 'scalar')
SCHEMAS['birth-guess'] = fields('year exact relation', 'scalar') | fields('anchors', ['birth-guess-anchor']) | fields('told', 'birth-guess-told')
SCHEMAS['person']['birthGuess'] = Field('birth-guess')
SCHEMAS['probable-identity'] = fields('alias', 'reference') | fields('weight', 'scalar') | fields('name basis') | fields('sources', ['reference'])
SCHEMAS['person']['probableIdentities'] = Field(['probable-identity'])
SCHEMAS['possible-card'] = (fields('birth death summary') | fields('names', ['text']) | fields('facts', ['fact']) | fields('events', ['event'])
                            | fields('papers', ['reference']) | fields('media', ['image']))
SCHEMAS['probable-identity']['card'] = Field('possible-card', 'host-private')
# Where the person was looked for: the host-private reader only, never a public field.
SCHEMAS['coverage-source'] = fields('title') | fields('id', 'reference') | fields('outcome last strength identified recordRead surnameSearch placeSearch planComplete missingMore', 'scalar') | fields('forms missingForms', ['text'])
SCHEMAS['coverage-never'] = fields('title') | fields('id', 'reference')
SCHEMAS['coverage'] = fields('searched found identified recheck neverMore', 'scalar') | fields('sources', ['coverage-source']) | fields('never', ['coverage-never'])
SCHEMAS['person']['coverage'] = Field('coverage', 'host-private')
# What was told or read and what we propose instead: the family's own card, never a public field.
SCHEMAS['amendment'] = fields('original value basis') | fields('id', 'reference') | fields('field origin state weight leading revision', 'scalar') | fields('sources', ['reference'])
SCHEMAS['person']['amendments'] = Field(['amendment'], 'host-private')
SCHEMAS['person'] |= fields('story storyMore') | fields('illustrations', ['image']) | fields('relationshipUncertain', 'scalar')
SCHEMAS['image'] |= fields('sid sourceSid originalAsset', 'reference') | fields('photo cardOnly', 'scalar') | fields('mentionRole basis') | fields('crop face', ['scalar'])
SCHEMAS['name-presentation'] = fields('display full sourceName note patronymic maidenSurname byLanguage') | fields('isWoman isWife surnameUnknown maidenStatus', 'scalar') | fields('maidenSources', ['reference'])
SCHEMAS['confirmation'] = fields('basis') | fields('level research identityAccepted', 'scalar') | fields('sources', ['reference'])
SCHEMAS['retired-fact'] = SCHEMAS['fact'] | fields('retiredBecause')
SCHEMAS['card'] = fields('birth death place placeRole birthKind deathKind connectionNote connectionShort dateBasis dateReference')
SCHEMAS['family'] = fields('id husband wife', 'reference') | fields('children provenance', ['reference']) | fields('events', ['event']) | fields('status derived weight', 'scalar') | fields('basis')
SCHEMAS['edge'] = fields('from to parent child family identity', 'reference') | fields('type status role confidence weight missing missing_max main_line', 'scalar') | fields('sources', ['reference']) | fields('text note basis') | fields('derived', 'scalar')
SCHEMAS['source'] = fields('excerpt subjects', ['reference']) | fields('title description text') | fields('id record asset image', 'reference') | fields('kind', 'scalar') | fields('assetIn', ('map', 'reference'))
SCHEMAS['contribution-status'] = fields('applied errors warnings', ['text'])
SCHEMAS['research'] = fields('updates highlights', ['fact']) | fields('contributions', 'contribution-status')
SCHEMAS['badge'] = fields('text title') | fields('kind', 'scalar')
SCHEMAS['card-review'] = fields('text') | fields('kind likelihood', 'scalar') | fields('replaces', ['reference']) | fields('sources', ['reference'])
SCHEMAS['card-status'] = fields('origin in_original_tree in_current_ancestry family_memory', 'scalar') | fields('badges', ['badge']) | fields('review', 'card-review') | fields('confirmed', ['fact']) | fields('documented_relationships candidate_relationships', ['edge'])
SCHEMAS['graph'] = fields('people', ('map', 'person')) | fields('sources', ('map', 'source')) | fields('edges associations', ['edge']) | fields('families', ['family']) | fields('feeds', ['feed']) | fields('research', 'research') | fields('root narrator defaultViewer', 'reference') | fields('readerLabels', ('map', 'text')) | fields('identityAliases', ('map', 'reference')) | fields('cardStatuses', ('map', 'card-status'))
SCHEMAS['graph']['worldMap'] = Field('world')
SCHEMAS['graph']['presentationAliases'] = Field(('map', 'reference'), 'host-private')
SCHEMAS['profile-family'] = fields('id', 'reference') | fields('source_language fictional', 'scalar') | fields('title') | fields('languages', ['reference'])
SCHEMAS['profile'] = fields('schema_version', 'scalar') | fields('data', 'reference') | fields('family', 'profile-family') | fields('reader_names', ('map', 'name-row'))
SCHEMAS['host-text'] = fields('text') | fields('people', ['reference'])
# A separate working seal: these fields are never added to graph/feed schemas.
SCHEMAS['correspondence-reply'] = fields('text by at meaning') | fields('feedback', 'reference')
SCHEMAS['correspondence-person'] = fields('name') | fields('id', 'reference')
SCHEMAS['correspondence-item'] = (fields('title subject recipient text sender context sent_by sent_at how relevance cost_note destination')
    | fields('id state language destination_link follow_up cost kind', 'reference')
    | fields('line settles why_now')
    | fields('people', ['correspondence-person'])
    | fields('has_aim score shelved free_first', 'scalar')
    | fields('replies', ['correspondence-reply']))
SCHEMAS['correspondence-view'] = fields('text') | fields('items', ['correspondence-item'])
SCHEMAS['record'] = fields('interest', policy='never') | fields('id', 'reference') | fields('kind fictional privacy', 'scalar') | fields('title reading') | fields('fields', 'literal') | fields('events', ['event'])
# Storage-only forms have explicit never rules; diagnostics are not reader outputs.
STORAGE_ONLY = {
    'archive-rights': 'schema_version kind holder declared_by declared_at effective_from permissions living_subject_consent',
    'memory': 'id told_by date narrator items visibility blanks', 'version': 'interest id title line people status unknown_weight versions tests updated summary advice',
    'case': 'id question state waiting_on story_level basis narrative outcome waiting budget second_looks',
    'search': 'interest id at by source question query hits coverage meaning strict control saved result result_state provenance candidate_forms',
    'correspondence': 'id title subject recipient channel destination follow_up language text people question request sender state sent replies closed_at priority cost cost_note kind how relevance aim',
    'answer': 'id request by at text', 'scenario': 'level basis through_object rows hardship_map not_taken',
    'privacy': 'closed_topics living living_rule people life_decisions',
    'attestation': 'page language reviewer author digest safety_digest inspection_digest rules verdict at stage',
    'intake': 'id told_by date items people families record living_rule',
}
for name, names in STORAGE_ONLY.items():
    SCHEMAS[name] = fields(names, policy='never')

EVENT_KINDS = {'BIRT': 'birth', 'DEAT': 'death', 'MARR': 'marriage',
               'RESI': 'address', 'ADDR': 'address', 'address': 'address', 'residence': 'address'}


def event_kind(event):
    value = event.get('type') or event.get('tag')
    if any(EVENT_KINDS.get(event.get(key), event.get(key)) == 'address' for key in ('type', 'tag')):
        return 'address'
    return EVENT_KINDS.get(value, value)


def plain_text(text):
    # Declared text stays literal. Consumers escape it; markup-like spellings and
    # typographic controls are not evidence of a data/privacy failure.
    return unicodedata.normalize('NFC', text)


def project(value, shape, languages, surfaces=None, path='root'):
    return _project(value, shape, languages, surfaces, path)


def _project(value, shape, languages, surfaces=None, path='root'):
    """Default deny at every depth, including data supplied as nested metadata."""
    if value is None:
        return None
    if shape == 'literal':
        # Literal fields are structured source readings, not language rows or
        # extensible reader metadata. Every key and leaf is displayed and scanned.
        if isinstance(value, dict):
            result = {}
            for key, child in value.items():
                key = plain_text(key)
                if surfaces is not None:
                    surfaces.append((f'{path}.label[{key}]', key))
                result[key] = project(child, 'literal', languages, surfaces, f'{path}.{key}')
            return result
        if isinstance(value, list):
            return [project(v, 'literal', languages, surfaces, f'{path}[{i}]') for i, v in enumerate(value)]
        return project(value, 'text', languages, surfaces, path)
    if isinstance(shape, list):
        if not isinstance(value, list):
            raise ValueError(f'{path}: expected list')  # noqa: TRY004
        return [project(v, shape[0], languages, surfaces, f'{path}[{i}]') for i, v in enumerate(value)]
    if shape == 'image' and isinstance(value, str):
        value = {'asset': value}
    if isinstance(shape, tuple):
        if not isinstance(value, dict):
            raise ValueError(f'{path}: expected map')  # noqa: TRY004
        if shape[1] == 'text':
            value = {plain_text(k): v for k, v in value.items()}
            if surfaces is not None:
                surfaces.extend((f'{path}.label[{k}]', k) for k in value)
        return {k: project(v, shape[1], languages, surfaces, f'{path}.{k}') for k, v in value.items()}
    if shape in {'scalar', 'reference'}:
        if isinstance(value, (dict, list)):
            raise ValueError(f'{path}: scalar cannot contain nested reader surfaces')
        if surfaces is not None and isinstance(value, str) and shape == 'scalar':
            surfaces.append((path, value))
        return (plain_text(value) if shape == 'scalar' else unicodedata.normalize('NFC', value)) if isinstance(value, str) else copy.deepcopy(value)
    if shape in {'text', 'name-row'}:
        if isinstance(value, dict):
            return {k: project(v, 'text' if k != 'short' else 'name-row', languages, surfaces, f'{path}.{k}')
                    for k, v in value.items() if k in languages or (shape == 'name-row' and k == 'short')}
        if not isinstance(value, (str, int, float, bool)):
            raise ValueError(f'{path}: expected declared text')
        if isinstance(value, str):
            value = plain_text(value)
        if surfaces is not None and isinstance(value, str):
            surfaces.append((path, value))
        return copy.deepcopy(value)
    if not isinstance(value, dict):
        raise ValueError(f'{path}: expected {shape} object')  # noqa: TRY004
    schema = SCHEMAS[shape]
    return {k: project(v, schema[k].shape, languages, surfaces, f'{path}.{k}')
            for k, v in value.items() if k in schema and schema[k].policy != 'never'}


def confirmed_name(person):
    """No inferred part of a protected person's canonical name becomes reader fact."""
    names = person.get('names', [])
    if not any(n.get('inferred_parts') for n in names):
        return person.get('name', '')
    name = next((n for n in names if n), {})
    return ' '.join(name[k] for k in ('given', 'patronymic', 'surname')
                    if name.get(k) and k not in name.get('inferred_parts', {}))


def restrict_graph(instance, graph, *, host_private=False):
    from familiar.checks.engine import _known_people, life_status, load

    from .edition import apply
    apply(instance, graph)
    from familiar.tree.builder import read_json
    from familiar.tree.surnames import apply as surname_display
    surname_display(instance, graph, read_json(instance.path('tree_metadata'), {}))
    from .subjects import attribute_documents
    withheld = attribute_documents(instance, graph, family_display=host_private)
    graph = private_graph(instance, graph, host_private=host_private, withheld=withheld, amendments=True)
    if host_private:
        return graph
    privacy = load(instance.path('privacy'), {})
    known = _known_people(instance)
    for pid, person in list(graph.get('people', {}).items()):
        person.pop('probableIdentities', None)
        if life_status(known.get(pid, {'id': pid}), privacy) == 'dead':
            # The imported living flag is a source classification; a reader gets
            # the effective assessment, including the common age horizon.
            person['living'] = False
        if life_status(known.get(pid, {'id': pid}), privacy) != 'dead':
            # Preserve the reader's original empty containers without exposing fields.
            result = {'id': pid, 'name': confirmed_name(person), **({'placeholder': person['placeholder']} if person.get('placeholder') else {}), 'facts': [], 'events': [], 'media': []}
            first_name = next((n for n in person.get('names', []) if n), {})
            patronymic = first_name.get('patronymic', '')
            result['treeName'] = ' '.join(result['name'].replace(patronymic, '').split()) if patronymic else result['name']
            if person.get('reportedKinship'):
                result['reportedKinship'] = person['reportedKinship']
            # A living person's name in the reader's language is still only the name.
            if (local := (person.get('namePresentation') or {}).get('byLanguage')) and result['name'] == person.get('name'):
                result['namePresentation'] = {'byLanguage': local}
            graph['people'][pid] = result
    # Card explanations can contain dates, evidence and superseded claims.
    statuses = graph.get('cardStatuses', {})
    for pid in list(statuses):
        if life_status(known.get(pid, {'id': pid}), privacy) != 'dead':
            del statuses[pid]
            continue
        status = statuses[pid]
        for key in ('documented_relationships', 'candidate_relationships'):
            if key in status:
                status[key] = [edge for edge in status[key] if all(
                    life_status(known.get(member, {'id': member}), privacy) == 'dead'
                    for member in (edge.get(k) for k in ('from', 'to', 'parent', 'child')) if member)]
    for family in graph.get('families', []):
        members = [family.get('husband'), family.get('wife'), *family.get('children', [])]
        if any(pid and life_status(known.get(pid, {'id': pid}), privacy) != 'dead' for pid in members):
            family['events'] = []
            family.pop('basis', None)
    from .subjects import closure, protected_record
    for sid, source in list(graph.get('sources', {}).items()):
        resolved = closure(instance, source, shape='source', people=known)
        if (any(life_status(known[pid], privacy) != 'dead' for pid in resolved.people) or
                any(map(protected_record, resolved.records.values()))):
            graph['sources'][sid] = {key: val for key, val in source.items() if key in {'id', 'kind'}}
    for collection in ('edges', 'associations'):
        for edge in graph.get(collection, []):
            members = [edge.get(k) for k in ('from', 'to', 'parent', 'child')]
            if any(pid and life_status(known.get(pid, {'id': pid}), privacy) != 'dead' for pid in members):
                for key in ('text', 'note', 'basis'):
                    edge.pop(key, None)
    if 'feeds' in graph:
        from .narrative import restrict_feed as project_narrative
        graph['feeds'] = [project_narrative(instance, feed) for feed in graph['feeds']]
    return graph


def restrict_feed(instance, feed):
    from .narrative import restrict_feed as project_narrative
    from .subjects import attribute_documents
    from familiar.tree.builder import _build
    from .edition import apply
    graph = apply(instance, _build(instance))
    graph['feeds'] = [copy.deepcopy(feed)]
    withheld = attribute_documents(instance, graph)
    return project_narrative(instance, private_graph(
        instance, graph, host_private=False, withheld=withheld)['feeds'][0])


def public_references(instance, value, *, graph=None):
    """Replace storage ids after checks have bound the canonical references."""
    from familiar.checks.engine import _known_people, life_status
    from familiar.tree.life import _participants

    known = _known_people(instance)
    graph = graph or {}
    sources = graph.get('sources', {})
    aliases = graph.get('identityAliases', {})
    reserved = known.keys() | sources.keys() | aliases.keys()
    replacements = {}

    def assign(ids, kind):
        number = 0
        for ident in ids:
            if ident in replacements:
                continue
            number += 1
            while (opaque := f'public-{kind}-{number}') in reserved:
                number += 1
            replacements[ident] = opaque

    people = {row['id']: row for row in known.values() if life_status(row, {}) != 'dead'}
    assign(sorted(people, key=lambda pid: ((confirmed_name(people[pid]) or '').casefold(), pid)), 'person')
    absorbed = {row['id']: row for target in set(aliases.values()) if target in known
                for row in _participants(known[target])}
    assign((pid for pid in sorted(aliases) if life_status(absorbed.get(pid, {}), {}) != 'dead'), 'alias')
    assign((sid for sid, source in sources.items() if source.keys() <= {'id', 'kind'}), 'source')

    def rewrite(node):
        if isinstance(node, dict):
            return {replacements.get(k, k): rewrite(v) for k, v in node.items()}
        if isinstance(node, list):
            return [rewrite(v) for v in node]
        return replacements.get(node, node) if isinstance(node, str) else node

    return rewrite(value)


def scan(instance, value, shape, *, host_private=False):
    from .memory_visibility import require_displayable
    require_displayable(instance, value)
    """Scan precisely what the declared projection can publish, in every language."""
    from familiar.checks.engine import load
    from familiar.rules.cascade import Registry
    from familiar.rules.roles import method_root
    if shape == 'feed':
        value = restrict_feed(instance, value)
    surfaces = []
    projected = project(value, shape, instance.languages, surfaces)
    # Recheck pairs on the exact declared bytes, including the local host projection.
    from .restorations import restorations
    if any(restorations(projected)):
        from .subjects import closure
        closure(instance, projected, shape=shape)
    if shape == 'graph' and not host_private:
        projected.pop('presentationAliases', None)
        from .subjects import protected_record
        for person in projected.get('people', {}).values():
            person.pop('probableIdentities', None)
            person.pop('coverage', None)  # the host-private display fields have no public path
            person.pop('amendments', None)
        from familiar.checks.engine import _known_people, generated, life_status

        from .subjects import closure
        known = _known_people(instance)
        privacy = load(instance.path('privacy'), {})
        resolved = closure(instance, projected, shape='graph', people=known)
        for image in resolved.images:
            image_subjects = closure(instance, image, shape='image', people=known)
            subjects = image_subjects.people
            if image.get('kind') == 'photo-treatment' and any(life_status(known[pid], privacy) != 'dead' for pid in subjects):
                raise ValueError('TRUST-06: living photo treatment is local to the host only')
            if image.get('kind') == 'document-scan' and not image.get('record'):
                raise ValueError('TRUST-10: tree document scan needs a canonical corpus record')
            if image_subjects.records and (any(life_status(known[pid], privacy) != 'dead' for pid in subjects) or
                    any(map(protected_record, image_subjects.records.values()))):
                raise ValueError('TRUST-06: living person document cannot be shown as a tree image')
            if generated(image) and (image.get('role') in {'portrait', 'document'} or image.get('is_portrait') or
                    image.get('subject_living') or image.get('subject_child') or
                    any(life_status(known[pid], privacy) != 'dead' for pid in subjects)):
                raise ValueError('TRUST-08: generated image has an excluded role or living/child subject')
            if generated(image) and image.get('reconstruction') is not True:
                raise ValueError('TRUST-08: generated tree image needs reconstruction disclosure')
            if image.get('kind') == 'family-photograph':
                from .archive import photograph_rights
                rights = photograph_rights(instance, image)
                if not rights or not rights.get('holder') or not rights.get('permissions', {}).get('family_app'):
                    raise ValueError('TRUST-10: tree family photograph lacks family-app rights')
    terms = list(load(instance.path('privacy'), {}).get('closed_topics', []))
    registry = Registry(method_root() / 'rules', instance)
    scope = 'feed:' + str(value.get('id')) if shape == 'feed' else None
    for key in ('privacy.closed_topics_file', 'privacy.present_day_politics_file'):
        if name := registry.resolve_setting(key, scope).value:
            path = instance.root / name
            data = tomllib.loads(path.read_text(encoding='utf-8')) if path.suffix == '.toml' else load(path, {})
            terms.extend(data.get('terms', data.get('closed_topics', [])))
    # Class-R term matches are reported by checks.engine's text worklist. The old
    # surface x term loop discarded every match; retain its form check once.
    for entry in terms:
        term = entry.get('term') if isinstance(entry, dict) else entry
        if not isinstance(term, str) or not term.strip():
            raise ValueError('TRUST-07: restricted terms must be nonempty text')
    return projected


def quotation_filter(instance, records):
    """Detect a telling literal span, including a cropped or translated reading."""
    from familiar.checks.engine import load, record_path, strings
    from familiar.reader.graph import card_memory

    def fragments(text, minimum):
        # Count whole words. Part of a district or province name can otherwise
        # turn an ordinary birthplace into a quotation from an unrelated sheet.
        words = list(re.finditer(r"[^\W_]+(?:[-’'][^\W_]+)*", text))
        for start, word in enumerate(words):
            length = len(word.group())
            end = start + 1
            while end < len(words) and length < minimum:
                length += len(words[end].group()) + 1
                end += 1
            if length >= minimum:
                yield ' '.join(w.group().casefold() for w in words[start:end]), word.start(), words[end - 1].end()

    # A citation can also accompany an ordinary name or a researcher's own
    # argument. Only an explicitly quoted passage uses the shorter threshold.
    withheld, cited = set(), {}
    translations = card_memory(instance).values() if records else ()
    for rid in records:
        record = load(record_path(instance, rid), {})
        lines = {line.strip() for text in strings([record.get('reading'), record.get('fields')])
                 for line in text.splitlines() if line.strip()}
        lines |= {texts[line] for texts in translations for line in lines if line in texts}
        cited[rid] = {part for line in lines for part, _, _ in fragments(line, 16)}
        withheld.update(part for line in lines for part, _, _ in fragments(line, 40))

    def redact(text, sources=()):
        matches = []
        if withheld and len(text) >= 40:
            matches.extend((a, b) for part, a, b in fragments(text, 40) if part in withheld)
        selected = [cited[sid] for sid in sources if sid in cited]
        if selected:
            for quote in re.finditer(r'«([^»]+)»|“([^”]+)”|„([^”]+)”|"([^"]+)"', text):
                start = quote.start(quote.lastindex)
                matches.extend((start + a, start + b) for part, a, b in fragments(quote[quote.lastindex], 16)
                               if any(part in terms for terms in selected))
        pieces, stop = [], 0
        for start, end in sorted(matches):
            if not pieces or start > stop + 1:
                pieces.extend((text[stop:start], '…'))
            stop = max(end, stop)
        return ''.join([*pieces, text[stop:]]) if pieces else text
    return redact


def private_graph(instance, graph, *, host_private=True, withheld=(), amendments=False):
    """Exclude protected documents and addresses from every family display."""
    from familiar.checks.engine import _known_people, life_status, load, record_path, strings

    from .restorations import period_pair
    from .subjects import closure, fileless_memory, historical_records, protected_record
    known = _known_people(instance, family_display=host_private)
    privacy = load(instance.path('privacy'), {})
    addresses = set()

    def dead(pid):
        return life_status(known.get(pid, {'id': pid}), privacy) == 'dead'

    if host_private:
        for pid, person in graph.get('people', {}).items():
            status = life_status(known.get(pid, {'id': pid}), privacy)
            if status == 'unknown':
                person.pop('living', None)
            else:
                person['living'] = status == 'living'
    for person in graph.get('people', {}).values():
        person.pop('amendments', None)

    def blocked_id(ref):
        return ('source', ref) in withheld or ('record', ref) in withheld

    literal_readings = {}

    def unsafe_document(node, shape, *, chapter=False):
        if node.get('_document_private') or (not node.get('excerpt') and ('record', node.get('record')) in withheld):
            return True
        resolved = closure(instance, node, shape=shape, people=known)
        attributed = (resolved.people or shape == 'image' and period_pair(node)
                      or host_private and chapter and historical_records(resolved))
        unsafe = (not attributed or any(life_status(known[p], privacy) != 'dead' for p in resolved.people)
                  or any(map(protected_record, resolved.records.values())))
        if not unsafe and shape == 'document' and node.get('excerpt'):
            # Closure checked these exact literal fields and their own people.
            # Only their read strings are independent of the withheld full sheet.
            fields = resolved.records[node['record']]['fields']
            for part in [node, *node.get('parts', []), *node.get('snippets', [])]:
                if part.get('field') in fields and part.get('read') == fields[part['field']]:
                    literal_readings[id(part)] = part['read']
        return unsafe

    sources = graph.get('sources', {})
    dropped_sources = {sid for sid, source in sources.items()
                       if blocked_id(sid) or not (host_private and fileless_memory(source) and not source.get('_document_attributed'))
                       and unsafe_document(source, 'source')}
    blocked_papers = {sid for sid in dropped_sources if (
        sources[sid].get('record') or sources[sid].get('asset') or sources[sid].get('kind') in
        {'document', 'document-scan', 'archive-record', 'home-paper', 'index-entry'})}
    paper_ids = {sid: sources[sid].get('record') or sid for sid in dropped_sources}
    blocked_assets = {ref for kind, ref in withheld if kind == 'asset'}
    if not host_private:
        from .gallery import photographs
        blocked_assets.update('/' + name for name, photo in photographs(instance).items()
                              if photo.get('unnamed_faces') or photo.get('show') == 'private')
    # Literal copies carried to a different narrative field have the same
    # protection as a typed citation. Short common field values are handled
    # through the citation, where their meaning is known.
    records = {ref for kind, ref in withheld if kind == 'record'}
    quotes_record = quotation_filter(instance, records)
    inline_assets = re.compile(r'''(?:src=["']|href=["']|\]\()(/[^"'\s)<>]+)''')

    def safe_text(text, cited=()):
        if text in blocked_assets:
            return ''
        if blocked_assets:
            text = inline_assets.sub(lambda match: match[0].replace(match[1], '#') if match[1] in blocked_assets else match[0], text)
        return quotes_record(text, cited)

    def cites_withheld(node):
        return any(('record', s) in withheld or s in blocked_papers
                   for s in [*(node.get('sources') or []), *(node.get('provenance') or [])])

    def walk(node, key='', cited=()):
        if isinstance(node, list):
            return [walk(v, key, cited) for v in node if not isinstance(v, dict) or not excluded(v, key)]
        if isinstance(node, dict):
            withhold_basis = key in {'facts', 'retiredFacts', 'events', 'names'} and cites_withheld(node)
            if withhold_basis:
                cited = [paper_ids.get(sid, sid) for sid in
                         [*(node.get('sources') or []), *(node.get('provenance') or [])] if blocked_id(sid) or sid in blocked_papers]
            return {k: literal_readings[id(node)] if k == 'read' and id(node) in literal_readings else walk(v, k, cited)
                    for k, v in node.items() if k.casefold() not in {'address', 'addr', 'адрес'}
                    and not (key == 'flow' and k == 'placeholder' and not host_private)
                    and not (withhold_basis and k in {'basis', 'source_text', 'note', 'cause'})
                    and not (isinstance(v, dict) and excluded(v, k))}
        if isinstance(node, str) and key in {'id', 'record', 'sources', 'provenance', 'sid', 'sourceSid'} and node in sources:
            return node
        return safe_text(node, cited) if isinstance(node, str) else node

    # Where a dead person lived is family history, not an address: the locality stays.
    # Explicit address events, and every residence of a living or unknown person, remain excluded.
    localities = {id(e) for pid, person in (graph.get('people') or {}).items()
                  if isinstance(person, dict) and pid in known and life_status(known[pid], privacy) == 'dead'
                  for e in person.get('events') or []
                  if isinstance(e, dict) and {e.get('type'), e.get('tag')} & {'residence', 'RESI'}
                  and not {e.get('type'), e.get('tag')} & {'address', 'ADDR'}}

    def excluded(node, key):
        if key == 'truth' and ('asset', node.get('record')) in withheld:
            return True
        if any(node.get(k) in blocked_assets for k in ('asset', 'full', 'originalAsset', 'url')
               if isinstance(node.get(k), str)):
            return True
        if event_kind(node) == 'address':
            if id(node) in localities:
                return False
            addresses.update(str(node[k]) for k in ('place', 'value', 'text', 'note') if node.get(k))
            return True
        treatment = node if node.get('kind') == 'photo-treatment' else node.get('ours', {})
        if treatment.get('kind') == 'photo-treatment':
            resolved = closure(instance, node, shape='image', people=known)
            living = [p for p in resolved.people if life_status(known[p], privacy) != 'dead']
            if living and not host_private:
                return True
        if not host_private and key in {'media', 'illustrations', 'figures', 'picture'}:
            resolved = closure(instance, node, shape='image', people=known)
            if any(life_status(known[p], privacy) != 'dead' for p in resolved.people):
                return True
        if key == 'notes' and cites_withheld(node):
            return True
        if key in {'facts', 'retiredFacts'} and node.get('record'):
            return unsafe_document(node, 'fact')
        if key == 'records' or node.get('kind') == 'document-scan' or (key in {'media', 'illustrations', 'figures', 'picture'} and (node.get('record') or node.get('photo') is False)):
            return unsafe_document(node, 'document' if key == 'records' else 'image', chapter=key in {'records', 'figures', 'picture'})
        return False

    for feed in graph.get('feeds', []) if host_private else []:
        from .narrative import restrict_feed
        feed.update(restrict_feed(instance, feed, host_private=True))
    if amendments and instance.path('amendments').is_dir():
        from familiar.tree.amendments import apply
        from .memory_visibility import require_displayable, select
        memory = select(instance)
        tellings = {row['id'] for _, telling in memory[0] for row in [telling, *telling.get('items', [])]}

        def safe_source(sid):
            if blocked_id(sid) or sid in memory[1]:
                return False
            if record_path(instance, sid).is_file():
                return not unsafe_document({'record': sid}, 'source')
            return sid in tellings or sid in graph['sources'] and sid not in dropped_sources

        def visible(row):
            if not dead(row['person']) or not all(safe_source(s) for s in (row['original']['source'], *row.get('sources', []))):
                return False
            try:
                require_displayable(instance, row, selection=memory)
            except ValueError:
                return False
            return all(safe_text(s) == s for s in strings([row['original']['text'], row['basis'], row['value']]))

        apply(instance, graph, visible=visible, shown=host_private)
    for sid in dropped_sources:
        graph['sources'][sid] = {k: v for k, v in graph['sources'][sid].items() if k in {'id', 'kind'}}
    graph = walk(graph)
    from familiar.reader.experiences import protect_game_media
    protect_game_media(graph)

    def redact(node):
        if isinstance(node, dict):
            return {k: redact(v) for k, v in node.items()}
        if isinstance(node, list):
            return [redact(v) for v in node]
        if isinstance(node, str):
            for address in sorted(addresses, key=len, reverse=True):
                node = node.replace(address, '')
        return node
    return redact(graph)


def media_omissions(instance, feeds):
    """Private advice from the same projections that remove chapter media and games."""
    from familiar.checks.engine import _known_people, life_status, load
    from familiar.tree.builder import _build
    from familiar.reader.experiences import play
    from .subjects import attribute_documents, closure
    graph = _build(instance)
    graph['feeds'] = copy.deepcopy(feeds)
    play(instance, graph)
    withheld = attribute_documents(instance, graph)
    known, privacy = _known_people(instance), load(instance.path('privacy'), {})
    rows = []
    shown = private_graph(instance, copy.deepcopy(graph), withheld=withheld)
    for feed, visible_feed in zip(graph['feeds'], shown['feeds']):
        def chapter_media(chapter, visible, cid):
            for field in ('records', 'picture', 'figures'):
                items = chapter.get(field, [])
                items = items if isinstance(items, list) else [items]
                kept = visible.get(field, [])
                kept = kept if isinstance(kept, list) else [kept]
                for index, item in enumerate(items):
                    if not item or any(all(item.get(k) == v.get(k) for k in ('asset', 'record', 'subjects', 'ours')) for v in kept):
                        continue
                    resolved = closure(instance, item, shape='document' if field == 'records' else 'image', people=known)
                    subjects = [known[p].get('name', p) + ' (' + life_status(known[p], privacy) + ')'
                                for p in sorted(resolved.people) if life_status(known[p], privacy) != 'dead']
                    rows.append({'feed': feed['id'], 'chapter': cid, 'view': 'host',
                        'field': field, 'item': item.get('record') or item.get('asset') or str(index + 1),
                        'label': item.get('title') or item.get('caption') or str(index + 1),
                        'reason': ', '.join(subjects) or 'protected document or undeclared subjects',
                        'action': 'document' if field == 'records' or resolved.records else 'picture'})
            truth = chapter.get('game', {}).get('truth', {}).get('record')
            if truth and truth != visible.get('game', {}).get('truth', {}).get('record'):
                cause = next((r for r in reversed(rows) if r['chapter'] == cid and r['view'] == 'host'), {})
                rows.append(dict(cause, feed=feed['id'], chapter=cid, view='host',
                                 field='game', item=truth, label=cause.get('label', truth), reason=cause.get('reason', 'withheld document'), action='document'))
            for index, extra in enumerate(chapter.get('extras', [])):
                chapter_media(extra, visible.get('extras', [])[index] if index < len(visible.get('extras', [])) else {}, cid)
        for chapter, visible in zip(feed.get('chapters', []), visible_feed.get('chapters', [])):
            chapter_media(chapter, visible, chapter['id'])
    return rows


def scan_assets(instance, value, *, errors=None, seen=None):
    """Check each reachable URL once; collect failures without granting publication."""
    from familiar.reader.assets import publication_bytes
    collected = [] if errors is None else errors
    seen = set() if seen is None else seen
    def walk(node):
        if isinstance(node, dict):
            for key, child in node.items():
                if key in {'asset', 'full', 'cover', 'orig', 'originalAsset'} and isinstance(child, str) and child and child not in seen:
                    seen.add(child)
                    try:
                        path = instance.media_file(child)
                        if path is None:
                            raise ValueError('missing projected media')
                        publication_bytes(path.read_bytes(), child)
                    except (ValueError, OSError) as exc:
                        collected.append({'location': child, 'message': str(exc)})
                else:
                    walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)
    if errors is None and collected:
        raise ValueError(f'{len(collected)} asset violations:\n' + '\n'.join(
            f'{row["location"]}: {row["message"]}' for row in collected))


_SEAL = object()


class Publication:
    """Opaque serialized capability. Only the gate constructs one; callers get copies."""
    def __init__(self, seal, inputs, files, data, verdict, manifest=None):
        if seal is not _SEAL:
            raise TypeError('Publication is constructed by the family gate')
        self.inputs = copy.deepcopy(inputs)
        self.__files = dict(files)
        self.__data = copy.deepcopy(data)
        self.verdict = copy.deepcopy(verdict)
        self.__working = verdict.get('state') == 'working'
        self.__host_private = verdict.get('state') == 'host-private'
        self.manifest = copy.deepcopy(manifest or {})
        self.__digest = hashlib.sha256(json.dumps(self.inputs, sort_keys=True).encode()).hexdigest()

    def data(self):
        return copy.deepcopy(self.__data)

    def files(self):
        return dict(self.__files)

    @property
    def working(self):
        return self.__working

    @property
    def host_private(self):
        return self.__host_private

    def check(self, instance):
        from .writer import display_instance, fingerprints
        if self.__host_private:
            instance = display_instance(instance)
        if self.__digest != hashlib.sha256(json.dumps(self.inputs, sort_keys=True).encode()).hexdigest() or self.inputs != fingerprints(instance):
            raise ValueError('family inputs changed before publication')


def _seal(inputs, files, data, verdict, manifest=None):
    return Publication(_SEAL, inputs, files, data, verdict, manifest)
