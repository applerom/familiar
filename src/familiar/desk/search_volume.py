# START_MODULE_CONTRACT: MOD-DESK-SEARCH-VOLUME
# PURPOSE: Show rough anonymous search volume from existing journals and region source catalogues.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - normalization happens only in this display; collectors acquire no steps, fields or checks [review: engine lead]
# - growth means first journal appearance in the last three recorded working days, not catalogue discovery [review: engine lead]
# - only counts and ordinal days leave the coverage projection; unknown classes stay other [review: browser walk]
# CHANGES_WITH:
# - MOD-DESK-SHOW (anonymous coverage)
# - MOD-SEARCH-LEDGER (source ids and aliases)
# - MOD-RESEARCH-COVERAGE (optional catalogue place aliases for planning)
# :END_MODULE_CONTRACT
import re
import tomllib
from collections import Counter, defaultdict
from datetime import date
from urllib.parse import urlsplit

from familiar.instance.packs import pack_file


def name_key(value):
    return re.sub(r'\s+', ' ', value.strip().casefold()).replace('_', '-')


def domain(value):
    """A URL, bare domain or domain/path; never an arbitrary source title."""
    try:
        parsed = urlsplit(value if '://' in value else '//' + value)
        host = (parsed.hostname or '').casefold().rstrip('.')
        host = host.encode('idna').decode('ascii')
        return host.removeprefix('www.') if '.' in host and ' ' not in host else ''
    except (ValueError, UnicodeError):
        return ''


ALIASES = {
    'obd-memorial': ['ОБД', 'ОБД Мемориал', 'ОБД-Мемориал', 'obd', 'obd-memorial.ru', 'ОБД Мемориал / архивный образ'],
    'pamyat-naroda': ['Память народа', 'Память-народа', 'pamyat naroda', 'pamyat-naroda.ru'],
    'podvig-naroda': ['Подвиг народа', 'Подвиг-народа', 'podvignaroda.ru', 'podvig-naroda.ru', 'podvignaroda'],
    'familysearch': ['FamilySearch', 'Family Search', 'familysearch.org'],
    'familysearch-tree': ['FamilySearch Tree', 'FamilySearch Family Tree'],
    'familysearch-records': ['FamilySearch Records', 'FamilySearch Catalog', 'familysearch-catalog'],
    'familysearch-fulltext': ['FamilySearch Full-Text', 'FamilySearch Full-Text original', 'familysearch.fulltext'],
    'zhnivo': ['Жніво', 'Zhnivo'],
    'represii-by': ['represii', 'represii.net'],
    'stsg-pows': ['stsg-pow', 'Dokumentationsstelle Dresden / Soviet prisoners of war'],
    'yad-vashem': ['Yad Vashem'],
    'jri-poland': ['jri-poland-legacy'],
    'archives-by': ['by-archives'],
    'web-search': ['web-search', 'google', 'Встроенный веб-поиск', 'Встроенный веб-поиск среды',
                   'встроенный web search', 'web search tool through host source_gate'],
    'geneteka': ['Geneteka', 'geneteka.genealodzy.pl'],
    'szukajwarchiwach': ['Szukaj w Archiwach', 'szukajwarchiwach.gov.pl', 'szukajwarchiwach.pl'],
    'myheritage': ['MyHeritage', 'My Heritage', 'myheritage.com', 'myheritage.pl', 'myheritage.ru'],
    'ancestry': ['Ancestry', 'ancestry.com'],
    'geni': ['Geni', 'geni.com'],
}


class Sources:
    def __init__(self, instance, read=None):
        read = read or (lambda p: p.read_bytes() if p.is_file() else None)
        self.sources, self.names, self.domains = {}, defaultdict(set), defaultdict(set)
        self.coverage_places = []
        for sid, aliases in ALIASES.items():
            for alias in [sid, *aliases]:
                self.names[name_key(alias)].add(sid)
                if host := domain(alias):
                    self.domains[host].add(sid)
        entries = []
        for pack in instance.packs:
            name = pack['data'].get('pack', {}).get('files', {}).get('sources')
            if name:
                data = tomllib.loads(read(pack_file(pack, name)).decode('utf-8-sig'))
                entries.extend(data.get('source', []))
                self.coverage_places.extend(data.get('coverage', {}).get('places', []))
        for entry in entries:
            sid = entry.get('id')
            if not isinstance(sid, str) or not sid.strip():
                continue
            sid = self.canonical(sid)
            self.sources[sid] = self.sources.get(sid, {}) | entry
            for alias in [entry['id'], entry.get('title', ''), *entry.get('aliases', [])]:
                if isinstance(alias, str) and alias.strip():
                    self.names[name_key(alias)].add(sid)
            for host in entry.get('domains', []):
                if isinstance(host, str) and (host := domain(host)):
                    self.domains[host].add(sid)

    def canonical(self, value):
        if isinstance(value, dict):
            value = next((value[k] for k in ('id', 'source_id', 'url', 'domain', 'title', 'name')
                          if isinstance(value.get(k), str) and value[k].strip()), '')
        if not isinstance(value, str) or not value.strip():
            return ''
        key = name_key(value)
        matches = self.names.get(key, set())
        if len(matches) == 1:
            return next(iter(matches))
        if host := domain(value):
            # Longest declared domain wins; shared host domains never force a merge.
            for candidate in [host, *['.'.join(host.split('.')[n:])
                                      for n in range(1, len(host.split('.')) - 1)]]:
                matches = self.domains.get(candidate, set())
                if matches:
                    return next(iter(matches)) if len(matches) == 1 else host
            return host
        return key

    def category(self, sid):
        source = self.sources.get(sid, {})
        classes = set(source.get('classes', []))
        # Multi-purpose catalogues use one deterministic category, never several counts.
        for category, members in CATEGORIES.items():
            if classes & members:
                return category
        return 'other'


CATEGORIES = {
    'military': {'military', 'award'},
    'registers': {'parish-register', 'civil-register', 'census-revision'},
    'census': {'census', 'household-book', 'village-council'},
    'trees': {'family-tree', 'tree'},
    'repression': {'repression', 'forced-labour', 'special-settlement'},
    'press': {'memory-book', 'newspaper', 'press'},
    'other': set(),
}


def coverage(rows, catalog):
    """Count recorded attempts, retaining undated attempts without inventing days."""
    visits, source_days, first, undated_sources = Counter(), defaultdict(set), {}, set()
    checked, kinds = set(), Counter()
    requests = undated = gaps = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        sid = catalog.canonical(row.get('source_id') or row.get('source'))
        if not sid:
            continue
        checked.add(sid)
        requests += 1
        kinds[catalog.category(sid)] += 1
        gaps += row.get('result_state') == 'access-gap'
        try:
            day = date.fromisoformat(str(row.get('at', ''))[:10]).isoformat()
        except ValueError:
            undated += 1
            undated_sources.add(sid)
            continue
        visits[day] += 1
        source_days[sid].add(day)
        first[sid] = min(day, first.get(sid, day))
    if not requests:
        return None
    days = sorted(visits)
    recent = set(days[-3:])
    return {'known': len(set(catalog.sources) | checked), 'checked': len(checked),
            'requests': requests, 'days': len(days), 'daily': [visits[d] for d in days],
            'new': sum(day in recent and sid not in undated_sources for sid, day in first.items()),
            'recent_days': min(3, len(days)),
            'repeated': sum(len(value) > 1 for value in source_days.values()),
            'categories': {key: kinds[key] for key in CATEGORIES if kinds[key]},
            'undated': undated, 'access_gaps': gaps}
