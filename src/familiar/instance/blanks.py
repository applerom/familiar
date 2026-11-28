# START_MODULE_CONTRACT: MOD-FAMILY-BLANKS
# PURPOSE: Say what a card of the family's own line lacks that a relative may know, with our leading guess beside it.
# PRD_REF: docs/PRD.md#BLANKS
# INVARIANTS:
# - an empty field means nobody asked: only a direct ancestor whose child (or who) belongs to the witness horizon is offered, never a living person or a closed line [review: engine lead]
# - a well-known card offers nothing; a field a relative already spoke to, or an open ask already covers, is not offered again [review: engine lead]
# - a guess comes from the weight of an open version or a probable parent link; offering it changes no weight [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-ASKS (horizons, asks about the same person)
# - MOD-DESK-BUILD (card invitation in the conversation links)
# - MOD-RESEARCH-PLAN (first move of a thin line)
# :END_MODULE_CONTRACT
import json
import re
from collections import defaultdict
from datetime import date

from familiar.tree.builder import read_json
from familiar.tree.birth_guess import _birth, _link, _sex, _year, guesses as birth_guesses

from .asks import closed_line, horizons, row_lines, rows as files, waiting
from .correspondence import version_options

CORE, MORE = ('name', 'patronymic', 'birth', 'spouse'), ('occupation', 'siblings')
GUESS_FROM, FIRM_FROM = .3, .9
MANY = 30  # journal rows of a line after which its bare card should have been shown to a relative
SETTLED = {'decided', 'closed', 'settled', 'accepted', 'resolved'}
DROPPED = {'rejected', 'refuted', 'discarded', 'dropped', 'ruled-out', 'superseded', 'disproved'}
# A telling that names the year in prose ("born in May 1935") is a year the family gave.
BORN = re.compile(r'\b(родил|рожд|born|birth|urodz|född)', re.I)
WANTS = {'name': 'name', 'patronymic': 'patronymic', 'maiden': 'spouse', 'date': 'birth'}


def number(value):
    return value if type(value) in (int, float) else None


