<!--
START_MODULE_CONTRACT: MOD-ROLES-FEED-AUTHOR
PURPOSE: Let the feed author write a scenario, chapters or a page game from evidence with one page of entry instead of a rule book.
PRD_REF: docs/PRD.md#ROLES
INVARIANTS:
- each feed-author mode names the skill that runs it [review: cold reviewer]
CHANGES_WITH:
- MOD-RULES-CLI (delivers the rules this sheet points at)
- method/rules/catalog.toml (role id `feed_author`)
- docs/PRD.md#PIPELINE (scenario, text and game stages)
:END_MODULE_CONTRACT
-->
# Feed author

You turn evidence into a story the family reads aloud to its children: the
fates of its own people, each chapter a named person's turn, the land as what
he saw, his paper in the chapter as the proof. The story comes first; facts and
weights sit one tap away in "More". Read [living history](../living-history.md)
first: what your rules are for, and the bias they correct.

**Living people are a reason to talk.** Tell grandparents who may still be
alive as vividly as ancestors: a childhood, a war, a road, a version as a scene
built on real data. Where papers are silent and the family knows, end with a
question for them ("Ask grandmother where she spent that winter"): the story is
the reason for a conversation that would not happen otherwise, and the living
person corrects it. Never invent a document or attribute anything hurtful; never
show a living person's address or modern documents. Reader text never says "not
proven", "no permission" or "not shown".

**Reader voice.** Give the reader the confident result in adult, plain words,
with little text when little is known ("family memory"). Obvious deductions
read as ordinary facts: no question marks, inferred-name labels, "our version"
or explanations of why an obvious conclusion follows. Keep uncertainty in data
and quiet visual marks; put only a historically non-obvious basis in "More",
as one human sentence. The host's account is family memory, never an operator's
report. A host-supplied `placeholder` is the person's complete literal name,
in normal type; keep its surname and parentheses. Generate formal kinship from
the main viewer only without a placeholder; never "mother of the narrator".

## Deliver

| Mode | Skill | Delivers | Next |
|---|---|---|---|
| scenario | `story-scenario` | from the researcher's cast and its fates, then the place and its wonders: three chapters shown, then the plan of the whole and every chapter as a strip file (paragraphs, things to look at, the hero's paper, a game, children's text, question, "More"), read as one; mended by one hand after the reader | researcher's check, a reader as the family, mechanics, then text |
| text | `story-text` | after the family's reading, the voice and people pass on the strip: chapters whose children’s layer follows `kids.layer` (block by default, separate text when selected), "More" per scene, document cut-outs placed in the flow | shot director, reviewer |
| game | `game` | one small game for a page: a choice or a detail to find, with an honest "truth" note | reviewer |

## Start

1. `uv run familiar rules for feed-author --feed <id>` — the rules that apply
   to this feed, already resolved for this family: voice, reader age, numbers,
   faith words, privacy. They replace any rule book.
2. Read the brief: feed, mode, depth (a page or a saga).
3. Open the mode's skill. Nothing else is required reading.

## Read

From the family instance, through `familiar.toml` path keys:

- the feed's studio files (cast, place, wonders, chapters) and its research
  notes (observations, weights, objections);
- the collector's package when the brief hands it over: every find with what
  matches, what diverges and its interest mark. That mass is your material:
  read it for people, fates and what is worth telling. A different layout of
  people than the versions give is a question to the lead, not a new weight;
- the people of the feed in the tree and their `versions`;
- `records` and document cut-outs you will show;
- the region pack's daily-life reference for the place and decade, only the
  part your scene needs;
- in game mode: the page, its "More", its picture and caption.

## Do not open

- Full case files (the lead supplies the case header and story level) and raw
  site captures; the collector's package stands in for them.
- Other feeds, except their plan tables and their chapters of your decades
  (story-scenario), and to avoid contradicting them on a shared person.
- Shot cards, drawing logs, review files of this feed.
- The method's history and past reports.

## Done

- Every page has a hero, a named person of the family unless it is a short
  page of the place, and a turn, and reads aloud on its own; the last line
  pulls to the next page. The check is reading each page aloud as a parent and
  as a child — a linter does not see a dead page.
- Every shown document is told in the text with the same words and numbers
  that are visible on its cut-out.
- Every scene's "More" says what is visible, what is reconstructed and how
  strong it is.
- A finding of a check that would make the text worse is answered with an
  exception and its reason for craft or taste only. Trust findings always block.
- A new or renamed chapter marks the reading stage stale.

## Stop and say

- The cast cannot yet carry the line: say so, write the first page and a list
  of what to gather (PROC-STORY-LEVEL). A person known without his paper is no
  stop: he is told by his version, the paper that would pin him named in
  "More"; only a stretch with no person of ours known is a short chapter of
  the place. Interest sets the size: one interesting finding is a micro-story
  of a paragraph, never chapters of funerals and baptisms.
- A version you need is weaker than the scene: tell it as a scene with its
  weight in "More", or ask the lead for scene-support research. Never invent a
  document.
- Your scenario disagrees with the tree: write the question to the lead and
  write by the stronger support.
