---
name: memory-first
description: Start a line that rests on living memory and home papers, people born roughly 1900-1960, often townspeople, with no parish registers open to search.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-MEMORY-FIRST
PURPOSE: Take a line that has only living memory and home papers through a first pass that ends in a named paper and weighted versions, with namesakes kept as separate weighted family sets rather than a pile or a stop.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- the order names one bridge paper and drafts its request before any step that queries an index, a database or the web; waiting for the paper never pauses the names-only pass [review: cold reviewer]
- the names-only pass is bounded, keeps every namesake in a separate family set with a weight, what matches and what diverges, and never merges sets; a possibly living person carries only name and kinship [review: cold reviewer]
- every line question names the paper that settles it [review: cold reviewer]
- a request to relatives carries our version, exactly one paper, an outcome for each possible answer, an addressee who can hold the paper and a state [review: cold reviewer]
- every way out of a pass leaves the case in a declared state; there is no "nothing found" exit [review: cold reviewer]
- examples come from a fictional family [review: engine lead]
CHANGES_WITH:
- MOD-ROLES-RESEARCHER (names this skill in its case mode)
- method/rules/catalog.toml (rules the skill relies on without restating)
- docs/PRD.md#INSTANCE (request record and case states, proposed shape)
:END_MODULE_CONTRACT
-->
# Memory first

Record document spellings literally; the memory intake agent never chooses the clan's display surname or substitutes it into a person's display name.

One family paper that records kinship is worth more than a hundred surname
queries: the web gives namesakes, the bridge is a paper. This skill gets to
that paper, keeps the case honest meanwhile, and turns namesakes into
weighted family sets instead of noise or a stop.

**Use it when** the line has no parish with continuous registers and no
record older than the twentieth century; with a parish and an anchor record
use `research-versions`; a found village switches there (step 7).
**Inputs:** the line's people with provenance, the case file, the family's
answers so far, the region pack.

## Line questions

Four questions; open one weighted version set per question at once,
including "somewhere else" and "unknown" (CRAFT-PROBABILISTIC).

| Question | Paper that settles it | Fallback paper |
|---|---|---|
| who: full name, patronymic or middle name, year of birth | birth certificate of a child, which names the parent | military or service book; work-record book |
| where from: place of birth, parents | the person's own birth or marriage record; personnel file at the workplace | military book (place of call-up); death certificate |
| who the wife or husband was before marriage | marriage certificate | the spouse's own birth certificate; the gravestone |
| death and grave | death certificate | a photo of the whole gravestone; the cemetery's register |

A field is one independent fact (patronymic, year within two, place,
occupation, address, a spouse's or child's name), never a common surname
alone; weight by fields (CRAFT-WEIGHT-BY-FIELDS).

## Order

1. **Line card.** Read all the family recorded (card notes, earlier answers,
   not only the latest); an old note ("born and raised in the town") outranks
   a picture of the period. Mark each statement memory, hearsay or paper
   (CRAFT-FAMILY-WORD-WEIGHT); write weighted versions now, one axis per
   question (a patronymic apart from a year). A namesake is not a version but
   a candidate set. Marriages, divorces and deaths in the tree decide who can
   hold a paper and who can witness.
2. **Bridge paper.** Name the one paper most likely kept at home that names
   the previous generation; check what fields it carries in that period
   before promising them (RP-1).
3. **Request to the family** (below), to whoever holds the paper by step 1
   (a divorced in-law's memory and papers end at the divorce); a question
   about a person goes to someone who knew them (saw / heard / saw a paper).
   A "no" that refutes nothing never weakens a version. Firm memory limits
   by its time's rules (a status only rear workers got places the person in
   the rear): a filter once the rule is checked.
4. **While waiting: one namesake pass** (below), cemeteries and service
   files included. It runs even when the family gave only names.
5. **One bounded search per new field**, in the source class that fits it,
   once the pack confirms the index covers this place and years (RP-3); a
   zero outside coverage means nothing.
6. **Letters, last.** A letter to a registry, archive or cemetery only with
   full name, year, place and kinship; the host or relatives send it (RP-4).
   First: a living person can usually get a repeat certificate of their own
   birth or marriage, and that may be the very paper.
7. **Bridge to the village, if evidenced.** Only a recorded rural birthplace
   and continuous parish records justify switching to parish-first. Otherwise
   keep the urban route and test the parents' actual place of birth (RP-5).

## Names only: one namesake pass

Most new families start with names only (a grandparent's siblings, no dates
or papers): one pass over the period's open indexes gives the mass to weigh
(CRAFT-KEEP-THE-MASS).

