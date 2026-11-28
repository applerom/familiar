# Research coverage: who was looked for where

The ledger answers "was this person looked for in this source, when, by whom
and how hard" from existing journals and read records. Nothing is added to a
researcher's work except naming three things on each row.

## Writing a row (agents)

`research form search` shows the row. Beyond the old fields:

- `people`: tree ids of the people the search is for. Empty if it is about a
  place or a surname and no person yet. The matrix can recover a surname-place
  population from the actual query, family places and overlapping dates.
- `source`: an id of the region source catalogue (`sources.toml` of the pack).
  Anything else is advice from `instance check`, with the nearest id; web search
  is `web-search`. The matrix groups uncatalogued sources by site, aside.
- `by`: `{agent, model, effort}`, e.g. `{"agent": "collector-w23", "model":
  "gpt-6.2-sol", "effort": "high"}`; a host or family member reading themselves
  is model `human`.
- A zero is worth most with `control` (a known person found by the same query)
  and `coverage.forms` listing every spelling read.

## Naming the series and depth on a row (agents)

When you read frames of a book — a parish register, a revision, a census — say
which book, which years and how deep, in `coverage`; nothing else changes:

```json
"coverage": {"series": "ponta-do-moinho-baptisms", "years": "1900-1902",
             "depth": "full", "forms": ["Calhau"], "read": 212, "note": "..."}
```

- `series`: an `id` of the family's series list (`sources/series.json`, form
  `research form series`). No series for the book yet? Add it: `id`, `kind`,
  `place`, `years` that exist, `holder`, `online` (where the copy is, which
  years, `access`), `missing` (years absent from the copy).
- `depth`: `full` — every entry of the year, all columns; `surname` — only
  the surname column or one letter of an index; `named` — you looked for named
  entries; `index` — someone else's index, page not opened. A year read for one
  name is not a read year for another question, so say `named` when that is
  what you did.
- Several books in one pass: `"series": [{"id": ..., "years": ..., "depth": ...,
  "entries": "No 6-47"}, ...]`; `entries` is optional text.

Rows without `series` stay valid. Rows without `depth` show on the map as "depth
unknown"; a row that does not name its series but used a series' online source
for its place counts as "depth unknown" there too. `instance check` advises on
an unknown series id or depth; it never refuses.

## The access ledger (agents, lead)

A journal row says what was searched. It cannot say what exists and cannot be
opened: a parish book that lies in a reading room leaves no rows, so "not tried",
"tried, no record" and "exists, no access from home" used to look the same. The
ledger (`research/access.json`, path key `access`, form `research form access`)
says, per place and kind of paper: what years, which holder and call number, and
one state with its date, author and report:

| State | Means |
|---|---|
| `home` | opens from home, not finished (`read` of `of`) |
| `copy` | the archive sells a copy remotely: `price`, and in `needs` what is still missing to order it (sheet numbers) |
| `room` | no access from home: only in the archive's reading room |
| `letter` | no access from home: the archive answers letters |
| `unknown` | not settled where it is, or whether it survives |
| `read` | read, with `read`/`of` when counted |
| `none` | nothing to read: lost, or this holder or site has none |

**At hand-in** an executor records each verdict in one command; the same place,
kind and years (or `--id`) change the row instead of adding one:

```
familiar research access record --place "Ponta do Moinho" --line Calhau --kind parish \
  --years 1911-1915 --state room --holder "Invented diocesan archive" --reference "books 5-6" \
  --look-for "Children of a Calhau household" --by collector-a --report research/2026-11-12/README.md
familiar research access record --id a1 --state read --read 31 --of 31 --by collector-b
familiar research access [--line Calhau] [--place "Ponta do Moinho"]
familiar research access record --id a7 --state copy --price "3 dollars a page" --needs "page numbers" --by collector-b
familiar research access --order        # copies to order, then the reading-room list
familiar research access --markdown --save   # the whole ledger as ACCESS.md beside it; every later verdict renews it
familiar research access note "What we have read so far." --section "The narrator's lines"
familiar research access note --place "Ponta do Moinho" --section "The narrator's lines"
```

