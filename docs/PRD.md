# Familiar — PRD

> Product truth for Familiar. One file on purpose: it also carries early design
> notes and the plan until a split reduces drift more than it costs.
> The map from this file to code and method is the Why Graph: a router
> (`docs/why-graph.xml`) and one shard per capability. How the layer works
> here: `docs/why-layer.md`.
>
> Status 2026-11-12: architecture fixed, first capability (rules) being built.
> Everything marked `pilot` works inside the pilot instance (a private family
> repository) and has to earn its way here.

---

## 1) Problem

A family knows its last three generations by memory and almost nothing before.
Archives hold the rest as dead lines: a baptism entry, a passenger list, a card
in a military file. Turning those lines into a story a grandparent reads aloud
takes years of evenings, three or four scripts, palaeography, local history,
writing and drawing. One person rarely has all of it.

Agents can do that work. The pilot showed it on two family lines. It also
showed what breaks when the work is steered by hand: hundreds of rules written
after single remarks, checks that guard taste harder than truth, writers who
must read 190 KB before the first sentence, and a method that only works where
a rural parish kept its books.

## 2) Product

Familiar is an agent-run engine that researches a family and tells its living
history. A familiar is a companion that acts on its own: it searches records,
compares hands, weighs versions, restores the setting of a place and time, and
writes scenes. Every scene stands on a document; the reasoning sits one tap
away.

Familiar is the engine and the method. A family is an instance that uses it.

## 3) Users

- **Primary: the family's agents.** They read this repository first and then
  explain it to their host. Entry documents are written for them.
- **The host** — the person who keeps the family instance: brings papers and
  memories, logs in to archives, decides what is published.
- **Readers** — relatives of any age, usually on a phone. They never see
  engine vocabulary.

## 4) Use cases
<!-- PRD_ANCHOR: USE-CASES -->

- **UC-START** — a new family begins from living memory, home papers and an
  optional GEDCOM, and reaches a first honest page.
- **UC-RESEARCH** — an agent extends a line: finds records, reads them, weighs
  identity and kinship, records versions with weights.
- **UC-STORY** — evidence becomes a feed: scenario, text, document cut-outs,
  drawings, translations.
- **UC-READ** — a relative reads a chapter; "More" shows facts, weights and
  doubts; a document shows its cut-out and reading.
- **UC-CORRECT** — the family corrects a memory or a reading; affected pages
  are flagged, nothing is silently rewritten.
- **UC-TUNE** — the host changes voice, language, depth, privacy or drawing
  style through declared settings, never by editing the engine.
- **UC-REGION** — a family from another region plugs in a region pack: sources,
  site recipes, name variants, calendars, daily-life reference.
- **UC-SHOW** — the app is shown to strangers in demo mode with a fictional
  family.

## 5) Layers
<!-- PRD_ANCHOR: LAYERS -->

Four layers. A layer never contains content of a layer below it in this table.

| Layer | Holds | Changes when |
|---|---|---|
| **Engine and method** | skills, role sheets, trust core, pipeline, app, build | Familiar itself changes |
| **Region pack** | sources and their access rules, site recipes, variant dictionary, scripts and calendars, visual reference of daily life | the family comes from another region |
| **Family instance** | people, cases, versions, decisions, feeds, taste settings, media | always: this is the family |
| **Host environment** | which subscriptions, which models per role, concurrency, schedule, UI | the host works differently |

This repository holds the first layer and the contracts of the other three.
The default host environment is one subscription and no orchestration tooling.
Multi-subscription fleet management is a separate, project-independent tool;
Familiar only declares the interface it needs from it (model tier per role, a
gate before launching an agent). With one subscription the agent writes and the
host or another person independently reads and confirms the exact material.
Publication is an optional host-selected adapter: `none` by default, or explicit
`aws`; local build and loopback serving need no cloud configuration.

## 5a) Architecture
<!-- PRD_ANCHOR: ARCH -->

Three things on disk, never mixed.

```
familiar/                 the engine: this repository
  src/familiar/           code; one package, one command `familiar`
  method/                 the method as text and data
    rules/                trust core, rule catalog, settings registry
    roles/                role entry sheets
    skills/               skills
  regions/                region pack contract; packs may also live outside
  demo/                   the fictional family: an instance like any other
  scripts/                repository tooling (WHY validator)
  docs/  tests/

<family>/                 an instance: the family's own private repository
  familiar.toml           the family root: id, languages, region packs, paths,
                          settings and rule modes of this family
  exceptions.toml         "this rule does not apply here, because"
  tree/ cases/ versions/ feeds/ media/ ...   family data

<region pack>/            sources, recipes, variants, calendars, reference
  pack.toml               pack id, settings and rule modes of the region
```

- **The engine is installed, the instance is opened.** Family commands run
  against a family root found in this order: `--root`, `FAMILIAR_ROOT`, the
  nearest `familiar.toml` upward from the working directory. `method list/show`
  instead reads bundled resources without family lookup or startup maintenance.
- **The engine never writes into itself** while working for a family, and an
  instance never holds engine code. A family that needs different behaviour
  changes a setting, a mode or records an exception; if none fits, that is a
  request to the engine, not a local patch.
- **Data has a declared shape.** Each kind of family data the engine reads is
  named in the instance contract with its path key in `familiar.toml`. Code
  reads paths from the root, never from constants.
- **The demo family is the test fixture.** Every engine test runs on fictional
  data; the pilot proves the same code on a real family from outside.
- **Capabilities** (router of the Why Graph) are the unit of ownership and of
  extraction: rules, roles, instance, tree, research, pipeline, build, region,
  demo, host interface, governance.

## 5b) Instance contract
<!-- PRD_ANCHOR: INSTANCE -->

What a family root holds and how the engine finds it. Version 1.1 (major schema_version remains 1); the first
audit of the pilot found its paths bound in code in at least fifteen places of
the feed core alone, so the contract is introduced by pointing `[paths]` at
where things are today and moving one kind of data at a time.

```toml
schema_version = 1
region_packs = []            # ordered; later packs win

[engine]
version = "0.2.0"            # exact tested release, 0.MINOR.PATCH

[family]
id = "<stable opaque id>"
title = "<title for readers>"
source_language = "<BCP-47>"  # the language the family writes in
languages = ["<BCP-47>"]      # languages readers get
fictional = false             # optional boolean; invented demonstration family

[paths]                       # every key optional; defaults below
tree_snapshot = "tree/snapshot"            # people and families, normalised
imports = "imports"                        # originals of GEDCOM and exports, immutable
evidence = "tree/evidence.json"            # the research graph over the snapshot
contributions = "tree/contributions"       # packets from researchers, authorship kept
identity_decisions = "tree/identity-decisions.json"
working_version = "tree/working-version.json"
associations = "tree/associations.json"
card_reviews = "tree/card-reviews.json"
tree_metadata = "tree/metadata.json" # import origins, root, original-card and removed-edge annotations
cases = "cases"
versions = "versions"
questions = "family/questions"
answers = "family/answers"
memory = "family/memory"
privacy = "family/privacy.json"            # closed topics and people: data, not rules
variant_overrides = "family/variants.json" # the family's own name and place forms
feeds = "feeds"                            # one directory per feed
edition = "edition/cards.json"             # hand-written additions to cards
gallery = "edition/gallery.json"
records = "records"                        # any read document; literal fields kept
originals = "originals"                    # documents as received, read-only after intake
captures = "captures"                      # pages saved while searching
media = "media"                            # cut-outs and pictures, with a manifest
searches = "searches"                      # what was searched and what it covered
state = ".state"
build = ".build"
export = "export"                          # regenerated; never the only copy of anything

[settings]                    # values of declared settings
[modes]                       # modes of declared non-trust rules
```

- **Engine release.** New instances pin `[engine] version`; older unpinned instances
  remain readable. A malformed pin is a configuration error. `instance check`
  (including JSON) and `desk build` warn with both pinned and installed numbers
  on drift. A version difference alone does not establish schema incompatibility;
  structural validation remains authoritative. `instance record-release --wheel
  <installed-wheel> --commit <full-engine-commit>` verifies the wheel's package
  bytes against the installation and writes `work/engine-release.json` with the
  version, declared source commit and wheel SHA-256. The commit is host-provided
  provenance, not a signature or proof of a source-to-wheel build.
- **Paths are relative to `familiar.toml`**, never to the working directory or
  to a source file. A path that leaves the root is an error unless the host
  maps it (an external disk for `originals`).
- **Empty is valid.** A missing optional directory reads as an empty
  collection. The minimum for a first chapter: `[family]`, a snapshot of people
  (families may be empty), one feed directory, the documents and media that
  feed uses. No GEDCOM, drawing, game, translation or orchestration tool is
  required.
- **Executable v1 decisions (2026-11-12).** `Instance(root)` validates before
  returning metadata (`id`, `source_language`, `languages`, `region_packs`),
  `config`, `root`, and `path(key)`. Version is the integer major `1`; booleans,
  missing versions and other majors fail. All four family fields above are
  required, languages is nonempty; language tags are nonempty strings (full
  BCP-47 validation is deferred). Unknown family/path keys and non-text paths fail. fictional is optional, boolean, default false.
  `collection(key)` returns sorted data files (no directories, hidden files or CONTRACT.md) or decoded JSON; missing
  collections return `[]`, malformed existing JSON fails rather than disappearing.
- **Host mapping.** `FAMILIAR_HOST_PATHS` is a JSON object keyed by the canonical
  absolute family root, whose value maps declared path keys to absolute paths.
  The host may instead pass this object as `host_paths=`. It is out of band,
  never persisted by Familiar. A mapped key replaces the family path. Unmapped
  paths, including region pack paths, must resolve inside the root; symlinks
  are resolved. External region pack mapping is deferred. This is a resolution
  boundary, not protection against concurrent filesystem replacement.
- **Commands.** `instance init <dir> --title <text> --language <tag>` creates
  only the config exclusively (defaults: Untitled family, en). `instance paths`
  reports every location and its origin. `instance check` loads the entire rules
  cascade and validates present forms and references; missing optional data is valid.
  Both human output and `--json` return every finding. `instance check --path
  records/collector/` (repeatable) or `--prefix records/collector-` validates only
  selected JSON/JSONL files against available reference indexes. It reports its
  file set and scope, never a family publication verdict. No match is an error.
  Chapter readiness requires people and authored chapter text; cycle readiness
  requires actual cases, versions, evidence edges and searches, with no validation
  errors. Historical truth and editorial judgement remain review work; media and
  presentation checks belong to `feed check`. Directories alone prove no readiness.
- **Working tree versus reader output.** `tree build` and `tree stats` default to
  the private working graph. Explicit `reader export/serve --host-private --output DIR`
  provides the host's local reader with living/unknown facts and narrative;
  living documents and structured addresses remain excluded. Its labelled
  `host-private` generation cannot be published or certified as a clean release.
  Unclassified addresses in free prose require editorial review. Readable family inputs, including unpermitted living
  dates and places, remain available to the host and researchers. An unrelated
  unfinished chapter does not block this view. `--output DIR` stores a labelled
  `working-tree.json`, without a publication pointer or clean verdict.
  Private working trees and host-private readers take a stable **display input
  snapshot**: explicit record/source/provenance references in declared inputs
  select records (including recursive record references and saved index captures).
  Unreferenced records and search logs are neither read nor fingerprinted and
  cannot influence life assessment or enter the private bundle. Used records
  must pass their own form checks. `reader export --host-private --output DIR`
  remains a single command while collectors edit unrelated records/searches.
  Changes to selected inputs still refuse snapshot/build/commit and invalidate
  the local reader. This is not a publication waiver: public tree/reader output
  retains the whole-family gate, fingerprints, permissions and independent reading.
  Original/capture/import archives are selected by explicit file references.
  Absolute original references also resolve below the host-mapped `originals`
  root, just as local document delivery does; other external paths still fail.
  Record source metadata (`image`, `scan`, `original`) is descriptive, not a
  delivery route; only a record's declared `saved_result` selects a local file.
  The permanent media manifest declares its media files. Other archive bytes
  are absent from the private snapshot. Mutable forms are copied; immutable
  archives use hard links on the same volume with a verified-copy fallback.
  Staged edits detach links before writing, so failed mutations cannot change
  originals. Public validation fingerprints the adopted corpus and its selected files.
  Collector captures and unreferenced original/import/media archive bytes are
  working research material outside the gate snapshot and watch; explicit file
  references, import JSON and the media manifest select the inputs actually used.
  Their cleanup remains the host's responsibility.
  Snapshot scratch lives under `paths.state/snapshots`, beside the family by
  default. CLI startup and library snapshot use reap only leased Familiar
  directories older than 24 hours with a confirmed absent owner process;
  live, inaccessible, unmarked and legacy system-temp directories are retained.
  Cleanup reports one stderr line; logical snapshots of at least 256 MiB
  announce their size and archive-link policy without contaminating JSON output.
  **Reader words:** present the confident result, without justifying obvious
  deductions. Inferred name components stay in research data; a surname supplied
  from children has one plain explanation on the full card. Public living-name exclusions
  remain in force. Memory, including the host's account, is simply "family
  memory"; documents carry their own title. No operator/narrator terminology,
  "our version", "needs confirmation" labels or question-mark badges.
  Uncertainty stays in quiet colour/dotted links and "More"; an explicit derived
  basis appears only there, in one human sentence for a historically non-obvious
  conclusion. A host-supplied `placeholder` is the complete literal display name,
  in normal type, in every reader view; never strip its surname or parentheses.
  A tree card answers **who this is**: given name and surname without patronymic,
  known life years, and birthplace when known. Names wrap instead of truncating.
  Kinship, confidence, source variants and explanations belong to the full card;
  a possible connection is shown by the dotted line alone.
  Only without a placeholder may an unnamed person get a generated surname and
  formal kinship from the main viewer. Documents and researcher
  decisions lead the card, followed by family memory; retired versions stay in
  "More". Say little when little is known.
  `--view reader` selects permission-filtered output and checked generations.
  Python `build(instance, view='working')` is explicit; the existing Python
  default remains the checked reader projection for adapter compatibility.
  Ordinary unpermitted living fields are omitted, not a veto on the whole family.
  A chapter showing a living person's document or unpermitted image still refuses,
  naming the item. Free prose needs independent R1 reading.
  `reader preview` prints the permission-filtered reader graph/profile in a
  `state: preview` envelope; `--output DIR` saves exact review files and a ticket
  into a new directory. It needs no prior independent reading and creates no
  generation pointer, release or permission to publish. Other public guarantees
  still apply; it is suitable for inspecting living-person omissions before reading.
