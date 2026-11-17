# START_MODULE_CONTRACT: MOD-INSTANCE-VALIDATION
# PURPOSE: Check authored family forms and references before reporting content readiness.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - misplaced family/requests data reports the configured questions path instead of silently disappearing [review: engine lead]
# - invalid settings and dangling adopted references cannot receive a valid report; collector-only form errors remain separate [review: engine lead]
# - empty folders do not count as chapter or cycle content [review: engine lead]
# - own-file checks name every selected finding without certifying unrelated files or publication [review: engine lead]
# - absent source details remain null; literal fields need no invented transcript [review: engine lead]
# - editorial completeness does not block data validation [review: engine lead]
# - malformed documents, chapters and evidence containers report their file and repair form together [review: engine lead]
# - full checks expose nonblocking birth-clan surname differences after identity resolution [review: engine lead]
# - search journal rows outside the ledger form are advice that names the migration command, never a refusal [review: engine lead]
# - a controlled saved zero supports only against arguments; missing read scope or doubtful queries remain unusable [review: engine lead]
# - whole and selected-file checks report rejected contributions with their claim and cause [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE (the shared family boundary contract)
# - docs/PRD.md#FORMS
# - MOD-RULES-CASCADE
# - MOD-INSTANCE-RESEARCH-FORMS
# - MOD-SEARCH-LEDGER (ledger findings)
# :END_MODULE_CONTRACT
import hashlib
import json
import math
import re
import unicodedata

from .gate import boundary
from .research_forms import request_storage_errors
from familiar.check_policy import decision as check_decision


