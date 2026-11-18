# START_MODULE_CONTRACT: MOD-INTAKE-KINSHIP-CASE
# PURPOSE: Carry a private kinship research case into Familiar's attributed working forms.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - an original case and its normalized files are saved together without overwriting family data [review: engine lead]
# - dependent copies never raise relationship weight; contradictory claims and unknown life remain protected [review: engine lead]
# - a search keeps its declared targets and outcome without inferring negative evidence or original executor strength [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-WRITER
# - MOD-TREE-CONTRIBUTIONS
# - MOD-TREE-LIFE
# - MOD-SEARCH-LEDGER
# :END_MODULE_CONTRACT
import csv
import hashlib
import io
import json
import os
import re
import stat
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from familiar.instance.gate import assertions, boundary
from familiar.instance.research_forms import numeric_errors
from familiar.instance.writer import mutate
from familiar.research.search_ledger import Resolver, count, parse_by

from .core import safe, token

REGISTERS = {
    'people': ('person-register.csv', 'person_id',
               'preferred_label living_status names_as_written normalized_name_variants birth_estimate death_estimate '
               'places historical_jurisdictions relatives_as_reported occupation_or_status '
               'confession_or_community_as_recorded source_artifact_ids candidate_status merge_or_split_rationale notes'),
    'relationships': ('relationship-register.csv', 'relationship_id',
                      'person_a_id relationship_type person_b_id biological_legal_household claim_ids '
                      'supporting_artifact_ids contradicting_artifact_ids independence_groups status confidence rationale'),
    'artifacts': ('artifact-register.csv', 'artifact_id',
                  'captured_at source_title source_url_or_path source_type repository_or_archive archival_reference '
                  'record_date place_as_written language_script person_ids names_as_written summary provenance_level '
                  'directness originality independence_group legibility access_notes sha256 related_claim_ids '
                  'reliability_notes status reading local_file'),
    'claims': ('claims-register.csv', 'claim_id',
               'claim_text subject_person_ids claim_type artifact_ids supporting_independence_groups '
               'contradicting_artifact_ids status confidence rationale next_action'),
    'searches': ('search-log.csv', 'search_id',
                 'timestamp target_person_ids research_goal query language_locale source_or_domain filters '
                 'result_status artifact_ids blocker captcha_attempts next_step'),
}
WEIGHTS = {
    'hypothesis': (.30, .36, .42),
    'unresolved': (.15, .22, .28),
    'single-source': (.36, .43, .49),
    'corroborated': (.55, .65, .75),
    'strongly-corroborated': (.70, .80, .90),
    'contradicted': (0, 0, 0),
}
CONFIDENCE = ('low', 'moderate', 'high')
SCANS = {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff', '.gif', '.bmp', '.pdf'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def parts(value):
    return list(dict.fromkeys(p.strip() for p in re.split(r'[;,]', value) if p.strip()))


def json_object(value):
    try:
        result = json.loads(value, parse_constant=lambda name: None)
    except ValueError:
        return {}
    return result if isinstance(result, dict) else {}


def case_files(folder):
    """Read once so the archive, CSV conversion and checksum checks use the same bytes."""
    files, directories = {}, []
    def unreadable(exc):
        raise exc
    for directory, dirs, names in os.walk(folder, onerror=unreadable, followlinks=False):
        for name in sorted(dirs + names):
            path = Path(directory) / name
            info = path.lstat()
            is_reparse = getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
            if stat.S_ISLNK(info.st_mode) or is_reparse:
                raise ValueError(f'Case contains a linked path: {path.relative_to(folder)}; copy it into the case first')
            key = path.relative_to(folder).as_posix()
            if path.is_dir():
                directories.append(key + '/')
            elif stat.S_ISREG(info.st_mode):
                files[key] = path.read_bytes()
            else:
                raise ValueError(f'Case contains a non-regular file: {key}')
    return files, directories


def zip_case(files, directories):
    out = io.BytesIO()
    with ZipFile(out, 'w') as archive:
        for name in sorted([*files, *directories]):
            archive.writestr(ZipInfo(name), files.get(name, b''), compress_type=ZIP_DEFLATED)
    return out.getvalue()


class Case:
    def __init__(self, instance, folder, files, ident):
        self.instance = instance
        self.folder = folder
        self.files = files
        self.ident = f'kinship-{ident}'
        self.resolver = Resolver(instance)
        self.changes = {}
        self.losses = []
        self.counts = {kind: {'imported': 0, 'skipped': 0} for kind in REGISTERS}
        self.archive_only = files.keys() - {name for name, _, _ in REGISTERS.values()}
        self.people = {}
        self.artifacts = {}
        self.captures = {}
        self.claims = {}
        self.goals = {}
        self.decisions = []
        self.associations = []
        self.package = {'author': 'kinship-case', 'schema': 1, 'people': {}, 'facts': {},
                        'sources': {self.ident: {'kind': 'import', 'intake': self.ident}},
                        'edges': []}

    def loss(self, kind, row, field, reason, *, skip=False):
        self.losses.append({'file': REGISTERS[kind][0], 'row': row, 'field': field, 'reason': reason})
        if skip:
            self.counts[kind]['skipped'] += 1

    def rows(self, kind):
        filename, key, extra = REGISTERS[kind]
        if filename not in self.files:
            raise ValueError(f'Missing case register: {filename}')
        stream = io.StringIO(self.files[filename].decode('utf-8-sig'), newline='')
        reader = csv.DictReader(stream, strict=True)
        headers = reader.fieldnames or []
        if key not in headers or len(set(headers)) != len(headers):
            raise ValueError(f'{filename}: expected unique CSV headers including {key}')
        known = {key, *extra.split()}
        for name in headers:
            if name not in known:
                self.loss(kind, None, name, 'Unknown column; retained in the case ZIP')
        seen = set()
        for row in reader:
            local = (row.get(key) or '').strip()
            location = f'line {reader.line_num}' + (f' ({local})' if local else '')
            if None in row or any(v is None for v in row.values()):
                self.loss(kind, location, key, 'Row has a different number of cells than the header', skip=True)
            elif not re.fullmatch(r'[A-Za-z0-9_-]+', local) or local.lower() in seen:
                self.loss(kind, location, key, 'Missing, invalid or duplicate row ID', skip=True)
            else:
                seen.add(local.lower())
                yield local, defaultdict(str, {k: v for k, v in row.items() if k in known})

    def output_id(self, kind, local):
        return f'{self.ident}-{kind}-{local.lower()}'

    def refs(self, kind, local, field, raw, index):
        refs = []
        for key in parts(raw):
            if key in index:
                refs.append(index[key])
            else:
                self.loss(kind, local, field, f'No imported row for {key!r}')
        return refs

    def read_people(self):
        for local, row in self.rows('people'):
            label = row['preferred_label'].strip()
            if not label:
                self.loss('people', local, 'preferred_label', 'Missing card name', skip=True)
                continue
            pid = self.people[local] = self.output_id('person', local)
            raw = row['living_status'].strip().casefold()
            status = {'deceased': 'dead', 'dead': 'dead', 'living': 'living'}.get(raw, 'unknown')
            if status == 'unknown' and raw not in {'', 'unknown', 'possibly-living', 'possibly living'}:
                self.loss('people', local, 'living_status', f'Unrecognized value {raw!r}; protected as unknown')
            self.decisions.append({'person': pid, 'status': status, 'by': 'kinship-case',
                                   'at': date.today().isoformat(),
                                   'basis': f"Imported case classification: {raw or 'unspecified'}"})
            # Labels and estimates come from a research register. Do not split labels or promote its estimates to events.
            self.package['people'][pid] = {'name': label, 'kinship_case': written(row)}
            self.counts['people']['imported'] += 1

    def saved_file(self, local, row, rid):
        locator = row['source_url_or_path'].strip()
        snapshot = re.search(r'(?:^|;\s*)snapshot=([^;\r\n]+)', row['access_notes'])
        name = row['local_file'].strip() or (snapshot[1].strip() if snapshot else '')
        if not name and locator and '://' not in locator:
            name = locator
        if not name:
            if row['sha256'].strip():
                self.loss('artifacts', local, 'sha256', 'Checksum has no local file in the case')
            return {}
        path = Path(name)
        if path.is_absolute():
            name = path.relative_to(self.folder).as_posix() if path.is_relative_to(self.folder) else name
        else:
            name = path.as_posix()
        if name not in self.files:
            self.loss('artifacts', local, 'source_url_or_path', 'Local file unavailable inside the case')
            return {}
        raw = self.files[name]
        sha = digest(raw)
        expected = row['sha256'].strip().casefold()
        if expected and sha != expected:
            self.loss('artifacts', local, 'sha256', 'Checksum mismatch; file kept only in the case ZIP')
            return {}
        suffix = Path(name).suffix.lower()
        scan = suffix in SCANS
        target = safe(self.instance, 'originals', f'{self.ident}/{rid}{suffix if scan else ".bin"}')
        if scan:
            target = self.captures.setdefault(sha, target)
        self.changes[target] = raw
        self.archive_only.discard(name)
        locator = self.relative(target)
        if scan:
            return {'scan': locator, 'sha256': sha, 'collector_note': {'frame_sha256': {locator: sha}}}
        return {'original': locator, 'sha256': sha}

    def read_artifacts(self):
        for local, row in self.rows('artifacts'):
            rid = self.output_id('artifact', local)
            title = row['source_title'].strip()
            if not title:
                self.loss('artifacts', local, 'source_title', 'Missing record title', skip=True)
                continue
            original = row['originality'].strip().casefold()
            directness = row['directness'].strip().casefold()
            for key, value, allowed in (
                ('originality', original, {'original', 'image-of-original', 'official-extract',
                                          'index', 'transcription', 'derivative', 'unknown'}),
                ('directness', directness, {'direct', 'indirect', 'negative', 'lead-only'}),
                ('legibility', row['legibility'].strip().casefold(), {'clear', 'partial', 'poor', 'unreadable'}),
            ):
                if value and value not in allowed:
                    self.loss('artifacts', local, key, f'Unrecognized value {value!r}; kept as written')
            group = row['independence_group'].strip().casefold()
            if ',' in group or ';' in group:
                self.loss('artifacts', local, 'independence_group', 'Multiple groups on one artifact; independence unassessed')
                group = ''
            subjects = self.refs('artifacts', local, 'person_ids', row['person_ids'], self.people)
            fields = {key.replace('_', ' ').capitalize(): row[key]
                      for key in ('record_date', 'place_as_written', 'names_as_written') if row[key].strip()}
            reading = row['reading'] if row['reading'].strip() else ''
            source = {'title': title, 'repository': row['repository_or_archive'], 'reference': row['archival_reference']}
            locator = row['source_url_or_path'].strip()
            if re.match(r'https?://', locator, re.I):
                source['url'] = locator
            if sid := self.resolver.row_source({'source': row['repository_or_archive'], 'url': source.get('url')}):
                source['id'] = sid
            kind = 'index-entry' if 'index' in {original, row['source_type'].strip().casefold()} else 'archive-record'
            record = {'id': rid, 'kind': kind, 'title': title, 'source': source, 'subjects': subjects,
                      'language': parts(row['language_script']) or ['und'], 'kinship_case': written(row),
                      'fields': fields or ({'Registered source title': title} if not reading else {}),
                      **self.saved_file(local, row, rid)}
            if kind == 'index-entry' and (saved := record.get('original') or record.get('scan')):
                record['saved_result'] = saved
            if reading:
                record['reading'] = reading
            if not (reading or fields) or kind == 'index-entry' or directness == 'lead-only':
                record['record_role'] = 'catalogue'
            # A missing subject reference precludes a trustworthy full-document disclosure.
            if len(subjects) != len(parts(row['person_ids'])):
                record['privacy'] = 'living-possible'
            self.changes[safe(self.instance, 'records', rid + '.json')] = record
            self.artifacts[local] = {'id': rid, 'group': group, 'title': title}
            self.package['sources'][rid] = {'kind': kind, 'record': rid, 'title': title, 'subjects': subjects,
                                           'dependency_group': self.dependency(group)}
            if record.get('privacy') != 'living-possible':
                for pid in subjects:
                    # The documentary citation gives the card a paper link without making a factual or identity claim.
                    self.package['facts'].setdefault(pid, []).append(
                        {'label': 'document', 'text': title, 'status': 'export', 'sources': [rid], 'detailOnly': True})
            self.counts['artifacts']['imported'] += 1

    def dependency(self, group):
        return f'{self.ident}:group:{group}' if group else f'{self.ident}:ungrouped'

    def arguments(self, artifacts):
        grouped = defaultdict(list)
        for item in artifacts:
            if item not in grouped[item['group']]:
                grouped[item['group']].append(item)
        return [{'text': '\n'.join(item['title'] for item in items),
                 'sources': [item['id'] for item in items], 'dependency_group': self.dependency(group)}
                for group, items in grouped.items()]

    def evidence(self, kind, local, row, for_field):
        supporting = self.refs(kind, local, for_field, row[for_field], self.artifacts)
        against = self.refs(kind, local, 'contradicting_artifact_ids', row['contradicting_artifact_ids'], self.artifacts)
        return supporting, against

    def assessment(self, kind, local, row, supporting, against, group_field):
        status = row['status'].strip().casefold()
        confidence = row['confidence'].strip().casefold()
        if confidence and confidence not in CONFIDENCE:
            self.loss(kind, local, 'confidence', f'Unrecognized value {confidence!r}; using low')
        tier = CONFIDENCE.index(confidence) if confidence in CONFIDENCE else 0
        groups = {item['group'] for item in supporting if item['group']}
        for group in parts(row[group_field]):
            if group.casefold() not in groups:
                self.loss(kind, local, group_field, f'Group {group!r} has no imported supporting artifact')
        if status not in WEIGHTS:
            if status:
                self.loss(kind, local, 'status', f'Unrecognized value {status!r}; kept as unresolved research')
            status = 'unresolved'
        if status in {'corroborated', 'strongly-corroborated'} and (len(groups) < 2 or against):
            self.loss(kind, local, 'status',
                      'Corroboration lacks two distinct groups or has contrary evidence; reduced to unresolved research')
            status = 'unresolved'
        return status, WEIGHTS[status][tier]

    def save_version(self, ident, title, people, *, row=None, assessment=None, supporting=(), against=()):
        status, weight = assessment or ('unresolved', 0)
        entry = {'id': ident, 'title': title, 'line': '', 'people': people, 'status': 'open',
                 'unknown_weight': round(1 - weight, 2), 'versions': [], 'tests': []}
        if row is not None:
            entry['kinship_case'] = written(row)
            entry['versions'].append({'id': ident + '-assertion', 'label': title, 'weight': weight,
                                      'for': self.arguments(supporting), 'against': self.arguments(against)})
            if status == 'contradicted':
                entry['versions'][0]['state'] = 'conflict'
            if row['rationale'].strip():
                entry['summary'] = row['rationale']
            if row['next_action'].strip():
                entry['advice'] = [row['next_action']]
        self.changes[safe(self.instance, 'versions', ident + '.json')] = entry
        return entry

    def read_claims(self):
        for local, row in self.rows('claims'):
            text = row['claim_text'].strip()
            if not text:
                self.loss('claims', local, 'claim_text', 'Missing proposition', skip=True)
                continue
            people = self.refs('claims', local, 'subject_person_ids', row['subject_person_ids'], self.people)
            supporting, against = self.evidence('claims', local, row, 'artifact_ids')
            assessment = self.assessment('claims', local, row, supporting, against, 'supporting_independence_groups')
            ident = self.output_id('claim', local)
            self.save_version(ident, text, people, row=row, assessment=assessment, supporting=supporting, against=against)
            self.claims[local] = (ident, supporting, against)
            self.counts['claims']['imported'] += 1

    def read_relationships(self):
        kind = 'relationships'
        graph_links = []
        for local, row in self.rows(kind):
            a, b = row['person_a_id'].strip(), row['person_b_id'].strip()
            if a not in self.people or b not in self.people or a == b:
                self.loss(kind, local, 'person_a_id/person_b_id', 'Expected two distinct imported people', skip=True)
                continue
            left, right = self.people[a], self.people[b]
            supporting, against = self.evidence(kind, local, row, 'supporting_artifact_ids')
            claims = self.refs(kind, local, 'claim_ids', row['claim_ids'], self.claims)
            for _, claim_for, claim_against in claims:
                supporting.extend(claim_for)
                against.extend(claim_against)
            status, weight = self.assessment(kind, local, row, supporting, against, 'independence_groups')
            relation = row['relationship_type'].strip().casefold()
            nature = row['biological_legal_household'].strip().casefold()
            title = ' — '.join((self.package['people'][left]['name'], relation or 'relationship',
                                self.package['people'][right]['name']))
            ident = self.output_id('relationship', local)
            version = self.save_version(ident, title, [left, right], row=row, assessment=(status, weight),
                                        supporting=supporting, against=against)
            version['kinship_case']['claim_versions'] = [claim for claim, _, _ in claims]
            self.counts[kind]['imported'] += 1
            parent = relation in {'parent-of', 'child-of'}
            spouse = relation in {'spouse-of', 'spouse'}
            sibling = relation in {'sibling-of', 'sibling'}
            if not (parent or spouse or sibling):
                self.loss(kind, local, 'relationship_type', f'{relation!r} has no direct tree link; kept as a version')
                continue
            if nature not in ({'', 'legal'} if spouse else {'', 'biological'}):
                self.loss(kind, local, 'biological_legal_household', f'{nature!r} has no matching tree link; kept as a version')
                continue
            if status == 'contradicted' or row['status'].strip().casefold() not in WEIGHTS:
                continue  # A refuted or unclassified proposition is not an active connection.
            sources = list(dict.fromkeys(item['id'] for item in supporting)) or [self.ident]
            link = {'text': title, 'status': 'verified' if weight >= .5 else 'hypothesis', 'weight': weight,
                    'sources': sources, 'basis': 'Imported relationship register',
                    'kinship_case': {'version': ident, 'status_as_written': row['status'],
                                     'confidence_as_written': row['confidence']}}
            if parent:
                elder, child = (left, right) if relation == 'parent-of' else (right, left)
                link.update(parent=elder, child=child, **{'type': 'parent', 'from': elder, 'to': child})
            else:
                # The case names two spouses, without assigning husband/wife roles.
                link.update({'type': 'spouse' if spouse else 'sibling', 'from': left, 'to': right})
            graph_links.append((local, link))
        self.tree_links(graph_links)

    def tree_links(self, links):
        parents, associations = defaultdict(set), set()
        for local, link in sorted(links, key=lambda row: -row[1]['weight']):
            if 'parent' in link:
                parent, child = link['parent'], link['child']
                pending, visited = [parent], set()
                while pending and child not in visited:
                    current = pending.pop()
                    if current not in visited:
                        visited.add(current)
                        pending.extend(parents[current])
                if child in visited or parent in parents[child]:
                    self.loss('relationships', local, 'relationship_type', 'Duplicate link or ancestry cycle; kept as a version')
                    continue
                parents[child].add(parent)
                self.package['edges'].append(link)
            else:
                key = link['type'], frozenset((link['from'], link['to']))
                if key in associations:
                    self.loss('relationships', local, 'relationship_type', 'Duplicate link; kept as a version')
                    continue
                associations.add(key)
                self.associations.append(link)

    def read_searches(self):
        searches = []
        for local, row in self.rows('searches'):
            try:
                raw_at = row['timestamp'].strip()
                try:
                    at = date.fromisoformat(raw_at).isoformat()
                except ValueError:
                    at = datetime.fromisoformat(raw_at).isoformat()
            except ValueError:
                self.loss('searches', local, 'timestamp', 'Expected ISO date or timestamp', skip=True)
                continue
            source_text = row['source_or_domain'].strip()
            query = row['query'].strip()
            if not (source_text and query):
                self.loss('searches', local, 'source_or_domain/query', 'Missing source or query', skip=True)
                continue
            query = json_object(query) or query
            if isinstance(query, dict) and (
                'review' in query or query.get('mode') == 'review'
                or list(assertions(query)) or list(numeric_errors(query))
            ):
                query = row['query']
            source = self.resolver.row_source({'source': source_text, 'query': query}) or source_text
            ids = self.refs('searches', local, 'target_person_ids', row['target_person_ids'], self.people)
            saved = self.refs('searches', local, 'artifact_ids', row['artifact_ids'], self.artifacts)
            filters = json_object(row['filters'])
            scope = filters.get('coverage', filters)
            scope = scope if isinstance(scope, dict) else {}
            state = row['result_status'].strip().casefold()
            if state not in {'found', 'not-found', 'partial', 'blocked', 'captcha', 'error', 'unknown', 'unrecorded', ''}:
                self.loss('searches', local, 'result_status', f'Unrecognized value {state!r}; outcome unrecorded')
            attempts = count(row['captcha_attempts'])
            if row['captcha_attempts'].strip() and attempts is None:
                self.loss('searches', local, 'captcha_attempts', 'Unrecognized attempt count; kept as written')
            note = row['blocker'].strip() or scope.get('note') or row['filters'] or 'Scope as recorded in the source case'
            forms = scope.get('forms')
            if isinstance(forms, str):
                forms = parts(forms)
            forms = [form for form in forms if isinstance(form, str)] if isinstance(forms, list) else []
            years = scope.get('years')
            if isinstance(years, list):
                years = [year for year in years if type(year) in (int, str)]
            if type(years) not in (int, str, list):
                years = None
            coverage = {'years': years, 'forms': forms, 'read': count(scope.get('read')), 'note': str(note)}
            captcha = bool(re.search(r'captcha|капч', str(note), re.I))
            if state in {'blocked', 'captcha', 'error'} or (
                state == 'partial' and (captcha or attempts or row['blocker'].strip())
            ):
                result, hits = 'access-gap', 0
                coverage.update(read=0, forms=[])
                if state == 'captcha' or attempts or captcha:
                    coverage['note'] = f'CAPTCHA: {note}'
            elif state == 'not-found' and not parts(row['artifact_ids']):
                result, hits = 'zero-uncontrolled', 0
            elif state in {'found', 'partial'} and (reported := parts(row['artifact_ids'])):
                result, hits = 'results', len(reported)
            else:
                if state in {'found', 'not-found'}:
                    self.loss('searches', local, 'result_status', 'Outcome and artifact IDs disagree; outcome unrecorded')
                result, hits = 'unrecorded', None
            goal = row['research_goal'].strip() or 'Imported case search'
            if goal not in self.goals:
                question = self.output_id('goal', str(len(self.goals) + 1))
                self.goals[goal] = self.save_version(question, goal, [])
            question = self.goals[goal]
            question['people'] = list(dict.fromkeys([*question['people'], *ids]))
            executor = parse_by(filters.get('by'))
            by = {key: executor[key] if isinstance(executor[key], str) else None for key in ('agent', 'model', 'effort')}
            searches.append({'id': self.output_id('search', local), 'at': at, 'by': by,
                             'people': ids, 'source': source, 'source_as_written': source_text, 'question': question['id'],
                             'query': query, 'hits': hits, 'coverage': coverage, 'result_state': result,
                             'meaning': result, 'saved': [item['id'] for item in saved], 'kinship_case': written(row)})
            self.counts['searches']['imported'] += 1
        if searches:
            path = safe(self.instance, 'searches', self.ident + '.jsonl')
            self.changes[path] = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in searches).encode('utf-8')

    def relative(self, path):
        return path.relative_to(self.instance.root).as_posix()

    def plan(self):
        self.read_people()
        self.read_artifacts()
        self.read_claims()
        self.read_relationships()
        self.read_searches()
        for local, pid in self.people.items():
            row = self.package['people'][pid]['kinship_case']
            references = self.refs('people', local, 'source_artifact_ids', row.get('source_artifact_ids', ''), self.artifacts)
            if references:
                row['record_ids'] = [r['id'] for r in references]
        for local, item in self.artifacts.items():
            row = self.changes[safe(self.instance, 'records', item['id'] + '.json')]['kinship_case']
            references = self.refs('artifacts', local, 'related_claim_ids', row.get('related_claim_ids', ''), self.claims)
            if references:
                row['claim_versions'] = [item[0] for item in references]
        path = safe(self.instance, 'contributions', f'kinship-case/{self.ident}.json')
        self.changes[path] = self.package
        question = next(iter(self.goals.values()), None)
        if question is None:
            question = self.save_version(self.output_id('goal', '1'), 'Imported kinship case', list(self.people.values()))
        path = safe(self.instance, 'cases', self.ident + '.json')
        self.changes[path] = {'id': self.ident, 'state': 'open', 'question': question['id'],
                              'story_level': 'card', 'basis': [self.ident], 'thread': question['title']}


