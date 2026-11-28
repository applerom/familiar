# PURPOSE: Give every person without a recorded birth year an orientation year from the nearest dated relatives.
# A guess is never an event or a research bound. The family reader may use it for its age horizon
# (MOD-TREE-LIFE). A recorded year replaces it on the next build; nothing is stored.
import re
from datetime import date

YEAR = re.compile(r'\b(1\d{3}|20\d{2})\b')
REJECTED = {'rejected', 'disproved'}
# What the card itself tells bounds an estimate: how old somebody at least was in a year the card names.
TOLD_AGES = {'military': 17, 'marriage': 15, 'baptism': 0, 'event': 0}
VERSION_FLOOR = .3  # the weight from which a version is drawn (dashed) and told
# Words of one man's service; a village's war ("the front came") says nothing about his age.
SERVICE = re.compile(r'\b(?:солдат|рядов(?:ой|ым|ого)\b|лазарет|на фронт|ранен|ранил|мобилизова|призван|полк(?:а|у|е|ом)?\b|'
                     r'żołnierz|szeregow(?:y|ym|ego)\b|na froncie|ranny|ranili|lazaret|zmobilizowa|pułk|'
                     r'soldier|wounded|at the front|regiment|drafted|enlisted|soldat|regement|sårad|inkallad)', re.I)
KIN = (r'(?:отец|отца|отцом|мать|матери|сын|сына|сыну|сыном|дочь|дочери|брат|брата|братья|братьев|сестра|муж|мужа|дед|деда|'
       r'ojciec|ojca|matka|syn|syna|córka|bracia|mąż|męża|dziadek|'
       r'father|mother|sons?|daughter|brothers?|husband|grandfather|far|bror|bröder)')
BORN = re.compile(r'\b(?:родил|рожд|г\.\s?р\.|urodz|ur\.|born|född)', re.I)
# The family's rule: a parent is guessed from the first known child; when no child is dated, the spouse, then
# brothers and sisters, then parents. A real date always beats a chain of guesses.
ORDER = {'child': 0, 'spouse': 1, 'sibling': 2, 'parent': 3}


def _year(value):
    found = YEAR.search(str(value or ''))
    return int(found.group(1)) if found else None


def _is(event, tag, kind):
    """As the reader reads a card: an imported tag, or a research event of that kind that is not a version."""
    return event.get('tag') == tag or (event.get('type') == kind and event.get('status') not in REJECTED | {'hypothesis'})


def birth_date(person):
    card = person.get('cardPresentation') or {}
    if 'birth' in card:  # as the reader: a card decision wins over the event
        return card['birth']
    return next((e['date'] for e in person.get('events', [])
                 if _is(e, 'BIRT', 'birth') and _year(e.get('date'))), '')


def _birth(person):
    return _year(birth_date(person))


def _death(person):
    card = person.get('cardPresentation') or {}
    if 'death' in card:
        return _year(card['death'])
    return next((y for e in person.get('events', []) if _is(e, 'DEAT', 'death') if (y := _year(e.get('date')))), None)


def _sex(pid, person, families):
    sex = str(person.get('sex') or '').lower()
    if sex in {'m', 'f'}:
        return sex
    if (person.get('namePresentation') or {}).get('isWoman') is True:
        return 'f'
    if any(f.get('husband') == pid for f in families):
        return 'm'
    return 'f' if any(f.get('wife') == pid for f in families) else ''


def _link(edge):
    """The reader's three confidence levels of a link: 1 firm, 2 probable, 3 a weak version."""
    weight = edge.get('weight')
    if isinstance(weight, (int, float)):
        return 3 if weight < .3 else 2 if weight < .5 else 1
    if edge.get('status') in {'verified', 'export'}:
        return 1
    return 2 if edge.get('status') == 'hypothesis' and edge.get('likelihood') == 'probable' else 3


def _said(value):
    return ' '.join(v for v in value.values() if isinstance(v, str)) if isinstance(value, dict) else str(value or '')