1. **Fingerprint first.** The person is a set: parents, siblings, spouse,
   village or town, the patronymic the papers would carry
   (CRAFT-IDENTITY-BY-FAMILY-SET); a wide year window from the tree.
2. **Forms by ear.** Every name and surname as each scribe and indexer of the
   period would write it, in each script in use (CRAFT-NAME-BY-EAR).
3. **The pass.** The indexes the pack names for this place and period
   (RP-2, RP-3), each run once with every form over the whole window; read
   the full result list; coverage is "N of M read", zeros recorded. Service
   files only where service is likely by age and sex; a cemetery index under
   about a fifth of its catalogue gives no zero.
4. **Sets, not hits.** Hits sharing a field (father, address, village,
   unit, grave) form one candidate set with a weight by fingerprint fields,
   a line of what matches and diverges; sets stay separate, and divergence
   lowers a weight, never drops a set.
5. **The living.** Whoever may be alive, with their spouses and children:
   name and kinship only (TRUST-06).

**The pass is over** when every named index ran with every form over the
window; a second pass needs a new field. Exits are declared, never "nothing
found":

- *Versions:* each set is a row with its weight, beside "none of these" and
  "unknown"; a set at half or more is told as most likely so.
- *Relatives:* within the witness horizon (CRAFT-PROBABILISTIC), unprompted
  first: the one fact that splits the leading sets (a sibling's name, a
  town, who went to war) and the leading set's bridge paper; never
  candidates to choose from.
- *Wide hypotheses:* a load-bearing zero over read coverage goes to
  `wide-hypotheses`.

### Where a names-only search breaks

One line per lesson from live passes, with what to do instead.

- No year: run the window in slices; coverage names the slices run.
- A patronymic is a field only where the period's papers carried it (RP-1).
- Search every script the period's clerks used, not only the family's spelling: a Cyrillic form found what Latin queries missed.
- Read the source page, not the search snippet: a snippet misread a field that the published list showed plainly.
- Asking with a parent's name does not prove the parent in the result: some aggregators match on any relative and hide the fields; keep such a hit a candidate set until the record itself names the parent.
- A login or captcha flag on a page that already shows a result (including "nothing found") is a false alarm; record the result, report the flag.

## Forks

- **Common surname.** Each candidate set gets the one family paper that
  confirms or drops it; a namesake dropped by age stays an unrelated
  candidate with a kinship test, never a parent or uncle (TRUST-04).
- **Memory names two places.** Ask whether they belong to different people
  (one spouse from each) before averaging them into one version.
- **A woman of the line.** Service sources only after period, region and
  eligibility; sex alone never establishes absence.
- **No paper at home:** "not presented", never "does not exist"; the
  repeat certificate (step 6) before letters.

## Request to the family

One record per paper: the witness's question, then our version; one paper
and why; what each answer decides; an addressee who can hold it; a state
(`draft`, `asked`, `answered`, `not-presented`, `closed`). Never "everything
you have" or surnames to choose from. Shape: `familiar research form
request`; address, signature and paper guidance: `docs/PRD.md#INSTANCE`.
`outcomes` and `fallback` are for the researcher, only `host_next` for the host.

## Case states and when to stop

- `open` — a test is running. A site that refuses closes the route, not the
  person: go on by another route; repeat only with new access.
- `waiting-for-family` — no new distinguishing field after the pass; the
  next test is a named paper and the sets stay weighted versions. A new web
  series waits for a new field; the namesake pass, done once, does not.
- `bridged` — a paper recorded kinship; write the next test (next
  generation or step 7).
- `review` — the third pass left the link's status unchanged; the lead
  reviews the case before any new series.

Only what was read goes into coverage: a server answer and a loaded page are
not a read document (TRUST-05). Progress is bridges (papers in which kinship
is written) and changed weights, never the number of queries.

## What can be told already

Memory as a story, an interesting finding as a micro-story even on a card
(CRAFT-INTEREST); a place's background only on a paper, firm memory or a
version at half or more, never a surname-frequency map; the checkpoint names
the story level evidence allows (PROC-STORY-LEVEL).

## Ask the region pack

- RP-1: Which fields did birth, marriage and death certificates carry by decade?
- RP-2: Which cemetery indexes exist here, and how full is each against its catalogue?
- RP-3: Which indexes hold service, award, repression, memorial-book and
  address-book records for this place and years, and how do they read a zero?
- RP-4: Where is a civil record of this year kept now, who may request it, how long closed?
- RP-5: Where do rural parish and village-council records of this period sit; which are open?

No answer in the pack: say so in the report; the gap goes to the pack, not
into your text.

**In the report:** "What breaks the pattern" and "What was wrong in the
brief and the tools".

## Engine commands

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | resolved rules for the current role | present |
