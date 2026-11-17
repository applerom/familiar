# The family gate

Check weights live in `src/familiar/check-weights.json`. Only registered core
data/privacy/install findings block output. Presentation, text style, required
editorial completeness and service-locator spelling lint are removed; unknown
checks advise. A missing weight does not grant a new acceptance requirement.
The declared projection, living/document exclusions, source fidelity and
independent review binding remain core guarantees.
Tree contributions are adopted family inputs: a rejected package is a blocking
data finding in whole-instance and selected-file checks, naming its file, claim
and cause. Source ids resolve across contributions in the same family, including
mutual references. Packages remain atomic; no working graph or reader/desk output
can be delivered after any package fails to apply.
Person references use the working tree (snapshot plus applied contributions), including merged ids resolved to their successors; inspect ids with `tree build --view working` or `tree person ID`.
In host text an id leaks only when non-alphabetic, explicitly delimited as a reference, part of a path, or immediately qualified by an id/person/version/question/case/record/source type; we hide the reference with a notice and preserve the remaining prose.
Numeric calendar and folio notation (including Roman months, year ranges and slash years) is prose, never a working path.
An explicitly attributed cut-out uses its declared subjects, which must agree with its corpus record; only a cut-out without subjects inherits chapter people, while shared scans still accumulate protected gallery and source uses.
Privacy configuration stays strict. Invalid presentation preferences use engine
defaults without changing the stored family file; unknown nonprivacy preferences
and stale text-lexicon paths cannot stop display. Setting weights use the same
registry as findings, rather than creating a second set of gates.

What it promises, to whom, and how to extend it without opening a hole.
Read this before you add a form, a reader surface, an output or a check.

We report withheld chapter cut-outs, pictures and game evidence as private advice
in `feed check` and `feed pages --text`, separately for the local host and readers.
Advice names the item, protected subjects and life status, and the next action:
clarify life status or separate a deceased-only excerpt.
A living person’s full document remains excluded. Omission remains safe and
does not itself block a build; conflicting subjects still refuse it.

A `photo-treatment` is the same real photographic frame with colour or print
processing, distinct from a generated reconstruction. The original picture has
`ours` with `kind: photo-treatment`, its own `asset`, `caption` and `disclosure`;
we bind `orig`, subjects and corpus reference to the original. The original needs
a corpus record (`period-picture` or `document-scan`) or `family-photograph`
rights and explicit subjects. See `forms/photo-treatment.json`; install the
`images` extra for dimension checks. Both frames must have the same pixel size.
Dimensions do not establish that facial features stayed unchanged: the author
and reader must verify that claim. No face transplant or blending is permitted.
Captions identify the real original; the processed caption discloses the changes,
and the reader opens the original through the existing pair control. A treatment
inherits original privacy: deceased subjects follow the original's display rules;
living or unknown subjects remain in the family display and are excluded
from public reader exports. Protected
documents remain excluded in both views. Existing stored forms are unchanged.

A `photo-restoration` generates a sharp photograph from an existing real frame,
only when every original subject is known dead. Living or unknown subjects are
refused even in the local host display, in every display. It never supplies
a document, source, cut-out or game evidence. The original retains its own rights
and privacy rules, and is one tap away in both the chapter and person card.
See `forms/photo-restoration.json`: put the restoration under the original's
`ours`, assign its stable `id`, list `versions`, and choose a `primary` version id.
All saved variants are available to readers; the selected primary opens first.
Each version has its own asset, caption, disclosure and `recipe`: positive version
number, exact model revision, ISO run date, literal prompt (or a durable local
reference), invented details, original/output SHA-256 and numeric comparison
measurements. `comparison` records attempts, chosen attempt, reduced width in
pixels, blur radius in pixels and mean absolute error (0–255 intensity scale).
These numbers describe the comparison; they do not certify facial identity.
Optional `crop` is `[left, top, width, height]` in original pixels, excluding a
printed caption. Output size may differ; aspect ratio must stay within 2% of that
crop. Install the `images` extra. Replace example hashes with actual file hashes.
Family writer transactions preserve every saved version; append a new version
and asset instead of editing or deleting the old one. Bound hashes also reject
changed original/output bytes during display. Direct manual edits to family JSON
have no independent historical baseline: retain old files and recipes yourself.
`familiar --root FAMILY feed restorations` lists all authored versions and recipes,
including model, date and age in days, for future regeneration in the host's
environment. The engine does not invoke an image model. Existing forms need no
carry-over; `photo-treatment` still forbids generation and requires equal sizes.

Collector captures and unreferenced original, import and media archive bytes are
research working material, outside the snapshot and input watch; only declared
file references, import JSON and the media manifest select them. Cleanup remains
the host's responsibility; adopted-input validation and race checks remain intact.