There is one ledger, the JSON. The page is its print: every row with its verdict's date,
author and report, the copies with price and what is missing to order them, the reading-room
list in `order`. Words around the rows (the header, a section, a place, `--room` above the
list) are kept in the ledger by `access note`. `--save` never overwrites a page kept by hand,
and `instance check` says when the page is not the print of the ledger. Words may be given as
a JSON row by language: `--look-for '{"en": "...", "pl": "..."}'`.

A verdict "does not open from home" is a finding: it goes into the ledger the same
day with its call numbers, and nobody walks that road again until access changes.
A row marked `--doubtful` (the book may not hold our place) neither opens nor
closes a road. Years and depth read inside one book stay in the series list.

- `research plan` puts the books of the line's places above its approaches, each
  with its state. When nothing of the place opens from home, approaches that stand
  on the books read "no access from home", the next step is the reading-room order
  or the letter, and no pass over name bases follows; what costs nothing (a home
  paper, a map of record keepers) is kept beside it as "Meanwhile". A copy that can be
  ordered is no closed road: the next step orders it with its price, or finds out what `needs`
  names. Books that open
  from home come before a question or a letter. A line without ledger rows says
  "not tried".
- `instance check` advises, never refuses: when a version, a top-level note in
  `research/` (the strategy) or the desk's plan says a line is exhausted or a person
  not found while the ledger holds unread books of its place, and the same passage
  does not say what is unread; and when a line has many journal rows and no ledger
  row for its place. "Exhausted" is written about a kind of source, with the years
  read, never about a line.
- The family reads the same on the search map: per place, what we have read and
  where the rest lies, and the reading-room list to take along. `look_for` is read
  by relatives and never names the living; `note` stays with the research.

## Forms and the identity score (agents)

