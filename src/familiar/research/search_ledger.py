# START_MODULE_CONTRACT: MOD-SEARCH-LEDGER
# PURPOSE: Name the people, the catalogue source and the executor of each search journal row, and carry old rows over once without losing their text.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - migration preserves original text and normalizes ids, counts and incomplete outcomes without inventing negative evidence [review: engine lead]
# - an uncertain person or source match is left empty and counted, never guessed [review: engine lead]
# - repeated migration only enriches an executor, catalogue source or inferred person; archive originals remain unchanged [review: engine lead]
# - nothing is written without apply, and only through the family writer [review: engine lead]
# CHANGES_WITH:
# - MOD-RESEARCH-COVERAGE (reads the ledger form)
# - MOD-INSTANCE-VALIDATION (ledger findings)
# - docs/research-coverage.md
# :END_MODULE_CONTRACT
import difflib
import hashlib
import json
import math
import re
from collections import Counter
from fnmatch import fnmatchcase
from functools import lru_cache
from urllib.parse import unquote_plus

from familiar.desk.search_volume import ALIASES, Sources, domain, name_key
from familiar.instance.gate import boundary
from familiar.intake.names import _form as latin_form

from .search_variants import _entries, norm

EFFORT = re.compile(r'(?<![a-z0-9])(xhigh|max|high|medium|low)(?![a-z0-9])', re.I)
MODEL = re.compile(r'gpt[-\s]?[\d.]+[-\s]?(?:sol|terra)|claude[-\s]?(?:opus|sonnet|haiku)(?:[-\s]?[\d.]+)?|'
                   r'(?<![a-z0-9])(?:sol|terra|opus|sonnet|haiku)(?![a-z0-9])|(?<![a-z0-9])(?:codex|claude)(?![a-z0-9])', re.I)
HUMAN = re.compile(r'(?<![\w])(owner|host|human|хозяин|владелец)(?![\w])', re.I)
WEB = re.compile(r'google|web[- ]?search|веб-?поиск', re.I)
WORD = re.compile(r'[^\W\d_]+[\w*?]*')
METHOD = re.compile(r'host browser|host source_gate ledger|встроенный веб-ридер', re.I)
VOWELS = set('aeiouyаеёиоуыэюя')


def parse_by(value):
    """{agent, model, effort} from a journal's free text; the text itself survives as as_written."""
    if isinstance(value, dict):
        return {**value, 'agent': value.get('agent') or None, 'model': value.get('model') or None,
                'effort': value.get('effort') or None}
    text = str(value or '').strip()
    found = list(MODEL.finditer(text))
    specific = [m for m in found if re.search(r'sol|terra|opus|sonnet|haiku', m.group(0), re.I)]
    model = (specific or found or [None])[0]
    stripped = text
    for m in sorted(found, key=lambda m: -m.start()):
        stripped = stripped[:m.start()] + ' ' + stripped[m.end():]
    effort = list(EFFORT.finditer(stripped))
    effort = effort[-1] if effort else None
    if effort:
        stripped = stripped[:effort.start()] + ' ' + stripped[effort.end():]
    human = HUMAN.search(text)
    parts = [p.strip(' -_') for p in re.split(r'[/;,()]', stripped)]
    agent = next((p for p in parts if p), None) or text or None
    return {'agent': agent,
            'model': re.sub(r'[-\s]+', '-', model.group(0).lower()) if model else 'human' if human else None,
            'effort': effort.group(1).lower() if effort else None, 'as_written': text}


