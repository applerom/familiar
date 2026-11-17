---
name: branch-abroad
description: Trace a possible emigrant across name changes and record systems by testing a bridge between departure and arrival families.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-BRANCH-ABROAD
PURPOSE: Distinguish a cross-border family continuation from overseas namesakes using paired record systems and a bounded bridge test.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- disappearance alone cannot establish emigration and a changed spelling alone cannot identify the arrival person [review: cold reviewer]
- candidates are compared on household and route fields rather than a surname hit count [review: cold reviewer]
- missing access changes the next source move without becoming negative evidence [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-RESEARCHER (case mode)
- MOD-RESEARCH-PACKET (primary family inputs)
- MOD-SOURCE-SEARCH (host authorization and journal coverage)
- MOD-INSTANCE-PACKS (departure and arrival knowledge)
- regions/questions.json (RP-61, RP-62, RP-63)
- docs/PRD.md#SOURCE-SEARCH (capture replay is not live search)
:END_MODULE_CONTRACT
-->
# Branch abroad

Inputs: departure person and household, known anchor records, possible route and
arrival country, case question, previous coverage and a budget. Output: compared
arrival candidates, the name bridge, relatives with separate weights, actual
coverage and a distinguishing next record. Story writing follows this pass.

## Order

1. Recover the family packet and earlier card notes before selecting a country.
   Separate left home, crossed a border, settled abroad, returned and unknown.
   Disappearance from a local index alone does not establish emigration: compare
   its coverage with death, internal migration and missing-book alternatives.
   Record the supported departure/arrival interval; a named destination or a
   linked overseas family makes a testable route, not an accepted identity.
2. Ask departure and arrival packs RP-61 and RP-62 for the relevant years, and
   RP-63 for language/script changes. The method chooses which observation
   distinguishes candidates; packs supply source classes, custody, fields,
   variants, calendars and access. Source websites and recipes stay in packs.
3. Build a variant ledger: literal source form, script, suggested search form,
   transformation and supporting locator. Transliteration, phonetic spelling,
   shortened names, married names and translated given names are search leads.
   Do not assume a changed spelling proves a legal name change, or that every
   immigrant changed a name. A document giving both forms is a strong bridge;
   otherwise compare households across records. Preserve each literal spelling.
   Add forms written by ear: for each leg of the route name who held the pen
   (parish priest, imperial clerk, shipping agent, border officer) and that
   scribe's language and script, then write the name, surname and village as
   that scribe would have heard them. A village no one outside its language
   could spell is found only this way. Add each such form, and every new form
   met in a hit, to the family's variant file as unverified with whose ear it
   assumes or where it was seen; being unverified is a mark, not a reason to
   leave it out (CRAFT-NAME-BY-EAR). A record found through it is one more
   grain, and a matching set of family names beside it makes it strong.
4. Compare candidates in a large destination population using these fields:

   | Field | Comparison |
   |---|---|
   | Birth date or age interval | Event type, precision, calendar and contradictory dates |
   | Birthplace and jurisdiction | Historical place forms and administrative changes |
   | Parents, including mother's birth surname | Compare the pair and source lineage, not a guessed patronymic |
   | Spouse, previous spouse and children | Whole household fingerprint across years; allow remarriage and stepchildren |
   | Arrival route and chronology | Port, last residence, destination and return journeys |
   | Address, occupation, contact or sponsor | Historical ties that distinguish namesakes; a neighbour is not automatically kin |

   Separate observation, locator, dependency group, match/conflict and missing
   field. Copies of one original add no independent bridge. A rare surname may
   justify a bounded surname-only pass; inspect the reported size first. A common
   one needs family/place/date constraints, not an unbounded list of bearers.
5. Test search behaviour with a known record before trusting a zero. Use the
   host-authorized source adapter and pack recipe for one bounded query at a
   time; journal exact forms, country/years and index coverage actually read.
   Keep a later name together with the birth name in searches. If an aggregator
   closes a record, try the original publisher through its allowed route; if a
   site refuses access, continue another permitted source or local comparison.
6. Test both ends of the proposed bridge. For a spouse, compare parents, siblings
   and earlier marriage before absorbing children with a different surname.
   Compare arrival parents phonetically with departure households and their
   full set of children. A sponsor, neighbour or obituary relative can supply
   a distinguishing field, but its relationship needs its own assessment.
   Keep living relatives at the permitted name/kinship boundary; a historical
   address is a research discriminator, not a reason to investigate living people.
7. Decide per axis: arrival identity, spouse, child, death and burial need their
   own status and support. Reweigh versions including unknown; a country's
   migration pattern supplies context, not identity. Pick the cheapest record
   separating the remaining candidates, with positive, contrary, unreadable and
   unavailable outcomes before execution. Stop at the case budget. Leave open
   for a next test within budget, waiting for a named access/paper, review when
   exhausted, or closed with an outcome. No hit or route refusal settles no
   event unless the relevant coverage was actually read.

## Engine commands

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | resolved researcher obligations | present |
| `familiar research packet` | original family testimony, records and omission manifest | present |
| `familiar tree person` | card and linked research for one candidate | present |
| `familiar pack ask` | country/year-scoped pack answers by RP id | present |
| `familiar search query` | proposed unified live source query through host permission; not built | planned |

The engine has a source-search API and a captured-response replay adapter.
Live network/browser access is supplied by an authorized host, never inferred
from the replay tool. If absent, compare saved records and report that access gap.
Persist family proposals only through `instance.writer.mutate` via the host.

## Ask the region pack

- RP-61: Which departure, arrival, naturalization and return records cover these countries and years, where are they kept, and which route is free and accessible?
- RP-62: Which fields in destination censuses, vital records, applications, obituaries and burial records distinguish birth families, previous marriages and overseas relatives in this period?
- RP-63: Which name and place variants, script conversions and jurisdiction changes must be tested between departure and arrival records, without treating a spelling as identity evidence?

Ask each side about its own territory and period. An unanswered pack question
is a gap to report, not a national recipe to invent in this skill.

## Handoff

List questions answered, literal/new forms and transformations tested, candidate
table, chosen bridge and objections, independent support, coverage, state,
spent budget and next record. Include what was wrong in the brief and the tools.
