# START_MODULE_CONTRACT: MOD-INSTANCE-RESEARCH-FORMS
# PURPOSE: Protect stored containers, finite probabilities and auditable acceptance decisions.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - ask storage diagnostics respect the instance asks override [review: engine lead]
# - accepted assertions at every ingestion surface need strong status and auditable grounds [review: engine lead]
# - optional interest stays separate from probability and reports malformed fields [review: engine lead]
# - a story choice by interest is allowed only among versions of at least half the heaviest weight [review: engine lead]
# - unknown numeric metadata is allowed; nonfinite numbers and invalid probabilities are refused [review: engine lead]
# - file container errors name the file, expected shape and complete form command [review: engine lead]
# CHANGES_WITH:
# - MOD-METHOD-VOCABULARY (single enum and numeric-domain authority)
# - MOD-FAMILY-GATE (the shared family boundary contract)
# - docs/PRD.md#FORMS
# :END_MODULE_CONTRACT
import math
import tomllib
from datetime import date

from familiar.rules.roles import method_root

VOCABULARY = tomllib.loads((method_root() / 'vocabulary.toml').read_text(encoding='utf-8'))

REVIEW_CLASSES = frozenset(VOCABULARY['enums']['review_classes'])
REVIEW_VERDICTS = frozenset(VOCABULARY['enums']['review_verdicts'])
REVIEW_READERS = frozenset(VOCABULARY['enums']['review_readers'])
REVIEW_WEIGHTS = frozenset(VOCABULARY['enums']['review_weights'])
CASE_STATES = frozenset(VOCABULARY['enums']['case_states'])
OUTPUT_STATES = frozenset(VOCABULARY['enums']['output_states'])
CLEAN, PREVIEW, STALE = VOCABULARY['enums']['output_states'][:3]


def require_container(path, value, *, form=None):
    # Corpus record ids may themselves be "documents" or "evidence". Apply a
    # feed schema only beside feed.json; evidence callers select it explicitly.
    form = form or (path.stem if path.name in {'documents.json', 'chapters.json'}
                    and (path.parent / 'feed.json').is_file() else None)
    shapes = {'documents': (dict, 'объект по идентификаторам: {"paper": {"record": "paper", "caption": "…", "source": "…", "snippets": []}}'),
              'chapters': (list, 'массив объектов глав: [{"id": "first", "title": "…", "text": "…", "people": [], "records": []}]'),
              'evidence': (dict, 'объект: {"sources": [], "edges": []}')}
    if form not in shapes:
        return value
    kind, example = shapes[form]
    if not isinstance(value, kind):
        raise ValueError(f'{path}: ожидается {example}; полный пример: familiar research form {form}.')  # noqa: TRY004 -- collected form diagnostic
    if form == 'documents' and any(not isinstance(v, dict) for k, v in value.items() if not k.startswith('_')):
        raise ValueError(f'{path}: каждый идентификатор документа должен содержать объект; пример: familiar research form documents.')
    if form == 'chapters' and any(not isinstance(v, dict) for v in value):
        raise ValueError(f'{path}: каждый элемент массива должен быть объектом главы; пример: familiar research form chapters.')
    if form == 'evidence':
        for key in ('sources', 'edges'):
            if key in value and (not isinstance(value[key], list) or any(not isinstance(v, dict) for v in value[key])):
                raise ValueError(f'{path}: {key} должен быть массивом объектов; пример: familiar research form evidence.')
    return value


def request_storage_errors(instance):
    """Diagnose the tempting alternate folder without treating it as an input."""
    misplaced = instance._inside('family/requests')
    questions = instance.path('asks')
    if misplaced.is_relative_to(questions):
        return []
    return [(path, (f'Ask stored outside paths.asks: move it to {questions}; '
                    'inspect configured storage with instance paths.'))
            for path in sorted(misplaced.rglob('*'))
            if path.is_file() and path.suffix in {'.json', '.jsonl'}
            and not path.is_relative_to(questions)
            and not any(p.startswith('.') for p in path.relative_to(misplaced).parts)]


def numeric_errors(value, key='', domain=None):
    """Protect stored probability and finite numbers; unknown metadata is allowed."""
    if isinstance(value, dict):
        for name, child in value.items():
            yield from numeric_errors(child, name)
    elif isinstance(value, list):
        for child in value:
            yield from numeric_errors(child, key)
    elif type(value) in (int, float) and not math.isfinite(value):
        yield f'{key}: number must be finite'
    elif key in {'weight', 'unknown_weight', 'probability'} and (
            type(value) not in (int, float) or not 0 <= value <= 1):
        yield f'{key}: probability must be a finite number in [0,1]'


