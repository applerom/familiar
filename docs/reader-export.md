<!--

START_MODULE_CONTRACT: MOD-READER-EXPORT-CONTRACT
PURPOSE: Specify the rebuildable reader boundary independently of a family's authoring and the host's publishing environment.
PRD_REF: docs/PRD.md#ARCH
INVARIANTS:
- the format defines an offline, versioned delivery with byte-level integrity [review: engine lead]
CHANGES_WITH:
- MOD-READER-PROFILE
- MOD-READER-BOOK (offline print artifact and semantic classes)
- docs/PRD.md#INSTANCE
:END_MODULE_CONTRACT
-->
# Reader export v1

The assembled desk uses one lower row on every screen: at most four places with
an icon and a word (tree, relatives, stories, papers), only those the family has.
The quieter places, the remark, the private notice and the engine version are one
static list which the page top opens as “More”. Both are assembled once by
`desk/build.py`, styled by `desk.css`, and controlled by `desk.js`; the reader's
own tabs (the same three places without a desk) are hidden in an assembled desk.
A full-screen feed always has a visible exit.

**Papers** (`#view=papers`, `&of=<person>` for one person, `&paper=<id>` for an
open one) show every paper of the delivered graph once: a person's attached scans,
the documents of the card, and scanned records for everybody they name. The page
asks for nothing the graph does not carry. By person the nearest to the reader
come first; by time they stand in decades; photographs are the third tab. An open
paper lies over the page with its reading, taken from the document's own page in
the reader's language. A step through the reader is a history entry that keeps its
scroll position, so Back returns to the place. Cards and chapters open the same
view.

`reader-src/plain-words.json` lists words that never reach a family's page; the
shell build fails on one in its strings or in a bundled pack's desk words.

Every remark entry opens the same sheet on the first click without scrolling.
Hover shows at most a hint. Outside click, Escape and the entry itself dismiss
an empty sheet; dismissal of a populated sheet saves and collapses it. The entry
advertises unsent text and resumes it with its original person/question/page
context, including after navigation or reload. Contextual entries retain their
own drafts. Research alternative counts belong beside work volume.

Interface changes are accepted by an executed browser walk, not screenshots
alone or automatic UI tests. Record user actions, expected and observed results
(including first click, hover and pointer leave, all dismissals, retained text,
round-trip navigation and narrow layout). Use and extend
[`method/interface-walk.md`](../method/interface-walk.md); attach the completed
table and screenshots of each screen to the external task report.

The tree card answers “who this is”: given name and the clan's display surname,
known life years and known birthplace. Patronymic, kinship, weights, source
spellings and explanations belong to the full card; uncertain links remain
dotted. Long names wrap. An explicit owner placeholder is retained whole.
`tree_metadata.surname_forms` is the reversible family decision; literal names
and document contents are unchanged. The full card lists its own documentary
spellings and explains a father's surname supplied from children. A name has a
form per reader language (`namePresentation.byLanguage`, from `name_forms`
decisions); without one the family's main name stands. Documentary spellings of
the whole name sit in the card's "More" with their documents
(`docs/language-checks.md`).

Optional `paths.world_map` declares an atlas (people, homes, places, paths; schema 1). Feed `play.json` attaches spots and panoramas by image asset and games by feed/chapter ID. Panorama assets and game truth.record crops must be registered media. Public map prose is withheld for mixed protected places; hidden stops are removed from paths. The private host atlas retains all places; address fields and protected document rewards remain excluded.

Local host view: `familiar --root FAMILY reader export --host-private --output PRIVATE-DIR`,
then `familiar --root FAMILY reader serve --host-private --output PRIVATE-DIR`.
Serve also creates a missing private bundle. An explicit separate output is mandatory.
The family display tells stories about living, unknown and deceased people alike,
including dates, places, facts, captions, games and authored cards. No permissions are requested.
Living documents (and documents without resolved subjects), structured address
events/fields and their repeated literal values are excluded. Unclassified addresses
in prose still require human review. State is `host-private`, never a clean release;
ordinary publication refuses its seal. Local consumption checks current display
input fingerprints and payload hashes. Every served HTML screen carries a language-pack
private notice. This is local delivery, not authorization to upload its files.

The local family reader and signed-in desk use `privacy.family_years` (75 by default)
for a person whose life status is uncertain. A recorded birth or dated participation can establish that age,
including for an unknown merged card or a precautionary import. An explicit
living declaration or refusal still protects the person. The public reader uses
`privacy.living_years` (100 by default).