- **Rules compatibility.** Historical rules-only configs without both schema
  version and family metadata may still be loaded by the rules adapter, through
  `Instance(..., legacy_rules=True)`. Versioned configs always get full validation;
  new instances and instance commands never use this compatibility mode.
- **Intake normalises.** A GEDCOM, a home paper or a single memory all become
  people and families with provenance that tells memory from paper from import.
  The original import is kept unchanged.
- **Ids are opaque strings**, unique within a family and kind; nothing in the
  engine assumes a format. A document or picture is addressed by id; the
  manifest names the file.
- **Authored data, built data and export are separate.** What a person or an
  agent wrote is never stored only inside something a build regenerates.
- **Writes** go only to the instance's own roots; `originals` is read-only
  after intake; a build commits its checked generation by atomic pointer replacement.
- **Schemas carry a version.** An unknown major version stops a command before
  it writes.

What is not in the instance:

| Belongs to | Examples |
|---|---|
| Region pack | sources, site recipes and access rules, scripts and calendars, shared name and place forms, daily-life reference. A family's correction to a pack is a proposal, not a write into the installed pack |
| Host environment | where a pack is installed, port and address, publish target and credentials, browser sessions, model tiers and the launch gate, backup, and the shared ledger of load on sources: two families of one host do not get two independent limits on one site |

### Family data forms · contract 1.1
<!-- PRD_ANCHOR: FORMS -->

### Kinship words
<!-- PRD_ANCHOR: KINSHIP-WORDS -->

The reader names a relationship with its language's exact word first and offers
its explanation and permitted tree path on hover or tap. One table resolver
uses gender, the viewer's gender, parent/spouse side and generation distances;
unknown sex or a missing word keeps a descriptive fallback. The existing
qualification of uncertain links remains visible. Literal narrator kinship
still heads the card for that narrator, with computed kinship alongside it.

Russian, Polish and English language packs own their vocabulary and explanations,
including historical words with an explicit marker. The offline “Kinship words”
page is reachable from the menu and each explanation. It groups words and gives
examples relative to the selected viewer using only the permitted reader graph.
Without a matching permitted person it says there is no example; it never reads
research files. Half-siblings require known differing parents; step and spiritual
kinship require explicit links. A missing parent never proves a step relation.
The glossary has no separate children's mode; explanations use short definitions.

### Attributed card wording

**Attributed card wording.** Table memory items may retain literal `kinship`;
the memory's canonical `narrator` anchors it. The reader exposes each wording as
`person.reportedKinship: [{viewer, text, sources}]`. For that viewer the literal
word heads the card, even without a graph path; the computed path is a separate
qualified explanation. It is firm evidence of what the narrator said, not a new
kinship decision. Older combined person/kin table items can be projected from
their retained literal text. Switching the viewer never reuses another person's
wording. Kinship remains a permitted living-person surface.

A canonical name may carry `inferred_parts`, keyed by `given`, `patronymic`, or
`surname`, each with nonempty `basis` and optional source `provenance`. Other
parts retain their original status. Editable memory/table drafts accept this
structure; intake does not guess missing components from a parent. Private
cards mark the particular parts and show their bases. Public canonical names,
feed name signatures and person nodes omit inferred parts for living/unknown
people, irrespective of ordinary name consent. Authored free prose still needs
independent reading; component metadata cannot classify arbitrary prose.

**Clan surname display.** `tree_metadata.surname_forms[]` stores explicit decisions:
`id`, `form`, `variants[]`, `basis` (`family-memory` or `document-frequency`) and
optional `people[]` restricting membership. Without `people`, all people whose
literal surname matches an equivalent spelling are included, including regular
gender forms in the family language. Use `tree surname set ID --form FORM
--variant SPELLING` (repeat `--variant` and, if needed, `--person`). Omit `--form`
to select the most frequent attributed family-memory spelling, falling back to
the most frequent documentary spelling; ties retain source order. The command
saves the selected form, so later sources do not silently change the decision.
Change the row's `form` once or repeat the command to update every member's
tree, lists, line captions and generation strip on the next build. Canonical
`names[]`, record fields, quotes and crops remain literal. The full card says
“Written in records” using only that person's documentary surname spellings.
Regular Russian and Polish gender endings use the selected display language;
other surnames remain invariant. Cases in line titles follow existing reader rules.
A named father with no surname may receive a `derived-from-children` name with
`inferred_parts.surname` and the child ids as its basis; this is a reversible graph
derivation, never an input correction. Ambiguous fathers or competing child clans
prevent that inference. No mother's maiden name is supplied this way. Full cards
explain the derivation; public living/unknown names still omit inferred parts.
Instance checks report paternal spelling differences without a decision as
nonblocking `surname_findings`, with the next action “назови форму рода”.
Clan membership, form selection and these findings use birth surnames. Explicit
married names are excluded; an untyped surname shared with the woman's husband
is treated as married unless explicitly marked as a birth name. Ordinary gender
endings compare as one spelling. Attributed input names remain unchanged.

Derived facts use an origin-matching heading and badge. A firm place from a
combined birth/death column stays firm, with `uncertainty: event-kind`: only
the kind of event is unknown. Memory source captions say whose account it was
and when it was recorded; an internal operator role becomes the family narrator.
The reader does not repeat a death cause already present in its death fact.

Reader bundles carry the declared `paths.world_map` atlas and feed `play.json`: interactive picture spots, choice/lot games and registered panorama images. Public atlases retain only deceased attributed participants and visible route stops; the local host view retains the atlas. Game document rewards follow the enclosing chapter’s document exclusions. These are typed data, never executable family content.

**Naming an unnamed tree person.** A contribution may use its existing
`people` map to fill an existing card whose `name` and all recorded name parts
are empty. Supply only `names` (given/patronymic/surname with resolved
`provenance` source ids), optionally the matching `name`. The working card
retains the earlier `name` and `names` in `nameHistory`, with author and
contribution locator. A named card still refuses replacement; use a separate
evidence decision for a correction. No duplicate person or merge is needed.

**Text for the host.** `family requests [REQUEST] --text` renders one letter per
paper, with a greeting, family-history purpose, an unprompted question before
our version, one paper and why, a useful no-paper answer and a closing.
Request `question` is a versions-file ID; optional `witness_question` is the
unprompted memory question asked before `our_version`, as the supplied form shows.
`research form request` prints the JSON template and its storage instruction:
`family/questions/<id>.json`, or configured `paths.questions` (`instance paths`).
JSON/JSONL files mistakenly saved in `family/requests` outside that configured
collection produce a validation diagnostic with the destination; host output
refuses the misplaced input instead of silently claiming there are no requests.
Request `call_as` is the host's ready-to-use form of address, never inferred
from the full name; `sender_name` supplies the signature. Both are optional:
without them the pack supplies a neutral greeting and thank-you. Optional
`paper_description`, `look_in`, `photograph` supplies specific instructions;
absent paragraphs are omitted, never inferred from a title. An absent question
or version has no filler paragraph. A request addressed to `host` is a home-search
note, with its own next step and no wait for a reply to oneself. Researcher-only
`fallback`, `outcomes` and test instructions never become host advice; optional
`host_next` is the separate host-facing next step. Paper citations use semicolons.
`feed pages [FEED] --text [--page CHAPTER]` reads title, story, children's block
and support; its first line calls unreviewed, released or changed material a
draft. A current independent reading of the source page permits the reviewed
label. The text renderer is a private working view of the family's own page, with its
papers and words intact. It is labelled working material, not a reader publication.
A nearby explanation names whose information needs consent or life-status clarification.

`family confirmation` explains the machine checks, the reader's job, lapsing
confirmation and the limits of release; it is also printed before reading or
blind acceptance. `family next` gives at most two ordinary current actions,
plus the complete counted list of reader omissions: draft request,
dated wait, answer and its recorded decision, paper bridge, missing test or
unreviewed story. An unchanged wait stays a wait, without reissuing the request.
With accepted memories or papers but no question yet, `family next` asks for a
first case and discriminating paper; a tree alone asks for attributed memory.
Only an empty family gets the initial intake invitation.
`family summary` separates papers, firm testimony, hearsay, open questions with
their test paper, and stories ready for reading or needing a reader. A paper's
entry is not by itself a decision of identity or kinship.

All five are read-only, snapshot-based private `host` views. Their seal cannot
be committed as a reader generation. Unrelated publication failures do not deny
access to the host's own words. Source-language packs provide the wording;
missing wording reports a pack gap. Stored prose is never translated or rewritten.
Reader narrative is associated with canonical people, never by word matches.
Optional chapter `prose` divides title, text, more, ask or text_kids into
`{people: [...], text: ...}` blocks. Blocks about protected people require summary
permission; without it they are silently omitted, while other blocks remain.
A block may carry `otherwise: {people: [...], text: ...}`, an alternative written
by the author for exactly this case. It is shown only if its own declared people
permit it, and is part of the exact bytes independently reviewed. No engine
explanation or chapter `kind` becomes reader text. Optional `people` on each
place, fact, variant, extra, link or children's object permits independently
attributed parts to survive; absent attribution conservatively inherits chapter
people. This authoring attribution is not exported as prose.
Unsplit prose defaults to chapter people. Feed `prose` uses the same blocks
for title, lead, period and line; private host text retains them all. A name match only enters the review
worklist; meaning still requires independent reading. Neither command sends or publishes.

`family next`, `family requests` and `family summary` derive their omission
inventory from the same projection that removes reader bytes: each person once,
with affected chapter and paragraph counts and other omitted parts named.
Unknown life status produces a researcher question with the known birth date
and place. Known living people produce a request for permission to show the
exact omitted words, added to the existing family letter rather than a separate
letter per person; without a matching recipient it asks the relative to forward
the named question. It does not infer a recipient's identity from a nickname.
An explicit reply still has to be recorded; no question grants permission.

`instance init --language ru --address informal` connects the shipped Russian
pack and selects ты; `formal` (default) selects вы. `names[].patronymic` is an
optional literal part of a name. Identity proposals compare all names across
scripts and report matched fields; only an explicit decision merges people.

Life status is `dead`, `living` or `unknown` and is assessed after identity.
`privacy.living_years` in the setting registry defaults to 110 for every intake.
A birth upper bound before current year minus this horizon implies dead for
privacy, not a historical death date. Approximate births use a five-year margin; after-dates have no historic upper bound.
Missing birth may be bounded by directly
dated parents, children or spouse; conflicting estimates use their union.
Privacy bounds are deliberately wide (parent/child 0–120 years, spouses ±100),
never typical-generation averages that could declassify a younger spouse.
Dated canonical record subjects and attributed baptism/marriage events also bound
birth: child/baptized/named no later than the record, parent/godparent/spouse
at least 12 years earlier. A deceased role establishes death. Hypothetical
attributions, unlinked names, prose and source metadata provide no bound.
Record bounds do not propagate to relatives; conflicting bounds retain the union.
`privacy.json` may hold `life_decisions`: `{person, status, basis, by, at, revoked}`.
A written decision needs no death certificate; setting revoked=true cancels it.
An explicit living privacy declaration overrides derived death classifications.
Unknown remains distinct and receives the same reader protection as living.