def _served(fact, person):
    """Years a told fact puts this man at war: personal words of service, and a year nobody else's and not a birth."""
    given = next((n['given'] for n in person.get('names') or [] if n and n.get('given')), '').split(' ')[0]
    root = re.escape(given[:max(3, len(given) - 1)])

    def others(sentence):
        """Somebody's father, son or brother, unless the sentence names this very man (not as "father Pyotr")."""
        if not re.search(rf'\b{KIN}\b', sentence, re.I):
            return False
        return not given or not re.search(rf'\b{root}', sentence, re.I) or re.search(rf'\b{KIN}\s+{root}', sentence, re.I)

    own = [s for s in re.split(r'(?<=[.!?;])\s+', re.sub(r'\([^)]*\)', '', _said(fact.get('text')))) if not others(s)]
    if fact.get('eventType') != 'military' and not SERVICE.search(' '.join([_said(fact.get('label')), *own])):
        return []
    return [int(y) for s in own if not BORN.search(s) for y in YEAR.findall(s)]


def told(pid, person, families, sex=''):
    """Latest birth year each dated thing on the card allows: [(latest, kind, year)], the tightest first."""
    rows = []
    for event in person.get('events') or []:
        kind, year, weight = event.get('type') or str(event.get('tag', '')).lower(), _year(event.get('date')), event.get('weight')
        if not year or kind in {'birth', 'death', 'burial', 'birt', 'deat', 'buri'} or event.get('status') in REJECTED:
            continue
        if weight < VERSION_FLOOR if isinstance(weight, (int, float)) else event.get('status') == 'hypothesis':
            continue
        rows.append(({'marr': 'marriage', 'chr': 'baptism', 'bapm': 'baptism'}.get(kind, kind), year))
    for family in families:
        if family.get('status') not in REJECTED | {'hypothesis'}:
            rows += [('marriage', year) for e in family.get('events') or [] if (e.get('type') == 'marriage' or e.get('tag') == 'MARR')
                     and (year := _year(e.get('date')))]
    for fact in person.get('facts') or [] if sex != 'f' else ():
        weight = fact.get('weight')
        shown = weight >= VERSION_FLOOR if isinstance(weight, (int, float)) else fact.get('status') in {'verified', 'export'}
        if shown and fact.get('status') not in REJECTED | {'conflict'} and not fact.get('detailOnly'):
            rows += [('military', year) for year in _served(fact, person)]
    kinds = {(kind if kind in TOLD_AGES else 'event', year) for kind, year in rows}
    return sorted((year - TOLD_AGES[kind], kind, year) for kind, year in kinds)


def first_child_age(ages, sex, around):
    """How old a father or mother usually was at the first child born around this year (setting tree.first_child_age)."""
    eras = sorted((int(start), row) for start, row in ages.items())
    row = eras[0][1]
    for start, value in eras:
        if around >= start:
            row = value
    if sex in {'m', 'f'}:
        return int(row['father' if sex == 'm' else 'mother'])
    return round((row['father'] + row['mother']) / 2)


