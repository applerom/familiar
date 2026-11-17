# PURPOSE: Give every person without a recorded birth year an orientation year from the nearest dated relatives.
# A guess is reader presentation only: never an event, a research bound or life-status evidence (MOD-TREE-LIFE
# keeps its own conservative bounds). A recorded year replaces it on the next build; nothing is stored.
import re
from datetime import date

YEAR = re.compile(r'\b(1\d{3}|20\d{2})\b')
REJECTED = {'rejected', 'disproved'}
# The family's rule: a parent is guessed from the first known child; when no child is dated, the spouse, then
# brothers and sisters, then parents. A real date always beats a chain of guesses.
ORDER = {'child': 0, 'spouse': 1, 'sibling': 2, 'parent': 3}


def _year(value):
    found = YEAR.search(str(value or ''))
    return int(found.group(1)) if found else None


def _is(event, tag, kind):
    """As the reader reads a card: an imported tag, or a research event of that kind that is not a version."""
    return event.get('tag') == tag or (event.get('type') == kind and event.get('status') not in REJECTED | {'hypothesis'})


def _birth(person):
    card = person.get('cardPresentation') or {}
    if 'birth' in card:  # as the reader: a card decision wins over the event
        return _year(card['birth'])
    return next((y for e in person.get('events', []) if _is(e, 'BIRT', 'birth') if (y := _year(e.get('date')))), None)


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


def guesses(graph, ages, eligible=None):
    """{person id: guess} for people without a birth year; `eligible` limits who may receive one."""
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
                found[pid] = (year, step)
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

    return {pid: {'year': 5 * round(dated[pid][0] / 5), 'exact': dated[pid][0], 'relation': relation,
                  'anchors': [{'id': a, 'year': dated[a][0], 'guessed': a in result, 'age': age(pid, relation, a),
                               'offset': dated[pid][0] - dated[a][0]} for a in anchors]}
            for pid, (relation, anchors) in result.items()}


def apply(instance, graph, *, host_private=False):
    """Attach `birthGuess` to reader people. In a public projection only to people already shown as deceased:
    a protected person gets no guessed age, and their hidden dates are no longer in the graph to anchor others."""
    from familiar.rules.cascade import Registry
    from familiar.rules.roles import method_root
    ages = Registry(method_root() / 'rules', instance).resolve_setting('tree.first_child_age').value
    people = graph['people']
    eligible = None if host_private else {pid for pid, p in people.items() if p.get('living') is False}
    for pid, guess in guesses(graph, ages, eligible).items():
        people[pid]['birthGuess'] = guess
    return graph