Private display snapshots include only explicitly referenced corpus records and
their captures, with record form checks. Unreferenced records and all search logs
stay outside the snapshot, fingerprint and HTTP input watch; collectors can keep
editing them during export and serving. A selected record or other display input
changing still refuses the build or invalidates the session. Public export retains
the full family gate and complete dependency policy.

Private archives/captures/imports enter the snapshot only by file reference;
media comes from the permanent manifest (or explicit legacy asset references).
Snapshots use `paths.state/snapshots`, not the system drive's temporary folder.
Forms are copied; immutable archives are hard-linked where possible, with a
verified-copy fallback and detachment before staged mutation. Inputs totaling
256 MiB or more emit a size notice to stderr. At CLI startup, and before an API
snapshot, Familiar reaps only its new lease-marked directories older than one
day whose owner PID is confirmed gone; it emits one cleanup line. Unmarked
and legacy system-temp leftovers are deliberately untouched.

`reader preview` prints the public projection, before
independent reading. `reader preview --output NEW-DIR` saves exact review material
and its ticket. Neither route creates a generation or authorizes publication.

Both reader modes derive document subjects from gallery owners, chapter people
and facts citing sources, as well as explicit record participants. Subjects add
across shared records, source IDs and scan assets before filtering: attaching a
living person's document to a deceased person's card cannot release it. A scan,
its reading and local source link share the same exclusion. Literal text excerpts
remain scoped to their declared fields and have no full-document link.

Public output inherits a paper's exclusion in attributed prose and games. Use
`sources` on prose blocks, their alternatives or game text objects to identify the
records or tree sources they draw from. A game also inherits the exclusion of a
paper referenced by its reward.

The scan catches literal wording, dates in digits and words, and distinctive
words from withheld papers. Independent reading is needed to catch an author’s
free retelling. The scan expands full dates found in digits or with a numeric day
and year and a written month. It uses the configured reader languages, with
built-in month forms for English, Polish, Russian and Swedish.

The signed-in family desk shows described frames while pictures are being drawn
with either shared or personal login. Public feeds and reader export require
finished frames.

Family editorial cards are declared by `paths.edition` (PRD FORMS). Both tree and
reader delivery apply the same card decisions before enforcing privacy. The family display includes stories, photographs and compound
name/date explanations for everyone. Public output limits living and unknown
people to names and kinship. All selected files must resolve locally. The edition is a
fingerprinted family input: changing it makes previous reader generations stale
and requires reviewing the changed card bytes. It never changes research events,
life assessments or source originals.

`familiar --root <family> reader export --output <empty-directory>` writes only
there. Omitting output uses `paths.export`. The destination must be disjoint from
every family input, including media, and may never be an existing populated
directory. Export does not move, delete, generate or recompress an input image.
The host chooses delivery addresses, access controls, publication and rollback.

`reader verify --output <directory>` is the consumption boundary: it calls the
checked generation reader and verifies the exact file set and every delivered
digest. Withdrawn uses are refused with a removal list. Other input edits mark
the generation outdated and leave it readable; rebuild in another empty directory. A host must verify
before serving a stored bundle. This local mechanism cannot revoke an already
published external copy or make a static browser recheck private inputs.

The directory is a generation container. `CURRENT.json` points at
`.generations/<digest>/`, where the files below live. Use `reader verify` or the
checked `writer.read_generation` API before handing a generation to a host.
Share only the verified payload. The sibling `.generations/<digest>.json`
is the host's metadata with dependency paths and review records. Rebuild
public generations created before this layout.
Raw path reads are outside the engine boundary. Payloads retain the v1 shape.

