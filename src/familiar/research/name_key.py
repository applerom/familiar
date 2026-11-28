# START_MODULE_CONTRACT: MOD-NAME-KEY
# PURPOSE: One search key for a surname's or a place's forms across scripts, genders, cases and old letters, from pack rules.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - a key only proposes a search form or a hint; it never merges clans, rewrites a name or enters plan completeness [review: engine lead]
# - without a region pack that declares a key, no form is proposed [review: engine lead]
# - a person's other surname (a step-father's, a convert's) never joins two surnames: the key reads spellings, not people [review: engine lead]
# CHANGES_WITH:
# - MOD-SEARCH-VARIANTS
# - regions/belarus-podlasie/name_key.toml
# - regions/pl/pack.toml
# - regions/ru/pack.toml
# :END_MODULE_CONTRACT
import re
import unicodedata

from familiar.instance.packs import pack_file, read

# Daitch-Mokotoff: (pattern, at start, before a vowel, otherwise); 'NC' not coded, '|' alternatives.
DM_RULES = [(p, *c.split()) for p, c in (
    ('schtsch', '2 4 4'), ('schtsh', '2 4 4'), ('schtch', '2 4 4'), ('shtch', '2 4 4'), ('szczs', '2 4 4'),
    ('szcz', '2 4 4'), ('shch', '2 4 4'), ('zhdzh', '2 4 4'), ('chs', '5 54 54'), ('csz', '4 4 4'), ('czs', '4 4 4'),
    ('drz', '4 4 4'), ('drs', '4 4 4'), ('dsh', '4 4 4'), ('dsz', '4 4 4'), ('dzh', '4 4 4'), ('dzs', '4 4 4'),
    ('sch', '4 4 4'), ('sht', '2 43 43'), ('szt', '2 43 43'), ('shd', '2 43 43'), ('szd', '2 43 43'), ('tch', '4 4 4'),
    ('trz', '4 4 4'), ('trs', '4 4 4'), ('tsh', '4 4 4'), ('tsz', '4 4 4'), ('zdz', '2 4 4'), ('zhd', '2 43 43'),
    ('zsh', '4 4 4'), ('ai', '0 1 NC'), ('aj', '0 1 NC'), ('ay', '0 1 NC'), ('au', '0 7 NC'), ('cz', '4 4 4'),
    ('cs', '4 4 4'), ('ch', '5|4 5|4 5|4'), ('ck', '5|45 5|45 5|45'), ('ds', '4 4 4'), ('dz', '4 4 4'), ('dt', '3 3 3'),
    ('ei', '0 1 NC'), ('ej', '0 1 NC'), ('ey', '0 1 NC'), ('eu', '1 1 NC'), ('fb', '7 7 7'), ('ia', '1 NC NC'),
    ('ie', '1 NC NC'), ('io', '1 NC NC'), ('iu', '1 NC NC'), ('ks', '5 54 54'), ('kh', '5 5 5'), ('mn', '66 66 66'),
    ('nm', '66 66 66'), ('oi', '0 1 NC'), ('oj', '0 1 NC'), ('oy', '0 1 NC'), ('pf', '7 7 7'), ('ph', '7 7 7'),
    ('rz', '94|4 94|4 94|4'), ('rs', '94|4 94|4 94|4'), ('sc', '2 4 4'), ('sh', '4 4 4'), ('st', '2 43 43'),
    ('sz', '4 4 4'), ('tc', '4 4 4'), ('th', '3 3 3'), ('ts', '4 4 4'), ('tz', '4 4 4'), ('ui', '0 1 NC'),
    ('uj', '0 1 NC'), ('uy', '0 1 NC'), ('ue', '0 NC NC'), ('zd', '2 43 43'), ('zh', '4 4 4'), ('zs', '4 4 4'),
    ('a', '0 NC NC'), ('b', '7 7 7'), ('c', '5|4 5|4 5|4'), ('d', '3 3 3'), ('e', '0 NC NC'), ('f', '7 7 7'),
    ('g', '5 5 5'), ('h', '5 5 NC'), ('i', '0 NC NC'), ('j', '1|4 1|4 1|4'), ('k', '5 5 5'), ('l', '8 8 8'),
    ('m', '6 6 6'), ('n', '6 6 6'), ('o', '0 NC NC'), ('p', '7 7 7'), ('q', '5 5 5'), ('r', '9 9 9'), ('s', '4 4 4'),
    ('t', '3 3 3'), ('u', '0 NC NC'), ('v', '7 7 7'), ('w', '7 7 7'), ('x', '5 54 54'), ('y', '1 NC NC'),
    ('z', '4 4 4'))]
