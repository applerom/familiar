# START_MODULE_CONTRACT: MOD-DESK-SEARCH-MAP
# PURPOSE: Show the host, per family line, what of the open record was read: year strips of record series, the field of name bases and the empty cells to read next.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - the page is the host's: the shared hosted projection omits it and its navigation link [review: engine lead]
# - meaning is carried by form; where the map cannot tell, the page says unknown [review: browser walk]
# - no person's name and no external link leaves the map; years, places and source titles only [review: engine lead]
# CHANGES_WITH:
# - MOD-SEARCH-MAP (the view)
# - MOD-DESK-BUILD (page and navigation)
# :END_MODULE_CONTRACT
import html

PAGE = 'desk/search-map.html'
STATES = ('full', 'surname', 'named', 'index', 'unknown', 'online', 'login', 'archive', 'missing', 'blocked')


def strip(series, w):
    esc = html.escape
    years = {int(y): state for y, state in series['years'].items()}
    window = set(series['window'])
    rows = []
    for decade in sorted({y // 10 * 10 for y in years}):
        cells = []
        for year in range(decade, decade + 10):
            if year not in years:
                cells.append('<i class="y none" aria-hidden="true"></i>')
                continue
            state = years[year]
            label = f"{year} · {w['states'][state]}" + (f" · {w['window']}" if year in window else '')
            cells.append(f'<i class="y s-{state}{" w" if year in window else ""}" title="{esc(label)}" '
                         f'aria-label="{esc(label)}"></i>')
        rows.append(f'<div class="decade"><span>{decade}</span>{"".join(cells)}</div>')
    return '<div class="strip" role="group">' + ''.join(rows) + '</div>'


def series_card(series, w):
    esc = html.escape
    title = series.get('title') or f"{series['kind']} · {series['place']}"
    counts = series['counts']
    read = sum(counts.get(s, 0) for s in ('full', 'surname'))
    total = sum(counts.values())
    meta = ' · '.join(v for v in (series.get('holder'), ', '.join(series['online'])) if v)
    return (f'<article class="series"><header><strong>{esc(title)}</strong>'
            f'<span class="tally"><b>{read}</b>/{total}</span></header>'
            + (f'<small>{esc(meta)}</small>' if meta else '') + strip(series, w) + '</article>')


def legend(w):
    return ('<ul class="legend">' + ''.join(f'<li><i class="y s-{state}"></i>{html.escape(w["states"][state])}</li>'
                                            for state in STATES)
            + f'<li><i class="y s-online w"></i>{html.escape(w["window"])}</li></ul>')


def base_tile(base, w):
    esc = html.escape
    state = 'opened' if base['opened'] else 'never'
    if base['fits'] is None:
        state += ' fit-unknown'
    parts = []
    if base['opened']:
        parts.append(w['returned_read'].format(hits=base['hits'], read=base['read']))
        if base['unknown_counts']:
            parts.append(w['uncounted'].format(n=base['unknown_counts']))
    else:
        parts.append(w['never'])
    if base['forms_known']:
        share = len(base.get('forms_read', []))
        parts.append(w['forms'].format(read=share, known=len(base['forms_known'])))
    missing = (f'<small>{esc(w["not_read"])} {esc(", ".join(base["forms_missing"][:6]))}'
               + ('…' if len(base['forms_missing']) > 6 else '') + '</small>') if base['opened'] and base['forms_missing'] else ''
    filled = len(base.get('forms_read', [])) / len(base['forms_known']) if base['opened'] and base['forms_known'] else 0
    return (f'<li class="base {state}" style="--f:{filled * 100:.0f}%"><strong>{esc(base["title"])}</strong>'
            f'<span>{esc(" · ".join(parts))}</span>{missing}</li>')


def next_item(run, titles, w):
    esc = html.escape
    first, last = run['years']
    years = str(first) if first == last else f'{first}–{last}'
    where = f' · {esc(run["where"])}' if run.get('where') else ''
    return (f'<li class="cost-{run["cost"]}"><i class="y s-{run["state"]}"></i><div><strong>{esc(titles[run["series"]])} '
            f'{years}</strong><span>{esc(w["states"][run["state"]])} · {esc(w["cost"][str(run["cost"])])}{where}</span></div></li>')


def line_section(line, w):
    esc = html.escape
    totals = line['totals']
    read = totals.get('full', 0) + totals.get('surname', 0)
    touched = sum(totals.get(s, 0) for s in ('named', 'index', 'unknown'))
    open_online = totals.get('online', 0) + totals.get('login', 0)
    archive = totals.get('archive', 0) + totals.get('missing', 0)
    out = [f'<section class="map-line"><h2 class="h2">{esc(line["surname"] or line["start"])}</h2>']
    if line['series']:
        counts = [(read, w['count_read']), (touched, w['count_touched']), (open_online, w['count_online']),
                  (archive, w['count_archive'])]
        out.append('<div class="counts" style="--counter-count:4">' + ''.join(
            f'<div><b>{n}</b><span>{esc(label)}</span></div>' for n, label in counts) + '</div>')
        out.append(f'<h3>{esc(w["series"])}</h3><div class="series-list">'
                   + ''.join(series_card(s, w) for s in line['series']) + '</div>')
    else:
        out.append(f'<p class="sub">{esc(w["series_unknown"])}</p>')
    if line['bases'] or not line['fit_people']:
        out.append(f'<h3>{esc(w["bases"])}</h3>')
    if not line['fit_people']:
        out.append(f'<p class="sub">{esc(w["fit_unknown"])}</p>')
    if line['bases']:
        out.append('<ul class="bases">' + ''.join(base_tile(b, w) for b in line['bases']) + '</ul>')
    titles = {s['id']: s.get('title') or f"{s['kind']} · {s['place']}" for s in line['series']}
    if line['next']:
        out.append(f'<h3>{esc(w["next"])}</h3><ol class="next">'
                   + ''.join(next_item(r, titles, w) for r in line['next']) + '</ol>')
    out.append('</section>')
    return ''.join(out)


def page(active, w, view, *, language=None):
    esc = html.escape
    language = language or active.source_language
    body = ''.join(line_section(line, w) for line in view['lines'] if line['series'] or line['bases'])
    if view['series_list'] and any(line['series'] for line in view['lines']):
        body += legend(w)
    return ('<!doctype html><html lang="' + esc(language) + '"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,nofollow,noarchive"><title>' + esc(w['title'])
            + '</title><link rel="stylesheet" href="/desk/show.css"><link rel="stylesheet" href="/desk/search-map.css">'
            '</head><body class="familiar-show search-map"><main class="wrap"><section class="since">'
            '<div class="kicker">' + esc(w['kicker']) + '</div><h1>' + esc(w['title']) + '</h1></section>'
            + (body or '<p class="sub">' + esc(w['series_unknown']) + '</p>') + '</main></body></html>').encode()


def project(active, w):
    """The page bytes, or None when the working journals cannot be read (the desk still builds)."""
    from familiar.research.search_map import build
    try:
        view = build(active)
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        return None
    if not view['series_list'] and not any(line['bases'] for line in view['lines']):
        return None
    return page(active, w['search_map'], view)