class Resolver:
    """Source text to a catalogue id: the pack catalogue, shared aliases, then domains."""

    def __init__(self, instance):
        self.catalog = Sources(instance)
        self.known = set(self.catalog.sources) | set(ALIASES)
        self._resolved_text = lru_cache(maxsize=4096)(self._resolve_text)

    def source(self, text):
        """(id, hint): an id of the catalogue, or None with the nearest id as advice."""
        if isinstance(text, dict):
            for key in ('id', 'source_id', 'kind', 'url', 'domain', 'title', 'name', 'holder'):
                if text.get(key) and (sid := self.source(text[key])[0]):
                    return sid, None
            return None, None
        if not isinstance(text, str) or not text.strip():
            return None, None
        return self._resolved_text(text)

    def _resolve_text(self, text):
        if METHOD.search(text):
            return None, None
        text = {'pamyat': 'pamyat-naroda', 'ww1': 'gwar', 'szukaj': 'szukajwarchiwach', 'web': 'web-search'}.get(text, text)
        if text in self.known:
            return text, None
        sid = self.catalog.canonical(text)
        if sid in self.known:
            return sid, None
        if WEB.search(text) and domain(text) not in {'docs.google.com', 'drive.google.com'}:
            return 'web-search', None
        near = difflib.get_close_matches(name_key(text), sorted(self.known), n=1, cutoff=.5)
        return None, near[0] if near else None

    def row_source(self, row):
        query = row.get('query') if isinstance(row.get('query'), dict) else {}
        # Historical imports used one id. Recover a channel from preserved text/URLs before that generic id wins.
        raw = json.dumps({k: row.get(k) for k in ('source', 'source_as_written', 'query', 'url', 'final_url')}, ensure_ascii=False).lower()
        declared, _ = self.source(row.get('source'))
        if (not declared or declared.startswith('familysearch')) and ('familysearch' in raw or 'family search' in raw):
            if re.search(r'full[- ._]?text|/search/full', raw):
                return 'familysearch-fulltext'
            if re.search(r'familysearch-tree|/tree/|/search/tree|familysearch[^"\n]{0,12}tree', raw):
                return 'familysearch-tree'
            if re.search(r'familysearch[- ._]?(?:records|catalog)|familysearch[^"\n]{0,12}records|/search/record|/ark:/|/search/catalog|/search/film', raw):
                return 'familysearch-records'
        for text in [row.get('source'), row.get('site'), row.get('url'), row.get('final_url'), query.get('site'), query.get('url')]:
            source, _ = self.source(text)
            if source:
                return source
        for url in re.findall(r'https?://[^\s<>"\)]+', json.dumps(row.get('query'), ensure_ascii=False) + ' ' + str(row.get('source') or '')):
            source, _ = self.source(url)
            if source:
                return source
        return None


def stem(form):
    return form[:-1] if len(form) > 4 and form[-1] in VOWELS else form


def tokens(text):
    return [norm(t) for t in WORD.findall(text)]


def is_review(row):
    query = row.get('query')
    return isinstance(query, dict) and (query.get('mode') == 'review' or 'review' in query)


def row_tokens(row):
    """Words of the actual query and of the forms the researcher says were read."""
    out = []

    def walk(value):
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str):
            out.extend(tokens(unquote_plus(value) if '%' in value else value))

    walk(row.get('query'))
    coverage = row.get('coverage')
    walk(coverage.get('forms') if isinstance(coverage, dict) else None)
    return out


def given_groups(instance, kind='given_name'):
    """norm(given-name form) -> every form of the same variant entries (pack and family)."""
    groups = {}
    for entry in _entries(instance):
        if entry.get('kind') == kind:
            forms = {norm(f['text']) for f in entry['forms']} | {norm(entry.get('canonical', ''))}
            for form in forms:
                groups.setdefault(form, set()).update(forms)
    return groups


