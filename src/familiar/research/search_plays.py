"""The method registry, family preferences and attribution of recorded searches."""
import tomllib
from collections import defaultdict
from functools import cache

from familiar.rules.roles import method_root

from .coverage_context import contains, text
from .search_variants import norm


@cache
def registry():
    return tomllib.loads(method_root().joinpath('research-plays.toml').read_text(encoding='utf-8'))


class PlaySettings:
    def __init__(self, config):
        if not isinstance(config, dict):
            raise ValueError('research must be a table')
        self.focus = config.get('focus', [])
        self.overrides = config.get('plays', {})
        self.plays = {play['id']: play for play in registry()['play']}
        self.default_order = {pid: index for index, pid in enumerate(self.plays, 1)}
        if not isinstance(self.focus, list) or not all(isinstance(name, str) and name.strip() for name in self.focus):
            raise ValueError('research.focus must be an array of line names')
        if not isinstance(self.overrides, dict):
            raise ValueError('research.plays must be a table')
        for pid, options in self.overrides.items():
            if pid not in self.plays:
                raise ValueError(f'research.plays: unknown play {pid}')
            self.validate(options, f'research.plays.{pid}', family=True)
            for name, line in options.get('lines', {}).items():
                self.validate(line, f'research.plays.{pid}.lines.{name}')

    @staticmethod
    def validate(options, path, *, family=False):
        keys = {'enabled', 'order'} | ({'lines'} if family else set())
        if not isinstance(options, dict) or options.keys() - keys:
            raise ValueError(f'{path} must contain enabled, order or a line override')
        if type(options.get('enabled', True)) is not bool or type(options.get('order', 1)) is not int:
            raise ValueError(f'{path}: enabled must be boolean and order must be integer')
        if family and not isinstance(options.get('lines', {}), dict):
            raise ValueError(f'{path}.lines must be a table')

    def choices(self, forms, line_keys):
        choices = []
        for pid, play in self.plays.items():
            options = self.overrides.get(pid, {})
            line = next((v for name, v in options.get('lines', {}).items()
                         if line_keys(name) & forms), {})
            order = line.get('order', options.get('order', self.default_order[pid]))
            enabled = line.get('enabled', options.get('enabled', True))
            choices.append((order, enabled, play))
        return sorted(choices, key=lambda choice: choice[0])


SURNAME = {'surname', 'surnames', 'last_name', 'lastName', 'family_name', 'n', 'фамилия'}
PLACE = {'place', 'places', 'place_birth', 'birth_place', 'birthplace', 'parish', 'town',
         'village', 'district', 'province', 'locality', 'region', 'rid', 'w', 'county',
         'birth_place_uezd', 'birth_place_volost'}
CATALOGUE = {'archive', 'fond', 'inventory', 'series', 'catalogue', 'catalog', 'queryType'}
EVENT = {'episode', 'event', 'data_i_mesto_priziva', 'draft_place', 'enlistment_place',
         'recruitment_district', 'prisoner_list', 'unit', 'regiment'}
HOUSEHOLD = {'household', 'given_names', 'family_members', 'names'}
INDIVIDUAL = {'given', 'given_name', 'first_name', 'firstName', 'name', 'full_name', 'patronymic',
              'father', 'mother', 'parents', 'spouse', 'child'}


def query_mode(query):
    return str(query.get('mode') or '').strip().lower().replace('_', '-').replace(' ', '-')