class Family:
    """The links, years and own lines of one graph (the working tree or the host-private reader's)."""

    def __init__(self, instance, graph, living=None):
        from familiar.rules.cascade import Registry
        from familiar.rules.roles import method_root
        registry = Registry(method_root() / 'rules', instance)
        self.instance, self.graph = instance, graph
        self.people, self.aliases = graph['people'], graph.get('identityAliases', {})
        self.years = registry.resolve_setting('research.witness_horizon_years').value
        self.today = date.today().year
        pack = instance.language_pack_data.get(instance.source_language, {}).get('data', {})
        self.patronymics = pack.get('desk', {}).get('blanks', {}).get('patronymics') is True
        self.living = living if living is not None else {
            pid for pid, p in self.people.items() if p.get('life_assessment', {}).get('status') == 'living'}
        families = graph.get('families', [])
        self.sex = lambda pid: _sex(pid, self.people[pid], families)
        self.parents, self.children, self.partners = (defaultdict(dict), defaultdict(dict), defaultdict(set))
        for edge in graph.get('edges', []):
            parent, child = edge.get('parent'), edge.get('child')
            if (parent in self.people and child in self.people and parent != child
                    and edge.get('status') not in {'conflict', 'rejected', 'disproved'}):
                self.parents[child][parent] = self.children[parent][child] = edge
        for family in families:
            pair = [p for p in (family.get('husband'), family.get('wife')) if p in self.people]
            for child in family.get('children', []):
                for parent in pair if child in self.people else ():
                    link = {'status': 'export'} | {k: family[k] for k in ('status', 'weight') if family.get(k) is not None}
                    if child not in self.children[parent]:
                        self.parents[child][parent] = self.children[parent][child] = link
            if len(pair) == 2 and _link(family | {'status': family.get('status', 'export')}) < 3:
                self.partners[pair[0]].add(pair[1])
                self.partners[pair[1]].add(pair[0])
        for ups in self.parents.values():
            firm = [p for p, edge in ups.items() if _link(edge) < 3]
            for a in firm:
                self.partners[a].update(b for b in firm if b != a and self.sex(a) != self.sex(b))
        ages = registry.resolve_setting('tree.first_child_age').value
        guessed = birth_guesses(graph, ages)
        self.born = {pid: _birth(p) or guessed.get(pid, {}).get('exact') for pid, p in self.people.items()}
        self.closed = horizons(instance)
        self.own = self._own()

    def id(self, pid):
        return self.aliases.get(pid, pid)

    def up(self, pid):
        return [p for p, edge in self.parents[pid].items() if _link(edge) < 3]

    def down(self, pid):
        return [c for c, edge in self.children[pid].items() if _link(edge) < 3]

    def _own(self):
        """Direct ancestors of the family's home people and of their spouses: {person: generation}."""
        metadata = read_json(self.instance.path('tree_metadata'), {})
        home = {self.id(metadata.get(k)) for k in ('root', 'narrator')} & self.people.keys()
        home = home or self.living & self.people.keys()  # a family that named neither starts from its living members
        home |= {p for pid in home for p in self.partners[pid]}
        found, level, depth = {}, home, 0
        while level:
            depth += 1
            level = {p for pid in level for p, edge in self.parents[pid].items() if _link(edge) == 1} - found.keys() - home
            found.update(dict.fromkeys(level, depth))
        return found

    def names(self, pid):
        return [n for n in self.people[pid].get('names') or [] if n]

    def given(self, pid):
        return next((n['given'] for n in self.names(pid) if n.get('given')), '')

    def surnames(self, pid):
        shown = (self.people[pid].get('surnameDisplay') or {}).get('form')
        return list(dict.fromkeys([*([shown] if shown else []), *(n['surname'] for n in self.names(pid) if n.get('surname'))]))

    def within_horizon(self, pid):
        """Somebody alive could know: this person, or a child of theirs, was born within the witness horizon."""
        since = self.today - self.years
        return any((self.born.get(p) or 0) >= since or p in self.living for p in [pid, *self.down(pid)])

    def open_line(self, pid):
        return not closed_line(self.instance, self.surnames(pid), self.closed)

    def askable(self, pid):
        return pid in self.people and pid not in self.living and self.within_horizon(pid) and self.open_line(pid)

    def fathers(self, pid):
        return [(p, edge) for p, edge in self.parents[pid].items()
                if self.given(p) and (edge.get('role') in {'father', 'отец', 'ojciec'} or self.sex(p) == 'm')]

    def missing(self, pid):
        """What the card lacks, the heart of it first; [] for a card that says who this was."""
        person, named = self.people[pid], self.names(pid)
        facts = [*(person.get('events') or []), *(person.get('facts') or [])]
        if person.get('story'):
            return []
        core, given = [], self.given(pid)
        if not given or not any(n.get('surname') for n in named):
            core.append('name')
        if (self.patronymics and given and not any(n.get('patronymic') for n in named)
                and not any(_link(edge) == 1 for _, edge in self.fathers(pid))):
            core.append('patronymic')
        if not _birth(person) and not any(_year(f.get('date') or f.get('text')) and (
                'birth' in (f.get('type'), f.get('eventType')) or BORN.search(str(f.get('text') or ''))) for f in facts):
            core.append('birth')
        if self.down(pid) and not any(self.given(p) for p in self.partners[pid]):
            core.append('spouse')
        if len(core) < 2:
            return core
        if not person.get('summary') and not any('occupation' in (f.get('type'), f.get('eventType')) for f in facts):
            core.append('occupation')
        if not any(len(self.down(p)) > 1 for p in self.up(pid)):
            core.append('siblings')
        return core

    def father_guess(self, pid):
        """A probable father when nothing firmer names one: the best of the dashed links."""
        found = [(number(edge.get('weight')) or 0, p) for p, edge in self.fathers(pid)]
        if not found or max(found)[0] >= FIRM_FROM or any(_link(e) == 1 for _, e in self.fathers(pid)):
            return None
        weight, parent = max(found)
        return {'person': parent, 'weight': weight, 'value': self.people[parent].get('name', '')} if weight >= GUESS_FROM else None


def version_guesses(versions, aliases):
    """{(person, field): guess} of the leading options that name the field they would fill."""
    found = {}
    for question in versions:
        if question.get('status', question.get('state')) in SETTLED | DROPPED:
            continue
        for option in version_options(question):
            weight, guess = number(option.get('weight')), option.get('guess')
            if (weight is None or weight < GUESS_FROM or option.get('status', option.get('state')) in DROPPED | SETTLED
                    or not isinstance(guess, dict) or not guess.get('value') or guess.get('field') not in CORE + MORE):
                continue
            people = question.get('people') or ['']
            pid = guess.get('person') or people[0]
            key = (aliases.get(pid, pid), guess['field'])
            if weight > found.get(key, {}).get('weight', 0):
                found[key] = {'value': guess['value'], 'weight': weight, 'version': question['id']}
    return found


