---
name: story-scenario
description: Make a family's feed in the order that works - the cast and their papers, the place as what they saw, shared events, the plan as fates, three chapters shown, then strips, the whole, joints, a reader's pass, pictures last.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-STORY-SCENARIO
PURPOSE: Let a writer with only the engine make a feed a grandparent reads with a child on a phone.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- the order starts from the cast and their papers; the place enters as what they saw (against feeds that followed a place with the family absent; not against the place) [review: cold reviewer]
- a chapter's hero is a named person of the family; a place-only chapter is short and only where no one of ours is known (against chapters about other people; not against short place chapters) [review: cold reviewer]
- a person without his paper is told by his version, its weight said once (against weights as a reason to tell the weather instead) [review: cold reviewer]
- three chapters are shown before the rest are written (against whole feeds rejected after a day's work) [review: cold reviewer]
- a shared event of the century goes to one feed's side before chapters (against sibling feeds telling one century alike) [review: cold reviewer]
- a joint between two facts is weighed like a fact (against true facts joined into an untrue claim) [review: cold reviewer]
- the measures are a guide; no step turns them into a gate (against standardised chapters) [review: cold reviewer]
- the chapter file layout is the contract between writer and mechanics [review: cold reviewer]
- the example is the invented family's [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-FEED-AUTHOR (names this skill in its scenario mode)
- MOD-SKILL-STORY-TEXT (voice, people and documents after the strip)
- method/living-history.md (what the invariants were written against)
- method/rules/catalog.toml (rules relied on)
- method/rules/settings.toml (story measures)
- docs/PRD.md#FORMS (chapter flow)
- docs/feed-studio.md (mechanics, the reader's table)
- regions/CONTRACT.md (RP-21 to RP-23 answered in a pack's answers.md)
:END_MODULE_CONTRACT
-->
# Story scenario: the method of a feed

A grandparent reads a feed with a child on a phone, about *their own
people*. Read [living history](../../living-history.md) first: each rule here
was written against one failure, and obeyed too hard brings back the one
before. A *researcher* gathers and checks, a *writer* composes, a *reader*
reads as the family will, *mechanics* (scripts) carry files into the feed.

Tools: `familiar rules for feed-author --feed <id>`, `tree person` (facts,
versions, records), `pack ask`, `pack calendar`, `feed chapters`, `feed
storyboard` (a phone-width page), `feed rhythm` (notes; counts chapters a
person of the tree opens and chapters with a cut).

## Order

1. **The cast** (researcher) -> `studio/fates.md`: who the feed follows,
   ancestors, wives, brothers, a neighbour of the yard from a version. A
   table, a row a person: years, events by papers, cuts held, the main hole.
   Then each life as dated events with the paper under each (record, line to
   cut, reading), the link's weight once; **the turns** (wanted, stood in the
   way, did); **how it was done** there and then (papers, fares, prices, the
   levy); **the neighbours** who did the same that year, on whom a guess at
   *why* stands; **the holes** and where their paper should lie; the queue of
   papers by how much life each adds. The cast's dates by year are the
   family's river: name gaps of twenty years.
2. **The place as what they saw** (researcher) -> `studio/place.md`,
   `studio/wonders.md`: coordinates; names under every authority with years;
   town, road, market, church; distances with sources. Wonders by decade
   against the cast's years: what was seen there, who of the cast meets it,
   what to show, **firm** or **to check**; peaceful ones two to one; dates in
   their calendar (RP-21); what reached a household (RP-23).
3. **The family's table of shared events** (lead, once per family, before any
   feed's chapters; each feed adds its column) -> `feeds/shared-events.md`:
   year and event (a war, the collective farm, the crossing, the sky) x feeds
   -> which hero lived it and how. Each feed takes an event from its hero's
   side; what one feed tells, another leaves out; one picture lives in one
   feed. The same years, the same honesty: an idyll here beside
   dispossession there is a lie by omission. An old line's early named people
   are heroes, not a preface.
4. **The plan as fates** (writer) -> top of `studio/chapters/README.md`: the
   seat of kinship (below); the feed in five sentences as a child retells it;
   a through-thing that opens, returns and closes; a row a chapter: whose
   fate and years, title, **the turn**, **why** (our guess and its
   neighbours), **his paper**, the wonder or custom (RP-22) that enters
   through him, game, the chapter ideas that dissolved into it. It opens with
   the surname's own root, checked in a dictionary and with the researcher.
5. **Three chapters shown** (writer, then lead): three strips of different
   fates written whole and read before the rest. A wrong direction costs a
   day; a sample, an hour.
6. **Every chapter as a strip** (writer) -> `studio/chapters/NN-slug.md`,
   below; a picture not held is a grey frame; all rough before one polished.
7. **The whole read as one** (writer) -> half a page in the README, as a
   grandparent over two evenings: wars lead a quarter at most; games vary;
   the end answers the opening; people come back. Name the weakest chapters,
   those no person of ours opens, wonders **to check** (never a fact in the
   text), lines "by general history" with nothing behind them, the paper each
   frame awaits. Hand in `studio/joints.md`: every joint sentence (below), a
   line each - chapter, sentence, the link it claims, its weight and file or
   "coincidence".
8. **Facts and joints checked, pins made** (researcher): a verdict and source
   per wonder, fact and joint, mended in the fewest words; a fact now firm is
   told more boldly. A pin: the researcher makes the record, the crop (one
   line, readable at 390 px), its reading and `cuts` entry; the writer adds
   `R:`. A real image's licence is read at its keeper (TRUST-10).
9. **A reader's pass** (one reader who wrote none of it): the whole feed in
   `feed storyboard` by the six questions of
   [feed studio](../../../docs/feed-studio.md#the-readers-pass), a table, not
   edits; the writer mends in the fewest words. Skipped only for a lone first
   page or mends with no new chapter, joint or seat.
10. **Into the feed** (mechanics): `feed chapters`, `feed rhythm`, the
    instance check; no word changes. Then the family reads the whole.
11. **Only then** drawings (`shot-card`, `drawing`), translations and the
    voice and people pass (`story-text`); made earlier, they are made twice.

## Rules that made the difference

- **His paper stands in the chapter**, a cut with its reading right after the
  paragraph that says it: the proof we did not invent him. As a rule one
  paper a chapter; a fate may take two cuts of it. Never the subject, turn or
  title: no chapter about a sheet, a scribe, a spelling or the search
  (CRAFT-DOCUMENT-SUPPORTS). A later copy confirms, never pins (DOC-10).
- **No paper of his held yet: he is still told**, by his version, the paper
  that would pin him named in "More": no paper yet is the reason to tell him
  by a version, not a reason to skip him.
  A chapter of the place alone covers only a stretch with no one of ours
  known, and is short.
- **The place is a version**: the region is fact; the village goes by its
  weight - from 0.5 fact; from 0.3 its households are told by name as who
  they were, the bridge to the family said **once** where first needed ("Our
  version is that Amaro's father came from there"); below 0.3 the region.
  Two rival places: each road is its people's true fate; the end leaves the
  choice open.
- **The family moment and the wonder are one scene**: riding home from a
  christening they see the comet; a wonder beside it is a textbook insert
  (CRAFT-EVENT-FIT).
- **A joint is a fact with its own weight.** "The same surname", "next door",
  "reached", "stayed home", "even the same name", "remember…?" join two true
  facts into a claim. Look up the weight of *that link* in versions and tree:
  none - a coincidence, said once as one, or cut; from 0.3 our version.
  Nothing "reached" a person unless a paper says so; two surnames standing
  next to each other in Amaro's ship's list do not make their bearers kin.
- **What the story may not claim**: where a person was or that he stayed,
  when the sources read whole do not name him; where the plot rests on it,
  say once that we do not know. A guess at *why*, resting on the neighbours,
  is ours and allowed.
- **The general is not a feature**: would it fit the neighbouring surname
  unedited? Then it is an aside (CRAFT-COMMON-NOT-FEATURE).
- **One seat of kinship**: the owner's, named in every plan; an in-law's line
  by first name, "Rosa, grandmother of the owner's wife" (TASTE-READER-NEUTRAL).
- **Killed neighbours, deportation, famine**: once, true, at a child's
  height, one named household and by which power; no game about harm.
- **The text tells it as it was**; doubt lives in "More", except the one
  bridge and the one "we do not know" (TASTE-NARRATOR-VOICE). Living people by
  name and kinship (TRUST-06).

## Measures: a guide, never a gate

About 200 words a chapter, paragraphs of 30-45, at most two in a row without
a look or a game, children's text about 80 words, a game every second
chapter (`story.*` settings; `feed rhythm` notes); a whole fate may need more.
A feed in perfectly even measure looks artificial: the writer decides.

## The chapter file: contract between writer and mechanics

```
# NN · Title · years
id: <stable-id, optional>
picture: <same alternatives as L>
---
T: <paragraph>
L: file=<path> | caption=<what, who made it, when>
L: placeholder | kind=<drawing|real-image|map|family-photo> | ratio=<3:2> | says=<what will be there>
R: record=<record id> | cut=<the line to show> | reading=<plain reading> | caption=<what this shows>
R: file=<path> | caption=<what it shows> | reading=<plain reading>
D: kind=<guess|find|choice|count|trace> | ask=<question> | options=<a / b / c; "-" if none; trace: A -> B -> C> | answer=<shared answer> | after=<closing line>
D: kind=choice | ask=<open question> | options=<a / b> | answers=<case for a / case for b> | after=<closing line>
---
KIDS: <children's text>
ASK: <question for the child>
MORE:
- <line>
```

As a rule one paper and five "More" lines, including "Our version:" in the
feed language. `**` in a `reading` prints as asterisks (known). Fields,
`import.json`, `mentions`: [feed studio](../../../docs/feed-studio.md).
Example: the invented family's [Ferrolho strips](../../../demo/feeds/ferrolho/studio/chapters/).

## In the report

The plan, the three chapters shown and what their reading changed, step 7's
half page and joints, the reader's table and its mends, "What was wrong in
the brief and the tools".