def query_label(row, source, places=(), surnames=()):
    """Old observations require a source class and an identifiable query axis."""
    if 'play' in row:
        play = row['play']
        return (play, 'recorded') if isinstance(play, str) and play in play_ids() else (None, 'unrecorded')
    query = row.get('query')
    query = query if isinstance(query, dict) else {}
    mode, keys = query_mode(query), {k for k, v in query.items() if v}
    classes = set(source.get('classes', []))
    if mode in {'archive-letter', 'request', 'enquiry', 'inquiry'} and source.get('kind') in {'archive', 'registry'}:
        return 'archive-letters', 'inferred'
    if mode in {'ask-family', 'family-interview', 'home-document'} and classes & {'family-memory', 'home-paper'}:
        return 'ask-family', 'inferred'
    parish_book = bool(classes & {'parish-register', 'civil-register'})
    if parish_book:
        if keys & {'witness', 'witnesses', 'godparent', 'godparents', 'neighbour', 'neighbor'}:
            return 'neighbors-godparents', 'inferred'
        if 'household' in keys or mode in {'household', 'household-fingerprint'}:
            return 'household-fingerprint', 'inferred'
    if mode == 'family-reconstitution':
        if parish_book and keys & HOUSEHOLD:
            return 'household-fingerprint', 'inferred'
        if (classes & play_classes('place-nest') and keys & SURNAME and keys & (PLACE - {'rid', 'w'})
                and not keys & (HOUSEHOLD | INDIVIDUAL)):
            return 'place-nest', 'inferred'
        return None, 'unrecorded'
    term = query.get('query') or query.get('place') or query.get('q')
    coverage = row.get('coverage')
    forms = coverage.get('forms') if isinstance(coverage, dict) else None
    if classes & play_classes('place-administration') and (
            keys & {'record_keeper', 'administration', 'deanery', 'jurisdiction'} or
            mode in {'parish-history', 'church-history', 'place-administration', 'jurisdiction'} or
            'place-reference' in classes and keys & PLACE or
            'record-keeper' in classes and (mode in {'read-topic', 'read', 'lookup'}
                                            or isinstance(forms, list) and any(norm(f) in places for f in forms if isinstance(f, str)))):
        return 'place-administration', 'inferred'
    if 'forum' in classes and (keys & {'topic', 'post', 'queries', 'terms', 'url', 'pages'} or 'forum' in mode):
        return 'forums', 'inferred'
    if 'cemetery' in classes and keys & (PLACE | SURNAME | {'cemetery', 'burial', 'grave', 'terms'}):
        return 'cemeteries', 'inferred'
    if classes & {'archive-guide', 'inventory', 'census-revision', 'consistory'}:
        if keys & CATALOGUE and (keys & PLACE or isinstance(term, str) and place_term(term, places)):
            return 'keeper-forms', 'inferred'
        if keys & {'fond', 'inventory', 'series'} and not keys & SURNAME:
            return 'deep-inventories', 'inferred'
    if classes & play_classes('generation-events') and keys & EVENT:
        if keys & {'birth_year', 'year_birth', 'birth_date', 'date_birth', 'year', 'years'} or mode in {'event-list', 'cohort'}:
            return 'generation-events', 'inferred'
    if source.get('kind') == 'index' or classes & {'web-search', 'name-index'}:
        if keys & SURNAME and keys & (PLACE | {'data_i_mesto_priziva', 'draft_place'}):
            return 'surname-place', 'inferred'
        written = [query[k] for k in ('query', 'queries', 'terms', 'q', 'q_requested') if k in query]
        if isinstance(row.get('query'), str):
            written.append(row['query'])
        for value in written:
            for term in value if isinstance(value, list) else [value]:
                phrase = text(term)
                if any(contains(phrase, name) for name in surnames) and any(contains(phrase, place) for place in places):
                    return 'surname-place', 'inferred'
    return None, 'unrecorded'


@cache
def play_ids():
    return frozenset(play['id'] for play in registry()['play'])


@cache
def play_classes(pid):
    return frozenset(next(play['classes'] for play in registry()['play'] if play['id'] == pid))


def source_classes(sid, source):
    if sid == 'web-search':
        return source | {'classes': [*source.get('classes', []), 'web-search']}
    return source


def query_places(row):
    query = row.get('query')
    if not isinstance(query, dict):
        return []
    return [text(query[key]) for key in query.keys() & PLACE - {'rid', 'w'} if text(query[key])]


def query_surnames(row):
    query = row.get('query')
    return [text(query[key]) for key in query.keys() & SURNAME] if isinstance(query, dict) else []


def place_term(value, places):
    word = norm(value).rstrip('*')
    return len(word) >= 4 and any(contains(word, place) or place.startswith(word) for place in places)


def bridge_link(link, *, default_status=None):
    status, weight = link.get('status', default_status), link.get('weight')
    return status in {'export', 'verified', 'accepted', 'hypothesis'} and (
        weight is None and status != 'hypothesis' or type(weight) in (int, float) and .5 <= weight <= 1)


def links_to_living(graph):
    """Follow parentage from a living relative without crossing any weak link."""
    parents = defaultdict(set)
    for edge in graph.get('edges', []):
        if bridge_link(edge):
            parents[edge['child']].add(edge['parent'])
    living = {pid for pid, p in graph['people'].items() if p.get('life_assessment', {}).get('status') == 'living'}
    pending = sorted(living)
    linked = set(living)
    for pid in pending:
        new = parents[pid] - linked
        linked.update(new)
        pending.extend(sorted(new))
    return living, linked - living
