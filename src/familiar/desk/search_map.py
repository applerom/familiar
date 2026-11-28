# START_MODULE_CONTRACT: MOD-DESK-SEARCH-MAP
# PURPOSE: Show, per family line, what was read and where the unread books lie: the books of its places, year strips of record series, the field of name bases, the cells to read next and a reading-room list to take along.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - the page is the host's: the shared hosted projection omits it and its navigation link [review: engine lead]
# - meaning is carried by form; where the map cannot tell, the page says unknown [review: browser walk]
# - headings, ledger lines and translated text omit names of people whose death is unestablished [review: engine lead]
# - where a book lies is told as a plan: no warning, no verdict, and nothing where nothing exists [review: engine lead]
# - the lines the family works on come first and open; the rest fold to one row; detail is one tap away [review: browser walk]
# CHANGES_WITH:
# - MOD-SEARCH-MAP (the view)
# - MOD-ACCESS-LEDGER (books of a place and the reading-room list)
# - MOD-DESK-BUILD (page and navigation)
# :END_MODULE_CONTRACT
import html
import re

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


def timeline(line, w, tr=str):
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
            bars.append(f'<span class="lane"><span class="kind">{esc(tr(lanes[kind][0]["kind"]))}</span><span class="axis">'
                        f'<span class="yrs" style="--from:{(lo - first) / span * 100:.2f}%;'
                        f'--width:{(hi - lo + 1) / span * 100:.2f}%">{cells}</span></span></span>')
        detail = ''.join(
            f'<div class="one"><small><b>{esc(tr(s.get("title") or s["kind"] + " · " + s["place"]))}</b>'
            + ''.join(f' · {esc(v)}' for v in (s.get('holder'), ', '.join(s['online'])) if v) + '</small>'
            + strip(s, w) + '</div>' for s in every)
        rows.append(f'<details class="series"{" open" if len(line["series"]) <= 3 else ""}><summary><span class="label">{esc(tr(place))}</span>'
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


MARKS = {'read': 'full', 'home': 'online', 'copy': 'online', 'room': 'archive', 'letter': 'archive', 'unknown': 'login'}


def shelves(places, w, language, texts, strict):
    """The books of each place: what we have read and where the rest lies. Nothing is said where nothing exists."""
    from familiar.research.access_ledger import MARKS_ORDER, in_order, progress, say, title
    esc, b = html.escape, w['books']
    out = []
    for place in places:
        groups = {}
        for row in in_order(place['books']):
            if row['state'] in MARKS and not row.get('doubtful'):
                holder = say(row.get('holder'), language, texts) if row['state'] in {'copy', 'room', 'letter'} else ''
                groups.setdefault((MARKS_ORDER.index(row['state']), holder), []).append(row)
        body = []
        for (n, holder), rows in sorted(groups.items(), key=lambda item: item[0][0]):
            state = MARKS_ORDER[n]
            head = b[state].format(holder=holder) if holder or state not in {'copy', 'room', 'letter'} else b[state + '_some']
            items = []
            for row in rows:
                where = [say(row.get('holder'), language, texts) if not holder else '', say(row.get('reference'), language, texts),
                         progress(row, b, language, texts) if state in {'read', 'home'} else '']
                detail = ' · '.join(v for v in where if v)
                items.append(f'<li><i class="y s-{MARKS[state]}"></i><span>{esc(title(row, b, language, texts, strict=strict))}'
                             + (f'<small>{esc(detail)}</small>' if detail else '') + '</span></li>')
            body.append(f'<h5>{esc(head)}</h5><ul>{"".join(items)}</ul>')
        if body:
            name = say(place.get('title') or place['place'], language, texts)
            out.append(f'<article class="shelf"><h4>{esc(name)}</h4>{"".join(body)}</article>')
    return f'<div class="shelves">{"".join(out)}</div>' if out else ''


def take_along(places, w, language, texts, strict):
    """The reading-room list by archive: call number, place and books, what to look for."""
    from familiar.research.access_ledger import reading_room, say, title
    esc, b = html.escape, w['books']
    archives = {}
    for place, row in reading_room(places):
        holder = say(row.get('holder'), language, texts) or b['order_any']
        name = say(place.get('title') or place['place'], language, texts)
        wanted = say(row.get('look_for'), language, texts, strict=strict)
        archives.setdefault(holder, []).append(
            f'<li><b>{esc(say(row.get("reference"), language, texts))}</b><span>{esc(name)} · '
            f'{esc(title(row, b, language, texts, strict=strict))}</span>' + (f'<em>{esc(wanted)}</em>' if wanted else '') + '</li>')
    if not archives:
        return ''
    return (f'<section class="take-along" id="reading-room"><h2 class="h2">{esc(b["order_title"])}</h2>'
            f'<p class="sub">{esc(b["order_sub"])}</p>'
            + ''.join(f'<h3>{esc(holder)}</h3><ol>{"".join(rows)}</ol>' for holder, rows in archives.items()) + '</section>')


def line_section(line, w, *, open_, language='', texts=None, strict=False):
    from familiar.research.search_map import base_groups
    esc = html.escape
    def tr(value):
        return (texts or {}).get(value, value)
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
           f'{esc(tr(line["surname"]) or w["no_surname"])}</h2><span class="line-tally">'
           f'{esc(" · ".join(t for t in tally if t))}</span></summary>']
    if books := shelves(line['access'], w, language, texts, strict):
        out.append(f'<h3>{esc(w["books"]["families_heading"])}</h3>' + books)
    if line['series']:
        counts = [(read, w['count_read']), (touched, w['count_touched']), (open_online, w['count_online']),
                  (archive, w['count_archive'])]
        out.append('<div class="counts" style="--counter-count:4">' + ''.join(
            f'<div><b>{n}</b><span>{esc(label)}</span></div>' for n, label in counts) + '</div>')
        out.append(f'<h3>{esc(w["series"])}</h3>' + timeline(line, w, tr))
    titles = {s['id']: tr(s.get('title') or f"{s['kind']} · {s['place']}") for s in line['series']}
    if line['next']:
        out.append(f'<h3>{esc(w["next"])}</h3><ol class="next">'
                   + ''.join(next_item(r, titles, w) for r in line['next'][:5]) + '</ol>')
    if line['bases'] or not line['fit_people']:
        out.append(f'<h3>{esc(w["bases"])}</h3>')
    if not line['fit_people']:
        out.append(f'<p class="sub">{esc(w["fit_unknown"])}</p>')
    out.append(field(line, w) + '</details>')
    return ''.join(out)


