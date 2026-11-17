---
name: research-versions
description: Lay out the whole mass of finds about a family's people, then run each link the story turns on through competing versions, a distinguishing test and a budgeted decision or pause.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-RESEARCH-VERSIONS
PURPOSE: Turn competing explanations of one family link into a bounded test and a revisable decision.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- the layout of people over the whole mass precedes the split into axes; no find is dropped for a divergence alone [review: cold reviewer]
- a test maps positive, contrary and unavailable outcomes before execution [review: cold reviewer]
- exhaustion leaves a state and reopening trigger rather than another search series [review: cold reviewer]
- an anomalous link remains literal until evidence supports its replacement [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-RESEARCHER (case and scene support entry)
- docs/PRD.md#FORMS (versions and provenance)
:END_MODULE_CONTRACT
-->
# Research versions

Use after an anchor record or the first memory-first pass. A fate is a
compound question: first lay out the whole mass, then split it into links.
The role supplies rules; this skill supplies the pass.

## Prepare

Read the original family notes on the people's cards, earlier answers and
source records before the current version summary. Inventory missing inputs;
a recent summary may have lost an older, direct observation. Record each
statement's locator and how the informant could know it.

## Lay out the mass

Gather every find from the packet and the collector's tables literally, each
with what matches and diverges; a divergence is a note, never a drop
(CRAFT-KEEP-THE-MASS); mark what is worth telling (CRAFT-INTEREST). Lay out
the whole mass at once: how many people, which lines are one person, which
fates it allows. Two or three weighted layouts plus an unknown remainder are
one question of their own ("one man married twice" against "two
namesakes"); a namesake table beside it keeps candidates fitting several.

Write every weighted question to the instance's configured versions
directory (one per file, earlier arguments and dated attribution kept), not
only beside the story; verify it appears in the person card.

## Split into links

Only then split the links the story turns on, one axis each: identity,
parents, birthplace or death year. Split combined questions within a layout. Versions on that axis exclude each other; put namesakes compatible
with several versions in a separate candidate table. Assign weights summing
to one, including an explicit unknown remainder. These are reasoned estimates,
not measured frequencies. Explain the allocation and its sensitivity.

## Compare

Make a compact table: observation and locator, which version it favours or
hurts, and dependency group. An original, its index and two readings are one
information lineage. A historical migration pattern suggests a prior; it is
not a personal match. Compare the family-specific evidence before that prior.
Test whether the conclusion survives removing its weakest reading. Explain
strong contradictions rather than outvoting them with generic similarities.

Anomalies follow CRAFT-FIX-IMPOSSIBLE-LINKS: literal dates and the link stay;
a very young father or a birth after the father's death is not itself a
refutation. Keep the earlier decision and the reason for changing it.

## Choose a test

Pick the cheapest available observation whose outcomes separate live versions.
Specify source class, field, coverage needed and fallback; ask the region pack
about record fields and availability. Re-reading a saved record can beat a new
query. Shape of a weighted question with its test: `familiar research form
version` (versions with weights, `unknown_weight`, and per test the outcomes
`positive`, `contrary`, `unreadable`, `unavailable`, each with effects on
versions). The next test is authored after reading.

Write outcomes before execution. A zero changes weights only if the expected
entry should occur in the relevant coverage actually read. Recompute all
weights after the observation, including unknown. No version has a protected
rank or minimum weight. Keep fact reading, identity and kinship decisions separate.

### Check the read coverage before widening

When a quick scan, thumbnails or OCR found nothing in a well-grounded narrow
window, consider a detailed reading of faint lines and unusual parent formulas.
Check the next section if the book orders entries by baptism rather than birth.
Choose re-reading or widening by expected value and access; a quick selection is
not a full reading. Basis: ex-ussr-kinship-research v1.46.0,
references/metric-books-scans.md:16 (adapted method, not a live source check).

For a composite book, check the end and section boundaries for an index, then
verify the parish by title and record content. A position in another year's
book is only a first probe until the binding order is compared. For a missing
child in a confession list, establish how that section records the child's age
group; the youngest observed child does not establish an inclusion threshold.
Basis: the same guide, references/field-lessons.md:42,83–87 and
references/search-result-validation.md:27.

A participant-role index may omit an untagged volume or attach a field from a
different row. Verify role, date and name on the image, and distinguish a case's
date from the event date. A viewer's 401 concerns that request; it alone does not
prove the browser is signed out. Preserve the normal viewer URL and frame; if
needed, check login in the ordinary interface without repeating image requests.
An explicit login challenge goes to the host. Basis: the same guide,
references/source-strategy.md:125 and references/browser-and-captcha.md:120–122;
these outside observations do not attest another site's index or access.

## Budget and stops

Before the pass record a time or effort cap, maximum source moves, spent amount
and checkpoint. Use the brief's budget; if absent, declare a provisional cap
of one distinguishing test and report that assumption. Stop at the first cap.

| Trigger | State | Checkpoint and reopening trigger |
|---|---|---|
| Test executing within budget | open | next observation and remaining budget |
| Named paper or access missing | waiting | holder or route, missing item; resume when it arrives |
| Budget exhausted or repeated unchanged evidence | review | coverage, weights, best next test and cost; lead allocates a new budget |
| Evidence resolves the question sufficiently for its stated use | closed | decision, grounds, remaining doubt; reopen on a new material contradiction |

Closing is a justified decision, including synthesis without a single direct
bridge; it does not certify neighbouring links. If unresolved, give the best
supported version and its status, or an explicit tie, without promoting it to
an accepted card fact. A pause stops searching, not telling: a leading version
at half or more is what the story tells as "most likely so". A route failure closes that route, not the question.
These are executable case states. A closed case requires an outcome; waiting
requires reason, resumes_on and holder. Use the canonical case form.

## Handoff

Leave the question, weights before/after with reasons, read coverage, decision
and scope, spent budget, state, next test and reopening trigger. Link the
source packet so second-look can recover primary testimony independently of
your summary. Name what the evidence now permits the story to tell.
Separate the earlier coverage from newly read pages and titles-only leads;
give the reason for a substantial repeat. Basis: ex-ussr-kinship-research
v1.46.0, SKILL.md:254–255.

## Engine commands

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | resolved rules for the current role | present |