Collector records and search journals are working research: their form findings
appear separately in whole-instance checks and remain strict under `--path`,
without blocking display or release. Exact references from authored tree, memory,
feeds, cases or versions adopt their research dependencies recursively; those
records and journals must validate and remain stable throughout every output build.

The reader card dictionary in PRD FORMS declares compound name, confirmation,
retired-fact and card-status surfaces. Family display includes them for everyone.
Public output requires a known-dead owner and known-dead relationship endpoints.
Stored public generations track these uses, so a new living/unknown assessment
requires removing them before consumption.

Private display scopes are a local delivery policy, never a narrower public
verdict. They copy mutable forms and only referenced corpus records/captures,
with declared media and original files. Unrelated working research cannot
enter a local reader or change its input watch. Public adapters reset that
scope and retain the full gate for adopted family data. Immutable archive bytes may be linked
in scratch; staged mutations detach links, and publication still checks exact
input digests. Scratch leases permit cleanup only after a day and confirmed
owner-process exit; old unmarked system-temp copies are outside auto-cleanup.

## Whom it protects, and from what

The gate protects a family's readers and its living members from **honest
mistakes**: an agent that mislabels a picture, forgets a subject, copies an
example, marks a weak version accepted; an import that brings addresses,
undeclared private fields; a life assessment changed after a build; two
agents working at once.

It is not a security boundary against:

- **the host**, who publishes (TRUST-11) and can show anything outside the
  engine. The gate labels what it hands over truthfully; it does not police the
  owner;
- **engine code written to evade it** (forged capabilities, monkeypatching).
  That is engine review, not a runtime guarantee;
- **a compromised agent or process** on the host's machine. Sandboxing and
  network policy belong to the host environment.

Family agents edit family files with their own tools. The engine is therefore
not the only writer of a family, and cannot be. The hard boundary is where data
**leaves** the family, not where it is written.

## Two classes of guarantee

The test that sorts every rule: *can two honest, careful readers disagree on
whether this item breaks it?* No: class F. Yes: class R.

### Class F: properties of data and its form. Enforced without exception

A class-F rule is decided by the engine from ids, types, links, flags and
numbers. It has no waiver, no mode and no "review" outcome. Any route by which
an honest mistake gets past it is a defect of the gate.

| | Guarantee | Trust |
|---|---|---|
| F1 | Every shown document, record, picture, cover and person resolves to a local item by its exact canonical id. Ids are compared after NFC; case, spacing and mixed-script variants are unknown ids that fail, never fuzzy matches. | 01, 10 |
| F2 | **Subject closure.** The people an output shows are computed by the engine from structured links: chapter people, document and picture subjects, the explicit subjects of every record a document or a picture points to (including `document-scan` pictures), tree and clan members, covers, nested image variants, records behind tree sources. An author's list can add people, never remove them. | 06 |
| F3 | **Living projection.** Family display tells stories about everyone. Public output limits living and unknown people to name and kinship, without a consent widening path. In both modes, addresses and protected full documents are excluded; literal excerpts resolve their selected fields and recorded subjects independently. Real living/child photos never go to a generator; face restoration requires deceased subjects. | 06, 08 |
| F4 | **Acceptance.** An assertion shown as accepted has a strong status, a finite weight in its declared range, sources, a basis and a decision. Contradictory flags fail. A weak version is shown only as a version. | 04 |
| F5 | **Declared projection.** Every reader surface is declared and treated as literal Unicode text in NFC; rendering escapes text. A field without a declaration does not exist in output. Text-form lint does not refuse markup-like spellings, character references or typographic controls. | 02, 07 |
| F6 | **Disclosure form.** A generated reconstruction never occupies a portrait or document role; a `document-scan` names its record. | 08 |
| F7 | **Coverage form.** "Not found" carries typed coverage; zero read is an access gap, never negative evidence. | 05 |
| F8 | **Generations.** An output is built from one snapshot and committed atomically. Its manifest records, for every shown item, the people and fields it uses and its public exclusions, plus digests of the safety inputs (privacy, restriction lists, archive rights, life status). The checked reader refuses a generation whose uses are no longer permitted and names what must be removed. A change in any other input marks it *outdated*, not unsafe. | 06, 11 |
| F9 | No layer, feed or exception changes a trust rule's mode. | all |

### Class R: properties of meaning. The machine helps, a reader confirms

What prose, captions and translations *say*, and what an image *shows*, is
decided by reading. A machine check here is a proxy with both false negatives
(paraphrase, another language, an encoding) and false positives (a namesake,
a word in another sense). Made blocking, it produces holes and obstruction at
once. Class R covers:

- R1 what text says about living people (TRUST-06 in prose);
- R2 closed family topics and present-day politics (TRUST-07);
- R3 what an image shows: who is in the frame, text painted or drawn in it,
  whether a "period picture" is one (TRUST-08, 09);
- R4 scene support, literal reading beyond string equality, collective blame
  (TRUST-02, 03, 12); neutrality of a region pack (keeper review).

**What the machine does:** a worklist per page and picture: people in the
subject closure, people whose names occur in the text, restricted-term hits
after decoding and normalisation, unknown life status, names in a record dated
inside the living horizon that are not mapped to a person. A worklist entry
never blocks by itself; its blind spots are written next to the check.
Vocabulary/style cues have been removed from the engine. Saved text-review
exceptions remain readable for compatibility. `feed check --text FILE` explains
that prose is accepted manually and certifies no data guarantee. Core privacy
worklists and independent attestation remain unchanged.

**How class R is closed: an attestation bound to the shown bytes.** A reviewer
who is not the author of the page records: page or picture id, language, the
digest of exactly what the reader gets (text, children's text, captions,
translations, picture bytes), the rules attested, verdict, date, and the digest
of the safety inputs it was read against. A clean generation includes a page
only with a current attestation matching its bytes. The gate checks the
binding, never the judgement. When the shown bytes or the safety inputs change,
the attestation lapses and the page is unreviewed again. Edits elsewhere in the
family do not touch it.

The binding is itself class F: "every shown surface was in front of a reviewer,
in the exact bytes shown" is decided by digests, not by reading.

## Output states

- **clean**: class F holds and every page has a current attestation;
- **preview**: produced for work; labelled in its data; never taken by export;
- **outdated**: clean when built, safety inputs unchanged, other inputs moved;
- **withdrawn**: a use is no longer permitted; the reader refuses it and lists
  what to remove;
- **host release**: the host may release unreviewed pages (TRUST-11). The
  decision is recorded with the pages it names and stays in the manifest. A
  class-F failure cannot be released.

## Writing into a family

An entry point (intake, contribution, helper, approval) validates **the item it
stores**: its form, its own acceptance flags, its references. It refuses a
malformed item and reports. It never refuses because another part of the family
is blocked: a chapter draft with an unresolved reference must not stop a
relative's memory from being recorded. Hand edits are expected; the family
check reports them, and the output gate is where they matter.

`instance/writer.py` is the engine's only writer: confined paths, staged and
atomic writes, diagnostics in a state root disjoint from every input. This is a
discipline of engine code, not a trust guarantee.

## Extending

- **A form.** Declare every field: shape; policy `always`, `host-private`
  or `never`; and whether it carries person references. A person reference
  feeds the subject closure. A field that can carry an address is never
  `always`; event types are a closed list with an exclusion set.
- **A reader surface.** Declare it as text. It is plain, normalised, scanned
  and part of the attested page digest. Never an unrestricted object.
- **An output.** Only through `gate.publication`: projection, uses manifest,
  generation commit. Consumers read only through the checked reader.
- **A check.** Decide its class by the test above first. A class-F check is
  exhaustive and blocking and has one representative honest-error/control check per data guarantee.
  Other routes are reviewed; the suite is not an exhaustive proof of closure. A class-R check yields worklist entries only and states its
  blind spots.
- **A test** for a gate change shows one honest-mistake route failing the way it
  should, with a valid control beside it.

## Implemented boundary (12 November 2026)

`tree.builder.build(instance, enrich=callback)` supports instance presentation.
The callback mutates the snapshot graph in place before the single identity
pass. It must not write inputs. Its return value is ignored, and the resulting
graph still passes the ordinary living projection, declared-field scan, asset
checks and publication seal. It does not expose a raw pre-identity output.
`publication(..., tree_enrich=callback)` supports the same hook only for `tree`.
Undeclared presentation fields are omitted; this hook does not extend the
reader schema or certify compatibility with an external app.

`tree build` defaults to the private working tree; Python callers request
`build(instance, view='working')`. It retains the family's dates, places and
working fields and does not require unrelated drafts to be publishable.
`tree build --output DIR` writes `working-tree.json`, labelled `view: working`,
without a generation or clean verdict. `--view reader` and the existing Python
default select the checked projection. Unpermitted ordinary living fields are
omitted from reader output. Explicit documents and images still enforce the
unconditional exclusions and permissions, with the offending item identified.

The error routes and controls live in [gate-error-routes.md](gate-error-routes.md).

