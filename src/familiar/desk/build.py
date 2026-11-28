# START_MODULE_CONTRACT: MOD-DESK-BUILD
# PURPOSE: Wrap a checked personal reader in a static narrator desk without copying family inputs.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - only the checked reader delivery and explicitly projected desk pages leave the instance [review: engine lead]
# - changing the decision or any selected input invalidates the in-memory desk before storage or upload [review: engine lead]
# - building with a different engine release warns before assembling the desk [review: engine lead]
# - shell or desk wording updates consume the existing private reader without exporting family data again [review: engine lead]
# - desk assembly depends on host authorization and family inputs, never a publication target [review: engine lead]
# - shared hosted projection omits correspondence pages, navigation and receipts [review: engine lead]
# - personal staging also removes correspondence receipts from the common feedback file [review: engine lead]
# - local serving pins verified bytes, reloads a changed build record and refuses changed file-set metadata [review: engine lead]
# - reader receipts use only explicit status and reply fields bound to the assembled mark bytes [review: engine lead]
# - one static lower row of at most four places, none of them empty, is the same on every desk HTML; a fifth place stops the build [review: engine lead]
# - every quieter place, the private notice and the engine version are static in one list the page top opens [review: browser walk]
# - reader and supplemental pages use one packaged page-top component with reserved control slots [review: browser walk]
# - fictional demo exports use portable links and omit server-backed editing controls [review: engine lead]
# - public-reader demos consume the public, independently read seal instead of the host-private projection [review: engine lead]
# - the desk line front uses checked reader names and watches the research inputs from which its counts are derived [review: browser walk]
# - the search map is the host's page: the shared hosted projection omits it with its link [review: engine lead]
# CHANGES_WITH:
# - MOD-READER-SERVER (packaged shell manifest)
# - MOD-FAMILY-WRITER (checked reader consumption and desk output)
# - MOD-RESEARCH-COVERAGE (line front)
# - MOD-DESK-SEARCH-MAP (host page)
# :END_MODULE_CONTRACT
import html
import json
import os
import re
import uuid
from dataclasses import dataclass
from importlib.resources import files as package_files
from pathlib import Path
from threading import RLock

from familiar import __version__
from familiar.instance.gate import boundary
from familiar.instance.writer import encode

from .attachments import ATTACH_LIMITS
from .model import decision, listing, relative, settings, sha, source, words


PAPERS = {'archive-record', 'home-paper', 'record', 'document', 'document-scan'}