`research forms Морецкий Lunografow [--kind surname|place|given_name] [--year Y]`
lists dictionary forms first, then marked suggestions: `by clan decision` (one
row of `tree_metadata.surname_forms`) and `by key` — spellings the family has
already written (dictionary, clan decisions, tree names) whose key matches. The
key folds scripts, pre-reform letters, -owa/-ówna/-ska/-ая, act cases and
"z ...ich" to one stem and a sound code (rules: the region pack's `name_key.toml`,
the language packs' `[language.surname_key]`). Key forms are worth a query; they
never become required forms, never close or open a plan and never join clans.
What the key does not settle: a misread village name gets sound
neighbours, not a correction — a place is told apart by its record, not by sound;
two real surnames may share a code; a person's other surname (a convert's, a
step-father's) is about the person. `instance check` lists tree spellings that
share a key outside any one clan decision (`same-key`, `outside`): decide or ignore.

`research compare FILE` scores "one person or two". `FILE` is
`{"a": mention, "b": mention, "pool": N}` or `{"target": mention, "candidates":
{"id": mention}, "pool": N}`; a mention carries what a record already says:
`given`, `surname`, `sex`, `born` `[lo, hi]` or `born_exact`, `year`, `place` or
`places`, `parish`, `manor`, `rite` (`latin`, `uniate`, `orthodox`, `revision`),
`father`, `mother`, `spouse`, `maiden`, `siblings`, `sponsors` (surnames),
`household` ("1816 No 18"), `class`, `died`. Each argument gives a likelihood
ratio with its basis; arguments of one group (the family, the place) are damped.
A name's weight is its rarity among the family tree's people (fallback 1/25
with few traces). `pool` is how many men of that age the place held (region
default with its basis); `weight` is one person among them. With candidates,
`unseen` is its own row: a path's share among the candidates we saw is not its
identity weight. The score is your objection and instrument: it merges nothing,
writes nothing and the family never sees it. Where you and the score differ by
more than two times, say why in the decision.

## Planning approaches

Run `research plan` for all surname lines, or `research plan --line "Example"`
for one. A starting person's tree ID also selects a line. `--json` shows
stable approach IDs, which inputs are missing, sources tried, and passes whose
approach was inferred. Follow the next step on the first applicable, enabled
approach that still has work. Inventory work requires a place at the frontier
and a chain to living family with every link at least 0.5.

Use **Surname households by place** (`place-nest`) when a surname and a
historical place give you a way around a break in the line. A place in an
origin hypothesis with weight ≥0.3 also works. Start at the earliest register,
revision, census, inventory or parishioner list and follow the households
forward, including neighboring parishes. Return a household table by generation
and decade for which books survive. Record proposed people and their links
within the nest with weights, then rank the candidates for the person at the
break with a separate weight and reason for each proposed link to the family.
A weight below 0.3 is a normal entry in that table. Add a link to the family
only when there is a reason for it. Inventory work goes deeper from an
already linked frontier. This approach builds toward the frontier from the
earliest local records.

A line has a place when the access ledger, a version from 0.3 up or a told fact gives
one, whatever its cards record; it has a parish when the ledger's parish books name
their church, and a registrar when the ledger holds a row answered by letter.

Set optional `play` on new journal rows to the method ID, for example
`"play": "keeper-forms"`. Record the usual query, scope and result. When
the observation shows the whole scope was covered, `coverage.complete: true`
can record the closure. Preserve the actual years, forms, reading and control.
Old rows remain valid. The plan infers an approach only when the source and
query support it. Other rows are listed under `unrecorded_play`. A draft
letter is visible in the plan, and a sent letter starts the wait for an answer.

For a nest pass, write the target locality in `query.place`, even when you
read a neighboring parish. Record the years actually in scope so the plan can
find the earliest decade, or part of one, still open in the journal. Mark a scope complete once its
households and applicable candidates have been recorded. A legacy
`family-reconstitution` query with one household's names counts as a
household fingerprint. A surname sweep of a locality counts as a place nest.
The plan counts contributors' people of the same surname and place who have
no chain of links weighted at least 0.5 to the family.

For place forms, the plan compares the dictionary's `kind: "place"` entries
with the keepers' countries and catalogue languages/scripts. Add `language`
when the language of a form is known. An untagged spelling can cover a script
while its language is still unrecorded.

```toml
[research]
focus = ["Example", "Another"]

[research.plays.archive-letters]
order = 1

[research.plays.surname-place.lines."Example"]
enabled = false
```

Focus brings those lines to the top of the plan, `coverage --lines`, and
`coverage --recheck`. Use `coverage --recheck --line "Example"` to keep
the queue to that line. Set `enabled` and `order` for a play at the family
level or override either in its `lines` table. Lower numbers come first,
with ties in [registry order](../method/research-plays.toml). Without play
overrides, recheck keeps its existing score order within each line group.

## When the family can say no more

Not every family can ask its relatives. A teller may say that on a line —
a wife's parents' families, a side where nobody is left or nobody talks — no
more will come, now or later. Then what we have gathered is the material, and
the story is ours to put together from the whole of the indirect evidence.

**Closing a line.** The family's words go into `family/horizons.json`, one
entry per line, the line named as in `[research] focus` and the versions:

```
familiar family horizon close Calhau --by "the host" --since 2026-11-12 \
  --known "Nobody on Rosa's side is left to ask; she came from near Amaro's village." \
  --reopen-when "a Calhau descendant on the islands writes back"
familiar family horizon open Calhau
```

From then on unanswered questions on that line leave the Relatives page, the
cards and the feeds; asks already answered stay as they are. `family ask
create` refuses a new unanswered ask on the line unless `--despite-horizon`
says it was meant (write why in `next_hint`). `research plan` marks the
home-document approach "nobody left to ask", puts the indirect approaches first
and the offline letters and deep inventories last, as options the host may
choose. `--known` is a lead, not a fact: turn it into arguments `for` and
`against` of the versions with `kind: "family"`.

**Silence is not an argument.** A weight moves only by an argument — a
document, a count over households and names, an indirect sign. That nobody can
be asked moves no weight. It changes the decision: we stop waiting with the
story.

**Indirect signs.** Each is an argument of a version, and each tells apart
something of its own; most are fields of `research compare`:

- faith and parish (`rite`, `parish`): which books hold the family; a namesake
  of another rite falls away;
- staying put (`place`, the region's `pool`): rural families married and stayed
  in their parish; a candidate at home outweighs a namesake far away;
- a name from grandfather to grandson (`father`, `given`): a name repeated a
  generation apart ties households of one line;
- the parents' age (`born`): a candidate too young or too old to be a parent drops out;
- a rare set of names (name shares, `siblings`): parents and children together
  are a household's fingerprint;
- godparents and marriages (`sponsors`, `spouse`, `maiden`): one circle in two
  acts makes them one family.

**Three layers of certainty.** We speak of each in its own way. The land and
the faith — which parish, which estate, under which rule the family lived — is
usually the firmest. The line, or the nest of one village, is a version. The
people in it are the actors of that version. In the demo, that the Calhau family
lived on the islands and went to a Catholic parish is firm; which parish Rosa
came from is a version (Ponta do Moinho 0.5, Ponta das Garças 0.3); the father
we would give her there is an actor of the version. A layer from 0.5 is told
plainly; below, as our version, without a caveat in every sentence: the form
carries the doubt (a dotted line and rings in the tree, the "our version" line),
not the words.

**The leading version is named.** An open question on a closed line gets a
`story_choice` in its `versions/*.json`:

```json
"story_choice": {"version": "ponta-das-garcas", "by": "interest",
                 "basis": "A bride from another island gives the family a crossing to tell.",
                 "date": "2026-11-22"}
```

By default the story tells the heaviest version (`by: "weight"`). When rivals
are close — at least half the weight of the first — interest may choose: a
lively story, documents with frames, the history of the land (the version's
`interest`). Interest never enters a weight, never lifts a version weaker than
half of the first, and never changes the thresholds for drawing a link (0.5 and
0.3). `instance check` refuses a choice that breaks this, names the versions
with their weights, and hints "name the leading version" for an open question
on a closed line. A version told on the main line of the tree should be the one
drawn there: where `main_line` hangs a person of another version, the check says so.

**The story is reversible.** When new material comes — an archive, someone
else's pedigree, a chance answer — weights are recounted, the choice is
revisited and the story is corrected. So chapters hang on the household, the
place and the event rather than on a chain of fathers. `family horizon open`
brings the questions back.

## The search map (lead, host)

`research map [--line NAME] [--json]` answers for a line: what of the open
record has been read, and what has not. The desk shows the same as the host's
page "Search map" (left out of the copy the family reads).

All chains of one surname are one line. The lines the family works on (its
`research.main_lines`, or, without them, lines with open questions) come first
and open; the rest fold to one row with their tallies. On the page a place is
one row on the line's time axis, a lane per kind of book; a tap opens each
series year by year. Name bases are small tiles, holes first, then the least
read; the numbers and the forms not read are behind a tap, and bases opened
off the line's fit sit behind one more.

- **Record series**, year by year, the best reading reached: in full; surname
  column; named entries; someone's index; depth unknown; and for unread years
  online (open or with the host's login), archive only (no online copy: where
  it is, from `holder`), missing from the copy, did not open (an access gap).
  A series belongs to a line by its `lines`, otherwise by its place — the
  places of the line's people and of its leading versions.
- **Name bases**: for every catalogue base that fits the line, whether it was
  opened, how many rows it returned and how many were read, which of the
  family's surname forms (`research forms`) were read and which not. A base
  fits when the catalogue's `years`, `born`, `countries`, `regions`, `parishes`,
  `episodes` and `planning_requires` admit at least one dead person of the line
  with a recorded place — the same applicability as `coverage --recheck`. A
  base that cannot hold these people is not a hole and is not listed. Where
  nobody on the line has a place, the map says fit is unknown. A base that
  holds one community's records says so with `communities` (`jewish`,
  `christian`); it is a hole only for a line whose people's own records name
  that community (a faith, a rite, a parish, a baptism). Another community
  rules it out; none recorded leaves it as "only if the line was ...", never a
  hole. An emigration or other episode still needs `episodes` or
  `planning_requires`.
- **Books of the place** (the access ledger, above): what was read, where the rest
  lies, and the reading-room list. The page exists in each reader language that has
  its translations.
- **Read next**: the empty cells, as runs of years, ranked by value — the
  years in which a record of that kind can name the people of the line's open
  questions and its frontier (their birth windows; marriages 15–45 years
  after; deaths up to 90), and the place of the leading version — then by cost:
  online now, the host's login, a letter to the archive.

"Exhausted" is a statement about the map. While open online years in the
question's window remain unread, `research plan` reports no play as exhausted
and no repeat ceiling for the line (the old count stays in JSON as
`repeat_ceiling`); it shows **Open record** with the first runs to read, and
where the next step would have been a question to relatives or a letter, the
next step is to read those books. Without a series list the plan says the open
record is unknown rather than read.

## Reading it (lead, host)

- `familiar research coverage`: counts of access-ledger entries open from home and still to read, by family line.
  `--line NAME` or a starting person ID lists the entries with their place, reference and reading progress.
  The journal summary gives the number of rows with no tree person. A row documents a place reading when it
  records reading at a specific place or in a named series. A place-scoped corpus record also counts for its
  named place. These readings measure visits and individual records. Book completion comes from the ledger.
- `--family`: the full matrix. Cells: R result rows, D read record, +F explicitly established identity, Z zero
  with control, z zero without control, ? outcome not recorded, ! access gap, . not looked; the digit is
  the strongest pass (1-4; 0 means no model was recorded, which counts as weak);
  `?` means the person was inferred from the row's question only.
  `~` means a surname search in place/period, not an individual search.
- `--person ID`: one person, every source with passes, dates, executors,
  forms read and surname/given-name dictionary forms not read; and what was never
  looked at. A repeat ceiling marks three completed passes without a newly
  recorded item and removes the cell from recheck. Newly dated or referenced
  read records restart the count. Access gaps and dubious queries do not
  count as completed passes.
- `--recheck [N]`: the N most useful cells to look at again: never looked,
  access gap, only passes weaker than `research.recheck_strength`, zero without
  control, spellings missing, and a source whose catalogue entry carries an
  `updated` date later than the last pass. Open questions and sources that gave
  finds for the family rank higher. Plan a stronger pass from the top of this list.
  Catalogue `years`, `countries`, optional `regions`, `parishes` and `episodes` filter the queue and
  "never looked". A life window uses birth/death dates; without death it allows
  120 years, and a `birth_guess`/reader `birthGuess` has 30 years either side.
  This is planning orientation, not evidence of a date or a new life-status bound.
  Explicit birth/death statements in family notes also orient this window,
  including uncertain memories; unrelated biography years do not. Conflicting
  dates retain the union. No inferred event is saved and life status is unchanged.
  Unknown dates/places remain eligible. Pack `coverage.places` aliases connect
  written places to countries/regions; ambiguous borderlands can name several.
  Excluded cells are counted as `not_applicable` (epoch/region), shown as `-`
  when empty; recorded passes stay visible even outside the planning window.
  `totals.eligible_cells` counts applicable cells for deceased people across
  the catalogue sources the ledger knows about. `totals.cells` counts recorded
  person-by-source cells.

  An optional catalogue `born = [first, last]` gives the inclusive birth years
  of people covered by a source. A known birth window wholly outside this range
  excludes the cell by epoch. An overlapping or unknown birth window leaves the
  cell eligible under the other filters. For wartime collections, `born` still
  applies when `years` includes later awards or is unknown.
- `--lines`: one row for each father's line from the tree root, each spouse,
  and each maternal branch. Rows show the surname, the chain to its farthest
  ancestor, and the weight of each hypothesized parent link followed (minimum
  0.30). They include up to three open question titles with the weight of each
  leading answer. A question's `line` surname matches declared
  `tree/metadata.json` surname forms and regular gender forms. A question
  without `line` matches by a person anywhere in the chain. The default order
  multiplies the number of unsearched and weak cells by one plus the highest
  open answer weight. Set `"research.main_lines" = ["Surname A", "Surname B"]`
  under `[settings]` in `familiar.toml` to pin these lines in order and mark the
  remaining lines as secondary in the CLI and the desk. With this setting,
  line fronts count living people and those of unknown status outside the
  queue. The recheck queue labels rows by line where known and puts cells for
  the chosen chains and their ancestors' siblings before other people,
  retaining the usual score order within each group.
- `--json`; `--save` also writes `coverage.json` in the instance state
  directory (`instance paths`, key `state`) with the matrix and full queue.

Strength comes from `research.search_strength` (keys `model:effort`, either
side `*`; region and family layers add or replace keys). Reading is local: no
network, and a conclusion rests on what the journal says, not on what the site
holds.

### Collateral branches

In the instance's `familiar.toml` set `"research.collateral" = "hints"` under
`[settings]`. The family desk shows the effective mode next to **Lines** on the
research progress page. Edit that line and rebuild the desk to change the mode.

- `off`: leave collateral descendants out of planning and omit their hints.
- `hints` (default): show each linked, already read record under **Collateral
  hints**, with the person, link status and related ancestor. These people
  contribute no planning cells to the matrix or recheck queue.
- `full`: also plan searches for these branches. `collateral.totals` and
  `collateral.people` give their own matrix counts and rows. These cells come
  after the main queue, even when their scores are higher.

The root, spouses and their ancestors define the main lines. Their own siblings
keep the existing research scope. The collateral group follows descendants of
ancestors' siblings, including the descendants' spouses. Living and possibly
living people stay outside recheck in every mode. Existing journals, records
and version files remain the inputs.

## Scope, completeness and read records

Analytical summaries use `record_role: "analysis"`; source maps/catalogues can
use `record_role: "catalogue"`. They supply no personal record visit. Old comparison
tables containing `target_ids`, `record` and `weights` are recognised without edits.

A local review uses `query: {"mode": "review"}`, the usual row identifiers,
`people`, `source`, `by`, `question`, `coverage` and `hits` (0 is allowed).
Its `record_links` is an array of `{person, record, status}`; `record` is an
exact record id or local record path; statuses are `same`, `other`, `mention`,
`unestablished` or `conflict`. Save the reasoning in `meaning`/`saved`.
A review supplies no search pass, strength, forms, yield, negative evidence or
source availability. It resolves only the named record and person; unknown
candidates stay open. Legacy `query.review` rows are also reviews; single-person
saved comparison reports with exact record ids and explicit same/other conclusions
remain usable. Multi-person prose is left unresolved. Review assessments never
become accepted tree assertions or +F by themselves.

Accepted person facts and accepted identity decisions resolve exact record or
document references through the tree source registry. Generic site roots and
verified searches do not establish identity. Other candidates of an already
linked principal become `other`; a co-defendant or witness remains contextual.
A contrary reading against an accepted identity stays a conflict.

Surname-only queries apply to matching surname forms in the family's recorded
place and overlapping period (`people_basis: "surname-place"`, `scope: ["surname"]`).
An old question's people do not turn such a query into a personal search.
Named queries and declared people retain their individual scope. These are
coverage associations only, never identity or kinship decisions; journals remain unchanged.

Explicit `people` always survive an incomplete name dictionary; cells list the
affected search ids in `dictionary_mismatches` as advice to enrich it. A migrated
question-only attribution remains refinable. Read records expose `record_links`
with principal/mention status, original match confidence and direct birth/parent
differences. An unresolved principal yields `action: link-record` before model
strength or missing forms: establish the link from the document already read.
An explicit `other`/`different` or incompatible birth/parents closes that candidate
as another person, never a negative search. Context mentions are retained apart.
Cells containing only contextual mentions use `identity: context-only`; the
queue does not request another search to resolve a role the record did not give.

`availability` independently carries the latest recorded source access, date,
refusal kind and search id. It never replaces a previous best outcome. A stopped
source yields `action: wait-for-access`, including for people not yet searched;
local record-link work can continue. A later recorded accessible pass releases
the stop. This is local journal knowledge, not a live host gate query.
An accessible document page does not release a stopped search route.
`latest_refusal` also preserves the cell's own last denial after other people's
source visits. Day-only observations in different journals have no established
same-day ordering: a success does not silently clear that day's stop. A later
dated accessible search or an ordered same-journal recovery can release it.
`query_issues` keeps composite surname fields, recorded syntax probes and
substring/similar-result warnings visible as `query-dubious`; such a pass cannot
supply a zero or read-form coverage. A clean earlier pass remains available.

`records/**/*.json` and `research/team/**/corpus/records/*.json` contribute local
source visits when an actual person/subject or read field names a tree person.
Each visit retains its record path. References in versions, links alone, saved
queries and speculative collector notes do not count. Identical record copies
count once. A name match means a read record is available (`records`, D), not
established identity. An explicit record `match.confidence: "same"` with a
tree id, or an accepted tree assertion referring to that record/document,
supplies `identified: true` (+F/✓). Positive `hits` stays `outcome: "found"`
for JSON compatibility, but means result rows (R), never a found relative.
Place-only catalogue checks also remain visible (`scope: ["place"]`), labelled
as a place visit rather than a personal search. A surname with a parent's name
selects that parent's descendants, not the parent whose name appeared in the query.

`strength` is the strongest model/effort actually recorded, also per executor.
`plan_complete` separately compares read forms against the person's dictionary
forms and their recorded `candidate_forms`. The coverage on a shared journal
row can describe searches for several people. It stays visible as read
coverage and does not add other people's forms to their requirements.
An incomplete plan is eligible for `--recheck` even with positive rows or
a strong executor, subject to the source's scope and the repeat ceiling.
Records alone do not close a search plan. Successful textual
controls in `coverage.note` or `meaning` have `control_basis: ["text"]`; they do
not repair missing years/forms/read scope on an incomplete zero.

Source `search_languages`, `search_scripts` and optional `search_language_eras`
filter applicable forms; full `forms` and `missing_forms` remain in JSON. Cards
show at most four missing forms. Source `planning_requires = "parish"` or
`"episode"` and `planning_terms` suppress blind new suggestions when relevant
context is unestablished, without asserting that a source cannot contain the person.
Recorded visits remain visible. Parish/country fit is not proof of indexed coverage.

Variant forms accept `annotation`, `sex` (`M`/`F`), `people` (tree ids) and
`episode` independently of `text`. Legacy spaced editorial brackets become
annotations on read; an inline supplied letter remains part of the spelling.
Unambiguous feminine surname endings and legacy emigration annotations supply
planning metadata, preserving `as_written`. An explicitly recorded sex takes
precedence. Episode forms apply to matching catalogue `search_episodes`/`episodes`
or an emigration source for an emigration form. A successful unannotated spelling
counts. Catalogue `search_match: prefix` additionally covers longer forms.
When catalogue writing is unknown, only writing actually used in successful
query name fields is required; `script_status: unverified` means "письменность
не проверена", never established language coverage. Dated personal episodes,
including uncertain attributed family memory, raise fitting sources; military
sources covering only childhood rank lower. Estimated births over 100 years
before source coverage suppress new work (`age-at-source-start`), keeping all
recorded visits visible. These are planning assessments only.

Version arguments may use `search:<id>` findings as before. On `against` only,
`result_state: zero-with-control`, finite zero hits, nonempty years/forms,
positive read coverage and a recorded positive control can supply a weak
negative argument within that scope. Uncontrolled zeros, refusals and dubious
queries cannot. A zero never becomes an identity or kinship fact.

FamilySearch has independent `familysearch-tree`, `familysearch-records` and
`familysearch-fulltext` cells. Existing URLs and preserved original labels select
a channel. Bare ambiguous `familysearch` rows remain visible as "channel
unrecorded", excluded from new suggestions; they never close any of the three.

## Showing it

- Host-private reader: the person panel gets "Where we looked" (folded line, then a row per source with outcome
  mark, latest pass, strength dots and forms tried; "not looked in yet" lists only sources fitting the epoch and region).
  The block is computed from the host's own journals when the private reader is built (the display snapshot holds
  no journals), so rebuild with `reader export --host-private` to refresh it. Schema field `coverage` has the policy
  `host-private`: it is absent from every public projection, and `scan` removes it from a public graph as a second guard.