def guesses(graph, ages, eligible=None, *, limits=None):
    """{person id: guess} for people without a birth year; `eligible` limits who may receive one.

    `limits` ({person id: latest birth year}) are what the cards tell (`bounds`). Life assessment never passes them:
    a version must not age anybody out of the protection of the living.
    """
    limits = limits or {}
    people, families = graph['people'], graph.get('families', [])
    sex = {pid: _sex(pid, p, families) for pid, p in people.items()}
    parents, children = {}, {}
    for edge in graph.get('edges', []):
        parent, child = edge.get('parent'), edge.get('child')
        if edge.get('status') in REJECTED or parent not in people or child not in people or parent == child:
            continue
        parents.setdefault(child, []).append((parent, _link(edge)))
        children.setdefault(parent, []).append((child, _link(edge)))
    spouses = {}
    for family in families:
        pair = [family.get('husband'), family.get('wife')]
        if all(p in people for p in pair):
            spouses.setdefault(pair[0], set()).add(pair[1])
            spouses.setdefault(pair[1], set()).add(pair[0])
    for ups in parents.values():  # parents of one child are partners, as the reader draws them
        for a, _ in ups:
            spouses.setdefault(a, set()).update(b for b, _ in ups if b != a and sex[a] != sex[b])
    siblings = {}  # a pair is as firm as the weaker of its two links to a shared parent
    for kids in children.values():
        for a, la in kids:
            row = siblings.setdefault(a, {})
            for b, lb in kids:
                if b != a:
                    row[b] = min(row.get(b, 3), max(la, lb))
    dated = {pid: (y, 0) for pid, p in people.items() if (y := _birth(p))}
    now = date.today().year

    def estimate(pid, relation, anchors):
        """The one formula per relation, used when a guess is made and again when its anchors move."""
        ys = [dated[a][0] for a in anchors]
        if relation == 'child':
            return ys[0] - first_child_age(ages, sex[pid], ys[0])
        if relation == 'spouse':
            around = ys[0] + first_child_age(ages, sex[anchors[0]], ys[0] + 25)
            return ys[0] + first_child_age(ages, sex[anchors[0]], around) - first_child_age(ages, sex[pid], around)
        if relation == 'sibling':
            return round(sum(ys) / len(ys))
        return round(sum(y + first_child_age(ages, sex[a], y + 25) for a, y in zip(anchors, ys)) / len(ys))

    def nearest(links):
        """Relatives with a year, nearest first: a real date, then a firmer link."""
        links = [(r, lv) for r, lv in links if r in dated]
        if not links:
            return [], 0
        key = min((dated[r][1], lv) for r, lv in links)
        return [r for r, lv in links if (dated[r][1], lv) == key], key[1]

    result, step = {}, 0
    while True:
        step += 1
        found = {}
        for pid in people:
            if pid in dated or (eligible is not None and pid not in eligible):
                continue
            options = []
            kids, level = nearest(children.get(pid, []))
            if kids:
                options.append((level, 'child', [min(kids, key=lambda c: dated[c][0])]))
            mates, _ = nearest((s, 1) for s in spouses.get(pid, ()))
            if mates:
                options.append((1, 'spouse', [min(mates, key=lambda s: dated[s][0])]))
            sibs, level = nearest(siblings.get(pid, {}).items())
            if sibs:
                options.append((level, 'sibling', sorted(sibs, key=lambda s: dated[s][0])))
            ups, level = nearest(parents.get(pid, []))
            if ups:
                options.append((level, 'parent', ups))
            death = _death(people[pid])
            ranked = sorted(((dated[o[2][0]][1], o[0], ORDER[o[1]]), o[1], o[2], estimate(pid, o[1], o[2])) for o in options)
            ranked = [o for o in ranked if o[3] <= now and (death is None or o[3] <= death)]
            if ranked:
                _, relation, anchors, year = ranked[0]
                found[pid] = (min(year, limits.get(pid, year)), step)
                result[pid] = (relation, anchors)
        if not found:
            break
        dated.update(found)
    # One family, one timeline: a guessed parent is never younger than the first child at the firmest level,
    # guessed or not (a grandson's year can reveal an elder son); a guessed child is never older than a real
    # parent. Guesses resting on a moved guess follow it.
    for _ in range(50):
        moved = False
        for pid, (relation, anchors) in list(result.items()):
            year = estimate(pid, relation, anchors)
            kids = [(c, lv) for c, lv in children.get(pid, []) if c in dated]
            if kids:
                top = min(lv for _, lv in kids)
                first = min((c for c, lv in kids if lv == top), key=lambda c: dated[c][0])
                if (cap := estimate(pid, 'child', [first])) < year:
                    year, result[pid] = cap, ('child', [first])
            real = [p for p, lv in parents.get(pid, []) if p in dated and p not in result and lv < 3]
            if real and year < (floor := max(dated[p][0] for p in real) + 16):
                year, result[pid] = floor, ('parent', [max(real, key=lambda p: dated[p][0])])
            year = min(year, limits.get(pid, year))
            if year != dated[pid][0]:
                dated[pid], moved = (year, dated[pid][1]), True
        if not moved:
            break

    def age(pid, relation, a):
        """The rule behind one anchor: a parent's age at the first child, or how much older this spouse is."""
        y = dated[a][0]
        if relation == 'child':
            return first_child_age(ages, sex[pid], y)
        if relation == 'parent':
            return first_child_age(ages, sex[a], y + 25)
        return estimate(pid, 'spouse', [a]) - y if relation == 'spouse' else 0

    def rounded(pid):
        year = 5 * round(dated[pid][0] / 5)
        return year if year <= limits.get(pid, year) else 5 * (dated[pid][0] // 5)

    return {pid: {'year': rounded(pid), 'exact': dated[pid][0], 'relation': relation,
                  'anchors': [{'id': a, 'year': dated[a][0], 'guessed': a in result, 'age': age(pid, relation, a),
                               'offset': dated[pid][0] - dated[a][0]} for a in anchors]}
            for pid, (relation, anchors) in result.items()}


def bounds(graph):
    """({person: told row that bounds the birth}, {person: (told row, relative)} where the two cannot agree).

    A dated thing on the card yields to what real years of close relatives allow: a child's year less a parent's
    greatest age, a parent's year plus the least. Outside them no estimate moves.
    """
    people, families = graph['people'], graph.get('families', [])
    mine, floors = {}, {}
    for family in families:
        for pid in {family.get('husband'), family.get('wife')}:
            mine.setdefault(pid, []).append(family)
    for edge in graph.get('edges', []):
        parent, child = edge.get('parent'), edge.get('child')
        if edge.get('status') in REJECTED or parent not in people or child not in people or _link(edge) == 3:
            continue
        if year := _birth(people[child]):
            oldest = 50 if _sex(parent, people[parent], mine.get(parent, [])) == 'f' else 65
            floors.setdefault(parent, []).append((year - oldest, child))
        if year := _birth(people[parent]):
            floors.setdefault(child, []).append((year + 14, parent))
    limits, clashes = {}, {}
    for pid, person in people.items():
        own = mine.get(pid, [])
        if _birth(person) or not (rows := told(pid, person, own, _sex(pid, person, own))):
            continue
        floor, relative = max(floors.get(pid, []), default=(None, None))
        agreed = [row for row in rows if floor is None or row[0] >= floor]
        if agreed:
            limits[pid] = agreed[0]
        if len(agreed) < len(rows):
            clashes[pid] = (rows[0], relative)
    return limits, clashes


def check(instance, graph, fail):
    """Advice only: what a card tells and the years of close relatives leave no possible year of birth."""
    if not bounds(graph)[1]:
        return
    from .life import family_cards
    graph = family_cards(instance, graph)
    people, location = graph['people'], instance.path('contributions')
    for pid, ((latest, kind, year), relative) in sorted(bounds(graph)[1].items()):
        fail(location, f"{people[pid].get('name') or pid}: the card tells of {year} ({kind}), so a birth by {latest}, while "
             f"{people[relative].get('name') or relative} was born in {_birth(people[relative])}; the estimated year of birth "
             'keeps to the relatives. One of the two belongs to somebody else: correct the link, the year or the version')


def apply(instance, graph, *, host_private=False):
    """Attach `birthGuess` to reader people. In a public projection only to people already shown as deceased:
    a protected person gets no guessed age, and their hidden dates are no longer in the graph to anchor others."""
    from familiar.rules.cascade import Registry
    from familiar.rules.roles import method_root
    ages = Registry(method_root() / 'rules', instance).resolve_setting('tree.first_child_age').value
    people = graph['people']
    eligible = None if host_private else {pid for pid, p in people.items() if p.get('living') is False}
    limits, _ = bounds(graph)
    plain = guesses(graph, ages, eligible)
    agreed = guesses(graph, ages, eligible, limits={pid: row[0] for pid, row in limits.items()}) if limits else plain
    for pid, guess in agreed.items():
        if pid in limits and guess['exact'] < plain[pid]['exact']:
            latest, kind, year = limits[pid]
            guess['told'] = {'year': year, 'kind': kind, 'latest': latest, 'before': plain[pid]['year']}
        people[pid]['birthGuess'] = guess
    return graph