def spoken(feedback, aliases):
    """{person: fields a relative already spoke to on the card}; '' is a remark about the whole card."""
    found = defaultdict(set)
    for row in feedback:
        kind, _, rest = str(row.get('subject') or '').partition(':')
        if kind == 'blank' and ':' in rest:
            pid, _, field = rest.rpartition(':')
            found[aliases.get(pid, pid)].add(field)
        elif row.get('person') and row.get('kind') in {'correction', 'name_person'}:
            found[aliases.get(row['person'], row['person'])].add('')
    return found


def ask_about(row, aliases):
    about, aim = row.get('about') or {}, row.get('aim') or {}
    return {aliases.get(p, p) for p in [about.get('person'), *aim.get('people', [])] if p}


def offers(family, versions, feedback, asks):
    """{person: [{field, guess?}]}: the invitations of every thin card of the family's own lines."""
    guessed, told = version_guesses(versions, family.aliases), spoken(feedback, family.aliases)
    covered = defaultdict(set)
    for row in asks:
        about = row.get('about') or {}
        if about.get('person') and row.get('state') != 'proposed':
            covered[family.id(about['person'])].update(WANTS[w] for w in row.get('wants', []) if w in WANTS)
    result = {}
    for pid in family.own:
        if not family.askable(pid):
            continue
        fields = family.missing(pid)
        father = family.father_guess(pid)
        if father and (fields or not family.patronymics) and not any(n.get('patronymic') for n in family.names(pid)):
            fields = ['father', *(f for f in fields if f != 'patronymic')]
        items = []
        for field in fields:
            if field not in told[pid] | covered[pid]:
                guess = father if field == 'father' else guessed.get((pid, field))
                items.append({'field': field, **({'guess': guess} if guess else {})})
        if items:
            result[pid] = items
    return result


def shown_before(family, pid, feedback, asks):
    """A relative has seen this person's blanks: an ask about them went out, or they answered on the card."""
    return bool(spoken(feedback, family.aliases)[pid]) or any(
        pid in ask_about(row, family.aliases) and row.get('state') != 'proposed' for row in asks)


def inbox(instance):
    found = []
    for path in sorted(instance._inside('family/feedback/inbox').glob('*.json')):
        try:
            row = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        if isinstance(row, dict):
            found.append(row)
    return found


def thin(family, pid):
    """Known by little more than a name: no year, and the name is incomplete or only read from a child's patronymic."""
    fields = family.missing(pid)
    named = [n for n in family.names(pid) if n.get('given')]
    return 'birth' in fields and (bool({'name', 'patronymic', 'spouse'} & set(fields))
                                  or bool(named) and all(n.get('type') == 'inferred' for n in named))


def check(instance, graph, versions, searches, chosen, fail):
    """Advice only: many journal rows on a line whose bare card nobody put before a relative."""
    from familiar.research.coverage import surname_keys
    if not searches or not graph.get('people'):
        return
    family = Family(instance, graph)
    bare = [pid for pid in family.own if family.askable(pid) and thin(family, pid)]
    if not bare:
        return
    asks, feedback, language = [row for _, row in files(instance.path('asks'))], inbox(instance), instance.source_language
    lines = {row.get('id'): (row.get('line') or '', {family.id(p) for p in row.get('people') or []}) for row in versions}
    for pid in bare:
        if shown_before(family, pid, feedback, asks):
            continue
        keys = set().union(*(surname_keys(s, language) for s in family.surnames(pid)), set())
        count = 0
        for row in searches:
            line, people = lines.get(row.get('question'), ('', set()))
            named = {family.id(p) for p in row.get('people') or [] if isinstance(p, str)}
            count += pid in named | people or bool(keys & surname_keys(line, language))
        if count >= MANY and chosen(instance.path('asks')):
            fail(instance.path('asks'), f"{family.people[pid].get('name') or pid}: {count} journal rows on the line, and nobody "
                 f"showed a relative this card with its blanks ({', '.join(family.missing(pid))}). One word of the family "
                 'can replace them: send the card, or record an ask about this person (family ask create)')
