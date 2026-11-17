---
name: wide-hypotheses
description: After a load-bearing zero or a broken line, ask what people did instead of what we searched for, which paper that left, and plan cheap mass tests of every trace.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-WIDE-HYPOTHESES
PURPOSE: Turn an honest "not found" into weighted behaviour hypotheses, each with a located paper trace and a cheap test, instead of a dead end or a guess.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- the generator starts only from a read coverage map; a zero without coverage goes back to collection [review: cold reviewer]
- every hypothesis names its historical ground, its paper trace and who can test it; a low weight never removes a cheap test [review: cold reviewer]
- a test outcome is classed as no record, no coverage or a faulty search before any weight moves [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-RESEARCHER (wide hypotheses mode)
- MOD-RESEARCH-PACKET (fingerprint, coverage and anomalies)
- MOD-INSTANCE-PACKS (chronicle and source classes of the place)
- regions/questions.json (RP-65)
- method/rules/catalog.toml (CRAFT-WIDE-HYPOTHESES)
:END_MODULE_CONTRACT
-->
# Wide hypotheses

A collector says honestly "not in these books"; the one who composes weighs
what there is. Neither asks what people did instead, and what paper that
left. This pass does, by system: list behaviours, find each one's trace, test
the traces in bulk. An agent can hold a hundred variants where a person holds
three; here they are fates and papers, not spellings.

## When

- A load-bearing zero: a collector returned "not found" for a link the story
  stands on (a baptism, a marriage, an adult fate) and its coverage was read.
- A broken line: a person vanishes, births have a gap, a record turns up in a
  foreign parish, faith or country.
- Before letters to archives, so one letter closes several questions.
- Not at the start: without coverage it invents what the first index holds.
  Not after every zero. A small question the composer may run alone.

## Input

1. The question in one sentence and what the story loses without an answer.
2. The family fingerprint: parents and children with dates, godparents,
   neighbouring families (CRAFT-IDENTITY-BY-FAMILY-SET).
3. The coverage map: what was read, the years each source really holds, where
   the zero is and what lies outside coverage. No map: return to collection.
4. The chronicle of the place and decade: closures of churches, faith laws,
   wars, borders, resettlements, economy, distances to the nearest centres.
   Ask the region pack RP-65; a missing answer is a gap to report.
5. Anomalies from collection: a record in another parish or faith, margin
   notes, repeated names, breaks in numbering or years.
6. The source catalog and limits: free only, which logins the host holds,
   what is already ordered.

## Generate

Work without sites: open a page or two only to confirm a source exists.
Go wide first and censor later. For each behaviour below ask whether it fits
this place, decade and family, and keep every fitting one.

| Behaviour | What to consider |
|---|---|
| Faith and power | a church closed or handed to another confession; formal conversion under pressure; mixed marriages required in a foreign church; secret sacraments with no entry; late baptisms and returns after a toleration law; walking to a priest of one's own rite elsewhere |
| Distance and money | the nearest open church against the market town; marriage in the bride's parish; godparents from another parish; seasonal work, service in town; emigration and return |
| The state | conscription and service; war and flight; occupation; border change; repatriation and population exchange; deportation, arrest, rehabilitation; land reform, consolidation, collectivisation; passports |
| The family | widowhood and remarriage; children of a first marriage under shared memory; birth out of wedlock and legitimation; a dead child's name given to the next; a married or double surname; a surname reshaped by another language |
| How the record was made | the scribe's language and ear (CRAFT-NAME-BY-EAR); indexer misreadings (w/n/m/u, S/L, case endings); old and new calendar; entry in a later year; a lost book and its second copy; late supplementary entries; a court finding of birth |

For each hypothesis find its trace: which document, who kept it, where it is
today (country, archive, series), whether an open index or scans exist and
who can open them. Look beyond registers:

| Source class | Examples |
|---|---|
| Church | consistory second copies; neighbouring parishes and other confessions (CRAFT-NEIGHBOUR-PARISH); pre-marriage inquiries; parish household lists; conversion lists; deanery reports and visitations; diocesan yearbooks showing where a closed parish was attached; burial books |
| State | revisions and censuses; household and conscription lists; residence books and voter lists; passport files; civil registration from its legal start; courts, notaries, probate; land books; village household books |
| Army | conscription lists, personnel files, award papers (age, father), loss lists, captivity |
| Repression | investigation files (parents, siblings, addresses), deportation lists, rehabilitation |
| Movement | passenger lists and the contact left at home; consular books; naturalization; evacuation and repatriation lists; refugee and displaced-person files |
| Local | school books, cooperatives, newspapers (local, emigrant, diocesan), address books, cemetery registers and photo projects |
| Open today | public trees, genealogy forums, volunteer indexers (they know where an index came from), local historians, books of memory; logins and personal accounts are the host's |

## Output

1. Hypotheses: what people did and why, the ground (history of the place, a
   neighbours' pattern), a weight; the block sums to one with "other".
2. A trace per hypothesis, located as above.
3. Crossing papers first: one paper testing several hypotheses or people.
4. A plan ordered by cheapness times story shift, with an executor per row:
   agent now, host (login, captcha, family papers), archive letter. Each row
   states before execution what counts as found, as not there, as outside
   coverage and as a search that could not have found it.
5. Name forms along the way: by the scribe's ear and by indexer misreadings.
6. Questions to relatives within the witness horizon (CRAFT-PROBABILISTIC):
   not "where was grandfather baptised" but "is there a certificate, a
   letter from abroad, a paper at home".
7. Interest: which hypotheses give a scene if confirmed (CRAFT-INTEREST).

## Test and cycle

The generator does not test. A collector runs the cheap layer literally, with
coverage. Before a weight moves, class each zero:

| Zero | Meaning | Next |
|---|---|---|
| no record | the source holds the years and was read whole | lower that hypothesis |
| no coverage | volume, years or entry numbers are missing | the gap itself is the find: seek the second copy or archive |
| faulty search | a filter, required field, result cap or role mix-up could hide the record | test the search with a known record, then repeat |

A strict reviewer checks facts, not boldness: does the series, collection or
index exist, is it really open and free, is a reference invented. A weak but
cheap idea keeps its place. The composer then reweighs, chooses letters and
host questions, and calls the generator again only if the load-bearing zero
remains. A narrowed question (one volume, one year, missing entries) is
progress even without the person.

## Engine commands

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | resolved rules for the current role | present |
| `familiar research packet` | fingerprint, coverage, anomalies and omission manifest | present |
| `familiar pack ask` | place and decade answers by RP id | present |

## Ask the region pack

- RP-65: Which events of this place and period (church closures and transfers, faith laws, wars, border changes, resettlements, lost or relocated books) moved where people took their acts and papers, and where are those papers kept today?

## Handoff

Hypotheses with weights and grounds, traces, crossing papers, the plan with
executors and outcome classes, name forms, witness questions, interest marks.
Include what was wrong in the brief and the tools.