A literal text document excerpt names record `excerpt` field keys. The record's
`field_subjects` assigns canonical people to each selected field; every displayed
reading must equal that literal field. An excerpt carries no full reading, scan,
asset or full-sheet link. Its closure includes only those fields' subjects plus
any additional author-declared subjects; a full sheet retains every subject.
Documents about protected people are excluded regardless of any consent.
Document subjects also accumulate from card galleries, chapter attachments and
facts citing their sources. Shared record, source and scan references retain the
union of these subjects in both reader modes; a protected attachment cannot be
released through an ancestor's gallery. Unattached documents remain withheld.
Image crops still need a reviewed derivative route; this text route cannot certify pixels.

The family gate produces a publication capability from a private input snapshot.
Only `instance/writer.py` writes family data in engine code, validating the changed
items. Other drafts do not block intake; family agents may hand-edit inputs. The
output boundary, not sole authorship, holds the trust promises in `docs/gate.md`.
Writer/output discipline is held by engine review and the retained data journey.
Reader fields are default-deny declarations in `instance/publication.py`: unknown
fields disappear at every depth; scalar declarations reject nested surfaces.
Living persons project to name and kinship; canonical permissions can widen only
explicitly permitted fields. Addresses and living documents have no declaration.
Canonical IDs and local symbols resolve independently of chapter.people; document
record mappings, picture subjects, mini-trees and covers also participate.

All declared text (all languages, captions, metadata, children's layers and literal
record pages) is literal NFC text, escaped by rendering. Text-form lint is
removed; undeclared fields still disappear. Restriction and name matches feed a nonblocking
review worklist. Clean output requires independent attestations bound to displayed
page and image bytes, language and scoped safety inputs; unreviewed output is preview.
`method/vocabulary.toml` supplies method enums and delivered
method vocabulary (`research vocabulary`). Probabilities are finite [0,1]; accepted
ones must be at least .5 with sources, basis and decision. JSON NaN/Infinity fail.
Acceptance applies recursively across all engine collections; quoted originals
are raw evidence, not engine acceptance decisions.

Output directories contain immutable `.generations/<digest>/` plus atomically
replaced `CURRENT.json`. Input fingerprints include permission/restriction bytes,
config and packs for snapshot consistency; provenance records engine version and
method hash, not source-code comments. Payload digests bind the exact generation.
Inputs are rechecked immediately before commit. A uses manifest records each shown
item/person/field/permission. Checked consumption refuses withdrawn uses or changed
payloads and names removals; unrelated edits make it outdated and still readable.
Diagnostics carry `output.state=preview` and a current blocked/clear verdict.
An external/static copy and direct filesystem reads outside the engine cannot be
revoked locally. See [gate guarantees and extension rules](gate.md).

**Family archive declaration (`paths.archive_rights`, default `family/archive-rights.json`)**

One storage-only object declares `schema_version: 1`, `kind: family-photograph`,
`holder`, `declared_by`, ISO dates `declared_at` and `effective_from`, and boolean
`permissions` (`family_app`, `processing`, `colourisation`). It explicitly has
`living_subject_consent: false`: ownership never grants the pictured person's
consent. It supplies rights to family photographs only. An image with `holder`,
`received_from`, or `rights` uses its own decision instead. The declaration is
fingerprinted for both publication and chapter approvals and is never projected
to the reader. Original archive bytes remain untouched.

**Scenario (`feeds/<id>/scenario.json`)**