class Tree:
    """The people of the tree as search forms; names only, no judgement of identity."""

    def __init__(self, instance, graph=None):
        if graph is None:
            from familiar.tree.builder import _build
            graph = _build(instance)
        self.groups = given_groups(instance)
        self.surname_groups = given_groups(instance, 'surname')
        self.shown = {norm(f['text']): f['text'] for e in _entries(instance) for f in e['forms']}
        self.people, self.stems, self.exact = {}, {}, {}
        self.latin_form = lru_cache(maxsize=8192)(latin_form)
        for pid, person in graph['people'].items():
            surnames, givens = {}, set()
            for name in person.get('names', []) or []:
                if name.get('surname'):
                    surnames.setdefault(norm(name['surname']), name['surname'])
                if name.get('given'):
                    givens.update(tokens(name['given']))
            for form, shown in list(surnames.items()):
                for variant in self.surname_groups.get(form, ()):
                    surnames.setdefault(variant, self.shown.get(variant, shown))
            for form in list(givens):
                givens |= self.groups.get(form, set())
            required = dict(surnames) | {f: self.shown[f] for f in givens if f in self.shown}
            givens |= {self.latin_form(form) for form in givens} - {''}
            for form, shown in list(surnames.items()):
                if latin := self.latin_form(form):
                    surnames.setdefault(latin, shown)
            label = next((n.get('display') for n in person.get('names', []) if n.get('display')), None) or person.get('name') or pid
            shown = label.split(' ·')[0]
            self.people[pid] = {'id': pid, 'name': shown, 'surnames': surnames, 'givens': givens, 'required_forms': required}
            for form in surnames:
                key = stem(form)
                (self.stems if len(key) >= 4 else self.exact).setdefault(key, set()).add(pid)
        self.aliases = graph.get('identityAliases', {})
        self.graph = graph

    def person(self, ident):
        ident = self.aliases.get(ident, ident)
        return self.people.get(ident)

    def match(self, words):
        """People whose surname form and given name both appear among the words."""
        words = set(words) | {self.latin_form(w) for w in words} - {''}
        by_surname = set()
        for word in words:
            by_surname |= self.exact.get(word, set())
            for k in range(4, len(word) + 1):
                by_surname |= self.stems.get(word[:k], set())
        return sorted(p for p in by_surname if self.people[p]['givens'] & words)

    def missing_surnames(self, pid, words):
        """Tree surname and dictionary surname/given-name forms not covered, including query masks."""
        words = set(words) | {self.latin_form(w) for w in words} - {''}
        out = []
        for form, shown in self.people[pid]['required_forms'].items():
            key = stem(form)
            seen = any(fnmatchcase(form, w) or fnmatchcase(w, form) if '*' in w + form or '?' in w + form else
                       w == form or (len(key) >= 4 and w.startswith(key)) for w in words)
            if not seen:
                out.append(shown)
        return list(dict.fromkeys(out))


def read_versions(instance):
    """Question id -> saved question, with its tree people normalized for the ledger."""
    result = {}
    base = instance.path('versions')
    for file in sorted(base.rglob('*.json')) if base.exists() else []:
        try:
            data = json.loads(file.read_text(encoding='utf-8-sig'))
        except (ValueError, OSError):
            continue
        if isinstance(data, dict) and isinstance(data.get('id'), str):
            people = data.get('people', [])
            people = list(people.values()) if isinstance(people, dict) else people
            result[data['id']] = data | {'people': [p for p in people if isinstance(p, str)]
                                        if isinstance(people, list) else []}
    return result


def infer_people(tree, versions, row):
    """(people, basis) or ([], None) when the match is not clear."""
    asked = [p for p in versions.get(row.get('question'), {}).get('people', []) if tree.person(p)]
    asked = [tree.aliases.get(p, p) for p in asked]
    named = tree.match(row_tokens(row))
    both = [p for p in asked if p in named]
    if both:
        return both, 'question+name'
    if 0 < len(named) <= 3:
        return named, 'name'
    if 0 < len(asked) <= 3:
        return asked, 'question'
    return [], None


def search_files(instance):
    base = instance.path('searches')
    return sorted(p for p in base.rglob('*') if p.suffix in {'.json', '.jsonl'}
                  and not any(part.startswith('.') for part in p.relative_to(base).parts)) if base.exists() else []


def read_rows(path):
    """(rows, single): the objects of one journal file, None when it is broken (reported, never rewritten)."""
    try:
        text = path.read_text(encoding='utf-8-sig')
        if path.suffix == '.jsonl':
            return [json.loads(line) for line in text.splitlines() if line.strip()], False
        data = json.loads(text)
        return (data if isinstance(data, list) else [data]), not isinstance(data, list)
    except (ValueError, OSError):
        return None, False


def in_ledger_form(row):
    return isinstance(row.get('by'), dict) and isinstance(row.get('people'), list)


