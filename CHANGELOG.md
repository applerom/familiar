# Changelog

## 0.41.0 — 18 November 2026

- A family that already keeps an archive can move in. `docs/moving-in.md` tells
  an agent where people, kinship, notes, photographs, papers and finished
  stories go and how to count what was lost on the way. What the family's own
  archive holds as known arrives as firm family memory; only what that archive
  itself doubted stays a version.
- `intake photo` attaches a family photograph to the people on it, one file or
  a whole table at once. The received file is kept byte for byte; the picture
  stands on each person's card and on the Photos page.
- `intake gedcom --own` takes the family's own tree as the family's word, with
  solid lines. Without it a GEDCOM stays another tree's claims.
  A death read from a GEDCOM stays an imported claim in both modes, so whose
  tree it is never opens a possibly living person's papers.
- `instance init --language en` connects the English host wording by itself.
- `intake kinship-case` carries an ex-ussr-kinship-research case into Familiar:
  people, relationships with their standing, artifacts with scans, claims and
  the search log, so coverage knows where was already looked. A dry run comes
  first; `docs/moving-from-kinship-research.md` has the mapping.
- The tree steps one generation at a time again. The wheel and the round
  buttons add or drop exactly one generation of ancestors, one step per turn
  of the wheel, and the whole drawn tree refits the screen. A crowded row gets
  narrower tiles, down to an initial, instead of running off the edge. A click
  centres the tree on that person. This replaces the map-like zoom of 0.40.0.
- The tile tells the card's name: bracketed remarks of an old import are
  dropped, and a written surname the card no longer carries stays only as the
  known maiden name or the clan's adopted spelling.
- Home, not court: notices such as "documents exist but do not confirm the
  facts" are gone from the pages a family reads. Rule `CRAFT-HOME-NOT-COURT`
  asks every role to tell the leading version and stay silent where nothing is
  known.
- An explicit unknown life decision is honoured in the family display, and a
  card no longer cites a withheld paper of a protected person.
- Data: memory intake accepts JSON with notes and an archive original; photo
  intake stores gallery bindings with original and display hashes; kinship
  intake saves the complete case ZIP and maps its registers into working
  forms. Nothing already stored changes shape.

## 0.40.1 — 18 November 2026

- A cut-out keeps its own picture on the person's card; the whole sheet stands
  only for sources without one.

## 0.40.0 — 18 November 2026

- The tree zooms like a map: the wheel and the pinch only scale the picture
  under the pointer, and who stands in the centre changes by choosing a person.
  A couple is joined by a ring and their child hangs from it. Every tile shows
  a year, estimated when no record gives one; distant tiles open into the whole
  name when zoomed. The count sits in the corner map. The rays, the generation
  switch and the large add-relative entry are gone.
- A person's card tells the leading version. Versions weaker than 0.3 and their
  papers stay in the investigation; grounds, search coverage and retired claims
  share one fold at the end. Scans a source carries are shown as pictures.
- Relatives is a conversation, not a form: the tree comes first in the
  navigation, each ask names the person it is about, hints drop into one
  answer field, and the state buttons and counters are gone. An occasion never
  states an age.
- Show preserved scans and thumbnails on local document pages.
- Use a 75-year default for uncertain life status in the family reader
  (`privacy.family_years`); the public horizon stays `privacy.living_years`.

## 0.39.1 — 18 November 2026

- We show one tree count, keep sibling stacks as a visual cue, and leave out
  unknown parent tiles. The central couple and their children fit together.

## 0.39.0 — 18 November 2026

- The family tree keeps every person on a tile. Sibling stacks open in birth
  order, older generations recede towards the horizon, and missing parents
  have a place. The count opens family lists for people outside the canvas.
  Select a tile to read the person's card, then choose when to centre their family.

## 0.38.0 — 18 November 2026

- Relatives gathers conversation prompts by living witness, adds a mode for
  grandchildren and brings open asks into the family feed and tree. Answers
  marked private, including answers to tender asks, can stay in research memory.
- Data: Run `family ask migrate` to carry `family/questions` and old `relative`
  letters to `family/asks`, preserving question IDs, replies and original
  references. Rebuild the desk and provision its stack to receive the new
  feedback kinds in a hosted desk.

