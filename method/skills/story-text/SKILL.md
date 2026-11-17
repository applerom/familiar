---
name: story-text
description: Write chapters from an accepted scenario: a voice that tells rather than argues, documents that support the scene instead of being retold, versions as scenes, a children's layer, and "More" for everything else.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-STORY-TEXT
PURPOSE: Let a feed author of any family turn scenario rows into pages that read aloud as a story while every scene keeps its support one tap away.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- a chapter is written from its scenario row, and the order reaches documents only after the row and the first draft [review: cold reviewer]
- a frame counts as read only when the author looked at the image of the cut-out; a placeholder is not a reading [review: cold reviewer]
- every rewrite example puts a person who acts in place of a record, a reference or an investigator [review: cold reviewer]
- the children's layer follows the feed's setting, for each of its values [review: cold reviewer]
- the order ends with checks, a waiver with a reason for a finding that would worsen the text, and a stale mark on the reading stage [review: cold reviewer]
- every rewritten sentence is taken from the demo feed's text [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-FEED-AUTHOR (names this skill in its text mode)
- MOD-CHECKS-CLI (the check the order runs)
- MOD-FEED-CLI (person, doc, status and build commands the order names)
- method/rules/catalog.toml (rules the skill relies on without restating)
- docs/PRD.md#FORMS (chapter and feed document forms the text fills)
- regions/CONTRACT.md (RP-22 answered in a pack's answers.md)
:END_MODULE_CONTRACT
-->
# Story text

The scenario already chose the hero, the turn and the support. Your job is the
voice: a page a parent reads aloud without stumbling and a child follows to
the end. The story stands in the text; what it stands on waits in "More".

**Inputs:** the scenario, the research notes and versions of the feed, the
records and their images, the region pack, the resolved rules of the feed.

**Output:** chapters in the chapter form (text, "More", children's layer,
records and their place in the flow, facts, variants, places) and the feed's
document entries.

## Engine commands

Commands marked *planned* are not in the engine yet. Until they are, do the
same by hand from the files named in the brief, or with the host's tool for
it, and say which in your report.

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | the resolved rules and settings of this feed, for the role `feed-author` with `--feed <id>` | present |
| `familiar pack ask` | a numbered region question answered for a country and year | present |
| `familiar feed person` | a person of the tree placed in the feed: symbol, names in the feed's languages, no duplicates; takes a name form with `--name` where it cannot derive one | present |
| `familiar feed doc` | a cut-out and the full sheet cropped from a record's image and entered in the feed's documents with the reading you give; it never reads the frame; use --index READING --source SOURCE --where LOCATOR for an index without an image | present |
| `familiar feed check` | mandatory data findings and advisory text cues; `--text FILE` checks a chapter draft outside the feed using this family's settings, with no publication verdict | present |
| `familiar rules waive` | an exception for one rule and scope, with its reason | present |
| `familiar feed status` | per stage, the chapters whose input changed since it was accepted, and the next step | present |
| `familiar feed build` | the feed built into the reader's catalogue, stopping on an unresolved person or document | present |

## Order

1. **Settings.** Run `familiar rules for feed-author --feed <id>` and note
   what shapes the page: reader age, `kids.layer`, name form, frames per
   chapter, number density.
2. **The row.** Take one chapter's scenario row. Reread the last paragraph of
   the chapter before it: the two must read as one.
3. **First draft from the row.** Open on the hero and what they care about, not
   on the village or the year. Keep the page on one choice: the set-up, the
   turn the row names, what follows, and a last line that pulls to the next
   page (CRAFT-ARC). Write the leading version as it happened; two versions of
   near equal weight become the plot of one scene, as in the demo's chapter
   with the torn place name.
4. **Documents.** Only now place the records the row names. Enter each with
   `familiar feed doc`, then read the frame yourself on the image of the
   cut-out it made. If a tool returned a placeholder or an error instead of
   the image, the frame is not read: say so and do not write its reading. Find
   the one visible detail that turns the scene and tell it with the words and
   numbers on the cut-out; place the cut-out right after that paragraph. A
   phrase of the paper a reader cannot follow is explained in one sentence by
   what it meant for the person, or left out. A record you have only from
   an index appears as its index entry, never as a cut-out (TRUST-01).
5. **World through people.** Every paragraph of history is retold as what
   someone of the family saw, heard, held or paid (CRAFT-WORLD-THROUGH-PEOPLE).
   For the daily detail of a scene ask the pack (RP-22), only for the part the
   scene needs.
6. **Memory.** Tell family memory as a story in plain words, without naming
   who remembered it and without adding what the family did not say. Where a
   paper disagrees, the text follows the version research accepted and "More"
   says the difference (CRAFT-FAMILY-WORD-WEIGHT).
7. **Words.** Read each sentence as the reader age in the settings would hear
   it: a word the child has not heard is replaced, a period word stays only
   when the scene needs it and is explained in the same sentence, a rare word
   is checked in a dictionary of the language before it is kept, and every
   action has someone who does it.
8. **"More" per scene.** A short list: what the papers say, what was
   reconstructed and on what, how strong it is in plain words ("about one
   chance in two"), where the pictures come from, what is still missing.
9. **Children's layer** by `kids.layer`. With `block`: the block TASTE-KIDS
   describes, written last, when the page is final, and tried on the page: can
   a child answer and find everything without another page? With
   `separate_text`: a shorter text with the same meaning, nothing added. With
   `none`: no layer, and the page still has to read aloud to a child.
10. **People.** Place every person the chapter names with
    `familiar feed person`; never type a name form by guess.
    Divide narrative into `prose` blocks with explicit `people`. A protected
    block disappears quietly for readers; optional `otherwise: {people: [...],
    text: ...}` is your own alternative and obeys the same permissions.
    Places and other nested passages can declare their own `people` so an
    unrelated protected person does not remove them with the rest of a chapter.
11. **Checks.** Run `familiar feed check <feed>`. Fix what is right. A finding
    that would make the text worse is answered with
    `familiar rules waive <rule> --scope <chapter> --reason "..."`, and a check
    that is wrong goes to the report (PROC-CHECK-SERVES-STORY). This includes
    dictionary cues attached to trust rules; their dismissal cannot waive data
    guarantees or the independent reading. For a draft not in a feed yet, run
    `familiar feed check --text FILE` with the family root selected.
12. **Read aloud and hand on.** Read each page aloud once as a parent and once
    as a child: who is the hero, what did they want, what happens next? Build with
    `familiar feed build` and look at the page as the reader will. A new or
    renamed chapter leaves the reading stage stale: confirm it with
    `familiar feed status` and say so when you hand on.

## Rewrites

Typical first drafts and what they become. From the fictional family:

| Before | After |
|---|---|
| The passenger list of 1921 records that the passage was paid by the passenger himself. | On the ship's list, in the column that asks who paid, the clerk wrote one word: Self. |
| Apparently the godfather was the same cousin, but we cannot be sure. | The godfather held the baby over the font. It was Manuel Tavares, the same cousin whose address Amaro had carried across the ocean four years before. |
| The certificate states the mother's birthplace as "Ponta d" with the rest illegible. | For Rosa: Ponta d... and there the paper is folded, and along the fold it tore. |
| Mill towns of the region employed large numbers of island immigrants in this period. | For the next forty years the cotton mill was his day. |

The doubt in the second line does not vanish: it moves to "More" as a plain
sentence about how likely the godfather is the cousin.

## Forks

- **The draft translates the document paragraph by paragraph.** Stop. Keep the
  one detail that turns the scene; the rest of the reading lives under the
  cut-out and in "More" (CRAFT-DOCUMENT-SUPPORTS).
- **The scene needs more than its support carries.** Tell it with its weight in
  "More", or ask the lead for scene-support research. A paper is never
  invented to fill the gap.
- **A sentence explains how we know.** "The record says", "it turned out",
  "we do not know": give the act to the person ("he told the priest") and the
  reasoning to "More".
- **A hard page.** Keep the loss in the scene and leave out the detail that
  wounds; TASTE-KIDS and TASTE-HARDSHIP-DENSITY set how much.
- **A check and the story disagree.** The story wins; the waiver carries the
  reason, the same move (step 11).

## Ask the region pack

- RP-22: What did daily life look like in this place and decade for the
  question named: house, work, money and prices, road, school, faith?

If the pack has no answer, say so in the report: the gap goes to the pack, not
into the text.

## In the report

The chapters written; the waivers with reasons; frames not read and why;
questions to the lead; a section "What was wrong in the brief and the tools".
