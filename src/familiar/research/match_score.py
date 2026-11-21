# START_MODULE_CONTRACT: MOD-MATCH-SCORE
# PURPOSE: Score "one person or two" as a product of likelihood ratios with a basis in words; rank candidates beside the unseen.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - the score is the researcher's instrument and objection: it never merges, never writes and never blocks [review: engine lead]
# - dependent arguments in one group are damped (strongest whole, the next at 1/2, then 1/4), never multiplied in full [review: engine lead]
# - name shares come only from traces the family already has; with few traces the fallback says so [review: engine lead]
# - a candidate's share among candidates keeps the unseen candidates as their own row [review: engine lead]
# CHANGES_WITH:
# - MOD-NAME-KEY
# - MOD-SEARCH-VARIANTS
# - regions/belarus-podlasie/evidence.toml
# :END_MODULE_CONTRACT
import math
import re
from datetime import date

from familiar.instance.gate import boundary
from familiar.instance.packs import pack_file, read

from .name_key import Key, key
from .search_variants import _entries, norm

FALLBACK = {'pool': 600, 'pool_basis': 'engine fallback: no region evidence file', 'surname_share': 0.05,
            'surname_share_basis': 'engine fallback share of one surname', 'village_share': 0.2,
            'village_share_basis': 'engine fallback share of one village'}
NAME_BACKGROUND, SMOOTHING, FEW_TRACES = 1 / 25, 12, 30


class Context:
    """What one family's data says once: name classes, name shares, place records, region evidence."""

    def __init__(self, instance):
        from familiar.tree.builder import _build
        self.key = key(instance)
        self.evidence = {'rite': {}, 'defaults': dict(FALLBACK)}
        for pack in instance.packs:
            if file := pack['data'].get('pack', {}).get('files', {}).get('evidence'):
                data = read(pack_file(pack, file))
                self.evidence['rite'] |= data.get('rite', {})
                self.evidence['defaults'] |= data.get('defaults', {})
        entries = _entries(instance)
        self.given, self.places, self.surnames = {}, {}, {}
        for entry in entries:
            texts = [entry.get('canonical', ''), *(f['text'] for f in entry['forms'])]
            book = {'given_name': self.given, 'place': self.places, 'surname': self.surnames}.get(entry['kind'])
            for text in filter(None, texts):
                if book is self.given:
                    book.setdefault(self.word(text), set()).add(entry['id'])
                elif book is not None:
                    book.setdefault(self.word(text), entry)
        from familiar.tree.builder import read_json
        for row in read_json(instance.path('tree_metadata'), {}).get('surname_forms', []):
            for text in [row.get('form'), *row.get('variants', [])]:
                if text:
                    self.surnames.setdefault(self.word(text), {'id': 'clan:' + row.get('id', '')})
        self.counts, self.total = {'M': {}, 'F': {}}, {'M': 0, 'F': 0}
        for person in _build(instance)['people'].values():
            sex = str(person.get('sex', '')).upper()
            given = next((n['given'] for n in person.get('names', []) if n.get('given')), '')
            if sex in self.counts and given and not person.get('placeholder'):
                classes = self.classes(given)
                for c in classes:
                    self.counts[sex][c] = self.counts[sex].get(c, 0) + 1 / len(classes)
                self.total[sex] += 1

    def word(self, text):
        first = re.sub(r'\(.*?\)', '', str(text)).split()
        first = first[0] if first else ''
        return Key.fold(self.key.translit(first)) if self.key else norm(first)

    def classes(self, given):
        w = self.word(given)
        return self.given.get(w) or {'form:' + w}

    def share(self, classes, sex):
        sex = sex if sex in self.counts else 'M'
        n = self.total[sex]
        if n < FEW_TRACES:
            return NAME_BACKGROUND, f'few traces ({n} named people of that sex): fallback 1/25'
        q = max((self.counts[sex].get(c, 0) + SMOOTHING * NAME_BACKGROUND) / (n + SMOOTHING) for c in classes)
        return q, f'q={q:.3f} among {n} {"men" if sex == "M" else "women"} of the family tree'

    def same_surname(self, a, b):
        if self.key and (how := self.key.relation(a, b, 'surname')):
            return how
        ea, eb = self.surnames.get(self.word(a)), self.surnames.get(self.word(b))
        if ea and eb and ea['id'] == eb['id']:
            return 'one dictionary entry or clan decision'
        return 'same letters' if self.word(a) == self.word(b) else None

    def place(self, text):
        entry = self.places.get(self.word(text))
        return (entry['id'], entry) if entry else ('form:' + self.word(text), {})


def a_given(ctx, x, y):
    if not x.get('given') or not y.get('given'):
        return []
    cx, cy = ctx.classes(x['given']), ctx.classes(y['given'])
    if cx & cy:
        q, basis = ctx.share(cx & cy, x.get('sex') or y.get('sex') or 'M')
        return [(0.95 / q, f"one given name {x['given']} / {y['given']}; {basis}",
                 'a corpus searched for this name inflates q; a rare name weighs more')]
    return [(0.03, f"different given names {x['given']} / {y['given']}", "clerks swap a man's names now and then")]