## 0.37.1 — 18 November 2026

- A letter whose question has only a weak leading answer now ranks as fully
  open: we know little there, so the letter can tell us most.

## 0.37.0 — 18 November 2026

- We show Documents by family line and person, rank ready letters by what they
  can establish, and set letters aside when their linked version is settled.
- Data: Run `family correspondence migrate-relatives` to move old relative
  letters and replies to family questions. External letters without an `aim`
  stay available under No aim.

## 0.36.3 — 18 November 2026

- We skip military sources outside a person's birth cohort and accept plain-text person notes in builds.

## 0.36.2 — 18 November 2026

- We recheck the chosen main lines and ancestors' siblings first, label the
  queue by line, and count living people and those of unknown status separately
  in the line fronts.

## 0.36.1 — 18 November 2026

- We follow weighted parent links from 0.30, show the ancestry chain by
  surname, match open questions to their line, and show the family's chosen
  main lines first in coverage and the desk.

## 0.36.0 — 18 November 2026

- We see each family line's farthest known ancestor, open parent versions and
  coverage gaps in `research coverage --lines` and the family desk. Read records
  can surface hints from collateral branches. When enabled, their descendants
  and spouses have their own coverage totals and follow the main recheck queue.

## 0.35.0 — 17 November 2026

- We turn correspondence into a mailbox: compact letter rows, status and recipient
  groups, an inline phone letter and a wide reading pane. Copy the destination,
  subject and text separately; people still send and record replies themselves.
- Letters accept optional `subject`, `priority` (`first`/`later`), `cost`
  (`free`/`paid`/`unknown`), `cost_note`, recipient `kind`, `how`, `relevance`
  and state `not_needed` through `family correspondence create` and `update`.
  Planning can change after sending while the sent text and replies stay literal.
  Postal destinations are copyable text. Existing letters need no migration.

## 0.34.0 — 17 November 2026

- We tell family stories about everyone, including living people and people whose
  life status is unknown. We remove permission letters and field-by-field consent.
  Family desks and private reader/book exports retain their stories and captions;
  public output gives outsiders only names and kinship. Document, address and
  image-generation exclusions remain.
- Data: Remove `allowed` and `consent` from each `privacy.json` `living[]` object,
  keeping `id` (or use the person ID as the entry). No carry-over command is needed:
  the removed fields are ignored; no family facts change.

## 0.33.1 — 17 November 2026

- We accept sourced spouse unions through contribution `families`, including a
  spouse added in the same package. Weight and basis reach the reader's existing
  lines: weights from 0.3 to below 0.5 are dashed, including probable links;
  weights of 0.5 and above are solid. Parent links remain separate `edges`.
- We let relatives' letters omit `destination` or use `null`. The correspondence
  page keeps the text and Copy action without an invented address or send link.
  Existing contributions, unions and letters keep their stored form.

## 0.33.0 — 17 November 2026

- We preserve each participant's life protection across identity merges. Existing
  disputed merges may now hide facts, crops and prose from public reader, demo and
  book output and refuse photo restoration. `instance check` advises which cards
  and death evidence conflict: record a reasoned `privacy.life_decisions` entry
  for the canonical person or undo the merge; correct death dates before birth.
  A death decision on an absorbed card alone cannot release the merged person.
- Books use a generic family-story title and report an omission when reader
  privacy removes the feed title. Host prose also retains Roman-month dates.
- We clarify that personal reader access grants the desk's accepted private
  family dataset, including living information except documents and addresses;
  service pages and correspondence stay owner-only and public output stays limited.
- We add deceased-only `photo-restoration` pairs: generated photographs with a
  one-tap real original, disclosed inventions, reader-selectable variants and
  append-only version recipes bound to both files. `feed restorations` lists
  recipes and their age for future regeneration; photo-treatment rules stay strict.
- We show a restored or treated photograph as a face with one caption, a quiet switch between
  variants named by the new optional version `label`, and one small line that opens how it was
  made: disclosure, invented details, model and date, comparison numbers and the recipe.
- A life line keeps a date span as a span ("≈1925 – 1941/45") in cards, tree, overview and feed
  reader chips; event lists show "1941–1945" instead of the first year alone.