def page(active, w, view, *, language=None, texts=None, protected=None):
    from familiar.research.search_map import working
    esc = html.escape
    language = language or active.source_language
    strict = language != active.source_language
    shown = [line for line in view['lines'] if line['series'] or line['bases'] or line['access']]
    main = [line for line in shown if working(line)] or shown[:1]
    body = ''.join(line_section(line, w, open_=line in main, language=language, texts=texts, strict=strict) for line in shown)
    if body and not view['series_list']:
        body = f'<p class="sub series-unknown">{esc(w["series_unknown"])}</p>' + body
    if view['series_list'] and any(line['series'] for line in view['lines']):
        body += legend(w)
    listed = take_along(view['access'], w, language, texts, strict)
    to_list = f'<p class="to-list"><a href="#reading-room">{esc(w["books"]["order_title"])}</a></p>' if listed else ''
    body += listed
    rendered = ('<!doctype html><html lang="' + esc(language) + '"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,nofollow,noarchive"><title>' + esc(w['title'])
            + '</title><link rel="stylesheet" href="/desk/show.css"><link rel="stylesheet" href="/desk/search-map.css">'
            '</head><body class="familiar-show search-map"><main class="wrap"><section class="since">'
            '<div class="kicker">' + esc(w['kicker']) + '</div><h1>' + esc(w['title']) + '</h1>' + to_list + '</section>'
            + (body or '<p class="sub">' + esc(w['series_unknown']) + '</p>') + '</main></body></html>')
    if protected is not None:
        def redact(match):
            value = html.unescape(match[2])
            clean = protected.sub('…', value)
            return match[1] + esc(clean) if clean != value else match[0]
        rendered = re.sub(r'(>|(?:title|aria-label)=")([^<>"]+)(?=<|")', redact, rendered)
    return rendered.encode()


def project(active, w, languages=()):
    """{page name: bytes} in the family's language and each (language, words, texts); empty when the journals cannot be read."""
    from familiar.research.search_map import build
    try:
        view = build(active)
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        return {}
    if not view['series_list'] and not view['access'] and not any(line['bases'] for line in view['lines']):
        return {}
    from familiar.instance.subjects import protected_names
    protected = protected_names(active)
    pages = {PAGE: page(active, w['search_map'], view, protected=protected)}
    for language, words, texts in languages:
        pages[PAGE.replace('.html', f'.{language}.html')] = page(
            active, words['search_map'], view, language=language, texts=texts, protected=protected)
    return pages
