# START_MODULE_CONTRACT: MOD-SEARCH-READERS
# PURPOSE: Interpret captured source responses without browser, network or family database access.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - captured index rows retain the pilot reader semantics [review: engine lead]
# - a malformed or failed index response never supplies negative evidence [review: engine lead]
# CHANGES_WITH:
# - regions/belarus-podlasie/recipes/index.toml
# :END_MODULE_CONTRACT
import json
import re
from html import unescape as _unescape
from urllib.parse import parse_qs as _parse_qs
from urllib.parse import urlsplit as _urlsplit

PN = 'https://pamyat-naroda.ru/heroes'

def _first(v):
    return (v[0] if v else '') if isinstance(v, list) else (v or '')

def _all(v):
    return ' / '.join(dict.fromkeys(x for x in v if x)) if isinstance(v, list) else (v or '')

def _index_count(response, count):
    data = response.get('data')
    if (response.get('error') or response.get('errors') or response.get('success') is False or
            response.get('status') in ('error', 'failed') or not isinstance(data, list) or
            isinstance(count, bool) or not isinstance(count, (int, str)) or
            not re.fullmatch(r'[0-9]+', str(count))):
        return None
    total = int(count)
    return total if total >= len(data) else None

def pamyat_read(responses, params=None, final=False):
    """responses: [(url, post, body)] from pamyat-naroda.ru/entrypoint/api/. Only 'heroes/search' counts;
    the last one wins. metadata.total is capped at 10000 by the site (Elasticsearch)."""
    found = None
    for url, post, body in responses:
        if '"heroes/search"' not in (post or ''):
            continue
        try:
            found = json.loads(body)
        except ValueError:
            continue
    if not found or found.get('status') != 'success':
        return None, None, []
    meta = found.get('metadata')
    total = _index_count(found, meta.get('total')) if isinstance(meta, dict) else None
    if total is None:
        return None, None, []
    if total == 0:
        return 'empty', 0, []
    rows = [f'# найдено {total}{" (потолок сайта, на деле больше)" if total >= 10000 else ""}; страница {meta.get("page")} из {meta.get("max_page")}, по {meta.get("size")}']
    for hit in found.get('data') or []:
        s = hit.get('_source') or {}
        name = ' '.join(x for x in (_all(s.get('last_name')), _all(s.get('first_name')), _all(s.get('middle_name'))) if x)
        fate = ' '.join(x for x in (_first(s.get('prichina_vibitiya')), _first(s.get('data_vibitiya')) or _first(s.get('date_death'))) if x)
        rows.append(' | '.join(x for x in (
            name, 'р. ' + _first(s.get('date_birth')) if s.get('date_birth') else '', _first(s.get('place_birth')),
            _first(s.get('rank')), 'призыв: ' + _first(s.get('data_i_mesto_priziva')) if s.get('data_i_mesto_priziva') else '',
            fate, f'{hit.get("_index")}/{s.get("__type") or hit.get("_type")}',
            f'{PN}/{hit.get("_index")}-{s.get("__type") or hit.get("_type")}{hit.get("_id")}/') if x))
    return 'results', total, rows

def _szukaj_clean(value):
    from html import unescape
    return ' '.join(unescape(re.sub(r'<[^>]+>', ' ', value)).split())

def szukaj_count(html):
    """(state, count) from a results page: the number beside the checked material-type tab (All / Textual records / …).
    None when the page has no result tabs (not a results page yet)."""
    tab = re.search(r'<input\b(?=[^>]*\bchecked\b)(?=[^>]*name="_Result_filters")[^>]*>.*?<p class="ilosc">\s*([\d\s.,]*)</p>', html, re.DOTALL)
    if not tab:
        return None
    count = int(re.sub(r'\D', '', tab.group(1)) or 0)
    return ('empty' if count == 0 else 'results'), count