- We keep an explicitly attributed cut-out with its corpus subjects instead of
  adding chapter participants; conflicting subjects refuse delivery and shared
  protected scans stay private. Withheld chapter media and game evidence now
  produce advice for the host and reader displays, also in plain-text pages.
- We preserve numeric historical dates, slash years and folio fractions in host prose.
- We pair real photographs with disclosed `photo-treatment` variants, binding the
  original, subjects and pixel dimensions. Living treatments require picture consent
  and remain local to the host; drawings keep their existing restrictions.
- We resolve person references against the working tree, including applied research
  contributions and explicit identity successors: records, versions, questions, letters,
  document cut-outs, privacy, search coverage, feeds and research packets use the same people.
- We let a contribution name an existing unnamed person with sourced name parts, retaining
  the earlier state in working history without adding and merging another card.
- We keep word-shaped identifiers in ordinary host prose. Explicit references and working
  locators are hidden with an explanation while the remaining text stays visible.
- A family question is addressed to a role (`host`, `relative`, `narrator`) or to one person
  of the working tree; any other addressee is refused with the known ids.
- Stored forms are unchanged. Existing unlinked records, contribution death events and
  identity-merge workarounds remain valid without edits.

## 0.32.0 — 17 November 2026

- We serialize family cloud commands, recheck personal entry immediately before upload, resume interrupted
  login transitions from non-data `.state` bookkeeping, and receipt inapplicable actions without blocking feedback.
- We keep agent-prepared correspondence beside family questions: recipient, sending and reply links,
  literal letters, named senders, sending history, original replies and researcher interpretations.
  The owner has a phone-first Correspondence page with copy, sent and reply actions through feedback.
  Agents prepare; people send. Shared-login publication omits correspondence pages, navigation and data
  and refuses its feedback actions; personal logins enable owner access. Reader roles and public reader
  demos cannot access correspondence. Local loopback desks remain owner workspaces.
- We withdraw correspondence and wait for CDN invalidation before switching to shared login, normalize
  protected paths, and retain unauthorized legacy actions without blocking feedback intake.
- Family commands create and update drafts, mark sending, preserve replies and their original files, interpret and close
  conversations. Researchers receive the family setting `host.correspondence_voice`, with a neutral
  polite default. Outgoing living-person details remain limited to names and kinship.
- A letter answered to the sender's own mailbox carries no follow-up address (`follow_up: null`); the page then
  says the reply returns to where it was sent from. The card labels whom the letter is about.
- This is a new optional stored form; there are no prior correspondence records to carry over.

## 0.31.3 — 17 November 2026

- We resolve sources across contributions in the same family, including mutual references, without
  depending on filename order. Rejected packages remain atomic and never reach a working tree, desk
  build or reader export. Whole-instance and selected-file checks now report their file, claim and cause.
- Hosts whose trees already omitted a contribution will now see a blocking `instance check` finding.
  Declare the missing source in a family contribution or evidence, or repair the named claim and rerun
  the check before rebuilding. Stored data forms are unchanged.
- Unknown references list known ids, including version people and record subjects.

## 0.31.2 — 17 November 2026

- We build the independently read Russian fictional family at `/ru/` alongside the English demo in one
  Pages run. Its public reader keeps the chapter, literal document excerpt and child question while
  excluding living-person prose. We corrected unsupported story details and an unconfirmed imported
  death on the tree; the original GEDCOM remains intact. Two Russian screenshots accompany the demo.
- Static demo export accepts `--public-reader` to wrap the accepted public projection. The English
  reader shell and accepted family inputs stay unchanged; language links appear throughout the Russian
  desk and on the English investigation pages. Builds use disposable family copies and never attest.
- We order contribution updates by recorded date and source ids rather than file modification times,
  so a clean archive on Linux preserves the reader bytes inspected on Windows.

## 0.31.1 — 17 November 2026

- The first-family tutorial and installed journey use one fictional Bea and Ben Example family, with
  deceased document subjects and non-word identifiers. The bundled inputs reach reader review without
  changing their meaning; the guide names files the agent authors and the commands that check them.
