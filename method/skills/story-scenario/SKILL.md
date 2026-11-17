---
name: story-scenario
description: Turn a researched line with weighted versions into a scenario: what level of story the evidence carries, whose fate, which turn, what is on screen in each chapter and what each scene stands on.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-STORY-SCENARIO
PURPOSE: Let a feed author of any family decide what story the evidence can carry and lay it out chapter by chapter before a sentence of text is written.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- the first step decides the level of the story from the evidence, before any chapter, version or window is chosen [review: cold reviewer]
- a level below a feed ends the scenario in a card or a story page, never in chapters [review: cold reviewer]
- the example scenario row carries every column, and each support names a declared kind and a strength [review: cold reviewer]
- nothing the scenario leaves out is lost: every dropped fact gets a destination [review: cold reviewer]
- a date is not called strange before the calendar and the local norm are asked [review: cold reviewer]
- the example rows are the chapters of the demo feed, so no real family enters the method [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-FEED-AUTHOR (names this skill in its scenario mode)
- method/rules/catalog.toml (rules the skill relies on without restating)
- docs/PRD.md#FORMS (versions, cases and feed forms the scenario reads)
- regions/CONTRACT.md (RP-21 to RP-23 answered in a pack's answers.md)
:END_MODULE_CONTRACT
-->
# Story scenario

A researched line is a heap of good facts. The scenario decides which of them
make a fate worth reading aloud and puts everything else one tap away. You
choose; you never bend a fact. A chapter is written only after its row here
says who the hero is, what turns, and what the scene stands on.

**Inputs:** the feed's research notes and versions, the people of the feed in
the tree, the case of the line with its story level, the records you may show,
the region pack, the feed profile (depth: a page or a saga).

**Output:** the scenario next to the feed: the level, a thread object, one row
per chapter (below), the hardship map and the list of what was not taken.

## Engine commands

Commands marked *planned* are not in the engine yet. Until they are, do the
same by hand from the files named in the brief, or with the host's tool for
it, and say which in your report.

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | the resolved rules and settings of this feed, for the role `feed-author` with `--feed <id>` | present |
| `familiar tree person` | one person: facts with provenance, versions with weights, records, case state; disagreements shown side by side, not resolved | present |
| `familiar research norm` | counts from a read-only parish or place index: weddings by month and weekday, deaths per village and year, gaps between children, who else died that season | planned |
| `familiar pack ask` | a numbered region question answered for a country and year | present |
| `familiar pack calendar` | a date in the record's calendar and today's, its weekday; requires --country and --style; reports pack context and explicit gaps for church seasons and fasts | present |

## Order

1. **Level first.** Before choosing a chapter, count the papers about the
   line's own people, generation by generation, from the case and the tree
   (`familiar tree person` for each). Read the ceiling the evidence allows by
   PROC-STORY-LEVEL and write it at the top of the scenario; a leading version
   at half or more counts as a link. Below a feed, stop
   here and make a card or a story page (below); do not plan chapters.
   Then size the story by interest (CRAFT-INTEREST): read optional
   `interest: {level, tell}` on records, versions (and single alternatives)
   and searches; `level` is 0-1, separate from weight; absent or null means
   unassessed, never zero. Carry the source ID and `tell` into the shortlist,
   check the evidence behind a collector's suggestion, never discard for low
   interest. One interesting finding is a titled micro-story paragraph, not
   chapters of funerals and baptisms; the writer's own sense of "alive" has
   been wrong about this.
2. **Fate before facts.** For each person with a paper, write one line: what
   they wanted, what they feared, what they chose. A person with no answer has
   no chapter yet: merge them into another fate or ask the lead for
   scene-support research.
3. **Find the turn.** Look for what breaks the pattern (CRAFT-ANOMALY-IS-STORY):
   a long pause between children, an age that disagrees with a baptism, a name
   that changes form, a death just before a wedding, a move. Before calling a
   date strange, ask the calendar (`familiar pack calendar`, RP-21) and count
   the local norm yourself (`familiar research norm`): how many weddings that
   month, how many deaths in that village that year. The best turns lie in
   those counts, not in the family's card.
4. **Versions as scenes.** For every open question that touches a fate, read
   its versions file. The weight of a link limits what "More" says, not the
   scene: the leading version is told as it happened (CRAFT-VERSION-SCENES).
   Two versions near equal weight may be the plot of one scene, as in the
   demo's torn place name. Write the support and its strength in the row.
5. **Windows on the world.** Give each chapter one or two windows, different
   from its neighbours': money and prices, a fair, a custom or feast, a craft,
   the ruler or an official, a famous neighbour, a road or a machine, school,
   faith, a book or film the readers know (CRAFT-HOOKS-FAMILIAR; the readers'
   hooks come from where the family's readers live, not from the region). Ask
   the pack for the daily life of that place and decade (RP-22) and for the
   events that reached a household there (RP-23). Check every meeting of a hero
   with a great event against the table of ages and places (CRAFT-EVENT-FIT).
6. **A thread object.** Before writing rows, choose one thing that can open and
   close the feed: a ticket, a stone, a sack, an address in a pocket.
7. **Rows.** One row per chapter (below). The title names the turn through a
   thing or a choice, never a date.
8. **Hardship map.** Mark each chapter that carries a death, a war or an
   epidemic. A run longer than `story.max_hardship_run` means one of them is
   retold through a peaceful window.
9. **Not taken.** List every fact you did not use with its destination: "More"
   of a named chapter, a tab, a branch, or dropped with a reason. Nothing found
   is lost by the scenario.
10. **Against the tree.** Compare each row with the tree. A conflict is a
    question to the lead; until it is answered, write by the stronger support.

Save new or revised weighted versions in the instance's configured versions
directory, not only beside the scenario.

## Scenario rows

Supports are of three kinds: `record` (the person's own paper), `norm`
(counted in that parish or place, with the count), `version` (weighted, and no
paper says otherwise). Strength is `verified`, `probable` or `possible`, or the
version's weight. A scene with several supports lists them all.

Example from the fictional family:

| Chapter | Hero | Wants / fears / chooses | Turn | Support | Documents | Window | For children |
|---|---|---|---|---|---|---|---|
| One word in the column of who paid | Amaro | wants work across the ocean / fears arriving with nobody / pays his own passage | the clerk writes "Self" in the column of who paid | record: passenger list line, verified | after the first paragraph: the cut-out "By whom was passage paid: Self" | a cousin's address as the only map | one small bag: what goes in it? |
| A girl from the point | Rosa | wants a home with Amaro / fears a strange town / follows him across the water | the godfather is the cousin who met the ship; her village is torn off at the fold | record: baptism certificate, verified; version: the village an hour's walk away 0.50 against the island across the strait 0.30 | after the third paragraph: the cut-out of the mother's line with the tear | a garden of kale grown as on the islands | if one end of your name were torn off, could friends guess it? |

## Forks

- **Too many good facts.** "We have it" is no reason to put a fact in; "it does
  not touch the fate" is no reason to throw it out. Change its form: what the
  hero saw, heard, carried or paid (CRAFT-WORLD-THROUGH-PEOPLE). What still has
  no scene goes to the list of what was not taken.
- **A famous namesake or a notable native of the village.** A fact about the
  surname or the place, never a hint of kinship (TRUST-04).
- **The line passes to another surname through a daughter.** End on her and her
  child; that the surname lives on elsewhere goes to "More".
- **A vivid side fate.** A branch of a few pages that returns to the main line
  (CRAFT-SIDE-AND-LENGTH), not a squeezed paragraph.
- **A weak link in the middle of the line.** Tell the leading version; write its
  support and objection in the research notes; never raise it in the tree.
- **A chapter is a chronicle of years without a choice.** Rebuild it around one
  thing a family member holds; that thing is usually the title.

## Story page

When the evidence carries a story page and not a feed, make one page and stop.

- One person or couple, one place, told as a story from firm memory and the one
  paper about them; the paper is shown and told in the text.
- One window on the world of that place and decade, from the pack.
- No chapters, no turn invented to fill a gap, no promise of a sequel. A
  scene beyond the day the paper records stands on a leading version or the
  norm of the place and says so in "More".
- "More" says what the page stands on, what is still open, and the next paper
  that would raise the line to a feed, with who could hold it.
- A card is less: facts and memory with provenance. An interesting finding
  on a card is told as its micro-story paragraph (CRAFT-INTEREST).

A story page is an honest result, not a failed feed: it names what is missing
instead of filling it.

## Ask the region pack

- RP-21: Which calendar did records of this country use in this year, how far
  did it stand from today's, and which church seasons and fasts kept people
  from marrying?
- RP-22: What did daily life look like in this place and decade for the
  question named: house, work, money and prices, road, school, faith?
- RP-23: Which events and changes of rule reached an ordinary household here in
  this decade, and in what form: a levy, a tax, a requisition, a new language
  of papers, a new border?

If the pack has no answer, say so in the report: the gap goes to the pack, not
into the scenario.

## In the report

The level and what it stands on; the rows; the list of what was not taken;
the questions to the lead; a section "What was wrong in the brief and the
tools".
