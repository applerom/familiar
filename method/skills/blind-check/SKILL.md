---
name: blind-check
description: Check a drawing as a stranger to its intent: write what the picture tells before opening anything, build the scene in space, count in full-size crops, then compare with the caption and the page and give each picture a verdict with a ready request.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-BLIND-CHECK
PURPOSE: Let a reviewer of any family see a drawing the way its readers will, with no knowledge of what was meant, so that broken logic of the scene is found before the host finds it.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- "what I see" is written before the caption or the page is opened, and the shot card and the generation log are never opened [review: cold reviewer]
- the passes include gaze in space, a count in full-size crops and the logic of the place, all before the caption [review: cold reviewer]
- a person who could not be there, a picture that passes for a photograph or a record, and a likeness of a living person are findings of weight trust and stop the picture [review: cold reviewer]
- the example finding carries every field, a canonical weight and a declared verdict, and every verdict but keep has a ready request [review: cold reviewer]
- a picture is marked only when the image itself was seen; a placeholder is reported as not reviewed [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-REVIEWER (names this skill in its blind-check mode)
- MOD-SKILL-DRAWING (hands the picture over)
- method/vocabulary.toml (review_weights)
- method/rules/catalog.toml (rules the skill relies on without restating)
:END_MODULE_CONTRACT
-->
# Blind check

One question: what story does this picture tell someone who knows nothing
about it? A child will ask "why?" about what you skip. A list of anachronisms
does not see a broken scene: a whole set of pictures once passed such a list
while the logic of every frame was wrong.

**Inputs:** the picture file and the page title. The caption and the page only
at step 5.

**Never open:** the shot card, generation logs, briefs to the artist, the
feed's research notes, earlier reviews of this feed. Otherwise you see what
they meant to draw. Whoever drew the picture does not check it.

**Output:** a file of findings next to the feed, written after each picture so
that a break loses nothing; a summary of the wave.

## What the host environment provides

A reviewer who sees images and has not seen the card or the brief, and a way
to cut an image into full-size crops. Which model sees, and at what cost, is
the host's choice.

## Engine commands

Commands marked *planned* are not in the engine yet. Until they are, do the
same by hand from the files named in the brief, or with the host's tool for
it, and say which in your report.

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | the resolved rules and settings of this feed, for the role `reviewer` with `--feed <id>` | present |
| `familiar feed crops` | a picture cut into a full-size grid and around each animal and hand, in a temporary folder | planned |
| `familiar feed pages` | the page of a picture: text, "More", the caption | present |
| `familiar feed accept` | the stage `blind` marked passed for current chapters | present |

## Order

1. **Look at the whole**, with the title only, at a moderate size. Before any
   check, write three to five lines of "what I see": who is who, of what age,
   how they seem related; what happens and who came to whom; where each one
   looks; season, hour, weather, where the light comes from; what a child
   will ask.
2. **Build the space.** Put everyone on a plan seen from above. Does what they
   look at stand in front of them or behind? Where does each group move, will
   two groups meet? A face turned to us cannot see what is behind it. On the
   flat picture a gaze often meets its target; in space it passes by.
3. **Count in full-size crops.** Each animal apart; hands and fingers, legs,
   runners, wheels, shafts, machines. What is hidden, say "hidden, not
   counted", never "all correct".
4. **The other passes.**
   - **Logic of the place:** where a door leads, where the stove stands and
     where its smoke goes, whether a cart runs along the road, whether a
     machine could work.
   - **Every visible thing:** why it is here, for these people, at this hour;
     whole, on the right side, the working side out.
   - **Groups:** copied faces and poses; posing; the waiting look anxious,
     not bored.
   - **Physics:** how many lights, do shadows agree; snow, mud, water, tracks;
     clothes and shoes for the season.
   - **Style:** next to another drawing of the feed, is it the same book? A
     picture close to a photograph is a finding.
   - **Letters and digits:** where none should be, and anything that could be
     read as a paper or a record.
   - **Faces:** a face of the twentieth century large and clear, where the feed
     keeps such faces turned away.
5. **Now open the caption and the page** (`familiar feed pages`). Does the
   caption promise what is visible? Does the picture argue with the page? How
   many people does the page put in the scene, and how many are drawn? This is
   the first moment you may learn what was meant.
6. **Write the findings** (form below), each with where on the picture and a
   canonical weight. End each picture with its main cause, a verdict and,
   unless the verdict is keep, a ready sentence for the request. When a
   caption fix is enough, propose the caption.
7. **Wave summary:** a table of file, verdict and main finding, and five to
   eight lines on what repeats from picture to picture and what the shot card
   should have said.
8. **Mark.** `familiar feed accept <feed> --stage blind` only for pictures you
   actually saw. A tool that returned a placeholder or nothing instead of the
   image: that picture was not reviewed; list it as such. A mark means
   "reviewed", not "no findings".

## Weights

Weights are the canonical `review_weights` of the engine vocabulary:

- `trust`: stop; the picture does not go on. A person stands where the page
  puts no one, or a child who does not exist; the picture looks like a
  photograph or a record; a face looks like a living person. The lead hears
  it now.
- `breaks-story`: a child sees it at once: the visitor stands where the host
  should, gazes miss, groups collide, five legs.
- `stumble`: an attentive viewer notices.
- `taste`: style within the feed's setting; the host decides.

Verdicts: `keep`, `fix-caption`, `fix-locally`, `redraw`.

## A finding

Example from the fictional family:

```json
{
  "picture": "rosa-1925 / font",
  "where": "centre, the man's hands",
  "weight": "breaks-story",
  "finding": "The man looks at the window, not at the baby he holds; a child cannot tell who matters.",
  "verdict": "fix-locally",
  "request": "The godfather looks down at the baby in his hands; the window stays behind him."
}
```

## Forks

- **Not a judge of the family's facts.** Ages and who is present belong to the
  card; you rule sight. A conflict is a question to the lead.
- **Unsure of a historical detail** with no support: mark it "check", with no
  weight.
- **What the eye allows is not an error:** a far shaft hidden by the horse, a
  face turned away on purpose, the softness of a painted style.
- **The picture is clean.** Say so. Precision, not length.

## In the report

Pictures seen and not seen; verdicts; what repeats and what the card should
say; a section "What was wrong in the brief and the tools".