- Host-text refusals name the conflicting internal identifier and its declaration file, including
  collisions in input prose that previously disappeared silently. Stored family inputs are unchanged.

## 0.31.0 — 17 November 2026

- New method skill `on-site-researcher` and a researcher mode for it: when the open sources of a place are
  read and the needed book lies in a reading room, find a person who works in that archive through the
  regional forum, order by a unit, and take the returned photograph in as a paper with a reading of its
  own. The host posts, pays and sends; a helper's "nothing found" counts only with its coverage. The forum
  card of the Belarus and Podlasie pack describes the route as reported.
- README names the neighbouring open projects and where Familiar stands among them, and says that the
  maintainers also run research for families who ask.
- Documentation corrected after an independent cold walk: reading confirmations under `.state/` are not
  derivable and belong in the backup; a lost `.secrets/` is restored from the backup, not by a new
  provision; which inputs an agent writes as files and which only through commands; the fonts' licence
  beside MIT.

## 0.30.0 — 17 November 2026

First public release. Install tags, not `main`; see `docs/upgrading.md` for what a release promises.

- The place where a dead person lived stays in the family's pages. A residence was treated as an address:
  the event was dropped and its place name was removed from every text of the delivery, birth places and
  story sentences included. Explicit address events and every residence of a living or unknown person
  remain excluded as before. No stored data changes; rebuild the reader or desk.
- `desk export-demo` writes a fictional family's desk as a portable static site: relative links, the
  fiction mark on every page, feedback and adding people switched off. It refuses a family that is not
  declared fictional or whose reader pages are not confirmed. `scripts/build_demo_site.py` builds the
  Ferrolho demo this way; the build is checked on Windows and on Linux.
- The Ferrolho demo carries a recorded reading of its reader pages, so `reader export` works on a clean
  checkout.
- Documentation for outsiders: agent-first README, `docs/first-family.md` (installation from a tagged
  release), `docs/architecture.md` (engine, family instance, host environment; where each setting and
  secret lives), `docs/upgrading.md`, `CONTRIBUTING.md`, `SECURITY.md`. A changed stored form now ships
  its carry-over command and a changelog line starting `Data:`.

## 0.29.7 — 16 November 2026

- Coverage excludes analytical comparison tables and explicitly labelled source maps from personal record visits. Accepted tree facts and identity decisions resolve record links through exact document references; contextual participants remain separate from principal candidates.
- Local reviews (`query.mode = "review"`, including legacy `query.review`) assess individual record links without adding source passes, strength, forms, findings or availability. A completed assessment leaves incomplete search coverage open; contradictory accepted links remain conflicts. Search and record forms document the distinction.

## 0.29.6 — 16 November 2026

- A display snapshot no longer fails on a search journal row whose `question` names a version. A version citing `search:<id>` adopts the journal into the snapshot, but versions themselves stay out of it, so the reference is checked on the whole instance only.

## 0.29.5 — 16 November 2026

- Coverage puts unresolved record identity and participant roles before repeat searches. Explicit people survive dictionary mismatches; contrary birth/parent data and previous other-person assessments remain visible.
- Search forms carry editorial annotations, sex, person and episode applicability separately from spelling. Catalogue writing and prefix semantics constrain missing forms; unknown writing is marked explicitly. Estimated age and dated family episodes improve source priorities.
- Latest source refusal is independent of the strongest earlier outcome; a stopped search waits for access even when a document page opens. Dubious composite or substring queries cannot become negative coverage.
- Version arguments against a hypothesis may cite a saved zero with positive control and actual read scope; uncontrolled zeros and access gaps remain unusable.

## 0.29.4 — 16 November 2026

- The private desk rebuilds the "Where we looked" block when search journals, records, versions or the family variant dictionary change. The reader cache key covered only the display snapshot, which holds no journals, so a fresh recheck kept the old strength on the desk.

## 0.29.3 — 16 November 2026

- Memory intake drops a bridge label (`placeholder`) from an existing person once a told name arrives. The reader showed the label instead of the name and treated the person as unnamed: no search hit, no chip, no kinship path.

## 0.29.2 — 16 November 2026

