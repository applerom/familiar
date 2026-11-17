---
name: story-reading
description: Read a built feed page by page through three readers, write each finding with its place, weight and a ready sentence, and send each finding where it belongs.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-STORY-READING
PURPOSE: Let a reviewer of any family find what a linter cannot see, a dead page, by reading each page as its readers will, and turn findings into fixes or lessons.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- mechanical checks run before any page is read, and the scenario and the author's notes are opened only after the page was read as a reader [review: cold reviewer]
- three readers are declared, each with who reads, how and what they ask, and the number used in a pass comes from the settings [review: cold reviewer]
- the example finding carries page, place, reader, weight, a ready sentence and a class, all from declared values [review: cold reviewer]
- every weight of a finding has a route, and a finding repeated across pages is classified rather than fixed page by page [review: cold reviewer]
- a page is marked read only after it was read whole with its "More" [review: cold reviewer]
- the example finding points at a page of the demo feed [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-REVIEWER (names this skill in its page-reading mode)
- MOD-CHECKS-CLI (the check the order runs first)
- MOD-FEED-CLI (the accept command that marks the reading stage)
- method/rules/catalog.toml (rules the skill relies on without restating; settings review.readers, review.readers_before_host)
- docs/PRD.md#SETTINGS (where a remark lands)
:END_MODULE_CONTRACT
-->
# Story reading

A linter passes a dead page with no findings: a retold register, a list of
years, a hero who wants nothing. Only a reader notices. You read each page as
the people who will read it, one page at a time, and write what breaks the
story where it breaks. You do not rewrite the page; you hand the author a
ready sentence.

**Inputs:** the built feed page by page with its "More", the cut-outs and
captions, the research notes and versions for facts and weights, the host's
earlier remarks on this family's feeds, the resolved rules.

**Output:** findings per page on disk, a hardship map, marks for the pages
read, and a short list of what repeats.

## Engine commands

Commands marked *planned* are not in the engine yet. Until they are, do the
same by hand from the files named in the brief, or with the host's tool for
it, and say which in your report.

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | the resolved rules and settings of this feed, for the role `reviewer` with `--feed <id>` | present |
| `familiar feed check` | mechanical findings with their mode; exit status says whether trust blocks | present |
| `familiar feed pages` | the feed as pages: text, "More", children's layer, cut-outs with captions and readings, the title plate, and which people die on which page | present |
| `familiar research vocabulary` | canonical readers, weights, classes and doubt marks from the validator schema | present |
| `familiar feed accept` | the stage marked passed for current chapters; --pages CHAPTER_ID selects reading pages; a later change makes a chapter stale again | present |

## Readers

The settings say how many readers a pass uses: `review.readers` for an
ordinary pass, `review.readers_before_host` before the host sees the feed. One
reader means the first below.

- **Parent and child.** A parent reads the page aloud to a child of the
  feed's reader age. Asks: where do I stumble, which word does the child not
  know, who did this, can the child answer the question at the end from this
  page or their own life? What will the child retell after this page? Nothing
  to retell is a `breaks-story` finding: the page shrinks to a line or merges,
  however well documented and sad it is (CRAFT-INTEREST).
- **Teenager on a phone.** Reads alone, fast, on a narrow screen. Asks: does
  this page hold on its own, who is the hero, what do they want, what turns,
  why open the next page? Does a paragraph run past the screen, does a title or
  a sentence give the ending away?
- **Picky editor.** Reads with the host's earlier remarks open as samples.
  Asks: do the facts and ages agree with "More" and the versions, does the
  cut-out show the person the caption names with the words the text uses, does
  the text claim as documented what the paper does not carry (a leading
  version told as it happened, with its weight in "More", is not that), does
  an internal key or a working note
  show, is an event told twice, do this page's end and the next page's start
  read as one?

## Order

1. **Checks first.** Run `familiar feed check <feed>`. Mechanical findings go
   back to the author before anyone reads (PROC-CHECKS-FIRST); read the rest.
2. **Pages.** Export the feed with `familiar feed pages <feed>`. From it write
   the hardship map: which page carries which death, war or epidemic. A run
   longer than `story.max_hardship_run` is a finding on the later page.
3. **Read each page whole**, with its "More", its cut-outs and its children's
   layer, once per reader of the pass. Read the last paragraph of a page
   together with the first of the next.
4. **Write each finding to disk the moment it is made** (form below), with a
   ready sentence the author can paste.
5. **Then the intentions.** Only after a page was read as a reader, open its
   scenario row and the research notes, to tell a wrong fact from a choice and
   to check a weight.
6. **Weigh and route** each finding (below). Collect what repeats across
   pages.
7. **Mark.** `familiar feed accept <feed> --stage reading` only when every page
   was read whole with "More"; otherwise list the pages read in the report and
   leave the stage open. A mark says "read", not "no findings".

A story page is stored as one element of `chapters.json`; this is the storage adapter, not a demand to write a longer feed.

`feed pages` returns gate-validated content with `output.state=clean` and input
fingerprints. To diagnose a blocked page use `feed pages <feed> --preview`:
it returns `output.state=preview` and the current trust verdict; it cannot be
used as a checked export. Refresh `feed status` before consuming a saved build;
a changed permission or restriction makes the catalogue stale and removes it.

## A finding

Canonical weights, classes and readers come from `familiar research vocabulary`
(`method/vocabulary.toml`); validate a finding with `research validate-review`.

Example from the fictional family:

```json
{
  "page": "rosa-1925",
  "where": "paragraph 3, sentence 2",
  "reader": "parent-and-child",
  "weight": "stumble",
  "finding": "'Ponta d...' read aloud is a sound, not a word; the child loses the thread at the tear.",
  "fix": "For Rosa the clerk began 'Ponta d', and there the paper is folded and torn.",
  "class": "craft"
}
```

## Routes

- `trust`: stop; the page does not go on. The lead hears it now, with the
  place and the paper it contradicts.
- `breaks-story`: the author rewrites the page from its scenario row; a page
  with no hero or no turn may go back to the scenario.
- `stumble`: the author pastes the ready sentence or writes a better one.
- `taste`: the author decides; the host's setting rules.
- **Repeated** on three or more pages: do not fix it page by page. Class it as
  PROC-REMARK-INTAKE asks: trust, craft or taste, each to its own place. A
  wrong check goes to the report.

## Forks

- **The page is clean.** Say so. Precision, not length.
- **A fact looks wrong but "More" explains it.** Not a finding of fact; maybe a
  stumble if the reader trips on it before "More".
- **You disagree with a version.** Not your call: a question to the lead with
  the paper you would check.
- **The children's question needs another page.** A finding on this page.

## In the report

Pages read and by which readers; findings by weight; the hardship map; what
repeats and where it should land; a section "What was wrong in the brief and
the tools".