An authored scenario holds `level` (card/page/feed), `basis` (case, version,
record and person locators), `through_object`, `rows`, `hardship_map`, and
`not_taken` (each fact's locator, reason and destination, usually More).
Each row carries a stable chapter id, hero, want/fear, turn, support locators,
version scenes, document placements, windows into daily life, and a children's
question. These are author judgements, not generated facts. The pipeline hashes
scenario.json with the other catalogs; a change invalidates prior approvals.

`feed pages [id]` exposes materialized chapters in order plus the explicit
`chapters[].hardships` annotations (kind, people, description). Missing
annotations are reported as unassessed pages; no deaths are inferred from prose.
`feed accept ID --stage reading --pages CHAPTER_ID ...` updates only those
pages; a whole-feed acceptance omits --pages. Unknown ids fail without writing.
`feed doc ID KEY --index READING --source SOURCE --where LOCATOR` creates an
index-only document with `kind=index` and `image_seen=false`, without assets.
`tree person ID` retains names/events, graph claims/links, sources, version
weights, touching cases, questions and records, with file locators; missing
weights stay unknown. `pack calendar YYYY-MM-DD --country CC --style
julian|gregorian` resolves a covering pack before converting; calendar choice
must come from reading the register. Church seasons/fasts remain explicit gaps
unless the pack supplies computable tables.

**Deferred parish norm form**

`research norm` needs a read-only index collection: stable entry id, source and
page/line locator, parish/place, record kind, literal date with calendar style,
normalized date, person and household ids, and explicit coverage intervals,
missing pages and indexing fraction. A household link must carry its evidence
and uncertainty so birth intervals do not merge namesakes. Counts must return
the denominator and coverage. Current instance forms have no such collection;
therefore the command remains planned.


Feed materialization: `feed build [id] --out DIR` commits `feeds.json` and
`status.json` in a checked generation below DIR (default paths.build/feeds). No family script is executed.
`feed read --out DIR` verifies and reads a stored catalogue.
`feed status [id]` reports per-chapter fingerprints, pending stages, translation
snapshots and waiting_family. `feed accept ID --stage STAGE` records a human or
agent review against the current dependencies; it is never called by build.
`feed new ID`, `feed person ID PERSON --name SOURCE_FORM`, and
`feed doc ID KEY FRAME BOX READING` prepare authored catalogs. Cropping requires
Pillow. They intentionally edit author data, unlike build/status.

`paths.feed_graph` optionally supplies an already materialized graph; without it,
person IDs come from snapshot people and evidence. `paths.media_archive` supplies
parked local assets. Defaults are export/graph.json and media-archive. Both follow
the instance path confinement and explicit host mapping contract.
Translations use `_source` as the source-snapshot key, independently of the
configured source language. Catalogs use stable corpus record IDs, never paths.
Crop indices use explicit `index_base`, defaulting to one-based; `field` is literal data. Build preserves order and chapter/catalog content.
In a chapter record reference, `kids: true` selects its `pick` crops for children, up to four crops per chapter in order. Without any marks, the first record and its first extra crop remain the default; `kidsRecords: false` hides all records.


JSON objects may carry `_about` and `fictional` metadata. Required fields are
marked R, optional fields O; empty arrays are valid unless stated otherwise.
Ids are nonempty strings unique within their kind. `records` is recursive;
each record id equals its filename stem, unique throughout that root.
`provenance` is a nonempty array of record ids, memory **item** ids, import ids,
or `host`. Version arguments additionally accept `pack:<pack>/<source>`;
this qualified syntax identifies a pack source, not proof of its historical claim.

**Intake additions**

`intake memory input.toml`: id, told_by, date, items (id, text, strength,
witness), people (local id, optional existing person id, sex, living, names,
events, notes), families (id, husband/wife local ids, children local ids,
provenance). Each name/event/note and family cites memory item ids in
provenance. An unnamed remembered person has names = []. Missing living
status defaults true for privacy. No text inference is performed.

**Kin Sheet 1 — лист родных.** A table is a telling, never a tree import.
`intake table relatives.xlsx --id relatives --told-by host --date YYYY-MM-DD
--language ru [--mapping columns.toml]` prepares private
`.state/intake/table-relatives/{memory.toml,reading.json,original.xlsx}`;
CSV/TSV use the same route. First nonempty row per sheet is the header.
Review the editable memory TOML and the complete addressed cell ledger, then
`intake memory .state/intake/table-relatives/memory.toml --original
.state/intake/table-relatives/original.xlsx`. Its SHA-256 binds the original;
acceptance copies it under originals and repeated acceptance is unchanged.
Preparation does not mutate the tree; it refuses replacement of a different draft.
Unknown headers are notes; `columns."Sheet1!A"="person"` in a separate TOML
mapping overrides a column (roles: person, person_kin, kin, birth, death,
birth_place, death_place, place, notes, witness, living).
Missing person columns reject together with all cell findings.
Every nonempty cell is an attributed literal item or addressed loss (headers).
Raw Excel serial, date format, rendered text and link remain with the item;
unsupported displays and cached formulas are reported. Excel display locale
is not stored reliably: d mmmm yyyy assumes Russian, builtin 14 assumes US;
other date displays stay raw with a loss, never a fabricated display.
Unambiguous parent/grandparent items without doubt default to firm, assuming
acquaintance; other items are hearsay. Every item names the applied rule and
witness; reviewers must check this assumption. Exact textual/Excel dates become
events. Doubtful dates and shared birth/death places stay card facts with status,
never accepted events. A dash is an addressed empty-value loss. Parsed names use title case; literal items retain exact spelling. Pack-labelled card facts
exclude duplicate names and events; narrator questions are separate from reviewer hints.
Dictionary paths create bridges. Patronymic, an exact surname or neighbouring surname context and compatible
generations can propose a family in `relationship_hypotheses`; `enabled=false`
removes that family and both card notes before acceptance. Similar surnames never merge.
No name matches merge people. The narrator is living and anchors the tree; memory
may name `narrator` by local person id (or `told_by` matching that key).
Unnamed bridge people carry `placeholder` in the family language, never an invented
name. Intake-generated facts, families and parent edges carry `derived=true` and
`basis` (one family-language rationale); narrator statements omit `derived`, even
when doubtful. Draft `narrator` is a local id; accepted metadata `narrator` and
`root` are canonical ids. Working graph `narrator`, `defaultViewer` and `root`
resolve identity aliases. Reader projection must retain `placeholder`, `derived`,
`basis`, `narrator` and `defaultViewer`; the display owns kin labels and layout.
Other life status is unknown unless explicitly supplied;
existing living protections apply to this ordinary memory intake.
`forms/kin-sheet.csv` is the blank Russian template: одна строка — один человек,
сомнение помечать «?», ничего не выдумывать, пустое оставлять пустым.
RU synonyms and kin paths, PL/EN template headers live in language packs.
The host downloads Google Sheets: public sheets offer `.../export?format=xlsx`.
No network or automatic identity acceptance. External links stay in literal items
and private reading-report research leads; card prose points to the original cell.
`research form research-permission.json` supplies a short permission form; save it
at `paths.research_permission` (default `family/research-permission.json`). It records
authorizer, recipient, date, transmission, research and personal-show scope, excluding
publication. Summary reports its presence. It grants no publication permission;
existing privacy consents and independent reading remain required.
Initialization supplies `* -text` git attributes and ignores environment, state, build
and default reader-output directories, preserving any existing git policy files.

`intake paper reading.toml --original scan`: id, people/families as above,
record (title, source, language, fields, reading, doubt, people mapping literal
names to local ids). Reading and literal fields must be supplied by a reader.
Original bytes are preserved under originals/<id>/; the record id is the intake
id. Claims cite that id. Torn text stays in fields/reading and doubt.

`intake gedcom file --id id --living-years 110 --as-of YYYY-MM-DD` accepts UTF-8
GEDCOM, preserves original bytes under imports/<id>/ and emits an import
manifest. Supported individual names, sex, inline notes, dated/placed events,
family spouses, children and union events normalize into snapshot forms.
`_MARNM` becomes a married name, and `EVEN/TYPE` preserves the event description.
`PHRASE` wording survives in attributed notes beside its full tag path and parent
value, including unsupported adoption/role enums. Union notes remain in the
snapshot; they have no public reader declaration. Preserving a phrase does not
interpret its role or create an adoption relationship; unsupported parent tags
still appear in the loss report.
GEDCOM claims and imported kinship default to hypotheses, with the attribution
"Recorded in another tree (unverified)"; inline/referenced `SOUR` titles,
`PAGE` and `QUAY` remain source text, never family testimony or a weight.
Unrepresented tags (including subfields of supported tags) appear with counts
in .state/intake/<id>.json. A tag retained only in the original is a loss from
the normalized forms. Unknown birth defaults living; otherwise no death and
latest birth year newer than as-of year minus threshold means living.

Reports in .state/intake include digest, counts, losses, next_step and
candidates. A repeated id with identical content is idempotent; changed content
requires a new id. Existing IDs must be explicitly declared via existing;
names alone never merge. Candidates use canonical, alias, sources, evidence,
next_test and status=candidate. They are proposals for identity_decisions.merges,
never automatically accepted. `research form identity.json` lists the required
presentation and decision fields. An accepted identity redirects both edge
endpoint spellings and families, retains both sets of names/events/claims, and
resolves old document references to the active canonical card. Removing the
decision restores the unchanged source cards. Identity acceptance does not
promote the imported claims to accepted facts.
The snapshot additionally retains display/tag/plain adapter fields for the
current graph builder. Contributions preserve attributed claim sources in the
derived graph. Intake does not establish document identity or kinship truth.

**Documentary decisions and card documents.** `research form contribution.json`
supplies the form for `research contribute FILE.json`. The writer saves a new
attributed package, validates it atomically and leaves the snapshot untouched.
`relationship_decisions[]` selects exactly one existing union (`family`) or
parent/child pair; `previous_status` protects against stale decisions. Sources,
status, plain text and basis are required. Old link data stays in derived history;
accepting a union does not accept its parent links. `fact_replacements[]` names
one prior text/source set, its replacement and a retirement reason; the old fact
survives in `retiredFacts`. `events` adds dated, record-backed person events.
Removing a contribution restores the unchanged inputs.

`research form card-document.json` supplies the form for `research document
FILE.json --author ID`: canonical `record`, existing canonical `subjects`, optional
`snippets` with file, caption and literal read. File names are relative to the
form. One atomic writer operation saves the corpus record, source, per-person
attachments and checksummed PNG/JPEG/WebP cut-outs in the permanent manifest.
Existing records, contributions and media are refused; use a new ID. A document
attachment itself establishes no identity or relationship. The usual accumulated
subject and living-document exclusions apply to its reading, scan and source link.
Record `subjects` accepts canonical ID strings for attachments; structured roles
still require the literal `written` name. Attaching a card invents neither.

**Person (`tree_snapshot/people.json`, wrapper `people[]`)**

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `id` | R | Stable person id | always |
| `sex` | R | Recorded sex or unknown | permission:sex |
| `living` | R | Boolean living status | never |
| `names[]` | R | given, surname, type (birth/married/as-written), provenance | always |
| `events[]` | R | Events below | permission:events |
| `notes[]` | R | text and provenance | permission:notes |

**Family (`families.json`, wrapper `families[]`)**

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `id` | R | Stable family id | kinship always; events require subject policy |
| `husband, wife` | O | Person ids or null; no placeholder people | kinship always; events require subject policy |
| `children[]` | R | Person ids | kinship always; events require subject policy |
| `events[]` | R | Events of the union | kinship always; events require subject policy |
| `provenance[]` | R | Ground for family assertions | kinship always; events require subject policy |

**Event**

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `type` | R | Event kind | permission for living subject; always for deceased |
| `date` | R | Literal date text, including uncertainty | permission for living subject; always for deceased |
| `place` | O | Place text or null; a map may be absent | permission for living subject; always for deceased |
| `provenance[]` | R | Ground for the assertion | permission for living subject; always for deceased |
| `value, note` | O | Recorded value and explanation | permission for living subject; always for deceased |
| `open_question` | O | Id in versions; unresolved place may remain null | permission for living subject; always for deceased |

**Evidence graph (`evidence`)**

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `sources[]` | O | id, kind, record id; memory points to memory item; import points to an import manifest, never a fabricated document | declared graph projection; research/context/withdrawals never |
| `edges[]` | R | type, from/to person ids, sources, confidence (same/probable/possible) | declared graph projection; research/context/withdrawals never |
| `people, context` | O | Additional graph assertions and context | declared graph projection; research/context/withdrawals never |
| `remove_edges[], research[]` | O | Withdrawals; case and question links | declared graph projection; research/context/withdrawals never |

**Memory (`memory/*.json`)**

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `id, told_by, date` | R | Telling id, narrator, telling date | never (research only) |
| `items[]` | R | id, text, strength (firm/hearsay), witness (how teller could know) | never (research only) |

**Read record (`records/**/*.json`)**

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `id` | R | Filename stem | never for living subjects; declared record projection otherwise |
| `kind` | R | home-paper / archive-record / index-entry | never for living subjects; declared record projection otherwise |
| `title` | R | Document title | never for living subjects; declared record projection otherwise |
| `source` | R | Holder/archive locator, received date, description, image or null | never for living subjects; declared record projection otherwise |
| `language[]` | R | Document languages | never for living subjects; declared record projection otherwise |
| `fields` | R | Literal field names and readings | never for living subjects; declared record projection otherwise |
| `reading` | R | Literal reading, or empty when nonempty literal fields are preserved; empty reading and fields together fail | never for living subjects; declared record projection otherwise |
| `doubt[]` | O | field and explanation of uncertain letters | never for living subjects; declared record projection otherwise |
| `people` | O | Written name to person id mapping | never for living subjects; declared record projection otherwise |
| `person, events[], relatives[], match, privacy` | O | Extraction, identity assessment and publication restrictions | never for living subjects; declared record projection otherwise |

Missing descriptive source fields are null, not a reason to discard a record.
Name components, sex and event dates may be absent/null; names, event types,
provenance and collection structure remain required. A record with literal
fields needs no `reading`; null/absent reading is valid with nonempty fields.
Wrong field types still fail; no name, date or sex is inferred.

Records, version questions/alternatives and searches may carry optional
`interest: {level, tell}`: finite level 0–1 and one line of what to tell.
Either member or the object may be null/absent (unassessed). This is editorial
interest, separate from probability, retained for the story-scenario shortlist
and never used to discard research or automatically select a scene. It is
research metadata and has no reader projection. `research form record.json`,
`version.json`, `search.json` and `paper.toml` show the supplied forms.

**Open question (`versions/*.json`)**

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `id, title, line, people[], status` | R | Question identity, scope and current status | never (research only) |
| `unknown_weight` | R | Share reserved for unknown alternatives | never (research only) |
| `versions[]` | R | id, label, weight, for/against arrays of text and sources; optional state, people, place, reading | never (research only) |
| `tests[]` | R | Next discriminating tests: text, where, would | never (research only) |
| `updated, summary, advice[]` | O | Revision date, orientation and recommendations | never (research only) |

**Search and coverage (`searches/*.jsonl`)**

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `id, at, by, source, question, query, hits` | R | Search identity, time, executor `{agent, model, effort}`, region catalogue source id, question id, actual query and hit count | never (research only) |
| `people[]` | O | Tree ids the search was run for; `people_basis` (declared, inferred, unresolved) after migration. `research coverage` reads it | never (research only) |
| `coverage` | R | Actual read scope: years, forms, read, note; optional indexed/total counts | never (research only) |
| `meaning` | R for zero hits | What absence can and cannot establish | never (research only) |
| `strict, control, saved[], result` | O | Matching mode, positive control, record ids and result | never (research only) |

**Case (`cases/*.json`)**

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `id, question` | R | Case and open-question id | never (research only) |
| `state` | R | open / waiting-for-family / bridged / review / waiting / closed | never (research only) |
| `waiting_on` | R when waiting-for-family | Request id | never (research only) |
| `story_level` | R | card / story-page / feed | never (research only) |
| `basis[]` | R | Provenance supporting the level | never (research only) |
| `narrative` | O | Companion working Markdown, not machine state | never (research only) |

**Research additions (existing field changed: case state enum only)**

Cases add `outcome` (required nonempty text when closed), `waiting` (required
when waiting: reason, resumes_on, holder = family/source-access/reviewer),
optional `budget` (unit, finite nonnegative limit and spent, checkpoint).
Spent may exceed limit: this records exhaustion, never erases work already done.
Legacy waiting-for-family remains valid with its request reference.

Version arguments add required `dependency_group`: arguments from the same
original, including copies/indexes/readings, share this group and count once.
An argument's `sources[]` may also name `search:<id>` for a saved search with
positive hits. This is weak index support, not a read original or documentary
acceptance; record the limitation in argument text and keep its weight low.
Copies and index rows from one source share `dependency_group`. No conversion
of every hit to a record is required. Missing, empty or inaccessible searches
cannot supply this positive support. There is no automatic weight arithmetic.
Tests add required `outcomes[]`: kind, observation, nonempty effects[]. Include
positive, contrary, unavailable and unreadable. Each effect names version
(version id or unknown), change (raise/lower/unchanged/reconsider), reason.
Existing text/where/would remain descriptive; no automatic weight arithmetic.

Cases add optional `second_looks[]`: id, claim, scope, inspected[] (nonempty
locators), missing[] (may be empty), objections[] (may be empty; text, locator,
strength strong/moderate/weak), verdict correct/contested/error, next_test,
owner_response {state, text}. Use state=pending with an explicit pending text
until the owner answers; a reviewer cannot impersonate the owner.

`research packet --case <id>` or `--people <ids>` assembles an instance-only
packet; `--mode owner` includes primary evidence then the owner argument.
`--mode second-look` withholds arguments and weights until `--stage argument`,
after the checker saves its own evidence table. This is an agent protocol,
not access control. `--json` returns the same data. `--max-chars` bounds compact
JSON (default 24000) with an omission manifest; missing collections are named.
Unlinked memories, answers and records are explicitly included as supersets.
Original images are referenced, never certified as read by packet assembly.

<!-- PRD_ANCHOR: PERSON-CARD -->

`research person <ID-or-name>` is the story author's private discovery card.
It works for a person absent from the tree too. It keeps parents, spouses,
children, siblings and half-siblings with their attributed relation status;
`--relative ID` adds a candidate research seed without asserting kinship.
It searches canonical research inputs and extra collections declared by the
family, including unlinked observations and surname neighbours. `--alias NAME`
adds a spelling; the engine never rejects a hit for a conflicting date, parent
or place. Recorded versions, weights, literal fields and match qualifications
remain at their source; missing weights stay unknown. Retrieval is not an
identity or kinship decision.

Default canonical discovery includes both JSON and JSONL (including the search
log); coverage counts read files and retains each matching line's locator.
`research form search` (or `search.json`) supplies fields and storage instructions.

The front table repeats literal family fields and typed relatives of direct
name/relative hits, with their source locators and recorded match levels.
Grouping identical written family fields is not a merger of people; a parent's
surname is never inferred from a child's. A second table quotes version labels,
supplied weights and the unknown share, without reweighting them. Unlabelled
cells and free prose remain in the observations for the author to interpret.

Configuration belongs to `familiar.toml`, for example (invented family):

```toml
[research.person_card.aliases]
"Bea Example" = ["Beatrice Example"]

[[research.person_card.sources]]
id = "old-readings"
path = "research/readings"
glob = "**/*.md"
historical = true

[[research.person_card.sources]]
id = "village-index"
path = "research/village.json"
historical = true
```

Each source has a unique `id`, `path` relative to the family, or `path_key`
with an optional path confined below that declared instance/host root. Hidden
directories are skipped; use `exclude` glob patterns to skip other caches.
JSON arrays/containers split into whole observations (optional `pointer` selects
a subtree); JSONL uses line locators. Text retains complete matching paragraphs
or table rows and exact line ranges, retaining context under matching person
headings (`heading_context = false` disables that expansion; context collections
default to it disabled). SQLite requires `format = "sqlite"` and a
single `query = "SELECT ..."`; it opens with `mode=ro`, `immutable=1` and `query_only`, optional
`key` names a stable row ID, and `decode = ["payload"]` parses JSON columns.
A nonempty WAL is an explicit access gap: supply a checkpointed snapshot;
the card never checkpoints or creates database sidecars. A source changing
during a read is reported and its observations discarded.
For imported record histories, `record_arrays = { "/previous" = "/record" }`
declares arrays of independent observations: each payload has its exact nested
locator, each container's remaining context is retained in `origins`, and the
parent lists its `expanded_arrays` rather than repeating their bodies. A matched
parent retains every historical payload without a second name/date filter.
Privacy is assessed separately on each payload and its container context;
unexpanded nested protected records conservatively close the containing body.
`kind` labels a collection; `terms` adds place or context search terms; `include`
explicitly includes an entire small context source. Matching is token based,
case/diacritic folded; it is not transliteration or fuzzy identity matching.
An alias that contains just a surname broadens retrieval deliberately.
Optional `people` limits a collection to named queries/IDs, with a visible
out-of-scope coverage mark. `reference_roots` lists additional relative family
directories for resolving old copy pointers; file-relative pointers are also
checked. A `kind = "context"` source alone may declare `context_fields` to show
just, for example, its title; the remaining field names and exact full-content
locator remain in the card. Family record observations are not projected this
way.

`historical = true` declares a family-reviewed historical collection, not an
automatic age inference. Unclassified legacy bodies stay closed by default.
Canonical living/unknown cards expose name and kinship only; protected subject
IDs, known living names, record privacy flags, living-status prose cues and closed-topic cues close
observation bodies with reasons. Name-only hits in historical prose require
review and do not identify that prose with an unknown canonical person.
This diagnostic is a preview, never a checked reader publication or permission
to expose living documents. No source is modified and no URL is fetched.

The default is a reading overview: every open observation has a short excerpt,
retrieval scope and supplied match qualification. Its zero-based row index is
a locator: `--observation N` returns that whole observation with every original
file/line/JSON/SQLite locator, copy pointer and import envelope. Use identical
query/seeds/catalog and unchanged inputs. Closed row indices refer to the
`--full --inline` closed array. Written-name
groups do not merge identities. Story/context row indices point into the same
manifest. Folded counts cover bodies, import envelopes, container context and
copy pointers. Ellipses mark shortened prose; the complete record remains at
its locator. Reader relationship calculation and Russian words are reused
(Node.js required for this part); an absent tree candidate has no asserted kinship.
`--full` restores literal bodies and reversible sharing described below.

`--catalog FILE` trials the same `[research.person_card]` TOML configuration
without changing family settings. Compact JSON on stdout is bounded by
`--max-chars` (default 800000 Unicode characters): all retrieved locators,
closed reasons, unreadable/missing collection coverage and body omissions are
explicit. If even the locator manifest cannot fit, the command fails rather
than claim complete retrieval. Identical observations share locators; distinct
readings are never collapsed. Canonical import envelopes are retained alongside
each representation of the same unchanged observation. By default repeated
data values are shared inside observation data/copies (`$ref` into `shared_values`,
`$literal` escapes a source object); recurring record layouts use
`{"$row": [ID, cells]}` with their exact keys in `value_columns[ID]`.
Repeated HTML, URL and line fragments use `{"$text": parts}`: concatenate the
resolved string parts to recover the exact original, including markup and
uncertain letters. This does not render, clean or shorten the source reading.
Repeated locators use `$Cx` and
`locator_values`, repeated locator prefixes use `@Lx` and `locator_roots`, and closure reason codes
resolve in `closure_reasons`. These are reversible encodings, not abridgements.
Repeated metadata keys are declared once in `table_columns`; the named sections
use arrays in that column order, with null for absent summary metadata. Literal
record fields are unchanged. `--inline` returns object rows, repeated values and
full locators instead. Copy pointers say local, missing, undeclared host
or remote; assembly never claims an image was inspected. An undeclared collection
or unlisted spelling is a coverage gap, not absence of a family record.
`familiar.research.card_context.expand_card` expands a compact card to ordinary
object rows, literal record fields, full locators and written closure reasons,
without opening a family or fetching a URL. The installed journey compares
these observation fields with the inline form from the same installed engine.

Collector records and search journals report form findings as `research_in_progress`
without blocking display, desk, reader, feeds or release; `instance check --path`
remains strict. Explicit references from tree, memory, feeds, cases or versions
adopt research recursively: those inputs must validate and remain stable for output.

`instance check` reports research_ready and next role/skill independently of
chapter readiness: researcher: memory-first, name a bridge paper before indexes;
parish-first researchers select research-versions after inspecting the anchor.

**Request to relatives (`questions/*.json`)**

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `id, case, question` | R | Request, case id and question id | never (research only) |
| `our_version` | R | Our version for relatives to correct | never (research only) |
| `paper` | R | One paper as text, never an array | never (research only) |
| `why_this_paper` | R | Discriminating field expected | never (research only) |
| `outcomes` | R | Answer to next action mapping, >=2 entries including no-paper | never (research only) |
| `addressee, holder_reason` | R | Who and why they may hold the paper | never (research only) |
| `state` | R | draft / asked / answered / not-presented / closed | never (research only) |
| `answer` | R when answered | Id in answers | never (research only) |
| `witness_question, fallback, priority, asked_at, answered_at` | O | Witness-bounded question, alternative, ordering and dates | never (research only) |

**Feed head (`feeds/<id>/feed.json`)**

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `id, title, lead` | R | Feed identity and introduction | declared feed projection; persons/profile stay internal |
| `persons` | R | Local symbol to person id map | declared feed projection; persons/profile stay internal |
| `profile` | R | anchor, readers, kids, pictures, depth, languages, games, names | declared feed projection; persons/profile stay internal |
| `people[], period, line, cover, parts[], gens[]` | O | Presentation order, period, line, cover and divisions | declared feed projection; persons/profile stay internal |

Crop selection uses explicit `index_base` (0 or 1), on a reference or its document;
absence means 1. Snippet `field` never changes indexing. Invalid selections stop
build with a chapter locator. Replacing a full frame under existing crops is
rejected: use a new document key and recrop. Approval fingerprints include authored
scenario/lab/studio inputs, effective settings/rules, records and nested media.
`profile.scripts` optionally maps language tags to Unicode script names for
generation-label validation; the engine assumes no language alphabet.

**Chapter (`chapters.json` array)**

`research form chapters` emits the complete array; `research form chapter`
emits one object to place inside that array.

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `id, title, text, people[], records[]` | R | Identity, prose, local person symbols, document references (doc, pick) | declared chapter projection; unknown fields never |
| `text_kids` | R when kids.layer=separate_text | Separate children prose | declared chapter projection; unknown fields never |
| `year, part, kind, more, ask, picture, flow[], facts[], variants[], places[]` | O | Date/division, expansion, kids block, art, placement, evidence and places; map nullable | declared chapter projection; unknown fields never |

**Feed document (`documents.json`, keyed by document id)**

`research form documents` emits the complete object; `research form document`
emits one value to put under its document id, for example `{"paper": <value>}`.
`research form evidence` emits the `tree/evidence.json` object with sources
and edges arrays; replace the fictional person and source references with saved ids.
A source introduced by intake is declared only by that intake contribution;
evidence edges reference its id without redeclaring it in evidence sources.

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `record, caption, source, snippets[]` | R | Record id, caption, attribution, snippets (asset nullable, field, read) | declared document projection; never for living subjects |
| `full, where, fictional` | O | Full image nullable, locator, invented marker | declared document projection; never for living subjects |

Chapter `extras[]` carries title/text/more/kids, records and a picture (catalogue
key or image object). An image `orig` may be a local asset string (projected as
an image asset object), or a nested image object; both undergo asset checks.

**Image trust forms.** Pictures use `kind`: `period-picture` (source and open
licence), `family-photograph` (holder; permission for living subjects),
`document-scan` (record reference, no open licence requirement), or
`generated-reconstruction` (reconstruction=true and disclosure; never a portrait).
Legacy untyped pictures remain period pictures. `subjects[]` names local feed
symbols or canonical person ids; [] explicitly says no people are shown.
Missing subjects beside living people is an unverified association signal.
`media_roots` in familiar.toml is a nonempty list of declared path keys, default
["media", "media_archive"]; each file must exist inside one of these roots.

Records optionally carry `subjects[] = {person, role, written}` for every person
in a marriage, census or newspaper. Legacy `person` and `people` remain valid.
An index-entry can have `saved_result: null`: it is a locator with an unsaved
result, never proof of a read original. A non-null saved_result is a local file
path, included in the immutable input snapshot and dependency fingerprint.
Missing saved results are reported as evidence gaps when used in a feed.
Literal record fields may contain nested maps and lists: every key and leaf is
rendered as escaped text and restriction-scanned, without language filtering.
This does not authorize arbitrary nested metadata in other reader fields.

Restricted vocabulary entries may remain strings or become `{term,
family_person, family_period:[first_year,last_year]}`. The binding exempts only
a chapter explicitly naming that tree person and dated within that period;
undated chapters still require review. It never exempts every use of a surname.
Life status is living/dead/unknown, combined with privacy.living; absent dates
or explicit classification remain unknown and are reported separately.

**Privacy (`privacy`)**

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `closed_topics[]` | O | Family-defined closed subjects | never (research only) |
| `living[]` | O | Objects: id (person), allowed[] (canonical INFO_FIELDS identifiers; local labels are separate), consent | never (research only) |
| `consent` | R if allowed is nonempty | by (giver), at (date); absent/null means no recorded permission | never (research only) |
| `living_rule` | O | Family explanation; cannot weaken TRUST-06 | never (research only) |

**Answer (`answers/*.json`)**

| Field | Required | Meaning | Publication |
|---|---|---|---|
| `id, request, by, at, text` | R | Answer id, request id, narrator, time, actual reply | never (research only) |

Without a permission record a living person is limited to name and kinship.

Reader card surface dictionary (the recursive allow-list is
`instance/publication.py`; unknown nested keys are discarded):

`paths.edition` selects an optional JSON file or a directory of JSON files with
`schema_version: 1` and `people: {person_id: patch}`. A legacy people/updates/feeds
envelope supplies only card patches; feeds and updates retain their own pipeline.
Patches can set name, namePresentation, cardPresentation, story, storyMore,
summary, facts, media, illustrations and relationshipUncertain. Story and
storyMore are text or configured language maps; a story can retain the reader's
`\n---\n` separator for its expandable continuation. Card years and dateBasis
are presentation decisions, never research events or life-status evidence.
`birthGuess` is the engine's orientation year for a person without a recorded
birth (`tree/birth_guess.py`, setting `tree.first_child_age`): the first known
child minus a parent's usual age at a first child, else a spouse, brothers and
sisters, then parents; a real date beats a chain of guesses and one timeline
keeps a guessed parent older than every child. It is computed at each reader
build after the restriction, rounded to five years, dead-only in a public
projection, and is never stored, a research bound or life-status evidence.
An edition fact list replaces the curated list, retaining only additional facts
explicitly marked `card: true`; evidence statuses and acceptance rules still apply.
Canonical cards win collisions with merged aliases. Duplicate cards across files
are errors. Selected media must have local asset URLs (and optional originalAsset,
full, source IDs, photo flag and title); missing files fail instance validation,
even for private cards. The projection applies the edition inside the privacy
boundary; no caller can reinstate private editorial fields after that boundary.

| Field | Reader meaning and shape | Disclosure |
|---|---|---|
| `placeholder` | family-language role for an unnamed person; fallback is “name not recorded” | name and kinship only |
| `events[].cause` | literal cause of death | same permission as the event |
| `facts[].derived, testimony, basis` | our inference versus firm/uncertain family account, with its reason | same permission as the fact |
| `families[].status, derived, basis` | qualified union; basis may contain narrative | basis requires dead family members in public mode |
| `narrator, defaultViewer` | declared viewer references; absent viewer never implies “your” | kinship only |
| `readerLabels` | language-pack display words | no family data |
| `namePresentation` | display/full/source name, patronymic, maiden surname, note; sex/marriage and surname flags, maiden status and source references | dead only |
| `story, storyMore` | multilingual card narrative and expandable continuation | dead only |
| `illustrations[]` | selected attributed images using the image schema | dead only |
| `confirmation` | level, identityAccepted, research, translated basis and source references; does not confirm relatives | dead only |
| `retiredFacts[]` | fact fields plus `retiredBecause`; previous claims, never current facts | dead only |
| `public_fact` | attributed reader prose, not a publication permission | dead only |
| `status` | card-level research qualification, separate from fact and relationship status | dead only |
| `identityAliases[]` | former person references for navigation; global alias map remains navigation | dead only on person |
| `cardStatuses[person]` | origin flags, badges(text/title/kind), review(kind/likelihood/text/replaces/sources), confirmed facts and documented/candidate edges | dead owner only; relationship explanations also require dead endpoints |
| `cardPresentation` | birth/death/place and kinds/role; translated connectionNote/connectionShort/dateBasis/dateReference | explanations dead only; existing individual birth/death permissions retain only the corresponding date and kind |
| `living_basis` | internal assessment supporting privacy classification | never |
| `author` | internal contributor attribution, potentially an agent identifier | never |
| `imported_context` | raw import context, possibly private source details and locators | never |

The new compound card surfaces deliberately have no consent widening path.
Existing `name`, `events`, `facts` and other canonical permissions continue to
govern their existing fields; they do not authorize an entire card explanation.
Unknown life status is protected even with all existing permissions. All new
display text is scanned in every configured language. Reference lists carry IDs,
not display prose. A generation records card-status owners and relationship
endpoints so a changed life assessment invalidates consumption.
An empty allowed list is not consent to publish any other information.

**Legacy, read through adapters.** The existing graph builder's snapshot,
evidence, identity decisions and contributions remain its adapter inputs; no
conversion or graph rewriting is implied here. Older snapshot/import shapes
need their existing tree adapter before strict normalized-form validation.
Legacy feed document `record` paths are accepted by the instance validator
alongside record ids; the demo retains these paths for feed consumers.
Legacy Markdown cases keep their prose, but need a JSON state companion.
Legacy questions `note/items` queues and help prose (topic/question/why/hint/who,
status=open) require an explicit request adapter; prose alone cannot prove one
paper or exhaustive outcomes. Legacy edition people/updates/feeds is read by
its edition adapter, not treated as canonical cards. Distributed searches,
privacy rules, variants and archives require manifests/adapters; missing
normalized data must never be certified complete. Strict instance checking
reports unmigrated forms, rather than silently treating them as valid.

**File-valued settings.** Keep `privacy.closed_topics_file`,
`privacy.present_day_politics_file`, `lang.lexicon` as settings so existing
feed-scoped overrides and provenance survive. They do not become new path keys.
`Instance.data_file(value)` resolves them inside the root (including symlink
resolution), rejecting traversal and absolute escapes. Empty returns `empty`,
a nonexistent file `missing`, read failure `unreadable`, otherwise `readable`.
Registry validates confinement on loading every assignment; instance checking
reports all effective family/feed outcomes and treats missing/unreadable
configured files as errors. Consumers must use this resolver, never root/value
string concatenation. No file-setting host override is implicit.



## 5c) Region pack
<!-- PRD_ANCHOR: REGION-PACK -->

A pack is the detachable knowledge of a place or of a language: true for any
family from there and empty of every family. Packs are what families can share.
The working detail of each file is in `regions/CONTRACT.md`.

**Questions a pack answers** (driven by roles and skills, not by files):

Host wording also declares supported address forms, date templates and month
names, and integer plural categories in `host_format`. English, Polish and
Russian use the same engine path; missing host resources produce an explicit
pack gap, never a fallback language on this host-text surface. Separate built-in
word fallbacks exist in `desk.words` and table intake (bundled ru/pl/en); the
reader intake also uses bundled English for the initial unmapped English instance.
These defaults do not supply a region pack or its source recipes.
Language-specific limits (such as vocative
forms) remain declared gaps rather than inferred family facts.

| # | Question | Kind | File |
|---|---|---|---|
| Q1 | Which sources exist for this place and years, what does each cover? | data | `sources.toml` |
| Q2 | How is a source reached: open, host sign-in, request, paid; which recipe? | data, recipe id | `sources.toml`, `recipes/` |
| Q3 | How does a source read a zero; how much of its catalogue is indexed? | data | `sources.toml` |
| Q4 | Who keeps a record of this class and year now, who may ask, how long closed? | data | `custody.toml` |
| Q5 | Which fields did a certificate carry in each decade? | data | `custody.toml` |
| Q6 | Calendar, border, administration and language of records in a year | data | `chronology.toml` |
| Q7 | Forms of names, surnames and places in each alphabet and period | data | `variants.toml` |
| Q8 | Daily life of a place and decade for drawings and text | text by question | `reference/` |
| Q9 | Numbered questions of engine skills (RP-1 ...) | text by question | `answers.md` |

- **Kinds of content.** Data is read by code and agents; text for an agent is
  read by question, never whole; a recipe is read by a search tool. A recipe
  needs a source record; a source without a recipe is normal.
- **Status of every claim:** `verified` (seen on `checked`, with `basis`),
  `reported` (secondary, not rechecked), `unverified` (general knowledge or a
  candidate; never the ground of a letter or a "not found"). A verified claim
  older than a year reads as reported.
- **Unknown source years:** `years=[]` retains a candidate with «годы неизвестны»
  in a year-filtered answer and requires a gap naming its id and the missing
  coverage. Mixed cards with outside observations are reported, with dates
  and observers in their basis.
- **Gaps are declared** in `pack.toml` `[[gap]]`; a missing file never reads as
  "nothing exists". A skill whose question the pack cannot answer reports the
  gap to the pack, not into its text.
- **Never in a pack:** a person, family, case, version, decision, a family's
  search or its coverage; family-only ids, paths, file-level archive
  references; a village chosen because a family lived there; ranking of
  sources by value for one family. A family's correction is a proposal to the
  pack's keeper. Loading checks identity, kind, confined file paths and unique
  source ids; the keeper reviews schemas, family neutrality, historical claims
  and rights. The source-class vocabulary lives in `regions/CONTRACT.md`.
- **Pace is not a pack value.** A source states what the site publishes; the
  host's shared ledger sets the pace for all families of one host.
- **Two kinds, one mechanism.** `pack.kind` is `region` or `language`. A region
  pack names the languages of its records (`record_languages`); a language pack
  holds gendered and case forms of surnames, transliteration, word lists of the
  voice checks and words of faith and daily life. Region packs are an ordered
  list (later wins on settings; a source id repeated across packs is a load
  error); language packs are keyed by tag, one per tag, and apply only to text
  in their language. A question is answered by the region pack whose countries
  and years cover it; answers are never merged.
- **Where packs live.** In this repository under `regions/`, or anywhere the
  host maps a pack id to a path; the family names packs, the host resolves them.

Pack resolution precedence is host mapping (`FAMILIAR_HOST_PACKS`, a JSON
object of id to absolute path), then bundled id under `regions/` (also shipped
in the wheel), then an existing confined family-relative path. Host overrides
are explicit; symlinks cannot escape the family boundary. `instance paths`
reports the resolved pack file and origin. Historical local region layers with
no passport remain region layers; an explicit wrong `pack.kind` is rejected.
`language_packs = { en = "example-language" }` selects one pack for each tag.
A language pack has `[pack] kind = "language"`, optional settings/modes and
`[language]` data (inline `lexicon`, surname forms and transliteration tables).
`Registry.language_data(scope)` returns that data only for the selected tag.
The old `lang.lexicon` file setting remains deprecated for compatibility;
new packs use inline language data, never a path to a family's lexicon.

A scope may append `/language:en` to an existing feed/chapter/item scope,
or be `language:en` alone. Exact tags match; no implicit language fallback.
Unqualified scopes keep their previous results. Language base and feed layers
precede their region counterparts, then family. `lang.preferred_terms` and
`names.gendered_surnames` now admit language rather than region assignments.
A feed's source and each translation pass their own language in the scope.

`familiar pack ask RP-1 --country BY --year 1950` returns one answer from the
last region pack covering country and year, without merging packs. Missing
coverage and missing answers are explicit; declared gaps accompany the latter.
Data catalogues have a budget of 100 array-table records and 2000 lines;
code and prose retain the 400-line warning.

## 6) Trust core
<!-- PRD_ANCHOR: TRUST -->

Twelve invariants. They are the only rules that are never a setting.

1. A document is never invented: no paper, no reference to a missing one, no
   drawing made to look like a record.
2. Cut-out, caption and text agree; the reading is literal; doubt is marked.
3. A scene without a document names what it stands on and how strongly.
4. Identity and kinship are versions with weights; a weak version is never
   written into a card as accepted. Nationality is not inferred.
5. "Not found" always states what was actually covered.
6. Nothing is invented about the living. About a living person only what that
   person allowed is told; without a recorded permission that is name and
   kinship. Their documents and addresses are not shown; photos of children
   and the living never go to an image generator.
7. Closed family topics and present-day politics stay out (lists are family
   data, the mechanism is engine).
8. A reconstruction is called a reconstruction: a drawing is neither a portrait
   nor a document; colourisation adds no detail.
9. No person in a frame who was not there; the unusual only by source.
10. Period images carry a source and an open licence; documents are stored
    locally, never hot-linked.
11. The host publishes. Strangers see demo mode.
12. No people, faith or neighbourhood is blamed as a group: what a document
    attributes to an authority or to named persons is told as theirs. (How
    hardship is framed beyond that is a setting.)

## 7) Rules and settings
<!-- PRD_ANCHOR: SETTINGS -->

The pilot grew 116 rules in 24 days; 62 came from a single remark each. The
system below replaces "a thousand knobs" with four kinds and one cascade.

| Kind | Lives in | Enforced by | Configurable |
|---|---|---|---|
| **trust** | trust core (above) | engine check where mechanical, strong review otherwise | no |
| **craft** | the rule catalog, delivered to the role it serves by command | advice; never blocks | the role may deviate with one line of reason |
| **taste** | a declared setting with a default | check in mode `block`, `advise` or `off` | yes: region, family, feed |
| **process** | the pipeline and role sheets | pipeline state | by the host environment |

- **One registry of settings.** Each has an id, the layer that owns it, a
  default, and the use case it serves. An undeclared setting does not exist.
- **Family address.** `host.address` is `formal` (default) or `informal`, scoped
  to language or family. The source-language pack supplies the corresponding
  wording; unsupported forms are reported as a pack gap. Set it as
  `"host.address" = "informal"` under the family's `[settings]` table.
- **Cascade:** engine default → region pack → family → feed → single exception
  with a reason. The default for a new family is `advise`.
- **Exceptions are first-class.** One command records "this rule does not apply
  here, because…". Three exceptions to one rule mean the check is wrong.
- **Where a remark lands.** A host remark is classified first: trust → rule and
  check now; craft → a line in a role sheet; taste → a setting of that family.
  Craft becomes a rule only after it repeats.
- **A check serves the story.** Core data, privacy and installation guarantees
  carry weights in `src/familiar/check-weights.json`; only these and the single
  installed journey block. Text, style and editorial-completeness lint is removed.
  Existing `text-review` exceptions remain readable and cannot suppress core data
  findings or replace independent reading. `feed check --text FILE` explains that
  prose is accepted manually; it certifies neither data nor publication readiness.

### Data model
<!-- PRD_ANCHOR: RULES-MODEL -->

Rules and settings are data. Engine files live in `method/rules/`.

**Rule** (`trust.toml`, `catalog.toml`):

| Field | Meaning |
|---|---|
| `id` | stable, e.g. `TRUST-04`, `TASTE-NUMBERS` |
| `kind` | `trust`, `craft`, `taste`, `process` |
| `statement` | one or two sentences an agent can act on |
| `roles` | the roles it is delivered to |
| `serves` | the use case it protects |
| `check` | `check:<id>` for a mechanical check, `review:<role>` for a judgement, empty for advice; a list when a rule has both |
| `mode` | default mode: `block`, `advise` or `off` |
| `reads` | ids of the settings its check or its wording depends on |

**Setting** (`settings.toml`): `id` (dotted, e.g. `reader.default_age`),
`type`, `default`, `help`, `serves`, `scopes` (which layers may set it:
`language`, `region`, `family`, `feed`). Optional `choices` closes the list of
values; `item_choices` closes the list of items of an array.

**Layer file** (a region's `pack.toml`, a family's `familiar.toml`): a
`[settings]` table of values, a `[modes]` table of rule modes, and the same two
tables per feed under `[feed.<id>]`.

**Exception** (`exceptions.toml` of the family): `rule`, `scope` (feed,
chapter or item), `reason`, `date`, `by`.

What the kinds allow:

| Kind | Modes a layer may set | Notes |
|---|---|---|
| trust | none | always enforced; loading a layer that touches it is an error |
| craft | `advise`, `off` | never blocks; a role deviates by recording a reason |
| taste | `block`, `advise`, `off` | engine default for a new family is `advise` |
| process | `block`, `advise`, `off` | set by the family or the host environment |

Resolution always returns the value together with the layer that decided it.
A layer that names an undeclared setting or rule fails to load. Commands:
`familiar rules check`, `familiar rules for <role>`, `familiar rules explain
<id>`, `familiar rules waive`, `familiar rules report`.

Implementation conventions (rules core):

- `region_packs = ["id-or-path", ...]` in `familiar.toml` names directories containing
  `pack.toml` or pack files; paths must stay inside the family root unless host-mapped. Later packs
  win. Base region layers precede family; all feed overrides follow base layers
  (region feeds first, family feeds last).
- Dotted setting IDs are literal TOML keys: `[settings]` then `"voice.depth" = 2`.
  Registry table keys supply `id`; an explicit `id` must agree. Supported types:
  `string`, `integer`, `float`, `boolean`, `array`, `table` (strict, including bool
  versus int); optional `choices` restricts values.
- Exceptions are `[[exception]]` records. Scopes are `feed:<id>`,
  `feed:<id>/chapter:<n>` or `feed:<id>/item:<id>`. A waiver sets mode `off`
  for that scope and descendants; more specific scopes win, then later records.
  A nonblank reason, date and author are mandatory. CLI fills the date; the author is
  `host` unless `--by` names a role or an agent (never an OS account name). Trust always has engine mode `block`.
- Process modes may be set only in the family base layer. Setting `scopes`
  independently controls which layers may supply its values.
- `rules explain <id> --scope ...` returns the matching assignment chain and
  winner. Python `Registry(engine, root=None)` exposes
  `resolve_setting(id, scope=None)` and `rule_mode(id, scope=None)`; each returns
  `Resolution(value, layer, chain)`. Construction validates every feed, including
  feeds other than the one being resolved. `rules --engine <directory>` allows
  an explicit engine-data directory. Installed wheels include method resources.
  Numeric settings declare inclusive `minimum` and `maximum` in the registry;
  defaults and every layer obey them. Exception reports resolve `rules.exception_alarm`.
  Delivered JSON includes `check` and `serves`; text names each enforcer.

## 8) Roles
<!-- PRD_ANCHOR: ROLES -->

`src/familiar/rules/roles.py::ROLES` is the single declared registry consumed by
rule loading and delivery. Sheet stems and registry ids must match
exactly; unknown rule or reviewing roles fail loading. Packaging bundles the
whole `method/` tree as `familiar/_method`; checkout discovery uses the same layout.

`familiar method list`, `familiar method show role <id>` and
`familiar method show skill <id>` expose these installed resources by closed
identifier, never by an arbitrary path. They neither discover a family nor run
its startup maintenance, even with `--root` or `FAMILIAR_ROOT` present. Rules
remain family-scoped: `familiar --root <explicit-root> rules for <role>`.
`agent-skill/familiar/SKILL.md` is the thin portable Agent Skills entry for
0.3.x; it routes to the installed method rather than copying it. The host
chooses the family and retains source access, sending and publication.
The entry skill uses engine commands for family writes and reports missing
write operations; it supplies neither an installer, a plugin loader nor MCP.

Nine roles. Each has one entry sheet (target 6 KB), a "do not open" list, and
receives the rules that apply to it by command, not by reading a book. Target
context before work: 30 KB, 40 KB for the feed author.

| Role | Id | Delivers |
|---|---|---|
| Lead | `lead` | portfolio, budgets, briefs, acceptance |
| Researcher (case, scene support, generation review) | `researcher` | links, versions with weights |
| Second look (reader, refuter) | `second-look` | corrected reading, objections by strength |
| Recipe searcher | `recipe-searcher` | coverage tables from known sources |
| Feed author (scenario, text, game) | `feed-author` | chapters |
| Shot director | `shot-director` | shot cards |
| Artist | `artist` | drawings |
| Reviewer (blind check, page reading) | `reviewer` | findings per page or picture |
| Translator | `translator` | translations that follow the primary language |

The id is the name of the role's sheet in `method/roles/`, the value used in a
rule's `roles`, and the argument of `familiar rules for <role>`.

The pilot's `blind-check` skill is the reference shape for an entry sheet.

## 9) Pipeline and research starts
<!-- PRD_ANCHOR: PIPELINE -->

Stages: intake → research → versions → scenario → text → shot card → drawing →
blind check → reading → translation → connect. Connect is a step of the pipeline run by an engine command, not a role. State is data: each stage
records what it was built from, so a changed input marks its dependants stale.

Research has two starts, chosen by what the family has:

- **parish-first** — a deep tree and a rural parish with continuous registers:
  read the parish, measure the local norm, find the anomaly, tell the scene.
- **memory-first** — living memory of people born in the twentieth century,
  often in a large city with closed registers: home papers first, witnesses
  asked with our version in the question, then cemeteries, award and military
  files, address books, obituaries, civil-registry requests by a relative.

The level of a story follows the evidence: card, story page, feed. A family
line with no document about its own people is not yet a feed.

## 10) Features
<!-- PRD_ANCHOR: FEATURES -->

State: `pilot` — works in the pilot instance, not extracted; `planned`;
`extracted` — lives here with a contract and a test.

| ID | Feature | State |
|---|---|---|
| FEAT-TRUST | Trust core with engine checks | extracted (mechanical checks plus explicit review limits) |
| FEAT-SETTINGS | Settings registry, cascade, exceptions | extracted (bounded installed slice) |
| FEAT-ROLES | Role entry sheets and per-role rule delivery | extracted (nine sheets and rule delivery) |
| FEAT-PIPELINE | Feed pipeline with fingerprints and next step | extracted (fingerprints and stage marks) |
| FEAT-BUILD | Feed build and reader app | extracted (installed catalogues, checked reader and packaged shell) |
| FEAT-START-PARISH | Parish-first research | pilot |
| FEAT-START-MEMORY | Memory-first research | extracted (installed intake and method) |
| FEAT-INSTANCE | Family root: one config for tree, feeds, media, export, port | extracted (bounded installed slice) |
| FEAT-INTAKE | GEDCOM and paper intake with a loss report | extracted (bounded installed slice) |
| FEAT-TREE | Family graph: snapshot, evidence, contributions and identity decisions become one graph with provenance | extracted (bounded installed slice) |
| FEAT-REGION | Region pack contract and first pack | extracted (contract, sources, custody, chronology, answers; recipes, variants and reference queued) |
| FEAT-LANGUAGE-PACK | Language pack: surname forms, transliteration, word lists, words of faith | extracted (bounded installed slice) |
| FEAT-DEMO | Fictional family, zero to first chapter | extracted (bounded installed slice) |
| FEAT-BOUNDARY | Layer map and validator | pilot (narrow) |
| FEAT-FACE | Name, voice, "how it works" page | pilot (media only) |

## 11) Definition of Done
<!-- PRD_ANCHOR: DOD -->

Engine acceptance follows the weighted core guarantees and single installed
journey in `docs/why-layer.md` section 9. Form/surface lint is removed; timing
advises, test size blocks. Optional WHY diagnostics preserve explicit links.


- **Extraction.** A piece moves here only when a second consumer needs it. It
  arrives with a module contract, a Why Graph node, and a fictional-data path
  through it in a journey or gate test. No names, ids, paths or decisions of any real family.
- **Cold start.** A strong agent with only this repository and the fictional
  family reaches a first chapter without the host's chat history, on one
  subscription.
- **Roles.** Entry context is measured, not promised.
- **Trust.** Each of the twelve invariants names its check or its reviewer.
- **Settings.** No check reads a value that the registry does not declare.

## 12) Not in scope

- A hosted service, accounts, a shared platform of records.
- Paid sources as a default path: they are listed as options.
- Bypassing site protection of any kind.
- Rules written in advance for regions nobody is researching.

## 13) Plan
<!-- PRD_ANCHOR: PLAN -->

The pilot instance keeps working throughout: Familiar grows by extraction, not
by rewrite. Stages follow real work.

| Stage | Driven by | Lands here |
|---|---|---|
| 0. Order | the pilot's own friction | trust core, settings registry, role sheets |
| 1. Memory-first start | two hard family lines in the pilot | the skill, the source classes, the story levels |
| 2. Family root | a second family | instance contract, intake, build and app that read it |
| 3. Region pack | that family's region | pack contract, first pack split out |
| 4. Fictional family | cold-start exam | demo data, "start a new family" for agents |
| 5. Opening | the author's decision | licence, public entry, pricing by subscription |

Open design questions (decided when the first real case needs them):

- **Language is not region**: decided, see the region pack section (one
  mechanism, two kinds of pack); the language layer of the cascade is implemented.
- **Readiness for a full cycle** checks normalized forms and references; it
  does not certify historical truth or visual quality.

Own engine code, method and pack texts use MIT; third-party resources retain
their notices. Open decisions for the author: whether the name is free to use
publicly; when the repository becomes visible.

<!-- PRD_ANCHOR: PRINT-BOOK -->
### Print book

`reader book --output EMPTY-DIR` delivers one self-contained HTML book, local
images and `book.css`, with no runtime dependencies or external resources.
It preserves feed/chapter order, cover and contents, document placement and
original readings, and chapter-end grounds and versions. Full text is default;
`--kids`, `--language`, `--page-size A5|A4` and `--host-private` select the same
reader layers and privacy projection. Independent reading must match the current
reader units and safety inputs; pipeline marks and host releases do not qualify.
Unaccepted/changed chapters are excluded and counted with reasons. The public
mode retains the full family gate; the local family book never authorizes upload.
The reader's current translation rule applies: retain stale translations until
replacement and report stale/missing units, with its existing en/ru fallback.
Interaction prompts, games, sound, video and outbound links are omitted.
The replaceable stylesheet defines A5/A4 pages, binding margins, chapter page
breaks, crop/caption grouping and CSS page counters; browser support is verified
by the host's PDF print, not guaranteed for every browser. There is no new tree
layout. Details, semantic classes and the static-copy boundary: `docs/reader-export.md#offline-print-book`.

## Installed slice and enforcement boundaries (14 November 2026)

An installed engine can ingest attributed memory and papers, build an evidence
graph, recover research packets, validate forms and trust, and build JSON story
catalogues. The wheel includes the portable reader shell: export/verify and
loopback serve show a tree and chapters without Node or a pilot checkout.
The agent authors chapters; `feed build` materializes catalogues, while reader
export/serve provides the rendered reading surface. Canonical forms ship with
`research form NAME` (see README); cropping uses the images extra. Local desk
build/serve need host authorization and valid family data, not AWS.

The output writer owns the trust boundary: ordinary builds refuse mechanical
blocking findings before creating output. Historical and visual review remain
human/agent work. Acceptance is shared across versions, contributions and chapter
facts: accepted requires a strong status, sources, basis and an auditable decision.
The privacy checker examines declared published fields, not stored private dates;
subject completeness in prose requires review. Approval dependencies include
permission and restricted-vocabulary contents. Research packets preserve graph
contribution locators; owner decisions are staged separately from primary inputs.
Zero-read observations can be recorded as access-gap, never as negative evidence.

<!-- PRD_ANCHOR: SOURCE-SEARCH -->
### Bounded source search and host access

Research consumes recipes and period-filtered general forms from the family's
resolved region packs; `family/variants.json` adds family-only forms using the
same `variant` array shape. Candidate comparisons count explicit independent
dependency groups: one is possible, two probable; neither accepts identity.
These are search suggestions, not documentary assertions.

The host interface has three operations: `authorize(family_id, source, url)`
returns a permission token or denies; `fetch(token, url)` returns one bounded
capture (`status`, `html`, `text`, `responses` URL/post/body triples);
`report(token, outcome)` records completion or failure. Denial invokes no
transport. Sessions, secrets, waiting, challenge handling, shared source budgets
and cross-family accounting belong to the host. `PilotGateHost` injects its
existing Gate and browser transport; callers must not wrap an already gated
transport a second time. `SingleFamilyHost` needs explicit opt-in and serves
one family without shared accounting; it is unsuitable for concurrent families.

`research.source_search.search` resolves one region recipe, checks its HTTP(S)
URL and obtains explicit host authorization before reading the capture.
It validates the captured coverage, then stages an exclusive search record
through the writer: record forms, numeric domains and references are checked
before commit, independently of unrelated unfinished family drafts. Invalid
records are rolled back; this is not whole-family publication approval.
It records query/forms/years, returned/total/read, saved local record
locators, pack version and recipe id. Callers declare rows actually inspected;
capturing a page does not declare its documents read. A loaded zero is one read
index response (`unit=index-response`), never one document. Unloaded pages and
refusals are access gaps, never negative evidence. Challenges take precedence
over any JSON results. No retries or automatic pagination are implemented.

Four readers are available: Geneteka, Szukaj w Archiwach, Pamyat Naroda and
OBD Memorial. OBD has no verified empty signal; its shell remains not_ready.
The offline replay entry is `familiar --root ROOT research replay
--request request.json --capture capture.json --allow-replay`. Complete fictional
examples are available through `research form search-request` and `research form capture`.
`question` references a saved versions-file id (the matching `research form version`
example is `versions/birthplace.json`), not the question text or a family letter id.
For that Geneteka example declare `region_packs = ["belarus-podlasie"]` in
`familiar.toml`; a language pack supplies wording, not a recipe. Replay uses the same
gate and record path and never opens a network connection. Live transport is
provided by the host, not bundled in the engine.

`feed pages --text` and `family summary` distinguish accepted reader pages
from the separate feed view. They recompute the reader review against its current
bytes and safety inputs; a confirmed reader page is explicitly reported even
when the separate feed projection still needs reading. They do not transfer
attestations across different projections or permissions.

## Private narrator desk
<!-- PRD_ANCHOR: FAMILY-DESK -->

The owner's Correspondence page keeps prepared letters beside family questions.
`family/correspondence` (or `paths.correspondence`) stores recipient, channel
(`forum`, `archive`, `message`, `relative`), destination email/HTTP(S) URL, reply
URL, recipient language, literal text, person/question/request references and a
host or named relative as sender. States are `draft`, `ready`, `sent`, `answered`,
`closed`; sending records who and when. Replies preserve literal text, author,
date, origin, original UTF-8 bytes and the researcher's interpretation.
An interpretation is research advice; it never changes the tree automatically.
We add an optional form without changing existing stored forms or migrating data.

`research form correspondence` supplies a fictional example. Under
`family correspondence`, use `create FILE`, `update ID PATCH`, `sent ID --by NAME`,
`reply ID --text TEXT` (or `--file UTF8_FILE`) `--by NAME --source ORIGIN`,
`interpret ID --reply 1 --meaning TEXT`, `close ID`, or `--text` to list open work.
For a binary original, combine `--file FILE --text LITERAL_TRANSCRIPT`; we retain
the original and its digest, marking the supplied text as a transcript rather
than claiming that the engine read the file.
`--at` records a known sending/reply date; without it the current UTC time is used.
Updates change draft/ready letter fields; sent text and literal replies remain history.
Researchers receive `"host.correspondence_voice"` from the family's `[settings]`;
the default is neutral and polite. They review outgoing living-person prose with
the same rules as family letters: names and kinship only.

The phone page shows Send, Waiting for a reply and Replies in one column.
Copy preserves the complete prepared text; destination and reply links open the
host's own mail or website. Sent and reply actions use the existing feedback inbox.
Local receipt applies marks through the family writer; `desk fetch-feedback`
does the same for hosted feedback, retaining its signed login identity and raw
envelope. Retries do not duplicate replies. Researchers rebuild the desk after
interpretation; a hosted mark is pending locally until feedback is fetched.
Shared-login publication omits correspondence, its navigation and feedback data,
and refuses its actions: a shared password identifies no owner. Personal hosted
marks require an identified owner; loopback origin is explicit. Reader roles
cannot fetch this page or forge its actions; public demo exports omit correspondence. Familiar sends nothing and signs into no external service.

Personal AWS desks offer an owner-only Access page for issuing a tree-linked
login, resetting its password, enabling/disabling or deleting it. Each API call
verifies the signed owner cookie against current Cognito attributes and KVS.
Temporary passwords appear once, with a personal handoff cue; no invitations
are sent. They are plain on purpose — the login's letters and the person's
birth year (else the current year) — because relatives, often elderly, read
them off a message and type them; Cognito forces a new password at first
sign-in, and the pool asks only for six characters. Revocation matches the existing CLI; the current owner cannot change
their own login through the page. IAM grants only the desk's pool and KVS.

A narrator sees their family's personal reader, progress and questions locally
on loopback, or behind one shared login when optionally hosted on AWS, and
sends literal corrections back to the family instance.
This is a separate host-authorized delivery, not a public reader release:
ordinary living-person projection and independent reading requirements remain.
`family/desk-access.json` records host, recipient, decision date, reason, family,
the accepted personal-reader dataset (`dataset="accepted-family-reader"`)
and allowed desk pages. Updating accepted family material needs no new access
decision. Revoking
or changing it blocks the next build/publication; already delivered bytes must
be withdrawn or replaced by the host. Every HTML page labels the personal copy
with a quiet lower-edge “private version” label and the engine version, before
JavaScript runs. There is no upper private-copy banner.

`familiar desk build` only assembles a directory. It reuses, or re-seals when its
data dependencies change, a checked `reader export --host-private` generation from `[desk].source` (`.` by
default; its private display snapshot is independent of unrelated research drafts),
the packaged unmodified shell, and declared pages: `desk/journal/*.md`,
`desk/stories/*.md` linked as separate stories from progress, open cases'
thread/next step, `desk/plan.md`, and questions' witness question before our
version with a separate answer field. Absent journal/plan are stated honestly.
An optional `plan` path with `plan_format="search-table"` projects only the
topic and question columns of a research search plan, excluding internal bookkeeping.
Only selected fields are escaped into HTML; raw records, source files, bundle
internals, credentials and deployment state are not delivery resources.
The disposable directory defaults to `.secrets/desk-site`; output must be a
separate child of `.secrets`. Local build and serve neither read nor validate
publication settings, including unknown targets. They check the host decision,
family identity and selected inputs. `desk serve` without a build points to
`desk build` or `desk serve --build`; `--port 0` chooses a free loopback port
and Ctrl+C stops serving.

Local desk delivery verifies the build once, pins its bytes, checks file-set
metadata on requests and revalidates only when the build record changes; damaged
builds refuse delivery. Both local servers use persistent HTTP, long private
caching for hashed shell assets and conditional ETags for stable URLs.
Loopback-only listening also accepts `localhost` and `*.localhost` with matching
same-origin feedback (for example `http://family.localhost:8771/`). Local feedback
accepts consecutive messages without a ten-second pause.

`desk/show.json` projects the investigation as cumulative counters, source-type
volumes, every recorded alternative (including ruled-out ones with literal contrary
arguments), numeric weight histories and newest-first event pages of 24 rows.
Recent substantive shifts come first; git dates order events internally but no
date, clock, visit delta or speed enters this projection. Git history is read in
one log and one batch of version blobs; routine checks coalesce in ordered
portions of at most 60, independent of elapsed time. Commit subjects,
query text and internal paths are never delivered. Versions about people outside
the checked reader are omitted; living-person version details use generic labels.
The show also works without git or search history; absent volume data never
creates activity. A confirmed version counts as in the tree only when its
supporting source is present in the checked reader. Document readings count
saved archive/home records with fields or a literal reading; index hits and
pages are not documents. Unknown source types remain explicitly unknown.
This page is a derived display: researchers must read versions and search logs instead of treating it as family evidence.

The optional “Where we searched” block contains only counts: known/checked
sources, recorded attempts by ordinal working day, repeat passes on distinct
days and attempts by source category. Known sources combine connected region
`sources.toml` catalogues and sources encountered in the journal. Categories
come from existing catalogue classes: military, registers, census, trees,
repression, press and other; a multi-purpose source gets one category in that
order. Unknown sources are other. A small alias table in `desk/search_volume.py`
and unambiguous catalogue domains normalize common spellings only while counting.
This approximate display adds no collector step, form field, validation or
maintained family registry. No family details enter the block.

Growth means first journal appearance during the last three recorded working
days (or all recorded days if fewer), rather than an invented catalogue discovery
date. Undated attempts stay in totals and are excluded from day bars, growth and
repeat evidence. Access gaps remain attempts, never evidence of a searched
source's negative result. No journal attempts means no block, even with a known
region catalogue. Categories count attempts so their sum equals the total.

`desk serve [--build] [--port N]` serves that exact checked publication directory
on `127.0.0.1`, without login. The same relative feedback endpoints work locally
and when hosted: POST saves the literal message envelope; GET with `subject`
returns messages for that person or question. Local writes go through the family
writer into the immutable feedback inbox. `desk publish` without `--build`
uploads the reviewed bytes; serving never rebuilds unless explicitly requested.

The desk tree offers a labelled "add a relative" entry beside the tree, relation
buttons in the person card, a pointer from the remark sheet, glowing places in
builder mode, long press and context menu. One sheet adds one person with plain
fields (names, maiden name, birth, living or died, how it is known, a note);
only a name or a relation is required, and "add another" keeps the anchor. A
table path remains for many people at once. `add_person` feedback carries the
accepted `anchor`, `relation`, optional `place` address, the bounded
`new_person` strings and a readable `text` composed from them. Dashed pending cards survive browser reloads and
subsequent desk builds, never modifying the accepted graph. A small family gets
seven initial places; “I do not know” leaves a place open. `reviewed_pending`
ids in the show clear browser copies after the researcher reads the inbox.
Every screen (tree, families, person card, search, investigation and a full-screen
feed step) offers a quiet lower-right “Remark”. Desktop hover or click opens a
small card; phones use a bottom sheet. It reserves the lower edge without covering
tree controls, minimap or navigation. Drafts survive closing and browser reload.
An unnamed or incomplete name has a direct “Give a name” action (`name_person`).
Card corrections, new relatives and question answers use the same sender and inbox.

Every message includes `page` (path, query and anchor), `screen`, stable `person`,
`question`, `feed`, one-based `step`, actual `text_mode` (`kids` or `full`),
`language`, `selection` (at most 300 characters), `viewport`, `engine_version`,
`build` and client/server times. The human `where` line locates the visible place.
The opened form freezes that context, including for a recovered draft. Receipt
“Received” appears after the inbox acknowledges the id. Browser-owned ids list
only that reader's remarks: sent, read, addressed, with an explicit researcher reply.
`family/feedback/read/<id>.json` may contain `status="read"|"addressed"` and
`reply` (literal text to this reader); an older mark still means read. Other mark
fields stay internal. Local GET returns live receipts; hosted receipts enter
`desk/feedback.json` on the next build/publication.

The show counts questions, alternatives explored, ruled-out alternatives,
versions confirmed in the tree and remaining work. Every open question offers
feedback through the existing sender with its original safe question ID and
human title. The work log pages turn entirely in the browser over prepared
portions; all time fields stay out of the delivered data.

On phones the reader's tabs include the investigation; the reserved lower edge
holds the private label and remark entry. Ghost places are hidden. The addition sheet uses “Who would you like
to add?” with a separate literal “next to: name” caption. Wide-screen child
places are kept inside the visible tree area as its camera changes; a relocated
place gets no misleading wire through unrelated people.

`[publication]` selects optional publication: absence of the table or
`target="none"` means local-only work; explicit `target="aws"` chooses AWS.
There is no `local` target: local viewing needs no publication target.
Cloud commands (`provision`, `publish`, `fetch-feedback`, `verify`, `delete-stack`)
validate this selection before any disk mutation, startup maintenance or external
process. At `none` they explain local build/serve and the AWS configuration;
an unknown target names the two valid choices. Even `publish --build` refuses
before rebuilding. AWS uses region `eu-north-1`, an optional CLI profile, a
dedicated `familiar-*` stack and a family tag.
`desk provision` creates/updates one CloudFormation stack, saves generated
login/password and deployment coordinates only to ignored `.secrets/desk.txt`,
and tests anonymous 401 before any data upload. Missing AWS CLI or profile
is a safe actionable error. Failed provisioning may retain credentials and
stack identity for retry; other cloud commands name all missing deployment
fields and direct the host to `desk provision`. A discovered stack is never
adopted without matching saved identity; lost identity requires restoring its
private state backup. Stack operations use Express
mode with rollback disabled, so a failed resource can be fixed and retried.
Existing stack tags and its identity must match. `desk publish` checks the
recorded decision and built file manifest before uploading only that delivery
allowlist; it does not rebuild or rerun CloudFormation. `desk publish --build`
explicitly combines local rebuilding and publication for frequent development updates.
The template creates a
private encrypted S3 bucket, two origin access controls, a CloudFront Function
containing only a credential hash, CloudFront distribution/headers, and an
IAM-authenticated Lambda URL whose policy permits only that distribution.
All viewer behaviors authenticate before cache lookup; indexing is disallowed.
Static files cache on CloudFront for five minutes and browsers revalidate.
Publication syncs the built directory and requests `/*` invalidation without
waiting for it. Feedback is never cached. The default is a development desk:
short update cycles and retryable infrastructure, rather than availability machinery.
The AWS adapter is replaceable without changing local desk assembly.

The separate desk script handles navigation and the common sender; the shell
declares stable context and routes its existing actions there. Feedback carries exact text, page/person/question context,
client and server time and an idempotency id. JSON is limited to 20 KB and
text to 6000 characters; inbox ids are atomic and idempotent. Unknown fields and
nonempty string kinds are retained for compatible receiver evolution, with no
cooldown, captcha or new rate gate. The browser signs the request-body digest before CloudFront's origin
signing. `desk fetch-feedback` saves immutable raw JSON under
`family/feedback/inbox/`, retaining remote originals. Nothing is accepted into
memory automatically. `family next/summary` count unread inbox files (a matching
`family/feedback/read/<id>.json` marks a researcher-read item). Receivers deployed
before contextual remarks reject the new envelope: run `desk provision` to update
that owned stack before publishing a 0.8 desk. Assembly never deploys it.
Removal uses CloudFormation on this owned stack only; the bucket is deliberately
retained so feedback is not lost. A host separately removes only its retained
bucket after saving the inbox. No account-wide cleanup is part of this feature.