For a local browser shell, run `familiar --root <family> reader serve --output
<directory> --port 8768`. Open http://127.0.0.1:8768/ to read the tree, cards
and stories. This loopback-only service reads through the
checked generation reader once before listening, then pins the verified bytes in
memory. Before every response (including a conditional 304), a metadata walk
checks input file names, size and nanosecond modification/change times. Additions,
removals or edits refuse with HTTP 409: inputs changed; rebuild and restart.
This deliberately also refuses ordinary outdated inputs during a server session.
No request rereads or hashes payloads or input contents. New generations are picked
up on restart, or Python hosts can call `httpd.reverify()` for an explicit full
check and atomic replacement of the in-memory snapshot. Failed reverification
keeps delivery blocked. `reader verify` remains the independent full-check command.
It serves the packaged shell, delivery files and `/reader-manifest.json` (schema, family id,
state, file digests and relative `profile`). Private dependency paths, `bundle.json`,
generation metadata and family inputs have no HTTP route. A withdrawn or damaged
generation refuses startup. A generation already outdated at startup remains
readable if its safety inputs still permit it (host-private requires its display
inputs to match); later relevant input changes require restarting the session.
The service is a local host adapter, not an authenticated public hosting service.
The wheel includes a prebuilt browser shell: Node is unnecessary at runtime.
Startup verifies the shell SHA-256/size manifest as well as the family
container; shell/family path collisions refuse delivery. Unknown paths have no
filesystem fallback. The manifest detects damaged package files, not malicious
replacement of both files and manifest.

All successful responses carry an ETag for the exact served bytes, including
the private HTML notice. Profile, graph, HTML and other stable names use
`Cache-Control: private, no-cache` and support `If-None-Match`/304 and HEAD.
Non-HTML URLs containing their full SHA-256 use a private one-year immutable
cache. A hash merely recorded in a manifest does not make a stable URL immutable.
Cached external copies cannot be recalled. Metadata invalidation detects honest
file edits, not an adversary preserving metadata; restart/full verification hashes
the contents again. The HTTP allowlist never includes generation metadata.

The shared TypeScript, styles, fonts and general map geometry live in `reader-src/`.
They contain no family payloads. With Node >=22.13 and Bun 1.3.10, from this repository:

```powershell
cd reader-src
bun install --frozen-lockfile --ignore-scripts
bun run reader:shell
cd ..
uv build --wheel
```

The build copies the root `THIRD_PARTY_NOTICES.txt` into `reader-shell/`
and seals its bytes with the same SHA-256/size manifest as the other files; no family root,
public directory, pilot checkout or development proxy is an input. Bun's lockfile
pins the toolchain, including the CSS transformer. Shell reproducibility can be
checked as optional release advice. MIT runtime copyright/permission and full OFL font texts must accompany
every shell copy. Reader serving delivers this file through the shell allowlist,
and desk assembly copies it into the static site. The shell manifest also seals the root
engine `LICENSE`, stored once in this repository and bundled as `_licenses/LICENSE`.
Reader serving and desk assembly deliver it at `/LICENSE`; a damaged licence
refuses delivery just like damaged shell assets. Data-only `reader export`
generations contain graph/profile/media, not the shell, React or engine fonts;
when supplying a shell with them, keep the complete shell and its notices.
Family media rights remain separate. The wheel also includes root LICENSE and
THIRD_PARTY_NOTICES.txt in dist-info/licenses through PEP 639 metadata.
Commit sources, lockfile, compiled assets and manifest together. Hatch includes
`reader-shell/` as `familiar/_reader_shell` in the wheel. Runtime needs no Node.
`host.feedback` is disabled when absent (legacy profiles may retain their API).

