# START_MODULE_CONTRACT: MOD-SOURCE-SEARCH
# PURPOSE: Turn one host-authorized recipe query into an auditable family search record.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - denied host permission never invokes transport [review: engine lead]
# - observations save beside incomplete unrelated drafts; absent recipes name region configuration [review: engine lead]
# - a saved observation carries the ledger form: people, the recipe source id, by as {agent, model, effort} [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE
# - MOD-INSTANCE-PACKS
# - MOD-SEARCH-LEDGER
# :END_MODULE_CONTRACT
import re
import uuid
from datetime import UTC, datetime
from urllib.parse import urlencode, urlsplit

from familiar.instance import gate
from familiar.instance.packs import pack_file, read

from . import search_readers as readers
from .search_ledger import parse_by
from .search_variants import expand


def recipe_for(instance, source):
    found = []
    for pack in instance.packs:
        files = pack['data'].get('pack', {}).get('files', {})
        if 'recipes' not in files:
            continue
        index = pack_file(pack, files['recipes'])
        for entry in read(index).get('recipe', []):
            if entry['id'] == source:
                recipe = read(pack_file(pack, str(index.relative_to(pack['path'].parent).parent / entry['file'])))['recipe']
                found.append((recipe, pack))
    if not found:
        raise ValueError(f'Нет рецепта источника {source} в region_packs. '
                         'Объявите пакет края с этим рецептом в familiar.toml '
                         '(для geneteka: region_packs = ["belarus-podlasie"]); языковой пакет рецептов не добавляет.')
    if len(found) > 1:
        raise ValueError(f'Несколько рецептов источника {source}: ' + ', '.join(p['id'] for _, p in found) +
                         '; оставьте одно объявление в region_packs.')
    return found[0]


def parse(recipe, response, params):
    html, text = response.get('html', ''), response.get('text', '')
    status = response.get('status', 200)
    if status in (401, 403, 429) or '/paywall' in urlsplit(response.get('url', '')).path.lower() or re.search(
            r'g-recaptcha|h-captcha|cf-challenge|cf-chl-|_Incapsula_Resource|verify you are human|captcha|войдите', html + '\n' + text, re.IGNORECASE):
        return 'refused', None, []
    if status >= 400:
        return 'not_ready', None, []
    name = recipe['list_reader']
    if name == 'geneteka':
        result = readers.geneteka_read(response.get('responses', []), params, known=None)
    elif name == 'pamyat-naroda':
        result = readers.pamyat_read(response.get('responses', []), params)
    elif name in {'szukajwarchiwach', 'obd-memorial'}:
        result = {'szukajwarchiwach': readers.szukaj_read, 'obd-memorial': readers.obd_read}[name](html)
    else:
        raise ValueError('Unsupported list reader: ' + name)
    return (result[0] or 'not_ready', result[1], result[2])


@gate.boundary('writer')
def search(instance, source, params, *, host, question, by, years, forms,
           read_count=0, saved=(), note='Captured index only; documents not read', people=()):
    recipe, pack = recipe_for(instance, source)
    query = {key: value.format_map(params) for key, value in recipe.get('parameters', {}).items()}
    url = recipe['url'] + ('&' if '?' in recipe['url'] else '?') + urlencode(query)
    parts = urlsplit(url)
    if parts.scheme not in {'http', 'https'} or not parts.hostname or parts.username or parts.password:
        raise ValueError('Recipe URL must be HTTP(S) without credentials')
    # Host owns sessions, permission and shared pacing. No transport before approval.
    token = host.authorize(instance.id, source, url)
    if token is None or token is False:
        raise PermissionError(f'Хозяин отказал в доступе к {source}; получите его разрешение в шлюзе доступа. '
                              'Для разрешённого локального повтора добавьте --allow-replay.')
    try:
        response = host.fetch(token, url)
        state, count, lines = parse(recipe, response, params)
    except Exception:
        host.report(token, 'error')
        raise
    host.report(token, 'captcha' if state == 'refused' and response.get('status', 200) == 200 else response.get('status', 200))
    # Header lines are metadata, never counted as inspected rows.
    available = len([line for line in lines if not line.startswith('#')])
    if type(read_count) is not int or not 0 <= read_count <= available:
        raise ValueError('read_count exceeds captured rows')
    if state not in {'results', 'empty'} and read_count:
        raise ValueError('Unavailable response cannot be read coverage')
    row = {'id': 's-' + uuid.uuid4().hex, 'at': datetime.now(UTC).isoformat(),
               'by': parse_by(by), 'people': list(people), 'source': source, 'question': question, 'query': params,
               'hits': count, 'result_state': state, 'saved': list(saved),
               'coverage': {'years': years, 'forms': forms, 'read': read_count, 'total': count,
                             'returned': available, 'note': note},
               'provenance': {'pack': pack['id'], 'version': pack['data']['pack'].get('version'), 'recipe': recipe['id']}}
    row['candidate_forms'] = {key: expand(instance, value, key) for key, value in params.items()
                              if key in {'given_name', 'surname', 'place'} and value}
    if state == 'empty':
        # A loaded zero is one inspected index answer, not a read document.
        row['coverage'].update(read=1, unit='index-response')
        row['meaning'] = 'No entries in this query; no claim beyond this index coverage'
    elif state in {'not_ready', 'refused'}:
        row.update(hits=0, observed_hits=None, result_state='access-gap', meaning='access-gap', access_state=state)
    return save_search(instance, row)


@gate.boundary('writer')
def save_search(instance, row):
    """Validate the observation and its references, independent of unrelated drafts."""
    if not isinstance(row.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]+', row['id']):
        raise ValueError('Search id must be a confined filename')
    from familiar.instance.writer import mutate
    path = instance.path('searches') / (row['id'] + '.json')
    mutate(instance, {path: row}, exclusive=[path])
    return row