def written(row):
    return {('status_as_written' if key == 'status' else key): value
            for key, value in row.items() if value.strip()}


@boundary('writer')
def intake_case(instance, folder, ident, *, apply=False):
    folder = folder.resolve(strict=True)
    if not folder.is_dir() or instance.root.is_relative_to(folder):
        raise ValueError('Use a separate case directory that does not contain the destination family')
    token(ident)
    files, directories = case_files(folder)
    archive = zip_case(files, directories)
    sha = digest(archive)
    case = Case(instance, folder, files, ident.lower())
    manifest = safe(instance, 'imports', case.ident + '.json')
    original = safe(instance, 'imports', f'{case.ident}/case.zip')
    report_path = safe(instance, 'state', f'intake/{case.ident}.json')
    already_applied = manifest.is_file()
    if already_applied:
        stored = json.loads(manifest.read_bytes())
        if stored.get('sha256') != sha:
            raise ValueError('Intake ID already used with different case bytes; review the old intake before using a new ID')
        if not original.is_file() or digest(original.read_bytes()) != sha:
            raise ValueError('The previously saved case ZIP is missing or differs from its intake digest')
        if report_path.is_file():
            return json.loads(report_path.read_bytes()) | {'status': 'already-applied'}
    try:
        case.plan()
    except csv.Error as exc:
        raise ValueError(f'Invalid CSV in the case registers: {exc}') from exc
    report = {'status': 'applied', 'id': case.ident, 'kind': 'kinship-case', 'digest': sha,
              'counts': case.counts, 'tree_links': len(case.package['edges']) + len(case.associations),
              'losses': case.losses, 'archive_only': sorted(case.archive_only), 'original': case.relative(original)}
    if already_applied:
        return report | {'status': 'already-applied'}
    case.changes.update({
        manifest: {'id': case.ident, 'kind': 'kinship-case', 'original': case.relative(original), 'sha256': sha},
        original: archive,
        report_path: report,
    })
    exclusive = set(case.changes)
    expect = {}

    def current(key):
        path = safe(instance, key)
        if path.is_file():
            expect[path] = path.read_bytes()
            return path, json.loads(expect[path])
        exclusive.add(path)
        return path, {}

    if case.decisions:
        privacy, value = current('privacy')
        value.setdefault('life_decisions', []).extend(case.decisions)
        case.changes[privacy] = value
    if case.associations:
        evidence, value = current('evidence')
        # Preserve the legacy mixed list, including its fallback meaning when there are no parent edges.
        if 'associations' not in value:
            value['associations'] = [edge for edge in value.get('edges', [])
                                     if edge.get('type') != 'parent' and not {'child', 'parent'} <= edge.keys()]
        value['associations'].extend(case.associations)
        case.changes[evidence] = value
    if any(path.exists() for path in exclusive):
        raise ValueError('Intake would replace an existing family file; inspect the destination before proceeding')
    if apply:
        mutate(instance, case.changes, exclusive=exclusive, expect=expect)
        return report
    return report | {'status': 'dry-run'}