def interest_errors(row):
    """Editorial interest never changes identity weight or removes an observation."""
    entries = [('interest', row.get('interest'))]
    entries += [(f'versions[{n}].interest', v.get('interest'))
                for n, v in enumerate(row.get('versions', [])) if isinstance(v, dict)]
    for field, value in entries:
        if value is None:
            continue
        if not isinstance(value, dict):
            yield field, 'expected object with level and tell, or null'
            continue
        level, tell = value.get('level'), value.get('tell')
        if level is not None and (type(level) not in (int, float) or not math.isfinite(level) or not 0 <= level <= 1):
            yield field + '.level', 'must be a finite number in [0,1] or null'
        if tell is not None and not isinstance(tell, str):
            yield field + '.tell', 'must be text or null'


STORY_BY = ('weight', 'interest')
CLOSED_VERSIONS = {'refuted', 'rejected', 'disproved'}


def story_leader(row):
    """(id, weight) of the heaviest open version: the one told by default."""
    options = [(v['weight'], v['id']) for v in row.get('versions', []) if isinstance(v, dict)
               and type(v.get('weight')) in (int, float) and v.get('state') not in CLOSED_VERSIONS and v.get('id')]
    return max(options, key=lambda item: item[0])[::-1] if options else (None, None)


def story_errors(row):
    """The version the story tells. Interest chooses only among close rivals and never touches a weight."""
    choice = row.get('story_choice')
    if choice is None:
        return
    if not isinstance(choice, dict) or set(choice) - {'version', 'by', 'basis', 'date'}:
        yield 'story_choice: expected version, by, basis, date'
        return
    options = {v.get('id'): v for v in row.get('versions', []) if isinstance(v, dict)}
    chosen = options.get(choice.get('version'))
    if chosen is None:
        yield f"story_choice.version {choice.get('version')!r} is not a version of this question"
        return
    if choice.get('by') not in STORY_BY:
        yield 'story_choice.by must be weight or interest'
    if not isinstance(choice.get('basis'), str) or not choice['basis'].strip():
        yield 'story_choice.basis: one sentence on why this version leads the story'
    try:
        date.fromisoformat(choice.get('date'))
    except (TypeError, ValueError):
        yield 'story_choice.date must be YYYY-MM-DD'
    if chosen.get('state') in CLOSED_VERSIONS:
        yield f"story_choice: {chosen['id']} is {chosen['state']}; a story never tells a refuted version"
        return
    top, heaviest = story_leader(row)
    weight = chosen.get('weight')
    if top is None or type(weight) not in (int, float):
        return
    if choice.get('by') == 'weight' and weight < heaviest:
        yield (f"story_choice: {chosen['id']} ({weight:g}) is chosen by weight, but {top} weighs {heaviest:g}; "
               f"tell {top}, or choose by interest among versions of at least {heaviest / 2:g}")
    if choice.get('by') == 'interest' and weight < heaviest / 2:
        yield (f"story_choice: {chosen['id']} ({weight:g}) is chosen by interest, but it is weaker than half of "
               f"{top} ({heaviest:g}); interest chooses only among versions of at least {heaviest / 2:g}")


def acceptance_error(fact):
    """Accepted assertions require a documentary decision, at every entry surface."""
    if not fact.get('accepted') and fact.get('status') not in {'accepted', 'accepted_evidence'}:
        return None
    if 'accepted' in fact and (type(fact['accepted']) is not bool or fact['accepted'] is False):
        return 'Contradictory accepted flag and status.'
    if fact.get('status') not in {'verified', 'accepted', 'accepted_evidence'}:
        return 'A weak version is marked as accepted.'
    if type(fact.get('weight')) not in (int, float) or not math.isfinite(fact['weight']) or not .5 <= fact['weight'] <= 1:
        return 'Accepted assertion weight must be a finite number in [0.5,1].'
    if fact.get('confidence') in {'possible', 'hypothesis', 'weak'} or (isinstance(fact.get('weight'), (int, float)) and fact['weight'] < .5):
        return 'A weak version is marked as accepted.'
    if not fact.get('basis') or not fact.get('sources') or not fact.get('decision'):
        return 'Accepted assertion requires sources, basis and an auditable decision.'
    return None