- Author desk (`/coverage`, host tool `reading_desk.py`): people by sources from `.state/coverage.json` (nearest to the
  root first, hover for dates and executors) and the recheck queue. Refresh the file with
  `research coverage --family --json --save`.

## Old journals

`familiar research migrate-searches` is a dry run that counts; `--apply` writes
through the family writer, once. It only appends `people`, `people_basis`
(`inferred` or `unresolved`), `people_from`, rewrites `source` to the catalogue
id and `by` to the object, and keeps the written text in `source_as_written` and
`by.as_written`. A person is placed from the names searched (surname and given
name, with variants, against the tree) and from the people of the row's question;
an unclear match is left empty and counted. Names use the tree's forms, given-name
and surname variants and exact transliteration comparison, without fuzzy identity
claims. Question-only rows are refined on repeat when a named person can be found;
rows without names keep their question basis (`?`). Declared people are preserved.

`--executors file.json` supplies a host-prepared map such as
`{"collector-a": {"model": "gpt-6.2-sol", "effort": "high"}}`. Labels match exactly
or as prefixes at a separator (`-`, `_`, `/`, space, `;`, `(`); the longest match
wins. Thus `collector-a1` does not match `collector-a10`. Conflicting matches
stay unknown. Only missing/generic executor details are enriched, also on rows
already migrated, with `by_basis: "executor-map"`; the old text survives.
The engine never finds or reads the host's run log itself. Keep evidence and
uncertain mappings with the host, outside the engine repository.