def upgrade(row, resolver, tree, versions, stats):
    """The row with the ledger fields; only appends and rewrites source and by."""
    row = dict(row)
    if not isinstance(row.get('id'), str) or not row['id'].strip():
        row['id'] = 'legacy-' + row_digest(row)
    stats['rows'] += 1
    if isinstance(row.get('by'), str):
        by = parse_by(row['by'])
        row['by'] = by
        stats['by_model'] += bool(by['model'])
        stats['by_effort'] += bool(by['effort'])
    source = resolver.row_source(row)
    if source and source != row.get('source'):
        row.setdefault('source_as_written', row.get('source'))
        row['source'] = source
    if source:
        stats['source_known'] += 1
    else:
        stats['source_unknown'][str(row.get('source'))[:80]] += 1
    if isinstance(row.get('people'), list):
        stats['people_declared'] += 1
        row.setdefault('people_basis', 'declared')
    else:
        people, basis = infer_people(tree, versions, row)
        row['people'] = people
        row['people_basis'] = 'inferred' if people else 'unresolved'
        if basis:
            row['people_from'] = basis
        stats['people_inferred' if people else 'people_unresolved'] += 1
        stats['people_seen'].update(people)
    return row


def fresh_stats():
    return {'rows': 0, 'by_model': 0, 'by_effort': 0, 'source_known': 0, 'source_unknown': Counter(),
            'people_declared': 0, 'people_inferred': 0, 'people_unresolved': 0, 'people_seen': Counter()}


def executor_map(path):
    """Explicit host evidence, supplied by the caller; the engine never reads a host ledger."""
    if path is None:
        return {}
    from pathlib import Path
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or any(not isinstance(k, str) or not k or
            not isinstance(v, dict) or any(not isinstance(v.get(f), str) or not v[f].strip()
                                          for f in ('model', 'effort')) for k, v in data.items()):
        raise ValueError('executors must map labels or prefixes to {model, effort}')
    return data


def enrich(row, tree, versions, executors, counts, resolver):
    row = dict(row)
    if not isinstance(row.get('id'), str) or not row['id'].strip():
        row['id'] = 'legacy-' + row_digest(row)
    source = resolver.row_source(row)
    if source and source != row.get('source'):
        row.setdefault('source_as_written', row.get('source'))
        row['source'] = source
    by = parse_by(row.get('by'))
    labels = [str(by.get(k) or '') for k in ('agent', 'as_written')]
    matches = [(len(key), value) for key, value in executors.items()
               if any(label == key or (label.startswith(key) and label[len(key):len(key)+1] in '-_/ ;(')
                      for label in labels)]
    if matches:
        longest = max(n for n, _ in matches)
        choices = {(v['model'], v['effort']) for n, v in matches if n == longest}
        if len(choices) == 1:
            model, effort = choices.pop()
            # Explicit, already recorded model/effort are stronger than a prefix map.
            generic = by.get('model') in {None, 'codex', 'claude'}
            compatible = generic or re.search(r'(?<![a-z0-9])' + re.escape(by['model']) + r'(?![a-z0-9])', model, re.I)
            if compatible and by.get('effort') in {None, effort} and (not by.get('effort') or generic):
                new = by | {'model': model if generic else by['model'], 'effort': by.get('effort') or effort}
                if new != by:
                    row['by'], row['by_basis'] = new, 'executor-map'
                    counts['executor_rows'] += 1
    if row.get('people_from') == 'question' or (row.get('people_basis') == 'unresolved'):
        people, basis = infer_people(tree, versions, row)
        if people and basis != 'question':
            row.update(people=people, people_basis='inferred', people_from=basis)
            counts['people_refined'] += 1
    return row