def a_surname(ctx, x, y):
    if not x.get('surname') or not y.get('surname'):
        return []
    d = ctx.evidence['defaults']
    if how := ctx.same_surname(x['surname'], y['surname']):
        u = d['surname_share']
        return [(0.97 / u, f"one surname {x['surname']} / {y['surname']} ({how}); u={u}", d['surname_share_basis'])]
    return [(0.02, f"different surnames {x['surname']} / {y['surname']}", "mother's or step-father's surname, a clerk's slip")]


def a_age(ctx, x, y):
    ex, ey = x.get('born_exact'), y.get('born_exact')
    if ex and ey:
        days = abs((date.fromisoformat(ex) - date.fromisoformat(ey)).days)
        return [(40.0, f'same birth date {ex}', '')] if days <= 3 else [
            (0.02, f'two exact birth dates {ex} / {ey}', 'a misread year or a copy error')]
    bx, by = x.get('born'), y.get('born')
    if not bx or not by:
        return []
    gap = max(0, max(bx[0], by[0]) - min(bx[1], by[1]))
    width = (bx[1] - bx[0]) + (by[1] - by[0])
    r = math.exp(-1 / 2.0)  # revision ages drift about two years
    p_same = 0.6 + 0.4 * min(1, width / 10) if gap == 0 else 0.4 * (1 - r) * r ** (gap - 1)
    p_other = min(1, (width + 2) / 30) if gap == 0 else 2 / 30
    return [(p_same / p_other, f'birth {bx[0]}-{bx[1]} / {by[0]}-{by[1]}: gap {gap} y', 'a wide window carries little')]


def a_place(ctx, x, y):
    def spots(m):
        out = []
        for text in m.get('places') or [m.get('place')]:
            if text:
                ident, entry = ctx.place(text)
                parish = entry.get('parish') or m.get('parish')
                if isinstance(parish, dict):  # a place record names its parish by rite
                    parish = parish.get(m.get('rite')) or parish.get('latin') or next(iter(parish.values()), None)
                out.append((ident, text, parish, entry.get('manor') or m.get('manor')))
        return out
    d, best = ctx.evidence['defaults'], None
    for ia, ta, pa, ma in spots(x):
        for ib, tb, pb, mb in spots(y):
            if ia == ib:
                u = d['village_share']
                cand = (0.6 / u, f'same place {ta} / {tb}; u={u}', d['village_share_basis'])
            elif ma and ma == mb:
                cand = (0.8, f'{ta} / {tb}: one manor ({ma})', 'proximity by manor only')
            elif pa and pa == pb:
                cand = (0.43, f'{ta} / {tb}: one parish ({pa})', 'no coordinates yet; a move inside a parish is common')
            elif pa and pb:
                cand = (0.125, f'{ta} / {tb}: different parishes', '')
            else:
                cand = (0.5, f'{ta} / {tb}: different places, parish unknown', 'add parish or coordinates to the place record')
            best = cand if best is None or cand[0] > best[0] else best
    return [best] if best else []


def a_rite(ctx, x, y):
    rules, out = ctx.evidence['rite'], []
    rx, ry = x.get('rite'), y.get('rite')
    if rx and ry and 'revision' not in (rx, ry) and rules:
        year = min(x.get('year', 9999), y.get('year', 9999))
        if rx == ry:
            out.append((1.1, f'same rite of book ({rx})', ''))
        elif {rx, ry} == {'latin', 'uniate'} and year < rules['union_year']:
            out.append((rules['before_union'], f"latin / uniate before {rules['union_year']}: bi-ritual families", ''))
        else:
            out.append((rules['after_union'], f'rite {rx} / {ry}', 'conversion and mixed marriages; the rite of a book is not always of the person'))
    latin = set(rules.get('latin_calendar', []))
    for m, other in ((x, y), (y, x)):
        if m.get('given') and other.get('rite') == 'orthodox' and (ctx.classes(m['given']) | {ctx.word(m['given'])}) & latin:
            out.append((rules['latin_name_in_orthodox'], f"{m['given']} is a Latin-calendar name in an Orthodox act", 'calendar knowledge, not counted'))
    return out