def szukaj_rows(html, base='https://www.szukajwarchiwach.gov.pl'):
    """One row per unit: «title | years | sygnatura | archive | scans/no scans | tags | link»."""
    rows = []
    for block in re.split(r'<div class="row search-result">', html)[1:]:
        title = re.search(r'<p class="h4 search-title">\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.DOTALL)
        if not title:
            continue
        fields = {}
        for dt, dd in re.findall(r'<dt>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>', block, re.DOTALL):
            dd = re.sub(r'<button\b.*?</button>', ' ', dd, flags=re.DOTALL)
            fields[_szukaj_clean(dt).rstrip(':').strip().lower()] = _szukaj_clean(dd)
        def field(*names, fields=fields):
            return next((fields[n] for n in names if fields.get(n)), '')
        scans = 'brak skanów' if 'no-picture' in block else 'skany'
        tags = ' '.join(t for t in re.findall(r'#[^<#]+', field('tags and indexes', 'tagi i indeksy', 'теги и индексы')) if t.strip())
        href = title.group(1)
        link = href if href.startswith('http') else base + href
        cells = [_szukaj_clean(title.group(2)), field('year / years', 'rok / lata', 'год / годы'),
                 field('reference code', 'sygnatura', 'шифр'), field('archives', 'archiwum', 'архив'), scans,
                 field('description', 'opis', 'описание')[:200], tags.strip(), link]
        rows.append(' | '.join(c.replace('|', '/') for c in cells))
    return rows

def szukaj_read(html):
    """(state, count, rows) of a szukajwarchiwach results page. Zero is the page's own block «brak-wynikow»
    («No results» / «Brak wyników»), checked 8.11.2026 on Qzwxjvbnkplm. (None, None, []) = not a results page yet."""
    if 'class="brak-wynikow"' in html:
        return 'empty', 0, []
    counted = szukaj_count(html)
    if not counted:
        return None, None, []
    return counted[0], counted[1], szukaj_rows(html)

def obd_read(html):
    """Rendered OBD list and record; IDs come from the site's own click attributes."""
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    fields = re.findall(r'class="card_param-title"[^>]*>(.*?)</span>\s*<span class="card_param-result"[^>]*>(.*?)</span>', html, re.DOTALL)
    if fields:
        return 'results', 1, [' | '.join((_szukaj_clean(k), _szukaj_clean(v))) for k, v in fields]
    count = re.search(r'Записи с\s+\d+\s+по\s+\d+\s+из\s+([\d\s]+)<', html)
    rows = []
    for block in re.split(r'<div\b[^>]*class="row search-result"[^>]*>', html)[1:]:
        block = block.split('<!-- bottom paginator')[0]
        ident = re.search(r'\bid_common="(\d+)"', block)
        if not ident:
            continue
        cells = re.findall(r'<div class="search-result__col-(?:name|date-birth|date-out|place)">(.*?)</div>', block, re.DOTALL)
        rows.append(' | '.join([_szukaj_clean(c) for c in cells] + ['https://obd-memorial.ru/html/info.htm?id=' + ident.group(1)]))
    if count and rows:
        return 'results', int(re.sub(r'\D', '', count.group(1))), rows
    # A zero marker has not been observed live: never infer absence from the shell.
    return None, None, []

def _gt_text(cell):
    """Cell HTML -> text; the 'Inne nazwiska' tooltip of a surname stays in brackets."""
    cell = cell if isinstance(cell, str) else ('' if cell is None else str(cell))
    alt = [' '.join(_unescape(t).split()) for t in re.findall(r'title="([^"]*)"', cell)]
    text = ' '.join(_unescape(re.sub(r'<[^>]+>', ' ', cell)).split())
    alt = [t for t in alt if t]
    return text + (f' [{"; ".join(alt)}]' if alt else '')

def _gt_notes(cell):
    titles = [_unescape(t) for t in re.findall(r'title="([^"]*)"', cell or '')]
    keep = [t for t in titles if not t.startswith(('Miejsce przechowywania', 'Indeks dodał', 'Zgłoś'))]
    return re.sub(r'\s+', ' ', ' | '.join(keep)).strip(' |')

def _gt_scan(cell):
    m = re.search(r'<a class="gt"[^>]*href="([^"]+)"', cell or '')
    return _unescape(m.group(1)) if m else ''

def geneteka_row(bdm, row):
    """One row, fixed columns ('—' when empty): year | act | person | parents (mother's maiden name 'z d.') |
    parish / village (S: + spouse and parents, parish) | notes (date, age, other names; S: the village) | scan | gid, rid.
    Column order on the site: B and D — year, act, name, surname, father, mother, mother's surname, parish, village,
    notes; S — year, act, name, surname, parents, name2, surname2, parents2, parish, notes."""
    cells = list(row) + [''] * 10
    last = row[-1] if row and isinstance(row[-1], str) else ''
    gid = re.search(r'gid=(\d+)', last)
    rid = re.search(r'[?&;]rid=(\d+)', last)
    t = [_gt_text(c) for c in cells[:9]]
    person = f'{t[2]} {t[3]}'.strip()
    if bdm == 'S':
        parents = f'родители: {t[4]}' if t[4] else ''
        spouse = ' '.join(x for x in (f'{t[5]} {t[6]}'.strip(), f'(родители: {t[7]})' if t[7] else '') if x)
        cols = [t[0], t[1], person, parents, ('+ ' + spouse if spouse else '+ ?') + (f' / {t[8]}' if t[8] else '')]
    else:
        mother = ' '.join(x for x in (t[5], f'z d. {t[6]}' if t[6] else '') if x)
        parents = '; '.join(x for x in (f'ojciec {t[4]}' if t[4] else '', f'matka {mother}' if mother else '') if x)
        cols = [t[0], t[1], person, parents, f'{t[7]} / {t[8]}'.strip(' /')]
    ids = ' '.join(x for x in (f'gid {gid.group(1)}' if gid else '', f'rid {rid.group(1)}' if rid else '') if x)
    cols += [_gt_notes(last), _gt_scan(last) or 'без скана', ids]
    return ' | '.join((c or '—').replace('|', '/') for c in cols), ((bdm, gid.group(1)) if gid else None)

def geneteka_read(responses, params=None, final=False, known=None):
    """responses: [(url, post, body)] from .../api/getAct.php. The last answer whose request carries the asked
    surname wins (DataTables may redraw). Zero is recordsFiltered 0 in the site's own JSON."""
    params = params or {}
    want = params.get('surname', params.get('search_lastname', ''))
    found, bdm = None, 'B'
    for url, post, body in responses:
        q = {k: v[0] for k, v in _parse_qs(_urlsplit(url).query + '&' + (post or ''), keep_blank_values=True).items()}
        if want and q.get('search_lastname', '').casefold() != want.casefold():
            continue
        try:
            d = json.loads(body.lstrip('﻿') if isinstance(body, str) else body)
        except (ValueError, TypeError):
            continue
        if isinstance(d, dict) and 'data' in d:
            found, bdm = d, q.get('bdm', 'B').upper()
    if found is None:
        return None, None, []
    total = _index_count(found, found.get('recordsFiltered', found.get('recordsTotal')))
    data = found.get('data')
    if total is None:
        return None, None, []
    if total == 0:
        return 'empty', 0, []
    lines, keys = [], []
    for r in data:
        line, key = geneteka_row(bdm, r)
        lines.append(line)
        keys.append(key)
    marks = known([k for k in keys if k]) if known else {}
    lines = [f'{line} | уже: {marks[k]}' if k in marks else line for line, k in zip(lines, keys)]
    kind = {'B': 'крещения', 'S': 'браки', 'D': 'смерти'}.get(bdm, bdm)
    head = f'# {kind}: {total}; в ответе {len(data)}'
    if marks:
        head += f'; из них уже локально {len(marks)} (programs/reconstitution: корпус или выгрузка)'
    return 'results', total, [head] + lines