When raising the release version, update all three install tags in
[`first-family.md`](first-family.md#1-install-the-engine-and-choose-a-new-family)
to the same version. Before releasing, commit the engine and run (replace the denied root with the
local family checkout that must be unavailable):

```powershell
uv run python scripts/check_release.py --deny-root <family-checkout> --wheel-dir "$env:LOCALAPPDATA\Familiar\dist"
```

This builds from `git archive HEAD` in a temporary directory and denies every
named family root in Python build processes; denial probes must fail as expected.
It checks required packaged method/forms/region/shell files and sealed shell and
licence bytes, then prints the wheel's commit and SHA-256. Node/Bun are unnecessary
for this check. Optional `--rebuild-shell` rebuilds a separate scratch copy under
Node permissions and only prints reproducibility advice; it never changes the
wheel's committed source. This is an accidental-dependency check, not a sandbox
for hostile build code. Pass each local family root with its own `--deny-root`.

The public demo site is built from `main` on every push and must follow the release.
Check it at the tip before delivering (a few seconds):

```powershell
Remove-Item -Recurse -Force "$env:TEMP\familiar-demo-site" -ErrorAction SilentlyContinue
uv run python -X utf8 scripts/build_demo_site.py --out "$env:TEMP\familiar-demo-site"
```

`Unreviewed reader pages: ...` means a demo page changed since its last independent
reading: in that demo family prepare it with `feed review FEED --kind reader --out NEW-DIR`,
read the pages in a browser, and confirm the ticket with `feed accept` before the release.

## Files

- `reader-profile.json`: profile v1, relative `data: graph.json`; family metadata
  comes from the instance. No pilot language or storage defaults.
- `graph.json`: people dictionary, ordered edges/families/feeds, sources,
  associations, root and card statuses. Existing claim statuses and array order
  are retained. Canonical attributed names/events get the reader's display keys.
  Dates supplied only by tentative facts cannot replace ordinary card dates.
- Permanent media keeps its registered names. A canonical record has a local
  document page with its title and escaped reading. When the record names a
  preserved image, the page shows the image before the reading and opens it
  at its delivered size. The graph source keeps its page URL in `asset` and
  supplies the scan URL in `image`. Back follows browser history with the reader
  home as the direct-entry fallback. Research URLs stay private.
- `bundle.json`, written last: integer `schema_version: 1`, `family_id`,
  `state: clean` (or recorded `host release`) and `files` mapping relative
  names to SHA-256 (plus the stable media id and kind where relevant).
  Automatic scans add `source_sha256` for the exact capture bytes.

No timestamps or output-directory paths enter the bundle: unchanged inputs
produce exactly the same bytes in two empty directories. A preview serializer
is internal, is marked `state: preview` and cannot pass `reader verify`.

Export calls `instance/gate.py`; verify checks the committed uses without
requiring unrelated drafts to be complete. Editorial pipeline marks guide the
next work; they are not evidence that a page was read. Export enforces class F
and every displayed surface requires current independent reading attestations,
including the tree/profile/document pages: use the review API in `docs/gate.md`.
No artificial scenario/drawing/connect marks are needed to export reviewed bytes.

Unnamed people remain navigable by their supplied `placeholder`, or a language-pack fallback.
Events retain `cause`; facts retain `derived`, `basis` and firm/uncertain `testimony`.
Family unions retain their status and inference flag. Public mode removes union/edge
bases involving protected people. `narrator`/`defaultViewer` identify the viewer only
when declared; `readerLabels` supplies the source-language wording.

## Permanent media

`paths.media/manifest.json`:

```json
{"schema_version":1,"assets":[{"id":"image-one","sha256":"<64 hex>",
  "kind":"crop","file":"assets/<digest>.jpg","export":"records/crop.jpg",
  "origin":{"record":"invented-paper","region":"name line"}}]}
```

`id` and `export` are unique. `file` resolves within the permanent media root,
including after symlink resolution. `kind` and `origin` say what this is and
where it belongs in family data; an optional `source_id` associates a preserved
display derivative with a graph source. Digests are verified, not inferred from
file size. A derivative with `source_id` also carries `source_sha256`; changing
that local primary document refuses the old derivative rather than reusing it.
When an adopted record names a file in `source.locator` or its capture fields,
the reader selects a file inside the instance or mapped originals, checks any
recorded frame checksum and binds the original in the publication snapshot.
Pillow (the `images` extra) makes a metadata-free image with a longest side of
1800 px. The engine links a pixel-only PDF when a PDF is the selected capture
and optional `pypdfium2` is available in its Python environment. A captured page
image takes precedence over a PDF. Text remains available when a capture
or decoder is unavailable. These exports need no permanent media rows.
The manifest contains authored media and retained derivatives, never
the sole copy in the export directory. The feed builder, approval fingerprints
and trust check resolve the same manifest through `Instance.media_file()`;
legacy media roots remain readable when no manifest exists.

Every reader asset reference must resolve through that manifest or a generated
document page. An undeclared local asset is an error. Only used media are
delivered. Generated pages and media may not collide with each other or the
three reserved bundle filenames. Private paths/provenance are not copied into
the delivery manifest.

External links require declared `media.external_embeds` kinds: `map` currently
allows HTTPS OpenStreetMap, `video` HTTPS YouTube. Documents and image assets
cannot use that exception. Host CDN rewriting belongs after this export,
with an independently verified delivery receipt.

## Current extraction boundary

The portable path builds canonical attributed tree data, current feeds, local record
pages and registered media. Pilot editorial regexes, display-only hypothesis
groups, generation estimates, colour/play passes and host CDN rewrites remain
in its adapter; equality with that adapter is not implied. A blocked pilot
cannot establish a clean-export comparison. Copy-only preservation and a
preview delivery replay can test byte/order preservation without bypassing the
gate, but are explicitly weaker evidence. A switch needs full projection
parity and a clean gate first.

## Offline print book

```powershell
familiar --root FAMILY reader book --output EMPTY-DIR
familiar --root FAMILY reader book --host-private --kids --language ru --page-size A4 --output ANOTHER-EMPTY-DIR
```

The destination is mandatory, empty and disjoint from family inputs. Open
`index.html` directly in a browser, offline. It needs no service, JavaScript,
web fonts, renderer package or other runtime dependency. Print or save as PDF
with the browser; disable its own header/footer, use CSS page size and 100%
scale. A5 is default. The stylesheet's page margin boxes supply page numbers;
older browsers may ignore them. Inspect the resulting PDF before printing.

## Admission and privacy

The factory is `gate.publication(reader|reader-private, for_review=True)`, not
raw feed materialization. Public mode keeps the full family gate, default-deny
projection, living-document and address exclusions. Host-private mode
uses the same local display scope and privacy exclusions as `reader export
--host-private`; it is labelled family-only and is no authority to publish.

The existing `_review_manifest` validates independent reading against current
reader units, exact delivered media and safety inputs. A chapter, its feed
metadata and the family profile must have valid independent attestations for
every configured reader language. Host-release rows and editorial pipeline
marks never admit a book chapter. The whole reader tree need not be reviewed
because the book does not display it. Crops/illustrations are bound inside the
chapter's reader digest. A changed chapter/image is excluded; a safety change
can lapse all affected reading. CLI JSON names every excluded chapter and
reason (`not-independently-read`, `changed-after-reading`, invalid current
reading, or `withheld-by-reader`). With no eligible chapters it refuses before
creating a destination. Success counts included/excluded chapters and warnings.

Review exact local-family bytes when needed:

```powershell
familiar --root FAMILY reader preview --host-private --output NEW-REVIEW-DIR
# An independent reader inspects these exact files before confirming:
familiar --root FAMILY feed accept FEED --stage reading --kind reader-private --reviewer READER --author AUTHOR --ticket NEW-REVIEW-DIR/review-ticket.json
```

Omit `--host-private` and use `--kind reader` for public material. This adds
review preparation; ordinary private reader export retains its existing policy.
Identical reader units can share existing attestations; different projected
bytes cannot. The engine verifies binding, not whether two named people actually
read independently. Fictional acceptance fixtures are not family approval.

Only `instance/writer.py` writes the result. It checks the sealed source before
composition and before atomically renaming the staged folder. This flat artifact
is a registered consumption adapter: the factory owns the full gate, so the
book wrapper does not repeat that same family verdict a third time. The result
is a final static delivery, like paper, not a stored reader generation or a source
for another engine output. It cannot recall already printed pages or recheck
family inputs offline. Rebuild from current family inputs before a new distribution.
The source review ticket, private inputs and research record files are absent.

## Contents and language

Cover: family title, edition, fiction/private notice, selected feed titles.
Contents links point only to internal anchors. Feeds are parts, chapters retain
their authored order. Full text preserves paragraph `flow` placement of crops
and figures. Unplaced items follow prose. A crop has its caption and literal
original reading; multiple crops keep their own caption/reading groups.
No full-document navigation or extra document pages are copied.

Children use `kids.text`, then `text_kids`, otherwise full text with an explicit
warning; `kids.title` overrides the title. As in the reader, children's records
honour `kidsRecords=false`; marked chapter record references show up to four selected crops in order. Without marks, the first record and its first extra crop are shown. Adult flow positions do not apply to children's paragraphs. More/versions,
source attribution, places and applicable extras become chapter-end evidence;
weights present in that already-reviewed prose or typed facts are retained,
with fact bases and decisions, never inferred. Generated illustrations keep
an explicit reconstruction disclosure.
The reader's `tr` lookup is retained (requested language, then en, then ru).
Its existing translation rule retains stale units until the next author batch;
the CLI reports stale/missing counts rather than claiming translations fresh.
Literal document readings stay in the original language. No translation is made.

Games (including game-labelled prose blocks), sound, video, spots, panoramas, all outbound links and imperative UI
sentences (click/tap/press, Russian, Polish and Swedish equivalents) are removed.
The CLI reports the removed passage count. This bounded cue list is not a
semantic judgement: authors should read the print text for other UI references.
English click/tap/press cues require a UI object or direction, so ordinary
narrative uses of a water tap or printing press remain text.
No pedigree diagram is included: the existing tree model is interactive data,
and producing a paper diagram would require a new layout.

## Files and semantic classes

`index.html`, **`book.css`** and only the selected local images (original relative
paths). The stylesheet is the sole design surface; replace it in the book or in
the engine package before building. There are no inline styles. Checked SVG
dependencies stay local and relative; root-absolute SVG resources require a
relative derivative, since `/image` cannot resolve from a portable file folder.

| Class | Meaning |
|---|---|
| `book`, `book-a5` / `book-a4`, `book-full` / `book-kids` | Edition root, page size and text layer |
| `book-cover`, `book-edition`, `book-feed-titles` | Cover and feed inventory |
| `book-fictional`, `book-private` | Required delivery notices |
| `book-toc`, `book-body` | Linked contents and main text |
| `book-part`, `book-part-header` | Feed as a part; starts a page |
| `book-chapter`, `book-chapter-header`, `book-year` | Chapter and heading; next chapter starts a page |
| `book-figure`, `book-image`, `book-caption`, `book-credit`, `book-disclosure` | Illustration, attribution and reconstruction notice |
| `book-document`, `book-reading` | Crop with caption and original reading |
| `book-question`, `book-fact`, `book-fact-basis` | Printable question, stated fact and its grounds/weight |
| `book-evidence`, `book-version`, `book-place`, `book-extra` | Chapter-end grounds and additional material |

Native `header/nav/main/section/article/aside/figure/figcaption/blockquote`,
headings, paragraphs and lists retain meaning without CSS. Only contents has
links. IDs `part-N`, `chapter-N-M` are presentation anchors, not private IDs.
CSS uses mirrored inner/outer margins (20/16 mm), bottom page counters, ordinary
page breaks (no inserted recto blanks), orphans/widows and nonbreaking figures.
Oversized images shrink proportionally; an exceptionally long literal reading
can still exceed a physical page and needs PDF review or designer adjustment.

### Growing tree and document links

The reader computes origin and confirmation from the projected graph, not from
new family fields. Family memory follows attributed memory sources; a document
confirmation requires a non-derived, non-tentative birth, marriage, death or
parent link citing a documentary source. Existing manual confirmations remain
visible. Index entries, memory, images and unsupported inferences do not become
documentary confirmation.
The family's own imported tree (cards the graph marks `in_original_tree`) is the
narrator's memory: the export adds `family_memory` to those card statuses and the
tree shows a green check with the grounds "from the family tree". Setting
`tree.import_is_family_memory = false` in the family's `[settings]` turns this
off for an instance whose import is not the family's own tree. People added by
research keep the check only for a document or firm testimony. A document mark
without a check means documents exist that do not confirm the facts (muted on
the tree, said on the full card). The card collects permitted documents through the
source subjects and the person’s attributed claims as well as explicit media;
source captions and local record links remain available. The source kind is not
changed when a local derivative is delivered, and privacy exclusions still apply.

An unnamed placeholder connecting a proposed parent to children is shown on the
tree and the card exactly as the family data carries it (for example
`… Surname`); the engine never substitutes a child's surname, a feminine form or
a transliteration. The tree card has no dates or place and its links remain
tentative; the basis stays on the full card.

The tree is a window around one person: that person and partner side by side,
ancestors above in as many generations as fit (cards, then round marks, then
dots), children below, the card of that person beside it. A corner miniature
shows the whole family by year of birth and opens the full overview. Wheel and
pinch zoom in people, not pixels: inwards over a person moves the tree to that
person, keeping the branch that was drawn above them, with a way back; inwards
elsewhere drops a generation. Outwards adds a generation at each step; once all
are open it returns the way the gesture came in, and when the person was chosen
otherwise (a click, a `#person=` link, search) it steps along the kinship path
towards the family's home people (down to a child, up to a parent, across to a
partner), so the wheel always leads back to the wide tree. Only at a home person
with every generation open does the picture merely shrink. The minus button and
the `-` key do the same. The overview opens from the corner miniature alone,
never from a gesture. Each couple of parents is drawn father on
the left and mother on the right; a link without a recorded role takes it from
the parent's sex, so an unexplored paternal line keeps its side. A person nobody
recorded a birth year for shows the engine's guess in italics ("≈1895"), with
the relatives and the rule behind it under the card's evidence. A family memory is marked
with a check when it is firm, also when the family's own written answer is saved
as a record: that saved copy carries the telling and is not a document about the
person.