VOWELS = set('aeiouy')
CYRILLIC_VOWELS = set('аеёиоуыэюяъ')


class Key:
    """Rules of the family's region pack (sound values) and chosen language packs (letters, endings)."""

    def __init__(self, sound, letters, iotated, after_soft, soft, prefixes, endings):
        self.sound, self.letters, self.iotated, self.after_soft, self.soft = sound, letters, iotated, after_soft, soft
        self.prefixes = [re.compile(p) for p in prefixes]
        self.endings = [(re.compile(p), r) for p, r in endings]

    def translit(self, word):
        w = re.sub(r'\[[^\]]*\]|[?*()]', '', str(word).casefold()).strip()
        out = []
        for i, ch in enumerate(w):
            prev, nxt = (w[i - 1] if i else ''), (w[i + 1] if i + 1 < len(w) else '')
            if ch == 'ь' and nxt in self.after_soft:
                out.append(self.soft)
            elif ch in self.after_soft and prev == 'ь':
                out.append(self.after_soft[ch])
            elif ch in self.iotated and (not prev or prev in CYRILLIC_VOWELS or not prev.isalpha()):
                out.append(self.iotated[ch])
            else:
                out.append(self.letters.get(ch, ch))
        return ''.join(out)

    @staticmethod
    def fold(text):
        text = text.replace('ł', 'l').replace('ż', 'zh').replace('ź', 'zh')
        text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
        return re.sub(r'[^a-z]', '', text)

    def stem(self, surname):
        """Masculine nominative stem: -owa, -ówna, -ska, -ая, act cases and 'z ...ich' fold to one spelling."""
        w = self.translit(surname).replace('ówna', 'owna')
        for prefix in self.prefixes:
            w = prefix.sub('', w)
        for pattern, replacement in self.endings:
            new = pattern.sub(replacement, w)
            if new != w:
                return new
        return w

    def sound_codes(self, text):
        w = self.fold(text)
        if not w:
            return frozenset()
        branches, i = [('', None)], 0
        while i < len(w):
            for pat, start, vowel, other in DM_RULES:
                if w.startswith(pat, i):
                    nxt = w[i + len(pat):i + len(pat) + 1]
                    col = self.sound.get(pat) or (start if i == 0 else vowel if nxt in VOWELS else other)
                    new = []
                    for code, last in branches:
                        for alt in col.split('|'):
                            new.append((code, None) if alt == 'NC' else (code, last) if alt == last else (code + alt, alt))
                    branches = list(dict.fromkeys(new))
                    i += len(pat)
                    break
            else:
                i += 1
        return frozenset((c + '000000')[:6] for c, _ in branches)

    def relation(self, a, b, kind):
        """'same stem' | 'sound' | None. Places also share their first two letters: a village name is short."""
        if kind == 'surname':
            sa, sb = self.stem(a), self.stem(b)
            if self.fold(sa) == self.fold(sb):
                return 'same stem'
            return 'sound' if self.sound_codes(sa) & self.sound_codes(sb) else None
        fa, fb = self.fold(self.translit(a)), self.fold(self.translit(b))
        if fa == fb:
            return 'same letters'
        return 'sound' if fa[:2] == fb[:2] and self.sound_codes(fa) & self.sound_codes(fb) else None


def key(instance):
    """The family's key, or None when no region pack declares one."""
    if hasattr(instance, '_name_key'):
        return instance._name_key
    sound = None
    for pack in instance.packs:
        if file := pack['data'].get('pack', {}).get('files', {}).get('name_key'):
            sound = (sound or {}) | read(pack_file(pack, file)).get('sound', {})
    letters, iotated, after_soft, soft, prefixes, endings = {}, {}, {}, 'i', [], []
    for pack in instance.language_pack_data.values():
        rules = pack['data'].get('language', {}).get('surname_key', {})
        letters |= rules.get('letters', {})
        iotated |= rules.get('iotated', {})
        after_soft |= rules.get('after_soft', {})
        soft = rules.get('soft_before_vowel', soft)
        prefixes += rules.get('prefixes', [])
        endings += [tuple(e) for e in rules.get('endings', [])]
    instance._name_key = Key(sound, letters, iotated, after_soft, soft, prefixes, endings) if sound is not None else None
    return instance._name_key