- Coverage distinguishes surname searches in a place and period, individual searches, result rows, read records and explicitly established identity. Existing records and corpus records count as source visits without promoting name matches to identity.
- Planning reads dated family notes, catalogue parish/episode context and source language/script constraints. Textual positive controls survive; missing forms and incomplete plans remain visible independently of executor strength.
- FamilySearch Tree, Records and Full Text have separate coverage cells; ambiguous old labels remain unclassified. Private person cards show result rows and identity separately, with a short list of missing forms and the full list in JSON.

## 0.29.1 — 16 November 2026

- Legacy search imports assign stable provenance ids, normalize explicit counts and preserve unrecorded outcomes and incomplete zeros without claiming negative evidence.
- Coverage includes pack/family surname and given-name variants and query masks; living or possibly living people leave the recheck queue and are counted separately. Source URLs resolve by catalogue domain, transport labels without a source are counted aside.
- Expanded the Belarus–Podlasie source catalogue with forums, memory, diaspora, cemetery and library resources, keeping unknown dates and access gaps explicit.

## 0.29.0 — 16 November 2026

- Host-private reader: the person panel has a "Where we looked" section (ru, pl, en, sv)
  from the search coverage matrix. A folded line ("Looked in 12 sources · found in 3 · worth another look: 2"),
  then each source with its outcome mark (found, zero with control, zero without control, no access),
  the latest pass date, strength in dots and the name forms tried; "Not looked in yet" lists only sources
  that fit the person's epoch and region. The block is declared host-private only and never reaches the
  public projection; without a journal the section is simply absent.
- `research coverage --family --json` carries each person's `distance` from the tree root, so a display can order
  rows by closeness.

## 0.28.1 — 16 November 2026

- Search migration accepts an explicit executor map, enriches previously migrated
  rows, and refines question-only people using names and variants.
- Archived SEARCHES journals are copied with source line provenance, deduplicated
  across archives and repeat runs; malformed rows are counted without changing originals.
- Coverage suggestions account for catalogue epoch and geography, counting
  unsuitable cells separately while retaining the searches actually recorded.

## 0.28.0 — 16 November 2026

- Search coverage ledger. A search journal row now names the people it was run
  for (`people`, tree ids), a source of the region catalogue (`source`) and the
  executor as `by` = `{agent, model, effort}`. `familiar research
  migrate-searches` carries old rows over once (dry run, `--apply` to write):
  people inferred from the question and the names searched, the catalogue
  source by alias, domain or the address asked, `by` parsed; the written text
  stays in `source_as_written` and `by.as_written`, uncertain matches stay empty
  and are counted.
- `familiar research coverage`: person-by-source matrix (found, zero with
  control, zero without control, access gap, never looked; forms read and
  missing; first and last pass; who and how hard), `--person ID` card,
  `--recheck [N]` queue by usefulness, `--json`, `--save` (stores
  `coverage.json` in the instance state directory for the desk and display).
- Pass strength 1-4 from model and effort: setting `research.search_strength`
  (region and family layers) and `research.recheck_strength`.
- `instance check` advises on journal rows outside the ledger form; forms
  `search` and `search-request` and the demo family show it.

## 0.27.0 — 16 November 2026

- Prepare editable memory intake drafts from desk feedback; accepted feedback gets a read receipt without replacing existing receipts.

## 0.26.3 — 16 November 2026