def legacy_row(row):
    """Normalize known old shapes, keeping every original field and uncertain outcome."""
    if not isinstance(row, dict) or not all(row.get(k) for k in ('at', 'source', 'by')) or 'query' not in row:
        return None
    out = dict(row)
    result = row.get('result')
    if not isinstance(result, dict):
        results = row.get('results')
        result = results[0] if isinstance(results, list) and len(results) == 1 and isinstance(results[0], dict) else {}
    state = row.get('result_state') or row.get('state') or result.get('state') or row.get('status')
    state = str(state or '').lower()
    blocked = row.get('protected') is True or row.get('sent_to_site') is False or row.get('gate_refused') is True
    blocked |= any(s in state for s in ('refus', 'captcha', 'not_ready', 'not-ready', 'login', 'timeout', 'error', 'incomplete')) or state in {'401', '403', '429', '503'}
    if blocked:
        if 'result_state' in out and out['result_state'] != 'access-gap':
            out['result_state_as_written'] = out['result_state']
        out['result_state'] = 'access-gap'
    elif 'result_state' not in out:
        out['result_state'] = 'access-gap' if blocked else state or 'unknown'
    hits = count(row.get('hits'))
    if hits is None:
        hits = count(row.get('count'))
    if hits is None:
        hits = count(result.get('count'))
    if hits is None and isinstance(row.get('results'), list) and row['results']:
        values = [count(r.get('count')) if isinstance(r, dict) else None for r in row['results']]
        if all(v is not None for v in values):
            hits = count(sum(values))
    if out.get('hits') != hits or type(out.get('hits')) is not type(hits):
        if 'hits' in out:
            out['hits_as_written'] = out['hits']
    out['hits'] = hits
    coverage = row.get('coverage')
    if not isinstance(coverage, dict):
        if coverage is not None:
            out['coverage_as_written'] = coverage
        out['coverage'] = {'read': row.get('read', row.get('rows_read')), 'forms': [],
                           'note': str(coverage or row.get('coverage_note') or 'Legacy journal: reading scope unknown')}
    coverage = dict(out['coverage'])
    read = count(coverage.get('read'))
    if read != coverage.get('read') or type(read) is not type(coverage.get('read')):
        coverage['read_as_written'] = coverage.get('read')
    coverage['read'] = read
    out['coverage'] = coverage
    incomplete = hits == 0 and not (coverage.get('years') and coverage.get('forms') and read and read > 0)
    if blocked or out['result_state'] == 'access-gap':
        state, meaning = 'access-gap', 'access-gap'
    elif hits is None:
        state, meaning = 'unrecorded', 'unrecorded'
    elif incomplete:
        state, meaning = 'zero-uncontrolled', 'zero-uncontrolled'
    else:
        return out
    for key, value in [('result_state', state), ('meaning', meaning)]:
        if key in out and out[key] != value:
            out.setdefault(key + '_as_written', out[key])
        out[key] = value
    return out


def count(value):
    """Only explicit counts, including old digit strings; never '?' or prose."""
    if isinstance(value, str) and re.fullmatch(r'(?:\d+|\d{1,3}(?:[ \u00a0\u202f]\d{3})+)(?:\.\d+)?', value.strip()):
        value = float(re.sub(r'\s', '', value))
    return value if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 9007199254740991 else None


