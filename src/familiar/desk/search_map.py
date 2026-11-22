# START_MODULE_CONTRACT: MOD-DESK-SEARCH-MAP
# PURPOSE: Show the host, per family line, what of the open record was read: year strips of record series, the field of name bases and the empty cells to read next.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - the page is the host's: the shared hosted projection omits it and its navigation link [review: engine lead]
# - meaning is carried by form; where the map cannot tell, the page says unknown [review: browser walk]
# - no person's name and no external link leaves the map; years, places and source titles only [review: engine lead]
# - the lines the family works on come first and open; the rest fold to one row; detail is one tap away [review: browser walk]
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


def timeline(line, w):
    """Every series of the line on one time axis, a row of years each; its decade grid is one tap away."""
    esc = html.escape
    years = [int(y) for s in line['series'] for y in s['years']]
    first, last = min(years) // 10 * 10, max(years)
    span = last - first + 1
    step = 50 if span > 150 else 20 if span > 60 else 10
    ticks = ''.join(f'<span style="--at:{(d - first) / span * 100:.2f}%">{d}</span>'
                    for d in range(first, last + 1, step) if d == first or (d - first) / span < .92)
    from familiar.research.search_map import kind_class
    places = {}
    for series in line['series']:
        places.setdefault(series['place'], {}).setdefault(kind_class(series['kind']), []).append(series)
    rows = []
    for place, lanes in places.items():
        every = [s for kind in lanes.values() for s in kind]
        read = sum(s['counts'].get(k, 0) for s in every for k in ('full', 'surname'))
        total = sum(sum(s['counts'].values()) for s in every)
        bars = []
        for kind in sorted(lanes, key=LANES.index):
            # Books of one kind in one place, period after period, on one lane; where two overlap, the better reading shows.
            own, window = {}, set()
            for series in lanes[kind]:
                window.update(series['window'])
                for year, state in series['years'].items():
                    if ORDER.index(state) < ORDER.index(own.get(int(year), 'missing')):
                        own[int(year)] = state
                    own.setdefault(int(year), state)
            lo, hi = min(own), max(own)
            cells = ''.join(f'<i class="y s-{own[y]}{" w" if y in window else ""}"></i>' if y in own
                            else '<i class="y none"></i>' for y in range(lo, hi + 1))
            bars.append(f'<span class="lane"><span class="kind">{esc(lanes[kind][0]["kind"])}</span><span class="axis">'
                        f'<span class="yrs" style="--from:{(lo - first) / span * 100:.2f}%;'
                        f'--width:{(hi - lo + 1) / span * 100:.2f}%">{cells}</span></span></span>')
        detail = ''.join(
            f'<div class="one"><small><b>{esc(s.get("title") or s["kind"] + " · " + s["place"])}</b>'
            + ''.join(f' · {esc(v)}' for v in (s.get('holder'), ', '.join(s['online'])) if v) + '</small>'
            + strip(s, w) + '</div>' for s in every)
        rows.append(f'<details class="series"{" open" if len(line["series"]) <= 3 else ""}><summary><span class="label">{esc(place)}</span>'
                    f'<span class="tally"><b>{read}</b>/{total}</span><span class="lanes" aria-hidden="true">'
                    f'{"".join(bars)}</span></summary>{detail}</details>')
    return f'<div class="timeline"><div class="ticks" aria-hidden="true">{ticks}</div>{"".join(rows)}</div>'


FEW = 8  # a line with this few bases shows every one as a tile
LANES = ['birth', 'marriage', 'death', 'life']
ORDER = ['full', 'surname', 'named', 'index', 'unknown', 'online', 'login', 'blocked', 'archive', 'missing']


def legend(w):
    return ('<ul class="legend">' + ''.join(f'<li><i class="y s-{state}"></i>{html.escape(w["states"][state])}</li>'
                                            for state in STATES)
            + f'<li><i class="y s-online w"></i>{html.escape(w["window"])}</li></ul>')


def base_tile(base, w):
    """A base as a tile: its name and the share of the family's forms read; the numbers behind a tap."""
    esc = html.escape
    state = 'opened' if base['opened'] else 'never'
    known = len(base['forms_known'])
    share = len(base.get('forms_read', []))
    filled = share / known if base['opened'] and known else 0
    detail = []
    if base['opened']:
        detail.append(w['returned_read'].format(hits=base['hits'], read=base['read'])
                      + (' · ' + w['uncounted'].format(n=base['unknown_counts']) if base['unknown_counts'] else ''))
        if known:
            detail.append(w['forms'].format(read=share, known=known))
        if base['forms_missing']:
            detail.append(f'{w["not_read"]} {", ".join(base["forms_missing"])}')
        if base.get('last'):
            detail.append(base['last'])
    else:
        detail.append(w['never'])
    mark = f'{share}/{known}' if base['opened'] and known else ''
    return (f'<li class="base {state}" style="--f:{filled * 100:.0f}%"><details><summary>'
            f'<strong>{esc(base["title"])}</strong>' + (f'<span class="share">{esc(mark)}</span>' if mark else '')
            + '</summary>' + ''.join(f'<small>{esc(d)}</small>' for d in detail) + '</details></li>')


