---
name: second-look
description: Check a difficult reading with the proposed transcription, or challenge an identity or kinship conclusion against its primary evidence.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-SECOND-LOOK
PURPOSE: Expose a mistaken reading or inference without inheriting a summary's missing evidence.
PRD_REF: docs/PRD.md#ROLES
INVARIANTS:
- both modes require primary inputs and declare missing evidence before judging [review: cold reviewer]
- reader mode compares our version against letter alternatives and same-hand samples [review: cold reviewer]
- each verdict has a reason and an explicit consequence for the case owner [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-SECOND-LOOK (mode entry and reasoning access boundary)
- docs/PRD.md#FORMS (reading, doubt and provenance)
:END_MODULE_CONTRACT
-->
# Second look

Choose reader or refuter mode for one named claim. Independence means testing
the evidence yourself, not being deprived of it. This is an informed check;
a blind reading is a separate task when explicitly requested.

## Input gate

Both modes receive the question, intended use, proposed answer and output
location. Inventory supplied and missing inputs before giving a verdict.

- Reader: our version of the transcription with doubts; cut-out and full
  page, exact frame locator, same-hand comparison samples, and what inference
  turns on the disputed field. Consult the region pack for script conventions.
- Refuter: original family notes on the people's cards, earlier family answers
  with witness basis, cited documents and their literal readings, source
  locators and dependencies, tree context, competing versions and weights,
  actual search coverage, and the specific inference to challenge. A packet
  containing only versions is incomplete: request the primary material or
  report a limited verdict with the omitted items named.

Missing images permit a critique of an inference, not a certified reading.
Do not silently treat a transcript as an inspected original.

## Reader

1. Inspect the image alongside our version. Locate the decisive word and its
   surrounding formula, headings and line breaks.
2. For each disputed letter list alternatives, stroke count and the same-hand
   samples with locators. If no useful sample exists, say so. Familiar names
   suggest candidates; they do not supply visible strokes.
3. Return a corrected literal reading with doubt marks, visible versus supplied
   text, and the consequence of each surviving reading for the claim. If the
   image cannot decide it, preserve alternatives and name a better image or
   another record that could. Agreement needs letter evidence too.

When a late birth date conflicts with a parish entry, compare birth, baptism
and registration as separate events in their established calendars. Preserve
each literal date; agreement after conversion suggests a candidate, not an
identity. When an apparent patronymic conflicts with the father's name, a
hereditary byname is one testable explanation: compare dated forms for the
father, grandfather and household, keeping competing people separate.
Basis: ex-ussr-kinship-research v1.46.0,
references/ex-ussr-locale-guide.md:80,136 (adapted method).

## Refuter

First form an evidence table from the primary packet, then compare the offered
versions. Seek the strongest counterexample: a namesake, incompatible spouse,
dependent sources counted twice, an omitted family observation, or a background
pattern counted as a personal match. Check that versions share one axis and
leave room for unknown; candidates and questions must not share a probability sum.

Check the inference against its stated grounds. If the role sheet withholds
the case argument, identify the precise inference supplied in the brief and
declare that unseen reasoning was not audited; do not claim to have refuted it.
Remove the weakest reading and ask whether the conclusion survives. An unusual
date combination invites a test, not an invented replacement relationship.
Look the other way too: a find left out for a differing year, spelling or
place without an argument over the whole mass is an objection, and a
divergence alone never makes a claim wrong.

## Verdict and return

Give a verdict per claim, not per person or whole case. These English labels
mean supported, contested and erroneous respectively:

| Verdict | Meaning | Case owner action |
|---|---|---|
| holds | evidence supports the claim within the declared scope; objections answered | retain decision with this review linked; no automatic promotion of other links |
| disputed | plausible claim with an unresolved conflict or missing decisive input | record objection, recompute weights without a floor or guaranteed leader, name the next distinguishing test |
| wrong | a located contradiction defeats the reading or inference as stated | withdraw or correct that claim with history; re-evaluate dependent conclusions |

For every objection supply locator, observation, inference, strength and the
record or comparison that would settle it. A disputed verdict can favour a
version but cannot impose a minimum weight. When input is incomplete, name the
best supported version or tie and the scope of the provisional verdict.
The case owner records the response to each objection; reviewer agreement is
not an additional historical source.

## Engine commands

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | resolved rules for the current role | present |
| `familiar research vocabulary` | canonical verdicts and doubt marks from the validator schema | present |

Canonical form verdicts and doubt marks: `familiar research vocabulary` (the shared schema). These encode the
method verdicts supported, contested and erroneous.