def row_digest(row):
    origin = row.get('origin')
    if isinstance(origin, dict) and origin.get('sha256'):
        return origin['sha256']
    ignored = {'people_basis', 'people_from', 'by_basis', 'origin', 'source_as_written'}
    if str(row.get('id', '')).startswith('legacy-'):
        ignored.add('id')
    if row.get('people_basis') in {'inferred', 'unresolved'}:
        ignored.add('people')
    original = {k: v for k, v in row.items() if k not in ignored}
    if isinstance(original.get('by'), dict) and 'as_written' in original['by']:
        original['by'] = original['by']['as_written']
    if 'source_as_written' in row:
        original['source'] = row['source_as_written']
    return hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def legacy_files(instance, paths):
    from pathlib import Path
    roots = paths or [instance.root / 'research' / 'team']
    found = set()
    for value in roots:
        path = Path(value)
        path = (instance.root / path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_relative_to(instance.root):
            raise ValueError('legacy journals must be inside the family root')
        if paths and not path.exists():
            raise ValueError(f'legacy journal not found: {path}')
        for p in ([path] if path.is_file() else path.rglob('*.jsonl')):
            if p.name.lower().startswith('searches') and p.resolve().is_relative_to(instance.root) and not p.resolve().is_relative_to(instance.path('searches')):
                found.add(p)
    return sorted(found)


@boundary('writer')
def migrate(instance, *, apply=False, executors=None, legacy=None):
    """One-time carry-over of old rows; a dry run unless apply is set."""
    resolver, tree, versions = Resolver(instance), Tree(instance), read_versions(instance)
    executors = executor_map(executors)
    counts = Counter(executor_rows=0, people_refined=0, legacy_rows=0, legacy_imported=0, legacy_duplicates=0, legacy_unparsed=0)
    seen = set()
    stats, changes, broken, already = fresh_stats(), {}, [], 0
    for path in search_files(instance):
        rows, single = read_rows(path)
        if rows is None:
            broken.append(str(path.relative_to(instance.root)))
            continue
        out = []
        for row in rows:
            if isinstance(row, dict):
                seen.add(row_digest(row))
            if isinstance(row, dict) and not in_ledger_form(row):
                out.append(enrich(upgrade(row, resolver, tree, versions, stats), tree, versions, executors, counts, resolver))
            else:
                out.append(enrich(row, tree, versions, executors, counts, resolver) if isinstance(row, dict) else row)
                already += isinstance(row, dict)
        if out == rows:
            continue
        if path.suffix == '.jsonl':
            text = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in out)
        else:
            text = json.dumps(out[0] if single else out, ensure_ascii=False, indent=2) + '\n'
        changes[path] = text.encode('utf-8')
    for path in legacy_files(instance, legacy):
        out = []
        for number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
            if not line.strip():
                continue
            counts['legacy_rows'] += 1
            try:
                original = json.loads(line)
            except ValueError:
                original = None
            row = legacy_row(original)
            if row is None:
                counts['legacy_unparsed'] += 1
                continue
            digest = row_digest(original)
            if digest in seen:
                counts['legacy_duplicates'] += 1
                continue
            seen.add(digest)
            if 'id' in row:
                row['id_as_written'] = row['id']
            row['id'] = 'legacy-' + digest
            row = enrich(upgrade(row, resolver, tree, versions, stats), tree, versions, executors, counts, resolver)
            row['origin'] = {'path': path.relative_to(instance.root).as_posix(), 'line': number, 'sha256': digest}
            out.append(row)
            counts['legacy_imported'] += 1
        if out:
            rel = path.relative_to(instance.root).as_posix()
            suffix = hashlib.sha256(rel.encode()).hexdigest()[:10]
            slug = re.sub(r'[^\w-]+', '-', path.parent.name).strip('-') or 'archive'
            target = instance.path('searches') / f'legacy-{slug}-{suffix}.jsonl'
            prefix = changes.get(target, target.read_bytes() if target.exists() else b'')
            changes[target] = prefix + (b'\n' if prefix and not prefix.endswith(b'\n') else b'') + ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in out).encode('utf-8')
    if apply and changes:
        from familiar.instance.writer import mutate
        mutate(instance, changes, working_journals=True)
    return {'applied': bool(apply and changes), 'files': len(changes), 'rows_migrated': stats['rows'],
            'rows_already_in_form': already, 'unreadable_files': broken,
            **counts,
            'by': {'with_model': stats['by_model'], 'with_effort': stats['by_effort']},
            'source': {'recognised_rows': stats['source_known'],
                       'unrecognised_rows': sum(stats['source_unknown'].values()),
                       'unrecognised_texts': stats['source_unknown'].most_common(12)},
            'people': {'declared_rows': stats['people_declared'], 'inferred_rows': stats['people_inferred'],
                       'unresolved_rows': stats['people_unresolved'], 'distinct_people': len(stats['people_seen'])}}


def findings(instance, rows_by_file):
    """One advice per file and kind, for rows not in the ledger form or naming no catalogue source."""
    resolver, found = Resolver(instance), []
    for path, rows in rows_by_file.items():
        old = sum(not in_ledger_form(r) for r in rows)
        if old:
            found.append((path, f'{old} search rows are not in the ledger form (people, catalogue source, by as {{agent, model, effort}}); '
                                'run: familiar research migrate-searches'))
        odd = Counter()
        for row in rows:
            if in_ledger_form(row):
                source, hint = resolver.source(row.get('source'))
                if not source:
                    odd[(str(row.get('source'))[:60], hint)] += 1
        for (text, hint), n in odd.items():
            found.append((path, f'{n} rows name source "{text}" that is not a catalogue id'
                                + (f'; nearest: {hint}' if hint else '; add it to the region catalogue or use an existing id')))
        if any(isinstance(r.get('people'), list) and not all(isinstance(p, str) for p in r['people']) for r in rows):
            found.append((path, 'people must be an array of tree ids'))
    return found