def a_family(ctx, x, y):
    out = []
    for field, sex in (('father', 'M'), ('mother', 'F'), ('spouse', 'F' if (x.get('sex') or 'M') == 'M' else 'M')):
        fx, fy = x.get(field), y.get(field)
        if fx and fy:
            if shared := ctx.classes(fx) & ctx.classes(fy):
                q, basis = ctx.share(shared, sex)
                out.append((0.95 / q, f'{field} {fx} = {fy}; {basis}', ''))
            elif field == 'spouse' and abs(x.get('year', 0) - y.get('year', 0)) > 5:
                out.append((0.4, f"spouse {fx} / {fy}, {abs(x['year'] - y['year'])} years apart", 'widowhood and remarriage'))
            else:
                out.append((0.08, f'{field} {fx} / {fy}', 'patronymics in revisions err'))
    if x.get('maiden') and y.get('maiden'):
        how = ctx.same_surname(x['maiden'], y['maiden'])
        out.append((0.9 / 0.03, f"maiden name {x['maiden']} / {y['maiden']} ({how})", '') if how else
                   (0.1, f"maiden name {x['maiden']} / {y['maiden']}", ''))
    sx = {c for s in x.get('siblings', []) for c in ctx.classes(s)}
    for c in sorted(sx & {c for s in y.get('siblings', []) for c in ctx.classes(s)}):
        q, basis = ctx.share({c}, 'M')
        out.append((0.9 / q, f'sibling {c} in both; {basis}', ''))
    return out


def a_network(ctx, x, y):
    own = [m['surname'] for m in (x, y) if m.get('surname')]
    out = []
    for s in x.get('sponsors', []):
        if any(ctx.same_surname(s, t) for t in y.get('sponsors', [])):
            kin = any(ctx.same_surname(s, o) for o in own)
            out.append((1.2 if kin else 2.0, f'shared sponsor surname {s}', 'kin sponsor each other; the own surname is weak'))
    return out


def a_household(ctx, x, y):
    hx, hy = x.get('household'), y.get('household')
    if not hx or not hy:
        return []
    if hx == hy:
        return [(20.0, f'same household {hx}', 'a number may be reused across revisions')]
    if hx.split()[0] == hy.split()[0]:
        return [(0.01, f'two rows of one list ({hx} / {hy})', 'a double entry happens, but is marked')]
    return []


def a_class(ctx, x, y):
    if x.get('class') and y.get('class'):
        return [(1.0, f"same class ({x['class']})", '')] if x['class'] == y['class'] else [
            (0.2, f"class {x['class']} / {y['class']}", '')]
    return []


def a_died(ctx, x, y):
    return [(0.01, f"died {m['died']}, the other record is {o['year']}", 'misread dates or another person')
            for m, o in ((x, y), (y, x)) if m.get('died') and o.get('year') and o['year'] > m['died'] + 1]


ARGUMENTS = [('given name', a_given), ('surname', a_surname), ('age', a_age), ('place', a_place), ('rite', a_rite),
             ('family', a_family), ('sponsors', a_network), ('household', a_household), ('class', a_class),
             ('death', a_died)]


def damp(ratios):
    """Strongest whole, each next at half the exponent: dependent arguments add less than their product."""
    value = 1.0
    for side in (sorted((r for r in ratios if r >= 1), reverse=True), sorted(r for r in ratios if r < 1)):
        for i, r in enumerate(side):
            value *= r ** (0.5 ** i)
    return value


def score(ctx, x, y, pool=None):
    pool = pool or ctx.evidence['defaults']['pool']
    groups, total = [], 1.0
    for name, argument in ARGUMENTS:
        if items := argument(ctx, x, y):
            lr = damp([i[0] for i in items])
            total *= lr
            groups.append({'group': name, 'lr': float(f'{lr:.3g}'),
                           'items': [{'lr': float(f'{i[0]:.3g}'), 'basis': i[1], 'caveat': i[2]} for i in items]})
    weight = total / (total + pool - 1)
    groups.sort(key=lambda g: -abs(math.log(max(g['lr'], 1e-300))))
    words = '; '.join(f"{g['group']} ×{g['lr']:.3g} ({g['items'][0]['basis']})" for g in groups)
    return {'lr': total, 'weight': round(weight, 4), 'pool': pool, 'arguments': groups, 'words': words,
            'pool_basis': ctx.evidence['defaults']['pool_basis'] if pool == ctx.evidence['defaults']['pool'] else 'given',
            'accepted': False}


@boundary('research')
def compare(instance, x, y, pool=None):
    """Two mentions (see docs/research-coverage.md#identity-score): weight of one person among pool men, with reasons."""
    return score(Context(instance), x, y, pool)


@boundary('research')
def rank(instance, target, candidates, pool=None):
    """Each candidate's share of the target beside the unseen: an unseen man of the pool has LR 1 on average."""
    ctx = Context(instance)
    rows = {cid: score(ctx, target, c, pool) for cid, c in candidates.items()}
    pool = pool or ctx.evidence['defaults']['pool']
    unseen = max(pool - len(rows), 0)
    total = sum(r['lr'] for r in rows.values()) + unseen
    out = [{'id': cid, 'share': round(r['lr'] / total, 4), 'weight': r['weight'], 'words': r['words']}
           for cid, r in rows.items()]
    out.sort(key=lambda r: -r['share'])
    return {'pool': pool, 'candidates': out, 'unseen': {'count': unseen, 'share': round(unseen / total, 4)},
            'details': rows, 'accepted': False}
