# START_MODULE_CONTRACT: MOD-RESEARCH-COVERAGE-QUALITY
# PURPOSE: Keep query quality and latest source availability separate from findings and executor strength.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - a dubious query and an access refusal never supply negative evidence [review: engine lead]
# - only recorded local observations inform availability; no host state is guessed [review: engine lead]
# :END_MODULE_CONTRACT
import re

from .coverage_context import text
from .search_ledger import row_tokens


def query_issues(row, tree=None):
    coverage = row.get('coverage') if isinstance(row.get('coverage'), dict) else {}
    quality = row.get('query_quality') or coverage.get('query_quality')
    issues = []
    if quality in ('dubious', 'invalid', 'substring', 'composite'):
        issues.append(str(quality))
    query = row.get('query')
    note = text([row.get('meaning'), coverage.get('note')])
    if isinstance(query, dict) and query.get('syntax_probe'):
        issues.append('syntax-probe')
    if re.search(r'(?i)по подстрок|совпадени\w* подстрок|подстрока .{0,100}друг|substring|только похожие документы|только подстроч', note):
        issues.append('substring-or-similar-results')
    if tree and isinstance(query, dict):
        for key, value in query.items():
            if not isinstance(value, str) or not re.search(r'surname|last.?name|olsearch-name|фамили', key, re.I):
                continue
            words = set(row_tokens({'query': value}))
            known = {w for w in words if any(w in p['surnames'] for p in tree.people.values())}
            if len(known) > 1:
                issues.append('multiple-surnames-in-one-field')
    return sorted(set(issues))


def availability(row, gap):
    raw = text([row.get('coverage'), row.get('meaning'), row.get('error'), row.get('status')])
    code = re.search(r'(?<!\d)(401|403|429|500|502|503|504)(?!\d)', raw)
    refusal = code.group(1) if code else 'captcha' if re.search(r'(?i)captcha|капч', raw) else 'not-ready' if re.search(r'not_ready|не загруз', raw) else row.get('result_state')
    query = row.get('query')
    route = 'search'
    if isinstance(query, dict) and query.get('url') and not any(re.search(r'name|surname|фамили|имя|search', k, re.I) for k in query):
        from urllib.parse import urlsplit
        route = 'page' if urlsplit(str(query['url'])).path.strip('/') else 'search'
    return {'at': str(row.get('at') or ''), 'state': 'stopped' if gap else 'available',
            'kind': refusal if gap else None, 'search': row.get('id'), 'route': route}