def validate_changes(instance, paths):
    """Own-item validation; unrelated drafts are neither preconditions nor waivers."""
    from familiar.rules.cascade import Registry
    from familiar.rules.roles import method_root

    from .gate import require_assertions
    from .research_forms import numeric_errors
    Registry(method_root() / 'rules', instance)
    selected = set()
    for path in paths:
        selected.add(str(path))
        if path.parent == instance.path('tree_snapshot'):
            selected.add(str(path.parent))
        if path == instance.path('privacy'):
            selected.add('privacy')
        if path == instance.path('evidence'):
            selected.update({'evidence', 'evidence source'})
        if path.suffix not in {'.json', '.jsonl'}:
            continue
        values = ([json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
                  if path.suffix == '.jsonl' else [json.loads(path.read_text(encoding='utf-8'))])
        for value in values:
            require_assertions(value)
            if path.parent == instance.path('tree_snapshot'):
                selected.update(p['id'] for p in value.get('people', []))
            if not path.is_relative_to(instance.path('state')):
                errors = list(numeric_errors(value))
                if errors:
                    raise ValueError('; '.join(errors))
    try:
        result = _check(instance, selected)
    except (TypeError, AttributeError, KeyError) as exc:
        raise ValueError('malformed changed item: ' + str(exc)) from exc
    # Draft catalogues may point to a record not saved yet; the output gate
    # still checks every reference. This is the sole reference relaxation.
    errors = [e for e in result['errors'] if not (
        e['message'].startswith('unknown record ') and
        any(p.parent.parent == instance.path('feeds') and str(p) == e['location'] for p in paths))]
    if any(p.is_relative_to(instance.path('contributions')) for p in paths):
        from familiar.tree.builder import _build
        _build(instance)
    if errors:
        raise ValueError('; '.join(e['message'] for e in errors))


@boundary('diagnostic')
def check(instance, *, paths=None, prefix=None):
    if paths or prefix:
        selected = set()
        for value in paths or []:
            path = (instance.root / value).resolve()
            if not path.is_relative_to(instance.root):
                raise ValueError('check path must stay inside the family root')
            if not path.exists():
                raise ValueError('check path does not exist: ' + str(value))
            selected.update(p for p in ([path] if path.is_file() else path.rglob('*'))
                            if p.is_file() and p.suffix in {'.json', '.jsonl'})
        if prefix:
            start = (instance.root / prefix).resolve()
            if not start.is_relative_to(instance.root):
                raise ValueError('check prefix must stay inside the family root')
            selected.update(p for p in start.parent.rglob('*') if p.is_file()
                            and str(p).startswith(str(start)) and p.suffix in {'.json', '.jsonl'})
        if not selected:
            raise ValueError('no JSON/JSONL files selected; nothing was checked')
        locations = {str(p) for p in selected}
        if instance.path('tree_snapshot') / 'people.json' in selected:
            locations.add(str(instance.path('tree_snapshot')))
            locations.update(p['id'] for p in json.loads((instance.path('tree_snapshot') / 'people.json').read_text(encoding='utf-8'))['people'])
        if instance.path('tree_snapshot') / 'families.json' in selected:
            locations.add(str(instance.path('tree_snapshot')))
        if instance.path('privacy') in selected:
            locations.add('privacy')
        if instance.path('evidence') in selected:
            locations.update({'evidence', 'evidence source'})
        result = _forms(instance, locations)
        return dict(result, scope='selected-files', files=sorted(str(p.relative_to(instance.root)) for p in selected),
                    unverified=['unselected files, family readiness and publication guarantees'])
    from .gate import evaluate
    verdict = evaluate(instance)
    result = verdict['forms']
    result['valid'] = not verdict['blocked']
    result['errors'] = [{'location': f['location'], 'message': f['message']} for f in verdict['findings'] if f['mode'] == 'block' and f['certainty'] == 'finding']
    result['advice'] = [f for f in verdict['findings'] if f['mode'] != 'block']
    if result['valid']:
        from familiar.tree.builder import _build, read_json
        from familiar.tree.surnames import findings
        result['surname_findings'] = findings(_build(instance), read_json(instance.path('tree_metadata'), {}),
                                              instance.source_language)
    return result


def _forms(instance, selected=None):
    try:
        return _check(instance, selected)
    except (ValueError, OSError, TypeError, AttributeError, KeyError) as exc:
        return {'valid': False, 'errors': [{'location': 'family data', 'weight': 'instance.required-identity-privacy-fields-or-executable-collection-container',
                                           'message': f'malformed form: {exc}'}],
                'data_files': {}, 'first_chapter_missing': ['resolve validation errors'],
                'full_cycle_missing': ['resolve validation errors'],
                'unverified': ['readiness withheld after malformed form']}


def _check(instance, selected=None):
    from familiar.rules.cascade import Registry
    from familiar.rules.roles import method_root

    errors = []
    advice = []
    research_work = []
    work_paths = set()
    from .display import research_inputs
    adopted = research_inputs(instance) if selected is None else set()
    research_roots = {key: instance.path(key) for key in ('records', 'searches')}
    from .archive import declaration
    try:
        declaration(instance)
    except (ValueError, TypeError, OSError) as exc:
        if selected is None or str(instance.path('archive_rights')) in selected:
            errors.append({'location': 'archive_rights', 'message': str(exc), 'weight': 'instance.archive-rights'})
    registry = Registry(method_root() / 'rules', instance)
    data_files = {}
    for scope in [None] + sorted({target for _, target, _ in registry.layers if target}):
        for key in ('privacy.closed_topics_file', 'privacy.present_day_politics_file'):
            result = instance.data_file(registry.resolve_setting(key, scope).value)
            data_files[f'{scope or "family"}:{key}'] = result
            if result['status'] in {'missing', 'unreadable'} and (selected is None or str(instance.root / 'familiar.toml') in selected):
                if key != 'lang.lexicon':
                    errors.append({'location': key, 'message': result['status'], 'weight': 'instance.restriction-list'})

    def fail(where, message, rule=None):
        if selected is None or str(where) in selected or any(str(where).startswith(p + ':') for p in selected):
            location = str(where)
            path = location if location in working_files else location.rpartition(':')[0]
            working = selected is None and path in working_files
            if working:
                work_paths.add(path)
            target = research_work if working else errors if check_decision(rule) == 'block' else advice
            target.append({'location': location, 'message': message, 'weight': rule})

    working_files = {str(p) for root in research_roots.values() for p in root.rglob('*')
                     if p.is_file() and p not in adopted} if selected is None else set()

    from .edition import errors as edition_errors
    for message in edition_errors(instance):
        fail(instance.path('edition'), message, 'instance.message')

    def load(path, default):
        if not path.exists():
            return default
        try:
            from .research_forms import require_container
            from .subjects import normalized
            return require_container(path, normalized(json.loads(path.read_text(encoding='utf-8'))),
                                     form='evidence' if path == instance.path('evidence') else None)
        except (ValueError, OSError, TypeError) as exc:
            fail(path, str(exc), 'instance.str-exc')
            return default

    for path, message in request_storage_errors(instance):
        fail(path, message, 'instance.message')

    def rows(key):
        path = instance.path(key)
        files = [path] if path.is_file() else sorted(path.rglob('*')) if path.exists() else []
        result = []
        for file in files:
            if any(p.startswith('.') for p in file.relative_to(path.parent).parts):
                continue
            if file.suffix == '.json':
                data = load(file, {})
                if key == 'records' and not isinstance(data, dict):
                    fail(file, 'record: expected one object per JSON file', 'instance.record-expected-one-object-per-json-file')
                    continue
                entries = data if isinstance(data, list) else [data]
            elif file.suffix == '.jsonl':
                entries = []
                try:
                    lines = file.read_text(encoding='utf-8-sig').splitlines()
                except (ValueError, OSError) as exc:
                    fail(file, str(exc), 'instance.str-exc')
                    continue
                for n, line in enumerate(lines, 1):
                    if line.strip():
                        try:
                            entries.append(json.loads(line))
                        except ValueError as exc:
                            fail(f'{file}:{n}', str(exc), 'instance.str-exc')
            else:
                continue
            for entry in entries:
                if isinstance(entry, dict):
                    result.append((file, entry))
                else:
                    fail(file, 'expected object', 'instance.expected-object')
        return result

    def required(row, fields, where, prefix=''):
        if not isinstance(row, dict):
            fail(where, f'{prefix or "form"}: expected object with {fields}', 'instance.f-prefix-or-form-expected-object-with')
            return False
        for field in fields.split():
            if field not in row or row[field] is None or row[field] == '':
                if where == 'privacy' or field in {'id', 'record', 'person'}:
                    fail(where, f'required data field {prefix}{field}', 'instance.required-identity-privacy-fields-or-executable-collection')
            elif (field in {'names', 'events', 'notes', 'children', 'provenance', 'items',
                           'language', 'versions', 'tests', 'for', 'against', 'basis',
                           'allowed', 'records', 'snippets', 'sources', 'people'}
                  and not isinstance(row[field], list)):
                fail(where, f'{prefix}{field} must be an array', 'instance.required-identity-privacy-fields-or-executable-collection-container')
        return True

    def index(entries, label):
        result = {}
        for path, row in entries:
            required(row, 'id', path)
            if not isinstance(row, dict):
                continue
            ident = row.get('id')
            if not isinstance(ident, str) or not ident.strip():
                fail(path, f'{label} id must be nonempty text', 'instance.f-label-id-must-be-nonempty-text')
                continue
            if ident in result:
                fail(path, f'duplicate {label} id {ident}', 'instance.f-duplicate-label-id-ident')
            result[ident] = row
        return result

    def question_ref(row, where):
        # A display snapshot holds only adopted research, never the versions folder;
        # the question reference is checked on the whole instance.
        if not getattr(instance, '_immutable_snapshot', False):
            ref(row.get('question'), versions, where)

    def ref(value, known, where):
        if value is not None and (not isinstance(value, str) or value not in known):
            ids = sorted(known)
            hint = ', '.join(ids[:20]) or '(none declared)'
            if len(ids) > 20:
                hint += f', … ({len(ids)} total); inspect the family declarations with instance paths'
            fail(where, f'unknown reference {value}; known ids: {hint}', 'instance.f-unknown-reference-value')

    snapshot = instance.path('tree_snapshot')
    people_data = load(snapshot / 'people.json', {})
    families_data = load(snapshot / 'families.json', {})
    if selected is not None and str(snapshot / 'people.json') not in selected and not isinstance(people_data, dict):
        people_data = {}
    if selected is not None and str(snapshot / 'families.json') not in selected and not isinstance(families_data, dict):
        families_data = {}
    people_rows = people_data.get('people', [])
    family_rows = families_data.get('families', [])
    if selected is not None:
        if str(snapshot / 'people.json') not in selected:
            people_rows = [p for p in people_rows if isinstance(p, dict)] if isinstance(people_rows, list) else []
        if str(snapshot / 'families.json') not in selected:
            family_rows = [p for p in family_rows if isinstance(p, dict)] if isinstance(family_rows, list) else []
    people = index([(snapshot, p) for p in people_rows], 'person')
    from familiar.tree.surnames import decision_errors
    metadata_path = instance.path('tree_metadata')
    metadata = load(metadata_path, {})
    for message in decision_errors(metadata):
        fail(metadata_path, message, 'instance.message')
    records_rows, memory_rows = rows('records'), rows('memory')
    records = index([(p, r) for p, r in records_rows if p in adopted or selected is not None], 'record')
    index([(p, r) for p, r in records_rows if p not in adopted and selected is None], 'working record')
    searches = rows('searches')
    search_index = index(searches, 'search')
    index(memory_rows, 'memory')
    items = index([(path, item) for path, row in memory_rows for item in (row.get('items', []) if isinstance(row.get('items', []), list) else [])], 'memory item')
    versions_rows, cases_rows, requests_rows = rows('versions'), rows('cases'), rows('questions')
    versions, cases = index(versions_rows, 'question'), index(cases_rows, 'case')
    requests, answers = index(requests_rows, 'request'), index(rows('answers'), 'answer')
    imports = index(rows('imports'), 'import')
    grounds = set(records) | set(items) | set(imports) | {'host'}

    def provenance(values, where, pack=False, search=False, against=False):
        if not isinstance(values, list) or not values:
            fail(where, 'nonempty provenance/source array required', 'instance.nonempty-provenance-source-array-required')
            return
        for value in values:
            if pack and isinstance(value, str) and re.fullmatch(r'pack:[^/\s]+/[^\s]+', value):
                continue
            if search and isinstance(value, str) and value.startswith('search:'):
                observation = search_index.get(value[7:], {})
                hits = observation.get('hits')
                from familiar.research.coverage import outcome
                controlled_zero = (against and type(hits) in (int, float) and hits == 0
                                   and observation.get('result_state') == 'zero-with-control'
                                   and outcome(observation) == 'zero-controlled')
                if not controlled_zero and (type(hits) not in (int, float) or not math.isfinite(hits) or hits <= 0
                        or observation.get('result_state') in {'access-gap', 'refused', 'not_ready', 'empty'}):
                    fail(where, f'{value}: weak argument requires saved findings, or a controlled zero for against', 'instance.f-value-weak-argument-requires-a-saved')
                continue
            ref(value, grounds, where)

    def walk(row, where):
        if isinstance(row, dict):
            for key, value in row.items():
                if key == 'provenance':
                    provenance(value, where)
                elif key == 'open_question':
                    ref(value, versions, where)
                else:
                    walk(value, where)
        elif isinstance(row, list):
            for value in row:
                walk(value, where)

    def chosen(path):
        return selected is None or str(path) in selected

    for ident, person in people.items():
        if not chosen(ident):
            continue
        required(person, 'id names events notes', ident)
        if person.get('living') is not None and type(person.get('living')) is not bool:
            fail(ident, 'living must be boolean or null (unknown)', 'instance.living-must-be-boolean-or-null-unknown')
        if person.get('sex') is not None and not isinstance(person['sex'], str):
            fail(ident, 'sex must be text or null', 'instance.sex-must-be-text-or-null')
        for name in person.get('names', []):
            required(name, 'type provenance', ident)
            inferred = name.get('inferred_parts', {})
            if not isinstance(inferred, dict) or set(inferred) - {'given', 'patronymic', 'surname'}:
                fail(ident, 'names[].inferred_parts: expected given/patronymic/surname object', 'instance.names-inferred-parts-expected-given-patronymic-surname')
            else:
                for part, explanation in inferred.items():
                    if not isinstance(explanation, dict) or not isinstance(explanation.get('basis'), str) or not explanation['basis'].strip():
                        fail(ident, f'names[].inferred_parts.{part}.basis: nonempty inference explanation required', 'instance.f-names-inferred-parts-part-basis-nonempty')
                    elif not name.get(part):
                        fail(ident, f'names[].inferred_parts.{part}: missing name part', 'instance.f-names-inferred-parts-part-missing-name')
            for key in ('given', 'surname'):
                if name.get(key) is not None and not isinstance(name[key], str):
                    fail(ident, f'name {key} must be text; empty means unrecorded', 'instance.f-name-key-must-be-text-empty')
            if name.get('patronymic') is not None and not isinstance(name['patronymic'], str):
                fail(ident, 'patronymic must be literal text', 'instance.patronymic-must-be-literal-text')
        for event in person.get('events', []):
            required(event, 'type provenance', ident)
            if event.get('date') is not None and not isinstance(event['date'], str):
                fail(ident, 'event date must be literal text; empty means unrecorded', 'instance.event-date-must-be-literal-text-empty')
        walk(person, ident)
    for family in family_rows if chosen(snapshot) else []:
        required(family, 'id children events provenance', snapshot)
        for member in [family.get('husband'), family.get('wife'), *family.get('children', [])]:
            ref(member, people, snapshot)
        walk(family, snapshot)
    for path, row in records_rows:
        if not chosen(path):
            continue
        required(row, 'id kind title source language fields', path)
        if not isinstance(row.get('fields'), dict):
            fail(path, 'fields must be a literal field map', 'instance.fields-must-be-a-literal-field-map')
        if (row.get('reading') is not None and not isinstance(row['reading'], str)) or not (row.get('reading') or row.get('fields')):
            fail(path, 'reading/fields: provide nonempty literal reading text or a nonempty fields object', 'instance.reading-fields-provide-nonempty-literal-reading-text')
        from .subjects import normalized
        if row.get('id') != normalized(path.stem):
            fail(path, 'record id must equal filename stem', 'instance.record-id-must-equal-filename-stem')
        if row.get('kind') not in ('home-paper', 'archive-record', 'index-entry'):
            fail(path, 'kind: expected home-paper, archive-record or index-entry', 'instance.kind-expected-home-paper-archive-record-or')
        if 'subjects' in row:
            if not isinstance(row['subjects'], list):
                fail(path, 'subjects must be an array', 'instance.subjects-must-be-an-array')
            else:
                for subject in row['subjects']:
                    if isinstance(subject, str):
                        ref(subject, people, path)
                        continue  # A card attachment supplies no invented written name or role.
                    if not required(subject, 'person role written', path, 'subjects[].'):
                        continue
                    ref(subject.get('person'), people, path)
        if row.get('kind') == 'index-entry' and row.get('saved_result') is not None:
            saved = row['saved_result']
            if not isinstance(saved, str) or not saved.strip():
                fail(path, 'saved_result must be a local path or null', 'instance.saved-result-must-be-a-local-path')
            elif not (instance.root / saved).resolve().is_relative_to(instance.root) or not (instance.root / saved).is_file():
                fail(path, 'saved_result file missing or outside instance', 'instance.saved-result-file-missing-or-outside-instance')
        for person in (row.get('people', {}).values() if isinstance(row.get('people'), dict) else []):
            ref(person, people, path)
        from .subjects import explicit_subjects
        try:
            for person in explicit_subjects(row):
                ref(person, people, path)
        except (ValueError, TypeError, AttributeError) as exc:
            fail(path, str(exc), 'instance.str-exc')
    for path, row in memory_rows:
        if not chosen(path):
            continue
        required(row, 'id told_by date items', path)
        for item in row.get('items', []):
            required(item, 'id text strength witness', path)
            if item.get('strength') not in {'firm', 'hearsay'}:
                fail(path, 'invalid memory strength', 'instance.invalid-memory-strength')
    for path, row in versions_rows:
        if not chosen(path):
            continue
        required(row, 'id title line people status unknown_weight versions tests', path)
        for person in row.get('people', []):
            ref(person, people, path)
        weights = [v.get('weight') for v in row.get('versions', [])] + [row.get('unknown_weight')]
        if not all(type(w) in (float, int) and 0 <= w <= 1 for w in weights):
            fail(path, 'weights must be numbers in [0,1]', 'instance.weights-must-be-numbers-in-0-1')
        elif abs(sum(weights) - 1) > 1e-8:
            fail(path, 'version weights plus unknown_weight must sum to one', 'instance.version-weights-plus-unknown-weight-must-sum')
        for version in row.get('versions', []):
            required(version, 'id label weight for against', path)
            for side in ('for', 'against'):
                arguments = version.get(side, [])
                if not isinstance(arguments, list):
                    continue  # required() reports the array error.
                for n, argument in enumerate(arguments):
                    field = f'versions[{version.get("id", "?")}].{side}[{n}]'
                    if not isinstance(argument, dict):
                        fail(path, field + ': expected object with text, sources, dependency_group', 'instance.field-expected-object-with-text-sources-dependency')
                        continue
                    for key in ('text', 'sources'):
                        if not argument.get(key):
                            fail(path, f'{field}.{key}: required', 'instance.f-field-key-required')
                    if not isinstance(argument.get('text'), str):
                        fail(path, field + '.text: expected text', 'instance.field-text-expected-text')
                    if not isinstance(argument.get('sources'), list):
                        fail(path, field + '.sources: expected array', 'instance.field-sources-expected-array')
                    else:
                        provenance(argument['sources'], path, pack=True, search=True, against=side == 'against')
    for path, row in cases_rows:
        if not chosen(path):
            continue
        required(row, 'id state question story_level basis', path)
        question_ref(row, path)
        if row.get('state') == 'waiting-for-family':
            ref(row.get('waiting_on'), requests, path)
        provenance(row.get('basis'), path)
    for path, row in requests_rows:
        if not chosen(path):
            continue
        required(row, 'id case question our_version paper why_this_paper outcomes addressee holder_reason state', path)
        ref(row.get('case'), cases, path)
        question_ref(row, path)
        if row.get('state') == 'answered':
            required(row, 'answer', path)
            ref(row.get('answer'), answers, path)
    from .correspondence import validate as validate_correspondence
    for path, row in rows('correspondence'):
        if not chosen(path):
            continue
        try:
            validate_correspondence(row)
        except (ValueError, TypeError, KeyError) as exc:
            fail(path, str(exc), 'instance.required-identity-privacy-fields-or-executable-collection-container')
            continue
        if path.stem != row['id']:
            fail(path, 'correspondence id differs from filename', 'instance.required-identity-privacy-fields-or-executable-collection')
        for person in row['people']:
            ref(person, people, path)
        if row.get('question'):
            question_ref(row, path)
        if row.get('request'):
            ref(row['request'], requests, path)
        for reply in row.get('replies', []):
            original = instance._inside(reply['original'])
            if not original.is_relative_to(instance.path('originals')) or not original.is_file():
                fail(path, 'reply original must exist inside originals', 'instance.required-identity-privacy-fields-or-executable-collection')
            else:
                raw = original.read_bytes()
                if reply.get('original_sha256') and hashlib.sha256(raw).hexdigest() != reply['original_sha256']:
                    fail(path, 'reply original bytes changed', 'instance.required-identity-privacy-fields-or-executable-collection')
                if not reply.get('transcript') and unicodedata.normalize('NFC', raw.decode('utf-8-sig')) != reply['text']:
                    fail(path, 'reply differs from literal original', 'instance.required-identity-privacy-fields-or-executable-collection')
    for path, row in rows('answers'):
        if not chosen(path):
            continue
        required(row, 'id request by at text', path)
        ref(row.get('request'), requests, path)
    for path, row in searches:
        if not chosen(path):
            continue
        required(row, 'id at by source question query coverage hits', path)
        question_ref(row, path)
        coverage = row.get('coverage', {})
        if not isinstance(coverage, dict):
            fail(path, 'coverage: expected object with years, forms, read, note', 'instance.coverage-expected-object-with-years-forms-read')
            coverage = {}
        for label, value in [('hits', row.get('hits')), ('coverage.read', coverage.get('read'))]:
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 9007199254740991):
                fail(path, f'search {label} must be a finite nonnegative count', 'instance.f-search-label-must-be-a-finite')
        from familiar.research.search_ledger import is_review
        if row.get('hits') == 0 and not is_review(row):
            required(row, 'meaning', path)
            required(coverage, 'years forms read note', path, 'coverage.')
            if row.get('result_state') not in {'access-gap', 'zero-uncontrolled'}:
                if (not coverage.get('years') or not coverage.get('forms') or
                        type(coverage.get('read')) not in (int, float) or not math.isfinite(coverage['read']) or coverage['read'] <= 0):
                    fail(path, 'coverage.years/coverage.forms/coverage.read: negative evidence requires nonempty years/forms and positive read coverage', 'instance.coverage-years-coverage-forms-coverage-read-negative')
            elif row.get('meaning') != row.get('result_state'):
                fail(path, 'access gap or uncontrolled zero cannot claim negative evidence; meaning must name result_state', 'instance.zero-read-access-gap-cannot-claim-negative')
    ledger_rows = {}
    for path, row in searches:
        if chosen(path):
            ledger_rows.setdefault(path, []).append(row)
    if ledger_rows:
        from familiar.research.search_ledger import findings as ledger_findings
        for where, message in ledger_findings(instance, ledger_rows):
            fail(where, message, 'instance.search-ledger')  # advice: the matrix reads these fields, nothing refuses without them
    from .gate import assertions
    from .model import DEFAULTS
    def nonstandard(value):
        raise ValueError('Nonstandard JSON number: ' + value)
    # Acceptance is a storage policy, not a list of favoured collections.
    seen = set()
    for key in DEFAULTS:
        if key in {'build', 'state', 'export', 'originals', 'captures', 'imports', 'media', 'media_archive'}:
            continue
        base = instance.path(key)
        for path in [base] if base.is_file() else sorted(base.rglob('*')):
            if not chosen(path) or not path.is_file() or path.suffix not in {'.json', '.jsonl'} or path in seen:
                continue
            seen.add(path)
            try:
                text = path.read_text(encoding='utf-8-sig')
                for n, line in enumerate(text.splitlines() if path.suffix == '.jsonl' else [text], 1):
                    if not line.strip():
                        continue
                    try:
                        value = json.loads(line, parse_constant=nonstandard)
                    except ValueError as exc:
                        fail(f'{path}:{n}' if path.suffix == '.jsonl' else path, str(exc), 'instance.str-exc')
                        continue
                    try:
                        for error in assertions(value):
                            fail(path, error, 'instance.error')
                        from .research_forms import numeric_errors
                        for error in set(numeric_errors(value)):
                            fail(path, error, 'instance.error')
                    except (TypeError, AttributeError, KeyError) as exc:
                        fail(path, f'malformed form: {exc}', 'instance.f-malformed-form-exc')
            except (ValueError, OSError) as exc:
                fail(path, str(exc), 'instance.str-exc')
    contribution_files = list(instance.path('contributions').glob('*/*.json'))
    if contribution_files and (selected is None or any(chosen(path) for path in contribution_files)):
        from familiar.tree.builder import _snapshot_graph
        graph = _snapshot_graph(instance, people_data, apply_identity=False)
        for error in graph['research']['contributions']['errors']:
            fail(instance.root / error['file'], error['error'], 'instance.contribution-not-applied')
    for value in (people_rows, family_rows, [r for _, r in versions_rows]) if selected is None else []:
        for error in assertions(value):
            fail(snapshot, error, 'instance.error')
    privacy = load(instance.path('privacy'), {})
    for decision in privacy.get('life_decisions', []) if chosen('privacy') else []:
        if not required(decision, 'person status by at', 'privacy'):
            continue
        ref(decision.get('person'), people, 'privacy')
        if decision.get('status') not in {'dead', 'living', 'unknown'}:
            fail('privacy', 'life decision status must be dead, living or unknown', 'instance.life-decision-status-must-be-dead-living')
        if not all(isinstance(decision.get(k), str) and decision[k].strip() for k in ('basis', 'by', 'at')):
            fail('privacy', 'life decision needs a written basis, author and date', 'instance.life-decision-needs-a-written-basis-author')
        if 'revoked' in decision and type(decision['revoked']) is not bool:
            fail('privacy', 'life decision revoked must be boolean', 'instance.life-decision-revoked-must-be-boolean')
    for permission in privacy.get('living', []) if chosen('privacy') else []:
        if not required(permission, 'id allowed', 'privacy'):
            continue
        ref(permission.get('id'), people, 'privacy')
        allowed = permission.get('allowed')
        if not isinstance(allowed, list) or not all(isinstance(x, str) and x.strip() for x in allowed):
            fail('privacy', 'allowed must list kinds of information in family words', 'instance.allowed-must-list-kinds-of-information-in')
        else:
            from .publication import INFO_FIELDS
            if set(allowed) - INFO_FIELDS:
                fail('privacy', 'allowed must use canonical publication field identifiers; addresses and documents are never permitted', 'instance.allowed-must-use-canonical-publication-field-identifiers')
        if allowed:
            required(permission.get('consent'), 'by at', 'privacy')
    evidence = load(instance.path('evidence'), {})
    for source in evidence.get('sources', []) if chosen(instance.path('evidence')) else []:
        required(source, 'id kind record', 'evidence source')
        if source.get('kind') == 'memory':
            ref(source.get('record'), items, 'evidence source')
        elif source.get('kind') == 'import':
            ref(source.get('record'), imports, 'evidence source')
        else:
            ref(source.get('record'), records, 'evidence source')
    for edge in evidence.get('edges', []) if chosen(instance.path('evidence')) else []:
        required(edge, 'type from to sources confidence', 'evidence')
        ref(edge.get('from'), people, 'evidence')
        ref(edge.get('to'), people, 'evidence')
        provenance(edge.get('sources'), 'evidence')
    chapter_count = 0
    feeds = instance.path('feeds')
    feed_ids = set()
    for directory in sorted(feeds.iterdir()) if feeds.exists() else []:
        if selected is not None and not any(str(p) in selected for p in directory.glob('*.json')):
            continue
        if not directory.is_dir() or directory.name.startswith('.'):
            continue
        if not (directory / 'feed.json').is_file():
            continue
        head = load(directory / 'feed.json', {})
        chapters = load(directory / 'chapters.json', [])
        for error in assertions(chapters):
            fail(directory / 'chapters.json', error, 'instance.error')
        docs = load(directory / 'documents.json', {})
        required(head, 'id title lead persons profile', directory / 'feed.json')
        if head.get('id') in feed_ids:
            fail(directory / 'feed.json', 'duplicate feed id', 'instance.duplicate-feed-id')
        feed_ids.add(head.get('id'))
        if head.get('id') != directory.name:
            fail(directory / 'feed.json', 'feed id must match its directory', 'instance.feed-id-must-match-its-directory')
        aliases = head.get('persons', {})
        for person in aliases.values():
            ref(person, people, directory / 'feed.json')
        chapter_ids = set()
        for chapter in chapters:
            required(chapter, 'id title text people records', directory / 'chapters.json')
            cid = chapter.get('id')
            if cid in chapter_ids or (isinstance(cid, str) and (cid.startswith('__') or '/' in cid or '@' in cid)):
                fail(directory / 'chapters.json', 'duplicate or reserved chapter id: ' + str(cid), 'instance.duplicate-or-reserved-chapter-id-str-cid')
            chapter_ids.add(cid)
            for person in chapter.get('people', []):
                ref(person, aliases, directory / 'chapters.json')
            for record in chapter.get('records', []):
                ref(record.get('doc'), docs, directory / 'chapters.json')
            chapter_count += bool(chapter.get('text'))
        pictures = load(directory / 'pictures.json', {})
        images = [v for v in pictures.values() if isinstance(v, dict)]
        images += [c['picture'] for c in chapters if isinstance(c.get('picture'), dict)]
        for image in images:
            if 'kind' in image and image['kind'] not in {'period-picture', 'family-photograph', 'document-scan', 'generated-reconstruction', 'ours-drawing', 'reconstruction', 'generated'}:
                fail(directory / 'pictures.json', 'unknown image kind', 'instance.unknown-image-kind')
            if 'subjects' in image:
                if not isinstance(image['subjects'], list):
                    fail(directory / 'pictures.json', 'image subjects must be an array', 'instance.image-subjects-must-be-an-array')
                else:
                    for subject in image['subjects']:
                        if subject not in aliases and subject not in people:
                            fail(directory / 'pictures.json', 'unknown image subject', 'instance.unknown-image-subject')
        for ident, doc in docs.items():
            if ident.startswith('_'):
                continue
            required(doc, 'record caption source snippets', directory / 'documents.json')
            target = doc.get('record')
            if target not in records:
                fail(directory / 'documents.json', f'unknown record {target}', 'instance.f-unknown-record-target')
    first = ([] if people else ['nonempty people']) + ([] if chapter_count else ['authored chapter'])
    cycle = [key for key, present in [('cases', cases), ('versions', versions), ('evidence', evidence.get('edges')), ('searches', searches)] if not present] if selected is None else []
    if errors:
        first.append('resolve validation errors')
        cycle.append('resolve validation errors')
    research_work = [dict(pair) for pair in dict.fromkeys(tuple(e.items()) for e in research_work)]
    return {'research_ready': bool(people) and not errors,
            'research_next': 'researcher: memory-first; name one bridge paper before searching indexes' if people and not errors else 'lead: resolve missing people or validation errors',
            'valid': not errors, 'errors': errors, 'advice': advice,
            'research_in_progress': {'count': len(research_work),
                                     'paths': sorted(work_paths),
                                     'findings': research_work},
            'data_files': data_files, 'first_chapter_missing': first,
            'full_cycle_missing': cycle, 'unverified': ['historical truth and editorial judgement',
                                                     'media bytes and feed presentation: use feed check']}