The read-only private `host` view supplies `family requests --text`, `family
summary`, `family next`, `family confirmation` and `feed pages --text`. It uses
an immutable snapshot, declared plain text and a final fingerprint check, but
is not reader publication: the writer refuses its working seal. The host sees
their own words and papers even beside unrelated publication failures. The family display tells stories about everyone; documents and addresses
remain excluded. It asks relatives about the past without requesting permission. Host story labels concern reading of those full source bytes.

For readers, narrative blocks are associated with canonical people through
chapter and feed `prose` links; unsplit text defaults to their declared people.
The family display includes every passage. Public output silently omits blocks
about living or unknown people, or uses an authored `otherwise` passage about
deceased people. Nested prose inherits chapter subjects unless declared separately.
No omissions are turned into permission requests.

Life assessments use one registered horizon (default 110) for all intake kinds.
Unknown is represented separately and is protected. Direct-generation estimates
never manufacture a birth event. Family decisions retain basis, author, date and
an explicit revocation flag; a positive living privacy declaration always wins.

A document `excerpt` selects exact literal record field keys with recorded
`field_subjects`. Missing assignments, substituted reading, scan assets and full
links refuse. Its subject closure and generation uses follow only selected
fields, and are rechecked on consumption. A full document retains all subjects
and cannot be cleared by an author's shorter list. A selected living subject
refuses in every display. Pixel crops are not certified by this text route.

The fast level has one honest-error/control check for each data guarantee F1-F9
and one for the mechanical review binding. The full level adds the single
installed-wheel journey: memory and a paper to independent reading, reader export
and checked consumption. Source demo replays, output baselines and structural
tripwires are not part of the suite. The route table states the exact retained
representatives; it does not claim every route has been exhaustively tested.

Prepare exact projected review material with
`familiar feed review ID --kind reader --out NEW_DIRECTORY`. Inspect the files,
then pass its `review-ticket.json` to `feed accept ... --ticket PATH`. The ticket
contains the kind, feed, languages, page byte digests and safety digest. A changed
selected page or safety input refuses confirmation; it never substitutes a fresh
build for what was read. Keep each review directory private and remove it when
the review is finished. It is preview material, never reader export.

For Python, keep the ticket with the exact `.files()` you read:

```python
from familiar.instance.gate import publication
from familiar.instance.review import attest, review_ticket
material = publication(instance, 'reader', for_review=True)
ticket = review_ticket(material)
# Inspect material.files(), including every selected language and media byte.
attest(instance, 'reader', reviewer='reviewer-id', author='author-id', ticket=ticket)
```

`feed accept ID --stage reading --reviewer REVIEWER --author AUTHOR --kind reader --ticket PATH`
records the same independent verdict; `--kind feeds` is the default. Reading
attests R1-R4; blind checks record R3 and do not close reading. Partial feed
reading can name `--pages`; the shell/introduction (`__feed__`) needs reading too.
`--languages TAG ...` narrows confirmation to the languages actually inspected.
The output names the selected scope; missing languages/pages remain preview.
Duplicate feed/chapter ids and reserved chapter ids fail before review units
are built; a duplicate unit key also fails rather than overwriting a digest.
Pre-ticket attestations require a new inspection: their old rows cannot silently
retain the new binding claim. Checked generations with those rows are withdrawn
with an inspection-ticket removal reason.
The host may explicitly record `host_release(instance, kind, by=host, pages=...)`;
this produces the separate `host release` state, never a waiver of class F.

Review unit bytes use deterministic compact UTF-8 page serialization (preserving
field and array order), every displayed language, and exact reachable media
SHA-256 digests. Reader document pages and profile have their own byte digests.
Whitespace in the surrounding JSON envelope is not displayed content. Method
and engine provenance and per-item/person/field uses are in `generation.json`.
Working notes and unshown corpus fields do not invalidate a page review.

Publishers take an exclusive per-destination lock before generation or pointer
changes. A second publisher receives "Publication in progress ... retry" and
can repeat after the first finishes. A lock left by a process/OS crash requires
host inspection and removal; automatic crash recovery is not claimed.
Generated-image/document exclusions and used-person life-status safety changes
are rechecked on every checked consumption, in every display.

Still deferred before further hardening: junction policy inside the root and
broader diagnostic-root overlap checks. The gate is an honest-error boundary; engine structural tripwires are
review aids, not a sandbox. The host must verify before handing a generation to
readers; external copies cannot be recalled by this local engine.
A research original that a private display only tests for existence (`local`,
`saved_result`, `original`, `image`, `scan` without a media row derived from
it) is a presence dependency: name, size and time bind it, the snapshot holds
an empty marker, and its bytes are never read.

Snapshots copy only declared fingerprinted family inputs and the review registry,
never unrelated root contents. Host-mapped roots and engine/host packs are read
in place: fingerprints before and after assembly reject changed dependencies,
so a mixed-input build cannot be returned or committed.
