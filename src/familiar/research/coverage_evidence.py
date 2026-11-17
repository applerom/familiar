# START_MODULE_CONTRACT: MOD-RESEARCH-COVERAGE-EVIDENCE
# PURPOSE: Recover accepted record links and local review assessments without manufacturing source visits.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - analysis and review never supply search strength, access or negative coverage [review: engine lead]
# - accepted tree references resolve exact records or document URLs, never a whole source domain [review: engine lead]
# - local review assessments retain their provenance and do not become accepted tree facts [review: engine lead]
# :END_MODULE_CONTRACT
import json
import re
from urllib.parse import unquote, urlsplit


def analytical(record):
    if record.get('record_role') in {'analysis', 'catalogue'}:
        return True
    # Carry over old comparison tables: their target ids and weights describe
    # hypotheses, not people read in the external source. No filename heuristic.
    fields = record.get('fields') or {}
    return isinstance(fields, dict) and not record.get('person') and any(
        isinstance(rows, list) and any(isinstance(r, dict) and 'target_ids' in r and 'weights' in r and 'record' in r for r in rows)
        for rows in fields.values())


def references(value):
    """Exact ids/paths and document URLs, including old 'site/ + page' locators."""
    if isinstance(value, dict):
        return set().union(*(references(value[k]) for k in ('record', 'records', 'url', 'locator', 'archive_ref') if k in value), set())
    if isinstance(value, list):
        return set().union(*(references(v) for v in value), set())
    if not isinstance(value, str):
        return set()
    raw = re.sub(r'(https?://[^\s;]+/)\s*\+\s*([^\s;]+)', r'\1\2', value)
    result = set()
    for url in re.findall(r'https?://[^\s;<>"\u00ab\u00bb]+', raw):
        parsed = urlsplit(unquote(url))
        if parsed.path.strip('/'):
            result.add(parsed.netloc.lower().removeprefix('www.') + parsed.path.rstrip('/') + ('?' + parsed.query if parsed.query else ''))
    if not re.search(r'\s|https?://', value):
        result.add(value.removeprefix('record:').removeprefix('records/').removesuffix('.json'))
    return result


def accepted_links(tree):
    result = {}
    for pid, person in tree.graph['people'].items():
        assertions = person.get('facts', []) + [h.get('decision', {}) for h in person.get('identityHistory', [])]
        for fact in assertions:
            if fact.get('status') not in {'verified', 'accepted', 'accepted_evidence', 'accepted_family_confirmation'}:
                continue
            if fact.get('assesses_identity') is False or fact.get('scope') in {'search', 'relationship'}:
                continue
            for ref in fact.get('sources', []):
                keys = references(ref) | references(tree.graph.get('sources', {}).get(ref, {}))
                for key in keys:
                    result.setdefault(key, set()).add(pid)
    return result


def review_links(instance, row):
    """Explicit assessments; old saved comparison rows remain readable as reviews."""
    for link in row.get('record_links', []):
        if isinstance(link, dict) and link.get('status') in {'same', 'other', 'unestablished', 'mention', 'conflict'}:
            yield link
    # Legacy reports sometimes compare several people in one table. A table's
    # singular pronoun cannot safely decide which of those people it addresses.
    if len(row.get('people', [])) != 1:
        return
    for saved in row.get('saved', []):
        if not isinstance(saved, str):
            continue
        path = (instance.root / saved).resolve()
        if not path.is_relative_to(instance.root) or path.suffix != '.json':
            continue
        try:
            report = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        fields = report.get('fields', {}) if isinstance(report, dict) else {}
        for rows in fields.values() if isinstance(fields, dict) else []:
            for item in rows if isinstance(rows, list) else []:
                if not isinstance(item, dict):
                    continue
                verdict = item.get('вывод', '')
                status = ('other' if re.match(r'^не (?:он|она)(?:\b)', verdict) else
                          'same' if re.match(r'^(?:он|она)(?:\b)', verdict) else None)
                if status:
                    # Delimiters separate exact record ids; prose/approximate
                    # locators are intentionally left unresolved.
                    for ref in re.split(r'[;,]|\s+\(', item.get('запись', '')):
                        ref = ref.strip()
                        if ref and not re.search(r'\s', ref):
                            yield {'record': ref, 'person': row['people'][0], 'status': status}