Migration also discovers `research/team/**/SEARCHES*.jsonl` (case insensitive),
or accepts repeated `--legacy PATH` files/directories inside the family root.
It copies recognised rows to `searches/legacy-<folder>-<path-hash>.jsonl`, leaving
archives unchanged. Each copy has `origin: {path, line, sha256}`; content hashes
skip identical rows across copied journals and repeated runs. Old `state`,
`result`, single `results`, `read` and `rows_read` shapes are read conservatively:
refusals remain access gaps, missing reading scope is never invented as a zero.
Unparsed lines and duplicates have separate counters. Dry run changes no files;
repeating an applied migration with the same map adds nothing.


## Incomplete archival outcomes and search variants

Archive copies receive `id = legacy-<origin.sha256>`; an original id and any
normalized count, state or meaning survive in `*_as_written`. Explicit numeric
strings (including grouped thousands), `count`, `result.count` and complete
`results[].count` lists become finite counts. Missing counts remain `hits: null`,
`result_state: unrecorded`, `meaning: unrecorded` ("итог не записан"). An access
refusal remains an access gap even when no count was recorded.

A recorded zero without years, forms or positive read coverage becomes
`result_state: zero-uncontrolled`, `meaning: zero-uncontrolled` ("ноль без
контроля"). It is accepted as an incomplete observation, never negative evidence;
the original meaning remains available. A positive control cannot upgrade it.

Missing forms include the pack's `variants.toml` and the family's configured
`variant_overrides` (default `family/variants.json`, `{"variant": [...]}` with the
same entries as the pack). Dictionaries supply search candidates, not identity.
Query and coverage masks `*` and `?` cover matching forms. Family notes and
uncertainty belong in the dictionary; automatic transliteration adds no new
required spelling.

The engine life assessment excludes every person other than `dead` from
`--recheck`, without hiding their recorded searches. `totals.living_or_possibly_living`
counts these people. Transport labels such as Host browser or host source_gate
ledger resolve through a URL in the row; absent a source, they count in
`totals.rows_without_source` and do not become source columns. Catalogue domains
match URL paths and equivalent Unicode/punycode hosts. General forums own their
domain; a transcription hosted there retains its own catalogue id when explicitly
named. Unknown catalogue years (`[]`) never exclude a source from planning.
