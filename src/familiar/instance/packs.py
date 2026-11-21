# START_MODULE_CONTRACT: MOD-INSTANCE-PACKS
# PURPOSE: Resolve shared pack identities independently of family storage and enforce composition boundaries.
# PRD_REF: docs/PRD.md#REGION-PACK
# INVARIANTS:
# - pack kinds and duplicate source ids fail at load time [review: engine lead]
# - a new registry question becomes an exact-id implicit gap [review: engine lead]
# - year selection keeps referenced sources of unknown coverage with an explicit label [review: engine lead]
# CHANGES_WITH:
# - pyproject.toml (bundled regions)
# :END_MODULE_CONTRACT
import json
import os
import pickle
import re
import tomllib
from functools import lru_cache
from pathlib import Path

from .model import require


def read(path):
    return pickle.loads(_parse(path.read_bytes()))


@lru_cache(maxsize=64)
def _parse(content):
    # Every new instance reads its packs; parse each distinct content once per process.
    return pickle.dumps(tomllib.loads(content.decode('utf-8')), pickle.HIGHEST_PROTOCOL)


def bundled_root():
    installed = Path(__file__).resolve().parents[1] / '_regions'
    return installed if installed.is_dir() else Path(__file__).resolve().parents[3] / 'regions'


def load_packs(instance, mapping=None):
    mapping = json.loads(os.environ.get('FAMILIAR_HOST_PACKS', '{}')) if mapping is None else mapping
    require(isinstance(mapping, dict), 'host packs must map ids to absolute paths')
    for key, value in mapping.items():
        require(isinstance(key, str) and isinstance(value, str) and Path(value).is_absolute(),
                'host pack mappings must be absolute paths')

    def load(ref, kind):
        if ref in mapping:
            path, origin = Path(mapping[ref]).resolve(), 'host'
        elif re.fullmatch(r'[A-Za-z0-9_-]+', ref) and (bundled_root() / ref).is_dir():
            path, origin = bundled_root() / ref, 'bundled'
        else:
            path, origin = instance._inside(ref), 'family'
        file = path / 'pack.toml' if path.is_dir() else path
        data = read(file)
        # Pre-passport local region layers retain their historical meaning.
        require(data.get('pack', {}).get('kind', 'region') == kind, f'wrong pack kind: {ref}')
        return {'id': ref, 'path': file, 'origin': origin, 'data': data}

    regions = [load(ref, 'region') for ref in instance.region_packs]
    languages = {tag: load(ref, 'language') for tag, ref in instance.language_packs.items()}
    seen = set()
    for pack in regions:
        file = pack['data'].get('pack', {}).get('files', {}).get('sources')
        if not file:
            continue
        path = pack_file(pack, file)
        for source in read(path).get('source', []):
            ident = source['id']
            require(ident not in seen, f'duplicate source id: {ident}')
            seen.add(ident)
    return regions, languages


def pack_file(pack, relative):
    root = pack['path'].parent.resolve()
    path = (root / relative).resolve()
    require(path.is_relative_to(root), 'pack file leaves pack root')
    return path


def question_coverage(pack, questions=None):
    """Registry growth creates visible implicit gaps, never invalidates old packs."""
    questions = json.loads((bundled_root() / 'questions.json').read_text(encoding='utf-8')) if questions is None else questions
    name = pack['data'].get('pack', {}).get('files', {}).get('answers')
    text = pack_file(pack, name).read_text(encoding='utf-8') if name else ''
    sections = re.split(r'^## (RP-[0-9]+)\s*$', text, flags=re.MULTILINE)
    answers = {sections[i]: sections[i + 1].strip() for i in range(1, len(sections), 2)}
    declared = {}
    for gap in pack['data'].get('gap', []):
        for qid in re.findall(r'(?<![\w-])RP-[0-9]+(?![\w-])', gap['what']):
            declared[qid] = gap
    return {q['id']: ({'state': 'answered', 'text': answers[q['id']]} if q['id'] in answers else
                     {'state': 'gap', 'implicit': q['id'] not in declared,
                      **declared.get(q['id'], {'what': q['id'] + ': no answer in this pack',
                                               'next': 'Keeper: research the registered question.'})}) for q in questions}


def answer_sources(pack, text, country, year):
    """Source cards cited by an answer; unknown years are candidates, not exclusions."""
    name = pack['data'].get('pack', {}).get('files', {}).get('sources')
    if not name:
        return []
    ids = set(re.findall(r'\bsource: ([A-Za-z0-9_-]+)', text))
    result = []
    for source in read(pack_file(pack, name)).get('source', []):
        if source['id'] not in ids or country not in source.get('countries', []):
            continue
        years = source.get('years', [])
        if years and not years[0] <= year <= years[1]:
            continue
        result.append({**source, 'years_note': f'{years[0]}–{years[1]}' if years else 'годы неизвестны'})
    return result