def icon(path):
    return ('<svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" fill="none" stroke="currentColor" '
            'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + path + '</svg>')


ICONS = {
    'tree_short': icon('<circle cx="12" cy="5" r="2.5"/><circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="19" r="2.5"/>'
                       '<path d="M12 7.5V12M12 12 6.8 16.6M12 12l5.2 4.6"/>'),
    'nav_asks': icon('<path d="M4 5h16v11H11l-5 4v-4H4z"/><path d="M8.5 9h7M8.5 12h4.5"/>'),
    'nav_stories': icon('<path d="M3 5.5A2.5 2.5 0 0 1 5.5 3H11v16H5.5A2.5 2.5 0 0 0 3 21z"/>'
                        '<path d="M21 5.5A2.5 2.5 0 0 0 18.5 3H13v16h5.5A2.5 2.5 0 0 1 21 21z"/>'),
    'nav_papers': icon('<path d="M6 3h8l5 5v13H6z"/><path d="M14 3v5h5M9 13h7M9 17h5"/>'),
}


def hosted_files(files, *, personal, feedback_ids=(), photos=None, fictional_draft=False):
    from familiar.feeds.flow import require_finished

    from .feed_strip import PAGE as STRIP_PAGE

    from familiar.instance.gallery import external_faces
    graph = json.loads(files['graph.json']) if 'graph.json' in files else {}
    if not fictional_draft:
        require_finished(graph.get('feeds', []))
    projected, cuts, originals = external_faces(graph, photos or {}, files.__getitem__)
    result = {name: raw for name, raw in files.items()
              if name not in originals and name != STRIP_PAGE
              and (personal or not name.startswith(('desk/correspondence.', 'desk/search-map.')))}
    if projected != graph:
        from .asks import faces
        previous = faces(graph, graph['people'])
        current = faces(projected, projected['people'])
        avatar_changes = {css.encode(): current.get(pid, '').encode()
                          for pid, css in previous.items() if css != current.get(pid)}
        result['graph.json'] = encode(projected)
        if cuts.keys() & result.keys():
            raise ValueError('A face rendition takes a hosted desk asset name')
        result.update(cuts)
        for name, raw in result.items():
            if name.startswith('desk/asks') and name.endswith('.html'):
                for old, new in avatar_changes.items():
                    raw = raw.replace(old, new)
                result[name] = raw
    for name, raw in result.items():
        if name.endswith('.html'):
            if not personal:
                raw = re.sub(rb'<a data-desk-label="nav_(?:correspondence|search_map)"[^>]*>.*?</a>', b'', raw)
            result[name] = re.sub(rb'<p data-local-feed-strip>.*?</p>', b'', raw)
        if not personal and re.fullmatch(r'desk/asks-links(?:\.[a-z-]+)?\.json', name):
            links = json.loads(raw)
            from .feedback_offer import amendment_reply
            if 'blanks' in links:
                links['blanks'] = {pid: kept for pid, slots in links['blanks'].items()
                                   if (kept := [slot for slot in slots if not amendment_reply(slot)])}
            result[name] = encode(links)
    if 'desk/feedback.json' in result:
        result['desk/feedback.json'] = encode({k: v for k, v in json.loads(result['desk/feedback.json']).items()
                                               if k in feedback_ids})
    if not personal and 'desk/asks-reminders.json' in result:
        result['desk/asks-reminders.json'] = encode([r for r in json.loads(result['desk/asks-reminders.json']) if not r['birthday']])
    if 'reader-manifest.json' in result:
        manifest = json.loads(result['reader-manifest.json'])
        paths = [name for name in manifest['files'] if name not in originals]
        manifest['files'] = {name: sha(result[name]) for name in [*paths, *sorted(cuts)]}
        result['reader-manifest.json'] = encode(manifest)
    return result


def shell():
    from familiar.reader.server import license_bytes, shell_files
    try:
        return shell_files()
    except FileNotFoundError:
        # Editable/source execution has no wheel resources. Validate the same
        # checked-in shell manifest, rather than rebuilding or changing it.
        root = Path(__file__).resolve().parents[3] / 'reader-shell'
        manifest = json.loads((root / 'shell-manifest.json').read_bytes())
        result = {}
        for name, expected in manifest['files'].items():
            data = (root / relative(name)).read_bytes()
            if sha(data) != expected['sha256'] or len(data) != expected['size']:
                raise ValueError('Reader shell damaged')
            result[name] = data
        result['LICENSE'] = license_bytes(manifest)
        return result


@dataclass
class DeskBundle:
    files: dict
    instance: object
    watch: object
    stamp: object
    inputs: dict
    listings: dict
    coverage_stamp: dict | None

    def check(self, instance):
        from familiar.instance.writer import coverage_inputs
        if instance.root != self.instance.root or self.watch.stamp() != self.stamp:
            raise ValueError('desk source changed; rebuild')
        if self.coverage_stamp is not None and coverage_inputs(source(instance)) != self.coverage_stamp:
            raise ValueError('desk coverage inputs changed; rebuild')
        if any((p.read_bytes() if p.is_file() else None) != raw
               for p, raw in self.inputs.items()):
            raise ValueError('desk decision or selected page changed; rebuild')
        if any(listing(root, pattern)[1] != names
               for (root, pattern), names in self.listings.items()):
            raise ValueError('desk page selection changed; rebuild')


@boundary('consume')
def assemble(instance):
    decision(instance)
    config = settings(instance)
    active = source(instance)
    if active.id != instance.id:
        raise ValueError('desk source belongs to another family')
    from familiar.instance.writer import desk_reader
    with desk_reader(instance, active) as snapshot:
        delivered, watch, stamp = snapshot
    return _assemble_checked(instance, active, config, delivered, watch, stamp)


def _assemble_checked(instance, active, config, delivered, watch, stamp, *, public_reader=False):
    from familiar.instance.writer import coverage_inputs
    coverage_stamp = None if public_reader else coverage_inputs(active)
    bundle = json.loads(delivered['bundle.json'])
    expected = 'clean' if public_reader else 'host-private'
    if bundle.get('state') != expected:
        raise ValueError(f'desk requires a checked {expected} reader generation')
    delivery = {name: delivered[name] for name in bundle['files']}
    path, raw = decision(instance)
    w = words(instance)
    build_id = str(uuid.uuid4())
    files = shell()
    if clash := sorted(set(files) & set(bundle['files'])):
        raise ValueError(f'{len(clash)} reader files take names of the reader shell ({", ".join(clash[:3])}); '
                         'rename their export in media/manifest.json')
    files.update(delivery)
    files['reader-manifest.json'] = encode({k: bundle[k] for k in
        ('schema_version', 'family_id', 'state')} | {'profile': 'reader-profile.json',
        'files': {name: sha(data) for name, data in delivery.items()}})
    from .pages import project
    pages, inputs, listings = project(active, config, w)
    from .show import line_section, page as show_page, project as project_show
    graph = json.loads(delivery['graph.json'])
    inbox = active._inside('family/feedback/inbox')
    inbox_paths, listings[inbox, '*.json'] = listing(inbox, '*.json')
    inbox_rows = {p: json.loads(inputs.setdefault(p, p.read_bytes())) for p in inbox_paths}
    summaries = []
    if not public_reader:
        from .asks import project as project_asks
        asks, links, reminders, summaries, ask_inputs, ask_listings = project_asks(
            active, graph, delivery, w, feedback=inbox_rows.values())
        pages['desk/asks.html'] = asks
        pages['desk/asks-links.json'] = encode(links)
        pages['desk/asks-reminders.json'] = encode(reminders)
        from familiar.reader.graph import card_memory
        for lang, texts in card_memory(active).items():
            asks_in, links_in, reminders_in, *_ = project_asks(
                active, graph, delivery, words(instance, lang), feedback=inbox_rows.values(), language=lang, texts=texts)
            pages[f'desk/asks.{lang}.html'] = asks_in
            pages[f'desk/asks-links.{lang}.json'] = encode(links_in)
            pages[f'desk/asks-reminders.{lang}.json'] = encode(reminders_in)
        inputs.update(ask_inputs)
        listings.update(ask_listings)
    show, show_inputs, show_listings = project_show(active, graph, w['show'] | {'tree': w['tree']}, asks=summaries)
    show_inputs.update(inputs)
    inputs = show_inputs
    listings.update(show_listings)
    pages['desk/show.json'] = encode(show)
    lines = '' if public_reader else line_section(active, graph, w['show'])
    from .feed_strip import PAGE as STRIP_PAGE, page as feed_strip
    strips = not public_reader and any(feed['chapters'] for feed in graph.get('feeds', []))
    if strips:
        pages[STRIP_PAGE] = feed_strip(graph['feeds'], active.source_language).encode('utf-8')
    pages['desk/progress.html'] = show_page(active, w, 'desk/journal.html' in pages, lines=lines, strips=strips)
    from familiar.reader.graph import card_memory
    memory = card_memory(active)
    def translated(value, texts):
        if isinstance(value, dict):
            return {k: translated(v, texts) for k, v in value.items()}
        if isinstance(value, list):
            return [translated(v, texts) for v in value]
        return texts.get(value.strip(), value) if isinstance(value, str) else value
    # The investigation in another reader language: its captions, the family's translated texts, local names.
    for lang, texts in memory.items():
        lw = words(instance, lang)
        shown_in = project_show(active, graph, lw['show'] | {'tree': lw['tree']}, asks=summaries)[0]
        pages[f'desk/show.{lang}.json'] = encode(translated(shown_in, texts))
        lines_in = '' if public_reader else line_section(active, graph, lw['show'], language=lang, texts=texts)
        pages[f'desk/progress.{lang}.html'] = show_page(active, lw, 'desk/journal.html' in pages, lines=lines_in,
                                                        language=lang, data=f'desk/show.{lang}.json', strips=strips)
    if not public_reader:
        # All desk languages render one checked correspondence projection.
        from .correspondence import checked_letters, project as project_correspondence
        letters, correspondence_inputs, correspondence_listings = checked_letters(active)
        pages.update(project_correspondence(active, w, letters))
        inputs.update(correspondence_inputs)
        listings.update(correspondence_listings)
        for lang, texts in memory.items():
            names = {pid: form for pid, person in graph.get('people', {}).items()
                     if isinstance(form := ((person.get('namePresentation') or {}).get('byLanguage') or {}).get(lang), str)
                     and form.strip()}
            pages.update(project_correspondence(active, words(instance, lang), letters, language=lang, texts=texts, local_names=names))
    from .search_map import PAGE as SEARCH_MAP, project as project_map
    pages.update(project_map(active, w, [(lang, words(instance, lang), texts) for lang, texts in memory.items()]))
    from .feedback import owner_only, receipt, research_feedback
    def read_mark(path):
        raw = path.read_bytes() if path.is_file() else None
        inputs[path] = raw
        return raw
    pages['desk/feedback.json'] = encode({p.stem: receipt(active, p.stem, read_mark)
        for p, row in inbox_rows.items() if not owner_only(row) and not research_feedback(row)})
    from familiar.instance.memory_visibility import check_delivery
    check_delivery(active, pages)
    if clash := sorted(set(files) & (set(pages) | {'desk/desk.js', 'desk/desk.css', 'desk/words.json', 'robots.txt'})):
        raise ValueError(f'{len(clash)} reader files take names of desk pages ({", ".join(clash[:3])}); '
                         'rename their export in media/manifest.json')
    files.update(pages)
    assets = package_files('familiar.desk').joinpath('assets')
    files.update({'desk/' + name: assets.joinpath(name).read_bytes()
                  for name in ('desk.js', 'desk.css', 'session.js', 'show.js', 'show.css', 'tree-add.js', 'tree-add.css', 'access.js', 'access.css', 'correspondence.js', 'correspondence.css', 'search-map.css')})
    if not public_reader:
        for name in ('asks.js', 'asks.css'):
            files['desk/' + name] = assets.joinpath(name).read_bytes()
    files['desk/access.html'] = assets.joinpath('access.html').read_bytes()
    files['desk/words.json'] = encode(w | {'languages': {lang: words(instance, lang)
        for lang in instance.languages}, 'source_language': instance.source_language,
        'asks_languages': sorted(lang for lang in instance.languages if f'desk/asks.{lang}.html' in files),
        'page_languages': {page: sorted(lang for lang in instance.languages if f'desk/{page}.{lang}.html' in files)
                           for page in ('asks', 'correspondence', 'progress', 'search-map')},
        'engine_version': __version__, 'build': build_id,
        'family_id': instance.id, 'attach_limits': ATTACH_LIMITS})
    files['robots.txt'] = b'User-agent: *\nDisallow: /\n'
    styles = ''.join('<link rel="stylesheet" href="/' + name + '">'
                     for name in files if name.startswith('assets/tokens-') and name.endswith('.css'))
    people = list(graph.get('people', {}).values())
    # The lower row: what a reader comes for, at most four places, and only those this family has.
    navigation = [('tree_short', '/#view=tree')]
    if b'class="ask-card"' in pages.get('desk/asks.html', b''):
        navigation.append(('nav_asks', '/desk/asks.html'))
    if any(f.get('chapters') for f in graph.get('feeds', [])) or any(p.get('story') for p in people):
        navigation.append(('nav_stories', '/#view=stories'))
    if any(m.get('asset') for p in people for m in p.get('media', []) + p.get('illustrations', [])) or any(
            s.get('image') or s.get('asset') and s.get('kind') in PAPERS for s in graph.get('sources', {}).values()):
        navigation.append(('nav_papers', '/#view=papers'))
    if len(navigation) > 4:
        raise ValueError('The lower row holds at most four places; CRAFT-PLAIN-PAGES')
    # Everything else is one tap away behind the page top: never in a reader's way, never lost to the narrator.
    quiet = [('nav_families', '/#view=families')] if people else []
    if graph.get('worldMap'):
        quiet.append(('nav_world', '/#view=world'))
    quiet.append(('nav_progress', '/desk/progress.html'))
    if SEARCH_MAP in pages:
        quiet.append(('nav_search_map', '/' + SEARCH_MAP))
    if 'desk/correspondence.html' in pages:
        quiet.append(('nav_correspondence', '/desk/correspondence.html'))
    def link(label, href, icon=''):
        return ('<a data-desk-label="' + label + '" href="' + href + '">' + icon + '<span>'
                + html.escape(w[label]) + '</span></a>')
    notice = ('<span class="desk-private-label">' + html.escape(w['private_notice']) + '</span>'
              '<small class="desk-version">Familiar ' + html.escape(__version__) + '</small>')
    banner = (styles + '<footer id="desk-footer"><aside id="desk-notice" role="note">' + notice + '</aside><nav id="desk-nav" aria-label="Familiar">'
              + ''.join(link(label, href, ICONS[label]) for label, href in navigation)
              + '</nav><span id="desk-feedback-entry"></span></footer>'
              '<nav id="desk-more" hidden>' + ''.join(link(label, href) for label, href in quiet)
              + '<p class="desk-colophon">' + notice + '</p></nav>'
              '<link rel="stylesheet" href="/desk/desk.css">'
              '<script src="/desk/session.js"></script>'
              '<script defer src="/desk/desk.js"></script>')
    top_script = next(name for name in files if name.startswith('assets/pageTop-') and name.endswith('.js'))
    top_styles = ''.join('<link rel="stylesheet" href="/' + name + '">'
                         for name in files if name.startswith('assets/page-top-') and name.endswith('.css'))
    for name, data in list(files.items()):
        relative(name)
        if name.endswith('.html'):
            top = (top_styles + '<div id="page-top"></div><script type="module" src="/'
                   + top_script + '"></script>') if name != 'index.html' else ''
            # The quiet lower notice exists before JavaScript, on document pages too.
            files[name] = re.sub(rb'<body\b[^>]*>', lambda m: m[0] + (banner + top).encode(),
                                 data, count=1, flags=re.IGNORECASE)
            if b'id="desk-notice"' not in files[name]:
                files[name] = data + banner.encode()
            if name == 'index.html':
                files[name] += (b'<link rel="stylesheet" href="/desk/tree-add.css">'
                                b'<script defer src="/desk/tree-add.js"></script>')
            if not public_reader and (name == 'index.html' or re.fullmatch(r'desk/asks(\.[a-z-]+)?\.html', name)):
                files[name] += (b'<link rel="stylesheet" href="/desk/asks.css">'
                                b'<script defer src="/desk/asks.js"></script>')
    # HTML delivery includes the private notice; manifest digests describe those
    # delivered bytes, not the unwrapped source document.
    files['reader-manifest.json'] = encode({k: bundle[k] for k in ('schema_version', 'family_id', 'state')}
        | {'profile': 'reader-profile.json', 'files': {name: sha(files[name]) for name in delivery}})
    inputs[path] = raw
    inputs[instance.root / 'familiar.toml'] = (instance.root / 'familiar.toml').read_bytes()
    result = DeskBundle(files, instance, watch, stamp, inputs, listings, coverage_stamp)
    result.check(instance)
    return result


@boundary('consume')
def read_build(instance):
    """Publication consumes a built artifact, not a second family rebuild."""
    from .model import output
    path = instance._inside('.secrets/desk-build.json')
    if not path.is_file():
        raise ValueError('Desk is not built; run desk build or desk serve --build')
    manifest = json.loads(path.read_bytes())
    _, raw = decision(instance)
    if (manifest.get('family_id') != instance.id or manifest.get('decision_sha256') != sha(raw)
            or manifest.get('schema_version') != 1):
        raise ValueError('Desk decision changed; rebuild before publishing')
    root = output(instance)
    actual = {p.relative_to(root).as_posix(): p for p in root.rglob('*') if p.is_file()}
    if set(actual) != set(manifest['files']):
        raise ValueError('Desk file selection changed; rebuild')
    if any(sha(path.read_bytes()) != manifest['files'][name] for name, path in actual.items()):
        raise ValueError('Desk file bytes changed; rebuild')
    for name in actual:
        relative(name)
    return actual


class CheckedDesk:
    """Pin verified delivery; stat the set, hash again only on a new build record."""

    def __init__(self, instance):
        self.instance = instance
        self.lock = RLock()
        self.marker = instance._inside('.secrets/desk-build.json')
        if not self.marker.is_file():
            read_build(instance)  # Preserve the actionable missing-build diagnostic.
        self.reload()

    def stamp(self):
        from familiar.instance.writer import _metadata

        from .model import output
        result = {}
        def visit(path):
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        visit(entry.path)
                    else:
                        result[entry.path] = _metadata(Path(entry.path), entry.stat())
        visit(output(self.instance))
        for path in (self.marker, decision(self.instance)[0], self.instance.root / 'familiar.toml'):
            result[str(path)] = _metadata(path)
        return result

    def reload(self):
        self.invalid = True
        before = self.stamp()
        paths = read_build(self.instance)
        manifest = json.loads(self.marker.read_bytes())
        files = {name: path.read_bytes() for name, path in paths.items()}
        after = self.stamp()
        changed = [name for name in before.keys() | after.keys()
                   if before.get(name) != after.get(name)]
        changed.extend(name for name, data in files.items() if sha(data) != manifest['files'][name])
        if changed:
            raise ValueError('Desk changed while checking build: ' + ', '.join(changed))
        self.active = source(self.instance)
        self.memory = None
        self.check_memory(files)
        self.files = files
        self.immutable_paths = {name for name in shell() if name.startswith('assets/')}
        self.etags = {name: '"' + sha(data) + '"' for name, data in files.items()}
        self.metadata = before
        self.invalid = False

    def check(self):
        from familiar.instance.writer import _metadata
        with self.lock:
            if _metadata(self.marker) != self.metadata[str(self.marker)]:
                self.reload()
            if self.invalid or self.stamp() != self.metadata:
                self.invalid = True
                raise ValueError('Desk changed; rebuild')
            self.check_memory(self.files)

    def check_memory(self, files):
        from familiar.instance.memory_visibility import check_delivery, stamp
        before = stamp(self.active)
        if before != self.memory:
            check_delivery(self.active, files)
            if stamp(self.active) != before:
                raise ValueError('Desk memory changed during review; retry')
            self.memory = before

    def resource(self, name):
        with self.lock:
            self.check()
            return self.files[name], self.etags[name]


@boundary('consume')
def build(instance):
    import sys

    if message := instance.engine_warning():
        print(f'WARNING: {message}', file=sys.stderr)
    from familiar.instance.gate import QUARANTINE
    from familiar.instance.writer import state_memory, store_desk
    QUARANTINE.clear()
    bundle = assemble(instance)
    store_desk(instance, bundle)
    # Quarantine never goes quiet: the build names what waits, publish counts it before sending.
    waiting = [row for rows in QUARANTINE.values() for row in rows]
    state_memory(instance, 'desk-quarantine.json', {'quarantine': waiting})
    for row in waiting:
        print(f"QUARANTINE: {row['file']} ({row['author']}): waits for {', '.join(row['waits'])}; not on the site")
    return len(bundle.files)


@boundary('consume')
def export_demo(instance, out, *, public_reader=False):
    """A portable, read-only desk for an explicitly fictional family only."""
    if instance.config.get('family', {}).get('fictional') is not True:
        raise ValueError('Static demo export requires family.fictional = true')
    if public_reader:
        from familiar.instance.gate import publication
        from familiar.instance.writer import InputWatch
        checked = publication(instance, 'reader')
        decision(instance)
        active = source(instance)
        if active.id != instance.id or active.root != instance.root:
            raise ValueError('Public demo reader must use its own family root')
        watch = InputWatch(active)
        stamp = watch.stamp()
        checked.check(active)
        bundle = _assemble_checked(instance, active, settings(instance), checked.files(),
                                   watch, stamp, public_reader=True)
    else:
        bundle = assemble(instance)
    from familiar.instance.gallery import photographs
    files = hosted_files(bundle.files, personal=True, photos=photographs(instance),
                         fictional_draft=not public_reader)
    # Personal desk scripts require a feedback/auth server. The public demo has
    # neither; retain only the reader, investigation and their static navigation.
    omitted = {'desk/desk.js', 'desk/session.js', 'desk/tree-add.js', 'desk/tree-add.css',
               'desk/access.html', 'desk/access.js', 'desk/access.css', 'desk/feedback.json',
               'desk/correspondence.html', 'desk/correspondence.js', 'desk/correspondence.css'}
    for name in omitted:
        files.pop(name, None)
    def links(value, key=''):
        if isinstance(value, dict):
            return {k: links(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [links(v, key) for v in value]
        if key in {'asset', 'full', 'url', 'href'} and isinstance(value, str) and value.startswith('/') and not value.startswith('//'):
            return value[1:]
        return value
    files['graph.json'] = encode(links(json.loads(files['graph.json'])))
    for name, raw in list(files.items()):
        if not name.endswith('.html'):
            continue
        text = raw.decode('utf-8')
        text = re.sub(r'<a data-desk-label="nav_correspondence"[^>]*>.*?</a>', '', text)
        text = re.sub(r'<script\b[^>]*src="/(' + '|'.join(re.escape(n) for n in omitted)
                      + r')"[^>]*></script>', '', text)
        text = re.sub(r'<link\b[^>]*href="/desk/tree-add.css"[^>]*>', '', text)
        text = re.sub(r'((?:href|src)=")/(?!/)', r'\1', text)
        # Each real HTML file has a base back to the site root. Hash routes and
        # source documents therefore survive direct navigation and refresh on Pages.
        base = '../' * (len(Path(name).parts) - 1) or './'
        head = '<base href="' + base + '"><meta name="familiar-static-demo" content="true">'
        if re.search(r'<head\b', text):
            text = re.sub(r'(<head\b[^>]*>)', r'\1' + head, text, count=1)
        else:
            text = re.sub(r'(<html\b[^>]*>)', r'\1<head>' + head + '</head>', text, count=1)
        notice = ('Вымышленная семья · показ' if public_reader and instance.source_language == 'ru'
                  else 'Fictional family · demonstration')
        text = re.sub(r'(<span class="desk-private-label">).*?(</span>)',
                      lambda m: m[1] + notice + m[2], text)
        text = re.sub(r'<form\b[^>]*class="desk-answer".*?</form>', '', text, flags=re.DOTALL)
        files[name] = text.encode('utf-8')
    # This is a derived display, not a reader generation to be consumed again.
    manifest = json.loads(files['reader-manifest.json'])
    manifest['files'] = {name: sha(files[name]) for name in manifest['files']}
    files['reader-manifest.json'] = encode(manifest)
    files['.nojekyll'] = b''
    from familiar.instance.writer import save_demo_site
    save_demo_site(instance, out, bundle)
    return len(files)
