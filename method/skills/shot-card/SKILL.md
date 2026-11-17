---
name: shot-card
description: Stage one minute of an approved scene as a shot card a generator cannot misread, with daily life asked of the region pack by question.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-SHOT-CARD
PURPOSE: Let a shot director of any family turn a scene into a card that leaves the generator nothing to guess, while the region's daily life stays in its pack.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- the meaning sentence is written before the passport, the staging and the prompt, and without it the card stops [review: cold reviewer]
- who may stand in the frame is decided from the tree for the scene's year before any face, reference or prompt, and a person not known to be alive is left out [review: cold reviewer]
- every face in the card names one declared face source, and no source admits a photograph of a living person or a child [review: cold reviewer]
- each pack answer becomes one of four declared marks, and a mark below likely never puts an unusual visible thing in the frame [review: cold reviewer]
- daily life is asked of the region pack by registered question, and an unanswered question is reported as a gap of the pack [review: cold reviewer]
- the prompt is assembled from the card after the staging, and the object list is closed [review: cold reviewer]
- the example card is a scene of the demo feed with people of the demo family [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-SHOT-DIRECTOR (names this skill as its work)
- MOD-SKILL-DRAWING (reads the card this skill writes)
- regions/questions.json (RP-31 to RP-38)
- regions/CONTRACT.md (Q8: daily-life reference read by question)
- method/rules/catalog.toml (rules the skill relies on without restating)
:END_MODULE_CONTRACT
-->
# Shot card

A list of people and things is not a shot: a generator arranges them
prettily, under golden light, with props for comfort. The card is direction:
who came to whom, where each looks, what hour and season, what is not there.

**Inputs:** the page with "More", its scenario row and notes, the character
sheet, the tree, the region pack, the feed's style.

**Output:** one card per scene next to the feed (form below); new facts of
daily life as one-line proposals to the pack's keeper.

## Engine commands

Commands marked *planned* are not in the engine yet. Until they are, do the
same by hand from the files named in the brief, or with the host's tool for
it, and say which in your report.

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | the resolved rules and settings of this feed, for the role `shot-director` with `--feed <id>` | present |
| `familiar feed pages` | the chapter as a page: text, "More", children's layer, pictures with captions | present |
| `familiar tree person` | one person: dated facts with provenance, versions with weights | present |
| `familiar pack ask` | a numbered region question answered for a country and year, or the declared gap | present |
| `familiar research sky` | sun and moon for a date, hour and place: side of dawn, height, phase | planned |
| `familiar feed card` | a card checked against its form: meaning present, people alive on the scene's year, face sources declared, objects closed | planned |
| `familiar feed accept` | the stage `cards` marked passed for current chapters | present |

## Order

1. **Pick the minute.** Read the page aloud and choose one minute with a turn
   in it: the ticket already unfolded, the letter already torn. For a scene
   only proposed, two questions are enough: would a child understand it
   without a caption, and does anything visible break today's picture of the
   past? If it does, take the clearer variant of the scene.
2. **Meaning in one sentence:** what a child grasps in two seconds and the one
   sign that shows it. No sentence, no card: go back to step 1.
3. **Who may be there.** For each person the page puts in the minute, run
   `familiar tree person` and write: alive on the scene's year or not, age
   counted from birth or baptism (an age from a death record is checked
   against the births of children), and whether custom let them be present.
   Unknown whether alive means out of the frame. Nobody is added for company:
   a crowd is strangers.
4. **Faces.** Each person in the card gets one face source:
   - `invented` — an ordinary face, consistent with the character sheet;
   - `described` — a text of features written by an agent; the photograph it
     came from stays outside the generator;
   - `photo-of-deceased` — only when the setting allows it and the family
     archive records the rights;
   - `turned` — back, profile at a distance, silhouette: the default for
     people within living memory.

   A photograph of a living person or of a child is never a face source.
5. **Passport.** Write ten to twenty lines of what will be visible, each with a
   mark (below). Ask the pack only for what is still missing, by question:
   dwelling RP-31, dress RP-32, harness RP-33, objects and light RP-34,
   settlement RP-35, authority RP-36, customs RP-37, what drawings get wrong
   RP-38. Compute the sky for the date with `familiar research sky`, never by
   eye. Page and notes disagree: a question to the lead; stage by the
   stronger support.
6. **Leave out.** A visible unusual thing enters only at `certain` or `likely`
   and the caption explains it. At `version` or `no data`: the simplest common
   solution or nothing. An unknown building: a corner or a wall.
7. **Stage from above.** Stand where the camera stands: height, direction; who
   is left, centre, right, near, far. For each person: what they look at and
   where that stands, what each hand does; a face turned to us cannot see what
   is behind it. One direction per moving group. One light: source, side,
   colour, strength, and what does not shine. Objects by name: whose, where,
   in what state, why at this hour; then "nothing else". One line of local
   custom. Counts: people, hands, animal legs, wheels. One living detail a
   child finds, with a job in the scene.
8. **Caption and original.** The caption promises only what is visible. The
   original is the chapter's real picture or record the drawing pairs with;
   none, say so.
9. **Prompt.** Assemble it from the card in the generator's language: the
   feed's style first, then hour and light, camera, people by their features,
   the closed list, what must not appear. Ask affirmatively: a ban on
   numerals still asks for a clock face with tick marks.
10. **Read the prompt as the generator would**, literally; rewrite each word
    that invites something extra.
11. **Mark.** After all cards of a wave, `familiar feed accept <feed> --stage
    cards`.

## Marks from the pack

| Pack answer | Mark |
|---|---|
| `verified`, about this place and decade | `certain` |
| `reported`, or about a neighbouring place or decade | `likely` |
| `unverified`, or reasoned from the whole | `version` |
| no answer, or a declared gap | `no data` |

A family's own paper or photograph of the scene outranks the pack and is
marked by its own strength.

## The card

Example from the fictional family:

```text
scene:     rosa-1925 / font
meaning:   the man who met the ship now holds the new baby over the water
present:   Manuel Tavares, godfather (tree: alive 1925); Amaro and Rosa,
           parents; the priest. Nobody else named.
faces:     all invented; seen at the angle of the rite, no close portraits
passport:  stone font (likely, RP-35); priest in white over black (likely,
           RP-36); women's heads covered (likely, RP-32); April daylight
           (certain: date, sky)
leave out: the torn record (it belongs to the cut-out, not the drawing)
staging:   camera at a child's height behind the front pew; font centre;
           Manuel left of it, both hands under the baby, looking down at her;
           priest right, pouring, looking at the water; parents behind
           Manuel, looking at the baby
light:     one side window left, cool spring daylight; no candles lit
objects:   font, small jug in the priest's hand, white cloth; nothing else
counts:    four adults, one baby, eight hands
detail:    Manuel's cap folded in his pocket
caption:   The godfather holds the baby over the font.
original:  the baptism record of the chapter
```

## Forks

- **A host's remark on a drawing** maps to a passport question; if none fits,
  add one to the feed's questionnaire and say so.
- **A crowd of the twentieth century:** backs and silhouettes.

## Ask the region pack

- RP-31: How was a dwelling of this place, decade and estate laid out, inside and out: entrance and passage, the stove and its place, the place of honour, benches, floor, height of the ceiling, windows, roof?
- RP-32: What did people of each estate, age and marital state wear here in this decade and season: head cover, hair and beard, outer garment, footwear, and what marked a feast, a wedding or mourning?
- RP-33: Which vehicles, harness and animals did a household here use in this decade and season, and how was each hitched and driven?
- RP-34: Which objects stood in a room of this estate here in this decade, and which light was used at which hour of which season?
- RP-35: How did the settlement, its roads, its market and its house of worship look in this year, and what was built or changed when?
- RP-36: How did an official, a soldier, a policeman or a priest look here in this year, whose portrait hung in an office, and how did a public procedure run?
- RP-37: How were everyday and ritual acts done here in this decade, who did them and who by custom stayed away: rocking a cradle, spinning, a baptism, a wedding, a burial?
- RP-38: What do drawings of this place and decade commonly get wrong, which look-alikes from neighbouring lands creep in, and what stands in their place?

The answer expected is a line per claim with its status and basis, the
decade and estate it covers, and a sample image with its licence where the
pack has one. No answer: mark `no data`, stage the simplest frame, and report
the question id as a gap of the pack, not as a fact of the card.

## In the report

Cards; questions to the lead; gaps sent to the pack; a section "What was
wrong in the brief and the tools".