def next_item(run, titles, w):
    esc = html.escape
    first, last = run['years']
    years = str(first) if first == last else f'{first}–{last}'
    where = f' · {esc(run["where"])}' if run.get('where') else ''
    return (f'<li class="cost-{run["cost"]}"><i class="y s-{run["state"]}"></i><div><strong>{esc(titles[run["series"]])} '
            f'{years}</strong><span>{esc(w["states"][run["state"]])} · {esc(w["cost"][str(run["cost"])])}{where}</span></div></li>')


def field(line, w):
    """Bases that fit the line as tiles; those that fit only another community's line, or were opened off it, one tap away."""
    from familiar.research.search_map import base_groups
    esc = html.escape
    tiles, rest = base_groups(line)
    if len(tiles) + len(rest) <= FEW:
        tiles, rest = tiles + [b for b in rest if b['opened']], [b for b in rest if not b['opened']]
    out = []
    if tiles:
        out.append('<ul class="bases">' + ''.join(base_tile(b, w) for b in tiles) + '</ul>')
    groups = {}
    for b in rest:
        if b.get('community_unknown') and not b['opened']:
            groups.setdefault(', '.join(w.get(c, c) for c in b['communities']), []).append(b['title'])
    for c, names in groups.items():
        out.append(f'<p class="doubt">{esc(w["fit_doubt"].format(c=c, n=", ".join(names)))}</p>')
    if opened := [b for b in rest if b['opened']]:
        out.append(f'<details class="rest"><summary>{esc(w["rest"].format(n=len(opened)))}</summary><ul class="bases">'
                   + ''.join(base_tile(b, w) for b in opened) + '</ul></details>')
    return ''.join(out)


def line_section(line, w, *, open_):
    from familiar.research.search_map import base_groups
    esc = html.escape
    totals = line['totals']
    read = totals.get('full', 0) + totals.get('surname', 0)
    touched = sum(totals.get(s, 0) for s in ('named', 'index', 'unknown'))
    open_online = totals.get('online', 0) + totals.get('login', 0)
    archive = totals.get('archive', 0) + totals.get('missing', 0)
    years = sum(sum(s['counts'].values()) for s in line['series'])
    tiles = base_groups(line)[0]
    tally = [w['tally_years'].format(read=read, years=years) if years else '',
             w['tally_bases'].format(opened=sum(b['opened'] for b in tiles), fit=len(tiles)) if tiles else '']
    out = [f'<details class="map-line"{" open" if open_ else ""}><summary><h2 class="h2">'
           f'{esc(line["surname"] or w["no_surname"])}</h2><span class="line-tally">'
           f'{esc(" · ".join(t for t in tally if t))}</span></summary>']
    if line['series']:
        counts = [(read, w['count_read']), (touched, w['count_touched']), (open_online, w['count_online']),
                  (archive, w['count_archive'])]
        out.append('<div class="counts" style="--counter-count:4">' + ''.join(
            f'<div><b>{n}</b><span>{esc(label)}</span></div>' for n, label in counts) + '</div>')
        out.append(f'<h3>{esc(w["series"])}</h3>' + timeline(line, w))
    titles = {s['id']: s.get('title') or f"{s['kind']} · {s['place']}" for s in line['series']}
    if line['next']:
        out.append(f'<h3>{esc(w["next"])}</h3><ol class="next">'
                   + ''.join(next_item(r, titles, w) for r in line['next'][:5]) + '</ol>')
    if line['bases'] or not line['fit_people']:
        out.append(f'<h3>{esc(w["bases"])}</h3>')
    if not line['fit_people']:
        out.append(f'<p class="sub">{esc(w["fit_unknown"])}</p>')
    out.append(field(line, w) + '</details>')
    return ''.join(out)


def page(active, w, view, *, language=None):
    from familiar.research.search_map import working
    esc = html.escape
    language = language or active.source_language
    shown = [line for line in view['lines'] if line['series'] or line['bases']]
    main = [line for line in shown if working(line)] or shown[:1]
    body = ''.join(line_section(line, w, open_=line in main) for line in shown)
    if body and not view['series_list']:
        body = f'<p class="sub series-unknown">{esc(w["series_unknown"])}</p>' + body
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