- Desk "Add a relative": the chosen "Relation" button now stays highlighted
  (the sheet's general chip rule outranked it); a double click on a chip no
  longer selects its text. Narrator feedback.

## 0.26.2 — 16 November 2026

- Desk logins: the first-sign-in password is now plain — the login's letters
  and the person's birth year, or the current year when no birth year is known
  (`helena1925`). The old 28-character random string with `!` and `_` broke on
  double-click selection and on typing, and a relative never got in. The user
  pool asks only for six characters with no required classes, so the new
  password chosen at first sign-in is not refused either; a temporary password
  now lasts 30 days. Hosted desks need `desk provision`, then `desk user reset`
  for logins still waiting for their first sign-in.

## 0.26.1 — 16 November 2026

- Desk builder: the place for a parent sits above the person and names the
  missing one ("Mother" when the father is known); the partner place says
  "Wife" for a man and "Husband" for a woman (also in the card's actions); a new
  child joins the end of the row of children already drawn, as a plain plus when
  the row is full. Tree cards carry their person id (`data-person`), so the desk
  no longer guesses people by the names shown.

## 0.26.0 — 16 November 2026

- Desk: a visible "Add a relative" button by the tree and "Add relatives" in a
  person's card (father, mother, brother or sister, son or daughter, husband or
  wife, other kin in own words, and "whose relative" to pick anyone in the tree)
  open a one-person form with plain fields: names, birth, living or died, how it
  is known, a note. "Add another" follows; many people at once still go as a
  table. The addition keeps the fields as `new_person` beside a readable text and
  stays pending for the researcher. Hosted desks need `desk provision` for the new
  receiver before publishing.
- A repeated research contribution no longer revives a fact the family retired;
  a malformed index answer is no longer counted as a zero (false negative), a
  counted partial answer keeps its coverage; GEDCOM PHRASE text is kept verbatim
  with its context.
- Region pack and reading method updated from the kinship research guide v1.46
  (Lithuanian metrikai path, corrected OBD fields, re-reading a narrow period
  before widening a search).

## 0.25.1 — 16 November 2026

- Zooming out always leads back to the wide tree: after all generations of a
  person are open, the wheel, pinch and minus button return the way the
  gesture came in, or, for a person chosen by a click or a link, step towards
  the family's home people one relative at a time. Clicks keep working.

## 0.25.0 — 16 November 2026

- Give every person without a recorded birth year an orientation year: the
  first known child minus the usual age of a father or mother at a first child
  in that era (setting `tree.first_child_age`, regions and families may change
  it), else a spouse, brothers and sisters, then parents. Shown in italics as
  "≈1895" with its grounds under the card's evidence; never stored, and a
  recorded year replaces it. The whole-family view places people by it too.
- Draw the father on the left and the mother on the right: parent links
  without a recorded role take it from the parent's sex.
- Zooming out past the last generation no longer swaps the tree for the
  whole-family view; that view opens from the corner miniature only.
- Show birth and death years that research recorded as typed events.

## 0.24.0 — 15 November 2026

- Return the tree to a window around one person, with the corner miniature of
  the whole family by year and generation levels; the flat map of 0.19–0.21 was
  unreadable on a phone and hid the connections. Marks and link weights stay.
- Zoom the tree in people: wheel or pinch outwards adds generations as the
  gesture goes and then opens the whole family; inwards over a person moves the
  tree to them and keeps their visible branch, with a button back.
- A two-finger pinch on tree cards no longer opens the add-relative sheet.

## 0.23.0 — 15 November 2026

- Let chapter authors select up to four document crops for children.

## 0.22.2 — 15 November 2026

- Carry relationship decision confidence and weight into the working graph.

## 0.22.1 — 15 November 2026

- Give the reader page an empty icon so the browser console stays clean.

## 0.22.0 — 15 November 2026

- Count the family's own imported tree as firm family memory: a green check with
  the grounds "from the family tree" (setting `tree.import_is_family_memory`,
  on by default; research additions still need a document or firm testimony).
- Read a document mark without a check as "documents exist, they do not confirm
  the facts": muted on the map, stated on the full card.
- Fix the desk add-person script: a duplicate `identity` name stopped it from loading.

## 0.21.0 — 15 November 2026

- Lay the tree out as one compact map of all groups (nested branches, childless
  children folded into columns, cross links drawn lighter); open on the whole
  tree or, when that is only dots, on the neighbours of whoever is looking, with
  no card until a person is chosen and a way back to the whole tree.
- Keep zoom smooth on hundreds of people; names stay readable at map scale.
- Check firm family testimony also when the family's answer is saved as a record.
- Show an unnamed connecting person's placeholder exactly as the family data has it.

## 0.20.0 — 15 November 2026

- Let the family owner issue, reset, enable, disable and remove personal desk
  logins on Access, with tree search and a one-time password handoff.
- Verify the current owner and revocable session in every administration call;
  scope Cognito/KVS rights to this desk and provision its pinned signing runtime.

## 0.19.0 — 15 November 2026

- Navigate the whole family tree as a map; selecting a person keeps the map in place.
- Mark firm family testimony or documentary confirmation with a check; explain its basis on the full card.
- Correct unnamed connector evidence and singular English generation wording.

## 0.18.0 — 15 November 2026

- Let a reader attach a correction directly to a life event in the growing tree.
- Render unnamed hypothetical connecting people compactly, using their children’s
  clan form when it can be determined and keeping the explanation on the card.

## 0.17.1 — 15 November 2026

- Keep incidental login-page requests from replacing OAuth state/PKCE; carry person IDs only in signed JSON, without HTTP-header character restrictions.

## 0.17.0 — 15 November 2026

- Show attributed family-memory and documentary origins, evidence-based confirmation,
  linked documents and a growing-tree summary in the reader.

## 0.16.0 — 15 November 2026

- Opt published AWS desks into host-created Cognito personal logins with reader
  and owner roles, managed password changes/recovery and revocable edge sessions.
- Add desk user commands and initialize reader kinship from the login's person;
  readers retain their own choice and send remarks with a verified author.
- Keep shared-login publication as the default and loopback viewing unchanged.

## 0.15.0 — 15 November 2026

- Show anonymous search coverage in the investigation: known and checked sources,
  first journal appearances, working-day bars, repeat passes and source categories.
  Normalize common aliases and domains only while counting existing journals;
  collectors and search forms acquire no new steps, fields or checks.
- Keep the remark sheet usable after scrolling an investigation past its header.

## 0.14.0 — 15 November 2026

- Compare and choose clan surname forms by birth names, excluding explicit married
  names and untyped names shared with a husband. Preserve literal source names
  and report genuine paternal spelling differences in full instance checks.
- Share the page top across reader and investigation screens, reserving space
  for unavailable controls. Combine work totals in the investigation and omit
  zero values.

## 0.13.0 — 15 November 2026

- Use one lower navigation, private label, version and remark entry across the
  reader and investigation. Open remarks on the first click without scrolling;
  dismiss and resume drafts with a visible unsent-text indicator.
- Put alternative outcomes beside research volume. Require a recorded browser
  walk at desktop and phone widths for interface acceptance; provide a reusable
  walk sheet in the reviewer method.
- Render a translated feed period as text so the stories screen remains usable
  with a language-keyed reader delivery.

## 0.12.1 — 15 November 2026

- Keep one installed journey and weighted core data, privacy and install checks.
  Drop presentation and method lint requirements; time overruns only advise.
  Core contracts remain authored with code; surface contracts are optional.
- Use safe defaults for malformed presentation preferences while keeping privacy
  configuration and trust modes strict.

## 0.12.0 — 14 November 2026

- Keep tree cards to names, life years and birthplace. Store one reversible clan
  surname decision, preserve each person's documentary spellings, derive a
  surname only for an unambiguous named father from his children, and report
  undecided paternal spelling differences without blocking the reader.

## 0.11.0 — 14 November 2026

- Keep collector record and journal form findings separate from display readiness;
  validate and watch adopted research dependencies, with strict own-path checks
  and one unknown journal numeric-field finding per file and affected-row count.

## 0.10.0

- Investigation shows recorded weight shifts, all alternatives and rejection arguments, cumulative source coverage and paginated work without dates. Question remarks retain their question ID; privacy, navigation and feedback share one lower row.

Engine numbers follow the rule in `AGENTS.md` ("Engine version"). Each desk build
records the number it was built with in the family's `.secrets/desk-build.json`.

## 0.9.0 — 14 November 2026

- Add language-pack kinship words, qualified tree paths and an offline kinship
  glossary with examples from the permitted reader graph (Russian, Polish, English).

## 0.8.0 — 14 November 2026

- Add remarks from every desk screen, precise page and reading context, persistent
  drafts, browser-owned receipts and researcher replies. Invite unnamed relatives
  to be named through the same inbox. Move the private label and engine version
  to the lower edge. Cloud receivers require `desk provision` before publishing.

## 0.7.0 — 14 November 2026

- Keep unreferenced collector captures and archive bytes outside snapshots and
  watches; retain referenced-file race checks and the full public corpus gate.
  Compile host text identifier checks once for quick summaries on large families.
- Serve pinned checked desks over persistent HTTP with conditional browser
  caching and cheap corruption checks. Both local servers accept localhost names;
  local desk feedback accepts consecutive messages without a cooldown.

## 0.6.0 — 14 November 2026

- Add `reader book`: an offline A5/A4 HTML book with one replaceable stylesheet,
  full or children's text, document crops, original readings and chapter-end
  grounds. Admission reuses current independent reader attestations and the
  chosen public or host-private privacy projection; omissions are counted.
- Private reader previews can save review tickets for the exact local bytes.
  Existing private reader delivery remains available without book acceptance.

## 0.5.0 — 14 November 2026

- Expand the Belarus–Podlasie pack to 51 sources with dated provenance and
  explicit unknown-year gaps. Pack answers retain unknown-year source candidates;
  Polish and Latin record-reading cues are available by selected language.
- License the engine, method and own pack texts under MIT; carry third-party
  notices with wheels, reader shells and desk sites. Neutralize reader storage
  keys and remove private implementation instructions.

## 0.4.0 — 14 November 2026

- `research replay` exposes offline capture replay with full request/capture
  forms and actionable recipe/permission refusals. The separate module entry
  is removed. Complete documents, chapters and evidence forms match file containers;
  malformed containers name the file and repair example.
- Text pages and family summaries report current reader confirmation separately
  from pending feed review. Duplicate source declarations name both files and
  explain intake ownership; PRD and README describe actual search and language defaults.

## 0.3.0 — 14 November 2026

- Publication is optional: absent `[publication]` or `target = "none"` keeps work
  local. Desk build/serve ignore cloud settings; cloud commands require explicit
  `aws` before any disk mutation or external process, including publish --build.
- AWS failures explain missing CLI/profile and deployment state recovery;
  an unbuilt local desk points to build or serve --build.
- `method list` and `method show role/skill <id>` read bundled method resources
  without family discovery or startup maintenance. A thin portable Agent Skill
  and local-first documentation describe the installed path.

## 0.2.2 — 14 November 2026

- Person edits reuse build-local input reference indexes and resolve each distinct
  dependency path once per check. Publication validates restricted-term forms
  once; semantic text findings, privacy, gate and review checks remain in place.
- Person normalization, prose/date adaptation and card serialization run in
  memory instead of reading thousands of cache files. Feeds, documents and media
  keep checked reuse; privacy and full graph validation remain authoritative.

## 0.2.1 — 14 November 2026

- Desk builds reuse their checked private reader and unchanged media. Person
  projections and feed materialization are cached by content; shell and desk
  wording changes do not export family data again. Privacy and gate checks remain
  authoritative; the engine release number is recorded without clearing the cache.

## 0.2.0 — 14 November 2026

- Engine-owned reader sources and a locked Bun build reproduce the packaged shell
  without a pilot checkout; all six existing delivery files retain their exact bytes.
- Instances pin `[engine] version`; checks and desk builds warn on a mismatch.
  `instance record-release` records the installed wheel's SHA-256 and engine commit.

## 0.1.0 — 14 November 2026

First numbered state of the engine: everything before it shipped as 0.0.1.

- Number visible: `familiar --version`, `instance check`, a small mark in the desk
  notice bar and in the private reader's notice; desk builds record `engine_version`
  and `built_at`.
- Desk tree: ghost places are a builder mode. Ordinary viewing shows none; a quiet
  toggle beside the tree controls turns it on (automatic for a family under three
  people); long-press or right-click on a person still adds a relative. Ghost words
  fit any person: "Сын или дочь", "Муж или жена", "Родитель".
- Version heat by meaning: отпала, ослабла / маловероятно, возможно, окрепла /
  скорее всего так, почти наверняка, подтвердилась; "ослабла" and "окрепла" only
  after a real fall or rise. Log events: ослабла, отпала, окрепла, подтвердилась;
  versions born together on one branch are one row ("Новые версии: 6").
- Large families: desk listings compare names in one order (case broke the check
  on Windows); private display snapshots bind research originals that are only
  tested for existence by name, size and time (pilot: 3.1 GiB became 262 MiB);
  desk history reads one git log instead of one process per commit.
- Desk journal dates in family words; one-row phone menu.