def _place_words(text):
    head = re.split(r'[,(]', text)[0]
    return [w for w in re.findall(r'[^\W\d_]+', head) if w[:1].isupper() and len(w) >= 4]


def vocabulary(instance, kind, entries):
    """Spellings the family already wrote: dictionary forms, clan decisions and tree names. No record prose."""
    cache = instance.__dict__.setdefault('_key_vocabulary', {})
    if kind in cache:
        return cache[kind]
    words = {}
    for entry in entries:
        if entry['kind'] == kind:
            for form in entry['forms']:
                if '*' not in form['text'] and '?' not in form['text']:
                    words.setdefault(form['text'], 'dictionary ' + entry.get('id', ''))
    if kind in {'surname', 'place'}:
        from familiar.tree.builder import _build, read_json
        graph = _build(instance)
        if kind == 'surname':
            from familiar.tree.surnames import birth_names
            for row in read_json(instance.path('tree_metadata'), {}).get('surname_forms', []):
                for form in [row.get('form'), *row.get('variants', [])]:
                    if form:
                        words.setdefault(form, 'clan ' + row.get('id', ''))
            for own in birth_names(graph).values():
                for name in own:
                    if name.get('surname'):
                        words.setdefault(name['surname'], 'tree')
        else:
            for person in graph['people'].values():
                for event in person.get('events', []):
                    for word in _place_words(str(event.get('place') or '')):
                        words.setdefault(word, 'tree')
    cache[kind] = words
    return words


def key_forms(instance, word, kind, known, entries):
    """Forms the family wrote that share the word's key and are not already among the dictionary's forms."""
    rules = key(instance)
    if rules is None or kind not in {'surname', 'place'}:
        return []
    seen = {k.casefold() for k in known}
    return [{'text': form, 'via': 'key', 'key': how, 'from': origin}
            for form, origin in vocabulary(instance, kind, entries).items()
            if form.casefold() not in seen and (how := rules.relation(word, form, kind))]


def findings(instance, graph, metadata):
    """Hint: tree surnames that share a key but are neither one clan decision nor one dictionary entry."""
    rules = key(instance)
    if rules is None:
        return []
    from familiar.tree.surnames import birth_names, clan_key

    from .search_variants import _entries
    people = {}
    for pid, own in birth_names(graph).items():
        for name in own:
            if name.get('surname') and not graph['people'][pid].get('placeholder'):
                people.setdefault(name['surname'], set()).add(pid)
    joined = [{clan_key(v) for v in [r.get('form', ''), *r.get('variants', [])]} for r in metadata.get('surname_forms', [])]
    joined += [{clan_key(f['text']) for f in e['forms']} for e in _entries(instance) if e['kind'] == 'surname']
    forms = sorted(people)
    parent = {f: f for f in forms}
    stems = {form: rules.stem(form) for form in forms}
    folded = {form: rules.fold(stem) for form, stem in stems.items()}
    sounds = {form: rules.sound_codes(stem) for form, stem in stems.items()}

    def root(f):
        while parent[f] != f:
            parent[f] = parent[parent[f]]
            f = parent[f]
        return f
    for i, a in enumerate(forms):
        for b in forms[i + 1:]:
            if folded[a] == folded[b] or sounds[a] & sounds[b]:
                parent[root(a)] = root(b)
    groups = {}
    for f in forms:
        groups.setdefault(root(f), []).append(f)
    result = []
    for spellings in groups.values():
        clans = {clan_key(s) for s in spellings}
        if len(clans) < 2 or any(clans <= j for j in joined):
            continue
        widest = max(joined, key=lambda j: len(clans & j), default=set())
        result.append({'location': 'tree_metadata.surname_forms', 'kind': 'same-key', 'spellings': spellings,
                       'outside': [s for s in spellings if clan_key(s) not in widest] if clans & widest else [],
                       'people': sorted(set().union(*(people[s] for s in spellings))),
                       'message': 'эти написания похожи на одну фамилию по ключу; если это один род — '
                                  'familiar tree surname set ID --variant FORM ... или формы в family/variants.json; '
                                  'если разные — ничего не делать'})
    return result
