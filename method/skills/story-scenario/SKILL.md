---
name: story-scenario
description: Make a family's feed in the order that works - the cast, the place as they saw it, shared events and gestures, the plan as fates, three chapters shown, every chapter, the check, a reader as the family, one hand mending, the rough whole shown, pictures last.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-STORY-SCENARIO
PURPOSE: Let a writer with only the engine make a feed a grandparent reads with a child on a phone.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- the order starts from the cast; the place enters as what they saw (against feeds of a place without the family) [review: cold reviewer]
- a chapter's hero is a named person of the family who holds it, or the chapter merges or leaves (against chapters filled by others; not against the land, never for invented life) [review: cold reviewer]
- a feed opens and closes on people the family remembers (against possible kin taken for its own) [review: cold reviewer]
- three chapters are shown before the rest (against whole feeds rejected after a day) [review: cold reviewer]
- a shared event or gesture goes to one feed's side before chapters (against sibling feeds telling one century alike) [review: cold reviewer]
- a joint between two facts is weighed like a fact (against true facts joined into an untrue claim) [review: cold reviewer]
- a reader as the family and one hand's mending come before installing (against dead chapters that passed the check) [review: cold reviewer]
- the measures are a guide; no step turns them into a gate (against standardised chapters) [review: cold reviewer]
- the chapter file layout is the contract between writer and mechanics [review: cold reviewer]
- the example is the invented family's [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-FEED-AUTHOR (names this skill in its scenario mode)
- MOD-SKILL-STORY-TEXT (voice, people and documents after the strip)
- method/living-history.md (what the invariants were written against)
- method/rules/catalog.toml, method/rules/settings.toml (rules, story measures)
- docs/PRD.md#FORMS (chapter flow)
- docs/feed-studio.md (mechanics, the reader's table)
- regions/CONTRACT.md (RP-21 to RP-23 answered in a pack's answers.md)
:END_MODULE_CONTRACT
-->
# Story scenario: the method of a feed

A grandparent reads a feed with a child on a phone, about *their own
people*. Read [living history](../../living-history.md) first. A
*researcher* gathers and checks, a *writer* composes, a *reader* reads as the
family will, *mechanics* (scripts) carry files into the feed.

Tools: `familiar rules for feed-author --feed <id>`, `tree person`, `pack
ask`, `pack calendar`, `feed storyboard` (phone width), `feed rhythm`.

## Order

1. **The cast** (researcher) -> `studio/fates.md`, by CRAFT-RESEARCH-BEFORE-TEXT:
   a row a person (years, events by papers, cuts held, the main hole);
   **ages at each event** (a boy of sixteen at the levy is a turn,
   "registered" is not); a line for each person of the family's records
   outside the cast; each life as dated events with its paper, the link's
   weight once; the turns; **how it was done** under each scene a turn
   needs; the neighbours who did the same; the holes. Cuts come cropped to
   their line, readable at 390 px, or every writer crops them again.
2. **The place as they saw it** (researcher) -> `studio/place.md`,
   `studio/wonders.md` (CRAFT-RESEARCH-BEFORE-TEXT, CRAFT-EVENT-FIT): dates
   in their calendar (RP-21), what reached a household (RP-23).
3. **Shared events and gestures** (lead, once per family, before any
   chapters; each feed adds its column) -> `feeds/shared-events.md`: year,
   event or gesture (a war, the collective farm, a wife waiting for letters)
   x feeds -> whose side. What one feed tells, another leaves out: one
   gesture in two feeds reads as one story told twice. One picture, one
   feed. An idyll here beside dispossession there is a lie by omission.
4. **The plan as fates** (writer) -> top of `studio/chapters/README.md`: the
   owner's seat of kinship (TASTE-READER-NEUTRAL); the feed in five
   sentences as a child retells it; a through-thing that opens, returns and
   closes; a row a chapter: whose fate, title, **the turn**, **why** (our
   guess, its neighbours), **his paper**, the wonder or custom (RP-22),
   game; then **waiting for a paper**: who has no chapter yet and what would
   give him one. After the surname's root the feed **opens and closes on
   people the family remembers**, however better-papered the older ones:
   possible kin stand inside, named so at once, or the reader takes them for
   his own great-grandparents.
5. **Three chapters shown** (writer, then lead): three strips of different
   fates written whole and read before the rest. A wrong direction costs a
   day; a sample, an hour.
6. **Every chapter as a strip** (writer) -> `studio/chapters/NN-slug.md`,
   below; a picture not held is a placeholder that describes the frame; all
   rough before one polished.
7. **The whole read as one** (writer) -> half a page in the README, as over
   two evenings: wars a quarter at most; games vary; the end answers the
   opening; the weakest chapters; wonders **to check**. `studio/joints.md`:
   a line per joint sentence (below) - chapter, sentence, link, weight and
   file or "coincidence".
8. **Checked and pinned** (a researcher who wrote none of it): facts and
   readings mended in the fewest words, a firm fact told more boldly;
   groundless joints and doubts of staging go to the writer as a list. His
   brief names the scene as not his ([living history](../../living-history.md#by-role)):
   so named, the line held across whole feeds. A pin: record, crop, reading,
   `cuts` entry; the writer adds `R:`. A licence is read at the keeper (TRUST-10).
9. **A reader as the family** (who wrote none of it): the whole in `feed
   storyboard`, by [feed studio](../../../docs/feed-studio.md#the-readers-pass),
   a table, not edits. The check does not replace it: in the first whole
   feeds, each checked, it found a dead chapter in each. Skipped only for a
   lone page or a mend with no new chapter or joint.
10. **One hand mends** (the writer; of several, one for the whole, the best
    chapters as the model: a second hand reads plainer). What the reader
    found alive stays word for word; the rest is mended around it. His
    remedies are advice: answer the feeling, your way if better, say where.
    A new fact comes from the cast and goes to a short check of the mending.
11. **Into the feed** (mechanics): `feed chapters`, `feed rhythm`, the
    instance check; no word changes. **The family reads the rough whole**,
    described frames, nothing drawn: enough to judge, and the first showing.
12. **Only then** drawings (`shot-card`, `drawing`), translations and the
    voice and people pass (`story-text`); made earlier, they are made twice.

## Rules that made the difference

- **His paper stands in the chapter**, a cut with its reading right after the
  paragraph that says it: the proof we did not invent him. As a rule one
  paper a chapter; a fate may take two cuts of it. Never the subject, turn or
  title: no chapter about a sheet, a scribe, a spelling or the search
  (CRAFT-DOCUMENT-SUPPORTS). A later copy confirms, never pins (DOC-10).
- **Without his paper he is still told**, by his version, the paper that
  would pin him named in "More", while he holds his chapter. Where a
  neighbour's memory, the place or the war fills it, he has left it: merge it
  into its neighbour or take it off; he and what we seek stay in "More"
  there or under "waiting for a paper". Not against the land in chapters
  that live; never padded with invented life. A chapter of the place alone
  only where no one of ours is known, and short.
- **The hero** is of the tree or tied at 0.3 and more. A namesake below it
  stands by name as a neighbour in another's chapter, never kin, never a
  hero; his paper may go to "More".
- **The place is a version**: the region is fact; the village from 0.5 fact;
  from 0.3 its households told by name, the bridge said **once** ("Our
  version is that Amaro's father came from there"); below 0.3 the region.
  One "our version" a link and one in a chapter's text; a second goes to
  "More". Two rival places: each road is its people's true fate; the end
  leaves the choice open.
- **A joint is a fact with its own weight.** "The same surname", "next door",
  "reached", "stayed home", "remember…?" join two true facts into a claim:
  look up *that link's* weight; none - a coincidence said once, or cut; from
  0.3 our version; along a chain the weights multiply. Nothing "reached" a
  person unless a paper says so; two surnames side by side in Amaro's ship's
  list are not kin.
- **What the story may not claim**: where a person was or that he stayed,
  when the sources read whole do not name him; where the plot rests on it,
  say once that we do not know. A guess at *why*, on the neighbours, is ours.
  A hero with no choice (a child driven away): the turn is what he did inside
  what was done to him, what he held on to, how he came back; the guess is
  at *how*, on neighbours of the same road; with none, we tell what we hold.
- **Killed neighbours, deportation, famine**: once, true, at a child's
  height, one named household and by which power; no game about harm.
- **The text tells it as it was**; doubt lives in "More", except the one
  bridge and the one "we do not know" (TASTE-NARRATOR-VOICE). Living people by
  name and kinship (TRUST-06); not known dead counts as living, and "ask
  grandmother" is written only where the family said she lives.

## Measures: a guide, never a gate

About 300 words a whole fate, fewer a short chapter; paragraphs of 30-45, at
most two in a row without a look or a game, children's text about 80 words,
a game every second chapter (`story.*` settings, `feed rhythm`). Even
measure looks artificial: the writer decides.

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
R: file=<path> | record=<record id> | caption=<what it shows> | reading=<plain reading>
D: kind=<guess|find|choice|count|trace> | ask=<question> | options=<a / b / c; "-" if none; trace: A -> B -> C> | answer=<shared answer> | after=<closing line>
D: kind=choice | ask=<open question> | options=<a / b> | answers=<case for a / case for b> | after=<closing line>
---
KIDS: <children's text>
ASK: <question for the child>
MORE:
- <line>
```

As a rule one paper and five "More" lines, including "Our version:" in the
feed language. Fields,
`import.json`, `mentions`: [feed studio](../../../docs/feed-studio.md).
Example: the invented family's [Ferrolho strips](../../../demo/feeds/ferrolho/studio/chapters/).

## In the report

The plan, the three chapters shown and what their reading changed, step 7's
half page and joints, the reader's table and the mending ledger, "What was
wrong in the brief and the tools".
